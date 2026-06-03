# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLM 設定ダイアログ（OCR と設定で共有）"""

import logging
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import C, LANG
from pagefolio.ocr import MAX_OCR_MAX_TOKENS, fetch_lm_studio_models
from pagefolio.settings import _current_font_size

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
#  LLM 設定ダイアログ（OCR と設定で共有）
# ══════════════════════════════════════════
class LLMConfigDialog(tk.Toplevel):
    """LM Studio の URL・モデル・OCR 解像度倍率・タイムアウトを編集する共通ダイアログ"""

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
            fs = _current_font_size
        w = max(520, int(fs * 42))
        h = max(420, self.winfo_reqheight() + 20)
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

        # URL
        url_row = tk.Frame(self, bg=C["BG_DARK"])
        url_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            url_row,
            text=self._L["settings_lm_url"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=14,
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

        # モデル
        model_row = tk.Frame(self, bg=C["BG_DARK"])
        model_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            model_row,
            text=self._L["settings_lm_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=14,
            anchor="w",
        ).pack(side="left")
        self.lm_model_var = tk.StringVar(
            value=self.current_settings.get("lm_studio_model", ""),
        )
        self.lm_model_combo = ttk.Combobox(
            model_row,
            textvariable=self.lm_model_var,
            font=self._font(-1),
            values=[],
        )
        self.lm_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(
            self,
            text=self._L["settings_lm_model_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=24)

        # 解像度倍率
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

        # タイムアウト
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

        # 最大トークン
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

        # 温度（temperature）
        tmp_row = tk.Frame(self, bg=C["BG_DARK"])
        tmp_row.pack(fill="x", padx=24, pady=2)
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

        # 並列度（concurrency）
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

        # 接続テスト・モデル取得
        lm_btn_row = tk.Frame(self, bg=C["BG_DARK"])
        lm_btn_row.pack(fill="x", padx=24, pady=(6, 2))
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

        self.lm_status_var = tk.StringVar(value="")
        self.lm_status_label = tk.Label(
            self,
            textvariable=self.lm_status_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
            wraplength=420,
            justify="left",
        )
        self.lm_status_label.pack(anchor="w", padx=24, pady=(2, 4))

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

    def _set_lm_status(self, text, kind="info"):
        """LM Studio 操作の状態を表示する。kind: 'info' / 'ok' / 'fail'"""
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

    def _fetch_models(self):
        url = self.lm_url_var.get().strip()
        if not url:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error="URL is empty"),
                kind="fail",
            )
            return
        self._set_lm_status(self._L["settings_lm_testing"].format(url=url), kind="info")
        try:
            models = fetch_lm_studio_models(url, timeout=10)
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
        url = self.lm_url_var.get().strip()
        if not url:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error="URL is empty"),
                kind="fail",
            )
            return
        self._set_lm_status(self._L["settings_lm_testing"].format(url=url), kind="info")
        try:
            models = fetch_lm_studio_models(url, timeout=10)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self._set_lm_status(
                self._L["settings_lm_test_fail"].format(error=str(e)), kind="fail"
            )
            return
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )

    def _apply(self):
        llm_settings = {}
        llm_settings["lm_studio_url"] = self.lm_url_var.get().strip() or (
            "http://localhost:1234"
        )
        llm_settings["lm_studio_model"] = self.lm_model_var.get().strip()
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
