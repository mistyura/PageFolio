# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR Mixin — プロバイダ非依存 OCR ユーティリティと LM Studio デフォルト設定"""

import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox

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
DEFAULT_OCR_MAX_TOKENS = -1  # -1: モデル側の最大値（context window）に委ねる
# UI 上の最大値（Qwen2.5 系の 262144 トークンまで）
# LM Studio は max_tokens=-1 でモデル最大値を使うため、通常は -1 で十分
MAX_OCR_MAX_TOKENS = 262144
DEFAULT_OCR_TEMPERATURE = 0.1  # OCR 用途は低温推奨（ハルシネーション抑制）
DEFAULT_OCR_CONCURRENCY = 2  # API 呼び出しの並列度（1〜MAX_OCR_CONCURRENCY）
MAX_OCR_CONCURRENCY = 8

# テキスト埋め込み判定の最小非空白文字数しきい値（D-06 文字数しきい値方式）
# 1〜2 文字程度のページ番号・薄い OCR レイヤーのわずかな文字による誤検出を抑制するため
# 3 文字以上を「テキスト埋め込みあり」と判定する
EMBEDDED_TEXT_MIN_CHARS = 3


def page_to_png_b64(page, scale=DEFAULT_OCR_SCALE):
    """fitz.Page を PNG → base64 文字列に変換する（汎用ユーティリティ）。

    注意: fitz.Page にアクセスするため、メインスレッドで呼び出すこと（D-13/D-05）。
    """
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("ascii")


def has_embedded_text(page, threshold=EMBEDDED_TEXT_MIN_CHARS):
    """ページにテキストが埋め込まれているかを文字数しきい値方式で判定する。

    引数:
      page:      fitz.Page オブジェクト
      threshold: 非空白文字数のしきい値（この値以上なら True）

    戻り値: True（テキスト埋め込みあり = OCR スキップ推奨）/ False（OCR 実行推奨）

    注意: fitz.Page にアクセスするため、メインスレッドから呼び出すこと（D-05）。
    例外: page.get_text() 失敗時は安全側（OCR 実行）として False を返す。

    T-04-05 対応: 抽出テキスト本体をログ出力しない（bool のみ返す）。
    """
    try:
        text = page.get_text()
        # 非空白文字数（スペース・改行・タブを除く）をカウント
        non_ws = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
        return non_ws >= threshold
    except Exception as e:
        logger.debug("has_embedded_text: get_text() 失敗（OCR を実行します）: %s", e)
        return False  # 安全側=OCR 実行


def run_parallel(
    provider,
    images_b64,
    page_indices,
    concurrency=None,
    prompt="",
    timeout=None,
    on_progress=None,
    is_cancelled=None,
):
    """画像辞書(page_idx->b64)を ThreadPoolExecutor でプロバイダ非依存に並列 OCR する。

    引数:
      provider:     OCRProvider インスタンス（ocr_image / max_concurrency を持つ）
      images_b64:   {page_idx: base64_png_str} 画像変換済みのみを含む辞書
      page_indices: 対象ページの順序付きリスト（images_b64 に無いキーはスキップ）
      concurrency:  並列度（None なら provider.default_concurrency を使用）
                    [1, provider.max_concurrency] にクランプされる（D-10）
      prompt:       OCR 指示テキスト
      timeout:      未使用（Provider が内部で保持する）
      on_progress(done, page_idx, status): 完了通知コールバック
      is_cancelled() -> bool: キャンセル判定。True を返すと以降の処理を中止

    戻り値: (results, errors, fatal_msg, fatal_kind) のタプル
      results:    {page_idx: text}
      errors:     {page_idx: message}（ページ単位の失敗）
      fatal_msg / fatal_kind: 致命的エラー（connection / timeout）の最初の発生時
                              のメッセージと種別。無ければ (None, None)
    """
    # 並列度のクランプ（D-10）: concurrency=None なら default_concurrency を使用
    if concurrency is None:
        concurrency = provider.default_concurrency
    workers = max(1, min(provider.max_concurrency, int(concurrency)))

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
            # Provider 非依存: per-page で provider.ocr_image を呼ぶ（D-04）
            text = provider.ocr_image(b64, prompt)
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


def build_provider(settings):
    """settings 辞書から OCRProvider インスタンスを生成するファクトリ。

    引数:
      settings: アプリ設定辞書（lm_studio_url / lm_studio_model 等を参照）

    戻り値: OCRProvider インスタンス

    Phase 4 では ocr_provider 未指定（後方互換）でも LMStudioProvider を返す。
    claude/gemini/tesseract は Phase 5/6/7 で追加予定（D-CONTEXT）。
    """
    # 関数内 import で循環 import を回避（_start_ocr の前例と同様）
    from pagefolio.ocr_providers import LMStudioProvider

    name = settings.get("ocr_provider", "lmstudio")

    if name in ("lmstudio", "", "off"):
        # "off" は Phase 5 で UI 化。Phase 4 では LM Studio として動作させ後方互換を維持
        return LMStudioProvider(
            url=settings.get("lm_studio_url", DEFAULT_LM_STUDIO_URL),
            model=settings.get("lm_studio_model", ""),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS)),
            temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        )
    # Phase 5/6/7 で追加するプロバイダはここに分岐を追加する
    raise ValueError(f"未対応のプロバイダ: {name}")


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

        # build_provider で settings から Provider を生成（CR-01: ValueError を捕捉）
        try:
            provider = build_provider(self.settings)
        except ValueError as e:
            name = self.settings.get("ocr_provider", "")
            logger.error("未対応の OCR プロバイダ '%s' が設定されています: %s", name, e)
            messagebox.showerror(
                self._t("err_title"),
                self._t("ocr_provider_unsupported").format(name=name),
                parent=self.root,
            )
            return

        # 並列度クランプ上限を provider.max_concurrency に変更（D-10）
        concurrency = max(
            1,
            min(
                provider.max_concurrency,
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
            provider=provider,
            lang=self.lang,
            font_func=self._font,
        )
