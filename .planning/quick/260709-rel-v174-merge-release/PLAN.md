---
quick_id: 260709-rel
slug: v174-merge-release
date: 2026-07-09
description: ブランチ claude/prompt-markdown-formatting-1loozg を main へマージし v1.7.4 をリリース（ビルド・タグ・GitHub Release）
---

# Quick Task 260709-rel: v1.7.4 マージ・リリース

## 背景

ブランチ `claude/prompt-markdown-formatting-1loozg` に v1.7.4 の実機能（OCR カスタム/サマリプロンプトの外部 md ファイル読込・Markdown 表示プリセット一本化・モデル取得タイムアウト見直し・OCR ダイアログ右ペインのスクロール対応）が実装済み（`.planning/quick/260709-pmf-prompt-markdown-formatting-1loozg` 参照）。
`APP_VERSION = v1.7.4`・README バッジ・開発履歴.md は更新済みで、コード作業は不要。main への取り込みと公開リリースを行う。

## タスク

1. ブランチを検証（pytest + ruff）
2. PR を作成し main へマージ（merge commit）
3. PyInstaller で onedir ビルド（`--onedir --noconsole --icon=pagefolio.ico --name=PageFolio`）し `dist/PageFolio` を更新コミット
4. リリース成果物 `PageFolio-v1.7.4-win64.zip` + `.sha256` を作成
5. 注釈付きタグ `v1.7.4` を付与し GitHub Release を Latest として公開（成果物添付）

## 検証方法

- pytest / ruff check・format がグリーンであること
- ビルドした exe を実際に起動しプロセスが立ち上がることを確認
- GitHub Release が Latest・非 draft・成果物 2 件添付であること
