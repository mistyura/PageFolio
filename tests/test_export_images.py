"""画像エクスポート機能のテスト。
page_ops のモジュール関数（parse_page_ranges / compute_export_scale /
export_page_image）と Mixin の対象ページ解決ロジックを検証する。
"""

import os

import fitz
import pytest
from PIL import Image

from pagefolio.constants import (
    DEFAULT_EXPORT_LONG_EDGE,
    EXPORT_LONG_EDGE_PRESETS,
)
from pagefolio.page_ops import (
    PageOpsMixin,
    compute_export_scale,
    export_page_image,
    parse_page_ranges,
)

# ===== ページ範囲パース =====


class TestParsePageRanges:
    """parse_page_ranges（モジュール関数）のテスト"""

    def test_single_page(self):
        assert parse_page_ranges("2", 5) == [(2, 2)]

    def test_range(self):
        assert parse_page_ranges("1-3", 5) == [(1, 3)]

    def test_multiple_parts(self):
        assert parse_page_ranges("1-2, 4", 5) == [(1, 2), (4, 4)]

    def test_invalid_text(self):
        assert parse_page_ranges("abc", 5) is None

    def test_out_of_range(self):
        assert parse_page_ranges("6", 5) is None

    def test_reversed_range(self):
        assert parse_page_ranges("3-1", 5) is None

    def test_empty(self):
        assert parse_page_ranges("", 5) is None


# ===== 倍率計算 =====


class TestComputeExportScale:
    """compute_export_scale のテスト"""

    def test_a4_portrait(self):
        # A4 縦: 長辺 842pt → 1568px
        scale = compute_export_scale(595, 842, 1568)
        assert scale == pytest.approx(1568 / 842)

    def test_landscape_uses_long_edge(self):
        # 横長ページでは幅が長辺になる
        scale = compute_export_scale(842, 595, 1568)
        assert scale == pytest.approx(1568 / 842)

    def test_zero_size_fallback(self):
        assert compute_export_scale(0, 0, 1568) == 1.0

    def test_zero_target_fallback(self):
        assert compute_export_scale(595, 842, 0) == 1.0


# ===== 画像出力 =====


class TestExportPageImage:
    """export_page_image のテスト"""

    def test_png_long_edge(self, sample_pdf_doc, tmp_path):
        out = str(tmp_path / "page.png")
        export_page_image(sample_pdf_doc[0], out, 1568, fmt="png")
        assert os.path.exists(out)
        with Image.open(out) as img:
            assert img.format == "PNG"
            # 丸めにより ±1px の誤差を許容
            assert abs(max(img.size) - 1568) <= 1

    def test_jpg_format(self, sample_pdf_doc, tmp_path):
        out = str(tmp_path / "page.jpg")
        export_page_image(sample_pdf_doc[0], out, 1024, fmt="jpg", jpg_quality=70)
        assert os.path.exists(out)
        with Image.open(out) as img:
            assert img.format == "JPEG"
            assert abs(max(img.size) - 1024) <= 1

    def test_rotation_reflected(self, sample_pdf_doc, tmp_path):
        # 90度回転したページは横長画像として出力される
        page = sample_pdf_doc[1]
        page.set_rotation(90)
        out = str(tmp_path / "rotated.png")
        export_page_image(page, out, 1568, fmt="png")
        with Image.open(out) as img:
            w, h = img.size
            assert w > h
            assert abs(w - 1568) <= 1

    def test_cropbox_reflected(self, sample_pdf_doc, tmp_path):
        # トリミング後は CropBox の縦横比で出力される
        page = sample_pdf_doc[2]
        page.set_cropbox(fitz.Rect(0, 0, 400, 200))
        out = str(tmp_path / "cropped.png")
        export_page_image(page, out, 1000, fmt="png")
        with Image.open(out) as img:
            w, h = img.size
            assert abs(w - 1000) <= 1
            assert abs(h - 500) <= 1

    def test_presets_contain_default(self):
        assert DEFAULT_EXPORT_LONG_EDGE in EXPORT_LONG_EDGE_PRESETS


# ===== 対象ページ解決 =====


class _DummyExportApp(PageOpsMixin):
    """Tk 非依存で _resolve_export_pages を検証するためのダミー"""

    def __init__(self, doc, selected_pages=None):
        self.doc = doc
        self.selected_pages = set(selected_pages or [])


class TestResolveExportPages:
    """PageOpsMixin._resolve_export_pages のテスト"""

    def test_scope_all(self, sample_pdf_doc):
        app = _DummyExportApp(sample_pdf_doc)
        pages = app._resolve_export_pages({"scope": "all"})
        assert pages == [0, 1, 2]

    def test_scope_selected(self, sample_pdf_doc):
        app = _DummyExportApp(sample_pdf_doc, selected_pages={2, 0})
        pages = app._resolve_export_pages({"scope": "selected"})
        assert pages == [0, 2]

    def test_scope_range(self, sample_pdf_doc):
        app = _DummyExportApp(sample_pdf_doc)
        pages = app._resolve_export_pages(
            {"scope": "range", "ranges": [(1, 2), (3, 3)]}
        )
        assert pages == [0, 1, 2]

    def test_scope_range_dedup(self, sample_pdf_doc):
        app = _DummyExportApp(sample_pdf_doc)
        pages = app._resolve_export_pages(
            {"scope": "range", "ranges": [(1, 2), (2, 3)]}
        )
        assert pages == [0, 1, 2]
