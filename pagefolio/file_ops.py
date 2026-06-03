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
        elif op == "merge_resize":
            # data = {"insert_at": int, "merged_bytes": bytes,
            #         "orig_pages": [(idx, bytes)]}
            state["data"] = kwargs["data"]
        self._undo_stack.append(state)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack:
            self._set_status(self._t("undo_empty"))
            return
        state = self._undo_stack.pop()
        inverse = self._restore_state(state)
        self._redo_stack.append(inverse)
        self._set_status(self._t("undo_done"))

    def _redo(self):
        if not self._redo_stack:
            self._set_status(self._t("redo_empty"))
            return
        state = self._redo_stack.pop()
        inverse = self._restore_state(state)
        self._undo_stack.append(inverse)
        self._set_status(self._t("redo_done"))

    def _apply_inverse(self, state):
        """現在の doc 状態から逆デルタを構築して返す。
        _restore_state 内で逆操作を適用する直前に呼ぶ。
        返り値は pdf_bytes キーを持たない op 別 state dict。
        """
        op = state["op"]
        inv = {
            "op": op,
            "current_page": self.current_page,
            "selected_pages": set(self.selected_pages),
        }
        if op == "rotate":
            # 適用前の現在の rotation を逆デルタに格納
            inv["data"] = [
                (page_i, self.doc[page_i].rotation) for page_i, _ in state["data"]
            ]
        elif op == "crop":
            page_i, _ = state["data"]
            cb = self.doc[page_i].cropbox
            inv["data"] = (page_i, (cb.x0, cb.y0, cb.x1, cb.y1))
        elif op == "delete":
            # delete の逆（undo 後に redo するための逆デルタ）:
            # _restore_state(delete) は insert を実行（undo = 削除ページを復元）。
            # redo 用には「復元されたページを再削除」する情報が必要。
            # op="delete_redo": 現在（挿入済み）のページ bytes をキャプチャして保存。
            captured = []
            for page_i, _ in state["data"]:
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=page_i, to_page=page_i)
                captured.append((page_i, tmp.tobytes()))
                tmp.close()
            inv["op"] = "delete_redo"
            inv["data"] = captured
        elif op == "delete_redo":
            # delete_redo の逆（redo 後に undo するため）:
            # _restore_state(delete_redo) は delete を実行する。
            # その逆は「削除ページを復元（insert）」= delete op として bytes を返す。
            captured = []
            for page_i, _ in state["data"]:
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=page_i, to_page=page_i)
                captured.append((page_i, tmp.tobytes()))
                tmp.close()
            inv["op"] = "delete"
            inv["data"] = captured
        elif op == "move":
            # move の逆: move_page(src, dest) の逆順列を計算して bulk_move で逆操作。
            # move_page の順列を計算し、逆順列を doc.select() で適用する。
            src, actual_dest = state["data"]
            n = len(self.doc)
            order = list(range(n))
            item = order.pop(src)
            if src < actual_dest:
                order.insert(actual_dest - 1, item)
            else:
                order.insert(actual_dest, item)
            inverse_order = [0] * n
            for i, v in enumerate(order):
                inverse_order[v] = i
            inv["op"] = "bulk_move"
            inv["data"] = inverse_order
        elif op == "duplicate":
            inv["data"] = state["data"] + 1  # 複製ページのインデックス（削除対象）
            inv["op"] = "duplicate_undo"
        elif op == "duplicate_undo":
            # duplicate_undo の逆は duplicate（再複製）
            inv["data"] = state["data"] - 1
            inv["op"] = "duplicate"
        elif op == "bulk_move":
            new_order = state["data"]
            inverse_order = [0] * len(new_order)
            for i, v in enumerate(new_order):
                inverse_order[v] = i
            inv["data"] = inverse_order
        elif op == "bulk_crop":
            # 適用前の現在の cropbox を逆デルタに格納
            inv["data"] = [
                (
                    page_i,
                    (
                        self.doc[page_i].cropbox.x0,
                        self.doc[page_i].cropbox.y0,
                        self.doc[page_i].cropbox.x1,
                        self.doc[page_i].cropbox.y1,
                    ),
                )
                for page_i, _ in state["data"]
            ]
        elif op == "insert":
            # insert の逆: 挿入されたページを bytes でキャプチャして delete 形式に変換
            # （Task 2 で完全実装。本タスクでは insert はページ増減系のため仮実装）
            insert_at, num = state["data"]
            captured = []
            for i in range(insert_at, insert_at + num):
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=i, to_page=i)
                captured.append((i, tmp.tobytes()))
                tmp.close()
            inv["op"] = "insert_undo"
            inv["data"] = captured
        elif op == "insert_undo":
            # insert_undo の逆は insert（bytes を再挿入）
            inv["op"] = "insert_redo"
            inv["data"] = state["data"]
        elif op == "insert_redo":
            insert_at = state["data"][0][0] if state["data"] else 0
            num = len(state["data"])
            captured = []
            for i in range(insert_at, insert_at + num):
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=i, to_page=i)
                captured.append((i, tmp.tobytes()))
                tmp.close()
            inv["op"] = "insert_undo"
            inv["data"] = captured
        elif op == "merge":
            # merge の逆: 追加されたページを bytes でキャプチャ（Task 2 で完全実装）
            old_count = state["data"]
            captured = []
            for i in range(old_count, len(self.doc)):
                tmp = fitz.open()
                tmp.insert_pdf(self.doc, from_page=i, to_page=i)
                captured.append((i, tmp.tobytes()))
                tmp.close()
            inv["op"] = "merge_undo"
            inv["data"] = (old_count, captured)
        elif op == "merge_undo":
            old_count, captured = state["data"]
            inv["op"] = "merge"
            inv["data"] = old_count
        elif op == "merge_resize":
            # merge_resize の逆: 結合ページを除去し元ページを復元するための逆デルタ
            # 逆デルタ = merge_resize_undo（結合ページ削除 + 元ページ再挿入）
            inv["op"] = "merge_resize_undo"
            inv["data"] = state["data"]
        elif op == "merge_resize_undo":
            # merge_resize_undo の逆: 元ページを削除し結合ページを再挿入
            inv["op"] = "merge_resize"
            inv["data"] = state["data"]
        else:
            # 未知の op はそのまま返す（安全フォールバック）
            inv["data"] = state.get("data")
        return inv

    def _restore_state(self, state):
        """op 別逆操作を適用し、逆方向へ戻すための op 別 state（逆デルタ）を返す。
        pdf_bytes キーは一切使用しない（D-05）。
        """
        op = state["op"]
        # 適用前の状態から逆デルタを構築
        inverse = self._apply_inverse(state)

        if op == "rotate":
            for page_i, old_rot in state["data"]:
                self.doc[page_i].set_rotation(old_rot)
        elif op == "crop":
            page_i, (x0, y0, x1, y1) = state["data"]
            self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        elif op == "delete":
            # undo: 昇順で再挿入（インデックスずれ防止）
            for page_i, page_bytes in state["data"]:
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "delete_redo":
            # redo: 昇順インデックスのページを逆順で削除（インデックスずれ防止）
            targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
            for page_i in targets:
                self.doc.delete_page(page_i)
        elif op == "move":
            # undo: move_page(src, dest) の逆順列を doc.select() で元の順序に戻す。
            src, actual_dest = state["data"]
            n = len(self.doc)
            # move_page(src, dest) の結果の順列を計算
            order = list(range(n))
            item = order.pop(src)
            if src < actual_dest:
                order.insert(actual_dest - 1, item)
            else:
                order.insert(actual_dest, item)
            # 逆順列: order[i] = j → inverse[j] = i
            inverse_order = [0] * n
            for i, v in enumerate(order):
                inverse_order[v] = i
            self.doc.select(inverse_order)
        elif op == "duplicate":
            self.doc.delete_page(state["data"] + 1)
        elif op == "duplicate_undo":
            # duplicate_undo: インデックスを再複製
            pno = state["data"] - 1
            tmp = fitz.open()
            tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
            self.doc.insert_pdf(tmp, start_at=pno + 1)
            tmp.close()
        elif op == "insert":
            insert_at, num = state["data"]
            for _ in range(num):
                self.doc.delete_page(insert_at)
        elif op == "insert_undo":
            # insert_undo: キャプチャした bytes を昇順で再挿入
            for page_i, page_bytes in state["data"]:
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "insert_redo":
            # insert_redo: 再挿入後にそのページを削除（insert の再実行相当）
            for page_i, page_bytes in state["data"]:
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "merge":
            old_count = state["data"]
            while len(self.doc) > old_count:
                self.doc.delete_page(old_count)
        elif op == "merge_undo":
            # merge_undo: キャプチャした bytes を昇順で再追加
            old_count, captured = state["data"]
            for page_i, page_bytes in captured:
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "merge_resize":
            # merge_resize の undo: 結合ページを削除し元ページを復元
            d = state["data"]
            insert_at = d["insert_at"]
            # 結合ページを削除
            self.doc.delete_page(insert_at)
            # 元ページを昇順で再挿入
            for idx, page_bytes in sorted(d["orig_pages"], key=lambda x: x[0]):
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=idx)
                tmp.close()
        elif op == "merge_resize_undo":
            # merge_resize_undo の実行: 元ページを削除し結合ページを再挿入（redo）
            d = state["data"]
            insert_at = d["insert_at"]
            # 元ページ（昇順インデックス）を逆順で削除してから結合ページを挿入
            orig_indices = sorted([idx for idx, _ in d["orig_pages"]], reverse=True)
            for idx in orig_indices:
                self.doc.delete_page(idx)
            tmp = fitz.open(stream=d["merged_bytes"], filetype="pdf")
            self.doc.insert_pdf(tmp, start_at=insert_at)
            tmp.close()
        elif op == "bulk_move":
            new_order = state["data"]
            inverse_order = [0] * len(new_order)
            for i, v in enumerate(new_order):
                inverse_order[v] = i
            self.doc.select(inverse_order)
        elif op == "bulk_crop":
            for page_i, (x0, y0, x1, y1) in state["data"]:
                self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))

        self.current_page = min(state["current_page"], max(0, len(self.doc) - 1))
        self.selected_pages = state["selected_pages"]
        self._invalidate_thumb_cache()
        self._preview_gen += 1
        self._thumb_gen += 1
        self._refresh_all()
        return inverse

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
            self.doc = self._open_path_as_pdf(path)
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
