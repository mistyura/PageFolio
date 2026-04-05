---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T01: PDF操作テストの作成

fitz を使って PDF の読込・保存・回転・削除・挿入・結合・分割・トリミングの各操作をテストする。PDFEditorApp のメソッドは GUI 依存が強いため、fitz の API を直接テストしてアプリの PDF 操作ロジックと同等の操作が正しく動くことを検証する。

## Inputs

- `pagefolio.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_pdf_ops.py`

## Verification

pytest tests/test_pdf_ops.py -v
