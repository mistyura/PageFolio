# Phase 04 依存検証の再結合（2026-11-05、W05c計測入力後）

## 判定範囲と生証拠

Phase 06のW05c計測追加により、公式`verification.status`は`tests/test_startup_windows.py`だけを変更入力として`stale`とした。Phase 04のROADMAP成功条件5件、PLAN 6件のmust-have、要件5件、既存21 truthを縮小せずに現在の実装と試験へ再照合した。製品の起動・通知・復帰処理とUI文言は前回のcovered入力から変化していない。今回のWindows試験差分はmanual native-quitの観測を追加し、明示flagの自動対照以外には接続しない。`tests/w05c_evidence.py`のnative callbackはメモリ記録と元WndProcへの委譲だけで、元の終了判断を変更しない。観測の故障注入、Noのあり/なし、実Windows process、回収前snapshot、外部native窓とowner終了の試験を読んだ。正式W05c/scriptの利用者No成功は未取得である。

新しい単一全件の正本は`.planning/phases/06-release-validation/06-05-evidence/w05c-instrumentation-native-20261105/`。`result.json`はexit 0、2026-11-05T06:08:57.301Z〜06:28:50.681Z、`changed: []`。`before`/`after`は各**167一意入力**で一致し、再照合時の現行SHA-256も167/167一致した。runnerの配列には重複1件があり、実hash台帳の一意キー数は167である。JUnitは2293 testcase、failure/error/skip各0。`stdout.txt`は2293 passed / 2 warnings / 1191.69秒。Phase 04対象のDoD19、startup_control52、focus32、foreground_audit24、notice61、wake23、windows88の計299件と、新規W05c証拠39件は全て成功した。新39件はPhase 04の実機受入件数に算入しない。

`checks.json`はRuff check 2回ともexit0、formatは144 Python変更なし、ASTはexit0。ただしrunnerのRuff check 2回のstderrにはアクセス拒否warningがある。直前のRuff対象列挙は144ファイル/stderr空、全件終了後の`ruff check . --no-cache`とverbose再実行はexit0/警告なし。runnerのwarningは試験開始前の一過性で、Ruffがパスを示さず原因パスは未特定。生warningを消さない。pytest警告2件はPyMuPDFの`ByteString`廃止予告と`record_property`/xunit2非互換である。最初のsandbox実行の`init.tcl`読取不可・0件/1errorは別の環境試行であり、上記native全件と混同しない。

## 必須ゲート順

| 順 | ゲート | 今回の判定 |
|---|---|---|
| 1 | `verify:post` Nyquist | 6 PLAN/13タスク/5要件の自動対応を現行299 named testと新全件JUnitへ再結合。MISSING/PARTIAL 0。新39件は計測の正負対照。 |
| 2 | `verify:post` Security | 計画時22脅威の緩和実装を確認しopen 0。新計測は試験process限定、製品network/auth/schema境界は不変。 |
| 3 | `verify:post` UI | 静的6柱のみ継承。実画面capture・クリック・DPI/UAC・実EXEは未実施なので`partial`/score null。 |
| 4 | `execute:post` Code review/disposition | 新観測の接続・元処理委譲・計測失敗時の拒否を確認。新規Critical/Warning 0。CR-01 fixed、WR-01 deferredを維持。 |
| 5 | Regression | Phase 04は現マイルストーンの最初のphaseで先行VERIFICATIONはない。今回の単一全件と299件を回帰証拠として再利用し、pytestを重複起動しない。 |
| 6 | Goal verification | ROADMAP 5条件/要件5件/既存21 truthを現在の製品配線・試験assert・新JUnitに再結合。承認済みPhase 04自動範囲21/21、behavior-unverified 0。 |

Phase 04の禁止事項3件はflagged-unverified、未分類edge5件、WR-01の並行15609ms/単独15140ms、`DEP-05`、`owner_missing`、前景切替要求元の不明、Phase 06の実機/視覚/DPI/UAC/EXE受入は未解除。W05c元No不成立の原因と正式台帳の28 pass/80必須not-run・対象外2 not-runも変更しない。Phase 04の限定判定をPhase 06の出荷許可に転用しない。
