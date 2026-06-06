# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLM 設定ダイアログ（OCR と設定で共有）"""

import logging
import os
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import LANG, C
from pagefolio.ocr import MAX_OCR_MAX_TOKENS
from pagefolio.ocr_providers import ClaudeProvider, LMStudioProvider
from pagefolio.settings import get_current_font_size

logger = logging.getLogger(__name__)

# effort 値の許可リスト（D-17）
_EFFORT_VALUES = ("low", "medium", "high", "xhigh", "max")


# ══════════════════════════════════════════
#  LLM 設定ダイアログ（OCR と設定で共有）
# ══════════════════════════════════════════
class LLMConfigDialog(tk.Toplevel):
    """プロバイダ選択・欄切替・モデル更新・effort 切替を行う共通ダイアログ。

    対応プロバイダ（off/lmstudio/claude）:
    プロバイダ選択:
      - off: OCR を無効化（OCR ボタンは disabled になる）
      - lmstudio: LM Studio URL・モデル欄を表示
      - claude: claude モデル欄・effort/temperature 欄を表示

    # Phase 6: gemini / Phase 7: tesseract を追加予定
    """

    def __init__(
        self,
        parent,
        current_settings,
        on_apply,
        font_func=None,
        lang="ja",
    ):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["llm_config_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.current_settings = dict(current_settings)
        self.on_apply = on_apply
        self._font = font_func or (
            lambda d=0, w=None: (
                ("Segoe UI", max(7, 10 + d), w) if w else ("Segoe UI", max(7, 10 + d))
            )
        )

        self._build()
        self.update_idletasks()
        try:
            fs = int(self._font(0)[1])
        except Exception:
            fs = get_current_font_size()
        w = max(540, int(fs * 44))
        h = max(480, self.winfo_reqheight() + 20)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text=self._L["llm_config_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        # ── プロバイダ選択（off / lmstudio / claude）──
        provider_row = tk.Frame(self, bg=C["BG_DARK"])
        provider_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            provider_row,
            text=self._L["ocr_provider_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.provider_var = tk.StringVar(
            value=self.current_settings.get("ocr_provider", "off"),
        )
        self.provider_combo = ttk.Combobox(
            provider_row,
            textvariable=self.provider_var,
            # Phase 6: gemini / Phase 7: tesseract を追加予定
            values=["off", "lmstudio", "claude"],
            state="readonly",
            font=self._font(-1),
            width=14,
        )
        self.provider_combo.pack(side="left", padx=4)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # ── LM Studio 固有欄（lmstudio 選択時のみ表示）──
        self.url_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # URL
        url_row = tk.Frame(self.url_section_frame, bg=C["BG_DARK"])
        url_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            url_row,
            text=self._L["settings_lm_url"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.lm_url_var = tk.StringVar(
            value=self.current_settings.get("lm_studio_url", "http://localhost:1234"),
        )
        tk.Entry(
            url_row,
            textvariable=self.lm_url_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=4)

        # LM Studio モデル
        lm_model_row = tk.Frame(self.url_section_frame, bg=C["BG_DARK"])
        lm_model_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            lm_model_row,
            text=self._L["settings_lm_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.lm_model_var = tk.StringVar(
            value=self.current_settings.get("lm_studio_model", ""),
        )
        self.lm_model_combo = ttk.Combobox(
            lm_model_row,
            textvariable=self.lm_model_var,
            font=self._font(-1),
            values=[],
        )
        self.lm_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(
            self.url_section_frame,
            text=self._L["settings_lm_model_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w")

        # LM Studio 接続テスト・モデル取得ボタン
        lm_btn_row = tk.Frame(self.url_section_frame, bg=C["BG_DARK"])
        lm_btn_row.pack(fill="x", padx=0, pady=(6, 2))
        ttk.Button(
            lm_btn_row,
            text=self._L["settings_lm_fetch_models"],
            command=self._fetch_models,
        ).pack(side="left", padx=2)
        ttk.Button(
            lm_btn_row,
            text=self._L["settings_lm_test"],
            command=self._test_connection,
        ).pack(side="left", padx=2)

        # ── Claude 固有欄（claude 選択時のみ表示）──
        self.claude_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # claude モデル選択
        claude_model_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
        claude_model_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            claude_model_row,
            text=self._L["settings_lm_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.claude_model_var = tk.StringVar(
            value=self.current_settings.get("claude_model", "claude-sonnet-4-6"),
        )
        self.claude_model_combo = ttk.Combobox(
            claude_model_row,
            textvariable=self.claude_model_var,
            font=self._font(-1),
            values=ClaudeProvider.RECOMMENDED_MODELS,
        )
        self.claude_model_combo.pack(side="left", fill="x", expand=True, padx=4)
        self.claude_model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

        # claude モデル更新ボタン
        claude_btn_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
        claude_btn_row.pack(fill="x", padx=0, pady=(4, 2))
        ttk.Button(
            claude_btn_row,
            text=self._L["ocr_model_refresh"],
            command=self._refresh_claude_models,
        ).pack(side="left", padx=2)

        # ── effort 欄（claude かつ effort 対応モデル時のみ表示）──
        self.effort_frame = tk.Frame(self, bg=C["BG_DARK"])
        effort_row = tk.Frame(self.effort_frame, bg=C["BG_DARK"])
        effort_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            effort_row,
            text=self._L["ocr_effort_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.effort_var = tk.StringVar(
            value=self.current_settings.get("ocr_effort", "low"),
        )
        ttk.Combobox(
            effort_row,
            textvariable=self.effort_var,
            values=list(_EFFORT_VALUES),
            state="readonly",
            font=self._font(-1),
            width=10,
        ).pack(side="left", padx=4)

        # ── temperature 欄（off/lmstudio または haiku 系モデル時に表示）──
        self.temperature_frame = tk.Frame(self, bg=C["BG_DARK"])
        tmp_row = tk.Frame(self.temperature_frame, bg=C["BG_DARK"])
        tmp_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            tmp_row,
            text=self._L["ocr_temperature_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_temperature_var = tk.DoubleVar(
            value=float(self.current_settings.get("ocr_temperature", 0.1)),
        )
        tk.Spinbox(
            tmp_row,
            from_=0.0,
            to=2.0,
            increment=0.1,
            textvariable=self.ocr_temperature_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)
        tk.Label(
            tmp_row,
            text=self._L["ocr_temperature_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=4)

        # ── 解像度倍率 ──
        scale_row = tk.Frame(self, bg=C["BG_DARK"])
        scale_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(
            scale_row,
            text=self._L["settings_ocr_scale"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_scale_var = tk.DoubleVar(
            value=float(self.current_settings.get("ocr_scale", 2.0)),
        )
        tk.Spinbox(
            scale_row,
            from_=1.0,
            to=4.0,
            increment=0.5,
            textvariable=self.ocr_scale_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)

        # ── タイムアウト ──
        to_row = tk.Frame(self, bg=C["BG_DARK"])
        to_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            to_row,
            text=self._L["settings_ocr_timeout"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_timeout_var = tk.IntVar(
            value=int(self.current_settings.get("ocr_timeout", 120)),
        )
        tk.Spinbox(
            to_row,
            from_=10,
            to=600,
            increment=10,
            textvariable=self.ocr_timeout_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)

        # ── 最大トークン ──
        mt_row = tk.Frame(self, bg=C["BG_DARK"])
        mt_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            mt_row,
            text=self._L["ocr_max_tokens_short"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_max_tokens_var = tk.IntVar(
            value=int(self.current_settings.get("ocr_max_tokens", -1)),
        )
        tk.Spinbox(
            mt_row,
            from_=-1,
            to=MAX_OCR_MAX_TOKENS,
            increment=1024,
            textvariable=self.ocr_max_tokens_var,
            width=8,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)
        tk.Label(
            mt_row,
            text=self._L["ocr_max_tokens_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=4)

        # ── 並列度（concurrency）──
        conc_row = tk.Frame(self, bg=C["BG_DARK"])
        conc_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            conc_row,
            text=self._L["settings_ocr_concurrency"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_concurrency_var = tk.IntVar(
            value=int(self.current_settings.get("ocr_concurrency", 2)),
        )
        tk.Spinbox(
            conc_row,
            from_=1,
            to=8,
            increment=1,
            textvariable=self.ocr_concurrency_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)
        tk.Label(
            conc_row,
            text=self._L["settings_ocr_concurrency_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=4)

        # ── ステータスラベル ──
        self.lm_status_var = tk.StringVar(value="")
        self.lm_status_label = tk.Label(
            self,
            textvariable=self.lm_status_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        )
        self.lm_status_label.pack(anchor="w", padx=24, pady=(2, 4))

        # ── 操作ボタン ──
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["llm_config_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(
            btn_row, text=self._L["llm_config_cancel"], command=self.destroy
        ).pack(side="left", padx=8)

        # 初期表示：選択中プロバイダに応じて欄を切替
        self._on_provider_change()

    # ── プロバイダ変更ハンドラ ──────────────────────────
    def _on_provider_change(self, _event=None):
        """プロバイダ選択に応じて下位欄を pack/pack_forget で切替。"""
        provider = self.provider_var.get()

        # LM Studio 固有欄
        if provider == "lmstudio":
            self.url_section_frame.pack(fill="x", padx=24, pady=(4, 2))
        else:
            self.url_section_frame.pack_forget()

        # Claude 固有欄
        if provider == "claude":
            self.claude_section_frame.pack(fill="x", padx=24, pady=(4, 2))
            # モデルに応じて effort/temperature を切替
            self._on_model_change()
        else:
            self.claude_section_frame.pack_forget()
            # lmstudio / off では temperature 欄を表示し effort 欄を隠す（従来挙動）
            self.effort_frame.pack_forget()
            self.temperature_frame.pack(fill="x", padx=24, pady=2)

    # ── モデル変更ハンドラ（effort/temperature 切替）──────
    def _on_model_change(self, _event=None):
        """claude モデル変更時に effort/temperature 欄を切替。

        effort 対応モデル（sonnet/opus 系）のとき effort 欄を表示し
        temperature 欄を隠す（D-17）。haiku 系は temperature 欄を表示。
        """
        model = self.claude_model_var.get()
        if self._model_supports_effort(model):
            self.effort_frame.pack(fill="x", padx=24, pady=2)
            self.temperature_frame.pack_forget()
        else:
            self.temperature_frame.pack(fill="x", padx=24, pady=2)
            self.effort_frame.pack_forget()

    # ── effort 対応判定 ────────────────────────────────
    def _model_supports_effort(self, model):
        """モデルが effort パラメータ（output_config）に対応しているか判定する。

        ClaudeProvider.EFFORT_MODELS 集合 + プレフィックス判定を流用（D-16/D-17）。

        戻り値: haiku 系は False、sonnet/opus 系は True。
        """
        if not model:
            return False
        if "haiku" in model:
            return False
        if model in ClaudeProvider.EFFORT_MODELS:
            return True
        # 前方互換：明示リストにないモデルはプレフィックスで判定
        has_opus_or_sonnet = "opus" in model or "sonnet" in model
        return has_opus_or_sonnet and "haiku" not in model

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

    # ── LM Studio モデル取得 ────────────────────────────
    def _fetch_models(self):
        """LM Studio からモデル一覧を取得して Combobox に反映する。"""
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
        self.lm_model_combo["values"] = models
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    def _test_connection(self):
        """LM Studio への接続をテストする。"""
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
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    # ── Claude モデル更新 ───────────────────────────────
    def _refresh_claude_models(self):
        """Claude モデル一覧を取得して Combobox に反映する。

        ANTHROPIC_API_KEY が未設定でも ClaudeProvider.list_models が
        RECOMMENDED_MODELS を返すので静的リストが常に表示される（D-08）。
        api_key は os.environ 読み取りのみ。settings には書かない（D-01/D-05）。
        """
        self._set_lm_status("⏳ Claude モデル一覧を取得中…", kind="info")
        # api_key は環境変数からのみ読み取る（settings への書き込み禁止・D-01/D-05）
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        try:
            models = ClaudeProvider(api_key=api_key, model="").list_models()
        except (ConnectionError, TimeoutError, RuntimeError, Exception) as e:
            # 例外時は静的推奨リストへフォールバック（D-08）
            logger.warning("Claude モデル取得失敗（静的リストへフォールバック）: %s", e)
            models = ClaudeProvider.RECOMMENDED_MODELS
            self.claude_model_combo["values"] = models
            self._set_lm_status(
                "環境変数 ANTHROPIC_API_KEY が未設定のため静的リストを表示中",
                kind="info",
            )
            return
        self.claude_model_combo["values"] = models
        if not api_key:
            self._set_lm_status(
                "環境変数 ANTHROPIC_API_KEY が未設定のため静的リストを表示中",
                kind="info",
            )
        else:
            self._set_lm_status(
                self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
            )

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

        # Claude 設定（claude_model・ocr_effort は api_key と異なり無害な設定値）
        llm_settings["claude_model"] = (
            self.claude_model_var.get().strip() or "claude-sonnet-4-6"
        )
        raw_effort = self.effort_var.get()
        llm_settings["ocr_effort"] = (
            raw_effort if raw_effort in _EFFORT_VALUES else "low"
        )

        # 共通数値設定（クランプして格納）
        try:
            llm_settings["ocr_scale"] = max(
                1.0, min(4.0, float(self.ocr_scale_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_scale"] = 2.0
        try:
            llm_settings["ocr_timeout"] = max(
                10, min(600, int(self.ocr_timeout_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_timeout"] = 120
        try:
            mt = int(self.ocr_max_tokens_var.get())
            llm_settings["ocr_max_tokens"] = max(-1, min(MAX_OCR_MAX_TOKENS, mt))
        except (tk.TclError, ValueError):
            llm_settings["ocr_max_tokens"] = -1
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

        self.destroy()
        if self.on_apply:
            self.on_apply(llm_settings)
