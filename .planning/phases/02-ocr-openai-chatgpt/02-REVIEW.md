---
phase: 02-ocr-openai-chatgpt
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - docs/CONFIGURATION.md
  - docs/OCR-PROVIDERS.md
  - pagefolio/dialogs/batch_ocr.py
  - pagefolio/dialogs/llm_config/dialog.py
  - pagefolio/dialogs/llm_config/model_fetch.py
  - pagefolio/dialogs/llm_config/sections.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_providers/__init__.py
  - pagefolio/ocr_providers/catalog.py
  - pagefolio/ocr_providers/openai_provider.py
  - pagefolio/ocr_providers/registry.py
  - pagefolio/settings.py
  - tests/test_batch_ocr_dialog.py
  - tests/test_ocr_fallback.py
  - tests/test_ocr_provider_catalog.py
  - tests/test_ocr_providers.py
  - tests/test_provider_ui.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 02 のスコープ（OCR プロバイダメタデータの catalog 化 + OpenAI(ChatGPT) プロバイダ追加）を標準深度でファイル単位レビューした。プロジェクト context に明記されていた既知バグ類型「プロバイダ分岐の網羅漏れ」（`ocr_dialog.py` の if/elif に `openai` 分岐が無く裸の `api_key` なしで `build_provider` が呼ばれる）は、`_apply_llm_settings` と `_on_run` の両方に `openai` 分岐が実装済みで、コミット 36e7cc2 の修正が正しく反映されていることを確認した。他の if/elif チェーン（`_on_provider_change`、`build_provider`、`_is_cloud_provider` 系、`_confirm_cost`/`_check_cloud_api_key`/`_resolved_host_text` 等）も openai を含めて網羅されている。

API キーの取り扱い（`_SENSITIVE_KEYS` ガード・`registry.py` の独立性制約・セッションキー優先順位）、同意ゲート（`_confirm_cost`/`_confirm_summary_cost` が「今後表示しない」オプションなしで毎回表示される構造）、多層防御（`_validate_openai_id`/`_sanitize_header_value`/`_apply_gen_params`/`_build_payload` の detail クランプ）はいずれも実装・テストとも整合しており、迂回経路は見つからなかった。`docs/CONFIGURATION.md` の機密キー集合（12エントリ）は `registry.sensitive_keys()` の実際の出力と一致し、`pagefolio/lang.py` の ja/en キー数も完全一致（477件）していることを確認した。

一方、`pagefolio/dialogs/batch_ocr.py`（`OCRDialog` からの意図的なコピペ移植モジュール）のバッチ横断サマリのリトライ待機処理に、コピペ移植の際に紛れ込んだ **BLOCKER 級のバグ**を1件検出した（下記 CR-01）。単発 OCR ダイアログ（`ocr_dialog.py`）の対応箇所は正しい実装になっており、`batch_ocr.py` 側だけが誤っている。加えて、この不具合を検知できるテストが存在しないテストギャップも確認した。

## Critical Issues

### CR-01: バッチ横断サマリのリトライ待機が `TypeError` でワーカースレッドごと落ち、UI が永久にハングする

**File:** `pagefolio/dialogs/batch_ocr.py:1132-1158`（該当行は 1154）

**Issue:**

`_batch_summary_worker` の `OCRRetryableError`（HTTP 429 / 5xx）リトライ待機で、`interruptible_sleep` の第2引数に `threading.Event` インスタンスそのもの（`self._summary_cancel_flag`）を渡している。

```python
interruptible_sleep(delay, self._summary_cancel_flag)
```

`interruptible_sleep(total, is_cancelled, step=0.5)`（`pagefolio/ocr.py:204`）は内部で `is_cancelled()` を **呼び出し可能なもの**として扱う：

```python
def interruptible_sleep(total, is_cancelled, step=0.5):
    remaining = total
    while remaining > 0:
        if is_cancelled():   # ← Event インスタンスをそのまま呼ぶと TypeError
            return
        ...
```

`threading.Event` インスタンスは呼び出し不可能（`__call__` を実装していない）ため、`is_cancelled()` の評価で `TypeError: 'Event' object is not callable` が送出される。

この呼び出しは `_batch_summary_worker` 内の `except OCRRetryableError as e:` ブロック内にあり、それ自体を囲む try/except は無いため、例外はそのままバックグラウンドスレッド（`threading.Thread(target=self._batch_summary_worker, ...)`）を丸ごと殺して伝播する。Python のデフォルト動作では、この例外は `threading.excepthook` を通じて標準エラーへログされるだけで、`self.after(0, ...)` によるメインスレッドへの終了通知（成功/失敗/キャンセルいずれの分岐も）が一切実行されない。

結果として:
- `self._summary_running = True` のまま復帰しない（`_summary_ui_reset()` が呼ばれない）
- `self._summary_btn` は `disabled` のまま復帰しない
- ユーザーは「サマリ作成」ボタンが永久に押せなくなる（ダイアログを閉じて開き直すまで回復不能）
- OpenAI/Claude/Gemini/RunPod のいずれのクラウドプロバイダでも、バッチ横断サマリ実行中に一度でも 429（レート制限）または 5xx を受信すると発生する（1回目の失敗で即座に再現し、`MAX_RETRIES` に達する前の必ず通る経路）

同一パターンは他の全箇所で正しく実装されている（`.is_set` という**呼び出し可能な bound method** を渡している）ことをコードベース全体で確認済み:
- `pagefolio/ocr_dialog.py:2318` — `interruptible_sleep(delay, self._summary_cancel_flag.is_set)`（単発 OCR ダイアログのサマリ・正しい）
- `pagefolio/ocr.py:379` — `interruptible_sleep(delay, lambda: bool(_is_cancelled()))`（並列 OCR・正しい）
- `pagefolio/ocr_pipeline.py:248` — `interruptible_sleep(delay, _is_cancelled)`（producer-consumer パイプライン・正しい）

`batch_ocr.py` はモジュール冒頭の docstring で「`OCRDialog` の対応メソッドと同一挙動の独立実装（コピペ移植）」と明記されている設計だが、今回のコピペで `.is_set` の呼び忘れが1箇所紛れ込んだ。

**テストギャップ:** `tests/test_batch_ocr_dialog.py::TestBatchSummary` はバッチサマリの正常系（`test_batch_summary_concat`）・ゼロ件 no-op（`test_batch_summary_zero_completed_noop`）・過大入力警告（`test_batch_summary_oversized_warns`）のみを検証しており、`OCRRetryableError` を送出してリトライ待機を通す経路は一度もテストされていない。単発側 `ocr_dialog.py` の等価な経路も直接のリトライテストは見当たらないが、少なくとも `batch_ocr.py` 固有のコピペ移植箇所ゆえに、この divergence を検知するテストが必要。

**Fix:**

```python
# pagefolio/dialogs/batch_ocr.py:1154
-                interruptible_sleep(delay, self._summary_cancel_flag)
+                interruptible_sleep(delay, self._summary_cancel_flag.is_set)
```

併せて、同じクラスの divergence バグを構造的に防ぐため、`_batch_summary_worker` のリトライループ全体を try/except で堅牢化する（例: `except OCRRetryableError` ブロック内で `interruptible_sleep` 呼び出し自体が失敗しても外側の `except Exception` が捕捉できるよう包む、または `run_parallel`/`consume_one` と同様の共有リトライヘルパーへ `ocr.py` 側で一本化し、`ocr_dialog.py`/`batch_ocr.py` 双方がそれを呼ぶ形にリファクタする）ことを推奨する。回帰防止のため、`OCRRetryableError` を送出する `complete_text_ex` に対する `_batch_summary_worker` のリトライ待機テストを追加すること。

## Warnings

### WR-01: コピペ移植方針がコード分岐（今回のような divergence バグ）を構造的に許容してしまう

**File:** `pagefolio/dialogs/batch_ocr.py`（`_is_cloud_provider`/`_estimate_cost`/`_confirm_cost`/`_check_cloud_api_key`/`_insert_markdown`/`_format_pages_text`/`_summary_worker` 相当・約150行超）

**Issue:** `04-02-PLAN.md` の Review Incorporation 懸念5 により、`OCRDialog` を継承せず該当メソッド群を意図的にコピペ移植する設計が採られている。単一ファイルでの一貫性検証はしやすい反面、CR-01 のように「片方だけ実装ミスが混入し、テストで一方しか固定されない」リスクを本質的に抱える。実際に `interruptible_sleep` の呼び出し引数という、レビューで見落としやすい小さな差分がすり抜けた。

**Fix:** 少なくとも「両ファイルの対応関数が同一の入出力契約を満たすこと」を機械的に固定するパリティテスト（`tests/test_batch_ocr_dialog.py::TestSingleVsBatchHostParity` のような比較テスト）を、コスト確認まわりだけでなくリトライ待機ロジックにも拡張することを推奨する。あるいは、リトライループ自体を `pagefolio/ocr.py` に共有ヘルパーとして切り出し、両ダイアログがそれを呼ぶ形に統合すれば、この種の divergence は構造的に発生しなくなる。

### WR-02: `_batch_summary_worker` は単発版と異なり `OCRContextLengthError`/`NotImplementedError`/`TimeoutError` を個別に区別しない

**File:** `pagefolio/dialogs/batch_ocr.py:1132-1158`

**Issue:** `ocr_dialog.py:_summary_worker`（2276-2358行）は `OCRContextLengthError`（コンテキスト長超過）・`TimeoutError`・`NotImplementedError`（三重ガードの3段目）をそれぞれ専用の `error_kind` として区別し、`_on_summary_error` がユーザーへ状況別の具体的なガイダンス（`ocr_summary_ctx_exceeded`/`ocr_summary_timeout` 等）を表示する。一方 `batch_ocr.py:_batch_summary_worker` はこれらを一括で `except Exception as e:` の汎用エラーとして扱い、`_on_batch_summary_error` も `kind` パラメータを持たない。

バッチサマリでコンテキスト長超過やタイムアウトが発生した場合、ユーザーは「なぜ失敗したか」「どう対処すべきか」の具体的な案内を受け取れず、汎用エラーメッセージのみが表示される。機能として動作はするが、単発 OCR ダイアログと比べてユーザー体験の一貫性が失われている。

**Fix:** 意図的な簡略化であれば問題ないが、`ocr_dialog.py` 側と同水準のエラー種別区別（少なくとも `OCRContextLengthError` の専用メッセージ）をバッチサマリにも追加することを検討する。

## Info

### IN-01: `OCR_PRICE_TABLE` の部分一致ルックアップはキーの宣言順に依存する脆い設計

**File:** `pagefolio/ocr_dialog.py:96-102`, `pagefolio/dialogs/batch_ocr.py:121-129`

**Issue:** `_lookup_price` は `for key, prices in OCR_PRICE_TABLE.items(): if key in model: return prices` という部分文字列一致で単価を解決する。現在のエントリ順序（例: `"claude-sonnet"` が `"claude-3-5-sonnet"` より後）では意図通り動作するが、将来モデル ID を追加する際に順序を誤ると（例: 汎用的なキーを具体的なキーより前に置いてしまう）、誤った単価にサイレントに解決されてしまう。誤った単価はコスト見積り表示にのみ影響し実際の課金には影響しないため深刻度は低いが、順序依存のロジックであることをコメントで明示するか、より厳密な照合（完全一致優先→接頭辞一致のフォールバック、`effort_values_for_model` と同様のパターン）へ寄せることを推奨する。

**Fix:** コメントで「キー追加時は具体的なモデル ID を汎用キーより前に置くこと」を明記する、または `openai_provider.py:effort_values_for_model` と同様に「完全一致優先 → 接頭辞一致」の2段階解決へ統一する。

---

_Reviewed: 2026-08-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
