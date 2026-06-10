# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""定数定義 — バージョン・ファイル名・拡張子定数 + themes/lang 再エクスポート"""

# themes.py / lang.py からの再エクスポート（後方互換 import 表面を維持）
from pagefolio.lang import LANG  # noqa: F401
from pagefolio.themes import THEMES, C  # noqa: F401

# ===================== バージョン =====================
APP_VERSION = "v1.4.1"

# ===================== ファイル名定数 =====================
SETTINGS_FILE = "pagefolio_settings.json"
PLUGINS_DIR = "plugins"

# ===================== 対応拡張子（D-05）=====================
SUPPORTED_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
)

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"})
