---
estimated_steps: 1
estimated_files: 2
skills_used: []
---

# T05: リント・テスト・受け入れ確認

全 py ファイルに対して ruff check && ruff format を実行し警告ゼロを確認する。pytest を実行し全テストがパスすることを確認する。

## Inputs

- `T01〜T04 の全変更完了後の状態`

## Expected Output

- `ruff check . がエラーゼロ`
- `pytest が全件 PASSED`

## Verification

ruff check . && ruff format . の出力にエラーなし。pytest の出力に FAILED がゼロ
