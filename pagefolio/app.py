# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""メインアプリケーションクラス — Mixin を統合した PDFEditorApp"""

import tkinter as tk
import traceback
from tkinter import messagebox

from pagefolio.constants import LANG, C
from pagefolio.dialogs import PluginDialog, SettingsDialog
from pagefolio.dnd import DnDMixin
from pagefolio.file_drop import _setup_file_drop
from pagefolio.file_ops import FileOpsMixin
from pagefolio.page_ops import PageOpsMixin
from pagefolio.plugins import PluginManager
from pagefolio.settings import (
    _apply_theme,
    _load_settings,
    _save_settings,
)
from pagefolio.ui_builder import UIBuilderMixin
from pagefolio.viewer import ViewerMixin


class PDFEditorApp(UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin):
    MAX_UNDO = 20

    def __init__(self, root):
        self.root = root
        self.root.title("PageFolio")
        self.root.geometry("1200x780")
        self.root.minsize(800, 600)

        # 設定読み込み・テーマ適用
        self.settings = _load_settings()
        self.font_size = self.settings.get("font_size", 10)
        self.lang = self.settings.get("lang", "ja")
        import pagefolio.settings as _settings_mod

        _settings_mod._current_font_size = self.font_size
        _apply_theme(self.settings.get("theme", "dark"))
        self.root.configure(bg=C["BG_DARK"])

        self.doc = None
        self.filepath = None
        self.current_page = 0
        self.selected_pages = set()
        self.thumb_images = []
        self.thumb_cache = {}
        self._dnd_src_idx = None
        self._dnd_ghost = None
        self._dnd_indicator = None
        self.crop_rect = None
        self.crop_drag_start = None
        self.crop_mode = False

        # Undo / Redo
        self._undo_stack = []
        self._redo_stack = []
        self._pending_click = None

        # プラグインマネージャー
        self.plugin_manager = PluginManager()
        disabled_plugins = self.settings.get("disabled_plugins", [])
        self.plugin_manager.load_all(app=self, disabled_ids=disabled_plugins)

        self._build_styles()
        self._build_ui()

        # WM_DELETE_WINDOW
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # キーボードショートカット
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
        self.root.bind("<Delete>", lambda e: self._delete_selected())

    # ══════════════════════════════════════════
    #  ユーティリティ
    # ══════════════════════════════════════════
    def _update_doc_buttons_state(self):
        """ファイル開閉状態に応じてボタンの活性/非活性を切り替え"""
        state = ["!disabled"] if self.doc else ["disabled"]
        for b in self._doc_buttons:
            try:
                b.state(state)
            except Exception:  # noqa: S110
                pass

    def _check_doc(self):
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_no_doc"))
            return False
        return True

    def _get_targets(self):
        return list(self.selected_pages) if self.selected_pages else [self.current_page]

    # ── D&D ファイルオープン ハンドラ ──
    def _on_dnd_enter(self, event):
        """ドラッグがプレビュー領域に入ったときのビジュアルフィードバック"""
        self.preview_canvas.configure(bg=C["ACCENT"])
        self.preview_canvas.delete("dnd_hint")
        cx = self.preview_canvas.winfo_width() // 2
        cy = self.preview_canvas.winfo_height() // 2
        self.preview_canvas.create_text(
            cx,
            cy,
            text=self._t("dnd_drop_hint"),
            fill=C["TEXT_MAIN"],
            font=self._font(4, "bold"),
            tags="dnd_hint",
        )
        return event.action

    def _on_dnd_leave(self, event):
        """ドラッグがプレビュー領域を離れたときにフィードバックをリセット"""
        self.preview_canvas.configure(bg=C["PREVIEW_BG"])
        self.preview_canvas.delete("dnd_hint")
        return event.action

    def _on_dnd_drop(self, event):
        """ドロップされたファイルを処理する"""
        from pagefolio.dialogs import MergeOrderDialog

        self.preview_canvas.configure(bg=C["PREVIEW_BG"])
        self.preview_canvas.delete("dnd_hint")

        raw_paths = self.preview_canvas.tk.splitlist(event.data)
        pdf_paths = [p for p in raw_paths if p.lower().endswith(".pdf")]

        if not pdf_paths:
            if raw_paths:
                messagebox.showwarning(
                    self._t("confirm_title"), self._t("dnd_pdf_only")
                )
            return event.action

        if len(pdf_paths) == 1:
            if self.doc:
                if not messagebox.askyesno(
                    self._t("confirm_title"), self._t("dnd_replace_confirm")
                ):
                    return event.action
            self._open_pdf_path(pdf_paths[0])
        else:
            MergeOrderDialog(
                self.root, list(pdf_paths), self._do_open_merged, lang=self.lang
            )

        return event.action

    def _quit(self):
        if self.doc:
            if messagebox.askyesno(self._t("confirm_title"), self._t("quit_confirm")):
                self.doc.close()
                self.root.destroy()
        else:
            self.root.destroy()

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _font(self, delta=0, weight=None):
        """テーマ対応フォントタプルを返す"""
        size = max(7, self.font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _t(self, key):
        """現在の言語でテキストを返すヘルパー"""
        return LANG[self.lang].get(key, LANG["ja"].get(key, key))

    def _toggle_lang(self):
        """言語を切り替えて UI を再構築する"""
        self.lang = "en" if self.lang == "ja" else "ja"
        self.settings["lang"] = self.lang
        _save_settings(self.settings)
        self._rebuild_ui()

    # ══════════════════════════════════════════
    #  プラグイン管理
    # ══════════════════════════════════════════
    def _build_plugin_ui(self):
        """有効プラグインのカスタムUIを構築する"""
        if not hasattr(self, "_plugin_ui_frame") or self._plugin_ui_frame is None:
            return
        for w in self._plugin_ui_frame.winfo_children():
            w.destroy()
        for _plugin_id, plugin in self.plugin_manager.plugins.items():
            try:
                pf = tk.Frame(self._plugin_ui_frame, bg=C["BG_CARD"], bd=0)
                pf.pack(fill="x", padx=10, pady=3)
                tk.Label(
                    pf,
                    text=f"🔌 {plugin.name}",
                    bg=C["BG_CARD"],
                    fg=C["WARNING"],
                    font=self._font(-1, "bold"),
                ).pack(anchor="w", padx=8, pady=(4, 2))
                plugin.build_ui(self, pf)
            except Exception:
                traceback.print_exc()

    def _open_plugin_dialog(self):
        """プラグイン管理ダイアログを開く"""
        PluginDialog(self.root, self)

    def _reload_plugins(self):
        """プラグインを再読み込みして設定を保存する"""
        self.settings["disabled_plugins"] = self.plugin_manager.get_disabled_ids()
        _save_settings(self.settings)
        self._build_plugin_ui()

    # ══════════════════════════════════════════
    #  設定ダイアログ
    # ══════════════════════════════════════════
    def _open_settings(self):
        """設定ダイアログを開く"""
        SettingsDialog(self.root, self.settings, self._apply_settings, self._font)

    def _apply_settings(self, new_settings):
        """設定変更を適用してUIを再構築"""
        self.settings = new_settings
        self.font_size = new_settings.get("font_size", 10)
        self.lang = new_settings.get("lang", self.lang)
        import pagefolio.settings as _settings_mod

        _settings_mod._current_font_size = self.font_size
        _apply_theme(new_settings.get("theme", "dark"))
        _save_settings(new_settings)
        self._rebuild_ui()
        self._set_status(self._t("status_settings"))

    def _rebuild_ui(self):
        """テーマ・フォント変更時にUI全体を再構築"""
        self.root.configure(bg=C["BG_DARK"])
        for w in self.root.winfo_children():
            w.destroy()
        self.thumb_images.clear()
        self.thumb_cache.clear()
        self.crop_rect = None
        self.crop_drag_start = None
        self.crop_mode = False
        self.crop_overlay_ids = []
        self.crop_rect_id = None
        self._plugin_ui_frame = None
        self._build_styles()
        self._build_ui()
        if self.doc:
            self._refresh_all()
        else:
            self._show_preview()
            self._update_doc_buttons_state()
        _setup_file_drop(self)
