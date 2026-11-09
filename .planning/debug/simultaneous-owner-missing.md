---
status: investigating
trigger: "$gsd-debug で独立調査して / restart"
created: 2026-10-23
updated: 2026-10-28
---

## Current Focus

hypothesis: 原因未確定。10月28日の通知待機中のWinEventは公開578ms後の別窓で、前景先PID4080は現存Code.exeの作成時刻と先行記録からVS Codeと同定を補強した。ただし記録PIDは窓所有者であり、切替要求元・操作は未採取。元owner_missingは初回終了要求stack欠落により未確定で、両事例の因果も未確定。10月23日の手動終了否定や別試行の手動終了回答を今回へ転用しない。
test: 過去native全件1846 passed/1 failedと原本を保持。利用者の停止条件解消指示後、診断原本保存・AST一致の整形で全体Ruff137件成功。保留中のnative接続と9プロセス試験は各1回成功し、単一全件2071 passed/2 warnings/480.86秒/exit0、失敗0・ERROR0・skip0・入力不変。監査のviolation/audit_error/transitionは0。証拠はquality-gate-unblock-20261028/。
expecting: 今回の10月28日10:51:42〜44 JSTごろの操作確認は「覚えていない／不明」と回答済み。同じ質問を再度出さない。保存済みWinEventと回答から操作主体やclose入口は復元できず、環境要因・製品修復済み・元owner_missing解決とは断定しない。
next_action: 現行入力の品質停止は解除済み。Phase 6のresume_contractに従い、現行入力・依存検証の鮮度・台帳を照合して未実施受入へ戻す。古い成功hashへの付け替えやPhaseの自動完了は行わない。元owner_missing/過去の切替要求元は未確定のまま、再発時は初回証拠を保持して本debugを継続する。未実施の人手受入と出荷承認は別条件。過去の停止記録・47原本は保持する。

## Symptoms

expected: 同時起動は編集画面1つに収束し、fresh二次起動も同じ一次へ復帰要求できる。
actual: test_simultaneous_real_processes_construct_one_editor[2]のfresh二次がowner_missingでexit 1。
errors: AssertionError: 接続先guardが要求を中断した。guard_blocked=owner_missing、owner_result=acquired。
timeline: 05-02-01の保存・終了制御変更後の初回全件で発生。前回05-01全件1660 passed。変更との因果は未証明。
reproduction: 既存.venvの単一全件pytest、専用basetemp pf_0502_task1_20261023。1674 passed/1 failed、252.25秒。

## Evidence

- timestamp: 2026-10-28（利用者承認後の品質停止解除）
  checked: quality-gate-unblock.md、quality-gate-unblock-20261028/の原本・入力manifest・全体Ruff・native接続/9プロセス・全件pytestの各ログとJSON/XML。
  found: 過去診断1件を原本保存・AST不変で整形。全体Ruff137件成功、native局所各1回成功、全件2071 passed/2 warnings/480.86秒/exit0。失敗/ERROR/skip0、入力不変、監査違反/欠落/未知切替0。警告は既知PyMuPDF廃止予告とJUnit互換性通知でTcl漏洩/スレッド例外なし。
  implication: 現行の品質停止を解除し、Phase 6の再開前照合へ戻す。以下の元停止記録を当時の事実として保持し、過去失敗をpassへ変更しない。元の原因未確定と未実施受入・出荷未承認は残る。

- timestamp: 2026-10-28（独立したRuff内部異常対策）
  checked: resolved/ruff-format-source-panic.md、ruff-format-source-panic-matrix.json、ruff-format-source-panic-after.json、ruff-format-source-panic-fixture.json。
  found: 読取拒否の過去pytest生成物3フォルダーをルートで走査するとRuff 0.17.1がpanic。該当3フォルダーだけを.gitignoreに追加し、.ruff.tomlで既存ルールを継承・Markdownのformatだけ除外。全体lintは警告なしexit0、全体formatはpanicなしで過去diag_btn_press.pyの書式差1件を報告（exit1、136 formatted）。現行Python115件・隔離入力5項目・AST/diff確認成功。
  implication: 内部異常の対策は完了したが全体formatゲートは未通過。上のCurrent Focusで記録した元のpanicは対策前の記録であり、最新結果は本項と独立debugを参照。原本の書式差を消す/除外して通過扱いにせず、native接続/9process・全件・製品修正・Phase後続・commit・出荷停止を維持する。

- timestamp: 2026-10-28（試験見直し実装・全体format停止）
  checked: 利用者の「この案で実装と局所検証へ進む」、承認済み手順1〜3、既存132入力/index、試験3ファイル、unit-v3-pytest.txt、static-all.json。
  found: 記録ベース24 passed/1 warning/0.65秒。初回import収集エラーはtestsパッケージ経路へ修正し原ログ保持。対象lint/format・AST成功。全体lintはアクセス警告5件付きexit0、全体formatは通常権限でも内部panic。実OSの接続/9process試験は起動せず、手順1で停止。証拠正本はsimultaneous-owner-missing-evidence/notice-contract-20261028-implementation/。
  implication: 試験実装は実OS未検証。元失敗・47原本・未解決原因は維持。製品/版番号/pyproject/indexを変更せず、全件/Phase/commit/出荷停止も維持する。

- timestamp: 2026-10-28（再開・試験見直し設計）
  checked: 現行D-12、tests/test_startup_windows.pyの前景assert/WinEvent/子経路、NativeNoticeLifetimeの表示/破棄、既存probeのbind監査、Microsoft公式API仕様。
  found: 待機全体の前後2値比較は、外部切替でも失敗し、一時的な前景奪取後の復帰を単独では検出できない。現資料から要求元を追加同定する方法はなく、原因は未確定。利用者は見直し案の設計と内容確認後の実装を選択した。設計正本はsimultaneous-owner-missing-evidence/notice-test-review-20261028.md。未説明切替/監査不足は失敗停止を維持する案で、期限・重複抑制を緩和しない。
  implication: 提案内容の確認待ち。今回は設計文書と本記録のみ変更、Python/製品/版番号の変更・追加試験・commitなし。元の全件失敗・原本・未解決原因とPhase/出荷停止を保持する。

- timestamp: 2026-10-28T03:15:30Z（追加診断は一回のみ、未再現）
  checked: notice-probe-20261028-4186632ffba54d25b37703d6e2db059a/ のrun/pytest、入力128件、保存56ファイル、9 processのnotice-probe.jsonと既存監査、probe_notice_once.py
  found: 1 passed/1 warning/2.44秒・exit0、入力不変、保存56件hash一致、9 processのprobe.errors空。29観測の前景はTerminal HWND396656で不変、WinEvent0件。ownerはSetWindowPos→ShowWindow→DestroyWindowのみを記録し、show:1913→destroy:1637・remaining_ms=0で期限ループ経由のcloseを実測。SetForegroundWindow/AllowSetForegroundWindow呼出0件。lastinputはobserver開始前に14983046→14983109、その後固定。対象lint/format/AST成功、全体formatはRuff内部panicで未確認。
  implication: 今回の動作・診断採取を確認したが元失敗の原因は確定しない。追加診断は親の範囲判断で実施済み、反復なし。元47原本・最新全件失敗・DEP-05未解除・Phase停止を保持し、今回許可範囲の独立調査は完了。利用者回答待ちでも停止解除待ちの自動実行でもない。

- timestamp: 2026-10-28（今回時刻への利用者回答）
  checked: 親が提示した10月28日10:51:42〜44 JSTごろのTerminal→VS Code等への切替・操作の記憶確認
  found: 利用者回答原文は「覚えていない／不明」。今回時刻への回答としてnotice-recurrence-20261028.mdにDATA_START/DATA_ENDで保存した。操作の実施/不実施はどちらも確定しない。
  implication: 同じ質問を再度出さず、別試行の回答も代用しない。既存証拠内の調査は完了したが原因は未確定。次は未実施の限定診断案に対する採取範囲の判断であり、回答待ち・解決・実装再開とは扱わない。

- timestamp: 2026-10-28T02:06:32Z（保存原本の限定調査）
  checked: simultaneous-owner-missing-evidence/notice-recurrence-20261028.md、47原本/保存コピー、127入力manifest、当時hash一致のtests/test_startup_windows.pyとstartup_win32.py、先行normal manifest、現存PID4080のみのprocess情報
  found: 原本/コピー47件5905bytesの全hash一致。peer8件は非取得・同一snapshot/期限・前景789312で一致、全9子は正常完了。通知公開578ms後にVS Codeのプロセスへ前景変化。現存PID4080はCode.exe、生成時刻00:20:25.945754Zで失敗前から生存。監査pidは窓所有者由来で切替要求元ではない。寿命1859ms/期限差1800msは原本と整合するが、失敗行以後のassertは未到達。close入口・入力・呼出stackは未採取。
  implication: 前景先と変化区間を絞れたが原因未確定。この観測後に利用者から「覚えていない／不明」と回答を受領した（上記項目）。別時刻の人手回答を転用せず、元owner_missing/DEP-05との因果を保留。製品/試験変更・再実行・commitなし。Phase06と関連する既存停止条件を維持する。

- timestamp: 2026-10-28T01:51:44Z（Phase06世代3の再発、停止）
  checked: `.planning/phases/06-release-validation/06-04g3-quality-fixed/{run.json,pytest-full.txt,inputs-before.json,inputs-after.json,failure-notice-manifest.json}` と失敗ケース47原本ファイル
  found: native単一全件1846 passed / 1 failed / 1 warning / 180.20秒。`test_notice_dedup_eight_processes_keep_original_deadline` の前景assertが396656→789312で失敗。127入力の前後hash一致。owner PID16616の表示前後は396656、破棄前後は789312。公開tick9957265から578ms後のWinEventでPID4080/Chrome_WidgetWin_1へ変化、通知HWND3738882とは異なる。observer解除成功・errorなし。9 processのresult/traceback等47ファイル5905bytesをコピーし全SHA256一致。表示/破棄の瞬間以外での前景変化を実測したが、変更を起こした主体・操作・製品関与は未確定。
  implication: 再発時停止を適用し、再実行・修正・後続・commit・出荷を停止。先行する別の読込拒否試行への「手動で閉じた／終了した」という利用者回答を今回へ転用しない。元owner_missing/DEP-05の原因解決や同一原因と断定しない。詳細停止報告は `06-04g3-QUALITY-STOP.md`。Phase06未完了。

- timestamp: 2026-10-25（再発監視の確認・利用者判断で監視継続）
  checked: Phase 6 の単一全件ログ 15 本（.planning/phases/06-release-validation/*full*.txt・06-preflight/06-reviews-pytest*.txt、2026-10-24 05:54〜22:30）
  found: 失敗があったのは 3 本で、内容は test_config_notification の 3 件（Tcl 同種、06-01-STOP.md→親 debug commit 07244dc で解消）と test_takeover_two_candidates_after_confirmed_initialization_death（resolved/takeover-loser-expired.md でテスト側の前提誤りと確定）。normal-entry-script の communicate 期限超過・owner_missing の再発は 0 件。最新は 2024 passed / 1 warning（06-05-g1prep-full.txt）。
  implication: 再発証拠なし。原因未確定のため resolved にはせず、status investigating（再発監視）を維持する。Phase 6 最終ゲートまで監視し、再発時は最初の証拠を保持して continue で再開する。

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

root_cause: 未確定。初回の呼出stack欠落により、どの終了要求が一次を閉じたかを遡って実証できない。10月28日の通知待機中の前景変化はVS Codeのプロセスへの変化だが、操作・要求元・製品関与と元owner_missing/DEP-05との因果は未確定。
fix: 製品修復なし。前景WinEvent監査・一次生存assert・非表示検証runnerを追加。診断の時計比較はTcl時計へ揃え、native callbackからTkを再入呼出ししないよう修正。期限・guard・元の製品合否条件は維持。
verification: 10月23日の履歴は対象9件×3回・全件1680 passedで、最新合格へ転用しない。最新10月28日native全件は1846 passed/1 failed/1 warning/180.20秒/exit1、原本47件hash一致を保持。追加診断1回は1 passed/1 warning/2.44秒で未再現、128入力不変・保存56件hash一致。対象ラッパーlint/formatとAST成功、全体ruff checkはアクセス警告2件付き成功、全体formatはRuff内部panicで未確認。品質全件・Phase合格にはしない。
files_changed: 過去調査の既存差分を保持。先行continueでは本debug記録、notice-recurrence-20261028.md、外付けprobeと単発証拠を追加/更新。その後の承認でtests/test_startup_windows.pyを変更し、tests/startup_foreground_audit.pyとtests/test_startup_foreground_audit.pyを追加。設計文書・実装証拠・開発履歴を更新。製品・版番号・pyproject・期限は未変更。試験の前景判定だけを承認済みの保守的な複合判定へ変更。native未検証、commitなし。
disposition: unresolved/investigating。resolvedへ移動しない。DEP-05-REGRESSION未解除。10月28日の同種再発でPhase実装・後続・接続人手確認・commit・出荷の再停止を維持。今回時刻は「覚えていない／不明」と回答済み、保存原本調査と親が承認した追加診断一回の分析は完了。同じ質問・自動反復は不要。元失敗の因果を確定する新たな再発証拠等が得られるまで未解決として引き継ぐ。

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
