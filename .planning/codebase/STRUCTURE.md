# Codebase Structure

**Analysis Date:** 2026-07-22

## Directory Layout

```
PageFolio/
├── pagefolio/                    # Main package (Python module)
│   ├── __init__.py               # Package marker
│   ├── __main__.py               # CLI entry point (python -m pagefolio)
│   ├── app.py                    # PDFEditorApp main class (Mixin composition)
│   │
│   ├── [Core Configuration]
│   ├── constants.py              # Version, file names, extensions, unit conversions
│   ├── themes.py                 # Color theme definitions (THEMES dict, C singleton)
│   ├── lang.py                   # Language strings (LANG dict: ja, en)
│   ├── settings.py               # Settings I/O, font helpers, theme application
│   │
│   ├── [Feature Mixins] (8 mixins, each in separate file)
│   ├── ui_builder.py             # UIBuilderMixin — Tkinter styles & layout
│   ├── file_ops.py               # FileOpsMixin — open/save/undo/redo/password
│   ├── page_ops.py               # PageOpsMixin — rotate/delete/crop/insert/merge
│   ├── redact_ops.py             # RedactOpsMixin — black strikethrough & mosaic
│   ├── viewer.py                 # ViewerMixin — preview/zoom/thumbnails/selection
│   ├── dnd.py                    # DnDMixin — drag-and-drop reordering
│   ├── ocr.py                    # OCRMixin — OCR dispatch & provider mgmt
│   ├── print_ops.py              # PrintOpsMixin — print to default PDF handler
│   │
│   ├── [Pure Logic Layers] (Tk/fitz independent)
│   ├── ocr_pipeline.py           # PipelineState, consume_one, try_enqueue (thread-safe)
│   ├── pagination.py             # Window calculation, index transforms (pure functions)
│   ├── undo_store.py             # Blob storage (FileBlob, MemBlob, UndoBlobStore)
│   ├── md_render.py              # Markdown parsing (pure functions)
│   │
│   ├── [OCR & Text Processing]
│   ├── ocr_engine.py             # OCR orchestration (deprecated: see ocr_pipeline)
│   ├── ocr_dialog.py             # Multi-page OCR execution UI (OCRDialog class)
│   ├── ocr_fallback.py           # Fallback OCR routing logic
│   ├── batch_ocr_state.py        # Batch OCR state tracking
│   ├── ocr_providers/            # OCR provider package
│   │   ├── __init__.py           # Package marker
│   │   ├── base.py               # OCRProvider ABC, URL validation
│   │   ├── errors.py             # Custom exception types (OCRAPIKeyError, etc.)
│   │   ├── registry.py           # Provider discovery (env vars only, Tk/settings independent)
│   │   ├── claude.py             # Claude API provider
│   │   ├── gemini.py             # Gemini API provider
│   │   ├── lmstudio.py           # LM Studio local provider
│   │   ├── tesseract.py          # Tesseract CLI provider
│   │   ├── ollama.py             # Ollama local provider
│   │   └── runpod.py             # RunPod serverless provider
│   │
│   ├── [UI Components]
│   ├── dialogs/                  # Dialogs package (modal windows)
│   │   ├── __init__.py           # Re-exports for backward compat
│   │   ├── about.py              # AboutDialog
│   │   ├── settings.py           # SettingsDialog (theme, font, shortcuts, OCR config)
│   │   ├── plugin.py             # PluginDialog (enable/disable plugins)
│   │   ├── password.py           # SetPasswordDialog (PDF password encryption)
│   │   ├── merge.py              # MergeOrderDialog, MergeResizeDialog
│   │   ├── shortcuts.py          # ShortcutsDialog (keybinding editor)
│   │   ├── export_images.py      # ExportImagesDialog (batch export to PNG/JPG)
│   │   ├── batch_ocr.py          # BatchOCRDialog (multi-page OCR)
│   │   ├── ocr_dialog.py         # OCRDialog (single dialog, for compat)
│   │   └── llm_config/           # LLM provider config sub-package
│   │       ├── __init__.py       # LLMConfigDialog composite (Mixin-based)
│   │       ├── dialog.py         # Base dialog structure & prompt file notice
│   │       ├── sections.py       # UI sections (provider, model, temp, etc.)
│   │       └── model_fetch.py    # Async model list fetching (background thread)
│   │
│   ├── [Utilities & Helpers]
│   ├── plugins.py                # Plugin system (PDFEditorPlugin ABC, PluginManager)
│   ├── thumb_cache.py            # LRU thumbnail cache (LruCache class)
│   ├── toast.py                  # Toast notifications (ToastManager)
│   ├── file_drop.py              # Drag-and-drop file handler setup
│   └── [Deprecated/Legacy]
│       └── ocr_engine.py         # Legacy OCR runner (see ocr_pipeline)
│
├── pagefolio.py                  # CLI launcher script (redirects to __main__.py)
├── tests/                        # Test suite (pytest)
│   ├── conftest.py               # Pytest fixtures & shared setup
│   ├── test_imports.py           # Import guards (no hardcodes)
│   ├── test_ocr*.py              # OCR pipeline, providers, engine, fallback
│   ├── test_batch_ocr*.py        # Batch OCR dialog & state
│   ├── test_pdf_ops.py           # Page operations (rotate, crop, delete, merge)
│   ├── test_undo_stress.py       # Undo/redo stress tests
│   ├── test_pagination.py        # Window calculation, page indexing
│   ├── test_provider_ui.py       # LLM config dialog UI
│   ├── test_settings*.py         # Settings, themes, keybindings
│   ├── test_plugins.py           # Plugin system lifecycle
│   ├── test_password.py          # PDF password encryption
│   ├── test_shortcuts_dialog.py  # Keybinding editor
│   ├── test_export_images.py     # Batch export
│   ├── test_print.py             # Print functionality
│   ├── test_viewer.py            # Preview & thumbnails
│   ├── test_md_render.py         # Markdown parsing
│   ├── test_toast.py             # Toast notifications
│   ├── test_thumb_cache.py       # LRU cache
│   ├── test_v150_regression.py   # v1.5.0 specific regression tests
│   ├── test_font_hardcode_guard.py    # Font size hardcode checks
│   ├── test_lang_parity.py       # ja/en language key parity
│   ├── test_source_keyguard.py   # Source code audit (API keys, etc.)
│   ├── test_selection_invariant.py    # Selection logic invariants
│   └── test_utils.py             # Utility function tests
│
├── plugins/                      # User/built-in plugins
│   └── page_info.py              # Example plugin: page info display
│
├── .planning/                    # Planning & analysis documents
│   ├── codebase/                 # Codebase maps (generated by /gsd-map-codebase)
│   │   ├── ARCHITECTURE.md       # This file
│   │   └── STRUCTURE.md          # This file
│   ├── milestones/               # Milestone phase plans (v1.4.0, v1.6.0, etc.)
│   ├── debug/                    # Debug session notes
│   ├── quick/                    # Quick task logs
│   └── research/                 # Research documents
│
├── pyproject.toml                # Python project metadata (minimal, see poetry)
├── requirements.txt              # Runtime dependencies
├── PageFolio.spec                # PyInstaller spec (for .exe builds)
├── CLAUDE.md                     # AI development instructions (this project's guide)
├── README.md                     # User-facing documentation
├── 開発履歴.md                    # Development changelog (Japanese)
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                       # MIT License
└── pagefolio.ico                 # Application icon
```

## Directory Purposes

**`pagefolio/`**
- Purpose: Main Python package containing all application code
- Contains: Mixins, OCR providers, dialogs, utilities, pure logic layers
- Key files: `app.py` (entry point for composition), Mixin files, OCR provider package

**`pagefolio/ocr_providers/`**
- Purpose: Pluggable OCR backend implementations
- Contains: ABC, implementations (Claude, Gemini, Tesseract, Ollama, LM Studio, RunPod), error types
- Key files: `base.py` (OCRProvider ABC), `registry.py` (provider discovery via env vars)

**`pagefolio/dialogs/`**
- Purpose: Modal dialog implementations
- Contains: Individual dialog classes, LLM config sub-package
- Key files: `settings.py` (main settings dialog), `llm_config/` (provider setup), `batch_ocr.py` (OCR UI)

**`pagefolio/dialogs/llm_config/`**
- Purpose: Separate LLM provider configuration dialogs
- Contains: LLMConfigDialog, model fetching, UI sections
- Key files: `dialog.py` (main), `sections.py` (UI building), `model_fetch.py` (async fetch)

**`tests/`**
- Purpose: Unit & integration test suite
- Contains: pytest test modules covering all major features
- Key files: `conftest.py` (fixtures), `test_*.py` (feature tests)

**`plugins/`**
- Purpose: User-defined or bundled plugin directory
- Contains: Python modules implementing PDFEditorPlugin interface
- Key files: `page_info.py` (example plugin)

**`.planning/codebase/`**
- Purpose: Codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated by: `/gsd-map-codebase` GSD command
- Used by: `/gsd-plan-phase`, `/gsd-execute-phase` for context

## Key File Locations

**Entry Points:**
- `pagefolio.py`: Simple launcher script (redirects to `pagefolio/__main__.py`)
- `pagefolio/__main__.py`: Main entry point (`python -m pagefolio`); creates Tk root and PDFEditorApp

**Configuration:**
- `pagefolio/constants.py`: Version string (APP_VERSION), file names, supported extensions
- `pagefolio/settings.py`: Settings file I/O, theme application, font helpers
- `pagefolio/themes.py`: Color theme definitions (dark/light), theme dict singleton `C`
- `pagefolio/lang.py`: Language strings (ja/en), localization dict `LANG`

**Core Logic:**
- `pagefolio/app.py`: PDFEditorApp class — Mixin composition root, state mgmt, event dispatch
- Mixin files (8 total):
  - `pagefolio/ui_builder.py`: UI styling & layout
  - `pagefolio/file_ops.py`: File open/save, undo/redo
  - `pagefolio/page_ops.py`: Page operations (rotate, crop, delete, merge)
  - `pagefolio/redact_ops.py`: Redaction (black/mosaic)
  - `pagefolio/viewer.py`: Preview & thumbnails
  - `pagefolio/dnd.py`: Drag-and-drop reordering
  - `pagefolio/ocr.py`: OCR dispatch
  - `pagefolio/print_ops.py`: Print to default handler

**Pure Logic Layers:**
- `pagefolio/ocr_pipeline.py`: Thread-safe producer-consumer state (PipelineState, consume_one)
- `pagefolio/pagination.py`: Thumbnail window calculation (pure functions, Tk/fitz independent)
- `pagefolio/undo_store.py`: Blob storage for large page data (FileBlob, MemBlob)
- `pagefolio/md_render.py`: Markdown parsing (pure functions)

**OCR System:**
- `pagefolio/ocr.py`: OCRMixin, provider dispatch, prompt resolution
- `pagefolio/ocr_providers/base.py`: OCRProvider ABC and error types
- `pagefolio/ocr_providers/{claude,gemini,tesseract,lmstudio,ollama,runpod}.py`: Implementations
- `pagefolio/ocr_providers/registry.py`: Provider discovery (env vars, Python stdlib only)
- `pagefolio/ocr_dialog.py`: Multi-page OCR UI
- `pagefolio/batch_ocr_state.py`: Batch OCR state management

**Dialogs:**
- `pagefolio/dialogs/settings.py`: SettingsDialog (theme, font, shortcuts, OCR provider)
- `pagefolio/dialogs/llm_config/dialog.py`: LLMConfigDialog (API key, model, temperature)
- `pagefolio/dialogs/batch_ocr.py`: BatchOCRDialog (batch OCR execution)
- `pagefolio/dialogs/merge.py`: MergeOrderDialog, MergeResizeDialog
- `pagefolio/dialogs/password.py`: SetPasswordDialog
- `pagefolio/dialogs/shortcuts.py`: ShortcutsDialog (keybinding editor)
- `pagefolio/dialogs/plugin.py`: PluginDialog (enable/disable plugins)
- `pagefolio/dialogs/export_images.py`: ExportImagesDialog

**Plugins & Utilities:**
- `pagefolio/plugins.py`: PluginManager, PDFEditorPlugin ABC
- `pagefolio/thumb_cache.py`: LRU thumbnail cache
- `pagefolio/toast.py`: Toast notification system
- `pagefolio/file_drop.py`: Drag-and-drop file handler

**Testing:**
- `tests/conftest.py`: Pytest fixtures (fake app, fake doc, fake provider)
- `tests/test_ocr_providers.py`: OCR provider implementations
- `tests/test_ocr_pipeline.py`: Pipeline state machine
- `tests/test_pagination.py`: Window calculation
- `tests/test_pdf_ops.py`: Page operations
- `tests/test_undo_stress.py`: Undo/redo stability

## Naming Conventions

**Files:**
- Mixin files: lowercase_with_underscores + `_mixin` inferred from class name (e.g., `file_ops.py` → FileOpsMixin)
- Dialog files: lowercase_with_underscores, file name hints dialog name (e.g., `settings.py` → SettingsDialog)
- Provider files: lowercase provider name (e.g., `claude.py`, `tesseract.py`)
- Test files: `test_` prefix + module under test (e.g., `test_pagination.py` tests `pagination.py`)

**Directories:**
- Packages: lowercase, descriptive (e.g., `ocr_providers`, `dialogs`)
- Sub-packages: nested lowercase (e.g., `dialogs/llm_config`)

**Modules (Python files):**
- Single word or snake_case: `settings.py`, `file_ops.py`, `page_ops.py`
- Avoid hyphens; use underscores for readability

**Classes:**
- PascalCase: `PDFEditorApp`, `UIBuilderMixin`, `OCRDialog`, `FileOpsMixin`
- Suffixes: `Mixin` for Mixins (e.g., `FileOpsMixin`), `Dialog` for dialogs (e.g., `SettingsDialog`)

**Functions:**
- snake_case: `_open_file()`, `_save_undo()`, `parse_page_ranges()`
- Private (internal): `_` prefix (e.g., `_check_doc()`, `_update_doc_buttons_state()`)
- Pure functions: no underscore prefix (e.g., `parse_page_ranges()` in `page_ops.py`)

**Variables:**
- snake_case: `current_page`, `selected_pages`, `crop_rect`, `undo_stack`
- Constants: UPPER_CASE (e.g., `APP_VERSION`, `MAX_UNDO`, `SUPPORTED_EXTENSIONS`)
- Private instance attributes: `self._` prefix (e.g., `self._undo_blob_store`, `self._page_window_start`)

## Where to Add New Code

**New PDF Page Operation (rotate/crop/delete/etc.):**
1. **Implementation:** Add method to `PageOpsMixin` in `pagefolio/page_ops.py`
   - Example: `def _new_operation(self, page_indices): ...`
2. **Undo support:** Add `"new_op"` case to `_save_undo()` in `FileOpsMixin`
3. **Undo restoration:** Add `"new_op"` case to `_undo()` and `_redo()` in `FileOpsMixin`
4. **UI button:** Add button to right panel in `_build_ui()` in `UIBuilderMixin` or in dialog
5. **Tests:** Create `tests/test_new_operation.py` covering operation + undo/redo

**New OCR Provider:**
1. **Implementation:** Create `pagefolio/ocr_providers/newprovider.py`
   - Subclass `OCRProvider` from `base.py`
   - Implement `ocr_image(b64_png, prompt, **kwargs)` and `list_models()`
   - Define error handling and model list timeout
2. **Registration:** Add provider name to `_BUILTIN_PROVIDER_NAMES` in `pagefolio/plugins.py`
3. **Configuration UI:** Add sections to `pagefolio/dialogs/llm_config/sections.py` if new API keys needed
4. **Tests:** Create `tests/test_ocr_providers.py` entry with mocked HTTP calls
5. **Documentation:** Update `CLAUDE.md` and `README.md` with setup instructions

**New Dialog:**
1. **Implementation:** Create `pagefolio/dialogs/newdialog.py`
   - Subclass `tk.Toplevel`
   - Follow `SettingsDialog` structure: `__init__`, `ok_clicked()`, layout methods
2. **Re-export:** Add to `pagefolio/dialogs/__init__.py`
3. **Launch:** Add method to app (or menu item) that calls `NewDialog(self.root, app=self, ...)`
4. **Tests:** Create `tests/test_newdialog.py` with UI interaction tests

**New Plugin Hook:**
1. **Hook definition:** Add method to `PDFEditorPlugin` base class in `pagefolio/plugins.py`
   - Example: `def on_page_rename(self, app, page_index, new_name): pass`
2. **Dispatch:** Call hook in appropriate Mixin method
   - Example: In `PageOpsMixin._rename_page()` → `plugin_manager.fire_hook("on_page_rename", app=self, ...)`
3. **Plugin implementations:** Plugins override hook in subclass
4. **Tests:** Add hook test to `tests/test_plugins.py`

**Pure Logic Layer (Tk/fitz independent):**
1. **Location:** New file in `pagefolio/` (e.g., `new_logic.py`)
   - Import only Python stdlib or minimal external (not Tk, fitz, or UI modules)
2. **Structure:** Pure functions or lightweight classes
   - Example: `def compute_something(input): return output` (no side effects)
3. **Usage:** Called from Mixin methods or dialogs (Tk-dependent layer)
4. **Tests:** `tests/test_new_logic.py` — mock-free, fast unit tests

**Utility/Helper:**
1. **Location:** `pagefolio/` (new file) or add to existing `pagefolio/utils.py` if it exists
2. **Scope:** Shared functions/classes used by multiple modules
3. **Example:** New image processing helper → `pagefolio/image_utils.py`
4. **Tests:** `tests/test_image_utils.py`

## Special Directories

**`.planning/codebase/`**
- Purpose: Generated codebase analysis documents
- Generated by: `/gsd-map-codebase` (Codebase mapper agent)
- Contents: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Committed: Yes (frozen snapshots of codebase understanding)

**`.planning/milestones/`**
- Purpose: Phase plans for each milestone (v1.4.0, v1.6.0, v1.7.1, v1.8.0, etc.)
- Contents: Phase-level task breakdowns, success criteria, context docs
- Committed: Yes (project planning history)

**`.planning/quick/`**
- Purpose: Ad-hoc task logs (quick fixes, hotfixes, small features)
- Committed: Yes (context handoff between sessions)

**`venv/`**
- Purpose: Python virtual environment (local development)
- Committed: No (`.gitignore` excludes)

**`__pycache__/` and `.pytest_cache/`**
- Purpose: Python bytecode and pytest cache
- Committed: No (`.gitignore` excludes)

**`pagefolio_settings.json`**
- Purpose: User settings persisted at runtime (theme, font size, shortcuts, etc.)
- Location: Project root (or `$APPDATA/PageFolio/` when frozen)
- Committed: No (`.gitignore` excludes; user-specific)

**`.coverage`**
- Purpose: pytest coverage database (generated by `pytest --cov`)
- Committed: No (`.gitignore` excludes)

---

*Structure analysis: 2026-07-22*
