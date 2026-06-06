# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ抽象基底クラスと各プロバイダ実装"""

import abc
import json
import logging
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class OCRProvider(abc.ABC):
    """OCR プロバイダ抽象基底クラス。

    例外規約:
      ocr_image() および list_models() は以下のいずれかを raise しうる:
        ConnectionError  — 接続失敗（ネットワーク到達不能、サーバ未起動）
        TimeoutError     — タイムアウト
        OCRAPIKeyError   — APIキー未設定（クラウドプロバイダのみ）
        RuntimeError     — APIエラー（4xx/5xx、Vision非対応モデル等）
                           またはレスポンス形式不正
    """

    default_concurrency: int = 2
    max_concurrency: int = 8

    @abc.abstractmethod
    def ocr_image(self, b64_png, prompt, **kwargs):
        """PNG の base64 文字列を送信し OCR テキスト（str）を返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: プロバイダ固有の追加パラメータ

        戻り値: OCR 結果テキスト（str）

        例外:
          ConnectionError / TimeoutError / OCRAPIKeyError / RuntimeError
          （クラス docstring の例外規約を参照）
        """

    @abc.abstractmethod
    def list_models(self):
        """利用可能なモデル ID のリストを返す。取得不能時は空リストを返す。

        戻り値: モデル ID 文字列のリスト（list[str]）

        例外:
          ConnectionError / TimeoutError / RuntimeError（クラス docstring 参照）
        """


class OCRAPIKeyError(RuntimeError):
    """APIキー未設定を示す専用例外。環境変数名を保持する。"""

    def __init__(self, env_var):
        self.env_var = env_var
        super().__init__(f"環境変数 {env_var} が設定されていません")


class LMStudioProvider(OCRProvider):
    """LM Studio OpenAI 互換 Vision API プロバイダ（urllib 直叩き）。

    LM Studio の /v1/chat/completions エンドポイントを使って OCR を実行する。
    接続先は settings 由来の URL（既定: http://localhost:1234）を使用する。
    """

    default_concurrency = 2
    max_concurrency = 8

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
          RuntimeError:    HTTP エラー（4xx/5xx）またはレスポンス形式不正
        """
        endpoint = self.url.rstrip("/") + "/v1/chat/completions"
        payload = self._build_payload(b64_png, prompt)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            raise RuntimeError(f"HTTP {e.code}: {err_body or e.reason}") from e
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

        try:
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def list_models(self):
        """LM Studio /v1/models からモデル ID リストを取得する。

        戻り値: モデル ID 文字列のリスト（list[str]）。None id は除外される。

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        timeout = 10  # モデル一覧取得は短めのタイムアウト
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
