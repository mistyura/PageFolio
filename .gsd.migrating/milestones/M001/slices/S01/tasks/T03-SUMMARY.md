---
id: T03
parent: S01
milestone: M001
key_files:
  - C:/Users/shdwf/work/project/PageFolio/pagefolio/file_ops.py
  - C:/Users/shdwf/work/project/PageFolio/pagefolio/page_ops.py
key_decisions:
  - filetypes フィルター文字列は frozenset から sorted() で動的生成（拡張子追加時の保守性を確保）
  - 挿入ダイアログも4エントリーに変更（_merge_pdf は変更しない — UI-SPEC の指示通り）
  - status_opened_image は _open_pdf_path 内で拡張子チェックにより分岐（D&D 経由での呼び出しにも対応）
duration: 
verification_result: passed
completed_at: 2026-05-04T04:01:27.853Z
blocker_discovered: false
---

# T03: file_ops.py と page_ops.py のファイルダイアログを4エントリーのfiletypesに更新し、画像ファイルの上書き保存フォールスルーと status_opened_image 表示を実装した

**file_ops.py と page_ops.py のファイルダイアログを4エントリーのfiletypesに更新し、画像ファイルの上書き保存フォールスルーと status_opened_image 表示を実装した**

## What Happened

以下の変更を行った。

1. pagefolio/file_ops.py に IMAGE_EXTENSIONS と SUPPORTED_EXTENSIONS のインポートを追加。

2. _open_file() の filetypes を UI-SPEC D-06 仕様の4エントリーに変更:
   - サポートファイル (SUPPORTED_EXTENSIONS 全拡張子)
   - PDFファイル (*.pdf)
   - 画像ファイル (IMAGE_EXTENSIONS 全拡張子)
   - すべて (*.\*)
   各エントリーのフィルター文字列は frozenset から動的生成。

3. _open_pdf_path() に拡張子チェックを追加し、画像ファイルを開いた場合は status_opened_image を表示するように変更（PDF の場合は従来の status_opened を使用）。

4. _save_file() に IMAGE_EXTENSIONS チェックを追加（D-11対応）:
   - filepath の拡張子が IMAGE_EXTENSIONS に含まれる場合は status_image_save_as を表示して _save_as() にフォールスルー
   - 確認ダイアログは表示しない（UI-SPEC Interaction Contract 通り）

5. pagefolio/page_ops.py の _insert_from_file() ダイアログも同様に4エントリーのfiletypesに変更（D-06 の挿入ダイアログ変更要件）。IMAGE_EXTENSIONS と SUPPORTED_EXTENSIONS をインポート追加。

ruff の import-order 警告が page_ops.py で1件発生したが --fix で自動修正済み。

## Verification

ruff check pagefolio/file_ops.py pagefolio/page_ops.py がクリーン。python -c ast.parse の構文確認が両ファイルとも通過。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ruff check pagefolio/file_ops.py pagefolio/page_ops.py` | 0 | All checks passed | 800ms |
| 2 | `python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read())"` | 0 | file_ops.py: 構文OK | 200ms |
| 3 | `python -c "import ast; ast.parse(open('pagefolio/page_ops.py', encoding='utf-8').read())"` | 0 | page_ops.py: 構文OK | 200ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `C:/Users/shdwf/work/project/PageFolio/pagefolio/file_ops.py`
- `C:/Users/shdwf/work/project/PageFolio/pagefolio/page_ops.py`
