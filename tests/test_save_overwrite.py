"""縮小して保存（上書き）のテスト。
FileOpsMixin の _is_current_file / _overwrite_current_file を
Tk 非依存のダミーアプリで検証する。
"""

import logging
import os
import shutil

import fitz
import pytest

from pagefolio.file_ops import FileOpsMixin


class _DummySaveApp(FileOpsMixin):
    """Tk 非依存で保存ヘルパーを検証するためのダミー"""

    def __init__(self, doc, filepath):
        self.doc = doc
        self.filepath = filepath


@pytest.fixture()
def open_pdf_app(sample_pdf, tmp_path):
    """tmp_path 上のコピーを開いた状態のダミーアプリを返す"""
    copy_path = str(tmp_path / "target.pdf")
    shutil.copy2(sample_pdf, copy_path)
    app = _DummySaveApp(fitz.open(copy_path), copy_path)
    yield app
    try:
        app.doc.close()
    except Exception as e:
        logging.getLogger(__name__).debug("doc.close 失敗: %s", e)


class TestIsCurrentFile:
    """_is_current_file のテスト"""

    def test_same_path(self, open_pdf_app):
        assert open_pdf_app._is_current_file(open_pdf_app.filepath) is True

    def test_different_path(self, open_pdf_app, tmp_path):
        assert open_pdf_app._is_current_file(str(tmp_path / "other.pdf")) is False

    def test_nonexistent_same_normalized_path(self, open_pdf_app, tmp_path):
        # 区切り・相対表記が違っても同一ファイルと判定される
        redundant = str(tmp_path / "." / "target.pdf")
        assert open_pdf_app._is_current_file(redundant) is True

    def test_empty_path(self, open_pdf_app):
        assert open_pdf_app._is_current_file("") is False

    def test_no_filepath_no_name(self):
        # メモリ上のドキュメント（filepath なし）は常に False
        doc = fitz.open()
        doc.new_page()
        app = _DummySaveApp(doc, None)
        assert app._is_current_file("/some/path.pdf") is False
        doc.close()


class TestOverwriteCurrentFile:
    """_overwrite_current_file のテスト"""

    def test_direct_save_to_open_file_fails(self, open_pdf_app):
        """前提の確認: 開いているファイルへの非インクリメンタル直接保存は失敗する"""
        with pytest.raises((ValueError, RuntimeError)):
            open_pdf_app.doc.save(open_pdf_app.filepath, garbage=4, deflate=1, clean=1)

    def test_overwrite_compressed(self, open_pdf_app):
        """縮小保存オプション付きで元ファイルへ上書きできる"""
        path = open_pdf_app.filepath
        open_pdf_app._overwrite_current_file(path, garbage=4, deflate=1, clean=1)
        assert os.path.exists(path)
        assert not os.path.exists(path + ".tmp")
        # doc は新しいファイルから開き直されている
        assert open_pdf_app.doc.name == path
        assert len(open_pdf_app.doc) == 3

    def test_overwrite_preserves_changes(self, open_pdf_app):
        """上書き前の編集（回転）が保存後も保持される"""
        path = open_pdf_app.filepath
        open_pdf_app.doc[0].set_rotation(90)
        open_pdf_app._overwrite_current_file(path, garbage=4, deflate=1, clean=1)
        doc2 = fitz.open(path)
        assert doc2[0].rotation == 90
        assert len(doc2) == 3
        doc2.close()

    def test_overwrite_failure_restores_doc(self, open_pdf_app, tmp_path):
        """書き込み失敗時は doc がメモリ上から復元され操作を継続できる"""
        bad_path = str(tmp_path / "no_such_dir" / "out.pdf")
        with pytest.raises(OSError):
            open_pdf_app._overwrite_current_file(bad_path)
        # doc は復元されており引き続き利用可能
        assert len(open_pdf_app.doc) == 3
        assert "Page 1" in open_pdf_app.doc[0].get_text()
