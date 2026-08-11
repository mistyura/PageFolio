# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio.ocr_providers.catalog の契約・独立性制約テスト（V190-CAT-01/02）"""

import ast
import dataclasses
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestCatalogContents:
    """PROVIDERS の内容が既存コードの現行挙動と一致することを固定する"""

    def test_all_eight_keys_present(self):
        """PROVIDERS が既存5プロバイダ+off+tesseract+openai の8キーを持つ"""
        from pagefolio.ocr_providers import catalog

        assert set(catalog.PROVIDERS) == {
            "off",
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
            "openai",
        }

    def test_provider_names_matches_sections_base_providers_plus_openai(self):
        """provider_names() が sections.py:_base_providers の現行順+openaiと一致する"""
        from pagefolio.ocr_providers import catalog

        expected = [
            "off",
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
            "openai",
        ]
        assert catalog.provider_names() == expected

    def test_provider_names_exclude_off(self):
        """provider_names(include_off=False) は off を含まない"""
        from pagefolio.ocr_providers import catalog

        assert "off" not in catalog.provider_names(include_off=False)

    def test_fallback_candidate_names_matches_sections_base_fallback_plus_openai(self):
        """fallback_candidate_names() が sections.py:_base_fallback_providers
        の現行6件（off を含まない）+ openai と一致する"""
        from pagefolio.ocr_providers import catalog

        expected = [
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
            "openai",
        ]
        assert catalog.fallback_candidate_names() == expected


class TestProviderMetaFieldContract:
    """ProviderMeta のフィールド型契約とアクセサ戻り型表を機械保証する

    レビュー MEDIUM-7 の反映。
    """

    EXPECTED_FIELDS = [
        "name",
        "display_name_key",
        "is_cloud",
        "model_setting_key",
        "default_model",
        "host",
        "fallback_eligible",
        "api_key_missing_lang_key",
    ]

    def test_field_names_and_order_match_plan(self):
        """dataclasses.fields(ProviderMeta) が計画のフィールド型表と同じ名前・順序"""
        from pagefolio.ocr_providers.catalog import ProviderMeta

        names = [f.name for f in dataclasses.fields(ProviderMeta)]
        assert names == self.EXPECTED_FIELDS

    def test_nullable_fields_have_at_least_one_none_entry(self):
        """str | None 宣言の5フィールドが実際に None を取るエントリを最低1件持つ"""
        from pagefolio.ocr_providers import catalog

        nullable_fields = [
            "display_name_key",
            "model_setting_key",
            "default_model",
            "host",
            "api_key_missing_lang_key",
        ]
        for field in nullable_fields:
            has_none = any(
                getattr(meta, field) is None for meta in catalog.PROVIDERS.values()
            )
            assert has_none, f"{field} に None を取るエントリが1件も無い"

    def test_bool_fields_are_bool_for_all_entries(self):
        """bool 宣言の2フィールドが全エントリで bool 型である"""
        from pagefolio.ocr_providers import catalog

        for meta in catalog.PROVIDERS.values():
            assert isinstance(meta.is_cloud, bool)
            assert isinstance(meta.fallback_eligible, bool)

    def test_default_model_for_and_host_for_always_return_str(self):
        """default_model_for / host_for は未登録名でも必ず str を返す"""
        from pagefolio.ocr_providers import catalog

        assert isinstance(catalog.default_model_for("unknown-plugin"), str)
        assert isinstance(catalog.host_for("unknown-plugin", {}), str)
        assert isinstance(catalog.default_model_for("lmstudio"), str)
        assert isinstance(catalog.host_for("lmstudio", {}), str)

    def test_optional_accessors_return_none_for_unknown_name(self):
        """display_name_key_for/model_setting_key_for/api_key_missing_lang_key_for
        は未登録名で None を返す"""
        from pagefolio.ocr_providers import catalog

        assert catalog.display_name_key_for("unknown-plugin") is None
        assert catalog.model_setting_key_for("unknown-plugin") is None
        assert catalog.api_key_missing_lang_key_for("unknown-plugin") is None


class TestCatalogDefaultModelMatchesProvider:
    """D-05 の機械保証: default_model_for が対応 Provider の RECOMMENDED_MODELS
    に含まれることを catalog を介さず Provider を直接 import して突き合わせる"""

    def test_claude_default_model_in_recommended(self):
        from pagefolio.ocr_providers import ClaudeProvider, catalog

        assert catalog.default_model_for("claude") in ClaudeProvider.RECOMMENDED_MODELS

    def test_gemini_default_model_in_recommended(self):
        from pagefolio.ocr_providers import GeminiProvider, catalog

        assert catalog.default_model_for("gemini") in GeminiProvider.RECOMMENDED_MODELS

    def test_openai_default_model_in_recommended(self):
        from pagefolio.ocr_providers import OpenAIProvider, catalog

        assert catalog.default_model_for("openai") in OpenAIProvider.RECOMMENDED_MODELS


class TestCatalogRegistryIndependence:
    """V190-CAT-02: registry.py の独立性制約と catalog の一方向依存を AST で固定する"""

    def test_registry_imports_only_os(self):
        """registry.py の import 文が os 以外を含まない（特に pagefolio 系が0件）"""
        source = (REPO_ROOT / "pagefolio" / "ocr_providers" / "registry.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        mods = [
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        ]
        mods += [
            n.module
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        ]
        assert mods == ["os"], mods
        pagefolio_mods = [m for m in mods if m.startswith("pagefolio")]
        assert pagefolio_mods == []

    def test_catalog_internal_import_is_registry_only(self):
        """catalog.py の内部 import が pagefolio.ocr_providers.registry 1件のみ"""
        source = (REPO_ROOT / "pagefolio" / "ocr_providers" / "catalog.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        mods = [
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        ]
        mods += [
            n.module
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        ]
        inner = [m for m in mods if m.startswith("pagefolio")]
        assert inner == ["pagefolio.ocr_providers.registry"], inner

    def test_no_circular_import_settings_then_catalog(self):
        """import pagefolio.settings -> import pagefolio.ocr_providers.catalog の順で
        新規サブプロセスが正常終了する（循環 import が無いことの確認）"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import pagefolio.settings; import pagefolio.ocr_providers.catalog",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_no_circular_import_catalog_then_settings(self):
        """逆順（catalog -> settings）でも新規サブプロセスが正常終了する"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import pagefolio.ocr_providers.catalog; import pagefolio.settings",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


class TestCatalogRegistryParity:
    """assumption-delta の不変条件テスト: registry と catalog の対応関係を固定する"""

    def test_all_env_key_providers_registered_and_cloud(self):
        """PROVIDER_ENV_KEYS の全キーが catalog.PROVIDERS に存在し is_cloud=True"""
        from pagefolio.ocr_providers import catalog
        from pagefolio.ocr_providers.registry import PROVIDER_ENV_KEYS

        for name in PROVIDER_ENV_KEYS:
            assert name in catalog.PROVIDERS, f"{name} が catalog.PROVIDERS に無い"
            assert catalog.PROVIDERS[name].is_cloud is True, (
                f"{name} は環境変数を持つのに is_cloud=False"
            )

    def test_all_provider_meta_fields_resolvable(self):
        """全 ProviderMeta エントリの8フィールドすべてが属性として解決できる"""
        from pagefolio.ocr_providers import catalog
        from pagefolio.ocr_providers.catalog import ProviderMeta

        fields = [f.name for f in dataclasses.fields(ProviderMeta)]
        for meta in catalog.PROVIDERS.values():
            for field in fields:
                # AttributeError が出ないことのみ確認する（値の妥当性は他が担当）
                getattr(meta, field)


class TestCatalogSensitiveKeyGuard:
    """_save_settings が openai_api_key を settings.json へ書き出さないことを検証する
    （既存 TestSaveSettingsKeyGuard の claude/gemini ケースと同型）"""

    def test_openai_api_key_not_written_to_file(self, tmp_path, monkeypatch):
        from pagefolio.settings import _save_settings

        settings_path = tmp_path / "test_settings.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "ocr_provider": "openai",
            "openai_api_key": "sk-openai-secret-should-not-appear",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "openai_api_key" not in raw, (
            "openai_api_key が JSON ファイルに書き込まれた（V190-OAI-02 違反）"
        )
        assert "sk-openai-secret-should-not-appear" not in raw

    def test_openai_api_key_env_variant_not_written_to_file(
        self, tmp_path, monkeypatch
    ):
        from pagefolio.settings import _save_settings

        settings_path = tmp_path / "test_settings2.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {
            "theme": "dark",
            "OPENAI_API_KEY": "sk-openai-env-secret",
        }
        _save_settings(settings)

        raw = settings_path.read_text(encoding="utf-8")
        assert "OPENAI_API_KEY" not in raw
        assert "sk-openai-env-secret" not in raw

    def test_openai_model_non_sensitive_key_is_persisted(self, tmp_path, monkeypatch):
        """非機密キー openai_model は通常どおり永続化される（過剰フィルタでない確認）"""
        from pagefolio.settings import _save_settings

        settings_path = tmp_path / "test_settings3.json"
        monkeypatch.setattr(
            "pagefolio.settings._get_settings_path",
            lambda: str(settings_path),
        )

        settings = {"theme": "dark", "openai_model": "gpt-5.1"}
        _save_settings(settings)

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data.get("openai_model") == "gpt-5.1"
