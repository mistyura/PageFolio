---
gsd_plan_version: 1.0
quick_id: 260812-adk
slug: config-json-claude-md-assembly-claude-md
description: config.json に claude_md_assembly を追加し CLAUDE.md のブロックを link 化
date: 2026-08-12
mode: quick
branch: quick/260812-adk-config-json-claude-md-assembly-claude-md
---

# Quick Plan 260812-adk — `claude_md_assembly` の追加と CLAUDE.md ブロックの link 化

## 背景

3 プロジェクト比較（260812-9tv）の差分 #5。最後の未解消項目。

| プロジェクト | `claude_md_assembly` | CLAUDE.md の 4 ブロック |
|---|---|---|
| numbers | `mode: embed` + blocks 4 つすべて `link` | link 記述（`.planning/` の各ドキュメントへの参照文） |
| loto | 同上（numbers と同値） | 同上 |
| **PageFolio** | **キーなし** | **`project` / `architecture` は本文を embed、`stack` / `conventions` は空** |

**設定を追加するだけでは config と CLAUDE.md が乖離する**（ブランチ運用で是正したのと同じ構造）。
今回は設定追加とブロック本体の link 化を同時に行い、乖離を作らない。

## 事前調査: link 化で情報が失われないか

CLAUDE.md の `architecture` ブロック（embed）に書かれている内容が、リンク先に存在するかを確認した。

| CLAUDE.md embed の項目 | `.planning/codebase/ARCHITECTURE.md` | `.planning/PROJECT.md` |
|---|---|---|
| Threading（`root.after()` / `_preview_gen` / ThreadPoolExecutor） | あり（L266・より詳しい） | あり（Constraints） |
| Global state（`C` / `_current_font_size`） | あり（L267） | あり |
| `MAX_UNDO = 20` / デルタ dict | あり（L268） | あり |
| Blob ライフサイクル（64KiB 閾値・eviction・redo クリア・close/exit purge・直接 `append`/`clear` 禁止） | あり（L206-211 / L269） | あり（Constraints） |
| CropBox safety | あり（L270） | あり |
| **ヘルパー名 `_capture_page_blob()` / `_blob_bytes()`** | **なし** | **あり**（260812-a8u で追加した Constraints） |

さらに ARCHITECTURE.md は CLAUDE.md の embed にない項目（PDF open/close のリソースリーク、Pagination window 不変条件）も持つ。
→ **link 化による情報損失はない。** 唯一 ARCHITECTURE.md に無いヘルパー名だけ、Task 1 で補記して完全にする。

## 確定事項

1. 記述の型は **numbers / loto と同一**（各ブロックに `## 見出し` + 参照先 1 文）。文面は PageFolio の実情に合わせる
2. `skills` / `workflow` / `profile` ブロックは `claude_md_assembly.blocks` の対象外のため**無変更**
3. `config.json` は `claude_md_assembly` キーの追加のみ。他キーは触らない
4. トレードオフ: CLAUDE.md 単体では制約の本文が読めなくなり、エージェントはリンク先を開く必要がある。
   これは numbers/loto が意図的に選んだ設計（CLAUDE.md を薄く保つ）であり、それに合わせる

## タスク

### Task 1: `ARCHITECTURE.md` に Blob ヘルパー名を補記

- **files**: `.planning/codebase/ARCHITECTURE.md`
- **action**: 「Blob storage」の制約行に `_capture_page_blob()` / `_blob_bytes()` の名前を補う
- **verify**: `grep -c "_capture_page_blob"` が 1 以上
- **done**: link 化しても CLAUDE.md の embed 内容がすべてリンク先で読める

### Task 2: `CLAUDE.md` の 4 ブロックを link 記述へ置換

- **files**: `CLAUDE.md`
- **action**: `project` / `stack` / `conventions` / `architecture` の各ブロック（`<!-- GSD:*-start -->` 〜 `<!-- GSD:*-end -->` の中身）を link 記述へ差し替える。マーカー行は保持
- **verify**: 4 ブロックすべてに `## 見出し` と `.planning/` へのリンクが 1 つ以上あること。マーカーが 4 対とも維持されていること。リンク先ファイルが実在すること
- **done**: numbers / loto と同型の link 構成になっている

### Task 3: `config.json` に `claude_md_assembly` を追加

- **files**: `.planning/config.json`
- **action**: numbers / loto と同値の `claude_md_assembly`（`mode: embed` + blocks 4 つ `link`）を追加。挿入位置は `claude_md_path` の直後（loto と同じ）
- **verify**: 3 プロジェクトで `claude_md_assembly` が同値。`claude_md_assembly` 以外のトップレベルキーが `HEAD` 版と完全一致
- **done**: 設定と CLAUDE.md の実体が一致している

### Task 4: 検証

- **action**: `ruff check .` と `pytest`
- **done**: リリースゲート合格

## スコープ外

- `skills` / `workflow` / `profile` ブロック（`claude_md_assembly.blocks` の対象外）
- CLAUDE.md 前半（手書きの PageFolio 固有指示書部分）の変更
- `.planning/codebase/*.md` の内容拡充（Task 1 のヘルパー名補記を除く）
