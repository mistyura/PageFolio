"""W05cの観測専用。入力・前面化・終了判断を行わない。"""

import ctypes as ct
import faulthandler
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
from ctypes import wintypes as wt
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_event(observer, hwnd, message, wparam, lparam, subclass_id, remove, forward):
    """I/OもTkも使わず、観測失敗時にも元WndProcへ委譲する。"""
    try:
        if message == 0x111 and wparam & 0xFFFF == 7:
            observer.emit("native_no", hwnd=hwnd)
        if message == 0x82:
            observer.emit("native_destroy", hwnd=hwnd)
            if not remove(hwnd, subclass_id):
                observer.emit("acquisition_error", error="RemoveWindowSubclass failed")
    except Exception as e:
        observer.errors.append(f"native: {type(e).__name__}: {e}")
    return forward(hwnd, message, wparam, lparam)


def save(path, value):
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    pending.replace(path)


def checkpoint(run, manifest, answer_path, stage):
    """既存ownerへ観測だけを依頼。失敗時も証拠を保存し、再試行しない。"""
    from pagefolio.startup_win32 import Win32Backend

    fixture = Path(manifest["fixture"])
    expected = manifest["expected_owner"]
    assert manifest["case"] == "native-quit" and expected["manual"] is True
    assert fixture == run / "uat-owner-native-quit"
    assert stage in {"before_peer", "before_stop"}
    target = run / f"w05c-check-{stage}.json"
    assert not target.exists(), "同じ段階の自動再試行は禁止"
    answer = json.loads(answer_path.read_text(encoding="utf-8"))
    assert answer["entry"] == "script", "新候補はscriptだけ"
    request = {"request_id": uuid4().hex, "stage": stage}
    backend = Win32Backend(
        None if manifest["namespace"] == "fixed-production" else manifest["namespace"]
    )
    try:
        with backend._validate_peer(expected["pid"], expected["process_created"]):
            save(fixture / "w05c-snapshot-request.json", request)
        deadline = time.monotonic() + 3
        snapshot = None
        while time.monotonic() < deadline:
            source = fixture / "w05c-pre-collection.json"
            if source.exists():
                value = json.loads(source.read_text(encoding="utf-8"))
                if value["request_id"] == request["request_id"]:
                    snapshot = value
                    break
            time.sleep(0.02)
        assert snapshot is not None, "回収前snapshot応答なし"
        lines = (fixture / "w05c-events.jsonl").read_bytes().splitlines(keepends=True)
        prefix = b"".join(lines[: snapshot["events"]])
        assert hashlib.sha256(prefix).hexdigest() == snapshot["log_sha256"]
        events = [json.loads(line) for line in lines[: snapshot["events"]]]
        identity = {
            "run_id": run.name,
            "pid": expected["pid"],
            "process_created": expected["process_created"],
            "entry": answer["entry"],
            "manual": True,
            "diagnostic_only": manifest.get("diagnostic_only", False),
            "peers": answer["peers"],
        }
        node = shutil.which("node")
        assert node
        validator = (
            Path(__file__).resolve().parents[1]
            / ".planning/phases/06-release-validation/06-05-w05c-evidence.cjs"
        )
        result = subprocess.run(  # noqa: S603 — 固定のvalidatorへJSONをstdinで渡す。
            [node, str(validator)],
            input=json.dumps(
                {
                    "events": events,
                    "snapshot": snapshot,
                    "answer": answer,
                    "identity": identity,
                    "stage": stage,
                }
            ),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        record = {
            "ok": result.returncode == 0,
            "run_id": run.name,
            "snapshot": snapshot,
            "answer_path": str(answer_path.resolve()),
            "answer_sha256": digest(answer_path),
            "answer_record": {k: v for k, v in answer.items() if k != "peers"},
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        save(target, record)
        assert record["ok"], result.stderr
        return record
    except Exception as e:
        if not target.exists():
            save(
                target,
                {"ok": False, "run_id": run.name, "error": f"{type(e).__name__}: {e}"},
            )
        raise
    finally:
        backend.close()


def preserve(run, fixture, stage):
    """stop以前/以後を別の変更禁止ディレクトリに保存する。"""
    dest = run / ("w05c-collection-" + stage)
    dest.mkdir()
    files = {}
    for source in sorted(fixture.iterdir()):
        if source.is_file():
            target = dest / source.name
            data = source.read_bytes()
            target.write_bytes(data)
            files[source.name] = hashlib.sha256(data).hexdigest()
    save(
        dest / "copies.json",
        {"run_id": run.name, "utc": datetime.now(UTC).isoformat(), "files": files},
    )
    return dest


def collect(run, manifest):
    """識別済みの同じrunだけを既存stopで回収する。期限は延長しない。"""
    from pagefolio.startup_win32 import Win32Backend, _bind

    fixture = Path(manifest["fixture"])
    expected = manifest["expected_owner"]
    backend = Win32Backend(
        None if manifest["namespace"] == "fixed-production" else manifest["namespace"]
    )
    try:
        with backend._validate_peer(
            expected["pid"], expected["process_created"], allow_exited=True
        ) as process:
            # マーカー欠落時にも最新snapshotを要求し、採取不能自体を残す。
            if not any(
                (run / name).exists()
                for name in ("w05c-check-before_stop.json", "w05c-v3-before_stop.json")
            ):
                request = {"request_id": uuid4().hex, "stage": "failed-before-stop"}
                save(fixture / "w05c-snapshot-request.json", request)
                snapshot_deadline = time.monotonic() + 1
                while time.monotonic() < snapshot_deadline:
                    snapshot_path = fixture / "w05c-pre-collection.json"
                    if (
                        snapshot_path.exists()
                        and json.loads(snapshot_path.read_text(encoding="utf-8"))[
                            "request_id"
                        ]
                        == request["request_id"]
                    ):
                        break
                    time.sleep(0.02)
            before = preserve(run, fixture, "before")
            foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)()
            save(
                before / "owner.json",
                {
                    "pid": expected["pid"],
                    "process_created": expected["process_created"],
                    "foreground": foreground,
                    "foreground_identity": window_identity(backend, foreground),
                    "utc": datetime.now(UTC).isoformat(),
                    "already_exited": backend._process_has_exited(process),
                    "windows": native_windows(backend, expected["pid"]),
                },
            )
            (fixture / "stop").touch()
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and not backend._process_has_exited(
                process
            ):
                time.sleep(0.02)
            after = preserve(run, fixture, "after")
            exited = backend._process_has_exited(process)
            save(
                after / "owner.json",
                {
                    "pid": expected["pid"],
                    "process_created": expected["process_created"],
                    "exited": exited,
                    "utc": datetime.now(UTC).isoformat(),
                },
            )
            assert exited, "同ownerの停止未完了。再起動せず証拠を保持する"
    finally:
        backend.close()


def native_windows(backend, pid):
    """別processから窓を読取する。前面化・入力APIは使わない。"""
    from pagefolio.startup_win32 import _bind

    found = []
    callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    visible = _bind(backend.api.u, "IsWindowVisible", wt.BOOL, wt.HWND)
    get_class = _bind(
        backend.api.u, "GetClassNameW", ct.c_int, wt.HWND, wt.LPWSTR, ct.c_int
    )

    def visit(hwnd, data):
        identity = window_identity(backend, hwnd)
        if identity["pid"] == pid:
            text = ct.create_unicode_buffer(256)
            get_class(hwnd, text, 256)
            found.append(
                {"hwnd": hwnd, "class": text.value, "visible": bool(visible(hwnd))}
            )
        return True

    callback = callback_type(visit)
    enum = _bind(backend.api.u, "EnumWindows", wt.BOOL, callback_type, wt.LPARAM)
    if not enum(callback, 0):
        raise OSError(ct.get_last_error(), "EnumWindows failed")
    return found


def window_identity(backend, hwnd):
    pid = wt.DWORD()
    thread = backend.api.GetWindowThreadProcessId(hwnd, ct.byref(pid)) if hwnd else 0
    return {"pid": pid.value, "thread": thread}


class QuitEvidence:
    """native callbackではメモリへ追記するだけ。Tk側のtimerで書き出す。"""

    def __init__(self, fixture, identity):
        self.fixture = fixture
        self.identity = {"run_id": fixture.parent.name, **identity}
        self.events = []
        self.written = 0
        self.errors = []
        self.hwnd = 0
        self.closed = False
        self.started = time.monotonic()

    def emit(self, event, **details):
        self.events.append(
            {
                **self.identity,
                "seq": len(self.events) + 1,
                "utc": datetime.now(UTC).isoformat(),
                "monotonic": time.monotonic(),
                "event": event,
                "hwnd": self.hwnd,
                **details,
            }
        )

    def flush(self):
        try:
            if self.written < len(self.events):
                batch = self.events[self.written :]
                with (self.fixture / "w05c-events.jsonl").open(
                    "a", encoding="utf-8", newline="\n"
                ) as stream:
                    stream.write("".join(json.dumps(e) + "\n" for e in batch))
                self.written += len(batch)
        except Exception as e:
            self.errors.append(f"flush: {type(e).__name__}: {e}")

    def close(self):
        if self.closed:
            return
        self.emit("observer_closed")
        self.flush()
        path = self.fixture / "w05c-events.jsonl"
        try:
            log_hash = digest(path)
        except Exception as e:
            self.errors.append(f"final hash: {type(e).__name__}: {e}")
            log_hash = None
        record = json.dumps(
            {
                **self.identity,
                "events": len(self.events),
                "written": self.written,
                "pending": len(self.events) - self.written,
                "errors": self.errors,
                "sha256": log_hash,
            }
        )
        try:
            (self.fixture / "w05c-observer-final.json").write_text(
                record, encoding="utf-8"
            )
        except Exception as e:
            # 元処理の例外を計測保存の例外で置き換えない。final欠落はhelperが拒否する。
            self.errors.append(f"final write: {type(e).__name__}: {e}")
        self.closed = True

    def state(self, app):
        if any(e["event"] == "root_destroy_return" for e in self.events):
            return {"root_alive": False}
        try:
            doc = app.doc
            return {
                "root_alive": bool(app.root.winfo_exists()),
                "pages": len(doc) if doc else 0,
                "rotations": [p.rotation for p in doc] if doc else [],
                "undo": len(app._undo_stack),
                "redo": len(app._redo_stack),
            }
        except Exception as e:
            self.emit("acquisition_error", error=f"{type(e).__name__}: {e}")
            return {"error": str(e)}

    def wrap(self, function, event, app=None):
        def observed(*args, **kwargs):
            self.emit(
                event + "_enter", state=self.state(app) if app is not None else None
            )
            try:
                result = function(*args, **kwargs)
            except Exception as e:
                self.emit(event + "_error", error=f"{type(e).__name__}: {e}")
                raise
            self.emit(
                event + "_return",
                result=result if isinstance(result, (bool, int, str)) else None,
                state=self.state(app) if app is not None else None,
            )
            return result

        return observed

    def snapshot(self, app, request):
        """元readyのマーカーと同時点の編集状態を回収前に固定する。"""
        marker = self.fixture / "quit-cancelled"
        value = {
            **self.identity,
            "request_id": request["request_id"],
            "state": self.state(app),
            "marker": marker.exists(),
            "marker_sha256": digest(marker) if marker.exists() else None,
            "stop": (self.fixture / "stop").exists(),
            "stop_all": (self.fixture.parent / "stop-all").exists(),
            "elapsed": time.monotonic() - self.started,
        }
        self.emit(
            "pre_collection",
            **{k: v for k, v in value.items() if k not in self.identity},
        )
        self.flush()
        with (self.fixture / "w05c-pre-collection-stack.log").open(
            "w", encoding="utf-8"
        ) as stream:
            faulthandler.dump_traceback(file=stream, all_threads=True)
        value.update(
            events=self.written,
            errors=list(self.errors),
            log_sha256=digest(self.fixture / "w05c-events.jsonl"),
        )
        save(self.fixture / "w05c-pre-collection.json", value)


def install(app, fixture, backend):
    """同一ownerのTk thread内だけでpopup subclassを登録する。"""
    from tkinter import messagebox

    from pagefolio.startup_win32 import _bind

    observer = QuitEvidence(
        fixture,
        {
            "pid": os.getpid(),
            "process_created": backend._created(backend.api.GetCurrentProcess()),
        },
    )
    plan_path = fixture / "w05c-plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        observer.identity.update(schema="w05c-v3", plan_sha256=plan["plan_sha256"])
    root = app.root
    app._w05c_evidence = observer
    messagebox.askyesno = observer.wrap(messagebox.askyesno, "ask", app)
    app._quit = observer.wrap(app._quit, "quit", app)
    app._focus_cleanup = observer.wrap(app._focus_cleanup, "cleanup", app)
    root.destroy = observer.wrap(root.destroy, "root_destroy")
    original_error = root.report_callback_exception

    def report_error(kind, value, tb):
        observer.emit(
            "tk_error", traceback="".join(traceback.format_exception(kind, value, tb))
        )
        original_error(kind, value, tb)

    root.report_callback_exception = report_error
    comctl = ct.WinDLL("comctl32", use_last_error=True)
    callback_type = ct.WINFUNCTYPE(
        ct.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, ct.c_size_t, ct.c_size_t
    )
    set_subclass = _bind(
        comctl,
        "SetWindowSubclass",
        wt.BOOL,
        wt.HWND,
        callback_type,
        ct.c_size_t,
        ct.c_size_t,
    )
    remove = _bind(
        comctl, "RemoveWindowSubclass", wt.BOOL, wt.HWND, callback_type, ct.c_size_t
    )
    forward = _bind(
        comctl, "DefSubclassProc", ct.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
    )

    def native(hwnd, message, wparam, lparam, subclass_id, data):
        return native_event(
            observer,
            hwnd,
            message,
            wparam,
            lparam,
            subclass_id,
            lambda window, sid: remove(window, callback, sid),
            forward,
        )

    callback = callback_type(native)
    observer.callback = callback  # native側が使う間は強参照を維持する。
    observed = set()
    requests = set()

    def poll():
        try:
            hwnd = backend._owned_popup([backend._top_level_hwnd(root)])
            if hwnd and hwnd not in observed:
                observer.hwnd = hwnd
                if not set_subclass(hwnd, callback, 905, 0):
                    raise OSError(ct.get_last_error(), "SetWindowSubclass failed")
                observed.add(hwnd)
                observer.emit("native_shown", hwnd=hwnd)
            for label in (
                "during_confirm",
                "after_no" if plan_path.exists() else "after_answer",
            ):
                peer_path = fixture / f"w05c-peer-{label}.json"
                if peer_path.exists() and label not in requests:
                    peer = json.loads(peer_path.read_text(encoding="utf-8"))
                    requests.add(label)
                    observer.emit("peer_" + label, peer=peer)
            request_path = fixture / "w05c-snapshot-request.json"
            if request_path.exists():
                request = json.loads(request_path.read_text(encoding="utf-8"))
                if request["request_id"] not in requests:
                    requests.add(request["request_id"])
                    observer.snapshot(app, request)
        except Exception as e:
            observer.emit("acquisition_error", error=f"{type(e).__name__}: {e}")
        observer.flush()
        if not observer.closed:
            root.after(50, poll)

    observer.emit("observer_started", state=observer.state(app))
    if plan_path.exists():
        observer.emit("watchdog_registered", **app._w05c_watchdog)
    root.after(50, poll)
    return observer
