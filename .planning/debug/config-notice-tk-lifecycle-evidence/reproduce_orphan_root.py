"""失敗した DnD 初期化が後続の Tk 画像へ及ぼす影響を再現する。"""

import tkinter as tk
from unittest.mock import patch

from PIL import Image, ImageTk
from tkinterdnd2 import TkinterDnD

if tk._default_root is not None:
    raise AssertionError("開始時点で default root が存在する")
with patch.object(
    TkinterDnD, "_require", side_effect=RuntimeError("simulated tkdnd failure")
):
    try:
        TkinterDnD.Tk()
    except RuntimeError as error:
        if str(error) != "simulated tkdnd failure":
            raise
    else:
        raise AssertionError("DnD 初期化の失敗を再現できない")

orphan = tk._default_root
if orphan is None or not orphan.winfo_exists():
    raise AssertionError("失敗した Tk root が残っていない")
root = tk.Tk()
try:
    if tk._default_root is not orphan:
        raise AssertionError("default root が切り替わった")
    canvas = tk.Canvas(root)
    canvas.pack()
    bitmap = Image.new("RGB", (1, 1), "red")
    implicit_photo = ImageTk.PhotoImage(bitmap)
    try:
        canvas.create_image(0, 0, image=implicit_photo)
    except tk.TclError as error:
        if "does not exist" not in str(error):
            raise
        print(f"implicit image: {error}")
    else:
        raise AssertionError("別 interpreter の画像を Canvas が誤って受け入れた")

    explicit_photo = ImageTk.PhotoImage(bitmap, master=canvas)
    canvas.create_image(0, 0, image=explicit_photo)
    print("explicit master: canvas image created")
finally:
    root.destroy()
    orphan.destroy()
