---
phase: 03-v1-5-0
plan: 04
subsystem: pdf-page-editing
tags: [pymupdf, fitz, tkinter, redact, mosaic, undo, rotation]

# Dependency graph
requires:
  - phase: 03-03
    provides: "回転座標共通ヘルパー _derotate_rect（page_ops.py・黒塗り/モザイクが再利用）"
provides:
  - "黒塗り/モザイクの連続適用（_apply_page_edit から _redact_mode_off 呼び出しを削除・D-05）"
  - "モザイク粒度スライダー mosaic_block_var/scale・_on_mosaic_block_release（settings永続化・D-06）"
  - "複数矩形一括適用 self._redact_rects・_clear_redact_rects・クリアボタン（D-07）"
  - "_apply_page_edit への _derotate_rect 統合（黒塗り/モザイクの回転座標対応・D-08）"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_apply_page_edit は対象矩形集合（_redact_rects＋crop_rect）を構築後、各矩形を _canvas_rect_to_pdf→_derotate_rect→mediabox相対化の1本道で変換してから _save_undo をループ外1回だけ呼ぶ"
    - "モードの継続（連続適用）とモード切替時の相互排他（_toggle_redact_mode/_toggle_crop_mode）は別コードパスとして明確に分離する"

key-files:
  created: []
  modified:
    - pagefolio/redact_ops.py
    - pagefolio/page_ops.py
    - pagefolio/ui_builder.py
    - pagefolio/lang.py
    - tests/test_page_polish.py
    - CLAUDE.md

key-decisions:
  - "_apply_page_edit(kind, block=None) へシグネチャ変更。block はモザイク時のみ使用し、redact 時は無視される（呼び出し側 _apply_mosaic が settings 値を解決して渡す）"
  - "複数矩形は self._redact_rects（蓄積）＋現在の self.crop_rect の合算から構築し、単一矩形の既存フロー（crop_rectのみ）との後方互換を保つ"
  - "_redact_rects/_redact_rect_overlay_ids は _toggle_redact_mode 進入時に lazy init（app.py __init__ は変更しない）。_crop_drag_end 側でも getattr 防御的初期化を二重で持たせ、テストや異常系での AttributeError を防ぐ"
  - "複数矩形の持続オーバーレイは実線アウトラインのみ（stipple省略・RESEARCH.md Open Question 2 の解決どおり）"
  - "_apply_page_edit 適用後の後片付けで _redact_mode_off は呼ばない（D-05）が、_clear_crop_overlay/_clear_redact_rects は呼ぶ（オーバーレイ・蓄積矩形は毎回クリア、モードのみ維持）"

patterns-established:
  - "_derotate_rect の呼び出しは _crop_page（03-03）と _apply_page_edit（本プラン）の2箇所に集約され、いずれも _canvas_rect_to_pdf 直後・mediabox相対化前の同一順序を守る（回転座標変換ロジックの重複実装防止・03-CONTEXT.md D-08）"

requirements-completed: [V171-PAGE-02]

coverage:
  - id: D1
    description: "黒塗り/モザイク適用後もモードが維持され、明示トグルでのみOFFになる（D-05・連続適用）"
    requirement: "V171-PAGE-02"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_redact_mode_persist_after_apply"
        status: pass
    human_judgment: false
  - id: D2
    description: "モザイク粒度スライダーで粗さを変更でき、値はsettingsに永続化される（D-06）"
    requirement: "V171-PAGE-02"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_mosaic_block_granularity_changes_output"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_mosaic_block_default_backward_compatible"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_apply_mosaic_uses_mosaic_block_setting"
        status: pass
    human_judgment: false
  - id: D3
    description: "複数矩形を追加→一括適用でき、1回のUndoで全矩形がまとめて戻る（D-07）"
    requirement: "V171-PAGE-02"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_multi_rect_apply_single_undo_restores_all"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_multi_rect_apply_calls_save_undo_once"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_crop_drag_end_accumulates_multi_rect"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_clear_redact_rects_removes_accumulated_state"
        status: pass
    human_judgment: false
  - id: D4
    description: "回転90/180/270ページで黒塗り/モザイク矩形が見たままの位置へ適用される（D-08・_derotate_rect統合）"
    requirement: "V171-PAGE-02"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_redact_derotate_position_matches_rotated_page"
        status: pass
    human_judgment: true
    rationale: "derotate統合の数値ロジック（_derotate_rect経由でrect座標が期待値に一致）はユニットテストで検証済みだが、実プレビュー上でのドラッグ操作感・見た目の位置一致は end-of-phase human-verify 対象（03-PLAN.md Task2 verify セクション・VALIDATION.md Manual-Only 明記）"
  - id: D5
    description: "複数矩形一括適用でも各矩形の下地コンテンツが個別に実削除され、情報漏えいがない（T-3-04）"
    requirement: "V171-PAGE-02"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestRedactPolish::test_multi_rect_apply_single_undo_restores_all（適用前後のget_text比較で両矩形とも実削除を確認）"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-07-05
status: complete
---

# Phase 3 Plan 4: 黒塗り/モザイク棚卸し（V171-PAGE-02）Summary

**黒塗り/モザイクを連続適用可能にし、モザイク粒度スライダー・複数矩形一括適用（1回undo）・page.derotation_matrixによる回転座標対応を`_apply_page_edit`へ統合**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-05T06:26:00Z（前プラン03-03完了直後・読解含む）
- **Completed:** 2026-07-05T06:44:02Z
- **Tasks:** 2
- **Files modified:** 6（うちCLAUDE.md追記1）

## Accomplishments
- `_apply_page_edit` の後片付けから `_redact_mode_off()` 呼び出しのみを削除し、黒塗り/モザイク適用後もモードが維持される連続適用を実現（D-05）。トリミングとの相互排他ロジック（`_toggle_redact_mode`/`_toggle_crop_mode`）は不変
- `_mosaic_page` に `block` 引数を追加（既定 `MOSAIC_BLOCK`・後方互換）。`ui_builder.py` にモザイク粒度スライダー（`mosaic_block_var`/`mosaic_block_scale`）を追加し、`_on_mosaic_block_release` で `settings["mosaic_block"]` へ永続化（D-06）
- `_apply_page_edit` を複数矩形対応へ改修。`self._redact_rects`（ドラッグ完了ごとに蓄積・`_crop_drag_end` の redact モード分岐）＋現在の `crop_rect` から対象矩形集合を構築し、`_save_undo` はターゲットページ集合に対しループの外側で必ず1回だけ呼ぶ（D-07・Pitfall4）。「クリア」ボタン（`_clear_redact_rects`）で全矩形・オーバーレイを削除可能
- 各矩形の座標変換に 03-03 で確立した `_derotate_rect`（`page.derotation_matrix`）を統合し、`_canvas_rect_to_pdf → _derotate_rect → mediabox相対化` の1本道で黒塗り/モザイク/トリミングの3操作すべてが回転座標に対応（D-08）。CLAUDE.md の既知の制限「矩形は未回転のページ座標系で適用される」の記述を解消後の内容へ更新
- `tests/test_page_polish.py` へ `TestRedactPolish` を追加（連続適用・モザイク粒度差・後方互換・settings連携・複数矩形一括適用+単一undo・`_save_undo`単一呼出し・回転90度derotate位置一致・クリア機能・ドラッグ蓄積・LANGパリティの計13テスト）

## Task Commits

Each task was committed atomically:

1. **Task 1: 連続適用（D-05）＋モザイク粒度スライダー（D-06）** - `128e938` (feat)
2. **Task 2: 複数矩形の一括適用（D-07）＋回転座標対応の統合（D-08）** - `dabcdec` (feat)
3. **CLAUDE.md既知の制限のD-08解消後更新** - `6669fa3` (docs)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/redact_ops.py` - `_apply_mosaic`/`_apply_page_edit`/`_mosaic_page` の改修、`_on_mosaic_block_release`・`_clear_redact_rects` を追加、`_toggle_redact_mode`/`_redact_mode_off` へ複数矩形状態のlazy init/クリアを統合
- `pagefolio/page_ops.py` - `_crop_drag_end` へ redact モードの複数矩形蓄積分岐（`_redact_rects`・持続オーバーレイ）を追加
- `pagefolio/ui_builder.py` - モザイク粒度スライダーと「クリア」ボタンを f3b セクションへ追加
- `pagefolio/lang.py` - `mosaic_block_label`/`btn_redact_clear` を ja/en 両辞書へ追加
- `tests/test_page_polish.py` - `TestRedactPolish` クラス（13テスト）を追加
- `CLAUDE.md` - 既知の制限の「矩形は未回転のページ座標系で適用される」を D-08 解消後の内容（見たままの位置に適用）へ更新、D-05/D-06/D-07 の挙動を追記

## Decisions Made
- `_apply_page_edit(kind, block=None)` へシグネチャ変更。block はモザイク時のみ意味を持ち、`_apply_mosaic` が `settings.get("mosaic_block", MOSAIC_BLOCK)` を解決して渡す（`MOSAIC_BLOCK` 定数は不変のまま既定値として温存）
- 複数矩形は `self._redact_rects`（蓄積）＋現在の `self.crop_rect` の合算から構築し、単一矩形のみの既存フロー（crop_rectのみセット）との後方互換を保った
- `_redact_rects`/`_redact_rect_overlay_ids` は `_toggle_redact_mode` 進入時に lazy init（app.py `__init__` は変更しない）。`_crop_drag_end` 側でも `getattr` 防御的初期化を二重に持たせ、異常系での AttributeError を防止
- 複数矩形の持続オーバーレイは実線アウトラインのみ（stipple省略・RESEARCH.md Open Question 2 の解決どおり採用）
- `_apply_page_edit` 適用後の後片付けで `_redact_mode_off` は呼ばない（D-05）が、`_clear_crop_overlay`/`_clear_redact_rects` は呼ぶ（オーバーレイ・蓄積矩形は毎回クリアしモードのみ維持する設計）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 2/4・PATTERNS.md の既存 analog をほぼそのまま採用）。

## Issues Encountered

`ruff format` が `ui_builder.py` の `.bind("<ButtonRelease-1>", self._on_mosaic_block_release)` を1行へ再整形（改行折返しの自動整形差分）。フォーマッタの自動整形結果をそのまま採用（Rule 1 - リント整合の軽微な自動修正）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-02 完了。黒塗り/モザイクの棚卸し4項目（D-05〜D-08）すべて実装済み
- `_derotate_rect` の実プレビュー上での回転座標対応（見た目の位置一致）・複数矩形の連続ドラッグ操作感は end-of-phase human-verify 対象として残存（03-CONTEXT.md/03-RESEARCH.md・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 833件グリーン（従来822件から+11）・`ruff check`/`ruff format --check` クリーン
- Phase 3 の全4プラン（03-01〜03-04）完了。V171-PAGE-01（03-01）・V171-TEST-01（03-02）・V171-PAGE-03（03-03）・V171-PAGE-02（本プラン03-04）で全要件充足。Phase 3 完了、Phase 4（UI/UX磨き込み+既知バグ棚卸し）へ進行可能

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/redact_ops.py
- FOUND: pagefolio/page_ops.py
- FOUND: pagefolio/ui_builder.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_page_polish.py
- FOUND: CLAUDE.md
- FOUND: 128e938 (Task 1 commit)
- FOUND: dabcdec (Task 2 commit)
- FOUND: 6669fa3 (CLAUDE.md update commit)
