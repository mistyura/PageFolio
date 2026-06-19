# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ抽象基底クラスと各プロバイダ実装"""

import abc
import base64
import json
import logging
import socket
import subprocess
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

    def ocr_image_ex(self, b64_png, prompt, **kwargs):
        """OCR テキストと応答途切れフラグのタプルを返す（段階導入・A1）。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: プロバイダ固有の追加パラメータ

        戻り値: (text, truncated) のタプル（typing.Tuple[str, bool] 相当）。
          truncated はトークン超過等で応答が途切れたとき True。
          基底デフォルトは (ocr_image(...), False) で、途切れ未対応プロバイダ
          （LM Studio / Tesseract）はこのまま後方互換となる。途切れを検出する
          プロバイダ（Claude / Gemini）のみオーバーライドする。
          部分テキストは破棄せず常に返す（途切れは「成功＋警告」・D-05）。

        例外:
          ocr_image() と同一の例外規約（クラス docstring 参照）。
        """
        return (self.ocr_image(b64_png, prompt, **kwargs), False)


class OCRAPIKeyError(RuntimeError):
    """APIキー未設定を示す専用例外。環境変数名を保持する。"""

    def __init__(self, env_var):
        self.env_var = env_var
        super().__init__(f"環境変数 {env_var} が設定されていません")


class OCRRetryableError(RuntimeError):
    """429/5xx リトライ可能エラー。retry_after（秒）と HTTP ステータスを保持する。

    code は 429（レート制限）と 5xx（サーバエラー）の表示分岐に使う。
    不明な発生元（プラグイン等）では None のままでよい。
    """

    def __init__(self, message, retry_after=None, code=None):
        self.retry_after = retry_after
        self.code = code
        super().__init__(message)


def _retryable_http_message(code):
    """HTTP ステータスコードからリトライ可能エラーの表示文言を組み立てる。

    429 はレート制限、5xx はサーバ側エラーであり別物のため文言を分ける
    （500 を「レート制限」と誤認させない）。
    """
    if code == 429:
        return "HTTP 429: レート制限（リトライ可能）"
    return f"HTTP {code}: サーバエラー（リトライ可能）"


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


class ClaudeProvider(OCRProvider):
    """Anthropic Claude messages API プロバイダ（urllib 直叩き）。

    Anthropic の /v1/messages エンドポイントを使って OCR を実行する。
    APIキーは環境変数 ANTHROPIC_API_KEY から取得し、settings には保存しない。
    """

    default_concurrency = 2
    max_concurrency = 2

    ANTHROPIC_VERSION = "2023-06-01"
    MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
    MODELS_ENDPOINT = "https://api.anthropic.com/v1/models"
    RECOMMENDED_MODELS = ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8"]

    # effort 対応モデル集合（haiku は非対応・D-16）
    EFFORT_MODELS = {
        "claude-sonnet-4-6",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-opus-4-5",
    }

    def __init__(
        self,
        api_key,
        model,
        timeout=120,
        max_tokens=4096,
        temperature=0.1,
        effort="low",
    ):
        """初期化。

        引数:
          api_key:     Anthropic API キー（環境変数 ANTHROPIC_API_KEY 由来）
          model:       使用するモデル ID（例: "claude-sonnet-4-6"）
          timeout:     HTTP タイムアウト秒数（既定: 120）
          max_tokens:  最大トークン数（既定: 4096）
          temperature: 温度パラメータ（haiku のみ使用・既定: 0.1）
          effort:      effort レベル（sonnet/opus 系で使用・既定: "low"）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.effort = effort

    def _supports_effort(self):
        """このモデルが effort パラメータ（output_config）に対応しているか判定する。

        M-3: EFFORT_MODELS 完全一致時のみ True。前方互換の prefix 判定を撤廃。
        戻り値: EFFORT_MODELS 完全一致モデルは True、それ以外は False。
        """
        return self.model in self.EFFORT_MODELS

    def _supports_temperature(self):
        """このモデルが temperature パラメータに対応しているか判定する。

        M-3: haiku 系のみ True。それ以外（未知モデル含む）は False。
        """
        return "haiku" in self.model

    def _build_payload(self, b64_png, prompt):
        """Anthropic messages API リクエストボディを構築する（内部メソッド）。

        M-3: 3 分岐で安全なパラメータを付与する。
          - effort 対応（EFFORT_MODELS 完全一致）→ output_config.effort のみ
          - haiku 系 → temperature のみ
          - 未知モデル → 両方省略（最も安全な前方互換・D-16）
        """
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_png,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        if self._supports_effort():
            # effort 対応モデル: output_config を付与（temperature は送らない）
            payload["output_config"] = {"effort": self.effort}
        elif self._supports_temperature():
            # haiku 系: temperature を付与（output_config は送らない・D-16）
            payload["temperature"] = self.temperature
        # それ以外（未知モデル）: 両方省略（最も安全な前方互換）
        return payload

    def _post_messages(self, b64_png, prompt):
        """messages API へ POST し HTTP レスポンス body（str）を返す（内部）。

        HTTP / 接続 / タイムアウトの例外マッピングは ocr_image と同一規約
        （OCRRetryableError / RuntimeError / TimeoutError / ConnectionError）。
        ocr_image と ocr_image_ex の両方から呼ばれる共有経路。
        """
        payload = self._build_payload(b64_png, prompt)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            self.MESSAGES_ENDPOINT,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 429 または 5xx はリトライ可能として OCRRetryableError を送出する
            if e.code == 429 or e.code >= 500:
                retry_after = None
                raw_retry = e.headers.get("Retry-After") if e.headers else None
                if raw_retry:
                    try:
                        retry_after = float(raw_retry)
                    except (ValueError, TypeError):
                        retry_after = None
                raise OCRRetryableError(
                    _retryable_http_message(e.code),
                    retry_after=retry_after,
                    code=e.code,
                ) from e
            # 4xx（429 以外）は retryable ではない
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

    @staticmethod
    def _extract_text(result, body):
        """Claude messages レスポンス（dict）から text ブロックを結合して返す。

        M-9: block.get("text") で text キー欠落ブロックを安全にスキップ。
        content[0] 決め打ち禁止（Pitfall 6）。text が無ければ RuntimeError。
        """
        texts = [
            block.get("text")
            for block in result.get("content", [])
            if block.get("type") == "text" and block.get("text")
        ]
        if not texts:
            raise RuntimeError(f"Unexpected response format: {body[:500]}")
        return "\n".join(texts)

    def ocr_image(self, b64_png, prompt, **kwargs):
        """Anthropic messages API を呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          OCRRetryableError: HTTP 429 または 5xx（リトライ可能）
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP 4xx（429 以外）またはレスポンス形式不正
        """
        body = self._post_messages(b64_png, prompt)
        try:
            result = json.loads(body)
            return self._extract_text(result, body)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def ocr_image_ex(self, b64_png, prompt, **kwargs):
        """OCR テキストと途切れフラグ (text, truncated) を返す（D-05・A2）。

        stop_reason == "max_tokens" のとき truncated=True。途切れても部分
        テキストは破棄せず返す（途切れは「成功＋警告」として扱う・Pitfall 2）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_messages(b64_png, prompt)
        try:
            result = json.loads(body)
            text = self._extract_text(result, body)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        # stop_reason は外部入力のため .get() 安全アクセス（A2）
        truncated = result.get("stop_reason") == "max_tokens"
        return (text, truncated)

    def list_models(self):
        """Anthropic /v1/models から vision 対応モデル ID リストを取得する。

        キー未設定（空文字/None）の場合は API を呼ばず
        RECOMMENDED_MODELS を返す（D-08）。

        戻り値: モデル ID 文字列のリスト（list[str]）

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        if not self.api_key:
            # キー未設定・オフライン時でも選択肢が出るよう静的リストを返す（D-08）
            return list(self.RECOMMENDED_MODELS)

        timeout = 10
        req = urllib.request.Request(  # noqa: S310
            self.MODELS_ENDPOINT,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
            },
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

        # capabilities.image_input.supported が True のモデルのみ返す
        return [
            m.get("id")
            for m in data.get("data", [])
            if m.get("id")
            and m.get("capabilities", {}).get("image_input", {}).get("supported", False)
        ]


class GeminiProvider(OCRProvider):
    """Google Gemini generateContent API プロバイダ（urllib 直叩き）。

    APIキーは GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバックで取得する。
    settings には保存しない。認証は x-goog-api-key ヘッダー（?key= 不使用・D-05）。
    """

    default_concurrency = 1  # D-07: Gemini Free Tier 10 RPM 対応
    max_concurrency = 1  # D-07: 並列度上限

    GENERATE_CONTENT_ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent"
    )
    MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
    RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]  # D-08

    def __init__(self, api_key, model, timeout=120, max_tokens=4096, temperature=0.1):
        """初期化。

        引数:
          api_key:     Google API キー（GEMINI_API_KEY / GOOGLE_API_KEY 由来）
          model:       使用するモデル ID（例: "gemini-2.5-flash"）
          timeout:     HTTP タイムアウト秒数（既定: 120）
          max_tokens:  最大出力トークン数（既定: 4096）
          temperature: 温度パラメータ（OCR 用途は低温推奨、既定: 0.1）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _build_payload(self, b64_png, prompt):
        """Gemini generateContent リクエストボディを構築する（内部メソッド）。

        M-4: pro 系モデルでは thinkingConfig を省略（2.5-pro は thinking 無効化不可）。
        flash 等（non-pro）は thinkingBudget=0 で thinking を無効化する（D-09）。
        H-7: gemma 等の非 gemini 系モデルは thinkingConfig 非対応で
        400 INVALID_ARGUMENT になるため、gemini の non-pro に限って送信する。
        """
        gen_config = {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_tokens,
        }
        # M-4/H-7: thinkingConfig は gemini の non-pro（flash 等）のみに送る
        if self.model.startswith("gemini") and "pro" not in self.model:
            # flash 等: thinkingConfig は generationConfig 直下（Pitfall-C・D-09）
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}
        return {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64_png}},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": gen_config,
        }

    def _parse_response(self, body):
        """Gemini レスポンス JSON から OCR テキストを抽出する（内部メソッド）。

        candidates 空チェック必須（安全フィルタ・RECITATION ブロック対策・Pitfall-D）。
        """
        candidates = body.get("candidates", [])
        if not candidates:
            reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
            raise RuntimeError(f"Gemini blocked: {reason}")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p["text"] for p in parts if "text" in p]
        if not texts:
            raise RuntimeError(f"Gemini: no text in response: {body}")
        return "\n".join(texts)

    def _post_generate(self, b64_png, prompt):
        """generateContent API へ POST し HTTP レスポンス body（str）を返す（内部）。

        HTTP / 接続 / タイムアウトの例外マッピングは ocr_image と同一規約。
        ocr_image と ocr_image_ex の両方から呼ばれる共有経路。
        """
        endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=self.model)
        payload = self._build_payload(b64_png, prompt)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                # ヘッダー認証（?key= URL クエリ不使用・D-05）
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 429 または 5xx はリトライ可能（ClaudeProvider と同一構造）
            if e.code == 429 or e.code >= 500:
                retry_after = None
                raw_retry = e.headers.get("Retry-After") if e.headers else None
                if raw_retry:
                    try:
                        retry_after = float(raw_retry)
                    except (ValueError, TypeError):
                        retry_after = None
                raise OCRRetryableError(
                    _retryable_http_message(e.code),
                    retry_after=retry_after,
                    code=e.code,
                ) from e
            # 4xx（429 以外）は retryable ではない
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

    @staticmethod
    def _is_truncated(result):
        """Gemini レスポンスが finishReason==MAX_TOKENS で途切れたか判定する（A2）。

        candidates / finishReason は外部入力のため .get() 安全アクセス。
        candidates 欠落時は False（途切れではない）。
        """
        candidates = result.get("candidates", [])
        if not candidates:
            return False
        return candidates[0].get("finishReason") == "MAX_TOKENS"

    def ocr_image(self, b64_png, prompt, **kwargs):
        """Gemini generateContent API を呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          OCRRetryableError: HTTP 429 または 5xx（リトライ可能）
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP 4xx（429 以外）またはレスポンス形式不正・ブロック
        """
        body = self._post_generate(b64_png, prompt)
        # レスポンス解析: candidates[].content.parts[].text を結合
        try:
            result = json.loads(body)
            return self._parse_response(result)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def ocr_image_ex(self, b64_png, prompt, **kwargs):
        """OCR テキストと途切れフラグ (text, truncated) を返す（D-05・A2）。

        finishReason == "MAX_TOKENS" のとき truncated=True。途切れても部分
        テキストは破棄せず返す（途切れは「成功＋警告」として扱う・Pitfall 2）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_generate(b64_png, prompt)
        try:
            result = json.loads(body)
            text = self._parse_response(result)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        truncated = self._is_truncated(result)
        return (text, truncated)

    def list_models(self):
        """Gemini /v1beta/models から generateContent 対応モデル ID リストを取得する。

        キー未設定（空文字/None）の場合は API を呼ばず
        RECOMMENDED_MODELS を返す（D-08）。

        戻り値: モデル ID 文字列のリスト（list[str]）。"models/" プレフィックスを除去。

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        if not self.api_key:
            # キー未設定・オフライン時でも選択肢が出るよう静的リストを返す（D-08）
            return list(self.RECOMMENDED_MODELS)

        timeout = 10
        req = urllib.request.Request(  # noqa: S310
            self.MODELS_ENDPOINT,
            headers={"x-goog-api-key": self.api_key},
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

        # supportedGenerationMethods に "generateContent" を含むモデルのみ返す
        # "models/gemini-2.5-flash" → "gemini-2.5-flash" にプレフィックスを除去
        return [
            m.get("name", "").replace("models/", "")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
            and m.get("name", "")
        ]


def _detect_tesseract():
    """起動時に一度だけ呼ばれる Tesseract 存在チェック関数。

    戻り値: (available: bool, langs: frozenset[str]) のタプル。
    Tesseract が見つかれば (True, {インストール済み言語...}) を、
    見つからなければ (False, frozenset()) を返す。
    """
    try:
        r = subprocess.run(
            ["tesseract", "--version"],  # noqa: S603 S607
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            return False, frozenset()
        # --list-langs でインストール済み言語を取得
        # Windows は stdout、Linux 系は stderr に出力する場合があるため両方を確認
        r2 = subprocess.run(
            ["tesseract", "--list-langs"],  # noqa: S603 S607
            capture_output=True,
            timeout=5,
        )
        raw = (r2.stdout or r2.stderr).decode(errors="replace")
        langs = frozenset(
            line.strip()
            for line in raw.splitlines()
            if line.strip() and not line.lower().startswith("list of")
        )
        return True, langs
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, frozenset()


# アプリ起動時に一度だけ評価（D-01）
_TESSERACT_AVAILABLE, _TESSERACT_LANGS = _detect_tesseract()


class TesseractProvider(OCRProvider):
    """Tesseract OCR プロバイダ（subprocess 直呼び・ネットワーク不要）。

    tesseract コマンドを stdin パイプ方式で呼び出して OCR を実行する。
    API キー・ネットワーク接続は不要でオフライン環境でも動作する。

    注意: LLM ベースのプロバイダより精度が劣る場合があります。
    """

    default_concurrency = 1  # CPU バウンド・シングルスレッド前提
    max_concurrency = 2

    RECOMMENDED_LANGS: list = ["jpn+eng", "eng", "jpn"]

    def __init__(self, lang="jpn+eng", psm=3, timeout=60):
        """初期化。

        引数:
          lang:    Tesseract に渡す言語コード（例: "jpn+eng"）。
                   実際の ocr_image 実行時は _TESSERACT_LANGS による自動解決を優先する。
          psm:     ページセグメンテーションモード（3=全自動、6=単一ブロック）
          timeout: subprocess タイムアウト秒数（既定: 60）
        """
        self.lang = lang
        self.psm = psm
        self.timeout = timeout

    def ocr_image(self, b64_png, prompt, **kwargs):
        """Tesseract を stdin パイプ方式で呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト（Tesseract では無視される。インターフェース互換用）
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          RuntimeError:  tesseract コマンドが見つからない、または終了コード != 0
          TimeoutError:  tesseract がタイムアウト（D-T2）
        """
        # jpn が利用可能なら jpn+eng、なければ eng にフォールバック（D-04）
        lang = "jpn+eng" if "jpn" in _TESSERACT_LANGS else "eng"
        png_bytes = base64.b64decode(b64_png)
        try:
            result = subprocess.run(  # noqa: S603
                ["tesseract", "stdin", "stdout", "-l", lang, "--psm", str(self.psm)],  # noqa: S607
                input=png_bytes,
                capture_output=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as e:
            raise RuntimeError("tesseract コマンドが見つかりません") from e
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(
                f"Tesseract がタイムアウトしました ({self.timeout}s)"
            ) from e
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"Tesseract エラー (rc={result.returncode}): {err}")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def list_models(self):
        """利用可能な Tesseract 言語コードのリストを返す。

        戻り値: ["tesseract"]（固定の単一エントリ）
        """
        return ["tesseract"]
