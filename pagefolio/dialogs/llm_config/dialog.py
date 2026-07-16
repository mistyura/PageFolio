# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLMConfigDialog の DialogMixin。

__init__ / _apply / _on_provider_change / _on_model_change /
_model_supports_effort / _resize_to_fit / _add_prompt_file_notice /
_set_lm_status とスクロール域構築の共通部を担う。
"""

import copy
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import CUSTOM_PROMPT_FILE, LANG, SUMMARY_PROMPT_FILE, C
from pagefolio.ocr import MAX_OCR_MAX_TOKENS
from pagefolio.ocr_providers import ClaudeProvider, _detect_tesseract
from pagefolio.settings import get_current_font_size, prompt_file_exists

# effort 値の許可リスト（D-17）
_EFFORT_VALUES = ("low", "medium", "high", "xhigh", "max")


class DialogMixin:
    """__init__ / _apply / _on_* / スクロール域構築等の共通部を担う Mixin。"""

    def __init__(
        self,
        parent,
        current_settings,
        on_apply,
        font_func=None,
        lang="ja",
        plugin_manager=None,
        session_api_keys=None,
    ):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["llm_config_title"])
        self.configure(bg=C["BG_DARK"])
        # 環境によって画面解像度が低い/フォントが大きいと内容が画面に収まらないため、
        # スクロール可能にしつつウィンドウのリサイズも許可する（H-6）。
        self.resizable(True, True)
        self.minsize(420, 320)
        self.grab_set()

        self.current_settings = dict(current_settings)
        # CR-02 修正: prompt_templates はネスト辞書（items・各テンプレート dict）
        # を持つため、上の dict() による浅いコピーでは app.settings["prompt_templates"]
        # と同一参照を共有したままになる。ダイアログ内の CRUD 操作（保存/削除/
        # リネーム）が呼び出し元の app.settings を汚染しないよう、ここで
        # ディープコピーして完全に独立させる（V180-TMPL-01/03・02-REVIEW CR-02）。
        self.current_settings["prompt_templates"] = copy.deepcopy(
            current_settings.get("prompt_templates", {"active": "", "items": {}})
        )
        self.on_apply = on_apply
        self._font = font_func or (
            lambda d=0, w=None: (
                ("Segoe UI", max(7, 10 + d), w) if w else ("Segoe UI", max(7, 10 + d))
            )
        )
        self._plugin_manager = plugin_manager
        # V171-KEY-01: session_api_keys は複製せず参照をそのまま保持する
        # （複製すると app._session_api_keys の実体へ変更が反映されない）。
        self._session_api_keys = (
            session_api_keys if session_api_keys is not None else {}
        )
        # D-05/Pitfall 2: ocr_providers.py と同じ _detect_tesseract() を都度呼び、
        # ダイアログを開く度に再評価する（再起動なしで言語パック追加を反映）。
        self._tesseract_available, self._tesseract_langs = _detect_tesseract()
        # 02-REVIEW CR-01 修正: 初期プロバイダは Tesseract 可用性が判明した
        # *後* に確定させる。可用性判定前に current_settings の値をそのまま
        # self._last_valid_provider へ入れると、永続化された値が
        # "tesseract"（かつ現在は未インストール）の場合、_on_provider_change
        # のガードが自分自身にフォールバックする自己参照になり無効化される。
        _initial_provider = current_settings.get("ocr_provider", "off")
        if _initial_provider == "tesseract" and not self._tesseract_available:
            _initial_provider = "off"
        # 選択リセット用（D-02）・sections.py の provider_var 初期値もこれと
        # 揃える（_initial_provider として公開し、combobox とガードのフォール
        # バック先が最初から一致するようにする）。
        self._initial_provider = _initial_provider
        self._last_valid_provider = _initial_provider

        # _dialog_w は _build() 内の _resize_to_fit() が参照するため、_build() より
        # 前に確定させておく（未設定だと AttributeError でダイアログが開けない）。
        try:
            fs = int(self._font(0)[1])
        except Exception:
            fs = get_current_font_size()
        self._dialog_w = max(540, int(fs * 44))

        self._build()
        self.update_idletasks()
        h = self._compute_dialog_height()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{self._dialog_w}x{h}+{px - self._dialog_w // 2}+{py - h // 2}")

    # ── スクロール可能領域の構築（H-6）──────────────────
    def _build_scrollable_area(self):
        """本文をスクロール可能な Canvas 上に構築するための土台を作る。

        画面が小さい/フォントが大きい環境でも内容全体へアクセスできるよう、
        Apply/Cancel ボタン行はスクロール領域の外（下部固定）に配置する。
        戻り値は本文ウィジェットの親として使う Frame（self._body）。
        """
        outer = tk.Frame(self, bg=C["BG_DARK"])
        outer.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=C["BG_DARK"], highlightthickness=0, borderwidth=0)
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        body = tk.Frame(canvas, bg=C["BG_DARK"])
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(_event=None):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except tk.TclError:
                pass

        def _on_canvas_configure(event):
            try:
                canvas.itemconfig(body_window, width=event.width)
            except tk.TclError:
                pass

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        def _bind_wheel(_event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel_linux)
            canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        def _unbind_wheel(_event=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        self.bind("<Destroy>", lambda _e: _unbind_wheel(), add="+")

        self._canvas = canvas
        return body

    # ── ダイアログ高さ算出（画面サイズにクランプ・H-6）──────
    def _compute_dialog_height(self):
        """本文の必要高さと画面サイズから、はみ出さないウィンドウ高を求める。

        内容が画面に収まる場合はそのまま表示し、収まらない場合は画面高に
        クランプしてスクロールバー経由でアクセスできるようにする。
        """
        try:
            self.update_idletasks()
            content_h = self._body.winfo_reqheight() + self._btn_row.winfo_reqheight()
            screen_h = self.winfo_screenheight()
        except tk.TclError:
            return 480
        max_h = max(320, screen_h - 100)
        return min(max_h, max(480, content_h + 40))

    # ── プロバイダ変更ハンドラ ──────────────────────────
    def _on_provider_change(self, _event=None):
        """プロバイダ選択に応じて下位欄を pack/pack_forget で切替。"""
        provider = self.provider_var.get()

        # Tesseract 未インストール時: 選択を前の有効プロバイダに戻す（D-02 代替）
        if provider == "tesseract" and not self._tesseract_available:
            self.provider_var.set(self._last_valid_provider)
            self._set_lm_status(
                self._L.get(
                    "tesseract_not_installed_hint",
                    "Tesseract is not installed. Please use another provider.",
                ),
                kind="fail",
            )
            return
        # 有効な選択を記録
        self._last_valid_provider = provider

        # LM Studio 固有欄
        # H-4: before=self.scale_row でプロバイダ別セクションをボタン行より上に挿入
        if provider == "lmstudio":
            self.url_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
        else:
            self.url_section_frame.pack_forget()

        # Ollama 固有欄
        if provider == "ollama":
            self.ollama_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
        else:
            self.ollama_section_frame.pack_forget()

        # RunPod 固有欄
        if provider == "runpod":
            self.runpod_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
        else:
            self.runpod_section_frame.pack_forget()

        # Claude 固有欄
        if provider == "claude":
            self.claude_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
            self.gemini_section_frame.pack_forget()
            self.tesseract_section_frame.pack_forget()
            # D-15: 固有設定の直後・共通パラメータ群の先頭に見出しを再配置
            self._common_section_heading.pack(
                anchor="w", padx=24, pady=(6, 2), before=self.scale_row
            )
            # モデルに応じて effort/temperature を切替
            self._on_model_change()
        elif provider == "gemini":
            # Gemini: モデル欄を表示、effort 非対応のため temperature のみ（D-09）
            self.gemini_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
            self.claude_section_frame.pack_forget()
            self.tesseract_section_frame.pack_forget()
            self.effort_frame.pack_forget()
            self._common_section_heading.pack(
                anchor="w", padx=24, pady=(6, 2), before=self.scale_row
            )
            self.temperature_frame.pack(
                fill="x", padx=24, pady=2, before=self.scale_row
            )
            self._resize_to_fit()
        elif provider == "tesseract":
            # Tesseract: 精度注記フレームを表示。API 設定・temperature は不要（D-03）
            self.tesseract_section_frame.pack(
                fill="x", padx=24, pady=(4, 2), before=self.scale_row
            )
            self.claude_section_frame.pack_forget()
            self.gemini_section_frame.pack_forget()
            self.effort_frame.pack_forget()
            self.temperature_frame.pack_forget()
            self._common_section_heading.pack(
                anchor="w", padx=24, pady=(6, 2), before=self.scale_row
            )
            self._resize_to_fit()
        else:
            self.claude_section_frame.pack_forget()
            self.gemini_section_frame.pack_forget()
            self.tesseract_section_frame.pack_forget()
            # lmstudio / off では temperature 欄を表示し effort 欄を隠す（従来挙動）
            self.effort_frame.pack_forget()
            self._common_section_heading.pack(
                anchor="w", padx=24, pady=(6, 2), before=self.scale_row
            )
            self.temperature_frame.pack(
                fill="x", padx=24, pady=2, before=self.scale_row
            )
            self._resize_to_fit()

    # ── モデル変更ハンドラ（effort/temperature 切替）──────
    def _on_model_change(self, _event=None):
        """claude モデル変更時に effort/temperature 欄を切替。

        effort 対応モデル（sonnet/opus 系）のとき effort 欄を表示し
        temperature 欄を隠す（D-17）。haiku 系は temperature 欄を表示。
        H-4: before=self.scale_row でボタン行より上に挿入。
        H-5: 末尾で _resize_to_fit を呼びダイアログ高さを追従させる。
        """
        model = self.claude_model_var.get()
        if self._model_supports_effort(model):
            self.effort_frame.pack(fill="x", padx=24, pady=2, before=self.scale_row)
            self.temperature_frame.pack_forget()
        else:
            self.temperature_frame.pack(
                fill="x", padx=24, pady=2, before=self.scale_row
            )
            self.effort_frame.pack_forget()
        self._resize_to_fit()

    # ── effort 対応判定 ────────────────────────────────
    def _model_supports_effort(self, model):
        """モデルが effort パラメータ（output_config）に対応しているか判定する。

        M-3: ocr_providers.ClaudeProvider._supports_effort と同じ判定に揃える。
        EFFORT_MODELS 完全一致のみ True（前方互換 prefix 判定を撤廃）。

        戻り値: EFFORT_MODELS 完全一致のみ True、それ以外は False。
        """
        if not model:
            return False
        # M-3: EFFORT_MODELS 完全一致のみ True（prefix 判定撤廃・D-16 整合）
        return model in ClaudeProvider.EFFORT_MODELS

    # ── ダイアログ高さ再計算（H-5）──────────────────────
    def _resize_to_fit(self):
        """プロバイダ/モデル切替後にダイアログ高さを再計算して現在位置で再適用する。

        self._dialog_w を幅として維持し、winfo_reqheight から高さを算出する。
        ウィンドウ破棄レースに備え TclError を最小スコープで保護（D-18）。
        """
        try:
            self.update_idletasks()
            h = self._compute_dialog_height()
            # ユーザーが手動でリサイズ済みの場合はその幅を維持する（H-6）。
            w = max(self._dialog_w, self.winfo_width())
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    # ── 外部プロンプトファイル注記（V174-2）─────────────────
    def _add_prompt_file_notice(self, body, filename):
        """外部プロンプト md ファイル検出時のみ注記ラベルを追加する。

        実行ファイルと同じ階層に filename（ocr_custom_prompt.md /
        ocr_summary_prompt.md）が存在すれば「ファイル連動モード」
        （開いたとき入力欄へ反映・適用時に書き戻し）である旨を WARNING 色で
        表示する。空ファイルでも連動対象のため存在のみで判定する。
        ファイルが無ければ何も追加しない（通常ユーザーの画面は従来どおり）。
        """
        if not prompt_file_exists(filename):
            return
        notice_row = tk.Frame(body, bg=C["BG_DARK"])
        notice_row.pack(fill="x", padx=24, pady=(0, 2))
        tk.Label(
            notice_row,
            text="",
            bg=C["BG_DARK"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        tk.Label(
            notice_row,
            text=self._L.get(
                "ocr_prompt_file_in_use",
                "📄 {file} と連動中 — 適用時にこの欄の内容をファイルへ保存します",
            ).format(file=filename),
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(-2),
            anchor="w",
        ).pack(side="left", padx=4)

    # ── ステータス表示 ──────────────────────────────────
    def _set_lm_status(self, text, kind="info"):
        """LM Studio / Claude 操作の状態を表示する。kind: 'info' / 'ok' / 'fail'"""
        color = {
            "ok": C["SUCCESS"],
            "fail": C["ACCENT"],
            "info": C["WARNING"],
        }.get(kind, C["TEXT_MAIN"])
        self.lm_status_var.set(text)
        try:
            self.lm_status_label.configure(fg=color)
        except tk.TclError:
            pass
        # ボタン押下直後の状態を即時描画
        try:
            self.update_idletasks()
        except tk.TclError:
            pass

    # ── 設定保存 ────────────────────────────────────────
    def _apply(self):
        """現在の UI 値を llm_settings に収集して on_apply コールバックに渡す。

        セキュリティ制約:
          - api_key 系キーは絶対に llm_settings に入れない（成功基準1・T-05-12）
          - ocr_provider / claude_model / ocr_effort は無害な設定値として格納する
        """
        llm_settings = {}

        # プロバイダ選択（OCR-UI-01）
        llm_settings["ocr_provider"] = self.provider_var.get()

        # LM Studio 設定
        llm_settings["lm_studio_url"] = self.lm_url_var.get().strip() or (
            "http://localhost:1234"
        )
        llm_settings["lm_studio_model"] = self.lm_model_var.get().strip()

        # Ollama 設定
        llm_settings["ollama_url"] = self.ollama_url_var.get().strip() or (
            "http://localhost:11434"
        )
        llm_settings["ollama_model"] = self.ollama_model_var.get().strip()

        # RunPod 設定
        llm_settings["runpod_url"] = self.runpod_url_var.get().strip()
        llm_settings["runpod_model"] = self.runpod_model_var.get().strip()

        # Claude 設定（claude_model・ocr_effort は api_key と異なり無害な設定値）
        llm_settings["claude_model"] = (
            self.claude_model_var.get().strip() or "claude-sonnet-4-6"
        )
        raw_effort = self.effort_var.get()
        llm_settings["ocr_effort"] = (
            raw_effort if raw_effort in _EFFORT_VALUES else "low"
        )
        # Gemini 設定（gemini_model は api_key と異なり無害な設定値・T-06-10）
        llm_settings["gemini_model"] = (
            self.gemini_model_var.get().strip() or "gemini-2.5-flash"
        )

        # Tesseract 設定（D-04: lang は self._tesseract_langs 由来の固定値。
        # D-05: ダイアログ生成時に再検出済みの値を使う。getattr フォールバックは
        # _apply を Tk 生成なしスタブ経由で呼ぶ既存テスト経路の安全確保のため
        # （Phase 05-03 の _session_api_keys と同型パターン）
        _tess_langs = getattr(self, "_tesseract_langs", frozenset())
        llm_settings["tesseract_lang"] = "jpn+eng" if "jpn" in _tess_langs else "eng"

        # 共通数値設定（クランプして格納）
        try:
            llm_settings["ocr_scale"] = max(
                1.0, min(4.0, float(self.ocr_scale_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_scale"] = 1.5  # WR-01: D-11 整合
        try:
            llm_settings["ocr_timeout"] = max(
                10, min(900, int(self.ocr_timeout_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_timeout"] = 120
        try:
            mt = int(self.ocr_max_tokens_var.get())
            llm_settings["ocr_max_tokens"] = max(-1, min(MAX_OCR_MAX_TOKENS, mt))
        except (tk.TclError, ValueError):
            llm_settings["ocr_max_tokens"] = -1
        llm_settings["ocr_custom_prompt"] = self.ocr_prompt_text.get(
            "1.0", "end"
        ).strip()
        llm_settings["ocr_summary_prompt"] = self.ocr_summary_prompt_text.get(
            "1.0", "end"
        ).strip()
        # V174-2: ファイル連動モード（外部 md ファイルが既に存在する場合）は
        # 入力欄の内容をファイルへ書き戻す（画面 ⇄ md の双方向同期）。
        # ファイルを使わないユーザーには新規作成しない（settings のみで完結）。
        # 分割前は同一モジュール内の名前空間で
        # monkeypatch(pagefolio.dialogs.llm_config, "prompt_file_exists"/...) が
        # 効いていたため、分割後も pagefolio.dialogs.llm_config（パッケージ）
        # 経由の遅延 import で同じ差し替え可能性を保つ（Plan 02 の
        # _detect_tesseract 遅延 import と同型の措置）。
        from pagefolio.dialogs.llm_config import (
            prompt_file_exists as _prompt_file_exists,
        )
        from pagefolio.dialogs.llm_config import (
            save_prompt_file as _save_prompt_file,
        )

        if _prompt_file_exists(CUSTOM_PROMPT_FILE):
            _save_prompt_file(CUSTOM_PROMPT_FILE, llm_settings["ocr_custom_prompt"])
        if _prompt_file_exists(SUMMARY_PROMPT_FILE):
            _save_prompt_file(SUMMARY_PROMPT_FILE, llm_settings["ocr_summary_prompt"])
        try:
            tmp = float(self.ocr_temperature_var.get())
            llm_settings["ocr_temperature"] = max(0.0, min(2.0, tmp))
        except (tk.TclError, ValueError):
            llm_settings["ocr_temperature"] = 0.1
        try:
            conc = int(self.ocr_concurrency_var.get())
            llm_settings["ocr_concurrency"] = max(1, min(8, conc))
        except (tk.TclError, ValueError):
            llm_settings["ocr_concurrency"] = 2

        # v1.8.0 Phase 2: アクティブテンプレート名の収集（V180-TMPL-01〜05）。
        # CR-02 修正: CRUD 操作（保存/削除/リネーム）は sections.py 側で
        # 分離済み（__init__ でディープコピー済み）の self.current_settings
        # のみを in-place 変更し、もはや永続化しない。_apply が active +
        # items を一括収集し、on_apply 経由で単一経路で確定・永続化する
        # （Apply/Cancel 契約の回復）。items は copy.deepcopy して
        # app.settings へ完全独立した構造を渡す（内側のテンプレート dict まで
        # 独立させ、以後のエイリアス共有を防ぐ）。既存の _apply スタブ経路
        # （current_settings/_active_template_name 未設定）との後方互換の
        # ため getattr でフォールバックする。
        existing_templates = getattr(self, "current_settings", {}).get(
            "prompt_templates", {"active": "", "items": {}}
        )
        llm_settings["prompt_templates"] = {
            "active": getattr(
                self, "_active_template_name", existing_templates.get("active", "")
            ),
            "items": copy.deepcopy(existing_templates.get("items", {})),
        }

        # v1.8.0 Phase 2: フォールバック設定の収集（V180-FALL-01/03・D-14）。
        # fallback_enabled_var/_fallback_chain 未設定の既存 _apply スタブ経路
        # （current_settings 同様の後方互換）では既定値（False・空リスト）を
        # 収集する。_fallback_chain の各要素は既知プロバイダ一覧
        # （_fallback_known_providers）でホワイトリスト検証してから格納する
        # （Input Validation・ASVS L1・T-02-07）。
        _fallback_enabled_var = getattr(self, "fallback_enabled_var", None)
        llm_settings["ocr_fallback_enabled"] = bool(
            _fallback_enabled_var.get() if _fallback_enabled_var is not None else False
        )
        _known_fallback_providers = getattr(self, "_fallback_known_providers", [])
        llm_settings["ocr_fallback_chain"] = [
            name
            for name in getattr(self, "_fallback_chain", [])
            if name in _known_fallback_providers
        ]

        # セッション限定 APIキーの同期（D-04/D-06・V171-KEY-01/04）
        # llm_settings dict には絶対に入れない（成功基準1・T-05-12）。
        for provider_key, var in (
            ("claude", self.claude_api_key_var),
            ("gemini", self.gemini_api_key_var),
            ("runpod", self.runpod_api_key_var),
        ):
            key = var.get().strip()
            if key:
                self._session_api_keys[provider_key] = key
            else:
                self._session_api_keys.pop(provider_key, None)

        self.destroy()
        if self.on_apply:
            self.on_apply(llm_settings)
