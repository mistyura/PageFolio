# Phase 04 現行入力の再検証（2026-11-05）

## 判定境界

Phase 06 の `resume_contract` が依存元 Phase 04 の検証鮮度を要求したため、完了済み6 PLAN / 6 SUMMARYを再実装せず、`verify-phase-goal.md` のゲートを現行入力で再評価した。製品・試験・版・STATE・ROADMAP・Phase 05/06を編集せず、W05cの人手受入を起動していない。

前回 `04-VERIFICATION.md` は21/21 passedだったが、所有CLI `verification.status` は `tests/startup_wake_child.py`、`tests/test_startup_wake.py`、`tests/test_startup_windows.py` を moved_files とする stale を返した。`e13a00b` との差分は前二者が当時未追跡だったためnumstatに出ず、Windows試験は432行追加・68行削除。`test_focus_restore_real_main_windows` に合成fixtureの自動ケースを追加し、native通知の前景監査と9process試験に接続した。実機W05cの操作・視覚合格を意味しない。

## 現行実走と入力同一性

証拠ディレクトリは `04-reverify-20261105-full/`。新規 `04-reverify-current.cjs` が一意のディレクトリとbasetempを作り、全件を一度だけ実行した。`run.json` の実行時刻はUTC 00:30:28〜00:40:01、終了値0。`stdout.txt` は **2254 passed / 2 warnings / 571.44秒**。`junit.xml` のsuiteはtests 2254、failures/errors/skipped各0。`stderr.txt` は空。実行前後の `inputs-before.json` / `inputs-after.json` でPythonとAGENTS・pyproject・Ruff設定の118入力は118/118一致、変更0。前回の2231件等は今回の実走と混同しない。

Phase 04対象の名前付きtestcaseは299件で、DoD19、startup_control52、startup_focus32、startup_foreground_audit24、startup_notice61、startup_wake23、startup_windows88。目標への主要な直結例は `test_native_tcl_getmessage_stall_recovers_with_product_wake` 3件、`test_constructor_failure_real_main_nonactivate_notice` 1件、`test_notice_dedup_eight_processes_keep_original_deadline` 1件、`test_focus_restore_real_main_windows` 30件、`test_working_state_real_main_continues` 3件で、JUnitに失敗・skipなし。自動試験の `manual=True` は合成PDF/OCRによる回帰で、利用者の実操作ではない。

全件警告2件はPyMuPDFのByteString廃止予告とpytestの `record_property` / xunit2 非互換通知。Ruff `check .` は終了値0だが、実走中の新basetempを走査してアクセス拒否warningを出した。`format --check .` は同じアクセス拒否で終了値2となり、生出力を `ruff-format-check.txt` に保持した。basetempを除外した `check . --extend-exclude .planning` は終了値0（`ruff-check-excluding-evidence.txt`）、`format --check . --extend-exclude .planning` も終了値0、115 files already formatted（`ruff-format-check-excluding-evidence.txt`）。AST `pagefolio.py`、対象 `git diff --check` も成功。品質初回の環境境界を隠さず、製品の整形不良とは判定しない。

## ゲート処置

| 順 | ゲート | 現行判断 |
|---|---|---|
| 1 | Nyquist | 6計画・13タスク・5要件の既存対応を、現行299名付き試験と全件JUnitへ再結合。自動範囲MISSING/PARTIAL 0。人手Wは対象外。 |
| 2 | Security | 計画時T-04-01〜21/SCの22脅威についてopen 0。製品のnetwork/auth/schemaは増えず、変更された監査・合成fixtureに新たな未緩和highを検出せず。 |
| 3 | UI | 抽象6柱の静的判定のみ。実画面capture、実クリック、DPI、UAC、EXEはPhase 06に残し、partial/score nullを維持。 |
| 4 | Code review | Windows試験の現行差分と監査接続を確認。新規Critical/Warning 0、既知Warning 1。CR-01 fixed / WR-01 deferredを維持。 |
| 5 | Regression | 現マイルストーンのPhase 04は最初のPhase。先行PhaseのVERIFICATIONがないため専用の先行回帰対象なし。今回の単一全件成功はより広い回帰証拠。 |
| 6 | 独立goal verification | ROADMAPの5成功条件と5要件を、現行製品・試験・生JUnitで再照合。承認済みPhase04の自動範囲21/21を維持。 |

WR-01の並行15609ms/単独15140ms、DEP-05、owner_missing、元の前景切替要求元の未確定、禁止事項3件flagged-unverified、edge5件unclassified、人手Wのnot-runは解除しない。Phase 06の実機受入・出荷許可は別判定。
