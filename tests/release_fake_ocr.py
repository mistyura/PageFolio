"""配布EXE受入用の合成OCRサーバ（127.0.0.1専用）と合成PDFの生成。

製品は未改変のまま、既存のOllama設定（ollama_url / ollama_model）経由で接続する。
既存プロバイダが使うHTTP形状だけを返す。

- ``GET /v1/models``            -> ``{"data": [{"id": <model>}]}``
- ``POST /v1/chat/completions`` -> ``{"choices": [{"message": {"content": ...},
  "finish_reason": "stop"}]}``

外部へは一切転送しない（クライアントコードを持たない）。画像本体は保存せず、SHA-256だけを
記録する。受理する画像は準備した1ページ分に限り、それ以外は拒否して記録する。
単体試験・fixtureの成功は実配布EXEの成功ではない。実接続の実証は06-04-02で別に行う。
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import struct
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL = "pagefolio-uat-fixture"
LOOPBACK = "127.0.0.1"
PROVIDER_TIMEOUT = 120  # 既存 ocr_timeout の既定値
RESULT_TEXT = "PageFolio UAT 合成OCR結果"
_PNG = b"\x89PNG\r\n\x1a\n"
_MAX_BODY = 32 * 1024 * 1024
_MAX_EDGE = 8000
MODES = ("success", "hold", "error")


def _now():
    return datetime.now(timezone.utc).isoformat()


def png_size(data):
    """PNGシグネチャとIHDRだけを検査し (幅, 高さ) を返す。不正なら None。"""
    if len(data) < 24 or not data.startswith(_PNG) or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    if not (0 < width <= _MAX_EDGE and 0 < height <= _MAX_EDGE):
        return None
    return width, height


def extract_image(payload):
    """既存 _build_payload 形状の画像data URLをdecodeして返す。無ければNone。"""
    try:
        content = payload["messages"][0]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, list):
        return None
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "image_url":
            continue
        url = (item.get("image_url") or {}).get("url", "")
        prefix = "data:image/png;base64,"
        if not isinstance(url, str) or not url.startswith(prefix):
            return None
        try:
            return base64.b64decode(url[len(prefix) :], validate=True)
        except (binascii.Error, ValueError):
            return None
    return None


class FakeOcrServer:
    """loopback専用。待機/成功/エラー応答と、画像hash・page・attempt単位の記録を持つ。"""

    def __init__(
        self,
        *,
        mode="success",
        run_id="",
        log_path=None,
        release_flag=None,
        provider_timeout=PROVIDER_TIMEOUT,
        hold_limit=None,
        error_status=400,
        expected_pages=1,
        host=LOOPBACK,
        port=0,
    ):
        if host != LOOPBACK:
            raise ValueError("fake OCRは127.0.0.1以外にlistenしません")
        if mode not in MODES:
            raise ValueError(f"未対応のmode: {mode}")
        if hold_limit is None:
            hold_limit = max(1, min(90, provider_timeout - 10))
        if hold_limit >= provider_timeout:
            raise ValueError("待機上限はprovider timeoutより短くする必要があります")
        if mode == "error" and error_status in (429,) + tuple(range(500, 600)):
            # 通常ケースで429/5xxは出さない。再送を誘発する応答は指定できない。
            raise ValueError("error応答に429/5xxは使えません(再送を誘発する)")
        self.mode = mode
        self.run_id = run_id
        self.log_path = Path(log_path) if log_path else None
        self.release_flag = Path(release_flag) if release_flag else None
        self.hold_limit = hold_limit
        self.error_status = error_status
        self.expected_pages = expected_pages
        self.events = []
        self._lock = threading.Lock()
        self._release = threading.Event()
        self._pages = {}  # image sha256 -> page_id
        self._registered = {}  # 事前登録した描画hash -> page_id
        self._attempts = {}
        self._seq = 0
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # 標準エラーへ出さない
                return

            def _send(self, status, body):
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionError, OSError):
                    pass

            def do_GET(self):
                if self.client_address[0] != LOOPBACK:
                    return self._send(403, {"error": "loopback only"})
                if self.path.rstrip("/") == "/v1/models":
                    server._record("models", path=self.path)
                    return self._send(
                        200,
                        {"object": "list", "data": [{"id": MODEL, "object": "model"}]},
                    )
                self._send(404, {"error": "not found"})

            def do_POST(self):
                if self.client_address[0] != LOOPBACK:
                    return self._send(403, {"error": "loopback only"})
                if self.path.rstrip("/") != "/v1/chat/completions":
                    return self._send(404, {"error": "not found"})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= _MAX_BODY:
                        raise ValueError
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    server._record("rejected", reason="bad-body")
                    return self._send(400, {"error": "bad request"})
                status, body = server._handle_chat(payload)
                self._send(status, body)

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        self._thread = None

    # -- 記録 -------------------------------------------------------------
    def _record(self, event, **fields):
        with self._lock:
            self._seq += 1
            item = {
                "seq": self._seq,
                "event": event,
                "time": _now(),
                "monotonic": time.monotonic(),
                "run_id": self.run_id,
                "mode": self.mode,
                **fields,
            }
            self.events.append(item)
            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        return item

    # -- 公開API ------------------------------------------------------------
    @property
    def port(self):
        return self._httpd.server_address[1]

    @property
    def url(self):
        return f"http://{LOOPBACK}:{self.port}"

    def allow_image(self, sha256, page_id="p1"):
        """描画結果のhashを事前に分かっている場合だけ厳格に登録する。"""
        with self._lock:
            self._registered[sha256] = page_id

    def start(self):
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._release.set()
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def release(self):
        self._release.set()

    def wait_received(self, count=1, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.summary()["posts"] >= count:
                return True
            time.sleep(0.02)
        return False

    def summary(self):
        with self._lock:
            events = list(self.events)
        received = [e for e in events if e["event"] == "received"]
        attempts = {}
        for item in received:
            attempts.setdefault(item["image_sha256"], []).append(item["attempt_id"])
        return {
            "posts": len(received),
            "rejected": [e for e in events if e["event"] == "rejected"],
            "attempts_by_image": {k: len(v) for k, v in attempts.items()},
            "retransmissions": [
                {"image_sha256": k, "attempt_ids": v}
                for k, v in attempts.items()
                if len(v) > 1
            ],
            "completed": [e["attempt_id"] for e in events if e["event"] == "completed"],
            "released": [e["attempt_id"] for e in events if e["event"] == "released"],
            "expired": [e["attempt_id"] for e in events if e["event"] == "expired"],
            "events": events,
        }

    def single_attempt_ok(self, pages=1):
        """通常ケースの期待: 論理ページ数ぶんのPOSTで再送・拒否・期限切れが無い。"""
        data = self.summary()
        reasons = []
        if data["posts"] != pages:
            reasons.append(f"POST数が{data['posts']}件(期待{pages}件)")
        if data["retransmissions"]:
            reasons.append("再送が発生した")
        if data["rejected"]:
            reasons.append("拒否された要求がある")
        if data["expired"]:
            reasons.append("待機上限に到達した")
        if len(data["completed"]) != data["posts"]:
            reasons.append("未完了のattemptがある")
        return not reasons, reasons

    # -- 内部 -------------------------------------------------------------
    def _bind_page(self, image_hash):
        with self._lock:
            if image_hash in self._registered:
                return self._registered[image_hash]
            if self._registered:
                return None  # 厳格モード: 登録外は拒否
            if image_hash in self._pages:
                return self._pages[image_hash]
            if len(self._pages) >= self.expected_pages:
                return None  # 対象ページ数を超える別画像
            page_id = f"p{len(self._pages) + 1}"
            self._pages[image_hash] = page_id
            return page_id

    def _handle_chat(self, payload):
        image = extract_image(payload)
        if image is None or png_size(image) is None:
            self._record("rejected", reason="no-synthetic-png")
            return 400, {"error": {"message": "unsupported input"}}
        image_hash = hashlib.sha256(image).hexdigest()
        page_id = self._bind_page(image_hash)
        if page_id is None:
            self._record("rejected", reason="unexpected-image", image_sha256=image_hash)
            return 409, {"error": {"message": "unexpected image"}}
        with self._lock:
            number = self._attempts.get(image_hash, 0) + 1
            self._attempts[image_hash] = number
        attempt_id = f"{image_hash[:12]}-{number}"
        request_id = uuid.uuid4().hex
        ids = {
            "request_id": request_id,
            "attempt_id": attempt_id,
            "image_sha256": image_hash,
            "page_id": page_id,
        }
        self._record("received", **ids)
        if self.mode == "error":
            self._record("completed", status=self.error_status, **ids)
            return self.error_status, {"error": {"message": "fixture error"}}
        if self.mode == "hold":
            if not self._wait_release():
                self._record("expired", hold_limit=self.hold_limit, **ids)
            else:
                self._record("released", **ids)
        body = {
            "id": request_id,
            "object": "chat.completion",
            "model": MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": RESULT_TEXT},
                    "finish_reason": "stop",
                }
            ],
        }
        self._record("completed", status=200, **ids)
        return 200, body

    def _wait_release(self):
        deadline = time.monotonic() + self.hold_limit
        while time.monotonic() < deadline:
            if self._release.wait(0.1):
                return True
            if self.release_flag is not None and self.release_flag.exists():
                return True
        return False


# -- 合成PDF ----------------------------------------------------------------
def make_one_page_image_pdf(path, *, label="PageFolio UAT"):
    """埋込文字のない1ページの画像PDF。OCR接続/W04/W05b用。"""
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=64)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((60, 80), label, fill="black", font=font)
    draw.text((60, 240), "OCR TEST 0123456789", fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    document = fitz.open()
    try:
        page = document.new_page(width=300, height=400)
        page.insert_image(page.rect, stream=buffer.getvalue())
        document.save(str(path))
    finally:
        document.close()
    return pdf_facts(path)


def make_text_pdf(path, *, pages=3):
    """未保存編集(W03)用の複数ページPDF。OCR用とは別fixture。"""
    import fitz

    document = fitz.open()
    try:
        for number in range(1, pages + 1):
            page = document.new_page(width=300, height=400)
            page.insert_text((40, 80), f"UAT edit page {number}")
        document.save(str(path))
    finally:
        document.close()
    return pdf_facts(path)


def pdf_facts(path):
    import fitz

    path = Path(path)
    document = fitz.open(str(path))
    try:
        embedded = any(page.get_text().strip() for page in document)
        facts = {
            "pages": document.page_count,
            "has_embedded_text": embedded,
            "images_on_first_page": len(document[0].get_images()),
        }
    finally:
        document.close()
    facts["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="試験run directory")
    parser.add_argument("--mode", choices=MODES, default="hold")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--provider-timeout", type=int, default=PROVIDER_TIMEOUT)
    parser.add_argument("--serve-seconds", type=float, default=3600.0)
    args = parser.parse_args(argv)
    evidence = args.run / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    server = FakeOcrServer(
        mode=args.mode,
        run_id=args.run_id,
        log_path=evidence / "fake-ocr-events.jsonl",
        release_flag=args.run / "release.flag",
        provider_timeout=args.provider_timeout,
        port=args.port,
    ).start()
    info = {
        "url": server.url,
        "port": server.port,
        "mode": args.mode,
        "started": _now(),
    }
    (args.run / "fake-ocr.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps(info, ensure_ascii=False), flush=True)
    stop_flag = args.run / "stop-fake-ocr.flag"
    deadline = time.monotonic() + args.serve_seconds
    try:
        while time.monotonic() < deadline and not stop_flag.exists():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        summary = server.summary()
        server.stop()
        (evidence / "fake-ocr-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
