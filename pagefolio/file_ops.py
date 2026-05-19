# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ファイル操作 Mixin — open/save/undo/redo"""

import logging
import os
from tkinter import filedialog, messagebox

import fitz

from pagefolio.constants import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class FileOpsMixin:
    """PDFEditorApp のファイル操作・Undo/Redo メソッド群"""

    # ══════════════════════════════════════════
    #  Undo / Redo
    # ══════════════════════════════════════════
    def _save_undo(self, op, **kwargs):
        if not self.doc:
            return
        state = {
            "op": op,
            "current_page": self.current_page,
            "selected_pages": set(self.selected_pages),
        }
        if op == "rotate":
            state["data"] = [(i, self.doc[i].rotation) for i in kwargs["targets"]]
        elif op == "crop":
            page_i = kwargs["page_i"]
            cb = self.doc[page_i].cropbox
            state["data"] = (page_i, (cb.x0, cb.y0, cb.x1, cb.y1))
        elif op == "delete":
            targets = sorted(kwargs["targets"])
            data = []
            for i in targets:
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=i, to_page=i)
                data.append((i, tmp.tobytes()))
                tmp.close()
            state["data"] = data
        elif op == "move":
            state["data"] = (kwargs["src"], kwargs["actual_dest"])
        elif op == "duplicate":
            state["data"] = kwargs["pno"]
        elif op == "insert":
            state["data"] = [kwargs["insert_at"], 0]
        elif op == "merge":
            state["data"] = len(self.doc)
        elif op == "bulk_move":
            state["data"] = kwargs["new_order"]  # 整数リスト
        elif op == "bulk_crop":
            state["data"] = kwargs["crop_data"]  # [(page_i, (x0,y0,x1,y1)), ...]
        self._undo_stack.append(state)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack:
            self._set_status(self._t("undo_empty"))
            return
        if self.doc:
            self._redo_stack.append(
                {
                    "pdf_bytes": self.doc.tobytes(),
                    "current_page": self.current_page,
                    "selected_pages": set(self.selected_pages),
                }
            )
        state = self._undo_stack.pop()
        self._restore_state(state)
        self._set_status(self._t("undo_done"))

    def _redo(self):
        if not self._redo_stack:
            self._set_status(self._t("redo_empty"))
            return
        if self.doc:
            self._undo_stack.append(
                {
                    "pdf_bytes": self.doc.tobytes(),
                    "current_page": self.current_page,
                    "selected_pages": set(self.selected_pages),
                }
            )
        state = self._redo_stack.pop()
        self._restore_state(state)
        self._set_status(self._t("redo_done"))

    def _restore_state(self, state):
        if "pdf_bytes" in state:
            # 旧来形式（Redo スタック由来）またはフォールバック
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(stream=state["pdf_bytes"], filetype="pdf")
        else:
            op = state["op"]
            if op == "rotate":
                for page_i, old_rot in state["data"]:
                    self.doc[page_i].set_rotation(old_rot)
            elif op == "crop":
                page_i, (x0, y0, x1, y1) = state["data"]
                self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
            elif op == "delete":
                # 昇順で再挿入（インデックスずれ防止）
                for page_i, page_bytes in state["data"]:
                    tmp = fitz.open(stream=page_bytes, filetype="pdf")
                    self.doc.insert_pdf(tmp, start_at=page_i)
                    tmp.close()
            elif op == "move":
                src, actual_dest = state["data"]
                self.doc.move_page(actual_dest, src)
            elif op == "duplicate":
                self.doc.delete_page(state["data"] + 1)
            elif op == "insert":
                insert_at, num = state["data"]
                for _ in range(num):
                    self.doc.delete_page(insert_at)
            elif op == "merge":
                old_count = state["data"]
                while len(self.doc) > old_count:
                    self.doc.delete_page(old_count)
            elif op == "bulk_move":
                new_order = state["data"]
                inverse = [0] * len(new_order)
                for i, v in enumerate(new_order):
                    inverse[v] = i
                self.doc.select(inverse)
            elif op == "bulk_crop":
                for page_i, (x0, y0, x1, y1) in state["data"]:
                    self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))

        self.current_page = min(state["current_page"], max(0, len(self.doc) - 1))
        self.selected_pages = state["selected_pages"]
        self._invalidate_thumb_cache()
        self._preview_gen += 1
        self._thumb_gen += 1
        self._refresh_all()

    # ══════════════════════════════════════════
    #  ファイル操作
    # ══════════════════════════════════════════
    def _open_file(self):
        _supported_filter = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        _image_filter = " ".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            filetypes=[
                (self._t("filetypes_supported"), _supported_filter),
                (self._t("filetypes_pdf"), "*.pdf"),
                (self._t("filetypes_image"), _image_filter),
                (self._t("filetypes_all"), "*.*"),
            ]
        )
        if not paths:
            return
        if len(paths) == 1:
            self._open_pdf_path(paths[0])
        else:
            self._open_multiple_pdfs(list(paths))

    def _open_multiple_pdfs(self, paths):
        """複数PDFを結合して1つのドキュメントとして開く"""
        from pagefolio.dialogs import MergeOrderDialog

        MergeOrderDialog(self.root, paths, self._do_open_merged, lang=self.lang)

    def _open_path_as_pdf(self, path):
        """ファイルをPDF互換のDocumentとして開く。画像の場合はPDFに変換する。"""
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            img_doc = fitz.open(path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()
            return fitz.open(stream=pdf_bytes, filetype="pdf")
        return fitz.open(path)

    def _do_open_merged(self, ordered_paths):
        """結合順ダイアログ確定後、結合して開く"""
        try:
            if self.doc:
                self.doc.close()
            merged = fitz.open()
            total = 0
            for path in ordered_paths:
                src = self._open_path_as_pdf(path)
                merged.insert_pdf(src)
                total += len(src)
                src.close()
            self.doc = merged
            self.filepath = None
            self.current_page = 0
            self.selected_pages.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._invalidate_thumb_cache()
            self._preview_gen += 1
            self._thumb_gen += 1
            self._refresh_all()
            names = ", ".join(os.path.basename(p) for p in ordered_paths)
            self._set_status(
                self._t("status_merged_open").format(
                    count=len(ordered_paths), total=total, names=names
                )
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _open_pdf_path(self, path):
        """パス指定でPDFを開く（ダイアログ / D&D 共用）"""
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(path)
            self.filepath = path
            self.current_page = 0
            self.selected_pages.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._invalidate_thumb_cache()
            self._preview_gen += 1
            self._thumb_gen += 1
            self._refresh_all()
            ext = os.path.splitext(path)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                self._set_status(
                    self._t("status_opened_image").format(name=os.path.basename(path))
                )
            else:
                self._set_status(
                    self._t("status_opened").format(
                        name=os.path.basename(path), n=len(self.doc)
                    )
                )
            self.plugin_manager.fire_event("on_file_open", self, path)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _save_file(self):
        """上書き保存 — 確認ダイアログ付き"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        if not self.filepath:
            self._save_as()
            return
        ext = os.path.splitext(self.filepath)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            self._set_status(self._t("status_image_save_as"))
            self._save_as()
            return
        if not messagebox.askyesno(
            self._t("save_confirm_title"),
            self._t("save_confirm_msg").format(name=os.path.basename(self.filepath)),
        ):
            return
        try:
            try:
                self.doc.save(
                    self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP
                )
            except Exception as e:
                logger.debug("incremental save 失敗、tmp ファイル経由で保存: %s", e)
                tmp = self.filepath + ".tmp"
                self.doc.save(tmp)
                os.replace(tmp, self.filepath)
            self._set_status(
                self._t("status_saved").format(name=os.path.basename(self.filepath))
            )
            self.plugin_manager.fire_event("on_file_save", self, self.filepath)
        except Exception as e:
            messagebox.showerror(
                self._t("err_save_title"), self._t("err_save_msg").format(e=e)
            )

    def _save_as(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")],
        )
        if not path:
            return
        try:
            self.doc.save(path)
            self.filepath = path
            self._set_status(
                self._t("status_saved").format(name=os.path.basename(path))
            )
            self.plugin_manager.fire_event("on_file_save", self, path)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _close_file(self):
        """現在開いているファイルを閉じる（アプリは終了しない）"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        if not messagebox.askyesno(self._t("confirm_title"), self._t("close_confirm")):
            return
        try:
            self.doc.close()
        except Exception as e:
            logger.debug("doc.close 失敗: %s", e)
        self.doc = None
        self.filepath = None
        self.current_page = 0
        self.selected_pages.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._invalidate_thumb_cache()
        self._preview_gen += 1
        self._thumb_gen += 1
        self._refresh_all()
        self._set_status(self._t("status_closed"))
        self.plugin_manager.fire_event("on_file_close", self)

    def _save_compressed(self):
        """縮小最適化して名前を付けて保存（garbage=4, deflate=1, clean=1）"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")],
        )
        if not path:
            return
        try:
            self.doc.save(path, garbage=4, deflate=1, clean=1)
            self._set_status(
                self._t("status_compressed").format(name=os.path.basename(path))
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))
