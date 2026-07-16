---
phase: 05-blob-shortcutsdialog
plan: 02
subsystem: ui
tags: [tkinter, thumbnail-virtualization, lru-cache, pagination, debounce]

# Dependency graph
requires:
  - phase: 05-blob-shortcutsdialog (plan 01)
    provides: "pagefolio/thumb_cache.py の LruCache + pagination.py の compute_visible_range/prioritized_render_order 純関数"
  - phase: 05-blob-shortcutsdialog (plan 04)
    provides: "app.py の共存改修面（ShortcutsDialog WR-01/WR-02、同一ファイルの別セクション）"
provides:
  - "constants.THUMB_CACHE_MAX(300) 定数"
  - "app.py: self.thumb_cache = LruCache(THUMB_CACHE_MAX) + self._thumb_scroll_after"
  - "viewer.py: _visible_local_range/_thumb_yscroll/_on_thumb_scroll/_render_visible_thumbs"
  - "viewer.py: _build_thumbnails の可視範囲優先＋アイドル先読みの2段レンダリング改修"
  - "ui_builder.py: thumb_canvas yscrollcommand の _thumb_yscroll 配線"
affects: [phase-06-quality-assurance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "05-01 で確定した純ロジック層（LruCache/compute_visible_range/prioritized_render_order）を viewer.py の薄い Tk 依存ラッパーから消費する統合パターン"
    - "スクロールデバウンス（root.after_cancel + root.after(150,...)）と世代カウンタ併用による陳腐化描画破棄"

key-files:
  created: []
  modified:
    - pagefolio/constants.py
    - pagefolio/app.py
    - pagefolio/viewer.py
    - pagefolio/ui_builder.py
    - tests/test_viewer.py

key-decisions:
  - "THUMB_CACHE_MAX=300（PAGE_SIZE_MAX=100 の3倍・D-05/D-06 の例示値をそのまま採用）。ユーザー設定 UI は追加しない"
  - "デバウンス待機時間は D-02 の例示どおり150msを採用（実装時チューニング可・Claude's Discretion）"
  - "_build_thumbnails は visible_order/rest_order の2チェーン（after(0)/after_idle）に分割し、prioritized_render_order の返り値をスライスして境界を決定する形で実装（新規座標系を作らずpagination純関数のみで完結）"
  - "_thumb_placeholder_labels を self へ保持し、_render_visible_thumbs からも同じプレースホルダ参照を再利用（窓ローカル添字 i-lo の参照契約を維持）"

patterns-established:
  - "Pattern: Tk座標収集ヘルパー（_visible_local_range）は pagination.compute_visible_range へ委譲し、Canvas未レイアウト時は明示的に窓全体へフォールバックする（dnd.py._dnd_dest_index と同型の分離）"

requirements-completed: [V180-PERF-01, V180-PERF-02]

coverage:
  - id: D1
    description: "_build_thumbnails が pagination.prioritized_render_order を用い、可視範囲ページを非可視の窓内ページより先にレンダリングする（V180-PERF-01）"
    requirement: "V180-PERF-01"
    verification:
      - kind: unit
        ref: "tests/test_viewer.py::TestPrioritizedRenderOrderViewerIntegration::test_visible_pages_rendered_before_rest_of_window"
        status: pass
      - kind: unit
        ref: "tests/test_pagination.py::TestPrioritizedRenderOrder"
        status: pass
    human_judgment: false
  - id: D2
    description: "サムネイル Canvas のスクロールがデバウンス（既定150ms）で _render_visible_thumbs を起動し、thumb_cache ヒット分は即時反映・ミス分のみ _get_thumb_photo でレンダリングし、_thumb_gen 世代ガードで陳腐化描画を破棄する（D-02）"
    requirement: "V180-PERF-01"
    verification:
      - kind: unit
        ref: "tests/test_viewer.py::TestRenderVisibleThumbsGenGuard（gen不一致No-op/doc未オープンNo-op/キャッシュヒット分の即時反映を検証する3ケース）"
        status: pass
    human_judgment: false
  - id: D3
    description: "self.thumb_cache が LruCache(THUMB_CACHE_MAX) インスタンスであり、既存の _invalidate_thumb_cache/_get_thumb_photo 呼び出し面（in/[]/[]=/pop/clear）が無改造で動作する（V180-PERF-02）"
    requirement: "V180-PERF-02"
    verification:
      - kind: unit
        ref: "pytest tests/test_pagination.py tests/test_viewer.py -x（全89→95件グリーン）"
        status: pass
      - kind: unit
        ref: "pytest 全1078件（既存1072件+新規6件）グリーン・回帰なし"
        status: pass
    human_judgment: false
  - id: D4
    description: "_visible_local_range が Canvas 未レイアウト（winfo_height()<=1）・フレーム未生成時に窓全体へフォールバックし、可視範囲・描画順序は selected_pages へ一切窓ローカル添字を書き込まない（prohibition統合）"
    requirement: "V180-PERF-01"
    verification:
      - kind: unit
        ref: "tests/test_viewer.py::TestVisibleLocalRangeFallback（フレーム空→(0,0)・未レイアウト→窓全体の2ケース）"
        status: pass
    human_judgment: false

duration: 約20分
completed: 2026-07-16
status: complete
---

# Phase 5 Plan 2: サムネイル仮想化統合（可視範囲優先描画 + スクロールデバウンス + LRU化）Summary

**05-01 の純ロジック基盤（LruCache/pagination純関数）を viewer.py へ統合し、_build_thumbnails を可視範囲優先→アイドル先読みの2段レンダリングへ改修。thumb_canvas スクロールを150msデバウンス化し thumb_cache を LruCache(300) で有界化した。**

## Performance

- **Duration:** 約20分
- **Started:** 2026-07-16（見積り）
- **Completed:** 2026-07-16
- **Tasks:** 2 / 2 完了
- **Files modified:** 5

## Accomplishments
- `pagefolio/constants.py` に `THUMB_CACHE_MAX = 300`（最大窓サイズ100の3倍・D-05/D-06）を追加
- `pagefolio/app.py` の `self.thumb_cache` を `LruCache(THUMB_CACHE_MAX)` インスタンスへ置換し、スクロールデバウンス用 `self._thumb_scroll_after` を新設。`_invalidate_thumb_cache`/`_get_thumb_photo` の既存呼び出し面（`in`/`[]`/`[]=`/`pop`/`clear`）は無改造で動作
- `pagefolio/viewer.py` に `_visible_local_range()`（Tk座標収集のみ担当し比較は `pagination.compute_visible_range` へ委譲）・`_thumb_yscroll`（yscrollcommandラッパー）・`_on_thumb_scroll`（150msデバウンススケジューラ）・`_render_visible_thumbs`（世代ガード付き可視範囲再描画）を新設
- `_build_thumbnails` を `pagination.prioritized_render_order` による2段レンダリング（可視範囲は `root.after(0)` 連鎖・窓内残りは `root.after_idle` 連鎖）へ改修。`_thumb_gen` 世代ガードはそのまま維持
- `pagefolio/ui_builder.py` の thumb_canvas `yscrollcommand` を `self._thumb_yscroll` へ配線し、既存 `<MouseWheel>` バインドの後段でも `_on_thumb_scroll` を呼ぶよう改修
- `tests/test_viewer.py` に世代ガード（gen不一致No-op・doc未オープンNo-op・キャッシュヒット分の即時反映）・`_visible_local_range` フォールバック分岐（フレーム空/未レイアウト）・`prioritized_render_order` の描画順序契約の3系統・計6テストを追加

## Task Commits

Each task was committed atomically:

1. **Task 1: THUMB_CACHE_MAX 定数追加 + app.py thumb_cache の LruCache 化** - `0ed12ee` (feat)
2. **Task 2: viewer 優先度付き2段レンダリング + スクロールデバウンス配線 + テスト** - `d44657c` (feat)

_Note: 本プランに TDD タスクはなし（全て通常の auto タスク）。_

## Files Created/Modified
- `pagefolio/constants.py` - `THUMB_CACHE_MAX` 定数を追加
- `pagefolio/app.py` - `thumb_cache` を `LruCache` 化・`_thumb_scroll_after` 属性新設・import 追加（`THUMB_CACHE_MAX`/`LruCache`）
- `pagefolio/viewer.py` - `_visible_local_range`/`_thumb_yscroll`/`_on_thumb_scroll`/`_render_visible_thumbs` 新設・`_build_thumbnails` を2段レンダリングへ改修・`compute_visible_range`/`prioritized_render_order` の import 追加
- `pagefolio/ui_builder.py` - thumb_canvas の `yscrollcommand`/`MouseWheel` バインドをデバウンス起点へ配線（`self._thumb_scrollbar` を self 保持へ変更）
- `tests/test_viewer.py` - サムネイル仮想化の世代ガード・フォールバック・描画順序契約テストを追加（6件）

## Decisions Made
- `THUMB_CACHE_MAX` は CONTEXT.md の例示値300をそのまま採用（`pagination.PAGE_SIZE_MAX`(100) の3倍・D-05のスラッシング防止条件を満たす）
- デバウンス待機時間は例示どおり150msを採用（Claude's Discretion・実装時チューニング可の位置づけ）
- `_build_thumbnails` は `prioritized_render_order` が返す1本のリストを可視件数でスライスし、可視分は `after(0)` 連鎖、残りは `after_idle` 連鎖という2つの再帰クロージャに分割する実装を採用。これにより総仕事量は現行と同じ（全 index を1回ずつ処理）を保ったまま優先度付けを実現した
- 可視件数の算出は `prioritized_render_order` 内部と同一のクランプ式（`max(lo, min(vis, hi))`）を `_build_thumbnails` 側でも再現し、可視/残りの分割境界を関数の実装と一致させた（関数のブラックボックス性を壊さず整合性を保証）
- `_thumb_placeholder_labels` を新規に `self` 属性として保持し、`_build_thumbnails`（初回描画）と `_render_visible_thumbs`（デバウンス後描画）の両方から同じプレースホルダ参照（窓ローカル添字 `i - lo`）を共有する設計とした

## Deviations from Plan

None - plan executed exactly as written（2タスクとも計画の action どおりに実装し、acceptance_criteria を全て満たした）。

## Issues Encountered

None. `ruff check . && ruff format .` はクリーン、`pytest` は既存1072件 + 新規6件の計1078件が全通過（回帰なし）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V180-PERF-01/02（サムネイル可視範囲優先描画・thumb_cache LRU化）が本プランで解消済み。05-01 の V180-PERF-03（selected_pages 不変条件プロパティテスト）と合わせ、堅牢性フェーズの Performance 系3要件（PERF-01〜03）は完了
- 05-01/05-03/05-04 は既に完了済みのため、本プラン（05-02）の完了で Phase 5（堅牢性強化）は全4プラン・2ウェーブとも完了
- 手動確認（大量ページPDFでのスクロール体感・非ブロッキング）は次回実機検証時に実施可能

---
*Phase: 05-blob-shortcutsdialog*
*Completed: 2026-07-16*

## Self-Check: PASSED

- FOUND: pagefolio/constants.py
- FOUND: pagefolio/app.py
- FOUND: pagefolio/viewer.py
- FOUND: pagefolio/ui_builder.py
- FOUND: tests/test_viewer.py
- FOUND: .planning/phases/05-blob-shortcutsdialog/05-02-SUMMARY.md
- FOUND commit: 0ed12ee
- FOUND commit: d44657c
