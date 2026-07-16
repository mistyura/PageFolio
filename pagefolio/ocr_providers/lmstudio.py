# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LM Studio OpenAI 互換 Vision API プロバイダ"""

import json
import socket
import urllib.error
import urllib.request

from pagefolio.ocr_providers.base import OCRProvider, _require_http_scheme
from pagefolio.ocr_providers.errors import _raise_mapped_http_error


class LMStudioProvider(OCRProvider):
    """LM Studio OpenAI 互換 Vision API プロバイダ（urllib 直叩き）。

    LM Studio の /v1/chat/completions エンドポイントを使って OCR を実行する。
    接続先は settings 由来の URL（既定: http://localhost:1234）を使用する。
    """

    default_concurrency = 2
    max_concurrency = 8
    supports_text_prompt = True

    def __init__(self, url, model, timeout=120, max_tokens=-1, temperature=0.1):
        """初期化。

        引数:
          url:         LM Studio サーバの URL（例: "http://localhost:1234"）
          model:       使用するモデル名（空文字なら "local-model" にフォールバック）
          timeout:     HTTP タイムアウト秒数（既定: 120）
          max_tokens:  最大トークン数（-1 でモデル最大値に委ねる）
          temperature: 温度パラメータ（OCR 用途は低温推奨、既定: 0.1）
        """
        self.url = url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _build_payload(self, b64_png, prompt):
        """LM Studio Chat Completions リクエストボディを構築する（内部メソッド）。"""
        return {
            "model": self.model or "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_png}",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

    def _build_text_payload(self, text, prompt):
        """テキストのみの Chat Completions リクエストボディを構築する（内部）。

        画像ブロックを含めない点以外は _build_payload と同一構造。
        ブロック順は既存の「画像→プロンプト」に対応する「文書テキスト→指示」。
        """
        return {
            "model": self.model or "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

    def _post_chat(self, payload):
        """Chat Completions へ POST し HTTP レスポンス body（str）を返す（内部）。

        HTTP / 接続 / タイムアウトの例外マッピングは ocr_image と同一規約。
        ocr_image と complete_text_ex の両方から呼ばれる共有経路。
        """
        _require_http_scheme(self.url)
        endpoint = self.url.rstrip("/") + "/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            _raise_mapped_http_error(e)
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

    def ocr_image(self, b64_png, prompt, **kwargs):
        """LM Studio Chat Completions API を呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          ConnectionError: 接続失敗（LM Studio 未起動等）
          TimeoutError:    タイムアウト
          OCRRetryableError: HTTP 429/5xx（リトライ可能）
          RuntimeError:    HTTP 4xx（429 以外）またはレスポンス形式不正
        """
        body = self._post_chat(self._build_payload(b64_png, prompt))
        try:
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def complete_text_ex(self, text, prompt, **kwargs):
        """テキストのみを送信し (text, truncated) を返す（サマリ生成用）。

        finish_reason == "length" のとき truncated=True。部分テキストは
        破棄せず返す（途切れは「成功＋警告」・D-05）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_chat(self._build_text_payload(text, prompt))
        try:
            result = json.loads(body)
            choice = result["choices"][0]
            out = choice["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        truncated = choice.get("finish_reason") == "length"
        return (out, truncated)

    def list_models(self):
        """LM Studio /v1/models からモデル ID リストを取得する。

        戻り値: モデル ID 文字列のリスト（list[str]）。None id は除外される。

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        _require_http_scheme(self.url)
        timeout = self.model_list_timeout  # ローカルは即応するため短め（既定 10 秒）
        endpoint = self.url.rstrip("/") + "/v1/models"
        req = urllib.request.Request(endpoint, method="GET")  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {timeout}s") from e
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {timeout}s") from e
            raise ConnectionError(str(reason)) from e

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Unexpected response: {body[:500]}") from e
        return [m.get("id") for m in data.get("data", []) if m.get("id")]
