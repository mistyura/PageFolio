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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
DEFAULT_OCR_CONCURRENCY = 2  # API 呼び出しの並列度（1〜MAX_OCR_CONCURRENCY）
MAX_OCR_CONCURRENCY = 8


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


def call_lm_studio_parallel(
    url,
    model,
    prompt,
    images_b64,
    page_indices,
    concurrency=DEFAULT_OCR_CONCURRENCY,
    timeout=DEFAULT_OCR_TIMEOUT,
    max_tokens=DEFAULT_OCR_MAX_TOKENS,
    temperature=DEFAULT_OCR_TEMPERATURE,
    on_progress=None,
    is_cancelled=None,
):
    """画像辞書 (page_idx -> b64) を ThreadPoolExecutor で並列 OCR する。

    引数:
      images_b64: {page_idx: base64_png_str} 画像変換済みのみを含む辞書
      page_indices: 対象ページの順序付きリスト（出力順制御用、images_b64 に
                    無いキーはスキップ）
      concurrency: 並列度（1〜MAX_OCR_CONCURRENCY にクランプ）
      on_progress(done, page_idx, status): 完了通知コールバック。
                    status は "ok" / "err"
      is_cancelled() -> bool: キャンセル判定。True を返すと以降の処理を中止

    戻り値: (results, errors, fatal_msg, fatal_kind) のタプル
      results: {page_idx: text}
      errors:  {page_idx: message}（ページ単位の失敗）
      fatal_msg / fatal_kind: 致命的エラー（connection / timeout）の最初の発生時
                              のメッセージと種別。無ければ (None, None)
    """
    workers = max(1, min(MAX_OCR_CONCURRENCY, int(concurrency)))
    targets = [(p, images_b64[p]) for p in page_indices if p in images_b64]
    if not targets:
        return {}, {}, None, None
    workers = min(workers, len(targets))

    results = {}
    errors = {}
    fatal = {"msg": None, "kind": None}

    def _is_cancelled():
        return bool(is_cancelled and is_cancelled())

    def _call(page_idx, b64):
        if _is_cancelled() or fatal["msg"] is not None:
            return ("cancel", page_idx, None)
        try:
            text = call_lm_studio(
                url,
                model,
                b64,
                prompt,
                timeout=timeout,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return ("ok", page_idx, text)
        except ConnectionError as e:
            return ("fatal_conn", page_idx, str(e))
        except TimeoutError as e:
            return ("fatal_timeout", page_idx, str(e))
        except RuntimeError as e:
            return ("err", page_idx, str(e))
        except Exception as e:
            logger.exception("OCR 呼び出し失敗: %s", e)
            return ("err", page_idx, str(e))

    done = 0
    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        future_to_page = {executor.submit(_call, p, b64): p for p, b64 in targets}
        for future in as_completed(future_to_page):
            if _is_cancelled():
                break
            status, page_idx, payload = future.result()
            if status == "ok":
                results[page_idx] = payload
            elif status == "err":
                errors[page_idx] = payload
            elif status in ("fatal_conn", "fatal_timeout"):
                if fatal["msg"] is None:
                    fatal["msg"] = payload
                    fatal["kind"] = (
                        "connection" if status == "fatal_conn" else "timeout"
                    )
                break
            elif status == "cancel":
                continue
            done += 1
            if on_progress is not None:
                try:
                    on_progress(done, page_idx, status)
                except Exception as e:
                    logger.debug("on_progress コールバック失敗: %s", e)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return results, errors, fatal["msg"], fatal["kind"]


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
        concurrency = max(
            1,
            min(
                MAX_OCR_CONCURRENCY,
                int(self.settings.get("ocr_concurrency", DEFAULT_OCR_CONCURRENCY)),
            ),
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
            concurrency=concurrency,
            lang=self.lang,
            font_func=self._font,
        )
