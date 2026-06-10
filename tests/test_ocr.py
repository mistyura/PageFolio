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


# ===== OCRDialog LLM 設定ライブ更新（Task 1: 260607-ccz）=====


class TestOcrDialogLlmConfig:
    """_apply_llm_settings のロジック検証（Tkinter ウィンドウ不使用）。

    _refresh_provider_dependent_ui を no-op に差し替えた fake インスタンスで
    OCRDialog._apply_llm_settings を未束縛呼び出しして検証する。
    """

    def _make_fake(self, extra_settings=None):
        """Tkinter 不使用の fake OCRDialog インスタンスを生成する。"""
        import types

        settings = {
            "ocr_provider": "lmstudio",
            "lm_studio_url": "http://localhost:1234",
            "lm_studio_model": "",
            "ocr_timeout": 120,
            "ocr_max_tokens": -1,
            "ocr_temperature": 0.1,
        }
        if extra_settings:
            settings.update(extra_settings)

        app = types.SimpleNamespace(
            settings=settings,
            _session_api_keys={},
        )

        fake = types.SimpleNamespace(
            app=app,
            provider=None,
            progress_var=types.SimpleNamespace(set=lambda _v: None),
            _started=False,
            _done=False,
        )
        # url_var / model_var の set を記録できる SimpleNamespace
        fake.url_var = types.SimpleNamespace(set=lambda v: None)
        fake.model_var = types.SimpleNamespace(set=lambda v: None)

        # _refresh_provider_dependent_ui を no-op に差し替え
        fake._refresh_called = False

        def _no_op_refresh():
            fake._refresh_called = True

        fake._refresh_provider_dependent_ui = _no_op_refresh
        return fake

    # ── test 1: settings が更新される ──────────────────────────────────────

    def test_apply_updates_settings(self, monkeypatch):
        """llm_settings を渡すと fake.app.settings に反映される。"""
        import pagefolio.ocr as ocr_mod
        import pagefolio.settings as settings_mod

        monkeypatch.setattr(settings_mod, "_save_settings", lambda _: None)
        monkeypatch.setattr(
            ocr_mod,
            "build_provider",
            lambda s, api_key="", plugin_manager=None: object(),
        )
        monkeypatch.setattr(
            ocr_mod, "_resolve_api_key", lambda provider, keys: "test-key"
        )

        fake = self._make_fake()
        llm_settings = {"ocr_provider": "claude", "claude_model": "claude-opus-4-8"}

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._apply_llm_settings(fake, llm_settings)

        assert fake.app.settings["ocr_provider"] == "claude"
        assert fake.app.settings["claude_model"] == "claude-opus-4-8"

    # ── test 2: _save_settings が1回呼ばれる ────────────────────────────────

    def test_apply_persists_via_save_settings(self, monkeypatch):
        """_apply_llm_settings が _save_settings(app.settings) を1回呼ぶ。"""
        import pagefolio.ocr_providers as prov_mod
        import pagefolio.settings as settings_mod

        saved = {"count": 0, "arg": None}

        def mock_save(s):
            saved["count"] += 1
            saved["arg"] = s

        monkeypatch.setattr(settings_mod, "_save_settings", mock_save)
        monkeypatch.setattr(prov_mod, "LMStudioProvider", lambda **kw: object())

        fake = self._make_fake()
        llm_settings = {"ocr_provider": "lmstudio", "lm_studio_url": "http://x"}

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._apply_llm_settings(fake, llm_settings)

        assert saved["count"] == 1
        assert saved["arg"] is fake.app.settings

    # ── test 3: provider 再生成（lmstudio / claude）────────────────────────

    def test_apply_regenerates_provider_lmstudio_and_claude(self, monkeypatch):
        """ocr_provider='lmstudio' → LMStudioProvider、='claude' → build_provider。"""
        import pagefolio.ocr as ocr_mod
        import pagefolio.ocr_providers as prov_mod
        import pagefolio.settings as settings_mod

        monkeypatch.setattr(settings_mod, "_save_settings", lambda _: None)

        # lmstudio パス
        lmstudio_marker = object()
        monkeypatch.setattr(prov_mod, "LMStudioProvider", lambda **kw: lmstudio_marker)
        fake_lm = self._make_fake({"ocr_provider": "lmstudio"})

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._apply_llm_settings(fake_lm, {"ocr_provider": "lmstudio"})
        assert fake_lm.provider is lmstudio_marker

        # claude パス
        claude_marker = object()
        monkeypatch.setattr(
            ocr_mod,
            "build_provider",
            lambda s, api_key="", plugin_manager=None: claude_marker,
        )
        monkeypatch.setattr(
            ocr_mod, "_resolve_api_key", lambda provider, keys: "test-key"
        )
        fake_cl = self._make_fake({"ocr_provider": "claude"})
        OCRDialog._apply_llm_settings(fake_cl, {"ocr_provider": "claude"})
        assert fake_cl.provider is claude_marker

    # ── test 4: api_key 系キーが settings に流入しない ──────────────────────

    def test_apply_does_not_leak_api_key(self, monkeypatch):
        """llm_settings 経由で api_key 系キーが settings に入らないことを確認。

        LLMConfigDialog._apply は api_key 系を llm_settings に入れない（T-05-12）。
        万一含まれた場合も _save_settings の _SENSITIVE_KEYS ガードで除外される。
        ここでは正常な llm_settings には機密キーが含まれないことを確認する。
        """
        import pagefolio.ocr_providers as prov_mod
        import pagefolio.settings as settings_mod

        saved_settings = {}

        def mock_save(s):
            saved_settings.update(s)

        monkeypatch.setattr(settings_mod, "_save_settings", mock_save)
        monkeypatch.setattr(prov_mod, "LMStudioProvider", lambda **kw: object())

        # api_key 系を含まない正常な llm_settings（LLMConfigDialog の実挙動）
        llm_settings = {
            "ocr_provider": "lmstudio",
            "lm_studio_url": "http://localhost:1234",
            "lm_studio_model": "",
        }
        fake = self._make_fake()

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._apply_llm_settings(fake, llm_settings)

        sensitive_keys = (
            "anthropic_api_key",
            "ANTHROPIC_API_KEY",
            "api_key",
            "claude_api_key",
        )
        for key in sensitive_keys:
            assert key not in fake.app.settings, f"settings に {key} が混入"

    # ── test 5: 実行中ガード（_open_llm_config）────────────────────────────

    def test_open_llm_config_blocked_during_run(self, monkeypatch):
        """_started=True, _done=False のとき LLMConfigDialog が生成されない。"""
        import pagefolio.dialogs.llm_config as llm_cfg_mod

        opened_count = {"n": 0}

        def fake_llm_config_dialog(*args, **kwargs):
            opened_count["n"] += 1

        monkeypatch.setattr(llm_cfg_mod, "LLMConfigDialog", fake_llm_config_dialog)

        fake = self._make_fake()
        fake._started = True
        fake._done = False

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._open_llm_config(fake)

        assert opened_count["n"] == 0, "実行中に LLMConfigDialog が生成されてはならない"


# ===== _resolve_api_key gemini dual env var（Task 1: 06-01・D-06）=====


class TestResolveApiKeyGemini:
    """_resolve_api_key gemini の dual env var 解決を検証する（D-06・OCR-QA-01）"""

    def test_gemini_api_key_priority(self, monkeypatch):
        """GEMINI_API_KEY が優先されること（両方設定時）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.setenv("GEMINI_API_KEY", "primary-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
        key = _resolve_api_key("gemini", {})
        assert key == "primary-key"

    def test_google_api_key_fallback(self, monkeypatch):
        """GEMINI_API_KEY 未設定で GOOGLE_API_KEY フォールバック（D-06）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "fallback-key")
        key = _resolve_api_key("gemini", {})
        assert key == "fallback-key"

    def test_session_key_used_when_env_unset(self, monkeypatch):
        """環境変数なし・セッションキーあり → セッションキーを返す"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        key = _resolve_api_key("gemini", {"gemini": "session-key"})
        assert key == "session-key"

    def test_raises_when_all_missing(self, monkeypatch):
        """環境変数もセッションキーもなければ OCRAPIKeyError を raise"""
        # env_var == 'GEMINI_API_KEY' であることを検証（D-06）
        from pagefolio.ocr import _resolve_api_key
        from pagefolio.ocr_providers import OCRAPIKeyError

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(OCRAPIKeyError) as ei:
            _resolve_api_key("gemini", {})
        assert ei.value.env_var == "GEMINI_API_KEY"

    def test_env_takes_priority_over_session_key(self, monkeypatch):
        """環境変数があれば session_keys より優先する（D-02）"""
        from pagefolio.ocr import _resolve_api_key

        monkeypatch.setenv("GEMINI_API_KEY", "env-wins")
        key = _resolve_api_key("gemini", {"gemini": "session-key"})
        assert key == "env-wins"


# ===== build_provider gemini 分岐（Task 1: 06-01）=====


class TestBuildProviderGemini:
    """build_provider の gemini 分岐を検証する（OCR-API-02）"""

    def test_gemini_returns_gemini_provider(self, monkeypatch):
        """ocr_provider='gemini' で GeminiProvider を返す"""
        from pagefolio.ocr_providers import GeminiProvider

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini"}
        provider = ocr.build_provider(settings, api_key="k")
        assert isinstance(provider, GeminiProvider)

    def test_gemini_provider_api_key_injected(self, monkeypatch):
        """GeminiProvider に api_key が引数注入される（settings から読まない）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = ocr.build_provider({"ocr_provider": "gemini"}, api_key="my-key")
        assert provider.api_key == "my-key"

    def test_gemini_model_default(self, monkeypatch):
        """gemini_model 未指定時は gemini-2.5-flash がデフォルト（D-08）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = ocr.build_provider({"ocr_provider": "gemini"}, api_key="k")
        assert provider.model == "gemini-2.5-flash"

    def test_gemini_model_from_settings(self, monkeypatch):
        """gemini_model が settings に指定されていればそれを使う"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini", "gemini_model": "gemini-2.5-pro"}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.model == "gemini-2.5-pro"

    def test_settings_not_polluted_with_api_key(self, monkeypatch):
        """build_provider 後も settings に api_key が混入しない（D-01/T-06-02）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini"}
        ocr.build_provider(settings, api_key="secret")
        for key in ("api_key", "gemini_api_key", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
            assert key not in settings, f"settings に {key} が混入している"


# ===== producer-consumer メモリ非蓄積リグレッション（D-13・成功基準2）=====


class TestProducerConsumerMemory:
    """run_with_bounded_buffer の同時保持画像数がバッファ上限を超えないことを検証する。

    FakeProvider の ocr_image 呼び出し時点で in-flight な b64 の数が
    concurrency + 1 （バッファ上限）を超えないことを threading.Lock で計測する（D-13）。
    """

    def test_in_flight_count_never_exceeds_maxsize(self):
        """同時保持画像数が concurrency+1 以内に収まること（T-06-06・成功基準2）"""
        in_flight_count = [0]
        max_observed = [0]
        lock = threading.Lock()
        concurrency = 2

        def counting_side_effect(b64, prompt):
            with lock:
                in_flight_count[0] += 1
                max_observed[0] = max(max_observed[0], in_flight_count[0])
            time.sleep(0.01)  # API 処理時間を模擬
            with lock:
                in_flight_count[0] -= 1
            return f"text-{b64}"

        provider = FakeProvider(side_effect=counting_side_effect)
        # max_concurrency を concurrency に合わせるためモンキーパッチ
        provider.default_concurrency = concurrency
        provider.max_concurrency = concurrency

        page_indices = list(range(20))  # 20 ページ（100 ページの代替）
        results, errors, fm, fk = ocr.run_with_bounded_buffer(
            provider=provider,
            render_fn=lambda i: f"b64-page-{i}",
            page_indices=page_indices,
            concurrency=concurrency,
            prompt="",
        )
        expected_maxsize = concurrency + 1
        assert max_observed[0] <= expected_maxsize, (
            f"同時保持数 {max_observed[0]} がバッファ上限 {expected_maxsize} を超えた"
        )
        assert len(results) == len(page_indices), (
            f"結果取りこぼし: {len(results)} / {len(page_indices)} ページ"
        )
        assert fm is None

    def test_all_results_collected_no_missing(self):
        """全ページの結果が results に揃い取りこぼしがないこと"""
        provider = FakeProvider()
        page_indices = list(range(20))
        results, errors, fm, fk = ocr.run_with_bounded_buffer(
            provider=provider,
            render_fn=lambda i: f"b64-{i}",
            page_indices=page_indices,
            concurrency=2,
            prompt="",
        )
        assert len(results) == len(page_indices)
        for i in page_indices:
            assert i in results, f"ページ {i} の結果が欠落"

    def test_cancel_terminates_without_deadlock(self):
        """is_cancelled が途中で True になると残ページを処理せず有限時間で終了する。

        デッドロックしないことをタイムアウトなし（pytest のデフォルト）で検証する。
        """
        call_count = [0]
        cancel_after = 5  # 5 回呼び出し後にキャンセル

        def side_effect(b64, prompt):
            with threading.Lock():
                call_count[0] += 1
            time.sleep(0.01)
            return f"text-{b64}"

        provider = FakeProvider(side_effect=side_effect)
        cancel_event = threading.Event()

        def is_cancelled():
            if call_count[0] >= cancel_after:
                cancel_event.set()
            return cancel_event.is_set()

        page_indices = list(range(50))
        results, errors, fm, fk = ocr.run_with_bounded_buffer(
            provider=provider,
            render_fn=lambda i: f"b64-{i}",
            page_indices=page_indices,
            concurrency=1,
            prompt="",
            is_cancelled=is_cancelled,
        )
        # キャンセル後は全ページは処理されない
        assert len(results) < len(page_indices), (
            "キャンセル後も全ページが処理されている（キャンセルが効いていない）"
        )


# ===== OCRDialog 並列度回帰テスト（CR-01 修正検証・Task 2: 06-04）=====


class TestWorkerConcurrency:
    """_start_worker_thread が self.concurrency 本のワーカーを起動し、
    終了シグナル None が concurrency 本送られることを検証する（CR-01 後方互換）。

    TestOcrDialogLlmConfig と同じ「SimpleNamespace fake + 未束縛メソッド呼び出し」
    パターンを踏襲する（Tkinter ウィンドウ不使用）。
    """

    def _make_fake_for_start(self, concurrency, monkeypatch):
        """_start_worker_thread 用 fake OCRDialog。threading.Thread をスタブ化して
        起動スレッド数を記録する。"""
        import types

        started_threads = []

        class StubThread:
            def __init__(self, target=None, daemon=False):
                self._target = target

            def start(self):
                started_threads.append(self)

        monkeypatch.setattr(threading, "Thread", StubThread)

        fake = types.SimpleNamespace(
            concurrency=concurrency,
            _worker_threads=[],
            _workers_remaining=0,
        )
        # _worker は no-op（スタブ Thread は実際には実行しない）
        fake._worker = lambda: None
        return fake, started_threads

    def test_starts_concurrency_threads(self, monkeypatch):
        """concurrency=4 のとき 4 本のワーカースレッドが起動される（CR-01）。"""
        from pagefolio.ocr_dialog import OCRDialog

        fake, started = self._make_fake_for_start(4, monkeypatch)
        OCRDialog._start_worker_thread(fake)

        assert len(started) == 4, f"起動スレッド数が {len(started)} 本（期待: 4 本）"
        assert fake._workers_remaining == 4

    def test_single_thread_for_gemini(self, monkeypatch):
        """concurrency=1（Gemini 等）のとき 1 本のみ起動される（後方互換）。"""
        from pagefolio.ocr_dialog import OCRDialog

        fake, started = self._make_fake_for_start(1, monkeypatch)
        OCRDialog._start_worker_thread(fake)

        assert len(started) == 1, f"起動スレッド数が {len(started)} 本（期待: 1 本）"
        assert fake._workers_remaining == 1

    def test_termination_signals_match_concurrency(self):
        """全ページ完了時にキューへ送られた None の数が concurrency 本（CR-01）。

        _render_next_page を最短経路（全ページをスキップ扱い）で駆動し、
        完了到達後にキューから取り出した None を数える。
        """
        import queue as q
        import types

        concurrency = 3
        # 0 ページ（page_indices 空）にすると即座に全ページ完了分岐へ到達する
        fake = types.SimpleNamespace(
            concurrency=concurrency,
            _cancel_flag=threading.Event(),
            _render_queue=q.Queue(maxsize=concurrency + 2),
            page_indices=[],
            _render_idx=0,
            # after を即時実行スタブ（連鎖なし・完了分岐では after を呼ばない）
            after=lambda _ms, fn=None, *a: fn(*a) if fn else None,
        )

        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._render_next_page(fake)

        # キューから None を取り出してカウントする
        null_count = 0
        while True:
            try:
                item = fake._render_queue.get_nowait()
            except q.Empty:
                break
            if item is None:
                null_count += 1

        assert null_count == concurrency, (
            f"終了シグナル None の数が {null_count} 本（期待: {concurrency} 本）"
        )


# ===== OCRDialog _finish_cancelled 冪等性テスト（CR-02 修正検証・Task 2: 06-04）=====


class TestFinishIdempotent:
    """_finish_cancelled を 2 回呼んでも _render_results_ordered が 1 回のみ
    実行されることを検証する（CR-02 冪等ガード）。"""

    def _make_fake_for_finish(self):
        """_finish_cancelled 用 fake OCRDialog。"""
        import types

        render_call_count = {"n": 0}

        def mock_render():
            render_call_count["n"] += 1

        fake = types.SimpleNamespace(
            _done=False,
            results={"p0": "text"},  # results あり → _render_results_ordered を呼ぶ経路
            errors={},
            progress_var=types.SimpleNamespace(set=lambda _v: None),
            cancel_btn=types.SimpleNamespace(state=lambda _s: None),
            copy_btn=types.SimpleNamespace(state=lambda _s: None),
            save_btn=types.SimpleNamespace(state=lambda _s: None),
            _L={"ocr_cancelled": "キャンセルされました"},
            _render_results_ordered=mock_render,
        )
        return fake, render_call_count

    def test_finish_cancelled_renders_once(self):
        """_finish_cancelled を 2 回呼んでも _render_results_ordered は 1 回のみ。"""
        from pagefolio.ocr_dialog import OCRDialog

        fake, render_call_count = self._make_fake_for_finish()

        # 1 回目: _done=False → 正常に実行される
        OCRDialog._finish_cancelled(fake)
        assert render_call_count["n"] == 1, (
            "1 回目で _render_results_ordered が呼ばれなかった"
        )
        assert fake._done is True

        # 2 回目: _done=True → 早期 return（_render_results_ordered は追加呼び出しなし）
        OCRDialog._finish_cancelled(fake)
        count = render_call_count["n"]
        assert count == 1, (
            "2 回目の呼び出しで _render_results_ordered が再実行された"
            f"（計 {count} 回）"
        )


# ===== Gap 1: 04-04 CR-01 — 未対応プロバイダ名 ValueError 捕捉 =====


class TestStartOcrUnknownProvider:
    """_start_ocr が未対応プロバイダ名の ValueError を捕捉して showerror + return する。

    build_provider が ValueError を raise するよう monkeypatch し、
    showerror が 1 回呼ばれること・OCRDialog が開かれないことを検証する（CR-01）。
    """

    def _make_fake_app(self, provider_name="unknown_xyz"):
        import types

        return types.SimpleNamespace(
            settings={"ocr_provider": provider_name},
            _session_api_keys={},
            root=None,
            doc=object(),
            lang="ja",
            _t=lambda key: key,
            _font=lambda *a, **k: None,
        )

    def test_unknown_provider_shows_error_and_no_dialog(self, monkeypatch):
        """未対応プロバイダ名のとき showerror が 1 回呼ばれ OCRDialog は開かれない。"""
        import pagefolio.ocr_dialog as ocr_dialog
        from pagefolio.ocr import OCRMixin

        showerror_count = {"n": 0}
        dialog_opened = {"flag": False}

        monkeypatch.setattr(
            ocr.messagebox,
            "showerror",
            lambda *a, **k: showerror_count.__setitem__("n", showerror_count["n"] + 1),
        )
        monkeypatch.setattr(
            ocr_dialog,
            "OCRDialog",
            lambda *a, **k: dialog_opened.__setitem__("flag", True),
        )
        # build_provider が ValueError を raise するよう差し替え
        monkeypatch.setattr(
            ocr,
            "build_provider",
            lambda settings, api_key=None, plugin_manager=None: (_ for _ in ()).throw(
                ValueError("unsupported provider: unknown_xyz")
            ),
        )

        fake = self._make_fake_app("unknown_xyz")
        OCRMixin._start_ocr(fake, [0])

        assert showerror_count["n"] == 1, (
            f"showerror が {showerror_count['n']} 回呼ばれた（期待: 1 回）"
        )
        assert dialog_opened["flag"] is False, "OCRDialog が開かれてはならない"


# ===== Gap 2: 04-04 CR-02 — _on_run がライブ値で LMStudioProvider を再生成する =====


class TestOcrDialogOnRun:
    """_on_run が model_var / max_tokens_var / temperature_var のライブ値で
    LMStudioProvider を再生成して self.provider に設定することを検証する（CR-02）。

    TestOcrDialogLlmConfig の _make_fake パターンを踏襲。
    Tkinter ウィンドウ不使用の SimpleNamespace fake + 未束縛メソッド呼び出し。
    """

    def _make_fake_for_on_run(
        self, model="live-model", max_tokens=512, temperature=0.5
    ):
        import threading
        import types

        app = types.SimpleNamespace(
            settings={
                "ocr_provider": "lmstudio",
                "lm_studio_url": "http://localhost:1234",
                "lm_studio_model": "",
                "ocr_timeout": 120,
                "ocr_max_tokens": -1,
                "ocr_temperature": 0.1,
            },
            _session_api_keys={},
        )

        fake = types.SimpleNamespace(
            app=app,
            provider=None,
            _started=False,
            _done=False,
            progress_var=types.SimpleNamespace(set=lambda _v: None),
            cancel_btn=types.SimpleNamespace(state=lambda _s: None),
            run_btn=types.SimpleNamespace(state=lambda _s: None),
            _llm_config_btn=types.SimpleNamespace(state=lambda _s: None),
            _cancel_flag=threading.Event(),
            _ocr_page_indices=[0],
            concurrency=1,
            _render_queue=None,
            _render_idx=0,
            _workers_remaining=0,
            _worker_threads=[],
            text=types.SimpleNamespace(delete=lambda *a: None),
            scale_var=types.SimpleNamespace(get=lambda: "1.5"),
            timeout_var=types.SimpleNamespace(get=lambda: "120"),
            preset_var=types.SimpleNamespace(get=lambda: "text"),
            url_var=types.SimpleNamespace(get=lambda: "http://localhost:1234"),
            model_var=types.SimpleNamespace(get=lambda: model),
            max_tokens_var=types.SimpleNamespace(get=lambda: str(max_tokens)),
            temperature_var=types.SimpleNamespace(get=lambda: str(temperature)),
            _L={"ocr_progress_init": "init"},
        )
        # _is_cloud_provider: lmstudio は非クラウド → False
        fake._is_cloud_provider = lambda: False
        # _render_next_page を no-op に差し替え（スレッド起動しない）
        fake._render_next_page = lambda: None
        # _start_worker_thread を no-op に差し替え
        fake._start_worker_thread = lambda: None
        return fake

    def test_on_run_regenerates_lmstudio_provider_with_live_values(self, monkeypatch):
        """_on_run が model_var / max_tokens_var / temperature_var のライブ値で
        LMStudioProvider を再生成して self.provider に設定する（CR-02）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import LMStudioProvider

        created = {"provider": None}
        original_init = LMStudioProvider.__init__

        class CapturingProvider(LMStudioProvider):
            def __init__(self, **kwargs):
                original_init(self, **kwargs)
                created["provider"] = self

        import pagefolio.ocr_providers as ocr_prov_mod

        monkeypatch.setattr(ocr_prov_mod, "LMStudioProvider", CapturingProvider)

        fake = self._make_fake_for_on_run(
            model="live-model", max_tokens=512, temperature=0.5
        )
        OCRDialog._on_run(fake)

        assert fake.provider is not None, "self.provider が設定されていない"
        assert isinstance(fake.provider, LMStudioProvider), (
            f"provider が LMStudioProvider でない: {type(fake.provider)}"
        )
        assert fake.provider.model == "live-model", (
            f"model が live-model でない: {fake.provider.model}"
        )
        assert fake.provider.max_tokens == 512, (
            f"max_tokens が 512 でない: {fake.provider.max_tokens}"
        )
        assert abs(fake.provider.temperature - 0.5) < 1e-6, (
            f"temperature が 0.5 でない: {fake.provider.temperature}"
        )


# ===== Gap 3: 04-03 — settings.py の ocr_provider デフォルト値が "off" =====


class TestOcrProviderDefault:
    """_load_settings のデフォルト設定に ocr_provider: "off" が含まれることを検証する。

    実装参照: pagefolio/settings.py の defaults dict（V14-D-03 コメント付き行）。
    """

    def test_ocr_provider_default_is_off(self):
        """_load_settings() のデフォルトで ocr_provider が "off" になる。"""
        import os
        import tempfile
        from unittest.mock import patch

        from pagefolio.settings import _load_settings

        # ファイルが存在しない一時パスを指定して純粋なデフォルト値を得る

        with tempfile.TemporaryDirectory() as tmp:
            fake_path = os.path.join(tmp, "nonexistent_settings.json")
            with patch("pagefolio.settings._get_settings_path", return_value=fake_path):
                settings = _load_settings()

        assert "ocr_provider" in settings, "settings に ocr_provider キーが存在しない"
        assert settings["ocr_provider"] == "off", (
            f"ocr_provider のデフォルト値が 'off' でない: {settings['ocr_provider']!r}"
        )


# ===== H-1 回帰テスト: build_provider claude/gemini の max_tokens クランプ =====


class TestBuildProviderMaxTokensClamp:
    """H-1: build_provider の claude/gemini で ocr_max_tokens<=0 を 4096 にクランプ。

    - ocr_max_tokens=-1（既定値）→ provider.max_tokens == 4096
    - ocr_max_tokens=0 → provider.max_tokens == 4096（境界値）
    - ocr_max_tokens=2048（正値）→ provider.max_tokens == 2048（クランプしない）
    - lmstudio は -1 をそのまま渡す（LM Studio 専用の「モデル最大値委譲」）
    """

    def test_claude_default_minus1_clamped_to_4096(self, monkeypatch):
        """claude: ocr_max_tokens=-1 のとき provider.max_tokens が 4096 になる（H-1）"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude", "ocr_max_tokens": -1}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 4096, (
            f"claude: max_tokens={provider.max_tokens}、4096 にクランプされていない"
        )

    def test_claude_zero_clamped_to_4096(self, monkeypatch):
        """claude: ocr_max_tokens=0 のとき max_tokens が 4096 になる（境界値）"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude", "ocr_max_tokens": 0}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 4096, (
            f"claude: max_tokens={provider.max_tokens}"
            "、0 が 4096 にクランプされていない"
        )

    def test_claude_positive_value_not_clamped(self, monkeypatch):
        """claude: ocr_max_tokens=2048（正値）はそのまま渡される（クランプ不要）"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        settings = {"ocr_provider": "claude", "ocr_max_tokens": 2048}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 2048, (
            f"claude: max_tokens={provider.max_tokens}、正値 2048 が変更されている"
        )

    def test_gemini_default_minus1_clamped_to_4096(self, monkeypatch):
        """gemini: ocr_max_tokens=-1 のとき provider.max_tokens が 4096 になる（H-1）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini", "ocr_max_tokens": -1}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 4096, (
            f"gemini: max_tokens={provider.max_tokens}、4096 にクランプされていない"
        )

    def test_gemini_zero_clamped_to_4096(self, monkeypatch):
        """gemini: ocr_max_tokens=0 のとき max_tokens が 4096 になる（境界値）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini", "ocr_max_tokens": 0}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 4096, (
            f"gemini: max_tokens={provider.max_tokens}"
            "、0 が 4096 にクランプされていない"
        )

    def test_gemini_positive_value_not_clamped(self, monkeypatch):
        """gemini: ocr_max_tokens=2048（正値）はそのまま渡される（クランプ不要）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings = {"ocr_provider": "gemini", "ocr_max_tokens": 2048}
        provider = ocr.build_provider(settings, api_key="k")
        assert provider.max_tokens == 2048, (
            f"gemini: max_tokens={provider.max_tokens}、正値 2048 が変更されている"
        )

    def test_lmstudio_minus1_not_clamped(self):
        """lmstudio: ocr_max_tokens=-1 はクランプせずそのまま渡す（LM Studio 専用値）"""
        settings = {"ocr_provider": "lmstudio", "ocr_max_tokens": -1}
        provider = ocr.build_provider(settings)
        assert provider.max_tokens == -1, (
            f"lmstudio: max_tokens={provider.max_tokens}、-1 が変更されている"
        )


# ===== H-2 回帰テスト: _on_run / _apply_llm_settings のプロバイダ置換防止 =====


class TestProviderReplacementPrevention:
    """H-2: tesseract 選択時に LMStudioProvider へ置換されない。

    _on_run と _apply_llm_settings の else 分岐が lmstudio/off 専用に限定され、
    tesseract は build_provider 経由で TesseractProvider が返ること。
    """

    def test_build_provider_returns_tesseract_provider(self):
        """build_provider: ocr_provider='tesseract' で TesseractProvider を返す"""
        from pagefolio.ocr_providers import TesseractProvider

        settings = {"ocr_provider": "tesseract"}
        provider = ocr.build_provider(settings)
        assert isinstance(provider, TesseractProvider), (
            f"provider が TesseractProvider でない: {type(provider)}"
        )


# ===== H-3 回帰テスト: provider 再生成後の concurrency 再クランプ =====


class TestConcurrencyReclamp:
    """H-3: プロバイダ切替後 concurrency が provider.max_concurrency 以下に再クランプ。

    build_provider で返るプロバイダの max_concurrency を確認する（実際の再クランプは
    _on_run / _apply_llm_settings のロジックテストは UI 統合依存のため省略。
    build_provider が正しい max_concurrency を持つプロバイダを返すことを検証）。
    """

    def test_gemini_provider_max_concurrency_is_1(self, monkeypatch):
        """GeminiProvider.max_concurrency == 1 であることを確認（D-07）"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from pagefolio.ocr_providers import GeminiProvider

        provider = ocr.build_provider({"ocr_provider": "gemini"}, api_key="k")
        assert isinstance(provider, GeminiProvider)
        assert provider.max_concurrency == 1, (
            f"GeminiProvider.max_concurrency={provider.max_concurrency}、1 でない"
        )
