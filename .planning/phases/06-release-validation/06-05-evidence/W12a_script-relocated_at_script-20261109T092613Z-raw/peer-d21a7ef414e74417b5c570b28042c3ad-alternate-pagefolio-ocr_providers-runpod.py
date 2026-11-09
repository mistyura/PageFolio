# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""RunPod Serverless OpenAI 互換 Vision API プロバイダ"""

import json
import socket
import urllib.error
import urllib.request

from pagefolio.ocr_providers.base import OCRProvider, _require_http_scheme
from pagefolio.ocr_providers.errors import OCRAPIKeyError, _raise_mapped_http_error


class RunPodProvider(OCRProvider):
    """RunPod Serverless OpenAI 互換 Vision API プロバイダ（urllib 直叩き）。

    RunPod の API キーは環境変数 RUNPOD_API_KEY から取得し、settings には保存しない。
    接続先エンドポイント URL は settings 由来の URL を使用する。
    """

    default_concurrency = 2
    max_concurrency = 4
    supports_text_prompt = True
    # Serverless の初回起動（コールドスタート）はワーカー起動＋モデル
    # ロード待ちで 10 秒を大きく超えることがあるため 90 秒に引き上げる
    # （V174。取得は llm_config 側でバックグラウンド実行し UI は塞がない）
    model_list_timeout = 90

    def __init__(
        self, api_key, url, model, timeout=120, max_tokens=-1, temperature=0.1
    ):
        """初期化。

        引数:
          api_key:     RunPod API キー（環境変数 RUNPOD_API_KEY 由来）
          url:         RunPod Serverless エンドポイント URL
          model:       使用するモデル名（空文字なら "runpod-model" にフォールバック）
          timeout:     HTTP タイムアウト秒数（既定: 120）
          max_tokens:  最大トークン数（-1 でモデル最大値に委ねる）
          temperature: 温度パラメータ（OCR 用途は低温推奨、既定: 0.1）
        """
        self.api_key = api_key
        self.url = url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _build_payload(self, b64_png, prompt):
        """RunPod Chat Completions リクエストボディを構築する（内部メソッド）。"""
        return {
            "model": self.model or "runpod-model",
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
            "model": self.model or "runpod-model",
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

    def ocr_image(self, b64_png, prompt, **kwargs):
        """RunPod Serverless API を呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          OCRAPIKeyError:  APIキー未設定
          ConnectionError: 接続失敗
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

    def _post_chat(self, payload):
        """Chat Completions へ POST し HTTP レスポンス body（str）を返す（内部）。

        API キー / URL 未設定チェックと 429/5xx の OCRRetryableError 変換を含む。
        ocr_image と complete_text_ex の両方から呼ばれる共有経路。
        """
        if not self.api_key:
            raise OCRAPIKeyError("RUNPOD_API_KEY")
        if not self.url:
            raise RuntimeError("RunPod エンドポイントURLが設定されていません")
        _require_http_scheme(self.url)

        endpoint = self.url.rstrip("/") + "/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 429/5xx → OCRRetryableError、コンテキスト長超過 → 専用例外（共有）
            _raise_mapped_http_error(e)
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

    def list_models(self):
        """RunPod /models からモデル ID リストを取得する。"""
        if not self.api_key or not self.url:
            return [self.model] if self.model else ["runpod-model"]
        _require_http_scheme(self.url)

        timeout = self.model_list_timeout
        endpoint = self.url.rstrip("/") + "/models"

        req = urllib.request.Request(  # noqa: S310
            endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
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
