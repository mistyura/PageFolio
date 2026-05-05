---
id: T02
parent: S04
milestone: M001
key_files:
  - pagefolio/constants.py
key_decisions:
  - status_bulk_moved は D&D セクション（status_dnd_moved 直下）に配置し、機能グループの一貫性を維持した
  - status_bulk_cropped と confirm_bulk_crop はトリミングセクション（status_cropped 直下）に配置した
duration: 
verification_result: passed
completed_at: 2026-05-04T05:03:05.291Z
blocker_discovered: false
---

# T02: constants.py の LANG 辞書に bulk_move / bulk_crop 用ステータスキーを ja/en 両方に追加した

**constants.py の LANG 辞書に bulk_move / bulk_crop 用ステータスキーを ja/en 両方に追加した**

## What Happened

pagefolio/constants.py の LANG["ja"] と LANG["en"] に、T03(dnd.py) と T04(page_ops.py) が参照する3つのキーを追加した。

- `status_bulk_cropped`: トリミング一括適用後のステータスメッセージ（ja/en）
- `confirm_bulk_crop`: 一括トリミング実行前の確認ダイアログ文言（ja/en）
- `status_bulk_moved`: D&D 一括移動後のステータスメッセージ（ja/en）

ja の crop セクション（`status_cropped` 直下）に `status_bulk_cropped` と `confirm_bulk_crop` を追加、D&D セクション（`status_dnd_moved` 直下）に `status_bulk_moved` を追加。en セクションも同じ配置で追加。ruff check/format ともに通過・変更なし。

## Verification

grep で 6 件（ja 3件 + en 3件）確認。ruff check/format 通過。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'status_bulk_moved|status_bulk_cropped|confirm_bulk_crop' pagefolio/constants.py` | 0 | ✅ pass | 200ms |
| 2 | `ruff check pagefolio/constants.py && ruff format pagefolio/constants.py` | 0 | ✅ pass | 800ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pagefolio/constants.py`
