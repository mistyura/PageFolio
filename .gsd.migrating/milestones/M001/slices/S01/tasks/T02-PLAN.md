---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T02: constants.py 拡張子定数・LANG キー追加

pagefolio/constants.py に SUPPORTED_EXTENSIONS と IMAGE_EXTENSIONS の 2 定数を追加する（D-05）。LANG['ja'] と LANG['en'] 両方に新規キー filetypes_supported / filetypes_image / status_opened_image / status_image_save_as を追加し、既存キー dnd_drop_hint / dnd_pdf_only / dlg_insert_title の値を UI-SPEC の Copywriting Contract に従い更新する。

## Inputs

- `.planning/phases/01-基盤と画像対応/01-UI-SPEC.md §Constants Contract`
- `.planning/phases/01-基盤と画像対応/01-UI-SPEC.md §Copywriting Contract`

## Expected Output

- `SUPPORTED_EXTENSIONS と IMAGE_EXTENSIONS が constants.py に存在する`
- `LANG['ja'] と LANG['en'] に 4 新規キー追加・3 キーの値更新`

## Verification

python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']" が通る。ruff check pagefolio/constants.py がクリーン
