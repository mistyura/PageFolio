---
estimated_steps: 11
estimated_files: 3
skills_used: []
---

# T05: ruff リント・フォーマットと pytest 全件パスを確認

全変更ファイルが ruff check/format をパスし、pytest 108件全 PASSED であることを確認する。問題があれば修正する。

Steps:
1. ruff check . を実行してエラー・警告を確認
2. エラーがあれば修正（E501 は括弧折り返し、F401 は不要 import 削除など）
3. ruff format . でフォーマット適用
4. pytest を実行して 108件全 PASSED を確認
5. FAILED があれば原因を調査して修正（T02〜T04 の変更による regression を確認）

Must-haves:
- ruff check . がエラー・警告ゼロ
- ruff format . で変更なし（または適用済み）
- pytest 108件全 PASSED（新規テストは追加しない）

## Inputs

- `pagefolio/app.py`
- `pagefolio/viewer.py`
- `pagefolio/file_ops.py`

## Expected Output

- `pagefolio/app.py`
- `pagefolio/viewer.py`
- `pagefolio/file_ops.py`

## Verification

ruff check . && ruff format . --check && pytest --tb=short -q
