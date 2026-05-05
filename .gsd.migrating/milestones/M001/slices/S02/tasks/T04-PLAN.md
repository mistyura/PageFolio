---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T04: file_ops.py のドキュメント入替3箇所で gen カウンターをインクリメント

file_ops.py の _open_pdf_path()、_do_open_merged()、_restore_state() の3箇所でドキュメント入替時に self._preview_gen += 1 と self._thumb_gen += 1 をインクリメントする。これにより、前のドキュメントに対して発行されたバックグラウンドレンダリング処理が新しいドキュメントに誤適用されることを防ぐ。

挿入位置ルール: 各箇所で self._invalidate_thumb_cache() 呼び出しの直後、self._refresh_all() 呼び出しの前に2行追加する。

Steps:
1. _open_pdf_path()（line 144 付近）の self._invalidate_thumb_cache() 直後に追加:
   self._preview_gen += 1
   self._thumb_gen += 1
2. _do_open_merged()（line 122 付近）の self._invalidate_thumb_cache() 直後に同様追加
3. _restore_state()（line 74 付近）の self._invalidate_thumb_cache() 直後に同様追加
4. ruff check . && ruff format . で確認
5. pytest で 108件 PASSED を確認

Must-haves:
- 3箇所すべてで _preview_gen と _thumb_gen がインクリメントされる
- 各箇所で _invalidate_thumb_cache() の後、_refresh_all() の前に配置される

## Inputs

- `pagefolio/file_ops.py`
- `pagefolio/viewer.py`
- `pagefolio/app.py`

## Expected Output

- `pagefolio/file_ops.py`

## Verification

grep -c '_preview_gen\|_thumb_gen' pagefolio/file_ops.py
