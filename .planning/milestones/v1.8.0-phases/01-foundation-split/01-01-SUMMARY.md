---
phase: 01-foundation-split
plan: 01
subsystem: testing
tags: [refactor, packaging, backward-compat, tests, pytest]

# Dependency graph
requires: []
provides:
  - "tests/test_imports.py の TestOcrProvidersImports（ocr_providers 全17シンボルの package-level import 後方互換テスト）"
  - "pagefolio トップレベル非公開の負ガード（ClaudeProvider/GeminiProvider/LMStudioProvider/OCRProvider/LLMConfigDialog）"
  - "llm_config 両経路 import（pagefolio.dialogs.llm_config / pagefolio.dialogs 経由）の既存回帰テスト維持確認"
affects: [01-foundation-split Wave 2 (ocr_providers パッケージ分割), 01-foundation-split Wave 3 (llm_config Mixin 分割)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "後方互換 import 安全網の先行拡張（分割前にテストを緑で確立し、分割中に赤くなれば即座に検知するサイクル）"

key-files:
  created: []
  modified:
    - tests/test_imports.py

key-decisions:
  - "既存 TestDialogsImports の記法（1シンボル=1テストメソッド + assert）をそのまま複製し、新規パターンを持ち込まなかった"
  - "llm_config 両経路 import テストは既存（test_individual_module_llm_config / test_llm_config_via_dialogs_subpackage）で充足済みと確認し、変更を加えなかった"
  - "公開面負ガードは TestPackageSurface に2メソッド追加する形にし、既存クラス構成を変えなかった"

patterns-established:
  - "分割前に後方互換 import テストを先行拡張し、現行 monolith に対して今すぐ全緑にする（TDD 的サイクルの起点）"

requirements-completed: [V180-REFAC-01, V180-REFAC-02]

coverage:
  - id: D1
    description: "ocr_providers パッケージ直下 import の後方互換テスト（TestOcrProvidersImports・全17シンボル + 一括import）を追加し、現行 monolith で全緑"
    requirement: "V180-REFAC-01"
    verification:
      - kind: unit
        ref: "tests/test_imports.py::TestOcrProvidersImports (pytest tests/test_imports.py -k OcrProviders -q)"
        status: pass
    human_judgment: false
  - id: D2
    description: "llm_config 両経路 import（pagefolio.dialogs.llm_config 直接 / pagefolio.dialogs 経由）が既存テストで緑であることを確認し、pagefolio トップレベルに ClaudeProvider/LLMConfigDialog 等が非公開であることを検証する負ガードを追加"
    requirement: "V180-REFAC-02"
    verification:
      - kind: unit
        ref: "tests/test_imports.py::TestDialogsImports / TestPackageSurface (pytest tests/test_imports.py -k \"LlmConfig or PackageSurface or llm_config\" -q)"
        status: pass
    human_judgment: false

duration: 約6分
completed: 2026-07-14
status: complete
---

# Phase 01 Plan 01: 後方互換 import 安全網の先行拡張 Summary

**ocr_providers 全17シンボル（private ヘルパー含む）の package-level import 後方互換テストと、pagefolio トップレベル非公開の負ガードを、Wave 2/3 の肥大モジュール分割に先立って現行 monolith に対し全緑で確立した**

## Performance

- **Duration:** 約6分
- **Started:** 2026-07-13T20:40:44Z
- **Completed:** 2026-07-14T (実行完了時刻)
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `tests/test_imports.py` に `TestOcrProvidersImports`（19テストメソッド）を新規追加。`OCRProvider`・6プロバイダクラス・3エラークラス・8個の private ヘルパー/定数（`_require_http_scheme`・`parse_retry_after`・`looks_like_context_error`・`_raise_mapped_http_error`・`_detect_tesseract`・`_ALLOWED_URL_SCHEMES`・`_CONTEXT_ERROR_MARKERS`・`_retryable_http_message`）を個別 + 一括 import の両方で検証
- `llm_config` の両経路 import（`pagefolio.dialogs.llm_config` 直接 / `pagefolio.dialogs` 経由）が既存テスト（`test_individual_module_llm_config`・`test_llm_config_via_dialogs_subpackage`）で既に充足していることを確認（変更不要）
- `pagefolio` トップレベルの公開面負ガードを `TestPackageSurface` に追加: `ClaudeProvider`/`GeminiProvider`/`LMStudioProvider`/`OCRProvider`/`LLMConfigDialog` がいずれも `hasattr(pagefolio, ...)` で `False` になることを機械的に保証（Pitfall 4 の回帰防止）
- pytest 全901件・ruff 全クリーンを確認（分割前のベースライン確立）

## Task Commits

Each task was committed atomically:

1. **Task 1: ocr_providers 後方互換 import テスト（TestOcrProvidersImports）を追加** - `d8c5fe9` (test)
2. **Task 2: llm_config 両経路 import と公開面ガードを確認・補完** - `f7b5b9d` (test)

**Plan metadata:** (このコミット・docs: complete plan)

## Files Created/Modified
- `tests/test_imports.py` - `TestOcrProvidersImports` クラス新規追加（19メソッド）・`TestPackageSurface` に負ガード2メソッド追加

## Decisions Made
- 既存 `TestDialogsImports` の記法（1シンボル=1テストメソッド + `assert ... is not None` / `assert callable(...)`）をそのまま複製し、新規の検証パターンを持ち込まなかった（一貫性優先）
- llm_config 両経路 import は既存テストで充足済みと確認したため無変更とした（Task 2 の「確認のみで変更しない」指示に従った）
- 公開面負ガードは既存 `TestPackageSurface` クラスへのメソッド追加とし、新規クラスは作らなかった（既存構成との一貫性）

## Deviations from Plan

None - plan executed exactly as written（ruff E501 対応のため docstring を短縮する軽微な調整のみ行ったが、これはコード変更ではなく同一プランの Task 1 実行中の記述調整であり、Rule 1〜4 に該当する逸脱ではない）

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 2（ocr_providers パッケージ分割）・Wave 3（llm_config Mixin 分割）の回帰検知装置が確立された。分割作業中に `pytest tests/test_imports.py -k "OcrProviders or LlmConfig or PackageSurface" -q` を実行すれば re-export 漏れを即座に検知できる
- 次プラン（01-02 以降）で ocr_providers/llm_config の実分割・`_SENSITIVE_KEYS` レジストリ化に着手可能
- ブロッカーなし

---
*Phase: 01-foundation-split*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: .planning/phases/01-foundation-split/01-01-SUMMARY.md
- FOUND: tests/test_imports.py
- FOUND commit: d8c5fe9
- FOUND commit: f7b5b9d
