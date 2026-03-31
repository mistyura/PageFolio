# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""エントリーポイント — python -m pagefolio"""

import tkinter as tk

from pagefolio.app import PDFEditorApp
from pagefolio.file_drop import _setup_file_drop

try:
    from tkinterdnd2 import TkinterDnD

    _HAS_TKDND = True
except ImportError:
    _HAS_TKDND = False


def main():
    if _HAS_TKDND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PDFEditorApp(root)
    _setup_file_drop(app)
    root.mainloop()


if __name__ == "__main__":
    main()
