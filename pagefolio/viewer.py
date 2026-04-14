# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""表示 Mixin — プレビュー・ズーム・サムネイル・選択・ポップアップ"""

import tkinter as tk
from tkinter import ttk

import fitz
from PIL import Image, ImageTk

from pagefolio.constants import C


class ViewerMixin:
    """PDFEditorApp の表示・ナビゲーション・サムネイルメソッド群"""

    # ── 選択 ──
    def _toggle_select(self, i):
        if i in self.selected_pages:
            self.selected_pages.discard(i)
        else:
            self.selected_pages.add(i)
        self._refresh_thumbs_selection_only()

    def _select_all(self):
        if not self.doc:
            return
        self.selected_pages = set(range(len(self.doc)))
        self._refresh_thumbs_selection_only()

    def _deselect_all(self):
        self.selected_pages.clear()
        self._refresh_thumbs_selection_only()

    # ── プレビュー ──
    def _show_preview(self):
        self.preview_canvas.delete("all")
        self.crop_overlay_ids = []
        self.crop_rect_id = None
        if not self.doc or len(self.doc) == 0:
            self.preview_canvas.update_idletasks()
            cw = self.preview_canvas.winfo_width()
            ch = self.preview_canvas.winfo_height()
            self.preview_canvas.create_text(
                cw // 2,
                ch // 2 - 16,
                text=self._t("preview_empty1"),
                fill=C["TEXT_SUB"],
                font=self._font(4),
            )
            self.preview_canvas.create_text(
                cw // 2,
                ch // 2 + 16,
                text=self._t("preview_empty2"),
                fill=C["TEXT_SUB"],
                font=self._font(),
            )
            return
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom * 1.5, self.zoom * 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.preview_img_ref = photo
        pad = 10
        self.preview_canvas.create_rectangle(
            pad + 3,
            pad + 3,
            pad + pix.width + 3,
            pad + pix.height + 3,
            fill=C["TEXT_SUB"],
            outline="",
        )
        self.preview_canvas.create_rectangle(
            pad,
            pad,
            pad + pix.width,
            pad + pix.height,
            fill="",
            outline=C["TEXT_SUB"],
            width=1,
        )
        self.preview_canvas.create_image(pad, pad, anchor="nw", image=photo)
        self.preview_canvas.configure(
            scrollregion=(0, 0, pix.width + pad * 2, pix.height + pad * 2)
        )

    # ── ナビゲーション & ズーム ──
    def _prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._refresh_all()
            self.plugin_manager.fire_event("on_page_change", self, self.current_page)

    def _next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self._refresh_all()
            self.plugin_manager.fire_event("on_page_change", self, self.current_page)

    def _zoom(self, delta):
        self.zoom = max(0.3, min(3.0, self.zoom + delta))
        self.zoom_label.configure(text=f"{int(self.zoom * 100)}%")
        self._show_preview()

    # ── サムネイルキャッシュ ──
    def _invalidate_thumb_cache(self, pages=None):
        if pages is None:
            self.thumb_cache.clear()
        else:
            for p in pages:
                self.thumb_cache.pop(p, None)

    def _get_thumb_photo(self, i):
        if i in self.thumb_cache:
            return self.thumb_cache[i]
        page = self.doc[i]
        mat = fitz.Matrix(0.22, 0.22)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.thumb_cache[i] = photo
        return photo

    # ── 表示更新 ──
    def _refresh_all(self):
        self._build_thumbnails()
        self._show_preview()
        self._update_doc_buttons_state()
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page + 1} / {n}" if n else "- / -"
        )
        if n <= 1:
            self.prev_btn.state(["disabled"])
            self.next_btn.state(["disabled"])
        else:
            prev_st = ["!disabled"] if self.current_page > 0 else ["disabled"]
            next_st = ["!disabled"] if self.current_page < n - 1 else ["disabled"]
            self.prev_btn.state(prev_st)
            self.next_btn.state(next_st)

    def _refresh_thumbs_selection_only(self):
        """選択・カレント変更のみ — 画像再生成なし"""
        frames = self.thumb_inner.winfo_children()
        for i, frame in enumerate(frames):
            is_sel = i in self.selected_pages
            is_cur = i == self.current_page
            bg = C["ACCENT"] if is_sel else (C["BG_CARD"] if is_cur else C["BG_PANEL"])
            frame.configure(bg=bg)
            for child in frame.winfo_children():
                child.configure(bg=bg)
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page + 1} / {n}" if n else "- / -"
        )
        if n <= 1:
            self.prev_btn.state(["disabled"])
            self.next_btn.state(["disabled"])
        else:
            prev_st = ["!disabled"] if self.current_page > 0 else ["disabled"]
            next_st = ["!disabled"] if self.current_page < n - 1 else ["disabled"]
            self.prev_btn.state(prev_st)
            self.next_btn.state(next_st)

    def _build_thumbnails(self):
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.thumb_images.clear()
        if not self.doc:
            return
        for i in range(len(self.doc)):
            self._add_thumb(i)

    def _add_thumb(self, i):
        photo = self._get_thumb_photo(i)
        self.thumb_images.append(photo)

        is_sel = i in self.selected_pages
        is_cur = i == self.current_page
        bg = C["ACCENT"] if is_sel else (C["BG_CARD"] if is_cur else C["BG_PANEL"])

        frame = tk.Frame(self.thumb_inner, bg=bg, cursor="hand2")
        frame.pack(fill="x", padx=6, pady=3)

        lbl = tk.Label(frame, image=photo, bg=bg)
        lbl.pack(pady=(4, 0))
        tk.Label(
            frame, text=f"p.{i + 1}", bg=bg, fg=C["TEXT_MAIN"], font=self._font(-2)
        ).pack(pady=(0, 4))

        def on_press(event, idx=i):
            self._dnd_src_idx = idx
            self._dnd_press_x = event.x_root
            self._dnd_press_y = event.y_root
            self._dnd_dragging = False

        def on_motion(event, idx=i):
            if self._dnd_src_idx is None:
                return
            dx = abs(event.x_root - self._dnd_press_x)
            dy = abs(event.y_root - self._dnd_press_y)
            if not self._dnd_dragging and (dx > 5 or dy > 5):
                self._dnd_dragging = True
                self._dnd_start_ghost(idx)
            if self._dnd_dragging:
                self._dnd_move_ghost(event)
                self._dnd_show_indicator(event)

        def on_release(event, idx=i):
            if self._dnd_dragging:
                self._dnd_drop(event)
            else:
                if event.state & 0x0004:  # Ctrl
                    self._toggle_select(idx)
                else:
                    self._pending_click = self.root.after(
                        250, lambda: self._single_click(idx)
                    )
            self._dnd_src_idx = None
            self._dnd_dragging = False
            self._dnd_destroy_ghost()
            self._dnd_clear_indicator()

        def on_double(event, idx=i):
            if hasattr(self, "_pending_click") and self._pending_click:
                self.root.after_cancel(self._pending_click)
                self._pending_click = None
            self._show_page_popup(idx)

        for w in (frame, lbl):
            w.bind("<ButtonPress-1>", on_press)
            w.bind("<B1-Motion>", on_motion)
            w.bind("<ButtonRelease-1>", on_release)
            w.bind("<Double-Button-1>", on_double)

    # ── ページ拡大表示ポップアップ ──
    def _single_click(self, idx):
        """遅延実行されるシングルクリック処理"""
        self._pending_click = None
        self.selected_pages.clear()
        self.current_page = idx
        self._refresh_all()

    def _show_page_popup(self, idx):
        """サムネイルダブルクリックでページを拡大表示"""
        if not self.doc or idx >= len(self.doc):
            return
        popup = tk.Toplevel(self.root)
        popup.configure(bg=C["PREVIEW_BG"])
        popup.geometry("900x700")
        popup.transient(self.root)

        toolbar = tk.Frame(popup, bg=C["BG_PANEL"], height=56)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        popup_state = {"idx": idx, "zoom": 1.5}
        n = len(self.doc)

        def update_nav():
            i = popup_state["idx"]
            page_lbl.configure(text=f"{i + 1} / {n}")
            popup.title(f"ページ {i + 1} / {n}")
            if n <= 1:
                prev_btn.state(["disabled"])
                next_btn.state(["disabled"])
            else:
                prev_btn.state(["!disabled"] if i > 0 else ["disabled"])
                next_btn.state(["!disabled"] if i < n - 1 else ["disabled"])

        def render_page():
            canvas.delete("all")
            page = self.doc[popup_state["idx"]]
            mat = fitz.Matrix(popup_state["zoom"], popup_state["zoom"])
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            canvas._photo = photo
            pad = 10
            canvas.create_rectangle(
                pad + 3,
                pad + 3,
                pad + pix.width + 3,
                pad + pix.height + 3,
                fill=C["TEXT_SUB"],
                outline="",
            )
            canvas.create_rectangle(
                pad,
                pad,
                pad + pix.width,
                pad + pix.height,
                fill="",
                outline=C["TEXT_SUB"],
                width=1,
            )
            canvas.create_image(pad, pad, anchor="nw", image=photo)
            canvas.configure(
                scrollregion=(
                    0,
                    0,
                    pix.width + pad * 2,
                    pix.height + pad * 2,
                )
            )
            zoom_lbl.configure(text=f"{int(popup_state['zoom'] / 1.5 * 100)}%")
            update_nav()

        def go_prev():
            if popup_state["idx"] > 0:
                popup_state["idx"] -= 1
                render_page()

        def go_next():
            if popup_state["idx"] < n - 1:
                popup_state["idx"] += 1
                render_page()

        def zoom_in():
            popup_state["zoom"] = min(5.0, popup_state["zoom"] + 0.3)
            render_page()

        def zoom_out():
            popup_state["zoom"] = max(0.3, popup_state["zoom"] - 0.3)
            render_page()

        prev_btn = ttk.Button(toolbar, text="◀", command=go_prev)
        prev_btn.pack(side="left", padx=(12, 4), pady=10)
        page_lbl = tk.Label(
            toolbar,
            text=f"{idx + 1} / {n}",
            bg=C["BG_PANEL"],
            fg=C["TEXT_MAIN"],
            font=self._font(2, "bold"),
        )
        page_lbl.pack(side="left", padx=6)
        next_btn = ttk.Button(toolbar, text="▶", command=go_next)
        next_btn.pack(side="left", padx=4)

        zoom_lbl = tk.Label(
            toolbar,
            text="100%",
            bg=C["BG_PANEL"],
            fg=C["TEXT_SUB"],
            font=self._font(0),
        )
        zoom_lbl.pack(side="right", padx=8)
        ttk.Button(
            toolbar,
            text="🔍 縮小",
            command=zoom_out,
        ).pack(side="right", padx=4, pady=10)
        ttk.Button(
            toolbar,
            text="🔍 拡大",
            command=zoom_in,
        ).pack(side="right", padx=4, pady=10)
        ttk.Button(
            toolbar, text="✕ 閉じる", command=popup.destroy, style="Danger.TButton"
        ).pack(side="right", padx=8, pady=10)

        frame = tk.Frame(popup, bg=C["PREVIEW_BG"])
        frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(frame, bg=C["PREVIEW_BG"], highlightthickness=0)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        render_page()
        popup.focus_set()
