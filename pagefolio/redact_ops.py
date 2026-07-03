# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ページ編集 Mixin — 黒塗り（redaction）・モザイク"""

import io
import logging
from tkinter import messagebox

import fitz
from PIL import Image

from pagefolio.constants import MOSAIC_BLOCK

logger = logging.getLogger(__name__)


class RedactOpsMixin:
    """PDFEditorApp のページ編集（黒塗り・モザイク）メソッド群。

    矩形選択はトリミングと同じキャンバスドラッグ（crop_rect / stipple
    オーバーレイ / _canvas_rect_to_pdf）を共用する。トリミングモードとは
    相互排他（片方を ON にするともう片方は OFF になる）。

    適用は破壊的:
      - 黒塗りは add_redact_annot + apply_redactions による真の墨消しで、
        矩形下のテキスト・画像はファイルから実削除される。
      - モザイクも先に redaction で下地コンテンツを実削除してから
        ピクセル化画像を焼き込む（モザイク下からのテキスト抽出漏えい防止）。
      - apply_redactions は矩形に交差する注釈も削除する（PyMuPDF 仕様）。

    このため undo は page_edit op（適用前ページ bytes キャプチャ）で行う。
    トリミング同様、回転表示中のページでも矩形は未回転のページ座標系で
    適用される（crop と同じ制約）。
    """

    def _toggle_redact_mode(self):
        self.redact_mode = not self.redact_mode
        if self.redact_mode:
            # トリミングモードとは相互排他
            if self.crop_mode:
                self._toggle_crop_mode()
            self.redact_toggle_btn.configure(
                text=self._t("redact_mode_on"), style="CropOn.TButton"
            )
            self.preview_canvas.configure(cursor="crosshair")
        else:
            self.redact_toggle_btn.configure(
                text=self._t("redact_mode_off"), style="TButton"
            )
            self.preview_canvas.configure(cursor="")
            self._clear_crop_overlay()

    def _redact_mode_off(self):
        """黒塗りモードを明示的に OFF にする（適用完了・相互排他用）。"""
        if self.redact_mode:
            self.redact_mode = False
            self.redact_toggle_btn.configure(
                text=self._t("redact_mode_off"), style="TButton"
            )
            self.preview_canvas.configure(cursor="")
            self._clear_crop_overlay()

    def _apply_redact(self):
        """選択矩形を黒塗り（真の墨消し）として対象ページへ適用する。"""
        self._apply_page_edit("redact")

    def _apply_mosaic(self):
        """選択矩形をモザイクとして対象ページへ適用する。"""
        self._apply_page_edit("mosaic")

    def _apply_page_edit(self, kind):
        """黒塗り/モザイクの共通適用フロー。

        トリミングの一括適用（_crop_page の bulk 分岐）と同じく、現在
        ページ上の選択矩形を相対座標へ変換し、各対象ページのページサイズ
        に合わせて適用する。undo は page_edit op（適用前 bytes）。
        """
        if not self._check_doc():
            return
        if not self.crop_rect:
            messagebox.showinfo(self._t("info_title"), self._t("info_redact_drag"))
            return
        targets = self._get_targets()
        if len(targets) > 1:
            if not messagebox.askyesno(
                self._t("confirm_title"),
                self._t("confirm_bulk_redact").format(count=len(targets)),
            ):
                return

        x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._canvas_rect_to_pdf(*self.crop_rect)
        cur_mb = self.doc[self.current_page].mediabox
        rel = (
            x0_pdf / cur_mb.width,
            y0_pdf / cur_mb.height,
            x1_pdf / cur_mb.width,
            y1_pdf / cur_mb.height,
        )

        self._save_undo("page_edit", targets=targets)
        applied = []
        for i in targets:
            page = self.doc[i]
            rect = self._page_rect_from_rel(page, rel)
            if rect is None:
                continue
            try:
                if kind == "redact":
                    self._redact_page(page, rect)
                else:
                    self._mosaic_page(page, rect)
                applied.append(i)
            except Exception as e:
                logger.error("ページ編集失敗 (kind=%s, page=%s): %s", kind, i, e)

        if not applied:
            # 1 ページも適用されなかった場合は直前に積んだ undo エントリを
            # 取り除く（doc は無変更のため）
            if self._undo_stack:
                self._undo_stack.pop()
            messagebox.showerror(self._t("err_title"), self._t("err_redact_small"))
            return

        # 後片付け（トリミング適用完了と同じ作法）
        self.crop_rect = None
        self._redact_mode_off()
        self.crop_info_var.set(self._t("crop_no_sel"))
        self._invalidate_thumb_cache(applied)
        self._refresh_all()
        key = "status_redacted" if kind == "redact" else "status_mosaic"
        self._set_status(self._t(key).format(count=len(applied)))
        self.plugin_manager.fire_event("on_page_edit", self, applied, kind)

    @staticmethod
    def _page_rect_from_rel(page, rel):
        """相対座標 rel をページの mediabox 上の fitz.Rect へ変換する。

        mediabox 内へクランプし、空・微小（1pt 未満）なら None を返す
        （トリミングの bulk 分岐と同じ安全処理）。
        """
        mb = page.mediabox
        rect = fitz.Rect(
            mb.x0 + rel[0] * mb.width,
            mb.y0 + rel[1] * mb.height,
            mb.x0 + rel[2] * mb.width,
            mb.y0 + rel[3] * mb.height,
        )
        rect = fitz.Rect(
            max(rect.x0, mb.x0),
            max(rect.y0, mb.y0),
            min(rect.x1, mb.x1),
            min(rect.y1, mb.y1),
        )
        if rect.is_empty or rect.is_infinite or rect.width < 1 or rect.height < 1:
            return None
        return rect

    @staticmethod
    def _redact_page(page, rect):
        """rect を黒で墨消しする（テキスト・画像を実削除する真の redaction）。"""
        page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()

    @staticmethod
    def _mosaic_page(page, rect):
        """rect をモザイク化する。

        手順:
          1. 領域を 2 倍スケールでレンダリング（fitz.Matrix(2, 2)）
          2. Pillow で NEAREST 縮小 → 元サイズへ拡大しピクセル化
          3. redaction で下地コンテンツを実削除（モザイク下からの
             テキスト抽出漏えいを防ぐ — 画像を重ねるだけでは不十分）
          4. モザイク画像を rect へ焼き込み（insert_image）
        """
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        small = img.resize(
            (max(1, img.width // MOSAIC_BLOCK), max(1, img.height // MOSAIC_BLOCK)),
            Image.NEAREST,
        )
        mosaic = small.resize(img.size, Image.NEAREST)
        buf = io.BytesIO()
        mosaic.save(buf, format="PNG")
        page.add_redact_annot(rect)
        page.apply_redactions()
        page.insert_image(rect, stream=buf.getvalue())
