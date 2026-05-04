---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T03: file_ops.py ファイルダイアログ・保存フロー変更

_open_file() の filetypes を UI-SPEC の 4 エントリーに変更（D-06）。挿入ダイアログの filetypes も同様に変更。_save_file() に IMAGE_EXTENSIONS チェックを追加し _save_as() フォールスルーを実装（D-11）。単体画像オープン後に status_opened_image を表示する。

## Inputs

- `pagefolio/file_ops.py 現在の内容`
- `pagefolio/constants.py（T02 完了後）`
- `.planning/phases/01-基盤と画像対応/01-UI-SPEC.md §Interaction Contract`
- `.planning/phases/01-基盤と画像対応/01-UI-SPEC.md §Phase 1 UI Surface Area`

## Expected Output

- `_open_file() が 4 エントリーの filetypes を持つ`
- `_save_file() が IMAGE_EXTENSIONS チェックで _save_as() にフォールスルーする`

## Verification

ruff check pagefolio/file_ops.py がクリーン。python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read())" が通る
