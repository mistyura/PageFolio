# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR Mixin — プロバイダ非依存 OCR ユーティリティと LM Studio デフォルト設定"""

import base64
import logging
import sys
import time
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

# プロバイダ別 OCR プロンプトテンプレート（V16-AI-02）
# provider → preset → 文言。claude / gemini のみ定義し、それ以外
# （lmstudio / tesseract / off）は汎用 OCR_PROMPTS へフォールバックする
# （Pitfall 4: Tesseract は prompt を無視・LMStudio はモデル依存）。
# claude は XML タグで構造を明示すると精度が上がる傾向、gemini は
# 明示的・命令的な指示を好む傾向に合わせて文言を分けている [ASSUMED]。
PROVIDER_OCR_PROMPTS: "dict[str, dict[str, str]]" = {
    "claude": {
        "text": (
            "<task>画像内のテキストをすべて正確に書き出す</task>\n"
            "<rules>本文のみを出力する。装飾的な前置き・説明・後書きは"
            "一切付けない。</rules>"
        ),
        "table": (
            "<task>画像内の表を Markdown テーブル形式で書き出す</task>\n"
            "<rules>表は | で区切った Markdown テーブルで再現する。"
            "表以外の説明や前置きは出力しない。本文のみ。</rules>"
        ),
        "markdown": (
            "<task>画像内の文書を Markdown で書き出す</task>\n"
            "<rules>見出し(#)・箇条書き(-)・表(|)を元の構造どおりに使う。"
            "装飾的な前置きや説明文は出力しない。本文のみ。</rules>"
        ),
    },
    "gemini": {
        "text": (
            "次の画像を OCR し、写っているテキストをすべて正確に書き出して"
            "ください。前置き・後書き・説明は付けず、本文のみを返してください。"
        ),
        "table": (
            "次の画像内の表を OCR し、Markdown テーブル形式で出力してください。"
            "表以外の説明や前置きは付けず、テーブル本文のみを返してください。"
        ),
        "markdown": (
            "次の画像を OCR し、結果を Markdown 形式で出力してください。"
            "必ず見出し・リスト・表を元の構造どおりに再現し、"
            "前置き・後書き・コードフェンスは付けず本文のみを返してください。"
        ),
    },
}


def resolve_ocr_prompt(preset, provider_name, custom_prompt=""):
    """OCR プロンプトを解決する純関数（Tk/ネットワーク非依存・文字列合成のみ）。

    優先順位:
      1. custom_prompt が非空ならそのまま返す（カスタム上書き最優先）
      2. PROVIDER_OCR_PROMPTS[provider_name][preset]（プロバイダ別テンプレート）
      3. OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])（汎用プリセット・既定 text）

    後方互換: custom_prompt 上書きは現行 _on_run（ocr_dialog.py:1086-1087）の
    「カスタムがあれば完全上書き」挙動を温存する（成功基準3・Pitfall 3）。
    未定義 provider/preset の既定フォールバックは OCR_PROMPTS["text"] で、
    既存 _on_run（ocr_dialog.py:1090）の既定値と一致させて挙動を変えない
    （Pitfall 4: lmstudio / tesseract / off は汎用プロンプトへフォールバック）。

    引数:
      preset:        プロンプトプリセット名（"text" / "table" / "markdown" 等）
      provider_name: プロバイダ名（"claude" / "gemini" / "lmstudio" / ...）
      custom_prompt: ユーザー指定のカスタムプロンプト（非空なら最優先）

    戻り値: 解決済みプロンプト文字列
    """
    if custom_prompt:
        return custom_prompt
    by_provider = PROVIDER_OCR_PROMPTS.get(provider_name, {})
    if preset in by_provider:
        return by_provider[preset]
    return OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])


# 全ページ統合サマリ生成用の既定プロンプト（ドメイン非依存）。
# レシート集計のような業務固有の列指定は ocr_summary_prompt（カスタム）で
# 上書きする想定。入力テキストは "--- Page N ---" 区切りの全ページ連結。
DEFAULT_SUMMARY_PROMPT = (
    '以下は複数ページ文書の OCR 結果です（"--- Page N ---" がページ区切り）。'
    "全ページの内容を統合したサマリを作成してください。"
    "表形式のデータが含まれる場合は、全ページをマージした一覧表を "
    "Markdown テーブルで作成し、合計行も付けてください。"
    "前置き・後書き・説明は不要です。"
)

# プロバイダ別サマリプロンプト（PROVIDER_OCR_PROMPTS と同型・claude/gemini のみ）
PROVIDER_SUMMARY_PROMPTS: "dict[str, str]" = {
    "claude": (
        "<task>複数ページ文書の OCR 結果を統合したサマリを作成する</task>\n"
        '<input>"--- Page N ---" がページ区切りの全ページ連結テキスト</input>\n'
        "<rules>表形式のデータが含まれる場合は、全ページをマージした一覧表を "
        "| 区切りの Markdown テーブルで作成し、合計行も付ける。"
        "装飾的な前置き・説明・後書きは一切付けない。本文のみ。</rules>"
    ),
    "gemini": (
        '次のテキストは複数ページ文書の OCR 結果です（"--- Page N ---" が'
        "ページ区切り）。全ページの内容を統合したサマリを作成してください。"
        "表形式のデータが含まれる場合は、全ページをマージした一覧表を "
        "Markdown テーブルで作成し、合計行も付けてください。"
        "前置き・後書き・コードフェンスは付けず本文のみを返してください。"
    ),
}


def resolve_summary_prompt(provider_name, custom_prompt=""):
    """サマリ生成プロンプトを解決する純関数（resolve_ocr_prompt と同型）。

    優先順位:
      1. custom_prompt が非空ならそのまま返す（カスタム上書き最優先）
      2. PROVIDER_SUMMARY_PROMPTS[provider_name]（プロバイダ別テンプレート）
      3. DEFAULT_SUMMARY_PROMPT（汎用既定）

    引数:
      provider_name: プロバイダ名（"claude" / "gemini" / "lmstudio" / ...）
      custom_prompt: settings["ocr_summary_prompt"] 由来のカスタムプロンプト

    戻り値: 解決済みプロンプト文字列
    """
    if custom_prompt:
        return custom_prompt
    return PROVIDER_SUMMARY_PROMPTS.get(provider_name, DEFAULT_SUMMARY_PROMPT)


def resolve_render_markdown(preset, custom_prompt="", render_markdown=False):
    """結果表示を Markdown 整形描画するかを判定する純関数（Tk 非依存）。

    カスタムプロンプト使用時はプリセット選択が実プロンプトへ反映されない
    （resolve_ocr_prompt / resolve_summary_prompt でカスタムが最優先）ため、
    描画形式もプリセットではなくカスタム側の個別フラグに従う。巨大な
    カスタムプロンプトが Markdown 出力を指示していても、プリセットを
    "markdown" に切り替えずに整形描画を有効化できる。

    引数:
      preset:          プロンプトプリセット名（"text" / "table" / "markdown"）
      custom_prompt:   使用中のカスタムプロンプト（空ならプリセット準拠）
      render_markdown: カスタムプロンプト側の Markdown 描画フラグ
                       （settings["ocr_custom_prompt_markdown"] /
                        settings["ocr_summary_markdown"] 由来）

    戻り値: True なら Markdown 整形描画、False なら素朴描画

    後方互換: custom_prompt が空のときは従来どおり preset == "markdown" の
    判定をそのまま返す（既存ユーザーの描画挙動は変わらない）。
    """
    if custom_prompt:
        return bool(render_markdown)
    return preset == "markdown"


DEFAULT_LM_STUDIO_URL = "http://localhost:1234"
DEFAULT_OCR_TIMEOUT = 120  # 秒
DEFAULT_OCR_SCALE = 1.5  # D-11: 新規既定 1.5 に統一（WR-01）
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

# バックオフ定数（OCR-PERF-04 指数バックオフ）
MAX_RETRIES = 3  # リトライ最大回数（OCRRetryableError 時・無限ループ防止）
RETRY_BASE_DELAY = 1.0  # 初回待機秒数（以降 base * 2**(attempt-1)）

# M-5: Retry-After 上限クランプ（過大値で長時間 sleep する DoS を防止・T-rkp-01）
RETRY_AFTER_CAP = 60.0  # 秒（サーバ指定の Retry-After をこの値以下にクランプ）


def clamp_retry_after(retry_after, cap=RETRY_AFTER_CAP):
    """retry_after（秒）を cap 以下にクランプして返す（M-5・T-rkp-01）。

    引数:
      retry_after: サーバ指定の Retry-After 値（秒・float または int）
      cap:         上限秒数（既定: RETRY_AFTER_CAP=60.0）

    戻り値: min(retry_after, cap)
    """
    return min(retry_after, cap)


def interruptible_sleep(total, is_cancelled, step=0.5):
    """total 秒を step 秒刻みで分割 sleep し、各ステップで is_cancelled を確認する。

    is_cancelled() が True を返した時点で残り時間を打ち切り return する（M-5）。

    引数:
      total:        合計スリープ秒数（float）
      is_cancelled: キャンセル判定関数（() -> bool）
      step:         各スリープのステップ秒数（既定: 0.5）
    """
    remaining = total
    while remaining > 0:
        if is_cancelled():
            return
        chunk = min(step, remaining)
        time.sleep(chunk)
        remaining -= chunk


def _resolve_api_key(provider_name, session_keys):
    """プロバイダ名とセッションキー辞書からAPIキーを解決する。

    優先順位: セッションキー(入力値) > 環境変数（V171-KEY-02・優先順反転）。
    解決できなければ OCRAPIKeyError を raise する（成功基準2）。

    引数:
      provider_name: プロバイダ名（claude / gemini / runpod）
      session_keys:  プロバイダ別セッションキー辞書（例: {"claude": "sk-ant-..."}）

    戻り値: APIキー文字列

    例外:
      OCRAPIKeyError — 環境変数もセッションキーも未設定の場合（env_var 属性付き）

    注意: os.environ への書き込みは一切行わない（読み取り専用原則の継続）。
    """
    import os

    from pagefolio.ocr_providers import OCRAPIKeyError

    if provider_name == "claude":
        env_var = "ANTHROPIC_API_KEY"
        # セッションキー(入力値)を優先（V171-KEY-02）
        key = session_keys.get("claude", "")
        if key:
            return key
        # セッションキー未設定のときのみ環境変数へフォールバック
        key = os.environ.get(env_var)
        if key:
            return key
        # どちらも未設定 → 実行前に明示エラーを raise（成功基準2）
        raise OCRAPIKeyError(env_var)

    if provider_name == "gemini":
        # セッションキー(入力値)を優先（V171-KEY-02）
        key = session_keys.get("gemini", "")
        if key:
            return key
        # dual env var の内部優先順は不変：GEMINI_API_KEY 優先・
        # 未設定なら GOOGLE_API_KEY フォールバック（D-06）。
        # os.environ への書き込みは行わない（読み取り専用原則）。
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            return key
        # どちらも未設定 → 主変数名 GEMINI_API_KEY でエラー（D-06）
        raise OCRAPIKeyError("GEMINI_API_KEY")

    if provider_name == "runpod":
        env_var = "RUNPOD_API_KEY"
        key = session_keys.get("runpod", "")
        if key:
            return key
        key = os.environ.get(env_var)
        if key:
            return key
        raise OCRAPIKeyError(env_var)

    # 未対応プロバイダ
    raise OCRAPIKeyError(f"{provider_name.upper()}_API_KEY")


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
        # OCRRetryableError（429/5xx）は指数バックオフ（最大 MAX_RETRIES 回）でリトライ
        # Retry-After ヘッダがある場合はその値を優先する（OCR-PERF-04）
        from pagefolio.ocr_providers import OCRRetryableError

        for attempt in range(1, MAX_RETRIES + 1):
            # WR-02: リトライ待機直後の再開時にもキャンセル/fatal を再確認し、
            # Cancel 後に追加の課金対象 API 呼び出しが発生しないようにする。
            if _is_cancelled() or fatal["msg"] is not None:
                return ("cancel", page_idx, None)
            try:
                # Provider 非依存: per-page で provider.ocr_image を呼ぶ（D-04）
                text = provider.ocr_image(b64, prompt)
                return ("ok", page_idx, text)
            except OCRRetryableError as e:
                if attempt >= MAX_RETRIES:
                    # 最大リトライ回数に達した → errors に記録
                    return ("err", page_idx, str(e))
                # waiting 進捗を通知（D-15）。status に "waiting/{attempt}" を埋めて
                # リトライ番号を ocr_dialog 側で取得できるようにする
                if on_progress is not None:
                    try:
                        on_progress(None, page_idx, f"waiting/{attempt}")
                    except Exception as pe:
                        logger.debug("on_progress waiting コールバック失敗: %s", pe)
                # Retry-After 優先・なければ指数バックオフ（1s→2s→4s→…）
                raw_delay = (
                    e.retry_after
                    if e.retry_after is not None
                    else RETRY_BASE_DELAY * (2 ** (attempt - 1))
                )
                delay = clamp_retry_after(raw_delay)
                interruptible_sleep(delay, lambda: bool(_is_cancelled()))
            except ConnectionError as e:
                return ("fatal_conn", page_idx, str(e))
            except TimeoutError as e:
                return ("fatal_timeout", page_idx, str(e))
            except RuntimeError as e:
                return ("err", page_idx, str(e))
            except Exception as e:
                logger.exception("OCR 呼び出し失敗: %s", e)
                return ("err", page_idx, str(e))
        # ここには到達しない（for ループ内で必ず return）
        return ("err", page_idx, "リトライ上限超過")

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
        # WR-02: cancel_futures は Python 3.9+ 追加（3.8 互換分岐）
        if sys.version_info >= (3, 9):
            executor.shutdown(wait=False, cancel_futures=True)
        else:
            executor.shutdown(wait=False)

    return results, errors, fatal["msg"], fatal["kind"]


def build_provider(settings, api_key=None, plugin_manager=None):
    """settings 辞書から OCRProvider インスタンスを生成するファクトリ。

    引数:
      settings:       アプリ設定辞書（lm_studio_url / lm_studio_model 等を参照）
      api_key:        クラウドプロバイダ用 API キー（引数注入・settings には格納しない）
                      D-01/D-05: api_key は settings から読まず・settings へ書き込まない
      plugin_manager: PluginManager インスタンス（省略可・None）。
                      _provider_registry 登録プロバイダへのフォールバックを有効化。

    戻り値: OCRProvider インスタンス

    注意: api_key は settings へ書き込まない（D-01・D-05）。
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
    elif name == "claude":
        # api_key は settings から読まず引数のみ・settings へ書き込まない（D-01/D-05）
        from pagefolio.ocr_providers import ClaudeProvider

        # H-1: -1 は LM Studio 専用の「モデル最大値委譲」値。
        # Anthropic API は正の整数必須のため mt <= 0 のとき 4096 にクランプする。
        mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
        mt = 4096 if mt <= 0 else mt
        return ClaudeProvider(
            api_key=api_key or "",
            model=settings.get("claude_model", "claude-sonnet-4-6"),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=mt,
            temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
            effort=settings.get("ocr_effort", "low"),
        )
    elif name == "gemini":
        # api_key は settings から読まず引数のみ・settings へ書き込まない（D-01/D-05）
        # effort パラメータなし（D-09: Gemini は temperature のみ）
        from pagefolio.ocr_providers import GeminiProvider

        # H-1: -1 は LM Studio 専用の「モデル最大値委譲」値。
        # Gemini API も正の整数必須のため mt <= 0 のとき 4096 にクランプする。
        mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
        mt = 4096 if mt <= 0 else mt
        return GeminiProvider(
            api_key=api_key or "",
            model=settings.get("gemini_model", "gemini-2.5-flash"),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=mt,
            temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        )
    elif name == "ollama":
        from pagefolio.ocr_providers import OllamaProvider

        return OllamaProvider(
            url=settings.get("ollama_url", "http://localhost:11434"),
            model=settings.get("ollama_model", ""),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS)),
            temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        )
    elif name == "runpod":
        from pagefolio.ocr_providers import RunPodProvider

        mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
        mt = 4096 if mt <= 0 else mt
        return RunPodProvider(
            api_key=api_key or "",
            url=settings.get("runpod_url", ""),
            model=settings.get("runpod_model", ""),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            max_tokens=mt,
            temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        )
    elif name == "tesseract":
        from pagefolio.ocr_providers import TesseractProvider, _detect_tesseract

        # D-05: build_provider 呼び出しの都度、言語パック検出を再評価する
        # （再起動なしで追加した言語パックを反映）。
        _, _tesseract_langs = _detect_tesseract()
        return TesseractProvider(
            lang=settings.get("tesseract_lang", "jpn+eng"),
            psm=int(settings.get("tesseract_psm", 3)),
            timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
            available_langs=_tesseract_langs,
        )
    # プラグイン登録プロバイダへのフォールバック（D-07）
    # M-7: cls() は引数なしコンストラクタ契約。例外は RuntimeError に正規化。
    # D-10: get_ocr_provider() 公開アクセサ経由で参照（私有属性への直接アクセス廃止）
    cls = plugin_manager.get_ocr_provider(name) if plugin_manager is not None else None
    if cls is not None:
        try:
            return cls()
        except Exception as e:
            raise RuntimeError(
                f"プラグインプロバイダ '{name}' の初期化に失敗しました: {e}"
            ) from e
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
        custom_prompt = self.settings.get("ocr_custom_prompt", "")
        scale = float(self.settings.get("ocr_scale", DEFAULT_OCR_SCALE))
        timeout = int(self.settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT))
        max_tokens = int(self.settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
        temperature = float(
            self.settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)
        )

        # クラウドプロバイダ（claude 等）のキー事前解決（成功基準3・D-02/D-03）
        # 環境変数 or 既存セッションキーがあればここで解決して provider に注入する。
        # 未解決でもここではブロックせず OCRDialog を開く。OCRDialog がマスク付き
        # セッションキー入力欄を表示し（成功基準3）、実行時にキー未入力なら明示エラーで
        # 中止する（成功基準2 は OCRDialog._on_run が担保）。
        name = self.settings.get("ocr_provider", "")
        api_key = None
        _cloud_providers = {
            "claude",
            "gemini",
            "runpod",
        }  # Phase 6: gemini 追加, runpod 追加
        if name in _cloud_providers:
            from pagefolio.ocr_providers import OCRAPIKeyError

            # self._session_api_keys が無い経路（テスト等）に備え getattr で安全に参照
            session_keys = getattr(self, "_session_api_keys", {})
            try:
                api_key = _resolve_api_key(name, session_keys)
            except OCRAPIKeyError:
                # キー未解決: OCRDialog のセッションキー入力欄に委ねる（成功基準3）
                api_key = None

        # build_provider で settings から Provider を生成（CR-01: ValueError を捕捉）
        try:
            provider = build_provider(
                self.settings,
                api_key=api_key,
                plugin_manager=getattr(self, "plugin_manager", None),
            )
        except ValueError as e:
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
            custom_prompt=custom_prompt,
        )
