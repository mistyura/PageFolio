---
estimated_steps: 51
estimated_files: 1
skills_used: []
---

# T02: file_ops.py の _restore_state() を差分/全体バイト両対応ディスパッチャに書き換え

T01 で新シグネチャになった `_save_undo()` が生成する差分フォーマット（`"op"` キー付き）と、`_undo()` / `_redo()` が Redo スタックに積む旧フォーマット（`"pdf_bytes"` キー付き）の両方を処理できるよう `_restore_state()` をディスパッチャに書き換える。

**新 _restore_state() ロジック:**
```python
def _restore_state(self, state):
    if "pdf_bytes" in state:
        # 旧来形式（Redo スタック由来）またはフォールバック
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(stream=state["pdf_bytes"], filetype="pdf")
    else:
        op = state["op"]
        if op == "rotate":
            for page_i, old_rot in state["data"]:
                self.doc[page_i].set_rotation(old_rot)
        elif op == "crop":
            page_i, (x0, y0, x1, y1) = state["data"]
            self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        elif op == "delete":
            # 昇順で再挿入（インデックスずれ防止）
            for page_i, page_bytes in state["data"]:
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "move":
            src, actual_dest = state["data"]
            self.doc.move_page(actual_dest, src)
        elif op == "duplicate":
            self.doc.delete_page(state["data"] + 1)
        elif op == "insert":
            insert_at, num = state["data"]
            for _ in range(num):
                self.doc.delete_page(insert_at)
        elif op == "merge":
            old_count = state["data"]
            while len(self.doc) > old_count:
                self.doc.delete_page(old_count)

    self.current_page = min(state["current_page"], max(0, len(self.doc) - 1))
    self.selected_pages = state["selected_pages"]
    self._invalidate_thumb_cache()
    self._preview_gen += 1
    self._thumb_gen += 1
    self._refresh_all()
```

**`_undo()` / `_redo()` の変更点:**
- `_undo()`: Redo スタックへのプッシュは変更なし（引き続き `{"pdf_bytes": self.doc.tobytes(), ...}` の全体バイト形式）。`_restore_state()` 呼び出しはそのまま
- `_redo()`: Undo スタックへのプッシュも変更なし（全体バイト形式でプッシュ → `_restore_state()` が `pdf_bytes` キーを検出して従来処理）。`_restore_state()` 呼び出しはそのまま

**重要な制約:**
- `move` の逆操作は `doc.move_page(actual_dest, src)` で元位置に戻す（PyMuPDF の `move_page(from_, to_)` の仕様通り）
- `delete` undo の再挿入は state["data"] が昇順ソート済みのため、そのまま昇順 insert_pdf する
- `_invalidate_thumb_cache()` の直後に `_preview_gen += 1` と `_thumb_gen += 1` をインクリメントする順序は S02 で確立した規約通り（順序変更禁止）
- T01 の `_save_undo()` が `pagefolio/file_ops.py` に実装済みであることを前提にする

## Inputs

- `pagefolio/file_ops.py`

## Expected Output

- `pagefolio/file_ops.py`

## Verification

python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"
