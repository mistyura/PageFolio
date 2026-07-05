---
phase: 01-api-llm
plan: 01
subsystem: api
tags: [api-key-resolution, ocr, lang-i18n, session-keys, tdd]

# Dependency graph
requires: []
provides:
  - "_resolve_api_key（pagefolio/ocr.py）の優先順を「セッションキー(入力値) → 環境変数」へ反転（claude/gemini/runpod 全分岐）"
  - "反転仕様を固定する回帰テスト（claude/gemini 書き換え + RunPod 新設 TestResolveApiKeyRunPod）"
  - "後続プラン（Plan 02 の入力欄・Plan 03 のエラー文言）が参照する新規/更新 LANG キー（ja/en）"
affects: [01-api-llm/01-02-PLAN, 01-api-llm/01-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_resolve_api_key は build_provider・OCRDialog 実行ゲートの単一の真実源。この1関数の反転で全呼び出し経路が一括反転する"
    - "gemini の dual env var（GEMINI_API_KEY→GOOGLE_API_KEY）内部順序は反転対象外・維持"
    - "os.environ への書き込みは一切行わない読み取り専用原則を継続（Phase 05-03 決定の継続）"

key-files:
  created: []
  modified:
    - pagefolio/ocr.py
    - tests/test_ocr.py
    - pagefolio/lang.py

key-decisions:
  - "_resolve_api_key の優先順を claude/gemini/runpod 全分岐で「session_keys → 環境変数 → OCRAPIKeyError」へ反転（V171-KEY-02・シグネチャ不変）"
  - "gemini の dual env var 内部優先順（GEMINI_API_KEY 優先）は反転対象外として維持"
  - "既存の env優先固定テスト（test_env_var_takes_priority_over_session_key 等）は新規追加ではなく書き換え・リネームで対応（Pitfall 4 の指摘通り）"
  - "llm_env_key_unset_static[_gemini/_runpod] のヒント文言も UI-SPEC の D-11 更新後文言へ ja/en 同時調整（新規キー追加はせず既存キーの text のみ更新）"
  - "ocr_session_key_label は本プランでは未削除（撤去対象 UI を撤去する Plan 03 と同一プランで削除し、実行時 KeyError の窓を作らない）"

patterns-established:
  - "APIキー解決順反転はロジック層1関数（_resolve_api_key）への集約で全経路へ波及させる（UI層・実行ゲート層は再実装しない）"

requirements-completed: [V171-KEY-02, V171-KEY-04, V171-TEST-02]

coverage:
  - id: D1
    description: "_resolve_api_key の優先順を「session_keys(入力値) → 環境変数」へ反転（claude/gemini/runpod 全分岐）"
    requirement: "V171-KEY-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKey::test_session_key_takes_priority_over_env_var"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyGemini::test_session_key_takes_priority_over_env_var"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyRunPod::test_session_key_takes_priority_over_env_var"
        status: pass
    human_judgment: false
  - id: D2
    description: "両方未設定で OCRAPIKeyError を raise（claude/gemini/runpod）"
    requirement: "V171-KEY-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKey::test_no_env_no_session_raises_ocr_api_key_error"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyGemini::test_raises_when_all_missing"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyRunPod::test_no_env_no_session_raises_ocr_api_key_error"
        status: pass
    human_judgment: false
  - id: D3
    description: "RunPod も _session_api_keys 機構で3ケース（入力優先/環境変数フォールバック/raise）を満たす新規テストクラス TestResolveApiKeyRunPod"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyRunPod (4 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "_resolve_api_key は os.environ への書き込みを一切行わない（読み取り専用原則の回帰防止）"
    requirement: "V171-KEY-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKey::test_os_environ_not_written"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyGemini::test_os_environ_not_written"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py::TestResolveApiKeyRunPod::test_os_environ_not_written"
        status: pass
    human_judgment: false
  - id: D5
    description: "新規/更新 LANG キーが ja/en 同一キーで整備され lang parity がグリーン"
    requirement: "V171-TEST-02"
    verification:
      - kind: unit
        ref: "tests/test_lang_parity.py::test_lang_keys_parity"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-07-05
status: complete
---

# Phase 01 Plan 01: APIキー解決優先順反転 + LANG先行整備 Summary

**`_resolve_api_key` の解決優先順を「環境変数優先」から「セッションキー(入力値)優先」へ反転し、claude/gemini書き換え + RunPod新設の回帰テストと、後続プラン参照用のLANGキー（ja/en）を整備**

## Performance

- **Duration:** 約5分
- **Tasks:** 3/3 completed
- **Files modified:** 3（pagefolio/ocr.py, tests/test_ocr.py, pagefolio/lang.py）

## Accomplishments
- `_resolve_api_key`（`pagefolio/ocr.py`）の claude/gemini/runpod 全分岐で「session_keys(入力値) → 環境変数 → OCRAPIKeyError」の順序へ反転。gemini の dual env var（GEMINI_API_KEY→GOOGLE_API_KEY）内部順序は不変。関数シグネチャ `(provider_name, session_keys)` も不変のため呼び出し元（build_provider・OCRDialog）は無変更で追従
- 既存の env優先固定テスト（`TestResolveApiKey`/`TestResolveApiKeyGemini`）を入力値優先の期待値へ書き換え（新規追加ではなくリネーム＋アサーション反転）、`TestResolveApiKeyRunPod` を新設（入力優先/環境変数フォールバック/raise の3ケース + os.environ 非書込み確認）
- 新規 LANG キー6件（`llm_api_key_label`/`llm_key_toggle_show`/`llm_key_toggle_hide`/`llm_key_session_note`/`llm_key_env_set_note`/`ocr_api_key_missing_runpod`）を ja/en 両辞書へ整備し、既存エラー文言2件（`ocr_api_key_missing`/`_gemini`）を LLM設定ダイアログ導線案内へ更新

## Task Commits

Each task was committed atomically:

1. **Task 1: 解決系テストを入力値優先へ書き換え + RunPod 版を新設** - `ea3e6f5` (test)
2. **Task 2: _resolve_api_key の優先順を反転（session_keys → 環境変数）** - `b13870b` (fix)
3. **Task 3: 新規/更新 LANG キーを ja/en 両辞書へ整備** - `82f6a06` (docs)

_Note: Task 1 was the RED phase (TDD) — 3 priority-flip tests intentionally failed until Task 2 (GREEN)._

## Files Created/Modified
- `tests/test_ocr.py` - `TestResolveApiKey`/`TestResolveApiKeyGemini` を入力値優先の期待値へ書き換え、`TestResolveApiKeyRunPod` を新設（4テスト）
- `pagefolio/ocr.py` - `_resolve_api_key` の claude/gemini/runpod 全分岐で session_keys を先に判定するよう反転。docstring も更新
- `pagefolio/lang.py` - 新規キー6件（ja/en）追加、既存エラー文言2件（`ocr_api_key_missing`/`_gemini`）とヒント文言3件（`llm_env_key_unset_static`系）をUI-SPEC準拠へ更新

## Decisions Made
- `_resolve_api_key` の優先順反転は関数内部の順序入替のみで実装し、シグネチャ・呼び出し元は無変更（RESEARCH.md Pattern 1 の推奨通り・全経路が一括で追従）
- gemini の dual env var 内部優先順（GEMINI_API_KEY 優先）は反転対象外として明示的に維持
- `llm_env_key_unset_static`系の既存ヒント文言は UI-SPEC の D-11 更新後文言（「APIキー未設定のため推奨モデル一覧を表示中…」）へ ja/en 同時更新（Task 3 の action 指示通り、キー追加なし・text のみ調整）
- `ocr_session_key_label` は本プランでは削除せず維持（撤去対象 UI 自体を撤去する Plan 03 と同一プランで削除する方針を継続）

## Deviations from Plan

None - plan executed exactly as written（ruff の E501 対応で `# noqa: E501` を既存コードベースの確立済みパターンに倣って一部テストdocstring/lang.py の長い行へ付与したのみ。これは既存の `pagefolio/ocr_dialog.py`/`pagefolio/ocr_providers.py` 等で使われている既存パターンの踏襲であり、新規逸脱ではない）

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02（LLMConfigDialog へのAPIキー入力欄追加）が参照する LANG キー（`llm_api_key_label` 等）は整備済み
- Plan 03（OCRDialog の旧セッションキー UI 撤去・エラー文言差し替え）が参照する `ocr_api_key_missing_runpod` と更新後の `ocr_api_key_missing`/`_gemini` 文言は整備済み。`ocr_session_key_label` の削除は Plan 03 の撤去タスクと同時実施が前提
- フルスイート 712 件グリーン（ベースライン707件 + 新規5件）・`ruff check . && ruff format .` クリーン確認済み

---
*Phase: 01-api-llm*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/ocr.py
- FOUND: tests/test_ocr.py
- FOUND: pagefolio/lang.py
- FOUND commit: ea3e6f5
- FOUND commit: b13870b
- FOUND commit: 82f6a06
