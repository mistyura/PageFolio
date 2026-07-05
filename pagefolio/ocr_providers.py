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
from urllib.parse import quote, urlsplit

logger = logging.getLogger(__name__)

# L-6e/D-13: ユーザー入力 URL/エンドポイントを持つ全プロバイダ
# （LM Studio / Ollama / RunPod）へ共通適用する許可スキーム。
_ALLOWED_URL_SCHEMES = ("http", "https")


def _require_http_scheme(url):
    """url のスキームが http/https のみであることを検証する（L-6e・D-13）。

    リクエスト送信の直前（`_post_chat`/`list_models` 冒頭）で呼ぶこと。
    コンストラクタでの eager 検証は行わない（空URL/入力途中の値でも
    プロバイダのインスタンス化自体は失敗させない既存方針との整合・A2）。

    引数:
      url: 検証対象の URL 文字列

    例外:
      RuntimeError: スキームが http/https 以外（file:// 等の悪用防止）
    """
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise RuntimeError(f"サポートされていない URL スキームです: {scheme or url}")


class OCRProvider(abc.ABC):
    """OCR プロバイダ抽象基底クラス。

    例外規約:
      ocr_image() および list_models() は以下のいずれかを raise しうる:
        ConnectionError       — 接続失敗（ネットワーク到達不能、サーバ未起動）
        TimeoutError          — タイムアウト
        OCRAPIKeyError        — APIキー未設定（クラウドプロバイダのみ）
        OCRRetryableError     — HTTP 429/5xx（リトライ可能・全プロバイダ共通）
        OCRContextLengthError — 入力がコンテキスト長上限を超過（400/413/422
                                + body 判定。主に complete_text_ex で発生）
        RuntimeError          — その他 APIエラー（4xx、Vision非対応モデル等）
                                またはレスポンス形式不正
    """

    default_concurrency: int = 2
    max_concurrency: int = 8
    # テキストのみ補完（complete_text_ex）対応フラグ。LLM 系プロバイダで True。
    supports_text_prompt: bool = False

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

    def complete_text_ex(self, text, prompt, **kwargs):
        """テキストのみを LLM に送信し (text, truncated) を返す（サマリ生成用）。

        引数:
          text:   入力テキスト（複数ページの OCR 結果連結など）
          prompt: 指示テキスト（サマリ生成指示など）
          **kwargs: プロバイダ固有の追加パラメータ

        戻り値: (text, truncated) のタプル（str, bool）。
          truncated はトークン超過等で応答が途切れたとき True。
          部分テキストは破棄せず常に返す（途切れは「成功＋警告」・D-05）。

        既定は NotImplementedError（Tesseract 等の非 LLM プロバイダ）。
        supports_text_prompt が True のプロバイダのみオーバーライドする。
        送信中の 1 リクエストは urlopen の制約上、即時中断できない
        （キャンセルは呼び出し側のリトライ待機でのみ反応する）。

        例外:
          ocr_image() と同一の例外規約（クラス docstring 参照）に加え、
          非対応プロバイダでは NotImplementedError。
        """
        raise NotImplementedError(
            f"{type(self).__name__} はテキストのみの補完に対応していません"
        )


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


class OCRContextLengthError(RuntimeError):
    """入力がモデルのコンテキスト長上限を超えたことを示す専用例外。

    サマリ生成（全ページ連結テキスト）で入力過大の 4xx を検出し、
    「ページ数を減らして再実行」の専用ガイダンス表示に使う。
    判定漏れは従来どおり RuntimeError に落ちる（安全側フォールバック）。
    """


# コンテキスト長超過エラーの body 判定マーカー（小文字比較）。
# OpenAI 互換: context_length_exceeded / Claude: prompt is too long
# Gemini: exceeds the maximum number of tokens / 汎用: context length 等
_CONTEXT_ERROR_MARKERS = (
    "context_length_exceeded",
    "context length",
    "maximum context",
    "maximum number of tokens",
    "too many tokens",
    "prompt is too long",
    "input token",
    "token limit",
)


def parse_retry_after(headers):
    """Retry-After ヘッダー値を float 秒として解析する（純関数）。

    headers が None・ヘッダー欠落・数値でない値（HTTP-date 形式等）は
    None を返す。全プロバイダの 429/5xx 変換で共用する。
    """
    raw = headers.get("Retry-After") if headers else None
    if not raw:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def looks_like_context_error(code, body):
    """HTTP エラーがコンテキスト長超過らしいかを判定する純関数。

    400/413/422 のいずれかで、かつ body に既知のマーカー文字列が
    含まれるとき True。マーカーは小文字比較。
    """
    if code not in (400, 413, 422):
        return False
    lowered = (body or "").lower()
    return any(marker in lowered for marker in _CONTEXT_ERROR_MARKERS)


def _raise_mapped_http_error(e):
    """urllib.error.HTTPError を共通例外規約へ変換して送出する（内部共有）。

    429/5xx           → OCRRetryableError（Retry-After を反映）
    コンテキスト長超過 → OCRContextLengthError（400/413/422 + body 判定）
    その他 4xx        → RuntimeError（従来文言 "HTTP {code}: {body}" を維持）

    全プロバイダの HTTPError ハンドラから呼ばれ、リトライ挙動を対称化する。
    """
    if e.code == 429 or e.code >= 500:
        raise OCRRetryableError(
            _retryable_http_message(e.code),
            retry_after=parse_retry_after(e.headers),
            code=e.code,
        ) from e
    try:
        err_body = e.read().decode("utf-8", errors="replace")
    except Exception:
        err_body = ""
    # L-6d: 巨大レスポンスによる UI/ログ肥大を防ぐため一定長で切り詰める
    # （全プロバイダ共通ヘルパーのため 5 プロバイダ全てのエラーメッセージに波及）。
    err_body = err_body[:500]
    message = f"HTTP {e.code}: {err_body or e.reason}"
    if looks_like_context_error(e.code, err_body):
        raise OCRContextLengthError(message) from e
    raise RuntimeError(message) from e


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
    supports_text_prompt = True

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
        return self._apply_gen_params(payload)

    def _apply_gen_params(self, payload):
        """モデル種別に応じた生成パラメータを payload に付与する（内部・M-3）。

        3 分岐で安全なパラメータを付与する:
          - effort 対応（EFFORT_MODELS 完全一致）→ output_config.effort のみ
          - haiku 系 → temperature のみ
          - 未知モデル → 両方省略（最も安全な前方互換・D-16）
        _build_payload と _build_text_payload の共有経路。
        """
        if self._supports_effort():
            # effort 対応モデル: output_config を付与（temperature は送らない）
            payload["output_config"] = {"effort": self.effort}
        elif self._supports_temperature():
            # haiku 系: temperature を付与（output_config は送らない・D-16）
            payload["temperature"] = self.temperature
        # それ以外（未知モデル）: 両方省略（最も安全な前方互換）
        return payload

    def _build_text_payload(self, text, prompt):
        """テキストのみの messages API リクエストボディを構築する（内部）。

        画像ブロックを含めない点以外は _build_payload と同一構造。
        ブロック順は既存の「画像→プロンプト」に対応する「文書テキスト→指示」。
        """
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        return self._apply_gen_params(payload)

    def _post_messages(self, b64_png, prompt):
        """messages API へ POST し HTTP レスポンス body（str）を返す（内部）。

        HTTP / 接続 / タイムアウトの例外マッピングは ocr_image と同一規約
        （OCRRetryableError / RuntimeError / TimeoutError / ConnectionError）。
        ocr_image と ocr_image_ex の両方から呼ばれる共有経路。
        """
        return self._post_payload(self._build_payload(b64_png, prompt))

    def _post_payload(self, payload):
        """messages API へ payload を POST し HTTP レスポンス body（str）を返す。

        _post_messages（画像あり）と complete_text_ex（テキストのみ）の共有経路。
        """
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
            # 429/5xx → OCRRetryableError、コンテキスト長超過 → 専用例外（共有）
            _raise_mapped_http_error(e)
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

    def complete_text_ex(self, text, prompt, **kwargs):
        """テキストのみを送信し (text, truncated) を返す（サマリ生成用）。

        stop_reason == "max_tokens" のとき truncated=True。部分テキストは
        破棄せず返す（途切れは「成功＋警告」・D-05）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_payload(self._build_text_payload(text, prompt))
        try:
            result = json.loads(body)
            out = self._extract_text(result, body)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        truncated = result.get("stop_reason") == "max_tokens"
        return (out, truncated)

    def _fetch_models_page(self, after_id=None):
        """Anthropic /v1/models を1ページ分呼び出し、レスポンス dict を返す（内部）。

        after_id 指定時はカーソルを進めて次ページを取得する（L-6b）。
        HTTP / 接続 / タイムアウトの例外マッピングは list_models と同一規約。
        """
        timeout = 10
        endpoint = self.MODELS_ENDPOINT
        if after_id:
            endpoint = f"{endpoint}?after_id={quote(after_id, safe='')}"
        req = urllib.request.Request(  # noqa: S310
            endpoint,
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
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Unexpected response: {body[:500]}") from e

    def list_models(self):
        """Anthropic /v1/models から vision 対応モデル ID リストを取得する。

        キー未設定（空文字/None）の場合は API を呼ばず
        RECOMMENDED_MODELS を返す（D-08）。

        L-6b: `has_more`/`last_id` カーソルを辿り全ページのモデルを連結して
        返す（1 ページで完結する応答では従来と同じ結果になる後方互換）。

        戻り値: モデル ID 文字列のリスト（list[str]）

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        if not self.api_key:
            # キー未設定・オフライン時でも選択肢が出るよう静的リストを返す（D-08）
            return list(self.RECOMMENDED_MODELS)

        results = []
        after_id = None
        while True:
            data = self._fetch_models_page(after_id=after_id)
            # capabilities.image_input.supported が True のモデルのみ返す
            results.extend(
                m.get("id")
                for m in data.get("data", [])
                if m.get("id")
                and m.get("capabilities", {})
                .get("image_input", {})
                .get("supported", False)
            )
            if data.get("has_more") and data.get("last_id"):
                after_id = data.get("last_id")
                continue
            break
        return results


class GeminiProvider(OCRProvider):
    """Google Gemini generateContent API プロバイダ（urllib 直叩き）。

    APIキーは GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバックで取得する。
    settings には保存しない。認証は x-goog-api-key ヘッダー（?key= 不使用・D-05）。
    """

    default_concurrency = 1  # D-07: Gemini Free Tier 10 RPM 対応
    max_concurrency = 1  # D-07: 並列度上限
    supports_text_prompt = True

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
        return {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64_png}},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": self._build_generation_config(),
        }

    def _build_generation_config(self):
        """generationConfig（temperature / maxOutputTokens / thinking）を構築する。

        _build_payload と _build_text_payload の共有経路（M-4/H-7 の
        thinkingConfig 分岐を一元化）。
        """
        gen_config = {
            "temperature": self.temperature,
            "maxOutputTokens": self.max_tokens,
        }
        # M-4/H-7: thinkingConfig は gemini の non-pro（flash 等）のみに送る
        if self.model.startswith("gemini") and "pro" not in self.model:
            # flash 等: thinkingConfig は generationConfig 直下（Pitfall-C・D-09）
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}
        return gen_config

    def _build_text_payload(self, text, prompt):
        """テキストのみの generateContent リクエストボディを構築する（内部）。

        inline_data（画像）を含めない点以外は _build_payload と同一構造。
        パーツ順は既存の「画像→プロンプト」に対応する「文書テキスト→指示」。
        """
        return {
            "contents": [
                {
                    "parts": [
                        {"text": text},
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": self._build_generation_config(),
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
        return self._post_payload(self._build_payload(b64_png, prompt))

    def _post_payload(self, payload):
        """generateContent API へ payload を POST し body（str）を返す（内部）。

        _post_generate（画像あり）と complete_text_ex（テキストのみ）の共有経路。
        """
        # L-6f: モデル名を URL パスセグメントとしてエスケープする
        # （予約文字を含むモデル名で意図しないパス/クエリにならないよう防止）。
        safe_model = quote(self.model, safe="")
        endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=safe_model)
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
            # 429/5xx → OCRRetryableError、コンテキスト長超過 → 専用例外（共有）
            _raise_mapped_http_error(e)
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

    def complete_text_ex(self, text, prompt, **kwargs):
        """テキストのみを送信し (text, truncated) を返す（サマリ生成用）。

        finishReason == "MAX_TOKENS" のとき truncated=True。部分テキストは
        破棄せず返す（途切れは「成功＋警告」・D-05）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_payload(self._build_text_payload(text, prompt))
        try:
            result = json.loads(body)
            out = self._parse_response(result)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        truncated = self._is_truncated(result)
        return (out, truncated)

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
    """Tesseract の存在・インストール済み言語を検出する関数。

    D-05: import 時に一度だけ固定するのではなく、TesseractProvider の生成時
    （build_provider 呼び出しの都度・llm_config.py の UI 構築時）に**都度呼び出し
    可能**な関数として設計する。呼び出しコストは subprocess 起動2回（数十ms）で
    頻度的に無視できる。呼び出しの都度 subprocess を起動しないこと（並列 OCR の
    ocr_image からは呼ばない — Anti-Pattern）。

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


class TesseractProvider(OCRProvider):
    """Tesseract OCR プロバイダ（subprocess 直呼び・ネットワーク不要）。

    tesseract コマンドを stdin パイプ方式で呼び出して OCR を実行する。
    API キー・ネットワーク接続は不要でオフライン環境でも動作する。

    注意: LLM ベースのプロバイダより精度が劣る場合があります。
    """

    default_concurrency = 1  # CPU バウンド・シングルスレッド前提
    max_concurrency = 2

    RECOMMENDED_LANGS: list = ["jpn+eng", "eng", "jpn"]

    def __init__(self, lang="jpn+eng", psm=3, timeout=60, available_langs=None):
        """初期化。

        引数:
          lang:    Tesseract に渡す要求言語コード（例: "jpn+eng"）。"+" 区切りで
                   複数指定可能。段階的縮退（D-06）により実際に使われる言語は
                   self.effective_lang に確定される。
          psm:     ページセグメンテーションモード（3=全自動、6=単一ブロック）
          timeout: subprocess タイムアウト秒数（既定: 60）
          available_langs: 検出済みの利用可能言語集合（frozenset[str] 等）。
                   None（既定）のときはこの場で _detect_tesseract() を呼び直し
                   再検出する（D-05: プロバイダ生成時に都度再評価・再起動不要で
                   言語パック追加を反映）。呼び出し元（build_provider 等）が
                   再検出済みの結果を明示的に渡すことも可能。
        """
        self.lang = lang
        self.psm = psm
        self.timeout = timeout
        if available_langs is None:
            _, available_langs = _detect_tesseract()
        self.available_langs = available_langs or frozenset()
        # D-06: __init__ 時点で段階的縮退を確定し、ocr_image は都度計算しない
        self.effective_lang, self.lang_fallback = self._resolve_lang(
            self.lang, self.available_langs
        )
        # フォールバック発生時の注記表示（D-07・Task 2）が読む要求/実効ペア
        self.requested_lang = self.lang

    @staticmethod
    def _resolve_lang(requested_raw, available_langs):
        """段階的縮退で実効言語を確定する（D-06）。

        まず要求言語（"+" 区切り）のうち利用可能な部分集合を、要求の指定順を
        保ったまま残す。部分集合が非空ならそれを実効言語とする。空（＝全滅、
        または要求自体が空）なら現行の自動決定（jpn 利用可→"jpn+eng" /
        なし→"eng"）へ落とす。常にどちらかの分岐で値を返し、例外は送出しない
        （必ず何かしらの言語で実行できることを保証する）。

        戻り値: (effective_lang: str, fallback_occurred: bool) のタプル。
        fallback_occurred は「要求言語が非空で、かつ実効言語が要求と完全一致
        しない」場合に True になる。
        """
        requested = [t for t in (requested_raw or "").split("+") if t]
        subset = [t for t in requested if t in available_langs]
        if subset:
            return "+".join(subset), subset != requested
        auto = "jpn+eng" if "jpn" in available_langs else "eng"
        return auto, bool(requested)

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
        # -l へ渡すのは __init__ で段階的縮退済みの実効言語のみ（検出済み集合
        # との積を取った結果）。生の self.lang を直接渡さない（T-2-T01 mitigate）。
        lang = self.effective_lang
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


class OllamaProvider(OCRProvider):
    """Ollama OpenAI 互換 API プロバイダ（urllib 直叩き）。

    Ollama の /v1/chat/completions エンドポイントを使って OCR を実行する。
    接続先は settings 由来の URL（既定: http://localhost:11434）を使用する。
    """

    default_concurrency = 2
    max_concurrency = 8
    supports_text_prompt = True

    def __init__(self, url, model, timeout=120, max_tokens=-1, temperature=0.1):
        """初期化。

        引数:
          url:         Ollama サーバの URL（例: "http://localhost:11434"）
          model:       使用するモデル名（空文字なら "llava" にフォールバック）
          timeout:     HTTP タイムアウト秒数（既定: 120）
          max_tokens:  最大トークン数（-1 でモデル最大値に委ねる）
          temperature: 温度パラメータ（OCR 用途は低温推奨、既定: 0.1）
        """
        self.url = url or "http://localhost:11434"
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _build_payload(self, b64_png, prompt):
        """Ollama Chat Completions リクエストボディを構築する（内部メソッド）。"""
        return {
            "model": self.model or "llava",
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
            "model": self.model or "llava",
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
            # 429/5xx → OCRRetryableError、コンテキスト長超過 → 専用例外（共有）
            _raise_mapped_http_error(e)
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

    def ocr_image(self, b64_png, prompt, **kwargs):
        """Ollama Chat Completions API を呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          ConnectionError: 接続失敗（Ollama 未起動等）
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
        """Ollama /v1/models からモデル ID リストを取得する。

        戻り値: モデル ID 文字列のリスト（list[str]）。None id は除外される。

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        _require_http_scheme(self.url)
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


class RunPodProvider(OCRProvider):
    """RunPod Serverless OpenAI 互換 Vision API プロバイダ（urllib 直叩き）。

    RunPod の API キーは環境変数 RUNPOD_API_KEY から取得し、settings には保存しない。
    接続先エンドポイント URL は settings 由来の URL を使用する。
    """

    default_concurrency = 2
    max_concurrency = 4
    supports_text_prompt = True

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

        timeout = 10
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
