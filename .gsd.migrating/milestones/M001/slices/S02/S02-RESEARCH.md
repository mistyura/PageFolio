# S02: バックグラウンドレンダリング — Research

**Date:** 2026-05-04

## Summary

現在のコードはプレビュー・サムネイル生成をすべてメインスレッド（Tkinter イベントループ）で同期実行している。`_show_preview()`（viewer.py:61-87）は `page.get_pixmap(matrix=fitz.Matrix(zoom*1.5, …))` をメインスレッドで呼び出すため、ページ切替・ズーム変更のたびに 50〜200 ms の UI フリーズが発生する。`_build_thumbnails()`（viewer.py:167-174）はファイルオープン時に全ページをループして `_get_thumb_photo(i)` → `get_pixmap()` を同期実行するため、100 ページの PDF では数秒規模のフリーズになる。

バックグラウンドレンダリングには **2 つの独立した手法** を使う。プレビューは `threading.Thread` + `root.after(0, cb)` パターン（重い高解像度レンダリングをワーカースレッドに移譲）、サムネイルは `root.after_idle()` 逐次スケジューリングパターン（1 枚ずつレンダリングしてイベントループに返す）。両手法を組み合わせることで UI 応答性を維持しつつ実装複雑度を最小に抑える。

PyMuPDF は **スレッド安全でない**（同一 `fitz.Document` オブジェクトへの並行アクセス不可）。ワーカースレッドは専用の `fitz.Document` インスタンスを開いて使用し終えたら閉じる必要がある。`ImageTk.PhotoImage` はメインスレッドでしか作成できないため、スレッド境界を越えるのは生のピクセルバイト列（`pix.samples`）のみとする。

## Recommendation

**プレビュー**: Generation counter + background thread パターンを採用する。  
**サムネイル**: `root.after_idle()` による逐次プログレッシブローディングを採用する（スレッドなし）。

この組み合わせが最適な理由:
- スレッドは高解像度プレビューのみに限定し、サムネイル（小さい）はメインスレッドのアイドル時間に分散処理 → 実装・デバッグのリスクを最小化
- Generation counter により急速なページ切替・ズーム操作で古いレンダリング結果を破棄できる
- PyMuPDF のスレッド非安全問題を「ワーカー専用 doc インスタンス」で回避

## Implementation Landscape

### Key Files

- `pagefolio/viewer.py` — メイン変更対象。`_show_preview()`・`_build_thumbnails()`・`_add_thumb()` を改修
- `pagefolio/app.py` — `__init__` に新規状態変数（`_preview_gen`, `_thumb_gen`）を追加
- `pagefolio/file_ops.py` — `_open_pdf_path()`, `_do_open_merged()`, `_restore_state()` で `_thumb_gen` をインクリメントする必要あり（ドキュメント入替時にサムネイル逐次レンダリングをキャンセルするため）

### 新規状態変数（`app.py __init__` に追加）

```python
self._preview_gen = 0   # プレビュー世代カウンター（stale render の破棄用）
self._thumb_gen = 0     # サムネイル逐次レンダリング世代（ドキュメント入替でキャンセル）
```

### プレビューバックグラウンドレンダリングパターン（`_show_preview` 改修）

```python
def _show_preview(self):
    self.preview_canvas.delete("all")
    # ... 空ドキュメント処理は既存のまま ...

    self._preview_gen += 1
    gen = self._preview_gen
    page_idx = self.current_page
    zoom = self.zoom
    filepath = self.filepath
    # unsaved doc (merged) の場合は bytes をメインスレッドで取得してから渡す
    doc_bytes = self.doc.tobytes() if not filepath else None

    # ローディングプレースホルダーを即時表示
    cw = self.preview_canvas.winfo_width() or 400
    ch = self.preview_canvas.winfo_height() or 600
    self.preview_canvas.create_text(cw//2, ch//2, text="...", fill=C["TEXT_SUB"], font=self._font(4))

    def worker():
        try:
            if filepath:
                tmp_doc = fitz.open(filepath)
            else:
                tmp_doc = fitz.open(stream=doc_bytes, filetype="pdf")
            page = tmp_doc[page_idx]
            mat = fitz.Matrix(zoom * 1.5, zoom * 1.5)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            samples = bytes(pix.samples)
            w, h = pix.width, pix.height
            tmp_doc.close()
        except Exception:
            return
        self.root.after(0, lambda: _apply(samples, w, h))

    def _apply(samples, w, h):
        if self._preview_gen != gen or not self.doc:
            return   # stale or doc closed
        img = Image.frombytes("RGB", [w, h], samples)
        photo = ImageTk.PhotoImage(img)
        self.preview_img_ref = photo
        # ... 既存の canvas 描画処理（shadow rect + image）...

    import threading
    threading.Thread(target=worker, daemon=True).start()
```

### サムネイル逐次プログレッシブローディングパターン（`_build_thumbnails` 改修）

```python
def _build_thumbnails(self):
    self._thumb_gen += 1
    gen = self._thumb_gen
    for w in self.thumb_inner.winfo_children():
        w.destroy()
    self.thumb_images.clear()
    if not self.doc:
        return
    n = len(self.doc)
    # プレースホルダーフレームを全ページ分即時作成（UI 構造を先に確立）
    placeholder_labels = []
    for i in range(n):
        frame, lbl = self._add_thumb_placeholder(i)
        placeholder_labels.append((frame, lbl))

    def render_next(i):
        if self._thumb_gen != gen or not self.doc:
            return
        if i >= len(self.doc):
            return
        photo = self._get_thumb_photo(i)
        frame, lbl = placeholder_labels[i]
        lbl.configure(image=photo)
        self.thumb_images.append(photo)
        self.root.after(0, lambda: render_next(i + 1))

    self.root.after_idle(lambda: render_next(0))
```

### `_add_thumb_placeholder(i)` 新規メソッド

既存 `_add_thumb(i)` をリファクタリングして分離:
- `_add_thumb_placeholder(i)`: frame・プレースホルダー Label・イベントバインディングを作成、`(frame, lbl)` を返す
- `_add_thumb(i)`: 後方互換で `_add_thumb_placeholder` + 即時画像セット（ポップアップ内など既存呼び出しがなければ削除可）

### Build Order

1. **T01**: `app.py __init__` に `_preview_gen = 0` と `_thumb_gen = 0` を追加
2. **T02**: `viewer.py` — `_show_preview()` をバックグラウンドスレッドパターンに改修
3. **T03**: `viewer.py` — `_build_thumbnails()` を `after_idle()` プログレッシブローディングに改修（`_add_thumb_placeholder` を分離）
4. **T04**: `file_ops.py` — `_open_pdf_path()`, `_do_open_merged()`, `_restore_state()` で `self._thumb_gen += 1` と `self._preview_gen += 1` を追加（ドキュメント入替時のキャンセル）
5. **T05**: `ruff check . && ruff format .` → `pytest`

T01 が T02–T04 の前提。T02 と T03 は独立。T04 は T02・T03 の後。

### Verification Approach

```bash
ruff check . && ruff format .
pytest   # 108件全 PASSED が必須
```

手動確認（GUI 起動）:
- 50+ ページ PDF を開く → サムネイルが1枚ずつプログレッシブに表示される
- ページを素早く切り替える → UI がフリーズしない（プレースホルダー表示後に非同期で更新）
- ズームを変更する → 旧レンダリング結果が表示されず、新しいものだけが表示される
- 別 PDF を続けて開く → 前の PDF のサムネイルレンダリングがキャンセルされる

## Constraints

- PyMuPDF は同一 `fitz.Document` オブジェクトへの並行アクセス非対応 — ワーカースレッドは必ず専用 `fitz.open()` インスタンスを使うこと
- `ImageTk.PhotoImage` はメインスレッドでのみ作成可能 — スレッド境界は `bytes(pix.samples)` で区切る
- `_zoom()` は `_show_preview()` を直接呼ぶ（viewer.py:105）— 改修後も同じ呼び出し形式を維持する
- Windows: `threading.Thread(daemon=True)` で確実にプロセス終了時にスレッドが終了するよう設定すること

## Common Pitfalls

- **`ImageTk.PhotoImage` の GC**: `self.preview_img_ref` と `self.thumb_images` への参照保持は既存コードで対応済み — 改修後も維持すること
- **`self.doc` が None または閉じられた状態でコールバックが発火**: `_apply()` 内で `if not self.doc:` をチェックすること
- **`doc_bytes = self.doc.tobytes()` の呼び出しタイミング**: メインスレッドで `tobytes()` を呼んでからスレッドを起動すること（スレッド内で `self.doc` にアクセスしない）
- **大規模 PDF のオープン時**: `_open_pdf_path()` の `_invalidate_thumb_cache()` の後に必ず `_thumb_gen += 1` すること — これがないと旧レンダリングシーケンスが新ドキュメントに対して走り続ける
- **`_rebuild_ui()` (app.py:346)**: UI 再構築時も `_preview_gen += 1` と `_thumb_gen += 1` が必要

## Open Risks

- `self.doc.tobytes()` による bytes コピーは大規模 PDF（50MB 超）でメモリ負荷になる。unsaved merged doc の場合のみ発生するケースだが、通常の filepath ありドキュメントではファイルから再オープンするため問題ない
- Tkinter の `after_idle()` + `after(0, ...)` の組み合わせでサムネイルレンダリングループが意図せず高頻度で実行される可能性 — 必要に応じて `after(1, ...)` に変更して負荷を調整する
