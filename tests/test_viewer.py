"""ViewerMixin._render_preview_pixmap の回帰テスト（TEST-02 / BUG-03）。

Tk 非依存の純関数ヘルパーを直接呼び出して検証する。
- doc.tobytes() が一切呼ばれないこと（SC-1）
- get_pixmap で妥当な samples（長さ w*h*3、RGB）が得られること（D-09）

さらに V180-PERF-01 のサムネイル仮想化（可視範囲優先描画 + デバウンス）に関する
純ロジックテストを追加する（_render_visible_thumbs の世代ガード等）。
"""

import types

import fitz

from pagefolio.pagination import prioritized_render_order
from pagefolio.thumb_cache import LruCache
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


# ── サムネイル仮想化（V180-PERF-01・05-02）──────────────────────────


class _FakeLabel:
    """lbl.configure(image=...) 呼び出しを記録するだけのスパイ。"""

    def __init__(self):
        self.configured = []

    def configure(self, image=None):
        self.configured.append(image)


def _make_render_stub(n_pages=5, thumb_gen=1, visible_range=(0, 5)):
    """_render_visible_thumbs を Tk root なしで検証するためのスタブを返す。

    _visible_local_range は固定値へ差し替え、_get_thumb_photo はスパイに
    差し替える（Tk root 不要な範囲・PATTERNS.md 純関数のみのテスト方針）。
    """
    labels = [(object(), _FakeLabel()) for _ in range(n_pages)]
    calls = {"get_thumb_photo": []}

    stub = types.SimpleNamespace(
        doc=list(range(n_pages)),
        _thumb_gen=thumb_gen,
        _page_window_start=0,
        _page_size=n_pages,
        thumb_cache=LruCache(300),
        thumb_images=[],
        _thumb_placeholder_labels=labels,
    )

    def fake_get_thumb_photo(i):
        calls["get_thumb_photo"].append(i)
        return f"photo-{i}"

    stub._get_thumb_photo = fake_get_thumb_photo
    stub._visible_local_range = lambda: visible_range
    stub._render_visible_thumbs = ViewerMixin._render_visible_thumbs.__get__(stub)
    return stub, labels, calls


class TestRenderVisibleThumbsGenGuard:
    """_render_visible_thumbs の世代ガード（V180-PERF-01・T-05-05）。"""

    def test_gen_mismatch_is_noop(self):
        """gen が現在の _thumb_gen と不一致なら _get_thumb_photo を一切呼ばない"""
        stub, labels, calls = _make_render_stub(thumb_gen=2)
        stub._render_visible_thumbs(gen=1)
        assert calls["get_thumb_photo"] == [], (
            "gen不一致なのに _get_thumb_photo が呼ばれた"
        )
        assert all(lbl.configured == [] for _frame, lbl in labels)

    def test_no_doc_is_noop(self):
        """doc が None（ファイルを閉じた後）なら No-op"""
        stub, labels, calls = _make_render_stub(thumb_gen=1)
        stub.doc = None
        stub._render_visible_thumbs(gen=1)
        assert calls["get_thumb_photo"] == []

    def test_gen_match_renders_visible_range_only_with_cache_hit_shortcut(self):
        """gen一致時: 可視範囲のみ処理し、キャッシュヒット分は再レンダリングしない"""
        stub, labels, calls = _make_render_stub(
            n_pages=5, thumb_gen=1, visible_range=(1, 3)
        )
        stub.thumb_cache[1] = "cached-photo-1"  # index1 のみ事前キャッシュ済み
        stub._render_visible_thumbs(gen=1)

        assert calls["get_thumb_photo"] == [2], (
            "キャッシュヒット分(index1)まで呼ばれた、"
            "またはミス分(index2)が呼ばれていない"
        )
        assert labels[1][1].configured == ["cached-photo-1"]
        assert labels[2][1].configured == ["photo-2"]
        # 可視範囲外(0,3,4)は触れられない（selected_pages 等への波及もない）
        assert labels[0][1].configured == []
        assert labels[3][1].configured == []
        assert labels[4][1].configured == []


class TestVisibleLocalRangeFallback:
    """_visible_local_range のフォールバック分岐（Tk root不要な純粋な範囲のみ検証）。"""

    def test_no_frames_returns_zero_range(self):
        """thumb_inner にフレームが無い（未生成）場合は (0, 0) を返す"""
        stub = types.SimpleNamespace(
            thumb_inner=types.SimpleNamespace(winfo_children=lambda: [])
        )
        stub._visible_local_range = ViewerMixin._visible_local_range.__get__(stub)
        assert stub._visible_local_range() == (0, 0)

    def test_canvas_not_yet_laid_out_falls_back_to_full_window(self):
        """thumb_canvas.winfo_height() <= 1（未レイアウト）なら窓全体へフォールバック"""
        frames = [object(), object(), object()]
        stub = types.SimpleNamespace(
            thumb_inner=types.SimpleNamespace(winfo_children=lambda: frames),
            thumb_canvas=types.SimpleNamespace(winfo_height=lambda: 1),
        )
        stub._visible_local_range = ViewerMixin._visible_local_range.__get__(stub)
        assert stub._visible_local_range() == (0, len(frames))


class TestPrioritizedRenderOrderViewerIntegration:
    """viewer._build_thumbnails の描画順序契約（可視先頭・残り後続・V180-PERF-01）。"""

    def test_visible_pages_rendered_before_rest_of_window(self):
        """窓 [0,10) 中、可視範囲 [4,7) が先頭に来て残りが後続すること"""
        order = prioritized_render_order(lo=0, hi=10, vis_lo=4, vis_hi=7)
        assert order[:3] == [4, 5, 6], "可視範囲が先頭に来ていない"
        assert set(order) == set(range(10)), "全ページ index が1回ずつ含まれない"
        assert len(order) == 10
