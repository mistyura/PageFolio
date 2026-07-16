---
phase: 03-ocr-e2e
plan: 02
subsystem: testing
tags: [ocr, threading, producer-consumer, e2e, pytest, mock-testing]

# Dependency graph
requires:
  - phase: 03-ocr-e2e
    provides: "OCRRunEngine（03-01 で抽出済みの consumer 駆動軽量クラス）と tests/test_ocr_engine.py の FakeProvider/TestOCRRunEngineUnit 基盤"
provides:
  - "TestOCRRunEngineE2E（tests/test_ocr_engine.py・6シナリオ）: OCRRunEngine 自体を実スレッド駆動で起動する高忠実度 E2E モックテスト"
  - "FakeProvider の complete_text_ex/supports_text_prompt 拡張（サマリ生成カバレッジ・実 API 非依存）"
  - "_drive_engine E2E producer スタブヘルパー（try_enqueue/send_sentinels のみで OCRRunEngine のコードパスを検証）"
affects: [04-batch-ocr]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "E2E モックテストは OCRRunEngine 自体を start() して検証する（テスト専用ドライバの自作ではなく Engine のコードパスを高忠実度で通す・D-13）"
    - "サマリ生成（complete_text_ex）は OCRRunEngine へ統合せず、OCR実行→結果連結→サマリ生成というフロー全体をテストコード側で再現して検証する（Pitfall 4/A2）"

key-files:
  created: []
  modified:
    - tests/test_ocr_engine.py

key-decisions:
  - "producer スタブ（_drive_engine）は cancel_flag を明示チェックしない設計を採用した。consume_one が各アイテム処理開始時に is_fatal()/cancel_flag を再確認するため、producer が全ページを enqueue し終えても、キャンセル/fatal 確定後の残アイテムは consumer 側が API 呼び出し自体をスキップする。producer 側にキャンセルチェックを重複実装する必要がない（既存 consume_one の契約への信頼）"
  - "サーキットブレーカーテストは OCRRetryableError(retry_after=0.01) を使い、clamp_retry_after/interruptible_sleep の実待機時間を極小化してテストを高速化した（1ページあたり MAX_RETRIES=3 回の呼び出し × 3ページで DEFAULT_CIRCUIT_BREAKER_THRESHOLD=3 に到達する構造を利用）"

requirements-completed: [V180-QA-01]

coverage:
  - id: D1
    description: "複数ページ正常系（成功のみ）が OCRRunEngine 経由で全ページ結果を返し on_complete が1回だけ呼ばれる"
    requirement: "V180-QA-01"
    verification:
      - kind: e2e
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_all_pages_success"
        status: pass
    human_judgment: false
  - id: D2
    description: "ページエラー混在（一部ページのみ非リトライ由来の失敗）でも取りこぼしなく成功/エラーへ振り分けられ完了する"
    requirement: "V180-QA-01"
    verification:
      - kind: e2e
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_partial_page_errors"
        status: pass
    human_judgment: false
  - id: D3
    description: "cancel_flag セット後、有限時間内にキャンセルが反映され残ページの ocr_image 呼び出しが行われず on_cancelled 経由で終了する"
    requirement: "V180-QA-01"
    verification:
      - kind: e2e
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_cancel_stops_processing"
        status: pass
    human_judgment: false
  - id: D4
    description: "連続失敗が DEFAULT_CIRCUIT_BREAKER_THRESHOLD に達すると fatal 確定し残ページの API 呼び出しをスキップして on_fatal（circuit_breaker）経由で終了する"
    requirement: "V180-QA-01"
    verification:
      - kind: e2e
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_circuit_breaker_stops_calls"
        status: pass
    human_judgment: false
  - id: D5
    description: "OCR 実行（OCRRunEngine 経由）→ results 連結 → provider.complete_text_ex によるサマリ生成の一気通貫フローが実 API 非依存で成功する"
    requirement: "V180-QA-01"
    verification:
      - kind: e2e
        ref: "tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_ocr_then_summary_flow"
        status: pass
    human_judgment: false
  - id: D6
    description: "フルスイート回帰ゼロ・ruff clean"
    requirement: "V180-QA-01"
    verification:
      - kind: integration
        ref: "pytest (996 passed)"
        status: pass
      - kind: other
        ref: "ruff check . && ruff format --check ."
        status: pass
    human_judgment: false

# Metrics
duration: 約16分
completed: 2026-07-15
status: complete
---

# Phase 3 Plan 2: OCR→サマリ E2E モックテスト Summary

**OCRRunEngine を実スレッド駆動（threading.Thread + queue.Queue）で起動する6シナリオの E2E モックテストを tests/test_ocr_engine.py に追加し、OCR→サマリの一気通貫フローを実 API 非依存で保証**

## Performance

- **Duration:** 約16分
- **Started:** 2026-07-14T20:23:08Z (推定・03-01 完了直後)
- **Completed:** 2026-07-14T20:39:23Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `tests/test_ocr_engine.py` に `TestOCRRunEngineE2E`（5メソッド）を新設し、`OCRRunEngine` 自体を `start()` して実スレッド駆動で検証する E2E モックテストを整備した（D-13: テスト専用ドライバの自作ではなく Engine のコードパスを高忠実度で通す）
- 薄い producer スタブヘルパー `_drive_engine` を新設し、`engine.queue` へ `try_enqueue` → `send_sentinels`（部分送出対応の再試行込み）でページを投入する。consumer 側は `OCRRunEngine.start()` が内部で担う
- 正常系（`test_all_pages_success`）・ページエラー混在（`test_partial_page_errors`）・キャンセル（`test_cancel_stops_processing`）・サーキットブレーカー（`test_circuit_breaker_stops_calls`）・OCR→サマリ一気通貫（`test_ocr_then_summary_flow`）の5シナリオを実装し、既存の単体4テストと合わせて `TestOCRRunEngineE2E` + `TestOCRRunEngineUnit` で計9テストが green
- `FakeProvider`（`tests/test_ocr_engine.py` 内・03-01 で複製済みの1クラス限定）に `supports_text_prompt = True`/`complete_text_ex` を追加し、サマリ生成カバレッジ（D-15）を実 API 非依存で満たした。03-01 で残した「pipeline テストとのカプセル化のため意図的に複製・拡張した」旨のコメントを維持し、サマリ対応拡張分も同じ意図である旨を補足した（レビュー提案対応）
- サマリ生成（`complete_text_ex` 相当）は Pitfall 4/A2 に従い `OCRRunEngine` へ統合せず、「OCR 実行（Engine 経由）→ results 連結 → `provider.complete_text_ex` 呼び出し」というフロー全体をテストコード側で再現する形で検証した
- flaky 対策として全 E2E テストでワーカー join に `timeout=10.0`、producer スレッド join に `timeout=5.0` を適用し、join 後に `not t.is_alive()` を明示アサートして「timeout 内に確実に終了した」ことを検証。アサーションは結果セットの内容ベースで実行時間非依存

## Task Commits

Each task was committed atomically:

1. **Task 1: E2E 正常系・ページエラー混在・キャンセルの3シナリオ** - `d7f019d` (test)
2. **Task 2: E2E サーキットブレーカー・OCR→サマリ一気通貫の2シナリオ + FakeProvider サマリ拡張** - `d84eee3` (test)

**Plan metadata:** (this commit) - `docs: complete 03-02 plan`

## Files Created/Modified
- `tests/test_ocr_engine.py` - `TestOCRRunEngineE2E`（5テストメソッド）+ `_drive_engine`（E2E producer スタブヘルパー）+ `FakeProvider` へ `complete_text_ex`/`supports_text_prompt` 拡張

## Decisions Made
- producer スタブ（`_drive_engine`）は cancel_flag を自前でチェックしない設計にした。`consume_one` が各アイテム処理開始時に `is_fatal()`/キャンセル判定を再確認する既存契約に委ね、producer 側での重複実装を避けた（既に enqueue 済みのアイテムは consumer 側で API 呼び出しがスキップされる）
- サーキットブレーカーテストは `OCRRetryableError(retry_after=0.01)` を使い、`clamp_retry_after`/`interruptible_sleep` の実待機を極小化してテスト時間を短縮した（1ページ = `MAX_RETRIES`(3) 回の呼び出し、3ページ分の連続失敗で `DEFAULT_CIRCUIT_BREAKER_THRESHOLD`(3) に到達する構造をそのまま利用）
- キャンセルテスト・サーキットブレーカーテストは `run_pages` を20ページに設定し、実際の呼び出し回数（それぞれ3回付近・9回付近）が全ページ数より十分少ないことを明確にアサートできるようにした

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 3（OCRRunEngine 抽出 + E2Eテスト）は本プランで全完了。`OCRRunEngine` は単一ファイル OCR の実運用構造を維持したまま抽出済みで、E2E モックテスト（6シナリオ・実 API 非依存）による回帰網も確立した
- Phase 4（バッチ OCR）は `BatchOCRDialog` がファイルごとに `OCRRunEngine` を新規生成して再利用できる（D-01/D-11 の直接の恩恵）。本プランで確立した `FakeProvider`/E2E テストパターンもそのまま応用できる
- `開発履歴.md` の更新は本プランのタスクスコープ外（テストコードのみの内部整備・UI/機能変更なし）とし、フェーズ完了時のドキュメント整合ステップに委ねる
- ブロッカーなし

---
*Phase: 03-ocr-e2e*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: tests/test_ocr_engine.py
- FOUND: .planning/phases/03-ocr-e2e/03-02-SUMMARY.md
- FOUND: d7f019d (git log)
- FOUND: d84eee3 (git log)
