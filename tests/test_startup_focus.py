"""既存画面復帰の状態・入力先・有限点滅の回帰試験。"""

import importlib.util
import threading
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
