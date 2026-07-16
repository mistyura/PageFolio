---
phase: 05-blob-shortcutsdialog
plan: 01
subsystem: infra
tags: [pagination, lru-cache, ordereddict, property-testing, thumbnail-virtualization]

# Dependency graph
requires:
  - phase: 01-foundation-split
    provides: Tk/fitz 非依存の純ロジック層新設方針（pagination.py/undo_store.py の系譜）
provides:
  - "pagefolio/thumb_cache.py の LruCache（dict風API: in/[]/[]=/pop/clear/len）"
  - "pagination.py の compute_visible_range/prioritized_render_order 純関数"
  - "tests/test_selection_invariant.py（selected_pages 全ページインデックス不変条件のプロパティ風テスト）"
affects: [05-02-viewer-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk/fitz 非依存の純ロジック層への新規集約（thumb_cache.py・pagination.py 拡張）"
    - "collections.OrderedDict ベースの LRU（move_to_end/popitem(last=False)）"
    - "random.Random(seed) 駆動のプロパティ風テスト（hypothesis 不使用）"

key-files:
  created:
    - pagefolio/thumb_cache.py
    - tests/test_thumb_cache.py
    - tests/test_selection_invariant.py
  modified:
    - pagefolio/pagination.py
    - tests/test_pagination.py

key-decisions:
  - "LruCache は新規モジュール pagefolio/thumb_cache.py に配置（pagination.py は窓計算専用に責務を保つ・RESEARCH.md Open Question 1 推奨採用）"
  - "compute_visible_range/prioritized_render_order は pagination.py へ追加し新規座標系モジュールを作らない（落とし穴1回避策）"
  - "D&D シミュレーションは既存 _dnd_drop の実装どおり移動後に selected_pages を clear する挙動を踏襲"

patterns-established:
  - "Pattern: 新規純ロジックはモジュール docstring 冒頭に「Tkinter/fitz 非依存」宣言を明記する"
  - "Pattern: LRU dict風API（__contains__/__getitem__/__setitem__/pop/clear/__len__）で既存呼び出し面を無改造で維持する契約"

requirements-completed: [V180-PERF-01, V180-PERF-02, V180-PERF-03]

coverage:
  - id: D1
    description: "LruCache が LRU エビクション + recency 更新を提供する dict風コンテナ（V180-PERF-02 基盤）"
    requirement: "V180-PERF-02"
    verification:
      - kind: unit
        ref: "tests/test_thumb_cache.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "compute_visible_range/prioritized_render_order が pagination.py の Tk非依存純関数として確定（V180-PERF-01 基盤）"
    requirement: "V180-PERF-01"
    verification:
      - kind: unit
        ref: "tests/test_pagination.py::TestVisibleRange, tests/test_pagination.py::TestPrioritizedRenderOrder"
        status: pass
    human_judgment: false
  - id: D3
    description: "selected_pages 全ページインデックス不変条件がシード固定プロパティ風テストで保証される（V180-PERF-03）"
    requirement: "V180-PERF-03"
    verification:
      - kind: unit
        ref: "tests/test_selection_invariant.py::TestSelectionInvariant"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-16
status: complete
---

# Phase 5 Plan 1: Blob/仮想化基盤層（LruCache + pagination純関数 + 選択不変条件テスト）Summary

**サムネイル仮想化と selected_pages 不変条件保証の Tk/fitz 非依存基盤層を新設: OrderedDict ベース LruCache（pagefolio/thumb_cache.py）、可視範囲/優先描画順序の純関数（pagination.py）、500ページ相当のシード固定プロパティ風テスト**

## Performance

- **Duration:** 約20分
- **Started:** 2026-07-16（見積り）
- **Completed:** 2026-07-16
- **Tasks:** 3 / 3 完了
- **Files modified:** 5（新規3・変更2）

## Accomplishments
- `pagefolio/thumb_cache.py` に `LruCache` を新設。`OrderedDict` ベースで容量到達時に最古参照エントリを1件エビクトし、`__getitem__`/`__setitem__` で recency を更新する dict風 API（`__contains__`/`__getitem__`/`__setitem__`/`pop`/`clear`/`__len__`）を実装。viewer.py の既存呼び出し面（in/[]/[]=/pop/clear）が 05-02 で無改造で載る契約を確定
- `pagination.py` に `compute_visible_range(view_top, view_bottom, frame_bounds)` と `prioritized_render_order(lo, hi, vis_lo, vis_hi)` を追加。viewport 交差判定と可視範囲優先の描画順序決定を Tk 非依存純関数として確定（Tk 依存の座標収集は 05-02 の viewer 側が担う設計を踏襲）
- `tests/test_selection_invariant.py` を新設。`random.Random(seed)` 駆動で選択トグル/スクロール・窓移動/D&D 並び替え相当のランダム操作列を n_pages=500(+520) 相当・20シードでパラメトライズし、`selected_pages` が常に全ページインデックス範囲内に収まることを回帰検証

## Task Commits

Each task was committed atomically:

1. **Task 1: LruCache コンテナ新設（pagefolio/thumb_cache.py）+ ユニットテスト** - `ce5e5d1` (feat)
2. **Task 2: 可視範囲・優先描画順序の純関数を pagination.py へ追加 + ユニットテスト** - `d532219` (feat)
3. **Task 3: selected_pages 全ページインデックス不変条件のプロパティ風テスト新設** - `618518e` (test)

_Note: 本プランに TDD タスクはなし（全て通常の auto タスク）。_

## Files Created/Modified
- `pagefolio/thumb_cache.py` - `LruCache` クラス（OrderedDict ベース・Tk/fitz非依存の汎用 LRU コンテナ）
- `tests/test_thumb_cache.py` - LruCache のユニットテスト9件（エビクション・recency・pop/clear/contains/len・KeyError）
- `pagefolio/pagination.py` - `compute_visible_range`/`prioritized_render_order` 純関数を追加
- `tests/test_pagination.py` - `TestVisibleRange`/`TestPrioritizedRenderOrder` を追加（14件）
- `tests/test_selection_invariant.py` - selected_pages 不変条件のプロパティ風テスト（21件・20シード+固定520ページケース）

## Decisions Made
- LRU コンテナの配置先（D-08・RESEARCH.md Open Question 1）: 新規モジュール `pagefolio/thumb_cache.py` として独立させた。`pagination.py` は窓計算専用の責務を保ち、命名的な混乱を避ける
- `prioritized_render_order` の防御的クランプ: `vis_lo`/`vis_hi` を呼び出し側の前提を信頼せず `[lo, hi)` へ再クランプすることで、呼び出し元の実装ミスがあっても不変条件（全index1回被覆・長さ一致）を機械的に保証する
- D&D シミュレーション（Task 3）は実 `fitz.Document`/実際のページ並替えを行わず、既存 `_dnd_drop` の観測可能な挙動（移動後に `selected_pages.clear()`）のみを踏襲してモデル化。並べ替え後の index 再マッピングそのものは 05-02 以降の viewer 統合時に実データで検証される想定

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

`prioritized_render_order` のテストケース `test_visible_clamped_to_window` を作成する際、当初のクランプ期待値の計算を誤り（vis_lo が lo 未満の場合に visible がプレフィックス整列されて防御クランプの効果が見えないケースを選んでいた）、`vis_hi` が `hi` を超えるケース（`prioritized_render_order(10, 15, 12, 20)`）に差し替えて防御的クランプの意味を正しく検証できるよう修正した（コミット前に発見・修正済み）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 05-02（viewer.py 統合）が本プランの3成果物（`LruCache`・`compute_visible_range`・`prioritized_render_order`）を消費できる状態。シグネチャは本プランで確定済み
- `pytest`（全1057件）・`ruff check . && ruff format .` ともにクリーン
- ブロッカーなし

## Self-Check: PASSED

All created files verified present on disk; all task commit hashes (ce5e5d1, d532219, 618518e) verified in git log.

---
*Phase: 05-blob-shortcutsdialog*
*Completed: 2026-07-16*
