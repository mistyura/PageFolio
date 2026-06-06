"""OCR モジュール（LM Studio クライアント）のユニットテスト"""

import base64
import io
import json
import os
import socket
import sys
import threading
import time
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio import ocr  # noqa: E402
from pagefolio.ocr_providers import LMStudioProvider, OCRProvider  # noqa: E402

# ===== テスト用ダブル =====


class FakeProvider(OCRProvider):
    """run_parallel テスト用の偽 Provider。ocr_image は b64 をもとにテキストを返す。"""

    default_concurrency = 2
    max_concurrency = 4

    def __init__(self, side_effect=None):
        """side_effect が None なら f"text-{b64}" を返す。callable なら呼び出す。"""
        self._side_effect = side_effect

    def ocr_image(self, b64_png, prompt, **kwargs):
        if self._side_effect is not None:
            return self._side_effect(b64_png, prompt)
        return f"text-{b64_png}"

    def list_models(self):
        return ["fake-model"]


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


# ===== LMStudioProvider のペイロード・レスポンス処理テスト =====
# （旧 TestBuildChatPayload / TestCallLmStudio を LMStudioProvider 経由で維持）


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


class TestLMStudioProviderPayload:
    """LMStudioProvider._build_payload のペイロード構造を確認する"""

    def test_image_url_uses_data_uri(self):
        p = LMStudioProvider(url="http://x", model="llava")
        payload = p._build_payload("ZmFrZWltYWdl", "describe")
        content = payload["messages"][0]["content"]
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert content[0]["image_url"]["url"].endswith("ZmFrZWltYWdl")
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "describe"

    def test_model_fallback(self):
        """空のモデル名は 'local-model' にフォールバック"""
        p = LMStudioProvider(url="http://x", model="")
        payload = p._build_payload("abc", "p")
        assert payload["model"] == "local-model"

    def test_role_is_user(self):
        p = LMStudioProvider(url="http://x", model="m")
        payload = p._build_payload("a", "p")
        assert payload["messages"][0]["role"] == "user"

    def test_max_tokens_default(self):
        """max_tokens 未指定なら -1（無制限）"""
        p = LMStudioProvider(url="http://x", model="m")
        payload = p._build_payload("a", "p")
        assert payload["max_tokens"] == -1

    def test_max_tokens_custom(self):
        p = LMStudioProvider(url="http://x", model="m", max_tokens=4096)
        payload = p._build_payload("a", "p")
        assert payload["max_tokens"] == 4096

    def test_temperature_default(self):
        """temperature 未指定なら 0.1（OCR 推奨値）"""
        p = LMStudioProvider(url="http://x", model="m")
        payload = p._build_payload("a", "p")
        assert payload["temperature"] == 0.1

    def test_temperature_custom(self):
        p = LMStudioProvider(url="http://x", model="m", temperature=0.5)
        payload = p._build_payload("a", "p")
        assert payload["temperature"] == 0.5


class TestLMStudioProviderOcrImage:
    """LMStudioProvider.ocr_image のレスポンス処理と例外マッピング"""

    def _make_provider(self):
        import pagefolio.ocr_providers as op

        return LMStudioProvider(url="http://localhost:1234", model="m"), op

    def test_success_returns_content(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://localhost:1234", model="m", timeout=5)
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["timeout"] = timeout
            body = json.dumps({"choices": [{"message": {"content": "hello world"}}]})
            return _FakeResponse(body)

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        text = p.ocr_image("Zg==", "p")
        assert text == "hello world"
        assert captured["url"] == "http://localhost:1234/v1/chat/completions"
        assert captured["timeout"] == 5

    def test_connection_error_raises_connection_error(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="m")

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(ConnectionError):
            p.ocr_image("Zg==", "p")

    def test_socket_timeout_raises_timeout_error(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="m", timeout=1)

        def fake_urlopen(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "p")

    def test_urlerror_with_timeout_reason_raises_timeout(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="m", timeout=1)

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError(socket.timeout("inner"))

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(TimeoutError):
            p.ocr_image("Zg==", "p")

    def test_http_error_raises_runtime_error(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="m")

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                "http://x", 500, "Server Error", {}, io.BytesIO(b"oops")
            )

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(RuntimeError) as ei:
            p.ocr_image("Zg==", "p")
        assert "500" in str(ei.value)

    def test_malformed_response_raises_runtime_error(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="m")

        def fake_urlopen(req, timeout=None):
            return _FakeResponse("{}")  # choices 無し

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(RuntimeError):
            p.ocr_image("Zg==", "p")


class TestLMStudioProviderListModels:
    """LMStudioProvider.list_models のレスポンス処理と例外マッピング"""

    def test_returns_model_ids(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://localhost:1234", model="")
        body = json.dumps(
            {"data": [{"id": "llava-v1.6"}, {"id": "qwen-vl"}, {"id": None}]}
        )

        def fake_urlopen(req, timeout=None):
            assert req.full_url == "http://localhost:1234/v1/models"
            return _FakeResponse(body)

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        ids = p.list_models()
        assert ids == ["llava-v1.6", "qwen-vl"]

    def test_connection_failure(self, monkeypatch):
        import pagefolio.ocr_providers as op

        p = LMStudioProvider(url="http://x", model="")

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("refused")

        monkeypatch.setattr(op.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(ConnectionError):
            p.list_models()


# ===== run_parallel (Provider 非依存) =====


class TestRunParallel:
    """run_parallel の並列実行・順序保持・キャンセル・致命的エラー処理"""

    def test_empty_inputs_return_empty(self):
        provider = FakeProvider()
        results, errors, fm, fk = ocr.run_parallel(
            provider, images_b64={}, page_indices=[]
        )
        assert results == {}
        assert errors == {}
        assert fm is None and fk is None

    def test_all_succeed_preserves_results_by_page_idx(self):
        """ページごとに正しい結果が返り、入力順に依らず辞書で取得できる (Test 1)"""
        provider = FakeProvider()
        images = {0: "A", 2: "B", 5: "C"}
        results, errors, fm, fk = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=[0, 2, 5],
            concurrency=3,
        )
        assert results == {0: "text-A", 2: "text-B", 5: "text-C"}
        assert errors == {}
        assert fm is None

    def test_runtime_error_is_per_page_not_fatal(self):
        """RuntimeError は当該ページのみ errors に記録、他ページは継続 (Test 2)"""

        def side_effect(b64, prompt):
            if b64 == "BAD":
                raise RuntimeError("HTTP 500: oops")
            return f"ok-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        images = {0: "A", 1: "BAD", 2: "C"}
        results, errors, fm, fk = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=[0, 1, 2],
            concurrency=2,
        )
        assert results == {0: "ok-A", 2: "ok-C"}
        assert 1 in errors
        assert "HTTP 500" in errors[1]
        assert fm is None

    def test_connection_error_is_fatal(self):
        """ConnectionError は fatal_msg に記録され、kind='connection' (Test 2)"""

        def side_effect(b64, prompt):
            raise ConnectionError("refused")

        provider = FakeProvider(side_effect=side_effect)
        results, errors, fm, fk = ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        assert fm is not None
        assert "refused" in fm
        assert fk == "connection"

    def test_timeout_error_is_fatal(self):
        """TimeoutError は fatal_msg に記録され、kind='timeout' (Test 2)"""

        def side_effect(b64, prompt):
            raise TimeoutError("timed out")

        provider = FakeProvider(side_effect=side_effect)
        _, _, fm, fk = ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        assert fm is not None
        assert fk == "timeout"

    def test_concurrency_clamped_to_provider_max(self):
        """concurrency=999 でも provider.max_concurrency にクランプされる (Test 3)"""
        provider = FakeProvider()  # max_concurrency=4
        images = {i: f"i{i}" for i in range(3)}
        results, _, _, _ = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=[0, 1, 2],
            concurrency=999,
        )
        assert len(results) == 3

    def test_concurrency_none_uses_default_concurrency(self):
        """concurrency=None のとき provider.default_concurrency を使う (Test 3)"""
        provider = FakeProvider()  # default_concurrency=2
        images = {i: f"i{i}" for i in range(4)}
        results, _, _, _ = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=[0, 1, 2, 3],
            concurrency=None,
        )
        assert len(results) == 4

    def test_cancel_stops_submission(self):
        """is_cancelled() が True を返すと以降の呼び出しはスキップされる (Test 4)"""
        call_count = {"n": 0}
        lock = threading.Lock()
        cancel = threading.Event()

        def side_effect(b64, prompt):
            with lock:
                call_count["n"] += 1
                if call_count["n"] >= 1:
                    cancel.set()
            return b64

        provider = FakeProvider(side_effect=side_effect)
        images = {i: f"img{i}" for i in range(10)}
        results, _, _, _ = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=list(range(10)),
            concurrency=1,
            is_cancelled=cancel.is_set,
        )
        assert len(results) < 10

    def test_progress_callback_called_for_each_done(self):
        """on_progress が完了ごとに done=1,2,3.. でコールされる (Test 5)"""
        provider = FakeProvider()
        calls = []

        def on_progress(done, page_idx, status):
            calls.append((done, page_idx, status))

        images = {0: "A", 1: "B", 2: "C"}
        ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=[0, 1, 2],
            concurrency=1,
            on_progress=on_progress,
        )
        assert len(calls) == 3
        assert [c[0] for c in calls] == [1, 2, 3]
        assert all(c[2] == "ok" for c in calls)

    def test_concurrency_actually_parallel(self):
        """concurrency=4 で並列に走ること（同時実行数の最大値で検証）"""
        in_flight = 0
        max_in_flight = 0
        lock = threading.Lock()

        def side_effect(b64, prompt):
            nonlocal in_flight, max_in_flight
            with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return b64

        provider = FakeProvider(side_effect=side_effect)
        images = {i: f"img{i}" for i in range(4)}
        results, _, _, _ = ocr.run_parallel(
            provider,
            images_b64=images,
            page_indices=list(range(4)),
            concurrency=4,
        )
        assert len(results) == 4
        assert max_in_flight >= 2


# ===== has_embedded_text =====


class TestHasEmbeddedText:
    """has_embedded_text: テキスト有りページで True、空ページで False を返す (Test 6)"""

    def test_text_rich_page_returns_true(self, sample_pdf_doc):
        """テキストが埋め込まれたページは True を返す"""
        # conftest.py の sample_pdf_doc は各ページに "Page N" テキストを挿入済み
        page = sample_pdf_doc[0]
        result = ocr.has_embedded_text(page)
        assert result is True

    def test_empty_page_returns_false(self):
        """テキストが無いページは False を返す"""
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # テキストなし
        result = ocr.has_embedded_text(page)
        assert result is False
        doc.close()

    def test_few_chars_page_returns_false(self):
        """極少文字（しきい値未満）のページは False を返す"""
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Hi", fontsize=12)  # 2文字: しきい値未満
        result = ocr.has_embedded_text(page)
        assert result is False
        doc.close()

    def test_sufficient_chars_page_returns_true(self):
        """しきい値以上の文字があるページは True を返す"""
        import fitz

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        # 20文字以上を挿入
        page.insert_text(
            (72, 72), "This is sufficient text for detection.", fontsize=12
        )
        result = ocr.has_embedded_text(page)
        assert result is True
        doc.close()


# ===== 定数の公開確認 =====


class TestConstants:
    """定数が公開されているか"""

    def test_default_concurrency_constant(self):
        """DEFAULT_OCR_CONCURRENCY / MAX_OCR_CONCURRENCY が公開されている"""
        assert ocr.DEFAULT_OCR_CONCURRENCY == 2
        assert ocr.MAX_OCR_CONCURRENCY == 8

    def test_embedded_text_min_chars_defined(self):
        """EMBEDDED_TEXT_MIN_CHARS が ocr.py に定義されている"""
        assert hasattr(ocr, "EMBEDDED_TEXT_MIN_CHARS")
        assert isinstance(ocr.EMBEDDED_TEXT_MIN_CHARS, int)
        assert ocr.EMBEDDED_TEXT_MIN_CHARS > 0


# ===== build_provider ファクトリ =====


class TestBuildProvider:
    """build_provider の動作検証（Task 2 の振る舞い）"""

    def test_lmstudio_returns_lmstudio_provider(self):
        """ocr_provider='lmstudio' のとき LMStudioProvider を返す (Test 1)"""
        settings = {
            "ocr_provider": "lmstudio",
            "lm_studio_url": "http://x",
            "lm_studio_model": "m",
        }
        provider = ocr.build_provider(settings)
        assert isinstance(provider, LMStudioProvider)
        assert provider.url == "http://x"
        assert provider.model == "m"

    def test_no_ocr_provider_key_returns_lmstudio_provider(self):
        """ocr_provider キーなし設定でも LMStudioProvider を返す（後方互換 Test 2）"""
        provider = ocr.build_provider({})
        assert isinstance(provider, LMStudioProvider)

    def test_returns_ocr_provider_instance(self):
        """build_provider が返す provider は OCRProvider インスタンス (Test 3)"""
        provider = ocr.build_provider({"ocr_provider": "lmstudio"})
        assert isinstance(provider, OCRProvider)


# ===== _resolve_api_key（Task 1: 05-03）=====


class TestResolveApiKey:
    """_resolve_api_key の動作検証（キー解決・環境変数優先・未設定時エラー）"""

    def test_env_var_present_returns_env_value(self, monkeypatch):
        """環境変数 ANTHROPIC_API_KEY があればその値を返す（成功基準3・D-02）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-abc")
        result = _resolve_api_key("claude", {})
        assert result == "env-key-abc"

    def test_env_var_absent_session_key_returned(self, monkeypatch):
        """環境変数未設定・セッションキーあり → セッションキーを返す（D-02）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _resolve_api_key("claude", {"claude": "sess-key"})
        assert result == "sess-key"

    def test_env_var_takes_priority_over_session_key(self, monkeypatch):
        """session_keys にキーがあっても環境変数を優先して返す（D-02 優先順位）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-wins")
        result = _resolve_api_key("claude", {"claude": "session-key"})
        assert result == "env-wins"

    def test_no_env_no_session_raises_ocr_api_key_error(self, monkeypatch):
        """環境変数もセッションキーもなければ OCRAPIKeyError を raise（成功基準2）"""
        from pagefolio.ocr import _resolve_api_key
        from pagefolio.ocr_providers import OCRAPIKeyError

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(OCRAPIKeyError) as ei:
            _resolve_api_key("claude", {})
        assert ei.value.env_var == "ANTHROPIC_API_KEY"

    def test_os_environ_not_written(self, monkeypatch):
        """_resolve_api_key は os.environ への書き込みを行わない（D-05）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.setenv("ANTHROPIC_API_KEY", "original-key")
        _resolve_api_key("claude", {"claude": "sess"})
        # 環境変数が書き換えられていないことを確認
        import os

        assert os.environ.get("ANTHROPIC_API_KEY") == "original-key"


# ===== build_provider claude 分岐（Task 1: 05-03）=====


class TestBuildProviderClaude:
    """build_provider の claude 分岐検証（キー引数注入・settings への非漏洩）"""

    def test_claude_returns_claude_provider(self, monkeypatch):
        """ocr_provider='claude' で ClaudeProvider を返す（成功基準1）"""
        from pagefolio.ocr_providers import ClaudeProvider

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude"}
        provider = ocr.build_provider(settings, api_key="k")
        assert isinstance(provider, ClaudeProvider)

    def test_claude_provider_api_key_is_injected(self, monkeypatch):
        """ClaudeProvider に api_key が引数注入される（settings から読まない・SC3）"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = ocr.build_provider({"ocr_provider": "claude"}, api_key="my-key")
        assert provider.api_key == "my-key"

    def test_claude_model_default(self, monkeypatch):
        """claude_model 未指定時は claude-sonnet-4-6 がデフォルト"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider = ocr.build_provider({"ocr_provider": "claude"}, api_key="k")
        assert provider.model == "claude-sonnet-4-6"

    def test_claude_model_from_settings(self, monkeypatch):
        """claude_model が settings に指定されていればそれを使う"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude", "claude_model": "claude-haiku-4-5"}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.model == "claude-haiku-4-5"

    def test_settings_not_polluted_with_api_key(self, monkeypatch):
        """build_provider 後も settings に api_key が混入しない（成功基準1/3）"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude"}
        ocr.build_provider(settings, api_key="secret")
        # api_key 系のキーが settings に入っていないこと
        for key in (
            "api_key",
            "claude_api_key",
            "anthropic_api_key",
            "ANTHROPIC_API_KEY",
        ):
            assert key not in settings, f"settings に {key} が混入している"


# ===== run_parallel バックオフ（Task 2: 05-03）=====


class TestRunParallelBackoff:
    """run_parallel の OCRRetryableError 指数バックオフ検証（成功基準8・OCR-PERF-04）"""

    def test_retryable_once_then_success(self, monkeypatch):
        """1回 OCRRetryableError 後に成功 → results に入る（リトライ成功）"""
        from unittest.mock import MagicMock

        import pagefolio.ocr as ocr_mod
        from pagefolio.ocr_providers import OCRRetryableError

        mock_time = MagicMock()
        monkeypatch.setattr(ocr_mod, "time", mock_time)

        call_count = {"n": 0}

        def side_effect(b64, prompt):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OCRRetryableError("429 rate limit", retry_after=None)
            return "ok-text"

        provider = FakeProvider(side_effect=side_effect)
        results, errors, fm, fk = ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        assert 0 in results
        assert results[0] == "ok-text"
        assert errors == {}

    def test_always_retryable_errors_after_max_retries(self, monkeypatch):
        """毎回 OCRRetryableError → 最大3回後に errors 記録（無限ループしない）"""
        from unittest.mock import MagicMock

        import pagefolio.ocr as ocr_mod
        from pagefolio.ocr_providers import OCRRetryableError

        mock_time = MagicMock()
        monkeypatch.setattr(ocr_mod, "time", mock_time)

        call_count = {"n": 0}

        def side_effect(b64, prompt):
            call_count["n"] += 1
            raise OCRRetryableError("429 always")

        provider = FakeProvider(side_effect=side_effect)
        results, errors, fm, fk = ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        # errors に記録されること
        assert 0 in errors
        # MAX_RETRIES=3 で上限になること（コール数 ≤ MAX_RETRIES）
        assert call_count["n"] <= ocr.MAX_RETRIES
        assert results == {}

    def test_retry_after_is_used_for_sleep(self, monkeypatch):
        """retry_after 付きエラーは sleep にその値を使う（Retry-After 優先）"""
        from unittest.mock import MagicMock

        import pagefolio.ocr as ocr_mod
        from pagefolio.ocr_providers import OCRRetryableError

        mock_time = MagicMock()
        monkeypatch.setattr(ocr_mod, "time", mock_time)

        call_count = {"n": 0}

        def side_effect(b64, prompt):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OCRRetryableError("429", retry_after=5.0)
            return "ok"

        provider = FakeProvider(side_effect=side_effect)
        ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        # sleep が 5.0 で呼ばれていること（Retry-After 優先・D-15）
        sleep_calls = [c.args[0] for c in mock_time.sleep.call_args_list]
        assert any(s == 5.0 for s in sleep_calls), (
            f"sleep(5.0) が呼ばれていない: {sleep_calls}"
        )

    def test_exponential_backoff_without_retry_after(self, monkeypatch):
        """retry_after が None なら指数バックオフ（RETRY_BASE_DELAY * 2^(n-1)）"""
        from unittest.mock import MagicMock

        import pagefolio.ocr as ocr_mod
        from pagefolio.ocr_providers import OCRRetryableError

        mock_time = MagicMock()
        monkeypatch.setattr(ocr_mod, "time", mock_time)

        call_count = {"n": 0}

        def side_effect(b64, prompt):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise OCRRetryableError("429", retry_after=None)
            return "ok"

        provider = FakeProvider(side_effect=side_effect)
        ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
        )
        sleep_calls = [c.args[0] for c in mock_time.sleep.call_args_list]
        # 少なくとも1回は RETRY_BASE_DELAY（1.0）以上で sleep されること
        assert len(sleep_calls) >= 1
        assert all(s >= ocr.RETRY_BASE_DELAY for s in sleep_calls)

    def test_waiting_status_on_progress_called(self, monkeypatch):
        """リトライ中に on_progress が status='waiting' で呼ばれる（D-15）"""
        from unittest.mock import MagicMock

        import pagefolio.ocr as ocr_mod
        from pagefolio.ocr_providers import OCRRetryableError

        mock_time = MagicMock()
        monkeypatch.setattr(ocr_mod, "time", mock_time)

        call_count = {"n": 0}

        def side_effect(b64, prompt):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OCRRetryableError("429", retry_after=None)
            return "ok"

        progress_calls = []

        def on_progress(done, page_idx, status):
            progress_calls.append((done, page_idx, status))

        provider = FakeProvider(side_effect=side_effect)
        ocr.run_parallel(
            provider,
            images_b64={0: "A"},
            page_indices=[0],
            concurrency=1,
            on_progress=on_progress,
        )
        # "waiting/{attempt}" ステータスのコールが1回以上あること
        # status は "waiting/{attempt}" 形式（ocr_dialog 側でリトライ番号を参照できる）
        waiting_calls = [
            c for c in progress_calls if c[2] is not None and c[2].startswith("waiting")
        ]
        assert len(waiting_calls) >= 1


# ===== _start_ocr クラウドゲート（成功基準3 リグレッション: 05-05 目視 NG 修正）=====


class TestStartOcrCloudGate:
    """claude かつキー未解決でも _start_ocr が OCRDialog を開く（成功基準3）。

    旧実装は env 未設定・セッションキー空のとき即エラーで return し OCRDialog を
    生成しなかったため、05-05 のマスク付きセッションキー入力欄に到達できなかった。
    """

    def _make_fake_app(self):
        import types

        return types.SimpleNamespace(
            settings={"ocr_provider": "claude"},
            _session_api_keys={},
            root=None,
            doc=object(),
            lang="ja",
            _t=lambda key: key,
            _font=lambda *a, **k: None,
        )

    def test_cloud_no_key_opens_dialog_without_error(self, monkeypatch):
        """env 未設定・セッションキー空でも showerror せず OCRDialog を開く"""
        import pagefolio.ocr_dialog as ocr_dialog
        from pagefolio.ocr import OCRMixin

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        opened = {"dialog": False}
        err = {"count": 0}

        def fake_dialog(*args, **kwargs):
            opened["dialog"] = True
            return object()

        monkeypatch.setattr(ocr_dialog, "OCRDialog", fake_dialog)
        monkeypatch.setattr(
            ocr.messagebox,
            "showerror",
            lambda *a, **k: err.__setitem__("count", err["count"] + 1),
        )

        fake = self._make_fake_app()
        OCRMixin._start_ocr(fake, [0])

        assert opened["dialog"] is True
        assert err["count"] == 0

    def test_cloud_env_key_resolved_opens_dialog(self, monkeypatch):
        """env 設定済みなら従来どおり OCRDialog を開く（後方互換）"""
        import pagefolio.ocr_dialog as ocr_dialog
        from pagefolio.ocr import OCRMixin

        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")

        opened = {"dialog": False}
        monkeypatch.setattr(
            ocr_dialog,
            "OCRDialog",
            lambda *a, **k: opened.__setitem__("dialog", True),
        )

        fake = self._make_fake_app()
        OCRMixin._start_ocr(fake, [0])

        assert opened["dialog"] is True
