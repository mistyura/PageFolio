---
quick_id: 260609-aaa
slug: v140-build-release
status: complete
date: 2026-06-09
commit: 9888c4f
---

# Quick Task 260609-aaa: v1.4.0 ビルド・git push・GitHub Release 作成 — COMPLETE

## 実行結果

### Task 1: PyInstaller ビルド ✓
- `pyinstaller PageFolio.spec --clean -y` 完了
- `dist/PageFolio/PageFolio.exe` 生成確認

### Task 2: zip アーカイブ作成 ✓
- `PageFolio-v1.4.0-win64.zip`（36MB）をプロジェクトルートに作成
- `dist/PageFolio/` フォルダ（`PageFolio.exe` + `_internal/`）を含む

### Task 3: git push + タグ ✓
- `git push origin main`: `cbcc3a7..9888c4f`（115 コミット）
- `git tag v1.4.0` + `git push origin v1.4.0` 完了

### Task 4: GitHub Release ✓
- URL: https://github.com/mistyura/PageFolio/releases/tag/v1.4.0
- タイトル: "PageFolio v1.4.0 — マルチプロバイダ OCR 対応"
- アセット: `PageFolio-v1.4.0-win64.zip`（36MB）
- リリースノート: Claude / Gemini / Tesseract OCR 対応、セキュリティ基盤、逐次レンダリング

## 備考

- `PageFolio-v1.4.0-win64.zip` はプロジェクトルートに残留（リポジトリには未追跡・gitignore 対象外）
- 必要に応じて削除: `rm PageFolio-v1.4.0-win64.zip`
