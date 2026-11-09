---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "起動判定基盤の初期化失敗が利用者向け案内を通らず例外終了する"
  - id: WR-01
    severity: warning
    disposition: deferred
    title: "並行負荷で二次終了の15.5秒予算超過を観測"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "否認した採用判断でもW05cを正式passにできる"
open: 0
total: 3
recorded: 2026-10-28
---

## 2026-11-06 constructor通知 dedup 試験の差分処置（現行）

対象 `tests/test_startup_windows.py:471-516,2514-2529,2531-2565,2577-2589` と既存 lease 契約を独立照合し、新規指摘0。7子を通知呼出直前まで準備し、owner表示ready後に解放するので、bootstrap遅延を1800msの表示寿命に算入しない。実呼出tickが元表示期限内、7子すべて coalesced 結果・新規表示0・同deadlineであることを assert する。失敗時は `finally` で生成した子だけを回収する。制御REDは期限後981msに呼び出した子だけ新規表示1回、修正後4条件と周辺5条件は成功。初回全件2397pass/2failを不合格のまま保持し、新単一全件・所有CLI verificationは未完了。製品と元証拠は不変。CR-01/02 fixed、WR-01 deferred、`open: 0`/`total: 3` を維持する。正式G3受入30pass/78not-run/対象外2、`release_allowed=false`、DEP-05・owner_missing・他の未解明事項を解除しない。根拠: `04-REVIEW.md` 現行節、`04-REVALIDATION-CONSTRUCTOR-20261106.md`、`.planning/debug/constructor-notice-dedup-20261106/`。

## 2026-11-06 CR-02修正後の独立再レビュー

CR-02をfixedへ変更。v3 validatorと正式helperはdecisionが「採用」と完全一致する場合だけ通過する。v2/v3・否認/未知値7種・dry-run/書込の28例は実際の拒否エラーと全ファイルbytes不変を検査し、既存肯定例と合わせ107件成功。修正前v3失敗のRED XMLと修正後GREEN XML、04-REVIEW.mdの独立再レビューを照合した。新単一全件 `04-reverify-20261106-cr02/` は本節記録時に実行中で、まだ親検証完了としない。CR-01 fixed/WR-01 deferred、台帳28/80/2、ready_for_retry=false、出荷不可を維持。

## 2026-11-06 独立レビューの追加指摘（修正前の履歴）

CR-02をopenとして登録。v3 validatorと正式記録helperが採用判断の真偽値だけを検査し、「不採用」でもpass化できる。厳密な採用値の比較とv2/v3・dry-run/書込両モードの否認回帰を追加してから再レビューする。CR-01 fixed/WR-01 deferredは維持し、修正完了まで親検証と正式受入を進めない。

## 2026-11-05 W05c計測差分の処置確認

新規指摘0。CR-01は製品の独立通知経路と今回のconstructor失敗回帰成功からfixed、WR-01は並行15609ms/単独15140msの原値を維持してPhase 06 W07bへdeferred。`open: 0`/`total: 2`を変更しない。正式W05c/scriptのNo、実画面受入、原因不明は解決扱いにしない。詳細は`04-REVALIDATION-W05C-20261105.md`。

## 2026-11-05 現行差分の処置確認

現行再監査で新規指摘0。CR-01は既存製品経路と現行のconstructor失敗試験成功によりfixed、WR-01は並行15609ms・単独15140msの原値を保持してPhase06 W07bへdeferred。台帳のopen 0 / total 2を維持する。実走の範囲と生証拠は `04-REVALIDATION-20261105.md`。人手Wや未確定原因を解決扱いにしない。

# Phase 04 コードレビュー処置

## 2026-10-28 品質停止解除後の処置確認（最新）

19ファイルの現行再監査で新規指摘0。現在のREVIEW件数はCritical 0 / Warning 1 / Info 0、下記処置台帳は履歴CR-01を含むtotal 2 / open 0のまま。CR-01 fixedは既存修正と同じ製品bytes・最新全件成功で再確認し、WR-01 deferredは承認済みPhase06のW07b再評価へ維持する。deferredをresolved/passに変えていない。根拠は `04-GATES-CURRENT-20261028.md` / `.json`、最新全件は `.planning/debug/quality-gate-unblock-20261028/full.json`。SECURITYのopen 0とコードレビュー台帳のopen 0は異なる集計であり、人手Wのnot-runは残る。

| Finding | Severity | Disposition | Source |
|---|---|---|---|
| CR-01 | critical | fixed | 04-06修正済み。旧__main__.py:20のbackend_factory OSError注入でexit1/案内なしを再現し、修正後は__main__.py:19-42→startup_notice.py:77-101→Win32NoticeBackend→実native窓に接続。独立再監査25 passed、編集画面0/通知1/前面不変/両入口を確認 (not in the current review) |
| WR-01 | warning | deferred | 2026-10-22承認済み受入再計画、06-UAT-CARRYOVER.mdのW07b上限再評価。15609msと15140msの両方を保持 |

WR-01は既知事項の移管であり修正済み扱いではない。CR-01の旧失敗証拠は04-REVIEW.mdと04-VERIFICATION.mdの再検証履歴に残し、04-06のコードと独立実走で解消を確認した。
