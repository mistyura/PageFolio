"""OCRProvider 抽象基底クラス・OCRAPIKeyError・LMStudioProvider のユニットテスト"""

import abc
import io
import json
import socket
import urllib.error

import pytest  # noqa: F401 (used for pytest.raises)

# ===== Task 1: OCRProvider 抽象基底クラス + OCRAPIKeyError =====


class TestOCRProviderAbstract:
    """OCRProvider 抽象基底クラスの構造を確認する"""

    def test_is_abc_subclass(self):
        """OCRProvider は abc.ABC のサブクラスであること"""
        from pagefolio.ocr_providers import OCRProvider

        assert issubclass(OCRProvider, abc.ABC)

    def test_ocr_image_is_abstract(self):
        """ocr_image が抽象メソッドのため未実装サブクラスはインスタンス化不可"""
        from pagefolio.ocr_providers import OCRProvider

        class Partial(OCRProvider):
            def list_models(self):
                return []

        with pytest.raises(TypeError):
            Partial()

    def test_list_models_is_abstract(self):
        """list_models が抽象メソッドのため未実装サブクラスはインスタンス化不可"""
        from pagefolio.ocr_providers import OCRProvider

        class Partial(OCRProvider):
            def ocr_image(self, b64_png, prompt, **kwargs):
                return ""

        with pytest.raises(TypeError):
            Partial()

    def test_default_concurrency_is_int(self):
        """default_concurrency がクラス属性として int で定義されている"""
        from pagefolio.ocr_providers import OCRProvider

        assert isinstance(OCRProvider.default_concurrency, int)

    def test_max_concurrency_is_int(self):
        """max_concurrency がクラス属性として int で定義されている"""
        from pagefolio.ocr_providers import OCRProvider

        assert isinstance(OCRProvider.max_concurrency, int)

    def test_both_abstract_implemented_instantiates(self):
        """両抽象メソッドを実装すればインスタンス化できる"""
        from pagefolio.ocr_providers import OCRProvider

        class Concrete(OCRProvider):
            def ocr_image(self, b64_png, prompt, **kwargs):
                return "text"

            def list_models(self):
                return []

        obj = Concrete()
        assert obj is not None


class TestOCRAPIKeyError:
    """OCRAPIKeyError の構造を確認する"""

    def test_is_runtime_error_subclass(self):
        """OCRAPIKeyError は RuntimeError のサブクラスであること"""
        from pagefolio.ocr_providers import OCRAPIKeyError

        assert issubclass(OCRAPIKeyError, RuntimeError)

    def test_env_var_attribute(self):
        """env_var 属性に渡した環境変数名を保持する"""
        from pagefolio.ocr_providers import OCRAPIKeyError

        e = OCRAPIKeyError("FOO_KEY")
        assert e.env_var == "FOO_KEY"

    def test_message_contains_env_var(self):
        """例外メッセージに環境変数名が含まれる"""
        from pagefolio.ocr_providers import OCRAPIKeyError

        e = OCRAPIKeyError("BAR_KEY")
        assert "BAR_KEY" in str(e)


# ===== Task 2: LMStudioProvider =====


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


class TestLMStudioProviderBasic:
    """LMStudioProvider の基本属性とインターフェース準拠を確認する"""

    def test_is_ocr_provider_subclass(self):
        """LMStudioProvider は OCRProvider のサブクラスであること"""
        from pagefolio.ocr_providers import LMStudioProvider, OCRProvider

        assert issubclass(LMStudioProvider, OCRProvider)

    def test_instantiation(self):
        """LMStudioProvider がインスタンス化できる"""
        from pagefolio.ocr_providers import LMStudioProvider

        p = LMStudioProvider("http://localhost:1234", "m")
        assert p is not None

    def test_default_concurrency(self):
        """default_concurrency == 2（現行 DEFAULT_OCR_CONCURRENCY と一致）"""
        from pagefolio.ocr_providers import LMStudioProvider

        assert LMStudioProvider.default_concurrency == 2

    def test_max_concurrency(self):
        """max_concurrency == 8（現行 MAX_OCR_CONCURRENCY と一致）"""
        from pagefolio.ocr_providers import LMStudioProvider

        assert LMStudioProvider.max_concurrency == 8


class TestLMStudioProviderOcrImage:
    """LMStudioProvider.ocr_image の振る舞いを確認する"""

    def test_success_returns_content(self, monkeypatch):
        """正常レスポンスから choices[0].message.content を返す"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps({"choices": [{"message": {"content": "hello world"}}]})
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        result = p.ocr_image("Zg==", "describe")
        assert result == "hello world"

    def test_payload_has_data_uri(self, monkeypatch):
        """送信 payload に data:image/png;base64, で始まる image_url が含まれる"""
        from pagefolio import ocr_providers

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["data"] = json.loads(req.data.decode("utf-8"))
            body = json.dumps({"choices": [{"message": {"content": "ok"}}]})
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        p.ocr_image("ZmFrZQ==", "test prompt")

        content = captured["data"]["messages"][0]["content"]
        image_part = next(c for c in content if c["type"] == "image_url")
        assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
        assert image_part["image_url"]["url"].endswith("ZmFrZQ==")
        text_part = next(c for c in content if c["type"] == "text")
        assert text_part["text"] == "test prompt"

    def test_empty_model_fallback(self, monkeypatch):
        """model が空のとき 'local-model' にフォールバックする"""
        from pagefolio import ocr_providers

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["data"] = json.loads(req.data.decode("utf-8"))
            body = json.dumps({"choices": [{"message": {"content": "ok"}}]})
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "")
        p.ocr_image("Zg==", "p")
        assert captured["data"]["model"] == "local-model"

    def test_connection_error(self, monkeypatch):
        """接続失敗で ConnectionError を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(ConnectionError):
            p.ocr_image("Zg==", "p")

    def test_socket_timeout_raises_timeout_error(self, monkeypatch):
        """socket.timeout で TimeoutError を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "p")

    def test_urlerror_timeout_reason(self, monkeypatch):
        """URLError の reason が socket.timeout なら TimeoutError を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError(socket.timeout("inner timeout"))

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "p")

    def test_http_error_raises_runtime_error(self, monkeypatch):
        """HTTPError で RuntimeError（HTTP コード含む）を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                "http://x", 500, "Server Error", {}, io.BytesIO(b"oops")
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(RuntimeError) as ei:
            p.ocr_image("Zg==", "p")
        assert "500" in str(ei.value)

    def test_malformed_response_raises_runtime_error(self, monkeypatch):
        """不正レスポンス形式で RuntimeError を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            return _FakeResponse("{}")  # choices 無し

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(RuntimeError):
            p.ocr_image("Zg==", "p")


class TestLMStudioProviderListModels:
    """LMStudioProvider.list_models の振る舞いを確認する"""

    def test_returns_model_ids(self, monkeypatch):
        """正常レスポンスからモデル ID リストを返す（None id は除外）"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {"data": [{"id": "llava-v1.6"}, {"id": "qwen-vl"}, {"id": None}]}
        )

        def fake_urlopen(req, timeout=None):
            assert "/v1/models" in req.full_url
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        ids = p.list_models()
        assert ids == ["llava-v1.6", "qwen-vl"]

    def test_connection_failure(self, monkeypatch):
        """接続失敗で ConnectionError を raise する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(ConnectionError):
            p.list_models()


# ===== Task 1: OCRRetryableError =====


class TestOCRRetryableError:
    """OCRRetryableError の構造と属性を確認する"""

    def test_is_runtime_error_subclass(self):
        """OCRRetryableError は RuntimeError のサブクラスであること"""
        from pagefolio.ocr_providers import OCRRetryableError

        assert issubclass(OCRRetryableError, RuntimeError)

    def test_retry_after_with_value(self):
        """retry_after 引数を指定するとその値を保持する"""
        from pagefolio.ocr_providers import OCRRetryableError

        e = OCRRetryableError("429 Too Many Requests", retry_after=5.0)
        assert e.retry_after == 5.0

    def test_retry_after_default_none(self):
        """retry_after 省略時は None になる"""
        from pagefolio.ocr_providers import OCRRetryableError

        e = OCRRetryableError("503 Service Unavailable")
        assert e.retry_after is None

    def test_message_preserved(self):
        """例外メッセージが正しく保持される"""
        from pagefolio.ocr_providers import OCRRetryableError

        e = OCRRetryableError("レート制限超過")
        assert "レート制限超過" in str(e)


# ===== Task 1: ClaudeProvider 骨格（payload 構築・effort 判定）=====


class TestClaudeProviderBasic:
    """ClaudeProvider の基本属性とクラス定数を確認する"""

    def test_is_ocr_provider_subclass(self):
        """ClaudeProvider は OCRProvider のサブクラスであること"""
        from pagefolio.ocr_providers import ClaudeProvider, OCRProvider

        assert issubclass(ClaudeProvider, OCRProvider)

    def test_default_concurrency(self):
        """default_concurrency == 2（OCR-PERF-03 Claude=2）"""
        from pagefolio.ocr_providers import ClaudeProvider

        assert ClaudeProvider.default_concurrency == 2

    def test_max_concurrency(self):
        """max_concurrency == 2（OCR-PERF-03 Claude=2 上限）"""
        from pagefolio.ocr_providers import ClaudeProvider

        assert ClaudeProvider.max_concurrency == 2

    def test_anthropic_version_constant(self):
        """ANTHROPIC_VERSION が '2023-06-01' であること"""
        from pagefolio.ocr_providers import ClaudeProvider

        assert ClaudeProvider.ANTHROPIC_VERSION == "2023-06-01"

    def test_messages_endpoint_constant(self):
        """MESSAGES_ENDPOINT が Anthropic messages API URL であること"""
        from pagefolio.ocr_providers import ClaudeProvider

        assert "api.anthropic.com/v1/messages" in ClaudeProvider.MESSAGES_ENDPOINT

    def test_recommended_models_contains_haiku_sonnet_opus(self):
        """RECOMMENDED_MODELS に haiku / sonnet / opus が含まれること"""
        from pagefolio.ocr_providers import ClaudeProvider

        ids = ClaudeProvider.RECOMMENDED_MODELS
        assert any("haiku" in m for m in ids)
        assert any("sonnet" in m for m in ids)
        assert any("opus" in m for m in ids)

    def test_instantiation(self):
        """ClaudeProvider がインスタンス化できる"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("test-key", "claude-sonnet-4-6")
        assert p is not None


class TestClaudeProviderSupportsEffort:
    """ClaudeProvider._supports_effort() のモデル別判定を確認する"""

    def test_haiku_not_supports_effort(self):
        """claude-haiku-4-5 は effort 非対応（D-16）"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-haiku-4-5")
        assert p._supports_effort() is False

    def test_sonnet_supports_effort(self):
        """claude-sonnet-4-6 は effort 対応"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        assert p._supports_effort() is True

    def test_opus_supports_effort(self):
        """claude-opus-4-8 は effort 対応"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-opus-4-8")
        assert p._supports_effort() is True


class TestClaudeProviderBuildPayload:
    """ClaudeProvider._build_payload() の構造を確認する"""

    def test_opus_payload_has_output_config_effort(self):
        """opus モデルは output_config.effort を含み temperature を含まない"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-opus-4-8")
        payload = p._build_payload("AAA", "テスト")
        assert "output_config" in payload
        assert payload["output_config"]["effort"] == "low"
        assert "temperature" not in payload

    def test_sonnet_payload_has_output_config_effort(self):
        """sonnet モデルは output_config.effort を含み temperature を含まない"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        payload = p._build_payload("AAA", "テスト")
        assert "output_config" in payload
        assert "effort" in payload["output_config"]
        assert "temperature" not in payload

    def test_haiku_payload_has_temperature_no_output_config(self):
        """haiku モデルは temperature を含み output_config を含まない（D-16）"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-haiku-4-5")
        payload = p._build_payload("AAA", "テスト")
        assert "temperature" in payload
        assert "output_config" not in payload

    def test_payload_has_model_and_max_tokens(self):
        """payload のトップレベルに model と max_tokens を持つ"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        payload = p._build_payload("AAA", "テスト")
        assert "model" in payload
        assert "max_tokens" in payload
        assert payload["model"] == "claude-sonnet-4-6"

    def test_payload_image_block_format(self):
        """content[0] が正しい base64 image ブロック形式であること"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        payload = p._build_payload("TestBase64==", "プロンプト")
        content = payload["messages"][0]["content"]
        image_block = content[0]
        assert image_block["type"] == "image"
        assert image_block["source"]["type"] == "base64"
        assert image_block["source"]["media_type"] == "image/png"
        assert image_block["source"]["data"] == "TestBase64=="

    def test_payload_text_block_format(self):
        """content[1] が正しいテキストブロック形式であること"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        payload = p._build_payload("AAA", "OCRプロンプト")
        content = payload["messages"][0]["content"]
        text_block = content[1]
        assert text_block["type"] == "text"
        assert text_block["text"] == "OCRプロンプト"


# ===== Task 2: ClaudeProvider.ocr_image / list_models =====


class _FakeClaudeResponse:
    """ClaudeProvider テスト用 urlopen 文脈マネージャーモック"""

    def __init__(self, body, headers=None):
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self._headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


class _FakeHTTPError(urllib.error.HTTPError):
    """テスト用 HTTPError モック（Retry-After ヘッダーをシミュレート）"""

    def __init__(self, code, reason="Error", body=b"", headers=None):
        self._body_bytes = body if isinstance(body, bytes) else body.encode("utf-8")
        self._fake_headers = headers or {}
        super().__init__("http://x", code, reason, {}, io.BytesIO(self._body_bytes))
        # headers 属性を差し替えてテスト用 dict で上書きする
        self.headers = self._fake_headers

    def read(self):
        return self._body_bytes


class TestClaudeProviderOcrImage:
    """ClaudeProvider.ocr_image の振る舞いを確認する"""

    def test_success_returns_text(self, monkeypatch):
        """正常レスポンス（type=='text' ブロック）から OCR テキストを返す"""
        from pagefolio import ocr_providers

        body = json.dumps({"content": [{"type": "text", "text": "OCR 結果テキスト"}]})

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("test-key", "claude-sonnet-4-6")
        result = p.ocr_image("Zg==", "テキストを書き出して")
        assert result == "OCR 結果テキスト"

    def test_mixed_content_joins_text_blocks(self, monkeypatch):
        """thinking+text 混在でも type=='text' ブロックのみ結合して返す（Pitfall 6）"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "content": [
                    {"type": "thinking", "thinking": "考え中..."},
                    {"type": "text", "text": "1行目"},
                    {"type": "text", "text": "2行目"},
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-opus-4-8")
        result = p.ocr_image("Zg==", "テスト")
        assert result == "1行目\n2行目"
        assert "thinking" not in result

    def test_429_raises_ocr_retryable_error(self, monkeypatch):
        """HTTP 429 応答で OCRRetryableError を送出する"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(429, "Too Many Requests", b"rate limit")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(OCRRetryableError):
            p.ocr_image("Zg==", "テスト")

    def test_429_with_retry_after_header(self, monkeypatch):
        """Retry-After ヘッダーがあれば retry_after に反映される"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(
                429, "Too Many Requests", b"rate limit", headers={"Retry-After": "3"}
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(OCRRetryableError) as ei:
            p.ocr_image("Zg==", "テスト")
        assert ei.value.retry_after == 3.0

    def test_503_raises_ocr_retryable_error(self, monkeypatch):
        """HTTP 503（5xx）応答で OCRRetryableError を送出する"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(503, "Service Unavailable", b"server error")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(OCRRetryableError):
            p.ocr_image("Zg==", "テスト")

    def test_400_raises_runtime_error_not_retryable(self, monkeypatch):
        """HTTP 400（4xx・429 以外）は RuntimeError（retryable ではない）"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(400, "Bad Request", b"invalid param")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(RuntimeError) as ei:
            p.ocr_image("Zg==", "テスト")
        # OCRRetryableError ではないことを確認
        from pagefolio.ocr_providers import OCRRetryableError

        assert not isinstance(ei.value, OCRRetryableError)

    def test_socket_timeout_raises_timeout_error(self, monkeypatch):
        """socket.timeout で TimeoutError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "テスト")

    def test_urlerror_raises_connection_error(self, monkeypatch):
        """URLError で ConnectionError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(ConnectionError):
            p.ocr_image("Zg==", "テスト")

    def test_request_headers_contain_required_fields(self, monkeypatch):
        """リクエストヘッダーに x-api-key と anthropic-version が含まれる"""
        from pagefolio import ocr_providers

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            body = json.dumps({"content": [{"type": "text", "text": "ok"}]})
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("my-api-key", "claude-sonnet-4-6")
        p.ocr_image("Zg==", "テスト")
        # urllib は先頭大文字に正規化するため大文字小文字を無視して確認
        header_keys_lower = {k.lower() for k in captured["headers"]}
        assert "x-api-key" in header_keys_lower
        assert "anthropic-version" in header_keys_lower


class TestClaudeProviderListModels:
    """ClaudeProvider.list_models の振る舞いを確認する"""

    def test_no_api_key_returns_recommended_models(self):
        """api_key が空文字のとき API を呼ばず RECOMMENDED_MODELS を返す（D-08）"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("", "claude-sonnet-4-6")
        result = p.list_models()
        assert result == list(ClaudeProvider.RECOMMENDED_MODELS)

    def test_no_api_key_none_returns_recommended_models(self):
        """api_key が None のとき API を呼ばず RECOMMENDED_MODELS を返す（D-08）"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(None, "claude-sonnet-4-6")
        result = p.list_models()
        assert result == list(ClaudeProvider.RECOMMENDED_MODELS)

    def test_with_api_key_filters_vision_capable_models(self, monkeypatch):
        """キー設定時は /v1/models を呼び vision 対応モデルのみ返す"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "data": [
                    {
                        "id": "claude-sonnet-4-6",
                        "capabilities": {"image_input": {"supported": True}},
                    },
                    {
                        "id": "claude-haiku-4-5",
                        "capabilities": {"image_input": {"supported": True}},
                    },
                    {
                        "id": "claude-text-only",
                        "capabilities": {"image_input": {"supported": False}},
                    },
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            assert "/v1/models" in req.full_url
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("my-key", "claude-sonnet-4-6")
        result = p.list_models()
        assert "claude-sonnet-4-6" in result
        assert "claude-haiku-4-5" in result
        assert "claude-text-only" not in result

    def test_connection_error_raises(self, monkeypatch):
        """接続失敗で ConnectionError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("valid-key", "claude-sonnet-4-6")
        with pytest.raises(ConnectionError):
            p.list_models()


# ===== Task 1 (06-01): GeminiProvider テスト（D-14・OCR-QA-01） =====


class TestGeminiProviderBasic:
    """GeminiProvider の基本属性とインターフェース準拠を確認する（D-14 ①基盤）"""

    def test_is_ocr_provider_subclass(self):
        """GeminiProvider は OCRProvider のサブクラスであること"""
        from pagefolio.ocr_providers import GeminiProvider, OCRProvider

        assert issubclass(GeminiProvider, OCRProvider)

    def test_instantiation(self):
        """GeminiProvider がインスタンス化できる"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        assert p is not None

    def test_default_concurrency(self):
        """default_concurrency == 1（D-07: Gemini Free Tier 10 RPM 対応）"""
        from pagefolio.ocr_providers import GeminiProvider

        assert GeminiProvider.default_concurrency == 1

    def test_max_concurrency(self):
        """max_concurrency == 1（D-07: 並列度上限）"""
        from pagefolio.ocr_providers import GeminiProvider

        assert GeminiProvider.max_concurrency == 1


class TestGeminiProviderBuildPayload:
    """GeminiProvider._build_payload の構造を確認する（D-14 ①）"""

    def test_inline_data_mime_type(self):
        """parts[0].inline_data.mime_type が 'image/png' であること"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_payload("ZmFrZQ==", "describe")
        parts = payload["contents"][0]["parts"]
        assert parts[0]["inline_data"]["mime_type"] == "image/png"

    def test_inline_data_data(self):
        """parts[0].inline_data.data が b64_png と一致すること"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_payload("ZmFrZQ==", "describe")
        parts = payload["contents"][0]["parts"]
        assert parts[0]["inline_data"]["data"] == "ZmFrZQ=="

    def test_text_part(self):
        """parts[1].text が prompt と一致すること"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_payload("ZmFrZQ==", "describe")
        parts = payload["contents"][0]["parts"]
        assert parts[1]["text"] == "describe"

    def test_thinking_budget_zero(self):
        """generationConfig.thinkingConfig.thinkingBudget == 0（D-09/Pitfall-C）"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_payload("b64", "p")
        assert payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0

    def test_x_goog_api_key_header(self, monkeypatch):
        """x-goog-api-key ヘッダーに api_key が設定される（D-05/T-06-01）"""
        from pagefolio import ocr_providers

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            body = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="test-key", model="gemini-2.5-flash")
        p.ocr_image("Zg==", "describe")
        # urllib は先頭大文字に正規化する場合があるため lower で比較
        header_keys_lower = {k.lower(): v for k, v in captured["headers"].items()}
        assert header_keys_lower.get("x-goog-api-key") == "test-key"

    def test_no_query_key_in_url(self, monkeypatch):
        """URL クエリパラメータ ?key= が使われないこと（D-05/T-06-01）"""
        from pagefolio import ocr_providers

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            body = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="test-key", model="gemini-2.5-flash")
        p.ocr_image("Zg==", "describe")
        assert "?key=" not in captured["url"]


class TestGeminiProviderOcrImage:
    """GeminiProvider.ocr_image の振る舞いを確認する（D-14 ②）"""

    def test_success_returns_joined_text(self, monkeypatch):
        """正常 candidates → parts[].text を改行結合して返す"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "行1"}, {"text": "行2"}]}}]}
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        result = p.ocr_image("Zg==", "describe")
        assert result == "行1\n行2"

    def test_empty_candidates_raises_runtime_error(self, monkeypatch):
        """candidates が空のとき RuntimeError を送出する（Pitfall-D/T-06-03）"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(RuntimeError):
            p.ocr_image("Zg==", "describe")

    def test_429_raises_ocr_retryable_error(self, monkeypatch):
        """HTTP 429 応答で OCRRetryableError を送出する"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(429, "Too Many Requests", b"rate limit")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(OCRRetryableError):
            p.ocr_image("Zg==", "describe")

    def test_503_raises_ocr_retryable_error(self, monkeypatch):
        """HTTP 503（5xx）応答で OCRRetryableError を送出する"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(503, "Service Unavailable", b"server error")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(OCRRetryableError):
            p.ocr_image("Zg==", "describe")

    def test_400_raises_runtime_error_not_retryable(self, monkeypatch):
        """HTTP 400（4xx・429 以外）は RuntimeError（retryable ではない）"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(400, "Bad Request", b"invalid param")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(RuntimeError) as ei:
            p.ocr_image("Zg==", "describe")
        from pagefolio.ocr_providers import OCRRetryableError

        assert not isinstance(ei.value, OCRRetryableError)

    def test_socket_timeout_raises_timeout_error(self, monkeypatch):
        """socket.timeout で TimeoutError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "describe")

    def test_urlerror_raises_connection_error(self, monkeypatch):
        """URLError で ConnectionError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(ConnectionError):
            p.ocr_image("Zg==", "describe")


class TestGeminiProviderListModels:
    """GeminiProvider.list_models の振る舞いを確認する（D-14 ③）"""

    def test_no_api_key_returns_recommended_models(self):
        """api_key が空文字のとき API を呼ばず RECOMMENDED_MODELS を返す（D-08）"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="", model="gemini-2.5-flash")
        result = p.list_models()
        assert result == list(GeminiProvider.RECOMMENDED_MODELS)

    def test_no_api_key_none_returns_recommended_models(self):
        """api_key が None のとき API を呼ばず RECOMMENDED_MODELS を返す（D-08）"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key=None, model="gemini-2.5-flash")
        result = p.list_models()
        assert result == list(GeminiProvider.RECOMMENDED_MODELS)

    def test_filters_by_generate_content_method(self, monkeypatch):
        """supportedGenerationMethods に generateContent を含むモデルのみ返す"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "models": [
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-pro",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/embedding-001",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="my-key", model="gemini-2.5-flash")
        result = p.list_models()
        assert "gemini-2.5-flash" in result
        assert "gemini-2.5-pro" in result
        assert "embedding-001" not in result

    def test_removes_models_prefix(self, monkeypatch):
        """'models/' プレフィックスを除去して返す"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "models": [
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    }
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="my-key", model="gemini-2.5-flash")
        result = p.list_models()
        assert result == ["gemini-2.5-flash"]

    def test_connection_error_raises(self, monkeypatch):
        """接続失敗で ConnectionError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("refused")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="valid-key", model="gemini-2.5-flash")
        with pytest.raises(ConnectionError):
            p.list_models()


# ===== Phase 7: TesseractProvider =====


class TestTesseractProviderBasic:
    """TesseractProvider の基本属性とインターフェース準拠を確認する（OCR-EXT-01）"""

    def test_is_ocr_provider_subclass(self):
        """TesseractProvider は OCRProvider のサブクラスであること"""
        from pagefolio.ocr_providers import OCRProvider, TesseractProvider

        assert issubclass(TesseractProvider, OCRProvider)

    def test_instantiation(self):
        """TesseractProvider がエラーなくインスタンス化できること"""
        from pagefolio.ocr_providers import TesseractProvider

        p = TesseractProvider()
        assert p is not None

    def test_default_concurrency(self):
        """default_concurrency == 1（CPU バウンド・シングルスレッド前提）"""
        from pagefolio.ocr_providers import TesseractProvider

        assert TesseractProvider.default_concurrency == 1

    def test_max_concurrency(self):
        """max_concurrency == 2"""
        from pagefolio.ocr_providers import TesseractProvider

        assert TesseractProvider.max_concurrency == 2

    def test_list_models(self):
        """list_models() が ["tesseract"] を返すこと"""
        from pagefolio.ocr_providers import TesseractProvider

        p = TesseractProvider()
        assert p.list_models() == ["tesseract"]

    def test_recommended_langs_is_list(self):
        """RECOMMENDED_LANGS がリストであること"""
        from pagefolio.ocr_providers import TesseractProvider

        assert isinstance(TesseractProvider.RECOMMENDED_LANGS, list)


class TestTesseractProviderOcrImage:
    """TesseractProvider.ocr_image の各動作ケースを検証する（OCR-EXT-01）"""

    def test_ocr_image_success(self, monkeypatch):
        """subprocess.run が rc=0 を返すとき OCR テキストが返ること"""
        from pagefolio import ocr_providers

        class FakeResult:
            returncode = 0
            stdout = b"OCR\n"
            stderr = b""

        def fake_run(cmd, input=None, capture_output=False, timeout=None):
            return FakeResult()

        monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
        p = ocr_providers.TesseractProvider()
        # base64 of 1x1 transparent PNG (valid base64 string)
        import base64

        result = p.ocr_image(base64.b64encode(b"fake_png").decode(), "describe")
        assert result == "OCR"

    def test_ocr_image_nonzero_returncode_raises_runtime_error(self, monkeypatch):
        """rc != 0 のとき RuntimeError が送出されること"""
        from pagefolio import ocr_providers

        class FakeResult:
            returncode = 1
            stdout = b""
            stderr = b"Error occurred"

        def fake_run(cmd, **kw):
            return FakeResult()

        monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
        p = ocr_providers.TesseractProvider()
        import base64

        with pytest.raises(RuntimeError):
            p.ocr_image(base64.b64encode(b"fake_png").decode(), "describe")

    def test_ocr_image_file_not_found_raises_runtime_error(self, monkeypatch):
        """FileNotFoundError → RuntimeError が送出されること"""
        from pagefolio import ocr_providers

        def fake_run(cmd, **kw):
            raise FileNotFoundError("tesseract")

        monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
        p = ocr_providers.TesseractProvider()
        import base64

        with pytest.raises(RuntimeError, match="tesseract コマンドが見つかりません"):
            p.ocr_image(base64.b64encode(b"fake_png").decode(), "describe")

    def test_ocr_image_timeout_raises_timeout_error(self, monkeypatch):
        """TimeoutExpired のとき TimeoutError が送出されること"""
        import subprocess

        from pagefolio import ocr_providers

        def fake_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 60)

        monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
        p = ocr_providers.TesseractProvider(timeout=60)
        import base64

        with pytest.raises(TimeoutError):
            p.ocr_image(base64.b64encode(b"fake_png").decode(), "describe")

    def test_lang_fallback_to_eng_when_jpn_not_available(self, monkeypatch):
        """_TESSERACT_LANGS に jpn がない場合 -l eng が渡されること（D-04）"""
        from pagefolio import ocr_providers

        monkeypatch.setattr(ocr_providers, "_TESSERACT_LANGS", frozenset({"eng"}))

        captured = {}

        class FakeResult:
            returncode = 0
            stdout = b"text\n"
            stderr = b""

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return FakeResult()

        monkeypatch.setattr(ocr_providers.subprocess, "run", fake_run)
        p = ocr_providers.TesseractProvider()
        import base64

        p.ocr_image(base64.b64encode(b"fake_png").decode(), "describe")
        assert "-l" in captured["cmd"]
        lang_idx = captured["cmd"].index("-l") + 1
        assert captured["cmd"][lang_idx] == "eng", (
            f"Expected 'eng' but got '{captured['cmd'][lang_idx]}'"
        )


# ===== M-3 回帰テスト: _supports_effort 厳格化 =====


class TestClaudeProviderSupportsEffortStrict:
    """M-3: _supports_effort が EFFORT_MODELS 完全一致のみ True を返す。

    - EFFORT_MODELS 外（claude-sonnet-4-5 等）は False
    - EFFORT_MODELS 内（claude-sonnet-4-6）は True
    - 未知モデル（claude-future-9）の payload に effort/temperature 不在
    - haiku は temperature を含む
    """

    def test_effort_models_outside_returns_false(self):
        """EFFORT_MODELS 外のモデルは False を返す（M-3）。"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(api_key="", model="claude-sonnet-4-5")
        assert p._supports_effort() is False

    def test_effort_models_inside_returns_true(self):
        """EFFORT_MODELS 内のモデルは True を返す（M-3）。"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(api_key="", model="claude-sonnet-4-6")
        assert p._supports_effort() is True

    def test_unknown_model_no_effort_no_temperature(self):
        """未知モデルの payload に output_config も temperature も含まれない。"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(api_key="", model="claude-future-9")
        payload = p._build_payload("b64", "prompt")
        assert "output_config" not in payload, "未知モデルに output_config が含まれた"
        assert "temperature" not in payload, "未知モデルに temperature が含まれた"

    def test_haiku_model_has_temperature(self):
        """haiku モデルの payload には temperature が含まれる。"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(api_key="", model="claude-haiku-4-5")
        payload = p._build_payload("b64", "prompt")
        assert "temperature" in payload, "haiku モデルに temperature が含まれない"
        assert "output_config" not in payload, "haiku モデルに output_config が含まれた"


# ===== M-4 回帰テスト: gemini-2.5-pro thinkingConfig 省略 =====


class TestGeminiProviderThinkingConfig:
    """M-4: gemini-2.5-pro 系では thinkingConfig が省略される。"""

    def test_pro_model_no_thinking_config(self):
        """gemini-2.5-pro の payload に thinkingConfig が含まれない（M-4）。"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="", model="gemini-2.5-pro")
        payload = p._build_payload("b64", "prompt")
        cfg = payload["generationConfig"]
        assert "thinkingConfig" not in cfg, (
            "gemini-2.5-pro の generationConfig に thinkingConfig が含まれた"
        )

    def test_flash_model_has_thinking_config(self):
        """gemini-2.5-flash の payload には thinkingConfig が含まれる。"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="", model="gemini-2.5-flash")
        payload = p._build_payload("b64", "prompt")
        cfg = payload["generationConfig"]
        assert "thinkingConfig" in cfg, (
            "gemini-2.5-flash の generationConfig に thinkingConfig が含まれない"
        )

    def test_gemma_model_no_thinking_config(self):
        """gemma 系モデルの payload に thinkingConfig が含まれない（H-7）。

        Gemini API 経由の gemma モデルは thinkingConfig 非対応で
        400 INVALID_ARGUMENT になるため省略する。
        """
        from pagefolio.ocr_providers import GeminiProvider

        for model in ("gemma-3-27b-it", "gemma-4-26b-it"):
            p = GeminiProvider(api_key="", model=model)
            payload = p._build_payload("b64", "prompt")
            cfg = payload["generationConfig"]
            assert "thinkingConfig" not in cfg, (
                f"{model} の generationConfig に thinkingConfig が含まれた"
            )


# ===== M-9 回帰テスト: ClaudeProvider text キー欠落で KeyError 非伝播 =====


class TestClaudeProviderTextKeyMissing:
    """M-9: text キー欠落ブロックを含むレスポンスで KeyError が漏れない。"""

    def test_block_without_text_key_skipped(self, monkeypatch):
        """type='text' だが text キーが欠落したブロックを含んでも KeyError しない。"""
        import json as json_mod

        from pagefolio import ocr_providers

        # text キーが欠落したブロックと正常ブロックを混在させる
        body = json_mod.dumps(
            {
                "content": [
                    {"type": "text"},  # text キー欠落
                    {"type": "text", "text": "hello"},  # 正常
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        result = p.ocr_image("Zg==", "prompt")
        # text キーありのブロックのみ結合される
        assert result == "hello"

    def test_all_blocks_without_text_raises_runtime(self, monkeypatch):
        """全ブロックに text キーが無ければ RuntimeError が送出される。"""
        import json as json_mod

        from pagefolio import ocr_providers

        body = json_mod.dumps({"content": [{"type": "text"}, {"type": "image"}]})

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(RuntimeError):
            p.ocr_image("Zg==", "prompt")


# ===== M-7 回帰テスト: build_provider プラグイン RuntimeError 正規化 =====


class TestBuildProviderPluginRuntimeError:
    """M-7: プラグイン cls() が例外を投げると RuntimeError に正規化される。"""

    def test_plugin_constructor_exception_normalized_to_runtime_error(self):
        """cls() が例外を投げると RuntimeError（素の例外が漏れない）。"""
        import types

        from pagefolio.ocr import build_provider
        from pagefolio.ocr_providers import OCRProvider

        class BrokenPlugin(OCRProvider):
            def __init__(self):
                raise ValueError("init error")

            def ocr_image(self, b64, prompt, **kw):
                return ""

            def list_models(self):
                return []

        registry = {"broken": BrokenPlugin}
        fake_pm = types.SimpleNamespace(_provider_registry=registry)
        settings = {"ocr_provider": "broken"}

        with pytest.raises(RuntimeError, match="broken"):
            build_provider(settings, plugin_manager=fake_pm)


# ===== 429/5xx メッセージ分離（v1.4.3）=====


class TestRetryableErrorMessageSplit:
    """429 はレート制限、5xx はサーバエラーと文言が分かれることを検証する。

    旧実装は「レート制限またはサーバエラー」と一括表示しており、
    HTTP 500 をレート制限と誤認させていた。
    """

    def _patched_provider(self, monkeypatch, provider_kind, code):
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(code)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        if provider_kind == "claude":
            return ocr_providers.ClaudeProvider(api_key="k", model="claude-sonnet-4-6")
        return ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")

    @pytest.mark.parametrize("kind", ["claude", "gemini"])
    def test_429_message_is_rate_limit(self, monkeypatch, kind):
        """HTTP 429 では「レート制限」と表示し code=429 を保持する。"""
        from pagefolio.ocr_providers import OCRRetryableError

        p = self._patched_provider(monkeypatch, kind, 429)
        with pytest.raises(OCRRetryableError) as ei:
            p.ocr_image("Zg==", "p")
        assert ei.value.code == 429
        assert "レート制限" in str(ei.value)
        assert "サーバエラー" not in str(ei.value)

    @pytest.mark.parametrize("kind", ["claude", "gemini"])
    def test_500_message_is_server_error(self, monkeypatch, kind):
        """HTTP 500 では「サーバエラー」と表示し code=500 を保持する。"""
        from pagefolio.ocr_providers import OCRRetryableError

        p = self._patched_provider(monkeypatch, kind, 500)
        with pytest.raises(OCRRetryableError) as ei:
            p.ocr_image("Zg==", "p")
        assert ei.value.code == 500
        assert "サーバエラー" in str(ei.value)
        assert "レート制限" not in str(ei.value)


# ===== Plan 03-02: ocr_image_ex 途切れ検出（V16-QUAL-04 / D-05・A2） =====


class TestOcrImageExTruncation:
    """ocr_image_ex の応答途切れ検出と部分テキスト保持を確認する。

    途切れは例外でなく (text, truncated) タプルのフラグで運ぶ（Pitfall 2）。
    部分テキストは破棄せず常に返す（D-05 必達）。
    """

    def test_claude_truncated_detects_and_keeps_text(self, monkeypatch):
        """Claude stop_reason==max_tokens → (部分テキスト, True)・テキスト保持"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "content": [{"type": "text", "text": "途中まで"}],
                "stop_reason": "max_tokens",
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        text, truncated = p.ocr_image_ex("Zg==", "テスト")
        assert truncated is True
        assert text == "途中まで"  # 部分テキストが破棄されない（D-05）

    def test_claude_normal_not_truncated(self, monkeypatch):
        """Claude stop_reason==end_turn → (テキスト, False)"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "content": [{"type": "text", "text": "完了テキスト"}],
                "stop_reason": "end_turn",
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        text, truncated = p.ocr_image_ex("Zg==", "テスト")
        assert truncated is False
        assert text == "完了テキスト"

    def test_claude_missing_stop_reason_not_truncated(self, monkeypatch):
        """Claude stop_reason 欠落（.get 安全アクセス）→ (テキスト, False)"""
        from pagefolio import ocr_providers

        body = json.dumps({"content": [{"type": "text", "text": "本文"}]})

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        text, truncated = p.ocr_image_ex("Zg==", "テスト")
        assert truncated is False
        assert text == "本文"

    def test_gemini_truncated_detects_and_keeps_text(self, monkeypatch):
        """Gemini finishReason==MAX_TOKENS → (部分テキスト, True)・テキスト保持"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "途中で切れ"}]},
                        "finishReason": "MAX_TOKENS",
                    }
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        text, truncated = p.ocr_image_ex("Zg==", "describe")
        assert truncated is True
        assert text == "途中で切れ"  # 部分テキストが破棄されない（D-05）

    def test_gemini_normal_not_truncated(self, monkeypatch):
        """Gemini finishReason==STOP → (テキスト, False)"""
        from pagefolio import ocr_providers

        body = json.dumps(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "全文"}]},
                        "finishReason": "STOP",
                    }
                ]
            }
        )

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        text, truncated = p.ocr_image_ex("Zg==", "describe")
        assert truncated is False
        assert text == "全文"

    def test_base_default_lmstudio_backward_compat(self, monkeypatch):
        """途切れ未対応プロバイダ（LM Studio）は基底デフォルトで常に False"""
        from pagefolio import ocr_providers

        body = json.dumps({"choices": [{"message": {"content": "ローカル OCR"}}]})

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "local-model")
        text, truncated = p.ocr_image_ex("Zg==", "テスト")
        assert truncated is False
        assert text == "ローカル OCR"


# ===== Plan 03-03: クラウドプロバイダのキー値ログ非出力（V16-QUAL-02 / D-11） =====


class TestProviderKeyNotLogged:
    """クラウドプロバイダ ocr_image が API キー値をログへ出さないことを確認する。

    キー値（インスタンスに渡したダミーキー）が caplog.text に現れないことのみ
    アサートする（キー名出力は監査対象外・Pitfall 4）。
    """

    def test_claude_key_value_not_logged(self, monkeypatch, caplog):
        import logging

        from pagefolio import ocr_providers

        body = json.dumps({"content": [{"type": "text", "text": "ok"}]})

        def fake_urlopen(req, timeout=None):
            return _FakeClaudeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("sk-ant-LEAK-CLAUDE-KEY", "claude-sonnet-4-6")
        with caplog.at_level(logging.DEBUG):
            p.ocr_image("Zg==", "テスト")
        assert "sk-ant-LEAK-CLAUDE-KEY" not in caplog.text, (
            "Claude API キー値がログに出力された（D-11 違反）"
        )

    def test_gemini_key_value_not_logged(self, monkeypatch, caplog):
        import logging

        from pagefolio import ocr_providers

        body = json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(
            api_key="AIza-LEAK-GEMINI-KEY", model="gemini-2.5-flash"
        )
        with caplog.at_level(logging.DEBUG):
            p.ocr_image("Zg==", "describe")
        assert "AIza-LEAK-GEMINI-KEY" not in caplog.text, (
            "Gemini API キー値がログに出力された（D-11 違反）"
        )


# ===== OllamaProvider & RunPodProvider =====
class TestOllamaProvider:
    """OllamaProvider の振る舞いを確認する"""

    def test_subclass_and_basic(self):
        from pagefolio.ocr_providers import OCRProvider, OllamaProvider

        assert issubclass(OllamaProvider, OCRProvider)
        p = OllamaProvider("http://localhost:11434", "llava")
        assert p.url == "http://localhost:11434"
        assert p.model == "llava"
        assert p.default_concurrency == 2
        assert p.max_concurrency == 8

    def test_ocr_image_success(self, monkeypatch):
        from pagefolio import ocr_providers

        body = json.dumps({"choices": [{"message": {"content": "Ollama OCR"}}]})

        def fake_urlopen(req, timeout=None):
            assert req.full_url == "http://localhost:11434/v1/chat/completions"
            payload = json.loads(req.data.decode("utf-8"))
            assert payload["model"] == "llava"
            assert payload["messages"][0]["content"][1]["text"] == "テスト"
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.OllamaProvider("http://localhost:11434", "llava")
        assert p.ocr_image("Zg==", "テスト") == "Ollama OCR"


class TestRunPodProvider:
    """RunPodProvider の振る舞いを確認する"""

    def test_subclass_and_basic(self):
        from pagefolio.ocr_providers import OCRProvider, RunPodProvider

        assert issubclass(RunPodProvider, OCRProvider)
        p = RunPodProvider("api-key", "https://api.runpod.ai/v1/endpoint", "model")
        assert p.api_key == "api-key"
        assert p.url == "https://api.runpod.ai/v1/endpoint"
        assert p.model == "model"

    def test_ocr_image_missing_key(self):
        from pagefolio.ocr_providers import OCRAPIKeyError, RunPodProvider

        p = RunPodProvider("", "https://api.runpod.ai/v1/endpoint", "model")
        import pytest

        with pytest.raises(OCRAPIKeyError):
            p.ocr_image("Zg==", "テスト")

    def test_ocr_image_success(self, monkeypatch):
        from pagefolio import ocr_providers

        body = json.dumps({"choices": [{"message": {"content": "RunPod OCR"}}]})

        def fake_urlopen(req, timeout=None):
            assert req.full_url == "https://api.runpod.ai/v1/endpoint/chat/completions"
            assert req.headers["Authorization"] == "Bearer test-runpod-key"
            payload = json.loads(req.data.decode("utf-8"))
            assert payload["model"] == "model"
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.RunPodProvider(
            "test-runpod-key",
            "https://api.runpod.ai/v1/endpoint",
            "model",
        )
        assert p.ocr_image("Zg==", "テスト") == "RunPod OCR"

    def test_key_value_not_logged(self, monkeypatch, caplog):
        import logging

        from pagefolio import ocr_providers

        body = json.dumps({"choices": [{"message": {"content": "RunPod OCR"}}]})

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.RunPodProvider(
            "rpod-LEAK-KEY",
            "https://api.runpod.ai/v1/endpoint",
            "model",
        )
        with caplog.at_level(logging.DEBUG):
            p.ocr_image("Zg==", "テスト")
        assert "rpod-LEAK-KEY" not in caplog.text, "RunPod APIキーがログに出力された"


# ===== 全ページ統合サマリ: complete_text_ex / supports_text_prompt =====


class TestCompleteTextBase:
    """基底 OCRProvider の complete_text_ex / supports_text_prompt を確認する"""

    def _make_concrete(self):
        from pagefolio.ocr_providers import OCRProvider

        class Concrete(OCRProvider):
            def ocr_image(self, b64_png, prompt, **kwargs):
                return "text"

            def list_models(self):
                return []

        return Concrete()

    def test_supports_text_prompt_default_false(self):
        """基底クラスの supports_text_prompt 既定値は False"""
        from pagefolio.ocr_providers import OCRProvider

        assert OCRProvider.supports_text_prompt is False

    def test_complete_text_ex_raises_not_implemented(self):
        """既定の complete_text_ex は NotImplementedError を送出する"""
        obj = self._make_concrete()
        with pytest.raises(NotImplementedError):
            obj.complete_text_ex("text", "prompt")

    def test_tesseract_not_supported(self):
        """Tesseract は非 LLM のため supports_text_prompt=False のまま"""
        from pagefolio.ocr_providers import TesseractProvider

        assert TesseractProvider.supports_text_prompt is False
        p = TesseractProvider()
        with pytest.raises(NotImplementedError):
            p.complete_text_ex("text", "prompt")

    def test_llm_providers_supported(self):
        """LLM 系プロバイダは supports_text_prompt=True"""
        from pagefolio.ocr_providers import (
            ClaudeProvider,
            GeminiProvider,
            LMStudioProvider,
            OllamaProvider,
            RunPodProvider,
        )

        for cls in (
            LMStudioProvider,
            ClaudeProvider,
            GeminiProvider,
            OllamaProvider,
            RunPodProvider,
        ):
            assert cls.supports_text_prompt is True, cls.__name__


class TestLMStudioCompleteText:
    """LMStudioProvider.complete_text_ex / _build_text_payload を確認する"""

    def test_text_payload_has_no_image_block(self):
        """_build_text_payload に image_url ブロックが含まれない"""
        from pagefolio.ocr_providers import LMStudioProvider

        p = LMStudioProvider("http://localhost:1234", "m")
        payload = p._build_text_payload("doc text", "summarize")
        content = payload["messages"][0]["content"]
        assert all(c["type"] == "text" for c in content)
        assert content[0]["text"] == "doc text"
        assert content[1]["text"] == "summarize"

    def test_success_returns_text_and_not_truncated(self, monkeypatch):
        """正常レスポンスから (text, False) を返す"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {
                    "choices": [
                        {"message": {"content": "summary"}, "finish_reason": "stop"}
                    ]
                }
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        assert p.complete_text_ex("doc", "sum") == ("summary", False)

    def test_truncated_on_finish_reason_length(self, monkeypatch):
        """finish_reason == "length" のとき truncated=True"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {
                    "choices": [
                        {"message": {"content": "part"}, "finish_reason": "length"}
                    ]
                }
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        assert p.complete_text_ex("doc", "sum") == ("part", True)

    def test_bad_response_raises_runtime_error(self, monkeypatch):
        """レスポンス形式不正で RuntimeError"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            return _FakeResponse(json.dumps({"unexpected": True}))

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://localhost:1234", "m")
        with pytest.raises(RuntimeError):
            p.complete_text_ex("doc", "sum")


class TestClaudeCompleteText:
    """ClaudeProvider.complete_text_ex / _build_text_payload を確認する"""

    def test_text_payload_has_no_image_block(self):
        """_build_text_payload に image ブロックが含まれない"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider(api_key="k", model="claude-sonnet-4-6")
        payload = p._build_text_payload("doc text", "summarize")
        content = payload["messages"][0]["content"]
        assert all(c["type"] == "text" for c in content)
        assert content[0]["text"] == "doc text"
        assert content[1]["text"] == "summarize"

    def test_text_payload_gen_params_match_build_payload(self):
        """effort/temperature 分岐が _build_payload と同一（共有ヘルパー検証）"""
        from pagefolio.ocr_providers import ClaudeProvider

        # effort 対応モデル: output_config のみ
        p = ClaudeProvider(api_key="k", model="claude-sonnet-4-6", effort="high")
        img = p._build_payload("Zg==", "x")
        txt = p._build_text_payload("doc", "x")
        assert txt.get("output_config") == img.get("output_config")
        assert "temperature" not in txt and "temperature" not in img
        # haiku 系: temperature のみ
        p2 = ClaudeProvider(api_key="k", model="claude-haiku-4-5", temperature=0.3)
        img2 = p2._build_payload("Zg==", "x")
        txt2 = p2._build_text_payload("doc", "x")
        assert txt2.get("temperature") == img2.get("temperature") == 0.3
        assert "output_config" not in txt2 and "output_config" not in img2

    def test_truncated_on_max_tokens(self, monkeypatch):
        """stop_reason == "max_tokens" のとき truncated=True"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {
                    "content": [{"type": "text", "text": "partial summary"}],
                    "stop_reason": "max_tokens",
                }
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider(api_key="k", model="claude-sonnet-4-6")
        assert p.complete_text_ex("doc", "sum") == ("partial summary", True)

    def test_retryable_on_429(self, monkeypatch):
        """HTTP 429 で OCRRetryableError を送出する"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                "https://api.anthropic.com/v1/messages",
                429,
                "Too Many Requests",
                {"Retry-After": "5"},
                io.BytesIO(b""),
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider(api_key="k", model="claude-sonnet-4-6")
        with pytest.raises(ocr_providers.OCRRetryableError) as ei:
            p.complete_text_ex("doc", "sum")
        assert ei.value.retry_after == 5.0


class TestGeminiCompleteText:
    """GeminiProvider.complete_text_ex / _build_text_payload を確認する"""

    def test_text_payload_has_no_inline_data(self):
        """_build_text_payload に inline_data（画像）が含まれない"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        payload = p._build_text_payload("doc text", "summarize")
        parts = payload["contents"][0]["parts"]
        assert all("inline_data" not in part for part in parts)
        assert parts[0]["text"] == "doc text"
        assert parts[1]["text"] == "summarize"

    def test_text_payload_generation_config_matches(self):
        """generationConfig が _build_payload と同一（thinkingConfig 分岐含む）"""
        from pagefolio.ocr_providers import GeminiProvider

        p = GeminiProvider(api_key="k", model="gemini-2.5-flash")
        img = p._build_payload("Zg==", "x")
        txt = p._build_text_payload("doc", "x")
        assert txt["generationConfig"] == img["generationConfig"]

    def test_truncated_on_max_tokens(self, monkeypatch):
        """finishReason == "MAX_TOKENS" のとき truncated=True"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "partial"}]},
                            "finishReason": "MAX_TOKENS",
                        }
                    ]
                }
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        assert p.complete_text_ex("doc", "sum") == ("partial", True)

    def test_blocked_raises_runtime_error(self, monkeypatch):
        """candidates 空（安全フィルタブロック）で RuntimeError"""
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}})
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider(api_key="k", model="gemini-2.5-flash")
        with pytest.raises(RuntimeError):
            p.complete_text_ex("doc", "sum")


class TestOllamaRunPodCompleteText:
    """Ollama / RunPod の complete_text_ex を確認する"""

    def test_ollama_text_payload_has_no_image_block(self):
        from pagefolio.ocr_providers import OllamaProvider

        p = OllamaProvider("http://localhost:11434", "llava")
        content = p._build_text_payload("doc", "sum")["messages"][0]["content"]
        assert all(c["type"] == "text" for c in content)

    def test_ollama_truncated_on_length(self, monkeypatch):
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {
                    "choices": [
                        {"message": {"content": "part"}, "finish_reason": "length"}
                    ]
                }
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.OllamaProvider("http://localhost:11434", "llava")
        assert p.complete_text_ex("doc", "sum") == ("part", True)

    def test_runpod_missing_key_raises(self):
        """RunPod: APIキー未設定で OCRAPIKeyError"""
        from pagefolio.ocr_providers import OCRAPIKeyError, RunPodProvider

        p = RunPodProvider("", "https://api.runpod.ai/v1/endpoint", "m")
        with pytest.raises(OCRAPIKeyError):
            p.complete_text_ex("doc", "sum")

    def test_runpod_success(self, monkeypatch):
        from pagefolio import ocr_providers

        def fake_urlopen(req, timeout=None):
            body = json.dumps(
                {"choices": [{"message": {"content": "sum"}, "finish_reason": "stop"}]}
            )
            return _FakeResponse(body)

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.RunPodProvider(
            "key", "https://api.runpod.ai/v1/endpoint", "m"
        )
        assert p.complete_text_ex("doc", "sum") == ("sum", False)


class TestParseRetryAfter:
    """parse_retry_after 純関数の検証"""

    def test_numeric_string(self):
        from pagefolio.ocr_providers import parse_retry_after

        assert parse_retry_after({"Retry-After": "30"}) == 30.0
        assert parse_retry_after({"Retry-After": "1.5"}) == 1.5

    def test_none_headers(self):
        from pagefolio.ocr_providers import parse_retry_after

        assert parse_retry_after(None) is None

    def test_missing_header(self):
        from pagefolio.ocr_providers import parse_retry_after

        assert parse_retry_after({}) is None

    def test_http_date_format_returns_none(self):
        """HTTP-date 形式（数値でない）は None（従来挙動と同じ）"""
        from pagefolio.ocr_providers import parse_retry_after

        assert parse_retry_after({"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}) is (
            None
        )


class TestLooksLikeContextError:
    """looks_like_context_error 純関数の検証"""

    @pytest.mark.parametrize("code", [400, 413, 422])
    def test_context_markers_detected(self, code):
        from pagefolio.ocr_providers import looks_like_context_error

        assert looks_like_context_error(code, '{"error": "context_length_exceeded"}')
        assert looks_like_context_error(code, "Prompt is too long: 250000 tokens")
        assert looks_like_context_error(code, "exceeds the maximum number of tokens")

    def test_case_insensitive(self):
        from pagefolio.ocr_providers import looks_like_context_error

        assert looks_like_context_error(400, "CONTEXT LENGTH exceeded")

    def test_other_400_body_not_detected(self):
        from pagefolio.ocr_providers import looks_like_context_error

        assert not looks_like_context_error(400, "invalid api key")
        assert not looks_like_context_error(400, "")
        assert not looks_like_context_error(400, None)

    def test_non_4xx_codes_not_detected(self):
        """429/5xx はリトライ側で扱うため context 判定しない"""
        from pagefolio.ocr_providers import looks_like_context_error

        assert not looks_like_context_error(429, "context length")
        assert not looks_like_context_error(500, "context length")


class TestLMStudioRetrySymmetry:
    """LMStudio の 429/5xx リトライ対称化（v1.6.5）の検証。

    従来は全 HTTPError が RuntimeError 化されサマリ生成でリトライされなかった。
    クラウド系（Claude/Gemini/RunPod）と同じ OCRRetryableError へ対称化する。
    """

    def test_429_raises_retryable_with_retry_after(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(
                429, "Too Many Requests", b"rate limit", headers={"Retry-After": "30"}
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(OCRRetryableError) as ei:
            p.complete_text_ex("doc", "sum")
        assert ei.value.retry_after == 30.0
        assert ei.value.code == 429

    def test_500_raises_retryable(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(500, "Server Error", b"oops")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(OCRRetryableError):
            p.ocr_image("Zg==", "p")

    def test_401_raises_plain_runtime_error(self, monkeypatch):
        """401（認証エラー）はリトライ対象外の RuntimeError のまま"""
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(401, "Unauthorized", b"bad key")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(RuntimeError) as ei:
            p.complete_text_ex("doc", "sum")
        assert not isinstance(ei.value, OCRRetryableError)
        assert "401" in str(ei.value)

    def test_400_context_error_raises_context_length(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRContextLengthError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(
                400, "Bad Request", b'{"error": "context_length_exceeded"}'
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.LMStudioProvider("http://x", "m")
        with pytest.raises(OCRContextLengthError):
            p.complete_text_ex("doc", "sum")


class TestOllamaRetrySymmetry:
    """Ollama の 429/5xx リトライ対称化（v1.6.5）の検証"""

    def test_429_raises_retryable(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(429, "Too Many Requests", b"rate limit")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.OllamaProvider("http://x", "m")
        with pytest.raises(OCRRetryableError):
            p.complete_text_ex("doc", "sum")

    def test_400_context_error_raises_context_length(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRContextLengthError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(400, "Bad Request", b"too many tokens in prompt")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.OllamaProvider("http://x", "m")
        with pytest.raises(OCRContextLengthError):
            p.complete_text_ex("doc", "sum")

    def test_404_raises_plain_runtime_error(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRRetryableError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(404, "Not Found", b"no such model")

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.OllamaProvider("http://x", "m")
        with pytest.raises(RuntimeError) as ei:
            p.ocr_image("Zg==", "p")
        assert not isinstance(ei.value, OCRRetryableError)


class TestCloudContextLengthError:
    """クラウド系プロバイダの context 超過 → OCRContextLengthError 検証"""

    def test_claude_prompt_too_long(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRContextLengthError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(
                400,
                "Bad Request",
                b'{"error": {"message": "prompt is too long: 250000 tokens"}}',
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.ClaudeProvider("key", "claude-sonnet-4-6")
        with pytest.raises(OCRContextLengthError):
            p.complete_text_ex("doc", "sum")

    def test_gemini_token_limit(self, monkeypatch):
        from pagefolio import ocr_providers
        from pagefolio.ocr_providers import OCRContextLengthError

        def fake_urlopen(req, timeout=None):
            raise _FakeHTTPError(
                400, "Bad Request", b"input exceeds the maximum number of tokens"
            )

        monkeypatch.setattr(ocr_providers.urllib.request, "urlopen", fake_urlopen)
        p = ocr_providers.GeminiProvider("key", "gemini-2.5-flash")
        with pytest.raises(OCRContextLengthError):
            p.complete_text_ex("doc", "sum")
