---
estimated_steps: 37
estimated_files: 1
skills_used: []
---

# T02: _show_preview() をバックグラウンドスレッドパターンに改修

viewer.py の _show_preview() をバックグラウンドスレッドパターンに書き換える。PyMuPDF の page.get_pixmap() はメインスレッドで実行すると 50〜200ms ブロックするため、これを daemon=True のワーカースレッドに移譲し、_preview_gen による世代管理で stale 結果を破棄する。

重要な制約（必読）:
- PyMuPDF は同一 fitz.Document への並行アクセス非対応。ワーカーは必ず専用の fitz.open() インスタンスを使い、使い終わったら必ず close() する（例外時も finally で閉じる）
- ImageTk.PhotoImage はメインスレッドでのみ作成可能。スレッド境界を越えるのは bytes(pix.samples) のみ
- self.filepath がある場合: ワーカーで fitz.open(filepath) して専用インスタンスを開く
- self.filepath が None（未保存結合 doc）の場合: メインスレッドで doc_bytes = self.doc.tobytes() を実行してからスレッドを起動する（スレッド内で self.doc にアクセスしない）
- self.preview_img_ref = photo の参照保持は維持すること（GC 防止）

Steps:
1. viewer.py の import 冒頭に `import threading` を追加
2. _show_preview() を以下のパターンに書き換え:
   a. キャンバス消去・crop overlay リセット・ドキュメントなし処理（既存コードのまま）
   b. `self._preview_gen += 1; gen = self._preview_gen`
   c. ローカル変数にコピー: `page_idx = self.current_page; zoom = self.zoom; filepath = self.filepath`
   d. `doc_bytes = self.doc.tobytes() if not filepath else None`（メインスレッドで実行）
   e. ローディングプレースホルダーを即時描画（canvas.create_text で "..." を表示）
   f. worker() 関数（スレッド実行）を定義:
      - filepath があれば tmp_doc = fitz.open(filepath)、なければ tmp_doc = fitz.open(stream=doc_bytes, filetype="pdf")
      - try/finally で tmp_doc.close() を保証
      - page = tmp_doc[page_idx]; mat = fitz.Matrix(zoom * 1.5, zoom * 1.5); pix = page.get_pixmap(matrix=mat, alpha=False)
      - samples = bytes(pix.samples); w, h = pix.width, pix.height
      - 例外時は logger.debug でログして return
      - self.root.after(0, lambda: _apply(samples, w, h)) でメインスレッドに委譲
   g. _apply(samples, w, h) 関数（メインスレッドで root.after から呼ばれる）を定義:
      - if self._preview_gen != gen or not self.doc: return  # stale チェック
      - img = Image.frombytes("RGB", [w, h], samples)
      - photo = ImageTk.PhotoImage(img)
      - self.preview_img_ref = photo
      - 既存の pad=10、shadow rect、border rect、canvas.create_image、scrollregion 設定を再現
   h. threading.Thread(target=worker, daemon=True).start() でスレッド起動
3. ruff check . && ruff format . で確認

Must-haves:
- worker() が fitz.Document 専用インスタンスを finally で必ず close() する
- _apply() が _preview_gen != gen チェックを行う
- self.preview_img_ref 参照保持が維持される
- doc_bytes = self.doc.tobytes() がメインスレッドで実行される（スレッド内ではない）
- daemon=True が設定される
- 例外時は logger.debug でログする（無声失敗を避ける）

## Inputs

- `pagefolio/viewer.py`
- `pagefolio/app.py`

## Expected Output

- `pagefolio/viewer.py`

## Verification

grep -c 'threading\|_preview_gen\|daemon=True' pagefolio/viewer.py

## Observability Impact

worker スレッド内の例外を logger.debug に出力。_apply() の stale チェックにより旧レンダリング結果の誤表示を防止。
