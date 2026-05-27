"""OCR モジュール（LM Studio クライアント）のユニットテスト"""

import base64
import io
import json
import os
import socket
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio import ocr  # noqa: E402

# ===== ペイロード組み立て =====


class TestBuildChatPayload:
    """build_chat_payload の構造を確認する"""

    def test_image_url_uses_data_uri(self):
        payload = ocr.build_chat_payload("llava", "ZmFrZWltYWdl", "describe")
        content = payload["messages"][0]["content"]
        # 1要素目: image_url、2要素目: text
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert content[0]["image_url"]["url"].endswith("ZmFrZWltYWdl")
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "describe"

    def test_model_fallback(self):
        """空のモデル名は 'local-model' にフォールバック"""
        payload = ocr.build_chat_payload("", "abc", "p")
        assert payload["model"] == "local-model"

    def test_role_is_user(self):
        payload = ocr.build_chat_payload("m", "a", "p")
        assert payload["messages"][0]["role"] == "user"

    def test_max_tokens_default(self):
        """max_tokens 未指定なら -1（無制限）"""
        payload = ocr.build_chat_payload("m", "a", "p")
        assert payload["max_tokens"] == -1

    def test_max_tokens_custom(self):
        payload = ocr.build_chat_payload("m", "a", "p", max_tokens=4096)
        assert payload["max_tokens"] == 4096

    def test_temperature_default(self):
        """temperature 未指定なら 0.1（OCR 推奨値）"""
        payload = ocr.build_chat_payload("m", "a", "p")
        assert payload["temperature"] == 0.1

    def test_temperature_custom(self):
        payload = ocr.build_chat_payload("m", "a", "p", temperature=0.5)
        assert payload["temperature"] == 0.5


# ===== ページ → PNG base64 =====


class TestPageToPngB64:
    """page_to_png_b64 が有効な base64 PNG を返すか"""

    def test_returns_valid_base64_png(self, sample_pdf_doc):
        page = sample_pdf_doc[0]
        b64 = ocr.page_to_png_b64(page, scale=1.0)
        assert isinstance(b64, str)
        raw = base64.b64decode(b64)
        # PNG マジックナンバー
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"

    def test_scale_affects_size(self, sample_pdf_doc):
        """倍率を上げるとファイルサイズが大きくなる"""
        page = sample_pdf_doc[0]
        small = base64.b64decode(ocr.page_to_png_b64(page, scale=1.0))
        large = base64.b64decode(ocr.page_to_png_b64(page, scale=3.0))
        assert len(large) > len(small)


# ===== call_lm_studio（モック） =====


class _FakeResponse:
    """urllib.request.urlopen の文脈マネージャーをモック"""

    def __init__(self, body):
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


class TestCallLmStudio:
    """call_lm_studio のレスポンス処理と例外マッピング"""

    def test_success_returns_content(self, monkeypatch):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["data"] = req.data
            captured["timeout"] = timeout
            body = json.dumps({"choices": [{"message": {"content": "hello world"}}]})
            return _FakeResponse(body)

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        text = ocr.call_lm_studio("http://localhost:1234", "m", "Zg==", "p", timeout=5)
        assert text == "hello world"
        assert captured["url"] == "http://localhost:1234/v1/chat/completions"
        assert captured["timeout"] == 5
        sent = json.loads(captured["data"].decode("utf-8"))
        assert sent["messages"][0]["content"][1]["text"] == "p"

    def test_connection_error_raises_connection_error(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(ConnectionError):
            ocr.call_lm_studio("http://x", "m", "Zg==", "p")

    def test_socket_timeout_raises_timeout_error(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(TimeoutError):
            ocr.call_lm_studio("http://x", "m", "Zg==", "p", timeout=1)

    def test_urlerror_with_timeout_reason_raises_timeout(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError(socket.timeout("inner"))

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(TimeoutError):
            ocr.call_lm_studio("http://x", "m", "Zg==", "p", timeout=1)

    def test_http_error_raises_runtime_error(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                "http://x", 500, "Server Error", {}, io.BytesIO(b"oops")
            )

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(RuntimeError) as ei:
            ocr.call_lm_studio("http://x", "m", "Zg==", "p")
        assert "500" in str(ei.value)

    def test_malformed_response_raises_runtime_error(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            return _FakeResponse("{}")  # choices 無し

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(RuntimeError):
            ocr.call_lm_studio("http://x", "m", "Zg==", "p")


# ===== fetch_lm_studio_models（モック） =====


class TestCallLmStudioParallel:
    """call_lm_studio_parallel の並列実行・順序保持・キャンセル・致命的エラー処理"""

    def test_empty_inputs_return_empty(self, monkeypatch):
        results, errors, fm, fk = ocr.call_lm_studio_parallel(
            "http://x", "m", "p", images_b64={}, page_indices=[]
        )
        assert results == {}
        assert errors == {}
        assert fm is None and fk is None

    def test_all_succeed_preserves_results_by_page_idx(self, monkeypatch):
        """ページごとに正しい結果が返り、入力順に依らず辞書で取得できる"""

        def fake_call(url, model, b64, prompt, **kw):
            return f"text-{b64}"

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        images = {0: "A", 2: "B", 5: "C"}
        results, errors, fm, fk = ocr.call_lm_studio_parallel(
            "http://x",
            "m",
            "p",
            images,
            page_indices=[0, 2, 5],
            concurrency=3,
        )
        assert results == {0: "text-A", 2: "text-B", 5: "text-C"}
        assert errors == {}
        assert fm is None

    def test_concurrency_actually_parallel(self, monkeypatch):
        """concurrency=4 で 4 件並列に走ること（同時実行数の最大値で検証）"""
        import threading
        import time

        in_flight = 0
        max_in_flight = 0
        lock = threading.Lock()

        def fake_call(url, model, b64, prompt, **kw):
            nonlocal in_flight, max_in_flight
            with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return b64

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        images = {i: f"img{i}" for i in range(4)}
        results, _, _, _ = ocr.call_lm_studio_parallel(
            "http://x", "m", "p", images, page_indices=list(range(4)), concurrency=4
        )
        assert len(results) == 4
        assert max_in_flight >= 2  # 少なくとも 2 件は並列で走った

    def test_runtime_error_is_per_page_not_fatal(self, monkeypatch):
        """RuntimeError は当該ページのみ errors に記録、他ページは継続"""

        def fake_call(url, model, b64, prompt, **kw):
            if b64 == "BAD":
                raise RuntimeError("HTTP 500: oops")
            return f"ok-{b64}"

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        images = {0: "A", 1: "BAD", 2: "C"}
        results, errors, fm, fk = ocr.call_lm_studio_parallel(
            "http://x", "m", "p", images, page_indices=[0, 1, 2], concurrency=2
        )
        assert results == {0: "ok-A", 2: "ok-C"}
        assert 1 in errors
        assert "HTTP 500" in errors[1]
        assert fm is None

    def test_connection_error_is_fatal(self, monkeypatch):
        """ConnectionError は fatal_msg に記録され、kind='connection'"""

        def fake_call(url, model, b64, prompt, **kw):
            raise ConnectionError("refused")

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        results, errors, fm, fk = ocr.call_lm_studio_parallel(
            "http://x", "m", "p", {0: "A"}, page_indices=[0], concurrency=1
        )
        assert fm is not None
        assert "refused" in fm
        assert fk == "connection"

    def test_timeout_error_is_fatal(self, monkeypatch):
        def fake_call(url, model, b64, prompt, **kw):
            raise TimeoutError("timed out")

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        _, _, fm, fk = ocr.call_lm_studio_parallel(
            "http://x", "m", "p", {0: "A"}, page_indices=[0], concurrency=1
        )
        assert fm is not None
        assert fk == "timeout"

    def test_cancel_stops_submission(self, monkeypatch):
        """is_cancelled() が True を返すと以降の呼び出しはスキップされる"""
        import threading

        call_count = {"n": 0}
        lock = threading.Lock()
        cancel = threading.Event()

        def fake_call(url, model, b64, prompt, **kw):
            with lock:
                call_count["n"] += 1
                if call_count["n"] >= 1:
                    cancel.set()
            return b64

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        images = {i: f"img{i}" for i in range(10)}
        results, _, _, _ = ocr.call_lm_studio_parallel(
            "http://x",
            "m",
            "p",
            images,
            page_indices=list(range(10)),
            concurrency=1,
            is_cancelled=cancel.is_set,
        )
        # キャンセル後の呼び出しは "cancel" として results に入らない
        assert len(results) < 10

    def test_progress_callback_called_for_each_done(self, monkeypatch):
        def fake_call(url, model, b64, prompt, **kw):
            return b64

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        calls = []

        def on_progress(done, page_idx, status):
            calls.append((done, page_idx, status))

        images = {0: "A", 1: "B", 2: "C"}
        ocr.call_lm_studio_parallel(
            "http://x",
            "m",
            "p",
            images,
            page_indices=[0, 1, 2],
            concurrency=1,
            on_progress=on_progress,
        )
        assert len(calls) == 3
        # done は 1, 2, 3 とインクリメントされる
        assert [c[0] for c in calls] == [1, 2, 3]
        assert all(c[2] == "ok" for c in calls)

    def test_concurrency_clamped_to_max(self, monkeypatch):
        """concurrency > MAX_OCR_CONCURRENCY は MAX にクランプされる（落ちずに動く）"""

        def fake_call(url, model, b64, prompt, **kw):
            return b64

        monkeypatch.setattr(ocr, "call_lm_studio", fake_call)
        images = {i: f"i{i}" for i in range(3)}
        results, _, _, _ = ocr.call_lm_studio_parallel(
            "http://x",
            "m",
            "p",
            images,
            page_indices=[0, 1, 2],
            concurrency=999,
        )
        assert len(results) == 3

    def test_default_concurrency_constant(self):
        """DEFAULT_OCR_CONCURRENCY / MAX_OCR_CONCURRENCY が公開されている"""
        assert ocr.DEFAULT_OCR_CONCURRENCY == 2
        assert ocr.MAX_OCR_CONCURRENCY == 8


class TestFetchModels:
    def test_returns_model_ids(self, monkeypatch):
        body = json.dumps(
            {"data": [{"id": "llava-v1.6"}, {"id": "qwen-vl"}, {"id": None}]}
        )

        def fake_urlopen(req, timeout=None):
            assert req.full_url == "http://localhost:1234/v1/models"
            return _FakeResponse(body)

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        ids = ocr.fetch_lm_studio_models("http://localhost:1234")
        assert ids == ["llava-v1.6", "qwen-vl"]

    def test_connection_failure(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("refused")

        monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(ConnectionError):
            ocr.fetch_lm_studio_models("http://x")
