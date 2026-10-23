---
phase: "05"
review_file: 05-REVIEW.md
open: 2
total: 2
findings:
  - id: CR-01
    severity: critical
    title: 内側ショートカット画面の終了で外側設定画面の通知保護が失われる
    disposition: open
  - id: CR-02
    severity: critical
    title: 最小化中にも設定通知の期限が進み未確認イベントを破棄する
    disposition: open
---

# Phase 05 コードレビュー対応

| ID | Severity | Disposition | 対応 |
|---|---|---|---|
| CR-01 | critical | open | 外側Settingsへのgrab復元を実Tk回帰付きで修正する |
| CR-02 | critical | open | 最小化/非表示中に設定通知を非消化で中断し残時間を保つ |

既存の人手12 pass・全件1789 passには上記2境界の検証を含めない。修正後の検証証拠とコミットを記録してから解決扱いにする。
