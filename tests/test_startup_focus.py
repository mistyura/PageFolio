"""既存画面復帰の状態・入力先・有限点滅の回帰試験。"""

import ctypes as ct
import hashlib
import importlib.util
import threading
from collections import deque
from types import SimpleNamespace

import pytest


class Widget:
    def __init__(self, master=None, state="normal"):
        self.master = master
        self.children = []
        if master:
            master.children.append(self)
        self.alive = True
        self.placement = state
        self.bounds = "800x600+30+40"
        self.bindings = {}
        self.focused = None
        self.last = None
        self.grab = None
        self.calls = []
        self.timers = {}

    def winfo_exists(self):
        return self.alive

    def winfo_children(self):
        return self.children

    def winfo_toplevel(self):
        return self

    def state(self, value=None):
        if value:
            self.calls.append(("state", value))
            self.placement = value
        return self.placement

    def geometry(self, value=None):
        if value:
            self.calls.append(("geometry", value))
            self.bounds = value
        return self.bounds

    def bind(self, event, callback, add=None):
        assert add == "+"
        key = str(len(self.bindings))
        self.bindings[key] = (event, callback)
        return key

    def unbind(self, event, key):
        del self.bindings[key]

    def focus_get(self):
        return self.focused

    def focus_lastfor(self):
        return self.last

    def focus_set(self):
        self.calls.append(("focus",))

    def grab_current(self):
        return self.grab

    def after(self, delay, callback):
        key = str(len(self.timers))
        self.timers[key] = (delay, callback)
        return key

    def after_cancel(self, key):
        self.timers.pop(key, None)


class Backend:
    def __init__(self):
        self.calls = []
        self.allowed = True
        self.popup = None
        self.generation = "one"
        self.focus_restorer = None
        self.restore_effect = None

    def _assert_thread(self):
        assert threading.current_thread() is threading.main_thread()

    def _top_level_hwnd(self, widget):
        return id(widget) if widget.alive else None

    def _window_process_id(self, hwnd):
        return (10, 20) if hwnd else None

    def _activation_target_valid(self, hwnd):
        return bool(hwnd)

    def _owned_popup(self, handles):
        return self.popup

    def _z_order(self, handles):
        return list(reversed(handles))

    def _restore_placement(self, hwnd, is_current):
        if not is_current():
            return False
        self.calls.append(("restore", hwnd))
        if self.restore_effect:
            self.restore_effect()
        return True

    def _foreground_window(self, hwnd, is_current):
        if not is_current():
            return "expired"
        self.calls.append(("foreground", hwnd))
        return "completed" if self.allowed else "foreground_denied"

    def _flash_window(self, hwnd):
        self.calls.append(("flash", hwnd, 3, 250))

    def _stop_flash(self, hwnd):
        self.calls.append(("stop", hwnd))


def controller():
    assert importlib.util.find_spec("pagefolio.startup_focus") is not None, (
        "既存状態を維持する FocusRestorer が必要"
    )
    from pagefolio.startup_focus import FocusRestorer

    root = Widget()
    app = SimpleNamespace(root=root, status="OCR progress")
    backend = Backend()
    return FocusRestorer(app, backend), root, backend


@pytest.mark.parametrize("prior", ["normal", "zoomed"])
def test_placement_returns_to_last_non_iconic_state(prior):
    focus, root, backend = controller()
    root.placement = prior
    focus._remember_window_state(SimpleNamespace(widget=root))
    root.placement = "iconic"
    focus._remember_window_state(SimpleNamespace(widget=root))
    assert focus.restore() == "completed"
    assert root.placement == prior
    assert root.bounds == "800x600+30+40"
    assert backend.calls[0][0] == "restore"
    assert focus.app.status == "OCR progress"


def test_placement_os_restored_correctly_does_not_rewrite_geometry():
    focus, root, backend = controller()
    root.placement = "iconic"
    backend.restore_effect = lambda: setattr(root, "placement", "normal")
    assert focus.restore() == "completed"
    assert not any(call[0] == "geometry" for call in root.calls)


def test_placement_corrects_mismatched_normal_geometry_after_os_restore():
    focus, root, backend = controller()
    root.placement = "iconic"

    def restore_different_geometry():
        root.placement = "normal"
        root.bounds = "100x100+0+0"

    backend.restore_effect = restore_different_geometry
    assert focus.restore() == "completed"
    assert root.bounds == "800x600+30+40"


@pytest.mark.parametrize("name", ["thumb_canvas", "preview_canvas", "entry"])
def test_focus_child_preserved_and_toplevel_focus_does_not_overwrite(name):
    focus, root, backend = controller()
    child = Widget(root)
    child.winfo_toplevel = lambda: root
    child.name = name
    focus._remember_focus(SimpleNamespace(widget=child))
    focus._remember_focus(SimpleNamespace(widget=root))
    assert focus.restore() == "completed"
    assert child.calls == [("focus",)]
    assert len([c for c in backend.calls if c[0] == "foreground"]) == 1


def test_modal_without_grab_returns_to_live_parent_after_nested_close():
    focus, root, backend = controller()
    settings = Widget(root)
    llm = Widget(settings)
    entry = Widget(settings)
    entry.winfo_toplevel = lambda: settings
    settings.last = entry
    focus.observe()
    focus._remember_focus(SimpleNamespace(widget=entry))
    focus._remember_focus(SimpleNamespace(widget=llm))
    llm.alive = False
    assert focus.restore() == "completed"
    assert ("foreground", id(settings)) in backend.calls
    assert entry.calls == [("focus",)]
    assert root.grab is None


def test_modal_grab_and_native_popup_preserve_input_focus():
    focus, root, backend = controller()
    dialog = Widget(root)
    root.grab = dialog
    focus.observe()
    assert focus.restore() == "completed"
    assert ("foreground", id(dialog)) in backend.calls
    backend.popup = 123456
    backend.calls.clear()
    dialog.calls.clear()
    assert focus.restore() == "completed"
    assert ("foreground", 123456) in backend.calls
    assert not root.calls and not dialog.calls
    assert root.grab is dialog


def test_rebuild_discards_dead_widget_and_falls_back_to_root():
    focus, root, _ = controller()
    old = Widget(root)
    old.winfo_toplevel = lambda: root
    focus._remember_focus(SimpleNamespace(widget=old))
    old.alive = False
    assert focus.restore() == "completed"
    assert not old.calls
    assert root.calls == [("focus",)]
    assert focus.last_focus_widget is None


@pytest.mark.parametrize("delegation", [False, True])
def test_foreground_denied_only_flashes_and_stop_never_retries(delegation):
    focus, root, backend = controller()
    backend.allowed = False  # 委譲成功後もユーザー入力で許可は失効し得る。
    backend.delegation = delegation
    assert focus.restore() == "foreground_denied"
    assert not root.calls
    assert backend.calls == [
        ("foreground", id(root)),
        ("flash", id(root), 3, 250),
    ]
    stops = [(ms, cb) for ms, cb in root.timers.values() if ms > 50]
    assert len(stops) == 1 and stops[0][0] <= 2000
    stops[0][1]()
    assert backend.calls[-1] == ("stop", id(root))
    assert sum(c[0] == "foreground" for c in backend.calls) == 1


def test_expired_generation_and_destroyed_stop_are_inert():
    focus, root, backend = controller()
    assert focus.restore(is_current=lambda: False) == "expired"
    assert not backend.calls
    backend.allowed = False
    focus.restore()
    stop = [cb for ms, cb in root.timers.values() if ms > 50][0]
    backend.generation = "two"
    stop()
    assert not any(c[0] == "stop" for c in backend.calls)
    root.alive = False
    assert focus.restore() == "expired"


def test_each_side_effect_rechecks_deadline_and_nested_restore_is_inert():
    focus, root, backend = controller()
    root.placement = "iconic"
    live = [True]

    def expire():
        assert focus.restore() == "expired"
        live[0] = False

    backend.restore_effect = expire
    assert focus.restore(is_current=lambda: live[0]) == "expired"
    assert backend.calls == [("restore", id(root))]


def test_close_removes_only_own_binding_ids():
    focus, root, _ = controller()
    unrelated = root.bind("<FocusIn>", lambda event: None, add="+")
    focus.close()
    assert list(root.bindings) == [unrelated]
    assert not root.timers


def test_tk_menu_is_not_a_window_activation_target():
    focus, root, _ = controller()
    menu = Widget(root)
    menu.state = None
    focus.observe()
    assert menu not in focus.windows
    assert focus.restore() == "completed"


def test_working_state_real_pdf_history_and_blobs_continue(sample_pdf_doc, monkeypatch):
    from pagefolio.constants import LANG
    from pagefolio.file_ops import FileOpsMixin
    from pagefolio.page_ops import PageOpsMixin
    from pagefolio.startup_focus import FocusRestorer

    class App(FileOpsMixin, PageOpsMixin):
        MAX_UNDO = 20

        def _check_doc(self):
            return True

        def _get_targets(self):
            return sorted(self.selected_pages)

        def _refresh_all(self):
            pass

        def _invalidate_thumb_cache(self, *args):
            pass

        def _t(self, key):
            return LANG["ja"][key]

        def _set_status(self, value):
            self.status = value

    app = App()
    app.root = Widget()
    app.doc = sample_pdf_doc
    app.lang = "ja"
    app.current_page = 0
    app.selected_pages = {0}
    app._undo_stack = deque(maxlen=20)
    app._redo_stack = deque(maxlen=20)
    app._preview_gen = app._thumb_gen = 0
    app.plugin_manager = SimpleNamespace(fire_event=lambda *args: None)
    monkeypatch.setattr("pagefolio.page_ops.messagebox.askyesno", lambda *args: True)
    focus = FocusRestorer(app, Backend())

    def snapshot():
        return (
            id(app),
            id(app.doc),
            tuple(hashlib.sha256(p.get_pixmap().samples).hexdigest() for p in app.doc),
            tuple(id(s) for s in app._undo_stack),
            tuple(id(s) for s in app._redo_stack),
            app.current_page,
            set(app.selected_pages),
            app.status,
        )

    try:
        app._rotate_selected(90)
        app.selected_pages = {1}
        app._delete_selected()
        blob = app._undo_stack[-1]["data"][0][1]
        blob_bytes = app._blob_bytes(blob)
        before = snapshot()
        assert focus.restore() == "completed"
        assert snapshot() == before
        assert app._undo_stack[-1]["data"][0][1] is blob
        assert app._blob_bytes(blob) == blob_bytes
        for operation in (app._undo, app._redo, app._undo, app._redo):
            operation()
            before = snapshot()
            assert focus.restore() == "completed"
            assert snapshot() == before
        assert len(app.doc) == 2 and app.doc[0].rotation == 90
    finally:
        focus.close()
        app._clear_undo_stacks()


def test_ocr_same_engine_worker_and_generation_complete_after_restore():
    from pagefolio.ocr_engine import OCRRunEngine
    from pagefolio.ocr_pipeline import send_sentinels, try_enqueue
    from pagefolio.ocr_providers import OCRProvider

    entered, release, complete = [threading.Event() for _ in range(3)]

    class Provider(OCRProvider):
        def ocr_image(self, b64_png, prompt, **kwargs):
            assert isinstance(b64_png, str)
            entered.set()
            assert release.wait(3)
            return "completed OCR"

        def list_models(self):
            return ["isolated-fake"]

    focus, _, _ = controller()
    engine = OCRRunEngine(
        Provider(), "local prompt", [0], 1, threading.Event(), on_complete=complete.set
    )
    dialog = SimpleNamespace(_run_gen=7, _engine=engine)
    focus.app.ocr_dialog = dialog
    workers = engine.start()
    try:
        assert try_enqueue(engine.queue, (0, "base64-image"))
        assert send_sentinels(engine.queue, 1) == 1
        assert entered.wait(2)
        assert focus.restore() == "completed"
        assert focus.app.ocr_dialog is dialog
        assert dialog._run_gen == 7 and dialog._engine is engine
        assert engine._worker_threads[0] is workers[0] and workers[0].is_alive()
        release.set()
        assert complete.wait(3)
        assert engine.results == {0: "completed OCR"}
        assert engine.progress_count() == 1
    finally:
        release.set()
        for worker in workers:
            worker.join(3)
            assert not worker.is_alive()
        focus.close()


@pytest.mark.parametrize("kind", ["foreign", "unknown", "cycle", "unowned"])
def test_modal_native_unverified_owner_never_selected(kind):
    from pagefolio.startup_win32 import Win32Backend

    backend = Win32Backend.__new__(Win32Backend)
    owner = {2: 3, 3: 2} if kind == "cycle" else {2: 99 if kind == "unknown" else 0}
    backend.api = SimpleNamespace(
        GetGUIThreadInfo=lambda *a: False,
        GetLastActivePopup=lambda *a: 2,
        IsWindowVisible=lambda hwnd: True,
        IsWindowEnabled=lambda hwnd: hwnd == 2,
        GetWindow=lambda hwnd, flag: owner.get(hwnd, 0),
    )
    backend._thread_windows = lambda: [2]
    backend._window_process_id = lambda hwnd: (
        (10, 20)
        if hwnd in {1, 2, 3} and not (kind == "foreign" and hwnd == 2)
        else None
    )
    assert backend._owned_popup([1]) is None


def test_modal_disabled_parent_is_not_activated_without_verified_popup():
    focus, root, backend = controller()
    backend._activation_target_valid = lambda hwnd: False
    root.placement = "iconic"
    assert focus.restore() == "expired"
    assert not backend.calls


@pytest.mark.parametrize("mismatch", ["none", "pid", "thread", "dead"])
def test_normalized_hwnd_is_same_process_and_ui_thread(mismatch):
    from pagefolio.startup_win32 import Win32Backend

    backend = Win32Backend.__new__(Win32Backend)
    backend.pid = 10
    backend._assert_thread = lambda: None
    backend.logger = SimpleNamespace(debug=lambda *a: None)

    def identity(hwnd, pointer):
        assert hwnd == 99  # Tk内部HWND=5を副作用APIへ渡さない。
        ct.cast(pointer, ct.POINTER(ct.c_ulong)).contents.value = (
            20 if mismatch == "pid" else 10
        )
        return threading.get_native_id() + (1 if mismatch == "thread" else 0)

    backend.api = SimpleNamespace(
        GetAncestor=lambda hwnd, flag: 99,
        IsWindow=lambda hwnd: mismatch != "dead",
        GetWindowThreadProcessId=identity,
    )
    widget = SimpleNamespace(winfo_id=lambda: 5)
    assert backend._top_level_hwnd(widget) == (99 if mismatch == "none" else None)
