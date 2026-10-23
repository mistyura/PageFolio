---
phase: 05-config-notification
reviewed: 2026-10-23T16:42:28Z
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
  critical: 2
  warning: 0
  info: 0
  total: 2
status: issues_found
---

# Phase 5: コードレビュー報告

**レビュー日時:** 2026-10-23T16:42:28Z（2026-10-24 JST）
**深度:** standard
**対象ファイル:** 21
**状態:** issues_found

## Summary

指定された21ファイルを対象に、基点 `4f0fb97` からのPhase 5差分と現在の呼出関係を確認した。新しい設定通知が利用者に見えない間に消化される経路を2件検出した。いずれも通知キューが保持するイベントを失う正しさの問題であり、D-18/D-21とV110-CFG-04の受入に影響する。BLOCKERは2件、WARNING・INFOはnone。

構造プリパスと外部レビューレーンの指定はない。過去のレビュー結果・計画・テスト成功は現行コードの正しさの証明として扱わず、下記の具体的な経路をソースで追跡した。既知のDEP-05/owner_missing/通知前景不一致/Tcl解放警告、descriptor不明の禁止2件、未分類edge4件、および既報のUI advisoryは本指摘に重複計上していない。既存の未コミット別件差分は変更していない。

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: BLOCKER — 内側ショートカット画面の終了で外側設定画面の通知保護が失われる

**File:** `C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/shortcuts.py:283-284`

**関連箇所:** `pagefolio/dialogs/settings.py:279-285`、`pagefolio/app.py:543-555`、`pagefolio/app.py:603-606`。

**発火条件:** 一般設定を開き、その中のショートカット設定で「保存」を押す。設定JSONの保存が失敗するか、unreadable保護によって保存が抑止され、外側の一般設定画面を10秒以上開いたままにする。既に待機中の読込・保存通知がある状態で内側をキャンセルした場合も同じ経路になる。

**Issue:** 内側の `ShortcutsDialog` は `grab_set()`（同ファイル60行）で外側のgrabを置き換える。保存は新しい `_persist_settings()` を通って通知を登録した直後、内側だけを `destroy()` する。呼出側 `_open_shortcuts_dialog()` に外側grabを復元する処理がなく、外側SettingsDialogが生存していてもgrabがなくなる。通知監視は `grab_current()` だけでモーダルを判定するため、次のidle/監視でメイン画面のToastを表示し、外側画面を閉じる前に期限でイベントを `popleft()` する。外側に隠れた保存失敗通知を利用者が閉鎖後に確認できなくなる。

**根拠:** 同じ問題に対し、LLM画面には `dialogs/settings.py:246-258` と `ocr_dialog.py:1030-1042` に内側Destroy時の外側grab復元が追加されているが、ショートカット経路には接続されていない。既存 `TestLlmSaveOrigins.test_real_nested_close_restores_outer_grab` はこのTkのgrab消失を扱う。一方、`TestToolSaveOrigins.test_shortcuts_close_leaves_failed_event_for_display` はfakeの `destroy` でgrabをNoneにし、外側SettingsDialogの存在を表現せず通知開始を期待しているため、この製品経路を検出できない。既報の「外側Applyによるショートカット値の巻戻り」とは別の通知寿命の欠陥である。

**影響:** ショートカット保存の失敗・保存抑止を認識できず、読込通知を含む待機イベントも外側画面の背後で消化される。文書化された「内側を閉じても外側モーダルがある間は待つ」（`docs/CONFIGURATION.md:323`）を満たさない。

**Fix:** ショートカットにも内側自身のDestroy時に生存する外側SettingsDialogへgrabを戻す処理を接続する。保存・キャンセル・WM閉鎖を同じ後処理に通し、他の子widgetのDestroyでは復元しない。LLMと共通の小さなヘルパーにまとめてもよい。実Settings→実Shortcuts→保存失敗／キャンセル→外側を10秒以上保持→外側閉鎖の回帰を追加し、外側grab・イベント数・未消化時間を確認する。

### CR-02: BLOCKER — 最小化中にも設定通知の期限が進み未確認イベントを破棄する

**File:** `C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:616-645`

**関連箇所:** `pagefolio/app.py:547-557`、`pagefolio/app.py:598-606`、`pagefolio/toast.py:120-131`。

**発火条件:** 読込失敗または保存失敗の通知が表示中／待機中にメインウィンドウを最小化し、そのまま通知の残時間以上待つ。例えば表示4秒後に最小化して6秒以上待つ。

**Issue:** 表示開始条件はrootの存在・grab・Toastのカテゴリだけであり、rootが実際に表示されているかを確認しない。表示中の監視もgrabの有無しか確認せず、最小化による非表示を中断理由にしていない。Tkの `after` は最小化中も進むため、Toastの期限callbackから `expired` が送られ、`_on_config_notice_closed()` は不可視時間を残時間から引いてイベントを消化する。後続イベントも `after_idle` で同じ最小化中のrootに表示開始され、最小化を続ければFIFO全体が画面に出ないまま失われる。

**根拠:** `shown_at` は `app.py:640` で無条件に開始し、`toast.py:122` の期限はウィンドウの表示状態と独立して予約される。`app.py:603-604` が期限時に再判定するのはモーダルgrabのみ。対象のApp/Toastに `<Map>`/`<Unmap>` や `winfo_viewable()` 等による中断・復帰の処理はない。既存試験は `withdraw()` したrootでも通知の開始を許しており、非表示時間を可視時間から除く境界を検証していない。

**影響:** 元の設定を読めなかったこと、または変更が次回起動に残らないことを利用者が一度も確認できない。D-21の各イベント10秒の「可視時間」と、未消化通知を捨てない契約に反する。これは他アプリによる通常の重なり検出を要求する指摘ではなく、製品自身が観測できる最小化・非表示状態に限定する。

**Fix:** rootが非表示／最小化された場合は設定通知だけを非消化の終了理由で中断し、可視だった時間だけを残時間から差し引く。表示開始と期限の消化条件にも可視性を含め、再表示時に同じevent_id・残時間で再開する。root自身のMap/Unmapイベント等を使い、子widgetイベントや既存PDF/印刷Toastに干渉しない。通知前に最小化、4秒表示後に最小化、複数イベントを残したまま長時間最小化の回帰で、復帰前の消化0と復帰後の残り6秒／各10秒を確認する。

## レビューの証拠と限界

- 本報告の2件は現行ソースの呼出・grab・timer・消化条件から導いた指摘である。レビュー中に新しいGUI・実プロセス・障害注入試験は起動しておらず、新規の実機再現結果とは表記しない。
- 既存の全件1789 passed / 1 warning、局所280 passed、Ruff/format/AST、H01〜H12の12 passは提出済み証拠として参照した。今回の2境界を通過した証拠ではない。不要な成功試験の反復は行っていない。
- 実装・テスト・共有文書は変更していない。出力は本レビューのみで、commitは行っていない。

---

_Reviewed: 2026-10-23T16:42:28Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
