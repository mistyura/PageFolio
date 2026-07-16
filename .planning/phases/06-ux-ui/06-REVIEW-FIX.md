---
phase: 06-ux-ui
fixed_at: 2026-07-16T12:11:00Z
review_path: .planning/phases/06-ux-ui/06-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-07-16T12:11:00Z
**Source review:** .planning/phases/06-ux-ui/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (critical_warning scope — IN-01 excluded)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `_center()`'s new screen-height clamp in ocr_dialog.py is neutralized by `self.minsize(960, 620)`

**Files modified:** `pagefolio/ocr_dialog.py`, `tests/test_ocr_dialog_center.py`
**Commit:** e2c85e0
**Applied fix:** Raised the screen-height clamp floor in `_center()` from `320` to `620`
(`max_h = max(620, self.winfo_screenheight() - 100)`), matching the dialog's own
`self.minsize(960, 620)` call. This ensures the y-position calculation
(`py - h // 2`) is computed against the same height Tk will actually enforce, so
`minsize()` no longer silently grows the window past the position the clamp
intended, which previously pushed the dialog's bottom edge off-screen on short
displays.

Added a new regression test file `tests/test_ocr_dialog_center.py` that calls the
real `_center()` method against a lightweight `tk.Toplevel` (bypassing the heavy
`OCRDialog.__init__`) with `winfo_screenheight`/`_font_size` monkeypatched, and a
`geometry()` spy to capture the height Tk was asked for. Verified empirically that
this test fails against the pre-fix code (`h=500 < 620`) and passes against the
fix, plus an additional test confirming large screens still get the full
uncompressed height (680) as before.

### WR-02: `PluginDialog`'s `<Destroy>`-bound wheel-unbind fires on every child-row destroy, not just dialog close

**Files modified:** `pagefolio/dialogs/plugin.py`, `tests/test_plugin_dialog_wheel.py`
**Commit:** 8b4c423
**Applied fix:** Guarded the `<Destroy>` handler bound on the `PluginDialog`
Toplevel so it only calls `_unbind_wheel()` when the event's widget is the dialog
itself (`e.widget is self`), preventing the bindtag-propagated `<Destroy>` events
fired by every destroyed child row (e.g. during `_refresh_list()`/`_rescan()`)
from globally unbinding `<MouseWheel>`/`<Button-4>`/`<Button-5>`.

Added a new regression test file `tests/test_plugin_dialog_wheel.py` with two
tests: one that simulates `<Enter>` to bind the global wheel handlers, calls the
real `_rescan()` (which destroys and rebuilds child rows), and asserts the global
`<MouseWheel>` binding survives; another that confirms the guard is not overly
broad — destroying the dialog itself still unbinds the global handler as
intended. Verified empirically that the first test fails against the pre-fix
code and passes against the fix.

### WR-03: `ToastManager.show()` silently drops an updated `retry_cb` when re-showing the same active category

**Files modified:** `pagefolio/toast.py`, `tests/test_toast.py`
**Commit:** f3224a1
**Applied fix:** `ToastManager` now keeps a reference to the retry button
(`self._retry_btn`, set in `_build_frame()` and cleared in `_destroy_frame()`).
When `show()` is called again for the same active category, it now reconfigures
`self._retry_btn`'s `command` to the newly passed `retry_cb` in addition to
updating the message text, so the "再試行" button always invokes the most
recently supplied callback.

Added a regression test (`test_same_category_reshow_rebinds_retry_cb`) to the
existing `tests/test_toast.py` that shows the same category twice with two
distinct callbacks, invokes the retry button, and asserts only the second
callback fired. Verified empirically that this test fails against the pre-fix
code (old callback fires, or in this case no callback fires since the new one
was dropped) and passes against the fix.

## Skipped Issues

None — all in-scope findings (WR-01, WR-02, WR-03) were fixed. IN-01 was excluded
from this run per `fix_scope: critical_warning`.

**Verification performed for all fixes:**
- Tier 1 (re-read): confirmed for all three files.
- Tier 2 (syntax): `python -c "import ast; ast.parse(...)"` passed for all three
  modified source files.
- `ruff check .` and `ruff format --check .`: all checks passed (87 files
  formatted) after all fixes.
- Full `pytest` suite: 1101 passed (0 failed) after all fixes, including the 6
  new/added regression tests (2 in `test_ocr_dialog_center.py`, 2 in
  `test_plugin_dialog_wheel.py`, 1 new test in `test_toast.py`, plus the
  pre-existing 15 `test_toast.py` tests continuing to pass).
- Each new regression test was additionally confirmed to *fail* against the
  pre-fix source (via a throwaway revert-and-restore check) to validate it
  actually detects the defect described in REVIEW.md, not just superficially
  pass.

---

_Fixed: 2026-07-16T12:11:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
