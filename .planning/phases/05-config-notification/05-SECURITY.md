---
phase: "05"
slug: config-notification
status: verified
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: "2026-10-24"
---

## 2026-11-06 W05c v3 / CR-02後の脅威再照合（現行）

Nyquist後、計画時14脅威の緩和先と製品コードの同一性を確認した。読込失敗とmissingの区別、保護中保存0、排他的tmp→replace/所有tmpだけのcleanup、機密除外、通知所有を現行試験assert・新JUnitへ照合。2361件成功、170入力前後/現行一致、Phase05関連498件全成功。ASVS L1 / closed14 / open0を維持する。共有検証側の否認判断は厳密比較と28否認回帰で保護され、人手/実EXEの未受入は免除しない。`05-REVALIDATION-20261106.md` 参照。

## 2026-11-05 W05c計測後の脅威再照合（履歴）

Phase 04の新報告を確認したうえで、計画時14脅威の緩和実装を現行設定・通知コードと新JUnitへ再結合した。機密除外、原本保護、排他的tmp→replace、読取不能時の保存抑止、通知所有は不変。新W05c観測は試験process限定で、製品network/auth/schema境界を増やさない。14 closed / `threats_open: 0`（ASVS L1）を維持する。DEP-05/owner_missing、正式実機/EXE受入と出荷未承認は解消扱いにしない。`05-REVALIDATION-W05C-20261105.md`参照。

# Phase 05 — セキュリティ検証

## 2026-11-05 現行入力・脅威再照合

新しい2254件の単一native全件と現行118入力一致により、設定読込分類・原本保護・機密除外・排他的tmp→replace・通知所有の回帰を確認した。計画時14件はclosed、`threats_open: 0`、ASVS L1を維持。今回変化したrelease試験は指定範囲の未実施拒否と隔離copyの保護を強化し、新しい依存・ネットワーク・認証・schema境界を設けない。[05-REVALIDATION-20261105.md](05-REVALIDATION-20261105.md)参照。DEP-05/owner_missing等の原因解決とPhase 06出荷承認は主張しない。

## 2026-10-28 案B・配布文書契約変更後の限定再照合（現行）

Nyquist照合後、計画時14脅威の対策と新差分の境界を評価した。製品・依存・設定保護の試験はCR-03後の検証入力と不変（05-REVERIFY-SCOPE-20261028.json）。14 closed / threats_open0、ASVS L1を維持。追加依存導入なし、L1/計画時登録あり/open0の短絡条件により一般深掘り監査は再実施しない。

新全件2232件の生証拠と151入力一致を独立確認。案BはPhase06のW11の2キーだけの保証範囲変更で、設定原本保護・機密除外・FIFO・終了保留を弱めない。固定承認hash/110カード集合/108必須/2対象外とW11偽pass拒否は監査入口に接続されていることを読取確認した。Phase06全体のSecurity/本受入や出荷の代替判定はしない。旧未分類edge、DEP-05/owner_missing等の原因未解決を維持する。

## 2026-10-28 CR-03 修正後の独立再照合（現行）

Nyquist の現行入力照合後、計画時の STRIDE 14件と実装・試験を再評価した。14 closed / threats_open 0、ASVS L1 を維持する。settings.py の機密除外・例外型のみのログ・排他的 tmp/replace、app.py の unreadable 抑止・終了保留・通知所有、ネスト設定の一保存とセッションキー保護は不変。計画時登録あり・L1・open 0 の短絡条件により追加の一般深掘り監査は行わない。

CR-03 は別途コードレビューで差分を独立評価した。OCR off 時に旧 provider の能力だけで本文送信を許す経路は、ボタンと _on_summary の入口の二箇所で拒否され、本文構築・キー確認・worker 起動より前で return する。実ネット送信は行っていない。登録済み14脅威の範囲や実機出荷判定を拡張しない。

再利用した正本は `ocr-off-summary-evidence/native-20261028/` の2083 passed・exit 0。verifierの独立照合は147入力不一致0（`05-REVERIFY-20261028.json`）。依存導入・製品編集なし。以下の2071件等は過去時点として保持する。H01〜H14および禁止事項の意味評価2件は既存利用者pass、未分類edge/旧投影IDの同一性とPhase 06受入は別扱いである。

独立したgsd-security-auditorが計画済み14脅威を照合した。共有T-05-SCは1件として集計。全dispositionはmitigate、14 closed、blocking/non-blocking openは各0。新しい脅威の一般走査やリスク受容は行っていない。

## Trust Boundaries

| 境界 | 対策 |
|---|---|
| 設定JSONとAppメモリ | 読込分類・原本保護・排他的tmpと原子的置換 |
| 保存結果とUI寿命 | 共通保存owner・固定文言・FIFOと世代管理 |
| LLM/sessionキーと永続化 | 機密除外コピー・低層guard・単一保存owner |
| 試験/harnessと利用者ファイル | import前の解決先隔離・限定障害注入・原本hash照合 |
| 実測と完了判定 | 自動・利用者回答・未実施・証拠限界の区別 |

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|---|---|---|---|---|---|---|
| T-05-01 | Tampering | 読込/自動保存 | high | mitigate | app.py:153,753、TestLoadProtectionの書込0/原本保持 | closed |
| T-05-02 | Information Disclosure | 読込結果/通知/ログ | high | mitigate | settings.py:313,317、app.py:644、秘密sentinelのUI/log非流出assert | closed |
| T-05-03 | Denial of Service | 読込/初回Toast | medium | mitigate | settings.py:308,322,325、app.py:234,539、TestLoadTracer実App編集継続 | closed |
| T-05-04 | Tampering | 原子的保存 | high | mitigate | settings.py:377,389、test_settings_keyguard.py:16,63の5障害点と既存tmp保持 | closed |
| T-05-05 | Information Disclosure | 保存copy/ログ | high | mitigate | settings.py:356,363,384、機密除外・入力非破壊・例外sentinel試験 | closed |
| T-05-06 | Repudiation | 共通保存/Apply | medium | mitigate | app.py:668,677,681,875、TestSaveFlowのbool/偽成功抑止/保護解除 | closed |
| T-05-07 | Denial of Service | Toast/再構築 | medium | mitigate | app.py:530,565,590,637、toast.py:119,132,186、境界/100件FIFO/旧callback試験 | closed |
| T-05-08 | Tampering | 終了操作 | high | mitigate | app.py:654,753、TestExitSaveFailureとTestConfigAcceptanceの資源保持/次回省略/flag解除 | closed |
| T-05-09 | Tampering | ネストLLM設定 | high | mitigate | dialogs/settings.py:224、app.py:857、TestLlmSaveOriginsの単一保存/外側Cancel境界 | closed |
| T-05-10 | Repudiation | 全保存handler | medium | mitigate | 全10操作群の実handler試験、TestSaveOriginCoverageのAST棚卸し、低層callerはapp.py:676のみ | closed |
| T-05-11 | Information Disclosure | LLM/sessionキー | high | mitigate | dialogs/llm_config/dialog.py:489,671、settings.py:363、provider_ui/session非流出assert | closed |
| T-05-12 | Tampering | 障害注入harness | high | mitigate | tests/config_notice_support.py:57,67,97,114,124,139、TestScenarioIsolationの原本hash/初期化例外cleanup | closed |
| T-05-13 | Repudiation | EVIDENCE/VALIDATION | medium | mitigate | 05-04-task1-full/pytest.txt:32、status.json:12、05-EVIDENCE.jsonの環境失敗/人手結果/証拠限界 | closed |
| T-05-SC | Tampering | パッケージ導入 | high | mitigate | Phaseのrequirements/pyproject差分0、新規installなし、既存未commit依存差分を別途記録 | closed |

製品pathはpagefolio/配下、試験はtests/配下。実行証拠は同ディレクトリの05-EVIDENCE.json、各SUMMARY、05-UAT.mdを参照。

## Accepted Risks Log

受容したリスクなし。

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|---|---|---|---|---|
| 2026-10-24 | 14 | 14 | 0 | gsd-security-auditor、ASVS L1 |

## 限界と未解除事項

手動harness全起動の終了・原本hash照合完了は終了ログから確認できない。自動隔離試験のhash照合と区別する。DEP-05・owner_missing・通知前景不一致・Tcl解放警告・descriptor不明の禁止2件・未分類edge4件は未解除。今回の登録済み対策の検証は出荷承認ではなく、再発時停止とPhase 6の実EXE受入を維持する。

## Sign-Off

- [x] 全脅威のdispositionと対策根拠を確認
- [x] accepted riskなし
- [x] threats_open: 0
- [x] status: verified

**Approval:** verified 2026-10-24

## 再照合 2026-10-28

Phase 05 の再検証ゲートで、4 PLAN の計画時 STRIDE 登録（T-05-01〜13 と共有 T-05-SC）と現行実装・試験を ASVS L1 の深さで再照合した。14 closed / open 0 を維持する。計画時登録あり・L1・open 0 のため、secure-phase の短絡条件に従い追加の深掘り監査は行わない。

読込分類と例外本文を出さないログ（settings.py:308）、機密除外コピー・排他的 tmp・close 後の replace・所有 tmp だけの削除（settings.py:352）、読込不能時の書込抑止と保存結果の通知（app.py:683）、保存失敗時の終了保留（app.py:668）、通知の event/generation と可視寿命（app.py:523〜、toast.py:116〜）を確認した。ネスト設定の単一保存と session 辞書保持は dialogs/settings.py:224 と TestLlmSaveOrigins、保存入口の棚卸しは TestSaveOriginCoverage、隔離と原本 hash は tests/config_notice_support.py:57/165 と TestScenarioIsolation が引き続き対応する。

05-VALIDATION.md の今回の入力・環境照合により、既存単一全件 2071 passed / 2 warnings / exit 0 を再利用する。今回の Phase 05 再検証では依存定義変更・パッケージ導入・製品編集を行っていない。T-05-SC の旧記述は当時の Phase 実装についての記録であり、前回 verification 以降の requirements.txt の変更が存在しないという意味ではない。今回の依存定義は再利用した全件証拠と一致している。

人手受入と未実施事項を分離し、過去の失敗原本と未解除事項を保持する。Phase 06 の W05b 自動復帰未実証と出荷停止は、本監査では解除しない。

## Security Audit 2026-10-28

| Metric | Count |
|---|---|
| Threats found | 14 |
| Closed | 14 |
| Open | 0 |

## 2026-11-06 constructor同期修正後の再照合

製品/設定/通知/機密鍵のコードと依存は前回から不変。constructor試験同期と履歴の記載だけの差分であり、既存14 closed/open0を再利用。全件2401/Phase05関連498件成功。未解除事項・出荷停止は維持する。


## 2026-11-07 G4採取基盤変更後の差分照合

`05-REVALIDATION-G4-20261107.md` と `../04-startup-control/04-QUALITY-G4-20261107.json` を参照。単一全件2481 passed/2 warnings、174入力と追加12入力不変、Ruff/format/AST成功。変更は採取試験基盤と証拠/文書のみで、製品の実装・表示・版番号・固定EXEは不変。G4レビュー7指摘を解消。既存の静的評価と未解除リスクを維持し、正式人手受入・UI capture・出荷承認へ転用しない。独立verificationは後続で現行fingerprintを照合する。
