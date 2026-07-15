# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ショートカット設定ダイアログ（実キーキャプチャによる GUI 編集・V171-UIUX-01）"""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pagefolio.constants import LANG, C

logger = logging.getLogger(__name__)

# 修飾キー単体の keysym（Pitfall 2: これらだけでは確定しない・入力待ち継続）
_MODIFIER_KEYSYMS = {
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Shift_L",
    "Shift_R",
    "Caps_Lock",
    "Num_Lock",
}

# cmd_map の 11 コマンドの表示順・LANG キー対応（D-03）
_CMD_ORDER = (
    ("open_file", "shortcut_cmd_open_file"),
    ("save_file", "shortcut_cmd_save_file"),
    ("undo", "shortcut_cmd_undo"),
    ("redo", "shortcut_cmd_redo"),
    ("save_as", "shortcut_cmd_save_as"),
    ("delete", "shortcut_cmd_delete"),
    ("toggle_mode", "shortcut_cmd_toggle_mode"),
    ("print_pdf", "shortcut_cmd_print_pdf"),
    ("rotate_right", "shortcut_cmd_rotate_right"),
    ("rotate_left", "shortcut_cmd_rotate_left"),
    ("rotate_180", "shortcut_cmd_rotate_180"),
)


# ══════════════════════════════════════════
#  ショートカット設定ダイアログ
# ══════════════════════════════════════════
class ShortcutsDialog(tk.Toplevel):
    """cmd_map の全11コマンドを実キーキャプチャで編集するダイアログ（D-01〜D-08）。

    保存前は一時状態（self._shortcuts）のみを編集し、app.settings / 実バインドへは
    「保存」ボタンを押すまで反映しない。
    """

    def __init__(self, parent, app, font_func=None, lang="ja"):
        super().__init__(parent)
        self._app = app
        self._L = LANG[lang]
        self._font = font_func
        self.title(self._L["shortcuts_title"])
        self.configure(bg=C["BG_DARK"])
        self.resizable(False, False)
        self.grab_set()

        # 保存前の一時編集状態（既定＋ユーザー設定のマージ結果からコピー）
        from pagefolio.app import merge_shortcuts

        self._shortcuts = dict(
            merge_shortcuts(app._default_shortcuts, app.settings.get("shortcuts", {}))
        )
        # 11 コマンド全てを対象にする（rotate 系は既定になければ空文字 = 未割当）
        for cmd_name, _label_key in _CMD_ORDER:
            self._shortcuts.setdefault(cmd_name, "")

        self._capturing_cmd = None
        self._key_labels = {}

        self._build()
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w = max(480, self.winfo_reqwidth() + 20)
        h = max(420, self.winfo_reqheight() + 20)
        self.geometry(f"{w}x{h}+{px - w // 2}+{py - h // 2}")

    # ── UI 構築 ──────────────────────────────────────────
    def _build(self):
        tk.Label(
            self,
            text=self._L["shortcuts_title"],
            bg=C["BG_DARK"],
            fg=C["ACCENT"],
            font=self._font(2, "bold"),
        ).pack(pady=(14, 10))

        rows_frame = tk.Frame(self, bg=C["BG_DARK"])
        rows_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # 列見出し
        tk.Label(
            rows_frame,
            text=self._L["shortcuts_col_command"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
        tk.Label(
            rows_frame,
            text=self._L["shortcuts_col_key"],
            bg=C["BG_DARK"],
            fg=C["TEXT_SUB"],
            font=self._font(-1, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 6))

        for i, (cmd_name, label_key) in enumerate(_CMD_ORDER, start=1):
            tk.Label(
                rows_frame,
                text=self._L[label_key],
                bg=C["BG_DARK"],
                fg=C["TEXT_MAIN"],
                font=self._font(0),
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=3)

            key_label = tk.Label(
                rows_frame,
                text=self._display_text(cmd_name),
                bg=C["BG_CARD"],
                fg=C["TEXT_MAIN"],
                font=self._font(0),
                width=14,
                anchor="w",
            )
            key_label.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=3)
            self._key_labels[cmd_name] = key_label

            ttk.Button(
                rows_frame,
                text=self._L["shortcuts_btn_change"],
                command=lambda c=cmd_name: self._start_capture(c),
            ).grid(row=i, column=2, padx=4, pady=3)

            ttk.Button(
                rows_frame,
                text=self._L["shortcuts_btn_clear"],
                command=lambda c=cmd_name: self._clear_cmd(c),
            ).grid(row=i, column=3, padx=4, pady=3)

        btn_row = tk.Frame(self, bg=C["BG_DARK"])
        btn_row.pack(pady=(4, 14))
        ttk.Button(
            btn_row,
            text=self._L["shortcuts_btn_save"],
            style="Accent.TButton",
            command=self._on_save,
        ).pack(side="left", padx=6)
        ttk.Button(
            btn_row,
            text=self._L["shortcuts_btn_reset_all"],
            command=self._on_reset_all,
        ).pack(side="left", padx=6)
        ttk.Button(
            btn_row,
            text=self._L["shortcuts_btn_cancel"],
            command=self.destroy,
        ).pack(side="left", padx=6)

    # ── 表示ヘルパー ──────────────────────────────────────────
    def _display_text(self, cmd_name):
        from pagefolio.app import keysym_to_display

        keysym = self._shortcuts.get(cmd_name, "")
        if not keysym:
            return self._L["shortcuts_unassigned"]
        return keysym_to_display(keysym)

    def _label_for_cmd(self, cmd_name):
        for name, label_key in _CMD_ORDER:
            if name == cmd_name:
                return self._L[label_key]
        return cmd_name

    def _refresh_row(self, cmd_name):
        label = self._key_labels.get(cmd_name)
        if label is not None:
            label.configure(text=self._display_text(cmd_name))

    def _refresh_all_rows(self):
        for cmd_name, _label_key in _CMD_ORDER:
            self._refresh_row(cmd_name)

    # ── キャプチャ（変更）──────────────────────────────────────────
    def _start_capture(self, cmd_name):
        if self._capturing_cmd is not None:
            prev_cmd = self._capturing_cmd
            self._end_capture()
            self._refresh_row(prev_cmd)  # WR-01: 旧行の表示を復元
        self._capturing_cmd = cmd_name
        label = self._key_labels.get(cmd_name)
        if label is not None:
            label.configure(text=self._L["shortcuts_capture_waiting"])
        self.bind("<KeyPress>", self._on_capture_keypress)
        self.focus_set()

    def _end_capture(self):
        self._capturing_cmd = None
        try:
            self.unbind("<KeyPress>")
        except Exception as e:
            logger.debug("キャプチャ bind 解除失敗: %s", e)

    def _on_capture_keypress(self, event):
        cmd_name = self._capturing_cmd
        if cmd_name is None:
            return

        if event.keysym == "Escape":
            self._end_capture()
            self._refresh_row(cmd_name)
            return

        if event.keysym in _MODIFIER_KEYSYMS:
            # Pitfall 2: 修飾キー単体では確定せず入力待ちを継続する
            return

        from pagefolio.app import build_keysym_from_event, find_duplicate_binding

        new_keysym = build_keysym_from_event(event.state, event.keysym)
        dup_cmd = find_duplicate_binding(self._shortcuts, cmd_name, new_keysym)
        if dup_cmd is not None:
            messagebox.showerror(
                self._L["err_title"],
                self._L["shortcuts_dup_error"].format(cmd=self._label_for_cmd(dup_cmd)),
            )
            self._end_capture()
            self._refresh_row(cmd_name)
            return

        self._shortcuts[cmd_name] = new_keysym
        self._end_capture()
        self._refresh_row(cmd_name)

    # ── 解除・全体リセット（D-06・D-08）──────────────────────────────────────────
    def _clear_cmd(self, cmd_name):
        if self._capturing_cmd == cmd_name:
            self._end_capture()
        self._shortcuts[cmd_name] = ""
        self._refresh_row(cmd_name)

    def _on_reset_all(self):
        if self._capturing_cmd is not None:
            self._end_capture()
        self._shortcuts = {
            cmd_name: self._app._default_shortcuts.get(cmd_name, "")
            for cmd_name, _label_key in _CMD_ORDER
        }
        self._refresh_all_rows()

    # ── 保存（D-04・D-05・D-06）──────────────────────────────────────────
    def _on_save(self):
        if self._capturing_cmd is not None:
            self._end_capture()
            self._refresh_all_rows()

        from pagefolio.app import find_duplicate_binding

        for cmd_name, keysym in self._shortcuts.items():
            dup_cmd = find_duplicate_binding(self._shortcuts, cmd_name, keysym)
            if dup_cmd is not None:
                messagebox.showerror(
                    self._L["err_title"],
                    self._L["shortcuts_dup_error"].format(
                        cmd=self._label_for_cmd(dup_cmd)
                    ),
                )
                return

        default_shortcuts = self._app._default_shortcuts
        diff = {
            cmd_name: keysym
            for cmd_name, keysym in self._shortcuts.items()
            if keysym != default_shortcuts.get(cmd_name, "")
        }
        self._app.settings["shortcuts"] = diff
        self._app._bind_shortcuts()

        from pagefolio.settings import _save_settings

        _save_settings(self._app.settings)
        self.destroy()
