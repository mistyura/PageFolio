---
phase: "06"
slug: "release-validation"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-24"
---

# Phase 06 — 検証戦略

6計画・12タスクの検証契約。実装・ビルド・実機受入は未実施。下表は実行担当と依存の割当であり、合格記録ではない。

## Test Infrastructure

| 項目 | 内容 |
|---|---|
| Framework | 既存 pytest 9.1.1 |
| Config | pyproject.toml（編集禁止） |
| Quick | `.venv/Scripts/python.exe -m pytest -q tests/test_release_build.py tests/test_release_contract.py --basetemp="$env:LOCALAPPDATA\Temp\pf06_quick_$([guid]::NewGuid().ToString('N'))"`（Wave 0で新設） |
| Full | `.venv/Scripts/python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf06_full_$([guid]::NewGuid().ToString('N'))"` |
| 所要時間 | quick目標30秒、全件参考266.81秒。新規試験後は再計測 |

## Sampling Rate

- タスクごとに影響する局所試験。Python編集時はRuff check、Python対象format、再lint、pagefolio.py AST確認。
- コミット前とwave末に単一プロセスの全件pytest。対象コード・入力・環境が一致する成功済み証拠は同一性を確認して再利用し、無理由に再実行しない。
- GUI/foreground試験を並列実行しない。局所/全件ともpytest実行ごとに未使用のrepo外basetempを指定。
- DEP-05、owner_missing、通知前景不一致、Tcl警告、未分類edgeの同種失敗再発で実装・後続実行・コミットを停止。最初の失敗とresult.json、traceback.log、poll/reader/process診断を保持し該当gsd-debugへ戻る。期限延長・skip・除外は禁止。
- 最大フィードバック待ち時間は局所30秒目標、全件は参考約267秒。実測結果で記録し直す。

## Per-Task Verification Map

| Task / Wave | Requirement | 自動検証・実測 | Threat Ref | 状態 |
|---|---|---|---|---|
| 06-01-01 / 1 | DIST-01/02/03, QA-01 | TestReleaseTracerのargv/保護負例→repo外の実CLI一回、pytest内は実buildなし | T-06-01/02 | not-run |
| 06-01-02 / 1 | DIST-02/03, QA-01 | test_release_build.py全件、保護3名/競合/障害/旧tree/限定-text bytes | T-06-01/02/03 | not-run |
| 06-02-01 / 2 | DIST-01, QA-03 | TestVersionAndDocs/TestSampleSourcesを新設 | T-06-04/05 | not-run |
| 06-02-02 / 2 | DIST-02/03, QA-03 | TestGuideAndWorkflowを追加、契約全件 | T-06-04/05 | not-run |
| 06-03-01 / 3 | QA-01/02, DIST-03 | TestIsolation/TestOwnership/TestEvidenceAuditを新設 | T-06-06/08 | not-run |
| 06-03-02 / 3 | QA-01/02 | TestFakeOcr/TestSettingsFaultPreparationを追加 | T-06-07/08 | not-run |
| 06-04-01 / 4 | DIST-01/02, QA-01/02/03 | actionで実v1.10.0初回/再build各1回→read-only audit --build-only | T-06-09/10 | not-run |
| 06-04-02 / 4 | DIST-03, QA-02 | 実保護/起動/更新、1page実EXE接続/native modal＋人手→audit --preparation-only | T-06-09/10 | not-run |
| 06-05-01 / 5 | QA-02 | TestCaseCoverageを追加、24枝番+WR-01+X6のカード | T-06-11/12 | not-run |
| 06-05-02 / 5 | QA-02/03, DIST-02/03 | audit --require-pass（担当16ID全subrow）＋G1〜G6の人手結果 | T-06-11/12 | not-run |
| 06-06-01 / 6 | QA-02 | audit --require-pass（担当15ID全subrow）＋G7〜G14の人手結果/時間契約 | T-06-13 | not-run |
| 06-06-02 / 6 | QA-01/02/03 | 台帳入力確定→品質全件一度/同一性再利用→証拠記録→read-only audit --for-handoff・全人手pass/Phase4鮮度・親4ゲートの担当/pending引渡し | T-06-14 | not-run |

IDはすべてV110-接頭辞。各PLANのautomated直後にfails_whenを置く。allow-pendingは台帳構造だけを検証し、人手passの代替にはしない。

## 引渡し前監査と親ゲート後の最終監査

audit APIは06-03-PLANのaudit_contractを正本とする。--allow-pending（途中の構造監査）、--for-handoff（全実機/品質が揃った引渡し準備監査）、flagなし（親ゲート後の最終監査）を区別する。--require-passは指定IDの全入口/条件subrowに実測根拠付きpassを要求するtask完了監査、--build-onlyは確定2runと配布/historyの読取照合、--preparation-onlyは保護/実接続/障害成立と人手回答の監査である。これらと--allow-pending/--for-handoffの5flagは相互排他。06-03-01のTestEvidenceAuditは同じ証拠fixtureについて、親4ゲートのみpendingなら引渡し成功/最終失敗、4ゲートの根拠付きpass反映後だけ最終成功となる正負両方向を検証する。

| 順序 / 担当 | コマンド・成果物 | 成功条件 / 停止条件 |
|---|---|---|
| 1 / 06-06-02実行担当 | 共通Ruff/format/AST、上記Full（同一性付き成功再利用可）→06-EVIDENCE/06-RELEASE-GATEへ結果記録 | 全必須人手pass、build/protection/版/品質と現行入力一致、Phase4 fresh。失敗/未実施/古い証拠なら引渡し停止 |
| 2 / 06-06-02実行担当 | `.venv/Scripts/python.exe tests/release_uat_support.py audit --phase-dir .planning/phases/06-release-validation --for-handoff` | 親のcode-review/secure-phase/Nyquist/独立verificationだけpendingで、各担当・実行手段・期待報告が明記されていればexit0。handoff_ready=true、phase_complete=false、release_allowed=false。その他の未達・既知失敗・対象不一致はnonzero |
| 3 / 親orchestrator | `$gsd-code-review 06`、`$gsd-secure-phase 06`、`$gsd-validate-phase 06`、独立verifierのgoal-backward verification | 実走して報告path/hash・対象入力・exit・時刻・判定を06-RELEASE-GATEへ反映。VALIDATIONは実測に基づく更新だけ。修正が入れば影響する証拠/品質/実機を再検証する |
| 4 / 親orchestrator | `.venv/Scripts/python.exe tests/release_uat_support.py audit --phase-dir .planning/phases/06-release-validation` | 4独立ゲート成功、未評価/未解消high threat 0、Nyquist実走合格、全必須人手pass/Phase4 fresh/現行入力一致、未解除リリース条件の根拠付き評価でexit0。pending/not-run/fail/stale/根拠不足があればPhase完了・出荷停止 |

06-06-02のdoneは手順2の引渡し準備まで。手順3〜4は親の担当であり、その結果を手順2の前提にしない。最終監査もPhase完了フラグを前提にせず、親は手順4の成功後に正式完了を判断する。未評価high threatと未実走Nyquistは引渡し時に親担当pendingとして保持するが、最終監査では必ず不合格になる。W11等の人手not-runはこの例外に含まれず、06-06-02はblocked集計までとする。

## Wave 0 Requirements

- [ ] 06-01-01先頭でtests/test_release_build.pyを新設し、そのtaskのverify前にCLI境界を固定する。
- [ ] 06-02-01でtests/test_release_contract.pyを新設し、06-02-02/06-05-01で拡張する。
- [ ] 06-03-01でtests/release_uat_support.pyとtests/test_release_uat_support.pyを新設。既存harnessのentryはscript/module/relocatedのみ。auditの全モードと担当行/読取専用build/準備/引渡し/最終監査の正負fixtureを同taskで作る。
- [ ] 06-03-02でtests/release_fake_ocr.pyを作り、06-04-02で既存Ollama設定を通した実配布EXE接続を実証する。
- [ ] 06-05-01で06-UAT.md/06-MANUAL-EVIDENCE.jsonへ全カードとnot-run行を作る。テスト専用binary/faultを実配布のpassへ転用しない。

Wave 0は独立した水平実装計画ではなく、各作成taskの先頭に置く試験scaffold。依存順は06-01→02→03→04→05→06。現時点で全scaffold未実装。

## Manual-Only Verifications

正本は06-UAT-CARRYOVER.mdおよび04-WINDOWS-UAT.md。必須ケースは W01、W02、W03、W04、W05a、W05b、W05c、W06、W07a、W07b、W08a、W08b、W08c、W08d、W09a、W09b、W09c、W09d、W10a、W10b、W11、W12a、W12b、W12c、WR-01。各枝番を計画・UATに割当し、入口・条件単位の結果を残す。

- 少数ずつPython→EXEの順に案内し、ケースID＋観察結果を受け取ってから次へ進む。
- 対象commit/差分hash、OS/Python/Tk、権限/session、入口、binary hash、観測時刻、結果、ログと必要な画面記録を保持。
- 別session未準備はnot-run。新規アカウント・資格情報取得・mockで代替しない。
- WR-01の並行負荷15609msと単独15140msを保持し、15.5秒契約の再評価を追跡。
- Phase5 H01〜H14と意味評価2件のpassは正本の同一性を照合して再利用。EXE固有受入は新規IDで扱う。
- Phase4 staleの再検証を必須依存として残す。未解除原因を全件成功で解決済みにしない。
- 全必須実機passと品質/security/Nyquistの証拠が揃うまでPhase6完了・リリースを停止。

## ケース別のPLAN/UAT割当

全行のカード作成は06-05-01、UAT正本は06-UAT.md、結果は06-MANUAL-EVIDENCE.json。全行not-runから開始し、共通操作はPython→EXE、専用faultは証拠種別を明示する。

| Case | 組 | 実施task | 必須観測 | 状態 |
|---|---|---|---|---|
| W01 | G1 | 06-05-02 | normal/zoomed、state/geometry/status | not-run |
| W02 | G1 | 06-05-02 | settings/thumb/preview実入力/selection/カーソル | not-run |
| W03 | G2 | 06-05-02 | 未保存3頁PDF・Undo→Redo→Undo→Redo | not-run |
| W04 | G2 | 06-05-02 | 1page画像PDF/並列1の同page-attempt・進捗/完了 | not-run |
| W05a | G3 | 06-05-02 | 入れ子を閉じた外側入力 | not-run |
| W05b | G3 | 06-05-02 | hold中のOCRDialog閉じる確認→peer→いいえ→同処理完了 | not-run |
| W05c | G3 | 06-05-02 | 終了No・編集/排他保持 | not-run |
| W06 | G7 | 06-06-01 | 実OS拒否・有限点滅・15秒再前面化なし | not-run |
| W07a | G7 | 06-06-01 | slowready・5秒失効・10秒案内・遅延復帰0 | not-run |
| W07b | G8 | 06-06-01 | busy・expired queue副作用0 | not-run |
| W08a | G9 | 06-06-01 | 初期化死亡/同時claim/引継ぎ1回 | not-run |
| W08b | G9 | 06-06-01 | 正常/強制/初期化/公開前例外後再起動 | not-run |
| W08c | G10 | 06-06-01 | Noのmutex/Yes後の新一次 | not-run |
| W08d | G10 | 06-06-01 | root/worker/released/古mapping/同時claim/OS死亡 | not-run |
| W09a | G11 | 06-06-01 | 新noticeクリック/入力非干渉/10秒/集約/閉鎖後15秒 | not-run |
| W09b | G11 | 06-06-01 | 実DPI100% | not-run |
| W09c | G12 | 06-06-01 | 実DPI150% | not-run |
| W09d | G12 | 06-06-01 | 実DPI200% | not-run |
| W10a | G13 | 06-06-01 | medium→elevated・4資源/UAC | not-run |
| W10b | G13 | 06-06-01 | elevated→medium・4資源/UAC | not-run |
| W11 | G14 | 06-06-01 | 既存別session各1画面/復帰/元状態保持、未準備は停止 | not-run |
| W12a | G4 | 06-05-02 | script/module/relocatedの一次二次3×3 | not-run |
| W12b | G4 | 06-05-02 | 最終実EXE/Python/来歴固定の実tracer peer/別配置の双方向 | not-run |
| W12c | G4 | 06-05-02 | Explorer/端末・実入力/foregroundとAPI戻り別記 | not-run |
| WR-01 | G8 | 06-06-01 | 15609msと15140ms保持・15.5秒契約再評価 | not-run |

X01〜X06は06-05-02/G5〜G6。missing/corrupt/unreadable/write-replace/FIFO-rebuild-exit/サンプル利用更新版表示を実EXE固有のsubrowで確認する。

## 共通品質ゲートの具体コマンド

Python変更後: `.venv/Scripts/ruff.exe check .` → `.venv/Scripts/ruff.exe format . --config "include = ['*.py', '*.pyi', '*.ipynb']"` → 同じRuff check → `.venv/Scripts/python.exe -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read()); print('AST OK')"`。

コミット前/wave末/人手受入前は上記Fullを単一processで実行。新規GUIDのrepo外basetempを検証してから利用する。前回1797 passed/1 warning/266.81秒は履歴で、103入力manifestだけで新規test/build入力を含む今回の同一性を主張しない。全入力・環境を照合できた場合だけ再利用。再発停止の診断は最初の実測を保持する。

Phase4 staleの再検証は親がWave3終了後かつ06-04-01の最終入力固定前に担当する。$gsd-execute-phase 04の再検証経路を使い、完了済みplanのためverifierが呼ばれなければ親が同workflowの独立verifier/必要なvalidate-phaseを明示実走する。既存W移管は維持しfresh化を人手合格にしない。06-05-02開始前と06-06-02引渡し前にもdigestを照合する。W11がnot-runなら06-06-01未完了。06-06-02はblocked集計までで、Nyquist/Phase完了を偽装しない。

Phase6 edge6はunclassified/unresolved、禁止6はdescriptorless flagged-unverified。Phase4禁止3/edge5とPhase5edge4を別集合で保持する。試験計画の存在はprobe解決の証拠ではない。

## Reviews Round 1 — 実行・再開・失効の契約

基準レビューcommit: 8b513b8。採否の正本は各06-01〜06-06-PLAN.mdのReview Dispositions Ledger。下記は計画であり未実行。

- buildの最終入力はcommit+dirtyhash・全入力manifest・依存版で固定する。既存dirtyは取消/自動commitせずtask hunkのみstage。無関係hunkが分離できなければ親へ返す。
- 実build前に絶対entry/icon/spec/work/dist・既定dist成功・重複/reparse/保護名の負例をpytestで確認する。tracerはrepo外。最終版は06-04 actionで初回/再buildの2回のみ、verifyで第三buildをしない。
- 配布元は直接起動せず完全copyで受入する。詳細CONFIGURATION文書も同梱し、そのhashとガイド相対リンクを確認する。
- 06-04-02完了はpreparation-onlyが保護/接続/native modal/障害成立と回答を全件要求する。G1〜G6はrequire-pass W01,W02,W03,W04,W05a,W05b,W05c,W12a,W12b,W12c,X01,X02,X03,X04,X05,X06、G7〜G14はrequire-pass W06,W07a,W07b,W08a,W08b,W08c,W08d,W09a,W09b,W09c,W09d,W10a,W10b,W11,WR-01。allow-pendingは完了verifyに使わない。
- OCR接続/W04/W05bは1page画像PDF・対象1page・並列1・summaryなし。W03の3page編集用PDFと区別する。W05bは実行中の閉じる確認で発火させ、エラー応答だけでmodalが出るとは仮定しない。
- X01は起動安定時まで不存在/無警告、終了時の正当な保存は別観測。版はAbout/folder/report、タイトル変更なし。設定故障は外部lock・tmp/元hash・操作/通知時点で確認し、noconsole DEBUG logを前提にしない。
- W12bは06-05のpeer_contractを適用。v1.10.0最終実EXEを主対象とし、06-01実tracerの別版peerは来歴/実版/source hashと役割を分離する。公式旧版リリースや本番主対象の代替として扱わない。検証不能なpeerの枝はnot-run。
- 中断時はrun/対象hash/Phase4 digest/環境/回答済みと未実施subrow/所有資源回収を保存。同一性確認後だけ残りから再開する。元passを消さず変更理由とsuperseded_byを追記し、新世代行をnot-runから作る。

| 変更 | 必須の戻り先/失効範囲 |
|---|---|
| 製品・起動/通知コード、build依存/収集設定 | Phase4対象なら親再検証→品質→06-04の2回build/保護/接続→全production-exe人手行を新hashで再実施 |
| Pythonのみのfixture/観測/環境 | 影響するPython/EXEカードと観測証拠を失効。入力/環境/covered_digestが同じ無関係行だけ再利用 |
| 同梱文書/版表示 | 同梱/版/X06/契約試験を更新。EXEhash変更なら全EXE行も再実施 |
| UAT回答・ケース宣言等、TestCaseCoverageの入力 | 台帳内容確定後に品質ゲートを評価。品質証拠の出力だけを自己参照hashへ含めない |
| WR-01同負荷再計測が15500ms超 | fail/出荷停止→debugと修正、または利用者の明示承認を得た契約再計画。負荷縮小・期限延長で黙示合格にしない |
| W11既存別session準備不能 | not-run/出荷停止、親から準備継続か明示承認を要する再計画へ。アカウント新設・mock代替なし |

全件pytestは台帳入力確定後に一度実行するか同一性を検証した成功を再利用し、06-EVIDENCEに記録した後のverifyはread-only for-handoffだけとする。必要な再実行を回避するため入力を証拠出力と偽装しない。

## Validation Sign-Off

- [ ] 全タスクにautomated verifyまたはWave 0依存
- [ ] 連続3タスクの検証欠落なし
- [ ] 新設試験・EXE adapterをWave 0へ割当
- [ ] watch modeなし
- [ ] ケースID全件の計画・UAT対応
- [ ] 実装後gsd-validate-phaseで検証し、根拠に基づく状態更新

**Approval:** pending。計画レビュー合格と実行後のvalidatedを区別する。
