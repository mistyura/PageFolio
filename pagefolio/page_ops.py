# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ページ操作 Mixin — 回転・削除・トリミング・挿入・結合・分割"""

import os
from tkinter import filedialog, messagebox, simpledialog

import fitz

from pagefolio.constants import (
    DEFAULT_EXPORT_JPG_QUALITY,
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    C,
)


def parse_page_ranges(text, max_page):
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


def compute_export_scale(width_pt, height_pt, target_long_px):
    """ページ寸法(pt)と目標長辺ピクセル数からレンダリング倍率を計算する"""
    long_edge = max(width_pt, height_pt)
    if long_edge <= 0 or target_long_px <= 0:
        return 1.0
    return target_long_px / long_edge


def export_page_image(
    page, out_path, target_long_px, fmt="png", jpg_quality=DEFAULT_EXPORT_JPG_QUALITY
):
    """fitz.Page を画像ファイルとして保存する。

    page.rect（CropBox・回転反映後の表示矩形）の長辺が target_long_px に
    なるよう倍率を計算してレンダリングするため、アプリ内で編集した
    トリミング・回転の結果がそのまま画像に反映される。
    注意: fitz.Page にアクセスするためメインスレッドで呼び出すこと。
    """
    scale = compute_export_scale(page.rect.width, page.rect.height, target_long_px)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    if fmt == "jpg":
        pix.save(out_path, jpg_quality=jpg_quality)
    else:
        pix.save(out_path)


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
        # H1 即時反映（V16-QUAL-01 / 真因 a・セレクション意味論）:
        # プレビューは常に current_page を描画するため、回転対象 targets に
        # current_page が含まれない場合（Ctrl+クリックで current 以外を選択）、
        # 回転後もプレビューが回転対象外のページを表示し続け「回らない」ように
        # 見える。current を回転対象の代表（昇順の先頭）へ寄せ、回転結果が
        # 即座にプレビューへ反映されるようにする。3 ステップ順序
        # （回転適用 → _invalidate_thumb_cache → _refresh_all）と
        # _refresh_all 内の reconcile_window_start 窓正規化は温存する。
        if targets and self.current_page not in targets:
            self.current_page = min(targets)
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

        # Clean up TOC (remove entries pointing to deleted pages)
        toc = self.doc.get_toc()
        new_toc = [item for item in toc if item[2] != -1]
        if len(new_toc) != len(toc):
            self.doc.set_toc(new_toc)

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

    def _insert_blank_page(self):
        """アクティブページの直後に白紙ページを挿入する"""
        if not self._check_doc():
            return
        pno = self.current_page
        self._save_undo("insert_blank", pno=pno)
        try:
            page = self.doc[pno]
            w, h = page.rect.width, page.rect.height
            self.doc.new_page(pno + 1, width=w, height=h)
            self._invalidate_thumb_cache()
            self.current_page = pno + 1
            self._refresh_all()
            self._set_status(
                self._t("status_duplicated")
                .replace("p.{page} を複製", "白紙ページ")
                .replace("Duplicated p.{page} and ", "Blank page ")
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _add_watermark_text(self):
        """選択ページにテキスト透かしを追加する"""
        if not self._check_doc():
            return
        targets = self._get_targets()
        text = simpledialog.askstring(
            self._t("btn_watermark"),
            "透かしテキストを入力してください:\n(例: CONFIDENTIAL, 社外秘)",
            parent=self.root,
        )
        if not text:
            return
        self._save_undo("watermark", targets=targets)
        for i in targets:
            page = self.doc[i]
            rect = page.rect
            center_p = fitz.Point(rect.width / 2 - len(text) * 10, rect.height / 2)
            page.insert_text(
                center_p,
                text,
                fontsize=48,
                fontname="helv",
                color=(0.8, 0.8, 0.8),
                fill_opacity=0.5,
                rotate=45,
                overlay=True,
            )
        self._invalidate_thumb_cache(targets)
        self._refresh_all()
        self._set_status(f"透かしを追加しました ({len(targets)} ページ)")

    def _add_page_numbers(self):
        """選択ページにページ番号を印字する"""
        if not self._check_doc():
            return
        targets = self._get_targets()
        self._save_undo("page_numbers", targets=targets)
        total = len(self.doc)
        for _idx, i in enumerate(targets):
            page = self.doc[i]
            rect = page.rect
            text = f"{i + 1} / {total}"
            p = fitz.Point(rect.width - 60, rect.height - 30)
            page.insert_text(p, text, fontsize=12, fontname="helv", color=(0, 0, 0))
        self._invalidate_thumb_cache(targets)
        self._refresh_all()
        self._set_status(f"ページ番号を印字しました ({len(targets)} ページ)")

    # ── トリミング ──
    def _toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            # 黒塗りモードとは相互排他（redact_ops.py 側と対）
            self._redact_mode_off()
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

    def _canvas_rect_to_pdf(self, sx, sy, ex, ey):
        """プレビューキャンバス座標の矩形を PDF 点座標（page 左上原点）へ変換する。

        プレビューは self.zoom * 1.5 倍で描画され、画像はキャンバス上で
        pad=10 オフセットされている（viewer.py の _show_preview と対応）。
        トリミング・黒塗り・モザイクの矩形選択が共用する。
        """
        scale = self.zoom * 1.5
        img_offset = 10
        return (
            (sx - img_offset) / scale,
            (sy - img_offset) / scale,
            (ex - img_offset) / scale,
            (ey - img_offset) / scale,
        )

    def _crop_drag_start(self, event):
        # 矩形選択はトリミングと黒塗り/モザイクで共用する
        if not (self.crop_mode or self.redact_mode):
            return
        cx = self.preview_canvas.canvasx(event.x)
        cy = self.preview_canvas.canvasy(event.y)
        self.crop_drag_start = (cx, cy)
        self.crop_rect = None
        self._clear_crop_overlay()

    def _crop_drag_move(self, event):
        if not (self.crop_mode or self.redact_mode) or not self.crop_drag_start:
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
        fx0, fy0, fx1, fy1 = self._canvas_rect_to_pdf(sx, sy, ex, ey)
        px0, py0, px1, py1 = int(fx0), int(fy0), int(fx1), int(fy1)
        self.crop_info_var.set(
            f"({px0},{py0}) - ({px1},{py1})  {px1 - px0}×{py1 - py0} pt"
        )

    def _crop_drag_end(self, event):
        if not (self.crop_mode or self.redact_mode):
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
            x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._canvas_rect_to_pdf(*self.crop_rect)
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
            x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._canvas_rect_to_pdf(*self.crop_rect)
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
            # 例外時は num=0 のままの不完全な insert state を破棄する。
            # 残すと undo が range(0) で 1 ページも削除せず、部分挿入が取り残される。
            if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
                self._undo_stack.pop()
            self._invalidate_thumb_cache()
            self._refresh_all()
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
        try:
            # 結合ページを生成（まだ doc には挿入しない）
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

            # 元ページと結合ページの bytes をキャプチャして op 別デルタで保存（D-05）
            insert_at = targets[0]
            orig_pages = []
            for idx in sorted(targets):
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=idx, to_page=idx)
                orig_pages.append((idx, tmp.tobytes()))
                tmp.close()
            merged_bytes = new_doc.tobytes()
            new_doc.close()

            self._save_undo(
                "merge_resize",
                data={
                    "insert_at": insert_at,
                    "merged_bytes": merged_bytes,
                    "orig_pages": orig_pages,
                },
            )

            # 結合ページを挿入
            merged_doc = fitz.open(stream=merged_bytes, filetype="pdf")
            self.doc.insert_pdf(merged_doc, start_at=insert_at)
            merged_doc.close()

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
                current_toc = self.doc.get_toc()
                page_offset = len(self.doc)
                src_toc = src.get_toc()
                for item in src_toc:
                    item[2] += page_offset

                self.doc.insert_pdf(src)
                self.doc.set_toc(current_toc + src_toc)

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
        return parse_page_ranges(text, max_page)

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

                # TOCの切り出しとページ番号のシフト
                current_toc = self.doc.get_toc()
                new_toc = []
                for item in current_toc:
                    lvl, title, pno = item[:3]
                    if s <= pno <= e:
                        new_toc.append([lvl, title, pno - s + 1] + item[3:])
                if new_toc:
                    out.set_toc(new_toc)

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

                # TOCの切り出し
                current_toc = self.doc.get_toc()
                new_toc = []
                for item in current_toc:
                    lvl, title, pno = item[:3]
                    if pno == i + 1:
                        new_toc.append([lvl, title, 1] + item[3:])
                if new_toc:
                    out.set_toc(new_toc)

                out_path = os.path.join(folder, filenames[i])
                out.save(out_path, **save_kwargs)
                out.close()
            self._set_status(
                self._t("status_split_each").format(count=n, folder=folder)
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    # ── 画像エクスポート ──
    def _export_pages_as_images(self):
        """ページを画像ファイル（1ページ1ファイル）に変換するダイアログを開く"""
        if not self._check_doc():
            return
        from pagefolio.dialogs import ExportImagesDialog

        ExportImagesDialog(
            self.root,
            total_pages=len(self.doc),
            selected_count=len(self.selected_pages),
            callback=self._do_export_images,
            lang=self.lang,
        )

    def _resolve_export_pages(self, options):
        """エクスポート対象の 0 始まりページインデックスを昇順リストで返す"""
        scope = options["scope"]
        if scope == "selected":
            return sorted(self.selected_pages)
        if scope == "range":
            pages = set()
            for s, e in options["ranges"]:
                pages.update(range(s - 1, e))
            return sorted(pages)
        return list(range(len(self.doc)))

    def _do_export_images(self, options):
        """ExportImagesDialog 確定後の画像変換処理（メインスレッドで実行）"""
        if not self.doc:
            return
        pages = self._resolve_export_pages(options)
        if not pages:
            messagebox.showinfo(self._t("info_title"), self._t("export_no_pages"))
            return
        folder = filedialog.askdirectory(title=self._t("dlg_export_save_dir"))
        if not folder:
            return
        base = "page"
        if self.doc.name:
            base = os.path.splitext(os.path.basename(self.doc.name))[0]
        ext = "jpg" if options["fmt"] == "jpg" else "png"
        digits = len(str(len(self.doc)))
        filenames = [f"{base}_p{str(p + 1).zfill(digits)}.{ext}" for p in pages]
        if not self._check_split_overwrite(folder, filenames):
            return
        total = len(pages)
        try:
            for k, p in enumerate(pages):
                export_page_image(
                    self.doc[p],
                    os.path.join(folder, filenames[k]),
                    options["long_px"],
                    fmt=options["fmt"],
                    jpg_quality=options.get("quality", DEFAULT_EXPORT_JPG_QUALITY),
                )
                self._set_status(
                    self._t("status_exporting").format(done=k + 1, total=total)
                )
                self.root.update_idletasks()
            self._set_status(
                self._t("status_exported").format(count=total, folder=folder)
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))
