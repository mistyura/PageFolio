---
phase: 04-ocr
plan: 02
subsystem: ocr
tags: [batch-ocr, tkinter-dialog, threading, ocr-engine-reuse, tdd]

# Dependency graph
requires:
  - phase: 04-ocr (04-01)
    provides: "BatchFileEntry/BatchState/enqueue_files/count_pending/STATUS_* 定数（Tk/fitz非依存の純ロジック層）"
  - phase: 03-ocr-e2e
    provides: "OCRRunEngine（ファイルごとに新規生成して再利用する per-run 独立原則の設計根拠）"
provides:
  - "pagefolio/dialogs/batch_ocr.py（BatchOCRDialog・独立設計 D-04 の Toplevel ダイアログ）"
  - "D&D+ファイル選択によるキュー投入・3列Treeview・二段進捗・集約コスト確認（OCRDialogからのコピペ移植）"
  - "ファイル間逐次のファイルループコントローラ（per-fileOCRRunEngine新規生成・2階層キャンセル・失敗自動スキップ・再実行制御）"
affects: [04-03-batch-summary-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tk 3.14 環境でのワーカースレッド駆動テスト: mainloop()/quit() ポンピング方式（update() 単純ポンピングは main thread is not in main loop で失敗する）"
    - "OCRDialog のインスタンスメソッド（コスト確認系）を継承せずコピペ移植する独立ダイアログパターン"

key-files:
  created:
    - pagefolio/dialogs/batch_ocr.py
    - tests/test_batch_ocr_dialog.py
  modified:
    - pagefolio/lang.py

key-decisions:
  - "OCRDialog の _confirm_cost/_estimate_cost/_is_cloud_provider/_check_cloud_api_key は継承せず同一シグネチャ・同一挙動の独立実装としてコピペ移植した（ocr_dialog.py は本フェーズで無変更）"
  - "バッチ中止によりキャンセルされたファイルの status は STATUS_DONE/STATUS_FAILED ではなく STATUS_PENDING へ戻す設計とし、次回の _on_start_batch（count_pending 経由）で再度処理対象になるようにした（完了済み・失敗確定ファイルとは区別）"
  - "provider/concurrency/prompt はバッチ開始時に _build_provider_once で1回だけ構築しファイル間で使い回す（Assumption A2・ファイルごとの再構築はしない）"
  - "テストの Tk 駆動は Python 3.14 の tkinter 制約（ワーカースレッドからの after() はメインスレッドが mainloop 内にいることを要求）に対応するため、update() 単純ポンピングではなく mainloop()/quit() 方式へ設計した"

patterns-established:
  - "_advance_to_next_file が毎回 self._batch_cancel_flag.is_set() を確認してから次ファイルの Engine を起動する（Pitfall 2 の一手を単一メソッドに集約）"
  - "_on_close は世代無効化（_run_gen += 1）を先に行い、後続の after コールバックが gen ガードで即 return するため destroy 後のウィジェットアクセスが構造的に発生しない"

requirements-completed: [V180-BATCH-01, V180-BATCH-02, V180-BATCH-03, V180-BATCH-04]

coverage:
  - id: D1
    description: "D&D + 「+ ファイル追加」の両方で複数PDF/画像をキューへ投入でき、SUPPORTED_EXTENSIONS外は除外・重複は enqueue_files で1件に集約される"
    requirement: V180-BATCH-01
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_rerun_skips_completed"
        status: pass
    human_judgment: true
    rationale: "実 tkinterdnd2 のネイティブ D&D イベントはヘッドレステスト不可（04-VALIDATION.md Manual-Only Verifications）。自動テストは _enqueue_files 経由のキュー投入ロジックのみ検証し、実ウィンドウでのドロップ操作は人手確認が必要"
  - id: D2
    description: "3列 Treeview キュー一覧（ファイル名/状態/ページ内進捗）+ ファイル軸/ページ軸の二段進捗表示が独立カウンタで動作する"
    requirement: V180-BATCH-02
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_progress_never_exceeds_total"
        status: pass
    human_judgment: true
    rationale: "Treeview 行の警告色表示（C[WARNING]）はテーマ色の視覚確認が必要（04-VALIDATION.md Manual-Only Verifications）。進捗集計ロジック自体は自動テストで検証済み"
  - id: D3
    description: "ファイル単位の fatal（サーキットブレーカー）発生時は自動スキップし、次ファイルの OCRRunEngine が新規生成されて処理が継続する"
    requirement: V180-BATCH-03
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_file_failure_continues"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_all_files_fail"
        status: pass
    human_judgment: false
  - id: D4
    description: "「バッチ中止」1ボタンで batch+file の2階層フラグが同時 set され、実行中ファイルが停止し次ファイルの Engine が新規生成されない"
    requirement: V180-BATCH-04
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_batch_cancel_stops_all"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_cancel_before_start_noop"
        status: pass
    human_judgment: false
  - id: D5
    description: "バッチ実行中のダイアログクローズ（WM_DELETE_WINDOW相当）で2階層フラグ set + 世代無効化 + destroy によりワーカーが安全停止し、遅延コールバックが世代ガードで無害化される"
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_close_during_run_stops_threads"
        status: pass
    human_judgment: false
  - id: D6
    description: "中止/完了後の再実行では STATUS_PENDING のみが処理対象となり、STATUS_DONE の完了済みファイルは再送信されない（count_pending 連携）"
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchOCRDialogE2E::test_rerun_skips_completed"
        status: pass
    human_judgment: false

duration: 27min
completed: 2026-07-15
status: complete
---

# Phase 4 Plan 2: バッチOCRダイアログ コア実装 Summary

**独立設計の `BatchOCRDialog`（D-04）に D&D+ファイル選択キュー投入・3列Treeview二段進捗・OCRDialogコピペ移植コスト確認・ファイル間逐次の per-file `OCRRunEngine` 新規生成ループ・2階層キャンセル・WM_DELETE_WINDOWクローズ安全化・再実行制御を実装し、E2Eモックテスト7件で固めた**

## Performance

- **Duration:** 27分
- **Started:** 2026-07-15T21:18:24+09:00
- **Completed:** 2026-07-15T21:45:16+09:00
- **Tasks:** 3
- **Files modified:** 3（新規2・変更1）

## Accomplishments
- `pagefolio/dialogs/batch_ocr.py` を新規作成し、`BatchOCRDialog(tk.Toplevel)` を `self.app.doc`/`self.app.filepath` を一切参照しない独立設計（D-04）で構築
- D&D（`tk.splitlist`+`SUPPORTED_EXTENSIONS`フィルタ）+「+ ファイル追加」（`askopenfilenames`）の両方でキュー投入でき、`enqueue_files`（04-01）による重複除外・事前ページ数スキャン（応答性確保のため `update_idletasks` 併用）を実装
- 3列 `ttk.Treeview`（ファイル名/状態/ページ内進捗）+ ファイル軸（`BatchState.files_done()`）とページ軸（`OCRRunEngine.progress_count()`）を独立させた二段進捗表示（D-08）を実装
- `OCRDialog`（`ocr_dialog.py`）の `_confirm_cost`/`_estimate_cost`/`_is_cloud_provider`/`_check_cloud_api_key` を継承せず同一シグネチャ・同一挙動でコピペ移植し（レビュー懸念5）、`_confirm_batch_cost` で STATUS_ERROR を除外した合計ページ数の集約コスト確認（D-03）を実装
- ファイル間逐次のファイルループコントローラ（`_start_file_engine`/`_render_next_page_for`/`_advance_to_next_file`）を実装。`OCRRunEngine` はファイルごとに新規生成され（D-11外挿）、fitz はファイル間もメインスレッド逐次（Pitfall 1・落とし穴3）
- 「バッチ中止」1ボタンで `_batch_cancel_flag`/`_file_cancel_flag` の2階層フラグを同時 set する D-10 と、`_on_close`（WM_DELETE_WINDOW）で実行中クローズ時に同フラグ set + `_run_gen += 1` 世代無効化 + `destroy()` する安全化（レビュー懸念1・HIGH）を実装
- `_set_running_ui` による実行中/停止のボタン活性切替（レビュー懸念3）と、`count_pending` 連携による `BatchState(total_files=count_pending(entries))` 構築（STATUS_ERROR除外・レビュー懸念6）を実装
- `tests/test_batch_ocr_dialog.py` に E2Eモックテスト7件（`test_file_failure_continues`/`test_batch_cancel_stops_all`/`test_cancel_before_start_noop`/`test_all_files_fail`/`test_progress_never_exceeds_total`/`test_close_during_run_stops_threads`/`test_rerun_skips_completed`）を新設し、実 fitz/実ネットワーク非依存で全件 green を確認

## Task Commits

Each task was committed atomically:

1. **Task 1: BatchOCRDialog 骨格・キュー投入・Treeview・二段進捗・集約コスト確認** - `668a9ca` (feat)
2. **Task 2: ファイルループコントローラ・per-file Engine 生成・2階層キャンセル・失敗自動スキップ・クローズ処理・再実行制御** - `885ba3b` (feat)
3. **Task 3: test_batch_ocr_dialog.py — E2E モックテスト（失敗分離・キャンセル・エッジ）** - `7b666d8` (test)

_Note: プラン frontmatter は tdd="true" だが、Task 1/2 は本プラン独自の実装先行構造（テストファイル自体は Task 3 が新規作成）のため plan の action/verify 記載どおり feat コミットとした。Task 3 で E2E テストを新設し全件 green を確認している。_

## Files Created/Modified
- `pagefolio/dialogs/batch_ocr.py` - BatchOCRDialog（独立設計・D&D+ファイル選択投入・3列Treeview二段進捗・コスト確認コピペ移植・ファイルループコントローラ・2階層キャンセル・WM_DELETE_WINDOWクローズ安全化）
- `pagefolio/lang.py` - `batch_*` 系キー17件（`batch_dialog_title`〜`batch_empty_queue_msg`）をja/en同時追加
- `tests/test_batch_ocr_dialog.py` - E2Eモックテスト7件（FakeProvider+fitzモックで実API/実PDF非依存）

## Decisions Made
- `OCRDialog` のコスト確認系メソッドは継承・cross-import せず同一シグネチャ・同一挙動のコピペ移植とした（`ocr_dialog.py` は本フェーズで無変更、レビュー懸念5どおり）
- バッチ中止でキャンセルされたファイルの status は `STATUS_PENDING` へ戻す設計とした（完了済み `STATUS_DONE`・確定失敗 `STATUS_FAILED` とは区別し、次回実行の `count_pending` で再度処理対象になる）。プラン本文に明記のない実装判断だが、D-11（中止後も完了済み結果は保持）・レビュー懸念3（再実行は STATUS_PENDING のみ処理）の両方と整合するため採用した
- provider/concurrency/prompt はバッチ開始時に `_build_provider_once` で1回だけ構築しファイル間で使い回す（Assumption A2 のとおり、ファイルごとの再構築はしない）
- E2Eテストの Tk 駆動方式は当初 `update()` による単純ポンピングを設計したが、Python 3.14 の tkinter が「ワーカースレッドからの `after()` 呼び出しにはメインスレッドが `mainloop()` 内にいること」を要求するため（`RuntimeError: main thread is not in main loop`）、`mainloop()`/`quit()` による自己再帰ポーリング方式へ設計変更した（詳細は Deviations 参照）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E2Eテストの Tk イベントループ駆動方式を update() ポンピングから mainloop()/quit() 方式へ変更**
- **Found during:** Task 3（test_batch_ocr_dialog.py 実行時）
- **Issue:** 当初 `widget.update()` を繰り返し呼ぶポンピング方式でワーカースレッドからのコールバック処理を試みたが、実行環境の Python 3.14 の tkinter は `RuntimeError: main thread is not in main loop` を送出しワーカースレッドからの `self.after(...)` 呼び出しが失敗した（本番コードは `root.mainloop()` で起動するため無影響。テストハーネスのみの問題）
- **Fix:** `_pump_until`/`_pump_for` ヘルパーを `widget.after(poll_ms, _poll)` で自己再帰的にポーリングしつつ実際に `widget.mainloop()` を実行し、条件成立/タイムアウトで `quit()` する方式へ変更
- **Files modified:** tests/test_batch_ocr_dialog.py
- **Verification:** `pytest tests/test_batch_ocr_dialog.py -q` を3回連続実行し毎回7件green（フレーキーでないことを確認）
- **Committed in:** 7b666d8（Task 3 commit）

**2. [Rule 3 - Blocking] テスト用 tk.Tk() の生成をモジュールスコープの単一インスタンスへ変更**
- **Found during:** Task 3（test_batch_ocr_dialog.py 実行時）
- **Issue:** 当初テストごとに `tk.Tk()` を生成・破棄する function スコープの fixture を設計したが、1つ目のテスト完了後の2つ目の `tk.Tk()` 生成で `TclError: Can't find a usable tk.tcl`（ttk テーマファイル読込失敗）が発生した。同一プロセス内で複数の `tk.Tk()` を逐次生成・破棄すると Tcl のグローバル状態（ttk テーマキャッシュ）が壊れる既知の環境依存制約
- **Fix:** `tk_root` fixture を `scope="module"` に変更し、テストモジュール全体で1つの `tk.Tk()` を共有する構成へ変更（個々の `BatchOCRDialog`（Toplevel）は各テストが生成・破棄する既存設計は維持）
- **Files modified:** tests/test_batch_ocr_dialog.py
- **Verification:** 全7テストが同一プロセス内で連続green
- **Committed in:** 7b666d8（Task 3 commit）

---

**Total deviations:** 2 auto-fixed（いずれも Rule 3・テストハーネスの環境依存問題。本番コード（`pagefolio/dialogs/batch_ocr.py`）への影響なし）
**Impact on plan:** テストの実行基盤に関する修正のみで、プランが要求する検証項目（7テスト関数・失敗分離・2階層キャンセル・再実行スキップ）はすべて計画どおり満たしている。No scope creep。

## Issues Encountered
None（Deviations 参照の2件はテストハーネスの環境対応であり、機能実装自体への影響はなし）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `BatchOCRDialog` のコア機能（キュー投入・二段進捗・集約コスト確認・ファイルループ・2階層キャンセル・再実行制御）が確立され、04-03（ファイル横断統合サマリ・ファイル別結果閲覧・メニュー起動導線・`pagefolio/dialogs/__init__.py` re-export）から直接利用できる状態
- `BatchFileEntry.results`/`errors`（04-01 由来）は本プランのファイルループで per-file に蓄積されており、04-03 の統合サマリ連結（D-15: `=== ファイル名.pdf ===` 見出し挿入）がそのまま利用できる
- 04-VALIDATION.md の Manual-Only Verifications（実ウィンドウでのD&D投入・Treeview警告色の両テーマ確認）は `/gsd-verify-work` 実行時の人手確認事項として残存（コード上のブロッカーではない）
- ブロッカーなし。フルスイート1010件green・ruffクリーンで次プラン（04-03）へ進行可能

---
*Phase: 04-ocr*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/batch_ocr.py
- FOUND: tests/test_batch_ocr_dialog.py
- FOUND: .planning/phases/04-ocr/04-02-SUMMARY.md
- FOUND commit: 668a9ca
- FOUND commit: 885ba3b
- FOUND commit: 7b666d8
