# Codebase Structure

**Analysis Date:** 2026-06-10

## Directory Layout

```
PageFolio/
├── pagefolio/                      # Main package (Python module)
│   ├── __init__.py                 # Public API re-exports (backward-compat imports)
│   ├── __main__.py                 # Entry point for `python -m pagefolio`
│   ├── app.py                      # PDFEditorApp main class (Mixin aggregator)
│   ├── constants.py                # APP_VERSION, file extensions, dir paths
│   ├── themes.py                   # Color palette (THEMES dict, C runtime dict)
│   ├── lang.py                     # Localization (LANG ja/en)
│   ├── settings.py                 # JSON I/O, theme application, API key filtering
│   ├── plugins.py                  # PDFEditorPlugin ABC, PluginManager
│   │
│   ├── ui_builder.py               # UIBuilderMixin (ttk styles, layout)
│   ├── file_ops.py                 # FileOpsMixin (open/save, undo/redo)
│   ├── page_ops.py                 # PageOpsMixin (rotate, delete, crop, merge, split)
│   ├── viewer.py                   # ViewerMixin (preview, zoom, thumbnails, selection)
│   ├── dnd.py                      # DnDMixin (drag-and-drop reorder)
│   ├── ocr.py                      # OCRMixin (provider builder, parallel execution, retries)
│   ├── ocr_providers.py            # OCRProvider ABC + concrete backends
│   ├── ocr_dialog.py               # OCRDialog (progress UI, result export)
│   ├── file_drop.py                # TkinterDnD integration for file drag-drop
│   │
│   └── dialogs/                    # Dialog subpackage
│       ├── __init__.py             # Re-exports (backward-compat imports)
│       ├── about.py                # AboutDialog (version, license, links)
│       ├── settings.py             # SettingsDialog (theme, font size, language)
│       ├── plugin.py               # PluginDialog (enable/disable plugins)
│       ├── merge.py                # MergeOrderDialog, MergeResizeDialog
│       └── llm_config.py           # LLMConfigDialog (OCR provider setup)
│
├── pagefolio.py                    # Top-level entry point (imports __main__.main)
├── tests/                          # Test suite (pytest)
│   ├── conftest.py                 # Fixtures (sample PDFs, app factory)
│   ├── test_imports.py             # Package import + backward-compat tests
│   ├── test_utils.py               # Settings/theme utility tests
│   ├── test_pdf_ops.py             # PDF manipulation via fitz directly
│   ├── test_plugins.py             # Plugin discovery/loading/events
│   ├── test_viewer.py              # Preview/thumbnail rendering
│   ├── test_ocr.py                 # OCR helper functions, retry logic
│   ├── test_ocr_providers.py       # Provider unit tests (mocked APIs)
│   ├── test_provider_ui.py         # Provider UI dialog tests
│   ├── test_settings_keyguard.py   # API key non-persistence guard
│   └── __init__.py
│
├── plugins/                        # Plugin directory (user extensions)
│   └── page_info.py                # Sample plugin: display page metadata
│
├── pagefolio.ico                   # Application icon
├── pagefolio_settings.json         # User config (auto-generated, persisted at runtime)
│
├── pyproject.toml                  # Project metadata, Ruff/pytest config
├── requirements.txt                # Fixed-version dependencies
├── README.md                       # User documentation
├── CLAUDE.md                       # AI development instructions (this repo)
├── 開発履歴.md                      # Development changelog (Japanese)
├── LICENSE                         # MIT License
│
├── docs/                           # Screenshot images
├── .planning/                      # GSD planning artifacts
├── .gsd/                           # GSD runtime state
├── .claude/                        # Claude context files
└── PyInstaller files (build/, dist/) when compiled
```

## Directory Purposes

**`pagefolio/`:**
- Purpose: Main application package (importable as `import pagefolio`)
- Contains: Core app class, mixins, OCR system, plugin system, UI dialogs, utilities
- Key files: `app.py`, `constants.py`, `themes.py`, `lang.py`, `settings.py`

**`pagefolio/dialogs/`:**
- Purpose: Modal dialog subpackage (organized from monolithic dialogs.py)
- Contains: 5 dialog classes (About, Settings, Plugin, Merge, LLMConfig)
- Re-exports: Via `__init__.py` for `from pagefolio.dialogs import SettingsDialog` backward compat

**`tests/`:**
- Purpose: pytest test suite (9 modules, ~800 lines)
- Contains: Unit tests for PDF ops, plugins, viewers, OCR, settings security
- Key: Fixtures in `conftest.py` (sample PDF generation, app factory)

**`plugins/`:**
- Purpose: User-installable extension directory
- Contains: Sample plugin `page_info.py` showing plugin API
- Note: Dynamically discovered at runtime; plugins can register OCR providers

## Key File Locations

**Entry Points:**
- `pagefolio.py`: Script entry (calls `__main__.main()`)
- `pagefolio/__main__.py`: Module entry (creates Tk root, PDFEditorApp, runs mainloop)
- `pagefolio/__init__.py`: Package API (re-exports public classes/functions)

**Configuration:**
- `pagefolio/constants.py`: APP_VERSION, SUPPORTED_EXTENSIONS (frozen set), PLUGINS_DIR
- `pagefolio/themes.py`: THEMES dict (dark/light palettes), runtime `C` dict
- `pagefolio/lang.py`: LANG dict (ja/en strings)
- `pagefolio/settings.py`: _load_settings(), _save_settings(), _apply_theme(), _make_font()

**Core Logic:**
- `pagefolio/app.py`: PDFEditorApp class (mixin aggregator, state holder, lifecycle)
- `pagefolio/file_ops.py`: Open, save, undo/redo (snapshot-based)
- `pagefolio/page_ops.py`: Rotate, delete, crop (CropBox), duplicate, merge, split
- `pagefolio/viewer.py`: Preview rendering, zoom, thumbnails, selection UI
- `pagefolio/dnd.py`: Thumbnail D&D reordering (ghost image, indicators)
- `pagefolio/ocr.py`: Provider builder, concurrent execution, retry logic
- `pagefolio/ocr_providers.py`: OCRProvider ABC + LMStudio, Claude, Gemini, Tesseract

**Testing:**
- `tests/conftest.py`: Fixtures, sample PDF factory
- `tests/test_pdf_ops.py`: fitz direct ops (save, delete, crop)
- `tests/test_ocr.py`: Parallel execution, retry helpers
- `tests/test_settings_keyguard.py`: API key isolation verification

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `file_ops.py`, `ui_builder.py`, `page_ops.py`)
- Test files: `test_<feature>.py` (e.g., `test_pdf_ops.py`, `test_plugins.py`)
- Dialogs: Named after feature (`merge.py` for merge dialogs, `llm_config.py` for OCR config)

**Directories:**
- Package: `pagefolio` (main package)
- Subpackage: `pagefolio/dialogs/` (dialog group)
- Test: `tests/` (all tests)
- Plugin: `plugins/` (user extensions)

**Classes:**
- PascalCase: `PDFEditorApp`, `UIBuilderMixin`, `FileOpsMixin`
- Mixin suffix: `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`
- Dialog suffix: `AboutDialog`, `SettingsDialog`, `MergeOrderDialog`
- OCR: `OCRProvider` (ABC), `LMStudioProvider`, `ClaudeProvider`, `GeminiProvider`, `TesseractProvider`

**Methods:**
- Internal/private: `_` prefix (e.g., `_build_styles`, `_refresh_all`, `_set_status`)
- Public API: Plain names (e.g., `discover_plugins`, `load_plugin`, `fire_event`)
- Event handlers: `_on_` or `_do_` prefix (e.g., `_do_merge`, `_do_insert`, `_on_mouse_down`)

**Variables:**
- Instance attributes: `snake_case` (e.g., `current_page`, `selected_pages`, `thumb_cache`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `APP_VERSION`, `THEMES`, `LANG`, `MAX_UNDO`)

## Where to Add New Code

**New Feature (e.g., Export to Image):**
- Primary logic: Add method to appropriate mixin (e.g., `ViewerMixin` for image export)
- Tests: `tests/test_viewer.py` for viewer features
- UI: Add button/menu item in `UIBuilderMixin._build_ui()`
- Dialogs: If complex settings needed, create new dialog in `pagefolio/dialogs/<feature>.py`

**New Page Operation (e.g., Watermark):**
- Logic: Add method to `PageOpsMixin` in `pagefolio/page_ops.py`
- Tests: Add test class to `tests/test_pdf_ops.py`
- UI: Add button in `UIBuilderMixin._build_tools_page_ops()` section
- Plugin event: Fire event in operation method, add hook to `PDFEditorPlugin` if needed

**New Dialog:**
- Single dialog: Create in `pagefolio/dialogs/<feature>.py`
- Multiple dialogs for feature: Group in `pagefolio/dialogs/<feature>.py` with multiple classes
- Re-export: Add import to `pagefolio/dialogs/__init__.py`
- Call: Import and instantiate from relevant mixin (e.g., merge dialogs from `PageOpsMixin._do_merge()`)

**New OCR Provider:**
- Implementation: Subclass `OCRProvider` in `pagefolio/ocr_providers.py`
- Registration: Plugin calls `app.plugin_manager.register_ocr_provider(name, provider_class)` on load
- UI config: Add settings fields to `LLMConfigDialog` in `pagefolio/dialogs/llm_config.py` if needed
- Tests: Add provider unit test to `tests/test_ocr_providers.py`

**New Plugin:**
- Location: Create `plugins/<plugin_name>.py`
- Base: Subclass `PDFEditorPlugin` from `pagefolio.plugins`
- Hooks: Implement desired hook methods (on_file_open, on_page_rotate, build_ui, etc.)
- Discovery: Automatically found by `PluginManager.load_all()` at startup
- Tests: Create `tests/test_plugin_<name>.py` if needed

**Utility Functions:**
- Settings utils: Add to `pagefolio/settings.py` (font, theme, JSON)
- OCR helpers: Add to `pagefolio/ocr.py` (parallel execution, retry logic)
- Constants: Add to `pagefolio/constants.py` if app-wide; to local module if single-use

## Special Directories

**`pagefolio/dialogs/`:**
- Purpose: Modal dialog definitions grouped by feature
- Generated: No (hand-authored)
- Committed: Yes
- Note: Each dialog is Tk.Toplevel subclass; takes parent, font func, lang dict as params

**`plugins/`:**
- Purpose: User-installable plugins directory
- Generated: No (hand-authored, user can add)
- Committed: Yes (includes sample `page_info.py`)
- Discovery: PluginManager scans for `.py` files at startup; each must subclass `PDFEditorPlugin`

**`tests/`:**
- Purpose: pytest test suite
- Generated: No (hand-authored)
- Committed: Yes
- Run: `pytest` (or `pytest tests/` for specific dir)
- Coverage: `pytest --cov=pagefolio` shows coverage metrics

**`.planning/`:**
- Purpose: GSD planning artifacts (phases, quick tasks, research)
- Generated: Yes (by GSD commands)
- Committed: Selective (e.g., phase plans committed, runtime state in .gitignore)

**`build/`, `dist/`:**
- Purpose: PyInstaller compilation output
- Generated: Yes (by PyInstaller)
- Committed: No (.gitignore excludes)

---

*Structure analysis: 2026-06-10*
