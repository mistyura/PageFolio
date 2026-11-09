# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""後方互換の公開 API。起動排他前には GUI/OCR をロードしない。"""

from importlib import import_module

_EXPORTS = {
    "app": ("PDFEditorApp",),
    "constants": ("APP_VERSION", "LANG", "THEMES", "C"),
    "dialogs": (
        "AboutDialog",
        "MergeOrderDialog",
        "MergeResizeDialog",
        "PluginDialog",
        "SettingsDialog",
    ),
    "ocr": (
        "OCR_PROMPTS",
        "OCRMixin",
        "build_provider",
        "has_embedded_text",
        "page_to_png_b64",
        "run_parallel",
    ),
    "plugins": ("PDFEditorPlugin", "PluginManager"),
    "settings": (
        "_apply_theme",
        "_detect_system_theme",
        "_get_settings_path",
        "_load_settings",
        "_make_font",
        "_resolve_theme",
        "_save_settings",
        "get_current_font_size",
        "set_current_font_size",
    ),
}
__all__ = [name for names in _EXPORTS.values() for name in names]


def __getattr__(name):
    for module, names in _EXPORTS.items():
        if name in names:
            value = getattr(import_module(f"pagefolio.{module}"), name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
