---
id: T01
parent: S02
milestone: M001
key_files:
  - pagefolio/app.py
key_decisions:
  - 世代カウンターを __init__ の Undo/Redo スタック定義直後に配置し、バックグラウンドレンダリング関連の状態変数グループとして区別した
  - _rebuild_ui() では thumb_images.clear() の直後にインクリメントを挿入し、キャッシュクリアと世代更新を連続させた
duration: 
verification_result: passed
completed_at: 2026-05-04T04:13:53.795Z
blocker_discovered: false
---

# T01: app.py に _preview_gen / _thumb_gen 世代カウンターを追加し _rebuild_ui() でリセット

**app.py に _preview_gen / _thumb_gen 世代カウンターを追加し _rebuild_ui() でリセット**

## What Happened

pagefolio/app.py の PDFEditorApp.__init__ に `self._preview_gen = 0` と `self._thumb_gen = 0` を追加した（line 85–86）。これらはバックグラウンドレンダリング（T02・T03 で実装予定）が stale な結果を破棄するための世代カウンター。

また _rebuild_ui() メソッドで `self.thumb_images.clear()` 直後（line 356–357）に両変数のインクリメントを追加した。UI 再構築前に発行されたレンダリング結果が新しいウィジェットへ誤適用されないよう、再構築のたびに世代番号を進める。

ruff check / ruff format --check ともにクリーン。grep -c による検証コマンドで 4 箇所（初期化 2 + インクリメント 2）が確認された。

## Verification

grep -c '_preview_gen\|_thumb_gen' pagefolio/app.py → 4（__init__ 初期化 2 箇所 + _rebuild_ui インクリメント 2 箇所）。ruff check . && ruff format . --check → All checks passed!

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c '_preview_gen\|_thumb_gen' pagefolio/app.py` | 0 | ✅ pass | 120ms |
| 2 | `ruff check . && ruff format . --check` | 0 | ✅ pass | 3200ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pagefolio/app.py`
