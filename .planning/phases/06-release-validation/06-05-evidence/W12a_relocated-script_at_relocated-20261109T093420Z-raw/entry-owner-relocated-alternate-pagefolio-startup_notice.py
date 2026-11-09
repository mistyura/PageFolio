"""編集画面にも設定 I/O にも依存しない、確認済み起動失敗の案内。"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from pagefolio.lang import LANG

NOTICE_LIFETIME_MS = 10000


class StartupFailureReason(StrEnum):
    CHECK_FAILED = "check_failed"
    CONTACT_FAILED = "contact_failed"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class NoticeOutcome:
    result: str
    reason: StartupFailureReason | None = None
    os_error: int = 0


def _failure_reason(outcome, verified_owner):
    if outcome.result in {"primary", "completed", "foreground_denied"}:
        return None
    if outcome.result == "expired":
        return StartupFailureReason.TIMEOUT
    if outcome.result == "connection_failed" and verified_owner:
        return StartupFailureReason.CONTACT_FAILED
    return StartupFailureReason.CHECK_FAILED


def _notice_language(language_id):
    # GetUserDefaultUILanguage の primary language が日本語の場合のみ ja。
    return "ja" if language_id & 0x3FF == 0x11 else "en"


def _notice_text(reason, language):
    keys = {
        StartupFailureReason.CHECK_FAILED: "startup_notice_check_failed",
        StartupFailureReason.CONTACT_FAILED: "startup_notice_contact_failed",
        StartupFailureReason.TIMEOUT: "startup_notice_timeout",
    }
    text = LANG[language]
    return (
        text["startup_notice_title"],
        text[keys[reason]],
        text["startup_notice_close"],
    )


def notice_deadline_tick(shown_tick, lifetime_ms=NOTICE_LIFETIME_MS):
    return shown_tick + lifetime_ms


def notice_remaining_ms(deadline_tick, now):
    return max(0, deadline_tick - now)


def _record_notification_unavailable(reason, error, logger=None):
    os_error = getattr(error, "winerror", None) or getattr(error, "errno", None) or 0
    if type(os_error) is not int or os_error < 0:
        os_error = 0
    try:
        (logger or logging.getLogger(__name__)).warning(
            "notification_unavailable reason=%s os_error=%s", reason, os_error
        )
    except Exception as e:
        # 診断障害で元の通知失敗を境界外へ漏らさない。
        _ = e
        return NoticeOutcome("notification_unavailable", reason, os_error)
    return NoticeOutcome("notification_unavailable", reason, os_error)


def show_startup_initialization_failure(*, backend_factory=None):
    """起動backendが未完成の時、別の通知専用backendを一度だけ作る。"""
    from pagefolio.startup_control import StartupOutcome

    if backend_factory is None:
        from pagefolio.startup_win32 import Win32NoticeBackend

        backend_factory = Win32NoticeBackend
    backend = None
    reason = StartupFailureReason.CHECK_FAILED
    try:
        backend = backend_factory()
        result = show_startup_failure(StartupOutcome(reason), backend)
    except Exception as e:
        result = _record_notification_unavailable(reason, e)
    finally:
        if backend is not None:
            try:
                backend.close()
            except Exception as e:
                result = _record_notification_unavailable(
                    reason, e, getattr(backend, "logger", None)
                )
    return result


def show_startup_failure(outcome, backend):
    reason = _failure_reason(outcome, bool(getattr(backend, "observed_owner", None)))
    if reason is None:
        return NoticeOutcome("not_required")
    try:
        with backend._create_notice_lease(reason) as lease:
            if not lease.acquired:
                return NoticeOutcome("coalesced", reason)
            text = _notice_text(reason, _notice_language(backend.notice_language()))
            backend.display_notice(reason, text, lease)
        return NoticeOutcome("shown", reason)
    except Exception as e:
        return _record_notification_unavailable(
            reason, e, getattr(backend, "logger", None)
        )
