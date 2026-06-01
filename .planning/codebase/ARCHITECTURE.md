<!-- refreshed: 2026-06-01 -->
# Architecture

**Analysis Date:** 2026-06-01

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Entry Points                                 │
│  `pagefolio.py` (script)  /  `pagefolio/__main__.py` (module)   │
└───────────────────────────────┬─────────────────────────────────┘
                                │ instantiates
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PDFEditorApp                                 │
│              `pagefolio/app.py`                                  │
│  (UIBuilderMixin + FileOpsMixin + PageOpsMixin +                 │
│   ViewerMixin + DnDMixin + OCRMixin)                             │
└──┬────────┬────────┬────────┬────────┬────────┬─────────────────┘
   │        │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼        ▼
UI Build  File     Page    Preview  Drag&Drop  OCR
Mixin     Ops      Ops     Render   Reorder    (LM Studio)
`ui_      `file_   `page_  `viewer  `dnd.py`   `ocr.py`
 builder`  ops`     ops`    .py`
                                ▲
                    ┌───────────┴──────────┐
                    │  Support Modules      │
                    │  `constants.py`       │
                    │  `settings.py`        │
                    │  `dialogs.py`         │
                    │  `plugins.py`         │
                    │  `file_drop.py`       │
                    │  `ocr_dialog.py`      │
                    └──────────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │  External            │
                    │  pymupdf (fitz)       │
                    │  Pillow (PIL)         │
                    │  tkinterdnd2          │
                    │  LM Studio HTTP API   │
                    └──────────────────────┘
```

## Design Patterns

**Mixin Composition:**
`PDFEditorApp` in `pagefolio/app.py` inherits from six Mixin classes simultaneously. Each Mixin owns a distinct slice of functionality. All Mixins share `self` state (the single `PDFEditorApp` instance).

```python
class PDFEditorApp(
    UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin, OCRMixin
):
```

**Observer / Event Hook (Plugin System):**
`PluginManager.fire_event(event_name, *args, **kwargs)` in `pagefolio/plugins.py` iterates all enabled plugins and calls the matching method. The app calls `fire_event` after each significant operation.

**Strategy (Theme):**
Theme colors are stored in `THEMES` dict in `pagefolio/constants.py`. At runtime `_apply_theme()` from `pagefolio/settings.py` updates the module-level `C` dict in-place so all code referencing `C["BG_DARK"]` etc. picks up the new theme without import changes.

**Command / Undo-Redo:**
`FileOpsMixin` (`pagefolio/file_ops.py`) maintains `self._undo_stack` / `self._redo_stack` (max 20 entries, `MAX_UNDO = 20`). Each undoable operation saves a `bytes` snapshot of the PDF via `fitz.Document.write()`.

## Core Components

| Component | Responsibility | File |
|-----------|----------------|------|
| `PDFEditorApp` | Root app class; wires all Mixins, holds all state, sets up keybindings | `pagefolio/app.py` |
| `UIBuilderMixin` | Builds ttk styles, PanedWindow layout, toolbar, thumbnail panel, preview canvas, right tool panel | `pagefolio/ui_builder.py` |
| `FileOpsMixin` | Open/Save/SaveAs/Undo/Redo; snapshot-based undo stack | `pagefolio/file_ops.py` |
| `PageOpsMixin` | Rotate, delete, crop (CropBox), insert, merge, split | `pagefolio/page_ops.py` |
| `ViewerMixin` | Render preview (fitz→PIL→Tk), thumbnails with cache, zoom, popup preview | `pagefolio/viewer.py` |
| `DnDMixin` | Thumbnail drag-and-drop reorder (single or multi-page) | `pagefolio/dnd.py` |
| `OCRMixin` | LM Studio Vision API integration; concurrent page OCR | `pagefolio/ocr.py` |
| `PluginManager` | Discover/load/unload/enable/disable plugins; fire lifecycle events | `pagefolio/plugins.py` |
| `PDFEditorPlugin` | Abstract base for third-party plugins | `pagefolio/plugins.py` |
| Constants & Theme | `THEMES`, `C` (runtime dict), `APP_VERSION`, `LANG`, `SUPPORTED_EXTENSIONS` | `pagefolio/constants.py` |
| Settings utils | Read/write `pagefolio_settings.json`, theme application, font helpers | `pagefolio/settings.py` |
| Dialogs | `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`, `MergeResizeDialog` | `pagefolio/dialogs.py` |
| OCR Dialog | `OCRDialog` — multi-page OCR results viewer/exporter | `pagefolio/ocr_dialog.py` |
| File Drop | tkinterdnd2 integration for drag-and-drop file open | `pagefolio/file_drop.py` |

## Data Flow

### File Open

1. User triggers open via menu/keyboard/file-drop → `FileOpsMixin._open_file()` (`pagefolio/file_ops.py`)
2. `fitz.open(path)` loads the PDF into `self.doc`
3. `self._refresh_all()` is called → triggers thumbnail generation and preview render
4. `PluginManager.fire_event("on_file_open", app, path)` notifies plugins

### Page Render (Preview)

1. `ViewerMixin._show_page()` (`pagefolio/viewer.py`) reads `self.current_page`
2. `fitz.Page.get_pixmap(matrix=fitz.Matrix(zoom * 1.5, zoom * 1.5))` renders to pixmap
3. Pixmap bytes → `PIL.Image` → `ImageTk.PhotoImage` stored on canvas
4. Background thread via generation counter (`self._preview_gen`) prevents stale renders

### Thumbnail Generation

1. `ViewerMixin._rebuild_thumbs()` iterates all pages
2. Each page rendered at `fitz.Matrix(0.22, 0.22)` scale
3. Results cached in `self.thumb_cache` dict keyed by page index
4. Background thread with `self._thumb_gen` counter guards against races

### Page Operation (example: rotate)

1. `PageOpsMixin._rotate_page()` (`pagefolio/page_ops.py`) called
2. Undo snapshot saved: `self._undo_stack.append(self.doc.write())`
3. `fitz.Page.set_rotation()` applied
4. `self._refresh_all()` redraws UI
5. `PluginManager.fire_event("on_page_rotate", ...)` fires

### OCR Flow

1. User opens OCR dialog → `OCRMixin` (`pagefolio/ocr.py`)
2. Target pages rendered at `DEFAULT_OCR_SCALE` (2.0×) via `page_to_png_b64()`
3. HTTP POST to LM Studio OpenAI-compatible endpoint (`http://localhost:1234`)
4. Concurrent requests via `ThreadPoolExecutor` up to `DEFAULT_OCR_CONCURRENCY` (2)
5. Results displayed in `OCRDialog` (`pagefolio/ocr_dialog.py`)

## State Management

All application state is held as attributes on the single `PDFEditorApp` instance (`self`):

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.doc` | `fitz.Document \| None` | Open PDF document |
| `self.filepath` | `str \| None` | Path of the open file |
| `self.current_page` | `int` | 0-based current page index |
| `self.selected_pages` | `set[int]` | Multi-selection set |
| `self._undo_stack` | `list[bytes]` | PDF snapshots (max 20) |
| `self._redo_stack` | `list[bytes]` | PDF snapshots for redo |
| `self.thumb_cache` | `dict[int, ImageTk.PhotoImage]` | Thumbnail image cache |
| `self._doc_buttons` | `list[ttk.Button]` | Buttons disabled when no doc |
| `self.crop_mode` | `bool` | Whether crop selection is active |
| `self.crop_rect` | `tuple \| None` | Current crop selection rect |
| `self.edit_mode` | `bool` | Edit vs View mode |
| `self.settings` | `dict` | Persisted settings from JSON |
| `self.font_size` | `int` | Base font size (8–16) |
| `self.plugin_manager` | `PluginManager` | Plugin lifecycle manager |
| `self._preview_gen` | `int` | Generation counter for preview thread |
| `self._thumb_gen` | `int` | Generation counter for thumbnail thread |

Settings are persisted to `pagefolio_settings.json` via `_save_settings()` from `pagefolio/settings.py`.

## Extension Points

### Plugin System

Plugins are `.py` files placed in the `plugins/` directory at the project root.

**To create a plugin:**
1. Create `plugins/myplugin.py`
2. Define a class inheriting `PDFEditorPlugin` from `pagefolio.plugins`
3. Override any lifecycle hooks needed

**Available hooks (all optional):**

| Hook | Signature | Trigger |
|------|-----------|---------|
| `on_load` | `(app)` | Plugin enabled/loaded |
| `on_unload` | `(app)` | Plugin disabled/unloaded |
| `on_file_open` | `(app, path)` | File opened |
| `on_file_save` | `(app, path)` | File saved |
| `on_page_rotate` | `(app, pages, degrees)` | Page rotated |
| `on_page_delete` | `(app, pages)` | Page deleted |
| `on_page_crop` | `(app, page_index)` | Page cropped |
| `on_page_change` | `(app, page_index)` | Current page changed |
| `on_insert` | `(app, paths, insert_at)` | Pages inserted |
| `on_merge` | `(app, paths)` | PDFs merged |
| `build_ui` | `(app, parent)` | Build custom UI in given `tk.Frame` |

**Plugin discovery:** `PluginManager.discover_plugins()` scans `plugins/*.py` (excluding `_`-prefixed files). Plugins are loaded at startup; enable/disable state is persisted in `settings["disabled_plugins"]`.

### Theme Extension

New themes can be added to the `THEMES` dict in `pagefolio/constants.py`. The `SettingsDialog` in `pagefolio/dialogs.py` dynamically reads `THEMES.keys()` to populate the theme selector.

## Architectural Constraints

- **Threading:** UI runs on the Tkinter main thread. Preview and thumbnail renders are dispatched to daemon threads; generation counters (`_preview_gen`, `_thumb_gen`) prevent stale results from overwriting newer ones. OCR uses `ThreadPoolExecutor`.
- **Global state:** `C` (theme dict) and `_current_font_size` in `pagefolio/settings.py` are module-level mutable singletons updated at runtime.
- **Undo limit:** Hard-coded to `MAX_UNDO = 20` snapshots in `pagefolio/app.py`. Each snapshot is a full PDF `bytes` serialization.
- **CropBox safety:** All crop operations must clamp the `CropBox` inside the page's `MediaBox` before calling `set_cropbox()` (`pagefolio/page_ops.py`).

## Anti-Patterns

### Accessing theme colors via raw strings instead of `C` dict

**What happens:** Code hardcodes color like `bg="#1a1a2e"` instead of `bg=C["BG_DARK"]`
**Why it's wrong:** Theme switching via `_apply_theme()` won't affect hardcoded colors
**Do this instead:** Always use `C["BG_DARK"]`, `C["ACCENT"]` etc. from `pagefolio/constants.py`

### Hardcoding font sizes

**What happens:** Code sets `font=("Helvetica", 10)` directly
**Why it's wrong:** User font size setting (`self.font_size`) is ignored
**Do this instead:** Use `self._font(delta)` helper (defined in `pagefolio/ui_builder.py`) where `delta` adjusts relative to base size

## Error Handling

**Strategy:** Explicit `except Exception as e:` blocks with `logger.exception()` or `logger.debug()`. Bare `except:` is forbidden by project convention.

**Patterns:**
- File operations use `messagebox.showerror()` for user-visible failures
- Plugin callbacks are individually wrapped so one plugin failure cannot crash others
- Background render threads silently discard results when generation counter has advanced

---

*Architecture analysis: 2026-06-01*
