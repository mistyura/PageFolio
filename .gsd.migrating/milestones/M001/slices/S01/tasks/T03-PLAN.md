---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T03: _parse_page_ranges のテスト作成

PDFEditorApp._parse_page_ranges の単体テスト。正常系（単一ページ、範囲、複数範囲）、異常系（空文字列、範囲外、不正形式、逆範囲）。メソッドは self を使わないがインスタンス経由で呼ぶため、モックオブジェクトを作成してテストする。

## Inputs

- `pagefolio.py`

## Expected Output

- `tests/test_utils.py (追記)`

## Verification

pytest tests/test_utils.py -v -k parse_page_ranges
