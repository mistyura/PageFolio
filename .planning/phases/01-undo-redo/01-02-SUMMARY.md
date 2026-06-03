---
phase: "01-undo-redo"
plan: "02"
subsystem: "Undo/Redo"
tags: [refactoring, performance, REFAC-03, deque]
dependency_graph:
  requires: [01-01]
  provides: [deque-undo-redo-stack, O1-undo-trim]
  affects: [pagefolio/app.py, pagefolio/file_ops.py]
tech_stack:
  added: [collections.deque]
  patterns: [deque-maxlen, O1-append]
key_files:
  created: []
  modified:
    - pagefolio/app.py
    - pagefolio/file_ops.py
    - pagefolio/constants.py
    - 開発履歴.md
    - README.md
decisions:
  - "D-06: _undo_stack/_redo_stack の両方を deque(maxlen=MAX_UNDO) 化し、手動 pop(0) を削除"
metrics:
  duration: "約 10 分"
  completed_date: "2026-06-03"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 1 Plan 2: deque(maxlen=MAX_UNDO) 化 Summary

**One-liner:** `_undo_stack`/`_redo_stack` を `collections.deque(maxlen=MAX_UNDO)` に変更し `_save_undo` の手動 `list.pop(0)` O(n) トリムを撤廃して上限管理を O(1) に一本化（REFAC-03）

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | _undo/_redo_stack を deque(maxlen=MAX_UNDO) 化し手動トリムを削除 | c5ef5c0 | pagefolio/app.py, pagefolio/file_ops.py |
| 2 | lint・既存テスト確認と開発履歴・バージョン更新 | 7dd5244 | pagefolio/constants.py, 開発履歴.md, README.md |

## What Was Built

### pagefolio/app.py

- `from collections import deque` をトップレベル import に追加
- `__init__` 内の `self._undo_stack = []` / `self._redo_stack = []` を `deque(maxlen=self.MAX_UNDO)` へ置換（D-06）

### pagefolio/file_ops.py

- `_save_undo()` 末尾にあった手動トリム 2 行を削除:
  ```python
  # 削除前:
  if len(self._undo_stack) > self.MAX_UNDO:
      self._undo_stack.pop(0)
  ```
  deque の `maxlen` が自動で先頭要素を破棄するため不要になった

### pagefolio/page_ops.py（変更なし）

- `_do_insert` の `self._undo_stack[-1]["data"][1] = total`（line 344）が deque でも O(1) で成立することを確認（変更不要）
- `_do_merge_resize` の手動 `pop(0)` は 01-01 で既に撤廃済み（残存なし）

### pagefolio/constants.py

- `APP_VERSION`: `v1.2.3` → `v1.2.4`

### 開発履歴.md / README.md

- v1.2.4 エントリ追加（deque 化・技術詳細を記載）
- README.md バージョンバッジを v1.2.4 に同期

## Key Design Decisions

1. **D-06 準拠**: `_undo_stack`/`_redo_stack` の両方を `deque(maxlen=MAX_UNDO)` 化。redo スタックは通常 MAX_UNDO を超えないが、一貫性のために両方を deque にした
2. **deque[-1] の互換性**: `page_ops.py` の `_undo_stack[-1]` 末尾参照は deque でも O(1) で成立（Python の deque は両端アクセスが O(1)）
3. **`.append()`/`.pop()`/`.clear()` 互換**: これらのメソッドは deque と list で同一インターフェースのため、`_undo`/`_redo` への変更は不要

## Deviations from Plan

### 計画通りに実行

本プランは計画通りに実行されました。

`_do_merge_resize` の手動 `pop(0)` は 01-01 ですでに撤廃されており、残存確認の結果 `pagefolio/page_ops.py` に変更は不要でした（計画の「残存有無を確認」通り）。

## Verification

- `python -m pytest tests/ -q`: **149 passed**（既存テスト全通）
- `ruff check .`: **All checks passed!**
- `ruff format --check .`: **23 files already formatted**
- `grep "deque(maxlen=self.MAX_UNDO)" pagefolio/app.py`: 2 件ヒット（`_undo_stack`/`_redo_stack` 両方）
- `grep "pop(0)" pagefolio/file_ops.py pagefolio/page_ops.py pagefolio/app.py`: 0 件
- `APP_VERSION`: `v1.2.4`

## Known Stubs

なし。

## Threat Flags

本プランで新規追加したネットワークエンドポイント・auth パス・PII 取り扱いはなし。
`collections.deque` は標準ライブラリのため Package Legitimacy Gate 不要（T-02-SC 通り）。

## Self-Check: PASSED

- [x] `pagefolio/app.py` 存在確認: FOUND
- [x] `pagefolio/file_ops.py` 存在確認: FOUND
- [x] `pagefolio/constants.py` 存在確認: FOUND
- [x] コミット c5ef5c0 存在確認: FOUND
- [x] コミット 7dd5244 存在確認: FOUND
