---
phase: 01-safety-rollback
fixed_at: 2026-08-10T11:37:51Z
review_path: .planning/phases/01-safety-rollback/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-08-10T11:37:51Z
**Source review:** .planning/phases/01-safety-rollback/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Undo/Redo 復元失敗保護が「多ページ復元の部分適用」を考慮していない

**Files modified:** `pagefolio/file_ops.py`, `pagefolio/lang.py`, `tests/test_pdf_ops.py`
**Commit:** `cb5344e`
**Applied fix:**

`_undo`/`_redo` の復元失敗保護は `_restore_state` の適用が atomic であることを
暗黙に前提としていたが、`delete`/`page_edit`/`insert_undo`/`insert_redo`/
`merge_undo`/`merge_resize`/`merge_resize_undo`/`delete_redo` は 1 ページずつ
`self.doc` を mutate するループのため、途中の1件で例外が出ると「それより前は
既に doc へ適用済み」の状態のまま、元の（全件ぶんの）state をそのままスタック
へ戻して再試行を促していた。ユーザーが再試行すると、同じ全件ぶんの delta が
先頭から再適用され、既に成功していたページへ重複 insert/delete が発生し得た。

`page_ops.py` の `_do_insert`（同フェーズの 01-04 で改修済み）が「実際に何件
適用できたか」を `total`/`removed`/`residual` で追跡している設計を精神的な
precedent としつつ、review 自身が提示した Fix スニペット（「未適用分のみを
表す state を構築してスタックへ戻す」方式）に合わせて実装した:

- 新設の `PartialRestoreError` 例外（`remaining_state`/`original_exception` を
  保持）と `_restore_partial_error` ヘルパーを追加。
- 上記 8 op すべての多ページループで「何件適用できたか」（`applied` カウント
  または `deleted`/`captured` 集合）を追跡し、途中で例外が出た場合は
  - 成功済み分の Blob を `_release_blob` で解放し（二重解放・リーク防止）、
  - **未適用分のみ**を表す `remaining_state`（同じ op・同じ shape のデータ）
    を構築して `PartialRestoreError` として送出する。
- `merge_resize`（「結合ページ削除」→「元ページ再挿入」の2フェーズ構成）は
  `_merged_page_deleted` フラグを remaining state に持たせ、再試行時に結合
  ページを二重削除しない（削除済みかどうかを追跡できないと、再試行が誤って
  別ページを削除してしまう）よう対応した。
- `_undo`/`_redo` は `PartialRestoreError` を専用の except 節で捕捉し、
  `remaining_state` をスタックへ戻す。`_restore_state` の末尾処理（例外で
  未到達）を `_handle_partial_restore` で肩代わりし、`current_page` の
  クランプ・`selected_pages` の範囲外インデックス間引き・再描画を行う。
- 専用のエラーメッセージ（`err_undo_restore_failed_partial`/
  `err_redo_restore_failed_partial`、ja/en）を追加し、「一部のページは
  既に変更されています。もう一度実行すると残りのページに処理を再試行します」
  旨をユーザーへ明示する（既存の atomic op 向けメッセージとは区別）。

**回帰テスト（`tests/test_pdf_ops.py::TestUndoRedoRestoreFailure`）:**
3パターンで、途中失敗→部分適用の検証と、障害解消後の再試行で doc が
重複/欠損なく正しく復旧することを検証した。
- `test_delete_undo_partial_failure_preserves_remaining_and_retry_completes`:
  挿入系ループ（`delete` の undo）。2件目の Blob 読み込み失敗を注入。
- `test_delete_redo_partial_failure_preserves_remaining_and_retry_completes`:
  削除系ループ（`delete_redo` の redo）。2件目の `delete_page` 失敗を注入。
- `test_merge_resize_undo_partial_failure_preserves_remaining_and_retry_completes`:
  2フェーズ構成（`merge_resize` の undo）。`_merged_page_deleted` フラグに
  よる再試行時の二重削除防止を検証。

各テストで (a) 1回目の失敗後に doc が二重適用や過剰削除なく実際に適用できた
分だけの状態に留まること、(b) undo/redo スタックに未適用分のみを表す1エントリ
だけが残ること、(c) 障害条件解消後の再試行で doc が最終的に元の内容（digest
一致）へ正しく復旧し、スタックも正常な1件ずつの状態に戻ることを確認した。

**注記:** 本フィックスは REVIEW.md の Fix スニペット（`applied`/`remaining`
の shape の踏襲）を direct precedent とし、`_do_insert` は設計思想（実際の
適用件数を明示的に追跡し、フィクション上の「全件成功/全件失敗」を仮定しない）
の precedent として参照した。`_do_insert` 自体が行う「巻き戻しロールバック」
までは行わず、REVIEW 自身の提案どおり「未適用分のみを次回の対象として正確に
表す」方式を採用している（ロールバック方式は delete 系ループでキャプチャ
していない bytes の再確保が必要になり複雑度・リスクが増すため）。

**要人間検証（推奨）:** `merge_resize` の2フェーズ制御（`_merged_page_deleted`
フラグ）は本フェーズ新設の複雑なロジックであり、回帰テストで基本シナリオを
検証済みだが、実運用での大規模 PDF・高頻度 undo/redo での動作は開発者による
追加確認を推奨する。

---

### WR-01: `_apply_inverse` の `delete`→`delete_redo` 変換が意味のない（誤った内容の）Blob をキャプチャしている

**Files modified:** `pagefolio/file_ops.py`, `tests/test_pdf_ops.py`
**Commit:** `747ef9c`
**Applied fix:**

`_apply_inverse` の `op == "delete"` 分岐は、`_restore_state` の mutation
（削除ページの再挿入）より前に呼ばれるため、その時点ではまだページが
未挿入で `_capture_page_blob(page_i)` を呼んでも無関係な別ページの内容を
誤ってキャプチャしていた。消費側（`delete_redo` の restore・次段の
inverse）はどちらも `page_i` のみを参照し blob を使わないため実害は
無かったが、無駄な `_capture_page_blob` 呼び出し（Blob 確保・後で解放
されるまでリソースを握る）が発生していた。

REVIEW.md の Fix 提案どおり、`inv["data"]` をプレースホルダ（`None`）化
し、無駄なキャプチャ・Blob 保持を廃止した。`_release_blob`（CR-01 で
追加した `hasattr(blob, "release")` ガード）が `None` を安全に無視する
ため、`_dispose_state` 側の変更は不要だった。

**回帰テスト:** `test_delete_undo_apply_inverse_does_not_capture_blob`
（`TestAllOpsUndoRedoRoundtrip`）を追加し、`_capture_page_blob` が
`delete`→`delete_redo` 変換時に一度も呼ばれないこと、および構築される
`inverse["data"]` の各要素が `(page_i, None)` になっていることを検証した。

---

### WR-02: OCR OFF ガードの既定値が `build_provider` と UI 側で不一致

**Files modified:** `pagefolio/app.py`, `pagefolio/ocr.py`, `tests/test_provider_ui.py`
**Commit:** `4e5dbc9`
**Applied fix:**

`_update_ocr_buttons_state`/`_update_batch_menu_state`（UI側の活性判定）は
`settings.get("ocr_provider", "off")` を、`build_provider` は
`settings.get("ocr_provider", "lmstudio")` をそれぞれ既定値として使って
おり、`ocr_provider` キー欠落時に UI は disabled 表示のまま
`build_provider` は普通にプロバイダを生成してしまう食い違いがあった。

`pagefolio/ocr.py` に `DEFAULT_OCR_PROVIDER` 定数を新設し、`build_provider`
と app.py の両関数がこの単一の情報源を参照するよう統一した。

**方向性の判断（REVIEW の提案からの適応）:** REVIEW.md は「既定値を
一箇所に集約する」とだけ述べ、どちらの値（`"off"` / `"lmstudio"`）へ
統一するかは明示していなかった。調査の結果、`build_provider` 側には
`tests/test_ocr.py::test_no_ocr_provider_key_returns_lmstudio_provider`
という「`ocr_provider` キーなし設定でも `LMStudioProvider` を返す」
ことを明示的に固定した既存の後方互換契約があった。`"off"` 側へ統一する
とこの契約を破壊し、かつ LMStudioProvider（ローカル完結・外部送信なし）
まで拒否することになり、得られる安全性向上より既存契約の破壊コストの
方が大きいと判断し、`"lmstudio"` へ統一した（外部送信を伴うクラウド
プロバイダではなくローカル完結プロバイダのため、キー欠落時のフェイル
セーフとしても許容範囲と判断）。

**回帰テスト:** `test_missing_ocr_provider_key_matches_build_provider_default`
（`TestUpdateOcrButtonsState`）を追加し、`ocr_provider` キーなし設定で
UI側の活性判定（`!disabled`）と `build_provider` の実際の挙動（プロバイダ
生成成功）が一致すること、および両者が同一の `DEFAULT_OCR_PROVIDER`
定数を参照していることを検証した。既存の後方互換テストは変更なしで
そのまま green。

---

### WR-03: 分割保存（`_split_by_range`/`_split_each_page`）がパスワード保護を引き継がない

**Files modified:** `pagefolio/page_ops.py`, `pagefolio/lang.py`, `tests/test_pdf_ops.py`
**Commit:** `2768af7`
**Applied fix:**

`<scope_guidance>` の指示に従い、まず本 finding が本フェーズの差分外・
要件外（V190-SAFE-01/02 は上書き/別名/縮小保存/上書きフォールバックの
4経路のみを対象とし、分割保存は対象外）であることを確認したうえで、
「正しく自己完結したフィックスが利用可能か」を評価した。

調査の結果、`self` にはパスワード文字列そのものを一切保持していない
ことを確認した（`pdf_has_password` は真偽値のみ、`_authenticate_doc`
内で入力されたパスワードはローカル変数のまま関数を抜けると破棄される）。
そのため「元のパスワードで分割後ファイルを再暗号化する」という完全な
修正には、(a) セッション中パスワードをメモリ保持する設計変更（新たな
セキュリティ上のトレードオフを伴う）、または (b) 分割時にパスワード
再入力を求める新規UIフロー（エラーハンドリング・ダイアログ文言等の
設計判断を要する）のいずれかが必要であり、`<scope_guidance>` が
明示的に禁止する「設計判断やアプリが保持していない状態を要する半端な
フィックス」に該当すると判断した。

一方で、この finding が指摘する核心の害は「保護が**静かに**失われる」
点にある。この部分だけは、既存の `compress_split_confirm` と同型の
確認ダイアログパターンを使い、パスワード再暗号化ロジックには一切
触れない自己完結した最小フィックスとして解決可能だったため、
REVIEW.md の Fix セクションが挙げるフォールバック案（「少なくとも
『分割後のファイルはパスワード保護されません』という警告を明示する」）
を適用した:

- `pdf_has_password` が真の場合、分割の実処理（`_check_split_overwrite`
  通過後・圧縮確認ダイアログの前）で警告確認ダイアログを表示し、
  ユーザーが拒否すれば分割を中止する。
- 保存の暗号化 semantics 自体は変更していない（分割後ファイルは
  従来どおり平文のまま — 挙動を変えたのは「ユーザーへの開示と確認」の
  みで、実際の暗号化処理には一切手を加えていない）。

再暗号化そのもの（パスワード再入力による分割後ファイルの保護）は
今回のスコープ外として別 issue で追跡することを推奨する。

**回帰テスト:** `TestPdfSplit` に4件追加。
- `test_split_by_range_password_protected_declines_writes_no_files`:
  警告が表示され、拒否時にファイルが1つも生成されないこと。
- `test_split_by_range_password_protected_accepts_proceeds`: 承諾時に
  従来どおり分割が実行されること（回帰防止）。
- `test_split_each_page_password_protected_declines_writes_no_files`:
  `_split_each_page` 側でも同様に機能すること。
- `test_split_by_range_without_password_skips_warning`: 非保護PDFでは
  警告が出ず、既存の圧縮確認ダイアログのみが表示されること（既存動作
  の保持）。

**要人間検証（推奨）:** 分割保存でのパスワード再暗号化（パスワード
再入力フローの追加）自体は今回未着手のため、別途 backlog/todo として
追跡することを推奨する。

## Skipped Issues

None — 全ての in-scope finding を修正した。

## 検証サマリ

- `ruff check` / `ruff format --check`: 変更した全ファイルで通過。
- `python -c "import ast; ast.parse(...)"`: 変更した全ファイルで構文確認済み。
- `pytest`（フルスイート）: 4コミットそれぞれの直後に実行し、最終的に
  1167 件すべて green（実行環境: 本ワークツリー内、`--basetemp` を
  スクラッチパス指定）。
- lang.py の ja/en キー整合（`tests/test_lang_parity.py`）: 新規追加した
  4キー（`err_undo_restore_failed_partial`/`err_redo_restore_failed_partial`/
  `split_password_warn_title`/`split_password_warn_msg`）を含め green。

---

_Fixed: 2026-08-10T11:37:51Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
