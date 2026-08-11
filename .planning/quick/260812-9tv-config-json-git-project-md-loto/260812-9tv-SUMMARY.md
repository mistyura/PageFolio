---
gsd_summary_version: 1.0
quick_id: 260812-9tv
slug: config-json-git-project-md-loto
description: config.json の git セクションと PROJECT.md のブランチ運用節を loto/numbers に合わせる
date: 2026-08-12
status: complete
---

# Quick Summary 260812-9tv — config.json の `git` セクションと PROJECT.md のブランチ運用節を loto/numbers に合わせる

## 結果

前タスク 260812-9ev がドキュメント（`docs/DEVELOPMENT.md` / `CONTRIBUTING.md`）だけを揃えたのに対し、本タスクで **設定と GSD 規範**を揃えた。これにより quick task が `main` へ直接コミットされる経路を設定レベルで塞いだ。

## 変更内容

### `.planning/config.json`（`git` セクションの 3 キーのみ）

| キー | 変更前 | 変更後 |
|---|---|---|
| `branching_strategy` | `"none"` | `"milestone"` |
| `milestone_branch_template` | `"gsd/{milestone}-{slug}"` | `"feature/{milestone}"` |
| `quick_branch_template` | `null` | `"quick/{num}-{slug}"` |

`create_tag` / `phase_branch_template` は既に同値のため無変更。**`git` 以外のトップレベルキーは 1 つも変更していない**（`model_policy` / `granularity` / `review` 等は PageFolio 固有のため丸コピー禁止）。検証スクリプトで `HEAD` 版との差分が `git` セクションのみであることを機械確認済み。

### `.planning/PROJECT.md`

- `## Context` 表に入口 1 行を追加（`ブランチ運用（v1.10.0 以降）` → 下記節へのポインタ）。loto/numbers は `## Constraints` 末尾に置いているが、PageFolio に同節がないため `## Context` を入口とした
- `## ブランチ運用` 節を `## Key Decisions` の直前に新設。numbers 原典の 5 部構成（導入 / 設定表 / 分岐元とマージ先 / なぜ quick task を `main` へ入れないか / 例外を要する場合）を踏襲し、内容は PageFolio の実測事実へ差し替え
- 末尾 `*Last updated:*` を本変更の記録で更新

## 調査の訂正（ユーザー指摘による）

初回調査で numbers の **`main`** を参照し「loto の SUMMARY にある『numbers と同値化』は事実と異なる」と報告したが、**これは誤り**だった。numbers は `feature/v0.18.0` をチェックアウトしており、同ブランチに `milestone` 戦略と `## ブランチ運用` 節が揃っている。numbers 自身のルール（`main` へは `/gsd-complete-milestone` 時に一度だけ統合）に従った結果、`main` 側が未反映だっただけ。

| プロジェクト | 参照ブランチ | `branching_strategy` | `## ブランチ運用` 節 | 発効 |
|---|---|---|---|---|
| numbers | `feature/v0.18.0`（進行中） | `milestone` | あり（**パターンの原典**） | v0.18.0 開始時・2026-08-12 確立 |
| loto | `main`（v0.18.0 出荷済み） | `milestone` | あり（numbers を踏襲） | v0.19.0 以降・2026-08-12 確立 |
| PageFolio | `main`（v1.9.0 出荷済み） | `milestone`（本タスク） | あり（本タスク） | **v1.10.0 以降**・2026-08-12 確立 |

3 プロジェクトの `git` セクションが同値であることを検証スクリプトで確認済み。

## PROJECT.md に記載した検証済み事実

### PageFolio 自身（`git log --first-parent` で実測）

- v1.7.x = PR #30（merge `f2ead82` / 2026-07-05）、v1.8.0 = PR #33（merge `8b8b423` / 2026-07-16）、v1.8.1 = PR #34（merge `8741bad` / 2026-07-22）
- **v1.9.0 マイルストーン全体が `main` 直進行** — `8741bad` 以降マージコミットなし。2026-07-22〜2026-08-12 の **163 コミット**が `main` の first-parent 上
- quick task も直コミット（`260810-f1u`=`a553df7` / `260811-asq`=`3f83067` / `260812-9ev`=`467b092`,`293bb53`）
- ブランチ命名の揺れ: `dev/v1.7.x` / `dev/v1.8.0` / `feature/v1.5.0-improvements`（PR #18）/ `feature/add-ollama-runpod`（PR #26）

### numbers の二重実装事故（numbers リポジトリで直接検証）

`260721-bfc` の `b44b665`（`make optimize` 新設 / 2026-07-21）が `main` 直コミット → `feature/v0.17.0` マージは 12 日後の `cf3bec0`（2026-08-02）→ 監査 W-1 誤検出の revert `309fca6`（2026-08-02）。**PageFolio で二重実装事故が起きたとは書いていない**（実際に起きていない）。

## 検証

- `config["git"] == loto["git"] == numbers["git"]` を assert で確認
- `git` 以外のトップレベルキーが `HEAD` 版と完全一致することを assert で確認
- `## ブランチ運用` 節の 5 部構成・設定表 3 行の実値一致・`## Context` 入口・発効表記を assert で確認
- `ruff check .` → All checks passed
- `pytest -q` → **1404 passed**（後述の注意点あり）

### テスト実行時の注意（要申し送り）

1 回目のフルスイートで `tests/test_toast.py` に **8 件の setup ERROR**（1396 passed, 8 errors）が発生。`tests/test_toast.py` 単体では 33 passed、フルスイート再実行では 1404 passed でグリーン。ドキュメント・設定のみの変更で Tkinter テストに影響する経路はなく、**CLAUDE.md「リリースゲート」節が「現行環境では再現しない」と記載している `TclError` 由来のセットアップ ERROR 症状が再現した**ものと判断する。同節の記載（累計 17 回連続グリーン）は本日時点で更新が必要。

## スコープ外

- `## Constraints` 節の新設（比較 #3・ユーザー判断で見送り）
- `## フェーズ完了 DoD` 節と `tests/test_gsd_dod.py` 相当の機械ゲート（比較 #4・loto のみ保有）
- `claude_md_assembly` キーの追加（比較 #5）
- numbers `main` への反映（numbers 側の `/gsd-complete-milestone` で解消される）
- 既存ブランチのリネーム・過去履歴の書き換え

## 申し送り

- 本タスク自体は init 時点の設定（`branch_name: null`）に従い `main` 上で実施した。**次の `/gsd-quick` からは `quick/{num}-{slug}` ブランチが自動作成される**
- config が決めるのはブランチ名だけで分岐元は実行時 HEAD 依存のため、**quick task 開始前に現在のブランチを確認すること**
- `/gsd-new-milestone` で v1.10.0 を定義後、最初の `/gsd-execute-phase` が `feature/v1.10.0` を自動作成・切替する
