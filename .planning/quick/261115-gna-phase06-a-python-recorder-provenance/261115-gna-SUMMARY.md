---
phase: quick-261115-gna
plan: 01
subsystem: phase06-release-validation
tags: [recorder, formal_provenance, python-reuse, uat, revalidation]
requirements: [V110-QA-02]
status: complete
commits: 3
plan_head_before: aceed78b6ad4e40911966674d512c7e7fb6e8e54
plan_head_after: 6c10a0e
key-files:
  created:
    - .planning/phases/06-release-validation/06-05-python-provenance.cjs
    - .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-verify-recorders.cjs
    - .planning/quick/261115-gna-phase06-a-python-recorder-provenance/261115-gna-reverify.cjs
    - .planning/phases/04-startup-control/04-reverify-20261115-pyrec/
    - .planning/phases/04-startup-control/04-QUALITY-PYREC-20261115.json
    - .planning/phases/04-startup-control/04-REVALIDATION-PYREC-20261115.md
    - .planning/phases/05-config-notification/05-REVALIDATION-PYREC-20261115.md
  modified:
    - .planning/phases/06-release-validation/06-05-record-w01-python.cjs
    - .planning/phases/06-release-validation/06-05-record-w02-settings.cjs
    - .planning/phases/06-release-validation/06-05-record-w03-python.cjs
    - .planning/phases/06-release-validation/06-05-record-w04.cjs
    - .planning/phases/06-release-validation/06-05-record-w05b.cjs
    - .planning/phases/06-release-validation/06-05-record-w12c.cjs
    - .planning/phases/04-startup-control/04-VERIFICATION.md
    - .planning/phases/05-config-notification/05-VERIFICATION.md
    - 開発履歴.md
actuals:
  tasks: 3
  commits: 3
---

# Phase quick-261115-gna Plan 01: 区分A Python recorder の来歴照合 Summary

区分A Python 18行の recorder が、旧harness採取を書込前に拒否し、`formal_provenance` を現行 tree と照合し、照合済みの `restored_final_dir` から凍結65入力を読み、台帳の新有効行を一意に選び、CRLF の 06-UAT.md を正しく更新するようになった。Phase04/05 は単一全件 pytest（2488 passed）で再検証し、両方 `passed` に戻した。

`commits: 3` はタスクコミット3件の実測値（`git rev-list --count aceed78..HEAD` を SUMMARY 作成時点で測定）。この SUMMARY 自体の docs コミットは別に1件ある。

## タスクとコミット

| Task | 内容 | コミット |
|------|------|----------|
| 1 | 共通 `06-05-python-provenance.cjs` 新設、W01 recorder 改修、4モード検証スクリプト | 0832241 |
| 2 | W02/W05a・W03・W04・W05b の Python 経路へ同じゲートを展開、W12c に `environment.elevated` を追加 | 0f98e58 |
| 3 | Phase04/05 再検証、開発履歴追記、QUALITY 集約・REVALIDATION 2本、VERIFICATION digest 更新 | 6c10a0e |

## 検証結果（実測）

- e2e-w01（隔離 temp repo）: 正例3件（dry-run、本記録、再実行拒否）と改変13件がすべて期待どおり。改変は個別の理由で拒否され、拒否後に temp repo は無変化。本記録では `python_input_generation`・`supersedes` が不変、`observation_basis` に6欄が入り、UAT は card 以外の CRLF 行が不変で集計行だけ更新。
- real-report: `restored_final_dir`、input_manifest 65件、現行bytes drift 0。
- legacy-reject all: 旧 pass session 18件（W05c 除外）が全件 dry-run で `formal_provenance欠落` として拒否。実台帳・06-UAT.md・06-05-evidence 一覧は無変化。
- static all: 5 recorder が module を使い、final_dir 直読み無し、`--dry-run` 対応。W12c は `elevated` を出力。W05c・W12a・W12b recorder と driver 群は aceed78 と hash 一致。
- Task 2 の pytest（test_w12c_evidence・test_w05c_evidence・test_w05c_runner・test_release_contract）: 163 passed。
- Task 3 の単一全件 pytest（`.\.venv\Scripts\python.exe -m pytest -q -rA -p no:cacheprovider --basetemp=…pf04-04-reverify-20261115-pyrec`）: **2488 passed / 2 warnings、失敗0・ERROR0・クラッシュなし**、735.61秒、exit 0、標準エラー空。187入力は実行前後で不変（changed・missing とも空）。Ruff check・format --check（503 files）・AST 成功。症状①（TclError）・②（STATUS_BREAKPOINT）とも観測なし。再実行は行っていない（全件は1回のみ）。
- 開発履歴追記後の再hashは `post-history-inputs.json` に保存し、全件後の差分が `開発履歴.md` の1件だけであることを確認。
- `git diff aceed78 -- '*.py' pyproject.toml` は差分なし。

## Phase04/05 の verification.status

両方 `passed`（所有CLI `verification.status` で確認）。digest 更新の3条件（全件成功、inputs の changed・missing が空、変更ファイルと covered_files の共通部分が 04 では w12c のみ・05 では w12c と開発履歴のみ）をすべて満たしたため、独立 verifier ではなく executor が機械的に再計算して更新した。

- 04: `v4:sha256:8490d00c…` → `v4:sha256:5f0c02af…`
- 05: `v4:sha256:0c8cddf8…` → `v4:sha256:d97bcecc…`

covered_files・score・truth 本文は変更していない。直前の current_execution は `prior_execution_20261109_w12b_pid`（historical: true）として残した。

## 逸脱・環境事項

- **venv の欠落と再作成（利用者承認済み）**: clone のやり直しで `.venv` が消失していたため、Task 2 の pytest と Task 3 は一時停止した。利用者が 2026-11-15 に requirements.txt の固定版で venv を再作成（Python 3.15.2 / PyMuPDF 1.28.2 / Pillow 13.0.0 / Tk 9.0、前回と同版）。再検証文書・QUALITY JSON・environment.txt に記載。`.planning/tmp/`、`pagefolio_settings.json`、`.env` も無かったが、全件の結果には影響しなかった。
- 実装は計画どおり。共通 module には計画記載の関数に加え、補助関数（`applyUatPass`・`provenanceRaw`・`provenanceBasis`・`walk`・`sha`）を追加で公開した。
- 再検証の入力集合は、前回の186件に共通 provenance module を加えた187件。

## 残課題（本 quick の範囲外）

- W05c script/module の2行（`06-05-record-w05c-python.cjs`）は利用者決定どおり未改修（別 quick。tests/test_w05c_*.py の限定承認が要り、Phase04/05 の再検証がもう一度必要）。同 recorder は LF 前提の marker のため、現行 CRLF の 06-UAT.md では card missing で停止する。
- 独立コードレビューは未実施。W02〜W05b recorder の正例は実データでしか確かめられないので、最初の実 session でまず `--dry-run` を通すこと。
- 区分A の実機採取は、更新後の 04-VERIFICATION.md を前提に開始できる（`formal_provenance.phase04.report_sha256` が採取開始時の hash を固定するため）。

## Self-Check: PASSED

- 作成ファイル（06-05-python-provenance.cjs、261115-gna-verify-recorders.cjs、261115-gna-reverify.cjs、04-reverify-20261115-pyrec/、04-QUALITY-PYREC-20261115.json、REVALIDATION 2本）が存在。
- コミット 0832241・0f98e58・6c10a0e が HEAD の祖先として存在。
