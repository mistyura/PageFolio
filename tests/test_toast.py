# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""``ToastManager`` の単体テスト（V180-QA-02）。

`tests/test_batch_ocr_dialog.py` のモジュール共有 `tk.Tk()`（`withdraw()` した
隠しルート）パターンをそのまま流用する。個々のトースト Frame は各テストが
`ToastManager` 経由で生成・破棄する。
"""

import pytest

tk = pytest.importorskip("tkinter")
from tkinter import ttk  # noqa: E402

import pagefolio.toast as toast_mod  # noqa: E402


@pytest.fixture(scope="module")
def tk_root():
    """モジュール全体で1つの `tk.Tk()` を共有する。

    `test_batch_ocr_dialog.py` と同方針。
    """
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


class _FakeApp:
    """`ToastManager` 単体テスト用の最小スタブ（`root`/`_font`/`_t` のみ提供）。"""

    def __init__(self, root):
        self.root = root

    def _font(self, delta=0, weight=None):
        size = max(7, 10 + delta)
        if weight:
            return ("Segoe UI", size, weight)
        return ("Segoe UI", size)

    def _t(self, key):
        return {"toast_retry_btn": "再試行"}.get(key, key)


def _find_button(frame, text):
    for w in frame.winfo_children():
        if isinstance(w, ttk.Button) and w.cget("text") == text:
            return w
    return None


class TestToastManagerShowDismiss:
    """show/dismiss/再試行/置換/更新の各挙動（D-04/D-07/D-08）。"""

    def test_show_sets_active_category(self, tk_root):
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        tm.show("save_file", "失敗しました", retry_cb=lambda: None)
        try:
            assert tm._active_category == "save_file"
            assert tm._frame is not None
            assert tm._frame.winfo_exists()
        finally:
            tm._destroy_frame()

    def test_second_show_replaces_single_toast(self, tk_root):
        """異なるカテゴリの2回目 show は既存 Frame を破棄して置換する（D-07）。"""
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        tm.show("save_file", "保存失敗", retry_cb=lambda: None)
        first_frame = tm._frame
        tm.show("print", "印刷失敗", retry_cb=lambda: None)
        try:
            assert tm._active_category == "print"
            assert tm._frame is not first_frame
            assert not first_frame.winfo_exists()
        finally:
            tm._destroy_frame()

    def test_dismiss_matching_removes_and_mismatch_is_noop(self, tk_root):
        """dismiss(一致カテゴリ)で消え、dismiss(不一致)は no-op（D-08）。"""
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        tm.show("save_file", "保存失敗", retry_cb=lambda: None)
        frame = tm._frame

        tm.dismiss("print")  # 不一致 → no-op
        assert tm._active_category == "save_file"
        assert tm._frame is frame
        assert frame.winfo_exists()

        tm.dismiss("save_file")  # 一致 → 破棄
        assert tm._active_category is None
        assert tm._frame is None
        assert not frame.winfo_exists()

    def test_retry_button_invokes_retry_cb(self, tk_root):
        """再試行ボタン押下で retry_cb() が呼ばれる（D-03）。"""
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        calls = []
        tm.show("save_file", "保存失敗", retry_cb=lambda: calls.append(True))
        try:
            btn = _find_button(tm._frame, "再試行")
            assert btn is not None
            btn.invoke()
            assert calls == [True]
        finally:
            tm._destroy_frame()

    def test_close_button_dismisses_toast(self, tk_root):
        """✕ボタン押下で dismiss される。"""
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        tm.show("save_file", "保存失敗", retry_cb=lambda: None)
        btn = _find_button(tm._frame, "✕")
        assert btn is not None
        btn.invoke()
        assert tm._active_category is None
        assert tm._frame is None

    def test_same_category_reshow_updates_message_and_stays(self, tk_root):
        """同一カテゴリ再showで文言更新され残る（D-04・回数制限なし）。"""
        app = _FakeApp(tk_root)
        tm = toast_mod.ToastManager(app)
        tm.show("save_file", "1回目の失敗", retry_cb=lambda: None)
        first_frame = tm._frame

        tm.show("save_file", "2回目の失敗", retry_cb=lambda: None)
        try:
            assert tm._frame is first_frame  # Frame は再生成されない
            assert tm._msg_var.get() == "2回目の失敗"
        finally:
            tm._destroy_frame()


def test_toast_retry_btn_lang_keys_present():
    from pagefolio.lang import LANG

    assert "toast_retry_btn" in LANG["ja"]
    assert "toast_retry_btn" in LANG["en"]
