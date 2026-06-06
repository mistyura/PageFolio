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
