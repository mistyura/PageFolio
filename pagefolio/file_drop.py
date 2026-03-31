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
    """tkinterdnd2 による preview_canvas への D&D 登録。未インストール時はスキップ。"""
    if not _HAS_TKDND:
        return
    canvas = app.preview_canvas
    canvas.drop_target_register(DND_FILES)
    canvas.dnd_bind("<<DropEnter>>", app._on_dnd_enter)
    canvas.dnd_bind("<<DropLeave>>", app._on_dnd_leave)
    canvas.dnd_bind("<<Drop>>", app._on_dnd_drop)
