# Codebase Structure

**Analysis Date:** 2026-07-16

## Directory Layout

```
PageFolio/
├── pagefolio/                      # Main application package
│   ├── __init__.py                 # Package init
│   ├── __main__.py                 # Entry point: python -m pagefolio
│   ├── app.py                      # PDFEditorApp main class (8 Mixins)
│   ├── constants.py                # Version, file names, extensions, re-exports
│   ├── themes.py                   # Color theme definitions (THEMES, C dict)
│   ├── lang.py                     # Localization (LANG dict: ja, en)
│   ├── settings.py                 # Settings I/O, theme resolution, font helpers
│   ├── plugins.py                  # Plugin system: PDFEditorPlugin, PluginManager
│   │
│   ├── ui_builder.py               # UIBuilderMixin: UI construction, styling
│   ├── file_ops.py                 # FileOpsMixin: file I/O, undo/redo
│   ├── page_ops.py                 # PageOpsMixin: rotate, delete, crop, merge
│   ├── redact_ops.py               # RedactOpsMixin: blackout, mosaic
│   ├── viewer.py                   # ViewerMixin: preview, zoom, thumbnails
│   ├── dnd.py                      # DnDMixin: drag-and-drop reordering
│   ├── ocr.py                      # OCRMixin: OCR orchestration, provider selection
│   ├── print_ops.py                # PrintOpsMixin: printing via OS handler
│   │
│   ├── undo_store.py               # Blob storage: MemBlob, FileBlob, UndoBlobStore
│   ├── thumb_cache.py              # LRU thumbnail cache
│   ├── pagination.py               # Thumbnail window virtualization (pure logic)
│   ├── md_render.py                # Markdown result parsing (pure logic)
│   ├── toast.py                    # Toast notifications
│   ├── file_drop.py                # D&D file drop setup (tkinterdnd2 wrapper)
│   │
│   ├── ocr_pipeline.py             # OCR producer-consumer pure logic (Tk/fitz-free)
│   ├── ocr_dialog.py               # OCRDialog: OCR execution UI, result display
│   ├── ocr_engine.py               # OCRRunEngine: low-level provider orchestration
│   ├── ocr_fallback.py             # Fallback prompts for providers
│   │
│   ├── ocr_providers/              # OCR provider implementations
│   │   ├── __init__.py
│   │   ├── base.py                 # OCRProvider ABC
│   │   ├── registry.py             # Provider env var registry (std lib only)
│   │   ├── errors.py               # OCRAPIKeyError, OCRRetryableError, etc.
│   │   ├── claude.py               # ClaudeProvider
│   │   ├── gemini.py               # GeminiProvider
│   │   ├── tesseract.py            # TesseractProvider
│   │   ├── lmstudio.py             # LMStudioProvider
│   │   ├── ollama.py               # OllamaProvider
│   │   └── runpod.py               # RunPodProvider
│   │
│   ├── dialogs/                    # Secondary UI windows (Toplevel dialogs)
│   │   ├── __init__.py             # Re-exports
│   │   ├── about.py                # AboutDialog
│   │   ├── settings.py             # SettingsDialog (theme, font, plugins)
│   │   ├── plugin.py               # PluginDialog (plugin enable/disable)
│   │   ├── password.py             # SetPasswordDialog (PDF encryption)
│   │   ├── merge.py                # MergeOrderDialog, MergeResizeDialog
│   │   ├── export_images.py        # ExportImagesDialog
│   │   ├── shortcuts.py            # ShortcutsDialog (keybind editor)
│   │   ├── batch_ocr.py            # BatchOCRDialog (batch file OCR UI)
│   │   └── llm_config/             # LLM provider configuration dialog
│   │       ├── __init__.py         # LLMConfigDialog
│   │       ├── dialog.py           # DialogMixin
│   │       ├── sections.py         # SectionsMixin
│   │       └── model_fetch.py      # ModelFetchMixin (async model fetching)
│   │
│   ├── batch_ocr_state.py          # BatchState: batch OCR file list state
│   └── [utility modules]            # md_render.py, lang.py, etc.
│
├── tests/                           # Test suite
│   ├── conftest.py                 # pytest fixtures, mock app setup
│   ├── test_*.py                   # 34 test files (OCR, UI, PDF ops, etc.)
│   └── ...
│
├── plugins/                        # Third-party plugins directory
│   └── (user-installed plugins)
│
├── pagefolio.py                    # Root entry script (python pagefolio.py)
├── pagefolio_settings.json         # Persisted user settings (gitignored)
├── PageFolio.spec                  # PyInstaller spec (gitignored, rebuild per exe)
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project metadata
├── CLAUDE.md                       # AI development instructions (this file)
├── README.md                       # End-user documentation
├── 開発履歴.md                     # Development changelog (Japanese)
├── LICENSE                         # MIT License
└── .planning/                      # GSD workflow artifacts
    ├── codebase/                   # Architecture/structure analysis
    │   ├── ARCHITECTURE.md         # Architecture overview
    │   └── STRUCTURE.md            # (This file)
    └── milestones/                 # Phase plans for v1.x.x
```

## Directory Purposes

**`pagefolio/`**
- Purpose: Main application package
- Contains: All application code, organized by concern (UI, file ops, OCR, etc.)
- Key files: `app.py` (main class), `__main__.py` (entry), `constants.py` (version)

**`pagefolio/dialogs/`**
- Purpose: Secondary Tkinter Toplevel windows for user interaction
- Contains: Dialog classes for settings, merge, OCR, LLM config, batch operations
- Key files: `settings.py` (SettingsDialog), `llm_config/` (LLM config UI)

**`pagefolio/ocr_providers/`**
- Purpose: Pluggable OCR backends with unified interface
- Contains: ABC base class, 6 concrete providers, error definitions
- Key files: `base.py` (OCRProvider ABC), `registry.py` (env var mapping)

**`tests/`**
- Purpose: Automated test suite
- Contains: 34 test files covering OCR, UI, PDF ops, settings, etc.
- Key files: `conftest.py` (fixtures), test modules organized by feature

**`plugins/`**
- Purpose: Third-party plugin installation directory
- Contains: User-installed plugins (auto-discovered at startup)
- Key files: None (populated by users)

## Key File Locations

**Entry Points:**
- `pagefolio.py`: CLI script entry point (imports and calls `__main__.main()`)
- `pagefolio/__main__.py`: Application bootstrap, Tk window creation, app instantiation

**Configuration:**
- `pagefolio/constants.py`: Version (`APP_VERSION`), file names, supported extensions, re-exported `THEMES`, `C`, `LANG`
- `pagefolio/themes.py`: Color theme definitions (dark/light), runtime `C` dict
- `pagefolio/lang.py`: Localization strings (ja, en)
- `pagefolio/settings.py`: Settings I/O (JSON), theme resolution, font generation, external prompt file loading
- `pagefolio_settings.json`: Persisted user settings (ignored by git)

**Core Logic:**
- `pagefolio/app.py`: `PDFEditorApp` main class, 8 Mixins, initialization, shortcuts, menu bar
- `pagefolio/ui_builder.py`: Tkinter styles, layout construction, UI methods
- `pagefolio/file_ops.py`: Open/save, undo/redo, password handling
- `pagefolio/page_ops.py`: Page rotate, delete, crop, merge, insert, split
- `pagefolio/redact_ops.py`: Redaction (blackout/mosaic), rectangle selection

**Viewing & Rendering:**
- `pagefolio/viewer.py`: Preview canvas, zoom, thumbnail rendering
- `pagefolio/thumb_cache.py`: LRU thumbnail cache (MemoryBounded)
- `pagefolio/pagination.py`: Thumbnail window virtualization (pure logic, Tk-free)

**OCR System:**
- `pagefolio/ocr.py`: OCRMixin, provider selection, prompt resolution
- `pagefolio/ocr_dialog.py`: OCR UI dialog, result display/export
- `pagefolio/ocr_pipeline.py`: Producer-consumer pure logic (Tk/fitz-free)
- `pagefolio/ocr_engine.py`: Low-level provider orchestration
- `pagefolio/ocr_providers/base.py`: `OCRProvider` abstract base
- `pagefolio/ocr_providers/registry.py`: Env var mapping (std lib only)
- `pagefolio/ocr_providers/claude.py`, `gemini.py`, `tesseract.py`, `lmstudio.py`, `ollama.py`, `runpod.py`: Concrete providers

**Utilities:**
- `pagefolio/plugins.py`: Plugin system, lifecycle management
- `pagefolio/undo_store.py`: Blob storage (MemBlob, FileBlob, lifecycle)
- `pagefolio/md_render.py`: Markdown parsing for OCR results (pure logic, Tk-free)
- `pagefolio/toast.py`: Toast notification manager
- `pagefolio/file_drop.py`: D&D file drop setup (tkinterdnd2 wrapper)

**Testing:**
- `tests/conftest.py`: pytest fixtures, mock app factory
- `tests/test_*.py`: 34 test files by feature

## Naming Conventions

**Files:**
- Mixin modules: `*_ops.py` (e.g., `file_ops.py`, `page_ops.py`, `redact_ops.py`)
- Dialog modules: `dialogs/*.py` (e.g., `settings.py`, `merge.py`)
- OCR modules: `ocr*.py` or `ocr_providers/*.py`
- Test modules: `test_*.py` (pytest discovery)
- No hyphens in filenames (Python import compatibility)

**Functions:**
- Private/internal: `_name()` prefix (e.g., `_open_file()`, `_render_preview()`)
- Public: `name()` (rare for Mixins; usually called via `self`)
- Pure logic helpers: lowercase (e.g., `merge_shortcuts()`, `clamp_page_size()`)

**Variables:**
- Class attributes: `PascalCase` only for constants (e.g., `MAX_UNDO`)
- Instance attributes: `snake_case`, internal ones prefixed with `_` (e.g., `self.doc`, `self._undo_stack`)
- Persistent config: `self.settings` (dict with keys like `"theme"`, `"font_size"`)

**Types:**
- OCRProvider subclasses: `<Provider>Provider` (e.g., `ClaudeProvider`, `GeminiProvider`)
- Dialog classes: `<Feature>Dialog` (e.g., `SettingsDialog`, `BatchOCRDialog`)
- Mixin classes: `<Concern>Mixin` (e.g., `FileOpsMixin`, `PageOpsMixin`)

## Where to Add New Code

**New Feature (Page Operation):**
- Primary code: Add method to appropriate Mixin in `pagefolio/*_ops.py` or create new Mixin file
- Undo support: Create delta dict with operation type, affected pages, captured page blobs; call `self._push_evicting(delta)`
- UI trigger: Add button/menu item in `UIBuilderMixin._build_ui()` or dialog, bind to Mixin method
- Tests: Create `tests/test_<feature>.py` with fixture-based mocks

**New Dialog/Settings:**
- Dialog class: Create in `pagefolio/dialogs/<feature>.py` as `tk.Toplevel` subclass
- Re-export: Add import/export in `pagefolio/dialogs/__init__.py`
- Integration: Call from menu/button, pass `app` reference for state access
- Tests: Create `tests/test_<feature>_dialog.py` with window-handling fixtures

**New OCR Provider:**
- Provider class: Create in `pagefolio/ocr_providers/<provider_name>.py`, inherit `OCRProvider`
- Implement: `ocr_image_ex()`, optional `supports_text_prompt()` / `complete_text_ex()`
- Registry: Add env var entry in `pagefolio/ocr_providers/registry.py`
- UI: Add selection option in `LLMConfigDialog` (auto-discovered from registry)
- Tests: Create `tests/test_<provider>_provider.py` with mock API responses

**New Utility Function (Pure Logic):**
- Location: Create new module `pagefolio/<concern>.py` if fits pattern, or add to existing utility
- Pattern: No Tkinter / PyMuPDF imports (pure logic)
- Example: `pagination.py` handles window arithmetic; `md_render.py` parses markdown
- Tests: Create `tests/test_<concern>.py`, test with pure function calls

**Plugin Hook:**
- Define hook: Add signature to `pagefolio/plugins.py:PDFEditorPlugin` docstring + `PluginManager._dispatch()`
- Emit hook: Call `self.plugin_manager.dispatch(hook_name, **args)` from relevant Mixin
- Example: `on_page_delete` emitted after page deletion, plugins can react via callback

**Test File:**
- Naming: `tests/test_<feature_or_module>.py`
- Fixtures: Use `conftest.py` fixtures (`app_instance`, `mock_pdf`, etc.)
- Parametrization: Use `@pytest.mark.parametrize` for multiple scenarios
- Isolation: Each test should create own app instance or mock; no shared state between tests

## Special Directories

**`.planning/`**
- Purpose: GSD workflow artifacts
- Generated: Yes (by orchestrator)
- Committed: Yes (plans and decisions)
- Contains: Phase plans, codebase analysis, phase execution logs

**`plugins/`**
- Purpose: User-installed third-party plugins
- Generated: No (user-installed)
- Committed: No (.gitignore)
- Contains: Plugin .py files auto-discovered at startup

**`.ruff_cache/` / `__pycache__/`**
- Purpose: Build/linting cache
- Generated: Yes (by tools)
- Committed: No (.gitignore)
- Contains: Compiled Python bytecode, linter cache

**`dist/`**
- Purpose: PyInstaller build output
- Generated: Yes (by PyInstaller)
- Committed: Partially (*.zip tracked, *.spec rebuilt per version)
- Contains: Executable artifacts, redistributable packages

**`.pytest_cache/` / `.coverage`**
- Purpose: Test artifacts
- Generated: Yes (by pytest)
- Committed: No (.gitignore)
- Contains: Test discovery cache, coverage data

## Coding Patterns by Concern

### File Operations (UI initiator pattern)
```python
# In UIBuilderMixin event handler
def _open_file_dialog(self):
    path = filedialog.askopenfilename(...)
    if not path:
        return
    self._open_file(path)  # Delegates to FileOpsMixin

# In FileOpsMixin
def _open_file(self, path):
    try:
        self.doc = fitz.open(path)
        self.filepath = path
        self.current_page = 0
        self._refresh_all()
        self._set_status(f"Opened {path}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
```

### Page Operations with Undo
```python
# In PageOpsMixin
def _rotate_selected(self, degrees):
    if not self._check_doc():
        return
    targets = self._get_targets()
    
    # Capture undo delta BEFORE modification
    delta = {
        "op": "rotate",
        "pages": {p: self.doc[p].rotation for p in targets},
    }
    
    # Apply operation
    for page_i in targets:
        self.doc[page_i].set_rotation(degrees)
    
    # Push to stack (auto-evicts if full)
    self._push_evicting(delta)
    self._clear_redo_stack()
    self._refresh_all()
    self._set_status(f"Rotated {len(targets)} pages")
```

### Dialog with Results Back to App
```python
# In dialogs/settings.py
class SettingsDialog(tk.Toplevel):
    def __init__(self, root, app, ...):
        self.app = app  # Reference to main app
        # ... build UI ...
        self.bind("<Return>", self._on_ok)
    
    def _on_ok(self, event=None):
        # Update app state
        self.app.settings["theme"] = self.theme_var.get()
        self.app.settings["font_size"] = self.font_size_var.get()
        _save_settings(self.app.settings)
        # Rebuild UI with new settings
        self.app._rebuild_ui()
        self.destroy()
```

### Pure Logic (No Tk/fitz)
```python
# In pagination.py
def clamp_page_size(size):
    """Clamp page size to valid range (10-100)."""
    return max(10, min(100, int(size)))

def compute_window_range(total_pages, window_start, window_size):
    """Compute (start, end) indices for thumbnail virtualization."""
    end = min(window_start + window_size, total_pages)
    return (window_start, end)
```

### OCR Provider Pattern
```python
# In ocr_providers/claude.py
class ClaudeProvider(OCRProvider):
    model_list_timeout = 30  # 30s for cloud
    
    def ocr_image_ex(self, image_base64, prompt):
        """Inherited signature, must return (text, stop_reason)."""
        # Build request, call Claude API
        response = self._api_call(...)
        return (response.text, response.stop_reason)
    
    def supports_text_prompt(self):
        return True  # Can generate summaries
    
    def complete_text_ex(self, texts_by_page, prompt):
        """Multi-page summary via text-only endpoint."""
        # Combine texts, call API
        return summary_text
```

---

*Structure analysis: 2026-07-16*
