# 条件付き実装再開の再チェック（2026-10-23）

## 判定

**PASS — Phase 5の実装を条件付きで再開可。出荷承認ではない。**

利用者は「一次の生存確認」「通知前景イベント監査」「対象3回連続成功」「全件1回と静的検証成功」を条件として、原因未確定のまま実装を進めることを承認した。従来の原因確定まで停止する条件を置き換える。owner_missing・DEP-05はinvestigating/monitoringのまま残し、修復済み・resolved扱いにしない。再発時は実装・後続実行・コミットを停止し、最初の失敗証拠から調査する。

| 条件 | 実測結果 |
|---|---|
| 一次の生存・編集画面1つ | 同時起動[2]/[8]/[slow]でfresh前後の生存、constructed合計1、同じownerへの応答を確認。終了要求はfresh完了後かつstop_all=true |
| 前景イベント監査 | EVENT_SYSTEM_FOREGROUNDを受信し、時刻・HWND・PID・classを記録。実window表示eventで受信経路を独立検証。全ケースで解除成功 |
| 対象3回連続 | 各9 passed / 1 warning、44.83秒・45.28秒・45.96秒 |
| 単一全件 | 1680 passed / 1 warning / 254.81秒 / exit 0 |
| 静的検証 | Ruff check成功、Python対象format 102 files left unchanged、pagefolio.py/tracer/runner AST成功、diff --check成功 |

全件は除外・skip・期限延長なし。`-x`は失敗時打切り用で、最終全件は失敗なしで全1680件を実行。既存警告はPyMuPDF ByteString非推奨。

## 変更

- `tests/test_startup_windows.py`: 同時起動のfresh前後の一次生存をassertし、終了要求が応答完了後であることを検証。試験内の前景WinEvent監査を追加。タイトル・入力内容は取得せず、同一threadで登録・解除しcallbackを強参照する。NativeNoticeLifetimeの既存表示/破棄前後値とともに診断を保存する。
- 終了入口監査の期限比較は、Tcl 9.0.4のafterが使うTcl時刻へ統一。Python monotonicも診断として保持する。watchdogは10000msのまま、期限前の発火を許す誤差幅は加えていない。
- `run_resume_check.py`: 非表示pythonwランナーからCREATE_NO_WINDOWでpytestを実行。開始前のみ、console以外の同じ前景が2秒安定したことを確認する（上限30秒、未安定なら試験開始前に失敗）。前景変更・強制focusは行わない。対象3回→全件1回、最初の失敗で停止し、診断をコピーしてSHA256一致を確認する。
- 製品コード・requirements・版番号は今回変更なし。app.py/settings.py/test_config_notification.py/test_settings_keyguard.pyは05-02-CHECKPOINT記載の先行変更時hashと一致。

## 途中失敗と対処（成功で上書きしない）

1. `resume-check-20261023/target-1.txt`: 1 passed / 1 failed。通知前景が199190→134248。EVENT_SYSTEM_FOREGROUNDで、WindowsTerminal PID30308からCode PID27368へ、通知待機中の7518203tickに変化した。表示前後は199190、破棄前後は134248。通知HWNDは854114。どの主体が前景変更を要求したかまでは特定していない。実行環境の切り分けとして非表示起動と前景安定確認を採用した。
2. `resume-hidden-20261023/`: 1回目9 passed、2回目7 passed / 1 failedで打切り。watchdog監査のPython monotonic比較で予定時刻より0.2431ms早いとして失敗した。Tcl afterはTcl_GetTimeから絶対期限を作る一方、テストは別時計のmonotonicを厳密比較していたため、同じTcl時計での期限検証へ修正した。
3. `resume-clock-fixed-20261023/target-1.txt`: 8 passed / 1 failed。時計を共通監査関数で取得したため、native WM_CLOSE受信callbackからTk/Tclへ再入し、PyEval_RestoreThreadのGIL fatal errorが発生。Tcl取得をTk起点のWM/ボタン/watchdog callbackと登録処理に限定し、native受信callbackからのTk呼出しを除去した。診断追加時の不具合として記録する。
4. 最終`resume-final-20261023/`: 修正後コードで対象9件×3回、全件1680件をすべて成功。native WM_CLOSEを対象セット先頭に移して修正経路を先に検証した。

最終target-3のwatchdogはTcl予定時刻に対して+11642usだったが、Python monotonic予定時刻に対して-3602.8usだった。同一実行で時計間の差を実測しており、旧比較なら依然不合格になる。修正は単なる反復で成功を得たものではない。初回owner_missingの約3.4秒終了とは規模が異なり、同一原因と断定しない。

## 証拠

`resume-final-20261023/status.json`に実行command・終了値・時間・保存数。各targetに96ファイル、fullに423ファイル、合計711ファイルを原本とSHA256一致で保存し、コピー後も全hashを再検証した。原本の専用basetempは保持。過去の失敗ログも保持する。

最終通知監査は3対象回と全件のいずれも前景199190で開始・終了、観測中のforegroundイベントなし、observer解除成功。これは観測区間の結果であり、未知の送信元PIDや過去の終了要求を復元したものではない。

tracer SHA256: `b3a4afcb619284e572628c2925af3af4680c424139a8734861712e73355aaa24`。

## 根拠・限界

- [SetWinEventHook](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwineventhook)、[WINEVENTPROC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nc-winuser-wineventproc)、[UnhookWinEvent](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-unhookwinevent): event時刻・window情報を受信。同じthreadのmessage loopで処理して解除する。
- [Tcl 9.0.4 tclTimer.c](https://raw.githubusercontent.com/tcltk/tcl/core-9-0-4/generic/tclTimer.c): afterの期限生成と発火判定はTcl_GetTimeを使う。[Tcl clock](https://www.tcl-lang.org/man/tcl8.7/TclCmd/clock.html)のmicrosecondsはepoch基準の時刻で、Python monotonicとは別の時計。
- 非表示実行と開始前安定確認は、測定環境を整える対処。共有desktopへの将来の外部入力を排除するものではない。次回同じ前景assertが失敗しても、無条件に環境要因として捨てない。
- 未実施のWindows EXE/UATや未解決の根本原因を、この結果で合格・解決扱いにしない。

## 再開位置

`$gsd-execute-phase 5`で05-02-01の先行差分と本証拠を照合し、必要なGSDゲートを経てコミット・後続へ進める。05-02自体は未完了でSUMMARYは未作成、今回コミット・05-02-02着手は行っていない。コード・依存・環境が変わっていない成功済み検証は再利用し、変更後の必要な検証は省略しない。
