# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio.dialogs — 後方互換の再エクスポート集約

既存の `from pagefolio.dialogs import AboutDialog, SettingsDialog, ...` を
サブパッケージ化後も維持するための再エクスポートモジュール。
"""

from pagefolio.dialogs.about import AboutDialog  # noqa: F401
from pagefolio.dialogs.export_images import ExportImagesDialog  # noqa: F401
from pagefolio.dialogs.llm_config import LLMConfigDialog  # noqa: F401
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog  # noqa: F401
from pagefolio.dialogs.plugin import PluginDialog  # noqa: F401
from pagefolio.dialogs.settings import SettingsDialog  # noqa: F401
