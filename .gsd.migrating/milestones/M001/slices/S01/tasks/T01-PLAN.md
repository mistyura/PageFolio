---
estimated_steps: 1
estimated_files: 2
skills_used: []
---

# T01: tests ディレクトリと conftest.py の作成

tests/ ディレクトリと tests/__init__.py を作成。conftest.py に tmp_path ベースの一時設定ファイルフィクスチャ、テスト用 PDF 生成フィクスチャを定義する。

## Inputs

- `pagefolio.py`

## Expected Output

- `tests/__init__.py`
- `tests/conftest.py`

## Verification

python -c "import tests" && pytest --co tests/
