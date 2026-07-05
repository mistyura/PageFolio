---
phase: 03-v1-5-0
plan: 03
subsystem: pdf-page-editing
tags: [pymupdf, fitz, tkinter, crop, rotation, undo]

# Dependency graph
requires:
  - phase: 03-01
    provides: "画像透かし_add_watermark_image（page_ops.py・同一ファイルへの追記の前提コンテキスト）"
provides:
  - "回転座標共通ヘルパー _derotate_rect（page_ops.py・黒塗り/モザイク/トリミングが共用予定）"
  - "crop_info の mm＋％表示 _format_crop_info（page_ops.py）"
  - "矩形の矢印キー微調整 _nudge_crop_rect / _redraw_crop_overlay（page_ops.py・ui_builder.py キーバインド）"
  - "数値指定（mm）トリミング compute_margin_crop_rect / _crop_by_margin（page_ops.py・ui_builder.py ボタン・lang.py キー）"
  - "PT_PER_MM 定数（constants.py・mm↔pt換算の単一情報源）"
affects: [03-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "回転座標の逆変換は page.derotation_matrix を使う共通静的メソッドへ集約し、呼び出し側は _canvas_rect_to_pdf の直後・mediabox 相対化の前に1本道で通す（D-08・二重補正防止）"
    - "オーバーレイ再描画ロジックを _redraw_crop_overlay へ抽出し、ドラッグ中(_crop_drag_move)と矢印キー微調整(_nudge_crop_rect)の両方から共用する"
    - "mm 指定系の undo は既存 bulk_crop op（適用前 cropbox キャプチャ）を再利用し、新規 op を増やさない"

key-files:
  created: []
  modified:
    - pagefolio/page_ops.py
    - pagefolio/ui_builder.py
    - pagefolio/lang.py
    - pagefolio/constants.py
    - tests/test_page_polish.py

key-decisions:
  - "_derotate_rect は page.rotation==0 のとき早期に恒等（min/max正規化のみ）を返し、90/180/270 のみ page.derotation_matrix を計算する（無回転ページでの余計な行列計算を回避）"
  - "crop_info（_format_crop_info）は _canvas_rect_to_pdf 後・derotate 前の値をそのまま使う（画面上で選択した見たままのサイズを mm 表示するのが自然なため。derotate は _crop_page 適用時のみ必要）"
  - "矢印キー微調整は preview_canvas への bind とし、_crop_drag_start 内で focus_set() してキー入力を受理できるようにする（Tk はクリック後でないとキーイベントを渡さないため）"
  - "数値指定トリミングの mm 入力は simpledialog.askfloat の4連続呼び出し（上→下→左→右）とし、専用ダイアログは作らない。基準は「現在の cropbox」（A2・RESEARCH.md で解決済みの Open Question）"
  - "_crop_by_margin の undo は新規 op を作らず既存 bulk_crop を流用（file_ops.py の _apply_inverse がすでに対称処理を実装済みのため）"

patterns-established:
  - "derotate → mediabox相対化 の適用順序固定パターンは 03-04（黒塗り/モザイクの複数矩形対応）でも _apply_page_edit 側から同じ _derotate_rect を呼ぶ形で再利用される"

requirements-completed: [V171-PAGE-03]

coverage:
  - id: D1
    description: "回転90/180/270 のページで、トリミング矩形が見たままの位置へ適用される（_derotate_rect 共通ヘルパー）"
    requirement: "V171-PAGE-03"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestDerotateRect::test_derotate_identity_when_rotation_zero"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestDerotateRect::test_derotate_rotation_90_roundtrip"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestDerotateRect::test_derotate_rotation_180_roundtrip"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestDerotateRect::test_derotate_rotation_270_roundtrip"
        status: pass
    human_judgment: false
  - id: D2
    description: "確定済み矩形を矢印キーで1pt移動、Shift+矢印で右下辺リサイズできる（D-09）"
    requirement: "V171-PAGE-03"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestCropPolish::test_nudge_move"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestCropPolish::test_nudge_resize"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestCropPolish::test_nudge_noop_when_rect_unset"
        status: pass
    human_judgment: true
    rationale: "矩形ドラッグ/矢印微調整の操作感（プレビューへの視覚的反映）は end-of-phase human-verify 対象（VALIDATION.md Manual-Only・PLAN.md verify セクション明記）。ロジック自体はユニットテストで数値検証済み。"
  - id: D3
    description: "『上下左右から何mm削るか』の余白指定で選択ページへ一括トリミングできる（D-10）"
    requirement: "V171-PAGE-03"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestMarginCrop::test_margin_crop_apply_and_undo"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestMarginCrop::test_margin_crop_basic_subtraction"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestMarginCrop::test_margin_crop_too_small_returns_none"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestMarginCrop::test_margin_crop_cancel_is_noop"
        status: pass
    human_judgment: false
  - id: D4
    description: "crop_info が「45×60mm（28%）」形式（mm換算＋ページ占有率）で表示される（D-11）"
    requirement: "V171-PAGE-03"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestFormatCropInfo::test_format_crop_info_mm_and_percent"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestFormatCropInfo::test_format_crop_info_zero_mediabox_safe"
        status: pass
    human_judgment: false
  - id: D5
    description: "mm→pt換算はPT_PER_MM単一定数に集約され、derotateは1定義のみで黒塗り/モザイク/トリミングの重複実装を禁止する（脅威登録T-3-05）"
    requirement: "V171-PAGE-03"
    verification:
      - kind: unit
        ref: "grep -c 'def _derotate_rect' pagefolio/page_ops.py (結果=1)"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-07-05
status: complete
---

# Phase 3 Plan 3: 回転/トリミング棚卸し（V171-PAGE-03）Summary

**page.derotation_matrix を使う共通ヘルパー_derotate_rectで黒塗り/モザイク/トリミングの座標ズレを構造的に解消し、矢印キー微調整・mm指定トリミング・crop_infoのmm＋%表示を実装**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-05T06:14:00Z（前プラン完了直後・読解含む）
- **Completed:** 2026-07-05T06:21:53Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `pagefolio/page_ops.py` に静的メソッド `_derotate_rect(page, x0, y0, x1, y1)` を追加。`page.rotation==0` で恒等（正規化のみ）、90/180/270 で `page.derotation_matrix` により表示座標→未回転座標へ正しく逆変換する（D-08）。`_crop_page` の単一・bulk 両分岐へ `_canvas_rect_to_pdf` 直後・mediabox 相対化前の1本道で統合し、次プラン（03-04）の黒塗り/モザイクからも再利用可能な共通ヘルパーとして確立
- `_format_crop_info` 純関数を追加し、`_crop_drag_move`（→ `_redraw_crop_overlay` へ抽出後）の crop_info 表示を「45×60mm（28%）」形式へ拡張（D-11）。`PT_PER_MM = 72/25.4` を `constants.py` に単一情報源として新設
- `_nudge_crop_rect(dx_pt, dy_pt, resize=False)` を追加。確定済み矩形を矢印キーで1pt移動、Shift+矢印で右下辺リサイズ（D-09）。オーバーレイ再描画は `_redraw_crop_overlay` へ抽出し、ドラッグ中と矢印微調整の両方から共用。`preview_canvas` へ矢印/Shift+矢印バインドを追加し、`_crop_drag_start` で `focus_set()` してキー入力を受理可能にした
- `compute_margin_crop_rect` 純関数と `_crop_by_margin` メソッドを追加（D-10）。「上下左右から何mm削るか」を `simpledialog.askfloat` の連続入力で受け取り、現在の cropbox（A2）から差し引く。undo は既存 `bulk_crop` op を再利用。差引結果が幅/高さ1pt未満なら安全側フォールバック（None・T-3-03）
- `tests/test_page_polish.py` へ `TestDerotateRect`（回転0恒等＋90/180/270 roundtrip）・`TestFormatCropInfo`・`TestCropPolish`（移動/リサイズ/未確定no-op/モードOFF）・`TestMarginCrop`（純関数＋FakeApp適用/undo/キャンセル）の4クラス計19テストを追加

## Task Commits

Each task was committed atomically:

1. **Task 1: 回転座標共通ヘルパー_derotate_rect + トリミング統合 + crop_info mm表示（D-08/D-11）** - `f4b948e` (feat)
2. **Task 2: 矩形の矢印キー微調整_nudge_crop_rect（D-09）** - `2bbbe39` (feat)
3. **Task 3: 数値指定（mm）トリミング_crop_by_margin（D-10）** - `d0a272f` (feat)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/page_ops.py` - `_derotate_rect`（静的）・`_format_crop_info`（純関数）・`_redraw_crop_overlay`（抽出）・`_nudge_crop_rect`・`compute_margin_crop_rect`（純関数）・`_crop_by_margin` を追加。`_crop_page`（単一/bulk）へ derotate 統合、`_crop_drag_start` へ `focus_set()`
- `pagefolio/ui_builder.py` - preview_canvas へ矢印/Shift+矢印キーバインド追加、トリミングセクションへ `btn_crop_margin` ボタン追加
- `pagefolio/lang.py` - ja/en 両辞書へ `btn_crop_margin`/`dlg_crop_margin_title`/`crop_margin_top`/`crop_margin_bottom`/`crop_margin_left`/`crop_margin_right` を追加
- `pagefolio/constants.py` - `PT_PER_MM = 72 / 25.4` を追加
- `tests/test_page_polish.py` - `TestDerotateRect`/`TestFormatCropInfo`/`TestCropPolish`/`TestMarginCrop`の4クラス19テストを追加

## Decisions Made
- `_derotate_rect` は回転0のとき `page.derotation_matrix` を計算せず早期returnで min/max 正規化のみ行う（無回転ページでの余計な行列計算回避・パフォーマンス配慮）
- crop_info（mm表示）は derotate 前の canvas→pdf 変換値をそのまま使う。ユーザーが画面上で見て選択したサイズをそのまま mm 表示するのが直感的なため（derotate は `_crop_page` の実適用時のみ必要という PLAN.md の役割分担どおり）
- 数値指定トリミングは専用ダイアログを新設せず `simpledialog.askfloat` の4連続呼び出し（Claude's Discretion・RESEARCH.md/CONTEXT.md で明示的に選択可とされた形）
- `_crop_by_margin` の undo は新規 op を作らず既存 `bulk_crop`（file_ops.py の `_apply_inverse` が既に対称処理実装済み）を再利用し、undo/redo ロジックの分散を避けた

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 2/Code Examples のコード例をほぼそのまま採用、PATTERNS.md の既存 analog をそのまま踏襲）。

## Issues Encountered

`zip()` に `strict=` 引数を要求する ruff B905 警告が `TestDerotateRect` のroundtripテストで発生。`strict=True` は Python 3.10+ 限定のため CLAUDE.md の Python 3.8+ 互換制約に抵触すると判断し、`zip()` を使わず `range(4)` によるインデックスループへ書き換えて解消（Rule 1 - リント整合の軽微な自動修正）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-03 完了。共通ヘルパー `_derotate_rect` が確立されたため、03-04（黒塗り/モザイク棚卸し・D-05連続適用/D-06モザイク粒度/D-07複数矩形/D-08統合）は `_apply_page_edit` からこのヘルパーを呼ぶだけで座標対応を再利用できる
- 矩形ドラッグ/矢印微調整の操作感（視覚的な見た目）は end-of-phase human-verify 対象として残存（PLAN.md verify セクション・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 822件グリーン（従来805件から+17: derotate系7・crop_polish系5・margin_crop系5）・`ruff check`/`ruff format --check` クリーン
- CLAUDE.md §既知の制限「矩形は未回転のページ座標系で適用される」は本プラン（トリミング側）では解消済みだが、黒塗り/モザイク側の統合は03-04完了後にまとめて更新予定（03-CONTEXT.md canonical_refs 明記どおり）

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/page_ops.py
- FOUND: tests/test_page_polish.py
- FOUND: .planning/phases/03-v1-5-0/03-03-SUMMARY.md
- FOUND: f4b948e (Task 1 commit)
- FOUND: 2bbbe39 (Task 2 commit)
- FOUND: d0a272f (Task 3 commit)
