# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""_save_settings の機密キー非永続化ガードテスト（成功基準1）"""

import json
import os

import pytest

from pagefolio.settings import _SENSITIVE_KEYS, _load_settings, _save_settings


class TestSensitiveKeysConstant:
    """_SENSITIVE_KEYS 定数の構成テスト"""

    def test_sensitive_keys_exists(self):
        """_SENSITIVE_KEYS が set として存在する"""
        assert isinstance(_SENSITIVE_KEYS, set)

    def test_sensitive_keys_contains_claude(self):
        """claude_api_key が含まれる"""
        assert "claude_api_key" in _SENSITIVE_KEYS

    def test_sensitive_keys_contains_anthropic(self):
        """anthropic_api_key が含まれる"""
        assert "anthropic_api_key" in _SENSITIVE_KEYS

    def test_sensitive_keys_contains_gemini(self):
        """gemini_api_key が含まれる"""
        assert "gemini_api_key" in _SENSITIVE_KEYS

    def test_sensitive_keys_contains_api_key(self):
        """汎用 api_key が含まれる"""
        assert "api_key" in _SENSITIVE_KEYS


class TestSaveSettingsKeyGuard:
    """_save_settings の機密キーガードテスト（成功基準1）"""

    def test_claude_api_key_not_written_to_file(self, tmp_path, monkeypatch):
        """claude_api_key を含む settings を保存しても JSON ファイルに現れない"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "lang": "ja",
            "claude_api_key": "sk-ant-secret-should-not-appear",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "claude_api_key" not in raw, "claude_api_key が JSON ファイルに書き込まれた（成功基準1 違反）"
        assert "sk-ant-secret-should-not-appear" not in raw, "APIキー値が JSON ファイルに書き込まれた"

    def test_anthropic_api_key_not_written_to_file(self, tmp_path, monkeypatch):
        """anthropic_api_key を含む settings を保存しても JSON ファイルに現れない"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "anthropic_api_key": "sk-ant-another-secret",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "anthropic_api_key" not in raw
        assert "sk-ant-another-secret" not in raw

    def test_gemini_api_key_not_written_to_file(self, tmp_path, monkeypatch):
        """gemini_api_key を含む settings を保存しても JSON ファイルに現れない"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "gemini_api_key": "AIza-gemini-secret",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "gemini_api_key" not in raw
        assert "AIza-gemini-secret" not in raw

    def test_api_key_not_written_to_file(self, tmp_path, monkeypatch):
        """汎用 api_key を含む settings を保存しても JSON ファイルに現れない"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "api_key": "generic-api-key-secret",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "api_key" not in raw
        assert "generic-api-key-secret" not in raw

    def test_non_sensitive_keys_are_saved_normally(self, tmp_path, monkeypatch):
        """機密キー以外（theme / ocr_provider 等）は通常どおり保存される"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "lang": "ja",
            "ocr_provider": "claude",
            "claude_model": "claude-sonnet-4-6",
        }
        _save_settings(settings)

        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved["theme"] == "dark"
        assert saved["lang"] == "ja"
        assert saved["ocr_provider"] == "claude"
        assert saved["claude_model"] == "claude-sonnet-4-6"

    def test_input_dict_not_mutated(self, tmp_path, monkeypatch):
        """_save_settings への入力 dict 自体は破壊的変更されない"""
        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "claude_api_key": "should-remain-in-original-dict",
        }
        original_keys = set(settings.keys())
        original_value = settings["claude_api_key"]

        _save_settings(settings)

        # 元の dict は変更されていない
        assert set(settings.keys()) == original_keys, "入力 dict のキーが変更された（破壊的変更）"
        assert settings["claude_api_key"] == original_value, "入力 dict の値が変更された"


class TestLoadSettingsDefaults:
    """_load_settings のデフォルト値テスト"""

    def test_claude_model_default(self, tmp_path, monkeypatch):
        """_load_settings() の戻り値に claude_model == 'claude-sonnet-4-6' が含まれる"""
        settings_path = tmp_path / "no_settings.json"  # 存在しないパス
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        result = _load_settings()
        assert "claude_model" in result, "claude_model が _load_settings の戻り値に含まれない"
        assert result["claude_model"] == "claude-sonnet-4-6"

    def test_ocr_effort_default(self, tmp_path, monkeypatch):
        """_load_settings() の戻り値に ocr_effort == 'low' が含まれる"""
        settings_path = tmp_path / "no_settings.json"  # 存在しないパス
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        result = _load_settings()
        assert "ocr_effort" in result, "ocr_effort が _load_settings の戻り値に含まれない"
        assert result["ocr_effort"] == "low"

    def test_load_with_existing_file_preserves_defaults(self, tmp_path, monkeypatch):
        """既存設定ファイルにないキーはデフォルト値で補完される"""
        settings_path = tmp_path / "partial_settings.json"
        settings_path.write_text(
            json.dumps({"theme": "light", "lang": "en"}), encoding="utf-8"
        )
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        result = _load_settings()
        assert result["theme"] == "light"  # ファイルの値を優先
        assert result["claude_model"] == "claude-sonnet-4-6"  # デフォルト補完
        assert result["ocr_effort"] == "low"  # デフォルト補完
