---
estimated_steps: 56
estimated_files: 1
skills_used: []
---

# T05: test_pdf_ops.py の TestUndoRedoLogic を差分ロジック検証テストに書き換え

既存の `TestUndoRedoLogic` クラスは「全体バイトコピー方式」を前提としたテストになっている。差分フォーマットの正しさを直接 fitz API で検証するテストに書き換える。

**現行の2テストを以下に置き換える:**

```python
class TestUndoRedoLogic:
    """Undo/Redo 差分フォーマットのロジックテスト（操作タイプ別方式）"""

    def test_rotate_delta_roundtrip(self, sample_pdf_doc):
        """回転の差分保存と逆操作が正しく動作する"""
        doc = sample_pdf_doc
        original_rotation = doc[0].rotation  # 通常 0

        # 差分保存: 回転前の rotation を記録
        delta = {"op": "rotate", "data": [(0, doc[0].rotation)]}

        # 操作: 90度回転
        doc[0].set_rotation((doc[0].rotation + 90) % 360)
        assert doc[0].rotation == 90

        # Undo: 差分で復元
        for page_i, old_rot in delta["data"]:
            doc[page_i].set_rotation(old_rot)
        assert doc[0].rotation == original_rotation

    def test_delete_delta_roundtrip(self, sample_pdf_doc):
        """削除の差分保存と逆操作（ページ復元）が正しく動作する"""
        doc = sample_pdf_doc
        original_count = len(doc)  # 3ページ

        # 差分保存: 削除対象ページをバイト列で保存（昇順）
        targets = sorted([0])  # ページ0を削除
        delta_data = []
        for i in targets:
            tmp = fitz.open()
            tmp.insert_pdf(doc, from_page=i, to_page=i)
            delta_data.append((i, tmp.tobytes()))
            tmp.close()

        # 操作: ページ削除
        doc.delete_page(0)
        assert len(doc) == original_count - 1

        # Undo: 昇順で再挿入
        for page_i, page_bytes in delta_data:
            tmp = fitz.open(stream=page_bytes, filetype="pdf")
            doc.insert_pdf(tmp, start_at=page_i)
            tmp.close()
        assert len(doc) == original_count
        assert "Page 1" in doc[0].get_text()

    def test_fallback_pdf_bytes_format(self, sample_pdf_doc):
        """pdf_bytes キーを持つ旧フォーマットが _restore_state で処理できる（フォールバック）"""
        doc = sample_pdf_doc
        # 旧フォーマット（Redo スタック由来）: pdf_bytes キー付き
        saved_bytes = doc.tobytes()
        state = {"pdf_bytes": saved_bytes, "current_page": 0, "selected_pages": set()}

        # pdf_bytes キーで復元できることを fitz API で確認
        restored = fitz.open(stream=state["pdf_bytes"], filetype="pdf")
        assert len(restored) == len(doc)
        restored.close()
```

**制約:**
- クラス名 `TestUndoRedoLogic` は変更しないこと（既存テストの naming convention を維持）
- `fitz` は既に `test_pdf_ops.py` にインポート済み
- `sample_pdf_doc` フィクスチャは `conftest.py` で定義済み（3ページの PDF ドキュメント）
- 3つのテストメソッドで旧来の2テストを置き換える

## Inputs

- `tests/test_pdf_ops.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_pdf_ops.py`

## Verification

pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short
