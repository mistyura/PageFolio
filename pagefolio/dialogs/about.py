# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""About ダイアログ"""

import logging
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import APP_VERSION, LANG, C

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
#  About ダイアログ
# ══════════════════════════════════════════
class AboutDialog(tk.Toplevel):
    def __init__(self, parent, font_func, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["about_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self._font = font_func
        self._build()
        self.update_idletasks()
        w = 360
        h = max(300, self.winfo_reqheight() + 20)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text="PageFolio",
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            # D-12/D-13: font_size 設定（既定12・8〜16）に追従させる。
            # delta=4 は既定値12との組合せで是正前の見た目（16pt）を再現する
            # （R3: 最大値16でも20ptに収まり360px幅ダイアログ内で横はみ出しなし）。
            font=self._font(4, "bold"),
        ).pack(pady=(20, 2))
        tk.Label(
            self,
            text=APP_VERSION,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(0),
        ).pack()
        tk.Label(
            self,
            text=self._L["about_subtitle"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(pady=(2, 12))

        sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
        sep.pack(fill="x", padx=30, pady=4)

        tk.Label(
            self,
            text="Copyright (c) 2026 mistyura",
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(pady=(6, 2))
        tk.Label(
            self,
            text="MIT License",
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack()
        tk.Label(
            self,
            text="https://github.com/mistyura/PageFolio",
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
        ).pack(pady=(2, 16))

        ttk.Button(
            self, text=self._L["about_ok"], command=self.destroy, style="Accent.TButton"
        ).pack(pady=(0, 16))
