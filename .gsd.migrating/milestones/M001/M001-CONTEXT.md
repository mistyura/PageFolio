# M001 Context

v0.9.8.2 の PDF 編集ツールを v1.0 として完成させるマイルストーン。4フェーズで8要件をカバーする。

## Key Decisions (Phase 1 より)

- **D-01:** requirements.txt は直接依存のみ（PyMuPDF, Pillow, tkinterdnd2, pyinstaller, pytest, pytest-cov, ruff）。pip freeze 由来の無関係パッケージは除外
- **D-05:** 画像対応拡張子: PNG/JPG/JPEG/BMP/TIFF/TIF（4形式6拡張子）
- **D-06:** 「開く」ダイアログのデフォルトフィルターは「サポートファイル (*.pdf;*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif)」
- **D-07:** D&D フィルターを `SUPPORTED_EXTENSIONS` 定数（`constants.py`）に統一
- **D-09:** 複数画像の同時開封は `MergeOrderDialog` フローで処理（PDF と混在しても同様）
- **D-11:** 画像ファイルの上書き保存（Ctrl+S）は `_save_as()` にフォールスルー（PyMuPDF は画像形式での書き戻し不可のため）

## Implementation Notes

- `fitz.open()` は画像ファイルを単一ページ PDF として扱う → 既存操作がそのまま動く
- バックグラウンドレンダリング: `threading.Thread` + `root.after()` でスレッドセーフに UI 更新
- Undo 差分方式: 変更ページのバイト列のみキャッシュ（全体コピーより大幅にメモリ削減）
- 主な変更ファイル: `pagefolio/constants.py`, `pagefolio/file_ops.py`, `pagefolio/app.py`, `pagefolio/viewer.py`, `pagefolio/dnd.py`, `pagefolio/dialogs.py`, `pagefolio/settings.py`

## Phase 1 UI-SPEC 承認済み

`.planning/phases/01-基盤と画像対応/01-UI-SPEC.md` にて UI 仕様が承認済み。実装前に参照すること。
