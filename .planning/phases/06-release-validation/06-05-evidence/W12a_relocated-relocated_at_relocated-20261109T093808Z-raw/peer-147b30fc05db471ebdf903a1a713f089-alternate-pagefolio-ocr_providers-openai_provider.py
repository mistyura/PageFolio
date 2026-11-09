# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OpenAI Chat Completions API プロバイダ"""

import json
import re
import socket
import urllib.error
import urllib.request

from pagefolio.ocr_providers.base import OCRProvider
from pagefolio.ocr_providers.errors import _raise_mapped_http_error

# 02-CAPABILITY-MATRIX.md 導出結果(3)で確定した判定パターン（D-13）。
# 値の根拠は 02-CAPABILITY-MATRIX.md の reasoning_effort 列。
#   - o-series（o1/o1-mini/o1-pro/o3/o3-mini/o3-pro/o4-mini 等）:
#     真ケース実例 "o3"（reasoning_effort=yes 確認済み）
#   - gpt-5 ファミリ（-chat-latest サフィックス付きスナップショットを除く）:
#     真ケース実例 "gpt-5.1"（o 系以外で reasoning_effort=yes と確認済み・
#     レビュー HIGH 02-01-2 対応。gpt-5.1 は「configurable reasoning and
#     non-reasoning effort」に対応する非 o 系推論モデル）
#   - 偽ケース実例: "gpt-4o"（Intelligence バッジ・Reasoning 非対応）、
#     "gpt-5-chat-latest"（gpt-5 ファミリだが -chat-latest サフィックス付き
#     ChatGPT 向けスナップショットで Reasoning 非対応）
_REASONING_O_SERIES_RE = re.compile(r"^o\d")
_REASONING_GPT5_RE = re.compile(r"^gpt-5")
_CHAT_LATEST_SUFFIX = "-chat-latest"

# 02-CAPABILITY-MATRIX.md 導出結果(4)で確認した非チャット/非vision系 ID の
# カテゴリを部分文字列で表す除外マーカー（D-07）。単独の "image" は含めない
# （将来 ID に "image" を含む vision 対応チャットモデルが出た場合の過剰除外を
# 避けるため・レビュー MEDIUM 02-03-3）。画像生成モデルは "gpt-image" という
# より限定的なマーカーで落とす。
#   - "embedding": text-embedding-3-large / -small / ada-002
#   - "tts":       tts-1 / tts-1-hd
#   - "whisper":   whisper-1
#   - "audio":     gpt-4o-mini-tts・gpt-4o-audio-preview 等の音声系
#   - "dall-e":    dall-e-3 等
#   - "gpt-image": gpt-image-1 / -1.5 / -mini / -2 / -latest
#   - "moderation": omni-moderation-latest
#   - "realtime":  gpt-realtime / gpt-4o-realtime-preview 等
#   - "transcribe": gpt-4o-transcribe / gpt-4o-mini-transcribe
#   - "search":    チャット/vision 用途ではない検索系エンドポイント向け ID
_EXCLUDED_MODEL_MARKERS = (
    "embedding",
    "tts",
    "whisper",
    "audio",
    "dall-e",
    "gpt-image",
    "moderation",
    "realtime",
    "transcribe",
    "search",
)

# 02-CAPABILITY-MATRIX.md モデル一覧テーブルの allowed_effort_values 列の
# 転記（D-09・reasoning_effort=yes と確認された行のみ）。キーはモデル ID の
# 完全一致、または（将来の拡張用の）ファミリ接頭辞。reasoning_effort が
# no/unknown のモデル（gpt-4o・gpt-5-chat-latest 等）はエントリを持たない
# （D-10 の安全側省略・02-04 Task 1）。
EFFORT_VALUES_BY_MODEL = {
    "gpt-5-nano": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "gpt-5-mini": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.1": ("none", "low", "medium", "high"),
    "gpt-5.2": ("none", "low", "medium", "high", "xhigh"),
    "gpt-5.6-terra": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "gpt-5.6-sol": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    "o3": ("none", "minimal", "low", "medium", "high", "xhigh", "max"),
}

# 画像 detail レベルの許容値（V190-OAI-08・D-16）。UI 側は readonly
# Combobox でこの値域のみを選ばせるが、pagefolio_settings.json は手編集
# 可能なため、送信直前（_build_payload）でも同じ値域で多層防御する。
_VALID_DETAIL_VALUES = frozenset({"low", "high", "auto"})

# ヘッダ値として不正な ASCII 制御文字（\r/\n/\t を含む \x00-\x1f と \x7f）。
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def effort_values_for_model(model):
    """モデル ID の reasoning_effort 許容値タプルを返す（D-13 系の純関数）。

    値域の一次情報は 02-CAPABILITY-MATRIX.md の allowed_effort_values 列
    （`EFFORT_VALUES_BY_MODEL` へ転記済み）。完全一致 →
    `EFFORT_VALUES_BY_MODEL` の宣言順での接頭辞一致、の順に引く。該当が
    無ければ空タプルを返し、呼び出し側（UI の readonly Combobox・
    `_apply_gen_params` の両方）は reasoning_effort を送らない
    （D-10 の安全側省略・レビュー HIGH 02-04-1）。

    引数:
      model: モデル ID 文字列（None・空文字も許容）

    戻り値: 許容値タプル（tuple[str, ...]）。未記録なら空タプル。
    """
    if not model:
        return ()
    if model in EFFORT_VALUES_BY_MODEL:
        return EFFORT_VALUES_BY_MODEL[model]
    for prefix, values in EFFORT_VALUES_BY_MODEL.items():
        if prefix != model and model.startswith(prefix):
            return values
    return ()


def _sanitize_header_value(value):
    """ヘッダ組み立て直前の多層防御（D-17・T-02-05）。

    `str(value).strip()` した結果に ASCII 制御文字が1つでも含まれる場合は
    空文字を返す。UI 側の入力検証（`_validate_openai_id`）を経由しない
    手編集された `pagefolio_settings.json` 由来の値でも、`_headers()` が
    返すヘッダ値に改行・復帰・その他制御文字が現れないようにする。

    引数:
      value: 検証対象の値（文字列以外も str() で変換して扱う）

    戻り値: 安全な文字列。制御文字を含む場合は空文字。
    """
    cleaned = str(value).strip()
    if _CONTROL_CHAR_RE.search(cleaned):
        return ""
    return cleaned


def filter_selectable_models(model_ids):
    """モデル ID 一覧から OCR/チャット用途でない ID を除外する（D-07・純関数）。

    Tk / HTTP / インスタンス状態には一切触れない。入力順を保ったまま、
    小文字化した ID に `_EXCLUDED_MODEL_MARKERS` のいずれかを含むものを
    除外する。空・None 要素は落とす。

    本関数は**選択肢として提示してよいか**を判定するだけで、**画像入力に
    対応するかは保証しない**。OpenAI の `GET /v1/models` には Anthropic の
    `capabilities.image_input` に相当するフィールドが存在しないため
    （RESEARCH.md Pitfall 2）、能力の確認は 02-CAPABILITY-MATRIX.md と
    `VERIFIED_VISION_MODELS` が担う。

    引数:
      model_ids: モデル ID 文字列のイテラブル（None・空文字混在可）

    戻り値: 除外後のモデル ID リスト（入力順維持・list[str]）
    """
    result = []
    for model_id in model_ids or ():
        if not model_id:
            continue
        lowered = model_id.lower()
        if any(marker in lowered for marker in _EXCLUDED_MODEL_MARKERS):
            continue
        result.append(model_id)
    return result


def order_models_for_display(model_ids):
    """VERIFIED_VISION_MODELS を先頭に据えてモデル ID を並び替える（純関数）。

    `OpenAIProvider.VERIFIED_VISION_MODELS` に含まれる ID をその宣言順で
    先頭へ、残りを入力順のまま後ろへ並べる。重複は先勝ちで 1 回だけ出す。
    Tk / HTTP / インスタンス状態には一切触れない（レビュー HIGH 02-03-1）。

    これにより Combobox の先頭（＝ユーザーが最初に目にする候補と、値未設定
    時に選ばれる候補）が常に画像入力確認済みのモデルになる。

    引数:
      model_ids: モデル ID 文字列のイテラブル

    戻り値: 並び替え後のモデル ID リスト（list[str]）
    """
    ids = list(model_ids or ())
    verified_set = set(OpenAIProvider.VERIFIED_VISION_MODELS)
    seen = set()
    ordered = []
    for verified_id in OpenAIProvider.VERIFIED_VISION_MODELS:
        if verified_id in ids and verified_id not in seen:
            ordered.append(verified_id)
            seen.add(verified_id)
    for model_id in ids:
        if model_id in verified_set or model_id in seen:
            continue
        ordered.append(model_id)
        seen.add(model_id)
    return ordered


def is_reasoning_model(model):
    """モデル ID が推論系（reasoning_effort 対応）かを判定する（D-13・単一判定源）。

    プロバイダ側の temperature 省略（D-11）と UI 側の reasoning effort
    欄の表示切替（D-15・02-04）の両方をこの 1 関数が駆動する。空文字・
    None でも例外を投げず False を返す。

    引数:
      model: モデル ID 文字列（None・空文字も許容）

    戻り値: 推論系なら True、それ以外は False（bool）
    """
    if not model:
        return False
    if _REASONING_O_SERIES_RE.match(model):
        return True
    if _REASONING_GPT5_RE.match(model) and _CHAT_LATEST_SUFFIX not in model:
        return True
    return False


class OpenAIProvider(OCRProvider):
    """OpenAI Chat Completions API プロバイダ（urllib 直叩き）。

    OpenAI の /v1/chat/completions エンドポイントを使って OCR を実行する。
    APIキーは環境変数 OPENAI_API_KEY から取得し、settings には保存しない。
    """

    default_concurrency = 2  # D-14: Claude 相当
    max_concurrency = 2  # D-14
    supports_text_prompt = True
    # クラウド API のネットワーク遅延を見込みモデル一覧取得は 30 秒
    # （Claude/Gemini と同値）。
    model_list_timeout = 30

    CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    MODELS_ENDPOINT = "https://api.openai.com/v1/models"

    # 02-CAPABILITY-MATRIX.md 導出結果(2)。全件 vision_input=yes・
    # evidence=official-doc（inferred 行は含まない）。
    RECOMMENDED_MODELS = [
        "gpt-5-nano",
        "gpt-5-mini",
        "gpt-5.1",
        "gpt-5.2",
        "gpt-4o",
    ]
    # 能力マトリクスで vision_input=yes を確認済みの集合（02-03 がモデル
    # 一覧の並び替え・注記に使う）。
    VERIFIED_VISION_MODELS = tuple(RECOMMENDED_MODELS)

    def __init__(
        self,
        api_key,
        model,
        timeout=120,
        max_tokens=4096,
        temperature=0.1,
        detail="high",
        reasoning_effort=None,
        organization="",
        project="",
    ):
        """初期化。

        引数:
          api_key:          OpenAI API キー（環境変数 OPENAI_API_KEY 由来）
          model:            使用するモデル ID（例: "gpt-5.1"）
          timeout:          HTTP タイムアウト秒数（既定: 120）
          max_tokens:       最大トークン数（max_completion_tokens として送信・
                            既定: 4096）
          temperature:      温度パラメータ（非推論系モデルのみ使用・既定: 0.1）
          detail:           画像 detail レベル（既定: "high"・D-16）
          reasoning_effort: reasoning effort レベル（推論系モデルかつ真値の
                            ときのみ送信・D-15）
          organization:     OpenAI-Organization ヘッダ値（空なら送信しない・D-17）
          project:          OpenAI-Project ヘッダ値（空なら送信しない・D-17）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.detail = detail
        self.reasoning_effort = reasoning_effort
        self.organization = organization
        self.project = project

    def _headers(self):
        """リクエストヘッダを組み立てる（内部・D-17）。

        organization / project は `_sanitize_header_value` を通した後の
        真値のときのみヘッダを追加する（空文字・制御文字入り値は送らない・
        T-02-05 の多層防御）。
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        organization = _sanitize_header_value(self.organization)
        if organization:
            headers["OpenAI-Organization"] = organization
        project = _sanitize_header_value(self.project)
        if project:
            headers["OpenAI-Project"] = project
        return headers

    def _apply_gen_params(self, payload):
        """モデル種別に応じた生成パラメータを payload に付与する（内部）。

        D-10/D-11/D-13 の実装:
        - トークン上限キーは常に max_completion_tokens（max_tokens は
          非推奨のため使わない・D-10）。
        - 推論系モデル（is_reasoning_model 真）には temperature を送らず、
          reasoning_effort が真値 **かつ** effort_values_for_model の
          許容集合に含まれるときのみ reasoning_effort を送る（レビュー
          HIGH 02-04-1・多層防御。pagefolio_settings.json は手編集可能
          なため UI 側の readonly 制約だけでは未知値の送信を防げない）。
        - 非推論系モデルには temperature のみ送る。
        _build_payload と _build_text_payload の共有経路。
        """
        payload["max_completion_tokens"] = self.max_tokens
        if not is_reasoning_model(self.model):
            payload["temperature"] = self.temperature
        elif self.reasoning_effort and self.reasoning_effort in (
            effort_values_for_model(self.model)
        ):
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    def _build_payload(self, b64_png, prompt):
        """OpenAI Chat Completions リクエストボディを構築する（内部メソッド）。

        detail は `_VALID_DETAIL_VALUES`（D-16）に含まれない値なら送信
        直前に "high" へ倒す（edge: V190-OAI-08 invalid-input・多層防御。
        UI 側の readonly Combobox を経由しない手編集された
        pagefolio_settings.json 由来の値でも OCR がエラーにならない）。
        """
        detail = self.detail if self.detail in _VALID_DETAIL_VALUES else "high"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_png}",
                                "detail": detail,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        return self._apply_gen_params(payload)

    def _build_text_payload(self, text, prompt):
        """テキストのみの Chat Completions リクエストボディを構築する（内部）。

        画像ブロックを含めない点以外は _build_payload と同一構造。
        """
        payload = {
            "model": self.model,
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

    def _post_chat(self, payload):
        """Chat Completions へ POST し HTTP レスポンス body（str）を返す（内部）。

        エンドポイントは固定 https 定数のためユーザー入力 URL のスキーム
        検証（_require_http_scheme）は不要。既定の TLS 検証を使う
        （ssl の import・context 指定は行わない）。
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            self.CHAT_ENDPOINT,
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 429/5xx → OCRRetryableError、コンテキスト長超過 → 専用例外（共有・D-12）
            _raise_mapped_http_error(e)
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

    def ocr_image(self, b64_png, prompt, **kwargs):
        """OpenAI Chat Completions API を呼び出して OCR テキストを返す。

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
        body = self._post_chat(self._build_payload(b64_png, prompt))
        try:
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def ocr_image_ex(self, b64_png, prompt, **kwargs):
        """OCR テキストと途切れフラグ (text, truncated) を返す。

        finish_reason == "length" のとき truncated=True。途切れても部分
        テキストは破棄せず返す（途切れは「成功＋警告」）。

        戻り値: (text, truncated) のタプル（str, bool）
        例外:  ocr_image() と同一規約
        """
        body = self._post_chat(self._build_payload(b64_png, prompt))
        try:
            result = json.loads(body)
            choice = result["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e
        truncated = choice.get("finish_reason") == "length"
        return (text, truncated)

    def complete_text_ex(self, text, prompt, **kwargs):
        """テキストのみを送信し (text, truncated) を返す（サマリ生成用）。

        finish_reason == "length" のとき truncated=True。部分テキストは
        破棄せず返す（途切れは「成功＋警告」）。

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
        """OpenAI /v1/models からチャット/vision 向けモデル ID を取得する。

        api_key が偽（空文字/None）のときは API を呼ばず RECOMMENDED_MODELS
        を返す（D-08・claude.py:list_models と同型）。キーがあれば GET
        /v1/models を叩き、filter_selectable_models（D-07）→
        order_models_for_display（レビュー HIGH 02-03-1）の順に通す。
        フィルタ後の結果が空リストになった場合も RECOMMENDED_MODELS へ
        合流する（D-08）。

        D-08 の「同一経路」の解釈（レビュー MEDIUM-11）: 本メソッドは HTTP
        失敗を例外化し、0 件のみ静的一覧へ合流させる。既存 Claude / Gemini
        と同じ構造であり、UI 側（model_fetch.py の _on_error）が例外を
        受けて同じ静的一覧と同じステータスへ合流させる。D-08 が求める
        「失敗時パスの 1 本化」は**観測可能な結末の同一性**（Combobox に
        入る一覧とステータス表示が完全に一致する）として満たす。この同一性
        は tests/test_provider_ui.py の回帰テストで固定されている。

        V190-OAI-13 の適用範囲（レビュー MEDIUM-10）: 429/5xx の指数
        バックオフと Retry-After 尊重は OCR 実行ループ
        （ocr_pipeline.consume_one）の責務であり、モデル一覧取得はその
        ループを通らないため適用対象外。既存 4 プロバイダの list_models も
        同様で、ここだけ非対称にはしない。

        戻り値: モデル ID 文字列のリスト（list[str]）

        例外:
          ConnectionError: 接続失敗
          TimeoutError:    タイムアウト
          RuntimeError:    HTTP エラーまたはレスポンス形式不正
        """
        if not self.api_key:
            return list(self.RECOMMENDED_MODELS)

        req = urllib.request.Request(  # noqa: S310
            self.MODELS_ENDPOINT,
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310
                req, timeout=self.model_list_timeout
            ) as resp:
                body = resp.read().decode("utf-8")
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.model_list_timeout}s") from e
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.model_list_timeout}s") from e
            raise ConnectionError(str(reason)) from e

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Unexpected response: {body[:500]}") from e

        model_ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
        selectable = order_models_for_display(filter_selectable_models(model_ids))
        if not selectable:
            return list(self.RECOMMENDED_MODELS)
        return selectable
