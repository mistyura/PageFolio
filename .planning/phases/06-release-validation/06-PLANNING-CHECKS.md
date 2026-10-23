# Phase 06 — 計画監査

## Reviews再計画 Round 1（2026-10-24、レビュー基準 8b513b8）

### コミット前の全件ゲート（親、2026-10-24）

**後続デバッグで今回のテスト保留を解除:** `config-notice-tk-lifecycle`でDnD初期化失敗→残留root→後続画像先不一致を故障注入で確認し、通知再構築テストの不要DnD依存だけを除去。修正後native単一全件は1797 passed / 1 warning / 269.43秒 / exit 0、Ruff check（native再確認で警告なし）・format・ASTも合格。証拠は`.planning/debug/config-notice-tk-lifecycle-evidence/RESULTS.md`。製品コード・版番号変更なし。以下は初回失敗の履歴として保持し、外部tkdnd間欠原因・DEP-05等の未解除条件とPhase6実機受入/出荷停止は維持する。

テスト隔離修正と専用証拠は `98dd70a` に分離commit。今回の計画差分とは別commitにし、既存のrequirements/startup診断/config等のdirtyは取り込まない。検証はそれらを含む現行作業ツリーで実施したもので、clean checkoutだけの検証とは区別する。rawログのCRLF・pytest由来の末尾空白は証拠SHA保持のため変更しない。差分空白検査ではrawログだけを除外し、編集したコード/Markdown/JSONを確認する。

- 初回sandbox: 1700 passed / 68 failed / 29 errors / 4 warnings / 193.95秒 / exit 1。`Cannot find a usable init.tcl`が多発。ログ`06-reviews-pytest-sandbox.txt`、basetemp `C:/Users/shdwf/AppData/Local/Temp/pf06_reviews_20261024-055130`を保持。
- sandbox外の最小Tk起動は9.0.4で成功。そのため別の新規basetempで全件を一度再実行した。
- native: 1795 passed / 2 failed / 2 warnings / 269.56秒 / exit 1。`tests/test_config_notification.py::TestNotificationLifecycle::test_real_rebuild_restores_same_notice_in_current_language`が`can't find package tkdnd`→`Unable to load tkdnd library.`、`TestLoadTracer::test_corrupt_settings_show_one_real_toast_and_keep_pdf_editable`が`image "pyimage9" does not exist`。原因未確定。ログ`06-reviews-pytest-native.txt`、basetemp `C:/Users/shdwf/AppData/Local/Temp/pf06_reviews_native_20261024-055832`を保持。
- 両ログはTemp原本からコピーしSHA-256一致確認済み。既存dirtyの製品コードは変更せず、修復・除外・期限延長・追加再試行はしていない。計画検証の合格とコミット前pytestの未合格を分離し、commitと後続実行を保留する。次はGSD debugで2件を調査する。Phase6の製品実装/build/人手UATは未実施。

親の独立checkerは今回改訂後に `VERIFICATION PASSED`（blocker 0 / warning 0 / info 0）を返した。6要件・D-01〜16・レビューR06-01〜12の反映を確認。decision-coverageは16/16、post-planning gap-analysisは22/22、未被覆0。verify-failure-directionsはtask内15件ok/readError=null。verify-command-pathsは15件not_applicableでありPythonコマンドのパス実在確認を意味しない。製品実装・build・実機受入の合格ではない。

今回の正本は各PLANのReview Dispositions Ledger。旧「最終計画レビュー」「Checker revision」は前回計画時の履歴であり、今回の独立checker合格として再利用しない。R06-01〜12と全current actionable個別指摘に採用/見送りを明記した。plannerは製品コード・STATE・ROADMAP・CONTEXT・レビュー原文・既存dirtyを編集していない。親は検証後にSTATEの再開説明を更新し、既存dirtyを保持した。

| 対象 | 今回の実行契約変更 |
|---|---|
| 06-01 | 絶対argv、既定dist正例、実build前の境界負例、repo外tracer、限定-text属性、process/lock、同梱詳細文書 |
| 06-02 | dirty hunk分離、最新節/最終更新欄、offline詳細リンク、古lock/保持容量の手動手順 |
| 06-03 | 全subrow require-pass、read-only build/preparation監査、1page画像OCR、実在W05b modal、外部設定障害証拠、再開/失効契約 |
| 06-04 | 実build2回と読取verifyの分離、最終build前の親Phase4再検証、実接続/保護の完了監査 |
| 06-05 | 来歴固定の別版peer、X01無警告/About表示、EXEの手動状態準備、担当16ID全subrow監査 |
| 06-06 | 担当15ID全subrow監査、WR-01不適合分岐、W11判断依頼、台帳確定後の全件一度とread-only引渡し |

6 plans / 6 waves / 12 tasks / tracer先頭を維持。各task最大5変更ファイル。追加の実装予定ファイルは06-01-02の.gitattributesだけで、正本4パスへの-text属性を扱う。既存CONFIGURATIONは配布時にcopyするが新しいsource正本を複製しない。見積はcalibration実測factor=1/sample_count=0/confidence=low、合計174000 tokens（38000/17000/42000/24000/26000/27000）。scopeを縮小していない。

### Reviews source coverage

| SOURCE | ID | Plan / Task | Status |
|---|---|---|---|
| GOAL / REQ / CONTEXT | 既存5成功条件・6要件・D-01〜D-16・持越し条件 | 下記Multi-Source Coverage Auditの既存割当を維持 | COVERED（計画割当のみ） |
| RESEARCH | 出力境界/私有作業先/原本bytes | 06-01-01/02。旧記述の曖昧な「ソースとの親子重複」は操作先ごとの判定へ具体化 | COVERED |
| RESEARCH | 詳細文書の到達性 | 06-01-01 + 06-02-02で同梱docs/CONFIGURATION.mdを選択 | COVERED |
| RESEARCH | 実EXE接続/故障/証拠種別 | 06-03-01/02 + 06-04-02 + 06-05-01/02 | COVERED |
| RESEARCH | Phase4再検証・最終品質・未解除 | 06-04 phase4_dependency / 06-06-01/02 | COVERED |
| REVIEWS | R06-01/02 | 06-01-01/02/build_contract | COVERED |
| REVIEWS | R06-03 | 06-03-01 audit_contract / 06-04-01 | COVERED |
| REVIEWS | R06-04 | 06-03 resume_contract / 06-04 phase4_dependency / 06-05/06 | COVERED |
| REVIEWS | R06-05 | 06-05 peer_contract / 06-05-01/02 | COVERED |
| REVIEWS | R06-06 | 06-06-01 | COVERED |
| REVIEWS | R06-07/08/09 | 06-03-02 / 06-04-02 / 06-05-01/02 | COVERED |
| REVIEWS | R06-10 | 06-05-02 | COVERED |
| REVIEWS | R06-11 | 06-03 audit_contract / 06-04-02 / 06-05-02 / 06-06-01 | COVERED |
| REVIEWS | R06-12 | 全PLAN execution_rules / 06-02-01 / 06-04-01 | COVERED |

各reviewerのLOW/MEDIUM追加案（改行、ガイド成果物、lock/timeout、rename retry、容量、索引、mainリンク、plugins、audit独立点検、copy再利用、再開、W06試行上限、品質二重実行）も関連PLANのledgerで採否を記録。Antigravityの架空path/API/要件/About説明とatomic要約はConsensus訂正を優先し、実装へ採用しない。

### Current runtime checks / source grounding

- GSD init/stateを読取、query agent-skills gsd-planner --skills-onlyは設定なし。project skillはsession-handoffのみ。graphify statusはdisabled。追加研究/mapperは再実行せず06-RESEARCH/06-PATTERNSと親のソース訂正を再利用。
- plan:pre activeHooksのplanner contribution4件を確認。assumption-delta scan 6はdetected=false/signals=[]。schema対象なし。改訂後の全PLAN＋ROADMAPをapi-coverage.cjsへ入力しdetected=false/signals=[]、既存COVERAGE.mdの理由を維持。security ASVS1/highとT-06-01〜14の一意性を維持。
- 親の今回precheckはcontext-drift stale=[]、codebase-drift skipped/no-mapped-commit、UI frontend=false/block=false。下段の旧precheck記録を今回結果へ読み替えない。
- git ls-filesで既存の2原本、pagefolio.py/pagefolio.ico、constants/settings/app/ocr/ocr_dialog/ollama/about、docs/CONFIGURATION/DEVELOPMENT、README/開発履歴、tests/conftest/test_gsd_dod/test_startup_windows/config_notice_support、.gitignoreを確認。引用pathは実在するtracked source。新規.gitattributes、distribution/、tools/build_release.py、tests/test_release_*とrelease_uat_support/release_fake_ocr、後続BUILD/PROTECTION/UAT/MANUAL/EVIDENCE/RELEASE-GATEは実装予定であり現存扱いしない。
- SPECなし。親の今回edge-probeは全6件unclassified/unresolved、verification/resolution/reason=null、probe=unclassified — review manually。coverage applicable6/resolved0/unresolved6/unclassified6。下段のflagged assumptions・prohibition recall/projectProhibitions/descriptorless契約をそのまま保持する。
- frontmatter.validate --schema planとverify.plan-structureは全6PLAN valid=true、errors0/warnings0、各2task。静的検査は12task/17automatedの直後fails_when、各task最大5files、D-01〜16、6要件、T-06-01〜14一意、全PLANのRound 1 ledgerを確認（errors=[]）。局所/全件の全pytestコマンドはGUID付きrepo外専用basetempを使う。末尾</output>、継続sentinelなし。git diff --checkはexit0。製品の実装/pytest/build/manualはこのplannerでは未実施。独立checkerとcommitは親担当。


## 最終計画レビュー（2026-10-24）

- 独立checker初回はblocker2/warning1。revision1の後、別のcheckerが再評価し `VERIFICATION PASSED`、blocker0/warning0/info0。
- 調査Open Questionsの計画上の処置、引渡し監査と親4ゲート後の最終監査の順序、試験analogの具体参照を修正した。実機未実施・回帰原因未解除は維持。
- 決定論チェック: decision-coverage-planは16/16、gap-analysis.plan-postは要件6＋決定16の22/22、いずれもpassed。verify-failure-directionsは15/15、readErrorなし。
- verify-command-pathsはPython形式に対し全15件not_applicable。パス検証成功とは扱わず、checkerが新規成果物と作成順の依存を確認した。
- UI gateはfrontend=false/block=false。context/codebase driftはそれぞれ比較資料なし・mapped commitなしでskipped。
- モデルresolverはresearcher/mapper/checkerへsonnet、plannerへopusを返したが、この環境で選択できないためセッションモデルを継承。typed agentの役割分離とresolver指定effortは維持した。
- 製品の実装・実build・Phase06実機受入は未実施。VALIDATIONはdraftのまま。計画の合格をPhase完了や出荷承認へ読み替えない。

作成: 2026-10-24 JST。plannerは計画だけを作成。親が行ったコミット前pytestは以下に記録する。製品実装・build・実機受入は未実施。

## 親のコミット前全件ゲート

- サンドボックス内の初回はTclのinit.tclを発見できず、最初のTk fixtureで1 ERROR / 3 warnings / 0.67秒 / exit 1。ログ: `C:/Users/shdwf/AppData/Local/Temp/pf06_plan_69f62963f8464e468968619de7ddbddf.log`。全件成功に含めない。
- 承認された通常Windows環境で、新しいrepo外専用basetempを使い `.venv/Scripts/python.exe -m pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf06_plan_native_cc3bbc3d70a4408da8f501341441b69f` を単一プロセス実行。**1797 passed / 1 warning / 274.44秒 / exit 0**。テスト除外・skip追加・期限延長なし。警告はPyMuPDFのByteString非推奨。
- 通常環境ログ: `C:/Users/shdwf/AppData/Local/Temp/pf06_plan_native_cc3bbc3d70a4408da8f501341441b69f.log`。同名ディレクトリに実行時診断を保持。
- 対象は既存dirtyコードを含む現ワークツリー。Phase06の新規製品機能は未実装。今回の成功をDEP-05等の原因解決・Phase04鮮度回復・実機合格としない。
- GSD state.planned-phaseはReady to executeを機械status executingへ写像する。state.jsonはROADMAPのPlannedをin_progressへ写像するが、実行済みtaskは0/6、STATE本文で実行未着手を明示。ROADMAP更新後に正規publishStateContractで再生成した。

## Discoveryと適用条件

- Level 0（実装計画のコード接点確認）: 完了済み06-RESEARCHと06-PATTERNSを使用。新依存・追加外部サービス統合なし。既存Ollamaの現コードから /v1/models・/v1/chat/completions と ollama_url/ollama_model を確認し、fake接続を具体化した。
- 標準mode / coarse / tracer=true / reversibility=true / MVP=false。1taskずつ、全6wave直列。最大5変更ファイル/task。
- estimate-calibration: factor=1、sample_count=0、confidence=low。raw/tokens合計150000（各plan内は15000〜34000）。実測ではなく投影。
- agent-skills gsd-planner --skills-only: 設定なし。project session-handoffを読取。graphifyはdisabled、文書地図は古いため現物/研究を優先。
- history-digestからPhase4/5を選択し04-06/05-04 SUMMARYと最新STATE/UATを照合。SUMMARYの古い未完了記載より現行STATEと最新UATを優先する。
- Write/Edit専用toolがないため、新規PLANはapply_patch Add File、既存VALIDATION/ROADMAPは限定Update Fileで作成。

## plan:pre contribution適用

JSONをparseし、activeHooksのkind=contributionかつinto=plannerのみ4件を取得した。

| Contribution | 適用/結果 |
|---|---|
| api-coverage | ROADMAP Phase6＋全PLANをdetectorへ入力。detected=false、signals=[]。製品の外部API統合は追加せず、既存Ollama経路へのloopback試験のみ。COVERAGE.mdに理由を残す |
| assumption-delta | 親実測detected=false。identityの新決定なし |
| schema-gate | Phase6/CONTEXT/RESEARCH/全files_modifiedにPayload/Prisma/Drizzle/Supabase/TypeORM schema対象なし。push不要 |
| security | 全PLANにASVS1/security_block_on=highの脅威表。T-06-01〜14はphase内一意、T-06-SCのみ予約共有 |

親のprecheck: ui frontend=false/block=false、context drift=no-upstream-artifacts、codebase drift=no-mapped-commit。これらは製品の合格証拠ではない。

## 依存とファイル所有

| Plan / Wave | needs | creates / 利用者ができること | checkpoint / human |
|---|---|---|---|
| 06-01 / 1 | 既存サンプル、品質baseline、既存PyInstaller | 専用CLIで安全なサンプル付きonedirを生成 | 実build、既存環境依存 |
| 06-02 / 2 | CLI/正本/ガイド | v1.10.0と利用・更新・build手順の一致 | なし |
| 06-03 / 3 | CLI/report契約と版 | 実EXE隔離観測・fake OCR/障害準備 | 実EXE接続は次planで証明 |
| 06-04 / 4 | 全build入力/adapter | 最終版の実初回/再build、保護、接続実証 | OCR開始/観察のhuman-check |
| 06-05 / 5 | 固定binary/準備、Phase4 fresh | 全カード・一般操作/入口/EXE設定受入 | 小分けhuman-check |
| 06-06 / 6 | 一般操作受入 | OS条件/別session/最終品質を証拠で判定し親の独立ゲートへ引渡し | 小分けhuman-check、W11未準備なら停止 |

同waveは各1planなので共有ファイル競合なし。Windows foreground、出力lock、同じrelease treeと証拠台帳が非ファイル依存。Phase4再検証は親の別workflowで、06-05実機開始と06-06完了に必須。W11の準備不能は計画作成を妨げず実行完了を妨げる。

06-06-02の検証順は品質→証拠記録→audit --for-handoff→親へ引渡し。親がcode-review/secure-phase/Nyquist/独立verificationを実走して結果を反映した後、flagなしauditで最終判定する。引渡し時に許容できるpendingは親の4独立ゲートのみで、人手not-runや既知失敗を許容しない。引渡し準備完了とPhase完了/出荷を別状態にし、全ゲート前の完了/出荷禁止を保持する。

## Multi-Source Coverage Audit

COVEREDは実装taskへの割当済みの意味。実装/検証済みを意味しない。

| SOURCE | ID | Feature / Requirement | Plan / Task | Status |
|---|---|---|---|---|
| GOAL | SC1 | 出力外正本・初回/再build・SHA・利用手順 | 06-01 / 06-02 / 06-04 / 06-05 | COVERED |
| GOAL | SC2 | 起動/再build/更新で設定とprompt保護 | 06-01 / 06-04 / 06-05 | COVERED |
| GOAL | SC3 | 起動/初期化/config/build障害と全品質 | 06-01 / 06-03 / 06-06 | COVERED |
| GOAL | SC4 | Python各入口/実配布EXE受入と未実施区別 | 06-03 / 06-04 / 06-05 / 06-06 | COVERED |
| GOAL | SC5 | v1.10.0と保証範囲の説明 | 06-02 / 06-05 / 06-06 | COVERED |
| REQ | V110-DIST-01 | 出力外の2正本・source管理 | 06-01 / 06-02 / 06-04 | COVERED |
| REQ | V110-DIST-02 | 単一build/同梱/機械照合/使い方 | 06-01 / 06-02 / 06-04 / 06-05 | COVERED |
| REQ | V110-DIST-03 | 設定/実prompt非破壊 | 06-01 / 06-02 / 06-03 / 06-04 / 06-05 | COVERED |
| REQ | V110-QA-01 | 障害自動化/全品質 | 06-01 / 06-03 / 06-04 / 06-06 | COVERED |
| REQ | V110-QA-02 | 実Windows/Python/EXE受入 | 06-03 / 06-04 / 06-05 / 06-06 | COVERED |
| REQ | V110-QA-03 | 版/変更/保証整合 | 06-02 / 06-04 / 06-05 / 06-06 | COVERED |
| RESEARCH | A1/P1 | copyfile・旧原本保持・AST版読取 | 06-01-01 / 06-02-01 | COVERED |
| RESEARCH | A1/P2 | preflight、reparse/未知/調査不能、所有lock | 06-01-01/02 | COVERED |
| RESEARCH | A1/P2 | private staging、公開前再確認、history/復帰 | 06-01-01/02 | COVERED |
| RESEARCH | A1/P3 | EXE隣と_internal区別、既存prompt連動 | 06-01-01 / 06-02-02 / 06-05-02 | COVERED |
| RESEARCH | A2/P4 | report全項目、秘密非収集、成功/UAT分離 | 06-01-01/02 / 06-04-01 | COVERED |
| RESEARCH | A3/tests | build/copy/hash/report/publish/同時runの故障境界 | 06-01-02 | COVERED |
| RESEARCH | A3/EXE | 未改変EXE完全copy、PID/時刻、実Ollama設定経由fake OCR | 06-03-01/02 / 06-04-02 | COVERED |
| RESEARCH | A3/config | 隔離EXEだけのファイルlock障害 | 06-03-02 / 06-04-02 / 06-05-02 | COVERED |
| RESEARCH | A3/W | W24+WR01、入口matrixと証拠種別 | 06-05-01/02 / 06-06-01 | COVERED |
| RESEARCH | A3/W11 | 別session未準備をnot-run・出荷停止 | 06-06-01/02 | COVERED |
| RESEARCH | A3/WR01 | 15609ms/15140ms保持と15.5秒再評価 | 06-06-01 | COVERED |
| RESEARCH | A4/runtime | 新OS登録/自動移行なし・版付き出力の追跡方針 | 06-02-02 | COVERED |
| RESEARCH | A5/security | ASVS1/high、境界・秘密・偽pass・所有PID | 全6計画のT-06-01〜14 | COVERED |
| RESEARCH | stack/audit | 既存PyInstaller/標準lib、SUS保持、新規install時のみgate | 全6計画のT-06-SC | COVERED |
| RESEARCH | history | Phase4 stale再検証/Phase5 H16再利用 | 06-05-01/02 / 06-06-02 | COVERED |
| RESEARCH | regression | 未解除原因の再発停止・初回診断保持・fresh basetemp | 全6計画 execution_rules / 06-06-02 | COVERED |
| RESEARCH | calibration | 13 analogは部分一致、安全pipeline/EXEadapter新設 | 06-01 / 06-03 | COVERED |
| CONTEXT | carryover-01 | 全必須人手passまで完了/出荷停止、元記録保持 | 06-05 / 06-06 | COVERED |
| CONTEXT | carryover-02 | Phase4禁止3/edge5、Phase5edge4の未解除別集合 | 06-06-02 | COVERED |
| CONTEXT | quality | Ruff/format/AST/全件・hash再利用・Nyquist | 全6計画 / 06-06-02 | COVERED |
| CONTEXT | D-01 | 日本語ガイドとREADME | 06-01-01 / 06-02-01/02 | COVERED |
| CONTEXT | D-02 | 用途別コピー/名前変更/原本維持 | 06-01-01 / 06-02-02 / 06-05-02 | COVERED |
| CONTEXT | D-03 | 最短ガイド・編集・衝突注意・詳細リンク | 06-01-01 / 06-02-02 | COVERED |
| CONTEXT | D-04 | Markdown形式 | 06-01-01 / 06-02-02 | COVERED |
| CONTEXT | D-05 | 別folder更新と旧版保持 | 06-02-02 / 06-04-02 | COVERED |
| CONTEXT | D-06 | 保護ファイル検出はbuildより前 | 06-01-01/02 / 06-04-02 | COVERED |
| CONTEXT | D-07 | コピー衝突時停止・両方保持 | 06-02-02 / 06-04-02 | COVERED |
| CONTEXT | D-08 | 版番号付きfolder | 06-01-01 / 06-02-01 / 06-04-01 | COVERED |
| CONTEXT | D-09 | 単一CLI初回/再build | 06-01-01/02 / 06-04-01 | COVERED |
| CONTEXT | D-10 | 短い成否と詳細report | 06-01-01/02 / 06-04-01 | COVERED |
| CONTEXT | D-11 | 未完成物と理由/log保持 | 06-01-01/02 | COVERED |
| CONTEXT | D-12 | 成功後の案内・EXE非自動起動 | 06-01-01 / 06-04-01 | COVERED |
| CONTEXT | D-13 | 小分け・回答後に次 | 06-05-01/02 / 06-06-01 | COVERED |
| CONTEXT | D-14 | Python→EXE、両入口・混在 | 06-03-01/02 / 06-05-01/02 / 06-06-01 | COVERED |
| CONTEXT | D-15 | ID＋観察回答と必須環境 | 06-05-01/02 / 06-06-01 | COVERED |
| CONTEXT | D-16 | 視覚ケース/異常中心の画像＋ログ | 06-05-01/02 / 06-06-01 | COVERED |

Deferred Ideas（自動更新/自動移行、PDF引数転送、最近使ったファイル、復旧、外部prompt保存失敗通知、OCR共通化、実API UAT等）は実装対象に加えない。fake HTTPは既存設定の試験支援である。

## Flagged assumptions — spec-less edge fallback

SPECなし、default-ON fallbackを適用。親が要件原文6件でedge-probe.cjsを実行した結果をそのまま保持する。unclassifiedの自動resolved/backstop/dismissは禁止。

| Requirement | category | status | verification | resolution | reason | probe |
|---|---|---|---|---|---|---|
| V110-DIST-01 | unclassified | unresolved | null | null | null | unclassified — review manually |
| V110-DIST-02 | unclassified | unresolved | null | null | null | unclassified — review manually |
| V110-DIST-03 | unclassified | unresolved | null | null | null | unclassified — review manually |
| V110-QA-01 | unclassified | unresolved | null | null | null | unclassified — review manually |
| V110-QA-02 | unclassified | unresolved | null | null | null | unclassified — review manually |
| V110-QA-03 | unclassified | unresolved | null | null | null | unclassified — review manually |

coverage: applicable=6 / resolved=0 / unresolved=6 / unclassified=6。全6件をflagged assumptionsとして保持。計画に詳細acceptanceがあることは分類不能な元probeを解決した証拠ではない。

## Prohibition recall → precision → serializer

各要件を「作者が望まない何に変わるか」でrecallし、通常のcorrectness/hygieneをdrop、個別の安全性/透明性をkeepした。canonなpath traversal/injection/秘密漏洩はgsd-secure-phaseへ回し、このprobeの新項目にしない。

| Req | raw recall（各10候補） | keep |
|---|---|---|
| DIST-01 | 移動、改稿、出力同居、文字化け、改行変更、copy失敗、欠落、hash誤り、追跡漏れ、link逸脱 | 原本の移動/改稿/出力巻込み禁止 |
| DIST-02 | buildを出荷扱い、fakeを実build扱い、同梱欠落、hash誤り、版誤り、CLI不統一、report欠落、copy失敗、ログ欠落、リンク切れ | build成功を実機/出荷承認と表示禁止 |
| DIST-03 | 無断上書き、無断削除、自動移行、旧版破棄、衝突黙殺、lock不備、race、snapshot不足、copy失敗、path逸脱 | 利用者ファイル無断消去/上書き禁止 |
| QA-01 | 成功で原因解除、期限延長、除外、skip、fixture不備、assert誤り、collect漏れ、report欠落、ログ欠落、test並列干渉 | 成功全件を根本解決/依存解除へ転用禁止 |
| QA-02 | fakeを実機pass、not-runをpass、試験EXE代用、画像だけで時間判定、入力代替、case漏れ、時刻不足、hash不足、PID誤り、snapshot不足 | fake/試験EXE/未実施を本番人手passへ投影禁止 |
| QA-03 | 旧版も保証、OS制約回避保証、未出荷を公開済扱い、版不一致、badge誤り、履歴欠落、説明リンク切れ、AST失敗、folder誤り、report誤り | 旧版/OS前面化を過大保証禁止 |

keep6件はinstalled probe-core.cjsのprojectProhibitionsでprojectionし、dispositionForProhibitionが全6件unverified/flagged=trueを返すことを確認した。最初のshell quoting/文字encoding試行は不採用、Unicode escape入力で原文一致を確認した最終結果のみ使用。check_* descriptorは生成していない。

| Req | must_haves.prohibitions配置 | status / disposition |
|---|---|---|
| V110-DIST-01 | 06-01 | unresolved / flagged-unverified |
| V110-DIST-02 | 06-01 | unresolved / flagged-unverified |
| V110-DIST-03 | 06-01 | unresolved / flagged-unverified |
| V110-QA-01 | 06-06 | unresolved / flagged-unverified |
| V110-QA-02 | 06-03 | unresolved / flagged-unverified |
| V110-QA-03 | 06-02 | unresolved / flagged-unverified |

no-silent-drop: edge surfaced6 = authored resolved0 + flagged assumptions6。prohibitions surfaced6 = authored6 + unrepresented0。計画taskの負例試験は将来実行するもので、probeの検証済みdescriptorへ捏造しない。

## 検証コマンドの根拠

init.plan-phase 06 prior_verify_commandsから.venv/Scripts/python.exe -m pytest -q、Ruff/Python対象format/ASTを継承。fullのbasetempだけ毎回GUIDで未使用のrepo外pathへ更新する。新test/CLIは06-01-01、06-02-01、06-03-01/02、06-05-01が先に作成し、後続はdepends_onで保証。buildと全件は60秒超の長いゲート、局所は60秒以内目標。未実行を合格にしない。

テキストcount/negative-grepを製品のverifyに使わず、実ファイル不変・subprocess起動有無・失敗物・意味のある契約試験で判定する。新testは現在不存在がbaselineであり、実装前成功とはしない。

## 現在の検証状態

2026-10-24に全6PLANのfrontmatter.validate --schema planとverify.plan-structureがvalid=true（errors0/warnings0、各2task）、末尾</output>、継続sentinelなしを確認した。静的監査で6plan/12task/automated15件すべて直後fails_when、action内D-01〜D-16の16件、requirements6件、各task最大5files、脅威T-06-01〜14の一意性を確認した。git diff --checkはexit0。生成reportの自己参照hashを避ける外部run reportとの照合も06-01へ明示した。

製品test/build/manualはnot-run。計画検証は製品合格ではない。commitは親担当の品質ゲート後であり、本plannerは実施していない。

## Checker revision 1/3

- research_resolution: RESEARCHのOpen Questions 5件を、計画上の処置が確定したRESOLVEDとして担当task/実行停止条件へ対応付けた。W11未準備・WR-01未合格・fixture未実証・回帰原因未解除は変更しない。RESEARCHはこの節以外を編集しない。
- dependency_correctness: 06-03のaudit APIへ--for-handoffを追加し、06-06-02の引渡し前検証と親4ゲート後の最終監査について担当・コマンド・成功条件を分離した。品質証拠は引渡し監査より前に生成する。親結果は引渡し前検証の前提にしない。全ゲート前のPhase完了/出荷は禁止のまま。
- pattern_compliance: 06-01のtest_release_build.pyへtests/conftest.pyの実ディスクfixture、06-02のtest_release_contract.pyへtests/test_gsd_dod.pyのread-only文書契約をread_firstで明示し、未完了をvalidated/passへ変えない採用要点を記した。
- 既存の6plans/6waves/12tasks、D-01〜16、6要件、W24枝番+WR-01/X01〜X06の割当を維持する。親の初回verify-command probeは15/15 failure direction確認済み、Python path probeはnot_applicableで未検査という区別を維持し、このrevisionでは静的構造/整合のみ検証する。
- revision後の実測: 全6PLANにfrontmatter.validate --schema plan / verify.plan-structureを実行し、すべてvalid=true、errors/warnings=0、各2tasks。静的整合検査はerrors=[]、wave1〜6、automated15件の直後にfails_when、全task最大5files、action中D-01〜16、6要件、全W24枝番+WR-01/X01〜X06、末尾</output>とsentinelなしを確認した。RESEARCHのOpen Questionsを除く本文SHA-256は修正前後で一致（e08596ec2e0edd1bd9b6185e617e102eb69bbfa3697dd0d29ad0e3e72275718c）、06-04/05 PLANも全体SHA一致。phase06対象git diff --checkはexit0。製品build/pytest/実機/commitは未実施で、親checkerの再評価は別途必要。
