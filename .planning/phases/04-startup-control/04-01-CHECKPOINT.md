---
phase: 04-startup-control
plan: "01"
status: awaiting-human-verification
type: checkpoint:human-verify
gate: blocking-human
current_task: 04-01-03
completed_tasks: [04-01-01, 04-01-02]
task_commits: [8b5b304, 282d8fe, de27654]
branch: feature/v1.10.0
use_worktrees: false
next_plan_allowed: false
created: 2026-10-21
---

# 04-01 — 方式成立性の実機確認待ち

**進捗: 2/3 tasks。04-01/Phase4をcomplete・validatedへ変更しない。**
SUMMARYは最終Task3完了後に作成する。要件をCompleteにせず、04-02を開始しない。

## 完了した作業

| Task | 内容 | commit |
|---|---|---|
| 04-01-01 | 未完了liveと正式完了/検証待ちのDoDを区別。archive義務と空走査ガードを維持 | 8b5b304 |
| 04-01-01 補強 | 途中ProgressとSUMMARY件数の整合・太字なしPhase行を検査 | 282d8fe |
| 04-01-02 | 型付きWin32所有権/IPC/取消し寿命、実main→Tk→terminal、非活性通知と隔離試験 | de27654 |

## 検証済み

- ruff check: All checks passed!
- ruff format: 成功。整形後のcheckと試験を実行。
- pagefolio.py AST: AST OK。
- 単一全件pytest: **1437 passed / 1 warning / 68.31秒**。
- 計画指定Windows tracer: **14 passed / 1 warning / 37.46秒**。
- 元設定/2種プロンプト: 全試験・各spawn子の存在/SHA-256が不変。
- UAC、別sessionログイン、クリック待ちは通常pytestに含めていない。
- 対象commitの削除ファイルなし。既存未コミットplanning変更はそのまま保持。

実測と手動試験の実行方法は [04-TRACER-EVIDENCE.md](04-TRACER-EVIDENCE.md) を参照。
同時二次の実測terminalはforeground_deniedであり、OSによる前面化成功とは扱わない。

## 現在の停止理由

計画04-01-03の `gate="blocking-human"`。
A3の実際のクリック/入力維持、A4の権限差全資源、固定本番名が未実施である。
自動pytestの成功やworktree無効化の承認は、この実機ゲートの代替にならない。

## 再開手順（実行担当が自動化を準備する）

1. 専用の対話セッションで、`_spawn` により一時fixtureを準備する。
   namespaceを試験ごとのUUIDにして通常/昇格の両子で共有する。
   `_test_scenario_bootstrap` は設定・2種プロンプト・pluginsを子ごとに隔離し原本hashを確認する。
2. **A3:** 利用者が他アプリで入力を続けてからnotice-manualを開始する。
   利用者は案内の「閉じる」を実際にクリックし、入力先が変わらないか確認する。
   notice-timerでも別runを行い、10秒自動閉鎖と入力継続を確認する。
   ready/result.jsonのforeground HWND・shown_tick・closed_tickと目視結果を保存する。
3. **A4:** manual-ownerを通常、manual-secondaryを昇格して実行する回と、
   ownerを昇格、secondaryを通常にする回を別runで行う。
   実行担当は `Start-Process -Verb RunAs -WindowStyle Hidden` を使用し、利用者はUACへ応答する。
   resource-audit.jsonのSID/LUID/session、owner判定、mapping snapshot、terminal、notice leaseを
   **両順序・4資源ごとに**転記する。失敗は資源名とWinErrorを残して停止しACLを広げない。
4. **固定本番名:** namespace=fixed-productionのpreflightを先行する。
   既存/不明ownerがあれば無関係なwindowへ作用せず中断する。
   安全を確認できた専用セッションで同じmain/固定名の試験を行う。
5. A1/A2/A5の自動結果と公式時計仕様も確認し、A1〜A5の実機欄を根拠付きで確定する。
   fail/not-runが1件でもあれば後続04-02は開始しない。
6. 計画指定tracer、必須全件pytest等を再確認する。Task3完了後にSUMMARYを作成し、
   自己検証・状態/進捗更新・共有requirement ready-idsの手順へ進む。

## 留意点

- REDの失敗は実測したが、AGENTS.mdのコミット前全件pytest成功を優先してREDコミットを作らなかった。
  機械判定済みRED evidenceもない。最終SUMMARYでTDDゲート完全遵守と書かない。
- claim前import除去のため、pagefolio/__init__.pyの既存公開APIを遅延再export化した（Rule2）。
- 一度だけ既存OCR試験中のTk解放警告を観測。最終実行では未再現。
  詳細はdeferred-items.md。通常のPyMuPDF非推奨警告は継続している。
- 版情報・README・開発履歴・実配布EXEの統合は計画どおりPhase6担当。

## 永続記録の自己検証: PASSED

Task1/2の3コミットと対象ファイルの存在を確認した。
04-01-SUMMARY.mdは存在せず、完了を偽っていない。
