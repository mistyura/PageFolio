---
estimated_steps: 31
estimated_files: 1
skills_used: []
---

# T03: _build_thumbnails() を after_idle() プログレッシブローディングに改修

viewer.py の _build_thumbnails() を after_idle() プログレッシブローディングパターンに書き換える。現在は全ページを同期ループ処理するため大規模 PDF で数秒フリーズする。プレースホルダーフレームを全ページ分即時作成し、after_idle() で1枚ずつ逐次レンダリングすることで UI の応答性を維持する。

重要な制約:
- _get_thumb_photo(i) は self.doc[i] をメインスレッドで使うため PyMuPDF のスレッド安全性問題は発生しない（スレッドは使わない）
- self.thumb_images リストは PhotoImage の GC 防止に使用されているため、render_next() 内で photo を append し続けること
- _add_thumb() は後方互換で残すか、既存コードが参照していなければ削除可。既存の popup 内 render_page() は self.doc を直接使うため影響なし。

Steps:
1. _add_thumb(i) を2つのメソッドに分割:
   a. _add_thumb_placeholder(i): frame・プレースホルダー Label（image 引数なし）・ページ番号 Label・全イベントバインディング（on_press/on_motion/on_release/on_double）を作成し、(frame, lbl) を返す。self.thumb_images.append は呼ばない。
   b. _add_thumb(i): _add_thumb_placeholder(i) を呼び、photo = self._get_thumb_photo(i) で画像取得、lbl.configure(image=photo)、self.thumb_images.append(photo) する（後方互換維持）
2. _build_thumbnails() を以下のパターンに書き換え:
   a. self._thumb_gen += 1; gen = self._thumb_gen
   b. 既存子ウィジェット削除: for w in self.thumb_inner.winfo_children(): w.destroy()
   c. self.thumb_images.clear()
   d. if not self.doc: return
   e. プレースホルダーを全ページ分即時作成: placeholder_labels = [self._add_thumb_placeholder(i) for i in range(len(self.doc))]
   f. render_next(i) クロージャ定義:
      - if self._thumb_gen != gen or not self.doc: return  # stale チェック
      - if i >= len(self.doc): return
      - photo = self._get_thumb_photo(i)
      - frame, lbl = placeholder_labels[i]
      - lbl.configure(image=photo)
      - self.thumb_images.append(photo)
      - self.root.after(0, lambda: render_next(i + 1))
   g. self.root.after_idle(lambda: render_next(0))
3. ruff check . && ruff format . で確認

Must-haves:
- _add_thumb_placeholder(i) が (frame, lbl) を返す
- _build_thumbnails() がプレースホルダーを即時作成し、after_idle() で逐次レンダリングをスケジュール
- self.thumb_images への photo append が render_next() 内で行われる
- 世代チェックが render_next() 先頭に含まれる
- _add_thumb() は削除しても可（viewer.py 内の _show_page_popup は self.doc を直接使うため影響なし）

## Inputs

- `pagefolio/viewer.py`

## Expected Output

- `pagefolio/viewer.py`

## Verification

grep -c '_add_thumb_placeholder\|after_idle\|render_next' pagefolio/viewer.py

## Observability Impact

_thumb_gen 不一致で render_next が早期リターンした場合、サムネイルがプレースホルダーのまま残る（視認可能な診断シグナル）。
