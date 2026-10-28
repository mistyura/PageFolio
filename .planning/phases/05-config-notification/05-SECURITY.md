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

# Phase 05 — セキュリティ検証

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
