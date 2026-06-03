# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Settings ダイアログ"""

import logging
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import C, LANG

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
#  設定ダイアログ
# ══════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_settings, callback, font_func=None):
        super().__init__(parent)
        lang = current_settings.get("lang", "ja")
        self._L = LANG[lang]
        self.title(self._L["settings_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.callback = callback
        self.current_settings = dict(current_settings)
        self._font = font_func

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = current_settings.get("font_size", 12)
        w = max(460, int(fs * 38))
        h = max(420, self.winfo_reqheight() + 20)
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text=self._L["settings_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        tf = tk.Frame(self, bg=C["BG_DARK"])
        tf.pack(fill="x", padx=24, pady=6)
        tk.Label(
            tf,
            text=self._L["settings_theme"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.theme_var = tk.StringVar(value=self.current_settings.get("theme", "dark"))
        theme_options = [
            (self._L["settings_theme_dark"], "dark"),
            (self._L["settings_theme_light"], "light"),
            (self._L["settings_theme_system"], "system"),
        ]
        for text, value in theme_options:
            tk.Radiobutton(
                tf,
                text=text,
                variable=self.theme_var,
                value=value,
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                selectcolor=C["BG_CARD"],
                activebackground=C["BG_DARK"],
                activeforeground=C["TEXT_MAIN"],
                font=self._font(-1),
            ).pack(side="left", padx=6)

        ff = tk.Frame(self, bg=C["BG_DARK"])
        ff.pack(fill="x", padx=24, pady=6)
        tk.Label(
            ff,
            text=self._L["settings_font"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.font_var = tk.IntVar(value=self.current_settings.get("font_size", 10))
        tk.Spinbox(
            ff,
            from_=8,
            to=16,
            textvariable=self.font_var,
            width=4,
            font=self._font(0),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=8)
        tk.Label(
            ff,
            text=self._L["settings_font_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
        ).pack(side="left")

        self.preview_label = tk.Label(
            self,
            text=self._L["settings_preview_text"],
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            font=("Segoe UI", self.font_var.get()),
            padx=12,
            pady=8,
        )
        self.preview_label.pack(padx=24, pady=8, fill="x")
        self.font_var.trace_add("write", self._update_preview)

        # ── LM Studio (OCR) セクション ──
        sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
        sep.pack(fill="x", padx=24, pady=(8, 4))
        tk.Label(
            self,
            text=self._L["settings_lm_studio_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        ).pack(anchor="w", padx=24, pady=(4, 2))

        ttk.Button(
            self,
            text=self._L["settings_open_llm_config"],
            command=self._open_llm_config,
        ).pack(anchor="w", padx=24, pady=(2, 8))

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["settings_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(btn_row, text=self._L["settings_cancel"], command=self.destroy).pack(
            side="left", padx=8
        )

    def _update_preview(self, *_):
        try:
            size = self.font_var.get()
            size = max(8, min(16, size))
            self.preview_label.configure(font=("Segoe UI", size))
        except Exception as e:
            logger.debug("フォントプレビュー更新失敗: %s", e)

    def _open_llm_config(self):
        """LLM 設定ダイアログを開き、適用時に current_settings を更新する"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        lang = self.current_settings.get("lang", "ja")

        def on_apply(llm_settings):
            self.current_settings.update(llm_settings)

        LLMConfigDialog(
            self,
            self.current_settings,
            on_apply=on_apply,
            font_func=self._font,
            lang=lang,
        )

    def _apply(self):
        new_settings = dict(self.current_settings)
        new_settings["theme"] = self.theme_var.get()
        new_settings["font_size"] = max(8, min(16, self.font_var.get()))
        self.destroy()
        self.callback(new_settings)
