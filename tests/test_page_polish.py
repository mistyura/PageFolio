# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Phase 3（ページ操作磨き込み + v1.5.0 回帰テスト）の新規テストを収容する
専用ファイル（D-15・tests/test_pdf_ops.py の肥大化防止）。

機能別にテストクラスを追加していく。まずは画像透かし（V171-PAGE-01）。
"""

import collections
import types

import fitz

import pagefolio.file_ops as fo
import pagefolio.page_ops as po
import pagefolio.redact_ops as ro
from pagefolio.lang import LANG


def _make_app(doc):
    """tests/test_pdf_ops.py:TestContentOpsUndoFix._make_app と同型の FakeApp。"""

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


def _make_png_bytes(tmp_path, name="logo.png", size=(200, 100), color=(255, 0, 0, 200)):
    from PIL import Image

    path = tmp_path / name
    img = Image.new("RGBA", size, color)
    img.save(path, format="PNG")
    return str(path)


def _make_jpeg_bytes(tmp_path, name="logo.jpg", size=(200, 100), color=(0, 255, 0)):
    from PIL import Image

    path = tmp_path / name
    img = Image.new("RGB", size, color)
    img.save(path, format="JPEG")
    return str(path)


class TestImageWatermarkRect:
    """_watermark_image_rect の純関数検証（fitz.Rect のみ必要・doc 不要）。"""

    def test_center_and_half_width_landscape(self):
        page_rect = fitz.Rect(0, 0, 595, 842)  # A4
        rect = po.PageOpsMixin._watermark_image_rect(page_rect, 200, 100)
        # 幅は約50%に縮小される
        assert abs(rect.width - page_rect.width * 0.5) < 0.01
        # 中央配置: 矩形の中心 == ページの中心
        assert abs((rect.x0 + rect.x1) / 2 - page_rect.width / 2) < 0.01
        assert abs((rect.y0 + rect.y1) / 2 - page_rect.height / 2) < 0.01

    def test_clamped_for_extreme_tall_image(self):
        page_rect = fitz.Rect(0, 0, 595, 842)
        # 縦長画像: 幅50%だと高さがページ高さの90%を超えるため高さ基準クランプ
        rect = po.PageOpsMixin._watermark_image_rect(page_rect, 50, 2000)
        assert rect.height <= page_rect.height * 0.9 + 0.01
        assert abs((rect.x0 + rect.x1) / 2 - page_rect.width / 2) < 0.01


class TestImageWatermark:
    """_add_watermark_image の適用・undo 往復・破損画像ハンドリング。"""

    def test_png_watermark_embeds_image_and_undo_removes_it(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        app = _make_app(sample_pdf_doc)
        app.current_page = 0
        png_path = _make_png_bytes(tmp_path)
        monkeypatch.setattr(po.filedialog, "askopenfilename", lambda **kw: png_path)

        page = app.doc[0]
        n_before = len(page.get_images(full=True))
        app._add_watermark_image()
        assert len(app.doc[0].get_images(full=True)) > n_before

        app._undo()
        assert len(app.doc[0].get_images(full=True)) == n_before
        assert "Page 1" in app.doc[0].get_text()

    def test_jpeg_watermark_embeds_image(self, sample_pdf_doc, monkeypatch, tmp_path):
        app = _make_app(sample_pdf_doc)
        app.selected_pages = {0, 1}
        jpg_path = _make_jpeg_bytes(tmp_path)
        monkeypatch.setattr(po.filedialog, "askopenfilename", lambda **kw: jpg_path)

        n_before_0 = len(app.doc[0].get_images(full=True))
        n_before_1 = len(app.doc[1].get_images(full=True))
        app._add_watermark_image()
        assert len(app.doc[0].get_images(full=True)) > n_before_0
        assert len(app.doc[1].get_images(full=True)) > n_before_1
        # 未選択ページは変化なし
        assert len(app.doc[2].get_images(full=True)) == 0

    def test_no_path_selected_is_noop(self, sample_pdf_doc, monkeypatch):
        app = _make_app(sample_pdf_doc)
        monkeypatch.setattr(po.filedialog, "askopenfilename", lambda **kw: "")
        n_before = len(app.doc[0].get_images(full=True))
        app._add_watermark_image()
        assert len(app.doc[0].get_images(full=True)) == n_before
        assert len(app._undo_stack) == 0

    def test_corrupted_image_shows_error_without_crash(
        self, sample_pdf_doc, monkeypatch, tmp_path
    ):
        app = _make_app(sample_pdf_doc)
        bad_path = tmp_path / "broken.png"
        bad_path.write_bytes(b"not a real image")
        monkeypatch.setattr(
            po.filedialog, "askopenfilename", lambda **kw: str(bad_path)
        )
        errors = []
        monkeypatch.setattr(
            po.messagebox, "showerror", lambda title, msg: errors.append((title, msg))
        )

        app._add_watermark_image()  # 例外送出しない

        assert len(errors) == 1
        assert len(app._undo_stack) == 0
        assert len(app.doc[0].get_images(full=True)) == 0


class TestImageWatermarkLang:
    """btn_watermark_image LANG キーの ja/en 存在確認（UI 生成は Tk 必要なため）。"""

    def test_key_exists_in_both_languages(self):
        assert "btn_watermark_image" in LANG["ja"]
        assert "btn_watermark_image" in LANG["en"]
