---
phase: "05"
review_file: 05-REVIEW.md
open: 0
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
    disposition: fixed
---

# Phase 05 コードレビュー対応

**2026-11-06 現行入力の独立再照合:** 既存34ファイルの不変部分を再利用し、共有検証差分はPhase04独立再レビューと厳密な採用判断の回帰へ接続した。Phase05設定/通知/OCR offの製品hashは不変、現行JUnitの関連498件と新全件2361件は成功、170入力前後/現行一致。新規指摘0でCR-01/02/03・WR-01のfixed/open0を維持。Phase04側CR-02とは別IDとして扱う。人手H受入は既存証拠の継承で、Phase06人手/EXE受入と出荷停止は未解除。[05-REVALIDATION-20261106.md](05-REVALIDATION-20261106.md)参照。

**2026-11-05 W05c計測差分の処置確認:** 新規指摘0。CR-01/02/03とWR-01の既存fixed/open0は現行製品不変と設定・通知/OCR off回帰の新JUnit成功で維持する。Phase 04の新しい公式passedも確認。元W05cのNo未取得、Phase 06受入・出荷停止、既知の未確定原因は解決扱いにしない。[05-REVALIDATION-W05C-20261105.md](05-REVALIDATION-W05C-20261105.md)参照。

**2026-11-05 現行再照合:** 新しい単一native全件2254 passedと現行118入力一致を確認し、追加指摘0。CR-01/02/03・WR-01のfixed、open0を維持。旧2232件は現行正本に転用しない。[05-REVALIDATION-20261105.md](05-REVALIDATION-20261105.md)参照。Phase 06受入・出荷停止と既知の原因未確定事項を維持。

**案B・配布文書契約変更後の再照合:** 新規指摘0。製品/CR-03回帰は不変、全2232件の正本と151入力一致を独立確認し、下表4件fixed/open0を維持。Phase06の保証対象外は承認済みW11の2行だけでnot-runを保持し、他108行と品質・安全条件を免除しない。過去全件件数は当時の解消根拠であり、最新は05-REVERIFY-SCOPE-20261028.json。

| ID | Severity | Disposition | 対応 |
|---|---|---|---|
| CR-01 | critical | fixed | 7bbb06c、実Tk save/cancel/wm回帰、利用者H13 pass、独立再レビューで解消確認 |
| CR-02 | critical | fixed | 7bbb06c、可視時間/FIFO/withdraw/iconify回帰、利用者H14 pass、独立再レビューで解消確認 |
| WR-01 | warning | fixed | 2654882、Entryのときだけ入力先verified、非入力/Noneはunverified、独立再レビューで解消確認 |
| CR-03 | critical | fixed | v1.10.2でUIと入口のoff拒否・旧表示除去。独立verifierが差分/呼出順/既存保存ownerを再レビューし追加指摘0。3 provider×4ケースの実メソッド回帰と全件2083件の成功を現行147入力一致で再利用。05-REVIEW.md現行節と05-REVERIFY-20261028.json参照。 |

**2026-10-28 更新:** CR-03を修正済みに変更。以下の2071件と未解決説明は発見時の履歴で、今回の結果は2083 passed/2 warnings/463.98秒・入力不変。W05b・新ビルド・実機受入・出荷停止は維持する。

既存の人手12 pass・全件1789 passは修正前の証拠として保持する。修正後の全件1797 pass/1 warning/266.81秒、利用者追加2 pass、独立再レビューcleanはCR-01/CR-02/WR-01だけの解決根拠である。05-REVIEW.iter1.mdとiter2.mdは各再レビュー前の原本コピー（SHA256一致）。今回のスコープ再照合はdegraded/no-task-commits-sinceで27ファイルへ広がり、未コミットの通知関連変更も確認した。既存全件2071 pass/2 warnings/480.86秒は入力ハッシュ一致のため再利用可能だが、CR-03の解消を意味しない。既知の外部依存・内容不明のプローブ・出荷停止は解除しない。
