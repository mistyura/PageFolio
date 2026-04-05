"""PDF 操作のテスト。
pagefolio.py のPDF操作ロジックは Tkinter に強く結合しているため、
fitz API を直接使ってアプリと同等の操作が正しく動くことを検証する。
"""

import os
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
    """Undo/Redo のロジックテスト（PDF のバイトコピーベース）"""

    def test_save_and_restore_state(self, sample_pdf_doc):
        """状態の保存と復元（アプリの _save_undo / _restore_state と同等）"""
        # 状態保存（PDF バイト列）
        saved_state = sample_pdf_doc.tobytes()
        original_pages = len(sample_pdf_doc)

        # 変更: ページ削除
        sample_pdf_doc.delete_page(0)
        assert len(sample_pdf_doc) == original_pages - 1

        # 状態復元
        restored_doc = fitz.open("pdf", saved_state)
        assert len(restored_doc) == original_pages
        assert "Page 1" in restored_doc[0].get_text()
        restored_doc.close()

    def test_redo_after_undo(self, sample_pdf_doc):
        """Undo後のRedo（バイト列ベース）"""
        # 初期状態保存
        state_before = sample_pdf_doc.tobytes()

        # 操作: 回転
        sample_pdf_doc[0].set_rotation(90)
        state_after = sample_pdf_doc.tobytes()

        # Undo: 元に戻す
        restored = fitz.open("pdf", state_before)
        assert restored[0].rotation == 0

        # Redo: やり直す
        re_restored = fitz.open("pdf", state_after)
        assert re_restored[0].rotation == 90

        restored.close()
        re_restored.close()


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
