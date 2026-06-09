---
quick_id: 260609-aaa
slug: v140-build-release
description: v1.4.0 ビルド・git push・GitHub Release 作成
date: 2026-06-09
status: in_progress
must_haves:
  truths:
    - dist/PageFolio-v1.4.0-win64.zip が存在する
    - git tag v1.4.0 が作成されている
    - GitHub Release v1.4.0 が公開されている（zip アセット付き）
  artifacts:
    - PageFolio-v1.4.0-win64.zip
    - GitHub Release: https://github.com/mistyura/PageFolio/releases/tag/v1.4.0
---

# Quick Task 260609-aaa: v1.4.0 ビルド・git push・GitHub Release 作成

## Goal

Phase 07 完了済みの v1.4.0 コードベースをビルドして GitHub へ公開する。

## Tasks

### Task 1: PyInstaller ビルド

**File:** `dist/PageFolio/`（再ビルド）

**Action:**
1. `pyinstaller PageFolio.spec --clean` でクリーンビルド実行
2. `dist/PageFolio/PageFolio.exe` が生成されることを確認

**Verify:** `dist/PageFolio/PageFolio.exe` が存在する

---

### Task 2: zip アーカイブ作成

**File:** `PageFolio-v1.4.0-win64.zip`

**Action:**
1. `dist/PageFolio/` を `PageFolio-v1.4.0-win64.zip` として圧縮
2. `pagefolio_settings.json`（開発用設定）を除外して圧縮

**Verify:** `PageFolio-v1.4.0-win64.zip` が存在する

---

### Task 3: git push + タグ作成

**Action:**
1. `git push origin main` で 115 コミットを push
2. `git tag v1.4.0` でタグを作成
3. `git push origin v1.4.0` でタグを push

**Verify:** `git tag -l v1.4.0` が結果を返す

---

### Task 4: GitHub Release 作成

**Action:**
1. `gh release create v1.4.0` でリリースを作成
   - タイトル: `PageFolio v1.4.0 — マルチプロバイダ OCR 対応`
   - ノート: 開発履歴.md の v1.4.0 サマリーを元に作成
   - アセット: `PageFolio-v1.4.0-win64.zip`

**Verify:** `gh release view v1.4.0` が正常出力

---

## Release Notes テンプレート

```
## PageFolio v1.4.0 — マルチプロバイダ OCR 対応

### 新機能

- **Claude OCR**: Anthropic Claude（messages API）による高精度 OCR。ANTHROPIC_API_KEY 環境変数で設定。
- **Gemini OCR**: Google Gemini（generateContent・inline_data）による OCR。GEMINI_API_KEY / GOOGLE_API_KEY 対応。
- **Tesseract OCR**: ローカル・オフラインで動作する Tesseract プロバイダを追加。pytesseract 不要。
- **プラグイン拡張フック**: `register_ocr_provider` フックによりサードパーティプラグインが独自 OCR バックエンドを登録可能に。
- **セキュリティ基盤**: APIキーは `pagefolio_settings.json` に書き込まれず、セッションメモリのみに保持。
- **逐次レンダリング**: 大容量 PDF の OCR でページ単位にレンダリング→送信→破棄するメモリ最適化。

### ダウンロード

**Windows**: `PageFolio-v1.4.0-win64.zip` を展開して `PageFolio.exe` を起動。

### OCR プロバイダ設定

| プロバイダ | 必要な設定 | 特徴 |
|-----------|-----------|------|
| LM Studio | ローカルサーバ起動 | ローカル・無料・GPU 推奨 |
| Claude | ANTHROPIC_API_KEY | 高精度・有料 |
| Gemini | GEMINI_API_KEY | 高精度・有料 |
| Tesseract | tesseract コマンド | ローカル・無料・精度は LLM より劣る |

詳細: [README](https://github.com/mistyura/PageFolio#readme)
```
