---
id: T05
parent: S03
milestone: M001
key_files:
  - tests/test_pdf_ops.py
key_decisions:
  - 旧2テスト（全体バイト方式）を差分フォーマット検証の3テストで置換。クラス名 TestUndoRedoLogic は維持
duration: 
verification_result: passed
completed_at: 2026-05-04T04:47:59.606Z
blocker_discovered: false
---

# T05: test_pdf_ops.py の TestUndoRedoLogic を差分フォーマット検証の3テストに書き換え（全体バイト方式の旧2テストを置換）

**test_pdf_ops.py の TestUndoRedoLogic を差分フォーマット検証の3テストに書き換え（全体バイト方式の旧2テストを置換）**

## What Happened

既存の `TestUndoRedoLogic` クラスは全体バイトコピー方式を前提とした `test_save_and_restore_state` と `test_redo_after_undo` の2テストを持っていた。これらを差分フォーマット（操作タイプ別方式）の正しさを直接 fitz API で検証する3テストに置き換えた。

1. `test_rotate_delta_roundtrip`: 回転操作の差分（`{"op": "rotate", "data": [(page_i, old_rot)]}`）を保存し、Undo として `set_rotation()` で元の値に戻せることを検証。
2. `test_delete_delta_roundtrip`: 削除操作の差分（削除対象ページをバイト列で昇順保存）を検証。`fitz.open()` + `insert_pdf()` + `tobytes()` でページ抽出、削除後に `insert_pdf(stream=...)` で再挿入してページ数とテキスト内容を確認。
3. `test_fallback_pdf_bytes_format`: Redo スタック由来の旧フォーマット（`pdf_bytes` キー付き辞書）が `fitz.open(stream=...)` で復元できることを確認。

docstring の行長が ruff の 88 文字制限を超えたため、`test_fallback_pdf_bytes_format` のドキュメント文字列を短縮した（「フォールバック」部分を削除）。これ以外はタスクプランと完全一致。

## Verification

- `pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short` → 3テスト全パス (0.18s)
- `pytest tests/ -v --tb=short` → 109テスト全パス、リグレッションなし
- `ruff check tests/test_pdf_ops.py && ruff format --check tests/test_pdf_ops.py` → All checks passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short` | 0 | ✅ pass | 180ms |
| 2 | `pytest tests/ -v --tb=short` | 0 | ✅ pass | 1060ms |
| 3 | `ruff check tests/test_pdf_ops.py && ruff format --check tests/test_pdf_ops.py` | 0 | ✅ pass | 500ms |

## Deviations

test_fallback_pdf_bytes_format の docstring を ruff の行長制限（88文字）に合わせて短縮。機能・ロジックの変更なし。

## Known Issues

none

## Files Created/Modified

- `tests/test_pdf_ops.py`
