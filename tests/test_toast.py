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

import pagefolio.file_ops as fo  # noqa: E402
import pagefolio.print_ops as po  # noqa: E402
import pagefolio.toast as toast_mod  # noqa: E402
import pagefolio.ui_builder as ui_builder_mod  # noqa: E402


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


class TestToastRegeneratedAfterRebuild:
    """`_rebuild_ui()` 相当（root 直下ウィジェット全破棄→再生成）の後も

    self._toast が有効であることを検証する（Pitfall 2）。`_build_ui()` 全体は
    重量級のため呼ばず、ToastManager 再生成のみを最小 FakeApp で模す
    （CONTEXT.md Claude's Discretion・plan 記載の「または最小の FakeApp」）。
    """

    def test_toast_manager_regenerated_after_root_children_destroyed(self, tk_root):
        app = _FakeApp(tk_root)
        app._toast = toast_mod.ToastManager(app)
        first = app._toast
        first.show("save_file", "失敗", retry_cb=lambda: None)

        # _rebuild_ui() 相当: root 直下ウィジェットを全破棄してから
        # _build_ui() を再実行する
        for w in tk_root.winfo_children():
            w.destroy()
        app._toast = toast_mod.ToastManager(app)  # _build_ui() 内の再生成に相当

        assert app._toast is not first
        assert isinstance(app._toast, toast_mod.ToastManager)
        # 新しい ToastManager が有効に show/dismiss できる
        app._toast.show("print", "印刷失敗", retry_cb=lambda: None)
        assert app._toast._active_category == "print"
        app._toast.dismiss("print")


class _FakeHelperApp(ui_builder_mod.UIBuilderMixin):
    """`_show_error_or_toast` 共通ヘルパー（R2）のみを検証する最小スタブ。"""

    def __init__(self, toast=None):
        self._toast = toast


class TestShowErrorOrToast:
    """`_show_error_or_toast` の toast あり/フォールバック両分岐（レビュー R2）。"""

    def test_uses_toast_show_when_toast_available(self):
        calls = []

        class _FakeToast:
            def show(self, category, message, retry_cb):
                calls.append((category, message, retry_cb))

        app = _FakeHelperApp(toast=_FakeToast())
        retry_cb = lambda: None  # noqa: E731
        app._show_error_or_toast("save_file", "title", "msg", retry_cb)

        assert calls == [("save_file", "msg", retry_cb)]

    def test_falls_back_to_messagebox_when_toast_missing(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            ui_builder_mod.messagebox,
            "showerror",
            lambda title, msg: calls.append((title, msg)),
        )
        app = _FakeHelperApp(toast=None)
        app._show_error_or_toast("save_file", "title", "msg", lambda: None)

        assert calls == [("title", "msg")]


# ══════════════════════════════════════════
#  Task 3: 保存/印刷失敗パスの統合テスト
# ══════════════════════════════════════════


class _RecordingToast:
    """show/dismiss 呼び出しを記録するスタブ `ToastManager`。"""

    def __init__(self):
        self.shown = []
        self.dismissed = []

    def show(self, category, message, retry_cb):
        self.shown.append((category, message, retry_cb))

    def dismiss(self, category):
        self.dismissed.append(category)


class _FakePluginManager:
    def fire_event(self, *a, **kw):
        pass


class _RaisingThenOkDoc:
    """1回目の save() は例外・2回目以降は成功する偽 doc。"""

    def __init__(self):
        self.calls = 0

    def save(self, *a, **kw):
        self.calls += 1
        if self.calls == 1:
            raise Exception("保存失敗（一時要因）")


class _FakeFileOpsApp(fo.FileOpsMixin, ui_builder_mod.UIBuilderMixin):
    """`_save_*` 系メソッドの失敗/成功パスをトースト経由で検証する FakeApp。"""

    def __init__(self, doc, toast, filepath=None, overwrite_error=None):
        self.doc = doc
        self.filepath = filepath
        self._toast = toast
        self.plugin_manager = _FakePluginManager()
        self._overwrite_error = overwrite_error

    def _t(self, key):
        return {
            "save_confirm_title": "確認",
            "save_confirm_msg": "{name}",
            "err_save_title": "err_save_title",
            "err_save_msg": "保存に失敗しました:\n{e}",
            "err_title": "err_title",
            "status_saved": "saved {name}",
            "status_compressed": "compressed {name}",
        }.get(key, key)

    def _set_status(self, *a):
        pass

    def _overwrite_current_file(self, path, **kw):
        if self._overwrite_error is not None:
            raise self._overwrite_error
        self.doc = fo.fitz.open(path)

    def _is_current_file(self, path):
        return False


class TestSaveFilePathsUseSharedHelper:
    """file_ops.py の保存3メソッドが _show_error_or_toast/dismiss を呼ぶ。

    D-02/D-08 の検証。
    """

    def test_save_file_failure_shows_toast_with_retry(self, monkeypatch):
        """上書き保存の失敗が _show_error_or_toast 経由でトースト表示される。"""
        monkeypatch.setattr(fo.messagebox, "askyesno", lambda *a, **k: True)
        toast = _RecordingToast()
        app = _FakeFileOpsApp(
            doc=_RaisingThenOkDoc(),
            toast=toast,
            filepath="test.pdf",
            overwrite_error=OSError("overwrite失敗"),
        )

        app._save_file()

        assert len(toast.shown) == 1
        category, msg, retry_cb = toast.shown[0]
        assert category == "save_file"
        assert "保存に失敗しました" in msg
        assert retry_cb == app._save_file

    def test_save_as_failure_then_success_dismisses(self, monkeypatch, tmp_path):
        out_path = str(tmp_path / "out.pdf")
        monkeypatch.setattr(fo.filedialog, "asksaveasfilename", lambda **k: out_path)
        toast = _RecordingToast()
        doc = _RaisingThenOkDoc()
        app = _FakeFileOpsApp(doc=doc, toast=toast)

        app._save_as()  # 1回目: 失敗
        assert toast.shown[-1][0] == "save_as"
        assert toast.shown[-1][2] == app._save_as

        app._save_as()  # 2回目: 成功 → dismiss
        assert toast.dismissed[-1] == "save_as"

    def test_save_compressed_failure_shows_toast(self, monkeypatch, tmp_path):
        out_path = str(tmp_path / "out.pdf")
        monkeypatch.setattr(fo.filedialog, "asksaveasfilename", lambda **k: out_path)
        toast = _RecordingToast()
        app = _FakeFileOpsApp(doc=_RaisingThenOkDoc(), toast=toast)

        app._save_compressed()

        assert toast.shown[-1][0] == "save_compressed"
        assert toast.shown[-1][2] == app._save_compressed


class _FakePrintApp(po.PrintOpsMixin, ui_builder_mod.UIBuilderMixin):
    def __init__(self, toast, doc=None):
        self._toast = toast
        self.doc = doc if doc is not None else object()

    def _check_doc(self):
        return True

    def _t(self, key):
        return {
            "err_print_title": "err_print_title",
            "err_print_msg": "印刷に失敗しました:\n{e}",
            "err_print_no_handler": "既定ハンドラが見つかりません",
            "status_print_sent": "sent {name}",
            "status_print_opened": "opened {name}",
        }.get(key, key)

    def _set_status(self, *a):
        pass


class TestPrintPathsDistinguishFailureMessages:
    """印刷の一時ファイル失敗と OS 印刷失敗が異なる文言で区別できる（レビュー R1）。"""

    def test_tempfile_failure_and_os_failure_have_distinct_messages(self, monkeypatch):
        toast = _RecordingToast()
        app = _FakePrintApp(toast=toast)

        # 一時ファイル生成失敗（write_print_tempfile 例外）
        def _raise_tempfile(doc):
            raise Exception("disk full")

        monkeypatch.setattr(po, "write_print_tempfile", _raise_tempfile)
        app._print_pdf()

        assert toast.shown[-1][0] == "print"
        msg_tempfile = toast.shown[-1][1]
        assert "disk full" in msg_tempfile
        assert toast.shown[-1][2] == app._print_pdf

        # OS 印刷コマンド失敗（既定ハンドラ不在）
        monkeypatch.setattr(po, "write_print_tempfile", lambda doc: "x.pdf")
        monkeypatch.setattr(
            po.os,
            "startfile",
            lambda *a, **k: (_ for _ in ()).throw(OSError("no handler")),
            raising=False,
        )
        app._print_pdf()

        msg_os_failure = toast.shown[-1][1]
        assert toast.shown[-1][0] == "print"
        assert msg_os_failure != msg_tempfile
        assert "既定ハンドラ" in msg_os_failure

    def test_send_to_printer_success_dismisses_toast(self, monkeypatch, tmp_path):
        toast = _RecordingToast()
        app = _FakePrintApp(toast=toast)
        monkeypatch.setattr(po.os, "startfile", lambda *a, **k: None, raising=False)

        app._send_to_printer(str(tmp_path / "x.pdf"))

        assert toast.dismissed[-1] == "print"
