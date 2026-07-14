# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""プロンプトテンプレート管理の純ロジック層テスト（02-01 Task 1/2・V180-TMPL-01〜05）。

settings.py のテンプレート CRUD ヘルパー（save/get/list/delete/rename/exists）
と、load_custom_prompt/load_summary_prompt の3段解決（外部ファイル > アクティブ
テンプレート > 設定欄）を検証する。test_settings_keyguard.py と同型のスタイル
（Tk/fitz 非依存・_load_settings/_save_settings と同じ関数型 CRUD ヘルパーを
直接呼ぶ）を踏襲する。
"""

import pytest

from pagefolio.settings import (
    _SENSITIVE_KEYS,
    delete_template,
    get_template,
    list_template_names,
    rename_template,
    save_template,
    template_name_exists,
)


class TestSaveTemplate:
    """save_template / get_template の往復・上書き・空名拒否（D-01/D-04）。"""

    def test_save_then_get_roundtrip(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        assert get_template(settings, "A") == {
            "custom_prompt": "c1",
            "summary_prompt": "s1",
        }

    def test_get_unregistered_name_returns_none(self):
        settings = {}
        assert get_template(settings, "not-registered") is None

    def test_save_duplicate_name_overwrites(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        save_template(settings, "A", "c2", "s2")
        assert get_template(settings, "A") == {
            "custom_prompt": "c2",
            "summary_prompt": "s2",
        }

    def test_save_empty_name_raises_value_error(self):
        settings = {}
        with pytest.raises(ValueError):
            save_template(settings, "", "c1", "s1")

    def test_save_whitespace_only_name_raises_value_error(self):
        settings = {}
        with pytest.raises(ValueError):
            save_template(settings, "   ", "c1", "s1")

    def test_save_initializes_prompt_templates_on_uninitialized_settings(self):
        """settings に prompt_templates キーが無くても安全に動く。"""
        settings = {"theme": "dark"}
        save_template(settings, "A", "c1", "s1")
        assert settings["prompt_templates"]["items"]["A"] == {
            "custom_prompt": "c1",
            "summary_prompt": "s1",
        }


class TestListAndSelect:
    """list_template_names の sorted 順・active 切替の settings 反映（V180-TMPL-02）"""

    def test_list_template_names_sorted(self):
        settings = {}
        save_template(settings, "Zebra", "c", "s")
        save_template(settings, "Alpha", "c", "s")
        save_template(settings, "Mid", "c", "s")
        assert list_template_names(settings) == ["Alpha", "Mid", "Zebra"]

    def test_list_template_names_empty_when_none_saved(self):
        settings = {}
        assert list_template_names(settings) == []

    def test_active_switch_reflected_in_settings(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        save_template(settings, "B", "c2", "s2")
        settings["prompt_templates"]["active"] = "A"
        assert settings["prompt_templates"]["active"] == "A"
        settings["prompt_templates"]["active"] = "B"
        assert settings["prompt_templates"]["active"] == "B"

    def test_template_name_exists_true_for_registered(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        assert template_name_exists(settings, "A") is True

    def test_template_name_exists_false_for_unregistered(self):
        settings = {}
        assert template_name_exists(settings, "unregistered") is False

    def test_template_name_exists_false_for_empty_or_whitespace(self):
        settings = {}
        assert template_name_exists(settings, "") is False
        assert template_name_exists(settings, "   ") is False


class TestDeleteRename:
    """delete_template のアクティブ削除禁止（D-03）・rename の重複拒否（D-04）。"""

    def test_delete_removes_template(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        delete_template(settings, "A")
        assert get_template(settings, "A") is None

    def test_delete_unregistered_name_is_noop(self):
        settings = {}
        delete_template(settings, "not-registered")  # 例外なく完了する

    def test_delete_active_template_raises_value_error(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        settings["prompt_templates"]["active"] = "A"
        with pytest.raises(ValueError):
            delete_template(settings, "A")
        # 削除拒否後もテンプレートは残っている
        assert get_template(settings, "A") is not None

    def test_delete_non_active_template_succeeds(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        save_template(settings, "B", "c2", "s2")
        settings["prompt_templates"]["active"] = "A"
        delete_template(settings, "B")
        assert get_template(settings, "B") is None

    def test_rename_normal(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        rename_template(settings, "A", "A2")
        assert get_template(settings, "A") is None
        assert get_template(settings, "A2") == {
            "custom_prompt": "c1",
            "summary_prompt": "s1",
        }

    def test_rename_to_duplicate_raises_value_error(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        save_template(settings, "B", "c2", "s2")
        with pytest.raises(ValueError):
            rename_template(settings, "A", "B")
        # 失敗後も元の状態が維持される
        assert get_template(settings, "A") is not None
        assert get_template(settings, "B") == {
            "custom_prompt": "c2",
            "summary_prompt": "s2",
        }

    def test_rename_to_empty_name_raises_value_error(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        with pytest.raises(ValueError):
            rename_template(settings, "A", "")

    def test_rename_unregistered_old_name_raises_value_error(self):
        settings = {}
        with pytest.raises(ValueError):
            rename_template(settings, "not-registered", "New")

    def test_rename_active_template_follows_new_name(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        settings["prompt_templates"]["active"] = "A"
        rename_template(settings, "A", "A2")
        assert settings["prompt_templates"]["active"] == "A2"

    def test_rename_non_active_template_does_not_change_active(self):
        settings = {}
        save_template(settings, "A", "c1", "s1")
        save_template(settings, "B", "c2", "s2")
        settings["prompt_templates"]["active"] = "A"
        rename_template(settings, "B", "B2")
        assert settings["prompt_templates"]["active"] == "A"


class TestExternalFileSync:
    """外部mdファイル > アクティブテンプレート > 設定欄の3段解決（V180-TMPL-04/05）"""

    # Task 2 で実装する。ここでは Wave 0 の雛形のみ（プレースホルダ）。
    pass


class TestSensitiveKeysNotPolluted:
    """新規キーが _SENSITIVE_KEYS を汚染しないことの検証（prohibition 検証）。"""

    def test_prompt_templates_not_in_sensitive_keys(self):
        assert "prompt_templates" not in _SENSITIVE_KEYS

    def test_ocr_fallback_enabled_not_in_sensitive_keys(self):
        assert "ocr_fallback_enabled" not in _SENSITIVE_KEYS

    def test_ocr_fallback_chain_not_in_sensitive_keys(self):
        assert "ocr_fallback_chain" not in _SENSITIVE_KEYS
