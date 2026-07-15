# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""メインアプリケーションクラス — Mixin を統合した PDFEditorApp"""

import logging
import os
import tkinter as tk
from collections import deque
from tkinter import messagebox

from pagefolio.constants import LANG, SUPPORTED_EXTENSIONS, C
from pagefolio.dialogs import PluginDialog, SettingsDialog
from pagefolio.dnd import DnDMixin
from pagefolio.file_drop import _setup_file_drop
from pagefolio.file_ops import FileOpsMixin
from pagefolio.ocr import OCRMixin
from pagefolio.page_ops import PageOpsMixin
from pagefolio.pagination import clamp_page_size
from pagefolio.plugins import PluginManager
from pagefolio.print_ops import PrintOpsMixin
from pagefolio.redact_ops import RedactOpsMixin
from pagefolio.settings import (
    _apply_theme,
    _load_settings,
    _save_settings,
    set_current_font_size,
)
from pagefolio.ui_builder import UIBuilderMixin
from pagefolio.viewer import ViewerMixin

logger = logging.getLogger(__name__)


def merge_shortcuts(default_shortcuts, custom_shortcuts):
    """既定＋ユーザー設定のショートカット辞書をマージする（後勝ち）。

    Tk/fitz 非依存の純関数（V171-TEST-01・D-13）。
    """
    return {**default_shortcuts, **custom_shortcuts}


def shift_variant_keysym(keysym):
    """Control-小文字 の keysym から Shift 補完用の大文字版 keysym を返す。

    対象外パターンは None を返す。Tk/fitz 非依存の純関数（V171-TEST-01・D-13）。
    """
    if keysym.startswith("<Control-") and len(keysym) == 11 and keysym[-2].islower():
        return keysym[:-2] + keysym[-2].upper() + ">"
    return None


_SHORTCUT_MOD_ORDER = ("Control", "Alt", "Shift")


def build_keysym_from_event(
    state, keysym, shift_mask=0x1, control_mask=0x4, alt_mask=0x20000
):
    """event.state ビットマスクと event.keysym から Tk bind 用文字列を組み立てる。

    ショートカット GUI 編集の実キーキャプチャ方式を支える純関数（V171-UIUX-01・D-02）。
    修飾は Control, Alt, Shift の順で連結し、修飾なしの場合はキー単体を返す。
    """
    mods = []
    if state & control_mask:
        mods.append("Control")
    if state & alt_mask:
        mods.append("Alt")
    if state & shift_mask:
        mods.append("Shift")
    if not mods:
        return f"<{keysym}>"
    return f"<{'-'.join(mods)}-{keysym}>"


def find_duplicate_binding(shortcuts, cmd_name, new_keysym):
    """新規割当キーが自分以外のコマンドと重複していないか判定する。

    重複割当を保存時に拒否する要件を支える純関数（V171-UIUX-01・D-04）。
    衝突しているコマンド名を返し、衝突がなければ None を返す。
    """
    if not new_keysym:
        return None
    for other_cmd, other_keysym in shortcuts.items():
        if other_cmd != cmd_name and other_keysym == new_keysym:
            return other_cmd
    return None


def keysym_to_display(keysym):
    """Tk keysym 文字列を人間可読な表示形式へ変換する。

    ショートカット一覧の可読性向上を支える純関数（V171-UIUX-01・D-07）。
    内部保存は Tk keysym のまま変えず、表示専用に変換する。
    """
    if not keysym:
        return ""
    inner = keysym.strip("<>")
    parts = inner.split("-")
    *mods, key = parts
    display_mods = {"Control": "Ctrl", "Alt": "Alt", "Shift": "Shift"}
    out = [display_mods.get(m, m) for m in mods]
    out.append(key.upper() if len(key) == 1 else key)
    return "+".join(out)


class PDFEditorApp(
    UIBuilderMixin,
    FileOpsMixin,
    PageOpsMixin,
    RedactOpsMixin,
    ViewerMixin,
    DnDMixin,
    OCRMixin,
    PrintOpsMixin,
):
    MAX_UNDO = 20

    def __init__(self, root):
        logging.basicConfig(
            level=logging.WARNING,
            format="%(levelname)s:%(name)s:%(message)s",
        )
        self.root = root
        self.root.title("PageFolio")
        self.root.minsize(800, 600)

        # 設定読み込み・テーマ適用
        self.settings = _load_settings()
        self.font_size = self.settings.get("font_size", 10)
        self.lang = self.settings.get("lang", "ja")
        set_current_font_size(self.font_size)
        _apply_theme(self.settings.get("theme", "dark"))
        self.root.configure(bg=C["BG_DARK"])

        # 前回終了時のウィンドウジオメトリを復元
        saved_geom = self.settings.get("window_geometry", "")
        if saved_geom:
            try:
                self.root.geometry(saved_geom)
            except Exception as e:
                logger.debug("ジオメトリ復元失敗: %s", e)
                self.root.geometry("1200x780")
        else:
            self.root.geometry("1200x780")

        # 閲覧/編集モード（デフォルト: 閲覧モード）
        self.edit_mode = self.settings.get("edit_mode", False)
        self._mode_btn = None

        # セッション中のみ保持する API キー辞書（プロバイダ別 dict）
        # settings へは入れない・os.environ にも書かない・プロセス終了で消滅（D-01）
        self._session_api_keys = {}

        self.doc = None
        self.filepath = None
        # 開いている PDF が元々パスワード保護されていたか（解除メニューの活性判定）
        self.pdf_has_password = False
        self._opened_needed_password = False
        self.current_page = 0
        self.selected_pages = set()

        # ページネーション窓状態の単一の真実（D-05）
        # _page_window_start: 窓オフセット（全ページ index 起点・既定 0）
        # _page_size: 表示件数（settings からクランプ復元・W1）
        self._page_window_start = 0
        self._page_size = clamp_page_size(self.settings.get("thumb_page_size", 20))

        self.thumb_images = []
        self.thumb_cache = {}
        self._dnd_src_idx = None
        self._dnd_ghost = None
        self._dnd_indicator = None
        self.crop_rect = None
        self.crop_drag_start = None
        self.crop_mode = False
        self.redact_mode = False

        # Undo / Redo
        self._undo_stack = deque(maxlen=self.MAX_UNDO)
        self._redo_stack = deque(maxlen=self.MAX_UNDO)
        self._pending_click = None

        # バックグラウンドレンダリング世代カウンター
        self._preview_gen = 0  # プレビュー世代カウンター
        self._thumb_gen = 0  # サムネイル世代カウンター

        # プラグインマネージャー
        self.plugin_manager = PluginManager()
        disabled_plugins = self.settings.get("disabled_plugins", [])
        self.plugin_manager.load_all(app=self, disabled_ids=disabled_plugins)

        self._build_styles()
        self._build_ui()
        self._build_menubar()

        # WM_DELETE_WINDOW
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # キーボードショートカットの動的読み込み（既定 8 種・後続 04-02 の
        # ShortcutsDialog 保存時にも self._bind_shortcuts() を再利用する・D-05）
        self._default_shortcuts = {
            "open_file": "<Control-o>",
            "save_file": "<Control-s>",
            "undo": "<Control-z>",
            "redo": "<Control-y>",
            "save_as": "<Control-S>",
            "delete": "<Delete>",
            "toggle_mode": "<F5>",
            "print_pdf": "<Control-p>",
        }

        self._cmd_map = {
            "open_file": self._open_file,
            "save_file": self._save_file,
            "undo": self._undo,
            "redo": self._redo,
            "save_as": self._save_as,
            "delete": self._delete_selected,
            "toggle_mode": self._toggle_edit_mode,
            "print_pdf": self._print_pdf,
            "rotate_right": lambda: self._rotate_selected(90),
            "rotate_left": lambda: self._rotate_selected(270),
            "rotate_180": lambda: self._rotate_selected(180),
        }

        self._bind_shortcuts()

    def _bind_shortcuts(self):
        """settings["shortcuts"] から現在のキーバインドを（再）構築する（D-05）。

        再呼び出し時は前回バインドした keysym（shift variant 含む）を
        先に unbind してから新設定で再バインドする（旧キーが残らない・Pitfall 1）。
        """
        for old_keysym in getattr(self, "_bound_keysyms", []):
            try:
                self.root.unbind(old_keysym)
            except Exception as e:
                logger.debug("ショートカット unbind 失敗: %s", e)

        custom_shortcuts = self.settings.get("shortcuts", {})
        shortcuts = merge_shortcuts(self._default_shortcuts, custom_shortcuts)

        bound = []
        for cmd_name, keysym in shortcuts.items():
            func = self._cmd_map.get(cmd_name)
            if func and keysym:
                try:
                    self.root.bind(keysym, lambda e, f=func: f())
                    bound.append(keysym)
                    # 大文字小文字の対応 (Shift なし Control などのため)
                    variant = shift_variant_keysym(keysym)
                    if variant is not None:
                        self.root.bind(variant, lambda e, f=func: f())
                        bound.append(variant)
                except Exception as ex:
                    logger.warning(
                        f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}"
                    )
        self._bound_keysyms = bound

    # ══════════════════════════════════════════
    #  メニューバー（v1.8.0 Phase 4・04-03・D-01 本プロジェクト初導入）
    # ══════════════════════════════════════════
    def _build_menubar(self):
        """メニューバー（tk.Menu）を構築する（D-01）。

        最小構成: 「ツール」メニュー1つに「バッチOCR」項目のみを持つ
        （Open Question 1・他機能のメニュー化は本フェーズのスコープ外）。
        アクセラレータキーは設定しない（クリック起動のみ・Pitfall 5・
        既存 ShortcutsDialog cmd_map 11コマンドとの衝突を構造的に回避）。
        `_rebuild_ui` からも呼ばれ、root.winfo_children() 破棄後のテーマ
        切替時にもメニューバーが再構築される。
        """
        menubar = tk.Menu(self.root)
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label=self._t("batch_menu_item"), command=self._open_batch_ocr
        )
        menubar.add_cascade(label=self._t("batch_menu_tools"), menu=tools_menu)
        self.root.config(menu=menubar)
        self._menubar = menubar

    def _open_batch_ocr(self):
        """メニュー「バッチOCR」からダイアログを起動する（D-04: doc/filepath 非参照）"""
        from pagefolio.dialogs import BatchOCRDialog

        BatchOCRDialog(self.root, app=self, lang=self.lang, font_func=self._font)

    # ══════════════════════════════════════════
    #  ユーティリティ
    # ══════════════════════════════════════════
    def _update_doc_buttons_state(self):
        """ファイル開閉状態に応じてボタンの活性/非活性を切り替え"""
        state = ["!disabled"] if self.doc else ["disabled"]
        for b in self._doc_buttons:
            try:
                b.state(state)
            except Exception as e:
                logger.debug("ボタン状態変更失敗: %s", e)
        # OCR ボタン状態も連動して更新する（off では doc があっても disabled）
        self._update_ocr_buttons_state()

    def _update_ocr_buttons_state(self):
        """OCR プロバイダ設定と doc 状態に応じて OCR ボタンの活性/非活性を切り替え。

        ocr_provider が "off" のとき、またはドキュメントが開かれていないとき
        disabled 化する。外部送信・課金をゼロにする安全策（成功基準6・D-09）。
        """
        is_ocr_on = self.settings.get("ocr_provider", "off") != "off"
        state = ["!disabled"] if (is_ocr_on and self.doc) else ["disabled"]
        for b in getattr(self, "_ocr_buttons", []):
            try:
                b.state(state)
            except Exception as e:
                logger.debug("OCR ボタン状態変更失敗: %s", e)

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
        pdf_paths = [
            p
            for p in raw_paths
            if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
        ]

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

    def _on_thumb_dnd_motion(self, event):
        """外部からのファイルドラッグ時のインジケーター表示"""
        if not self.doc:
            return event.action
        self._dnd_show_indicator(event)
        return event.action

    def _on_thumb_dnd_drop(self, event):
        """サムネイルへのファイルドロップ（特定位置への挿入）"""
        self._dnd_clear_indicator()
        if not self.doc:
            return self._on_dnd_drop(event)

        dest = self._dnd_dest_index(event)
        if dest is None:
            return event.action

        raw_paths = self.preview_canvas.tk.splitlist(event.data)
        pdf_paths = [
            p
            for p in raw_paths
            if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
        ]

        if not pdf_paths:
            if raw_paths:
                messagebox.showwarning(
                    self._t("confirm_title"), self._t("dnd_pdf_only")
                )
            return event.action

        # 複数ファイルの場合は挿入順序ダイアログを出さずにそのまま処理するか、
        # または MergeOrderDialog を出す。既存実装に合わせ _do_insert を直接呼ぶ
        if len(pdf_paths) > 1:
            from pagefolio.dialogs import MergeOrderDialog

            MergeOrderDialog(
                self.root,
                list(pdf_paths),
                lambda ordered: self._do_insert(ordered, dest),
                lang=self.lang,
            )
        else:
            self._do_insert(pdf_paths, dest)

        return event.action

    def _quit(self):
        self._save_window_state()
        if self.doc:
            if messagebox.askyesno(self._t("confirm_title"), self._t("quit_confirm")):
                self._clear_undo_stacks()  # Blob 解放 + 一時ディレクトリ purge
                self.doc.close()
                self.root.destroy()
        else:
            self._clear_undo_stacks()
            self.root.destroy()

    def _set_status(self, msg):
        self.status_var.set(msg)

    # ══════════════════════════════════════════
    #  閲覧/編集モード切替
    # ══════════════════════════════════════════
    def _toggle_edit_mode(self):
        """閲覧モード ↔ 編集モードを切り替える"""
        self.edit_mode = not self.edit_mode
        self._update_edit_buttons_state()
        self._update_mode_btn()

    def _update_edit_buttons_state(self):
        """編集モード/閲覧モードに応じて編集専用ボタンの活性/非活性を切り替え"""
        state = ["!disabled"] if self.edit_mode else ["disabled"]
        for b in self._edit_only_buttons:
            try:
                b.state(state)
            except Exception as e:
                logger.debug("編集ボタン状態変更失敗: %s", e)
        # 編集モード時はドキュメント状態も再チェック
        if self.edit_mode:
            self._update_doc_buttons_state()

    def _save_sash_positions(self):
        """現在のサッシ位置を設定に保存"""
        try:
            self.settings["sash_left"] = self._paned.sash_coord(0)[0]
            if len(self._paned.panes()) > 2:
                self.settings["sash_right"] = self._paned.sash_coord(1)[0]
        except Exception as e:
            logger.debug("サッシ位置保存失敗: %s", e)

    def _restore_edit_sashes(self):
        """編集モード用サッシ位置を復元"""
        try:
            self._paned.update_idletasks()
            total = self._paned.winfo_width()
            if total <= 100:
                return
            left = self.settings.get("sash_left", int(total * 0.15))
            right = self.settings.get("sash_right", int(total * 0.77))
            left = max(100, min(left, total - 450))
            right = max(left + 200, min(right, total - 220))
            self._paned.sash_place(0, left, 0)
            self._paned.sash_place(1, right, 0)
        except Exception as e:
            logger.debug("サッシ位置復元失敗: %s", e)

    def _update_mode_btn(self):
        """モード切替ボタンのテキスト・スタイルを更新"""
        if self._mode_btn is None:
            return
        try:
            if self.edit_mode:
                self._mode_btn.configure(
                    text=self._t("mode_edit_label"), style="Accent.TButton"
                )
            else:
                self._mode_btn.configure(
                    text=self._t("mode_view_label"), style="TButton"
                )
        except Exception as e:
            logger.debug("モードボタン更新失敗: %s", e)

    def _save_window_state(self):
        """ウィンドウのジオメトリ・サッシ位置・モードを設定に保存"""
        try:
            geom = self.root.geometry()
            if geom and "x" in geom:
                self.settings["window_geometry"] = geom
        except Exception as e:
            logger.debug("ジオメトリ保存失敗: %s", e)
        self._save_sash_positions()
        self.settings["edit_mode"] = self.edit_mode
        _save_settings(self.settings)

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
            except Exception as e:
                logger.exception("プラグイン UI 構築失敗: %s", e)

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
        """設定ダイアログを開く（二重起動ガード付き）。

        既に開いている場合は新規生成せず既存ウィンドウを前面へ出す。
        二重起動すると current_settings のコピーが2つ独立に存在し、
        片方の変更がもう片方の「適用」/「キャンセル」で消失し得るため
        （「LLM設定を適用しても更新されない」に見えるバグの一因）。
        """
        existing = getattr(self, "_settings_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return
        # M-8: plugin_manager を渡して LLMConfigDialog でプラグインプロバイダを表示
        # V171-UIUX-01・D-01: app=self を渡し ShortcutsDialog から _cmd_map 等を参照
        self._settings_dialog = SettingsDialog(
            self.root,
            self.settings,
            self._apply_settings,
            self._font,
            plugin_manager=getattr(self, "plugin_manager", None),
            session_api_keys=getattr(self, "_session_api_keys", None),
            app=self,
            on_llm_apply=self._apply_llm_settings_live,
        )

    def _apply_llm_settings_live(self, llm_settings):
        """LLMConfigDialog のネスト適用を app.settings（メモリ）へ即時反映する（D-14）。

        SettingsDialog 経由のネスト適用（on_llm_apply）から呼ばれる軽量反映
        メソッド。テーマ/フォントは llm_settings に含まれないため
        `_rebuild_ui()` は呼ばない（ここで呼ぶと、開いている SettingsDialog
        Toplevel まで `root.winfo_children()` の destroy 対象になってしまう）。
        外側 SettingsDialog のキャンセルとは独立して確定させることで、
        ディスク（`_save_settings` 済み）とメモリの不整合（C4）を解消する。
        """
        self.settings.update(llm_settings)
        _save_settings(self.settings)

    def _apply_settings(self, new_settings):
        """設定変更を適用してUIを再構築"""
        self.settings = new_settings
        self.font_size = new_settings.get("font_size", 10)
        self.lang = new_settings.get("lang", self.lang)
        set_current_font_size(self.font_size)
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
        self._preview_gen += 1
        self._thumb_gen += 1
        self.thumb_cache.clear()
        self.crop_rect = None
        self.crop_drag_start = None
        self.crop_mode = False
        self.redact_mode = False
        self.crop_overlay_ids = []
        self.crop_rect_id = None
        self._plugin_ui_frame = None
        self._mode_btn = None
        self._build_styles()
        self._build_ui()
        self._build_menubar()
        if self.doc:
            self._refresh_all()
        else:
            self._show_preview()
            self._update_doc_buttons_state()
        _setup_file_drop(self)
