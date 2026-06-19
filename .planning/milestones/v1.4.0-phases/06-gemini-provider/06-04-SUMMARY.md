---
phase: 06-gemini-provider
plan: 04
subsystem: OCR
tags: [concurrency, thread-safety, idempotency, python38-compat, security]
dependency_graph:
  requires: [06-02]
  provides: [OCR-PERF-02-restored, CR-01-fixed, CR-02-fixed, WR-01-fixed, WR-02-fixed, WR-03-fixed]
  affects: [pagefolio/ocr_dialog.py, pagefolio/ocr.py, pagefolio/settings.py, pagefolio/dialogs/llm_config.py, tests/test_ocr.py]
tech_stack:
  added: []
  patterns:
    - threading.Lock による共有カウンタ保護（CR-01）
    - 最終ワーカー調整（_workers_remaining カウンタ）による単一終了処理
    - 冪等ガード（if self._done: return）パターン（CR-02）
    - sys.version_info 分岐による Python 3.8/3.9+ 互換コード（WR-02）
key_files:
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/ocr.py
    - pagefolio/settings.py
    - pagefolio/dialogs/llm_config.py
    - tests/test_ocr.py
decisions:
  - "[Phase 06-04]: _workers_remaining カウンタ（Lock 配下）で最終ワーカーのみ終了処理を呼ぶ（単一終了処理の保証・CR-01）"
  - "[Phase 06-04]: _fatal_msg/_fatal_kind を共有属性に昇格し Lock 保護（複数ワーカーの致命的エラー報告・CR-01）"
  - "[Phase 06-04]: import time as _time をワーカーループ外に移動（IN-02 修正）"
  - "[Phase 06-04]: DEFAULT_OCR_SCALE = 1.5 に統一し D-11 既定と整合（WR-01）"
  - "[Phase 06-04]: _SENSITIVE_KEYS に google_api_key / GOOGLE_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY 大文字バリアントを追加（WR-03）"
metrics:
  duration_minutes: 6
  completed_date: "2026-06-07"
  tasks_completed: 3
  files_modified: 5
requirements:
  - OCR-PERF-02
  - OCR-PERF-05
  - OCR-QA-01
---

# Phase 06 Plan 04: ギャップクロージャ（CR-01 並列度復元・CR-02 冪等ガード・WR-01/02/03）サマリー

**一言:** LM Studio 並列度を `self.concurrency` 本に復元（`threading.Lock` 保護 + 最終ワーカー調整）し、キャンセル時の結果二重挿入を冪等ガードで解消。Python 3.8 互換化と GOOGLE_API_KEY 平文保存防止も同時達成。

---

## 完了タスク

| # | タスク名 | コミット | 変更ファイル |
|---|---------|---------|------------|
| 1 | CR-01 複数ワーカー化・done Lock・終了シグナル concurrency 本・CR-02 冪等ガード | ea81ed9 | pagefolio/ocr_dialog.py |
| 2 | 並列度回帰テスト（TestWorkerConcurrency）と冪等性テスト（TestFinishIdempotent）を追加 | a213482 | tests/test_ocr.py |
| 3 | 技術的負債 WR-01/WR-02/WR-03 を解消 | a6f15bc | pagefolio/ocr.py, pagefolio/settings.py, pagefolio/dialogs/llm_config.py, pagefolio/ocr_dialog.py |

---

## 実施内容詳細

### Task 1: CR-01 複数ワーカー化（pagefolio/ocr_dialog.py）

**CR-01 複数ワーカー起動:**
- `_start_worker_thread` を `for _ in range(self.concurrency):` ループに変更し `self.concurrency` 本の `threading.Thread` を起動
- `__init__` の `self._worker_thread = None` を `self._worker_threads = []` に置換
- 新属性: `_done_lock`（threading.Lock）・`_done_count`（int）・`_workers_remaining`（int）・`_fatal_msg`/`_fatal_kind`

**CR-01 終了シグナル concurrency 本:**
- `_render_next_page` の全ページ完了分岐: `for _ in range(self.concurrency): self._render_queue.put(None)`
- キャンセル分岐（2 箇所）: 同様に `for _ in range(self.concurrency):` でワーカー数分 put

**CR-01 done カウンタ Lock 化:**
- ローカル変数 `done` を撤廃し、完了/失敗ごとに `with self._done_lock: self._done_count += 1`
- 進捗読み取りも `with self._done_lock: total_done = self._done_count + skipped_count`

**CR-01 全ワーカー終了後の単一終了処理:**
- `_worker` の break 後: `with self._done_lock: self._workers_remaining -= 1; is_last = ...`
- `is_last` が False のワーカーは即 return（終了処理をスキップ）
- `is_last` が True の最終ワーカーのみ `_finish_error`/`_finish_cancelled`/`_render_results_ordered`+`_finish_complete` を after(0) 経由で呼ぶ

**CR-02 冪等ガード:**
- `_finish_cancelled` / `_finish_complete` / `_finish_error` の各冒頭に `if self._done: return` を追加

**IN-02 修正（副次的改善）:**
- `import time as _time` をリトライループ内から `_worker` の冒頭に移動

### Task 2: 回帰テスト追加（tests/test_ocr.py）

`TestWorkerConcurrency`:
- `test_starts_concurrency_threads`: threading.Thread をスタブ化して起動数 == concurrency=4 を検証
- `test_single_thread_for_gemini`: concurrency=1 で 1 本のみ（後方互換）
- `test_termination_signals_match_concurrency`: 0 ページリストで即座に完了分岐到達、キューから取り出した None 数 == concurrency=3 を検証

`TestFinishIdempotent`:
- `test_finish_cancelled_renders_once`: `_finish_cancelled` を 2 回呼んで `_render_results_ordered` が 1 回のみ実行を検証

### Task 3: 技術的負債解消（WR-01/02/03）

**WR-01（ocr_scale 1.5 統一）:**
- `pagefolio/ocr.py`: `DEFAULT_OCR_SCALE = 2.0` → `1.5`
- `pagefolio/dialogs/llm_config.py`: `get("ocr_scale", 2.0)` → `1.5`、例外パス `2.0` → `1.5`
- `pagefolio/ocr_dialog.py`: 例外フォールバック `self._ocr_scale = 2.0` → `1.5`

**WR-02（Python 3.8 互換 shutdown）:**
- `pagefolio/ocr.py`: `import sys` 追加
- `run_with_bounded_buffer` と `run_parallel` の `executor.shutdown`: `sys.version_info >= (3, 9)` 分岐で `cancel_futures=True` をガード

**WR-03（_SENSITIVE_KEYS 強化）:**
- `pagefolio/settings.py`: `google_api_key`・`GOOGLE_API_KEY`・`GEMINI_API_KEY`・`ANTHROPIC_API_KEY` を追加
- Gemini フォールバックキー名が `pagefolio_settings.json` に平文保存されるのを防止

---

## 検証結果

| 検証項目 | 結果 |
|---------|------|
| `pytest tests/ -q` | 377 passed（旧 373 + 新規 4）|
| `ruff check . && ruff format .` | クリーン |
| `for _ in range(self.concurrency)` 出現数（grep） | 4 箇所（_start_worker_thread × 1 + _render_next_page × 3） |
| `with self._done_lock:` 出現数 | 9 箇所 |
| `if self._done: return` ガード | 3 メソッドすべて（_finish_complete / _finish_cancelled / _finish_error） |
| `done += 1` の残存 | 0 |
| 裸の `except:` | 0 |
| `DEFAULT_OCR_SCALE = 1.5` | 確認済み |
| `sys.version_info >= (3, 9)` 分岐 | 2 箇所（run_with_bounded_buffer / run_parallel） |
| `GOOGLE_API_KEY` in `_SENSITIVE_KEYS` | 確認済み |

---

## 成功基準達成状況

| 成功基準 | 状態 |
|---------|------|
| LM Studio で OCR を起動すると self.concurrency 本のワーカーが起動（OCR-PERF-02 後方互換復元） | ACHIEVED |
| 全ページ完了時・キャンセル時に self.concurrency 本の終了シグナルが送られる | ACHIEVED |
| 共有 done カウンタが Lock 保護される | ACHIEVED |
| 全ワーカー終了後に結果描画と完了処理が一度だけ実行される | ACHIEVED |
| キャンセル時に _finish_cancelled が複数回呼ばれても OCR 結果が二重挿入されない（CR-02） | ACHIEVED |
| Gemini（concurrency=1）の挙動が変わらない（後方互換） | ACHIEVED |
| ocr_scale 例外フォールバックが 1.5 に統一（WR-01） | ACHIEVED |
| executor.shutdown が Python 3.8 で TypeError を出さない（WR-02） | ACHIEVED |
| _SENSITIVE_KEYS が GOOGLE_API_KEY 系を含む（WR-03） | ACHIEVED |
| フルスイート pytest グリーン | ACHIEVED（377 passed） |

---

## プラン計画との差分（偏差）

**自動適用した改善（CLAUDE.md ルール 2）:**

1. `[Rule 2 - IN-02 修正] import time as _time をループ外に移動`
   - 発見場所: Task 1 _worker 改修時
   - 内容: `import time as _time` がリトライループ内に置かれていた（06-REVIEW.md IN-02）。同タスクで修正
   - 変更ファイル: pagefolio/ocr_dialog.py

計画外の修正なし。その他 WR-01/02/03 はすべて計画（Task 3）の範囲内。

---

## 既知のスタブ

なし。

---

## Threat Flags

なし（新規ネットワークエンドポイント・認証パス・ファイルアクセスパターンの追加なし）。

---

## Self-Check: PASSED

- `pagefolio/ocr_dialog.py` 存在確認: FOUND
- `tests/test_ocr.py` 存在確認: FOUND
- コミット ea81ed9 存在確認: FOUND
- コミット a213482 存在確認: FOUND
- コミット a6f15bc 存在確認: FOUND
- 全テスト 377 passed: CONFIRMED
