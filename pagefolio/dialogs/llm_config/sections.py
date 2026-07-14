# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLMConfigDialog の SectionsMixin（_build の UI セクション構築）"""

import os
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE, C
from pagefolio.dialogs.llm_config.dialog import _EFFORT_VALUES
from pagefolio.ocr import MAX_OCR_MAX_TOKENS
from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider
from pagefolio.ocr_providers.registry import env_vars_for
from pagefolio.settings import load_prompt_file


def _configured_env_var(provider_name):
    """provider_name の環境変数が既に設定済みか判定し、表示用の変数名を返す。

    D-09 #4: env_vars_for() のタプル順（Gemini は GEMINI_API_KEY 優先→
    GOOGLE_API_KEY フォールバック）をそのまま「設定済み」判定・表示名決定に
    使う。戻り値は (設定済みか, 表示用変数名) のタプル。表示用変数名は
    タプル順で最初に設定済みのものを返し、いずれも未設定ならタプル先頭
    （呼び出し側は「設定済み」フラグが False のときこの値を使わない）。
    """
    env_vars = env_vars_for(provider_name)
    if not env_vars:
        return False, ""
    for var in env_vars:
        if os.environ.get(var):
            return True, var
    return False, env_vars[0]


class SectionsMixin:
    """_build の UI セクション構築を担う Mixin。"""

    def _build(self):
        # ボタン行を先に下部固定でパックし、スクロール領域が残りを使うようにする
        # （pack はパック順に空間を割り当てるため、この順序が重要・H-6）。
        self._btn_row = tk.Frame(self, bg=C["BG_DARK"])
        self._btn_row.pack(side="bottom", pady=(8, 14))

        body = self._build_scrollable_area()
        self._body = body

        tk.Label(
            body,
            text=self._L["llm_config_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        # ── プロバイダ選択（off / lmstudio / claude）──
        provider_row = tk.Frame(body, bg=C["BG_DARK"])
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
            body,
            text=self._L["llm_config_provider_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        )
        self._provider_section_heading.pack(anchor="w", padx=24, pady=(6, 2))

        # ── LM Studio 固有欄（lmstudio 選択時のみ表示）──
        self.url_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
        self.ollama_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
        self.runpod_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
        # H-7: 表示切替ボタンを先に右詰めでパックして必要幅を確保し、
        # 幅が足りない場合は Entry 側（expand）が縮むようにする。
        runpod_key_toggle_btn.pack(side="right", padx=(2, 0))
        self.runpod_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)

        runpod_note = self._L["llm_key_session_note"]
        _runpod_env_set, _runpod_env_var = _configured_env_var("runpod")
        if _runpod_env_set:
            runpod_note += " " + self._L["llm_key_env_set_note"].format(
                env_var=_runpod_env_var
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
        self.claude_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
        # H-7: 表示切替ボタンを先に右詰めでパックして必要幅を確保し、
        # 幅が足りない場合は Entry 側（expand）が縮むようにする。
        claude_key_toggle_btn.pack(side="right", padx=(2, 0))
        self.claude_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)

        claude_note = self._L["llm_key_session_note"]
        _claude_env_set, _claude_env_var = _configured_env_var("claude")
        if _claude_env_set:
            claude_note += " " + self._L["llm_key_env_set_note"].format(
                env_var=_claude_env_var
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
        self.gemini_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
        # H-7: 表示切替ボタンを先に右詰めでパックして必要幅を確保し、
        # 幅が足りない場合は Entry 側（expand）が縮むようにする。
        gemini_key_toggle_btn.pack(side="right", padx=(2, 0))
        self.gemini_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)

        gemini_note = self._L["llm_key_session_note"]
        _gemini_env_set, _gemini_env_var = _configured_env_var("gemini")
        if _gemini_env_set:
            gemini_note += " " + self._L["llm_key_env_set_note"].format(
                env_var=_gemini_env_var
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
        self.tesseract_section_frame = tk.Frame(body, bg=C["BG_DARK"])

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
            body,
            text=self._L["llm_config_common_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        )

        # ── effort 欄（claude かつ effort 対応モデル時のみ表示）──
        self.effort_frame = tk.Frame(body, bg=C["BG_DARK"])
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
        self.temperature_frame = tk.Frame(body, bg=C["BG_DARK"])
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
        self.scale_row = tk.Frame(body, bg=C["BG_DARK"])
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
            body,
            text=self._L["ocr_scale_tradeoff_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=24)

        # ── タイムアウト ──
        to_row = tk.Frame(body, bg=C["BG_DARK"])
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
        mt_row = tk.Frame(body, bg=C["BG_DARK"])
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
        prompt_row = tk.Frame(body, bg=C["BG_DARK"])
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
        # 初期値の挿入。外部 md ファイル（exe と同階層）が存在すればその内容を
        # 入力欄へ反映する（ファイル連動モード・V174-2。無ければ設定値）
        default_prompt = load_prompt_file(CUSTOM_PROMPT_FILE) or (
            self.current_settings.get("ocr_custom_prompt", "")
        )
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

        # V174-2: 外部 md ファイル（exe と同階層）検出時の注記。
        # ファイル連動モード（開いたとき入力欄へ反映・適用時に書き戻し）で
        # あることをユーザーへ明示する
        self._add_prompt_file_notice(body, CUSTOM_PROMPT_FILE)

        # ── サマリプロンプト（全ページ統合サマリ生成用）──
        summary_row = tk.Frame(body, bg=C["BG_DARK"])
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
        # 初期値の挿入（カスタムプロンプト側と同型のファイル連動・V174-2）
        default_summary_prompt = load_prompt_file(SUMMARY_PROMPT_FILE) or (
            self.current_settings.get("ocr_summary_prompt", "")
        )
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

        # V174-2: 外部 md ファイル検出時の注記（カスタムプロンプト側と同型）
        self._add_prompt_file_notice(body, SUMMARY_PROMPT_FILE)

        # ── 並列度（concurrency）──
        conc_row = tk.Frame(body, bg=C["BG_DARK"])
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
            body,
            textvariable=self.lm_status_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        )
        self.lm_status_label.pack(anchor="w", padx=24, pady=(2, 4))

        # ── 操作ボタン（self._btn_row は _build_scrollable_area 前に確保済み）──
        ttk.Button(
            self._btn_row,
            text=self._L["llm_config_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(
            self._btn_row, text=self._L["llm_config_cancel"], command=self.destroy
        ).pack(side="left", padx=8)

        # 初期表示：選択中プロバイダに応じて欄を切替
        self._on_provider_change()
