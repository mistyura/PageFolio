# Phase 4 — 起動 tracer の実測証拠

状態: **Task 2 自動検証済み、Task 3 blocking-human 待ち。04-01 は未完了。**

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
| A1 | 無応答peer、5秒単一期限＋有限cleanup、GC/取消し競合 | pass: 実peer故障注入でexpired、elapsed 4900〜5550ms。80ms connect取消し/500ms quarantine寿命もpass | 自動条件pass。実機記録の確認待ち |
| A2 | 部分公開、PID再利用相当、同時2件以上 | pass: 奇数sequence・生成時刻不一致を拒否。同時2件が実Tk callbackのterminalへ到達 | 自動条件pass。実機記録の確認待ち |
| A3 | 表示・手動閉鎖・10秒閉鎖で他アプリの入力先不変 | 自動pass: Win32前面HWNDの表示前/後一致、短縮閉鎖、実10秒timer | **pending**: 利用者が他アプリで入力を継続し、実際の閉じるクリック・10秒経過を目視確認する |
| A4 | medium→elevated / elevated→medium のowner・mapping・双方向pipe・notice lease | 同一integrityの全4資源はpass | **pending**: 両作成順序・4資源すべて。SID・認証LUID・session IDを別記。ACLの自動拡張は禁止 |
| A5 | 別processで共有tickの順序が成立、wall clock非依存 | pass: 親before ≤ 子GetTickCount64 ≤ 親after。time.timeを負値へ差し替えてもtickが継続 | 公式仕様と自動結果の確認待ち。OS時計は変更していない |

**A3/A4・固定本番名は未実施。A1〜A5全件の最終passまでは04-02を開始しない。**

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
