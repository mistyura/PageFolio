---
phase: 05-config-notification
reviewed: 2026-10-23T17:09:18Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - docs/CONFIGURATION.md
  - pagefolio/app.py
  - pagefolio/dialogs/plugin.py
  - pagefolio/dialogs/settings.py
  - pagefolio/dialogs/shortcuts.py
  - pagefolio/lang.py
  - pagefolio/ocr_dialog.py
  - pagefolio/redact_ops.py
  - pagefolio/settings.py
  - pagefolio/toast.py
  - pagefolio/ui_builder.py
  - pagefolio/viewer.py
  - tests/config_notice_support.py
  - tests/test_config_notification.py
  - tests/test_ocr.py
  - tests/test_pagination.py
  - tests/test_provider_ui.py
  - tests/test_settings_keyguard.py
  - tests/test_startup_windows.py
  - tests/test_toast.py
  - 開発履歴.md
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 5: コードレビュー報告

**レビュー日時:** 2026-10-23T17:09:18Z（2026-10-24 JST）
**深度:** standard
**対象ファイル:** 21
**状態:** issues_found

## Summary

修正コミット `7bbb06ce7f409b8ed090eb73d7a812ec9293926f` の3ファイルを、前回のCR-01/CR-02と既存の通知状態遷移に照合した。元のBLOCKER 2件はコード上解消した。一方、修正に伴って変更されたフォーカス試験に、入力先の前提を確認せずverifiedと記録できるWARNINGを1件検出した。現行の未解決件数はBLOCKER 0、WARNING 1、INFO none。

指定21ファイルの前回レビュー結果を引き継ぎ、今回の再確認は `pagefolio/app.py`、`pagefolio/dialogs/settings.py`、`tests/test_config_notification.py` の修正差分と関連経路に限定した。構造プリパスと外部レビューレーンの指定はない。元レビューは `05-REVIEW.iter1.md` に保存され、更新前の本書とのSHA256一致を確認した。

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: WARNING — フォーカス試験が入力欄を確認せずverifiedと記録できる

**File:** `C:/Users/shdwf/work/project/PageFolio/tests/test_config_notification.py:1514-1519`

**発火条件:** `TestLoadTracer.test_corrupt_settings_show_one_real_toast_and_keep_pdf_editable` の実行時に、Tk root自身やボタン等の入力欄以外へフォーカスがある場合。

**Issue:** 修正コミットはEntryの `focus_force()` とともに、入力先の前提を確定していた `assert focused is entry` も除いている。現行コードはEntryを生成するだけでフォーカス先を確認せず、任意の非Noneウィジェットが同一なら `focus_check=verified` と記録する。このため実際には入力欄のフォーカス保持を一度も通していない試験を、入力先を奪わない証拠へ読み替えられる。05-01-PLANの「入力可能なwidgetにフォーカスがある前提を確認」と、取得不能時の未検証記録を分ける契約が弱まっている。製品のフォーカス奪取を実測したという指摘ではない。

**根拠:** `entry = ttk.Entry(root)` は1510行に残るが、それをフォーカス先として参照するassertは存在しない。1517行の条件は `focused is not None` のみであり、`focused is root` でも1519行のverifiedに到達する。従来は同条件でも `focused is entry` で拒否できたため、今回の差分によるテスト信頼性の退行である。

**影響:** V110-CFG-01/04の入力先維持について、自動証拠が確認した範囲を過大に記録する。局所・全件成功の件数から、この入力欄の前提が満たされたとは判断できない。

**Fix:** 前景の強制取得は戻さず、既存の入力欄へ適切な通常フォーカス設定を行うか、観測したフォーカス先が対象Entryまたは入力可能widgetである場合だけ入力先維持をverifiedと記録する。非入力widgetやNoneの場合はその理由でunverifiedを記録する。一般のウィジェット同一性を確認した場合は、入力欄の検証結果と区別した属性名にする。修正後も人手確認済みとは扱わない。

## 前回指摘の解決判定

| 元ID | 判定 | 現行ソース・回帰の根拠 |
|---|---|---|
| CR-01 | コード上解消 / fixed: requires human verification | `dialogs/settings.py:286-296` は内側Shortcuts自身のDestroyに限定し、生存する外側へgrabを復元する。実Settings→実Shortcutsのsave/cancel/wm 3経路、子widget破棄、外側12秒保持、閉鎖後の通知開始を追加回帰が確認する。既存fakeも外側grabを残す条件へ修正された。 |
| CR-02 | コード上解消 / fixed: requires human verification | `app.py:166-167` のroot Map/Unmap接続と `app.py:549-558` の可視性処理で、root非表示をhidden理由で中断する。開始時・100ms監視・期限消化時もviewableを確認し、非消化理由はイベントを保持する。旧callbackはgeneration/event_idで拒否し、復帰は同じイベントの残時間を使用する。仮想時計3件と実withdraw/iconify 2件で、40秒非表示・残6000ms・FIFO・子widgetイベント・旧callbackを被覆している。 |

両件の修正コミットは `7bbb06ce7f409b8ed090eb73d7a812ec9293926f`。今回の修正差分から、上記2件の再発や別の新規製品BLOCKERは検出しなかった。人手確認の未実施は残るコード指摘として件数へ重複計上しない。

## レビューの証拠と限界

- `05-REVIEW-FIX.md`、`05-reviewfix-evidence.json`、`05-reviewfix-quality.json`、実行ログを読み、局所288 passed / 1 warning / 15.35秒 / exit0、単一全件1797 passed / 1 warning / 266.50秒 / exit0を確認した。Ruff/format109 unchanged/AST成功、入力103件と診断423件のhash一致は提出済み専用証拠を参照した。レビュー中に試験・GUI・新規実プロセスを起動しておらず、これらを自分の再実行結果とは表記しない。
- 新規回帰は8件。元2件のREDの後に実装され、現在のコミットに含まれる追加境界と旧callback/FIFO/残時間のassertを照合した。対象3ファイルに未コミット差分はない。
- H01〜H12の12 passは修正前の人手証拠である。修正後の今回2境界は人手未実施。修正報告の `fixed: requires human verification` を維持し、自動成功で人手合格に読み替えない。
- DEP-05/owner_missing/通知前景不一致/Tcl解放警告、descriptor不明の禁止2件、未分類edge4件は未解除。今回のコード判定は出荷承認・Phase正式完了ではなく、同種再発時停止を維持する。既報UI advisoryを新規指摘へ重複計上しない。
- 実装・テスト・共有文書は変更していない。出力は本レビューのみで、commitは行っていない。

---

_Reviewed: 2026-10-23T17:09:18Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
