---
phase: 03-ocr-a
plan: 02
subsystem: ocr
tags: [ocr, providers, claude, gemini, lang, ocr_dialog, truncation, retry]

# Dependency graph
requires:
  - phase: 03-ocr-a/01
    provides: Phase 3 体感品質・堅牢性の文脈（viewer 側は無関係・files_modified 重複ゼロ）
provides:
  - OCRProvider.ocr_image_ex 段階導入（基底デフォルト=(ocr_image(...),False)）
  - Claude/Gemini の応答途切れ検出（stop_reason/finishReason）+ 部分テキスト保持（D-05）
  - _truncated_pages 集合 + 当該ページへの ocr_err_truncated 併記（パネル内提示・D-04）
  - 待機文言の純関数ヘルパー _build_retry_wait_message（delay→sec 反映・D-06）
  - lang.py: ocr_err_truncated 新規 + ocr_waiting_retry/_server へ {sec} 追加（ja/en parity 291）
affects: [03-03, OCR堅牢性, OCRDialog, クラウドプロバイダ]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "途切れ伝搬は ocr_image_ex の (text, truncated) タプルで運ぶ（属性共有/例外化を避けスレッド安全・Pitfall 2）"
    - "HTTP/解析を _post_messages/_post_generate/_extract_text/_parse_response に分離し ocr_image と ocr_image_ex で共有"
    - "待機文言は _build_retry_wait_message へ抽出し delay 先算出→sec=round(delay) を反映（Tk 非依存で直接テスト可能）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - tests/test_ocr_providers.py
    - tests/test_ocr.py

key-decisions:
  - "A1: ocr_image_ex 段階導入を採用（戻り値タプル化/属性共有を回避し ocr_image の str 契約・全戻り値アサートを無傷で温存）。"
  - "A2: Claude stop_reason==max_tokens / Gemini finishReason==MAX_TOKENS を .get() 安全アクセスで検査。"
  - "D-05: 途切れは「成功＋警告」。部分テキストは破棄せず results に保持し ocr_err_truncated を併記。"
  - "D-06: delay（clamp 後の実待機秒）を待機文言生成の前へ移動し sec=round(delay) を反映。順序入替の回帰を純関数テストで防止。"
  - "D-04: messagebox 能動通知は採らずパネル内（text ウィジェット）提示を強化。"

patterns-established:
  - "途切れ検出テスト: stop_reason/finishReason を含むモックボディで (部分テキスト, True) と保持を assert"
  - "待機文言テスト: 実 delay（clamp 後）由来 round(delay) が文言に含まれ生 raw_delay（86400）が漏れないことを Tk 非依存で assert"

requirements-completed: [V16-QUAL-04]
---

# 03-02 SUMMARY — OCR 堅牢性（応答途切れ検出・部分テキスト保持・待機秒数文言）

## 概要

V16-QUAL-04（成功基準4）を達成。OCR の応答途切れ（トークン超過）を検出してユーザーに
「状況＋次アクション」を提示し、レート制限待機表示に実待機秒数を併記した。実装は既存の
パネル内提示（OCRDialog）の作法を踏襲し、messagebox 能動通知は採らない（D-04）。

## Task 1: ocr_image_ex 段階導入 + Claude/Gemini 途切れ検出

- `OCRProvider` に非抽象メソッド `ocr_image_ex(b64_png, prompt, **kwargs) -> (text, truncated)`
  を新設。基底デフォルトは `(self.ocr_image(...), False)` で LM Studio / Tesseract は後方互換。
- Claude: HTTP 部を `_post_messages`、text 抽出を `_extract_text` に分離し、`ocr_image` と
  `ocr_image_ex` で共有。`ocr_image_ex` は `stop_reason == "max_tokens"` を検査して
  `(text, truncated)` を返す。
- Gemini: HTTP 部を `_post_generate`、途切れ判定を `_is_truncated`（`finishReason == "MAX_TOKENS"`）
  に分離。`ocr_image` の str 契約・例外規約・`_parse_response` は不変。
- 途切れは例外化せずフラグ伝搬（部分テキスト喪失を防ぐ・Pitfall 2）。
- テスト: `TestOcrImageExTruncation`（Claude/Gemini truncated 検出＋部分テキスト保持、
  stop_reason 欠落の正常系、LM Studio 基底デフォルト後方互換）6 件追加。既存 109 件は無改変で全緑。

## Task 2: _worker 伝搬・併記 + 待機秒数文言 + 待機文言の純関数抽出

- `_worker` の API 呼び出しを `text, truncated = self.provider.ocr_image_ex(...)` に変更し、
  `_record_page_success(page_idx, text, truncated=truncated)` で伝搬。
- `_record_page_success` に `truncated` 引数を追加し `_truncated_pages`（set）へ登録/解除。
  `__init__` で初期化、`_on_run` のリラン時 clear・再開時は対象ページを discard。
- `_render_results_ordered` で当該ページの部分テキスト直後に `ocr_err_truncated` を併記。
- 待機文言を純関数 `_build_retry_wait_message(wait_key, page_idx, attempt, delay)` へ抽出。
  `_worker` で `delay = clamp_retry_after(raw_delay)` を待機文言生成より前に算出し、
  `sec=round(delay)` を反映（D-06 順序入替）。`after` クロージャは生成済み文言を set するだけ。
- lang.py: `ocr_err_truncated` 新規 + `ocr_waiting_retry`/`ocr_waiting_retry_server` に `{sec}`
  追加（ja/en 同一キー・parity 291）。
- テスト: `TestRetryWaitMessage`（429 の clamp 後 sec 反映、5xx の生値 86400 非漏洩、
  ja/en×両キーの KeyError 非送出）3 件追加。

## 検証結果

- `pytest tests/test_ocr_providers.py tests/test_ocr.py` — 239 passed
- 全テスト `pytest` — 576 passed
- `ruff check . && ruff format .` — All checks passed
- LANG parity — `set(LANG['ja'])==set(LANG['en'])` OK（291 キー）

## 次プラン（03-03）への申し送り

- lang.py は本プランで確定（`{sec}` 追加・`ocr_err_truncated` 新規・parity 291）。03-03 の
  LANG parity 回帰テストはこの確定状態（291 キー）を基準にできる。
- 03-03 は `tests/test_ocr_providers.py` を caplog テストで触るが本プランの追加関数とは別関数のため衝突なし。
- 実 API での stop_reason/finishReason 値の最終確認は 03-03 の D-08 実機検証チェックリストで実施予定。
