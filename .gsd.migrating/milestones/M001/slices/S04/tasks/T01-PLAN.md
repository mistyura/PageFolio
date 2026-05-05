---
estimated_steps: 24
estimated_files: 1
skills_used: []
---

# T01: file_ops.py に bulk_move / bulk_crop の Undo 差分サポートを追加する

S03 で確立した Undo 差分パターンを拡張し、`_save_undo()` に `bulk_move` / `bulk_crop` 分岐を追加し、`_restore_state()` に対応する逆変換を追加する。このタスクは T03 (dnd.py) と T04 (page_ops.py) のブロッカー。

`_save_undo()` に追加する分岐（既存の `elif op == "merge":` の後）:
```python
elif op == "bulk_move":
    state["data"] = kwargs["new_order"]  # 整数リスト
elif op == "bulk_crop":
    state["data"] = kwargs["crop_data"]  # [(page_i, (x0,y0,x1,y1)), ...]
```

`_restore_state()` に追加する分岐（既存の `elif op == "merge":` ブロックの後）:
```python
elif op == "bulk_move":
    new_order = state["data"]
    inverse = [0] * len(new_order)
    for i, v in enumerate(new_order):
        inverse[v] = i
    self.doc.select(inverse)
elif op == "bulk_crop":
    for page_i, (x0, y0, x1, y1) in state["data"]:
        self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
```

注意点:
- `bulk_move` の逆変換は `inverse[new_order[i]] = i` で構築する順列の逆順列。`doc.select(inverse)` で元のページ順に戻す。
- `bulk_crop` の cropbox はタプル `(x0, y0, x1, y1)` 形式で保存し、復元時に `fitz.Rect()` で再構築（S03 の crop op と同じパターン）。
- `doc.select()` 後は既存ページ参照が無効になるため、restore 後のページ参照は `_refresh_all()` 経由で再取得される（既存の共通後処理で対応済み）。

## Inputs

- `pagefolio/file_ops.py`

## Expected Output

- `pagefolio/file_ops.py`

## Verification

grep -c "bulk_move\|bulk_crop" pagefolio/file_ops.py
