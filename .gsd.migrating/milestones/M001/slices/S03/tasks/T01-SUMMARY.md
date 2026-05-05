---
id: T01
parent: S03
milestone: M001
key_files:
  - pagefolio/file_ops.py
key_decisions:
  - fitz.Rect は Python タプルとして保存（C 側オブジェクトの寿命管理のため直接保持しない）
  - delete op は昇順ソート後に単ページ fitz.open() + insert_pdf + tobytes() + close() で抽出
  - insert op は呼び出し側がループ後に [1] を更新できるようミュータブルリストとして保存
duration: 
verification_result: passed
completed_at: 2026-05-04T04:41:50.755Z
blocker_discovered: false
---

# T01: _save_undo() を差分形式シグネチャ (op, **kwargs) に書き換え、操作タイプ別の最小差分データを保存するよう変更

**_save_undo() を差分形式シグネチャ (op, **kwargs) に書き換え、操作タイプ別の最小差分データを保存するよう変更**

## What Happened

file_ops.py の `_save_undo(self)` を `_save_undo(self, op, **kwargs)` に書き換えた。共通ベースとして `{"op": op, "current_page": ..., "selected_pages": ...}` を構築し、op の値に応じて if/elif で `state["data"]` を設定する。各 op の実装：rotate は targets リストの各ページ rotation を保存、crop は fitz.Rect をタプル形式で保存（C 側寿命管理回避）、delete は昇順ソート後に各ページを fitz.open() で単ページ抽出し tobytes() → close()、move は (src, actual_dest)、duplicate は pno、insert は [insert_at, 0] のミュータブルリスト、merge は現在のページ数。スタック上限チェックと _redo_stack.clear() は既存ロジックを維持。`_restore_state` と呼び出し元（page_ops.py, dnd.py）の更新は後続タスクで行う。

## Verification

python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')" → exit 0, 出力 OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"` | 0 | ✅ pass | 200ms |

## Deviations

なし

## Known Issues

呼び出し元（page_ops.py, dnd.py）はまだ引数なし _save_undo() を呼んでおり、後続タスクで更新が必要

## Files Created/Modified

- `pagefolio/file_ops.py`
