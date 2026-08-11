---
gsd_summary_version: 1.0
quick_id: 260812-adk
slug: config-json-claude-md-assembly-claude-md
description: config.json に claude_md_assembly を追加し CLAUDE.md のブロックを link 化
date: 2026-08-12
status: complete
branch: quick/260812-adk-config-json-claude-md-assembly-claude-md
---

# Quick Summary 260812-adk — `claude_md_assembly` の追加と CLAUDE.md ブロックの link 化

## 結果

3 プロジェクト比較（260812-9tv）の**差分 #5 を解消し、比較で挙げた 5 差分すべてが完了**した（#6 は numbers 側の案件で、numbers の `/gsd-complete-milestone` で自動解消）。

設定キーの追加だけでは config と CLAUDE.md の実体が乖離するため（ブランチ運用で是正したのと同じ構造）、**ブロック本体の link 化を同時に実施**した。

## 変更内容

### `.planning/config.json`

`claude_md_path` の直後（loto と同じ位置）に numbers/loto と同値のキーを追加。

```json
"claude_md_assembly": {
  "mode": "embed",
  "blocks": { "project": "link", "stack": "link", "conventions": "link", "architecture": "link" }
}
```

`claude_md_assembly` 以外のトップレベルキーが `HEAD` 版と完全一致することを assert で確認済み。

### `CLAUDE.md`（GSD ブロック 4 つ）

| ブロック | 変更前 | 変更後 |
|---|---|---|
| `project` | `## Project` に概要・Core Value を **embed** | `.planning/PROJECT.md` への参照 1 文（制約 9 項目を列挙して誘導） |
| `stack` | **空** | `## Technology Stack` → `.planning/codebase/STACK.md` |
| `conventions` | **空** | `## Conventions` → `.planning/codebase/CONVENTIONS.md` |
| `architecture` | `## Architectural Constraints` に制約 5 項目を **embed** | `## Architecture` → `.planning/codebase/ARCHITECTURE.md` + 補足 4 本（STRUCTURE / CONCERNS / INTEGRATIONS / TESTING） |

`skills` / `workflow` / `profile` ブロックは `claude_md_assembly.blocks` の対象外のため無変更。CLAUDE.md 前半の手書き部分も無変更。

### `.planning/codebase/ARCHITECTURE.md`

link 化で唯一失われる情報だったヘルパー名を「Blob storage」制約行へ補記した。

> Capture MUST go through `_capture_page_blob(page_i)` and restore MUST go through `self._blob_bytes(data)` (raw `bytes` accepted for backward compatibility).

## 事前調査: 情報損失の有無

CLAUDE.md の `architecture` embed に書かれていた内容がリンク先に存在するかを 1 項目ずつ照合した。

| embed の項目 | ARCHITECTURE.md | PROJECT.md |
|---|---|---|
| Threading（`root.after()` / `_preview_gen` / ThreadPoolExecutor） | あり（**より詳しい** — `PipelineState` の Lock 保護まで記載） | あり |
| Global state（`C` / `_current_font_size`） | あり（`_apply_theme()` / `set_current_font_size()` まで記載） | あり |
| `MAX_UNDO = 20` / デルタ dict | あり | あり |
| Blob ライフサイクル（64KiB 閾値・eviction・redo クリア・close/exit purge・直接 `append`/`clear` 禁止） | あり | あり |
| CropBox safety | あり | あり |
| ヘルパー名 `_capture_page_blob()` / `_blob_bytes()` | **なし → 本タスクで補記** | あり（260812-a8u の Constraints） |

さらに ARCHITECTURE.md は embed になかった項目（PDF open/close のリソースリーク、Pagination window の不変条件）も持つ。
→ **link 化による情報損失はない。むしろリンク先のほうが情報量が多い。**

## トレードオフ（意図的に受け入れた点）

CLAUDE.md 単体では制約の本文が読めなくなり、エージェントはリンク先を開く必要がある。これは numbers/loto が意図的に選んだ設計（CLAUDE.md を薄く保ち、正本を `.planning/` に一元化する）であり、揃えることを優先した。

なお PageFolio の CLAUDE.md 前半には「コーディング規約」「禁止事項」「既知の制限・注意事項」「リリースゲート」が手書きで残っており、**日常的に必要な規約はリンクを開かなくても読める**状態は維持されている。

## 検証

- ARCHITECTURE.md にヘルパー名 2 つが存在することを assert で確認
- 4 ブロックすべてで GSD マーカー対の維持・`##` 見出しの存在・`.planning/` リンクの存在を assert で確認し、**リンク先 8 本すべてがファイルとして実在**することを `os.path.exists` で確認
- `claude_md_assembly` が 3 プロジェクトで同値、他キーは `HEAD` 版と完全一致であることを assert で確認
- `ruff check .` → All checks passed
- `pytest -q --basetemp=...pf_pytest_tmp_adk` → **1404 passed**（失敗 0・ERROR 0・クラッシュなし＝リリースゲート合格。症状①の再発なし）

## 3 プロジェクト比較の最終状態

| # | 差分 | 状態 |
|---|---|---|
| 1 | `config.json` の `git` 3 キー | ✅ 260812-9tv |
| 2 | `PROJECT.md` の `## ブランチ運用` 節 | ✅ 260812-9tv |
| 3 | `PROJECT.md` の `## Constraints` 節 | ✅ 260812-a8u |
| 4 | `## フェーズ完了 DoD` + 機械ゲートテスト | ⬜ 未対応（**loto のみ保有**・テストコード追加を伴う） |
| 5 | `claude_md_assembly` | ✅ 本タスク |
| 6 | numbers `main` への反映 | — numbers 側の `/gsd-complete-milestone` で自動解消 |

## スコープ外

- `skills` / `workflow` / `profile` ブロック（`claude_md_assembly.blocks` の対象外）
- CLAUDE.md 前半（手書きの PageFolio 固有指示書部分）
- `.planning/codebase/*.md` の内容拡充（Task 1 のヘルパー名補記を除く）
- 差分 #4（`## フェーズ完了 DoD` + `tests/test_gsd_dod.py` 相当）

## 申し送り

- **CLAUDE.md の制約は正本が `.planning/` 側に移った。** 今後アーキテクチャ制約を変更するときは `.planning/codebase/ARCHITECTURE.md`（および `.planning/PROJECT.md` の Constraints）を直すこと。CLAUDE.md の GSD ブロック内を手で書き足すと次の assembly で消える
- 残る差分は #4 のみ。loto が `tests/test_gsd_dod.py` で ROADMAP の `Complete` 行と `NN-VALIDATION.md` の status の乖離を機械検知しているもので、**テストコードの新規追加を伴う**ため次マイルストーンの要件として扱うか単発 quick かの判断が要る
