---
phase: 01-safety-rollback
verified: 2026-08-11T00:30:00Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "旧 Truth 5 の欠陥（_apply_inverse が partial-failure retry 由来の縮小 state[\"data\"] をそのまま次段の逆デルタとして使い回すため、再試行成功後の redo/undo でページの欠落・重複・内容混入が起きる）は 01-06（f9973ce..e41b7e3）の _pending_inverse／_merge_pending_inverse 方式により解消を確認した。旧 01-VERIFICATION.md の Evidence 3（delete undo→retry→redo）・Evidence 4（merge_resize undo→retry→redo→undo）の再現手順をそのままテスト化した回帰テスト（TestUndoRedoRestoreFailure 新設 8 件）が green で、独自の名指し実行でも再現しないことを確認した"
    - "delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の7opすべてで5手以上往復の回帰テストが追加され、merge_undo の非該当性も明示的にピン留めされた。蓄積逆デルタ Blob の evict/clear 時の解放・二重解放なしを検証するストレステスト2件も追加され green（TestBlobLeakDetection）"
  gaps_remaining:
    - "Truth 5（V190-UNDO-01 / Success Criterion 5）は依然として FAILED — 旧欠陥とは別種の新しい欠陥（01-REVIEW.md CR-02、file_ops.py:555-589 の page_edit 復元ループ）で再現。詳細は gaps を参照"
  regressions: []
gaps:
  - truth: "Undo/Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われず、Document が部分変更のまま残らない（V190-UNDO-01 / ROADMAP Success Criteria 5）"
    status: failed
    reason: >
      01-06（f9973ce..e41b7e3）は前回検証（01-VERIFICATION.md 旧版）が
      指摘した「_apply_inverse が縮小 state を次段逆デルタとして使い回す」
      欠陥（Evidence 3・4）を _pending_inverse／_merge_pending_inverse 方式で
      正しく解消した（本検証で独立に再確認・下記 Evidence A 参照）。
      しかし 01-06 完了後に実行された 2 回目のコードレビュー（01-REVIEW.md、
      commit 5bc55ca）が、01-06 自身が実装した蓄積方式のコードを精査する
      過程で **新規の Critical 欠陥（CR-02）** を発見しており、本検証で
      独立に実行・再現してこれを確認した。`_restore_state` の
      `op == "page_edit"` 分岐（`pagefolio/file_ops.py:555-589`）は
      1 ページにつき `delete_page(page_i)` → `insert_pdf(tmp, start_at=page_i)`
      という「唯一の 2 段階 mutation」を行う。`delete_page` が成功した
      直後に `insert_pdf` が失敗すると、doc からは既にそのページの
      内容が失われているにもかかわらず、doc から消えた内容の唯一の
      コピーである `captured`（`_capture_page_blob(page_i)` で事前捕捉）が
      `except Exception: self._release_blob(captured); raise` で
      **解放（破棄）される**。この時点でページ内容は doc にも Blob にも
      存在しない恒久的な喪失状態になり、かつ `remaining_state` は
      「doc は無変更（page_i は未適用のまま）」という前提で構築される
      ため、doc の実際のページ数（1 少ない）と矛盾したまま
      スタックへ戻る——まさに Success Criterion 5 が禁じる「Document が
      部分変更のまま残る」状態である。ユーザーが案内どおり再試行すると、
      インデックスがずれた状態で `_capture_page_blob(page_i)` が
      隣接ページ（無関係な別ページ）の内容を誤って捕捉し、その隣接
      ページを巻き添えで削除してしまう（二次被害）。独立再現スクリプトで
      実測したところ、4 ページ doc・page_edit(targets=[0,1]) の undo が
      1 回目の insert_pdf で失敗 → 2 回目（障害解消後）の undo は
      **例外を出さずに正常終了したように見える**にもかかわらず、
      最終的な doc は `['Page 1', 'Page 2', 'Page 4']`（3 ページ）で
      確定し、`Page 3` の内容が **エラー通知なく恒久的に消失**した
      （下記 Evidence B）。旧欠陥（Evidence 3・4）と異なり、この経路は
      01-06 の新規テスト（`TestUndoRedoRestoreFailure` 8 件）のいずれも
      カバーしていない（既存の `page_edit` 回帰テストは `_blob_bytes`
      読み込み失敗＝`delete_page` 呼び出し「前」のみを模しており、
      `delete_page` 成功後・`insert_pdf` 失敗という分岐そのものに
      到達しない）。`.planning/REQUIREMENTS.md` は V190-UNDO-01 を
      `[x]`（Complete）と記載しているが、本検証はこれを時期尚早と判断する。
    artifacts:
      - path: "pagefolio/file_ops.py"
        issue: "_restore_state の page_edit 分岐（555-589行目）: delete_page(page_i) 成功後に insert_pdf(tmp, start_at=page_i) が失敗すると、doc から失われた内容の唯一のコピーである captured を解放してしまい、恒久的なページ内容喪失が発生する。remaining_state は doc が無変更であるかのように構築されるため、doc の実ページ数と矛盾したままスタックへ戻り、再試行時に隣接ページを巻き添えで削除する（01-REVIEW.md CR-02。本検証で file_ops.py:512-517（delete）・613-616（insert base op）の関連箇所も含め独立に再確認）"
    missing:
      - "delete_page が成功した後に insert_pdf が失敗した場合、captured から即座にロールバック（元内容を doc へ再挿入）を試みるか、ロールバックが不可能な場合は captured を解放せず remaining_state の一部として保持し、専用の強い警告文言（『このページの内容が失われた可能性があります』）を出す対応（01-REVIEW.md CR-02 の Fix案）"
      - "page_edit の partial-failure 回帰テストに『delete_page 成功後・insert_pdf 失敗』のケースを追加し、(a) 内容が失われないこと、(b) 隣接ページが巻き添えにならないことを digest 一致で検証すること（既存の test_page_edit_partial_retry_then_redo_undo_roundtrip は _blob_bytes 失敗＝delete_page 呼び出し前のみをカバーしており非該当）"
      - "(付随・Warning) WR-04: delete（512-517行目）・insert_undo（617-641行目付近）・merge_undo・merge_resize・merge_resize_undo の tmp = fitz.open()→insert_pdf→tmp.close() が finally で保護されておらず、insert_pdf 失敗時に一時 fitz.Document が未クローズのまま残る"
      - "(付随・Warning) WR-05: insert（base op、613-616行目）の削除ループが CR-01/V190-UNDO-01 の部分適用保護から意図的に除外されたままであり、page_edit と同型の『doc 実ページ数と remaining_state の矛盾→再試行での巻き添え過剰削除』リスクが残る"
human_verification: []
---

# Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保）Verification Report

**Phase Goal:** 保存・複数ファイル挿入・ページ複製・設定 UI 操作・Undo/Redo のいずれかが失敗しても、Document・Undo 履歴・外部ファイルが確実に操作前の状態へ戻り、OCR OFF が通常 OCR・バッチ OCR・プラグイン経路すべてで一貫した意味を持つ。
**Verified:** 2026-08-11T00:30:00Z
**Status:** gaps_found
**Re-verification:** Yes — 01-06（Undo/Redo 逆デルタ縮小によるデータ破損の是正）適用後の再検証

## 重要な結論（先出し）

**01-06 は旧 Truth 5 の欠陥（Evidence 3・4）を正しく解消した。** 本検証で `TestUndoRedoRestoreFailure` の新設 8 件を独立に名指し実行し、さらに旧 Evidence 3・4 の再現手順を独自スクリプトで再実行して、いずれも欠陥が再現しないことを確認した（Evidence A）。

しかし、01-06 完了後に実行された 2 回目のコードレビュー（`01-REVIEW.md`、commit `5bc55ca`）が **01-06 自身の実装（page_edit 分岐）に新規の Critical 欠陥（CR-02）** を発見しており、本検証は独自に再現スクリプトを実行してこれを確認した（Evidence B）。`delete_page` が成功した直後に `insert_pdf` が失敗すると、doc から失われたページ内容の唯一のコピーが解放されてしまい、かつ再試行時に無関係な隣接ページが巻き添えで恒久的に消失する（本検証の再現では `Page 3` が最終的にエラー通知なく消えた）。これは Success Criterion 5 が明示的に禁じる「Document が部分変更のまま残る」状態そのものであり、対象は 01-06 が修正したのと同じコード領域（`_restore_state` の復元ループ）である。

`.planning/REQUIREMENTS.md` は V190-UNDO-01 を `[x]`（Complete）と記載しているが、CR-02 が未解消である以上、本検証はこれを時期尚早と判断し、**Truth 5（V190-UNDO-01）を継続して FAILED とする**。旧欠陥は解消されたが、Success Criterion 5 全体としては依然未達成であり、gap を継続する。

## Goal Achievement

### Observable Truths（ROADMAP.md Success Criteria 1〜5 を単位とする）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | パスワード保護 PDF を「保存」「名前を付けて保存」「上書き（フォールバック）」で保存しても暗号化が維持され、`pdf_has_password` が実ファイルと一致する（V190-SAFE-01/02） | ✓ VERIFIED | 01-06 の変更差分（`git diff --stat 2768af7..HEAD`）は `pagefolio/file_ops.py`・`tests/test_pdf_ops.py`・`tests/test_undo_stress.py` のみで、パスワード保存経路（`_save_as`/`_overwrite_current_file`/`_save_compressed`/`_save_file` フォールバック）は非対象。`pytest tests/test_password.py -q` を独立実行し 23 件 green（リグレッションなし） |
| 2 | OCR が OFF のとき通常 OCR・バッチ OCR・プラグイン経由いずれからも `off` がプロバイダ生成可能な値として扱われず、バッチ OCR が起動・実行開始できない（V190-SAFE-03） | ✓ VERIFIED | 01-06 は `pagefolio/ocr.py` を一切変更していない（`git diff --stat` で確認）。`pytest tests/test_ocr.py tests/test_provider_ui.py -q` を独立実行し 296 件 green |
| 3 | 複数ファイル挿入が途中失敗してもページ数・Undo スタックが操作前と一致し挿入元 Document は必ずクローズされる。ページ複製失敗時も既存ページ・Undo スタックが不変（V190-SAFE-04/05） | ✓ VERIFIED | `pagefolio/page_ops.py`（`_do_insert`/`_duplicate_page`）は `git diff --stat 2768af7..HEAD -- pagefolio/page_ops.py` で差分ゼロと確認（01-06 は file_ops.py の undo/redo 復元ロジックのみを変更し、挿入/複製の順操作自体には触れていない）。`pytest tests/test_pdf_ops.py -k "InsertRollback or DuplicateUndoTiming" -q` を独立実行し green |
| 4 | LLMConfigDialog を Cancel しても外部プロンプトファイルは変更されず、選択済みテンプレート編集後の切替では常に未保存確認が出る（V190-CFG-01/02） | ✓ VERIFIED | `pagefolio/dialogs/llm_config/` は `git diff --stat 2768af7..HEAD` で差分ゼロと確認。前回検証時点の VERIFIED 判定に変化なし |
| 5 | Undo/Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われず、Document が部分変更のまま残らない。duplicate/merge/merge_resize の4手往復回帰テストがページ構成一致を担保する（V190-UNDO-01/02） | ✗ FAILED（新経路で再現・CR-02） | 旧欠陥（Evidence 3・4）は解消を確認（Evidence A）。しかし page_edit 復元ループの新規欠陥（CR-02）により、`delete_page` 成功後の `insert_pdf` 失敗で doc が部分変更のまま確定し、再試行で隣接ページが巻き添えで恒久喪失することを独自再現で確認（Evidence B）。V190-UNDO-02 の「4手往復」自体（失敗注入なし）は引き続き VERIFIED（`TestAllOpsUndoRedoRoundtrip` 27件 green） |

**Score:** 4/5 truths verified（1件 failed。旧欠陥は解消されたが、同一 Success Criterion 内で新たな欠陥を検出）

#### Truth 5 の詳細 Evidence（本検証で独立実行・再現した結果）

**Evidence A（旧欠陥の解消を再確認）:**

- `pytest tests/test_pdf_ops.py::TestUndoRedoRestoreFailure -q`（名指し実行）: **15 passed**（01-04/01-05 由来の既存3件 + 01-06 新設8件 + 従来の関連テスト、全件独立実行で green を確認）
- `pytest tests/test_undo_stress.py::TestBlobLeakDetection -q`（名指し実行）: **5 passed**（01-06 新設2件を含む。蓄積逆デルタ Blob の evict/clear 時解放・往復中の二重解放なしを機械検証）
- 旧 01-VERIFICATION.md の Evidence 3（delete undo の 2 件目失敗→再試行成功→redo でページ構成が破損）・Evidence 4（merge_resize undo の 2 段階目失敗→再試行成功→redo→undo で内容混入）は、01-06 が追加した `test_delete_undo_partial_retry_then_redo_undo_roundtrip` / `test_merge_resize_undo_partial_retry_then_redo_undo_roundtrip` としてそのままテスト化されており、green であることを確認した

**Evidence B（新欠陥・CR-02 の独立再現）: page_edit の undo で delete_page 成功後に insert_pdf が失敗 → 再試行 → 隣接ページが巻き添えで恒久喪失**

手順（本検証用の独立スクリプトで、既存テストコードに依存せず再現）: 4 ページ doc（`Page 1`〜`Page 4`）→ `targets=[0,1]` で `page_edit`（黒塗り編集）→ `_undo()` を実行、`insert_pdf` の 2 回目の呼び出しで例外を注入:

```
1回目 undo（失敗）:
  errors shown: [('err_title', 'err_undo_restore_failed_partial')]
  doc len after 1st (failed) undo: 3  ← delete_page は成功済み、doc が既に1ページ短い
  doc content: ['', 'Page 3\n', 'Page 4\n']
  undo_stack[-1]: op=page_edit, data=[(0,...), (1,...)]  ← doc は3ページなのに remaining_state は「4ページ時点の未適用分」を表しており矛盾

2回目 undo（insert_pdf の障害を解消後・再試行）:
  errors shown: 追加エラーなし（成功したように見える）
  doc len after retry: 3  ← 本来は4ページに戻るはずが3ページのまま確定
  final doc content: ['Page 1\n', 'Page 2\n', 'Page 4\n']
  expected (original): ['Page 1\n', 'Page 2\n', 'Page 3\n', 'Page 4\n']
  → MISMATCH: Page 3 の内容がエラー通知なく恒久的に消失
```

再試行が「エラーなく完了したように見える」にもかかわらず、`Page 3`（当初の page_edit 対象外だった無関係なページ）が巻き添えで削除され、ユーザーへの通知は一切ない。これは 01-REVIEW.md CR-02 が指摘した再現手順と一致する。

**根本原因（コードで再確認）:** `_restore_state` の `page_edit` 分岐（`pagefolio/file_ops.py:566-589`）は、1 ページにつき `delete_page(page_i)` → `insert_pdf(tmp, start_at=page_i)` という 2 段階 mutation を行う唯一の op である。`delete_page` が成功した直後に `insert_pdf` が失敗すると、`except Exception: self._release_blob(captured); raise`（577行目）が、doc から消えた内容の唯一のコピーである `captured` を解放してしまう。外側の `except Exception as e:` 節（582行目）は `state["data"][applied:]`（`applied` はこの反復で加算される前に例外が出るため、失敗したページを含む）を `remaining_state` として構築するが、これは「doc は無変更」という前提の下でのみ正しい未適用分の表現であり、実際には `delete_page` が既に成功しているため doc は 1 ページ短い状態で確定している。この不整合が次の再試行時のインデックスずれを生み、無関係な隣接ページの巻き添え削除につながる。01-06 が新設した `_pending_inverse`／`_merge_pending_inverse` 方式（旧欠陥の解消）はこの分岐の**外側**（次段の逆デルタ構築）にのみ関与しており、この分岐**内側**（delete_page/insert_pdf 間の失敗時のロールバック欠如）には触れていない。同型の risk が `delete`（512-517行目）・`insert_undo`・`merge_undo`・`merge_resize`・`merge_resize_undo` の `tmp.close()` 未保護（WR-04）や `insert`（base op、613-616行目）の部分適用保護欠如（WR-05）にも波及していることを 01-REVIEW.md・本検証の双方で確認した。

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/file_ops.py`（`_merge_pending_inverse`・`_pending_inverse` 蓄積方式） | 部分失敗をまたいで完全な逆デルタを蓄積・合流 | ✓ VERIFIED（旧欠陥は解消） / ✗ 新欠陥あり（CR-02） | `_merge_pending_inverse`（146-161行目）・`_restore_partial_error` への `pending_inverse` 引数（163-180行目）・7 op 全展開を確認。旧欠陥の解消は Evidence A で確認。ただし page_edit 分岐内部の delete_page/insert_pdf 間のロールバック欠如（CR-02）は本方式の対象外のまま残る |
| `tests/test_pdf_ops.py::TestUndoRedoRestoreFailure`（8件新設） | 7 op + merge_undo 非該当ピンの5手以上往復回帰テスト | ✓ VERIFIED | 名指し実行で 15 passed（新設8件含む）。旧 Evidence 3・4 の再現手順をそのままテスト化していることをコード読解で確認 |
| `tests/test_undo_stress.py::TestBlobLeakDetection`（2件新設） | 蓄積逆デルタ Blob の解放・二重解放なし | ✓ VERIFIED | 名指し実行で 5 passed（新設2件含む） |
| `pagefolio/file_ops.py`（page_edit 分岐の delete_page/insert_pdf 間の失敗保護） | delete_page 成功後の insert_pdf 失敗でも内容が失われない | ✗ MISSING | 01-REVIEW.md CR-02 が指摘した Fix（ロールバック試行 or captured 保持）は未実装。本検証の独立再現（Evidence B）で内容喪失を確認 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `file_ops.py:_restore_state` 各 op mutation ループ | `_merge_pending_inverse` | 実際に適用できたページ分の逆デルタエントリを蓄積 | ✓ WIRED | 7 op すべてで確認（`grep -n "_merge_pending_inverse("` が delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の全分岐に出現） |
| `file_ops.py:_restore_partial_error` | `remaining_state["_pending_inverse"]` | 部分失敗時に蓄積分を引き継ぐ | ✓ WIRED | 全呼び出し箇所で `pending_inverse=merged_pending` が渡されていることを確認 |
| `file_ops.py:_dispose_state` | `_release_blob` | `_pending_inverse` エントリも解放対象に含める | ✓ WIRED | 126-129行目で確認。`TestBlobLeakDetection` の2新設テストで実測確認済み |
| `file_ops.py:_restore_state`（page_edit 分岐） | ロールバック処理（delete_page 成功後の insert_pdf 失敗時） | captured を保持 or 即時復元 | ✗ NOT_WIRED | 実装が存在しない。`except Exception: self._release_blob(captured); raise` が無条件に captured を解放する（577行目） |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 保存4経路の暗号化維持（回帰） | `pytest tests/test_password.py -q` | 23 passed | ✓ PASS |
| OCR OFF ガード + Apply/Cancel 契約（回帰） | `pytest tests/test_ocr.py tests/test_provider_ui.py -q` | 296 passed | ✓ PASS |
| 挿入ロールバック・複製後置化・4手往復（失敗注入なし、回帰） | `pytest tests/test_pdf_ops.py -k "InsertRollback or DuplicateUndoTiming or AllOpsUndoRedoRoundtrip" -q` | 27 passed | ✓ PASS |
| 01-06 新設回帰テスト（旧 Evidence 3・4 のテスト化） | `pytest tests/test_pdf_ops.py::TestUndoRedoRestoreFailure -q` | 15 passed | ✓ PASS |
| Blob ライフサイクル（蓄積逆デルタの解放・二重解放なし） | `pytest tests/test_undo_stress.py::TestBlobLeakDetection -q` | 5 passed | ✓ PASS |
| 独立再現A: 旧 Evidence 3/4 の再現手順（再実行） | 本検証用スクリプト | 欠陥再現せず（doc/スタック/redo/undo 往復すべて元の内容と一致） | ✓ PASS（旧欠陥解消確認） |
| 独立再現B: page_edit の delete_page 成功後 insert_pdf 失敗 → 再試行 → 隣接ページ喪失 | 本検証用スクリプト（Evidence B） | 再試行後、doc は3ページのまま確定し Page 3 が消失（エラー通知なし） | ✗ FAIL（新欠陥・Truth 5 の根拠） |
| lint | `ruff check . && ruff format --check .` | 全ファイル green | ✓ PASS |
| フルスイート（1回のみ実行、既存結果の確認） | `pytest -q` | 1177 passed（オーケストレーターの直前実行結果を採用。本検証は個別ファイル/クラス単位で重複実行し same 結果を確認） | ✓ PASS（ただし CR-02 を検出できるテストは1件も存在しない） |
| debt marker 走査 | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"`（01-06 変更3ファイル） | 該当ゼロ | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V190-SAFE-01 | 01-01 | 保存3経路+フォールバックの暗号化維持 | ✓ SATISFIED | `tests/test_password.py` green・01-06 は対象コードパス未変更 |
| V190-SAFE-02 | 01-01 | `pdf_has_password` の論理導出・実ファイル一致 | ✓ SATISFIED | 同上 |
| V190-SAFE-03 | 01-02 | OCR OFF の全経路一貫化 | ✓ SATISFIED | `tests/test_ocr.py`/`test_provider_ui.py` green・01-06 は `ocr.py` 未変更 |
| V190-SAFE-04 | 01-04 | 複数ファイル挿入のロールバック | ✓ SATISFIED | `TestInsertRollback` green・`page_ops.py` は01-06の差分外 |
| V190-SAFE-05 | 01-04 | ページ複製の Undo 後置確定 | ✓ SATISFIED | `TestDuplicateUndoTiming` green・同上 |
| V190-CFG-01 | 01-03 | LLM設定 Cancel は外部ファイル不変 | ✓ SATISFIED | `dialogs/llm_config/` は01-06の差分外 |
| V190-CFG-02 | 01-03 | 未保存確認の単一判定経路 | ✓ SATISFIED | 同上 |
| V190-UNDO-01 | 01-04・01-06 | Undo/Redo 復元失敗時の state 保全・Document 完全性 | ✗ BLOCKED | REQUIREMENTS.md は `[x]` 記載だが時期尚早と判断。旧欠陥（Evidence 3・4）は解消したが、新欠陥（CR-02、page_edit の delete_page/insert_pdf 間のロールバック欠如）で「Document が部分変更のまま残らない」要件が未達成（Evidence B） |
| V190-UNDO-02 | 01-05 | duplicate/merge/merge_resize の4手往復（失敗注入なし） | ✓ SATISFIED | `TestAllOpsUndoRedoRoundtrip` green |

ORPHANED requirements: なし（Phase 1 の Requirements 9件すべてがいずれかの PLAN の `requirements` フィールドに現れている）。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER の debt marker | — | 01-06 が変更した3ファイルで検索したが該当ゼロ |
| `pagefolio/file_ops.py:566-589`（`_restore_state` の `page_edit` 分岐） | `delete_page` 成功後の `insert_pdf` 失敗時、`captured`（doc から失われた内容の唯一のコピー）を無条件解放しロールバックしない | 🛑 Blocker | Truth 5 / V190-UNDO-01 未達成の直接原因（CR-02）。本検証で独立再現（Evidence B） |
| `pagefolio/file_ops.py:512-517`（`delete`）ほか `insert_undo`/`merge_undo`/`merge_resize`/`merge_resize_undo` | `tmp = fitz.open()` → `insert_pdf` → `tmp.close()` が `finally` 未保護 | ⚠️ Warning | `insert_pdf` 失敗時に一時 `fitz.Document` が未クローズのまま残る（WR-04、01-REVIEW.md）。CR-02 ほど即座のデータ破損ではないが、Blob ライフサイクル規約（CLAUDE.md）の趣旨に反する |
| `pagefolio/file_ops.py:613-616`（`insert` base op） | 削除ループが CR-01/V190-UNDO-01 の部分適用保護から意図的に除外されたまま | ⚠️ Warning | `delete_page` が mid-loop で失敗すると、doc は無変更という前提で元の（`num`件ぶんの）state がそのまま戻り、再試行で `num` 回（`k`回ではなく）削除が再実行され既存ページを過剰削除しうる（WR-05、01-REVIEW.md）。page_edit（CR-02）と同型の脅威モデル |
| `.planning/REQUIREMENTS.md:33` | `V190-UNDO-01` が `[x]`（Complete）と記載 | ⚠️ Warning（情報） | CR-02 が未解消のため本検証はこれを時期尚早と判断。是正プラン完了・再検証 passed 後にチェックを維持するのが適切 |

### Human Verification Required

なし（今回の gap はコードレベルで確定的に再現・特定できたため、人間検証待ちの項目はない）。

### Gaps Summary

01-06（`f9973ce`..`e41b7e3`）は、前回検証が指摘した Truth 5 の欠陥（`_apply_inverse` が partial-failure retry 由来の縮小 `state["data"]` を次段逆デルタの元データとして使い回し、再試行成功後の redo/undo でページの欠落・重複・内容混入が起きる問題、旧 Evidence 3・4）を、`_pending_inverse`／`_merge_pending_inverse` によるデータモデル変更（mutation ループ内で実際に適用できたページ分の逆データを蓄積し、部分失敗時は remaining_state へ引き継ぐ方式）で **正しく解消した**。本検証は `TestUndoRedoRestoreFailure` の新設8件・`TestBlobLeakDetection` の新設2件を独立に名指し実行し、また旧 Evidence 3・4 の再現手順そのものを独自スクリプトで再実行して、いずれも欠陥が再現しないことを確認した。Truths 1〜4（V190-SAFE-01〜05・V190-CFG-01/02）についても、01-06 の変更差分が該当コードパスに一切触れていないことを `git diff --stat` で確認し、関連テスト（342件超）の独立実行で回帰がないことを確認した。

一方、01-06 完了後に実行された2回目のコードレビュー（`01-REVIEW.md`、commit `5bc55ca`）が、01-06 自身が実装した蓄積方式のコード（`_restore_state` の各 op mutation ループ）を精査する過程で、**旧欠陥とは独立した新規の Critical 欠陥（CR-02）** を `page_edit` 分岐に発見した。`page_edit` は「1ページにつき `delete_page` → `insert_pdf` の2段階 mutation」を行う唯一の op であり、`delete_page` が成功した直後に `insert_pdf` が失敗すると、doc から失われた内容の唯一のコピー（`captured`）が解放されてしまい、かつ `remaining_state` は「doc は無変更」という誤った前提で構築される。本検証はこの欠陥を独立スクリプトで再現し（Evidence B）、再試行が「成功したように見える」にもかかわらず、無関係な隣接ページ（`Page 3`）がエラー通知なく恒久的に消失することを実測で確認した。

Success Criterion 5 の文言「Undo/Redo の復元処理が失敗した場合、…Document が部分変更のまま残らない」は、この CR-02 のシナリオにおいて明確に満たされていない。これは 01-06 が対処した「旧欠陥」と発生メカニズムこそ異なる（旧欠陥＝次段の逆デルタが縮小されるサイレントなデータ破損／新欠陥＝2段階 mutation の中間失敗による即時のデータ喪失と隣接ページ巻き添え）が、**同一の Success Criterion 5・同一のコード領域（`_restore_state` の復元ループ）に属する未解決の欠陥**であるため、本検証は Truth 5（V190-UNDO-01）を継続して FAILED と判定する。旧欠陥が pre-existing（`ae30ae3` 時点のコードにも同種の「page 数不変を前提とした remaining_state 構築」という構造的弱点が存在した）であるか 01-06 由来であるかを問わず、Success Criterion 5 自身が「失敗時は Document が部分変更のまま残らない」ことを明示的な受け入れ条件として掲げている以上、この具体的な再現可能シナリオが残っている状態でフェーズを合格とすることはできない。

`.planning/REQUIREMENTS.md` は V190-UNDO-01 を `[x]`（Complete）と記載しているが、本検証はこれを時期尚早と判断する。CR-02（および波及する WR-04・WR-05）を閉じる是正プランを追加実行し、再検証で本 gap が解消されたことを確認したうえで Complete 判定を確定すべきである。

**推奨対応:** 01-REVIEW.md CR-02 の Fix案（`delete_page` 成功後の `insert_pdf` 失敗時に `captured` からのロールバックを試み、ロールバックも失敗した場合は `captured` を解放せず保持したうえで強い警告文言を出す）を実装し、「`delete_page` 成功後・`insert_pdf` 失敗」を狙い撃ちしたテストを追加すること。あわせて WR-04（`tmp.close()` の `finally` 保護）・WR-05（`insert` base op への部分適用保護の展開）も同一の是正プランに含めることを推奨する（いずれも `_restore_state` の同じ復元ループ群に属し、脅威モデル・修正パターンが共通するため）。

---

_Verified: 2026-08-11T00:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — 01-06（`f9973ce`..`e41b7e3`）+ コードレビュー再実行（`5bc55ca`、CR-02検出）適用後_
