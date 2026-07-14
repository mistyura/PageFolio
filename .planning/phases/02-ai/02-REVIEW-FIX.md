---
phase: 02-ai
fixed_at: 2026-07-14T15:24:28Z
review_path: .planning/phases/02-ai/02-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 02 (AI): Code Review Fix Report

**Fixed at:** 2026-07-14T15:24:28Z
**Source review:** .planning/phases/02-ai/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (CR-01, CR-02, WR-01〜WR-05; fix_scope=critical_warning, IN-01 out of scope)
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: Tesseract-unavailable initial-provider guard is self-referential and silently disables the dialog's first paint

**Files modified:** `pagefolio/dialogs/llm_config/dialog.py`, `pagefolio/dialogs/llm_config/sections.py`
**Commit:** d8af0ad
**Applied fix:** `dialog.py.__init__` now calls `_detect_tesseract()` first, then computes `_initial_provider` from `current_settings.get("ocr_provider", "off")`, falling back to `"off"` if it is `"tesseract"` and Tesseract is unavailable. This resolved value is stored both as `self._initial_provider` (new attribute) and `self._last_valid_provider`. `sections.py`'s `provider_var` StringVar now initializes from `self._initial_provider` instead of re-reading the raw `current_settings` value, so the combobox and the `_on_provider_change` guard's fallback target always agree from first paint. Verified by reproducing the reviewer's scenario logic directly (`current_settings={"ocr_provider": "tesseract"}`, `_tesseract_available=False` → `_initial_provider`/`_last_valid_provider` both resolve to `"off"`, eliminating the self-referential early return).

### CR-02: `settings.py` prompt-template CRUD helpers crash with `KeyError` on a partially-shaped `prompt_templates` value

**Files modified:** `pagefolio/settings.py`
**Commit:** 794566d
**Applied fix:** Added `_ensure_template_shape(settings)` helper that normalizes both the top-level `prompt_templates` key (via `setdefault`) and its nested `active`/`items` keys individually. Replaced the shallow `settings.setdefault("prompt_templates", ...)` + direct indexing in `list_template_names`, `get_template`, `template_name_exists`, `save_template`, `delete_template`, and `rename_template` with calls to this shared helper. Verified directly: `list_template_names({"prompt_templates": {"active": "foo"}})` now returns `[]` instead of raising `KeyError: 'items'`, and `get_template({"prompt_templates": {}}, "x")` returns `None`.

### WR-01: Fallback provider switch doesn't refresh the dialog's provider/model display or LM Studio field visibility

**Files modified:** `pagefolio/ocr_dialog.py`, `tests/test_ocr_fallback.py`
**Commit:** 8bd3932
**Applied fix:** `_provider_display_name()` and `_provider_model_name()` now read `getattr(self, "_active_ocr_settings", None) or self.app.settings` (matching `_active_provider_name()`'s existing pattern) instead of `self.app.settings` unconditionally. `_switch_to_fallback_provider` now calls `self._refresh_provider_dependent_ui()` immediately after rebuilding `self.provider` and re-clamping concurrency, so the header labels and LM Studio field visibility are re-evaluated after every fallback switch. The headless test harness `_make_dialog` in `tests/test_ocr_fallback.py` was updated to stub `_refresh_provider_dependent_ui` as a no-op (matching the method's own documented "テストでは no-op に差し替え可能" contract), since headless test instances never call `_build()` and have no real Tk widgets to update.

### WR-02: `_on_summary` aliases `app.settings` directly instead of defensively copying it like `_on_run`

**Files modified:** `pagefolio/ocr_dialog.py`
**Commit:** 7c2c8d7
**Applied fix:** Changed `s = settings if settings is not None else self.app.settings` to `s = settings if settings is not None else dict(self.app.settings)` in `_on_summary`, matching `_on_run`'s existing defensive-copy pattern and restoring the "self.app.settings は一切書き換えない" invariant's safety net.

### WR-03: Template-switch "unsaved changes" confirmation is unguarded outside file-linked mode and when no template was previously active

**Files modified:** `pagefolio/dialogs/llm_config/sections.py`, `tests/test_provider_ui.py`
**Commit:** 61e4c75
**Applied fix:** Restructured `_has_unsaved_template_changes` so that when `self._active_template_name` is empty, it returns `bool(current_custom.strip() or current_summary.strip())` (warns on any typed free-form text regardless of file-linked mode), instead of unconditionally returning `False`. The existing file-linked-mode + active-template-present branch semantics are preserved unchanged for the case where a template was previously active. Added regression test `TestTemplateChangeFlow::test_no_active_template_warns_on_unsaved_freeform_text` covering `active_template_name=""` with non-empty typed text, asserting `askyesno` fires and a `False` response preserves the typed text and blocks the switch.

### WR-04: Fallback confirmation dialog shows the raw internal provider key instead of a localized display name

**Files modified:** `pagefolio/ocr_dialog.py`, `tests/test_ocr_fallback.py`
**Commit:** 5330b60
**Applied fix:** Added `_provider_key_to_display_name(name)` helper — a string-only (no `isinstance` check) version of the mapping already inside `_provider_display_name()` — and used it to format the `candidate` placeholder in `_propose_fallback`'s `fallback_confirm_msg`. Updated `tests/test_ocr_fallback.py::TestSummaryFallback::test_summary_excludes_tesseract_candidate` to assert the localized display name (`d._L["ocr_provider_name_gemini"]`, i.e. "Gemini (Google AI)") appears in the confirmation message instead of the raw lowercase `"gemini"` string.

### WR-05: `_save_settings` performs a non-atomic write, widening the crash surface described in CR-02

**Files modified:** `pagefolio/settings.py`
**Commit:** c2ea4ec
**Applied fix:** `_save_settings` now writes to a temp path (`path + ".tmp"`) and uses `os.replace(tmp_path, path)` for an atomic rename, instead of writing directly to the target path. This guarantees the on-disk settings file is always either fully the old or fully the new content, never a partial/truncated write.

## Skipped Issues

None — all 7 in-scope findings were fixed.

---

_Fixed: 2026-07-14T15:24:28Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
