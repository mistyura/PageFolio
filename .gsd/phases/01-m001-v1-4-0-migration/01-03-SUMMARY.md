---
id: S03
parent: M001
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# S03: Gemini Provider

**# Phase 06 Plan 01: GeminiProvider 中核実装 Summary**

## What Happened

# Phase 06 Plan 01: GeminiProvider 中核実装 Summary

**One-liner:** x-goog-api-key ヘッダー認証・thinkingBudget=0・dual env var 解決を備えた GeminiProvider を ClaudeProvider テンプレートで実装し、build_provider / _resolve_api_key / _cloud_providers に gemini 配線を追加。

---

## Objective

OCR-API-02（Gemini で OCR 実行）と OCR-QA-01（Provider モックテスト）の中核実装。
GeminiProvider クラスを ocr_providers.py に追加し、ocr.py に gemini 配線を加えた。
TDD パターンで RED（テスト先行）→ GREEN（実装）の順で実施。

---

## Tasks Completed

| Task | 説明 | Commit | ファイル |
|------|------|--------|---------|
| 1 | GeminiProvider モックテスト追加（RED） | 070ed31 | tests/test_ocr_providers.py, tests/test_ocr.py |
| 2 | GeminiProvider クラス実装（GREEN） | 16b1487 | pagefolio/ocr_providers.py |
| 3 | build_provider・_resolve_api_key・_cloud_providers に gemini 配線 | 86ae460 | pagefolio/ocr.py |

---

## Implementation Details

### GeminiProvider クラス（pagefolio/ocr_providers.py）

- `default_concurrency = 1` / `max_concurrency = 1`（D-07: Gemini Free Tier 10 RPM 対応）
- `RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]`（D-08: 旧 preview ID 不使用）
- `_build_payload`: `contents[0].parts` に `inline_data`（先頭）+ `text`（次）を配置
  - `generationConfig.thinkingConfig.thinkingBudget = 0`（Pitfall-C: generationConfig 直下）
- `ocr_image`: `x-goog-api-key` ヘッダー認証（URL `?key=` 不使用・D-05/T-06-01）
  - 429/5xx → `OCRRetryableError`、4xx → `RuntimeError`（ClaudeProvider と同型）
- `_parse_response`: `candidates` 空チェック → `promptFeedback.blockReason` 含む RuntimeError（Pitfall-D/T-06-03）
- `list_models`: api_key 未設定時は RECOMMENDED_MODELS・設定時は `generateContent` フィルタ

### gemini 配線（pagefolio/ocr.py）

- `_resolve_api_key("gemini", ...)`: `GEMINI_API_KEY` 優先 → `GOOGLE_API_KEY` フォールバック → セッションキー → `OCRAPIKeyError("GEMINI_API_KEY")`（D-06）
- `build_provider({"ocr_provider": "gemini"}, api_key=...)`: `GeminiProvider` を返す（OCR-API-02）
- `_start_ocr` の `_cloud_providers = {"claude", "gemini"}`: gemini を追加

---

## Test Results

| テストスイート | 結果 |
|--------------|------|
| `pytest tests/test_ocr_providers.py -k Gemini -q` | 22 passed |
| `pytest tests/test_ocr.py -k "Gemini or BuildProvider or ResolveApiKey" -q` | 23 passed |
| `pytest tests/test_ocr_providers.py tests/test_ocr.py -q`（全件・回帰含む） | 146 passed |
| `ruff check .` | クリーン |

---

## Deviations from Plan

なし — プランどおりに実行。

---

## Threat Model Coverage

| Threat ID | 対応状況 |
|-----------|---------|
| T-06-01 | `x-goog-api-key` ヘッダー認証実装・`?key=` URL クエリ不使用を grep/テストで検証 |
| T-06-02 | api_key は os.environ 読み取りのみ・settings への書き込みなしをテストで検証 |
| T-06-03 | candidates 空チェック → RuntimeError 実装・テストで検証 |
| T-06-04 | 例外メッセージに api_key・b64_png を含まない（HTTP エラー本文のみ） |

---

## Known Stubs

なし。

---

## Threat Flags

なし（計画された Gemini API 境界のみ。新規境界の追加なし）。

---

## Self-Check

確認済みファイル:
- `pagefolio/ocr_providers.py` に `class GeminiProvider(OCRProvider)` が存在する: OK
- `pagefolio/ocr.py` に `elif name == "gemini":` が存在する: OK
- `pagefolio/ocr.py` に `if provider_name == "gemini":` が存在する: OK
- `pagefolio/ocr.py` の `_cloud_providers = {"claude", "gemini"}` が存在する: OK
- `tests/test_ocr_providers.py` に `class TestGeminiProviderBuildPayload` が存在する: OK
- `tests/test_ocr.py` に `class TestResolveApiKeyGemini` と `class TestBuildProviderGemini` が存在する: OK

確認済みコミット:
- 070ed31: test(06-01) RED — 存在確認 OK
- 16b1487: feat(06-01) GeminiProvider 実装 — 存在確認 OK
- 86ae460: feat(06-01) gemini 配線 — 存在確認 OK

## Self-Check: PASSED

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

# Phase 06 Plan 03: Gemini UI 統合・ocr_scale 最適化 Summary

**One-liner:** ocr_scale 既定を 1.5 に変更・Gemini プロバイダを SettingsDialog と OCRDialog に統合し、プロバイダ判定系全メソッド（_is_cloud_provider/_needs_session_key/_provider_display_name/_apply_llm_settings/_confirm_cost）を dual env var 対応で gemini 対応化。

---

## Objective

OCR-PERF-05（ocr_scale 1.5 + ヒント）と OCR-API-02 の UI 統合部分・OCR-QA-01 補助文言を満たす。
Plan 01（GeminiProvider コア）を基盤として UI 層に gemini を接続。

---

## Tasks Completed

| Task | 説明 | Commit | ファイル |
|------|------|--------|---------|
| 1 | ocr_scale 既定 1.5 化・gemini_model 既定追加・Gemini/ヒント文言追加・テスト | c1306b8 | settings.py, lang.py, tests/test_settings_keyguard.py |
| 2 | llm_config.py に gemini プロバイダ欄と ocr_scale 常設ヒントを追加 | d5e066b | dialogs/llm_config.py, tests/test_provider_ui.py |
| 3 | ocr_dialog.py の gemini 分岐追加・v1.4.0 バージョン同期 | 6e54067 | ocr_dialog.py, constants.py, 開発履歴.md, README.md, tests/test_provider_ui.py |

---

## Implementation Details

### Task 1: settings.py・lang.py

- `settings.py` defaults: `"ocr_scale": 2.0` → `"ocr_scale": 1.5`（D-11）
- `settings.py` defaults: `"gemini_model": "gemini-2.5-flash"` を追加（D-08）
- `lang.py` ja/en 両辞書: `ocr_provider_name_gemini`・`ocr_api_key_missing_gemini`・`ocr_scale_tradeoff_hint` を `ocr_provider_name_claude` 近傍に追加
- `test_settings_keyguard.py`: `TestLoadSettingsDefaults` に `test_ocr_scale_default_is_1_5`・`test_gemini_model_default`・既存の `test_load_with_existing_file_preserves_defaults` への追加アサーションを追加

### Task 2: dialogs/llm_config.py

- import に `GeminiProvider` を追加
- `provider_combo.values`: `["off", "lmstudio", "claude", "gemini"]`
- `gemini_section_frame`: `claude_section_frame` と同パターン。`gemini_model_var`（既定 current_settings.get("gemini_model","gemini-2.5-flash")）・`gemini_model_combo`（values=GeminiProvider.RECOMMENDED_MODELS）・「モデル更新」ボタン（_refresh_gemini_models）
- `_refresh_gemini_models`: GEMINI_API_KEY / GOOGLE_API_KEY 読取・静的リストフォールバック（D-08）
- `_on_provider_change` gemini 分岐: gemini_section_frame pack・claude_section_frame pack_forget・effort_frame pack_forget・temperature_frame pack（D-09: temperature のみ）
- ocr_scale 常設ヒント Label: `C["TEXT_SUB"]`・`self._font(-2)`（テーマ色ハードコードなし）
- `_apply` に `gemini_model` 収集を追加（api_key 系収集ゼロを維持・T-06-10）

### Task 3: ocr_dialog.py + バージョン同期

- `_provider_display_name`: `name == "gemini" or isinstance(provider, GeminiProvider)` → `ocr_provider_name_gemini`
- `_is_cloud_provider`: `name in ("claude", "gemini")` + `isinstance(provider, (ClaudeProvider, GeminiProvider))`（Pitfall-F）
- `_estimate_cost`: Gemini モデル判定（"gemini" in model）→ gemini-2.5-flash $0.075/$0.30 / gemini-2.5-pro $1.25/$10 MTok の粗い見積もり（D-10）
- `_needs_session_key`: `name == "gemini"` のとき `not (GEMINI_API_KEY or GOOGLE_API_KEY)`（dual env var・D-06/Pitfall-G）
- `_confirm_cost`: gemini 時 host="generativelanguage.googleapis.com"・model=gemini_model（claude 時は従来通り）
- `_apply_llm_settings` provider 再生成: `elif name == "gemini":` 分岐を追加（_resolve_api_key("gemini") → build_provider）
- `_on_run` クラウドゲート: セッションキーエラー文言を gemini 用（ocr_api_key_missing_gemini）で出し分け・格納先を `_session_api_keys["gemini"]`（T-06-11）
- `_on_run` provider 再生成: `elif name == "gemini":` 分岐を追加
- `constants.py`: APP_VERSION = "v1.4.0"
- `開発履歴.md`: v1.4.0 正式リリースエントリ追加
- `README.md`: バッジ v1.4.0 に同期

---

## Test Results

| テストスイート | 結果 |
|--------------|------|
| `pytest tests/test_settings_keyguard.py -q` | 16 passed |
| `pytest tests/test_provider_ui.py -q` | 36 passed |
| `pytest -q`（全件・回帰含む） | 370 passed |
| `ruff check .` | クリーン |

---

## Deviations from Plan

なし — プランどおりに実行。

---

## Threat Model Coverage

| Threat ID | 対応状況 |
|-----------|---------|
| T-06-10 | `_apply` に api_key 系キーの収集なしを実装・grep 検証済み |
| T-06-11 | gemini セッションキーを `_session_api_keys["gemini"]` に格納・settings への書き込みなし |
| T-06-12 | gemini もコスト確認ダイアログ（generativelanguage.googleapis.com・ページ数・概算コスト）を毎回表示 |
| T-06-13 | _refresh_gemini_models は失敗時に静的 RECOMMENDED_MODELS へフォールバック（D-08） |

---

## Known Stubs

なし。

---

## Threat Flags

なし（計画された Gemini API 境界のみ。新規境界の追加なし）。

---

## Self-Check

**ファイル存在確認:**
- `pagefolio/settings.py` に `"ocr_scale": 1.5` が存在する: OK
- `pagefolio/settings.py` に `"gemini_model": "gemini-2.5-flash"` が存在する: OK
- `pagefolio/lang.py` に `ocr_provider_name_gemini` が ja/en 両方に存在する: OK
- `pagefolio/lang.py` に `ocr_scale_tradeoff_hint` が ja/en 両方に存在する: OK
- `pagefolio/dialogs/llm_config.py` に `"gemini"` が provider_combo values に存在する: OK
- `pagefolio/dialogs/llm_config.py` に `gemini_section_frame` が存在する: OK
- `pagefolio/ocr_dialog.py` に `_is_cloud_provider` の gemini 分岐が存在する: OK
- `pagefolio/ocr_dialog.py` に `_needs_session_key` の gemini dual env var 分岐が存在する: OK
- `pagefolio/ocr_dialog.py` に `generativelanguage.googleapis.com` が存在する: OK
- `pagefolio/constants.py` に `APP_VERSION = "v1.4.0"` が存在する: OK

**コミット存在確認:**
- c1306b8: feat(06-03) Task 1 — 存在確認 OK
- d5e066b: feat(06-03) Task 2 — 存在確認 OK
- 6e54067: feat(06-03) Task 3 — 存在確認 OK

## Self-Check: PASSED

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
