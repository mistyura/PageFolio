---
id: S01
parent: M001
milestone: M001
provides:
  - ["requirements.txt 7パッケージ固定済み", "PNG/JPG/BMP/TIFF ファイルのファイルダイアログ・D&D 開封対応", "画像ファイルの上書き保存 → PDF 保存ダイアログへのフォールスルー", "SUPPORTED_EXTENSIONS / IMAGE_EXTENSIONS 定数による拡張子管理の一元化"]
requires:
  []
affects:
  []
key_files:
  - ["requirements.txt", "pagefolio/constants.py", "pagefolio/file_ops.py", "pagefolio/page_ops.py", "pagefolio/app.py"]
key_decisions:
  - ["SUPPORTED_EXTENSIONS / IMAGE_EXTENSIONS を frozenset で constants.py に定義し、file_ops.py・page_ops.py・app.py の3箇所で共有参照（ハードコード撲滅）", "filetypes フィルター文字列は frozenset から sorted() で動的生成し、拡張子追加時の保守性を確保", "_save_file() の画像フォールスルーは確認ダイアログなしで _save_as() に直行（UI-SPEC Interaction Contract 準拠）", "拡張子チェックは os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS パターンで統一"]
patterns_established:
  - ["拡張子定数は constants.py の frozenset で一元管理し、各モジュールは import して参照する", "ファイルダイアログの filetypes は frozenset から sorted() で動的生成する", "画像ファイル判定は os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS パターンを使う"]
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-05-04T04:04:26.539Z
blocker_discovered: false
---

# S01: 基盤と画像対応

**requirements.txt を7パッケージに整理し、PNG/JPG/BMP/TIFF の開封・編集・保存フローを実装した**

## What Happened

S01 は5タスクで構成され、すべて計画通りに完了した。

**T01 (requirements.txt 整備)**: ファイルを確認したところすでに直接依存7パッケージ（PyMuPDF, Pillow, tkinterdnd2, pyinstaller, pytest, pytest-cov, ruff）がバージョン固定で記載されており、変更不要であった。

**T02 (constants.py 拡張)**: SUPPORTED_EXTENSIONS と IMAGE_EXTENSIONS を frozenset として追加。LANG['ja']/'en' に新規4キー（filetypes_supported, filetypes_image, status_opened_image, status_image_save_as）を追加し、既存3キー（dnd_drop_hint, dnd_pdf_only, dlg_insert_title）を画像対応の文言に更新した。ruff E501 は括弧折り返しで対処。

**T03 (file_ops.py 変更)**: _open_file() の filetypes を4エントリー（サポート全拡張子・PDFのみ・画像のみ・すべて）に変更。_open_pdf_path() に拡張子チェックを追加して画像オープン時は status_opened_image を表示。_save_file() に IMAGE_EXTENSIONS チェックを追加して _save_as() フォールスルーを実装。page_ops.py の挿入ダイアログも同様に更新した。

**T04 (app.py D&D 拡張)**: _on_dnd_drop() の '.pdf' ハードコード比較を os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS に置換し、画像ファイルのドロップも受け付けるようにした。

**T05 (リント・テスト確認)**: ruff check . && ruff format . が "All checks passed / 20 files left unchanged"、pytest が108件全PASSED で完了を確認。

## Verification

1. ruff check . && ruff format . → All checks passed / 20 files left unchanged（エラー・警告ゼロ）
2. pytest → 108 passed in 1.20s（test_pdf_ops.py 31件、test_plugins.py 40件、test_utils.py 37件 — FAILED ゼロ）
3. python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']" → OK
4. grep -c '==' requirements.txt → 7（仕様通り7パッケージ）

## Requirements Advanced

- MAINT-02 — requirements.txt を直接依存7パッケージのみにバージョン固定で整理済みを確認・維持した
- IMG-01 — ファイルダイアログ・D&D 両経路で PNG/JPG/BMP/TIFF を開けるようになり、既存編集操作（回転・削除・結合等）が使えるパスが整備された

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

T03 の実装スコープが file_ops.py に加えて page_ops.py（_insert_from_file のダイアログ）も含む形となった。これは UI-SPEC D-06 の「挿入ダイアログも4エントリーに変更」要件を満たすための自然な拡張であり、計画外ではあるが仕様の範囲内。

## Known Limitations

- GUI レイヤーでの実動作確認（実際のファイルダイアログ・D&D）は自動テストでは未検証
- 画像ファイルを fitz.open() で開いた際の実際のサムネイル・プレビュー品質は手動確認が必要
- _merge_pdf ダイアログは UI-SPEC の指示通り変更しておらず PDF のみ対応のまま

## Follow-ups

- 手動 GUI テスト: PNG/JPG/BMP/TIFF を開いてサムネイル・プレビュー・全編集操作を確認
- 手動 GUI テスト: 画像ファイル開封後に Ctrl+S で PDF 保存ダイアログが開くことを確認
- S02（バックグラウンドレンダリング）では viewer.py のプレビュー生成をスレッド化する必要がある

## Files Created/Modified

- `requirements.txt` — 直接依存7パッケージのバージョン固定（変更なし・確認のみ）
- `pagefolio/constants.py` — SUPPORTED_EXTENSIONS・IMAGE_EXTENSIONS 定数追加、LANG に新規4キー追加・既存3キー更新
- `pagefolio/file_ops.py` — ファイルダイアログを4エントリーに変更、画像オープン時の status 分岐、_save_file() に IMAGE_EXTENSIONS チェックとフォールスルー実装
- `pagefolio/page_ops.py` — 挿入ダイアログの filetypes を4エントリーに変更
- `pagefolio/app.py` — _on_dnd_drop() の拡張子フィルターを SUPPORTED_EXTENSIONS 定数参照に変更
