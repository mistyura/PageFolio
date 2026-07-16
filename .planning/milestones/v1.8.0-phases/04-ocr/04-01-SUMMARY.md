---
phase: 04-ocr
plan: 01
subsystem: ocr
tags: [batch-ocr, pure-logic-layer, threading-lock, tdd]

# Dependency graph
requires:
  - phase: 03-ocr-e2e
    provides: OCRRunEngine（ファイルごとに新規生成して再利用する per-run 独立原則の設計根拠）
provides:
  - "pagefolio/batch_ocr_state.py（Tk/fitz 非依存の純ロジック層）"
  - "BatchFileEntry / BatchState / enqueue_files / count_pending / STATUS_* 定数"
affects: [04-02-batch-ocr-dialog, 04-03-batch-summary-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "純ロジック層（Tk/fitz 非依存）+ threading.Lock 保護カウンタ（ocr_pipeline.py の PipelineState を踏襲）"
    - "per-file 状態を独立保持し使い回さない（ocr_engine.py の per-run 新規生成原則のファイル単位外挿）"

key-files:
  created:
    - pagefolio/batch_ocr_state.py
    - tests/test_batch_ocr_state.py
  modified: []

key-decisions:
  - "count_pending(entries) を新設し STATUS_PENDING のみを実行対象=分母として算入。STATUS_ERROR（壊れたPDF）は BatchState.total_files から除外され、remaining() が完了時に必ず0へ収束する契約を確立（レビュー懸念6反映）"
  - "BatchFileEntry.status は生成時 STATUS_PENDING固定。壊れたPDFは page_count=0 の代わりに STATUS_ERROR として明示的に表現できる設計とした（Open Question 2）"

patterns-established:
  - "BatchState.files_done()（ファイル軸）と OCRRunEngine.progress_count()（ページ軸）は完全に独立したカウンタとして扱い、どちらか一方から他方を逆算しない（落とし穴5の構造的予防）"

requirements-completed: [V180-BATCH-01, V180-BATCH-02]

coverage:
  - id: D1
    description: "enqueue_files による重複除外つきキュー投入（同一パス再投入は不増加・空リストは no-op・page_counts反映）"
    requirement: V180-BATCH-01
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestEnqueueFiles::test_enqueue_files"
        status: pass
    human_judgment: false
  - id: D2
    description: "BatchFileEntry の初期状態は STATUS_PENDING、STATUS定数5種は全て相異なる文字列"
    requirement: V180-BATCH-02
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestStateTransitions::test_state_transitions"
        status: pass
    human_judgment: false
  - id: D3
    description: "BatchState の mark_completed/mark_failed/mark_cancelled で files_done() が単調増加しtotal_filesを超えない・remaining()が正しく収束する"
    requirement: V180-BATCH-02
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestProgressAggregation::test_progress_aggregation"
        status: pass
    human_judgment: false
  - id: D4
    description: "壊れた/開けないPDFを page_count=0 の代わりに STATUS_ERROR として表現できる"
    requirement: V180-BATCH-02
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestBrokenPdfErrorStatus::test_broken_pdf_error_status"
        status: pass
    human_judgment: false
  - id: D5
    description: "count_pending が STATUS_ERROR を除外し、BatchState.total_files をこの値で構築するとremaining()が完了時0へ収束する（レビュー懸念6の進捗収束保証）"
    requirement: V180-BATCH-02
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestErrorFileExcludedFromTotal::test_error_file_excluded_from_total"
        status: pass
    human_judgment: false
  - id: D6
    description: "batch_ocr_state.py はトップレベルで tkinter / fitz を import しない（純ロジック層のbackstop）"
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_state.py::TestNoTkFitzToplevelImport::test_no_tk_fitz_toplevel_import"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-07-15
status: complete
---

# Phase 4 Plan 1: バッチOCRファイルキュー純ロジック層 Summary

**BatchFileEntry/BatchState/enqueue_files/count_pending を提供するTk/fitz非依存の純ロジック層 `pagefolio/batch_ocr_state.py` をTDD（RED→GREEN）で新設し、ファイル軸進捗集計とSTATUS_ERROR除外による進捗収束を6単体テストで固めた**

## Performance

- **Duration:** 8分
- **Started:** 2026-07-15T12:08:00Z
- **Completed:** 2026-07-15T12:16:07Z
- **Tasks:** 2
- **Files modified:** 2（新規2）

## Accomplishments
- `pagefolio/batch_ocr_state.py` を新規作成し、`BatchFileEntry`（path/display_name/page_count/status/results/errors）・`BatchState`（total_files/completed/failed/cancelled + mark_*/files_done/remaining）・`enqueue_files`（dedupつきキュー投入）・`count_pending`（STATUS_PENDINGのみ算入）・STATUS_PENDING/RUNNING/DONE/FAILED/ERROR 定数を提供
- `BatchState.files_done()`（ファイル軸）と `OCRRunEngine.progress_count()`（ページ軸）を完全に独立したカウンタとして設計し、落とし穴5（進捗二重集計の矛盾）を構造的に予防
- `count_pending` により STATUS_ERROR（壊れたPDF）が `BatchState.total_files` の分母から除外され、`remaining()` が実行完了時に必ず0へ収束する契約を確立（レビュー懸念6反映）
- TDD RED→GREEN フローを厳守: Task 1 で6テストを先行作成し `ModuleNotFoundError` によるRED（構文エラーではない）を確認、Task 2 実装後に全6テストGREEN化

## Task Commits

Each task was committed atomically:

1. **Task 1: test_batch_ocr_state.py を先行作成（Wave 0 / RED テスト先行）** - `e41c648` (test)
2. **Task 2: batch_ocr_state.py を実装してテストを GREEN 化** - `774fe2b` (feat)

_Note: TDD タスクのため test → feat の2コミット構成（refactor不要のため無し）_

## Files Created/Modified
- `pagefolio/batch_ocr_state.py` - バッチOCRファイルキューの状態遷移・ファイル軸進捗集計を担う純ロジック層（BatchFileEntry/BatchState/enqueue_files/count_pending/STATUS定数）
- `tests/test_batch_ocr_state.py` - 上記6項目の単体テスト（RED先行作成→実装でGREEN化）

## Decisions Made
- `count_pending(entries)` を新設し STATUS_PENDING のみを実行対象＝分母として算入。04-02 が `BatchState(total_files=count_pending(entries))` を構築する際 STATUS_ERROR を除外し `remaining()` の完了時0収束を保証する契約とした（プラン Review Incorporation・懸念6反映）
- `BatchFileEntry` は per-file 状態（results/errors 含む）を独立保持し使い回さない設計とし、`ocr_engine.py` の D-09/D-11「実行ごとに新規生成」原則をファイル単位へ外挿した

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - `ruff format` が2箇所の行長超過（E501）を自動整形で解消した以外、追加の問題は発生しなかった（フォーマッタの通常動作の範囲内でありRule 1-3の逸脱ではない）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `pagefolio/batch_ocr_state.py` の `BatchFileEntry`/`BatchState`/`enqueue_files`/`count_pending`/STATUS定数が確立され、04-02（BatchOCRDialog コア実装）から直接 import して利用できる状態
- `count_pending` によるSTATUS_ERROR除外契約は04-02の集約コスト確認ダイアログ（D-03、STATUS_ERRORをページ合計から除外する設計）と整合済み
- ブロッカーなし。フルスイート1003件green・ruffクリーンで次プランへ進行可能

---
*Phase: 04-ocr*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: pagefolio/batch_ocr_state.py
- FOUND: tests/test_batch_ocr_state.py
- FOUND commit: e41c648
- FOUND commit: 774fe2b
