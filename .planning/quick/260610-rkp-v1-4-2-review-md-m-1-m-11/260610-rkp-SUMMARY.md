---
quick_id: 260610-rkp
slug: v1-4-2-review-md-m-1-m-11
phase: quick
plan: 260610-rkp
subsystem: ocr
tags: [bugfix, stability, i18n, threading, provider-api]
completed_date: 2026-06-10
duration_minutes: ~60
tasks_completed: 4
tasks_total: 4
files_created: 0
files_modified: 14
key_decisions:
  - OCR_PRICE_TABLE 辞書を ocr_dialog.py モジュールレベルに定義し _estimate_cost の if/elif を廃止
  - _run_gen 世代カウンタは viewer.py の _preview_gen パターンと完全に揃えた
  - EFFORT_MODELS 完全一致のみ effort 送信（前方互換優先で未知モデルは何も送らない）
  - LANG キーはエラー文言とフェッチ中文言を分離して誤誘導を排除
commits:
  - e98593f: fix(quick-260610-rkp-01) M-1/M-2/M-5 スレッド/ライフサイクル安定化
  - 793080a: fix(quick-260610-rkp-02) M-3/M-4/M-7/M-8/M-9 プロバイダ API 堅牢化
  - 1530d22: refactor(quick-260610-rkp-03) M-6/M-10/M-11 UI/i18n/コスト一貫性修正
  - 7d68f97: chore(quick-260610-rkp-04) v1.4.2 バージョン更新・ドキュメント同期・REVIEW.md 完了マーク
---

# Quick 260610-rkp: v1.4.2 — REVIEW.md M-1〜M-11 安定化修正 Summary

v1.4.0 コードレビュー指摘の中優先度 11 件（M-1〜M-11）を全て解消し、v1.4.2 としてリリース。
スレッド/ライフサイクル安定化・プロバイダ API 堅牢化・UI/i18n/コスト一貫性の 3 軸で対応。

---

## 完了タスク

| # | タスク | コミット | 主要ファイル |
|---|--------|---------|-------------|
| 1 | M-1/M-2/M-5 スレッド/ライフサイクル安定化 | e98593f | ocr_dialog.py, ocr.py, tests/test_ocr.py |
| 2 | M-3/M-4/M-7/M-8/M-9 プロバイダ API 堅牢化 | 793080a | ocr_providers.py, dialogs/llm_config.py, dialogs/settings.py, app.py, tests/test_ocr_providers.py, tests/test_provider_ui.py |
| 3 | M-6/M-10/M-11 UI/i18n/コスト一貫性 | 1530d22 | ocr_dialog.py, dialogs/llm_config.py, lang.py |
| 4 | v1.4.2 バージョン更新・ドキュメント同期 | 7d68f97 | constants.py, README.md, 開発履歴.md, REVIEW.md |

---

## 実装詳細

### Task 1: スレッド/ライフサイクル安定化 (M-1/M-2/M-5)

**M-1 — producer のブロッキング put を排除**
- `put(timeout=0.1)` busy-loop → `put_nowait` + `queue.Full` 時は `after(100)` 再スケジュール
- 終了シグナル `put(None)` 無タイムアウト → `put_nowait` + 再スケジュールパターンに統一
- UI フリーズの最大ケース（タイムアウト 600 秒）を構造的に排除

**M-2 — 世代カウンタ (_run_gen) 導入**
- `self._run_gen = 0` を `__init__` に追加
- `_on_run`, `_clear_text`, `_on_close` で `self._run_gen += 1` してから新世代でワーカー起動
- `_render_next_page(gen)`, `_start_worker_thread(gen)`, `_worker(gen)` が世代一致確認
- viewer.py の `_preview_gen` と同一パターン（コードベース内で一貫したイディオム）

**M-5 — Retry-After クランプ + キャンセル対応スリープ**
- `RETRY_AFTER_CAP = 60.0` 上限値を定数化
- `clamp_retry_after(retry_after, cap=RETRY_AFTER_CAP)` でサーバ指定値を上限クランプ
- `interruptible_sleep(total, is_cancelled, step=0.5)` で 0.5 秒刻みにキャンセル確認
- `run_with_bounded_buffer` / `run_parallel` の全 sleep 箇所に適用

### Task 2: プロバイダ API 堅牢化 (M-3/M-4/M-7/M-8/M-9)

**M-3 — _supports_effort を EFFORT_MODELS 完全一致のみに変更**
- 従来: `"sonnet" in model` で True → effort 非対応の claude-sonnet-4-5 に 400
- 修正後: `model in self.EFFORT_MODELS` の完全一致のみ
- 3-way ブランチ: effort モデル → `output_config`, haiku → `temperature`, 未知 → 何も送らない
- `LLMConfigDialog._model_supports_effort` も同様に完全一致に変更

**M-4 — Gemini 2.5 Pro で thinkingConfig 省略**
- `"pro" not in self.model` の条件を追加し、Pro 系では `thinkingConfig` をペイロードから除外
- 2.5 Pro は thinking 無効化不可で 400 INVALID_ARGUMENT が返る見込みに対応

**M-7 — プラグインプロバイダ初期化の例外正規化**
- `cls()` を `try/except Exception as e: raise RuntimeError(...)` でラップ
- プラグイン失敗が Tk コールバック内で未処理例外になる問題を解消

**M-8 — SettingsDialog → LLMConfigDialog への plugin_manager 伝播**
- `SettingsDialog.__init__` に `plugin_manager=None` 引数追加
- `app.py` の `_open_settings` から `plugin_manager=getattr(self, "plugin_manager", None)` を渡す
- `_open_llm_config` から `LLMConfigDialog` へ `plugin_manager=` を渡すルートが確立

**M-9 — ClaudeProvider レスポンスパースの KeyError 防止**
- `block["text"]` → `block.get("text")` に変更
- フィルタ条件: `block.get("type") == "text" and block.get("text")` で None/欠落を除外

### Task 3: UI/i18n/コスト一貫性 (M-6/M-10/M-11)

**M-6 — OCR_PRICE_TABLE 辞書化**
- `OCR_PRICE_TABLE: dict[str, tuple[float, float]]` をモジュールレベルに定義
- `_lookup_price(model)` ヘルパーで部分一致フォールバック付き辞書引き
- gemini-2.5-flash 単価: $0.075/$0.30 → $0.30/$2.50 MTok に更新（実勢反映）
- `_estimate_cost` の if/elif チェーンが 1 行の辞書引きに変わり拡張容易

**M-10 — 8 箇所のハードコード日本語を LANG 辞書へ移植**
新規 LANG キー（ja/en 両方）:
- `ocr_cost_estimate` — コスト表示文字列
- `ocr_provider_rebuild_error` — プロバイダ再生成エラー
- `llm_fetching_claude_models` — Claude モデル取得中
- `llm_fetching_gemini_models` — Gemini モデル取得中
- `llm_env_key_unset_static` — ANTHROPIC_API_KEY 未設定静的リスト表示
- `llm_env_key_unset_static_gemini` — GEMINI_API_KEY 未設定静的リスト表示
- `llm_model_fetch_failed` — モデル取得失敗フォールバック（エラー内容付き）

**M-11 — except タプルの簡約**
- `except (ValueError, Exception)` → `except Exception` (ocr_dialog.py)
- `except (ConnectionError, TimeoutError, RuntimeError, Exception)` → `except Exception` (llm_config.py 2 箇所)

---

## テスト追加

| テストクラス | カバー | ファイル |
|------------|--------|---------|
| `TestClampRetryAfter` | clamp_retry_after 境界値 | test_ocr.py |
| `TestInterruptibleSleep` | キャンセル対応スリープ | test_ocr.py |
| `TestRenderNextPageQueueFullInvariant` | put_nowait + after(100) 再スケジュール | test_ocr.py |
| `TestRunParallelBackoff` (修正) | sum ベースアサーション対応 | test_ocr.py |
| `TestClaudeProviderSupportsEffortStrict` | EFFORT_MODELS 完全一致のみ | test_ocr_providers.py |
| `TestGeminiProviderThinkingConfig` | Pro で thinkingConfig 省略 | test_ocr_providers.py |
| `TestClaudeProviderTextKeyMissing` | block.get("text") KeyError 防止 | test_ocr_providers.py |
| `TestBuildProviderPluginRuntimeError` | プラグイン初期化例外正規化 | test_ocr_providers.py |
| `TestSettingsDialogPluginManager` | plugin_manager パラメータ保持 | test_provider_ui.py |

最終テスト結果: **425 passed** (ruff check/format: 全通過)

---

## 計画からの逸脱

なし — 計画通りに実行。

---

## Self-Check: PASSED

- [x] SUMMARY.md 作成済み: `.planning/quick/260610-rkp-v1-4-2-review-md-m-1-m-11/260610-rkp-SUMMARY.md`
- [x] コミット e98593f 存在確認済み
- [x] コミット 793080a 存在確認済み
- [x] コミット 1530d22 存在確認済み
- [x] コミット 7d68f97 存在確認済み
- [x] APP_VERSION = "v1.4.2" 更新済み
- [x] LANG ja/en キー一致: 258 キー
- [x] 425 テスト全通過
