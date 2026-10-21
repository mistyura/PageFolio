"""Windows 起動制御の実プロセス tracer（UAC・操作待ちは通常収集しない）。"""

import ctypes as ct
import hashlib
import importlib.util
import json
import logging
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes as wt
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows API を実測する試験")
def test_tracer_abi_backend_available():
    assert importlib.util.find_spec("pagefolio.startup_win32") is not None


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows 実測")
_ROOT = Path(__file__).resolve().parents[1]
_ORIGINALS = (
    "pagefolio_settings.json",
    "ocr_custom_prompt.md",
    "ocr_summary_prompt.md",
)


def _fingerprints():
    return {
        name: hashlib.sha256((_ROOT / name).read_bytes()).hexdigest()
        if (_ROOT / name).exists()
        else None
        for name in _ORIGINALS
    }


@pytest.fixture(autouse=True)
def _unchanged_originals():
    before = _fingerprints()
    yield
    assert _fingerprints() == before


def _spawn(tmp_path, namespace, role):
    fixture = tmp_path / role
    fixture.mkdir()
    (fixture / "plugins").mkdir()
    (fixture / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    for name in _ORIGINALS[1:]:
        (fixture / name).write_text("isolated test prompt", encoding="utf-8")
    # コマンドは既知のPythonとこのファイルに固定。fixture/roleは試験自身が生成する。
    return subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "_test_scenario_bootstrap",
            str(fixture),
            namespace,
            role,
        ],
        cwd=_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW,
    ), fixture


def _finish(child):
    try:
        out, err = child.communicate(timeout=12)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()
        pytest.fail("子process が12秒以内に終了しない")
    assert child.returncode == 0, err
    return json.loads(out.strip().splitlines()[-1])


def _wait_file(child, path):
    deadline = time.monotonic() + 8
    while not path.exists() and time.monotonic() < deadline:
        if child.poll() is not None:
            _finish(child)
            pytest.fail("ownerがready前に終了")
        time.sleep(0.02)
    assert path.exists(), "owner readyを8秒以内に確認できない"


def test_tracer_abi_64bit_snapshot_and_thread(tmp_path):
    from pagefolio.startup_win32 import Win32Backend

    backend = Win32Backend(uuid4().hex)
    errors = []
    try:
        assert ct.sizeof(wt.HANDLE) == 8
        assert backend.claim(uuid4().hex) == "acquired"
        snapshot = backend._read_owner()
        assert snapshot["pid"] == os.getpid()
        assert snapshot["process_created"] > 2**32
        assert snapshot["session_id"] == backend.session_id
        with pytest.raises(PermissionError):
            backend._validate_peer(os.getpid(), snapshot["process_created"] + 1)

        def wrong_thread():
            try:
                backend.close()
            except RuntimeError as e:
                errors.append(str(e))

        worker = threading.Thread(target=wrong_thread)
        worker.start()
        worker.join(1)
        assert errors
        ct.c_ulonglong.from_address(backend.view).value = 3
        with pytest.raises(ValueError, match="公開途中"):
            backend._read_owner()
    finally:
        backend.close()


def test_tracer_io_lifetime_pending_connect_cancel():
    from pagefolio.startup_win32 import OwnedHandle, PendingIO, Win32Backend

    backend = Win32Backend(uuid4().hex)
    pipe = OwnedHandle(
        backend.api,
        backend.api.CreateNamedPipeW(
            backend._pipe_name(uuid4().hex),
            3 | 0x40000000 | 0x80000,
            8,
            8,
            2048,
            2048,
            0,
            ct.byref(backend.pipe_security.attributes),
        ),
    )
    try:
        pending = PendingIO(backend.api, pipe)
        assert not backend.api.ConnectNamedPipe(
            pipe.value, ct.byref(pending.overlapped)
        )
        started = backend.tick_ms()
        with pytest.raises(TimeoutError):
            pending.finish(started + 80)
        assert pending.completed
        assert pending.event.value is None
        assert backend.tick_ms() - started < 650
    finally:
        pipe.close()
        backend.close()


def test_tracer_e2e_real_main_terminal_ack(tmp_path):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, "owner")
    try:
        _wait_file(owner, fixture / "ready")
        children = [
            _spawn(tmp_path, namespace, role)[0]
            for role in ("secondary-a", "secondary-b")
        ]
        for child in children:
            result = _finish(child)
            assert result["constructed"] == 0
            assert result["result"] in {"completed", "foreground_denied"}
            assert result["elapsed"] < 5500
        (fixture / "stop").touch()
        result = _finish(owner)
        assert result["constructed"] == 1
        assert result["restored"] == 1
        assert result["status_preserved"]
    finally:
        if owner.poll() is None:
            owner.kill()
            _, errors = owner.communicate()
            if errors:
                print("owner診断:", errors)


def test_tracer_io_lifetime_unresponsive_peer_five_second_deadline(tmp_path):
    namespace = uuid4().hex
    peer, fixture = _spawn(tmp_path, namespace, "stall")
    try:
        _wait_file(peer, fixture / "ready")
        child, _ = _spawn(tmp_path, namespace, "request-timeout")
        result = _finish(child)
        assert result["result"] == "expired"
        assert 4900 <= result["elapsed"] <= 5550
        (fixture / "stop").touch()
        _finish(peer)
    finally:
        if peer.poll() is None:
            peer.kill()
            peer.communicate()


def test_tracer_e2e_initialization_failure_releases_owner(tmp_path):
    namespace = uuid4().hex
    failed, _ = _spawn(tmp_path, namespace, "init-failure")
    assert _finish(failed)["result"] == "initialization_failed"
    owner, fixture = _spawn(tmp_path, namespace, "owner")
    try:
        _wait_file(owner, fixture / "ready")
        (fixture / "stop").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.communicate()


def test_tracer_e2e_api_denial_does_not_construct_app(tmp_path):
    child, _ = _spawn(tmp_path, uuid4().hex, "api-denied")
    result = _finish(child)
    assert result["result"] == "api_denied"
    assert result["constructed"] == 0


def test_tracer_notice_real_main_failure_path(tmp_path):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, "stall")
    try:
        _wait_file(owner, fixture / "ready")
        child, _ = _spawn(tmp_path, namespace, "notice-via-main")
        result = _finish(child)
        assert result["result"] == "connection_failed"
        assert result["constructed"] == 0
        assert 9900 <= result["elapsed"] <= 11500
        (fixture / "stop").touch()
        _finish(owner)
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.communicate()


def test_tracer_abi_shared_tick_wall_clock_independent(tmp_path, monkeypatch):
    from pagefolio.startup_win32 import _tick_ms

    before = _tick_ms()
    child, _ = _spawn(tmp_path, uuid4().hex, "tick")
    child_tick = _finish(child)["tick"]
    monkeypatch.setattr(time, "time", lambda: -(10**12))
    after = _tick_ms()
    assert before <= child_tick <= after


def test_tracer_io_lifetime_quarantine_keeps_native_buffers(monkeypatch):
    import gc

    from pagefolio import startup_win32 as win

    backend = win.Win32Backend(uuid4().hex)
    pipe = win.OwnedHandle(
        backend.api,
        backend.api.CreateNamedPipeW(
            backend._pipe_name(uuid4().hex),
            3 | 0x40000000 | 0x80000,
            8,
            8,
            2048,
            2048,
            0,
            ct.byref(backend.pipe_security.attributes),
        ),
    )
    pending = win.PendingIO(backend.api, pipe, ct.create_string_buffer(1024))
    original = backend.api.GetOverlappedResult
    try:
        backend.api.ConnectNamedPipe(pipe.value, ct.byref(pending.overlapped))

        def incomplete(*args):
            ct.set_last_error(win.ERROR_IO_INCOMPLETE)
            return False

        monkeypatch.setattr(backend.api, "GetOverlappedResult", incomplete)
        pending.cancel()
        assert pending in win._pending_io_quarantine
        pipe.close()
        gc.collect()
        assert pipe.value is not None
        assert pending.event.value is not None
        assert len(pending.buffer) == 1024
    finally:
        backend.api.GetOverlappedResult = original
        deadline = time.monotonic() + 2
        while pending in win._pending_io_quarantine and time.monotonic() < deadline:
            time.sleep(0.01)
        backend.close()
    assert pending not in win._pending_io_quarantine
    assert pipe.value is None


@pytest.mark.parametrize("manual_close", [False, True])
def test_tracer_notice_nonactivate_lifetime_and_close(manual_close):
    from pagefolio.startup_win32 import NativeNoticeLifetime, Win32Backend, _bind

    backend = Win32Backend(uuid4().hex)
    foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
    post = _bind(
        backend.api.u, "PostMessageW", wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
    )
    before = foreground()
    seen = []
    started = backend.tick_ms()

    def observe(hwnd):
        seen.append((hwnd, foreground()))
        if manual_close:
            assert post(hwnd, 0x111, 101, 0)

    try:
        notice = NativeNoticeLifetime(backend, "connection_failed")
        notice.show(lifetime_ms=150, on_show=observe)
        assert seen and seen[0][1] == before
        assert foreground() == before
        assert notice.hwnd is None
        assert backend.tick_ms() - started < 1000
        assert notice.callback is not None
    finally:
        backend.close()


def test_tracer_notice_ten_second_production_timer():
    from pagefolio.startup_win32 import NativeNoticeLifetime, Win32Backend

    backend = Win32Backend(uuid4().hex)
    try:
        started = backend.tick_ms()
        NativeNoticeLifetime(backend, "connection_failed").show()
        elapsed = backend.tick_ms() - started
        assert 9900 <= elapsed <= 11500
    finally:
        backend.close()


def test_tracer_notice_lease_process_dedup(tmp_path):
    namespace = uuid4().hex
    holder, fixture = _spawn(tmp_path, namespace, "lease-owner")
    try:
        _wait_file(holder, fixture / "ready")
        child, _ = _spawn(tmp_path, namespace, "lease-secondary")
        assert _finish(child)["acquired"] is False
        (fixture / "stop").touch()
        assert _finish(holder)["acquired"] is True
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.communicate()


def _run_scenario(fixture, namespace, role):
    """各spawnで初回app import前に設定/プロンプト/pluginsを隔離する。"""
    sys.path.insert(0, str(_ROOT))
    from pagefolio import plugins, settings

    settings._get_base_dir = lambda: str(fixture)
    plugins._get_plugins_dir = lambda: str(fixture / "plugins")
    from pagefolio.startup_win32 import Win32Backend, _tick_ms

    backend_namespace = None if namespace == "fixed-production" else namespace
    if role.startswith("lease-"):
        from pagefolio.startup_win32 import NoticeLease

        backend = Win32Backend(backend_namespace)
        try:
            with NoticeLease(backend, "connection_failed") as lease:
                if role == "lease-owner":
                    assert lease.acquired
                    (fixture / "ready").touch()
                    deadline = time.monotonic() + 8
                    while (
                        not (fixture / "stop").exists() and time.monotonic() < deadline
                    ):
                        time.sleep(0.02)
                print(json.dumps({"acquired": lease.acquired}))
        finally:
            backend.close()
        return
    if role in {"notice-manual", "notice-timer", "preflight"}:
        from pagefolio.startup_win32 import (
            NativeNoticeLifetime,
            NoticeLease,
            _bind,
        )

        backend = Win32Backend(backend_namespace)
        try:
            if role == "preflight":
                outcome = backend.claim(uuid4().hex)
                assert outcome == "acquired", "無関係なownerの可能性があるため中断"
                print(json.dumps({"result": "no_existing_owner"}))
                return
            foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
            before = foreground()
            start = backend.tick_ms()
            audit = {"foreground_before": before, "started_tick": start}

            def visible(hwnd):
                audit.update(
                    hwnd=hwnd,
                    shown_tick=backend.tick_ms(),
                    foreground_shown=foreground(),
                )
                (fixture / "ready").write_text(json.dumps(audit), encoding="utf-8")

            with NoticeLease(backend, "connection_failed") as lease:
                audit["lease_acquired"] = lease.acquired
                if lease.acquired:
                    NativeNoticeLifetime(backend, "connection_failed").show(
                        on_show=visible
                    )
            audit.update(closed_tick=backend.tick_ms(), foreground_after=foreground())
            (fixture / "result.json").write_text(json.dumps(audit), encoding="utf-8")
            print(json.dumps(audit))
        finally:
            backend.close()
        return

    if role == "tick":
        print(json.dumps({"tick": _tick_ms()}))
        return
    if role == "stall":
        backend = Win32Backend(backend_namespace)
        try:
            assert backend.claim(uuid4().hex) == "acquired"

            def stall(raw):
                time.sleep(5.5)
                return {"request_id": raw["request_id"], "result": "completed"}

            backend.listen(stall)
            backend.publish_state("ready", True)
            (fixture / "ready").touch()
            deadline = time.monotonic() + 9
            while not (fixture / "stop").exists() and time.monotonic() < deadline:
                time.sleep(0.02)
        finally:
            backend.close()
        print(json.dumps({"result": "stopped"}))
        return
    # 重いapp importの前に全パスが隔離されたことを各子で検査する。
    assert Path(settings._get_settings_path()).parent == fixture
    assert Path(plugins._get_plugins_dir()).parent == fixture
    from pagefolio.__main__ import main

    counts = {"constructed": 0, "restored": 0, "status_preserved": True}
    app_reference = []
    if role in {"owner", "manual-owner", "init-failure"}:
        from pagefolio import app as app_module

        class TracedApp(app_module.PDFEditorApp):
            def __init__(self, root):
                counts["constructed"] += 1
                if role == "init-failure":
                    raise RuntimeError("tracer-initialization-failure")
                super().__init__(root)
                app_reference.append(self)

                def stop_poll():
                    if (fixture / "stop").exists():
                        self._quit()
                    else:
                        root.after(50, stop_poll)

                root.after(50, stop_poll)
                root.after(120000 if role == "manual-owner" else 10000, self._quit)

        app_module.PDFEditorApp = TracedApp

    class Backend(Win32Backend):
        def __init__(self):
            super().__init__(backend_namespace)
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.StreamHandler(sys.stderr))
            self.audit = {
                "sid": self.sid,
                "authentication_luid": self.authentication_luid,
                "session_id": self.session_id,
                "pid": self.pid,
            }
            self.notice_lease = None
            if role == "api-denied":

                def deny(*args):
                    ct.set_last_error(5)
                    return None

                self.api.CreateMutexExW = deny
            if role == "notice-via-main":

                def deny_pipe(*args):
                    ct.set_last_error(5)
                    return ct.c_void_p(-1).value

                self.api.CreateFileW = deny_pipe

        def request_activation(self, started_tick):
            result = super().request_activation(started_tick)
            self.audit["terminal_result"] = result
            self.audit["elapsed"] = self.tick_ms() - started_tick
            return result

        def claim(self, generation):
            from pagefolio.startup_win32 import NoticeLease

            result = super().claim(generation)
            self.audit["owner_result"] = result
            if role.startswith("manual-"):
                if result == "acquired":
                    self.notice_lease = NoticeLease(self, "A4-resource-check")
                    self.notice_lease.__enter__()
                    self.audit["notice_acquired"] = self.notice_lease.acquired
                else:
                    with NoticeLease(self, "A4-resource-check") as lease:
                        self.audit["notice_acquired"] = lease.acquired
                self.audit["snapshot"] = self._read_owner()
            return result

        def close(self):
            if self.notice_lease is not None:
                self.notice_lease.__exit__(None, None, None)
                self.notice_lease = None
            (fixture / "resource-audit.json").write_text(
                json.dumps(self.audit), encoding="utf-8"
            )
            super().close()

        def publish_state(self, state, ready):
            super().publish_state(state, ready)
            if ready:
                (fixture / "ready").write_text(json.dumps(self.audit), encoding="utf-8")

        def restore_window(self, hwnd, is_current=lambda: True):
            counts["restored"] += 1
            app = app_reference[0]
            status = app.status_var.get()
            result = super().restore_window(hwnd, is_current=is_current)
            counts["status_preserved"] &= app.status_var.get() == status
            return result

        def show_notice(self, reason):
            if role == "notice-via-main":
                return super().show_notice(reason)
            if role == "request-timeout":
                assert reason == "expired"
                return
            raise AssertionError(f"正常tracerで失敗案内: {reason}")

    started = _tick_ms()
    try:
        result = main(backend_factory=Backend)
    except PermissionError:
        assert role == "api-denied"
        result = "api_denied"
    except RuntimeError as e:
        assert role == "init-failure" and str(e) == "tracer-initialization-failure"
        result = "initialization_failed"
    if role not in {"owner", "manual-owner", "init-failure"}:
        assert "pagefolio.app" not in sys.modules
    record = {**counts, "result": result, "elapsed": _tick_ms() - started}
    (fixture / "result.json").write_text(json.dumps(record), encoding="utf-8")
    print(json.dumps(record))


def _test_scenario_bootstrap(fixture, namespace, role):
    before = _fingerprints()
    try:
        _run_scenario(fixture, namespace, role)
    finally:
        assert _fingerprints() == before, "元設定/プロンプトが変更された"


if __name__ == "__main__":
    assert sys.argv[1] == "_test_scenario_bootstrap"
    _test_scenario_bootstrap(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
