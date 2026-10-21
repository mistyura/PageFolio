"""Windows 起動制御の実プロセス tracer（UAC・操作待ちは通常収集しない）。"""

import ctypes as ct
import hashlib
import importlib.util
import json
import logging
import os
import runpy
import shutil
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
    if role == "entry-relocated":
        shutil.copytree(
            _ROOT / "pagefolio",
            fixture / "alternate" / "pagefolio",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copyfile(_ROOT / "pagefolio.py", fixture / "alternate" / "pagefolio.py")
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


def _reclaim(children):
    """この試験が生成したPIDだけをfinallyで回収する。"""
    for child in children:
        if child.poll() is None:
            child.kill()
        child.communicate()


@pytest.mark.parametrize("count", [2, 8])
def test_simultaneous_real_processes_construct_one_editor(tmp_path, count):
    namespace = uuid4().hex
    children = [_spawn(tmp_path, namespace, f"simultaneous-{i}") for i in range(count)]
    try:
        deadline = time.monotonic() + 8
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
        (tmp_path / "stop-all").touch()
        results = [_finish(child) for child, _ in children]
        assert sum(r["constructed"] for r in results) == 1
        assert sum(r["result"] == "primary" for r in results) == 1
        assert all(
            r["result"] in {"primary", "completed", "foreground_denied"}
            for r in results
        )
    finally:
        _reclaim([child for child, _ in children])


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
        assert measured["focus_correct"]
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


def _prepare_focus_case(app, fixture, case):
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
            assert release.wait(6), "OCR解除の期限切れ"
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
            "focus_correct": result != "completed"
            or state["focus"] is None
            or root.focus_get() is state["focus"],
        }
        (fixture / "focus-result.json").write_text(json.dumps(record))
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
        0, str(fixture / "alternate") if role == "entry-relocated" else str(_ROOT)
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
    backend_instances = []
    may_be_primary = role in {
        "owner",
        "manual-owner",
        "init-failure",
    } or role.startswith(("simultaneous-", "takeover-", "lifecycle-", "focus-owner-"))
    if may_be_primary:
        from pagefolio import app as app_module

        class TracedApp(app_module.PDFEditorApp):
            def __init__(self, root):
                counts["constructed"] += 1
                if role == "init-failure":
                    raise RuntimeError("tracer-initialization-failure")
                super().__init__(root)
                app_reference.append(self)
                if role.startswith("focus-owner-"):
                    root.after(
                        150,
                        lambda: _prepare_focus_case(
                            self, fixture, role.removeprefix("focus-owner-")
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
                    if (fixture / "stop").exists() or (
                        fixture.parent / "stop-all"
                    ).exists():
                        if role.startswith("focus-owner-"):
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
                root.after(120000 if role == "manual-owner" else 10000, self._quit)

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
            process = super()._observe_owner(owner)
            if role.startswith("takeover-"):
                (fixture / "observed").touch()
            return process

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
                (fixture / "ready").write_text(json.dumps(self.audit), encoding="utf-8")

        def restore_window(self, hwnd, is_current=lambda: True):
            counts["restored"] += 1
            app = app_reference[0]
            status = app.status_var.get()
            if role.startswith("focus-owner-"):
                app._focus_before()
            result = super().restore_window(hwnd, is_current=is_current)
            counts["status_preserved"] &= app.status_var.get() == status
            if role.startswith("focus-owner-"):
                app._focus_after(result)
            return result

        def _foreground_window(self, hwnd, is_current):
            if role.startswith("focus-owner-"):
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
            if role in {"notice-via-main", "api-denied"}:
                return super().show_notice(reason)
            if role == "request-timeout":
                assert reason == "expired"
                return
            raise AssertionError(f"正常tracerで失敗案内: {reason}")

        def display_notice(self, reason, text, lease):
            from pagefolio.startup_win32 import NativeNoticeLifetime

            NativeNoticeLifetime(self, reason, text=text).show(lifetime_ms=150)

    started = _tick_ms()
    try:
        if role.startswith("entry-"):
            from pagefolio import constants, startup_win32

            startup_win32.Win32Backend = Backend
            if role == "entry-relocated":
                constants.APP_VERSION = "v99.test"
                assert Path(startup_win32.__file__).is_relative_to(
                    fixture / "alternate"
                )
                runpy.run_path(
                    str(fixture / "alternate" / "pagefolio.py"), run_name="__main__"
                )
            elif role == "entry-script":
                runpy.run_path(str(_ROOT / "pagefolio.py"), run_name="__main__")
            else:
                runpy.run_module("pagefolio", run_name="__main__")
            result = backend_instances[-1].audit["terminal_result"]
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
    before = _fingerprints()
    try:
        _run_scenario(fixture, namespace, role)
    finally:
        assert _fingerprints() == before, "元設定/プロンプトが変更された"


if __name__ == "__main__":
    assert sys.argv[1] == "_test_scenario_bootstrap"
    _test_scenario_bootstrap(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
