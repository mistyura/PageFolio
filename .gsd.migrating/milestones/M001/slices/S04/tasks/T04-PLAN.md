---
estimated_steps: 81
estimated_files: 1
skills_used: []
---

# T04: page_ops.py の _crop_page() に複数ページ一括トリミング対応を追加する

page_ops.py の `_crop_page()` を変更し、複数ページ選択時に相対座標変換 + bulk_crop op で一括トリミングを適用する。単ページ選択時は既存コードパスを維持する。

**変更手順:**
1. `_crop_page()` の `if not self.crop_rect:` チェックの直後に `targets = self._get_targets()` を追加
2. 複数ページ確認ダイアログを追加:
```python
if len(targets) > 1:
    if not messagebox.askyesno(
        self._t("confirm_title"),
        self._t("confirm_bulk_crop").format(count=len(targets)),
    ):
        return
```
3. 単ページ (`len(targets) == 1`) の場合: 既存コードを維持（`self._save_undo("crop", page_i=self.current_page)` から始まるブロック、`self._invalidate_thumb_cache([self.current_page])` の前まで）
4. 複数ページ (`len(targets) > 1`) の場合: 以下のブロックを追加:
```python
else:
    sx, sy, ex, ey = self.crop_rect
    scale = self.zoom * 1.5
    img_offset = 10
    x0_pdf = (sx - img_offset) / scale
    y0_pdf = (sy - img_offset) / scale
    x1_pdf = (ex - img_offset) / scale
    y1_pdf = (ey - img_offset) / scale
    cur_mb = self.doc[self.current_page].mediabox
    rel = (
        x0_pdf / cur_mb.width,
        y0_pdf / cur_mb.height,
        x1_pdf / cur_mb.width,
        y1_pdf / cur_mb.height,
    )
    EPS = 0.01
    crop_data = []
    for i in targets:
        cb = self.doc[i].cropbox
        crop_data.append((i, (cb.x0, cb.y0, cb.x1, cb.y1)))
    self._save_undo("bulk_crop", crop_data=crop_data)
    for i in targets:
        page = self.doc[i]
        mb = page.mediabox
        new_rect = fitz.Rect(
            mb.x0 + rel[0] * mb.width,
            mb.y0 + rel[1] * mb.height,
            mb.x0 + rel[2] * mb.width,
            mb.y0 + rel[3] * mb.height,
        )
        new_rect = fitz.Rect(
            max(round(new_rect.x0, 2), mb.x0 + EPS),
            max(round(new_rect.y0, 2), mb.y0 + EPS),
            min(round(new_rect.x1, 2), mb.x1 - EPS),
            min(round(new_rect.y1, 2), mb.y1 - EPS),
        )
        if (
            new_rect.is_empty
            or new_rect.is_infinite
            or new_rect.width < 1
            or new_rect.height < 1
        ):
            continue
        try:
            page.set_cropbox(new_rect)
        except ValueError:
            continue
```
5. 共通後処理（モードリセット・ステータス表示）を if/else の外に配置。既存の `self._invalidate_thumb_cache([self.current_page])` を `self._invalidate_thumb_cache(targets)` に変更。ステータス表示とイベント通知は targets のサイズで分岐:
```python
self.crop_rect = None
self.crop_mode = False
self.crop_toggle_btn.configure(text=self._t("crop_mode_off"), style="TButton")
self.preview_canvas.configure(cursor="")
self.crop_info_var.set(self._t("crop_no_sel"))
self._invalidate_thumb_cache(targets)
self._refresh_all()
if len(targets) == 1:
    self._set_status(self._t("status_cropped").format(page=self.current_page + 1))
    self.plugin_manager.fire_event("on_page_crop", self, self.current_page)
else:
    self._set_status(self._t("status_bulk_cropped").format(count=len(targets)))
    self.plugin_manager.fire_event("on_page_crop", self, targets)
```

**T01 前提:** `_save_undo("bulk_crop", crop_data=...)` は T01 で追加した分岐が必要。
**T02 前提:** `confirm_bulk_crop` / `status_bulk_cropped` は T02 で追加した LANG キーが必要。

## Inputs

- `pagefolio/page_ops.py`
- `pagefolio/file_ops.py`
- `pagefolio/constants.py`

## Expected Output

- `pagefolio/page_ops.py`

## Verification

grep -c "bulk_crop\|confirm_bulk_crop\|_get_targets" pagefolio/page_ops.py
