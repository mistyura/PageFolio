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
  warning: 5
  info: 0
  total: 6
status: issues_found
---

# Phase 01-api-llm: Code Review Report

**Reviewed:** 2026-07-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the OCR/LLM configuration surface (provider selection, session-only
API key handling, cost-confirmation gates, and the OCR execution dialog)
plus the ja/en language table and associated tests, against the current
state of the code (note: a prior `01-REVIEW.md` in this directory covered an
earlier commit — its CR-01 finding about the RunPod cost dialog showing
`api.anthropic.com` has since been fixed by commit `9f13287`, and its WR-02
about a missing `ocr_provider_name_runpod` key has also been fixed; those
items are not repeated here).

Most of the security-sensitive behavior (API keys never persisted to
`pagefolio_settings.json`, session keys kept only in
`app._session_api_keys`, mandatory cost-confirmation dialogs before any
cloud submission, masked key entry fields) is implemented correctly and is
well covered by `tests/test_ocr.py` / `tests/test_provider_ui.py`.

One genuine Python-3.8-compatibility regression was found in
`pagefolio/ocr_dialog.py` (module-level PEP 585 generic syntax evaluated
eagerly, contradicting the project's stated "Python 3.8+" baseline — and
inconsistent with the equivalent, correctly-quoted annotations already
present in `pagefolio/ocr.py`). A confirmed i18n defect was also found: two
LLM Config dialog labels reference LANG keys that do not exist in *either*
language dictionary, so the hardcoded Japanese fallback text always renders
even when the UI language is English. Several lower-severity robustness
gaps around the OCR circuit breaker, progress accounting, cost-estimation
fallback, and the "is this a cloud provider" classification for Ollama are
also documented below.

## Critical Issues

### CR-01: `OCR_PRICE_TABLE` / `_lookup_price` use Python 3.9+-only generic syntax, breaking the stated Python 3.8+ baseline

**File:** `pagefolio/ocr_dialog.py:31` (also `pagefolio/ocr_dialog.py:63`)
**Issue:**

```python
OCR_PRICE_TABLE: dict[str, tuple[float, float]] = {
    ...
}
...
def _lookup_price(model: str) -> tuple[float, float]:
```

`CLAUDE.md` declares `Python 3.8+`, explicitly noting "型ヒントは 3.8 互換"
(type hints must be 3.8-compatible). PEP 585 subscripted builtin generics
(`dict[str, ...]`, `tuple[...]`) are only usable as *runtime-evaluated*
expressions starting in Python 3.9 — on 3.8 this raises
`TypeError: 'type' object is not subscriptable` the moment the module is
imported (module-level variable annotations, unlike function annotations,
are evaluated eagerly unless `from __future__ import annotations` is
present, which this file does not have).

This is a real regression, not a hypothetical: `pagefolio/ocr.py` uses the
*exact same* annotation shape one file over and correctly guards it by
quoting the type as a string literal (`PROVIDER_OCR_PROMPTS: "dict[str,
dict[str, str]]" = {...}` at `ocr.py:40`, `PROVIDER_SUMMARY_PROMPTS:
"dict[str, str]" = {...}` at `ocr.py:117`) — proving the team was aware of
the 3.8 constraint but missed it in `ocr_dialog.py`. Because
`pagefolio/ocr_dialog.py` is imported lazily (`from pagefolio.ocr_dialog
import OCRDialog` inside `OCRMixin._start_ocr`), the app itself will start
fine on Python 3.8, but the entire OCR feature (the core feature this phase
is about) crashes the instant a user tries to run OCR, and every test that
imports `pagefolio.ocr_dialog` (i.e. most of `tests/test_provider_ui.py` and
several tests in `tests/test_ocr.py`) would fail collection under 3.8.

**Fix:**
```python
OCR_PRICE_TABLE: "dict[str, tuple[float, float]]" = {
    ...
}
...
def _lookup_price(model: str) -> "tuple[float, float]":
```
(or add `from __future__ import annotations` at the top of the file, which
defers *all* annotation evaluation and is the more robust fix going
forward).

## Warnings

### WR-01: `ocr_custom_prompt_label` / `ocr_custom_prompt_hint` LANG keys don't exist — English UI silently shows Japanese text

**File:** `pagefolio/dialogs/llm_config.py:830`, `pagefolio/dialogs/llm_config.py:854-856`
**Issue:**

```python
text=self._L.get("ocr_custom_prompt_label", "カスタムプロンプト:"),
...
text=self._L.get(
    "ocr_custom_prompt_hint", "(空欄でデフォルトのプロンプトを使用)"
),
```

`"ocr_custom_prompt_label"` and `"ocr_custom_prompt_hint"` are not defined
anywhere in `pagefolio/lang.py` — not in `LANG["ja"]` and not in
`LANG["en"]` (verified: zero matches for either key in the file). Because
`.get(key, fallback)` always resolves to the hardcoded Japanese fallback
string when the key is absent, **every** user — including English-mode
users (`lang="en"`) — sees the Japanese "カスタムプロンプト:" label and
"(空欄でデフォルトのプロンプトを使用)" hint on the "Custom Prompt" row of the
LLM Config dialog. This breaks the ja/en localization CLAUDE.md mandates
("LANG の新規キーは ja / en 両方に同一キーで追加"), and is not caught by
`tests/test_lang_parity.py`-style key-parity checks because the key is
missing from *both* dictionaries symmetrically (parity holds, translation
doesn't exist).

Contrast with the adjacent, correctly-defined summary-prompt row, which
uses real keys present in both dictionaries:
`pagefolio/lang.py:555-556` (ja) / `pagefolio/lang.py:1131-1132` (en).

**Fix:** Add both keys to `LANG["ja"]` and `LANG["en"]` in
`pagefolio/lang.py`, mirroring the `ocr_summary_prompt_label` /
`ocr_summary_prompt_hint` pattern, e.g.:
```python
# ja
"ocr_custom_prompt_label": "カスタムプロンプト:",
"ocr_custom_prompt_hint": "(空欄でデフォルトのプロンプトを使用)",
# en
"ocr_custom_prompt_label": "Custom prompt:",
"ocr_custom_prompt_hint": "(blank: use the default prompt)",
```
and remove the hardcoded fallback strings from `llm_config.py` (or keep
them only as a safety net, now that the real translations exist).

### WR-02: Non-retryable page failures (`RuntimeError`) never trip the OCR circuit breaker, defeating its purpose for systemic failures like a bad API key

**File:** `pagefolio/ocr_dialog.py:1518-1528` (worker `except RuntimeError` / `except Exception` branches), compare with `_record_retryable_failure` at `pagefolio/ocr_dialog.py:672-689`
**Issue:** The circuit breaker (`CB_CONSECUTIVE_FAILURES`, comment: "サーバ側が
完全に落ちている時に全ページ × リトライ待機を消化しないための保険") only
increments `_consec_err_count` inside `_record_retryable_failure`, which is
called solely when an `OCRRetryableError` exhausts its retries. The
`RuntimeError` and bare `except Exception` branches in `_worker()` (e.g. a
non-retryable 4xx from the provider — including an invalid/expired API key,
which will fail identically on *every* page) record into `self.errors` and
bump `_done_count`, but never touch `_consec_err_count` or `_fatal_msg`.
Consequently a deterministic, systemic failure (bad credentials, malformed
request, etc.) is never caught by the circuit breaker and the run will
plow through every remaining page issuing one doomed request each —
exactly the wasteful, no-early-abort scenario the circuit breaker exists to
prevent, just triggered via a different exception type.

**Fix:** Also feed `RuntimeError`/generic-exception page failures into the
same consecutive-failure counter (or a parallel one) that
`_record_retryable_failure` maintains, so `CB_CONSECUTIVE_FAILURES`
consecutive non-retryable failures also abort the run early.

### WR-03: `_is_cloud_provider()` never treats Ollama as "external", even when `ollama_url` points at a remote host

**File:** `pagefolio/ocr_dialog.py:775-792`, `pagefolio/ocr.py:771-775` (`_cloud_providers = {"claude", "gemini", "runpod"}`)
**Issue:** The cost-confirmation gate (`_confirm_cost`/`_confirm_summary_cost`)
and the API-key gate (`_check_cloud_api_key`) are only invoked when
`_is_cloud_provider()` is true, and that check hardcodes
`name in ("claude", "gemini", "runpod")` — Ollama is always treated as
local. But `settings_ollama_url` (`pagefolio/dialogs/llm_config.py:242-253`)
is a free-form URL the user can point at any remote host. If a user
legitimately configures a hosted/remote Ollama endpoint, page images are
sent over the network to a third party exactly like Claude/Gemini/RunPod,
yet none of the "this will send your pages to an external service" /
cost-confirmation safeguards apply — silently contradicting the app's own
stated assumption that "Tesseract / LM Studio / Ollama はローカル完結"
(CLAUDE.md, 既知の制限・注意事項).

**Fix:** Derive "is this submission external" from whether the configured
host is loopback (`localhost`/`127.0.0.1`) rather than from a fixed
provider-name allowlist, or explicitly ask for the same confirmation
whenever `ollama_url`/`lm_studio_url` resolve to a non-local host.

### WR-04: Pages that fail during main-thread rendering are excluded from the progress-bar tally, so a completed run can show < 100%

**File:** `pagefolio/ocr_dialog.py:1367-1411` (`_render_next_page`, exception branch at 1407-1409)
**Issue:** When `page_to_png_b64`/`has_embedded_text`/`page.get_text()`
raises inside `_render_next_page` (main thread), the page is recorded into
`self.errors` but is never added to `_skipped_pages` nor counted via
`_done_count` (that only happens for pages that actually reach the
consumer/worker or the embedded-text-skip path). Since `_on_progress_bar`
and the "done" text are both driven by `_done_count + skipped_count`
(`pagefolio/ocr_dialog.py:1381-1394`, `1532-1537`), a run that hits this
render-time exception path finishes (`_finish_complete` still fires, since
that's gated on `_render_idx >= total`, not on the tally) with the progress
bar visually short of `maximum`. Purely cosmetic, but can make a
successfully-completed run look stuck/incomplete to the user.

**Fix:** When catching the render exception, also increment `_done_count`
(under `_done_lock`) or add the page to a "render-failed" set that's
included in the done-tally computation, so the bar always reaches its
maximum on completion.

### WR-05: `_lookup_price`'s substring-containment matching silently falls back to the most expensive tier for RunPod/custom models

**File:** `pagefolio/ocr_dialog.py:63-69`
**Issue:**
```python
def _lookup_price(model: str) -> tuple[float, float]:
    for key, prices in OCR_PRICE_TABLE.items():
        if key in model:
            return prices
    return _PRICE_FALLBACK  # (5.0, 25.0) — the single most expensive tier
```
`OCR_PRICE_TABLE` only contains Claude/Gemini model-name substrings, so any
RunPod deployment (`model = settings.get("runpod_model", "") or "runpod"`,
`pagefolio/ocr_dialog.py:1035`) or unrecognized custom model name always
falls through to `_PRICE_FALLBACK`, i.e. the highest priced tier in the
table ($5/$25 per MTok — Opus-level pricing). For a self-hosted RunPod
endpoint that may in fact be free or priced completely differently, the
mandatory cost-confirmation dialog (`_confirm_cost`) will show a needlessly
alarming and inaccurate "estimated cost", undermining the credibility of
that safeguard. Separately, matching is done via plain substring
containment (`key in model`) rather than exact/prefix matching, which is
inherently order-dependent for overlapping keys (e.g. `"claude-3-sonnet"`
vs `"claude-sonnet"`) and will silently mis-price any future model name
that happens to contain one of these substrings incidentally.

**Fix:** For RunPod (and any provider without a known per-token price),
either omit the dollar estimate entirely and state "pricing depends on your
endpoint configuration" in the confirmation dialog, or require an explicit,
user-configured price-per-page for self-hosted providers instead of
defaulting to the most expensive hosted-API tier.

---

_Reviewed: 2026-07-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
