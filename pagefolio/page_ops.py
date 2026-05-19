# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ページ操作 Mixin — 回転・削除・トリミング・挿入・結合・分割"""

import os
from tkinter import filedialog, messagebox, simpledialog

import fitz

from pagefolio.constants import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS, C


class PageOpsMixin:
    """PDFEditorApp のページ操作メソッド群"""

    def _rotate_selected(self, deg):
        if not self._check_doc():
            return
        targets = self._get_targets()
        self._save_undo("rotate", targets=targets)
        for i in targets:
            page = self.doc[i]
            page.set_rotation((page.rotation + deg) % 360)
        self._invalidate_thumb_cache(targets)
        self._refresh_all()
        self._set_status(self._t("status_rotated").format(count=len(targets), deg=deg))
        self.plugin_manager.fire_event("on_page_rotate", self, targets, deg)

    def _delete_selected(self):
        if not self._check_doc():
            return
        targets = sorted(self._get_targets(), reverse=True)
        if not targets:
            messagebox.showinfo(self._t("info_title"), self._t("info_no_page_sel"))
            return
        if len(targets) >= len(self.doc):
            messagebox.showwarning(
                self._t("warn_del_all_title"),
                self._t("warn_del_all"),
            )
            return
        if not messagebox.askyesno(
            self._t("confirm_title"), self._t("confirm_del").format(count=len(targets))
        ):
            return
        self._save_undo("delete", targets=targets)
        for i in targets:
            self.doc.delete_page(i)
        self.selected_pages.clear()
        self.current_page = min(self.current_page, max(0, len(self.doc) - 1))
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(self._t("status_deleted").format(count=len(targets)))
        self.plugin_manager.fire_event("on_page_delete", self, targets)

    def _duplicate_page(self):
        """アクティブページを直後に複製して挿入する"""
        if not self._check_doc():
            return
        pno = self.current_page
        self._save_undo("duplicate", pno=pno)
        try:
            tmp = fitz.open()
            tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
            self.doc.insert_pdf(tmp, start_at=pno + 1)
            tmp.close()
            self._invalidate_thumb_cache()
            self.current_page = pno + 1
            self._refresh_all()
            self._set_status(self._t("status_duplicated").format(page=pno + 1))
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    # ── トリミング ──
    def _toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            self.crop_toggle_btn.configure(
                text=self._t("crop_mode_on"), style="CropOn.TButton"
            )
            self.preview_canvas.configure(cursor="crosshair")
        else:
            self.crop_toggle_btn.configure(
                text=self._t("crop_mode_off"), style="TButton"
            )
            self.preview_canvas.configure(cursor="")
            self._clear_crop_overlay()

    def _crop_drag_start(self, event):
        if not self.crop_mode:
            return
        cx = self.preview_canvas.canvasx(event.x)
        cy = self.preview_canvas.canvasy(event.y)
        self.crop_drag_start = (cx, cy)
        self.crop_rect = None
        self._clear_crop_overlay()

    def _crop_drag_move(self, event):
        if not self.crop_mode or not self.crop_drag_start:
            return
        cx = self.preview_canvas.canvasx(event.x)
        cy = self.preview_canvas.canvasy(event.y)
        x0, y0 = self.crop_drag_start
        sx, sy, ex, ey = min(x0, cx), min(y0, cy), max(x0, cx), max(y0, cy)

        sr = self.preview_canvas.cget("scrollregion")
        if sr:
            parts = sr.split()
            pw = (
                float(parts[2])
                if len(parts) >= 3
                else self.preview_canvas.winfo_width()
            )
            ph = (
                float(parts[3])
                if len(parts) >= 4
                else self.preview_canvas.winfo_height()
            )
        else:
            pw = self.preview_canvas.winfo_width()
            ph = self.preview_canvas.winfo_height()

        _ov = dict(fill="#000000", stipple="gray50", outline="")
        if not self.crop_overlay_ids:
            cr = self.preview_canvas.create_rectangle
            self.crop_overlay_ids = [
                cr(0, 0, pw, sy, **_ov),
                cr(0, ey, pw, ph, **_ov),
                cr(0, sy, sx, ey, **_ov),
                cr(ex, sy, pw, ey, **_ov),
            ]
            self.crop_rect_id = self.preview_canvas.create_rectangle(
                sx, sy, ex, ey, outline=C["ACCENT"], width=2, dash=(4, 3)
            )
        else:
            self.preview_canvas.coords(self.crop_overlay_ids[0], 0, 0, pw, sy)
            self.preview_canvas.coords(self.crop_overlay_ids[1], 0, ey, pw, ph)
            self.preview_canvas.coords(self.crop_overlay_ids[2], 0, sy, sx, ey)
            self.preview_canvas.coords(self.crop_overlay_ids[3], ex, sy, pw, ey)
            if self.crop_rect_id:
                self.preview_canvas.coords(self.crop_rect_id, sx, sy, ex, ey)

        self.crop_rect = (sx, sy, ex, ey)
        scale = self.zoom * 1.5
        img_offset = 10
        px0 = int((sx - img_offset) / scale)
        py0 = int((sy - img_offset) / scale)
        px1 = int((ex - img_offset) / scale)
        py1 = int((ey - img_offset) / scale)
        self.crop_info_var.set(
            f"({px0},{py0}) - ({px1},{py1})  {px1 - px0}×{py1 - py0} pt"
        )

    def _crop_drag_end(self, event):
        if not self.crop_mode:
            return
        self._crop_drag_move(event)

    def _clear_crop_overlay(self):
        for oid in self.crop_overlay_ids:
            self.preview_canvas.delete(oid)
        self.crop_overlay_ids = []
        if self.crop_rect_id:
            self.preview_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    def _crop_reset(self):
        self.crop_rect = None
        self.crop_info_var.set(self._t("crop_no_sel"))
        self._clear_crop_overlay()

    def _crop_page(self):
        if not self._check_doc():
            return
        if not self.crop_rect:
            messagebox.showinfo(self._t("info_title"), self._t("info_crop_drag"))
            return
        targets = self._get_targets()
        if len(targets) > 1:
            if not messagebox.askyesno(
                self._t("confirm_title"),
                self._t("confirm_bulk_crop").format(count=len(targets)),
            ):
                return
        if len(targets) == 1:
            self._save_undo("crop", page_i=self.current_page)
            sx, sy, ex, ey = self.crop_rect
            scale = self.zoom * 1.5
            img_offset = 10
            x0_pdf = (sx - img_offset) / scale
            y0_pdf = (sy - img_offset) / scale
            x1_pdf = (ex - img_offset) / scale
            y1_pdf = (ey - img_offset) / scale
            page = self.doc[self.current_page]
            mb = page.mediabox
            new_rect = fitz.Rect(
                mb.x0 + x0_pdf, mb.y0 + y0_pdf, mb.x0 + x1_pdf, mb.y0 + y1_pdf
            )
            EPS = 0.01
            new_rect = fitz.Rect(
                max(round(new_rect.x0, 2), mb.x0 + EPS),
                max(round(new_rect.y0, 2), mb.y0 + EPS),
                min(round(new_rect.x1, 2), mb.x1 - EPS),
                min(round(new_rect.y1, 2), mb.y1 - EPS),
            )
            if (
                new_rect.is_empty
                or new_rect.is_infinite
                or new_rect.width < 1
                or new_rect.height < 1
            ):
                messagebox.showerror(self._t("err_title"), self._t("err_crop_small"))
                return
            try:
                page.set_cropbox(new_rect)
            except ValueError as e:
                messagebox.showerror(
                    self._t("err_crop_title"), self._t("err_crop_msg").format(e=e)
                )
                return
        else:
            sx, sy, ex, ey = self.crop_rect
            scale = self.zoom * 1.5
            img_offset = 10
            x0_pdf = (sx - img_offset) / scale
            y0_pdf = (sy - img_offset) / scale
            x1_pdf = (ex - img_offset) / scale
            y1_pdf = (ey - img_offset) / scale
            cur_mb = self.doc[self.current_page].mediabox
            rel = (
                x0_pdf / cur_mb.width,
                y0_pdf / cur_mb.height,
                x1_pdf / cur_mb.width,
                y1_pdf / cur_mb.height,
            )
            EPS = 0.01
            crop_data = []
            for i in targets:
                cb = self.doc[i].cropbox
                crop_data.append((i, (cb.x0, cb.y0, cb.x1, cb.y1)))
            self._save_undo("bulk_crop", crop_data=crop_data)
            for i in targets:
                page = self.doc[i]
                mb = page.mediabox
                new_rect = fitz.Rect(
                    mb.x0 + rel[0] * mb.width,
                    mb.y0 + rel[1] * mb.height,
                    mb.x0 + rel[2] * mb.width,
                    mb.y0 + rel[3] * mb.height,
                )
                new_rect = fitz.Rect(
                    max(round(new_rect.x0, 2), mb.x0 + EPS),
                    max(round(new_rect.y0, 2), mb.y0 + EPS),
                    min(round(new_rect.x1, 2), mb.x1 - EPS),
                    min(round(new_rect.y1, 2), mb.y1 - EPS),
                )
                if (
                    new_rect.is_empty
                    or new_rect.is_infinite
                    or new_rect.width < 1
                    or new_rect.height < 1
                ):
                    continue
                try:
                    page.set_cropbox(new_rect)
                except ValueError:
                    continue
        self.crop_rect = None
        self.crop_mode = False
        self.crop_toggle_btn.configure(text=self._t("crop_mode_off"), style="TButton")
        self.preview_canvas.configure(cursor="")
        self.crop_info_var.set(self._t("crop_no_sel"))
        self._invalidate_thumb_cache(targets)
        self._refresh_all()
        if len(targets) == 1:
            self._set_status(
                self._t("status_cropped").format(page=self.current_page + 1)
            )
            self.plugin_manager.fire_event("on_page_crop", self, self.current_page)
        else:
            self._set_status(self._t("status_bulk_cropped").format(count=len(targets)))
            self.plugin_manager.fire_event("on_page_crop", self, targets)

    # ── 挿入・結合 ──
    def _insert_from_file(self, mode="pos"):
        """別PDFから挿入。mode: 'head'=先頭, 'tail'=末尾, 'pos'=指定位置"""
        if not self._check_doc():
            return
        _supported_filter = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        _image_filter = " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title=self._t("dlg_insert_title"),
            filetypes=[
                (self._t("filetypes_supported"), _supported_filter),
                (self._t("filetypes_pdf"), "*.pdf"),
                (self._t("filetypes_image"), _image_filter),
                (self._t("filetypes_all"), "*.*"),
            ],
        )
        if not paths:
            return

        if mode == "head":
            insert_at = 0
        elif mode == "tail":
            insert_at = len(self.doc)
        else:
            pos = simpledialog.askinteger(
                self._t("dlg_insert_pos_title"),
                self._t("dlg_insert_pos_msg").format(n=len(self.doc)),
                minvalue=0,
                maxvalue=len(self.doc),
                initialvalue=self.current_page + 1,
            )
            if pos is None:
                return
            insert_at = pos

        if len(paths) > 1:
            from pagefolio.dialogs import MergeOrderDialog

            MergeOrderDialog(
                self.root,
                list(paths),
                lambda ordered: self._do_insert(ordered, insert_at),
                lang=self.lang,
            )
        else:
            self._do_insert(list(paths), insert_at)

    def _do_insert(self, ordered_paths, insert_at):
        """結合順確定後に実際の挿入を行う"""
        self._save_undo("insert", insert_at=insert_at)
        try:
            total = 0
            pos = insert_at
            for path in ordered_paths:
                src = self._open_path_as_pdf(path)
                self.doc.insert_pdf(src, start_at=pos)
                pos += len(src)
                total += len(src)
                src.close()
            self._undo_stack[-1]["data"][1] = total
            self._invalidate_thumb_cache()
            self._refresh_all()
            if insert_at == 0:
                where = self._t("status_insert_head")
            elif insert_at >= len(self.doc) - total:
                where = self._t("status_insert_tail")
            else:
                where = self._t("status_insert_pos").format(pos=insert_at)
            self._set_status(
                self._t("status_inserted").format(
                    count=len(ordered_paths), total=total, where=where
                )
            )
            self.plugin_manager.fire_event("on_insert", self, ordered_paths, insert_at)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _merge_pdf(self):
        if not self._check_doc():
            return
        paths = filedialog.askopenfilenames(
            title=self._t("dlg_merge_title"),
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")],
        )
        if not paths:
            return
        from pagefolio.dialogs import MergeOrderDialog

        MergeOrderDialog(self.root, list(paths), self._do_merge, lang=self.lang)

    def _merge_resize_pages(self):
        """選択ページを1枚に結合してリサイズする（例: 2× A4 → 1× A3）"""
        if not self._check_doc():
            return
        targets = sorted(self._get_targets())
        if len(targets) < 2:
            messagebox.showinfo(self._t("info_title"), self._t("info_merge_resize_min"))
            return

        page_infos = []
        for i in targets:
            r = self.doc[i].rect
            page_infos.append((i + 1, r.width, r.height))

        from pagefolio.dialogs import MergeResizeDialog

        MergeResizeDialog(
            self.root,
            page_infos,
            lambda direction, out_w, out_h: self._do_merge_resize(
                targets, direction, out_w, out_h
            ),
            lang=self.lang,
            font_func=self._font,
        )

    def _do_merge_resize(self, targets, direction, out_w, out_h):
        """結合・リサイズの実処理。targets は昇順のページインデックス。"""
        # Undo はスナップショット形式で保存（_restore_state が pdf_bytes を扱う）
        self._undo_stack.append(
            {
                "pdf_bytes": self.doc.tobytes(),
                "current_page": self.current_page,
                "selected_pages": set(self.selected_pages),
            }
        )
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

        try:
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=out_w, height=out_h)

            offset = 0.0
            for src_pno in targets:
                src_rect = self.doc[src_pno].rect
                if direction == "horizontal":
                    target_rect = fitz.Rect(
                        offset, 0, offset + src_rect.width, src_rect.height
                    )
                    offset += src_rect.width
                else:
                    target_rect = fitz.Rect(
                        0, offset, src_rect.width, offset + src_rect.height
                    )
                    offset += src_rect.height
                new_page.show_pdf_page(target_rect, self.doc, src_pno)

            insert_at = targets[0]
            self.doc.insert_pdf(new_doc, start_at=insert_at)
            new_doc.close()

            # 元ページは挿入により +1 シフトしているので +1 した位置を逆順削除
            for i in sorted(targets, reverse=True):
                self.doc.delete_page(i + 1)

            self.selected_pages = {insert_at}
            self.current_page = insert_at
            self._invalidate_thumb_cache()
            self._preview_gen += 1
            self._thumb_gen += 1
            self._refresh_all()
            self._set_status(
                self._t("status_merge_resize").format(
                    count=len(targets), w=int(out_w), h=int(out_h)
                )
            )
            self.plugin_manager.fire_event(
                "on_merge_resize", self, targets, direction, out_w, out_h
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _do_merge(self, ordered_paths):
        self._save_undo("merge")
        try:
            total = 0
            for path in ordered_paths:
                src = fitz.open(path)
                self.doc.insert_pdf(src)
                total += len(src)
                src.close()
            self._invalidate_thumb_cache()
            self._refresh_all()
            self._set_status(
                self._t("status_merged").format(count=len(ordered_paths), total=total)
            )
            self.plugin_manager.fire_event("on_merge", self, ordered_paths)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    # ── 分割 ──
    def _parse_page_ranges(self, text, max_page):
        """ページ範囲文字列をパースして [(start, end), ...] のリストを返す。
        ページ番号は1始まり、返り値も1始まり。無効時は None を返す。"""
        ranges = []
        text = text.strip()
        if not text:
            return None
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                tokens = part.split("-", 1)
                try:
                    s, e = int(tokens[0].strip()), int(tokens[1].strip())
                except ValueError:
                    return None
                if s < 1 or e < 1 or s > max_page or e > max_page or s > e:
                    return None
                ranges.append((s, e))
            else:
                try:
                    p = int(part)
                except ValueError:
                    return None
                if p < 1 or p > max_page:
                    return None
                ranges.append((p, p))
        return ranges if ranges else None

    def _check_split_overwrite(self, folder, filenames):
        """分割先に同名ファイルがあれば確認ダイアログを表示。続行ならTrue。"""
        existing = [f for f in filenames if os.path.exists(os.path.join(folder, f))]
        if not existing:
            return True
        names = "\n".join(existing[:10])
        if len(existing) > 10:
            names += f"\n… 他 {len(existing) - 10} ファイル"
        return messagebox.askyesno(
            self._t("split_overwrite_title"),
            self._t("split_overwrite_msg").format(files=names),
        )

    def _split_by_range(self):
        """ページ範囲を指定して分割保存"""
        if not self._check_doc():
            return
        n = len(self.doc)
        range_str = simpledialog.askstring(
            self._t("dlg_split_range_title"),
            self._t("dlg_split_range_msg").format(n=n),
        )
        if range_str is None:
            return
        if not range_str.strip():
            messagebox.showinfo(self._t("info_title"), self._t("err_split_no_range"))
            return
        ranges = self._parse_page_ranges(range_str, n)
        if ranges is None:
            messagebox.showerror(
                self._t("err_title"), self._t("err_split_range").format(n=n)
            )
            return
        folder = filedialog.askdirectory(title=self._t("dlg_split_save_dir"))
        if not folder:
            return
        base = "split"
        if self.doc.name:
            base = os.path.splitext(os.path.basename(self.doc.name))[0]
        try:
            filenames = []
            for _idx, (s, e) in enumerate(ranges, 1):
                if s == e:
                    filenames.append(f"{base}_p{s}.pdf")
                else:
                    filenames.append(f"{base}_p{s}-{e}.pdf")
            if not self._check_split_overwrite(folder, filenames):
                return
            compress = messagebox.askyesno(
                self._t("compress_split_confirm_title"),
                self._t("compress_split_confirm_msg"),
            )
            save_kwargs = {"garbage": 4, "deflate": 1, "clean": 1} if compress else {}
            for idx, (s, e) in enumerate(ranges):
                out = fitz.open()
                out.insert_pdf(self.doc, from_page=s - 1, to_page=e - 1)
                out_path = os.path.join(folder, filenames[idx])
                out.save(out_path, **save_kwargs)
                out.close()
            self._set_status(
                self._t("status_split_range").format(count=len(ranges), folder=folder)
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _split_each_page(self):
        """全ページを1ページずつ個別PDFに分割保存"""
        if not self._check_doc():
            return
        folder = filedialog.askdirectory(title=self._t("dlg_split_save_dir"))
        if not folder:
            return
        base = "split"
        if self.doc.name:
            base = os.path.splitext(os.path.basename(self.doc.name))[0]
        n = len(self.doc)
        digits = len(str(n))
        try:
            filenames = [f"{base}_p{str(i + 1).zfill(digits)}.pdf" for i in range(n)]
            if not self._check_split_overwrite(folder, filenames):
                return
            compress = messagebox.askyesno(
                self._t("compress_split_confirm_title"),
                self._t("compress_split_confirm_msg"),
            )
            save_kwargs = {"garbage": 4, "deflate": 1, "clean": 1} if compress else {}
            for i in range(n):
                out = fitz.open()
                out.insert_pdf(self.doc, from_page=i, to_page=i)
                out_path = os.path.join(folder, filenames[i])
                out.save(out_path, **save_kwargs)
                out.close()
            self._set_status(
                self._t("status_split_each").format(count=n, folder=folder)
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))
