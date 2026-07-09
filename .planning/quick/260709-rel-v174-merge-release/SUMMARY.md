---
quick_id: 260709-rel
slug: v174-merge-release
date: 2026-07-09
status: complete
---

# Quick Task 260709-rel: v1.7.4 マージ・リリース — Summary

## 実施内容

| 手順 | 結果 |
|------|------|
| ブランチ検証 | pytest 880 件グリーン・ruff check / format クリーン（Windows 実機 / Python 3.14 venv） |
| マージ | PR #32 を merge commit で main へ取り込み（`14d8465`） |
| PyInstaller ビルド | onedir 再ビルド（exe + base_library.zip 更新）→ `v1.7.4 ビルド` コミット `0c92af4`。ビルド後 exe を実起動しプロセス生成を確認 |
| 成果物 | `PageFolio-v1.7.4-win64.zip`（約 39.6MB）+ `.sha256`（`6f43c2f9…c70`） |
| タグ | 注釈付き `v1.7.4` を `0c92af4` に付与・push |
| Release | GitHub Release `v1.7.4` を Latest として公開・成果物 2 件添付 |

## リリース

- タグ: `v1.7.4`（ビルドコミット `0c92af4`）
- URL: https://github.com/mistyura/PageFolio/releases/tag/v1.7.4
- Latest: 是・draft/prerelease: 否

## 含まれる v1.7.4 変更

- OCR カスタム/サマリプロンプトの外部 md ファイル読込・入力欄との双方向連動
- Markdown 整形表示の指定を OCR ダイアログのプリセットへ一本化
- クラウド LLM（Claude/Gemini/RunPod）のモデル一覧取得の非同期化・プロバイダ別タイムアウト見直し
- OCR ダイアログ右ペインの縦スクロール対応

詳細は [260709-pmf-prompt-markdown-formatting-1loozg/SUMMARY.md](../260709-pmf-prompt-markdown-formatting-1loozg/SUMMARY.md) を参照。

## 備考

- タグ名は既存タグと衝突しなかったためサフィックスなしで付与。
- `dist/PageFolio` は git 追跡対象のため、再ビルドしたバイナリをコミットしてからリリースした。
- GUI 実機での機能確認（外部 md ファイル連動・LLM 設定の非同期モデル取得・右ペインスクロール）は今回のリリース作業スコープ外（次回のユーザー実機確認を推奨）。
