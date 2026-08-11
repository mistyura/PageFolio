---
phase: 03-qa-release-gate
fixed_at: 2026-08-11T12:03:43Z
review_path: .planning/phases/03-qa-release-gate/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-08-11T12:03:43Z
**Source review:** .planning/phases/03-qa-release-gate/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4（CR-01 / WR-01 / WR-02 / WR-03。IN-01 は指示によりスコープ外）
- Fixed: 4
- Skipped: 0

**検証実施環境:** 隔離ワークツリー（`workflow.use_worktrees=true` のため git worktree
`.claude/worktrees/rf-03-370-1786448603` 上・ブランチ `gsd-reviewfix/03-370`）。
`.venv` はワークツリーに複製されないため、メイン作業ツリーの
`C:/Users/shdwf/work/project/PageFolio/.venv/Scripts/python.exe` をインタプリタとして
ワークツリー内の cwd から実行した。フルスイート（`pytest -q`、1404 件収集 =
着手前 1398 件 + 本修正で追加した回帰テスト 6 件）は失敗 0 件で完走した
（1 回目は CLAUDE.md 記載の既知 `STATUS_BREAKPOINT` フレーキーで途中クラッシュ、
再実行で 1404 passed を確認）。この結果はメイン作業ツリーへ fast-forward マージ
した後も同一コミット群として再現可能。

## Fixed Issues

### CR-01: 別ファイルを開いた後に保存失敗トーストを再試行すると、無関係なドキュメントの内容で元ファイルを無確認上書きしてしまう

**Files modified:** `pagefolio/file_ops.py`
**Commit:** `7251698`
**Applied fix:** レビューの「より堅牢な代替/追加策」（`retry_cb` 束縛時に `self.doc` の
identity も束縛し、実行時に一致しなければ書き込まない案）を採用した。
`_do_save_file` / `_do_save_as` / `_do_save_compressed` に `bound_doc` 引数を追加し、
確認・パス選択層（`_save_file` / `_save_as` / `_save_compressed`）が
`functools.partial(self._do_save_XXX, path, self.doc)` の形で確認時点の
`self.doc` を確定パスと共に束縛するよう変更した。実保存層の先頭ガードを
`if not self.doc: ...` から `if not self.doc or self.doc is not bound_doc: ...`
へ拡張し、再試行実行時に `self.doc` が束縛時と異なる（別ファイルが開かれた・
閉じられた）場合は一切書き込みを行わずステータス通知のみで戻るようにした。
`_open_pdf_path` / `_do_open_merged` / `_close_file` 側は無改造（トースト表示の
消し忘れ経路が将来増えても、実保存層側のガードが構造的に誤書き込みを防ぐ
ため、複数箇所への防御コード追加を避けて過剰な複雑化を回避した）。
3 経路とも `encryption=fitz.PDF_ENCRYPT_KEEP` の指定は変更しておらず、
`tests/test_password.py`（32 件）は全件 green のまま。

### WR-01: `app.doc` 差し替えシナリオがテストで一切カバーされていない

**Files modified:** `tests/test_toast.py`
**Commit:** `5817e7b`
**Applied fix:** `_save_file` / `_save_as` / `_save_compressed` の3経路それぞれに、
`retry_cb` 取得後に `app.doc` を別ドキュメントへ差し替えてから `retry_cb` を
呼んでも、無関係なドキュメントの内容が束縛パスへ書き込まれないことを検証する
テストを追加した（`test_save_file_retry_does_not_write_unrelated_doc_after_doc_swapped`
ほか2件）。既存の `test_save_file_retry_writes_to_bound_path_not_current_filepath`
（`app.filepath` の差し替えのみ検証）は置き換えず、補完として追加した。
CR-01 実装前に一時的にコード側の識別子チェックを外した状態でこれらのテストを
実行し、3件とも RED（無関係ドキュメントの内容が書き込まれてしまう）になる
ことを確認済み。CR-01 適用後は GREEN。

### WR-02: ドキュメントを閉じた後もトーストが永久に残留する

**Files modified:** `pagefolio/file_ops.py`, `tests/test_toast.py`
**Commit:** `3562b09`
**Applied fix:** CR-01 で拡張した早期 return ガード（`self.doc` が falsy、または
`bound_doc` と不一致）の直前で、該当カテゴリ（`save_file` / `save_as` /
`save_compressed`）のトーストを `self._toast.dismiss(...)` するよう
3経路すべてに追加した。これにより、ファイルを閉じた後（または別ファイルを
開いた後）に古いトーストの再試行が発火しても、書き込みを行わないだけでなく
トースト自体も消える。保存3経路それぞれに、ドキュメントを閉じた後の再試行で
`toast.dismissed[-1]` が該当カテゴリになることを検証する回帰テストを追加した
（`test_save_file_retry_dismisses_toast_after_doc_closed` ほか2件）。ガード変更
前の状態でこれらのテストを実行し、3件とも RED（`toast.dismissed` が空のまま）
になることを確認済み。ガード変更後は GREEN。

### WR-03: docstring が実態以上の安全性を主張しており誤解を招く

**Files modified:** `pagefolio/file_ops.py`（CR-01 コミット `7251698` に含まれる）
**Commit:** `7251698`（CR-01 と同一コミット）
**Applied fix:** レビューの Fix 節が提示した2案（docstring 訂正 / 実装変更で
実際に同一性を保証する）のうち、CR-01 で後者（実装変更）を採用したため、
`_do_save_file` / `_do_save_as` / `_do_save_compressed` の docstring は
CR-01 のコミット内で「`path` だけでなく確認時点の `self.doc` も `bound_doc`
として束縛しており、再試行時点で `self.doc` が別ドキュメントへ差し替わって
いる場合は書き込みを一切行わない」という実態どおりの記述へ書き換え済み
（WR-02 のコミットでトースト dismiss の記述も追記）。旧 docstring が主張して
いた「アプリ状態が変化しても束縛された `path` へのみ書き込む」という
書き込み**先**のみの保証から、書き込む**内容**（ドキュメント本体）の正しさも
保証する記述へ更新されており、実装と乖離のない状態になっている。CR-01/WR-02
の実装変更それ自体が docstring の不正確さを解消する構造になっているため、
独立した追加コミットは作成していない（レビューの Fix 節が「実装を変更する
ことで実際に self.doc の同一性も保証する」ことを WR-03 の解決策として明示
的に許容している）。

## Skipped Issues

None — 対象4件はすべて修正済み（IN-01 はスコープ外のため未対応）。

---

_Fixed: 2026-08-11T12:03:43Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
