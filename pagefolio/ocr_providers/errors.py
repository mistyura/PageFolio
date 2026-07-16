# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ共通の例外クラスと HTTP エラー変換ヘルパー"""


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
