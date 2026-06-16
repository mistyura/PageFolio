# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ファイル D&D — tkinterdnd2 によるプレビューキャンバスへのドロップ登録"""

try:
    from tkinterdnd2 import DND_FILES

    _HAS_TKDND = True
except ImportError:
    _HAS_TKDND = False


def _setup_file_drop(app):
    """tkinterdnd2 で preview_canvas / thumb_canvas に D&D 登録する。

    未インストール時はスキップする。
    """
    if not _HAS_TKDND:
        return

    def bind_canvas(canvas, is_thumb=False):
        canvas.drop_target_register(DND_FILES)
        canvas.dnd_bind("<<DropEnter>>", app._on_dnd_enter)
        canvas.dnd_bind("<<DropLeave>>", app._on_dnd_leave)

        # サムネイルへのドロップ時は特別なハンドラを使う
        drop_handler = app._on_thumb_dnd_drop if is_thumb else app._on_dnd_drop
        canvas.dnd_bind("<<Drop>>", drop_handler)

        # サムネイル領域専用のドラッグ中のインジケーター表示用イベント
        if is_thumb:
            canvas.dnd_bind("<<DropPosition>>", app._on_thumb_dnd_motion)

    bind_canvas(app.preview_canvas, is_thumb=False)
    bind_canvas(app.thumb_canvas, is_thumb=True)
