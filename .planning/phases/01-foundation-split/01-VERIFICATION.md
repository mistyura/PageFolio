---
phase: 01-foundation-split
verified: 2026-07-14T09:45:57Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1: 基盤分割（肥大モジュールリファクタリング） Verification Report

**Phase Goal:** 肥大化した OCR プロバイダー/LLM設定モジュールが責務別パッケージに分割され、APIキー秘匿の管理も中央レジストリ化されて、以降の機能追加の土台が整う。
**Verified:** 2026-07-14T09:45:57Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ocr_providers.py`（1537行）が責務別パッケージへ分割され、既存 import が変更なく動作する | ✓ VERIFIED | `pagefolio/ocr_providers/` に `__init__.py`/`base.py`/`errors.py`/`registry.py`/`lmstudio.py`/`claude.py`/`gemini.py`/`tesseract.py`/`ollama.py`/`runpod.py` の10ファイルが存在。旧 `pagefolio/ocr_providers.py` は存在しない（`ls` で `No such file`確認）。`python -c "from pagefolio.ocr_providers import ClaudeProvider, OCRProvider, parse_retry_after"` 相当は `tests/test_imports.py::TestOcrProvidersImports`（19件）で緑。`tests/test_ocr_providers.py`（D-03凍結・無修正）185件全通過 |
| 2 | `dialogs/llm_config.py`（1659行）が責務別パッケージへ分割され、既存 import パスが変更なく動作する | ✓ VERIFIED | `pagefolio/dialogs/llm_config/` に `__init__.py`/`dialog.py`/`sections.py`/`model_fetch.py` の4ファイルが存在。旧 `pagefolio/dialogs/llm_config.py` は削除済み。`from pagefolio.dialogs.llm_config import LLMConfigDialog` と `from pagefolio.dialogs import LLMConfigDialog` の両経路が動作（`tests/test_imports.py` 55件緑）。MRO 構造テスト（`TestLLMConfigDialogMRO` 3件）が緑: `tk.Toplevel` が3 Mixin より後ろ・`__init__` は `DialogMixin` に集約 |
| 3 | `_SENSITIVE_KEYS` がプロバイダ→環境変数マッピングから生成される中央レジストリとなり、新プロバイダ追加時の手動追加漏れが構造的に起きなくなる | ✓ VERIFIED | `pagefolio/ocr_providers/registry.py` 新設・`os` のみ依存（AST検証で pagefolio 内部 import ゼロを確認）。`pagefolio/settings.py:29` で `_SENSITIVE_KEYS = sensitive_keys()`（ハードコード撤廃）。`sensitive_keys()` 実行結果が現行10エントリを完全包含（実行確認: `superset: True`）。D-09 の4参照面（settings._SENSITIVE_KEYS / ocr._resolve_api_key / ocr_dialog._check_cloud_api_key / llm_config の sections.py・model_fetch.py）すべてが `registry.env_vars_for`/`primary_env_var` を参照するよう配線されていることを grep で実物確認 |
| 4 | 分割前に拡張された `test_imports.py` の後方互換 import テストと既存 pytest 全件がグリーンのまま維持される | ✓ VERIFIED | `pytest -q`（全906件）が全緑（実行確認）。`ruff check . && ruff format --check .` クリーン（実行確認・69ファイル）。`tests/test_imports.py`（55件）・`tests/test_ocr_providers.py`（185件・D-03凍結で無修正）ともに緑 |

**Score:** 4/4 truths verified（0 present-but-behavior-unverified）

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/ocr_providers/__init__.py` | 全シンボル完全 re-export | ✓ VERIFIED | 存在・`TestOcrProvidersImports` 19件緑 |
| `pagefolio/ocr_providers/base.py` | `OCRProvider` ABC + `_require_http_scheme` | ✓ VERIFIED | 存在・import 可 |
| `pagefolio/ocr_providers/errors.py` | 3例外クラス + リトライ/コンテキスト判定ヘルパー | ✓ VERIFIED | 存在・import 可 |
| `pagefolio/ocr_providers/registry.py` | `PROVIDER_ENV_KEYS` + 導出関数群（新設） | ✓ VERIFIED | 存在・stdlib(`os`)のみ依存をAST検証で確認・独立性制約がdocstringとCLAUDE.md（297行）双方に明記 |
| `pagefolio/ocr_providers/{lmstudio,claude,gemini,tesseract,ollama,runpod}.py` | 1プロバイダ1ファイル | ✓ VERIFIED | 6ファイルすべて存在 |
| `pagefolio/dialogs/llm_config/{__init__,dialog,sections,model_fetch}.py` | Mixin 3層 + 統合クラス | ✓ VERIFIED | 4ファイルすべて存在。`LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel)` のMRO健全性を確認 |
| `tests/test_settings_keyguard.py` の registry 網羅性テスト | `sensitive_keys()` が現行10エントリを部分集合として含む | ✓ VERIFIED | 実行で `superset: True` を確認。テストスイート内で緑 |
| 旧 `pagefolio/ocr_providers.py` / `pagefolio/dialogs/llm_config.py` | 削除済み | ✓ VERIFIED | `ls` で `No such file or directory` を確認 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `pagefolio/settings.py` | `pagefolio/ocr_providers/registry.py` | `from pagefolio.ocr_providers.registry import sensitive_keys` | ✓ WIRED | サブモジュール直接指定 import（循環回避）。`_SENSITIVE_KEYS = sensitive_keys()` で実配線確認 |
| `pagefolio/ocr.py` (`_resolve_api_key`) | `registry.py` | `env_vars_for` / `primary_env_var` | ✓ WIRED | grep で実装確認。セッションキー優先→env_vars_forタプル順フォールバック→OCRAPIKeyError の順序を実物確認 |
| `pagefolio/ocr_dialog.py` (`_check_cloud_api_key`) | `registry.py` | `primary_env_var` | ✓ WIRED | `ocr_dialog.py:1256,1270` で確認 |
| `pagefolio/dialogs/llm_config/sections.py` | `registry.py` | `env_vars_for`（D-09 #4） | ✓ WIRED | `sections.py:14,27` で確認 |
| `pagefolio/dialogs/llm_config/model_fetch.py` | `registry.py` | `env_vars_for`（D-09 #5） | ✓ WIRED | `model_fetch.py:12,28` で確認 |
| 内部 import 元（`ocr.py`/`ocr_dialog.py`/`app.py`/`plugins.py`） | `pagefolio.ocr_providers` package-level | D-10 旧パス維持 | ✓ WIRED | 906件フルスイート緑・後方互換 import テスト緑で間接確認 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 全テストスイート緑 | `pytest -q` | 906 passed | ✓ PASS |
| D-03凍結テスト無修正で通過 | `pytest tests/test_ocr_providers.py -q` | 185 passed | ✓ PASS |
| 後方互換 import 安全網緑 | `pytest tests/test_imports.py -q` | 55 passed | ✓ PASS |
| MRO 構造健全性（Pitfall 3） | `pytest tests/test_provider_ui.py -k MRO -q` | 3 passed | ✓ PASS |
| registry.py 独立性（AST検証） | `python -c "import ast; ..."` | pagefolio内部import 0件 | ✓ PASS |
| `sensitive_keys()` 現行10エントリ包含 | `python -c "from pagefolio.ocr_providers.registry import sensitive_keys; ..."` | superset: True | ✓ PASS |
| `pagefolio` トップレベル非公開ガード | `python -c "import pagefolio; assert not hasattr(...)"` | OK | ✓ PASS |
| Lint/フォーマット | `ruff check . && ruff format --check .` | All checks passed / 69 files formatted | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| V180-REFAC-01 | 01-01, 01-02 | ocr_providers.py パッケージ分割 | ✓ SATISFIED | パッケージ10ファイル存在・後方互換テスト緑・REQUIREMENTS.md で Complete |
| V180-REFAC-02 | 01-01, 01-04 | dialogs/llm_config.py パッケージ分割 | ✓ SATISFIED | Mixin 3層パッケージ存在・MRO健全性緑・REQUIREMENTS.md で Complete |
| V180-ROBUST-02 | 01-02, 01-03, 01-04 | `_SENSITIVE_KEYS` 中央レジストリ化 | ✓ SATISFIED | registry.py新設・4参照面すべて配線確認・REQUIREMENTS.md で Complete |

No orphaned requirements: REQUIREMENTS.md Traceability セクションで Phase 1 に対応付けられる要件は上記3件のみ（他要件はすべて Phase 2 以降）。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pagefolio/ocr_providers/registry.py:44-53` | — | `resolve_env_key()` is dead code; docstring falsely claims `ocr.py` consumes it, while `ocr.py`/`model_fetch.py`/`sections.py` each hand-roll the same loop instead (WR-01, 01-REVIEW.md) | ⚠️ Warning | Not a live bug (all 3 call sites currently resolve identically), but undermines the "single source of truth" goal of registry.py — a future precedence change in only one of the 4 copies would silently diverge. Non-blocking per code-review disposition (0 critical) |
| `pagefolio/dialogs/llm_config/dialog.py:17` vs `dialog.py:439-449` | — | Inconsistent monkeypatch seam after package split: `_apply()` uses a deferred package-level import for `prompt_file_exists`/`save_prompt_file`, but `_add_prompt_file_notice()` (dialog.py:17) and `sections.py`'s initial prompt load (`sections.py:15`) still use top-level module-load imports (WR-02, 01-REVIEW.md) | ⚠️ Warning | Not a live bug today (both resolve to identical real functions at runtime); creates an untested blind spot for future monkeypatch-based tests/plugins. Non-blocking |
| `pagefolio/dialogs/llm_config/__init__.py:22-32` | — | Class docstring lists only 4 of 7 supported providers and references a stale "Phase 7: tesseract を追加予定" comment, even though ollama/runpod/tesseract are fully implemented (IN-01, 01-REVIEW.md) | ℹ️ Info | Documentation drift carried over verbatim by the mechanical split; no functional impact |

No debt markers (`TBD`/`FIXME`/`XXX`) found in phase-modified files. No hardcoded secrets, bare `except:`, or empty implementations found.

### Human Verification Required

None. All must-haves are code-verifiable and were verified directly against the codebase (file existence, import behavior, AST inspection, full test-suite execution, and grep-confirmed wiring). The phase's own Manual-Only item (LLM 設定ダイアログの実表示・目視確認) is explicitly declared out of v1.8.0 scope in PROJECT.md and is compensated for by the headless MRO structure test (`TestLLMConfigDialogMRO`), per 01-04-PLAN.md's own verification strategy.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria are verified against the actual codebase (not just SUMMARY.md claims): both target files are physically split into the packages the plans describe, the old monolith files are deleted, the central `registry.py` exists with stdlib-only independence enforced by AST check, all 4 D-09 reference sites are wired to it (confirmed via source inspection), and the full 906-test suite plus ruff lint/format are green.

The code review (01-REVIEW.md) surfaced 2 warnings (dead-code `resolve_env_key` with a false docstring claim; inconsistent monkeypatch seam in the llm_config split) and 1 info item (stale provider-list docstring). These are real quality issues worth a follow-up cleanup pass, but none of them contradict a must-have truth, break behavior, or leave any of the three required refactors substantively incomplete — they are exactly the kind of "still works, but the single-source-of-truth story has a loose thread" issues the review process is designed to catch for later remediation, not phase-blocking gaps.

---

_Verified: 2026-07-14T09:45:57Z_
_Verifier: Claude (gsd-verifier)_
