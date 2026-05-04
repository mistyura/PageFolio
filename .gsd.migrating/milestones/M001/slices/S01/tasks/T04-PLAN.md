---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T04: app.py D&D フィルター拡張

_on_dnd_drop() の '.pdf' ハードコードフィルターを SUPPORTED_EXTENSIONS 定数参照に差し替える（D-07, D-08）。

## Inputs

- `pagefolio/app.py の _on_dnd_drop() 付近の現在コード`
- `pagefolio/constants.py（T02 完了後）`
- `.planning/phases/01-基盤と画像対応/01-CONTEXT.md §Integration Points`

## Expected Output

- `_on_dnd_drop() が SUPPORTED_EXTENSIONS でフィルタリングしている`
- `'.pdf' のハードコード文字列比較が消えている`

## Verification

ruff check pagefolio/app.py がクリーン。python -c "import ast; ast.parse(open('pagefolio/app.py', encoding='utf-8').read())" が通る
