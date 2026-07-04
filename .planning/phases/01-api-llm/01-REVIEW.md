---
phase: 01-api-llm
reviewed: 2026-07-05T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - pagefolio/app.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/dialogs/settings.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - tests/test_ocr.py
  - tests/test_provider_ui.py
findings:
  critical: 1
  warning: 4
  info: 0
  total: 5
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This phase moves API-key entry for cloud OCR providers (Claude / Gemini / RunPod)
out of `OCRDialog` and into a single, always-available section of
`LLMConfigDialog`, and flips the `_resolve_api_key` priority so a live
session-entered key now wins over an environment variable (V171-KEY-02). The
diff itself (`pagefolio/dialogs/llm_config.py`, `pagefolio/ocr.py`,
`pagefolio/ocr_dialog.py`, `pagefolio/lang.py`) is internally consistent and
well covered by new unit tests (`tests/test_ocr.py`,
`tests/test_provider_ui.py`) for the key-resolution and non-leak guarantees
(no `api_key` ever reaches `settings`/`llm_settings`).

However, reviewing the full files (not just the diff hunks) surfaced one
pre-existing but directly-relevant defect that undermines the security/
transparency guarantee this exact feature is supposed to provide: the "cloud
submission confirmation" dialogs (`_confirm_cost` / `_confirm_summary_cost`)
still only distinguish `gemini` vs. "everything else = claude", so when
`ocr_provider == "runpod"` the user is shown `api.anthropic.com` as the
destination host and a Claude-model cost estimate — even though the actual
destination is the user's own configured RunPod endpoint URL. Since RunPod is
one of the three providers whose API-key UI this very phase completed, this is
in-scope and worth fixing now. A handful of smaller RunPod/tesseract-related
gaps are also noted below.

## Critical Issues

### CR-01: RunPod cost/destination confirmation dialog shows the wrong host and model

**File:** `pagefolio/ocr_dialog.py:1012-1046` (`_confirm_cost`) and
`pagefolio/ocr_dialog.py:1048-1071` (`_confirm_summary_cost`)

**Issue:** Both methods branch only on `if name == "gemini": ... else: # claude
(デフォルト)`. `_is_cloud_provider()` (used as the gate before calling these
methods, e.g. `ocr_dialog.py:1130` and `:1812`) treats `claude`, `gemini`, and
`runpod` all as cloud providers, so `_confirm_cost`/`_confirm_summary_cost` are
also invoked for RunPod. Because there is no `runpod` branch, the code falls
into the `else` clause and reports `host = "api.anthropic.com"` and
`model = self.app.settings.get("claude_model", ...)` even when the user
actually selected RunPod and configured an arbitrary `runpod_url` endpoint.

This is a security/transparency defect, not just a cosmetic one: the entire
purpose of this dialog (per the code's own D-12 comments — "送信先ホスト … を
明示する") is to accurately disclose *where* page images / OCR text are about
to be sent before an external, billed submission happens. For RunPod, the real
destination is whatever `runpod_url` the user (or an attacker who tampered
with settings) has configured — it could be any host — yet the dialog falsely
claims the data goes to Anthropic. This can lull a user into approving a
submission to an unintended/unexpected endpoint, and the accompanying cost
estimate is also wrong (computed from Claude pricing/token assumptions instead
of anything RunPod-specific).

No test exercises this path: `TestConfirmCost` in `tests/test_provider_ui.py`
only covers `ocr_provider == "claude"`, and `TestCheckCloudApiKey` only tests
key *resolution* for runpod, not the cost/host confirmation content.

**Fix:**
```python
def _confirm_cost(self, page_count=None):
    name = self.app.settings.get("ocr_provider", "")
    if name == "gemini":
        model = self.app.settings.get("gemini_model", "gemini-2.5-flash")
        host = "generativelanguage.googleapis.com"
    elif name == "runpod":
        model = self.app.settings.get("runpod_model", "") or "runpod"
        host = self.app.settings.get("runpod_url", "") or self._L.get(
            "llm_runpod_host_unset", "(RunPod endpoint URL)"
        )
    else:
        # claude（デフォルト）
        model = self.app.settings.get("claude_model", "claude-sonnet-4-6")
        host = "api.anthropic.com"
    ...
```
Apply the equivalent `elif name == "runpod":` branch to `_confirm_summary_cost`
as well, and add a regression test parametrized over
`["claude", "gemini", "runpod"]` asserting the displayed host matches the
provider actually being used.

## Warnings

### WR-01: `_last_valid_provider` fallback is self-referential when the saved provider is an unavailable Tesseract

**File:** `pagefolio/dialogs/llm_config.py:75`, `:969-981`

**Issue:** `self._last_valid_provider = current_settings.get("ocr_provider", "off")`
is initialized directly from the persisted setting, with no validation. If the
persisted `ocr_provider` is `"tesseract"` but Tesseract is no longer available
on this machine (e.g. moved to a machine without the binary), then at dialog
build time `_on_provider_change()` runs with `provider == "tesseract"` and
`self._last_valid_provider == "tesseract"` (the same value). The "reset to
last known-good provider" guard:
```python
if provider == "tesseract" and not _TESSERACT_AVAILABLE:
    self.provider_var.set(self._last_valid_provider)   # sets "tesseract" -> "tesseract" (no-op)
    self._set_lm_status(...)
    return
```
does nothing useful — it returns immediately, before any of the
section-frame `pack()`/`pack_forget()` logic runs, so the dialog shows the
combobox still on "tesseract", no provider-specific fields at all, and only a
warning label. If the user does not notice and simply clicks "適用", `_apply()`
reads `self.provider_var.get()` directly (`llm_config.py:1333`) and happily
persists `ocr_provider: "tesseract"` again — the broken state survives the
round trip through the dialog that was supposed to protect against it.

**Fix:** Validate availability when seeding the fallback, e.g.:
```python
saved_provider = current_settings.get("ocr_provider", "off")
self._last_valid_provider = (
    "off" if saved_provider == "tesseract" and not _TESSERACT_AVAILABLE
    else saved_provider
)
```
and additionally force `self.provider_var.set(self._last_valid_provider)`
once up front in `__init__` (before `_build()`) so the combobox itself never
opens on an already-invalid tesseract selection.

### WR-02: OCR dialog has no localized display name for RunPod

**File:** `pagefolio/ocr_dialog.py:693-710` (`_provider_display_name`)

**Issue:** `_provider_display_name` explicitly handles `claude`, `gemini`,
`tesseract`, and `lmstudio`/`""`, but has no branch for `runpod` and falls
through to `return name`, returning the raw internal string `"runpod"`. Every
other provider gets a friendly localized label (e.g. `"Claude (Anthropic)"`,
`"Gemini (Google AI)"`); RunPod does not, and there is no
`ocr_provider_name_runpod` key in `pagefolio/lang.py` at all (confirmed via
search — the key doesn't exist in either `ja` or `en`).

**Fix:** Add `ocr_provider_name_runpod` to both `ja`/`en` dicts in `lang.py`
(e.g. `"RunPod (Serverless)"`) and add a matching branch:
```python
if name == "runpod":
    return self._L["ocr_provider_name_runpod"]
```

### WR-03: Dead `env_var` values for gemini/runpod in `_check_cloud_api_key`

**File:** `pagefolio/ocr_dialog.py:1096-1104`

**Issue:**
```python
env_var = {
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "runpod": "RUNPOD_API_KEY",
}.get(name, "")
messagebox.showerror(
    self._L["err_title"],
    self._L[msg_key].format(env_var=env_var),
    parent=self,
)
```
`self._L[msg_key]` for `gemini`/`runpod`
(`ocr_api_key_missing_gemini` / `ocr_api_key_missing_runpod` in `lang.py`)
does **not** contain an `{env_var}` placeholder — the env-var name is already
hardcoded into the prose of those strings. `.format(env_var=...)` silently
ignores the unused keyword for those two cases (Python's `str.format` does not
raise on unused kwargs), so there's no runtime failure, but the `"gemini"` /
`"runpod"` entries in the `env_var` dict are dead code that could mislead a
future maintainer editing those LANG strings into thinking `{env_var}` is
consumed there.

**Fix:** Either add `{env_var}` placeholders to the gemini/runpod strings and
rely on the dict uniformly, or drop the unused `gemini`/`runpod` entries and
only build `env_var` for the `claude` case, to keep the mapping honest.

### WR-04: Switching provider to "off" while an `OCRDialog` is already open does not disable Run/Resume

**File:** `pagefolio/ocr_dialog.py:920-936` (`_apply_llm_settings`, `name in
("lmstudio", "", "off")` branch)

**Issue:** `_update_ocr_buttons_state` (in `pagefolio/app.py:190-202`) disables
the OCR launch buttons entirely when `ocr_provider == "off"`, but that check
only runs when *opening a new* `OCRDialog`. If a dialog is already open and
the user changes the provider to `"off"` via the embedded "⚙ LLM 設定…"
button, `_apply_llm_settings` treats `"off"` exactly like `"lmstudio"` (backward-
compat branch) and rebuilds a live `LMStudioProvider` — the Run/Resume buttons
in the already-open dialog remain enabled and OCR proceeds against
LM Studio's default URL even though the app-level setting is meant to mean
"OCR disabled". This is a pre-existing behavior gap rather than something
newly introduced by this phase, but it directly affects the same
`_apply_llm_settings` code path this phase touches for key handling.

**Fix:** In `_apply_llm_settings`, when `name == "off"`, disable
`run_btn`/`resume_btn` (mirroring `_update_ocr_buttons_state`'s intent) instead
of silently falling back to the LM Studio provider.

---

_Reviewed: 2026-07-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
