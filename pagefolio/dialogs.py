# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ダイアログ — About, Settings, Plugin, MergeOrder"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

import fitz

from pagefolio.constants import APP_VERSION, LANG, PLUGINS_DIR, C
from pagefolio.plugins import _get_plugins_dir
from pagefolio.settings import _current_font_size


# ══════════════════════════════════════════
#  About ダイアログ
# ══════════════════════════════════════════
class AboutDialog(tk.Toplevel):
    def __init__(self, parent, font_func, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["about_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self._font = font_func
        self._build()
        self.update_idletasks()
        w = 360
        h = max(300, self.winfo_reqheight() + 20)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text="PageFolio",
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(20, 2))
        tk.Label(
            self,
            text=APP_VERSION,
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(0),
        ).pack()
        tk.Label(
            self,
            text=self._L["about_subtitle"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(pady=(2, 12))

        sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
        sep.pack(fill="x", padx=30, pady=4)

        tk.Label(
            self,
            text="Copyright (c) 2026 mistyura",
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(pady=(6, 2))
        tk.Label(
            self,
            text="MIT License",
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack()
        tk.Label(
            self,
            text="https://github.com/mistyura/PageFolio",
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
        ).pack(pady=(2, 16))

        ttk.Button(
            self, text=self._L["about_ok"], command=self.destroy, style="Accent.TButton"
        ).pack(pady=(0, 16))


# ══════════════════════════════════════════
#  設定ダイアログ
# ══════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_settings, callback, font_func=None):
        super().__init__(parent)
        lang = current_settings.get("lang", "ja")
        self._L = LANG[lang]
        self.title(self._L["settings_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.callback = callback
        self.current_settings = dict(current_settings)
        self._font = font_func

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = current_settings.get("font_size", 12)
        w = max(380, int(fs * 32))
        h = max(280, int(fs * 24))
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text=self._L["settings_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        tf = tk.Frame(self, bg=C["BG_DARK"])
        tf.pack(fill="x", padx=24, pady=6)
        tk.Label(
            tf,
            text=self._L["settings_theme"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.theme_var = tk.StringVar(value=self.current_settings.get("theme", "dark"))
        theme_options = [
            (self._L["settings_theme_dark"], "dark"),
            (self._L["settings_theme_light"], "light"),
            (self._L["settings_theme_system"], "system"),
        ]
        for text, value in theme_options:
            tk.Radiobutton(
                tf,
                text=text,
                variable=self.theme_var,
                value=value,
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                selectcolor=C["BG_CARD"],
                activebackground=C["BG_DARK"],
                activeforeground=C["TEXT_MAIN"],
                font=self._font(-1),
            ).pack(side="left", padx=6)

        ff = tk.Frame(self, bg=C["BG_DARK"])
        ff.pack(fill="x", padx=24, pady=6)
        tk.Label(
            ff,
            text=self._L["settings_font"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.font_var = tk.IntVar(value=self.current_settings.get("font_size", 10))
        tk.Spinbox(
            ff,
            from_=8,
            to=16,
            textvariable=self.font_var,
            width=4,
            font=self._font(0),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=8)
        tk.Label(
            ff,
            text=self._L["settings_font_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
        ).pack(side="left")

        self.preview_label = tk.Label(
            self,
            text=self._L["settings_preview_text"],
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            font=("Segoe UI", self.font_var.get()),
            padx=12,
            pady=8,
        )
        self.preview_label.pack(padx=24, pady=8, fill="x")
        self.font_var.trace_add("write", self._update_preview)

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["settings_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(btn_row, text=self._L["settings_cancel"], command=self.destroy).pack(
            side="left", padx=8
        )

    def _update_preview(self, *_):
        try:
            size = self.font_var.get()
            size = max(8, min(16, size))
            self.preview_label.configure(font=("Segoe UI", size))
        except Exception:  # noqa: S110
            pass

    def _apply(self):
        new_settings = dict(self.current_settings)
        new_settings["theme"] = self.theme_var.get()
        new_settings["font_size"] = max(8, min(16, self.font_var.get()))
        self.destroy()
        self.callback(new_settings)


# ══════════════════════════════════════════
#  プラグイン管理ダイアログ
# ══════════════════════════════════════════
class PluginDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self._L = LANG[app.lang]
        self.title(self._L["plugin_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(True, True)
        self.grab_set()

        self.app = app
        self.pm = app.plugin_manager
        self._font_size = app.font_size

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = self._font_size
        w = max(500, int(fs * 42))
        h = max(400, int(fs * 30))
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(420, 340)

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        tk.Label(
            self,
            text=self._L["plugin_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))

        plugins_dir = _get_plugins_dir()
        tk.Label(
            self,
            text=self._L["plugin_dir_label"].format(path=plugins_dir),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
            wraplength=450,
        ).pack(pady=(0, 8))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        canvas = tk.Canvas(list_frame, bg=C["BG_PANEL"], highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self._list_inner = tk.Frame(canvas, bg=C["BG_PANEL"])
        canvas.create_window((0, 0), window=self._list_inner, anchor="nw", tags="inner")
        self._list_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all"),
            ),
        )
        canvas.bind(
            "<Configure>", lambda e: canvas.itemconfigure("inner", width=e.width)
        )
        self._list_canvas = canvas

        self._refresh_list()

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(8, 4))
        ttk.Button(btn_row, text=self._L["plugin_rescan"], command=self._rescan).pack(
            side="left", padx=4
        )
        ttk.Button(
            btn_row, text=self._L["plugin_open_folder"], command=self._open_folder
        ).pack(side="left", padx=4)

        ok_row = tk.Frame(self, bg=C["BG_DARK"])
        ok_row.pack(pady=(4, 14))
        ttk.Button(
            ok_row,
            text=self._L["plugin_close"],
            style="Accent.TButton",
            command=self._close,
        ).pack(side="left", padx=8)

    def _refresh_list(self):
        for w in self._list_inner.winfo_children():
            w.destroy()

        all_plugins = self.pm.all_plugins
        if not all_plugins:
            tk.Label(
                self._list_inner,
                text=self._L["plugin_empty"].format(dir=PLUGINS_DIR),
                bg=C["BG_PANEL"],
                fg=C["TEXT_SUB"],
                font=self._font(),
                justify="center",
            ).pack(pady=30)
            return

        self._check_vars = {}
        for plugin_id, plugin in all_plugins.items():
            row = tk.Frame(self._list_inner, bg=C["BG_CARD"], bd=0)
            row.pack(fill="x", padx=6, pady=3)

            var = tk.BooleanVar(value=self.pm.is_enabled(plugin_id))
            self._check_vars[plugin_id] = var

            cb = tk.Checkbutton(
                row,
                variable=var,
                command=lambda pid=plugin_id: self._toggle(pid),
                bg=C["BG_CARD"],
                activebackground=C["BG_CARD"],
                selectcolor=C["BG_PANEL"],
            )
            cb.pack(side="left", padx=(8, 4), pady=6)

            info = tk.Frame(row, bg=C["BG_CARD"])
            info.pack(side="left", fill="x", expand=True, pady=4)

            name_text = f"{plugin.name}  v{plugin.version}"
            tk.Label(
                info,
                text=name_text,
                bg=C["BG_CARD"],
                fg=C["TEXT_MAIN"],
                font=self._font(0, "bold"),
                anchor="w",
            ).pack(anchor="w")

            if plugin.description:
                tk.Label(
                    info,
                    text=plugin.description,
                    bg=C["BG_CARD"],
                    fg=C["TEXT_SUB"],
                    font=self._font(-2),
                    anchor="w",
                    wraplength=350,
                ).pack(anchor="w")

            if plugin.author:
                author_txt = self._L["plugin_author"].format(
                    author=plugin.author,
                )
                tk.Label(
                    info,
                    text=author_txt,
                    bg=C["BG_CARD"],
                    fg=C["TEXT_SUB"],
                    font=self._font(-2),
                    anchor="w",
                ).pack(anchor="w")

    def _toggle(self, plugin_id):
        if self._check_vars[plugin_id].get():
            self.pm.enable_plugin(plugin_id, self.app)
        else:
            self.pm.disable_plugin(plugin_id, self.app)
        self.app._reload_plugins()

    def _rescan(self):
        """プラグインを再検出・再読み込みする"""
        for pid in list(self.pm.all_plugins.keys()):
            self.pm.unload_plugin(pid, self.app)
        disabled = self.app.settings.get("disabled_plugins", [])
        self.pm.load_all(app=self.app, disabled_ids=disabled)
        self._refresh_list()
        self.app._reload_plugins()

    def _open_folder(self):
        """プラグインフォルダを作成して開く"""
        plugins_dir = _get_plugins_dir()
        os.makedirs(plugins_dir, exist_ok=True)
        try:
            os.startfile(plugins_dir)  # noqa: S606
        except AttributeError:
            import subprocess

            subprocess.Popen(["xdg-open", plugins_dir])  # noqa: S603, S607

    def _close(self):
        self.app._reload_plugins()
        self.destroy()


# ══════════════════════════════════════════
#  結合順ダイアログ
# ══════════════════════════════════════════
class MergeOrderDialog(tk.Toplevel):
    def __init__(self, parent, paths, callback, lang="ja"):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["merge_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(True, True)
        self.grab_set()

        self.paths = paths
        self.callback = callback
        self._font_size = _current_font_size

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
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = self._font_size
        w = max(480, int(fs * 40))
        base_h = max(420, int(fs * 32))
        extra_h = max(0, len(self.paths) - 4) * int(fs * 2.5)
        h = min(base_h + extra_h, parent.winfo_height() - 40)
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(400, 350)

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        tk.Label(
            self,
            text=self._L["merge_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))
        tk.Label(
            self,
            text=self._L["merge_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="center",
        ).pack(pady=(0, 8))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        list_height = max(6, min(20, len(self.paths) + 2))
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=sb.set,
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            selectbackground=C["ACCENT"],
            selectforeground="#fff",
            font=self._font(-1),
            activestyle="none",
            bd=0,
            highlightthickness=0,
            height=list_height,
        )
        sb.configure(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)

        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=6)
        ttk.Button(btn_row, text=self._L["merge_up"], command=self._move_up).pack(
            side="left", padx=4
        )
        ttk.Button(btn_row, text=self._L["merge_down"], command=self._move_down).pack(
            side="left", padx=4
        )
        ttk.Button(
            btn_row,
            text=self._L["merge_remove"],
            style="Danger.TButton",
            command=self._remove_item,
        ).pack(side="left", padx=4)

        self.info_var = tk.StringVar()
        tk.Label(
            self,
            textvariable=self.info_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-1),
        ).pack(pady=2)
        self._update_info()

        ok_row = tk.Frame(self, bg=C["BG_DARK"])
        ok_row.pack(pady=(4, 14))
        ttk.Button(
            ok_row,
            text=self._L["merge_confirm"],
            style="Accent.TButton",
            command=self._confirm,
        ).pack(side="left", padx=8)
        ttk.Button(ok_row, text=self._L["merge_cancel"], command=self.destroy).pack(
            side="left", padx=8
        )

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.paths[i - 1], self.paths[i] = self.paths[i], self.paths[i - 1]
        self._reload_list(i - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.paths) - 1:
            return
        i = sel[0]
        self.paths[i], self.paths[i + 1] = self.paths[i + 1], self.paths[i]
        self._reload_list(i + 1)

    def _remove_item(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self.paths.pop(i)
        self._reload_list(max(0, i - 1))

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
        info_txt = self._L["merge_info"].format(
            count=len(self.paths),
            total=total,
        )
        self.info_var.set(info_txt)

    def _confirm(self):
        if not self.paths:
            messagebox.showinfo(
                self._L.get("info_title", "Info"),
                self._L["merge_no_files"],
                parent=self,
            )
            return
        self.destroy()
        self.callback(self.paths)
