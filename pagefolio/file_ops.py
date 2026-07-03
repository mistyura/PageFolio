# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ファイル操作 Mixin — open/save/undo/redo"""

import logging
import os
from tkinter import filedialog, messagebox, simpledialog

import fitz

from pagefolio.constants import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class PDFPasswordError(Exception):
    """パスワード付き PDF の認証がキャンセル/失敗したことを表す例外。"""


def save_with_password(doc, path, password):
    """doc を AES-256 で暗号化し、owner/user 両方に password を設定して保存する。"""
    doc.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw=password,
        user_pw=password,
    )


def save_without_password(doc, path):
    """doc を暗号化なし（パスワード解除済み）で保存する。"""
    doc.save(path, encryption=fitz.PDF_ENCRYPT_NONE)


class FileOpsMixin:
    """PDFEditorApp のファイル操作・Undo/Redo メソッド群"""

    # ══════════════════════════════════════════
    #  Undo / Redo
    # ══════════════════════════════════════════
    def _get_undo_store(self):
        """undo デルタ用 Blob ストアを返す（遅延生成）。

        遅延生成のため、__init__ を通らないテスト用フェイクでも
        そのまま動作する。
        """
        store = getattr(self, "_undo_blob_store", None)
        if store is None:
            from pagefolio.undo_store import UndoBlobStore

            store = UndoBlobStore()
            self._undo_blob_store = store
        return store

    def _capture_page_blob(self, page_i):
        """page_i の 1 ページを単独 PDF として Blob 化して返す。

        delete / insert / merge / page_edit 系デルタの共有キャプチャ経路。
        64KiB 以上はディスク退避（FileBlob）、未満はメモリ保持（MemBlob）。
        """
        tmp = fitz.open()
        tmp.insert_pdf(self.doc, from_page=page_i, to_page=page_i)
        data = tmp.tobytes()
        tmp.close()
        return self._get_undo_store().put(data)

    @staticmethod
    def _blob_bytes(data):
        """Blob（load() を持つ）または生 bytes からページ bytes を取り出す。

        既存テスト・プラグイン等が生 bytes を state に入れても動く後方互換層。
        """
        return data.load() if hasattr(data, "load") else data

    def _dispose_state(self, state):
        """state 内の Blob を解放する（evict・redo クリア・消費時に呼ぶ）。

        生 bytes（Blob でない値）は無視する（後方互換）。
        """

        def _release(x):
            if hasattr(x, "release"):
                x.release()

        op = state.get("op")
        data = state.get("data")
        if data is None:
            return
        if op in ("delete", "delete_redo", "page_edit", "insert_undo", "insert_redo"):
            for _i, blob in data:
                _release(blob)
        elif op == "merge_undo":
            _old_count, captured = data
            for _i, blob in captured:
                _release(blob)
        elif op in ("merge_resize", "merge_resize_undo"):
            _release(data.get("merged_bytes"))
            for _i, blob in data.get("orig_pages", []):
                _release(blob)

    def _push_evicting(self, stack, state):
        """deque へ push する前に、溢れて evict される最古 state を解放する。

        deque(maxlen) の自動 evict は要素を黙って捨てるため、FileBlob の
        一時ファイルが残ってしまう。append 前にフックして解放する。
        maxlen が None のスタック（テスト用フェイク等）では何もしない。
        """
        if stack.maxlen is not None and len(stack) == stack.maxlen and stack:
            self._dispose_state(stack[0])
        stack.append(state)

    def _clear_redo_stack(self):
        """redo スタックを Blob 解放付きでクリアする。"""
        for st in self._redo_stack:
            self._dispose_state(st)
        self._redo_stack.clear()

    def _clear_undo_stacks(self):
        """undo/redo 両スタックを Blob 解放付きでクリアし、ストアを purge する。

        ファイルオープン / クローズ / アプリ終了時に呼ぶ。
        """
        for st in list(self._undo_stack) + list(self._redo_stack):
            self._dispose_state(st)
        self._undo_stack.clear()
        self._redo_stack.clear()
        store = getattr(self, "_undo_blob_store", None)
        if store is not None:
            store.purge()

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
            state["data"] = [
                (i, self._capture_page_blob(i)) for i in sorted(kwargs["targets"])
            ]
        elif op == "page_edit":
            # ページ内容の破壊的編集（黒塗り・モザイク等）: 適用前のページを
            # bytes でキャプチャする。ページ数不変・対称 op（対 op 不要）
            state["data"] = [
                (i, self._capture_page_blob(i)) for i in sorted(kwargs["targets"])
            ]
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
            # data = {"insert_at": int, "merged_bytes": bytes|Blob,
            #         "orig_pages": [(idx, bytes|Blob)]}
            state["data"] = kwargs["data"]
        self._push_evicting(self._undo_stack, state)
        self._clear_redo_stack()

    def _undo(self):
        if not self._undo_stack:
            self._set_status(self._t("undo_empty"))
            return
        state = self._undo_stack.pop()
        inverse = self._restore_state(state)
        # 消費済み state の Blob を解放する。ただし逆デルタが同一 data を
        # 共有する op（insert_undo→insert_redo / merge_resize 系）は解放しない
        if inverse.get("data") is not state.get("data"):
            self._dispose_state(state)
        self._push_evicting(self._redo_stack, inverse)
        self._set_status(self._t("undo_done"))

    def _redo(self):
        if not self._redo_stack:
            self._set_status(self._t("redo_empty"))
            return
        state = self._redo_stack.pop()
        inverse = self._restore_state(state)
        if inverse.get("data") is not state.get("data"):
            self._dispose_state(state)
        self._push_evicting(self._undo_stack, inverse)
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
            inv["op"] = "delete_redo"
            inv["data"] = [
                (page_i, self._capture_page_blob(page_i)) for page_i, _ in state["data"]
            ]
        elif op == "delete_redo":
            # delete_redo の逆（redo 後に undo するため）:
            # _restore_state(delete_redo) は delete を実行する。
            # その逆は「削除ページを復元（insert）」= delete op として bytes を返す。
            inv["op"] = "delete"
            inv["data"] = [
                (page_i, self._capture_page_blob(page_i)) for page_i, _ in state["data"]
            ]
        elif op == "page_edit":
            # page_edit は対称 op: 逆デルタ = 適用後（現在）のページ bytes。
            # undo→redo 往復でも同じ op のまま入れ替わる
            inv["data"] = [
                (page_i, self._capture_page_blob(page_i)) for page_i, _ in state["data"]
            ]
        elif op == "move":
            # move の逆: move_page(src, dest) の逆順列を計算して bulk_move で逆操作。
            # move_page の順列を計算し、逆順列を doc.select() で適用する。
            src, actual_dest = state["data"]
            n = len(self.doc)
            # actual_dest = 移動後ページの最終位置（末尾=n-1, 前方=dest-1, 後方=dest）。
            # range から src を取り除き actual_dest へ挿入すれば現 doc 順序に一致する。
            order = list(range(n))
            item = order.pop(src)
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
            inv["op"] = "insert_undo"
            inv["data"] = [
                (i, self._capture_page_blob(i))
                for i in range(insert_at, insert_at + num)
            ]
        elif op == "insert_undo":
            # insert_undo の逆は insert（bytes を再挿入）
            inv["op"] = "insert_redo"
            inv["data"] = state["data"]
        elif op == "insert_redo":
            insert_at = state["data"][0][0] if state["data"] else 0
            num = len(state["data"])
            inv["op"] = "insert_undo"
            inv["data"] = [
                (i, self._capture_page_blob(i))
                for i in range(insert_at, insert_at + num)
            ]
        elif op == "merge":
            # merge の逆: 追加されたページを bytes でキャプチャ（Task 2 で完全実装）
            old_count = state["data"]
            inv["op"] = "merge_undo"
            inv["data"] = (
                old_count,
                [
                    (i, self._capture_page_blob(i))
                    for i in range(old_count, len(self.doc))
                ],
            )
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
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "delete_redo":
            # redo: 昇順インデックスのページを逆順で削除（インデックスずれ防止）
            targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
            for page_i in targets:
                self.doc.delete_page(page_i)
        elif op == "page_edit":
            # ページ内容の置換（黒塗り・モザイク等の破壊的編集の undo/redo）。
            # ページ数は不変のため昇順で 1 ページずつ delete→insert しても
            # 他ページのインデックスはずれない
            for page_i, page_bytes in state["data"]:
                self.doc.delete_page(page_i)
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "move":
            # undo: move_page(src, dest) の逆順列を doc.select() で元の順序に戻す。
            src, actual_dest = state["data"]
            n = len(self.doc)
            # actual_dest = 移動後ページの最終位置。range から src を取り除き
            # actual_dest へ挿入すると現 doc（移動後）の順列に一致する（末尾含む）。
            order = list(range(n))
            item = order.pop(src)
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
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "insert_redo":
            # insert_redo: insert の再実行相当。キャプチャした bytes を昇順で再挿入する
            # （insert→undo→redo の連鎖では「再挿入」が正しい挙動）。
            for page_i, page_bytes in state["data"]:
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
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
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
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
                tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
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
            tmp = fitz.open(stream=self._blob_bytes(d["merged_bytes"]), filetype="pdf")
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
        # 防御コピー: state 内の set を共有束縛すると以降の破壊的変更が
        # スタック上の他デルタを汚染しうる（保存側は set(...) でコピー済み）。
        self.selected_pages = set(state["selected_pages"])
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
        """ファイルをPDF互換のDocumentとして開く。画像の場合はPDFに変換する。

        暗号化 PDF はパスワードを入力させて認証する。直近に開いたファイルが
        パスワードを要求したかは ``self._opened_needed_password`` に記録する
        （呼び出し側がパスワード解除メニューの活性判定に利用）。
        """
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            img_doc = fitz.open(path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()
            self._opened_needed_password = False
            return fitz.open(stream=pdf_bytes, filetype="pdf")
        doc = fitz.open(path)
        self._opened_needed_password = bool(doc.needs_pass)
        if doc.needs_pass:
            if not self._authenticate_doc(doc, path):
                doc.close()
                raise PDFPasswordError(self._t("status_password_cancelled"))
        return doc

    def _authenticate_doc(self, doc, path):
        """パスワードを入力させて doc を認証する。成功で True、キャンセルで False。"""
        name = os.path.basename(path)
        prompt = self._t("open_password_prompt").format(name=name)
        while True:
            pw = simpledialog.askstring(
                self._t("open_password_title"),
                prompt,
                show="*",
                parent=self.root,
            )
            if pw is None:
                return False
            if doc.authenticate(pw):
                return True
            prompt = self._t("err_password_wrong").format(name=name)

    def _do_open_merged(self, ordered_paths):
        """結合順ダイアログ確定後、結合して開く"""
        merged = fitz.open()
        try:
            total = 0
            for path in ordered_paths:
                src = self._open_path_as_pdf(path)
                merged.insert_pdf(src)
                total += len(src)
                src.close()
        except PDFPasswordError:
            merged.close()
            self._set_status(self._t("status_password_cancelled"))
            return
        except Exception as e:
            merged.close()
            messagebox.showerror(self._t("err_title"), str(e))
            return
        try:
            if self.doc:
                self.doc.close()
            self.doc = merged
            self.filepath = None
            # 結合後の出力は暗号化なしの新規ドキュメント
            self.pdf_has_password = False
            self.current_page = 0
            self.selected_pages.clear()
            self._clear_undo_stacks()
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
        # 認証成功まで現在の doc を閉じない（パスワードキャンセル時の取り違え防止）
        try:
            new_doc = self._open_path_as_pdf(path)
        except PDFPasswordError:
            self._set_status(self._t("status_password_cancelled"))
            return
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))
            return
        had_password = getattr(self, "_opened_needed_password", False)
        try:
            if self.doc:
                self.doc.close()
            self.doc = new_doc
            self.filepath = path
            self.pdf_has_password = had_password
            self.current_page = 0
            self.selected_pages.clear()
            self._clear_undo_stacks()
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

    def _is_current_file(self, path):
        """path が現在開いているファイル自身かを判定する"""
        if not path:
            return False
        candidates = [p for p in (self.filepath, getattr(self.doc, "name", "")) if p]
        for cand in candidates:
            try:
                if os.path.exists(path) and os.path.samefile(path, cand):
                    return True
            except OSError as e:
                logger.debug("samefile 判定失敗: %s", e)
            if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
                os.path.abspath(cand)
            ):
                return True
        return False

    def _overwrite_current_file(self, path, **save_kwargs):
        """開いている元ファイル自身へ上書き保存する。

        fitz.Document が元ファイルのハンドルを保持しているため、
        非インクリメンタル保存は同一パスへ直接 save() できず、
        Windows では os.replace も PermissionError になる。
        メモリ上へシリアライズ → doc を close してハンドル解放 →
        tmp ファイル経由で os.replace → 新ファイルを開き直す。
        書き込み失敗時はメモリ上の bytes から doc を復元して例外を再送出する。
        """
        data = self.doc.tobytes(**save_kwargs)
        self.doc.close()
        try:
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            self.doc = fitz.open(path)
        except Exception:
            self.doc = fitz.open(stream=data, filetype="pdf")
            raise

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
                logger.debug("incremental save 失敗、開き直して保存: %s", e)
                self._overwrite_current_file(self.filepath)
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
        self.pdf_has_password = False
        self.current_page = 0
        self.selected_pages.clear()
        self._clear_undo_stacks()
        self._invalidate_thumb_cache()
        self._preview_gen += 1
        self._thumb_gen += 1
        self._refresh_all()
        self._set_status(self._t("status_closed"))
        self.plugin_manager.fire_event("on_file_close", self)

    def _save_compressed(self):
        """縮小最適化して名前を付けて保存（garbage=4, deflate=1, clean=1）。
        現在開いているファイル自身を指定した場合は上書き保存する。"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        dialog_kwargs = {
            "defaultextension": ".pdf",
            "filetypes": [(self._t("filetypes_pdf"), "*.pdf")],
        }
        if self.filepath:
            dialog_kwargs["initialdir"] = os.path.dirname(self.filepath)
            dialog_kwargs["initialfile"] = os.path.basename(self.filepath)
        path = filedialog.asksaveasfilename(**dialog_kwargs)
        if not path:
            return
        save_kwargs = {"garbage": 4, "deflate": 1, "clean": 1}
        try:
            if self._is_current_file(path):
                # 元ファイルへの上書き: ハンドル解放してから置き換える
                self._overwrite_current_file(path, **save_kwargs)
                self.filepath = path
            else:
                self.doc.save(path, **save_kwargs)
            self._set_status(
                self._t("status_compressed").format(name=os.path.basename(path))
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    # ══════════════════════════════════════════
    #  パスワード（暗号化）操作
    # ══════════════════════════════════════════
    def _suggest_save_name(self, suffix):
        """現在のファイル名に suffix を付けた保存ダイアログ用 kwargs を返す。"""
        kwargs = {
            "defaultextension": ".pdf",
            "filetypes": [(self._t("filetypes_pdf"), "*.pdf")],
        }
        if self.filepath:
            base = os.path.basename(self.filepath)
            stem, _ext = os.path.splitext(base)
            kwargs["initialdir"] = os.path.dirname(self.filepath)
            kwargs["initialfile"] = f"{stem}{suffix}.pdf"
        return kwargs

    def _set_password(self):
        """パスワードを設定（暗号化）して名前を付けて保存する。"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        from pagefolio.dialogs import SetPasswordDialog

        SetPasswordDialog(self.root, self._font, self._do_set_password, lang=self.lang)

    def _do_set_password(self, password):
        """SetPasswordDialog 確定後に暗号化保存を実行する。"""
        path = filedialog.asksaveasfilename(
            **self._suggest_save_name(self._t("pwd_suffix_protected"))
        )
        if not path:
            return
        kwargs = {
            "encryption": fitz.PDF_ENCRYPT_AES_256,
            "owner_pw": password,
            "user_pw": password,
        }
        try:
            if self._is_current_file(path):
                # 元ファイルへ上書き → 開き直し後に同じパスワードで再認証し継続利用可に
                self._overwrite_current_file(path, **kwargs)
                self.filepath = path
                if self.doc.needs_pass:
                    self.doc.authenticate(password)
                self.pdf_has_password = True
            else:
                save_with_password(self.doc, path, password)
            self._set_status(
                self._t("status_password_set").format(name=os.path.basename(path))
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _remove_password(self):
        """パスワード（暗号化）を解除して名前を付けて保存する。"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        if not getattr(self, "pdf_has_password", False):
            messagebox.showinfo(self._t("info_title"), self._t("info_no_password"))
            return
        path = filedialog.asksaveasfilename(
            **self._suggest_save_name(self._t("pwd_suffix_decrypted"))
        )
        if not path:
            return
        kwargs = {"encryption": fitz.PDF_ENCRYPT_NONE}
        try:
            if self._is_current_file(path):
                self._overwrite_current_file(path, **kwargs)
                self.filepath = path
                self.pdf_has_password = False
            else:
                save_without_password(self.doc, path)
            self._set_status(
                self._t("status_password_removed").format(name=os.path.basename(path))
            )
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))
