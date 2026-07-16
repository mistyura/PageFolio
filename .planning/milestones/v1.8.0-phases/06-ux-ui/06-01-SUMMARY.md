---
phase: 06-ux-ui
plan: 01
subsystem: ui
tags: [tkinter, toast, error-handling, i18n, mixin]

# Dependency graph
requires: []
provides:
  - "pagefolio/toast.py の ToastManager（保存/印刷失敗の再試行付き非モーダルトースト）"
  - "UIBuilderMixin._show_error_or_toast(category, title, msg, retry_cb) 共通ヘルパー"
  - "file_ops.py/print_ops.py の保存3操作+印刷の失敗パスのトースト化・成功パスの dismiss"
affects: [06-02-ui-consistency-audit, 06-03-changelog-insert-redo]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "place() オーバーレイによる常駐通知 Frame（Toplevel/overrideredirect 不採用）"
    - "_build_ui() 内で毎回インスタンス化し直すコンポーネント（_build_menubar と同型・_rebuild_ui 対応）"
    - "getattr(self, '_toast', None) フォールバックを Mixin 共通ヘルパーへ集約（_show_error_or_toast）"

key-files:
  created:
    - pagefolio/toast.py
    - tests/test_toast.py
  modified:
    - pagefolio/lang.py
    - pagefolio/ui_builder.py
    - pagefolio/file_ops.py
    - pagefolio/print_ops.py
    - tests/test_print.py

key-decisions:
  - "トースト対象は保存3操作+印刷の4操作のみ（D-01/D-02）。約80箇所の messagebox は網羅置換しない"
  - "印刷の一時ファイル生成失敗とOS印刷コマンド失敗は同一カテゴリ print だが異なるLANGキー（err_print_msg vs err_print_no_handler）で文言区別する（レビューR1）"
  - "getattr(self, '_toast', None) → messagebox フォールバックをUIBuilderMixin._show_error_or_toastへ共通化（レビューR2）"

patterns-established:
  - "Pattern: 常駐通知コンポーネントは _build_ui() 内で再生成し _rebuild_ui() のウィジェット全破棄に耐える（ToastManager/menubar 共通の設計）"

requirements-completed: [V180-QA-02]

coverage:
  - id: D1
    description: "ToastManager が place() 右下オーバーレイで単一トーストを show/update/dismiss し、再試行コールバックを発火する"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestToastManagerShowDismiss"
        status: pass
    human_judgment: false
  - id: D2
    description: "_build_ui() が ToastManager を毎回再生成し、テーマ切替（_rebuild_ui）後も self._toast が有効"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestToastRegeneratedAfterRebuild"
        status: pass
    human_judgment: false
  - id: D3
    description: "UIBuilderMixin._show_error_or_toast がトースト表示/messageboxフォールバックを一元化する（レビューR2）"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestShowErrorOrToast"
        status: pass
    human_judgment: false
  - id: D4
    description: "保存3操作（_save_file/_save_as/_save_compressed）の失敗が共通ヘルパー経由でトースト表示され、成功パスでdismissされる"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper"
        status: pass
    human_judgment: false
  - id: D5
    description: "印刷の一時ファイル失敗とOS印刷失敗が同一カテゴリprintで異なる文言により区別できる（レビューR1）。成功パスでdismissされる"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestPrintPathsDistinguishFailureMessages"
        status: pass
    human_judgment: false
  - id: D6
    description: "LANG ja/en 双方に toast_retry_btn キーが同数存在する（D-09）"
    requirement: "V180-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_lang_parity.py::test_lang_keys_parity"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-16
status: complete
---

# Phase 6 Plan 01: 保存/印刷失敗の再試行トースト通知 Summary

**place() オーバーレイの ToastManager を新設し、保存3操作+印刷失敗を共通ヘルパー _show_error_or_toast 経由でトースト化（自動消滅なし・同時1件・成功/別経路成功で dismiss）**

## Performance

- **Duration:** 約20分
- **Started:** 2026-07-16T10:51:33Z
- **Completed:** 2026-07-16T11:06:37Z
- **Tasks:** 3
- **Files modified:** 7（新規2・改修5）

## Accomplishments
- `pagefolio/toast.py` に `ToastManager` を新設。右下 `place()` オーバーレイで単一トーストを show/dismiss し、同一カテゴリ再showは文言更新のみ（D-04）、異なるカテゴリは常に置換（D-07）
- `ui_builder.py` の `_build_ui()` 内で `self._toast = ToastManager(self)` を毎回再生成し、`_rebuild_ui()`（テーマ切替時の root 全ウィジェット破棄）後もトーストが有効であることを保証（Pitfall 2）
- `UIBuilderMixin._show_error_or_toast(category, title, msg, retry_cb)` 共通ヘルパーを新設し、`_toast` 未生成時は `messagebox.showerror` へフォールバック（レビューR2・5失敗パスの `getattr` 重複を解消）
- `file_ops.py` の `_save_file`/`_save_as`/`_save_compressed` の失敗パスをトースト化、成功パス（他経路含む）に `dismiss(category)` を追加（D-02/D-08）
- `print_ops.py` の `_print_pdf`（一時ファイル生成失敗）と `_send_to_printer`（OS印刷コマンド失敗）を同一カテゴリ `"print"` としつつ、異なる LANG キー（`err_print_msg` vs `err_print_no_handler`）で文言を区別（レビューR1）。成功2パスに `dismiss("print")` を追加
- LANG ja/en 双方に `toast_retry_btn` キーを追加（parity 維持）

## Task Commits

Each task was committed atomically:

1. **Task 1: ToastManager 実装 + 単体テスト + LANG キー追加** - `e998749` (feat)
2. **Task 2: ui_builder._build_ui への ToastManager 配線 + _show_error_or_toast 共通ヘルパー** - `245d5fc` (feat)
3. **Task 3: 保存/印刷失敗パスのトースト化 + 成功パスの dismiss（統合テスト）** - `a4398c7` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pagefolio/toast.py` - `ToastManager`（show/dismiss、右下place()オーバーレイ、単一トースト置換/更新）
- `tests/test_toast.py` - ToastManager単体テスト＋_show_error_or_toast両分岐＋保存/印刷統合テスト
- `pagefolio/lang.py` - ja/en 双方に `toast_retry_btn` キー追加
- `pagefolio/ui_builder.py` - `_build_ui()` 内の ToastManager 再生成 + `_show_error_or_toast` 共通ヘルパー
- `pagefolio/file_ops.py` - 保存3メソッドの失敗パス→トースト、成功パス→dismiss
- `pagefolio/print_ops.py` - 印刷2メソッドの失敗パス→トースト（R1文言区別）、成功パス→dismiss
- `tests/test_print.py` - `_DummyPrintApp` に `_show_error_or_toast` フォールバック契約シムを追加（既存テストの回帰修正）

## Decisions Made
- トースト対象は保存3操作+印刷のみ（D-01/D-02）。入力バリデーション・ファイルオープン・パスワード系の `messagebox.showerror` は変更せず維持（D-01、grep確認済み）
- 印刷の2失敗経路は同一カテゴリ `"print"`（D-07 同時1件維持）だが `err_print_msg.format(e=e)`（一時ファイル失敗・例外詳細含む）と `err_print_no_handler`（OSハンドラ不在）で文言を区別（レビューR1採用）
- `getattr(self, "_toast", None)` → `messagebox` フォールバックは `UIBuilderMixin._show_error_or_toast` へ一元化（レビューR2採用）。dismiss 呼び出し側は各成功パスで個別に `getattr` ガードを維持（dismiss には共通ヘルパーを設けず、show/フォールバックのみ共通化という設計判断）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 既存 `tests/test_print.py::TestSendToPrinter::test_no_handler_shows_error` の回帰修正**
- **Found during:** Task 3（print_ops.py 改修後の全体テスト実行）
- **Issue:** `_send_to_printer` のOS印刷失敗パスを `messagebox.showerror` から `self._show_error_or_toast(...)` へ置換したため、既存テストの Tk 非依存ダミー `_DummyPrintApp` に `_show_error_or_toast` メソッドが存在せず `AttributeError` で失敗
- **Fix:** `_DummyPrintApp` に、実装（`UIBuilderMixin._show_error_or_toast`）と同じフォールバック契約（`_toast` なしなら `messagebox.showerror`）を再現する最小シムメソッドを追加。UIBuilderMixin を mixin せず Tk非依存の設計意図を維持
- **Files modified:** `tests/test_print.py`
- **Verification:** `pytest tests/test_print.py -x -q` グリーン（6件）。フルスイート再実行で解消確認
- **Committed in:** `a4398c7`（Task 3 コミット内）

---

**Total deviations:** 1 auto-fixed（Rule 1・既存テストの回帰修正）
**Impact on plan:** print_ops.py の契約変更に直接起因する既存テストの追随修正のみ。スコープ拡大なし。

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V180-QA-02 完了。フルスイート 1093 件グリーン・ruff クリーン
- Plan 02（UI一貫性監査: スクロール/フォント）・Plan 03（開発履歴.md整合+insert_redoバグ修正）は本プランと独立して着手可能

---
*Phase: 06-ux-ui*
*Completed: 2026-07-16*

## Self-Check: PASSED

全作成/改修ファイル（pagefolio/toast.py・tests/test_toast.py・pagefolio/lang.py・
pagefolio/ui_builder.py・pagefolio/file_ops.py・pagefolio/print_ops.py・
tests/test_print.py・本SUMMARY.md）の実在確認、および Task 1〜3・SUMMARY 各コミット
（e998749/245d5fc/a4398c7/f641dd0）の `git log` 実在確認とも FOUND。
