---
phase: 05-blob-shortcutsdialog
verified: 2026-07-16T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正）Verification Report

**Phase Goal:** 大量ページ PDF でもサムネイル描画が高速に保たれ、長時間運用でも Blob リークが検出可能で、ShortcutsDialog の UI 表示・入力衝突バグが解消される。
**Verified:** 2026-07-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 大量ページ PDF で窓内サムネイルが可視範囲のみ実体化され、既存 `pagination.py` 窓表示の外層契約（local↔global 変換）を変えずに描画が高速化される | ✓ VERIFIED | `pagefolio/pagination.py:124-170` に `compute_visible_range`/`prioritized_render_order` を追加（`window_bounds`/`to_global` 等の既存 API は無改造）。`pagefolio/viewer.py:282-395` の `_visible_local_range`/`_build_thumbnails`/`_render_visible_thumbs` がこれらを消費し、可視範囲を `after(0)` 連鎖で先に描画・残りを `after_idle` で先読み。`tests/test_viewer.py::TestPrioritizedRenderOrderViewerIntegration`・`TestRenderVisibleThumbsGenGuard`・`TestVisibleLocalRangeFallback` がグリーン |
| 2 | `thumb_cache` に LRU eviction が導入され、大量ページを開いてもメモリ使用が有界に保たれる | ✓ VERIFIED | `pagefolio/thumb_cache.py` に `LruCache`（OrderedDict ベース、`__setitem__` で `popitem(last=False)` エビクト、`__getitem__` で `move_to_end`）。`pagefolio/constants.py:49` `THUMB_CACHE_MAX = 300`。`pagefolio/app.py:29,189` で `self.thumb_cache = LruCache(THUMB_CACHE_MAX)` に置換済み（旧 `self.thumb_cache = {}` は残存せず）。`tests/test_thumb_cache.py`（9件）グリーン |
| 3 | `selected_pages` 全ページインデックス不変条件・D&D・窓表示との整合が回帰テストで保証される | ✓ VERIFIED | `tests/test_selection_invariant.py` が `random.Random(seed)` 駆動で 20 シード × n_pages=500(+520 固定ケース) の選択トグル/スクロール/D&D 相当操作列を実行し、各ステップで `selected_pages` の全要素が `[0, n_pages)` に収まることをアサート（21件、全通過） |
| 4 | Blob ライフサイクルのリーク検出ロギングが強化され、Windows AV スキャンによる `os.unlink` の `PermissionError` 発生時も回帰テストでリークなしと確認できる | ✓ VERIFIED | `pagefolio/undo_store.py`: `MemBlob`/`FileBlob` に `_released` フラグ + `__del__`（`sys.is_finalizing()` 早期 return・`except Exception as e:` で握り潰し・リーク時 `logger.warning`）。二重解放も `release()` 冒頭でガードし warning のみで実処理をスキップ。`tests/test_undo_stress.py::TestBlobLeakDetection` の3項目（PermissionError mock 非クラッシュ・double-release 連鎖検出・tmpdir 残留0＋偽陽性なし）が全通過 |
| 5 | ShortcutsDialog でキャプチャ対象を切り替えても前行の「キーを押してください」表示が残留せず、修飾キーなしの単キー登録が通常入力ウィジェットと衝突しなくなる | ✓ VERIFIED | WR-01: `pagefolio/dialogs/shortcuts.py:189-193` `_start_capture` が旧 `_capturing_cmd` を `prev_cmd` へ退避し `_end_capture()` 後に `_refresh_row(prev_cmd)` を呼ぶ。WR-02: `pagefolio/app.py:91,94-106` `should_suppress_for_focused_input` 純関数（Ctrl/Alt 含む組合せは常に非抑止・入力系クラスのみ抑止）+ `_bind_shortcuts:264-272` の `_make_guarded_handler` が `root.focus_get()` の None を空文字列へフォールバックしつつガードを適用。`tests/test_shortcuts_dialog.py`（12件）全通過 |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/thumb_cache.py` | LruCache（Tk/fitz非依存） | ✓ VERIFIED | 存在・`import tkinter`/`import fitz` なし・dict風API全実装 |
| `pagefolio/pagination.py` | compute_visible_range / prioritized_render_order | ✓ VERIFIED | 両関数存在、fitz/tkinter import なし |
| `pagefolio/constants.py` | THUMB_CACHE_MAX | ✓ VERIFIED | 値300（PAGE_SIZE_MAX=100 超） |
| `pagefolio/viewer.py` | 優先度付き2段レンダリング + デバウンス | ✓ VERIFIED | `_visible_local_range`/`_thumb_yscroll`/`_on_thumb_scroll`/`_render_visible_thumbs` 存在・`_build_thumbnails` が `prioritized_render_order` を呼ぶ |
| `pagefolio/ui_builder.py` | yscrollcommand 配線 | ✓ VERIFIED | `yscrollcommand=self._thumb_yscroll` |
| `pagefolio/undo_store.py` | _released + __del__ | ✓ VERIFIED | MemBlob/FileBlob 両方に実装 |
| `pagefolio/dialogs/shortcuts.py` | WR-01 修正 | ✓ VERIFIED | `_start_capture` に prev_cmd 復元 |
| `pagefolio/app.py` | WR-02 フォーカスガード | ✓ VERIFIED | `should_suppress_for_focused_input` + `_bind_shortcuts` 配線 |
| `tests/test_thumb_cache.py`, `tests/test_pagination.py`, `tests/test_selection_invariant.py`, `tests/test_viewer.py`, `tests/test_undo_stress.py`, `tests/test_shortcuts_dialog.py` | 各要件の回帰テスト | ✓ VERIFIED | 全て存在・非stub・全件グリーン |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app.py.__init__` | `LruCache(THUMB_CACHE_MAX)` | `self.thumb_cache = LruCache(THUMB_CACHE_MAX)` | ✓ WIRED | app.py:189 |
| `ui_builder.py` yscrollcommand | `viewer._thumb_yscroll` | `self.thumb_canvas.configure(yscrollcommand=self._thumb_yscroll)` | ✓ WIRED | ui_builder.py:234 |
| `viewer._on_thumb_scroll` | `_render_visible_thumbs` (デバウンス) | `root.after(150, self._render_visible_thumbs, self._thumb_gen)` | ✓ WIRED | viewer.py:376-382 |
| `viewer._build_thumbnails` | `pagination.prioritized_render_order` | 呼び出し + スライス分割（after(0)/after_idle） | ✓ WIRED | viewer.py:323 |
| `app._bind_shortcuts` 発火ラムダ | `should_suppress_for_focused_input` | `_make_guarded_handler` 内でガード判定後に `f()` | ✓ WIRED | app.py:264-272 |
| `file_ops.py` の blob.release() 呼び出し面 | `undo_store.py` の release()/__del__ | 無改造のまま呼び出される | ✓ WIRED | file_ops.py 未改造・test_undo_stress.py で経路確認 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V180-PERF-01 | 05-01, 05-02 | 窓内サムネイル可視範囲のみ実体化 | ✓ SATISFIED | pagination純関数 + viewer統合 + テスト |
| V180-PERF-02 | 05-01, 05-02 | thumb_cache LRU eviction | ✓ SATISFIED | LruCache + THUMB_CACHE_MAX配線 |
| V180-PERF-03 | 05-01 | selected_pages 不変条件回帰テスト | ✓ SATISFIED | test_selection_invariant.py |
| V180-ROBUST-01 | 05-03 | Blobリーク検出 + AV衝突回帰テスト | ✓ SATISFIED | undo_store.py改修 + TestBlobLeakDetection |
| V180-ROBUST-03 | 05-04 | ShortcutsDialog WR-01/WR-02解消 | ✓ SATISFIED | shortcuts.py/app.py改修 + test_shortcuts_dialog.py |

REQUIREMENTS.md のトレーサビリティ表（Phase 5 行）と完全一致。孤立要件なし。

### Anti-Patterns Found

フェーズ変更対象ファイル（`pagefolio/thumb_cache.py`, `pagination.py`, `viewer.py`, `app.py`, `constants.py`, `ui_builder.py`, `undo_store.py`, `dialogs/shortcuts.py`）を走査。`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` 系マーカーなし。ブロッカーなし。

コードレビュー（05-REVIEW.md）は critical 0・warning 3・info 2 を報告済み（WR-01: MemBlob/FileBlob の release後load挙動不整合、WR-02: Combobox が `_INPUT_WIDGET_CLASSES` 未収録、WR-03: heap-growth閾値テストのフレーク性リスク、IN-01/IN-02: 死んだ定数・Shift-variant重複検出漏れ）。いずれも本フェーズの5つの成功基準を無効化するものではなく、既存のコードレビュー記録として引き継がれるのみ（gaps ではなく品質改善候補）。

### Behavioral Spot-Checks / Full Test Run

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| フェーズ関連テストスイート | `pytest tests/test_thumb_cache.py tests/test_pagination.py tests/test_selection_invariant.py tests/test_viewer.py tests/test_undo_stress.py tests/test_shortcuts_dialog.py -q` | 144 passed | ✓ PASS |
| 全体回帰（1回のみ実行） | `pytest -q` | 1078 passed | ✓ PASS |
| Lint | `ruff check .` | All checks passed | ✓ PASS |
| コミットハッシュ実在確認 | `git cat-file -e <hash>` ×10（05-01〜05-04の全タスクコミット） | 全て存在 | ✓ PASS |

### Human Verification Required

なし。全ての must-have が自動検証で確認され、UI体感（大量ページPDFでのスクロール描画速度）は各PLANの `<verification>` で「手動確認（任意・非ブロッキング）」と明記されており、必須の human-verify 項目としては計画されていない。

### Deferred Items (informational — 05-03発見の既存バグ)

Phase 5 のスコープ外・後続フェーズの success criteria とも一致しないため「deferred」として次アクション候補に留め、gapsには計上しない。

| # | Item | Note |
|---|------|------|
| 1 | `pagefolio/file_ops.py` の insert→undo→redo→undo（2回目のundo）でページが重複するバグ | 05-03 Task 2 で発見。`undo_store.py`/Blobライフサイクルとは無関係（release()は常に1回ずつ正しく呼ばれることを確認済み）。`.planning/phases/05-blob-shortcutsdialog/deferred-items.md` に原因・再現コード・推奨対応を記録済み。Phase 6（QA-02/03/04）の goal/success criteriaとは一致しないため次期マイルストーン以降のクイックタスク候補として残す |

### Gaps Summary

なし。ROADMAP.md の5つの Success Criteria、REQUIREMENTS.md の5要件（V180-PERF-01/02/03, V180-ROBUST-01/03）、各PLANのmust_havesが全て codebase 上で確認された。全1078件のpytestとruffがクリーン。コードレビューのwarning/info 5件は品質改善候補として記録されるのみでブロッカーではない。

---

_Verified: 2026-07-16_
_Verifier: Claude (gsd-verifier)_
