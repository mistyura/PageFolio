# S02: バックグラウンドレンダリング

**Goal:** プレビューとサムネイル生成をメインスレッドから分離し、大規模 PDF でページ切替・ズーム変更時に UI がフリーズしないようにする
**Demo:** 大規模 PDF を開いてページ切替・ズームを操作しても UI が応答し続ける

## Must-Haves

- `ruff check . && ruff format .` がエラー・警告ゼロでパス
- `pytest` が 108 件全 PASSED
- `_show_preview()` がバックグラウンドスレッドパターンに改修され、generation counter で stale 結果を破棄する
- `_build_thumbnails()` が `after_idle()` プログレッシブローディングに改修され、UI が即時応答する
- ドキュメント入替時（open/merge/undo-restore）に gen カウンターがインクリメントされ、前 doc のレンダリングがキャンセルされる

## Proof Level

- This slice proves: contract — ruff + pytest による静的・単体検証のみ。実際の非同期挙動はヘッドレス環境では確認不可のため、GUI 手動確認は UAT フェーズで実施

## Integration Closure

Upstream: `pagefolio/app.py`（状態変数）、`pagefolio/file_ops.py`（doc 入替トリガー）、`pagefolio/viewer.py`（レンダリング実装）。New wiring: `_preview_gen`・`_thumb_gen` カウンターが app.py → viewer.py → file_ops.py の3モジュール間で共有される。Remaining: S03（Undo 差分化）は本スライスの gen カウンターを引き継がないため独立。

## Verification

- `_preview_gen` と `_thumb_gen` の値を `logger.debug` で出力すると、どの世代のレンダリングが発火・キャンセルされたかをログで追跡可能
- ワーカースレッド内の例外は `except Exception` でキャッチして `logger.debug` に出力すること（無声失敗を避ける）
- stale チェック（`_preview_gen != gen`）が早期リターンした場合の診断は UI 上でプレースホルダーが残留することで視認できる

## Tasks

- [x] **T01: app.py に _preview_gen / _thumb_gen 状態変数を追加し _rebuild_ui() でリセット** `est:30m`
  PDFEditorApp.__init__ に self._preview_gen = 0 と self._thumb_gen = 0 を追加する。これらは T02・T03 で実装するバックグラウンドレンダリングが古い（stale）結果を破棄するための世代カウンター。_rebuild_ui() でも両変数をインクリメントして、UI 再構築前に発行されたレンダリング結果が新しいウィジェットに誤適用されないようにする。
  - Files: `pagefolio/app.py`
  - Verify: grep -c '_preview_gen\|_thumb_gen' pagefolio/app.py

- [x] **T02: _show_preview() をバックグラウンドスレッドパターンに改修** `est:60m`
  viewer.py の _show_preview() をバックグラウンドスレッドパターンに書き換える。PyMuPDF の page.get_pixmap() はメインスレッドで実行すると 50〜200ms ブロックするため、これを daemon=True のワーカースレッドに移譲し、_preview_gen による世代管理で stale 結果を破棄する。
  - Files: `pagefolio/viewer.py`
  - Verify: grep -c 'threading\|_preview_gen\|daemon=True' pagefolio/viewer.py

- [x] **T03: _build_thumbnails() を after_idle() プログレッシブローディングに改修** `est:60m`
  viewer.py の _build_thumbnails() を after_idle() プログレッシブローディングパターンに書き換える。現在は全ページを同期ループ処理するため大規模 PDF で数秒フリーズする。プレースホルダーフレームを全ページ分即時作成し、after_idle() で1枚ずつ逐次レンダリングすることで UI の応答性を維持する。
  - Files: `pagefolio/viewer.py`
  - Verify: grep -c '_add_thumb_placeholder\|after_idle\|render_next' pagefolio/viewer.py

- [x] **T04: file_ops.py のドキュメント入替3箇所で gen カウンターをインクリメント** `est:30m`
  file_ops.py の _open_pdf_path()、_do_open_merged()、_restore_state() の3箇所でドキュメント入替時に self._preview_gen += 1 と self._thumb_gen += 1 をインクリメントする。これにより、前のドキュメントに対して発行されたバックグラウンドレンダリング処理が新しいドキュメントに誤適用されることを防ぐ。
  - Files: `pagefolio/file_ops.py`
  - Verify: grep -c '_preview_gen\|_thumb_gen' pagefolio/file_ops.py

- [x] **T05: ruff リント・フォーマットと pytest 全件パスを確認** `est:20m`
  全変更ファイルが ruff check/format をパスし、pytest 108件全 PASSED であることを確認する。問題があれば修正する。
  - Files: `pagefolio/app.py`, `pagefolio/viewer.py`, `pagefolio/file_ops.py`
  - Verify: ruff check . && ruff format . --check && pytest --tb=short -q

## Files Likely Touched

- pagefolio/app.py
- pagefolio/viewer.py
- pagefolio/file_ops.py
