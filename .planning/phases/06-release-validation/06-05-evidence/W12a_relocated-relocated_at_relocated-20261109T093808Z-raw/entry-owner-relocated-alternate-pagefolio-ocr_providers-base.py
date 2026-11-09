# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ抽象基底クラスと URL スキーム検証ヘルパー"""

import abc
import logging
from urllib.parse import urlsplit

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
    # list_models（モデル一覧取得）用タイムアウト秒。OCR 本体の timeout とは
    # 独立した値で、ローカルプロバイダ（LM Studio / Ollama）は即応するため
    # 短い既定 10 秒のまま、クラウドはネットワーク遅延・サーバレスの
    # コールドスタートを見込んで各サブクラスで引き上げる。
    model_list_timeout: int = 10

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
