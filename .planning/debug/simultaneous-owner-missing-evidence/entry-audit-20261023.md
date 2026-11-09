# 終了入口監査の追加と検証（2026-10-23T12:30:59Z）

原因未確定。初回owner_missingとDEP-05 communicate timeoutは解消扱いにしない。調査の製品コード変更・コミット・Phase再開なし。

## 変更と観測範囲

`tests/test_startup_windows.py`のsimultaneous系に限定して、WM_DELETE_WINDOW/終了ボタンの元のTcl commandを保持したラッパーを追加。`entry_registered`/`entry_fired`を記録する。watchdogの登録ではafter ID・登録monotonic・due_monotonic・delay_msを記録し、通常10000ms・手動/UAT120000msを維持。既存quit_requestedのtick/monotonic/stop/stop_all/stackを保持した。

独立3ケースは試験が所有するfixture内だけでWMプロトコルcommandを呼出し、終了ボタンinvokeを行い、watchdogは10秒の自然発火を待つ。意図的呼出しはtest_triggerイベントを残す。WMケースは登録済みTcl commandの経路検証であり、実OSのWM_CLOSE送信元を再現・同定する試験ではない。各ケースで入口が1つだけ発火し、元の正常終了まで通ること、watchdog期限との前後関係を検証した。

## 検証結果

- 初回sandbox対象3試験: **3 failed / 3 warnings / 2.24秒 / exit 1**。3件ともTk作成時に `Cannot find a usable init.tcl`。新診断実行前の環境アクセス失敗。`entry-audit-targeted.txt`を保存し、通常権限で再実行した。owner_missing/DEP-05の再発と混同しない。
- 通常権限対象3試験: **3 passed / 1 warning / 19.08秒 / exit 0**。`entry-audit-targeted-native.txt`。
- 新診断評価の全件1回: **1678 passed / 1 warning / 266.92秒 / exit 0**。`entry-audit-full.txt`。フィルタ・skip・期限変更なし。警告はPyMuPDF ByteString非推奨のみ。
- Ruff check . は成功。formatの初回 `--extension md:markdown` は非対応指定でexit 1、ファイル変更なし。その後Python対象formatは1 file reformatted / 100 unchanged。sandbox試験生成物作成後は通常権限でもそのディレクトリのアクセス拒否でformat exit 2。生成物1ディレクトリ `pf_owner_missing_entry_audit_20261023` だけを走査除外し、既知のPython対象指定で全101ファイルを再確認: check成功→101 files unchanged→check成功。ソース除外・pyproject変更なし。
- `pagefolio.py`とtracerのAST、`git diff --check`成功。
- pagefolio/app.py、pagefolio/settings.py、tests/test_config_notification.py、tests/test_settings_keyguard.pyのSHA256はforensics-20261023.mdに記録した値と全て一致。

```powershell
.venv/Scripts/python.exe -m pytest tests/test_startup_windows.py::test_simultaneous_exit_audit_distinguishes_entry -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_entry_audit_native_20261023"
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_entry_full_20261023"
.venv/Scripts/ruff.exe check . --extend-exclude pf_owner_missing_entry_audit_20261023
.venv/Scripts/ruff.exe format . --config 'include=["*.py", "*.pyi", "*.ipynb"]' --extend-exclude pf_owner_missing_entry_audit_20261023
```

## 全件の入口監査証拠

専用basetemp `pf_owner_missing_entry_full_20261023` の6 JSONLを `entry-audit-artifacts/` 以下へ相対パスを維持してコピーし、全て原本とSHA256一致を確認。原本・初回失敗証拠は保持した。

| fixture | 発火・終了 | SHA256（exit-audit.jsonl） |
|---|---|---|
| test_simultaneous_exit_audit_d0/simultaneous-audit-wm | test_trigger→wm→quit、stop_all=false | 56298FCB63BBF552FE7DAE5E0D0AB1EC4C6FF3444463613DC70FAA1DC5C95DA9 |
| test_simultaneous_exit_audit_d1/simultaneous-audit-button | test_trigger→button→quit、stop_all=false | DA70FAC50156CC4A75F06756C55ABBB7756FEB5AF05D7E511635F5A7EDCD5259 |
| test_simultaneous_exit_audit_d2/simultaneous-audit-watchdog | watchdog→quit、stop_all=false | 14177ED1739BF0A2241A450F9DBB280D980CD5BA1A6DC22B2788BFA8CB67FCD1 |
| test_simultaneous_real_process0/simultaneous-0 | stop_poll→quit、stop_all=true | E86FD34C73329F05A4D6C685176B6ED184B6C2F6C976987EAC7E02F1C4CF2E27 |
| test_simultaneous_real_process1/simultaneous-0 | stop_poll→quit、stop_all=true | 34A2032452209E780714B6FDA39935D87FF45FF558333D38F1B4649C3516EB87 |
| test_simultaneous_real_process2/simultaneous-slow-0 | stop_poll→quit、stop_all=true | 19BDF71978382EFCB60605434C084739869F3108F4B88687DB35F61977E2B434 |

| ファイル | SHA256 |
|---|---|
| tests/test_startup_windows.py | 24B021A69B84298C63E363C222F452861F4A0A207603A82AB7D9A0656FF79C82 |
| entry-audit-targeted.txt | B10CAEE257CA44B6A80F96A5E500A478C57ED9F9A6BA299BB8FB8454CE6999F2 |
| entry-audit-targeted-native.txt | C9DBDFDC3A48DA328F8397CFC5024F2B7A52ABC5FC37AA95D57F31AFE2D83CFD |
| entry-audit-full.txt | 3BB276D3739754911C28227E3799ADEDCAD0C936533380CAAFD55B574AD84D89 |

## 調査方針checkpoint

監査は動作するが初回現象は未再現。追加の同条件反復をせず、次の選択を利用者へ提示する。

1. 追加監査を保持し、新しい再発証拠を待つ。Phase停止・未コミット・DEP-05未解除を維持。
2. OS入力元を特定する外部トレースの設計へ進む。必要な権限・対象プロセス・採取範囲を先に具体化する。初回証拠から送信元を遡及復元できるとは扱わない。

どちらも原因修復・条件付きPhase再開の承認ではない。

### 利用者回答（2026-10-23T12:38:20Z）

回答「1」により、追加監査を保持して新しい再発証拠を待つ方針が確定。追加試験の反復・外部トレース設計は行わない。Phase 5停止・DEP-05未解除・未コミットを維持し、再発時は最初の失敗ログとexit-audit.jsonl/resource-audit/result/tracebackを保存して同じdebugを継続する。
