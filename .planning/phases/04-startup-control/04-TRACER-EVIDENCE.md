# Phase 4 — 起動 tracer の実測証拠

状態: **Task 3の実機ゲートを2026-10-21に確認済み。A1〜A5すべてpass。**
Phase4全体のvalidated/完了判定は後続04-02〜05とフェーズ検証を待つ。

2026-10-21、Windows 11 build 26300 / Session 1 / Python 3.15.0 / 64bit / 既存 .venv。
通常試験は一意の run nonce を owner/state/pipe/notice の全名前空間へ注入した。
本番既定名、権限差、利用者の入力継続は自動試験の合格から推定しない。

## 自動検証の結果

| 検証 | 実結果 |
|---|---|
| Task 1 DoD 局所（初回） | 18 passed / 1 warning / 0.42秒。後に途中SUMMARY整合の回帰を1件追加 |
| Task 1 コミット前の単一全件 | 1422 passed / 1 warning / 33.72秒 |
| Task 2 確定版の単一全件 | **1437 passed / 1 warning / 68.31秒**、skip/除外なし |
| 計画指定tracer最終実行 | **14 passed / 1 warning / 37.46秒** (`.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer`) |
| Task3実機確認後の指定tracer | **14 passed / 1 warning / 37.97秒** |
| Task3実機確認後の単一全件pytest | **1437 passed / 1 warning / 67.89秒** |
| `.venv/Scripts/ruff.exe check .` | All checks passed! |
| `.venv/Scripts/ruff.exe format .` | 成功。整形後にcheck/全件pytestを実行 |
| `pagefolio.py` AST 構文確認 | AST OK |
| 原本3ファイル | 各試験・各spawn子で存在/非存在とSHA-256の前後一致をassert。内容・APIキーは出力しない |
| plugins | 各子で初回app importより前に空の一時pluginsへ差し替え |

唯一の最終警告は既存PyMuPDFのByteString DeprecationWarning。
途中の1436件実行では、既存OCR backoff試験中にTk Variable.__del__の
`RuntimeError: main thread is not in main loop` 警告も発生した。
最終1437件では再現していない。原因未確認としてdeferred-items.mdへ残す。

最終局所run（pytest-23）のfixture result.json実値:

| ケース | 実測 |
|---|---|
| 無応答peer | expired、5000ms、app構築0 |
| 同時二次 a / b | 各62ms、各app構築0、双方foreground_denied（前面化成功とは扱わない） |
| 一次 | app構築1、同じrootの復帰callback 2回、status不変 |
| 実main接続失敗案内 | connection_failed、10031ms、app構築0 |
| mutex API拒否 | api_denied、15ms、app構築0 |
| 初期化例外 / 続く一次 | initialization_failed 250ms / 新一次構築1 |

## I1〜I4

| 段階 | 試験名（tests/test_startup_windows.py） | 確認した事実 |
|---|---|---|
| I1 | tracer_abi_64bit_snapshot_and_thread | HANDLE 8 bytes、生成時刻が32bitを超える、snapshotのPID/session一致、生成時刻不一致・奇数sequence拒否、別thread close拒否 |
| I2 | tracer_io_lifetime_pending_connect_cancel | 実ConnectNamedPipeを80ms期限でCancelIoExし、完了確認・event解放を650ms未満で確認 |
| I2 | tracer_io_lifetime_quarantine_keeps_native_buffers | 完了照合を故意に遅延。GC後もpipe/event/OVERLAPPED/bufferを保持し、照合再開後reaperが回収 |
| I3 | tracer_e2e_real_main_terminal_ack | 実main・実PDFEditorApp/Tk・実mutex/pipe。一次構築1、同時二次2件は構築0、双方terminal完了、同じrootで復帰、status不変 |
| I3 | tracer_e2e_initialization_failure_releases_owner | app初期化例外後、別processが同じ名前をclaimして実appを1回構築 |
| I3 | tracer_e2e_api_denial_does_not_construct_app | CreateMutexExW拒否を注入し、編集画面構築0、app module importなし |
| I4 | tracer_notice_nonactivate_lifetime_and_close | 実WS_EX_NOACTIVATE/TOOLWINDOW小窓、短縮timer/閉じるメッセージ、前面HWND不変、WndProc強保持 |
| I4 | tracer_notice_ten_second_production_timer | 本番10000ms timerで自動閉鎖（9900〜11500msのassert） |
| I4 | tracer_notice_lease_process_dedup | 別processの同一原因lease取得を拒否、表示権は1件 |
| I4 | tracer_notice_real_main_failure_path | 実mainの接続拒否→本番非活性案内→10秒後終了、追加app 0 |

I3の初回実測で、DisconnectNamedPipeが未読terminalを破棄する問題を検出した。
同じ絶対期限内の受信確認を追加して解消した。無期限FlushFileBuffersは使用しない。
listenerは周期的なconnect取消しを避け、同時接続を8本の有界workerで処理する。
I/Oの同時保有/未完了退避は32スロットを上限とし、取消し要求だけでbufferを解放しない。

## A1〜A5 — 自動結果と実機結果を分離

| ID | 条件・期待 | 自動結果 | 実機欄 / 最終判定 |
|---|---|---|---|
| A1 | 無応答peer、5秒単一期限＋有限cleanup、GC/取消し競合 | pass: 実peer故障注入でexpired、elapsed実値5000ms。80ms connect取消し/500ms quarantine寿命もpass | **pass**: 該当assert・実測・再開後tracerを照合 |
| A2 | 部分公開、PID再利用相当、同時2件以上 | pass: 奇数sequence・生成時刻不一致を拒否。同時2件が実Tk callbackのterminalへ到達 | **pass**: 生成時刻照合、部分公開拒否、同時二次2件の証拠を確認 |
| A3 | 表示・手動閉鎖・10秒閉鎖で他アプリの入力先不変 | 自動pass: Win32前面HWNDの表示前/後一致、短縮閉鎖、実10秒timer | **pass**: 実クリック閉鎖1937ms、無操作retry10000ms、両runの前面HWND不変と利用者の入力継続確認 |
| A4 | medium→elevated / elevated→medium のowner・mapping・双方向pipe・notice lease | 同一integrityの全4資源はpass | **pass**: 両順序・全4資源の生記録を照合。SID/session同一、認証LUIDは別値。ACL拡張なし |
| A5 | 別processで共有tickの順序が成立、wall clock非依存 | pass: 親before ≤ 子GetTickCount64 ≤ 親after。time.timeを負値へ差し替えてもtickが継続 | **pass**: 自動assertとGetTickCount64公式仕様を照合。OS時計変更なし |

**A1〜A5の停止ゲートは解消。固定本番名も専用試験一次の識別後にpass。**
この実行担当は04-02を開始せず、完了記録を親オーケストレーターへ返す。

## Task 3 — 実機の最終記録

対象製品コード: de27654（実機開始時HEADは32868b7、以後製品コード変更なし）。
集約JSONは [04-HUMAN-EVIDENCE.json](04-HUMAN-EVIDENCE.json)。全24個の集約recordを
`.planning/tmp/phase04-human-687c05821bc9445ab735c887a5a48b71/` の元JSON/readyと比較し一致。
原データは削除していない。親記録の試験process残留は0、原本3ファイルは不存在を維持。

| ケース | 条件・実測 | 判定 |
|---|---|---|
| A3 実クリック | shown=56864203 / closed=56866140、1937ms。foreground=135134が前/表示中/閉鎖後で一致。利用者「クリックして閉じ、入力も続けられた」 | pass |
| A3 自動閉鎖 初回 | shown=56922375 / closed=56924109、1734ms。利用者がクリックしたと回答 | 自動閉鎖の証拠として不採用。消去せず保存 |
| A3 自動閉鎖 retry | shown=56982843 / closed=56992843、10000ms。foreground=1640822不変。利用者「触れずに待ち、入力も続けられた」 | pass |
| A4 通常一次→昇格二次 | 一次PID29640 / 二次10920。SID=S-1-5-5-0-204810、session=1。認証LUID209750 / 208027。owner acquired/existing、mappingのPID・生成時刻・generation一致、notice true/false、双方向terminal foreground_denied 62ms。構築1/0、一次復帰1/status保持 | 全4資源pass。前面化成功とは扱わない |
| A4 昇格一次→通常二次 | 一次PID26640 / 二次33552。同SID/session、認証LUID208027 / 209750。owner acquired/existing、mapping identity一致、notice true/false、双方向terminal completed 63ms。構築1/0、一次復帰1/status保持 | 全4資源pass |
| 固定本番名 初回 | preflight no_existing_owner後、ランチャーPIDとready.pidが異なったため試験側の同一性ガードで中断。二次未起動 | 製品不合格と区別し保存 |
| 固定本番名 retry | preflight no_existing_owner。launcher32632→実Python子20592をCIMで照合後のみ二次35168起動。terminal foreground_denied 31ms、構築1/0、一次復帰1/status保持 | pass |

UACは利用者が応答済み。GUI helper起動にはすべてWindowStyle Hiddenを指定。
通常/昇格の区別は実際の起動方法と認証LUIDを記録し、logon SID差を仮定しなかった。
所有者側snapshotのstate=initializingと二次側readyは可変stateの正常な推移であり、
照合した不変identity（PID/生成時刻/session/generation）は同一である。

## 手動確認用bootstrap（通常pytestはUAC/操作待ちを行わない）

実行担当が `tests/test_startup_windows.py` の `_spawn` を使って一時fixtureを用意する。
各fixtureには設定JSON、2種の試験プロンプト、空pluginsを作る。`_test_scenario_bootstrap`
は全子で隔離を適用し、最後に原本3ファイルのSHA-256/存在を再照合する。

| role | 用途と成果物 |
|---|---|
| preflight | `namespace=fixed-production` で既存ownerがいない場合だけ通過。既存/不明ならwindowに触れず中断 |
| notice-manual / notice-timer | 本番10秒の非活性案内。readyとresult.jsonにHWND・表示tick・閉鎖tick・前面HWNDを記録 |
| manual-owner | 専用試験画面を最大120秒保持。ready/resource-audit.jsonにSID/LUID/session、owner判定、snapshot、notice所有を記録 |
| manual-secondary | 同じnamespaceの一次へ要求。resource-audit.jsonにowner/mapping/notice結果、terminal結果とelapsedを記録 |

固定本番名試験は専用対話セッションでpreflightを先行する。
A3は利用者が他アプリへ入力してから実行担当が案内を表示し、
「閉じる」を実際にクリックする回と、操作せず10秒待つ回を別々に記録する。
A4は実行担当が `Start-Process -Verb RunAs -WindowStyle Hidden` で片側を準備し、
利用者はUACに応答する。通常→昇格と昇格→通常を別runとして保存する。
手動fixtureのstopファイルは実行担当が作成し、子の終了と原本不変を確認する。

固定本番名overrideは試験factory内だけに閉じ、製品CLI/環境変数は増やしていない。
失敗が出た資源は理由・WinErrorを記録し、User SID/EveryoneへACLを緩和しない。

## 一次資料

- [GetTickCount64](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-gettickcount64): システム起動後の経過ミリ秒、壁時計補正と分離。A5の仕様根拠。
- [CancelIoEx](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex): 取消し後も完了までOVERLAPPEDの再利用/解放を禁止。I2の寿命契約。
- [CreateNamedPipeW](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew): overlapped、instance上限、remote拒否。
- [CreateMutexExW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexexw): 明示アクセス権と同一thread所有。

## 手順上の調整

- AGENTS.mdのコミット前全件pytest成功を優先し、REDの失敗状態はコミットしなかった。
  Task1は9 failed/9 passed、Task2の初期probeはassertionで1 failedを実測した。
  REDコミット/機械判定済みRED evidenceは存在せず、TDDゲート完全遵守とは扱わない。
- claim前の重いimportを除くため、`pagefolio/__init__.py` の既存公開APIを
  PEP562遅延再exportへ変更した（Rule2）。全件回帰で互換性を確認した。
- Task1の自己レビューで途中進捗のSUMMARY件数整合を補強した（Rule1、282d8fe）。
- バージョン/README/開発履歴の同期と実EXE検証は、計画どおりPhase6の担当。
