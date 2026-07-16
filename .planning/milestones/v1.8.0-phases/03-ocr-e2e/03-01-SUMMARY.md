---
phase: 03-ocr-e2e
plan: 01
subsystem: ocr
tags: [ocr, threading, producer-consumer, refactor, tkinter, pymupdf]

# Dependency graph
requires:
  - phase: 01-foundation-split
    provides: Tk/fitz 非依存の純ロジック層への分割方針（pagination.py/undo_store.py 前例）
  - phase: 02-ai
    provides: 現行 ocr_dialog.py の状態（テンプレート/フォールバック機能追加後の2520行版）
provides:
  - "OCRRunEngine（pagefolio/ocr_engine.py）: producer-consumer の consumer 駆動部（Tk/fitz 非依存・queue/PipelineStateを一度だけ生成して公開）"
  - "OCRDialog の Engine 委譲ラッパー化（_start_worker_thread/_render_next_page/_retry_sentinels）"
  - "完了理由別アダプタ + メインスレッド finalizer パターン（_on_engine_*/_safe_finish_*）"
affects: [04-batch-ocr, 03-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk/fitz 非依存 consumer 駆動軽量クラス（pagination.py/ocr_pipeline.py/undo_store.py と同格の純ロジック層系譜への新規参加）"
    - "ワーカースレッド側は世代ガード評価 + after(0,...) 投函のみ、winfo_exists() はメインスレッド finalizer 側でのみ呼ぶ二段構成"

key-files:
  created:
    - pagefolio/ocr_engine.py
    - tests/test_ocr_engine.py
  modified:
    - pagefolio/ocr_dialog.py
    - tests/test_ocr.py

key-decisions:
  - "queue.Queue/PipelineState は OCRRunEngine.start() 内で一度だけ生成し self.queue プロパティで公開。producer(OCRDialog._render_next_page)は self._engine.queue のみを参照（落とし穴10・T-03-02 対応）"
  - "self._pstate は Engine 抽出後も後方互換のため vestigial 属性として維持（_clear_text/_on_run が None へリセットする既存の観測可能な挙動・既存回帰テストとの互換性を優先）"
  - "_skip_base/_render_failed_base は完全に削除（Engine が実行ごとに新規生成されるため D-11/D-12 によりベースライン差分計算が構造的に不要）"

patterns-established:
  - "OCRRunEngine: 単一ファイル OCR とバッチ OCR（Phase 4）で共用可能な consumer 実行エンジン。ファイルごとに新規生成して再利用する設計"

requirements-completed: [V180-REFAC-03]

coverage:
  - id: D1
    description: "OCRRunEngine が pagefolio.ocr_engine から単独 import 可能で、Tk/fitz に一切依存しない（トップレベル import は threading/queue/logging と pagefolio.ocr_pipeline のみ）"
    requirement: "V180-REFAC-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineUnit::test_engine_importable"
        status: pass
    human_judgment: false
  - id: D2
    description: "単一ページ OCR 成功で on_success コールバックが1回呼ばれ、engine.results に結果が格納される"
    requirement: "V180-REFAC-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineUnit::test_single_page_success_invokes_on_success"
        status: pass
    human_judgment: false
  - id: D3
    description: "producer（OCRDialog._render_next_page）と consumer（Engine ワーカー）が同一 queue.Queue インスタンスを共有する（落とし穴10 の同一性検証）"
    requirement: "V180-REFAC-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineUnit::test_queue_is_single_shared_instance"
        status: pass
      - kind: integration
        ref: "tests/test_ocr.py::TestWorkerConcurrency::test_termination_signals_match_concurrency"
        status: pass
    human_judgment: false
  - id: D4
    description: "concurrency>1 で全ページ成功後、最終ワーカーのみが on_complete をちょうど1回呼ぶ（CR-01 単一終了処理保証）"
    requirement: "V180-REFAC-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineUnit::test_final_worker_calls_on_complete_once"
        status: pass
    human_judgment: false
  - id: D5
    description: "OCRDialog が OCRRunEngine への委譲ラッパー化後も、単一ファイル OCR の進捗・キャンセル・リトライ・resume・fatal 挙動が抽出前と同一のまま維持される（既存回帰テスト群 + フルスイート）"
    requirement: "V180-REFAC-03"
    verification:
      - kind: integration
        ref: "pytest tests/test_provider_ui.py tests/test_ocr_fallback.py tests/test_ocr.py tests/test_ocr_pipeline.py tests/test_ocr_engine.py -x (326 passed)"
        status: pass
      - kind: integration
        ref: "pytest (991 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "単一ファイル OCR の実行・進捗・キャンセル・リトライの GUI 実機動作"
    verification: []
    human_judgment: true
    rationale: "Tkinter GUI はヘッドレス pytest で駆動不可（03-VALIDATION.md Manual-Only Verifications に明記済み・既存方針どおり）"

# Metrics
duration: 約32分
completed: 2026-07-15
status: complete
---

# Phase 3 Plan 1: OCRRunEngine 抽出 Summary

**producer-consumer の consumer 駆動部を新設 `pagefolio/ocr_engine.py` の `OCRRunEngine` へ抽出し、`OCRDialog` を薄い委譲ラッパー化（producer/consumer のキューは `self._engine.queue` に一本化）**

## Performance

- **Duration:** 約32分
- **Started:** 2026-07-15T04:51:00+09:00 (推定)
- **Completed:** 2026-07-15T05:23:08+09:00
- **Tasks:** 2
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments
- `pagefolio/ocr_engine.py` を新設し `OCRRunEngine`（Tk/fitz 非依存の consumer 駆動軽量クラス）を実装。`queue.Queue`/`PipelineState` を `start()` 内で一度だけ生成して `self.queue` プロパティで公開し、既存の `pagefolio.ocr_pipeline`（`PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`）をそのまま呼び出す薄い consumer レイヤーとして実装した
- `tests/test_ocr_engine.py` に `TestOCRRunEngineUnit`（4テスト: import・単一ページ成功・キュー同一性・最終ワーカー単一 on_complete）を新設し、RED→GREEN で固定した
- `OCRDialog._start_worker_thread` を `OCRRunEngine` 生成 + `start()` の委譲ラッパーへ置換し、旧 `_worker` メソッドを削除した
- producer（`_render_next_page`）・`_retry_sentinels` のキュー参照を `self._engine.queue` に一本化（落とし穴10・T-03-02 対応）
- 完了理由別コールバック（`on_complete`/`on_cancelled`/`on_fatal`）を受け取るアダプタ（`_on_engine_complete`/`_on_engine_cancelled`/`_on_engine_fatal`）とメインスレッド finalizer（`_safe_finish_complete`/`_safe_finish_cancelled`/`_safe_finish_error`）を新設し、ワーカースレッド側では `winfo_exists()` を呼ばず世代ガード + `after(0, ...)` 投函のみを行う構成にした（REVIEW MEDIUM 対応）
- `_skip_base`/`_render_failed_base` を完全に削除（Engine が実行ごとに新規生成されるためベースライン差分計算が構造的に不要・REVIEW LOW 対応）

## Task Commits

Each task was committed atomically:

1. **Task 1: OCRRunEngine（consumer 駆動の軽量クラス）を新設し unit スモークで固定** - `7052edc` (feat)
2. **Task 2: OCRDialog を Engine 委譲ラッパー化（producer 残留・キュー一本化・完了アダプタ）** - `d8c9e2c` (refactor)

**Plan metadata:** (this commit) - `docs: complete 03-01 plan`

## Files Created/Modified
- `pagefolio/ocr_engine.py` - `OCRRunEngine`（consumer 駆動の軽量クラス。queue/PipelineState 一元生成・完了理由別コールバック）
- `tests/test_ocr_engine.py` - `TestOCRRunEngineUnit`（4テスト）+ 複製・拡張した `FakeProvider`
- `pagefolio/ocr_dialog.py` - `_start_worker_thread`/`_render_next_page`/`_retry_sentinels` を Engine 委譲へ変更、`_worker` 削除、完了理由別アダプタ+finalizer 新設、`_skip_base`/`_render_failed_base` 削除
- `tests/test_ocr.py` - `TestWorkerConcurrency`/`TestRenderNextPageQueueFullInvariant`/`TestForceOcrOption` の fake を Engine 委譲後の構造（`_engine` スタブ）へ更新（アサーション内容は既存のまま維持）

## Decisions Made
- キュー/PipelineState の生成責任は `OCRRunEngine.start()` に一元化し、producer は `self._engine.queue` のみを参照する方式を採用（03-RESEARCH.md Open Question 1 の推奨解どおり）
- `self._pstate` インスタンス属性は Engine 抽出後も vestigial（実際のロジックは参照しない）属性として維持した。理由: `_clear_text`/`_on_run` が「前回実行の致命的エラー状態を None へリセットする」という既存の観測可能な挙動を検証する既存回帰テスト（`TestClearResetsFatalState`）がこの属性を直接検査しており、削除すると後方互換が壊れるため。実際の共有状態は完全に `self._engine`（`OCRRunEngine._pstate`）が所有する
- `_skip_base`/`_render_failed_base` は Engine 側で D-11（実行ごとの新規生成）により構造的に不要になったため完全に削除した（プラン記載どおり）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_ocr_engine.py の sentinel 送出をキュー容量に合わせて再試行方式へ修正**
- **Found during:** Task 1（TDD の GREEN フェーズ・`test_final_worker_calls_on_complete_once`）
- **Issue:** `queue.Queue(maxsize=concurrency+1)` に対し、2ページ分の enqueue 後に `send_sentinels(engine.queue, 2)` を1回だけ呼ぶと、バッファ上限（3）に対し2アイテム+1本しか入らず1本しか送出されない（部分送出）。テストが `sent == 2` を期待していたため失敗した
- **Fix:** `_send_all_sentinels` ヘルパー（`pagefolio/ocr_dialog.py` の `_retry_sentinels` と同型の再試行ループ）をテストに追加し、consumer がアイテムを消費して空きができるまで待って残数を再送するようにした
- **Files modified:** tests/test_ocr_engine.py
- **Verification:** `pytest tests/test_ocr_engine.py::TestOCRRunEngineUnit -x` が4件グリーン
- **Committed in:** 7052edc (Task 1 commit)

**2. [Rule 1 - Bug] 既存テスト（tests/test_ocr.py）の内部構造依存 fake を Engine 委譲後の構造へ更新**
- **Found during:** Task 2（委譲後のフルスイート実行で発覚）
- **Issue:** `TestWorkerConcurrency`（2テスト）・`TestRenderNextPageQueueFullInvariant`（1テスト）・`TestForceOcrOption`（2テスト）が `_start_worker_thread`/`_render_next_page` を直接呼び出すテストで、旧内部属性（`self._render_queue`/`self._pstate`/`_skip_base`/`_render_failed_base`）を持つ `SimpleNamespace` fake を使用していたため、Engine 委譲後の `self._engine.queue`/`self._engine.is_fatal()` 等の参照で `AttributeError` が発生し6件が失敗した
- **Fix:** 各 fake に `_engine`（`.queue`/`.is_fatal()`/`.note_skip()`/`.note_render_failed()`/`.progress_count()` を持つ最小スタブ）を追加し、`_start_worker_thread` 経由のテストには Engine 構築に必要な最小属性（`provider`/`_ocr_prompt`/`_run_pages`/`_cancel_flag`）とコールバック委譲先メソッドのスタブを追加した。既存のアサーション内容（起動スレッド数・終了シグナル数・`_render_idx` 不変条件・スキップ集合の内容）は一切変更していない
- **Files modified:** tests/test_ocr.py
- **Verification:** `pytest tests/test_ocr.py -q` が157件グリーン、フルスイート `pytest` が991件グリーン
- **Committed in:** d8c9e2c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed（Rule 1: バグ修正 × 2）
**Impact on plan:** いずれも「同一ロジックの配置換えのみで観測挙動を変えない」という本フェーズの方針（D-04）を維持するために必要な修正であり、スコープの逸脱はない。plan の `files_modified` には `tests/test_ocr.py` が明記されていなかったが、プラン自身の acceptance criteria（`pytest tests/test_provider_ui.py tests/test_ocr_fallback.py tests/test_ocr.py -x` が green であること）を満たすために直接起因する必須修正だった。

## Issues Encountered
None（上記2件は Deviations として記録済み）

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `OCRRunEngine` は単一ファイル OCR で実運用中の構造を維持したまま抽出済み。Phase 4（バッチ OCR）は `BatchOCRDialog` がファイルごとに `OCRRunEngine` を新規生成して再利用できる（D-01/D-11 の直接の恩恵）
- 03-02（E2E モックテスト）は本プランで確立した `OCRRunEngine`/`FakeProvider` パターンをそのまま基盤にできる
- ブロッカーなし

---
*Phase: 03-ocr-e2e*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_engine.py
- FOUND: tests/test_ocr_engine.py
- FOUND: .planning/phases/03-ocr-e2e/03-01-SUMMARY.md
- FOUND: 7052edc (git log)
- FOUND: d8c9e2c (git log)
