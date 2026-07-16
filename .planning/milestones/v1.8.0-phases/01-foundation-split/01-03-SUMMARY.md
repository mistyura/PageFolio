---
phase: 01-foundation-split
plan: 03
subsystem: ocr
tags: [refactor, registry, sensitive-keys, api-key-resolution, security]

# Dependency graph
requires:
  - phase: 01-foundation-split (Plan 02)
    provides: "pagefolio/ocr_providers/registry.py（env_vars_for/primary_env_var/resolve_env_key/sensitive_keys）"
provides:
  - "settings._SENSITIVE_KEYS が registry.sensitive_keys() から生成される（ハードコード撤廃）"
  - "ocr._resolve_api_key が registry.env_vars_for()/primary_env_var() 経由の統一ループへ置換（claude/gemini/runpod 個別分岐を撤廃）"
  - "ocr_dialog._check_cloud_api_key のエラーメッセージ env var 参照が registry.primary_env_var() へ置換"
affects: [01-foundation-split Plan 04 (llm_config Mixin 分割・残り1参照面の registry 統合)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "サブモジュール直接指定 import（from pagefolio.ocr_providers.registry import ...）で循環 import と重い __init__ 経由を回避（Pitfall 6）"

key-files:
  created: []
  modified:
    - pagefolio/settings.py
    - pagefolio/ocr.py
    - pagefolio/ocr_dialog.py

key-decisions:
  - "registry.primary_env_var() は未登録プロバイダで KeyError ではなく \"\" を返す実装（Plan 02 で確認済み）だったため、ocr_dialog.py 側で try/except KeyError を追加せず素通しで置換した（現行 .get(name, \"\") 挙動と完全一致）"

patterns-established: []

requirements-completed: [V180-ROBUST-02]

coverage:
  - id: D1
    description: "settings._SENSITIVE_KEYS を registry.sensitive_keys() 生成へ置換し、keyguard 3経路テストが緑を維持"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: unit
        ref: "tests/test_settings_keyguard.py (pytest tests/test_settings_keyguard.py -q)"
        status: pass
      - kind: unit
        ref: "python -c \"from pagefolio.settings import _SENSITIVE_KEYS; ...\" 現行10エントリ包含確認"
        status: pass
    human_judgment: false
  - id: D2
    description: "ocr._resolve_api_key を registry.env_vars_for() 経由の統一ループへ置換し、セッションキー優先・Gemini dual env var 優先順（GEMINI_API_KEY→GOOGLE_API_KEY）・未知プロバイダ raise 挙動を不変維持"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py (pytest tests/test_provider_ui.py -q)"
        status: pass
      - kind: unit
        ref: "tests/test_ocr.py および tests/test_ocr_providers.py (pytest tests/test_ocr.py tests/test_ocr_providers.py -q)"
        status: pass
    human_judgment: false
  - id: D3
    description: "ocr_dialog._check_cloud_api_key のエラーメッセージ env var 参照を registry.primary_env_var() へ置換し、未知プロバイダで空文字フォールバックを保持"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py (pytest tests/test_provider_ui.py -q・env_var メッセージ表示テスト含む)"
        status: pass
    human_judgment: false

duration: 約5分
completed: 2026-07-14
status: complete
---

# Phase 01 Plan 03: registry 参照統合（settings/ocr/ocr_dialog） Summary

**settings.py の `_SENSITIVE_KEYS`・ocr.py の `_resolve_api_key`・ocr_dialog.py の `_check_cloud_api_key` を Plan 02 で新設した `registry.py` 参照へ置換し、プロバイダ→環境変数マッピングの重複を解消した**

## Performance

- **Duration:** 約5分
- **Started:** 2026-07-14T09:04:24Z
- **Completed:** 2026-07-14T09:09:11Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `settings._SENSITIVE_KEYS` のハードコード10エントリ集合を `registry.sensitive_keys()` 生成へ置換（循環 import 回避のためサブモジュール直接 import）
- `ocr._resolve_api_key` の claude/gemini/runpod 個別ハードコード分岐（3ブロック）を `registry.env_vars_for()` を使った単一の優先順ループへ統合。セッションキー優先→環境変数フォールバックの2段構造、Gemini の dual env var 優先順（GEMINI_API_KEY→GOOGLE_API_KEY）、未知プロバイダのフォールバック raise は完全不変
- `ocr_dialog._check_cloud_api_key` のエラーメッセージ用 env var dict（3エントリのハードコード）を `registry.primary_env_var()` へ置換
- `pytest tests/test_settings_keyguard.py -q`（19件）・`pytest tests/test_provider_ui.py tests/test_ocr.py tests/test_ocr_providers.py -q`（438件）・`pytest -q`（全903件）・`ruff check . && ruff format --check .` 全緑を確認

## Task Commits

Each task was committed atomically:

1. **Task 1: settings._SENSITIVE_KEYS を registry.sensitive_keys() 生成へ置換** - `4409fef` (refactor)
2. **Task 2: ocr._resolve_api_key と ocr_dialog._check_cloud_api_key を registry 参照へ置換** - `69a5456` (refactor)

**Plan metadata:** (このコミット・docs: complete plan)

## Files Created/Modified
- `pagefolio/settings.py` - `_SENSITIVE_KEYS` を registry.sensitive_keys() 生成へ置換
- `pagefolio/ocr.py` - `_resolve_api_key` を registry.env_vars_for()/primary_env_var() 経由の統一ループへ置換
- `pagefolio/ocr_dialog.py` - `_check_cloud_api_key` の env var 参照を registry.primary_env_var() へ置換

## Decisions Made
- `registry.primary_env_var()` は Plan 02 の実装確認により未登録プロバイダで `KeyError` ではなく `""` を返すため、ocr_dialog.py 側に try/except を追加せず直接呼び出しに置換した（現行 `.get(name, "")` 挙動と完全一致・計画時の想定分岐が不要と判明）

## Deviations from Plan

None - plan executed exactly as written（registry.primary_env_var() の実際の戻り値仕様が計画の想定「KeyError の可能性」と異なっていたが、これは実装確認の結果であり動作変更を伴わない記述の簡略化のみ）

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- D-09 の4参照面のうち3面（settings._SENSITIVE_KEYS / ocr._resolve_api_key / ocr_dialog._check_cloud_api_key）が registry.py を Single Source of Truth として参照する状態になった
- 残る4番目の面（llm_config の環境変数チェック）は Plan 04（llm_config Mixin 分割）に同梱予定
- ブロッカーなし

---
*Phase: 01-foundation-split*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/settings.py
- FOUND: pagefolio/ocr.py
- FOUND: pagefolio/ocr_dialog.py
- FOUND commit: 4409fef
- FOUND commit: 69a5456
