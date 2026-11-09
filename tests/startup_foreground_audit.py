"""通知試験専用のAPI監査と、保存証拠に対する保守的な前景判定。"""

import ctypes as ct
import json
import os
import threading
import time
import traceback
from ctypes import wintypes as wt

WATCHED = {
    "CreateWindowExW",
    "SetWindowPos",
    "ShowWindow",
    "DestroyWindow",
    "SetForegroundWindow",
    "AllowSetForegroundWindow",
    "SetActiveWindow",
    "SetFocus",
    "BringWindowToTop",
    "SwitchToThisWindow",
    "AttachThreadInput",
    "ShowWindowAsync",
    "SetWindowPlacement",
    "SetWindowLongPtrW",
    "SetWindowLongW",
}
REQUIRED = {"CreateWindowExW", "SetWindowPos", "ShowWindow", "DestroyWindow"}
FORBIDDEN = WATCHED - REQUIRED


class _NativeObservation:
    def __init__(self, bind):
        user = ct.WinDLL("user32", use_last_error=True)
        kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.foreground = bind(user, "GetForegroundWindow", wt.HWND)
        self.tick = bind(kernel, "GetTickCount64", ct.c_ulonglong)
        self.window_thread = bind(
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

    def created(self, pid):
        handle = self.open_process(0x1000, False, pid)
        if not handle:
            raise ct.WinError(ct.get_last_error())
        try:
            times = [wt.FILETIME() for _ in range(4)]
            if not self.process_times(handle, *(ct.byref(t) for t in times)):
                raise ct.WinError(ct.get_last_error())
            return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        finally:
            if not self.close_handle(handle):
                raise ct.WinError(ct.get_last_error())

    def identity(self, hwnd):
        pid = wt.DWORD()
        thread = self.window_thread(hwnd, ct.byref(pid)) if hwnd else 0
        if not thread or not pid.value:
            raise OSError("前景窓のidentityを取得できない")
        return {
            "hwnd": int(hwnd),
            "pid": pid.value,
            "thread": thread,
            "created": self.created(pid.value),
        }


class NoticeCallAudit:
    """引数・結果・例外・last-errorを保ち、試験子のbindだけを監査する。"""

    def __init__(self, win, path, role, *, observation=None):
        self.win, self.path, self.role = win, path, role
        self.original_bind = win._bind
        self.observation = observation or _NativeObservation(self.original_bind)
        self.pid = os.getpid()
        self.created = self.observation.created(self.pid)
        self.records, self.errors, self.bindings = [], [], set()
        self.calls = 0

    def record(self, kind, **details):
        error = ct.get_last_error()
        try:
            started = time.monotonic_ns()
            row = {
                "kind": kind,
                "seq": len(self.records),
                "tick": self.observation.tick(),
                "monotonic_ns": started,
                "thread": threading.get_ident(),
                "foreground": self.observation.identity(self.observation.foreground()),
                **details,
            }
            row["capture_ns"] = time.monotonic_ns() - started
            self.records.append(row)
        except Exception as exc:
            self.errors.append({"kind": kind, "error": type(exc).__name__})
        finally:
            ct.set_last_error(error)

    def identity(self, hwnd):
        error = ct.get_last_error()
        try:
            return self.observation.identity(hwnd)
        except Exception as exc:
            self.errors.append({"kind": "event_identity", "error": type(exc).__name__})
            return {}
        finally:
            ct.set_last_error(error)

    def wrap(self, name, function):
        def call(*args):
            error = ct.get_last_error()
            self.calls += 1
            call_id = self.calls
            # 自試験の窓の識別・activation指定のみ。窓名/入力内容は保存しない。
            if name == "CreateWindowExW":
                arguments = {"ex_style": args[0], "style": args[3]}
            elif name == "SetWindowPos":
                arguments = {"hwnd": args[0], "flags": args[6]}
            elif name in {"ShowWindow", "ShowWindowAsync"}:
                arguments = {"hwnd": args[0], "command": args[1]}
            else:
                arguments = {"target": args[0] if args else None}
            stack = [
                {"file": frame.filename, "line": frame.lineno, "name": frame.name}
                for frame in traceback.extract_stack(limit=8)[:-1]
            ]
            self.record(
                "api_call", call=call_id, api=name, arguments=arguments, stack=stack
            )
            ct.set_last_error(error)
            try:
                result = function(*args)
            except Exception as exc:
                error = ct.get_last_error()
                self.record(
                    "api_error", call=call_id, api=name, error=type(exc).__name__
                )
                ct.set_last_error(error)
                raise
            error = ct.get_last_error()
            self.record(
                "api_return", call=call_id, api=name, result=result, last_error=error
            )
            ct.set_last_error(error)
            return result

        return call

    def bind(self, dll, name, result, *args):
        function = self.original_bind(dll, name, result, *args)
        if name in WATCHED:
            self.bindings.add(name)
            return self.wrap(name, function)
        return function

    def __enter__(self):
        self.win._bind = self.bind
        self.record("process_started")
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.record(
                "process_finished", exception=exc_type.__name__ if exc_type else None
            )
        finally:
            self.win._bind = self.original_bind
        payload = {
            "schema": 1,
            "pid": self.pid,
            "created": self.created,
            "role": self.role,
            "bindings": sorted(self.bindings),
            "records": self.records,
            "errors": self.errors,
        }
        with self.path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


def classify_notice_foreground(audits, events, final, expected_pids):
    """未知の外部切替・採取不足も成功にしない。原ログには書き込まない。"""
    violations, errors, transitions = [], [], []
    owned = []
    points = []
    actual_pids = [audit.get("pid") for audit in audits]
    if (
        len(expected_pids) != 9
        or len(set(expected_pids)) != 9
        or len(actual_pids) != len(set(actual_pids))
        or set(actual_pids) != set(expected_pids)
    ):
        errors.append("子processの記録が不足/重複/不一致")
    owners = [audit for audit in audits if audit.get("role") == "notice-case-owner"]
    if len(owners) != 1:
        errors.append("owner記録が1件でない")
    if {audit.get("role") for audit in audits} != {
        "notice-case-owner",
        *(f"notice-case-peer-{i}" for i in range(8)),
    }:
        errors.append("owner/peer roleの欠落または重複")
    for audit in audits:
        rows = audit.get("records", [])
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("tick"), int)
            or not isinstance(row.get("monotonic_ns"), int)
            or not isinstance(row.get("foreground"), dict)
            for row in rows
        ):
            errors.append("process監査の行構造不正")
            continue
        if (
            audit.get("schema") != 1
            or not audit.get("created")
            or audit.get("errors") != []
            or len(rows) < 2
            or rows[0].get("kind") != "process_started"
            or rows[-1].get("kind") != "process_finished"
            or "exception" not in rows[-1]
            or rows[-1].get("exception") is not None
            or [row.get("seq") for row in rows] != list(range(len(rows)))
            or [row["tick"] for row in rows] != sorted(row["tick"] for row in rows)
            or [row["monotonic_ns"] for row in rows]
            != sorted(row["monotonic_ns"] for row in rows)
        ):
            errors.append(f"process監査不完全: {audit.get('pid')}")
        if not {"SetForegroundWindow", "AllowSetForegroundWindow"} <= set(
            audit.get("bindings", [])
        ):
            errors.append("backend構築前からのbind監査がない")
        calls = {}
        returned = set()
        for row in rows:
            points.append(row.get("foreground", {}))
            kind, api = row.get("kind"), row.get("api")
            if kind == "api_call":
                call_id = row.get("call")
                if call_id in calls or not call_id or api not in WATCHED:
                    errors.append("API呼出identity不正")
                calls[call_id] = row
                args = row.get("arguments", {})
                if api in FORBIDDEN:
                    violations.append(f"禁止API要求: {api}")
                if (
                    api == "CreateWindowExW"
                    and not args.get("ex_style", 0) & 0x08000000
                ):
                    violations.append("WS_EX_NOACTIVATE欠落")
                if api == "SetWindowPos" and not args.get("flags", 0) & 0x10:
                    violations.append("SWP_NOACTIVATE欠落")
                if api == "ShowWindow" and args.get("command") != 4:
                    violations.append("SW_SHOWNOACTIVATE以外の表示要求")
            elif kind in {"api_return", "api_error"}:
                call_id = row.get("call")
                call = calls.get(call_id)
                if not call or call_id in returned or call.get("api") != api:
                    errors.append("API呼出/復帰の対応不正")
                returned.add(call_id)
                if kind == "api_error":
                    errors.append("API例外")
                if api in REQUIRED - {"ShowWindow"} and not row.get("result"):
                    errors.append(f"API不成立: {api}")
                if api == "CreateWindowExW" and call and row.get("result"):
                    owned.append(
                        {
                            "hwnd": row["result"],
                            "pid": audit["pid"],
                            "created": audit["created"],
                            "start": call["tick"],
                            "end": rows[-1]["tick"],
                        }
                    )
        if set(calls) != returned:
            errors.append("API復帰記録欠落")
        called = {row.get("api") for row in calls.values()}
        if audit.get("role") == "notice-case-owner":
            if not REQUIRED <= called or not REQUIRED <= set(audit.get("bindings", [])):
                errors.append("通知の必須API監査欠落")
        else:
            if not str(audit.get("role", "")).startswith("notice-case-peer-"):
                errors.append("未知の試験子role")
            if calls:
                violations.append("peerが通知/activation APIを実行")

    if not events or events[0].get("event") != "observer_started":
        errors.append("WinEvent監査開始なし")
    if (
        not events
        or events[-1].get("event") != "observer_stopped"
        or events[-1].get("removed") is not True
        or events[-1].get("errors") != []
    ):
        errors.append("WinEvent監査終了/解除不成立")
    if not {"notice_show_call", "notice_published", "notice_returned"} <= {
        row.get("event") for row in events
    }:
        errors.append("通知の観測区間不完全")
    for row in events:
        if row.get("event") == "winevent" and row.get("event_id") != 3:
            errors.append("前景以外のevent混入")
        if row.get("event") == "notice_published":
            if not any(window["hwnd"] == row.get("hwnd") for window in owned):
                errors.append("通知HWNDとCreateWindowの対応なし")
            continue
        if not row.get("identity_available") or not row.get("process_created"):
            errors.append("WinEvent/前景窓identity不足")
        point = {
            "hwnd": row.get("hwnd"),
            "pid": row.get("pid"),
            "created": row.get("process_created"),
            "thread": row.get("window_thread_id"),
        }
        points.append(point)
        if row.get("event") == "winevent":
            event_tick = row.get("event_tick")
            if not isinstance(event_tick, int):
                errors.append("WinEvent発生時刻欠落")
            else:
                for window in owned:
                    # WinEvent時刻はDWORD。API観測はGetTickCount64。
                    age = (event_tick - window["start"]) & 0xFFFFFFFF
                    if row.get("hwnd") == window["hwnd"] and age <= (
                        window["end"] - window["start"]
                    ):
                        violations.append("通知窓への一時的な前景化")

    baseline = None
    for point in points:
        if not all(point.get(key) for key in ("hwnd", "pid", "created", "thread")):
            errors.append("前景窓identityを取得できない")
            continue
        identity = (point["hwnd"], point["pid"], point["created"])
        if point["pid"] in expected_pids:
            violations.append("対象試験子の窓が前景化")
        if baseline is None:
            baseline = identity
        elif identity != baseline:
            transitions.append("要求元未確定の前景切替")
    for before, after in (
        ("foreground_before", "foreground_after"),
        ("foreground_before_show", "foreground_after_show"),
        ("foreground_before_close", "foreground_after_close"),
    ):
        if not final.get(before) or not final.get(after):
            errors.append(f"前景実測値欠落: {before}/{after}")
        elif final[before] != final[after]:
            transitions.append(f"前景不一致: {before}/{after}")
    verdict = (
        "violation"
        if violations
        else "audit_error"
        if errors
        else "unexplained_transition"
        if transitions
        else "pass"
    )
    return {
        "verdict": verdict,
        "violations": sorted(set(violations)),
        "audit_errors": sorted(set(errors)),
        "transitions": sorted(set(transitions)),
    }
