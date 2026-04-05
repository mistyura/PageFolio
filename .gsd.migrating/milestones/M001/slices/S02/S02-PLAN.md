# S02: PDF操作テスト

**Goal:** PDF の読込・保存・回転・削除・挿入・結合・分割・トリミングの基本操作をテストする
**Demo:** After this: pytest tests/test_pdf_ops.py が全てパスする

## Tasks
- [x] **T01: PDF操作テスト26件を作成（読込・保存・回転・削除・挿入・結合・分割・トリミング・Undo/Redo）** — fitz を使って PDF の読込・保存・回転・削除・挿入・結合・分割・トリミングの各操作をテストする。PDFEditorApp のメソッドは GUI 依存が強いため、fitz の API を直接テストしてアプリの PDF 操作ロジックと同等の操作が正しく動くことを検証する。
  - Estimate: 25min
  - Files: tests/test_pdf_ops.py
  - Verify: pytest tests/test_pdf_ops.py -v
- [x] **T02: S02 検証: ruff + pytest グリーン確認完了** — リントチェックと全テスト実行でグリーン確認。
  - Estimate: 5min
  - Verify: ruff check . && ruff format --check . && pytest tests/ -v
