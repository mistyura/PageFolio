---
gsd_summary_version: 1.0
quick_id: 260812-9ev
slug: loto-numbers
description: ブランチ運用ルールを loto/numbers に合わせる
date: 2026-08-12
status: complete
---

# Quick Summary 260812-9ev — ブランチ運用ルールを loto/numbers に合わせる

## 結果

PageFolio のブランチ運用規約を、姉妹プロジェクト loto / numbers の現行運用に統一した。

## 変更内容

### `docs/DEVELOPMENT.md`（「ブランチ運用」「PR プロセス」節）

| 項目 | 変更前 | 変更後（loto/numbers 準拠） |
|------|--------|---------------------------|
| main への直接コミット | 記述なし | **禁止**と明記。開発は機能ブランチ上で行う |
| ブランチ命名 | `fix/` `feat/` `docs/` `refactor/` + 短い説明 | `feature/v<バージョン>`（例: `feature/v1.10.0`）を正とし、単発作業のみ `feat/<短い説明>` を許容 |
| PR | 「GitHub で PR を作成」 | **`main` を対象**に作成、タイトル・本文とも**日本語** |
| コミットメッセージ | 日本語（形式指定なし） | **Conventional Commits 準拠の日本語** `type(scope): 日本語の説明`（type: feat/fix/docs/test/refactor/chore/build） |
| PR 手順 | 「レビュープロセス」5 項目 | loto/numbers と同じ番号付き 6 手順に再構成。PR 前チェックリストは維持 |

### `CONTRIBUTING.md`（「プルリクエストのガイドライン」節）

- ブランチ命名・コミット規約を `docs/DEVELOPMENT.md` を単一の情報源とする要約に置き換え、重複と食い違いを解消
- コミットメッセージ例を Conventional Commits 形式へ差し替え
- レビュープロセス手順 1・2 を「機能ブランチを切る」「`main` を対象に日本語で PR」へ更新

## loto/numbers との意図的な差分

| 項目 | loto / numbers | PageFolio | 理由 |
|------|---------------|-----------|------|
| CI green のマージ条件 | GitHub Actions `CI` / `test (3.12)` 必須 | **ローカルゲート**（`ruff check . && ruff format .` + `pytest`）に読み替え | PageFolio に `.github/workflows/` が存在しない |
| branch protection | numbers のみ `.github/branch-protection.yaml` あり | 未整備（doc に VERIFY コメントで明記） | 必須ステータスチェック（CI）が前提のため。CI 構築後に検討 |
| ブランチ命名の doc 表記 | numbers doc は `feat/<name>`（実態は `feature/v0.18.0` で doc が遅れている） | `feature/v<バージョン>` を正とし `feat/<短い説明>` を副として併記 | 2 プロジェクトの**現行実態**（loto #34-#36、numbers `feature/v0.17.0`/`v0.18.0`）に合わせた |

## 検証

- `ruff check .` → All checks passed / `ruff format --check .` → 90 files already formatted
- `pytest -q --basetemp=...` → **1404 passed**（リリースゲート合格条件を単一プロセスで完走）
- 旧命名規則（`fix/短い説明` 等）の残存 0 件を grep で確認

## スコープ外（未実施）

- `.github/workflows/ci.yml` の新規作成（CI 構築は別タスク。これがない限り loto/numbers と完全同一の PR ゲートにはできない）
- `.github/branch-protection.yaml` の作成
- `CLAUDE.md` の変更（loto/numbers の CLAUDE.md にもブランチ規約は無く、言語ルール表は既に整合済み）
- `開発履歴.md` への追記（`APP_VERSION` 変更を伴わないドキュメント整備のため。記録は STATE.md の Quick Tasks 表）
- 既存ブランチのリネーム・過去履歴の書き換え

## 申し送り

次回以降のマイルストーン作業は `main` へ直接コミットせず、`feature/v<次バージョン>` を切ってから着手すること。本タスク自体は GSD の quick 設定（`branch_name: null`）に従い `main` 上で実施した。
