"""W05cの診断専用。既存受入を更新せず、native応答と回収順を観測する。"""

import ctypes as ct
import hashlib
import json
import subprocess
import sys
import time
import traceback
from ctypes import wintypes as wt
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests import test_startup_windows as harness  # noqa: E402


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def owner(fixture, namespace):
    import tkinter as tk
    from tkinter import messagebox

    from pagefolio.startup_win32 import _bind

    original_prepare = harness._prepare_focus_case

    def prepare(app, path, case, *, manual=False):
        root = app.root
        observed = set()
        callbacks = []
        backend = app._startup_focus.backend

        def emit(event, **details):
            record = {
                "event": event,
                "utc": datetime.now(UTC).isoformat(),
                "monotonic": time.monotonic(),
                "stop": (fixture / "stop").exists(),
                **details,
            }
            with (fixture / "probe.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

        def state():
            try:
                alive = bool(root.winfo_exists())
            except tk.TclError:
                alive = False
            return {
                "root_alive": alive,
                "pages": len(app.doc) if app.doc else 0,
                "rotations": [page.rotation for page in app.doc] if app.doc else [],
            }

        original_ask = messagebox.askyesno

        def ask(*args, **kwargs):
            emit("ask_enter", args=list(args), state=state())
            result = original_ask(*args, **kwargs)
            emit("ask_return", result=result, state=state())
            return result

        messagebox.askyesno = ask
        original_quit = app._quit

        def quit_observed():
            emit(
                "quit_enter",
                state=state(),
                callers=[
                    {
                        "file": Path(frame.filename).name,
                        "line": frame.lineno,
                        "function": frame.name,
                    }
                    for frame in traceback.extract_stack(limit=6)
                ],
            )
            result = original_quit()
            emit("quit_return", state=state())
            return result

        app._quit = quit_observed
        previous_error = root.report_callback_exception

        def report_error(kind, value, tb):
            emit(
                "tk_error",
                traceback="".join(traceback.format_exception(kind, value, tb)),
            )
            previous_error(kind, value, tb)

        root.report_callback_exception = report_error
        root.bind(
            "<Destroy>",
            lambda event: emit("root_destroy") if event.widget is root else None,
            add="+",
        )

        # native受信callbackではTk APIを呼ばず、元のWndProcへ必ず委譲する。
        comctl = ct.WinDLL("comctl32", use_last_error=True)
        callback_type = ct.WINFUNCTYPE(
            ct.c_ssize_t,
            wt.HWND,
            wt.UINT,
            wt.WPARAM,
            wt.LPARAM,
            ct.c_size_t,
            ct.c_size_t,
        )
        install = _bind(
            comctl,
            "SetWindowSubclass",
            wt.BOOL,
            wt.HWND,
            callback_type,
            ct.c_size_t,
            ct.c_size_t,
        )
        remove = _bind(
            comctl, "RemoveWindowSubclass", wt.BOOL, wt.HWND, callback_type, ct.c_size_t
        )
        forward = _bind(
            comctl,
            "DefSubclassProc",
            ct.c_ssize_t,
            wt.HWND,
            wt.UINT,
            wt.WPARAM,
            wt.LPARAM,
        )

        def observe(hwnd, message, wparam, lparam, subclass_id, data):
            try:
                if message in {0x111, 0x10, 0x2, 0x82}:
                    emit(
                        "native_message",
                        hwnd=hwnd,
                        message=message,
                        wparam=wparam,
                        lparam=lparam,
                    )
                if message == 0x82:
                    remove(hwnd, callback, subclass_id)
            except Exception as e:
                print(
                    f"native観測の記録失敗: {type(e).__name__}",
                    file=sys.stderr,
                    flush=True,
                )
            return forward(hwnd, message, wparam, lparam)

        callback = callback_type(observe)
        callbacks.append(callback)
        app._w05c_probe_callbacks = callbacks

        def monitor():
            hwnd = backend._owned_popup([backend._top_level_hwnd(root)])
            if hwnd and hwnd not in observed:
                observed.add(hwnd)
                if not install(hwnd, callback, 905, 0):
                    raise OSError(ct.get_last_error(), "native観測登録失敗")
                emit("native_observed", hwnd=hwnd)
            cancelled = (fixture / "quit-cancelled").exists()
            measured = {"native": hwnd, "cancelled": cancelled, **state()}
            if measured != getattr(monitor, "previous", None):
                emit("state", **measured)
                monitor.previous = measured
            root.after(100, monitor)

        root.after(100, monitor)
        original_prepare(app, path, case, manual=manual)
        original_cleanup = app._focus_cleanup

        def cleanup():
            emit("cleanup_enter", state=state())
            result = original_cleanup()
            emit("cleanup_return", state=state())
            return result

        app._focus_cleanup = cleanup
        emit("prepare_return", state=state())

    harness._prepare_focus_case = prepare
    harness._test_scenario_bootstrap(fixture, namespace, "uat-owner-native-quit")


def start():
    before = harness._fingerprints()
    run = ROOT / ".planning" / "tmp" / ("pagefolio-w05c-probe-" + uuid4().hex)
    fixture = run / "uat-owner-native-quit"
    fixture.mkdir(parents=True)
    (fixture / "plugins").mkdir()
    (fixture / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    for name in harness._ORIGINALS[1:]:
        (fixture / name).write_text("isolated test prompt", encoding="utf-8")
    namespace = uuid4().hex
    with (
        (fixture / "stdout.log").open("w", encoding="utf-8") as out,
        (fixture / "stderr.log").open("w", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "owner",
                str(fixture),
                namespace,
            ],
            cwd=ROOT,
            stdout=out,
            stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    harness._wait_file(child, fixture / "focus-ready")
    expected = json.loads((fixture / "ready").read_text(encoding="utf-8"))
    manifest = {
        "run": str(run),
        "namespace": namespace,
        "case": "native-quit",
        "role": "uat-owner-native-quit",
        "fixture": str(fixture),
        "launcher_pid": child.pid,
        "originals_before": before,
        "expected_owner": {**expected, "manual": True},
        "diagnostic_only": True,
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "harness_sha256": hashlib.sha256(
            Path(harness.__file__).read_bytes()
        ).hexdigest(),
        "python": sys.version,
    }
    save(run / "manifest.json", manifest)
    if harness._fingerprints() != before:
        raise RuntimeError("原本が変化したため診断を中断")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "start":
        start()
    elif sys.argv[1] == "owner":
        owner(Path(sys.argv[2]), sys.argv[3])
    else:
        harness._uat_harness(sys.argv[1:])
