---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T01: requirements.txt 整備

現在の pip freeze 全出力を直接依存のみに書き直す。PyMuPDF, Pillow, tkinterdnd2, pyinstaller（実行依存）と pytest, pytest-cov, ruff（dev 依存）をバージョン固定で記載する。無関係パッケージ（altgraph, numpy 等）はすべて除外する（D-01〜D-04）。

## Inputs

- `現在の requirements.txt の内容`
- `.planning/phases/01-基盤と画像対応/01-CONTEXT.md §D-01〜D-04`

## Expected Output

- `requirements.txt が直接依存 7 パッケージのみを含む`
- `インストール済みバージョンと一致したバージョン固定`

## Verification

cat requirements.txt でエントリー数が 7 以下であることを確認
