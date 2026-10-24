---
phase: 06-release-validation
plan: "01"
subsystem: release-build
tags: [pyinstaller, onedir, release-cli, sha256, gitattributes, tdd]

requires:
  - phase: 05-config-notification
    provides: 外部プロンプト/設定の保護名(constants.py)とApply書戻し仕様
provides:
  - tools/build_release.py: 安全確認から公開までの単一CLI(初回・管理済み再ビルド共通)
  - distribution/samples/ 2正本(元dist/PageFolioのサンプルとbyte一致)と distribution/はじめに.md
  - tests/test_release_build.py: CLI経路・境界・障害注入の70件(実PyInstallerは起動しない)
  - .gitattributes: 旧2サンプルと新正本2ファイルだけ-text
affects: [06-02, 06-03, 06-04, 06-05, 06-06]

plan_head_before: 07244dce67b774a59f7831cbbc27c7485fbf8cdd
plan_head_after: db7ba213130cf6e63dc13c69929b001ce58b002f

actuals:
  tokens: 12772
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "所有run(.release-work/<run-id>)内でのみ私有PyInstallerを実行し、検証後に版付きfinalへ昇格"
    - "同梱reportと外部run reportの双方で全名/bytes/dirを照合する管理済み配布判定"
    - "同一最終先lockをxbで排他取得し、PID+生成時刻+run-idを記録(奪わない)"

key-files:
  created:
    - tools/build_release.py
    - tests/test_release_build.py
    - distribution/samples/ocr_custom_prompt_sample.md
    - distribution/samples/ocr_summary_prompt_sample.md
    - distribution/はじめに.md
    - .gitattributes
  modified: []

key-decisions:
  - "管理済み再ビルドの判定は同梱release-report.jsonのrun_idから output/.release-work/<run_id>/report.json を引き、embedded_report_sha256・distribution_manifest・directoriesの三者一致を要求する(絶対パスの保存値は信用しない)"
  - "成功reportは複製(done)を書き込み成功した後でのみreportへ反映し、書込失敗が成功段階(complete)へ落ちないようにした"
  - "要件V110-DIST-01〜03/QA-01は本計画だけでは達成と言えない(実機受入・06-04の最終build・phase全体ゲートが未了)ため mark-complete しなかった"

patterns-established:
  - "拒否は副作用前(lock・work・history作成前)に行い、builder呼出0・元bytes不変を実ディスクfixtureでassertする"
  - "障害注入はPath.rename/shutil.copyfile/_write_jsonのmonkeypatchで公開・復帰・照合・report書込の各境界を再現する"

requirements-completed: []

duration: 1h(再開分のみ。停止前の実装・調査は含まない)
completed: 2026-10-24
status: complete
---

# Phase 6 Plan 01: サンプル配布と安全な配布CLI Summary

**正本2サンプルをEXE隣へ同梱・SHA-256照合し、保護名/未知ファイル/リンク/同時run/各種故障でも利用者ファイルと旧配布を失わない単一配布CLI(tools/build_release.py)を、実onedirの初回build・管理済み再buildまで実測して追加した。**

## Performance

- **再開後の実行:** Task 1 の実CLI tracer・commit → Task 2 のRED→GREEN・全件ゲート・commit
- **Tasks:** 2/2
- **Commits:** 2(measured: `07244dc..db7ba21`)

## Accomplishments

- `distribution/samples/` に元の `dist/PageFolio/` の2サンプルをcopyfileで保存。元との全文bytes一致を `cmp` と試験で確認(元は未変更)。
- `tools/build_release.py`: AST版/保護3名、出力境界、私有run、固定argv(絶対パス)、同梱SHA-256、公開直前再検査、公開後照合、失敗物保持を実装。入口は `.venv/Scripts/python.exe tools/build_release.py --output-root <dir>`(既定 `dist`、兄弟の旧 `dist/PageFolio` は触れない)。
- Task 2: 空先または前回の検証済みmanifestと完全一致する管理済み配布だけを再ビルド対象にし、旧treeを `.release-history/<run-id>/` へ保持。3保護名(通常ファイル/同名dir/broken link、大小文字非依存)、未知/改変/欠落、junction/reparse、`.release-work`/`.release-history` が通常ファイル、既存lockは、いずれもbuilder呼出0・副作用0で停止。
- build/copy/hash/report書込/履歴移動/昇格/復帰/公開後照合/中断の各故障でnonzeroと失敗物(INCOMPLETE・build.log・report.json)を保持。復帰失敗は `rollback_error` として元失敗と共に記録。
- `.gitattributes` を新設し、旧2サンプルと新正本2ファイルだけを `-text`。`core.autocrlf=true` の隔離Git fixtureで blob と checkout 後のbytesが一致することを試験。
- `tests/test_release_build.py` は 16 → 70 件(TestReleaseTracer / TestPreflight / TestRebuild / TestFailureRetention / TestCommandLine / TestGitAttributes)。pytestから実PyInstallerは起動しない。

## Task Commits

1. **Task 06-01-01(tracer):** `509e05c` feat(06-01): 正本サンプルから検証済みonedirを作る配布CLIを追加
2. **Task 06-01-02:** `db7ba21` feat(06-01): 再ビルド・競合・公開失敗でも利用者ファイルと旧成果物を保持

(RED は単独commitせず、`06-01-task1-red.*` / `06-01-task2-red.*` に証拠のみ保存。)

## 検証結果(実測)

| 項目 | 結果 |
| --- | --- |
| Task 1 局所 | `tests/test_release_build.py::TestReleaseTracer` 16 passed |
| Task 1 実CLI(repo外GUID output-root) | exit 0 / 59秒(初回)。`PageFolio-v1.9.1` に EXE・`_internal`・2サンプル・はじめに.md・docs/CONFIGURATION.md・release-report.json。2サンプルは正本・元distとcmp一致、`artifact_role=technical-tracer` / `release_allowed=false` / `manual_uat=not-run`。出力先: `C:\Users\shdwf\AppData\Local\Temp\pf06_tracer_acce06df0c694f10be4a1ed80f690793` |
| Task 2 実CLI管理済み再build(同output-root) | exit 0 / 32秒。旧treeが `.release-history/2db21a6b…` へ保持された。ログ `06-01-task2-rebuild-cli.txt` |
| Task 2 RED | 16 failed / 54 passed(`06-01-task2-red.txt` / `.xml`)。振る舞い未実装による失敗 |
| Task 2 GREEN | `tests/test_release_build.py` 70 passed |
| Ruff check → format → 再check → AST | 全合格(113 files)。LF正規化後にも再実行し合格 |
| Task 1 commit前 全件(単一プロセス・native) | `06-01-task1-full-after-debug.txt`: 1813 passed, 1 warning(commit 07244dc の調査修正後。以降ソースに更新なしをmtimeで確認して同一性を再利用) |
| Task 2 commit前 全件(単一プロセス・native) | **1867 passed, 1 warning in 361.34s (0:06:01) / exit 0**。basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_01_task2_full_267e564b25ba42ff99e974f07324323e`、ログ `06-01-task2-full.txt`。-k/--ignore/skip による除外なし |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 編集スクリプトによるCRLF混入**
- **Found during:** Task 2 commit直後(`git show --stat` の差分行数が異常に大きかった)
- **Issue:** Windows上の `Path.read_text/write_text` により tools/build_release.py と tests/test_release_build.py がCRLFへ変換されていた(プロジェクトのPythonはLF)。
- **Fix:** 2ファイルをLFへ戻し、Ruff check/format/AST と `tests/test_release_build.py` 70 passed を再実行して、未pushの自コミット `e457838` を `db7ba21` へamend。
- **補足:** 全件1867 passedはCRLF版での実行。LF化は改行のみの変更(Python構文上同一)で、局所70件と品質ゲートは再実行済み。全件ゲートの再実行はしていない。
- **Commit:** db7ba21

**2. [Rule 1 - Bug] 試験の誤判定**
- 「private」の部分一致が `clean_private_directories` キーに反応したため、固有文字列(`private user content` / `private inner`)の検査に直した。

**3. [Rule 3 - Blocking] Ruff S603/S607**
- 試験内のsubprocess呼出に `# noqa: S603` を付け、gitは `shutil.which` で解決。長い文字列行も分割。

### 計画外の扱い

- 実CLIの管理済み再buildをTask 2の追加検証として1回実施(計画のverifyはpytestのみ)。最終版の2回build契約は06-04のもので、本再buildは技術tracerであり正式リリースではない。

## Authentication Gates

なし。

## Issues Encountered

- 再開前にTask 1のnative全件でTcl同種の失敗が出て停止していた(`06-01-STOP.md`)。親のdebug(commit 07244dc)で解消済み。今回の2回の全件ではTcl失敗・ERROR・クラッシュなし。症状①(TclError)は再発し得る環境症状として CLAUDE.md に記載があり、今後も非再現を前提にしない。

## Known Stubs

なし。

## Threat Flags

なし(新規ネットワーク/認証経路なし。ファイル/プロセス境界は計画の threat_model T-06-01〜03 の範囲)。

## 既知の制限・次への申し送り

- 本計画の合格は**実装/技術tracer合格**であり、実機受入・出荷承認ではない。生成物は `technical-tracer` / `release_allowed=false`。
- 同梱 `はじめに.md` は初期版(説明の完成は06-02)。古いlockの回復手順(所有者確認)も06-02で案内する。
- 管理済み配布にユーザーが `ocr_custom_prompt.md` 等を置くと再ビルドは停止する(設計どおり。完全copy上で受入し、配布元は直接起動しない)。
- 追加の自動削除/保持上限は実装していない(D-11)。履歴・失敗runの容量管理は手動。
- 既存dirty(`06-01-dirty-baseline.json` の8件)は戻さず、stage/commitもしていない。基準後に `.planning/STATE.md` がオーケストレータ更新で変化している。

## Self-Check: PASSED

- 作成ファイル: tools/build_release.py, tests/test_release_build.py, distribution/samples/ 2ファイル, distribution/はじめに.md, .gitattributes — すべて存在
- コミット: 509e05c, db7ba21 — HEAD の祖先として存在
