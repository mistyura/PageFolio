---
phase: "05"
slug: "config-notification"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-22"
---

# Phase 5 — Validation Strategy

設定読込・保存失敗の通知と原本保護の検証契約。05-01〜04の自動実測と2026-10-24 JSTの利用者によるH01〜H12の12 passを下記へ同期した。独立Nyquist監査で4/4要件COVERED・9/9タスク自動検証・具体的な試験ギャップ0、現行入力103件のSHA256一致を確認した。実測正本は[05-EVIDENCE.json](05-EVIDENCE.json)、人手は[05-UAT.md](05-UAT.md)。外部依存と内容不明のプローブの未解除は維持し、Phase正式完了は後続の独立検証で判定する。

## Test Infrastructure

| 項目 | 内容 |
|---|---|
| Framework | pytest 9.1.1、プロジェクト `.venv` |
| Config file | `pyproject.toml`（編集禁止） |
| Quick run command | `.venv/Scripts/python.exe -m pytest -q tests/test_settings_keyguard.py` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` |
| Estimated runtime | 局所60秒以内を目標、全件は実行後に実測を記録。時間超過を理由に除外しない |

## Sampling Rate

- 各実装タスク後は対応する局所テストを実行する。新設テストの作成をその検証コマンドに先行させる。
- 各コミット前・wave 完了時・`$gsd-verify-work` 前に単一プロセスの全件 pytest が失敗0・ERROR0・クラッシュなしで完走すること。
- Python 編集時は `.venv/Scripts/ruff.exe check .`、`.venv/Scripts/ruff.exe format . --config "include = ['*.py', '*.pyi', '*.ipynb']"`、整形後の同じlint、`pagefolio.py` の AST 構文確認も必須。
- 同じコード・入力・環境で成功済みの検証は再利用し、不要な再実行はしない。
- TclError を観測したら最初の結果を残し、CLAUDE.md:135-150 に従って該当ファイル単体と全件で切り分ける。skip・部分成功を全件合格と扱わない。

## 実行前の外部依存 — DEP-05-REGRESSION

**状態: 未充足・原因未確定。2026-10-23利用者判断により再発時停止を条件に実行承認済み。** レビュー時の **1 failed / 1634 passed / 0 errors / 1 warning / 354.41秒 / exit 1** は履歴として保持。診断commit `9384268`の最新単一全件は **1637 passed / failed 0 / ERROR 0 / 1 warning / 263.66秒 / exit 0**。テスト・requirements・ログのhash一致を確認したが、元のnormal-entry-scriptの`communicate(timeout=12)`期限超過は再現せず、原因修復・依存解除ではない。採用済み診断版でPhase 5へ進み、単一全件ゲートで同種失敗が再発したら実装・後続実行・コミットを停止する。実command・対象hash・途中の失敗・警告と利用者判断はdebug記録を参照。

修復commit `8689c27` 適用時の1635 passed / failed 0 / ERROR 0 / skipped 0 / 1 warning / 239.82秒 / exit 0は歴史証拠として維持するが、現在の実装GOに使用しない。詳細は [debug記録](../../debug/dep-05-regression.md)。旧6 failed / 1623 passedも05-PLANNING-CHECKS.mdに保持する。

- 現在の対象は上記normal-entry-scriptの子process終了期限超過。過去6失敗と同じ原因と推定せず、独立した `$gsd-debug` で原因を調査し必要な修復を行う。本Phaseの設定通知実装に修復を混ぜない。
- **Wave 1の製品編集・05-01-01実行前に必須**: 2026-10-23の利用者判断、診断commit `9384268`の適用、診断版の全件1637 passed / exit 0のcommand・対象hash・環境をdebug記録と照合する。これは未充足の依存に対する条件付き実行許可であり、解除証拠ではない。同一コード・入力・環境の成功済み検証は再利用し、製品変更後は現在コードで単一全件pytestを失敗0・ERROR0・クラッシュなし・exit 0で完走する。テスト削除・skip・フィルタ除外で条件を満たさない。
- 解除証拠には独立作業の参照、修復commit、検証対象commit/差分、Windows・Python/Tk・sandbox境界・basetempを含む環境、実行command、collected/passed/failed/ERROR件数、終了値、クラッシュ有無を残す。未記録・不一致なら解除不可。初期失敗と再試行結果は履歴として保持する。
- 全件commandは上表を使用する。既存tempの権限競合時は05-PLANNING-CHECKS.mdと同様に未使用の専用basetempを明示し、変更した実commandを証拠へ残す。basetemp変更はテスト除外ではない。
- この監視条件を05-01〜04の全タスク・各コミット前・wave末・最終ゲートへ引き継ぐ。依存は未充足のまま保持し、同種失敗が再発したらタスク/後続実行/コミット/Phase完了を停止する。最初の失敗出力・専用basetempのresult.json/traceback.log・poll/reader/process診断を保存して `$gsd-debug continue dep-05-regression` で原因を切り分ける。独立修復と現在コードの単一全件再検証を証拠化してから再開し、単なる再試行成功で停止を解除しない。

| 解除に必要な証拠 | 現在の記録 |
|---|---|
| 独立修復作業・適用済みcommit | `.planning/debug/dep-05-regression.md` / `8689c2720e38fc2397407e38317687d1952b22f6` |
| 診断採用後の単一全件command・環境・件数・exit | 9384268、1637 passed/1 warning/263.66秒/exit 0。対象hash一致。原因修復・再充足証拠とはしない |
| DEP-05-REGRESSION解除 | 未充足。原因未確定。条件付き承認下で05-01〜04の実装/受入を実施。最新全件1789 passed/1 warning/278.95秒/exit 0、利用者H01〜H12は12 pass。同種3症状の原因修復ではない。独立検証/Nyquistは未実施 |

## Per-Task Verification Map

各テストは該当タスクで先に作成・拡張してから実行した。下表のcommandは対象を示す計画値で、実行時の追加フラグ・専用basetemp・件数は下記実測表と05-EVIDENCEに記録する。Task/Wave/Threatの被覆は自動試験と利用者の明示回答を区別する。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| 05-01-01 | 05-01 | 1 | V110-CFG-01/03/04 | T-05-01/02/03 | 破損ファイルから実App/実Toast/PDF編集まで到達、原本保護 | E2E tracer | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestLoadTracer` | 存在・実走済 | 自動pass（実測表参照） |
| 05-01-02 | 05-01 | 1 | V110-CFG-01/03/04 | T-05-01/02/03 | 不存在/破損/読取不能の区別、読込通知一回、終了Yes/Noで書込0 | unit + integration | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestLoadBoundaries tests/test_config_notification.py::TestLoadProtection tests/test_settings_keyguard.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-02-01 | 05-02 | 2 | V110-CFG-02/03/04 | T-05-04/05/06/08 | 原子的保存、機密除外、明示成功だけ保護解除、終了失敗通知 | unit + integration | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestSaveFlow tests/test_config_notification.py::TestExitSaveFailure tests/test_settings_keyguard.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-02-02 | 05-02 | 2 | V110-CFG-02/04 | T-05-06/07 | 各失敗FIFO保持、期限/閉じる/競合/再構築/言語変更、PDF/印刷retry維持 | Tk + lifecycle | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestNotificationLifecycle tests/test_toast.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-03-01 | 05-03 | 3 | V110-CFG-02/03/04 | T-05-09/10/11 | plugin no-op保存0、明示同値Apply再試行、メモリ保持 | integration | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestAppSaveOrigins` | 存在・実走済 | 自動pass（実測表参照） |
| 05-03-02 | 05-03 | 3 | V110-CFG-02/03/04 | T-05-09/10/11 | LLM一保存・外側Cancel境界、既存OCR/ownerなしstub互換 | integration | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestLlmSaveOrigins tests/test_provider_ui.py tests/test_ocr.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-03-03 | 05-03 | 3 | V110-CFG-02/03/04 | T-05-10/11 | 全ツール保存通知、既存pagination回帰、AST caller棚卸し | integration + AST inventory | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestToolSaveOrigins tests/test_config_notification.py::TestSaveOriginCoverage tests/test_pagination.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-04-01 | 05-04 | 4 | V110-CFG-01/02/03/04 | T-05-12/13 | 複合操作でもPDF編集/原本維持、障害注入を私有環境に限定 | E2E + isolation | `.venv/Scripts/python.exe -m pytest -q tests/test_config_notification.py::TestConfigAcceptance tests/test_config_notification.py::TestScenarioIsolation tests/test_toast.py` | 存在・実走済 | 自動pass（実測表参照） |
| 05-04-02 | 05-04 | 4 | V110-CFG-01/02/03/04 | T-05-13 | 実結果だけを証拠化し全件失敗0/ERROR0/クラッシュなし | full regression + quality | `.venv/Scripts/python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"`（lint/format/ASTもPLAN記載どおり必須） | 存在・実走済 | 自動pass / 人手12 pass |

T-05-SC は各PLAN共通の導入ゲートであり、本計画に新規パッケージ導入はない。ASVS1 の high/critical 未緩和は完了をブロックする。

## Wave 0 Requirements

## 実行結果との対応（2026-10-24）

| Task / Wave | Threat | 実測結果・根拠 | 状態 |
|---|---|---|---|
| 05-01-01 / 1 | T-05-01/02/03 | 実App tracer+Toast35 passed、全件1639 passed、実focus JUnit2 passed。05-01-SUMMARY。人手H01/H02/H03を別実施 | 自動pass / 人手pass |
| 05-01-02 / 1 | T-05-01/02/03 | 境界40 passed、全件1660 passed。05-01-SUMMARY | 自動pass |
| 05-02-01 / 2 | T-05-04/05/08 | 承認時入力hash一致の全件1680 passedを再利用。05-02-SUMMARY | 自動pass |
| 05-02-02 / 2 | T-05-06/07 | 局所104 passed、全件1694 passed。05-02-SUMMARY。人手H04/H06/H07/H08を別実施 | 自動pass / 人手pass |
| 05-03-01 / 3 | T-05-09/10/11 | 局所26 passed、全件1718 passed。05-03-SUMMARY | 自動pass |
| 05-03-02 / 3 | T-05-09/10/11 | 局所428 passed、全件1745 passed。05-03-SUMMARY | 自動pass |
| 05-03-03 / 3 | T-05-10/11 | 局所117 passed、全件1778 passed。追加Tcl解放警告は05-03-deferred-items.mdでopen | 自動pass / 警告未解決 |
| 05-04-01 / 4 | T-05-12/13 | config全体+Toast+PDF280 passed、最終単一全件1789 passed/1 warning/278.95秒/exit0。診断423原本/コピー/manifest一致、入力103hash一致。05-EVIDENCE。利用者H01〜H12は05-UATに原文記録 | 自動pass / 人手12 pass |
| 05-04-02 / 4 | T-05-13 | Python入力103hashを再照合し、コード・依存・環境を変えず全件とRuff/format108 unchanged/AST成功を再利用。説明・証拠を12 passへ同期。descriptor不明2件は未解除 | タスク完了 / 独立検証待ち |
| 各タスク | T-05-SC | 新規installなし、pyproject.toml編集なし、依存の既存未commit差分は保持 | 対策を維持 |

上の実測表と05-EVIDENCEが自動実行値の正本。人手は05-UATの利用者回答を正本とし、H03の約10秒自然消去とH04の✕、H06のApply直後のモーダル保持を区別する。通知開始前の厳密な境界は自動証拠。独立検証・Nyquist・Phase 6 EXE受入は未実施のまま。

### Wave 0監査項目（2026-10-24独立監査済み）

- [x] `tests/test_config_notification.py` — 05-01-01 の先頭tracerで作成し、その後の各タスクが上表のクラスを追加した。テストだけの独立した基盤waveは設けない。
- [x] `tests/test_settings_keyguard.py` — 05-01-02/05-02-01で読込境界・AtomicSettingsWriteを拡張した。
- [x] `tests/test_toast.py` — 05-02-02で再試行なし/自動消去/競合を追加し、既存PDF保存/印刷の再試行動作も維持した。
- [x] `tests/config_notice_support.py`・`05-NOTICE-HARNESS.py`・`TestScenarioIsolation` — 05-04-01で作成し、恒久pytestはtests内helperだけをimportする。隔離自動検証と人手12項目を実施した。
- [x] `tests/test_provider_ui.py`・`tests/test_ocr.py`・`tests/test_pagination.py` — 05-03-02/03で実App保存owner経由へ既存spy/stubを移行し、保存一回と状態更新のassertを維持した。
- [x] Tcl/Tkの実行経路は制限外 `.venv`・専用basetempとする。05-PLANNING-CHECKS.mdのToast 33 passedおよび全件ERROR 0が根拠。sandboxのTclError原因解明・全件合格とは区別する。
- [ ] `DEP-05-REGRESSION` — 診断版の全件は1637 passedだが、元の終了待ち失敗は未再現・原因未確定で未解除。2026-10-23利用者判断により診断採用・再発時停止の条件で実行する。チェックを完了に変えない。
- 新規テストフレームワーク・パッケージの導入は不要。

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| 起動後通知が入力先を奪わず編集を続行できる | V110-CFG-01/04 | 実Windows/Tkでの操作感・フォーカス | 隔離した破損設定で起動し、PDF操作と通知の表示・自動消去を確認する。本番設定を使わない |
| 連続保存失敗・言語変更・再構築で未消化通知を失わない | V110-CFG-02/04 | 複数操作中の可視性と文言 | 隔離環境で保存失敗を注入し、連続変更と再構築後に各通知を認識でき、成功表示が出ないことを確認する |
| PDF/印刷通知と競合しても各設定失敗を確認できる | V110-CFG-04 | 同時操作時の可読性 | 既存retry通知を表示中に設定保存を失敗させ、既存通知を閉じると設定通知へ進むことを確認する |
| 終了保存失敗を認識し、編集継続または再度の終了を選べる | V110-CFG-02/04 | 終了時の可視性と操作感 | D-19承認済み。利用者が確認Noの保存0、初回失敗時の画面維持、次回確認Yesの保存省略、明示成功flag解除を目視する |
| unreadable保護中の未保存通知・モーダル終了後の可視時間 | V110-CFG-02/03/04 | 原本保護の文言と実操作中の可視性 | 利用者がD-20の明示未保存通知/終了無通知、Settings/OCR/Pluginを10秒以上保持しても解除後にD-21の各イベントが表示されることを確認する |

## 未解決の仕様プローブ

SPECなしの edge-probe は V110-CFG-01/02/03/04 全4行が `unclassified` / `unresolved`、verification/resolution は null のまま。要件・CONTEXT由来の境界テストを上表へ追加してもプローブの解決証拠へ置き換えない。05-01記載の descriptor-less prohibition 2件は文言・編集継続の人手確認を踏まえて評価したが、禁止内容のdescriptorがなくIDとの対応が確定できないため `flagged-unverified` を維持する。人手gateの完了と未識別項目の解決を混同しない。

## Validation Sign-Off

- [x] 全タスクに automated verify または Wave 0 作成依存がある
- [x] 自動検証なしのタスクが3つ連続しない
- [x] Wave 0 が未作成の参照を被覆する
- [x] watch-mode を使用しない
- [x] 局所フィードバック60秒目標と全件実測を記録する
- [x] 実装後に確認してから `nyquist_compliant: true` にする

**Approval:** validated 2026-10-24（独立監査、4要件・9タスク、追加ギャップ0）

## Validation Audit 2026-10-23

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
