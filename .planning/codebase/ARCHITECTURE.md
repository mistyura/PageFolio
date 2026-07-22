<!-- refreshed: 2026-07-22 -->
# Architecture

**Analysis Date:** 2026-07-22

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Tkinter UI Layer                              │
│          (UIBuilderMixin, ViewerMixin, DnDMixin)                 │
│  Dialogs: Settings, LLM Config, Batch OCR, Merge, Password       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    root.mainloop()
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│           PDFEditorApp (Mixin Composition Layer)                 │
│  `pagefolio/app.py`                                              │
│  • 8 Mixins: UIBuilder, FileOps, PageOps, Redact, Viewer,       │
│    DnD, OCR, PrintOps                                            │
│  • State: doc, current_page, selected_pages, crop_rect, etc.    │
│  • Undo/Redo stacks (max 20 entries)                             │
└──────────────────────────┬──────────────────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  File Ops  │  │  Page Ops  │  │ OCR Mixin  │
    │FileOpsMixin│  │PageOpsMixin│  │ OCRMixin   │
    │ `file_ops` │  │`page_ops`  │  │  `ocr.py`  │
    └────────────┘  └────────────┘  └────┬───────┘
         │               │                 │
         │ Undo/Redo     │                 │ Provider
         │ Blob Store    │                 │ Dispatch
         │               │                 │
         ▼               ▼                 ▼
    ┌────────────────────────────────────────────┐
    │      PDF Logic Layer (Tk/fitz Independent)  │
    │                                             │
    │  • ocr_pipeline.py (PipelineState, etc.)    │
    │  • ocr_fallback.py (fallback routing)       │
    │  • pagination.py (window calculation)       │
    │  • undo_store.py (FileBlob/MemBlob)        │
    │  • md_render.py (Markdown parsing)          │
    │  • page_ops.py (pure functions)             │
    └────────────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────────────┐
    │     OCR Providers (Base + Implementations)  │
    │      `pagefolio/ocr_providers/`             │
    │                                             │
    │  • base.py (OCRProvider ABC)                │
    │  • claude.py (Claude API)                   │
    │  • gemini.py (Gemini API)                   │
    │  • lmstudio.py (Local LM Studio)            │
    │  • tesseract.py (Tesseract OCR)             │
    │  • ollama.py (Ollama Local)                 │
    │  • runpod.py (RunPod Serverless)            │
    │  • registry.py (Provider discovery)         │
    └────────────────────────────────────────────┘
         │
         ▼
    ┌────────────────────────────────────────────┐
    │      PDF & LLM External Services            │
    │                                             │
    │  • fitz (PyMuPDF) — PDF manipulation        │
    │  • Claude API, Gemini API — LLM OCR        │
    │  • Local: Tesseract, Ollama, LM Studio     │
    └────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| PDFEditorApp | Main composition root, state mgmt, event dispatch | `pagefolio/app.py` |
| UIBuilderMixin | Tkinter theme & layout construction | `pagefolio/ui_builder.py` |
| FileOpsMixin | Open/save/undo/redo, password handling | `pagefolio/file_ops.py` |
| PageOpsMixin | Rotate/delete/crop/insert/merge/split pages | `pagefolio/page_ops.py` |
| RedactOpsMixin | Redaction (black strikethrough) & mosaic | `pagefolio/redact_ops.py` |
| ViewerMixin | Preview, thumbnails, zoom, selection | `pagefolio/viewer.py` |
| DnDMixin | Drag-and-drop thumbnail reordering | `pagefolio/dnd.py` |
| OCRMixin | OCR dispatch, provider mgmt, button state | `pagefolio/ocr.py` |
| PrintOpsMixin | Print to default PDF handler | `pagefolio/print_ops.py` |
| OCRProvider (ABC) | Abstract interface for all OCR backends | `pagefolio/ocr_providers/base.py` |
| PluginManager | Plugin discovery, load/unload, lifecycle | `pagefolio/plugins.py` |
| SettingsDialog | Theme, font, OCR provider config | `pagefolio/dialogs/settings.py` |
| LLMConfigDialog | Cloud provider (Claude/Gemini) API setup | `pagefolio/dialogs/llm_config/dialog.py` |
| BatchOCRDialog | Multi-page OCR execution UI | `pagefolio/dialogs/batch_ocr.py` |
| PipelineState | Thread-safe producer-consumer coordination | `pagefolio/ocr_pipeline.py` |

## Pattern Overview

**Overall:** Mixin composition with pure logic layers for testability.

**Key Characteristics:**
- **Mixin Composition:** PDFEditorApp statically composes 8 mixins, each providing cohesive feature domain
- **Pure Logic Layers:** `ocr_pipeline.py`, `pagination.py`, `undo_store.py`, `md_render.py` are Tk/fitz independent pure functions/classes for testability
- **Plugin System:** Dynamic hook registration (on_load, on_file_open, on_page_rotate, etc.) with error isolation per plugin
- **Single State Source:** `self.doc` (fitz.Document), `self.current_page`, `self.selected_pages` are the primary state; all views/operations derive from these

## Layers

**UI Layer (Tkinter):**
- Purpose: Render PDF preview, thumbnails, status bar, handle user input
- Location: `pagefolio/app.py` (init → `_build_ui()`), `pagefolio/ui_builder.py` (styles), `pagefolio/viewer.py` (rendering)
- Contains: Tkinter widgets (Canvas, Frame, Button), event handlers, widget state
- Depends on: fitz for page rendering, settings for theme/font
- Used by: Root tk.Tk mainloop

**Application Layer (Mixins):**
- Purpose: Coordinate operations across file I/O, page editing, OCR dispatch, plugin lifecycle
- Location: `pagefolio/app.py` (composition), individual mixin files
- Contains: Business logic, state transitions, event dispatch, error handling
- Depends on: PDF/OCR logic layers, Tk for UI updates
- Used by: UI event handlers

**PDF/OCR Logic Layer (Pure Functions):**
- Purpose: Decouple business logic from Tkinter/fitz for testability
- Location: `pagefolio/ocr_pipeline.py`, `pagefolio/pagination.py`, `pagefolio/undo_store.py`, `pagefolio/md_render.py`, `pagefolio/page_ops.py`
- Contains: State machines, coordinate transforms, Markdown parsing, deferred allocation
- Depends on: Python stdlib only (or minimal external)
- Used by: Application layer (Mixins), tests

**OCR Provider Layer (Plugin Pattern):**
- Purpose: Abstract different OCR backends (local & cloud)
- Location: `pagefolio/ocr_providers/` package
- Contains: `OCRProvider` ABC, concrete providers (Claude, Gemini, Tesseract, etc.), error types
- Depends on: External APIs (http), local CLI tools (Tesseract), Python stdlib
- Used by: OCRMixin (dispatch → provider instance), plugin system (custom provider registration)

**Data Storage Layer:**
- Purpose: Serialize/deserialize PDFs, settings, cache
- Location: fitz.Document (RAM), `pagefolio_settings.json` (disk), tempfiles (Blob cache)
- Contains: PDF bytes, JSON config, LRU thumbnail cache
- Depends on: PyMuPDF (fitz), filesystem
- Used by: All layers (read/write)

## Data Flow

### Primary Request Path (User Opens PDF)

1. **User clicks "Open"** → `_open_file()` in `FileOpsMixin`
2. **File dialog** → User selects PDF path
3. **Password check** (if needed) → `_authenticate_doc()` prompts for password
4. **Load PDF** → `fitz.open(filepath)` → `self.doc`
5. **Update state** → `self.current_page = 0`, `self.selected_pages = {}`
6. **Clear undo/redo** → `_clear_undo_stacks()`
7. **Refresh all** → `_refresh_all()` →
   - `_show_preview()` (renders current page via `_render_preview_pixmap()`)
   - `_refresh_thumbs_all()` (batch generate thumbnails on `root.after()`)
   - `_set_status(f"Opened: {filename}")`
8. **Update buttons** → `_update_doc_buttons_state()`

### Undo/Redo Operation (User Rotates Page)

1. **User selects pages & clicks "Rotate 90°"**
2. **Save undo** → `_save_undo("rotate", targets=selected_pages)` records rotation angle for each page
3. **Apply operation** → Update `self.doc[i].rotation` for each page
4. **Clear redo** → `_clear_redo_stack()` (redo stack is invalidated by new operation)
5. **Refresh** → `_refresh_all()` updates preview & thumbnails
6. **Status** → Shows operation result

When user clicks "Undo":
1. **Pop undo stack** → Retrieve stored rotation angles
2. **Restore** → Set `self.doc[i].rotation` back to original
3. **Push redo** → `_save_undo()` into redo stack with inverse operation
4. **Refresh** → Display restored state

### OCR Multi-Page Flow (Batch OCR Dialog)

1. **User opens batch OCR dialog** → `BatchOCRDialog()`
2. **Select pages & provider** → User chooses pages, sets prompt, picks OCR provider
3. **Click Run** → Dialog spawns worker threads via `ThreadPoolExecutor`
4. **Producer** (main thread via `root.after()`):
   - Render page to base64 PNG
   - Enqueue to shared `queue.Queue`
   - Use `PipelineState.record_success()` to update progress
5. **Consumer** (worker threads):
   - Dequeue image from queue
   - Call `OCRProvider.ocr_image(b64_png, prompt)` (may retry on 429/5xx)
   - Update `PipelineState` with result or error
   - Repeat until sentinel (None) received
6. **Dialog waits** → Polls `PipelineState` progress, displays results incrementally
7. **Summary** (optional) → Call `OCRProvider.complete_text_ex()` to merge all results

### State Management

**Primary State Sources:**
- `self.doc` (`fitz.Document`) — Open PDF or None
- `self.current_page` (int) — 0-based page index
- `self.selected_pages` (set[int]) — Multi-selected page indices
- `self.settings` (dict) — Persisted config (theme, font size, shortcuts, etc.)
- `self.zoom` (float) — Preview zoom factor
- `self._page_window_start` (int) — Thumbnail window start index (pagination)
- `self._page_size` (int) — Thumbnail window size (10–100 pages)

**Derived State:**
- `self.preview_img_ref` — ImageTk.PhotoImage currently displayed
- `self.thumb_images` — List of ImageTk.PhotoImage for visible window
- `self.crop_rect` — Active crop selection or None
- `self.crop_mode` — Boolean flag for crop mode active
- `self._undo_stack`, `self._redo_stack` (deque) — Operation history

**Blob Store Lifecycle:**
- On operation (rotate/crop/delete/merge) → Capture affected pages as Blob (FileBlob ≥64KiB, MemBlob <64KiB)
- On push to undo stack → Store Blob reference in state dict
- On stack eviction (maxlen=20 reached) → Call `_dispose_state()` to release temp files
- On redo clear (new operation after undo) → Release entire redo stack
- On close/exit → `_clear_undo_stacks()` purges all Blob files

## Key Abstractions

**fitz.Document:**
- Purpose: In-memory PDF representation
- Examples: `self.doc = fitz.open(filepath)`, `self.doc[page_i]`, `self.doc.save(path)`
- Pattern: Mutable object-oriented API; modifications are in-place

**OCRProvider (ABC):**
- Purpose: Abstract backend-agnostic OCR interface
- Examples: `ClaudeProvider`, `GeminiProvider`, `TesseractProvider`
- Pattern: Factory (`build_provider()` in `ocr.py`) → polymorphic dispatch to backend-specific `.ocr_image(b64_png, prompt)`

**PipelineState:**
- Purpose: Thread-safe coordination for multi-threaded OCR
- Examples: `state.record_success()`, `state.record_retryable_failure()`, `state.fatal_msg`
- Pattern: Lock-protected counters + condition variables (imitated via property checks in caller)

**Blob (FileBlob / MemBlob):**
- Purpose: Lazy-load undo page data from disk or memory
- Examples: `FileBlob(path)` for temp file, `MemBlob(bytes_data)` for small data
- Pattern: `data.load()` returns bytes; released via `data.release()`

**Undo Delta Dict:**
- Purpose: Compact representation of one operation's state change
- Examples: `{"op": "rotate", "data": [(page_i, angle), ...]}`, `{"op": "delete", "data": [(page_i, blob), ...]}`
- Pattern: Op-specific encoding reduces memory; Blob pointers stored inline

## Entry Points

**Main Entry Point (Command Line):**
- Location: `pagefolio.py` or `python -m pagefolio`
- Triggers: `python pagefolio.py` / `python -m pagefolio`
- Responsibilities: Import main, call `main()`

**Application Initialization:**
- Location: `pagefolio/__main__.py:main()`
- Triggers: Script entry
- Responsibilities: Create root Tk window, instantiate PDFEditorApp, setup file drop, enter mainloop

**PDFEditorApp.__init__:**
- Location: `pagefolio/app.py:138–290`
- Triggers: Mixin initialization via `super().__init__()` (Python MRO)
- Responsibilities: Load settings, apply theme, build UI, bind shortcuts, load plugins

**Menu/Dialog Entry Points:**
- Shortcuts (e.g., Ctrl+O) → Bound via `_bind_shortcuts()` to `self._cmd_map` functions
- Menu items (e.g., "Tools → Batch OCR") → `_open_batch_ocr()` → `BatchOCRDialog`
- Dialog buttons → Direct method calls on app instance

## Architectural Constraints

- **Threading:** UI runs on Tkinter main thread. Preview/thumbnail rendering queued via `root.after()` (chained callbacks); generation counters (`_preview_gen`, `_thumb_gen`) prevent stale renders overwriting newer ones. OCR uses `ThreadPoolExecutor` with workers calling into `PipelineState` (Lock-protected).
- **Global state:** `C` (theme dict) in `pagefolio/settings.py` and `_current_font_size` are module-level mutable singletons updated at runtime via `_apply_theme()` and `set_current_font_size()`.
- **Undo limit:** Hard-coded to `MAX_UNDO = 20` in `pagefolio/app.py`. Each entry stores operation delta dict; full PDF serialization is avoided.
- **Blob storage:** Undo stack holds Blob references (FileBlob/MemBlob). Lifecycle: capture on operation → push to stack → pop on undo/redo or evict → release temp file. Direct `append()`/`clear()` to `_undo_stack` bypasses cleanup and leaks files.
- **CropBox safety:** All crop operations must clamp CropBox inside page's MediaBox before calling `set_cropbox()` (see `_derotate_rect()` helper in `page_ops.py`).
- **PDF open/close:** `fitz.Document` must be closed on app exit or file close, else temp MMaps remain open (resource leak).
- **Pagination window:** Global `selected_pages` stays full-document indices; thumbnail window conversion happens only in view layer via `to_global()` / `window_for_page()` (pure functions).
- **Plugin isolation:** Plugin `on_*` hooks wrapped individually so one plugin error doesn't crash others. Hook implementations must handle their own exceptions.

## Anti-Patterns

### Direct Undo Stack Manipulation

**What happens:** Code calls `self._undo_stack.append()` or `.clear()` directly instead of `_push_evicting()` / `_clear_redo_stack()` / `_clear_undo_stacks()`.

**Why it's wrong:** FileBlob temp files never released; disk space leaks.

**Do this instead:** Use wrapper methods (`_push_evicting()`, `_clear_undo_stacks()`) that call `_dispose_state()` on evicted/cleared Blobs.

### Hardcoded Colors or Font Sizes

**What happens:** Code uses hex strings like `"#ff5733"` or `font=("Segoe UI", 12)` instead of theme dict `C` and `_font()` helper.

**Why it's wrong:** Theme switching breaks; inconsistent UX; font size changes don't propagate.

**Do this instead:** Reference `C["ACCENT"]` for colors, call `self._font(delta)` for fonts (base + delta pattern).

### Circular Imports via Settings

**What happens:** `ocr_providers/registry.py` imports from `pagefolio.settings` or UI modules.

**Why it's wrong:** Violates independent `registry.py` constraint (V180-ROBUST-02); settings.py → dialogs → registry → settings creates import cycle.

**Do this instead:** `registry.py` uses only `os` stdlib; reads env vars and class attributes only. Settings/UI logic stays in `ocr.py` (caller).

### Blocking Calls on Main Thread

**What happens:** OCR or network call runs synchronously in event handler without threading.

**Why it's wrong:** Freezes UI during network I/O; user can't cancel.

**Do this instead:** Spawn `ThreadPoolExecutor`, use `root.after()` for progress polling, store worker state in `PipelineState`.

## Error Handling

**Strategy:** User-visible errors via `messagebox.showerror()` or status bar; logged to stderr.

**Patterns:**
- **File I/O errors:** Catch `OSError` → show messagebox with filename and error reason
- **PDF parsing errors:** Catch `fitz.FileError` (corrupted PDFs, wrong format) → show "Invalid PDF"
- **OCR API errors:** Map provider exceptions (ConnectionError, TimeoutError, OCRAPIKeyError, OCRRetryableError) → show user message or retry UI
- **Plugin errors:** Individual hook try/except; error logged but doesn't stop other plugins
- **Password errors:** Catch `PDFPasswordError` → show "Password incorrect" and re-prompt

## Cross-Cutting Concerns

**Logging:** Root logger set to WARNING in `PDFEditorApp.__init__()`. Debug logs via `logger.debug()` (e.g., in `_bind_shortcuts`).

**Validation:** Input validation in pure functions (e.g., `parse_page_ranges()` in `page_ops.py`). UI field validation in dialog `ok_clicked()` handlers.

**Authentication:** PDF password handled in `_authenticate_doc()` (FileOpsMixin); prompts via `simpledialog.askstring()`. API keys stored in `self._session_api_keys` dict (not persisted to disk).

**Settings Persistence:** `_load_settings()` / `_save_settings()` in `settings.py`; JSON file `pagefolio_settings.json`. API keys excluded via `_SENSITIVE_KEYS` guard.

---

*Architecture analysis: 2026-07-22*
