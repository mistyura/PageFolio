---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T01: app.py に _preview_gen / _thumb_gen 状態変数を追加し _rebuild_ui() でリセット

PDFEditorApp.__init__ に self._preview_gen = 0 と self._thumb_gen = 0 を追加する。これらは T02・T03 で実装するバックグラウンドレンダリングが古い（stale）結果を破棄するための世代カウンター。_rebuild_ui() でも両変数をインクリメントして、UI 再構築前に発行されたレンダリング結果が新しいウィジェットに誤適用されないようにする。

Steps:
1. pagefolio/app.py の __init__ メソッドで「self._undo_stack = []」「self._redo_stack = []」などの状態変数ブロック末尾（line 82 付近）に追加:
   self._preview_gen = 0   # プレビュー世代カウンター
   self._thumb_gen = 0     # サムネイル世代カウンター
2. _rebuild_ui() メソッド（line 346〜）で self.thumb_images.clear() の直後に追加:
   self._preview_gen += 1
   self._thumb_gen += 1
3. ruff check . && ruff format . で確認

Must-haves:
- _preview_gen と _thumb_gen が __init__ で 0 に初期化される
- _rebuild_ui() で両変数がインクリメントされる（= UI 再構築時に旧レンダリングをキャンセル）
- ruff クリーン

## Inputs

- `pagefolio/app.py`

## Expected Output

- `pagefolio/app.py`

## Verification

grep -c '_preview_gen\|_thumb_gen' pagefolio/app.py
