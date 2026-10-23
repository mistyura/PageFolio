---
phase: 05-config-notification
plan: "01"
subsystem: configuration
tags: [settings, tkinter, toast, pytest]
requires:
  - phase: 04-startup-control
    provides: 起動後の非モーダル通知方針とWindows起動回帰試験
provides:
  - 設定読込のok/missing/corrupt/unreadable分類と辞書互換API
  - 破損・読取不能時のApp所有通知と終了自動保存の原本保護
  - 実App・実Toast・PDF操作を通る回帰tracerと読込境界試験
affects: [05-02, 05-03, 05-04]
actuals:
  tokens: 5798
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [App所有の通知イベント, 読込結果statusと辞書互換wrapper]
key-files:
  created: [tests/test_config_notification.py]
  modified: [pagefolio/settings.py, pagefolio/app.py, pagefolio/toast.py, pagefolio/lang.py]
key-decisions:
  - 読込失敗時は例外本文を通知・ログに出さず固定文言と例外型・errnoのみを使う
  - 終了自動保存は読込失敗中にメモリ値の収集より前で止める
patterns-established:
  - 通知イベントはAppのdequeが保持しToastは表示・閉鎖だけを担当する
requirements-completed: []
requirements-addressed: [V110-CFG-01, V110-CFG-03, V110-CFG-04]
commits: 2
plan_head_before: 4f0fb978214f73b565b5ca147d592ccb825d2cfc
plan_head_after: 58f017d6f241ae8d50d12b28692b4a2ba4ad3204
duration: 54min
completed: 2026-10-23
status: complete
---

# Phase 05 Plan 01: 設定読込失敗の通知と原本保護 Summary

破損した設定JSONから既定値で実Appを起動し、画面構築後に期限付きToastを一度表示してPDF編集を続けられる経路を実装した。

## Performance

- **Duration:** 約54分（承認待ちによる中断を含む）
- **Started:** 2026-10-23T06:09:07+09:00
- **Completed:** 2026-10-23T07:03:00+09:00
- **Tasks:** 2
- **Files changed:** 5

## Accomplishments

- `_load_settings_result()` が不存在、破損、読取不能、正常を分類し、既存 `_load_settings()` は辞書を返し続ける。UTF-8 BOM、部分辞書、未知設定キーも扱う。
- App が読込失敗イベントを一度登録し、初回UI完成後に実Toastで通知する。Toastは再試行ボタンなし、10秒の期限と手動閉鎖を持ち、従来のPDF/印刷retry契約を維持する。
- 読込失敗中の `_save_window_state()` は設定値の収集前に終了し、終了確認のYes/NoとDocumentなしの各分岐で原本を上書きせず退避コピーも作らない。

## Task Commits

1. **Task 1: 05-01-01 起動tracerと通知経路:** `be8f78a` — 実App、実Toast、PDF回転、原本保護を実装・検証。
2. **Task 2: 05-01-02 読込境界と終了保護:** `58f017d` — 破損/読取不能/不存在/競合と終了分岐の試験を追加。文言定義を整形。

## Verification

- Task 1 tracer + 既存Toast: 35 passed / 1 warning。通常権限単一全件: **1639 passed / 1 warning / 241.70秒 / exit 0**。記録 `05-01-task1-full.txt`（実行ログ `.log` とSHA256一致）。
- Task 2 局所: 40 passed / 1 warning。通常権限単一全件: **1660 passed / 1 warning / 234.19秒 / exit 0**。記録 `05-01-task2-full.txt`（実行ログ `.log` とSHA256一致）。
- 実Tk tracerのJUnit: 2 passed、`focus_check=verified`。入力可能なEntryへ実フォーカスを取得し、Toast再表示後も同じEntryとgrabなしを確認。`05-01-focus.xml`。
- `ruff check .`、`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"`、再check、`pagefolio.py` のAST解析が成功。
- 制限環境での初回全件は `init.tcl` 読取不能による38 failed / 24 ERRORで失敗した。通常権限で同じ全件を実行して上記のexit 0を確認した。この初回失敗はDEP対象の子process終了期限ではない。

## TDD Notes

- Task 1では実App tracerが `_settings_autosave_blocked` 不在の予定assertionでREDとなり、その後の実装でGREENを確認した。RED単独コミットはAGENTS.mdのコミット前全件成功条件により作っていない。
- Task 2の新しい境界試験はTask 1の実装ですでに通過したため、新たなREDはなかった。対象試験と全件の実測を保持し、REDを捏造しない。

## Deviations from Plan

- Task 1の後に指定フォーマッタを再実行した際、Task 1で追加した `lang.py` 文言の改行整形がTask 2コミットに入った。文言内容は不変。
- Task 2のRED未発生は上記のとおり。その他の機能スコープ変更はない。

## Dependency and Remaining Work

- 親によるWave 1後処理は未完了。実装2コミットは存在するが、SUMMARY・検証証拠の文書コミットは未実施。承認済みの制限外Gitコマンドがプロセス生成時の `アクセスが拒否されました。 (os error 5)` で実行不能となった。最後に確認したindexにはROADMAP、SUMMARY、focus.xmlが含まれ、ROADMAPには開始前からの差分もあるため、そのまま一括コミットしない。
- Wave末ゲートのschema-driftはblock=false、codebase-driftはno-mapped-commitでskip。必須UIゲートはGSD CLI 1.18.0の `query ui.safety-gate` / `query ui safety-gate` / `ui safety-gate` がUnknown commandとなり未検証。hookのonError=haltに従いWave 2未開始。実装は完了しているが、Phase 5完了・Wave末ゲート通過とは扱わない。

- `DEP-05-REGRESSION`は**未充足・原因未確定**のまま。2026-10-23の条件付き実行承認と診断commit `9384268`、事前hash一致を確認した。今回の通常権限全件では同種の子process終了期限失敗は起きていない。成功を依存解除とは扱わず、後続planでも再発時停止を維持する。
- 保存失敗イベントのFIFOと再構築・PDF/印刷通知競合、明示保存での保護解除は05-02以降の担当。V110-CFG-01/03/04の最終要件完了と人手UATはまだ主張しない。

## Self-Check: PASSED

## 2026-10-23 再開時の後処理

- SUMMARY・focus.xmlを `ca052ab` で限定コミットし、開始前のROADMAP等のindexを保持した。
- CLIの実装済み入口は `check ui-safety-gate 5`。旧query名ではなく正式checkを実行しexit 0 / block=falseを確認。Task行形式をパーサー契約へ合わせた後はscopeStatusのdegraded表示も解消した。TkinterのPythonファイルはこのゲートのWeb向けUI判定対象外であり、実Tk検証の代替とはしない。
- `check verify-schema-drift 5`: block=false。`check verify-codebase-drift 5`: no-mapped-commitによるskip。Wave 1の必須ゲートのcommand errorは復旧済み。

変更5ファイル、SUMMARY、検証記録2件、JUnitの存在と、`be8f78a`・`58f017d`がHEADの祖先であることを確認した。台帳基点からの実測コミット数は2。
