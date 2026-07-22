---
quick_id: 260722-rel
slug: v181-merge-release
date: 2026-07-22
description: PR #34（v1.8.1 Gemini 400 修正）マージ後のリリース作業（ビルド・タグ・GitHub Release）
---

# Quick Task 260722-rel: v1.8.1 マージ・リリース

## 背景

ブランチ `claude/gemini-api-400-error-5li33o` の v1.8.1（Gemini 新世代モデル 400 エラー修正 +
推奨モデルリスト追補）は GSD 遡及精査（GSD-AUDIT-DIRECTIVE 項目 1〜4）完了後、
PR #34 として 2026-07-22 に main へマージ済み（merge commit `8741bad`）。
GSD-AUDIT-DIRECTIVE 項目 5（リリース系）を本タスクで実施する。
`APP_VERSION = v1.8.1`・README バッジ・開発履歴.md は更新済みで、コード作業は不要。

## タスク

1. ~~PR 作成・マージ~~ → 完了（PR #34・ユーザーがマージ・2026-07-22）
2. main のツリーがブランチ先端 `3f1c00a` と同一であることを確認（pytest 1109 件・ruff
   クリーンの検証を流用）
3. PyInstaller で onedir ビルド（`--onedir --noconsole --icon=pagefolio.ico --name=PageFolio`）し
   `dist/PageFolio` を更新コミット
   - **注意（指示書項目 5）**: `ocr_custom_prompt_sample.md` / `ocr_summary_prompt_sample.md` は
     dist/PageFolio 直下にのみ git 管理されているため、ビルド前に退避しビルド後に復元・
     内容不変を確認する（v1.8.1 の架空化編集を失わないこと）
4. リリース成果物 `PageFolio-v1.8.1-win64.zip` + `.sha256` を作成
5. 注釈付きタグ `v1.8.1` を付与し GitHub Release を Latest として公開（成果物添付）

## 検証方法

- main ツリーとブランチ先端の diff がゼロであること（検証流用の前提）
- ビルドした exe を実際に起動しプロセスが立ち上がることを確認
- サンプルプロンプト 2 ファイルがビルド後も v1.8.1 の内容（架空化済み）であること
- GitHub Release が Latest・非 draft・成果物 2 件添付であること
