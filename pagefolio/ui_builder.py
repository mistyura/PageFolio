# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""UI構築 Mixin — スタイル定義・レイアウト構築"""

import tkinter as tk
from tkinter import ttk

from pagefolio.constants import C


class UIBuilderMixin:
    """PDFEditorApp のUI構築メソッド群"""

    def _build_styles(self):
        fs = self.font_size
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=C["BG_DARK"])
        style.configure("Panel.TFrame", background=C["BG_PANEL"])
        style.configure("Card.TFrame", background=C["BG_CARD"])
        style.configure(
            "TLabel",
            background=C["BG_DARK"],
            foreground=C["TEXT_MAIN"],
            font=("Segoe UI", fs),
        )
        style.configure(
            "Title.TLabel",
            background=C["BG_DARK"],
            foreground=C["ACCENT"],
            font=("Segoe UI", fs + 8, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=C["BG_DARK"],
            foreground=C["TEXT_SUB"],
            font=("Segoe UI", fs - 1),
        )
        style.configure(
            "Status.TLabel",
            background=C["BG_PANEL"],
            foreground=C["SUCCESS"],
            font=("Segoe UI", fs - 1),
        )
        style.configure(
            "TButton",
            background=C["BG_CARD"],
            foreground=C["TEXT_MAIN"],
            font=("Segoe UI", fs - 1, "bold"),
            borderwidth=0,
            padding=(10, 6),
        )
        style.map(
            "TButton",
            background=[("active", C["ACCENT"]), ("pressed", C["ACCENT2"])],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "Accent.TButton",
            background=C["ACCENT"],
            foreground="#ffffff",
            font=("Segoe UI", fs, "bold"),
            borderwidth=0,
            padding=(12, 7),
        )
        style.map("Accent.TButton", background=[("active", C["BTN_HOVER"])])
        style.configure(
            "Danger.TButton",
            background=C["DANGER_BG"],
            foreground=C["DANGER_FG"],
            font=("Segoe UI", fs - 1, "bold"),
            borderwidth=0,
            padding=(10, 6),
        )
        style.map("Danger.TButton", background=[("active", C["ACCENT"])])
        style.configure(
            "CropOn.TButton",
            background=C["CROP_ON_BG"],
            foreground="#ffffff",
            font=("Segoe UI", fs - 1, "bold"),
            borderwidth=2,
            padding=(10, 6),
        )
        style.map("CropOn.TButton", background=[("active", "#aa0000")])
        style.configure(
            "TScrollbar",
            background=C["BG_CARD"],
            troughcolor=C["BG_PANEL"],
            borderwidth=0,
            arrowsize=12,
        )
        style.configure(
            "Horizontal.TScale", background=C["BG_DARK"], troughcolor=C["BG_CARD"]
        )

    def _build_ui(self):

        header_h = max(60, int(self.font_size * 5.5))
        header = tk.Frame(self.root, bg=C["BG_PANEL"], height=header_h)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="✦ PageFolio",
            bg=C["BG_PANEL"],
            fg=C["ACCENT"],
            font=self._font(6, "bold"),
        ).pack(side="left", padx=20, pady=12)

        # 閲覧/編集モード切替ボタン
        mode_style = "Accent.TButton" if self.edit_mode else "TButton"
        mode_text = (
            self._t("mode_edit_label") if self.edit_mode else self._t("mode_view_label")
        )
        self._mode_btn = ttk.Button(
            header,
            text=mode_text,
            style=mode_style,
            command=self._toggle_edit_mode,
        )
        self._mode_btn.pack(side="left", padx=16, pady=12)

        self.status_var = tk.StringVar(value=self._t("status_initial"))
        tk.Label(
            header,
            textvariable=self.status_var,
            bg=C["BG_PANEL"],
            fg=C["SUCCESS"],
            font=self._font(-1),
        ).pack(side="right", padx=20)

        self._paned = tk.PanedWindow(
            self.root,
            orient="horizontal",
            bg=C["BG_DARK"],
            sashwidth=5,
            sashrelief="flat",
            opaqueresize=True,
            bd=0,
        )
        self._paned.pack(fill="both", expand=True)

        left_width = max(170, int(self.font_size * 15))
        left = tk.Frame(self._paned, bg=C["BG_PANEL"])
        self._build_thumb_panel(left)
        self._paned.add(left, minsize=130, width=left_width)

        center = tk.Frame(self._paned, bg=C["BG_DARK"])
        self._build_preview(center)
        self._paned.add(center, minsize=300)

        # 右パネル（ツール）— 常時表示
        self._right_panel = tk.Frame(self._paned, bg=C["BG_PANEL"])
        self._build_tools_scrollable(self._right_panel)
        self._paned.add(self._right_panel, minsize=220)

        def _set_sash():
            self._paned.update_idletasks()
            total = self._paned.winfo_width()
            if total <= 100:
                return
            left_pos = self.settings.get("sash_left", int(total * 0.15))
            right_pos = self.settings.get("sash_right", int(total * 0.77))
            left_pos = max(100, min(left_pos, total - 450))
            right_pos = max(left_pos + 200, min(right_pos, total - 220))
            self._paned.sash_place(0, left_pos, 0)
            self._paned.sash_place(1, right_pos, 0)

        self.root.after(200, _set_sash)

    def _build_thumb_panel(self, parent):
        hdr = tk.Frame(parent, bg=C["BG_PANEL"])
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(
            hdr,
            text=self._t("panel_pages"),
            bg=C["BG_PANEL"],
            fg=C["ACCENT"],
            font=self._font(0, "bold"),
        ).pack(side="left")
        tk.Label(
            hdr,
            text=self._t("dnd_hint"),
            bg=C["BG_PANEL"],
            fg=C["TEXT_SUB"],
            font=self._font(-3),
        ).pack(side="right")

        sel_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        sel_frame.pack(fill="x", padx=6, pady=2)
        ttk.Button(
            sel_frame, text=self._t("select_all"), command=self._select_all
        ).pack(side="left", padx=2)
        ttk.Button(
            sel_frame, text=self._t("deselect"), command=self._deselect_all
        ).pack(side="left", padx=2)

        canvas_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.thumb_canvas = tk.Canvas(
            canvas_frame, bg=C["BG_PANEL"], highlightthickness=0
        )
        sb = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=self.thumb_canvas.yview
        )
        self.thumb_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.thumb_canvas.pack(fill="both", expand=True)

        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=C["BG_PANEL"])
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor="nw")
        self.thumb_inner.bind(
            "<Configure>",
            lambda e: self.thumb_canvas.configure(
                scrollregion=self.thumb_canvas.bbox("all")
            ),
        )
        self.thumb_canvas.bind(
            "<MouseWheel>",
            lambda e: self.thumb_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )

    def _build_preview(self, parent):
        toolbar_h = max(52, int(self.font_size * 4.5))
        toolbar = tk.Frame(parent, bg=C["BG_PANEL"], height=toolbar_h)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self.prev_btn = ttk.Button(
            toolbar, text=self._t("btn_prev"), command=self._prev_page, width=4
        )
        self.prev_btn.pack(side="left", padx=(10, 2), pady=6)
        self.page_label = tk.Label(
            toolbar,
            text="- / -",
            bg=C["BG_PANEL"],
            fg=C["TEXT_MAIN"],
            font=self._font(0, "bold"),
            width=8,
        )
        self.page_label.pack(side="left", padx=4)
        self.next_btn = ttk.Button(
            toolbar, text=self._t("btn_next"), command=self._next_page, width=4
        )
        self.next_btn.pack(side="left", padx=(2, 10))

        ttk.Button(
            toolbar,
            text=self._t("btn_zoom_out"),
            command=lambda: self._zoom(-0.2),
            width=4,
        ).pack(side="right", padx=(2, 10), pady=6)
        ttk.Button(
            toolbar,
            text=self._t("btn_zoom_in"),
            command=lambda: self._zoom(0.2),
            width=4,
        ).pack(side="right", padx=2)
        self.zoom_label = tk.Label(
            toolbar,
            text="100%",
            bg=C["BG_PANEL"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            width=6,
        )
        self.zoom_label.pack(side="right", padx=6)

        frame = tk.Frame(parent, bg=C["BG_DARK"])
        frame.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(frame, bg=C["PREVIEW_BG"], highlightthickness=0)
        vbar = ttk.Scrollbar(
            frame, orient="vertical", command=self.preview_canvas.yview
        )
        hbar = ttk.Scrollbar(
            frame, orient="horizontal", command=self.preview_canvas.xview
        )
        self.preview_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind(
            "<MouseWheel>",
            lambda e: self.preview_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )
        self.preview_canvas.bind("<ButtonPress-1>", self._crop_drag_start)
        self.preview_canvas.bind("<B1-Motion>", self._crop_drag_move)
        self.preview_canvas.bind("<ButtonRelease-1>", self._crop_drag_end)
        self.zoom = 1.0
        self.preview_img_ref = None
        self.crop_rect_id = None
        self.crop_overlay_ids = []

    def _build_tools_scrollable(self, parent):
        """右ペインをスクロール可能にするラッパー"""
        canvas = tk.Canvas(parent, bg=C["BG_PANEL"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["BG_PANEL"])
        canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner_window")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure("inner_window", width=canvas.winfo_width())

        inner.bind("<Configure>", _on_configure)
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure("inner_window", width=e.width),
        )
        canvas.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        def _bind_mousewheel_recursive(widget):
            widget.bind(
                "<MouseWheel>",
                lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
                add="+",
            )
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)

        self._build_tools(inner)

        def _after_build():
            _bind_mousewheel_recursive(inner)
            canvas.yview_moveto(0)

        inner.after(100, _after_build)

    def _build_tools(self, parent):
        from pagefolio.dialogs import AboutDialog

        self._doc_buttons = []
        self._edit_only_buttons = []

        def section(title):
            f = tk.Frame(parent, bg=C["BG_CARD"], bd=0)
            f.pack(fill="x", padx=10, pady=5)
            tk.Label(
                f,
                text=title,
                bg=C["BG_CARD"],
                fg=C["WARNING"],
                font=self._font(-1, "bold"),
            ).pack(anchor="w", padx=8, pady=(6, 2))
            return f

        def btn(parent, text, cmd, style="TButton", needs_doc=False, edit_only=False):
            b = ttk.Button(parent, text=text, command=cmd, style=style)
            b.pack(fill="x", padx=8, pady=2)
            if needs_doc:
                self._doc_buttons.append(b)
            if edit_only:
                self._edit_only_buttons.append(b)
            return b

        f5 = section(self._t("sec_settings"))
        btn(f5, self._t("btn_settings"), self._open_settings)
        btn(
            f5,
            self._t("btn_about"),
            lambda: AboutDialog(self.root, self._font, self.lang),
        )
        btn(f5, self._t("btn_lang"), self._toggle_lang)

        f = section(self._t("sec_file"))
        btn(f, self._t("btn_open"), self._open_file, "Accent.TButton")
        btn(f, self._t("btn_save"), self._save_file, needs_doc=True, edit_only=True)
        btn(f, self._t("btn_save_as"), self._save_as, needs_doc=True, edit_only=True)
        btn(
            f,
            self._t("btn_save_compressed"),
            self._save_compressed,
            needs_doc=True,
            edit_only=True,
        )
        btn(f, self._t("btn_quit"), self._quit, "Danger.TButton")

        f_ur = section(self._t("sec_undo"))
        ur_row = tk.Frame(f_ur, bg=C["BG_CARD"])
        ur_row.pack(fill="x", padx=6, pady=2)
        b_undo = ttk.Button(ur_row, text=self._t("btn_undo"), command=self._undo)
        b_undo.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self._doc_buttons.append(b_undo)
        self._edit_only_buttons.append(b_undo)
        b_redo = ttk.Button(ur_row, text=self._t("btn_redo"), command=self._redo)
        b_redo.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self._doc_buttons.append(b_redo)
        self._edit_only_buttons.append(b_redo)

        f2 = section(self._t("sec_page"))
        tk.Label(
            f2,
            text=self._t("lbl_rotate"),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=8)
        rot_row1 = tk.Frame(f2, bg=C["BG_CARD"])
        rot_row1.pack(fill="x", padx=6, pady=(2, 0))
        for deg, lkey in [(270, "btn_rot_left"), (90, "btn_rot_right")]:
            b = ttk.Button(
                rot_row1,
                text=self._t(lkey),
                command=lambda d=deg: self._rotate_selected(d),
            )
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            self._doc_buttons.append(b)
            self._edit_only_buttons.append(b)
        rot_row2 = tk.Frame(f2, bg=C["BG_CARD"])
        rot_row2.pack(fill="x", padx=6, pady=(0, 2))
        b180 = ttk.Button(
            rot_row2,
            text=self._t("btn_rot_180"),
            command=lambda: self._rotate_selected(180),
        )
        b180.pack(fill="x", padx=2, pady=2)
        self._doc_buttons.append(b180)
        self._edit_only_buttons.append(b180)

        btn(
            f2,
            self._t("btn_delete"),
            self._delete_selected,
            "Danger.TButton",
            needs_doc=True,
            edit_only=True,
        )
        btn(
            f2,
            self._t("btn_duplicate"),
            self._duplicate_page,
            needs_doc=True,
            edit_only=True,
        )

        f3 = section(self._t("sec_crop"))
        self.crop_mode_var = tk.BooleanVar(value=False)
        self.crop_toggle_btn = ttk.Button(
            f3, text=self._t("crop_mode_off"), command=self._toggle_crop_mode
        )
        self.crop_toggle_btn.pack(fill="x", padx=8, pady=(4, 2))
        self._doc_buttons.append(self.crop_toggle_btn)
        self._edit_only_buttons.append(self.crop_toggle_btn)
        tk.Label(
            f3,
            text=self._t("crop_hint"),
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=8)

        self.crop_info_var = tk.StringVar(value=self._t("crop_no_sel"))
        tk.Label(
            f3,
            textvariable=self.crop_info_var,
            bg=C["BG_CARD"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=8, pady=2)

        btn(f3, self._t("btn_crop"), self._crop_page, needs_doc=True, edit_only=True)
        btn(
            f3,
            self._t("btn_crop_reset"),
            self._crop_reset,
            "Danger.TButton",
            needs_doc=True,
            edit_only=True,
        )

        f4 = section(self._t("sec_insert"))
        btn(
            f4,
            self._t("btn_insert_head"),
            lambda: self._insert_from_file("head"),
            needs_doc=True,
            edit_only=True,
        )
        btn(
            f4,
            self._t("btn_insert_tail"),
            lambda: self._insert_from_file("tail"),
            needs_doc=True,
            edit_only=True,
        )
        btn(
            f4,
            self._t("btn_insert_pos"),
            lambda: self._insert_from_file("pos"),
            needs_doc=True,
            edit_only=True,
        )
        btn(f4, self._t("btn_merge"), self._merge_pdf, needs_doc=True, edit_only=True)

        f5_split = section(self._t("sec_split"))
        btn(
            f5_split,
            self._t("btn_split_range"),
            self._split_by_range,
            needs_doc=True,
            edit_only=True,
        )
        btn(
            f5_split,
            self._t("btn_split_each"),
            self._split_each_page,
            needs_doc=True,
            edit_only=True,
        )

        f_plug = section(self._t("sec_plugin"))
        btn(f_plug, self._t("btn_plugin_mgr"), self._open_plugin_dialog)
        self._plugin_ui_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        self._plugin_ui_frame.pack(fill="x", padx=0, pady=0)
        self._build_plugin_ui()

        self._update_doc_buttons_state()
        self._update_edit_buttons_state()
