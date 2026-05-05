---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T02: constants.py の LANG 辞書に bulk_move / bulk_crop 用ステータスキーを追加する

T03 (dnd.py) と T04 (page_ops.py) が参照する LANG キーを ja/en 両方に追加する。

追加するキー（LANG["ja"] と LANG["en"] の両方に追加）:
- `"status_bulk_moved"`: ja = `"{count}ページを一括移動しました"` / en = `"Moved {count} page(s)"`
- `"status_bulk_cropped"`: ja = `"選択{count}ページをトリミングしました"` / en = `"Trimmed {count} selected page(s)"`
- `"confirm_bulk_crop"`: ja = `"選択中の{count}ページすべてにトリミングを適用しますか？"` / en = `"Apply crop to all {count} selected page(s)?"`

挿入位置:
- LANG["ja"]: `"status_cropped"` キーの近く（トリミングセクション内）
- LANG["en"]: 対応するトリミングセクション
- `"status_bulk_moved"` は D&D セクション（`"status_dnd_moved"` の近く）に追加してもよい

## Inputs

- `pagefolio/constants.py`

## Expected Output

- `pagefolio/constants.py`

## Verification

grep -c "status_bulk_moved\|status_bulk_cropped\|confirm_bulk_crop" pagefolio/constants.py
