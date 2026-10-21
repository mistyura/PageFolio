---
phase: 04-startup-control
plan: "05"
status: complete
subsystem: testing
tags: [windows, startup, acceptance]
requires: [04-01, 04-02, 04-03, 04-04]
provides: [起動経路横断受入, 実機受入のPhase6移管追跡]
affects: [06-release-validation]
tech-stack:
  added: []
  patterns: [自動実証と人手未実施の分離]
key-files:
  created: [.planning/phases/04-startup-control/04-WINDOWS-UAT.md, .planning/phases/04-startup-control/04-05-EVIDENCE.json]
  modified: [tests/test_startup_windows.py, .planning/phases/04-startup-control/04-VALIDATION.md]
requirements-completed: [V110-START-01, V110-START-02, V110-START-03, V110-FOCUS-01, V110-FOCUS-02]
key-decisions:
  - 承認済み再計画に従い未実施のW人手受入をPhase6へ移管しリリース停止条件を維持する
duration: 中断を挟む継続実行
completed: 2026-10-22
actuals:
  tokens: 15722
  tasks: 2
  commits: 3
plan_head_before: b26ddec8bd056ae66d0ac23788f33894408ed42f
plan_head_after: 3df02b2431a73f58bb5813297ee980e75d1fa55b
---

# Phase 4 Plan 5: 起動経路横断受入と移管証拠の照合 Summary

両Python入口・別配置の一次/二次9組と期限失効を実証し、W01〜W12の未実施人手受入をPhase 6のリリース停止条件へ対応付けた。

## 完了タスク

| Task | 内容 | Commit |
|---|---|---|
| 04-05-01 | 起動経路横断試験と明示実機harness、実測正本の整備 | 7ea8fb4 |
| 04-05-02 | 自動受入のhash/祖先関係と全W移管表を照合 | 本SUMMARYと検証監査の文書commit |

Task1の再実装なし。tested_fileのSHA-256はD5749E4B163FADD4988B4FD797592AFAD204A1B47077CF27D5C383D20B0C8A57でEVIDENCEと一致し、7ea8fb4はHEADの祖先。製品基準b26ddec、試験commit7ea8fb4、承認済み再計画3df02b2を区別した。

## 検証結果

- Task1: 局所140 passed/0.61秒、指定Windows受入6 passed/22.23秒、単一全件1603 passed/212.88秒（警告1、失敗/ERROR/skipなし）。ruff/AST成功。数値正本は04-05-EVIDENCE.json。
- Task2: tests/test_gsd_dod.pyは19 passed/1 warning/0.59秒。sandbox一時領域拒否後、正規昇格で成功。
- SUMMARY→Progress後にvalidate-phaseをインライン実走。既存VALIDATIONのState A監査、5要件/11タスクの対応を確認し自動ギャップ0。起動関連とDoD/i18nは204 passed/1 warning/190.22秒、追加テストなしでvalidatedへ更新。
- VALIDATION更新後の単一全件pytestは1603 passed/1 warning/209.19秒、失敗/ERROR/skipなし。120秒目標超過を保持。親の正式Phase完了とDoD再確認はこの後に行う。
- W01〜W12の人手未実施は06-UAT-CARRYOVER.mdの全行へ対応し、全必須passまでV110-QA-02のリリース停止を維持する。
- SUMMARY後のProgress更新、validate-phase実走、VALIDATION更新、単一全件pytest、親による正式完了とDoD再確認の順を適用する。本SUMMARYのcompleteは計画実行の完了であり、Phase正式完了や実機合格を意味しない。

## Deviations from Plan

- 2026-10-22の明示承認でTask2のblocking-human条件を再計画し、実機受入をPhase6へ移管（3df02b2）。機能契約の免除なし。
- Task1のREDはowner role未配線によるharness失敗で、製品未実装の正当なREDとは主張しない。既存挙動の試験拡張で製品コード変更なし。AGENTSの全件成功前commit禁止を優先しRED単独commitなし。

## 未解決・引継ぎ

- W全人手部分not-run、W11は別アカウント準備不能。実EXEはPhase6担当。
- W07bの並行負荷15609ms（15.5秒を109ms超過）と単独15140msを両方保持。任意負荷時の上限保証へ外挿しない。
- 禁止事項3件flagged-unverified、edge5件unclassified/unresolvedを保持。自動resolvedにしない。
- 新依存/pyproject/製品CLI/版情報変更なし、新しい信頼境界なし、Known Stubなし。
- requirements-completedは計画宣言IDの被覆メタデータであり、最終実機受入の完了を意味しない。要件台帳は親のShared-ID判定後に更新する。

## Self-Check: PASSED

Task1の5成果物・本SUMMARY・Phase6移管正本の存在、7ea8fb4の祖先関係、試験SHA-256一致を確認。actuals.tokensは既存Task1実diff文字数/4の15722を継承し、最終文書commit前に差分から再計測する。commitsは永続ledgerのbaseからHEADまでgit rev-listで実測した3件（中断記録・承認済み再計画を含む）。
