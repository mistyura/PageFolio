# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ダイアログ — About, Settings, Plugin, MergeOrder"""

import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk

import fitz

from pagefolio.constants import APP_VERSION, LANG, PLUGINS_DIR, C
from pagefolio.ocr import fetch_lm_studio_models
from pagefolio.plugins import _get_plugins_dir
from pagefolio.settings import _current_font_size

logger = logging.getLogger(__name__)


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
        w = max(460, int(fs * 38))
        h = max(320, int(fs * 24))
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

        # ── LM Studio (OCR) セクション ──
        sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
        sep.pack(fill="x", padx=24, pady=(8, 4))
        tk.Label(
            self,
            text=self._L["settings_lm_studio_section"],
            bg=C["BG_DARK"],
            fg=C["WARNING"],
            font=self._font(0, "bold"),
        ).pack(anchor="w", padx=24, pady=(4, 2))

        ttk.Button(
            self,
            text=self._L["settings_open_llm_config"],
            command=self._open_llm_config,
        ).pack(anchor="w", padx=24, pady=(2, 8))

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
        except Exception as e:
            logger.debug("フォントプレビュー更新失敗: %s", e)

    def _open_llm_config(self):
        """LLM 設定ダイアログを開き、適用時に current_settings を更新する"""
        lang = self.current_settings.get("lang", "ja")

        def on_apply(llm_settings):
            self.current_settings.update(llm_settings)

        LLMConfigDialog(
            self,
            self.current_settings,
            on_apply=on_apply,
            font_func=self._font,
            lang=lang,
        )

    def _apply(self):
        new_settings = dict(self.current_settings)
        new_settings["theme"] = self.theme_var.get()
        new_settings["font_size"] = max(8, min(16, self.font_var.get()))
        self.destroy()
        self.callback(new_settings)


# ══════════════════════════════════════════
#  LLM 設定ダイアログ（OCR と設定で共有）
# ══════════════════════════════════════════
class LLMConfigDialog(tk.Toplevel):
    """LM Studio の URL・モデル・OCR 解像度倍率・タイムアウトを編集する共通ダイアログ"""

    def __init__(
        self,
        parent,
        current_settings,
        on_apply,
        font_func=None,
        lang="ja",
    ):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["llm_config_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.current_settings = dict(current_settings)
        self.on_apply = on_apply
        self._font = font_func or (
            lambda d=0, w=None: (
                ("Segoe UI", max(7, 10 + d), w) if w else ("Segoe UI", max(7, 10 + d))
            )
        )

        self._build()
        self.update_idletasks()
        fs = _current_font_size()
        w = max(460, int(fs * 38))
        h = max(360, self.winfo_reqheight() + 20)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    def _build(self):
        tk.Label(
            self,
            text=self._L["llm_config_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        # URL
        url_row = tk.Frame(self, bg=C["BG_DARK"])
        url_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            url_row,
            text=self._L["settings_lm_url"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=14,
            anchor="w",
        ).pack(side="left")
        self.lm_url_var = tk.StringVar(
            value=self.current_settings.get("lm_studio_url", "http://localhost:1234"),
        )
        tk.Entry(
            url_row,
            textvariable=self.lm_url_var,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            insertbackground=C["TEXT_MAIN"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=4)

        # モデル
        model_row = tk.Frame(self, bg=C["BG_DARK"])
        model_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            model_row,
            text=self._L["settings_lm_model"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=14,
            anchor="w",
        ).pack(side="left")
        self.lm_model_var = tk.StringVar(
            value=self.current_settings.get("lm_studio_model", ""),
        )
        self.lm_model_combo = ttk.Combobox(
            model_row,
            textvariable=self.lm_model_var,
            font=self._font(-1),
            values=[],
        )
        self.lm_model_combo.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(
            self,
            text=self._L["settings_lm_model_hint"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-2),
        ).pack(anchor="w", padx=24)

        # 解像度倍率
        scale_row = tk.Frame(self, bg=C["BG_DARK"])
        scale_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(
            scale_row,
            text=self._L["settings_ocr_scale"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_scale_var = tk.DoubleVar(
            value=float(self.current_settings.get("ocr_scale", 2.0)),
        )
        tk.Spinbox(
            scale_row,
            from_=1.0,
            to=4.0,
            increment=0.5,
            textvariable=self.ocr_scale_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)

        # タイムアウト
        to_row = tk.Frame(self, bg=C["BG_DARK"])
        to_row.pack(fill="x", padx=24, pady=2)
        tk.Label(
            to_row,
            text=self._L["settings_ocr_timeout"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
            width=20,
            anchor="w",
        ).pack(side="left")
        self.ocr_timeout_var = tk.IntVar(
            value=int(self.current_settings.get("ocr_timeout", 120)),
        )
        tk.Spinbox(
            to_row,
            from_=10,
            to=600,
            increment=10,
            textvariable=self.ocr_timeout_var,
            width=6,
            font=self._font(-1),
            bg=C["BG_CARD"],
            fg=C["TEXT_MAIN"],
            buttonbackground=C["BG_PANEL"],
            insertbackground=C["TEXT_MAIN"],
        ).pack(side="left", padx=4)

        # 接続テスト・モデル取得
        lm_btn_row = tk.Frame(self, bg=C["BG_DARK"])
        lm_btn_row.pack(fill="x", padx=24, pady=(6, 2))
        ttk.Button(
            lm_btn_row,
            text=self._L["settings_lm_fetch_models"],
            command=self._fetch_models,
        ).pack(side="left", padx=2)
        ttk.Button(
            lm_btn_row,
            text=self._L["settings_lm_test"],
            command=self._test_connection,
        ).pack(side="left", padx=2)

        self.lm_status_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self.lm_status_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(-2),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(2, 4))

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["llm_config_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(
            btn_row, text=self._L["llm_config_cancel"], command=self.destroy
        ).pack(side="left", padx=8)

    def _fetch_models(self):
        url = self.lm_url_var.get().strip()
        if not url:
            self.lm_status_var.set(
                self._L["settings_lm_test_fail"].format(error="URL is empty")
            )
            return
        try:
            models = fetch_lm_studio_models(url, timeout=10)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self.lm_status_var.set(
                self._L["settings_lm_test_fail"].format(error=str(e))
            )
            return
        self.lm_model_combo["values"] = models
        self.lm_status_var.set(self._L["settings_lm_test_ok"].format(count=len(models)))

    def _test_connection(self):
        url = self.lm_url_var.get().strip()
        if not url:
            self.lm_status_var.set(
                self._L["settings_lm_test_fail"].format(error="URL is empty")
            )
            return
        try:
            models = fetch_lm_studio_models(url, timeout=10)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            self.lm_status_var.set(
                self._L["settings_lm_test_fail"].format(error=str(e))
            )
            return
        self.lm_status_var.set(self._L["settings_lm_test_ok"].format(count=len(models)))

    def _apply(self):
        llm_settings = {}
        llm_settings["lm_studio_url"] = self.lm_url_var.get().strip() or (
            "http://localhost:1234"
        )
        llm_settings["lm_studio_model"] = self.lm_model_var.get().strip()
        try:
            llm_settings["ocr_scale"] = max(
                1.0, min(4.0, float(self.ocr_scale_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_scale"] = 2.0
        try:
            llm_settings["ocr_timeout"] = max(
                10, min(600, int(self.ocr_timeout_var.get()))
            )
        except (tk.TclError, ValueError):
            llm_settings["ocr_timeout"] = 120
        self.destroy()
        if self.on_apply:
            self.on_apply(llm_settings)


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
            except Exception as e:
                logger.debug("ページ数取得失敗: %s", e)
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


# ══════════════════════════════════════════
#  ページ結合・リサイズダイアログ
# ══════════════════════════════════════════
class MergeResizeDialog(tk.Toplevel):
    """選択ページを1枚に結合・リサイズするための方向選択ダイアログ"""

    def __init__(self, parent, page_infos, callback, lang="ja", font_func=None):
        super().__init__(parent)
        self._L = LANG[lang]
        self.title(self._L["mr_dialog_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.page_infos = page_infos  # [(page_no_1based, width, height), ...]
        self.callback = callback
        self._font_size = _current_font_size
        self._font_func = font_func

        self._build()
        self._update_size_preview()
        self.update_idletasks()
        fs = self._font_size
        w = max(420, int(fs * 38))
        h = max(360, int(fs * 28) + len(page_infos) * (fs + 6))
        h = min(h, parent.winfo_height() - 40)
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")
        self.minsize(380, 300)

    def _font(self, delta=0, weight=None):
        if self._font_func:
            return self._font_func(delta, weight)
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        count = len(self.page_infos)

        tk.Label(
            self,
            text=self._L["mr_dialog_heading"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 4))

        tk.Label(
            self,
            text=self._L["mr_dialog_hint"].format(count=count),
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1),
            justify="center",
        ).pack(pady=(0, 10))

        # 方向選択
        df = tk.Frame(self, bg=C["BG_DARK"])
        df.pack(fill="x", padx=24, pady=4)
        tk.Label(
            df,
            text=self._L["mr_direction"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(0),
        ).pack(side="left")
        self.dir_var = tk.StringVar(value="horizontal")
        for value, key in (
            ("horizontal", "mr_horizontal"),
            ("vertical", "mr_vertical"),
        ):
            tk.Radiobutton(
                df,
                text=self._L[key],
                variable=self.dir_var,
                value=value,
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                selectcolor=C["BG_CARD"],
                activebackground=C["BG_DARK"],
                activeforeground=C["TEXT_MAIN"],
                font=self._font(-1),
                command=self._update_size_preview,
            ).pack(side="left", padx=6)

        # 結合順表示
        tk.Label(
            self,
            text=self._L["mr_order_label"],
            bg=C["BG_DARK"],
            fg=C["TEXT_MAIN"],
            font=self._font(-1),
        ).pack(anchor="w", padx=24, pady=(8, 2))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="x", padx=24, pady=2)
        for pno, w, h in self.page_infos:
            tk.Label(
                list_frame,
                text=f"  p.{pno}   ({int(w)}×{int(h)} pt)",
                bg=C["BG_PANEL"],
                fg=C["TEXT_MAIN"],
                font=self._font(-1),
                anchor="w",
            ).pack(fill="x", padx=4, pady=1)

        # 出力サイズプレビュー
        self.size_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self.size_var,
            bg=C["BG_DARK"],
            fg=C["SUCCESS"],
            font=self._font(0, "bold"),
        ).pack(pady=(10, 4))

        # ボタン
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(
            btn_row,
            text=self._L["mr_apply"],
            style="Accent.TButton",
            command=self._apply,
        ).pack(side="left", padx=8)
        ttk.Button(
            btn_row,
            text=self._L["mr_cancel"],
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _compute_size(self):
        widths = [w for _, w, _ in self.page_infos]
        heights = [h for _, _, h in self.page_infos]
        if self.dir_var.get() == "horizontal":
            return sum(widths), max(heights)
        return max(widths), sum(heights)

    def _update_size_preview(self):
        w, h = self._compute_size()
        self.size_var.set(self._L["mr_size_preview"].format(w=int(w), h=int(h)))

    def _apply(self):
        direction = self.dir_var.get()
        out_w, out_h = self._compute_size()
        self.destroy()
        self.callback(direction, out_w, out_h)
