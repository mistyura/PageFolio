---
phase: 04-startup-control
plan: "06"
status: complete
subsystem: startup
tags: [win32, startup, notice, cleanup, gap-closure]
requires:
  - phase: 04-04
    provides: 非活性のnative案内、NoticeLease、初回期限
  - phase: 04-05
    provides: 隔離済みWindows subprocess受入
provides:
  - 起動backendの構築失敗から独立通知への有限な経路
  - 部分初期化と通知障害時の資源解放・診断境界
  - CR-01の名前付き回帰と実行証拠
affects: [04-startup-control, 06-release-validation]
tech-stack:
  added: []
  patterns: [通知専用Win32基底, 取得直後の資源登録, 同一名の通知lease共有]
key-files:
  created:
    - .planning/phases/04-startup-control/04-06-EVIDENCE.json
  modified:
    - pagefolio/__main__.py
    - pagefolio/startup_win32.py
    - pagefolio/startup_notice.py
    - tests/test_startup_notice.py
    - tests/test_startup_windows.py
key-decisions:
  - 起動backend未完成時は既存の起動所有権を推定せず、通知専用backendを一度だけ作る
  - 通知同期・表示・解放を確認できない場合はnotification_unavailableを返す
  - 版情報と人手Windows/実EXE受入は承認済みのPhase 6へ維持する
requirements-completed: [V110-START-02, V110-START-03]
actuals:
  tokens: 10239
  tasks: 2
  commits: 2
commits: 2
plan_head_before: ff8b9355b8bbdbf5fb92b056bdba47b6adfb9bdf
plan_head_after: cc45bd7de98451ef50879620abc4e8cca527d843
duration: "実行開始時刻未記録（全件試験2回の実測は214.36秒/227.59秒）"
completed: 2026-10-22
---

# Phase 4 Plan 6: 起動backend構築失敗の独立通知 Summary

Win32Backendの構築例外を編集画面生成前にcheck_failedへ分類し、通知専用のWin32NoticeBackendから既存の非活性案内を表示できるようにした。通知そのものが使えない場合はnotification_unavailableを返し、両Python入口は終了値1とする。

## 完了タスク

| Task | 内容 | Commit |
|---|---|---|
| 04-06-01 | 起動入口、独立通知基盤、実mainからnative窓への回帰 | `216304e` |
| 04-06-02 | 部分初期化と通知障害の解放、旧新8process集約、証拠 | `cc45bd7` |

通知用基底は起動owner・mapping・pipeを作らず、既存の正規prefix、SID/LUID、ACL、NoticeLease、NativeNoticeLifetimeを共有する。起動側のdescriptor生成が途中で失敗した際は取得済み資源を逆順に解放する。通常closeで一部の解放が失敗しても残りを試し、失敗結果を送出する。

## 検証結果

- RED: `test_backend_constructor_failure_uses_independent_notice`と`test_initialization_notice_factory_failure_is_finite`は旧mainの未捕捉例外を結果assertionで再現。初回の引数TypeErrorは採用せず試験を直して再実行。Task 2の部分解放は`released=['pipe']`と期待`['pipe','mapping','owner']`の差でRED。`tdd-red-evidence`機械判定は実行していない。数値・コマンドの詳細は04-06-EVIDENCE.json。
- Task 1の単一全件pytest: **1609 passed、警告1、214.36秒**。Task 2の単一全件pytest: **1629 passed、警告1、227.59秒**。いずれも終了値0で失敗/skipなし。
- Task 2の関連6ファイル164 passed、Windows選択15 passed、通知単体61 passed。実mainからnative窓1・編集画面0・表示/閉鎖前後のforeground HWND不変、両入口の通知不能exit1、旧新順序を替えた8processの初回期限固定と表示1、後続のowner再取得をassertした。
- `.venv/Scripts/ruff.exe check .`、`ruff format .`、pagefolio.pyのAST解析、EVIDENCE.jsonのJSON解析はいずれも終了値0。対象ソース/試験5ファイルのSHA-256は証拠JSONと一致した。

製品既定の10000msと9999/10000境界は既存fake clock試験で確認し、今回の通常pytestのnative窓は150ms（8processの先頭は1800ms）へ短縮した。この試験から任意負荷時の15.5秒上限を保証しない。

## Deviations from Plan

- AGENTS.mdの「コミット前にpytest」へ従い、REDだけのコミットを作らず、各タスクのGREEN後に全件合格してからコミットした。
- REDの対象assertion失敗は確認したが、TDD referenceの`gsd_run check tdd-red-evidence`は実行していない。実際のREDコマンドと終了値を証拠JSONに記録し、機械判定済みとは扱わない。
- 04-06-01で後続の両入口・8process・再起動試験の土台を同じ5ファイルへ先に追加した。04-06-02で故障matrixと旧新経路の相互集約を完成した。

## 残課題と引継ぎ

- CR-01の独立code reviewとgoal-backward再検証、validate-phase実走、Phase 4正式完了・DoD再確認は親のcloseoutに残す。旧VALIDATION/VERIFICATION/REVIEW-DISPOSITIONの結論は本計画だけで変更していない。
- W01〜W12人手部分、別session・UAC/DPI・実EXEは06-UAT-CARRYOVER.mdでnot-runのまま。WR-01は並行負荷15609msと単独15140msを保持する。禁止事項3件とedge5件の未解決状態を変更していない。
- 版番号、README、開発履歴の同期は現行CONTEXTに従いPhase 6の責務とする。

## Self-Check: PASSED

EVIDENCE.jsonと対象5ファイルの存在、2コミットのHEAD祖先関係、対象SHA-256、開始HEADからのコミット実測2件、stub検索0件、全受入試験の終了値を確認した。
