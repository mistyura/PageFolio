# 案B限定再計画の差分確認 — 2026-10-28

## 変更と検証の範囲

承認原文とD-17〜D-19は06-W11-SCOPE-APPROVAL.mdに固定。既存06-01〜04と旧研究/レビュー/証拠は変更せず、07/08の4taskを05/06より前へ追加した。PROJECT/REQUIREMENTS/ROADMAP、CONTEXT/CARRYOVER/VALIDATION、05/06の現行契約を整合した。UAT/JSON台帳・テスト・製品・配布文書・STATEはこの計画作業で編集していない。

06-05/06-06/06-07/06-08について `frontmatter.validate --schema plan` と `verify.plan-structure` がvalid=true、errors=[]、warnings=[]、各2task。各ファイル末尾は `</output>`。新07/08の見積補正はfactor=1/sample_count=0/confidence=low。pytest・GUI・build・commitは未実行。独立checkerは親担当。

## 依存と実行順

| Plan / Wave | needs | creates | 人手 |
|---|---|---|---|
| 06-07 / 5 | 既存監査と承認正本 | 固定scope、全mode回帰、110行保持の台帳 | なし |
| 06-08 / 6 | 07の監査/台帳契約 | 配布文書、品質/freeze、新世代2build/保護/接続 | 接続操作・確認 |
| 06-05 / 7 | 08の実成果物/準備 | G1〜G6の必須実機結果 | 小分け |
| 06-06 / 8 | 05の必須結果 | G7〜G13、108必須/対象外2、品質/親ゲート引渡し | 小分け |

07/08はTestCaseCoverageとUAT/台帳が重複し、08は07の監査を消費する。GSDの同wave共有変更ファイル禁止とdepends_on規則により別waveを維持した。全件の同一性再利用は可能だが、実際に試験が読む入力の変更後は再評価が必要。wave末品質を免除しない。

## Multi-Source Coverage Audit

COVEREDはtaskへの割当であり実装/実測passではない。旧01〜04の成果を再作成せず、当初監査は06-PLANNING-CHECKS.mdを履歴として参照する。

| SOURCE | ID | 対象 | Plan / Task | Status |
|---|---|---|---|---|
| GOAL | SC1 | 正本/実2build/SHA/利用手順 | 01/02/04保持、08-01/05-02 | COVERED |
| GOAL | SC2 | 設定/prompt保護 | 01/04保持、08-02/05-02 | COVERED |
| GOAL | SC3 | 故障自動化と全品質 | 01/03保持、07/08/06-02 | COVERED |
| GOAL | SC4 | 各入口/実EXE、108必須/2未確認 | 07/08/05/06 | COVERED |
| GOAL | SC5 | 版/保証説明 | 02保持、08-01/05-02/06-02 | COVERED |
| REQ | V110-DIST-01 | 正本2個保持 | 01/02保持、08-01 | COVERED |
| REQ | V110-DIST-02 | 同手順2build/同梱/使用 | 01/02保持、08/05 | COVERED |
| REQ | V110-DIST-03 | 原本非破壊 | 01/03保持、08-02/05 | COVERED |
| REQ | V110-QA-01 | 回帰/全品質 | 07/08/06-02 | COVERED |
| REQ | V110-QA-02 | 台帳/実機/未実施区別 | 07/08/05/06 | COVERED |
| REQ | V110-QA-03 | APP_VERSION/保証文書 | 08-01/05-02/06-02 | COVERED |
| RESEARCH | A1/P1/P2 | bytesコピー・preflight・私有出力/復帰 | 01保持、08の既存build契約 | COVERED |
| RESEARCH | A1/P3 | EXE隣/外部prompt・配布リンク | 01/02保持、08/05 | COVERED |
| RESEARCH | A2/P4 | AST版/詳細report/秘密非収集/成功分離 | 01/02保持、08/06 | COVERED |
| RESEARCH | A3 | 実EXE adapter/外部fault/fake OCR | 03保持、08-02/05/06 | COVERED |
| RESEARCH | A4/Runtime State | 自動移行なし/旧dist保持/OS登録/秘密 | 02保持、08/05 | COVERED |
| RESEARCH | A5/Security | ASVS1/high・STRIDE・読取監査 | 各PLAN、07 T15/16、08 T17/18、親4ゲート | COVERED |
| RESEARCH | W/WR-01/既知ゲート | 旧W11停止の限定置換、その他継続 | 07の固定scope、05/06の全観測 | COVERED |
| CONTEXT | D-01 | ガイド/README | 01/02保持、08-01 | COVERED |
| CONTEXT | D-02 | OCR/summary別copy | 02保持、08-01/05-02 | COVERED |
| CONTEXT | D-03 | 短い手順/参照 | 02保持、08-01 | COVERED |
| CONTEXT | D-04 | Markdownガイド | 01/02保持、08-01 | COVERED |
| CONTEXT | D-05 | 別folder更新/旧版保持 | 02保持、08-02/05-02 | COVERED |
| CONTEXT | D-06 | builder前保護停止 | 01保持、08-01/02 | COVERED |
| CONTEXT | D-07 | 衝突時両方保持 | 02保持、08-02/05-02 | COVERED |
| CONTEXT | D-08 | 版付きfolder | 01/02保持、08-01 | COVERED |
| CONTEXT | D-09 | 単一build入口 | 01保持、08-01 | COVERED |
| CONTEXT | D-10 | 成否/出力先/report | 01保持、08-01 | COVERED |
| CONTEXT | D-11 | 失敗物/ログ保持 | 01保持、08-01 | COVERED |
| CONTEXT | D-12 | EXE自動起動なし | 01保持、08-01 | COVERED |
| CONTEXT | D-13 | 小分け人手 | 08-02/05/06 | COVERED |
| CONTEXT | D-14 | Python→EXE/各入口 | 08-02/05/06 | COVERED |
| CONTEXT | D-15 | ID/原文/環境 | 07/08-02/05/06 | COVERED |
| CONTEXT | D-16 | 必要な画面/実測 | 08-02/05/06 | COVERED |
| CONTEXT | D-17 | 単一session/正確なW11 2行 | 07/08-01/06-01 | COVERED |
| CONTEXT | D-18 | 31/110/108/2、全安全必須 | 07/05/06 | COVERED |
| CONTEXT | D-19 | 契約先行/新世代freeze/旧証拠保全 | 07→08→05→06 | COVERED |

新規技術/依存の採用はなく既存研究を再利用。承認された2行以外のdefer、runtimeで複数sessionを禁止する機能、保留中の別製品機能は計画に含めていない。

## 独立checkerへの確認点

2026-10-28 独立checker最終判定: **VERIFICATION PASSED、BLOCKER 0 / WARNING 0 / INFO 0**。初回の4指摘は各automatedコマンド直後にfails_whenを追加して解消。`06-W11-verify-failure-directions-revised.json` はstatus=ok、全23コマンドseverity=none、readError=null。要件6/6・決定19/19・対象4PLAN構造検査validの既存結果を再利用。計画合格は実機受入・Phase完了・出荷許可ではない。

- 06-03の旧audit_contractとの差分が07の固定scopeだけで、W11未承認時の厳密拒否を保持すること。
- 31case/110cardの正規集合を台帳自身から自己生成せず、必須108行の欠落/重複/任意免除を拒否すること。
- 05/06のscope_amendmentは旧v1.10.0/06-04世代参照と旧W11停止を明示的に置換し、他の観測条件は維持すること。
- 08は文書変更後の新世代実2build・保護・接続を必須化し、過去pass/hashの移植をしないこと。
- 品質/waveゲートと実入力変更の再評価を守り、計画合格・準備成功・人手pass・正式出荷判断を混同しないこと。
