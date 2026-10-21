"""起動制御の絶対期限・集約・所有権を仮想時計で検証する。"""

import struct
from dataclasses import asdict
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pagefolio.startup_control import ActivationRequest, StartupCoordinator


class ClockBackend:
    def __init__(self):
        self.now = 10000
        self.calls = 0
        self.result = "foreground_denied"
        self.during_restore = lambda: None
        self.logger = SimpleNamespace(debug=lambda *a: None)

    def tick_ms(self):
        return self.now

    def restore_window(self, hwnd, is_current=lambda: True):
        self.during_restore()
        if not is_current():
            return "expired"
        self.calls += 1
        return self.result

    def request_activation(self, started_tick):
        self.now = started_tick + 5000
        return "completed"

    def close(self, **kwargs):
        pass

    def stop_accepting(self):
        pass


@pytest.fixture
def control():
    backend = ClockBackend()
    coordinator = StartupCoordinator(backend)
    coordinator.root = SimpleNamespace(winfo_id=lambda: 7)
    return coordinator, backend


def request(coordinator, backend, **kwargs):
    values = dict(
        request_id=uuid4().hex,
        issued_tick=backend.now,
        deadline_tick=backend.now + 5000,
        generation=coordinator.generation,
    )
    values.update(kwargs)
    return asdict(ActivationRequest(**values))


def test_accepted_is_not_terminal_and_eight_requests_restore_once(control):
    c, b = control
    requests = [request(c, b) for _ in range(8)]
    assert all(c._receive(r)["result"] == "accepted" for r in requests)
    c._dispatch_pending()
    assert b.calls == 1
    replies = [c._receive(r) for r in requests]
    assert all(r["result"] == "foreground_denied" for r in replies)
    assert sum(r["coalesced"] for r in replies) == 7


@pytest.mark.parametrize("elapsed, expected", [(4999, 1), (5000, 0), (8000, 0)])
def test_busy_main_thread_discards_expired_request(control, elapsed, expected):
    c, b = control
    raw = request(c, b)
    assert c._receive(raw)["result"] == "accepted"
    b.now += elapsed
    c._dispatch_pending()
    assert b.calls == expected
    assert c._receive(raw)["result"] == ("foreground_denied" if expected else "expired")


def test_fixed_cooldown_does_not_extend_and_edge_is_independent(control):
    c, b = control
    first = request(c, b)
    c._receive(first)
    c._dispatch_pending()
    completed = b.now
    for offset in (1, 200, 499):
        b.now = completed + offset
        reply = c._receive(request(c, b))
        assert reply["result"] == "foreground_denied"
        assert reply["coalesced"]
        assert reply["completed_tick"] == completed
    b.now = completed + 500
    raw = request(c, b)
    assert c._receive(raw)["result"] == "accepted"
    c._dispatch_pending()
    assert b.calls == 2
    assert not c._receive(raw)["coalesced"]


def test_callback_reentry_and_terminal_last_arrival_coalesce(control):
    c, b = control
    first = request(c, b)
    late = request(c, b)
    c._receive(first)

    def nested():
        assert c._receive(late)["result"] == "accepted"
        c._dispatch_pending()

    b.during_restore = nested
    c._dispatch_pending()
    assert b.calls == 1
    assert c._receive(late)["coalesced"]


def test_each_batch_member_keeps_own_deadline(control):
    c, b = control
    old = request(c, b, issued_tick=6000, deadline_tick=11000)
    fresh = request(c, b)
    c._receive(old)
    c._receive(fresh)
    b.during_restore = lambda: setattr(b, "now", 11000)
    c._dispatch_pending()
    assert b.calls == 1
    assert c._receive(old)["result"] == "expired"
    assert c._receive(fresh)["result"] == "foreground_denied"


def test_all_members_expire_before_os_side_effect(control):
    c, b = control
    raw = request(c, b)
    c._receive(raw)
    b.during_restore = lambda: setattr(b, "now", b.now + 5000)
    c._dispatch_pending()
    assert b.calls == 0
    assert c._receive(raw)["result"] == "expired"


@pytest.mark.parametrize(
    "values",
    [
        {"generation": "0" * 32},
        {"issued_tick": 10001},
        {"deadline_tick": 15001},
        {"op": "delete"},
        {"issued_tick": True},
        {"request_id": "x" * 32},
        {"request_id": "a" * 1025},
    ],
)
def test_invalid_requests_never_reach_ui(control, values):
    c, b = control
    assert c._receive(request(c, b, **values))["result"] in {"invalid", "expired"}
    c._dispatch_pending()
    assert b.calls == 0


def test_generation_change_invalidates_queued_requests(control):
    c, b = control
    c._receive(request(c, b))
    c.generation = uuid4().hex
    c._dispatch_pending()
    assert b.calls == 0


def test_repeated_id_never_repeats_side_effect_and_modified_id_is_invalid(control):
    c, b = control
    raw = request(c, b)
    c._receive(raw)
    c._dispatch_pending()
    b.now += 600
    assert c._receive(raw)["result"] == "foreground_denied"
    assert (
        c._receive({**raw, "deadline_tick": raw["deadline_tick"] - 1})["result"]
        == "invalid"
    )
    c._dispatch_pending()
    assert b.calls == 1


def test_pending_queue_and_terminal_cache_are_bounded(control):
    c, b = control
    for _ in range(32):
        assert c._receive(request(c, b))["result"] == "accepted"
    assert c._receive(request(c, b))["result"] == "busy"
    c._dispatch_pending()
    for _ in range(160):
        c._receive(request(c, b))
    assert len(c.terminal_cache) <= 128


def test_late_ack_never_reports_success(control):
    c, b = control
    assert c.request_activation(b.now).result == "expired"


@pytest.mark.parametrize("payload", [b"{", b"[]", b"null", b"\xff"])
def test_wire_invalid_json_never_reaches_receiver(monkeypatch, payload):
    from pagefolio import startup_win32 as win

    chunks = iter([struct.pack("<I", len(payload)), payload])
    monkeypatch.setattr(win, "_read_exact", lambda *a: next(chunks))
    with pytest.raises((ValueError, UnicodeError)):
        win._read_frame(None, None, 15000)


@pytest.mark.parametrize("size", [0, 1025, 2**32 - 1])
def test_oversized_frame_rejected_before_payload(monkeypatch, size):
    from pagefolio import startup_win32 as win

    monkeypatch.setattr(win, "_read_exact", lambda *a: struct.pack("<I", size))
    with pytest.raises(ValueError, match="サイズ"):
        win._read_frame(None, None, 15000)


@pytest.mark.parametrize(
    "changes",
    [
        {"result": "unknown"},
        {"request_id": "b" * 32},
        {"completed_tick": 15000},
        {"completed_tick": 9999},
        {"completed_tick": True},
        {"coalesced": "yes"},
    ],
)
def test_unknown_or_invalid_terminal_is_not_success(changes):
    from pagefolio.startup_win32 import Win32Backend

    backend = Win32Backend.__new__(Win32Backend)
    backend.tick_ms = lambda: 14999
    reply = {
        "request_id": "a" * 32,
        "result": "completed",
        "completed_tick": 14999,
        "coalesced": False,
    }
    assert (
        backend._validate_reply({**reply, **changes}, "a" * 32, 10000, 15000)
        == "connection_failed"
    )


@pytest.mark.parametrize("operation", ["read", "write"])
def test_expired_io_never_starts_native_operation(operation):
    from pagefolio import startup_win32 as win

    api = SimpleNamespace(GetTickCount64=lambda: 15000)
    with pytest.raises(TimeoutError):
        win._io(
            api, None, operation, 15000, data=b"x" if operation == "write" else None
        )


def test_guard_rechecks_before_foreground_and_flash():
    from pagefolio.startup_win32 import Win32Backend

    backend = Win32Backend.__new__(Win32Backend)
    backend._assert_thread = lambda: None
    calls = []
    ticks = iter([True, False])
    backend.api = SimpleNamespace(
        GetAncestor=lambda *a: 7,
        SetForegroundWindow=lambda *a: calls.append("foreground"),
    )
    assert backend.restore_window(7, is_current=lambda: next(ticks)) == "expired"
    assert calls == []
    ticks = iter([True, True, False])
    assert backend.restore_window(7, is_current=lambda: next(ticks)) == "expired"
    assert calls == ["foreground"]


class TakeoverBackend(ClockBackend):
    def __init__(self):
        super().__init__()
        self.observed_owner = {
            "pid": 77,
            "process_created": 1234,
            "generation": "a" * 32,
            "state": "initializing",
        }
        self.observed_process = object()
        self.exited = True
        self.claims = 0
        self.listen_calls = 0
        self.winner = "acquired"

    def _process_has_exited(self, process):
        return self.exited

    def try_takeover(self, generation, owner, deadline):
        self.claims += 1
        return self.winner

    def listen(self, callback):
        self.listen_calls += 1


def test_confirmed_initializing_process_death_claims_only_once():
    b = TakeoverBackend()
    c = StartupCoordinator(b)
    assert c._try_takeover(15000)
    assert not c._try_takeover(15000)
    assert b.claims == b.listen_calls == 1
    assert c.takeover_attempted


@pytest.mark.parametrize(
    "condition",
    ["alive", "ready", "closing", "released", "unknown", "no_handle", "deadline"],
)
def test_unconfirmed_or_noninitializing_death_never_claims(condition):
    b = TakeoverBackend()
    if condition == "alive":
        b.exited = False
    elif condition in {"ready", "closing", "released"}:
        b.observed_owner["state"] = condition
    elif condition == "unknown":
        b.observed_owner = None
    elif condition == "no_handle":
        b.observed_process = None
    elif condition == "deadline":
        b.now = 15000
    c = StartupCoordinator(b)
    assert not c._try_takeover(15000)
    assert b.claims == b.listen_calls == 0


def test_losing_candidate_never_attempts_second_claim():
    b = TakeoverBackend()
    b.winner = "existing"
    c = StartupCoordinator(b)
    assert not c._try_takeover(15000)
    assert not c._try_takeover(15000)
    assert b.claims == 1
    assert b.listen_calls == 0


def test_close_publishes_release_only_after_root_destroyed():
    b = ClockBackend()
    records = []
    b.close = lambda **kwargs: records.append(kwargs)
    c = StartupCoordinator(b)
    c.root = SimpleNamespace(winfo_exists=lambda: True)
    c.close()
    assert records == [{"root_absent": False}]
    c = StartupCoordinator(b)
    c.root = SimpleNamespace(winfo_exists=lambda: False)
    c.close()
    assert records[-1] == {"root_absent": True}


@pytest.mark.parametrize(
    "failure", [PermissionError("OpenProcess"), PermissionError("PID再利用")]
)
def test_identity_validation_failure_never_pins_or_takes_over(failure):
    from pagefolio.startup_win32 import Win32Backend

    b = Win32Backend.__new__(Win32Backend)
    b.observed_owner = b.observed_process = None
    b._validate_peer = lambda *args: (_ for _ in ()).throw(failure)
    owner = {"pid": 1, "process_created": 123, "session_id": 1, "generation": "a" * 32}
    with pytest.raises(PermissionError):
        b._observe_owner(owner)
    assert b.observed_process is b.observed_owner is None


def test_wait_failed_is_not_death():
    import ctypes as ct

    from pagefolio.startup_win32 import Win32Backend

    b = Win32Backend.__new__(Win32Backend)

    def failed(*args):
        ct.set_last_error(6)
        return 0xFFFFFFFF

    b.api = SimpleNamespace(WaitForSingleObject=failed)
    with pytest.raises(OSError):
        b._process_has_exited(SimpleNamespace(value=7))


def test_readiness_retries_share_deadline_and_clamp_poll(monkeypatch):
    from pagefolio import startup_win32 as win

    b = win.Win32Backend.__new__(win.Win32Backend)
    clock = [10000]
    b.tick_ms = lambda: clock[0]
    b.logger = SimpleNamespace(debug=lambda *args: None)
    b.takeover_callback = lambda deadline: False
    b._read_owner = lambda: {"state": "initializing", "ready": False}
    b._observe_owner = lambda owner: object()
    b._process_has_exited = lambda process: False
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += int(seconds * 1000)

    monkeypatch.setattr(win.time, "sleep", sleep)
    assert b.request_activation(5013) == "expired"
    assert clock[0] == 10013
    assert sleeps == [0.013]


@pytest.mark.parametrize("operation", ["read", "write"])
def test_fragmented_transport_always_uses_original_deadline(monkeypatch, operation):
    from pagefolio import startup_win32 as win

    deadlines = []

    def io(api, pipe, op, deadline, data=None, size=0):
        deadlines.append(deadline)
        return 1 if op == "write" else b"x"

    monkeypatch.setattr(win, "_io", io)
    if operation == "read":
        assert win._read_exact(None, None, 4, 15000) == b"xxxx"
    else:
        win._write_frame(None, None, {"op": "activate"}, 15000)
    assert len(deadlines) >= 4
    assert set(deadlines) == {15000}


def test_coalesced_terminal_may_precede_new_request_issued_tick():
    from pagefolio.startup_win32 import Win32Backend

    b = Win32Backend.__new__(Win32Backend)
    b.tick_ms = lambda: 10499
    reply = {
        "request_id": "a" * 32,
        "result": "foreground_denied",
        "completed_tick": 10000,
        "coalesced": True,
    }
    assert b._validate_reply(reply, "a" * 32, 10499, 15499) == "foreground_denied"
    assert b._validate_reply(reply, "a" * 32, 10500, 15500) == "connection_failed"
