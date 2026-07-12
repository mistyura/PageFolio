---
quick_id: 260623-rel
slug: v161-merge-release
date: 2026-06-23
description: ブランチ claude/great-maxwell-k67sbc を main へマージし v1.6.1 をリリース（ビルド・タグ・GitHub Release）
---

# Quick Task 260623-rel: v1.6.1 マージ・リリース

## 背景

ブランチ `claude/great-maxwell-k67sbc` に v1.6.1 の実機能（OCR タイムアウト上限拡大・PDF パスワード対応・印刷機能）が実装済み。
`APP_VERSION = v1.6.1`・README バッジ・開発履歴.md は更新済みで、コード作業は不要。main への取り込みと公開リリースを行う。

## タスク

1. ブランチを検証（pytest + ruff）
2. PyInstaller で onedir ビルド（`--onedir --noconsole --icon=pagefolio.ico --name=PageFolio`）し `dist/PageFolio` を更新コミット
3. PR を作成し main へマージ（前例踏襲・merge commit）
4. リリース成果物 `PageFolio-v1.6.1-win64.zip` + `.sha256` を作成
5. 注釈付きタグ `v1.6.1` を付与し GitHub Release を Latest として公開（成果物添付）

## 検証

- pytest: 613 件グリーン
- ruff check / format: クリーン
- Release: Latest・draft なし・成果物 2 件添付
