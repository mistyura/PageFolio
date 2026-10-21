"""起動前案内の事実分類・有限期限・非活性境界の回帰試験。"""

import logging
import sys
import threading
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from pagefolio.startup_control import StartupCoordinator, StartupOutcome


def test_claim_failure_is_check_failed_without_owner_assumption():
    class Backend:
        def claim(self, generation):
            raise OSError(5, "private path / SID / API")

    try:
        observed = StartupCoordinator(Backend()).claim().result
    except OSError:
        observed = "unhandled_exception"
    assert observed == "check_failed"


@pytest.mark.parametrize(
    "result,verified,expected",
    [
        ("check_failed", False, "check_failed"),
        ("connection_failed", False, "check_failed"),
        ("connection_failed", True, "contact_failed"),
        ("expired", False, "timeout"),
        ("expired", True, "timeout"),
        ("completed", True, None),
        ("foreground_denied", True, None),
        ("primary", False, None),
    ],
)
def test_reason_uses_only_verified_facts(result, verified, expected):
    from pagefolio.startup_notice import _failure_reason

    reason = _failure_reason(StartupOutcome(result), verified)
    assert (reason.value if reason else None) == expected


@pytest.mark.parametrize(
    "langid,expected", [(0x411, "ja"), (0x409, "en"), (0x804, "en")]
)
def test_os_language_without_settings_io(langid, expected):
    from pagefolio.startup_notice import _notice_language

    assert _notice_language(langid) == expected


def test_notice_text_is_fixed_localized_and_private_data_free():
    from pagefolio.startup_notice import StartupFailureReason, _notice_text

    for language in ("ja", "en"):
        for reason in StartupFailureReason:
            title, message, close = _notice_text(reason, language)
            assert title == "PageFolio"
            assert message and close
            assert not any(
                token in message for token in ("SID", "PID", "traceback", "API")
            )


class NoticeBackend:
    def __init__(self, *, acquired=True, failed=False):
        self.observed_owner = {"pid": 1}
        self.logger = logging.getLogger("notice-test")
        self.acquired, self.failed = acquired, failed
        self.calls = []
        self.last_os_error = 5

    @contextmanager
    def _create_notice_lease(self, reason):
        self.calls.append(("lease", reason))
        try:
            yield SimpleNamespace(acquired=self.acquired)
        finally:
            self.calls.append(("release", reason))

    def notice_language(self):
        return 0x411

    def display_notice(self, reason, text, lease):
        self.calls.append(("show", reason, text))
        if self.failed:
            raise OSError(5, "private secret")

    def close(self):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 起動入口")
def test_backend_constructor_failure_uses_independent_notice(monkeypatch):
    from pagefolio import startup_win32
    from pagefolio.__main__ import main

    marker = "private-path-SID-secret"
    calls = []
    notice = NoticeBackend()
    notice.observed_owner = None

    def failed_backend():
        calls.append("backend")
        raise OSError(5, marker)

    def notice_factory():
        calls.append("notice")
        return notice

    monkeypatch.setattr(
        startup_win32, "Win32NoticeBackend", notice_factory, raising=False
    )
    try:
        result = main(backend_factory=failed_backend)
    except OSError:
        result = "unhandled_exception"
    assert result == "check_failed"
    assert calls == ["backend", "notice"]
    assert [call[0] for call in notice.calls] == ["lease", "show", "release"]
    assert not any(marker in str(call) for call in notice.calls)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 起動入口")
def test_initialization_notice_factory_failure_is_finite(monkeypatch, caplog):
    from pagefolio import startup_win32
    from pagefolio.__main__ import main

    marker = "private-path-SID-secret"
    attempts = []

    def failed_backend():
        raise OSError(5, marker)

    def failed_notice():
        attempts.append(1)
        raise OSError(5, marker)

    monkeypatch.setattr(
        startup_win32, "Win32NoticeBackend", failed_notice, raising=False
    )
    with caplog.at_level(logging.WARNING):
        try:
            result = main(backend_factory=failed_backend)
        except OSError:
            result = "unhandled_exception"
    assert result == "notification_unavailable"
    assert attempts == [1]
    assert marker not in caplog.text


@pytest.mark.parametrize("result", ["completed", "foreground_denied", "primary"])
def test_success_and_foreground_denial_never_enter_notice_boundary(result):
    from pagefolio.startup_notice import show_startup_failure

    backend = NoticeBackend()
    assert (
        show_startup_failure(StartupOutcome(result), backend).result == "not_required"
    )
    assert not backend.calls


@pytest.mark.parametrize("acquired,expected", [(True, "shown"), (False, "coalesced")])
def test_notice_lease_controls_display(acquired, expected):
    from pagefolio.startup_notice import show_startup_failure

    backend = NoticeBackend(acquired=acquired)
    assert (
        show_startup_failure(StartupOutcome("connection_failed"), backend).result
        == expected
    )
    assert sum(call[0] == "show" for call in backend.calls) == int(acquired)
    assert backend.calls[-1][0] == "release"


def test_failed_window_is_not_reported_as_shown_and_private_error_is_not_logged(caplog):
    from pagefolio.startup_notice import show_startup_failure

    backend = NoticeBackend(failed=True)
    with caplog.at_level(logging.WARNING):
        outcome = show_startup_failure(StartupOutcome("expired"), backend)
    assert outcome.result == "notification_unavailable"
    assert outcome.os_error == 5
    assert "private secret" not in caplog.text
    assert backend.calls[-1][0] == "release"


@pytest.mark.parametrize(
    "now,remaining", [(100, 10000), (10099, 1), (10100, 0), (10200, 0)]
)
def test_notice_fixed_deadline_9999_10000(now, remaining):
    from pagefolio.startup_notice import (
        NOTICE_LIFETIME_MS,
        notice_deadline_tick,
        notice_remaining_ms,
    )

    assert NOTICE_LIFETIME_MS == 10000
    deadline = notice_deadline_tick(100)
    assert deadline == 10100
    assert notice_remaining_ms(deadline, now) == remaining


@pytest.mark.skipif(sys.platform != "win32", reason="実mutexの所有threadを確認")
def test_mutex_existence_without_published_window_is_not_coalesced():
    from uuid import uuid4

    from pagefolio.startup_win32 import NoticeLease, Win32Backend

    namespace = uuid4().hex
    ready, release = threading.Event(), threading.Event()
    errors = []

    def hold_unpublished():
        backend = Win32Backend(namespace)
        try:
            with NoticeLease(backend, "check_failed"):
                ready.set()
                release.wait(3)
        except Exception as e:
            errors.append(e)
            ready.set()
        finally:
            backend.close()

    owner = threading.Thread(target=hold_unpublished)
    owner.start()
    backend = Win32Backend(namespace)
    try:
        assert ready.wait(2) and not errors
        try:
            with NoticeLease(backend, "check_failed") as lease:
                observed = "coalesced" if not lease.acquired else "new_window"
        except (OSError, ValueError):
            observed = "notification_unavailable"
        assert observed == "notification_unavailable"
    finally:
        release.set()
        owner.join(2)
        backend.close()
    assert not owner.is_alive() and not errors


@pytest.mark.parametrize(
    "state,alive,visible,now,expected",
    [
        ("shown", True, True, 9999, "visible"),
        ("shown", True, True, 10000, "unknown"),
        ("shown", True, False, 500, "unknown"),
        ("preparing", True, False, 500, "unknown"),
        ("closed", True, False, 500, "closed"),
        ("shown", False, False, 500, "dead"),
    ],
)
def test_notice_snapshot_separates_visible_closed_dead_and_unknown(
    state, alive, visible, now, expected
):
    from pagefolio.startup_win32 import NoticeLease

    @contextmanager
    def peer(*args, **kwargs):
        yield object()

    def window_pid(hwnd, pid):
        pid._obj.value = 123
        return 1

    def window_class(hwnd, buffer, size):
        buffer.value = "PageFolioNotice" + "a" * 32
        return len(buffer.value)

    backend = SimpleNamespace(
        prefix="test",
        _validate_peer=peer,
        _process_has_exited=lambda p: not alive,
        tick_ms=lambda: now,
        api=SimpleNamespace(
            GetWindowThreadProcessId=window_pid,
            GetClassNameW=window_class,
            IsWindow=lambda h: visible,
            IsWindowVisible=lambda h: visible,
        ),
    )
    snapshot = {
        "pid": 123,
        "process_created": 456,
        "state": state,
        "hwnd": 789,
        "deadline_tick": 10000,
        "generation": "a" * 32,
    }
    lease = NoticeLease(backend, "check_failed")
    assert lease._owner_status(snapshot) == expected
    assert snapshot["deadline_tick"] == 10000


@pytest.mark.skipif(sys.platform != "win32", reason="実Win32の失敗/cleanup境界")
def test_notice_creation_failure_is_finite_and_releases_lease(monkeypatch):
    import ctypes as ct
    import time
    from uuid import uuid4

    from pagefolio import startup_win32 as win
    from pagefolio.startup_notice import show_startup_failure

    backend = win.Win32Backend(uuid4().hex)
    original = win._bind

    def bind(dll, name, result, *args):
        if name == "CreateWindowExW":

            def denied(*values):
                ct.set_last_error(5)
                return 0

            return denied
        return original(dll, name, result, *args)

    monkeypatch.setattr(win, "_bind", bind)
    try:
        started = time.monotonic()
        result = show_startup_failure(StartupOutcome("expired"), backend)
        assert result.result == "notification_unavailable" and result.os_error == 5
        assert time.monotonic() - started < 0.5
        # 前回の失敗でmutexを残さず、手動closeと同様に新ownerが取得できる。
        with win.NoticeLease(backend, "timeout") as lease:
            assert lease.acquired
    finally:
        backend.close()


@pytest.mark.skipif(sys.platform != "win32", reason="実mappingの公開途中を注入")
def test_partial_notice_publication_fails_closed_and_cleans_handles():
    import ctypes as ct
    from uuid import uuid4

    from pagefolio.startup_win32 import NoticeLease, Win32Backend

    backend = Win32Backend(uuid4().hex)
    try:
        with NoticeLease(backend, "timeout") as owner:
            ct.c_ulonglong.from_address(owner.view).value = 3
            candidate = NoticeLease(backend, "timeout")
            with pytest.raises(ValueError, match="公開途中"):
                candidate.__enter__()
            assert candidate.view is None
            assert candidate.handle.value is None
            assert candidate.mapping.value is None
    finally:
        backend.close()


@pytest.mark.skipif(
    sys.platform != "win32", reason="実mutexのabandonedとprocess生存を区別"
)
def test_abandoned_notice_thread_with_live_process_is_not_new_owner():
    from uuid import uuid4

    from pagefolio.startup_win32 import NoticeLease, Win32Backend

    namespace = uuid4().hex
    holders = []

    def abandon():
        backend = Win32Backend(namespace)
        lease = NoticeLease(backend, "timeout")
        lease.__enter__()
        holders.append((backend, lease))

    thread = threading.Thread(target=abandon)
    thread.start()
    thread.join(2)
    assert not thread.is_alive() and len(holders) == 1
    backend = Win32Backend(namespace)
    try:
        with pytest.raises(OSError, match="終了を確認できない"):
            with NoticeLease(backend, "timeout"):
                pytest.fail("thread死亡だけではprocess死亡とみなせない")
    finally:
        backend.close()
        old, lease = holders[0]
        old.owner_thread = threading.get_ident()
        lease.owns_mutex = False
        lease._dispose()
        old.close()


@pytest.mark.parametrize(
    "corrupt",
    [
        {"protocol": 0},
        {"pid": True},
        {"reason": "wrong"},
        {"hwnd": 0},
        {"deadline_tick": 11001},
        {"shown_tick": 501},
        {"extra": 1},
    ],
)
def test_notice_snapshot_corruption_never_authorizes_join(corrupt):
    import ctypes as ct
    import json
    import struct

    from pagefolio.startup_win32 import NoticeLease

    buffer = ct.create_string_buffer(4096)
    backend = SimpleNamespace(prefix="test", session_id=1, tick_ms=lambda: 500)
    lease = NoticeLease(backend, "timeout")
    lease.view = ct.addressof(buffer)
    snapshot = {
        "protocol": 1,
        "pid": 123,
        "process_created": 456,
        "session_id": 1,
        "generation": "a" * 32,
        "reason": "timeout",
        "state": "shown",
        "hwnd": 789,
        "shown_tick": 0,
        "deadline_tick": 10000,
        **corrupt,
    }
    raw = json.dumps(snapshot).encode()
    ct.memmove(lease.view, struct.pack("<QI", 2, len(raw)) + raw, 12 + len(raw))
    with pytest.raises(ValueError):
        lease._read_snapshot()


def test_eight_joiners_do_not_change_first_notice_deadline():
    from pagefolio.startup_notice import show_startup_failure

    backend = NoticeBackend(acquired=False)
    snapshot = {"hwnd": 123, "shown_tick": 0, "deadline_tick": 10000}

    @contextmanager
    def existing(reason):
        yield SimpleNamespace(acquired=False, snapshot=snapshot)

    backend._create_notice_lease = existing
    for _ in range(8):
        assert (
            show_startup_failure(StartupOutcome("expired"), backend).result
            == "coalesced"
        )
    assert snapshot == {"hwnd": 123, "shown_tick": 0, "deadline_tick": 10000}
    assert not backend.calls


def test_owner_cannot_extend_already_shown_deadline():
    from pagefolio.startup_win32 import NoticeLease

    lease = NoticeLease(SimpleNamespace(prefix="test"), "timeout")
    lease.snapshot = {
        "state": "shown",
        "hwnd": 123,
        "shown_tick": 0,
        "deadline_tick": 10000,
    }
    lease.mark_shown(123, 0, 10000)
    with pytest.raises(ValueError, match="更新できない"):
        lease.mark_shown(123, 9999, 19999)
    assert lease.snapshot["deadline_tick"] == 10000
