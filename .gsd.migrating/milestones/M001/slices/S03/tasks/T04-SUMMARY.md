---
id: T04
parent: S03
milestone: M001
key_files:
  - pagefolio/dnd.py
key_decisions:
  - _save_undo() は self.doc.move_page() の実行後かつ actual_dest 確定後に呼ぶ（差分形式で actual_dest が必須のため）
duration: 
verification_result: passed
completed_at: 2026-05-04T04:46:17.220Z
blocker_discovered: false
---

# T04: dnd.py の _dnd_drop() で _save_undo() 呼び出しを actual_dest 確定後に移動し、新シグネチャ ("move", src=src, actual_dest=actual_dest) に更新

**dnd.py の _dnd_drop() で _save_undo() 呼び出しを actual_dest 確定後に移動し、新シグネチャ ("move", src=src, actual_dest=actual_dest) に更新**

## What Happened

タスクプランの通り、`dnd.py` の `_dnd_drop()` メソッドにある `self._save_undo()` 呼び出し（旧: 引数なし、位置: actual_dest 計算前の行99）を変更した。

**変更内容:**
- `self._save_undo()` をブロック冒頭（actual_dest 未確定の位置）から削除
- `if dest >= n: ... else: ...` ブロックの直後（actual_dest 確定後）に `self._save_undo("move", src=src, actual_dest=actual_dest)` を追加

**設計上の理由:**
差分形式の `_save_undo` は `actual_dest` を kwargs として受け取り、undo 時に `move_page(actual_dest, src)` で逆操作するため、`actual_dest` が確定してから呼び出す必要がある。また、`self.doc.move_page()` の実行後に呼ぶことで、undo エントリが「移動済み状態からの逆操作」として正しく記録される。

## Verification

構文チェック: `python -c "import ast; ast.parse(...); print('OK')"` → OK
ruff check: All checks passed!
ruff format --check: 1 file already formatted

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "import ast; ast.parse(open('pagefolio/dnd.py', encoding='utf-8').read()); print('OK')"` | 0 | ✅ pass | 150ms |
| 2 | `ruff check pagefolio/dnd.py` | 0 | ✅ pass | 200ms |
| 3 | `ruff format pagefolio/dnd.py --check` | 0 | ✅ pass | 180ms |

## Deviations

なし

## Known Issues

なし

## Files Created/Modified

- `pagefolio/dnd.py`
