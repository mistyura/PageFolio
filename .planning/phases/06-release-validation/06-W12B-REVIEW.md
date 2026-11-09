---
phase: 06-release-validation
reviewed: 2026-11-06T16:17:56Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - .planning/phases/06-release-validation/06-05-w12b-driver.py
  - .planning/phases/06-release-validation/06-05-record-w12b.cjs
  - .planning/phases/06-release-validation/06-W12B-COLLECTION.md
  - tests/test_w12b_evidence.py
  - tests/test_startup_windows.py
  - tests/release_uat_support.py
  - tests/test_release_uat_support.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# W12b 混在入口の独立コードレビュー

## Summary

W12b由来の7ファイルを標準深度で照合した。新driverは世代5の最終EXE treeを固定保持先で検証し、tracer行では2026-11-07新runのsource manifest・両report・64入力・保持treeを照合する（`06-05-w12b-driver.py:82-143,190-207`）。旧run/hashの再現とは扱わない。一次Pythonは既存owner不在を読取で確認してから固定namespaceの実script/module入口へ進み（`tests/test_startup_windows.py:3382-3399,3442-3453`）、一次EXEは既存 `release_uat_support.prepare/start` の完全copyを起動する。二次後の外部foregroundは利用者入力を求める前に採取する（driver`:375-395`）。Python二次の真のAPI戻り値はresource-auditから記録し、未改変EXE二次の7行は `unsupported` として正式helperが拒否する（driver`:311-375`、helper`:65-67,204-217`）。利用者原文・回収後の別回答・有限肯定形、現行source集合と採用helper自身、Phase04 fresh、64bit FILETIMEの照合を確認した。

**CR-01は差分再レビューで解消を確認した。** EXE一次の設定overlayが起動前に宣言され、正式helperは停止後copyの `ok` と未宣言ファイル・ディレクトリ・配布元ファイル差分を検査する。新規指摘はない。実機互換・人手回答・全件pytest・Phase04/05親鮮度の再検証は未実施であり、W12b 9行は `not-run`、`release_allowed=false` を維持する。実装担当の対象50件＋既存入口3件成功と修正後の隔離26件成功、Ruff/format・AST・Node・担当diffcheck成功は報告として再利用し、こちらではpytest・GUI・buildを実行していない。全tree diffcheckの既存CRLF大量差分による失敗は成功扱いしない。

## Narrative Findings (AI reviewer)

### CR-01 — 停止後の未宣言copy変更を検査せず正式passにできる（修正済み）

**当初分類:** BLOCKER／**現在:** 修正済み  
**File:** `.planning/phases/06-release-validation/06-05-w12b-driver.py:261-270,413-417`、`.planning/phases/06-release-validation/06-05-record-w12b.cjs:186-199`  
**Issue:** EXE一次の `support.prepare()` に設定JSONのoverlayを宣言していない。世代5の最終配布treeには `pagefolio_settings.json` がなく、製品の通常終了は `_save_window_state()`→`_persist_settings()` で実行EXEと同じディレクトリへ同ファイルを書き得る（`pagefolio/app.py:669-678,766-778`、`pagefolio/settings.py:37-50`）。`support.verify_copy()` はこの新規ファイルを `undeclared` として `ok=false` にする（`tests/release_uat_support.py:809-837`）。ところが採用helperは停止後snapshotの `source_unchanged` と `copy.distribution_changed.length===0` だけを確認し、`copy.ok`・`undeclared`・`extra_dirs` を見ない。したがって設定保存に限らず、隔離copy内の任意の未宣言ファイルを残したrunでも、他の証拠が揃えば `exe-script`/`exe-module` を `pass` にできる。追加試験 `tests/test_release_uat_support.py:266-286` 自体が「未宣言設定の生成はcopy差分になる」と示すが、W12b helperの採用拒否へは接続されていない。  
**Fix:** 配布treeに存在しない設定JSONは `support.prepare(..., overlays={support.SETTINGS_NAME: None})` などで明示的に可変overlayとして宣言する。正式helperは停止後snapshotの `copy.ok===true`、`undeclared=[]`、`missing_dirs=[]`、`extra_dirs=[]`、`distribution_changed=[]` とcopy/sourceの対応を要求し、宣言済みoverlayの変化だけを別欄で許容・記録する。設定保存と未宣言ファイル追加を別々の回帰にし、後者はdry-run/書込とも全ファイルbytes不変で拒否する。

**2026-11-07再監査:** `06-05-w12b-driver.py:261-271` は `support.prepare(..., overlays={support.SETTINGS_NAME: None})` を `support.start` より前に呼ぶ。`tests/release_uat_support.py:959-975` はcopy照合後にoverlayをmanifestへ宣言するため、起動前の宣言時序が成立する。`06-05-record-w12b.cjs:175-191` は最終snapshotについてoverlayの名前・値・起動前ログを照合し、`copy.ok===true`、`distribution_changed`・`missing_dirs`・`extra_dirs`・`undeclared`・`locked_unverified` の空配列を要求し、`overlay_changed` は設定JSONだけを許す。`tests/test_w12b_evidence.py:387-426` は宣言→起動の順序を、同`:535-549` はcopy改変とoverlay欠落の拒否を対象に含む。修正後隔離26件成功は実装担当の報告を再利用したもので、実機・全件の成功には算入しない。

### CR-02 — Python二次のlauncher PID照合（2026-11-09 差分レビュー・修正済み）

**経緯:** 実採取run `release-uat-cd223f3bcaf34f8f84bbe79f17b28129` でhelperが `Python二次API/排他証拠不一致` を返した。Windows venvでは `Popen.pid`（driverの `peer_identity.pid`=2972）がlauncher、resource-auditの `pid`（24248）が実インタプリタのため `audit.pid===peer.pid` が常に偽。調査は `../../debug/w12b-pid-mismatch.md`。修正は二次auditへの `parent_pid` 追加とhelperの親子照合。

独立レビュー（gsd-code-reviewer、読取専用）の指摘と処置:

- **BL-01（BLOCKER→修正済み）:** 親子照合のOR分岐で `peer.pid` の型・非owner制約が外れ、pid/parent_pid欠落同士や owner PIDを起動元とする記録を受理し得た。`Number.isInteger(peer.pid) && peer.pid>0 && peer.pid!==owner.pid` と `audit.pid>0` を明示し、該当2変異を拒否試験に追加。
- **WR-01（修正済み）:** 直接起動分岐（`audit.pid===peer.pid`）の受理試験がなかった。`test_w12b_accepts_direct_python_peer_without_launcher` を追加。
- **WR-02（修正済み）:** 台帳にlauncher PIDしか残らなかった。`audit_pid`/`audit_parent_pid` を記録し、正式記録試験で値を照合。
- **IN-06（修正済み）:** machine埋込 `peer_identity.audit` と `resource-audit.json` の一致を照合していなかった。W12cと同じ完全一致を追加し、埋込のみ改変の拒否試験を追加。
- IN-01〜05: PID再利用リスクなし、`owner` はスコープ内、audit鍵集合の厳密比較への影響なし、W12cに同種不具合なし、採取前の作業tree凍結が必要 — 情報のみ。

反映後の単一全件は `../04-startup-control/04-reverify-20261109-w12b-pid/`（2488 passed、186入力不変）。修正後の実機再採取は未実施。

## 照合した境界と未実施

- `tests/release_uat_support.py:705-729` のproduction owner probeは読取不能・アクセス拒否もownerありとして開始を拒否する。今回の `_record_for` 修正（`:1076-1108`）は自身のPopenで同一性を取得できない場合にその子だけをkill/waitする。所有PID再照合のもとで `support.stop` は所有記録だけを通常終了・必要時force終了する（`:1280-1344`）。
- driverは一次起動後に20秒の準備を取り、peer前と観察前に期限余白を確認する（`:276-305,388-405`）。短期限の負対照は `tests/test_w12b_evidence.py:356-405` でpeerを起動せずstopへ進む。これは実機の120秒内完遂の実測ではない。
- helperの肯定fixtureは実 `release_uat_support` run manifestの主要欄（source、copy、processes、snapshots）とPython peerのresource-audit形式に合わせている（`tests/test_w12b_evidence.py:97-130,137-205`、`tests/release_uat_support.py:885-978,1076-1245`）。ただし正式採用の単体fixtureは実GUIを起動しない。EXE二次7行を成功に転用できないこと、人手の画面数・同session復帰・状態保持は実機と直接回答で別途確認する。
