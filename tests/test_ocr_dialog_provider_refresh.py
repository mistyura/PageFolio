"""OCR ダイアログの LLM 設定適用後にプロバイダ表示が古いまま残る問題の回帰テスト。

事象（利用者報告）: LLM 設定でプロバイダ/モデルを変更しても OCR ダイアログの表示が
即時反映されない。表示は旧プロバイダのまま、実際の送信先だけが新プロバイダになり
「表示と実送信先の食い違い」で意図しない外部 API へ画像を送る可能性があった
（.planning/todos/pending/2026-10-24-ocr-dialog-provider-stale.md /
.planning/debug/ocr-ollama-uses-lmstudio-url.md）。

根因は 2 つの独立した機構:
  B1: _on_run / _on_summary が確定した設定スナップショット（_active_ocr_settings）が
      実行後も残り、_provider_display_name / _provider_model_name がそれを優先参照する
      ため、_apply_llm_settings が app.settings だけ更新しても表示が旧プロバイダのまま。
  B2: _apply_llm_settings が表示更新（_refresh_provider_dependent_ui）を provider 再生成
      より前に呼ぶため、isinstance(self.provider, ...) が旧 provider を見てしまう。

Tk ウィンドウは使わない（OCRDialog.__new__ で Tk 初期化を省略した headless インスタンス
+ 最小ウィジェットスタブ）。実メソッド _refresh_provider_dependent_ui /
_provider_display_name / _provider_model_name を通して「表示される値」を直接検証する。
"""

import types

import pytest

from pagefolio.lang import LANG

L = LANG["ja"]


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Label:
    """tk.Label の最小スタブ（configure(text=...) の最新値だけ保持）。"""

    def __init__(self):
        self.text = None

    def configure(self, **kw):
        if "text" in kw:
            self.text = kw["text"]


class _Frame:
    def pack(self, **kw):
        pass

    def pack_forget(self):
        pass


def _make_dialog(settings, provider, active_snapshot=None):
    """_apply_llm_settings を実メソッドの表示更新込みで駆動する headless ダイアログ。"""
    from pagefolio.ocr_dialog import OCRDialog

    d = OCRDialog.__new__(OCRDialog)
    d.app = types.SimpleNamespace(
        settings=dict(settings),
        _session_api_keys={},
        plugin_manager=None,
        _persist_settings=lambda: True,
    )
    d._L = L
    d.provider = provider
    d._active_ocr_settings = active_snapshot
    d.custom_prompt = ""
    d.concurrency = 1
    d.progress_var = _Var()
    d.url_var = _Var(settings.get("lm_studio_url", ""))
    d.model_var = _Var(settings.get("lm_studio_model", ""))
    # 実 _refresh_provider_dependent_ui が触れるウィジェット
    d._provider_value_label = _Label()
    d._model_value_label = _Label()
    d._lmstudio_server_frame = _Frame()
    d._lmstudio_model_frame = _Frame()
    d._params_row = object()
    d._grow_to_fit = lambda: None
    # Tk 依存の周辺は no-op（本テストの対象外）
    d._sync_param_vars_from_settings = lambda: None
    d._update_summary_btn_state = lambda: None
    d._update_preset_note = lambda: None
    d._maybe_show_lang_fallback_notice = lambda: None
    return d


def _base_settings(provider):
    return {
        "ocr_provider": provider,
        "lm_studio_url": "http://localhost:1234",
        "lm_studio_model": "lm-model",
        "ollama_url": "http://127.0.0.1:17327",
        "ollama_model": "ollama-model",
        "claude_model": "claude-sonnet-4-6",
        "gemini_model": "gemini-3.1-flash-lite",
        "openai_model": "gpt-5.1",
        "ocr_timeout": 120,
        "ocr_max_tokens": -1,
        "ocr_temperature": 0.1,
        "lang": "ja",
    }


@pytest.fixture(autouse=True)
def _no_real_keys(monkeypatch):
    """実環境の API キーに依存させない（キー有無は表示の検証と無関係）。"""
    for var in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "RUNPOD_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


class TestApplyLlmSettingsRefreshesDisplay:
    def test_ollama_to_gemini_after_a_run_shows_gemini(self):
        """1 回実行した後（スナップショット確定済み）に ollama -> gemini へ適用すると、
        表示ラベル・モデルは新プロバイダ gemini になる（旧 ollama のままにしない）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import GeminiProvider, OllamaProvider

        old = _base_settings("ollama")
        d = _make_dialog(
            old,
            OllamaProvider(url=old["ollama_url"], model=old["ollama_model"]),
            active_snapshot=dict(old),  # _on_run が確定した旧スナップショット
        )

        OCRDialog._apply_llm_settings(
            d, {"ocr_provider": "gemini", "gemini_model": "gemini-3.1-flash-lite"}
        )

        assert isinstance(d.provider, GeminiProvider)
        assert d._provider_value_label.text == L["ocr_provider_name_gemini"], (
            f"表示が旧プロバイダのまま: {d._provider_value_label.text!r}"
        )
        assert "gemini-3.1-flash-lite" in d._model_value_label.text
        assert "ollama" not in d._provider_value_label.text

    def test_active_snapshot_is_cleared_on_apply(self):
        """適用後は旧スナップショットが表示判定を固定しない（None に戻る）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import OllamaProvider

        old = _base_settings("ollama")
        d = _make_dialog(
            old,
            OllamaProvider(url=old["ollama_url"], model=old["ollama_model"]),
            active_snapshot=dict(old),
        )

        OCRDialog._apply_llm_settings(d, {"ocr_provider": "gemini"})

        assert d._active_ocr_settings is None
        assert d._active_provider_name() == "gemini"

    def test_gemini_to_openai_before_any_run_shows_openai(self):
        """一度も実行していない（スナップショットなし）場合でも、provider 再生成より
        前に表示更新して旧 provider の isinstance に引きずられる順序バグがない。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import GeminiProvider, OpenAIProvider

        old = _base_settings("gemini")
        d = _make_dialog(old, GeminiProvider(api_key="x", model=old["gemini_model"]))

        OCRDialog._apply_llm_settings(
            d, {"ocr_provider": "openai", "openai_model": "gpt-5.1"}
        )

        assert isinstance(d.provider, OpenAIProvider)
        assert d._provider_value_label.text == L["ocr_provider_name_openai"], (
            f"表示が旧プロバイダのまま: {d._provider_value_label.text!r}"
        )
        assert "gpt-5.1" in d._model_value_label.text
        assert "gemini-3.1-flash-lite" not in d._model_value_label.text

    def test_lmstudio_to_ollama_shows_ollama_model(self):
        """ローカル同士の切替（lmstudio -> ollama）でもモデル表示が新しい値になる。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import LMStudioProvider, OllamaProvider

        old = _base_settings("lmstudio")
        d = _make_dialog(
            old,
            LMStudioProvider(url=old["lm_studio_url"], model=old["lm_studio_model"]),
        )

        OCRDialog._apply_llm_settings(
            d, {"ocr_provider": "ollama", "ollama_model": "ollama-model"}
        )

        assert isinstance(d.provider, OllamaProvider)
        assert d._provider_value_label.text == "ollama"
        assert "ollama-model" in d._model_value_label.text
        assert "lm-model" not in d._model_value_label.text

    def test_refresh_runs_after_provider_regeneration(self):
        """_refresh_provider_dependent_ui は provider 再生成の後に 1 回だけ呼ばれる
        （呼び出し時点で self.provider は新プロバイダ）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import GeminiProvider, OllamaProvider

        old = _base_settings("ollama")
        d = _make_dialog(
            old, OllamaProvider(url=old["ollama_url"], model=old["ollama_model"])
        )
        seen = []
        d._refresh_provider_dependent_ui = lambda: seen.append(d.provider)

        OCRDialog._apply_llm_settings(d, {"ocr_provider": "gemini"})

        assert len(seen) == 1, f"表示更新の呼び出し回数が想定外: {len(seen)}"
        assert isinstance(seen[0], GeminiProvider), (
            f"表示更新が旧 provider の状態で呼ばれた: {type(seen[0]).__name__}"
        )

    def test_refresh_still_runs_when_provider_regeneration_fails(self, monkeypatch):
        """provider 再生成が例外で失敗しても表示更新は必ず実行される。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import OllamaProvider

        def _boom(*a, **k):
            raise RuntimeError("build failed")

        monkeypatch.setattr("pagefolio.ocr.build_provider", _boom)
        old = _base_settings("ollama")
        d = _make_dialog(
            old, OllamaProvider(url=old["ollama_url"], model=old["ollama_model"])
        )
        calls = []
        d._refresh_provider_dependent_ui = lambda: calls.append(1)

        OCRDialog._apply_llm_settings(d, {"ocr_provider": "gemini"})

        assert calls == [1]
        assert d.progress_var.get()  # 失敗通知（ocr_provider_rebuild_error）が出ている
