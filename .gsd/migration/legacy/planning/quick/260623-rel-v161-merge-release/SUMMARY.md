---
quick_id: 260623-rel
slug: v161-merge-release
date: 2026-06-23
status: complete
---

# Quick Task 260623-rel: v1.6.1 マージ・リリース — Summary

## 実施内容

| 手順 | 結果 |
|------|------|
| ブランチ検証 | pytest 613 件グリーン・ruff check / format クリーン |
| PyInstaller ビルド | onedir 再ビルド（exe + base_library.zip 更新）→ `v1.6.1 ビルド` コミット `c8e33bc` |
| マージ | PR #25 を merge commit で main へ取り込み（`fd20608`） |
| 成果物 | `PageFolio-v1.6.1-win64.zip`（約 39MB・976 エントリ）+ `.sha256`（`21ac345d…f8863`） |
| タグ | 注釈付き `v1.6.1` を `fd20608` に付与・push |
| Release | GitHub Release `v1.6.1` を Latest として公開・成果物 2 件添付 |

## リリース

- タグ: `v1.6.1`（merge commit `fd20608`）
- URL: https://github.com/mistyura/PageFolio/releases/tag/v1.6.1
- Latest: 是・draft/prerelease: 否

## 含まれる v1.6.1 変更

- PDF パスワード対応（付与/解除・AES-256）
- 印刷機能（Ctrl+P・既定 PDF ハンドラ送信・未関連付け時フォールバック）
- OCR タイムアウト上限を 600 秒 → 900 秒へ拡大

## 備考

- 前例（v1.6.0-3 等）のタグは `-N` サフィックス付きだったが、v1.6.1 は衝突する ref が無いためサフィックスなしで付与。
- `dist/PageFolio` は git 追跡対象のため、再ビルドしたバイナリをコミットしてからリリースした。
