---
quick_id: 260703-svm
slug: v165-v170-stabilization-memopt
date: 2026-07-03
status: complete
---

# Summary: v1.6.5（サマリ安定化 + 黒塗り/モザイク）/ v1.7.0（Undo ディスク退避 + ストレステスト）

ブランチ: `claude/v1-6-5-v1-7-0-planning-3rqiah`
コミット: `8949f65`（v1.6.5）/ `3146706`（v1.7.0）— いずれも push 済み
品質確認: `ruff check` / `ruff format` クリーン / `pytest` **707 件パス**（v1.6.4 時点 667 → +40）
（※実行環境に tkinter 3.11 が無く、`python3.12` で pytest を実行）

[PLAN.md](./PLAN.md)（承認済みプラン）をフェーズ順に完遂した。プランからの逸脱は
「テストが発見した既存バグ 1 件（透かし rotate=45）の追加修正」のみ。

## 実施内容

### v1.6.5（コミット `8949f65`・テスト 700 件時点）

- **Phase B — エラーハンドリング統一**: LM Studio / Ollama の 429/5xx を
  `OCRRetryableError` へマップ（5 プロバイダのリトライ対称化）。HTTPError 変換を
  `_raise_mapped_http_error` + `parse_retry_after` + `looks_like_context_error` に
  共通化。`OCRContextLengthError` 新設（400/413/422 + body マーカー判定）。
  `_summary_worker` を kind 別分類（ctx/timeout/汎用）へ拡張し、
  `ocr_summary_ctx_exceeded` / `ocr_summary_timeout` の専用ガイダンスを表示。
  サマリ専用タイムアウト（`SUMMARY_TIMEOUT_MIN=300`・実行中のみ引き上げ→復元）と
  20 万文字超の事前警告（`ocr_summary_too_long_confirm`）を追加。
- **Phase A — 進捗 UX**: サマリ実行中は indeterminate パルス + 経過秒数ティッカー
  （`_summary_tick`・`ocr_summary_elapsed`）。リトライ待機文言は
  `_set_summary_base_msg` でティッカーと合成。終了時 `_summary_progress_stop` で
  determinate（OCR 完了の満杯表示）へ復元。
- **Phase C — 黒塗り/モザイク**: `_canvas_rect_to_pdf` ヘルパー化（3 箇所の重複排除）
  → `page_edit` op 新設（適用前ページ bytes・対称 op・`_capture_page_bytes` 共通化）
  → 新規 `redact_ops.py`（`RedactOpsMixin`）。黒塗りは `add_redact_annot` +
  `apply_redactions` の真の墨消し、モザイクは**先に redaction で下地実削除**してから
  NEAREST ピクセル化画像（`MOSAIC_BLOCK=16`）を焼き込み。トリミングと矩形選択共用・
  相互排他・複数ページ相対座標一括適用。UI はトリミング直下の `sec_redact`。
- **Phase D — テスト**: プロバイダのリトライ対称/context 判定・純関数・サマリ例外
  シミュレーション（切断/タイムアウト/401/429/ctx）・page_edit 往復・黒塗り永続性・
  モザイク下地削除の 33 件を追加。

### v1.7.0（コミット `3146706`・テスト 707 件）

- **Phase 1 — ディスク退避**: 新規 `undo_store.py`
  （`MemBlob`/`FileBlob`/`UndoBlobStore`・64KiB 閾値・書込失敗は MemBlob へ
  フォールバック・atexit purge）。`_capture_page_blob` へ差し替え、復元は
  `_blob_bytes`（生 bytes 後方互換）。merge_resize の merged_bytes/orig_pages も
  Blob 化。ライフサイクルフック: `_push_evicting`（deque 溢れ）・
  `_clear_redo_stack`・消費時 dispose（**逆デルタが同一 data を共有する
  insert_undo→insert_redo / merge_resize 系は identity 比較で除外**）・
  `_clear_undo_stacks`（オープン/クローズ/`_quit` で解放 + purge）。
- **Phase 2 — undo no-op バグ修正**: 白紙挿入 → 既存 `insert` op 再利用、
  透かし/ページ番号 → `page_edit` op。**追加発見バグ**: 透かしの
  `insert_text(rotate=45)` は PyMuPDF で無効値（90 度単位のみ）で
  ValueError により透かし追加自体が失敗していた → `morph=(pivot, Matrix(45))` へ修正。
- **Phase 3 — ストレステスト**: 新規 `tests/test_undo_stress.py`（4 件・約 7 秒）。
  120 ページ・1 ページ 64KiB 超（sha256 チェーンの決定的ノイズ画像で高解像度画像
  PDF を模擬）。正当性 25 サイクル・tracemalloc ヒープ増分 < 20MB・
  **Blob 不変条件**（ストア内ファイル数 ≤ ライブ state・クリア後ディレクトリ消滅）・
  eviction（MAX_UNDO+5 世代で evict 分の物理削除）。
- **Phase 4 — ドキュメント**: `ARCHITECTURE.md` の旧「full PDF serialization」記述を
  実態へ修正。CLAUDE.md に Blob ライフサイクル規約（直接 `append`/`clear` 禁止）を
  追記。STATE.md / MILESTONES.md / 開発履歴.md / README バッジ / `APP_VERSION` 同期。

## 注意点・潜在リスク

- **GUI 実機確認は未実施**（headless 環境）: サマリのパルス + 経過秒数表示、
  黒塗り/モザイクの矩形選択と見た目、モード相互排他、キャンセル挙動。
- 実 LLM プロバイダでの実 429 / 実タイムアウト / 実 context 超過の文言表示は未検証。
- `apply_redactions()` は矩形交差の注釈も削除（PyMuPDF 仕様）。矩形は未回転の
  ページ座標系で適用（トリミングと同じ制約）。
- 前回クラッシュ時の `pagefolio_undo_*` 残骸の起動時掃除は未実装（低優先の将来候補）。
- main へのマージ・タグ・GitHub Release・PyInstaller リビルドは未実施（次セッション）。

## 実行推奨コマンド

```
ruff check . && pytest
```
