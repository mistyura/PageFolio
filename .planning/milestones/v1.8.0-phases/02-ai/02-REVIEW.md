---
phase: 02-ai
reviewed: 2026-07-15T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - pagefolio/dialogs/llm_config/dialog.py
  - pagefolio/dialogs/llm_config/sections.py
  - pagefolio/lang.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_fallback.py
  - pagefolio/settings.py
  - tests/test_ocr.py
  - tests/test_ocr_fallback.py
  - tests/test_prompt_templates.py
  - tests/test_provider_ui.py
findings:
  critical: 2
  warning: 5
  info: 1
  total: 8
status: issues_found
---

# Phase 02 (AI): Code Review Report — Fresh Independent Pass

**Reviewed:** 2026-07-15
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This is a fresh, independent pass over the current state of the files listed above — findings are re-derived from the code as it stands today, not copied from the prior `02-REVIEW.md`. Where a prior finding still reproduces in current code it is restated here (verified independently, not assumed); where a prior finding has actually been fixed, that is confirmed explicitly.

**Confirmed fixed:** the prior CR-02 (prompt-template save/delete/rename bypassing the Apply/Cancel contract via a shallow copy of `current_settings` + immediate `_save_settings()` calls) is now correctly resolved:
- `pagefolio/dialogs/llm_config/dialog.py:47-55` deep-copies `prompt_templates` (including nested `items`/per-template dicts) in `__init__`, isolating `self.current_settings` from the caller's live settings object.
- `pagefolio/dialogs/llm_config/sections.py`'s `_on_template_save`/`_on_template_delete`/`_on_template_rename` no longer call `_save_settings()` (verified via source grep — zero occurrences of `_save_settings` in `sections.py`); all three only mutate the deep-copied `self.current_settings`.
- `_on_template_delete` now gates on `messagebox.askyesno` before deleting (verified with a bound-method call: reproduced both the "No" → item survives and "Yes" → item removed paths).
- `_apply()` (`dialog.py:470-488`) collects `prompt_templates` (`active` + deep-copied `items`) exactly once for `on_apply`, restoring single-commit-on-Apply semantics. `tests/test_provider_ui.py::TestTemplateCancelContract` exercises this with real bound-method calls (`LLMConfigDialog._apply(stub)`), and the 02-06 gap-closure classes (`TestTemplateChangeFlow`, `TestTemplateNameValidationUI`, `TestTemplateDeleteButtonState`) exercise the D-03/D-04/D-05/D-07 handler state transitions the same way.

**Still open (verified by direct reproduction, not carried over blindly):** two issues from before this fresh pass still reproduce unchanged in the current code (CR-01 and WR-01 below), and this pass also surfaces two new defects (CR-02, and the settings-write robustness gap in WR-05) plus additional consistency gaps.

## Critical Issues

### CR-01: Tesseract-unavailable initial-provider guard is self-referential and silently disables the dialog's first paint

**File:** `pagefolio/dialogs/llm_config/dialog.py:68-72`, `dialog.py:164-180` (`_on_provider_change`), `pagefolio/dialogs/llm_config/sections.py:78-80, 1148-1149`

**Issue:** `__init__` initializes the "last known-good provider" guard directly from persisted settings, *before* Tesseract availability is known:
```python
# dialog.py:68-72
self._last_valid_provider = current_settings.get("ocr_provider", "off")
...
self._tesseract_available, self._tesseract_langs = _detect_tesseract()
```
`sections.py` initializes `self.provider_var` from the same source (`current_settings.get("ocr_provider", "off")`), and `_build()` unconditionally calls `self._on_provider_change()` once at the end to set up initial visibility. `_on_provider_change`'s Tesseract guard is:
```python
# dialog.py:169-178
if provider == "tesseract" and not self._tesseract_available:
    self.provider_var.set(self._last_valid_provider)
    self._set_lm_status(..., kind="fail")
    return
```
If a user previously selected Tesseract on a machine where it was installed, `pagefolio_settings.json` persists `"ocr_provider": "tesseract"`. Opening the dialog on a machine/session where Tesseract is *not* available (uninstalled, PATH changed, etc.) means both `provider_var` and `_last_valid_provider` start as `"tesseract"` — the "fallback" target is the same invalid value being rejected. The guard's `self.provider_var.set(self._last_valid_provider)` is a no-op, and the function `return`s early **before reaching any of the pack/pack_forget calls that build the rest of the dialog's initial layout** (common-settings heading, temperature/effort frames, Tesseract accuracy-warning frame, etc.).

Reproduced directly by invoking the real bound method with the exact state `__init__`/`_build` would produce in this scenario:
```
provider_var after call: tesseract
status calls: [('Tesseract is not installed. Please use another provider.',), {'kind': 'fail'}]
```
The combobox keeps showing the invalid `"tesseract"` selection and the entire "common settings" section (including the temperature control) never gets packed on first paint. The user must manually re-select any other provider to trigger normal layout — until then the dialog opens visibly broken.

**Fix:** Resolve the initial provider against Tesseract availability *after* detection, and before either `self.provider_var` or `self._last_valid_provider` is set:
```python
# dialog.py __init__, after self._tesseract_available is known
_initial_provider = current_settings.get("ocr_provider", "off")
if _initial_provider == "tesseract" and not self._tesseract_available:
    _initial_provider = "off"
self._last_valid_provider = _initial_provider
```
and use the same `_initial_provider` value (not `current_settings.get("ocr_provider", "off")` again) when constructing `self.provider_var` in `sections.py`, so the combobox and the guard's fallback target start in agreement.

### CR-02: `settings.py` prompt-template CRUD helpers crash with `KeyError` on a partially-shaped `prompt_templates` value

**File:** `pagefolio/settings.py:161-237` (`list_template_names`, `get_template`, `template_name_exists`, `save_template`, `delete_template`, `rename_template`); root cause in `_load_settings` at `pagefolio/settings.py:279-289`

**Issue:** Every template helper guards against `prompt_templates` being *entirely absent* with `settings.setdefault("prompt_templates", {"active": "", "items": {}})`. `dict.setdefault` is a no-op once the top-level key exists at all — even if its value is only partially shaped, e.g. `{"active": "foo"}` with no `"items"` key, or `{}`. `_load_settings()` performs the same shallow, top-level-only `setdefault` (`for k, v in defaults.items(): data.setdefault(k, v)`) and never normalizes an existing-but-malformed `prompt_templates` value.

Reproduced directly against the real function:
```
>>> from pagefolio.settings import list_template_names
>>> list_template_names({"prompt_templates": {"active": "foo"}})
KeyError: 'items'
```
`sections.py:841` calls `list_template_names(self.current_settings)` unconditionally while building the LLM settings dialog, and `settings.load_custom_prompt`/`load_summary_prompt` call `get_template` (same failure mode) whenever `prompt_templates["active"]` is truthy — i.e. every OCR run and every dialog open once a template has ever been made active. Any settings.json with a partially-shaped `prompt_templates` (hand edit, external tooling, a future migration, or a write interrupted mid-flight — see WR-05) turns into a hard crash on the OCR/LLM-config code path, with no exception handling anywhere upstream that catches it.

**Fix:** Normalize the nested shape defensively wherever `prompt_templates` is touched, e.g. a shared helper:
```python
def _ensure_template_shape(settings):
    tpl = settings.setdefault("prompt_templates", {"active": "", "items": {}})
    tpl.setdefault("active", "")
    tpl.setdefault("items", {})
    return tpl
```
and use `_ensure_template_shape(settings)` in place of the current `settings.setdefault("prompt_templates", ...)` + direct `["items"]`/`["active"]` indexing in `list_template_names`, `get_template`, `template_name_exists`, `save_template`, `delete_template`, and `rename_template`.

## Warnings

### WR-01: Fallback provider switch doesn't refresh the dialog's provider/model display or LM Studio field visibility

**File:** `pagefolio/ocr_dialog.py:808-849` (`_provider_display_name`, `_provider_model_name`), `pagefolio/ocr_dialog.py:305` (`show_lmstudio_fields`, evaluated once in `_build`), `pagefolio/ocr_dialog.py:2367-2418` (`_switch_to_fallback_provider`)

**Issue:** `_provider_display_name()` and `_provider_model_name()` both read `self.app.settings.get("ocr_provider", "")` — the *persisted* provider, not `self._active_ocr_settings` (the dialog-local fallback snapshot that `_switch_to_fallback_provider` builds and that is documented elsewhere as the source of truth during a fallback run, e.g. `_active_provider_name()` at `ocr_dialog.py:2272-2275` explicitly reads `self._active_ocr_settings or self.app.settings`). `_provider_display_name`'s `isinstance(self.provider, ClaudeProvider)` fallback doesn't rescue this either, since the `name == "claude"` branch short-circuits `or` before the isinstance check is reached whenever the persisted setting still says `"claude"`.

`_switch_to_fallback_provider` rebuilds `self.provider` for the candidate and re-clamps `self.concurrency`, but never calls `_refresh_provider_dependent_ui()` (the method that exists specifically to re-evaluate these two things after a provider change — see `_apply_llm_settings`, which does call it). Consequently:
- The "OCR プロバイダ:" / "モデル:" header labels keep showing the *original* provider/model after a silent fallback switch, even though the actual outbound request now targets a different vendor.
- If the fallback candidate is `lmstudio` (or vice versa, switching away from it), the LM Studio URL/model fields' visibility (`show_lmstudio_fields`, computed once in `_build()`) is never re-evaluated, so the fields that would let the user confirm/adjust the new destination stay hidden (or shown when they shouldn't be).

The initial `_propose_fallback` confirmation dialog itself does show the correct destination, so the user's *first* consent is informed — but the dialog's persistent header becomes misleading for the remainder of the run, undermining the "always show the destination" transparency goal the fallback feature is designed around.

**Fix:**
```python
# _switch_to_fallback_provider, immediately after self.provider is rebuilt
self._refresh_provider_dependent_ui()
```
and change `_provider_display_name`/`_provider_model_name` to read `self._active_ocr_settings or self.app.settings` (matching `_active_provider_name()`'s existing pattern) instead of `self.app.settings` unconditionally.

### WR-02: `_on_summary` aliases `app.settings` directly instead of defensively copying it like `_on_run`

**File:** `pagefolio/ocr_dialog.py:2024-2025` (contrast with `1328-1330`)

**Issue:** `_on_run` snapshots settings defensively:
```python
# ocr_dialog.py:1328-1330
self._active_ocr_settings = (
    settings if settings is not None else dict(self.app.settings)
)
```
`_on_summary`, which is documented with the identical "Pitfall 4: `self.app.settings` は一切書き換えない" invariant, instead does:
```python
# ocr_dialog.py:2024-2025
s = settings if settings is not None else self.app.settings
self._active_ocr_settings = s
```
When `_on_summary()` is called with no explicit `settings` (the normal "📊 サマリ作成" button path), `self._active_ocr_settings` becomes the *live* `self.app.settings` object rather than a copy. Nothing currently writes through `self._active_ocr_settings` in place, so there is no observable corruption today, but the asymmetry with `_on_run` removes the defensive copy that is the documented safety net for this exact invariant — a very natural future change (any code that does `self._active_ocr_settings[...] = ...`, which several nearby helpers already treat this attribute as a safe-to-mutate local snapshot) would silently mutate and persist changes to `app.settings`.

**Fix:**
```python
s = settings if settings is not None else dict(self.app.settings)
```

### WR-03: Template-switch "unsaved changes" confirmation is unguarded outside file-linked mode and when no template was previously active

**File:** `pagefolio/dialogs/llm_config/sections.py:1153-1175` (`_has_unsaved_template_changes`), `1196-1241` (`_on_template_change`)

**Issue:** `_on_template_change` always overwrites the custom/summary prompt text widgets with the newly-selected template's saved content once the (conditional) confirmation passes. `_has_unsaved_template_changes` only returns `True` (triggering the "discard unsaved changes?" dialog) when **both**:
1. at least one of `ocr_custom_prompt.md` / `ocr_summary_prompt.md` exists (file-linked mode), **and**
2. `self._active_template_name` is non-empty (a template was already active).

In the far more common scenario — no external prompt files linked, and no template selected yet in this session, but the user has typed a prompt directly into the text box — switching the template combo to load a saved template **silently discards the typed text with zero confirmation**, because condition 2 fails regardless of file-linking. This is a real, easily reachable data-loss path: type a custom prompt → decide to try a saved template from the dropdown → the typed prompt disappears with no warning. `tests/test_provider_ui.py::TestTemplateChangeFlow` (the 02-06 gap-closure tests) only exercises scenarios with a non-empty `active_template_name`, so this gap has no regression coverage.

**Fix:** Broaden the check so any non-empty pending edit is protected, independent of file-linking or a pre-existing active template:
```python
def _has_unsaved_template_changes(self, current_custom, current_summary):
    if not self._active_template_name:
        # No prior active template: still warn if there is unsaved free-form text
        return bool(current_custom.strip() or current_summary.strip())
    if not (prompt_file_exists(CUSTOM_PROMPT_FILE) or prompt_file_exists(SUMMARY_PROMPT_FILE)):
        return False
    ...
```
(adjust to preserve the existing file-linked-mode semantics for the "active template present" branch). Add a regression test with `active_template_name=""` and non-empty `custom_text`/`summary_text` asserting `askyesno` fires and a `False` response preserves the typed text.

### WR-04: Fallback confirmation dialog shows the raw internal provider key instead of a localized display name

**File:** `pagefolio/ocr_dialog.py:2334-2346` (`_propose_fallback`)

**Issue:** Everywhere else in the dialog, the active provider is shown via `_provider_display_name()` (e.g. `"Claude (Anthropic)"`, `"Gemini (Google AI)"`, `"RunPod (Serverless)"`). The fallback confirmation dialog instead formats `fallback_confirm_msg` with the raw internal candidate identifier:
```python
self._L["fallback_confirm_msg"].format(
    reason=self._L[reason_key],
    candidate=candidate,          # e.g. "gemini", "runpod", "tesseract" — not localized
    host=self._fallback_candidate_host(candidate),
)
```
This inconsistency is locked in rather than caught by the test suite: `tests/test_ocr_fallback.py::TestSummaryFallback::test_summary_excludes_tesseract_candidate` explicitly asserts the raw string `"gemini"` appears in the confirmation message.

**Fix:** Add a small `name → display name` lookup parameterized by provider (factoring the mapping already inside `_provider_display_name()`), and use it for `candidate` when formatting `fallback_confirm_msg`; update the corresponding test assertion to match.

### WR-05: `_save_settings` performs a non-atomic write, widening the crash surface described in CR-02

**File:** `pagefolio/settings.py:292-311`

**Issue:** `_save_settings` writes directly to the target path (`with open(path, "w", ...) as f: json.dump(...)`) with no temp-file-plus-`os.replace` pattern. A process kill, power loss, or full disk mid-write can leave `pagefolio_settings.json` truncated or otherwise structurally incomplete. Most truncations raise `JSONDecodeError`, which `_load_settings`'s broad `except Exception` already tolerates by falling back to full in-memory defaults — but a write that succeeds up to a JSON-structurally-valid-yet-semantically-incomplete point (plausible given `json.dump`'s internal buffering/flush behavior on a multi-key document) can produce exactly the "`prompt_templates` present but missing `items`" shape that CR-02 shows crashes the app.

**Fix:** Write-then-rename for atomicity:
```python
tmp_path = path + ".tmp"
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(to_save, f, ensure_ascii=False, indent=2)
os.replace(tmp_path, path)
```
This guarantees the on-disk file is always either the fully-old or fully-new version, never a partial write — independent of, and complementary to, the CR-02 fix.

## Info

### IN-01: Unknown-cloud-provider API-key-missing message falls back to Claude-specific wording

**File:** `pagefolio/ocr_dialog.py:1283-1290` (`_check_cloud_api_key`)

**Issue:**
```python
msg_key = {
    "claude": "ocr_api_key_missing",
    "gemini": "ocr_api_key_missing_gemini",
    "runpod": "ocr_api_key_missing_runpod",
}.get(name, "ocr_api_key_missing")
```
For a provider name outside these three (currently unreachable through the built-in `_is_cloud_provider` isinstance checks, but reachable if a plugin raises `OCRAPIKeyError` through this path), the fallback message text is the Claude-specific wording — only the `{env_var}` placeholder is generic. Impact is low today since this branch is not reachable via the built-in providers, but it is a latent wording bug for plugin-provided cloud OCR providers.

**Fix:** Low priority. If/when plugin-provided cloud providers are expected to hit this path, add a genuinely generic fallback message key rather than reusing `ocr_api_key_missing`.

---

_Reviewed: 2026-07-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
