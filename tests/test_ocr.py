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
