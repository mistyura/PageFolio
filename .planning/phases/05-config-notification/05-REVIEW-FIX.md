---
phase: 05-config-notification
fixed_at: 2026-10-23T17:04:55Z
review_path: .planning/phases/05-config-notification/05-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
commits: 1
commit: 7bbb06ce7f409b8ed090eb73d7a812ec9293926f
---

# Phase 05: コードレビュー修正報告

**修正日時:** 2026-10-24 02:04:55 JST
**元レビュー:** `.planning/phases/05-config-notification/05-REVIEW.md`
**反復:** 1
**対象:** Critical 2件、Warning 0件。修正2件、スキップ0件。

## 修正した指摘

### CR-01: 内側ショートカット終了時に外側設定画面の通知保護を維持

**判定:** fixed: requires human verification
**コミット:** `7bbb06ce7f409b8ed090eb73d7a812ec9293926f`
**変更ファイル:** `pagefolio/dialogs/settings.py`、`tests/test_config_notification.py`

`_open_shortcuts_dialog()` が生成した内側自身の `<Destroy>` に後処理を接続し、生存する外側 `SettingsDialog` の grab を復元する。保存・取消・WM閉鎖のすべてが同じ経路を通り、子widgetのDestroyは対象外とした。focusの強制取得は追加していない。

実 `SettingsDialog` → 実 `ShortcutsDialog` の3経路を試験し、内側閉鎖後の外側grab、12秒経過後の通知未表示・イベント1件・残10000ms、外側閉鎖後の表示開始をassertした。既存fake試験にも外側grabを表現し、内側の保存直後に通知が始まる誤った期待を修正した。

**RED:** 固定runnerから `pytest tests/test_config_notification.py::TestToolSaveOrigins::test_real_shortcuts_close_restores_outer_grab -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_reviewfix_red01`。1 failed / 1 warning / 1.59秒 / exit1。保存後に `grab_current() is outer` が `None` で失敗した。`05-reviewfix-red01/pytest.txt` に原文を保存。

**GREEN:** 同試験のsave/cancel/wm 3件を含む局所288件と全件1797件が成功。実Tkでの自動検証は完了したが、修正後の人手受入は新しく実施していない。状態制御の論理修正として上記の `requires human verification` を保持し、独立レビューへ引き渡す。

### CR-02: root最小化・非表示中に通知の可視時間を消化しない

**判定:** fixed: requires human verification
**コミット:** `7bbb06ce7f409b8ed090eb73d7a812ec9293926f`
**変更ファイル:** `pagefolio/app.py`、`tests/test_config_notification.py`

root自身のMap/Unmapを監視し、不可視になった設定通知を `hidden` 理由で中断する。通知開始・既存100ms監視・期限callbackの消化判定に `root.winfo_viewable()` を含めた。中断はイベントを残し、可視だった時間だけを差し引いた残時間で同じevent_idを再開する。既存generation/event_id照合で古いcallbackを拒否し、子widgetイベントは無視する。

仮想時計では開始前非表示と表示4秒後の非表示に各3イベントを投入し、40秒非表示でも消化0、復帰後に10000ms/6000msで再開してFIFO完走することをassertした。期限直前に不可視になった場合の消化防止も確認した。実App/実Toastでは `withdraw` と `iconify` により実際のrootとFrameを非表示にし、残6000ms・同event_idでの復帰、子widgetイベント、旧期限/close callbackの拒否を確認した。

既存の再構築・plugin modal・LLM modal・複合受入・読込tracerは、実際に可視なrootで通知表示を期待する条件へ合わせた。tracerはwithdrawnの間に通知がないことも確認し、可視性の偽装は行っていない。tracerの強制focus取得を除き、通知前後で観測できた入力先が同じことを確認する。`ToastManager` と既存PDF/印刷retry実装は変更せず、該当回帰も局所検証に含めた。他アプリによる被覆検出へは拡大していない。

**RED:** 固定runnerから `pytest tests/test_config_notification.py::TestNotificationLifecycle::test_hidden_root_preserves_fifo_and_visible_time -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_reviewfix_red02`。1 failed / 1 warning / 0.20秒 / exit1。非表示40秒後、期待event_id `[1, 2, 3]` に対して空のFIFOとなるassertで失敗した。`05-reviewfix-red02/pytest.txt` に原文を保存。

**GREEN:** 新規5境界（仮想時計3件、実root2件）を含む局所288件と全件1797件が成功。修正後の人手受入は未実施で、論理修正の `requires human verification` は独立レビューへ引き渡す。

## 検証

実行場所は **main checkout / 通常Windows / `.venv`**。`workflow.use_worktrees=false` を尊重し、worktreeは作成していない。GUI/全件は専用hidden dispatcherから既存固定 `05-02-verify.py` を起動した。前景を強制変更せず、非console2秒安定・30秒上限とpytest期限を維持した。新install、skip、selector除外、期限延長は行っていない。

| 検証 | 結果 | 証拠 |
|---|---|---|
| 局所 `pytest tests/test_config_notification.py tests/test_toast.py tests/test_pdf_ops.py -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_reviewfix_targeted04` | 288 passed / 1 warning / 15.35秒 / exit0 | `05-reviewfix-targeted04/pytest.txt`・`status.json` |
| 単一全件 `pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_reviewfix_full03` | 1797 passed / failed0 / ERROR0 / skipped0 / 1 warning / 266.50秒 / exit0 | `05-reviewfix-full03/pytest.txt`・`status.json` |
| 全体Ruff → Python限定format → Ruff → AST → diff | 全成功、最終format109 files unchanged / exit0 | `05-reviewfix-quality.json` |
| 検証入力SHA256 | 103件、不一致0 | `05-reviewfix-inputs.json`・`05-reviewfix-evidence.json` |
| 診断原本/コピー/manifest SHA256 | 423件、不一致0 | `05-reviewfix-full03/artifacts/manifest.json` |
| DoDが読むplanningの最終snapshot | 229件のhashを保存 | `05-reviewfix-evidence.json` の `planning_gate_sha256` |
| dispatcher | `stopped` 確認 | `05-reviewfix-dispatch/stopped` |

全件のwarning1件は既存PyMuPDFのByteString非推奨。全件成功後、入力103件を再hashして一致確認し、その同じ製品・テストの3ファイルだけをcommitした。commit前に固定root/`feature/v1.10.0` を照合し、通常hooks付き `git commit --only ... -- pagefolio/dialogs/settings.py pagefolio/app.py tests/test_config_notification.py` を使用した。ROADMAPの既存staged blob `9b9f86ba59fe99666e128faf5931216e5bc19494` は前後一致。対象ソースの未commit差分は残っていない。

## 途中の失敗と適用契約の扱い

- 局所初回は新試験の連続TkinterDnD初期化で `can't find package tkdnd`（4 passed / 1 failed）。新しい表示状態試験を既存tracerと同じ実 `tk.Tk` + 実App経路へ修正した。次は新試験の復帰assertがteardown後に置かれた誤り（3 passed / 1 failed）を修正した。3回目は旧plugin試験がwithdrawn rootで通知を期待していたため37 passed / 1 failedとなり、可視条件へ修正した。製品の可視性を偽装せず、最終288件成功で解消した。各 `05-reviewfix-targeted01〜03` の初回出力を保持している。
- 全体Ruffのsandbox試行は既存証拠フォルダで `os error 5` を出したため、正規 `require_escalated` 経路で同じ品質検査を実行し成功した。
- 最初の全件要求は非console前景が30秒内に安定せずpytest開始前に停止した（`05-reviewfix-full/status.json`）。親へ準備signalを返し、利用者の切替済み回答後に再投入した。
- 次の全件は196 passed / 1 failed / 1 warning / 13.99秒、`test_completed_phases_are_validated` にて「未完了ProgressとPLAN/SUMMARY件数が不整合」で停止（`05-reviewfix-full02`）。親がSDKで実4SUMMARYに対するProgress件数3/4→4/4を同期し、In ProgressとPhase未完了を維持した。DoD試験やVALIDATIONを弱めず、対象DoD 1件成功を親が確認した後に全件を実施し直した。fixerは共有文書を変更していない。
- 2件は同じ恒久テストファイルの可視条件・モーダル条件に依存する。検証したtreeとcommitの一致を優先し、親の明示指示で **1 finding 1 commit契約から逸脱して同一atomic commitへ集約**した。未検証の中間treeを作らず、各CRのRED/GREENと同一commit参照を上記に保持した。修正2件に対しcommit数は1である。
- `05-REVIEW-FIX.md` と専用修正証拠は親のcommit対象とし、fixerはcommitしていない。REVIEW/VALIDATION/SECURITY等の親監査文書、共有STATE/state.json/ROADMAP/REQUIREMENTS、pyproject、版番号は変更していない。

## 残る確認事項

修正前の人手H01〜H12の12 passは既存証拠として保持し、今回の2境界を人手で再確認済みとは扱わない。独立code review・Phase正式完了・出荷判定は親へ引き渡す。

`DEP-05-REGRESSION`、owner_missing、通知前景不一致、既存Tcl別thread破棄警告は未解決のまま。本全件成功は原因修復・依存解除・出荷承認ではない。条件付き実装承認と同種再発時停止は継続し、今回の全件では当該症状の失敗は観測しなかった。descriptor不明の禁止2件・未分類edge4件を解除していない。

---

_修正担当: gsd-code-fixer / 反復1_

## 修正報告後の独立再確認と人手受入

2026-10-24 JSTに利用者がH13/CR-01とH14/CR-02を明示確認し、両項目passを05-UAT.mdへ記録した。上記requires human verificationは報告時点の状態で、当該2件の人手待ちは解消済み。WR-01は2654882で入力欄の場合だけverifiedを記録するよう修正し、独立再レビューはclean（critical/warning/info各0）。最新全件は05-focus-proof-final/の1797 passed / 1 warning / 266.81秒 / exit0。103入力・423診断のhash不一致0、Ruff/format109/AST成功。既知の外部依存・Tcl警告・内容不明のプローブ・出荷停止は維持する。
