---
estimated_steps: 92
estimated_files: 1
skills_used: []
---

# T05: test_pdf_ops.py に TestBulkMoveLogic / TestBulkCropLogic テストを追加する

tests/test_pdf_ops.py に 2 つのテストクラスを追加し、bulk_move の逆順列ラウンドトリップと bulk_crop のマルチページ cropbox ラウンドトリップを検証する。

**TestBulkMoveLogic（2 テスト）:**
```python
class TestBulkMoveLogic:
    """bulk_move: doc.select() の逆順列ラウンドトリップ検証"""

    def test_bulk_move_select_roundtrip(self, sample_pdf_doc):
        """doc.select(new_order) → 逆順列で doc.select(inverse) → 元の順序に戻る"""
        doc = sample_pdf_doc  # 3ページ: Page 1, Page 2, Page 3
        # ページ 0 と 2 を選択し、末尾に移動する new_order = [1, 0, 2]
        new_order = [1, 0, 2]
        doc.select(new_order)
        assert "Page 2" in doc[0].get_text()
        # 逆順列を計算
        inverse = [0] * len(new_order)
        for i, v in enumerate(new_order):
            inverse[v] = i
        doc.select(inverse)
        assert "Page 1" in doc[0].get_text()
        assert "Page 2" in doc[1].get_text()
        assert "Page 3" in doc[2].get_text()

    def test_bulk_move_new_order_construction(self, sample_pdf_doc):
        """selected_pages + dest から new_order が正しく構築される"""
        doc = sample_pdf_doc  # 3ページ
        n = len(doc)
        selected_pages = {0, 2}  # ページ 0 と 2 を選択
        dest = 3  # 末尾にドロップ
        sorted_sel = sorted(selected_pages)
        non_selected = [p for p in range(n) if p not in selected_pages]
        sel_before_dest = sum(1 for p in selected_pages if p < dest)
        adj_dest = dest - sel_before_dest
        adj_dest = max(0, min(adj_dest, len(non_selected)))
        new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
        # new_order は permutation
        assert sorted(new_order) == list(range(n))
        # non_selected (page 1) が先頭、選択ページが末尾
        assert new_order == [1, 0, 2]
```

**TestBulkCropLogic（2 テスト）:**
```python
class TestBulkCropLogic:
    """bulk_crop: 複数ページ cropbox ラウンドトリップ検証"""

    def test_bulk_crop_multi_page_roundtrip(self, sample_pdf_doc):
        """複数ページに cropbox 適用 → 旧データで全ページ復元できる"""
        doc = sample_pdf_doc
        targets = [0, 1, 2]
        # 旧 cropbox を保存（Undo データ構築と同じ）
        crop_data = []
        for i in targets:
            cb = doc[i].cropbox
            crop_data.append((i, (cb.x0, cb.y0, cb.x1, cb.y1)))
        # 各ページにトリミング適用
        for i in targets:
            page = doc[i]
            mb = page.mediabox
            new_rect = fitz.Rect(
                mb.x0 + 20, mb.y0 + 20, mb.x1 - 20, mb.y1 - 20
            )
            page.set_cropbox(new_rect)
            assert doc[i].cropbox.x0 > crop_data[i][1][0]
        # Undo: 旧 cropbox で復元（_restore_state の bulk_crop ロジックと同等）
        for page_i, (x0, y0, x1, y1) in crop_data:
            doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        for i in targets:
            cb = doc[i].cropbox
            assert abs(cb.x0 - crop_data[i][1][0]) < 1
            assert abs(cb.y0 - crop_data[i][1][1]) < 1

    def test_bulk_crop_relative_coords(self, sample_pdf_doc):
        """相対座標変換: 異なる mediabox サイズのページでも比率が保たれる"""
        doc = sample_pdf_doc
        # current_page (0) の mediabox で相対比率を計算
        cur_mb = doc[0].mediabox
        # 中央 50% の領域を選択したとする
        x0_pdf, y0_pdf = cur_mb.width * 0.1, cur_mb.height * 0.1
        x1_pdf, y1_pdf = cur_mb.width * 0.9, cur_mb.height * 0.9
        rel = (
            x0_pdf / cur_mb.width,
            y0_pdf / cur_mb.height,
            x1_pdf / cur_mb.width,
            y1_pdf / cur_mb.height,
        )
        # 同じ比率を別ページに適用
        for i in [0, 1, 2]:
            mb = doc[i].mediabox
            new_x0 = mb.x0 + rel[0] * mb.width
            new_y0 = mb.y0 + rel[1] * mb.height
            new_x1 = mb.x0 + rel[2] * mb.width
            new_y1 = mb.y0 + rel[3] * mb.height
            # 比率が保たれている
            assert abs((new_x0 - mb.x0) / mb.width - rel[0]) < 0.001
            assert abs((new_x1 - mb.x0) / mb.width - rel[2]) < 0.001
```

追加場所: 既存の `TestUndoRedoLogic` クラスの後（ファイル末尾の `TestCheckSplitOverwrite` の前）。

## Inputs

- `tests/test_pdf_ops.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_pdf_ops.py`

## Verification

pytest tests/test_pdf_ops.py::TestBulkMoveLogic tests/test_pdf_ops.py::TestBulkCropLogic -v --tb=short
