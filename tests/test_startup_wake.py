"""UI 見張りの投稿境界・寿命と、実 Tcl の待機停止からの回復を検証する。"""

import json
import logging
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from pagefolio.startup_wake import UiThreadWake
from tests.startup_wake_child import WakeApiBoundary


def _assert_wake_noninterference(data):
    """デスクトップの前景値に依存せず、見張りの副作用の境界を検査する。"""
    assert data["boundary_violations"] == [], data
    assert all(name == "PostThreadMessageW" for name in data["wake_api_requests"]), data
    assert all(name == "get_last_error" for name in data["wake_ctypes_requests"]), data
    assert data["posted"] == len(data["posts"]), data
    assert all(
        item["args"] == [data["creator_tid"], 0, 0, 0]
        and item["caller_tid"] != data["creator_tid"]
        for item in data["posts"]
    ), data


@pytest.mark.parametrize("foreground_unchanged", [False, True])
def test_noninterference_accepts_only_allowed_effects_independently_of_foreground(
    foreground_unchanged,
):
    _assert_wake_noninterference(
        {
            "foreground_unchanged": foreground_unchanged,
            "boundary_violations": [],
            "wake_api_requests": ["PostThreadMessageW"],
            "wake_ctypes_requests": [],
            "posted": 1,
            "creator_tid": 10,
            "posts": [{"args": [10, 0, 0, 0], "caller_tid": 20}],
        }
    )


@pytest.mark.parametrize(
    "violation",
    ["foreground-api", "ctypes-bypass", "other-thread", "other-message", "owner-call"],
)
def test_noninterference_rejects_forbidden_effects_even_if_foreground_is_unchanged(
    violation,
):
    data = {
        "foreground_unchanged": True,
        "boundary_violations": [],
        "wake_api_requests": ["PostThreadMessageW"],
        "wake_ctypes_requests": [],
        "posted": 1,
        "creator_tid": 10,
        "posts": [{"args": [10, 0, 0, 0], "caller_tid": 20}],
    }
    if violation == "foreground-api":
        data["wake_api_requests"].append("SetForegroundWindow")
    elif violation == "ctypes-bypass":
        data["wake_ctypes_requests"].append("WinDLL")
    elif violation == "other-thread":
        data["posts"][0]["args"][0] = 99
    elif violation == "other-message":
        data["posts"][0]["args"][1] = 0x100
    else:
        data["posts"][0]["caller_tid"] = 10
    with pytest.raises(AssertionError):
        _assert_wake_noninterference(data)


@pytest.mark.parametrize("api_name", ["SetForegroundWindow", "SendInput", "WinDLL"])
def test_api_boundary_records_forbidden_access_even_if_exception_is_caught(api_name):
    requests, violations = [], []
    api = WakeApiBoundary({}, requests, violations)
    with pytest.raises(RuntimeError, match="許可されていないAPI"):
        getattr(api, api_name)
    assert requests == violations == [api_name]


def test_posts_only_wm_null_to_creator_and_stops_before_close_returns():
    posts = []
    posted = threading.Event()
    owner = threading.get_native_id()

    def post(*args):
        posts.append((args, threading.get_native_id()))
        posted.set()
        return True

    wake = UiThreadWake(
        SimpleNamespace(PostThreadMessageW=post), logging.getLogger(__name__)
    )
    try:
        wake.start()
        worker = wake._worker
        wake.start()
        assert wake._worker is worker
        assert posted.wait(2)
    finally:
        wake.close()
    assert not worker.is_alive()
    assert posts
    assert all(args == (owner, 0, 0, 0) and tid != owner for args, tid in posts)
    wake.close()
    with pytest.raises(RuntimeError, match="再開"):
        wake.start()


def test_close_without_start_and_worker_start_failure(monkeypatch):
    wake = UiThreadWake(SimpleNamespace(), logging.getLogger(__name__))

    def fail_start(self):
        raise RuntimeError("thread-start-failed")

    monkeypatch.setattr(threading.Thread, "start", fail_start)
    with pytest.raises(RuntimeError, match="thread-start-failed"):
        wake.start()
    wake.close()
    wake.close()


def test_wrong_thread_cannot_start_wake():
    wake = UiThreadWake(SimpleNamespace(), logging.getLogger(__name__))
    errors = []

    def start():
        try:
            wake.start()
        except RuntimeError as e:
            errors.append(str(e))

    worker = threading.Thread(target=start)
    worker.start()
    worker.join(2)
    wake.close()
    assert errors == ["UI スレッド以外から見張りを開始できません"]
    assert wake._worker is None


def test_post_failure_retries_at_120ms_and_logs_once_per_failure_streak():
    results = iter([False, False, OSError("injected"), True, False])
    warnings = []
    intervals = []

    def post(*args):
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result

    def wait(interval):
        intervals.append(interval)
        return len(intervals) > 5

    wake = UiThreadWake(
        SimpleNamespace(PostThreadMessageW=post),
        SimpleNamespace(warning=lambda *args: warnings.append(args)),
    )
    wake._stop = SimpleNamespace(wait=wait)
    wake._run()
    assert intervals == [0.120] * 6
    assert len(warnings) == 2


def test_owner_exit_prevents_posting():
    wake = UiThreadWake(SimpleNamespace(), logging.getLogger(__name__))
    wake._stop = SimpleNamespace(wait=lambda interval: False)
    wake._owner = SimpleNamespace(is_alive=lambda: False)
    wake._run()  # API の無い偽物でも、投稿せず終了する。


@pytest.mark.parametrize("failure", [None, "root", "app", "mainloop", "wake"])
def test_entry_stops_wake_before_root_destruction(monkeypatch, failure):
    import tkinter

    from tkinterdnd2 import TkinterDnD

    from pagefolio import __main__ as entry
    from pagefolio import (
        app,
        file_drop,
        startup_control,
        startup_focus,
        startup_wake,
        startup_win32,
    )

    events = []

    def record(name):
        events.append(name)
        if failure == name:
            raise RuntimeError(name)

    class Root:
        def __init__(self):
            record("root")

        def after_idle(self, callback):
            events.append("idle")

        def mainloop(self):
            record("mainloop")

        def winfo_exists(self):
            return True

        def destroy(self):
            events.append("destroy")

    class Wake:
        def __init__(self, api, logger):
            events.append("wake-create")

        def start(self):
            record("wake")

        def close(self):
            events.append("wake-close")

    def make_app(root):
        record("app")
        return SimpleNamespace()

    backend = SimpleNamespace(api=object(), logger=logging.getLogger(__name__))
    coordinator = SimpleNamespace(
        backend=backend,
        claim=lambda: SimpleNamespace(primary=True),
        close=lambda: events.append("coordinator-close"),
    )
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(startup_win32, "_tick_ms", lambda: 1)
    monkeypatch.setattr(startup_control, "StartupCoordinator", lambda b: coordinator)
    monkeypatch.setattr(tkinter, "Tk", Root)
    monkeypatch.setattr(TkinterDnD, "Tk", Root)
    monkeypatch.setattr(app, "PDFEditorApp", make_app)
    monkeypatch.setattr(file_drop, "_setup_file_drop", lambda app: None)
    monkeypatch.setattr(startup_wake, "UiThreadWake", Wake)
    monkeypatch.setattr(
        startup_focus,
        "FocusRestorer",
        lambda app, backend: SimpleNamespace(
            close=lambda: events.append("focus-close")
        ),
    )
    if failure:
        with pytest.raises(RuntimeError, match=failure):
            entry.main(backend_factory=lambda: backend)
    else:
        assert entry.main(backend_factory=lambda: backend) == "primary"
    assert events[-2:] == ["destroy", "coordinator-close"]
    if failure == "root":
        assert "wake-create" not in events
    else:
        assert events.index("root") < events.index("wake")
        assert events.index("wake-close") < events.index("destroy")
        if "app" in events:
            assert events.index("wake") < events.index("app")
        if "focus-close" in events:
            assert events.index("wake-close") < events.index("focus-close")


@pytest.mark.skipif(sys.platform != "win32", reason="実 Windows/Tcl を使う回帰試験")
@pytest.mark.parametrize(
    "enabled, external_change", [(False, False), (True, False), (True, True)]
)
def test_native_tcl_getmessage_stall_recovers_with_product_wake(
    enabled, external_change, tmp_path
):
    helper = Path(__file__).with_name("startup_wake_child.py")
    command = [sys.executable, str(helper), "wake" if enabled else "control"]
    if external_change:
        command.append("--simulate-external-foreground")
    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=helper.parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except subprocess.TimeoutExpired as error:

        def decoded(value):
            return (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value
            )

        (tmp_path / "startup-wake-timeout.json").write_text(
            json.dumps(
                {
                    "command": command,
                    "timeout": error.timeout,
                    "stdout": decoded(error.stdout),
                    "stderr": decoded(error.stderr),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise
    # assertより先に全出力を保存する。失敗しても子JSONと診断情報を失わない。
    (tmp_path / "startup-wake-child.json").write_text(
        json.dumps(
            {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["removed"] == 1, result.stdout + result.stderr
    assert data["posted"] > 0 if enabled else data["posted"] == 0
    # 前景前後一致は外部操作に依存する診断値。非干渉は別の厳格な境界で保証する。
    _assert_wake_noninterference(data)
    assert data["foreground_observation_source"] == (
        "simulated" if external_change else "native"
    )
    if external_change:
        assert not data["foreground_unchanged"], data
    assert data["worker_stopped"]
    if enabled:
        assert data["first_beat_after_ghost_ms"] < 400, data
    else:
        assert data["first_beat_after_ghost_ms"] > 600, data
