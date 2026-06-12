---
quick_id: 260612-shc
slug: sharp-carson-zqfduf-v1-4-4
date: 2026-06-12
type: quick
mode: quick
---

# Plan: v1.4.4 の確定（マージ・リビルド・ドキュメント更新・公開）

## 背景

ブランチ `claude/sharp-carson-zqfduf` に v1.4.4 の開発成果（コミット5件）が揃っている。
`APP_VERSION = "v1.4.4"`・README バッジ・開発履歴.md・開発セッション SUMMARY.md は
ブランチ側で確定済み。main は当該ブランチへ fast-forward 可能（分岐なし）。
過去の v1.4.3 確定（260611-omi）と同型の「確定」作業を行う。

## v1.4.4 に含まれる変更（マージ由来）

- 機能追加: ページ→画像変換（1ページ1ファイル・AI/LLM 読取用途・`ExportImagesDialog`）
- バグ修正: 「縮小して保存」で元ファイルへ上書きできない問題（ハンドル解放→`os.replace`→開き直し）
- 機能追加: OCR リラン / 続きから再実行（リスタート）
- 機能追加: OCR サーキットブレーカー + エラー件数つき完了表示
- UI 改善: OCR ダイアログヘッダー（プロバイダ/モデル名 + ⚙LLM設定）
- README: Gemma 注意書きを動作実績ベースに更新

## タスク

### Task 1: main へ fast-forward マージ
- **files**: （git 操作のみ）
- **action**: `git merge --ff-only origin/claude/sharp-carson-zqfduf` で main を v1.4.4 へ前進
- **verify**: `grep APP_VERSION pagefolio/constants.py` が `v1.4.4`、`git log` が直線
- **done**: main HEAD = ブランチ先端（727b05f）

### Task 2: 品質ゲート + PyInstaller リビルド
- **files**: dist/PageFolio/PageFolio.exe, dist/PageFolio/_internal/base_library.zip
- **action**: `ruff check .` / `pytest` 確認 → `PyInstaller PageFolio.spec --noconfirm --clean` →
  ビルド成果物を「v1.4.4ビルド」コミット
- **verify**: ruff クリーン・pytest 全パス・dist 差分が exe/base_library.zip のみ
- **done**: 「v1.4.4ビルド」コミット作成

### Task 3: ドキュメント更新 + 公開
- **files**: .planning/STATE.md, 本ディレクトリ SUMMARY.md / PLAN.md
- **action**: STATE.md（frontmatter・Quick Tasks Completed 行追加・Session Continuity・
  Operator Next Steps）更新、SUMMARY.md の残タスクを確定済みに更新 →
  docs コミット → `git push origin main` → GitHub Release 作成（zip 添付）
- **verify**: STATE.md に 260612-shc 行、push 成功、Release 公開
- **done**: v1.4.4 が main・origin・GitHub Release に反映

## must_haves

- truths: main の APP_VERSION が v1.4.4 で確定／ruff・pytest グリーン
- artifacts: 「v1.4.4ビルド」コミット・STATE.md 更新・GitHub Release v1.4.4
- key_links: pagefolio/constants.py, PageFolio.spec, .planning/STATE.md
