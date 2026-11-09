---
phase: 04-startup-control
status: automated_passed_pending_verifier
reason: G4採取基盤の追加と共有試験harnessの変更
---

# G4採取基盤変更後の再検証

単一全件 `../04-startup-control/04-reverify-20261107-g4/` は2481 passed / 2 warnings、失敗・error・skip0、705.94秒、exit0。174入力は実行前後/回収時不変、追加12入力も一致、標準エラー空。Ruff check/format/AST成功。集約正本は `../04-startup-control/04-QUALITY-G4-20261107.json`。

constructor同期の直前成功からの変更は台帳/UAT2出力と試験・試験support6ファイル（新規3を含む）。製品・依存・版番号・固定最終EXEは不変。W12aの4指摘、W12bの1指摘、W12cの2指摘は独立再レビューで解消済み。レビュー正本は06-W12A/B/C-REVIEW.md。

- Nyquist: 既存の要件/タスク被覆は再利用し、新しい採取・採用境界の隔離試験を追加。全件成功を人手受入へ転用しない。
- Security: 製品側の権限/namespace/起動/通知/設定処理は不変。試験のproduction owner不在確認、所有PID+64bit FILETIME、自己子だけの回収、原本不変、overlayと配布copy全体、source/helper/実行体/手順のhash、直接回答と別承認をレビュー。既存の未解除項目は解除しない。
- UI: 製品表示変更なし。既存の静的評価を再利用し、新規capture/scoreや実機passは追加しない。
- Code review: G4レビュー7指摘の再レビュー解消済み。既存WR-01 deferredと他の未解除項目を維持。
- Verification: この集約後に独立verifierが所有CLIのfingerprintを更新し、現行freshを照合する。

全件後の追加変更は開発履歴の記録のみで、ソース/試験/実行環境は不変。文書更新前後の入力差分は `06-resume-20261107/post-history-inputs.json` に保存する。Phase06は10 pass / 98 not-run / 対象外2、W12bの7行・W12cの2行は未改変EXE内部API未取得。実機UATは未開始、release_allowed=false。
