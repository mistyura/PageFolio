---
phase: 06-gemini-provider
verified: 2026-06-07T14:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "LM Studio で OCR を起動すると self.concurrency 本のワーカースレッドが起動し、実効並列度が concurrency 設定どおりになる（CR-01・OCR-PERF-02 の後方互換復元）"
    - "全ページ生産完了時およびキャンセル時に self.concurrency 本の終了シグナル None がキューへ送られ、全ワーカーがブロックせず終了する"
    - "複数ワーカーが共有する done 進捗カウンタが threading.Lock で保護され、競合更新で取りこぼし/二重計上が起きない"
    - "キャンセル時に _finish_cancelled が複数回呼ばれても OCR 結果テキストが二重挿入されない（CR-02 冪等ガード）"
    - "ocr_scale の例外フォールバック値が 1.5 に統一（WR-01）"
    - "executor.shutdown の cancel_futures が Python 3.8 でも TypeError を出さない（WR-02）"
    - "_SENSITIVE_KEYS が google_api_key / GOOGLE_API_KEY 系を含み平文保存を防ぐ（WR-03）"
  gaps_remaining: []
  regressions: []
---

# Phase 06: Gemini Provider 検証レポート（再検証）

**フェーズゴール:** Gemini で OCR が実行でき、低スペック PC でも全ページ OCR 時のメモリ使用量が許容範囲に収まる
**検証日時:** 2026-06-07T14:00:00Z
**ステータス:** passed
**再検証:** Yes — 06-04 ギャップクロージャ（ea81ed9 / a213482 / a6f15bc / 4a9fe28）適用後

---

## ゴール達成評価

### 観測可能な真実

| # | 真実 | 状態 | 証拠 |
|---|------|------|------|
| 1 | GEMINI_API_KEY または GOOGLE_API_KEY を設定したユーザーが Gemini で OCR を実行でき、テキストが返される | ✓ VERIFIED | GeminiProvider 実装・22 テスト全通過・dual env var 解決・build_provider("gemini") が GeminiProvider を返す |
| 2 | 100 ページの PDF で OCR 実行中に全ページの base64 画像が同時にメモリに乗らない（ページ単位でレンダリング→送信→破棄） | ✓ VERIFIED | run_with_bounded_buffer が正しく実装済み・OCRDialog._start_worker_thread が for _ in range(self.concurrency): で self.concurrency 本のワーカーを起動（CR-01 解消）・TestWorkerConcurrency / TestFinishIdempotent 全通過 |
| 3 | ocr_scale のデフォルトが 1.5 になり、UI にコスト/精度のトレードオフ説明が表示される | ✓ VERIFIED | settings.py L43: "ocr_scale": 1.5・lang.py に ocr_scale_tradeoff_hint（ja/en）・llm_config.py に Label 表示・DEFAULT_OCR_SCALE = 1.5（WR-01 解消） |
| 4 | 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定がモックテストで検証されている（tests/test_ocr.py 通過） | ✓ VERIFIED | 377 テスト全通過（旧 373 + 新規 4）。TestWorkerConcurrency（3 テスト）・TestFinishIdempotent（1 テスト）追加 |

**スコア:** 4/4 真実が検証済み

---

## 再検証: ギャップクロージャ証拠

### CR-01: 複数ワーカー化（主要 BLOCKER の解消）

**ocr_dialog.py `_start_worker_thread`（L956-967）:**

```python
def _start_worker_thread(self):
    self._worker_threads = []
    self._workers_remaining = self.concurrency
    for _ in range(self.concurrency):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._worker_threads.append(t)
```

`for _ in range(self.concurrency)` が存在し、concurrency 本のワーカーを起動する。前回の 1 本固定は解消済み。

**終了シグナル concurrency 本（`_render_next_page`）:**
- L890: キャンセル先頭検出時 `for _ in range(self.concurrency): self._render_queue.put_nowait(None)`
- L903: 全ページ完了時 `for _ in range(self.concurrency): self._render_queue.put(None)`
- L937: put ブロッキング中のキャンセル検出時も同様

計 3 箇所で `range(self.concurrency)` による終了シグナルが確認された。

**done カウンタ Lock 化:**
- `__init__` に `self._done_lock = threading.Lock()`・`self._done_count = 0`・`self._workers_remaining = 0` が追加（L83-85）
- `_worker` 内ローカル変数 `done += 1` が撤廃（grep 結果: 0件）
- `with self._done_lock: self._done_count += 1` による Lock 配下の更新（9箇所確認）

**最終ワーカー調整（単一終了処理）:**
- L1075-1096: `with self._done_lock: self._workers_remaining -= 1; is_last = ...` で最終ワーカーのみ `_finish_*` を after(0) 経由で呼ぶ

**ワーカーブロック防止バックストップ:**
- L984: `item = self._render_queue.get(timeout=1.0)` + L987: `if self._cancel_flag.is_set(): break` でキューが空でも最大 1 秒以内に終了（put_nowait で sentinel が落ちた場合の保護）

### CR-02: 冪等ガード

- `_finish_complete`（L1125）: `if self._done: return` ガード確認
- `_finish_cancelled`（L1142）: `if self._done: return` ガード確認
- `_finish_error`（L1154）: `if self._done: return` ガード確認

TestFinishIdempotent.test_finish_cancelled_renders_once が 2 回呼び出しで `_render_results_ordered` が 1 回のみであることを検証済み。

### WR-01: ocr_scale フォールバック 1.5 統一

| 箇所 | 修正前 | 修正後 |
|------|--------|--------|
| `pagefolio/ocr.py` L36 `DEFAULT_OCR_SCALE` | 2.0 | 1.5 |
| `pagefolio/dialogs/llm_config.py` L329 get フォールバック | 2.0 | 1.5 |
| `pagefolio/dialogs/llm_config.py` L718 例外パス | 2.0 | 1.5 |
| `pagefolio/ocr_dialog.py` L808 例外パス | 2.0 | 1.5 |

全 4 箇所で 2.0 が残存しないことを grep で確認済み。

### WR-02: Python 3.8 互換 shutdown

`pagefolio/ocr.py` に `import sys` が追加され（L9）、以下の分岐が 2 箇所に存在:

```python
if sys.version_info >= (3, 9):
    executor.shutdown(wait=False, cancel_futures=True)
else:
    executor.shutdown(wait=False)
```

`run_with_bounded_buffer`（L321）・`run_parallel`（L448）の両方で確認済み。

### WR-03: _SENSITIVE_KEYS 強化

`pagefolio/settings.py` の `_SENSITIVE_KEYS`（L17-26）に以下が追加:

```python
"google_api_key",    # WR-03: Gemini フォールバックキー名（小文字）
"GEMINI_API_KEY",    # WR-03: 大文字バリアント
"GOOGLE_API_KEY",    # WR-03: Gemini フォールバックキー名（大文字・D-06）
"ANTHROPIC_API_KEY", # WR-03: 大文字バリアント
```

Gemini の dual env var フォールバックキーが settings に平文保存されないことが構造的に保証される。

---

## 成功基準 vs. 要件対応

| 要件 ID | 記述 | 真実 # | 状態 |
|---------|------|--------|------|
| OCR-API-02 | Gemini（generateContent・inline_data・モデル一覧・GEMINI_API_KEY/GOOGLE_API_KEY）でページを OCR できる | 1 | ✓ VERIFIED |
| OCR-PERF-02 | ページ単位の逐次レンダリング→送信→破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止） | 2 | ✓ VERIFIED（CR-01 解消により PARTIAL から昇格） |
| OCR-PERF-05 | ocr_scale のデフォルトを 1.5 に見直し、速度/コスト vs 精度のトレードオフヒントを UI に表示する | 3 | ✓ VERIFIED |
| OCR-QA-01 | 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする | 4 | ✓ VERIFIED |

**注記:** REQUIREMENTS.md の要件トレーサビリティテーブル（L99-101）では OCR-PERF-02 と OCR-PERF-05 が「Pending」のままになっている。コードベース実装は完了済みであり、REQUIREMENTS.md のステータス更新が漏れているが、フェーズゴール達成への影響はない（ドキュメント整合性の軽微な課題）。

---

## 必須アーティファクト

| アーティファクト | 期待内容 | 状態 | 詳細 |
|----------------|---------|------|------|
| `pagefolio/ocr_providers.py` | GeminiProvider クラス | ✓ VERIFIED | GeminiProvider(OCRProvider) 実装。_build_payload/ocr_image/_parse_response/list_models 完備 |
| `pagefolio/ocr.py` | build_provider の gemini 分岐・run_with_bounded_buffer・sys.version_info 分岐・DEFAULT_OCR_SCALE=1.5 | ✓ VERIFIED | L88 gemini 分岐・L139 run_with_bounded_buffer・L36 DEFAULT_OCR_SCALE=1.5・L321/L448 Python 3.8 互換分岐 |
| `pagefolio/ocr_dialog.py` | _render_queue・_start_worker_thread concurrency 本・done Lock・冪等ガード | ✓ VERIFIED | for _ in range(self.concurrency) 4箇所・_done_lock/done_count/workers_remaining・if self._done: return 3メソッド |
| `pagefolio/settings.py` | ocr_scale: 1.5・gemini_model 既定・google_api_key 系 _SENSITIVE_KEYS | ✓ VERIFIED | L43: "ocr_scale": 1.5・L54: "gemini_model": "gemini-2.5-flash"・L20-25: WR-03 キー群 |
| `pagefolio/lang.py` | ocr_scale_tradeoff_hint（ja/en） | ✓ VERIFIED | L317（ja）・L675（en）に存在 |
| `pagefolio/dialogs/llm_config.py` | gemini プロバイダ選択肢・gemini モデル欄・ocr_scale フォールバック 1.5 | ✓ VERIFIED | provider_combo に "gemini"・gemini_section_frame・get("ocr_scale", 1.5)・例外パス 1.5 |
| `pagefolio/constants.py` | APP_VERSION v1.4.0 | ✓ VERIFIED | L12: APP_VERSION = "v1.4.0" |
| `tests/test_ocr_providers.py` | TestGeminiProvider 系テスト | ✓ VERIFIED | 22 テスト全 PASS |
| `tests/test_ocr.py` | TestResolveApiKeyGemini・TestBuildProviderGemini・TestProducerConsumerMemory・TestWorkerConcurrency・TestFinishIdempotent | ✓ VERIFIED | 計 15 テスト全 PASS（新規 4 テスト含む） |
| `tests/test_provider_ui.py` | gemini プロバイダ判定テスト | ✓ VERIFIED | 全 PASS |
| `tests/test_settings_keyguard.py` | ocr_scale==1.5・gemini_model 既定テスト・google_api_key 系キーガード | ✓ VERIFIED | 377 PASS |

---

## キーリンク検証

| From | To | Via | 状態 | 詳細 |
|------|-----|-----|------|------|
| ocr.py build_provider | ocr_providers.GeminiProvider | `elif name == "gemini":` 分岐 | ✓ WIRED | 確認済み |
| ocr.py _resolve_api_key | os.environ GEMINI_API_KEY / GOOGLE_API_KEY | dual env var フォールバック | ✓ WIRED | 確認済み |
| ocr_dialog.py _start_worker_thread | _worker（concurrency 本） | for _ in range(self.concurrency) | ✓ WIRED | 前回 PARTIAL → 今回 VERIFIED（CR-01 解消） |
| ocr_dialog.py _render_next_page（全ページ完了/キャンセル） | _worker 群（終了） | concurrency 本の None 終了シグナル（3箇所） | ✓ WIRED | 前回 PARTIAL → 今回 VERIFIED |
| ocr_dialog.py _done_lock | _done_count / _workers_remaining | threading.Lock() | ✓ WIRED | 9箇所で with self._done_lock: 確認 |
| ocr_dialog.py _finish_cancelled / _finish_complete / _finish_error | 冪等保護 | if self._done: return 冒頭ガード | ✓ WIRED | 3メソッド全確認（CR-02 解消） |
| llm_config.py provider_combo | ocr_provider="gemini" | values=["off","lmstudio","claude","gemini"] | ✓ WIRED | 確認済み |
| settings.py _SENSITIVE_KEYS | GOOGLE_API_KEY / GEMINI_API_KEY 系 | _save_settings のキーガード | ✓ WIRED | WR-03 解消済み |
| ocr.py executor.shutdown | Python 3.8 互換分岐 | sys.version_info >= (3, 9) | ✓ WIRED | run_with_bounded_buffer / run_parallel 両方確認（WR-02 解消） |

---

## データフロートレース（Level 4）

| アーティファクト | データ変数 | ソース | 実データを返すか | 状態 |
|----------------|-----------|--------|----------------|------|
| GeminiProvider.ocr_image | text | Gemini generateContent API (urllib) | Yes（モックテスト検証済み） | ✓ FLOWING |
| run_with_bounded_buffer | results | render_fn → buf → provider.ocr_image | Yes・del b64 で破棄も確認 | ✓ FLOWING |
| OCRDialog._worker（複数） | self.results[page_idx] | _render_queue.get(timeout=1.0) → provider.ocr_image | Yes・concurrency 本のワーカーで並列処理（CR-01 解消） | ✓ FLOWING |

---

## 振る舞いスポットチェック

| 確認事項 | コマンド | 結果 | 状態 |
|---------|---------|------|------|
| フルスイート | pytest tests/ -q | 377 passed in 1.92s | ✓ PASS |
| 並列度テスト（CR-01） | pytest tests/test_ocr.py::TestWorkerConcurrency -q | 3 passed | ✓ PASS |
| 冪等性テスト（CR-02） | pytest tests/test_ocr.py::TestFinishIdempotent -q | 1 passed | ✓ PASS |
| GeminiProvider テスト全通過 | pytest tests/test_ocr_providers.py -k Gemini | 22 passed | ✓ PASS |
| メモリ非蓄積テスト | pytest tests/test_ocr.py::TestProducerConsumerMemory | 3 passed | ✓ PASS |
| コミット存在確認 | git log --oneline ea81ed9 a213482 a6f15bc 4a9fe28 | 4件確認済み | ✓ PASS |

---

## 要件カバレッジ

| 要件 ID | 記述（REQUIREMENTS.md より） | プラン | 状態 | 証拠 |
|---------|---------------------------|-------|------|------|
| OCR-API-02 | Gemini で OCR 実行 | 06-01, 06-03 | ✓ SATISFIED | GeminiProvider 実装・22 テスト通過 |
| OCR-PERF-02 | ページ単位 render→送信→破棄 | 06-02, 06-04 | ✓ SATISFIED | run_with_bounded_buffer 正常実装・CR-01 解消（concurrency 本ワーカー起動）・TestWorkerConcurrency 通過 |
| OCR-PERF-05 | ocr_scale 既定 1.5・UI ヒント | 06-03, 06-04 | ✓ SATISFIED | settings.py 1.5・lang.py ヒント・llm_config.py Label・全フォールバック 1.5 統一（WR-01） |
| OCR-QA-01 | Provider モックテスト | 06-01, 06-02, 06-03, 06-04 | ✓ SATISFIED | 377 テスト全通過（新規 TestWorkerConcurrency/TestFinishIdempotent 含む） |

---

## アンチパターン検出

| ファイル | 行 | パターン | 重大度 | 影響 |
|---------|----|---------|--------|------|
| `pagefolio/ocr_dialog.py` | L104 | `except Exception:` (`as e` なし) | INFO | `_font_size` のフォールバック戻り値のみで `e` 変数が不要なケース。CLAUDE.md「裸の except:」ルールは例外型を指定しない `except:` を指すため技術的に違反ではない。影響なし |
| `pagefolio/ocr_dialog.py` | L895 | `_finish_cancelled()` をメインスレッドから直接呼び出し（after(0) を介さず） | WARNING | キャンセル先頭検出パスで直接呼出し。ワーカーの最終処理（L1093）でも after(0, self._finish_cancelled) が呼ばれる可能性があるが、`if self._done: return` 冪等ガードにより二重実行は防止される（CR-02 解消済み）。デッドロックリスクなし |
| `pagefolio/ocr_dialog.py` | L890-894 | put_nowait(None) で sentinel が Full 時に落ちる可能性 | INFO | 06-REVIEW.md の指摘と同じ。L984 の `get(timeout=1.0)` + `_cancel_flag.is_set()` バックストップにより最大 1 秒以内にワーカーが終了するため、デッドロックではなく最大 1 秒の遅延キャンセル。ゴール達成を妨げない |

前回検証で BLOCKER として記録された CR-01（シングルスレッド退行）・CR-02（二重挿入）・WR-01/02/03 はすべて解消済み。

---

## 人間による検証が必要な項目

なし（今フェーズでは自動検証で全項目判定可能）。

---

## ギャップサマリー

Phase 06 の全 4 成功基準が VERIFIED となった。

06-04 ギャップクロージャにより:
- **SC-2（OCR-PERF-02）**: PARTIAL から VERIFIED へ昇格。`_start_worker_thread` が `self.concurrency` 本のワーカーを起動し、LM Studio の実効並列度が設定値どおりに復元された。
- **CR-02**: `_finish_cancelled` / `_finish_complete` / `_finish_error` の冪等ガードにより OCR 結果の二重挿入が解消された。
- **WR-01/02/03**: ocr_scale フォールバック値統一・Python 3.8 互換・SENSITIVE_KEYS 強化が完了した。

残存する軽微なドキュメント整合性の課題（REQUIREMENTS.md トレーサビリティテーブルの OCR-PERF-02/05 ステータスが "Pending" のまま）は次フェーズ（Phase 7）のドキュメント更新で対処可能。フェーズゴール達成への影響はない。

テストスイート: **377 passed**（旧 373 + 新規 4）。

---

_検証日時: 2026-06-07T14:00:00Z_
_検証者: Claude (gsd-verifier)_
_再検証: 06-04 ギャップクロージャ（ea81ed9 / a213482 / a6f15bc / 4a9fe28）適用後_
