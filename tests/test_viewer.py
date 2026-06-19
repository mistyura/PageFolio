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


class TestRotationReflectsInPreviewPixmap:
    """回転が _render_preview_pixmap に即時反映されること（V16-QUAL-01 / D-03）。

    PyMuPDF の set_rotation → get_pixmap は回転を即時反映するため、
    90/270° で pixmap の width/height が入れ替わり、180° では不変になる。
    H1 のバグは pixmap 層ではなく Canvas 層/セレクション意味論にある（Pitfall 1）。
    これらのテストは pixmap 層が回転を正しく反映することの回帰防止アンカー。
    """

    def test_rotate_90_swaps_wh(self):
        """90° 回転で width/height が入れ替わること（400×600 → 600×400 相当）"""
        doc = fitz.open()
        doc.new_page(width=400, height=600)
        stub = _make_stub(doc)
        _, w0, h0 = stub._render_preview_pixmap(0, 1.0)
        doc[0].set_rotation(90)
        _, w1, h1 = stub._render_preview_pixmap(0, 1.0)
        assert (w1, h1) == (h0, w0), (
            f"90° で w/h が入れ替わらない: ({w0},{h0}) → ({w1},{h1})"
        )

    def test_rotate_180_keeps_wh(self):
        """180° 回転で width/height が不変であること"""
        doc = fitz.open()
        doc.new_page(width=400, height=600)
        stub = _make_stub(doc)
        _, w0, h0 = stub._render_preview_pixmap(0, 1.0)
        doc[0].set_rotation(180)
        _, w1, h1 = stub._render_preview_pixmap(0, 1.0)
        assert (w1, h1) == (w0, h0), (
            f"180° で w/h が変化した: ({w0},{h0}) → ({w1},{h1})"
        )

    def test_rotate_270_swaps_wh(self):
        """270° 回転で width/height が入れ替わること"""
        doc = fitz.open()
        doc.new_page(width=400, height=600)
        stub = _make_stub(doc)
        _, w0, h0 = stub._render_preview_pixmap(0, 1.0)
        doc[0].set_rotation(270)
        _, w1, h1 = stub._render_preview_pixmap(0, 1.0)
        assert (w1, h1) == (h0, w0), (
            f"270° で w/h が入れ替わらない: ({w0},{h0}) → ({w1},{h1})"
        )
