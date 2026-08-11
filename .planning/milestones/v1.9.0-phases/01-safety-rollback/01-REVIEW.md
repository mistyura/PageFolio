---
phase: 01-safety-rollback
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - pagefolio/app.py
  - pagefolio/dialogs/batch_ocr.py
  - pagefolio/dialogs/llm_config/sections.py
  - pagefolio/file_ops.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_providers/__init__.py
  - pagefolio/ocr_providers/errors.py
  - pagefolio/page_ops.py
  - tests/test_ocr.py
  - tests/test_password.py
  - tests/test_pdf_ops.py
  - tests/test_provider_ui.py
  - tests/test_undo_stress.py
findings:
  critical: 0
  warning: 6
  info: 1
  total: 7
status: issues_found
---

# Phase 01: Code Review Report（再レビュー・iteration 3・01-07 ギャップ是正の検証）

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

前回レビュー（iteration 2）で検出した **CR-02**（`page_edit` の `delete_page`
成功後に `insert_pdf` が失敗すると `captured` Blob が解放されページ内容が
永久欠損する）、**WR-04**（`delete`/`insert_undo`/`merge_undo`/
`merge_resize`/`merge_resize_undo` の一時 `fitz.Document` が `finally` 未保護）、
**WR-05**（`insert` base op の削除ループが CR-01 の部分適用保護から除外されて
いた）は、01-07（option-b: 差し替えページを先に `insert_pdf` してから旧
ページを `delete_page` する順序反転）でいずれも是正されており、**回帰なく
正しく機能している**ことをコードトレースおよび既存の回帰テスト
（`tests/test_pdf_ops.py` の `test_page_edit_insert_failure_rolls_back_and_retry_preserves_neighbors`
/ `test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages`）で
確認した:

- **option-b の mutation 順序**: `_restore_state` の `page_edit` 分岐
  （`file_ops.py:596-681`）で、差し替えページを `insert_pdf` で先に入れて
  から旧ページを `delete_page` する順序になっており、doc がページ内容を
  失っている瞬間が構造的に存在しない（最悪でも新旧が両方残る＝喪失ゼロ）。
- **`_page_edit_inserted` 再試行マーカー**: `state` 側にのみ存在し
  `_apply_inverse` が構築する `inverse` へは一切漏れない設計（`inserted_marker`
  は `state.pop(...)` で取り出され、失敗時のみ `_restore_partial_error` の
  `page_edit_inserted=` 経由で `remaining_state` へ書き戻される）ことを確認。
- **`content_at_risk` の伝播**: `_undo`/`_redo` 双方で `err_..._content_at_risk`
  キーへの文言分岐が実装され、`lang.py` に ja/en 両方でキーが存在する
  （462 キーで完全一致）ことを確認。
- **一時 `fitz.Document`（`tmp`）の `finally` 保護**: `delete`（552-556行）・
  `duplicate_undo`（703-708行）・`page_edit`（619-666行）・`insert_undo`
  （754-758行）・`merge_undo`（818-822行）・`merge_resize`（856-860行）・
  `merge_resize_undo`（901-907行）の7箇所すべてで `finally: tmp.close()`
  が確認できた。
- **`insert`（base op）の削除ループ**: `already = len(state.get("_pending_inverse", []))`
  を `_merge_pending_inverse`（pop する）呼び出し**より前**に読み、複数
  ラウンドの部分失敗をまたいでも絶対ページインデックスが正しく復元される
  ことを手動トレース（5ページ挿入を2回に分けて失敗させるケース）で確認。
  `remaining_data = [insert_at, num - deleted]` により再試行時の過剰削除
  （WR-05 で指摘した「本来削除対象でない既存ページまで削除する」バグ）は
  再現しない。

一方で、この精査の過程で `content_at_risk` 判定に **1件の取りこぼし**
（WR-01・下記）を新規発見した。これは今回のフォーカスである「`content_at_risk`
の伝播が漏れなく機能しているか」という観点そのものに関わる指摘であり、
他の WARNING より重く見るべきである。加えて `page_ops.py` 側に、本フェーズの
主眼ではないが同一ファイルリスト内に存在する既存の一時ドキュメントリーク・
Undo エントリ残留・エラーハンドリング不足を複数検出した（WR-02〜WR-06）。
BLOCKER 相当（実データ損失が即時発生する不具合）は検出しなかった。

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: page_edit 再試行経路で `_capture_page_blob` 失敗時に `content_at_risk` が立たない

**File:** `pagefolio/file_ops.py:619-634`

**Issue:**
`_restore_state` の `page_edit` 分岐、再試行経路（`page_i in inserted_marker`）
では、差し替えページが既に `page_i` に挿入済みで旧ページが `page_i + 1` に
残っている「二重化状態」から再開する。

```python
if page_i in inserted_marker:
    captured = self._capture_page_blob(page_i + 1)
    try:
        self.doc.delete_page(page_i + 1)
    except Exception:
        self._release_blob(captured)
        content_at_risk = True
        raise
    inserted_marker.discard(page_i)
```

`self.doc.delete_page(page_i + 1)` が失敗した場合は `content_at_risk = True`
が正しく立つ。しかしその直前の `self._capture_page_blob(page_i + 1)`
自体が例外を送出した場合（Blob ストアの一時ファイル書き込み失敗等、
`UndoBlobStore` がディスクへ退避する経路で発生しうる I/O エラー）は、
この `try` の外側で発生するため `content_at_risk` は既定値 `False` の
まま外側の `except Exception as e:`（674-680行）へ抜け、
`_restore_partial_error` に `content_at_risk=False` で渡ってしまう。

この瞬間、doc は「差し替えページ（page_i）と旧ページ（page_i+1）が両方
存在する」二重化状態のまま変化していない（`delete_page` を一度も呼んで
いないため状態自体は悪化していないが、doc は依然として一意性が保証
されない状態のままである）。つまりこの回でも `content_at_risk`
（`PartialRestoreError` の docstring が定義する「内容の一意性が保証
されない状態（喪失または二重化）」）に該当するにもかかわらず、通常の
部分失敗メッセージ（`err_undo_restore_failed_partial` /
`err_redo_restore_failed_partial`）が表示され、専用の強い警告
（`..._content_at_risk`）が出ない。`_page_edit_inserted` マーカー自体は
正しく `page_i` を保持したまま伝播するため後続の再試行で復旧は可能だが、
ユーザーへの警告レベルが実態（ページが二重に存在している）より弱く
出てしまう。今回のフォーカスである「`content_at_risk` の伝播漏れをすべて
塞ぐ」という契約の一部が未網羅のまま残っている。

**Fix:**
`_capture_page_blob` 呼び出し自体も try で囲み、失敗時に
`content_at_risk = True` を立ててから re-raise する（正常経路の
`delete_page` 失敗時と同じ扱いにする）。

```python
if page_i in inserted_marker:
    try:
        captured = self._capture_page_blob(page_i + 1)
    except Exception:
        content_at_risk = True
        raise
    try:
        self.doc.delete_page(page_i + 1)
    except Exception:
        self._release_blob(captured)
        content_at_risk = True
        raise
    inserted_marker.discard(page_i)
```

### WR-02: `_overwrite_current_file` が `os.replace` 失敗時に `.tmp` ファイルを残す

**File:** `pagefolio/file_ops.py:1119-1132`

**Issue:**
```python
data = self.doc.tobytes(**save_kwargs)
self.doc.close()
try:
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    self.doc = fitz.open(path)
    self.pdf_has_password = derive_pdf_has_password(...)
except Exception:
    self.doc = fitz.open(stream=data, filetype="pdf")
    raise
```
`open(tmp, "wb")` の書き込みが完了した後、`os.replace(tmp, path)` が
（Windows でファイルロック・権限エラー等により）失敗すると、`except`
節は `self.doc` をメモリ上の bytes から復元するのみで、書き込み済みの
`path + ".tmp"` を削除しない。`tests/test_password.py::
TestSavePathsKeepEncryption::test_overwrite_failure_keeps_password_state`
は `pdf_has_password` と `doc` の復元のみを検証しており、この `.tmp`
ファイル残留は回帰テスト網羅外である。繰り返し保存に失敗すると同名の
`.tmp` ファイルがユーザーの作業ディレクトリに残り続ける。

**Fix:**
```python
except Exception:
    self.doc = fitz.open(stream=data, filetype="pdf")
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise
```

### WR-03: `_duplicate_page` の一時 `fitz.Document` が例外時に close されない

**File:** `pagefolio/page_ops.py:190-201`

**Issue:**
```python
try:
    tmp = fitz.open()
    tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
    self.doc.insert_pdf(tmp, start_at=pno + 1)
    tmp.close()
    self._save_undo("duplicate", pno=pno)
    ...
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
```
`tmp.insert_pdf(...)` または `self.doc.insert_pdf(tmp, ...)` が例外を
送出した場合、`tmp.close()` の行に到達せず `tmp` が close されないまま
リークする。`file_ops.py` 側は 01-07 で一時 `fitz.Document` 7 箇所
すべてに `finally` 保護が入ったのに対し、同じ「一時ドキュメントを作って
挿入する」パターンである `page_ops.py` 側にはこの保護が及んでおらず、
プロジェクト内で一貫性が欠けている。

**Fix:**
```python
tmp = fitz.open()
try:
    tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
    self.doc.insert_pdf(tmp, start_at=pno + 1)
finally:
    tmp.close()
self._save_undo("duplicate", pno=pno)
```

### WR-04: `_do_merge_resize` / `_do_merge` の一時 `fitz.Document` が例外時に close されない

**File:** `pagefolio/page_ops.py:871-935`（`_do_merge_resize`）、`pagefolio/page_ops.py:937-961`（`_do_merge`）

**Issue:**
`_do_merge_resize` は `new_doc = fitz.open()`（875行）の後、
`show_pdf_page` をページ数ぶんループ呼び出しし、成功後にのみ
`new_doc.close()`（900行）する。ループ内で例外（不正な `src_pno` 等）が
発生すると `new_doc` は close されずリークする。同様に
`merged_doc = fitz.open(...)`（912行）も `self.doc.insert_pdf(merged_doc, ...)`
（913行）が失敗すると close されない。

`_do_merge` も `src = fitz.open(path)`（942行）の後、`insert_pdf`/
`set_toc` が失敗すると `src.close()`（953行）に到達しない。

いずれも外側の `except Exception as e: messagebox.showerror(...)` で
捕捉されるため UI はクラッシュしないが、`fitz.Document` はプロセス終了
まで未解放のまま残る。

**Fix:** 各 `fitz.open()` 呼び出しを `try/finally` で囲み、例外経路でも
close する（`file_ops.py` の一時ドキュメント保護パターンと同型に揃える）。

### WR-05: `_insert_blank_page` が失敗時に無意味な Undo エントリを残す

**File:** `pagefolio/page_ops.py:203-226`

**Issue:**
```python
self._save_undo("insert", insert_at=pno + 1)
try:
    page = self.doc[pno]
    w, h = page.rect.width, page.rect.height
    self.doc.new_page(pno + 1, width=w, height=h)
    self._undo_stack[-1]["data"][1] = 1  # 挿入件数を確定
    ...
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
```
`_save_undo("insert", ...)` は mutation 前に呼ばれており、`self.doc[pno]`
や `new_page` が例外を送出すると `data=[insert_at, 0]`（挿入件数 0）の
Undo エントリがそのままスタックに残る。同ファイル内の `_do_insert`
（805-830行）は同種の失敗時に
`self._dispose_state(self._undo_stack.pop())` で明示的にエントリを
取り除いているのに対し、`_insert_blank_page` にはこの後始末がなく、
doc に変化がないのに「元に戻す」履歴が1件増える（実害は軽微だが、
同一ファイル内での実装非対称であり UX 上の不整合）。

**Fix:** `_do_insert` と同型のガードを追加する。
```python
except Exception as e:
    if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
        self._dispose_state(self._undo_stack.pop())
    messagebox.showerror(self._t("err_title"), str(e))
```

### WR-06: `_add_watermark_text` / `_add_page_numbers` / `_add_watermark_image` のページ変更ループに例外保護がない

**File:** `pagefolio/page_ops.py:228-263`（`_add_watermark_text`）、`pagefolio/page_ops.py:325-342`（`_add_page_numbers`）、`pagefolio/page_ops.py:265-305`（`_add_watermark_image`）

**Issue:**
3メソッドとも `self._save_undo("page_edit", targets=targets)` の直後に
`for i in targets: page = self.doc[i]; page.insert_text(...)` /
`page.insert_image(...)` のループを `try/except` なしで実行している。
途中のページで `insert_text`/`insert_image` が例外を送出すると（不正な
フォント・座標・画像データ等）、一部ページのみ変更された状態で例外が
そのまま呼び出し元（Tk のボタンコールバック）まで伝播し、
`messagebox.showerror` によるユーザー向けエラー表示なしに Tk のデフォルト
例外ハンドラ（コンソールへのトレースバック出力のみ）に落ちる。
`page_edit` op の undo 自体は対称設計のため後から Ctrl+Z すれば復旧
できるが、実行直後にユーザーへ何が起きたか通知されない点は、同ファイル
内の他の変更系メソッド（`_crop_page`・`_do_insert`・`_duplicate_page` 等）
が一貫して `try/except` + `messagebox.showerror` で失敗を明示している
方針と食い違う。

**Fix:** ループを `try/except Exception as e: messagebox.showerror(...)`
で囲み、他のページ変更系メソッドと同じ失敗通知パターンに揃える。

## Info

### IN-01: `page_edit`/`insert`/`delete` 系の2段階復元ロジックはトレース済み・健全

**File:** `pagefolio/file_ops.py:523-936`

`_restore_state` の `page_edit`（596-681行）・`delete`（537-566行）・
`delete_redo`（567-595行）・`insert`（709-739行）・`insert_undo`
（740-768行）・`insert_redo`（769-804行）・`merge_resize`
（828-876行）・`merge_resize_undo`（877-917行）の各分岐について、
`_merge_pending_inverse` によるページインデックス算出（特に `insert`
分岐の `already` オフセット計算、713-739行）、Blob 所有権の移転
（pop 一回のみ・二重解放なし）、`_page_edit_inserted` マーカーが
`state` 側にのみ存在し `inverse` に漏れないことを行単位で確認した。
複数ラウンドの部分失敗（例: 5ページ挿入中に2回に分けて失敗するケース）を
手動トレースした結果でも、絶対ページインデックスの復元は一貫して正しい。
既存の `tests/test_pdf_ops.py`（`test_page_edit_partial_retry_then_redo_undo_roundtrip`
`test_page_edit_insert_failure_rolls_back_and_retry_preserves_neighbors`
`test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages` ほか、
2440-3110行台のテスト群）・`tests/test_undo_stress.py` の Blob 不変条件
検証（deque eviction・redo clear・消費時の解放で二重解放なし）と合わせ、
WR-01 以外の追加是正は不要と判断する。`lang.py` は ja/en とも 462 キーで
完全一致しており、今回追加された `err_*_content_at_risk` 系キーも両言語
に存在することを確認した。

---

_Reviewed: 2026-08-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
