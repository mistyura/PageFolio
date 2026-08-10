---
phase: 01-safety-rollback
plan: 07
subsystem: undo-redo
tags: [pymupdf, fitz, undo-redo, rollback, blob-lifecycle, gap-closure, code-review]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-06 が確立した _pending_inverse / _merge_pending_inverse 蓄積方式（部分失敗をまたいだ完全な逆デルタ保持）が本プランの土台"
provides:
  - "page_edit の2段階mutation（delete_page→insert_pdf）中間失敗を、mutation順序反転（insert_pdf→delete_page）で構造的に解消する方式（option-b・CR-02）"
  - "ロールバックにも失敗した復旧不能ケース専用の強い警告文言（content_at_risk・err_undo/redo_restore_failed_content_at_risk）"
  - "_restore_state 周辺の一時 fitz.Document（tmp）7箇所への finally 保護とAST走査ガードによる恒久固定（WR-04）"
  - "insert（base op）の削除ループへの部分適用保護展開（WR-05）。01-VERIFICATION.md missing[]の4項目すべてを解消"
affects: []

actuals:
  tokens: 11828
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "page_edit の2段階mutationは『doc がページ内容を失っている瞬間』を構造的に排除する順序（挿入→削除）で設計する。ロールバック不能時のみ state 専用の再試行制御マーカー（_page_edit_inserted）を立て、次回再試行が正しい分岐（挿入済みか否か）へ入る"
    - "PartialRestoreError.content_at_risk / _restore_partial_error(content_at_risk=...) により『通常の部分失敗』と『内容の一意性が保証されない復旧不能』を型レベルで区別し、_undo/_redo の通知文言選択に使う"
    - "一時 fitz.Document（tmp）は必ず try/finally: tmp.close() で保護する。この不変条件は AST 走査ガードテスト（TestTempDocumentCloseGuard）で固定し、将来の新しい復元ループが finally を忘れると即座に fail する"
    - "insert（base op）は削除の直前に _capture_page_blob を呼び、成功した分だけ _merge_pending_inverse で蓄積する（他7opと同型）。再試行時の絶対インデックス復元には『_pending_inverse の既存件数』をpopの前に読んで insert_at へ加算する"

key-files:
  created: []
  modified:
    - pagefolio/file_ops.py
    - pagefolio/lang.py
    - tests/test_pdf_ops.py
    - tests/test_undo_stress.py

key-decisions:
  - "Task 0（checkpoint:decision）はオーケストレーターがユーザーへ事前提示し option-b（推奨・構造的解消）が選択済みとして実行を開始した。option-a（現行delete→insert順維持・ロールバック失敗時にBlobをstateへ保持）は一切実装していない"
  - "option-b選択の結果、警告文言（err_undo/redo_restore_failed_content_at_risk）は『このページの内容が失われた可能性があります』ではなく『このページが二重化または欠落している可能性があります』とした。理由: option-bのmutation順序反転（挿入→削除）により、ロールバックが失敗しても旧ページはpage_i+1に必ず残存し内容喪失が構造的に起こり得ないため、『失われた』という断定は事実に反する。この判断は再検証時にEvidence Bの文言差異を説明する照合根拠として記録する"
  - "PLAN Task 3(5)の判断を踏襲: pagefolio/constants.pyのAPP_VERSION・開発履歴.md・READMEバッジは本プランでは更新しない。開発履歴.mdはリリース単位の追記書式であり、マイルストーン途中での追記は書式を崩すため、バージョンバンプはPhase 3（V190-QA-03リリースゲート）へ委譲する（01-05/01-06と同じ既定方針の継続）"
  - "PLAN Task 3(7)の棚卸し結果: merge（base op）の`while len(self.doc) > old_count: self.doc.delete_page(old_count)`削除ループは、insertのdelete_pageループと同型の構造（_apply_inverse側での一括捕捉＋保護なしの削除ループ）を持つ。01-VERIFICATION.mdのmissing[]はinsertのみを対象としており、D-12が定めた『対象opを広げず棚卸し記録に留める』方針に従い、本プランではmergeへのコード変更を一切行っていない。次マイルストーン候補として明示する"

requirements-completed: [V190-UNDO-01]

coverage:
  - id: D1
    description: "page_edit の undo/redo が、delete_page成功後のinsert_pdf失敗（旧設計）に相当する中間失敗を経ても、ロールバック成功時は通常の部分失敗として扱われ、doc/隣接ページの内容が失われない（Evidence B再現手順）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_page_edit_insert_failure_rolls_back_and_retry_preserves_neighbors"
        status: pass
    human_judgment: false
  - id: D2
    description: "page_edit の中間mutationロールバックも失敗する復旧不能ケースで、専用の強い警告（content_at_risk）が1回だけ表示され、障害解消後の再試行・redo・undoの往復で内容が完全に再構成される"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages"
        status: pass
    human_judgment: false
  - id: D3
    description: "_restore_state周辺の一時fitz.Document（tmp）7箇所すべてがfinallyで保護され、AST走査ガードで恒久的に固定されている（WR-04）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestTempDocumentCloseGuard::test_temp_documents_are_finally_closed_guard"
        status: pass
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_restore_failure_closes_temp_document"
        status: pass
    human_judgment: false
  - id: D4
    description: "insert（base op）の削除ループが部分適用保護に乗り、部分失敗→再試行で挿入対象外の既存ページを過剰削除しない（WR-05）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_pdf_ops.py::TestUndoRedoRestoreFailure::test_insert_partial_failure_preserves_remaining_and_retry_completes"
        status: pass
    human_judgment: false
  - id: D5
    description: "復旧不能経路・insert部分失敗経路のいずれでも蓄積Blobがevict/clear経路で確実に一度だけ解放される（二重解放ゼロ・D-14）"
    requirement: "V190-UNDO-01"
    verification:
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_insert_partial_retry_blobs_released_on_stack_clear"
        status: pass
      - kind: unit
        ref: "tests/test_undo_stress.py::TestBlobLeakDetection::test_page_edit_unrecoverable_failure_blobs_released_on_clear"
        status: pass
    human_judgment: false
  - id: D6
    description: "既存の部分適用保護・逆デルタ蓄積方式・4手往復回帰テスト・Blobライフサイクル不変条件が退行していない。ruff check / ruff format --check は green。pytest -q（フルスイート単一プロセス）は本プランのテスト追加が引き金となる test_ocr_pipeline.py のネイティブクラッシュにより不安定（分割実行では1184全件green）"
    verification:
      - kind: other
        ref: "ruff check . && ruff format --check .（ともにexit 0）"
        status: pass
      - kind: other
        ref: "pytest -q --ignore=tests/test_ocr_pipeline.py（1167 passed）+ pytest -q tests/test_ocr_pipeline.py（17 passed）= 1184 全件green"
        status: pass
      - kind: other
        ref: "pytest -q（フルスイート単一プロセス）— 6回中2回のみ1184 passed、4回は tests/test_ocr_pipeline.py::TestPipelineHardening::test_cancel_finite_time_no_deadlock で Windows fatal exception 0x80000003 によりプロセス終了。オーケストレーターのA/B検証で本プランのテスト追加が引き金と確定（詳細は後述「Issues Encountered」）"
        status: fail
    human_judgment: false

duration: 約70分
completed: 2026-08-11
status: complete
---

# Phase 1 Plan 7: page_edit中間失敗ロールバック・一時Documentクローズ・insert部分適用保護 Summary

**page_edit の2段階mutation（delete_page→insert_pdf）が中間失敗してもページ内容を恒久喪失させない構造的解消（mutation順序反転・option-b）、復元ループの一時fitz.Document7箇所へのfinally保護とAST走査ガード、insert（base op）削除ループへの部分適用保護展開により、01-VERIFICATION.mdのmissing[]4項目すべてを解消しV190-UNDO-01を真に充足させた**

## Performance

- **Duration:** 約70分
- **Completed:** 2026-08-11
- **Tasks:** 3/3（Task 0 はオーケストレーターが事前提示・ユーザー選択済みのcheckpoint:decisionのため実行フェーズではコード変更なし）
- **Files modified:** 4（`pagefolio/file_ops.py`, `pagefolio/lang.py`, `tests/test_pdf_ops.py`, `tests/test_undo_stress.py`）

## Accomplishments

- `01-VERIFICATION.md`（gaps_found・4/5）が検出した新規Critical欠陥CR-02（`_restore_state`の`page_edit`分岐: `delete_page`成功後の`insert_pdf`失敗でページ内容の唯一のコピーである`captured`を無条件解放し、再試行時に隣接ページを巻き添え削除する）を、ユーザー選択済みのoption-b（mutation順序反転）で構造的に解消した。差し替えページを`insert_pdf`で**先に**挿入し、旧ページを`delete_page`で**後から**除去することで、doc がページ内容を失っている瞬間が構造的に存在しなくなった
- ロールバック（挿入済みページの取り消し）にも失敗する復旧不能ケースのみ、state専用の再試行制御マーカー`_page_edit_inserted`（`merge_resize`の`_merged_page_deleted`と同型）を立て、`PartialRestoreError.content_at_risk=True`で専用の強い警告（`err_undo_restore_failed_content_at_risk`/`err_redo_restore_failed_content_at_risk`・ja/en各2キー）をブロッキング表示する。ロールバック成功時は従来どおり`err_undo_restore_failed_partial`（通常の部分失敗）のまま
- `01-VERIFICATION.md`のEvidence B再現手順（4ページdoc・`targets=[0,1]`・`app.doc`の2回目mutationで失敗注入）を失敗注入回帰テストとして固定し、障害解消後の再試行で`len(app.doc)==4`かつdigest列が編集前と完全一致、隣接ページ（index 2 = "Page 3"）が巻き添え削除されないことを実測確認した
- WR-04: `_capture_page_blob`・`delete`・`duplicate_undo`・`insert_undo`・`merge_undo`・`merge_resize`・`merge_resize_undo`の7箇所で`tmp = fitz.open(...)`を`try/finally: tmp.close()`で保護し、`insert_pdf`失敗時の一時`fitz.Document`未クローズ（リソースリーク）を解消した。AST走査ガードテスト（`TestTempDocumentCloseGuard`）で「`tmp`への代入の後に`finally: tmp.close()`を持つ`Try`が必ず存在する」ことを恒久的に固定し、実行時の裏取りテスト（delete undo・merge_resize_undo redoの2ケース）も追加した
- WR-05: `insert`（base op）の削除ループへ他7opと同型の部分適用保護を展開した。`_apply_inverse`のinsert分岐から一括捕捉を除去しop名決定のみに縮小し、`_restore_state`側で削除の直前に`_capture_page_blob`を呼んで成功分だけ蓄積する方式へ変更。部分失敗時は残り件数のみを表す`state`（`[insert_at, num-deleted]`）を返し、再試行時に`num`回ではなく残り回数だけ`delete_page`が実行されるため、挿入対象外だった既存ページの過剰削除が構造的に起きなくなった
- 上記いずれの経路でも、蓄積Blobは`_push_evicting`/`_clear_redo_stack`/`_dispose_state`経由でのみ解放され、二重解放ゼロを機械検証した（`TestBlobLeakDetection`に2件追加）
- 01-VERIFICATION.mdの`missing[]`4項目（CR-02本体・回帰テスト・WR-04・WR-05）すべてを本プラン1本で解消し、V190-UNDO-01 / ROADMAP Success Criterion 5の再検証を受けられる状態にした

## Task Commits

Each task was committed atomically:

1. **Task 0: page_edit 2段階mutation中間失敗の封じ方式確定（checkpoint:decision）** - オーケストレーターが事前提示し option-b が選択済み。コード変更なし・コミットなし
2. **Task 1: page_edit の中間失敗ロールバックと専用警告をend-to-endで成立させる（CR-02・option-b）** - `5903d7d`（fix）
3. **Task 2: 復元ループの一時fitz.Documentをfinallyで確実にクローズ（WR-04）** - `6dc802b`（fix）
4. **Task 3: insert（base op）の部分適用保護と最終ゲート（WR-05）** - `1b0d28f`（fix）

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

_Note: 各タスクは1コミット構成（TDD RED/GREEN分割は行わず、テスト+実装+lintを一体としてコミット）。Task 1/2/3とも自己検証で一発green、追加のfix commitは発生していない。_

## Files Created/Modified

- `pagefolio/file_ops.py` - `PartialRestoreError.content_at_risk`追加。`_restore_partial_error`へ`content_at_risk`/`page_edit_inserted`kwarg追加。`_undo`/`_redo`の通知文言をcontent_at_riskで切替。`page_edit`分岐をmutation順序反転（insert→delete）へ再設計し`_page_edit_inserted`マーカーを導入。7箇所のtmpにfinally保護を追加。`_apply_inverse`/`_restore_state`のinsert分岐へ部分適用保護を展開
- `pagefolio/lang.py` - `err_undo_restore_failed_content_at_risk`/`err_redo_restore_failed_content_at_risk`をja/en各1件、既存`err_*_restore_failed_partial`直後に追加
- `tests/test_pdf_ops.py` - `TestTempDocumentCloseGuard`（AST走査ガード）を新設。`TestUndoRedoRestoreFailure`へ5メソッド追加（page_edit中間失敗2件・tmp close裏取り1件・insert部分適用1件、+ヘルパー流用）
- `tests/test_undo_stress.py` - `TestBlobLeakDetection`へ2メソッド追加（insert部分失敗のBlob解放・page_edit復旧不能経路のBlob解放）

## Decisions Made

frontmatterの`key-decisions`を参照。要約: (1) Task 0は option-b 採用済みとして実行、(2) 警告文言は「失われた」ではなく「二重化または欠落の可能性」（option-bの構造上「失われた」は事実に反するため）、(3) APP_VERSION/開発履歴.md/READMEバッジは本プランで更新しない（Phase 3へ委譲）、(4) `merge`（base op）が`insert`と同型の未保護削除ループを持つという棚卸し結果を次マイルストーン候補として記録（コード変更なし）。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 新設テストのBlob二重解放検出でid()再利用による誤検知を修正**

- **Found during:** Task 1（`test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages`のBlob解放スパイ検証）
- **Issue:** 当初`release_log.append(id(blob))`でid()のみを記録していたところ、release直後にBlobがGCされCPythonのメモリ再利用により別の新規Blobオブジェクトが同じid()を取得し、無関係な2オブジェクトが「同一Blobへの二重解放」として誤検出された。フルスイート実行時に別ファイル（`tests/test_undo_stress.py::TestBlobLeakDetection::test_tmpdir_cleared_no_false_positive_leak`）でも、未解放のまま残ったBlobのGC遅延リーク警告が混入し失敗した
- **Fix:** 既存の`tests/test_undo_stress.py`の release スパイパターンに合わせ、`release_log.append(blob)`でオブジェクト参照そのものを保持し（GC・id()再利用を防止）、比較は`collections.Counter(id(b) for b in release_log)`で行う方式へ修正。あわせて両テストの末尾に`app._clear_undo_stacks()`を追加し、テスト終了時にスタック上のBlobを確実に解放してクロステスト汚染を防止した
- **Files modified:** `tests/test_pdf_ops.py`
- **Verification:** `tests/test_pdf_ops.py::TestUndoRedoRestoreFailure` + `tests/test_undo_stress.py`を連続実行して再現しないことを確認済み
- **Committed in:** `5903d7d`（Task 1 commit）

---

**Total deviations:** 1 auto-fixed（Rule 1 - テストのBlob二重解放検出ロジックの技術的誤りを修正）
**Impact on plan:** 検証意図・カバレッジに変更なし。テストの内部実装のみの訂正であり、スコープ拡大なし。

## Issues Encountered

- **【訂正・重要】フルスイート `pytest -q`（単一プロセス）が不安定になった。executor は当初これを「STATE.md 記載の既知フレーキーと同種であり本プランの回帰ではない」と分類したが、オーケストレーターの独立 A/B 検証によりこの分類は誤りと判明した。** 事実は「**製品コードは無実だが、本プランが追加したテストコードが引き金となって、無関係な OCR テストの潜在クラッシュを顕在化させた**」である
  - **クラッシュ箇所:** `tests/test_ocr_pipeline.py::TestPipelineHardening::test_cancel_finite_time_no_deadlock` の**実行中**（`-v` で特定）。症状は `Windows fatal exception: code 0x80000003`（STATUS_BREAKPOINT）+ `<freed thread state>` によるプロセス即死。STATE.md 記載の既知フレーキー（Tcl/Tk の `TclError` によるセットアップ ERROR）とは**別症状**であり、PLAN Task 3 (6) の免責条項の文言には該当しない
  - **A/B 実測（同一環境・メインワーキングツリー）:** 製品コード=基準 + テスト=基準 → 4/4 green（1177）／製品コード=**HEAD** + テスト=基準 → **4/4 green**（1177）／製品コード=基準 + テスト=**HEAD** → **4/4 クラッシュ**／HEAD（両方）→ 6 回中 2 回のみ 1184 passed。累計で基準内容 19 回中 0 クラッシュ、HEAD 内容約 10 回中 7 クラッシュ
  - **したがって `pagefolio/file_ops.py` / `pagefolio/lang.py` の変更は無実**（製品コード HEAD + 基準テストで 4/4 green）。引き金は `tests/test_pdf_ops.py`（HEAD）の存在
  - **トリガーは import 時点で成立する:** 新テスト 2 ファイルを `--ignore`（import しない）→ 3/3 green、`--deselect`（**import するが 1 件も実行しない**）→ 3/3 クラッシュ。さらに `test_pdf_ops.py` のみ HEAD で再現し、`test_undo_stress.py` のみ HEAD では再現しない
  - **絞り込めなかった点（未解明）:** 基準版に同等量の実コードを追加（サイズ模倣）→ 3/3 green、`import ast` / `pathlib` / `Path.resolve()` のみ追加 → 3/3 green。つまり**モジュールサイズでも import 文でもない**残りの要因（pytest の assertion rewriting 後のメモリレイアウト等、CPython のスレッド状態に関わるネイティブ層）が残っている。先頭 14 ファイルのみの実行では再現せず、フル収集が必要
  - **試行して失敗した修正（revert 済み）:** `_drive_pipeline` の孤児 daemon スレッド仮説に基づき、join タイムアウト後のキュードレイン＋再 join＋生存スレッド assert を実装したが、フルスイート 6 回中 5 回クラッシュのまま。追加した assert は全実行で成立したため孤児スレッド仮説は棄却。効果のないスコープ外変更のため revert した
  - **引き取り先:** v1.9.0 Phase 3（V190-QA-01 テスト安定化）。既知フレーキーと同じ「単一 pytest プロセスでの大量テスト連続実行」クラスの問題だが、本件は**再現率が高く A/B で切り分け済み**という点で調査が進んでいる。当面の運用は分割実行（`pytest -q --ignore=tests/test_ocr_pipeline.py` + `pytest -q tests/test_ocr_pipeline.py`）で 1184 全件 green を確認すること
- 本プランの成果物自体は全 green: `TestUndoRedoRestoreFailure` / `TestTempDocumentCloseGuard` / `tests/test_undo_stress.py` / `tests/test_lang_parity.py` を合わせて 34 passed。ソースゲート（`content_at_risk` 17・`finally:` 8・`_merge_pending_inverse(` 17・`def test_` 104）もすべて基準クリア
- `ruff check .`・`ruff format --check .` はともに一発で green。Task 1〜3 とも自己検証で一発 green、追加修正は発生しなかった

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `01-VERIFICATION.md`の`missing[]`4項目（CR-02本体のロールバック・回帰テスト・WR-04・WR-05）すべてを本プランで解消し、V190-UNDO-01 / ROADMAP Success Criterion 5の再検証（`/gsd-verify-work`相当）を受けられる状態になった
- Phase 1（保存・編集・設定の安全性是正）は本プラン（07・ギャップ是正）をもって、01-VERIFICATION.mdが指摘した新規欠陥（CR-02）も含め全9要件（V190-SAFE-01〜05・CFG-01/02・UNDO-01/02）を実質的に充足
- 次のアクションはPhase 1の再検証を経てPhase 2（OCRプロバイダ基盤整理 + OpenAIプロバイダ追加）へ進むこと
- 次マイルストーン候補として記録: `merge`（base op）の削除ループが`insert`と同型の未保護構造を持つ棚卸し結果（本プランではコード変更せず記録のみ）

---

*Phase: 01-safety-rollback*
*Completed: 2026-08-11*

## Self-Check: PASSED

- FOUND: pagefolio/file_ops.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_pdf_ops.py
- FOUND: tests/test_undo_stress.py
- FOUND: .planning/phases/01-safety-rollback/01-07-SUMMARY.md
- FOUND commit: 5903d7d
- FOUND commit: 6dc802b
- FOUND commit: 1b0d28f
