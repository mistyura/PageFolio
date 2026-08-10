"""PDF 操作のテスト。
pagefolio.py のPDF操作ロジックは Tkinter に強く結合しているため、
fitz API を直接使ってアプリと同等の操作が正しく動くことを検証する。
"""

import ast
import os
import pathlib
from unittest.mock import patch

import fitz
import pytest

import pagefolio

# ===== PDF 読み込み =====


class TestPdfOpen:
    """PDF ファイルの読み込みテスト"""

    def test_open_valid_pdf(self, sample_pdf):
        """正常な PDF を開ける"""
        doc = fitz.open(sample_pdf)
        assert len(doc) == 3
        doc.close()

    def test_open_returns_correct_page_count(self, sample_pdf):
        """ページ数が正しい"""
        doc = fitz.open(sample_pdf)
        assert len(doc) == 3
        doc.close()

    def test_open_nonexistent_file_raises(self, tmp_path):
        """存在しないファイルを開くとエラー"""
        with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
            fitz.open(str(tmp_path / "nonexistent.pdf"))

    def test_page_text_content(self, sample_pdf):
        """各ページのテキスト内容が正しい"""
        doc = fitz.open(sample_pdf)
        for i in range(3):
            text = doc[i].get_text()
            assert f"Page {i + 1}" in text
        doc.close()


# ===== PDF 保存 =====


class TestPdfSave:
    """PDF ファイルの保存テスト"""

    def test_save_new_file(self, sample_pdf_doc, tmp_path):
        """新しいファイルとして保存できる"""
        save_path = str(tmp_path / "saved.pdf")
        sample_pdf_doc.save(save_path)
        assert os.path.exists(save_path)
        # 再度開いて検証
        doc2 = fitz.open(save_path)
        assert len(doc2) == 3
        doc2.close()

    def test_save_preserves_content(self, sample_pdf_doc, tmp_path):
        """保存後も内容が保持される"""
        save_path = str(tmp_path / "saved.pdf")
        sample_pdf_doc.save(save_path)
        doc2 = fitz.open(save_path)
        for i in range(3):
            text = doc2[i].get_text()
            assert f"Page {i + 1}" in text
        doc2.close()

    def test_incremental_save(self, sample_pdf, tmp_path):
        """incremental 保存（上書き保存のシミュレーション）"""
        import shutil

        copy_path = str(tmp_path / "copy.pdf")
        shutil.copy2(sample_pdf, copy_path)
        doc = fitz.open(copy_path)
        # 変更を加える
        doc[0].insert_text((72, 200), "Modified", fontsize=16)
        doc.save(copy_path, incremental=True, encryption=0)
        doc.close()
        # 再度開いて検証
        doc2 = fitz.open(copy_path)
        text = doc2[0].get_text()
        assert "Modified" in text
        doc2.close()


# ===== ページ回転 =====


class TestPageRotate:
    """ページ回転テスト（_rotate_selected と同等のロジック）"""

    def test_rotate_90(self, sample_pdf_doc):
        """90° 回転"""
        page = sample_pdf_doc[0]
        original = page.rotation
        page.set_rotation((original + 90) % 360)
        assert page.rotation == (original + 90) % 360

    def test_rotate_180(self, sample_pdf_doc):
        """180° 回転"""
        page = sample_pdf_doc[0]
        page.set_rotation(180)
        assert page.rotation == 180

    def test_rotate_360_returns_to_original(self, sample_pdf_doc):
        """360° 回転で元に戻る"""
        page = sample_pdf_doc[0]
        page.set_rotation(0)
        page.set_rotation((page.rotation + 360) % 360)
        assert page.rotation == 0

    def test_rotate_multiple_pages(self, sample_pdf_doc):
        """複数ページの回転"""
        targets = [0, 2]
        for i in targets:
            page = sample_pdf_doc[i]
            page.set_rotation((page.rotation + 90) % 360)
        assert sample_pdf_doc[0].rotation == 90
        assert sample_pdf_doc[1].rotation == 0  # 未変更
        assert sample_pdf_doc[2].rotation == 90


# ===== ページ削除 =====


class TestPageDelete:
    """ページ削除テスト（_delete_selected と同等のロジック）"""

    def test_delete_single_page(self, sample_pdf_doc):
        """1ページ削除"""
        sample_pdf_doc.delete_page(1)  # 2ページ目を削除
        assert len(sample_pdf_doc) == 2

    def test_delete_preserves_other_pages(self, sample_pdf_doc):
        """削除後に残りのページが正しい"""
        sample_pdf_doc.delete_page(1)
        text_0 = sample_pdf_doc[0].get_text()
        text_1 = sample_pdf_doc[1].get_text()
        assert "Page 1" in text_0
        assert "Page 3" in text_1

    def test_delete_multiple_pages_reverse_order(self, sample_pdf_doc):
        """複数ページを逆順で削除（アプリと同じロジック）"""
        targets = sorted([0, 2], reverse=True)
        for i in targets:
            sample_pdf_doc.delete_page(i)
        assert len(sample_pdf_doc) == 1
        assert "Page 2" in sample_pdf_doc[0].get_text()


# ===== ページ挿入 =====


class TestPageInsert:
    """ページ挿入テスト（_do_insert と同等のロジック）"""

    def test_insert_at_head(self, sample_pdf, multi_pdf_files):
        """先頭に挿入"""
        doc = fitz.open(sample_pdf)
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        doc.insert_pdf(src, from_page=0, to_page=len(src) - 1, start_at=0)
        assert len(doc) == 4
        doc.close()
        src.close()

    def test_insert_at_tail(self, sample_pdf, multi_pdf_files):
        """末尾に挿入"""
        doc = fitz.open(sample_pdf)
        original_len = len(doc)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        doc.insert_pdf(src, from_page=0, to_page=len(src) - 1)
        assert len(doc) == original_len + 2
        doc.close()
        src.close()


# ===== PDF 結合 =====


class TestPdfMerge:
    """PDF 結合テスト（_do_merge と同等のロジック）"""

    def test_merge_multiple_files(self, sample_pdf, multi_pdf_files):
        """複数ファイルの結合"""
        doc = fitz.open(sample_pdf)
        total_added = 0
        for path in multi_pdf_files:
            src = fitz.open(path)
            doc.insert_pdf(src)
            total_added += len(src)
            src.close()
        # 元3ページ + file1(1) + file2(2) + file3(3) = 9ページ
        assert len(doc) == 3 + total_added
        assert len(doc) == 9
        doc.close()


# ===== PDF 分割 =====


class TestPdfSplit:
    """PDF 分割テスト（_split_by_range / _split_each_page と同等のロジック）"""

    def test_split_by_range(self, sample_pdf, tmp_path):
        """範囲指定分割"""
        doc = fitz.open(sample_pdf)
        # 1-2ページを抽出
        out = fitz.open()
        for page_num in range(0, 2):  # 0-indexed: page 1-2
            out.insert_pdf(doc, from_page=page_num, to_page=page_num)
        out_path = str(tmp_path / "split_1-2.pdf")
        out.save(out_path)
        out.close()

        # 検証
        result = fitz.open(out_path)
        assert len(result) == 2
        assert "Page 1" in result[0].get_text()
        assert "Page 2" in result[1].get_text()
        result.close()
        doc.close()

    def test_split_each_page(self, sample_pdf, tmp_path):
        """1ページずつ分割"""
        doc = fitz.open(sample_pdf)
        n = len(doc)
        for i in range(n):
            out = fitz.open()
            out.insert_pdf(doc, from_page=i, to_page=i)
            out_path = str(tmp_path / f"page_{i + 1:02d}.pdf")
            out.save(out_path)
            out.close()

        # 検証: 各ファイルが存在し1ページ
        for i in range(n):
            path = str(tmp_path / f"page_{i + 1:02d}.pdf")
            assert os.path.exists(path)
            result = fitz.open(path)
            assert len(result) == 1
            assert f"Page {i + 1}" in result[0].get_text()
            result.close()
        doc.close()

    def test_split_single_page_extraction(self, sample_pdf, tmp_path):
        """単一ページ抽出"""
        doc = fitz.open(sample_pdf)
        out = fitz.open()
        out.insert_pdf(doc, from_page=1, to_page=1)  # 2ページ目
        out_path = str(tmp_path / "page2.pdf")
        out.save(out_path)
        out.close()

        result = fitz.open(out_path)
        assert len(result) == 1
        assert "Page 2" in result[0].get_text()
        result.close()
        doc.close()

    def test_split_by_range_no_input_shows_error(self, sample_pdf_doc, monkeypatch):
        """範囲未入力時は showerror + err_title で表示され showinfo は使わない
        （C7回帰）。"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.root = None

            def _check_doc(self):
                return self.doc is not None

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(sample_pdf_doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)

        calls = {"showerror": [], "showinfo": []}
        monkeypatch.setattr(po.simpledialog, "askstring", lambda *a, **kw: "")
        monkeypatch.setattr(
            po.messagebox,
            "showerror",
            lambda title, msg: calls["showerror"].append((title, msg)),
        )
        monkeypatch.setattr(
            po.messagebox,
            "showinfo",
            lambda title, msg: calls["showinfo"].append((title, msg)),
        )

        app._split_by_range()

        assert calls["showerror"] == [("err_title", "err_split_no_range")]
        assert calls["showinfo"] == []

    def _make_split_fake_app(self, doc, pdf_has_password):
        """_split_by_range/_split_each_page テスト用 FakeApp を生成する。"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.root = None
                self.pdf_has_password = pdf_has_password

            def _check_doc(self):
                return self.doc is not None

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_split_by_range_password_protected_declines_writes_no_files(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        """01-REVIEW.md WR-03 回帰テスト: pdf_has_password=True の場合、分割前に
        パスワード保護解除の警告確認が表示され、ユーザーが拒否すると分割は
        実行されない（ファイルが1つも生成されない）ことを検証する。
        """
        import pagefolio.page_ops as po

        app = self._make_split_fake_app(sample_pdf_doc, pdf_has_password=True)

        monkeypatch.setattr(po.simpledialog, "askstring", lambda *a, **kw: "1-2")
        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )

        askyesno_calls = []

        def fake_askyesno(title, msg):
            askyesno_calls.append((title, msg))
            return False  # パスワード警告を拒否

        monkeypatch.setattr(po.messagebox, "askyesno", fake_askyesno)

        app._split_by_range()

        # パスワード警告ダイアログが1回だけ表示され、拒否されたため
        # 圧縮確認まで到達せず、分割も実行されない
        assert askyesno_calls == [
            ("split_password_warn_title", "split_password_warn_msg")
        ]
        assert list(tmp_path.iterdir()) == []

    def test_split_by_range_password_protected_accepts_proceeds(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        """パスワード警告を承諾すれば、これまでどおり分割が実行される
        （警告追加が既存の分割動作を壊していないことの担保）。"""
        import pagefolio.page_ops as po

        app = self._make_split_fake_app(sample_pdf_doc, pdf_has_password=True)

        monkeypatch.setattr(po.simpledialog, "askstring", lambda *a, **kw: "1-2")
        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )
        monkeypatch.setattr(po.messagebox, "askyesno", lambda *a, **kw: True)

        app._split_by_range()

        files = sorted(p.name for p in tmp_path.iterdir())
        assert files == ["split_p1-2.pdf"]

    def test_split_each_page_password_protected_declines_writes_no_files(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        """_split_each_page 側でも同様にパスワード警告が機能することを検証する。"""
        import pagefolio.page_ops as po

        app = self._make_split_fake_app(sample_pdf_doc, pdf_has_password=True)

        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )
        monkeypatch.setattr(po.messagebox, "askyesno", lambda *a, **kw: False)

        app._split_each_page()

        assert list(tmp_path.iterdir()) == []

    def test_split_by_range_without_password_skips_warning(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        """pdf_has_password=False（通常PDF）ではパスワード警告が出ず、
        圧縮確認ダイアログのみが表示されることを検証する（既存動作の保持）。
        """
        import pagefolio.page_ops as po

        app = self._make_split_fake_app(sample_pdf_doc, pdf_has_password=False)

        monkeypatch.setattr(po.simpledialog, "askstring", lambda *a, **kw: "1-2")
        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )

        askyesno_calls = []

        def fake_askyesno(title, msg):
            askyesno_calls.append((title, msg))
            return False  # 圧縮確認を拒否（非圧縮で保存継続）

        monkeypatch.setattr(po.messagebox, "askyesno", fake_askyesno)

        app._split_by_range()

        assert askyesno_calls == [
            ("compress_split_confirm_title", "compress_split_confirm_msg")
        ]
        files = sorted(p.name for p in tmp_path.iterdir())
        assert files == ["split_p1-2.pdf"]


# ===== トリミング (CropBox) =====


class TestPageCrop:
    """ページトリミング（CropBox 設定）テスト"""

    def test_set_cropbox(self, sample_pdf_doc):
        """CropBox を設定できる"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        new_rect = fitz.Rect(
            mb.x0 + 50,
            mb.y0 + 50,
            mb.x1 - 50,
            mb.y1 - 50,
        )
        page.set_cropbox(new_rect)
        cb = page.cropbox
        assert abs(cb.x0 - new_rect.x0) < 1
        assert abs(cb.y0 - new_rect.y0) < 1

    def test_cropbox_within_mediabox(self, sample_pdf_doc):
        """CropBox は MediaBox 内に収まる（クランプロジック検証）"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        # アプリと同じクランプロジック
        eps = 0.01
        new_rect = fitz.Rect(
            max(round(100.0, 2), mb.x0 + eps),
            max(round(100.0, 2), mb.y0 + eps),
            min(round(400.0, 2), mb.x1 - eps),
            min(round(600.0, 2), mb.y1 - eps),
        )
        page.set_cropbox(new_rect)
        cb = page.cropbox
        assert cb.x0 >= mb.x0
        assert cb.y0 >= mb.y0
        assert cb.x1 <= mb.x1
        assert cb.y1 <= mb.y1

    def test_cropbox_reset(self, sample_pdf_doc):
        """CropBox をリセット（MediaBox に戻す）できる"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        # まずトリミング
        page.set_cropbox(fitz.Rect(50, 50, 400, 600))
        # リセット
        page.set_cropbox(mb)
        cb = page.cropbox
        assert abs(cb.x0 - mb.x0) < 1
        assert abs(cb.y0 - mb.y0) < 1

    def test_cropbox_too_small_is_detectable(self, sample_pdf_doc):
        """サイズが小さすぎるか検出可能"""
        # アプリ内では width < 1 or height < 1 で弾く
        tiny_rect = fitz.Rect(100, 100, 100.5, 100.5)
        assert tiny_rect.width < 1
        assert tiny_rect.height < 1


# ===== Undo/Redo ロジック =====


class TestUndoRedoLogic:
    """Undo/Redo 差分フォーマットのロジックテスト（操作タイプ別方式）"""

    def test_rotate_delta_roundtrip(self, sample_pdf_doc):
        """回転の差分保存と逆操作が正しく動作する"""
        doc = sample_pdf_doc
        original_rotation = doc[0].rotation  # 通常 0

        # 差分保存: 回転前の rotation を記録
        delta = {"op": "rotate", "data": [(0, doc[0].rotation)]}

        # 操作: 90度回転
        doc[0].set_rotation((doc[0].rotation + 90) % 360)
        assert doc[0].rotation == 90

        # Undo: 差分で復元
        for page_i, old_rot in delta["data"]:
            doc[page_i].set_rotation(old_rot)
        assert doc[0].rotation == original_rotation

    def test_delete_delta_roundtrip(self, sample_pdf_doc):
        """削除の差分保存と逆操作（ページ復元）が正しく動作する"""
        doc = sample_pdf_doc
        original_count = len(doc)  # 3ページ

        # 差分保存: 削除対象ページをバイト列で保存（昇順）
        targets = sorted([0])  # ページ0を削除
        delta_data = []
        for i in targets:
            tmp = fitz.open()
            tmp.insert_pdf(doc, from_page=i, to_page=i)
            delta_data.append((i, tmp.tobytes()))
            tmp.close()

        # 操作: ページ削除
        doc.delete_page(0)
        assert len(doc) == original_count - 1

        # Undo: 昇順で再挿入
        for page_i, page_bytes in delta_data:
            tmp = fitz.open(stream=page_bytes, filetype="pdf")
            doc.insert_pdf(tmp, start_at=page_i)
            tmp.close()
        assert len(doc) == original_count
        assert "Page 1" in doc[0].get_text()

    def test_restore_state_no_pdf_bytes_key(self):
        """_restore_state は pdf_bytes キーを含まない op 別 state を受け付ける"""
        # op 別 state（対称デルタ方式）: pdf_bytes キーなし
        state = {
            "op": "rotate",
            "current_page": 0,
            "selected_pages": set(),
            "data": [(0, 0)],
        }
        # pdf_bytes キーが存在しないことを確認
        assert "pdf_bytes" not in state

    def test_restore_state_returns_inverse_delta(self):
        """_restore_state が逆デルタ dict を返す（pdf_bytes キーなし）"""
        import collections

        import fitz

        import pagefolio.file_ops as fo

        # FileOpsMixin のメソッドを Mixin として使う簡易スタブ
        class FakeApp(fo.FileOpsMixin):
            def __init__(self, doc):
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)

        app = FakeApp(doc)
        # rotate op の逆デルタ取得テスト
        # 90 度回転を適用済みと仮定し undo state を構築
        app.doc[0].set_rotation(90)
        state = {
            "op": "rotate",
            "current_page": 0,
            "selected_pages": set(),
            "data": [(0, 0)],  # 元の rotation=0 に戻す
        }

        inverse = app._restore_state(state)
        # 逆デルタが返されること（dict 型）
        assert isinstance(inverse, dict)
        # pdf_bytes キーを含まないこと
        assert "pdf_bytes" not in inverse
        # op キーを持つこと
        assert "op" in inverse
        # 回転が元に戻っていること
        assert app.doc[0].rotation == 0
        doc.close()


# ===== insert/merge Undo→Redo ラウンドトリップ =====


class TestInsertMergeUndoRedo:
    """insert/merge の do→undo→redo ラウンドトリップ検証（Task 2 対応）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def test_insert_undo_removes_inserted_pages(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo で挿入ページが除去され元のページ数に戻る（BUG-01）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # insert op を _save_undo で記録（insert_at=1, num=0 → 書き戻し後に1）
        app._save_undo("insert", insert_at=1)
        # 実際の挿入（1ページを位置1に）
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        app.doc.insert_pdf(src, start_at=1)
        src.close()
        # 書き戻し
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # Undo: 挿入ページが除去される
        app._undo()
        assert len(app.doc) == original_count

    def test_insert_undo_redo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo → redo でページ内容ごと往復する"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        insert_at = 1

        # insert op
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[0])  # "File1 Page1" が含まれる1ページ
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # Undo
        app._undo()
        assert len(app.doc) == original_count
        # redo スタックに逆デルタが積まれていること
        assert len(app._redo_stack) == 1

        # Redo: 挿入ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        # 挿入位置のページに "File1 Page1" テキストが含まれること
        assert "File1 Page1" in app.doc[insert_at].get_text()

    def test_merge_resize_no_pdf_bytes_in_undo_stack(self):
        """_do_merge_resize が pdf_bytes キーを持たない state を undo スタックに積む"""
        import collections

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self):
                doc = fitz.open()
                for _ in range(4):
                    doc.new_page(width=595, height=842)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

            def plugin_manager(self):
                pass

        app = FakeApp()
        # ダミー plugin_manager
        import types

        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)

        # undo スタックに pdf_bytes キーが含まれないこと
        assert len(app._undo_stack) > 0
        for entry in app._undo_stack:
            assert "pdf_bytes" not in entry, f"pdf_bytes が残存: {entry.keys()}"


# ===== 挿入 Undo/Redo 内容同一性検証 =====


def _page_digest(page):
    """ページのテキスト内容から digest を返す（D-07 内容同一性用）。
    fitz.Page を受け取り、get_text() の文字列を返す。
    sample_pdf_doc/multi_pdf_files は "Page N" / "File1 PageM" 形式のテキストを持つため
    テキストベースの同一性検証が確実・高速。
    """
    return page.get_text().strip()


class TestInsertUndoRedo:
    """挿入 Undo/Redo の内容同一性・往復検証（TEST-01 / D-07）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def test_insert_undo_restores_page_count(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo で len(doc) が元に戻る（BUG-01 ページ数検証）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # insert: 2ページ PDF を位置1に挿入
        app._save_undo("insert", insert_at=1)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        app.doc.insert_pdf(src, start_at=1)
        src.close()
        app._undo_stack[-1]["data"][1] = 2
        assert len(app.doc) == original_count + 2

        # Undo: ページ数が元に戻る
        app._undo()
        assert len(app.doc) == original_count

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

    def test_insert_undo_restores_content(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo 後の残ページ digest が挿入前と一致する（D-07 内容同一性）"""
        app = self._make_fake_app(sample_pdf_doc)

        # 挿入前のページ digest を記録
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # insert: 1ページを位置2に挿入
        app._save_undo("insert", insert_at=2)
        src = fitz.open(multi_pdf_files[0])  # 1ページ: "File1 Page1"
        app.doc.insert_pdf(src, start_at=2)
        src.close()
        app._undo_stack[-1]["data"][1] = 1

        # Undo
        app._undo()

        # 残ページの digest が挿入前と一致する
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

    def test_insert_undo_redo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """do→undo→redo で len と挿入ページ digest が一致する（D-07 redo 往復）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        insert_at = 1

        # 挿入前の全ページ digest を記録
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # insert: 1ページを位置1に挿入（"File1 Page1" テキストを持つ）
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        inserted_digest = _page_digest(src[0])
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # 挿入後の挿入ページ digest を確認
        assert _page_digest(app.doc[insert_at]) == inserted_digest

        # Undo
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

        # Redo: 挿入ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[insert_at]) == inserted_digest

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._undo_stack:
            assert "pdf_bytes" not in entry

    def test_insert_undo_redo_undo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """insert→undo→redo→undo（2回目）の4手往復でページ数・内容が正しく
        往復し、挿入ページが重複しないことを検証する（D-17・insert_redo
        非対称復元バグの回帰テスト。修正前は2回目の undo でページが重複し
        len(doc) が元の枚数+1になっていた）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        insert_at = 1

        # 挿入前の全ページ digest を記録
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # insert: 1ページを位置1に挿入
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        inserted_digest = _page_digest(src[0])
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # 1回目の Undo: 挿入前の状態に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 挿入ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[insert_at]) == inserted_digest

        # 2回目の Undo: ここでページが重複せず、挿入前の状態に正しく戻ること
        app._undo()
        assert len(app.doc) == original_count
        after_second_undo_digests = [
            _page_digest(app.doc[i]) for i in range(len(app.doc))
        ]
        assert before_digests == after_second_undo_digests

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry
        for entry in app._undo_stack:
            assert "pdf_bytes" not in entry


# ===== 全 op 最小 do→undo→redo 往復テスト（安全網）=====


class TestAllOpsUndoRedoRoundtrip:
    """全 op（rotate/delete/move/duplicate/merge/bulk_move/bulk_crop/merge_resize）
    の最小 do→undo→redo 往復検証（Deferred 安全網 / D-04/D-05 整合）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def _make_full_fake_app(self, doc):
        """FileOpsMixin + PageOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_rotate_roundtrip(self, sample_pdf_doc):
        """rotate: 90度回転 → undo で 0 → redo で 90（rotation 属性で検証）"""
        app = self._make_fake_app(sample_pdf_doc)
        targets = [0]
        original_rot = app.doc[0].rotation  # 0

        # do: 90度回転
        app._save_undo("rotate", targets=targets)
        app.doc[0].set_rotation((app.doc[0].rotation + 90) % 360)
        assert app.doc[0].rotation == 90

        # undo
        app._undo()
        assert app.doc[0].rotation == original_rot

        # redo
        app._redo()
        assert app.doc[0].rotation == 90

        # pdf_bytes キーなし
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_delete_roundtrip(self, sample_pdf_doc):
        """delete: 1ページ削除 → undo で復元（digest 一致）→ redo で再削除"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        target_digest = _page_digest(app.doc[1])

        # do: ページ1を削除
        targets = sorted([1], reverse=True)
        app._save_undo("delete", targets=targets)
        app.doc.delete_page(1)
        assert len(app.doc) == original_count - 1

        # undo: ページが復元される
        app._undo()
        assert len(app.doc) == original_count
        assert _page_digest(app.doc[1]) == target_digest

        # redo: 再削除
        app._redo()
        assert len(app.doc) == original_count - 1

        # undo/redo エントリのトップレベルキーに pdf_bytes がないことを確認
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_delete_undo_apply_inverse_does_not_capture_blob(
        self, sample_pdf_doc, monkeypatch
    ):
        """WR-01 回帰テスト: delete の undo（_apply_inverse の "delete"→
        "delete_redo" 変換）で _capture_page_blob が呼ばれないことを検証する。

        修正前は mutation（ページ再挿入）より前のタイミングで
        _capture_page_blob(page_i) を呼んでおり、まだ挿入されていない
        ページ位置の無関係な内容を誤ってキャプチャした上、無駄な Blob
        確保（後で解放されるまでリソースを握る）が発生していた。
        delete_redo の data は page_i のみ使用し blob は参照しないため、
        修正後はプレースホルダ（None）になる。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        targets = sorted([0, 1], reverse=True)
        app._save_undo("delete", targets=targets)
        for i in targets:
            app.doc.delete_page(i)

        capture_calls = []
        original_capture = fo.FileOpsMixin._capture_page_blob

        def tracking_capture(self_app, page_i):
            capture_calls.append(page_i)
            return original_capture(self_app, page_i)

        monkeypatch.setattr(fo.FileOpsMixin, "_capture_page_blob", tracking_capture)

        app._undo()

        # delete → delete_redo 変換で _capture_page_blob が呼ばれていないこと
        assert capture_calls == []
        # redo スタックの data は page_i のみを保持し blob は None（プレースホルダ）
        inverse = app._redo_stack[-1]
        assert inverse["op"] == "delete_redo"
        for _page_i, blob in inverse["data"]:
            assert blob is None

    @pytest.mark.parametrize("src,dest", [(0, 2), (0, 3), (2, 0), (1, 3)])
    def test_move_roundtrip(self, sample_pdf_doc, src, dest):
        """move: 実 dnd 規約（actual_dest=最終位置, 末尾ドロップ dest>=n 含む）で
        do→undo で元順序、redo で移動後順序に戻ることを検証（CR-01 回帰防止）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: _save_undo は操作前に実 actual_dest を保存する必要があるため先に算出
        n = len(app.doc)
        actual_dest = (n - 1) if dest >= n else (dest if dest < src else dest - 1)
        app._save_undo("move", src=src, actual_dest=actual_dest)
        if dest >= n:
            app.doc.move_page(src, -1)
        else:
            app.doc.move_page(src, dest)
        moved_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert moved_order != original_order

        # undo: 元の順序に戻る
        app._undo()
        after_undo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_undo == original_order

        # redo: 移動後の順序に戻る
        app._redo()
        after_redo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_redo == moved_order

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_duplicate_roundtrip(self, sample_pdf_doc):
        """duplicate: ページ1複製 → undo で元ページ数 → redo で複製ページ復元"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        pno = 1
        src_digest = _page_digest(app.doc[pno])

        # do: ページ1を複製
        app._save_undo("duplicate", pno=pno)
        tmp = fitz.open()
        tmp.insert_pdf(app.doc, from_page=pno, to_page=pno)
        app.doc.insert_pdf(tmp, start_at=pno + 1)
        tmp.close()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[pno + 1]) == src_digest

        # undo: 複製ページが削除される
        app._undo()
        assert len(app.doc) == original_count

        # redo: 複製ページが復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[pno + 1]) == src_digest

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """merge: 1ページ PDF を結合 → undo でページ数復元 → redo で再結合"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # do: 1ページ PDF を結合（末尾に追加）
        app._save_undo("merge")
        src = fitz.open(multi_pdf_files[0])  # 1ページ: "File1 Page1"
        merged_digest = _page_digest(src[0])
        app.doc.insert_pdf(src)
        src.close()
        assert len(app.doc) == original_count + 1

        # undo: 結合ページが除去される
        app._undo()
        assert len(app.doc) == original_count

        # redo: 結合ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[original_count]) == merged_digest

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_bulk_move_roundtrip(self, sample_pdf_doc):
        """bulk_move: ページ順序変更 → undo で元順序 → redo で変更後順序"""
        app = self._make_fake_app(sample_pdf_doc)
        original_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: new_order = [2, 0, 1] (ページ2を先頭に)
        new_order = [2, 0, 1]
        app._save_undo("bulk_move", new_order=new_order)
        app.doc.select(new_order)
        reordered = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert reordered != original_order

        # undo: 元の順序に戻る
        app._undo()
        after_undo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_undo == original_order

        # redo: 変更後の順序に戻る
        app._redo()
        after_redo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_redo == reordered

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_bulk_crop_roundtrip(self, sample_pdf_doc):
        """bulk_crop: 複数ページ cropbox 設定 → undo で元 cropbox → redo で新 cropbox"""
        app = self._make_fake_app(sample_pdf_doc)
        targets = [0, 1]

        # 元の cropbox を記録
        original_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]

        # do: cropbox を縮小
        crop_data = [
            (i, (cb[0], cb[1], cb[2], cb[3]))
            for i, cb in zip(targets, original_cropboxes, strict=True)
        ]
        app._save_undo("bulk_crop", crop_data=crop_data)
        for i in targets:
            mb = app.doc[i].mediabox
            new_rect = fitz.Rect(mb.x0 + 20, mb.y0 + 20, mb.x1 - 20, mb.y1 - 20)
            app.doc[i].set_cropbox(new_rect)
        new_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]

        # undo: 元の cropbox に戻る
        app._undo()
        after_undo_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]
        for orig, after in zip(original_cropboxes, after_undo_cropboxes, strict=True):
            for o, a in zip(orig, after, strict=True):
                assert abs(o - a) < 1.0

        # redo: 縮小後の cropbox に戻る
        app._redo()
        after_redo_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]
        for new_cb, after in zip(new_cropboxes, after_redo_cropboxes, strict=True):
            for n, a in zip(new_cb, after, strict=True):
                assert abs(n - a) < 1.0

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_resize_roundtrip(self):
        """merge_resize: A4×2 を A3 に結合 → undo で元ページ復元 → redo で再結合"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self):
                doc = fitz.open()
                for i in range(3):
                    p = doc.new_page(width=595, height=842)
                    p.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp()
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        original_count = len(app.doc)  # 3
        original_digests = [_page_digest(app.doc[i]) for i in range(original_count)]

        # do: ページ0,1を横並びで結合（A3 サイズ）
        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        # 元3ページ - 2ページ + 1ページ = 2ページ
        assert len(app.doc) == original_count - 1
        # 結合ページのサイズが A3 になっていること
        assert abs(app.doc[0].rect.width - 1190) < 1

        # undo: 元のページ構成に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert original_digests == after_undo_digests

        # redo: 結合後の状態に戻る
        app._redo()
        assert len(app.doc) == original_count - 1
        assert abs(app.doc[0].rect.width - 1190) < 1

        # pdf_bytes キーなし
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_duplicate_undo_redo_undo_roundtrip(self, sample_pdf_doc):
        """duplicate: do→undo→redo→undo（2回目）の4手往復でページ数・
        digest列が操作前と一致することを検証する（V190-UNDO-02・D-17
        insert_redo 非対称復元バグ回帰テストの水平展開）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        pno = 1
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: ページ1を複製
        app._save_undo("duplicate", pno=pno)
        tmp = fitz.open()
        tmp.insert_pdf(app.doc, from_page=pno, to_page=pno)
        app.doc.insert_pdf(tmp, start_at=pno + 1)
        tmp.close()
        assert len(app.doc) == original_count + 1

        # 1回目の Undo: 複製前の状態に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 複製ページが復元される
        app._redo()
        assert len(app.doc) == original_count + 1

        # 2回目の Undo: ここでページが重複せず、複製前の状態に正しく戻ること
        app._undo()
        assert len(app.doc) == original_count
        after_second_undo_digests = [
            _page_digest(app.doc[i]) for i in range(len(app.doc))
        ]
        assert before_digests == after_second_undo_digests

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_undo_redo_undo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """merge: do→undo→redo→undo（2回目）の4手往復でページ数・digest列が
        操作前と一致することを検証する（V190-UNDO-02）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: 1ページ PDF を結合（末尾に追加）
        app._save_undo("merge")
        src = fitz.open(multi_pdf_files[0])  # 1ページ: "File1 Page1"
        app.doc.insert_pdf(src)
        src.close()
        assert len(app.doc) == original_count + 1

        # 1回目の Undo: 結合前の状態に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 結合ページが復元される
        app._redo()
        assert len(app.doc) == original_count + 1

        # 2回目の Undo: 結合前の状態に正しく戻ること
        app._undo()
        assert len(app.doc) == original_count
        after_second_undo_digests = [
            _page_digest(app.doc[i]) for i in range(len(app.doc))
        ]
        assert before_digests == after_second_undo_digests

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_resize_undo_redo_undo_roundtrip(self, sample_pdf_doc):
        """merge_resize: do→undo→redo→undo（2回目）の4手往復でページ数・
        digest列が操作前と一致することを検証する（V190-UNDO-02）。"""
        app = self._make_full_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        original_digests = [_page_digest(app.doc[i]) for i in range(original_count)]

        # do: ページ0,1を横並びで結合（A3 サイズ）
        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        assert len(app.doc) == original_count - 1

        # 1回目の Undo: 元のページ構成に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert original_digests == after_undo_digests

        # Redo: 結合後の状態に戻る
        app._redo()
        assert len(app.doc) == original_count - 1

        # 2回目の Undo: ここでページが壊れず元のページ構成に正しく戻ること
        app._undo()
        assert len(app.doc) == original_count
        after_second_undo_digests = [
            _page_digest(app.doc[i]) for i in range(len(app.doc))
        ]
        assert original_digests == after_second_undo_digests

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_duplicate_single_page_doc_roundtrip(self):
        """duplicate: 1ページのみの Document でも4手往復でページ構成が
        一致する（probe: V190-UNDO-02 / boundary）。"""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Only Page", fontsize=24)
        try:
            app = self._make_fake_app(doc)
            original_count = len(app.doc)  # 1
            pno = 0
            before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

            # do: 唯一のページを複製
            app._save_undo("duplicate", pno=pno)
            tmp = fitz.open()
            tmp.insert_pdf(app.doc, from_page=pno, to_page=pno)
            app.doc.insert_pdf(tmp, start_at=pno + 1)
            tmp.close()
            assert len(app.doc) == original_count + 1

            app._undo()
            assert len(app.doc) == original_count
            after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
            assert before_digests == after_undo_digests

            app._redo()
            assert len(app.doc) == original_count + 1

            app._undo()
            assert len(app.doc) == original_count
            after_second_undo_digests = [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]
            assert before_digests == after_second_undo_digests
        finally:
            doc.close()

    def test_merge_head_and_tail_adjacent_roundtrip(self, multi_pdf_files):
        """merge: 先頭（index 0隣接）・末尾（index len-1隣接）どちらの位置への
        結合でも、4手往復後のページ順序（digest列）が操作前と完全に一致する
        ことを検証する（probe: V190-UNDO-02 / adjacency）。ページ数だけでなく
        順序を見ることが本テストの主眼である。"""
        # --- 先頭隣接: 元 Document が1ページのみのため、結合ページは
        #     唯一の元ページ（index 0）の直後に入る
        head_doc = fitz.open(multi_pdf_files[0])  # 1ページ
        try:
            app = self._make_fake_app(head_doc)
            original_count = len(app.doc)
            before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

            app._save_undo("merge")
            src = fitz.open(multi_pdf_files[1])  # 2ページ
            app.doc.insert_pdf(src)
            src.close()
            assert len(app.doc) == original_count + 2

            app._undo()
            assert len(app.doc) == original_count
            assert before_digests == [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]

            app._redo()
            assert len(app.doc) == original_count + 2

            app._undo()
            assert len(app.doc) == original_count
            assert before_digests == [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]
        finally:
            head_doc.close()

        # --- 末尾隣接: 複数ページ Document の末尾へ結合
        tail_doc = fitz.open()
        for i in range(3):
            p = tail_doc.new_page(width=595, height=842)
            p.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
        try:
            app = self._make_fake_app(tail_doc)
            original_count = len(app.doc)
            before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

            app._save_undo("merge")
            src = fitz.open(multi_pdf_files[0])  # 1ページ
            app.doc.insert_pdf(src)
            src.close()
            assert len(app.doc) == original_count + 1

            app._undo()
            assert len(app.doc) == original_count
            assert before_digests == [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]

            app._redo()
            assert len(app.doc) == original_count + 1

            app._undo()
            assert len(app.doc) == original_count
            assert before_digests == [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]
        finally:
            tail_doc.close()

    def test_merge_resize_preserves_original_page_order(self):
        """merge_resize: 4手往復後、元から存在していたページの digest列が
        操作前と同順で一致することを検証する（probe: V190-UNDO-02 /
        ordering）。集合として一致するだけでは不十分であり、リストとしての
        順序比較を行う。"""
        doc = fitz.open()
        for i in range(4):
            p = doc.new_page(width=595, height=842)
            p.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
        try:
            app = self._make_full_fake_app(doc)
            original_count = len(app.doc)  # 4
            original_digests = [_page_digest(app.doc[i]) for i in range(original_count)]

            # target 以外のページ（index 0, 3）が結合ページを挟んで
            # 前後に残る構成
            targets = [1, 2]
            app._do_merge_resize(targets, "horizontal", 1190, 842)
            assert len(app.doc) == original_count - 1  # 3

            app._undo()
            assert len(app.doc) == original_count
            after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
            assert original_digests == after_undo_digests

            app._redo()
            assert len(app.doc) == original_count - 1

            app._undo()
            assert len(app.doc) == original_count
            after_second_undo_digests = [
                _page_digest(app.doc[i]) for i in range(len(app.doc))
            ]
            assert original_digests == after_second_undo_digests
        finally:
            doc.close()

    def test_merge_resize_preserves_original_page_dimensions(self):
        """merge_resize: 4手往復後、元から存在していたページの MediaBox
        幅・高さが操作前と一致することを検証する（probe: V190-UNDO-02 /
        precision）。リサイズ処理の丸め誤差が既存ページへ波及しないことを
        pytest.approx で確認する。"""
        doc = fitz.open()
        for i in range(4):
            p = doc.new_page(width=595, height=842)
            p.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
        try:
            app = self._make_full_fake_app(doc)
            original_count = len(app.doc)  # 4
            untouched = [0, 3]
            original_dims = {
                i: (app.doc[i].mediabox.width, app.doc[i].mediabox.height)
                for i in untouched
            }

            targets = [1, 2]
            app._do_merge_resize(targets, "horizontal", 1190, 842)

            app._undo()
            app._redo()
            app._undo()
            assert len(app.doc) == original_count

            for i in untouched:
                w, h = original_dims[i]
                assert app.doc[i].mediabox.width == pytest.approx(w)
                assert app.doc[i].mediabox.height == pytest.approx(h)
        finally:
            doc.close()

    def test_roundtrip_with_single_merge_source_file(
        self, sample_pdf_doc, multi_pdf_files
    ):
        """merge: マージ対象ファイルが1件だけの最小入力でも4手往復が成立する
        ことを検証する（probe: V190-UNDO-02 / empty）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        ordered_paths = [multi_pdf_files[0]]  # 1件のみ・1ページ
        app._save_undo("merge")
        for path in ordered_paths:
            src = fitz.open(path)
            app.doc.insert_pdf(src)
            src.close()
        assert len(app.doc) == original_count + 1

        app._undo()
        assert len(app.doc) == original_count
        assert before_digests == [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        app._redo()
        assert len(app.doc) == original_count + 1

        app._undo()
        assert len(app.doc) == original_count
        assert before_digests == [_page_digest(app.doc[i]) for i in range(len(app.doc))]


# ===== 挿入失敗ロールバック・複製Undoタイミング（V190-SAFE-04/05・Phase01 Plan04）=====


class TestInsertRollback:
    """複数ファイル挿入が途中で失敗した場合のロールバック検証（V190-SAFE-04）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin + PageOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _check_doc(self):
                return self.doc is not None

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_insert_failure_rolls_back_pages_and_undo_stack(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """2ファイル目の insert_pdf で例外 → ページ数・Undoスタック長・全ページ
        digest 列が操作前と一致する（既存ページを削除していないことも同時に担保）"""
        import pagefolio.page_ops as po

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        before_undo_len = len(app._undo_stack)

        errors = []
        monkeypatch.setattr(
            po.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        original_insert_pdf = fitz.Document.insert_pdf
        call_count = {"n": 0}

        def flaky_insert_pdf(self_doc, src, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("2ファイル目で失敗")
            return original_insert_pdf(self_doc, src, **kwargs)

        monkeypatch.setattr(fitz.Document, "insert_pdf", flaky_insert_pdf)

        app._do_insert([multi_pdf_files[1], multi_pdf_files[2]], 1)

        assert len(app.doc) == original_count
        assert len(app._undo_stack) == before_undo_len
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_digests == before_digests
        assert len(errors) == 1

    def test_insert_failure_closes_source_documents(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """挿入ループ途中の例外後も、開かれた挿入元 Document はすべて close
        されている（probe: concurrency・D-09）"""
        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        app = self._make_fake_app(sample_pdf_doc)
        monkeypatch.setattr(po.messagebox, "showerror", lambda *a, **k: None)

        opened_docs = []
        original_open_path_as_pdf = fo.FileOpsMixin._open_path_as_pdf

        def tracking_open_path_as_pdf(self_app, path):
            doc = original_open_path_as_pdf(self_app, path)
            opened_docs.append(doc)
            return doc

        monkeypatch.setattr(
            fo.FileOpsMixin, "_open_path_as_pdf", tracking_open_path_as_pdf
        )

        original_insert_pdf = fitz.Document.insert_pdf
        call_count = {"n": 0}

        def flaky_insert_pdf(self_doc, src, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("2ファイル目で失敗")
            return original_insert_pdf(self_doc, src, **kwargs)

        monkeypatch.setattr(fitz.Document, "insert_pdf", flaky_insert_pdf)

        app._do_insert([multi_pdf_files[1], multi_pdf_files[2]], 1)

        assert len(opened_docs) == 2
        assert all(d.is_closed for d in opened_docs)

    def test_insert_failure_single_file_boundary(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """1ファイル目で即例外 → ページ数・Undoスタック長が操作前と同じ
        （probe: boundary）"""
        import pagefolio.page_ops as po

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        before_undo_len = len(app._undo_stack)
        monkeypatch.setattr(po.messagebox, "showerror", lambda *a, **k: None)

        def failing_insert_pdf(self_doc, src, **kwargs):
            raise RuntimeError("1ファイル目で失敗")

        monkeypatch.setattr(fitz.Document, "insert_pdf", failing_insert_pdf)

        app._do_insert([multi_pdf_files[0]], 1)

        assert len(app.doc) == original_count
        assert len(app._undo_stack) == before_undo_len

    def test_insert_empty_path_list_boundary(self, sample_pdf_doc):
        """ordered_paths が空 → ページ数不変・例外なし・件数0の insert state が
        1件積まれる通常の成功扱い（probe: boundary）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        before_undo_len = len(app._undo_stack)

        app._do_insert([], 1)

        assert len(app.doc) == original_count
        assert len(app._undo_stack) == before_undo_len + 1
        assert app._undo_stack[-1]["op"] == "insert"
        assert app._undo_stack[-1]["data"][1] == 0

    def test_rollback_failure_warns_and_keeps_undo_state(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """挿入失敗の巻き戻し（delete_page）自体も失敗 → 警告ダイアログが1回
        表示され、Undoスタック最上位の insert state の件数が実際の挿入数に
        なっている。その state を使った undo で残存ページを正しく取り除ける
        （D-10）"""
        import pagefolio.page_ops as po

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        monkeypatch.setattr(po.messagebox, "showerror", lambda *a, **k: None)
        warnings = []
        monkeypatch.setattr(
            po.messagebox, "showwarning", lambda t, m: warnings.append((t, m))
        )

        original_insert_pdf = fitz.Document.insert_pdf
        call_count = {"n": 0}

        def flaky_insert_pdf(self_doc, src, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("2ファイル目で失敗")
            return original_insert_pdf(self_doc, src, **kwargs)

        monkeypatch.setattr(fitz.Document, "insert_pdf", flaky_insert_pdf)

        original_delete_page = fitz.Document.delete_page

        def failing_delete_page(self_doc, *a, **kw):
            raise RuntimeError("巻き戻し失敗")

        monkeypatch.setattr(fitz.Document, "delete_page", failing_delete_page)

        app._do_insert([multi_pdf_files[1], multi_pdf_files[2]], 1)

        assert len(warnings) == 1
        assert len(app._undo_stack) == 1
        assert app._undo_stack[-1]["op"] == "insert"
        assert app._undo_stack[-1]["data"][1] == 2  # 実際の挿入数

        # delete_page を復元し、残された state で undo すると残存ページを
        # 正しく取り除けることを確認する
        monkeypatch.setattr(fitz.Document, "delete_page", original_delete_page)
        app._undo()
        assert len(app.doc) == original_count


class TestDuplicateUndoTiming:
    """ページ複製の Undo 記録が実処理成功後に確定することの検証（V190-SAFE-05）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin + PageOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _check_doc(self):
                return self.doc is not None

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_duplicate_failure_leaves_pages_and_undo_stack_unchanged(
        self, sample_pdf_doc, monkeypatch
    ):
        """_duplicate_page の insert_pdf が例外 → ページ数・Undoスタック長・
        digest 列が不変で、エラーダイアログが1回表示される"""
        import pagefolio.page_ops as po

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        before_undo_len = len(app._undo_stack)

        errors = []
        monkeypatch.setattr(
            po.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        def failing_insert_pdf(self_doc, src, **kwargs):
            raise RuntimeError("複製に失敗")

        monkeypatch.setattr(fitz.Document, "insert_pdf", failing_insert_pdf)

        app._duplicate_page()

        assert len(app.doc) == original_count
        assert len(app._undo_stack) == before_undo_len
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_digests == before_digests
        assert len(errors) == 1

    def test_duplicate_success_records_undo_after_work(self, sample_pdf_doc):
        """正常系: duplicate state が1件積まれ、current_page が pno+1 になり、
        undo でページ数が元に戻る（後置化が成功パスを壊していないことの担保）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)
        pno = app.current_page

        app._duplicate_page()

        assert len(app.doc) == original_count + 1
        assert len(app._undo_stack) == 1
        assert app._undo_stack[-1]["op"] == "duplicate"
        assert app.current_page == pno + 1

        app._undo()
        assert len(app.doc) == original_count


# ファイル相対で pagefolio/file_ops.py を解決（CWD 非依存・WR-04）
_FILE_OPS_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "pagefolio" / "file_ops.py"
)


def _is_fitz_open_call(node):
    """node が `fitz.open(...)` 呼び出しかどうかを判定する（WR-04）。"""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "fitz"
    )


def _try_closes_tmp_in_finally(node):
    """node が `finally:` の中で `tmp.close()` を呼ぶ `ast.Try` かどうかを
    判定する（WR-04）。"""
    if not isinstance(node, ast.Try):
        return False
    for stmt in node.finalbody:
        for sub in ast.walk(stmt):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "close"
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "tmp"
            ):
                return True
    return False


def _iter_statement_lists(tree):
    """AST 内の `body`/`orelse`/`finalbody` を持つ全ノードの文リストを
    順に返す（WR-04）。"""
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(node, field, None)
            if isinstance(stmts, list):
                yield stmts


class TestTempDocumentCloseGuard:
    """pagefolio/file_ops.py の一時 fitz.Document（`tmp`）が、mutation が
    例外を送出しても必ず close されることを AST 解析で恒久的に固定する
    （WR-04）。tests/test_font_hardcode_guard.py のソース走査ガードと同型。
    """

    def test_temp_documents_are_finally_closed_guard(self):
        """`tmp = fitz.open(...)` の代入がある文リストには、それ以降に
        `finally: tmp.close()` を持つ `ast.Try` が必ず存在することを検証
        する。違反時は該当行番号を添えて失敗させる。"""
        source = _FILE_OPS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations = []
        for stmts in _iter_statement_lists(tree):
            for i, stmt in enumerate(stmts):
                is_tmp_assign = (
                    isinstance(stmt, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id == "tmp" for t in stmt.targets
                    )
                    and _is_fitz_open_call(stmt.value)
                )
                if not is_tmp_assign:
                    continue
                rest = stmts[i + 1 :]
                if not any(_try_closes_tmp_in_finally(s) for s in rest):
                    violations.append(stmt.lineno)
        assert not violations, (
            f"tmp = fitz.open(...) が finally: tmp.close() で保護されていない"
            f"行（pagefolio/file_ops.py）: {violations}"
        )


class TestUndoRedoRestoreFailure:
    """_undo / _redo の復元失敗時に state を保全しブロッキング通知する検証
    （V190-UNDO-01・D-13/D-14）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def test_undo_restore_failure_returns_state_to_stack(
        self, sample_pdf_doc, monkeypatch
    ):
        """_restore_state が例外を送出 → pop した state が _push_evicting 経由で
        undo スタックへ戻り、showerror が1回呼ばれ、_dispose_state は呼ばれない"""
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        app._save_undo("rotate", targets=[0])
        app.doc[0].set_rotation(90)

        before_undo_len = len(app._undo_stack)
        before_redo_len = len(app._redo_stack)

        dispose_calls = []
        monkeypatch.setattr(
            fo.FileOpsMixin,
            "_dispose_state",
            lambda self_app, state: dispose_calls.append(state),
        )

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        def failing_restore_state(self_app, state):
            raise RuntimeError("復元失敗")

        monkeypatch.setattr(fo.FileOpsMixin, "_restore_state", failing_restore_state)

        app._undo()

        assert len(app._undo_stack) == before_undo_len
        assert len(app._redo_stack) == before_redo_len
        assert len(errors) == 1
        assert dispose_calls == []

    def test_redo_restore_failure_returns_state_to_stack(
        self, sample_pdf_doc, monkeypatch
    ):
        """_redo 側でも _undo と同型の保護がかかる（pop した state が
        _push_evicting 経由で redo スタックへ戻る）"""
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        app._save_undo("rotate", targets=[0])
        app.doc[0].set_rotation(90)
        app._undo()  # 正常系で redo スタックへ積む（rotation は 0 に戻る）

        before_undo_len = len(app._undo_stack)
        before_redo_len = len(app._redo_stack)

        dispose_calls = []
        monkeypatch.setattr(
            fo.FileOpsMixin,
            "_dispose_state",
            lambda self_app, state: dispose_calls.append(state),
        )
        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        def failing_restore_state(self_app, state):
            raise RuntimeError("redo 復元失敗")

        monkeypatch.setattr(fo.FileOpsMixin, "_restore_state", failing_restore_state)

        app._redo()

        assert len(app._redo_stack) == before_redo_len
        assert len(app._undo_stack) == before_undo_len
        assert len(errors) == 1
        assert dispose_calls == []

    def test_undo_retry_after_failure_uses_same_state(
        self, sample_pdf_doc, monkeypatch
    ):
        """1回目の undo 失敗後、_restore_state を正常化して2回目の undo を
        呼ぶと同じ state で復元が成功する（履歴が失われていない＝Blobが
        解放されていないことの担保）"""
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        app._save_undo("rotate", targets=[0])
        app.doc[0].set_rotation(90)

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        original_restore_state = fo.FileOpsMixin._restore_state
        call_count = {"n": 0}

        def flaky_restore_state(self_app, state):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("1回目は失敗")
            return original_restore_state(self_app, state)

        monkeypatch.setattr(fo.FileOpsMixin, "_restore_state", flaky_restore_state)

        app._undo()  # 1回目: 失敗
        assert app.doc[0].rotation == 90  # 復元されていない
        assert len(app._undo_stack) == 1

        app._undo()  # 2回目: 同じ state で成功
        assert app.doc[0].rotation == 0
        assert len(app._undo_stack) == 0
        assert len(app._redo_stack) == 1

    def test_delete_undo_partial_failure_preserves_remaining_and_retry_completes(
        self, sample_pdf_doc, monkeypatch
    ):
        """CR-01 回帰テスト: delete の undo（複数ページ再挿入ループ）が2件目で
        失敗した場合、(a) doc が重複/欠損なく最終的に正しい状態へ復旧でき、
        (b) undo/redo スタックが整合したまま保たれることを検証する。

        再現条件は REVIEW.md 記載の想定どおり: 2件目以降の Blob 読み込みが
        失敗するケース（ディスク退避ファイルの消失等）を模す。修正前は
        pop した元の（2件ぶんの）state をそのまま undo スタックへ戻して
        いたため、次の undo で1件目に対して再度 insert_pdf が行われ
        ページが重複していた。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("delete", targets=targets)
        for i in sorted(targets, reverse=True):
            app.doc.delete_page(i)
        assert len(app.doc) == original_count - len(targets)

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        real_blob_bytes = fo.FileOpsMixin._blob_bytes
        call_count = {"n": 0}

        def flaky_blob_bytes(data):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("blob 読み込み失敗（模擬）")
            return real_blob_bytes(data)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_blob_bytes", staticmethod(flaky_blob_bytes)
        )

        # 1回目の Undo: 1件目（page 0）は成功して doc へ再挿入され、
        # 2件目（page 1）で失敗する
        app._undo()

        # (a) doc は「1件だけ適用された」部分状態のまま — 重複や余計な削除はない
        assert len(app.doc) == original_count - len(targets) + 1
        assert len(errors) == 1

        # (b) undo スタックには「未適用の1件だけ」を表す state が1つだけ残る
        #     （元の2件ぶんの state をそのまま戻していない）
        assert len(app._undo_stack) == 1
        remaining_state = app._undo_stack[-1]
        assert remaining_state["op"] == "delete"
        assert len(remaining_state["data"]) == 1
        assert remaining_state["data"][0][0] == 1
        # 復元は失敗しているため redo スタックは変化しない
        assert len(app._redo_stack) == 0

        # 2回目の Undo: 障害条件が解消（3回目以降の呼び出しは成功）され、
        # 残り1件が正しく復元される
        app._undo()
        assert len(app.doc) == original_count
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests
        assert len(app._undo_stack) == 0
        assert len(app._redo_stack) == 1

    def test_delete_redo_partial_failure_preserves_remaining_and_retry_completes(
        self, sample_pdf_doc, monkeypatch
    ):
        """CR-01 回帰テスト: delete_redo（複数ページ再削除ループ）が2件目で
        失敗した場合も、delete と対称に (a)(b) を満たすことを検証する
        （data に blob を使わない delete 系ループでも正しく動作することの
        確認・WR-01 のプレースホルダ化と合わせた回帰防止）。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        targets = [0, 1]
        app._save_undo("delete", targets=targets)
        for i in sorted(targets, reverse=True):
            app.doc.delete_page(i)
        assert len(app.doc) == original_count - len(targets)

        # 正常系で undo（pages 0,1 を復元）→ redo スタックに delete_redo が積まれる
        app._undo()
        assert len(app.doc) == original_count
        assert len(app._redo_stack) == 1
        assert app._redo_stack[-1]["op"] == "delete_redo"

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        real_delete_page = app.doc.delete_page
        call_count = {"n": 0}

        def flaky_delete_page(pno):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("delete_page 失敗（模擬）")
            return real_delete_page(pno)

        monkeypatch.setattr(app.doc, "delete_page", flaky_delete_page)

        # 1回目の Redo: delete_redo は降順(1,0)で削除するため、
        # 1件目(page 1)は成功し2件目(page 0)で失敗する
        app._redo()

        assert len(app.doc) == original_count - 1
        assert len(errors) == 1
        assert len(app._redo_stack) == 1
        remaining_state = app._redo_stack[-1]
        assert remaining_state["op"] == "delete_redo"
        assert len(remaining_state["data"]) == 1
        assert remaining_state["data"][0][0] == 0
        assert len(app._undo_stack) == 0

        # 2回目の Redo: 障害条件を解除して残り1件を削除しきる（重複削除は起きない）
        app._redo()
        assert len(app.doc) == original_count - len(targets)
        assert len(app._redo_stack) == 0
        assert len(app._undo_stack) == 1

    def test_delete_undo_partial_retry_then_redo_undo_roundtrip(
        self, sample_pdf_doc, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト（01-VERIFICATION.md Evidence 3）: delete の
        undo が2件目で失敗 → 再試行成功 → その後の redo で「当初 delete
        対象だった全ページ」が削除されることを検証する。cb5344e（CR-01）は
        『再試行成功直後の doc/スタック状態』までしか検証しておらず、この
        後続の redo でページ構成が破損する新欠陥（バグの移し替え）を
        検出できていなかった。修正前は再試行成功直後の redo_stack が
        『再試行時に実際に処理した残存分のみ』に縮小されており、redo
        しても1ページしか削除されなかった。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("delete", targets=targets)
        for i in sorted(targets, reverse=True):
            app.doc.delete_page(i)
        assert len(app.doc) == original_count - len(targets)

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_blob_bytes = fo.FileOpsMixin._blob_bytes
        call_count = {"n": 0}

        def flaky_blob_bytes(data):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("blob 読み込み失敗（模擬）")
            return real_blob_bytes(data)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_blob_bytes", staticmethod(flaky_blob_bytes)
        )

        # 1回目の Undo: page 0 のみ復元・page 1 で失敗
        app._undo()
        assert len(app.doc) == original_count - len(targets) + 1

        # 2回目の Undo: 障害解消後、残り1件が正しく復元される
        app._undo()
        assert len(app.doc) == original_count
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests

        # 再試行成功直後の redo_stack は「当初の delete 対象2件ぶん」を表す
        assert len(app._redo_stack) == 1
        redo_state = app._redo_stack[-1]
        assert redo_state["op"] == "delete_redo"
        assert len(redo_state["data"]) == 2
        assert {page_i for page_i, _ in redo_state["data"]} == {0, 1}

        # Redo: 両ページとも削除される（欠陥時は1ページしか削除されなかった）
        app._redo()
        assert len(app.doc) == original_count - len(targets)

        # さらに Undo: 元の内容へ完全に戻る
        app._undo()
        assert len(app.doc) == original_count
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_digests

    def test_delete_redo_partial_retry_then_undo_redo_roundtrip(
        self, sample_pdf_doc, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト: delete_redo の redo が2件目で失敗 →
        再試行成功 → その後の undo→redo でページ構成・内容が完全に元へ
        戻ることを検証する（delete 側と対称の往復・Evidence 3 の
        delete_redo 版）。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("delete", targets=targets)
        for i in sorted(targets, reverse=True):
            app.doc.delete_page(i)
        assert len(app.doc) == original_count - len(targets)

        # 正常系で undo（pages 0,1 を復元）→ redo スタックに delete_redo が積まれる
        app._undo()
        assert len(app.doc) == original_count
        assert len(app._redo_stack) == 1
        assert app._redo_stack[-1]["op"] == "delete_redo"

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_delete_page = app.doc.delete_page
        call_count = {"n": 0}

        def flaky_delete_page(pno):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("delete_page 失敗（模擬）")
            return real_delete_page(pno)

        monkeypatch.setattr(app.doc, "delete_page", flaky_delete_page)

        # 1回目の Redo: delete_redo は降順(1,0)で削除するため、
        # 1件目(page 1)は成功し2件目(page 0)で失敗する
        app._redo()
        assert len(app.doc) == original_count - 1

        # 2回目の Redo: 障害解消後、残り1件も削除しきる（重複削除は起きない）
        app._redo()
        assert len(app.doc) == original_count - len(targets)

        # 再試行成功直後の undo_stack は「当初の全2件ぶんの実データ」を表す
        # （欠陥時は再試行時に処理した1件のみに縮小されていた）
        assert len(app._undo_stack) == 1
        undo_state = app._undo_stack[-1]
        assert undo_state["op"] == "delete"
        assert len(undo_state["data"]) == 2
        assert {page_i for page_i, _ in undo_state["data"]} == {0, 1}
        for _page_i, blob in undo_state["data"]:
            assert blob is not None

        # Undo: 両ページとも復元される（欠陥時は1件しか復元されなかった）
        app._undo()
        assert len(app.doc) == original_count
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests

        # さらに Redo: 元のシーケンスと一致する（両ページ削除）
        app._redo()
        assert len(app.doc) == original_count - len(targets)

    def test_page_edit_partial_retry_then_redo_undo_roundtrip(
        self, sample_pdf_doc, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト: page_edit の undo が2件目で失敗 →
        再試行成功 → その後の redo で両ページとも編集後の内容に戻り、
        さらに undo で編集前の内容に戻ることを検証する。
        """
        import pagefolio.file_ops as fo
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_fake_app(sample_pdf_doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("page_edit", targets=targets)
        rect = fitz.Rect(60, 50, 300, 110)
        for i in targets:
            RedactOpsMixin._redact_page(app.doc[i], rect)
        after_edit_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_blob_bytes = fo.FileOpsMixin._blob_bytes
        call_count = {"n": 0}

        def flaky_blob_bytes(data):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("blob 読み込み失敗（模擬）")
            return real_blob_bytes(data)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_blob_bytes", staticmethod(flaky_blob_bytes)
        )

        # 1回目の Undo: page 0 のみ復元・page 1 で失敗
        app._undo()

        # 2回目の Undo: 障害解消後、残り1件も復元される
        app._undo()
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 両ページとも編集後の内容に戻る（欠陥時は1件しか反映されなかった）
        app._redo()
        after_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_edit_digests == after_redo_digests

        # さらに Undo: 編集前の内容へ完全に戻る
        app._undo()
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_digests

    def test_insert_undo_partial_retry_then_redo_undo_roundtrip(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト: insert_undo の redo（再挿入）が2件目で
        失敗 → 再試行成功 → その後の undo で挿入分がすべて消え、再度 redo
        すると挿入後の内容に戻ることを検証する。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        insert_at = 1
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        num = len(src)
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = num

        after_insert_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # Undo: 挿入分が消える（insert_undo が redo_stack に積まれる）
        app._undo()
        assert len(app.doc) == len(before_digests)
        assert app._redo_stack[-1]["op"] == "insert_undo"

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_blob_bytes = fo.FileOpsMixin._blob_bytes
        call_count = {"n": 0}

        def flaky_blob_bytes(data):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("blob 読み込み失敗（模擬）")
            return real_blob_bytes(data)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_blob_bytes", staticmethod(flaky_blob_bytes)
        )

        # 1回目の Redo: 1件目のみ再挿入・2件目で失敗
        app._redo()

        # 2回目の Redo: 障害解消後、残り1件も再挿入される
        app._redo()
        after_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_insert_digests == after_redo_digests

        # さらに Undo: 挿入分がすべて消える（欠陥時は1件しか消えなかった）
        app._undo()
        final_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_undo_digests

        # 再度 Redo: 挿入後の内容に戻る
        app._redo()
        final_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_insert_digests == final_redo_digests

    def test_insert_redo_partial_retry_then_undo_redo_roundtrip(
        self, sample_pdf_doc, multi_pdf_files, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト: insert_redo の undo（再挿入分の削除）
        が2件目で失敗 → 再試行成功 → その後の redo で挿入分がすべて戻り、
        再度 undo すると挿入前の内容に戻ることを検証する。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        insert_at = 1
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        num = len(src)
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = num

        after_insert_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        app._undo()  # insert_undo が redo_stack に積まれる
        assert len(app.doc) == len(before_digests)

        app._redo()  # insert_redo（成功）が undo_stack に積まれる
        assert app._undo_stack[-1]["op"] == "insert_redo"
        after_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_insert_digests == after_redo_digests

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_delete_page = app.doc.delete_page
        call_count = {"n": 0}

        def flaky_delete_page(pno):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("delete_page 失敗（模擬）")
            return real_delete_page(pno)

        monkeypatch.setattr(app.doc, "delete_page", flaky_delete_page)

        # 1回目の Undo: 1件目は削除成功・2件目で失敗
        app._undo()

        # 2回目の Undo: 障害解消後、残り1件も削除される
        app._undo()
        final_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_undo_digests

        # Redo: 挿入分がすべて戻る（欠陥時は1件しか戻らなかった）
        app._redo()
        final_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_insert_digests == final_redo_digests

        # さらに Undo: 挿入前の内容に戻る
        app._undo()
        last_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == last_digests

    def test_merge_resize_undo_partial_failure_preserves_remaining_and_retry_completes(
        self, monkeypatch
    ):
        """CR-01 回帰テスト: merge_resize の undo は「結合ページ削除」→
        「元ページ2件再挿入」の2フェーズで構成される。2フェーズ目の途中で
        失敗した場合、(a) 結合ページの二重削除が起きず最終的に正しい状態へ
        復旧でき、(b) undo/redo スタックが整合したまま保たれることを検証
        する（"_merged_page_deleted" フラグによる再試行時のスキップ制御の
        回帰防止）。
        """
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self):
                doc = fitz.open()
                for i in range(4):
                    page = doc.new_page(width=595, height=842)
                    page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp()
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)

        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        assert len(app.doc) == 3  # 4 - 2 + 1（結合ページ）
        assert len(app._undo_stack) == 1
        assert app._undo_stack[-1]["op"] == "merge_resize"

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        real_insert_pdf = app.doc.insert_pdf
        call_count = {"n": 0}

        def flaky_insert_pdf(src, start_at=-1, **kw):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("insert_pdf 失敗（模擬）")
            return real_insert_pdf(src, start_at=start_at, **kw)

        monkeypatch.setattr(app.doc, "insert_pdf", flaky_insert_pdf)

        # 1回目の Undo: 結合ページ削除（成功）→ 元ページ1件目挿入（成功）→
        # 元ページ2件目挿入で失敗
        app._undo()

        assert len(app.doc) == 3  # 結合ページ削除+1件復元 = 2-1+1... (3-1+1)
        assert len(errors) == 1
        assert len(app._undo_stack) == 1
        remaining_state = app._undo_stack[-1]
        assert remaining_state["op"] == "merge_resize"
        assert remaining_state["data"]["_merged_page_deleted"] is True
        assert len(remaining_state["data"]["orig_pages"]) == 1
        assert len(app._redo_stack) == 0

        # 2回目の Undo: "_merged_page_deleted" フラグにより結合ページを
        # 再度削除しようとしない（誤って別ページを削除しない）。
        # 残り1件を挿入して完了する。
        app._undo()

        assert len(app.doc) == 4
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests
        assert len(app._undo_stack) == 0
        assert len(app._redo_stack) == 1

    def _make_full_fake_app(self, n_pages=4):
        """FileOpsMixin + PageOpsMixin を使う FakeApp を生成する
        （merge_resize 系の駆動用。ページ数を引数で指定できる）。

        雛形: TestAllOpsUndoRedoRoundtrip._make_full_fake_app と、
        test_merge_resize_undo_partial_failure_preserves_remaining_and_retry_completes
        にインライン定義されている FakeApp。
        """
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, n):
                doc = fitz.open()
                for i in range(n):
                    page = doc.new_page(width=595, height=842)
                    page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(n_pages)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_merge_resize_undo_partial_retry_then_redo_undo_roundtrip(
        self, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト（01-VERIFICATION.md Evidence 4）:
        merge_resize の undo（結合ページ削除→元ページ再挿入）が2件目の
        元ページ再挿入で失敗 → 再試行成功 → その後の redo で結合ページの
        内容が結合直後と一致し（欠陥時は Page1 が重複し内容が壊れた）、
        さらに undo で結合前の内容へ完全に戻ることを検証する。
        """
        import pagefolio.file_ops as fo

        app = self._make_full_fake_app(n_pages=4)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        assert len(app.doc) == 3
        after_merge_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_insert_pdf = app.doc.insert_pdf
        call_count = {"n": 0}

        def flaky_insert_pdf(src, start_at=-1, **kw):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("insert_pdf 失敗（模擬）")
            return real_insert_pdf(src, start_at=start_at, **kw)

        monkeypatch.setattr(app.doc, "insert_pdf", flaky_insert_pdf)

        # 1回目の Undo: 結合ページ削除 → 元ページ1件目挿入（成功）→ 2件目で失敗
        app._undo()

        # 2回目の Undo: 障害解消後、残り1件も挿入される
        app._undo()
        assert len(app.doc) == 4
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 結合ページの内容が結合直後と一致する
        # （欠陥時は Page1 が重複し内容が壊れていた＝Evidence 4）
        app._redo()
        assert len(app.doc) == 3
        after_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_merge_digests == after_redo_digests

        # さらに Undo: 結合前の内容へ完全に戻る
        app._undo()
        assert len(app.doc) == 4
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_digests

    def test_merge_resize_redo_partial_retry_then_undo_redo_roundtrip(
        self, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト: merge_resize_undo の redo（元ページ削除
        →結合ページ再挿入）が2件目の元ページ削除で失敗 → 再試行成功 →
        その後の undo/redo でページ構成・内容が完全に往復することを検証
        する。
        """
        import pagefolio.file_ops as fo

        app = self._make_full_fake_app(n_pages=4)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        assert len(app.doc) == 3
        after_merge_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # 正常系で undo（4ページへ復旧）→ redo スタックに merge_resize_undo が積まれる
        app._undo()
        assert len(app.doc) == 4
        assert app._redo_stack[-1]["op"] == "merge_resize_undo"

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_delete_page = app.doc.delete_page
        call_count = {"n": 0}

        def flaky_delete_page(pno):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("delete_page 失敗（模擬）")
            return real_delete_page(pno)

        monkeypatch.setattr(app.doc, "delete_page", flaky_delete_page)

        # 1回目の Redo: 元ページ1件目は削除成功・2件目で失敗
        app._redo()

        # 2回目の Redo: 障害解消後、残り1件も削除され結合ページが再挿入される
        app._redo()
        assert len(app.doc) == 3
        after_retry_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_merge_digests == after_retry_digests

        # Undo: 結合前の内容へ完全に戻る（欠陥時は内容が破損した状態で確定していた）
        app._undo()
        assert len(app.doc) == 4
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # 再度 Redo: 結合直後の内容に戻る
        app._redo()
        assert len(app.doc) == 3
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_merge_digests == final_digests

    def test_merge_undo_partial_retry_roundtrip_inverse_unaffected(
        self, sample_pdf_doc, monkeypatch
    ):
        """V190-UNDO-01 非該当ピン（merge_undo）: merge_undo の逆デルタは
        old_count のみを運ぶスカラーであり per-page データを運ばないため、
        他 7 op で発生する「縮小逆デルタが次段へ伝搬する」欠陥の対象外で
        あることを、同型の部分失敗→再試行→往復テストで明示的に固定する。

        merge_undo の restore（元ページの再追加ループ）が2件目で失敗しても、
        再試行成功直後に構築される次段の逆デルタ（op="merge"）は old_count
        というスカラーのみであり、部分失敗の影響を一切受けない。
        """
        import pagefolio.file_ops as fo

        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: 2ページぶんの内容を結合（末尾に追加）
        app._save_undo("merge")
        merged_texts = ["Merged Page A", "Merged Page B"]
        for text in merged_texts:
            src = fitz.open()
            page = src.new_page(width=595, height=842)
            page.insert_text((72, 72), text, fontsize=20)
            app.doc.insert_pdf(src)
            src.close()
        assert len(app.doc) == original_count + 2
        after_merge_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # 1手目 Undo: 結合ページが除去される（merge_undo が redo_stack に積まれる）
        app._undo()
        assert len(app.doc) == original_count
        assert app._redo_stack[-1]["op"] == "merge_undo"

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        real_blob_bytes = fo.FileOpsMixin._blob_bytes
        call_count = {"n": 0}

        def flaky_blob_bytes(data):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("blob 読み込み失敗（模擬）")
            return real_blob_bytes(data)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_blob_bytes", staticmethod(flaky_blob_bytes)
        )

        # 2手目 Redo: 1件目のみ再追加・2件目で失敗
        app._redo()
        assert len(app.doc) == original_count + 1

        # 3手目 Redo: 障害解消後、残り1件も再追加される（merge_undo の再試行成功）
        app._redo()
        assert len(app.doc) == original_count + 2
        after_retry_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_merge_digests == after_retry_digests

        # 再試行成功直後に構築される次段の逆デルタ（merge_undo → merge）は
        # old_count のみのスカラーであり、部分失敗の影響を受けない
        # （merge_undo が本欠陥の非該当であることの直接証拠。redo() は
        # 復元結果を undo_stack へ積むため、確認対象は undo_stack 側）
        assert app._undo_stack[-1]["op"] == "merge"
        assert isinstance(app._undo_stack[-1]["data"], int)
        assert app._undo_stack[-1]["data"] == original_count

        # 4手目 Undo: 結合前の内容に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_second_undo_digests = [
            _page_digest(app.doc[i]) for i in range(len(app.doc))
        ]
        assert before_digests == after_second_undo_digests

        # 5手目 Redo: 結合後の内容に戻る
        app._redo()
        assert len(app.doc) == original_count + 2
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_merge_digests == final_digests

    def test_page_edit_insert_failure_rolls_back_and_retry_preserves_neighbors(
        self, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト（01-VERIFICATION.md Evidence B・CR-02・
        option-b）: page_edit の undo が、差し替えページ挿入は成功したが
        旧ページの delete_page が失敗した場合、挿入済みページを取り除く
        ロールバックを試み、ロールバックが成功すれば通常の部分失敗（強い
        警告ではない）として扱われることを検証する。障害解消後の再試行で
        doc が完全に元へ戻り、当初 page_edit の対象でなかった隣接ページ
        （index 2 = "Page 3"）が巻き添えで削除されないことを確認する。
        """
        import collections

        import pagefolio.file_ops as fo
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_full_fake_app(n_pages=4)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("page_edit", targets=targets)
        rect = fitz.Rect(60, 50, 300, 110)
        for i in targets:
            RedactOpsMixin._redact_page(app.doc[i], rect)

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        # release_log は Blob オブジェクト自体を保持する（id() のみを記録
        # すると release 直後に GC・メモリ再利用されて誤って id が衝突しう
        # るため、既存の test_undo_stress.py の release スパイと同型に、
        # オブジェクト参照を保持したまま id() ベースで比較する）。
        release_log = []
        real_release_blob = fo.FileOpsMixin._release_blob

        def spy_release_blob(blob):
            release_log.append(blob)
            return real_release_blob(blob)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_release_blob", staticmethod(spy_release_blob)
        )

        real_delete_page = fitz.Document.delete_page
        call_count = {"n": 0}

        def flaky_delete_page(self_doc, *a, **kw):
            if self_doc is app.doc:
                call_count["n"] += 1
                if call_count["n"] == 2:
                    raise RuntimeError("delete_page 失敗（模擬）")
            return real_delete_page(self_doc, *a, **kw)

        monkeypatch.setattr(fitz.Document, "delete_page", flaky_delete_page)

        # 1回目の undo: page 0 は成功。page 1 は差し替え挿入まで成功したが
        # 旧ページ削除（2回目の delete_page 呼び出し）で失敗し、直後の
        # ロールバック（3回目の delete_page 呼び出し）は成功する。
        app._undo()

        assert len(errors) == 1
        assert errors[0][1] == "err_undo_restore_failed_partial"
        assert len(app.doc) == 4

        # 2回目の undo（障害解除後の再試行）: 残り1件が正しく復元される
        app._undo()

        assert len(app.doc) == 4
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests
        assert _page_digest(app.doc[2]) == "Page 3"

        counts = collections.Counter(id(b) for b in release_log)
        assert all(c <= 1 for c in counts.values()), (
            f"double-release検出（_release_blob が2回以上呼ばれたBlobあり）: {counts}"
        )

        app._clear_undo_stacks()

    def test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages(
        self, monkeypatch
    ):
        """V190-UNDO-01 回帰テスト（01-VERIFICATION.md Evidence B・CR-02・
        option-b）: page_edit の undo でロールバックに使う delete_page 自体
        も失敗し続ける（回復不能）場合、専用の強い警告
        （err_undo_restore_failed_content_at_risk）が1回だけ表示される
        ことを検証する。障害解消後の再試行で doc が完全に復旧し、その後の
        redo→undo 往復まで内容が一致することを確認する（内容喪失なし・
        隣接ページの巻き添えなし・ページ重複なし）。
        """
        import collections

        import pagefolio.file_ops as fo
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_full_fake_app(n_pages=4)
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        targets = [0, 1]
        app._save_undo("page_edit", targets=targets)
        rect = fitz.Rect(60, 50, 300, 110)
        for i in targets:
            RedactOpsMixin._redact_page(app.doc[i], rect)
        after_edit_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        errors = []
        monkeypatch.setattr(
            fo.messagebox, "showerror", lambda t, m: errors.append((t, m))
        )

        # release_log は Blob オブジェクト自体を保持する（id() のみを記録
        # すると release 直後に GC・メモリ再利用されて誤って id が衝突しう
        # るため、既存の test_undo_stress.py の release スパイと同型に、
        # オブジェクト参照を保持したまま id() ベースで比較する）。
        release_log = []
        real_release_blob = fo.FileOpsMixin._release_blob

        def spy_release_blob(blob):
            release_log.append(blob)
            return real_release_blob(blob)

        monkeypatch.setattr(
            fo.FileOpsMixin, "_release_blob", staticmethod(spy_release_blob)
        )

        real_delete_page = fitz.Document.delete_page
        call_count = {"n": 0}
        disabled = {"v": False}

        def flaky_delete_page(self_doc, *a, **kw):
            if self_doc is app.doc:
                call_count["n"] += 1
                if call_count["n"] >= 2 and not disabled["v"]:
                    raise RuntimeError("delete_page 失敗（模擬・回復不能）")
            return real_delete_page(self_doc, *a, **kw)

        monkeypatch.setattr(fitz.Document, "delete_page", flaky_delete_page)

        # 1回目の undo: page 0 は成功。page 1 は旧ページ削除もロールバック
        # も両方失敗し、専用の強い警告が1回だけ表示される。
        app._undo()

        assert len(errors) == 1
        assert errors[0][1] == "err_undo_restore_failed_content_at_risk"

        # 障害を解除して undo を再試行する
        disabled["v"] = True
        app._undo()

        assert len(app.doc) == 4
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Redo: 両ページとも編集後の内容に戻る
        app._redo()
        after_redo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_edit_digests == after_redo_digests

        # さらに Undo: 編集前の内容へ完全に戻る
        app._undo()
        final_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == final_digests

        counts = collections.Counter(id(b) for b in release_log)
        assert all(c <= 1 for c in counts.values()), (
            f"double-release検出（_release_blob が2回以上呼ばれたBlobあり）: {counts}"
        )

        app._clear_undo_stacks()

    def test_restore_failure_closes_temp_document(self, sample_pdf_doc, monkeypatch):
        """WR-04: delete の undo と merge_resize_undo の redo で insert_pdf
        が失敗しても、pagefolio.file_ops 名前空間の fitz.open が返した全
        Document が確実に close されることを検証する（AST ガードの実行時
        裏取り）。"""
        import pagefolio.file_ops as fo

        monkeypatch.setattr(fo.messagebox, "showerror", lambda *a, **k: None)

        # --- ケース1: delete の undo ---
        app = self._make_fake_app(sample_pdf_doc)
        targets = [0, 1]
        app._save_undo("delete", targets=targets)
        for i in sorted(targets, reverse=True):
            app.doc.delete_page(i)

        opened_docs = []
        real_fitz_open = fo.fitz.open

        def spy_open(*a, **kw):
            d = real_fitz_open(*a, **kw)
            opened_docs.append(d)
            return d

        with monkeypatch.context() as m:
            m.setattr(fo.fitz, "open", spy_open)

            real_insert_pdf = fitz.Document.insert_pdf
            call_count = {"n": 0}

            def flaky_insert_pdf(self_doc, *a, **kw):
                if self_doc is app.doc:
                    call_count["n"] += 1
                    if call_count["n"] == 1:
                        raise RuntimeError("insert_pdf 失敗（模擬）")
                return real_insert_pdf(self_doc, *a, **kw)

            m.setattr(fitz.Document, "insert_pdf", flaky_insert_pdf)

            app._undo()

        assert opened_docs
        assert all(d.is_closed for d in opened_docs)

        # --- ケース2: merge_resize_undo の redo ---
        app2 = self._make_full_fake_app(n_pages=4)
        app2._do_merge_resize([0, 1], "horizontal", 1190, 842)
        app2._undo()  # merge_resize_undo が redo_stack に積まれる
        assert app2._redo_stack[-1]["op"] == "merge_resize_undo"

        opened_docs2 = []
        real_fitz_open2 = fo.fitz.open

        def spy_open2(*a, **kw):
            d = real_fitz_open2(*a, **kw)
            opened_docs2.append(d)
            return d

        with monkeypatch.context() as m:
            m.setattr(fo.fitz, "open", spy_open2)

            real_insert_pdf2 = fitz.Document.insert_pdf
            call_count2 = {"n": 0}

            def flaky_insert_pdf2(self_doc, *a, **kw):
                if self_doc is app2.doc:
                    call_count2["n"] += 1
                    if call_count2["n"] == 1:
                        raise RuntimeError("insert_pdf 失敗（模擬）")
                return real_insert_pdf2(self_doc, *a, **kw)

            m.setattr(fitz.Document, "insert_pdf", flaky_insert_pdf2)

            app2._redo()

        assert opened_docs2
        assert all(d.is_closed for d in opened_docs2)

    def test_undo_empty_stack_is_noop(self, sample_pdf_doc):
        """空スタックに対する undo はステータス表示のみで Document を
        変更しない"""
        app = self._make_fake_app(sample_pdf_doc)
        original_rotation = app.doc[0].rotation
        statuses = []
        app._set_status = lambda msg: statuses.append(msg)

        app._undo()

        assert app.doc[0].rotation == original_rotation
        assert statuses == ["undo_empty"]


# ===== bulk_move ロジック =====


class TestBulkMoveLogic:
    """bulk_move: doc.select() の逆順列ラウンドトリップ検証"""

    def test_bulk_move_select_roundtrip(self, sample_pdf_doc):
        """doc.select(new_order) → 逆順列で doc.select(inverse) → 元の順序に戻る"""
        doc = sample_pdf_doc  # 3ページ: Page 1, Page 2, Page 3
        # ページ 0 と 2 を選択し、末尾に移動する new_order = [1, 0, 2]
        new_order = [1, 0, 2]
        doc.select(new_order)
        assert "Page 2" in doc[0].get_text()
        # 逆順列を計算
        inverse = [0] * len(new_order)
        for i, v in enumerate(new_order):
            inverse[v] = i
        doc.select(inverse)
        assert "Page 1" in doc[0].get_text()
        assert "Page 2" in doc[1].get_text()
        assert "Page 3" in doc[2].get_text()

    def test_bulk_move_new_order_construction(self, sample_pdf_doc):
        """selected_pages + dest から new_order が正しく構築される"""
        doc = sample_pdf_doc  # 3ページ
        n = len(doc)
        selected_pages = {0, 2}  # ページ 0 と 2 を選択
        dest = 3  # 末尾にドロップ
        sorted_sel = sorted(selected_pages)
        non_selected = [p for p in range(n) if p not in selected_pages]
        sel_before_dest = sum(1 for p in selected_pages if p < dest)
        adj_dest = dest - sel_before_dest
        adj_dest = max(0, min(adj_dest, len(non_selected)))
        new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
        # new_order は permutation
        assert sorted(new_order) == list(range(n))
        # non_selected (page 1) が先頭、選択ページが末尾
        assert new_order == [1, 0, 2]


# ===== bulk_crop ロジック =====


class TestBulkCropLogic:
    """bulk_crop: 複数ページ cropbox ラウンドトリップ検証"""

    def test_bulk_crop_multi_page_roundtrip(self, sample_pdf_doc):
        """複数ページに cropbox 適用 → 旧データで全ページ復元できる"""
        doc = sample_pdf_doc
        targets = [0, 1, 2]
        # 旧 cropbox を保存（Undo データ構築と同じ）
        crop_data = []
        for i in targets:
            cb = doc[i].cropbox
            crop_data.append((i, (cb.x0, cb.y0, cb.x1, cb.y1)))
        # 各ページにトリミング適用
        for i in targets:
            page = doc[i]
            mb = page.mediabox
            new_rect = fitz.Rect(mb.x0 + 20, mb.y0 + 20, mb.x1 - 20, mb.y1 - 20)
            page.set_cropbox(new_rect)
            assert doc[i].cropbox.x0 > crop_data[i][1][0]
        # Undo: 旧 cropbox で復元（_restore_state の bulk_crop ロジックと同等）
        for page_i, (x0, y0, x1, y1) in crop_data:
            doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        for i in targets:
            cb = doc[i].cropbox
            assert abs(cb.x0 - crop_data[i][1][0]) < 1
            assert abs(cb.y0 - crop_data[i][1][1]) < 1

    def test_bulk_crop_relative_coords(self, sample_pdf_doc):
        """相対座標変換: 異なる mediabox サイズのページでも比率が保たれる"""
        doc = sample_pdf_doc
        # current_page (0) の mediabox で相対比率を計算
        cur_mb = doc[0].mediabox
        # 中央 50% の領域を選択したとする
        x0_pdf, y0_pdf = cur_mb.width * 0.1, cur_mb.height * 0.1
        x1_pdf, y1_pdf = cur_mb.width * 0.9, cur_mb.height * 0.9
        rel = (
            x0_pdf / cur_mb.width,
            y0_pdf / cur_mb.height,
            x1_pdf / cur_mb.width,
            y1_pdf / cur_mb.height,
        )
        # 同じ比率を別ページに適用
        for i in [0, 1, 2]:
            mb = doc[i].mediabox
            new_x0 = mb.x0 + rel[0] * mb.width
            new_y0 = mb.y0 + rel[1] * mb.height
            new_x1 = mb.x0 + rel[2] * mb.width
            new_y1 = mb.y0 + rel[3] * mb.height
            # 比率が保たれている（X 軸・Y 軸ともに）
            assert abs((new_x0 - mb.x0) / mb.width - rel[0]) < 0.001
            assert abs((new_x1 - mb.x0) / mb.width - rel[2]) < 0.001
            assert abs((new_y0 - mb.y0) / mb.height - rel[1]) < 0.001
            assert abs((new_y1 - mb.y0) / mb.height - rel[3]) < 0.001


# ===== _check_split_overwrite =====


class TestCheckSplitOverwrite:
    """_check_split_overwrite のモックテスト。

    Tkinter の messagebox.askyesno に依存するメソッドを
    モック置換してロジック部分を検証する。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        """テスト用の簡易オブジェクト"""

        class FakeApp:
            def _t(self, key):
                return key

        self.app = FakeApp()
        self.app._check_split_overwrite = (
            pagefolio.PDFEditorApp._check_split_overwrite.__get__(self.app)
        )

    def test_no_existing_files_returns_true(self, tmp_path):
        """同名ファイルが存在しなければ True を返す（ダイアログ不要）"""
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is True

    @patch("pagefolio.page_ops.messagebox.askyesno", return_value=True)
    def test_existing_files_user_accepts(self, mock_ask, tmp_path):
        """同名ファイルが存在し、ユーザーが Yes を選択 → True"""
        (tmp_path / "a.pdf").write_text("dummy")
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is True
        mock_ask.assert_called_once()

    @patch("pagefolio.page_ops.messagebox.askyesno", return_value=False)
    def test_existing_files_user_declines(self, mock_ask, tmp_path):
        """同名ファイルが存在し、ユーザーが No を選択 → False"""
        (tmp_path / "a.pdf").write_text("dummy")
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is False
        mock_ask.assert_called_once()


# ===== ページ結合・リサイズ =====


class TestMergeResizeLogic:
    """ページ結合・リサイズロジックのテスト (v1.1.0)"""

    def test_horizontal_merge_two_a4_to_a3(self):
        """A4 縦×2 を横並びで結合すると A3 横サイズになる"""
        doc = fitz.open()
        for _ in range(2):
            doc.new_page(width=595, height=842)  # A4 portrait

        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=out_w, height=out_h)
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(offset, 0, offset + r.width, r.height), doc, src_pno
            )
            offset += r.width

        assert new_page.rect.width == 1190
        assert new_page.rect.height == 842
        assert len(new_doc) == 1
        new_doc.close()
        doc.close()

    def test_vertical_merge_two_a4(self):
        """A4 縦×2 を縦並びで結合すると幅 595 / 高さ 1684 になる"""
        doc = fitz.open()
        for _ in range(2):
            doc.new_page(width=595, height=842)

        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = max(r.width for r in rects)
        out_h = sum(r.height for r in rects)

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=out_w, height=out_h)
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(0, offset, r.width, offset + r.height), doc, src_pno
            )
            offset += r.height

        assert new_page.rect.width == 595
        assert new_page.rect.height == 1684
        new_doc.close()
        doc.close()

    def test_merge_replaces_originals(self):
        """結合実行で元ページは削除され、合計ページ数が想定通り減る"""
        doc = fitz.open()
        for i in range(4):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"P{i + 1}", fontsize=20)
        targets = [1, 2]

        # 結合後の new_page を doc に挿入
        rects = [doc[i].rect for i in targets]
        new_doc = fitz.open()
        new_page = new_doc.new_page(
            width=sum(r.width for r in rects),
            height=max(r.height for r in rects),
        )
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(offset, 0, offset + r.width, r.height), doc, src_pno
            )
            offset += r.width

        insert_at = targets[0]
        doc.insert_pdf(new_doc, start_at=insert_at)
        new_doc.close()
        for i in sorted(targets, reverse=True):
            doc.delete_page(i + 1)

        # 元 4 ページ - 2 ページ + 1 ページ = 3 ページ
        assert len(doc) == 3
        # 挿入位置に結合ページが入っている
        assert doc[insert_at].rect.width == 1190
        doc.close()

    def test_three_a4_horizontal_merge(self):
        """A4 縦×3 を横並びで結合すると 1785×842 になる"""
        doc = fitz.open()
        for _ in range(3):
            doc.new_page(width=595, height=842)

        targets = [0, 1, 2]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)
        assert out_w == 595 * 3
        assert out_h == 842
        doc.close()

    def test_mixed_sizes_horizontal(self):
        """サイズが異なるページを横並びで結合（高さは最大値）"""
        doc = fitz.open()
        doc.new_page(width=595, height=842)  # A4
        doc.new_page(width=420, height=595)  # A5
        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)
        assert out_w == 595 + 420
        assert out_h == 842
        doc.close()


class TestPageEditRedactMosaic:
    """page_edit op（黒塗り・モザイク）の undo/redo 往復と適用ロジックの検証"""

    def _make_fake_app(self, doc):
        """FileOpsMixin + RedactOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.redact_ops as ro

        class FakeApp(fo.FileOpsMixin, ro.RedactOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_page_edit_roundtrip(self, sample_pdf_doc):
        """page_edit: 黒塗り → undo で復元（digest 一致）→ redo で再黒塗り"""
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_fake_app(sample_pdf_doc)
        before_digest = _page_digest(app.doc[0])
        assert "Page 1" in app.doc[0].get_text()

        # do: 黒塗り適用（テキストを覆う矩形）
        app._save_undo("page_edit", targets=[0])
        RedactOpsMixin._redact_page(app.doc[0], fitz.Rect(60, 50, 300, 110))
        assert "Page 1" not in app.doc[0].get_text()
        after_digest = _page_digest(app.doc[0])

        # undo: ページ内容が完全に復元される
        app._undo()
        assert len(app.doc) == 3
        assert "Page 1" in app.doc[0].get_text()
        assert _page_digest(app.doc[0]) == before_digest

        # redo: 黒塗りが再適用される
        app._redo()
        assert "Page 1" not in app.doc[0].get_text()
        assert _page_digest(app.doc[0]) == after_digest

        # 二往復目も安定（対称 op の入れ替わり検証）
        app._undo()
        assert _page_digest(app.doc[0]) == before_digest

        # pdf_bytes キーなし（op 別デルタ不変条件）
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_page_edit_multi_page(self, sample_pdf_doc):
        """page_edit: 複数ページ一括適用 → undo で全ページ復元"""
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_fake_app(sample_pdf_doc)
        digests = [_page_digest(app.doc[i]) for i in range(3)]

        app._save_undo("page_edit", targets=[0, 1, 2])
        for i in range(3):
            RedactOpsMixin._redact_page(app.doc[i], fitz.Rect(60, 50, 300, 110))
            assert f"Page {i + 1}" not in app.doc[i].get_text()

        app._undo()
        for i in range(3):
            assert _page_digest(app.doc[i]) == digests[i]
            assert f"Page {i + 1}" in app.doc[i].get_text()

    def test_redact_removes_text_permanently(self, sample_pdf_doc):
        """黒塗りは保存後もテキストが復元不能（真の墨消し）"""
        from pagefolio.redact_ops import RedactOpsMixin

        doc = sample_pdf_doc
        RedactOpsMixin._redact_page(doc[0], fitz.Rect(60, 50, 300, 110))
        # 保存 → 再オープンしても消えている
        reopened = fitz.open(stream=doc.tobytes(), filetype="pdf")
        assert "Page 1" not in reopened[0].get_text()
        reopened.close()

    def test_mosaic_removes_text_and_inserts_image(self, sample_pdf_doc):
        """モザイクは下地テキストを実削除し、ピクセル化画像を焼き込む"""
        from pagefolio.redact_ops import RedactOpsMixin

        page = sample_pdf_doc[0]
        n_before = len(page.get_images(full=True))
        RedactOpsMixin._mosaic_page(page, fitz.Rect(60, 50, 300, 110))
        assert "Page 1" not in page.get_text()
        assert len(page.get_images(full=True)) > n_before

    def test_page_rect_from_rel_clamp(self, sample_pdf_doc):
        """相対座標→ページ矩形変換: mediabox クランプと空・微小の除外"""
        from pagefolio.redact_ops import RedactOpsMixin

        page = sample_pdf_doc[0]  # 595x842
        r = RedactOpsMixin._page_rect_from_rel(page, (0.1, 0.1, 0.5, 0.2))
        assert r is not None
        assert abs(r.x0 - 59.5) < 0.01
        assert abs(r.y1 - 168.4) < 0.01

        # 空矩形 → None
        assert RedactOpsMixin._page_rect_from_rel(page, (0.5, 0.5, 0.5, 0.5)) is None
        # ページ外にはみ出す指定はクランプされる
        r2 = RedactOpsMixin._page_rect_from_rel(page, (-0.5, -0.5, 1.5, 1.5))
        assert r2 is not None
        assert r2.x0 == 0 and r2.y0 == 0
        assert r2.x1 == 595 and r2.y1 == 842


class TestContentOpsUndoFix:
    """insert_blank / watermark / page_numbers の undo no-op バグ修正（v1.7.0）。

    旧実装は _save_undo に存在しない op 名を渡しており、undo しても何も
    起こらなかった。insert_blank は既存 insert op、watermark / page_numbers
    は page_edit op へ置き換えて undo/redo 往復を検証する。
    """

    def _make_app(self, doc):
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po
        import pagefolio.redact_ops as ro

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin, ro.RedactOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.root = None

            def _check_doc(self):
                return self.doc is not None

            def _get_targets(self):
                return sorted(self.selected_pages) or [self.current_page]

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_insert_blank_roundtrip(self, sample_pdf_doc):
        """白紙挿入 → undo でページ数が戻る → redo で再挿入"""
        app = self._make_app(sample_pdf_doc)
        app.current_page = 0
        app._insert_blank_page()
        assert len(app.doc) == 4
        assert app.doc[1].get_text().strip() == ""  # 白紙
        # 白紙ページは元ページ（A4 595×842）とサイズ一致（D-14）
        assert app.doc[1].rect.width == app.doc[0].rect.width
        assert app.doc[1].rect.height == app.doc[0].rect.height

        app._undo()
        assert len(app.doc) == 3
        assert "Page 2" in app.doc[1].get_text()

        app._redo()
        assert len(app.doc) == 4
        assert app.doc[1].get_text().strip() == ""
        assert app.doc[1].rect.width == app.doc[0].rect.width
        assert app.doc[1].rect.height == app.doc[0].rect.height

    def test_watermark_roundtrip(self, sample_pdf_doc, monkeypatch):
        """透かし追加 → undo でテキストが消える → redo で再追加"""
        import pagefolio.page_ops as po

        app = self._make_app(sample_pdf_doc)
        app.selected_pages = {0, 1}
        monkeypatch.setattr(
            po.simpledialog, "askstring", lambda *a, **kw: "CONFIDENTIAL"
        )
        app._add_watermark_text()
        assert "CONFIDENTIAL" in app.doc[0].get_text()
        assert "CONFIDENTIAL" in app.doc[1].get_text()
        assert "CONFIDENTIAL" not in app.doc[2].get_text()

        app._undo()
        for i in range(3):
            assert "CONFIDENTIAL" not in app.doc[i].get_text()
        assert "Page 1" in app.doc[0].get_text()  # 元の内容は保持
        assert "Page 2" in app.doc[1].get_text()  # 両選択ページとも元テキスト保持
        assert "Page 3" in app.doc[2].get_text()  # 未選択ページも不変

        app._redo()
        assert "CONFIDENTIAL" in app.doc[0].get_text()
        assert "CONFIDENTIAL" in app.doc[1].get_text()

    def test_page_numbers_roundtrip(self, sample_pdf_doc):
        """ページ番号印字 → undo で消える → redo で再印字"""
        app = self._make_app(sample_pdf_doc)
        app.selected_pages = {0, 1, 2}
        app._add_page_numbers()
        assert "1 / 3" in app.doc[0].get_text()
        assert "3 / 3" in app.doc[2].get_text()

        app._undo()
        assert "1 / 3" not in app.doc[0].get_text()
        assert "Page 1" in app.doc[0].get_text()
        assert "2 / 3" not in app.doc[1].get_text()
        assert "Page 2" in app.doc[1].get_text()
        assert "3 / 3" not in app.doc[2].get_text()
        assert "Page 3" in app.doc[2].get_text()

        app._redo()
        assert "1 / 3" in app.doc[0].get_text()
        assert "3 / 3" in app.doc[2].get_text()
