---
phase: 01-safety-rollback
verified: 2026-08-10T13:20:00Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "「復元失敗直後、doc がスタック上の remaining state と矛盾する中間状態のまま残る」（旧 Truth 5 の再現条件そのもの）は解消を確認した。復元失敗直後の doc 内容は、スタックへ戻された remaining_state が表す『未適用分のみ』と正確に一致する（delete/merge_resize の両ケースで実測）"
    - "『失敗直後にユーザーが案内どおり再試行すると、既に成功済みの分へ mutation が重複適用される』という当初の再現手順は解消を確認した（重複挿入・二重削除は発生しない。merge_resize の _merged_page_deleted フラグによる二重削除防止も機能を実測確認）"
  gaps_remaining:
    - "Truth 5（V190-UNDO-01）は依然として FAILED — 旧欠陥とは異なる新しい経路で再現。詳細は gaps を参照"
  regressions:
    - "CR-01 の実装（_apply_inverse が state[\"data\"] をそのまま次段 inverse の元データとして使い回す設計）により、『部分失敗 → 再試行成功』のシーケンスを経由した state は、以後の redo/undo 方向の逆デルタが『再試行時に実際に処理した残存分のみ』に縮小されてしまい、元々の全件ぶんのページデータが恒久的に失われる。旧 CR-01 が防いだ『即時二重適用』とは別種の、より発見しづらい遅延的データ破損（サイレントなページ消失・内容混入）を新たに生んでいる。7/8 op（delete・delete_redo・page_edit・insert_undo・insert_redo・merge_resize・merge_resize_undo）で構造的に再現可能と判断（merge_undo のみ inverse がスカラー old_count のみを運ぶため非該当）。delete と merge_resize の2経路は実際にコードを実行して再現・実証済み"
gaps:
  - truth: "Undo/Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われず、Document が部分変更のまま残らない（V190-UNDO-01 / ROADMAP Success Criteria 5）"
    status: failed
    reason: >
      cb5344e（CR-01）は「復元失敗直後の doc 状態が remaining_state と矛盾する」
      「即時再試行で重複 mutation が起きる」という 01-REVIEW.md 記載の再現手順は
      解消した（下記 Evidence 1・2 で個別に実測確認）。しかし『履歴が失われない』
      という要件は依然として満たされていない。原因は _apply_inverse
      （pagefolio/file_ops.py:307-442）が常に `state["data"]` を直接の元データ
      として次段の逆デルタを構築する設計にあり、`_restore_state` の先頭で
      `inverse = self._apply_inverse(state)` を計算した「後」に mutation
      ループが実行される（313行目 → 各 op 分岐）。1回目の失敗で state が
      「未適用の残存分のみ」に縮小された remaining_state としてスタックへ
      戻され、2回目（再試行）でこの縮小版 remaining_state を使って
      `_restore_state` が呼ばれると、mutation 自体は正しく残存分だけを
      適用して doc を完全に復旧できる一方、`_apply_inverse` が同じ
      「縮小された state["data"]」から次段の逆デルタ（次の redo/undo 用の
      state）を構築してしまうため、押し戻された逆デルタは「今回の再試行分
      のみ」を表す不完全なデータになる。この不完全な逆デルタが次段の
      undo_stack/redo_stack へ積まれ、後続の redo（または undo）で
      「元々あった全ページ分の復元」が行われず、ページの欠落・別ページの
      混入が発生する。doc は最終的に元の内容と一致しない状態で確定し、
      ユーザーへの通知も一切ない（サイレントなデータ破損）。これは
      01-REVIEW.md CR-01 が指摘した「即時の重複挿入・過剰削除」とは異なる
      新種の欠陥であり、cb5344e は元の欠陥を解消したのではなく、より
      発見しづらい形へ*移し替えた*（shift）と判定する。
    artifacts:
      - path: "pagefolio/file_ops.py"
        issue: "_apply_inverse（307-442行目）が state[\"data\"] を直接／浅い変換で次段 inverse の元データとして使い回しており、state が partial-failure retry 由来の remaining_state（縮小データ）である場合に、次段の逆デルタも同じ縮小データを引き継いでしまう。_restore_partial_error（137-146行目）／各 op の except 節（458-642行目）は『再試行に必要な残存分』の追跡はするが、『再試行成功後に構築すべき、次段の逆デルタが本来必要とする完全なデータ』への言及・保持機構が存在しない"
    missing:
      - "『再試行の対象（残存分のみ）』と『再試行成功後に次段の逆デルタを構築する際の元データ（完全な当初のページ集合）』を別フィールドとして state に持たせるか、_apply_inverse を『mutation ループの中で実際に適用できた各ページの完全な逆データを蓄積し、それを使って逆デルタを構築する』方式へ改める（=『_restore_state 呼び出しをまたいで、当初の全件ぶんの逆データを保持し続ける』設計变更）"
      - "delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo の7 op すべてで、『部分失敗→再試行成功→さらにredo/undo→再度undo/redo』という5手以上の往復を通してページ構成が完全に元へ戻ることを検証する回帰テスト（既存の TestUndoRedoRestoreFailure 3件は『再試行成功直後の doc 状態』までしか検証しておらず、その後の redo/undo 往復の正しさを検証していないため、この欠陥を検出できていなかった）"
      - "merge_undo は inv[\"data\"] がスカラー（old_count）のみのため対象外だが、他 7 op の修正時に merge_undo も含めて同型の往復テストを追加し、非該当であることを明示的に固定する"
human_verification: []
---

# Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保）Verification Report

**Phase Goal:** 保存・複数ファイル挿入・ページ複製・設定 UI 操作・Undo/Redo のいずれかが失敗しても、Document・Undo 履歴・外部ファイルが確実に操作前の状態へ戻り、OCR OFF が通常 OCR・バッチ OCR・プラグイン経路すべてで一貫した意味を持つ。
**Verified:** 2026-08-10T13:20:00Z
**Status:** gaps_found
**Re-verification:** Yes — コードレビュー是正（CR-01/WR-01/WR-02/WR-03、4コミット）適用後の再検証

## 重要な結論（先出し）

前回検証（`previous_status: gaps_found`, 4/5）で指摘した Truth 5 の欠陥は、その**再現手順としては解消**を確認した。しかし独自の追加再現（下記 Evidence 3・4）により、CR-01 の修正実装自体に**新しい、より深刻なデータ破損経路**が存在することを実測で確認した。SUMMARY.md・01-REVIEW-FIX.md の「全4件修正済み・回帰テストで検証済み」という主張は、**修正コミット cb5344e が新設した回帰テスト（`TestUndoRedoRestoreFailure` の3件）が『再試行成功直後の doc 状態』までしか検証しておらず、その後の redo/undo 往復までは検証していない**という盲点により、この新欠陥を検出できていなかった。**Truth 5（V190-UNDO-01）は引き続き未達成であり、gap を継続する。**

## Goal Achievement

### Observable Truths（ROADMAP.md Success Criteria 1〜5 を単位とする）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | パスワード保護 PDF を「保存」「名前を付けて保存」「上書き（フォールバック）」で保存しても暗号化が維持され、`pdf_has_password` が実ファイルと一致する（V190-SAFE-01/02） | ✓ VERIFIED | `pagefolio/file_ops.py` の `_save_as`/`_overwrite_current_file`/`_save_compressed`/`_save_file` フォールバックすべてに `PDF_ENCRYPT_KEEP` が既定化されている（コード確認・4修正コミットはこの経路を一切変更していない）。WR-03（分割保存への警告確認ダイアログ追加）は `_split_by_range`/`_split_each_page` のみに影響し、本criterionの対象4経路（保存/名前を付けて保存/上書き/上書きフォールバック）には含まれないコードパス（`git diff` で確認）。`tests/test_password.py`（23件）を独立実行し全件 green |
| 2 | OCR が OFF のとき通常 OCR・バッチ OCR・プラグイン経由いずれからも `off` がプロバイダ生成可能な値として扱われず、バッチ OCR が起動・実行開始できない（V190-SAFE-03） | ✓ VERIFIED | `build_provider`（`ocr.py`）は `off` を専用例外 `OCRDisabledError` で明示的に拒否する分岐を維持（WR-02 はキー欠落時のデフォルト値を `DEFAULT_OCR_PROVIDER="lmstudio"` へ一元化しただけで、明示的な `"off"` の拒否ロジック自体には触れていない）。既定値統一により UI 側 (`_update_ocr_buttons_state`/`_update_batch_menu_state`) と `build_provider` の判定が完全一致することも確認。`tests/test_ocr.py`（165件）・`tests/test_provider_ui.py`（131件）を独立実行し全件 green |
| 3 | 複数ファイル挿入が途中失敗してもページ数・Undo スタックが操作前と一致し挿入元 Document は必ずクローズされる。ページ複製失敗時も既存ページ・Undo スタックが不変（V190-SAFE-04/05） | ✓ VERIFIED | `pagefolio/page_ops.py:_do_insert`/`_duplicate_page` は4修正コミットの差分に一切含まれない（`git diff 9e6836c..HEAD --stat` で `page_ops.py` の変更はWR-03の分割保存2ブロック追加のみと確認済み）。`tests/test_pdf_ops.py::TestInsertRollback`（5件）・`TestDuplicateUndoTiming`（2件）を独立実行し全件 green（リグレッションなし） |
| 4 | LLMConfigDialog を Cancel しても外部プロンプトファイルは変更されず、選択済みテンプレート編集後の切替では常に未保存確認が出る（V190-CFG-01/02） | ✓ VERIFIED | `pagefolio/dialogs/llm_config/` 配下は4修正コミットの差分に一切含まれない（`git diff --stat` で確認）。前回検証時点の VERIFIED 判定に変化なし |
| 5 | Undo/Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われず、Document が部分変更のまま残らない。duplicate/merge/merge_resize の4手往復回帰テストがページ構成一致を担保する（V190-UNDO-01/02） | ✗ FAILED（新経路で再現） | 前回指摘の再現手順（復元失敗直後の doc とスタックの矛盾／即時再試行での重複適用）は解消を確認（Evidence 1・2）。しかし『部分失敗→再試行成功』後の逆デルタが縮小データのまま次段スタックへ積まれ、後続の redo/undo でページ構成が恒久的に破損することを独自再現で確認（Evidence 3・4）。V190-UNDO-02 の「4手往復」自体（失敗注入なし）は引き続き VERIFIED（`TestAllOpsUndoRedoRoundtrip` 27件 green）だが、V190-UNDO-01 が要求する「履歴が失われない」は満たされない |

**Score:** 4/5 truths verified（1件 failed。前回と同スコアだが、failed の内実は異なる — 旧欠陥は解消、新欠陥を検出）

#### Truth 5 の詳細 Evidence（独立再現・cb5344e 適用後のコードに対する実行結果）

すべて `pagefolio.file_ops.FileOpsMixin`（一部 `pagefolio.page_ops.PageOpsMixin` 併用）を直接使う独立スクリプトで、既存テストコードには一切依存せず再現した。

**Evidence 1（解消確認）: delete の undo、2件目で Blob 読込失敗 → 1回目失敗直後の doc 状態**
```
1回目 undo 失敗直後: doc len = 3（3ページ削除分中1件のみ復元＝矛盾なし。remaining_state.data も1件のみを正しく表す）
undo_stack に残る state: op=delete, len(data)=1, data[0][0]=1
2回目 undo（障害解消後）: doc len = 4（元通り）、digest 一致、undo_stack=0, redo_stack=1
```
→ 旧欠陥（doc が中間状態のまま残る／同じ2件ぶん state で重複再試行される）は解消。

**Evidence 2（解消確認）: merge_resize の undo、二段階 mutation の1段目（結合ページ削除）自体が失敗**
```
delete_page(insert_at) 自体が例外 → doc は無変更のまま(3ページ)（mutation前に検出、_merged_page_deleted は False のまま正しく維持）
再試行（正常化後）: doc len = 4、digest 一致
```
→ 二段階 mutation の1段目失敗でも二重削除は起きない。

**Evidence 3（新欠陥・再現）: delete の undo、2件目で失敗 → 再試行成功 → その後の redo でページ構成が破損**

手順: 3ページ doc → `targets=[0,1]` で delete → undo（1件目成功・2件目で `_blob_bytes` 失敗）→ undo 再試行（成功、doc は元の3ページへ完全復旧・digest 一致）→ **ここまでは正常**。続けて **redo** を実行（元々の delete 操作を再現するはずの操作）:
```
再試行成功直後: redo_stack[-1] = {"op": "delete_redo", "data": [(1, None)]}  ← 本来 [(0,None),(1,None)] のはずが1件しかない
redo 実行後の doc 内容: ['Page 1\n', 'Page 3\n']  ← ページ数2（本来は「両方削除」で1ページのはず）
```
`redo_stack` に積まれた `delete_redo` state の `data` が「1回目の失敗後に残っていた1件（page_i=1）」だけを表しており、当初 delete 対象だった page_i=0 の情報が失われている。このため redo は page_i=0 を削除せず、doc の内容が本来のシーケンス（delete→undo→redo なら「2ページとも削除された状態」に戻るはず）と一致しない。

**Evidence 4（新欠陥・再現、より深刻）: merge_resize の undo、2件目の元ページ再挿入で失敗 → 再試行成功 → redo → 再度 undo でページ内容が破損**

手順: 4ページ doc → `targets=[0,1]` で merge_resize → undo（1件目の元ページ再挿入は成功・2件目で `insert_pdf` 失敗）→ undo 再試行（成功、doc は元の4ページへ完全復旧・digest 一致=前回検証時点の確認範囲はここまで）。続けて **redo → undo** を実行:
```
redo 実行後の doc 内容: ['Page 1\nPage 2\n', 'Page 1\n', 'Page 3\n', 'Page 4\n']  ← 結合ページの内容が壊れ、Page 1 が重複
続けて undo 実行後の doc 内容: ['Page 1\nPage 2\n', 'Page 2\n', 'Page 1\n', 'Page 3\n', 'Page 4\n']（5ページ、本来4ページ）
期待される元の内容: ['Page 1\n', 'Page 2\n', 'Page 3\n', 'Page 4\n']
```
この結果は、`01-REVIEW-FIX.md` が「回帰テストで確認済み」と主張する `test_merge_resize_undo_partial_failure_preserves_remaining_and_retry_completes` の検証範囲（＝再試行成功直後の doc 状態・スタック件数のみ）の**外側**で発生する。実際に該当テストを読み込み確認したところ、`app._undo()` を2回呼んで復旧を確認した時点で assertion が終了しており、その後の `_redo()`/再 `_undo()` の呼び出しは一切行われていない（`tests/test_pdf_ops.py:2306-2326`）。

**根本原因（コードで特定）:** `_restore_state`（`pagefolio/file_ops.py:444-661`）は関数冒頭（450行目）で `inverse = self._apply_inverse(state)` を計算してから mutation 分岐へ進む。`_apply_inverse`（307-442行目）は多くの op で `state["data"]` を直接（または軽い変換で）次段の逆デルタの元データとして使い回す設計であり、「今この呼び出しで渡された `state`」が partial-failure retry によって既に縮小された remaining_state である場合、その縮小データがそのまま次段（redo または undo）の永続的な逆デルタとして確定してしまう。CR-01 の `PartialRestoreError`/`_restore_partial_error` は「再試行時に何を残り実行すべきか」は正しく追跡しているが、「再試行が完了した“後”に、次の逆方向操作のために保持すべき完全なデータ」という別の関心事を一切扱っていない。8 op 中 `merge_undo` のみ逆デルタがスカラー（`old_count`）で per-page データを運ばないため非該当だが、`delete`／`delete_redo`／`page_edit`／`insert_undo`／`insert_redo`／`merge_resize`／`merge_resize_undo` の**7 op が構造的に同一欠陥を抱える**（このうち `delete`・`merge_resize`(undo方向)・`merge_resize_undo`(redo方向) の3方向は実行して実証済み。残り4方向はコード構造の完全な対称性から同型の欠陥が存在すると判断）。

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/file_ops.py`（`PartialRestoreError`／`_restore_partial_error`／8 op の部分適用追跡） | 部分適用時に未適用分のみの state を伝搬 | ✓ VERIFIED（再試行成功後の逆デルタ生成は ✗） | `PartialRestoreError` クラス（21-37行目）・`_restore_partial_error`（137-146行目）は実装され、即時の重複適用防止としては機能する（Evidence 1・2）。ただし `_apply_inverse` が縮小 state をそのまま次段データとして採用するため、再試行成功後の履歴保全は未達成（Evidence 3・4） |
| `pagefolio/file_ops.py:_apply_inverse`（`delete`→`delete_redo` の WR-01 プレースホルダ化） | 無駄な Blob キャプチャの排除 | ✓ VERIFIED | `inv["data"] = [(page_i, None) for page_i, _ in state["data"]]`（337行目）を確認。ただし同じ `state["data"]` 由来という構造自体が Truth 5 の新欠陥の一部（上記参照） |
| `pagefolio/ocr.py:DEFAULT_OCR_PROVIDER` | UI/build_provider 既定値の一元化 | ✓ VERIFIED | 定数定義（171行目）・`build_provider`（450行目）・`app.py` 2箇所（344/366行目付近）すべてが参照。回帰テスト green |
| `pagefolio/page_ops.py`（WR-03 分割保存の警告確認） | `pdf_has_password` 時の確認ダイアログ | ✓ VERIFIED | `_split_by_range`/`_split_each_page` に確認分岐を追加済み（コード・テスト確認）。本フェーズの必須条件（保存4経路）には影響しない |
| `tests/test_pdf_ops.py::TestUndoRedoRestoreFailure` | CR-01 の回帰テスト3件 | ⚠️ 不十分（盲点あり） | 3件とも green で実行確認済みだが、いずれも「再試行成功直後の doc/スタック状態」までしか検証しておらず、その後の redo/undo 往復を検証していないため Evidence 3・4 の欠陥を検出できない |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `file_ops.py:_undo`/`_redo` | `PartialRestoreError` | except節での捕捉・`remaining_state` の push | ✓ WIRED | コード確認・Evidence 1/2 で実測確認 |
| `file_ops.py:_restore_state`（8 op ループ） | `_restore_partial_error` | 途中失敗時の未適用分算出 | ✓ WIRED（算出自体は正しい） | 全 op で確認 |
| `file_ops.py:_restore_state` 冒頭 | `_apply_inverse(state)` | 次段逆デルタの事前計算 | ⚠️ WIRED だが不整合 | mutation 前に計算されるため、state が縮小済み remaining_state の場合、縮小データがそのまま次段へ伝搬される（Evidence 3・4 の根本原因） |
| `page_ops.py:_split_by_range`/`_split_each_page` | `messagebox.askyesno`（新設） | `pdf_has_password` 真の場合の確認 | ✓ WIRED | コード確認・テスト green |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 保存4経路＋パスワード付与/解除の実ファイル暗号化検証 | `pytest tests/test_password.py -q` | 23 passed | ✓ PASS |
| OCR OFF ガード全経路 | `pytest tests/test_ocr.py -q` | 165 passed | ✓ PASS |
| Apply/Cancel 契約 | `pytest tests/test_provider_ui.py -q` | 131 passed | ✓ PASS |
| 挿入ロールバック・複製後置化・4手往復（失敗注入なし） | `pytest tests/test_pdf_ops.py -k "InsertRollback or DuplicateUndoTiming or AllOpsUndoRedoRoundtrip" -q` | 27 passed | ✓ PASS |
| CR-01 公式回帰テスト（`TestUndoRedoRestoreFailure`） | `pytest tests/test_pdf_ops.py::TestUndoRedoRestoreFailure -v` | 7 passed | ✓ PASS（ただし検証範囲に盲点あり、上記参照） |
| 独立再現1: delete undo 部分失敗直後の doc 整合性 | 本検証用スクリプト（Evidence 1） | doc が remaining_state と矛盾しない | ✓ PASS（旧欠陥解消確認） |
| 独立再現2: merge_resize 二段階1段目自体の失敗 | 本検証用スクリプト（Evidence 2） | 二重削除なし・doc 無変更で保持 | ✓ PASS（旧欠陥解消確認） |
| 独立再現3: delete undo 部分失敗→再試行成功→redo | 本検証用スクリプト（Evidence 3） | redo 後のページ構成が元のシーケンスと不一致 | ✗ FAIL（新欠陥・Truth 5 の根拠） |
| 独立再現4: merge_resize undo 部分失敗→再試行成功→redo→undo | 本検証用スクリプト（Evidence 4） | 最終 doc がページ重複・内容混入・元の内容と不一致 | ✗ FAIL（新欠陥・Truth 5 の根拠） |
| lint | `ruff check . && ruff format --check .`（変更5ファイル） | 全ファイル green | ✓ PASS |
| フルスイート | `pytest -q`（1回のみ実行） | 1167 passed | ✓ PASS（既存回帰の範囲では健全。ただし本検証が発見した経路は既存テストのカバー範囲外） |
| debt marker 走査 | `grep -n -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"`（変更5ファイル） | 該当ゼロ | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V190-SAFE-01 | 01-01 | 保存3経路+フォールバックの暗号化維持 | ✓ SATISFIED | `tests/test_password.py` green・4修正コミットは対象コードパス未変更 |
| V190-SAFE-02 | 01-01 | `pdf_has_password` の論理導出・実ファイル一致 | ✓ SATISFIED | 同上 |
| V190-SAFE-03 | 01-02 | OCR OFF の全経路一貫化 | ✓ SATISFIED | `TestOCRDisabledGuard` green・WR-02 は既定値統一のみで拒否ロジック自体は不変 |
| V190-SAFE-04 | 01-04 | 複数ファイル挿入のロールバック | ✓ SATISFIED | `TestInsertRollback` green・`page_ops.py` の該当コードは4修正コミットの差分外 |
| V190-SAFE-05 | 01-04 | ページ複製の Undo 後置確定 | ✓ SATISFIED | `TestDuplicateUndoTiming` green・同上 |
| V190-CFG-01 | 01-03 | LLM設定 Cancel は外部ファイル不変 | ✓ SATISFIED | `dialogs/llm_config/` は4修正コミットの差分外 |
| V190-CFG-02 | 01-03 | 未保存確認の単一判定経路 | ✓ SATISFIED | 同上 |
| V190-UNDO-01 | 01-04 | Undo/Redo 復元失敗時の state 保全・Document 完全性 | ✗ BLOCKED | 旧再現手順は解消したが、新しい再現手順（Evidence 3・4）でサイレントなページ構成破損を確認。「履歴が失われない」という要件文言が未達成 |
| V190-UNDO-02 | 01-05 | duplicate/merge/merge_resize の4手往復（失敗注入なし） | ✓ SATISFIED | `TestAllOpsUndoRedoRoundtrip` green。ただし「失敗からの復旧を挟んだ往復」は対象外の既存テストのため、この観点では未カバー（V190-UNDO-01 側の gap として計上） |

ORPHANED requirements: なし（Phase 1 の Requirements 9件すべてがいずれかの PLAN の `requirements` フィールドに現れている）。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER の debt marker | — | 4修正コミットが変更した全ファイルで検索したが該当ゼロ |
| `pagefolio/file_ops.py:307-442`（`_apply_inverse`）と `pagefolio/file_ops.py:444-661`（`_restore_state`） | 次段逆デルタの計算が partial-failure retry 由来の縮小 state に依存 | 🛑 Blocker | Truth 5 / V190-UNDO-01 未達成の直接原因。7/8 op（merge_undo を除く）に共通する構造的欠陥（Evidence 3・4 で実証） |
| `tests/test_pdf_ops.py::TestUndoRedoRestoreFailure` | 3件の CR-01 回帰テストが「再試行成功直後」までしか検証せず、後続の redo/undo 往復を検証していない | ⚠️ Warning | この欠陥検出の盲点そのもの。既存テストの拡張（もしくは追加テスト）が是正計画に含まれるべき |
| `pagefolio/page_ops.py:1008-1082` | `_split_by_range`/`_split_each_page` は分割後ファイルへの実際のパスワード再付与は未実装（WR-03 は警告確認のみ） | ⚠️ Warning（情報） | 01-REVIEW-FIX.md が明記した既知の残スコープ。本フェーズの Success Criteria（保存/名前を付けて保存/上書きフォールバックのみが対象）には含まれない |

### Human Verification Required

なし（今回の gap はコードレベルで確定的に再現・特定できたため、人間検証待ちの項目はない）。

### Gaps Summary

4件の是正コミット（cb5344e/747ef9c/4e5dbc9/2768af7）を独立に検証した結果、Criteria 1〜4（V190-SAFE-01〜05・V190-CFG-01/02）は引き続き健全であり、いずれのコミットも該当コードパスへ悪影響を与えていないことを確認した。WR-02（OCR OFF既定値の一元化）・WR-03（分割保存の警告確認）はレビュー時の指摘どおり自己完結した改善であり、犯人捜しの対象にはならない。

一方 Criterion 5（V190-UNDO-01/02）については、**前回検証で指摘した欠陥の「再現手順」自体は解消したことを実測で確認した**（Evidence 1・2）。しかし、独自に踏み込んだ検証（「部分失敗→再試行成功」の“後”に redo/undo を1〜2手続ける」という、CR-01 自身の回帰テストがカバーしていない範囲）により、**cb5344e の実装アプローチそのものに起因する新しい欠陥**を発見した（Evidence 3・4）。

具体的には、`_apply_inverse` が次段の逆デルタを構築する際に用いる `state["data"]` が、partial-failure からの再試行時には「今回処理した残存分のみ」に縮小されており、この縮小データがそのまま — 再試行が完全に成功したにもかかわらず — 次の redo/undo 用の永続的な逆デルタとして確定してしまう。結果として、当初の全ページ分の情報が失われ、後続の redo/undo でページの欠落・重複・内容混入という**サイレントなデータ破損**が発生する。これは元の CR-01（即時の重複挿入・過剰削除で、少なくとも直後に発覚しやすい）よりも**発見が遅れやすく、実害としてはむしろ深刻な方向への“バグの移し替え”**と評価する。対象は8 op中 `merge_undo` を除く7 op（delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo）で、うち `delete` と `merge_resize`（両方向）は実際にコードを実行して実証済み、残り4方向はコード構造の完全な対称性から同型の欠陥を持つと判断する。

この欠陥は SUMMARY.md・01-REVIEW-FIX.md のいずれにも記載がなく、`git diff 9e6836c..HEAD` にもこれを是正するコードは含まれていない。「フルスイート1167件 green」という主張自体は事実だが、この欠陥を検出できるテストが1件も存在しないためテストスイートの green はこの欠陥の非存在を保証しない。

**推奨対応:** `_apply_inverse` を「mutation ループの実行結果（実際に適用できた各ページの完全なデータ）を蓄積してから逆デルタを構築する」方式へ改めるか、あるいは「partial-failure retry を経由した state から構築される逆デルタは、当初のフルセットのデータを別途保持しているフィールド（例: `state["_original_data"]`）から再構築する」設計変更が必要。修正時は、単に「再試行成功直後の doc/スタック状態」だけでなく、**その後さらに redo→undo（またはundo→redo）を1〜2手続けた最終的なページ構成が、失敗を一切挟まなかった場合と一致すること**を回帰テストの必須アサーションに追加すること（Evidence 3・4 の再現手順をそのままテスト化することを推奨）。

---

_Verified: 2026-08-10T13:20:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — 4件の code-review fix commit (cb5344e/747ef9c/4e5dbc9/2768af7) 適用後_
