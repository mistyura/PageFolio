"""
ページ情報表示プラグイン（サンプル）
現在のページのサイズ・回転角度・CropBox情報をツールパネルに表示する。
"""
import tkinter as tk

# pdf_editor.py から PDFEditorPlugin をインポート
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdf_editor import PDFEditorPlugin


class PageInfoPlugin(PDFEditorPlugin):
    name = "ページ情報表示"
    version = "1.0.0"
    description = "現在のページのサイズ・回転角度などを表示します"
    author = "PDF Editor Team"

    def __init__(self):
        self._label = None

    def _update_info(self, app):
        if not self._label:
            return
        if not app.doc or len(app.doc) == 0:
            self._label.configure(text="ファイル未読み込み")
            return
        page = app.doc[app.current_page]
        rect = page.rect
        rotation = page.rotation
        cropbox = page.cropbox
        mediabox = page.mediabox
        has_crop = (cropbox != mediabox)
        lines = [
            f"ページ {app.current_page + 1} / {len(app.doc)}",
            f"サイズ: {rect.width:.1f} × {rect.height:.1f} pt",
            f"回転: {rotation}°",
        ]
        if has_crop:
            lines.append(f"CropBox: ({cropbox.x0:.0f},{cropbox.y0:.0f})-"
                         f"({cropbox.x1:.0f},{cropbox.y1:.0f})")
        self._label.configure(text="\n".join(lines))

    def build_ui(self, app, parent):
        # テーマ色を動的に取得
        from pdf_editor import C
        self._label = tk.Label(parent, text="ファイル未読み込み",
                               bg=C["BG_CARD"], fg=C["TEXT_SUB"],
                               font=app._font(-2), justify="left",
                               anchor="w", padx=8, pady=4)
        self._label.pack(fill="x", padx=8, pady=(0, 4))
        self._update_info(app)

    def on_file_open(self, app, path):
        self._update_info(app)

    def on_page_change(self, app, page_index):
        self._update_info(app)

    def on_page_rotate(self, app, pages, degrees):
        self._update_info(app)

    def on_page_crop(self, app, page_index):
        self._update_info(app)

    def on_page_delete(self, app, pages):
        self._update_info(app)
