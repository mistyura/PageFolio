

## 2026-10-22 承認済み受入再計画（現行）

ユーザー承認: 「受入条件を再計画し、別セッション確認など準備できない項目をPhase 6へ移す」。
従来のW全必須passまでPhase 4を停止する条件と移管不可の判断を置き換える。
機能契約・保証範囲・実測・未実施の事実は変更しない。

- Phase 4は自動/Windows subprocess受入、A1〜A5実証、証拠照合と移管追跡を確認する。
- W01〜W12の未実施人手部分はPhase 6のV110-QA-02へ移管し、全件passまでリリースを停止する。
- not-runをpassに変えない。別session準備不能も維持し、アカウント新設や資格情報取得は行わない。
- 自動試験の失敗・未解決の製品欠陥・セキュリティhighは免除しない。
- Phase 4正式完了にはSUMMARY→Progress→validate-phase実走→全件pytest→正式完了→DoD再確認を要する。
- 移管正本: `.planning/phases/06-release-validation/06-UAT-CARRYOVER.md`。5要件の最終実機受入もここで追跡する。

以下の旧停止条件は再計画前の履歴。実施時期は上記の現行条件を適用する。

# Phase 4 — Windows受入記録

状態: **04-05 Task 1完了 / Task 2未承認 / Phase 4未完了**。
更新日: 2026-10-22。対象製品commit: `b26ddec`（04-05は試験と文書のみ）。
実EXE・ビルド・版同期はPhase 6、実API/課金試験は今回の対象外。

## 証拠の読み方

- **実証（自動）**: 実Win32/Tk/Python子processで観測した事実。実キーボード入力や目視評価を意味しない。
- **故障注入/純粋試験**: fake clock/OS失敗注入/identity関数での結果。実OS拒否・別session実証へ置換しない。
- **人手実証**: 利用者の回答と実測recordが対応するもの。旧通知primitiveのA3/A4は新通知leaseの再受入には使わない。
- **推定**: 設計/実装から想定した結果。passに数えない。
- **not-run**: 必須観測が未実施または準備不能。failと共にTask 2/Phase完了を止める。

## 環境・原本保護

| 項目 | 今回の実測 |
|---|---|
| OS | Windows 11 / build 26300 / 64bit |
| Python / Tcl / Tk | 3.15.0 / 9.0.4 / 9.0（manifestに実値） |
| 権限 / session | medium（IsUserAnAdmin=false）/ ProcessIdToSessionId=1 |
| 起動入口 | python pagefolio.py / python -m pagefolioをrunpyで本番コードのまま実行 |
| 名前空間 | 通常pytest/明示harnessはrun nonce。固定名は`--production`明示のみ |
| 設定/2プロンプト/plugins | 初回app import前に子fixtureへ隔離。元3ファイルの存在/SHA-256を前後assert |
| 原本実値 | 今回は3ファイルとも不存在を維持。APIキーの値・ファイル内容は記録しない |
| PIDの区別 | Windows venv launcher PIDと実Python PIDを別記。接続先照合は公開PID＋process_created |
| 実測記録 | `manifest.json`, `ready`, `resource-audit.json`, `result.json`, `inspection.json` |

## W01〜W12

各Wは下表の自動部分と人手部分を別に判定する。空欄/推定を合格へ補完しない。

| ID | 決定・要件 | 準備/期待 | 実証済みの範囲 | 人手の最終判定・未実施理由 |
|---|---|---|---|---|
| W01 | D-01/02、FOCUS-01/02 | `normal`, `zoomed`。最小化後に元state/geometryへ戻りstatus維持 | 04-03のscript/module各normal/zoomedは実Win32/Tk自動pass | **not-run**: 今回の目視・実入力確認待ち |
| W02 | D-04、FOCUS-02 | `settings`, `thumb`, `preview`。入力文字/selection/カーソル/直前widget維持 | 04-03自動pass。今回preview準備→script二次もstate/target保持、foreground_denied/63ms | **not-run**: 拒否を実キーボードfocus復帰成功と扱わない |
| W03 | D-01/04、FOCUS-02 | `pdf`。一時3ページPDFに回転/複製/削除、復帰後Undo→Redo→Undo→Redo | 04-03でDocument/履歴/Blob identity・digestと4操作自動pass | **not-run**: 利用者の内容確認待ち。原PDFは使わない |
| W04 | D-01、FOCUS-02 | `ocr`。local fake providerが待機中の同じengine/worker/run generationを保つ | 04-03自動pass。harnessも同じ実OCRDialog経路で準備 | **not-run**: 進捗/完了の目視待ち。実APIは実施していない |
| W05a | D-13、FOCUS-02 | `nested`。Settings→LLMConfig→子閉鎖でgrabなし、Settings入力を保持 | 04-03両入口で自動pass | **not-run**: 実入力/selection目視待ち |
| W05b | D-13、FOCUS-02 | `native-ocr`。OCRDialog所有messageboxが対象 | 04-03でTk親と異なる所有native HWND選択を自動pass | **not-run**: 人がmessageboxを閉じる。通常pytestの自動閉鎖と区別 |
| W05c | D-13、START-02/FOCUS-02 | `native-quit`。_quit確認中に再起動、Noで排他/編集維持 | 04-03自動pass | **not-run**: 実No操作と保存確認の目視待ち |
| W06 | D-14/15/16、FOCUS-01 | 別process入力中、許可委譲後も入力を続ける。OS拒否時はタスクバー3回/250ms、2秒内停止、15秒後再前面化なし | 04-03 fake OS拒否/有限点滅pass。今回previewは実foreground_denied | **not-run**: 実OS拒否時の点滅/入力/15秒目視をまだ照合していない。許可成功試行を拒否へ数えない |
| W07a | D-05/06/08/16、START-01/03 | `slowready`。初期化を6.5秒遅延、5秒失効後の復帰0 | 今回backend 5000ms/expired、二次15437ms、一次restored=0、案内10000msを実証 | **自動観測pass / 人手not-run**: 一次通常表示と期限切れ前面化を区別する最終確認待ち |
| W07b | D-06/08/16、START-03 | `busy`。ready後に保存/挿入相当のUI同期busyを6.5秒注入。復帰後expired queueの副作用0 | 単独再測定はbackend5000ms/expired、二次15140ms、busy前後restored0/0。並行負荷runは15609msで15.5秒上限を109ms超過、両方保存 | **単独条件pass / 人手not-run**: 負荷時の上限保証へ外挿しない。初回harness記録不備も不採用・保存 |
| W08a | D-07、START-02 | 初期化死亡→候補2者同時claim、新一次1つ、死亡確認後1回だけ引継ぎ | 04-02実subprocess pass、同時2/8起動もpass | **not-run**: 人手での最終観測照合待ち |
| W08b | START-02 | 正常終了・強制終了・初期化例外・公開前例外後に新一次 | 04-01/02実subprocess pass | **not-run**: 人手での最終観測照合待ち |
| W08c | START-02 | _quit No時はmutex保持、Yes後の独立起動のみ新一次 | 04-02/03実subprocess pass | **not-run**: W05c実No操作と対応付ける |
| W08d | D-07、START-01/02 | root消失/旧worker生存/released公開/古mapping保持/同時claimを別々に照合 | 04-02のreleased mapping/worker-alive・forced ready/initializing・partial/identity mismatch試験pass | **not-run**: OS process死亡とroot消失を混同せずrecord確認 |
| W09a | D-09/10/11/12/16、START-03 | 新通知lease、同原因8process、初回10秒期限不変、閉鎖後15秒残留なし | 04-04実nonceで8process・保持handle付き死亡回復pass。本番5000+10000ms、終了15015ms、閉鎖後15.007秒観測pass | **not-run**: 新通知で実クリック/他process入力継続の確認待ち |
| W09b | D-09/10/12 | Windows設定100% DPIで全文・閉じる領域を確認 | OS message font/window DPIの自動計算のみ | **not-run**: 100%実表示未確認 |
| W09c | D-09/10/12 | 同150% DPI | 同上。DPI引数mockは実測へ置換しない | **not-run**: 150%実表示未確認 |
| W09d | D-09/10/12 | 同200% DPI | 同上 | **not-run**: 200%実表示未確認 |
| W10a | START-01/03、FOCUS-01 | medium一次→elevated二次。owner/mapping/双方向pipe/新noticeを個別確認 | 旧A4のowner/mapping/pipeは実証済み。新通知は同一integrity自動passのみ | **not-run**: 新leaseでUAC操作/両権限を再受入する |
| W10b | START-01/03、FOCUS-01 | elevated一次→medium二次。同SID/LUID/session、4資源を個別記録 | 旧A4は同SID/session・LUID別値でpass。新leaseへ外挿しない | **not-run**: 新leaseで逆順再受入待ち |
| W11 | START-01 | 既存の別Windowsアカウントへ切替（元sessionをサインアウトしない）。各sessionに1画面、二次は同sessionへ復帰 | Local namespaceの設計/故障注入はあるが別session実証なし | **not-run（準備不能）**: 利用者「別アカウントがない／切替できない」。アカウント作成・資格情報取得はしない。mock passで代替しない |
| W12a | START-01、FOCUS-01 | script/module/別配置を一次・二次にした3×3。対応版の見かけを変えても共通ID | 今回cross_entry 3ケースで9組、編集構築1/二次0。同nonce、接続先PID/生成時刻照合 | **自動部分pass / 人手部分not-run** |
| W12b | START-01 | APP_VERSION/実行パス/sys.frozen変更時のID一致 | identity関数相当の試験pass。実EXE試験ではない | **自動部分pass**、実EXEはPhase 6 |
| W12c | FOCUS-01 | Explorerショートカット→Python、端末→Python。AllowSetForegroundWindow戻りと実foregroundを別記 | 前者は未実施。後者のharnessはAPI戻り/OS error/terminal結果を別記 | **not-run**: 本番固定名で利用者の実入力と入口別foreground確認待ち |

START/FOCUSはV110-START/V110-FOCUSの略。D-03はW08/W09、D-07はW08、残る全Dは表内に明示し、16決定を被覆する。

## 実行担当向けharness（利用者はコマンドを調べない）

作業ディレクトリはリポジトリroot。コマンドは**実行担当が実行**する。利用者は入力/クリック/UAC/画面評価だけ行う。
通常pytestと別の明示入口で、製品CLIは変更しない。ownerは最大120秒、fake OCRは110秒で解除、peerは最大18秒。
120秒を超えて確認する場合は停止して新runを準備する。初回準備失敗runも削除せず保持する。

```powershell
$uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case settings | ConvertFrom-Json
.venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
.venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
.venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
```

- W01: caseを`normal`, `zoomed`。開始時点で最小化を準備済み。peer後に元サイズ/最大化を確認。
- W02: `settings`には`unsaved input`、カーソル5、選択1〜7を準備。`thumb`, `preview`は当該widgetを操作先へ。
- W03: `pdf`。復帰時に同じ履歴で4手を実行し`continued`を作る。未保存PDFはメモリ上のみ。
- W04: `ocr`。peer時点でfake provider待機。復帰後に同workerを解放し、完了時`continued`を作る。
- W05: `nested`, `native-ocr`, `native-quit`。nativeケースの人手版は自動クリックしない。確認後に利用者がOK/Noを操作する。
- W06: `preview`を準備後、利用者が別processの入力欄へ切替。実行担当がpeer、入力を継続し15秒後まで観測。拒否が出なければnot-runのまま再試行。
- W07: `slowready`, `busy`を開始したら直ちにpeer。`scenario-ready`後にstartが戻る。5秒失効・10秒案内を実時間で記録し、復帰回数0とbusy前後0を確認する。
- W08: 既存の`test_lifecycle_*`, `test_takeover_*`, `test_simultaneous_*`を実行担当が実施し、生ready/audit/resultを照合する。人へprocess killコマンドを依頼しない。

W09は下記で**新しい可視通知lease**を準備する。別processの入力を続けたまま、閉じる領域の実クリックと無操作10秒を別runで確認する。
表示中に複数peerを起動してsnapshotのPID/generation/HWND/deadline完全一致を確認し、最初の表示から期限を更新しない。

```powershell
$notice = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json
.venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $notice.run
.venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $notice.run
```

通知は10秒で閉じるので、表示run中に確認できなければ再準備する。各DPIは利用者がWindows表示設定を変更した**実状態**で別runにする。
readyにwindow DPI/close_rect/snapshotを記録。非活性は表示/閉鎖の各直前直後foregroundで評価し、途中の任意画面切替と混同しない。

W10のUACは人が操作する。実行担当が`Start-Process -Verb RunAs -WindowStyle Hidden`で**同じharness peer/notice**を起動する。
ownerは上のstartを一方の権限で準備、peerをもう一方で実行。noticeは`--namespace <owner manifestのnonce>`で同じnonceの可視通知を一方に作り、もう一方からそのnotice runへpeerする。
逆順も繰り返し、SID/LUID/session、owner acquired/existing、mappingのPID/生成時刻/generation、pipe terminal/許可戻り、notice snapshot/acquiredを個別記録する。
旧`manual-owner`の`A4-resource-check`は可視窓未公開なので新lease試験に使用しない。

W11は既存の別sessionが用意できた場合だけ、共通`--namespace <nonce>`で各sessionにstartする。両manifestのsession IDが異なることを確認し、両方でpeer→inspect、元sessionへ戻って状態不変を照合する。現環境では準備不能なので実行しない。

W12cの固定名は`start --production --case preview`だけで明示する。preflightで既存ownerがあれば送信せず停止し、試験一次claimでもexistingを拒否する。
peerは毎回snapshotのPID/生成時刻を照合し、一次消失・別ownerへ切替時は追加rootも要求も生成しない（今回のguard負例で自動検証）。
Explorer用には実行担当が`.lnk`へ既知Python＋同じpeer引数を設定し、利用者が起動する。ショートカットの入口を本番CLIへのテスト引数追加で代替しない。

## 観測recordの必須欄

| ID/run | source commit | 権限/Session/入口 | started_tick / ready or shown_tick / closed_tick | foreground前/表示後/閉鎖前後 | root数 / 終了tick / restore数 | AllowSetForegroundWindow戻り / 実foreground | 判定・理由 |
|---|---|---|---|---|---|---|---|
| 今回preview | b26ddec | medium / 1 / owner main→script | started=65246421 / ready=65248921 | target=17044112、実foreground成功とは判定しない | 一次1/二次0、一次restored=1、二次63ms | peer auditにallowed/OS error、terminal=foreground_denied | 自動の状態保持pass。人手not-run |
| W07初回busy | b26ddec + 作業中harness | medium / 1 / module | started=65320796 / ready=65323484、UI busy6.5秒 | 未判定 | 一次1/二次0、restore0 | backend raw=connection_failed/5000ms、coordinatorは期限でexpiredへ補正 | **受入証拠へ不採用**: 旧harnessがrawを最終結果と誤記し、表示timerも150msのままだった。生run `pagefolio-uat-c63pyhuk`を保持、修正後再測定 |
| W07 busy並行負荷 | b26ddec + 試験追加 | medium / 1 / module | shown=65481687 / closed=65491687 | 表示/閉鎖各前後1575772不変 | 一次1/二次0、restore0、二次15609ms | backend expired/5515ms（cleanup含む） | **15.5秒上限109ms超過を保持**。cross_entry並行中。閉鎖443984ms後にHWND消失確認 |
| W07 busy単独 | 同上、コード変更なし | medium / 1 / module | shown=66244406 / deadline=66254406 / closed=66254421 | 表示/閉鎖各前後135134不変 | 一次1/二次0、restore0、二次15140ms | backend expired/5000ms | **単独条件pass**。全試験終了後に同harnessを1回だけ再測定。閉鎖56532ms後にHWND消失確認 |
| W07 slowready | b26ddec + 試験追加 | medium / 1 / script | shown=65750375 / closed=65760375 | 表示/閉鎖各前後135134不変 | 一次1/二次0、restore0、二次15437ms | backend expired/5000ms | **自動観測pass**。閉鎖175296ms後にHWND消失確認。人手承認とは分離 |

追加の最終実測・検証時間は`04-05-EVIDENCE.json`へ保存する。上記未実施の欄を自動的にpassへ変更しない。

## 故障注入と実機の境界・禁止事項

remote/他logon/不正wire/ACL拒否/PID再利用相当/stale generation/過大queueの拒否は04-01/02の故障注入・純粋試験。
他logon実session、実UAC、実OS入力によるforeground拒否とは別。OS foreground lock設定/ACLの緩和は行わない。
3禁止事項（強制前面化の迂回なし、作業状態の再生成なし、起動失敗で追加編集画面なし）は自動証拠を対応付けるが、人手最終判断は**flagged-unverified**を維持する。
SPECなしedge5件は**unclassified/unresolved**、verification/resolution/reason=nullを維持。probeを受入証拠だけでresolvedへ書き換えない。

## 完了ゲートと引き継ぎ

**W11準備不能を含め必須not-runがあるため、04-05/Phase 4は完了不可。**
Task 1のcommit後は`04-05-CHECKPOINT.md`に停止点を保存し、04-05-SUMMARY.mdを完了扱いで作らない。
Task 2はgate=blocking-human。全必須pass→SUMMARY/Progress→validate-phase実走→VALIDATION実結果→単一全件pytest→親Phase完了→DoD再確認の順序を守る。
現時点でvalidated・要件Complete・Phase[x]へ進めない。Phase 6の実EXE/実API未実施をPhase 4のpassへ混ぜない。
