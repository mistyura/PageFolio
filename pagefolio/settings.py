# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""設定ユーティリティ関数"""

import json
import logging
import os

from pagefolio.constants import SETTINGS_FILE, THEMES, C

logger = logging.getLogger(__name__)


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
        "ocr_scale": 2.0,
        "ocr_timeout": 120,
        "ocr_max_tokens": -1,
        "ocr_temperature": 0.1,
        "ocr_concurrency": 2,
        # V14-D-03: 安全デフォルト（Phase 4 では LMStudioProvider として動作）
        "ocr_provider": "off",
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
    """設定を保存する"""
    try:
        path = _get_settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
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
