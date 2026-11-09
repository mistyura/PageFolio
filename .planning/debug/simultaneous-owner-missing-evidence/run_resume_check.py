"""非表示launcherで、安定した前景を確認後に承認済みの有限検証を実行する。"""

import ctypes as ct
import hashlib
import json
import shutil
import subprocess
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from pagefolio.startup_win32 import Win32Backend, _bind  # noqa: E402

TARGETS = [
    "test_simultaneous_exit_audit_native_wm_close",
    "test_foreground_audit_receives_native_window_event",
    "test_notice_dedup_eight_processes_keep_original_deadline",
    "test_simultaneous_real_processes_construct_one_editor",
    "test_simultaneous_exit_audit_distinguishes_entry",
]
ARTIFACTS = {
    "result.json",
    "ready",
    "traceback.log",
    "exit-audit.jsonl",
    "foreground-audit.jsonl",
    "fresh-completed.json",
    "resource-audit.json",
    "native-trigger.json",
}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def preflight(destination):
    """テスト開始前だけ待つ。前景を変更せず、console遷移中は実行しない。"""
    backend = Win32Backend("resume-preflight")
    foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
    get_pid = _bind(
        backend.api.u,
        "GetWindowThreadProcessId",
        wt.DWORD,
        wt.HWND,
        ct.POINTER(wt.DWORD),
    )
    get_class = _bind(
        backend.api.u, "GetClassNameW", ct.c_int, wt.HWND, wt.LPWSTR, ct.c_int
    )
    observations = []
    previous = None
    stable_since = time.monotonic()
    deadline = stable_since + 30
    try:
        while time.monotonic() < deadline:
            hwnd = foreground()
            pid = wt.DWORD()
            name = ct.create_unicode_buffer(256)
            thread_id = get_pid(hwnd, ct.byref(pid)) if hwnd else 0
            length = get_class(hwnd, name, len(name)) if hwnd else 0
            identity = (hwnd, pid.value, name.value)
            now = time.monotonic()
            if identity != previous:
                previous = identity
                stable_since = now
                observations.append(
                    {
                        "monotonic": now,
                        "hwnd": hwnd,
                        "pid": pid.value,
                        "class": name.value,
                    }
                )
            ready = (
                thread_id
                and length
                and name.value
                not in {"CASCADIA_HOSTING_WINDOW_CLASS", "ConsoleWindowClass"}
                and now - stable_since >= 2
            )
            if ready:
                save_json(destination, {"ready": True, "observations": observations})
                return
            time.sleep(0.1)
        save_json(destination, {"ready": False, "observations": observations})
        raise RuntimeError("前景が安定せず、試験開始前に停止")
    finally:
        backend.close()


def preserve(source, destination):
    destination.mkdir()
    manifest = []
    for item in source.rglob("*"):
        if not item.is_file() or item.name not in ARTIFACTS:
            continue
        relative = item.relative_to(source)
        copied = destination / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, copied)
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if hashlib.sha256(copied.read_bytes()).hexdigest() != digest:
            raise RuntimeError("証拠コピーのSHA256不一致")
        manifest.append({"file": str(relative), "source": str(item), "sha256": digest})
    save_json(destination / "manifest.json", manifest)
    return len(manifest)


def main():
    evidence = Path(sys.argv[1]).resolve()
    temporary = Path(sys.argv[2]).resolve()
    evidence.mkdir()
    status = {"state": "preflight", "runs": []}
    status_path = evidence / "status.json"
    save_json(status_path, status)
    try:
        preflight(evidence / "preflight.json")
        for label in ("target-1", "target-2", "target-3", "full"):
            base = temporary / ("pf_" + evidence.name + "_" + label)
            if base.exists():
                raise RuntimeError("既存basetempの再利用は禁止")
            command = [str(ROOT / ".venv/Scripts/python.exe"), "-m", "pytest"]
            if label != "full":
                command.extend(
                    "tests/test_startup_windows.py::" + name for name in TARGETS
                )
            command.extend(["-x", "-q", "--tb=short", "--basetemp=" + str(base)])
            status["state"] = "running " + label
            save_json(status_path, status)
            started = time.monotonic()
            with (evidence / (label + ".txt")).open("xb") as output:
                result = subprocess.run(  # noqa: S603
                    command,
                    cwd=ROOT,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            artifacts = preserve(base, evidence / label)
            status["runs"].append(
                {
                    "label": label,
                    "exit_code": result.returncode,
                    "seconds": time.monotonic() - started,
                    "artifacts": artifacts,
                    "command": command,
                }
            )
            save_json(status_path, status)
            if result.returncode:
                status["state"] = "failed " + label
                save_json(status_path, status)
                return result.returncode
        status["state"] = "passed"
        save_json(status_path, status)
        return 0
    except Exception as e:
        status["state"] = "error"
        status["error"] = repr(e)
        save_json(status_path, status)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
