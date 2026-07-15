# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ShortcutsDialog の WR-01/WR-02 回帰テスト（V180-ROBUST-03）。

WR-01: キャプチャ対象を切り替えると前行の「キーを押してください」表示が
残留するバグ（`_start_capture` 修正）。実 Tk root を使い、
`tests/test_batch_ocr_dialog.py` と同じ module-scope フィクスチャで検証する。

WR-02: 修飾なし単キーショートカットが入力系ウィジェットの通常入力と衝突する
バグ（`should_suppress_for_focused_input` フォーカスガード）。Tk 非依存の
純関数のみで検証する（`tests/test_viewer.py` の純ロジックテストパターン）。

ShortcutsDialog 専用のテストファイルはこれまで存在しなかった（初の単体テスト整備）。
"""

import os
import sys
import tkinter as tk

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio.app import should_suppress_for_focused_input  # noqa: E402
from pagefolio.dialogs.shortcuts import ShortcutsDialog  # noqa: E402


# ══════════════════════════════════════════
#  WR-02: フォーカスガード純関数（Tk root 不要）
# ══════════════════════════════════════════
class TestShouldSuppressForFocusedInput:
    """should_suppress_for_focused_input の判定ロジック検証（D-09/D-10）"""

    def test_control_combo_never_suppressed(self):
        """Ctrl 組合せは入力系ウィジェットフォーカス中も抑止しない"""
        assert should_suppress_for_focused_input("<Control-o>", "Entry") is False

    def test_alt_combo_never_suppressed(self):
        """Alt 組合せも入力系ウィジェットフォーカス中も抑止しない"""
        assert should_suppress_for_focused_input("<Alt-x>", "Spinbox") is False

    def test_unmodified_key_suppressed_on_entry(self):
        """修飾なし単キーは Entry フォーカス中は抑止する"""
        assert should_suppress_for_focused_input("<Delete>", "Entry") is True

    def test_unmodified_key_suppressed_on_spinbox(self):
        """修飾なし単キーは Spinbox フォーカス中も抑止する（既定キー <Delete> 対応）"""
        assert should_suppress_for_focused_input("<Delete>", "Spinbox") is True

    def test_unmodified_key_suppressed_on_ttk_spinbox(self):
        """ttk.Spinbox（TSpinbox）フォーカス中も抑止する"""
        assert should_suppress_for_focused_input("<Delete>", "TSpinbox") is True

    def test_unmodified_key_suppressed_on_text(self):
        """Text ウィジェットフォーカス中も抑止する（既定キー <F5> 対応）"""
        assert should_suppress_for_focused_input("<F5>", "Text") is True

    def test_unmodified_key_not_suppressed_on_button(self):
        """非入力系ウィジェット（TButton）フォーカス中は抑止しない"""
        assert should_suppress_for_focused_input("<Delete>", "TButton") is False

    def test_unmodified_key_not_suppressed_when_no_focus(self):
        """フォーカスなし（空文字列フォールバック）のときは抑止しない"""
        assert should_suppress_for_focused_input("<Delete>", "") is False

    def test_shift_only_combo_suppressed_on_entry(self):
        """Shift のみの組合せは Entry フォーカス中は抑止する（大文字入力と同義）"""
        assert should_suppress_for_focused_input("<Shift-A>", "Entry") is True

    def test_shift_only_combo_not_suppressed_on_button(self):
        """Shift のみの組合せも非入力系ウィジェットフォーカス中は抑止しない"""
        assert should_suppress_for_focused_input("<Shift-A>", "TButton") is False


# ══════════════════════════════════════════
#  WR-01: キャプチャ切替時の旧行表示復元（実 Tk root 使用）
# ══════════════════════════════════════════
@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


class _FakeApp:
    """ShortcutsDialog インスタンス化に必要な最小限の app スタブ。

    `tests/test_undo_stress.py` の FakeApp パターンに倣い、必要属性のみ持たせる。
    """

    def __init__(self):
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
        self.settings = {"shortcuts": {}}

    def _bind_shortcuts(self):
        pass


@pytest.fixture()
def shortcuts_dialog(tk_root):
    app = _FakeApp()
    dlg = ShortcutsDialog(
        tk_root,
        app,
        font_func=lambda delta=0, weight=None: ("Segoe UI", 10),
        lang="ja",
    )
    yield dlg
    dlg.destroy()


class TestStartCaptureRestoresPreviousRow:
    """_start_capture のキャプチャ対象切替時の旧行表示復元を検証（WR-01）"""

    def test_switching_capture_restores_previous_row_label(self, shortcuts_dialog):
        dlg = shortcuts_dialog
        waiting_text = dlg._L["shortcuts_capture_waiting"]

        # コマンドA（open_file）のキャプチャを開始 → 行Aが waiting 表示になる
        dlg._start_capture("open_file")
        label_a = dlg._key_labels["open_file"]
        assert label_a.cget("text") == waiting_text

        # 保存/クリアせずコマンドB（save_file）のキャプチャを開始
        dlg._start_capture("save_file")
        label_b = dlg._key_labels["save_file"]

        # 行A（旧行）は shortcuts_capture_waiting のまま残留せず、
        # 通常の keysym 表示（_display_text 経由）へ復元されていること
        assert label_a.cget("text") != waiting_text
        assert label_a.cget("text") == dlg._display_text("open_file")

        # 行B（新行）は shortcuts_capture_waiting 表示になっていること
        assert label_b.cget("text") == waiting_text

        # キャプチャ状態自体も新コマンドへ切り替わっていること
        assert dlg._capturing_cmd == "save_file"

    def test_single_capture_start_shows_waiting_only_on_target_row(
        self, shortcuts_dialog
    ):
        """初回キャプチャ開始時は対象行のみ waiting 表示になる（回帰なし確認）"""
        dlg = shortcuts_dialog
        waiting_text = dlg._L["shortcuts_capture_waiting"]

        dlg._start_capture("undo")
        assert dlg._key_labels["undo"].cget("text") == waiting_text
        # 他の行は waiting 表示になっていない
        assert dlg._key_labels["redo"].cget("text") != waiting_text
