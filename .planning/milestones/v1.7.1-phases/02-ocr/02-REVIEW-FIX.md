---
phase: 02-ocr
fixed_at: 2026-07-05T00:00:00Z
review_path: .planning/phases/02-ocr/02-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-05T00:00:00Z
**Source review:** .planning/phases/02-ocr/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6（Critical 2 + Warning 4。Info 2件 (IN-01, IN-02) は fix_scope により対象外）
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: `OCR_PRICE_TABLE` type annotation breaks the project's Python 3.8 compatibility requirement

**Files modified:** `pagefolio/ocr_dialog.py`
**Commit:** `d8dc867`
**Applied fix:** `OCR_PRICE_TABLE` の型注釈 `dict[str, tuple[float, float]]` を文字列リテラル
`"dict[str, tuple[float, float]]"` に変更し、`pagefolio/ocr.py` の
`PROVIDER_OCR_PROMPTS`/`PROVIDER_SUMMARY_PROMPTS` と同じ規約に揃えた。これにより
Python 3.8 環境でのモジュール import 時 `TypeError` を回避する。

### CR-02: `RunPodProvider.list_models()` silently swallowing real errors and reports false success

**Files modified:** `pagefolio/ocr_providers.py`
**Commit:** `62242e6`
**Applied fix:** `list_models()` 内の2つの `except Exception: return [...]`（握り潰し）を撤去し、
他プロバイダ（LMStudio/Gemini/Ollama）と同じ例外契約
（`TimeoutError`/`RuntimeError`（HTTPError）/`ConnectionError`（URLError）、JSON パース失敗時は
`RuntimeError`）に揃えた。呼び出し元 `llm_config.py._refresh_runpod_models` の
`try/except Exception` による失敗表示分岐が正しく発火するようになる。

### WR-01: Partial sentinel delivery is not retried on cancel/fatal-error paths

**Files modified:** `pagefolio/ocr_dialog.py`
**Commit:** `6a82700`
**Applied fix:** `_render_next_page` の cancel / fatal 終了分岐で `send_sentinels` の戻り値
（実送信本数）を確認し、部分送出時は新設した `_retry_sentinels(gen, remaining)` ヘルパーで
残り本数のみを再試行するようにした。「全ページ完了」分岐が既に持っていた再試行ロジックと
同等の堅牢性を残り2分岐にも適用し、キュー満杯時の worker スレッド無限ポーリング残留を防止する。
`send_sentinels` の docstring 契約（「既に送信済みの本数を再送してはならない」）を守るため、
単純な `_render_next_page` 再呼び出しではなく専用ヘルパーで残数のみを扱う設計とした。

*注記: この修正はスレッド終了タイミングに関わるロジック修正であり、構文/静的検証のみでは
実行時の完全な正しさを保証できない。関連テスト（`test_ocr_dialog` 系・`test_ocr_pipeline.py`）は
全て通過しているが、キュー満杯を誘発する高負荷シナリオでの実地確認を推奨する。*

### WR-02: Cancellation is not re-checked between retry attempts

**Files modified:** `pagefolio/ocr_pipeline.py`, `pagefolio/ocr.py`
**Commit:** `788bbc5`
**Applied fix:** `ocr_pipeline.consume_one` のリトライループ（`for attempt in range(1, MAX_RETRIES + 1)`）
先頭と、レガシー実装 `ocr.run_parallel._call` の同等ループ先頭の両方に
`if _is_cancelled() or state.is_fatal(): return` （`ocr.py` 側は `fatal["msg"] is not None`）を追加。
バックオフ待機中に Cancel された場合、次のリトライ試行（追加の課金対象 API 呼び出し）へ進まず
即座に打ち切るようになる。レビューの File 欄が両ファイルを明示していたため、IN-01 で指摘された
「2つの重複実装が同じ穴を共有する」リスクを踏まえ両方を修正した（重複自体の解消は IN-01 の
スコープであり本 fix では対象外）。

*注記: この修正はキャンセル判定タイミングに関わるロジック修正であり、構文/静的検証のみでは
実行時の完全な正しさを保証できない。関連テストは全て通過しているが、実際のリトライ待機中に
Cancel を押す手動シナリオでの実地確認を推奨する。*

### WR-03: Dead/redundant branch in `RunPodProvider.list_models()`

**Files modified:** `pagefolio/ocr_providers.py`
**Commit:** `a25d540`
**Applied fix:** `base_url.endswith("/v1")` の if/else が両方とも同じ `base_url + "/models"` を
返していた死んだ分岐を撤去し、`endpoint = self.url.rstrip("/") + "/models"` の1行に集約した。

### WR-04: `PluginManager.load_plugin()` leaves a partially-loaded plugin registered when `on_load` raises

**Files modified:** `pagefolio/plugins.py`
**Commit:** `3e21d28`
**Applied fix:** `instance.on_load(app)` を専用の `try/except Exception` で包み、`enable_plugin()` と
同じ log-and-continue パターンに揃えた。`on_load` が例外を送出しても `self._plugins[plugin_id]` への
登録・戻り値（インスタンス）・`is_enabled()` の状態が矛盾しなくなる（半初期化インスタンスが
"失敗" と "登録済み" の両方の顔を持つ不整合を解消）。

## Skipped Issues

None — 対象6件すべて修正済み。

## テスト・リント結果

- `pytest -q`: **780 passed**（全件成功・リグレッションなし）
- `ruff check .`: **All checks passed!**
- `ruff format --check .`: **54 files already formatted**（フォーマット崩れなし）

## 対象外（fix_scope: critical_warning）

- IN-01: Duplicate retry/backoff implementation（`ocr.run_parallel` vs `ocr_pipeline.consume_one`）
- IN-02: `TesseractProvider.RECOMMENDED_LANGS` is unused dead code

Info レベルの2件は `fix_scope=critical_warning` のため今回は対象外。必要であれば
`fix_scope=all` で再実行するか、手動対応を検討のこと。

---

_Fixed: 2026-07-05T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
