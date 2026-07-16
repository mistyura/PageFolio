# Architecture

<!-- refreshed: 2026-07-16 -->
**Analysis Date:** 2026-07-16

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                   PDFEditorApp (Main Class)                 │
│  Composed of 8 Mixins: UI, File, Page, Redact, Viewer,     │
│  DnD, OCR, Print                                            │
├───────────────┬──────────────────┬───────────────────────┬──┤
│  UI/Dialog    │  Page Operations │  OCR System           │  │
│  Layer        │  & Rendering     │  (Multi-Provider)     │  │
│               │                  │                       │  │
└───────┬───────┴────────┬─────────┴───────┬───────────────┴──┘
        │                │                 │
        ▼                ▼                 ▼
┌──────────────────────────────────┬──────────────────────────┐
│  State Management                │  File I/O & Persistence  │
│  - doc (fitz.Document)           │  - pagefolio_settings    │
│  - current_page (int)            │  - Undo/Redo Blobs       │
│  - selected_pages (set)          │  - Plugin State          │
│  - _undo_stack / _redo_stack     │  - External Prompts     │
│  - settings (dict)               │                          │
└──────────────────────────────────┴──────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  PyMuPDF (fitz) / Tkinter / PIL (PIL)                       │
│  PDF manipulation, UI rendering, image processing           │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **PDFEditorApp** | Main application class, orchestrates all mixins | `pagefolio/app.py` |
| **UIBuilderMixin** | Tkinter UI construction, theming, styles, layout | `pagefolio/ui_builder.py` |
| **FileOpsMixin** | File I/O, undo/redo stack management, PDF save/load | `pagefolio/file_ops.py` |
| **PageOpsMixin** | Page operations (rotate, delete, crop, merge, split) | `pagefolio/page_ops.py` |
| **RedactOpsMixin** | Redaction (blackout/mosaic), rectangle selection | `pagefolio/redact_ops.py` |
| **ViewerMixin** | Preview canvas, zoom, thumbnail rendering, caching | `pagefolio/viewer.py` |
| **DnDMixin** | Drag-and-drop for thumbnail reordering | `pagefolio/dnd.py` |
| **OCRMixin** | OCR orchestration, provider selection, button state | `pagefolio/ocr.py` |
| **PrintOpsMixin** | Print dialog, OS integration (Windows printing) | `pagefolio/print_ops.py` |
| **OCR Provider System** | Multi-backend OCR (Claude, Gemini, Tesseract, etc.) | `pagefolio/ocr_providers/` |
| **OCR Pipeline** | Producer-consumer pure logic (Tk/fitz-independent) | `pagefolio/ocr_pipeline.py` |
| **Undo/Redo Blob Store** | Memory/disk blob management for undo operations | `pagefolio/undo_store.py` |
| **Plugin System** | Plugin loader, lifecycle, hook management | `pagefolio/plugins.py` |
| **Settings Manager** | JSON persistence, theme resolution, font generation | `pagefolio/settings.py` |
| **Pagination** | Thumbnail window virtualization pure logic | `pagefolio/pagination.py` |
| **Markdown Render** | OCR result markdown parsing and formatting | `pagefolio/md_render.py` |

## Pattern Overview

**Overall:** Multi-Mixin composition pattern with pure logic layers

**Key Characteristics:**
- Single large `PDFEditorApp` class composed of 8 focused Mixins
- Pure logic layers (Tk/fitz-independent) for pagination, OCR pipeline, markdown rendering, blob store
- Async-safe state management with generation counters for preview/thumbnail rendering
- Undo/Redo as deque-based operation deltas (max 20 entries), not full state snapshots
- Plugin system with hook points for lifecycle and page operations
- Multi-threaded OCR with ThreadPoolExecutor, circuit breaker for fault tolerance

## Layers

**UI Layer:**
- Purpose: Tkinter UI construction, event handling, dialog management
- Location: `pagefolio/ui_builder.py`, `pagefolio/dialogs/`, Mixin event handlers
- Contains: Button/menu definitions, layout, styling, event callbacks
- Depends on: Settings (theme/font), constants (colors), dialogs
- Used by: Main window, PDFEditorApp initialization

**State Management Layer:**
- Purpose: Centralized document and application state
- Location: PDFEditorApp attributes (`self.doc`, `self.current_page`, `self.settings`, etc.)
- Contains: PDF document reference, page selection, undo/redo stacks, user settings
- Depends on: None (foundational)
- Used by: All mixins

**File Operations Layer:**
- Purpose: PDF file I/O, undo/redo mechanics, password handling
- Location: `pagefolio/file_ops.py`, `pagefolio/undo_store.py`
- Contains: Open/save logic, Blob management (MemBlob/FileBlob), password encryption (AES-256)
- Depends on: PyMuPDF (fitz), state management
- Used by: All page-modifying operations

**Page Operations Layer:**
- Purpose: PDF page manipulation (rotate, delete, crop, merge, split)
- Location: `pagefolio/page_ops.py`
- Contains: Rotation, deletion, cropping (CropBox), merging, insertion, splitting
- Depends on: PyMuPDF (fitz), file operations (for undo deltas)
- Used by: Page editing workflows

**Redaction Layer:**
- Purpose: Content removal (blackout/mosaic application)
- Location: `pagefolio/redact_ops.py`
- Contains: Rectangle selection, redaction application, undo support
- Depends on: PyMuPDF (fitz), page operations, undo store
- Used by: Content redaction workflows

**Viewer Layer:**
- Purpose: PDF visualization, preview rendering, zoom, thumbnail display
- Location: `pagefolio/viewer.py`, `pagefolio/thumb_cache.py`
- Contains: Canvas rendering, zoom controls, thumbnail generation/caching, pagination
- Depends on: PyMuPDF (fitz), PIL/Pillow, LRU cache, pagination pure logic
- Used by: Display, thumbnail panel

**OCR System Layer:**
- Purpose: Text extraction from PDF pages via multiple providers
- Location: `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/ocr_pipeline.py`, `pagefolio/ocr_providers/`
- Contains: Provider abstraction (base + 6 implementations), dialog UI, pipeline pure logic, result formatting
- Depends on: Providers (Claude API, Google Gemini, Tesseract, LM Studio, Ollama, RunPod), threading, settings
- Used by: OCR workflows, batch operations

**Plugin System Layer:**
- Purpose: Third-party plugin loading and lifecycle management
- Location: `pagefolio/plugins.py`
- Contains: Plugin base class, manager, hook dispatch, enable/disable logic
- Depends on: Settings (disabled_plugins list)
- Used by: Application initialization, operation hooks

**Dialog Layer:**
- Purpose: Secondary windows for user interaction (settings, merge, OCR, etc.)
- Location: `pagefolio/dialogs/`
- Contains: Settings, merge order, LLM config, plugin mgmt, batch OCR, shortcuts editor
- Depends on: Settings, providers, UI helpers
- Used by: User-initiated configuration

## Data Flow

### Primary Request Path: Open → Edit → Save

1. User initiates file open → `_open_file()` (`FileOpsMixin`) (`pagefolio/file_ops.py:200+`)
2. File dialog shows → PyMuPDF opens document → `self.doc = fitz.open(path)` 
3. Password check if protected → `_authenticate_doc()` prompts user if needed
4. `self.current_page = 0` set, thumbnails generated
5. `_refresh_all()` → `_render_preview()` + `_queue_thumbnails()` render current page and window
6. User edits (rotate/crop/delete) → Operation creates undo delta, modifies `self.doc`
7. `_refresh_all()` re-renders UI with new state
8. User saves → `_save_file()` calls `self.doc.save()` with encryption if needed
9. `_push_evicting()` clears redo stack on new operation

### OCR Flow

1. User selects OCR provider, clicks "▶ 実行" in OCR dialog
2. `OCRDialog._on_run()` → `_run_gen()` initializes `PipelineState`
3. Producer (main thread after loop): `_render_next_page()` renders page to base64
4. `try_enqueue()` sends `(page_index, base64_image, prompt)` to queue
5. Consumer workers (ThreadPoolExecutor): `consume_one()` calls provider `ocr_image_ex()`
6. Retryable failures: backoff loop with circuit breaker (max 3 consecutive)
7. Fatal errors: `send_sentinels()` breaks producer, halts pipeline
8. Results collected: `_on_ocr_result()` callback formats result to dialog
9. Markdown preset: `_insert_markdown()` parses and formats result with `md_render.py`

### Undo/Redo Mechanism

1. Page edit operation (rotate/delete/crop) → create undo delta dict
2. Call `_push_evicting(delta)` with operation data (op type, affected pages, page bytes)
3. Redo stack cleared on new operation
4. Max 20 entries (MAX_UNDO) enforced by deque maxlen
5. Blob management: Large blobs (>64KiB) stored in tempfile, small in memory
6. On undo: retrieve delta from `_undo_stack`, apply inverse operation, push to `_redo_stack`
7. On quit: `_clear_undo_stacks()` → `_undo_blob_store.purge()` cleans tempfiles

**State Management:**
- `self.doc` holds active PyMuPDF Document (None when closed)
- `self.settings` dict persisted to `pagefolio_settings.json` (theme, font_size, disabled_plugins, shortcuts, etc.)
- `self._undo_stack` / `self._redo_stack` hold operation deltas as dicts (not full snapshots)
- `self._preview_gen` / `self._thumb_gen` generation counters prevent stale async renders overwriting newer ones
- Generation counter pattern: increment before starting async task, discard result if counter advanced while task ran

## Key Abstractions

**OCRProvider (ABC):**
- Purpose: Unified interface for text extraction backends
- Examples: `ClaudeProvider`, `GeminiProvider`, `TesseractProvider`, `LMStudioProvider`, `OllamaProvider`, `RunPodProvider`
- Pattern: Abstract base with `ocr_image_ex()` and optional `supports_text_prompt()`/`complete_text_ex()` for multi-page summaries
- Provider selection: environment variables (`PAGEFOLIO_<PROVIDER>_API_KEY`) or settings dialog input
- Timeout handling: class attribute `model_list_timeout` per provider (10s local, 30s cloud, 90s RunPod for cold starts)

**PipelineState:**
- Purpose: Thread-safe shared state for OCR producer-consumer pipeline
- Pattern: Internal `threading.Lock` protects counters (`done_count`, `consec_err_count`, `workers_remaining`)
- Circuit breaker: consecutive failure threshold (default 3) triggers fatal error
- Generation guard: `_run_gen` increments each OCR run, results discarded if generation advanced

**LruCache (Thumbnail Cache):**
- Purpose: Memory-bounded thumbnail image cache with LRU eviction
- Capacity: 300 items (3× max window size of 100)
- Keys: page index, values: `ImageTk.PhotoImage` objects
- Used by: Pagination virtualization to avoid regenerating common thumb images

**Blob Storage (MemBlob/FileBlob):**
- Purpose: Flexible storage for undo page snapshots (64KiB threshold)
- MemBlob: Small snapshots (<64KiB) stored in memory
- FileBlob: Large snapshots in tempfile, lazy-loaded on restore
- Pattern: `load()` returns bytes, `release()` cleans up tempfile (lifecycle managed by deque eviction and atexit)

## Entry Points

**Application Entry:**
- Location: `pagefolio.py` (CLI script)
- Triggers: Direct execution (`python pagefolio.py`)
- Responsibilities: Import and call `pagefolio.__main__.main()`

**Main Function:**
- Location: `pagefolio/__main__.py:main()`
- Triggers: Application launch
- Responsibilities: Create Tk root window, instantiate `PDFEditorApp`, optionally setup D&D, run event loop

**PDFEditorApp Constructor:**
- Location: `pagefolio/app.py:__init__`
- Triggers: Called by `main()`
- Responsibilities: Initialize state, load settings/theme, build UI, build menus, bind shortcuts, load plugins

**User Events:**
- File menu clicks → `_open_file()` / `_save_file()` / `_save_as()`
- Page operations → `_rotate_selected()` / `_delete_selected()` / `_open_crop_mode()`
- Undo/Redo → `_undo()` / `_redo()`
- OCR → `_open_batch_ocr()` → `BatchOCRDialog`
- Settings → Dialog windows (`SettingsDialog`, `LLMConfigDialog`, `ShortcutsDialog`)
- D&D File Drop → `_on_dnd_drop()` → `MergeOrderDialog`

## Architectural Constraints

- **Threading:** Tkinter main thread handles all UI rendering and state updates. PDF rendering (preview/thumbnails) and OCR are off-thread but results posted back to main via `root.after()` with generation guards. OCR uses `ThreadPoolExecutor` for parallel API calls.
- **Global state:** `C` (theme dict, `pagefolio/themes.py`) and `_current_font_size` (in `pagefolio/settings.py`) are module-level singletons updated at runtime when theme/font changes. All Mixin methods access via `self._font()` helper and `C` dict.
- **Undo limit:** Hard-coded `MAX_UNDO = 20` in `PDFEditorApp`. Each entry is operation-specific delta dict (rotate: rotation values, crop: CropBox tuple, delete: page blobs, etc.), not full PDF serialization.
- **Circular imports:** Settings module must not import pagefolio internals to prevent cycles on startup. OCR pipeline avoids importing UI modules; providers import only standard library + requests.
- **CropBox safety:** All crop operations must clamp `CropBox` inside page's `MediaBox` before calling `set_cropbox()` (`pagefolio/page_ops.py` helpers ensure this).
- **PDF not thread-safe:** `fitz.Document` never shared across threads. OCR renders pages on main thread, sends base64 bytes to workers.
- **Generation counter pattern:** Async renders (preview, thumbnails) increment gen counter before task, discard result if counter advanced during task (prevents stale renders overwriting fresh ones).

## Anti-Patterns

### Mixin Coupling Without Inheritance

**What happens:** Mixins call other Mixin methods directly via `self`, creating implicit dependencies.

**Why it's wrong:** Large class becomes hard to reason about; unclear which methods a Mixin truly depends on; refactoring breaks hidden contracts.

**Do this instead:** Document Mixin dependencies in module docstring (e.g., "PageOpsMixin depends on FileOpsMixin undo methods"). Accept that Mixin order in class definition matters; place higher-level Mixins after utility Mixins.

### State Snapshots in Undo Instead of Deltas

**What happens:** Early code stored full PDF bytes on every operation; `_undo_stack` contained megabytes per entry even for single-page edits.

**Why it's wrong:** Large memory footprint; slow to push/pop; defeats Undo limit (20 entries = 20 PDFs in memory).

**Do this instead:** (`v1.7.0+`) Store operation-specific deltas only: rotate stores angle list, delete stores affected page blobs, etc. Use `UndoBlobStore` to externalize >64KiB blobs to tempfiles.

### API Keys in Settings File

**What happens:** OCR provider API keys hardcoded in `pagefolio_settings.json` (insecure on shared machines).

**Why it's wrong:** Secrets in plaintext JSON; visible in version control if accidentally committed; leaked in backups.

**Do this instead:** (`v1.7.0+`) Load API keys from environment variables (`PAGEFOLIO_CLAUDE_API_KEY`, etc.) or session-only dict (`self._session_api_keys`). Settings file explicitly guards sensitive keys with `_SENSITIVE_KEYS` set.

### Generation Counter Omission in Async Tasks

**What happens:** Preview/thumbnail rendered in background completes *after* user navigates to new page; stale image overwrites fresh one.

**Why it's wrong:** UI flicker, incorrect preview shown; user confusion.

**Do this instead:** Increment `self._preview_gen` before rendering, pass gen ID to task callback, discard result if `self._preview_gen` advanced (true even if callback scheduled multiple times).

## Error Handling

**Strategy:** Try-except with user-visible messagebox feedback; plugin callbacks individually wrapped so one plugin failure cannot crash others.

**Patterns:**
- File not found → `messagebox.showerror()` with localized message
- PDF corrupted → `messagebox.showerror()` + fall back to closed state
- OCR provider error → `OCRRetryableError` (with backoff) vs. fatal error (stop pipeline, show message)
- Plugin callback error → Logged, pipeline continues, user notified via toast if critical
- Password prompt → `simpledialog.askstring()` with retry on failure

## Cross-Cutting Concerns

**Logging:** Standard `logging` module, `WARNING` level by default, file-specific loggers (`logger = logging.getLogger(__name__)`) for each module.

**Validation:** 
- CropBox: Clamped to MediaBox before application
- Page range: Validated against `self.doc.page_count` before operation
- Undo stack: Deque maxlen enforces cap; old entries auto-evicted

**Authentication:** 
- PDF password: Prompted via `simpledialog.askstring()` if document is encrypted
- API keys: Resolved from env vars → settings → dialog input in order of precedence

**Localization:** `self.lang` determines ja/en; all UI strings via `self._t("key_name")` helper (lookups from `LANG` dict in `pagefolio/lang.py`).

**Theming:** `C` global dict updated via `_apply_theme()` on startup or dialog change; all Tkinter colors reference `C` (e.g., `bg=C["BG_DARK"]`), no hex hardcodes.

---

*Architecture analysis: 2026-07-16*
