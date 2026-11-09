"""前景奪取・未知切替・監査欠落を、実窓を操作せず故障注入する。"""

import copy
import ctypes as ct
import json
import os
from types import SimpleNamespace

import pytest

from tests.startup_foreground_audit import NoticeCallAudit, classify_notice_foreground


def _identity(hwnd=40, pid=400, created=4000):
    return {"hwnd": hwnd, "pid": pid, "created": created, "thread": pid + 1}


def _row(kind, seq, **values):
    return {
        "kind": kind,
        "seq": seq,
        "tick": 100 + seq,
        "monotonic_ns": 1000 + seq,
        "thread": 1,
        "foreground": _identity(),
        "capture_ns": 1,
        **values,
    }


@pytest.fixture
def evidence():
    calls = [
        ("CreateWindowExW", {"ex_style": 0x08000080, "style": 0x80000000}, 50),
        ("SetWindowPos", {"hwnd": 50, "flags": 0x14}, 1),
        ("ShowWindow", {"hwnd": 50, "command": 4}, 0),
        ("DestroyWindow", {"target": 50}, 1),
    ]
    rows = [_row("process_started", 0)]
    for call_id, (api, arguments, result) in enumerate(calls, 1):
        rows.append(
            _row("api_call", len(rows), call=call_id, api=api, arguments=arguments)
        )
        rows.append(_row("api_return", len(rows), call=call_id, api=api, result=result))
    rows.append(_row("process_finished", len(rows), exception=None))
    bindings = [api for api, _, _ in calls] + [
        "SetForegroundWindow",
        "AllowSetForegroundWindow",
    ]
    audits = [
        {
            "schema": 1,
            "pid": 10,
            "created": 1000,
            "role": "notice-case-owner",
            "bindings": bindings,
            "records": rows,
            "errors": [],
        }
    ]
    for i in range(8):
        audits.append(
            {
                "schema": 1,
                "pid": 11 + i,
                "created": 1001 + i,
                "role": f"notice-case-peer-{i}",
                "bindings": bindings[-2:],
                "records": [
                    _row("process_started", 0),
                    _row("process_finished", 1, exception=None),
                ],
                "errors": [],
            }
        )
    events = []
    for event in (
        "observer_started",
        "notice_show_call",
        "notice_published",
        "notice_returned",
        "observer_stopped",
    ):
        events.append(
            {
                "event": event,
                "tick": 103,
                "hwnd": 50 if event == "notice_published" else 40,
                "pid": 10 if event == "notice_published" else 400,
                "process_created": 1000 if event == "notice_published" else 4000,
                "window_thread_id": 401,
                "identity_available": True,
                "removed": True,
                "errors": [],
            }
        )
    final = {
        name: 40
        for name in (
            "foreground_before",
            "foreground_after",
            "foreground_before_show",
            "foreground_after_show",
            "foreground_before_close",
            "foreground_after_close",
        )
    }
    return audits, events, final, list(range(10, 19))


def test_complete_unchanged_foreground_passes(evidence):
    original = copy.deepcopy(evidence)
    assert classify_notice_foreground(*evidence)["verdict"] == "pass"
    assert evidence == original


def test_transient_notice_activation_fails_even_after_return_to_original(evidence):
    audits, events, final, pids = evidence
    events.insert(
        -1,
        {
            **events[0],
            "event": "winevent",
            "event_id": 3,
            "event_tick": 104,
            "hwnd": 50,
            "pid": 10,
            "process_created": 1000,
        },
    )
    assert final["foreground_before"] == final["foreground_after"]
    assert classify_notice_foreground(audits, events, final, pids)["verdict"] == (
        "violation"
    )


def test_api_request_rejected_by_os_is_still_violation(evidence):
    rows = evidence[0][0]["records"]
    rows.insert(-1, _row("api_call", 0, api="SetForegroundWindow", call=5))
    rows.insert(-1, _row("api_return", 0, api="SetForegroundWindow", call=5, result=0))
    for i, row in enumerate(rows):
        row["seq"] = i
    result = classify_notice_foreground(*evidence)
    assert result["verdict"] == "violation"
    assert "禁止API要求: SetForegroundWindow" in result["violations"]


@pytest.mark.parametrize(
    "api,arguments",
    [
        ("CreateWindowExW", {"ex_style": 0x80}),
        ("SetWindowPos", {"hwnd": 50, "flags": 4}),
        ("ShowWindow", {"hwnd": 50, "command": 5}),
    ],
)
def test_activation_flags_regression_fails(evidence, api, arguments):
    row = next(
        row
        for row in evidence[0][0]["records"]
        if row["kind"] == "api_call" and row["api"] == api
    )
    row["arguments"] = arguments
    assert classify_notice_foreground(*evidence)["verdict"] == "violation"


def test_unknown_external_transition_fails_without_claiming_product_cause(evidence):
    evidence[1].insert(
        -1,
        {
            **evidence[1][0],
            "event": "winevent",
            "event_id": 3,
            "event_tick": 104,
            "hwnd": 90,
            "pid": 900,
            "process_created": 9000,
        },
    )
    result = classify_notice_foreground(*evidence)
    assert result["verdict"] == "unexplained_transition"
    assert not result["violations"]


@pytest.mark.parametrize(
    "damage",
    [
        "missing_peer",
        "duplicate_peer",
        "missing_start",
        "missing_finish",
        "missing_return",
        "missing_tick",
        "missing_bind",
        "duplicate_role",
        "callback_error",
        "unhook_failed",
        "event_identity",
        "process_identity",
        "local_value",
    ],
)
def test_incomplete_observation_never_passes(evidence, damage):
    audits, events, final, _ = evidence
    if damage == "missing_peer":
        audits.pop()
    elif damage == "duplicate_peer":
        audits[-1] = copy.deepcopy(audits[-2])
    elif damage == "missing_start":
        audits[0]["records"].pop(0)
    elif damage == "missing_finish":
        audits[0]["records"].pop()
    elif damage == "missing_return":
        audits[0]["records"].pop(2)
    elif damage == "missing_tick":
        audits[0]["records"][1].pop("tick")
    elif damage == "missing_bind":
        audits[0]["bindings"].remove("SetForegroundWindow")
    elif damage == "duplicate_role":
        audits[-1]["role"] = audits[-2]["role"]
    elif damage == "callback_error":
        events[-1]["errors"] = ["injected"]
    elif damage == "unhook_failed":
        events[-1]["removed"] = False
    elif damage == "event_identity":
        events[0].pop("process_created")
    elif damage == "process_identity":
        audits[0]["records"][0]["foreground"]["hwnd"] = 0
    elif damage == "local_value":
        final.pop("foreground_after_close")
    assert classify_notice_foreground(*evidence)["verdict"] == "audit_error"


def test_local_change_is_not_silently_accepted(evidence):
    evidence[2]["foreground_after_show"] = 90
    assert classify_notice_foreground(*evidence)["verdict"] == "unexplained_transition"


class _Observation:
    def created(self, pid):
        return pid + 1000

    def tick(self):
        return 100

    def foreground(self):
        return 40

    def identity(self, hwnd):
        return _identity(hwnd)


def test_wrapper_preserves_arguments_return_last_error_and_restores_bind(tmp_path):
    received = []

    def function(*args):
        received.append((args, ct.get_last_error()))
        ct.set_last_error(321)
        return 0

    win = SimpleNamespace(_bind=lambda *args: function)
    original = win._bind
    path = tmp_path / "calls.json"
    with NoticeCallAudit(win, path, "unit", observation=_Observation()):
        show = win._bind(None, "ShowWindow", None)
        ct.set_last_error(123)
        assert show(50, 4) == 0
        assert ct.get_last_error() == 321
    assert received == [((50, 4), 123)]
    assert win._bind is original
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["pid"] == os.getpid()
    assert not saved["errors"]
    assert saved["records"][-1]["kind"] == "process_finished"


def test_exception_restores_bind_and_retains_original_error(tmp_path):
    expected = OSError("injected")

    def function(*args):
        ct.set_last_error(555)
        raise expected

    win = SimpleNamespace(_bind=lambda *args: function)
    original = win._bind
    path = tmp_path / "calls.json"
    with pytest.raises(OSError, match="injected") as caught:
        with NoticeCallAudit(win, path, "unit", observation=_Observation()):
            win._bind(None, "DestroyWindow", None)(50)
    assert caught.value is expected
    assert ct.get_last_error() == 555
    assert win._bind is original
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["records"][-1]["exception"] == "OSError"
    assert saved["records"][-2]["kind"] == "api_error"


def test_capture_failure_is_recorded_without_changing_api_behavior(tmp_path):
    observation = _Observation()

    def unavailable(hwnd):
        raise OSError("no identity")

    observation.identity = unavailable
    win = SimpleNamespace(_bind=lambda *args: lambda *args2: 1)
    path = tmp_path / "calls.json"
    with NoticeCallAudit(win, path, "unit", observation=observation):
        assert win._bind(None, "DestroyWindow", None)(50) == 1
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["errors"]
    assert not saved["records"]
