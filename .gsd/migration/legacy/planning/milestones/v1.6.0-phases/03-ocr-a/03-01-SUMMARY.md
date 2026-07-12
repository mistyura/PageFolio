---
phase: 03-ocr-a
plan: 01
subsystem: ui
tags: [tkinter, pymupdf, rotation, preview, viewer, page_ops, pagination]

# Dependency graph
requires:
  - phase: 02-pagination
    provides: reconcile_window_start による窓正規化・_refresh_all 集約点
provides:
  - H1 回転プレビュー即時反映バグ（V16-QUAL-01）の原因除去修正（_rotate_selected）
  - 回転 w/h 単体テスト（90/270°入替・180°不変）— pixmap 回転反映の回帰防止アンカー
  - H1 真因の特定記録（セレクション意味論・仮説a）
affects: [03-02, 03-03, 回転UI, ページネーション]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "回転反映テストは _make_stub（types.SimpleNamespace + __get__ バインド）で Tk 非依存に検証"
    - "回転即時反映は current_page を回転対象代表へ寄せる原因除去（描画追加でなく真因除去）"

key-files:
  created: []
  modified:
    - pagefolio/page_ops.py
    - tests/test_viewer.py

key-decisions:
  - "H1 真因はセレクション意味論（仮説a）と特定。pixmap/Canvas 層は正常（実測再確認）。"
  - "修正は page_ops.py の _rotate_selected に限定。viewer.py は無改修（真因 b でないため）。"
  - "current が targets 外のとき min(targets) へ寄せ、3ステップ順序・窓正規化・on_page_rotate を温存。"

patterns-established:
  - "回転 w/h テスト: set_rotation 後に _render_preview_pixmap を再取得し w/h 入替/不変を assert"
  - "セレクション起因の体感バグは current_page を回転対象へ整合させて原因除去する"

requirements-completed: [V16-QUAL-01]

# Metrics
duration: 約15分
completed: 2026-06-19
status: complete
---

# Phase 03 Plan 01: 体感品質・回転プレビュー即時反映（H1）Summary

**H1 回転プレビュー即時反映バグの真因をセレクション意味論と特定し、_rotate_selected で current_page を回転対象へ寄せる原因除去で修正。90/270°入替・180°不変の回転 w/h 単体テストを回帰防止アンカーとして追加。**

## Performance

- **Duration:** 約15分
- **Started:** 2026-06-19T10:42Z
- **Completed (Task 1+2):** 2026-06-19T10:56Z
- **Tasks:** 3 完了（Task 1/2 実装＋ Task 3 human-verify 承認済み）
- **Files modified:** 2

## Accomplishments
- Task 1（調査）: H1 真因をセレクション意味論（仮説a）と静的コード解析で特定。pixmap 層が回転を即時反映することを自動アサートで再確認。
- Task 2（修正）: 回転 w/h 単体テスト 3 件（90/270°入替・180°不変）を追加し、特定した真因を原因除去で修正。
- Phase 2 窓正規化（reconcile_window_start）・世代ガード非追加の制約を温存し回帰なし。

## Task 1: H1 真因特定（静的コード解析・調査結論）

> 本環境はヘッドレス（非対話）のため `python pagefolio.py` の GUI 起動は行わず、コード経路を厳密に静的解析して真因を確定した。視覚的な最終確認は Task 3（human-verify）で実機検証する。

**自動 pixmap 検証（再確認）:** `python -c "...set_rotation(90)...get_pixmap()..."` → `600 400`（`pixmap rotation OK`）。pixmap 層は回転を正しく反映。Pitfall 1 の通り pixmap 層を疑わない。

**3 条件の切り分け（コードレベル）:**

| 条件 | targets（_get_targets） | _show_preview が描画する current_page | 即時反映 | 判定 |
|------|------------------------|--------------------------------------|----------|------|
| (a) 選択なしで現在ページ回転 | `[current_page]` | current_page（= 回転対象） | される | 正常 |
| (b) current 以外を選択して回転 | `selected_pages`（current を含まない） | current_page（= 回転対象外） | **されない** | **真因** |
| (c) スクロール状態で現在ページ回転 | `[current_page]` | current_page を anchor="nw" で再描画 | される | 正常（scroll は表示位置のみ） |

**真因（特定・1案確定）:** **仮説(a) セレクション意味論**。
`_show_preview`（viewer.py 85）は常に `page_idx = self.current_page` を描画する。`_rotate_selected` は `_get_targets()`（app.py 195-196）が返す `targets`（`selected_pages` 優先）を回転するが、ユーザーが Ctrl+クリック（`_toggle_select`, viewer.py 32-37）で `current_page` と異なるページを選択していると、回転後も `_show_preview` は回転対象外の `current_page` を描画し続け、プレビューが「回らない」ように見える。単一クリック（`_single_click`, viewer.py 381-386）は `selected_pages` をクリアし `current_page=idx` にするため、その経路では回転が反映され、症状が「選択状態によって出たり出なかったり」する点とも整合する。

**仮説(b) Canvas viewport は棄却:** `_show_preview` は毎回 `delete("all")` → `create_image(pad, pad, anchor="nw")` で回転後 pixmap を左上に再描画し、`scrollregion` も新 w/h から再計算する。回転 pixmap は必ず描画されるため、(b) は最悪でもスクロール位置の見栄え問題に留まり「回転が全く反映されない」原因にはならない。

**Task 2 修正方針（原因除去・描画追加でない）:** `_rotate_selected` で `current_page` が `targets` に含まれないとき `min(targets)`（昇順先頭）へ寄せ、回転結果が即プレビューへ反映されるようにする。3ステップ順序・`reconcile_window_start`・`on_page_rotate` 発火は温存。

## Task 2: 回転 w/h テスト + 原因除去修正

- `tests/test_viewer.py` に `TestRotationReflectsInPreviewPixmap`（`test_rotate_90_swaps_wh` / `test_rotate_180_keeps_wh` / `test_rotate_270_swaps_wh`）を追加。`_make_stub` を流用し Tk 非依存で回転反映を担保（実測 600×900 → 900×600）。
- `pagefolio/page_ops.py::_rotate_selected` に「current が targets 外なら `min(targets)` へ寄せる」最小修正を追加。viewer.py は無改修。
- `_preview_gen` 世代ガードは `_show_preview` に新規追加していない（grep で viewer.py に 0 件確認）。
- `_refresh_all` は依然 `reconcile_window_start`（line 225）を `_build_thumbnails`（228）/`_show_preview`（229）の前に呼ぶ（窓正規化温存）。

**検証結果:**
- `pytest tests/test_viewer.py -k rotate -x` → 3 passed（90/270°入替・180°不変が緑）
- `pytest tests/test_viewer.py tests/test_pagination.py -x` → 76 passed（Phase 2 窓挙動の回帰なし）
- `ruff check` / `ruff format --check`（page_ops.py / test_viewer.py）→ All checks passed / already formatted

## Task Commits

各タスクは個別にアトミックコミット:

1. **Task 2 (RED アンカー): 回転 w/h 単体テスト追加** - `b3f070a` (test)
2. **Task 2 (GREEN/原因除去): H1 即時反映バグ修正** - `8714aec` (fix)

_Task 1 はコード生成のない調査タスクのため、結論を本 SUMMARY に記録（上記 Task 1 節）。_

## Task 3: 実機 UAT（human-verify チェックポイント）— APPROVED

**結果:** ✅ ユーザーにより **承認（approved）**（2026-06-19）。

`<task type="checkpoint:human-verify" gate="blocking">` の実機目視確認をユーザーが実施し、回転即時反映が正しく動作することを確認した。検証観点:

1. 単一選択回転 → 再読込・ページ送りせずプレビューがその場で回る ✅
2. 複数選択一括回転 → 現在の窓内に見えている対象サムネイルが揃って回る（窓外は D-02/Pitfall 6 通り対象外）✅
3. スクロール状態での回転 → 表示破綻なく回転後寸法で正しく表示 ✅
4. 回転後の削除・ページ送り・窓ナビ（◀▶）で Phase 2 ページネーション挙動（snap back しない・窓内不変条件）に回帰なし ✅

成功基準 V16-QUAL-01 成功基準1（回転がプレビューへ即時反映される・手動 UAT 承認）を満たした。

## Files Created/Modified
- `tests/test_viewer.py` - 回転 w/h 単体テスト 3 件（90/270°入替・180°不変）を追加
- `pagefolio/page_ops.py` - `_rotate_selected` に current を回転対象代表へ寄せる原因除去修正を追加

## Decisions Made
- H1 真因をセレクション意味論（仮説a）に1案確定し、原因除去を page_ops.py に限定した。
- viewer.py は真因(b)でないため無改修。`_preview_gen` 世代ガードは禁止事項通り追加しない。
- `current_page` の寄せ先は昇順先頭 `min(targets)`（決定的・窓追従への影響が小さい）。

## Deviations from Plan

None - plan executed exactly as written.

ヘッドレス環境のため Task 1 は GUI 起動の代わりに厳密な静的コード解析で真因を特定したが、これは実行プロンプトの指示（acceptance_criteria は自動 pixmap 検証＋真因記録のみを要求）に沿った範囲であり計画からの逸脱ではない。視覚確認は Task 3（human-verify）に委譲。

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 1/2 完了・コミット済み。回転 w/h テストと原因除去修正は緑・回帰なし。
- **Task 3（blocking human-verify チェックポイント）はユーザー承認済み（approved）**。実機 UAT で回転即時反映を確認済み。プラン 03-01 完了。
- 同 Wave の 03-02、Wave 2 の 03-03 は本プランと独立。Phase 3 の残プラン実行に進める。

## Self-Check: PASSED

- FOUND: `.planning/phases/03-ocr-a/03-01-SUMMARY.md`
- FOUND: `tests/test_viewer.py`
- FOUND: `pagefolio/page_ops.py`
- FOUND commit: `b3f070a`（test）
- FOUND commit: `8714aec`（fix）

---
*Phase: 03-ocr-a*
*Completed (Task 1+2): 2026-06-19*
