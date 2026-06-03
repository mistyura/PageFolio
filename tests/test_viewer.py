"""ViewerMixin._render_preview_pixmap の回帰テスト（TEST-02 / BUG-03）。

Tk 非依存の純関数ヘルパーを直接呼び出して検証する。
- doc.tobytes() が一切呼ばれないこと（SC-1）
- get_pixmap で妥当な samples（長さ w*h*3、RGB）が得られること（D-09）
"""

import types

import fitz

from pagefolio.viewer import ViewerMixin


def _make_stub(doc):
    """ViewerMixin._render_preview_pixmap を Tk root なしで呼ぶための軽量スタブを返す。

    types.SimpleNamespace に doc 属性を持たせ、
    ViewerMixin の純関数メソッドをバインドする。
    """
    stub = types.SimpleNamespace(doc=doc)
    stub._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(stub)
    return stub


class TestPreviewRender:
    """_render_preview_pixmap の動作検証"""

    def test_render_does_not_call_tobytes(self, sample_pdf_doc, monkeypatch):
        """_render_preview_pixmap が doc.tobytes() を一切呼ばないこと（SC-1）"""
        called = {"n": 0}
        orig = fitz.Document.tobytes

        def spy(self, *a, **k):
            called["n"] += 1
            return orig(self, *a, **k)

        monkeypatch.setattr(fitz.Document, "tobytes", spy)

        stub = _make_stub(sample_pdf_doc)
        stub._render_preview_pixmap(0, 1.0)

        assert called["n"] == 0, "doc.tobytes() が呼ばれた（撤廃されていない）"

    def test_render_returns_valid_samples(self, sample_pdf_doc):
        """_render_preview_pixmap が妥当な samples を返すこと（D-09）

        戻り値 (samples, w, h) について:
        - samples が bytes または bytearray であること
        - len(samples) == w * h * 3（RGB・alpha=False）
        - w > 0 かつ h > 0
        """
        stub = _make_stub(sample_pdf_doc)
        samples, w, h = stub._render_preview_pixmap(0, 1.0)

        assert isinstance(samples, (bytes, bytearray)), "samples の型が不正"
        assert w > 0, "幅が 0 以下"
        assert h > 0, "高さが 0 以下"
        assert len(samples) == w * h * 3, (
            f"samples の長さ ({len(samples)}) が w*h*3 ({w * h * 3}) と一致しない"
        )
