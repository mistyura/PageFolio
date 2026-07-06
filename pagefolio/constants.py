# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""定数定義 — バージョン・ファイル名・拡張子定数 + themes/lang 再エクスポート"""

# themes.py / lang.py からの再エクスポート（後方互換 import 表面を維持）
from pagefolio.lang import LANG  # noqa: F401
from pagefolio.themes import THEMES, C  # noqa: F401

# ===================== バージョン =====================
APP_VERSION = "v1.7.2"

# ===================== ファイル名定数 =====================
SETTINGS_FILE = "pagefolio_settings.json"
PLUGINS_DIR = "plugins"

# ===================== 対応拡張子（D-05）=====================
SUPPORTED_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
)

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"})

# ===================== ページ編集（黒塗り・モザイク）=====================
# モザイクのブロック粗さ（2 倍レンダリング画像に対する縮小率。
# 大きいほど粗いモザイクになる）
MOSAIC_BLOCK = 16

# ===================== 単位換算 =====================
# PDF point <-> mm 換算の単一情報源（1pt = 1/72 inch・D-10/D-11 共通・
# 分散させると桁ズレ/丸め誤差の温床になる）
PT_PER_MM = 72 / 25.4

# ===================== 画像エクスポート =====================
# 長辺ピクセル数プリセット（LLM 読取用途: Claude≈1568 / Gemini≈3072 が目安）
EXPORT_LONG_EDGE_PRESETS = (1024, 1568, 2048, 3072)
DEFAULT_EXPORT_LONG_EDGE = 1568
DEFAULT_EXPORT_JPG_QUALITY = 85
