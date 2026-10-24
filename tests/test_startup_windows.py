"""Windows 起動制御の実プロセス tracer（UAC・操作待ちは通常収集しない）。"""

import argparse
import ctypes as ct
import faulthandler
import hashlib
import importlib.util
import json
import logging
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import warnings
from contextlib import nullcontext
from ctypes import wintypes as wt
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows API を実測する試験")
def test_tracer_abi_backend_available():
    assert importlib.util.find_spec("pagefolio.startup_win32") is not None


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows 実測")
_ROOT = Path(__file__).resolve().parents[1]
# Python import・Tk初期化の試験待機。製品の二次起動期限（5秒）とは別。
_BOOTSTRAP_TIMEOUT = 30
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


def _spawn(
    tmp_path, namespace, role, *, fixture_name=None, expected_owner=None, detached=False
):
    fixture = tmp_path / (fixture_name or role)
    fixture.mkdir()
    (fixture / "plugins").mkdir()
    (fixture / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    for name in _ORIGINALS[1:]:
        (fixture / name).write_text("isolated test prompt", encoding="utf-8")
    if expected_owner:
        (fixture / "expected-owner.json").write_text(
            json.dumps(expected_owner), encoding="utf-8"
        )
    if role in {"entry-relocated", "entry-owner-relocated"}:
        shutil.copytree(
            _ROOT / "pagefolio",
            fixture / "alternate" / "pagefolio",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copyfile(_ROOT / "pagefolio.py", fixture / "alternate" / "pagefolio.py")
    # コマンドは既知のPythonとこのファイルに固定。fixture/roleは試験自身が生成する。
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_test_scenario_bootstrap",
        str(fixture),
        namespace,
        role,
    ]
    if detached:
        with (
            (fixture / "stdout.log").open("w", encoding="utf-8") as out,
            (fixture / "stderr.log").open("w", encoding="utf-8") as err,
        ):
            child = subprocess.Popen(  # noqa: S603
                command,
                cwd=_ROOT,
                stdout=out,
                stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        return child, fixture
    return _pipe_popen(command), fixture


def _pipe_popen(command):
    child = subprocess.Popen(  # noqa: S603
        command,
        cwd=_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    # _stall_reportが「起動後に生まれた生存process」を探す基準時刻。
    child.pf_spawned_at = datetime.now()
    return child


# 子processの完了（終了とstdout/stderrのEOF）を待つ試験用の期限。
_FINISH_TIMEOUT = 12
# 期限超過でkillした後にpipeが閉じるのを待つ追加の期限。
# 保持者が残っても無期限には待たない。
_DRAIN_TIMEOUT = 5


def _stall_report(child):
    """期限超過時、「process自体が生存」と「終了済みだがpipeを保持する者がいる」を
    見分けるための証拠を集める。診断の失敗で本来の失敗を隠さない。"""
    lines = [f"poll={child.poll()}"]
    for name in ("stdout_thread", "stderr_thread"):
        reader = getattr(child, name, None)
        if reader is None:
            continue
        frame = sys._current_frames().get(reader.ident)
        where = (
            f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}" if frame else "-"
        )
        lines.append(f"{name}: alive={reader.is_alive()} at {where}")
    spawned = getattr(child, "pf_spawned_at", None)
    if spawned is not None:
        # 孫は親(launcher/Python)が死ぬと親pidで辿れない。起動後に生まれ今も生きている
        # processを、threadの状態別件数とともに列挙する（無関係なprocessも含みうる）。
        since = (spawned - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        script = (
            f"$since=[datetime]'{since}'; "
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CreationDate -ge $since } | ForEach-Object { "
            "$t = try { (Get-Process -Id $_.ProcessId -ErrorAction Stop).Threads | "
            'Group-Object { "$($_.ThreadState)/$($_.WaitReason)" } | '
            'ForEach-Object { "$($_.Name)=$($_.Count)" } } catch { "gone" }; '
            '"pid=$($_.ProcessId) ppid=$($_.ParentProcessId) $($_.Name) '
            "created=$($_.CreationDate.ToString('HH:mm:ss.fff')) "
            "threads=[$($t -join ',')]\" }"
        )
        try:
            shown = subprocess.run(  # noqa: S603
                ["powershell", "-NoProfile", "-Command", script],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=30,
            )
            lines.append("起動後に生まれた生存process:\n" + shown.stdout.strip())
        except Exception as e:
            lines.append(f"process一覧の取得に失敗: {e!r}")
    return "\n".join(lines)


def _finish(child, timeout=_FINISH_TIMEOUT):
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # killより前に証拠を採る。killすると生存/保持の区別が消える。
        exited = child.poll() is not None
        report = _stall_report(child)
        child.kill()
        try:
            out, err = child.communicate(timeout=_DRAIN_TIMEOUT)
        except subprocess.TimeoutExpired:
            out = err = "<kill後もpipeを保持する者が残りEOF未到達>"
        cause = (
            "processは終了済みだが、stdout/stderrを保持する者がいてEOFが来ない"
            if exited
            else "process自体が終了しない"
        )
        pytest.fail(
            f"子processが{timeout}秒以内に完了しない: {cause}\n{report}\n"
            f"stdout={out}\nstderr={err}"
        )
    assert child.returncode == 0, err
    return json.loads(out.strip().splitlines()[-1])


def _wait_file(child, path):
    deadline = time.monotonic() + _BOOTSTRAP_TIMEOUT
    while not path.exists() and time.monotonic() < deadline:
        if child.poll() is not None:
            _finish(child)
            pytest.fail("ownerがready前に終了")
        time.sleep(0.02)
    assert path.exists(), f"{path.name}を{_BOOTSTRAP_TIMEOUT}秒以内に確認できない"


# 孫が継承したstdout/stderrを保持したまま、子本体は結果を出力して終了する。
_PIPE_HOLDER = """
import json, subprocess, sys
g = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(60)"],
    close_fds=False,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
open(sys.argv[1], "w").write(str(g.pid))
print(json.dumps({"result": "completed"}), flush=True)
"""


def test_finish_reports_exited_process_whose_pipes_are_held(tmp_path, monkeypatch):
    """子は結果を出して終了済みでも、孫がpipeを保持するとcommunicateはEOFを待つ。
    _finishはこれを「process生存」と誤認せず、保持者を報告し、無期限に待たない。"""
    monkeypatch.setitem(globals(), "_DRAIN_TIMEOUT", 1)  # 試験時間の短縮
    pid_file = tmp_path / "holder.pid"
    child = _pipe_popen([sys.executable, "-c", _PIPE_HOLDER, str(pid_file)])
    started = time.monotonic()
    try:
        with pytest.raises(pytest.fail.Exception) as info:
            _finish(child, timeout=3)
        elapsed = time.monotonic() - started
        message = str(info.value)
        holder = pid_file.read_text()
        assert "processは終了済み" in message, message
        assert "stdout_thread: alive=True" in message, message
        assert f"pid={holder} " in message, message  # 保持者のpidを特定できる
        # 孫の寿命(60秒)を待たず、期限+診断+kill後の追加期限の範囲で戻る。
        assert elapsed < 3 + _DRAIN_TIMEOUT + 30, elapsed
    finally:
        if pid_file.exists():
            subprocess.run(  # noqa: S603
                ["taskkill", "/F", "/T", "/PID", pid_file.read_text()],  # noqa: S607
                capture_output=True,
                check=False,
            )
        _reclaim([child])


def test_finish_reports_live_process_as_not_exiting():
    child = _pipe_popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        with pytest.raises(pytest.fail.Exception) as info:
            _finish(child, timeout=2)
        message = str(info.value)
        assert "process自体が終了しない" in message, message
        assert "poll=None" in message, message
    finally:
        _reclaim([child])


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
    # 起動mutexと通知mutexの両APIを拒否。成功や表示済みへ偽装しない。
    assert result["result"] == "notification_unavailable"
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
        assert 100 <= result["elapsed"] <= 2000
        (fixture / "stop").touch()
        _finish(owner)
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.communicate()


def test_constructor_failure_real_main_nonactivate_notice(tmp_path):
    child, _ = _spawn(tmp_path, uuid4().hex, "constructor-failure-main")
    result = _finish(child)
    assert result["result"] == "check_failed"
    assert result["constructed"] == 0
    assert result["notice_calls"] == 1
    assert result["reason"] == "check_failed"
    assert result["foreground_before"] == result["foreground_shown"]
    assert result["foreground_before_show"] == result["foreground_after_show"]
    assert result["foreground_before_close"] == result["foreground_after_close"]
    assert result["foreground_before"] == result["foreground_after"]
    assert result["snapshot"]["deadline_tick"] - result["snapshot"]["shown_tick"] == 150


def test_constructor_failure_descriptor_stage_reaches_native_notice(tmp_path):
    child, _ = _spawn(tmp_path, uuid4().hex, "constructor-failure-descriptor")
    result = _finish(child)
    assert result["result"] == "check_failed"
    assert result["notice_calls"] == 1
    assert result["constructed"] == 0


def test_constructor_failure_manual_close_keeps_foreground(tmp_path):
    child, _ = _spawn(tmp_path, uuid4().hex, "constructor-failure-manual")
    result = _finish(child)
    assert result["result"] == "check_failed"
    assert result["notice_calls"] == 1
    assert result["foreground_before_show"] == result["foreground_after_show"]
    assert result["foreground_before_close"] == result["foreground_after_close"]


def test_constructor_failure_entry_exit(tmp_path):
    for role, expected in (
        ("constructor-failure-module", "check_failed"),
        ("constructor-failure-script", "check_failed"),
        ("constructor-failure-unavailable-module", "notification_unavailable"),
        ("constructor-failure-unavailable-script", "notification_unavailable"),
    ):
        child, _ = _spawn(tmp_path, uuid4().hex, role)
        result = _finish(child)
        assert result["result"] == expected
        assert result["exit"] == (1 if "unavailable" in role else 0)
        assert result["constructed"] == 0


@pytest.mark.parametrize("legacy_owner", [False, True])
def test_constructor_failure_notice_dedup(tmp_path, legacy_owner):
    namespace = uuid4().hex
    owner_role = (
        "constructor-failure-legacy-owner"
        if legacy_owner
        else "constructor-failure-owner"
    )
    owner, fixture = _spawn(tmp_path, namespace, owner_role)
    children = [owner]
    try:
        _wait_file(owner, fixture / "ready")
        first = json.loads((fixture / "ready").read_text(encoding="utf-8"))
        for index in range(7):
            join_type = "legacy-join" if index % 2 else "join"
            child, _ = _spawn(
                tmp_path, namespace, f"constructor-failure-{join_type}-{index}"
            )
            children.append(child)
        joined = [_finish(child) for child in children[1:]]
        assert all(item["result"] == "check_failed" for item in joined)
        assert all(item["notice_calls"] == 0 for item in joined)
        assert all(
            item["snapshot"]["deadline_tick"] == first["snapshot"]["deadline_tick"]
            for item in joined
        )
        assert _finish(owner)["notice_calls"] == 1
    finally:
        _reclaim(children)


def test_constructor_failure_cleanup_allows_restart(tmp_path):
    namespace = uuid4().hex
    child, _ = _spawn(tmp_path, namespace, "constructor-failure-main")
    assert _finish(child)["result"] == "check_failed"
    child, _ = _spawn(tmp_path, namespace, "preflight")
    assert _finish(child)["result"] == "no_existing_owner"


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
            r = notice.close_rect
            assert post(hwnd, 0x202, 0, ((r.top + 1) << 16) | (r.left + 1))

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


def test_tracer_notice_timeout_injected_timer():
    from pagefolio.startup_win32 import NativeNoticeLifetime, Win32Backend

    backend = Win32Backend(uuid4().hex)
    try:
        started = backend.tick_ms()
        NativeNoticeLifetime(backend, "connection_failed").show(lifetime_ms=150)
        elapsed = backend.tick_ms() - started
        assert 140 <= elapsed <= 1000
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


class _ForegroundAudit:
    """試験スレッドのWinEvent監査。入力・前景・製品の期限は変更しない。"""

    def __init__(self, backend, path, *, event=3):
        from pagefolio.startup_win32 import _bind

        self.backend = backend
        self.event = event
        self.path = path
        self.errors = []
        self.hook = None
        self.stream = None
        self.foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
        self.window_thread = _bind(
            backend.api.u,
            "GetWindowThreadProcessId",
            wt.DWORD,
            wt.HWND,
            ct.POINTER(wt.DWORD),
        )
        self.window_class = _bind(
            backend.api.u, "GetClassNameW", ct.c_int, wt.HWND, wt.LPWSTR, ct.c_int
        )
        callback_type = ct.WINFUNCTYPE(
            None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD
        )
        self.callback = callback_type(self._receive)
        self.install = _bind(
            backend.api.u,
            "SetWinEventHook",
            wt.HANDLE,
            wt.DWORD,
            wt.DWORD,
            wt.HMODULE,
            callback_type,
            wt.DWORD,
            wt.DWORD,
            wt.DWORD,
        )
        self.remove = _bind(backend.api.u, "UnhookWinEvent", wt.BOOL, wt.HANDLE)
        self.peek = _bind(
            backend.api.u,
            "PeekMessageW",
            wt.BOOL,
            ct.POINTER(wt.MSG),
            wt.HWND,
            wt.UINT,
            wt.UINT,
            wt.UINT,
        )
        self.translate = _bind(
            backend.api.u, "TranslateMessage", wt.BOOL, ct.POINTER(wt.MSG)
        )
        self.dispatch = _bind(
            backend.api.u, "DispatchMessageW", ct.c_ssize_t, ct.POINTER(wt.MSG)
        )

    def mark(self, event, *, hwnd=None, **details):
        if hwnd is None:
            hwnd = self.foreground()
        pid = wt.DWORD()
        thread_id = self.window_thread(hwnd, ct.byref(pid)) if hwnd else 0
        name = ct.create_unicode_buffer(256)
        length = self.window_class(hwnd, name, len(name)) if hwnd else 0
        record = {
            "event": event,
            "tick": self.backend.tick_ms(),
            "monotonic": time.monotonic(),
            "hwnd": hwnd,
            "pid": pid.value,
            "window_thread_id": thread_id,
            "class_name": name.value if length else "",
            "identity_available": bool(thread_id and length),
            **details,
        }
        self.stream.write(json.dumps(record) + "\n")
        self.stream.flush()

    def _receive(self, hook, event, hwnd, object_id, child_id, thread_id, event_tick):
        try:
            self.mark(
                "winevent",
                hwnd=hwnd or 0,
                event_id=event,
                event_tick=event_tick,
                event_thread_id=thread_id,
                object_id=object_id,
                child_id=child_id,
            )
        except Exception as e:
            # ctypes境界へ例外を漏らさず、終了時に診断失敗を不合格にする。
            self.errors.append(type(e).__name__)

    def __enter__(self):
        self.backend._assert_thread()
        self.stream = self.path.open("x", encoding="utf-8")
        try:
            # OUTOFCONTEXT。自processも含め、現在のdesktopの対象eventだけを観測。
            self.hook = self.install(
                self.event, self.event, None, self.callback, 0, 0, 0
            )
            if not self.hook:
                raise ct.WinError(ct.get_last_error())
            self.mark("observer_started", event_id=self.event)
            return self
        except Exception as e:
            if self.hook:
                self.remove(self.hook)
            self.stream.close()
            raise e

    def __exit__(self, exc_type, exc, tb):
        self.backend._assert_thread()
        try:
            # show()のmessage loop終了直後に到着済みの通知を同じthreadで処理。
            message = wt.MSG()
            for _ in range(256):
                if not self.peek(ct.byref(message), None, 0, 0, 1):
                    break
                self.translate(ct.byref(message))
                self.dispatch(ct.byref(message))
            else:
                self.errors.append("drain_limit")
        finally:
            removed = bool(self.remove(self.hook))
            try:
                self.mark("observer_stopped", removed=removed, errors=self.errors)
            finally:
                self.stream.close()
        if exc_type is None:
            assert removed and not self.errors, "前景監査の解除/受信に失敗"


def test_foreground_audit_receives_native_window_event(tmp_path):
    """実window表示eventでhookの受信・所有者記録・解除を検証。前景強制なし。"""
    from pagefolio.startup_win32 import NativeNoticeLifetime, Win32Backend

    backend = Win32Backend(uuid4().hex)
    path = tmp_path / "foreground-audit.jsonl"
    shown = []
    try:
        # EVENT_OBJECT_SHOWで同じ受信経路を検証。前景不変の製品合否とは別試験。
        with _ForegroundAudit(backend, path, event=0x8002):
            notice = NativeNoticeLifetime(backend, "contact_failed")
            notice.show(lifetime_ms=150, on_show=shown.append)
        records = [json.loads(line) for line in path.read_text().splitlines()]
        received = [
            row
            for row in records
            if row["event"] == "winevent" and row["hwnd"] == shown[0]
        ]
        assert received, "実windowの表示eventを受信していない"
        assert all(row["pid"] == os.getpid() for row in received)
        assert all(row["identity_available"] and row["event_tick"] for row in received)
        assert records[-1]["removed"] and not records[-1]["errors"]
    finally:
        backend.close()


def test_notice_dedup_eight_processes_keep_original_deadline(tmp_path):
    namespace = uuid4().hex
    owner, path = _spawn(tmp_path, namespace, "notice-case-owner")
    children = [owner]
    try:
        _wait_file(owner, path / "ready")
        initial = json.loads((path / "ready").read_text())
        peers = [
            _spawn(tmp_path, namespace, f"notice-case-peer-{i}")[0] for i in range(8)
        ]
        children.extend(peers)
        results = [_finish(child) for child in peers]
        assert all(not result["acquired"] for result in results)
        assert all(result["snapshot"] == initial["snapshot"] for result in results)
        final = _finish(owner)
        assert final["foreground_before"] == final["foreground_after"]
        assert 1700 <= final["elapsed"] < 3000
        assert final["deadline_tick"] == initial["snapshot"]["deadline_tick"]
        records = [
            json.loads(line)
            for line in (path / "foreground-audit.jsonl").read_text().splitlines()
        ]
        assert records[0]["event"] == "observer_started"
        assert records[-1]["removed"] and not records[-1]["errors"]
        assert {"notice_show_call", "notice_published", "notice_returned"} <= {
            row["event"] for row in records
        }
    finally:
        _reclaim(children)


def test_notice_dedup_different_reasons_and_manual_close_allow_new_owner(tmp_path):
    namespace = uuid4().hex
    owner, path = _spawn(tmp_path, namespace, "notice-case-owner")
    children = [owner]
    try:
        _wait_file(owner, path / "ready")
        other, _ = _spawn(tmp_path, namespace, "notice-case-other-reason")
        children.append(other)
        assert _finish(other)["acquired"]
        audit = json.loads((path / "ready").read_text())
        from pagefolio.startup_win32 import Win32Backend, _bind

        backend = Win32Backend(namespace)
        try:
            post = _bind(
                backend.api.u,
                "PostMessageW",
                wt.BOOL,
                wt.HWND,
                wt.UINT,
                wt.WPARAM,
                wt.LPARAM,
            )
            assert post(audit["snapshot"]["hwnd"], 0x10, 0, 0)
        finally:
            backend.close()
        assert _finish(owner)["acquired"]
        renewed, _ = _spawn(tmp_path, namespace, "notice-case-renewed")
        children.append(renewed)
        assert _finish(renewed)["acquired"]
    finally:
        _reclaim(children)


def test_notice_dedup_owner_crash_with_retained_handles_can_redisplay(tmp_path):
    from pagefolio.startup_win32 import (
        READ_CONTROL,
        SYNCHRONIZE,
        NoticeLease,
        OwnedHandle,
        Win32Backend,
        _bind,
    )

    namespace = uuid4().hex
    owner, path = _spawn(tmp_path, namespace, "notice-case-owner")
    children = [owner]
    backend = Win32Backend(namespace)
    kept = []
    try:
        _wait_file(owner, path / "ready")
        lease = NoticeLease(backend, "contact_failed")
        open_mutex = _bind(
            backend.api.k, "OpenMutexW", wt.HANDLE, wt.DWORD, wt.BOOL, wt.LPCWSTR
        )
        kept.append(
            OwnedHandle(
                backend.api, open_mutex(SYNCHRONIZE | READ_CONTROL, False, lease.name)
            )
        )
        kept.append(
            OwnedHandle(
                backend.api,
                backend.api.OpenFileMappingW(READ_CONTROL | 4, False, lease.state_name),
            )
        )
        owner.kill()
        owner.communicate()
        renewed, _ = _spawn(tmp_path, namespace, "notice-case-renewed")
        children.append(renewed)
        assert _finish(renewed)["acquired"]
    finally:
        for handle in kept:
            handle.close()
        backend.close()
        _reclaim(children)


@pytest.mark.parametrize("existing", [True, False])
def test_notice_dedup_access_denial_checks_same_name_once(
    tmp_path, monkeypatch, existing
):
    from pagefolio import startup_win32 as win
    from pagefolio.startup_control import StartupOutcome
    from pagefolio.startup_notice import show_startup_failure

    namespace = uuid4().hex
    children = []
    if existing:
        owner, path = _spawn(tmp_path, namespace, "notice-case-owner")
        children.append(owner)
        _wait_file(owner, path / "ready")
    backend = win.Win32Backend(namespace)
    backend.observed_owner = {"pid": 1}  # 接続相手は別に確認済みという故障注入。
    checks = []
    original = win._bind

    def bind(dll, name, result, *args):
        native = original(dll, name, result, *args)
        if name == "OpenMutexW":

            def open_same(access, inherit, object_name):
                checks.append(object_name)
                return native(access, inherit, object_name)

            return open_same
        return native

    def deny(*args):
        ct.set_last_error(5)
        return 0

    monkeypatch.setattr(win, "_bind", bind)
    backend.api.CreateMutexExW = deny
    try:
        result = show_startup_failure(StartupOutcome("connection_failed"), backend)
        assert result.result == (
            "coalesced" if existing else "notification_unavailable"
        )
        assert checks == [win.NoticeLease(backend, "contact_failed").name]
    finally:
        backend.close()
        _reclaim(children)


def _reclaim(children):
    """この試験が生成したPIDだけをfinallyで回収する。"""
    for child in children:
        if child.poll() is None:
            child.kill()
        try:
            child.communicate(timeout=_DRAIN_TIMEOUT)
        except subprocess.TimeoutExpired:
            # 保持者が残っても回収で無期限に待たない。失敗の報告は_finishが担う。
            warnings.warn(
                f"pid={child.pid}のpipeが{_DRAIN_TIMEOUT}秒以内に閉じない",
                RuntimeWarning,
                stacklevel=2,
            )


@pytest.mark.parametrize(
    "count, slow", [(2, False), (8, False), (2, True)], ids=["2", "8", "slow"]
)
def test_simultaneous_real_processes_construct_one_editor(tmp_path, count, slow):
    namespace = uuid4().hex
    role_prefix = "simultaneous-slow" if slow else "simultaneous"
    children = [_spawn(tmp_path, namespace, f"{role_prefix}-{i}") for i in range(count)]
    try:
        deadline = time.monotonic() + _BOOTSTRAP_TIMEOUT
        while (
            not any((fixture / "ready").exists() for _, fixture in children)
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        assert sum((fixture / "ready").exists() for _, fixture in children) == 1
        # 二次のterminal処理を済ませてから一次を終了する。
        deadline = time.monotonic() + 6
        while (
            sum(child.poll() is not None for child, _ in children) < count - 1
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        owner, owner_path = next(
            (child, path) for child, path in children if (path / "ready").exists()
        )
        results = [_finish(child) for child, _ in children if child is not owner]
        # 初期化が5秒を超えた場合のexpiredは仕様どおり。新しい起動だけで復帰する。
        for result in results:
            if result["result"] == "expired":
                assert 5000 <= result["elapsed"] < 6000
        if slow:
            assert all(result["result"] == "expired" for result in results)
        assert owner.poll() is None, "fresh起動前に一次processが終了した"
        fresh, _ = _spawn(
            tmp_path,
            namespace,
            "entry-module",
            expected_owner=json.loads((owner_path / "ready").read_text()),
        )
        children.append((fresh, tmp_path / "entry-module"))
        fresh_result = _finish(fresh)
        assert fresh_result["constructed"] == 0
        assert fresh_result["result"] in {"completed", "foreground_denied"}
        assert owner.poll() is None, "fresh応答完了までに一次processが終了した"
        (owner_path / "fresh-completed.json").write_text(
            json.dumps({"monotonic": time.monotonic(), "result": fresh_result}),
            encoding="utf-8",
        )
        (tmp_path / "stop-all").touch()
        owner_result = _finish(owner)
        if slow:
            assert owner_result["restored"] == 1, "期限切れ要求は遅れて復帰させない"
        results.append(owner_result)
        assert sum(r["constructed"] for r in results) == 1
        assert sum(r["result"] == "primary" for r in results) == 1
        assert all(
            r["result"] in {"primary", "completed", "foreground_denied", "expired"}
            for r in results
        )
        records = [
            json.loads(line)
            for line in (owner_path / "exit-audit.jsonl").read_text().splitlines()
        ]
        completed = json.loads((owner_path / "fresh-completed.json").read_text())
        quits = [row for row in records if row["event"] == "quit_requested"]
        assert len(quits) == 1
        assert quits[0]["stop_all"]
        assert quits[0]["monotonic"] >= completed["monotonic"]
        assert not any(row["event"] == "native_audit_error" for row in records)
        assert any(
            row["event"] == "native_observer_removed" and row["removed"]
            for row in records
        )
    finally:
        _reclaim([child for child, _ in children])


@pytest.mark.parametrize("entry", ["wm", "button", "watchdog"])
def test_simultaneous_exit_audit_distinguishes_entry(tmp_path, entry):
    """入口を意図的に発火し、監査と元の正常終了が両立することを確認する。"""
    child, fixture = _spawn(tmp_path, uuid4().hex, f"simultaneous-audit-{entry}")
    try:
        _wait_file(child, fixture / "ready")
        if entry != "watchdog":
            (fixture / "audit-trigger").touch()
        result = _finish(child)
        assert result["constructed"] == 1
        assert result["result"] == "primary"
        records = [
            json.loads(line)
            for line in (fixture / "exit-audit.jsonl").read_text().splitlines()
        ]
        registered = [r for r in records if r["event"] == "entry_registered"]
        assert {r["entry"] for r in registered} == {"wm", "button", "watchdog"}
        fired = [r for r in records if r["event"] == "entry_fired"]
        assert [r["entry"] for r in fired] == [entry]
        quits = [r for r in records if r["event"] == "quit_requested"]
        assert len(quits) == 1
        assert not any(r["event"] == "native_close_received" for r in records)
        assert not any(r["event"] == "native_audit_error" for r in records)
        assert not quits[0]["stop"] and not quits[0]["stop_all"]
        assert records.index(fired[0]) < records.index(quits[0])
        watchdog = next(r for r in registered if r["entry"] == "watchdog")
        assert watchdog["delay_ms"] == 10000
        assert watchdog["after_id"]
        # Tcl 9.0 afterはTcl_GetTimeの絶対時刻で発火する。Pythonの
        # monotonicとは時計が異なるため、同じTcl時計で期限を比較する。
        if entry == "watchdog":
            assert fired[0]["tcl_microseconds"] >= watchdog["due_tcl_microseconds"]
        else:
            assert fired[0]["tcl_microseconds"] < watchdog["due_tcl_microseconds"]
    finally:
        _reclaim([child])


def test_simultaneous_exit_audit_native_wm_close(tmp_path):
    """実OSメッセージの受信から元のTk終了処理までを試験専用HWNDで確認。"""
    from pagefolio.startup_win32 import Win32Backend, _bind

    namespace = uuid4().hex
    child, fixture = _spawn(tmp_path, namespace, "simultaneous-audit-native-wm")
    try:
        _wait_file(child, fixture / "ready")
        ready = json.loads((fixture / "ready").read_text())
        initial_records = [
            json.loads(line)
            for line in (fixture / "exit-audit.jsonl").read_text().splitlines()
        ]
        hwnd = next(
            r["hwnd"]
            for r in initial_records
            if r["event"] == "native_observer_registered"
        )
        user32 = ct.WinDLL("user32", use_last_error=True)
        owner_pid = wt.DWORD()
        window_thread = _bind(
            user32, "GetWindowThreadProcessId", wt.DWORD, wt.HWND, ct.POINTER(wt.DWORD)
        )
        assert child.poll() is None
        assert window_thread(hwnd, ct.byref(owner_pid))
        # Windows venvではPopen.pidはlauncher、Tk所有者はその実行process。
        assert owner_pid.value == ready["pid"] == ready["snapshot"]["pid"], (
            "このfixtureが公開した実行processのHWNDだけに送る"
        )
        post = _bind(
            user32, "PostMessageW", wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
        )
        # 送信元はこの意図的操作の記録。受信側から未知の送信元を推定しない。
        sent = {
            "event": "test_native_close_post",
            "sender_pid": os.getpid(),
            "launcher_pid": child.pid,
            "target_pid": owner_pid.value,
            "hwnd": hwnd,
            "message": 0x10,
            "monotonic": time.monotonic(),
        }
        (fixture / "native-trigger.json").write_text(json.dumps(sent), encoding="utf-8")
        backend = Win32Backend(namespace)
        try:
            with backend._validate_peer(owner_pid.value, ready["process_created"]):
                assert post(hwnd, 0x10, 0, 0), ct.get_last_error()
        finally:
            backend.close()
        result = _finish(child)
        assert result["result"] == "primary"
        assert result["constructed"] == 1
        records = [
            json.loads(line)
            for line in (fixture / "exit-audit.jsonl").read_text().splitlines()
        ]
        received = [r for r in records if r["event"] == "native_close_received"]
        fired = [r for r in records if r["event"] == "entry_fired"]
        quits = [r for r in records if r["event"] == "quit_requested"]
        destroyed = [r for r in records if r["event"] == "native_observer_removed"]
        assert len(received) == len(fired) == len(quits) == len(destroyed) == 1
        assert received[0]["hwnd"] == hwnd
        assert fired[0]["entry"] == "wm"
        assert not quits[0]["stop"] and not quits[0]["stop_all"]
        assert destroyed[0]["removed"]
        assert not any(r["event"] == "native_audit_error" for r in records)
        assert (
            records.index(received[0])
            < records.index(fired[0])
            < records.index(quits[0])
            < records.index(destroyed[0])
        )
        assert received[0]["monotonic"] >= sent["monotonic"]
        watchdog = next(
            r
            for r in records
            if r["event"] == "entry_registered" and r["entry"] == "watchdog"
        )
        assert watchdog["delay_ms"] == 10000
        assert quits[0]["monotonic"] < watchdog["due_monotonic"]
        assert "window_geometry" in json.loads(
            (fixture / "pagefolio_settings.json").read_text(encoding="utf-8")
        )
    finally:
        _reclaim([child])


def test_takeover_two_candidates_after_confirmed_initialization_death(tmp_path):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, "initializing-owner")
    candidates = []
    try:
        _wait_file(owner, fixture / "ready")
        candidates = [_spawn(tmp_path, namespace, f"takeover-{i}") for i in range(2)]
        for child, path in candidates:
            _wait_file(child, path / "observed")
        owner.kill()
        owner.communicate()
        deadline = time.monotonic() + 6
        while (
            not any((path / "ready").exists() for _, path in candidates)
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        assert sum((path / "ready").exists() for _, path in candidates) == 1
        deadline = time.monotonic() + 5
        while (
            sum(child.poll() is not None for child, _ in candidates) < 1
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        (tmp_path / "stop-all").touch()
        results = [_finish(child) for child, _ in candidates]
        assert sum(r["constructed"] for r in results) == 1
        audits = [
            json.loads((path / "resource-audit.json").read_text())
            for _, path in candidates
        ]
        assert sum(a.get("takeover_claim") == "acquired" for a in audits) == 1
        assert all(a.get("death_confirmed") for a in audits)
    finally:
        _reclaim([owner] + [child for child, _ in candidates])


def test_lifecycle_cancel_quit_keeps_owner_then_restarts(tmp_path):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, "lifecycle-cancel-owner")
    children = [owner]
    try:
        _wait_file(owner, fixture / "ready")
        (fixture / "cancel").touch()
        _wait_file(owner, fixture / "cancelled")
        secondary, _ = _spawn(tmp_path, namespace, "secondary-after-cancel")
        children.append(secondary)
        assert _finish(secondary)["result"] in {"completed", "foreground_denied"}
        assert owner.poll() is None
        (fixture / "stop").touch()
        assert _finish(owner)["constructed"] == 1
        restarted, path = _spawn(tmp_path, namespace, "lifecycle-restarted")
        children.append(restarted)
        _wait_file(restarted, path / "ready")
        (path / "stop").touch()
        assert _finish(restarted)["constructed"] == 1
    finally:
        _reclaim(children)


def test_lifecycle_released_mapping_allows_new_claim_while_old_process_lives(tmp_path):
    from pagefolio.startup_win32 import READ_CONTROL, OwnedHandle, Win32Backend

    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, "lifecycle-worker")
    reader = Win32Backend(namespace)
    held = None
    children = [owner]
    try:
        _wait_file(owner, fixture / "ready")
        held = OwnedHandle(
            reader.api,
            reader.api.OpenFileMappingW(READ_CONTROL | 4, False, reader.state_name),
        )
        before = reader._read_owner()
        (fixture / "stop").touch()
        _wait_file(owner, fixture / "worker-alive")
        released = reader._read_owner()
        assert released["state"] == "released"
        assert released["generation"] == before["generation"]
        assert released["release_generation"]
        assert owner.poll() is None
        new, path = _spawn(tmp_path, namespace, "lifecycle-new-owner")
        children.append(new)
        _wait_file(new, path / "ready")
        assert reader._read_owner()["generation"] != before["generation"]
        (path / "stop").touch()
        assert _finish(new)["constructed"] == 1
        (fixture / "release-worker").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        if held:
            held.close()
        reader.close()
        _reclaim(children)


@pytest.mark.parametrize("state", ["ready", "initializing"])
def test_lifecycle_independent_restart_after_forced_owner_exit(tmp_path, state):
    namespace = uuid4().hex
    role = "lifecycle-killed-owner" if state == "ready" else "initializing-owner"
    owner, fixture = _spawn(tmp_path, namespace, role)
    children = [owner]
    try:
        _wait_file(owner, fixture / "ready")
        owner.kill()
        owner.communicate()
        new, path = _spawn(tmp_path, namespace, "lifecycle-new-owner")
        children.append(new)
        _wait_file(new, path / "ready")
        (path / "stop").touch()
        assert _finish(new)["constructed"] == 1
    finally:
        _reclaim(children)


def test_lifecycle_exception_before_identity_publication_then_restart(tmp_path):
    namespace = uuid4().hex
    failed, _ = _spawn(tmp_path, namespace, "prepublish-failure")
    assert _finish(failed)["constructed"] == 0
    owner, path = _spawn(tmp_path, namespace, "lifecycle-new-owner")
    try:
        _wait_file(owner, path / "ready")
        (path / "stop").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        _reclaim([owner])


def test_lifecycle_both_python_entries_and_relocated_version_share_owner(tmp_path):
    namespace = uuid4().hex
    owner, path = _spawn(tmp_path, namespace, "owner")
    children = [owner]
    try:
        _wait_file(owner, path / "ready")
        for role in ("entry-script", "entry-module", "entry-relocated"):
            child, _ = _spawn(tmp_path, namespace, role)
            children.append(child)
            result = _finish(child)
            assert result["constructed"] == 0
            assert result["result"] in {"completed", "foreground_denied"}
        (path / "stop").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        _reclaim(children)


@pytest.mark.parametrize("entry", ["script", "module", "relocated"])
def test_cross_entry_owner_accepts_both_entries_and_other_location(tmp_path, entry):
    namespace = uuid4().hex
    owner, path = _spawn(tmp_path, namespace, f"entry-owner-{entry}")
    children = [owner]
    try:
        _wait_file(owner, path / "ready")
        identity = json.loads((path / "ready").read_text())
        for role in ("entry-script", "entry-module", "entry-relocated"):
            child, fixture = _spawn(tmp_path, namespace, role, expected_owner=identity)
            children.append(child)
            result = _finish(child)
            assert result["constructed"] == 0
            assert result["result"] in {"completed", "foreground_denied"}
            audit = json.loads((fixture / "resource-audit.json").read_text())
            # Windows venv launcher PID と実Python PIDは一致しないことがある。
            assert audit["verified_owner"]["pid"] == identity["pid"]
            assert "allow_foreground" in audit
        (path / "stop").touch()
        result = _finish(owner)
        assert result["constructed"] == 1 and result["status_preserved"]
        assert 1 <= result["restored"] <= 3
    finally:
        (path / "stop").touch()
        _reclaim(children)


def test_startup_acceptance_product_identity_ignores_version_location_and_frozen(
    monkeypatch, tmp_path
):
    from pagefolio import constants
    from pagefolio.startup_win32 import Win32Backend

    identities = []
    for version, frozen in (("v1.test", False), ("v99.test", True)):
        monkeypatch.setattr(constants, "APP_VERSION", version)
        monkeypatch.setattr(sys, "frozen", frozen, raising=False)
        monkeypatch.setattr(sys, "executable", str(tmp_path / version / "app.exe"))
        backend = Win32Backend()
        try:
            identities.append(
                (backend.owner_name, backend.state_name, backend._pipe_name("x"))
            )
        finally:
            backend.close()
    assert identities[0] == identities[1]
    assert identities[0][0] == "Local\\PageFolio.Startup.Owner"


@pytest.mark.parametrize("owner_present", [True, False])
def test_startup_acceptance_guard_never_requests_foreign_or_missing_owner(
    tmp_path, owner_present
):
    namespace = uuid4().hex
    children = []
    try:
        if owner_present:
            owner, path = _spawn(tmp_path, namespace, "owner")
            children.append(owner)
            _wait_file(owner, path / "ready")
            expected = json.loads((path / "ready").read_text())
            expected["process_created"] += 1
        else:
            expected = {"pid": 1, "process_created": 1}
        child, child_path = _spawn(
            tmp_path, namespace, "entry-module", expected_owner=expected
        )
        children.append(child)
        child.communicate(timeout=8)
        assert child.returncode != 0
        audit = json.loads((child_path / "resource-audit.json").read_text())
        assert audit["guard_blocked"]
        assert "allow_foreground" not in audit
        assert not (child_path / "ready").exists()
        if owner_present:
            (path / "stop").touch()
            result = _finish(owner)
            assert result["constructed"] == 1 and result["restored"] == 0
    finally:
        _reclaim(children)


def test_lifecycle_partial_mapping_reader_closes_without_takeover():
    from pagefolio.startup_control import StartupCoordinator
    from pagefolio.startup_win32 import READ_CONTROL, OwnedHandle, Win32Backend

    namespace = uuid4().hex
    owner = Win32Backend(namespace)
    secondary = Win32Backend(namespace)
    next_owner = Win32Backend(namespace)
    held = None
    try:
        assert owner.claim(uuid4().hex) == "acquired"
        held = OwnedHandle(
            secondary.api,
            secondary.api.OpenFileMappingW(
                READ_CONTROL | 4, False, secondary.state_name
            ),
        )
        ct.c_ulonglong.from_address(owner.view).value = 3
        control = StartupCoordinator(secondary)
        assert not control.claim().primary
        # 意図的に残余80msから開始し、長い組合せを通常pytestへ持ち込まない。
        result = control.request_activation(secondary.tick_ms() - 4920)
        assert result.result == "expired"
        assert not control.takeover_attempted
        assert secondary.observed_process is None
        control.close()
        owner.close()
        # 全readerを閉じた後には、未知identityを上書きせず通常一次になれる。
        held.close()
        held = None
        assert next_owner.claim(uuid4().hex) == "acquired"
    finally:
        if held:
            held.close()
        owner.close()
        secondary.close()
        next_owner.close()


def test_takeover_abandoned_owner_thread_with_live_process_uses_existing_pipe():
    from pagefolio.startup_control import StartupCoordinator
    from pagefolio.startup_win32 import Win32Backend

    namespace = uuid4().hex
    holder = []

    def owning_thread():
        b = Win32Backend(namespace)
        assert b.claim(uuid4().hex) == "acquired"
        b.listen(
            lambda raw: {
                "request_id": raw["request_id"],
                "result": "completed",
                "completed_tick": b.tick_ms(),
                "coalesced": False,
            }
        )
        b.publish_state("ready", True)
        holder.append(b)

    worker = threading.Thread(target=owning_thread)
    worker.start()
    worker.join(2)
    assert not worker.is_alive() and len(holder) == 1
    secondary = Win32Backend(namespace)
    control = StartupCoordinator(secondary)
    try:
        assert not control.claim().primary
        assert not secondary.owns_mutex
        assert control.request_activation(secondary.tick_ms()).result == "completed"
        assert not control.takeover_attempted
        assert control.root is None
    finally:
        control.close()
        # 死亡threadの試験資源だけを回収する。mutexは候補が返却済み。
        holder[0].owner_thread = threading.get_ident()
        holder[0].owns_mutex = False
        holder[0].close()


def test_lifecycle_failed_release_is_closing_until_all_readers_close(monkeypatch):
    from pagefolio.startup_win32 import READ_CONTROL, OwnedHandle, Win32Backend

    namespace = uuid4().hex
    owner, candidate, later = [Win32Backend(namespace) for _ in range(3)]
    held = None
    try:
        assert owner.claim(uuid4().hex) == "acquired"
        held = OwnedHandle(
            candidate.api,
            candidate.api.OpenFileMappingW(
                READ_CONTROL | 4, False, candidate.state_name
            ),
        )
        publish = owner._publish_owner

        def fail_release(state, ready):
            if state == "released":
                raise OSError("release故障注入")
            publish(state, ready)

        monkeypatch.setattr(owner, "_publish_owner", fail_release)
        owner.close(root_absent=True)
        assert candidate._read_owner()["state"] == "closing"
        assert candidate.claim(uuid4().hex) == "existing"
        assert not candidate.owns_mutex
        candidate.close()
        held.close()
        held = None
        assert later.claim(uuid4().hex) == "acquired"
    finally:
        if held:
            held.close()
        owner.close()
        candidate.close()
        later.close()


def test_lifecycle_release_follows_stop_and_precedes_mutex_release(monkeypatch):
    from pagefolio.startup_win32 import Win32Backend

    b = Win32Backend(uuid4().hex)
    states = []
    try:
        assert b.claim(uuid4().hex) == "acquired"
        b.listen(lambda raw: {"result": "expired"})
        publish = b._publish_owner

        def record(state, ready):
            states.append(
                (
                    state,
                    b.owns_mutex,
                    b.stop.is_set(),
                    any(w.is_alive() for w in b.workers),
                )
            )
            publish(state, ready)

        monkeypatch.setattr(b, "_publish_owner", record)
        b.close(root_absent=True)
        assert states[0][:3] == ("closing", True, False)
        assert states[1] == ("released", True, True, False)
        assert not b.owns_mutex
    finally:
        b.close()


@pytest.mark.parametrize("entry", ["entry-script", "entry-module"])
@pytest.mark.parametrize(
    "case",
    [
        "thumb",
        "preview",
        "settings",
        "nested",
        "native-ocr",
        "native-quit",
        "rebuild",
        "normal",
        "zoomed",
    ],
)
def test_focus_restore_real_main_windows(tmp_path, entry, case):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, f"focus-owner-{case}")
    children = [owner]
    try:
        _wait_file(owner, fixture / "focus-ready")
        child, _ = _spawn(tmp_path, namespace, entry)
        children.append(child)
        result = _finish(child)
        assert result["constructed"] == 0
        assert result["result"] in {"completed", "foreground_denied"}
        _wait_file(owner, fixture / "focus-result.json")
        measured = json.loads((fixture / "focus-result.json").read_text())
        assert measured["state_preserved"]
        assert measured["target_correct"]
        assert measured["focus_correct"], measured
        if case == "native-quit":
            _wait_file(owner, fixture / "quit-cancelled")
        (fixture / "stop").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        _reclaim(children)


@pytest.mark.parametrize("case", ["pdf", "ocr"])
def test_working_state_real_main_continues(tmp_path, case):
    namespace = uuid4().hex
    owner, fixture = _spawn(tmp_path, namespace, f"focus-owner-{case}")
    children = [owner]
    try:
        _wait_file(owner, fixture / "focus-ready")
        child, _ = _spawn(tmp_path, namespace, "entry-module")
        children.append(child)
        assert _finish(child)["result"] in {"completed", "foreground_denied"}
        _wait_file(owner, fixture / "focus-result.json")
        measured = json.loads((fixture / "focus-result.json").read_text())
        assert measured["state_preserved"] and measured["target_correct"]
        _wait_file(owner, fixture / "continued")
        (fixture / "stop").touch()
        assert _finish(owner)["constructed"] == 1
    finally:
        _reclaim(children)


def _prepare_focus_case(app, fixture, case, *, manual=False):
    """実main上で実widget/履歴/OCRを準備。native popupも期限内に自動閉鎖。"""
    import tkinter as tk
    from tkinter import messagebox, ttk

    import pymupdf as fitz

    from pagefolio.ocr_dialog import OCRDialog
    from pagefolio.ocr_providers import OCRProvider
    from pagefolio.startup_win32 import _bind
    from pagefolio.undo_store import FileBlob, MemBlob

    root, focus = app.root, app._startup_focus
    backend = focus.backend
    state = {"target": root, "entry": None, "ocr": None, "focus": None}
    release = threading.Event()
    entered = threading.Event()

    class Provider(OCRProvider):
        timeout = 10

        def ocr_image(self, b64_png, prompt, **kwargs):
            assert isinstance(b64_png, str)
            entered.set()
            assert release.wait(110 if manual else 6), "OCR解除の期限切れ"
            return "local OCR completed"

        def list_models(self):
            return ["isolated"]

    def pdf():
        app.doc = fitz.open()
        for i in range(3):
            app.doc.new_page().insert_text((50, 50), f"unsaved {i}")
        app.selected_pages = {0}
        app._rotate_selected(90)
        app._duplicate_page()
        # 本番delete経路でBlobを作り、確認だけ試験内で自動応答する。
        ask = messagebox.askyesno
        try:
            messagebox.askyesno = lambda *a, **kw: True
            app.selected_pages = {2}
            app._delete_selected()
        finally:
            messagebox.askyesno = ask

    def ocr_dialog():
        if not app.doc:
            app.doc = fitz.open()
            app.doc.new_page(width=100, height=100)
        dialog = OCRDialog(
            root,
            app,
            app.doc,
            [0],
            "",
            "isolated",
            "text",
            1,
            10,
            provider=Provider(),
            concurrency=1,
        )
        state.update(target=dialog, ocr=dialog)
        return dialog

    def blobs(value):
        if isinstance(value, (MemBlob, FileBlob)):
            return (
                id(value),
                hashlib.sha256(app._blob_bytes(value)).hexdigest(),
                value._released,
            )
        if isinstance(value, dict):
            return tuple((k, blobs(v)) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return tuple(blobs(v) for v in value)
        return value

    def snapshot():
        dialog, entry = state["ocr"], state["entry"]
        return (
            id(app),
            id(app.doc),
            tuple(hashlib.sha256(p.get_pixmap().samples).hexdigest() for p in app.doc)
            if app.doc
            else (),
            tuple((id(s), blobs(s)) for s in app._undo_stack),
            tuple((id(s), blobs(s)) for s in app._redo_stack),
            set(app.selected_pages),
            app.current_page,
            app.status_var.get(),
            str(root.grab_current()),
            (
                entry.get(),
                entry.index("insert"),
                entry.index("sel.first"),
                entry.index("sel.last"),
            )
            if entry
            else None,
            (
                id(dialog),
                dialog._run_gen,
                id(dialog._engine),
                tuple(id(t) for t in dialog._engine._worker_threads),
            )
            if dialog and dialog._engine
            else None,
        )

    def continued():
        if case == "pdf":
            for operation in (app._undo, app._redo, app._undo, app._redo):
                operation()
            assert len(app.doc) == 3 and app.doc[0].rotation == 90
            (fixture / "continued").touch()
        elif case == "ocr":
            dialog = state["ocr"]
            if dialog._done:
                assert dialog.results == {0: "local OCR completed"}
                assert not dialog.errors
                assert all(not t.is_alive() for t in dialog._engine._worker_threads)
                (fixture / "continued").touch()
            else:
                root.after(30, continued)

    def before():
        state["before"] = snapshot()

    def after(result):
        assert result in {"completed", "foreground_denied"}
        preserved = snapshot() == state["before"]
        expected = backend._top_level_hwnd(state["target"])
        actual = state.get("activated")
        if case.startswith("native-"):
            correct = actual not in {None, expected} and state.get("native") == actual
        else:
            correct = actual == expected
        if case in {"normal", "zoomed"}:
            correct &= root.state() == case
            if case == "normal":
                correct &= root.geometry() == state["geometry"]
        record = {
            "state_preserved": preserved,
            "target_correct": bool(correct),
            "result": result,
            "activated": actual,
            "expected_tk": expected,
            "native": state.get("native"),
            "placement": root.state(),
            "expected_focus": str(state["focus"]),
            "immediate_focus": str(root.focus_get()),
            "focus_correct": result != "completed"
            or state["focus"] is None
            or root.focus_get() is state["focus"],
        }

        def settled():
            # TkのFocusIn処理後に一度だけ観測。成功するまで再試行しない。
            record["settled_focus"] = str(root.focus_get())
            record["focus_correct"] = (
                result != "completed"
                or state["focus"] is None
                or root.focus_get() is state["focus"]
            )
            (fixture / "focus-result.json").write_text(json.dumps(record))

        root.after_idle(settled)
        release.set()
        if case in {"pdf", "ocr"}:
            root.after(30, continued)

    def cleanup():
        release.set()
        for window in list(root.winfo_children()):
            if isinstance(window, tk.Toplevel):
                window.destroy()
        if app.doc:
            app._clear_undo_stacks()
            app.doc.close()
            app.doc = None

    app._focus_before, app._focus_after = before, after
    app._focus_state = state
    app._focus_cleanup = cleanup
    if case == "pdf":
        pdf()
    elif case in {"ocr", "native-ocr"}:
        dialog = ocr_dialog()
        if case == "ocr":
            import pagefolio.ocr_dialog as module

            module.build_provider = lambda *a, **kw: dialog.provider
            dialog.force_ocr_var.set(True)
            dialog._on_run(settings={**app.settings, "ocr_provider": "tesseract"})
    elif case in {"settings", "nested"}:
        app._open_settings()
        dialog = app._settings_dialog
        entry = ttk.Entry(dialog)
        entry.pack()
        entry.insert(0, "unsaved input")
        entry.icursor(5)
        entry.selection_range(1, 7)
        entry.focus_set()
        state.update(target=dialog, entry=entry)
        state["focus"] = entry
        if case == "nested":
            dialog._open_llm_config()
            nested = dialog._llm_config_dialog

            def close_nested():
                nested.destroy()
                assert root.grab_current() is None
                entry.focus_set()

            root.after(100, close_nested)
    elif case == "rebuild":
        app.preview_canvas.focus_set()
        app._rebuild_ui()
    elif case in {"thumb", "preview"}:
        widget = getattr(app, "thumb_canvas" if case == "thumb" else "preview_canvas")
        widget.focus_set()
        state["focus"] = widget
    elif case in {"normal", "zoomed"}:
        root.state(case)

    def ready():
        focus.observe()
        if case == "ocr" and not entered.is_set():
            root.after(20, ready)
            return
        if case in {"normal", "zoomed"}:
            focus._remember_window_state()
            state["geometry"] = root.geometry()
            root.iconify()
        (fixture / "focus-ready").touch()
        if case.startswith("native-"):
            deadline = time.monotonic() + 5
            post = _bind(
                backend.api.u,
                "PostMessageW",
                wt.BOOL,
                wt.HWND,
                wt.UINT,
                wt.WPARAM,
                wt.LPARAM,
            )

            def close_native():
                if (
                    fixture / "focus-result.json"
                ).exists() or time.monotonic() > deadline:
                    popup = backend._owned_popup(
                        [backend._top_level_hwnd(state["target"])]
                    )
                    if popup:
                        assert post(popup, 0x111, 7 if case == "native-quit" else 1, 0)
                        return
                root.after(30, close_native)

            if not manual:
                root.after(30, close_native)
            if case == "native-quit":
                pdf()
                app._quit()
                assert root.winfo_exists()
                (fixture / "quit-cancelled").touch()
            else:
                messagebox.showinfo(
                    "isolated OCR", "operation continues", parent=state["target"]
                )

    root.after(250, ready)


def test_lifecycle_released_identity_mismatch_cannot_overwrite_mapping():
    from pagefolio.startup_win32 import READ_CONTROL, OwnedHandle, Win32Backend

    namespace = uuid4().hex
    owner, candidate = [Win32Backend(namespace) for _ in range(2)]
    held = None
    try:
        assert owner.claim(uuid4().hex) == "acquired"
        held = OwnedHandle(
            candidate.api,
            candidate.api.OpenFileMappingW(
                READ_CONTROL | 4, False, candidate.state_name
            ),
        )
        original_created = owner._created
        owner._created = lambda process: original_created(process) + 1
        owner.close(root_absent=True)
        before = candidate._read_owner()
        assert before["state"] == "released"
        assert candidate.claim(uuid4().hex) == "existing"
        assert candidate._read_owner() == before
    finally:
        if held:
            held.close()
        owner.close()
        candidate.close()


def _run_scenario(fixture, namespace, role):
    """各spawnで初回app import前に設定/プロンプト/pluginsを隔離する。"""
    sys.path.insert(
        0,
        str(fixture / "alternate")
        if role in {"entry-relocated", "entry-owner-relocated"}
        else str(_ROOT),
    )
    from pagefolio import plugins, settings

    settings._get_base_dir = lambda: str(fixture)
    plugins._get_plugins_dir = lambda: str(fixture / "plugins")
    from pagefolio.startup_win32 import Win32Backend, _tick_ms

    backend_namespace = None if namespace == "fixed-production" else namespace
    if role == "initializing-owner":
        backend = Win32Backend(backend_namespace)
        try:
            assert backend.claim(uuid4().hex) == "acquired"
            (fixture / "ready").touch()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                time.sleep(0.02)
        finally:
            backend.close()
        return
    if role.startswith("notice-case-"):
        from pagefolio.startup_win32 import NativeNoticeLifetime, NoticeLease, _bind

        backend = Win32Backend(backend_namespace)
        foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
        started = backend.tick_ms()
        audit = {"foreground_before": foreground()}
        reason = "timeout" if role == "notice-case-other-reason" else "contact_failed"
        lifetime = 1800 if role == "notice-case-owner" else 150
        if role == "notice-case-production-owner":
            lifetime = 10000
        try:
            with NoticeLease(backend, reason) as lease:
                audit.update(acquired=lease.acquired, snapshot=lease.snapshot)
                if lease.acquired:
                    notice = NativeNoticeLifetime(backend, reason, lease=lease)

                    def published(hwnd):
                        if observer is not None:
                            observer.mark("notice_published", hwnd=hwnd)
                        audit.update(
                            snapshot=lease.snapshot,
                            deadline_tick=notice.deadline_tick,
                            dpi=notice.dpi,
                            close_rect=[
                                notice.close_rect.left,
                                notice.close_rect.top,
                                notice.close_rect.right,
                                notice.close_rect.bottom,
                            ],
                        )
                        (fixture / "ready").write_text(
                            json.dumps(audit), encoding="utf-8"
                        )

                    with (
                        _ForegroundAudit(backend, fixture / "foreground-audit.jsonl")
                        if role == "notice-case-owner"
                        else nullcontext()
                    ) as observer:
                        if observer is not None:
                            observer.mark("notice_show_call")
                        notice.show(lifetime_ms=lifetime, on_show=published)
                        # 既存の4実測値とイベント時系列を両方保存する。
                        audit.update(
                            foreground_before_show=notice.foreground_before_show,
                            foreground_after_show=notice.foreground_after_show,
                            foreground_before_close=notice.foreground_before_close,
                            foreground_after_close=notice.foreground_after_close,
                        )
                        if observer is not None:
                            observer.mark(
                                "notice_returned",
                                foreground_before_show=notice.foreground_before_show,
                                foreground_after_show=notice.foreground_after_show,
                                foreground_before_close=notice.foreground_before_close,
                                foreground_after_close=notice.foreground_after_close,
                            )
            audit.update(
                elapsed=backend.tick_ms() - started, foreground_after=foreground()
            )
            (fixture / "result.json").write_text(json.dumps(audit), encoding="utf-8")
            print(json.dumps(audit))
        finally:
            backend.close()
        return
    if role.startswith("lease-"):
        from pagefolio.startup_win32 import NativeNoticeLifetime, NoticeLease

        backend = Win32Backend(backend_namespace)
        try:
            with NoticeLease(backend, "connection_failed") as lease:
                if role == "lease-owner":
                    assert lease.acquired
                    notice = NativeNoticeLifetime(
                        backend, "connection_failed", lease=lease
                    )

                    def publish(hwnd):
                        (fixture / "ready").touch()

                    notice.show(lifetime_ms=1800, on_show=publish)
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
                    snapshot=lease.snapshot,
                    dpi=notice.dpi,
                    close_rect=[
                        notice.close_rect.left,
                        notice.close_rect.top,
                        notice.close_rect.right,
                        notice.close_rect.bottom,
                    ],
                )
                (fixture / "ready").write_text(json.dumps(audit), encoding="utf-8")

            with NoticeLease(backend, "connection_failed") as lease:
                audit["lease_acquired"] = lease.acquired
                if lease.acquired:
                    notice = NativeNoticeLifetime(
                        backend, "connection_failed", lease=lease
                    )
                    notice.show(on_show=visible)
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

    if role.startswith("constructor-failure-"):
        from pagefolio import startup_win32 as win

        audit = {"constructed": 0, "notice_calls": 0}
        unavailable = "unavailable" in role

        if "legacy-" in role:
            from pagefolio.startup_control import StartupOutcome
            from pagefolio.startup_notice import show_startup_failure

            backend = win.Win32Backend(backend_namespace)
            try:
                if role == "constructor-failure-legacy-owner":
                    with win.NoticeLease(backend, "check_failed") as lease:
                        assert lease.acquired
                        notice = win.NativeNoticeLifetime(
                            backend, "check_failed", lease=lease
                        )

                        def visible(hwnd):
                            audit["notice_calls"] = 1
                            audit["snapshot"] = lease.snapshot.copy()
                            (fixture / "ready").write_text(
                                json.dumps(audit), encoding="utf-8"
                            )

                        notice.show(lifetime_ms=1800, on_show=visible)
                else:
                    result = show_startup_failure(
                        StartupOutcome("check_failed"), backend
                    )
                    assert result.result == "coalesced"
                    with win.NoticeLease(backend, "check_failed") as lease:
                        assert not lease.acquired
                        audit["snapshot"] = lease.snapshot
                audit["result"] = "check_failed"
            finally:
                backend.close()
            print(json.dumps(audit))
            return

        def fail_startup():
            raise OSError(5, "private-path-SID-secret")

        class NoticeOnly(win.Win32NoticeBackend):
            def __init__(self):
                if unavailable:
                    raise OSError(5, "private-path-SID-secret")
                super().__init__(backend_namespace)

            def _create_notice_lease(self, reason):
                from contextlib import contextmanager

                native = super()._create_notice_lease(reason)

                @contextmanager
                def observed():
                    with native as lease:
                        audit["snapshot"] = lease.snapshot
                        yield lease

                return observed()

            def display_notice(self, reason, text, lease):
                notice = win.NativeNoticeLifetime(self, reason, text=text, lease=lease)
                foreground = win._bind(self.api.u, "GetForegroundWindow", wt.HWND)
                audit["foreground_before"] = foreground()
                audit["reason"] = str(reason)

                def visible(hwnd):
                    audit["notice_calls"] += 1
                    audit["foreground_shown"] = foreground()
                    audit["snapshot"] = lease.snapshot.copy()
                    if role == "constructor-failure-owner":
                        (fixture / "ready").write_text(
                            json.dumps(audit), encoding="utf-8"
                        )
                    if role == "constructor-failure-manual":
                        post = win._bind(
                            self.api.u,
                            "PostMessageW",
                            wt.BOOL,
                            wt.HWND,
                            wt.UINT,
                            wt.WPARAM,
                            wt.LPARAM,
                        )
                        rect = notice.close_rect
                        assert post(
                            hwnd,
                            0x202,
                            0,
                            ((rect.top + 1) << 16) | (rect.left + 1),
                        )

                notice.show(
                    lifetime_ms=1800 if role == "constructor-failure-owner" else 150,
                    on_show=visible,
                )
                audit.update(
                    foreground_after=foreground(),
                    foreground_before_show=notice.foreground_before_show,
                    foreground_after_show=notice.foreground_after_show,
                    foreground_before_close=notice.foreground_before_close,
                    foreground_after_close=notice.foreground_after_close,
                )

        if role == "constructor-failure-descriptor":
            original_security = win._security_descriptor

            def fail_pipe_security(api, sid, rights):
                if rights == 0x12019F:
                    raise OSError(5, "private-path-SID-secret")
                return original_security(api, sid, rights)

            win._security_descriptor = fail_pipe_security
        else:
            win.Win32Backend = fail_startup
        win.Win32NoticeBackend = NoticeOnly
        entry = role.removeprefix("constructor-failure-")
        if entry in {"module", "script", "unavailable-module", "unavailable-script"}:
            try:
                if entry.endswith("script"):
                    runpy.run_path(str(_ROOT / "pagefolio.py"), run_name="__main__")
                else:
                    runpy.run_module("pagefolio", run_name="__main__")
            except SystemExit as e:
                audit["exit"] = e.code
            else:
                audit["exit"] = 0
            audit["result"] = (
                "notification_unavailable" if unavailable else "check_failed"
            )
        else:
            audit["result"] = main()
        assert "pagefolio.app" not in sys.modules
        print(json.dumps(audit))
        return

    counts = {"constructed": 0, "restored": 0, "status_preserved": True}
    app_reference = []
    backend_instances = []
    may_be_primary = role in {
        "owner",
        "manual-owner",
        "init-failure",
    } or role.startswith(
        (
            "simultaneous-",
            "takeover-",
            "lifecycle-",
            "focus-owner-",
            "entry-owner-",
            "uat-owner-",
        )
    )
    if may_be_primary:
        from pagefolio import app as app_module

        class TracedApp(app_module.PDFEditorApp):
            def _audit_exit(self, event, **details):
                if role.startswith("simultaneous-"):
                    record = {
                        "event": event,
                        "tick": _tick_ms(),
                        "monotonic": time.monotonic(),
                        "stop": (fixture / "stop").exists(),
                        "stop_all": (fixture.parent / "stop-all").exists(),
                        "stack": [
                            {
                                "file": Path(frame.filename).name,
                                "line": frame.lineno,
                                "function": frame.name,
                            }
                            for frame in traceback.extract_stack(limit=8)
                        ],
                        **details,
                    }
                    with (fixture / "exit-audit.jsonl").open(
                        "a", encoding="utf-8"
                    ) as audit_file:
                        audit_file.write(json.dumps(record) + "\n")

            def _quit(self):
                self._audit_exit("quit_requested")
                return super()._quit()

            def _audit_native_close(self, root):
                from pagefolio.startup_win32 import _bind

                # HWND所有thread内で登録。元のWndProcには必ず全メッセージを渡す。
                hwnd = backend_instances[0]._top_level_hwnd(root)
                assert hwnd, "終了監査には試験ウィンドウのHWNDが必要"
                comctl = ct.WinDLL("comctl32", use_last_error=True)
                callback_type = ct.WINFUNCTYPE(
                    ct.c_ssize_t,
                    wt.HWND,
                    wt.UINT,
                    wt.WPARAM,
                    wt.LPARAM,
                    ct.c_size_t,
                    ct.c_size_t,
                )
                install = _bind(
                    comctl,
                    "SetWindowSubclass",
                    wt.BOOL,
                    wt.HWND,
                    callback_type,
                    ct.c_size_t,
                    ct.c_size_t,
                )
                remove = _bind(
                    comctl,
                    "RemoveWindowSubclass",
                    wt.BOOL,
                    wt.HWND,
                    callback_type,
                    ct.c_size_t,
                )
                forward = _bind(
                    comctl,
                    "DefSubclassProc",
                    ct.c_ssize_t,
                    wt.HWND,
                    wt.UINT,
                    wt.WPARAM,
                    wt.LPARAM,
                )

                def observe(window, message, wparam, lparam, subclass_id, ref_data):
                    try:
                        if message == 0x10:  # WM_CLOSE
                            self._audit_exit("native_close_received", hwnd=window)
                        elif message == 0x82:  # WM_NCDESTROY
                            removed = remove(
                                window, self._native_close_callback, subclass_id
                            )
                            self._audit_exit(
                                "native_observer_removed",
                                hwnd=window,
                                removed=bool(removed),
                            )
                    except Exception as e:
                        # ctypes callbackから例外を漏らさず、診断失敗でも元処理を通す。
                        logging.exception("native exit audit failed")
                        try:
                            self._audit_exit(
                                "native_audit_error", error=type(e).__name__
                            )
                        except Exception as audit_error:
                            logging.error(
                                "native audit write failed: %s",
                                type(audit_error).__name__,
                            )
                    return forward(window, message, wparam, lparam)

                # C側は参照を保持しない。アプリの生存中callbackを解放しない。
                self._native_close_callback = callback_type(observe)
                assert install(hwnd, self._native_close_callback, 1, 0)
                self._audit_exit("native_observer_registered", hwnd=hwnd)

            def _audit_exit_entries(self, root):
                # 元のTcl commandへ委譲し、製品の終了判断・保存処理を維持する。
                def wrap(entry, command):
                    def callback():
                        # Tcl時計はTkが呼び出したPython callback内でだけ取得する。
                        # Win32 subclassの受信callbackからTkを再入呼出ししない。
                        self._audit_exit(
                            "entry_fired",
                            entry=entry,
                            tcl_microseconds=int(root.tk.call("clock", "microseconds")),
                        )
                        return root.tk.call(command)

                    return callback

                command = root.protocol("WM_DELETE_WINDOW")
                root.protocol("WM_DELETE_WINDOW", wrap("wm", command))
                self._audit_exit(
                    "entry_registered", entry="wm", original_command=command
                )
                pending = [root]
                buttons = []
                while pending:
                    widget = pending.pop()
                    pending.extend(widget.winfo_children())
                    if widget.winfo_class() == "TButton" and widget.cget(
                        "text"
                    ) == self._t("btn_quit"):
                        buttons.append(widget)
                assert len(buttons) == 1, "終了入口監査の対象ボタンは1つ"
                self._audit_quit_button = buttons[0]
                command = str(buttons[0].cget("command"))
                buttons[0].configure(command=wrap("button", command))
                self._audit_exit(
                    "entry_registered", entry="button", original_command=command
                )

            def __init__(self, root):
                counts["constructed"] += 1
                if role == "init-failure":
                    raise RuntimeError("tracer-initialization-failure")
                if role.startswith("simultaneous-slow-"):
                    time.sleep(8.5)
                super().__init__(root)
                if role.startswith("simultaneous-"):
                    self._audit_exit_entries(root)
                    self._audit_native_close(root)
                app_reference.append(self)
                if role == "uat-owner-slowready":
                    (fixture / "scenario-ready").touch()
                    time.sleep(6.5)
                if role == "uat-owner-busy":

                    def busy():
                        before = counts["restored"]
                        (fixture / "scenario-ready").touch()
                        time.sleep(6.5)
                        self.root.after(
                            500,
                            lambda: (fixture / "busy-result.json").write_text(
                                json.dumps(
                                    {
                                        "before": before,
                                        "after": counts["restored"],
                                        "tick": backend_instances[0].tick_ms(),
                                    }
                                )
                            ),
                        )

                    root.after(500, busy)
                if role.startswith(("focus-owner-", "uat-owner-")):
                    case = role.split("owner-", 1)[1]
                    root.after(
                        150,
                        lambda: _prepare_focus_case(
                            self,
                            fixture,
                            "preview" if case in {"busy", "slowready"} else case,
                            manual=role.startswith("uat-"),
                        ),
                    )
                if role == "lifecycle-cancel-owner":
                    import pymupdf as fitz

                    self.doc = fitz.open()
                    self.doc.new_page()
                    app_module.messagebox.askyesno = lambda *a: (
                        fixture / "stop"
                    ).exists()

                def stop_poll():
                    if (
                        role in {"simultaneous-audit-wm", "simultaneous-audit-button"}
                        and (fixture / "audit-trigger").exists()
                    ):
                        self._audit_exit("test_trigger", entry=role.rsplit("-", 1)[1])
                        if role == "simultaneous-audit-wm":
                            root.tk.call(root.protocol("WM_DELETE_WINDOW"))
                        else:
                            self._audit_quit_button.invoke()
                        return
                    if (fixture / "stop").exists() or (
                        fixture.parent / "stop-all"
                    ).exists():
                        if role.startswith(("focus-owner-", "uat-owner-")):
                            self._focus_cleanup()
                        self._quit()
                    else:
                        if (
                            role == "lifecycle-cancel-owner"
                            and (fixture / "cancel").exists()
                            and not (fixture / "cancelled").exists()
                        ):
                            self._quit()
                            assert root.winfo_exists()
                            (fixture / "cancelled").touch()
                        root.after(50, stop_poll)

                root.after(50, stop_poll)
                delay_ms = (
                    120000
                    if role == "manual-owner" or role.startswith("uat-")
                    else 10000
                )

                def watchdog():
                    self._audit_exit(
                        "entry_fired",
                        entry="watchdog",
                        tcl_microseconds=int(root.tk.call("clock", "microseconds")),
                    )
                    if role.startswith("uat-"):
                        self._focus_cleanup()
                    self._quit()

                registered_tcl_us = int(root.tk.call("clock", "microseconds"))
                registered_at = time.monotonic()
                after_id = root.after(delay_ms, watchdog)
                self._audit_exit(
                    "entry_registered",
                    entry="watchdog",
                    delay_ms=delay_ms,
                    after_id=after_id,
                    registered_monotonic=registered_at,
                    due_monotonic=registered_at + delay_ms / 1000,
                    registered_tcl_microseconds=registered_tcl_us,
                    due_tcl_microseconds=registered_tcl_us + delay_ms * 1000,
                )

        app_module.PDFEditorApp = TracedApp

    class Backend(Win32Backend):
        def __init__(self):
            super().__init__(backend_namespace)
            backend_instances.append(self)
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.StreamHandler(sys.stderr))
            self.audit = {
                "sid": self.sid,
                "authentication_luid": self.authentication_luid,
                "session_id": self.session_id,
                "pid": self.pid,
                "process_created": self._created(self.api.GetCurrentProcess()),
                "started_tick": self.tick_ms(),
            }
            self.notice_lease = None
            if role == "api-denied":

                def deny(*args):
                    ct.set_last_error(5)
                    return None

                self.api.CreateMutexExW = deny
            if role in {"notice-via-main", "notice-production-contact"}:

                def deny_pipe(*args):
                    ct.set_last_error(5)
                    return ct.c_void_p(-1).value

                self.api.CreateFileW = deny_pipe
            if role == "notice-production-check":
                original_mutex = self.api.CreateMutexExW

                def deny_owner(attributes, name, flags, access):
                    if name == self.owner_name:
                        ct.set_last_error(5)
                        return None
                    return original_mutex(attributes, name, flags, access)

                self.api.CreateMutexExW = deny_owner

        def _publish_owner(self, state, ready):
            if role == "prepublish-failure":
                raise RuntimeError("tracer-prepublish-failure")
            return super()._publish_owner(state, ready)

        def request_activation(self, started_tick):
            result = super().request_activation(started_tick)
            self.audit["terminal_result"] = result
            self.audit["elapsed"] = self.tick_ms() - started_tick
            return result

        def _observe_owner(self, owner):
            expected_file = fixture / "expected-owner.json"
            if expected_file.exists():
                expected = json.loads(expected_file.read_text(encoding="utf-8"))
                if any(owner[k] != expected[k] for k in ("pid", "process_created")):
                    self.audit["guard_blocked"] = "identity_mismatch"
                    raise PermissionError("接続先が試験一次と異なるため要求を中断")
            process = super()._observe_owner(owner)
            self.audit["verified_owner"] = owner
            if role.startswith("takeover-"):
                (fixture / "observed").touch()
            return process

        def _allow_foreground(self, pid):
            result = super()._allow_foreground(pid)
            self.audit["allow_foreground"] = {
                "pid": pid,
                "allowed": result[0],
                "os_error": result[1],
            }
            return result

        def try_takeover(self, generation, expected, deadline):
            self.audit["death_confirmed"] = self._process_has_exited(
                self.observed_process
            )
            self.audit["dead_identity"] = expected
            result = super().try_takeover(generation, expected, deadline)
            self.audit["takeover_claim"] = result
            return result

        def claim(self, generation):
            from pagefolio.startup_win32 import NoticeLease

            result = super().claim(generation)
            self.audit["owner_result"] = result
            if (fixture / "expected-owner.json").exists() and result == "acquired":
                self.audit["guard_blocked"] = "owner_missing"
                raise PermissionError("試験一次が消失したため要求せず中断")
            if role.startswith("uat-owner-") and result != "acquired":
                raise PermissionError("試験一次を確保できないため要求せず中断")
            if result == "acquired":
                (fixture / "initializing.json").write_text(
                    json.dumps(self.audit), encoding="utf-8"
                )
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

        def close(self, **kwargs):
            if self.notice_lease is not None:
                self.notice_lease.__exit__(None, None, None)
                self.notice_lease = None
            (fixture / "resource-audit.json").write_text(
                json.dumps(self.audit), encoding="utf-8"
            )
            super().close(**kwargs)

        def publish_state(self, state, ready):
            super().publish_state(state, ready)
            if ready:
                self.audit["snapshot"] = self._read_owner()
                self.audit["ready_tick"] = self.tick_ms()
                (fixture / "ready").write_text(json.dumps(self.audit), encoding="utf-8")

        def restore_window(self, hwnd, is_current=lambda: True):
            counts["restored"] += 1
            app = app_reference[0]
            status = app.status_var.get()
            if role.startswith(("focus-owner-", "uat-owner-")):
                app._focus_before()
            result = super().restore_window(hwnd, is_current=is_current)
            counts["status_preserved"] &= app.status_var.get() == status
            if role.startswith(("focus-owner-", "uat-owner-")):
                app._focus_after(result)
            return result

        def _foreground_window(self, hwnd, is_current):
            if role.startswith(("focus-owner-", "uat-owner-")):
                state = app_reference[0]._focus_state
                state["activated"] = hwnd
                handles = [
                    self._top_level_hwnd(w)
                    for w in self.focus_restorer.windows
                    if w.winfo_exists()
                ]
                state["native"] = self._owned_popup([h for h in handles if h])
            return super()._foreground_window(hwnd, is_current)

        def show_notice(self, reason):
            self.audit["notice_reason"] = reason
            if self.audit.get("guard_blocked"):
                raise AssertionError("接続先guardが要求を中断した")
            expected_file = fixture / "expected-owner.json"
            if expected_file.exists() and json.loads(expected_file.read_text()).get(
                "manual"
            ):
                return super().show_notice(reason)
            if role in {"notice-via-main", "api-denied"} or role.startswith(
                "notice-production-"
            ):
                return super().show_notice(reason)
            if role == "request-timeout":
                assert reason == "expired"
                return
            if role.startswith("simultaneous-") and reason == "expired":
                return
            raise AssertionError(f"正常tracerで失敗案内: {reason}")

        def display_notice(self, reason, text, lease):
            from pagefolio.startup_win32 import NativeNoticeLifetime, _bind

            notice = NativeNoticeLifetime(self, reason, text=text, lease=lease)
            expected_file = fixture / "expected-owner.json"
            manual = expected_file.exists() and json.loads(
                expected_file.read_text()
            ).get("manual")
            if role.startswith("notice-production-") or manual:
                foreground = _bind(self.api.u, "GetForegroundWindow", wt.HWND)
                self.audit["foreground_before"] = foreground()

                def visible(hwnd):
                    self.audit.update(
                        snapshot=lease.snapshot,
                        dpi=notice.dpi,
                        foreground_shown=foreground(),
                    )
                    (fixture / "ready").write_text(
                        json.dumps(self.audit), encoding="utf-8"
                    )

                notice.show(on_show=visible)
                self.audit.update(
                    closed_tick=self.tick_ms(), foreground_after=foreground()
                )
                self.audit.update(
                    foreground_before_show=notice.foreground_before_show,
                    foreground_after_show=notice.foreground_after_show,
                    foreground_before_close=notice.foreground_before_close,
                    foreground_after_close=notice.foreground_after_close,
                )
            else:
                notice.show(lifetime_ms=150)

    started = _tick_ms()
    try:
        if role.startswith("entry-"):
            from pagefolio import constants, startup_win32

            startup_win32.Win32Backend = Backend
            entry = (
                role.removeprefix("entry-owner-")
                if role.startswith("entry-owner-")
                else role.removeprefix("entry-")
            )
            if entry == "relocated":
                constants.APP_VERSION = "v99.test"
                assert Path(startup_win32.__file__).is_relative_to(
                    fixture / "alternate"
                )
                runpy.run_path(
                    str(fixture / "alternate" / "pagefolio.py"), run_name="__main__"
                )
            elif entry == "script":
                runpy.run_path(str(_ROOT / "pagefolio.py"), run_name="__main__")
            else:
                runpy.run_module("pagefolio", run_name="__main__")
            audit = backend_instances[-1].audit
            result = (
                "primary"
                if may_be_primary
                else audit.get("notice_reason", audit["terminal_result"])
            )
        else:
            result = main(backend_factory=Backend)
    except PermissionError:
        assert role == "api-denied"
        result = "api_denied"
    except RuntimeError as e:
        assert (
            role == "init-failure" and str(e) == "tracer-initialization-failure"
        ) or (role == "prepublish-failure" and str(e) == "tracer-prepublish-failure")
        result = "initialization_failed"
    if not may_be_primary:
        assert "pagefolio.app" not in sys.modules
    record = {**counts, "result": result, "elapsed": _tick_ms() - started}
    if role == "lifecycle-worker":
        (fixture / "worker-alive").touch()
        deadline = time.monotonic() + 8
        while not (fixture / "release-worker").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
    (fixture / "result.json").write_text(json.dumps(record), encoding="utf-8")
    print(json.dumps(record))


def _test_scenario_bootstrap(fixture, namespace, role):
    # 多数のlistenerスレッドのdumpで未読stderr pipeを詰まらせない。
    # 時限dumpは取り消さない。シナリオ完了後に終了処理（interpreter finalization）が
    # 止まった場合も、faulthandlerがfixtureへスタックを残す。fileはfaulthandlerが
    # 参照を保持し、interpreter終了時に取り消される。
    trace = (fixture / "traceback.log").open("w", encoding="utf-8")
    faulthandler.dump_traceback_later(10, repeat=True, file=trace)
    before = _fingerprints()
    try:
        _run_scenario(fixture, namespace, role)
    finally:
        assert _fingerprints() == before, "元設定/プロンプトが変更された"


def _uat_harness(argv):
    """明示実行専用。人の操作待ち・本番名は通常pytestへ収集しない。"""
    sys.path.insert(0, str(_ROOT))
    parser = argparse.ArgumentParser(description="隔離済みWindows受入の準備と観測")
    parser.add_argument(
        "action", choices=["start", "peer", "notice", "inspect", "stop"]
    )
    parser.add_argument("--run", type=Path)
    parser.add_argument(
        "--case",
        default="preview",
        choices=[
            "normal",
            "zoomed",
            "thumb",
            "preview",
            "settings",
            "nested",
            "native-ocr",
            "native-quit",
            "pdf",
            "ocr",
            "busy",
            "slowready",
        ],
    )
    parser.add_argument(
        "--entry", choices=["script", "module", "relocated"], default="module"
    )
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--namespace")
    args = parser.parse_args(argv)
    before = _fingerprints()
    from pagefolio.startup_win32 import Win32Backend, _bind

    def read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def save(path, value):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    try:
        if args.action in {"start", "notice"}:
            if args.action == "notice" and args.production:
                parser.error(
                    "noticeは試験nonceでのみ実行する。既存本番通知へ接続しない"
                )
            run = Path(
                tempfile.mkdtemp(
                    prefix="pagefolio-uat-", dir=_ROOT / ".planning" / "tmp"
                )
            )
            namespace = (
                "fixed-production" if args.production else args.namespace or uuid4().hex
            )
            backend = Win32Backend(None if args.production else namespace)
            try:
                if args.action == "start":
                    assert backend.claim(uuid4().hex) == "acquired", (
                        "既存owner検出。要求せず中断"
                    )
                environment = {
                    "os": str(sys.getwindowsversion()),
                    "python": sys.version,
                    "pointer_bits": ct.sizeof(wt.HANDLE) * 8,
                    "session_id": backend.session_id,
                    "sid": backend.sid,
                    "authentication_luid": backend.authentication_luid,
                    "foreground": _bind(
                        backend.api.u, "GetForegroundWindow", wt.HWND
                    )(),
                    "is_admin": bool(ct.windll.shell32.IsUserAnAdmin()),
                }
            finally:
                backend.close()
            import tkinter as tk

            interp = tk.Tcl()
            environment["tcl"] = str(interp.call("info", "patchlevel"))
            environment["tk"] = tk.TkVersion
            role = (
                "notice-case-production-owner"
                if args.action == "notice"
                else f"uat-owner-{args.case}"
            )
            child, fixture = _spawn(run, namespace, role, detached=True)
            git_executable = shutil.which("git")
            assert git_executable
            manifest = {
                "run": str(run),
                "namespace": namespace,
                "case": args.case,
                "role": role,
                "fixture": str(fixture),
                "launcher_pid": child.pid,
                "environment": environment,
                "originals_before": before,
                "source_commit": subprocess.check_output(  # noqa: S603
                    [git_executable, "rev-parse", "HEAD"], cwd=_ROOT, text=True
                ).strip(),
            }
            save(run / "manifest.json", manifest)
            marker = (
                "scenario-ready"
                if args.case in {"busy", "slowready"} and args.action == "start"
                else "focus-ready"
                if args.action == "start"
                else "ready"
            )
            _wait_file(child, fixture / marker)
            if args.action == "start":
                identity_path = fixture / "ready"
                if not identity_path.exists():
                    identity_path = fixture / "initializing.json"
                manifest["expected_owner"] = {
                    **read_json(identity_path),
                    "manual": True,
                }
                save(run / "manifest.json", manifest)
            print(json.dumps(manifest, ensure_ascii=False))
            return

        if args.run is None:
            parser.error("--runにはstart/noticeが出力したディレクトリを指定する")
        run = args.run.resolve()
        assert run.is_relative_to((_ROOT / ".planning" / "tmp").resolve())
        manifest = read_json(run / "manifest.json")
        fixture = Path(manifest["fixture"]).resolve()
        assert fixture.is_relative_to(run)
        assert _fingerprints() == manifest["originals_before"], "原本が変化。試験を中断"
        if args.action == "peer":
            if manifest["role"].startswith("notice-case-"):
                role, expected = "notice-case-peer-" + uuid4().hex, None
            else:
                role, expected = "entry-" + args.entry, manifest["expected_owner"]
            child, path = _spawn(
                run,
                manifest["namespace"],
                role,
                fixture_name="peer-" + uuid4().hex,
                expected_owner=expected,
            )
            try:
                # 本番5秒+10秒案内も有限待機。timeout後はこの子だけ回収する。
                out, err = child.communicate(timeout=18)
                (path / "stdout.log").write_text(out, encoding="utf-8")
                (path / "stderr.log").write_text(err, encoding="utf-8")
                assert child.returncode == 0, err
                result = read_json(path / "result.json")
                print(
                    json.dumps(
                        {"fixture": str(path), "result": result}, ensure_ascii=False
                    )
                )
            finally:
                _reclaim([child])
        elif args.action == "stop":
            assert not manifest["role"].startswith("notice-case-"), (
                "通知は実クリックまたは10秒で閉鎖する"
            )
            (fixture / "stop").touch()
            deadline = time.monotonic() + 8
            while (
                not (fixture / "result.json").exists() and time.monotonic() < deadline
            ):
                time.sleep(0.05)
            assert (fixture / "result.json").exists(), (
                "停止未完了。120秒の安全終了後inspectする"
            )
        if args.action in {"inspect", "stop"}:
            values = {
                "manifest": manifest,
                "originals_unchanged": _fingerprints() == before,
            }
            for name in (
                "ready",
                "resource-audit.json",
                "result.json",
                "focus-result.json",
                "busy-result.json",
            ):
                path = fixture / name
                if path.exists() and path.stat().st_size:
                    values[name] = read_json(path)
            save(run / "inspection.json", values)
            print(json.dumps(values, ensure_ascii=False))
    finally:
        assert _fingerprints() == before, "元設定/プロンプトが変更された"


if __name__ == "__main__":
    if sys.argv[1] == "--uat":
        _uat_harness(sys.argv[2:])
    else:
        assert sys.argv[1] == "_test_scenario_bootstrap"
        _test_scenario_bootstrap(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
