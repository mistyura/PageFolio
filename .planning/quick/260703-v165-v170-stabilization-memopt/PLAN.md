---
quick_id: 260703-svm
slug: v165-v170-stabilization-memopt
date: 2026-07-03
status: complete
---

# Plan: PageFolio v1.6.5（安定化パッチ）/ v1.7.0（コア最適化）実装プラン

> ユーザー承認済みプラン（2026-07-03）。実装は同日完了 — 実施結果は
> [SUMMARY.md](./SUMMARY.md) を参照。

## Context

v1.6.4 で導入した「複数ページ OCR 統合サマリ生成」機能には、①進捗表示が粗く体感フリーズする ②タイムアウト・トークン上限エラーの扱いが不親切 ③プロバイダ間でリトライ挙動が非対称、という安定性課題が残っている（v1.6.4 SUMMARY.md の既知リスクと一致）。v1.6.5 はこれらの安定化に加え、ユーザー要望のページ編集機能（黒塗り・モザイク）をトリミングと同じカテゴリに追加する。v1.7.0 は大規模 PDF での Undo/Redo メモリ圧迫の根本解決とストレステスト自動化を行う。

### 事前調査で確定した重要事実

- **v1.7.0 要件書の前提は実態と相違**: undo の「PDF 全体 doc.tobytes() 保持」は v1.3.0 で既に廃止済み（対称デルタ方式）。実際のメモリ消費源は `delete` op のページ単位 bytes（file_ops.py:56-64）と `merge_resize` の二重 bytes（page_ops.py:578-596）、および undo/redo 往復ごとの再キャプチャ（file_ops.py:127-146, 189-226）×最大20世代。→ **v1.7.0 は「ページ bytes デルタのディスク退避 + ストレステスト」に再定義**（要件書アプローチ案②に相当）。
- **undo バグ発見**: `insert_blank` / `watermark` / `page_numbers` op は `_save_undo`/`_restore_state` に分岐が無く undo が実質 no-op → v1.7.0 で修正。
- redaction API（`add_redact_annot`/`apply_redactions`）は未使用 → 黒塗りは新規実装。
- LMStudio/Ollama の `_post_chat` は 429/5xx を `OCRRetryableError` にマップせず、サマリーがリトライされない（Claude/Gemini/RunPod は対応済み）。
- サマリー実行中は progress_bar 未操作（テキストラベルのみ）・タイムアウトは OCR と共有の 120s。

### 前提判断（ユーザー質問ツールが利用不可だったため既定採用 — 承認時に変更可）

1. **成果物**: 本プラン承認後、v1.6.5 → v1.7.0 の順に本セッションで実装し、ブランチ `claude/v1-6-5-v1-7-0-planning-3rqiah` へコミット/プッシュ（GSD 記録も更新）。
2. **黒塗り・モザイクは要件メモの記載通り v1.6.5 に含める**。
3. **v1.7.0 はディスク退避方式へ再定義**（上記）。

---

## 第1部: v1.6.5

### Phase A: サマリー進捗 UX 改善（`pagefolio/ocr_dialog.py`）

indeterminate パルス + 経過秒数ティッカーの併用:
- `_on_summary`（:1860 付近）: `progress_bar.configure(mode="indeterminate")` + `.start(12)`、`_summary_started_at = time.monotonic()` 保持、`_summary_tick(gen)` を after(1000) で起動。
- 新メソッド `_summary_tick(gen)`: 世代ガード付きで `ocr_summary_elapsed`（`"{msg}（{sec}秒経過）"`）を毎秒更新。
- `_summary_worker` のリトライ待機文言（:1912-1919）は `_summary_base_msg` 更新に変更（ティッカーと合成、競合解消）。
- 新メソッド `_summary_progress_stop()`: tick を after_cancel → `progress_bar.stop()` → determinate に復元（OCR 完了の満杯表示へ）。`_summary_ui_reset` から呼ぶ。
- LANG: `ocr_summary_elapsed`（ja/en）。

### Phase B: エラーハンドリング統一（`pagefolio/ocr_providers.py`, `ocr_dialog.py`）

- **B-1 リトライ対称化**: Claude の Retry-After 解析（:480-491）を関数 `parse_retry_after(headers)` に共通化し、LMStudio `_post_chat`（:228-233）/ Ollama（:1116-1121）の HTTPError 節で 429/5xx → `OCRRetryableError(retry_after=..., code=...)` へマップ。
- **B-2 context window 超過の専用化**: 新例外 `OCRContextLengthError` + 判定純関数 `looks_like_context_error(code, body)`（400/413/422 + "context_length_exceeded" 等の文字列マッチ、小文字比較）。全5プロバイダの HTTPError ハンドラに組み込み。`_summary_worker` に `except OCRContextLengthError` / `except TimeoutError` を追加し、`_on_summary_error(msg, kind)` へ拡張。kind 別 LANG: `ocr_summary_ctx_exceeded`（ページ数を減らす案内）/ `ocr_summary_timeout`（タイムアウト延長案内）。判定漏れは従来の `ocr_summary_failed` に落ちる安全側フォールバック。
- **B-3 サマリー専用タイムアウト**: `_on_summary` で `provider.timeout` を一時的に `max(現値, 300)` へ引き上げ、`_summary_ui_reset` で復元（サマリー中は OCR ボタン disabled なので競合なし。docstring に前提明記）。定数 `SUMMARY_TIMEOUT_MIN = 300`。
- **B-4 事前警告**: `_on_summary` のコスト確認に `len(full_text) > 200_000` で追加確認 `ocr_summary_too_long_confirm`。

### Phase C: 黒塗り・モザイク

- **C-1 座標変換ヘルパー化**: `page_ops.py` に `_canvas_rect_to_pdf()`（`(canvas - 10) / (zoom * 1.5)`）を新設し、3箇所の重複（:294-299, :338-343, :373-378）を置換。
- **C-2 汎用 undo op `page_edit` 新設**（`file_ops.py`）: 対象ページの before-bytes をキャプチャする対称 op。新ヘルパー `_capture_page_bytes(i)`（既存 delete op の tmp.insert_pdf→tobytes パターンを関数化し、delete/insert/merge 分岐からも呼ぶ重複排除）。`_apply_inverse` では適用後 bytes を再キャプチャして同 op のまま返す（対 op 不要）。`_restore_state` は delete_page → insert_pdf(start_at=i) で復元（ページ数不変なので昇順ループで安全）。**このヘルパーが v1.7.0 ディスク退避の差し替え1点になる**。
- **C-3 RedactOpsMixin 新設**（新規 `pagefolio/redact_ops.py`、app.py の Mixin 列に追加）:
  - モード管理: `redact_mode` を追加し、既存 `_crop_drag_start/move/end` のガードを `crop_mode or redact_mode` に拡張（矩形選択・stipple オーバーレイを共用）。crop モードと相互排他。トグルは `CropOn.TButton` スタイル再利用。
  - `_apply_redact()`: `_save_undo("page_edit", targets=...)` → 各ページ `add_redact_annot(rect, fill=(0,0,0))` + `apply_redactions()`（下のテキスト・画像を実削除する真の墨消し）→ `_invalidate_thumb_cache` → `_refresh_all()`。複数ページは bulk_crop の相対座標変換パターン（page_ops.py:379-417）踏襲。
  - `_apply_mosaic()`: 領域を `get_pixmap(clip=rect, matrix=Matrix(2,2))` → Pillow で NEAREST 縮小→拡大（`MOSAIC_BLOCK=16` を constants.py）→ **先に redaction で下地コンテンツ削除**（モザイク下からのテキスト抽出漏えい防止が設計上の要点）→ `insert_image(rect, stream=png)` で焼き込み。
  - 副作用: `apply_redactions()` は矩形交差の注釈も削除 → docstring と開発履歴に明記。
  - UI: `ui_builder.py` `_build_tools` のトリミングセクション f3（:548-581）直後に `sec_redact` セクション（`section()`/`btn()` ヘルパー、`needs_doc=True, edit_only=True`）。
  - LANG（ja/en 両方・test_lang_parity）: `sec_redact`, `redact_mode_on/off`, `btn_apply_redact`, `btn_apply_mosaic`, `info_redact_drag`, `confirm_bulk_redact`, `status_redacted`, `status_mosaic`。

### Phase D: テスト・リリース

- `tests/test_ocr_providers.py`: LMStudio/Ollama の 429（Retry-After 反映）/500 → retryable、401 → RuntimeError 維持、400+context 文言 → `OCRContextLengthError`。`parse_retry_after`/`looks_like_context_error` の純関数テスト。
- サマリー例外シミュレーション（test_ocr.py 拡張 or 新規 test_ocr_summary.py）: FakeProvider に `ConnectionError`（ネットワーク切断）/`TimeoutError`/`RuntimeError("HTTP 401")`（不正キー）/`OCRRetryableError`（リトライ上限）/`OCRContextLengthError` を注入 → kind 別文言・UI 復帰・OCR 結果非破壊・progress_bar の determinate 復元を検証。
- `tests/test_pdf_ops.py`: `page_edit` の do→undo→redo 三段検証（test_bulk_crop_roundtrip :940- パターン）、redact 後 `get_text()` 空、mosaic 後 `get_images()` 増、全 op 網羅群（:711-）へ追加。
- `ruff check . && ruff format .` / `pytest` 全件 / `APP_VERSION = "v1.6.5"` / 開発履歴.md 追記 / README バッジ同期。

実装順序: B（独立）→ A → C-1 → C-2 → C-3 → D。

---

## 第2部: v1.7.0

### Phase 1: undo デルタのディスク退避（新規 `pagefolio/undo_store.py`）

- `MemBlob`（64KiB 未満はメモリ保持・I/O オーバーヘッド回避）/ `FileBlob`（`load()`/`release()`、unlink は suppress(OSError)）/ `UndoBlobStore`（`mkdtemp(prefix="pagefolio_undo_")` に mkstemp 書き出し、`purge()` で一括削除）。
- クリーンアップ: `atexit.register(purge)` + `_quit`/`_close_file` から明示 purge。Windows 考慮: fd 即 close（print_ops.py:20-30 パターン）、delete-on-close 系 API 不使用、unlink 失敗は suppress し purge/atexit の二段回収。
- **deque 溢れフック（設計決定）**: カスタム deque サブクラスは不採用（tests のフェイク7箇所が素の deque を自前生成しており全滅するため）。**素の deque を維持し、FileOpsMixin 側にフックを置く**:
  - `_save_undo`: append 前に maxlen 到達なら `_dispose_state(self._undo_stack[0])`（evict される要素を先に解放）。`_redo_stack.clear()` は各要素 dispose 付きの `_clear_redo_stack()` へ。
  - `_undo`/`_redo`: 受け側 append 前に同フック、消費済み state は直後に `_dispose_state`。
  - `_dispose_state(state)`: op 別に Blob を release。生 bytes は無視（後方互換）。
  - ストアは `_get_undo_store()` で遅延生成（フェイククラス無改修で動作）。
- 差し替えは v1.6.5 で導入する `_capture_page_bytes` → `_capture_page_blob`（put 経由）と `_restore_state` の `blob.load()`、merge_resize（page_ops.py:578-596）の 2 bytes の put 化のみ。
- 既存テスト影響: フェイクの素 deque は maxlen=None なら no-op で無害。「pdf_bytes 不在」不変条件テストはキー参照のみで無影響。実装前に `state["data"]` 直接参照を grep して洗い出す。

### Phase 2: insert_blank / watermark / page_numbers undo バグ修正

- `_insert_blank_page`（page_ops.py:160）→ 既存 `insert` op を再利用（`_save_undo("insert", ...)` + data[1]=1、:483 の既存パターン）。
- `_add_watermark_text`（:188）/ `_add_page_numbers`（:212）→ `page_edit` op へ置換（コンテンツ改変系は before-bytes が正解、バイト量はディスク退避が吸収）。
- 3操作の do→undo→redo ラウンドトリップテスト追加（undo 後に透かし文字列が get_text() から消えることまで検証）。

### Phase 3: ストレステスト自動化（新規 `tests/test_undo_stress.py`）

- フィクスチャ `pdf_120`: fitz で 120 ページ生成（session スコープ、生成2秒未満・CI 対応規模）。
- Test 1（正当性）: 5ページ delete → undo → redo → undo × 25 サイクル、ページ数・get_text() 一致。
- Test 2（メモリ）: `tracemalloc` で 30 サイクルのヒープ増分 < 20MB。ただし PyMuPDF の C 側は tracemalloc に映らないため、**Blob 不変条件（ストア内ファイル数上限・スタッククリア後にディレクトリ空）を主アサーション**とする。RSS は非 Windows のみ参考ログ + 緩い上限。
- Test 3（eviction）: MAX_UNDO+5 回積んで最古の Blob ファイルが物理削除されること。
- 実行時間 < 15 秒目標。

### Phase 4: ドキュメント・リリース

- `.planning/codebase/ARCHITECTURE.md:256` の旧「full PDF serialization」記述を実態（op 別デルタ + 64KiB 超の tempfile 退避）へ修正。
- CLAUDE.md の undo 規約に `page_edit` op と Blob ライフサイクルを追記。
- `APP_VERSION = "v1.7.0"` / 開発履歴.md / README バッジ。
- GSD 記録: `.planning/STATE.md`・`MILESTONES.md`・ROADMAP.md へ v1.6.5/v1.7.0 マイルストーンを記録。

---

## 変更ファイル一覧（主要）

| ファイル | v1.6.5 | v1.7.0 |
|---|---|---|
| `pagefolio/ocr_dialog.py` | 進捗ティッカー・例外分類・タイムアウト引き上げ | — |
| `pagefolio/ocr_providers.py` | 429/5xx マップ・`OCRContextLengthError`・`parse_retry_after` | — |
| `pagefolio/file_ops.py` | `page_edit` op・`_capture_page_bytes` | Blob 化・dispose/eviction フック |
| `pagefolio/page_ops.py` | 座標ヘルパー化 | 3op の undo 修正・merge_resize Blob 化 |
| `pagefolio/redact_ops.py`（新規） | RedactOpsMixin | — |
| `pagefolio/undo_store.py`（新規） | — | MemBlob/FileBlob/UndoBlobStore |
| `pagefolio/ui_builder.py` | sec_redact セクション | — |
| `pagefolio/lang.py` | 新キー ~13個（ja/en 対称） | — |
| `pagefolio/app.py` / `constants.py` | Mixin 追加・MOSAIC_BLOCK・版番 | 版番 |
| `tests/` | provider リトライ・サマリー例外・page_edit/redact/mosaic | test_undo_stress.py・3op ラウンドトリップ |

## リスクと緩和

1. **Blob 化による既存 667 テストへの影響**（最大リスク）→ `_capture_page_bytes` を v1.6.5 で先行導入し差し替え面を1点化。遅延ストア生成でフェイク無改修。実装前 grep で直接参照を洗い出し。
2. **Windows tempfile ロック** → unlink suppress + purge/atexit 二段回収。
3. **provider.timeout 一時変更** → サマリー中 OCR disabled で直列化済み。
4. **context 判定の文字列マッチ漏れ** → 従来メッセージへ安全側フォールバック（クラッシュしない）。

## 検証方法

- 各フェーズ完了ごとに `ruff check . && ruff format .` + `pytest` 全件グリーン（1タスクずつ完了の規約に従う）。
- v1.6.5: サマリー例外シミュレーションテストで ConnectionError/Timeout/401/429/context 超過の全経路が専用文言 + UI 復帰することを確認。redact 後に `page.get_text()` が空（真の墨消し）を確認。
- v1.7.0: ストレステストで Blob 不変条件（eviction 時のファイル削除・クリア後の空ディレクトリ）とヒープ増分上限を確認。
- GUI 実機確認は headless 環境のため不可 → 申し送りに実機確認項目（進捗パルス表示・黒塗り/モザイクの見た目・キャンセル挙動）を明記。
- 各バージョン完了時にコミットし `git push -u origin claude/v1-6-5-v1-7-0-planning-3rqiah`。
