---
phase: 06-ux-ui
plan: 02
subsystem: ui
tags: [tkinter, scroll, font, i18n-adjacent, regression-test]

# Dependency graph
requires: []
provides:
  - "about.py 見出しフォントの font_size 設定追従化（self._font(4, 'bold')）"
  - "tests/test_font_hardcode_guard.py（フォントサイズ数値ハードコード検出の回帰テスト）"
  - "plugin.py プラグイン一覧 Canvas のマウスホイール対応（llm_config 基準の動的 Enter/Leave 束縛）"
  - "ocr_dialog.py ダイアログ高さの画面高クランプ（低解像度環境の画面外はみ出し防止）"
  - ".planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md（スクロール/フォント監査記録）"
affects: [06-03-changelog-insert-redo]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "フォントハードコード検出のソーススキャン型回帰テスト（test_source_keyguard.py 踏襲・pagefolio/ 限定 rglob）"
    - "Canvas スクロールの動的 Enter/Leave bind_all/unbind_all マウスホイール束縛（llm_config/dialog.py 基準への個別是正）"
    - "ダイアログ高さの winfo_screenheight() クランプ（llm_config/dialog.py._compute_dialog_height 相当）"

key-files:
  created:
    - tests/test_font_hardcode_guard.py
    - .planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md
  modified:
    - pagefolio/dialogs/about.py
    - pagefolio/dialogs/plugin.py
    - pagefolio/ocr_dialog.py

key-decisions:
  - "about.py の delta 値は実測に基づき4を採用（既定font_size=12との組合せで是正前の見た目16ptを完全再現。RESEARCH.mdの提案値delta=6はbase=10という誤った仮定に基づいていたため実測で再確定）"
  - "スクロール是正はplugin.py（ホイール未対応）とocr_dialog.py（高さクランプ欠如）の2箇所のみに限定し、ui_builder.py等の静的bind方式は受容差分として監査記録に根拠付きで残す（D-11）"
  - "ocr_dialog.pyのside_canvasホイール束縛方式（静的再帰）はPitfall4の対象外（高さクランプのみが指摘事項）のため変更せず据え置く"

patterns-established:
  - "Pattern: ダイアログの数値フォントハードコードはtest_font_hardcode_guard.pyで構造的に再発防止する（allowlist不要・\\d+終端の正規表現で変数連動箇所を自動的に除外）"

requirements-completed: [V180-QA-03]

coverage:
  - id: D1
    description: "about.py の見出しフォントが font_size 設定（8〜16）に追従し、最大値でも360px幅ダイアログ内に収まる"
    requirement: "V180-QA-03"
    verification:
      - kind: unit
        ref: "tests/test_font_hardcode_guard.py::test_no_hardcoded_font_sizes"
        status: pass
    human_judgment: false
  - id: D2
    description: "フォントサイズ数値ハードコード検出の正規表現が数値リテラルのみに反応し変数指定を誤検知しない"
    requirement: "V180-QA-03"
    verification:
      - kind: unit
        ref: "tests/test_font_hardcode_guard.py::test_pattern_matches_only_literals"
        status: pass
    human_judgment: false
  - id: D3
    description: "plugin.py のプラグイン一覧Canvasがマウスホイールでスクロールできる（llm_config基準の動的束縛）"
    requirement: "V180-QA-03"
    verification:
      - kind: manual_procedural
        ref: "ruff check pagefolio/dialogs/plugin.py（構文検証）+ コードレビュー（Enter/Leave束縛のロジック確認）"
        status: pass
    human_judgment: true
    rationale: "実際のマウスホイールイベント配送はTkイベントループ・実ウィジェット階層に依存し、pytestのTk非依存スタブでは配送の実挙動を再現できない（06-SCROLL-FONT-AUDIT.md §1.4に記載の構造的テスト化困難）。実機でのホイール操作確認が必要。"
  - id: D4
    description: "ocr_dialog.py の _center() が画面高でダイアログ高さをクランプし低解像度環境で画面外にはみ出さない"
    requirement: "V180-QA-03"
    verification:
      - kind: unit
        ref: "pytest tests/test_pdf_ops.py（既存スイート回帰確認・_center変更が既存機能を壊さないことを担保）"
        status: pass
    human_judgment: true
    rationale: "低解像度実機環境でのダイアログ表示確認は自動テストで代替できない視覚的検証項目のため（06-SCROLL-FONT-AUDIT.md §1.3）。"
  - id: D5
    description: "スクロール実装を持つ8ファイルが基準実装と比較監査され、是正箇所と受容差分の判定根拠が監査記録に残る"
    requirement: "V180-QA-03"
    verification:
      - kind: other
        ref: ".planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md（判定表・是正根拠・受容差分根拠を全記載）"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-07-16
status: complete
---

# Phase 06 Plan 02: UI一貫性監査（スクロール・フォント）Summary

**about.py見出しフォントをself._font(4,"bold")へ是正しフォントハードコード検出の回帰テストを新設。plugin.pyにllm_config基準のマウスホイール束縛、ocr_dialog.pyに画面高クランプを個別追加し、監査対象8ファイルの判定根拠を06-SCROLL-FONT-AUDIT.mdへ記録**

## Performance

- **Duration:** 約17分
- **Started:** 2026-07-16T11:05:00Z
- **Completed:** 2026-07-16T11:22:00Z
- **Tasks:** 3
- **Files modified:** 5（新規2・改修3）

## Accomplishments
- `tests/test_font_hardcode_guard.py` を新規作成（`test_source_keyguard.py` の grep 型ソーススキャンを踏襲）。`test_no_hardcoded_font_sizes` は `pagefolio/` 全体でフォントサイズ数値ハードコードをゼロ件と確認。`test_pattern_matches_only_literals`（レビューR4反映）は正規表現が数値リテラルのみに反応し `self.font_size`/`fs`/`size` 等の変数指定を誤検知しないことを正負両方向で検証
- `pagefolio/dialogs/about.py:42` の `font=("Segoe UI", 16, "bold")` を `self._font(4, "bold")` へ是正。実測（`settings.py` 既定 `font_size=12`）に基づき delta=4 を確定し、既定設定で是正前の見た目（16pt）を完全再現。最大値（16）でも20ptに収まり、`tkinter.font.Font` 実測で "PageFolio" 描画幅128px（360px幅ダイアログ内に収まる・レビューR3懸念を実測で解消）
- `pagefolio/dialogs/plugin.py` のプラグイン一覧Canvasへ、llm_config/dialog.py 基準の動的 Enter/Leave `bind_all`/`unbind_all` マウスホイール束縛を追加（Pitfall 3 是正）。ダイアログ破棄時の `unbind_all` 漏れ防止も追加
- `pagefolio/ocr_dialog.py:_center()` へ `winfo_screenheight()` ベースの高さクランプを追加（Pitfall 4 是正）。低解像度・大フォント環境でダイアログ下端が画面外に出るリスクを解消
- `.planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md` を新規作成。監査対象8ファイル全件の判定表・是正箇所2件・受容差分4件（根拠付き）・フォント監査結果・除外対象3箇所・回帰テスト新設の記録を残した

## Task Commits

Each task was committed atomically:

1. **Task 1: フォントハードコード検出テスト新設 + about.py 見出しフォント是正** - `697387c` (test)
2. **Task 2: スクロール個別是正（plugin.py ホイール束縛 + ocr_dialog.py 高さクランプ）** - `6972b17` (fix)
3. **Task 3: スクロール/フォント監査記録の作成** - `f492d6f` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified
- `tests/test_font_hardcode_guard.py` - フォントサイズ数値ハードコード検出の回帰テスト（正負両方向を検証）
- `pagefolio/dialogs/about.py` - 見出しフォントを `self._font(4, "bold")` へ是正
- `pagefolio/dialogs/plugin.py` - プラグイン一覧Canvasへ動的マウスホイール束縛を追加
- `pagefolio/ocr_dialog.py` - `_center()` に画面高クランプを追加
- `.planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md` - スクロール/フォント監査記録（8ファイル判定表・是正根拠・受容差分根拠）

## Decisions Made
- about.py の delta 値は実測（`settings.py` 既定 `font_size=12`）に基づき **4** を採用。RESEARCH.md の提案値（delta=6、base=10 想定）は実際の既定値と異なっていたため、実装時に実測値で再確定した（flagged assumption A1 の解消）
- スクロール是正は `plugin.py`（ホイール未対応）と `ocr_dialog.py`（高さクランプ欠如）の2箇所のみに限定。`ui_builder.py` の静的bind方式・`ocr_dialog.py` の `side_canvas` ホイール方式・`viewer.py` のポップアップ Canvas は受容差分として監査記録に根拠付きで残した（D-11: 個別是正のみ・共通ヘルパー新設なし）
- `batch_ocr.py`/`llm_config/sections.py`/`merge.py` は `tk.Listbox`（Canvas非使用・ネイティブホイール対応）のため llm_config 基準（Canvas + 動的束縛）の対象範囲外と判定し、是正不要と確認した

## Deviations from Plan

None - plan executed exactly as written. Flagged assumption A1（about.py の delta 値）はプラン自体が「実装時に実測値で確定する」と明記していた事項であり、実測により delta=4 に確定した（計画通りの想定内対応）。

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V180-QA-03 完了。フルスイート 1095 件グリーン・ruff クリーン
- Plan 03（開発履歴.md整合 + insert_redoバグ修正）は本プランと独立して着手可能
- 実機でのプラグイン一覧ホイールスクロール・OCRダイアログ低解像度表示の目視確認は human-verify 対象として残る（coverage D3/D4 参照）

---
*Phase: 06-ux-ui*
*Completed: 2026-07-16*

## Self-Check: PASSED

全作成/改修ファイル（tests/test_font_hardcode_guard.py・pagefolio/dialogs/about.py・
pagefolio/dialogs/plugin.py・pagefolio/ocr_dialog.py・
.planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md・本SUMMARY.md）の実在確認、および
Task 1〜3・SUMMARYの各コミット（697387c/6972b17/f492d6f/2f9d0db）の `git log` 実在確認とも FOUND。
