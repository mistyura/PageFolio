# Phase 05 現行入力の再検証（2026-11-05）

Phase 06 の受入再開に必要な親検証の鮮度を回復するため、完了済みの 05-01〜04（4 PLAN / 4 SUMMARY）を再実装せず、現行コード・実走証拠・4要件と23 truthを独立に再照合した。製品、試験、Phase 04/06、共有 STATE/ROADMAP は編集していない。

## 入力と自動実走

- 正本は `.planning/phases/04-startup-control/04-reverify-20261105-full/` の `run.json`、`inputs-before.json`、`inputs-after.json`、`junit.xml`、`stdout.txt`、`stderr.txt`。2026-11-05T00:30:28.574Z〜00:40:01.299Z、単一 native 全件、exit 0、**2254 passed / 2 warnings / 571.44秒**。JUnit は2254 testcase、failure/error/skip 各0。実行前後118入力の変化0で、今回再照合時も118/118のSHA-256が現行と一致。
- この118入力は `pagefolio/settings.py`、`app.py`、`toast.py`、`ocr_dialog.py`、`tests/config_notice_support.py`、`test_config_notification.py`、`test_settings_keyguard.py`、`test_toast.py`、`test_ocr_dialog_provider_refresh.py`、`test_release_contract.py`、`test_release_uat_support.py` などPhase 05実装・関連試験を含む。JUnitでconfig_notification 143、settings_keyguard 26、toast 38、provider_refresh 18、release_contract 30、release_uat_support 243がpass。
- Phase 04回帰対象も同一JUnitでstartup_control 52、focus 32、notice 61、windows 88、foreground_audit 24、wake 23がpass。公式 `verification.status` も Phase 04 は `passed`。この単一全件の入力・環境を使い、pytestを重複起動していない。
- 旧 `.planning/phases/06-release-validation/06-08-evidence/native-docs-20261028/before.json` の151入力は現行から9件変化しており、旧2232件を現行全件に転用しない。README、`distribution/はじめに.md`、`constants.py`、`ocr_dialog.py`、`test_ocr.py`、`test_ocr_dialog_provider_refresh.py` は当時のSHA-256と一致。変化した `tests/release_uat_support.py`、`test_release_contract.py`、`test_release_uat_support.py`、`test_startup_windows.py` は新118入力に含まれ、現行の2254件に含まれる。残る変化はPhase 06のdriver・台帳・UATであり、Phase 05製品の変更ではない。

## 必須ゲートと独立判定

| ゲート | 現行判定 |
|---|---|
| Nyquist | 4/4要件 COVERED、9/9実装タスクの自動検証、追加gap0。設定I/Oと原本保護の実装・assert・現行JUnitを再結合。 |
| Security | 計画時14脅威のmitigateと実装を再照合し、14 closed / threats_open 0を維持。設定原本の排他的tmp→replace、機密除外、保存失敗時の編集継続に変更なし。新規依存・ネットワーク・認証・schema境界なし。 |
| UI | 既存の静的22/24を維持。設定通知の文言、寿命、表示配線は不変。OCR offの表示と入口拒否の回帰18件がpass。新規画面撮影・実EXE/DPI/UAC操作は行わず、実画面合格へ拡張しない。 |
| Code review / disposition | 変更されたrelease UAT試験は指定範囲だけのrequire-passと未実施拒否を検証し、原本保護を弱めない。新規critical/warning/info各0。CR-01/02/03とWR-01はfixed、open0の既存判定を維持。 |
| Regression | Phase 04の新規fresh passedと現行2254件中の対象試験成功を再利用。追加の全件実行なし。 |
| Goal verification | 設定読込分類、保存失敗通知、原本保護、FIFO/再構築/終了後の編集継続の4成功条件とPLANの19 truthを現行実装・JUnit・既存H01〜H14に再照合し、23/23。禁止事項の意味評価2件は既存の利用者passを継承。 |

`pagefolio/ocr_dialog.py` とOCR回帰は旧入力SHA-256と一致し、CR-03のoff時サマリ拒否を維持。UI評価のV-01/S-01、`DEP-05-REGRESSION`、`owner_missing`、通知前景不一致、descriptor不明2件、未分類edge4件の原因未確定は解除しない。Phase 06の台帳は31ケース/110行、現行28 pass/82 not-run（必須80 not-run、承認済みW11対象外2 not-run）で、実機受入と出荷判定は未完了、`release_approved: false` を維持する。

今回の報告・ゲート追補と新実走証拠を公式 `verification.fingerprint` のcovered入力に含める。旧報告内の2071/2083/2232件、CR-03未修正、全110行未実施等の記述は各時点の履歴であり、本節の現行判定と混同しない。
