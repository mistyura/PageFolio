---
quick_id: 260811-asq
status: complete
description: AGENTS.md と .agents/ の壊れた参照を修正し .gsd ランタイム生成物を gitignore する
date: 2026-08-11
---

# Quick Task 260811-asq Plan

## 目的

Codex 向け指示書 `AGENTS.md` と `.agents/skills/session-handoff/SKILL.md` は、`CLAUDE.md` 系ファイルからの機械的な `Claude` → `Codex` 一括置換で生成されており、置換がディレクトリ名・スキル名・ドメイン名まで巻き込んだ結果、**実在しない参照が 5 箇所**残っている。`.planning/config.json` で `codex` がデフォルトレビュアーに昇格している以上、これらは現役で読まれる指示書であり、壊れた参照は Codex を存在しないパスへ誘導する。

あわせて、GSD のランタイム生成物 `.gsd/dispatch-isolation-sentinel.json` が `.gitignore` のパターン漏れで未追跡のまま残っているため除外する。

## 修正対象（5 箇所）

| ファイル | 行 | 現状（誤） | 修正後 |
|----------|----|-----------|--------|
| `AGENTS.md` | 21 | `pagefolio/AGENTS.md` | `pagefolio/CLAUDE.md` |
| `AGENTS.md` | 99 | `[pagefolio/AGENTS.md](pagefolio/AGENTS.md)` | `[pagefolio/CLAUDE.md](pagefolio/CLAUDE.md)` |
| `AGENTS.md` | 117 | `Codex.ai` | `ChatGPT` |
| `AGENTS.md` | 118 | `.Codex/skills/session-handoff/SKILL.md` | `.agents/skills/session-handoff/SKILL.md` |
| `.agents/skills/session-handoff/SKILL.md` | 9 | `Codex.ai` | `ChatGPT` |

> 176 行目の `generate-Codex-profile` は Developer Profile セクションの管理者注記。GSD の実スキル名は `generate-claude-profile` であり、ランタイムに関係なくこの名前なので実名へ戻す。

## タスク

1. `AGENTS.md` の壊れた参照 5 箇所（表の 4 行 + `generate-Codex-profile`）を修正する。
2. `.agents/skills/session-handoff/SKILL.md` の `Codex.ai` を修正する。
3. `.gitignore` の GSD ランタイム除外ブロックへ `.gsd/dispatch-isolation-sentinel.json` を追加する。
4. `AGENTS.md`・`.agents/` を追跡対象としてコミットする。

## 完了条件

- `grep -n "Codex\.ai\|\.Codex/\|pagefolio/AGENTS\.md\|generate-Codex" AGENTS.md .agents/skills/session-handoff/SKILL.md` が 0 件。
- `AGENTS.md` 内の全リンク先ファイルが実在する。
- `git check-ignore .gsd/dispatch-isolation-sentinel.json` が一致する。
- `git status --short` に `.gsd/` と `AGENTS.md`・`.agents/` が未追跡として残らない。
- `AGENTS.md` と `CLAUDE.md` の差分が「Claude/Codex の呼び分け」のみになり、実在しない参照を含まない。

## 対象外

- `pagefolio/AGENTS.md` の新規作成（`pagefolio/CLAUDE.md` を共用参照する方針とする）。
- `.claude/settings.local.json` が追跡されている件（別課題として申し送る）。
- ソースコード変更なし。したがって `pytest` / `ruff` は非該当。
