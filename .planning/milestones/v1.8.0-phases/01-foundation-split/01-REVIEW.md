---
phase: 01-foundation-split
reviewed: 2026-07-14T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - pagefolio/dialogs/llm_config/__init__.py
  - pagefolio/dialogs/llm_config/dialog.py
  - pagefolio/dialogs/llm_config/model_fetch.py
  - pagefolio/dialogs/llm_config/sections.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_providers/__init__.py
  - pagefolio/ocr_providers/base.py
  - pagefolio/ocr_providers/claude.py
  - pagefolio/ocr_providers/errors.py
  - pagefolio/ocr_providers/gemini.py
  - pagefolio/ocr_providers/lmstudio.py
  - pagefolio/ocr_providers/ollama.py
  - pagefolio/ocr_providers/registry.py
  - pagefolio/ocr_providers/runpod.py
  - pagefolio/ocr_providers/tesseract.py
  - pagefolio/settings.py
  - tests/test_imports.py
  - tests/test_provider_ui.py
  - tests/test_settings_keyguard.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

This phase mechanically split `pagefolio/ocr_providers.py` into a package (`base`/`errors`/6 providers/`registry`) and `pagefolio/dialogs/llm_config.py` into a 3-layer Mixin package (`dialog`/`sections`/`model_fetch`), and introduced a new provider→env-var registry (`registry.py`) that `settings.py`, `ocr.py`, and `ocr_dialog.py` were rewired to consume.

The provider-file split itself (`base.py`/`errors.py`/`claude.py`/`gemini.py`/`lmstudio.py`/`ollama.py`/`runpod.py`/`tesseract.py`) is clean and behavior-preserving: request payloads, error mappings, retry/truncation handling, and `list_models` logic are byte-for-byte equivalent to what the docstrings claim, and the re-export surface in `ocr_providers/__init__.py` matches the 18-symbol contract asserted by `tests/test_imports.py::TestOcrProvidersImports`.

The `registry.py` rewiring, however, has two structural loose ends that are exactly the kind of subtle behavior/consistency drift a mechanical split can introduce even when every individual call site still "works": (1) `registry.resolve_env_key()` is dead code whose docstring makes a false claim about being consumed by `ocr.py`, while three separate call sites (`ocr.py`, `model_fetch.py`, `sections.py`) reimplement its exact logic by hand instead of calling it — undermining the registry's single-source-of-truth goal; (2) the llm_config package split broke the "package-level import for monkeypatch-compat" pattern the author correctly applied to `_apply()` but did not apply consistently to `_add_prompt_file_notice()` / `sections.py`'s initial prompt-value load, creating an untested blind spot. Neither is a live production bug (both currently resolve to the same real functions at runtime), but both are exactly the kind of "looks equivalent but silently isn't" issue worth fixing before this ships as the final state of the split.

No hardcoded secrets, dangerous eval/exec usage, or empty catch blocks were found in the reviewed files.

## Warnings

### WR-01: `registry.resolve_env_key()` is dead code with a false docstring claim; 3 call sites duplicate its logic instead of using it

**File:** `pagefolio/ocr_providers/registry.py:44-53`

**Issue:** The docstring states:

> `ocr.py` の `build_provider` キー解決（環境変数フォールバック段）が消費する。

This is incorrect — `resolve_env_key` has zero callers anywhere in `pagefolio/` (confirmed via full-repo grep) and no dedicated test file (`tests/test_registry*.py` does not exist). Meanwhile, three separate call sites independently reimplement the exact "loop `env_vars_for(name)` in order and return the first truthy `os.environ.get(var)`" logic that `resolve_env_key` was built to centralize:

- `pagefolio/ocr.py:208-246` (`_resolve_api_key`, env-var fallback loop at lines 241-244)
- `pagefolio/dialogs/llm_config/model_fetch.py:17-32` (`_env_fallback`)
- `pagefolio/dialogs/llm_config/sections.py:18-33` (`_configured_env_var`)

This directly undermines the stated purpose of `registry.py` (the module docstring calls it "触る場所が1箇所" for provider→env-var mapping, and `.planning/phases/01-foundation-split/01-02-SUMMARY.md` explicitly lists `resolve_env_key` as part of the new "基盤"). A future change to env-var precedence semantics made only in `resolve_env_key` (e.g. someone "fixing a bug" there) would silently not propagate to any of the three real call sites, and vice versa — three independent copies of security-relevant key-resolution logic is also a larger attack surface for a precedence bug (e.g. accidentally reading `GOOGLE_API_KEY` before `GEMINI_API_KEY` in only one of the three copies).

**Fix:** Either wire the 3 call sites through `resolve_env_key` directly:

```python
# pagefolio/ocr.py — _resolve_api_key env-var fallback
from pagefolio.ocr_providers.registry import primary_env_var, resolve_env_key

key = session_keys.get(provider_name, "")
if key:
    return key
key = resolve_env_key(provider_name)
if key:
    return key
raise OCRAPIKeyError(primary_env_var(provider_name))
```

and equivalently in `model_fetch.py:_env_fallback` / `sections.py:_configured_env_var` (the latter needs the *which var matched* info, so it may need a small variant, but should still route through `env_vars_for` + a single shared loop helper rather than 3 hand-rolled copies) — or, if `resolve_env_key` truly isn't needed as a distinct public entry point, delete it and correct the module docstring so it doesn't claim a non-existent consumer.

---

### WR-02: Inconsistent monkeypatch seam after the `llm_config` package split — `_apply()` uses the package-level indirection, `_add_prompt_file_notice()` and `sections.py`'s initial load do not

**File:** `pagefolio/dialogs/llm_config/dialog.py:17` (top-level import), `dialog.py:306-337` (`_add_prompt_file_notice`), `dialog.py:439-449` (`_apply`); `pagefolio/dialogs/llm_config/sections.py:15` (top-level import), `sections.py:833`, `sections.py:877`

**Issue:** Before the split, `dialogs/llm_config.py` was a single module, so `from pagefolio.settings import prompt_file_exists` created one name binding shared by every function in that module — monkeypatching `pagefolio.dialogs.llm_config.prompt_file_exists` (the module's own namespace) affected *all* call sites uniformly.

After the split into a package, `dialog.py`'s `_apply()` explicitly recognizes that this no longer holds and works around it with a deferred, package-level import (comment at `dialog.py:434-438` spells out the reasoning: "分割前は同一モジュール内の名前空間で monkeypatch(...) が効いていたため、分割後も ... 経由の遅延 import で同じ差し替え可能性を保つ"):

```python
# dialog.py:439-444 — _apply(), deliberately deferred + package-level
from pagefolio.dialogs.llm_config import (
    prompt_file_exists as _prompt_file_exists,
)
from pagefolio.dialogs.llm_config import (
    save_prompt_file as _save_prompt_file,
)
```

But `_add_prompt_file_notice()` in the very same file still uses the plain top-level import bound at module load (`dialog.py:17`: `from pagefolio.settings import get_current_font_size, prompt_file_exists`), and `sections.py`'s `_build()` does the same for `load_prompt_file` (`sections.py:15`: `from pagefolio.settings import load_prompt_file`, consumed at `sections.py:833` and `sections.py:877`). Neither `load_prompt_file` nor a package-level re-export of it even exists in `pagefolio/dialogs/llm_config/__init__.py` (only `prompt_file_exists`/`save_prompt_file` are re-exported there).

Concretely: `tests/test_provider_ui.py::TestApplyPromptFileWriteback` monkeypatches `pagefolio.dialogs.llm_config.prompt_file_exists`/`save_prompt_file` and only exercises `_apply()` — it passes precisely because `_apply()` got the special treatment. There is no equivalent test for `_add_prompt_file_notice()` or for the initial prompt textbox population in `sections.py`, so this gap is currently invisible, but it means: (a) the "ファイル連動中" notice logic and the initial-value population logic cannot be controlled the same way `_apply()`'s write-back can be in tests, and (b) any future code (tests, plugins, or a debugging monkeypatch) that assumes patching the package-level name affects *all* prompt-file behavior in the dialog — a reasonable assumption given `_apply()`'s own precedent — will silently only get partial effect.

Not a live production bug today (both import paths resolve to the identical real `pagefolio.settings` functions at runtime), but it is exactly the "split introduced a subtle seam nobody wired consistently" defect the phase's own risk profile calls out, and it will bite the next person who touches this file.

**Fix:** Pick one convention and apply it uniformly across `dialog.py`/`sections.py`:
- Either re-export `load_prompt_file` from `pagefolio/dialogs/llm_config/__init__.py` and have `_add_prompt_file_notice()` / `sections.py` import all three functions (`prompt_file_exists`, `save_prompt_file`, `load_prompt_file`) via the same deferred, package-level pattern `_apply()` uses, or
- Confirm package-level monkeypatch compatibility isn't actually required anywhere outside `_apply()`, and drop the special-casing there too (importing directly from `pagefolio.settings` everywhere, and updating `tests/test_provider_ui.py::TestApplyPromptFileWriteback` to monkeypatch `pagefolio.settings.prompt_file_exists`/`save_prompt_file` directly instead).

## Info

### IN-01: `LLMConfigDialog` class docstring lists only 4 of 7 supported providers

**File:** `pagefolio/dialogs/llm_config/__init__.py:22-32`

**Issue:** The class docstring's "対応プロバイダ" list only documents `off`/`lmstudio`/`claude`/`gemini`, plus a comment "# Phase 7: tesseract を追加予定" implying tesseract is still pending. In the actual carried-over code, `ollama`, `runpod`, and `tesseract` are all fully implemented (dedicated sections in `sections.py`, dedicated branches in `dialog.py::_on_provider_change`, dedicated refresh methods in `model_fetch.py`). This is stale documentation left over from an earlier milestone that the mechanical split carried forward verbatim without updating.

**Fix:** Update the docstring's provider list and remove/update the "Phase 7" comment to reflect that `ollama`/`runpod`/`tesseract` are already implemented, e.g.:

```python
"""...
対応プロバイダ（off/lmstudio/ollama/runpod/claude/gemini/tesseract）:
プロバイダ選択:
  - off: OCR を無効化
  - lmstudio / ollama: ローカル Vision API（URL・モデル欄を表示）
  - runpod: RunPod Serverless（URL・モデル・APIキー欄を表示）
  - claude: claude モデル欄・effort/temperature 欄を表示
  - gemini: gemini モデル欄・temperature 欄を表示（D-09・effort 非対応）
  - tesseract: 精度注記のみ（API設定不要）
...
"""
```

---

_Reviewed: 2026-07-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
