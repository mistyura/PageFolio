---
status: resolved
trigger: "全体整形確認でRuffが内部異常となっている件を対策して"
created: 2026-10-28
updated: 2026-10-28
---

## Symptoms

- expected: 全体の整形確認が内部異常なしで完了し、未整形と実行エラーを区別できる。
- actual: Ruff 0.17.1 の `format . --check` が `Expected a ruff source file` でpanicする。
- errors: `crates/ruff_db/src/diagnostic/mod.rs:528:14`。既存ログは notice-contract-20261028-implementation/ruff-format-check-all.txt。
- timeline: 2026-10-28の既存検証記録で複数回観測。Markdownを整形する挙動も既知。
- reproduction: リポジトリルートで `.venv/Scripts/ruff.exe format . --check`。

## Current Focus

hypothesis: 読取拒否となる過去pytest生成物をルートから走査した際の診断がRuff 0.17.1をpanicさせる。
test: 同一実行ファイルで対象3フォルダーの除外あり/なしを比較。新設定適用後の全体lint/formatと隔離入力5項目を確認。
expecting: 内部異常の対策と既存書式差を分離して報告できる。
next_action: 内部異常対策に続き、利用者の修正指示で書式差も解消。quality-gate-unblock.mdに全体Ruff成功・native局所2件成功・全件2071件成功を記録した。

## Constraints

- 既存dirty・未追跡ファイルを保全する。AGENTS.md・pyproject.tomlは編集しない。
- gsd-debugをインライン実行（スキルのspawn制約に従う）。不要な確認質問や再試行をしない。
- Ruffのpanic・アクセス拒否・書式差分を成功扱いにしない。
- 製品変更を目的としない。Phase 6の実機受入・出荷停止は変更しない。

## Evidence

- 既存requirements.txtと実行ファイルはいずれもruff 0.17.1。
- 過去記録ではPython明示対象113件のformat確認は成功、全履歴の確認は未完了。
- 通常権限へエスカレーションした読取専用の全体formatでも同じpanicを観測。
- 読取拒否の3フォルダーは `pf_0502_atomic_red/`・`pf_0502_flow_green/`・`pf_0502_flow_red/`。直接指定すると通常のioエラー、ルートの走査ではpanicとなる。
- `.planning/debug/ruff-format-source-panic-matrix.json`: 変更前の無除外はexit101/panic、3フォルダー除外でexit1/通常の書式差61件、さらにMarkdown除外でexit1/既存Python書式差1件。最初のPowerShell経由の比較には同条件でも異なる結果があったため、引数と終了コードをPython subprocessで直接保存したこの比較を対照証拠とする。診断panicのRuff内部実装自体は修正していない。
- `.planning/debug/ruff-format-source-panic-after.json`: 設定適用後の全体checkはexit0/警告なし。全体formatはexit1/1 file would be reformatted, 136 files already formatted、stderr空。製品・tests・tools・pluginsのPythonは115 files already formatted/exit0。
- `.planning/debug/ruff-format-source-panic-fixture.json`: 隔離した一時Gitリポジトリで5項目PASS。過去生成物だけの除外、Markdownのcheck/write両モードでの保全、未追跡の製品Python/現行.planning Python/同名のネストしたフォルダーの検出、継承したF821とtestsのS101例外を実Ruffで検証。
- `pagefolio.py`のAST成功、対象のgit diff --check成功。AGENTS.md・pyproject.toml・製品Python・試験Python・requirements.txt・版番号は本作業では編集していない。
- 全件pytest・native接続/9process試験は再実行していない。元デバッグは全件/Phase後続/commit/出荷停止中であり、今回の設定・文書の対策を理由に解除しない。

## 参照した公式仕様

- https://docs.astral.sh/ruff/configuration/ : `.ruff.toml`の優先順位、extendによる継承、Git除外、formatだけへのexclude設定。
- https://docs.astral.sh/ruff/formatter/ : Markdown内のコード整形と除外設定。
- 0.17.2/0.17.3の公式リリースノートに本panicの修正記載は確認できず、未検証の更新で直ったと判断せず現行pinを保持した。

## Resolution

root_cause: 読取拒否となる過去pytest生成物3フォルダーの走査時にRuff 0.17.1の診断がpanicする。Markdownの整形対象化は別の挙動であり、panicとは分けて対処した。
fix: .gitignoreへ該当ルート直下3フォルダーだけを追加。.ruff.tomlでpyproject.tomlのルールを継承し、format.excludeでMarkdownだけを除外。開発ガイド・貢献ガイド・開発履歴を更新。
verification: 全体lint成功/警告なし、全体formatは内部異常なしで既存書式差1件を正常に報告、対象Python115件成功、隔離入力5項目成功、AST/diff確認成功。
remaining: 本件の内部異常と残った書式差による品質停止は解消。書式差解消前原本はquality-gate-unblock-20261028/diag_btn_press.before.py.txtへ保存し、整形前後AST一致。過去の停止記録は経過として保持する。Phase 6の実機受入・出荷は引き続き未承認。
