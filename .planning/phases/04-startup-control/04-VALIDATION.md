---
phase: "04"
slug: "startup-control"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-21"
---

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

# Phase 4 — Validation Strategy

検証契約と実行証拠の対応。04-01〜04の実装/自動回帰とA1〜A5の実機ゲートは
各SUMMARYに実測済み。04-05 Task 1の統合/準備結果は本書と04-WINDOWS-UAT.mdに記録する。
**Task 2は承認済み再計画に基づく証拠照合を完了。Phase正式完了は親の検証待ち。**
2026-10-22にvalidate-phaseをインライン実走。Nyquistは現行Phase4の自動検証被覆を示し、Phase6へ移管した実機受入の合格を意味しない。

## Test Infrastructure

| 項目 | 内容 |
|---|---|
| Framework | pytest 9.1.1、既存 .venv |
| Config file | pyproject.toml（編集禁止） |
| Quick run command | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_gsd_dod.py`（起動3ファイルは各作成タスク後） |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q`（単一プロセス全件） |
| 実測時間 | 04-05指定局所140 passed / 0.61秒、cross_entry/startup_acceptance 6 passed / 22.23秒。04-06修正後の単一全件1629 passed / 1 warning / 217.71秒。失敗・ERROR・skipなし。全件120秒目標は超過したが除外しない |

## Sampling Rate

- 各実装タスク後に対象テストを実行する。
- 各コミット前・各 wave 後・verify-work 前に単一プロセス全件 pytest の合格を要求する。
- Python 編集時は `ruff check .` と `ruff format .`、`pagefolio.py` の AST 構文確認を行う。
- 通常pytestは各子bootstrapで設定/プロンプト/pluginsと名前空間を初回読込前に隔離し、同一integrityの実subprocess試験を収集する。UAC・ユーザー切替・手動操作・本番固定名は収集対象外の明示harnessで実施する必須A/W証拠であり、skipや免除に置換しない。
- 時間境界はfake clockで網羅し、実subprocessは短縮timerの注入結果と本番5000/10000msの代表実測を分ける。実時間5秒/10秒/閉鎖後15秒はW07/W09に残す。局所verify60秒未満、自動Windows群60秒以内、全件120秒を目標として実測し、目標超過を理由に無断除外しない。

## Per-Task Verification Map

全コマンドはリポジトリルートで実行する。各PLANのautomated直後のfails_whenを合否条件とする。
実装済み行は対応SUMMARYの実測へ接続した。人手の未実施を自動passと同一にしない。

| Task ID | Wave | Requirement | Secure Behavior / Decision | Test Type | Automated Command | File Exists / 作成依存 | Threat Ref | Status |
|---|---|---|---|---|---|---|---|---|
| 04-01-01 | 1 | 全5件の実行前提 | 未完了と完了の区別、完了義務維持 | 合成回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_gsd_dod.py` | 既存・拡張済み | T-04-04 | pass: 04-01-SUMMARY/04-TRACER-EVIDENCE |
| 04-01-02 | 1 | START-01/02/03, FOCUS-01/02 | 本番E2E、A1〜A5、D-01/05/06/08/10/11/12 | Windows subprocess＋実機 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer` | 作成済み | T-04-01/02/03 | pass: 04-01-SUMMARY、14 passed / 37.97秒 |
| 04-01-03 | 1 | 全5件の方式成立前提 | A3非活性/A4両integrity全資源、本番固定名、A1〜A5確定 | blocking-human＋tracer回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer` | 04-01-02依存 | T-04-01/02/03 | pass: 04-HUMAN-EVIDENCE/04-TRACER-EVIDENCE。新通知leaseのW09/10は別途未実施 |
| 04-02-01 | 2 | START-01/03, FOCUS-01 | D-03/05/06/08、失効・protocol | 純粋状態＋故障注入 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py` | 作成済み | T-04-05/06/08 | pass: 04-02-SUMMARY、52 passed / 0.09秒 |
| 04-02-02 | 2 | START-01/02/03 | D-07、終了と1回引継ぎ | unit＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or simultaneous or takeover"` | 04-01-02依存 | T-04-06/07/08 | pass: 04-02-SUMMARY、14 passed / 42.59秒 |
| 04-03-01 | 3 | FOCUS-01/02 | D-01/02/04/13/14/15/16 | unit＋Tk/Win32境界 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_focus.py` | 作成済み | T-04-09/10/11/12 | pass: 04-03-SUMMARY、27 passed / 0.21秒 |
| 04-03-02 | 3 | FOCUS-02 | doc/Undo/OCR/入力同一性 | 回帰＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "focus_restore or working_state"` | 04-01-02/04-03-01依存 | T-04-09/10 | pass: 04-03-SUMMARY/EVIDENCE、20 passed / 90.17秒。人手評価はW01〜06 |
| 04-04-01 | 4 | START-03, FOCUS-01 | D-09/10/12/14、日英分類・font guard | unit＋i18n | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py` | 作成済み | T-04-13/15 | pass: 04-04-SUMMARY、notice 42 passed / 0.07秒 |
| 04-04-02 | 4 | START-03 | D-10/11/12、10秒・集約 | fake clock＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "notice_dedup or notice_timeout or notice_nonactivate"` | 04-01-02/04-04-01依存 | T-04-14/15 | pass: 04-04-SUMMARY、8 passed / 6.52秒。実時間は04-04-NOTICE-RUNTIME |
| 04-05-01 | 5 | 全5件 | 全経路とW01〜W12準備 | 統合＋全件回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "cross_entry or startup_acceptance"` | 作成済み | T-04-01〜17 | 指定受入pass: 6 passed / 22.23秒、全件結果は04-05-EVIDENCE |
| 04-05-02 | 5 | 全5件 | 自動証拠と全W移管の照合 | 証拠照合＋DoD | `.venv/Scripts/python.exe -m pytest -q tests/test_gsd_dod.py` | 既存・実機表作成済み | T-04-16/17 | pass: 19 passed/0.59秒、全W人手部分は06-UAT-CARRYOVERへnot-runのまま移管 |
| 04-06-01 | 6 | START-03 | backend構築失敗→独立案内、編集画面0、非活性表示 | unit＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice"` | 作成済み | T-04-13/14/15 | pass: 04-06-EVIDENCEと本監査の対象試験。CR-01の旧未捕捉経路を検査 |
| 04-06-02 | 6 | START-02/03 | 部分初期化解放・通知障害・8process集約・再起動 | fault injection＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or initialization_cleanup or notice_deadline"` | 作成済み | T-04-03/13/14/15 | pass: 04-06-EVIDENCEと本監査の対象試験。人手WはPhase6でnot-run |

表中START/FOCUSの略記はそれぞれV110-START/V110-FOCUSを示す。各コミット前の全件pytest、Python変更時のruff check/formatとASTは全タスク共通の追加ゲート。新設Windows試験は対象Windowsでskipを合格にしない。

## Dependency Graph / Scope

| Plan | Needs | Creates | Checkpoint | Wave |
|---|---|---|---|---|
| 04-01 | 出荷済みPhase 3、既存入口/DoD | 正しいDoD、隔離済み実Win32起動tracer、A1〜A5証拠 | 04-01-03明示blocking-human | 1 |
| 04-02 | 04-01本番境界と成立性 | 有界期限・失効・1回引継ぎ | なし | 2 |
| 04-03 | 04-02要求/ACK契約 | 状態/入力/モーダル復帰 | なし | 3 |
| 04-04 | 04-01通知primitiveと04-02/03結果分類 | 3分類の非活性10秒案内/集約 | なし | 4 |
| 04-05 | 04-01〜04実装と試験 | 統合結果・Windows UAT・Phase6移管追跡 | 証拠照合（実機はPhase6） | 5 |
| 04-06 | 04-05完了とCR-01指摘 | 構築前失敗の案内・部分資源解放・実main回帰 | なし | 6 |

04-01は3タスク（DoD前提修正・製品tracer・方式実機確認）、04-02〜06は各2タスク。各タスク5ファイル以下で、共有ファイルと1タスクずつの規約に従い6wave直列。raw見積もり54k/28k/26k/26k/16k/26k、校正factor=1/sample_count=0/confidence=low。既知DoD不整合の前提修正後、最初の製品実装はtracerとし、A1〜A5の実証前に後続へ進まない。

## レビュー反映・証拠の境界

04-REVIEWS.mdのsnapshot SHA-256はEA99835FB98FDB345DFF7FF31D4E37C4F62165056F9D48FA0305A4FD45A063CE。未コミットでありcommit SHAは存在しない。各PLANのRound 1 ledgerに採否を記録した。

| Review | 実行・検証箇所 | 未実施の扱い |
|---|---|---|
| R1 | 04-01-02から各子で_get_base_dir/_get_plugins_dirを隔離、元3ファイルhash/存在比較 | 全waveで共用。cwd変更だけは不合格 |
| R2 | peer照合→owner PIDへの許可委譲→1回前面化、失敗/入力後失効/expired | 04-01/03自動、W06/W12実機を分離 |
| R3 | Settings子閉鎖後、OCR所有messagebox、終了確認中、UI再構築後 | 04-03回帰とW05/W08 |
| R4 | I1〜I4、PendingIO quarantine、WndProc強参照、所有thread/有限cleanup | A1/A3とGC/取消し故障注入 |
| R5 | initializing/ready/closing/released、部分公開、短命reader、旧worker生存、同時claim | 04-02の状態表とW08。死亡未確認のD-07緩和なし |
| R6 | 通常全件pytestと明示A/W harness、実時間代表、UAC/別session | 自動failは停止、人手W not-runはPhase6リリース停止 |

DoDの完了順序は04-05 SUMMARY→Progress自動更新→validate-phase実走→VALIDATION実結果更新→全件pytest→正式Phase完了→DoD再確認。Progress=Complete/Phase[ ]は全PLANのSUMMARY存在・件数・完了日が整合した場合だけ検証待ち中間状態とし、未登録/重複/欠落/真の矛盾は違反を維持する。

## Multi-Source Coverage Audit

| SOURCE | ID | Feature / Constraint | Plan | Status |
|---|---|---|---|---|
| GOAL | Phase 4 | 作業画面を増やさず進行中作業を保って復帰 | 04-01〜05 | COVERED |
| REQ | V110-START-01 | 対応版/配置/入口の同一セッション1画面 | 04-01/02/05 | COVERED |
| REQ | V110-START-02 | 正常/強制/初期化例外後再起動 | 04-01/02/05 | COVERED |
| REQ | V110-START-03 | 判定/通信失敗の識別と有限終了 | 04-02/04/05 | COVERED |
| REQ | V110-FOCUS-01 | 復元・OS許可前面化・拒否通知 | 04-02/03/05 | COVERED |
| REQ | V110-FOCUS-02 | 未保存/Undo/OCR/モーダル維持 | 04-03/05 | COVERED |
| CONTEXT | D-01 | 正常復帰通知を追加せず表示維持 | 04-01/03 | COVERED |
| CONTEXT | D-02 | 最小化前の状態 | 04-03 | COVERED |
| CONTEXT | D-03 | 500ms固定の連打集約 | 04-02 | COVERED |
| CONTEXT | D-04 | 直前の入力先 | 04-03 | COVERED |
| CONTEXT | D-05 | 準備中無表示待機 | 04-01/02 | COVERED |
| CONTEXT | D-06 | 最大5秒 | 04-01/02 | COVERED |
| CONTEXT | D-07 | 確認済み死亡後1回引継ぎ | 04-02 | COVERED |
| CONTEXT | D-08 | 受信側期限失効 | 04-01/02/03 | COVERED |
| CONTEXT | D-09 | 確認済み理由と次の操作 | 04-04 | COVERED |
| CONTEXT | D-10 | 手動閉鎖と10秒自動終了 | 04-04 | COVERED |
| CONTEXT | D-11 | 原因別process間集約・延長なし | 04-01/04 | COVERED |
| CONTEXT | D-12 | 案内の非活性 | 04-01/04 | COVERED |
| CONTEXT | D-13 | 最深modal/入力/選択維持 | 04-03 | COVERED |
| CONTEXT | D-14 | OS拒否はタスクバーだけ | 04-03/04 | COVERED |
| CONTEXT | D-15 | 3回・250ms・2秒以内停止 | 04-03 | COVERED |
| CONTEXT | D-16 | 自動前面化再試行なし | 04-03/04/05 | COVERED |
| RESEARCH | R-01 | Tk前排他・版/配置非依存ID・Local境界 | 04-01/02/05 | COVERED |
| RESEARCH | R-02 | PID/生成時刻/process handleの公開・照合 | 04-01/02 | COVERED |
| RESEARCH | R-03 | 全I/O期限・overlapped・cancel・finite cleanup | 04-01/02/04 | COVERED |
| RESEARCH | R-04 | ID/世代/期限・accepted/terminal/expiredの区別 | 04-01/02 | COVERED |
| RESEARCH | R-05 | Tk mainthread queue・メインスレッド直前失効 | 04-01/02/03 | COVERED |
| RESEARCH | R-06 | 状態保存・grab/native modal・有限点滅 | 04-03 | COVERED |
| RESEARCH | R-07 | 独立通知lease・非活性・10秒・日英 | 04-01/04 | COVERED |
| RESEARCH | R-08 | 最小権限ACL・remote拒否・peer/入力検証 | 04-01/02/05 | COVERED |
| RESEARCH | R-09 | DoD誤判定・合成ツリー負例・PROJECT説明 | 04-01-01 | COVERED |
| RESEARCH | A1〜A5 | IPC/所有者公開/非活性/ACL/共有時計の成立性 | 04-01-02自動＋04-01-03実機停止条件 | COVERED、04-TRACER-EVIDENCEで実証済み。新leaseのW09/10は再受入待ち |
| RESEARCH | R-10 | pure/fault injection/subprocess/実機を分離 | 04-01〜05 | COVERED |
| RESEARCH | R-11 | 新依存なし・pyproject不変・全件ゲート | 全PLAN共通 | COVERED |
| RESEARCH | R-12 | 別権限/別session/Python入口/同時終了 | 04-01/02/05 | COVERED |

除外はCONTEXTのDeferred Ideas、Phase 5設定通知、Phase 6配布EXE最終統合/版同期。研究の候補を採用済み実装と誤認せずA1〜A5で検証する。MISSING項目なしは「計画の被覆」であり実装達成ではない。

## Spec-less Assumptions / Prohibition Recall

SPECなしedge probeは5件すべてunclassified/unresolved、verification/resolution/reasonはnull、probeは「unclassified — review manually」。04-01のE-START-01/02/03・E-FOCUS-01/02に明示し、独立した境界受入を各taskへ計画した。5件を自動resolved/backstopへ変換しない。

禁止事項recallの候補と採用3件は既存どおり保持する。通常品質は行動試験へ、ACL/入力検証はthreat_modelとsecure-phaseへ委譲する。未解決禁止事項はverification=nullをprojectProhibitionsへ渡し、serializerが出力するstatement/status: unresolvedだけを04-01/03/04のmust_haves.prohibitionsへ格納する。check_*なしでflagged-unverifiedを維持し、judgmentという検証済みtierを先付けしない。5 assumptions+3 prohibitionsを保持し、04-05で実機証拠を照合しても未分類probeを自動resolvedにしない。

## Wave 0 Requirements

- [x] 04-01-01: DoDの未完了・完了・未登録・archive・重複/矛盾の合成ケース。
- [x] 04-01-02: tests/test_startup_windows.pyの実subprocess tracerとA1〜A5観測記録。
- [x] 04-01-03: A3/A4と本番固定名の実機確認。通常pytestとは別の必須証拠。
- [x] 04-02-01: tests/test_startup_control.pyの状態遷移・故障注入・時計fixture。
- [x] 04-03-01: tests/test_startup_focus.pyの復帰/入力/モーダルfixture。
- [x] 04-04-01: tests/test_startup_notice.pyの原因/時計/非活性fixture。
- [x] 04-05-01: 04-WINDOWS-UAT.mdのW01〜W12観測表（作成完了、人手合格とは別）。
- [x] 04-06-01/02: constructor前失敗、部分初期化解放、独立通知と両入口を名前付き回帰で検証。
- 追加テストフレームワークは不要。空テストや検証済みメタデータの仮作成で合格にしない。

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| 通常/最大化からの最小化復元、入力先維持 | V110-FOCUS-01/02 | TkとWin32の実表示 | 各状態から再起動し画面状態・入力先を記録 |
| 入れ子モーダル、未保存編集、Undo/Redo、OCR維持 | V110-FOCUS-02 | 実操作とスレッド状態 | 操作中に再起動し内容・選択・進捗を確認 |
| 前面化拒否時の有限点滅 | V110-FOCUS-01 | OS制約 | 他アプリ入力中に起動、拒否後の再前面化がないことを確認 |
| 非活性の失敗案内・10秒・プロセス間集約 | V110-START-03 | ウィンドウアクティブ状態 | 連打・権限差・通信不能で表示数と期限と操作先を記録 |
| 異なる配置・権限・セッションと終了競合 | V110-START-01/02 | OS同期オブジェクトの実挙動 | 対応するPython入口で複数起動・終了注入、別セッションは独立確認 |

上記の未実施人手部分と実EXEの最終配布統合検証はPhase 6の06-UAT-CARRYOVER.mdへ全件移管済み。Phase 4の自動結果と混同しない。

## 04-05 Task 1の実行証拠（2026-10-22）

- 指定局所: **140 passed / 1 warning / 0.61秒**。
- 指定Windows受入: **6 passed / 53 deselected / 1 warning / 22.23秒**。選択6件にskipなし。
- コミット前の単一全件: **1603 passed / 1 warning / 212.88秒**。通常収集にUAC/ユーザー切替/クリック待ち/固定本番claimなし。
- ruff check: **All checks passed!**。ruff format: **1 file reformatted / 99 files left unchanged**。
  整形後のコードで全件を実行。pagefolio.py AST: **AST OK**。git diff --check成功。
- 警告は既存PyMuPDFのByteString DeprecationWarningのみ。
- W07の実時間記録、原本前後一致、閉鎖15秒以上後のHWND消失と残留0は`04-05-EVIDENCE.json`。
- T-04-16: 固定本番名は明示harnessでのみclaim。preflightだけに頼らず一次claimでも競合を拒否し、peerは毎snapshotのPID/生成時刻を照合。
  一次消失/不一致の負例2件で許可委譲なし・新rootなし・既存一次の復帰0を検証。
- T-04-17: W01〜W12/全16決定を`04-WINDOWS-UAT.md`へ対応付け、実証/故障注入/推定/not-runを区別。
- T-04-SC: 依存追加なし、pyproject.toml変更なし。製品CLI/版情報は変更していない。

## Validation Sign-Off

- [x] 全タスクに automated verify または作成依存がある
- [x] 連続3タスクに検証空白がない
- [x] 未作成テストを作成するタスクがある（全対象ファイル作成済み）
- [x] watch modeを使用しない
- [x] フィードバック時間を実測する
- [x] validate-phaseで実検証後にstatusとnyquist_compliantを更新する

**Approval:** 現行Phase4自動検証被覆はvalidated。移管人手受入はnot-run、リリース承認はpending。

承認済み再計画によりTask 2は証拠照合として完了。W11は利用者回答「別アカウントがない／切替できない」により準備不能not-run。
新通知の実クリック/100・150・200% DPI/両integrity作成順、実OS拒否の操作感と入口別の目視も未確認。
04-05-SUMMARY作成→Progress更新後にvalidate-phaseを実走した。Shared-IDは全5SUMMARYの存在により判定可能だが、要件台帳とPhase正式完了は親が行う。

## 2026-10-22 validate-phase実走

State A（既存VALIDATIONの監査）。Nyquist hook有効、5 PLAN/5 SUMMARY、11タスクのverifyと5要件の対応、pytest/pyproject構成を確認。
START-01/02はtracer/lifecycle/takeover/cross_entry、START-03はcontrol/notice/期限失効、FOCUS-01/02はfocus_restore/working_state/modal/OCRへ接続した。
自動検証のMISSING/PARTIALは0、5要件すべてCOVERED。既存試験を実走し204 passed/1 warning/190.22秒、失敗/ERROR/skipなし。
実行コマンド: `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_startup_windows.py tests/test_gsd_dod.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py`。
ギャップなしのためworkflow Step3→6、追加テスト・監査子エージェントは不要。手動項目は全W移管表を維持。
VALIDATION更新後の単一プロセス全件pytestは1603 passed/1 warning/209.19秒、失敗/ERROR/skipなし。120秒目標超過は除外せず保持した。次は親Phase正式完了→DoD再確認。

## Validation Audit 2026-10-21

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## 2026-10-22 04-06後のvalidate-phase再監査

State Aを再監査した。`verify:post` のnyquist hookは有効。6 PLAN/6 SUMMARY、13タスクとPhase 4の5要件を照合し、04-06のSTART-02/03回帰を上表へ加えた。既存のSTART-01/FOCUS-01/02は04-01〜05の実試験との対応を維持する。04-06後の単一全件1629 passed/1 warning/217.71秒は04-06-EVIDENCE.jsonの実測であり、この監査中には再実行していない。

本監査で `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice or initialization_cleanup or notice_deadline"` を実走し、25 passed、102 deselected、1 warning、9.75秒、終了値0。選択した試験にskipはない。要件対応の自動検証にMISSING/PARTIALは0、Nyquistは現行Phase 4の自動範囲についてcompliantを維持する。人手Wと実EXEは06-UAT-CARRYOVERでnot-runのままであり、本監査の合格に含めない。追加テスト不要のため監査子エージェントは起動せず、同一担当がインライン実施した。

## 正式完了後のDoD確認（2026-10-22）

validate-phase後の単一全件pytestは1629 passed / 1 warning / 228.84秒（終了値0）。その後phase.completeを実行し、要件ID解析警告の5件はrequirements.mark-completeで全10書込面の成功を確認。ROADMAPのPhase行・ProgressとSTATE/state.jsonを同期した。正式完了後の tests/test_gsd_dod.py は19 passed / 1 warning / 0.64秒（終了値0）。W未実施とWR-01の移管は維持する。

追補: 改行整備後のDoD再確認は一時ディレクトリへのPermissionErrorとなったため、同一19件をサンドボックス外で実行し19 passed / 1 warning / 0.16秒（終了値0）。製品テストの失敗ではなく試験用tempへのアクセス制限だった。

## 2026-10-24 Phase 6前提の再監査（Phase 5変更後）

Phase 4検証報告のstale解消（`dd10ce7`、21/21 passed、digest `v3:sha256:5011dcc6...`）に続き、06-04最終build前の依存として実走した。現行HEAD（`dd10ce7`）で `tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_gsd_dod.py tests/test_startup_windows.py` を実行し **238 passed, 1 warning in 276.15s**、失敗/ERROR/skipなし（basetemp `C:\Users\shdwf\AppData\Local\Temp\pf04_validate_1792826444`）。5要件のMISSING/PARTIALは0でNyquist compliantを維持する。追加テストは不要のため監査子エージェントは起動していない。人手Wと実EXEは06-UAT-CARRYOVERでnot-runのままであり、本監査の合格に含めない。
