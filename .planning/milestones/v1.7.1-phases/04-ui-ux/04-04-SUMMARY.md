---
phase: 04-ui-ux
plan: 04
subsystem: ui
tags: [tkinter, i18n, lang-dict, messagebox, regression-test]

# Dependency graph
requires:
  - phase: 04-03
    provides: "LLMConfigDialog 共通/固有見出し・Ollama重複解消（C2）完了後の棚卸し残（C6/C7/未使用9キー）の引き継ぎ"
provides:
  - "viewer.py の _show_page_popup が LANG キー経由（popup_page_title/popup_zoom_out/popup_zoom_in/popup_close）で表示される（C6解消）"
  - "page_ops.py の _split_by_range が showerror+err_title で範囲未入力・範囲形式不正の両分岐を対称に扱う（C7解消）"
  - "lang.py の確定未使用キー（RESEARCH 9件 + D-11テスト自身が新規発見した2件=計11件）削除・ja/en キー集合一致"
  - "test_lang_parity.py の test_no_unused_lang_keys（D-11・常設回帰）"
affects: [04-ui-ux フェーズ完了後の締め・次マイルストーン]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "lang.py 未使用キー検出は 引用符付き完全一致（\"key\"/'key'）で pagefolio/(lang.py除く)・tests/・plugins/ を走査し、プレフィックス衝突（tesseract_not_installed vs _hint）を構造的に回避する"
    - "_ALLOWLIST 集合による動的参照キーの除外機構（現状ゼロ件・将来の f-string キー合成発生時に備える）"

key-files:
  created: []
  modified:
    - pagefolio/viewer.py
    - pagefolio/page_ops.py
    - pagefolio/lang.py
    - tests/test_lang_parity.py
    - tests/test_pdf_ops.py

key-decisions:
  - "D-11 の未使用キー検出テストは grep 相当の引用符付き完全一致方式を採用（AST走査ではなく）。動的キー合成はコードベース全体でゼロ件（RESEARCH Pitfall 3 確認済み）のため十分"
  - "テスト実装中に D-11 検査自体が新規発見した ocr_progress/ocr_progress_render（Phase 2 の統合プログレス化 D-03 で不要化していた活き残り）も RESEARCH の確定9件と同時に削除した（Rule 1 auto-fix・全件解消 D-19 の趣旨に整合）"
  - "tesseract_not_installed（削除）と tesseract_not_installed_hint（使用中・維持）はキー名プレフィックス衝突の代表例のため、削除操作は完全一致の該当行のみに限定した"

requirements-completed: [V171-UIUX-02]

coverage:
  - id: D1
    description: "viewer.py の _show_page_popup がポップアップタイトル・縮小/拡大/閉じるボタン文言を self._t() 経由で表示し、lang='en' で日本語が出ない（C6解消）"
    requirement: "V171-UIUX-02"
    verification:
      - kind: unit
        ref: "python -c AST/grep 検証（popup_page_title/popup_zoom_out/popup_zoom_in/popup_close の self._t() 経由使用・ja/en 両存在確認）"
        status: pass
      - kind: unit
        ref: "pytest tests/test_lang_parity.py -x -q"
        status: pass
      - kind: manual_procedural
        ref: "拡大ポップアップの実描画（en 表示で日本語が出ないこと）の目視確認"
        status: unknown
    human_judgment: true
    rationale: "Tkinter ウィジェットの実描画確認は既存テストスイート（実 Tk ウィジェット生成なし）では検証できず、VERIFICATION.md の Manual-Only 項目として記録される（既存 human-verify 運用と同じ・04-RESEARCH.md D-20）"
  - id: D2
    description: "page_ops.py の _split_by_range で範囲未入力エラーが showerror + err_title で表示され、範囲形式不正エラーと種別/タイトルが対称になる（C7解消）"
    requirement: "V171-UIUX-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py#TestPdfSplit::test_split_by_range_no_input_shows_error"
        status: pass
      - kind: unit
        ref: "pytest tests/test_pdf_ops.py -k split -x -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "lang.py の確定未使用キーが削除され、ja/en キー集合が一致したまま維持される。全 LANG キーがソース参照されることを検査する回帰テストが常設される（D-11）"
    requirement: "V171-UIUX-02"
    verification:
      - kind: unit
        ref: "tests/test_lang_parity.py#test_no_unused_lang_keys"
        status: pass
      - kind: unit
        ref: "pytest tests/test_lang_parity.py -x -q"
        status: pass
      - kind: unit
        ref: "pytest（フルスイート859件）"
        status: pass
    human_judgment: false

# Metrics
duration: 9min
completed: 2026-07-05
status: complete
---

# Phase 4 Plan 4: 文言/エラー一貫性監査の最終解消 Summary

**viewer.py 拡大ポップアップの LANG キー化（C6）・page_ops.py 分割エラーの messagebox 種別統一（C7）・lang.py 確定未使用11キー削除 + D-11 未使用キー検出回帰テスト常設**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-05T10:20:00Z
- **Completed:** 2026-07-05T10:29:42Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `pagefolio/viewer.py` の `_show_page_popup`（ポップアップタイトル・縮小/拡大/閉じるボタンの4箇所）を `self._t()` 経由の LANG キー参照へ置き換え、`lang="en"` でも日本語が出ない状態にした（C6 解消）。新規キー `popup_page_title`/`popup_zoom_out`/`popup_zoom_in`/`popup_close` を ja/en 両辞書へ同時追加
- `pagefolio/page_ops.py` の `_split_by_range` で範囲未入力エラーを `messagebox.showinfo`+`info_title` から `messagebox.showerror`+`err_title` へ変更し、直後の範囲形式不正エラーと種別/タイトルを対称化（C7 解消）。回帰テスト `test_split_by_range_no_input_shows_error` を `tests/test_pdf_ops.py` へ追加
- `pagefolio/lang.py` から確定未使用キーを削除: RESEARCH.md 監査表の9件（`ocr_provider_off_hint`/`tesseract_not_installed`/`llm_fetching_ollama_models`/`ocr_fetch_models`/`ocr_models_fetched`/`ocr_models_fetch_fail`/`ocr_models_fetching`/`sec_compress`/`warn_title`）に加え、新設した D-11 テスト自身が発見した `ocr_progress`/`ocr_progress_render`（Phase 2 の統合プログレス化で不要化していた活き残り）の計11件。使用中の `tesseract_not_installed_hint` は完全一致方式により誤削除を回避
- `tests/test_lang_parity.py` へ `test_no_unused_lang_keys`（D-11）を新設。`pagefolio/`（`lang.py` 除く）・`tests/`・`plugins/` 全 `.py` を走査し、各 LANG キーが引用符付き完全一致（`"key"`/`'key'`）でどこかに出現するかを検査。動的参照用の `_ALLOWLIST` 機構（現状ゼロ件）を用意

## Task Commits

Each task was committed atomically:

1. **Task 1: viewer.py の _show_page_popup ハードコード文言を LANG キー化（C6）** - `f4ce6bb` (fix)
2. **Task 2: page_ops.py の分割エラー messagebox 種別/タイトルを統一（C7）** - `b32d83a` (fix)
3. **Task 3: lang.py 確定未使用キーを削除し D-11 未使用キー検出テストを常設** - `dc20c80` (refactor)

## Files Created/Modified
- `pagefolio/viewer.py` - `_show_page_popup` の4箇所のハードコード日本語文言を `self._t()` 経由の LANG キー参照へ変更
- `pagefolio/page_ops.py` - `_split_by_range` の範囲未入力分岐を `showinfo`→`showerror`+`err_title` へ変更
- `pagefolio/lang.py` - popup_* 4キー新規追加（ja/en）・確定未使用11キー削除（ja/en）
- `tests/test_lang_parity.py` - `test_no_unused_lang_keys`（D-11・全キー参照検査・`_ALLOWLIST` 機構）を新設
- `tests/test_pdf_ops.py` - `test_split_by_range_no_input_shows_error`（C7 回帰テスト）を `TestPdfSplit` へ追加

## Decisions Made
- lang.py の未使用キー検出は AST ではなく grep 相当の「引用符付き完全一致」方式を採用。動的キー合成（f-string 等）はコードベース全体でゼロ件であることを RESEARCH.md で確認済みのため、実装コストの低い方式で十分と判断
- `test_no_unused_lang_keys` の実装・実行の過程で `ocr_progress`/`ocr_progress_render` という RESEARCH.md 確定表には無かった2件の未使用キーを発見。これは Phase 2（OCR磨き込み）の統合プログレス化（D-03）で既に不要化していた活き残りであり、D-19「棚卸しの活き残りは全件解消（次送りしない）」の趣旨および本タスクの目的（未使用キー0件を担保する回帰テストの確立）に照らし、RESEARCH の9件と同時に削除した（詳細は Deviations 参照）
- 削除対象キーの特定は「引用符で囲んだキー名の完全一致」のみで行い、`tesseract_not_installed`（削除）と `tesseract_not_installed_hint`（維持）のようなプレフィックス衝突ペアを誤って巻き込まないことを確認した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] D-11 検査が新規発見した未使用キー2件（`ocr_progress`/`ocr_progress_render`）を追加削除**
- **Found during:** Task 3（lang.py 確定未使用キー削除・D-11 テスト実装）
- **Issue:** plan/RESEARCH.md の確定未使用リストは9件だったが、新設した `test_no_unused_lang_keys` を実行した時点で `ocr_progress`/`ocr_progress_render` の2件も未使用と判定された。調査の結果、Phase 2（04-03 以前の OCR 磨き込みフェーズ）の統合プログレス化（D-03: レンダリング2段階表示を廃止し `done+skipped/total` の統合表示へ一本化）により、これらのキーは実装上不要になっていたが lang.py には残置されていたことが判明した
- **Fix:** RESEARCH.md 確定9件と同じ完全一致方式で ja/en 両辞書から追加削除。`ocr_progress_init`/`ocr_progress_ocr`（使用中）は維持
- **Files modified:** `pagefolio/lang.py`
- **Verification:** `pytest tests/test_lang_parity.py -x -q` グリーン（`test_no_unused_lang_keys` が未使用0件で通過）・`pytest` フルスイート859件グリーン・`ruff check . && ruff format . --check` クリーン
- **Committed in:** `dc20c80`（Task 3 commit）

---

**Total deviations:** 1 auto-fixed（Rule 1 — bug/dead-code discovered by the very regression test this task establishes）
**Impact on plan:** D-19「棚卸しの活き残りは全件解消」の趣旨と本プランの成功基準（未使用キー0件でテストが成立）を厳密に満たすために必要な追加対応。スコープ拡大ではなく、計画済みタスク（D-11テスト常設）の直接の副産物。

## Issues Encountered

None - 上記デビエーション以外は計画通り。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V171-UIUX-02（文言/エラー一貫性監査）は本プランで完了。棚卸し確定表（04-RESEARCH.md）の C6・C7・未使用キー全件（RESEARCH 確定9件 + 新規発見2件=計11件）を解消
- Phase 4 の4プラン全完了（04-01 ショートカット基盤・04-02 ShortcutsDialog+SettingsDialog再編・04-03 LLMConfigDialog整理+Ollama重複解消・04-04 本プラン）。V171-UIUX-01〜03・V171-TEST-03 全要件充足
- 拡大ポップアップの実描画（en 表示で日本語が出ないこと）の目視確認は VERIFICATION.md の Manual-Only 項目として記録が必要
- ブロッカーなし。`pytest` フルスイート859件グリーン・`ruff check . && ruff format .` クリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files exist on disk (pagefolio/viewer.py, pagefolio/page_ops.py,
pagefolio/lang.py, tests/test_lang_parity.py, tests/test_pdf_ops.py,
.planning/phases/04-ui-ux/04-04-SUMMARY.md) and all task commit hashes
(f4ce6bb, b32d83a, dc20c80) are present in git log.
