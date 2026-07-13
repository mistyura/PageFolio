"""pagefolio import 回帰テスト

REFAC-01〜04 のリファクタリングで変更・追加された import パスが
壊れていないことを「明示 import 文 + シンボル存在 assert」で検証する。

- TestConstantsImports  : REFAC-02 — constants / lang / themes の import 検証
- TestDialogsImports    : REFAC-01 — dialogs サブパッケージの import 検証
- TestSettingsApiImports: REFAC-04 — settings 公開 API の import と roundtrip
- TestPackageSurface    : pagefolio トップレベルの公開サーフェス存在検証

D-06: 明示 import 文 + assert のみ（importlib 動的方式は不採用）
D-08: Tk root 不要・ヘッドレス安全（dialog クラスはインスタンス化しない）
D-09: import 回帰テストはこのファイルに集約する
"""

import os
import sys

# pagefolio パッケージをインポートできるようにプロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pagefolio  # noqa: E402

# =============================================================================
# REFAC-02: constants / lang / themes の import パス検証
# =============================================================================


class TestConstantsImports:
    """REFAC-02 後方互換 — constants/lang/themes モジュールの import 検証"""

    def test_app_version_from_constants(self):
        """constants から APP_VERSION を import できる"""
        from pagefolio.constants import APP_VERSION

        assert APP_VERSION is not None

    def test_lang_from_constants(self):
        """constants から LANG を import できる（後方互換）"""
        from pagefolio.constants import LANG

        assert LANG is not None

    def test_themes_from_constants(self):
        """constants から THEMES を import できる（後方互換）"""
        from pagefolio.constants import THEMES

        assert THEMES is not None

    def test_c_from_constants(self):
        """constants から C（実行時テーマ辞書）を import できる（後方互換）"""
        from pagefolio.constants import C

        assert isinstance(C, dict)

    def test_constants_backward_compat_all(self):
        """constants から APP_VERSION/LANG/THEMES/C を一括 import できる"""
        from pagefolio.constants import APP_VERSION, LANG, THEMES, C

        assert APP_VERSION is not None
        assert LANG is not None
        assert THEMES is not None
        assert C is not None

    def test_lang_from_lang_module(self):
        """REFAC-02 分割後 pagefolio.lang モジュールから LANG を import できる"""
        from pagefolio.lang import LANG

        assert "ja" in LANG

    def test_themes_from_themes_module(self):
        """REFAC-02 分割後 pagefolio.themes から THEMES/C を import できる"""
        from pagefolio.themes import THEMES, C

        assert "dark" in THEMES
        assert isinstance(C, dict)


# =============================================================================
# REFAC-01: dialogs サブパッケージの import パス検証
# =============================================================================


class TestDialogsImports:
    """REFAC-01 — dialogs サブパッケージ分割後の import 検証

    D-08: dialog クラスはインスタンス化せず、シンボル存在のみ確認する。
    """

    def test_dialogs_subpackage_about(self):
        """pagefolio.dialogs から AboutDialog を import できる"""
        from pagefolio.dialogs import AboutDialog

        assert AboutDialog is not None

    def test_dialogs_subpackage_settings(self):
        """pagefolio.dialogs から SettingsDialog を import できる"""
        from pagefolio.dialogs import SettingsDialog

        assert SettingsDialog is not None

    def test_dialogs_subpackage_plugin(self):
        """pagefolio.dialogs から PluginDialog を import できる"""
        from pagefolio.dialogs import PluginDialog

        assert PluginDialog is not None

    def test_dialogs_subpackage_merge_order(self):
        """pagefolio.dialogs から MergeOrderDialog を import できる"""
        from pagefolio.dialogs import MergeOrderDialog

        assert MergeOrderDialog is not None

    def test_dialogs_subpackage_merge_resize(self):
        """pagefolio.dialogs から MergeResizeDialog を import できる"""
        from pagefolio.dialogs import MergeResizeDialog

        assert MergeResizeDialog is not None

    def test_dialogs_subpackage_all(self):
        """pagefolio.dialogs から全ダイアログクラスを一括 import できる"""
        from pagefolio.dialogs import (
            AboutDialog,
            MergeOrderDialog,
            MergeResizeDialog,
            PluginDialog,
            SettingsDialog,
        )

        assert AboutDialog is not None
        assert SettingsDialog is not None
        assert PluginDialog is not None
        assert MergeOrderDialog is not None
        assert MergeResizeDialog is not None

    def test_individual_module_about(self):
        """dialogs.about から AboutDialog を import できる"""
        from pagefolio.dialogs.about import AboutDialog

        assert AboutDialog is not None

    def test_individual_module_settings(self):
        """dialogs.settings から SettingsDialog を import できる"""
        from pagefolio.dialogs.settings import SettingsDialog

        assert SettingsDialog is not None

    def test_individual_module_plugin(self):
        """dialogs.plugin から PluginDialog を import できる"""
        from pagefolio.dialogs.plugin import PluginDialog

        assert PluginDialog is not None

    def test_individual_module_merge(self):
        """dialogs.merge から MergeOrderDialog/MergeResizeDialog を import できる"""
        from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog

        assert MergeOrderDialog is not None
        assert MergeResizeDialog is not None

    def test_individual_module_llm_config(self):
        """dialogs.llm_config から LLMConfigDialog を import できる

        LLMConfigDialog は pagefolio.dialogs 経由でアクセス可能だが、
        pagefolio トップレベルには非公開（RESEARCH §Common Pitfalls 4）。
        """
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        assert LLMConfigDialog is not None

    def test_llm_config_via_dialogs_subpackage(self):
        """pagefolio.dialogs 経由でも LLMConfigDialog を import できる"""
        from pagefolio.dialogs import LLMConfigDialog

        assert LLMConfigDialog is not None


# =============================================================================
# REFAC-01: ocr_providers パッケージ分割後の後方互換 import 検証（D-11）
# =============================================================================


class TestOcrProvidersImports:
    """REFAC-01 — ocr_providers パッケージ分割後の後方互換 import 検証

    D-11 完全再エクスポート契約。現行 monolith `pagefolio/ocr_providers.py`
    に対して今すぐ全緑になり、
    Wave 2 でパッケージ分割された後も緑を維持することが後方互換の契約そのものになる。
    プロバイダクラスはインスタンス化せずシンボル存在のみ確認する（D-08 踏襲）。
    """

    def test_ocr_provider_base_class(self):
        """pagefolio.ocr_providers から OCRProvider（ABC 基底）を import できる"""
        from pagefolio.ocr_providers import OCRProvider

        assert OCRProvider is not None

    def test_allowed_url_schemes(self):
        """pagefolio.ocr_providers から _ALLOWED_URL_SCHEMES を import できる"""
        from pagefolio.ocr_providers import _ALLOWED_URL_SCHEMES

        assert _ALLOWED_URL_SCHEMES is not None

    def test_require_http_scheme_helper(self):
        """pagefolio.ocr_providers から _require_http_scheme を import できる"""
        from pagefolio.ocr_providers import _require_http_scheme

        assert callable(_require_http_scheme)

    def test_ocr_api_key_error(self):
        """pagefolio.ocr_providers から OCRAPIKeyError を import できる"""
        from pagefolio.ocr_providers import OCRAPIKeyError

        assert OCRAPIKeyError is not None

    def test_ocr_retryable_error(self):
        """pagefolio.ocr_providers から OCRRetryableError を import できる"""
        from pagefolio.ocr_providers import OCRRetryableError

        assert OCRRetryableError is not None

    def test_retryable_http_message_helper(self):
        """pagefolio.ocr_providers から _retryable_http_message を import できる"""
        from pagefolio.ocr_providers import _retryable_http_message

        assert callable(_retryable_http_message)

    def test_ocr_context_length_error(self):
        """pagefolio.ocr_providers から OCRContextLengthError を import できる"""
        from pagefolio.ocr_providers import OCRContextLengthError

        assert OCRContextLengthError is not None

    def test_context_error_markers(self):
        """pagefolio.ocr_providers から _CONTEXT_ERROR_MARKERS を import できる"""
        from pagefolio.ocr_providers import _CONTEXT_ERROR_MARKERS

        assert _CONTEXT_ERROR_MARKERS is not None

    def test_parse_retry_after_helper(self):
        """pagefolio.ocr_providers から parse_retry_after を import できる（private）"""
        from pagefolio.ocr_providers import parse_retry_after

        assert callable(parse_retry_after)

    def test_looks_like_context_error_helper(self):
        """looks_like_context_error を import できる（private ヘルパー）"""
        from pagefolio.ocr_providers import looks_like_context_error

        assert callable(looks_like_context_error)

    def test_raise_mapped_http_error_helper(self):
        """_raise_mapped_http_error を import できる（private ヘルパー）"""
        from pagefolio.ocr_providers import _raise_mapped_http_error

        assert callable(_raise_mapped_http_error)

    def test_lmstudio_provider(self):
        """pagefolio.ocr_providers から LMStudioProvider を import できる"""
        from pagefolio.ocr_providers import LMStudioProvider

        assert LMStudioProvider is not None

    def test_claude_provider(self):
        """pagefolio.ocr_providers から ClaudeProvider を import できる"""
        from pagefolio.ocr_providers import ClaudeProvider

        assert ClaudeProvider is not None

    def test_gemini_provider(self):
        """pagefolio.ocr_providers から GeminiProvider を import できる"""
        from pagefolio.ocr_providers import GeminiProvider

        assert GeminiProvider is not None

    def test_detect_tesseract_helper(self):
        """_detect_tesseract を import できる（Pitfall 2 の private ヘルパー）"""
        from pagefolio.ocr_providers import _detect_tesseract

        assert callable(_detect_tesseract)

    def test_tesseract_provider(self):
        """pagefolio.ocr_providers から TesseractProvider を import できる"""
        from pagefolio.ocr_providers import TesseractProvider

        assert TesseractProvider is not None

    def test_ollama_provider(self):
        """pagefolio.ocr_providers から OllamaProvider を import できる"""
        from pagefolio.ocr_providers import OllamaProvider

        assert OllamaProvider is not None

    def test_runpod_provider(self):
        """pagefolio.ocr_providers から RunPodProvider を import できる"""
        from pagefolio.ocr_providers import RunPodProvider

        assert RunPodProvider is not None

    def test_ocr_providers_backward_compat_all(self):
        """全17シンボルを一括 import できる（漏れ検知の一括アサーション）"""
        from pagefolio.ocr_providers import (
            _ALLOWED_URL_SCHEMES,
            _CONTEXT_ERROR_MARKERS,
            ClaudeProvider,
            GeminiProvider,
            LMStudioProvider,
            OCRAPIKeyError,
            OCRContextLengthError,
            OCRProvider,
            OCRRetryableError,
            OllamaProvider,
            RunPodProvider,
            TesseractProvider,
            _detect_tesseract,
            _raise_mapped_http_error,
            _require_http_scheme,
            _retryable_http_message,
            looks_like_context_error,
            parse_retry_after,
        )

        assert OCRProvider is not None
        assert _ALLOWED_URL_SCHEMES is not None
        assert callable(_require_http_scheme)
        assert OCRAPIKeyError is not None
        assert OCRRetryableError is not None
        assert callable(_retryable_http_message)
        assert OCRContextLengthError is not None
        assert _CONTEXT_ERROR_MARKERS is not None
        assert callable(parse_retry_after)
        assert callable(looks_like_context_error)
        assert callable(_raise_mapped_http_error)
        assert LMStudioProvider is not None
        assert ClaudeProvider is not None
        assert GeminiProvider is not None
        assert callable(_detect_tesseract)
        assert TesseractProvider is not None
        assert OllamaProvider is not None
        assert RunPodProvider is not None


# =============================================================================
# REFAC-04: settings 公開 API の import と roundtrip 検証
# =============================================================================


class TestSettingsApiImports:
    """REFAC-04 — settings 公開 setter/getter の import 回帰テスト

    D-04: setter は単純代入のみ（クランプ等のバリデーションなし）。
    roundtrip テスト後は元値（12）に戻して副作用を残さない。
    """

    def test_setter_is_importable(self):
        """set_current_font_size を pagefolio.settings から import できる"""
        from pagefolio.settings import set_current_font_size

        assert callable(set_current_font_size)

    def test_getter_is_importable(self):
        """get_current_font_size を pagefolio.settings から import できる"""
        from pagefolio.settings import get_current_font_size

        assert callable(get_current_font_size)

    def test_setter_getter_roundtrip(self):
        """set_current_font_size(14) 後に get_current_font_size() == 14 となる"""
        from pagefolio.settings import get_current_font_size, set_current_font_size

        set_current_font_size(14)
        assert get_current_font_size() == 14
        set_current_font_size(12)  # 元に戻す（他テストへの副作用を防ぐ）

    def test_setter_via_top_level_package(self):
        """set_current_font_size が pagefolio トップレベルからも import できる"""
        from pagefolio import set_current_font_size

        assert callable(set_current_font_size)

    def test_getter_via_top_level_package(self):
        """get_current_font_size が pagefolio トップレベルからも import できる"""
        from pagefolio import get_current_font_size

        assert callable(get_current_font_size)


# =============================================================================
# pagefolio トップレベルの公開サーフェス存在検証
# =============================================================================


class TestPackageSurface:
    """pagefolio トップレベル公開サーフェスの hasattr 検証

    pagefolio/__init__.py の再エクスポートが全シンボルを公開していることを確認。
    D-07: 列挙漏れがないか実コードと突き合わせること。
    """

    def test_app_symbol(self):
        """PDFEditorApp がトップレベルに存在する"""
        assert hasattr(pagefolio, "PDFEditorApp")

    def test_version_symbol(self):
        """APP_VERSION がトップレベルに存在する"""
        assert hasattr(pagefolio, "APP_VERSION")

    def test_lang_symbol(self):
        """LANG がトップレベルに存在する"""
        assert hasattr(pagefolio, "LANG")

    def test_themes_symbol(self):
        """THEMES がトップレベルに存在する"""
        assert hasattr(pagefolio, "THEMES")

    def test_c_symbol(self):
        """C（実行時テーマ辞書）がトップレベルに存在する"""
        assert hasattr(pagefolio, "C")

    def test_dialogs_symbols(self):
        """ダイアログクラスがトップレベルに存在する"""
        assert hasattr(pagefolio, "AboutDialog")
        assert hasattr(pagefolio, "SettingsDialog")
        assert hasattr(pagefolio, "PluginDialog")
        assert hasattr(pagefolio, "MergeOrderDialog")
        assert hasattr(pagefolio, "MergeResizeDialog")

    def test_plugin_symbols(self):
        """プラグインシステムのシンボルがトップレベルに存在する"""
        assert hasattr(pagefolio, "PluginManager")
        assert hasattr(pagefolio, "PDFEditorPlugin")

    def test_ocr_symbol(self):
        """OCRMixin がトップレベルに存在する"""
        assert hasattr(pagefolio, "OCRMixin")

    def test_settings_util_symbols(self):
        """設定ユーティリティ関数がトップレベルに存在する"""
        assert hasattr(pagefolio, "_load_settings")
        assert hasattr(pagefolio, "_save_settings")
        assert hasattr(pagefolio, "_apply_theme")
        assert hasattr(pagefolio, "_make_font")

    def test_settings_api_symbols(self):
        """REFAC-04 で追加された公開 API がトップレベルに存在する"""
        assert hasattr(pagefolio, "set_current_font_size")
        assert hasattr(pagefolio, "get_current_font_size")
