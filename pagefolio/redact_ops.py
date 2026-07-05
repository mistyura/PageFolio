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
            # 複数矩形蓄積状態を初期化（D-07・lazy init・app.py __init__
            # は触らない）
            self._redact_rects = []
            self._redact_rect_overlay_ids = []
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
            self._clear_redact_rects()

    def _redact_mode_off(self):
        """黒塗りモードを明示的に OFF にする（適用完了・相互排他用）。"""
        if self.redact_mode:
            self.redact_mode = False
            self.redact_toggle_btn.configure(
                text=self._t("redact_mode_off"), style="TButton"
            )
            self.preview_canvas.configure(cursor="")
            self._clear_crop_overlay()
            self._clear_redact_rects()

    def _clear_redact_rects(self):
        """蓄積した複数矩形（D-07）とその持続オーバーレイを全クリアする。

        「クリア」ボタン、およびモードOFF時（_toggle_redact_mode/
        _redact_mode_off）の後片付けから呼ばれる。
        """
        for oid in getattr(self, "_redact_rect_overlay_ids", []):
            self.preview_canvas.delete(oid)
        self._redact_rects = []
        self._redact_rect_overlay_ids = []

    def _apply_redact(self):
        """選択矩形を黒塗り（真の墨消し）として対象ページへ適用する。"""
        self._apply_page_edit("redact")

    def _apply_mosaic(self):
        """選択矩形をモザイクとして対象ページへ適用する（D-06）。

        粒度は settings["mosaic_block"] から取得する（未設定時は既定値の
        MOSAIC_BLOCK を温存・constants.py は書き換えない）。
        """
        block = int(self.settings.get("mosaic_block", MOSAIC_BLOCK))
        self._apply_page_edit("mosaic", block=block)

    def _apply_page_edit(self, kind, block=None):
        """黒塗り/モザイクの共通適用フロー。

        トリミングの一括適用（_crop_page の bulk 分岐）と同じく、現在
        ページ上の選択矩形を相対座標へ変換し、各対象ページのページサイズ
        に合わせて適用する。undo は page_edit op（適用前 bytes）。

        D-05: 適用後もモードは維持される（_redact_mode_off は呼ばない）。
        相互排他ロジック（_toggle_redact_mode/_toggle_crop_mode）には
        一切触れない（RESEARCH.md Pitfall 3）。

        D-07: 適用対象矩形は self._redact_rects（蓄積済みの複数矩形）＋
        現在の crop_rect から構築する。_save_undo は対象ページ集合に
        対しループの外側で必ず1回だけ呼ぶ（Pitfall 4・複数矩形×複数
        ページでも1回のundoで全戻り）。

        D-08: 各矩形は _canvas_rect_to_pdf → _derotate_rect（表示座標→
        未回転座標）→ mediabox 相対化、の1本道で変換する（_crop_page と
        同じ順序・Pitfall 2）。
        """
        if not self._check_doc():
            return
        rect_list = list(getattr(self, "_redact_rects", None) or [])
        if self.crop_rect and self.crop_rect not in rect_list:
            rect_list.append(self.crop_rect)
        if not rect_list:
            messagebox.showinfo(self._t("info_title"), self._t("info_redact_drag"))
            return
        targets = self._get_targets()
        if len(targets) > 1:
            if not messagebox.askyesno(
                self._t("confirm_title"),
                self._t("confirm_bulk_redact").format(count=len(targets)),
            ):
                return

        base_page = self.doc[self.current_page]
        cur_mb = base_page.mediabox
        rel_list = []
        for r in rect_list:
            x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._canvas_rect_to_pdf(*r)
            # 表示（回転後）座標 → 未回転座標（D-08・mediabox 相対化の前
            # に挟む1本道・二重補正防止）
            x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._derotate_rect(
                base_page, x0_pdf, y0_pdf, x1_pdf, y1_pdf
            )
            rel_list.append(
                (
                    x0_pdf / cur_mb.width,
                    y0_pdf / cur_mb.height,
                    x1_pdf / cur_mb.width,
                    y1_pdf / cur_mb.height,
                )
            )

        # _save_undo はターゲットページ集合に対しループの外側で必ず1回
        # だけ（D-07・Pitfall 4）
        self._save_undo("page_edit", targets=targets)
        applied = []
        for i in targets:
            page = self.doc[i]
            page_changed = False
            for rel in rel_list:
                rect = self._page_rect_from_rel(page, rel)
                if rect is None:
                    continue
                try:
                    if kind == "redact":
                        self._redact_page(page, rect)
                    else:
                        self._mosaic_page(page, rect, block=block or MOSAIC_BLOCK)
                    page_changed = True
                except Exception as e:
                    logger.error("ページ編集失敗 (kind=%s, page=%s): %s", kind, i, e)
            if page_changed:
                applied.append(i)

        if not applied:
            # 1 ページも適用されなかった場合は直前に積んだ undo エントリを
            # 取り除く（doc は無変更のため）
            if self._undo_stack:
                self._undo_stack.pop()
            messagebox.showerror(self._t("err_title"), self._t("err_redact_small"))
            return

        # 後片付け（D-05: 連続適用のため _redact_mode_off は呼ばない。
        # 蓄積矩形・矩形オーバーレイのみクリアしモードは維持する）
        self.crop_rect = None
        self._clear_redact_rects()
        self._clear_crop_overlay()
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
    def _mosaic_page(page, rect, block=MOSAIC_BLOCK):
        """rect をモザイク化する。

        手順:
          1. 領域を 2 倍スケールでレンダリング（fitz.Matrix(2, 2)）
          2. Pillow で NEAREST 縮小 → 元サイズへ拡大しピクセル化
          3. redaction で下地コンテンツを実削除（モザイク下からの
             テキスト抽出漏えいを防ぐ — 画像を重ねるだけでは不十分）
          4. モザイク画像を rect へ焼き込み（insert_image）

        block: モザイクの粒度（大きいほど粗い）。既定は MOSAIC_BLOCK
        （constants.py・不変）。D-06 では呼び出し元 _apply_mosaic が
        settings["mosaic_block"] を渡す（未設定時はこの既定値のまま・
        後方互換）。
        """
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        small = img.resize(
            (max(1, img.width // block), max(1, img.height // block)),
            Image.NEAREST,
        )
        mosaic = small.resize(img.size, Image.NEAREST)
        buf = io.BytesIO()
        mosaic.save(buf, format="PNG")
        page.add_redact_annot(rect)
        page.apply_redactions()
        page.insert_image(rect, stream=buf.getvalue())

    def _on_mosaic_block_release(self, event=None):
        """モザイク粒度スライダーの変更値を settings へ永続化する（D-06）。

        既存 thumb_zoom スライダー（viewer.py._on_thumb_zoom_release）と
        同型の保存フロー。
        """
        if not hasattr(self, "mosaic_block_var"):
            return
        self.settings["mosaic_block"] = int(self.mosaic_block_var.get())
        from pagefolio.settings import _save_settings

        _save_settings(self.settings)
