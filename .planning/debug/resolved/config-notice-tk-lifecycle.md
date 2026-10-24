---
status: resolved
trigger: "$gsd-debug で Phase 6 --reviews の native 全件2失敗を調査・修正"
created: 2026-10-24
updated: 2026-10-24
---

# 設定通知テストの Tk ライフサイクル

## Symptoms

- expected: 設定通知の実Appテストを含む Windows native 単一プロセス全件が成功する。
- actual: 初回は `1795 passed, 2 failed, 2 warnings in 269.56s`。
- errors: 通知再構築テストで `Unable to load tkdnd library.`、後続の破損設定テストで `image "pyimage9" does not exist`。
- original log: `.planning/phases/06-release-validation/06-reviews-pytest-native.txt`。原本と元 basetemp `C:/Users/shdwf/AppData/Local/Temp/pf06_reviews_native_20261024-055832` は保持。

## Current Focus

hypothesis: 検証済み。通知再構築テストの不要な `TkinterDnD.Tk()` 初期化が間欠的に失敗し、残留rootが後続画像の暗黙masterになった。
test: 故障注入による残留root・画像先不一致の再現と、修正後の `tkdnd` 故障注入、native全件。
expecting: 通知テストがD&Dライブラリ読込失敗から独立し、native全件が成功する。
next_action: 親オーケストレーターが今回のテスト差分・本記録・証拠・開発履歴の今回追記のみを選択stageしてcommitする。

## Evidence

- timestamp: 2026-10-24 05:58 JST; 元ログで最初の失敗は `package require tkdnd`、2件目は `pyimage9`。2件目の根本原因を単独の製品不具合とは扱わない。
- timestamp: 2026-10-24 06:08 JST; 対象2件のみ `2 passed`、設定通知ファイル `143 passed`、全件冒頭3ファイル `174 passed`。間欠性を確認。
- timestamp: 2026-10-24 06:14 JST; `reproduce_orphan_root.py` で `_require` 例外を注入。Tk root が残留し、次のrootのCanvasで暗黙master画像が `pyimage1` 不在、明示master画像は成功。
- timestamp: 2026-10-24 06:17 JST; 修正後に `_require` を常時失敗させる `verify_notice_without_tkdnd.py` を実行。当該通知テスト `1 passed`。
- timestamp: 2026-10-24 06:18 JST; `ruff check .` exit 0、`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"` exit 0（111 files unchanged）、`pagefolio.py` AST OK。Ruff format はsandbox内のアクセス拒否後、正規escalationで完了。
- timestamp: 2026-10-24 06:22 JST; 修正後のfresh外部basetempによるnative単一プロセス全件 `1797 passed, 1 warning in 269.43s`、exit 0。`git diff --check` OK。ログとSHAは `../config-notice-tk-lifecycle-evidence/RESULTS.md`。
- timestamp: 2026-10-24 09:18 JST; `06-01-01` コミット前全件（`06-01-task1-full.txt`）で `tests/test_config_notification.py::TestConfigAcceptance::test_unreadable_permission_recovery_stays_blocked_until_restart`（`tests/config_notice_support.py:129` の `TkinterDnD.Tk()`）が `couldn't read file ".../tkdnd_compat.tcl"` → `RuntimeError: Unable to load tkdnd library.` で失敗し、破棄されない途中生成Tk rootが後続 `test_ocr_engine.py` のスレッドGCで回収されて `RuntimeWarning: the Tcl interpreter is leaked` を誘発。`06-01-STOP.md` にて停止。
- timestamp: 2026-10-24 14:11 JST; `tests/` 全体を検索し、設定通知テスト群に残っていた `TkinterDnD.Tk()` 呼び出し3箇所（`tests/config_notice_support.py:129`、`tests/test_config_notification.py:517`、`tests/test_config_notification.py:1427`）を特定。いずれもファイルD&D契約とは無関係なため `tk.Tk()`＋`_setup_file_drop` 無効化へ統一。`verify_notice_without_tkdnd.py` を `tests/test_config_notification.py` 全件対象へ拡張し、`TkinterDnD._require` 常時失敗下で `143 passed, 1 warning in 9.94s` を確認。
- timestamp: 2026-10-24 14:18 JST; Ruff check / format（113 files unchanged） / AST OK。新規外部 `--basetemp=C:\Users\shdwf\AppData\Local\Temp\pf06_01_task1_full_after_debug_14057535288b47bc9c29ab74fd7b2429` による単一プロセス全件 `1813 passed, 1 warning in 260.31s`、exit 0（ログ: `.planning/phases/06-release-validation/06-01-task1-full-after-debug.txt`）。Tcl interpreter leak 警告も解消。

## Eliminated

- 通知再構築そのものの時間・言語・原本保持ロジックの恒常的失敗: 対象単独、設定通知ファイル全体、故障注入下で成功。
- 製品viewerの複数Tk root対応を今回の主修正とする案: 製品入口 `pagefolio/__main__.py` は単一root参照を保持し、初期化例外時も `finally` で破棄する。失敗連鎖はテスト側の `TkinterDnD.Tk()` 直接生成で発生。

## Resolution

root_cause: 設定通知テスト群（`tests/test_config_notification.py` および `tests/config_notice_support.py`）が無関係なネイティブD&D初期化（`TkinterDnD.Tk()`）に依存し、その間欠失敗で破棄されないTk rootが後続の暗黙master画像不整合やワーカースレッドGCでのTcl interpreter leak警告を引き起こした。初回修正（`98dd70a`）は1テストのみを分離していたため、残る3箇所（`config_notice_support.py:129`、`test_config_notification.py:517, 1427`）で同種失敗が再発した。
fix: `tests/config_notice_support.py` の `IsolatedConfigApp.start()` および `tests/test_config_notification.py` の残り2箇所も `tk.Tk()`＋`_setup_file_drop` 無効化へ統一し、設定通知テスト群全体から `TkinterDnD.Tk()` 直接生成を除去した。通知・隔離Appの実契約は保持。
verification: `TkinterDnD._require` 故障注入下で `tests/test_config_notification.py` 全143件成功、Ruff/AST成功、単一プロセス全件1813件成功（1 warning: PyMuPDF ByteStringのみ）。詳細は証拠ファイル。
files_changed: ["tests/config_notice_support.py", "tests/test_config_notification.py", "開発履歴.md", ".planning/debug/resolved/config-notice-tk-lifecycle.md", ".planning/debug/config-notice-tk-lifecycle-evidence/"]
cycles: 2 investigations + 2 fixes
tdd: false
specialist_review: none
prevention: D&D初期化障害を注入した通知再構築テストの独立性検証と、単一プロセス全件pytestをゲートにする。

## Constraints

外部 `tkdnd` の間欠的な読込失敗がなぜ発生したかは未確定。製品D&D起動全般の修復完了を意味しない。今回の全件成功は DEP-05、owner_missing、通知前景不一致の未解決記録も解除しない。製品コード・版番号は変更していない。既存dirtyはstage対象外。commitは親オーケストレーターが実施する。
