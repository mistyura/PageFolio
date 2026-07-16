---
phase: 06-ux-ui
reviewed: 2026-07-16T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - pagefolio/dialogs/about.py
  - pagefolio/dialogs/plugin.py
  - pagefolio/file_ops.py
  - pagefolio/lang.py
  - pagefolio/ocr_dialog.py
  - pagefolio/print_ops.py
  - pagefolio/toast.py
  - pagefolio/ui_builder.py
  - tests/test_font_hardcode_guard.py
  - tests/test_pdf_ops.py
  - tests/test_print.py
  - tests/test_toast.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-07-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the three Phase 6 plans: the new `ToastManager` (06-01) and its wiring into
`file_ops.py`/`print_ops.py`/`ui_builder.py`/`lang.py`, the UI-consistency scroll/font
fixes (06-02) in `dialogs/plugin.py`, `ocr_dialog.py`, and `dialogs/about.py`, and the
`insert_redo` undo/redo asymmetry fix (06-03) in `file_ops.py`.

I traced the `insert → undo → redo → undo` state machine by hand across
`_save_undo`/`_apply_inverse`/`_restore_state` (file_ops.py:284-460) and confirmed the
06-03 fix is correct and properly symmetric with `delete_redo`: the second `_undo()`
now deletes the re-inserted page (descending index order) instead of re-inserting it a
second time, blob capture/dispose ordering is sound (capture happens before mutation in
`_apply_inverse`, and `_dispose_state` only releases blobs that are not shared with the
newly computed inverse), and the added regression test
(`test_insert_undo_redo_undo_roundtrip`) exercises exactly this 4-move sequence.
`pytest tests/test_pdf_ops.py` (67 tests), `tests/test_toast.py` +
`tests/test_print.py` + `tests/test_font_hardcode_guard.py` (23 tests) all pass, and
`ruff check` is clean on all 12 files.

The toast wiring (D-02/D-08) is also correct for the scenarios it's exercised against:
`retry_cb` is always a stable bound method (`self._save_file`, `self._save_as`,
`self._save_compressed`, `self._print_pdf`), so there is no stale-closure/double-firing
risk in the current call sites, all interactions are on the Tk main thread (no
`fitz.Document` crosses threads here), and `dismiss(category)` correctly no-ops when a
different category is currently showing.

That said, three provable defects were found, two of which I verified empirically with
throwaway Tkinter scripts rather than by inspection alone (see below). None are
data-loss/security-critical, but two directly undermine the stated intent of the
06-02 fixes they belong to.

## Warnings

### WR-01: `_center()`'s new screen-height clamp in ocr_dialog.py is neutralized by `self.minsize(960, 620)`

**File:** `pagefolio/ocr_dialog.py:201-214`
**Issue:**
The 06-02 fix adds a clamp so the dialog can't be taller than the screen:
```python
h = max(680, int(fs * 56))
try:
    max_h = max(320, self.winfo_screenheight() - 100)
    h = min(h, max_h)
except tk.TclError:
    pass
...
self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
self.minsize(960, 620)
```
The floor value `320` was copied verbatim from `llm_config/dialog.py._compute_dialog_height`
(pagefolio/dialogs/llm_config/dialog.py:171), where it is internally consistent because
that dialog's own `minsize` is `(420, 320)` — i.e. the floor equals the minsize height.
`OCRDialog`, however, calls `self.minsize(960, 620)` right after `geometry()`. On any
screen shorter than ~720px tall (620 + the 100px margin), the clamp computes
`h < 620`, but the subsequent `minsize(960, 620)` call forces Tkinter to grow the window
back up to at least 620px — silently discarding the clamp and re-introducing exactly the
off-screen-bottom problem the fix was meant to prevent.

I confirmed empirically that `minsize()` overrides a smaller prior `geometry()` height on
this environment:
```python
top.geometry('300x300+50+50')
top.minsize(960, 620)
top.update_idletasks()
top.winfo_height()  # -> 620, not 300
```
**Fix:** Either raise the clamp floor to match the dialog's own minsize, or lower the
minsize to match the floor, e.g.:
```python
max_h = max(620, self.winfo_screenheight() - 100)  # match minsize(960, 620)
h = min(h, max_h)
```

### WR-02: `PluginDialog`'s `<Destroy>`-bound wheel-unbind fires on every child-row destroy, not just dialog close

**File:** `pagefolio/dialogs/plugin.py:91-109`, `133-147`, `211-218`
**Issue:**
The 06-02 fix adds an Enter/Leave dynamic `bind_all` mousewheel binding for the plugin
list canvas, copied from `llm_config/dialog.py`:
```python
canvas.bind("<Enter>", _bind_wheel)
canvas.bind("<Leave>", _unbind_wheel)
self.bind("<Destroy>", lambda _e: _unbind_wheel(), add="+")
```
The intent (per the comment) is "unbind the global wheel handlers when the dialog
closes." However, in Tkinter, `<Destroy>` events propagate through a widget's bindtags,
which include its toplevel's tag — so `self.bind("<Destroy>", ...)` on the `PluginDialog`
Toplevel fires for **every** widget destroyed inside it, not only when the dialog itself
is destroyed. I confirmed this empirically:
```python
top.bind('<Destroy>', lambda e: calls.append(e.widget), add='+')
child2.destroy()   # -> fires the toplevel-bound handler immediately
```
`_refresh_list()` (plugin.py:133-147) does `for w in self._list_inner.winfo_children():
w.destroy()`, which is called from `_rescan()` (plugin.py:211-218). Every time the user
clicks "🔄 再検出" (rescan), each destroyed row fires `_unbind_wheel()`, globally
unbinding `<MouseWheel>`/`<Button-4>`/`<Button-5>` even though the dialog stays open.
Since re-binding only happens on the canvas's next `<Enter>` event, mousewheel
scrolling over the plugin list silently stops working after a rescan until the mouse
leaves and re-enters the canvas area — the opposite of "scroll pattern fix" the plan
intended to land.
**Fix:** Guard the handler so it only unbinds on the dialog's own destruction, e.g.:
```python
self.bind("<Destroy>", lambda e: _unbind_wheel() if e.widget is self else None, add="+")
```
(This same latent bug exists in the `llm_config/dialog.py` source pattern being copied,
so consider fixing both once identified.)

### WR-03: `ToastManager.show()` silently drops an updated `retry_cb` when re-showing the same active category

**File:** `pagefolio/toast.py:39-51`
**Issue:**
```python
def show(self, category, message, retry_cb):
    if self._active_category == category and self._frame is not None:
        self._msg_var.set(message)
        return
    self._destroy_frame()
    self._active_category = category
    self._build_frame(category, message, retry_cb)
```
When the same category is shown twice in a row (D-04, e.g. two consecutive save
failures), only the message text is updated — the `retry_cb` argument passed to the
second `show()` call is discarded, and the "再試行" button keeps invoking whatever
callback was bound when the Frame was first built. In the current codebase this is
harmless because every call site always passes the same stable bound method for a given
category (`self._save_file`, `self._save_as`, `self._save_compressed`, `self._print_pdf`),
but the API silently accepts a parameter it then ignores, which is a footgun for any
future caller that (legitimately, per the docstring's "same category → update message
only" contract) expects the newest callback to win.
**Fix:** Either document this explicitly as intentional in the docstring, or rebind the
button's command on repeat `show()`:
```python
if self._active_category == category and self._frame is not None:
    self._msg_var.set(message)
    self._retry_btn.configure(command=retry_cb)
    return
```
(requires keeping a reference to the retry button, e.g. `self._retry_btn`).

## Info

### IN-01: Retry on `_save_file`/`_save_compressed` re-triggers the overwrite confirmation dialog

**File:** `pagefolio/file_ops.py:648-687`, `735-767`
**Issue:** The toast's retry button for `save_file`/`save_compressed` calls `self._save_file`
/`self._save_compressed` directly, which re-shows the `askyesno` overwrite-confirmation
dialog (or, for `_save_compressed`, the save-as file picker) on every retry, rather than
retrying the save silently. This isn't incorrect, but a user who already confirmed once
and hit a transient I/O failure will be asked to confirm again on each retry click,
which is a bit more friction than "retry" usually implies.
**Fix:** Consider a low-level retry entry point that skips the confirmation dialog when
invoked via the toast's retry callback (out of scope for this phase's stated goals;
noted for future polish only).

---

_Reviewed: 2026-07-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
