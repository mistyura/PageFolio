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

## Eliminated

- 通知再構築そのものの時間・言語・原本保持ロジックの恒常的失敗: 対象単独、設定通知ファイル全体、故障注入下で成功。
- 製品viewerの複数Tk root対応を今回の主修正とする案: 製品入口 `pagefolio/__main__.py` は単一root参照を保持し、初期化例外時も `finally` で破棄する。失敗連鎖はテスト側の `TkinterDnD.Tk()` 直接生成で発生。

## Resolution

root_cause: 通知再構築テストが無関係なネイティブD&D初期化に依存し、その間欠失敗で破棄されないTk default rootが後続の暗黙master画像を別interpreterへ作成した。
fix: `tests/test_config_notification.py` の当該テストのみ `tk.Tk()` を使用し、同テストのファイルD&D登録を無効化した。通知の実App契約は保持。
verification: 故障注入下の対象テスト成功、Ruff/AST成功、native全件1797件成功。詳細は証拠ファイル。
files_changed: ["tests/test_config_notification.py", "開発履歴.md", ".planning/debug/resolved/config-notice-tk-lifecycle.md", ".planning/debug/config-notice-tk-lifecycle-evidence/"]
cycles: 1 investigation + 1 fix
tdd: false
specialist_review: none
prevention: D&D初期化障害を注入した通知再構築テストの独立性検証と、単一プロセス全件pytestをゲートにする。

## Constraints

外部 `tkdnd` の間欠的な読込失敗がなぜ発生したかは未確定。製品D&D起動全般の修復完了を意味しない。今回の全件成功は DEP-05、owner_missing、通知前景不一致の未解決記録も解除しない。製品コード・版番号は変更していない。既存dirtyはstage対象外。commitは親オーケストレーターが実施する。
