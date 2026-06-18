# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""表示 Mixin — プレビュー・ズーム・サムネイル・選択・ポップアップ"""

import logging
import tkinter as tk
from tkinter import ttk

import fitz
from PIL import Image, ImageTk

from pagefolio.constants import C
from pagefolio.pagination import to_global, window_bounds

logger = logging.getLogger(__name__)


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
    def _render_preview_pixmap(self, page_idx, zoom):
        """Tk 非依存の純関数プレビューレンダリングヘルパー。

        self.doc[page_idx] を直接参照して get_pixmap を同期呼び出しし、
        (samples: bytes, w: int, h: int) を返す。doc.tobytes() を一切呼ばない。
        """
        page = self.doc[page_idx]
        mat = fitz.Matrix(zoom * 1.5, zoom * 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return bytes(pix.samples), pix.width, pix.height

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

        page_idx = self.current_page
        zoom = self.zoom
        try:
            samples, w, h = self._render_preview_pixmap(page_idx, zoom)
        except Exception as e:
            logger.debug("プレビュー描画例外: %s", e)
            return
        img = Image.frombytes("RGB", [w, h], samples)
        photo = ImageTk.PhotoImage(img)
        self.preview_img_ref = photo
        pad = 10
        self.preview_canvas.delete("all")
        self.preview_canvas.create_rectangle(
            pad + 3,
            pad + 3,
            pad + w + 3,
            pad + h + 3,
            fill=C["TEXT_SUB"],
            outline="",
        )
        self.preview_canvas.create_rectangle(
            pad,
            pad,
            pad + w,
            pad + h,
            fill="",
            outline=C["TEXT_SUB"],
            width=1,
        )
        self.preview_canvas.create_image(pad, pad, anchor="nw", image=photo)
        self.preview_canvas.configure(scrollregion=(0, 0, w + pad * 2, h + pad * 2))

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
        zoom = getattr(self, "thumb_zoom_var", None)
        z = zoom.get() if zoom else 1.0
        mat = fitz.Matrix(0.22 * z, 0.22 * z)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.thumb_cache[i] = photo
        return photo

    def _on_thumb_zoom_release(self, event=None):
        if not hasattr(self, "thumb_zoom_var"):
            return
        self.settings["thumb_zoom"] = self.thumb_zoom_var.get()
        from pagefolio.settings import _save_settings

        _save_settings(self.settings)
        self._invalidate_thumb_cache()
        self._refresh_all()

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
            # enumerate 位置（窓ローカル）を全ページ index へ変換し照合（Pitfall 1）
            # selected_pages はローカル化せず全ページ index の不変条件を保つ（D-07）
            g = to_global(i, self._page_window_start)
            is_sel = g in self.selected_pages
            is_cur = g == self.current_page
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
        self._thumb_gen += 1
        gen = self._thumb_gen
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.thumb_images.clear()
        if not self.doc:
            return
        # 窓範囲 [lo, hi) のみ描画（D-10 端数最終窓クランプ）。
        # i は全ページ index のまま _add_thumb_placeholder へ渡す（D-06 src 整合）。
        lo, hi = window_bounds(self._page_window_start, self._page_size, len(self.doc))
        placeholder_labels = [self._add_thumb_placeholder(i) for i in range(lo, hi)]

        def render_next(i):
            if self._thumb_gen != gen or not self.doc:
                logger.debug(
                    "サムネイルレンダリングスキップ: gen=%s, current_gen=%s",
                    gen,
                    self._thumb_gen,
                )
                return
            if i >= hi:
                return
            photo = self._get_thumb_photo(i)
            # placeholder_labels は窓ローカル添字（i - lo）で参照する
            frame, lbl = placeholder_labels[i - lo]
            lbl.configure(image=photo)
            self.thumb_images.append(photo)
            self.root.after(0, lambda: render_next(i + 1))

        self.root.after_idle(lambda: render_next(lo))

    def _add_thumb_placeholder(self, i):
        """プレースホルダー frame・lbl を作成しイベントをバインドして返す"""
        is_sel = i in self.selected_pages
        is_cur = i == self.current_page
        bg = C["ACCENT"] if is_sel else (C["BG_CARD"] if is_cur else C["BG_PANEL"])

        frame = tk.Frame(self.thumb_inner, bg=bg, cursor="hand2")
        frame.pack(fill="x", padx=6, pady=3)

        lbl = tk.Label(frame, bg=bg)
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

        return frame, lbl

    def _add_thumb(self, i):
        frame, lbl = self._add_thumb_placeholder(i)
        photo = self._get_thumb_photo(i)
        lbl.configure(image=photo)
        self.thumb_images.append(photo)

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
