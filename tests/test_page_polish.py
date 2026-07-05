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


def _make_redact_app(doc, redact_mode=True):
    """_apply_page_edit のTk依存部分を最小スタブ化したFakeApp（D-05/D-06/
    D-07/D-08検証用）。_make_app に redact_mode・crop_rect 関連の Tk
    スタブ（preview_canvas/crop_info_var/crop_overlay_ids/crop_rect_id）
    と settings 辞書を追加する。
    """
    app = _make_app(doc)
    app.redact_mode = redact_mode
    app.crop_mode = False
    app.crop_rect = None
    app.crop_overlay_ids = []
    app.crop_rect_id = None
    app.settings = {}
    app.zoom = 1.0

    class _CropInfoVar:
        def set(self, *_a, **_kw):
            pass

    class _PreviewCanvas:
        def delete(self, *_a, **_kw):
            pass

        def configure(self, *_a, **_kw):
            pass

    app.crop_info_var = _CropInfoVar()
    app.preview_canvas = _PreviewCanvas()
    return app


class TestRedactPolish:
    """黒塗り/モザイクの棚卸し4項目（D-05連続適用・D-06モザイク粒度・
    D-07複数矩形一括適用・D-08回転座標対応）の検証（V171-PAGE-02）。"""

    def test_redact_mode_persist_after_apply(self, sample_pdf_doc):
        """D-05: 適用後もモードがTrueのまま維持される（連続適用）。"""
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        app.crop_rect = (25.0, 25.0, 325.0, 175.0)

        app._apply_page_edit("redact")

        assert app.redact_mode is True
        assert app.crop_rect is None  # 適用済み矩形のみクリア

    def test_mosaic_block_granularity_changes_output(self, sample_pdf_doc, monkeypatch):
        """D-06: block値によって縮小後サイズ（粗さ）が変わる。"""
        from PIL import Image as PILImage

        sizes = []
        orig_resize = PILImage.Image.resize

        def spy_resize(im_self, size, *a, **kw):
            sizes.append(size)
            return orig_resize(im_self, size, *a, **kw)

        monkeypatch.setattr(PILImage.Image, "resize", spy_resize)

        rect = fitz.Rect(60, 50, 300, 110)
        ro.RedactOpsMixin._mosaic_page(sample_pdf_doc[0], rect, block=8)
        small_size_8 = sizes[0]

        sizes.clear()
        ro.RedactOpsMixin._mosaic_page(sample_pdf_doc[1], rect, block=24)
        small_size_24 = sizes[0]

        assert small_size_8[0] > small_size_24[0]
        assert small_size_8[1] > small_size_24[1]

    def test_mosaic_block_default_backward_compatible(self, sample_pdf_doc):
        """D-06: block引数省略時は既存のMOSAIC_BLOCK既定値のまま動作する
        （後方互換）。"""
        page = sample_pdf_doc[2]
        rect = fitz.Rect(60, 50, 300, 110)
        n_images_before = len(page.get_images(full=True))
        ro.RedactOpsMixin._mosaic_page(page, rect)  # block省略
        assert len(page.get_images(full=True)) > n_images_before

    def test_apply_mosaic_uses_mosaic_block_setting(self, sample_pdf_doc, monkeypatch):
        """D-06: _apply_mosaic が settings['mosaic_block'] を _apply_page_edit
        へ渡す。"""
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        app.crop_rect = (25.0, 25.0, 325.0, 175.0)
        app.settings = {"mosaic_block": 20}

        captured = {}
        orig = ro.RedactOpsMixin._apply_page_edit

        def spy(self, kind, block=None):
            captured["block"] = block
            return orig(self, kind, block=block)

        monkeypatch.setattr(ro.RedactOpsMixin, "_apply_page_edit", spy)
        app._apply_mosaic()
        assert captured["block"] == 20

    def test_mosaic_block_label_lang_parity(self):
        assert "mosaic_block_label" in LANG["ja"]
        assert "mosaic_block_label" in LANG["en"]

    def test_multi_rect_apply_single_undo_restores_all(self, sample_pdf_doc):
        """D-07: 複数矩形を一括適用し、1回のundoで全て戻る（情報漏えい
        防止・下地コンテンツは各矩形で個別に実削除される）。"""
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        # pdf(表示)座標で (0,0)-(200,100) は "Page 1" テキストを含む領域、
        # (200,0)-(400,100) は別領域（重複なし・2矩形）
        app._redact_rects = [
            (10.0, 10.0, 310.0, 160.0),
            (310.0, 10.0, 610.0, 160.0),
        ]
        app.crop_rect = None

        assert "Page 1" in app.doc[0].get_text()
        app._apply_page_edit("redact")
        assert "Page 1" not in app.doc[0].get_text()
        assert app._redact_rects == []  # 適用後は蓄積矩形もクリア
        assert app.redact_mode is True  # D-05: モードは継続

        app._undo()
        assert "Page 1" in app.doc[0].get_text()

    def test_multi_rect_apply_calls_save_undo_once(self, sample_pdf_doc, monkeypatch):
        """D-07/Pitfall4: 複数矩形適用でも _save_undo はループ外で1回のみ
        呼ばれる。"""
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        app._redact_rects = [
            (10.0, 10.0, 310.0, 160.0),
            (310.0, 10.0, 610.0, 160.0),
        ]
        app.crop_rect = None

        calls = []
        orig_save_undo = app._save_undo

        def spy_save_undo(*a, **kw):
            calls.append((a, kw))
            return orig_save_undo(*a, **kw)

        monkeypatch.setattr(app, "_save_undo", spy_save_undo)
        app._apply_page_edit("redact")
        assert len(calls) == 1

    def test_redact_derotate_position_matches_rotated_page(
        self, sample_pdf_doc, monkeypatch
    ):
        """D-08: 回転90ページで、_apply_page_edit が _derotate_rect 経由の
        正しい未回転座標で _redact_page を呼ぶ。"""
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        page = app.doc[0]
        page.set_rotation(90)
        # canvas(10,10,310,160) -> _canvas_rect_to_pdf(zoom=1.0) -> 表示pdf
        # 座標(0,0,200,100)
        app.crop_rect = (10.0, 10.0, 310.0, 160.0)

        captured_rects = []
        orig_redact_page = ro.RedactOpsMixin._redact_page

        def spy_redact_page(pg, rect):
            captured_rects.append(rect)
            return orig_redact_page(pg, rect)

        monkeypatch.setattr(
            ro.RedactOpsMixin, "_redact_page", staticmethod(spy_redact_page)
        )

        app._apply_page_edit("redact")

        assert len(captured_rects) == 1
        expected_unrot = po.PageOpsMixin._derotate_rect(page, 0, 0, 200, 100)
        mb = page.mediabox
        expected_rect = fitz.Rect(
            mb.x0 + expected_unrot[0],
            mb.y0 + expected_unrot[1],
            mb.x0 + expected_unrot[2],
            mb.y0 + expected_unrot[3],
        )
        got = captured_rects[0]
        assert abs(got.x0 - expected_rect.x0) < 0.01
        assert abs(got.y0 - expected_rect.y0) < 0.01
        assert abs(got.x1 - expected_rect.x1) < 0.01
        assert abs(got.y1 - expected_rect.y1) < 0.01

    def test_clear_redact_rects_removes_accumulated_state(self, sample_pdf_doc):
        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app._redact_rects = [(1.0, 2.0, 3.0, 4.0)]
        app._redact_rect_overlay_ids = [101, 102]
        app._clear_redact_rects()
        assert app._redact_rects == []
        assert app._redact_rect_overlay_ids == []

    def test_btn_redact_clear_lang_parity(self):
        assert "btn_redact_clear" in LANG["ja"]
        assert "btn_redact_clear" in LANG["en"]

    def test_crop_drag_end_accumulates_multi_rect(self, sample_pdf_doc):
        """D-07: redactモードでのドラッグ完了ごとに _redact_rects へ矩形が
        蓄積される（_crop_drag_end のredact分岐）。"""

        class _StubCanvas:
            def __init__(self):
                self.deleted = []

            def cget(self, _key):
                return ""

            def winfo_width(self):
                return 400

            def winfo_height(self):
                return 500

            def create_rectangle(self, *_a, **_kw):
                return 1

            def coords(self, *_a, **_kw):
                pass

            def delete(self, oid):
                self.deleted.append(oid)

            def canvasx(self, x):
                return x

            def canvasy(self, y):
                return y

            def configure(self, **_kw):
                pass

            def focus_set(self):
                pass

        class _Event:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        app = _make_redact_app(sample_pdf_doc, redact_mode=True)
        app.current_page = 0
        app.preview_canvas = _StubCanvas()
        app.crop_drag_start = None

        app._crop_drag_start(_Event(10, 10))
        app._crop_drag_end(_Event(310, 160))

        assert len(app._redact_rects) == 1
        assert app.crop_rect is None  # 次のドラッグへ備えクリア


def _make_crop_app(doc):
    """_nudge_crop_rect のロジック検証用 FakeApp（D-09）。

    _redraw_crop_overlay は preview_canvas（Tk）へ依存するためスタブ化し、
    移動/リサイズの数値ロジックのみを検証する。
    """

    class FakeCropApp(po.PageOpsMixin):
        def __init__(self, d):
            self.doc = d
            self.current_page = 0
            self.zoom = 1.0
            self.crop_mode = True
            self.redact_mode = False
            self.crop_rect = None

        def _redraw_crop_overlay(self):
            pass

    return FakeCropApp(doc)


class TestCropPolish:
    """_nudge_crop_rect の移動/リサイズロジック検証（D-09）。"""

    def test_nudge_noop_when_rect_unset(self, sample_pdf_doc):
        app = _make_crop_app(sample_pdf_doc)
        app._nudge_crop_rect(1, 0)
        assert app.crop_rect is None

    def test_nudge_noop_when_mode_off(self, sample_pdf_doc):
        app = _make_crop_app(sample_pdf_doc)
        app.crop_mode = False
        app.redact_mode = False
        app.crop_rect = (10.0, 10.0, 50.0, 50.0)
        app._nudge_crop_rect(1, 0)
        assert app.crop_rect == (10.0, 10.0, 50.0, 50.0)

    def test_nudge_move(self, sample_pdf_doc):
        app = _make_crop_app(sample_pdf_doc)
        app.crop_rect = (10.0, 10.0, 50.0, 50.0)
        scale = app.zoom * 1.5
        app._nudge_crop_rect(1, 0)
        sx, sy, ex, ey = app.crop_rect
        assert abs(sx - (10.0 + scale)) < 0.001
        assert abs(ex - (50.0 + scale)) < 0.001
        assert sy == 10.0
        assert ey == 50.0

    def test_nudge_resize(self, sample_pdf_doc):
        app = _make_crop_app(sample_pdf_doc)
        app.crop_rect = (10.0, 10.0, 50.0, 50.0)
        scale = app.zoom * 1.5
        app._nudge_crop_rect(0, 1, resize=True)
        sx, sy, ex, ey = app.crop_rect
        assert sx == 10.0
        assert sy == 10.0
        assert ex == 50.0
        assert abs(ey - (50.0 + scale)) < 0.001

    def test_nudge_redact_mode_also_works(self, sample_pdf_doc):
        app = _make_crop_app(sample_pdf_doc)
        app.crop_mode = False
        app.redact_mode = True
        app.crop_rect = (10.0, 10.0, 50.0, 50.0)
        scale = app.zoom * 1.5
        app._nudge_crop_rect(0, -1)
        sx, sy, ex, ey = app.crop_rect
        assert abs(sy - (10.0 - scale)) < 0.001


class TestMarginCrop:
    """compute_margin_crop_rect（純関数）と _crop_by_margin（FakeApp）の
    検証（D-10）。"""

    def test_margin_crop_basic_subtraction(self):
        cb = fitz.Rect(0, 0, 200, 100)
        result = po.compute_margin_crop_rect(cb, 10, 10, 5, 5)
        assert result == (5, 10, 195, 90)

    def test_margin_crop_too_small_returns_none(self):
        cb = fitz.Rect(0, 0, 10, 10)
        result = po.compute_margin_crop_rect(cb, 5, 5, 5, 5)
        assert result is None

    def test_margin_crop_negative_margin_allowed_by_function(self):
        # 純関数自体は負値もそのまま計算する（入力側の minvalue=0 でガード）
        cb = fitz.Rect(0, 0, 200, 100)
        result = po.compute_margin_crop_rect(cb, -5, 0, 0, 0)
        assert result[1] == -5  # y0 = cb.y0 + margin_top(-5)

    def test_margin_crop_apply_and_undo(self, sample_pdf_doc, monkeypatch):
        app = _make_app(sample_pdf_doc)
        app.current_page = 0
        values = iter([10.0, 10.0, 5.0, 5.0])  # top, bottom, left, right (mm)
        monkeypatch.setattr(po.simpledialog, "askfloat", lambda *a, **kw: next(values))
        orig_cb = app.doc[0].cropbox

        app._crop_by_margin()
        new_cb = app.doc[0].cropbox
        assert new_cb.width < orig_cb.width
        assert new_cb.height < orig_cb.height

        app._undo()
        restored_cb = app.doc[0].cropbox
        assert abs(restored_cb.width - orig_cb.width) < 0.02
        assert abs(restored_cb.height - orig_cb.height) < 0.02

    def test_margin_crop_cancel_is_noop(self, sample_pdf_doc, monkeypatch):
        app = _make_app(sample_pdf_doc)
        monkeypatch.setattr(po.simpledialog, "askfloat", lambda *a, **kw: None)
        orig_cb = app.doc[0].cropbox

        app._crop_by_margin()

        assert app.doc[0].cropbox == orig_cb
        assert len(app._undo_stack) == 0
