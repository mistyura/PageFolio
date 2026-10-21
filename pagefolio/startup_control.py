"""Tk に依存しない起動要求と、メインスレッドへの有界受け渡し。"""

import json
from collections import OrderedDict
from dataclasses import asdict, dataclass
from queue import Empty, Queue
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class OwnerIdentity:
    pid: int
    process_created: int
    session_id: int
    generation: str


@dataclass(frozen=True)
class ActivationRequest:
    request_id: str
    issued_tick: int
    deadline_tick: int
    generation: str
    op: str = "activate"


@dataclass(frozen=True)
class ActivationReply:
    request_id: str
    result: str
    completed_tick: int | None = None
    coalesced: bool = False


@dataclass(frozen=True)
class StartupOutcome:
    result: str
    primary: bool = False


@dataclass
class _QueuedActivation:
    request: ActivationRequest


class StartupCoordinator:
    """worker は Queue のみを使い、Tk API は起動スレッドだけが呼ぶ。"""

    def __init__(self, backend):
        self.backend = backend
        self.queue = Queue(maxsize=32)
        self.root = None
        self.after_id = None
        self.closed = False
        self.generation = uuid4().hex
        self._lock = RLock()
        self._pending = {}
        self.terminal_cache = OrderedDict()
        self.active_batch = None
        self.first_terminal_tick = None
        self._cooldown_result = None
        self._cache_generation = self.generation
        self.takeover_attempted = False
        self.backend.takeover_callback = self._try_takeover

    def claim(self):
        result = self.backend.claim(self.generation)
        if result == "acquired":
            self.backend.listen(self._receive)
            return StartupOutcome("primary", True)
        return StartupOutcome(result, result == "primary")

    def _try_takeover(self, deadline):
        owner = getattr(self.backend, "observed_owner", None)
        process = getattr(self.backend, "observed_process", None)
        if (
            self.takeover_attempted
            or self.backend.tick_ms() >= deadline
            or not owner
            or owner["state"] != "initializing"
            or process is None
            or not self.backend._process_has_exited(process)
        ):
            return False
        self.takeover_attempted = True
        result = self.backend.try_takeover(self.generation, owner, deadline)
        self.backend.logger.debug(
            "起動引継ぎ: %s / %s / deadline=%s", owner["pid"], result, deadline
        )
        if result != "acquired":
            return False
        self.backend.listen(self._receive)
        return True

    def request_activation(self, started_tick):
        return self._wait_for_terminal(started_tick)

    def _wait_for_terminal(self, started_tick):
        result = self.backend.request_activation(started_tick)
        if self.backend.tick_ms() >= started_tick + 5000:
            result = "expired"
        return StartupOutcome(result, result == "primary")

    def _valid(self, request):
        return (
            not self.closed
            and request.generation == self.generation
            and self.backend.tick_ms() < request.deadline_tick
        )

    def _finish(self, item, result, tick, coalesced=False):
        reply = ActivationReply(item.request.request_id, result, tick, coalesced)
        self._pending.pop(item.request.request_id, None)
        self.terminal_cache[item.request.request_id] = (item.request, reply)
        while len(self.terminal_cache) > 128:
            self.terminal_cache.popitem(last=False)
        self.backend.logger.debug(
            "起動terminal: %s / %s / deadline=%s / tick=%s",
            reply.request_id,
            result,
            item.request.deadline_tick,
            tick,
        )
        return asdict(reply)

    def _coalesce_request(self, item):
        if self.active_batch is not None:
            self.active_batch.append(item)
            return asdict(ActivationReply(item.request.request_id, "accepted"))
        now = self.backend.tick_ms()
        if (
            self.first_terminal_tick is not None
            and now < self.first_terminal_tick + 500
        ):
            return self._finish(
                item, self._cooldown_result, self.first_terminal_tick, True
            )
        self.queue.put_nowait(item)
        return asdict(ActivationReply(item.request.request_id, "accepted"))

    def _receive(self, raw):
        try:
            if not isinstance(raw, dict) or len(json.dumps(raw).encode("utf-8")) > 1024:
                return {"result": "invalid"}
            request = ActivationRequest(**raw)
        except (TypeError, ValueError):
            return {"result": "invalid"}
        now = self.backend.tick_ms()
        if (
            request.op != "activate"
            or request.generation != self.generation
            or type(request.issued_tick) is not int
            or type(request.deadline_tick) is not int
            or not request.issued_tick <= now < request.deadline_tick
            or request.deadline_tick - request.issued_tick > 5000
            or not isinstance(request.request_id, str)
            or len(request.request_id) != 32
            or any(c not in "0123456789abcdef" for c in request.request_id)
        ):
            return asdict(ActivationReply(request.request_id, "expired"))
        with self._lock:
            if self._cache_generation != self.generation:
                self.terminal_cache.clear()
                self.first_terminal_tick = None
                self._cache_generation = self.generation
            cached = self.terminal_cache.get(request.request_id)
            if cached is not None:
                return (
                    asdict(cached[1]) if cached[0] == request else {"result": "invalid"}
                )
            pending = self._pending.get(request.request_id)
            if pending is not None:
                return (
                    asdict(ActivationReply(request.request_id, "accepted"))
                    if pending.request == request
                    else {"result": "invalid"}
                )
            if not self._valid(request):
                return asdict(ActivationReply(request.request_id, "expired"))
            if len(self._pending) >= 32:
                return asdict(ActivationReply(request.request_id, "busy"))
            item = _QueuedActivation(request)
            self._pending[request.request_id] = item
            return self._coalesce_request(item)

    def attach_tk(self, root):
        self.root = root
        self.backend.publish_state("ready", True)
        self._poll()

    def _poll(self):
        self.after_id = None
        if self.closed:
            return
        self._dispatch_pending()
        self.after_id = self.root.after(50, self._poll)

    def _dispatch_pending(self):
        with self._lock:
            if self.active_batch is not None or self.closed:
                return
            batch = []
            while True:
                try:
                    item = self.queue.get_nowait()
                except Empty:
                    break
                if self._valid(item.request):
                    batch.append(item)
                else:
                    self._finish(item, "expired", self.backend.tick_ms())
            if not batch:
                return
            self.active_batch = batch

        def is_current():
            with self._lock:
                return any(self._valid(item.request) for item in batch)

        result = "expired"
        try:
            if is_current():
                result = self.backend.restore_window(
                    self.root.winfo_id(), is_current=is_current
                )
        except Exception as e:
            self.backend.logger.debug("起動復帰失敗: %s", e)
            result = "connection_failed"
        finally:
            with self._lock:
                tick = self.backend.tick_ms()
                if result in {"completed", "foreground_denied"}:
                    self.first_terminal_tick = tick
                    self._cooldown_result = result
                for index, item in enumerate(batch):
                    self._finish(
                        item,
                        result if self._valid(item.request) else "expired",
                        tick,
                        index > 0,
                    )
                self.active_batch = None

    def close(self):
        root_absent = self.root is None
        if self.root is not None:
            try:
                root_absent = not self.root.winfo_exists()
            except Exception as e:
                # destroy後のTclError以外は、root不存在を確認した扱いにしない。
                import tkinter as tk

                root_absent = isinstance(
                    e, tk.TclError
                ) and "application has been destroyed" in str(e)
        self.closed = True
        self.backend.stop_accepting()
        if self.root is not None and self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception as e:
                self.backend.logger.debug("起動poll取消し: %s", e)
        with self._lock:
            for item in tuple(self._pending.values()):
                self._finish(item, "expired", self.backend.tick_ms())
        self.backend.close(root_absent=root_absent)
