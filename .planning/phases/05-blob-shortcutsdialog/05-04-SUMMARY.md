---
phase: 05-blob-shortcutsdialog
plan: 04
subsystem: ui
tags: [tkinter, shortcuts, focus-guard, pytest]

# Dependency graph
requires:
  - phase: 05-blob-shortcutsdialog (plan 01/03)
    provides: サムネイル仮想化・LRU化・Blobリーク検出（本プランとは独立実装だが同一フェーズの堅牢性強化）
provides:
  - ShortcutsDialog._start_capture のWR-01修正（キャプチャ対象切替時に旧行表示を復元）
  - app.py の should_suppress_for_focused_input 純関数 + _INPUT_WIDGET_CLASSES 定数（WR-02フォーカスガード）
  - _bind_shortcuts の発火ラムダへのフォーカスガード挿入（root.focus_get() None防御込み）
  - tests/test_shortcuts_dialog.py（ShortcutsDialog 初の単体テスト・WR-01/WR-02回帰検知）
affects: [phase-06-quality-assurance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk非依存の純関数によるフォーカスガード判定（app.py の build_keysym_from_event 等の隣接系譜）"
    - "実Tk root（module-scope fixture・withdraw）を使うウィジェット表示状態テスト（tests/test_batch_ocr_dialog.py の踏襲）"

key-files:
  created:
    - tests/test_shortcuts_dialog.py
  modified:
    - pagefolio/dialogs/shortcuts.py
    - pagefolio/app.py

key-decisions:
  - "WR-02はキャプチャ時の登録拒否ではなく発火側フォーカスガードで解消（D-09/D-10）。既定キー<Delete>/<F5>の潜在衝突も同時に根治"
  - "フォーカスガード純関数は Ctrl/Alt を含む組合せを常に非抑止とし、修飾なし単キー/Shiftのみの組合せのみ入力系ウィジェットフォーカス中に抑止"

patterns-established:
  - "Pattern: root.bind ラムダ内で focus_get().winfo_class() を判定材料として渡し、None時は空文字列へフォールバックする（Tk依存部分は呼び出し側、判定ロジックは純関数）"

requirements-completed: [V180-ROBUST-03]

coverage:
  - id: D1
    description: "ShortcutsDialog でキャプチャ対象を切り替えると前行の「キーを押してください」表示が残留せず、旧行が元のkeysym表示へ復元される（WR-01）"
    requirement: "V180-ROBUST-03"
    verification:
      - kind: unit
        ref: "tests/test_shortcuts_dialog.py::TestStartCaptureRestoresPreviousRow::test_switching_capture_restores_previous_row_label"
        status: pass
      - kind: unit
        ref: "tests/test_shortcuts_dialog.py::TestStartCaptureRestoresPreviousRow::test_single_capture_start_shows_waiting_only_on_target_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "should_suppress_for_focused_input が Ctrl/Alt 組合せを非抑止・入力系ウィジェット（Entry/Spinbox/TSpinbox/Text）フォーカス中の修飾なし単キー/Shiftのみの組合せを抑止・非入力系ウィジェットとフォーカスなしは非抑止と正しく判定する（WR-02）"
    requirement: "V180-ROBUST-03"
    verification:
      - kind: unit
        ref: "tests/test_shortcuts_dialog.py::TestShouldSuppressForFocusedInput（10ケース全通過）"
        status: pass
    human_judgment: false
  - id: D3
    description: "_bind_shortcuts の発火ラムダがフォーカスガードでラップされ、root.focus_get() が None を返すケースでも例外化しない"
    requirement: "V180-ROBUST-03"
    verification:
      - kind: unit
        ref: "tests/test_shortcuts_dialog.py::TestShouldSuppressForFocusedInput::test_unmodified_key_not_suppressed_when_no_focus"
        status: pass
      - kind: unit
        ref: "pytest 全件（1072件）グリーン — _bind_shortcuts 経由の既存ショートカット回帰なし"
        status: pass
    human_judgment: false

duration: 約15分
completed: 2026-07-16
status: complete
---

# Phase 5 Plan 4: ShortcutsDialog WR-01/WR-02 解消 Summary

**ShortcutsDialogの表示残留バグ（WR-01）をキャプチャ切替時の旧行復元で修正し、入力系ウィジェットとのキー衝突（WR-02）を`should_suppress_for_focused_input`フォーカスガードで解消。ShortcutsDialog初の単体テスト12件を新設。**

## Performance

- **Duration:** 約15分
- **Started:** 2026-07-16T (セッション開始時刻)
- **Completed:** 2026-07-16
- **Tasks:** 3
- **Files modified:** 3（新規1・改修2）

## Accomplishments
- WR-01: `_start_capture` がキャプチャ対象切替時に旧 `_capturing_cmd` を退避し `_end_capture()` 後に `_refresh_row(prev_cmd)` を呼ぶよう修正。前行の「キーを押してください」表示が残留しなくなった
- WR-02: `app.py` に `_INPUT_WIDGET_CLASSES` 定数と `should_suppress_for_focused_input(keysym, focused_widget_class)` 純関数を新設。`_bind_shortcuts` の発火ラムダをこのガードでラップし、Ctrl/Alt を含む組合せは従来どおり発火、修飾なし単キー/Shiftのみの組合せは入力系ウィジェット（Entry/TEntry/Spinbox/TSpinbox/Text）フォーカス中のみ抑止するよう改修。既定キー `<Delete>`/`<F5>` の潜在的な入力衝突も同時に根治
- `tests/test_shortcuts_dialog.py` を新設（ShortcutsDialog 初の単体テストファイル）。WR-02 は純関数の10ケース網羅（Ctrl/Alt非抑止・各入力系クラス抑止・非入力系非抑止・フォーカスなし防御・Shiftのみ組合せ）、WR-01 は実Tk root（module-scope fixture）でキャプチャ切替の実ウィジェット状態を検証

## Task Commits

Each task was committed atomically:

1. **Task 1: WR-01 修正（_start_capture でキャプチャ切替時に旧行表示を復元）** - `475a06a` (fix)
2. **Task 2: WR-02 修正（should_suppress_for_focused_input 純関数 + _bind_shortcuts フォーカスガード）** - `bcb95a5` (fix)
3. **Task 3: tests/test_shortcuts_dialog.py 新設（WR-01/WR-02 回帰テスト）** - `1940f87` (test)

_Note: 非TDDプラン（tdd属性なし）のため RED/GREEN 分離コミットは行わず、各タスク完了時にfix→testの順で1コミットずつ実施。_

## Files Created/Modified
- `pagefolio/dialogs/shortcuts.py` - `_start_capture` に旧行復元ロジックを追加（WR-01）
- `pagefolio/app.py` - `_INPUT_WIDGET_CLASSES`/`should_suppress_for_focused_input` 新設・`_bind_shortcuts` の発火ラムダをフォーカスガードでラップ（WR-02）
- `tests/test_shortcuts_dialog.py` - ShortcutsDialog 初の単体テスト（WR-01/WR-02 回帰検知、計12テスト）

## Decisions Made
- WR-02 はキャプチャ時の登録拒否ではなく発火側フォーカスガードで解消（D-09/D-10 に従い計画どおり実装。登録の自由度を維持しつつ既定キー衝突も同時根治）
- フォーカスガードのラムダは `root.focus_get()` が `None` の場合に空文字列へフォールバックし、`should_suppress_for_focused_input` 側は非入力系扱い（False＝非抑止）で応答する設計を採用（計画の Open Question 2 の推奨実装をそのまま採用）

## Deviations from Plan

None - plan executed exactly as written（3タスクとも計画の action どおりに実装し、acceptance_criteria を全て満たした）。

## Issues Encountered

None. `ruff check . && ruff format .` はクリーン、`pytest` は既存1060件 + 新規12件の計1072件が全通過（回帰なし）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V180-ROBUST-03（ShortcutsDialog WR-01/WR-02）が本プランで解消済み。Phase 5 の残り要件（V180-PERF-01〜03・V180-ROBUST-01）は 05-01/05-03 で対応済みのため、Phase 5 は全4プラン完了見込み
- 次は Phase 5 の完了確認（`/gsd-verify-work` 等）または Phase 6（品質保証仕上げ）への移行が可能

---
*Phase: 05-blob-shortcutsdialog*
*Completed: 2026-07-16*
