---
id: T01
parent: S04
milestone: M001
key_files:
  - pagefolio/file_ops.py
key_decisions:
  - bulk_move の逆変換は inverse[new_order[i]]=i で構築した順列の逆順列を doc.select() に渡す方式を採用（S03 差分パターンに準拠）
  - bulk_crop は操作前 cropbox を (page_i, (x0,y0,x1,y1)) タプルで保存し、復元時に fitz.Rect() で再構築（S03 crop op と同じパターン）
duration: 
verification_result: passed
completed_at: 2026-05-04T05:01:41.899Z
blocker_discovered: false
---

# T01: file_ops.py の _save_undo() / _restore_state() に bulk_move・bulk_crop 分岐を追加し、複数ページ操作の Undo 差分サポートを実装した

**file_ops.py の _save_undo() / _restore_state() に bulk_move・bulk_crop 分岐を追加し、複数ページ操作の Undo 差分サポートを実装した**

## What Happened

S03 で確立した差分 Undo パターンを拡張した。`_save_undo()` の `merge` 分岐の直後に `bulk_move`（new_order 整数リスト保存）と `bulk_crop`（[(page_i, (x0,y0,x1,y1)), ...] 保存）を追加。`_restore_state()` にも対応する逆変換を追加し、`bulk_move` は順列の逆順列を構築して `doc.select(inverse)` で元ページ順に戻す、`bulk_crop` は各ページの cropbox を fitz.Rect で再構築する形で実装した。どちらも S03 の crop/rotate パターンと一貫した最小差分方式。

## Verification

grep -c でファイル内 bulk_move/bulk_crop 参照数が 4 であることを確認（_save_undo x2、_restore_state x2）。ruff check/format が全パス。pytest 109 件全通過。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "bulk_move\|bulk_crop" pagefolio/file_ops.py` | 0 | ✅ pass (4件) | 50ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass | 800ms |
| 3 | `python -m pytest tests/ -q` | 0 | ✅ pass (109 passed) | 1090ms |

## Deviations

none

## Known Issues

none

## Files Created/Modified

- `pagefolio/file_ops.py`
