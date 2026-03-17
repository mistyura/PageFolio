# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Monolithic MVC-inspired single-file GUI application with plugin system

**Key Characteristics:**
- Single-file structure (`pagefolio.py`) with all UI, logic, and plugin infrastructure
- Event-driven architecture (keyboard shortcuts, mouse events, button clicks)
- Pub/sub plugin event system for extending functionality without modifying core
- Theme-based color management through global configuration dictionary
- Undo/Redo stack pattern with state serialization (max 20 operations)

## Layers

**UI Layer:**
- Purpose: Tkinter widget construction, layout, and styling
- Location: `pagefolio.py` - Methods prefixed `_build_*`, `_show_*`, style configuration (lines 668-850+)
- Contains: Frame hierarchy, Canvas-based controls, label updates, theme application
- Depends on: Theme engine (C dictionary), Font system, Language system
- Used by: User interactions, data display updates

**Business Logic Layer:**
- Purpose: PDF document manipulation, page operations, state management
- Location: `pagefolio.py` - Methods like `_open_file`, `_save_file`, `_rotate_selected`, `_delete_selected`, `_crop_page`, `_dnd_drop` (lines 1038-1820+)
- Contains: File I/O via `fitz.Document`, page transformations, selection tracking, Undo/Redo state
- Depends on: PDF library (pymupdf/fitz), UI layer for display updates
- Used by: Event handlers, plugin callbacks

**Data Layer:**
- Purpose: Document state, page metadata, user selections, settings persistence
- Location: `pagefolio.py` - Instance variables in `PDFEditorApp.__init__` (lines 610-646)
- Contains: `self.doc` (fitz.Document), `self.current_page` (int), `self.selected_pages` (set), `self.filepath` (str), cache structures
- Depends on: None (read/written by logic layer)
- Used by: All layers read/modify state

**Plugin System:**
- Purpose: Runtime extension mechanism for adding custom functionality
- Location: `pagefolio.py` - `PluginManager` class (lines 483-605) and `PDFEditorPlugin` base class (lines 431-480)
- Contains: Plugin discovery, loading, event dispatching, lifecycle management
- Depends on: Core app hooks, theme/font/language systems
- Used by: PDFEditorApp to fire events on key operations

**Theme & Configuration Layer:**
- Purpose: Centralized color management, font sizing, language localization, settings persistence
- Location: `pagefolio.py` - Global `THEMES` dict (lines 22-59), `LANG` dict (lines 61-355), functions `_apply_theme`, `_load_settings`, `_save_settings` (lines 359-398)
- Contains: Theme definitions, language strings, font size calculations
- Depends on: JSON I/O, Windows registry for system theme detection
- Used by: All UI components, dialogs, plugins

## Data Flow

**File Open Flow:**

1. User clicks "Open File" button or presses Ctrl+O → `_open_file()` triggered
2. File picker dialog opens (native Windows dialog)
3. User selects PDF path(s)
4. If multiple PDFs: `MergeOrderDialog` opens for user to confirm merge order
5. `_do_open_merged()` or `_open_pdf_path()` called with confirmed path(s)
6. `fitz.Document` created from PDF bytes
7. `self.doc` assigned; `self.filepath` updated; `self.current_page = 0`
8. `_save_undo()` called to create checkpoint
9. `_refresh_all()` called → `_build_thumbnails()` + `_show_preview()`
10. Thumbnails rendered at 0.22x scale, cached in `self.thumb_cache`
11. Page 0 rendered in preview at zoom scale 1.5x
12. Button states updated (`_update_doc_buttons_state()`)
13. Plugin event fired: `on_file_open(app, path)`
14. Status message displayed via `_set_status()`

**Page Modification Flow (Example: Rotation):**

1. User selects pages in thumbnail panel (multi-select via Ctrl/Shift) or single page auto-selected
2. User clicks rotation button (90°/180°/270°)
3. `_rotate_selected(deg)` called
4. `_save_undo()` creates state checkpoint before modification
5. For each selected page: `page.set_rotation(deg)` applied in fitz
6. `_refresh_all()` called to redraw
7. Plugin event fired: `on_page_rotate(app, [page_indices], degrees)`
8. Status message shows: "Rotated N page(s) by DEG°"
9. `_redo_stack.clear()` to invalidate future

**Undo/Redo Flow:**

1. Before any destructive operation, `_save_undo()` called
2. `_get_state()` serializes: `doc` byte content, `current_page`, `selected_pages`, `filepath`, `current_zoom`
3. Tuple pushed to `_undo_stack` (LIFO); if stack > MAX_UNDO, pop oldest
4. `_redo_stack.clear()` to prevent branching
5. User presses Ctrl+Z → `_undo()` called
6. Current state pushed to `_redo_stack`
7. Old state popped from `_undo_stack`
8. `_restore_state(state)` reconstructs: `self.doc`, `self.current_page`, selections
9. `_refresh_all()` redraws
10. User presses Ctrl+Y → `_redo()` reverses the flow

**Crop Flow:**

1. User toggles crop mode ON → button visual changes, hint displayed
2. User drags rectangle on preview canvas → `_crop_drag_start/move/end` events fire
3. Drag coordinates captured as `self.crop_rect` (fitz.Rect)
4. Red overlay drawn on canvas showing selection
5. User clicks "Crop to Selection" button → `_crop_page()` called
6. Coordinates scaled from preview space (zoom 1.5x) back to PDF points
7. Rect clamped to MediaBox to prevent out-of-bounds
8. `page.set_cropbox(cropped_rect)` applied
9. `_refresh_all()` redraws
10. Plugin event fired: `on_page_crop(app, page_index)`
11. Crop overlay cleared; crop mode toggled OFF

**Drag & Drop Page Reorder Flow:**

1. User clicks thumbnail frame → `_dnd_start_ghost()` called
2. Ghost copy created at mouse position with opacity
3. User drags → `_dnd_move_ghost()` updates ghost position
4. Drop indicator line drawn at insertion point via `_dnd_show_indicator()`
5. User releases → `_dnd_drop()` called
6. Destination index computed from event coordinates
7. `fitz.Document.move_page(src, dest)` reorders pages
8. `self.selected_pages` updated; `current_page` adjusted if needed
9. `_refresh_all()` redraws
10. Status message shows: "p.X → p.Y moved"
11. Plugin event fired: `on_page_reorder(app, src, dest)` if applicable

**State Management:**

- `self.doc` — fitz.Document instance or None (NULL when no file open)
- `self.current_page` — 0-indexed page number; updated when user navigates/modifies
- `self.selected_pages` — set of 0-indexed page numbers; cleared on file open
- `self.filepath` — absolute path to currently open PDF (None if not saved)
- `self.thumb_cache` — dict mapping `(doc_id, page_idx)` to PhotoImage for fast redraw
- `self._undo_stack` / `self._redo_stack` — LIFO stacks of serialized states
- `self.settings` — dict with "theme", "font_size", "lang", "disabled_plugins"
- `self.crop_rect` — fitz.Rect of user-selected crop area (None when not in crop mode)

## Key Abstractions

**PDFEditorApp:**
- Purpose: Central coordinator managing document, UI, and operations
- Examples: `pagefolio.py` lines 607-1930
- Pattern: Monolithic controller with 50+ methods, each handling a specific user action or internal update

**PluginManager:**
- Purpose: Discovers, loads, and manages plugin Python modules
- Examples: `pagefolio.py` lines 483-605; `plugins/page_info.py` lines 14-69
- Pattern: Plugin manager with hooks system; plugins inherit from `PDFEditorPlugin` base class and override event callbacks (`on_file_open`, `on_page_change`, `on_page_rotate`, etc.)

**PDFEditorPlugin (Base Class):**
- Purpose: Interface contract for plugins
- Examples: `pagefolio.py` lines 431-480
- Pattern: Abstract base defining lifecycle (`build_ui`) and event handlers (`on_*` methods)

**Dialog Classes:**
- Purpose: Modal windows for specific workflows
- Examples:
  - `SettingsDialog` (lines 1980-2074) — Theme/font configuration
  - `MergeOrderDialog` (lines 2230-2397) — Confirm/reorder multiple PDF merge
  - `PluginDialog` (lines 2074-2228) — Plugin management interface
  - `AboutDialog` (lines 1932-1980) — About/version info
- Pattern: Tkinter `tk.Toplevel` subclasses with callback patterns; e.g., `MergeOrderDialog` accepts `callback(ordered_paths)` in constructor

**Theme System:**
- Purpose: Centralized color palette management across all UI
- Examples: `THEMES` global dict with "dark" and "light" profiles
- Pattern: Two-level lookup — `THEMES["dark"]["BG_DARK"]` or via global `C` dict that's updated at runtime by `_apply_theme()`

**Language System:**
- Purpose: Internationalization (i18n) for UI strings
- Examples: `LANG["ja"]` and `LANG["en"]` dicts with 100+ keys
- Pattern: Single `_t(key)` helper method for lookups; fallback to Japanese if key missing

## Entry Points

**Application Startup:**
- Location: Lines 2380-2397 (main entry)
- Triggers: `python pagefolio.py` execution
- Responsibilities: Create Tk root, instantiate `PDFEditorApp`, start event loop with `root.mainloop()`

**File → Save:**
- Location: `_save_file()` method (line 1098)
- Triggers: Ctrl+S or "Save" button
- Responsibilities: Validate doc exists, prompt overwrite confirmation, write bytes to disk via `doc.write()`, update `filepath`, status display

**Thumbnail Click:**
- Location: `_single_click()` method (line 1547) → `_show_preview()` (line 1415)
- Triggers: Single mouse click on thumbnail
- Responsibilities: Set `current_page`, update selection state, redraw preview

**Keyboard Shortcut:**
- Location: `self.root.bind()` calls (lines 654-665)
- Triggers: Ctrl+O, Ctrl+S, Ctrl+Z, Ctrl+Y, Delete key press
- Responsibilities: Route to corresponding method (_open_file, _save_file, _undo, _redo, _delete_selected)

## Error Handling

**Strategy:** Try-catch with user-facing messagebox dialogs; logs via `traceback.print_exc()` to console

**Patterns:**

**File I/O Errors:**
```python
# Example: _save_file (line 1098)
try:
    # ... file operations
except Exception as e:
    messagebox.showerror(self._t("err_save_title"),
                         self._t("err_save_msg").format(e=e))
```

**PDF Operations (Crop, Rotate, Delete):**
```python
# Example: _crop_page (line 1267)
try:
    # ... pdf manipulation
except Exception as e:
    messagebox.showerror(self._t("err_crop_title"),
                         self._t("err_crop_msg").format(e=e))
```

**Plugin Loading (Graceful Fallback):**
```python
# PluginManager.load_all (line 545+)
try:
    # Load plugin module
except Exception:
    traceback.print_exc()
    # Continue with remaining plugins
```

**Validation Before Operations:**
```python
# Example: _rotate_selected (line 1144)
if not self._check_doc():
    return
# _check_doc shows messagebox if doc is None
```

## Cross-Cutting Concerns

**Logging:** Console output via `print()` and `traceback.print_exc()` on errors; no persistent log file

**Validation:**
- Document check: `_check_doc()` (line 1820) — ensures `self.doc` exists before operation
- Page selection: `_get_targets()` (line 1826) — uses selected pages or defaults to current page
- Coordinate bounds: CropBox clamped to MediaBox before applying via `set_cropbox()`

**Authentication:** None (single-user local application)

**State Consistency:**
- Undo/Redo stack depth capped at `MAX_UNDO = 20` (line 608)
- Thumbnail cache invalidated after modifications
- Plugin event fired after state changes for synchronization

---

*Architecture analysis: 2026-03-17*
