"""既存notice試験を一度だけ実行し、外付けの読み取り診断を保存する。"""

import ctypes as ct
import hashlib
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from ctypes import wintypes as wt
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).resolve()
TEST_FILE = ROOT / "tests/test_startup_windows.py"
TARGET = "test_notice_dedup_eight_processes_keep_original_deadline"
WRAPPED = {
    "SetForegroundWindow",
    "AllowSetForegroundWindow",
    "ShowWindow",
    "SetWindowPos",
    "DestroyWindow",
}
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LastInputInfo(ct.Structure):
    _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]


class Probe:
    """native callback内ではTkを呼ばず、APIの結果/last_errorを保つ。"""

    def __init__(self, bind):
        self.records = []
        self.errors = []
        user = ct.WinDLL("user32", use_last_error=True)
        kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.foreground = bind(user, "GetForegroundWindow", wt.HWND)
        self.tick = bind(kernel, "GetTickCount64", ct.c_ulonglong)
        self.last_input = bind(
            user, "GetLastInputInfo", wt.BOOL, ct.POINTER(LastInputInfo)
        )
        self.window_process = bind(
            user, "GetWindowThreadProcessId", wt.DWORD, wt.HWND, ct.POINTER(wt.DWORD)
        )
        self.open_process = bind(
            kernel, "OpenProcess", wt.HANDLE, wt.DWORD, wt.BOOL, wt.DWORD
        )
        self.close_handle = bind(kernel, "CloseHandle", wt.BOOL, wt.HANDLE)
        self.process_times = bind(
            kernel,
            "GetProcessTimes",
            wt.BOOL,
            wt.HANDLE,
            *(ct.POINTER(wt.FILETIME) for _ in range(4)),
        )
        self.image_name = bind(
            kernel,
            "QueryFullProcessImageNameW",
            wt.BOOL,
            wt.HANDLE,
            wt.DWORD,
            wt.LPWSTR,
            ct.POINTER(wt.DWORD),
        )

    def identity(self, hwnd):
        pid = wt.DWORD()
        thread = self.window_process(hwnd, ct.byref(pid)) if hwnd else 0
        value = {"hwnd": hwnd, "pid": pid.value, "thread_id": thread}
        handle = self.open_process(0x1000, False, pid.value) if pid.value else None
        if not handle:
            value["process_identity_error"] = ct.get_last_error()
            return value
        try:
            times = [wt.FILETIME() for _ in range(4)]
            if self.process_times(handle, *(ct.byref(t) for t in times)):
                value["process_created"] = (times[0].dwHighDateTime << 32) | times[
                    0
                ].dwLowDateTime
            else:
                value["process_created_error"] = ct.get_last_error()
            size = wt.DWORD(32768)
            name = ct.create_unicode_buffer(size.value)
            if self.image_name(handle, 0, name, ct.byref(size)):
                value["image"] = name.value
            else:
                value["image_error"] = ct.get_last_error()
        finally:
            self.close_handle(handle)
        return value

    def record(self, event, **details):
        error = ct.get_last_error()
        try:
            started = time.monotonic_ns()
            tick = self.tick()
            input_info = LastInputInfo(ct.sizeof(LastInputInfo), 0)
            input_ok = bool(self.last_input(ct.byref(input_info)))
            row = {
                "event": event,
                "utc": datetime.now(UTC).isoformat(),
                "tick": tick,
                "monotonic_ns": started,
                "observer_pid": os.getpid(),
                "foreground": self.identity(self.foreground()),
                "last_input_available": input_ok,
                "last_input_tick32": input_info.dwTime if input_ok else None,
                **details,
            }
            row["capture_duration_ns"] = time.monotonic_ns() - started
            self.records.append(row)
        except Exception as exc:
            self.errors.append(repr(exc))
        finally:
            ct.set_last_error(error)

    def wrap(self, name, function):
        def call(*args):
            error = ct.get_last_error()
            stack = [
                {"file": frame.filename, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_stack(limit=10)[:-1]
            ]
            context = {}
            frame = inspect.currentframe()
            try:
                frame = frame.f_back
                while frame:
                    if frame.f_code.co_filename.endswith("startup_win32.py"):
                        if frame.f_code.co_name == "procedure":
                            context["window_message"] = frame.f_locals.get("message")
                            context["close_click"] = frame.f_locals.get("close_click")
                        elif frame.f_code.co_name == "show":
                            context["remaining_ms"] = frame.f_locals.get("remaining")
                    frame = frame.f_back
            finally:
                del frame
            self.record(
                "api_enter",
                api=name,
                target=args[0] if args else None,
                arguments=list(args),
                stack=stack,
                close_context=context,
            )
            ct.set_last_error(error)
            result = function(*args)
            error = ct.get_last_error()
            try:
                self.record("api_return", api=name, result=result, last_error=error)
            finally:
                ct.set_last_error(error)
            return result

        return call


def child(fixture, namespace, role):
    from pagefolio import startup_win32 as win

    spec = importlib.util.spec_from_file_location("notice_probe_test", TEST_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_bind = win._bind
    probe = Probe(original_bind)

    def diagnostic_bind(dll, name, result, *args):
        function = original_bind(dll, name, result, *args)
        return probe.wrap(name, function) if name in WRAPPED else function

    original_mark = module._ForegroundAudit.mark

    def mark(observer, event, *, hwnd=None, **details):
        original_mark(observer, event, hwnd=hwnd, **details)
        probe.record(event, event_hwnd=hwnd, details=details)

    win._bind = diagnostic_bind
    module._ForegroundAudit.mark = mark
    probe.record("child_started", role=role)
    try:
        module._test_scenario_bootstrap(fixture, namespace, role)
    finally:
        probe.record("child_finished", role=role)
        save(
            fixture / "notice-probe.json",
            {
                "role": role,
                "records": probe.records,
                "errors": probe.errors,
                "limits": "入力時刻だけを観測。入力内容/種別/要求元は取得しない。",
            },
        )
        win._bind = original_bind
        module._ForegroundAudit.mark = original_mark
    if probe.errors:
        raise RuntimeError("追加診断の採取失敗")


class Plugin:
    def pytest_collection_modifyitems(self, items):
        if len(items) != 1 or items[0].name != TARGET:
            raise RuntimeError("指定した一試験以外の実行は禁止")
        module = items[0].module
        original = module._pipe_popen

        def spawn(command):
            if command[2] != "_test_scenario_bootstrap":
                raise RuntimeError("未知の子起動を拒否")
            return original([command[0], str(SCRIPT), "--child", *command[3:]])

        module._pipe_popen = spawn


def run_pytest(base):
    import pytest

    if base.exists():
        raise RuntimeError("既存basetempを再利用しない")
    return pytest.main(
        [
            str(TEST_FILE) + "::" + TARGET,
            "-q",
            "-x",
            "--tb=short",
            "--basetemp=" + str(base),
            "-o",
            "cache_dir=" + str(base) + "-cache",
        ],
        plugins=[Plugin()],
    )


def run_once():
    run_id = "notice-probe-20261028-" + uuid4().hex
    evidence = SCRIPT.parent / run_id
    base = Path(tempfile.gettempdir()) / ("pf_" + run_id)
    if base.exists():
        raise RuntimeError("既存basetempを再利用しない")
    evidence.mkdir()
    baseline = ROOT / (
        ".planning/phases/06-release-validation/06-04g3-quality-fixed/inputs-before.json"
    )
    files = list(json.loads(baseline.read_text(encoding="utf-8")))
    files.append(str(SCRIPT.relative_to(ROOT)))

    def snapshot():
        return {name: digest(ROOT / name) for name in files}

    before = snapshot()
    save(evidence / "inputs-before.json", before)
    command = [sys.executable, str(SCRIPT), "--pytest", str(base)]
    report = {
        "purpose": "一回限りの追加診断。品質合格・停止解除には用いない",
        "started": datetime.now(UTC).isoformat(),
        "command": command,
        "basetemp": str(base),
        "runs": 1,
    }
    save(evidence / "run.json", report)
    with (evidence / "pytest.txt").open("xb") as output:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    after = snapshot()
    save(evidence / "inputs-after.json", after)
    report.update(
        finished=datetime.now(UTC).isoformat(),
        exit_code=result.returncode,
        changed_inputs=[name for name in files if before[name] != after[name]],
        log_sha256=digest(evidence / "pytest.txt"),
    )
    if base.exists():
        copied = evidence / "artifacts"
        shutil.copytree(base, copied)
        manifest = {
            str(path.relative_to(base)): digest(path)
            for path in base.rglob("*")
            if path.is_file()
        }
        report["copied_unchanged"] = all(
            digest(copied / name) == value for name, value in manifest.items()
        )
        save(evidence / "artifacts-manifest.json", manifest)
        report["artifacts"] = len(manifest)
    save(evidence / "run.json", report)
    print(json.dumps({"evidence": str(evidence), **report}, ensure_ascii=False))
    return result.returncode or bool(report["changed_inputs"])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise SystemExit(run_once())
    if sys.argv[1] == "--child":
        child(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "--pytest":
        raise SystemExit(run_pytest(Path(sys.argv[2])))
    else:
        raise SystemExit("未知の実行モード")
