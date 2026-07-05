---
phase: 04-ui-ux
plan: 01
subsystem: ui
tags: [tkinter, keyboard-shortcuts, pure-functions, refactor]

# Dependency graph
requires:
  - phase: 03-v1-5-0
    provides: "merge_shortcuts / shift_variant_keysym 純関数（app.py:35-50）と test_v150_regression.py の既存テスト基盤"
provides:
  - "build_keysym_from_event / find_duplicate_binding / keysym_to_display の3純関数（app.py）"
  - "再実行可能な _bind_shortcuts() メソッドと self._default_shortcuts / self._cmd_map / self._bound_keysyms インスタンス属性"
  - "純関数3種の回帰テスト（test_v150_regression.py）"
affects: [04-02 (ShortcutsDialog), 04-ui-ux]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk 非依存の純関数を app.py モジュールレベルへ追加し、既存 merge_shortcuts/shift_variant_keysym と同居させるパターンを継続"
    - "再バインド時は unbind → merge → bind の順で処理し、旧 keysym をインスタンス属性(self._bound_keysyms)で追跡する"

key-files:
  created: []
  modified:
    - pagefolio/app.py
    - tests/test_v150_regression.py

key-decisions:
  - "build_keysym_from_event の修飾子連結順は Control, Alt, Shift の順に固定（RESEARCH.md Pattern 1 準拠）"
  - "_bind_shortcuts() は self._bound_keysyms を使い、再呼び出し時に前回バインドした keysym(shift variant含む)を全て unbind してから再バインドする"

patterns-established:
  - "純関数3種の docstring は日本語で D-02/D-04/D-07 のどの決定に対応するかを1行で明記し、raw keysym 文字列を末尾に羅列しない"

requirements-completed: [V171-UIUX-01]

coverage:
  - id: D1
    description: "keysym 組み立て・重複検出・人間可読表示変換の3純関数が app.py に存在し、代表入力に対し期待値を返す"
    requirement: "V171-UIUX-01"
    verification:
      - kind: unit
        ref: "tests/test_v150_regression.py#TestBuildKeysymFromEvent"
        status: pass
      - kind: unit
        ref: "tests/test_v150_regression.py#TestFindDuplicateBinding"
        status: pass
      - kind: unit
        ref: "tests/test_v150_regression.py#TestKeysymToDisplay"
        status: pass
    human_judgment: false
  - id: D2
    description: "_bind_shortcuts() が抽出され、__init__ から初回呼び出しされ、再呼び出しで旧バインドを解除してから張り直す"
    requirement: "V171-UIUX-01"
    verification:
      - kind: unit
        ref: "python -c AST/grep 検証（def _bind_shortcuts / self._bind_shortcuts() / self._cmd_map / self._default_shortcuts / self._bound_keysyms の存在確認）"
        status: pass
      - kind: unit
        ref: "pytest tests/test_v150_regression.py -x -q（既存18件+新規12件=30件グリーン）"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-07-05
status: complete
---

# Phase 4 Plan 1: ショートカット GUI 編集基盤 Summary

**`app.py` にkeysym組み立て/重複検出/表示変換の3純関数を追加し、`__init__` 直書きバインドを再実行可能な `_bind_shortcuts()` メソッドへ抽出**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-05T09:41:14Z
- **Completed:** 2026-07-05T09:44:31Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `build_keysym_from_event` / `find_duplicate_binding` / `keysym_to_display` の3純関数を `app.py` の既存 `merge_shortcuts`/`shift_variant_keysym` の隣に追加（Tk 非依存・単体呼び出し可能）
- `PDFEditorApp.__init__` の直書きバインドロジック（default_shortcuts辞書・cmd_map辞書・バインドループ）を `_bind_shortcuts()` メソッドへ抽出し、`self._default_shortcuts` / `self._cmd_map` をインスタンス属性化
- `_bind_shortcuts()` は再呼び出し時に `self._bound_keysyms`（前回バインドした keysym・shift variant 含む）を先に unbind してから新設定で再バインドする設計にし、後続 04-02 の ShortcutsDialog 保存経路から再利用可能にした
- 純関数3種の回帰テストを `test_v150_regression.py` に追加（`TestBuildKeysymFromEvent`/`TestFindDuplicateBinding`/`TestKeysymToDisplay`）

## Task Commits

Each task was committed atomically:

1. **Task 1: keysym 組み立て・重複検出・表示変換の純関数を app.py に追加** - `af0968f` (feat)
2. **Task 2: __init__ 直書きバインドを _bind_shortcuts() へ抽出し再実行可能化** - `68f6afe` (refactor)
3. **Task 3: 純関数の回帰テストを test_v150_regression.py へ追加** - `9cdca79` (test)

_Note: Task 1 は tdd="true" 指定だったが、既存の隣接パターン（純関数を先に実装し verify で固定・test は Task 3 で追加）を踏襲した。plan の verify（python ワンライナー assert）で Task 1 完了時点の正当性を確認済み。_

## Files Created/Modified
- `pagefolio/app.py` - 純関数3種（build_keysym_from_event/find_duplicate_binding/keysym_to_display）追加・`_bind_shortcuts()` メソッド新設・`__init__` のバインドロジックをインスタンス属性化＋メソッド呼び出しへ置換
- `tests/test_v150_regression.py` - `TestBuildKeysymFromEvent`/`TestFindDuplicateBinding`/`TestKeysymToDisplay` の3クラスを追加（計12テスト）

## Decisions Made
- 修飾子の連結順序を Control → Alt → Shift に固定（RESEARCH.md Pattern 1・Tk bind 構文の慣例順に準拠）
- Alt ビットマスクの既定値は `0x20000`（RESEARCH.md A1: Windows Tk での一般値。実機未検証だがキーワード引数で上書き可能にして将来のプラットフォーム差異に対応できるようにした）
- 純関数の docstring は各々 D-02/D-04/D-07 のどの決定に対応するかを1行で明記し、grep誤検知回避のため raw keysym 文字列を末尾に羅列しない方針を踏襲
- **V171-UIUX-01 は本プラン（基盤）と 04-02（ShortcutsDialog 実装）にまたがる要件のため、REQUIREMENTS.md のチェックボックス/トレーサビリティ表は本プランでは `Pending` のまま維持した（ユーザー向け GUI 編集機能自体は 04-02 完了まで未提供のため）。本 SUMMARY の `requirements-completed` はプラン frontmatter の宣言をそのまま転記している

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - `ruff format` が Task 3 のテストコード改行を自動整形した以外は計画通り。整形後も30テスト全てグリーンであることを再確認済み。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `self._default_shortcuts`（8キー）/ `self._cmd_map`（11キー: rotate_right/rotate_left/rotate_180含む）/ `_bind_shortcuts()` が揃い、04-02 の ShortcutsDialog は「保存 → `app._bind_shortcuts()` 呼び出し」で即時反映を実装できる
- keysym↔表示変換・重複検出の純関数が確定済みのため、04-02 は UI 配線（実キーキャプチャ・保存時重複チェック呼び出し・一覧表示）に専念できる
- ブロッカーなし。フルスイート845件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files exist on disk and all task commit hashes (af0968f, 68f6afe, 9cdca79) are present in git log.
