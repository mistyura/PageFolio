---
phase: 06-gemini-provider
reviewed: 2026-06-07T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - pagefolio/constants.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_providers.py
  - pagefolio/settings.py
  - tests/test_ocr.py
  - tests/test_ocr_providers.py
  - tests/test_provider_ui.py
  - tests/test_settings_keyguard.py
findings:
  critical: 2
  warning: 3
  info: 3
  total: 8
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-06-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 6 では Gemini OCR プロバイダ追加・`ocr_scale` デフォルト値の 1.5 への変更・OCRDialog の producer-consumer（有界バッファ）パイプラインへのリファクタリングが行われた。

セキュリティ設計（APIキー非永続化ガード）・Gemini dual env var 解決・コスト確認フローは概ね正しく実装されている。テストカバレッジも広い。

ただし以下の問題が発見された。

1. **BLOCKER × 2**: (a) `OCRDialog._worker` がシングルスレッドのため LM Studio ユーザーの並列度が常に 1 に退行する。(b) キャンセル時に `_finish_cancelled` が 2 回呼ばれ OCR 結果テキストがダイアログ上で二重表示される。
2. **WARNING × 3**: `DEFAULT_OCR_SCALE`（2.0）と設定デフォルト（1.5）の不整合・`executor.shutdown(cancel_futures=True)` の Python 3.8 非互換・`GOOGLE_API_KEY` が `_SENSITIVE_KEYS` 未登録。
3. **INFO × 3**: コードの重複・ループ内での `import` 実行・冗長な例外クラス列挙。

---

## Critical Issues

### CR-01: OCRDialog._worker がシングルスレッドのみ起動 — LM Studio 並列度が常に 1 に退行

**File:** `pagefolio/ocr_dialog.py:946-949`

**Issue:**
`_start_worker_thread` は `threading.Thread` を 1 本だけ起動する。`self.concurrency` の値はキューサイズ（`maxsize = self.concurrency + 1`、L869）に使われるのみで、consumer スレッド数に反映されていない。

Phase 計画は「LM Studio の並列度を最大 8 まで維持（後方互換）」と明記しているが、実装では LM Studio / Claude / Gemini すべてで実効並列度が 1 に固定される。LM Studio で `ocr_concurrency=4` を設定しているユーザーは静黙にパフォーマンスが 1/4 以下になる。

```python
# 現状: 1スレッドのみ
def _start_worker_thread(self):
    self._worker_thread = threading.Thread(target=self._worker, daemon=True)
    self._worker_thread.start()
```

```python
# 修正例: concurrency 本のスレッドを起動し、workers 本の終了シグナルを送る
def _start_worker_thread(self):
    self._worker_threads = []
    for _ in range(self.concurrency):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._worker_threads.append(t)

# _render_next_page の全ページ完了時（L895）も workers 本の None を送る
for _ in range(self.concurrency):
    self._render_queue.put(None)
```

> 注意: この修正に伴い、進捗管理（`done` カウンタ）のスレッドセーフ化（`threading.Lock`）と終了シグナル数の修正が必要。Gemini（`max_concurrency=1`）は `self.concurrency` が 1 なので変更なし。

---

### CR-02: `_finish_cancelled` がキャンセル時に 2 回呼ばれ OCR 結果が二重挿入される

**File:** `pagefolio/ocr_dialog.py:881-888, 1057-1058`

**Issue:**
`_render_next_page` の冒頭（L881）でキャンセルが検出された場合、以下の順序で実行される。

1. L887: `self._finish_cancelled()` が**メインスレッドで直接呼び出し**される。
2. L884: `put_nowait(None)` で worker に終了シグナルが送られる。
3. worker が `None` を受け取って終了し、L1057 の `_cancel_flag.is_set()` 分岐で `self.after(0, self._finish_cancelled)` が**後から再び呼ばれる**。

`_finish_cancelled` は `_done` チェックなしに `_render_results_ordered()` を呼ぶ（L1108-1109）ため、テキストエリアに OCR 結果テキストが 2 回挿入される（`text.insert("end", ...)` が 2 回実行される）。

```python
# 現状: _done チェックなし
def _finish_cancelled(self):
    self._done = True
    self.progress_var.set(self._L["ocr_cancelled"])
    ...
    if self.results or self.errors:
        self._render_results_ordered()  # <- 2回目も呼ばれる
```

```python
# 修正: 冪等ガードを追加
def _finish_cancelled(self):
    if self._done:        # 既に呼ばれていたら何もしない
        return
    self._done = True
    self.progress_var.set(self._L["ocr_cancelled"])
    ...
    if self.results or self.errors:
        self._render_results_ordered()
```

同様のガードを `_finish_complete` と `_finish_error` にも追加することを推奨する（これらはキャンセル時の二重呼び出し対象ではないが、防御的コーディング）。

---

## Warnings

### WR-01: `DEFAULT_OCR_SCALE`（2.0）と設定デフォルト（1.5）の不整合 — フォールバックが D-11 変更を無視

**Files:**
- `pagefolio/ocr.py:35` — `DEFAULT_OCR_SCALE = 2.0`
- `pagefolio/settings.py:43` — `"ocr_scale": 1.5`（D-11: 新規ユーザー既定を 1.5 へ変更）
- `pagefolio/dialogs/llm_config.py:328` — `self.current_settings.get("ocr_scale", 2.0)` ← 旧値
- `pagefolio/ocr_dialog.py:801` — `self._ocr_scale = 2.0`（`scale_var.get()` 失敗時フォールバック）← 旧値

**Issue:**
D-11 で `settings.py` のデフォルトが 1.5 に変更されたが、`llm_config.py` の `get("ocr_scale", 2.0)` と `ocr_dialog.py` の例外フォールバック `2.0` が更新されていない。通常フロー（settings 経由でウィジェット初期化）では 1.5 が使われるため機能的バグは起きないが、`TclError`/`ValueError` 例外パスでは 2.0 が使われる。

```python
# llm_config.py L328 修正
value=float(self.current_settings.get("ocr_scale", 1.5)),

# ocr_dialog.py L801 修正
except (tk.TclError, ValueError):
    self._ocr_scale = 1.5
```

また `ocr.py` の `DEFAULT_OCR_SCALE = 2.0` 定数も 1.5 に変更すべきかどうか設計判断が必要（この定数は `page_to_png_b64` のデフォルト引数として使われる）。

---

### WR-02: `executor.shutdown(cancel_futures=True)` が Python 3.8 で動作しない

**Files:**
- `pagefolio/ocr.py:319` — `run_with_bounded_buffer` 内
- `pagefolio/ocr.py:442` — `run_parallel` 内

**Issue:**
`ThreadPoolExecutor.shutdown()` の `cancel_futures` パラメータは **Python 3.9 で追加**された。プロジェクトは `CLAUDE.md` で "Python 3.8+" をサポート対象と宣言している。Python 3.8 環境で実行すると `TypeError: shutdown() got an unexpected keyword argument 'cancel_futures'` が発生し、OCR 機能全体が使用不能になる。

`run_parallel` は既存コードで同じ問題があったが、`run_with_bounded_buffer` は今回新規追加で同じ問題を引き継いだ。

```python
# 修正: Python 3.8 互換
import sys
if sys.version_info >= (3, 9):
    executor.shutdown(wait=False, cancel_futures=True)
else:
    executor.shutdown(wait=False)
```

---

### WR-03: `GOOGLE_API_KEY` が `_SENSITIVE_KEYS` に未登録

**File:** `pagefolio/settings.py:16`

**Issue:**
`_SENSITIVE_KEYS = {"claude_api_key", "gemini_api_key", "anthropic_api_key", "api_key"}` に `GOOGLE_API_KEY`（大文字）と `google_api_key`（小文字）が含まれていない。

Gemini プロバイダは `GOOGLE_API_KEY` を環境変数フォールバックとして使用するが（`ocr.py:91`）、`settings` 辞書に `GOOGLE_API_KEY` というキーが誤って格納された場合に `_save_settings` が除外せず JSON に平文で書き込まれてしまう。

構造的な防御の最後の砦として、設計上考えられる全キー名をカバーすべきである。

```python
# 修正
_SENSITIVE_KEYS = {
    "claude_api_key", "gemini_api_key", "google_api_key",
    "anthropic_api_key", "api_key",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY",
}
```

---

## Info

### IN-01: `_apply_llm_settings` と `_on_run` でプロバイダ再生成コードが重複

**File:** `pagefolio/ocr_dialog.py:622-659, 832-865`

**Issue:**
`_apply_llm_settings`（LLM設定変更時）と `_on_run`（実行ボタン押下時）の両方に、ほぼ同一の「プロバイダ再生成」ブランチ（claude/gemini/lmstudio 分岐 + `_resolve_api_key` + `build_provider`）が存在する。ロジックの二重管理により、将来プロバイダが追加された際に片方を更新し忘れるリスクがある。

```python
# 修正: 共通メソッドに抽出
def _rebuild_provider(self):
    """現在の settings と session_keys からプロバイダを再生成して self.provider に設定。"""
    name = self.app.settings.get("ocr_provider", "")
    from pagefolio.ocr import _resolve_api_key, build_provider
    from pagefolio.ocr_providers import OCRAPIKeyError
    session_keys = getattr(self.app, "_session_api_keys", {})
    api_key = None
    if name in ("claude", "gemini"):
        try:
            api_key = _resolve_api_key(name, session_keys)
        except OCRAPIKeyError:
            api_key = ""
    try:
        self.provider = build_provider(self.app.settings, api_key=api_key)
    except (ValueError, Exception) as e:
        logger.error("provider 再生成に失敗: %s", e)
        self.progress_var.set(f"プロバイダ再生成エラー: {e}")
```

---

### IN-02: `_worker` ループ内で毎回 `import time as _time` が実行される

**File:** `pagefolio/ocr_dialog.py:1008`

**Issue:**
`import` 文がリトライ処理ループの内部（`OCRRetryableError` キャッチ節）に置かれており、OCR リトライのたびに実行される。Python のインポートはモジュールキャッシュにより副作用は無視できるが、ループ内 `import` は慣習的に避けるべきであり、コードの可読性を下げる。ファイル先頭（L6 の `import logging` 付近）に移動すること。

---

### IN-03: `except (ConnectionError, TimeoutError, RuntimeError, Exception)` が冗長

**File:** `pagefolio/dialogs/llm_config.py:622, 658`

**Issue:**
`Exception` は `ConnectionError`、`TimeoutError`、`RuntimeError` のスーパークラスであるため、前の 3 つを列挙しても意味がない。プロジェクト規約（`CLAUDE.md`）の `except Exception as e:` 形式に統一すること。

```python
# 修正
except Exception as e:
    logger.warning("Claude モデル取得失敗（静的リストへフォールバック）: %s", e)
```

---

_Reviewed: 2026-06-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
