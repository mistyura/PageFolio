---
phase: "01-undo-redo"
plan: "03"
subsystem: "Undo/Redo テスト・バグ修正"
tags: [test, bug-fix, TDD, TEST-01, D-07, delete-redo, move-select, merge-resize-swap]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [insert-undo-content-integrity-test, all-ops-roundtrip-test]
  affects: [tests/test_pdf_ops.py, pagefolio/file_ops.py]
tech_stack:
  added: []
  patterns: [TDD, page-digest, delete_redo-op, move-select-inverse, merge-resize-undo-swap]
key_files:
  created: []
  modified:
    - tests/test_pdf_ops.py
    - pagefolio/file_ops.py
    - pagefolio/constants.py
    - 開発履歴.md
    - README.md
decisions:
  - "delete_redo op 分離: delete undo/redo 対称化のために delete_redo op を新設し、_restore_state(delete) = insert、_restore_state(delete_redo) = delete とする設計を採用"
  - "move 逆操作: move_page の厳密逆操作（fitz 依存）を廃止し、順列計算 + doc.select() による bulk_move 方式に統一"
  - "merge_resize undo/redo swap: _restore_state(merge_resize) で undo（結合取り消し）、_restore_state(merge_resize_undo) で redo（結合再実行）に swap"
  - "_page_digest: テキストベース（page.get_text().strip()）を採用（conftest サンプル PDF がテキストを持つため十分）"
  - "test_fallback_pdf_bytes_format 置換: 01-01 で test_restore_state_no_pdf_bytes_key / test_restore_state_returns_inverse_delta に置換済みのため本プランでの追加削除は不要と判断"
metrics:
  duration: "約 30 分"
  completed_date: "2026-06-03"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 1 Plan 3: 挿入 Undo/Redo 内容同一性・全 op 往復テスト Summary

**One-liner:** 挿入 Undo の内容同一性（digest）・redo 往復テスト（D-07）と全 op 最小往復安全網テストを追加し、テストで発見した delete/move/merge_resize の対称デルタバグ 3 件を Rule 1 自動修正（TEST-01 / Deferred 安全網）

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| TDD RED (Task 1) | 挿入 Undo/Redo 内容同一性・全 op 往復テスト追加 | 9e0bc28 | tests/test_pdf_ops.py |
| TDD GREEN (Task 1) | delete/move/merge_resize の Undo/Redo バグ修正 | afb1de1 | pagefolio/file_ops.py |
| Task 2 | バージョン更新・開発履歴追記 | 136585e | pagefolio/constants.py, 開発履歴.md, README.md |

## What Was Built

### tests/test_pdf_ops.py

- `_page_digest(page)` モジュールローカル関数を追加（`page.get_text().strip()` ベースのページ内容 digest）
- `class TestInsertUndoRedo` を追加（TEST-01 / D-07）:
  - `test_insert_undo_restores_page_count`: 挿入 N → Undo で `len(doc)` が元に戻ることを検証
  - `test_insert_undo_restores_content`: Undo 後の残ページ digest が挿入前と一致する内容同一性検証
  - `test_insert_undo_redo_roundtrip`: do→undo→redo で挿入ページ digest が一致する往復検証
- `class TestAllOpsUndoRedoRoundtrip` を追加（Deferred 安全網）:
  - `test_rotate_roundtrip`: 90度回転→undo→redo の rotation 属性検証
  - `test_delete_roundtrip`: 削除→undo（digest 復元）→redo の往復検証
  - `test_move_roundtrip`: ページ移動→undo（順序復元）→redo の往復検証
  - `test_duplicate_roundtrip`: 複製→undo→redo の往復検証
  - `test_merge_roundtrip`: merge→undo→redo の往復検証
  - `test_bulk_move_roundtrip`: bulk_move→undo→redo の順序 digest 検証
  - `test_bulk_crop_roundtrip`: bulk_crop→undo→redo の cropbox 属性検証
  - `test_merge_resize_roundtrip`: merge_resize→undo→redo の len・rect 検証
- 全テストで Undo/Redo state の `pdf_bytes` キー非依存を assert（D-05 整合）

### pagefolio/file_ops.py（Rule 1 バグ修正 — 3件）

**[Rule 1 - Bug] delete redo バグ修正**

- 原因: `_apply_inverse(delete)` が `op="delete"` のまま逆デルタを返していたため、redo 時に `_restore_state(delete)` が「insert 処理（undo 処理）」を再実行し、ページが毎 redo ごとに増殖していた
- 修正: `_apply_inverse(delete)` で `op="delete_redo"` に変更。`_restore_state` に `delete_redo` ブランチを追加（逆順で delete）

**[Rule 1 - Bug] move undo/redo バグ修正**

- 原因: `_restore_state(move)` が `doc.move_page(actual_dest, src)` を実行していたが、`move_page(src, dest)` の厳密な逆操作は `move_page(dest-1, src)`（src < dest 時）であり、誤った逆順で移動されていた。`src > dest` の場合も同様に失敗。
- 修正: `_apply_inverse(move)` で `move_page` の結果順列を計算し、逆順列を `bulk_move` op として返す。`_restore_state(move)` では `doc.select(inverse_order)` で正確に元の順序に戻す

**[Rule 1 - Bug] merge_resize undo/redo バグ修正**

- 原因: `_restore_state(merge_resize)` に「redo ロジック（元ページ削除 + 結合ページ挿入）」が実装され、`_restore_state(merge_resize_undo)` に「undo ロジック（結合ページ削除 + 元ページ復元）」が実装されていたが、undo スタックから取り出した `merge_resize` state は undo 処理（結合取り消し）をすべきなのに redo 処理が走っていた
- 修正: `_restore_state(merge_resize)` と `_restore_state(merge_resize_undo)` のロジックを入れ替え

## Key Design Decisions

1. **delete_redo op 分離**: `_restore_state(delete)` は「insert 処理」という設計上の対称性を維持しつつ、redo 用には専用 op `delete_redo` を設けて undo/redo を明確に分離した
2. **move 逆操作の bulk_move 化**: fitz の `move_page` は `src/dest` の大小関係で異なる動作をするため、厳密な逆操作計算が複雑。`doc.select()` による順列指定（bulk_move と同じ機構）に統一し信頼性を高めた
3. **merge_resize undo/redo swap**: `_apply_inverse` が返す逆デルタの op 名（`merge_resize_undo`/`merge_resize`）と `_restore_state` のブランチで実行するロジックを対称化した
4. **_page_digest のテキストベース採用**: conftest の `sample_pdf_doc`/`multi_pdf_files` は "Page N"/"File1 PageM" テキストを持つため、`page.get_text().strip()` が確実・高速（D-07 Claude's Discretion）

## Deviations from Plan

### 計画外の自動修正（Rule 1 — バグ3件）

**1. [Rule 1 - Bug] delete undo/redo 往復バグ**

- **発見:** Task 1 (TestAllOpsUndoRedoRoundtrip.test_delete_roundtrip)
- **症状:** redo 後 `len(doc) == 4`（期待: 2）。redo でページが再挿入されていた
- **原因:** `_apply_inverse(delete)` が `op="delete"` のままで返し、redo 時に insert が再実行
- **修正:** `op="delete_redo"` 新設、`_restore_state` に `delete_redo` ブランチ追加
- **ファイル:** `pagefolio/file_ops.py`
- **コミット:** afb1de1

**2. [Rule 1 - Bug] move undo/redo 往復バグ**

- **発見:** Task 1 (TestAllOpsUndoRedoRoundtrip.test_move_roundtrip)
- **症状:** undo 後順序が `['Page 3', 'Page 2', 'Page 1']`（期待: 元の順序）
- **原因:** `_restore_state(move)` が `move_page(actual_dest, src)` を実行するが、これは逆操作ではない
- **修正:** 順列計算 + `doc.select(inverse_order)` に変更
- **ファイル:** `pagefolio/file_ops.py`
- **コミット:** afb1de1

**3. [Rule 1 - Bug] merge_resize undo/redo 往復バグ**

- **発見:** Task 1 (TestAllOpsUndoRedoRoundtrip.test_merge_resize_roundtrip)
- **症状:** undo 後 `len(doc) == 1`（期待: 3）。undo 時に結合が再実行されていた
- **原因:** `_restore_state(merge_resize)` に redo ロジックが実装されていた（swap 必要）
- **修正:** `merge_resize` と `merge_resize_undo` ブランチのロジックを入れ替え
- **ファイル:** `pagefolio/file_ops.py`
- **コミット:** afb1de1

### test_fallback_pdf_bytes_format について

プランに「削除または置換」と記載があったが、01-01 のフェーズで `test_restore_state_no_pdf_bytes_key` / `test_restore_state_returns_inverse_delta` として既に置換済み。本プランでの追加作業は不要と判断し、SUMMARY に記録のみ。

## Verification

- `python -m pytest tests/ -q`: **160 passed**（既存 149 件 + 新規 11 件）
- `ruff check .`: **All checks passed!**
- `ruff format --check .`: **23 files already formatted**
- `tests/test_pdf_ops.py` に `class TestInsertUndoRedo` と `def test_insert_undo_redo_roundtrip` が存在: ✓
- `_page_digest` が digest 同一性検証に使われている: ✓
- Undo/Redo state に `pdf_bytes` キーが現れないことを全テストで assert: ✓
- `APP_VERSION`: `v1.2.5`

## Known Stubs

なし。

## Threat Flags

本プランで新規追加したネットワークエンドポイント・auth パス・PII 取り扱いはなし。
テストフィクスチャ生成の PDF のみで外部入力なし（T-03-01/T-03-02 通り）。

## Self-Check: PASSED

- [x] `tests/test_pdf_ops.py` 存在確認: FOUND
- [x] `pagefolio/file_ops.py` 存在確認: FOUND
- [x] コミット 9e0bc28 存在確認: FOUND
- [x] コミット afb1de1 存在確認: FOUND
- [x] コミット 136585e 存在確認: FOUND
- [x] `TestInsertUndoRedo` クラス存在: FOUND
- [x] `TestAllOpsUndoRedoRoundtrip` クラス存在: FOUND
- [x] 160 passed 確認: PASSED
