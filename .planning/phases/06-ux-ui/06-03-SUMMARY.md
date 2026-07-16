---
phase: 06-ux-ui
plan: 03
subsystem: core
tags: [pymupdf, undo-redo, changelog-audit, regression-test]

# Dependency graph
requires:
  - phase: 06-ux-ui (06-01)
    provides: "pagefolio/file_ops.py の保存系トースト化（同一ファイルの後続編集）"
provides:
  - "file_ops.py._restore_state の insert_redo ブロック修正（delete_redo 対称パターン化・ページ重複バグ解消）"
  - "tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip（insert 4手往復回帰テスト）"
  - ".planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md（開発履歴.md 日付整合監査記録）"
  - "開発履歴.md の v1.6.1 日付誤記修正（2026-06-22→2026-06-23）"
  - ".planning/PROJECT.md の V16-D-04 ステータス解消済み更新"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Undo/Redo デルタ復元の対称性原則: _apply_inverse の op 名に対応する _restore_state 側アクションは常に対称（挿入↔削除）であることを確認する（delete_redo ↔ insert_redo）"

key-files:
  created:
    - .planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md
  modified:
    - pagefolio/file_ops.py
    - tests/test_pdf_ops.py
    - 開発履歴.md
    - .planning/PROJECT.md

key-decisions:
  - "insert_redo 修正は delete_redo（348-358行目）の対称実装に倣い、昇順インデックスを降順で doc.delete_page する実装へ変更。修正範囲を _restore_state の insert_redo ブロックのみに限定し、_apply_inverse・他 op（delete/page_edit/merge 系等）は無変更（D-17）"
  - "開発履歴.md 整合監査で v1.6.1 の日付誤記1件を検出（開発履歴.md記載2026-06-22 vs 実際のタグ/MILESTONES.md記載2026-06-23）。3箇所（最終更新サマリ・索引テーブル・セクション見出し）を修正。V16-D-04が懸念していた「一時v1.7.0バンプの痕跡」はgit履歴上に現存せず既に解消済みと確認（D-14）"
  - "旧PDF Editor時代の同名バージョン見出しは意図的共存として無改変で維持（D-15）。MILESTONES.mdにv1.6.4の独立セクションが無い点は観測事項として監査記録に残すのみで対応せず（本プランのfiles_modified対象外）"

patterns-established:
  - "Pattern: Undo/Redo デルタ復元の対称性は _apply_inverse と _restore_state の op ペアを常に突き合わせて検証する（本プランはこの原則の1箇所適用）"

requirements-completed: [V180-QA-04]

coverage:
  - id: D1
    description: "insert→undo→redo→undo（2回目）の4手往復でページ数・内容が正しく往復し、挿入ページが重複しない（D-17）"
    requirement: "V180-QA-04"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D2
    description: "insert_redo の修正が _restore_state の insert_redo ブロックのみに限定され、_apply_inverse・他 op（delete/delete_redo/page_edit/insert/insert_undo/merge系）の対称性を壊していない"
    requirement: "V180-QA-04"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py（既存 insert 系3テスト）・tests/test_undo_stress.py（全件）"
        status: pass
    human_judgment: false
  - id: D3
    description: "開発履歴.md の PageFolio 時代エントリ（v1.0.0〜v1.7.4）が git タグ履歴・APP_VERSION 変更履歴・MILESTONES.md と突合され、不一致（v1.6.1 日付誤記）が検出・修正される（D-14）"
    requirement: "V180-QA-04"
    verification:
      - kind: other
        ref: ".planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md（確認範囲・判定根拠・修正内容を記載）"
        status: pass
    human_judgment: false
  - id: D4
    description: "旧 PDF Editor 時代の同名バージョン見出しが改変されず、監査記録に意図的共存として明記される（D-15）"
    requirement: "V180-QA-04"
    verification:
      - kind: other
        ref: ".planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md（旧 PDF Editor 時代エントリの意図的共存セクション）"
        status: pass
    human_judgment: false
  - id: D5
    description: "PROJECT.md の V16-D-04 ステータスが解消済みへ更新され、V16-D-05 行・他の決定行は不変（D-16）"
    requirement: "V180-QA-04"
    verification:
      - kind: other
        ref: ".planning/PROJECT.md（V16-D-04行のgit diff・scoped編集を確認）"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-16
status: complete
---

# Phase 6 Plan 03: 開発履歴.md整合監査 + insert_redo非対称復元バグ修正 Summary

**delete_redo対称パターンでinsert_redoのページ重複バグを修正し4手往復回帰テストを追加。開発履歴.mdをgitタグ・APP_VERSION履歴・MILESTONES.mdと突合してv1.6.1日付誤記を検出・修正し、PROJECT.mdのV16-D-04を解消済みへ更新**

## Performance

- **Duration:** 約20分
- **Started:** 2026-07-16T20:26:00+09:00
- **Completed:** 2026-07-16T20:40:00+09:00
- **Tasks:** 3
- **Files modified:** 5（新規1・改修4）

## Accomplishments
- `pagefolio/file_ops.py._restore_state()` の `insert_redo` ブロックが `doc.insert_pdf` で再挿入していたバグ（insert→undo→redo→undo の2回目でページが重複）を、`delete_redo`（348-358行目）の対称実装に倣い `doc.delete_page`（降順削除）へ修正（D-17）
- `tests/test_pdf_ops.py::TestInsertUndoRedo` へ `test_insert_undo_redo_undo_roundtrip`（insert→undo→redo→undo の4手往復）を新規追加。修正前は RED（len(doc) が本来3のところ5になる）を確認した上で修正しGREEN化（TDD RED/GREEN）
- 開発履歴.md を git タグ履歴・APP_VERSION 変更履歴（`git log --follow -p -- pagefolio/constants.py`）・`.planning/MILESTONES.md` と突合し、v1.6.1 の日付誤記（記載2026-06-22 vs 実際のタグ/リリース日2026-06-23）を検出・3箇所修正
- V16-D-04 が懸念していた「v1.6.0 期に一時 v1.7.0 へバンプ後巻き戻した痕跡」を git 履歴上で直接検証し、現存しない（既に解消済み）ことを確認
- `.planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md` を新規作成し、確認範囲・判定根拠・修正内容・旧 PDF Editor 時代エントリの意図的共存（D-15）を記録
- `.planning/PROJECT.md` の Key Decisions テーブル V16-D-04 を「⚠️ Revisit」から「✅ 解消済み」へ更新（06-CHANGELOG-AUDIT.md参照を明記）

## Task Commits

Each task was committed atomically (TDD Task 1 has RED→GREEN commits):

1. **Task 1 (RED): insert_redo非対称復元バグを検出する4手往復回帰テストを追加** - `fc1157d` (test)
2. **Task 1 (GREEN): insert_redoの非対称復元バグを修正しページ重複を解消** - `8a0ebd3` (fix)
3. **Task 2: 開発履歴.mdの日付整合監査（D-14/D-15/D-16）** - `9edf06d` (docs)
4. **Task 3: PROJECT.mdのV16-D-04ステータスを解消済みへ更新** - `ed5e584` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pagefolio/file_ops.py` - `_restore_state()` の `insert_redo` ブロックを削除（降順）へ修正（D-17）
- `tests/test_pdf_ops.py` - `TestInsertUndoRedo` へ4手往復回帰テストを追加
- `開発履歴.md` - v1.6.1 の日付誤記を3箇所修正（最終更新サマリ・索引テーブル・セクション見出し）
- `.planning/PROJECT.md` - V16-D-04 のステータスを「✅ 解消済み」へ更新
- `.planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md` - 開発履歴.md 整合監査記録（新規）

## Decisions Made
- insert_redo 修正は delete_redo の対称実装（昇順インデックスを降順で delete_page）へ倣い、修正範囲を insert_redo ブロックのみに限定（D-17。他 op・`_apply_inverse`・`_dispose_state` は無変更を git diff で確認済み）
- 開発履歴.md の v1.6.1 日付は「タイムアウト拡大の実装日（2026-06-22）」ではなく「タグ/リリース完了日（2026-06-23。パスワード対応・印刷機能を含む全体が完成した日）」を正とし、他の全エントリと同じ基準（タグ作成日=出荷日）に揃えた
- MILESTONES.md に v1.6.4 の独立セクションが無い点は本プランの files_modified 対象外（開発履歴.md のみが対象）のため、修正せず監査記録に観測事項として記録するに留めた

## Deviations from Plan

None - plan executed exactly as written. Task 1 の TDD RED/GREEN 手順・Task 2/3 の監査内容とも計画どおりに実施した。

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V180-QA-04 完了。フルスイート 1096 件グリーン・ruff クリーン
- Phase 6（品質保証仕上げ）は本プラン（Plan 03・Wave 2）の完了により全3プラン完了。フェーズレベル検証へ進める
- **繰り越し項目（レビュー R6・明示的 defer）**: `duplicate` / `merge` / `merge_resize` 等の他ページ構造変更 op に対する do→undo→redo→undo の4手往復回帰テストの水平展開は本フェーズでは実施せず、次マイルストーンの回帰テスト強化候補として繰り越す。insert_redo と同型の非対称復元バグが他 op に潜在していないかは未検証（STATE.md の Deferred Items へも転記予定）

---
*Phase: 06-ux-ui*
*Completed: 2026-07-16*
