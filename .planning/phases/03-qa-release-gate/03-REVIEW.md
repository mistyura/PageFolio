---
phase: 03-qa-release-gate
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - pagefolio/file_ops.py
  - tests/test_toast.py
  - pagefolio/constants.py
  - CLAUDE.md
  - README.md
  - 開発履歴.md
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 3 の実質的な変更は `pagefolio/file_ops.py` の保存3経路（上書き保存/名前を付けて保存/縮小保存）を「確認・パス選択層」と「確定 `path` を引数に取る実保存層（`_do_save_file` / `_do_save_as` / `_do_save_compressed`）」へ分離し、失敗トーストの再試行 (`retry_cb`) を `functools.partial` で確定パスへ束縛するリファクタリングです。目的（再試行時に確認ダイアログ・保存先ピッカーを再表示しない）自体は `tests/test_toast.py` の新規テストで手厚く検証されていますが、**束縛されるのは `path`（文字列）のみで `self.doc`（Document オブジェクト）は束縛されていない**ため、トースト表示中にユーザーが「別ファイルを開く」操作を行うと、再試行ボタンが「無関係な新しいドキュメントの内容を、失敗した旧ファイルのパスへ確認なしで上書きする」という致命的なデータ破損経路になり得ます。これは review_focus で名指しされていた懸念（確定パス束縛の安全性）そのものであり、`_open_pdf_path` / `_do_open_merged` / `_close_file` のいずれもアクティブなトーストを dismiss しないことで発生します。

`self.doc` が falsy になった後の再試行（ファイルを閉じた場合）については `_do_save_file` / `_do_save_as` / `_do_save_compressed` すべてで早期 return が実装されており、例外は漏れません（この点は安全）。暗号化維持（AES-256 の `encryption=PDF_ENCRYPT_KEEP`）も3経路すべての再試行パスで一貫して保持されており、劣化は見られません。裸の `except:` や `# type: ignore` の無断使用、Undo スタックへの直接 `append`/`clear` といったプロジェクト規約違反は今回の差分には見当たりません。

ドキュメント4ファイル（`CLAUDE.md`/`README.md`/`開発履歴.md`/`constants.py`）のバージョン表記は `APP_VERSION = v1.9.0` で三者一致しており問題ありません。

## Critical Issues

### CR-01: 別ファイルを開いた後に保存失敗トーストを再試行すると、無関係なドキュメントの内容で元ファイルを無確認上書きしてしまう

**File:** `pagefolio/file_ops.py:1135-1164`（`_do_save_file`）, `1186-1210`（`_do_save_as`）, `1248-1277`（`_do_save_compressed`）, `1046-1084`（`_open_pdf_path`）, `1005-1044`（`_do_open_merged`）, `1224-1246`（`_close_file`）

**Issue:**

`_do_save_file` / `_do_save_as` / `_do_save_compressed` の `retry_cb` は `functools.partial(self._do_save_XXX, path)` で「確定パス」のみを束縛しています。しかし関数本体は `self.doc` を実行時に**遅延参照**しており（例: `_do_save_file` 1148行目 `self.doc.save(path, incremental=True, ...)`）、`self.doc` 自体は束縛されていません。

一方、`_open_pdf_path`（1046-1084行）・`_do_open_merged`（1005-1044行）・`_close_file`（1224-1246行）はいずれも `self.doc` を新しいドキュメント（または `None`）へ差し替える際に、既存の `self._toast` を一切 dismiss しません（`grep` で確認した限り、保存成功時の `dismiss("save_file")` 等のみが呼ばれ、ファイルを開く/閉じる経路に `_toast` への参照は皆無）。

その結果、以下の手順で **元ファイルの内容が無関係な別ドキュメントの内容で無確認上書きされます**:

1. ファイル A（`pathA`）を開いて保存 → 一時的な要因（権限・排他ロック等）で失敗し、`retry_cb = functools.partial(self._do_save_file, pathA)` を持つトーストが表示される。
2. トーストを閉じずに、別ファイル B を開く（`_open_pdf_path`）。`self.doc` は B のドキュメントに、`self.filepath` は `pathB` に差し替わるが、**トーストは A 用の retry_cb を保持したまま画面に残り続ける**。
3. ユーザーがトーストの「再試行」ボタンを押す（「今開いているファイルの保存を再試行する」つもりで押す可能性が高い、あるいは単に消し忘れて後から押す）。
4. `_do_save_file(pathA)` が実行され、`self.doc`（= 今は B のドキュメント）の内容が `incremental=True` で失敗後 `_overwrite_current_file(pathA)` にフォールバックし、`pathA` のファイルが **B の内容で完全に上書き**される。確認ダイアログは一切表示されない（これがこの Phase の設計目的そのもの＝再試行時は確認をスキップする）。

`_do_save_as`・`_do_save_compressed` も同型の危険性を持ちます（`_do_save_compressed` は `_is_current_file(path)` を再試行時に再評価しますが、これも `self.filepath`/`self.doc.name` を実行時参照するため、判定結果に関わらず最終的に `self.doc`（= 別ドキュメント）の内容が束縛済み `path` へ書き込まれます）。

`tests/test_toast.py` の `test_save_file_retry_writes_to_bound_path_not_current_filepath`（481-508行）はこの領域を部分的にしかカバーしていません。検証しているのは「`app.filepath` を差し替えても書き込み先パスは変わらない」ことだけで、**`app.doc` そのものを別ドキュメントに差し替えるケースは一切テストされていません**。「意図通りの安全性」（束縛パス以外には書き込まない）は確認されていますが、「束縛パスに書き込まれる中身が正しいドキュメントであるか」は未検証のまま出荷されています。

これは CLAUDE.md の Core Value（「大きな PDF でも Undo/Redo が正しく・速く動作し」）およびプロジェクトの安全設計原則（黒塗り等の破壊的操作にすら明示確認を要求する設計思想）と真っ向から矛盾する、サイレントなデータ破損経路です。

**Fix:**

最小修正案: ファイルを開く/閉じる経路で、保存系トーストを強制的に dismiss する（`ToastManager` は単一トーストしか同時表示しない設計＝D-07 のため、アクティブなカテゴリを問わず閉じてよい）。

```python
# pagefolio/toast.py に追加
class ToastManager:
    ...
    def dismiss_all(self):
        """アクティブなトーストをカテゴリを問わず破棄する（ファイル切替時の安全装置）。"""
        self._destroy_frame()
        self._active_category = None
```

```python
# pagefolio/file_ops.py: _open_pdf_path / _do_open_merged / _close_file の
# self.doc 差し替え直前（または直後）に追加
if getattr(self, "_toast", None) is not None:
    self._toast.dismiss_all()
```

より堅牢な代替/追加策として、`retry_cb` の束縛時に `self.doc` の identity も束縛し、実行時に一致しなければ書き込まずに「ドキュメントが変更されたため再試行できません」という新規トーストへ差し替える方法も検討してください:

```python
def _do_save_file(self, path, bound_doc):
    if not self.doc or self.doc is not bound_doc:
        self._set_status(self._t("info_open_first"))
        return
    ...

# 呼び出し側
functools.partial(self._do_save_file, path, self.doc)
```

## Warnings

### WR-01: `app.doc` 差し替えシナリオがテストで一切カバーされていない

**File:** `tests/test_toast.py:481-508`（`test_save_file_retry_writes_to_bound_path_not_current_filepath`）

**Issue:** このテストは `app.filepath` の差し替えのみを検証しており、`app.doc` を別インスタンスへ差し替えるケース（＝実際に「別ファイルを開く」操作に相当するケース）を検証していません。この観点の欠如が CR-01 の見落としに直結しています。

**Fix:** 以下のようなケースを追加してください（少なくとも `_save_file` / `_save_as` / `_save_compressed` の3系統分）。

```python
def test_save_file_retry_does_not_write_unrelated_doc_after_doc_swapped(
    self, monkeypatch
):
    """retry_cb 取得後に app.doc が別ドキュメントへ差し替わった場合、
    retry_cb は無関係なドキュメントを束縛パスへ書き込んではならない。
    """
    monkeypatch.setattr(fo.messagebox, "askyesno", lambda *a, **k: True)
    toast = _RecordingToast()
    doc_a = _RaisingThenOkDoc()
    app = _FakeFileOpsApp(
        doc=doc_a, toast=toast, filepath="a.pdf",
        overwrite_error=OSError("overwrite失敗（一時要因）"),
    )
    app._save_file()  # a.pdf の保存失敗 → トースト
    _, _, retry_cb = toast.shown[0]

    # 「別ファイルを開く」操作を模す: doc も filepath も差し替わる
    doc_b = _RaisingThenOkDoc()
    app.doc = doc_b
    app.filepath = "b.pdf"
    app._overwrite_error = None

    retry_cb()

    # doc_b の内容が a.pdf へ書き込まれてはならない
    assert "a.pdf" not in doc_b.save_paths
```

現状の実装ではこのテストは失敗するはずです（CR-01 の再現テストとして使えます）。

### WR-02: ドキュメントを閉じた後もトーストが永久に残留する

**File:** `pagefolio/file_ops.py:1143-1145`（`_do_save_file`）, `1256-1258`（`_do_save_compressed`）, `1192-1194`（`_do_save_as`）

**Issue:** `self.doc` が falsy な場合の早期 return パスでは、`self._set_status(self._t("info_open_first"))` を呼ぶのみで、表示中のトースト（もしあれば）を dismiss していません。ファイルを閉じた後は再試行が恒久的に no-op になるにもかかわらず、ユーザーには「まだ再試行できる」ように見える壊れたトーストが画面に残り続けます。

**Fix:** 早期 return の直前でトーストを dismiss してください。

```python
if not self.doc:
    if getattr(self, "_toast", None) is not None:
        self._toast.dismiss("save_file")  # カテゴリ名は各関数に合わせる
    self._set_status(self._t("info_open_first"))
    return
```

### WR-03: docstring が実態以上の安全性を主張しており誤解を招く

**File:** `pagefolio/file_ops.py:1138-1142`（`_do_save_file`）, `1189-1191`（`_do_save_as`）, `1251-1255`（`_do_save_compressed`）

**Issue:** 各関数の docstring は「トースト表示中に別ファイルを開く・ファイルを閉じるなどアプリ状態が変化しても、確定時に束縛された `path` へのみ書き込む（D-11）」と記載していますが、これは「書き込み**先**が変わらない」ことしか保証しておらず、「書き込む**内容**（`self.doc`）が正しいドキュメントである」ことは保証していません。この文言が実装者・レビュアーに誤った安全性の印象を与え、CR-01 の見落としを助長した可能性があります。

**Fix:** docstring を実態に合わせて修正するか（例: 「`path` は束縛されるが `self.doc` は都度最新を参照するため、ドキュメントが差し替わっている場合は無関係な内容が書き込まれる」と明記）、CR-01 の修正と合わせて実際に `self.doc` の同一性も保証するよう実装を変更してください。

## Info

### IN-01: トーストカテゴリ文字列のマジックストリング重複

**File:** `pagefolio/file_ops.py:1156-1163`, `1202-1209`, `1269-1276`

**Issue:** `"save_file"` / `"save_as"` / `"save_compressed"` の各カテゴリ文字列が `dismiss()` 呼び出しと `_show_error_or_toast()` 呼び出しの両方にハードコードされて重複しています（各関数内で2回ずつ）。将来的なリネーム時の取りこぼしリスクがあります。

**Fix:** 各実保存層の先頭でカテゴリ名をローカル変数化する、またはモジュールレベルの定数（例: `TOAST_CATEGORY_SAVE_FILE = "save_file"`）に括り出すことを検討してください。優先度は低く、必須ではありません。

---

_Reviewed: 2026-08-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
