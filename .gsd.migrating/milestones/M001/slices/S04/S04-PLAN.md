# S04: 複数ページ操作と保守

**Goal:** 複数選択ページを D&D で一括移動し、一括トリミングも選択ページ全体に相対座標変換で適用できるようにする。Undo/Redo は S03 の差分パターンに完全準拠する。
**Demo:** 複数ページを選択して D&D で一括移動、および一括トリミングが動作する

## Must-Haves

- 2 ページ以上を選択してドラッグすると selected_pages 全体が doc.select(new_order) で一括移動し、Ctrl+Z で逆順列 select によって元の順序に戻る
- 2 ページ以上を選択してトリミングを実行すると全選択ページに相対座標変換後の cropbox が設定され、Ctrl+Z で全ページの旧 cropbox が復元される
- pytest tests/test_pdf_ops.py 全件 PASSED（新規 TestBulkMoveLogic / TestBulkCropLogic を含む）
- ruff check . && ruff format --check . でリントクリーン

## Proof Level

- This slice proves: - This slice proves: contract（fitz API + pytest でロジック保証。GUI の視覚確認は手動 UAT 必要）
- Real runtime required: no
- Human/UAT required: yes（複数選択 D&D の挙動、ゴースト N ページ表示、確認ダイアログは GUI で手動確認）

## Integration Closure

- Upstream surfaces consumed: `pagefolio/file_ops.py`（_save_undo/_restore_state）, `pagefolio/dnd.py`（_dnd_drop）, `pagefolio/page_ops.py`（_crop_page）, `pagefolio/constants.py`（LANG）
- New wiring: dnd.py の bulk_move 分岐 → file_ops.py の _restore_state で逆順列 select; page_ops.py の bulk_crop 分岐 → file_ops.py の _restore_state で cropbox 復元
- What remains: GUI 手動確認（複数選択 D&D・一括トリミング・Undo 確認）

## Verification

- Run the task and slice verification checks for this slice.

## Tasks

- [x] **T01: file_ops.py に bulk_move / bulk_crop の Undo 差分サポートを追加する** `est:30m`
  S03 で確立した Undo 差分パターンを拡張し、`_save_undo()` に `bulk_move` / `bulk_crop` 分岐を追加し、`_restore_state()` に対応する逆変換を追加する。このタスクは T03 (dnd.py) と T04 (page_ops.py) のブロッカー。
  - Files: `pagefolio/file_ops.py`
  - Verify: grep -c "bulk_move\|bulk_crop" pagefolio/file_ops.py

- [x] **T02: constants.py の LANG 辞書に bulk_move / bulk_crop 用ステータスキーを追加する** `est:15m`
  T03 (dnd.py) と T04 (page_ops.py) が参照する LANG キーを ja/en 両方に追加する。
  - Files: `pagefolio/constants.py`
  - Verify: grep -c "status_bulk_moved\|status_bulk_cropped\|confirm_bulk_crop" pagefolio/constants.py

- [x] **T03: dnd.py の _dnd_drop() に一括移動ルートを追加しゴーストに N ページ表示を追加する** `est:45m`
  dnd.py の `_dnd_drop()` と `_dnd_start_ghost()` を変更して複数ページ選択時の一括移動を実装する。
  - Files: `pagefolio/dnd.py`
  - Verify: grep -c "bulk_move\|sorted_sel\|non_selected" pagefolio/dnd.py

- [x] **T04: page_ops.py の _crop_page() に複数ページ一括トリミング対応を追加する** `est:45m`
  page_ops.py の `_crop_page()` を変更し、複数ページ選択時に相対座標変換 + bulk_crop op で一括トリミングを適用する。単ページ選択時は既存コードパスを維持する。
  - Files: `pagefolio/page_ops.py`
  - Verify: grep -c "bulk_crop\|confirm_bulk_crop\|_get_targets" pagefolio/page_ops.py

- [ ] **T05: test_pdf_ops.py に TestBulkMoveLogic / TestBulkCropLogic テストを追加する** `est:45m`
  tests/test_pdf_ops.py に 2 つのテストクラスを追加し、bulk_move の逆順列ラウンドトリップと bulk_crop のマルチページ cropbox ラウンドトリップを検証する。
  - Files: `tests/test_pdf_ops.py`
  - Verify: pytest tests/test_pdf_ops.py::TestBulkMoveLogic tests/test_pdf_ops.py::TestBulkCropLogic -v --tb=short

- [ ] **T06: ruff リントと pytest 全件確認を行い残存する問題を修正する** `est:15m`
  T01〜T05 で変更したすべてのファイルに対して ruff リント・フォーマットチェックと pytest 全件実行を行い、問題があれば修正する。
  - Files: `pagefolio/file_ops.py`, `pagefolio/dnd.py`, `pagefolio/page_ops.py`, `pagefolio/constants.py`, `tests/test_pdf_ops.py`
  - Verify: ruff check . && ruff format --check . && pytest --tb=short -q

## Files Likely Touched

- pagefolio/file_ops.py
- pagefolio/constants.py
- pagefolio/dnd.py
- pagefolio/page_ops.py
- tests/test_pdf_ops.py
