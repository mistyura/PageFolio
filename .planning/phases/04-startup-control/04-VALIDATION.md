---
phase: "04"
slug: "startup-control"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-21"
---

## 2026-11-06 CR-02修正後のNyquist再結合（現行）

採用判断を厳密化した後の単一全件 `04-reverify-20261106-cr02/` は2361 passed、failure/error/skip各0、170入力前後/現行一致。既存13タスク/5要件のPhase04対象299件に加え、W05c証拠39件/runner68件がpass。新28件はv2/v3・否認7種・dry-run/書込の実拒否と全ファイル無変更を検査する。REDの否認受理再現とGREEN107件を保持。MISSING/PARTIAL 0、追加テスト不要。Ruff check/format/AST成功、全件の標準エラー空。詳細は `04-REVALIDATION-20261106.md` / `04-QUALITY-CR02-20261106.json`。

## 2026-11-06 native確認窓の試験時序修正後のNyquist再監査（履歴）

GSD validate-phase State Aとして6 PLAN/13タスク/5要件の既存Per-Task Mapを現行JUnitへ再照合した。`04-reverify-20261106-native-fix/` の単一全件2333 passed、failure/error/skip各0、170入力前後不変。Phase04名付き299件（DoD19/control52/focus32/foreground_audit24/notice61/wake23/windows88）が全て成功し、MISSING/PARTIAL 0。試験側のnative popup出現待機と出現起点30秒閉鎖は製品5秒期限を変えない。W05c計測39件/runner40件は人手受入とは別。詳細は `04-REVALIDATION-20261106.md`。過負荷時の別モードとPhase06移管項目は未解除。

## 2026-11-05 W05c計測後のNyquist再監査

Phase 04の6計画・13タスク・5要件は、現行製品配線、試験assert、native全件JUnitの対象299件へ再結合した。自動範囲のMISSING/PARTIALは0。新設のW05c証拠39件は観測機構の正負対照であり、正式script人手Noのpassには数えない。全件2293 passed、failure/error/skip各0、167一意入力の前後・現行SHA-256一致。Nyquist `validated`/`nyquist_compliant`を維持する。品質の現在cleanとrunner事前warningの区別は`04-QUALITY-RECHECK-W05C-20261105.json`、証拠と限界は`04-REVALIDATION-W05C-20261105.md`。人手Wは未実施のまま。

## 2026-11-05 現行入力のNyquist再監査

Phase 06再開の依存検証として、6 PLAN / 6 SUMMARY・13タスク・5要件を現行コードと試験へ再照合した。Phase04の自動範囲はMISSING 0 / PARTIAL 0、`status: validated` / `nyquist_compliant: true`を維持する。新規単一全件は `04-reverify-20261105-full/{run.json,junit.xml,stdout.txt,inputs-before.json,inputs-after.json}` の **2254 passed / 2 warnings / 571.44秒 / exit0**、JUnit failures/errors/skipped 0。実行前後118入力は不変、Phase04対象の名前付き299件にskipはない。詳細と旧証拠との差異は `04-REVALIDATION-20261105.md`。合成fixtureの自動成功を実機W05cの人手passには使わない。

## 2026-10-28 品質停止解除後の Nyquist 再監査（最新）

Phase 06 再開の依存検証として State A、6 PLAN / 6 SUMMARY、13タスク、5要件を再照合した。下記 Per-Task Verification Map の自動範囲は COVERED、MISSING 0 / PARTIAL 0 を維持する。最新の単一全件は `.planning/debug/quality-gate-unblock-20261028/full.json`・`full.xml`・`full-0.stdout.txt` の **2071 passed / 2 warnings / 480.86秒、exit 0、failed/ERROR/skip 0**。2047件の旧成功とは別の実走であり、今回再実行していない。

実行時前後の146入力は不変。現行と142/146一致、Python137/137一致で、相違は `.gitignore`、`docs/DEVELOPMENT.md`、`CONTRIBUTING.md`、`開発履歴.md` の4件だけ。実装・tests・AGENTS・pyproject・依存定義・Ruff設定は一致する。Python実体SHA256と環境のPython/Windows/主要5パッケージ版も照合済み。通知監査の新24件を含む全件を現在の製品/試験に再利用する。全体Ruff/format/ASTは同所 `native-final.json` の成功を再利用する（Python137/137一致）。

`tests/test_startup_windows.py` の追加監査は `tests/startup_foreground_audit.py` の保守的判定と接続し、owner＋8 peerのidentity・期限不変・通知集約に加え、禁止API要求、一時的前景化、要求元未確定の切替、証拠不足を不合格にする。`tests/test_startup_foreground_audit.py` の故障注入、実接続1件、9プロセス1件も同一入力の成功証拠に含まれる。旧118入力に含まれる製品/既存試験の相違は当該Windows試験だけで、従来の製品側緩和策を変更していない。

今回変更するのは検証報告の本文と追補だけで、DoDが読む frontmatter の validated/compliant および既存タスク対応は維持する。全件後の DoD/リリース契約47件成功は当時の文書の確認として区別し、変更後の全文書が同一と主張しない。自動範囲の Nyquist は pass。人手W、実EXE、DEP-05/owner_missing、WR-01の未解消、初回前景変化の原因未確定は維持する。証拠・各hash・再利用判定は `04-GATES-CURRENT-20261028.md` と同名JSONに記録した。

## 2026-10-28 前回入力での Nyquist 再監査（履歴）

State A として6 PLAN/6 SUMMARY、13タスク、5要件（V110-START-01/02/03、V110-FOCUS-01/02）を下表の試験へ再照合した。自動検証の MISSING/PARTIAL は0、追加テストは不要。人手W項目と実EXE受入は `06-UAT-CARRYOVER.md` の not-run を維持する。

前回停止後の試験契約修正は `tests/test_startup_wake.py` と `tests/startup_wake_child.py` のみで、製品側のwake実装は変わっていない。前景値を診断として残し、`PostThreadMessageW` の送信先・`WM_NULL`・呼出スレッドと禁止APIを正負対照で検証する。旧判定を一時的に戻すと偽陽性を再現し、新判定の対象試験は23件合格した。初回原本の前景値変化の発生原因は証拠不足で未確定のまま。

ゲート報告編集前に現行118入力を `.planning/debug/startup-wake-foreground-evidence/full-native-after-state/inputs-before.json` と `inputs-after.json` に照合し、前後一致・当時の現行一致118/118を確認した。同じ入力の単一native全件試験は `run.json`（exit 0、入力不変）と `pytest.txt`（**2047 passed / 1 warning / 427.01秒**）を再利用し、理由のない再走をしていない。警告は既存PyMuPDFの `ByteString` 廃止予告のみ。本書更新後は本書だけが元manifestと異なるため、現在のDoD19件を専用basetempで実行し19 passed / 2 warnings / 0.42秒、exit 0（生ログ `04-gate-dod-20261028.txt`）。2つ目の警告は並行作業中のpytest共有cache書込であり、必須試験の失敗ではない。この判定は自動範囲の Nyquist 合格であり、Phase 04 の正式完了判定ではない。

## Validation Audit 2026-10-28

| Metric | Count |
|---|---:|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## 2026-10-28 再検証ゲート停止（解消前の原本）

Phase 06 の依存契約に従い、全6 PLAN/6 SUMMARY済みの Phase 04 を `aggregate_results` → `verify_phase_goal` の順で再開した。`verify:post` の最初の Nyquist ゲートで、現行ソースの必須試験が失敗したため停止した。過去の validated/compliant の記載は当時の履歴であり、現行の合格根拠ではない。

| 対象 | 現行結果 |
|---|---|
| 状態 | State A（既存 VALIDATION の再監査）、自動ギャップ1件、解消0件 |
| 要件の対応 | 全13タスク/5要件の既存対応を確認。F1 の新試験は UI 待機回復・前景不変・root破棄前停止を追加検証する |
| 現行全件 | **1810 passed / 1 failed / 1 warning / 144.87秒**。単一プロセス、`-x` で初回失敗時停止、終了値1 |
| 失敗 | `tests/test_startup_wake.py::test_native_tcl_getmessage_stall_recovers_with_product_wake[True]`、216行 `assert data["foreground_unchanged"]` が False |
| 影響する検証 | FOCUS-01/02 に関係する「他アプリの入力先を変えない」追加回帰を現行入力で証明できない。製品原因か外部前景変化かは未確定 |
| 証拠 | `04-reverify-20261028/native/run.json`、`pytest-full.txt`、`inputs-before.json`、`inputs-after.json`、`environment.txt` |
| 入力同一性 | 製品・試験・設定113ファイルの前後ハッシュ一致。入力マニフェストSHA256 `2c75948a9b85fae8f1d355bc14a5f97b96e31aeffbf5b288ac3055b98f3a6850` |
| 元ログ保全 | sandbox初回は `Cannot find a usable init.tcl`。root直下の `04-reverify-20261028/run.json` とログを保全。資源アクセス失敗として昇格1回のみ実施 |
| 再実行 | native失敗後の再走なし。許容値変更・skip・除外・製品修正なし |

F1 の過去 `2036 passed` と12件成功の申告は `.planning/debug/resolved/w02-preview-peer-expired.md` と既存生ログにあるが、採取時の全入力manifestがなく現行バイトへの結合を証明できなかったため、今回の合格根拠には採用していない。今回の失敗で過去ログを上書きしない。

Ruff全体checkはサンドボックス外で成功。F1関連7 Pythonの `format --check`、`pagefolio.py` AST、対象 `git diff --check` は成功。ただし全件合格を代替しない。全体 `ruff format .` は既存dirty保護と担当範囲制約により実施せず、再整形しない読み取り検査のみ行った。

後続の security/UI/code-review/regression/独立 verifier は、この停止を越えて完了扱いにしていない。`04-VERIFICATION.md` は更新せず stale を保持する。`phase.complete`、STATE/ROADMAP更新、コミットも未実施。W人手受入の Phase 06 移管、DEP-05、owner_missing、Tcl既知症状、WR-01、未分類edge/禁止事項の未解決状態は維持する。

## 2026-10-22 承認済み受入再計画（現行）

ユーザー承認: 「受入条件を再計画し、別セッション確認など準備できない項目をPhase 6へ移す」。
従来のW全必須passまでPhase 4を停止する条件と移管不可の判断を置き換える。
機能契約・保証範囲・実測・未実施の事実は変更しない。

- Phase 4は自動/Windows subprocess受入、A1〜A5実証、証拠照合と移管追跡を確認する。
- W01〜W12の未実施人手部分はPhase 6のV110-QA-02へ移管し、全件passまでリリースを停止する。
- not-runをpassに変えない。別session準備不能も維持し、アカウント新設や資格情報取得は行わない。
- 自動試験の失敗・未解決の製品欠陥・セキュリティhighは免除しない。
- Phase 4正式完了にはSUMMARY→Progress→validate-phase実走→全件pytest→正式完了→DoD再確認を要する。
- 移管正本: `.planning/phases/06-release-validation/06-UAT-CARRYOVER.md`。5要件の最終実機受入もここで追跡する。

以下の旧停止条件は再計画前の履歴。実施時期は上記の現行条件を適用する。

# Phase 4 — Validation Strategy

検証契約と実行証拠の対応。04-01〜04の実装/自動回帰とA1〜A5の実機ゲートは
各SUMMARYに実測済み。04-05 Task 1の統合/準備結果は本書と04-WINDOWS-UAT.mdに記録する。
**Task 2は承認済み再計画に基づく証拠照合を完了。Phase正式完了は親の検証待ち。**
2026-10-22にvalidate-phaseをインライン実走。Nyquistは現行Phase4の自動検証被覆を示し、Phase6へ移管した実機受入の合格を意味しない。

## Test Infrastructure

| 項目 | 内容 |
|---|---|
| Framework | pytest 9.1.1、既存 .venv |
| Config file | pyproject.toml（編集禁止） |
| Quick run command | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_gsd_dod.py`（起動3ファイルは各作成タスク後） |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q`（単一プロセス全件） |
| 実測時間 | 04-05指定局所140 passed / 0.61秒、cross_entry/startup_acceptance 6 passed / 22.23秒。04-06修正後の単一全件1629 passed / 1 warning / 217.71秒。失敗・ERROR・skipなし。全件120秒目標は超過したが除外しない |

## Sampling Rate

- 各実装タスク後に対象テストを実行する。
- 各コミット前・各 wave 後・verify-work 前に単一プロセス全件 pytest の合格を要求する。
- Python 編集時は `ruff check .` と `ruff format .`、`pagefolio.py` の AST 構文確認を行う。
- 通常pytestは各子bootstrapで設定/プロンプト/pluginsと名前空間を初回読込前に隔離し、同一integrityの実subprocess試験を収集する。UAC・ユーザー切替・手動操作・本番固定名は収集対象外の明示harnessで実施する必須A/W証拠であり、skipや免除に置換しない。
- 時間境界はfake clockで網羅し、実subprocessは短縮timerの注入結果と本番5000/10000msの代表実測を分ける。実時間5秒/10秒/閉鎖後15秒はW07/W09に残す。局所verify60秒未満、自動Windows群60秒以内、全件120秒を目標として実測し、目標超過を理由に無断除外しない。

## Per-Task Verification Map

全コマンドはリポジトリルートで実行する。各PLANのautomated直後のfails_whenを合否条件とする。
実装済み行は対応SUMMARYの実測へ接続した。人手の未実施を自動passと同一にしない。

| Task ID | Wave | Requirement | Secure Behavior / Decision | Test Type | Automated Command | File Exists / 作成依存 | Threat Ref | Status |
|---|---|---|---|---|---|---|---|---|
| 04-01-01 | 1 | 全5件の実行前提 | 未完了と完了の区別、完了義務維持 | 合成回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_gsd_dod.py` | 既存・拡張済み | T-04-04 | pass: 04-01-SUMMARY/04-TRACER-EVIDENCE |
| 04-01-02 | 1 | START-01/02/03, FOCUS-01/02 | 本番E2E、A1〜A5、D-01/05/06/08/10/11/12 | Windows subprocess＋実機 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer` | 作成済み | T-04-01/02/03 | pass: 04-01-SUMMARY、14 passed / 37.97秒 |
| 04-01-03 | 1 | 全5件の方式成立前提 | A3非活性/A4両integrity全資源、本番固定名、A1〜A5確定 | blocking-human＋tracer回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer` | 04-01-02依存 | T-04-01/02/03 | pass: 04-HUMAN-EVIDENCE/04-TRACER-EVIDENCE。新通知leaseのW09/10は別途未実施 |
| 04-02-01 | 2 | START-01/03, FOCUS-01 | D-03/05/06/08、失効・protocol | 純粋状態＋故障注入 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py` | 作成済み | T-04-05/06/08 | pass: 04-02-SUMMARY、52 passed / 0.09秒 |
| 04-02-02 | 2 | START-01/02/03 | D-07、終了と1回引継ぎ | unit＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or simultaneous or takeover"` | 04-01-02依存 | T-04-06/07/08 | pass: 04-02-SUMMARY、14 passed / 42.59秒 |
| 04-03-01 | 3 | FOCUS-01/02 | D-01/02/04/13/14/15/16 | unit＋Tk/Win32境界 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_focus.py` | 作成済み | T-04-09/10/11/12 | pass: 04-03-SUMMARY、27 passed / 0.21秒 |
| 04-03-02 | 3 | FOCUS-02 | doc/Undo/OCR/入力同一性 | 回帰＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "focus_restore or working_state"` | 04-01-02/04-03-01依存 | T-04-09/10 | pass: 04-03-SUMMARY/EVIDENCE、20 passed / 90.17秒。人手評価はW01〜06 |
| 04-04-01 | 4 | START-03, FOCUS-01 | D-09/10/12/14、日英分類・font guard | unit＋i18n | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py` | 作成済み | T-04-13/15 | pass: 04-04-SUMMARY、notice 42 passed / 0.07秒 |
| 04-04-02 | 4 | START-03 | D-10/11/12、10秒・集約 | fake clock＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "notice_dedup or notice_timeout or notice_nonactivate"` | 04-01-02/04-04-01依存 | T-04-14/15 | pass: 04-04-SUMMARY、8 passed / 6.52秒。実時間は04-04-NOTICE-RUNTIME |
| 04-05-01 | 5 | 全5件 | 全経路とW01〜W12準備 | 統合＋全件回帰 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "cross_entry or startup_acceptance"` | 作成済み | T-04-01〜17 | 指定受入pass: 6 passed / 22.23秒、全件結果は04-05-EVIDENCE |
| 04-05-02 | 5 | 全5件 | 自動証拠と全W移管の照合 | 証拠照合＋DoD | `.venv/Scripts/python.exe -m pytest -q tests/test_gsd_dod.py` | 既存・実機表作成済み | T-04-16/17 | pass: 19 passed/0.59秒、全W人手部分は06-UAT-CARRYOVERへnot-runのまま移管 |
| 04-06-01 | 6 | START-03 | backend構築失敗→独立案内、編集画面0、非活性表示 | unit＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice"` | 作成済み | T-04-13/14/15 | pass: 04-06-EVIDENCEと本監査の対象試験。CR-01の旧未捕捉経路を検査 |
| 04-06-02 | 6 | START-02/03 | 部分初期化解放・通知障害・8process集約・再起動 | fault injection＋Windows subprocess | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or initialization_cleanup or notice_deadline"` | 作成済み | T-04-03/13/14/15 | pass: 04-06-EVIDENCEと本監査の対象試験。人手WはPhase6でnot-run |

表中START/FOCUSの略記はそれぞれV110-START/V110-FOCUSを示す。各コミット前の全件pytest、Python変更時のruff check/formatとASTは全タスク共通の追加ゲート。新設Windows試験は対象Windowsでskipを合格にしない。

## Dependency Graph / Scope

| Plan | Needs | Creates | Checkpoint | Wave |
|---|---|---|---|---|
| 04-01 | 出荷済みPhase 3、既存入口/DoD | 正しいDoD、隔離済み実Win32起動tracer、A1〜A5証拠 | 04-01-03明示blocking-human | 1 |
| 04-02 | 04-01本番境界と成立性 | 有界期限・失効・1回引継ぎ | なし | 2 |
| 04-03 | 04-02要求/ACK契約 | 状態/入力/モーダル復帰 | なし | 3 |
| 04-04 | 04-01通知primitiveと04-02/03結果分類 | 3分類の非活性10秒案内/集約 | なし | 4 |
| 04-05 | 04-01〜04実装と試験 | 統合結果・Windows UAT・Phase6移管追跡 | 証拠照合（実機はPhase6） | 5 |
| 04-06 | 04-05完了とCR-01指摘 | 構築前失敗の案内・部分資源解放・実main回帰 | なし | 6 |

04-01は3タスク（DoD前提修正・製品tracer・方式実機確認）、04-02〜06は各2タスク。各タスク5ファイル以下で、共有ファイルと1タスクずつの規約に従い6wave直列。raw見積もり54k/28k/26k/26k/16k/26k、校正factor=1/sample_count=0/confidence=low。既知DoD不整合の前提修正後、最初の製品実装はtracerとし、A1〜A5の実証前に後続へ進まない。

## レビュー反映・証拠の境界

04-REVIEWS.mdのsnapshot SHA-256はEA99835FB98FDB345DFF7FF31D4E37C4F62165056F9D48FA0305A4FD45A063CE。未コミットでありcommit SHAは存在しない。各PLANのRound 1 ledgerに採否を記録した。

| Review | 実行・検証箇所 | 未実施の扱い |
|---|---|---|
| R1 | 04-01-02から各子で_get_base_dir/_get_plugins_dirを隔離、元3ファイルhash/存在比較 | 全waveで共用。cwd変更だけは不合格 |
| R2 | peer照合→owner PIDへの許可委譲→1回前面化、失敗/入力後失効/expired | 04-01/03自動、W06/W12実機を分離 |
| R3 | Settings子閉鎖後、OCR所有messagebox、終了確認中、UI再構築後 | 04-03回帰とW05/W08 |
| R4 | I1〜I4、PendingIO quarantine、WndProc強参照、所有thread/有限cleanup | A1/A3とGC/取消し故障注入 |
| R5 | initializing/ready/closing/released、部分公開、短命reader、旧worker生存、同時claim | 04-02の状態表とW08。死亡未確認のD-07緩和なし |
| R6 | 通常全件pytestと明示A/W harness、実時間代表、UAC/別session | 自動failは停止、人手W not-runはPhase6リリース停止 |

DoDの完了順序は04-05 SUMMARY→Progress自動更新→validate-phase実走→VALIDATION実結果更新→全件pytest→正式Phase完了→DoD再確認。Progress=Complete/Phase[ ]は全PLANのSUMMARY存在・件数・完了日が整合した場合だけ検証待ち中間状態とし、未登録/重複/欠落/真の矛盾は違反を維持する。

## Multi-Source Coverage Audit

| SOURCE | ID | Feature / Constraint | Plan | Status |
|---|---|---|---|---|
| GOAL | Phase 4 | 作業画面を増やさず進行中作業を保って復帰 | 04-01〜05 | COVERED |
| REQ | V110-START-01 | 対応版/配置/入口の同一セッション1画面 | 04-01/02/05 | COVERED |
| REQ | V110-START-02 | 正常/強制/初期化例外後再起動 | 04-01/02/05 | COVERED |
| REQ | V110-START-03 | 判定/通信失敗の識別と有限終了 | 04-02/04/05 | COVERED |
| REQ | V110-FOCUS-01 | 復元・OS許可前面化・拒否通知 | 04-02/03/05 | COVERED |
| REQ | V110-FOCUS-02 | 未保存/Undo/OCR/モーダル維持 | 04-03/05 | COVERED |
| CONTEXT | D-01 | 正常復帰通知を追加せず表示維持 | 04-01/03 | COVERED |
| CONTEXT | D-02 | 最小化前の状態 | 04-03 | COVERED |
| CONTEXT | D-03 | 500ms固定の連打集約 | 04-02 | COVERED |
| CONTEXT | D-04 | 直前の入力先 | 04-03 | COVERED |
| CONTEXT | D-05 | 準備中無表示待機 | 04-01/02 | COVERED |
| CONTEXT | D-06 | 最大5秒 | 04-01/02 | COVERED |
| CONTEXT | D-07 | 確認済み死亡後1回引継ぎ | 04-02 | COVERED |
| CONTEXT | D-08 | 受信側期限失効 | 04-01/02/03 | COVERED |
| CONTEXT | D-09 | 確認済み理由と次の操作 | 04-04 | COVERED |
| CONTEXT | D-10 | 手動閉鎖と10秒自動終了 | 04-04 | COVERED |
| CONTEXT | D-11 | 原因別process間集約・延長なし | 04-01/04 | COVERED |
| CONTEXT | D-12 | 案内の非活性 | 04-01/04 | COVERED |
| CONTEXT | D-13 | 最深modal/入力/選択維持 | 04-03 | COVERED |
| CONTEXT | D-14 | OS拒否はタスクバーだけ | 04-03/04 | COVERED |
| CONTEXT | D-15 | 3回・250ms・2秒以内停止 | 04-03 | COVERED |
| CONTEXT | D-16 | 自動前面化再試行なし | 04-03/04/05 | COVERED |
| RESEARCH | R-01 | Tk前排他・版/配置非依存ID・Local境界 | 04-01/02/05 | COVERED |
| RESEARCH | R-02 | PID/生成時刻/process handleの公開・照合 | 04-01/02 | COVERED |
| RESEARCH | R-03 | 全I/O期限・overlapped・cancel・finite cleanup | 04-01/02/04 | COVERED |
| RESEARCH | R-04 | ID/世代/期限・accepted/terminal/expiredの区別 | 04-01/02 | COVERED |
| RESEARCH | R-05 | Tk mainthread queue・メインスレッド直前失効 | 04-01/02/03 | COVERED |
| RESEARCH | R-06 | 状態保存・grab/native modal・有限点滅 | 04-03 | COVERED |
| RESEARCH | R-07 | 独立通知lease・非活性・10秒・日英 | 04-01/04 | COVERED |
| RESEARCH | R-08 | 最小権限ACL・remote拒否・peer/入力検証 | 04-01/02/05 | COVERED |
| RESEARCH | R-09 | DoD誤判定・合成ツリー負例・PROJECT説明 | 04-01-01 | COVERED |
| RESEARCH | A1〜A5 | IPC/所有者公開/非活性/ACL/共有時計の成立性 | 04-01-02自動＋04-01-03実機停止条件 | COVERED、04-TRACER-EVIDENCEで実証済み。新leaseのW09/10は再受入待ち |
| RESEARCH | R-10 | pure/fault injection/subprocess/実機を分離 | 04-01〜05 | COVERED |
| RESEARCH | R-11 | 新依存なし・pyproject不変・全件ゲート | 全PLAN共通 | COVERED |
| RESEARCH | R-12 | 別権限/別session/Python入口/同時終了 | 04-01/02/05 | COVERED |

除外はCONTEXTのDeferred Ideas、Phase 5設定通知、Phase 6配布EXE最終統合/版同期。研究の候補を採用済み実装と誤認せずA1〜A5で検証する。MISSING項目なしは「計画の被覆」であり実装達成ではない。

## Spec-less Assumptions / Prohibition Recall

SPECなしedge probeは5件すべてunclassified/unresolved、verification/resolution/reasonはnull、probeは「unclassified — review manually」。04-01のE-START-01/02/03・E-FOCUS-01/02に明示し、独立した境界受入を各taskへ計画した。5件を自動resolved/backstopへ変換しない。

禁止事項recallの候補と採用3件は既存どおり保持する。通常品質は行動試験へ、ACL/入力検証はthreat_modelとsecure-phaseへ委譲する。未解決禁止事項はverification=nullをprojectProhibitionsへ渡し、serializerが出力するstatement/status: unresolvedだけを04-01/03/04のmust_haves.prohibitionsへ格納する。check_*なしでflagged-unverifiedを維持し、judgmentという検証済みtierを先付けしない。5 assumptions+3 prohibitionsを保持し、04-05で実機証拠を照合しても未分類probeを自動resolvedにしない。

## Wave 0 Requirements

- [x] 04-01-01: DoDの未完了・完了・未登録・archive・重複/矛盾の合成ケース。
- [x] 04-01-02: tests/test_startup_windows.pyの実subprocess tracerとA1〜A5観測記録。
- [x] 04-01-03: A3/A4と本番固定名の実機確認。通常pytestとは別の必須証拠。
- [x] 04-02-01: tests/test_startup_control.pyの状態遷移・故障注入・時計fixture。
- [x] 04-03-01: tests/test_startup_focus.pyの復帰/入力/モーダルfixture。
- [x] 04-04-01: tests/test_startup_notice.pyの原因/時計/非活性fixture。
- [x] 04-05-01: 04-WINDOWS-UAT.mdのW01〜W12観測表（作成完了、人手合格とは別）。
- [x] 04-06-01/02: constructor前失敗、部分初期化解放、独立通知と両入口を名前付き回帰で検証。
- 追加テストフレームワークは不要。空テストや検証済みメタデータの仮作成で合格にしない。

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| 通常/最大化からの最小化復元、入力先維持 | V110-FOCUS-01/02 | TkとWin32の実表示 | 各状態から再起動し画面状態・入力先を記録 |
| 入れ子モーダル、未保存編集、Undo/Redo、OCR維持 | V110-FOCUS-02 | 実操作とスレッド状態 | 操作中に再起動し内容・選択・進捗を確認 |
| 前面化拒否時の有限点滅 | V110-FOCUS-01 | OS制約 | 他アプリ入力中に起動、拒否後の再前面化がないことを確認 |
| 非活性の失敗案内・10秒・プロセス間集約 | V110-START-03 | ウィンドウアクティブ状態 | 連打・権限差・通信不能で表示数と期限と操作先を記録 |
| 異なる配置・権限・セッションと終了競合 | V110-START-01/02 | OS同期オブジェクトの実挙動 | 対応するPython入口で複数起動・終了注入、別セッションは独立確認 |

上記の未実施人手部分と実EXEの最終配布統合検証はPhase 6の06-UAT-CARRYOVER.mdへ全件移管済み。Phase 4の自動結果と混同しない。

## 04-05 Task 1の実行証拠（2026-10-22）

- 指定局所: **140 passed / 1 warning / 0.61秒**。
- 指定Windows受入: **6 passed / 53 deselected / 1 warning / 22.23秒**。選択6件にskipなし。
- コミット前の単一全件: **1603 passed / 1 warning / 212.88秒**。通常収集にUAC/ユーザー切替/クリック待ち/固定本番claimなし。
- ruff check: **All checks passed!**。ruff format: **1 file reformatted / 99 files left unchanged**。
  整形後のコードで全件を実行。pagefolio.py AST: **AST OK**。git diff --check成功。
- 警告は既存PyMuPDFのByteString DeprecationWarningのみ。
- W07の実時間記録、原本前後一致、閉鎖15秒以上後のHWND消失と残留0は`04-05-EVIDENCE.json`。
- T-04-16: 固定本番名は明示harnessでのみclaim。preflightだけに頼らず一次claimでも競合を拒否し、peerは毎snapshotのPID/生成時刻を照合。
  一次消失/不一致の負例2件で許可委譲なし・新rootなし・既存一次の復帰0を検証。
- T-04-17: W01〜W12/全16決定を`04-WINDOWS-UAT.md`へ対応付け、実証/故障注入/推定/not-runを区別。
- T-04-SC: 依存追加なし、pyproject.toml変更なし。製品CLI/版情報は変更していない。

## Validation Sign-Off

- [x] 全タスクに automated verify または作成依存がある
- [x] 連続3タスクに検証空白がない
- [x] 未作成テストを作成するタスクがある（全対象ファイル作成済み）
- [x] watch modeを使用しない
- [x] フィードバック時間を実測する
- [x] validate-phaseで実検証後にstatusとnyquist_compliantを更新する

**Approval:** 現行Phase4自動検証被覆はvalidated。移管人手受入はnot-run、リリース承認はpending。

承認済み再計画によりTask 2は証拠照合として完了。W11は利用者回答「別アカウントがない／切替できない」により準備不能not-run。
新通知の実クリック/100・150・200% DPI/両integrity作成順、実OS拒否の操作感と入口別の目視も未確認。
04-05-SUMMARY作成→Progress更新後にvalidate-phaseを実走した。Shared-IDは全5SUMMARYの存在により判定可能だが、要件台帳とPhase正式完了は親が行う。

## 2026-10-22 validate-phase実走

State A（既存VALIDATIONの監査）。Nyquist hook有効、5 PLAN/5 SUMMARY、11タスクのverifyと5要件の対応、pytest/pyproject構成を確認。
START-01/02はtracer/lifecycle/takeover/cross_entry、START-03はcontrol/notice/期限失効、FOCUS-01/02はfocus_restore/working_state/modal/OCRへ接続した。
自動検証のMISSING/PARTIALは0、5要件すべてCOVERED。既存試験を実走し204 passed/1 warning/190.22秒、失敗/ERROR/skipなし。
実行コマンド: `.venv/Scripts/python.exe -m pytest -q tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_startup_windows.py tests/test_gsd_dod.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py`。
ギャップなしのためworkflow Step3→6、追加テスト・監査子エージェントは不要。手動項目は全W移管表を維持。
VALIDATION更新後の単一プロセス全件pytestは1603 passed/1 warning/209.19秒、失敗/ERROR/skipなし。120秒目標超過は除外せず保持した。次は親Phase正式完了→DoD再確認。

## Validation Audit 2026-10-21

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

## 2026-10-22 04-06後のvalidate-phase再監査

State Aを再監査した。`verify:post` のnyquist hookは有効。6 PLAN/6 SUMMARY、13タスクとPhase 4の5要件を照合し、04-06のSTART-02/03回帰を上表へ加えた。既存のSTART-01/FOCUS-01/02は04-01〜05の実試験との対応を維持する。04-06後の単一全件1629 passed/1 warning/217.71秒は04-06-EVIDENCE.jsonの実測であり、この監査中には再実行していない。

本監査で `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice or initialization_cleanup or notice_deadline"` を実走し、25 passed、102 deselected、1 warning、9.75秒、終了値0。選択した試験にskipはない。要件対応の自動検証にMISSING/PARTIALは0、Nyquistは現行Phase 4の自動範囲についてcompliantを維持する。人手Wと実EXEは06-UAT-CARRYOVERでnot-runのままであり、本監査の合格に含めない。追加テスト不要のため監査子エージェントは起動せず、同一担当がインライン実施した。

## 正式完了後のDoD確認（2026-10-22）

validate-phase後の単一全件pytestは1629 passed / 1 warning / 228.84秒（終了値0）。その後phase.completeを実行し、要件ID解析警告の5件はrequirements.mark-completeで全10書込面の成功を確認。ROADMAPのPhase行・ProgressとSTATE/state.jsonを同期した。正式完了後の tests/test_gsd_dod.py は19 passed / 1 warning / 0.64秒（終了値0）。W未実施とWR-01の移管は維持する。

追補: 改行整備後のDoD再確認は一時ディレクトリへのPermissionErrorとなったため、同一19件をサンドボックス外で実行し19 passed / 1 warning / 0.16秒（終了値0）。製品テストの失敗ではなく試験用tempへのアクセス制限だった。

## 2026-10-24 Phase 6前提の再監査（Phase 5変更後）

Phase 4検証報告のstale解消（`dd10ce7`、21/21 passed、digest `v3:sha256:5011dcc6...`）に続き、06-04最終build前の依存として実走した。現行HEAD（`dd10ce7`）で `tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_gsd_dod.py tests/test_startup_windows.py` を実行し **238 passed, 1 warning in 276.15s**、失敗/ERROR/skipなし（basetemp `C:\Users\shdwf\AppData\Local\Temp\pf04_validate_1792826444`）。5要件のMISSING/PARTIALは0でNyquist compliantを維持する。追加テストは不要のため監査子エージェントは起動していない。人手Wと実EXEは06-UAT-CARRYOVERでnot-runのままであり、本監査の合格に含めない。

## 2026-11-06 constructor同期修正後の再照合

constructor通知の試験前提をready/release同期へ修正。通知寿命1800msと製品期限は不変。制御RED1件→遅延0/2.1秒×通常/legacyの4件成功、他constructor5件成功。単一全件2401 passed/2 warnings/629.77秒、失敗・error・skip0、Phase04対象301件。171入力前後/回収時不変、全体Ruff/149format/AST成功。根拠: 04-REVALIDATION-CONSTRUCTOR-20261106.md、04-QUALITY-CONSTRUCTOR-20261106.json。既存Nyquist被覆を再利用し、未解除事項は維持する。


## 2026-11-07 G4採取基盤変更後の差分照合

`04-REVALIDATION-G4-20261107.md` と `../04-startup-control/04-QUALITY-G4-20261107.json` を参照。単一全件2481 passed/2 warnings、174入力と追加12入力不変、Ruff/format/AST成功。変更は採取試験基盤と証拠/文書のみで、製品の実装・表示・版番号・固定EXEは不変。G4レビュー7指摘を解消。既存の静的評価と未解除リスクを維持し、正式人手受入・UI capture・出荷承認へ転用しない。独立verificationは後続で現行fingerprintを照合する。
