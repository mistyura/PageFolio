---
id: T04
parent: S04
milestone: M001
key_files:
  - pagefolio/page_ops.py
key_decisions:
  - 複数ページルートでは現在ページの mediabox を基準に相対座標を算出し各ページに乗算する方式を採用（ページサイズが異なっても正しく比率変換される）
  - 単ページ時は既存コードパスを一切変更せず維持（後退互換）
  - set_cropbox の ValueError は複数ページ時には continue でスキップ（単ページ時は従来通りエラーダイアログ表示）
duration: 
verification_result: passed
completed_at: 2026-05-04T05:06:29.012Z
blocker_discovered: false
---

# T04: page_ops.py の _crop_page() に複数ページ一括トリミング対応を追加し、相対座標変換 + bulk_crop op で選択ページ全体に適用できるようにした

**page_ops.py の _crop_page() に複数ページ一括トリミング対応を追加し、相対座標変換 + bulk_crop op で選択ページ全体に適用できるようにした**

## What Happened

_crop_page() を単ページ／複数ページ分岐に書き換えた。`_get_targets()` で対象ページリストを取得し、2ページ以上の場合は確認ダイアログ（confirm_bulk_crop）を表示する。単ページ時は既存コードパスをそのまま維持。複数ページ時は、現在ページの mediabox を基準に相対座標（rel タプル）を算出し、各対象ページの mediabox に乗算して新しい cropbox を決定する。EPS クランプ・is_empty/is_infinite/サイズ 1 未満チェック・set_cropbox の ValueError を各ページで適用し、無効なページはスキップする。undo は T01 で追加した bulk_crop 分岐（crop_data リスト）を使用。後処理の _invalidate_thumb_cache・_refresh_all・ステータス表示・プラグインイベントを if/else の外に共通配置し、targets サイズで分岐するよう実装した。T01（_save_undo bulk_crop）・T02（LANG キー）が前提として正常に機能していることを確認済み。

## Verification

ruff check . && ruff format . → All checks passed（E501 を1件修正後クリア）。pytest → 109 passed in 0.99s。スライス検証コマンド `grep -c \"bulk_crop|confirm_bulk_crop|_get_targets\" pagefolio/page_ops.py` → 6（3キーワードすべてマッチ確認）。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ruff check . && ruff format .` | 0 | ✅ pass | 2100ms |
| 2 | `pytest --tb=short -q` | 0 | ✅ pass | 990ms |
| 3 | `grep -c "bulk_crop\|confirm_bulk_crop\|_get_targets" pagefolio/page_ops.py` | 0 | ✅ pass (count=6) | 100ms |

## Deviations

none

## Known Issues

none

## Files Created/Modified

- `pagefolio/page_ops.py`
