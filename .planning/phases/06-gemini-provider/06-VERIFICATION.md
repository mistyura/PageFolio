---
phase: 06-gemini-provider
verified: 2026-06-07T12:00:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "100 ページの PDF で OCR 実行中に全ページの base64 画像が同時にメモリに乗らない（ページ単位でレンダリング→送信→破棄）"
    status: partial
    reason: |
      OCR-PERF-02 のメモリ非蓄積自体は run_with_bounded_buffer ヘルパー（ocr.py）が
      正しく実装しており、TestProducerConsumerMemory テストも通過している。
      しかし OCRDialog._start_worker_thread がシングルスレッドしか起動しないため（CR-01）、
      LM Studio ユーザーの実効並列度が常に 1 に退行する。
      計画の要件「LM Studio の並列度（最大 8）は ThreadPoolExecutor で維持・後方互換」
      （06-02-PLAN.md: "LM Studio / Claude / Gemini の既存挙動・キャンセル・APIキーガードを壊さない"）
      が達成されていない。
      さらにキャンセル時 _finish_cancelled が 2 回呼ばれる CR-02 バグがある（_done ガードなし）。
    artifacts:
      - path: "pagefolio/ocr_dialog.py"
        issue: |
          _start_worker_thread (L946-949) は self.concurrency に関わらず
          threading.Thread を 1 本しか起動しない。
          concurrency=4 の LM Studio ユーザーは実効 1 スレッドで動作する（CR-01）。
      - path: "pagefolio/ocr_dialog.py"
        issue: |
          _finish_cancelled (L1104) に _done チェックがないため、
          _render_next_page 側で直接呼ばれた後さらに
          _worker 終了時の after(0, self._finish_cancelled) から 2 回目が呼ばれる（CR-02）。
    missing:
      - "_start_worker_thread を self.concurrency 本のスレッド起動に変更し、終了シグナルも concurrency 本送る"
      - "_finish_cancelled の冒頭に 'if self._done: return' ガードを追加する"
      - "done カウンタのスレッドセーフ化（threading.Lock）"
deferred: []
---

# Phase 06: Gemini Provider 検証レポート

**フェーズゴール:** Gemini で OCR が実行でき、低スペック PC でも全ページ OCR 時のメモリ使用量が許容範囲に収まる
**検証日時:** 2026-06-07T12:00:00Z
**ステータス:** gaps_found
**再検証:** No（初回検証）

---

## ゴール達成評価

### 観測可能な真実

| # | 真実 | 状態 | 証拠 |
|---|------|------|------|
| 1 | GEMINI_API_KEY または GOOGLE_API_KEY を設定したユーザーが Gemini で OCR を実行でき、テキストが返される | ✓ VERIFIED | GeminiProvider 実装あり・22 テスト全通過・dual env var 解決・build_provider("gemini") が GeminiProvider を返す |
| 2 | 100 ページの PDF で OCR 実行中に全ページの base64 画像が同時にメモリに乗らない | ✗ PARTIAL | run_with_bounded_buffer は正しく実装・TestProducerConsumerMemory 通過。しかし OCRDialog._start_worker_thread が 1 スレッドのみ起動（CR-01 未修正）→ LM Studio 後方互換が破損 |
| 3 | ocr_scale のデフォルトが 1.5 になり、UI にコスト/精度のトレードオフ説明が表示される | ✓ VERIFIED | settings.py L43: `"ocr_scale": 1.5`・lang.py に ocr_scale_tradeoff_hint (ja/en)・llm_config.py L347 に Label 表示 |
| 4 | 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定がモックテストで検証されている（tests/test_ocr.py 通過） | ✓ VERIFIED | 373 テスト全通過。GeminiProvider 系 22 テスト・TestResolveApiKeyGemini 5 テスト・TestBuildProviderGemini 5 テスト・TestProducerConsumerMemory 3 テスト |

**スコア:** 3/4 真実が検証済み（SC-2 は PARTIAL = BLOCKER）

---

## 成功基準 vs. 要件対応

| 要件 ID | 記述 | 真実 # | 状態 |
|---------|------|--------|------|
| OCR-API-02 | Gemini（generateContent・inline_data・モデル一覧・GEMINI_API_KEY/GOOGLE_API_KEY）でページを OCR できる | 1 | VERIFIED |
| OCR-PERF-02 | ページ単位の逐次レンダリング→送信→破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止） | 2 | PARTIAL (BLOCKER) |
| OCR-PERF-05 | ocr_scale のデフォルトを 1.5 に見直し、速度/コスト vs 精度のトレードオフヒントを UI に表示する | 3 | VERIFIED |
| OCR-QA-01 | 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする | 4 | VERIFIED |

---

## 必須アーティファクト

| アーティファクト | 期待内容 | 状態 | 詳細 |
|----------------|---------|------|------|
| `pagefolio/ocr_providers.py` | GeminiProvider クラス | ✓ VERIFIED | L428 に GeminiProvider(OCRProvider) 実装。_build_payload/ocr_image/_parse_response/list_models 完備 |
| `pagefolio/ocr.py` | build_provider の gemini 分岐・_resolve_api_key の dual env var・run_with_bounded_buffer | ✓ VERIFIED | L88 gemini 分岐・L485 build_provider gemini・L139 run_with_bounded_buffer 実装あり |
| `pagefolio/ocr_dialog.py` | _render_queue・producer-consumer 化 | ✓ SUBSTANTIVE / ✗ WIRING INCOMPLETE | _render_queue あり・_render_next_page(生産者) あり。しかし _start_worker_thread が 1 スレッドのみ起動（CR-01） |
| `pagefolio/settings.py` | ocr_scale: 1.5・gemini_model 既定 | ✓ VERIFIED | L43: `"ocr_scale": 1.5`・L54: `"gemini_model": "gemini-2.5-flash"` |
| `pagefolio/lang.py` | ocr_scale_tradeoff_hint（ja/en） | ✓ VERIFIED | L317（ja）・L675（en）に存在 |
| `pagefolio/dialogs/llm_config.py` | gemini プロバイダ選択肢・gemini モデル欄・ocr_scale ヒント | ✓ VERIFIED | provider_combo に "gemini"・gemini_section_frame・ocr_scale_tradeoff_hint Label |
| `pagefolio/constants.py` | APP_VERSION v1.4.0 | ✓ VERIFIED | L12: `APP_VERSION = "v1.4.0"` |
| `tests/test_ocr_providers.py` | TestGeminiProvider 系テスト | ✓ VERIFIED | 22 テスト全 PASS |
| `tests/test_ocr.py` | TestResolveApiKeyGemini・TestBuildProviderGemini・TestProducerConsumerMemory | ✓ VERIFIED | 計 11 テスト全 PASS |
| `tests/test_provider_ui.py` | gemini プロバイダ判定テスト | ✓ VERIFIED | TestIsCloudProvider gemini / TestNeedsSessionKey gemini 系 全 PASS |
| `tests/test_settings_keyguard.py` | ocr_scale==1.5・gemini_model 既定テスト | ✓ VERIFIED（テストスイート 373 PASS） | 全 PASS |

---

## キーリンク検証

| From | To | Via | 状態 | 詳細 |
|------|-----|-----|------|------|
| ocr.py build_provider | ocr_providers.GeminiProvider | `elif name == "gemini":` 分岐 (L485) | ✓ WIRED | 確認済み |
| ocr.py _resolve_api_key | os.environ GEMINI_API_KEY / GOOGLE_API_KEY | dual env var フォールバック (L91) | ✓ WIRED | 確認済み |
| ocr_dialog.py _render_next_page | _render_queue | queue.Queue(maxsize=concurrency+1) | ✓ WIRED | 確認済み |
| ocr_dialog.py _start_worker_thread | _worker | threading.Thread（1 本のみ） | ✗ PARTIAL | concurrency 本起動すべきところ 1 本のみ（CR-01） |
| llm_config.py provider_combo | ocr_provider="gemini" | values=["off","lmstudio","claude","gemini"] | ✓ WIRED | 確認済み |
| ocr_dialog.py _is_cloud_provider | gemini ゲート | `name in ("claude","gemini")` (L523) | ✓ WIRED | 確認済み |
| ocr_dialog.py _needs_session_key | GEMINI_API_KEY/GOOGLE_API_KEY | dual env var チェック (L578-582) | ✓ WIRED | 確認済み |

---

## データフロートレース（Level 4）

| アーティファクト | データ変数 | ソース | 実データを返すか | 状態 |
|----------------|-----------|--------|----------------|------|
| GeminiProvider.ocr_image | text | Gemini generateContent API (urllib) | Yes（モックテスト検証済み） | ✓ FLOWING（モック確認） |
| run_with_bounded_buffer | results | render_fn → buf → provider.ocr_image | Yes・del b64 で破棄も確認 | ✓ FLOWING |
| OCRDialog._worker | self.results[page_idx] | _render_queue.get() → provider.ocr_image | Yes・ただし concurrency=1 固定（CR-01） | ✗ PARTIAL |

---

## 振る舞いスポットチェック

| 確認事項 | コマンド | 結果 | 状態 |
|---------|---------|------|------|
| GeminiProvider テスト全通過 | pytest tests/test_ocr_providers.py -k Gemini | 22 passed | ✓ PASS |
| dual env var・build_provider テスト | pytest tests/test_ocr.py -k "Gemini or BuildProvider or ResolveApiKey" | 23 passed | ✓ PASS |
| メモリ非蓄積テスト | pytest tests/test_ocr.py::TestProducerConsumerMemory | 3 passed | ✓ PASS |
| provider_ui テスト（gemini 判定） | pytest tests/test_provider_ui.py | 52 passed | ✓ PASS |
| フルスイート | pytest tests/ | 373 passed | ✓ PASS |

---

## アンチパターン検出

| ファイル | 行 | パターン | 重大度 | 影響 |
|---------|----|---------|--------|------|
| `pagefolio/ocr_dialog.py` | L946-949 | `_start_worker_thread` が 1 スレッドのみ起動 | BLOCKER | LM Studio ユーザーの並列度が concurrency 設定に関わらず常に 1 に退行（CR-01） |
| `pagefolio/ocr_dialog.py` | L1104 / L887 | `_finish_cancelled` に `_done` ガードなし | BLOCKER | キャンセル時に `_render_results_ordered()` が 2 回呼ばれ OCR テキストが二重挿入される（CR-02） |
| `pagefolio/ocr_dialog.py` | L801 | `self._ocr_scale = 2.0`（例外パス） | WARNING | TclError/ValueError 例外パスで 1.5 でなく旧値 2.0 が使われる（WR-01） |
| `pagefolio/dialogs/llm_config.py` | L328 | `get("ocr_scale", 2.0)` | WARNING | UI 初期値フォールバックが旧値 2.0 のまま（WR-01）。settings 経由の通常フローは 1.5 が使われるため機能的バグは稀 |
| `pagefolio/dialogs/llm_config.py` | L717 | `llm_settings["ocr_scale"] = 2.0` | WARNING | _apply の TclError/ValueError 例外パスで旧値 2.0 が設定される（WR-01） |
| `pagefolio/ocr.py` | L35 | `DEFAULT_OCR_SCALE = 2.0` | WARNING | page_to_png_b64 デフォルト引数が旧値のまま（WR-01）。実際の呼び出しは settings 由来値で上書きされる |
| `pagefolio/ocr.py` | L319 | `executor.shutdown(cancel_futures=True)` | WARNING | Python 3.8 非互換（cancel_futures は 3.9+）。現環境 3.14.3 では問題なし（WR-02） |
| `pagefolio/ocr.py` | L442 | `executor.shutdown(cancel_futures=True)`（run_parallel） | WARNING | 同上（WR-02）。既存コードに同一問題あり |
| `pagefolio/settings.py` | L16 | _SENSITIVE_KEYS に GOOGLE_API_KEY・google_api_key が未登録 | WARNING | Gemini フォールバック env var キー名が保護集合から漏れる（WR-03）。実運用上 settings に書き込まれる設計にはなっていないが防御層として不完全 |
| `pagefolio/ocr_dialog.py` | L1008 | `import time as _time` がループ内 | INFO | リトライループ内の慣習違反（IN-02）。副作用はなし |

---

## 要件カバレッジ

| 要件 ID | 記述（REQUIREMENTS.md より） | プラン | 状態 | 証拠 |
|---------|---------------------------|-------|------|------|
| OCR-API-02 | Gemini で OCR 実行 | 06-01, 06-03 | ✓ SATISFIED | GeminiProvider 実装・22 テスト通過 |
| OCR-PERF-02 | ページ単位 render→送信→破棄 | 06-02 | ✗ BLOCKED | CR-01: OCRDialog._start_worker_thread が 1 スレッドのみ起動。run_with_bounded_buffer ヘルパーは正しいが OCRDialog が活用していない |
| OCR-PERF-05 | ocr_scale 既定 1.5・UI ヒント | 06-03 | ✓ SATISFIED | settings.py 1.5・lang.py ヒント・llm_config.py Label 確認済み |
| OCR-QA-01 | Provider モックテスト | 06-01, 06-02, 06-03 | ✓ SATISFIED | 373 テスト全通過 |

---

## 人間による検証が必要な項目

なし（今フェーズでは自動検証で全項目判定可能）。

---

## ギャップサマリー

Phase 06 では Gemini プロバイダの **API 実装・テスト・UI 統合・ocr_scale 設定** が正しく実装された（SC-1, SC-3, SC-4 は VERIFIED）。

しかし **CR-01（シングルスレッド退行）** が成功基準 SC-2（OCR-PERF-02）を BLOCKER 状態にしている。

06-02-PLAN.md は「LM Studio の並列度（最大 8）は ThreadPoolExecutor で維持し後方互換を守る」と明記し、Gemini(max_concurrency=1) の場合のみ「変更なし」と書いている。しかし現在の `_start_worker_thread` は **すべてのプロバイダ** で 1 スレッドのみ起動するため、LM Studio の concurrency=4 ユーザーは静黙にパフォーマンスが 1/4 以下に退行する。

さらに **CR-02（_finish_cancelled 二重呼び出し）** が OCR テキストの二重挿入バグを引き起こす。BLOCKER として評価するが、OCR-PERF-02 要件には直接関係しないためギャップは CR-01 にまとめた。

**警告事項（WR-01, WR-02, WR-03）** はフォールバックパスの不整合・Python 3.8 非互換・SENSITIVE_KEYS 漏れで、通常フローへの影響は軽微だが技術的負債として残る。

---

_検証日時: 2026-06-07T12:00:00Z_
_検証者: Claude (gsd-verifier)_
