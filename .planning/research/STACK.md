# Stack Research

**Domain:** Tkinter PDF editor — responsive UI, Windows D&D, PyInstaller packaging, performance
**Researched:** 2026-03-18
**Confidence:** MEDIUM (Tkinter/PyInstaller official docs verified; windnd/tkinterdnd2 via PyPI + GitHub)

---

## Recommended Stack

### Core Technologies (Unchanged — Constraints Lock These In)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.8+ | Runtime | Project constraint; PyInstaller 6.x supports 3.8–3.14 |
| Tkinter | stdlib | All GUI | Project constraint; no external GUI dep needed |
| PyMuPDF (pymupdf) | latest (>=1.23) | PDF render/edit | Project constraint; use `import pymupdf` not `import fitz` to avoid packaging collision |
| Pillow (PIL) | latest | Image conversion for Tkinter display | Project constraint |

### Supporting Libraries — New Additions

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tkinterdnd2 | 0.4.3 (Feb 2025) | Windows file drag-and-drop into Tkinter widgets | Replace windnd; use when D&D file open is needed |
| PyInstaller | 6.19.0 (Feb 2026) | Produce distributable folder-mode exe for Windows | exe packaging milestone |
| threading (stdlib) | stdlib | Background thumbnail/render workers | When PDF operations block the UI event loop |
| queue (stdlib) | stdlib | Thread-safe communication from worker to main thread | Pair with threading; never touch widgets from worker thread |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| PyInstaller spec file | Controls exactly what gets bundled | Prefer spec over bare CLI for complex deps like pymupdf + tkinterdnd2 |
| pyi-makespec | Generate initial .spec from CLI flags | Run once, then maintain spec manually |

---

## Responsive Layout — Approach

Tkinter's grid geometry manager with `rowconfigure`/`columnconfigure` `weight` parameters is the correct primitive for responsive layouts. No external library is needed.

**Pattern to use:**

```python
# Root or frame: columns/rows that should expand get weight=1
root.columnconfigure(0, weight=1)   # thumbnail panel fixed
root.columnconfigure(1, weight=3)   # preview expands
root.rowconfigure(0, weight=1)

# Widget fills available space
preview_frame.grid(row=0, column=1, sticky="nsew")
```

For the right-panel overflow issue specifically: the right tools panel is a scrollable Canvas — ensure it has `sticky="ns"` (not `nsew`) so it does not expand horizontally and cause the preview to be squeezed.

**Debounced resize callback (avoid doing expensive work on every Configure event):**

```python
self._resize_job = None

def _on_resize(self, event):
    if self._resize_job:
        self.after_cancel(self._resize_job)
    self._resize_job = self.after(150, self._do_layout_update)
```

`PanedWindow` is an option for user-adjustable pane sizing but adds complexity — use only if user-adjustable split is a requirement.

**Confidence: HIGH** — This is standard Tkinter geometry manager behavior, documented in stdlib.

---

## Windows File Drag-and-Drop — tkinterdnd2 over windnd

### Why Replace windnd

windnd v1.0.7 was last published August 2020 — over 5 years without updates. Its API (`windnd.hook_dropfiles`) hooks at the Win32 `WM_DROPFILES` message level. It has no active maintenance and does not support dropping onto specific widgets (only the whole window root). It is Windows-only with no cross-platform path.

### Why tkinterdnd2

tkinterdnd2 v0.4.3 (released February 28, 2025) wraps George Petasis' tkDnD2 Tk extension, using Windows OLE2 drag-and-drop interfaces. Key advantages:

- Drop target can be any specific widget (Canvas, Frame, Label) — not just the root window
- Returns a clean file path string via `event.data`, stripping `{}` braces that Windows paths can include
- Actively maintained fork (Eliav2/tkinterdnd2 on GitHub)
- Supports multiple files in one drop
- Has a PyInstaller hook file included in the package

**Integration requirement:** Replace `tk.Tk()` with `TkinterDnD.Tk()` as the root window class. This is a one-line change in `pagefolio.py`'s `if __name__ == "__main__"` block and has no side effects on existing Tkinter behavior.

```python
from tkinterdnd2 import TkinterDnD, DND_FILES

root = TkinterDnD.Tk()  # replaces tk.Tk()
# ...
canvas_preview.drop_target_register(DND_FILES)
canvas_preview.dnd_bind("<<Drop>>", on_file_drop)
```

**Fallback pattern:** Since windnd is already optional in the codebase, the same graceful-degradation import pattern can be used for tkinterdnd2 to keep the app functional if tkinterdnd2 is not installed.

**Confidence: HIGH** — PyPI page verified, version confirmed, OLE2 usage documented.

---

## PyInstaller Packaging

### Version

Use PyInstaller **6.19.0** (latest stable as of February 2026). Python 3.8–3.14 compatible.

```bash
pip install pyinstaller==6.19.0
```

### Critical: Import Name for PyMuPDF

`pagefolio.py` currently uses `import fitz`. There is an unrelated package named `fitz` on PyPI. PyInstaller can package the wrong one or fail to detect PyMuPDF's binaries. **Before packaging, change to:**

```python
import pymupdf as fitz  # was: import fitz
```

This one change prevents the most common PyInstaller+PyMuPDF packaging failure. **Confidence: HIGH** — documented in PyMuPDF official installation docs and GitHub issue #712.

### Recommended Spec File Approach

Avoid bare `pyinstaller pagefolio.py` for this project. Use a spec file to control hidden imports explicitly.

**Generate initial spec:**
```bash
pyi-makespec --windowed --name PageFolio --icon pagefolio.ico pagefolio.py
```

**Required additions to spec `Analysis()`:**

```python
from PyInstaller.utils.hooks import collect_all

pymupdf_datas, pymupdf_binaries, pymupdf_hiddenimports = collect_all('pymupdf')

a = Analysis(
    ['pagefolio.py'],
    datas=pymupdf_datas,
    binaries=pymupdf_binaries,
    hiddenimports=pymupdf_hiddenimports + ['tkinterdnd2'],
    ...
)
```

For tkinterdnd2, also copy its hook file into the project root and pass `--additional-hooks-dir=.` (or add the hook path to `hookspath` in the spec). This ensures tkdnd binaries are included.

### Critical: Windowed Mode stdout/stderr Guard

PyInstaller `--windowed` sets `sys.stdout` and `sys.stderr` to `None`. PyMuPDF can trigger `AttributeError: 'NoneType' object has no attribute 'flush'` in this state. Add this guard at the very top of `pagefolio.py` before any other imports:

```python
import sys, os
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
```

### Distribution Format

Use `--onedir` (folder mode, the PyInstaller default). The project decision record already confirms this — folder mode avoids the 5–30 second unpacking delay of `--onefile` single-exe mode.

**Confidence: MEDIUM** — `collect_all` approach is verified PyInstaller pattern; PyMuPDF-specific steps confirmed via GitHub issues but no single official combined guide exists.

---

## Performance Optimization

### Problem

PyMuPDF page rendering (`page.get_pixmap()`) is CPU-bound. When loading a large PDF (50+ pages), generating all thumbnails synchronously in `_build_thumbnails()` blocks the Tkinter event loop, freezing the UI.

### Recommended Pattern: threading + queue.Queue + after() polling

This is the canonical Tkinter threading pattern. No external library needed.

```python
import threading
import queue

class PDFEditorApp:
    def __init__(self):
        self._thumb_queue = queue.Queue()
        # Start polling
        self._poll_thumb_queue()

    def _poll_thumb_queue(self):
        """Called via after(); drains queue and updates UI."""
        try:
            while True:
                page_index, photo = self._thumb_queue.get_nowait()
                self._apply_thumb_photo(page_index, photo)
        except queue.Empty:
            pass
        self.after(50, self._poll_thumb_queue)  # poll every 50ms

    def _build_thumbnails_async(self):
        """Spawn worker thread for thumbnail generation."""
        def worker():
            for i in range(len(self.doc)):
                photo = self._render_thumb(i)
                self._thumb_queue.put((i, photo))
        threading.Thread(target=worker, daemon=True).start()
```

**Rules:**
- Never call `widget.configure()`, `canvas.create_image()`, or any Tkinter method from the worker thread — only from the main thread via `after()` or `after_idle()`.
- Use `daemon=True` so worker threads don't prevent app exit.
- The existing `thumb_cache` dict in PageFolio is already the right caching layer — populate it from the worker, apply photos in the main thread.

### Additional Optimizations (No Library Changes)

- Bind `<Configure>` on the preview canvas and debounce with `after(150, ...)` to avoid re-rendering the preview on every pixel of resize.
- Use `canvas.delete("all")` sparingly — prefer updating existing canvas items by tag rather than full redraws.
- `update_idletasks()` can flush pending geometry changes without blocking, useful before measuring widget dimensions.

**Confidence: HIGH** — threading + queue + after() is documented stdlib pattern; Tkinter thread-unsafety is a known, well-documented constraint.

---

## Installation

```bash
# New D&D dependency (replaces windnd)
pip install tkinterdnd2==0.4.3

# Packaging tool
pip install pyinstaller==6.19.0

# Existing deps (ensure current versions)
pip install pymupdf pillow
```

**requirements.txt (proposed):**
```
pymupdf
Pillow
tkinterdnd2>=0.4.3
```

PyInstaller as a dev/build-only dependency — not needed at runtime.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| tkinterdnd2 0.4.3 | windnd 1.0.7 | Never for new work; windnd is unmaintained (last release 2020) |
| tkinterdnd2 0.4.3 | python-tkdnd | If tkinterdnd2 fails on a specific Python/Windows combination; similar API |
| PyInstaller folder mode | PyInstaller --onefile | Never for this project; onefile has 5–30s startup delay |
| PyInstaller | cx_Freeze | If PyInstaller proves incompatible with a specific PyMuPDF version; more manual setup |
| threading + queue | asyncio | asyncio is for I/O-bound async; PyMuPDF rendering is CPU-bound; threading is correct |
| threading + queue | concurrent.futures | concurrent.futures.ThreadPoolExecutor is a valid alternative with cleaner API, but adds no benefit over bare threading for this pattern |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `import fitz` in packaged exe | Conflicts with unrelated `fitz` PyPI package; causes ModuleNotFoundError at runtime | `import pymupdf as fitz` |
| `windnd` for new D&D work | Unmaintained since 2020; only hooks root window; Windows-only with no future | `tkinterdnd2` |
| PyInstaller `--onefile` | 5–30 second startup while unpacking to temp dir; terrible UX for a desktop app | `--onedir` (default) folder distribution |
| Calling Tkinter widget methods from worker threads | Tkinter is not thread-safe; causes race conditions, crashes, corrupted state | Put results in `queue.Queue`; apply from main thread via `after()` |
| Fixed pixel widths/heights in grid layouts | Prevents responsive resizing; right panel overflow is caused by this | `columnconfigure(weight=N)` + `sticky="nsew"` |

---

## Stack Patterns by Condition

**If windnd is already installed on user machine:**
- Keep the existing fallback import for compatibility during transition; once tkinterdnd2 is the primary path, remove windnd fallback in a later cleanup pass.

**If PyMuPDF version is < 1.23:**
- `import pymupdf as fitz` may not work; verify PyMuPDF version before changing the import. PyMuPDF added the `pymupdf` top-level module name in 1.23.

**If tkinterdnd2 is not installed (distribution without it):**
- The existing graceful-degradation pattern (`try: import windnd except ImportError: pass`) should be replicated for tkinterdnd2 so the app still opens PDFs via the file dialog.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| PyInstaller 6.19.0 | Python 3.8–3.14 | Confirmed on PyPI |
| tkinterdnd2 0.4.3 | Python 3.6+ | Confirmed on PyPI; includes Windows ARM64 support |
| pymupdf (any modern) | PyInstaller 6.x | Use `collect_all('pymupdf')` in spec; use `import pymupdf as fitz` |
| tkinterdnd2 + PyInstaller | — | Requires copying tkinterdnd2's hook file and `--additional-hooks-dir=.` |

---

## Sources

- [tkinterdnd2 on PyPI](https://pypi.org/project/tkinterdnd2/) — version 0.4.3, release date Feb 2025 confirmed (HIGH confidence)
- [windnd on PyPI](https://pypi.org/project/windnd/) — version 1.0.7, last release Aug 2020 confirmed (HIGH confidence)
- [PyInstaller on PyPI](https://pypi.org/project/pyinstaller/) — version 6.19.0, Feb 2026 confirmed (HIGH confidence)
- [PyInstaller official docs — Using Spec Files](https://pyinstaller.org/en/stable/spec-files.html) — `collect_all` pattern verified (HIGH confidence)
- [PyMuPDF installation docs](https://pymupdf.readthedocs.io/en/latest/installation.html) — `import pymupdf` vs `import fitz` naming guidance (HIGH confidence)
- [pymupdf/PyMuPDF GitHub Discussion #3467](https://github.com/pymupdf/PyMuPDF/discussions/3467) — `sys.stdout None` guard for windowed mode (MEDIUM confidence — community finding)
- [pymupdf/PyMuPDF GitHub Issue #712](https://github.com/pymupdf/PyMuPDF/issues/712) — `import fitz` packaging failure pattern (MEDIUM confidence — community finding)
- [Eliav2/tkinterdnd2 on GitHub](https://github.com/Eliav2/tkinterdnd2) — active maintenance, hook file for PyInstaller (MEDIUM confidence)
- WebSearch: Tkinter grid weight responsive layout — corroborated by multiple sources (MEDIUM confidence)
- WebSearch: threading + queue.Queue + after() pattern — corroborated by multiple sources (HIGH confidence — standard Python pattern)

---

*Stack research for: PageFolio v1.0 — responsive UI, D&D, PyInstaller, performance*
*Researched: 2026-03-18*
