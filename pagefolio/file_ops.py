# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ファイル操作 Mixin — open/save/undo/redo"""

import logging
import os
from tkinter import filedialog, messagebox

import fitz

logger = logging.getLogger(__name__)


class FileOpsMixin:
    """PDFEditorApp のファイル操作・Undo/Redo メソッド群"""

    # ══════════════════════════════════════════
    #  Undo / Redo
    # ══════════════════════════════════════════
    def _save_undo(self):
        if not self.doc:
            return
        state = {
            "pdf_bytes": self.doc.tobytes(),
            "current_page": self.current_page,
            "selected_pages": set(self.selected_pages),
        }
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
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(stream=state["pdf_bytes"], filetype="pdf")
        self.current_page = min(state["current_page"], max(0, len(self.doc) - 1))
        self.selected_pages = state["selected_pages"]
        self._invalidate_thumb_cache()
        self._refresh_all()

    # ══════════════════════════════════════════
    #  ファイル操作
    # ══════════════════════════════════════════
    def _open_file(self):
        paths = filedialog.askopenfilenames(
            filetypes=[
                (self._t("filetypes_pdf"), "*.pdf"),
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

    def _do_open_merged(self, ordered_paths):
        """結合順ダイアログ確定後、結合して開く"""
        try:
            if self.doc:
                self.doc.close()
            merged = fitz.open()
            total = 0
            for path in ordered_paths:
                src = fitz.open(path)
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
            self._refresh_all()
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
