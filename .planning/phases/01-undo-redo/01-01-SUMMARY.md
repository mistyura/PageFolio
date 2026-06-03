---
phase: "01-undo-redo"
plan: "01"
subsystem: "Undo/Redo"
tags: [bug-fix, refactoring, performance, BUG-01, BUG-02]
dependency_graph:
  requires: []
  provides: [symmetric-delta-undo-redo, insert-undo-fix, merge-resize-delta]
  affects: [pagefolio/file_ops.py, pagefolio/page_ops.py]
tech_stack:
  added: []
  patterns: [symmetric-delta, inverse-operation, page-bytes-capture]
key_files:
  created: []
  modified:
    - pagefolio/file_ops.py
    - pagefolio/page_ops.py
    - tests/test_pdf_ops.py
    - pagefolio/constants.py
    - 開発履歴.md
    - README.md
decisions:
  - "D-01: _undo/_redo は doc.tobytes() を呼ばず _restore_state の逆デルタを相互スタックに push する対称設計を採用"
  - "D-04: insert/merge は巻き戻し直前に削除ページ bytes をキャプチャして redo 用デルタに格納"
  - "D-05: _restore_state の pdf_bytes 分岐を完全撤廃"
metrics:
  duration: "約 35 分"
  completed_date: "2026-06-03"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 6
---

# Phase 1 Plan 1: Undo/Redo 対称デルタ化 Summary

**One-liner:** `doc.tobytes()` 全体シリアライズを撤廃し全 op を op 別逆デルタで往復させる対称 Undo/Redo 設計への全面刷新（BUG-01 挿入 Undo 修正・BUG-02 フリーズ解消）

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| TDD RED (Task 1) | _restore_state 対称デルタ化の失敗テスト追加 | 9699e48 | tests/test_pdf_ops.py |
| Task 1 GREEN | _restore_state を逆デルタ返却型へ対称化し pdf_bytes 分岐を撤廃 | 2adb8f8 | pagefolio/file_ops.py, tests/test_pdf_ops.py |
| TDD RED (Task 2) | insert/merge/merge_resize undo-redo ラウンドトリップ RED テスト追加 | 931e4cf | tests/test_pdf_ops.py |
| Task 2 GREEN | insert/merge bytes キャプチャ完全実装と merge_resize の op 別デルタ化 | 1435a2c | pagefolio/file_ops.py, pagefolio/page_ops.py |
| Task 3 | バージョン更新・開発履歴追記・lint 修正 | 03b4462 | pagefolio/constants.py, 開発履歴.md, README.md, tests/test_pdf_ops.py |

## What Was Built

### pagefolio/file_ops.py

- **`_apply_inverse(state)`** 新規追加: 逆操作適用前に現在の doc 状態から op 別逆デルタを構築して返すヘルパー。全 op（rotate/crop/delete/move/duplicate/bulk_move/bulk_crop/insert/merge/merge_resize）に対応。
- **`_undo()`/`_redo()` 対称化**: `doc.tobytes()` を完全撤廃。`_restore_state()` の返す逆デルタを相互スタックに push する設計へ変更。
- **`_restore_state(state)` 対称化**: `pdf_bytes` 分岐を撤廃（D-05）。op 別逆操作を適用し逆デルタ dict を return する設計へ変更。`insert_undo`/`merge_undo`/`merge_resize`/`merge_resize_undo` を新規追加。
- **`_save_undo()` に `merge_resize` op 追加**: `data={insert_at, merged_bytes, orig_pages}` 形式の op 別デルタを保存。

### pagefolio/page_ops.py

- **`_do_merge_resize()` リファクタ**: `self._undo_stack.append({"pdf_bytes": self.doc.tobytes(), ...})` と手動 `pop(0)` トリムを撤廃。結合前に元ページ bytes・結合ページ bytes をキャプチャし `_save_undo("merge_resize", ...)` 経由の op 別デルタへ置換（D-05）。

### tests/test_pdf_ops.py

- `TestUndoRedoLogic`: `test_restore_state_no_pdf_bytes_key`・`test_restore_state_returns_inverse_delta` 追加（pdf_bytes 撤廃・逆デルタ返却を検証）
- `TestInsertMergeUndoRedo` クラス追加:
  - `test_insert_undo_removes_inserted_pages`: BUG-01 修正確認（insert→undo でページ数が元に戻る）
  - `test_insert_undo_redo_roundtrip`: insert→undo→redo でページ内容が復元される
  - `test_merge_resize_no_pdf_bytes_in_undo_stack`: merge_resize の pdf_bytes 撤廃確認

## Key Design Decisions

1. **対称デルタ方式（D-01/D-04/D-05）**: 順方向も巻き戻しも同じ `_save_undo` 互換スキーマ（`op`/`current_page`/`selected_pages`/`data`）を使い、`pdf_bytes` を一切持たない設計。
2. **insert/merge の逆デルタ**: `_apply_inverse` 内でページ削除直前に `tmp.tobytes()` でページ単位 bytes をキャプチャし `insert_undo`/`merge_undo` 形式のデルタに変換。
3. **merge_resize のデルタ**: 操作前に元ページ bytes + 操作後に結合ページ bytes をキャプチャ。`merge_resize_undo` で結合ページ削除・元ページ再挿入、`merge_resize` で逆操作を実現。
4. **不採用（D-02/D-03 遵守）**: 背景スレッドでの `tobytes()`・順方向全再適用方式のコードは一切追加していない。

## Deviations from Plan

### 計画通りに実行

本プランは計画通りに実行されました。Task 1 の仮実装で insert/merge の bytes キャプチャも先行実装したため、Task 2 では `_apply_inverse` の `insert`/`merge` 分岐（仮実装済み）と `merge_resize` の完全実装に集中できました。

### 自動修正（Rule 2）

なし。

### 軽微な設計上の裁量

- `duplicate` op の逆操作: `duplicate` → `duplicate_undo`（複製ページ削除）→ `duplicate`（再複製）の 3 段対称設計を採用。プランでは `duplicate` の対称化については明示されていなかったが、全 op 対称化方針（D-04）に従い実装。
- `insert_redo` op: undo した insert を再実行する際の op 名として `insert_redo` を定義。これは `insert_undo` と対称で、bytes から再挿入する処理を行う。

## Verification

- `python -m pytest tests/ -q`: **149 passed** (既存 145 件 + 新規 4 件)
- `ruff check .`: **All checks passed!**
- `ruff format --check .`: **23 files already formatted**
- `pagefolio/file_ops.py` / `pagefolio/page_ops.py` に `self.doc.tobytes()` なし（全体シリアライズ 0 件）
- `_undo`/`_redo`/`_restore_state`/`_do_merge_resize` いずれもドキュメント全体 `doc.tobytes()` を Undo/Redo 用途で呼ばない
- `APP_VERSION`: `v1.2.3`

## Known Stubs

なし。

## Threat Flags

本プランで新規追加したネットワークエンドポイント・auth パス・PII 取り扱いはなし。
`merge_resize` の `merged_bytes`/`orig_pages` はプロセス内メモリに閉じる（T-01-01 の accept 判断通り）。

## Self-Check: PASSED

- [x] `pagefolio/file_ops.py` 存在確認: FOUND
- [x] `pagefolio/page_ops.py` 存在確認: FOUND
- [x] `tests/test_pdf_ops.py` 存在確認: FOUND
- [x] コミット 9699e48 存在確認: FOUND
- [x] コミット 2adb8f8 存在確認: FOUND
- [x] コミット 931e4cf 存在確認: FOUND
- [x] コミット 1435a2c 存在確認: FOUND
- [x] コミット 03b4462 存在確認: FOUND
