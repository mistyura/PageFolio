---
id: T03
parent: S03
milestone: M001
key_files:
  - pagefolio/page_ops.py
key_decisions:
  - _do_insert の後払い更新は _undo_stack[-1]["data"][1] = total で直接書き込む（_save_undo がミュータブルリストで保存するため）
  - _rotate_selected では targets の取得順序を _save_undo 呼び出し前に移動し、回転前の rotation 値を正しく保存する
duration: 
verification_result: passed
completed_at: 2026-05-04T04:45:17.056Z
blocker_discovered: false
---

# T03: page_ops.py の _save_undo() 呼び出し6箇所を新シグネチャ (op, **kwargs) に更新

**page_ops.py の _save_undo() 呼び出し6箇所を新シグネチャ (op, **kwargs) に更新**

## What Happened

T01/T02 で変更された `_save_undo(op, **kwargs)` 差分形式シグネチャに合わせ、`page_ops.py` 内の6箇所の `self._save_undo()` 呼び出しを更新した。

変更内容:
1. `_rotate_selected(deg)` — `targets = self._get_targets()` の取得順序を `_save_undo()` 呼び出しの前に移動し、`self._save_undo("rotate", targets=targets)` に変更。これにより回転前の rotation 値が正しく保存される。
2. `_delete_selected()` — targets はすでに `sorted(self._get_targets(), reverse=True)` で確定済みのため、`self._save_undo("delete", targets=targets)` に変更。
3. `_duplicate_page()` — `self._save_undo("duplicate", pno=pno)` に変更。pno 確定後の位置を維持。
4. `_crop_page()` — `self._save_undo("crop", page_i=self.current_page)` に変更。cropbox 取得前の位置を維持。
5. `_do_insert()` — `self._save_undo("insert", insert_at=insert_at)` に変更し、ループ完了後に `self._undo_stack[-1]["data"][1] = total` で num_inserted を後払い書き込み。`_save_undo` 内では `state["data"] = [insert_at, 0]` のミュータブルリストで保存されるため、末尾エントリへの直接書き込みが機能する。
6. `_do_merge()` — `self._save_undo("merge")` に変更。ページ数は `_save_undo` 内で `len(self.doc)` から取得するため kwargs 不要。

構文チェック・リント・全テスト (108件) すべて通過。

## Verification

python -c "import ast; ast.parse(open('pagefolio/page_ops.py', encoding='utf-8').read()); print('OK')" → OK
ruff check . && ruff format . → All checks passed! 20 files left unchanged
pytest → 108 passed in 1.41s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "import ast; ast.parse(open('pagefolio/page_ops.py', encoding='utf-8').read()); print('OK')"` | 0 | ✅ pass | 200ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass | 3000ms |
| 3 | `pytest` | 0 | ✅ pass | 1410ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pagefolio/page_ops.py`
