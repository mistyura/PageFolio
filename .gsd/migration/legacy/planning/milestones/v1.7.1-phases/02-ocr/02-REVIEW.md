---
phase: 02-ocr
reviewed: 2026-07-05T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - pagefolio/dialogs/llm_config.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_pipeline.py
  - pagefolio/ocr_providers.py
  - pagefolio/plugins.py
  - tests/test_ocr.py
  - tests/test_ocr_pipeline.py
  - tests/test_ocr_providers.py
  - tests/test_plugins.py
  - tests/test_provider_ui.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-07-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the OCR provider-registry hardening, Tesseract language fallback, provider-layer
L-6 fixes, and the new `pagefolio/ocr_pipeline.py` producer-consumer unification module,
together with their test suites. The bulk of the phase's stated goals (URL scheme
validation, Gemini model-name escaping, error-body truncation, Claude models pagination,
plugin OCR-provider registry dedup/unload) are implemented correctly and are well covered
by tests.

Two defects are serious enough to block: an unquoted PEP 585 generic type annotation in
`ocr_dialog.py` that will raise `TypeError` at import time on the project's stated minimum
Python version (3.8), and `RunPodProvider.list_models()` silently swallowing network/parse
exceptions and returning a placeholder list while still reporting "success" to the user —
which also makes an entire exception-handling branch in `llm_config.py` unreachable dead
code. Several other issues (partial-sentinel thread leak, a cancellation-window gap that
can trigger one extra billed API call after Cancel, dead-code branch, and a plugin-load
bookkeeping inconsistency) are lower severity but worth fixing.

## Critical Issues

### CR-01: `OCR_PRICE_TABLE` type annotation breaks the project's Python 3.8 compatibility requirement

**File:** `pagefolio/ocr_dialog.py:37`
**Issue:**
```python
OCR_PRICE_TABLE: dict[str, tuple[float, float]] = {
    ...
}
```
This is a module-level variable annotation. Without `from __future__ import annotations`
(not present in this file), Python evaluates the annotation expression at import time to
populate `__annotations__`. `dict[str, ...]` / `tuple[float, float]` subscripting of
builtin generic types (PEP 585) is only supported from Python 3.9 onward — on Python 3.8
(the project's documented minimum per `CLAUDE.md`: "型ヒントは 3.8 互換" / requirements
say "Python 3.8+") this line raises `TypeError: 'type' object is not subscriptable` as
soon as `pagefolio.ocr_dialog` is imported, i.e. the first time a user opens the OCR
dialog. This breaks the entire OCR feature (the subject of this phase) on any Python 3.8
deployment.

Notably, the same phase's own code elsewhere in `pagefolio/ocr.py` deliberately avoids this
exact pitfall by quoting the annotation as a string literal:
```python
PROVIDER_OCR_PROMPTS: "dict[str, dict[str, str]]" = {...}
PROVIDER_SUMMARY_PROMPTS: "dict[str, str]" = {...}
```
`OCR_PRICE_TABLE`'s annotation was left unquoted, breaking that established convention.
The dev/test environment here runs Python 3.14, so this will not be caught by `pytest` —
it only manifests on 3.8/3.7-era interpreters, exactly the kind of latent bug that a
version-matrix-free CI will miss.

**Fix:**
```python
OCR_PRICE_TABLE: "dict[str, tuple[float, float]]" = {
    ...
}
```
(or add `from __future__ import annotations` at the top of the file, which fixes this
class of issue file-wide).

### CR-02: `RunPodProvider.list_models()` silently swallows real errors and reports false success

**File:** `pagefolio/ocr_providers.py:1493-1521`
**Issue:** Every other provider's `list_models()` (LMStudio, Claude, Gemini, Ollama) maps
`urllib` failures to the documented exception contract stated on `OCRProvider`
(`ConnectionError` / `TimeoutError` / `RuntimeError`). `RunPodProvider.list_models()` does
not:
```python
try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
except Exception:
    return [self.model] if self.model else ["runpod-model"]

try:
    data = json.loads(body)
    return [m.get("id") for m in data.get("data", []) if m.get("id")]
except Exception:
    return [self.model] if self.model else ["runpod-model"]
```
Both `except Exception` blocks swallow the error and return a placeholder single-item
list instead of propagating. This has two consequences:
1. It violates the `OCRProvider.list_models()` docstring's exception contract
   ("`ConnectionError` / `TimeoutError` / `RuntimeError`（クラス docstring 参照）").
2. In `pagefolio/dialogs/llm_config.py._refresh_runpod_models`, the caller wraps the call
   in `try/except Exception` expecting to show a "fail" status on error — but since
   `list_models()` never raises, that branch is dead code, and the UI instead shows the
   **"success"** status (`settings_lm_test_ok` — "接続OK ({count} モデル利用可能)") with
   a fabricated 1-item model list, even though the actual HTTP request failed (wrong URL,
   server down, timeout, malformed JSON, etc). The user is misled into believing the
   RunPod endpoint is reachable and configured correctly when it is not.

Confirmed by test coverage: `tests/test_ocr_providers.py::TestRunPodProvider` never
exercises a genuine network failure/success path through `list_models()` (only the
scheme-rejection test, which is validated *before* the swallowing `try` block and is
unaffected).

**Fix:** Remove the blanket `except Exception` swallowing and let errors propagate like
every other provider, e.g.:
```python
try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
except socket.timeout as e:
    raise TimeoutError(f"timed out after {timeout}s") from e
except urllib.error.HTTPError as e:
    raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
except urllib.error.URLError as e:
    reason = getattr(e, "reason", e)
    if isinstance(reason, socket.timeout):
        raise TimeoutError(f"timed out after {timeout}s") from e
    raise ConnectionError(str(reason)) from e

try:
    data = json.loads(body)
except json.JSONDecodeError as e:
    raise RuntimeError(f"Unexpected response: {body[:500]}") from e
return [m.get("id") for m in data.get("data", []) if m.get("id")]
```
If a fallback-list-on-error UX is genuinely wanted for RunPod, that decision should be
made explicitly in the caller (`_refresh_runpod_models`), not hidden inside the provider
in a way that contradicts the documented contract and other providers' behavior.

## Warnings

### WR-01: Partial sentinel delivery is not retried on cancel/fatal-error paths — worker thread leak

**File:** `pagefolio/ocr_dialog.py:1403-1416`
**Issue:** `_render_next_page` has three exit branches that must deliver one `None`
sentinel per worker via `send_sentinels(queue, concurrency)`. The "all pages complete"
branch correctly retries a partial send:
```python
sent = send_sentinels(self._render_queue, self.concurrency)
if sent < self.concurrency:
    g = gen
    self.after(100, lambda _g=g: self._render_next_page(_g))
    return
```
but the cancel and fatal-error branches call `send_sentinels` once and ignore the return
value entirely:
```python
if self._cancel_flag.is_set():
    send_sentinels(self._render_queue, self.concurrency)
    self._finish_cancelled()
    return
...
if self._pstate is not None and self._pstate.is_fatal():
    send_sentinels(self._render_queue, self.concurrency)
    self._finish_error(self._pstate.fatal_msg, kind=self._pstate.fatal_kind)
    return
```
Since `queue.Queue(maxsize=concurrency + 1)`, a full queue at the moment cancellation/fatal
is detected causes `send_sentinels` to deliver 0 (or a partial count) sentinels, and no
retry is scheduled. `_finish_cancelled`/`_finish_error` are called directly by the
producer regardless (so the UI does finish/update correctly), but any worker thread that
never receives its `None` will loop forever on `queue.get(timeout=1.0)`. For the
cancel path this self-heals (workers check `self._cancel_flag.is_set()` on each 1s
timeout and break), but for the **fatal-error path** `cancel_flag` is never set, so an
affected worker thread polls indefinitely (daemon thread — harmless at process exit, but
accumulates for the lifetime of the app across repeated OCR runs that hit connection/
timeout/circuit-breaker errors under load).

This is confirmed by contrast with the test-only producer harness in
`tests/test_ocr_pipeline.py::_drive_pipeline`, which explicitly loops
`while sent < workers: ... send_sentinels(...)` to guarantee delivery — the production
code only replicates that robustness for 1 of its 3 exit paths.

**Fix:** Apply the same retry-on-partial-send pattern used in the "complete" branch to the
cancel and fatal branches, e.g.:
```python
if self._cancel_flag.is_set():
    sent = send_sentinels(self._render_queue, self.concurrency)
    if sent < self.concurrency:
        g = gen
        self.after(50, lambda _g=g, n=self.concurrency - sent: self._retry_sentinels(_g, n))
    self._finish_cancelled()
    return
```
(with an equivalent retry helper reused for the fatal branch).

### WR-02: Cancellation is not re-checked between retry attempts — can issue one extra (billed) API call after Cancel

**File:** `pagefolio/ocr_pipeline.py:210-244` (mirrored in `pagefolio/ocr.py:351-392`
`run_parallel._call`)
**Issue:** `consume_one` checks `cancel_check()`/`state.is_fatal()` only once, before the
`for attempt in range(1, MAX_RETRIES + 1)` loop starts:
```python
if _is_cancelled() or state.is_fatal():
    return

for attempt in range(1, MAX_RETRIES + 1):
    try:
        text, truncated = provider.ocr_image_ex(b64, prompt)
        ...
    except OCRRetryableError as e:
        ...
        interruptible_sleep(delay, _is_cancelled)
    ...
```
`interruptible_sleep` correctly cuts the backoff wait short when cancelled, but control
then falls through to the *next* loop iteration, which calls `provider.ocr_image_ex(...)`
again — an actual outbound network request — without re-checking `_is_cancelled()`. So
pressing Cancel during a retry backoff wait does not prevent one further API call for that
page. Given this app puts significant emphasis on cost-consciousness for cloud OCR
providers (mandatory cost-confirmation dialogs, per-call cost estimates, session-only API
keys), an uncancellable extra billed request slipping through after the user explicitly
cancelled is a real (if narrow-window) user-facing issue, not just a style nit. The same
gap exists in the legacy `run_parallel._call` implementation in `ocr.py`, so both parallel
implementations of the retry logic share the bug (see IN-01).

**Fix:** Re-check cancellation at the top of each loop iteration, e.g.:
```python
for attempt in range(1, MAX_RETRIES + 1):
    if _is_cancelled() or state.is_fatal():
        return
    try:
        ...
```

### WR-03: Dead/redundant branch in `RunPodProvider.list_models()`

**File:** `pagefolio/ocr_providers.py:1500-1504`
**Issue:**
```python
base_url = self.url.rstrip("/")
if base_url.endswith("/v1"):
    endpoint = base_url + "/models"
else:
    endpoint = base_url + "/models"
```
Both branches produce the exact same `endpoint` value, so the `/v1`-suffix check has zero
effect on behavior. This looks like an incomplete implementation — most likely intended to
strip the `/v1` suffix on one branch (e.g. `base_url[: -len("/v1")] + "/v1/models"` vs.
`base_url + "/models"`) but never finished, leaving genuinely dead conditional logic and a
maintenance trap (a future reader will assume the branches differ).

**Fix:** Either implement the intended distinction or collapse to a single line:
```python
endpoint = self.url.rstrip("/") + "/models"
```

### WR-04: `PluginManager.load_plugin()` leaves a partially-loaded plugin registered when `on_load` raises

**File:** `pagefolio/plugins.py:125-163`
**Issue:**
```python
instance = plugin_class()
self._plugins[plugin_id] = instance
if app and plugin_id not in self._disabled:
    self._loading_plugin_id = plugin_id
    try:
        instance.on_load(app)
    finally:
        self._loading_plugin_id = None
return instance
except Exception as e:
    logger.exception("プラグインロード失敗 (%s): %s", plugin_id, e)
    return None
```
`self._plugins[plugin_id] = instance` happens *before* `on_load(app)` is called, and
`on_load` is only protected by the outer catch-all `try/except` that wraps the entire
function body. If `on_load` raises, `load_plugin()` returns `None` (signaling "load
failed" to the caller — e.g. `load_all` / discovery loops), but the plugin instance is
already present in `self._plugins` (and `self._plugin_modules`), so:
- `is_enabled(plugin_id)` returns `True` and the plugin shows up in `plugins`/`all_plugins`
  as loaded, contradicting the `None` return value the caller just received.
- If a partially-executed `on_load` had already called
  `app.plugin_manager.register_ocr_provider(...)` before raising, that OCR provider
  registration survives even though the plugin "failed to load".
- A subsequent call to `load_plugin(plugin_id, ...)` short-circuits at the top
  (`if plugin_id in self._plugins: return self._plugins[plugin_id]`) and silently returns
  the half-initialized instance instead of retrying `on_load`.

This is inconsistent with `enable_plugin()`, which wraps `on_load(app)` in its own
dedicated `try/except` so a failing `on_load` doesn't corrupt the enable/disable
bookkeeping. No test exercises `load_plugin` with a raising `on_load` (only
`enable_plugin`/`disable_plugin`/`unload_plugin` exception paths are tested in
`TestLifecycleExceptionHandling`).

**Fix:** Wrap `on_load(app)` in its own try/except (mirroring `enable_plugin`), and decide
explicitly whether a failing `on_load` should roll back the `self._plugins[plugin_id]`
registration or just log-and-continue like the other lifecycle hooks:
```python
instance = plugin_class()
self._plugins[plugin_id] = instance
if app and plugin_id not in self._disabled:
    self._loading_plugin_id = plugin_id
    try:
        instance.on_load(app)
    except Exception as e:
        logger.exception("プラグイン on_load 失敗 (%s): %s", plugin_id, e)
    finally:
        self._loading_plugin_id = None
return instance
```

## Info

### IN-01: Duplicate retry/backoff implementation (`ocr.run_parallel` vs `ocr_pipeline.consume_one`)

**File:** `pagefolio/ocr.py:305-428`, `pagefolio/ocr_pipeline.py:170-266`
**Issue:** `ocr.run_parallel` (with its inner `_call`) and `ocr_pipeline.consume_one`
implement essentially the same per-item retry/backoff/fatal-classification logic
independently. `run_parallel` is no longer called anywhere in `pagefolio/` production code
(only re-exported via `pagefolio/__init__.py` and exercised by `tests/test_ocr.py`), while
`ocr_dialog.py` now drives OCR through `ocr_pipeline.consume_one`. Both copies currently
share the same cancellation-check gap (WR-02), which is exactly the risk of this kind of
duplication: a future fix to one will not automatically propagate to the other.
**Fix:** Either mark `run_parallel` as deprecated/legacy in its docstring (if kept for
external plugin-author API compatibility) or remove it and have any remaining callers use
`ocr_pipeline` directly, to avoid two logic paths drifting apart.

### IN-02: `TesseractProvider.RECOMMENDED_LANGS` is unused dead code

**File:** `pagefolio/ocr_providers.py:1065`
**Issue:** `RECOMMENDED_LANGS: list = ["jpn+eng", "eng", "jpn"]` is defined as a class
attribute but is never read anywhere in production code (`TesseractProvider.list_models()`
unconditionally returns `["tesseract"]`, independent of installed/available languages or
`RECOMMENDED_LANGS`). It is referenced only by a test that asserts its type
(`test_recommended_langs_is_list`), and by older planning docs
(`.planning/milestones/v1.4.0-phases/07-tesseract-pluginmanager-qa/PATTERNS.md`) describing
a design where `list_models()` was meant to fall back to `RECOMMENDED_LANGS` when
tesseract isn't installed — a design that was apparently not carried into the current
implementation.
**Fix:** Either wire `RECOMMENDED_LANGS` into `list_models()`/UI as originally designed, or
remove the now-vestigial attribute and its type-only test to avoid confusing future
readers about its purpose.

---

_Reviewed: 2026-07-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
