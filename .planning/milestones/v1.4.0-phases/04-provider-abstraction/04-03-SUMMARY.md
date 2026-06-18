---
phase: 04-provider-abstraction
plan: "03"
subsystem: ocr
tags: [fitz, threading, provider-abstraction, embedded-text, skip-detection]

requires:
  - phase: 04-01
    provides: OCRProvider (abc.ABC), OCRAPIKeyError, LMStudioProvider
  - phase: 04-02
    provides: run_parallel / has_embedded_text / page_to_png_b64 / build_provider

provides:
  - スレッド境界再構成済み OCRDialog（provider 引数・メインスレッドレンダリング・埋め込みスキップ統合）
  - lang.py に ocr_text_skip_notice / ocr_progress_skip（日英）
  - settings.py に ocr_provider デフォルト "off"

affects:
  - phase-05 (OCR UI — provider 選択 UI / APIキー管理)
  - phase-06 (逐次レンダリング化)

tech-stack:
  added: []
  patterns:
    - "after() 小分けでメインスレッドのレンダリング/埋め込み判定を逐次実行し UI フリーズを回避"
    - "ワーカースレッドは文字列（b64）と provider のみを受け取り fitz.Document に一切触らない（D-03）"
    - "埋め込みテキストページは Vision API を経由せず get_text() 結果を直接 results に統合（D-07）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - pagefolio/settings.py

key-decisions:
  - "メインスレッドで _render_next_page を after(0) 連鎖させ、ページ数分ループ後に _start_worker_thread を呼ぶ設計を採用（D-01 事前レンダリング最小構成）"
  - "provider=None のフォールバック処理は _fetch_models のみ（None ガード）で実装し、通常パスは 04-02 の _start_ocr が常に provider を渡す前提を維持"
  - "スキップページの表示は [ocr_text_skip_notice] ヘッダー + 抽出テキスト本文の構成（T-04-09: ログには混入させない）"

patterns-established:
  - "スレッド分離: メインスレッド（fitz/Tkinter操作）↔ ワーカースレッド（HTTP IO）の境界を after() で橋渡し"
  - "_worker の docstring に 'fitz' 等の禁止ワードを書かない（automated grep チェック対応）"

requirements-completed:
  - OCR-PROV-02
  - OCR-PERF-01

duration: 6min
completed: "2026-06-06"
---

# Phase 04 Plan 03: OCRDialog スレッド境界再構成 Summary

**OCRDialog の _worker から fitz アクセスを完全排除し、メインスレッドの after() 小分けレンダリング・埋め込みテキストスキップ統合・run_parallel 結線を実現（Phase 4 三成功基準を UI 層で結実）**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-06T06:31:41Z
- **Completed:** 2026-06-06T06:37:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- settings.py の defaults に `ocr_provider: "off"` を追加（V14-D-03 安全デフォルト）
- lang.py の ja/en に `ocr_text_skip_notice` / `ocr_progress_skip` を追加（D-09）
- OCRDialog の `__init__` に `provider=None` 引数を確定シグネチャ通りに追加
- `_fetch_models` を `fetch_lm_studio_models()` → `self.provider.list_models()` に置換
- `_on_run` → `_render_next_page` （after 連鎖）→ `_start_worker_thread` のパイプラインを実装
- `_worker` 内から fitz/get_pixmap/self.doc[/page_to_png_b64 を完全排除（成功基準3・D-03）
- 埋め込みテキストページを Vision API スキップ + get_text() 結果を results に直投入（成功基準2・D-07）
- `_render_results_ordered` にスキップ由来区別表示（`ocr_text_skip_notice` 明示・D-08）

## Task Commits

1. **Task 1: settings に ocr_provider デフォルト、lang にスキップ通知文言を追加** - `55927da` (feat)
2. **Task 2: OCRDialog スレッド境界再構成・run_parallel / 埋め込みスキップ結線** - `d23225f` (feat)

## Files Created/Modified

- `pagefolio/ocr_dialog.py` — スレッド境界リファクタ済み OCRDialog（provider 受け取り・メインスレッドレンダリング・スキップ統合・run_parallel 結線）
- `pagefolio/lang.py` — ocr_text_skip_notice / ocr_progress_skip（ja/en）を追加
- `pagefolio/settings.py` — defaults dict に ocr_provider:"off" を追加

## Decisions Made

- `_render_next_page` を `after(0)` で連鎖する設計：レンダリング中も Tkinter イベントループを疎通させ UI フリーズを回避する（D-01）
- `_worker` docstring に禁止ワード（fitz/get_pixmap 等）を書かないルール：automated grep チェックが docstring を誤検知しないようにするため
- スキップページの結果表示は `[skip_notice]\n` + `extracted_text\n` の構成：埋め込みテキスト由来であることを視覚的に明示しつつ、テキスト本文は閲覧・コピー・保存に使用可能

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _worker docstring の禁止ワードによる automated grep 誤検知を修正**
- **Found during:** Task 2 の verify ステップ
- **Issue:** `_worker` の docstring に `get_pixmap` という文字列を含めていたため、automated grep チェックが `_worker` 本体に fitz コールが残っていると誤判定した
- **Fix:** docstring を「fitz アクセスゼロ・D-03」に書き換え（実装の変更なし）
- **Files modified:** `pagefolio/ocr_dialog.py`
- **Verification:** automated grep チェック通過
- **Committed in:** `d23225f`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** docstring 文言修正のみ。実装・仕様への影響なし。

## Issues Encountered

None — automated grep チェックで docstring 内の禁止ワードを一度誤検知したが即座に修正（上記 Deviations に記載）。

## Known Stubs

None — スキップページの UI 表示は `ocr_text_skip_notice` 文言で完全実装済み。`provider` が `None` の場合の `_fetch_models` ガードは暫定実装だが、04-02 の `_start_ocr` が常に provider を渡すため通常パスでは到達しない。

## User Setup Required

None — 外部サービス設定変更なし。`ocr_provider` デフォルトが `"off"` に変更されたが Phase 4 では LMStudioProvider として動作するため既存ユーザーへの影響なし。

## Next Phase Readiness

- Phase 4 三成功基準（後方互換 / 埋め込みスキップ / スレッド境界）がすべて UI 層で結実済み
- Phase 5 で `ocr_provider` の UI 切替・Claude/Gemini プロバイダ追加が可能な状態
- Phase 6 の逐次レンダリング化（レンダリング→送信→破棄）のフックポイント（`_render_next_page`）が実装済み

## Self-Check: PASSED

- FOUND: `pagefolio/ocr_dialog.py`
- FOUND: `pagefolio/lang.py`
- FOUND: `pagefolio/settings.py`
- FOUND: `.planning/phases/04-provider-abstraction/04-03-SUMMARY.md`
- FOUND: commit `55927da` (Task 1)
- FOUND: commit `d23225f` (Task 2)

---
*Phase: 04-provider-abstraction*
*Completed: 2026-06-06*
