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
        monkeypatch.setattr(
            print_ops.os,
            "startfile",
            lambda p, verb: calls.append((p, verb)),
            raising=False,
        )
        app = _DummyPrintApp(doc=_make_doc())
        target = str(tmp_path / "x.pdf")
        app._send_to_printer(target)
        assert calls == [(target, "print")]
        assert app.status is not None
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
