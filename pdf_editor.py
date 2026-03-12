"""
PDF Editor GUI - Windows 11
必要ライブラリ: pip install pymupdf pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # pymupdf
from PIL import Image, ImageTk
import io
import os


# ===================== カラーテーマ =====================
BG_DARK    = "#1a1a2e"
BG_PANEL   = "#16213e"
BG_CARD    = "#0f3460"
ACCENT     = "#e94560"
ACCENT2    = "#533483"
TEXT_MAIN  = "#eaeaea"
TEXT_SUB   = "#a0a0b0"
BTN_HOVER  = "#ff6b6b"
SUCCESS    = "#4ecca3"
WARNING    = "#ffd460"
CROP_ON_BG = "#8b0000"


class PDFEditorApp:
    MAX_UNDO = 20

    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor")
        self.root.geometry("1200x780")
        self.root.configure(bg=BG_DARK)
        self.root.minsize(900, 600)

        self.doc = None
        self.filepath = None
        self.current_page = 0
        self.selected_pages = set()
        self.thumb_images = []
        self.thumb_cache = {}       # サムネイルキャッシュ (#7)
        self._dnd_src_idx  = None
        self._dnd_ghost    = None
        self._dnd_indicator= None
        self.crop_rect = None
        self.crop_drag_start = None
        self.crop_mode = False

        # Undo / Redo (#18)
        self._undo_stack = []
        self._redo_stack = []

        self._build_styles()
        self._build_ui()

        # WM_DELETE_WINDOW (#5)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # キーボードショートカット (#12)
        self.root.bind("<Control-o>", lambda e: self._open_file())
        self.root.bind("<Control-O>", lambda e: self._open_file())
        self.root.bind("<Control-s>", lambda e: self._save_file())
        self.root.bind("<Control-S>", lambda e: self._save_file())
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-Z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-Y>", lambda e: self._redo())
        self.root.bind("<Control-Shift-s>", lambda e: self._save_as())
        self.root.bind("<Control-Shift-S>", lambda e: self._save_as())
        self.root.bind("<Delete>",    lambda e: self._delete_selected())

    # ─────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel",
                        background=BG_DARK, foreground=TEXT_MAIN,
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel",
                        background=BG_DARK, foreground=ACCENT,
                        font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel",
                        background=BG_DARK, foreground=TEXT_SUB,
                        font=("Segoe UI", 9))
        style.configure("Status.TLabel",
                        background=BG_PANEL, foreground=SUCCESS,
                        font=("Segoe UI", 9))
        style.configure("TButton",
                        background=BG_CARD, foreground=TEXT_MAIN,
                        font=("Segoe UI", 9, "bold"),
                        borderwidth=0, padding=(10, 6))
        style.map("TButton",
                  background=[("active", ACCENT), ("pressed", ACCENT2)],
                  foreground=[("active", "#ffffff")])
        style.configure("Accent.TButton",
                        background=ACCENT, foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0, padding=(12, 7))
        style.map("Accent.TButton",
                  background=[("active", BTN_HOVER)])
        style.configure("Danger.TButton",
                        background="#7c1c2e", foreground="#ffaaaa",
                        font=("Segoe UI", 9, "bold"),
                        borderwidth=0, padding=(10, 6))
        style.map("Danger.TButton",
                  background=[("active", ACCENT)])
        # トリミングモードON強調 (#16)
        style.configure("CropOn.TButton",
                        background=CROP_ON_BG, foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"),
                        borderwidth=2, padding=(10, 6))
        style.map("CropOn.TButton",
                  background=[("active", "#aa0000")])
        style.configure("TScrollbar",
                        background=BG_CARD, troughcolor=BG_PANEL,
                        borderwidth=0, arrowsize=12)
        style.configure("Horizontal.TScale",
                        background=BG_DARK, troughcolor=BG_CARD)

    # ─────────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG_PANEL, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="✦ PDF Editor", bg=BG_PANEL,
                 fg=ACCENT, font=("Segoe UI", 16, "bold")).pack(side="left", padx=20, pady=12)
        self.status_var = tk.StringVar(value="ファイルを開いてください")
        tk.Label(header, textvariable=self.status_var,
                 bg=BG_PANEL, fg=SUCCESS,
                 font=("Segoe UI", 9)).pack(side="right", padx=20)

        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=BG_PANEL, width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_thumb_panel(left)

        center = tk.Frame(main, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)
        self._build_preview(center)

        right = tk.Frame(main, bg=BG_PANEL, width=230)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_tools(right)

    # ─────────────────────────────────────────
    def _build_thumb_panel(self, parent):
        hdr = tk.Frame(parent, bg=BG_PANEL)
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(hdr, text="ページ一覧", bg=BG_PANEL,
                 fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(hdr, text="D&D で並替", bg=BG_PANEL,
                 fg=TEXT_SUB, font=("Segoe UI", 7)).pack(side="right")

        sel_frame = tk.Frame(parent, bg=BG_PANEL)
        sel_frame.pack(fill="x", padx=6, pady=2)
        ttk.Button(sel_frame, text="全選択",
                   command=self._select_all).pack(side="left", padx=2)
        ttk.Button(sel_frame, text="解除",
                   command=self._deselect_all).pack(side="left", padx=2)

        canvas_frame = tk.Frame(parent, bg=BG_PANEL)
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.thumb_canvas = tk.Canvas(canvas_frame, bg=BG_PANEL,
                                      highlightthickness=0)
        sb = ttk.Scrollbar(canvas_frame, orient="vertical",
                           command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.thumb_canvas.pack(fill="both", expand=True)

        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=BG_PANEL)
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner,
                                        anchor="nw")
        self.thumb_inner.bind("<Configure>",
                              lambda e: self.thumb_canvas.configure(
                                  scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.bind("<MouseWheel>",
                               lambda e: self.thumb_canvas.yview_scroll(
                                   int(-1*(e.delta/120)), "units"))

    # ─────────────────────────────────────────
    def _build_preview(self, parent):
        toolbar = tk.Frame(parent, bg=BG_PANEL, height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        ttk.Button(toolbar, text="◀ 前",
                   command=self._prev_page).pack(side="left", padx=6, pady=8)
        self.page_label = tk.Label(toolbar, text="- / -",
                                   bg=BG_PANEL, fg=TEXT_MAIN,
                                   font=("Segoe UI", 10, "bold"))
        self.page_label.pack(side="left", padx=4)
        ttk.Button(toolbar, text="次 ▶",
                   command=self._next_page).pack(side="left", padx=6)

        ttk.Button(toolbar, text="🔍 縮小",
                   command=lambda: self._zoom(-0.2)).pack(side="right", padx=4, pady=8)
        ttk.Button(toolbar, text="🔍 拡大",
                   command=lambda: self._zoom(0.2)).pack(side="right", padx=4)
        self.zoom_label = tk.Label(toolbar, text="100%",
                                   bg=BG_PANEL, fg=TEXT_SUB,
                                   font=("Segoe UI", 9))
        self.zoom_label.pack(side="right", padx=4)

        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(frame, bg="#111122",
                                        highlightthickness=0)
        vbar = ttk.Scrollbar(frame, orient="vertical",
                             command=self.preview_canvas.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal",
                             command=self.preview_canvas.xview)
        self.preview_canvas.configure(yscrollcommand=vbar.set,
                                      xscrollcommand=hbar.set)
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<MouseWheel>",
                                 lambda e: self.preview_canvas.yview_scroll(
                                     int(-1*(e.delta/120)), "units"))
        self.preview_canvas.bind("<ButtonPress-1>",   self._crop_drag_start)
        self.preview_canvas.bind("<B1-Motion>",       self._crop_drag_move)
        self.preview_canvas.bind("<ButtonRelease-1>", self._crop_drag_end)
        self.zoom = 1.0
        self.preview_img_ref = None
        self.crop_rect_id = None
        self.crop_overlay_ids = []

    # ─────────────────────────────────────────
    def _build_tools(self, parent):
        tk.Label(parent, text="ツール", bg=BG_PANEL,
                 fg=ACCENT, font=("Segoe UI", 11, "bold")).pack(pady=(14, 6))

        def section(title):
            f = tk.Frame(parent, bg=BG_CARD, bd=0)
            f.pack(fill="x", padx=10, pady=5)
            tk.Label(f, text=title, bg=BG_CARD, fg=WARNING,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6,2))
            return f

        def btn(parent, text, cmd, style="TButton"):
            ttk.Button(parent, text=text, command=cmd,
                       style=style).pack(fill="x", padx=8, pady=2)

        f = section("📂 ファイル")
        btn(f, "ファイルを開く (Ctrl+O)", self._open_file, "Accent.TButton")
        btn(f, "上書き保存 (Ctrl+S)", self._save_file)
        btn(f, "名前を付けて保存 (Ctrl+Shift+S)", self._save_as)
        btn(f, "✕ 終了", self._quit, "Danger.TButton")

        f_ur = section("↩ 元に戻す / やり直す")
        btn(f_ur, "↩ 元に戻す (Ctrl+Z)", self._undo)
        btn(f_ur, "↪ やり直す (Ctrl+Y)", self._redo)

        f2 = section("📄 ページ操作（選択ページ）")
        tk.Label(f2, text="回転角度:", bg=BG_CARD, fg=TEXT_SUB,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        rot_f = tk.Frame(f2, bg=BG_CARD)
        rot_f.pack(fill="x", padx=6, pady=2)
        for deg, label in [(90,"↻ 90°"), (180,"↺↻ 180°"), (270,"↺ 270°")]:
            ttk.Button(rot_f, text=label,
                       command=lambda d=deg: self._rotate_selected(d)
                       ).pack(side="left", expand=True, fill="x", padx=2, pady=2)

        btn(f2, "🗑 選択ページを削除 (Del)", self._delete_selected, "Danger.TButton")

        f3 = section("✂ トリミング（現在ページ）")
        self.crop_mode_var = tk.BooleanVar(value=False)
        self.crop_toggle_btn = ttk.Button(
            f3, text="✂ 範囲選択モード OFF",
            command=self._toggle_crop_mode)
        self.crop_toggle_btn.pack(fill="x", padx=8, pady=(4,2))
        tk.Label(f3, text="プレビュー上でドラッグして範囲を指定",
                 bg=BG_CARD, fg=TEXT_SUB, font=("Segoe UI", 8)).pack(anchor="w", padx=8)

        self.crop_info_var = tk.StringVar(value="範囲未選択")
        tk.Label(f3, textvariable=self.crop_info_var,
                 bg=BG_CARD, fg=SUCCESS, font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=2)

        btn(f3, "✔ 選択範囲でトリミング", self._crop_page)
        btn(f3, "✕ 選択範囲をリセット",   self._crop_reset, "Danger.TButton")

        f4 = section("📎 挿入・結合")
        btn(f4, "別PDFから挿入", self._insert_from_file)
        btn(f4, "PDFを末尾に結合", self._merge_pdf)

        f5 = section("🔀 ページ移動")
        move_f = tk.Frame(f5, bg=BG_CARD)
        move_f.pack(fill="x", padx=6, pady=4)
        tk.Label(move_f, text="移動先(1始まり):", bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 9)).pack(side="left")
        self.move_var = tk.IntVar(value=1)
        tk.Spinbox(move_f, from_=1, to=9999, textvariable=self.move_var,
                   width=5, bg=BG_DARK, fg=TEXT_MAIN,
                   insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0
                   ).pack(side="left", padx=4)
        btn(f5, "現在ページを移動", self._move_page)

    # ══════════════════════════════════════════
    #  Undo / Redo (#18)
    # ══════════════════════════════════════════
    def _save_undo(self):
        if not self.doc:
            return
        state = {
            'pdf_bytes': self.doc.tobytes(),
            'current_page': self.current_page,
            'selected_pages': set(self.selected_pages),
        }
        self._undo_stack.append(state)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack:
            self._set_status("元に戻す履歴がありません")
            return
        if self.doc:
            self._redo_stack.append({
                'pdf_bytes': self.doc.tobytes(),
                'current_page': self.current_page,
                'selected_pages': set(self.selected_pages),
            })
        state = self._undo_stack.pop()
        self._restore_state(state)
        self._set_status("元に戻しました")

    def _redo(self):
        if not self._redo_stack:
            self._set_status("やり直す履歴がありません")
            return
        if self.doc:
            self._undo_stack.append({
                'pdf_bytes': self.doc.tobytes(),
                'current_page': self.current_page,
                'selected_pages': set(self.selected_pages),
            })
        state = self._redo_stack.pop()
        self._restore_state(state)
        self._set_status("やり直しました")

    def _restore_state(self, state):
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(stream=state['pdf_bytes'], filetype="pdf")
        self.current_page = min(state['current_page'], max(0, len(self.doc) - 1))
        self.selected_pages = state['selected_pages']
        self._invalidate_thumb_cache()
        self._refresh_all()

    # ══════════════════════════════════════════
    #  ファイル操作
    # ══════════════════════════════════════════
    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("PDFファイル", "*.pdf"), ("すべて", "*.*")])
        if not path:
            return
        self._open_pdf_path(path)

    def _open_pdf_path(self, path):
        """パス指定でPDFを開く（ダイアログ / D&D 共用）"""
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(path)
            self.filepath = path
            self.current_page = 0
            self.selected_pages.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._invalidate_thumb_cache()
            self._refresh_all()
            self._set_status(f"開きました: {os.path.basename(path)}  ({len(self.doc)}ページ)")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _save_file(self):
        """上書き保存 — 確認ダイアログ付き (#14)"""
        if not self.doc or not self.filepath:
            messagebox.showinfo("情報", "先にファイルを開いてください")
            return
        if not messagebox.askyesno("上書き保存の確認",
                                    f"以下のファイルを上書き保存します。\n\n"
                                    f"{os.path.basename(self.filepath)}\n\n"
                                    f"元のファイルは上書きされます。よろしいですか？"):
            return
        try:
            try:
                self.doc.save(self.filepath, incremental=True,
                              encryption=fitz.PDF_ENCRYPT_KEEP)
            except Exception:
                tmp = self.filepath + ".tmp"
                self.doc.save(tmp)
                os.replace(tmp, self.filepath)
            self._set_status(f"保存しました: {os.path.basename(self.filepath)}")
        except Exception as e:
            messagebox.showerror("保存エラー", f"保存に失敗しました:\n{e}")

    def _save_as(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDFファイル", "*.pdf")])
        if not path:
            return
        try:
            self.doc.save(path)
            self.filepath = path
            self._set_status(f"保存しました: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    # ══════════════════════════════════════════
    #  ページ操作
    # ══════════════════════════════════════════
    def _rotate_selected(self, deg):
        if not self._check_doc():
            return
        self._save_undo()
        targets = self._get_targets()
        for i in targets:
            page = self.doc[i]
            page.set_rotation((page.rotation + deg) % 360)
        self._invalidate_thumb_cache(targets)
        self._refresh_all()
        self._set_status(f"{len(targets)}ページを{deg}°回転しました")

    def _delete_selected(self):
        if not self._check_doc():
            return
        targets = sorted(self._get_targets(), reverse=True)
        if not targets:
            messagebox.showinfo("情報", "削除するページを選択してください")
            return
        # 全ページ削除防止 (#17)
        if len(targets) >= len(self.doc):
            messagebox.showwarning("警告",
                "すべてのページを削除することはできません。\n"
                "最低1ページは残す必要があります。")
            return
        if not messagebox.askyesno("確認", f"{len(targets)}ページを削除しますか？"):
            return
        self._save_undo()
        for i in targets:
            self.doc.delete_page(i)
        self.selected_pages.clear()
        self.current_page = min(self.current_page, max(0, len(self.doc)-1))
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(f"{len(targets)}ページを削除しました")

    # ── トリミング (#16 視覚強調)
    def _toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            self.crop_toggle_btn.configure(
                text="🔴 範囲選択モード ON  (クリックで OFF)",
                style="CropOn.TButton")
            self.preview_canvas.configure(cursor="crosshair")
        else:
            self.crop_toggle_btn.configure(
                text="✂ 範囲選択モード OFF",
                style="TButton")
            self.preview_canvas.configure(cursor="")
            self._clear_crop_overlay()

    def _crop_drag_start(self, event):
        if not self.crop_mode:
            return
        cx = self.preview_canvas.canvasx(event.x)
        cy = self.preview_canvas.canvasy(event.y)
        self.crop_drag_start = (cx, cy)
        self.crop_rect = None
        self._clear_crop_overlay()

    # ── ドラッグ中 (#9 coords更新方式)
    def _crop_drag_move(self, event):
        if not self.crop_mode or not self.crop_drag_start:
            return
        cx = self.preview_canvas.canvasx(event.x)
        cy = self.preview_canvas.canvasy(event.y)
        x0, y0 = self.crop_drag_start
        sx, sy, ex, ey = min(x0,cx), min(y0,cy), max(x0,cx), max(y0,cy)

        sr = self.preview_canvas.cget("scrollregion")
        if sr:
            parts = sr.split()
            pw = float(parts[2]) if len(parts) >= 3 else self.preview_canvas.winfo_width()
            ph = float(parts[3]) if len(parts) >= 4 else self.preview_canvas.winfo_height()
        else:
            pw = self.preview_canvas.winfo_width()
            ph = self.preview_canvas.winfo_height()

        if not self.crop_overlay_ids:
            self.crop_overlay_ids = [
                self.preview_canvas.create_rectangle(0, 0, pw, sy, fill="#000000", stipple="gray50", outline=""),
                self.preview_canvas.create_rectangle(0, ey, pw, ph, fill="#000000", stipple="gray50", outline=""),
                self.preview_canvas.create_rectangle(0, sy, sx, ey, fill="#000000", stipple="gray50", outline=""),
                self.preview_canvas.create_rectangle(ex, sy, pw, ey, fill="#000000", stipple="gray50", outline=""),
            ]
            self.crop_rect_id = self.preview_canvas.create_rectangle(
                sx, sy, ex, ey, outline=ACCENT, width=2, dash=(4,3))
        else:
            self.preview_canvas.coords(self.crop_overlay_ids[0], 0, 0, pw, sy)
            self.preview_canvas.coords(self.crop_overlay_ids[1], 0, ey, pw, ph)
            self.preview_canvas.coords(self.crop_overlay_ids[2], 0, sy, sx, ey)
            self.preview_canvas.coords(self.crop_overlay_ids[3], ex, sy, pw, ey)
            if self.crop_rect_id:
                self.preview_canvas.coords(self.crop_rect_id, sx, sy, ex, ey)

        self.crop_rect = (sx, sy, ex, ey)
        scale = self.zoom * 1.5
        img_offset = 10
        px0 = int((sx - img_offset) / scale)
        py0 = int((sy - img_offset) / scale)
        px1 = int((ex - img_offset) / scale)
        py1 = int((ey - img_offset) / scale)
        self.crop_info_var.set(f"({px0},{py0}) - ({px1},{py1})  {px1-px0}×{py1-py0} pt")

    def _crop_drag_end(self, event):
        if not self.crop_mode:
            return
        self._crop_drag_move(event)

    def _clear_crop_overlay(self):
        for oid in self.crop_overlay_ids:
            self.preview_canvas.delete(oid)
        self.crop_overlay_ids = []
        if self.crop_rect_id:
            self.preview_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    def _crop_reset(self):
        self.crop_rect = None
        self.crop_info_var.set("範囲未選択")
        self._clear_crop_overlay()

    def _crop_page(self):
        if not self._check_doc():
            return
        if not self.crop_rect:
            messagebox.showinfo("情報", "プレビュー上でドラッグしてトリミング範囲を選択してください")
            return
        self._save_undo()
        sx, sy, ex, ey = self.crop_rect
        scale = self.zoom * 1.5
        img_offset = 10
        x0_pdf = (sx - img_offset) / scale
        y0_pdf = (sy - img_offset) / scale
        x1_pdf = (ex - img_offset) / scale
        y1_pdf = (ey - img_offset) / scale
        page = self.doc[self.current_page]
        mb = page.mediabox
        new_rect = fitz.Rect(mb.x0 + x0_pdf, mb.y0 + y0_pdf,
                             mb.x0 + x1_pdf, mb.y0 + y1_pdf)
        if new_rect.is_empty or new_rect.is_infinite:
            messagebox.showerror("エラー", "範囲が小さすぎます。もう一度ドラッグしてください")
            return
        page.set_cropbox(new_rect)
        self.crop_rect = None
        self.crop_mode = False
        self.crop_toggle_btn.configure(text="✂ 範囲選択モード OFF", style="TButton")
        self.preview_canvas.configure(cursor="")
        self.crop_info_var.set("範囲未選択")
        self._invalidate_thumb_cache([self.current_page])
        self._refresh_all()
        self._set_status(f"ページ{self.current_page+1}をトリミングしました")

    def _insert_from_file(self):
        if not self._check_doc():
            return
        paths = filedialog.askopenfilenames(
            title="挿入するPDFを選択（複数可）",
            filetypes=[("PDFファイル", "*.pdf")])
        if not paths:
            return
        pos = simpledialog.askinteger(
            "挿入位置",
            f"挿入する位置を入力してください\n(1〜{len(self.doc)+1})\n\n"
            f"例: 3 と入力 → 2ページ目と3ページ目の間に挿入",
            minvalue=1, maxvalue=len(self.doc)+1,
            initialvalue=self.current_page+2)
        if pos is None:
            return
        self._save_undo()
        try:
            insert_at = pos - 1
            for path in paths:
                src = fitz.open(path)
                self.doc.insert_pdf(src, start_at=insert_at)
                insert_at += len(src)
                src.close()
            self._invalidate_thumb_cache()
            self._refresh_all()
            self._set_status(f"{len(paths)}ファイルを{pos}ページ目に挿入しました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _merge_pdf(self):
        if not self._check_doc():
            return
        paths = filedialog.askopenfilenames(
            title="結合するPDFを選択（複数可・選択順に結合）",
            filetypes=[("PDFファイル", "*.pdf")])
        if not paths:
            return
        MergeOrderDialog(self.root, list(paths), self._do_merge)

    def _do_merge(self, ordered_paths):
        self._save_undo()
        try:
            total = 0
            for path in ordered_paths:
                src = fitz.open(path)
                self.doc.insert_pdf(src)
                total += len(src)
                src.close()
            self._invalidate_thumb_cache()
            self._refresh_all()
            self._set_status(
                f"{len(ordered_paths)}ファイル（計{total}ページ）を末尾に結合しました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def _move_page(self):
        if not self._check_doc():
            return
        src = self.current_page
        dest = self.move_var.get() - 1
        dest = max(0, min(dest, len(self.doc)-1))
        if dest == src:
            return
        self._save_undo()
        self.doc.move_page(src, dest)
        self.current_page = dest
        self.selected_pages.clear()
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(f'p.{src+1} → p.{dest+1} に移動しました')

    def _toggle_select(self, i):
        if i in self.selected_pages:
            self.selected_pages.discard(i)
        else:
            self.selected_pages.add(i)
        self._refresh_thumbs_selection_only()

    def _select_all(self):
        if not self.doc:
            return
        self.selected_pages = set(range(len(self.doc)))
        self._refresh_thumbs_selection_only()

    def _deselect_all(self):
        self.selected_pages.clear()
        self._refresh_thumbs_selection_only()

    def _show_preview(self):
        self.preview_canvas.delete("all")
        self.crop_overlay_ids = []
        self.crop_rect_id = None
        if not self.doc or len(self.doc) == 0:
            return
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom * 1.5, self.zoom * 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.preview_img_ref = photo
        self.preview_canvas.create_image(10, 10, anchor="nw", image=photo)
        self.preview_canvas.configure(
            scrollregion=(0, 0, pix.width+20, pix.height+20))

    # ══════════════════════════════════════════
    #  ナビゲーション & ズーム
    # ══════════════════════════════════════════
    def _prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._refresh_all()

    def _next_page(self):
        if self.doc and self.current_page < len(self.doc)-1:
            self.current_page += 1
            self._refresh_all()

    def _zoom(self, delta):
        self.zoom = max(0.3, min(3.0, self.zoom + delta))
        self.zoom_label.configure(text=f"{int(self.zoom*100)}%")
        self._show_preview()

    # ══════════════════════════════════════════
    #  サムネイル (#7 キャッシュ化)
    # ══════════════════════════════════════════
    def _invalidate_thumb_cache(self, pages=None):
        if pages is None:
            self.thumb_cache.clear()
        else:
            for p in pages:
                self.thumb_cache.pop(p, None)

    def _get_thumb_photo(self, i):
        if i in self.thumb_cache:
            return self.thumb_cache[i]
        page = self.doc[i]
        mat = fitz.Matrix(0.22, 0.22)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.thumb_cache[i] = photo
        return photo

    def _refresh_all(self):
        self._build_thumbnails()
        self._show_preview()
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page+1} / {n}" if n else "- / -")

    def _refresh_thumbs_selection_only(self):
        """選択・カレント変更のみ — 画像再生成なし (#8)"""
        frames = self.thumb_inner.winfo_children()
        for i, frame in enumerate(frames):
            is_sel = i in self.selected_pages
            is_cur = i == self.current_page
            bg = ACCENT if is_sel else (BG_CARD if is_cur else BG_PANEL)
            frame.configure(bg=bg)
            for child in frame.winfo_children():
                child.configure(bg=bg)
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page+1} / {n}" if n else "- / -")

    def _build_thumbnails(self):
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.thumb_images.clear()
        if not self.doc:
            return
        for i in range(len(self.doc)):
            self._add_thumb(i)

    def _add_thumb(self, i):
        photo = self._get_thumb_photo(i)
        self.thumb_images.append(photo)

        is_sel = i in self.selected_pages
        is_cur = i == self.current_page
        bg = ACCENT if is_sel else (BG_CARD if is_cur else BG_PANEL)

        frame = tk.Frame(self.thumb_inner, bg=bg, cursor="hand2")
        frame.pack(fill="x", padx=6, pady=3)

        lbl = tk.Label(frame, image=photo, bg=bg)
        lbl.pack(pady=(4,0))
        tk.Label(frame, text=f"p.{i+1}", bg=bg, fg=TEXT_MAIN,
                 font=("Segoe UI", 8)).pack(pady=(0,4))

        def on_press(event, idx=i):
            self._dnd_src_idx = idx
            self._dnd_press_x = event.x_root
            self._dnd_press_y = event.y_root
            self._dnd_dragging = False

        def on_motion(event, idx=i):
            if self._dnd_src_idx is None:
                return
            dx = abs(event.x_root - self._dnd_press_x)
            dy = abs(event.y_root - self._dnd_press_y)
            if not self._dnd_dragging and (dx > 5 or dy > 5):
                self._dnd_dragging = True
                self._dnd_start_ghost(idx)
            if self._dnd_dragging:
                self._dnd_move_ghost(event)
                self._dnd_show_indicator(event)

        def on_release(event, idx=i):
            if self._dnd_dragging:
                self._dnd_drop(event)
            else:
                if event.state & 0x0004:  # Ctrl
                    self._toggle_select(idx)
                else:
                    self.selected_pages.clear()
                    self.current_page = idx
                    self._refresh_all()
            self._dnd_src_idx  = None
            self._dnd_dragging = False
            self._dnd_destroy_ghost()
            self._dnd_clear_indicator()

        for w in (frame, lbl):
            w.bind('<ButtonPress-1>',   on_press)
            w.bind('<B1-Motion>',       on_motion)
            w.bind('<ButtonRelease-1>', on_release)

    # ══ D&D ヘルパー ══════════════════════════════
    def _dnd_start_ghost(self, idx):
        if self._dnd_ghost:
            self._dnd_ghost.destroy()
        photo = self.thumb_images[idx]
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes('-alpha', 0.6)
        ghost.attributes('-topmost', True)
        lbl = tk.Label(ghost, image=photo, bg=BG_CARD,
                       relief='flat', bd=2)
        lbl.pack()
        num = tk.Label(ghost, text=f'p.{idx+1}', bg=BG_CARD,
                       fg=ACCENT, font=('Segoe UI', 8, 'bold'))
        num.pack()
        self._dnd_ghost = ghost

    def _dnd_move_ghost(self, event):
        if self._dnd_ghost:
            self._dnd_ghost.geometry(f'+{event.x_root+12}+{event.y_root+8}')

    def _dnd_destroy_ghost(self):
        if self._dnd_ghost:
            self._dnd_ghost.destroy()
            self._dnd_ghost = None

    def _dnd_show_indicator(self, event):
        self._dnd_clear_indicator()
        dest = self._dnd_dest_index(event)
        if dest is None:
            return
        frames = self.thumb_inner.winfo_children()
        if not frames:
            return
        if dest < len(frames):
            fr = frames[dest]
        else:
            fr = frames[-1]
        fr.update_idletasks()
        fy = fr.winfo_y()
        fh = fr.winfo_height()
        y = fy if dest < len(frames) else fy + fh
        cw = self.thumb_canvas.winfo_width()
        self._dnd_indicator = self.thumb_canvas.create_line(
            4, y, cw - 4, y,
            fill=ACCENT, width=3, dash=(6, 3))

    def _dnd_clear_indicator(self):
        if self._dnd_indicator:
            self.thumb_canvas.delete(self._dnd_indicator)
            self._dnd_indicator = None

    def _dnd_dest_index(self, event):
        """マウス位置から挿入先を計算 (#4 バウンダリチェック強化)"""
        frames = self.thumb_inner.winfo_children()
        if not frames:
            return None
        canvas_y = event.y_root - self.thumb_canvas.winfo_rooty()
        cy = self.thumb_canvas.canvasy(canvas_y)
        first_y = frames[0].winfo_y()
        last_frame = frames[-1]
        last_bottom = last_frame.winfo_y() + last_frame.winfo_height()
        if cy < first_y:
            return 0
        if cy > last_bottom:
            return len(frames)
        for i, fr in enumerate(frames):
            fy = fr.winfo_y()
            fh = fr.winfo_height()
            if cy < fy + fh / 2:
                return i
        return len(frames)

    def _dnd_drop(self, event):
        src = self._dnd_src_idx
        dest = self._dnd_dest_index(event)
        if dest is None or src is None:
            return
        n = len(self.doc)
        dest = min(dest, n - 1)
        if dest == src:
            return
        self._save_undo()
        self.doc.move_page(src, dest)
        self.current_page = dest
        self.selected_pages.clear()
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(f'p.{src+1} → p.{dest+1} に移動しました')

    # ══════════════════════════════════════════
    #  ユーティリティ
    # ══════════════════════════════════════════
    def _check_doc(self):
        if not self.doc:
            messagebox.showinfo("情報", "先にPDFファイルを開いてください")
            return False
        return True

    def _get_targets(self):
        return list(self.selected_pages) if self.selected_pages else [self.current_page]

    def _quit(self):
        if self.doc:
            if messagebox.askyesno('確認',
                    'アプリを終了しますか？\n（未保存の変更は失われます）'):
                self.doc.close()
                self.root.destroy()
        else:
            self.root.destroy()

    def _set_status(self, msg):
        self.status_var.set(msg)


# ══════════════════════════════════════════
#  結合順ダイアログ (#3 ページ数キャッシュ)
# ══════════════════════════════════════════
class MergeOrderDialog(tk.Toplevel):
    def __init__(self, parent, paths, callback):
        super().__init__(parent)
        self.title("結合順の確認・変更")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)
        self.grab_set()

        self.paths = paths
        self.callback = callback

        # ページ数を初回のみ取得してキャッシュ (#3)
        self._page_counts = {}
        for p in paths:
            try:
                d = fitz.open(p)
                self._page_counts[p] = len(d)
                d.close()
            except Exception:
                self._page_counts[p] = 0

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = 480, 420
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")

    def _build(self):
        tk.Label(self, text="結合順の確認・並び替え",
                 bg=BG_DARK, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(pady=(14, 4))
        tk.Label(self,
                 text="ファイルを選択して ▲▼ で順番を変更できます\n"
                      "確定すると現在のPDFの末尾に順番通り結合されます",
                 bg=BG_DARK, fg=TEXT_SUB,
                 font=("Segoe UI", 9), justify="center").pack(pady=(0, 8))

        list_frame = tk.Frame(self, bg=BG_PANEL, bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=sb.set,
            bg=BG_CARD, fg=TEXT_MAIN,
            selectbackground=ACCENT, selectforeground="#fff",
            font=("Segoe UI", 9),
            activestyle="none",
            bd=0, highlightthickness=0,
            height=12)
        sb.configure(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)

        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")

        btn_row = tk.Frame(self, bg=BG_DARK)
        btn_row.pack(fill="x", padx=16, pady=6)
        ttk.Button(btn_row, text="▲ 上へ",
                   command=self._move_up).pack(side="left", padx=4)
        ttk.Button(btn_row, text="▼ 下へ",
                   command=self._move_down).pack(side="left", padx=4)
        ttk.Button(btn_row, text="✕ 削除",
                   style="Danger.TButton",
                   command=self._remove_item).pack(side="left", padx=4)

        self.info_var = tk.StringVar()
        tk.Label(self, textvariable=self.info_var,
                 bg=BG_DARK, fg=SUCCESS,
                 font=("Segoe UI", 9)).pack(pady=2)
        self._update_info()

        ok_row = tk.Frame(self, bg=BG_DARK)
        ok_row.pack(pady=(4, 14))
        ttk.Button(ok_row, text="✔ この順番で結合",
                   style="Accent.TButton",
                   command=self._confirm).pack(side="left", padx=8)
        ttk.Button(ok_row, text="キャンセル",
                   command=self.destroy).pack(side="left", padx=8)

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.paths[i-1], self.paths[i] = self.paths[i], self.paths[i-1]
        self._reload_list(i-1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.paths)-1:
            return
        i = sel[0]
        self.paths[i], self.paths[i+1] = self.paths[i+1], self.paths[i]
        self._reload_list(i+1)

    def _remove_item(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self.paths.pop(i)
        self._reload_list(max(0, i-1))

    def _reload_list(self, select_idx=None):
        self.listbox.delete(0, tk.END)
        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")
        if select_idx is not None and self.paths:
            self.listbox.selection_set(select_idx)
            self.listbox.see(select_idx)
        self._update_info()

    def _update_info(self):
        total = sum(self._page_counts.get(p, 0) for p in self.paths)
        self.info_var.set(f"合計 {len(self.paths)} ファイル  /  {total} ページ")

    def _confirm(self):
        if not self.paths:
            messagebox.showinfo("情報", "ファイルがありません", parent=self)
            return
        self.destroy()
        self.callback(self.paths)


# ─────────────────────────────────────────
#  ファイルD&D (#22)
# ─────────────────────────────────────────
def _setup_file_drop(root, app):
    """windnd による D&D。未インストール時はスキップ。"""
    try:
        import windnd
        def on_drop(files):
            for f in files:
                path = f.decode('utf-8') if isinstance(f, bytes) else f
                if path.lower().endswith('.pdf'):
                    app._open_pdf_path(path)
                    break
        windnd.hook_dropfiles(root, func=on_drop)
    except ImportError:
        pass


# ─────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditorApp(root)
    _setup_file_drop(root, app)
    root.mainloop()
