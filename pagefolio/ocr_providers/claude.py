# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Anthropic Claude messages API プロバイダ"""

import json
import socket
import urllib.error
import urllib.request
from urllib.parse import quote

from pagefolio.ocr_providers.base import OCRProvider
from pagefolio.ocr_providers.errors import _raise_mapped_http_error


class ClaudeProvider(OCRProvider):
    """Anthropic Claude messages API プロバイダ（urllib 直叩き）。

    Anthropic の /v1/messages エンドポイントを使って OCR を実行する。
    APIキーは環境変数 ANTHROPIC_API_KEY から取得し、settings には保存しない。
    """

    default_concurrency = 2
    max_concurrency = 2
    supports_text_prompt = True
    # クラウド API のネットワーク遅延を見込みモデル一覧取得は 30 秒（V174）
    model_list_timeout = 30

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
        timeout = self.model_list_timeout
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
