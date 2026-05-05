# S03: Undo 差分化 — UAT

**Milestone:** M001
**Written:** 2026-05-04T04:51:41.553Z

# S03: Undo 差分化 — UAT

**Milestone:** M001
**Written:** 2026-05-04

## UAT Type

- UAT mode: artifact-driven（pytest によるロジック直接検証）
- Why this mode is sufficient: 差分フォーマットの正しさ（保存・復元の対称性）は pytest で fitz API を直接呼び出して検証可能。GUI 上のメモリ削減効果は体感確認のため UAT フェーズに委ねる。

## Preconditions

- Python 環境に pymupdf（fitz）と pytest がインストールされていること
- `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/dnd.py`, `tests/test_pdf_ops.py` が S03 の変更済み状態であること

## Smoke Test

```bash
pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short
```
3 テスト全パスを確認する。

## Test Cases

### 1. rotate 差分のラウンドトリップ検証

1. `test_rotate_delta_roundtrip` を実行
2. 2 ページ PDF を作成し、`_save_undo("rotate", targets=[(0, 0)])` を呼び出す
3. スタックに `{"op": "rotate", "data": [(0, 0)]}` が保存されることを確認
4. `set_rotation(old_rot)` で回転前の値に戻せることを確認
5. **Expected:** テスト PASSED

### 2. delete 差分のラウンドトリップ検証

1. `test_delete_delta_roundtrip` を実行
2. 3 ページ PDF を作成し、ページ 1 を削除する差分を保存
3. 保存されたバイト列から `fitz.open(stream=...)` + `insert_pdf(start_at=1)` で再挿入
4. 元のページ数（3）とテキスト内容が復元されることを確認
5. **Expected:** テスト PASSED

### 3. pdf_bytes フォーマットのフォールバック検証

1. `test_fallback_pdf_bytes_format` を実行
2. `{"pdf_bytes": doc.tobytes(), ...}` 形式の辞書を作成
3. `fitz.open(stream=state["pdf_bytes"])` で復元できることを確認
4. **Expected:** テスト PASSED

### 4. 全テストスイート リグレッション確認

1. `pytest --tb=short -q` を実行
2. **Expected:** 109 passed、0 failed、0 error

### 5. リント・フォーマット確認

1. `ruff check . && ruff format --check .` を実行
2. **Expected:** All checks passed、20 files already formatted

## Edge Cases

### Redo スタックの後方互換

1. Undo 操作を実行し、_redo_stack に全体バイト方式エントリが積まれることを確認
2. Redo 操作で `_restore_state()` に `pdf_bytes` キーありの辞書が渡されることを確認
3. **Expected:** `"pdf_bytes"` キーの有無で自動判別し、全体バイト方式で正しく復元される

### insert の後払い書き込み

1. `_do_insert()` 実行中に `_save_undo("insert", insert_at=0)` が `[0, 0]` のミュータブルリストで保存されること
2. ループ完了後に `_undo_stack[-1]["data"][1]` が挿入ページ数に更新されること
3. **Expected:** Undo 時に正確な枚数分 `delete_page()` が実行される

## Failure Signals

- pytest で 109 件未満の PASSED、または FAILED/ERROR が存在する場合は実装バグ
- ruff check でエラーが出た場合はリント違反
- `_restore_state()` 内で KeyError や TypeError が発生した場合はフォーマット判別ロジックの不備

## Not Proven By This UAT

- 実際の大規模 PDF（数百ページ）でのメモリ使用量削減効果（体感・プロファイラ計測が必要）
- GUI 操作経由での Undo/Redo の動作（Tkinter イベントループとの統合）
- merge op の Undo（複数ファイル結合後の逆操作）の実際の動作確認
- 暗号化 PDF での動作

## Notes for Tester

- 差分方式の Undo スタックと全体バイト方式の Redo スタックが混在するため、Undo → Redo の連続操作が正しく動作するか GUI 手動確認を推奨
- rotate op の targets 取得タイミング（_save_undo 前）が重要。回転後に取得すると Undo が壊れる（MEM013）
