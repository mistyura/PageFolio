# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""プラグイン管理ダイアログ"""

import logging
import os
import tkinter as tk
from tkinter import ttk

from pagefolio.constants import C, LANG, PLUGINS_DIR
from pagefolio.plugins import _get_plugins_dir

logger = logging.getLogger(__name__)


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
