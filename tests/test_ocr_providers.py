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
        """opus モデルは payload に output_config.effort を含み temperature を含まない（成功基準7）"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-opus-4-8")
        payload = p._build_payload("AAA", "テスト")
        assert "output_config" in payload
        assert payload["output_config"]["effort"] == "low"
        assert "temperature" not in payload

    def test_sonnet_payload_has_output_config_effort(self):
        """sonnet モデルは payload に output_config.effort を含み temperature を含まない"""
        from pagefolio.ocr_providers import ClaudeProvider

        p = ClaudeProvider("k", "claude-sonnet-4-6")
        payload = p._build_payload("AAA", "テスト")
        assert "output_config" in payload
        assert "effort" in payload["output_config"]
        assert "temperature" not in payload

    def test_haiku_payload_has_temperature_no_output_config(self):
        """haiku モデルは payload に temperature を含み output_config を含まない（成功基準7・D-16）"""
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
