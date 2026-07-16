# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""印刷機能のテスト。

write_print_tempfile 純ヘルパーと _send_to_printer の OS 分岐を
Tk 非依存のダミーアプリで検証する。
"""

import os

import fitz

from pagefolio import print_ops
from pagefolio.constants import LANG
from pagefolio.print_ops import PrintOpsMixin, write_print_tempfile


class _DummyPrintApp(PrintOpsMixin):
    def __init__(self, doc, lang="ja"):
        self.doc = doc
        self.lang = lang
        self.status = None
        self._toast = None

    def _t(self, key):
        return LANG[self.lang].get(key, LANG["ja"].get(key, key))

    def _set_status(self, msg):
        self.status = msg

    def _show_error_or_toast(self, category, title, msg, retry_cb):
        """Tk 非依存ダミー版。UIBuilderMixin と同じフォールバック契約
        （_toast なしなら messagebox.showerror）のみ再現する（V180-QA-02）。
        """
        toast = getattr(self, "_toast", None)
        if toast is not None:
            toast.show(category, msg, retry_cb=retry_cb)
            return
        print_ops.messagebox.showerror(title, msg)


def _make_doc(pages=3):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=20)
    return doc


class TestWritePrintTempfile:
    def test_creates_valid_pdf(self, tmp_path):
        doc = _make_doc()
        path = write_print_tempfile(doc, dirpath=str(tmp_path))
        assert os.path.exists(path)
        assert path.endswith(".pdf")
        reopened = fitz.open(path)
        assert len(reopened) == 3
        reopened.close()
        doc.close()

    def test_reflects_current_state(self, tmp_path):
        # 回転などの編集状態が一時ファイルへ反映される
        doc = _make_doc()
        doc[0].set_rotation(90)
        path = write_print_tempfile(doc, dirpath=str(tmp_path))
        reopened = fitz.open(path)
        assert reopened[0].rotation == 90
        reopened.close()
        doc.close()


class TestSendToPrinter:
    def test_uses_startfile_when_available(self, tmp_path, monkeypatch):
        calls = []

        def fake_startfile(p, verb=None):
            calls.append((p, verb))

        monkeypatch.setattr(print_ops.os, "startfile", fake_startfile, raising=False)
        app = _DummyPrintApp(doc=_make_doc())
        target = str(tmp_path / "x.pdf")
        app._send_to_printer(target)
        assert calls == [(target, "print")]
        assert app.status is not None
        app.doc.close()

    def test_falls_back_to_open_when_print_verb_unassociated(
        self, tmp_path, monkeypatch
    ):
        # 印刷動詞が未関連付け（WinError 1155 相当）→ open 動詞で再試行
        calls = []

        def fake_startfile(p, verb=None):
            calls.append((p, verb))
            if verb == "print":
                raise OSError(1155, "no app associated")

        monkeypatch.setattr(print_ops.os, "startfile", fake_startfile, raising=False)
        app = _DummyPrintApp(doc=_make_doc())
        target = str(tmp_path / "x.pdf")
        app._send_to_printer(target)
        assert calls == [(target, "print"), (target, None)]
        assert "opened" in app.status or app.status is not None
        app.doc.close()

    def test_no_handler_shows_error(self, tmp_path, monkeypatch):
        # print も open も失敗 → エラー表示・status は更新されない
        def fake_startfile(p, verb=None):
            raise OSError(1155, "no app associated")

        monkeypatch.setattr(print_ops.os, "startfile", fake_startfile, raising=False)
        shown = {"error": False}
        monkeypatch.setattr(
            print_ops.messagebox,
            "showerror",
            lambda *a, **k: shown.__setitem__("error", True),
        )
        app = _DummyPrintApp(doc=_make_doc())
        app._send_to_printer(str(tmp_path / "x.pdf"))
        assert shown["error"] is True
        assert app.status is None
        app.doc.close()

    def test_unsupported_os_shows_info(self, tmp_path, monkeypatch):
        # startfile が存在しない OS では情報通知のみ
        monkeypatch.delattr(print_ops.os, "startfile", raising=False)
        shown = {"info": False}
        monkeypatch.setattr(
            print_ops.messagebox,
            "showinfo",
            lambda *a, **k: shown.__setitem__("info", True),
        )
        app = _DummyPrintApp(doc=_make_doc())
        app._send_to_printer(str(tmp_path / "x.pdf"))
        assert shown["info"] is True
        assert app.status is None
        app.doc.close()
