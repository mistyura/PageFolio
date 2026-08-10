# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""PDF パスワード（暗号化）対応のテスト。

FileOpsMixin の save_with_password / save_without_password 純ヘルパーと、
_open_path_as_pdf の認証フラグ・_do_set_password / _remove_password を
Tk 非依存のダミーアプリで検証する。
"""

import types

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
        self.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)

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


class TestSavePathsKeepEncryption:
    """通常の保存経路（Save As・上書き・縮小保存）が暗号化を維持することの
    実ファイル回帰テスト（V190-SAFE-01・D-01〜D-03）。"""

    def test_save_as_keeps_encryption(self, tmp_path, monkeypatch):
        # (1) 暗号化 PDF を tmp_path へ作成
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        # (2) 開き直して認証した Document を _DummyApp に載せる
        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)

        # (3) 保存先を monkeypatch で固定して _save_as() を呼ぶ
        out = str(tmp_path / "saved_as.pdf")
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
        app._save_as()

        # (4) 保存先を開き直して needs_pass / authenticate を実測する
        reopened = fitz.open(out)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        opened.close()

    def test_overwrite_current_file_keeps_encryption(self, tmp_path):
        # _overwrite_current_file を encryption 未指定で呼んでも暗号化が
        # 維持されることを実ファイルで検証する（D-02）
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)
        app.pdf_has_password = True

        app._overwrite_current_file(enc)

        reopened = fitz.open(enc)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_save_file_fallback_keeps_encryption(self, tmp_path, monkeypatch):
        # インクリメンタル保存を失敗させ _overwrite_current_file フォールバック
        # へ落としても暗号化が維持されることを検証する（D-02）
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)
        app.pdf_has_password = True

        monkeypatch.setattr(file_ops.messagebox, "askyesno", lambda *a, **k: True)

        original_save = fitz.Document.save

        def _fake_save(self_doc, *args, **kwargs):
            if kwargs.get("incremental"):
                raise RuntimeError("simulated incremental save failure")
            return original_save(self_doc, *args, **kwargs)

        monkeypatch.setattr(fitz.Document, "save", _fake_save)

        app._save_file()

        reopened = fitz.open(enc)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_save_compressed_overwrite_keeps_encryption(self, tmp_path, monkeypatch):
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)
        app.pdf_has_password = True

        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: enc)
        app._save_compressed()

        reopened = fitz.open(enc)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_save_compressed_new_path_keeps_encryption(self, tmp_path, monkeypatch):
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)
        app.pdf_has_password = True

        out = str(tmp_path / "compressed.pdf")
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
        app._save_compressed()

        reopened = fitz.open(out)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_set_password_kwargs_not_overridden(self, tmp_path, monkeypatch):
        # _do_set_password の同一ファイル上書き経路で AES-256 の明示指定が
        # _overwrite_current_file の KEEP 既定化に上書きされないことを検証する
        path = str(tmp_path / "target.pdf")
        d = _make_doc()
        d.save(path)
        d.close()

        doc = fitz.open(path)
        app = _DummyApp(doc=doc, filepath=path)
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: path)
        app._do_set_password("newsecret")

        assert app.pdf_has_password is True
        reopened = fitz.open(path)
        assert reopened.needs_pass
        assert reopened.authenticate("newsecret") > 0
        reopened.close()
        app.doc.close()

    def test_remove_password_kwargs_not_overridden(self, tmp_path, monkeypatch):
        # _remove_password の同一ファイル上書き経路で needs_pass が 0 になり
        # pdf_has_password が False になることを検証する
        path = str(tmp_path / "target.pdf")
        d = _make_doc()
        save_with_password(d, path, "secret")
        d.close()

        doc = fitz.open(path)
        doc.authenticate("secret")
        app = _DummyApp(doc=doc, filepath=path)
        app.pdf_has_password = True
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: path)
        app._remove_password()

        assert app.pdf_has_password is False
        reopened = fitz.open(path)
        assert not reopened.needs_pass
        reopened.close()
        app.doc.close()

    def test_save_as_twice_keeps_encryption(self, tmp_path, monkeypatch):
        # probe: idempotency — 同一の暗号化 Document に対し _save_as() を
        # 2 回連続で実行しても 2 回目の保存先も暗号化を維持する
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        opened = fitz.open(enc)
        opened.authenticate("secret")
        app = _DummyApp(doc=opened, filepath=enc)

        out = str(tmp_path / "saved_as.pdf")
        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
        app._save_as()
        app._save_as()

        reopened = fitz.open(out)
        assert reopened.needs_pass
        assert reopened.authenticate("secret") > 0
        reopened.close()
        app.doc.close()

    def test_remove_then_save_file_stays_plain(self, tmp_path, monkeypatch):
        # probe: idempotency — パスワード解除後に上書き保存しても再暗号化されない
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        doc = fitz.open(enc)
        doc.authenticate("secret")
        app = _DummyApp(doc=doc, filepath=enc)
        app.pdf_has_password = True

        monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: enc)
        app._remove_password()
        assert app.pdf_has_password is False

        monkeypatch.setattr(file_ops.messagebox, "askyesno", lambda *a, **k: True)
        app._save_file()

        assert app.pdf_has_password is False
        reopened = fitz.open(enc)
        assert not reopened.needs_pass
        reopened.close()
        app.doc.close()

    def test_overwrite_failure_keeps_password_state(self, tmp_path, monkeypatch):
        # probe: concurrency — os.replace が例外を送出した場合、
        # pdf_has_password は呼び出し前の値のまま変化せず、doc は
        # bytes から復元されて使用可能なままである
        enc = str(tmp_path / "enc.pdf")
        d = _make_doc()
        save_with_password(d, enc, "secret")
        d.close()

        doc = fitz.open(enc)
        doc.authenticate("secret")
        app = _DummyApp(doc=doc, filepath=enc)
        app.pdf_has_password = True

        def _fail_replace(*a, **kw):
            raise OSError("simulated os.replace failure")

        monkeypatch.setattr(file_ops.os, "replace", _fail_replace)

        with pytest.raises(OSError):
            app._overwrite_current_file(enc)

        assert app.pdf_has_password is True
        assert len(app.doc) == 3
        app.doc.close()


class TestDerivePdfHasPassword:
    """derive_pdf_has_password の純関数テスト（D-03）。"""

    def test_derive_keep_preserves_current(self):
        assert file_ops.derive_pdf_has_password(True, fitz.PDF_ENCRYPT_KEEP) is True
        assert file_ops.derive_pdf_has_password(False, fitz.PDF_ENCRYPT_KEEP) is False

    def test_derive_aes256_true(self):
        assert file_ops.derive_pdf_has_password(False, fitz.PDF_ENCRYPT_AES_256) is True

    def test_derive_none_false(self):
        assert file_ops.derive_pdf_has_password(True, fitz.PDF_ENCRYPT_NONE) is False
