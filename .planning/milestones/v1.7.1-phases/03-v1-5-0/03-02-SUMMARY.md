---
phase: 03-v1-5-0
plan: 02
subsystem: testing
tags: [pymupdf, fitz, pytest, pure-functions, dnd, shortcuts, toc]

# Dependency graph
requires: []
provides:
  - "D&D 挿入位置計算の純関数 compute_dnd_dest_index（pagefolio/dnd.py）"
  - "ショートカットマージ/Shift大文字補完判定の純関数 merge_shortcuts / shift_variant_keysym（pagefolio/app.py）"
  - "tests/test_v150_regression.py（新規・v1.5.0回帰テスト専用ファイル・D-15）"
  - "test_pdf_ops.py の TestContentOpsUndoFix への内容検証強化（D-14）"
affects: [03-03, 03-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk依存の薄いラッパー＋module-level純関数への抽出（pagination.py既定パターンの踏襲・D-13）"
    - "FakeApp mixin方式（FileOpsMixin/PageOpsMixin/RedactOpsMixin合成）でTOC操作をfitz.Documentごと検証"

key-files:
  created:
    - tests/test_v150_regression.py
  modified:
    - pagefolio/dnd.py
    - pagefolio/app.py
    - tests/test_pdf_ops.py

key-decisions:
  - "_dnd_dest_index はTk依存部（winfo_*/canvasy/event）のみ残し、cursor_y と frame_bounds 列からの index 算出は compute_dnd_dest_index へ完全委譲"
  - "merge_shortcuts/shift_variant_keysym は app.py module-level関数として抽出（新規モジュール化はRESEARCH.md A4の通り投資対効果が低いため見送り）"
  - "TOC回帰テストは削除・結合・分割（範囲/全ページ）の4パターンをFakeAppで直接検証（must_havesの3機能を上回る網羅）"

patterns-established:
  - "純関数抽出後も既存メソッド名・シグネチャ・実際のTk/fitz呼び出し順序は完全に不変（挙動保存のリファクタリング）"

requirements-completed: [V171-TEST-01]

coverage:
  - id: D1
    description: "D&D の挿入位置計算が純関数 compute_dnd_dest_index として抽出され、合成データで直接テストできる"
    requirement: "V171-TEST-01"
    verification:
      - kind: unit
        ref: "tests/test_v150_regression.py::TestDndDestIndex"
        status: pass
    human_judgment: false
  - id: D2
    description: "ショートカットのマージと Shift 大文字補完判定が純関数として抽出され直接テストできる"
    requirement: "V171-TEST-01"
    verification:
      - kind: unit
        ref: "tests/test_v150_regression.py::TestShortcutMerge"
        status: pass
    human_judgment: false
  - id: D3
    description: "削除/結合/分割時の TOC 保持・再採番が FakeApp で回帰検証される"
    requirement: "V171-TEST-01"
    verification:
      - kind: unit
        ref: "tests/test_v150_regression.py::TestTocPreservation"
        status: pass
    human_judgment: false
  - id: D4
    description: "既存 undo 往復テスト（白紙挿入・テキスト透かし・ページ番号）へ内容検証（ページサイズ一致・get_text 抽出）が追加される"
    requirement: "V171-TEST-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestContentOpsUndoFix (roundtrip系3件)"
        status: pass
    human_judgment: false
  - id: D5
    description: "抽出リファクタ前後で root.bind / D&D 挙動が不変で、既存テスト群がグリーン"
    requirement: "V171-TEST-01"
    verification:
      - kind: unit
        ref: "pytest フルスイート（805件）"
        status: pass
    human_judgment: false

# Metrics
duration: 7min
completed: 2026-07-05
status: complete
---

# Phase 3 Plan 2: v1.5.0 回帰テスト整備（V171-TEST-01）Summary

**D&D挿入位置計算とショートカットマージを純関数へ抽出し、TOC保持・D&D・ショートカットの3系統回帰テストを新規ファイルへ整備、既存undo往復テストへ内容検証を追加**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-05T14:57:21Z（前タスク完了直後）
- **Completed:** 2026-07-05T15:07:07Z
- **Tasks:** 3
- **Files modified:** 4（うち新規1）

## Accomplishments
- `pagefolio/dnd.py` に `compute_dnd_dest_index(cursor_y, frame_bounds)` 純関数を抽出。`_dnd_dest_index` は Tk 依存部（`winfo_*`/`canvasy`/`event`）のみ残す薄いラッパーへ改修
- `pagefolio/app.py` に `merge_shortcuts(default, custom)` / `shift_variant_keysym(keysym)` 純関数を抽出。`__init__` のショートカットマージ・Shift大文字補完ループを委譲する薄い形へ改修
- `tests/test_v150_regression.py` を新規作成（D-15）。`TestDndDestIndex`（境界値7件）・`TestShortcutMerge`（マージ/判定7件）・`TestTocPreservation`（削除/結合/範囲分割/全ページ分割の4件）で計18テストを追加
- `tests/test_pdf_ops.py` の `TestContentOpsUndoFix` 既存3メソッドへ内容検証を追記（D-14）: 白紙挿入のページサイズ一致・透かし/ページ番号の undo 後元コンテンツ保持を全選択ページ分（未選択ページ含む）で厚く検証
- `pytest` フルスイート 805 件グリーン（従来787件から+18）・`ruff check`/`ruff format --check` クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: 純ロジック抽出（compute_dnd_dest_index / merge_shortcuts / shift_variant_keysym）** - `8ed8217` (refactor)
2. **Task 2: 回帰テスト新規ファイル（D&D 位置・ショートカット・TOC 保持）** - `37cb618` (test)
3. **Task 3: 既存 undo 往復テストへ内容検証を追加（D-14）** - `f879091` (test)
4. **[フォローアップ] ruff format 整形（shift_variant_keysym 条件式1行化）** - `d215972` (style)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/dnd.py` - `compute_dnd_dest_index` 純関数を追加、`_dnd_dest_index` を薄いラッパー化
- `pagefolio/app.py` - `merge_shortcuts`/`shift_variant_keysym` 純関数を追加、`__init__` から委譲
- `tests/test_v150_regression.py` (新規) - `TestDndDestIndex`/`TestShortcutMerge`/`TestTocPreservation` の3クラス18テスト
- `tests/test_pdf_ops.py` - `test_insert_blank_roundtrip`/`test_watermark_roundtrip`/`test_page_numbers_roundtrip` へ内容検証assert追記

## Decisions Made
- `_dnd_dest_index`/ショートカットループの委譲は完全に挙動保存（既存 `root.bind`・`event`/`winfo_*` 呼び出し順序は不変）。抽出はロジックのみで実挙動は変えない（RESEARCH.md A4・脅威登録T-3-02の要求通り）
- TOC回帰テストは must_haves で言及された「削除/結合/分割」の3機能を、分割については範囲指定と全ページ分割の2パターンに分けて検証し網羅性を高めた（`_split_by_range`/`_split_each_page` 両方のTOC再採番コードパスを exercise）
- 内容検証の追加は既存テスト構造（メソッド数・assert前後関係）を一切変更せず、正常系assertの追記のみに留めた（D-14の「テスト構造は変えず」制約を厳守）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 5/6のコード例をそのまま採用、FakeApp mixinはtest_pdf_ops.pyの既存実装を再利用）。

唯一の追加作業は `ruff format` によるコードスタイル自動整形（`shift_variant_keysym` の複数行if文を1行へ短縮）で、これは Rule 3（ブロッキング解消・リント整合）に該当する軽微な自動修正。

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-TEST-01 完了。D&D・ショートカット・TOC保持の回帰網が張られ、以降のページ操作磨き込み（03-03/03-04）が既存挙動を壊していないか継続的に検証可能
- Wave 1（03-01・03-02）完了。Wave 2（03-03: 黒塗り/モザイク・回転座標対応）へ進行可能
- `pytest` フルスイート805件グリーン・`ruff check`/`ruff format --check`クリーン

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/dnd.py
- FOUND: pagefolio/app.py
- FOUND: tests/test_v150_regression.py
- FOUND: tests/test_pdf_ops.py
- FOUND: 8ed8217 (Task 1 commit)
- FOUND: 37cb618 (Task 2 commit)
- FOUND: f879091 (Task 3 commit)
- FOUND: d215972 (follow-up style commit)
