# Codebase Structure

**Analysis Date:** 2026-07-03

## Directory Layout

```
PageFolio/
├── pagefolio.py                    # Entry point: python pagefolio.py
├── pagefolio/                      # Main package
│   ├── __init__.py                 # Public API re-exports (backward compat)
│   ├── __main__.py                 # python -m pagefolio entry point
│   ├── app.py                      # PDFEditorApp root class + Mixin integration
│   ├── constants.py                # APP_VERSION, SUPPORTED_EXTENSIONS, etc. + theme/lang re-exports
│   ├── themes.py                   # THEMES dict (dark/light) + runtime C dict
│   ├── lang.py                     # LANG dict (ja/en) multilingual strings
│   ├── settings.py                 # Config I/O, theme application, font helpers
│   ├── plugins.py                  # PDFEditorPlugin base class + PluginManager
│   ├── ui_builder.py               # UIBuilderMixin — styles, layout, widgets
│   ├── file_ops.py                 # FileOpsMixin — open/save/undo/redo/password
│   ├── page_ops.py                 # PageOpsMixin — rotate/delete/crop/insert/merge/split
│   ├── redact_ops.py               # RedactOpsMixin — blackout & mosaic
│   ├── viewer.py                   # ViewerMixin — preview, thumbnails, zoom, selection
│   ├── dnd.py                      # DnDMixin — drag-and-drop page reordering
│   ├── ocr.py                      # OCRMixin — OCR orchestration; provider selection
│   ├── ocr_providers.py            # OCRProvider ABC + Claude/Gemini/LMStudio/Tesseract
│   ├── ocr_dialog.py               # OCRDialog — multi-page OCR UI; results viewer/exporter
│   ├── md_render.py                # parse_markdown() — Markdown→(line type, span) conversion
│   ├── print_ops.py                # PrintOpsMixin — print via OS handler
│   ├── undo_store.py               # UndoBlobStore, MemBlob, FileBlob — Blob lifecycle
│   ├── pagination.py               # Pure functions for window/index calculations
│   ├── file_drop.py                # tkinterdnd2 integration
│   ├── dialogs/                    # Dialog package
│   │   ├── __init__.py             # Re-exports for backward compat (from pagefolio.dialogs import ...)
│   │   ├── about.py                # AboutDialog
│   │   ├── settings.py             # SettingsDialog
│   │   ├── plugin.py               # PluginDialog
│   │   ├── merge.py                # MergeOrderDialog, MergeResizeDialog
│   │   ├── llm_config.py           # LLMConfigDialog — OCR provider/model setup
│   │   ├── export_images.py        # ExportImagesDialog — page→image export
│   │   └── password.py             # SetPasswordDialog — password entry UI
│   └── pagefolio.ico               # App icon (referenced by PyInstaller)
├── plugins/                        # Plugin directory (user/sample plugins)
│   └── page_info.py                # Sample plugin (page info display)
├── tests/                          # Test suite (pytest)
│   ├── conftest.py                 # Test fixtures (fake PDF, mock settings)
│   ├── test_imports.py             # Package import & backward compat tests
│   ├── test_utils.py               # Utility function tests
│   ├── test_pdf_ops.py             # PDF operation tests (rotate, crop, etc.)
│   ├── test_plugins.py             # PluginManager tests
│   ├── test_viewer.py              # Preview/thumbnail rendering tests
│   ├── test_settings_keyguard.py   # API key non-persistence guard tests
│   ├── test_ocr.py                 # OCR helper/parallel execution tests
│   ├── test_ocr_providers.py       # OCRProvider unit tests
│   ├── test_provider_ui.py         # Provider UI & resolve_ocr_prompt tests
│   ├── test_pagination.py          # Window calculation & index conversion tests
│   ├── test_md_render.py           # parse_markdown() pure function tests
│   ├── test_export_images.py       # Page→image export range/scale tests
│   ├── test_save_overwrite.py      # Shrink-and-save helper tests
│   ├── test_password.py            # PDF password add/remove & encrypt/decrypt tests
│   ├── test_print.py               # Print temp file generation tests
│   ├── test_undo_stress.py         # 120-page undo/redo stress (memory, eviction)
│   ├── test_lang_parity.py         # ja/en LANG key parity regression
│   └── test_source_keyguard.py     # API key pattern not-found scan in source
├── README.md                       # User-facing usage guide
├── CLAUDE.md                       # AI development instructions (this project)
├── 開発履歴.md                      # Change history (Japanese)
├── LICENSE                         # MIT License
├── pyproject.toml                  # pytest & Ruff config (pythonpath, line-length, rules)
├── requirements.txt                # Fixed dependency versions
├── PageFolio.spec                  # PyInstaller spec (onedir format)
├── pagefolio.ico                   # Icon file
├── .planning/                      # GSD documentation (created by orchestrator)
│   ├── codebase/                   # Codebase maps (ARCHITECTURE.md, STRUCTURE.md, etc.)
│   ├── phases/                     # Phase execution plans
│   └── ...
├── build/                          # PyInstaller build directory (generated; not committed)
└── dist/                           # PyInstaller dist directory (generated; committed for release)

(Runtime, created on first run)
└── pagefolio_settings.json         # User config (theme, font size, window geometry, etc.)
```

## Directory Purposes

**`pagefolio/` (Main Package):**
- Purpose: Application source code (Mixins, UI, file ops, OCR, dialogs)
- Contains: 30+ modules (1 Mixin per file + supporting utilities)
- Key files: `app.py` (root), `ui_builder.py` (layout), `file_ops.py` (I/O), `ocr.py` (external APIs)

**`pagefolio/dialogs/` (Dialog Package):**
- Purpose: Modal dialogs for user input (settings, password, export, etc.)
- Contains: 8 dialog classes (About, Settings, Plugin, Merge, LLMConfig, ExportImages, Password, OCR)
- Pattern: Each dialog inherits from `tk.Toplevel`; takes `parent` (Tk), font helper, lang dict as args

**`plugins/` (Plugin Directory):**
- Purpose: User-extensible plugins loaded at startup
- Contains: Python files implementing `PDFEditorPlugin` subclass
- Plugin discovery: Scanned via `PluginManager.load_all()` on app init

**`tests/` (Test Suite):**
- Purpose: pytest-based unit & integration tests
- Contains: 24 test modules covering imports, PDF ops, rendering, OCR, pagination, undo, etc.
- Run: `pytest` (or `pytest tests/test_specific.py` for single module)
- Coverage: Can run `pytest --cov=pagefolio` for coverage report

**`build/` (PyInstaller Build Artifacts):**
- Purpose: Temporary build directory (not committed)
- Lifecycle: Generated by PyInstaller; cleared before rebuild

**`dist/` (Distribution):**
- Purpose: Final executable output & release assets
- Contains: `PageFolio/` (onedir folder) + `PageFolio-<tag>-win64.zip` + `.sha256` files
- Pattern: Committed to git for immutable releases (CLAUDE.md release rules)

**`.planning/` (GSD Orchestrator Output):**
- Purpose: Planning and codebase documentation (generated by `/gsd-map-codebase`, `/gsd-plan-phase`)
- Contains: Markdown docs (ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, etc.)

## Key File Locations

**Entry Points:**
- `pagefolio.py`: Command-line entry point (delegates to `__main__.main()`)
- `pagefolio/__main__.py`: Package entry point; sets up Tk root and PDFEditorApp
- `pagefolio/app.py:47-174`: PDFEditorApp initialization (settings load, UI build, plugin load)

**Configuration:**
- `pagefolio/constants.py`: APP_VERSION, SUPPORTED_EXTENSIONS, defaults
- `pagefolio/themes.py`: THEMES dict (dark/light color schemes)
- `pagefolio/lang.py`: LANG dict (ja/en multilingual strings)
- `pagefolio/settings.py`: Config file I/O, theme application, font helpers
- `pyproject.toml`: Ruff & pytest configuration
- `requirements.txt`: Pinned dependency versions
- `pagefolio_settings.json`: Runtime user config (created on first run)

**Core Logic:**
- `pagefolio/app.py`: PDFEditorApp class + Mixin integration + state management
- `pagefolio/file_ops.py`: File open/save/undo/redo; password encryption/decryption
- `pagefolio/page_ops.py`: Page operations (rotate, delete, crop, insert, merge, split, export)
- `pagefolio/viewer.py`: Preview rendering, thumbnail generation & caching, zoom, selection
- `pagefolio/ui_builder.py`: Tkinter style definitions and layout construction

**Advanced Features:**
- `pagefolio/ocr.py`: OCR orchestration; provider selection; prompt resolution
- `pagefolio/ocr_providers.py`: OCR backend implementations (Claude, Gemini, LMStudio, Tesseract)
- `pagefolio/ocr_dialog.py`: OCRDialog UI; multi-page results viewer; summary generation
- `pagefolio/redact_ops.py`: Blackout & mosaic page editing
- `pagefolio/dnd.py`: Drag-and-drop thumbnail reordering
- `pagefolio/print_ops.py`: Print to OS default PDF handler

**Utilities:**
- `pagefolio/pagination.py`: Pure functions for window/index calculations (no Tk/fitz)
- `pagefolio/undo_store.py`: Blob abstraction (MemBlob/FileBlob); tempfile lifecycle
- `pagefolio/md_render.py`: Markdown→(line type, span) conversion (pure function)
- `pagefolio/plugins.py`: PluginManager; plugin lifecycle hooks
- `pagefolio/file_drop.py`: tkinterdnd2 integration for file drag-and-drop
- `pagefolio/dialogs/*.py`: Modal dialogs (About, Settings, Plugin, Merge, LLMConfig, Export, Password)

**Testing:**
- `tests/conftest.py`: Pytest fixtures (fake PDF, mock settings)
- `tests/test_*.py`: 24 test modules covering all major components
- Command: `pytest` to run all; `pytest tests/test_specific.py` for single module

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `file_ops.py`, `ui_builder.py`, `undo_store.py`)
- Test files: `test_<feature>.py` (e.g., `test_pdf_ops.py`, `test_ocr.py`)

**Directories:**
- Packages: `snake_case/` (e.g., `dialogs/`, `plugins/`)

**Classes:**
- Application: `PascalCase` (e.g., `PDFEditorApp`, `UIBuilderMixin`, `AboutDialog`)
- Mixin classes: End with `Mixin` suffix (e.g., `FileOpsMixin`, `ViewerMixin`)
- Dialog classes: End with `Dialog` suffix (e.g., `SettingsDialog`, `OCRDialog`)
- Plugin base: `PDFEditorPlugin`
- Blob classes: `MemBlob`, `FileBlob`
- OCR providers: `<Name>Provider` (e.g., `ClaudeProvider`, `GeminiProvider`)

**Functions/Methods:**
- Internal/private: `_snake_case()` with `_` prefix (e.g., `_build_ui()`, `_refresh_all()`, `_save_settings()`)
- Event handlers: `_on_<event>()` (e.g., `_on_dnd_drop()`, `_on_file_open()`)
- Action methods: `_do_<action>()` (e.g., `_do_merge()`, `_do_insert()`)
- Public API: Plain names (e.g., `load_all()`, `fire_event()`)
- Pure functions: snake_case (e.g., `parse_page_ranges()`, `clamp_window_start()`)

**Variables:**
- Instance state: `snake_case` (e.g., `self.doc`, `self.current_page`, `self.selected_pages`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_UNDO`, `OFFLOAD_THRESHOLD`, `PAGE_SIZE_DEFAULT`)
- Theme colors: Accessed via `C["KEY"]` dict (e.g., `C["BG_DARK"]`, `C["ACCENT"]`)
- Language strings: Accessed via `LANG["lang"]["key"]` (e.g., `LANG["ja"]["button_open"]`)

## Where to Add New Code

**New Feature (PDF operation):**
- Primary code: Create method in appropriate Mixin (or new Mixin if cross-cutting)
  - Rotation/deletion/cropping → `pagefolio/page_ops.py` (PageOpsMixin)
  - Rendering/zoom/thumbnails → `pagefolio/viewer.py` (ViewerMixin)
  - File I/O → `pagefolio/file_ops.py` (FileOpsMixin)
- Tests: `tests/test_<feature>.py` following existing test patterns
- UI: Add button/menu item in `pagefolio/ui_builder.py` (`_build_ui()` or `_build_tools_*()` methods)
- Plugin hook: Add new `on_<event>()` method to `PDFEditorPlugin` base class if other code needs to respond

**New Dialog:**
- Implementation: Create class in `pagefolio/dialogs/<name>.py` inheriting `tk.Toplevel`
- Pattern: Accept `parent`, `font` function, `lang` dict as constructor args; set `grab_set()` for modal behavior
- Re-export: Add to `pagefolio/dialogs/__init__.py` for backward-compatible import
- Integration: Import in `app.py` or calling Mixin; instantiate on user action (button click, menu item)

**New OCR Provider:**
- Implementation: Create class in `pagefolio/ocr_providers.py` inheriting `OCRProvider` ABC
- Methods: Implement `ocr_image_ex()` for image input; optionally `complete_text_ex()` for text-only summary
- Registration: Call `register_ocr_provider()` hook in plugin's `on_load()` or during app init
- UI: Add option to `LLMConfigDialog` dropdown (requires modification to dialog)

**New Utility Function:**
- If Tk/fitz-independent: Add to `pagefolio/<utility>.py` or create new module (e.g., `markdown_render.py`, `pagination.py`)
- If tied to operation: Add as static function in Mixin module or in supporting utility (e.g., `parse_page_ranges()` in `page_ops.py`)
- Tests: Add corresponding `tests/test_<utility>.py` with pure function test cases

**New Plugin:**
- Location: Create `.py` file in `plugins/` directory (auto-discovered on startup)
- Pattern: Inherit from `PDFEditorPlugin`; implement desired hook methods (minimal: `on_load()`)
- Example: See `plugins/page_info.py` (displays page count in status bar)

## Special Directories

**`pagefolio/dialogs/` (Dialog Package):**
- Purpose: Centralized modal UI for user input
- Generated: No (hand-written)
- Committed: Yes
- Pattern: Each dialog is a separate file; `__init__.py` re-exports for backward-compatible imports

**`plugins/` (Plugin Directory):**
- Purpose: User-extensible code loaded at runtime
- Generated: No (manual)
- Committed: Yes (contains sample plugins)
- Discovery: `PluginManager.load_all()` scans directory for `.py` files; imports dynamically

**`tests/` (Test Suite):**
- Purpose: Regression prevention; quality gate
- Generated: No (hand-written)
- Committed: Yes
- Run: `pytest` (config in `pyproject.toml`)
- Coverage: Track via `pytest --cov=pagefolio`

**`build/` (PyInstaller Artifacts):**
- Purpose: Temporary build output
- Generated: Yes (by `pyinstaller PageFolio.spec`)
- Committed: No (in `.gitignore`)
- Lifecycle: Cleared before rebuild

**`dist/` (Distribution Artifacts):**
- Purpose: Final executable & release assets
- Generated: Yes (by PyInstaller + zip + sha256 scripts)
- Committed: Yes (for immutable releases per CLAUDE.md)
- Contents: `PageFolio/` (onedir), `PageFolio-<tag>-win64.zip`, `.sha256` checksums

**`.planning/` (GSD Orchestrator Output):**
- Purpose: Planning docs (generated by commands like `/gsd-map-codebase`, `/gsd-plan-phase`)
- Generated: Yes (by orchestrator)
- Committed: Yes (tracks planning decisions)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, phase plans, etc.

---

*Structure analysis: 2026-07-03*
