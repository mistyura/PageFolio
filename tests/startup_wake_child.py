"""自己プロセスだけに幽霊メッセージを作る、UI 見張りの子プロセス試験。"""

import ctypes as ct
import faulthandler
import json
import logging
import sys
import threading
import time
from ctypes import wintypes as wt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pagefolio import startup_wake  # noqa: E402
from pagefolio.startup_wake import UiThreadWake  # noqa: E402
from pagefolio.startup_win32 import _bind  # noqa: E402


class WakeApiBoundary:
    """見張りへ渡すAPI以外への接触を、例外が握られても記録する。"""

    def __init__(self, allowed, requests, violations):
        self._allowed = allowed
        self._requests = requests
        self._violations = violations

    def __getattr__(self, name):
        self._requests.append(name)
        if name not in self._allowed:
            self._violations.append(name)
            raise RuntimeError(f"見張りに許可されていないAPI: {name}")
        return self._allowed[name]


def run(enabled, simulate_external_foreground=False):
    import tkinter as tk

    user = ct.WinDLL("user32", use_last_error=True)
    hook_proc = ct.WINFUNCTYPE(ct.c_ssize_t, ct.c_int, wt.WPARAM, wt.LPARAM)
    set_hook = _bind(
        user,
        "SetWindowsHookExW",
        wt.HANDLE,
        ct.c_int,
        hook_proc,
        wt.HINSTANCE,
        wt.DWORD,
    )
    unhook = _bind(user, "UnhookWindowsHookEx", wt.BOOL, wt.HANDLE)
    call_next = _bind(
        user, "CallNextHookEx", ct.c_ssize_t, wt.HANDLE, ct.c_int, wt.WPARAM, wt.LPARAM
    )
    peek = _bind(
        user,
        "PeekMessageW",
        wt.BOOL,
        ct.POINTER(wt.MSG),
        wt.HWND,
        wt.UINT,
        wt.UINT,
        wt.UINT,
    )
    post = _bind(
        user, "PostThreadMessageW", wt.BOOL, wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM
    )
    foreground = _bind(user, "GetForegroundWindow", wt.HWND)
    window_pid = _bind(
        user, "GetWindowThreadProcessId", wt.DWORD, wt.HWND, ct.POINTER(wt.DWORD)
    )
    window_title = _bind(user, "GetWindowTextW", ct.c_int, wt.HWND, wt.LPWSTR, ct.c_int)

    def foreground_snapshot():
        hwnd = foreground()
        pid = wt.DWORD()
        thread_id = window_pid(hwnd, ct.byref(pid)) if hwnd else 0
        title = ct.create_unicode_buffer(512)
        if hwnd:
            window_title(hwnd, title, len(title))
        return {
            "hwnd": hwnd,
            "pid": pid.value,
            "thread_id": thread_id,
            "title": title.value,
        }

    removed = []
    beats = []
    posts = []
    errors = []
    api_requests = []
    ctypes_requests = []
    boundary_violations = []
    ghost = 0x8007
    tid = threading.get_native_id()
    ready = threading.Event()
    done = threading.Event()

    @hook_proc
    def callback(code, wparam, lparam):
        if code >= 0 and wparam == 0:
            msg = ct.cast(lparam, ct.POINTER(wt.MSG)).contents
            if msg.message == ghost and not removed:
                removed.append(time.monotonic())
                taken = wt.MSG()
                if not peek(ct.byref(taken), None, ghost, ghost, 1):
                    errors.append("ghost-not-removed")
        return call_next(None, code, wparam, lparam)

    def heartbeat():
        beats.append(time.monotonic())
        ready.set()
        if done.is_set():
            root.setvar("wake_done", 1)
        else:
            root.after(25, heartbeat)

    def trigger():
        if not ready.wait(3):
            errors.append("no-heartbeat")
        time.sleep(0.1)
        if not post(tid, ghost, 0, 0):
            errors.append("ghost-post-failed")
        # 対照群の無期限待ちを必ず解き、親のタイムアウトに頼らず終了する。
        time.sleep(0.8)
        done.set()
        if not post(tid, 0, 0, 0):
            errors.append("rescue-post-failed")

    def counted_post(*args):
        caller = threading.get_native_id()
        posts.append({"args": args, "caller_tid": caller})
        if args != (tid, 0, 0, 0) or caller == tid:
            boundary_violations.append("invalid-thread-message")
            return False  # 不正な投稿は記録して止め、外部へ実際には送らない。
        return post(*args)

    # Tk 窓への別のメッセージが対照群を偶然起こすことを避け、同じ Tcl
    # Windows 通知器を使う vwait を直接実行する。Peek でスレッドのキューも作る。
    root = tk.Tcl()
    peek(ct.byref(wt.MSG()), None, 0, 0, 0)
    initial_foreground = foreground_snapshot()
    hook = set_hook(3, callback, None, tid)  # WH_GETMESSAGE、自スレッドのみ。
    if not hook:
        raise ct.WinError(ct.get_last_error())
    wake = UiThreadWake(
        WakeApiBoundary(
            {"PostThreadMessageW": counted_post}, api_requests, boundary_violations
        ),
        logging.getLogger(__name__),
    )
    # 注入APIを迂回したctypes利用も、見張りの通常境界外として拒否・記録する。
    original_ctypes = startup_wake.ct
    startup_wake.ct = WakeApiBoundary(
        {"get_last_error": ct.get_last_error}, ctypes_requests, boundary_violations
    )
    driver = threading.Thread(target=trigger, daemon=True)
    try:
        if enabled:
            wake.start()
        driver.start()
        root.after(25, heartbeat)
        root.eval("vwait wake_done")
    finally:
        done.set()
        wake.close()
        driver.join(3)
        unhook(hook)
        startup_wake.ct = original_ctypes
        final_foreground = foreground_snapshot()
    if errors:
        raise RuntimeError(errors)
    after = [t for t in beats if removed and t > removed[0]]
    # 前景変更の観測だけを模擬する。実ウィンドウへの前景・入力操作はしない。
    observed_initial = (
        -1 if simulate_external_foreground else initial_foreground["hwnd"]
    )
    observed_final = -2 if simulate_external_foreground else final_foreground["hwnd"]
    return {
        "removed": len(removed),
        "posted": len(posts),
        "posts": posts,
        "creator_tid": tid,
        "wake_api_requests": api_requests,
        "wake_ctypes_requests": ctypes_requests,
        "boundary_violations": boundary_violations,
        "first_beat_after_ghost_ms": (after[0] - removed[0]) * 1000 if after else None,
        "foreground_unchanged": observed_initial == observed_final,
        "foreground_observation_source": "simulated"
        if simulate_external_foreground
        else "native",
        "foreground_observed_handles": [observed_initial, observed_final],
        "foreground_before": initial_foreground,
        "foreground_after": final_foreground,
        "worker_stopped": wake._worker is None or not wake._worker.is_alive(),
    }


if __name__ == "__main__":
    faulthandler.dump_traceback_later(5, repeat=True)
    try:
        print(
            json.dumps(
                run(sys.argv[1] == "wake", "--simulate-external-foreground" in sys.argv)
            )
        )
    finally:
        faulthandler.cancel_dump_traceback_later()
