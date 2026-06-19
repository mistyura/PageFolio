# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""D&D Mixin — サムネイルのドラッグ＆ドロップによるページ並び替え"""

import tkinter as tk

from pagefolio.constants import C
from pagefolio.pagination import to_global, window_bounds


class DnDMixin:
    """PDFEditorApp のD&Dメソッド群"""

    def _dnd_start_ghost(self, idx):
        if self._dnd_ghost:
            self._dnd_ghost.destroy()
        photo = self.thumb_images[idx]
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes("-alpha", 0.6)
        ghost.attributes("-topmost", True)
        lbl = tk.Label(ghost, image=photo, bg=C["BG_CARD"], relief="flat", bd=2)
        lbl.pack()
        if idx in self.selected_pages and len(self.selected_pages) > 1:
            label_text = f"{len(self.selected_pages)} pages"
        else:
            label_text = f"p.{idx + 1}"
        num = tk.Label(
            ghost,
            text=label_text,
            bg=C["BG_CARD"],
            fg=C["ACCENT"],
            font=self._font(-2, "bold"),
        )
        num.pack()
        self._dnd_ghost = ghost

    def _dnd_move_ghost(self, event):
        if self._dnd_ghost:
            self._dnd_ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 8}")

    def _dnd_destroy_ghost(self):
        if self._dnd_ghost:
            self._dnd_ghost.destroy()
            self._dnd_ghost = None

    def _dnd_show_indicator(self, event):
        self._dnd_clear_indicator()
        dest = self._dnd_dest_index(event)
        if dest is None:
            return
        frames = self.thumb_inner.winfo_children()
        if not frames:
            return
        if dest < len(frames):
            fr = frames[dest]
        else:
            fr = frames[-1]
        fr.update_idletasks()
        fy = fr.winfo_y()
        fh = fr.winfo_height()
        y = fy if dest < len(frames) else fy + fh
        cw = self.thumb_canvas.winfo_width()
        self._dnd_indicator = self.thumb_canvas.create_line(
            4, y, cw - 4, y, fill=C["ACCENT"], width=3, dash=(6, 3)
        )

    def _dnd_clear_indicator(self):
        if self._dnd_indicator:
            self.thumb_canvas.delete(self._dnd_indicator)
            self._dnd_indicator = None

    def _dnd_dest_index(self, event):
        """マウス位置から挿入先を計算"""
        frames = self.thumb_inner.winfo_children()
        if not frames:
            return None
        canvas_y = event.y_root - self.thumb_canvas.winfo_rooty()
        cy = self.thumb_canvas.canvasy(canvas_y)
        first_y = frames[0].winfo_y()
        last_frame = frames[-1]
        last_bottom = last_frame.winfo_y() + last_frame.winfo_height()
        if cy < first_y:
            return 0
        if cy > last_bottom:
            return len(frames)
        for i, fr in enumerate(frames):
            fy = fr.winfo_y()
            fh = fr.winfo_height()
            if cy < fy + fh / 2:
                return i
        return len(frames)

    def _dnd_drop(self, event):
        src = self._dnd_src_idx
        dest = self._dnd_dest_index(event)
        if dest is None or src is None:
            return
        n = len(self.doc)
        # dest は窓内フレーム位置（ローカル）。to_global で全ページ index へ換算する
        # （変換は本 1 箇所のみ・Anti-Pattern「散在させない」・D-06）。src は
        # _add_thumb_placeholder が全ページ index で束縛するため変換不要。
        lo, _hi = window_bounds(self._page_window_start, self._page_size, n)
        dest = to_global(dest, lo)
        dest = max(0, min(dest, n))
        if src in self.selected_pages and len(self.selected_pages) > 1:
            sorted_sel = sorted(self.selected_pages)
            non_selected = [p for p in range(n) if p not in self.selected_pages]
            sel_before_dest = sum(1 for p in self.selected_pages if p < dest)
            adj_dest = dest - sel_before_dest
            adj_dest = max(0, min(adj_dest, len(non_selected)))
            new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
            if len(new_order) != n:
                return
            self.doc.select(new_order)
            self._save_undo("bulk_move", new_order=new_order)
            self.current_page = new_order.index(src)
            self.selected_pages.clear()
            self._invalidate_thumb_cache()
            self._refresh_all()
            self._set_status(self._t("status_bulk_moved").format(count=len(sorted_sel)))
            return
        if dest == src or dest == src + 1:
            return
        if dest >= n:
            self.doc.move_page(src, -1)
            actual_dest = n - 1
        else:
            actual_dest = dest if dest < src else dest - 1
            self.doc.move_page(src, dest)
        self._save_undo("move", src=src, actual_dest=actual_dest)
        self.current_page = actual_dest
        self.selected_pages.clear()
        self._invalidate_thumb_cache()
        self._refresh_all()
        msg = self._t("status_dnd_moved").format(
            src=src + 1,
            dest=actual_dest + 1,
        )
        self._set_status(msg)
