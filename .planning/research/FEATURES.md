# Feature Research

**Domain:** Desktop PDF page editor (lightweight, Windows, Tkinter/PyMuPDF)
**Researched:** 2026-03-18
**Confidence:** MEDIUM — Core UI patterns HIGH; D&D library comparison MEDIUM; exe distribution HIGH

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any desktop PDF tool. Missing these = product feels broken or amateurish.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Window resizes gracefully | All desktop apps resize; right-side panel clipping is a clear defect | MEDIUM | Use grid() with weight=1, sticky="nsew"; bind `<Configure>` to redraw canvas |
| PDF opens via file drop | Every modern desktop app accepts dropped files; opening only via menu feels outdated | LOW-MEDIUM | `windnd` is already an optional dep; `tkinterdnd2` is the alternative with better PyInstaller support |
| Thumbnails stay visible at narrow widths | Thumbnail panel must never overflow or disappear on normal window sizes | MEDIUM | Min-width on thumbnail frame; PanedWindow with sash constraints |
| Non-blocking UI during large-file open | UI freezing during open of 100+ page PDF is unacceptable; perceived as crash | MEDIUM | threading + queue + `after()` polling pattern |
| Visual feedback on drop target | Drop zones need hover highlight; no feedback = users unsure if action worked | LOW | Canvas color change on `<DragEnter>`/`<DragLeave>` events |
| Error messages in user language | Native-language error dialogs; not Python tracebacks | LOW | Already done for most; verify all error paths use `_t()` |
| Save confirmation before close | Standard for any editor; data loss = trust killer | LOW | Already implemented via `_quit()`; confirm completeness |
| Status bar showing current operation | Users need to know "Saving…", "Loading page 3 of 200…" | LOW | `_set_status()` exists; extend to cover all async operations |

### Differentiators (Competitive Advantage)

Features that raise PageFolio above generic PDF tools. PageFolio's core value is *lightweight + intuitive*; differentiators should serve that value specifically.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Drop PDF onto preview to open | Most natural gesture — user is looking at preview, drops file there; competitors use only menu or dedicated drop zone | LOW | windnd hook on preview Canvas widget; opens or merges depending on current state |
| Drop multiple PDFs to queue merge | Drag N files at once → auto-open MergeOrderDialog; reduces 3-step workflow to 1 | MEDIUM | windnd callback receives list of paths; route to existing `MergeOrderDialog` |
| Progress indicator for large PDFs | Skeleton/spinner during thumbnail generation; competitors freeze or show blank screen | MEDIUM | Run `_build_thumbnails()` in thread; update panel with `after()` as each thumb is ready |
| Incremental thumbnail rendering | Render thumbnails one-at-a-time as they complete; user can start interacting before all are ready | HIGH | Complex state: must guard against user actions on not-yet-rendered pages |
| Responsive split pane | PanedWindow sash lets user control thumbnail-vs-preview ratio; persisted in settings | MEDIUM | Replace fixed-width frame with `ttk.PanedWindow`; save sash position to settings JSON |
| Exe with splash screen | PyInstaller onedir + custom splash reduces perceived startup latency | MEDIUM | PyInstaller `--splash` flag or Tk splash Toplevel before mainloop |
| Plugin-visible D&D events | Fire `on_file_drop(app, paths)` plugin event so plugins can handle drop logic | LOW | Extend existing plugin event system; no new infrastructure needed |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Single-file exe (`--onefile`) | Simpler to share one file | PyInstaller onefile unpacks to temp dir at runtime; adds 2-10s cold startup, frustrates users; PyMuPDF's binary assets make the bundle large | Onedir folder distribution with a launcher .bat; already decided in PROJECT.md |
| Live preview update while dragging crop rect | Feels responsive | Rendering a full-resolution preview on every mouse-move event hammers CPU; Tkinter redraws synchronously and will freeze on large pages | Keep overlay rect update (fast) separate from preview re-render (only on confirmed crop) |
| Auto-save / autorecover | Prevents data loss, users ask for it | Requires background thread writing to disk continuously; state snapshot on every change bloats undo stack and creates I/O race conditions | Undo stack up to 20 steps provides adequate safety; explicit save prompt on quit |
| Tabbed multi-document interface | Open many PDFs simultaneously | Tkinter has no native tab widget suitable for document windows; implementing MDI on Tkinter creates deep architectural changes to a monolithic single-file app | Open multiple windows via separate processes, or defer to post-v1.0 |
| Full annotation/text edit | Users want to type into PDF | pymupdf supports it but it is complex (font embedding, redraw pipeline, CJK font handling); pulls far outside the "page operations" core value | Stay focused on page-level operations; link to Acrobat/LibreOffice for text editing |
| Cloud sync / online storage | Users want access anywhere | Network I/O in Tkinter requires async handling that the current architecture does not support; also adds authentication complexity | Local files only; users can put their PDF in Dropbox/OneDrive folder themselves |

---

## Feature Dependencies

```
[Responsive layout]
    └──requires──> [grid() weight configuration throughout _build_ui]
                       └──requires──> [Replace any place()-based layouts in preview/thumb panels]

[D&D file open]
    └──requires──> [windnd hook registration on target widget]
                       └──enhances──> [MergeOrderDialog] (already exists)
    └──requires──> [Drop visual feedback on Canvas]

[Non-blocking large file open]
    └──requires──> [threading.Thread + queue.Queue pattern]
                       └──requires──> [after() polling in main thread]
                       └──conflicts──> [Direct widget update from worker thread]

[Incremental thumbnail rendering]
    └──requires──> [Non-blocking large file open]
                       └──requires──> [Per-thumb after() callback]
    └──conflicts──> [User page operations on partially-loaded doc]

[Exe distribution]
    └──requires──> [PyInstaller onedir build]
                       └──requires──> [--hidden-import=fitz for PyMuPDF]
                       └──requires──> [windnd OR tkinterdnd2 hook files if D&D is bundled]
    └──enhances──> [Splash screen] (optional, reduces perceived startup lag)

[Plugin D&D events]
    └──requires──> [D&D file open] (provides the event trigger)
    └──enhances──> [Plugin system] (already exists)
```

### Dependency Notes

- **Responsive layout requires grid() weight configuration:** Current layout uses a mix of pack() and grid(). Mixing geometry managers within the same container causes unpredictable resize behavior. All containers in `_build_ui()` must be audited before responsive behavior will work reliably.
- **Non-blocking open conflicts with direct widget update:** Tkinter's main loop is not thread-safe. Worker threads must never call widget methods directly; all updates must go through `root.after(0, callback)` or a `queue.Queue` polled by `after()`.
- **Incremental thumbnails conflicts with user operations on partially-loaded doc:** If a user clicks page 50's thumbnail before generation is complete, `self.doc` may be in an inconsistent state. Either disable page operations until fully loaded (simpler, safe) or implement per-page ready flags (complex).
- **D&D requires windnd or tkinterdnd2:** `windnd` is lighter but has no published PyInstaller hook; `tkinterdnd2` includes `hook-tkinterdnd2.py` for bundling. If exe distribution is in scope (it is), prefer `tkinterdnd2` or verify windnd works in onedir mode.

---

## MVP Definition

PageFolio v1.0 MVP (this milestone scope) — the app already has all core PDF operations. v1.0 is about *quality and distribution*, not new features.

### Launch With (v1.0)

- [ ] **Responsive layout** — right-panel clipping is a visible defect; must fix before public release
- [ ] **D&D file open on preview area** — highest-impact UX improvement; maps to stated requirement
- [ ] **Non-blocking UI for large PDFs** — freezing UI on open is perceived as a crash; critical for quality
- [ ] **PyInstaller onedir exe** — required for distribution; stated primary deliverable
- [ ] **Bug fixes from full code review** — quality gate before v1.0 label

### Add After Validation (v1.x)

- [ ] **Incremental thumbnail rendering** — useful but adds complexity; add when large-PDF users complain
- [ ] **Responsive sash pane (PanedWindow)** — nice-to-have UX; add if layout refactor is done cleanly
- [ ] **Splash screen for exe** — add if startup latency is reported as a complaint

### Future Consideration (v2+)

- [ ] **Multiple PDF drop → merge queue** — extends D&D; natural next step after single-file drop works
- [ ] **Tabbed multi-document** — requires architectural change; defer until single-doc quality is solid
- [ ] **Plugin D&D events** — low effort but only matters when plugin ecosystem is active

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Responsive layout (fix right-panel clip) | HIGH | MEDIUM | P1 |
| D&D file open (preview area) | HIGH | LOW-MEDIUM | P1 |
| Non-blocking UI (threading for open) | HIGH | MEDIUM | P1 |
| PyInstaller onedir exe build | HIGH | MEDIUM | P1 |
| Code review + bug fixes | HIGH | MEDIUM | P1 |
| Progress indicator during load | MEDIUM | LOW | P2 |
| Responsive sash (PanedWindow) | MEDIUM | MEDIUM | P2 |
| Splash screen for exe | LOW | LOW | P3 |
| Plugin D&D events | LOW | LOW | P3 |
| Incremental thumbnail rendering | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.0 launch
- P2: Should have, add when core is stable
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

Scope: lightweight desktop PDF page editors — tools comparable to PageFolio's design intent (not Acrobat-class).

| Feature | PDF-XChange Editor (lite) | PDFsam Basic | Our Approach |
|---------|--------------------------|--------------|--------------|
| File drag-and-drop open | Yes — drag to window anywhere | Yes — drag to file list | Drop onto preview canvas; multiple files route to MergeOrderDialog |
| Window resize / responsive | Yes — full responsive | Yes — Swing layout | grid() with weights; no fixed pixel sizing |
| Thumbnail panel | Yes — resizable side panel | Yes — page preview list | PanedWindow sash for user control |
| Progress on load | Yes — progress bar in status | Yes — progress dialog | Spinner + status bar text; incremental thumb render |
| Non-blocking load | Yes | Yes | threading + after() pattern |
| Undo/Redo | Yes (multiple levels) | Limited | Already implemented (20 levels) |
| Portable exe / no-install | Yes (portable zip) | Yes (portable zip) | PyInstaller onedir folder |
| Plugin system | No | No | Already implemented — competitive differentiator |
| Theme (dark/light) | Partial (dark skin paid) | No | Already implemented — competitive differentiator |

---

## Implementation Notes

### D&D Library Recommendation

**Use `tkinterdnd2` over `windnd` for v1.0.**

Rationale: `tkinterdnd2` ships a `hook-tkinterdnd2.py` PyInstaller hook file, making bundling straightforward. `windnd` has no published PyInstaller hook and its maintenance activity on GitHub (cilame/windnd) has been sparse since 2020. Since PyInstaller exe distribution is a v1.0 deliverable, using a library with confirmed bundling support removes a significant risk. The API surface needed (register drop target on a widget, receive file paths) is identical between both libraries. Confidence: MEDIUM — verify `tkinterdnd2` works in PyInstaller onedir before committing.

### Responsive Layout Approach

**Use `ttk.PanedWindow` for the main split, `grid()` with weights everywhere else.**

Tkinter's `grid()` with `rowconfigure(index, weight=1)` and `columnconfigure(index, weight=1)` is the standard approach for responsive layouts. Current code mixes `pack()` and `grid()`; audit `_build_ui()` and standardize. The thumbnail/preview split should become a `ttk.PanedWindow` so users can drag the sash. Minimum pane widths prevent panels from collapsing to zero. Confidence: HIGH — standard Tkinter pattern, well-documented.

### Threading Pattern for Large File Open

**Worker thread for fitz.Document creation + thumbnail generation; communicate via `queue.Queue` + `root.after()`.**

Pattern:
1. Main thread: show spinner, disable doc buttons
2. Worker thread: open fitz.Document, generate thumbnails one by one, put results in queue
3. Main thread: `after(100, check_queue)` polling; update panel as items arrive
4. On completion: hide spinner, enable buttons, fire plugin event

Tkinter is not thread-safe; never call widget methods from the worker thread. Confidence: HIGH — standard Tkinter threading pattern.

---

## Sources

- PyInstaller onefile vs onedir startup comparison: [AhmedSyntax PyInstaller Guide](https://ahmedsyntax.com/pyinstaller-onefile/)
- PyInstaller operating mode documentation: [PyInstaller Docs](https://pyinstaller.org/en/stable/operating-mode.html)
- tkinterdnd2 PyInstaller hook: [pmgagne/tkinterdnd2 GitHub](https://github.com/pmgagne/tkinterdnd2)
- windnd library: [cilame/windnd GitHub](https://github.com/cilame/windnd)
- Tkinter threading + after() pattern: [TomTalksPython Medium](https://medium.com/tomtalkspython/tkinter-and-threading-building-responsive-python-gui-applications-02eed0e9b0a7)
- Tkinter responsive grid layout: [PythonGuides grid tutorial](https://pythonguides.com/python-tkinter-grid/)
- Drag-and-drop UX best practices: [Pencil & Paper D&D patterns](https://www.pencilandpaper.io/articles/ux-pattern-drag-and-drop)
- Progress indicator UX guidelines: [Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/designing-better-loading-progress-ux/)
- PyMuPDF hidden import issue: [PyMuPDF GitHub Issue #712](https://github.com/pymupdf/PyMuPDF/issues/712)
- PDF editor feature comparison 2025: [SodaPDF blog](https://www.sodapdf.com/blog/what-are-the-best-pdf-editors-2025-feature-comparison/)

---

*Feature research for: lightweight desktop PDF page editor (PageFolio v1.0)*
*Researched: 2026-03-18*
