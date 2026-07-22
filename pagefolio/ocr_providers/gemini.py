# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Google Gemini generateContent API プロバイダ"""

import json
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import quote

from pagefolio.ocr_providers.base import OCRProvider
from pagefolio.ocr_providers.errors import _raise_mapped_http_error


class GeminiProvider(OCRProvider):
    """Google Gemini generateContent API プロバイダ（urllib 直叩き）。

    APIキーは GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバックで取得する。
    settings には保存しない。認証は x-goog-api-key ヘッダー（?key= 不使用・D-05）。
    """

    default_concurrency = 1  # D-07: Gemini Free Tier 10 RPM 対応
    max_concurrency = 1  # D-07: 並列度上限
    supports_text_prompt = True
    # クラウド API のネットワーク遅延を見込みモデル一覧取得は 30 秒（V174）
    model_list_timeout = 30

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
          temperature: 温度パラメータ（OCR 用途は低温推奨、既定: 0.1）。
                       gemini-3 世代以降はサンプリングパラメータ指定が
                       400 で拒否されるため送信されず、この値は無視される
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
        """generationConfig（maxOutputTokens / temperature / thinking）を構築する。

        _build_payload と _build_text_payload の共有経路（M-4/H-7 の
        thinkingConfig 分岐を一元化）。

        gemini-3 世代以降は temperature / topP / topK 等のサンプリング
        パラメータと thinkingConfig（thinkingBudget）を含むリクエストが
        400 INVALID_ARGUMENT で拒否されるため、世代を判定できた
        gemini-2.x 以前に限って送信する（省略は全世代で合法＝安全側）。
        """
        gen_config = {
            "maxOutputTokens": self.max_tokens,
        }
        legacy = self._is_legacy_gemini()
        # temperature は gemini-2.x 以前と gemma 等の非 gemini 系のみに送る
        # （gemini-3 世代以降はサンプリングパラメータ指定自体が 400 になる）
        if legacy or not self.model.startswith("gemini"):
            gen_config["temperature"] = self.temperature
        # M-4/H-7: thinkingConfig は gemini-2.x 以前の non-pro（flash 等）のみに送る
        if legacy and "pro" not in self.model:
            # flash 等: thinkingConfig は generationConfig 直下（Pitfall-C・D-09）
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}
        return gen_config

    @staticmethod
    def _model_generation(model):
        """モデル ID 先頭の世代番号を int で返す（判定不能は None）。

        例: "gemini-2.5-flash" → 2、"gemini-3.6-flash" → 3、
        "gemini-flash-latest" / "gemma-3-27b-it" → None。
        """
        m = re.match(r"gemini-(\d+)", model)
        return int(m.group(1)) if m else None

    def _is_legacy_gemini(self):
        """temperature / thinkingConfig を送ってよい旧世代 gemini か判定する。

        gemini-3 世代以降は外部からのサンプリング温度・thinking 制御が
        400 INVALID_ARGUMENT で拒否されるため、世代番号を明示的に 2 以下と
        判定できた場合のみ True。バージョンレスのエイリアス
        （gemini-flash-latest 等）は最新世代とみなし False（安全側）。
        """
        gen = self._model_generation(self.model)
        return gen is not None and gen <= 2

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

        timeout = self.model_list_timeout
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
