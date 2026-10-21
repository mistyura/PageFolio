"""Tk に依存しない起動要求と、メインスレッドへの有界受け渡し。"""

from dataclasses import asdict, dataclass
from queue import Empty, Full, Queue
from threading import Event
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


@dataclass(frozen=True)
class StartupOutcome:
    result: str
    primary: bool = False


@dataclass
class _QueuedActivation:
    request: ActivationRequest
    finished: Event
    result: str = "expired"


class StartupCoordinator:
    """worker は Queue のみを使い、Tk API は起動スレッドだけが呼ぶ。"""

    def __init__(self, backend):
        self.backend = backend
        self.queue = Queue(maxsize=32)
        self.root = None
        self.after_id = None
        self.closed = False
        self.generation = uuid4().hex

    def claim(self):
        result = self.backend.claim(self.generation)
        if result == "acquired":
            self.backend.listen(self._receive)
            return StartupOutcome("primary", True)
        return StartupOutcome(result)

    def request_activation(self, started_tick):
        return StartupOutcome(self.backend.request_activation(started_tick))

    def _receive(self, raw):
        if self.closed:
            return {"request_id": raw.get("request_id"), "result": "expired"}
        try:
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
        ):
            return asdict(ActivationReply(request.request_id, "expired"))
        item = _QueuedActivation(request, Event())
        try:
            self.queue.put_nowait(item)
        except Full:
            return asdict(ActivationReply(request.request_id, "busy"))
        item.finished.wait(max(0, request.deadline_tick - now) / 1000)
        return asdict(ActivationReply(request.request_id, item.result))

    def attach_tk(self, root):
        self.root = root
        self.backend.publish_state("ready", True)
        self._poll()

    def _poll(self):
        self.after_id = None
        if self.closed:
            return
        while True:
            try:
                item = self.queue.get_nowait()
            except Empty:
                break
            if self.backend.tick_ms() < item.request.deadline_tick:
                item.result = self.backend.restore_window(self.root.winfo_id())
            item.finished.set()
        self.after_id = self.root.after(50, self._poll)

    def close(self):
        self.closed = True
        if self.root is not None and self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception as e:
                self.backend.logger.debug("起動poll取消し: %s", e)
        while True:
            try:
                item = self.queue.get_nowait()
            except Empty:
                break
            item.finished.set()
        self.backend.close()
