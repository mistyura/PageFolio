"""起動前案内の事実分類・有限期限・非活性境界の回帰試験。"""

import logging
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
