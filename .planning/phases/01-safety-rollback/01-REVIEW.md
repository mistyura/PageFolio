---
phase: 01-safety-rollback
reviewed: 2026-08-10T12:00:00Z
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
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase 01: Code Review Report（再レビュー・iteration 2）

**Reviewed:** 2026-08-10T12:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

前回レビュー（`01-REVIEW.md` iteration 1、`cb5344e`/`747ef9c`/`4e5dbc9`/`2768af7`
で fix 済み）の CR-01・WR-01・WR-02・WR-03 は、いずれも現在のソースで
再確認したところ **回帰なく正しく維持されている**：

- CR-01（多ページ復元の部分適用未対応）: `PartialRestoreError` /
  `_restore_partial_error` / `_handle_partial_restore` による保護が
  `delete`/`delete_redo`/`page_edit`/`insert_undo`/`insert_redo`/
  `merge_undo`/`merge_resize`/`merge_resize_undo` の全ループへ実装済み。
- WR-01（delete→delete_redo の無意味な Blob キャプチャ）: プレースホルダ
  （`None`）化済みで `_capture_page_blob` が呼ばれないことを確認。
- WR-02（OCR OFF ガードの既定値不一致）: `DEFAULT_OCR_PROVIDER` へ一元化
  済みで `app.py`/`ocr.py` 双方が同一定数を参照。
- WR-03（分割保存のパスワード保護喪失）: 警告確認ダイアログが実装済み。

今回のフォーカスである plan 01-06（`f9973ce`..`e41b7e3`、`_pending_inverse`
による逆デルタの部分失敗またぎ蓄積方式）を `pagefolio/file_ops.py` 全体に
わたって精査した。`_merge_pending_inverse` の pop による所有権移譲、
`merge_resize`/`merge_resize_undo` の identity 共有維持（`inv["data"] is
state["data"]`）、`_merged_page_deleted` フラグの hygiene（成功時に必ず
pop され次段へ漏れない）、`_restore_partial_error` への `pending_inverse`
引き渡し（全呼び出し箇所でマージ済みリストが渡っている）は、いずれも
設計どおり正しく機能していることを確認した。テスト（`TestUndoRedoRestoreFailure`
の一連の回帰テスト）も digest 一致・スタック内容の実データ検証を伴っており、
ページ数だけを見る vacuous なテストにはなっていない。

一方で、この精査の過程で **`page_edit` op の復元ループに新規の重大な
データ破損バグ（CR-02・今回新規発見）** を発見した。`delete_page` が
成功した直後に `insert_pdf` が失敗するという、このフェーズ自身が
前提としている「fitz 呼び出しは途中で失敗しうる」という脅威モデルの
中で、既存の partial-failure テストがカバーしていない具体的な１本の
分岐で、doc からは既に失われたページ内容を保持する Blob を誤って
解放してしまい、かつ再試行時に隣接ページを巻き添えで喪失しうる。
またその副産物として、複数の op の mutation ループで一時 `fitz.Document`
（`tmp`）が例外発生時に close されず残る小規模なリソースリーク
（WR-04）と、`insert`（base op）の delete ループが CR-01 と同型の
部分適用保護から意図的に除外されたまま残っている点（WR-05）を
警告として記録する。

## Critical Issues

### CR-02: `page_edit` の復元で `delete_page` 成功後に `insert_pdf` が失敗すると、直前にキャプチャした Blob が解放されページ内容が永久に失われる（さらに再試行で隣接ページも巻き添えで消える）

**File:** `pagefolio/file_ops.py:555-589`（`_restore_state` の
`op == "page_edit"` 分岐）

**Issue:**

```python
elif op == "page_edit":
    pending = []
    applied = 0
    try:
        for page_i, page_bytes in state["data"]:
            tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
            captured = self._capture_page_blob(page_i)
            try:
                self.doc.delete_page(page_i)
                self.doc.insert_pdf(tmp, start_at=page_i)
            except Exception:
                self._release_blob(captured)
                raise
            finally:
                tmp.close()
            pending.append((page_i, captured))
            applied += 1
    except Exception as e:
        ...
```

`page_edit` は唯一「1ページを `delete_page` してから `insert_pdf` で
差し替える」という **2段階 mutation** を行う op である（`delete`/
`delete_redo`/`insert_undo`/`insert_redo` はいずれも単発の
`insert_pdf` または `delete_page` のみで、この種の複合失敗は起こり
得ない）。

`captured = self._capture_page_blob(page_i)` は、まさにこれから
`delete_page` で消される **現在の（削除直前の）ページ内容**を捕捉する
もので、この内容は次段の逆デルタ（redo 方向）に使われる、doc から
消える瞬間の唯一のコピーである。

ここで `self.doc.delete_page(page_i)` が成功し、直後の
`self.doc.insert_pdf(tmp, start_at=page_i)` が失敗した場合を考える
（`tmp` は既に正常にオープンできているため、失敗要因は `self.doc` 側
のメモリ不足・内部破損・オブジェクトストリーム非互換等、CR-01 が
既に「起こりうる」と明示している fitz 呼び出し失敗の同じカテゴリ）。
このとき:

1. `self.doc` は既に `page_i` の元内容を失っている（`delete_page` 成功）。
2. 差し替え先の内容（`page_bytes`）も未挿入のまま（`insert_pdf` 失敗）。
3. `except Exception: self._release_blob(captured); raise` が、doc から
   消えた内容の唯一のコピーである `captured` を **解放（破棄）** する。

この時点で、そのページの内容（削除前の "現在" の状態）は doc にも
Blob にも存在しない、**恒久的に失われた状態**になる。

さらに悪いことに、この失敗は `except Exception as e:`（外側）で捕捉され
`_restore_partial_error(state, state["data"][applied:], e, ...)` により
「未適用分」として `page_i` を含む remaining state がスタックへ戻される
（`applied` はこの反復で加算される前に例外が出るため、このページは
「未適用」＝再試行対象のまま）。ユーザーが案内どおり再度 Undo/Redo を
実行すると:

- `tmp = fitz.open(page_bytes)` は変わらず成功する。
- しかし `captured2 = self._capture_page_blob(page_i)` は、**doc が既に
  シフトした状態**（`page_i` の位置には元々 `page_i+1` にあった別ページ
  の内容が来ている）に対して呼ばれるため、**無関係な隣接ページの内容を
  誤ってこの page_edit エントリの一部として捕捉**してしまう。
- 再試行の `delete_page(page_i)`/`insert_pdf(tmp)` が成功すると、doc の
  見た目上のページ数・`page_bytes` の内容自体は最終的に正しい位置へ
  収まるように見えるが、**実際には隣接していた別ページ（例: 元 P6）が
  丸ごと削除され消失している**。加えて `captured2`（誤って隣接ページの
  内容を保持した Blob）が次段の逆デルタ（redo 方向）に組み込まれるため、
  以降の Redo でこの巻き添えページの内容が誤った位置へ復元されるという
  二次被害も発生する。

これは CR-01 で確立された「fitz 呼び出しは外的要因で途中失敗しうる」
という脅威モデルの範囲内で発生しうる、**ドキュメントの内容が静かに
永久欠損する**（かつ隣接ページまで巻き添えにする）シナリオであり、
Critical（データ損失リスク）に分類する。

既存の回帰テスト `test_page_edit_partial_retry_then_redo_undo_roundtrip`
（`tests/test_pdf_ops.py:2366`）は `_blob_bytes` の失敗（`tmp = fitz.open(...)`
より前・`delete_page` 呼び出しより前のタイミング）のみを模しており、
`delete_page` 成功後に `insert_pdf` が失敗するこのシナリオはカバーして
いない（`captured` が解放される分岐そのものに到達しない）。

**Fix:**

`delete_page` が成功した後に `insert_pdf` が失敗した場合、`captured`
は「doc から失われた内容の最後のコピー」であり解放してはならない。
最低限、以下のいずれかの対応が必要:

1. **ロールバックを試みる**: `insert_pdf(tmp, ...)` が失敗した場合、
   `captured` を使って `insert_pdf(fitz.open(stream=self._blob_bytes(captured)),
   start_at=page_i)` で即座に元の内容を復元しようと試みる。ロールバック
   自体が成功すれば doc は mutation 前の状態に戻るため `captured` を
   通常どおり解放してよい。ロールバックも失敗した場合は `captured` を
   **解放せず**、`remaining_state` の一部として保持し、ユーザーへ
   「このページの内容が失われた可能性がある」ことを明示するエラー文言
   を出す。

   ```python
   try:
       self.doc.delete_page(page_i)
       try:
           self.doc.insert_pdf(tmp, start_at=page_i)
       except Exception:
           # 差し替え失敗: 削除前の内容を captured から復元しロールバック
           rb = fitz.open(stream=self._blob_bytes(captured), filetype="pdf")
           try:
               self.doc.insert_pdf(rb, start_at=page_i)
           finally:
               rb.close()
           raise
   except Exception:
       self._release_blob(captured)  # ロールバック成功時のみ安全に解放可能
       raise
   ```

2. 最低限の対応として、`delete_page` 成功後の `insert_pdf` 失敗だけは
   `captured` を解放せず、専用のエラー経路（例えば「このページの内容が
   失われた可能性があります。ファイルを閉じずに手動で確認してください」
   という強い警告）へ分岐させる。

いずれの対応でも、page_edit の partial-failure テストに
「`insert_pdf` 側（`delete_page` 成功後）が失敗するケース」を追加し、
(a) 内容が失われないこと、(b) 隣接ページが巻き添えにならないことを
digest 一致で検証すること。

## Warnings

### WR-04: `page_edit` 以外の複数ページ復元ループで、mutation 失敗時に一時 `fitz.Document`（`tmp`）が `close()` されず残る

**File:** `pagefolio/file_ops.py:500-525`（`delete`）、`617-641`
（`insert_undo`）、`682-696`（`merge_undo`）、`697-741`（`merge_resize`）、
`742-778`（`merge_resize_undo`）

**Issue:**
`page_edit` の分岐（`file_ops.py:568-579`）は `tmp = fitz.open(...)` を
`try/finally: tmp.close()` で保護しており、`insert_pdf` が失敗しても
`tmp` は確実に close される。しかし他の op（`delete`/`insert_undo`/
`merge_undo`/`merge_resize` フェーズ2/`merge_resize_undo`）は同じ
パターンで `tmp = fitz.open(...)` → `self.doc.insert_pdf(tmp, ...)` →
`tmp.close()` を実行しているが、`finally` で保護されていないため、
`insert_pdf` が例外を送出すると `tmp.close()` に到達せず、その
`fitz.Document` オブジェクトが未クローズのまま例外ハンドラへ抜ける
（例: `file_ops.py:512-517`）。

```python
for page_i, page_bytes in state["data"]:
    tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
    self.doc.insert_pdf(tmp, start_at=page_i)
    tmp.close()
    pending.append((page_i, None))
    applied += 1
```

これは `UndoBlobStore` が管理する Blob（tempfile/メモリ）のリークでは
なく、あくまで一時的な `fitz.Document` ラッパーオブジェクト（ストリーム
バッキング）の未解放であり、CR-01/CR-02 のような即座のデータ破損には
つながらない。ただし、この種の例外パスは PartialRestoreError の設計上
「異常系だが十分に起こりうる」前提であるため、繰り返し失敗が続く環境
（例: 継続的な Blob ロード障害下でユーザーが Undo/Redo を連打する）では
未クローズの `fitz.Document` が積み重なる可能性がある。

**Fix:** `page_edit` と同様に `finally: tmp.close()` で保護する。例:

```python
for page_i, page_bytes in state["data"]:
    tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
    try:
        self.doc.insert_pdf(tmp, start_at=page_i)
    finally:
        tmp.close()
    pending.append((page_i, None))
    applied += 1
```
同型の修正を `insert_undo`・`merge_undo`・`merge_resize`（元ページ再挿入
ループ）・`merge_resize_undo`（`merged_bytes` 挿入）の各箇所へ適用する。

### WR-05: `insert`（base op）の削除ループは CR-01 の部分適用保護から意図的に除外されたままであり、`page_edit` と同型の巻き添え喪失リスクが残る

**File:** `pagefolio/file_ops.py:613-616`（`_restore_state` の
`op == "insert"` 分岐）

**Issue:**
`_apply_inverse`/`_restore_state` のコメント（`file_ops.py:436-437`、
`613`）が明示しているとおり、`insert` op（ユーザーが複数ページを挿入した
操作そのものの undo 方向 = 挿入ページの削除）は今回の V190-UNDO-01 の
対象から意図的に除外されている:

```python
elif op == "insert":
    insert_at, num = state["data"]
    for _ in range(num):
        self.doc.delete_page(insert_at)
```

`num` が複数（例えば複数ページの PDF をまとめて挿入した場合）のとき、
このループが `k` 回目（`k < num`）の `delete_page` で失敗すると、例外は
`_undo`/`_redo` の **通常の**（`PartialRestoreError` ではない）
`except Exception as e:` 節で捕捉される。この節は「doc は無変更だった」
という前提で **元の（`num` 件ぶんの）state をそのまま**スタックへ
戻す（`file_ops.py:299`/`331` の `self._push_evicting(..., state)`）。

しかし実際には doc は既に `k` ページ分削除済みであり、`insert_at` の
位置には別の（本来削除対象ではない）コンテンツが来ている。ユーザーが
案内どおり再度 Undo/Redo を実行すると、`for _ in range(num): delete_page(insert_at)`
が **`num` 回**（`k` 回ではなく）再実行され、既に一部が削除済みの位置
から追加で `num - k` 回削除が続き、**本来挿入されていなかった既存
ページまで削除してしまう**（過剰削除・データ損失）。

これは CR-01 が「delete/page_edit/insert_undo/insert_redo/merge_undo/
merge_resize/merge_resize_undo/delete_redo」の8 op について対処した
のと同じクラスのバグが、`insert`（base op）にはコメントで明示的に
「対象外」とされたまま残存していることを示す。トリガー条件はやや稀
（`delete_page` が単体で mid-loop 失敗する必要があり、ここでは
`_blob_bytes` 経由のロード失敗のような外部起因の失敗パターンが
適用できない）だが、CR-01/CR-02 と同一の脅威モデル（fitz 呼び出しの
mid-loop 失敗）の下では発生しうる。

**Fix:** `insert` の削除ループも他の8 op と同型で「実際に削除できた
件数」を追跡し、失敗時は `PartialRestoreError` で「残り `num - k` 件」
を表す remaining state を返すようにする。この場合 Blob は関与しない
ため、追跡自体は単純（`deleted_count` のみでよい）。

```python
elif op == "insert":
    insert_at, num = state["data"]
    deleted = 0
    try:
        for _ in range(num):
            self.doc.delete_page(insert_at)
            deleted += 1
    except Exception as e:
        remaining = [insert_at, num - deleted]
        self._restore_partial_error(state, remaining, e)
```
（`insert` の `inverse`＝`insert_undo` は挿入ページの再構築のため
`_apply_inverse` 側の扱いも合わせて確認すること。）

---

_Reviewed: 2026-08-10T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
