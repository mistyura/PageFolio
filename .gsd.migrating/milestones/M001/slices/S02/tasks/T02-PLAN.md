---
estimated_steps: 1
estimated_files: 3
skills_used: []
---

# T02: S02 検証: ruff + pytest グリーン確認

リントチェックと全テスト実行でグリーン確認。

## Inputs

- `tests/test_pdf_ops.py`
- `tests/test_utils.py`
- `tests/conftest.py`

## Expected Output

- Update the implementation and proof artifacts needed for this task.

## Verification

ruff check . && ruff format --check . && pytest tests/ -v
