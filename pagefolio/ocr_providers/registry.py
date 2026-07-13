# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ → 環境変数 中央レジストリ（V180-ROBUST-02）。

独立性制約: registry.py は Python 標準ライブラリ（`os`）のみに依存し、
pagefolio 内部の他モジュール（特に `settings.py` や UI 関連モジュール）を
import しない。これは settings.py 等がこのモジュールを参照する際の循環
import を構造的に防ぐための制約であり、将来の変更でも内部モジュールへの
import 依存を追加してはならない。

新プロバイダの機密キー定義追加はこの1ファイルに閉じる（触る場所が1箇所）。
"""

import os

# プロバイダ名 → 環境変数名タプル（タプル順序が解決優先順）。
# Gemini は GEMINI_API_KEY 優先 → GOOGLE_API_KEY フォールバック（D-08）。
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
}


def env_vars_for(provider_name):
    """provider_name に対応する環境変数名のタプルを返す（解決優先順）。

    未登録プロバイダ（LM Studio / Ollama / Tesseract 等の非クラウド）は
    空タプルを返す。
    """
    return PROVIDER_ENV_KEYS.get(provider_name, ())


def primary_env_var(provider_name):
    """provider_name の第一優先環境変数名を返す。未登録なら空文字を返す。

    ocr_dialog.py の送信先確認ダイアログ（provider→env var 表示）が消費する。
    """
    env_vars = env_vars_for(provider_name)
    return env_vars[0] if env_vars else ""


def resolve_env_key(provider_name):
    """provider_name の環境変数値を優先順に解決して返す（見つからなければ None）。

    ocr.py の build_provider キー解決（環境変数フォールバック段）が消費する。
    """
    for env_var in env_vars_for(provider_name):
        value = os.environ.get(env_var)
        if value:
            return value
    return None


def sensitive_keys():
    """settings.json へ書き込んではならない機密キー名の集合を生成する。

    以下の3系統を全プロバイダについて導出し、settings._SENSITIVE_KEYS
    現行10エントリを完全包含する（Pitfall 5）:
      (1) セッションキー形式 "{provider_name}_api_key"
      (2) 各環境変数名そのものと、その小文字バリアント（.lower()）
      (3) プロバイダ非依存の汎用 "api_key"

    戻り値: 機密キー名の集合（set[str]）
    """
    keys = {"api_key"}
    for provider_name, env_vars in PROVIDER_ENV_KEYS.items():
        keys.add(f"{provider_name}_api_key")
        for var in env_vars:
            keys.add(var)
            keys.add(var.lower())
    return keys
