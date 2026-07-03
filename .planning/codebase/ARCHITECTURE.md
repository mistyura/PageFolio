# Architecture

**Analysis Date:** 2026-06-10

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Entry Point                                  │
│      `pagefolio.py` → `pagefolio/__main__.py`                   │
│                   ↓ creates Tk root                             │
│              PDFEditorApp (Mixin aggregation)                    │
└──────────┬────────────────────────────────────┬──────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│   UI Builder Mixin       │      │ Plugin System            │
│ `ui_builder.py`          │      │ `plugins.py`             │
│ - Theme application      │      │ - Plugin discovery       │
│ - Layout construction     │      │ - Event lifecycle        │
│ - Canvas/widget setup     │      │ - OCR provider registry  │
└──────────────────────────┘      └──────────────────────────┘
           │
           ├─────────────────┬────────────────┬─────────────┬────────────────┐
           │                 │                │             │                │
           ▼                 ▼                ▼             ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │File Ops Mix  │ │Page Ops Mix   │ │Viewer Mix    │ │DnD Mix       │ │OCR Mix       │
    │`file_ops.py` │ │`page_ops.py`  │ │`viewer.py`   │ │`dnd.py`      │ │`ocr.py`      │
    │              │ │               │ │              │ │              │ │              │
    │- Open/Save   │ │- Rotate       │ │- Render      │ │- D&D reorder │ │- Provider    │
    │- Undo/Redo   │ │- Delete       │ │- Zoom        │ │- Multi-select│ │  builder     │
    │- Snapshots   │ │- Crop         │ │- Thumbnails  │ │- Indicators  │ │- Parallel    │
    │              │ │- Duplicate    │ │- Selection   │ │              │ │  execution   │
    │              │ │- Merge/Split  │ │- Popup view  │ │              │ │- Retry logic │
    └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
           │                                   │
           └───────────┬──────────────────────┘
                       ▼
            ┌──────────────────────┐
            │   Document State     │
            │  (fitz.Document)     │
            │  Snapshots (undo)    │
            │  Caches (thumbs)     │
            └──────────────────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  PDF I/O │ │ Settings │ │ Dialogs  │
    │ `fitz`   │ │`settings.py` │ `dialogs/` │
    │ file ops │ │+ themes  │ │- About   │
    │          │ │+ lang    │ │- Settings│
    └──────────┘ └──────────┘ │- Plugin  │
                              │- Merge   │
                              │- LLM Cfg │
                              │- OCR Dlg │
                              └──────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `PDFEditorApp` | Root class; mixin aggregation; state holder; event dispatch; settings lifecycle | `pagefolio/app.py` |
| `UIBuilderMixin` | Theme configuration; ttk style setup; layout construction (paned, canvas, frames) | `pagefolio/ui_builder.py` |
| `FileOpsMixin` | File open/save/saveas; undo/redo stacks; op 別デルタ + Blob ライフサイクル管理 | `pagefolio/file_ops.py` |
| `PageOpsMixin` | Page rotation, deletion, cropping (CropBox), duplication, merge, split | `pagefolio/page_ops.py` |
| `ViewerMixin` | Preview rendering (fitz→PIL→Tk); zoom; thumbnail generation & cache; selection UI | `pagefolio/viewer.py` |
| `DnDMixin` | Thumbnail drag-and-drop reordering; ghost images; drop indicators | `pagefolio/dnd.py` |
| `OCRMixin` | Provider instantiation; concurrent OCR execution; retry/timeout logic | `pagefolio/ocr.py` |
| `PluginManager` | Plugin discovery, loading, event firing, OCR provider registration | `pagefolio/plugins.py` |
| `OCRProvider` (ABC) | Abstract base for OCR backends (LMStudio, Claude, Gemini, Tesseract) | `pagefolio/ocr_providers.py` |
| Dialogs | Modal windows for settings, about, plugin management, OCR config, merge, split | `pagefolio/dialogs/` |
| Constants | APP_VERSION, SUPPORTED_EXTENSIONS, PLUGINS_DIR | `pagefolio/constants.py` |
| Themes & Lang | Color palette (THEMES, C dict), localization (LANG ja/en) | `pagefolio/themes.py`, `pagefolio/lang.py` |
| Settings Utils | JSON I/O, theme application, font generation, API key filtering | `pagefolio/settings.py` |

## Pattern Overview

**Overall:** Mixin-based vertical slicing with plugin architecture for extensibility.

**Key Characteristics:**
- **Mixin inheritance model**: `PDFEditorApp` aggregates 6 functional mixins (UI, file, page, viewer, D&D, OCR) avoiding deep hierarchy
- **State centralization**: All mutable state lives in `PDFEditorApp` instance; methods operate on `self.*` attributes
- **Delta-based undo**: op 別逆デルタ（rotate=回転値 / crop=cropbox / delete・page_edit=ページ単位 bytes 等）を `deque(maxlen=20)` に保持。64KiB 以上のページ bytes は `UndoBlobStore`（`undo_store.py`）で tempfile へ退避しメモリから解放（v1.7.0）
- **Background rendering**: Preview and thumbnail generation dispatched to daemon threads; generation counters prevent stale updates
- **Plugin hooks**: 10+ event callbacks fire on document/page operations for extensibility
- **Two-layer dialog system**: Base dialogs in `pagefolio/dialogs/`, specialized OCR in `ocr_dialog.py`
- **Provider abstraction**: OCR backends pluggable via `OCRProvider` ABC; currently LMStudio, Claude, Gemini, Tesseract
- **Settings isolation**: API keys guarded via `_SENSITIVE_KEYS` set; never persisted to JSON (D-01)

## Layers

**Entry/Runtime Layer:**
- Purpose: Initialize Tkinter, load settings, create PDFEditorApp, set up file D&D
- Location: `pagefolio.py`, `pagefolio/__main__.py`
- Contains: Tk root creation, app instantiation
- Depends on: PDFEditorApp, TkinterDnD
- Used by: User (Python interpreter)

**Application Core Layer:**
- Purpose: Hold state, coordinate mixins, manage lifecycle
- Location: `pagefolio/app.py`
- Contains: PDFEditorApp class; `__init__`, keybindings, utility methods
- Depends on: All 6 mixins, PluginManager, settings module, dialogs
- Used by: UI/Runtime layer; tested by all test modules

**Functional Mixins Layer (Horizontal Slicing):**
- Purpose: Encapsulate feature families without coupling to app hierarchy
- Location: `pagefolio/ui_builder.py`, `file_ops.py`, `page_ops.py`, `viewer.py`, `dnd.py`, `ocr.py`
- Contains: Methods organized by responsibility
- Depends on: Constants, settings, themes, fitz, PIL, Tkinter
- Used by: PDFEditorApp (all 6 mixed in)

**OCR Abstraction Layer:**
- Purpose: Isolate provider implementations; coordinate parallel execution
- Location: `pagefolio/ocr.py`, `ocr_providers.py`, `ocr_dialog.py`
- Contains: Provider ABC, concrete implementations (LMStudio, Claude, Gemini, Tesseract), execution helpers
- Depends on: fitz, PIL, requests, anthropic SDK (Claude), google SDK (Gemini)
- Used by: OCRMixin (async execution), OCRDialog (UI progress)

**Plugin System Layer:**
- Purpose: Discover, load, manage third-party plugins; register OCR providers
- Location: `pagefolio/plugins.py`
- Contains: PDFEditorPlugin ABC, PluginManager
- Depends on: importlib, logging
- Used by: PDFEditorApp (lifecycle), dialogs (plugin UI)

**UI Dialogs Layer:**
- Purpose: Modal interactions for settings, about, file operations, OCR config
- Location: `pagefolio/dialogs/` (about.py, settings.py, plugin.py, merge.py, llm_config.py), `ocr_dialog.py`
- Contains: Tk.Toplevel subclasses with form/button interactions
- Depends on: Constants, themes, lang, settings
- Used by: FileOpsMixin (save-as, merge), PageOpsMixin (crop, split), OCRMixin (config)

**Storage & Configuration Layer:**
- Purpose: Persist settings, manage themes/language, format help
- Location: `pagefolio/constants.py`, `themes.py`, `lang.py`, `settings.py`
- Contains: Constant definitions, JSON I/O, theme color dicts
- Depends on: json, os
- Used by: All layers (config lookup)

## Data Flow

### Primary Request Path (File Open → Display)

1. User clicks "ファイルを開く" button in toolbar → `FileOpsMixin._open_file()` (`file_ops.py`)
2. `filedialog.askopenfilename()` → user selects PDF
3. `fitz.open(filepath)` opens document → `self.doc = <fitz.Document>`
4. Save undo snapshot (if previous doc exists) → `self._save_undo("open")`
5. Reset page state: `self.current_page = 0`, `self.selected_pages.clear()`
6. Refresh all views → `self._refresh_all()` calls:
   - `_show_preview()` (ViewerMixin): renders current page
   - `_show_thumbnails()` (ViewerMixin): generates all page thumbnails in background thread
7. Update button states → `_update_doc_buttons_state()`: enable doc-dependent buttons
8. Fire plugin event → `plugin_manager.fire_event("on_file_open", self, filepath)`
9. Display status → `_set_status("ファイルを開きました")`

### Page Operation Path (Example: Rotate)

1. User clicks "↻ 右90°" button → `PageOpsMixin._rotate_selected(90)`
2. Get affected pages → `self._get_targets()` (current or selected)
3. Save undo state → `_save_undo("rotate", targets=targets)` captures rotation before change
4. Mutate PDF → `for i in targets: doc[i].set_rotation(...)`
5. Invalidate caches → `_invalidate_thumb_cache(targets)` clears affected thumbnails
6. Refresh all → `_refresh_all()` re-renders preview + thumbnails
7. Fire event → `plugin_manager.fire_event("on_page_rotate", self, targets, deg)`
8. Status → `_set_status(f"回転しました: {len(targets)} ページ 90°")`

### Undo/Redo Path

1. User presses Ctrl+Z → `PDFEditorApp._undo()`
2. Pop state from `self._undo_stack` → `state = self._undo_stack.pop()`
3. Restore state → `_restore_state(state)` reverses operation:
   - "rotate": re-apply saved rotation list
   - "delete": re-insert saved page bytes
   - "crop": restore saved CropBox coordinates
4. Push inverse to redo → `self._redo_stack.append(inverse_state)`
5. Refresh UI → `_refresh_all()`

**State Management:**
- `self.doc`: Current `fitz.Document` (None if no file open)
- `self.current_page`: 0-based page index
- `self.selected_pages`: `set` of page indices for multi-select
- `self._undo_stack`: `deque(maxlen=MAX_UNDO=20)` of state dicts
- `self.crop_rect`: Current crop selection rect `(x0, y0, x1, y1)` or None
- `self.thumb_cache`: `{page_idx: ImageTk.PhotoImage}`
- `self._preview_gen`: Generation counter to discard stale preview renders
- `self._thumb_gen`: Generation counter to discard stale thumbnail renders

### OCR Execution Flow

1. User configures OCR in settings → selects provider (LMStudio/Claude/Gemini), inputs API key if needed
2. User clicks "🔍 OCR (選択ページ)" → `OCRMixin._do_ocr_selected()`
3. Launch OCRDialog → `OCRDialog(parent, app, doc, page_indices, ...)`
4. Dialog thread calls `run_parallel(provider, pages, ...)` → `ocr.py`
5. `run_parallel()` creates ThreadPoolExecutor with `ocr_concurrency` workers
6. Each page → `provider.ocr(page_idx)` in worker thread:
   - Render page to PNG bytes on main thread (thread-safe via `_render_preview_pixmap`)
   - Send base64 image + prompt to provider API (LMStudio HTTP, Claude/Gemini SDK)
   - Parse text response
   - Retry on rate-limit with clamped `Retry-After` (max 60s, checked every 0.5s)
7. Dialog UI updates progress bar and result accumulator
8. User can "エクスポート" results to text file
9. Dialog closes on cancel or completion

## Key Abstractions

**Document State Snapshot:**
- Purpose: Enable undo/redo without keeping multiple `fitz.Document` instances
- Examples: `file_ops.py` lines 23–62
- Pattern: Serialize complete PDF to `bytes` before operation; store operation type + metadata in dict

**Theme Dictionary (C):**
- Purpose: Runtime-mutable color palette for dark/light theme switching
- Examples: `themes.py` (THEMES definition), `settings.py` (_apply_theme)
- Pattern: Module-level `C = dict(THEMES["dark"])` updated by `_apply_theme()`; all UI colors reference `C["KEY"]`

**OCR Provider ABC:**
- Purpose: Standardize interface for different backends
- Examples: `ocr_providers.py` (LMStudioProvider, ClaudeProvider, GeminiProvider, TesseractProvider)
- Pattern: `OCRProvider` base class with `async ocr(provider_config, page_bytes) -> str`; subclasses implement HTTP/SDK calls

**Plugin Event Hook System:**
- Purpose: Allow third-party extensions without modifying core
- Examples: `plugins.py` (PDFEditorPlugin.on_page_rotate), `app.py` (fire_event calls)
- Pattern: Plugin subclasses override hook methods; PluginManager.fire_event wraps each call to catch exceptions

**Mixin Aggregation Pattern:**
- Purpose: Organize large class without deep inheritance
- Examples: `app.py` class definition line 32–34
- Pattern: PDFEditorApp inherits 6 mixins; each mixin adds methods without state conflicts

## Entry Points

**Python Script Execution:**
- Location: `pagefolio.py`
- Triggers: `python pagefolio.py`
- Responsibilities: Import and call `pagefolio.__main__.main()`

**Python Module Execution:**
- Location: `pagefolio/__main__.py`
- Triggers: `python -m pagefolio`
- Responsibilities: Initialize Tk root (with TkinterDnD if available), create PDFEditorApp, setup file D&D, run mainloop

**Programmatic API:**
- Location: `pagefolio/__init__.py` (re-exports)
- Usage: `from pagefolio import PDFEditorApp, PDFEditorPlugin, PluginManager`
- Responsibilities: Expose public API for plugins and external use

## Architectural Constraints

- **Threading:** Tkinter main thread only. Preview/thumbnail renders spawn daemon threads; generation counters (`_preview_gen`, `_thumb_gen`) prevent stale overwrites. OCR uses `ThreadPoolExecutor` for provider calls.
- **Global state:** Module-level `C` (theme dict) and `_current_font_size` in `pagefolio/settings.py` are mutable singletons. Updated at startup and when theme/font changes.
- **Undo limit:** Hard-coded `MAX_UNDO = 20` in `app.py`. 各エントリは op 別デルタ（full PDF シリアライズではない）。ページ bytes を持つデルタ（delete/page_edit/insert 系/merge 系/merge_resize）は `_capture_page_blob` 経由で Blob 化され、64KiB 以上は `pagefolio_undo_` 一時ディレクトリへ退避。deque 溢れ・redo クリア・消費時に `_dispose_state` で解放、ファイルクローズ/終了時に `_clear_undo_stacks` が purge、atexit でも回収（v1.7.0）。
- **CropBox safety:** All crop operations must clamp CropBox inside page's MediaBox before calling `set_cropbox()` (`page_ops.py` line ~130).
- **API key isolation:** Settings file never contains API keys (guarded by `_SENSITIVE_KEYS` in `settings.py`). Keys resolved from environment vars or session dict `self._session_api_keys`.
- **No file locking:** `fitz.Document` read-only after open; modifications staged in memory and written on save.

## Anti-Patterns

### Accessing Theme Colors via Raw Hex Strings

**What happens:** Some older code might use `bg="#e94560"` instead of `bg=C["ACCENT"]`

**Why it's wrong:** Theme switching updates `C` dict but not hardcoded hex strings; dark→light transition breaks UI colors in affected widgets

**Do this instead:** Always use `C["KEY"]` for color access; ensure all widget creation code uses `from pagefolio.constants import C` and references `C["BG_DARK"]`, `C["TEXT_MAIN"]`, etc.

### Directly Mutating `self.doc` Without Undo Snapshot

**What happens:** Code like `self.doc.delete_page(i)` without preceding `self._save_undo("delete", ...)`

**Why it's wrong:** Undo stack won't have state before operation; user presses Ctrl+Z and nothing happens

**Do this instead:** Always call `self._save_undo(op_type, ...)` before modifying `self.doc`, passing operation type and relevant metadata (targets, old values, etc.)

### Holding PDF Snapshots as `fitz.Document` Instead of `bytes`

**What happens:** Storing `fitz.Document` instances in undo stack

**Why it's wrong:** Multiple open documents consume memory and can cause file locking issues; fitz documents aren't safely serializable across threads

**Do this instead:** ページ単位のキャプチャは必ず `_capture_page_blob(page_i)` を使う（Blob 化・64KiB 以上はディスク退避）。復元は `fitz.open(stream=self._blob_bytes(data))`。`self.doc.tobytes()` の全体シリアライズを undo スタックへ入れてはならない。

### Starting Background Threads Without Generation Counter

**What happens:** Preview render started without incrementing `self._preview_gen`; new render started; old render finishes and overwrites new result

**Why it's wrong:** UI shows wrong page or outdated thumbnail when user clicks rapidly

**Do this instead:** Increment generation counter before thread dispatch; pass counter as thread arg; check counter in completion callback before updating UI

### Forgetting to Reset `self.selected_pages` on Destructive Operations

**What happens:** Delete page 5; selection still contains 5; next click on page 6 treats it as index 5

**Why it's wrong:** Multi-page operations operate on stale selection; corrupts subsequent edits

**Do this instead:** Clear or adjust `self.selected_pages` after operations that change page count (delete, merge); update `current_page` if needed

## Error Handling

**Strategy:** Graceful degradation with user-visible feedback via `messagebox`.

**Patterns:**
- File I/O: Wrap in `try/except Exception`; show error dialog with filename and error message
- Plugin callbacks: Each hook call wrapped individually; plugin exception logged but doesn't stop other plugins
- Background renders (preview/thumbnails): Exceptions logged; UI shows placeholder text or last good render
- OCR retries: Retry on rate-limit (429) with exponential backoff + Retry-After cap; show user "Retrying..." status
- PDF operations: Validate before mutate (e.g., check page count before delete all); show warning if operation would destroy file

## Cross-Cutting Concerns

**Logging:** All modules use `logging.getLogger(__name__)`; basicConfig set in `app.py.__init__` to WARNING level. Debug logs use `logger.debug(...)` for non-critical info.

**Validation:** File operations call `_check_doc()` to confirm PDF open. Page operations call `_get_targets()` to resolve multi-select. Crop operations clamp coordinates to MediaBox.

**Authentication:** API keys resolved in `ocr.py._resolve_api_key()` from environment vars first, then session dict. Never stored in settings JSON.

**Internationalization:** All UI strings via `LANG[self.lang]` dict lookup. Two languages: ja / en. Entry in LANG must exist in both keys to keep left-right parity.

---

*Architecture analysis: 2026-06-10*
