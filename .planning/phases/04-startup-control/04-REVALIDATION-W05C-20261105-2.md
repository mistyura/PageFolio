# Phase 04 依存検証の再結合 2回目（2026-11-05、W05c v3試験入力後）— 全件ゲートで停止

## 判定範囲と生証拠

公式`verification.status`は、前回の再結合（`04-REVALIDATION-W05C-20261105.md`、2293件正本）の後に未コミットで変わった試験側入力によって`stale`になった。前回正本の167一意入力と現行を照合すると160件が一致し、相違は`tests/test_startup_windows.py`、`tests/w05c_evidence.py`、`.gitignore`、`開発履歴.md`と、Phase 06の`06-05-record-w05c-python.cjs`、`06-05-w05c-evidence.cjs`、`06-07-quality.cjs`の7件である。新規の試験ファイル`tests/w05c_runner.py`と`tests/test_w05c_runner.py`も追加されている（前回入力集合の外）。製品コード（`pagefolio/`、`pagefolio.py`）は167入力の範囲で全件が一致した。前回版の試験バイト列はgitにも証拠にも残っていないため、前回との差分を行単位で再構成することはできない。

新しい単一プロセス全件の証拠は`04-reverify-20261105-w05c2-full/`にある。`runner.cjs`は実行に使ったランナーの写しで、実行後に複製したため入力hashには含めない。ランナーは`06-07-quality.cjs` plan05の入力集合と`04-reverify-current.cjs`の走査集合を合わせた170入力を使い、Ruffは非破壊の`format --check`で実行した。

| 項目 | 結果 |
|---|---|
| 実行 | 2026-11-05T09:46:21.212Z〜10:02:22.753Z、`-q -rA -p no:cacheprovider`、basetempは`%LOCALAPPDATA%\Temp\pf04-04-reverify-20261105-w05c2-full`。`-x`なし・除外なし |
| 結果 | **1 failed / 2332 passed / 2 warnings / 960.36秒、exit 1**。JUnitは2333 testcase、failures 1 / errors 0 / skipped 0。stderrは空 |
| 入力 | 170入力の前後一致170/170、停止記録作成時点の現行一致170/170、`changed: []` |
| 品質 | `ruff check . --no-cache`はexit 0。`ruff format --check`は146ファイルが変更不要。ASTはexit 0。いずれもstderrは空 |
| Ruff対象 | 146ファイル。前回の144ファイルに`tests/w05c_runner.py`と`tests/test_w05c_runner.py`が加わった |
| warning | PyMuPDFの`ByteString`廃止予告と、`record_property`の xunit2 非互換。どちらも前回と同じ |
| Phase 04の対象 | DoD19、startup_control52、focus32、foreground_audit24、notice61、wake23、windows88の計299件のうち**298 passed / 1 failed** |
| W05cの試験 | `test_w05c_evidence` 39件と`test_w05c_runner` 40件はすべて成功した。Phase 04の受入件数には数えない |

## 失敗（症状①のTclError/ERRORではなく、assertの失敗）

`tests/test_startup_windows.py::test_focus_restore_real_main_windows[native-quit-False-entry-module]`は1664行の`assert measured["target_correct"]`で失敗した。これは自動の native-quit 対照で、manual=False・`w05c-observe`なしのため、W05c observerは組み込まれていない。owner fixtureは`04-reverify-20261105-w05c2-full/failed-fixture-native-quit-False-entry-module/`に複製して保全した。

`focus-result.json`の値は`result: foreground_denied`、`activated: 5641316` = `expected_tk: 5641316`、`native: null`、`state_preserved: true`、`focus_correct: true`、3ページ/[90,90,0]だった。peerは`constructed 0` / `restored 0` / `foreground_denied` / 78ms。前面化要求の時点でowned native確認窓が取得されておらず（`native: null`）、Tk本体の窓が対象になった。native系の判定は`actual not in {None, expected} and native == actual`なので、この結果はFalseになる。

一つの仮説として、`focus-ready`の生成が`pdf()`と`app._quit()`のaskyesno表示より前にあるため、peerの前面化要求が確認窓の生成より先に処理された競合が考えられる。ただし未証明である。製品の欠陥なのか、試験の時序なのかは判断していない。

## CLAUDE.md の切り分け手順

1. **該当ファイル単体**（`04-reverify-20261105-w05c2-isolate-file/`、10:03:26Z〜10:09:51Z、同じフラグ、別basetemp）: **88 passed / 1 warning / 383.56秒、exit 0**。JUnitは88件、failure/error/skip 0。
2. **フルスイートの再実行**: 実施していない。今回の指示は「全件証拠は1回だけ」であり、失敗時は停止するよう求めている。再実行するかどうかは利用者の判断に委ねる。

単体実行の成功は、この失敗を原因へ切り分けるための記録である。合格の根拠にはしない。CLAUDE.mdのリリースゲート（単一プロセス全件で失敗0）は**不成立**。skip・除外・試験の削除・再実行でグリーンにすることは行っていない。

## 必須ゲート順

| 順 | ゲート | 今回の判定 |
|---|---|---|
| 0 | 単一全件 | **不成立（1 failed）**。ここで停止した |
| 1 | `verify:post` Nyquist | 未実施。新しい全件JUnitにPhase 04の対象failureが1件あるため、再結合しない |
| 2 | `verify:post` Security | 未実施 |
| 3 | `verify:post` UI | 未実施（実施する場合も静的6柱の継承のみ、partial / score nullの方針を維持する） |
| 4 | `execute:post` Code review/disposition | 未実施。CR-01 fixed / WR-01 deferredの台帳は変更していない |

`04-VALIDATION.md`、`04-SECURITY.md`、`04-UI-REVIEW.md`、`04-REVIEW.md`、`04-REVIEW-DISPOSITION.md`、`04-VERIFICATION.md`は変更していない。Phase 04の禁止事項3件のflagged-unverified、未分類edge 5件、WR-01（並行15609ms / 単独15140ms）、`DEP-05`、`owner_missing`、前景切替の要求元が不明であること、W05c元No不成立、正式台帳28 pass / 80 not-run・対象外2、出荷不可は、すべて未解除のまま維持する。製品・試験・`pyproject.toml`・Phase 06台帳・STATE/ROADMAPは変更しておらず、commitもしていない。

## 利用者の判断が必要な事項

- フルスイートを再実行してCLAUDE.md手順2を記録するか。仮にグリーンになっても、今回の失敗は記録に残す。
- `native-quit`自動対照の`target_correct=False`（`native: null`）を`/gsd-debug`で原因調査するか。このとき、`focus-ready`と確認窓生成の時序、および過去に同じ失敗があったかを確認する（`.planning`内の記録には同じ失敗が見当たらない）。
