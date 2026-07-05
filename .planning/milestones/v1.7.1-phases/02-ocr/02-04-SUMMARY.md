---
phase: 02-ocr
plan: 04
subsystem: ocr
tags: [ocr, producer-consumer, threading, queue, refactor, pure-logic-layer]

requires:
  - phase: 02-01
    provides: "PluginManager.get_ocr_provider/list_ocr_providers 公開アクセサ（本プランは未使用だが同フェーズの土台）"
  - phase: 02-02
    provides: "TesseractProvider 段階的縮退・OCRDialog 非モーダル注記パターン"
  - phase: 02-03
    provides: "_require_http_scheme・_probe_lm_provider・ClaudeProvider ページネーション（本プランは独立に L-1 を解消）"
provides:
  - "pagefolio/ocr_pipeline.py（Tk/fitz 非依存の producer-consumer 純ロジック層）: PipelineState / consume_one / try_enqueue / send_sentinels"
  - "ocr_dialog.py の _render_next_page / _worker を ocr_pipeline 経由の薄いラッパーへ縮小（D-01）"
  - "L-6a: レンダー失敗ページでも進捗が全ページ数（100%）に到達する"
  - "L-6g: fatal 確定後は producer が残ページの render を継続しない"
  - "L-6h: sentinel 容量不変条件を ocr_pipeline.py の docstring に明文化"
  - "ocr.py の未使用 run_with_bounded_buffer 削除（producer-consumer 二重実装解消）"
affects: []

tech-stack:
  added: []
  patterns:
    - "Tk/fitz 非依存の producer-consumer 純ロジック層（pagination.py/md_render.py/undo_store.py と同格のパターン・ocr_pipeline.py）"
    - "PipelineState（Lock 保護の共有カウンタ・fatal/サーキットブレーカー判定を1クラスへ集約）"
    - "consume_one によるリトライ/バックオフ/fatal 判定の関数化（コールバック境界で UI 層から分離）"
    - "try_enqueue/send_sentinels による非ブロッキング enqueue/sentinel 送出の共通化（部分送出可能・呼び出し元が再試行）"

key-files:
  created:
    - pagefolio/ocr_pipeline.py
    - tests/test_ocr_pipeline.py
  modified:
    - pagefolio/ocr.py
    - pagefolio/ocr_dialog.py
    - tests/test_ocr.py
    - CLAUDE.md
    - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md

key-decisions:
  - "D-01 の核心どおり ocr_dialog.py の実戦挙動（非ブロッキング put・世代ガード・waiting 進捗・skip status・render 失敗時の挙動）を仕様として ocr_pipeline.py を書き直した（逆方向は取らなかった）"
  - "producer 側のスレッドモデルは規定せず、ocr_dialog.py のメインスレッド after() 連鎖のまま維持（V14-D-05・Pitfall 1 回避）。ocr_pipeline.py は enqueue/sentinel の薄いユーティリティのみ提供"
  - "consume_one が PipelineState への state 更新（record_success/record_retryable_failure/record_fatal/record_page_error）を内部で完結させ、dialog 側コールバック（on_success/on_page_error）は results/errors 辞書のブックキーピングのみ担当する設計にし二重計上を防止した"
  - "L-6a のレンダー失敗計上は _skipped_pages と同型の _render_failed_pages 集合 + _render_failed_base（再開時基準）で実装し、_done_disp() ヘルパーに done_count+skip+render_failed の合算式を一元化（_render_next_page 2箇所・_worker 1箇所で共有）"
  - "TestProducerConsumerMemory（run_with_bounded_buffer 専用）と TestCircuitBreaker（サーキットブレーカートリップ判定）は tests/test_ocr_pipeline.py へ移設・PipelineState 直接テストへ置換した。ocr_dialog.py 側は TestRecordCallbacks として results/errors 辞書ブックキーピングのみを検証する薄いテストへ再編（両者ともロジック移動に伴う正当な移設・D-02）"

patterns-established:
  - "producer-consumer の共有状態は PipelineState 経由でのみ更新し、UI 層のコールバックは辞書ブックキーピングのみに限定する（二重計上防止の構造的ガード）"

requirements-completed: [V171-OCR-04]

coverage:
  - id: D1
    description: "producer-consumer ロジックが pagefolio/ocr_pipeline.py（Tk/fitz 非依存）の単一実装に一本化される"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "tests/test_ocr_pipeline.py::TestPipelineState, TestEnqueueHelpers, TestConsumeOne, TestProducerConsumerMemory"
        status: pass
    human_judgment: false
  - id: D2
    description: "ocr_dialog.py の _render_next_page / _worker が ocr_pipeline の関数/PipelineState を呼ぶ薄いラッパーへ縮小される"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "pytest tests/test_ocr.py -q（TestWorkerConcurrency・TestRenderNextPageQueueFullInvariant・TestForceOcrOption 他）"
        status: pass
    human_judgment: false
  - id: D3
    description: "レンダー失敗ページがあっても進捗が全ページ数（100%）に到達する（L-6a）"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "tests/test_ocr_pipeline.py::TestPipelineHardening::test_render_failure_progress"
        status: pass
    human_judgment: false
  - id: D4
    description: "fatal 発生後は producer が残ページの render を継続せず終了へ向かう（L-6g）"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "pagefolio/ocr_dialog.py _render_next_page の is_fatal() 分岐（grep 検証済み・専用ユニットテストは Tk 依存のため回帰網羅に依拠）"
        status: pass
    human_judgment: false
  - id: D5
    description: "sentinel（終了シグナル）の容量不変条件が ocr_pipeline.py の docstring に明文化される（L-6h）"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "tests/test_ocr_pipeline.py::TestEnqueueHelpers::test_send_sentinels_partial_when_full"
        status: pass
    human_judgment: false
  - id: D6
    description: "run_with_bounded_buffer が削除され本番未使用の二重実装が解消される"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "grep -rn \"run_with_bounded_buffer\" pagefolio/ （0件）"
        status: pass
    human_judgment: false
  - id: D7
    description: "既存 OCR テスト群（並列・キャンセル・進捗・リトライ）が回帰なくグリーン、フルスイートも回帰なし"
    requirement: "V171-OCR-04"
    verification:
      - kind: unit
        ref: "pytest -q（780件）・pytest tests/test_ocr.py tests/test_ocr_pipeline.py tests/test_ocr_providers.py tests/test_provider_ui.py tests/test_plugins.py -q（488件）"
        status: pass
    human_judgment: false

duration: 約55分
completed: 2026-07-05
status: complete
---

# Phase 02 Plan 04: producer-consumer 一本化（L-1）+ L-6a/L-6g/L-6h 同時解消 Summary

**producer-consumer の二重実装（ocr.py の未使用ヘルパー vs ocr_dialog.py 実戦実装）を新モジュール ocr_pipeline.py（Tk/fitz 非依存）へ一本化し、レンダー失敗時の進捗停滞（L-6a）・fatal 後の render 継続（L-6g）を同時修正、sentinel 容量不変条件（L-6h）を明文化**

## Performance

- **Duration:** 約55分
- **Started:** 2026-07-05T01:41:00Z (推定)
- **Completed:** 2026-07-05T02:36:00Z
- **Tasks:** 3 completed（Task 3 は検証専用・コード変更なし）
- **Files modified:** 7（新設2 / 修正5）

## Accomplishments
- `pagefolio/ocr_pipeline.py` を新設。`PipelineState`（Lock 保護の共有カウンタ・fatal/サーキットブレーカー判定）・`consume_one`（1アイテム消費のリトライ/バックオフ/fatal 判定）・`try_enqueue`/`send_sentinels`（非ブロッキング enqueue/sentinel 送出）を Tk/fitz 非依存の純ロジック層として実装（D-01/D-02）
- `tests/test_ocr.py` の `TestProducerConsumerMemory`（`run_with_bounded_buffer` 専用テスト3件）を `tests/test_ocr_pipeline.py` へ移設し新 API へ書き換え、`render_failure_progress`/`cancel_finite_time_no_deadlock` を新規追加（計17テスト）
- `pagefolio/ocr_dialog.py` の `_render_next_page`/`_worker` を `ocr_pipeline` の関数/`PipelineState` を呼ぶ薄いラッパーへ縮小。散在していた `_done_lock`/`_done_count`/`_workers_remaining`/`_fatal_msg`/`_fatal_kind`/`_consec_err_count` を `self._pstate`（`PipelineState` インスタンス）へ集約
- L-6a: `_render_next_page` の render 失敗 except 節で `_render_failed_pages` へページを計上し progress_var/progress_bar を更新（`_done_disp()` ヘルパーに done_count+skip+render_failed の合算式を一元化）
- L-6g: `_render_next_page` 冒頭に `self._pstate.is_fatal()` 分岐を追加し、fatal 確定後は残ページの render を継続せず sentinel を送出して終了へ向かうようにした
- L-6h: `ocr_pipeline.py` のモジュール docstring に sentinel 容量不変条件（終端シグナルは合計 workers 本・送信済み分は再送しない・バッファ満杯時は部分送出）を明文化
- `pagefolio/ocr.py` の未使用ヘルパー `run_with_bounded_buffer`（本番未参照・テストのみ消費）を削除し、不要になった `queue` import も除去
- `CLAUDE.md` のファイル構成表・OCR モジュール群表に `ocr_pipeline.py`/`test_ocr_pipeline.py` を追記
- `260610-aaa-REVIEW.md` の L-1・L-6a・L-6g・L-6h に解消済みマーク + コミットハッシュを追記（D-12）
- Task 3（回帰ゲート）: OCR テスト群（488件）・フルスイート（780件）・ruff check/format すべてグリーンを確認（コード変更なし）

## Task Commits

Each task was committed atomically:

1. **Task 1: ocr_pipeline.py 新設 + 既存 bounded buffer テスト移設・拡充** - `c4cd9da` (feat)
2. **Task 2: ocr_dialog.py 薄いラッパー化 + L-6a/L-6g 修正 + ocr.py 未使用ヘルパー削除 + CLAUDE.md/REVIEW.md 追記** - `ae97aaa` (feat)
3. **Task 3: 回帰ゲート（既存 OCR テスト群グリーン維持の単独検証）** - コード変更なし（検証のみ・全項目グリーン）

## Files Created/Modified
- `pagefolio/ocr_pipeline.py` - 新設: `PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`（Tk/fitz 非依存の producer-consumer 純ロジック層）
- `tests/test_ocr_pipeline.py` - 新設: `PipelineState`/enqueue ヘルパー/`consume_one`/移設 producer-consumer テスト/拡充テスト（17件）
- `pagefolio/ocr.py` - `run_with_bounded_buffer` 削除・不要になった `queue` import 除去
- `pagefolio/ocr_dialog.py` - `_render_next_page`/`_worker`/`_start_worker_thread` を `ocr_pipeline` 経由へ縮小。`_record_page_success`/`_record_page_error`（辞書ブックキーピング専用）・`_done_disp()` ヘルパーを新設。`__init__`/`_clear_text`/`_on_run` の共有状態初期化を `self._pstate` へ一本化
- `tests/test_ocr.py` - `TestProducerConsumerMemory`/`TestCircuitBreaker` を移設・再編（`TestRecordCallbacks` へ縮小）。`TestWorkerConcurrency`/`TestClearResetsFatalState`/`TestOcrDialogOnRun`/`TestRenderNextPageQueueFullInvariant`/`TestForceOcrOption` の fake を `_pstate` ベースへ更新
- `CLAUDE.md` - ファイル構成表・OCR モジュール群表に `ocr_pipeline.py`/`test_ocr_pipeline.py` を追記
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-1・L-6a・L-6g・L-6h に解消済みマーク+コミットハッシュを追記

## Decisions Made
- D-01 の核心どおり `ocr_dialog.py` の実戦挙動を仕様として `ocr_pipeline.py` を書き直した（ヘルパー側の理想仕様に dialog を寄せる逆方向は不採用・Pitfall 1）
- producer 側のスレッドモデルは規定せず、`ocr_dialog.py` のメインスレッド `after()` 連鎖のまま維持（V14-D-05 制約・Pitfall 1 回避）。`ocr_pipeline.py` は enqueue/sentinel の薄いユーティリティのみ提供し、専用 producer スレッドを内部に持たない
- `consume_one` が `PipelineState` への state 更新（成功/リトライ失敗/fatal/ページエラー）を内部で完結させ、dialog 側コールバック（`on_success`/`on_page_error`）は `results`/`errors` 辞書のブックキーピングのみを担当する設計にして二重計上を防止した
- L-6a のレンダー失敗計上は `_skipped_pages` と同型の `_render_failed_pages` 集合 + `_render_failed_base`（再開時基準）で実装し、`_done_disp()` ヘルパーに `done_count + skip + render_failed` の合算式を一元化（`_render_next_page` の2箇所・`_worker` の1箇所で共有し二重実装を避けた）
- `TestProducerConsumerMemory`（`run_with_bounded_buffer` 専用）と `TestCircuitBreaker`（サーキットブレーカートリップ判定）は `tests/test_ocr_pipeline.py` へ移設・`PipelineState` 直接テストへ置換した。`ocr_dialog.py` 側は `TestRecordCallbacks` として `results`/`errors` 辞書ブックキーピングのみを検証する薄いテストへ再編（両者ともロジック移動に伴う正当な移設であり、既存 OCR テスト群の意図＝並列・キャンセル・進捗・リトライの回帰なし、は維持されている）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TestCircuitBreaker`/複数 fake のアーキテクチャ非互換を修正**
- **Found during:** Task 2（`ocr_dialog.py` の PipelineState 一本化）
- **Issue:** `tests/test_ocr.py` の複数の SimpleNamespace fake（`TestWorkerConcurrency`・`TestClearResetsFatalState`・`TestOcrDialogOnRun`・`TestRenderNextPageQueueFullInvariant`・`TestForceOcrOption`・`TestCircuitBreaker`）が旧フラット属性（`_done_lock`/`_done_count`/`_workers_remaining`/`_fatal_msg`/`_fatal_kind`/`_consec_err_count`）に依存しており、`self._pstate` への一本化後は `AttributeError`/アサーション不一致で全て赤化する状態だった
- **Fix:** 各 fake を `_pstate=PipelineState(...)` ベースへ更新し、アサーションも `fake._pstate.xxx` を参照する形へ書き換え。`TestCircuitBreaker`（サーキットブレーカートリップ判定）は既に `tests/test_ocr_pipeline.py::TestPipelineState` で同等以上に検証済みのため、`TestRecordCallbacks`（results/errors 辞書ブックキーピングのみ検証）へ再編した
- **Files modified:** tests/test_ocr.py
- **Verification:** `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_ocr_pipeline.py -q` 255件グリーン、フルスイート780件グリーン
- **Committed in:** ae97aaa (Task 2 commit)

---

**Total deviations:** 1 auto-fixed（Rule 1: 既存テストのアーキテクチャ変更への追従・PipelineState 一本化に伴う正当な移設）
**Impact on plan:** D-01 が要求する「dialog 側の実戦挙動を仕様として一本化」を完遂するために必須の追従であり、スコープ逸脱はない。ロジック自体（circuit breaker trip・render 失敗計上等）はすべて test_ocr_pipeline.py または test_ocr.py 側で同等以上にカバーされている。

## Issues Encountered
None - 計画どおり実行し、既存テストの追従修正（上記デビエーション）以外の問題は発生しなかった。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V171-OCR-04（L-1 producer-consumer 一本化）完了。L-6a/L-6g/L-6h も同時解消（D-03）
- Phase 02（OCR 磨き込み）の全4プラン（02-01〜02-04）完了。V171-OCR-01〜04 すべて充足
- V14-D-05/06（fitz メインスレッドのみ・バッファ上限 concurrency+1）は一本化後も維持されている

---
*Phase: 02-ocr*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files confirmed present on disk. All commit hashes (c4cd9da, ae97aaa) confirmed present in git log.
