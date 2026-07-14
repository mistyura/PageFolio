# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""設定ユーティリティ関数"""

import json
import logging
import os

from pagefolio.constants import (
    CUSTOM_PROMPT_FILE,
    SETTINGS_FILE,
    SUMMARY_PROMPT_FILE,
    THEMES,
    C,
)

# 循環 import 回避のためサブモジュール直接指定で import する（Pitfall 6・
# pagefolio.ocr_providers の __init__ 経由だと全プロバイダを import する
# 重い経路になるため使わない）。
from pagefolio.ocr_providers.registry import sensitive_keys

logger = logging.getLogger(__name__)

# D-01: 機密キー集合（_save_settings が JSON へ書き込まないキー名）。
# Pitfall 1: APIキー平文漏洩防止の構造的ガード（最後の砦）。
# registry.sensitive_keys() から生成（V180-ROBUST-02・新プロバイダ追加時の
# 手動追加漏れを構造的に排除）。
_SENSITIVE_KEYS = sensitive_keys()


def _get_base_dir():
    """実行ファイルと同じディレクトリ（開発時はプロジェクトルート）を返す。

    設定ファイル・外部プロンプトファイルの配置基準を一元化する。
    """
    # __main__.py やトップレベル pagefolio.py のあるディレクトリを基準にする
    import sys

    if getattr(sys, "frozen", False):
        # PyInstaller でビルドされた場合
        return os.path.dirname(sys.executable)
    # 通常実行: プロジェクトルート（pagefolio/ パッケージの親）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_settings_path():
    """設定ファイルのパスを返す（実行ファイルと同じディレクトリ）"""
    return os.path.join(_get_base_dir(), SETTINGS_FILE)


def load_prompt_file(filename):
    """実行ファイルと同じ階層の外部プロンプトファイルを読み込む（V174-2）。

    巨大なカスタム/サマリプロンプトを設定欄ではなく md ファイルで管理する
    ための読込層。UTF-8（BOM 付き "utf-8-sig" も許容・Windows のエディタ対応）
    で読み込み、前後の空白を除去して返す。ファイルが存在しない・空・
    読込失敗のときは "" を返す（呼び出し側が設定欄の値へフォールバック）。

    引数:
      filename: CUSTOM_PROMPT_FILE / SUMMARY_PROMPT_FILE 等のファイル名

    戻り値: プロンプト文字列（無効時は ""）
    """
    path = os.path.join(_get_base_dir(), filename)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                return f.read().strip()
    except Exception as e:
        logger.warning("プロンプトファイルの読込に失敗しました (%s): %s", filename, e)
    return ""


def prompt_file_exists(filename):
    """外部プロンプトファイルが実行ファイルと同じ階層に存在するか返す（V174-2）。

    load_prompt_file と異なり空ファイルでも True（「ファイル連動モード」の
    判定に使う。空でも存在すれば LLM 設定の保存時に書き戻し対象となる）。
    """
    return os.path.exists(os.path.join(_get_base_dir(), filename))


def save_prompt_file(filename, content):
    """外部プロンプトファイルへ内容を書き込む（V174-2・UTF-8）。

    LLM 設定ダイアログの「適用」時、ファイル連動モード（ファイルが既に
    存在する場合）に入力欄の内容を書き戻すために使う。ファイルを新規作成は
    しない判断は呼び出し側（prompt_file_exists）の責務。

    引数:
      filename: CUSTOM_PROMPT_FILE / SUMMARY_PROMPT_FILE 等のファイル名
      content:  書き込むプロンプト文字列

    戻り値: 書き込み成功なら True（失敗時は warning ログのみで False）
    """
    path = os.path.join(_get_base_dir(), filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.warning("プロンプトファイルの保存に失敗しました (%s): %s", filename, e)
        return False


def load_custom_prompt(settings):
    """有効なカスタムプロンプトを返す（外部 md ファイル > 設定欄・V174-2）。

    ocr_custom_prompt.md が実行ファイルと同じ階層にあり非空なら、その内容を
    設定欄（settings["ocr_custom_prompt"]）より優先して返す。ファイルは
    呼び出しのたびに読み直すため、外部エディタでの編集が次回実行に反映される。
    """
    return load_prompt_file(CUSTOM_PROMPT_FILE) or settings.get("ocr_custom_prompt", "")


def load_summary_prompt(settings):
    """有効なサマリプロンプトを返す（外部 md ファイル > 設定欄・V174-2）。

    ocr_summary_prompt.md が実行ファイルと同じ階層にあり非空なら、その内容を
    設定欄（settings["ocr_summary_prompt"]）より優先して返す（load_custom_prompt
    と同型）。
    """
    return load_prompt_file(SUMMARY_PROMPT_FILE) or settings.get(
        "ocr_summary_prompt", ""
    )


# ═══════════════════════════════════════════════════════════════
# プロンプトテンプレート管理（v1.8.0 Phase 2・D-01〜D-04）
# ═══════════════════════════════════════════════════════════════
#
# すべて settings 辞書を第1引数に取る関数型 CRUD ヘルパー。既存の
# save_prompt_file/load_custom_prompt と同じ責務分離を踏襲し、settings.py
# 内では自動保存しない（_save_settings() の呼び出しは呼び出し側の責務）。
# 各関数冒頭で settings.setdefault("prompt_templates", ...) を行うため、
# 未初期化の settings 辞書に対しても安全に動作する。


def list_template_names(settings):
    """保存済みテンプレート名の一覧を sorted で返す（V180-TMPL-02）。"""
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    return sorted(settings["prompt_templates"]["items"].keys())


def get_template(settings, name):
    """テンプレート名からペア（custom_prompt/summary_prompt）を返す。

    未登録名の場合は None を返す。
    """
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    return settings["prompt_templates"]["items"].get(name)


def template_name_exists(settings, name):
    """テンプレート名が登録済みか純粋判定する（D-04）。

    空文字・空白のみの名前は save_template が ValueError で拒否するため
    登録され得ず、常に False を返す（無効な名前の弾き判定を兼ねる）。
    """
    if not name or not name.strip():
        return False
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    return name in settings["prompt_templates"]["items"]


def save_template(settings, name, custom_prompt, summary_prompt):
    """テンプレートを保存する（新規作成・上書き更新は共通処理・D-01 ペア保存）。

    name が空文字・空白のみの場合は ValueError を送出する（D-04）。
    既存名を指定した場合は内容を上書きする（新規/更新の区別はしない）。
    """
    if not name or not name.strip():
        raise ValueError("テンプレート名を空にすることはできません")
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    settings["prompt_templates"]["items"][name] = {
        "custom_prompt": custom_prompt,
        "summary_prompt": summary_prompt,
    }


def delete_template(settings, name):
    """テンプレートを削除する。

    アクティブテンプレート（prompt_templates["active"]）と一致する名前は
    ValueError で拒否する（D-03: 誤操作でカスタムプロンプトが消える事故を
    防止する防御的実装。UI 側の削除ボタン無効化と二重防御を構成する）。
    """
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    tpl = settings["prompt_templates"]
    if name and name == tpl["active"]:
        raise ValueError(
            f"アクティブなテンプレート '{name}' は削除できません（先に切替が必要です）"
        )
    tpl["items"].pop(name, None)


def rename_template(settings, old_name, new_name):
    """テンプレートをリネームする。

    new_name が空文字・空白のみ、または既存の別テンプレート名と重複する場合は
    ValueError を送出する（D-04）。old_name が未登録の場合も ValueError。
    old_name がアクティブテンプレートだった場合、active も new_name へ追従更新
    する。
    """
    if not new_name or not new_name.strip():
        raise ValueError("テンプレート名を空にすることはできません")
    settings.setdefault("prompt_templates", {"active": "", "items": {}})
    tpl = settings["prompt_templates"]
    if old_name not in tpl["items"]:
        raise ValueError(f"テンプレート '{old_name}' は存在しません")
    if new_name != old_name and new_name in tpl["items"]:
        raise ValueError(f"テンプレート名 '{new_name}' は既に使用されています")
    tpl["items"][new_name] = tpl["items"].pop(old_name)
    if tpl["active"] == old_name:
        tpl["active"] = new_name


def _load_settings():
    """設定を読み込む。ファイルがなければデフォルト値を返す"""
    defaults = {
        "theme": "dark",
        "font_size": 12,
        "lang": "ja",
        # OCR (LM Studio) 関連デフォルト値
        "lm_studio_url": "http://localhost:1234",
        "lm_studio_model": "",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "",
        "runpod_url": "",
        "runpod_model": "",
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
        # v1.8.0 Phase 2: プロンプトテンプレート管理（D-01/D-02・V180-TMPL-01〜05）
        # active: 現在選択中のテンプレート名（空文字 = 未選択・従来どおり設定欄
        # 直接編集と等価）。items: {テンプレート名: {"custom_prompt": str,
        # "summary_prompt": str}}（D-01: ペア保存）
        "prompt_templates": {"active": "", "items": {}},
        # v1.8.0 Phase 2: プロバイダーフォールバック（D-16・V180-FALL-01）
        # 既定は安全側（無効・空チェーン）。ユーザーが明示的に設定するまで発火しない。
        "ocr_fallback_enabled": False,
        "ocr_fallback_chain": [],
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
