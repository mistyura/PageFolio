---
phase: 05-blob-shortcutsdialog
reviewed: 2026-07-16T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - pagefolio/app.py
  - pagefolio/constants.py
  - pagefolio/dialogs/shortcuts.py
  - pagefolio/pagination.py
  - pagefolio/thumb_cache.py
  - pagefolio/ui_builder.py
  - pagefolio/undo_store.py
  - pagefolio/viewer.py
  - tests/test_pagination.py
  - tests/test_selection_invariant.py
  - tests/test_shortcuts_dialog.py
  - tests/test_thumb_cache.py
  - tests/test_undo_stress.py
  - tests/test_viewer.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-07-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the pagination virtualization layer (`pagination.py`), the new LRU thumbnail
cache (`thumb_cache.py`), the ShortcutsDialog real-key-capture UI (`dialogs/shortcuts.py`)
together with its focus-guard integration in `app.py`, and the undo Blob leak-detection
additions in `undo_store.py`, plus their respective test suites.

The pure-logic modules (`pagination.py`, `thumb_cache.py`) are well-covered by
property-style tests and I could not find a correctness defect in them — every
boundary case I traced (fractional last window, window-follow, LRU eviction/recency,
visible-range clamping) matches the implementation exactly.

I traced the undo/redo Blob ownership handshake across `undo_store.py` and
`file_ops.py._apply_inverse`/`_restore_state` (the "is not" identity check that
decides whether a consumed state's Blobs may be released) for the specific
delete/insert/page_edit chains and did not find a double-release or
premature-release path — the design holds up under the "insert→undo→redo→undo"
stress scenario the tests exercise.

No Critical-severity issues (security, data loss, crash) were found. The issues
below are Warning/Info-level robustness and quality gaps: an inconsistent
post-release failure mode between `MemBlob`/`FileBlob`, an incomplete
input-widget allowlist in the new shortcut focus guard, a stale dead constant
carried over from a prior phase review that still hasn't been removed, a
duplicate-shortcut detector that doesn't account for auto-generated Shift-variant
bindings, and a memory-threshold test that is a latent flakiness risk.

## Warnings

### WR-01: `MemBlob` and `FileBlob` fail differently when used after `release()`

**File:** `pagefolio/undo_store.py:50-64` (MemBlob) and `pagefolio/undo_store.py:92-108` (FileBlob)

**Issue:** `MemBlob.release()` sets `self._data = b""`, so a subsequent `load()` call
silently returns empty bytes with no error. `FileBlob.release()` unlinks the backing
temp file, so a subsequent `load()` call raises `FileNotFoundError` (an uncaught,
loud exception). Both classes exist to be interchangeable via the shared `load()`/
`release()` contract described in the module docstring ("release 後の load は不正"),
but a hypothetical use-after-release bug (e.g. a future regression in the
`_dispose_state`/"is not" identity-sharing logic in `file_ops.py`) would manifest
as **silent PDF corruption** for small pages (MemBlob, <64KiB) and a **hard crash**
for large pages (FileBlob, ≥64KiB) — the failure mode would depend purely on
page byte size, making such a regression very hard to reproduce/diagnose
consistently across test fixtures (the stress tests use large noise-image pages
that always route to FileBlob, so a MemBlob-side regression of this kind would
not be caught by the existing `test_undo_stress.py` suite).

**Fix:** Make `MemBlob.load()` raise consistently with `FileBlob.load()` after
release, e.g.:
```python
def load(self):
    if self._released:
        raise RuntimeError("MemBlob.load() called after release()")
    return self._data
```

### WR-02: Shortcut focus-guard allowlist omits editable Combobox widgets

**File:** `pagefolio/app.py:91` (`_INPUT_WIDGET_CLASSES`), `pagefolio/app.py:94-106`
(`should_suppress_for_focused_input`)

**Issue:** `_INPUT_WIDGET_CLASSES = {"Entry", "TEntry", "Spinbox", "TSpinbox", "Text"}`
is the complete list of widget classes for which unmodified/Shift-only shortcuts are
suppressed while typing. `ttk.Combobox` (winfo_class `"TCombobox"`) is a common
editable-text input widget (used elsewhere in the codebase, e.g.
`dialogs/llm_config/sections.py`, `dialogs/batch_ocr.py`) and is not in this set.
Today this is low-risk because all current Combobox usages live inside separate
`Toplevel` dialogs, where `self.root.bind(...)` sequences do not fire (a Toplevel
has its own bindtag chain distinct from `root`). However, the function's stated
purpose is general "input widget" protection (V180-ROBUST-03·D-09/D-10), and if a
Combobox is ever added directly to the main window (not a dialog), the same class
of bug this guard was built to fix (WR-02: unmodified single-key shortcuts firing
while the user is typing) would resurface silently, with no test coverage to catch
it since `_INPUT_WIDGET_CLASSES` is a hardcoded allowlist rather than a
capability check.

**Fix:** Add `"TCombobox"` (and plain `"Combobox"` for non-ttk callers) to
`_INPUT_WIDGET_CLASSES`, or better, detect input-capable widgets by checking for a
`get`/`selection_range` API rather than an explicit class-name allowlist.

### WR-03: Hardcoded 20MB heap-growth threshold is a flakiness risk

**File:** `tests/test_undo_stress.py:144-180` (`test_memory_and_blob_invariants`)

**Issue:** The test asserts `heap_growth < 20 * 1024 * 1024` based on
`tracemalloc.get_traced_memory()` deltas across 30 undo/redo cycles. Python heap
growth measured this way is sensitive to GC timing, interpreter version, and
whatever else is resident in the process during a CI run — this is a well-known
source of intermittent test flakiness for tracemalloc-based memory assertions.
The test file's own docstring already acknowledges the Blob-file-count invariant
(asserted immediately above via `_blob_files(app) <= live_states * len(targets)`)
is the "primary" leak-detection signal and calls the heap-growth check merely
"補完的な緩い上限" (a supplementary loose bound) — but it is still a hard `assert`
that can fail the whole test/CI run on an unrelated environment hiccup.

**Fix:** Either drop the heap-growth assertion (rely solely on the Blob-file-count
invariant, which is deterministic) or convert it to a non-fatal warning/log so a
transient heap spike does not fail CI for reasons unrelated to a real leak.

## Info

### IN-01: Dead constant `_SHORTCUT_MOD_ORDER` still unremoved

**File:** `pagefolio/app.py:54`

**Issue:** `_SHORTCUT_MOD_ORDER = ("Control", "Alt", "Shift")` is defined but never
referenced anywhere in the codebase — `build_keysym_from_event` (`app.py:57-74`)
hardcodes the same Control→Alt→Shift check order manually instead of iterating this
tuple. This exact dead-code finding was already reported in
`.planning/milestones/v1.7.1-phases/04-ui-ux/04-REVIEW.md` (IN-01) and has not been
addressed since.

**Fix:** Either remove the constant, or refactor `build_keysym_from_event` to
iterate `_SHORTCUT_MOD_ORDER` with its corresponding mask tuple so the constant is
actually load-bearing.

### IN-02: Duplicate-shortcut check ignores auto-generated Shift-variant bindings

**File:** `pagefolio/app.py:44-51` (`shift_variant_keysym`), `pagefolio/app.py:77-88`
(`find_duplicate_binding`), `pagefolio/dialogs/shortcuts.py:225-233,261-272`

**Issue:** `_bind_shortcuts` auto-binds an extra Shift-variant keysym (e.g.
`<Control-o>` → also binds `<Control-O>`) for any command whose keysym matches
`<Control-<lowercase>>`. `find_duplicate_binding`, used both during live key-capture
in `ShortcutsDialog._on_capture_keypress` and at `_on_save`, only compares the
literal stored keysym strings in `self._shortcuts`, never the derived Shift
variants. As a result, a user can assign a command (e.g. a rotate command, which is
always processed last due to dict-merge ordering) to a keysym that coincides with
another command's auto-generated Shift-variant without any duplicate-binding
warning; the two bindings silently race in `_bind_shortcuts`'s bind order and the
later one wins. In every ordering this codebase currently produces, the discarded
binding is always the undocumented "bonus" Shift-variant alias rather than a user's
primary assigned key, so the practical impact is low — but it is a real gap between
what the duplicate-detection UI promises ("no two commands share a key") and what
it actually checks.

**Fix:** Compute both the literal keysym and its `shift_variant_keysym` (if any)
for every existing command and check candidates against the full expanded set
before reporting "no duplicate".

---

_Reviewed: 2026-07-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
