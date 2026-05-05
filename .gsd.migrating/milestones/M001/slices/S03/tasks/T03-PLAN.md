---
estimated_steps: 25
estimated_files: 1
skills_used: []
---

# T03: page_ops.py の _save_undo() 呼び出し6箇所を新シグネチャに更新

T01/T02 で `_save_undo(op, **kwargs)` に変更されたため、`page_ops.py` 内の既存6箇所の `self._save_undo()` 呼び出しを新シグネチャに更新する。

**変更箇所と変更内容（必ずこの順序で確認・適用すること）:**

1. `_rotate_selected(deg)` — **順序変更が必要**
   - 現行: `self._save_undo()` → `targets = self._get_targets()`
   - 変更後: `targets = self._get_targets()` → `self._save_undo("rotate", targets=targets)` ← targets を先に取得してから渡す

2. `_delete_selected()` — targets はすでに上で取得済み
   - 現行: `self._save_undo()`（targets 変数は既に確定している）
   - 変更後: `self._save_undo("delete", targets=targets)` ← 削除前に呼ぶことを確認（現行も削除前）
   - 注意: `_delete_selected()` の targets は `sorted(self._get_targets(), reverse=True)` で降順ソート済み。`_save_undo` 内で昇順ソートし直すため問題なし

3. `_duplicate_page()` — pno を渡す
   - 現行: `pno = self.current_page` → `self._save_undo()`
   - 変更後: `self._save_undo("duplicate", pno=pno)` ← pno 確定後に呼ぶ（現行と同じ位置）

4. `_crop_page()` — current_page を渡す
   - 現行: `self._save_undo()` （page_ops.py:179）
   - 変更後: `self._save_undo("crop", page_i=self.current_page)` ← cropbox 取得前に呼ぶ（現行と同じ位置）

5. `_do_insert(ordered_paths, insert_at)` — **後払い更新あり**
   - 現行: `self._save_undo()` → `total = 0` → ループで挿入
   - 変更後: `self._save_undo("insert", insert_at=insert_at)` → ループで挿入 → `self._undo_stack[-1]["data"][1] = total` ← ループ完了後に num_inserted を書き込む
   - `_save_undo` が `state["data"] = [insert_at, 0]` のミュータブルリストで保存するため、スタックの末尾エントリを直接書き換える

6. `_do_merge(ordered_paths)` — ページ数は _save_undo 内で取得
   - 現行: `self._save_undo()`
   - 変更後: `self._save_undo("merge")` ← _save_undo 内で `len(self.doc)` を取得する設計のため kwargs 不要

**制約:**
- `_do_insert` の post-update は try ブロック内のループ完了後かつ _refresh_all() 前に行うこと
- `_rotate_selected` の targets 取得順序変更を必ず行うこと（これを忘れると「変更前の rotation」ではなく「変更後の rotation」が保存される）

## Inputs

- `pagefolio/file_ops.py`
- `pagefolio/page_ops.py`

## Expected Output

- `pagefolio/page_ops.py`

## Verification

python -c "import ast; ast.parse(open('pagefolio/page_ops.py', encoding='utf-8').read()); print('OK')"
