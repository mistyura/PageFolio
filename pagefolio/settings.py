# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""設定ユーティリティ関数"""

import json
import logging
import os

from pagefolio.constants import SETTINGS_FILE, THEMES, C

logger = logging.getLogger(__name__)

# D-01: 機密キー集合（_save_settings が JSON へ書き込まないキー名）
# Pitfall 1: APIキー平文漏洩防止の構造的ガード（最後の砦）
# WR-03: D-06 の dual env var（GEMINI_API_KEY / GOOGLE_API_KEY）フォールバック対応
_SENSITIVE_KEYS = {
    "claude_api_key",
    "gemini_api_key",
    "google_api_key",  # WR-03: Gemini フォールバックキー名（小文字）
    "anthropic_api_key",
    "api_key",
    "GEMINI_API_KEY",  # WR-03: 大文字バリアント
    "GOOGLE_API_KEY",  # WR-03: Gemini フォールバックキー名（大文字・D-06）
    "ANTHROPIC_API_KEY",  # WR-03: 大文字バリアント
}


def _get_settings_path():
    """設定ファイルのパスを返す（実行ファイルと同じディレクトリ）"""
    # __main__.py やトップレベル pagefolio.py のあるディレクトリを基準にする
    import sys

    if getattr(sys, "frozen", False):
        # PyInstaller でビルドされた場合
        base = os.path.dirname(sys.executable)
    else:
        # 通常実行: プロジェクトルート（pagefolio/ パッケージの親）
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, SETTINGS_FILE)


def _load_settings():
    """設定を読み込む。ファイルがなければデフォルト値を返す"""
    defaults = {
        "theme": "dark",
        "font_size": 12,
        "lang": "ja",
        # OCR (LM Studio) 関連デフォルト値
        "lm_studio_url": "http://localhost:1234",
        "lm_studio_model": "",
        "ocr_prompt_preset": "text",
        "ocr_scale": 1.5,  # D-11: 新規ユーザー既定を 1.5 へ変更（低スペック PC 推奨）
        "ocr_timeout": 120,
        "ocr_max_tokens": -1,
        "ocr_temperature": 0.1,
        "ocr_concurrency": 2,
        # V14-D-03: 安全デフォルト（Phase 4 では LMStudioProvider として動作）
        "ocr_provider": "off",
        # Phase 5: Claude Provider 設定（APIキーではない無害な設定値・OCR-UI-01）
        "claude_model": "claude-sonnet-4-6",  # STACK.md 推奨モデル
        "ocr_effort": "low",  # effort 対応モデル時の既定値（D-17）
        # Phase 6: Gemini Provider 設定（APIキーではない無害な設定値・D-08）
        "gemini_model": "gemini-2.5-flash",  # D-08: 推奨モデル既定値
        # Phase 02: サムネイル表示件数（D-04: 既定 20・許容 10〜100）
        # 読み出しは pagination.clamp_page_size 経由で範囲外/非数値を倒す（W1）
        "thumb_page_size": 20,
    }
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception as e:
        logger.debug("設定ファイル読み込み失敗: %s", e)
    return dict(defaults)


def _save_settings(settings):
    """設定を保存する。機密キー（_SENSITIVE_KEYS）は保存対象から除外する（D-01・成功基準1）"""
    # D-01: 機密キー混入チェック（Pitfall 1 構造的ガードの最後の砦）
    # キー値はログに出さず、キー名のみ警告する（D-04・Security Mistakes）
    leaked = [k for k in _SENSITIVE_KEYS if k in settings]
    if leaked:
        for k in leaked:
            logger.error(
                "機密キー '%s' が settings に混入しています（保存から除外します）", k
            )
        # 機密キーを除去した保存用コピーを作成（入力 dict は破壊的変更しない）
        to_save = {k: v for k, v in settings.items() if k not in _SENSITIVE_KEYS}
    else:
        to_save = settings
    try:
        path = _get_settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("設定ファイル保存失敗: %s", e)


def _detect_system_theme():
    """Windowsのシステムテーマを検出。ダーク→'dark'、ライト→'light'"""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception as e:
        logger.debug("システムテーマ検出失敗: %s", e)
        return "dark"


def _resolve_theme(theme_setting):
    """テーマ設定値を実際のテーマ名に解決する"""
    if theme_setting == "system":
        return _detect_system_theme()
    return theme_setting if theme_setting in THEMES else "dark"


def _apply_theme(theme_name):
    """テーマをグローバル辞書Cに適用"""
    resolved = _resolve_theme(theme_name)
    C.update(THEMES[resolved])


def _make_font(delta=0, weight=None, base_size=10):
    """フォントタプルを生成するグローバルヘルパー"""
    size = max(7, base_size + delta)
    if weight:
        return ("Segoe UI", size, weight)
    return ("Segoe UI", size)


# 現在のフォントサイズ（設定から読み込み後に更新）
_current_font_size = 12


def set_current_font_size(size: int) -> None:
    """現在のフォントサイズを更新する公開 setter"""
    global _current_font_size
    _current_font_size = size


def get_current_font_size() -> int:
    """現在のフォントサイズを返す公開 getter"""
    return _current_font_size
