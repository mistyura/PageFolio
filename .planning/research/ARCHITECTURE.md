# Architecture Research

**Domain:** Single-file Tkinter PDF editor (Windows desktop GUI)
**Researched:** 2026-03-18
**Confidence:** HIGH (responsive layout, PyInstaller) / MEDIUM (windnd encoding edge cases)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        pagefolio.py (single file)                    │
├──────────────────────────────────────────────────────────────────────┤
│  GLOBAL LAYER (constants, no runtime state)                          │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐                    │
│  │  THEMES  │  │   LANG   │  │  helper fns      │                    │
│  │  (dict)  │  │  (dict)  │  │  _load_settings  │                    │
│  └──────────┘  └──────────┘  └─────────────────┘                    │
├──────────────────────────────────────────────────────────────────────┤
│  PLUGIN LAYER (extensible, isolated from core)                       │
│  ┌────────────────────┐   ┌───────────────────────────────────┐      │
│  │  PDFEditorPlugin   │   │  PluginManager                    │      │
│  │  (base class)      │◄──│  scan / load / fire_event         │      │
│  └────────────────────┘   └───────────────────────────────────┘      │
├──────────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER (PDFEditorApp)                                    │
│  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │  UI / Layout   │  │  Business Logic  │  │  State (self.doc,  │   │
│  │  _build_*      │  │  _open/save/crop │  │  current_page,     │   │
│  │  _show_*       │  │  _rotate/delete  │  │  selected_pages,   │   │
│  │  _refresh_*    │  │  _dnd_*          │  │  undo/redo stacks) │   │
│  └────────┬───────┘  └────────┬─────────┘  └────────────────────┘   │
│           │                   │                                      │
│           └───────── _refresh_all() ──────────────────────────────── │
├──────────────────────────────────────────────────────────────────────┤
│  DIALOG LAYER (Toplevel modal windows)                               │
│  ┌──────────────┐  ┌───────────────────┐  ┌────────────────┐        │
│  │SettingsDialog│  │  MergeOrderDialog │  │  PluginDialog  │        │
│  └──────────────┘  └───────────────────┘  └────────────────┘        │
├──────────────────────────────────────────────────────────────────────┤
│  EXTERNAL DEPENDENCIES                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ pymupdf  │  │  Pillow  │  │  windnd  │  │  winreg  │            │
│  │  (fitz)  │  │  (PIL)   │  │  (D&D)   │  │ (theme)  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Global constants | Themes, strings, settings I/O — no mutable state | Module-level dicts and pure functions |
| PDFEditorApp | Central controller: UI construction, event routing, state mutation | Monolithic class, 50+ `_` prefixed methods |
| PluginManager | Plugin discovery, lifecycle, event dispatch | Separate class instantiated inside PDFEditorApp |
| PDFEditorPlugin | Interface contract for extensions | Base class with no-op event methods |
| Dialog classes | Modal workflows (settings, merge order) with callback return | `tk.Toplevel` subclass, callback pattern |
| windnd integration | OS-level file drop registration | Single `hook_dropfiles(widget, func)` call |
| PyInstaller build | Package Python + all deps into distributable folder | `.spec` file, `--onedir --noconsole` |

## Recommended Project Structure

The single-file constraint is non-negotiable. Within `pagefolio.py`, organize with clear section headers to maintain navigability at ~2,500+ lines:

```
pagefolio.py
├── [SECTION 1] Imports
├── [SECTION 2] Constants — THEMES, LANG, MAX_UNDO, SETTINGS_FILE
├── [SECTION 3] Settings helpers — _get_settings_path, _load_settings,
│               _save_settings, _detect_system_theme, _apply_theme
├── [SECTION 4] Plugin base — PDFEditorPlugin (abstract base class)
├── [SECTION 5] Plugin manager — PluginManager
├── [SECTION 6] PDFEditorApp
│   ├── __init__ (state initialization, bindings)
│   ├── --- UI BUILD ---
│   ├── _build_styles, _build_ui, _build_thumb_panel,
│   │   _build_preview, _build_tools_scrollable, _build_tools
│   ├── --- FILE OPS ---
│   ├── _open_file, _open_multiple_pdfs, _do_open_merged,
│   │   _open_pdf_path, _save_file, _save_as, _quit
│   ├── --- PAGE OPS ---
│   ├── _rotate_selected, _delete_selected
│   ├── --- CROP ---
│   ├── _toggle_crop_mode, _crop_drag_*, _crop_page, _crop_reset
│   ├── --- INSERT / MERGE ---
│   ├── _insert_from_file, _do_insert, _merge_pdf, _do_merge
│   ├── --- DRAG & DROP (file open via OS drop) ---  <-- NEW
│   ├── _on_files_dropped (windnd callback)
│   ├── --- DND PAGE REORDER ---
│   ├── _dnd_start_ghost, _dnd_move_ghost, _dnd_drop,
│   │   _dnd_show_indicator, _dnd_dest_index, _dnd_destroy_ghost
│   ├── --- DISPLAY ---
│   ├── _refresh_all, _build_thumbnails, _add_thumb, _show_preview
│   ├── --- RESPONSIVE LAYOUT ---  <-- NEW
│   ├── _on_window_resize, _update_pane_proportions
│   ├── --- NAVIGATION ---
│   ├── _prev_page, _next_page, _zoom
│   ├── --- UNDO / REDO ---
│   ├── _save_undo, _undo, _redo, _restore_state, _get_state
│   ├── --- UTILITIES ---
│   └── _check_doc, _get_targets, _update_doc_buttons_state,
│       _set_status, _font, _t, _invalidate_thumb_cache,
│       _get_thumb_photo, _open_settings, _apply_settings, _rebuild_ui
├── [SECTION 7] Dialog classes
│   ├── AboutDialog
│   ├── SettingsDialog
│   ├── PluginDialog
│   └── MergeOrderDialog
└── [SECTION 8] Entry point — if __name__ == "__main__"
```

### Structure Rationale

- **Section headers as `# ===` banners:** Replace ad-hoc organization with explicit sections. Editors that fold on `#` comments gain instant navigation.
- **New sections for new capabilities:** `--- DRAG & DROP (file open) ---` and `--- RESPONSIVE LAYOUT ---` are separate from existing DND-page-reorder and existing `_build_*` methods to avoid confusion.
- **Entry point at bottom:** `if __name__ == "__main__"` must remain last to avoid forward-reference issues with class definitions above it.

## Architectural Patterns

### Pattern 1: Responsive Layout via ttk.PanedWindow + Configure Binding

**What:** Replace fixed-width frames with a `ttk.PanedWindow` (horizontal orient) that splits thumbnail panel | preview | tools panel. Bind `<Configure>` on the root to adjust minimum pane sizes and reposition sash when needed.

**When to use:** Any time the main 3-column layout needs to be user-resizable and the preview panel should expand to fill available space.

**Trade-offs:** `ttk.PanedWindow` adds user-resizable sashes (positive for power users), but requires minimum-size enforcement to prevent panels from collapsing entirely.

**Example:**
```python
# _build_ui: replace fixed-width pack/grid with PanedWindow
paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
paned.pack(fill=tk.BOTH, expand=True)

thumb_panel = tk.Frame(paned, width=180, bg=C["BG_PANEL"])
preview_frame = tk.Frame(paned, bg=C["PREVIEW_BG"])
tools_frame   = tk.Frame(paned, width=220, bg=C["BG_PANEL"])

paned.add(thumb_panel,  weight=0)   # fixed-ish, don't expand
paned.add(preview_frame, weight=1)  # takes all extra space
paned.add(tools_frame,  weight=0)   # fixed-ish

# Enforce minimums so panels never collapse
paned.paneconfig(thumb_panel,  minsize=140)
paned.paneconfig(tools_frame,  minsize=180)

# Responsive sash re-positioning on resize
def _on_window_resize(event):
    w = event.width
    # Only fire on root-level Configure, not child widget Configure
    if event.widget is self.root:
        # Place right sash so tools panel keeps fixed width
        paned.sashpos(1, w - 220)
self.root.bind("<Configure>", _on_window_resize)
```

### Pattern 2: windnd File Drop Integration

**What:** Register `windnd.hook_dropfiles(widget, func)` on the preview canvas. The callback receives a list of byte-strings (Windows ANSI/OEM paths) that must be decoded before use.

**When to use:** The project already lists windnd as an optional dependency. Register drop on the preview area (where the user's eye is focused) and optionally also on the root window.

**Trade-offs:** windnd is Windows-only (acceptable given Windows-11-only target). It passes paths as `bytes`, not `str` — decoding with `'mbcs'` (Windows Multi-Byte Character Set) is the correct approach for Japanese Windows systems, not `'utf-8'`.

**Example:**
```python
# In __init__, after UI is built, if windnd is available:
try:
    import windnd
    windnd.hook_dropfiles(self.preview_canvas, func=self._on_files_dropped)
    # Also hook root so user can drop anywhere
    windnd.hook_dropfiles(self.root, func=self._on_files_dropped)
except ImportError:
    pass  # windnd is optional; D&D file open silently unavailable

def _on_files_dropped(self, files):
    # files is a list of bytes on Windows; decode with 'mbcs' for
    # correct Japanese filename handling (Windows system codepage)
    paths = []
    for f in files:
        if isinstance(f, bytes):
            path = f.decode('mbcs', errors='replace')
        else:
            path = f
        if path.lower().endswith('.pdf'):
            paths.append(path)
    if not paths:
        return
    if len(paths) == 1:
        self._open_pdf_path(paths[0])
    else:
        # Reuse MergeOrderDialog for multi-file drops
        MergeOrderDialog(self.root, paths, callback=self._do_open_merged)
```

**Encoding note:** Windows 11 is moving toward UTF-8 as system codepage (21H2+), but `'mbcs'` decodes correctly on both old and new codepages. Do NOT use `'utf-8'` directly — it will misread paths on systems still using CP932 (Japanese Shift-JIS codepage). [MEDIUM confidence — based on Windows codepage behavior, not windnd-specific documentation]

### Pattern 3: PyInstaller onedir Spec File

**What:** A committed `pagefolio.spec` file (not a bare CLI invocation) that encodes all build configuration: onedir mode, no console, plugins directory as datas, sys.stdout guard for PyMuPDF.

**When to use:** From the first exe build attempt. Committing the spec avoids losing configuration between dev sessions and makes CI reproducible.

**Trade-offs:** The spec file adds a build artifact to the repository, but it is small (~40 lines) and changes rarely. The alternative (documenting CLI flags in a README) leads to drift.

**Example:**
```python
# pagefolio.spec
# -*- mode: python ; coding: utf-8 -*-

import sys

a = Analysis(
    ['pagefolio.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins', 'plugins'),           # include plugins/ directory
    ],
    hiddenimports=[
        'pymupdf',
        'fitz',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PageFolio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # --noconsole; REQUIRES sys.stdout guard (see below)
    icon='pagefolio.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PageFolio',
)
```

```python
# pagefolio.py — MUST be at the very top, before any pymupdf import:
import sys, os
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
```

**Why the guard is required:** PyMuPDF <= 1.24.12 crashes on import when `--noconsole` sets `sys.stdout = None`. Fixed in 1.24.13, but the guard is a cheap insurance policy that costs nothing at runtime. (HIGH confidence — confirmed via PyMuPDF issue #3981.)

### Pattern 4: Single-File Code Organization with Section Banners

**What:** Use prominent `# ===` banner comments as section delimiters within the single file. Each logical group of methods gets one banner. The banners serve as a navigable table of contents and make grep-based navigation reliable.

**When to use:** Any single-file Python module exceeding ~500 lines. Beyond that, visual scanning becomes unreliable.

**Trade-offs:** No runtime cost. The only risk is inconsistent use — adopt them across the whole file at once, not incrementally.

**Example:**
```python
# ===========================================================================
# SECTION: RESPONSIVE LAYOUT
# ===========================================================================

def _on_window_resize(self, event): ...
def _update_pane_proportions(self): ...

# ===========================================================================
# SECTION: DRAG & DROP FILE OPEN (windnd)
# ===========================================================================

def _on_files_dropped(self, files): ...
```

## Data Flow

### Responsive Resize Flow

```
User resizes window
    ↓
root <Configure> event fires
    ↓
_on_window_resize(event) called
    ↓ (guard: event.widget is self.root, not a child widget)
PanedWindow.sashpos(1, event.width - tools_width) called
    ↓
Preview canvas gets more/less horizontal space
    ↓
Next _show_preview() call uses updated canvas dimensions
```

### File Drop Flow (windnd)

```
User drags PDF from Explorer → drops on preview canvas or root
    ↓
Windows shell calls registered WM_DROPFILES message handler
    ↓
windnd callback fires: _on_files_dropped(files: List[bytes])
    ↓
Decode bytes with 'mbcs', filter for .pdf extension
    ↓ (single file)           ↓ (multiple files)
_open_pdf_path(path)      MergeOrderDialog → _do_open_merged(paths)
    ↓
_refresh_all() → thumbnails + preview redrawn
Plugin event: on_file_open(app, path)
```

### PyInstaller Build Flow

```
Developer runs: pyinstaller pagefolio.spec
    ↓
Analysis phase: collects pagefolio.py, pymupdf, Pillow, Tkinter,
                windnd, plugins/ directory
    ↓
EXE phase: builds bootloader + frozen Python + app code
    ↓
COLLECT phase: assembles dist/PageFolio/ folder:
    PageFolio.exe
    _internal/          (all dependencies)
    plugins/            (from datas tuple)
    ↓
User runs: PageFolio.exe (or PageFolio起動.bat pointing to it)
    ↓
sys.stdout guard fires (if None under --noconsole)
pymupdf imported successfully
App starts normally
```

### Key Data Flows (Existing — unchanged)

1. **Page modification → display:** Any page op calls `_save_undo()` → modifies `self.doc` → `_refresh_all()` → `_build_thumbnails()` + `_show_preview()` → plugin events fire.
2. **Settings change → UI rebuild:** `SettingsDialog` callback → `_apply_settings()` → `_apply_theme()` updates global `C` → `_rebuild_ui()` destroys and recreates all widgets.
3. **Undo/Redo:** State serialized as `doc.write()` bytes tuple; pushed/popped from LIFO stacks; `_restore_state()` reconstructs `fitz.Document` from bytes.

## Scaling Considerations

This is a local single-user desktop application. "Scaling" means handling large PDFs, not user load.

| PDF Size | Concern | Approach |
|----------|---------|----------|
| < 50 pages | No issue | Current implementation adequate |
| 50-200 pages | Thumbnail build time | Lazy thumbnail generation (build only visible thumbs) |
| 200+ pages | Undo stack memory (each state = full PDF bytes) | Already capped at MAX_UNDO=20; sufficient |
| 500+ pages | Initial load time | Progress dialog during `_build_thumbnails()` |

### Scaling Priorities

1. **First bottleneck:** Thumbnail generation on open — already mitigated by `thumb_cache`. For large PDFs, lazy rendering (generate only on scroll-into-view) is the next step.
2. **Second bottleneck:** Undo stack memory with large PDFs — already bounded at 20 states. No action needed for v1.0.

## Anti-Patterns

### Anti-Pattern 1: Fixed-Width Frames for Responsive Layout

**What people do:** Use `frame.config(width=220)` with `pack(side=tk.LEFT)` and rely on `minsize` on the root window to prevent undersizing.

**Why it's wrong:** Does not respond to window expansion. The preview area stays fixed even as the user makes the window larger. Right panel gets clipped on small displays (current bug).

**Do this instead:** Use `ttk.PanedWindow` with `weight=1` on the preview pane. The preview then claims all extra space on resize. Pair with `paneconfig(minsize=...)` to prevent collapse.

### Anti-Pattern 2: Hooking windnd on Every Widget

**What people do:** Call `hook_dropfiles()` on every panel and sub-frame to ensure "any drop" works.

**Why it's wrong:** Multiple overlapping `WM_DROPFILES` handlers can interfere on Windows. More practically, it creates duplicate `_on_files_dropped` calls for a single drop event.

**Do this instead:** Register on `self.root` once. Because the root window covers the entire application area, any drop anywhere in the window reaches the root handler. Add a secondary registration on the preview canvas only if you need visual feedback (e.g., highlighting the drop zone on drag-enter).

### Anti-Pattern 3: Using `--onefile` for PyInstaller

**What people do:** Use `pyinstaller --onefile --noconsole pagefolio.py` for "simpler distribution."

**Why it's wrong:** `--onefile` extracts to a temp directory on every launch. For pymupdf (which bundles MuPDF native DLLs), this means significant startup latency (3-10 seconds on some Windows systems) plus antivirus false-positives from writing DLLs to `%TEMP%`.

**Do this instead:** Use `--onedir` (the default). Ship the `dist/PageFolio/` folder. This matches the project's stated constraint ("フォルダ形式配布").

### Anti-Pattern 4: Decoding windnd Paths as UTF-8

**What people do:** `path = f.decode('utf-8')` because "modern Windows is UTF-8."

**Why it's wrong:** Windows system codepage on Japanese Windows is still CP932 (Shift-JIS) unless the user has explicitly enabled the UTF-8 beta setting. `f.decode('utf-8')` raises `UnicodeDecodeError` on any path containing Japanese characters.

**Do this instead:** `f.decode('mbcs', errors='replace')` — `'mbcs'` maps to the current system codepage, handling both old CP932 systems and new UTF-8 systems correctly.

## Integration Points

### External Libraries

| Library | Integration Pattern | Notes |
|---------|---------------------|-------|
| pymupdf (fitz) | Direct import; `fitz.Document` as central state object | Use `import pymupdf as fitz` for forward compatibility; old `import fitz` still works |
| Pillow (PIL) | Used for `fitz.Pixmap` → `ImageTk.PhotoImage` conversion | Required for thumbnail and preview rendering |
| windnd | `hook_dropfiles(widget, func)` once in `__init__`; import guarded by `try/except ImportError` | Windows-only; treat as optional |
| winreg | Direct import for system theme detection in `_detect_system_theme()` | Already integrated |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| PDFEditorApp ↔ PluginManager | `plugin_manager.fire_event("on_*", self, ...)` — one-way push after state changes | Plugins must not call back into app synchronously |
| PDFEditorApp ↔ Dialog classes | Constructor callback pattern: `Dialog(parent, ..., callback=self._method)` | Dialog calls callback on confirm; caller never polls |
| Global `C` dict ↔ all UI | `_apply_theme()` mutates `C` in-place; `_rebuild_ui()` must be called after | Do not snapshot `C` values at widget construction time |
| windnd callback ↔ Tkinter event loop | windnd fires callback from Windows message thread; Tkinter is single-threaded — use `self.root.after(0, ...)` if any threading issues arise | Currently synchronous and stable |

## Sources

- windnd GitHub repository: https://github.com/cilame/windnd
- PyMuPDF issue #3981 (1.24.12 PyInstaller --noconsole crash): https://github.com/pymupdf/PyMuPDF/issues/3981
- PyInstaller spec files documentation: https://pyinstaller.org/en/stable/spec-files.html
- PyInstaller usage documentation: https://pyinstaller.org/en/stable/usage.html
- Packaging Tkinter apps with PyInstaller (pythonguis.com): https://www.pythonguis.com/tutorials/packaging-tkinter-applications-windows-pyinstaller/
- ttk.PanedWindow (anzeljg reference): https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/ttk-PanedWindow.html
- Windows UTF-8 codepage note: https://ao-system.net/en/note/204

---
*Architecture research for: PageFolio v1.0 — single-file Tkinter PDF editor*
*Researched: 2026-03-18*
