---
phase: 04-startup-control
status: automated_passed_pending_verifier
reason: 区分A Python recorder の来歴照合改修と W12c recorder の elevated 出力追加（採取helperの変更のみ、製品・試験は不変）
---

# Python recorder 改修後の再検証

単一全件 `../04-startup-control/04-reverify-20261115-pyrec/` は2488 passed / 2 warnings、失敗・error・skip 0、735.61秒、exit0。直近の再検証（W12b PID、186入力）に共通 provenance module を加えた187入力は実行前後で不変（changed・missing とも空）、標準エラー空。Ruff check / format --check（503 files）/ AST 成功。集約正本は `../04-startup-control/04-QUALITY-PYREC-20261115.json`。

環境: 2026-11-15 に venv を再作成した（git clone をやり直したため消失）。Python 3.15.2、PyMuPDF 1.28.2、Pillow 13.0.0、Tk 9.0 で前回と同版。clone のやり直しで git 管理外の `.planning/tmp/` も消えているが、全件の結果には影響しなかった（件数は前回と同じ2488）。

## 変更内容（W12b PID 再検証からの差分）

quick 261115-gna（`../../quick/261115-gna-phase06-a-python-recorder-provenance/`）による Phase06 区分A（Python 再採取）の正式記録 recorder の改修。`.py` は一切変更していない。

- 新設 `06-05-python-provenance.cjs`: 旧 harness 採取（`formal_provenance` なし）を書込前に拒否。`formal_provenance` の source_inputs・元 plugins・Phase04（report sha256・covered_digest・所有 CLI の fresh）・`provenance-before-stop.json` の matched を現行 tree と照合。消失した `final_dir` ではなく、tree hash・EXE hash・rebuild run_id を照合した `restored_final_dir` の release-report.json から凍結65入力を読む。台帳の新有効行（SUPERSESSION リンクと一致する行）を一意に選び、`python_input_generation` と `supersedes` は上書きせず、観測時の入力世代は `observation_basis.observed_python_input` に別欄で残す。CRLF を含む現行 06-UAT.md の card を特定（従来の recorder は LF 前提で20行とも card missing だった）。
- W01・W02/W05a・W03・W04・W05b の Python 経路に同じゲートを適用（production-exe 経路には適用しない）。`--dry-run` を追加（W05b は既存挙動を維持）。
- `06-05-record-w12c.cjs`: 新規記録が `environment.elevated`（`manifest.environment.is_admin`）を出力する（1行）。

W05c script/module の2行（`06-05-record-w05c-python.cjs`）は利用者判断により本改修の対象外で、recorder・試験とも未変更。製品コード・依存・版番号・固定最終EXE・駆動driver・`tests/` は不変。

- Nyquist: 既存の要件/タスク被覆を再利用。recorder の新しい照合境界は隔離 temp repo で、正例3件と改変13件（拒否理由を個別に確認）、実 repo の旧 pass session 18件の dry-run 拒否、凍結65入力の drift 0 で確認した。全件成功を人手受入へ転用しない。
- Security: 製品側の権限/namespace/起動/通知/設定処理は不変。recorder の照合は旧条件より緩めていない（既存の判定条件は変更せず、来歴・配布tree・行選択の照合を前段に追加）。残存リスク: `06-05-drivers/uat_row.py` は harness の formal_provenance に含まれない（`.py` を変更できないため。aceed78 との hash 一致と入力集合で不変を確認）。W12c の elevated は `is_admin` 欠落時に出力されない（変更禁止の試験 fixture と両立させるため。pass 行の欠落は release_uat_support の構造監査が検出する）。
- UI: 製品表示変更なし。
- Code review: 独立コードレビューは未実施（quick の executor による機械的な再検証）。
- Verification: 独立 verifier ではなく quick の executor が、所有 CLI の fingerprint で `04-VERIFICATION.md` の covered_digest を機械的に再計算して更新した。更新条件（全件成功、入力の changed・missing が空、変更ファイルと covered_files の共通部分が想定どおり＝本 phase では w12c recorder のみ）をすべて満たした場合だけ実施した。

## 台帳状態と次の手順

Phase06 は23 pass / 85 not-run / W11対象外2 not-run、release_allowed=false（台帳・06-UAT.md は未変更）。区分A の実機採取は、この更新後の `04-VERIFICATION.md` を前提に始める必要がある（`formal_provenance.phase04.report_sha256` は採取開始時の hash を固定するため、更新前に始めた採取は記録できない）。W02〜W05b の recorder は実データでの正例が未確認なので、最初の実 session でまず `--dry-run` を通すこと。W05c の2行は別 quick で扱う（Phase04/05 の再検証がもう一度必要になる）。
