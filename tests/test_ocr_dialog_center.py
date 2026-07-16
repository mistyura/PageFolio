# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""``OCRDialog._center()`` の画面高クランプ回帰テスト（WR-01・06-REVIEW.md）。

`OCRDialog.__init__` はドキュメント・OCR プロバイダ等を要求する重量級の
コンストラクタのため、`tests/test_toast.py` と同方針でモジュール共有の
隠しルートを使い、実際の `_center()` を最小限の差し替え（フォントサイズ・
`winfo_screenheight`・`geometry` のスパイ）だけで直接呼び出す。
"""

import re

import pytest

tk = pytest.importorskip("tkinter")

from pagefolio import ocr_dialog  # noqa: E402


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


def test_center_height_clamp_floor_matches_minsize(tk_root):
    """WR-01: 低解像度環境でも `_center()` が計算する h は 620 未満に
    クランプされない（= 直後の `self.minsize(960, 620)` と整合する）ことを
    検証する。

    修正前は floor が 320 だったため、画面高が小さい環境では
    `geometry()` に渡す h が 620 未満になり得た。その場合 `geometry()` が
    決めた中心位置（`py - h // 2`）は小さい h を前提に計算されるが、直後の
    `minsize(960, 620)` がウィンドウを 620px まで強制的に成長させるため、
    ウィンドウの下端が想定位置よりさらに下へずれ、画面外にはみ出す
    （06-REVIEW.md WR-01）。
    """
    top = tk.Toplevel(tk_root)
    try:
        # fs=12 -> h = max(680, 12*56=672) = 680（クランプ前の希望高さ）
        top._font_size = lambda: 12
        # 620 + 100px マージンより低い低解像度環境を模す
        top.winfo_screenheight = lambda: 600

        geometry_calls = []
        orig_geometry = tk.Toplevel.geometry

        def _spy_geometry(spec=None):
            if spec is not None:
                geometry_calls.append(spec)
            return orig_geometry(top, spec)

        top.geometry = _spy_geometry

        ocr_dialog.OCRDialog._center(top, tk_root)

        assert geometry_calls, "geometry() が呼ばれていない"
        # x/y オフセットが負の場合 f-string 組み立てにより "+-259" のような
        # 表記になり得るため、幅x高さ部分のみを解析する（座標部分は不問）。
        m = re.match(r"(\d+)x(\d+)", geometry_calls[0])
        assert m is not None, f"想定外の geometry 文字列: {geometry_calls[0]!r}"
        h = int(m.group(2))

        # フロアが minsize(960, 620) の高さ 620 と一致しているため、
        # 位置計算に使われた h は 620 を下回らない。
        assert h >= 620
    finally:
        top.destroy()


def test_center_height_clamp_does_not_exceed_available_screen_room(tk_root):
    """画面高が十分大きい場合はフォント由来の希望高さ(680)がそのまま使われ、
    クランプで不必要に縮められないことを確認する（フロア引き上げの副作用が
    ないことの確認）。
    """
    top = tk.Toplevel(tk_root)
    try:
        top._font_size = lambda: 12  # 希望高さ 680
        top.winfo_screenheight = lambda: 2000  # 十分に大きい画面

        geometry_calls = []
        orig_geometry = tk.Toplevel.geometry

        def _spy_geometry(spec=None):
            if spec is not None:
                geometry_calls.append(spec)
            return orig_geometry(top, spec)

        top.geometry = _spy_geometry

        ocr_dialog.OCRDialog._center(top, tk_root)

        m = re.match(r"(\d+)x(\d+)", geometry_calls[0])
        assert m is not None
        h = int(m.group(2))
        assert h == 680
    finally:
        top.destroy()
