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
from pagefolio.ocr_providers import (
    ClaudeProvider,
    GeminiProvider,
    LMStudioProvider,
    _detect_tesseract,
)
from pagefolio.settings import get_current_font_size

logger = logging.getLogger(__name__)

# effort 値の許可リスト（D-17）
_EFFORT_VALUES = ("low", "medium", "high", "xhigh", "max")


# ══════════════════════════════════════════
#  LLM 設定ダイアログ（OCR と設定で共有）
# ══════════════════════════════════════════
class LLMConfigDialog(tk.Toplevel):
    """プロバイダ選択・欄切替・モデル更新・effort 切替を行う共通ダイアログ。

    対応プロバイダ（off/lmstudio/claude/gemini）:
    プロバイダ選択:
      - off: OCR を無効化（OCR ボタンは disabled になる）
      - lmstudio: LM Studio URL・モデル欄を表示
      - claude: claude モデル欄・effort/temperature 欄を表示
      - gemini: gemini モデル欄・temperature 欄を表示（D-09・effort 非対応）

    # Phase 7: tesseract を追加予定
    """

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
        self.resizable(False, False)
        self.grab_set()

        self.current_settings = dict(current_settings)
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
        # Tesseract 未インストール時の選択リセット用（D-02）
        self._last_valid_provider = current_settings.get("ocr_provider", "off")
        # D-05/Pitfall 2: ocr_providers.py と同じ _detect_tesseract() を都度呼び、
        # ダイアログを開く度に再評価する（再起動なしで言語パック追加を反映）。
        self._tesseract_available, self._tesseract_langs = _detect_tesseract()

        # _dialog_w は _build() 内の _resize_to_fit() が参照するため、_build() より
        # 前に確定させておく（未設定だと AttributeError でダイアログが開けない）。
        try:
            fs = int(self._font(0)[1])
        except Exception:
            fs = get_current_font_size()
        self._dialog_w = max(540, int(fs * 44))

        self._build()
        self.update_idletasks()
        h = max(480, self.winfo_reqheight() + 20)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{self._dialog_w}x{h}+{px - self._dialog_w // 2}+{py - h // 2}")

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
        # プロバイダ一覧を動的構築（D-08）: 基本 + tesseract + プラグイン登録
        _base_providers = [
            "off",
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
        ]
        _plugin_extras = (
            self._plugin_manager.list_ocr_providers() if self._plugin_manager else []
        )
        self.provider_combo = ttk.Combobox(
            provider_row,
            textvariable=self.provider_var,
            values=_base_providers + _plugin_extras,
            state="readonly",
            font=self._font(-1),
            width=14,
        )
        self.provider_combo.pack(side="left", padx=4)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)
        # Tesseract 未インストール時の案内ラベル（D-02）
        if not self._tesseract_available:
            tk.Label(
                provider_row,
                text=self._L.get(
                    "tesseract_not_installed_hint",
                    "Tesseract is not installed.",
                ),
                bg=C["BG_DARK"],
                fg=C["TEXT_SUB"],
                font=self._font(-2),
            ).pack(side="left", padx=(8, 0))

        # ── 固有設定見出し（D-15: 選択中プロバイダ固有の設定）──
        # 常時表示・非トグル。以下の各プロバイダ固有セクションフレームは
        # before=self.scale_row でこの見出しの後ろへ挿入される（_on_provider_change）。
        self._provider_section_heading = tk.Label(
            self,
            text=self._L["llm_config_provider_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        )
        self._provider_section_heading.pack(anchor="w", padx=24, pady=(6, 2))

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

        # ── Ollama 固有欄（ollama 選択時のみ表示）──
        self.ollama_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # URL
        ollama_url_row = tk.Frame(self.ollama_section_frame, bg=C["BG_DARK"])
        ollama_url_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            ollama_url_row,
            text=self._L["settings_ollama_url"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ollama_url_var = tk.StringVar(
            value=self.current_settings.get("ollama_url", "http://localhost:11434"),
        )
        tk.Entry(
            ollama_url_row,
            textvariable=self.ollama_url_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=4)

        # Ollama モデル
        ollama_model_row = tk.Frame(self.ollama_section_frame, bg=C["BG_DARK"])
        ollama_model_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            ollama_model_row,
            text=self._L["settings_ollama_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ollama_model_var = tk.StringVar(
            value=self.current_settings.get("ollama_model", ""),
        )
        self.ollama_model_combo = ttk.Combobox(
            ollama_model_row,
            textvariable=self.ollama_model_var,
            font=self._font(-1),
            values=[],
        )
        self.ollama_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(
            self.ollama_section_frame,
            text=self._L["settings_ollama_model_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w")

        # Ollama 接続テスト・モデル取得ボタン
        ollama_btn_row = tk.Frame(self.ollama_section_frame, bg=C["BG_DARK"])
        ollama_btn_row.pack(fill="x", padx=0, pady=(6, 2))
        ttk.Button(
            ollama_btn_row,
            text=self._L["settings_lm_fetch_models"],
            command=self._fetch_ollama_models,
        ).pack(side="left", padx=2)
        ttk.Button(
            ollama_btn_row,
            text=self._L["settings_lm_test"],
            command=self._test_ollama_connection,
        ).pack(side="left", padx=2)

        # ── RunPod 固有欄（runpod 選択時のみ表示）──
        self.runpod_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # URL
        runpod_url_row = tk.Frame(self.runpod_section_frame, bg=C["BG_DARK"])
        runpod_url_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            runpod_url_row,
            text=self._L["settings_runpod_url"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.runpod_url_var = tk.StringVar(
            value=self.current_settings.get("runpod_url", ""),
        )
        tk.Entry(
            runpod_url_row,
            textvariable=self.runpod_url_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=4)

        # RunPod モデル
        runpod_model_row = tk.Frame(self.runpod_section_frame, bg=C["BG_DARK"])
        runpod_model_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            runpod_model_row,
            text=self._L["settings_runpod_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.runpod_model_var = tk.StringVar(
            value=self.current_settings.get("runpod_model", ""),
        )
        self.runpod_model_combo = ttk.Combobox(
            runpod_model_row,
            textvariable=self.runpod_model_var,
            font=self._font(-1),
            values=[],
        )
        self.runpod_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(
            self.runpod_section_frame,
            text=self._L["settings_runpod_model_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w")

        # RunPod APIキー入力欄（D-01/D-02/D-03・V171-KEY-01/04）
        runpod_key_row = tk.Frame(self.runpod_section_frame, bg=C["BG_DARK"])
        runpod_key_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            runpod_key_row,
            text=self._L["llm_api_key_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.runpod_api_key_var = tk.StringVar(
            value=self._session_api_keys.get("runpod", ""),
        )
        self.runpod_api_key_entry = tk.Entry(
            runpod_key_row,
            show="*",
            textvariable=self.runpod_api_key_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        )
        self.runpod_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)
        self._runpod_key_shown = False

        def _toggle_runpod_key():
            self._runpod_key_shown = not self._runpod_key_shown
            self.runpod_api_key_entry.configure(
                show="" if self._runpod_key_shown else "*"
            )
            runpod_key_toggle_btn.configure(
                text=self._L["llm_key_toggle_hide"]
                if self._runpod_key_shown
                else self._L["llm_key_toggle_show"]
            )

        runpod_key_toggle_btn = ttk.Button(
            runpod_key_row,
            text=self._L["llm_key_toggle_show"],
            width=4,
            command=_toggle_runpod_key,
        )
        runpod_key_toggle_btn.pack(side="left", padx=(2, 0))

        runpod_note = self._L["llm_key_session_note"]
        if os.environ.get("RUNPOD_API_KEY"):
            runpod_note += " " + self._L["llm_key_env_set_note"].format(
                env_var="RUNPOD_API_KEY"
            )
        tk.Label(
            self.runpod_section_frame,
            text=runpod_note,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))

        # RunPod モデル更新ボタン
        runpod_btn_row = tk.Frame(self.runpod_section_frame, bg=C["BG_DARK"])
        runpod_btn_row.pack(fill="x", padx=0, pady=(4, 2))
        ttk.Button(
            runpod_btn_row,
            text=self._L["ocr_model_refresh"],
            command=self._refresh_runpod_models,
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

        # Claude APIキー入力欄（D-01/D-02/D-03・V171-KEY-01）
        claude_key_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
        claude_key_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            claude_key_row,
            text=self._L["llm_api_key_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.claude_api_key_var = tk.StringVar(
            value=self._session_api_keys.get("claude", ""),
        )
        self.claude_api_key_entry = tk.Entry(
            claude_key_row,
            show="*",
            textvariable=self.claude_api_key_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        )
        self.claude_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)
        self._claude_key_shown = False

        def _toggle_claude_key():
            self._claude_key_shown = not self._claude_key_shown
            self.claude_api_key_entry.configure(
                show="" if self._claude_key_shown else "*"
            )
            claude_key_toggle_btn.configure(
                text=self._L["llm_key_toggle_hide"]
                if self._claude_key_shown
                else self._L["llm_key_toggle_show"]
            )

        claude_key_toggle_btn = ttk.Button(
            claude_key_row,
            text=self._L["llm_key_toggle_show"],
            width=4,
            command=_toggle_claude_key,
        )
        claude_key_toggle_btn.pack(side="left", padx=(2, 0))

        claude_note = self._L["llm_key_session_note"]
        if os.environ.get("ANTHROPIC_API_KEY"):
            claude_note += " " + self._L["llm_key_env_set_note"].format(
                env_var="ANTHROPIC_API_KEY"
            )
        tk.Label(
            self.claude_section_frame,
            text=claude_note,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))

        # claude モデル更新ボタン
        claude_btn_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
        claude_btn_row.pack(fill="x", padx=0, pady=(4, 2))
        ttk.Button(
            claude_btn_row,
            text=self._L["ocr_model_refresh"],
            command=self._refresh_claude_models,
        ).pack(side="left", padx=2)

        # ── Gemini 固有欄（gemini 選択時のみ表示）──
        self.gemini_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # gemini モデル選択
        gemini_model_row = tk.Frame(self.gemini_section_frame, bg=C["BG_DARK"])
        gemini_model_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            gemini_model_row,
            text=self._L["settings_lm_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.gemini_model_var = tk.StringVar(
            value=self.current_settings.get("gemini_model", "gemini-2.5-flash"),
        )
        self.gemini_model_combo = ttk.Combobox(
            gemini_model_row,
            textvariable=self.gemini_model_var,
            font=self._font(-1),
            values=GeminiProvider.RECOMMENDED_MODELS,
        )
        self.gemini_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        # Gemini APIキー入力欄（D-01/D-02/D-03・V171-KEY-01）
        gemini_key_row = tk.Frame(self.gemini_section_frame, bg=C["BG_DARK"])
        gemini_key_row.pack(fill="x", padx=0, pady=2)
        tk.Label(
            gemini_key_row,
            text=self._L["llm_api_key_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.gemini_api_key_var = tk.StringVar(
            value=self._session_api_keys.get("gemini", ""),
        )
        self.gemini_api_key_entry = tk.Entry(
            gemini_key_row,
            show="*",
            textvariable=self.gemini_api_key_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        )
        self.gemini_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)
        self._gemini_key_shown = False

        def _toggle_gemini_key():
            self._gemini_key_shown = not self._gemini_key_shown
            self.gemini_api_key_entry.configure(
                show="" if self._gemini_key_shown else "*"
            )
            gemini_key_toggle_btn.configure(
                text=self._L["llm_key_toggle_hide"]
                if self._gemini_key_shown
                else self._L["llm_key_toggle_show"]
            )

        gemini_key_toggle_btn = ttk.Button(
            gemini_key_row,
            text=self._L["llm_key_toggle_show"],
            width=4,
            command=_toggle_gemini_key,
        )
        gemini_key_toggle_btn.pack(side="left", padx=(2, 0))

        gemini_note = self._L["llm_key_session_note"]
        gemini_env_var = (
            "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_API_KEY"
        )
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            gemini_note += " " + self._L["llm_key_env_set_note"].format(
                env_var=gemini_env_var
            )
        tk.Label(
            self.gemini_section_frame,
            text=gemini_note,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))

        # gemini モデル更新ボタン
        gemini_btn_row = tk.Frame(self.gemini_section_frame, bg=C["BG_DARK"])
        gemini_btn_row.pack(fill="x", padx=0, pady=(4, 2))
        ttk.Button(
            gemini_btn_row,
            text=self._L["ocr_model_refresh"],
            command=self._refresh_gemini_models,
        ).pack(side="left", padx=2)

        # ── Tesseract 固有欄（tesseract 選択時のみ表示）──
        self.tesseract_section_frame = tk.Frame(self, bg=C["BG_DARK"])

        # 精度劣後注記（D-03: 常設ラベル・WARNING 色）
        tk.Label(
            self.tesseract_section_frame,
            text=self._L.get(
                "tesseract_accuracy_warning",
                "Note: Tesseract accuracy is lower than LLM-based providers.",
            ),
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(4, 2))

        # 言語フォールバック案内（jpn 未インストール時のみ表示）
        if "jpn" not in self._tesseract_langs:
            tk.Label(
                self.tesseract_section_frame,
                text=self._L.get(
                    "tesseract_lang_fallback",
                    "jpn language pack not found. Running with eng only.",
                ),
                bg=C["BG_DARK"],
                fg=C["TEXT_SUB"],
                font=self._font(-2),
            ).pack(anchor="w", pady=(0, 2))

        # ── 共通設定見出し（D-15: 全プロバイダ共通の設定）──
        # 未パック状態で生成し、_on_provider_change 内で before=self.scale_row
        # を使って毎回「固有設定エリアの直後・共通パラメータ群の先頭」へ再配置する
        # （プロバイダ固有フレームと同じ挿入先アンカーのため call 順で位置決めする）。
        self._common_section_heading = tk.Label(
            self,
            text=self._L["llm_config_common_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        )

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
        # H-4: self 属性として保持しプロバイダ別セクションのアンカーに使用
        self.scale_row = tk.Frame(self, bg=C["BG_DARK"])
        self.scale_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(
            self.scale_row,
            text=self._L["settings_ocr_scale"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        # WR-01: D-11 整合（フォールバック 2.0→1.5）
        self.ocr_scale_var = tk.DoubleVar(
            value=float(self.current_settings.get("ocr_scale", 1.5)),
        )
        tk.Spinbox(
            self.scale_row,
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

        # ocr_scale トレードオフ常設ヒント（D-12・テーマ色 C["TEXT_SUB"] 使用）
        tk.Label(
            self,
            text=self._L["ocr_scale_tradeoff_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=24)

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
            to=900,
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

        # ── カスタムプロンプト ──
        prompt_row = tk.Frame(self, bg=C["BG_DARK"])
        prompt_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            prompt_row,
            text=self._L.get("ocr_custom_prompt_label", "カスタムプロンプト:"),
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="nw",
        ).pack(side="left")
        self.ocr_prompt_text = tk.Text(
            prompt_row,
            width=30,
            height=3,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            wrap="word",
        )
        self.ocr_prompt_text.pack(side="left", fill="x", expand=True, padx=4)
        # 初期値の挿入
        default_prompt = self.current_settings.get("ocr_custom_prompt", "")
        if default_prompt:
            self.ocr_prompt_text.insert("1.0", default_prompt)
        tk.Label(
            prompt_row,
            text=self._L.get(
                "ocr_custom_prompt_hint", "(空欄でデフォルトのプロンプトを使用)"
            ),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=4, anchor="sw")

        # ── サマリプロンプト（全ページ統合サマリ生成用）──
        summary_row = tk.Frame(self, bg=C["BG_DARK"])
        summary_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            summary_row,
            text=self._L.get("ocr_summary_prompt_label", "サマリプロンプト:"),
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="nw",
        ).pack(side="left")
        self.ocr_summary_prompt_text = tk.Text(
            summary_row,
            width=30,
            height=3,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            wrap="word",
        )
        self.ocr_summary_prompt_text.pack(side="left", fill="x", expand=True, padx=4)
        # 初期値の挿入
        default_summary_prompt = self.current_settings.get("ocr_summary_prompt", "")
        if default_summary_prompt:
            self.ocr_summary_prompt_text.insert("1.0", default_summary_prompt)
        tk.Label(
            summary_row,
            text=self._L.get(
                "ocr_summary_prompt_hint", "(空欄で既定のサマリ指示を使用)"
            ),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=4, anchor="sw")

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
            h = max(480, self.winfo_reqheight() + 20)
            x = self.winfo_x()
            y = self.winfo_y()
            self.geometry(f"{self._dialog_w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

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

    # ── RunPod モデル更新 ───────────────────────────────
    def _refresh_runpod_models(self):
        """RunPod モデル一覧を取得して Combobox に反映する。

        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        """
        self._set_lm_status(self._L["llm_fetching_runpod_models"], kind="info")
        api_key = self.runpod_api_key_var.get().strip() or os.environ.get(
            "RUNPOD_API_KEY", ""
        )
        url = self.runpod_url_var.get().strip()
        if not api_key:
            self._set_lm_status(
                self._L["llm_env_key_unset_static_runpod"],
                kind="info",
            )
            return
        try:
            from pagefolio.ocr_providers import RunPodProvider

            models = RunPodProvider(api_key=api_key, url=url, model="").list_models()
        except Exception as e:
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="RunPod", e=e)
            )
            self._set_lm_status(
                str(e),
                kind="fail",
            )
            return
        self.runpod_model_combo["values"] = models
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    # ── Claude モデル更新 ───────────────────────────────
    def _refresh_claude_models(self):
        """Claude モデル一覧を取得して Combobox に反映する。

        ANTHROPIC_API_KEY が未設定でも ClaudeProvider.list_models が
        RECOMMENDED_MODELS を返すので静的リストが常に表示される（D-08）。
        api_key は settings に書かない（D-01/D-05）。
        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        """
        self._set_lm_status(self._L["llm_fetching_claude_models"], kind="info")
        api_key = self.claude_api_key_var.get().strip() or os.environ.get(
            "ANTHROPIC_API_KEY", ""
        )
        try:
            models = ClaudeProvider(api_key=api_key, model="").list_models()
        except Exception as e:
            # 例外時は静的推奨リストへフォールバック（D-08）
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="Claude", e=e)
            )
            models = ClaudeProvider.RECOMMENDED_MODELS
            self.claude_model_combo["values"] = models
            self._set_lm_status(
                self._L["llm_env_key_unset_static"],
                kind="info",
            )
            return
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

    # ── Gemini モデル更新 ───────────────────────────────
    def _refresh_gemini_models(self):
        """Gemini モデル一覧を取得して Combobox に反映する。

        GEMINI_API_KEY / GOOGLE_API_KEY が未設定でも GeminiProvider.list_models が
        RECOMMENDED_MODELS を返すので静的リストが常に表示される（D-08）。
        api_key は settings に書かない（D-01/D-05）。
        D-10: ダイアログ入力欄のライブ値（OK 前でも）を環境変数より優先する。
        """
        self._set_lm_status(self._L["llm_fetching_gemini_models"], kind="info")
        api_key = self.gemini_api_key_var.get().strip() or (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        )
        try:
            models = GeminiProvider(api_key=api_key, model="").list_models()
        except Exception as e:
            # 例外時は静的推奨リストへフォールバック（D-08）
            logger.warning(
                self._L["llm_model_fetch_failed"].format(provider="Gemini", e=e)
            )
            models = GeminiProvider.RECOMMENDED_MODELS
            self.gemini_model_combo["values"] = models
            self._set_lm_status(
                self._L["llm_env_key_unset_static_gemini"],
                kind="info",
            )
            return
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
