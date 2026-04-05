# S02: PDF操作テスト — UAT

**Milestone:** M001
**Written:** 2026-03-31T10:07:01.371Z

## S02 UAT: PDF操作テスト\n\n### テスト実行\n- [x] `pytest tests/test_pdf_ops.py -v` → 26件全パス\n- [x] `ruff check . && ruff format --check .` → グリーン\n\n### 検証項目\n- [x] PDF読込・保存テスト正常\n- [x] ページ回転・削除テスト正常\n- [x] ページ挿入・結合テスト正常\n- [x] ページ分割テスト正常\n- [x] トリミング（CropBox）テスト正常
