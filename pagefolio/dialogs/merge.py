# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""結合順ダイアログ・ページ結合リサイズダイアログ"""

import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk

import fitz

from pagefolio.constants import LANG, C
from pagefolio.settings import _current_font_size

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
#  結合順ダイアログ
# ══════════════════════════════════════════
class MergeOrderDialog(tk.Toplevel):
    def __init__(self, parent, paths, callback, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["merge_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(True, True)
        self.grab_set()

        self.paths = paths
        self.callback = callback
        self._font_size = _current_font_size

        self._page_counts = {}
        for p in paths:
            try:
                d = fitz.open(p)
                self._page_counts[p] = len(d)
                d.close()
            except Exception as e:
                logger.debug("ページ数取得失敗: %s", e)
                self._page_counts[p] = 0

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = self._font_size
        w = max(480, int(fs * 40))
        base_h = max(420, int(fs * 32))
        extra_h = max(0, len(self.paths) - 4) * int(fs * 2.5)
        h = min(base_h + extra_h, parent.winfo_height() - 40)
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(400, 350)

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        tk.Label(
            self,
            text=self._L["merge_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))
        tk.Label(
            self,
            text=self._L["merge_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="center",
        ).pack(pady=(0, 8))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        list_height = max(6, min(20, len(self.paths) + 2))
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=sb.set,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            selectbackground=C["ACCENT"],
            selectforeground="#fff",
            font=self._font(-1),
            activestyle="none",
            bd=0,
            highlightthickness=0,
            height=list_height,
        )
        sb.configure(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)

        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=6)
        ttk.Button(btn_row, text=self._L["merge_up"], command=self._move_up).pack(
            side="left", padx=4
        )
        ttk.Button(btn_row, text=self._L["merge_down"], command=self._move_down).pack(
            side="left", padx=4
        )
        ttk.Button(
            btn_row,
            text=self._L["merge_remove"],
            style="Danger.TButton",
            command=self._remove_item,
        ).pack(side="left", padx=4)

        self.info_var = tk.StringVar()
        tk.Label(
            self,
            textvariable=self.info_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-1),
        ).pack(pady=2)
        self._update_info()

        ok_row = tk.Frame(self, bg=C["BG_DARK"])
        ok_row.pack(pady=(4, 14))
        ttk.Button(
            ok_row,
            text=self._L["merge_confirm"],
            style="Accent.TButton",
            command=self._confirm,
        ).pack(side="left", padx=8)
        ttk.Button(ok_row, text=self._L["merge_cancel"], command=self.destroy).pack(
            side="left", padx=8
        )

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.paths[i - 1], self.paths[i] = self.paths[i], self.paths[i - 1]
        self._reload_list(i - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.paths) - 1:
            return
        i = sel[0]
        self.paths[i], self.paths[i + 1] = self.paths[i + 1], self.paths[i]
        self._reload_list(i + 1)

    def _remove_item(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self.paths.pop(i)
        self._reload_list(max(0, i - 1))

    def _reload_list(self, select_idx=None):
        self.listbox.delete(0, tk.END)
        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")
        if select_idx is not None and self.paths:
            self.listbox.selection_set(select_idx)
            self.listbox.see(select_idx)
        self._update_info()

    def _update_info(self):
        total = sum(self._page_counts.get(p, 0) for p in self.paths)
        info_txt = self._L["merge_info"].format(
            count=len(self.paths),
            total=total,
        )
        self.info_var.set(info_txt)

    def _confirm(self):
        if not self.paths:
            messagebox.showinfo(
                self._L.get("info_title", "Info"),
                self._L["merge_no_files"],
                parent=self,
            )
            return
        self.destroy()
        self.callback(self.paths)


# ══════════════════════════════════════════
#  ページ結合・リサイズダイアログ
# ══════════════════════════════════════════
class MergeResizeDialog(tk.Toplevel):
    """選択ページを1枚に結合・リサイズするための方向選択ダイアログ"""

    def __init__(self, parent, page_infos, callback, lang="ja", font_func=None):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["mr_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.page_infos = page_infos  # [(page_no_1based, width, height), ...]
        self.callback = callback
        self._font_size = _current_font_size
        self._font_func = font_func

        self._build()
        self._update_size_preview()
        self.update_idletasks()
        fs = self._font_size
        w = max(420, int(fs * 38))
        h = max(360, int(fs * 28) + len(page_infos) * (fs + 6))
        h = min(h, parent.winfo_height() - 40)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(380, 300)

    def _font(self, delta=0, weight=None):
        if self._font_func:
            return self._font_func(delta, weight)
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        count = len(self.page_infos)

        tk.Label(
            self,
            text=self._L["mr_dialog_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))

        tk.Label(
            self,
            text=self._L["mr_dialog_hint"].format(count=count),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="center",
        ).pack(pady=(0, 10))

        # 方向選択
        df = tk.Frame(self, bg=C["BG_DARK"])
        df.pack(fill="x", padx=24, pady=4)
        tk.Label(
            df,
            text=self._L["mr_direction"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.dir_var = tk.StringVar(value="horizontal")
        for value, key in (
            ("horizontal", "mr_horizontal"),
            ("vertical", "mr_vertical"),
        ):
            tk.Radiobutton(
                df,
                text=self._L[key],
                variable=self.dir_var,
                value=value,
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                selectcolor=C["BG_CARD"],
                activebackground=C["BG_DARK"],
                activeforeground=C["TEXT_MAIN"],
                font=self._font(-1),
                command=self._update_size_preview,
            ).pack(side="left", padx=6)

        # 結合順表示
        tk.Label(
            self,
            text=self._L["mr_order_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(anchor="w", padx=24, pady=(8, 2))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="x", padx=24, pady=2)
        for pno, w, h in self.page_infos:
            tk.Label(
                list_frame,
                text=f"  p.{pno}   ({int(w)}×{int(h)} pt)",
                bg=C["BG_PANEL"],
                fg=C["TEXT_MAIN"],
                font=self._font(-1),
                anchor="w",
            ).pack(fill="x", padx=4, pady=1)

        # 出力サイズプレビュー
        self.size_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self.size_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(0, "bold"),
        ).pack(pady=(10, 4))

        # ボタン
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["mr_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(
            btn_row,
            text=self._L["mr_cancel"],
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _compute_size(self):
        widths = [w for _, w, _ in self.page_infos]
        heights = [h for _, _, h in self.page_infos]
        if self.dir_var.get() == "horizontal":
            return sum(widths), max(heights)
        return max(widths), sum(heights)

    def _update_size_preview(self):
        w, h = self._compute_size()
        self.size_var.set(self._L["mr_size_preview"].format(w=int(w), h=int(h)))

    def _apply(self):
        direction = self.dir_var.get()
        out_w, out_h = self._compute_size()
        self.destroy()
        self.callback(direction, out_w, out_h)
