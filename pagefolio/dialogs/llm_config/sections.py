# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLMConfigDialog の SectionsMixin（_build の UI セクション構築）"""

import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE, C
from pagefolio.dialogs.llm_config.dialog import _EFFORT_VALUES
from pagefolio.ocr import MAX_OCR_MAX_TOKENS
from pagefolio.ocr_providers import ClaudeProvider, GeminiProvider
from pagefolio.ocr_providers.registry import env_vars_for
from pagefolio.settings import (
    delete_template,
    get_template,
    list_template_names,
    load_prompt_file,
    prompt_file_exists,
    rename_template,
    save_prompt_file,
    save_template,
    template_name_exists,
)


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
        # 02-REVIEW CR-01 修正: current_settings の生値ではなく dialog.py の
        # __init__ で Tesseract 可用性判定後に確定した self._initial_provider
        # を使う。こうしないと combobox が無効な "tesseract" のまま表示され、
        # _on_provider_change の自己参照フォールバックと組み合わさって初期
        # レイアウト構築（pack）が完了しなくなる（CR-01）。
        self.provider_var = tk.StringVar(
            value=self._initial_provider,
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

        # ── テンプレート管理（V180-TMPL-01〜05・D-01〜D-08）──
        # D-01: 1テンプレート = カスタムプロンプト + サマリプロンプトのペア保存。
        # combobox 1つで両方を同時に切り替える（provider_combo と同型パターン）。
        template_row = tk.Frame(body, bg=C["BG_DARK"])
        template_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(
            template_row,
            text=self._L["tmpl_section_title"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.template_var = tk.StringVar(
            value=self.current_settings.get("prompt_templates", {}).get("active", ""),
        )
        # D-01/D-05〜D-07: 現在アクティブなテンプレート名（切替時の比較・復帰・
        # 削除ボタン活性判定に使う）
        self._active_template_name = self.template_var.get()
        self.template_combo = ttk.Combobox(
            template_row,
            textvariable=self.template_var,
            values=list_template_names(self.current_settings),
            state="readonly",
            font=self._font(-1),
            width=14,
        )
        self.template_combo.pack(side="left", padx=4)
        self.template_combo.bind("<<ComboboxSelected>>", self._on_template_change)

        template_btn_row = tk.Frame(body, bg=C["BG_DARK"])
        template_btn_row.pack(fill="x", padx=24, pady=(0, 4))
        ttk.Button(
            template_btn_row,
            text=self._L["tmpl_save_btn"],
            command=self._on_template_save,
        ).pack(side="left", padx=2)
        # D-03: アクティブテンプレートの削除ボタンは無効化する（誤操作防止）
        self.template_delete_btn = ttk.Button(
            template_btn_row,
            text=self._L["tmpl_delete_btn"],
            command=self._on_template_delete,
        )
        self.template_delete_btn.pack(side="left", padx=2)
        ttk.Button(
            template_btn_row,
            text=self._L["tmpl_rename_btn"],
            command=self._on_template_rename,
        ).pack(side="left", padx=2)
        self._refresh_template_delete_state()

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

        # ── プロバイダーフォールバック（V180-FALL-01〜03・D-13〜D-16）──
        # D-16: 既定は「フォールバックなし（空リスト・トグルOFF）」の安全側既定。
        # トグルONで順序リスト（Listbox+上下ボタン+候補追加/除外）が現れる。
        fallback_row = tk.Frame(body, bg=C["BG_DARK"])
        fallback_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(
            fallback_row,
            text=self._L["fallback_section_title"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.fallback_enabled_var = tk.BooleanVar(
            value=bool(self.current_settings.get("ocr_fallback_enabled", False)),
        )
        ttk.Checkbutton(
            fallback_row,
            text=self._L["fallback_enable_toggle"],
            variable=self.fallback_enabled_var,
            command=self._on_fallback_toggle,
        ).pack(side="left", padx=4)

        # D-14: 候補一覧は全実行可能プロバイダ + プラグイン登録
        # （APIキー未設定のプロバイダも表示する）
        self._base_fallback_providers = [
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
        ]
        _fallback_plugin_extras = (
            self._plugin_manager.list_ocr_providers() if self._plugin_manager else []
        )
        self._fallback_known_providers = self._base_fallback_providers + list(
            _fallback_plugin_extras
        )
        # ホワイトリスト検証（Input Validation・ASVS L1）: 既知プロバイダ一覧に
        # 無い名前は読み込み時に除外する（T-02-07）
        _raw_fallback_chain = self.current_settings.get("ocr_fallback_chain", [])
        self._fallback_chain = [
            name
            for name in _raw_fallback_chain
            if name in self._fallback_known_providers
        ]

        self.fallback_list_frame = tk.Frame(body, bg=C["BG_DARK"])

        tk.Label(
            self.fallback_list_frame,
            text=self._L["fallback_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(0, 2))

        fallback_list_row = tk.Frame(self.fallback_list_frame, bg=C["BG_PANEL"], bd=0)
        fallback_list_row.pack(fill="x", pady=2)
        fallback_sb = ttk.Scrollbar(fallback_list_row, orient="vertical")
        self.fallback_listbox = tk.Listbox(
            fallback_list_row,
            yscrollcommand=fallback_sb.set,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            selectbackground=C["ACCENT"],
            selectforeground="#fff",
            font=self._font(-1),
            activestyle="none",
            bd=0,
            highlightthickness=0,
            height=4,
        )
        fallback_sb.configure(command=self.fallback_listbox.yview)
        fallback_sb.pack(side="right", fill="y")
        self.fallback_listbox.pack(side="left", fill="both", expand=True)

        fallback_btn_row = tk.Frame(self.fallback_list_frame, bg=C["BG_DARK"])
        fallback_btn_row.pack(fill="x", pady=(2, 2))
        self.fallback_up_btn = ttk.Button(
            fallback_btn_row,
            text=self._L["fallback_up_btn"],
            command=self._fallback_move_up,
        )
        self.fallback_up_btn.pack(side="left", padx=2)
        self.fallback_down_btn = ttk.Button(
            fallback_btn_row,
            text=self._L["fallback_down_btn"],
            command=self._fallback_move_down,
        )
        self.fallback_down_btn.pack(side="left", padx=2)

        # 候補追加/除外（D-14）
        fallback_add_row = tk.Frame(self.fallback_list_frame, bg=C["BG_DARK"])
        fallback_add_row.pack(fill="x", pady=(2, 4))
        self.fallback_candidate_var = tk.StringVar(
            value=self._fallback_known_providers[0]
            if self._fallback_known_providers
            else "",
        )
        self.fallback_candidate_combo = ttk.Combobox(
            fallback_add_row,
            textvariable=self.fallback_candidate_var,
            values=self._fallback_known_providers,
            state="readonly",
            font=self._font(-1),
            width=14,
        )
        self.fallback_candidate_combo.pack(side="left", padx=(0, 4))
        ttk.Button(
            fallback_add_row,
            text=self._L["fallback_add_btn"],
            command=self._fallback_add,
        ).pack(side="left", padx=2)
        ttk.Button(
            fallback_add_row,
            text=self._L["fallback_remove_btn"],
            command=self._fallback_remove,
        ).pack(side="left", padx=2)

        self._reload_fallback_list()
        # D-16: 初期表示はトグル状態に従う（既定 OFF のため通常は非表示）。
        # ここではまだ lm_status_label が未生成のため before= を使わず末尾へ
        # 積むだけでよい（この時点で以降に pack されるものはまだ無い）。
        if self.fallback_enabled_var.get():
            self.fallback_list_frame.pack(fill="x", padx=24, pady=(0, 4))

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

    # ── テンプレート管理ハンドラ（V180-TMPL-01〜05・D-01〜D-08）──────

    def _has_unsaved_template_changes(self, current_custom, current_summary):
        """テンプレート切替で入力欄の内容が失われる未保存差分があるか判定する。

        02-REVIEW WR-03 修正: 従来はファイル連動モード（ocr_custom_prompt.md/
        ocr_summary_prompt.md のいずれかが存在）かつアクティブテンプレートが
        既に選択済みのときのみ True を返し得た。しかし、ファイル非連動・かつ
        今セッションでまだテンプレートを選んでいない状態でも、ユーザーが
        入力欄へ直接テキストを打ち込んでいれば、テンプレート切替はその内容を
        無警告で破棄してしまう（データ損失パス）。

        アクティブテンプレート未選択の場合は「自由入力の未保存内容があるか」
        だけを見る（比較対象となる保存済みテンプレートが存在しないため）。
        アクティブテンプレートが選択済みの場合は、既存どおりファイル連動
        モード時のみ保存済み内容との差分を比較する。
        """
        if not self._active_template_name:
            return bool(current_custom.strip() or current_summary.strip())
        if not (
            prompt_file_exists(CUSTOM_PROMPT_FILE)
            or prompt_file_exists(SUMMARY_PROMPT_FILE)
        ):
            return False
        tpl = get_template(self.current_settings, self._active_template_name)
        if tpl is None:
            return False
        return current_custom != tpl.get(
            "custom_prompt", ""
        ) or current_summary != tpl.get("summary_prompt", "")

    def _refresh_template_delete_state(self):
        """削除ボタンの活性状態を更新する（D-03: アクティブテンプレートは無効化）。"""
        current = self.template_var.get()
        if current and current == self._active_template_name:
            self.template_delete_btn.state(["disabled"])
        else:
            self.template_delete_btn.state(["!disabled"])

    def _reload_template_combo(self, select_name=None):
        """テンプレート一覧を combobox の values へ反映する（V180-TMPL-02）。

        select_name が指定されていれば選択状態にする。削除ボタンの活性
        状態も併せて再評価する（D-03）。
        """
        names = list_template_names(self.current_settings)
        self.template_combo.configure(values=names)
        if select_name is not None:
            self.template_var.set(select_name)
        self._refresh_template_delete_state()

    def _on_template_change(self, _event=None):
        """テンプレート切替ハンドラ（D-05〜D-07）。

        1. 未保存差分の検知→確認（ファイル連動モードのみ・D-05）
        2. 選択テンプレートの内容を入力欄へ反映
        3. ファイル連動モードなら選択テンプレートの内容で外部ファイルを
           上書きし「アクティブテンプレートのライブ編集内容」の不変条件を
           保つ（D-07）
        """
        new_name = self.template_var.get()
        current_custom = self.ocr_prompt_text.get("1.0", "end").strip()
        current_summary = self.ocr_summary_prompt_text.get("1.0", "end").strip()
        if self._has_unsaved_template_changes(current_custom, current_summary):
            if not messagebox.askyesno(
                self._L["confirm_title"],
                self._L["tmpl_switch_discard_confirm"],
                parent=self,
            ):
                # D-05: キャンセルで切替を中止し、選択を元のアクティブ
                # テンプレートへ戻す
                self.template_var.set(self._active_template_name)
                return

        tpl = get_template(self.current_settings, new_name) if new_name else None
        custom_val = tpl.get("custom_prompt", "") if tpl else ""
        summary_val = tpl.get("summary_prompt", "") if tpl else ""
        self.ocr_prompt_text.delete("1.0", "end")
        if custom_val:
            self.ocr_prompt_text.insert("1.0", custom_val)
        self.ocr_summary_prompt_text.delete("1.0", "end")
        if summary_val:
            self.ocr_summary_prompt_text.insert("1.0", summary_val)

        # D-07: ファイル連動モードなら選択テンプレートの内容で外部ファイルを
        # 上書きする（外部ファイル＝常にアクティブテンプレートのライブ編集内容）
        if prompt_file_exists(CUSTOM_PROMPT_FILE):
            save_prompt_file(CUSTOM_PROMPT_FILE, custom_val)
        if prompt_file_exists(SUMMARY_PROMPT_FILE):
            save_prompt_file(SUMMARY_PROMPT_FILE, summary_val)

        self._active_template_name = new_name
        self.current_settings.setdefault(
            "prompt_templates", {"active": "", "items": {}}
        )
        self.current_settings["prompt_templates"]["active"] = new_name
        self._refresh_template_delete_state()

    def _on_template_save(self):
        """現在の入力欄内容を新規テンプレートとして保存する（D-01/D-04/D-06）。

        名前は askstring で入力させ、空名・重複名は ShortcutsDialog と同型の
        「showerror→return」パターンで拒否する（D-04）。ファイル連動モードの
        場合、開いた時点で外部ファイル内容が反映済みの入力欄内容をそのまま
        テンプレートへコピーする（D-06）。
        """
        name = simpledialog.askstring(
            self._L["tmpl_section_title"],
            self._L["tmpl_name_prompt"],
            parent=self,
        )
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showerror(self._L["err_title"], self._L["tmpl_empty_error"])
            return
        if template_name_exists(self.current_settings, name):
            messagebox.showerror(self._L["err_title"], self._L["tmpl_dup_error"])
            return

        custom_val = self.ocr_prompt_text.get("1.0", "end").strip()
        summary_val = self.ocr_summary_prompt_text.get("1.0", "end").strip()
        save_template(self.current_settings, name, custom_val, summary_val)
        self.current_settings.setdefault(
            "prompt_templates", {"active": "", "items": {}}
        )
        self.current_settings["prompt_templates"]["active"] = name
        self._active_template_name = name
        # CR-02 修正: 即時ディスク永続化を除去。self.current_settings は
        # __init__ でディープコピー分離済みのため、この変更は「キャンセル」
        # （destroy のみ）で破棄可能。永続化は Apply（_apply）経由の一括確定
        # に一本化する。
        self._reload_template_combo(name)

    def _on_template_delete(self):
        """選択中テンプレートを削除する（D-03: アクティブテンプレートは拒否）。

        UI 側の削除ボタン無効化（_refresh_template_delete_state）に加え、
        settings.delete_template の ValueError による二重防御を構成する。
        削除前に messagebox.askyesno で確認を出し、No 応答なら
        delete_template を呼ばずに中止する（誤削除防止・02-REVIEW Fix 案2）。
        """
        name = self.template_var.get()
        if not name:
            return
        if name == self._active_template_name:
            messagebox.showinfo(
                self._L["info_title"], self._L["tmpl_active_delete_blocked"]
            )
            return
        if not messagebox.askyesno(
            self._L["confirm_title"], self._L["tmpl_delete_confirm"], parent=self
        ):
            return
        try:
            delete_template(self.current_settings, name)
        except ValueError:
            messagebox.showinfo(
                self._L["info_title"], self._L["tmpl_active_delete_blocked"]
            )
            return
        # CR-02 修正: 即時ディスク永続化を除去（Apply 経由の一括確定へ一本化）。
        self._reload_template_combo(self._active_template_name)

    def _on_template_rename(self):
        """選択中テンプレートをリネームする（D-04: 空名・重複名は拒否）。"""
        old_name = self.template_var.get()
        if not old_name:
            return
        new_name = simpledialog.askstring(
            self._L["tmpl_section_title"],
            self._L["tmpl_name_prompt"],
            parent=self,
            initialvalue=old_name,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror(self._L["err_title"], self._L["tmpl_empty_error"])
            return
        try:
            rename_template(self.current_settings, old_name, new_name)
        except ValueError:
            messagebox.showerror(self._L["err_title"], self._L["tmpl_dup_error"])
            return
        # rename_template（settings.py）が prompt_templates["active"] を
        # 追従更新するため、ここでは self._active_template_name を同期するのみ
        if self._active_template_name == old_name:
            self._active_template_name = new_name
        # CR-02 修正: 即時ディスク永続化を除去（Apply 経由の一括確定へ一本化）。
        self._reload_template_combo(new_name)

    # ── フォールバック順設定ハンドラ（V180-FALL-01〜03・D-13〜D-16）───

    def _on_fallback_toggle(self):
        """トグル状態に応じて順序リスト frame を pack/pack_forget する（D-16）。

        url_section_frame 等の既存プロバイダ固有欄と同型の動的表示切替
        パターン（`_on_provider_change`）を踏襲する。
        """
        if self.fallback_enabled_var.get():
            self.fallback_list_frame.pack(
                fill="x", padx=24, pady=(0, 4), before=self.lm_status_label
            )
        else:
            self.fallback_list_frame.pack_forget()

    def _reload_fallback_list(self, select_index=None):
        """self._fallback_chain の内容を Listbox へ反映する（merge.py._reload_list
        と同型）。select_index が指定されていればその位置を選択状態にする。
        """
        self.fallback_listbox.delete(0, tk.END)
        for name in self._fallback_chain:
            self.fallback_listbox.insert(tk.END, f"  {name}")
        if select_index is not None and self._fallback_chain:
            self.fallback_listbox.selection_set(select_index)
            self.fallback_listbox.see(select_index)

    def _fallback_move_up(self):
        """選択中の候補を1つ上へ移動する（merge.py._move_up の移植・D-13）。"""
        sel = self.fallback_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self._fallback_chain[i - 1], self._fallback_chain[i] = (
            self._fallback_chain[i],
            self._fallback_chain[i - 1],
        )
        self._reload_fallback_list(i - 1)

    def _fallback_move_down(self):
        """選択中の候補を1つ下へ移動する（merge.py._move_down の移植・D-13）。"""
        sel = self.fallback_listbox.curselection()
        if not sel or sel[0] >= len(self._fallback_chain) - 1:
            return
        i = sel[0]
        self._fallback_chain[i], self._fallback_chain[i + 1] = (
            self._fallback_chain[i + 1],
            self._fallback_chain[i],
        )
        self._reload_fallback_list(i + 1)

    def _fallback_add(self):
        """候補一覧から選択したプロバイダをチェーンへ追加する（D-14）。

        既知プロバイダ一覧に無い名前・重複追加は無視する
        （ホワイトリスト検証・Input Validation・ASVS L1）。
        """
        candidate = self.fallback_candidate_var.get()
        if not candidate or candidate not in self._fallback_known_providers:
            return
        if candidate in self._fallback_chain:
            return
        self._fallback_chain.append(candidate)
        self._reload_fallback_list(len(self._fallback_chain) - 1)

    def _fallback_remove(self):
        """選択中の候補をチェーンから除外する。"""
        sel = self.fallback_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self._fallback_chain.pop(i)
        select_index = max(0, i - 1) if self._fallback_chain else None
        self._reload_fallback_list(select_index)
