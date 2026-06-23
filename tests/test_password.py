# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""PDF パスワード（暗号化）対応のテスト。

FileOpsMixin の save_with_password / save_without_password 純ヘルパーと、
_open_path_as_pdf の認証フラグ・_do_set_password / _remove_password を
Tk 非依存のダミーアプリで検証する。
"""

import fitz
import pytest

from pagefolio import file_ops
from pagefolio.constants import LANG
from pagefolio.file_ops import (
    FileOpsMixin,
    PDFPasswordError,
    save_with_password,
    save_without_password,
)


class _DummyApp(FileOpsMixin):
    """Tk 非依存でパスワード関連ヘルパーを検証するダミー。"""

    def __init__(self, doc, filepath=None, lang="ja"):
        self.doc = doc
        self.filepath = filepath
        self.lang = lang
        self.pdf_has_password = False
        self._opened_needed_password = False
        self.status = None

    def _t(self, key):
        return LANG[self.lang].get(key, LANG["ja"].get(key, key))

    def _set_status(self, msg):
        self.status = msg


def _make_doc(pages=3):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=20)
    return doc


class TestSavePasswordHelpers:
    """save_with_password / save_without_password の往復テスト"""

    def test_save_with_password_requires_pass(self, tmp_path):
        doc = _make_doc()
        out = str(tmp_path / "enc.pdf")
        save_with_password(doc, out, "secret")
        doc.close()
        reopened = fitz.open(out)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        assert len(reopened) == 3
        reopened.close()

    def test_wrong_password_fails(self, tmp_path):
        doc = _make_doc()
        out = str(tmp_path / "enc.pdf")
        save_with_password(doc, out, "secret")
        doc.close()
        reopened = fitz.open(out)
        assert reopened.authenticate("wrong") == 0
        reopened.close()

    def test_remove_password_roundtrip(self, tmp_path):
        # 暗号化ファイルを作成 → 開いて認証 → 解除保存 → 平文で開ける
        enc = str(tmp_path / "enc.pdf")
        doc = _make_doc()
        save_with_password(doc, enc, "secret")
        doc.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        dec = str(tmp_path / "dec.pdf")
        save_without_password(opened, dec)
        opened.close()

        plain = fitz.open(dec)
        assert not plain.needs_pass
        assert len(plain) == 3
        plain.close()


class TestOpenPathAuthFlag:
    """_open_path_as_pdf の認証フラグ・キャンセル例外"""

    def test_plain_pdf_flag_false(self, sample_pdf):
        app = _DummyApp(doc=None)
        doc = app._open_path_as_pdf(sample_pdf)
        assert app._opened_needed_password is False
        doc.close()

    def test_encrypted_pdf_authenticated(self, tmp_path, monkeypatch):
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        app = _DummyApp(doc=None)
        # 認証ダイアログの代わりに正しいパスワードで認証する
        monkeypatch.setattr(
            app, "_authenticate_doc", lambda doc, path: bool(doc.authenticate("secret"))
        )
        doc = app._open_path_as_pdf(enc)
        assert app._opened_needed_password is True
        assert len(doc) == 3
        doc.close()

    def test_encrypted_pdf_cancel_raises(self, tmp_path, monkeypatch):
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        app = _DummyApp(doc=None)
        monkeypatch.setattr(app, "_authenticate_doc", lambda doc, path: False)
        with pytest.raises(PDFPasswordError):
            app._open_path_as_pdf(enc)


class TestSetRemovePassword:
    """_do_set_password / _remove_password の保存挙動"""

    def test_do_set_password_writes_encrypted(self, tmp_path, monkeypatch):
        out = str(tmp_path / "out.pdf")
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
        app = _DummyApp(doc=_make_doc(), filepath=None)
        app._do_set_password("secret")
        assert app.status is not None
        reopened = fitz.open(out)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_do_set_password_cancel_dialog(self, tmp_path, monkeypatch):
        # 保存ダイアログをキャンセル（空文字）した場合は何もしない
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: "")
        app = _DummyApp(doc=_make_doc(), filepath=None)
        app._do_set_password("secret")
        assert app.status is None
        app.doc.close()

    def test_remove_password_writes_plain(self, tmp_path, monkeypatch):
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()
        opened = fitz.open(enc)
        opened.authenticate("secret")

        out = str(tmp_path / "plain.pdf")
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
        app = _DummyApp(doc=opened, filepath=enc)
        app.pdf_has_password = True
        app._remove_password()
        plain = fitz.open(out)
        assert not plain.needs_pass
        plain.close()
        opened.close()

    def test_remove_password_no_password_info(self, monkeypatch):
        # パスワード未設定なら情報表示のみで保存ダイアログは出ない
        called = {"info": False, "dialog": False}
        monkeypatch.setattr(
            file_ops.messagebox,
            "showinfo",
            lambda *a, **k: called.__setitem__("info", True),
        )
        monkeypatch.setattr(
            file_ops.filedialog,
            "asksaveasfilename",
            lambda **kw: called.__setitem__("dialog", True),
        )
        app = _DummyApp(doc=_make_doc())
        app.pdf_has_password = False
        app._remove_password()
        assert called["info"] is True
        assert called["dialog"] is False
        app.doc.close()
