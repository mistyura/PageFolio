---
phase: 03-ocr-e2e
reviewed: 2026-07-15T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_engine.py
  - tests/test_ocr.py
  - tests/test_ocr_engine.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-07-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 03-01 extracted the producer-consumer consumer-side logic from `OCRDialog`
into a new `OCRRunEngine` class (`pagefolio/ocr_engine.py`), and turned the
corresponding `OCRDialog` methods (`_start_worker_thread`, `_worker`,
`_done_disp`) into thin delegating wrappers. I traced the full extraction
against the pre-refactor implementation (`git diff 5330b60 d8c9e2c`) and
verified the delegation is behaviorally faithful for the paths I could trace
statically: queue/`PipelineState` single-instance ownership, sentinel/cancel/
fatal handling, generation-guarded `after()` dispatch, and the
`_safe_finish_*` `winfo_exists()` guards (which are actually a correctness
*improvement* over the old code, which scheduled `_render_results_ordered`/
`_finish_complete` via two independent `after(0, ...)` calls with no
existence check at execution time).

No BLOCKER-severity defects were found in the delegation itself. However, the
new `OCRRunEngine` introduces some quality/robustness regressions worth
fixing: an unguarded exception path in the worker loop that can silently hang
the dialog, dead/duplicated state that shadows `OCRDialog`'s own bookkeeping,
and a stale comment that overstates the actual thread-safety guarantees of
the shared result dictionaries. Test coverage for the new `OCRRunEngine`
(`tests/test_ocr_engine.py`) is solid for the happy path, page-error path,
cancellation, and circuit-breaker path, but does not exercise the failure
mode described in WR-01 below.

## Warnings

### WR-01: `_worker_loop` has no exception guard around callbacks — a bug in a callback can hang the engine forever

**File:** `pagefolio/ocr_engine.py:194-227`

**Issue:** `_worker_loop`'s `while True:` body calls `consume_one(...)` and then
(outside the `try/finally` that only covers `del b64`) `self._on_progress(...)`.
Neither call is wrapped in a broad `except Exception`. `consume_one` itself
catches all exceptions raised by `provider.ocr_image_ex`, but it does **not**
catch exceptions raised by the `on_success`/`on_page_error` callbacks it
invokes (`ocr_pipeline.py:230-238`) — those callbacks are `OCRRunEngine._handle_success`/
`_handle_page_error`, which in turn synchronously call the *dialog's* own
`_record_page_success`/`_record_page_error` methods (wired in
`ocr_dialog.py:1683-1684`). Similarly, `self._on_progress(...)`
(`ocr_engine.py:221-222`) is called unguarded.

If any of these callbacks raises (e.g. a future edit introduces a bug in
`_record_page_success`, or a downstream lambda throws), the exception
propagates out of `_worker_loop` entirely, **skipping the
`self._pstate.decrement_worker()` call at the end of the method
(`ocr_engine.py:225`)**. Since `decrement_worker()` is the sole mechanism that
detects "last worker done" and fires `on_complete`/`on_cancelled`/`on_fatal`,
a single unhandled exception in one worker permanently prevents the engine
from ever reaching `workers_remaining == 0` (unless every other worker also
happens to hit the same fault). The dialog is left with the progress bar
frozen, the Cancel button enabled but non-functional (cancelling won't help —
the dead worker never observes it because it's already gone), and no error
surfaced to the user. The only recovery is closing the dialog.

This mirrors an equivalent gap in the pre-refactor `_worker` method, but since
`OCRRunEngine` is new code introduced in this phase and is explicitly
designed for reuse by a future batch-OCR feature (per the module docstring),
this is the right time to close the gap rather than propagate it into a
second call site.

**Fix:** Wrap the callback-invoking portion of the loop body in a
catch-all that treats an unexpected callback exception as a page error
(so the worker still reaches `decrement_worker()`), e.g.:

```python
page_idx, b64 = item
try:
    consume_one(
        self.provider, item, self.prompt, self._pstate,
        cancel_check=self.cancel_flag.is_set,
        breaker_threshold=self._breaker_threshold,
        on_success=self._handle_success,
        on_page_error=self._handle_page_error,
        on_retry_wait=self._handle_retry_wait,
    )
    if self._on_progress is not None:
        self._on_progress(self.progress_count(), page_idx)
except Exception:
    logger.exception("OCR ワーカーのコールバック処理中に予期しない例外 (p.%d)", page_idx)
finally:
    del b64
```

Also add a regression test (in `tests/test_ocr_engine.py`) asserting that
`on_complete`/`on_cancelled`/`on_fatal` still fires exactly once even when
`on_success` raises.

### WR-02: `OCRRunEngine.results` / `.errors` / `.truncated_pages` are dead, divergent state

**File:** `pagefolio/ocr_engine.py:100-105, 161-177`

**Issue:** The docstring (lines 50-54) claims "D-09:
`results`/`errors`/`truncated_pages`/`skipped_pages`/`render_failed_pages` は
本クラスが内部状態として所有する" (this class owns these as internal state).
In practice, `skipped_pages`/`render_failed_pages` are genuinely load-bearing
(consumed by `progress_count()`), but `results`, `errors`, and
`truncated_pages` are write-only from the production code path: they are
populated in `_handle_success`/`_handle_page_error`
(`ocr_engine.py:161-177`), but nothing in `pagefolio/ocr_dialog.py` ever
reads `self._engine.results`, `self._engine.errors`, or
`self._engine.truncated_pages` (verified via grep — the only readers are
`tests/test_ocr_engine.py` assertions). `OCRDialog` maintains its own
independent copies of the same information (`self.results`, `self.errors`,
`self._truncated_pages`) via the wrapped callbacks
(`ocr_dialog.py:760-786`, wired at `ocr_dialog.py:1683-1684`).

This means every OCR run now maintains **two parallel copies** of the same
result/error data that must be kept in sync purely by convention (both sides
happen to be updated by the same callback chain today). A future change to
one side (e.g. clearing `OCRDialog.results` on cancel/resume without also
resetting `self._engine`, or vice versa) will silently desync them, and
because `self._engine.results` is never read by the dialog, such a bug would
not be caught by any assertion on displayed output — only by a test that
inspects `self._engine.results` directly (which is exactly what happened
here: the *tests* assert on `engine.results`, but the *application* never
looks at it).

**Fix:** Either (a) make `OCRDialog` read the ordered results directly from
`self._engine.results`/`.errors`/`.truncated_pages` instead of maintaining
its own shadow dicts (removing `_record_page_success`/`_record_page_error`
as bookkeeping methods and keeping them only as thin `on_*` wiring, or
removing them entirely), or (b) if the duplication is intentional for
backward-compat reasons, document explicitly in the class docstring that
`OCRRunEngine.results`/`.errors`/`.truncated_pages` are informational/test-only
and are not the source of truth consumed by the application, so future
maintainers don't assume otherwise.

### WR-03: Comment claims "Lock 保護" for shared result dicts, but no lock exists anywhere

**File:** `pagefolio/ocr_dialog.py:758`

**Issue:** The section header comment reads:
`# ── ページ結果記録（ワーカースレッドから呼ばれる・Lock 保護） ──`
("called from worker thread, lock-protected"). There is no `threading.Lock`
anywhere in `pagefolio/ocr_dialog.py` or `pagefolio/ocr_engine.py` guarding
`self.results`, `self.errors`, or `self._truncated_pages` (confirmed via
grep — the only lock in the whole OCR pipeline is `PipelineState._lock` in
`ocr_pipeline.py`, which only protects the numeric counters, not these
dicts/sets). `_record_page_success`/`_record_page_error` are invoked
synchronously from `OCRRunEngine._worker_loop` running on background
consumer threads (not dispatched via `self.after(0, ...)`), so these dict/set
mutations do happen from multiple threads. Correctness today relies entirely
on (1) CPython's GIL making single dict/set key operations atomic, and (2)
each worker thread only ever touching a disjoint `page_idx` key — an
invariant that is true today but is not enforced or even stated anywhere near
the code that depends on it.

**Fix:** Correct the comment to state the actual safety argument (GIL +
disjoint keys), e.g. `# ワーカースレッドから呼ばれる（GIL + page_idx 排他により
ロック不要。共有辞書への同一キー同時書込みが発生する変更を今後加える場合は
要 Lock 追加）`, so a future change that introduces same-key concurrent writes
(e.g. a shared aggregate counter) doesn't inherit a false sense of security
from the existing comment.

## Info

### IN-01: Unused `logger` in `pagefolio/ocr_engine.py`

**File:** `pagefolio/ocr_engine.py:39`

**Issue:** `logger = logging.getLogger(__name__)` is defined at module level
but never referenced anywhere else in the file (confirmed via grep for
`logger\.`). This is dead code / an unused binding.

**Fix:** Either use it (e.g. in the exception handler suggested in WR-01) or
remove the unused `logging` import and `logger` assignment.

---

_Reviewed: 2026-07-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
