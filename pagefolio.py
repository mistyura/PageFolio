# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""
PageFolio GUI - Windows 11
必要ライブラリ: pip install pymupdf pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # pymupdf
from PIL import Image, ImageTk
import io
import os
import json
import importlib
import importlib.util
import traceback


# ===================== カラーテーマ =====================
THEMES = {
    "dark": {
        "BG_DARK":    "#1a1a2e",
        "BG_PANEL":   "#16213e",
        "BG_CARD":    "#0f3460",
        "ACCENT":     "#e94560",
        "ACCENT2":    "#533483",
        "TEXT_MAIN":  "#eaeaea",
        "TEXT_SUB":   "#a0a0b0",
        "BTN_HOVER":  "#ff6b6b",
        "SUCCESS":    "#4ecca3",
        "WARNING":    "#ffd460",
        "CROP_ON_BG": "#8b0000",
        "PREVIEW_BG": "#111122",
        "DANGER_BG":  "#7c1c2e",
        "DANGER_FG":  "#ffaaaa",
    },
    "light": {
        "BG_DARK":    "#f0f0f5",
        "BG_PANEL":   "#e0e0ea",
        "BG_CARD":    "#d0d0dd",
        "ACCENT":     "#d63050",
        "ACCENT2":    "#7b52ab",
        "TEXT_MAIN":  "#1a1a2e",
        "TEXT_SUB":   "#555566",
        "BTN_HOVER":  "#ff6b6b",
        "SUCCESS":    "#2a9d6a",
        "WARNING":    "#b8860b",
        "CROP_ON_BG": "#cc3333",
        "PREVIEW_BG": "#c8c8d0",
        "DANGER_BG":  "#e8c0c0",
        "DANGER_FG":  "#7c1c2e",
    },
}

# 現在テーマの色をモジュールレベルで参照するための辞書（実行時に設定）
C = dict(THEMES["dark"])

# ===================== 言語辞書 =====================
LANG = {
    "ja": {
        # ヘッダー / ステータス
        "status_initial": "ファイルを開いてください",
        # サムネイルパネル
        "panel_pages": "ページ一覧",
        "dnd_hint": "D&D で並替",
        "select_all": "全選択",
        "deselect": "解除",
        # プレビューツールバー
        "btn_prev": "◀ 前",
        "btn_next": "次 ▶",
        "btn_zoom_in": "🔍 拡大",
        "btn_zoom_out": "🔍 縮小",
        # ツールセクション見出し
        "sec_settings": "⚙ 設定",
        "sec_file": "📂 ファイル",
        "sec_undo": "↩ 元に戻す / やり直す",
        "sec_page": "📄 ページ操作（選択ページ）",
        "sec_crop": "✂ トリミング（現在ページ）",
        "sec_insert": "📎 挿入・結合",
        "sec_plugin": "🔌 プラグイン",
        # 設定セクションボタン
        "btn_settings": "⚙ テーマ・フォント設定…",
        "btn_about": "ℹ About",
        "btn_lang": "🌐 English",
        # ファイルセクションボタン
        "btn_open": "ファイルを開く (Ctrl+O)",
        "btn_save": "上書き保存 (Ctrl+S)",
        "btn_save_as": "名前を付けて保存 (Ctrl+Shift+S)",
        "btn_quit": "✕ 終了",
        # Undo/Redo
        "btn_undo": "↩ Ctrl+Z",
        "btn_redo": "↪ Ctrl+Y",
        # ページ操作
        "lbl_rotate": "回転:",
        "btn_rot_left": "↺ 左90°",
        "btn_rot_right": "↻ 右90°",
        "btn_rot_180": "↕ 180°",
        "btn_delete": "🗑 選択ページを削除 (Del)",
        # トリミング
        "crop_mode_off": "✂ 範囲選択モード OFF",
        "crop_mode_on": "🔴 範囲選択モード ON  (クリックで OFF)",
        "crop_hint": "プレビュー上でドラッグして範囲を指定",
        "crop_no_sel": "範囲未選択",
        "btn_crop": "✔ 選択範囲でトリミング",
        "btn_crop_reset": "✕ 選択範囲をリセット",
        # 挿入・結合
        "btn_insert_head": "先頭に挿入",
        "btn_insert_tail": "末尾に挿入",
        "btn_insert_pos": "指定位置に挿入…",
        "btn_merge": "PDFを末尾に結合",
        # プラグイン
        "btn_plugin_mgr": "🔌 プラグイン管理…",
        # プレビュー空状態
        "preview_empty1": "📂 ファイルを開いてください",
        "preview_empty2": "Ctrl+O  または右パネル「ファイルを開く」",
        # 共通ボタン
        "btn_close": "✕ 閉じる",
        # ステータスメッセージ
        "undo_empty": "元に戻す履歴がありません",
        "redo_empty": "やり直す履歴がありません",
        "undo_done": "元に戻しました",
        "redo_done": "やり直しました",
        "status_settings": "設定を変更しました",
        # ファイル操作
        "filetypes_pdf": "PDFファイル",
        "filetypes_all": "すべて",
        "info_open_first": "先にファイルを開いてください",
        "save_confirm_title": "上書き保存の確認",
        "save_confirm_msg": "以下のファイルを上書き保存します。\n\n{name}\n\n元のファイルは上書きされます。よろしいですか？",
        "status_saved": "保存しました: {name}",
        "err_save_title": "保存エラー",
        "err_save_msg": "保存に失敗しました:\n{e}",
        "status_opened": "開きました: {name}  ({n}ページ)",
        "status_merged_open": "{count}ファイルを結合して開きました ({total}ページ): {names}",
        # ページ操作ステータス
        "status_rotated": "{count}ページを{deg}°回転しました",
        "info_no_page_sel": "削除するページを選択してください",
        "warn_del_all_title": "警告",
        "warn_del_all": "すべてのページを削除することはできません。\n最低1ページは残す必要があります。",
        "confirm_del": "{count}ページを削除しますか？",
        "status_deleted": "{count}ページを削除しました",
        # トリミング
        "info_crop_drag": "プレビュー上でドラッグしてトリミング範囲を選択してください",
        "status_cropped": "ページ{page}をトリミングしました",
        "err_crop_small": "範囲が小さすぎます。もう一度ドラッグしてください",
        "err_crop_title": "トリミングエラー",
        "err_crop_msg": "CropBoxの設定に失敗しました。\n範囲を調整して再度お試しください。\n\n{e}",
        # 挿入・結合ステータス
        "dlg_insert_title": "挿入するPDFを選択（複数可）",
        "dlg_insert_pos_title": "挿入位置",
        "dlg_insert_pos_msg": "何ページ目の後ろに挿入しますか？\n(0 = 先頭、1〜{n} = そのページの後ろ)\n\n例: 3 → 3ページ目の後ろに挿入",
        "status_insert_head": "先頭",
        "status_insert_tail": "末尾",
        "status_insert_pos": "{pos}ページ目の後ろ",
        "status_inserted": "{count}ファイル（計{total}ページ）を{where}に挿入しました",
        "dlg_merge_title": "結合するPDFを選択（複数可・選択順に結合）",
        "status_merged": "{count}ファイル（計{total}ページ）を末尾に結合しました",
        # 終了
        "quit_confirm": "アプリを終了しますか？\n（未保存の変更は失われます）",
        # doc 確認
        "info_no_doc": "先にPDFファイルを開いてください",
        # D&D ステータス
        "status_dnd_moved": "p.{src} → p.{dest} に移動しました",
        # About ダイアログ
        "about_title": "PageFolio について",
        "about_subtitle": "PDF Page Organizer",
        "about_ok": "OK",
        # 設定ダイアログ
        "settings_title": "設定",
        "settings_heading": "⚙ 設定",
        "settings_theme": "テーマ:",
        "settings_theme_dark": "ダーク",
        "settings_theme_light": "ライト",
        "settings_theme_system": "システム設定",
        "settings_font": "フォントサイズ:",
        "settings_font_hint": "pt  (8〜16)",
        "settings_preview_text": "サンプルテキスト  Sample Text  123",
        "settings_apply": "✔ 適用",
        "settings_cancel": "キャンセル",
        # 結合順ダイアログ
        "merge_title": "結合順の確認・変更",
        "merge_heading": "結合順の確認・並び替え",
        "merge_hint": "ファイルを選択して ▲▼ で順番を変更できます\n確定すると現在のPDFの末尾に順番通り結合されます",
        "merge_up": "▲ 上へ",
        "merge_down": "▼ 下へ",
        "merge_remove": "✕ 削除",
        "merge_info": "合計 {count} ファイル  /  {total} ページ",
        "merge_confirm": "✔ この順番で結合",
        "merge_cancel": "キャンセル",
        "merge_no_files": "ファイルがありません",
        # プラグインダイアログ
        "plugin_title": "プラグイン管理",
        "plugin_heading": "🔌 プラグイン管理",
        "plugin_dir_label": "プラグインフォルダ: {path}",
        "plugin_empty": "プラグインが見つかりません\n\n「{dir}」フォルダに .py ファイルを\n配置してください",
        "plugin_author": "作者: {author}",
        "plugin_rescan": "🔄 再検出",
        "plugin_open_folder": "📁 フォルダを開く",
        "plugin_close": "✔ 閉じる",
        # 共通エラー
        "err_title": "エラー",
        "info_title": "情報",
        "warn_title": "警告",
        "confirm_title": "確認",
    },
    "en": {
        # Header / status
        "status_initial": "Open a file to get started",
        # Thumbnail panel
        "panel_pages": "Pages",
        "dnd_hint": "Drag to reorder",
        "select_all": "Select All",
        "deselect": "Deselect",
        # Preview toolbar
        "btn_prev": "◀ Prev",
        "btn_next": "Next ▶",
        "btn_zoom_in": "🔍 Zoom In",
        "btn_zoom_out": "🔍 Zoom Out",
        # Tool section titles
        "sec_settings": "⚙ Settings",
        "sec_file": "📂 File",
        "sec_undo": "↩ Undo / Redo",
        "sec_page": "📄 Page Operations",
        "sec_crop": "✂ Crop (Current Page)",
        "sec_insert": "📎 Insert / Merge",
        "sec_plugin": "🔌 Plugins",
        # Settings section buttons
        "btn_settings": "⚙ Theme & Font…",
        "btn_about": "ℹ About",
        "btn_lang": "🌐 日本語",
        # File section buttons
        "btn_open": "Open File (Ctrl+O)",
        "btn_save": "Save (Ctrl+S)",
        "btn_save_as": "Save As (Ctrl+Shift+S)",
        "btn_quit": "✕ Quit",
        # Undo/Redo
        "btn_undo": "↩ Ctrl+Z",
        "btn_redo": "↪ Ctrl+Y",
        # Page operations
        "lbl_rotate": "Rotate:",
        "btn_rot_left": "↺ Left 90°",
        "btn_rot_right": "↻ Right 90°",
        "btn_rot_180": "↕ 180°",
        "btn_delete": "🗑 Delete Selected (Del)",
        # Crop
        "crop_mode_off": "✂ Crop Mode OFF",
        "crop_mode_on": "🔴 Crop Mode ON  (click to OFF)",
        "crop_hint": "Drag on preview to select crop area",
        "crop_no_sel": "No selection",
        "btn_crop": "✔ Crop to Selection",
        "btn_crop_reset": "✕ Reset Selection",
        # Insert/Merge
        "btn_insert_head": "Insert at Beginning",
        "btn_insert_tail": "Insert at End",
        "btn_insert_pos": "Insert at Position…",
        "btn_merge": "Merge PDF to End",
        # Plugin
        "btn_plugin_mgr": "🔌 Manage Plugins…",
        # Preview empty state
        "preview_empty1": "📂 Open a file to get started",
        "preview_empty2": "Ctrl+O  or use \"Open File\" in the right panel",
        # Common button
        "btn_close": "✕ Close",
        # Status messages
        "undo_empty": "Nothing to undo",
        "redo_empty": "Nothing to redo",
        "undo_done": "Undone",
        "redo_done": "Redone",
        "status_settings": "Settings updated",
        # File operations
        "filetypes_pdf": "PDF files",
        "filetypes_all": "All files",
        "info_open_first": "Please open a file first",
        "save_confirm_title": "Confirm Overwrite",
        "save_confirm_msg": "Overwrite the following file?\n\n{name}\n\nThis cannot be undone. Continue?",
        "status_saved": "Saved: {name}",
        "err_save_title": "Save Error",
        "err_save_msg": "Failed to save:\n{e}",
        "status_opened": "Opened: {name}  ({n} pages)",
        "status_merged_open": "Opened {count} files merged ({total} pages): {names}",
        # Page operations status
        "status_rotated": "Rotated {count} page(s) by {deg}°",
        "info_no_page_sel": "Please select pages to delete",
        "warn_del_all_title": "Warning",
        "warn_del_all": "Cannot delete all pages.\nAt least one page must remain.",
        "confirm_del": "Delete {count} page(s)?",
        "status_deleted": "Deleted {count} page(s)",
        # Crop
        "info_crop_drag": "Drag on the preview to select a crop area",
        "status_cropped": "Cropped page {page}",
        "err_crop_small": "Selection too small. Please drag again.",
        "err_crop_title": "Crop Error",
        "err_crop_msg": "Failed to set CropBox.\nAdjust the selection and try again.\n\n{e}",
        # Insert/Merge status
        "dlg_insert_title": "Select PDF(s) to Insert",
        "dlg_insert_pos_title": "Insert Position",
        "dlg_insert_pos_msg": "Insert after which page?\n(0 = beginning, 1–{n} = after that page)\n\nEx: 3 → insert after page 3",
        "status_insert_head": "beginning",
        "status_insert_tail": "end",
        "status_insert_pos": "after page {pos}",
        "status_inserted": "Inserted {count} file(s) ({total} pages) at {where}",
        "dlg_merge_title": "Select PDF(s) to Merge",
        "status_merged": "Merged {count} file(s) ({total} pages) to end",
        # Quit
        "quit_confirm": "Quit PageFolio?\n(Unsaved changes will be lost)",
        # Check doc
        "info_no_doc": "Please open a PDF file first",
        # D&D status
        "status_dnd_moved": "p.{src} → p.{dest} moved",
        # About dialog
        "about_title": "About PageFolio",
        "about_subtitle": "PDF Page Organizer",
        "about_ok": "OK",
        # Settings dialog
        "settings_title": "Settings",
        "settings_heading": "⚙ Settings",
        "settings_theme": "Theme:",
        "settings_theme_dark": "Dark",
        "settings_theme_light": "Light",
        "settings_theme_system": "System",
        "settings_font": "Font Size:",
        "settings_font_hint": "pt  (8–16)",
        "settings_preview_text": "Sample Text  サンプルテキスト  123",
        "settings_apply": "✔ Apply",
        "settings_cancel": "Cancel",
        # Merge order dialog
        "merge_title": "Confirm Merge Order",
        "merge_heading": "Confirm & Reorder",
        "merge_hint": "Select a file and use ▲▼ to reorder\nThe PDFs will be merged in this order",
        "merge_up": "▲ Up",
        "merge_down": "▼ Down",
        "merge_remove": "✕ Remove",
        "merge_info": "Total {count} file(s)  /  {total} pages",
        "merge_confirm": "✔ Merge in This Order",
        "merge_cancel": "Cancel",
        "merge_no_files": "No files",
        # Plugin dialog
        "plugin_title": "Plugin Manager",
        "plugin_heading": "🔌 Plugin Manager",
        "plugin_dir_label": "Plugin folder: {path}",
        "plugin_empty": "No plugins found\n\nPlace .py files in the\n\"{dir}\" folder",
        "plugin_author": "Author: {author}",
        "plugin_rescan": "🔄 Rescan",
        "plugin_open_folder": "📁 Open Folder",
        "plugin_close": "✔ Close",
        # Common error
        "err_title": "Error",
        "info_title": "Info",
        "warn_title": "Warning",
        "confirm_title": "Confirm",
    },
}

SETTINGS_FILE = "pagefolio_settings.json"

def _get_settings_path():
    """設定ファイルのパスを返す（スクリプトと同じディレクトリ）"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGS_FILE)

def _load_settings():
    """設定を読み込む。ファイルがなければデフォルト値を返す"""
    defaults = {"theme": "dark", "font_size": 12, "lang": "ja"}
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return dict(defaults)

def _save_settings(settings):
    """設定を保存する"""
    try:
        path = _get_settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _detect_system_theme():
    """Windowsのシステムテーマを検出。ダーク→'dark'、ライト→'light'"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception:
        return "dark"

def _resolve_theme(theme_setting):
    """テーマ設定値を実際のテーマ名に解決する"""
    if theme_setting == "system":
        return _detect_system_theme()
    return theme_setting if theme_setting in THEMES else "dark"

def _apply_theme(theme_name):
    """テーマをグローバル辞書Cに適用"""
    resolved = _resolve_theme(theme_name)
    C.update(THEMES[resolved])

def _make_font(delta=0, weight=None, base_size=10):
    """フォントタプルを生成するグローバルヘルパー"""
    size = max(7, base_size + delta)
    if weight:
        return ("Segoe UI", size, weight)
    return ("Segoe UI", size)

# 現在のフォントサイズ（設定から読み込み後に更新）
_current_font_size = 12


# ===================== プラグインシステム =====================

PLUGINS_DIR = "plugins"

def _get_plugins_dir():
    """プラグインディレクトリのパスを返す（スクリプトと同じディレクトリ内）"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), PLUGINS_DIR)


class PDFEditorPlugin:
    """プラグイン基底クラス。プラグインはこのクラスを継承して作成する。"""
    name = "Unnamed Plugin"
    version = "0.0.0"
    description = ""
    author = ""

    def on_load(self, app):
        """プラグインがロードされた時に呼ばれる"""
        pass

    def on_unload(self, app):
        """プラグインがアンロードされた時に呼ばれる"""
        pass

    def on_file_open(self, app, path):
        """ファイルが開かれた後に呼ばれる"""
        pass

    def on_file_save(self, app, path):
        """ファイルが保存された後に呼ばれる"""
        pass

    def on_page_rotate(self, app, pages, degrees):
        """ページが回転された後に呼ばれる"""
        pass

    def on_page_delete(self, app, pages):
        """ページが削除された後に呼ばれる"""
        pass

    def on_page_crop(self, app, page_index):
        """ページがトリミングされた後に呼ばれる"""
        pass

    def on_page_change(self, app, page_index):
        """表示ページが変更された時に呼ばれる"""
        pass

    def on_insert(self, app, paths, insert_at):
        """ページが挿入された後に呼ばれる"""
        pass

    def on_merge(self, app, paths):
        """PDFが結合された後に呼ばれる"""
        pass

    def build_ui(self, app, parent):
        """プラグイン独自のUIを構築する。parentはtk.Frameを受け取る。"""
        pass


class PluginManager:
    """プラグインの検出・読み込み・管理を行うマネージャー"""

    def __init__(self):
        self._plugins = {}        # {plugin_id: plugin_instance}
        self._plugin_modules = {} # {plugin_id: module}
        self._disabled = set()    # 無効化されたプラグインIDのセット

    @property
    def plugins(self):
        """有効なプラグイン一覧を返す"""
        return {k: v for k, v in self._plugins.items() if k not in self._disabled}

    @property
    def all_plugins(self):
        """全プラグイン一覧を返す（無効含む）"""
        return dict(self._plugins)

    def is_enabled(self, plugin_id):
        return plugin_id in self._plugins and plugin_id not in self._disabled

    def discover_plugins(self):
        """プラグインディレクトリからプラグインファイルを検出する"""
        plugins_dir = _get_plugins_dir()
        if not os.path.isdir(plugins_dir):
            return []
        found = []
        for name in sorted(os.listdir(plugins_dir)):
            if name.startswith("_") or not name.endswith(".py"):
                continue
            plugin_id = name[:-3]  # .py を除去
            found.append((plugin_id, os.path.join(plugins_dir, name)))
        return found

    def load_plugin(self, plugin_id, filepath, app=None):
        """プラグインファイルを読み込み、登録する"""
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]
        try:
            spec = importlib.util.spec_from_file_location(
                f"pdf_editor_plugin_{plugin_id}", filepath)
            module = importlib.util.module_from_spec(spec)
            # プラグインが "pdf_editor" モジュール名でインポートできるよう
            # pagefolio 自身を sys.modules に登録する
            import sys as _sys
            _this_module = _sys.modules.get(__name__) or _sys.modules.get("__main__")
            if "pdf_editor" not in _sys.modules and _this_module is not None:
                _sys.modules["pdf_editor"] = _this_module
            spec.loader.exec_module(module)
            self._plugin_modules[plugin_id] = module

            # モジュール内で PDFEditorPlugin を継承したクラスを探す
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, PDFEditorPlugin)
                        and attr is not PDFEditorPlugin):
                    plugin_class = attr
                    break

            if plugin_class is None:
                return None

            instance = plugin_class()
            self._plugins[plugin_id] = instance
            if app and plugin_id not in self._disabled:
                instance.on_load(app)
            return instance
        except Exception:
            traceback.print_exc()
            return None

    def unload_plugin(self, plugin_id, app=None):
        """プラグインをアンロードする"""
        if plugin_id in self._plugins:
            if app:
                try:
                    self._plugins[plugin_id].on_unload(app)
                except Exception:
                    traceback.print_exc()
            del self._plugins[plugin_id]
            self._plugin_modules.pop(plugin_id, None)

    def enable_plugin(self, plugin_id, app=None):
        """プラグインを有効化する"""
        self._disabled.discard(plugin_id)
        if plugin_id in self._plugins and app:
            try:
                self._plugins[plugin_id].on_load(app)
            except Exception:
                traceback.print_exc()

    def disable_plugin(self, plugin_id, app=None):
        """プラグインを無効化する"""
        if plugin_id in self._plugins and app:
            try:
                self._plugins[plugin_id].on_unload(app)
            except Exception:
                traceback.print_exc()
        self._disabled.add(plugin_id)

    def load_all(self, app=None, disabled_ids=None):
        """全プラグインを検出・読み込みする"""
        if disabled_ids:
            self._disabled = set(disabled_ids)
        for plugin_id, filepath in self.discover_plugins():
            self.load_plugin(plugin_id, filepath, app)

    def fire_event(self, event_name, *args, **kwargs):
        """有効な全プラグインにイベントを通知する"""
        for plugin_id, plugin in self.plugins.items():
            method = getattr(plugin, event_name, None)
            if method:
                try:
                    method(*args, **kwargs)
                except Exception:
                    traceback.print_exc()

    def get_disabled_ids(self):
        """無効化されたプラグインIDリストを返す"""
        return list(self._disabled)


class PDFEditorApp:
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
        global _current_font_size
        _current_font_size = self.font_size
        _apply_theme(self.settings.get("theme", "dark"))
        self.root.configure(bg=C["BG_DARK"])

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
        self._pending_click = None

        # プラグインマネージャー
        self.plugin_manager = PluginManager()
        disabled_plugins = self.settings.get("disabled_plugins", [])
        self.plugin_manager.load_all(app=self, disabled_ids=disabled_plugins)

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
        fs = self.font_size  # ベースフォントサイズ
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=C["BG_DARK"])
        style.configure("Panel.TFrame", background=C["BG_PANEL"])
        style.configure("Card.TFrame", background=C["BG_CARD"])
        style.configure("TLabel",
                        background=C["BG_DARK"], foreground=C["TEXT_MAIN"],
                        font=("Segoe UI", fs))
        style.configure("Title.TLabel",
                        background=C["BG_DARK"], foreground=C["ACCENT"],
                        font=("Segoe UI", fs + 8, "bold"))
        style.configure("Sub.TLabel",
                        background=C["BG_DARK"], foreground=C["TEXT_SUB"],
                        font=("Segoe UI", fs - 1))
        style.configure("Status.TLabel",
                        background=C["BG_PANEL"], foreground=C["SUCCESS"],
                        font=("Segoe UI", fs - 1))
        style.configure("TButton",
                        background=C["BG_CARD"], foreground=C["TEXT_MAIN"],
                        font=("Segoe UI", fs - 1, "bold"),
                        borderwidth=0, padding=(10, 6))
        style.map("TButton",
                  background=[("active", C["ACCENT"]), ("pressed", C["ACCENT2"])],
                  foreground=[("active", "#ffffff")])
        style.configure("Accent.TButton",
                        background=C["ACCENT"], foreground="#ffffff",
                        font=("Segoe UI", fs, "bold"),
                        borderwidth=0, padding=(12, 7))
        style.map("Accent.TButton",
                  background=[("active", C["BTN_HOVER"])])
        style.configure("Danger.TButton",
                        background=C["DANGER_BG"], foreground=C["DANGER_FG"],
                        font=("Segoe UI", fs - 1, "bold"),
                        borderwidth=0, padding=(10, 6))
        style.map("Danger.TButton",
                  background=[("active", C["ACCENT"])])
        # トリミングモードON強調 (#16)
        style.configure("CropOn.TButton",
                        background=C["CROP_ON_BG"], foreground="#ffffff",
                        font=("Segoe UI", fs - 1, "bold"),
                        borderwidth=2, padding=(10, 6))
        style.map("CropOn.TButton",
                  background=[("active", "#aa0000")])
        style.configure("TScrollbar",
                        background=C["BG_CARD"], troughcolor=C["BG_PANEL"],
                        borderwidth=0, arrowsize=12)
        style.configure("Horizontal.TScale",
                        background=C["BG_DARK"], troughcolor=C["BG_CARD"])

    # ─────────────────────────────────────────
    def _build_ui(self):
        # ---- ヘッダー（既存コードをそのまま維持）----
        header_h = max(56, int(self.font_size * 5))
        header = tk.Frame(self.root, bg=C["BG_PANEL"], height=header_h)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        tk.Label(header, text="✦ PageFolio", bg=C["BG_PANEL"],
                 fg=C["ACCENT"], font=self._font(6, "bold")).pack(side="left", padx=20, pady=12)
        self.status_var = tk.StringVar(value=self._t("status_initial"))
        tk.Label(header, textvariable=self.status_var,
                 bg=C["BG_PANEL"], fg=C["SUCCESS"],
                 font=self._font(-1)).pack(side="right", padx=20)

        # ---- 3ペイン PanedWindow（main Frame を廃止し直接 root に配置）----
        paned = tk.PanedWindow(self.root, orient="horizontal", bg=C["BG_DARK"],
                               sashwidth=5, sashrelief="flat",
                               opaqueresize=True, bd=0)
        paned.pack(fill="both", expand=True)

        # 左ペイン: サムネイル
        left_width = max(200, int(self.font_size * 18))
        left = tk.Frame(paned, bg=C["BG_PANEL"])
        self._build_thumb_panel(left)
        paned.add(left, minsize=150, width=left_width)

        # 中央ペイン: プレビュー
        center = tk.Frame(paned, bg=C["BG_DARK"])
        self._build_preview(center)
        paned.add(center, minsize=300)

        # 右ペイン: ツール（固定幅 → PanedWindow の3番目のペインに変更）
        right_width = max(260, int(self.font_size * 22))
        right = tk.Frame(paned, bg=C["BG_PANEL"])
        self._build_tools_scrollable(right)
        paned.add(right, minsize=220, width=right_width)

        # デフォルト比率 20:50:30 を描画後に設定
        def _set_sash():
            paned.update_idletasks()
            total = paned.winfo_width()
            if total > 100:
                paned.sash_place(0, int(total * 0.20), 0)
                paned.sash_place(1, int(total * 0.70), 0)
        self.root.after_idle(_set_sash)

    # ─────────────────────────────────────────
    def _build_thumb_panel(self, parent):
        hdr = tk.Frame(parent, bg=C["BG_PANEL"])
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(hdr, text=self._t("panel_pages"), bg=C["BG_PANEL"],
                 fg=C["ACCENT"], font=self._font(0, "bold")).pack(side="left")
        tk.Label(hdr, text=self._t("dnd_hint"), bg=C["BG_PANEL"],
                 fg=C["TEXT_SUB"], font=self._font(-3)).pack(side="right")

        sel_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        sel_frame.pack(fill="x", padx=6, pady=2)
        ttk.Button(sel_frame, text=self._t("select_all"),
                   command=self._select_all).pack(side="left", padx=2)
        ttk.Button(sel_frame, text=self._t("deselect"),
                   command=self._deselect_all).pack(side="left", padx=2)

        canvas_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.thumb_canvas = tk.Canvas(canvas_frame, bg=C["BG_PANEL"],
                                      highlightthickness=0)
        sb = ttk.Scrollbar(canvas_frame, orient="vertical",
                           command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.thumb_canvas.pack(fill="both", expand=True)

        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=C["BG_PANEL"])
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
        toolbar = tk.Frame(parent, bg=C["BG_PANEL"], height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self.prev_btn = ttk.Button(toolbar, text=self._t("btn_prev"),
                   command=self._prev_page)
        self.prev_btn.pack(side="left", padx=6, pady=8)
        self.page_label = tk.Label(toolbar, text="- / -",
                                   bg=C["BG_PANEL"], fg=C["TEXT_MAIN"],
                                   font=self._font(0, "bold"))
        self.page_label.pack(side="left", padx=4)
        self.next_btn = ttk.Button(toolbar, text=self._t("btn_next"),
                   command=self._next_page)
        self.next_btn.pack(side="left", padx=6)

        ttk.Button(toolbar, text=self._t("btn_zoom_out"),
                   command=lambda: self._zoom(-0.2)).pack(side="right", padx=4, pady=8)
        ttk.Button(toolbar, text=self._t("btn_zoom_in"),
                   command=lambda: self._zoom(0.2)).pack(side="right", padx=4)
        self.zoom_label = tk.Label(toolbar, text="100%",
                                   bg=C["BG_PANEL"], fg=C["TEXT_SUB"],
                                   font=self._font(-1))
        self.zoom_label.pack(side="right", padx=4)

        frame = tk.Frame(parent, bg=C["BG_DARK"])
        frame.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(frame, bg=C["PREVIEW_BG"],
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
    def _build_tools_scrollable(self, parent):
        """右ペインをスクロール可能にするラッパー"""
        canvas = tk.Canvas(parent, bg=C["BG_PANEL"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["BG_PANEL"])
        canvas.create_window((0, 0), window=inner, anchor="nw",
                             tags="inner_window")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 内部フレームの幅をキャンバスに合わせる
            canvas.itemconfigure("inner_window", width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure("inner_window",
                                                   width=e.width))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        # 内部ウィジェット上でもスクロールが効くようにバインドを伝播
        def _bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"),
                        add="+")
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)

        self._build_tools(inner)
        # ツール構築後にバインド＆スクロール位置を先頭にリセット
        def _after_build():
            _bind_mousewheel_recursive(inner)
            canvas.yview_moveto(0)
        inner.after(100, _after_build)

    # ─────────────────────────────────────────
    def _build_tools(self, parent):
        # ファイル依存ボタンのリスト（doc未開時に disabled にする）
        self._doc_buttons = []

        def section(title):
            f = tk.Frame(parent, bg=C["BG_CARD"], bd=0)
            f.pack(fill="x", padx=10, pady=5)
            tk.Label(f, text=title, bg=C["BG_CARD"], fg=C["WARNING"],
                     font=self._font(-1, "bold")).pack(anchor="w", padx=8, pady=(6,2))
            return f

        def btn(parent, text, cmd, style="TButton", needs_doc=False):
            b = ttk.Button(parent, text=text, command=cmd, style=style)
            b.pack(fill="x", padx=8, pady=2)
            if needs_doc:
                self._doc_buttons.append(b)
            return b

        f5 = section(self._t("sec_settings"))
        btn(f5, self._t("btn_settings"), self._open_settings)
        btn(f5, self._t("btn_about"), lambda: AboutDialog(self.root, self._font, self.lang))
        btn(f5, self._t("btn_lang"), self._toggle_lang)

        f = section(self._t("sec_file"))
        btn(f, self._t("btn_open"), self._open_file, "Accent.TButton")
        btn(f, self._t("btn_save"), self._save_file, needs_doc=True)
        btn(f, self._t("btn_save_as"), self._save_as, needs_doc=True)
        btn(f, self._t("btn_quit"), self._quit, "Danger.TButton")

        f_ur = section(self._t("sec_undo"))
        ur_row = tk.Frame(f_ur, bg=C["BG_CARD"])
        ur_row.pack(fill="x", padx=6, pady=2)
        b_undo = ttk.Button(ur_row, text=self._t("btn_undo"), command=self._undo)
        b_undo.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self._doc_buttons.append(b_undo)
        b_redo = ttk.Button(ur_row, text=self._t("btn_redo"), command=self._redo)
        b_redo.pack(side="left", expand=True, fill="x", padx=2, pady=2)
        self._doc_buttons.append(b_redo)

        f2 = section(self._t("sec_page"))
        tk.Label(f2, text=self._t("lbl_rotate"), bg=C["BG_CARD"], fg=C["TEXT_SUB"],
                 font=self._font(-2)).pack(anchor="w", padx=8)
        rot_row1 = tk.Frame(f2, bg=C["BG_CARD"])
        rot_row1.pack(fill="x", padx=6, pady=(2, 0))
        for deg, lkey in [(270, "btn_rot_left"), (90, "btn_rot_right")]:
            b = ttk.Button(rot_row1, text=self._t(lkey),
                           command=lambda d=deg: self._rotate_selected(d))
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            self._doc_buttons.append(b)
        rot_row2 = tk.Frame(f2, bg=C["BG_CARD"])
        rot_row2.pack(fill="x", padx=6, pady=(0, 2))
        b180 = ttk.Button(rot_row2, text=self._t("btn_rot_180"),
                          command=lambda: self._rotate_selected(180))
        b180.pack(fill="x", padx=2, pady=2)
        self._doc_buttons.append(b180)

        btn(f2, self._t("btn_delete"), self._delete_selected,
            "Danger.TButton", needs_doc=True)

        f3 = section(self._t("sec_crop"))
        self.crop_mode_var = tk.BooleanVar(value=False)
        self.crop_toggle_btn = ttk.Button(
            f3, text=self._t("crop_mode_off"),
            command=self._toggle_crop_mode)
        self.crop_toggle_btn.pack(fill="x", padx=8, pady=(4,2))
        self._doc_buttons.append(self.crop_toggle_btn)
        tk.Label(f3, text=self._t("crop_hint"),
                 bg=C["BG_CARD"], fg=C["TEXT_SUB"], font=self._font(-2)).pack(anchor="w", padx=8)

        self.crop_info_var = tk.StringVar(value=self._t("crop_no_sel"))
        tk.Label(f3, textvariable=self.crop_info_var,
                 bg=C["BG_CARD"], fg=C["TEXT_SUB"], font=self._font(-2)).pack(anchor="w", padx=8, pady=2)

        btn(f3, self._t("btn_crop"), self._crop_page, needs_doc=True)
        btn(f3, self._t("btn_crop_reset"), self._crop_reset, "Danger.TButton",
            needs_doc=True)

        f4 = section(self._t("sec_insert"))
        btn(f4, self._t("btn_insert_head"), lambda: self._insert_from_file("head"), needs_doc=True)
        btn(f4, self._t("btn_insert_tail"), lambda: self._insert_from_file("tail"), needs_doc=True)
        btn(f4, self._t("btn_insert_pos"), lambda: self._insert_from_file("pos"),
            needs_doc=True)
        btn(f4, self._t("btn_merge"), self._merge_pdf, needs_doc=True)

        # プラグインセクション
        f_plug = section(self._t("sec_plugin"))
        btn(f_plug, self._t("btn_plugin_mgr"), self._open_plugin_dialog)
        # 有効プラグインのUI構築
        self._plugin_ui_frame = tk.Frame(parent, bg=C["BG_PANEL"])
        self._plugin_ui_frame.pack(fill="x", padx=0, pady=0)
        self._build_plugin_ui()

        # 初期状態: すべてのdoc依存ボタンを disabled にする
        self._update_doc_buttons_state()

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
            self._set_status(self._t("undo_empty"))
            return
        if self.doc:
            self._redo_stack.append({
                'pdf_bytes': self.doc.tobytes(),
                'current_page': self.current_page,
                'selected_pages': set(self.selected_pages),
            })
        state = self._undo_stack.pop()
        self._restore_state(state)
        self._set_status(self._t("undo_done"))

    def _redo(self):
        if not self._redo_stack:
            self._set_status(self._t("redo_empty"))
            return
        if self.doc:
            self._undo_stack.append({
                'pdf_bytes': self.doc.tobytes(),
                'current_page': self.current_page,
                'selected_pages': set(self.selected_pages),
            })
        state = self._redo_stack.pop()
        self._restore_state(state)
        self._set_status(self._t("redo_done"))

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
        paths = filedialog.askopenfilenames(
            filetypes=[(self._t("filetypes_pdf"), "*.pdf"), (self._t("filetypes_all"), "*.*")])
        if not paths:
            return
        if len(paths) == 1:
            self._open_pdf_path(paths[0])
        else:
            # 複数ファイル選択時は結合して開く
            self._open_multiple_pdfs(list(paths))

    def _open_multiple_pdfs(self, paths):
        """複数PDFを結合して1つのドキュメントとして開く"""
        MergeOrderDialog(self.root, paths, self._do_open_merged, lang=self.lang)

    def _do_open_merged(self, ordered_paths):
        """結合順ダイアログ確定後、結合して開く"""
        try:
            if self.doc:
                self.doc.close()
            merged = fitz.open()
            total = 0
            for path in ordered_paths:
                src = fitz.open(path)
                merged.insert_pdf(src)
                total += len(src)
                src.close()
            self.doc = merged
            self.filepath = None  # 結合結果なので保存先なし
            self.current_page = 0
            self.selected_pages.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._invalidate_thumb_cache()
            self._refresh_all()
            names = ", ".join(os.path.basename(p) for p in ordered_paths)
            self._set_status(self._t("status_merged_open").format(
                count=len(ordered_paths), total=total, names=names))
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

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
            self._set_status(self._t("status_opened").format(
                name=os.path.basename(path), n=len(self.doc)))
            self.plugin_manager.fire_event("on_file_open", self, path)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _save_file(self):
        """上書き保存 — 確認ダイアログ付き (#14)"""
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
            return
        if not self.filepath:
            # 結合して開いた場合など保存先がない場合は名前を付けて保存
            self._save_as()
            return
        if not messagebox.askyesno(self._t("save_confirm_title"),
                                    self._t("save_confirm_msg").format(
                                        name=os.path.basename(self.filepath))):
            return
        try:
            try:
                self.doc.save(self.filepath, incremental=True,
                              encryption=fitz.PDF_ENCRYPT_KEEP)
            except Exception:
                tmp = self.filepath + ".tmp"
                self.doc.save(tmp)
                os.replace(tmp, self.filepath)
            self._set_status(self._t("status_saved").format(name=os.path.basename(self.filepath)))
            self.plugin_manager.fire_event("on_file_save", self, self.filepath)
        except Exception as e:
            messagebox.showerror(self._t("err_save_title"),
                                 self._t("err_save_msg").format(e=e))

    def _save_as(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")])
        if not path:
            return
        try:
            self.doc.save(path)
            self.filepath = path
            self._set_status(self._t("status_saved").format(name=os.path.basename(path)))
            self.plugin_manager.fire_event("on_file_save", self, path)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

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
        self._set_status(self._t("status_rotated").format(count=len(targets), deg=deg))
        self.plugin_manager.fire_event("on_page_rotate", self, targets, deg)

    def _delete_selected(self):
        if not self._check_doc():
            return
        targets = sorted(self._get_targets(), reverse=True)
        if not targets:
            messagebox.showinfo(self._t("info_title"), self._t("info_no_page_sel"))
            return
        # 全ページ削除防止 (#17)
        if len(targets) >= len(self.doc):
            messagebox.showwarning(self._t("warn_del_all_title"), self._t("warn_del_all"))
            return
        if not messagebox.askyesno(self._t("confirm_title"),
                                    self._t("confirm_del").format(count=len(targets))):
            return
        self._save_undo()
        for i in targets:
            self.doc.delete_page(i)
        self.selected_pages.clear()
        self.current_page = min(self.current_page, max(0, len(self.doc)-1))
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(self._t("status_deleted").format(count=len(targets)))
        self.plugin_manager.fire_event("on_page_delete", self, targets)

    # ── トリミング (#16 視覚強調)
    def _toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            self.crop_toggle_btn.configure(
                text=self._t("crop_mode_on"),
                style="CropOn.TButton")
            self.preview_canvas.configure(cursor="crosshair")
        else:
            self.crop_toggle_btn.configure(
                text=self._t("crop_mode_off"),
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
                sx, sy, ex, ey, outline=C["ACCENT"], width=2, dash=(4,3))
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
        self.crop_info_var.set(self._t("crop_no_sel"))
        self._clear_crop_overlay()

    def _crop_page(self):
        if not self._check_doc():
            return
        if not self.crop_rect:
            messagebox.showinfo(self._t("info_title"), self._t("info_crop_drag"))
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
        # CropBox を MediaBox の範囲内に厳密にクランプ
        # pymupdf は浮動小数点で厳密に比較するため余裕を持たせる
        EPS = 0.01
        new_rect = fitz.Rect(
            max(round(new_rect.x0, 2), mb.x0 + EPS),
            max(round(new_rect.y0, 2), mb.y0 + EPS),
            min(round(new_rect.x1, 2), mb.x1 - EPS),
            min(round(new_rect.y1, 2), mb.y1 - EPS)
        )
        if new_rect.is_empty or new_rect.is_infinite or new_rect.width < 1 or new_rect.height < 1:
            messagebox.showerror(self._t("err_title"), self._t("err_crop_small"))
            return
        try:
            page.set_cropbox(new_rect)
        except ValueError as e:
            messagebox.showerror(self._t("err_crop_title"),
                                 self._t("err_crop_msg").format(e=e))
            return
        self.crop_rect = None
        self.crop_mode = False
        self.crop_toggle_btn.configure(text=self._t("crop_mode_off"), style="TButton")
        self.preview_canvas.configure(cursor="")
        self.crop_info_var.set(self._t("crop_no_sel"))
        self._invalidate_thumb_cache([self.current_page])
        self._refresh_all()
        self._set_status(self._t("status_cropped").format(page=self.current_page+1))
        self.plugin_manager.fire_event("on_page_crop", self, self.current_page)

    def _insert_from_file(self, mode="pos"):
        """別PDFから挿入。mode: 'head'=先頭, 'tail'=末尾, 'pos'=指定位置"""
        if not self._check_doc():
            return
        paths = filedialog.askopenfilenames(
            title=self._t("dlg_insert_title"),
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")])
        if not paths:
            return

        if mode == "head":
            insert_at = 0
        elif mode == "tail":
            insert_at = len(self.doc)
        else:
            pos = simpledialog.askinteger(
                self._t("dlg_insert_pos_title"),
                self._t("dlg_insert_pos_msg").format(n=len(self.doc)),
                minvalue=0, maxvalue=len(self.doc),
                initialvalue=self.current_page + 1)
            if pos is None:
                return
            insert_at = pos

        # 複数ファイル時は結合順ダイアログを表示
        if len(paths) > 1:
            MergeOrderDialog(self.root, list(paths),
                             lambda ordered: self._do_insert(ordered, insert_at),
                             lang=self.lang)
        else:
            self._do_insert(list(paths), insert_at)

    def _do_insert(self, ordered_paths, insert_at):
        """結合順確定後に実際の挿入を行う"""
        self._save_undo()
        try:
            total = 0
            pos = insert_at
            for path in ordered_paths:
                src = fitz.open(path)
                self.doc.insert_pdf(src, start_at=pos)
                pos += len(src)
                total += len(src)
                src.close()
            self._invalidate_thumb_cache()
            self._refresh_all()
            if insert_at == 0:
                where = self._t("status_insert_head")
            elif insert_at >= len(self.doc) - total:
                where = self._t("status_insert_tail")
            else:
                where = self._t("status_insert_pos").format(pos=insert_at)
            self._set_status(self._t("status_inserted").format(
                count=len(ordered_paths), total=total, where=where))
            self.plugin_manager.fire_event("on_insert", self, ordered_paths, insert_at)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

    def _merge_pdf(self):
        if not self._check_doc():
            return
        paths = filedialog.askopenfilenames(
            title=self._t("dlg_merge_title"),
            filetypes=[(self._t("filetypes_pdf"), "*.pdf")])
        if not paths:
            return
        MergeOrderDialog(self.root, list(paths), self._do_merge, lang=self.lang)

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
            self._set_status(self._t("status_merged").format(
                count=len(ordered_paths), total=total))
            self.plugin_manager.fire_event("on_merge", self, ordered_paths)
        except Exception as e:
            messagebox.showerror(self._t("err_title"), str(e))

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
            # 空状態: 案内文を中央に表示
            self.preview_canvas.update_idletasks()
            cw = self.preview_canvas.winfo_width()
            ch = self.preview_canvas.winfo_height()
            self.preview_canvas.create_text(
                cw // 2, ch // 2 - 16,
                text=self._t("preview_empty1"),
                fill=C["TEXT_SUB"], font=self._font(4))
            self.preview_canvas.create_text(
                cw // 2, ch // 2 + 16,
                text=self._t("preview_empty2"),
                fill=C["TEXT_SUB"], font=self._font())
            return
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom * 1.5, self.zoom * 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        self.preview_img_ref = photo
        pad = 10
        # ページの影（ドロップシャドウ風）で境界を明確化
        self.preview_canvas.create_rectangle(
            pad + 3, pad + 3, pad + pix.width + 3, pad + pix.height + 3,
            fill=C["TEXT_SUB"], outline="")
        self.preview_canvas.create_rectangle(
            pad, pad, pad + pix.width, pad + pix.height,
            fill="", outline=C["TEXT_SUB"], width=1)
        self.preview_canvas.create_image(pad, pad, anchor="nw", image=photo)
        self.preview_canvas.configure(
            scrollregion=(0, 0, pix.width + pad * 2, pix.height + pad * 2))

    # ══════════════════════════════════════════
    #  ナビゲーション & ズーム
    # ══════════════════════════════════════════
    def _prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self._refresh_all()
            self.plugin_manager.fire_event("on_page_change", self, self.current_page)

    def _next_page(self):
        if self.doc and self.current_page < len(self.doc)-1:
            self.current_page += 1
            self._refresh_all()
            self.plugin_manager.fire_event("on_page_change", self, self.current_page)

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
        self._update_doc_buttons_state()
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page+1} / {n}" if n else "- / -")
        # ナビゲーションボタンの活性/非活性制御
        if n <= 1:
            self.prev_btn.state(["disabled"])
            self.next_btn.state(["disabled"])
        else:
            self.prev_btn.state(["!disabled"] if self.current_page > 0 else ["disabled"])
            self.next_btn.state(["!disabled"] if self.current_page < n - 1 else ["disabled"])

    def _refresh_thumbs_selection_only(self):
        """選択・カレント変更のみ — 画像再生成なし (#8)"""
        frames = self.thumb_inner.winfo_children()
        for i, frame in enumerate(frames):
            is_sel = i in self.selected_pages
            is_cur = i == self.current_page
            bg = C["ACCENT"] if is_sel else (C["BG_CARD"] if is_cur else C["BG_PANEL"])
            frame.configure(bg=bg)
            for child in frame.winfo_children():
                child.configure(bg=bg)
        n = len(self.doc) if self.doc else 0
        self.page_label.configure(
            text=f"{self.current_page+1} / {n}" if n else "- / -")
        # ナビゲーションボタンの活性/非活性制御
        if n <= 1:
            self.prev_btn.state(["disabled"])
            self.next_btn.state(["disabled"])
        else:
            self.prev_btn.state(["!disabled"] if self.current_page > 0 else ["disabled"])
            self.next_btn.state(["!disabled"] if self.current_page < n - 1 else ["disabled"])

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
        bg = C["ACCENT"] if is_sel else (C["BG_CARD"] if is_cur else C["BG_PANEL"])

        frame = tk.Frame(self.thumb_inner, bg=bg, cursor="hand2")
        frame.pack(fill="x", padx=6, pady=3)

        lbl = tk.Label(frame, image=photo, bg=bg)
        lbl.pack(pady=(4,0))
        tk.Label(frame, text=f"p.{i+1}", bg=bg, fg=C["TEXT_MAIN"],
                 font=self._font(-2)).pack(pady=(0,4))

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
                    # 遅延実行でダブルクリックと競合しないようにする
                    self._pending_click = self.root.after(
                        250, lambda: self._single_click(idx))
            self._dnd_src_idx  = None
            self._dnd_dragging = False
            self._dnd_destroy_ghost()
            self._dnd_clear_indicator()

        def on_double(event, idx=i):
            # シングルクリックの遅延実行をキャンセル
            if hasattr(self, '_pending_click') and self._pending_click:
                self.root.after_cancel(self._pending_click)
                self._pending_click = None
            self._show_page_popup(idx)

        for w in (frame, lbl):
            w.bind('<ButtonPress-1>',   on_press)
            w.bind('<B1-Motion>',       on_motion)
            w.bind('<ButtonRelease-1>', on_release)
            w.bind('<Double-Button-1>', on_double)

    # ══ ページ拡大表示ポップアップ ═════════════════════
    def _single_click(self, idx):
        """遅延実行されるシングルクリック処理"""
        self._pending_click = None
        self.selected_pages.clear()
        self.current_page = idx
        self._refresh_all()

    def _show_page_popup(self, idx):
        """サムネイルダブルクリックでページを拡大表示"""
        if not self.doc or idx >= len(self.doc):
            return
        popup = tk.Toplevel(self.root)
        popup.configure(bg=C["PREVIEW_BG"])
        popup.geometry("900x700")
        popup.transient(self.root)

        # ツールバー
        toolbar = tk.Frame(popup, bg=C["BG_PANEL"], height=40)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        popup_state = {"idx": idx, "zoom": 1.5}  # ミュータブルで共有
        n = len(self.doc)

        def update_nav():
            """ナビゲーションボタンの活性/非活性とラベル更新"""
            i = popup_state["idx"]
            page_lbl.configure(text=f"{i+1} / {n}")
            popup.title(f"ページ {i+1} / {n}")
            if n <= 1:
                prev_btn.state(["disabled"])
                next_btn.state(["disabled"])
            else:
                prev_btn.state(["!disabled"] if i > 0 else ["disabled"])
                next_btn.state(["!disabled"] if i < n - 1 else ["disabled"])

        def render_page():
            canvas.delete("all")
            page = self.doc[popup_state["idx"]]
            mat = fitz.Matrix(popup_state["zoom"], popup_state["zoom"])
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            canvas._photo = photo  # 参照を保持
            pad = 10
            canvas.create_rectangle(
                pad + 3, pad + 3, pad + pix.width + 3, pad + pix.height + 3,
                fill=C["TEXT_SUB"], outline="")
            canvas.create_rectangle(
                pad, pad, pad + pix.width, pad + pix.height,
                fill="", outline=C["TEXT_SUB"], width=1)
            canvas.create_image(pad, pad, anchor="nw", image=photo)
            canvas.configure(scrollregion=(0, 0, pix.width + pad * 2, pix.height + pad * 2))
            zoom_lbl.configure(text=f"{int(popup_state['zoom'] / 1.5 * 100)}%")
            update_nav()

        def go_prev():
            if popup_state["idx"] > 0:
                popup_state["idx"] -= 1
                render_page()

        def go_next():
            if popup_state["idx"] < n - 1:
                popup_state["idx"] += 1
                render_page()

        def zoom_in():
            popup_state["zoom"] = min(5.0, popup_state["zoom"] + 0.3)
            render_page()

        def zoom_out():
            popup_state["zoom"] = max(0.3, popup_state["zoom"] - 0.3)
            render_page()

        # ナビゲーション（左側）
        prev_btn = ttk.Button(toolbar, text="◀", command=go_prev)
        prev_btn.pack(side="left", padx=(10, 2), pady=6)
        page_lbl = tk.Label(toolbar, text=f"{idx+1} / {n}",
                            bg=C["BG_PANEL"], fg=C["TEXT_MAIN"],
                            font=self._font(0, "bold"))
        page_lbl.pack(side="left", padx=4)
        next_btn = ttk.Button(toolbar, text="▶", command=go_next)
        next_btn.pack(side="left", padx=2)

        # ズーム・閉じる（右側）
        zoom_lbl = tk.Label(toolbar, text="100%", bg=C["BG_PANEL"], fg=C["TEXT_SUB"],
                            font=self._font(-1))
        zoom_lbl.pack(side="right", padx=6)
        ttk.Button(toolbar, text="🔍 縮小", command=zoom_out).pack(side="right", padx=2, pady=6)
        ttk.Button(toolbar, text="🔍 拡大", command=zoom_in).pack(side="right", padx=2, pady=6)
        ttk.Button(toolbar, text="✕ 閉じる", command=popup.destroy,
                   style="Danger.TButton").pack(side="right", padx=6, pady=6)

        # キャンバス
        frame = tk.Frame(popup, bg=C["PREVIEW_BG"])
        frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(frame, bg=C["PREVIEW_BG"], highlightthickness=0)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        render_page()
        popup.focus_set()

    # ══ D&D ヘルパー ══════════════════════════════
    def _dnd_start_ghost(self, idx):
        if self._dnd_ghost:
            self._dnd_ghost.destroy()
        photo = self.thumb_images[idx]
        ghost = tk.Toplevel(self.root)
        ghost.overrideredirect(True)
        ghost.attributes('-alpha', 0.6)
        ghost.attributes('-topmost', True)
        lbl = tk.Label(ghost, image=photo, bg=C["BG_CARD"],
                       relief='flat', bd=2)
        lbl.pack()
        num = tk.Label(ghost, text=f'p.{idx+1}', bg=C["BG_CARD"],
                       fg=C["ACCENT"], font=self._font(-2, "bold"))
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
            fill=C["ACCENT"], width=3, dash=(6, 3))

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
        dest = max(0, min(dest, n))
        # move_page の仕様: dest が src より後ろの場合は dest-1 が実際の位置
        # dest == n の場合は末尾への移動
        if dest == src or dest == src + 1:
            return  # 同じ位置または直後（実質移動なし）
        self._save_undo()
        # fitz.move_page(src, dest) は dest の前に挿入
        # 末尾に移動したい場合は dest = -1 または dest = n
        if dest >= n:
            self.doc.move_page(src, -1)  # -1 = 末尾
            actual_dest = n - 1
        else:
            actual_dest = dest if dest < src else dest - 1
            self.doc.move_page(src, dest)
        self.current_page = actual_dest
        self.selected_pages.clear()
        self._invalidate_thumb_cache()
        self._refresh_all()
        self._set_status(self._t("status_dnd_moved").format(src=src+1, dest=actual_dest+1))

    # ══════════════════════════════════════════
    #  ユーティリティ
    # ══════════════════════════════════════════
    def _update_doc_buttons_state(self):
        """ファイル開閉状態に応じてボタンの活性/非活性を切り替え"""
        state = ["!disabled"] if self.doc else ["disabled"]
        for b in self._doc_buttons:
            try:
                b.state(state)
            except Exception:
                pass

    def _check_doc(self):
        if not self.doc:
            messagebox.showinfo(self._t("info_title"), self._t("info_no_doc"))
            return False
        return True

    def _get_targets(self):
        return list(self.selected_pages) if self.selected_pages else [self.current_page]

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
        if not hasattr(self, '_plugin_ui_frame') or self._plugin_ui_frame is None:
            return
        for w in self._plugin_ui_frame.winfo_children():
            w.destroy()
        for plugin_id, plugin in self.plugin_manager.plugins.items():
            try:
                pf = tk.Frame(self._plugin_ui_frame, bg=C["BG_CARD"], bd=0)
                pf.pack(fill="x", padx=10, pady=3)
                tk.Label(pf, text=f"🔌 {plugin.name}",
                         bg=C["BG_CARD"], fg=C["WARNING"],
                         font=self._font(-1, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
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
        SettingsDialog(self.root, self.settings, self._apply_settings)

    def _apply_settings(self, new_settings):
        """設定変更を適用してUIを再構築"""
        self.settings = new_settings
        self.font_size = new_settings.get("font_size", 10)
        self.lang = new_settings.get("lang", self.lang)
        global _current_font_size
        _current_font_size = self.font_size
        _apply_theme(new_settings.get("theme", "dark"))
        _save_settings(new_settings)
        self._rebuild_ui()
        self._set_status(self._t("status_settings"))

    def _rebuild_ui(self):
        """テーマ・フォント変更時にUI全体を再構築"""
        # メインフレーム以下を破棄して再構築
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
        w, h = 360, 260
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")

    def _build(self):
        tk.Label(self, text="PageFolio",
                 bg=C["BG_DARK"], fg=C["ACCENT"],
                 font=("Segoe UI", 16, "bold")).pack(pady=(20, 2))
        tk.Label(self, text="v0.9.2",
                 bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=self._font(0)).pack()
        tk.Label(self, text=self._L["about_subtitle"],
                 bg=C["BG_DARK"], fg=C["TEXT_MAIN"],
                 font=self._font(-1)).pack(pady=(2, 12))

        sep = tk.Frame(self, bg=C["BG_CARD"], height=1)
        sep.pack(fill="x", padx=30, pady=4)

        tk.Label(self, text="Copyright (c) 2026 mistyura",
                 bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=self._font(-2)).pack(pady=(6, 2))
        tk.Label(self, text="MIT License",
                 bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=self._font(-2)).pack()
        tk.Label(self, text="https://github.com/mistyura/PageFolio",
                 bg=C["BG_DARK"], fg=C["SUCCESS"],
                 font=self._font(-2)).pack(pady=(2, 16))

        ttk.Button(self, text=self._L["about_ok"], command=self.destroy,
                   style="Accent.TButton").pack(pady=(0, 16))


# ══════════════════════════════════════════
#  設定ダイアログ
# ══════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_settings, callback):
        super().__init__(parent)
        lang = current_settings.get("lang", "ja")
        self._L = LANG[lang]
        self.title(self._L["settings_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        self.callback = callback
        self.current_settings = dict(current_settings)

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        fs = current_settings.get("font_size", 12)
        w = max(380, int(fs * 32))
        h = max(280, int(fs * 24))
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")

    def _build(self):
        tk.Label(self, text=self._L["settings_heading"],
                 bg=C["BG_DARK"], fg=C["ACCENT"],
                 font=("Segoe UI", 13, "bold")).pack(pady=(14, 10))

        # テーマ選択
        tf = tk.Frame(self, bg=C["BG_DARK"])
        tf.pack(fill="x", padx=24, pady=6)
        tk.Label(tf, text=self._L["settings_theme"], bg=C["BG_DARK"], fg=C["TEXT_MAIN"],
                 font=("Segoe UI", 10)).pack(side="left")
        self.theme_var = tk.StringVar(value=self.current_settings.get("theme", "dark"))
        theme_options = [
            (self._L["settings_theme_dark"], "dark"),
            (self._L["settings_theme_light"], "light"),
            (self._L["settings_theme_system"], "system"),
        ]
        for text, value in theme_options:
            tk.Radiobutton(tf, text=text, variable=self.theme_var, value=value,
                           bg=C["BG_DARK"], fg=C["TEXT_MAIN"],
                           selectcolor=C["BG_CARD"], activebackground=C["BG_DARK"],
                           activeforeground=C["TEXT_MAIN"],
                           font=("Segoe UI", 9)).pack(side="left", padx=6)

        # フォントサイズ
        ff = tk.Frame(self, bg=C["BG_DARK"])
        ff.pack(fill="x", padx=24, pady=6)
        tk.Label(ff, text=self._L["settings_font"], bg=C["BG_DARK"], fg=C["TEXT_MAIN"],
                 font=("Segoe UI", 10)).pack(side="left")
        self.font_var = tk.IntVar(value=self.current_settings.get("font_size", 10))
        tk.Spinbox(ff, from_=8, to=16, textvariable=self.font_var, width=4,
                   font=("Segoe UI", 10),
                   bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
                   buttonbackground=C["BG_PANEL"],
                   insertbackground=C["TEXT_MAIN"]).pack(side="left", padx=8)
        tk.Label(ff, text=self._L["settings_font_hint"], bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=("Segoe UI", 9)).pack(side="left")

        # プレビュー
        self.preview_label = tk.Label(self, text=self._L["settings_preview_text"],
                                       bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
                                       font=("Segoe UI", self.font_var.get()),
                                       padx=12, pady=8)
        self.preview_label.pack(padx=24, pady=8, fill="x")
        self.font_var.trace_add("write", self._update_preview)

        # ボタン
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(8, 14))
        ttk.Button(btn_row, text=self._L["settings_apply"], style="Accent.TButton",
                   command=self._apply).pack(side="left", padx=8)
        ttk.Button(btn_row, text=self._L["settings_cancel"],
                   command=self.destroy).pack(side="left", padx=8)

    def _update_preview(self, *_):
        try:
            size = self.font_var.get()
            size = max(8, min(16, size))
            self.preview_label.configure(font=("Segoe UI", size))
        except Exception:
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
        tk.Label(self, text=self._L["plugin_heading"],
                 bg=C["BG_DARK"], fg=C["ACCENT"],
                 font=self._font(2, "bold")).pack(pady=(14, 4))

        plugins_dir = _get_plugins_dir()
        tk.Label(self,
                 text=self._L["plugin_dir_label"].format(path=plugins_dir),
                 bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=self._font(-2), wraplength=450).pack(pady=(0, 8))

        # プラグインリスト
        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        canvas = tk.Canvas(list_frame, bg=C["BG_PANEL"], highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self._list_inner = tk.Frame(canvas, bg=C["BG_PANEL"])
        canvas.create_window((0, 0), window=self._list_inner, anchor="nw",
                             tags="inner")
        self._list_inner.bind("<Configure>",
                              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure("inner", width=e.width))
        self._list_canvas = canvas

        self._refresh_list()

        # ボタン行
        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=(8, 4))
        ttk.Button(btn_row, text=self._L["plugin_rescan"],
                   command=self._rescan).pack(side="left", padx=4)
        ttk.Button(btn_row, text=self._L["plugin_open_folder"],
                   command=self._open_folder).pack(side="left", padx=4)

        ok_row = tk.Frame(self, bg=C["BG_DARK"])
        ok_row.pack(pady=(4, 14))
        ttk.Button(ok_row, text=self._L["plugin_close"], style="Accent.TButton",
                   command=self._close).pack(side="left", padx=8)

    def _refresh_list(self):
        for w in self._list_inner.winfo_children():
            w.destroy()

        all_plugins = self.pm.all_plugins
        if not all_plugins:
            tk.Label(self._list_inner,
                     text=self._L["plugin_empty"].format(dir=PLUGINS_DIR),
                     bg=C["BG_PANEL"], fg=C["TEXT_SUB"],
                     font=self._font(), justify="center").pack(pady=30)
            return

        self._check_vars = {}
        for plugin_id, plugin in all_plugins.items():
            row = tk.Frame(self._list_inner, bg=C["BG_CARD"], bd=0)
            row.pack(fill="x", padx=6, pady=3)

            var = tk.BooleanVar(value=self.pm.is_enabled(plugin_id))
            self._check_vars[plugin_id] = var

            cb = tk.Checkbutton(row, variable=var,
                                command=lambda pid=plugin_id: self._toggle(pid),
                                bg=C["BG_CARD"], activebackground=C["BG_CARD"],
                                selectcolor=C["BG_PANEL"])
            cb.pack(side="left", padx=(8, 4), pady=6)

            info = tk.Frame(row, bg=C["BG_CARD"])
            info.pack(side="left", fill="x", expand=True, pady=4)

            name_text = f"{plugin.name}  v{plugin.version}"
            tk.Label(info, text=name_text,
                     bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
                     font=self._font(0, "bold"), anchor="w").pack(anchor="w")

            if plugin.description:
                tk.Label(info, text=plugin.description,
                         bg=C["BG_CARD"], fg=C["TEXT_SUB"],
                         font=self._font(-2), anchor="w",
                         wraplength=350).pack(anchor="w")

            if plugin.author:
                tk.Label(info, text=self._L["plugin_author"].format(author=plugin.author),
                         bg=C["BG_CARD"], fg=C["TEXT_SUB"],
                         font=self._font(-2), anchor="w").pack(anchor="w")

    def _toggle(self, plugin_id):
        if self._check_vars[plugin_id].get():
            self.pm.enable_plugin(plugin_id, self.app)
        else:
            self.pm.disable_plugin(plugin_id, self.app)
        self.app._reload_plugins()

    def _rescan(self):
        """プラグインを再検出・再読み込みする"""
        # 既存プラグインを一度アンロード
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
        # Windowsのエクスプローラーで開く
        try:
            os.startfile(plugins_dir)
        except AttributeError:
            # Windows以外の場合
            import subprocess
            subprocess.Popen(["xdg-open", plugins_dir])

    def _close(self):
        self.app._reload_plugins()
        self.destroy()


# ══════════════════════════════════════════
#  結合順ダイアログ (#3 ページ数キャッシュ)
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
        fs = self._font_size
        w = max(480, int(fs * 40))
        # ファイル数に応じて高さを調整（1ファイルあたり約fs*2.5px分加算）
        base_h = max(420, int(fs * 32))
        extra_h = max(0, len(self.paths) - 4) * int(fs * 2.5)
        h = min(base_h + extra_h, parent.winfo_height() - 40)  # 親を超えない
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")
        self.minsize(400, 350)

    def _font(self, delta=0, weight=None):
        size = max(7, self._font_size + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _build(self):
        tk.Label(self, text=self._L["merge_heading"],
                 bg=C["BG_DARK"], fg=C["ACCENT"],
                 font=self._font(2, "bold")).pack(pady=(14, 4))
        tk.Label(self,
                 text=self._L["merge_hint"],
                 bg=C["BG_DARK"], fg=C["TEXT_SUB"],
                 font=self._font(-1), justify="center").pack(pady=(0, 8))

        list_frame = tk.Frame(self, bg=C["BG_PANEL"], bd=0)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        list_height = max(6, min(20, len(self.paths) + 2))
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=sb.set,
            bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
            selectbackground=C["ACCENT"], selectforeground="#fff",
            font=self._font(-1),
            activestyle="none",
            bd=0, highlightthickness=0,
            height=list_height)
        sb.configure(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)

        for p in self.paths:
            pc = self._page_counts.get(p, 0)
            self.listbox.insert(tk.END, f"  {os.path.basename(p)}  ({pc}p)")

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(fill="x", padx=16, pady=6)
        ttk.Button(btn_row, text=self._L["merge_up"],
                   command=self._move_up).pack(side="left", padx=4)
        ttk.Button(btn_row, text=self._L["merge_down"],
                   command=self._move_down).pack(side="left", padx=4)
        ttk.Button(btn_row, text=self._L["merge_remove"],
                   style="Danger.TButton",
                   command=self._remove_item).pack(side="left", padx=4)

        self.info_var = tk.StringVar()
        tk.Label(self, textvariable=self.info_var,
                 bg=C["BG_DARK"], fg=C["SUCCESS"],
                 font=self._font(-1)).pack(pady=2)
        self._update_info()

        ok_row = tk.Frame(self, bg=C["BG_DARK"])
        ok_row.pack(pady=(4, 14))
        ttk.Button(ok_row, text=self._L["merge_confirm"],
                   style="Accent.TButton",
                   command=self._confirm).pack(side="left", padx=8)
        ttk.Button(ok_row, text=self._L["merge_cancel"],
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
        self.info_var.set(self._L["merge_info"].format(count=len(self.paths), total=total))

    def _confirm(self):
        if not self.paths:
            messagebox.showinfo(self._L.get("info_title", "Info"),
                                self._L["merge_no_files"], parent=self)
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
