"""起動制御の型付き Win32 境界。import 時には DLL をロードしない。"""

import ctypes as ct
import hashlib
import json
import logging
import os
import struct
import threading
import time
from contextlib import nullcontext
from ctypes import wintypes as wt
from uuid import uuid4

INVALID_HANDLE_VALUE = ct.c_void_p(-1).value
SYNCHRONIZE = 0x100000
READ_CONTROL = 0x20000
OWNER_ACCESS = SYNCHRONIZE | READ_CONTROL | 1
WAIT_TIMEOUT = 258
ERROR_IO_PENDING = 997
ERROR_IO_INCOMPLETE = 996
ERROR_OPERATION_ABORTED = 995
_pending_io_quarantine = []
_quarantine_lock = threading.Lock()
_io_slots = threading.BoundedSemaphore(32)
_notice_lifetime_quarantine = []
_shutdown_owner_quarantine = []


class SECURITY_ATTRIBUTES(ct.Structure):
    _fields_ = [
        ("nLength", wt.DWORD),
        ("lpSecurityDescriptor", wt.LPVOID),
        ("bInheritHandle", wt.BOOL),
    ]


class OVERLAPPED(ct.Structure):
    _fields_ = [
        ("Internal", ct.c_size_t),
        ("InternalHigh", ct.c_size_t),
        ("Offset", wt.DWORD),
        ("OffsetHigh", wt.DWORD),
        ("hEvent", wt.HANDLE),
    ]


class SID_AND_ATTRIBUTES(ct.Structure):
    _fields_ = [("Sid", wt.LPVOID), ("Attributes", wt.DWORD)]


class GUITHREADINFO(ct.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("flags", wt.DWORD),
        ("hwndActive", wt.HWND),
        ("hwndFocus", wt.HWND),
        ("hwndCapture", wt.HWND),
        ("hwndMenuOwner", wt.HWND),
        ("hwndMoveSize", wt.HWND),
        ("hwndCaret", wt.HWND),
        ("rcCaret", wt.RECT),
    ]


def _bind(dll, name, result, *args):
    function = getattr(dll, name)
    function.restype = result
    function.argtypes = list(args)
    return function


class _API:
    def __init__(self):
        self.k = ct.WinDLL("kernel32", use_last_error=True)
        self.a = ct.WinDLL("advapi32", use_last_error=True)
        self.u = ct.WinDLL("user32", use_last_error=True)
        h, d, p, b = wt.HANDLE, wt.DWORD, wt.LPVOID, wt.BOOL
        pd = ct.POINTER(d)
        sa = ct.POINTER(SECURITY_ATTRIBUTES)
        ov = ct.POINTER(OVERLAPPED)
        for name, result, args in [
            ("CloseHandle", b, [h]),
            ("LocalFree", p, [p]),
            ("CreateMutexExW", h, [sa, wt.LPCWSTR, d, d]),
            ("WaitForSingleObject", d, [h, d]),
            ("ReleaseMutex", b, [h]),
            ("CreateEventW", h, [sa, b, b, wt.LPCWSTR]),
            ("CreateFileMappingW", h, [h, sa, d, d, d, wt.LPCWSTR]),
            ("OpenFileMappingW", h, [d, b, wt.LPCWSTR]),
            ("MapViewOfFile", p, [h, d, d, d, ct.c_size_t]),
            ("UnmapViewOfFile", b, [p]),
            ("GetTickCount64", ct.c_ulonglong, []),
            ("OpenProcess", h, [d, b, d]),
            ("GetCurrentProcess", h, []),
            ("GetProcessTimes", b, [h, p, p, p, p]),
            ("ProcessIdToSessionId", b, [d, pd]),
            ("CreateNamedPipeW", h, [wt.LPCWSTR, d, d, d, d, d, d, sa]),
            ("CreateFileW", h, [wt.LPCWSTR, d, d, sa, d, d, h]),
            ("ConnectNamedPipe", b, [h, ov]),
            ("DisconnectNamedPipe", b, [h]),
            ("ReadFile", b, [h, p, d, pd, ov]),
            ("WriteFile", b, [h, p, d, pd, ov]),
            ("CancelIoEx", b, [h, ov]),
            ("GetOverlappedResult", b, [h, ov, pd, b]),
            ("GetNamedPipeClientProcessId", b, [h, pd]),
            ("GetNamedPipeServerProcessId", b, [h, pd]),
        ]:
            setattr(self, name, _bind(self.k, name, result, *args))
        for name, result, args in [
            ("OpenProcessToken", b, [h, d, ct.POINTER(h)]),
            ("GetTokenInformation", b, [h, ct.c_int, p, d, pd]),
            ("ConvertSidToStringSidW", b, [p, ct.POINTER(wt.LPWSTR)]),
            (
                "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                b,
                [wt.LPCWSTR, d, ct.POINTER(p), pd],
            ),
            ("GetSecurityInfo", d, [h, ct.c_int, d, p, p, p, p, ct.POINTER(p)]),
            (
                "ConvertSecurityDescriptorToStringSecurityDescriptorW",
                b,
                [p, d, d, ct.POINTER(wt.LPWSTR), pd],
            ),
        ]:
            setattr(self, name, _bind(self.a, name, result, *args))
        self.AllowSetForegroundWindow = _bind(self.u, "AllowSetForegroundWindow", b, d)
        self.SetForegroundWindow = _bind(self.u, "SetForegroundWindow", b, wt.HWND)
        self.GetAncestor = _bind(self.u, "GetAncestor", wt.HWND, wt.HWND, wt.UINT)
        for name, result, args in [
            ("IsWindow", b, [wt.HWND]),
            ("IsWindowVisible", b, [wt.HWND]),
            ("IsWindowEnabled", b, [wt.HWND]),
            ("IsIconic", b, [wt.HWND]),
            ("ShowWindow", b, [wt.HWND, ct.c_int]),
            ("GetWindowThreadProcessId", d, [wt.HWND, pd]),
            ("GetClassNameW", ct.c_int, [wt.HWND, wt.LPWSTR, ct.c_int]),
            ("GetWindow", wt.HWND, [wt.HWND, wt.UINT]),
            ("GetLastActivePopup", wt.HWND, [wt.HWND]),
            ("GetGUIThreadInfo", b, [d, ct.POINTER(GUITHREADINFO)]),
        ]:
            setattr(self, name, _bind(self.u, name, result, *args))


def _check(value):
    if value is None or value == 0 or value == INVALID_HANDLE_VALUE:
        raise ct.WinError(ct.get_last_error())
    return value


class OwnedHandle:
    def __init__(self, api, value):
        self.api = api
        self.value = _check(value)

    def close(self):
        if self.value is not None:
            with _quarantine_lock:
                if any(p.pipe is self for p in _pending_io_quarantine):
                    return
            _check(self.api.CloseHandle(self.value))
            self.value = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _token(api, process):
    token = wt.HANDLE()
    _check(api.OpenProcessToken(process, 8, ct.byref(token)))
    with OwnedHandle(api, token.value) as handle:
        size = wt.DWORD()
        api.GetTokenInformation(handle.value, 2, None, 0, ct.byref(size))
        groups = ct.create_string_buffer(size.value)
        _check(api.GetTokenInformation(handle.value, 2, groups, size, ct.byref(size)))
        count = ct.cast(groups, ct.POINTER(wt.DWORD)).contents.value
        offset = ct.sizeof(wt.DWORD) + ct.alignment(SID_AND_ATTRIBUTES) - 1
        offset -= offset % ct.alignment(SID_AND_ATTRIBUTES)
        entries = (SID_AND_ATTRIBUTES * count).from_buffer(groups, offset)
        sid = None
        for entry in entries:
            if entry.Attributes & 0xC0000000 == 0xC0000000:
                text = wt.LPWSTR()
                _check(api.ConvertSidToStringSidW(entry.Sid, ct.byref(text)))
                try:
                    sid = text.value
                finally:
                    api.LocalFree(text)
        if sid is None:
            raise OSError("logon SID を確認できない")
        api.GetTokenInformation(handle.value, 10, None, 0, ct.byref(size))
        stats = ct.create_string_buffer(size.value)
        _check(api.GetTokenInformation(handle.value, 10, stats, size, ct.byref(size)))
        authentication_luid = struct.unpack_from("<Q", stats.raw, 8)[0]
        return sid, authentication_luid


class _Security:
    def __init__(self, api, sid, rights):
        self.api = api
        self.descriptor = wt.LPVOID()
        self.sddl = f"D:P(A;;0x{rights:x};;;{sid})(A;;0x{rights:x};;;SY)S:(ML;;NW;;;ME)"
        _check(
            api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                self.sddl, 1, ct.byref(self.descriptor), None
            )
        )
        self.attributes = SECURITY_ATTRIBUTES(
            ct.sizeof(SECURITY_ATTRIBUTES), self.descriptor, False
        )

    def close(self):
        if self.descriptor:
            self.api.LocalFree(self.descriptor)
            self.descriptor = wt.LPVOID()


def _security_descriptor(api, sid, rights):
    return _Security(api, sid, rights)


def _validate_acl(api, handle, expected, object_type=6):
    """既存オブジェクトの DACL を正規化した SDDL で厳密比較する。"""
    descriptor = wt.LPVOID()
    error = api.GetSecurityInfo(
        handle, object_type, 4 | 0x10, None, None, None, None, ct.byref(descriptor)
    )
    if error:
        raise ct.WinError(error)
    text = wt.LPWSTR()
    try:
        _check(
            api.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, 4 | 0x10, ct.byref(text), None
            )
        )
        wanted = expected.sddl.split("S:", 1)[0]
        # Win32 は数値権限を別名（RC/SY等）に正規化するため両方を同APIへ渡す。
        normalized = wt.LPWSTR()
        _check(
            api.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                expected.descriptor, 1, 4 | 0x10, ct.byref(normalized), None
            )
        )
        try:
            if text.value.replace("S:AI(", "S:(") != normalized.value:
                raise PermissionError(f"想定外のDACL: {wanted.split('(')[0]}")
        finally:
            api.LocalFree(normalized)
    finally:
        if text:
            api.LocalFree(text)
        api.LocalFree(descriptor)


def _tick_ms(api=None):
    return (api or _API()).GetTickCount64()


class PendingIO:
    """overlapped、event、buffer、pipe を完了まで一体で保持する。"""

    def __init__(self, api, pipe, buffer=None):
        if not _io_slots.acquire(blocking=False):
            raise OSError("未完了I/O上限のため受付停止")
        self.api = api
        self.pipe = pipe
        self.buffer = buffer
        try:
            self.event = OwnedHandle(api, api.CreateEventW(None, True, False, None))
        except Exception as e:
            _io_slots.release()
            raise e
        self.overlapped = OVERLAPPED()
        self.overlapped.hEvent = self.event.value
        self.completed = False

    def complete(self):
        if not self.completed:
            self.completed = True
            self.event.close()
            _io_slots.release()

    def finish(self, deadline):
        remaining = max(0, deadline - _tick_ms(self.api))
        wait = self.api.WaitForSingleObject(self.event.value, remaining)
        if wait == WAIT_TIMEOUT:
            self.cancel()
            raise TimeoutError("起動通信の期限切れ")
        if wait != 0:
            self.cancel()
            raise ct.WinError(ct.get_last_error())
        count = wt.DWORD()
        success = self.api.GetOverlappedResult(
            self.pipe.value, ct.byref(self.overlapped), ct.byref(count), False
        )
        error = ct.get_last_error()
        if success or error == ERROR_OPERATION_ABORTED:
            self.complete()
        if not success:
            raise ct.WinError(error)
        return count.value

    def cancel(self):
        if self.completed:
            return
        self.api.CancelIoEx(self.pipe.value, ct.byref(self.overlapped))
        deadline = _tick_ms(self.api) + 500
        while True:
            count = wt.DWORD()
            success = self.api.GetOverlappedResult(
                self.pipe.value, ct.byref(self.overlapped), ct.byref(count), False
            )
            error = ct.get_last_error()
            if success or error == ERROR_OPERATION_ABORTED:
                self.complete()
                return
            if _tick_ms(self.api) >= deadline:
                with _quarantine_lock:
                    _pending_io_quarantine.append(self)
                _start_reaper()
                return
            time.sleep(0.005)


_reaper = None


def _start_reaper():
    global _reaper
    with _quarantine_lock:
        if _reaper is not None and _reaper.is_alive():
            return
        _reaper = threading.Thread(target=_reap, daemon=True, name="startup-io-reaper")
        _reaper.start()


def _reap():
    global _reaper
    while True:
        with _quarantine_lock:
            items = tuple(_pending_io_quarantine)
            if not items:
                _reaper = None
                return
        for pending in items:
            count = wt.DWORD()
            success = pending.api.GetOverlappedResult(
                pending.pipe.value, ct.byref(pending.overlapped), ct.byref(count), False
            )
            if success or ct.get_last_error() == ERROR_OPERATION_ABORTED:
                pending.complete()
                with _quarantine_lock:
                    _pending_io_quarantine.remove(pending)
                pending.pipe.close()
        time.sleep(0.05)


def _io(api, pipe, operation, deadline, data=None, size=0):
    if _tick_ms(api) >= deadline:
        raise TimeoutError("起動通信の期限切れ")
    buffer = (
        ct.create_string_buffer(data)
        if data is not None
        else ct.create_string_buffer(size)
    )
    pending = PendingIO(api, pipe, buffer)
    count = wt.DWORD()
    function = api.WriteFile if operation == "write" else api.ReadFile
    success = function(
        pipe.value,
        buffer,
        len(data) if data is not None else size,
        ct.byref(count),
        ct.byref(pending.overlapped),
    )
    if not success and ct.get_last_error() != ERROR_IO_PENDING:
        error = ct.get_last_error()
        pending.complete()
        raise ct.WinError(error)
    length = pending.finish(deadline)
    return length if operation == "write" else buffer.raw[:length]


def _read_exact(api, pipe, size, deadline):
    chunks = bytearray()
    while len(chunks) < size:
        data = _io(api, pipe, "read", deadline, size=size - len(chunks))
        if not data:
            raise EOFError("pipe が閉じた")
        chunks.extend(data)
    return bytes(chunks)


def _read_frame(api, pipe, deadline):
    size = struct.unpack("<I", _read_exact(api, pipe, 4, deadline))[0]
    if not 0 < size <= 1024:
        raise ValueError("起動要求サイズが不正")
    result = json.loads(_read_exact(api, pipe, size, deadline).decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("起動要求の形式が不正")
    return result


def _write_frame(api, pipe, data, deadline):
    payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
    if not 0 < len(payload) <= 1024:
        raise ValueError("起動要求サイズが不正")
    wire = struct.pack("<I", len(payload)) + payload
    offset = 0
    while offset < len(wire):
        length = _io(api, pipe, "write", deadline, data=wire[offset:])
        if not length:
            raise EOFError("pipe が閉じた")
        offset += length


class Win32Backend:
    def __init__(self, namespace=None):
        self.api = _API()
        self.logger = logging.getLogger(__name__)
        self.owner_thread = threading.get_ident()
        self.sid, self.authentication_luid = _token(
            self.api, self.api.GetCurrentProcess()
        )
        self.pid = os.getpid()
        self.session_id = self._session(self.pid)
        self.prefix = "PageFolio.Startup" + (f".Test.{namespace}" if namespace else "")
        self.owner_name = "Local\\" + self.prefix + ".Owner"
        self.state_name = "Local\\" + self.prefix + ".State"
        self.owner = None
        self.mapping = None
        self.view = None
        self.owns_mutex = False
        self.generation = None
        self.sequence = 0
        self.stop = threading.Event()
        self.workers = []
        self.pipes = []
        self.peer_handles = []
        self.observed_owner = None
        self.observed_process = None
        self.takeover_callback = lambda deadline: False
        self.state = "initializing"
        self.release_generation = None
        self._closed = False
        self.owner_security = _security_descriptor(self.api, self.sid, OWNER_ACCESS)
        self.mapping_security = _security_descriptor(
            self.api, self.sid, READ_CONTROL | 6
        )
        self.pipe_security = _security_descriptor(self.api, self.sid, 0x12019F)

    def tick_ms(self):
        return _tick_ms(self.api)

    def _session(self, pid):
        session = wt.DWORD()
        _check(self.api.ProcessIdToSessionId(pid, ct.byref(session)))
        return session.value

    def _created(self, process):
        times = [ct.c_ulonglong() for _ in range(4)]
        _check(self.api.GetProcessTimes(process, *(ct.byref(t) for t in times)))
        return times[0].value

    def _validate_peer(self, pid, created=None, *, allow_exited=False):
        process = OwnedHandle(
            self.api, self.api.OpenProcess(SYNCHRONIZE | 0x1000, False, pid)
        )
        try:
            if (
                self._session(pid) != self.session_id
                or _token(self.api, process.value)[0] != self.sid
                or (created is not None and self._created(process.value) != created)
                or self.api.WaitForSingleObject(process.value, 0)
                not in ({0, WAIT_TIMEOUT} if allow_exited else {WAIT_TIMEOUT})
            ):
                raise PermissionError("起動相手の識別に失敗")
            return process
        except Exception as e:
            process.close()
            raise e

    def claim(self, generation):
        self._assert_thread()
        self.owner = OwnedHandle(
            self.api,
            self.api.CreateMutexExW(
                ct.byref(self.owner_security.attributes),
                self.owner_name,
                0,
                OWNER_ACCESS,
            ),
        )
        _validate_acl(self.api, self.owner.value, self.owner_security)
        result = self.api.WaitForSingleObject(self.owner.value, 0)
        if result == WAIT_TIMEOUT:
            return "existing"
        if result not in {0, 0x80}:
            raise ct.WinError(ct.get_last_error())
        self.owns_mutex = True
        return self._claim_mapping(generation)

    def _drop_mapping(self):
        if self.view:
            self.api.UnmapViewOfFile(self.view)
            self.view = None
        if self.mapping:
            self.mapping.close()
            self.mapping = None

    def _yield_mutex(self):
        if self.owns_mutex:
            _check(self.api.ReleaseMutex(self.owner.value))
            self.owns_mutex = False

    def _claim_mapping(self, generation, expected=None, deadline=None):
        """所有した候補だけがmappingを作り、旧世代を照合してから再公開する。"""
        self.generation = generation
        existing = self.api.OpenFileMappingW(READ_CONTROL | 6, False, self.state_name)
        if existing:
            self.mapping = OwnedHandle(self.api, existing)
            self._mapping_existed = True
        else:
            if ct.get_last_error() != 2:
                raise ct.WinError(ct.get_last_error())
            handle = self.api.CreateFileMappingW(
                INVALID_HANDLE_VALUE,
                ct.byref(self.mapping_security.attributes),
                4,
                0,
                4096,
                self.state_name,
            )
            self._mapping_existed = ct.get_last_error() == 183
            self.mapping = OwnedHandle(self.api, handle)
        _validate_acl(self.api, self.mapping.value, self.mapping_security)
        self.view = _check(self.api.MapViewOfFile(self.mapping.value, 6, 0, 0, 4096))
        # 新規mappingはゼロ初期化される。既存mappingの全公開前/破損を
        # 空と誤認しないようCreateFileMapping直後の判定を使う。
        if self._mapping_existed:
            try:
                previous = self._read_owner()
                if expected is None:
                    permitted = previous["state"] == "released"
                    if permitted:
                        try:
                            with self._validate_peer(
                                previous["pid"],
                                previous["process_created"],
                                allow_exited=True,
                            ):
                                pass
                        except OSError as e:
                            # 終了後PIDが存在しない場合もreleasedは有効。
                            # 生存する別processのPID再利用/権限拒否は許さない。
                            permitted = getattr(e, "winerror", None) == 87
                else:
                    permitted = (
                        all(
                            previous[key] == expected[key]
                            for key in (
                                "pid",
                                "process_created",
                                "session_id",
                                "generation",
                            )
                        )
                        and previous["state"] == "initializing"
                    )
                if not permitted:
                    self._drop_mapping()
                    self._yield_mutex()
                    return "existing"
            except (ValueError, FileNotFoundError):
                self._drop_mapping()
                self._yield_mutex()
                return "existing"
        if deadline is not None and self.tick_ms() >= deadline:
            self._drop_mapping()
            self._yield_mutex()
            return "existing"
        self.sequence = 0
        self.release_generation = None
        self._publish_owner("initializing", False)
        return "acquired"

    def try_takeover(self, generation, expected, deadline):
        self._assert_thread()
        if (
            self.tick_ms() >= deadline
            or self.observed_process is None
            or not self._process_has_exited(self.observed_process)
        ):
            return "existing"
        result = self.api.WaitForSingleObject(self.owner.value, 0)
        if result == WAIT_TIMEOUT:
            return "existing"
        if result not in {0, 0x80}:
            raise ct.WinError(ct.get_last_error())
        self.owns_mutex = True
        return self._claim_mapping(generation, expected, deadline)

    def _assert_thread(self):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("mutex所有・解放は起動スレッドのみ")

    def _publish_owner(self, state, ready):
        self._assert_thread()
        identity = {
            "protocol": 1,
            "generation": self.generation,
            "pid": self.pid,
            "process_created": self._created(self.api.GetCurrentProcess()),
            "session_id": self.session_id,
        }
        # identityもstateも同じseqlock内で置換する。古いreaderがmappingを
        # 保持していても、旧identityと新stateの混在を公開しない。
        self.sequence = ct.c_ulonglong.from_address(self.view).value
        if self.sequence % 2:
            self.sequence += 1
        self.sequence += 1
        ct.c_ulonglong.from_address(self.view).value = self.sequence
        data = json.dumps(identity).encode("utf-8")
        ct.memmove(self.view + 8, struct.pack("<I", len(data)) + data, 4 + len(data))
        mutable = json.dumps(
            {
                "state": state,
                "ready": ready,
                "release_generation": self.release_generation,
            }
        ).encode("utf-8")
        ct.memmove(
            self.view + 2048,
            struct.pack("<I", len(mutable)) + mutable,
            4 + len(mutable),
        )
        self.sequence += 1
        ct.c_ulonglong.from_address(self.view).value = self.sequence
        self.state = state

    def publish_state(self, state, ready):
        self._publish_owner(state, ready)

    def _read_owner(self):
        with OwnedHandle(
            self.api,
            self.api.OpenFileMappingW(READ_CONTROL | 4, False, self.state_name),
        ) as mapping:
            _validate_acl(self.api, mapping.value, self.mapping_security)
            view = _check(self.api.MapViewOfFile(mapping.value, 4, 0, 0, 4096))
            try:
                a = ct.string_at(view, 4096)
                b = ct.string_at(view, 4096)
                sequence = struct.unpack_from("<Q", a)[0]
                if not sequence or sequence % 2 or a != b:
                    raise ValueError("所有者情報の公開途中")
                size = struct.unpack_from("<I", a, 8)[0]
                state_size = struct.unpack_from("<I", a, 2048)[0]
                if not 0 < size < 2000 or not 0 < state_size < 2000:
                    raise ValueError("所有者情報の形式が不正")
                data = json.loads(a[12 : 12 + size])
                data.update(json.loads(a[2052 : 2052 + state_size]))
                if data.get("protocol") != 1:
                    raise ValueError("未対応起動protocol")
                if (
                    not isinstance(data.get("generation"), str)
                    or len(data["generation"]) != 32
                    or any(c not in "0123456789abcdef" for c in data["generation"])
                    or type(data.get("pid")) is not int
                    or data["pid"] <= 0
                    or type(data.get("process_created")) is not int
                    or data["process_created"] <= 0
                    or data.get("session_id") != self.session_id
                    or type(data.get("ready")) is not bool
                    or data.get("state")
                    not in {"initializing", "ready", "closing", "released"}
                    or data["ready"] != (data["state"] == "ready")
                    or (
                        data["state"] == "released"
                        and (
                            not isinstance(data.get("release_generation"), str)
                            or len(data["release_generation"]) != 32
                            or any(
                                c not in "0123456789abcdef"
                                for c in data["release_generation"]
                            )
                        )
                    )
                ):
                    raise ValueError("所有者identityが不正")
                return data
            finally:
                self.api.UnmapViewOfFile(view)

    def _observe_owner(self, owner):
        keys = ("pid", "process_created", "session_id", "generation")
        if self.observed_owner is not None and all(
            owner[k] == self.observed_owner[k] for k in keys
        ):
            self.observed_owner = owner
            return self.observed_process
        process = self._validate_peer(owner["pid"], owner["process_created"])
        if self.observed_process is not None:
            self.observed_process.close()
        self.observed_process = process
        self.observed_owner = owner
        return process

    def _process_has_exited(self, process):
        result = self.api.WaitForSingleObject(process.value, 0)
        if result not in {0, WAIT_TIMEOUT}:
            raise ct.WinError(ct.get_last_error())
        return result == 0

    def _pipe_name(self, generation):
        sid = hashlib.sha256(self.sid.encode()).hexdigest()[:24]
        return rf"\\.\pipe\{self.prefix}.{self.session_id}.{sid}.{generation}"

    def listen(self, callback):
        self._assert_thread()
        for index in range(8):
            pipe = OwnedHandle(
                self.api,
                self.api.CreateNamedPipeW(
                    self._pipe_name(self.generation),
                    3 | 0x40000000 | (0x80000 if index == 0 else 0),
                    8,
                    8,
                    2048,
                    2048,
                    0,
                    ct.byref(self.pipe_security.attributes),
                ),
            )
            self.pipes.append(pipe)
        for pipe in self.pipes:
            worker = threading.Thread(
                target=self._serve, args=(pipe, callback), daemon=True
            )
            self.workers.append(worker)
            worker.start()

    def _serve(self, pipe, callback):
        try:
            while not self.stop.is_set():
                with _quarantine_lock:
                    if len(_pending_io_quarantine) >= 32:
                        return
                pending = PendingIO(self.api, pipe)
                success = self.api.ConnectNamedPipe(
                    pipe.value, ct.byref(pending.overlapped)
                )
                error = ct.get_last_error()
                if not success and error == 535:
                    pending.complete()
                elif success or error == ERROR_IO_PENDING:
                    # listenerの待機は要求の5秒時計とは別。周期ごとの取消しは
                    # ちょうど接続したclientを切断する競合を生むため行わない。
                    while not self.stop.is_set():
                        wait = self.api.WaitForSingleObject(pending.event.value, 50)
                        if wait == 0:
                            break
                        if wait != WAIT_TIMEOUT:
                            pending.cancel()
                            raise ct.WinError(ct.get_last_error())
                    if self.stop.is_set():
                        pending.cancel()
                        return
                    pending.finish(self.tick_ms() + 100)
                else:
                    pending.complete()
                    raise ct.WinError(error)
                deadline = self.tick_ms() + 5000
                try:
                    pid = wt.DWORD()
                    _check(
                        self.api.GetNamedPipeClientProcessId(pipe.value, ct.byref(pid))
                    )
                    with self._validate_peer(pid.value):
                        request = _read_frame(self.api, pipe, deadline)
                        requested_deadline = request.get("deadline_tick")
                        if type(requested_deadline) is not int:
                            raise ValueError("要求期限が不正")
                        deadline = min(deadline, requested_deadline)
                        reply = callback(request)
                        if (
                            reply.get("result") == "accepted"
                            and self.tick_ms() < deadline
                        ):
                            _write_frame(self.api, pipe, reply, deadline)
                            while not self.stop.is_set() and self.tick_ms() < deadline:
                                self.stop.wait(
                                    min(25, deadline - self.tick_ms()) / 1000
                                )
                                reply = callback(request)
                                if reply.get("result") != "accepted":
                                    break
                        if self.tick_ms() < deadline and not self.stop.is_set():
                            _write_frame(self.api, pipe, reply, deadline)
                            # DisconnectNamedPipeは未読データを破棄する。
                            # terminalを読んだ相手の確認を同じ期限内で待つ。
                            _read_frame(self.api, pipe, deadline)
                except Exception as e:
                    self.logger.debug("起動受信失敗: %s", e)
                finally:
                    self.api.DisconnectNamedPipe(pipe.value)
        except Exception as e:
            self.logger.debug("起動listener停止: %s", e)
        finally:
            with _quarantine_lock:
                quarantined = any(p.pipe is pipe for p in _pending_io_quarantine)
            if not quarantined:
                pipe.close()

    def request_activation(self, started_tick):
        deadline = started_tick + 5000

        def pause(milliseconds):
            time.sleep(max(0, min(milliseconds, deadline - self.tick_ms())) / 1000)

        while self.tick_ms() < deadline:
            try:
                if self.takeover_callback(deadline):
                    return "primary"
                owner = self._read_owner()
                if owner["state"] in {"closing", "released"}:
                    return "connection_failed"
                with nullcontext(self._observe_owner(owner)) as process:
                    if self._process_has_exited(process):
                        if self.takeover_callback(deadline):
                            return "primary"
                        if owner["state"] != "initializing":
                            return "connection_failed"
                        pause(25)
                        continue
                    if not owner["ready"]:
                        pause(25)
                        continue
                    handle = self.api.CreateFileW(
                        self._pipe_name(owner["generation"]),
                        0xC0000000 | READ_CONTROL,
                        0,
                        None,
                        3,
                        0x40000000,
                        None,
                    )
                    if handle == INVALID_HANDLE_VALUE:
                        if ct.get_last_error() in {2, 231}:
                            pause(10)
                            continue
                        raise ct.WinError(ct.get_last_error())
                    with OwnedHandle(self.api, handle) as pipe:
                        pid = wt.DWORD()
                        _check(
                            self.api.GetNamedPipeServerProcessId(
                                pipe.value, ct.byref(pid)
                            )
                        )
                        if pid.value != owner["pid"]:
                            raise PermissionError("pipe所有者が不一致")
                        _validate_acl(self.api, pipe.value, self.pipe_security, 1)
                        current = self._read_owner()
                        if (
                            current["generation"] != owner["generation"]
                            or self.tick_ms() >= deadline
                            or self.api.WaitForSingleObject(process.value, 0)
                            != WAIT_TIMEOUT
                        ):
                            return "expired"
                        if self.tick_ms() >= deadline:
                            return "expired"
                        delegated, error = self._allow_foreground(owner["pid"])
                        self.logger.debug("前面化許可委譲: %s / %s", delegated, error)
                        request_id = uuid4().hex
                        _write_frame(
                            self.api,
                            pipe,
                            {
                                "request_id": request_id,
                                "issued_tick": started_tick,
                                "deadline_tick": deadline,
                                "generation": owner["generation"],
                                "op": "activate",
                            },
                            deadline,
                        )
                        try:
                            reply = _read_frame(self.api, pipe, deadline)
                            while True:
                                if self.tick_ms() >= deadline:
                                    return "expired"
                                result = self._validate_reply(
                                    reply, request_id, started_tick, deadline
                                )
                                if result != "accepted":
                                    break
                                self.logger.debug(
                                    "起動accepted: %s / deadline=%s",
                                    request_id,
                                    deadline,
                                )
                                reply = _read_frame(self.api, pipe, deadline)
                        except ValueError:
                            # 送信後は同じ副作用を新IDで再試行しない。
                            return "connection_failed"
                        _write_frame(self.api, pipe, {"received": request_id}, deadline)
                        if self.tick_ms() >= deadline:
                            return "expired"
                        return result
            except (FileNotFoundError, ValueError):
                pause(25)
            except TimeoutError:
                return "expired"
            except Exception as e:
                self.last_os_error = (
                    getattr(e, "winerror", None) or getattr(e, "errno", None) or 0
                )
                self.logger.debug("起動連絡失敗: os_error=%s", self.last_os_error)
                return "connection_failed"
        return "expired"

    def _validate_reply(self, reply, request_id, issued, deadline):
        if reply.get("request_id") != request_id:
            return "connection_failed"
        result = reply.get("result")
        if result not in {
            "accepted",
            "completed",
            "foreground_denied",
            "expired",
            "busy",
            "invalid",
            "connection_failed",
        }:
            return "connection_failed"
        if result in {"completed", "foreground_denied"}:
            tick = reply.get("completed_tick")
            if (
                type(tick) is not int
                or not 0 <= tick < deadline
                or tick > self.tick_ms()
                or type(reply.get("coalesced")) is not bool
                or (tick < issued and not (reply["coalesced"] and issued < tick + 500))
            ):
                return "connection_failed"
        return result

    def restore_window(self, hwnd, is_current=lambda: True):
        self._assert_thread()
        restorer = getattr(self, "focus_restorer", None)
        if restorer is not None:
            return restorer.restore(hwnd, is_current=is_current)
        if not is_current():
            return "expired"
        hwnd = self.api.GetAncestor(hwnd, 2) or hwnd
        if not is_current():
            return "expired"
        if self.api.SetForegroundWindow(hwnd):
            return "completed"
        if not is_current():
            return "expired"
        _flash_window(self.api, hwnd)
        return "foreground_denied"

    def _window_process_id(self, hwnd):
        if not hwnd or not self.api.IsWindow(hwnd):
            return None
        pid = wt.DWORD()
        thread = self.api.GetWindowThreadProcessId(hwnd, ct.byref(pid))
        if pid.value != self.pid or thread != threading.get_native_id():
            return None
        return pid.value, thread

    def _top_level_hwnd(self, widget):
        self._assert_thread()
        try:
            inner = widget.winfo_id()
            hwnd = self.api.GetAncestor(inner, 2)
            if not hwnd:
                hwnd = int(widget.wm_frame(), 0)
            return hwnd if self._window_process_id(hwnd) else None
        except Exception as e:
            self.logger.debug("復帰HWNDの正規化: %s", e)
            return None

    def _activation_target_valid(self, hwnd):
        return bool(self._window_process_id(hwnd) and self.api.IsWindowEnabled(hwnd))

    def _z_order(self, handles):
        """EnumThreadWindowsのZ-orderを自process/UI-threadだけに制限する。"""
        result = []
        callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

        def collect(hwnd, data):
            if hwnd in handles and self._window_process_id(hwnd):
                result.append(hwnd)
            return True

        callback = callback_type(collect)
        enum = _bind(
            self.api.u,
            "EnumThreadWindows",
            wt.BOOL,
            wt.DWORD,
            callback_type,
            wt.LPARAM,
        )
        enum(threading.get_native_id(), callback, 0)
        return result

    def _owned_popup(self, handles):
        known = set(handles)
        candidates = []
        info = GUITHREADINFO(cbSize=ct.sizeof(GUITHREADINFO))
        if self.api.GetGUIThreadInfo(threading.get_native_id(), ct.byref(info)):
            candidates.append(info.hwndActive)
        candidates.extend(self.api.GetLastActivePopup(hwnd) for hwnd in handles)
        # native modalがTk dialog所有でも、UI-thread列挙から漏らさない。
        candidates.extend(self._thread_windows())
        for hwnd in candidates:
            if (
                not hwnd
                or hwnd in known
                or not self._window_process_id(hwnd)
                or not self.api.IsWindowVisible(hwnd)
                or not self.api.IsWindowEnabled(hwnd)
            ):
                continue
            cursor = hwnd
            seen = set()
            disabled_parent = False
            while cursor and cursor not in seen:
                seen.add(cursor)
                if not self._window_process_id(cursor):
                    break
                if cursor in known:
                    disabled_parent |= not self.api.IsWindowEnabled(cursor)
                    if disabled_parent:
                        return hwnd
                    break
                cursor = self.api.GetWindow(cursor, 4)  # GW_OWNER
                if cursor:
                    disabled_parent |= not self.api.IsWindowEnabled(cursor)
        return None

    def _thread_windows(self):
        result = []
        callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

        def collect(hwnd, data):
            if self._window_process_id(hwnd):
                result.append(hwnd)
            return True

        callback = callback_type(collect)
        enum = _bind(
            self.api.u, "EnumThreadWindows", wt.BOOL, wt.DWORD, callback_type, wt.LPARAM
        )
        enum(threading.get_native_id(), callback, 0)
        return result

    def _restore_placement(self, hwnd, is_current):
        if not self._window_process_id(hwnd) or not is_current():
            return False
        self.api.ShowWindow(hwnd, 9)  # SW_RESTORE
        return True

    def _foreground_window(self, hwnd, is_current):
        if not self._window_process_id(hwnd) or not is_current():
            return "expired"
        return (
            "completed" if self.api.SetForegroundWindow(hwnd) else "foreground_denied"
        )

    def _flash_window(self, hwnd):
        _flash_window(self.api, hwnd)

    def _stop_flash(self, hwnd):
        _flash_window(self.api, hwnd, stop=True)

    def _allow_foreground(self, pid):
        return bool(self.api.AllowSetForegroundWindow(pid)), ct.get_last_error()

    def show_notice(self, reason):
        from pagefolio.startup_control import StartupOutcome
        from pagefolio.startup_notice import show_startup_failure

        return show_startup_failure(StartupOutcome(reason), self)

    def _create_notice_lease(self, reason):
        return NoticeLease(self, reason)

    def notice_language(self):
        return _bind(self.api.k, "GetUserDefaultUILanguage", wt.WORD)()

    def display_notice(self, reason, text, lease):
        notice = NativeNoticeLifetime(self, reason, text=text, lease=lease)
        notice.show()

    def _cancel_pending_io(self):
        for pipe in self.pipes:
            if pipe.value is not None:
                self.api.CancelIoEx(pipe.value, None)

    def stop_accepting(self):
        self._assert_thread()
        if self.owns_mutex and self.view:
            try:
                self._publish_owner("closing", False)
            except Exception as e:
                self.logger.debug("終了状態の公開失敗: %s", e)
        self.stop.set()
        self._cancel_pending_io()

    def close(self, *, root_absent=True):
        self._assert_thread()
        if self._closed:
            return
        self.stop_accepting()
        deadline = time.monotonic() + 0.5
        for worker in self.workers:
            worker.join(max(0, deadline - time.monotonic()))
        for index, pipe in enumerate(self.pipes):
            if index >= len(self.workers) or not self.workers[index].is_alive():
                pipe.close()
        if self.owns_mutex and not root_absent:
            # root破棄を証明できない異常終了はclosingの所有をprocess終了まで
            # 保持する。二次を新GUIへ進ませるために排他を解放しない。
            _shutdown_owner_quarantine.append(self)
            return
        if (
            root_absent
            and self.owns_mutex
            and self.view
            and not any(worker.is_alive() for worker in self.workers)
        ):
            try:
                self.release_generation = uuid4().hex
                self._publish_owner("released", False)
            except Exception as e:
                self.logger.debug("release公開失敗: %s", e)
        self._drop_mapping()
        if self.observed_process is not None:
            self.observed_process.close()
            self.observed_process = None
        if self.owner:
            self._yield_mutex()
            self.owner.close()
        for security in (
            self.owner_security,
            self.mapping_security,
            self.pipe_security,
        ):
            security.close()
        self._closed = True


def _restore_window(backend, hwnd):
    return backend.restore_window(hwnd)


def _flash_window(api, hwnd, *, stop=False):
    class FLASHWINFO(ct.Structure):
        _fields_ = [
            ("cbSize", wt.UINT),
            ("hwnd", wt.HWND),
            ("dwFlags", wt.DWORD),
            ("uCount", wt.UINT),
            ("dwTimeout", wt.DWORD),
        ]

    flash = _bind(api.u, "FlashWindowEx", wt.BOOL, ct.POINTER(FLASHWINFO))
    flash(ct.byref(FLASHWINFO(ct.sizeof(FLASHWINFO), hwnd, 0 if stop else 2, 3, 250)))


class NoticeLease:
    """原因別mutexと表示identityを照合し、表示スレッドだけが所有・公開する。"""

    def __init__(self, backend, reason):
        self.backend = backend
        self.reason = str(reason)
        suffix = hashlib.sha256(self.reason.encode()).hexdigest()[:16]
        self.name = "Local\\" + backend.prefix + ".Notice." + suffix
        self.state_name = self.name + ".State"
        self.handle = None
        self.mapping = None
        self.view = None
        self.acquired = False
        self.owns_mutex = False
        self.snapshot = None

    def _open_mapping(self, create):
        b = self.backend
        access = READ_CONTROL | (6 if create else 4)
        value = b.api.OpenFileMappingW(access, False, self.state_name)
        existed = bool(value)
        if not value:
            if not create or ct.get_last_error() != 2:
                raise ct.WinError(ct.get_last_error())
            value = b.api.CreateFileMappingW(
                INVALID_HANDLE_VALUE,
                ct.byref(b.mapping_security.attributes),
                4,
                0,
                4096,
                self.state_name,
            )
            existed = ct.get_last_error() == 183
        self.mapping = OwnedHandle(b.api, value)
        _validate_acl(b.api, self.mapping.value, b.mapping_security)
        self.view = _check(
            b.api.MapViewOfFile(self.mapping.value, 6 if create else 4, 0, 0, 4096)
        )
        return existed

    def _read_snapshot(self):
        # mutex所有者が公開中でも有界に失敗し、全ゼロを旧owner不存在とみなさない。
        for _ in range(3):
            before = ct.c_ulonglong.from_address(self.view).value
            if before == 0 or before % 2:
                continue
            size = ct.c_uint32.from_address(self.view + 8).value
            if not 0 < size <= 2048:
                raise ValueError("通知snapshotの長さが不正")
            raw = ct.string_at(self.view + 12, size)
            if ct.c_ulonglong.from_address(self.view).value == before:
                data = json.loads(raw)
                required = {
                    "protocol",
                    "reason",
                    "pid",
                    "process_created",
                    "session_id",
                    "generation",
                    "state",
                    "hwnd",
                    "shown_tick",
                    "deadline_tick",
                }
                if not isinstance(data, dict) or set(data) != required:
                    raise ValueError("通知snapshotが不正")
                if any(
                    type(data[key]) is not int
                    for key in (
                        "protocol",
                        "pid",
                        "process_created",
                        "session_id",
                        "hwnd",
                        "shown_tick",
                        "deadline_tick",
                    )
                ):
                    raise ValueError("通知snapshotの型が不正")
                if (
                    data["protocol"] != 1
                    or data["reason"] != self.reason
                    or data["session_id"] != self.backend.session_id
                    or data["pid"] <= 0
                    or data["process_created"] <= 0
                    or not isinstance(data["generation"], str)
                    or len(data["generation"]) != 32
                    or data["state"] not in {"preparing", "shown", "closed"}
                ):
                    raise ValueError("通知identityが不正")
                if data["state"] == "shown" and (
                    data["hwnd"] <= 0
                    or not 0 < data["deadline_tick"] - data["shown_tick"] <= 10000
                    or data["shown_tick"] > self.backend.tick_ms()
                ):
                    raise ValueError("通知表示状態が不正")
                return data
        raise ValueError("通知snapshotは未公開または公開途中")

    def _publish(self, state, *, hwnd=0, shown_tick=0, deadline_tick=0):
        self.backend._assert_thread()
        if not self.owns_mutex or not self.acquired:
            raise RuntimeError("通知所有者だけが公開できる")
        data = {
            "protocol": 1,
            "reason": self.reason,
            "pid": self.backend.pid,
            "process_created": self.backend._created(
                self.backend.api.GetCurrentProcess()
            ),
            "session_id": self.backend.session_id,
            "generation": self.snapshot["generation"] if self.snapshot else uuid4().hex,
            "state": state,
            "hwnd": hwnd,
            "shown_tick": shown_tick,
            "deadline_tick": deadline_tick,
        }
        before = ct.c_ulonglong.from_address(self.view).value
        before += before % 2
        ct.c_ulonglong.from_address(self.view).value = before + 1
        raw = json.dumps(data).encode("utf-8")
        ct.memmove(self.view + 8, struct.pack("<I", len(raw)) + raw, 4 + len(raw))
        ct.c_ulonglong.from_address(self.view).value = before + 2
        self.snapshot = data

    def mark_shown(self, hwnd, shown_tick, deadline_tick):
        if self.snapshot["state"] != "preparing":
            if all(
                self.snapshot[key] == value
                for key, value in (
                    ("hwnd", hwnd),
                    ("shown_tick", shown_tick),
                    ("deadline_tick", deadline_tick),
                )
            ):
                return
            raise ValueError("初回通知の表示期限は更新できない")
        self._publish(
            "shown", hwnd=hwnd, shown_tick=shown_tick, deadline_tick=deadline_tick
        )

    def _owner_status(self, snapshot):
        b = self.backend
        try:
            with b._validate_peer(
                snapshot["pid"], snapshot["process_created"], allow_exited=True
            ) as process:
                if b._process_has_exited(process):
                    return "dead"
        except OSError as e:
            if getattr(e, "winerror", None) == 87:  # PID自体の不存在をOSが確認。
                return "dead"
            raise
        if snapshot["state"] == "closed":
            return "closed"
        if snapshot["state"] != "shown":
            return "unknown"
        hwnd = snapshot["hwnd"]
        pid = wt.DWORD()
        class_name = ct.create_unicode_buffer(256)
        thread = b.api.GetWindowThreadProcessId(hwnd, ct.byref(pid))
        if (
            thread
            and pid.value == snapshot["pid"]
            and b.api.GetClassNameW(hwnd, class_name, len(class_name))
            and class_name.value == "PageFolioNotice" + snapshot["generation"]
            and b.api.IsWindow(hwnd)
            and b.api.IsWindowVisible(hwnd)
            and b.tick_ms() < snapshot["deadline_tick"]
        ):
            return "visible"
        return "unknown"

    def _verified_join(self):
        self._open_mapping(False)
        self.snapshot = self._read_snapshot()
        if self._owner_status(self.snapshot) != "visible":
            raise OSError("表示中の通知を確認できない")

    def __enter__(self):
        b = self.backend
        b._assert_thread()
        try:
            value = b.api.CreateMutexExW(
                ct.byref(b.owner_security.attributes),
                self.name,
                0,
                OWNER_ACCESS,
            )
            if not value and ct.get_last_error() == 5:
                # 別名/fail-openは使わず、同じ正規名への最小権限確認を一度だけ行う。
                open_mutex = _bind(
                    b.api.k, "OpenMutexW", wt.HANDLE, wt.DWORD, wt.BOOL, wt.LPCWSTR
                )
                self.handle = OwnedHandle(
                    b.api, open_mutex(SYNCHRONIZE | READ_CONTROL, False, self.name)
                )
                _validate_acl(b.api, self.handle.value, b.owner_security)
                self._verified_join()
                return self
            self.handle = OwnedHandle(b.api, value)
            _validate_acl(b.api, self.handle.value, b.owner_security)
            result = b.api.WaitForSingleObject(self.handle.value, 0)
            if result == WAIT_TIMEOUT:
                self._verified_join()
                return self
            if result not in {0, 0x80}:
                raise ct.WinError(ct.get_last_error())
            self.owns_mutex = True
            if self._open_mapping(True):
                previous = self._read_snapshot()
                status = self._owner_status(previous)
                if status == "visible":
                    # owner-threadだけが終了しても、生存窓の多重表示を許さない。
                    self.snapshot = previous
                    return self
                if status not in {"dead", "closed"}:
                    raise OSError("旧通知ownerの終了を確認できない")
            elif result == 0x80:
                # abandonedだけではprocess終了を証明しない。
                raise OSError("放棄通知のidentityがない")
            self.acquired = True
            self._publish("preparing")
            return self
        except Exception as e:
            self._dispose()
            raise e

    def _dispose(self):
        b = self.backend
        try:
            if self.view:
                _check(b.api.UnmapViewOfFile(self.view))
                self.view = None
        finally:
            try:
                if self.mapping:
                    self.mapping.close()
            finally:
                try:
                    if self.owns_mutex:
                        _check(b.api.ReleaseMutex(self.handle.value))
                        self.owns_mutex = False
                finally:
                    if self.handle:
                        self.handle.close()

    def __exit__(self, *args):
        self.backend._assert_thread()
        try:
            if self.acquired:
                self._publish("closed")
        finally:
            self._dispose()


class LOGFONT(ct.Structure):
    _fields_ = (
        [
            (name, wt.LONG)
            for name in (
                "lfHeight",
                "lfWidth",
                "lfEscapement",
                "lfOrientation",
                "lfWeight",
            )
        ]
        + [
            (name, wt.BYTE)
            for name in (
                "lfItalic",
                "lfUnderline",
                "lfStrikeOut",
                "lfCharSet",
                "lfOutPrecision",
                "lfClipPrecision",
                "lfQuality",
                "lfPitchAndFamily",
            )
        ]
        + [("lfFaceName", wt.WCHAR * 32)]
    )


class NONCLIENTMETRICS(ct.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("iBorderWidth", ct.c_int),
        ("iScrollWidth", ct.c_int),
        ("iScrollHeight", ct.c_int),
        ("iCaptionWidth", ct.c_int),
        ("iCaptionHeight", ct.c_int),
        ("lfCaptionFont", LOGFONT),
        ("iSmCaptionWidth", ct.c_int),
        ("iSmCaptionHeight", ct.c_int),
        ("lfSmCaptionFont", LOGFONT),
        ("iMenuWidth", ct.c_int),
        ("iMenuHeight", ct.c_int),
        ("lfMenuFont", LOGFONT),
        ("lfStatusFont", LOGFONT),
        ("lfMessageFont", LOGFONT),
        ("iPaddedBorderWidth", ct.c_int),
    ]


class PAINTSTRUCT(ct.Structure):
    _fields_ = [
        ("hdc", wt.HDC),
        ("fErase", wt.BOOL),
        ("rcPaint", wt.RECT),
        ("fRestore", wt.BOOL),
        ("fIncUpdate", wt.BOOL),
        ("rgbReserved", wt.BYTE * 32),
    ]


class NativeNoticeLifetime:
    """生成スレッドで全資源を解放し、クラス解除まで WndProc を強保持する。"""

    def __init__(self, backend, reason, *, text=None, lease=None):
        from pagefolio.startup_control import StartupOutcome
        from pagefolio.startup_notice import (
            StartupFailureReason,
            _failure_reason,
            _notice_language,
            _notice_text,
        )

        self.backend = backend
        self.reason = reason
        self.lease = lease
        self.window_generation = lease.snapshot["generation"] if lease else uuid4().hex
        classified = (
            StartupFailureReason(reason)
            if reason in StartupFailureReason
            else _failure_reason(StartupOutcome(reason), True)
        )
        self.text = text or _notice_text(
            classified, _notice_language(backend.notice_language())
        )
        self.callback = None
        self.hwnd = None
        self.error = None
        self.deadline_tick = None
        self.close_rect = wt.RECT()
        self.message_rect = wt.RECT()
        self.dpi = None
        self.foreground_before_show = None
        self.foreground_after_show = None
        self.foreground_before_close = None
        self.foreground_after_close = None

    def show(self, *, lifetime_ms=10000, on_show=None):
        from pagefolio.startup_notice import notice_deadline_tick, notice_remaining_ms

        self.backend._assert_thread()
        api = self.backend.api
        gdi = ct.WinDLL("gdi32", use_last_error=True)
        callback_type = ct.WINFUNCTYPE(
            ct.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
        )

        class WNDCLASS(ct.Structure):
            _fields_ = [
                ("style", wt.UINT),
                ("lpfnWndProc", callback_type),
                ("cbClsExtra", ct.c_int),
                ("cbWndExtra", ct.c_int),
                ("hInstance", wt.HINSTANCE),
                ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE),
                ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR),
            ]

        default = _bind(
            api.u,
            "DefWindowProcW",
            ct.c_ssize_t,
            wt.HWND,
            wt.UINT,
            wt.WPARAM,
            wt.LPARAM,
        )
        destroy_window = _bind(api.u, "DestroyWindow", wt.BOOL, wt.HWND)
        foreground = _bind(api.u, "GetForegroundWindow", wt.HWND)

        def destroy(hwnd):
            self.foreground_before_close = foreground()
            result = destroy_window(hwnd)
            self.foreground_after_close = foreground()
            return result

        timer = _bind(
            api.u, "SetTimer", ct.c_size_t, wt.HWND, ct.c_size_t, wt.UINT, wt.LPVOID
        )
        kill_timer = _bind(api.u, "KillTimer", wt.BOOL, wt.HWND, ct.c_size_t)
        select = _bind(gdi, "SelectObject", wt.HANDLE, wt.HDC, wt.HANDLE)
        draw_text = _bind(
            api.u,
            "DrawTextW",
            ct.c_int,
            wt.HDC,
            wt.LPCWSTR,
            ct.c_int,
            ct.POINTER(wt.RECT),
            wt.UINT,
        )
        begin_paint = _bind(
            api.u, "BeginPaint", wt.HDC, wt.HWND, ct.POINTER(PAINTSTRUCT)
        )
        end_paint = _bind(api.u, "EndPaint", wt.BOOL, wt.HWND, ct.POINTER(PAINTSTRUCT))
        frame = _bind(
            api.u,
            "DrawFrameControl",
            wt.BOOL,
            wt.HDC,
            ct.POINTER(wt.RECT),
            wt.UINT,
            wt.UINT,
        )
        background = _bind(gdi, "SetBkMode", ct.c_int, wt.HDC, ct.c_int)
        font = None

        def procedure(hwnd, message, wparam, lparam):
            try:
                if message == 0x21:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                    return 3
                if message == 0xF:  # WM_PAINT: 子BUTTON/STATICによるfocusを作らない。
                    paint = PAINTSTRUCT()
                    dc = _check(begin_paint(hwnd, ct.byref(paint)))
                    try:
                        if font:
                            old = select(dc, font)
                            try:
                                background(dc, 1)
                                draw_text(
                                    dc,
                                    self.text[1],
                                    -1,
                                    ct.byref(self.message_rect),
                                    0x10 | 0x800,
                                )
                                frame(dc, ct.byref(self.close_rect), 4, 0x10)
                                draw_text(
                                    dc,
                                    self.text[2],
                                    -1,
                                    ct.byref(self.close_rect),
                                    1 | 4 | 0x20 | 0x800,
                                )
                            finally:
                                select(dc, old)
                    finally:
                        end_paint(hwnd, ct.byref(paint))
                    return 0
                close_click = False
                if message == 0x202:  # WM_LBUTTONUP / client座標
                    x, y = (
                        ct.c_short(lparam & 0xFFFF).value,
                        ct.c_short((lparam >> 16) & 0xFFFF).value,
                    )
                    r = self.close_rect
                    close_click = r.left <= x < r.right and r.top <= y < r.bottom
                if message == 0x113:
                    if (
                        self.deadline_tick is not None
                        and notice_remaining_ms(
                            self.deadline_tick, self.backend.tick_ms()
                        )
                        == 0
                    ):
                        destroy(hwnd)
                    return 0
                if message == 0x10 or close_click:
                    destroy(hwnd)
                    return 0
                if message == 0x82:  # WM_NCDESTROY
                    kill_timer(hwnd, 1)
                    self.hwnd = None
                return default(hwnd, message, wparam, lparam)
            except Exception as e:
                self.error = e
                destroy(hwnd)
                return 0

        self.callback = callback_type(procedure)
        name = "PageFolioNotice" + self.window_generation
        register = _bind(api.u, "RegisterClassW", wt.ATOM, ct.POINTER(WNDCLASS))
        unregister = _bind(api.u, "UnregisterClassW", wt.BOOL, wt.LPCWSTR, wt.HINSTANCE)
        create = _bind(
            api.u,
            "CreateWindowExW",
            wt.HWND,
            wt.DWORD,
            wt.LPCWSTR,
            wt.LPCWSTR,
            wt.DWORD,
            ct.c_int,
            ct.c_int,
            ct.c_int,
            ct.c_int,
            wt.HWND,
            wt.HMENU,
            wt.HINSTANCE,
            wt.LPVOID,
        )
        show = _bind(api.u, "ShowWindow", wt.BOOL, wt.HWND, ct.c_int)
        peek = _bind(
            api.u,
            "PeekMessageW",
            wt.BOOL,
            ct.POINTER(wt.MSG),
            wt.HWND,
            wt.UINT,
            wt.UINT,
            wt.UINT,
        )
        dispatch = _bind(api.u, "DispatchMessageW", ct.c_ssize_t, ct.POINTER(wt.MSG))
        translate = _bind(api.u, "TranslateMessage", wt.BOOL, ct.POINTER(wt.MSG))
        wait = _bind(
            api.u,
            "MsgWaitForMultipleObjectsEx",
            wt.DWORD,
            wt.DWORD,
            wt.LPVOID,
            wt.DWORD,
            wt.DWORD,
            wt.DWORD,
        )
        delete = _bind(gdi, "DeleteObject", wt.BOOL, wt.HANDLE)
        window_class = WNDCLASS()
        window_class.lpfnWndProc = self.callback
        window_class.lpszClassName = name
        window_class.hbrBackground = 6  # COLOR_WINDOW + 1
        registered = False
        try:
            _check(register(ct.byref(window_class)))
            registered = True
            self.hwnd = _check(
                create(
                    0x08000080,
                    name,
                    self.text[0],
                    0x80000000,
                    0,
                    0,
                    1,
                    1,
                    None,
                    None,
                    None,
                    None,
                )
            )
            self.dpi = _check(
                _bind(api.u, "GetDpiForWindow", wt.UINT, wt.HWND)(self.hwnd)
            )
            metrics = NONCLIENTMETRICS(cbSize=ct.sizeof(NONCLIENTMETRICS))
            spi = _bind(
                api.u,
                "SystemParametersInfoForDpi",
                wt.BOOL,
                wt.UINT,
                wt.UINT,
                wt.LPVOID,
                wt.UINT,
                wt.UINT,
            )
            _check(spi(0x29, metrics.cbSize, ct.byref(metrics), 0, self.dpi))
            font = _check(
                _bind(gdi, "CreateFontIndirectW", wt.HANDLE, ct.POINTER(LOGFONT))(
                    ct.byref(metrics.lfMessageFont)
                )
            )
            work = wt.RECT()
            _check(
                _bind(
                    api.u,
                    "SystemParametersInfoW",
                    wt.BOOL,
                    wt.UINT,
                    wt.UINT,
                    wt.LPVOID,
                    wt.UINT,
                )(0x30, 0, ct.byref(work), 0)
            )
            scale = self.dpi / 96
            margin = max(1, round(16 * scale))
            width = min(round(560 * scale), work.right - work.left - 2 * margin)
            get_dc = _bind(api.u, "GetDC", wt.HDC, wt.HWND)
            release_dc = _bind(api.u, "ReleaseDC", ct.c_int, wt.HWND, wt.HDC)
            dc = _check(get_dc(self.hwnd))
            old = select(dc, font)
            try:
                measured = wt.RECT(0, 0, width - 2 * margin, 0)
                _check(
                    draw_text(
                        dc, self.text[1], -1, ct.byref(measured), 0x400 | 0x10 | 0x800
                    )
                )
                close = wt.RECT()
                _check(
                    draw_text(
                        dc, self.text[2], -1, ct.byref(close), 0x400 | 0x20 | 0x800
                    )
                )
            finally:
                select(dc, old)
                release_dc(self.hwnd, dc)
            self.message_rect = wt.RECT(
                margin, margin, width - margin, margin + measured.bottom
            )
            button_height = max(close.bottom + margin, round(32 * scale))
            button_width = max(close.right + 2 * margin, round(80 * scale))
            top = self.message_rect.bottom + margin
            self.close_rect = wt.RECT(
                width - margin - button_width, top, width - margin, top + button_height
            )
            height = self.close_rect.bottom + margin
            if width <= 2 * margin or height > work.bottom - work.top:
                raise OSError("通知の表示領域を確保できない")
            position = _bind(
                api.u,
                "SetWindowPos",
                wt.BOOL,
                wt.HWND,
                wt.HWND,
                ct.c_int,
                ct.c_int,
                ct.c_int,
                ct.c_int,
                wt.UINT,
            )
            _check(
                position(
                    self.hwnd,
                    None,
                    work.right - width - margin,
                    work.top + margin,
                    width,
                    height,
                    0x14,
                )
            )
            # 最初の表示時刻に一度だけ確定。後続案内による期限更新を行わない。
            self.deadline_tick = notice_deadline_tick(
                self.backend.tick_ms(), lifetime_ms
            )
            _check(timer(self.hwnd, 1, max(1, lifetime_ms), None))
            self.foreground_before_show = foreground()
            show(self.hwnd, 4)  # SW_SHOWNOACTIVATE
            self.foreground_after_show = foreground()
            if self.lease:
                self.lease.mark_shown(
                    self.hwnd, self.deadline_tick - lifetime_ms, self.deadline_tick
                )
            if on_show:
                on_show(self.hwnd)
            message = wt.MSG()
            while self.hwnd:
                remaining = notice_remaining_ms(
                    self.deadline_tick, self.backend.tick_ms()
                )
                if not remaining:
                    destroy(self.hwnd)
                    break
                if peek(ct.byref(message), None, 0, 0, 1):
                    if message.message == 0x12:
                        destroy(self.hwnd)
                        break
                    translate(ct.byref(message))
                    dispatch(ct.byref(message))
                elif wait(0, None, remaining, 0x4FF, 4) == 0xFFFFFFFF:
                    raise ct.WinError(ct.get_last_error())
        finally:
            if self.hwnd:
                kill_timer(self.hwnd, 1)
                destroy(self.hwnd)
            if font:
                delete(font)
            if registered and not unregister(name, None):
                _notice_lifetime_quarantine.append(self)
                raise ct.WinError(ct.get_last_error())
        if self.error is not None:
            raise self.error


def _show_notice_window(backend, reason):
    NativeNoticeLifetime(backend, reason).show()
