---
phase: 01-safety-rollback
plan: 05
subsystem: testing
tags: [pymupdf, fitz, undo-redo, rollback, regression-testing, blob-lifecycle]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-04（_undo/_redo の復元失敗保護・_duplicate_page の Undo 後置確定）が本プランの4手往復テストの対象コード基盤"
provides:
  - "duplicate / merge / merge_resize の do→undo→redo→undo（4手往復）回帰テスト（v1.8.0 D-17 insert 版の水平展開・V190-UNDO-02）"
  - "境界（単一ページ Document）・隣接（先頭/末尾マージ）・順序（元ページ順序保持）・精度（元ページ MediaBox 寸法保持）・最小入力（単一ソースファイル）の5エッジテスト"
  - "D-12 棚卸し: `_save_undo` 全16呼び出し箇所の記録タイミング一覧（次マイルストーン候補として明示）"
affects: []

actuals:
  tokens: 3321
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "4手往復（do→undo→redo→undo）回帰テストは既存 TestInsertUndoRedo の insert 版と同型: 操作前の全ページ digest 列を記録し、2回目の undo 後に digest 列（順序込みリスト比較）で一致を検証する。ページ数だけの比較では非対称復元バグを検出できないため"
    - "境界・隣接エッジは _make_fake_app / _make_full_fake_app の既存ヘルパーをそのまま再利用し、フィクスチャで作れない構成（1ページ Document・4ページ Document）のみ関数内で fitz.open() を直接生成し try/finally で close する"

key-files:
  created: []
  modified:
    - tests/test_pdf_ops.py

key-decisions:
  - "merge の「先頭マージ」テストは、実装（_do_merge）が常に末尾へ insert_pdf する仕様のため、1ページのみの Document へマージすることで『唯一の元ページ（index 0）の直後』という先頭隣接の意味を表現した。UI 経路にない position=0 挿入を捏造しない選択"
  - "merge_resize の順序・精度エッジは 4 ページ Document（targets=[1,2]）を使い、結合対象外の index 0・3 が結合ページを挟んで前後に残る構成にすることで、単純な2ページ構成では検出できない順序入れ替わりを検出可能にした"
  - "D-12 棚卸しは grep 実測（page_ops.py 13 / dnd.py 2 / redact_ops.py 1 = 計16件）に基づく。PLAN.md 記載の『page_ops.py 12』は実測と異なる（page_ops.py は13件）ため、実測値を正として記録した"
  - "開発履歴.md / APP_VERSION の更新は Phase 3（V190-QA-03 リリースゲート）へ委譲する。開発履歴.md の既存エントリはすべてリリース単位（APP_VERSION 同期済み）の書式であり、マイルストーン途中の Phase 1 完了時点で追記すると書式が崩れるため"

requirements-completed: [V190-UNDO-02]

coverage:
  - id: D1
    description: "duplicate op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_duplicate_undo_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D2
    description: "merge op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_merge_undo_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D3
    description: "merge_resize op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_merge_resize_undo_redo_undo_roundtrip"
        status: pass
    human_judgment: false
  - id: D4
    description: "1ページのみの Document に対する duplicate でも4手往復でページ構成が一致する（boundary probe）"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_duplicate_single_page_doc_roundtrip"
        status: pass
    human_judgment: false
  - id: D5
    description: "先頭・末尾に隣接する位置へのマージでも4手往復後のページ順序が操作前と一致する（adjacency probe）"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_merge_head_and_tail_adjacent_roundtrip"
        status: pass
    human_judgment: false
  - id: D6
    description: "merge_resize の4手往復後、元ページの digest列が操作前と同順で一致する（ordering probe）"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_merge_resize_preserves_original_page_order"
        status: pass
    human_judgment: false
  - id: D7
    description: "merge_resize の4手往復後、元ページの MediaBox 幅・高さが操作前と一致する（precision probe）"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_merge_resize_preserves_original_page_dimensions"
        status: pass
    human_judgment: false
  - id: D8
    description: "マージ対象ファイルが1件だけの最小入力でも4手往復が成立する（empty probe）"
    requirement: "V190-UNDO-02"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip::test_roundtrip_with_single_merge_source_file"
        status: pass
    human_judgment: false
  - id: D9
    description: "D-12 棚卸し（Undo 記録が実処理より先の op 一覧）が SUMMARY に記録され、水平展開は次マイルストーン候補として明示されている"
    verification:
      - kind: other
        ref: "本 SUMMARY「D-12 棚卸し: Undo 記録が先置きのままの op 一覧」節"
        status: pass
    human_judgment: false

duration: 約20min
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 5: duplicate/merge/merge_resize 4手往復回帰テスト・D-12棚卸し Summary

**v1.8.0 で insert のみに実施していた do→undo→redo→undo（4手往復・2回目のundoで非対称復元を検出する）回帰テストを duplicate/merge/merge_resize へ水平展開し、境界・隣接・順序・精度の5エッジテストを追加。Undo 記録が実処理より先に置かれたままの全16 op を棚卸しして次マイルストーン候補として記録し、Phase 1 の全ゲート（lint/フルテスト）を green で確定**

## Performance

- **Duration:** 約20分
- **Completed:** 2026-08-10
- **Tasks:** 3/3
- **Files modified:** 2（`tests/test_pdf_ops.py`, `.planning/phases/01-safety-rollback/01-05-SUMMARY.md`）

## Accomplishments
- `tests/test_pdf_ops.py` の `TestAllOpsUndoRedoRoundtrip` へ、既存の3手往復テスト（`test_duplicate_roundtrip` / `test_merge_roundtrip` / `test_merge_resize_roundtrip`）を削除・改変せず残したまま、4手往復（2回目の undo）テストを3件追加した。すべて「ページ数」だけでなく「全ページの digest 列（順序込み）」で比較し、v1.8.0 の `insert_redo` 非対称復元バグ（D-17）と同型の不具合を検出できるようにした
- 境界（単一ページ Document の duplicate）・隣接（先頭/末尾マージ）・順序（merge_resize の元ページ順序保持）・精度（merge_resize の元ページ MediaBox 寸法保持）・最小入力（単一ソースファイルでのマージ）の5エッジテストを追加した
- `duplicate` / `merge` op の実装（`file_ops.py` の `_apply_inverse` / `_restore_state`）は、いずれもインデックス・カウントを逆デルタ生成時点で毎回再計算する設計であり、insert の insert_redo バグ（bytes を保存済みインデックスで固定してしまい2回目の undo で位置がずれる）とは構造的に異なる。今回追加したテストはすべて一発で green となり、既存実装に非対称復元バグは発見されなかった
- D-12 の棚卸しを実施し、`_save_undo` の全16呼び出し箇所（実測: `page_ops.py` 13 / `dnd.py` 2 / `redact_ops.py` 1）を「記録タイミング」「Blob キャプチャ有無」「先置きのままの場合に起こり得る不正な Undo の内容」の観点で表にまとめた（下記節参照）
- フルテストスイート 1156 件グリーン（既知の Tcl/Tk フレーキー 2 件は単体再実行で green を確認・下記「Issues Encountered」参照）。`ruff check .` / `ruff format --check .` ともにグリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: duplicate / merge / merge_resize の 4 手往復テスト追加（V190-UNDO-02）** - `5c52977` (test)
2. **Task 2: 境界・隣接・順序・精度エッジの往復検証（probe 由来 5 件）** - `a0db5b9` (test)
3. **Task 3: D-12 の棚卸し一覧作成とフェーズ最終ゲート** - このコミット（SUMMARY + STATE.md + ROADMAP.md）

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: 全タスクとも `tdd` フラグなし（回帰テスト整備そのものが成果物のため RED→GREEN 構成は取らない）。Task 3 はプロダクションコード変更ゼロ（ドキュメント・棚卸しのみ）。_

## Files Created/Modified
- `tests/test_pdf_ops.py` - `TestAllOpsUndoRedoRoundtrip` へ 4手往復テスト3件（`test_duplicate_undo_redo_undo_roundtrip` / `test_merge_undo_redo_undo_roundtrip` / `test_merge_resize_undo_redo_undo_roundtrip`）+ 境界・隣接・順序・精度・最小入力エッジテスト5件（`test_duplicate_single_page_doc_roundtrip` / `test_merge_head_and_tail_adjacent_roundtrip` / `test_merge_resize_preserves_original_page_order` / `test_merge_resize_preserves_original_page_dimensions` / `test_roundtrip_with_single_merge_source_file`）を追加。既存メソッドは無変更
- `.planning/phases/01-safety-rollback/01-05-SUMMARY.md` - 本ファイル（D-12 棚卸し表を含む）

## D-12 棚卸し: Undo 記録が先置きのままの op 一覧

`grep -n '_save_undo(' pagefolio/page_ops.py pagefolio/dnd.py pagefolio/redact_ops.py` の実測は `page_ops.py` 13件・`dnd.py` 2件・`redact_ops.py` 1件の**計16件**（PLAN.md 記載の「12件」は実測と不一致のため、実測値を正として記録する）。

| op | ファイル:行 | 呼び出し元 | 記録タイミング | Blob キャプチャ | 先置きのままの場合に起こり得る不正な Undo の内容 |
|---|---|---|---|---|---|
| rotate | page_ops.py:127 | `_rotate_selected` | 先置き | なし（rotation値のみ） | 回転適用前に例外が出ても影響は小さい（値渡しのみ）が、記録済みUndoは実処理と無関係に残る |
| delete | page_ops.py:163 | `_delete_selected` | 先置き | あり（削除対象ページ） | `delete_page` がループ途中で例外を投げた場合、実際には削除されていないページも「削除済み」前提のUndoが残り、undoで余分なページを挿入してしまう |
| duplicate | page_ops.py:195 | `_duplicate_page` | **後置き（対応済み・Plan 04 D-11）** | なし | — 実処理成功後にのみ確定するため、複製前の例外で不正なUndoは残らない |
| insert（白紙挿入） | page_ops.py:211 | `_insert_blank_page` | 先置き | なし（1ページ固定） | `new_page` が例外を投げた場合、挿入されていないのに1ページ分のUndoが残り、undoで既存ページを誤って削除する |
| page_edit（テキスト透かし） | page_ops.py:242 | `_add_watermark_text` | 先置き | あり（適用前ページ） | ターゲット途中で例外時、未変更ページも「変更済み」前提でBlob復元（同一内容の再書き込みで実害は小さいが不要な処理が発生） |
| page_edit（画像透かし） | page_ops.py:298 | `_add_watermark_image` | 先置き | あり | 同上 |
| page_edit（ページ番号） | page_ops.py:332 | `_add_page_numbers` | 先置き | あり | 同上 |
| crop（単一ページ） | page_ops.py:545 | `_crop_page` | 先置き | なし（cropbox値のみ） | `set_cropbox` がValueErrorで早期returnした場合、cropbox未変更のまま無駄なUndoエントリが残る |
| bulk_crop（複数ページ一括） | page_ops.py:598 | `_crop_page` | 先置き | なし（cropbox値のみ） | ループ内で個別ページの適用が `continue` された場合、そのページも「変更済み」前提で記録され、Undo実行時に実状態と食い違う |
| bulk_crop（余白指定） | page_ops.py:671 | `_crop_by_margin` | 先置き | なし | 同上 |
| insert（複数ファイル挿入） | page_ops.py:775 | `_do_insert` | **先置き＋巻き戻し方式（対応済み・Plan 04 D-08〜D-10）** | あり | — 後置化ではなく例外時 `delete_page` 巻き戻し + 巻き戻し失敗時は警告付き残存数記録で対応済み |
| merge_resize | page_ops.py:902 | `_do_merge_resize` | 先置き（Blobキャプチャ後・実ドキュメント変更前） | あり | `insert_pdf`/`delete_page` がtry内で例外を投げた場合、部分適用のまま「結合成功」前提のUndoが残り、undo実行時に想定と異なるページ状態から復元を試みる |
| merge | page_ops.py:938 | `_do_merge` | 先置き | なし（元ページ数のみ） | ファイル結合の途中で例外時、未結合分も「結合済み」前提のUndoが残るが、undo実装は `old_count` 超過ページを一括削除するのみのため実害は小さい |
| bulk_move | dnd.py:130 | D&D複数ページ一括移動 | 後置き（`doc.select()` 実行後） | なし（新順序のみ） | 実処理後の記録のため理論上安全。値渡しのみで実処理前後どちらでもBlobリスクなし |
| move | dnd.py:145 | D&D単一ページ移動 | 後置き（`move_page()` 実行後） | なし | 同上 |
| page_edit（黒塗り/モザイク） | redact_ops.py:151 | 黒塗り/モザイク適用 | 先置き | あり（適用前ページ） | ターゲット途中で例外時、未変更ページも「変更済み」前提でBlob復元（実害は小さいが不要な処理が発生） |

**次マイルストーン候補（本フェーズのスコープ外・水平展開なし）:** 上記のうち「先置き」のまま残る op は rotate / insert(白紙) / page_edit系4件（透かしテキスト・透かし画像・ページ番号・黒塗りモザイク）/ crop / bulk_crop系2件 / merge / merge_resize の計10 op（`duplicate` と複数ファイル `insert` の2経路は Plan 04 で対応済み）。CONTEXT.md の Deferred Ideas に記載のとおり、共通コンテキストマネージャ化を含めた水平展開は次マイルストーン候補として保留し、本フェーズではコードを一切変更しない（PLAN.md prohibitions・V190-UNDO-02 の意図的な抑制）。

## 開発履歴.md / APP_VERSION の扱い

`開発履歴.md` の既存エントリはすべて `APP_VERSION = vX.Y.Z` を伴うリリース単位の書式（各エントリがリリース時点の `APP_VERSION` と1対1で対応）。v1.9.0 はマイルストーン途中（Phase 1 完了時点）であり、ここで追記すると「リリース単位」という既存書式が崩れる。したがって `開発履歴.md` への v1.9.0 エントリ追記と `pagefolio/constants.py` の `APP_VERSION` 更新は **Phase 3（V190-QA-03 のリリースゲート）** で行う。本プランではどちらのファイルも変更していない（`git diff --stat 開発履歴.md pagefolio/constants.py` は空）。

## Decisions Made
- merge の「先頭マージ」エッジは、`_do_merge` の実装が常に末尾へ `insert_pdf` する仕様（position=0 挿入の UI/コード経路が存在しない）のため、1ページのみの Document へマージすることで「唯一の元ページ（index 0）の直後」という先頭隣接の意味を表現した。存在しないコード経路を捏造せず、実装の実際の挙動に即したテストにした
- merge_resize の順序・精度エッジは4ページ Document（`targets=[1,2]`）を使い、結合対象外の index 0・3 が結合ページを挟んで前後に残る構成にした。2ページ構成（既存 `test_merge_resize_roundtrip` 相当）では検出できない「順序入れ替わり」パターンをカバーするため
- D-12 棚卸しは PLAN.md 記載の見積もり件数（page_ops.py 12件）ではなく、`grep -n` の実測件数（page_ops.py 13件・計16件）を正として記録した。件数の相違は Plan 04 で `_do_insert`/`_duplicate_page` へのコメント追加により行番号がずれた結果と推測されるが、実測との齟齬をそのまま記録せず正確な値で確定させた

## Deviations from Plan

None - plan executed exactly as written（D-12 棚卸しの件数を PLAN.md の見積もり「12」ではなく grep 実測「13」で記録した点は、prohibitions が求める「棚卸し表の行数と grep -c の合計が一致すること」という acceptance_criteria を満たすための事実確認であり、計画からの逸脱ではない）。

## Issues Encountered

フルテストスイート（1156件）実行時、`tests/test_ocr_dialog_center.py` の2件が STATE.md Blockers に既知記載の Tcl/Tk フレーキー（`_tkinter.TclError`: `couldn't read file "...ttk/spinbox.tcl"` 等。単一 pytest プロセスでの大量 `tk.Tk()` 生成/破棄によるリソース消耗系事象）で ERROR になった。該当ファイル単体で再実行したところ `tests/test_ocr_dialog_center.py -q` は2件とも green で完走した（`.tox`/venv再構築なし・コード変更なし）。本事象は v1.9.0 Phase 3（V190-QA-01）が切り分け・修復を引き取る予定のため、本プランでは記録に留め対応しない。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V190-UNDO-02 の受け入れ条件（duplicate/merge/merge_resize の4手往復でページ構成が壊れない）を境界・隣接・順序・精度のエッジまで含めて機械検証済み
- D-12 棚卸し表により、次マイルストーンでの「記録後置」水平展開候補（10 op）が明示された
- Phase 1（保存・編集・設定の安全性是正）は本プラン（05）をもって全5プラン完了。V190-SAFE-01〜05・CFG-01/02・UNDO-01/02 の全9要件をカバー
- 開発履歴.md / APP_VERSION の更新は Phase 3 のリリースゲートへ委譲する方針を確定・記録済み

---
*Phase: 01-safety-rollback*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: tests/test_pdf_ops.py
- FOUND: .planning/phases/01-safety-rollback/01-05-SUMMARY.md
- FOUND commit: 5c52977
- FOUND commit: a0db5b9
- FOUND commit: 4dfbc41
