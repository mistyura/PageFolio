---
phase: 03-ocr-e2e
fixed_at: 2026-07-15T00:30:00Z
review_path: .planning/phases/03-ocr-e2e/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-07-15T00:30:00Z
**Source review:** .planning/phases/03-ocr-e2e/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03; fix_scope=critical_warning excludes IN-01)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `_worker_loop` has no exception guard around callbacks — a bug in a callback can hang the engine forever

**Files modified:** `pagefolio/ocr_engine.py`, `tests/test_ocr_engine.py`
**Commit:** `62c9c86`
**Applied fix:** Wrapped the `consume_one(...)` call and the subsequent
`self._on_progress(...)` call in `OCRRunEngine._worker_loop` in a single
`try/except Exception` block that logs via `logger.exception(...)` and lets
execution fall through to `finally: del b64`, so the loop always reaches
`self._pstate.decrement_worker()` even if a success/error/progress callback
raises. This matches the fix suggested in REVIEW.md, adapted to keep the
`on_progress` call inside the guarded region (the review's snippet already
included it) and to route the exception message through the previously-unused
module `logger` (this also resolves IN-01 as a side effect, per the task
instructions).

Added a regression test,
`TestOCRRunEngineE2E.test_on_success_exception_still_reaches_on_complete`, in
`tests/test_ocr_engine.py`: an `on_success` callback that always raises
`ValueError`, run through 3 pages at concurrency=2, asserting `on_complete`
still fires exactly once. Verified the test fails without the fix (by
reasoning about the pre-fix code path — the unhandled exception would
propagate out of `_worker_loop` before `decrement_worker()`, so `on_complete`
would never fire and the test would time out/fail) and passes with the fix
applied (confirmed: `pytest tests/test_ocr_engine.py -q` → 10 passed).

### WR-02: `OCRRunEngine.results` / `.errors` / `.truncated_pages` are dead, divergent state

**Files modified:** `pagefolio/ocr_engine.py`
**Commit:** `793244e`
**Applied fix:** Chose REVIEW.md's option (b) — documented the duplication
explicitly rather than restructuring `OCRDialog` to read from the engine
(option (a)), since option (a) would require removing/rewiring
`_record_page_success`/`_record_page_error` and their callback wiring in
`pagefolio/ocr_dialog.py`, a materially larger change with more regression
surface than appropriate for an atomic warning-level fix. Extended the
`OCRRunEngine` class docstring (near the existing D-09 note) to state plainly
that `skipped_pages`/`render_failed_pages` are load-bearing (consumed by
`progress_count()`) while `results`/`errors`/`truncated_pages` are currently
write-only from the production code path — informational/test-only state,
not the source of truth consumed by the application (`OCRDialog` maintains
its own independent copies) — and to flag that future changes to the
`OCRDialog`-side copies will not automatically keep this state in sync.

### WR-03: Comment claims "Lock 保護" for shared result dicts, but no lock exists anywhere

**Files modified:** `pagefolio/ocr_dialog.py`
**Commit:** `557a8e8`
**Applied fix:** Replaced the misleading `# ── ページ結果記録（ワーカースレッドから呼ばれる・Lock 保護） ──`
section-header comment above `_record_page_success`/`_record_page_error`
(`pagefolio/ocr_dialog.py:758`) with the actual safety argument (GIL +
disjoint `page_idx` keys make single-key dict/set mutation safe without an
explicit lock), and added a note that introducing same-key concurrent writes
in the future would require adding a real `threading.Lock`. Matches the fix
text proposed in REVIEW.md, condensed to fit the existing comment style.

## Skipped Issues

None — all in-scope findings were fixed.

## Notes

- IN-01 (`Unused logger in pagefolio/ocr_engine.py`) was out of scope for this
  run (`fix_scope=critical_warning`), but is resolved as a side effect of the
  WR-01 fix: `logger.exception(...)` is now called from `_worker_loop`'s new
  exception handler, so `logger = logging.getLogger(__name__)` (line 39) is
  no longer dead code. No separate action was taken for IN-01.
- Verification performed after each fix: syntax check
  (`python -c "import ast; ast.parse(...)"`), `ruff check` + `ruff format --check`
  on modified files, and targeted `pytest` runs
  (`tests/test_ocr_engine.py`, `tests/test_ocr.py`). After all three fixes,
  a full-project `ruff check .` / `ruff format --check .` and full `pytest -q`
  run were performed as a final sanity pass: 997 passed, 0 failed.

---

_Fixed: 2026-07-15T00:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
