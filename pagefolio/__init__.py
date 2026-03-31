# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""PageFolio パッケージ — 後方互換の公開API"""

# 定数
# アプリケーション
from pagefolio.app import PDFEditorApp  # noqa: F401
from pagefolio.constants import APP_VERSION, LANG, THEMES, C  # noqa: F401

# ダイアログ
from pagefolio.dialogs import (  # noqa: F401
    AboutDialog,
    MergeOrderDialog,
    PluginDialog,
    SettingsDialog,
)

# プラグインシステム
from pagefolio.plugins import PDFEditorPlugin, PluginManager  # noqa: F401

# 設定ユーティリティ
from pagefolio.settings import (  # noqa: F401
    _apply_theme,
    _detect_system_theme,
    _get_settings_path,
    _load_settings,
    _make_font,
    _resolve_theme,
    _save_settings,
)
