# Phase 5 計画時の検証記録

2026-10-22。製品コードは変更していない。計画検証と実装後の受入は別である。

## 実行環境の切り分け

| 実行 | 結果 | 判断 |
|---|---|---|
| 調査: `tests/test_settings_keyguard.py` | 19 passed | 既存設定単体テスト成功 |
| 調査: Tk通知テスト（sandbox） | `Cannot find a usable init.tcl` | 実行環境の制限を含む。原因をインストール不足と断定しない |
| 全件pytest、sandbox、`--basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | 35 failed, 1570 passed, 24 errors, 3 warnings / 107.84秒 | Tcl初期化・Windows子プロセス等で失敗。未合格 |
| 制限外 `tests/test_toast.py`、専用basetemp | 33 passed, 1 warning / 0.49秒 | 単体成功。全件合格の代用ではない |
| 制限外全件、同じ既存basetemp | 1391 passed, 238 errors, 239 warnings / 40.45秒 | 既存tempディレクトリの削除権限によりセットアップ失敗。未合格 |
| 制限外全件、`--tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_phase5_plan_20261022"` | 6 failed, 1623 passed, 2 warnings / 257.06秒、exit 1 | 下記Windows起動・フォーカスの失敗が残る。未合格 |

最終全件実行で失敗したテスト:

- `tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor[2]`
- `tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor[8]`
- `tests/test_startup_windows.py::test_cross_entry_owner_accepts_both_entries_and_other_location[relocated]`
- `tests/test_startup_windows.py::test_focus_restore_real_main_windows[thumb-entry-script]`
- `tests/test_startup_windows.py::test_focus_restore_real_main_windows[preview-entry-module]`
- `tests/test_startup_windows.py::test_focus_restore_real_main_windows[nested-entry-script]`

症状はreadyの期限超過・expired・focus_correct不成立。原因未確定であり、環境だけの問題や製品欠陥と断定しない。既存maintenance作業もincompleteである。Phase 5の計画作成へ無関係な修正を混ぜず、全件合格までコミットを保留する。テスト削除・skipによる免除は行わない。

## 計画検証

- 計画担当による全4 PLAN の frontmatter/plan-structure: valid、errors/warningsなし。
- 決定的verify-command-paths: 11件、not_applicable。Pythonコマンドのパス検証成功を意味しない。
- 決定的verify-failure-directions: 11件ok、blocker/warningなし。
- 独立plan-checker初回: 2 blockers（research_resolution、既存全件失敗から必須品質ゲートへ到達する依存経路の不足）。
- revision 1: 調査の計画上の判断/実行経路を根拠付きで解決し、`DEP-05-REGRESSION`を実装前の必須依存として明記。既存失敗を修復済みにはしていない。
- 独立再検証: `VERIFICATION PASSED`。計画品質合格、実装依存未充足を区別して報告。
- 修正後のverify-command-paths/failure-directionsは前回と一致（11件）。
- decision-coverage-plan: passed、18/18、uncoveredなし。
- gap-analysis.plan-post: passed、要件4＋決定18＝22/22、uncovered 0。
- 4 plans / 4 waves / 8 tasks。計画の構造検証は合格、実装後のNyquist/UATは未実施。
- `commit_docs: true`だがAGENTS.mdのコミット前全件pytest成功条件が未達のためコミットを保留。既存の未コミット変更を維持する。
- 次は独立GSD debug/maintenanceで回帰依存を解消し、その成功証拠を確認してから `$gsd-execute-phase 5`。自動実装は開始していない。

## 2026-10-22 追記 — DEP-05-REGRESSION解除

上記は計画時点の失敗と判断として保持する。後続の独立 `$gsd-debug Phase 5` で、起動テストの期限切れ契約・bootstrap待機と、製品の入力先選択・Tkイベント処理後の観測を修復した。

- 修復commit: `8689c2720e38fc2397407e38317687d1952b22f6`（適用済み、v1.9.1）。
- 修正前は対象6件・全件1629件とも成功し非再現。その後、初期化8.5秒遅延1件と一時的toplevel focus 3件で修正前の失敗を決定的に再現した。
- 修正後Windows局所24件成功。最終全件は**1635 passed、failed 0、ERROR 0、skipped 0、1 warning、239.82秒、exit 0、クラッシュなし**。
- 実command: `.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_full_20261022_02"`。Windows 11 / Python 3.15.1 / Tk 9.0 / Tcl 9.0.4、sandbox外の単一pytestプロセス。既存未コミットの依存更新を含む環境。
- lint/AST成功。RuffのMarkdownコード例への適用を分離し、`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"` は100ファイル変更なしで成功。pyproject.tomlは変更なし。
- 原因・再現・初期警告・検証対象SHA256・ログ参照: [debug記録](../../debug/dep-05-regression.md)。旧focus失敗の個別イベント順序は旧証跡不足のため遡及確定しない。
- **DEP-05-REGRESSIONは充足。** Phase 5の実装・Nyquist/UATは未実施。次は `$gsd-execute-phase 5`。既存計画とmaintenanceの未コミット変更は保持する。

## 2026-10-22 追記 — reviews再計画（今回の現行判断）

上記解除記録は履歴として保持する。05-REVIEWS.mdの最新制限外単一全件は **1 failed / 1634 passed / 0 errors / 1 warning / 354.41秒 / exit 1**。normal-entry-scriptのchild.communicate(timeout=12)期限超過は原因未確定であり、**DEP-05-REGRESSIONを未充足へ戻す**。独立GSD debugと現在コード/環境の単一全件成功まで製品実装・コミットを停止する。今回、製品テスト・原因調査・製品コード変更・コミットは行っていない。

- 承認済み回答をD-19（終了初回停止/次回保存省略）、D-20（unreadableは正常再起動まで保存禁止）、D-21（同時1表示、各失敗10秒を保持）としてCONTEXTへ追記した。
- CR-05-01〜07、Divergent Views、LOW提案を4 PLANの具体タスクまたはReview Dispositions Ledgerへ反映した。レビュー原本は未コミットのためcommit SHAを捏造せず、内容SHA-256 `CD8A95E3821A801C078116799D9ADC69CBFD0C6CF680929E39ABC7B6B2EB4218` で識別する。
- 4 plans / 4 waves / 9 tasks。05-03を3タスクに分割し、plugin.py・test_ocr.py・test_pagination.pyを変更/verify対象へ追加。各taskのfilesは3〜5ファイル、read_first/acceptance_criteriaあり、全automatedの直後にfails_whenあり。変更を隠れた第6ファイルへ持たせていない。
- 全4 PLANのfrontmatter.validateとverify.plan-structureはvalid、errors/warningsなし。末尾はすべて閉じたoutput。これは計画品質の検証であり製品動作の合格ではない。
- requirements V110-CFG-01〜04とD-01〜21、GOAL/REQ/RESEARCH/CONTEXTを05-04のMulti-Source Coverage Auditへ対応付けた。最終のdecision-coverage/gap-analysis等は親の決定的ゲートで再確認する。
- plan:preの全planner contributionを確認。API detectorは実PLAN本文＋ROADMAP Phase 5に対してexit 1・detected=false（未入力skipではない）。assumption-delta scan 5はdetected=false。ORM schema pathは0。ASVS1/highの13脅威はphase内一意、T-05-SCを全PLANに維持。新規API/SDK/パッケージ導入なし。
- SPECなしfallbackを再実行: edge-probeの実要件4行はapplicable=4/resolved=0/unresolved=4/unclassified=4。projectProhibitionsの2件はdescriptor-less/unverified/flagged=trueのまま。利用者の目視結果前にpassへ変えない。
- 既存変更対象とPython/Ruff/AST入口のパス存在を確認。pagefolio/dialogs/plugin.py、tests/test_ocr.py、tests/test_pagination.pyを含む既存製品/試験/説明ファイルはgit追跡済み。新設予定5ファイルは未作成、05-VALIDATION.mdは既存の未追跡計画資料として区別した。
- estimate-calibrationはfactor=1/sample_count=0/confidence=low。raw見積りは01=24000、02=27000、03=32000（3 tasks）、04=18000、補正後同値。
- 整形契約は実証済みのPython include限定formatと整形後lintへ統一。恒久試験helperはtests/config_notice_support.pyとし、pytestからplanning harnessへのimport依存を作らない。
- ROADMAP/STATE/state.jsonの最終整合・独立checkerは親オーケストレータ担当。既存の別件未コミット差分とレビュー原文は保持した。

### レビュー再計画の最終検証

- 独立 `gsd-plan-checker`: **VERIFICATION PASSED**。4計画/4 waves/9タスク、4要件・21決定、CR-05-01〜07とdivergent/LOW処置、終了・unreadable・FIFOの具体的分岐を確認した。計画品質の合格であり実装GOではない。
- `check verify-command-paths 5 --raw`: exit 0、13件すべて `not_applicable`、blocker/warning 0、readErrorなし。Python/Ruffコマンドの実行・パス検証成功を意味しない。
- `check verify-failure-directions 5 --raw`: exit 0、13/13 `ok`、blocker/warning 0、readErrorなし。
- `query check.decision-coverage-plan`: passed、21/21、uncoveredなし。
- `check gap-analysis.plan-post`: passed、要件4＋決定21＝25/25、uncovered 0。
- context-driftはstaleなし。codebase-driftはno-mapped-commitでskip。UI gateはsandboxのEPERM後に制限外で読み直し、exit 0・frontend=true・hasFrontendEvidence=false・hasUiSpec=false・block=false・readErrorなし。UI-SPECは未作成。
- `query state.planned-phase`で計画完了を記録し、ROADMAP依存注記は既存4 wavesを再利用。その後、STATE/ROADMAP/state.jsonはレビューの最新回帰結果を根拠に「計画合格・DEP-05-REGRESSION未充足」へ整合した。GSDのstate.json再生成で省かれた既存maintenance記録は原文の値で復元した。
- 自動実行は無効のまま。製品コード・テスト変更、pytest/ruff/ASTの再実行、コミットは行っていない。AGENTS.mdのコミット前pytest合格条件未達のためcommit_docs=trueでも保留する。
- 次は独立 `$gsd-debug Phase 5 DEP-05-REGRESSION`。現行単一全件合格後に `$gsd-execute-phase 5`。

## 2026-10-22 追記 — 独立debug再評価（未解除）

上記から独立debugを実施。元失敗の二次起動result.jsonは約1秒で正常保存されており、communicateの出力読取りスレッド待機との切り分けが必要と判明。診断追加後の最新単一全件は1635 passed / failed 0 / ERROR 0 / 2 warnings / 231.65秒 / exit 0。元失敗は未再現・原因未確定で新規修復なし。Tcl別スレッド破棄警告との因果も未証明のため、依存は未解除。診断変更は未コミット、Phase 5実装未着手。詳細と途中の失敗を `.planning/debug/dep-05-regression.md` に保存。次は `$gsd-debug continue dep-05-regression`。
