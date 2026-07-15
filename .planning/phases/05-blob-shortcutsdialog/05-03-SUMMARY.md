---
phase: 05-blob-shortcutsdialog
plan: 03
subsystem: infra
tags: [undo-redo, blob-lifecycle, leak-detection, pytest, tempfile]

# Dependency graph
requires:
  - phase: 05-blob-shortcutsdialog (05-01)
    provides: pagination.py 純ロジック層の拡張系譜（Tk/fitz 非依存の純ロジック層集約パターン）
provides:
  - MemBlob/FileBlob の _released フラグ + __del__ によるリーク・二重解放検出（V180-ROBUST-01）
  - Windows AV スキャン衝突（PermissionError）・double-release連鎖・tmpdir残留の3項目回帰テスト（D-14①②③）
affects: [05-04（ShortcutsDialog WR-01/WR-02）, Phase 6（品質保証仕上げ）]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "__del__ + _released フラグによる軽量リーク検出（weakref レジストリ不採用・D-11）"
    - "sys.is_finalizing() によるインタプリタ終了時の __del__ 誤動作抑止（PEP 442）"

key-files:
  created:
    - .planning/phases/05-blob-shortcutsdialog/deferred-items.md
  modified:
    - pagefolio/undo_store.py
    - tests/test_undo_stress.py

key-decisions:
  - "D-14② の回帰テストは計画書許可の代替案（delete+undo+redo+undo）を採用。insert 版で file_ops.py の insert_redo restore に既存のページ重複バグを発見したため、pagination/undo_store 以外のファイルは無改造の原則を守り deferred-items.md へ記録した"

patterns-established:
  - "Blob サブクラス（MemBlob/FileBlob）の __del__ は sys.is_finalizing() 早期 return + except Exception as e: 握り潰しで終了時も安全"

requirements-completed: [V180-ROBUST-01]

coverage:
  - id: D1
    description: "MemBlob/FileBlob が _released フラグ + __del__ でリーク・二重解放を検出する"
    requirement: "V180-ROBUST-01"
    verification:
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_permission_error_on_unlink_does_not_crash"
        status: pass
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_double_release_chain_delete_undo_redo_undo"
        status: pass
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_tmpdir_cleared_no_false_positive_leak"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-16
status: complete
---

# Phase 5 Plan 3: Blobリーク検出強化 Summary

**MemBlob/FileBlob へ `_released` フラグ + `__del__` を追加しリーク・二重解放を警告ログで検出、Windows AV 衝突（PermissionError mock）・double-release連鎖・tmpdir残留の3項目を回帰テストで固定**

## Performance

- **Duration:** 約15分
- **Tasks:** 2
- **Files modified:** 2（+ 1 新規記録ファイル）

## Accomplishments
- `FileBlob`/`MemBlob` に `_released` フラグと `__del__` を追加し、release されないまま GC されたリーク・release の二重呼び出しを `logger.warning` で検出できるようにした（V180-ROBUST-01）
- `__del__` は `sys.is_finalizing()` 早期 return + `except Exception as e:`（裸の except 禁止規約準拠）でインタプリタ終了時にも例外を伝播させない
- 既存の `contextlib.suppress(OSError)` による Windows AV `PermissionError` 握り潰しは無改造のまま維持
- `tests/test_undo_stress.py` に `TestBlobLeakDetection` を新設し、D-14 の3項目（① AV衝突mock ② double-release連鎖 ③ tmpdir残留+偽陽性なし）を回帰テスト化

## Task Commits

Each task was committed atomically:

1. **Task 1: MemBlob/FileBlob へ _released フラグ + __del__ リーク検出を追加** - `2adeaf1` (feat)
2. **Task 2: D-14 の3項目回帰テストを test_undo_stress.py へ追加** - `fcf6818` (test)

## Files Created/Modified
- `pagefolio/undo_store.py` - `MemBlob`/`FileBlob` に `_released` フラグ・二重解放検出付き `release()`・`__del__`（リーク検出+ベストエフォート回収）を追加
- `tests/test_undo_stress.py` - `TestBlobLeakDetection` クラス新設（3テスト）。`import gc`・`import logging`・`import pagefolio.undo_store as undo_store` を追加
- `.planning/phases/05-blob-shortcutsdialog/deferred-items.md`（新規） - insert→undo→redo→undo でページが重複する既存バグ（`file_ops.py`）の記録

## Decisions Made
- D-14② の回帰テストは、計画書（05-03-PLAN.md）が明示的に許可する代替案「delete+undo+redo+undo」を採用した。理由は下記「Deviations from Plan」参照。

## Deviations from Plan

### Auto-fixed Issues

None（`undo_store.py`/`test_undo_stress.py` の改修自体は計画どおり実装し、追加の Rule 1〜3 自動修正は発生しなかった）

### Out-of-Scope Discovery（Rule外・SCOPE BOUNDARY 準拠で未修正・記録のみ）

**1. `pagefolio/file_ops.py` の insert→undo→redo→undo（2回目の undo）でページが重複するバグ**
- **発見の経緯:** Task 2 の D-14② テスト（計画書は「insert→undo→redo→undo、または delete+undo+redo+undo」のいずれかを許可）を実装する過程で、まず insert 版を手動シミュレーションしたところ、2回目の `_undo()` 後にページ数が想定の3ページではなく5ページ（重複）になることを発見した。
- **原因（推定）:** `_restore_state()` の `elif op == "insert_redo":` ブロックがページを再挿入しており、`delete`/`delete_redo` の対称パターン（削除↔挿入を交互）に倣うなら削除であるべき箇所。
- **対応:** 05-03 の `files_modified` は `undo_store.py`/`test_undo_stress.py` のみであり `file_ops.py` は対象外（SCOPE BOUNDARY: 現在のタスク変更が直接原因ではない既存バグは自動修正しない）。計画書が明示的に許可する代替案（delete+undo+redo+undo。delete/delete_redo は対称実装のためこのバグの影響を受けない）を採用してD-14②の目的（Blob double-release非発生の検証）を満たした。
- **記録先:** `.planning/phases/05-blob-shortcutsdialog/deferred-items.md`（原因分析・再現コード・推奨対応を記載）
- **影響:** Blob ライフサイクル（本フェーズのスコープ）には影響なし。release() は常に1回ずつ正しく呼ばれることを確認済み。ページ内容の往復整合性のみに影響する別種のバグ。

---

**Total deviations:** 1 out-of-scope discovery（未修正・記録のみ。Rule 1〜3 の自動修正は0件）
**Impact on plan:** 計画の完遂には影響なし。D-14②は計画書許可の代替アプローチで完全に満たした。

## Issues Encountered
None

## User Setup Required
None - 外部サービス設定は不要。

## Next Phase Readiness
- V180-ROBUST-01 完了。Blob ライフサイクルのリーク・二重解放検出とその回帰テストが整備された。
- `pagefolio/file_ops.py` の insert 往復バグ（deferred-items.md 記録）は次フェーズ以降（Phase 6 品質保証仕上げ、または別途クイックタスク）での対応候補。
- 05-04（ShortcutsDialog WR-01/WR-02）への依存・ブロッカーなし。

---
*Phase: 05-blob-shortcutsdialog*
*Completed: 2026-07-16*
