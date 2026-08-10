---
phase: 01-safety-rollback
reviewed: 2026-08-10T10:04:43Z
depth: standard
files_reviewed: 14
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
findings:
  critical: 1
  warning: 3
  info: 0
  total: 4
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-10T10:04:43Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

対象は `01-safety-rollback`（v1.9.0）の5プラン: (01-01) 保存経路の暗号化維持、
(01-02) OCR OFF ガードの全経路配線、(01-03) LLM設定ダイアログの外部プロンプト
ファイル書き込みの一本化、(01-04) 挿入ロールバック・複製Undo後置化・
Undo/Redo復元失敗時のstate保全、(01-05) duplicate/merge/merge_resize の
4手往復回帰テスト。

`git diff 5e33fb9..HEAD` で実差分を確認し、変更箇所を中心にレビューした。

- **暗号化維持（01-01）**: `_save_as` / `_save_file`（incremental・フォール
  バック双方）/ `_save_compressed`（上書き・別名保存双方）/ `_overwrite_current_file`
  の全経路で `encryption=fitz.PDF_ENCRYPT_KEEP` が既定化されており、
  `derive_pdf_has_password` による論理導出も明示指定（AES_256/NONE）を
  壊さない実装になっている。回帰テスト（`tests/test_password.py`）も
  実ファイルの `needs_pass`/`authenticate` を検証しており妥当。この点は
  クリーン。
- **OCR OFF ガード（01-02）**: `build_provider` の `"off"` 拒否・プラグイン
  フォールバックより前段でのブロック・`_start_ocr`/バッチOCR/OCRDialog内
  再生成/実行開始/メニュー入口の全経路にガードが配線されており、実行時
  スナップショット（`s = dict(self.app.settings)` 等）から都度 `ocr_provider`
  を読むため stale な `self.provider` に依存しない設計になっている。この点も
  クリーン。
- **プロンプトファイル書き込み一本化（01-03）**: `sections.py` からの書き込みが
  撤去され `dialog.py:_apply` へ一本化されている。テストも新契約へ追随済み。
- **ロールバック・Undo後置化（01-04）**: `_do_insert` の巻き戻し・
  `_duplicate_page` の Undo 後置確定は概ね正しく実装されているが、
  `_undo`/`_redo` の復元失敗保護（新設）に、複数ページにまたがる復元処理が
  **途中まで成功してから失敗した場合**の部分適用を考慮しない欠陥がある
  （CR-01・下記）。
- **4手往復テスト（01-05）**: `_page_digest`（テキスト内容ハッシュ相当）で
  ページ数だけでなく内容一致・順序一致まで検証しており、D-17 のような
  非対称復元バグを捕捉できるテスト品質になっている。

## Critical Issues

### CR-01: Undo/Redo 復元失敗保護が「多ページ復元の部分適用」を考慮していない

**File:** `pagefolio/file_ops.py:191-234`（`_undo`/`_redo` の新設 try/except）
および `pagefolio/file_ops.py:385-478`（`_restore_state` の複数ページ
ループ: `delete` / `page_edit` / `insert_undo` / `insert_redo` /
`merge_undo` / `merge_resize` / `merge_resize_undo` / `delete_redo`）

**Issue:**
今回新設された `_undo`/`_redo` の保護は次の前提に立っている:

> 「復元失敗時は pop した state を `_push_evicting` 経由でスタックへ戻す。
> `_dispose_state` は呼ばない — state はまだ消費されていないものとして
> 温存し、次回の undo で再試行できるようにする」（file_ops.py:199-204 の
> コメント）

しかしこの前提は **`_restore_state` の適用が atomic（全成功 or 無変更）で
あることを暗黙に要求している**のに対し、複数ページを順次処理するop
（`delete`/`page_edit`/`insert_undo`/`insert_redo`/`merge_undo`/
`merge_resize`/`merge_resize_undo`/`delete_redo`）の実装はforループで
1ページずつ `self.doc.insert_pdf(...)` / `self.doc.delete_page(...)` を
呼んでおり、途中の1件（例: 2ページ目のBlobが破損していて
`fitz.open(stream=...)` が例外）で失敗した場合、**それより前のページは
既にdocへ適用済み**のまま例外が送出される。

この時 `_undo`/`_redo` の except節は「doc は無変更だった」という前提で
同一 `state`（元のN件ぶんのデータ）をそのままスタックへ戻し、
ユーザーには「次回 Ctrl+Z で再試行できます」という趣旨のブロッキング
エラーのみを表示する。しかし実際には doc は既に一部ページが
挿入/削除された状態であり、`current_page`/`selected_pages`の更新も
行われないまま（`_restore_state` 末尾の更新処理に到達しない）中断する。

ユーザーがエラーダイアログの案内通りに再度 Undo を実行すると、
`_restore_state` は同じ `state["data"]`（N件フル分）を再度先頭から
適用しようとし、**既に成功していたページに対して再度 insert/delete が
行われ、ページの重複挿入や意図しない追加削除**が発生し得る
（`_do_insert` の巻き戻し処理が `removed`/`residual` を追跡して
部分適用に対応しているのとは対照的に、`_restore_state` 側にはこの
追跡がない）。

`page_ops.py` の `_do_insert`（本フェーズの01-04で改修）は同種の問題を
正しく扱っている（挿入済み件数を`total`で追跡し、巻き戻しが部分的にしか
成功しなかった場合は実際の残存数を state へ反映する）。同じ設計思想が
`_restore_state` の多ページループには適用されていない。

**再現条件の例（delete の undo）**: `_capture_page_blob` で取得した
Blob のうち2件目以降がディスク上のtempfile退避（`FileBlob`、64KiB以上）
であり、外部要因（アンチウイルスの隔離・一時ディレクトリのクリーンアップ・
ディスク容量枯渇）で該当tempfileが読めなくなった場合、
`self._blob_bytes(data)`→`data.load()` が例外を送出し、既に1ページ目は
`insert_pdf` 済みの状態でループが中断する。

**Fix:**
`_restore_state` の複数ページ処理を、`_do_insert` と同様に「実際に何件
適用できたか」を追跡し、部分適用が発生した場合は元の `state` をそのまま
戻すのではなく、**未適用分のみを表す state** を作り直してスタックへ
戻すこと。最低限、以下のいずれかの対応が必要:

```python
# 例: delete の undo（insert 系）を部分適用対応にする場合のイメージ
elif op == "delete":
    applied = []
    try:
        for page_i, page_bytes in state["data"]:
            tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
            self.doc.insert_pdf(tmp, start_at=page_i)
            tmp.close()
            applied.append((page_i, page_bytes))
    except Exception:
        remaining = [item for item in state["data"] if item not in applied]
        # 呼び出し元（_undo）が state["data"] を remaining に差し替えて
        # push_evicting できるよう、専用の例外や戻り値で伝える
        raise PartialRestoreError(remaining) from None
```

もしくは、複数ページ処理の前に「全Blobをまずロードしきってから
（`_blob_bytes` を先に全件呼んでバリデーションしてから）doc への
適用ループに入る」ことで、少なくとも「Blobロード失敗」由来の例外は
mutation前に確実に検出できるようにし、mutation自体（`insert_pdf`/
`delete_page`）は極力アトミックな塊として扱う設計にする。

いずれの対応も難しい場合は、最低限「復元処理の途中で例外が発生した
場合、doc が部分的に変更されている可能性がある」旨をエラーダイアログ
文言に含め、Undo/Redoスタックをその時点でクリアして安全側に倒す
（黙って再試行を促さない）フォールバックも検討に値する。

## Warnings

### WR-01: `_apply_inverse` の `delete`→`delete_redo` 変換が意味のない（誤った内容の）Blob をキャプチャしている

**File:** `pagefolio/file_ops.py:256-264`（`_apply_inverse`、`op == "delete"` 分岐）

**Issue:**
`_restore_state` は `inverse = self._apply_inverse(state)` を **doc への
mutation より前**に呼ぶ。`op == "delete"` の場合、`_apply_inverse` は

```python
inv["op"] = "delete_redo"
inv["data"] = [
    (page_i, self._capture_page_blob(page_i)) for page_i, _ in state["data"]
]
```

を実行するが、この時点では `page_i` の位置にはまだ削除されたページが
再挿入されておらず（mutationはこの後の `elif op == "delete":` ブロックで
行われる）、`_capture_page_blob(page_i)` は **無関係な別ページの内容**を
キャプチャしてしまう。コメントには「現在（挿入済み）のページ bytes を
キャプチャして保存」とあるが、実際には未挿入の時点で呼ばれており事実と
異なる。

実害としては、この誤ったBlobは `delete_redo` state の `data` フィールドに
格納されるが、消費側（`_restore_state` の `op == "delete_redo"` 分岐、
および次段の `_apply_inverse` の `op == "delete_redo"` 分岐）は
いずれも `for page_i, _ in state["data"]` という形で **Blobを常に
アンダースコアで捨てて `page_i` のみ使用**しているため、誤ったBlobが
実際にPDFへ書き戻されることはない（次に redo → undo と辿った時点で
`_apply_inverse` が改めて正しいタイミングで再キャプチャする）。

現状は無害だが、以下の理由でコード品質上の問題として指摘する:
- 不要な `_capture_page_blob` 呼び出し（`UndoBlobStore` へのメモリ/
  一時ファイル確保を伴う）が毎回発生し、後で `_dispose_state` により
  解放されるまでリソースを無駄に握る。
- コメントが実態と矛盾しており、将来このフィールドを「意味のある内容」
  として消費するコードが追加された場合、静かにデータ破損する地雷になる。

**Fix:** `delete`→`delete_redo` の変換では、`page_i` のリストだけを
保持し、`_capture_page_blob` を呼ばない（本来 `delete_redo` の
restore・further-inverse どちらも `page_i` しか使っていないため、
`data` を `[(page_i, None) for page_i, _ in state["data"]]` のように
プレースホルダ化するか、専用の軽量フィールドに置き換える）。

```python
elif op == "delete":
    inv["op"] = "delete_redo"
    # delete_redo の restore/次段 inverse はどちらも page_i のみを使い
    # blob は参照しない。挿入前のこの時点では正しい内容を捕捉できない
    # ため、無駄な _capture_page_blob 呼び出しをしない。
    inv["data"] = [(page_i, None) for page_i, _ in state["data"]]
```

（`_dispose_state` 側の `delete_redo` 分岐も `blob` が `None` の場合を
許容するよう `_release` のガードで対応可能）

### WR-02: OCR OFF ガードの既定値が `build_provider` と UI 側で不一致

**File:** `pagefolio/app.py:344-378`（`_update_ocr_buttons_state` /
`_update_batch_menu_state`、後者は本フェーズ新設）と
`pagefolio/ocr.py:435`（`build_provider`）

**Issue:**
`_update_batch_menu_state`（本フェーズ新設）・`_update_ocr_buttons_state`
（既存）はいずれも

```python
is_ocr_on = self.settings.get("ocr_provider", "off") != "off"
```

のように `"ocr_provider"` キー欠落時のデフォルトを `"off"` としている。
一方 `build_provider` は

```python
name = settings.get("ocr_provider", "lmstudio")
```

とデフォルトを `"lmstudio"` にしている。通常経路では `_load_settings()`
が常に `"ocr_provider": "off"` を補完するため実運用では顕在化しないが、
本フェーズが「OCR OFF を構造的に拒否する」ことを目的にしている以上、
UI側とプロバイダ生成側でデフォルト値の解釈が食い違っているのは
安全設計として脆い。設定辞書が何らかの理由（プラグイン供給の設定・
テスト・将来の設定移行処理のバグ）で `ocr_provider` キーを欠いた場合、
メニュー/ボタンは disabled 表示になる一方で `build_provider` は
LM Studio プロバイダを普通に生成してしまい、「見た目はOFFなのに
実行経路は動く」という食い違いが起こり得る。

**Fix:** 既定値を一箇所（例えば `DEFAULT_OCR_PROVIDER = "off"` のような
定数）に集約し、UI側・`build_provider`側の双方で同じ既定値を参照する
ようにする。

### WR-03: 分割保存（`_split_by_range`/`_split_each_page`）がパスワード保護を引き継がない

**File:** `pagefolio/page_ops.py:1008-1043`（`_split_by_range`）、
`pagefolio/page_ops.py:1067-1082`（`_split_each_page`）※いずれも
本フェーズの差分外（未変更コード）

**Issue:**
01-01 は「上書き保存・別名保存・縮小保存・上書きフォールバック」の
4経路について `encryption=fitz.PDF_ENCRYPT_KEEP` を徹底し、パスワード
保護PDFが平文で書き戻されないことを保証した。一方、`_split_by_range`/
`_split_each_page` は新規に `fitz.open()` した空ドキュメントへ
`insert_pdf` でページを複製し、

```python
out.save(out_path, **save_kwargs)  # save_kwargs に encryption 指定なし
```

として保存している。`out` は新規に開いた（暗号化情報を持たない）
ドキュメントであり、`encryption` 未指定時の既定 `PDF_ENCRYPT_KEEP` は
「`out` 自身の（＝無暗号の）状態を維持する」ことを意味するため、元の
PDFがパスワード保護されていても、分割後の個別PDFは**無条件で平文**に
なる。ユーザーがパスワードを入力して開いた機密文書を分割保存すると、
保護なしのファイルが静かに生成される。

本フェーズの差分には含まれないため BLOCKER ではなく WARNING とするが、
「保存経路の暗号化維持」という本フェーズのテーマに直接関係する残存
ギャップであり、後続フェーズでの対応候補として明記しておく。

**Fix:** `self.pdf_has_password` が真の場合、分割前に元ドキュメントの
パスワードを再入力させるか、`_suggest_save_name` と同様の確認ダイアログ
を出した上で `save_kwargs["encryption"] = fitz.PDF_ENCRYPT_AES_256` +
`owner_pw`/`user_pw` を設定して保存する（もしくは少なくとも「分割後の
ファイルはパスワード保護されません」という警告を明示する）。

---

_Reviewed: 2026-08-10T10:04:43Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
