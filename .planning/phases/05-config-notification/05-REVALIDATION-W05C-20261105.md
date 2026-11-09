# Phase 05 依存検証の再結合（2026-11-05、W05c計測入力後）

## 現行入力と依存元

公式`verification.status`はPhase 05のcovered集合で`tests/test_startup_windows.py`だけを変更として`stale`とした。Phase 04は先に必須ゲート順で再検証し、`04-VERIFICATION.md`の公式status `passed`を確認した。根拠は`../04-startup-control/04-REVALIDATION-W05C-20261105.md`と`04-QUALITY-RECHECK-W05C-20261105.json`。Phase 05の製品設定読込/保存/通知/OCR offコードとUI文言は前回covered入力から不変である。ROADMAP 4成功条件、4要件、4 PLANの既存19 truthを縮小しない。

新しい単一native全件の正本は`../06-release-validation/06-05-evidence/w05c-instrumentation-native-20261105/`。`result.json`はexit0、2026-11-05T06:08:57.301Z〜06:28:50.681Z、前後`changed: []`。hash台帳は**167一意入力**で、再照合時の現行SHA-256も167/167一致。設定/通知の主要実装・試験は全てこの台帳に含まれる。JUnitは2293 testcase、failure/error/skip各0、stdoutは2293 passed / 2 warnings / 1191.69秒。Phase 05関連のconfig_notification143、settings_keyguard26、toast38、OCR provider_refresh18、release_contract30、release_uat_support243件は全てpass。Phase 04対象299件も同じ全件でpass。新W05c証拠39件は正式人手受入とは区別する。最初のsandboxの`init.tcl`読取不可・0件/1errorは別試行であり、native結果に算入しない。

runner事前Ruff checkの2回はexit0だがアクセス拒否warningを出した。対象列挙は144ファイル/stderr空、formatは144変更なし/stderr空。全件終了後の現行`ruff check . --no-cache`と`ruff format --check . --no-cache`はともにexit0/stderr空で、167入力も現行一致。runner警告の原因パスは未特定とし、`../04-startup-control/04-QUALITY-RECHECK-W05C-20261105.json`にargv/exit/stdout/stderrとmanifest照合を保存した。pytest警告2件はPyMuPDFの`ByteString`廃止予告と`record_property`/xunit2非互換である。

## 必須ゲート順

| 順 | ゲート | 今回の判定 |
|---|---|---|
| 1 | `verify:post` Nyquist | 4要件/9実装タスクの自動対応を現行コード・assert・新JUnitへ再結合。MISSING/PARTIAL 0。 |
| 2 | `verify:post` Security | 計画時14脅威の設定原本・機密・排他的tmp→replace・通知所有の緩和を確認。open 0。新計測は試験process限定。 |
| 3 | `verify:post` UI | 製品UIは不変のため既存の静的22/24を限定継承。実表示capture/クリック/DPI/UAC/実EXEは未実施。V-01/S-01を維持。 |
| 4 | `execute:post` Code review/disposition | W05c計測差分は既存の設定保存経路/通知と干渉しない。新規Critical/Warning 0。CR-01/02/03とWR-01 fixed/open0を維持。 |
| 5 | Regression | Phase 04の新しい公式passed報告と同一native全件のPhase 04対象299件を確認。全件pytestを重複起動しない。 |
| 6 | Goal verification | 設定読込分類・保存失敗通知・原本保護・通知集約のROADMAP 4条件、4要件、既存23 truthを現行実装・JUnit・既存利用者H受入へ再結合。23/23、behavior-unverified 0。 |

H01〜H14と禁止事項2件の意味評価は以前の利用者passを継承し、今回の実施とは記録しない。`DEP-05-REGRESSION`、`owner_missing`、通知前景不一致、descriptor不明2件、未分類edge4件、UIのV-01/S-01は未解除。Phase 06の正式台帳28 pass/80必須not-run・対象外2 not-run、元W05cのNo不成立と原因不明、実EXE/DPI/UAC受入、`release_approved: false`は維持する。Phase 05の限定判定は出荷許可ではない。
