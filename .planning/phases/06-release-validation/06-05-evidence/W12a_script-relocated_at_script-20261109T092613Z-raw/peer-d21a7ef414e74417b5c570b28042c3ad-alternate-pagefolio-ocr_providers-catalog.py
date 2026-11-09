# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR プロバイダ非機密メタデータ中央カタログ（V190-CAT-01/02・D-01）。

独立性制約: 本モジュールは標準ライブラリと
`pagefolio.ocr_providers.registry` のみに依存し、Provider クラス
（`ocr_providers/claude.py` 等）を import しない。registry への一方向
import のみとし逆方向は作らない（D-05）。

責務境界: 非機密メタデータ（表示名・クラウド種別・既定モデル・送信先
ホスト・フォールバック可否・APIキー欠落 LANG キー）の単一情報源は
本モジュール、機密キー名・環境変数名の単一情報源は `registry.py`。
V190-CAT-01 の「変更面が1箇所」は「軸ごとに1箇所」を意味する
（非機密メタデータ=catalog / 機密キー・環境変数=registry・D-06）。
"""

from dataclasses import dataclass

# D-06: catalog → registry の一方向依存を宣言する（独立性制約テストが
# この import 文の存在を機械検証する）。ただし env_vars_for 自体は
# catalog から re-export しない（呼び出し側は registry を直接 import
# する・既存 sections.py/model_fetch.py の慣習を踏襲）。
from pagefolio.ocr_providers.registry import env_vars_for  # noqa: F401


@dataclass(frozen=True)
class ProviderMeta:
    """プロバイダ 1 件分の非機密メタデータ（フィールド型表は本フェーズ計画書参照）。"""

    name: str
    display_name_key: str | None
    is_cloud: bool
    model_setting_key: str | None
    default_model: str | None
    host: str | None
    fallback_eligible: bool
    api_key_missing_lang_key: str | None


PROVIDERS: dict[str, ProviderMeta] = {
    "off": ProviderMeta(
        name="off",
        display_name_key=None,
        is_cloud=False,
        model_setting_key=None,
        default_model=None,
        host=None,
        fallback_eligible=False,
        api_key_missing_lang_key=None,
    ),
    "lmstudio": ProviderMeta(
        name="lmstudio",
        display_name_key="ocr_provider_name_lmstudio",
        is_cloud=False,
        model_setting_key="lm_studio_model",
        default_model=None,
        host=None,
        fallback_eligible=True,
        api_key_missing_lang_key=None,
    ),
    "ollama": ProviderMeta(
        name="ollama",
        # lang.py に対応する LANG キーが実在しないため None（現行の
        # 未知キー素通し挙動＝ _provider_display_name と一致）。
        display_name_key=None,
        is_cloud=False,
        model_setting_key="ollama_model",
        default_model=None,
        host=None,
        fallback_eligible=True,
        api_key_missing_lang_key=None,
    ),
    "runpod": ProviderMeta(
        name="runpod",
        display_name_key="ocr_provider_name_runpod",
        is_cloud=True,
        model_setting_key="runpod_model",
        default_model=None,
        # host はユーザー設定の runpod_url 依存のため None（host_for が解決）
        host=None,
        fallback_eligible=True,
        api_key_missing_lang_key="ocr_api_key_missing_runpod",
    ),
    "claude": ProviderMeta(
        name="claude",
        display_name_key="ocr_provider_name_claude",
        is_cloud=True,
        model_setting_key="claude_model",
        default_model="claude-sonnet-4-6",
        host="api.anthropic.com",
        fallback_eligible=True,
        api_key_missing_lang_key="ocr_api_key_missing",
    ),
    "gemini": ProviderMeta(
        name="gemini",
        display_name_key="ocr_provider_name_gemini",
        is_cloud=True,
        model_setting_key="gemini_model",
        default_model="gemini-2.5-flash",
        host="generativelanguage.googleapis.com",
        fallback_eligible=True,
        api_key_missing_lang_key="ocr_api_key_missing_gemini",
    ),
    "tesseract": ProviderMeta(
        name="tesseract",
        display_name_key="ocr_provider_name_tesseract",
        is_cloud=False,
        model_setting_key=None,
        default_model=None,
        host=None,
        fallback_eligible=True,
        api_key_missing_lang_key=None,
    ),
    "openai": ProviderMeta(
        name="openai",
        display_name_key="ocr_provider_name_openai",
        is_cloud=True,
        model_setting_key="openai_model",
        # 02-CAPABILITY-MATRIX.md 導出結果(1)で確定した既定モデル。
        default_model="gpt-5.1",
        host="api.openai.com",
        fallback_eligible=True,
        api_key_missing_lang_key="ocr_api_key_missing_openai",
    ),
}


def provider_names(include_off: bool = True) -> list:
    """PROVIDERS の宣言順プロバイダ名リストを返す。"""
    return [n for n in PROVIDERS if include_off or n != "off"]


def fallback_candidate_names() -> list:
    """fallback_eligible=True のプロバイダ名を宣言順で返す（off を含まない）。"""
    return [n for n, m in PROVIDERS.items() if m.fallback_eligible]


def is_cloud_provider(name: str) -> bool:
    """name がクラウドプロバイダなら True。未登録名は False（D-04）。"""
    m = PROVIDERS.get(name)
    return bool(m and m.is_cloud)


def host_for(name: str, settings: dict) -> str:
    """name の送信先ホストを解決する。未登録・解決不能なら空文字。"""
    m = PROVIDERS.get(name)
    if m is None:
        return ""
    if m.host:
        return m.host
    if name == "runpod":
        return settings.get("runpod_url", "")
    return ""


def default_model_for(name: str) -> str:
    """name の既定モデル ID を返す。None・未登録なら空文字。"""
    m = PROVIDERS.get(name)
    return (m.default_model or "") if m else ""


def display_name_key_for(name: str) -> str | None:
    """name の表示名 LANG キーを返す。None・未登録なら None。"""
    m = PROVIDERS.get(name)
    return m.display_name_key if m else None


def model_setting_key_for(name: str) -> str | None:
    """name のモデル設定キー名を返す。None・未登録なら None。"""
    m = PROVIDERS.get(name)
    return m.model_setting_key if m else None


def api_key_missing_lang_key_for(name: str) -> str | None:
    """name の APIキー欠落エラー LANG キーを返す。None・未登録なら None。"""
    m = PROVIDERS.get(name)
    return m.api_key_missing_lang_key if m else None
