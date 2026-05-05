---
estimated_steps: 36
estimated_files: 1
skills_used: []
---

# T03: dnd.py の _dnd_drop() に一括移動ルートを追加しゴーストに N ページ表示を追加する

dnd.py の `_dnd_drop()` と `_dnd_start_ghost()` を変更して複数ページ選択時の一括移動を実装する。

**`_dnd_drop()` の変更:**
`src = self._dnd_src_idx` と `dest` 確定後、既存の `n = len(self.doc)` / `dest = max(...)` 処理の後、以下の複数選択分岐を追加し、条件を満たす場合は `return` で既存の単ページルートをスキップする:
```python
if src in self.selected_pages and len(self.selected_pages) > 1:
    sorted_sel = sorted(self.selected_pages)
    non_selected = [p for p in range(n) if p not in self.selected_pages]
    sel_before_dest = sum(1 for p in self.selected_pages if p < dest)
    adj_dest = dest - sel_before_dest
    adj_dest = max(0, min(adj_dest, len(non_selected)))
    new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
    if len(new_order) != n:
        return  # 安全確認: permutation でなければ中断
    self.doc.select(new_order)
    self._save_undo("bulk_move", new_order=new_order)
    self.current_page = new_order.index(src)
    self.selected_pages.clear()
    self._invalidate_thumb_cache()
    self._refresh_all()
    self._set_status(self._t("status_bulk_moved").format(count=len(sorted_sel)))
    return
```

注意:
- `self.doc.select(new_order)` の後に `_save_undo()` を呼ぶ（S03 パターン: doc 変更後に保存）
- `new_order` が `range(n)` と同一（移動なし）でも `doc.select()` + Undo エントリが入るが、副作用は軽微（許容）
- 既存の `if dest == src or dest == src + 1: return` は単ページルートのものなので複数選択ルートには不要

**`_dnd_start_ghost()` の変更:**
`num` ラベルのテキスト生成を条件分岐:
```python
if idx in self.selected_pages and len(self.selected_pages) > 1:
    label_text = f"{len(self.selected_pages)} pages"
else:
    label_text = f"p.{idx + 1}"
```
既存の `text=f"p.{idx + 1}"` を上記 `label_text` に差し替える。

**T01 前提:** `_save_undo("bulk_move", new_order=...)` は T01 で追加した分岐が必要。T01 完了後に実施すること。

## Inputs

- `pagefolio/dnd.py`
- `pagefolio/file_ops.py`
- `pagefolio/constants.py`

## Expected Output

- `pagefolio/dnd.py`

## Verification

grep -c "bulk_move\|sorted_sel\|non_selected" pagefolio/dnd.py
