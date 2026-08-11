---
phase: 01-safety-rollback
plan: 04
subsystem: page-ops
tags: [pymupdf, fitz, undo-redo, rollback, blob-lifecycle, tdd]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-01（file_ops.py の保存経路暗号化維持・derive_pdf_has_password）と01-02（OCR OFF ガード）はファイル面が独立"
provides:
  - "_do_insert は挿入済みページ数を追跡し、途中のファイルで例外が出た場合に同一インデックスへの delete_page で挿入分を巻き戻す（D-08）"
  - "挿入元 Document は try/finally で例外時も必ず close される（D-09）"
  - "巻き戻し自体が失敗した場合は残存ページ数を明示した警告ダイアログを表示し、実際の残存数を反映した Undo state を残す（D-10）"
  - "_do_insert の例外処理から Undo スタックへの直接 pop が排除され、_dispose_state 経由の解放に統一された（D-14）"
  - "_duplicate_page は _save_undo(\"duplicate\") を実処理成功後にのみ確定する（D-11）"
  - "_undo / _redo は _restore_state 失敗時に pop した state を _push_evicting 経由でスタックへ戻し、messagebox.showerror でブロッキング通知する（D-13/D-14）。_dispose_state は呼ばず Blob を温存し次回再試行できる"
  - "lang.py に warn_rollback_title / err_insert_rollback_failed / err_undo_restore_failed / err_redo_restore_failed を ja/en 追加"
affects: [01-05]

actuals:
  tokens: 6943
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "巻き戻しは delete_page(insert_at) を実挿入数だけ同一インデックスへ繰り返す既存パターン（file_ops.py の insert op undo と同一）を再利用し、新しいロジックを発明しない"
    - "Undo記録の後置確定（D-11）: 例外を送出しうる実処理がすべて成功した後にのみ _save_undo を呼ぶことで、不正な Undo 履歴の残留を構造的に防ぐ"
    - "復元失敗時の state 保全: _dispose_state を呼ばず _push_evicting でスタックへ戻すことで、Blob の二重解放と履歴喪失の両方を同時に防ぐ（Pitfall 4）"

key-files:
  created: []
  modified:
    - pagefolio/page_ops.py
    - pagefolio/file_ops.py
    - pagefolio/lang.py
    - tests/test_pdf_ops.py

key-decisions:
  - "D-08〜D-10/D-14の通りに実装。_do_insert は total/pos の初期化を外側 try の前へ移し、例外時は実際に delete_page が成功した件数（removed）を差し引いた残存数（residual）を Undo state の件数フィールドへ反映する。プラン原文は『total をそのまま書き込む』簡易パターンだったが、delete_page が巻き戻しループ途中で失敗する部分成功ケースでも正確な残存数になるよう removed 追跡版を採用した（Rule 1: 巻き戻し自体が部分的に成功した場合に total を過大計上して余分な既存ページまで削除してしまう潜在バグを防止）。全 delete_page が即座に失敗する典型的な失敗系テストでは removed=0 となり residual=total と一致するため、計画の想定挙動と結果は同一"
  - "D-11の通りに実装。_duplicate_page の _save_undo(\"duplicate\", pno=pno) を try ブロック内・tmp.close() の直後（実処理完了後）へ移動した"
  - "D-13/D-14の通りに実装。_undo/_redo の _restore_state 呼び出しを try/except で保護し、失敗時は _push_evicting(self._undo_stack または self._redo_stack, state) でスタックへ戻し、_dispose_state は呼ばない"

requirements-completed: [V190-SAFE-04, V190-SAFE-05, V190-UNDO-01]

coverage:
  - id: D1
    description: "複数ファイル挿入が途中のファイルで失敗しても既存ページ・Undoスタックが操作前と一致し、挿入元Documentは必ずcloseされる（1ファイル/2ファイル目失敗・空リストの境界を含む）"
    requirement: "V190-SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertRollback::test_insert_failure_rolls_back_pages_and_undo_stack"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertRollback::test_insert_failure_closes_source_documents"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertRollback::test_insert_failure_single_file_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertRollback::test_insert_empty_path_list_boundary"
        status: pass
    human_judgment: false
  - id: D2
    description: "巻き戻し（delete_page）自体が失敗した場合、警告ダイアログが1回表示され、実際の挿入数を反映したUndo stateが残り、そのstateで後からundoできる"
    requirement: "V190-SAFE-04"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertRollback::test_rollback_failure_warns_and_keeps_undo_state"
        status: pass
    human_judgment: false
  - id: D3
    description: "ページ複製が失敗した場合は既存ページ・Undoスタックが不変、成功した場合はUndo記録が実処理成功後にのみ確定する"
    requirement: "V190-SAFE-05"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestDuplicateUndoTiming::test_duplicate_failure_leaves_pages_and_undo_stack_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestDuplicateUndoTiming::test_duplicate_success_records_undo_after_work"
        status: pass
    human_judgment: false
  - id: D4
    description: "Undo/Redoの復元失敗時にpopしたstateがスタックへ戻りブロッキング通知される。Blobは二重解放されず、失敗後の再試行で同じstateが正しく再消費される。空スタックはno-op"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_undo_restore_failure_returns_state_to_stack"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_redo_restore_failure_returns_state_to_stack"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_undo_retry_after_failure_uses_same_state"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_undo_empty_stack_is_noop"
        status: pass
    human_judgment: false

duration: 約20min
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 4: 挿入ロールバック・複製Undo後置確定・Undo/Redo復元失敗保護 Summary

**複数ファイル挿入の失敗を delete_page 巻き戻し + try/finally close で無警告残留させず、ページ複製の Undo 記録を実処理成功後へ後置化し、_undo/_redo の復元失敗を _push_evicting 経由で state 保全しつつ messagebox でブロッキング通知するよう実装**

## Performance

- **Duration:** 約20分
- **Completed:** 2026-08-10
- **Tasks:** 3/3
- **Files modified:** 4（`pagefolio/page_ops.py`, `pagefolio/file_ops.py`, `pagefolio/lang.py`, `tests/test_pdf_ops.py`）

## Accomplishments
- `_do_insert` に挿入済みページ数（total）追跡と例外時の巻き戻し（同一インデックス `insert_at` への `delete_page` 反復・既存 `_restore_state` insert op undo と同一パターン）を実装。挿入元 Document は内側 `try/finally` で例外時も必ず `close()` される（D-08・D-09）
- 巻き戻し自体が失敗した場合（`delete_page` も例外）は、実際に削除できた件数を差し引いた残存数を Undo state の件数フィールドへ反映して残し、`messagebox.showwarning` で残存ページ数を明示する警告を1回表示する（D-10）。無警告の部分適用はゼロになった
- `_do_insert` の例外処理から Undo スタックへの直接 `pop` を排除し、巻き戻し成功時は `_dispose_state` 経由で解放してから取り除く形に統一した（D-14）
- `_duplicate_page` の `_save_undo("duplicate", pno=pno)` を実処理（`tmp.insert_pdf` → `self.doc.insert_pdf` → `tmp.close()`）成功後へ移動した。複製前に例外が出ても不正な Undo 履歴が残らない（D-11）
- `_undo` / `_redo` の `_restore_state` 呼び出しを `try/except` で保護し、失敗時は pop した state を `_push_evicting` 経由で元のスタックへ戻し、`messagebox.showerror` でブロッキング通知する。`_dispose_state` は呼ばず Blob 参照を温存するため、次回の undo/redo で同じ state を正しく再消費できる（D-13・D-14・Pitfall 4 回避）
- `pagefolio/lang.py` に `warn_rollback_title` / `err_insert_rollback_failed` / `err_undo_restore_failed` / `err_redo_restore_failed` を ja/en 両方に追加
- `tests/test_pdf_ops.py` に `TestInsertRollback`（5メソッド）・`TestDuplicateUndoTiming`（2メソッド）・`TestUndoRedoRestoreFailure`（4メソッド）を新設し、V190-SAFE-04/05・V190-UNDO-01 の不変条件を digest 比較・スタック長比較・Blob 解放呼び出し回数で機械検証した
- フルテストスイート（1150件）・ruff（check/format）ともにグリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: 複数ファイル挿入のロールバックとページ複製の Undo 後置確定** - `7627a64` (test/RED) → `681d22f` (feat/GREEN)
2. **Task 2: Undo / Redo 復元失敗時の state 保全とブロッキング通知** - `727624a` (test/RED) → `38440e7` (feat/GREEN)
3. **Task 3: ロールバック・Undo タイミング・復元失敗の回帰テスト整備** - `22f83d2` (test)

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: Task 1/2 は `tdd="true"` のため RED→GREEN の2コミット構成。実装が既に簡潔だったため REFACTOR コミットは不要と判断した。_

## Files Created/Modified
- `pagefolio/page_ops.py` - `_do_insert`（挿入巻き戻し・try/finally close・警告付き残存数反映）・`_duplicate_page`（Undo 後置確定）を変更。`logging` import を追加（巻き戻し失敗時の debug ログ用）
- `pagefolio/file_ops.py` - `_undo` / `_redo` に復元失敗時の例外保護（`_push_evicting` によるスタック復帰・`messagebox.showerror` 通知）を追加
- `pagefolio/lang.py` - `warn_rollback_title` / `err_insert_rollback_failed` / `err_undo_restore_failed` / `err_redo_restore_failed` を ja/en 両方に追加
- `tests/test_pdf_ops.py` - `TestInsertRollback`（5メソッド）・`TestDuplicateUndoTiming`（2メソッド）・`TestUndoRedoRestoreFailure`（4メソッド）を新設

## Decisions Made
- D-08〜D-10・D-14: `_do_insert` は「巻き戻しループで実際に `delete_page` が成功した件数（removed）を差し引いた残存数（residual）」を Undo state の件数フィールドへ書き込む実装を採用した。RESEARCH.md の概念パターンは `total` をそのまま書き込む簡易形だったが、`delete_page` が巻き戻しループの途中で失敗する部分成功ケースでも正確な残存数を反映できるよう removed 追跡版にした（Rule 1: total を過大計上すると、次回の undo が残存数より多い回数 `delete_page` を実行し既存ページまで削除してしまう潜在バグを防ぐため）。全 `delete_page` が即座に失敗する典型的な失敗系テストシナリオでは removed=0 のため residual=total と一致し、プランが要求する挙動・acceptance_criteria とは結果的に同一
- D-11: `_save_undo("duplicate", pno=pno)` の呼び出しシグネチャは変更せず、位置のみ `try` ブロック内・実処理完了後へ移動した
- D-13/D-14: `_undo`/`_redo` の例外ハンドラは `_dispose_state` を呼ばずスタックへ戻す（Pitfall 4 回避）。通知はモーダルな `messagebox.showerror` のみとし、トースト・ステータスバーは使わない（CONTEXT.md D-13 の確定方針どおり）

## Deviations from Plan

None - plan executed exactly as written（D-08 の残存数計算を `total` 直書きから `removed` 追跡版へ強化した点は上記 Decisions Made に記載のとおり Rule 1 相当の頑健化であり、プランの `must_haves`/`acceptance_criteria` が要求する可観測挙動とは一致する）。

### 検証グレップの既知の乖離（コード変更なし）

Task 2 の acceptance_criteria は `grep -n '_push_evicting(self._undo_stack, state)' pagefolio/file_ops.py` が1件を出力することを要求しているが、実際には2件出力される。追加の1件（188行目）は `_save_undo` 内の既存コード（本プラン非対象・変数名がたまたま `state` と一致しているだけ）であり、`_undo` の例外ハンドラ（205行目）とは無関係。振る舞いは `test_undo_restore_failure_returns_state_to_stack` / `test_undo_retry_after_failure_uses_same_state` で直接検証済みのため、実装は正しい。`_push_evicting(self._redo_stack, state)` 側は計画どおり1件（226行目）。

## Issues Encountered

None - フルテストスイート（1150件）・`ruff check .`・`ruff format --check .` すべて一発でグリーン。既知の Tcl/Tk フレーキー（STATE.md 記載事象）は本セッションでは発現しなかった。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V190-SAFE-04・V190-SAFE-05・V190-UNDO-01 の受け入れ条件（失敗時に操作前の状態へ確実に戻る・部分適用を無警告で残さない・Undo/Redo 履歴を失わない）を本プランの範囲で満たした
- D-12 の棚卸し（`_save_undo` の全16箇所の記録タイミング・Plan 05 が本格整理する素材）を以下に記録する:

| ファイル:行 | 呼び出し元 | op | 記録タイミング |
|---|---|---|---|
| page_ops.py:127 | `_rotate_selected` | rotate | 先置き（実処理前） |
| page_ops.py:163 | `_delete_selected` | delete | 先置き |
| page_ops.py:195 | `_duplicate_page` | duplicate | **後置き**（本プラン D-11 で是正済み） |
| page_ops.py:211 | `_insert_blank_page` | insert | 先置き |
| page_ops.py:242 | `_add_watermark_text` | page_edit | 先置き |
| page_ops.py:298 | `_add_watermark_image` | page_edit | 先置き |
| page_ops.py:332 | `_add_page_numbers` | page_edit | 先置き |
| page_ops.py:545 | `_crop_page`（単一ページ） | crop | 先置き |
| page_ops.py:598 | `_crop_page`（複数ページ一括） | bulk_crop | 先置き |
| page_ops.py:671 | `_crop_by_margin` | bulk_crop | 先置き |
| page_ops.py:775 | `_do_insert` | insert | 先置き＋巻き戻し方式（本プラン D-08 で例外安全化・後置化ではなくロールバックを選択） |
| page_ops.py:902 | `_do_merge_resize` | merge_resize | 先置き（Blob キャプチャ後・実ドキュメント変更前） |
| page_ops.py:938 | `_do_merge` | merge | 先置き |
| dnd.py:130 | D&D 複数ページ一括移動 | bulk_move | 後置き（`doc.select()` 実行後） |
| dnd.py:145 | D&D 単一ページ移動 | move | 後置き（`move_page()` 実行後） |
| redact_ops.py:151 | 黒塗り/モザイク適用 | page_edit | 先置き |

  記録が先置きのまま残る op（rotate/insert_blank/page_edit系3件/crop/bulk_crop系2件/merge/merge_resize）は本プランの対象外（D-12・要件対象は duplicate/insert の2経路のみ）。次マイルストーン候補として残す。
- 残る Wave 4 Plan（05: duplicate/merge/merge_resize の4手往復回帰テスト水平展開・記録先置き一覧の正式まとめ）は本プランが作成した `TestInsertRollback`/`TestDuplicateUndoTiming`/`TestUndoRedoRestoreFailure` と衝突しない独立ファイル面（同じ `tests/test_pdf_ops.py` 内だが別クラス・別メソッド）

---
*Phase: 01-safety-rollback*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: pagefolio/page_ops.py
- FOUND: pagefolio/file_ops.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_pdf_ops.py
- FOUND: .planning/phases/01-safety-rollback/01-04-SUMMARY.md
- FOUND commit: 7627a64
- FOUND commit: 681d22f
- FOUND commit: 727624a
- FOUND commit: 38440e7
- FOUND commit: 22f83d2
