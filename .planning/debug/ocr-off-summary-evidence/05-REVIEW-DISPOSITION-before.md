---
phase: "05"
review_file: 05-REVIEW.md
open: 1
total: 4
findings:
  - id: CR-01
    severity: critical
    title: 内側ショートカット画面の終了で外側設定画面の通知保護が失われる
    disposition: fixed
  - id: CR-02
    severity: critical
    title: 最小化中にも設定通知の期限が進み未確認イベントを破棄する
    disposition: fixed
  - id: WR-01
    severity: warning
    title: 入力欄以外のフォーカスをverifiedと記録できる
    disposition: fixed
  - id: CR-03
    severity: critical
    title: OCRを無効にしても旧プロバイダでサマリを送信できる
    disposition: open
---

# Phase 05 コードレビュー対応

| ID | Severity | Disposition | 対応 |
|---|---|---|---|
| CR-01 | critical | fixed | 7bbb06c、実Tk save/cancel/wm回帰、利用者H13 pass、独立再レビューで解消確認 |
| CR-02 | critical | fixed | 7bbb06c、可視時間/FIFO/withdraw/iconify回帰、利用者H14 pass、独立再レビューで解消確認 |
| WR-01 | warning | fixed | 2654882、Entryのときだけ入力先verified、非入力/Noneはunverified、独立再レビューで解消確認 |
| CR-03 | critical | open | 現行 `ocr_dialog.py:1193-1201, 813-825, 2218-2253, 2375-2379`。OCR完了後の `off` 切替で旧providerの能力によりサマリが有効化され、旧ローカルproviderなら本文を送信できる。実メソッドのheadless確認済み。製品修正・回帰・再レビュー待ち。 |

既存の人手12 pass・全件1789 passは修正前の証拠として保持する。修正後の全件1797 pass/1 warning/266.81秒、利用者追加2 pass、独立再レビューcleanはCR-01/CR-02/WR-01だけの解決根拠である。05-REVIEW.iter1.mdとiter2.mdは各再レビュー前の原本コピー（SHA256一致）。今回のスコープ再照合はdegraded/no-task-commits-sinceで27ファイルへ広がり、未コミットの通知関連変更も確認した。既存全件2071 pass/2 warnings/480.86秒は入力ハッシュ一致のため再利用可能だが、CR-03の解消を意味しない。既知の外部依存・内容不明のプローブ・出荷停止は解除しない。
