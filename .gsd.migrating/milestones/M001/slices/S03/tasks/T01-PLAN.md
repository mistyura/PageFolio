---
estimated_steps: 34
estimated_files: 1
skills_used: []
---

# T01: file_ops.py の _save_undo() を差分形式シグネチャに書き換え

現行の `_save_undo(self)` は常に `self.doc.tobytes()` で全体バイトを保存する。これを `_save_undo(self, op, **kwargs)` に書き換え、操作タイプ別に最小データのみを保存するよう変更する。

**新しい差分フォーマット定義:**
```python
# rotate: targets リストに含まれる各ページの現在の rotation を保存
{"op": "rotate", "data": [(page_i, old_rotation), ...], "current_page": int, "selected_pages": set}

# crop: 現在のページの cropbox を (x0,y0,x1,y1) タプルで保存
{"op": "crop", "data": (page_i, (x0, y0, x1, y1)), "current_page": int, "selected_pages": set}

# delete: 削除対象ページを昇順で 1ページずつ tobytes() して保存
{"op": "delete", "data": [(page_i, single_page_bytes), ...], "current_page": int, "selected_pages": set}

# move: src と actual_dest（実際の移動先インデックス）を保存
{"op": "move", "data": (src, actual_dest), "current_page": int, "selected_pages": set}

# duplicate: 複製元のページ番号 pno を保存（undo は pno+1 を削除）
{"op": "duplicate", "data": pno, "current_page": int, "selected_pages": set}

# insert: ミュータブルリスト [insert_at, 0] を保存（呼び出し側がループ後に [1] を更新）
{"op": "insert", "data": [insert_at, 0], "current_page": int, "selected_pages": set}

# merge: 現在のページ数（結合前）を保存
{"op": "merge", "data": len(self.doc), "current_page": int, "selected_pages": set}
```

**実装手順:**
1. `_save_undo(self, op, **kwargs)` にシグネチャを変更
2. `state = {"op": op, "current_page": self.current_page, "selected_pages": set(self.selected_pages)}` を共通ベースにする
3. op の値に応じて if/elif で state["data"] を構築する
   - `"rotate"`: `state["data"] = [(i, self.doc[i].rotation) for i in kwargs["targets"]]`
   - `"crop"`: `page_i = kwargs["page_i"]; cb = self.doc[page_i].cropbox; state["data"] = (page_i, (cb.x0, cb.y0, cb.x1, cb.y1))` ← fitz.Rect はタプルとして保存
   - `"delete"`: `targets = sorted(kwargs["targets"])` で昇順ソート後、各ページを `fitz.open()` で抽出して `tmp.tobytes()` を保存、tmp は close する
   - `"move"`: `state["data"] = (kwargs["src"], kwargs["actual_dest"])`
   - `"duplicate"`: `state["data"] = kwargs["pno"]`
   - `"insert"`: `state["data"] = [kwargs["insert_at"], 0]` （ミュータブルリスト）
   - `"merge"`: `state["data"] = len(self.doc)`
4. `self._undo_stack.append(state)` と上限チェック・`_redo_stack.clear()` はそのまま維持

**制約:**
- `delete` op での単ページ抽出は `fitz.open()` + `insert_pdf(from_page=i, to_page=i)` + `tobytes()` の後 `close()` を必ず呼ぶ
- `fitz.Rect` オブジェクトは Python タプルとして保存（C 側寿命管理のため直接保持しない）
- `fitz` は既に import 済みのため追加不要

## Inputs

- `pagefolio/file_ops.py`

## Expected Output

- `pagefolio/file_ops.py`

## Verification

python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"
