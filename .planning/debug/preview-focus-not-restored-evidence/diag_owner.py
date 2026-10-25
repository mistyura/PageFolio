# ruff: noqa
"""診断用の owner / peer (debug: preview-focus-not-restored)。diag_preview_focus.py から起動される。

本番の起動経路 (pagefolio.py -> pagefolio.__main__.main -> StartupCoordinator/FocusRestorer) を、
固有 namespace と隔離設定 (fixture) のまま動かす。tests/ の被覆ファイル (Phase 4 の covered_files) は
一切変更せず、同等の準備 (入力先を preview/thumb の Canvas に置く) と観測 (focus-result.json /
focus-trace.json) をこのファイルだけで行う。

  --role owner : 隔離PageFolioを一次として起動し、入力先を準備して観測を書く
  --role peer  : 二次起動 (既存画面の復帰要求)。結果を JSON 1 行で出力する
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import runpy
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


class FocusTrace:
    """入力先・前景・利用者入力の時系列を focus-trace.json へ残す。観測だけで状態は変えない。"""

    LIMIT = 1500

    def __init__(self, app, path):
        import tkinter as tk

        from pagefolio.startup_win32 import _bind

        self.tk = tk
        self.root = app.root
        self.focus = app._startup_focus
        self.backend = self.focus.backend
        self.path = path
        self.started = time.monotonic()
        self.entries = []
        self.stopped = False
        self.last_key = None
        self.last_dump = 0.0
        user32 = self.backend.api.u
        self.get_foreground = _bind(user32, "GetForegroundWindow", wt.HWND)
        self.get_os_focus = _bind(user32, "GetFocus", wt.HWND)
        self.get_cursor = _bind(
            user32, "GetCursorPos", wt.BOOL, ctypes.POINTER(wt.POINT)
        )
        self._install_bindings()
        self._install_focus_wrapper()
        self.snap("trace-start")
        self.root.after(100, self._sample)

    def note(self, kind, **fields):
        if len(self.entries) < self.LIMIT:
            self.entries.append(
                {"t": round(time.monotonic() - self.started, 3), "kind": kind, **fields}
            )

    def _widget_of_hwnd(self, hwnd):
        if not hwnd:
            return None
        pending = [self.root]
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            try:
                if widget.winfo_id() == hwnd:
                    return str(widget)
            except self.tk.TclError as e:
                self.note("error", where="widget_of_hwnd", error=repr(e))
        return None

    def _safe(self, call):
        try:
            return str(call())
        except (self.tk.TclError, KeyError) as e:
            return f"error:{e!r}"

    def snap(self, tag):
        point = wt.POINT()
        self.get_cursor(ctypes.byref(point))
        os_focus = self.get_os_focus()
        record = self.focus.windows.get(self.root, {})
        self.note(
            tag,
            foreground=self.get_foreground(),
            own=self.backend._top_level_hwnd(self.root),
            tk_focus=self._safe(self.root.focus_get),
            lastfor=self._safe(self.root.focus_lastfor),
            record=str(record.get("focus")),
            last_widget=str(self.focus.last_focus_widget),
            os_focus=os_focus,
            os_focus_widget=self._widget_of_hwnd(os_focus),
            cursor=[point.x, point.y],
            under_cursor=self._safe(
                lambda: self.root.winfo_containing(point.x, point.y)
            ),
        )

    def _install_bindings(self):
        for name, fields in (
            ("FocusIn", "%W %m %d"),
            ("FocusOut", "%W %m %d"),
            ("ButtonPress", "%W %b %X %Y"),
            ("ButtonRelease", "%W %b %X %Y"),
            ("KeyPress", "%W %K"),
            ("KeyRelease", "%W %K"),
        ):
            command = self.root.register(
                lambda *args, name=name: self.note(name, args=list(args))
            )
            self.root.tk.call("bind", "all", f"<{name}>", f"+{command} {fields}")

    def _install_focus_wrapper(self):
        def called(*args):
            # -lastfor/-displayof は入力先を変えない問い合わせ。自分の観測も含めて除外。
            if str(args[0]).startswith("-"):
                return
            stack = [
                f"{Path(f.filename).name}:{f.lineno}:{f.name}"
                for f in traceback.extract_stack()[:-1]
                if "pagefolio" in f.filename.lower()
            ]
            self.note("tcl-focus", text=" ".join(map(str, args))[:300], py=stack[-4:])

        self.root.tk.createcommand("pf_trace_focus", called)
        self.root.tk.eval(
            """
rename focus ::pf_trace_orig_focus
proc focus {args} {
    set result [uplevel 1 [list ::pf_trace_orig_focus {*}$args]]
    if {[llength $args] > 0} {
        set caller ""
        catch {set caller [info level -1]}
        pf_trace_focus $args -> $result tcl-caller: [string range $caller 0 120]
    }
    return $result
}
"""
        )

    def _sample(self):
        if self.stopped:
            return
        try:
            point = wt.POINT()
            self.get_cursor(ctypes.byref(point))
            key = (
                self.get_foreground(),
                self._safe(self.root.focus_get),
                self._widget_of_hwnd(self.get_os_focus()),
                self._safe(lambda: self.root.winfo_containing(point.x, point.y)),
            )
            if key != self.last_key:
                self.last_key = key
                self.snap("change")
            if time.monotonic() - self.last_dump > 2:
                self.dump()
        finally:
            if not self.stopped:
                self.root.after(100, self._sample)

    def dump(self):
        self.last_dump = time.monotonic()
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False), encoding="utf-8"
        )

    def stop(self):
        self.stopped = True
        self.snap("trace-stop")
        self.dump()


def prepare(app, fixture, case):
    root = app.root
    focus = app._startup_focus
    backend = focus.backend
    trace = FocusTrace(app, fixture / "focus-trace.json")
    widget = app.thumb_canvas if case == "thumb" else app.preview_canvas
    widget.focus_set()
    original = backend.restore_window

    def traced_restore(hwnd, is_current=lambda: True):
        trace.snap("restore-before")
        result = original(hwnd, is_current=is_current)
        trace.note("restore-result", result=result)
        trace.snap("restore-after")
        record = {
            "result": result,
            "expected_focus": str(widget),
            "immediate_focus": str(root.focus_get()),
        }

        def settled():
            record["settled_focus"] = str(root.focus_get())
            record["focus_correct"] = (
                result != "completed" or root.focus_get() is widget
            )
            trace.snap("settled")
            trace.dump()
            (fixture / "focus-result.json").write_text(
                json.dumps(record), encoding="utf-8"
            )

        root.after_idle(settled)
        return result

    backend.restore_window = traced_restore

    def ready():
        focus.observe()
        (fixture / "ready").touch()

    root.after(250, ready)

    def finish():
        trace.stop()
        app._quit()

    def stop_poll():
        if (fixture / "stop").exists():
            finish()
        else:
            root.after(50, stop_poll)

    root.after(50, stop_poll)
    root.after(180000, finish)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["owner", "peer"], required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--case", choices=["preview", "thumb"], default="preview")
    args = parser.parse_args()
    fixture = args.fixture
    sys.path.insert(0, str(REPO))
    from pagefolio import plugins, settings

    settings._get_base_dir = lambda: str(fixture)
    plugins._get_plugins_dir = lambda: str(fixture / "plugins")
    from pagefolio import startup_win32

    base = startup_win32.Win32Backend
    seen = {}

    class Backend(base):
        def __init__(self):
            super().__init__(args.namespace)

        def request_activation(self, started_tick):
            result = super().request_activation(started_tick)
            seen["terminal_result"] = result
            seen["elapsed"] = self.tick_ms() - started_tick
            return result

    startup_win32.Win32Backend = Backend
    if args.role == "owner":
        from pagefolio import app as app_module

        class DiagApp(app_module.PDFEditorApp):
            def __init__(self, root):
                super().__init__(root)
                root.after(150, lambda: prepare(self, fixture, args.case))

        app_module.PDFEditorApp = DiagApp
    runpy.run_path(str(REPO / "pagefolio.py"), run_name="__main__")
    if args.role == "peer":
        print(json.dumps(seen))


if __name__ == "__main__":
    main()
