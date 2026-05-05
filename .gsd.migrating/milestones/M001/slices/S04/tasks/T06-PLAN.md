---
estimated_steps: 9
estimated_files: 5
skills_used: []
---

# T06: ruff リントと pytest 全件確認を行い残存する問題を修正する

T01〜T05 で変更したすべてのファイルに対して ruff リント・フォーマットチェックと pytest 全件実行を行い、問題があれば修正する。

1. `ruff check .` を実行してリントエラーがないか確認。エラーがあれば修正。
2. `ruff format --check .` を実行してフォーマット違反がないか確認。違反があれば `ruff format .` で修正。
3. `pytest --tb=short -q` を実行して全件 PASSED を確認。失敗するテストがあれば原因を特定して修正。
4. 構文確認: `python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"` を各変更ファイルで実行（必要に応じて）。

注意:
- `pyproject.toml` / `ruff.toml` は編集禁止
- 裸の `except:` 句は禁止（`except Exception as e:` の形）
- `# type: ignore` の無断使用は禁止

## Inputs

- `pagefolio/file_ops.py`
- `pagefolio/dnd.py`
- `pagefolio/page_ops.py`
- `pagefolio/constants.py`
- `tests/test_pdf_ops.py`

## Expected Output

- `pagefolio/file_ops.py`
- `pagefolio/dnd.py`
- `pagefolio/page_ops.py`
- `pagefolio/constants.py`
- `tests/test_pdf_ops.py`

## Verification

ruff check . && ruff format --check . && pytest --tb=short -q
