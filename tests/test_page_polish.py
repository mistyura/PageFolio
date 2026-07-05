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


class TestDerotateRect:
    """_derotate_rect の座標変換検証（D-08）。回転0で恒等（正規化のみ）、
    90/180/270 で page.derotation_matrix による正しい逆変換を検証する。"""

    def _make_doc(self, rotation, w=200, h=100):
        doc = fitz.open()
        doc.new_page(width=w, height=h)
        page = doc[0]
        page.set_rotation(rotation)
        return doc, page

    def test_derotate_identity_when_rotation_zero(self):
        doc, page = self._make_doc(0)
        result = po.PageOpsMixin._derotate_rect(page, 10, 20, 60, 80)
        assert result == (10, 20, 60, 80)
        doc.close()

    def test_derotate_identity_normalizes_swapped_points(self):
        doc, page = self._make_doc(0)
        # x0>x1, y0>y1 で渡しても min/max 正規化される
        result = po.PageOpsMixin._derotate_rect(page, 60, 80, 10, 20)
        assert result == (10, 20, 60, 80)
        doc.close()

    def _assert_roundtrip(self, rotation):
        doc, page = self._make_doc(rotation)
        x0, y0, x1, y1 = 10, 20, 60, 80
        rx0, ry0, rx1, ry1 = po.PageOpsMixin._derotate_rect(page, x0, y0, x1, y1)
        # 未回転座標を rotation_matrix で表示座標へ戻すと元の入力に一致する
        rm = page.rotation_matrix
        p0 = fitz.Point(rx0, ry0) * rm
        p1 = fitz.Point(rx1, ry1) * rm
        got = (min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y))
        expected = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        assert all(abs(got[i] - expected[i]) < 0.01 for i in range(4))
        doc.close()

    def test_derotate_rotation_90_roundtrip(self):
        self._assert_roundtrip(90)

    def test_derotate_rotation_180_roundtrip(self):
        self._assert_roundtrip(180)

    def test_derotate_rotation_270_roundtrip(self):
        self._assert_roundtrip(270)


class TestFormatCropInfo:
    """_format_crop_info の mm/％ 文字列検証（D-11・純関数）。"""

    def test_format_crop_info_mm_and_percent(self):
        # 100mm x 50mm 相当の pt サイズ、mediabox 200mm x 100mm 相当 → 25%
        w_pt = 100 * po.PT_PER_MM
        h_pt = 50 * po.PT_PER_MM
        mb_w_pt = 200 * po.PT_PER_MM
        mb_h_pt = 100 * po.PT_PER_MM
        result = po._format_crop_info(w_pt, h_pt, mb_w_pt, mb_h_pt)
        assert "100" in result
        assert "50" in result
        assert "25" in result
        assert "mm" in result
        assert "%" in result

    def test_format_crop_info_zero_mediabox_safe(self):
        result = po._format_crop_info(10, 10, 0, 0)
        assert "0%" in result
