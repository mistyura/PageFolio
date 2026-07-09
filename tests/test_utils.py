"""pagefolio のユーティリティ関数テスト"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# pagefolio モジュールをインポート
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pagefolio
import pagefolio.settings as _settings_mod

# ===== _load_settings / _save_settings =====


class TestLoadSettings:
    """_load_settings のテスト"""

    def test_defaults_when_no_file(self, tmp_path):
        """設定ファイルがない場合はデフォルト値を返す"""
        fake_path = str(tmp_path / "nonexistent.json")
        with patch.object(_settings_mod, "_get_settings_path", return_value=fake_path):
            settings = pagefolio._load_settings()
        assert settings["theme"] == "dark"
        assert settings["font_size"] == 12
        assert settings["lang"] == "ja"

    def test_load_existing_file(self, tmp_settings):
        """既存設定ファイルを正しく読み込む"""
        path, write_fn = tmp_settings
        write_fn({"theme": "light", "font_size": 14, "lang": "en"})
        with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
            settings = pagefolio._load_settings()
        assert settings["theme"] == "light"
        assert settings["font_size"] == 14
        assert settings["lang"] == "en"

    def test_missing_keys_filled_with_defaults(self, tmp_settings):
        """一部のキーがない場合はデフォルトで補完される"""
        path, write_fn = tmp_settings
        write_fn({"theme": "light"})
        with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
            settings = pagefolio._load_settings()
        assert settings["theme"] == "light"
        assert settings["font_size"] == 12  # デフォルト
        assert settings["lang"] == "ja"  # デフォルト

    def test_invalid_json_returns_defaults(self, tmp_settings):
        """不正なJSONの場合はデフォルト値を返す"""
        path, _ = tmp_settings
        path.write_text("{invalid json!!!", encoding="utf-8")
        with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
            settings = pagefolio._load_settings()
        assert settings["theme"] == "dark"
        assert settings["font_size"] == 12


class TestSaveSettings:
    """_save_settings のテスト"""

    def test_save_and_reload(self, tmp_settings):
        """保存した設定が再読み込みで一致する"""
        path, _ = tmp_settings
        data = {"theme": "light", "font_size": 16, "lang": "en"}
        with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
            pagefolio._save_settings(data)
            loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == data

    def test_save_creates_file(self, tmp_path):
        """ファイルがなくても新規作成される"""
        path = tmp_path / "new_settings.json"
        with patch.object(_settings_mod, "_get_settings_path", return_value=str(path)):
            pagefolio._save_settings({"theme": "dark"})
        assert path.exists()


# ===== _resolve_theme / _apply_theme =====


class TestResolveTheme:
    """_resolve_theme のテスト"""

    def test_dark(self):
        assert pagefolio._resolve_theme("dark") == "dark"

    def test_light(self):
        assert pagefolio._resolve_theme("light") == "light"

    def test_unknown_falls_back_to_dark(self):
        assert pagefolio._resolve_theme("invalid") == "dark"
        assert pagefolio._resolve_theme("") == "dark"

    def test_system_resolves_to_dark_or_light(self):
        result = pagefolio._resolve_theme("system")
        assert result in ("dark", "light")


class TestApplyTheme:
    """_apply_theme のテスト"""

    def test_apply_dark(self):
        pagefolio._apply_theme("dark")
        assert pagefolio.C["BG_DARK"] == pagefolio.THEMES["dark"]["BG_DARK"]

    def test_apply_light(self):
        pagefolio._apply_theme("light")
        assert pagefolio.C["BG_DARK"] == pagefolio.THEMES["light"]["BG_DARK"]
        # 元に戻す
        pagefolio._apply_theme("dark")

    def test_apply_invalid_falls_back_to_dark(self):
        pagefolio._apply_theme("nonexistent")
        assert pagefolio.C["BG_DARK"] == pagefolio.THEMES["dark"]["BG_DARK"]


# ===== _make_font =====


class TestMakeFont:
    """_make_font のテスト"""

    def test_default(self):
        result = pagefolio._make_font()
        assert result == ("Segoe UI", 10)

    def test_positive_delta(self):
        result = pagefolio._make_font(delta=2, base_size=12)
        assert result == ("Segoe UI", 14)

    def test_negative_delta(self):
        result = pagefolio._make_font(delta=-2, base_size=12)
        assert result == ("Segoe UI", 10)

    def test_minimum_size_clamp(self):
        """フォントサイズは最小7に制限される"""
        result = pagefolio._make_font(delta=-100, base_size=10)
        assert result == ("Segoe UI", 7)

    def test_with_weight(self):
        result = pagefolio._make_font(delta=0, weight="bold", base_size=12)
        assert result == ("Segoe UI", 12, "bold")

    def test_without_weight(self):
        result = pagefolio._make_font(delta=0, base_size=12)
        assert len(result) == 2  # weight なしは2要素タプル


# ===== PDFEditorApp._parse_page_ranges =====


class TestParsePageRanges:
    """_parse_page_ranges のテスト。
    メソッドは self を使わないが PDFEditorApp のインスタンスメソッドなので、
    最小限のモックオブジェクトを作成してテストする。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        """テスト用の簡易オブジェクト（self のみ必要）"""

        class FakeApp:
            pass

        self.app = FakeApp()
        self.app._parse_page_ranges = pagefolio.PDFEditorApp._parse_page_ranges.__get__(
            self.app
        )

    # --- 正常系 ---

    def test_single_page(self):
        """単一ページ指定"""
        result = self.app._parse_page_ranges("3", 10)
        assert result == [(3, 3)]

    def test_page_range(self):
        """ページ範囲指定"""
        result = self.app._parse_page_ranges("1-3", 10)
        assert result == [(1, 3)]

    def test_multiple_ranges(self):
        """複数範囲指定（カンマ区切り）"""
        result = self.app._parse_page_ranges("1-3, 5-8", 10)
        assert result == [(1, 3), (5, 8)]

    def test_mixed_single_and_range(self):
        """単一ページと範囲の混在"""
        result = self.app._parse_page_ranges("1, 3-5, 8", 10)
        assert result == [(1, 1), (3, 5), (8, 8)]

    def test_with_spaces(self):
        """前後にスペースがある場合"""
        result = self.app._parse_page_ranges("  1 - 3 , 5  ", 10)
        assert result == [(1, 3), (5, 5)]

    def test_boundary_first_page(self):
        """最初のページ"""
        result = self.app._parse_page_ranges("1", 5)
        assert result == [(1, 1)]

    def test_boundary_last_page(self):
        """最後のページ"""
        result = self.app._parse_page_ranges("5", 5)
        assert result == [(5, 5)]

    def test_full_range(self):
        """全ページ範囲"""
        result = self.app._parse_page_ranges("1-5", 5)
        assert result == [(1, 5)]

    # --- 異常系 ---

    def test_empty_string(self):
        """空文字列"""
        result = self.app._parse_page_ranges("", 10)
        assert result is None

    def test_whitespace_only(self):
        """空白のみ"""
        result = self.app._parse_page_ranges("   ", 10)
        assert result is None

    def test_page_zero(self):
        """0ページ（範囲外）"""
        result = self.app._parse_page_ranges("0", 10)
        assert result is None

    def test_page_exceeds_max(self):
        """最大ページを超える"""
        result = self.app._parse_page_ranges("11", 10)
        assert result is None

    def test_reversed_range(self):
        """逆範囲（start > end）"""
        result = self.app._parse_page_ranges("5-3", 10)
        assert result is None

    def test_invalid_format(self):
        """不正なフォーマット"""
        result = self.app._parse_page_ranges("abc", 10)
        assert result is None

    def test_negative_page(self):
        """負のページ番号"""
        result = self.app._parse_page_ranges("-1", 10)
        # "-1" は range 解釈され "" と "1" に split → "" は int() で ValueError → None
        assert result is None

    def test_range_exceeds_max(self):
        """範囲の末尾が最大を超える"""
        result = self.app._parse_page_ranges("1-100", 10)
        assert result is None


# ===== _get_settings_path =====


class TestGetSettingsPath:
    """_get_settings_path の分岐テスト"""

    def test_frozen_mode(self, monkeypatch):
        """PyInstaller (frozen) モードでは sys.executable のディレクトリを基準にする"""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", os.path.join("/fake", "dir", "app.exe"))
        result = _settings_mod._get_settings_path()
        expected_dir = os.path.join("/fake", "dir")
        assert os.path.dirname(result) == expected_dir
        assert os.path.basename(result) == _settings_mod.SETTINGS_FILE

    def test_normal_mode(self, monkeypatch):
        """通常実行ではパッケージ親ディレクトリを基準にする"""
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = _settings_mod._get_settings_path()
        # pagefolio/ パッケージの親 + SETTINGS_FILE
        expected_base = os.path.dirname(
            os.path.dirname(os.path.abspath(_settings_mod.__file__))
        )
        assert result == os.path.join(expected_base, _settings_mod.SETTINGS_FILE)


# ===== 外部プロンプトファイル読込（V174-2） =====


class TestPromptFileLoading:
    """load_prompt_file / load_custom_prompt / load_summary_prompt のテスト。

    実行ファイルと同じ階層の ocr_custom_prompt.md / ocr_summary_prompt.md を
    設定欄より優先して読み込む（無ければ設定欄へフォールバック）。
    """

    def _use_base_dir(self, monkeypatch, tmp_path):
        """_get_base_dir を tmp_path に差し替える（実ファイル非依存化）。"""
        monkeypatch.setattr(_settings_mod, "_get_base_dir", lambda: str(tmp_path))

    def test_load_prompt_file_missing_returns_empty(self, monkeypatch, tmp_path):
        """ファイルが存在しないときは空文字を返す"""
        self._use_base_dir(monkeypatch, tmp_path)
        assert _settings_mod.load_prompt_file("ocr_custom_prompt.md") == ""

    def test_load_prompt_file_reads_and_strips(self, monkeypatch, tmp_path):
        """UTF-8 で読み込み、前後の空白・改行を除去して返す"""
        self._use_base_dir(monkeypatch, tmp_path)
        (tmp_path / "ocr_custom_prompt.md").write_text(
            "\n巨大なカスタムプロンプト\n\n", encoding="utf-8"
        )
        result = _settings_mod.load_prompt_file("ocr_custom_prompt.md")
        assert result == "巨大なカスタムプロンプト"

    def test_load_prompt_file_tolerates_bom(self, monkeypatch, tmp_path):
        """Windows エディタの BOM 付き UTF-8 でも BOM を除去して読む"""
        self._use_base_dir(monkeypatch, tmp_path)
        (tmp_path / "ocr_custom_prompt.md").write_bytes(
            b"\xef\xbb\xbf" + "プロンプト本文".encode("utf-8")
        )
        result = _settings_mod.load_prompt_file("ocr_custom_prompt.md")
        assert result == "プロンプト本文"

    def test_custom_prompt_file_overrides_settings(self, monkeypatch, tmp_path):
        """md ファイルが存在すれば設定欄の値より優先される"""
        self._use_base_dir(monkeypatch, tmp_path)
        (tmp_path / "ocr_custom_prompt.md").write_text(
            "ファイル側プロンプト", encoding="utf-8"
        )
        settings = {"ocr_custom_prompt": "設定欄プロンプト"}
        assert _settings_mod.load_custom_prompt(settings) == "ファイル側プロンプト"

    def test_custom_prompt_falls_back_to_settings(self, monkeypatch, tmp_path):
        """md ファイルが無ければ設定欄の値へフォールバックする"""
        self._use_base_dir(monkeypatch, tmp_path)
        settings = {"ocr_custom_prompt": "設定欄プロンプト"}
        assert _settings_mod.load_custom_prompt(settings) == "設定欄プロンプト"

    def test_custom_prompt_empty_file_falls_back(self, monkeypatch, tmp_path):
        """空（空白のみ）の md ファイルはフォールバック扱いになる"""
        self._use_base_dir(monkeypatch, tmp_path)
        (tmp_path / "ocr_custom_prompt.md").write_text("   \n", encoding="utf-8")
        settings = {"ocr_custom_prompt": "設定欄プロンプト"}
        assert _settings_mod.load_custom_prompt(settings) == "設定欄プロンプト"

    def test_summary_prompt_file_overrides_settings(self, monkeypatch, tmp_path):
        """サマリ側も同型: md ファイルが設定欄より優先される"""
        self._use_base_dir(monkeypatch, tmp_path)
        (tmp_path / "ocr_summary_prompt.md").write_text(
            "ファイル側サマリ指示", encoding="utf-8"
        )
        settings = {"ocr_summary_prompt": "設定欄サマリ指示"}
        assert _settings_mod.load_summary_prompt(settings) == "ファイル側サマリ指示"

    def test_summary_prompt_falls_back_to_settings(self, monkeypatch, tmp_path):
        """サマリ側も md ファイルが無ければ設定欄へフォールバックする"""
        self._use_base_dir(monkeypatch, tmp_path)
        settings = {"ocr_summary_prompt": "設定欄サマリ指示"}
        assert _settings_mod.load_summary_prompt(settings) == "設定欄サマリ指示"

    def test_filenames_match_constants(self):
        """読込対象ファイル名が constants の定数と一致している"""
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        assert CUSTOM_PROMPT_FILE == "ocr_custom_prompt.md"
        assert SUMMARY_PROMPT_FILE == "ocr_summary_prompt.md"


# ===== _save_settings 例外パス =====


class TestSaveSettingsError:
    """_save_settings の例外パステスト"""

    def test_save_to_invalid_path(self):
        """存在しないディレクトリへの保存は例外を投げずに return する"""
        invalid_path = os.path.join(
            "/nonexistent_dir_xyz", "sub", "pagefolio_settings.json"
        )
        with patch.object(
            _settings_mod, "_get_settings_path", return_value=invalid_path
        ):
            # 例外が raise されないことを確認（except 句でキャッチされる）
            _settings_mod._save_settings({"theme": "dark"})


# ===== _detect_system_theme 例外パス =====


class TestDetectSystemThemeError:
    """_detect_system_theme の例外パステスト"""

    def test_winreg_import_error(self):
        """winreg のインポートが失敗した場合 'dark' を返す"""
        # winreg がローカル import なので sys.modules に壊れたモジュールを注入
        broken = MagicMock()
        broken.OpenKey = MagicMock(side_effect=OSError("mocked"))
        with patch.dict("sys.modules", {"winreg": broken}):
            result = _settings_mod._detect_system_theme()
        assert result == "dark"
