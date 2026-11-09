# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""パスワード設定ダイアログ — PDF にパスワード（暗号化）を付与する際の入力 UI"""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pagefolio.constants import LANG, C
from pagefolio.settings import get_current_font_size

logger = logging.getLogger(__name__)


class SetPasswordDialog(tk.Toplevel):
    """パスワード設定ダイアログ。

    パスワードと確認用パスワードを入力させ、一致を検証してから
    callback(password) を呼ぶ。空欄・不一致時はエラーを表示して継続する。
    """

    def __init__(self, parent, font_fn=None, callback=None, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.callback = callback
        self._font_size = get_current_font_size()
        self.title(self._L["pwd_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.pwd_var = tk.StringVar(value="")
        self.confirm_var = tk.StringVar(value="")
        self.show_var = tk.BooleanVar(value=False)

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{max(0, px - w // 2)}+{max(0, py - h // 2)}")
        self._pwd_entry.focus_set()

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _entry(self, parent, variable):
        return tk.Entry(
            parent,
            textvariable=variable,
            show="" if self.show_var.get() else "*",
            font=self._font(0),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
            width=24,
        )

    def _build(self):
        tk.Label(
            self,
            text=self._L["pwd_dialog_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4), padx=16)
        tk.Label(
            self,
            text=self._L["pwd_dialog_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="left",
        ).pack(pady=(0, 10), padx=16, anchor="w")

        pwd_row = tk.Frame(self, bg=C["BG_DARK"])
        pwd_row.pack(fill="x", padx=16, pady=3)
        tk.Label(
            pwd_row,
            text=self._L["pwd_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
            width=12,
            anchor="w",
        ).pack(side="left")
        self._pwd_entry = self._entry(pwd_row, self.pwd_var)
        self._pwd_entry.pack(side="left", padx=4)

        confirm_row = tk.Frame(self, bg=C["BG_DARK"])
        confirm_row.pack(fill="x", padx=16, pady=3)
        tk.Label(
            confirm_row,
            text=self._L["pwd_confirm_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
            width=12,
            anchor="w",
        ).pack(side="left")
        self._confirm_entry = self._entry(confirm_row, self.confirm_var)
        self._confirm_entry.pack(side="left", padx=4)

        tk.Checkbutton(
            self,
            text=self._L["pwd_show"],
            variable=self.show_var,
            command=self._toggle_show,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            selectcolor=C["BG_CARD"],
            activebackground=C["BG_DARK"],
            activeforeground=C["TEXT_MAIN"],
            font=self._font(-1),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(2, 6))

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["pwd_apply"],
            style="Accent.TButton",
            command=self._on_ok,
        ).pack(side="right", padx=4)
        ttk.Button(btn_row, text=self._L["pwd_cancel"], command=self.destroy).pack(
            side="right", padx=4
        )
        self.bind("<Return>", lambda _e: self._on_ok())

    def _toggle_show(self):
        show = "" if self.show_var.get() else "*"
        self._pwd_entry.configure(show=show)
        self._confirm_entry.configure(show=show)

    def _on_ok(self):
        pwd = self.pwd_var.get()
        confirm = self.confirm_var.get()
        if not pwd:
            messagebox.showerror(
                self._L["err_title"], self._L["pwd_empty"], parent=self
            )
            return
        if pwd != confirm:
            messagebox.showerror(
                self._L["err_title"], self._L["pwd_mismatch"], parent=self
            )
            return
        self.destroy()
        if self.callback:
            self.callback(pwd)
