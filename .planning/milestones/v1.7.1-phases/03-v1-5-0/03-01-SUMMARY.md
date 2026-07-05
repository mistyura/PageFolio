---
phase: 03-v1-5-0
plan: 01
subsystem: pdf-page-editing
tags: [pymupdf, fitz, pillow, tkinter, watermark, undo]

# Dependency graph
requires: []
provides:
  - "画像（PNG/JPEG）透かしをページへ焼き込む _add_watermark_image / _watermark_image_rect（page_ops.py）"
  - "テキスト透かしボタン直後に結線された画像透かしボタン（ui_builder.py）"
  - "btn_watermark_image LANG キー（ja/en）"
  - "tests/test_page_polish.py（Phase 3 新規テスト専用ファイル・D-15）"
affects: [03-02, 03-03, 03-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "テキスト透かしと同型の page_edit undo フロー（_check_doc→_get_targets→_save_undo("page_edit")→適用ループ→_invalidate_thumb_cache→_refresh_all）を画像透かしへ複製"
    - "Pillow でアルファチャンネルを事前合成してから insert_image で焼き込む（insert_image 自体には不透明度引数がないため）"

key-files:
  created:
    - tests/test_page_polish.py
  modified:
    - pagefolio/page_ops.py
    - pagefolio/ui_builder.py
    - pagefolio/lang.py

key-decisions:
  - "PNG は既存アルファを0.5乗算、JPEGはconvert(\"RGBA\")後に均一128(=50%)をputalphaで付与（D-03）"
  - "_watermark_image_rect は幅50%縮小を既定としつつ、縦長画像で高さがページ高さ90%を超える場合は高さ基準へクランプ（Claude's Discretion）"
  - "undo は _save_undo(\"page_edit\", targets=targets) を適用ループの外側で1回だけ呼ぶ（page_ops.py 内 grep で出現1回を確認）"

patterns-established:
  - "画像系操作の undo/redo 検証は page.get_images() で行う（get_text() では画像の存在を検出できないため・Pitfall 5）"

requirements-completed: [V171-PAGE-01]

coverage:
  - id: D1
    description: "PNG/JPEG画像を選択ページ中央・幅約50%・50%透過で焼き込める"
    requirement: "V171-PAGE-01"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermark::test_png_watermark_embeds_image_and_undo_removes_it"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermark::test_jpeg_watermark_embeds_image"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermarkRect::test_center_and_half_width_landscape"
        status: pass
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermarkRect::test_clamped_for_extreme_tall_image"
        status: pass
    human_judgment: false
  - id: D2
    description: "画像透かし追加後、Undo で適用前のページ内容へ完全復元される"
    requirement: "V171-PAGE-01"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermark::test_png_watermark_embeds_image_and_undo_removes_it"
        status: pass
    human_judgment: false
  - id: D3
    description: "破損/非対応画像を選んでもクラッシュせず messagebox.showerror で通知される（T-3-01 DoS 耐性）"
    requirement: "V171-PAGE-01"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermark::test_corrupted_image_shows_error_without_crash"
        status: pass
    human_judgment: false
  - id: D4
    description: "透かしボタンがUIに追加され_add_watermark_imageに結線、LANG ja/enパリティ維持"
    requirement: "V171-PAGE-01"
    verification:
      - kind: unit
        ref: "tests/test_page_polish.py::TestImageWatermarkLang::test_key_exists_in_both_languages"
        status: pass
      - kind: unit
        ref: "tests/test_lang_parity.py (フルスイート内で実行・キー数一致)"
        status: pass
    human_judgment: false
  - id: D5
    description: "画像透かしの見た目（中央・約50%幅・半透明表示）が実PDFビューアで正しく描画される（RESEARCH.md A1）"
    verification: []
    human_judgment: true
    rationale: "insert_image が書き出す SMask の半透明表示は実際のPDFビューア/プレビューでの実描画確認が必要。ヘッドレスなunitテストでは get_images() の存在確認のみが可能で、視覚的な透過度・配置の正しさまでは検証できない。VALIDATION.md Manual-Only 項目・end-of-phase human-verify 対象（03-CONTEXT.md/03-RESEARCH.md A1 明記）。"

# Metrics
duration: 6min
completed: 2026-07-05
status: complete
---

# Phase 3 Plan 1: 画像透かし（V171-PAGE-01）Summary

**PNG/JPEG画像をページ中央・幅約50%・50%透過で焼き込む `_add_watermark_image`/`_watermark_image_rect` を実装し、既存テキスト透かしと同型の page_edit undo で完全復元可能にした**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-05T05:50:37Z
- **Completed:** 2026-07-05T05:56:00Z
- **Tasks:** 2
- **Files modified:** 4（うち新規1）

## Accomplishments
- `pagefolio/page_ops.py` に `_add_watermark_image`（ボタン→ファイル選択→即適用→page_edit undo）と `_watermark_image_rect`（中央配置・幅50%縮小・縦長クランプの純関数）を追加
- PNG の既存アルファは0.5乗算、JPEGはRGBA変換後に均一50%透過を付与（D-03）。破損/非対応画像は `try/except Exception` で保護し `messagebox.showerror` へフォールバック（T-3-01）
- `ui_builder.py` にテキスト透かしボタン直後で `_add_watermark_image` へ結線した画像透かしボタンを追加、`lang.py` ja/en 両辞書へ `btn_watermark_image` を同一キーで追加
- `tests/test_page_polish.py` を新規作成（D-15・Phase 3 の新規テスト専用ファイル）。純関数（中央配置・幅50%・クランプ）、PNG/JPEG埋め込み確認、undo往復、未選択時no-op、破損画像ハンドリング、LANGパリティの計9テストを追加

## Task Commits

Each task was committed atomically:

1. **Task 1: 画像透かしの適用ロジック（_add_watermark_image / _watermark_image_rect）** - `d876cd9` (feat)
2. **Task 2: 透かしボタンのUI結線とLANGキー追加** - `d43fe17` (feat)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/page_ops.py` - `_add_watermark_image`/`_watermark_image_rect` を追加（`from PIL import Image`/`import io` を冒頭に追加）
- `pagefolio/ui_builder.py` - テキスト透かしボタン直後に画像透かしボタンを結線
- `pagefolio/lang.py` - ja/en 両辞書へ `btn_watermark_image` キーを追加
- `tests/test_page_polish.py` (新規) - `TestImageWatermarkRect`/`TestImageWatermark`/`TestImageWatermarkLang` の3クラス9テスト

## Decisions Made
- D-03 に忠実に PNG は既存アルファ×0.5、JPEGは`convert("RGBA")`後に均一128を`putalpha`（画像自体のRGBA/SMaskに依存する`insert_image`の仕様どおり）
- D-02 の「ページ幅約50%・アスペクト比保持」に加え、縦長画像がページ高さの90%を超える場合は高さ基準へクランプ（Claude's Discretion・RESEARCH.md Pattern 1 のコード例を踏襲）
- undo は `_save_undo("page_edit", targets=targets)` を適用ループの外側で1回だけ呼ぶ既存パターンを完全踏襲（複数ページ選択時も1回のundoで全ページ復元）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md/PATTERNS.md のコード例をほぼそのまま採用）。

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-01 完了。03-02（黒塗り/モザイク棚卸し・OCR系並行プラン）へ進行可能
- 画像透かしの実描画（半透明・SMask）は end-of-phase human-verify 対象として残存（03-CONTEXT.md/03-RESEARCH.md A1・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 787件グリーン（従来780件から+7）・`ruff check`/`ruff format --check` クリーン

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/page_ops.py
- FOUND: tests/test_page_polish.py
- FOUND: .planning/phases/03-v1-5-0/03-01-SUMMARY.md
- FOUND: d876cd9 (Task 1 commit)
- FOUND: d43fe17 (Task 2 commit)
