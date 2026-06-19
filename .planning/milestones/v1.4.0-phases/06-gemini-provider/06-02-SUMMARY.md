---
phase: 06-gemini-provider
plan: "02"
subsystem: ocr-producer-consumer
tags: [ocr, producer-consumer, memory-optimization, bounded-buffer, thread-safety]
dependency_graph:
  requires:
    - Plan 06-01 (GeminiProvider クラス・build_provider・OCRProvider 抽象)
  provides:
    - run_with_bounded_buffer ヘルパー（pagefolio/ocr.py・Tk 非依存・D-13）
    - OCRDialog の producer-consumer 化（pagefolio/ocr_dialog.py）
    - メモリ非蓄積リグレッションテスト（tests/test_ocr.py）
  affects:
    - Plan 06-03（ocr_dialog.py の gemini UI 統合 — 同波、相互依存なし）
tech_stack:
  added:
    - queue（Python 標準ライブラリ・新規 pip 依存なし）
  patterns:
    - queue.Queue(maxsize=workers+1) による bounded buffer producer-consumer
    - メインスレッド（fitz 専属）→ ワーカースレッド（API 専属）のスレッド境界
    - キャンセル検出付き put ループ（timeout=0.1・Pitfall-B 対策）
    - None 終了シグナルによる consumer 終了（Pitfall-E 対策）
    - del b64 送信後即時破棄（D-04・成功基準2）
    - after(0) 経由でメインスレッドへ進捗通知（スレッドセーフ・Pitfall 3）
key_files:
  created: []
  modified:
    - pagefolio/ocr.py
    - pagefolio/ocr_dialog.py
    - tests/test_ocr.py
decisions:
  - "[Phase 06-02]: バッファ上限は concurrency+1（余裕係数 1: ワーカー飢えを防ぐ最小マージン・D-02）"
  - "[Phase 06-02]: run_with_bounded_buffer は Tk 非依存の ocr.py モジュール関数として切り出し（D-13 テスト可能化）"
  - "[Phase 06-02]: _worker は fitz/get_pixmap/page_to_png_b64/self.doc[ を一切使用しない（D-04 必達）"
  - "[Phase 06-02]: 全ページ base64 一括辞書蓄積（self._images = {}）を撤廃し render→送信→破棄パイプラインへ"
  - "[Phase 06-02]: 統合プログレス（done+skipped/total）を主軸とし、レンダリング 2 段表示を廃止（D-03）"
  - "[Phase 06-02]: consumer を先行起動してから producer を開始する（重なり実行で latency 短縮）"
metrics:
  duration: "約 20 分"
  completed: "2026-06-07"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 06 Plan 02: producer-consumer 逐次レンダリング・メモリ最適化 Summary

**One-liner:** queue.Queue(maxsize=concurrency+1) による bounded buffer producer-consumer で全ページ base64 一括保持を廃止し、ページ単位 render→送信→破棄パイプラインと Tk 非依存ヘルパーでメモリ上限を機械保証する。

---

## Objective

OCR-PERF-02（全ページ base64 の一括メモリ保持を廃止・ページ単位の render→送信→破棄）と OCR-QA-01（メモリ非蓄積リグレッションテスト）を満たす。

スレッド境界（Phase 4 D-03/D-04: ワーカー内 fitz アクセスゼロ）の必達要件を維持しつつ、Tk 非依存の `run_with_bounded_buffer` ヘルパーを切り出してテスト可能性を確保（D-13）。

---

## Tasks Completed

| Task | 説明 | Commit | ファイル |
|------|------|--------|---------|
| 1 | run_with_bounded_buffer ヘルパーを ocr.py に新設（Tk 非依存・producer-consumer） | e22b4b6 | pagefolio/ocr.py |
| 2 | TestProducerConsumerMemory でメモリ非蓄積リグレッションテストを追加（D-13） | e85f1e7 | tests/test_ocr.py |
| 3 | OCRDialog を producer-consumer 化し統合プログレス化（メモリ最適化・D-04） | 930d7de | pagefolio/ocr_dialog.py |

---

## Implementation Details

### Task 1: run_with_bounded_buffer（pagefolio/ocr.py）

- `import queue`（標準ライブラリ）を追加
- `run_with_bounded_buffer(provider, render_fn, page_indices, concurrency, prompt, on_done, is_cancelled)` を新設
- `maxsize = max(1, workers + 1)`（余裕係数 1・D-02）の `queue.Queue` を作成
- 生産者（`_producer` 内部スレッド）: `render_fn(page_idx)` → キャンセル検出付きブロッキング `put`（timeout=0.1・Pitfall-B）→ workers 本分の `None` 終了シグナル（Pitfall-E）
- 消費者（`_consumer`・ThreadPoolExecutor で workers 本並列）: `get(timeout=1.0)` → `None` で break → `provider.ocr_image` に OCRRetryableError バックオフ付きリトライ → `finally: del b64`（破棄・成功基準2）
- 戻り値は `(results, errors, fatal_msg, fatal_kind)`（run_parallel と同形）
- `render_fn` はメインスレッド前提だがコールバックのみに依存し Tk を import しない（D-13）

### Task 2: TestProducerConsumerMemory（tests/test_ocr.py）

- `test_in_flight_count_never_exceeds_maxsize`: `threading.Lock` で in_flight カウントを計測、同時保持数が `concurrency+1` 以内に収まることを 20 ページで検証
- `test_all_results_collected_no_missing`: 20 ページ全件が results に揃うことを検証
- `test_cancel_terminates_without_deadlock`: キャンセル後に残ページを処理せず有限時間で終了することを検証

### Task 3: OCRDialog producer-consumer 化（pagefolio/ocr_dialog.py）

- `import queue` を追加
- `self._images = {}` 一括辞書蓄積を撤廃 → `self._render_queue = None` に変更
- `_on_run` でキュー初期化 → `_start_worker_thread`（consumer 先行） → `_render_next_page`（producer 開始）の順に起動
- `_render_next_page`（生産者・メインスレッド）:
  - fitz アクセスはここのみ（D-04 必達）
  - 埋め込みテキストスキップはキューに積まず統合プログレスを直接更新
  - キャンセル検出付き put（timeout=0.1・Pitfall-B）
  - 全ページ完了 / キャンセル時に `None` 終了シグナル（Pitfall-E）
- `_worker`（消費者・ワーカー）:
  - `fitz`/`get_pixmap`/`page_to_png_b64`/`self.doc[` を一切使用しない（D-04 必達）
  - `get(timeout=1.0)` ループ → `None` で break → `provider.ocr_image` にリトライ
  - `finally: del b64`（送信後即時破棄・成功基準2・T-06-06）
  - 統合プログレス（done+skipped/total）を `after(0)` 経由で更新（D-03）
- `_clear_text` で `_render_queue = None` にリセット
- `run_parallel` の未使用 import を削除

---

## Test Results

| テストスイート | 結果 |
|--------------|------|
| `pytest tests/test_ocr.py::TestProducerConsumerMemory -q` | 3 passed |
| `pytest tests/test_ocr.py -q` | 71 passed |
| `pytest -q`（全件・回帰含む） | 373 passed |
| `ruff check .` | クリーン |
| `ast.parse(ocr_dialog.py)` | parse ok |

---

## Deviations from Plan

### 微細な実装差異（プラン精神との整合あり）

**1. [Rule 2 - 安全性強化] _render_next_page のスキップページ統合プログレス**

- **計画:** スキップページはキューに積まず次へ進む
- **実装:** スキップ時も `after(0)` 経由で統合プログレス（done+skipped/total）を更新する処理を追加（D-03 の「スキップも処理済みに含める」要件の実装）
- **理由:** 計画の記載が省略されていたが、D-03 の必達要件を満たすために追加

**2. [Rule 1 - 設計改善] consumer 先行起動**

- **計画:** `_render_next_page` 起動後にワーカーを起動すると記述
- **実装:** `_start_worker_thread`（consumer 先行）→ `_render_next_page`（producer）の順に変更
- **理由:** consumer を先行起動しないと producer が put に成功した後 consumer がいないデッドロックが発生するリスクがあるため

---

## Threat Model Coverage

| Threat ID | 対応状況 |
|-----------|---------|
| T-06-06 | `queue.Queue(maxsize=concurrency+1)` で同時保持を制限・`del b64` で送信後破棄・TestProducerConsumerMemory で機械検証 |
| T-06-07 | `_worker` 内に fitz/get_pixmap/page_to_png_b64/self.doc[ が存在しない（D-04 必達）・コードレビューで確認 |
| T-06-08 | put は timeout=0.1 ループで Full 時に cancel 確認（Pitfall-B）・get は timeout=1.0 で Empty 時に cancel 確認・None 終了シグナルで worker 終了（Pitfall-E）・TestProducerConsumerMemory でデッドロック非発生を検証 |
| T-06-09 | progress/error 文言に b64 画像データ・api_key を含めない（既存 T-04-09/T-05 ガード踏襲） |
| T-06-SC | 外部 pip パッケージ追加ゼロ（標準ライブラリ queue のみ追加） |

---

## Known Stubs

なし。

---

## Threat Flags

なし（計画された Gemini/Claude API 境界のみ。新規境界の追加なし）。

---

## Self-Check

**ファイル存在確認:**
- `pagefolio/ocr.py` に `def run_with_bounded_buffer` が存在する: OK
- `pagefolio/ocr.py` に `import queue` が存在する: OK
- `pagefolio/ocr.py` に `queue.Queue(maxsize=` が存在する: OK
- `pagefolio/ocr.py` に `del b64` が存在する: OK
- `pagefolio/ocr_dialog.py` に `self._render_queue` が存在する: OK
- `pagefolio/ocr_dialog.py` に `import queue` が存在する: OK
- `pagefolio/ocr_dialog.py` に `self._images = {}` の一括蓄積が存在しない: OK
- `pagefolio/ocr_dialog.py` の `_worker` に `del b64` が存在する: OK
- `tests/test_ocr.py` に `class TestProducerConsumerMemory` が存在する: OK

**コミット存在確認:**
- e22b4b6: feat(06-02) run_with_bounded_buffer 新設 — 存在確認 OK
- e85f1e7: test(06-02) TestProducerConsumerMemory 追加 — 存在確認 OK
- 930d7de: feat(06-02) OCRDialog producer-consumer 化 — 存在確認 OK

## Self-Check: PASSED
