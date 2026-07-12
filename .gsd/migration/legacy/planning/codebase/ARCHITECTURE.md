<!-- refreshed: 2026-07-03 -->
# Architecture

**Analysis Date:** 2026-07-03

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│              Application Entry Point & Window                │
│  pagefolio.py → __main__.py → PDFEditorApp(root)             │
│  `pagefolio/__main__.py` (Tk/TkinterDnD initialization)      │
└────────────────┬──────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│               PDFEditorApp (8 Mixin Unified Class)           │
│  Inherits from: UIBuilderMixin, FileOpsMixin, PageOpsMixin, │
│  RedactOpsMixin, ViewerMixin, DnDMixin, OCRMixin,            │
│  PrintOpsMixin                                               │
│  Location: `pagefolio/app.py`                                │
│  State: doc (fitz.Document), current_page, selected_pages,  │
│  undo/redo stacks, settings, plugin_manager                  │
└────────────┬─────────────────────┬──────────────────────────┘
             │                     │
    ┌────────▼────────┐  ┌─────────▼──────────┐
    │ UI & Rendering  │  │  PDF File & Page   │
    │   Mixins        │  │   Operations       │
    └─────────────────┘  └────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| PDFEditorApp | Root app; orchestrates all Mixins; manages state (doc, current_page, selected_pages, undo/redo) | `pagefolio/app.py` |
| UIBuilderMixin | Builds Tkinter styles, layouts (header, paned window, thumbnail panel, preview, tools) | `pagefolio/ui_builder.py` |
| FileOpsMixin | File open/save/saveas; Undo/Redo; password handling (encrypt/decrypt); Blob lifecycle | `pagefolio/file_ops.py` |
| PageOpsMixin | Page operations: rotate, delete, crop, insert, merge, split, image export | `pagefolio/page_ops.py` |
| RedactOpsMixin | Page editing: blackout redaction and mosaic (矩形選択共有) | `pagefolio/redact_ops.py` |
| ViewerMixin | Render preview; generate/cache thumbnails; zoom; select pages; popup preview | `pagefolio/viewer.py` |
| DnDMixin | Thumbnail drag-and-drop reordering (single/multi-page) | `pagefolio/dnd.py` |
| OCRMixin | OCR orchestration; provider selection/setup; concurrent page processing | `pagefolio/ocr.py` |
| PrintOpsMixin | Print PDF via OS default handler; temporary file creation | `pagefolio/print_ops.py` |
| PluginManager | Plugin discovery/load/unload/enable/disable; lifecycle event dispatch | `pagefolio/plugins.py` |
| PDFEditorPlugin | Abstract base class for third-party plugins | `pagefolio/plugins.py` |
| Dialogs | About, Settings, Plugin, Merge (order/resize), LLM config, Export Images, Password | `pagefolio/dialogs/` |
| OCRDialog | Multi-page OCR UI; progress display; result viewer/exporter; summary generation | `pagefolio/ocr_dialog.py` |
| UndoBlobStore | Memory/disk Blob lifecycle; 64KiB threshold; tempfile management; atexit purge | `pagefolio/undo_store.py` |
| Pagination Layer | Pure functions for window display calculations; local↔global index conversion | `pagefolio/pagination.py` |
| Themes/Lang | Color theme dicts (THEMES, C); multi-language string dicts (LANG) | `pagefolio/themes.py`, `pagefolio/lang.py` |
| Settings Utilities | Load/save JSON config; theme application; font helpers | `pagefolio/settings.py` |
| File Drop Handler | tkinterdnd2 integration for drag-and-drop file open | `pagefolio/file_drop.py` |

## Pattern Overview

**Overall:** Mixin composition pattern with state centralization.

**Key Characteristics:**
- Single PDFEditorApp class inherits 8 Mixins, each owning distinct responsibilities
- Centralized state in PDFEditorApp instance (doc, current_page, selected_pages, settings, etc.)
- Tkinter main-thread UI with background rendering via generation counters (`_preview_gen`, `_thumb_gen`)
- Plugin hook system for extensibility without modifying core
- Blob-based undo system with automatic memory/disk offloading for large PDFs

## Layers

**Presentation Layer (UI):**
- Purpose: Render Tkinter UI; handle user input; display preview/thumbnails
- Location: `pagefolio/ui_builder.py`, `pagefolio/viewer.py`, `pagefolio/dialogs/`
- Contains: Styles, layouts, Canvas widgets, Button/Label definitions
- Depends on: PDFEditorApp state; theme constants (C); language dicts (LANG)
- Used by: Main event loop

**Business Logic Layer (Operations):**
- Purpose: Implement PDF page operations; undo/redo; OCR orchestration
- Location: `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/redact_ops.py`, `pagefolio/ocr.py`, `pagefolio/print_ops.py`
- Contains: Page manipulation (rotate, crop, delete, merge), file I/O, OCR provider setup
- Depends on: fitz.Document; Blob system; OCR providers
- Used by: UI event handlers; user actions

**State & Configuration Layer:**
- Purpose: Manage app state persistence; theme/language resolution; plugin lifecycle
- Location: `pagefolio/settings.py`, `pagefolio/plugins.py`, `pagefolio/themes.py`, `pagefolio/lang.py`, `pagefolio/undo_store.py`
- Contains: JSON config read/write; theme dict application; plugin loading/firing hooks
- Depends on: Standard library (json, tempfile, importlib); constants
- Used by: App initialization; Mixin methods; dialogs

**External Integration Layer (I/O):**
- Purpose: Communicate with external systems (OCR APIs, file system, OS printer)
- Location: `pagefolio/ocr_providers.py`, `pagefolio/file_drop.py`, `pagefolio/print_ops.py`
- Contains: HTTP requests to LMStudio/Claude/Gemini; tkinterdnd2 bindings; OS printer calls
- Depends on: urllib, fitz, PIL; external APIs
- Used by: OCRMixin; FileOpsMixin; PrintOpsMixin

**Pure Utility Layer (Non-Tkinter/Non-fitz):**
- Purpose: Reusable logic independent of framework/UI
- Location: `pagefolio/pagination.py`, `pagefolio/md_render.py`, `pagefolio/undo_store.py`, `pagefolio/page_ops.py` (parsing functions)
- Contains: Window calculations, Markdown parsing, Blob I/O, page range parsing
- Depends on: Standard library only
- Used by: ViewerMixin, OCRDialog, FileOpsMixin

## Data Flow

### Primary Request Path (File Open)

1. User clicks "Open File" or D&D file → `_open_file()` or `_on_dnd_drop()` (`pagefolio/app.py:214-269`)
2. Dialog opens / file path extracted
3. Call `_open_pdf_path(path)` → `_authenticate_doc()` if password required (`pagefolio/file_ops.py`)
4. `fitz.open(path)` creates document; assign to `self.doc`
5. Set `self.current_page = 0`; clear `self.selected_pages`
6. Fire plugin hook `on_file_open(app, path)` (`pagefolio/plugins.py`)
7. Call `self._refresh_all()` → regenerate preview + thumbnails + update buttons
8. Update status bar via `_set_status()`

### Page Render (Preview Display)

1. User navigates to page N or page changes via operation
2. `_show_preview()` called (`pagefolio/viewer.py:61+`)
3. Increments `self._preview_gen` (generation counter)
4. Delegates to `root.after()` callback (main thread) to render `_render_preview_pixmap(page_idx, zoom)` (`pagefolio/viewer.py:50-59`)
5. Renders fitz page with `page.get_pixmap(matrix=fitz.Matrix(zoom*1.5, zoom*1.5))` → PIL Image → PhotoImage
6. Displays on `self.preview_canvas`
7. Older generation renders discarded silently (stale result protection)

### Thumbnail Generation

1. `_refresh_thumbs()` called (after file open / page changes)
2. For each page in current window (`_page_window_start` to `_page_window_start + _page_size`):
   - Check cache (`self.thumb_cache`)
   - If not cached: render via `root.after()` with generation counter `_thumb_gen`
   - Render: `page.get_pixmap(matrix=fitz.Matrix(0.22, 0.22))` → PIL → PhotoImage
   - Store in cache; display on Canvas
3. Stale renders (older `_thumb_gen`) discarded

### Page Operation (Example: Rotate)

1. User clicks "Rotate Right" → `_rotate_selected(90)`
2. Get target pages: `targets = self._get_targets()` (selected or current)
3. For each page in targets:
   - `page.set_rotation(deg)` rotates page metadata
4. Push undo delta: `{"op": "rotate", "data": [(page_i, deg), ...]}` → `_undo_stack`
5. Clear redo stack (operation invalidates redo path)
6. Fire plugin hook `on_page_rotate(app, pages, degrees)`
7. Call `_refresh_all()` to re-render
8. Update status bar

### Undo/Redo Flow

1. User presses Ctrl+Z → `_undo()` (`pagefolio/file_ops.py:100+`)
2. Pop from `_undo_stack` → get state dict with `op` and `data`
3. Based on `op` type (rotate, crop, delete, insert, etc.):
   - Restore previous state (undo side effect)
   - Compute reverse delta
4. Push reverse delta to `_redo_stack`
5. Call `_refresh_all()`
6. Blob disposal: Identity check prevents double-release; `_dispose_state()` called on eviction/redo clear

### OCR Flow

1. User selects pages and clicks "🔍 OCR" → `_on_ocr()` (`pagefolio/ocr.py`)
2. Open `OCRDialog` → display multi-page OCR UI
3. User chooses preset, provider, custom prompt
4. Dialog starts background worker thread via `_run_gen()` (generation guard)
5. For each page (concurrent ThreadPoolExecutor):
   - `_render_preview_pixmap()` renders to base64
   - `build_provider()` instantiates OCRProvider (Claude/Gemini/LMStudio/Tesseract)
   - Call `provider.ocr_image_ex()` → LLM/OCR API
   - Collect result
6. Display results in OCRDialog (Markdown or raw)
7. User can export, copy, or generate summary
8. Summary generation: concatenate all results; send as text_prompt to provider (text-only mode)

### Plugin Lifecycle

1. App initialization: `PluginManager.load_all(app, disabled_ids)`
2. Plugin discovery: scan `plugins/` directory for `.py` files
3. Dynamic import via `importlib.util.spec_from_file_location()`
4. Instantiate plugin; assign ID
5. Call `plugin.on_load(app)` hook
6. On file open/page change/operation: fire corresponding hook
7. User disables plugin via SettingsDialog → store in `settings["disabled_plugins"]`
8. On quit: call `plugin.on_unload(app)` for enabled plugins

**State Management:**
- `self.doc`: fitz.Document or None (represents open PDF in memory)
- `self.current_page`: 0-based index of displayed page
- `self.selected_pages`: set of 0-based page indices for bulk operations
- `self._undo_stack`: deque (maxlen=MAX_UNDO=20) of operation deltas
- `self._redo_stack`: deque of reverse deltas
- `self._page_window_start`: window offset for thumbnail display (D-05)
- `self._page_size`: number of thumbnails per window (default 20, range 10–100)
- `self.settings`: dict persisted to `pagefolio_settings.json` (theme, font size, window geom, etc.)
- `self.thumb_cache`: dict of PIL PhotoImage objects indexed by page number
- `self._preview_gen` / `self._thumb_gen`: generation counters for stale render protection

## Key Abstractions

**PDFEditorApp State Machine:**
- Purpose: Encapsulate all mutable state; single source of truth for app condition
- Examples: `self.doc`, `self.current_page`, `self.selected_pages`, `self.edit_mode`
- Pattern: Instance attributes updated by Mixin methods; state persisted to JSON on quit

**Mixin Composition:**
- Purpose: Separate concerns (UI, file ops, page ops, OCR) into independently testable classes
- Examples: UIBuilderMixin (layout), FileOpsMixin (I/O), OCRMixin (external API)
- Pattern: Each Mixin adds methods to PDFEditorApp via multiple inheritance

**Generation Counter (Stale Result Protection):**
- Purpose: Prevent old background renders from overwriting new ones
- Examples: `_preview_gen`, `_thumb_gen`
- Pattern: Increment counter before async work; discard if counter has advanced by time result arrives

**Blob Abstraction (Memory/Disk Offloading):**
- Purpose: Transparent storage of page bytes for undo/redo; auto-migrate to disk for large PDFs
- Examples: MemBlob (small data), FileBlob (large data offloaded to tempfile)
- Pattern: Unified `.load()` / `.release()` interface; UndoBlobStore manages lifecycle

**Pagination Window (Local ↔ Global Index Mapping):**
- Purpose: Display subset of pages (window) while maintaining full-page selections
- Examples: `to_global()` (local → full index), `to_local()` (reverse), `window_bounds()`, `clamp_window_start()`
- Pattern: Pure functions in `pagination.py` (no state, no Tk/fitz); ViewerMixin applies mappings on render

**Plugin Hook System:**
- Purpose: Allow third-party code to respond to events without modifying core
- Examples: `on_load`, `on_file_open`, `on_page_rotate`, `on_merge`, `build_ui`
- Pattern: PluginManager fires hooks by calling methods on plugin instances; exceptions in one plugin don't crash others

**OCR Provider Abstraction:**
- Purpose: Unified interface for multiple OCR backends (Claude, Gemini, LMStudio, Tesseract)
- Examples: `OCRProvider` (ABC), `ClaudeProvider`, `GeminiProvider`, `LMStudioProvider`, `TesseractProvider`
- Pattern: `build_provider()` factory selects implementation; `ocr_image_ex()` method for image input

**Theme & Language Dicts:**
- Purpose: Runtime-swappable color/text configuration
- Examples: `C` (theme dict, mutable at runtime), `LANG` (language strings, immutable)
- Pattern: UI reads from `C["BG_DARK"]`, `LANG["ja"]["button_open"]` instead of hardcoding

## Entry Points

**`pagefolio.py` (CLI entry point):**
- Location: `pagefolio.py` (root of repo)
- Triggers: `python pagefolio.py`
- Responsibilities: Import `__main__.main()` and invoke it

**`pagefolio/__main__.py` (Package entry point):**
- Location: `pagefolio/__main__.py`
- Triggers: `python -m pagefolio`
- Responsibilities: Initialize Tk/TkinterDnD root window; create PDFEditorApp instance; set up file drop handler; start event loop

**`PDFEditorApp.__init__()` (App initialization):**
- Location: `pagefolio/app.py:47-174`
- Triggers: Instantiation in `__main__.main()`
- Responsibilities: 
  - Load settings from JSON (`_load_settings()`)
  - Apply theme (`_apply_theme()`)
  - Restore window geometry
  - Build Tkinter styles (`_build_styles()`)
  - Build UI layout (`_build_ui()`)
  - Load plugins (`plugin_manager.load_all()`)
  - Set up keyboard shortcuts
  - Register WM_DELETE_WINDOW handler

**`_open_file()` / `_on_dnd_drop()` (File open entry):**
- Location: `pagefolio/file_ops.py`, `pagefolio/app.py:214-269`
- Triggers: User clicks "Open File" or drags file onto window
- Responsibilities: Validate path; open PDF; authenticate if password-protected; refresh UI

**Plugin hooks:**
- Location: `pagefolio/plugins.py`
- Triggers: Specific app events (file open, page rotate, etc.)
- Responsibilities: Fire registered plugin methods; catch exceptions to prevent cascade failures

## Architectural Constraints

- **Threading:** UI runs on Tkinter main thread. Preview and thumbnail renders are processed on main thread via `root.after()` chained calls; generation counters prevent stale results. OCR uses `ThreadPoolExecutor` for concurrent image processing.
- **Global state:** `C` (theme dict) and `_current_font_size` in `pagefolio/settings.py` are module-level mutable singletons updated at runtime during theme changes.
- **Circular imports:** Minimal — constants re-export themes/lang to avoid circular deps. Dialogs are imported locally in methods to prevent circular imports at module level.
- **Undo limit:** Hard-coded to `MAX_UNDO = 20` in `pagefolio/app.py:45`. Each entry is a delta dict (not full PDF serialization), indexed by operation type (rotate, crop, delete, etc.).
- **Undo Blob lifecycle (v1.7.0):** Page captures via `_capture_page_blob()` → UndoBlobStore. 64KiB+ → FileBlob (tempfile), <64KiB → MemBlob (memory). Restoration via `_blob_bytes()` (handles both Blob and raw bytes for backward compat). Disposal: deque eviction, redo clear, consumption, file close, atexit purge.
- **CropBox safety:** All crop operations must clamp CropBox inside MediaBox before calling `set_cropbox()`.
- **Password-protected PDFs:** Open via `_authenticate_doc()` prompt; password not stored in settings. Decrypt/encrypt operations via `save_with_password()` / `save_without_password()` (AES-256).
- **No fitz.Document sharing across threads:** OCR passes only base64-encoded pixmap data to worker threads.
- **Tkinter widget names follow convention:** `_` prefix for internal methods; `_on_*` for event handlers; `_do_*` for action methods.

## Anti-Patterns

### Accessing theme colors via raw hex strings instead of `C` dict

**What happens:** Code like `self.preview_canvas.configure(bg="#1a1a2e")` instead of `C["BG_DARK"]`
**Why it's wrong:** Theme changes at runtime won't update the widget. Hard-coded colors break in light/dark mode switching.
**Do this instead:** Always use `C["KEY"]` to read color at widget creation time and update time:
```python
# Wrong
self.canvas.configure(bg="#1a1a2e")

# Correct
self.canvas.configure(bg=C["BG_DARK"])
```
See `pagefolio/ui_builder.py:19+` for style definitions and `pagefolio/app.py:216` for runtime color usage.

### Hardcoding font sizes instead of using `_font()` helper

**What happens:** Code like `font=("Segoe UI", 12)` instead of `self._font(delta)`
**Why it's wrong:** Font size changes (settings) won't propagate. User's configured font size is ignored.
**Do this instead:** Use `self._font(delta)` to apply current base size + delta:
```python
# Wrong
label.configure(font=("Segoe UI", 12))

# Correct
label.configure(font=self._font(2))  # base_size + 2
```
See `pagefolio/ui_builder.py:100+` for `_font()` definition.

### Direct manipulation of undo/redo stacks via `append()` or `clear()`

**What happens:** `self._undo_stack.append(state)` without Blob lifecycle management
**Why it's wrong:** Blob references are never disposed; memory leaks for large PDFs or long undo histories.
**Do this instead:** Use `_push_evicting()` (which disposes evicted entries) or call `_clear_undo_stacks()` explicitly:
```python
# Wrong
self._undo_stack.append(state)
self._undo_stack.clear()

# Correct
self._push_evicting(self._undo_stack, state)  # disposes old if maxlen exceeded
self._clear_undo_stacks()  # calls purge on all Blobs
```
See `pagefolio/file_ops.py:115+` for `_push_evicting()` and `_clear_undo_stacks()` implementation.

### Not reconciling window start before thumbnail refresh

**What happens:** After delete/pagination changes, `_page_window_start` points to invalid window
**Why it's wrong:** Thumbnail display will jump or show wrong pages; scrolling breaks.
**Do this instead:** Call `reconcile_window_start()` from `pagination.py` before render:
```python
# In _refresh_thumbs after page deletion:
self._page_window_start = reconcile_window_start(
    self._page_window_start, self.current_page, self._page_size, len(self.doc)
)
```
See `pagefolio/pagination.py:73+` for reconciliation logic.

## Error Handling

**Strategy:** User-visible errors via `messagebox.showerror()` for operations. Background errors (plugins, OCR timeouts) logged but don't crash app.

**Patterns:**
- File I/O: Try-except with messagebox; log traceback
- Plugin hooks: Wrapped individually so one plugin failure doesn't crash others (see `_fire_hook()` in `pagefolio/plugins.py`)
- OCR: Timeout/network errors caught in worker thread; user notified via dialog status
- Undo/Redo: State mismatches logged; app stays responsive

## Cross-Cutting Concerns

**Logging:** Module-level `logger = logging.getLogger(__name__)` in each file. Config set in `PDFEditorApp.__init__()` to WARNING level (suppress debug noise in production).

**Validation:**
- Page index validation: `clamp` functions in `pagination.py` ensure indices stay in `[0, n_pages)`
- Password input: `simpledialog.askstring()` with password masking
- File path validation: `os.path.splitext()` checks extension; `SUPPORTED_EXTENSIONS` whitelist
- Page range parsing: `parse_page_ranges()` in `page_ops.py` validates user input

**Authentication:**
- Password-protected PDFs: `_authenticate_doc()` in `file_ops.py` prompts user; retries on failure
- API keys: Session-only storage in `_session_api_keys` dict (not persisted to JSON)

**Settings Persistence:**
- Load on app start: `_load_settings()` reads `pagefolio_settings.json`
- Save on app quit: `_save_settings()` writes back
- Sensitive keys (`_SENSITIVE_KEYS` in `settings.py`) excluded from JSON to prevent accidental secret leaks

---

*Architecture analysis: 2026-07-03*
