"""既存作業を変更せず、Tk の入力先とウィンドウ状態だけを復帰する。"""

import logging
import threading
import tkinter as tk

logger = logging.getLogger(__name__)


def _alive(widget):
    try:
        return widget is not None and bool(widget.winfo_exists())
    except Exception as e:
        logger.debug("復帰対象の生存確認: %s", e)
        return False


class FocusRestorer:
    def __init__(self, app, backend):
        self.app = app
        self.root = app.root
        self.backend = backend
        self.thread = threading.get_ident()
        self.closed = False
        self.restoring = False
        self.last_non_iconic_state = "normal"
        self.normal_geometry = None
        self.last_focus_widget = None
        self.last_toplevel = self.root
        self.windows = {}
        self.bindings = []
        self.stop_ids = set()
        self.poll_id = None
        self._remember_window_state()
        self.observe()
        self.poll_id = self.root.after(50, self._poll)

    def _assert_thread(self):
        if threading.get_ident() != self.thread:
            raise RuntimeError("復帰処理は Tk メインスレッド限定")

    def _remember_window_state(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if not _alive(self.root) or self.restoring:
            return
        state = self.root.state()
        if state in {"normal", "zoomed"}:
            self.last_non_iconic_state = state
            if state == "normal":
                self.normal_geometry = self.root.geometry()

    def _register(self, window):
        if window in self.windows:
            return
        parent = getattr(window, "master", None)
        while parent is not None and parent not in self.windows:
            parent = getattr(parent, "master", None)
        self.windows[window] = {"focus": None, "parent": parent, "visible": False}
        for event, callback in [("<FocusIn>", self._remember_focus)]:
            key = window.bind(event, callback, add="+")
            self.bindings.append((window, event, key))
        if window is self.root:
            for event in ("<Configure>", "<Map>"):
                key = window.bind(event, self._remember_window_state, add="+")
                self.bindings.append((window, event, key))

    def observe(self):
        """poll と復帰直前に、transient に依存せず Tk の子孫を発見する。"""
        self._assert_thread()
        if self.closed or not _alive(self.root):
            return
        pending = [self.root]
        while pending:
            widget = pending.pop()
            if not _alive(widget):
                continue
            # Tk Menu も winfo_toplevel() が自身を返すが復帰対象ではない。
            if widget.winfo_toplevel() is widget and callable(
                getattr(widget, "state", None)
            ):
                self._register(widget)
            pending.extend(reversed(widget.winfo_children()))
        minimized = self.root.state() == "iconic"
        for window, record in self.windows.items():
            if not _alive(window):
                record["focus"] = None
                continue
            if not minimized:
                record["visible"] = window.state() not in {"withdrawn", "iconic"}
            if not _alive(record["focus"]):
                record["focus"] = None
        current = self.root.focus_get()
        if _alive(current):
            self._remember_focus(type("FocusEvent", (), {"widget": current})())

    def _poll(self):
        self.poll_id = None
        if self.closed or not _alive(self.root):
            return
        self.observe()
        self.poll_id = self.root.after(50, self._poll)

    def _remember_focus(self, event):
        widget = event.widget
        if not _alive(widget):
            return
        window = widget.winfo_toplevel()
        if window not in self.windows:
            self._register(window)
        self.last_toplevel = window
        record = self.windows[window]
        if widget is not window or not _alive(record["focus"]):
            record["focus"] = widget
            self.last_focus_widget = widget

    def _select_activation_target(self):
        grab = self.root.grab_current()
        if _alive(grab):
            return grab.winfo_toplevel()
        target = self.last_toplevel
        visited = set()
        while target is not None and target not in visited:
            visited.add(target)
            record = self.windows.get(target)
            if record and _alive(target) and record["visible"]:
                return target
            target = record["parent"] if record else None
        # 同じ UI thread の Z-order を補助とする。別processはbackendが除外。
        handles = {
            self.backend._top_level_hwnd(window): window
            for window, record in self.windows.items()
            if _alive(window) and record["visible"]
        }
        for hwnd in self.backend._z_order(handles):
            if hwnd in handles:
                return handles[hwnd]
        return self.root

    def _focus_widget(self, target):
        for widget in (
            self.root.focus_get(),
            self.windows[target]["focus"],
            target.focus_lastfor(),
        ):
            if _alive(widget) and widget.winfo_toplevel() is target:
                return widget
        return target

    def restore(self, hwnd=None, is_current=lambda: True):
        self._assert_thread()
        if self.closed or self.restoring or not _alive(self.root) or not is_current():
            return "expired"
        self.observe()
        target = self._select_activation_target()
        root_hwnd = self.backend._top_level_hwnd(self.root)
        target_hwnd = self.backend._top_level_hwnd(target)
        handles = [
            self.backend._top_level_hwnd(window)
            for window in self.windows
            if _alive(window)
        ]
        popup = self.backend._owned_popup([handle for handle in handles if handle])
        selected = popup or target_hwnd
        identity = self.backend._window_process_id(selected)
        generation = self.backend.generation

        def current():
            return (
                not self.closed
                and _alive(self.root)
                and _alive(target)
                and generation == self.backend.generation
                and is_current()
                and self.backend._top_level_hwnd(self.root) == root_hwnd
                and self.backend._top_level_hwnd(target) == target_hwnd
                and identity is not None
                and self.backend._window_process_id(selected) == identity
                and self.backend._owned_popup([h for h in handles if h]) == popup
            )

        if not root_hwnd or not selected or not current():
            return "expired"
        self.restoring = True
        try:
            if self.root.state() == "iconic":
                if not self.backend._restore_placement(root_hwnd, current):
                    return "expired"
                # SW_RESTORE が保存placementを復元した場合は再設定しない。
                if self.root.state() != self.last_non_iconic_state:
                    if not current():
                        return "expired"
                    self.root.state(self.last_non_iconic_state)
                    if self.last_non_iconic_state == "normal" and self.normal_geometry:
                        if not current():
                            return "expired"
                        if self.root.geometry() != self.normal_geometry:
                            self.root.geometry(self.normal_geometry)
            result = self.backend._foreground_window(selected, current)
            if result == "completed" and not popup and current():
                widget = self._focus_widget(target)
                if current() and _alive(widget):
                    widget.focus_set()
            elif result == "foreground_denied" and current():
                self.backend._flash_window(root_hwnd)
                self._schedule_stop(root_hwnd, generation)
            return result
        finally:
            self.restoring = False

    def _schedule_stop(self, hwnd, generation):
        def stop():
            self.stop_ids.discard(key)
            if (
                not self.closed
                and _alive(self.root)
                and generation == self.backend.generation
                and self.backend._top_level_hwnd(self.root) == hwnd
            ):
                self.backend._stop_flash(hwnd)

        key = self.root.after(1000, stop)
        self.stop_ids.add(key)

    def close(self):
        self._assert_thread()
        self.closed = True
        for window, event, key in self.bindings:
            if _alive(window):
                try:
                    window.unbind(event, key)
                except tk.TclError as e:
                    logger.debug("復帰binding解除: %s", e)
        for key in self.stop_ids | ({self.poll_id} if self.poll_id else set()):
            if _alive(self.root):
                self.root.after_cancel(key)
        self.bindings.clear()
        self.stop_ids.clear()
