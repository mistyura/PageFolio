# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR Mixin — LM Studio (OpenAI 互換 Vision API) クライアント"""

import base64
import json
import logging
import socket
import urllib.error
import urllib.request

import fitz

logger = logging.getLogger(__name__)

# プロンプトプリセット
OCR_PROMPTS = {
    "text": (
        "この画像に写っているテキストをすべて正確に書き出してください。"
        "装飾・説明・前置きは不要です。本文のみを出力してください。"
    ),
    "table": (
        "この画像の表をMarkdownテーブル形式で正確に書き出してください。"
        "表以外の説明は不要です。"
    ),
    "markdown": (
        "この画像の内容をMarkdown形式で書き出してください。"
        "見出し・リスト・表を適切に使用し、文書の構造を保ってください。"
    ),
}

DEFAULT_LM_STUDIO_URL = "http://localhost:1234"
DEFAULT_OCR_TIMEOUT = 120  # 秒
DEFAULT_OCR_SCALE = 2.0
DEFAULT_OCR_MAX_TOKENS = -1  # -1: 無制限
DEFAULT_OCR_TEMPERATURE = 0.1  # OCR 用途は低温推奨（ハルシネーション抑制）


def page_to_png_b64(page, scale=DEFAULT_OCR_SCALE):
    """fitz.Page を PNG → base64 文字列に変換する"""
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("ascii")


def build_chat_payload(
    model,
    b64_png,
    prompt,
    max_tokens=DEFAULT_OCR_MAX_TOKENS,
    temperature=DEFAULT_OCR_TEMPERATURE,
):
    """LM Studio (OpenAI 互換) Chat Completions リクエストボディを構築する"""
    return {
        "model": model or "local-model",
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
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }


def call_lm_studio(
    url,
    model,
    b64_png,
    prompt,
    timeout=DEFAULT_OCR_TIMEOUT,
    max_tokens=DEFAULT_OCR_MAX_TOKENS,
    temperature=DEFAULT_OCR_TEMPERATURE,
):
    """LM Studio Chat Completions API を呼び出して結果テキストを返す。

    例外:
      ConnectionError: 接続失敗（LM Studio 未起動等）
      TimeoutError: タイムアウト
      RuntimeError: APIエラー（Vision 非対応モデル等）
    """
    endpoint = url.rstrip("/") + "/v1/chat/completions"
    payload = build_chat_payload(
        model, b64_png, prompt, max_tokens=max_tokens, temperature=temperature
    )
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        raise RuntimeError(f"HTTP {e.code}: {err_body or e.reason}") from e
    except socket.timeout as e:
        raise TimeoutError(f"timed out after {timeout}s") from e
    except urllib.error.URLError as e:
        # URLError は接続拒否やタイムアウトを含む
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"timed out after {timeout}s") from e
        raise ConnectionError(str(reason)) from e

    try:
        result = json.loads(body)
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"Unexpected response format: {body[:500]}") from e


def fetch_lm_studio_models(url, timeout=10):
    """LM Studio /v1/models からモデルID リストを取得する。

    例外:
      ConnectionError: 接続失敗
      TimeoutError: タイムアウト
      RuntimeError: APIエラー
    """
    endpoint = url.rstrip("/") + "/v1/models"
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


class OCRMixin:
    """LM Studio Vision API による OCR Mixin"""

    def _ocr_current_page(self):
        """現在ページを OCR する"""
        if not self._check_doc():
            return
        self._start_ocr([self.current_page])

    def _ocr_selected_pages(self):
        """選択中ページを一括 OCR する（選択ゼロなら現在ページ）"""
        if not self._check_doc():
            return
        targets = sorted(set(self._get_targets()))
        if not targets:
            return
        self._start_ocr(targets)

    def _start_ocr(self, page_indices):
        """OCR ダイアログを開いて非同期実行する"""
        from pagefolio.ocr_dialog import OCRDialog

        url = self.settings.get("lm_studio_url", DEFAULT_LM_STUDIO_URL)
        model = self.settings.get("lm_studio_model", "")
        preset = self.settings.get("ocr_prompt_preset", "text")
        scale = float(self.settings.get("ocr_scale", DEFAULT_OCR_SCALE))
        timeout = int(self.settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT))
        max_tokens = int(self.settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
        temperature = float(
            self.settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)
        )

        OCRDialog(
            self.root,
            app=self,
            doc=self.doc,
            page_indices=page_indices,
            url=url,
            model=model,
            preset=preset,
            scale=scale,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
            lang=self.lang,
            font_func=self._font,
        )
