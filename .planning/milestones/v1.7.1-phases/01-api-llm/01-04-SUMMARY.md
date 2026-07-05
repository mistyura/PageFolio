---
phase: 01-api-llm
plan: 04
subsystem: ui
tags: [tkinter, ocr, runpod, security, i18n]

# Dependency graph
requires:
  - phase: 01-api-llm (01-03)
    provides: OCRDialog旧キーUI撤去済み・_check_cloud_api_key一元化ゲート
provides:
  - "_confirm_cost / _confirm_summary_cost の runpod 分岐（正しい送信先ホスト・モデル開示）"
  - "_provider_display_name の runpod ローカライズ表示名（WR-02）"
  - "llm_runpod_host_unset / ocr_provider_name_runpod の ja/en LANG キー"
  - "TestConfirmCost の RunPod 送信先開示回帰テスト3件"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "クラウド送信前確認ダイアログの provider 分岐は if/elif/else の3分岐（gemini/runpod/claude既定）で統一し、新規プロバイダ追加時もこの並びに elif を挿入する"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "runpod_model が空文字のとき見積りモデル名は 'runpod' 固定文字列にフォールバック（_lookup_price は未知モデルを _PRICE_FALLBACK で吸収し例外を投げない）"
  - "runpod_url 未設定時のプレースホルダは新規 LANG キー llm_runpod_host_unset とし、api.anthropic.com への誤フォールバックを避ける"

patterns-established:
  - "_make_confirm_stub（tests/test_provider_ui.py）を provider/runpod_url/runpod_model 引数で拡張し _confirm_summary_cost も束縛するパターン。以後 provider 別の送信先開示テストを追加する際はこのスタブを再利用する"

requirements-completed: [V171-KEY-01, V171-KEY-02, V171-KEY-04, V171-TEST-02]

coverage:
  - id: D1
    description: "_confirm_cost が RunPod 選択時に host=runpod_url・model=runpod_model を開示し api.anthropic.com/claude_model へフォールスルーしない（CR-01解消）"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestConfirmCost::test_confirm_cost_runpod_shows_runpod_host"
        status: pass
    human_judgment: false
  - id: D2
    description: "_confirm_summary_cost が RunPod 選択時に host=runpod_url を開示し api.anthropic.com へフォールスルーしない"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestConfirmCost::test_confirm_summary_cost_runpod_shows_runpod_host"
        status: pass
    human_judgment: false
  - id: D3
    description: "runpod_url 未設定時、host は llm_runpod_host_unset のプレースホルダになり api.anthropic.com にならない"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestConfirmCost::test_confirm_cost_runpod_url_unset_shows_placeholder"
        status: pass
    human_judgment: false
  - id: D4
    description: "_provider_display_name が runpod でローカライズ済みラベル ocr_provider_name_runpod を返す（WR-02）"
    verification:
      - kind: unit
        ref: "tests/test_lang_parity.py (ja/en キー数一致・グリーン)"
        status: pass
    human_judgment: false
  - id: D5
    description: "RunPod 実クラウド OCR/サマリ実行時に送信前確認ダイアログの送信先表示が実際の runpod_url と一致することの実描画目視"
    verification: []
    human_judgment: true
    rationale: "Tkinter実描画・実APIキー投入を伴う人手確認（プランのManual-Onlyセクションに明記・非ブロッキング）"

duration: 約15分
completed: 2026-07-04
status: complete
---

# Phase 1 Plan 4: RunPod送信先確認ダイアログのCR-01ギャップ閉塞 Summary

**`_confirm_cost`/`_confirm_summary_cost` に `elif name == "runpod":` 分岐を追加し、RunPod選択時に `api.anthropic.com`/claudeモデルを誤開示していたCritical欠陥（01-REVIEW.md CR-01）を解消**

## Performance

- **Duration:** 約15分
- **Started:** 2026-07-04T17:01:00Z (概算)
- **Completed:** 2026-07-04T17:16:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `_confirm_cost`/`_confirm_summary_cost` の両方に `elif name == "runpod":` 分岐を追加し、host は `runpod_url`、model（`_confirm_cost` のみ）は `runpod_model` から取得するよう修正（CR-01解消）
- `runpod_url` 未設定時は新規 LANG キー `llm_runpod_host_unset` のプレースホルダを表示し、`api.anthropic.com` への誤フォールバックを構造的に排除
- `_provider_display_name` に runpod 分岐を追加し、生の `"runpod"` 文字列ではなくローカライズ済み `ocr_provider_name_runpod`（"RunPod (Serverless)"）を返すよう修正（WR-02）
- `TestConfirmCost` を拡張し、RunPod選択時の送信先/モデル開示・未設定時プレースホルダの3ケースを回帰テストとして追加。既存claude/geminiケースは無改変で継続グリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: _confirm_cost / _confirm_summary_cost に runpod 分岐を追加し、_provider_display_name の runpod 表示名と新規 LANG キーを整備する** - `9f13287` (fix)
2. **Task 2: TestConfirmCost を拡張し、_confirm_cost / _confirm_summary_cost の runpod 送信先開示を回帰テストで担保する** - `117ca42` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pagefolio/ocr_dialog.py` - `_confirm_cost`/`_confirm_summary_cost` に runpod 分岐追加・`_provider_display_name` に runpod 分岐追加
- `pagefolio/lang.py` - `llm_runpod_host_unset`・`ocr_provider_name_runpod` を ja/en 両辞書に追加
- `tests/test_provider_ui.py` - `_make_confirm_stub` を provider/runpod_url/runpod_model 引数へ拡張し `_confirm_summary_cost` も束縛。RunPod送信先開示の回帰テスト3件を追加

## Decisions Made
- runpod_model が空文字/未設定のとき見積りモデル名は固定文字列 `"runpod"` にフォールバック（`_lookup_price` は未知モデルでも `_PRICE_FALLBACK` を返し例外を投げないため安全）
- `_confirm_summary_cost` は元々 model を扱わない（char_count のみ）ため、runpod 分岐は host のみ算出（`_confirm_cost` と非対称だが元設計を踏襲）

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 01-REVIEW.md の CR-01（Critical・唯一のBlocker）を解消。フルスイート 728 件グリーン（725 baseline + 3 新規）・`ruff check .`/`ruff format --check .` ともにクリーン
- 残る WR-01/WR-03/WR-04（Warning・本フェーズ範囲外の既存挙動）は今回のスコープ外として次回棚卸し対象に据え置き
- Manual-Only 項目（RunPod実クラウドOCR/サマリの実描画目視3件）は人手確認待ちだが非ブロッキング

---
*Phase: 01-api-llm*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: .planning/phases/01-api-llm/01-04-SUMMARY.md
- FOUND: commit 9f13287
- FOUND: commit 117ca42
