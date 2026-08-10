---
phase: 01-safety-rollback
plan: 06
subsystem: undo-redo
tags: [pymupdf, fitz, undo-redo, rollback, blob-lifecycle, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-04（_undo/_redo の復元失敗保護・PartialRestoreError 基盤）と01-05（duplicate/merge/merge_resize の4手往復テスト水平展開）が本プランの土台"
provides:
  - "delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の7 op すべてで、部分失敗→再試行成功後も次段の逆デルタが完全な当初データを保持する方式（_pending_inverse・_merge_pending_inverse）"
  - "merge_undo が本欠陥の非該当であることを固定するピンテスト"
  - "蓄積逆デルタ用 Blob の evict/clear 時の解放と二重解放なしの機械検証"
  - "01-VERIFICATION.md Evidence 3・4 の再現手順をそのままテスト化した回帰テスト（V190-UNDO-01 の真の充足）"
affects: []

actuals:
  tokens: 13210
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "逆デルタの捕捉タイミングを『そのページを実際に mutate する瞬間』に統一する（mutation ループ内で蓄積）。_apply_inverse は op 名の決定のみを担当し、mutation より前に data を先取り構築しない（per-page op 全 7 種で統一）"
    - "_merge_pending_inverse(state, applied) は state から _pending_inverse を pop（取り出して削除）し applied と連結・page_index 昇順ソートして返す。pop であることで Blob 所有権が state → 返り値（次段 inverse["data"]）へ明示的に移り、_dispose_state(state) が後で呼ばれても二重解放が起きない"
    - "identity 共有が必要な op（merge_resize/merge_resize_undo）は _apply_inverse の inv[\"data\"] is state[\"data\"] を維持したまま、_restore_state 側で共有 dict の中身（d[\"orig_pages\"]）を _merge_pending_inverse の結果で差し替える（dict をまるごと入れ替えない）。_undo/_redo の disposal 判定（identity 比較）を壊さないための必須パターン"
    - "スカラーのみを運ぶ逆デルタ（merge_undo の old_count）は本欠陥の構造的な非該当であり、他 7 op と同型の往復テストで『非該当であること自体』を明示的にピン留めする"

key-files:
  created: []
  modified:
    - pagefolio/file_ops.py
    - tests/test_pdf_ops.py
    - tests/test_undo_stress.py

key-decisions:
  - "Task 0（checkpoint:decision）は方式 A（mutation ループ内で実際に適用できたページ分の逆データを蓄積し、部分失敗時は _pending_inverse として remaining_state へ引き継いで再試行時に合流させる）をオーケストレーターが事前提示・ユーザーが選択済みとして実行を開始した。方式 B（state[\"_original_data\"] に全件保持）は delete_redo/page_edit/insert_redo の3 op で成立しないため不採用という PLAN.md の事前検討どおり"
  - "merge_undo ピンテストの assertion 対象スタックを PLAN.md <behavior> 記載の app._redo_stack[-1] から app._undo_stack[-1] へ修正した（Rule 1・自動修正）。実装コードを変更する前に空実装（file_ops.py の Task3 差分を git stash で一時退避）で実測した結果、merge → undo → redo(fail) → redo(retry,success) の手順で『再試行成功直後に構築される scalar な merge state』は _redo() が _undo_stack へ push する（_redo() は常に inverse を undo_stack へ積む設計のため）ことを確認した。_redo_stack へ merge（scalar）state が来ることは _apply_inverse のマッピング（op:\"merge\"→inv.op:\"merge_undo\"、op:\"merge_undo\"→inv.op:\"merge\"）とスタックの alternation 不変条件から構造的に起こり得ない。PLAN.md の acceptance_criteria が意図する『merge_undo の逆デルタが old_count のみのスカラーで部分失敗の影響を受けない』という検証意図は変更せず、参照先スタックのみを実際に検証可能な undo_stack へ訂正した"
  - "Task 3 の merge_resize_undo テストヘルパーとして、TestAllOpsUndoRedoRoundtrip._make_full_fake_app と既存の test_merge_resize_undo_partial_failure_preserves_remaining_and_retry_completes のインライン FakeApp を雛形に、TestUndoRedoRestoreFailure._make_full_fake_app(n_pages=4) を新設した（PLAN.md action (5) の指示どおり）。既存テストメソッドのインライン定義はそのまま残した"

requirements-completed: [V190-UNDO-01]

coverage:
  - id: D1
    description: "delete の undo が部分失敗→再試行成功した後に redo すると、当初 delete 対象だった全ページが削除される（Evidence 3 の再現）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_delete_undo_partial_retry_then_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D2
    description: "delete_redo の redo が部分失敗→再試行成功した後に undo/redo を続けても全ページが正しく往復する"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_delete_redo_partial_retry_then_undo_redo_roundtrip"
        status: pass
    human_judgment: false
  - id: D3
    description: "page_edit の undo が部分失敗→再試行成功した後、redo で両ページとも編集後の内容に戻り undo で編集前に戻る"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_page_edit_partial_retry_then_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D4
    description: "insert_undo の redo（再挿入）が部分失敗→再試行成功後、undo/redo で挿入分が完全に往復する"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_insert_undo_partial_retry_then_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D5
    description: "insert_redo の undo（削除）が部分失敗→再試行成功後、undo/redo で挿入分が完全に往復する"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_insert_redo_partial_retry_then_undo_redo_roundtrip"
        status: pass
    human_judgment: false
  - id: D6
    description: "merge_resize の undo が部分失敗→再試行成功後、redo で結合ページ内容が破損せず、undo で結合前の内容に完全に戻る（Evidence 4 の再現）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_merge_resize_undo_partial_retry_then_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D7
    description: "merge_resize_undo の redo が部分失敗→再試行成功後、undo/redo でページ構成・内容が完全に往復する"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_merge_resize_redo_partial_retry_then_undo_redo_roundtrip"
        status: pass
    human_judgment: false
  - id: D8
    description: "merge_undo は逆デルタが old_count スカラーのみのため本欠陥の非該当であることが、同型の往復テストで明示的に固定されている"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_merge_undo_partial_retry_roundtrip_inverse_unaffected"
        status: pass
    human_judgment: false
  - id: D9
    description: "部分失敗を経由した state が再試行されないまま evict/clear された場合も、蓄積された逆デルタ用 Blob を含めて全解放され一時ファイルが残らない"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_pending_inverse_blobs_released_on_stack_clear"
        status: pass
    human_judgment: false
  - id: D10
    description: "5手往復のどの段階でも、同一 Blob に対する release() が2回以上呼ばれない"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_partial_retry_roundtrip_no_double_release"
        status: pass
    human_judgment: false
  - id: D11
    description: "cb5344e が閉じた『復元失敗直後の即時二重適用』防止と D-13 のブロッキング通知が退行していない（既存 TestUndoRedoRestoreFailure 3件・WR-01 ピンが green のまま）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure (既存3件) / TestAllOpsUndoRedoRoundtrip::test_delete_undo_apply_inverse_does_not_capture_blob"
        status: pass
    human_judgment: false
  - id: D12
    description: "ruff check / ruff format --check / フルテストスイート(pytest -q) の3ゲートがすべて green"
    verification:
      - kind: other
        ref: "ruff check . && ruff format --check . && pytest -q（1177 passed）"
        status: pass
    human_judgment: false

duration: 約45min
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 6: Undo/Redo 逆デルタ縮小によるデータ破損の是正 Summary

**delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の7 opで、部分失敗→再試行成功後に次段の逆デルタが「再試行分のみに縮小」して確定するサイレントなデータ破損（01-VERIFICATION.md Evidence 3・4）を、mutation ループ内で実際に適用できたページ分の逆データを蓄積する方式（_pending_inverse・_merge_pending_inverse）で解消し、merge_undoの非該当性をピン留めした**

## Performance

- **Duration:** 約45分
- **Completed:** 2026-08-10
- **Tasks:** 3/3（Task 0 は checkpoint:decision・決定記録のみでコード変更なし）
- **Files modified:** 3（`pagefolio/file_ops.py`, `tests/test_pdf_ops.py`, `tests/test_undo_stress.py`）

## Accomplishments

- `01-VERIFICATION.md` が FAILED と判定した Truth 5（V190-UNDO-01 / ROADMAP Success Criterion 5）を閉じた。cb5344e（CR-01）は「復元失敗直後の即時二重適用」を解消したが、`_apply_inverse` が常に `state["data"]`（部分失敗の再試行時には縮小済み）を次段逆デルタの元データとして使い回す設計のため、**バグを移し替えていた**（再試行成功直後の doc/スタック状態は正しく見えても、その後の redo/undo でページの欠落・内容混入が発生）
- `_restore_state` の mutation ループを「実際に適用できたページ分の逆データを、そのページを mutate する瞬間に蓄積する」方式へ変更した（7 op 全展開）。新設ヘルパー `_merge_pending_inverse(state, applied)` が、state から `_pending_inverse`（前回までの蓄積分）を pop して `applied`（今回分）と合流・page_index 昇順ソートして返す。pop であることで Blob 所有権が明示的に state → 返り値へ移り、`_dispose_state` による二重解放を構造的に防ぐ
- `_restore_partial_error` に `pending_inverse` 引数を追加し、部分失敗時に `remaining_state["_pending_inverse"]` として蓄積分を引き継ぐ（`None` の場合は `dict(state)` により前回までの蓄積が自然に継承される既定挙動は不変）
- merge_resize/merge_resize_undo は `_apply_inverse` の identity 共有（`inv["data"] is state["data"]`）を維持したまま、共有 dict の中身（`orig_pages`）だけを `_merge_pending_inverse` で差し替える方式にした（`_undo`/`_redo` の disposal 判定を壊さないための必須パターン）。あわせて `_merged_page_deleted` フラグを完了時に取り除き、Evidence 4 の「5ページ化・内容混入」の副次的原因（フラグの持ち越し）も同時に解消した
- `merge_undo` は逆デルタが `old_count` スカラーのみを運ぶため本欠陥の非該当であり、他 7 op と同型の 5 手以上往復テストで**非該当であること自体**を明示的にピン留めした
- 蓄積逆デルタ用 Blob の解放を `_dispose_state` へ拡張（`_pending_inverse` エントリも走査対象に追加）し、evict/clear 時のリーク・往復中の二重解放なしを機械検証する 2 件のストレステストを追加した
- 01-VERIFICATION.md の Evidence 3・4 の再現手順をそのまま回帰テスト化: delete undo→retry→redo で「両ページとも削除される」（欠陥時は1ページのみ）、merge_resize undo→retry→redo→undo で「4ページ・内容一致に戻る」（欠陥時は5ページ・内容混入）ことを実測確認
- 8 メソッド（`test_delete_undo_partial_retry_then_redo_undo_roundtrip` / `test_delete_redo_partial_retry_then_undo_redo_roundtrip` / `test_page_edit_partial_retry_then_redo_undo_roundtrip` / `test_insert_undo_partial_retry_then_redo_undo_roundtrip` / `test_insert_redo_partial_retry_then_undo_redo_roundtrip` / `test_merge_resize_undo_partial_retry_then_redo_undo_roundtrip` / `test_merge_resize_redo_partial_retry_then_undo_redo_roundtrip` / `test_merge_undo_partial_retry_roundtrip_inverse_unaffected`）を `TestUndoRedoRestoreFailure` へ追加し、2 件（`test_pending_inverse_blobs_released_on_stack_clear` / `test_partial_retry_roundtrip_no_double_release`）を `TestBlobLeakDetection` へ追加した
- フルテストスイート 1177 件グリーン（01-VERIFICATION.md 記載のベースライン 1167 件 + 本プラン新規10件）。`ruff check .` / `ruff format --check .` ともにグリーン。既知の Tcl/Tk フレーキーは本セッションでは発現しなかった

## Task Commits

Each task was committed atomically (TDD の RED→GREEN 構成):

1. **Task 0: 逆デルタのデータモデル変更方式の確定（checkpoint:decision）** - オーケストレーターが提示し方式 A（option-a）が事前選択済み。コード変更なし・コミットなし
2. **Task 1: delete/delete_redo の逆デルタ蓄積方式を end-to-end で成立させる** - `f9973ce`（test/RED）→ `a8cc933`（feat/GREEN）
3. **Task 2: page_edit/insert_undo/insert_redo への蓄積方式の展開** - `a56ed06`（test/RED）→ `eb5b6f1`（feat/GREEN）
4. **Task 3: merge_resize/merge_resize_undo の展開・merge_undo 非該当ピン・Blob 解放とフェーズ最終ゲート** - `b6c7bc8`（test/RED）→ `e41b7e3`（feat/GREEN）

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: Task 3 の RED 確認は、file_ops.py の Task 3 差分を `git stash` で一時退避し（Task 1/2 の実装は残したまま）新規 3 テストが実際に失敗することを確認した後、`git stash pop` で復元してから実装した（merge_resize/merge_resize_undo の修正は Task 1/2 とは独立したコード領域のため、この手順で正確な RED を得られる）。_

## Files Created/Modified

- `pagefolio/file_ops.py` - `_merge_pending_inverse` を新設。`_restore_partial_error` に `pending_inverse` 引数を追加。`_dispose_state` を `_pending_inverse` の Blob も解放するよう拡張。`_apply_inverse`/`_restore_state` の delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の7分岐を蓄積方式へ変更
- `tests/test_pdf_ops.py` - `TestUndoRedoRestoreFailure` へ 8 メソッド + `_make_full_fake_app` ヘルパーを追加
- `tests/test_undo_stress.py` - `TestBlobLeakDetection` へ 2 メソッドを追加

## Decisions Made

- Task 0（checkpoint:decision）は方式 A（推奨）を採用（`## key-decisions` frontmatter に詳細を記録）
- merge_undo ピンテストの assertion 対象スタックを、実測に基づき `app._redo_stack[-1]` から `app._undo_stack[-1]` へ訂正した（PLAN.md の behavior 記述の誤りを Rule 1 で自動修正。詳細は `## key-decisions` frontmatter を参照）
- Task 3 で `TestUndoRedoRestoreFailure._make_full_fake_app(n_pages=4)` を新設（PLAN.md action (5) の指示どおり。既存インライン FakeApp 定義は変更しない）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] merge_undo ピンテストの assertion 対象スタックを訂正**

- **Found during:** Task 3（`test_merge_undo_partial_retry_roundtrip_inverse_unaffected` の RED 確認）
- **Issue:** PLAN.md の `<behavior>` は「再試行成功直後の `app._redo_stack[-1]` が `op=="merge"` かつ `data` が int」と記述していたが、`_apply_inverse` のマッピング（`merge`→`merge_undo`、`merge_undo`→`merge`）と `_undo`/`_redo` のスタック push 方向（`_redo()` は常に結果を `undo_stack` へ積む）から、scalar な `merge` state が `redo_stack` に現れることは構造的に起こり得ないことを、Task 3 実装前（file_ops.py の Task 3 差分を一時退避した状態）での実測で確認した
- **Fix:** assertion 対象を `app._undo_stack[-1]` へ訂正した。検証意図（merge_undo の逆デルタが old_count のみのスカラーで部分失敗の影響を受けないこと）は変更していない
- **Files modified:** `tests/test_pdf_ops.py`
- **Verification:** 訂正後のテストは Task 3 実装前後どちらでも意味のある検証として成立する（merge_undo は元々本欠陥の対象外のため実装変更なしで green、これは想定どおり）
- **Committed in:** `b6c7bc8`（Task 3 test commit）

---

**Total deviations:** 1 auto-fixed（Rule 1 - テスト記述の技術的誤りの訂正）
**Impact on plan:** 検証意図・カバレッジに変更なし。参照先スタックのみの訂正であり、スコープ拡大なし。

## Issues Encountered

None - `ruff check .`・`ruff format --check .`・`pytest -q`（フルスイート 1177 件）すべて一発でグリーン。既知の Tcl/Tk フレーキー（STATE.md 記載事象）は本セッションでは発現しなかった。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V190-UNDO-01 の受け入れ条件（Undo/Redo の復元処理が失敗しても履歴が失われず Document が部分変更のまま残らない）を、01-VERIFICATION.md が発見した新経路（Evidence 3・4）まで含めて満たした
- Phase 1（保存・編集・設定の安全性是正）は本プラン（06・ギャップ是正）をもって全 9 要件（V190-SAFE-01〜05・CFG-01/02・UNDO-01/02）を充足
- 次のアクションは Phase 1 の再検証（`/gsd-verify-work` 相当）を経て Phase 2（OCR プロバイダ基盤整理 + OpenAI プロバイダ追加）へ進むこと

---

*Phase: 01-safety-rollback*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: pagefolio/file_ops.py
- FOUND: tests/test_pdf_ops.py
- FOUND: tests/test_undo_stress.py
- FOUND: .planning/phases/01-safety-rollback/01-06-SUMMARY.md
- FOUND commit: f9973ce
- FOUND commit: a8cc933
- FOUND commit: a56ed06
- FOUND commit: eb5b6f1
- FOUND commit: b6c7bc8
- FOUND commit: e41b7e3
