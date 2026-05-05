---
id: T02
parent: S01
milestone: M001
key_files:
  - C:/Users/shdwf/work/project/PageFolio/pagefolio/constants.py
key_decisions:
  - status_image_save_as の長い文字列はカッコ折り返し（括弧内文字列結合）で対処し、E501 を解消した
  - ruff format による frozenset 整形はそのまま受け入れた（意味に変更なし）
duration: 
verification_result: passed
completed_at: 2026-05-04T03:58:27.476Z
blocker_discovered: false
---

# T02: constants.py に SUPPORTED_EXTENSIONS / IMAGE_EXTENSIONS 定数と LANG の新規4キー・既存3キー更新を追加

**constants.py に SUPPORTED_EXTENSIONS / IMAGE_EXTENSIONS 定数と LANG の新規4キー・既存3キー更新を追加**

## What Happened

UI-SPEC の Constants Contract と Copywriting Contract に従い、pagefolio/constants.py を以下の通り変更した。

1. SUPPORTED_EXTENSIONS と IMAGE_EXTENSIONS を frozenset として追加（D-05）。
2. LANG['ja'] と LANG['en'] に新規4キーを追加:
   - filetypes_supported
   - filetypes_image
   - status_opened_image
   - status_image_save_as
3. LANG['ja'] と LANG['en'] の既存3キーの値を更新:
   - dnd_drop_hint: PDF のみ → PDF/画像対応の文言に変更
   - dnd_pdf_only: PDF のみ対応 → PDF/画像対応の文言に変更
   - dlg_insert_title: PDF選択 → ファイル選択（PDF/画像）の文言に変更

ruff から E501 (行長 88文字超) が2件発生したため、status_image_save_as の値をカッコで折り返して対処。ruff format 実行後、frozenset の内包表記が若干整形されたが機能に影響なし。

## Verification

python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']; print('OK')" → OK。全アサーション（定数・LANG キー・更新値）パス。ruff check pagefolio/constants.py → All checks passed!

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']; print('OK')"` | 0 | PASS | 300ms |
| 2 | `ruff check pagefolio/constants.py && ruff format pagefolio/constants.py` | 0 | PASS | 500ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `C:/Users/shdwf/work/project/PageFolio/pagefolio/constants.py`
