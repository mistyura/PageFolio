---
status: investigating
trigger: "$gsd-debug で独立調査して / restart"
created: 2026-10-23
updated: 2026-10-23T13:50:58Z
---

## Current Focus

hypothesis: 原因未確定。原本時系列で一次の終了はfresh fixture準備後・fresh bootstrap前と判明。通常のstop-all/後続ケースからの停止と時計変更を支持する証拠は無い。初回の終了要求stackが無く、WM/ボタン経由のイベントと異常なwatchdog発火を区別できない。利用者の手動終了は否定済み。
test: 承認条件の最終再チェックは対象9件×3回連続成功、単一全件1680 passed / 1 warning / 254.81秒 / exit 0。Ruff・Python102ファイルformat・AST成功。途中失敗を保存し、前景環境と診断の時計比較・Tcl再入を修正した。resume-check-20261023.md参照。
expecting: native_close_receivedにより実WM_CLOSEとTk直接WM呼出しを識別できる。初回の終了要求・未知の送信元PIDの遡及復元はできない。新しい通知試験失敗との因果も未確定。
next_action: 承認された再開条件を全て満たしたため、$gsd-execute-phase 5で05-02-01の既存差分・検証証拠を照合して実装を条件付き再開可。元のowner_missingとDEP-05は未解決・監視継続、出荷承認ではない。再発時は実装・後続実行・コミットを停止して最初の証拠から調査する。05-02未完了・未コミットは維持。本承認は従来の原因確定まで停止する条件を置き換える。

## Symptoms

expected: 同時起動は編集画面1つに収束し、fresh二次起動も同じ一次へ復帰要求できる。
actual: test_simultaneous_real_processes_construct_one_editor[2]のfresh二次がowner_missingでexit 1。
errors: AssertionError: 接続先guardが要求を中断した。guard_blocked=owner_missing、owner_result=acquired。
timeline: 05-02-01の保存・終了制御変更後の初回全件で発生。前回05-01全件1660 passed。変更との因果は未証明。
reproduction: 既存.venvの単一全件pytest、専用basetemp pf_0502_task1_20261023。1674 passed/1 failed、252.25秒。

## Evidence

- timestamp: 2026-10-23T13:50:58Z 条件付き実装再開の再チェックPASS
  checked: resume-check-20261023.md、resume-final-20261023/status.jsonと診断711ファイル（全hash再確認）、最終tracer・runner・静的検証
  found: 最終対象9件×3回成功、全件1680 passed/1 warning/254.81秒。fresh前後の一次生存・応答後のstop_all終了を確認。途中の前景不一致はTerminal→Codeの待機中イベントを実測。Tcl時計でのwatchdog比較へ修正し、診断が追加したnative callbackからのTcl再入を除去。target-3でTcl期限比+11642usとmonotonic期限比-3602.8usを実測した。製品等4ファイルhash不変。
  implication: 利用者の新しい条件を全て満たしたので実装再開は許可。過去の原因未確定を解決扱いせず、DEP-05未解除・出荷不可・再発時停止を維持。今回05-02-02への着手やコミットは行っていない。

- timestamp: 2026-10-23T13:06:34Z 通知前景不一致の切り分け
  checked: notice-focus-20261023.md、保存済みnotice 9プロセスのresult、notice-caseとNativeNoticeLifetime、追加診断の単体証拠19ファイル
  found: 失敗時8 peerの前後は199190、owner終了後134248、通知HWND6295044。表示/破棄前後の既存4値がこの分岐では未保存だったためtracerに保存を追加。単体1 passed/1 warning/2.49秒、今回は6時点全て199190、elapsed1875ms、期限差1800ms。原本と19ファイルのSHA256一致。Ruff check・Python101ファイルformat・AST成功。誤って整形した対象外60文書は原文へ復元。
  implication: 変化区間を切り分ける診断は準備できたが、失敗時のPID/class・イベント時刻を遡及復元できず原因未確定。製品修復・全件再実行なし。最新全件1 failed、Phase停止・未コミット・DEP-05未解除を維持。

- timestamp: 2026-10-23T12:54:47Z 実OS終了経路検証
  checked: tests/test_startup_windows.py、native-audit-20261023.md、native-audit-artifacts/targetedとfullの37ファイル（全SHA256一致）
  found: 親が試験実行PIDと生成時刻を確認してWM_CLOSEを送信。native_close_received→entry_fired/wm→quit_requested→native_observer_removedを実測。Tk直接WM/ボタン/watchdogではnative受信なし。通常同時起動3件もnative受信なし・stop_all=true、7ケース全て解除成功・監査errorなし。全件は1678 passed/1 failed、通知8プロセス試験の前景HWNDが199190から134248へ変化。初期の新規試験2失敗はHWND取得元・launcher PID誤認を修正し、両ログを保存した。
  implication: 承認された実OS経路検証は完了。初回owner_missingは未再現・未解決。通知試験の新失敗は原因未確定で環境要因と断定せず、修復や再実行で消さない。製品4ファイルhashは不変、Phase停止・未コミット・DEP-05未解除を維持。

- timestamp: 2026-10-23T12:30:59Z 終了入口監査と独立検証
  checked: tests/test_startup_windows.py、entry-audit-20261023.md、entry-audit-artifacts/の6 JSONL（原本SHA256一致）
  found: WM/ボタンは元Tcl commandへ委譲、watchdogは既存10000msを維持して登録/発火を記録。独立3試験は3 passed/19.08秒。単一全件は1678 passed/1 warning/266.92秒/exit 0。通常同時起動3ケースは全てstop_all=true・stop_poll経由。初回sandbox3 failedはinit.tclアクセス不可で、通常権限では成功。
  implication: 入口監査の動作を確認したが初回owner_missingは未再現。製品4ファイルhashは従前一致、製品修復なし。Ruffはsandbox生成物ディレクトリだけを走査除外して101 Pythonソースを検証。原因未確定・Phase停止・DEP-05未解除・未コミットを維持し、次の調査方針のcheckpointへ。

- timestamp: 2026-10-23T12:11:30Z 継続調査・原本時系列と追加3仮説
  checked: simultaneous-owner-missing-evidence/forensics-20261023.md、元basetempの3ケースのmetadata（昇格読み取りのみ）、Systemイベント、startup_focus/startup_win32/__main__/appとtracerの停止経路
  found: ready=11:43:01.182Z→初期二次result=.308Z→fresh fixture=.412Z→一次設定保存=.498Z→一次result=.581Z→fresh bootstrap=.793Z→owner_missing=.866Z。失敗ケースにはstop/stop-all無し、後続ケースのstop-allは別パス・6秒以上後。失敗前後5分のSystemイベント0件、復帰処理にroot破棄やclose送信なし。製品4ファイルと診断テストのhashは従前と一致。
  implication: 一次はfreshの所有権確認前に終了したが、fresh準備前に終了したわけではない。通常のstop-all共有・時計変更・復帰要求の直接closeを支持せず、入口別イベントまたは再発stackが必要。コード変更・試験反復・commitなし、調査は未解決。

- timestamp: 2026-10-23 診断付き全件と上限10回の対象試験
  checked: simultaneous-owner-missing-evidence/full-01.txt、campaign.txt、専用basetemp pf_owner_missing_full_01
  found: 全件1675 passed / 0 failed / 0 ERROR / 2 warnings / 242.80秒 / exit 0。上限10回の[2]は10/10成功（各3.84〜4.33秒）。全件のsimultaneous 3ケースはexit-auditにstop_poll→_quit、stop_all=trueを記録。初回失敗は再現しなかった。
  implication: 診断の出力を確認したが、初回の原因修復の証拠は得られていない。警告はPyMuPDF ByteString非推奨とtest_ocr_engine.pyのTcl interpreter別thread破棄で、今回失敗との因果は不明。

- timestamp: 2026-10-23 独立調査
  checked: 利用者回答、初回の隔離settings.json、tests/test_startup_windows.pyの終了経路
  found: 利用者はテスト中に閉じていない。初回一次の設定には終了時に保存するwindow_geometry/edit_mode/sashがあり、_quit経由の可能性が高い。stop-allはfresh二次の検証後にだけ作られる。子プロセスは別fixtureと独立したTkを使う。
  implication: 手動終了を原因と断定できない。正常終了要求の呼出元を捕捉するため、simultaneous系のTracedApp._quitだけにexit-audit.jsonlを追加した。製品コードと終了期限は変更していない。

- timestamp: 2026-10-23 診断付き単体
  checked: owner-missing-probe-01.log、専用basetemp pf_owner_missing_probe_01
  found: 対象[2]は1 passed / 1 warning / 4.48秒 / exit 0。再現なし。
  implication: 単体成功で原因解決とは扱わず、初回と同じ全件の前後関係を確認する。

- timestamp: 2026-10-23 初回全件
  checked: .planning/phases/05-config-notification/05-02-task1-failure（manifest.jsonで原本とのSHA256一致）
  found: 一次constructed=1/restored=1/result=primary/elapsed=3438。ready_tick-started_tick=3031。後続二次はowner_missing。通常の一次watchdogはApp構築後10000msなので単純な期限到達では説明できない。
  implication: 一次は例外終了せずmainloopを抜けている。元のDEP-05 communicate timeoutとは異なる失敗として調査する。

## Eliminated

- hypothesis: 後続の同時起動[8]/[slow]ケースの通常stop-allが失敗[2]の一次を閉じた。
  evidence: 原本の親ディレクトリはprocess0/process1/process2に分離され、後続stop-allの最早作成は11:43:07.472Z。失敗一次resultは11:43:01.581Z。パスと順序が成立しない。外部による一時作成・削除までは未監査。

- hypothesis: 利用者が試験ウィンドウを閉じた。
  evidence: 利用者回答「閉じていない」。外部ソフトやOSからの終了要求までは検証できていない。
- hypothesis: 通常の試験watchdogが予定どおり10秒経過して終了した。
  evidence: 初回一次のelapsed=3438msはApp構築後10000msの予定時刻より短い。時計/タイマー異常の有無は未確定。

## Resolution

root_cause: 未確定。初回の呼出stack欠落により、どの終了要求が一次を閉じたかを遡って実証できない。
fix: 製品修復なし。前景WinEvent監査・一次生存assert・非表示検証runnerを追加。診断の時計比較はTcl時計へ揃え、native callbackからTkを再入呼出ししないよう修正。期限・guard・元の製品合否条件は維持。
verification: 最終対象9件×3回連続成功、全件1680 passed/1 warning/254.81秒/exit 0。Ruff check、Python対象format（102 files unchanged）、AST3ファイル、diff --check成功。診断711ファイルのSHA256一致。Ruffはアクセス不可のsandbox生成物1ディレクトリだけを走査除外。製品等の既存4ファイルhashは初回失敗時から一致。
files_changed: tests/test_startup_windows.py、本debug記録・証拠、開発履歴.md。STATE/state.json/05-02-CHECKPOINTに実OS検証結果と全件の別失敗を記録し、先行差分とともに未コミットで保持する。
disposition: unresolved/monitoring。resolvedへ移動しない。DEP-05-REGRESSIONも未解除。利用者承認の条件を満たしたのでPhase 5実装は条件付きで再開可、出荷は不可。05-02-01は未コミットで、次のexecute-phaseで既存作業を照合する。同種失敗の再発時は再停止する。

## 実行commandと証拠hash

```powershell
.venv/Scripts/python.exe -m pytest 'tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor[2]' -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_probe_01"
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_full_01"
# 上限10回: 同じ[2]をpf_owner_missing_trial_1〜10の専用basetempで実行。失敗時打切り。
```

Windows通常権限、既存.venv Python 3.15.1。依存更新なし。全件のフィルタ/除外/skipなし。

| 対象 | SHA256 |
|---|---|
| tests/test_startup_windows.py | DC34E678D69EEA86EE53E9399BB3EEC57AC5C3EB08C8ED36998A74A4CDE8ECB4 |
| full-01.txt（元logと同一） | 002F4802E5AD78608CF641A49FDD06996BA22A6E524A2195394DD6064459279E |
| campaign.txt（元logと同一） | 725EA41A9F03CB56AE66A54CC077F7B0997B45567AF0887F733DF68F2148011D |

元の失敗証拠は05-02-task1-failure/と05-02-task1-full.logを保持。成功ログで置換しない。
