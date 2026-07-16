# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLMConfigDialog の ModelFetchMixin（_fetch_models_async + probe/refresh 群）"""

import logging
import os
import threading
import tkinter as tk

from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider, LMStudioProvider
from pagefolio.ocr_providers.registry import env_vars_for

logger = logging.getLogger(__name__)


def _env_fallback(provider_name):
    """provider_name の環境変数値を優先順（env_vars_for のタプル順）で解決する。

    D-09 #5: 旧コードの `os.environ.get("RUNPOD_API_KEY", "")` /
    `os.environ.get("ANTHROPIC_API_KEY", "")` /
    `os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")`
    という3箇所のハードコード分岐を、registry.env_vars_for() 経由の単一
    ループへ統合する。Gemini は GEMINI_API_KEY → GOOGLE_API_KEY の優先順が
    env_vars_for のタプル順そのものなので自動的に保たれる。
    いずれの環境変数も未設定なら空文字を返す（None にしない・現行仕様）。
    """
    for var in env_vars_for(provider_name):
        val = os.environ.get(var)
        if val:
            return val
    return ""


class ModelFetchMixin:
    """_fetch_models_async とプロバイダ別 probe/refresh 群を担う Mixin。"""

    # ── LM Studio モデル取得 ────────────────────────────
    def _probe_lm_provider(self, update_combo):
        """LM Studio への接続確認・モデル取得の共有ヘルパー（L-6i）。

        `_fetch_models`（モデル取得）と `_test_connection`（接続テストのみ）は
        「取得結果を Combobox へ反映するか」のみが差分のため、update_combo
        フラグでパラメータ化して重複ロジックを1箇所に集約する。

        引数:
          update_combo: True のとき取得したモデル一覧を
                        self.lm_model_combo["values"] へ反映する。
        """
        url = self.lm_url_var.get().strip()
        if not url:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error="URL is empty"),
                kind="fail",
            )
            return
        self._set_lm_status(self._L["settings_lm_testing"].format(url=url), kind="info")
        try:
            models = LMStudioProvider(url=url, model="").list_models()
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error=str(e)), kind="fail"
            )
            return
        if update_combo:
            self.lm_model_combo["values"] = models
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    def _fetch_models(self):
        """LM Studio からモデル一覧を取得して Combobox に反映する。"""
        self._probe_lm_provider(update_combo=True)

    def _test_connection(self):
        """LM Studio への接続をテストする。"""
        self._probe_lm_provider(update_combo=False)

    # ── Ollama モデル取得・テスト ────────────────────────
    def _probe_ollama_provider(self, update_combo):
        """Ollama への接続確認・モデル取得の共有ヘルパー（C2）。

        `_fetch_ollama_models`（モデル取得）と `_test_ollama_connection`
        （接続テストのみ）は「取得結果を Combobox へ反映するか」のみが差分のため、
        update_combo フラグでパラメータ化して重複ロジックを1箇所に集約する
        （LM Studio 用 `_probe_lm_provider` と同型の統合）。

        引数:
          update_combo: True のとき取得したモデル一覧を
                        self.ollama_model_combo["values"] へ反映する。
        """
        url = self.ollama_url_var.get().strip()
        if not url:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error="URL is empty"),
                kind="fail",
            )
            return
        self._set_lm_status(self._L["settings_lm_testing"].format(url=url), kind="info")
        try:
            from pagefolio.ocr_providers import OllamaProvider

            models = OllamaProvider(url=url, model="").list_models()
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error=str(e)), kind="fail"
            )
            return
        if update_combo:
            self.ollama_model_combo["values"] = models
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    def _fetch_ollama_models(self):
        """Ollama からモデル一覧を取得して Combobox に反映する。"""
        self._probe_ollama_provider(update_combo=True)

    def _test_ollama_connection(self):
        """Ollama への接続をテストする。"""
        self._probe_ollama_provider(update_combo=False)

    # ── クラウドモデル取得の非同期実行ヘルパー（V174）─────────
    def _fetch_models_async(self, fetch_fn, on_success, on_error):
        """モデル一覧取得をバックグラウンドスレッドで実行する共有ヘルパー。

        クラウドプロバイダ（Claude / Gemini / RunPod）のモデル一覧取得は
        model_list_timeout（30〜90 秒）まで待つため、メインスレッドで
        同期実行すると UI がその間フリーズする（特に RunPod Serverless の
        コールドスタート）。ワーカースレッドで fetch_fn() を実行し、結果は
        after(0) でメインスレッドへ戻して on_success(models) /
        on_error(exception) を呼ぶ。実行中の再クリックは
        _model_fetch_running ガードで無視する（Combobox 反映と
        ステータス更新はコールバック側の責務）。
        """
        if getattr(self, "_model_fetch_running", False):
            return
        self._model_fetch_running = True

        def _deliver(callback, arg):
            # メインスレッドへ結果を投函する。ダイアログ破棄後は静かに捨てる
            def _run():
                self._model_fetch_running = False
                try:
                    if not self.winfo_exists():
                        return
                except tk.TclError:
                    return
                callback(arg)

            try:
                self.after(0, _run)
            except (tk.TclError, RuntimeError):
                self._model_fetch_running = False

        def _worker():
            try:
                models = fetch_fn()
            except Exception as e:
                _deliver(on_error, e)
            else:
                _deliver(on_success, models)

        threading.Thread(target=_worker, daemon=True).start()

    # ── RunPod モデル更新 ───────────────────────────────
    def _refresh_runpod_models(self):
        """RunPod モデル一覧を取得して Combobox に反映する。

        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        V174: Serverless の初回起動（コールドスタート）はワーカー起動待ちで
        10 秒を大きく超えることがあるため、model_list_timeout=90 秒の取得を
        バックグラウンド実行し UI はブロックしない。
        """
        api_key = self.runpod_api_key_var.get().strip() or _env_fallback("runpod")
        url = self.runpod_url_var.get().strip()
        if not api_key:
            self._set_lm_status(
                self._L["llm_env_key_unset_static_runpod"],
                kind="info",
            )
            return
        self._set_lm_status(self._L["llm_fetching_runpod_models"], kind="info")
        from pagefolio.ocr_providers import RunPodProvider

        provider = RunPodProvider(api_key=api_key, url=url, model="")

        def _on_success(models):
            self.runpod_model_combo["values"] = models
            self._set_lm_status(
                self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
            )

        def _on_error(e):
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="RunPod", e=e)
            )
            self._set_lm_status(
                str(e),
                kind="fail",
            )

        self._fetch_models_async(provider.list_models, _on_success, _on_error)

    # ── Claude モデル更新 ───────────────────────────────
    def _refresh_claude_models(self):
        """Claude モデル一覧を取得して Combobox に反映する。

        ANTHROPIC_API_KEY が未設定でも ClaudeProvider.list_models が
        RECOMMENDED_MODELS を返すので静的リストが常に表示される（D-08）。
        api_key は settings に書かない（D-01/D-05）。
        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        """
        self._set_lm_status(self._L["llm_fetching_claude_models"], kind="info")
        api_key = self.claude_api_key_var.get().strip() or _env_fallback("claude")
        provider = ClaudeProvider(api_key=api_key, model="")

        def _on_success(models):
            self.claude_model_combo["values"] = models
            if not api_key:
                self._set_lm_status(
                    self._L["llm_env_key_unset_static"],
                    kind="info",
                )
            else:
                self._set_lm_status(
                    self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
                )

        def _on_error(e):
            # 例外時は静的推奨リストへフォールバック（D-08）
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="Claude", e=e)
            )
            self.claude_model_combo["values"] = ClaudeProvider.RECOMMENDED_MODELS
            self._set_lm_status(
                self._L["llm_env_key_unset_static"],
                kind="info",
            )

        # V174: クラウド API は model_list_timeout=30 秒までかかり得るため
        # バックグラウンド実行し UI はブロックしない
        self._fetch_models_async(provider.list_models, _on_success, _on_error)

    # ── Gemini モデル更新 ───────────────────────────────
    def _refresh_gemini_models(self):
        """Gemini モデル一覧を取得して Combobox に反映する。

        GEMINI_API_KEY / GOOGLE_API_KEY が未設定でも GeminiProvider.list_models が
        RECOMMENDED_MODELS を返すので静的リストが常に表示される（D-08）。
        api_key は settings に書かない（D-01/D-05）。
        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        """
        self._set_lm_status(self._L["llm_fetching_gemini_models"], kind="info")
        api_key = self.gemini_api_key_var.get().strip() or _env_fallback("gemini")
        provider = GeminiProvider(api_key=api_key, model="")

        def _on_success(models):
            self.gemini_model_combo["values"] = models
            if not api_key:
                self._set_lm_status(
                    self._L["llm_env_key_unset_static_gemini"],
                    kind="info",
                )
            else:
                self._set_lm_status(
                    self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
                )

        def _on_error(e):
            # 例外時は静的推奨リストへフォールバック（D-08）
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="Gemini", e=e)
            )
            self.gemini_model_combo["values"] = GeminiProvider.RECOMMENDED_MODELS
            self._set_lm_status(
                self._L["llm_env_key_unset_static_gemini"],
                kind="info",
            )

        # V174: クラウド API は model_list_timeout=30 秒までかかり得るため
        # バックグラウンド実行し UI はブロックしない
        self._fetch_models_async(provider.list_models, _on_success, _on_error)
