# 実OS終了経路の検証（2026-10-23）

利用者は再発待ちから方針変更し、選択1「実OS経路の検証」を承認した。初回owner_missingの再現・原因修復ではなく、受信監査がWindows経由とTk直接呼出しを識別できるかの検証である。

## 変更

- `tests/test_startup_windows.py` のsimultaneous系TracedAppだけに、同じUIスレッドでSetWindowSubclassを登録。WM_CLOSE受信を記録し、全メッセージをDefSubclassProcへ渡す。WM_NCDESTROYで登録を解除し、callbackのPython参照をアプリ生存中保持する。
- 独立した試験が作成したfixtureの実行PIDと生成時刻を照合して、親から対象HWNDにPostMessageW(WM_CLOSE)を1回送る。ランチャーPIDと実行PIDは別記録。ブロードキャストや実ユーザーのPageFolioを対象としない。
- 受信→Tk WM入口→_quit→登録解除の順序、正常終了、終了時設定保存、watchdog期限前、stop/stop-all無しを検証する。既存の直接WM/Tkボタン/10秒watchdogの3試験ではnative_close_receivedが無いことを検証する。
- タイムアウト、guard、既存同時起動の合否条件、製品コード、依存、版番号は変更しない。版番号同期は既存05-CONTEXTのPhase 6境界を維持する。

## 対象試験と修正経過

1. 初回4件: 1 failed / 3 passed / 1 warning / 22.60秒。新規試験のready.snapshot.hwnd参照がKeyError。送信前の試験実装誤りであり、owner_missing再発ではない。`native-targeted-20261023.txt`。
2. HWNDを登録監査から取得した1件: 1 failed / 1 warning / 3.49秒。HWND所有PID 16244とPopenのlauncher PID 28564が異なり、安全確認で送信前に停止。`native-targeted-fixed-20261023.txt`。試験fixtureが公開する実行PID・生成時刻の照合へ修正した。
3. 修正後1件: **1 passed / 1 warning / 3.45秒 / exit 0**。`native-targeted-pid-20261023.txt`。製品動作を修正した成功ではない。

すべて通常Windows権限・既存.venvで実行。各回で別basetempを使用し、失敗ログと原本は上書きしない。

## 実測された順序（単体成功）

送信PID=9128、launcher PID=3124、対象実行PID=26688、HWND=3345056。

| event | monotonic（秒） |
|---|---:|
| test_native_close_post（送信前記録） | 5576.0393039 |
| native_close_received | 5576.1129828 |
| entry_fired / wm | 5576.1145971 |
| quit_requested | 5576.1151424 |
| native_observer_removed / removed=true | 5576.1912848 |

resultはprimary、constructed=1、restored=0。監査登録時のwatchdogは10000ms。試験専用の意図的終了が通常の終了保存を通ることを確認した。

原本 `LOCALAPPDATA/Temp/pf_owner_native_pid_20261023/test_simultaneous_exit_audit_n0/simultaneous-audit-native-wm/` の6ファイルを `native-audit-artifacts/targeted/` にコピーし、全SHA256一致を確認した。manifest.jsonが原本パスとハッシュを持つ。

## 検証の限界

- 初回失敗にnative受信監査は存在しない。初回がWM_CLOSEだったことや送信元PIDは遡及して証明できない。
- 今回のsender_pidは試験の既知の送信元。WM_CLOSE受信だけから未知の送信元を特定したものではない。
- Tcl直接WMプロトコル呼出しと実WM_CLOSEを区別できても、WM_CLOSEのない終了にはボタン、タイマー、直接呼出し等が残る。
- 受信監査による時間変化はあり得る。通常試験の成功を元不具合の修復と扱わない。
- Phase 5停止、05-02-01未完了・未コミット、DEP-05未解除を維持する。

## API根拠

- [SetWindowSubclass](https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-setwindowsubclass): 同一thread内で登録しcallbackの生存を呼出側で管理。
- [DefSubclassProc](https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-defsubclassproc): 次のhandler、最後には元のwindow procedureへ委譲。
- [RemoveWindowSubclass](https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-removewindowsubclass): 同じcallbackとIDで解除。
- [PostMessageW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew): 対象windowを作成したthreadのqueueへ投稿する。

## 全件・静的検証

Ruff check成功、Python対象の全体formatは101 files unchanged、pagefolio.pyとtracerのAST成功、git diff --check成功。前回と同じアクセス不可sandbox生成物1ディレクトリだけをRuff走査から除外し、ソース除外・pyproject変更なし。

全件pytestは専用basetemp `LOCALAPPDATA/Temp/pf_owner_native_full_20261023` で1回実行し、**1678 passed / 1 failed / 1 warning / 274.31秒 / exit 1**。フィルタ・除外・skip・期限変更なし。新規実OS入口1件、既存入口3件、通常同時起動3件はいずれも成功。7ケース全てobserver解除成功・native_audit_error無し。通常同時起動3件はnative受信なし、stop_all=trueだった。

失敗は `test_notice_dedup_eight_processes_keep_original_deadline` の前景HWND比較（199190→134248）。owner_missing、communicate timeoutの再発ではない。該当notice-case分岐はTracedAppの新監査を使わないが、全件内の間接影響や外部の前景変更を除外したことにはならない。利用者操作・環境要因・製品原因のいずれも断定しない。owner resultのelapsed=1860ms、通知の期限差=1800ms。assert到達前の8 peerのacquired=falseとsnapshot一致は通過している。前景assert後の期限assertは未実行であり、試験全体は不合格のまま。

失敗ケースの19診断ファイルと成功7ケースの12ファイル、計31ファイルを `native-audit-artifacts/full/` にコピーして全SHA256一致確認。元の専用basetempと最初の失敗ログを保持し、無根拠の再実行はしない。全件ゲート未通過としてPhase 5停止・未コミットを継続する。

| 対象 | SHA256 |
|---|---|
| tests/test_startup_windows.py | AE6E493156CBEBEBFE0F257D676483E7C71CDD92930537EECCDA78A0690DC020 |
| native-full-20261023.txt | 8EDD100205F5DBEBCB7761F5412A46D04B3500E99B3F6CD7E485163B471C49AF |

pagefolio/app.py、pagefolio/settings.py、tests/test_config_notification.py、tests/test_settings_keyguard.pyは初回失敗時からSHA256一致を再確認した。
