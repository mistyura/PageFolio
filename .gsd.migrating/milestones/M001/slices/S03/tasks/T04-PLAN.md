---
estimated_steps: 27
estimated_files: 1
skills_used: []
---

# T04: dnd.py の _save_undo() 呼び出しを actual_dest 計算後に移動して新シグネチャに更新

`dnd.py` の `_dnd_drop()` メソッドにある `self._save_undo()` 呼び出しを新シグネチャ `_save_undo("move", src=src, actual_dest=actual_dest)` に更新する。

**重要な位置変更が必要:**
現行コードでは `self._save_undo()` が `actual_dest` の計算より **前** にある（行99付近）。差分形式では `actual_dest` を `_save_undo` に渡す必要があるため、呼び出しを `actual_dest` が確定した **後** に移動しなければならない。

**現行コードの構造（_dnd_drop メソッド）:**
```python
self._save_undo()          # ← ここが問題（actual_dest がまだない）
if dest >= n:
    self.doc.move_page(src, -1)
    actual_dest = n - 1
else:
    actual_dest = dest if dest < src else dest - 1
    self.doc.move_page(src, dest)
```

**変更後の構造:**
```python
if dest >= n:
    self.doc.move_page(src, -1)
    actual_dest = n - 1
else:
    actual_dest = dest if dest < src else dest - 1
    self.doc.move_page(src, dest)
self._save_undo("move", src=src, actual_dest=actual_dest)  # ← actual_dest 確定後
```

**制約:**
- `_save_undo` は `self.doc.move_page()` の **後** に呼ぶこと（move は既に実行済みのため、undo 時は `move_page(actual_dest, src)` で逆操作する）
- `_undo_stack` / `_redo_stack` のクリアは `_save_undo` 内で行われるため、呼び出し側での追加処理不要
- メソッド名が `_dnd_drop` であることを確認（grep 結果: dnd.py:90付近）

## Inputs

- `pagefolio/file_ops.py`
- `pagefolio/dnd.py`

## Expected Output

- `pagefolio/dnd.py`

## Verification

python -c "import ast; ast.parse(open('pagefolio/dnd.py', encoding='utf-8').read()); print('OK')"
