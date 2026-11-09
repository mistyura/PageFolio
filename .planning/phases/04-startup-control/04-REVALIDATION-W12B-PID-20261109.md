---
phase: 04-startup-control
status: automated_passed_pending_verifier
reason: W12b Python二次のvenv launcher PID不一致修正（試験harness・採取helper・証拠試験の変更）
---

# W12b PID照合修正後の再検証

単一全件 `../04-startup-control/04-reverify-20261109-w12b-pid/` は2488 passed / 2 warnings、失敗・error・skip 0、732.59秒、exit0。G4再検証と同じ174入力＋追加12入力（計186）は実行前後で不変、集約時の再hashでも差分なし、標準エラー空。Ruff check / format --check / AST成功。集約正本は `../04-startup-control/04-QUALITY-W12B-PID-20261109.json`。

format --check はG4時の「発見ファイルを引数列挙」方式だと503件でWindowsのコマンド長上限を超え起動できない（exit=null）ため、同じ探索対象を `.` で指定した。発見集合は `ruff-discovery.json` に保存。

## 変更内容（G4成功からの差分）

原因調査は `../../debug/w12b-pid-mismatch.md`。Windows venvの `.venv/Scripts/python.exe` はlauncherで、driverが記録する `Popen.pid` はlauncher、二次resource-auditの `pid` は実インタプリタの `os.getpid()` のため、helperの `audit.pid===peer.pid` が実採取で必ず不一致になっていた（run cd223f3b…で 2972 vs 24248）。

- `tests/test_startup_windows.py`: 二次Backendのauditに `parent_pid: os.getppid()` を追加。
- `06-05-record-w12b.cjs`: Python二次は `peer.pid` と `audit.pid` が正の整数かつownerと別、machine埋込auditとresource-audit.jsonの完全一致、かつ `audit.pid===peer.pid`（直接起動）または `audit.parent_pid===peer.pid`（launcher経由）を要求。台帳には `audit_pid`/`audit_parent_pid` も記録。
- `tests/test_w12b_evidence.py`: fixtureをlauncher形へ変更。直接起動の受理試験、parent不一致・欠落、owner PID取り違え、peer.pid欠落、owner PIDを起動元とする偽装、埋込audit不一致の拒否試験を追加。

製品コード・依存・版番号・固定最終EXE・driverは不変。

- Nyquist: 既存の要件/タスク被覆を再利用し、新しい照合境界の受理1件・拒否6件を追加。全件成功を人手受入へ転用しない。
- Security: 製品側の権限/namespace/起動/通知/設定処理は不変。照合は旧条件より緩めていない（旧条件で暗黙だったpeer.pidの整数・非owner制約を明示化し、埋込audit一致を追加）。Popenがハンドルを保持しlauncherは子の終了まで待つため、launcher PIDの再利用で別プロセスを親と誤認する余地はない。
- UI: 製品表示変更なし。
- Code review: 独立レビュー（`../06-release-validation/06-W12B-REVIEW.md` CR-02節）のBLOCKER1・WARNING2・INFO1を反映した後に本全件を実行。
- Verification: この集約後に独立verifierが所有CLIのfingerprintを更新し、現行freshを照合する。

保存済みrun `release-uat-cd223f3bcaf34f8f84bbe79f17b28129` は入力hashが変わったため正式記録に使えず保持のみ。Phase06は19 pass / 89 not-run / 対象外2、release_allowed=false。
