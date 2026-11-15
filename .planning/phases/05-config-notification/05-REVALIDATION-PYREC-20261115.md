---
phase: 05-config-notification
status: automated_passed_pending_verifier
reason: 区分A Python recorder の来歴照合改修と W12c recorder の elevated 出力追加（採取helperの変更のみ、製品・試験は不変）
---

# Python recorder 改修後の再検証

単一全件 `../04-startup-control/04-reverify-20261115-pyrec/` は2488 passed / 2 warnings、失敗・error・skip 0、735.61秒、exit0。187入力は実行前後で不変（changed・missing とも空）、標準エラー空。Ruff check / format --check / AST 成功。集約正本は `../04-startup-control/04-QUALITY-PYREC-20261115.json`。

環境: 2026-11-15 に venv を再作成した（git clone をやり直したため消失）。Python 3.15.2、PyMuPDF 1.28.2、Pillow 13.0.0、Tk 9.0 で前回と同版。git 管理外の `.planning/tmp/` も clone のやり直しで消えているが、全件の結果には影響しなかった。

## 変更内容（W12b PID 再検証からの差分）

Phase06 区分A の Python 再採取用 recorder の改修（共通 `06-05-python-provenance.cjs` の新設、W01/W02/W03/W04/W05b recorder への来歴照合・restored_final_dir・新有効行選択・CRLF 対応・dry-run の展開）と、W12c recorder の `environment.elevated` 出力追加。詳細は `../04-startup-control/04-REVALIDATION-PYREC-20261115.md`。`.py` は変更していない。全件後の追加変更は `開発履歴.md` の1項目の追記のみで、更新前後の入力差分は `../04-startup-control/04-reverify-20261115-pyrec/post-history-inputs.json` に保存した（差分は `開発履歴.md` だけ）。

W05c script/module の2行（`06-05-record-w05c-python.cjs`）は利用者判断により本改修の対象外で、未改修。製品コード・依存・版番号・固定最終EXEは不変。

- Nyquist: 既存の要件/タスク被覆を再利用。recorder の照合境界は隔離 temp repo の正例3件・改変13件と、旧 pass session 18件の dry-run 拒否で確認。全件成功を人手受入へ転用しない。
- Security: 製品側の権限/namespace/起動/通知/設定処理は不変。recorder の照合は旧条件より緩めていない。残存リスクは Phase04 側の文書に記載（driver の `uat_row.py` が formal_provenance に含まれない点、W12c の elevated が `is_admin` 欠落時に未出力な点）。既存の未解除項目は解除しない。
- UI: 製品表示変更なし。
- Code review: 独立コードレビューは未実施（quick の executor による機械的な再検証）。既存 WR-01 deferred と他の未解除項目を維持。
- Verification: 独立 verifier ではなく quick の executor が、所有 CLI の fingerprint で `05-VERIFICATION.md` の covered_digest を機械的に再計算して更新した。更新条件（全件成功、入力の changed・missing が空、変更ファイルと covered_files の共通部分が w12c recorder と `開発履歴.md` だけ）をすべて満たした場合だけ実施した。

Phase06 は23 pass / 85 not-run / W11対象外2 not-run、release_allowed=false（台帳・06-UAT.md は未変更）。区分A の実機採取は、更新後の `04-VERIFICATION.md` を前提に始める。W05c の2行は別 quick で扱う。
