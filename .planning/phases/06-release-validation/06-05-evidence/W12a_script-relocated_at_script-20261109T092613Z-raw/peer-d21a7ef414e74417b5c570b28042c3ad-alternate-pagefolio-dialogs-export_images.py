# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""画像エクスポートダイアログ — ページを画像（1ページ1ファイル）に変換"""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pagefolio.constants import (
    DEFAULT_EXPORT_JPG_QUALITY,
    DEFAULT_EXPORT_LONG_EDGE,
    EXPORT_LONG_EDGE_PRESETS,
    LANG,
    C,
)
from pagefolio.settings import get_current_font_size

logger = logging.getLogger(__name__)


class ExportImagesDialog(tk.Toplevel):
    """ページ→画像変換のオプション選択ダイアログ。

    確定時に callback(options) を呼ぶ。options は以下のキーを持つ dict:
      scope:   "all" | "selected" | "range"
      ranges:  scope=="range" 時の [(start, end), ...]（1始まり）
      long_px: 出力画像の長辺ピクセル数
      fmt:     "png" | "jpg"
      quality: JPEG 品質（fmt=="jpg" 時のみ使用）
    """

    def __init__(self, parent, total_pages, selected_count, callback, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["export_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.total_pages = total_pages
        self.selected_count = selected_count
        self.callback = callback
        self._font_size = get_current_font_size()

        self.scope_var = tk.StringVar(value="selected" if selected_count else "all")
        self.range_var = tk.StringVar(value="")
        self.size_var = tk.StringVar(value=str(DEFAULT_EXPORT_LONG_EDGE))
        self.fmt_var = tk.StringVar(value="png")
        self.quality_var = tk.IntVar(value=DEFAULT_EXPORT_JPG_QUALITY)

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{max(0, px - w // 2)}+{max(0, py - h // 2)}")

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _radio(self, parent, text, variable, value, state="normal"):
        return tk.Radiobutton(
            parent,
            text=text,
            variable=variable,
            value=value,
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            selectcolor=C["BG_CARD"],
            activebackground=C["BG_DARK"],
            activeforeground=C["TEXT_MAIN"],
            font=self._font(-1),
            state=state,
            anchor="w",
        )

    def _build(self):
        tk.Label(
            self,
            text=self._L["export_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4), padx=16)
        tk.Label(
            self,
            text=self._L["export_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="left",
        ).pack(pady=(0, 8), padx=16, anchor="w")

        # 対象ページ
        scope_frame = tk.Frame(self, bg=C["BG_DARK"])
        scope_frame.pack(fill="x", padx=16, pady=2)
        tk.Label(
            scope_frame,
            text=self._L["export_scope_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(anchor="w")
        self._radio(
            scope_frame, self._L["export_scope_all"], self.scope_var, "all"
        ).pack(anchor="w", padx=12)
        self._radio(
            scope_frame,
            self._L["export_scope_selected"].format(n=self.selected_count),
            self.scope_var,
            "selected",
            state="normal" if self.selected_count else "disabled",
        ).pack(anchor="w", padx=12)
        range_row = tk.Frame(scope_frame, bg=C["BG_DARK"])
        range_row.pack(fill="x", padx=12)
        self._radio(
            range_row, self._L["export_scope_range"], self.scope_var, "range"
        ).pack(side="left")
        tk.Entry(
            range_row,
            textvariable=self.range_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
            width=14,
        ).pack(side="left", padx=4)
        tk.Label(
            range_row,
            text=self._L["export_range_hint"].format(n=self.total_pages),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=2)

        # 長辺ピクセル数
        size_row = tk.Frame(self, bg=C["BG_DARK"])
        size_row.pack(fill="x", padx=16, pady=(8, 2))
        tk.Label(
            size_row,
            text=self._L["export_size_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        ttk.Combobox(
            size_row,
            textvariable=self.size_var,
            values=[str(v) for v in EXPORT_LONG_EDGE_PRESETS],
            state="readonly",
            width=8,
            font=self._font(-1),
        ).pack(side="left", padx=6)
        tk.Label(
            size_row,
            text=self._L["export_size_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(side="left", padx=2)

        # 形式・JPEG品質
        fmt_row = tk.Frame(self, bg=C["BG_DARK"])
        fmt_row.pack(fill="x", padx=16, pady=(8, 2))
        tk.Label(
            fmt_row,
            text=self._L["export_format_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self._radio(fmt_row, self._L["export_format_png"], self.fmt_var, "png").pack(
            side="left", padx=4
        )
        self._radio(fmt_row, self._L["export_format_jpg"], self.fmt_var, "jpg").pack(
            side="left", padx=4
        )

        quality_row = tk.Frame(self, bg=C["BG_DARK"])
        quality_row.pack(fill="x", padx=16, pady=2)
        tk.Label(
            quality_row,
            text=self._L["export_quality_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(side="left")
        self.quality_spin = tk.Spinbox(
            quality_row,
            from_=10,
            to=100,
            increment=5,
            textvariable=self.quality_var,
            width=5,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            relief="flat",
            state="disabled",
        )
        self.quality_spin.pack(side="left", padx=6)
        # JPEG 選択時のみ品質スピンボックスを有効化
        self.fmt_var.trace_add("write", lambda *_a: self._update_quality_state())

        # 実行・キャンセル
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(12, 14))
        ttk.Button(
            btn_row,
            text=self._L["export_apply"],
            style="Accent.TButton",
            command=self._on_ok,
        ).pack(side="right", padx=4)
        ttk.Button(btn_row, text=self._L["export_cancel"], command=self.destroy).pack(
            side="right", padx=4
        )

    def _update_quality_state(self):
        state = "normal" if self.fmt_var.get() == "jpg" else "disabled"
        self.quality_spin.configure(state=state)

    def _on_ok(self):
        from pagefolio.page_ops import parse_page_ranges

        scope = self.scope_var.get()
        ranges = None
        if scope == "range":
            ranges = parse_page_ranges(self.range_var.get(), self.total_pages)
            if ranges is None:
                messagebox.showerror(
                    self._L["err_title"],
                    self._L["err_split_range"].format(n=self.total_pages),
                    parent=self,
                )
                return
        try:
            long_px = int(self.size_var.get())
        except ValueError:
            long_px = DEFAULT_EXPORT_LONG_EDGE
        try:
            quality = max(10, min(100, int(self.quality_var.get())))
        except (ValueError, tk.TclError):
            quality = DEFAULT_EXPORT_JPG_QUALITY
        options = {
            "scope": scope,
            "ranges": ranges,
            "long_px": long_px,
            "fmt": self.fmt_var.get(),
            "quality": quality,
        }
        self.destroy()
        self.callback(options)
