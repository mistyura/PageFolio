"""PluginManager のテスト"""

import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pagefolio
import pagefolio.plugins as _plugins_mod

# ===== PluginManager 基本操作 =====


class TestPluginManagerInit:
    """PluginManager の初期化テスト"""

    def test_init_empty(self):
        """初期状態ではプラグインが空"""
        pm = pagefolio.PluginManager()
        assert pm.plugins == {}
        assert pm.all_plugins == {}

    def test_disabled_set_empty(self):
        """初期状態では無効化セットが空"""
        pm = pagefolio.PluginManager()
        assert pm.get_disabled_ids() == []


class TestPluginDiscovery:
    """プラグインの検出テスト"""

    def test_discover_from_directory(self, tmp_path, monkeypatch):
        """プラグインディレクトリからファイルを検出する"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        (plugins_dir / "my_plugin.py").write_text("# dummy", encoding="utf-8")
        (plugins_dir / "another.py").write_text("# dummy", encoding="utf-8")
        # _ プレフィックスのファイルは除外
        (plugins_dir / "_hidden.py").write_text("# dummy", encoding="utf-8")
        # .py 以外は除外
        (plugins_dir / "readme.txt").write_text("# dummy", encoding="utf-8")

        monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))

        pm = pagefolio.PluginManager()
        found = pm.discover_plugins()
        ids = [pid for pid, _ in found]
        assert "my_plugin" in ids
        assert "another" in ids
        assert "_hidden" not in ids
        assert "readme" not in ids

    def test_discover_empty_directory(self, tmp_path, monkeypatch):
        """空ディレクトリでは空リストを返す"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))

        pm = pagefolio.PluginManager()
        found = pm.discover_plugins()
        assert found == []

    def test_discover_nonexistent_directory(self, tmp_path, monkeypatch):
        """存在しないディレクトリでは空リストを返す"""
        monkeypatch.setattr(
            _plugins_mod, "_get_plugins_dir", lambda: str(tmp_path / "nonexistent")
        )
        pm = pagefolio.PluginManager()
        found = pm.discover_plugins()
        assert found == []


class TestPluginLoadUnload:
    """プラグインの読み込み・アンロードテスト"""

    def _create_plugin_file(self, path, name="TestPlugin"):
        """テスト用プラグインファイルを生成する"""
        code = textwrap.dedent(f"""\
            import pagefolio

            class {name}(pagefolio.PDFEditorPlugin):
                name = "{name}"
                version = "1.0.0"
                description = "Test plugin"
                author = "Test"

                def __init__(self):
                    self.loaded = False
                    self.events = []

                def on_load(self, app):
                    self.loaded = True

                def on_unload(self, app):
                    self.loaded = False

                def on_file_open(self, app, path):
                    self.events.append(("file_open", path))
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_load_plugin(self, tmp_path):
        """プラグインを読み込めるか"""
        plugin_file = self._create_plugin_file(tmp_path / "test_plug.py")

        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("test_plug", str(plugin_file))
        assert instance is not None
        assert instance.name == "TestPlugin"
        assert "test_plug" in pm.all_plugins

    def test_load_plugin_returns_same_instance(self, tmp_path):
        """同じ plugin_id で2回読み込むと同じインスタンスを返す"""
        plugin_file = self._create_plugin_file(tmp_path / "test_plug.py")

        pm = pagefolio.PluginManager()
        inst1 = pm.load_plugin("test_plug", str(plugin_file))
        inst2 = pm.load_plugin("test_plug", str(plugin_file))
        assert inst1 is inst2

    def test_load_plugin_with_no_subclass_returns_none(self, tmp_path):
        """PDFEditorPlugin のサブクラスがないファイルは None を返す"""
        no_class_file = tmp_path / "no_class.py"
        no_class_file.write_text("x = 1\n", encoding="utf-8")

        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("no_class", str(no_class_file))
        assert instance is None

    def test_load_invalid_file_returns_none(self, tmp_path):
        """不正な Python ファイルは None を返す"""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def !!!invalid syntax", encoding="utf-8")

        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("bad", str(bad_file))
        assert instance is None

    def test_unload_plugin(self, tmp_path):
        """プラグインをアンロードできる"""
        plugin_file = self._create_plugin_file(tmp_path / "test_plug.py")

        pm = pagefolio.PluginManager()
        pm.load_plugin("test_plug", str(plugin_file))
        assert "test_plug" in pm.all_plugins

        pm.unload_plugin("test_plug")
        assert "test_plug" not in pm.all_plugins


class TestPluginEnableDisable:
    """プラグインの有効・無効切替テスト"""

    def _create_plugin_file(self, path):
        code = textwrap.dedent("""\
            import pagefolio

            class MyPlugin(pagefolio.PDFEditorPlugin):
                name = "MyPlugin"
                version = "1.0.0"
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_disable_plugin(self, tmp_path):
        """プラグインを無効化"""
        plugin_file = self._create_plugin_file(tmp_path / "my_plug.py")

        pm = pagefolio.PluginManager()
        pm.load_plugin("my_plug", str(plugin_file))
        assert pm.is_enabled("my_plug")

        pm.disable_plugin("my_plug")
        assert not pm.is_enabled("my_plug")
        assert "my_plug" not in pm.plugins  # 有効リストから消える
        assert "my_plug" in pm.all_plugins  # 全リストには残る

    def test_enable_plugin(self, tmp_path):
        """無効化したプラグインを再有効化"""
        plugin_file = self._create_plugin_file(tmp_path / "my_plug.py")

        pm = pagefolio.PluginManager()
        pm.load_plugin("my_plug", str(plugin_file))
        pm.disable_plugin("my_plug")
        assert not pm.is_enabled("my_plug")

        pm.enable_plugin("my_plug")
        assert pm.is_enabled("my_plug")

    def test_disabled_ids(self, tmp_path):
        """get_disabled_ids が無効化されたIDリストを返す"""
        plugin_file = self._create_plugin_file(tmp_path / "my_plug.py")

        pm = pagefolio.PluginManager()
        pm.load_plugin("my_plug", str(plugin_file))
        pm.disable_plugin("my_plug")
        assert "my_plug" in pm.get_disabled_ids()


class TestPluginFireEvent:
    """プラグインイベント発火テスト"""

    def test_fire_event_calls_method(self, tmp_path):
        """fire_event で有効なプラグインのメソッドが呼ばれる"""
        code = textwrap.dedent("""\
            import pagefolio

            class EventPlugin(pagefolio.PDFEditorPlugin):
                name = "EventPlugin"
                version = "1.0.0"

                def __init__(self):
                    self.called = False
                    self.call_args = None

                def on_file_open(self, app, path):
                    self.called = True
                    self.call_args = (app, path)
        """)
        plugin_file = tmp_path / "event_plug.py"
        plugin_file.write_text(code, encoding="utf-8")

        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("event_plug", str(plugin_file))
        pm.fire_event("on_file_open", None, "/test/path.pdf")

        assert instance.called
        assert instance.call_args == (None, "/test/path.pdf")

    def test_fire_event_skips_disabled(self, tmp_path):
        """無効化されたプラグインはイベントが呼ばれない"""
        code = textwrap.dedent("""\
            import pagefolio

            class SkipPlugin(pagefolio.PDFEditorPlugin):
                name = "SkipPlugin"
                version = "1.0.0"

                def __init__(self):
                    self.called = False

                def on_file_open(self, app, path):
                    self.called = True
        """)
        plugin_file = tmp_path / "skip_plug.py"
        plugin_file.write_text(code, encoding="utf-8")

        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("skip_plug", str(plugin_file))
        pm.disable_plugin("skip_plug")
        pm.fire_event("on_file_open", None, "/test.pdf")

        assert not instance.called

    def test_fire_event_nonexistent_method_is_safe(self, tmp_path):
        """存在しないイベントメソッドでもエラーにならない"""
        code = textwrap.dedent("""\
            import pagefolio

            class SafePlugin(pagefolio.PDFEditorPlugin):
                name = "SafePlugin"
                version = "1.0.0"
        """)
        plugin_file = tmp_path / "safe_plug.py"
        plugin_file.write_text(code, encoding="utf-8")

        pm = pagefolio.PluginManager()
        pm.load_plugin("safe_plug", str(plugin_file))
        # 存在しないイベントでもエラーなし
        pm.fire_event("on_nonexistent_event", None)


class TestLoadAll:
    """load_all のテスト"""

    def test_load_all_with_disabled(self, tmp_path, monkeypatch):
        """load_all で disabled_ids を指定するとそのプラグインが無効化される"""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        for name in ["alpha", "beta"]:
            code = textwrap.dedent(f"""\
                import pagefolio

                class {name.capitalize()}Plugin(pagefolio.PDFEditorPlugin):
                    name = "{name}"
                    version = "1.0.0"
            """)
            (plugins_dir / f"{name}.py").write_text(code, encoding="utf-8")

        monkeypatch.setattr(_plugins_mod, "_get_plugins_dir", lambda: str(plugins_dir))

        pm = pagefolio.PluginManager()
        pm.load_all(disabled_ids=["beta"])

        assert pm.is_enabled("alpha")
        assert not pm.is_enabled("beta")
        assert "alpha" in pm.plugins
        assert "beta" not in pm.plugins
        assert "beta" in pm.all_plugins


# ===== _get_plugins_dir テスト =====


class TestGetPluginsDir:
    """_get_plugins_dir の分岐テスト"""

    def test_frozen_mode(self, monkeypatch):
        """frozen モード（exe 実行時）では sys.executable のディレクトリを基準にする"""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", os.path.join("/path", "to", "app.exe"))
        result = _plugins_mod._get_plugins_dir()
        expected = os.path.join("/path", "to", "plugins")
        assert result == expected

    def test_normal_mode(self, monkeypatch):
        """通常モード（スクリプト実行時）ではプロジェクトルートを基準にする"""
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = _plugins_mod._get_plugins_dir()
        # pagefolio/ の親ディレクトリ + "plugins"
        expected_base = os.path.dirname(
            os.path.dirname(os.path.abspath(_plugins_mod.__file__))
        )
        expected = os.path.join(expected_base, "plugins")
        assert result == expected


# ===== PDFEditorPlugin 基底クラス全メソッドテスト =====


class TestPDFEditorPluginBase:
    """PDFEditorPlugin 基底クラスの全メソッドが呼び出し可能で例外を投げないことを確認"""

    @pytest.mark.parametrize(
        "method_name, args",
        [
            ("on_load", ("app",)),
            ("on_unload", ("app",)),
            ("on_file_open", ("app", "/path.pdf")),
            ("on_file_save", ("app", "/path.pdf")),
            ("on_page_rotate", ("app", [0], 90)),
            ("on_page_delete", ("app", [0])),
            ("on_page_crop", ("app", 0)),
            ("on_page_change", ("app", 0)),
            ("on_insert", ("app", ["/a.pdf"], 0)),
            ("on_merge", ("app", ["/a.pdf"])),
            ("build_ui", ("app", "parent")),
        ],
    )
    def test_base_method_callable(self, method_name, args):
        """基底メソッド {method_name} が呼び出し可能で None を返す"""
        plugin = pagefolio.PDFEditorPlugin()
        method = getattr(plugin, method_name)
        result = method(*args)
        assert result is None


# ===== app 引数付きライフサイクルテスト =====


class TestPluginLifecycleWithApp:
    """load/unload/enable/disable を app 引数付きで呼んだ場合のテスト"""

    def _create_lifecycle_plugin(self, path):
        """on_load/on_unload でフラグを切り替えるプラグインファイルを生成"""
        code = textwrap.dedent("""\
            import pagefolio

            class LifecyclePlugin(pagefolio.PDFEditorPlugin):
                name = "LifecyclePlugin"
                version = "1.0.0"

                def __init__(self):
                    self.loaded = False
                    self.unloaded = False

                def on_load(self, app):
                    self.loaded = True

                def on_unload(self, app):
                    self.unloaded = True
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_load_plugin_with_app(self, tmp_path):
        """app 引数付きで load_plugin すると on_load(app) が呼ばれる"""
        plugin_file = self._create_lifecycle_plugin(tmp_path / "lc_plug.py")
        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("lc_plug", str(plugin_file), app="mock_app")
        assert instance.loaded is True

    def test_load_plugin_with_app_disabled(self, tmp_path):
        """disabled なプラグインは app 付き load でも on_load が呼ばれない"""
        plugin_file = self._create_lifecycle_plugin(tmp_path / "lc_plug.py")
        pm = pagefolio.PluginManager()
        pm._disabled.add("lc_plug")
        instance = pm.load_plugin("lc_plug", str(plugin_file), app="mock_app")
        assert instance.loaded is False

    def test_unload_plugin_with_app(self, tmp_path):
        """app 引数付きで unload_plugin すると on_unload(app) が呼ばれる"""
        plugin_file = self._create_lifecycle_plugin(tmp_path / "lc_plug.py")
        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("lc_plug", str(plugin_file))
        pm.unload_plugin("lc_plug", app="mock_app")
        assert instance.unloaded is True

    def test_enable_plugin_with_app(self, tmp_path):
        """disable → enable(app) で on_load(app) が呼ばれる"""
        plugin_file = self._create_lifecycle_plugin(tmp_path / "lc_plug.py")
        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("lc_plug", str(plugin_file))
        pm.disable_plugin("lc_plug")
        assert instance.loaded is False  # disable では loaded 不変
        instance.loaded = False  # 明示的にリセット
        pm.enable_plugin("lc_plug", app="mock_app")
        assert instance.loaded is True

    def test_disable_plugin_with_app(self, tmp_path):
        """disable(app) で on_unload(app) が呼ばれる"""
        plugin_file = self._create_lifecycle_plugin(tmp_path / "lc_plug.py")
        pm = pagefolio.PluginManager()
        instance = pm.load_plugin("lc_plug", str(plugin_file))
        pm.disable_plugin("lc_plug", app="mock_app")
        assert instance.unloaded is True


# ===== fire_event 例外ハンドリングテスト =====


class TestFireEventException:
    """fire_event 内で例外が発生した場合のテスト"""

    def _create_error_plugin(self, path, class_name="ErrorPlugin"):
        """イベントハンドラが例外を投げるプラグインファイルを生成"""
        code = textwrap.dedent(f"""\
            import pagefolio

            class {class_name}(pagefolio.PDFEditorPlugin):
                name = "{class_name}"
                version = "1.0.0"

                def on_file_open(self, app, path):
                    raise RuntimeError("Test error from {class_name}")
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def _create_tracking_plugin(self, path, class_name="TrackingPlugin"):
        """呼び出しを記録するプラグインファイルを生成"""
        code = textwrap.dedent(f"""\
            import pagefolio

            class {class_name}(pagefolio.PDFEditorPlugin):
                name = "{class_name}"
                version = "1.0.0"

                def __init__(self):
                    self.called = False

                def on_file_open(self, app, path):
                    self.called = True
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_fire_event_exception_caught(self, tmp_path):
        """プラグインが例外を投げても fire_event は正常に完了する"""
        error_file = self._create_error_plugin(tmp_path / "error_plug.py")
        pm = pagefolio.PluginManager()
        pm.load_plugin("error_plug", str(error_file))
        # 例外が飲み込まれて正常に return する
        pm.fire_event("on_file_open", None, "/test.pdf")

    def test_fire_event_exception_other_plugins_still_called(self, tmp_path):
        """例外プラグインの後の別プラグインも正常に呼ばれる"""
        error_file = self._create_error_plugin(tmp_path / "error_plug.py")
        tracking_file = self._create_tracking_plugin(tmp_path / "tracking_plug.py")

        pm = pagefolio.PluginManager()
        pm.load_plugin("error_plug", str(error_file))
        tracking = pm.load_plugin("tracking_plug", str(tracking_file))

        pm.fire_event("on_file_open", None, "/test.pdf")
        assert tracking.called is True


# ===== ライフサイクル例外ハンドリングテスト =====


class TestLifecycleExceptionHandling:
    """unload/enable/disable 内の例外ハンドリングテスト"""

    def _create_error_lifecycle_plugin(self, path):
        """on_load/on_unload が例外を投げるプラグインを生成"""
        code = textwrap.dedent("""\
            import pagefolio

            class ErrorLifecyclePlugin(pagefolio.PDFEditorPlugin):
                name = "ErrorLifecyclePlugin"
                version = "1.0.0"

                def on_load(self, app):
                    raise RuntimeError("on_load error")

                def on_unload(self, app):
                    raise RuntimeError("on_unload error")
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_unload_exception_caught(self, tmp_path):
        """unload 時に on_unload が例外を投げてもクラッシュしない"""
        plugin_file = self._create_error_lifecycle_plugin(tmp_path / "err_lc.py")
        pm = pagefolio.PluginManager()
        pm.load_plugin("err_lc", str(plugin_file))
        # app 付き unload → on_unload が例外 → 飲み込まれる
        pm.unload_plugin("err_lc", app="mock_app")
        assert "err_lc" not in pm.all_plugins

    def test_enable_exception_caught(self, tmp_path):
        """enable 時に on_load が例外を投げてもクラッシュしない"""
        plugin_file = self._create_error_lifecycle_plugin(tmp_path / "err_lc.py")
        pm = pagefolio.PluginManager()
        pm.load_plugin("err_lc", str(plugin_file))
        pm.disable_plugin("err_lc")
        # app 付き enable → on_load が例外 → 飲み込まれる
        pm.enable_plugin("err_lc", app="mock_app")
        assert pm.is_enabled("err_lc")

    def test_disable_exception_caught(self, tmp_path):
        """disable 時に on_unload が例外を投げてもクラッシュしない"""
        plugin_file = self._create_error_lifecycle_plugin(tmp_path / "err_lc.py")
        pm = pagefolio.PluginManager()
        pm.load_plugin("err_lc", str(plugin_file))
        # app 付き disable → on_unload が例外 → 飲み込まれる
        pm.disable_plugin("err_lc", app="mock_app")
        assert not pm.is_enabled("err_lc")


# ===== Phase 7: PluginManager._provider_registry =====


class TestPluginManagerProviderRegistry:
    """PluginManager.register_ocr_provider の動作を検証する（OCR-EXT-02）"""

    def test_initial_registry_is_empty(self):
        """初期状態では _provider_registry が空辞書であること"""
        pm = pagefolio.PluginManager()
        assert pm._provider_registry == {}

    def test_register_valid_provider(self):
        """OCRProvider サブクラスの登録が成功すること"""
        from pagefolio.ocr_providers import OCRProvider

        class DummyProvider(OCRProvider):
            def ocr_image(self, b64_png, prompt, **kwargs):
                return "dummy"

            def list_models(self):
                return ["dummy"]

        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("test", DummyProvider)
        assert pm._provider_registry["test"] is DummyProvider

    def test_register_non_subclass_raises_type_error(self):
        """OCRProvider 非サブクラスの登録で TypeError が送出されること"""
        pm = pagefolio.PluginManager()
        with pytest.raises(TypeError):
            pm.register_ocr_provider("bad", object)

    def test_build_provider_uses_registry(self):
        """build_provider が plugin_manager._provider_registry を参照すること（D-07）"""
        from pagefolio.ocr import build_provider
        from pagefolio.ocr_providers import OCRProvider

        class DummyProvider(OCRProvider):
            def ocr_image(self, b64_png, prompt, **kwargs):
                return "dummy"

            def list_models(self):
                return ["dummy"]

        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("test_plugin", DummyProvider)
        provider = build_provider({"ocr_provider": "test_plugin"}, plugin_manager=pm)
        assert isinstance(provider, DummyProvider)

    def test_build_provider_raises_value_error_for_unknown(self):
        """未登録かつ未知のプロバイダ名で ValueError が送出されること"""
        from pagefolio.ocr import build_provider

        pm = pagefolio.PluginManager()
        with pytest.raises(ValueError):
            build_provider({"ocr_provider": "completely_unknown"}, plugin_manager=pm)


# ===== Phase 02-01: register_ocr_provider 堅牢化・unload 解除・公開アクセサ =====


def _make_dummy_provider_class():
    """テスト用の OCRProvider サブクラスを生成する"""
    from pagefolio.ocr_providers import OCRProvider

    class DummyProvider(OCRProvider):
        def ocr_image(self, b64_png, prompt, **kwargs):
            return "dummy"

        def list_models(self):
            return ["dummy"]

    return DummyProvider


class TestRegisterOcrProviderDuplicatePolicy:
    """register_ocr_provider の重複名ポリシー検証（D-08）"""

    def test_register_duplicate_builtin_name_rejected_with_warning(self, caplog):
        """組み込み名 tesseract への登録は拒否され registry 非追加・WARNING が出る"""
        DummyProvider = _make_dummy_provider_class()
        pm = pagefolio.PluginManager()
        with caplog.at_level("WARNING"):
            pm.register_ocr_provider("tesseract", DummyProvider)
        assert "tesseract" not in pm._provider_registry
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_register_plugin_duplicate_name_overwrites_with_warning(self, caplog):
        """プラグイン同士の重複名登録は後勝ちで上書きされ WARNING が出る"""
        DummyA = _make_dummy_provider_class()
        DummyB = _make_dummy_provider_class()
        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("myprov", DummyA)
        with caplog.at_level("WARNING"):
            pm.register_ocr_provider("myprov", DummyB)
        assert pm._provider_registry["myprov"] is DummyB
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_register_non_subclass_still_raises_type_error(self):
        """非サブクラス登録は重複名ポリシーより先に TypeError 送出（既存挙動）"""
        pm = pagefolio.PluginManager()
        with pytest.raises(TypeError):
            pm.register_ocr_provider("tesseract", object)


class TestUnloadPluginDeregistersProvider:
    """unload_plugin による OCR プロバイダ登録解除（D-09）"""

    def _create_ocr_plugin_file(self, path, name="OcrPlugin"):
        """on_load でカスタム OCR プロバイダを登録するプラグインファイルを生成"""
        code = textwrap.dedent(f"""\
            import pagefolio
            from pagefolio.ocr_providers import OCRProvider


            class DummyProvider(OCRProvider):
                def ocr_image(self, b64_png, prompt, **kwargs):
                    return "dummy"

                def list_models(self):
                    return ["dummy"]


            class {name}(pagefolio.PDFEditorPlugin):
                name = "{name}"
                version = "1.0.0"

                def on_load(self, app):
                    app.plugin_manager.register_ocr_provider("myprov", DummyProvider)
        """)
        path.write_text(code, encoding="utf-8")
        return path

    def test_unload_deregisters_provider(self, tmp_path):
        """unload_plugin 後、そのプラグインが登録した名前が registry から消える"""

        class _App:
            pass

        pm = pagefolio.PluginManager()
        app = _App()
        app.plugin_manager = pm
        plugin_file = self._create_ocr_plugin_file(tmp_path / "ocr_plug.py")
        pm.load_plugin("ocr_plug", str(plugin_file), app=app)

        assert pm.get_ocr_provider("myprov") is not None

        pm.unload_plugin("ocr_plug")

        assert pm.get_ocr_provider("myprov") is None
        assert "myprov" not in pm.list_ocr_providers()

    def test_unload_deregisters_provider_owner_tracking_cleared(self, tmp_path):
        """unload 後、owner 辞書からも解除されること（再登録時に誤検出しない）"""

        class _App:
            pass

        pm = pagefolio.PluginManager()
        app = _App()
        app.plugin_manager = pm
        plugin_file = self._create_ocr_plugin_file(tmp_path / "ocr_plug.py")
        pm.load_plugin("ocr_plug", str(plugin_file), app=app)
        pm.unload_plugin("ocr_plug")

        assert "myprov" not in pm._provider_owners


class TestPublicAccessors:
    """get_ocr_provider / list_ocr_providers の公開アクセサテスト（D-10）"""

    def test_public_accessor_get_ocr_provider_returns_registered_class(self):
        DummyProvider = _make_dummy_provider_class()
        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("myprov", DummyProvider)
        assert pm.get_ocr_provider("myprov") is DummyProvider

    def test_public_accessor_get_ocr_provider_returns_none_for_unknown(self):
        pm = pagefolio.PluginManager()
        assert pm.get_ocr_provider("unknown") is None

    def test_public_accessor_list_ocr_providers_returns_registered_names(self):
        DummyProvider = _make_dummy_provider_class()
        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("myprov", DummyProvider)
        assert pm.list_ocr_providers() == ["myprov"]

    def test_build_provider_resolves_via_public_accessor(self):
        """build_provider が get_ocr_provider() 経由で解決すること（D-10）"""
        from pagefolio.ocr import build_provider

        DummyProvider = _make_dummy_provider_class()
        pm = pagefolio.PluginManager()
        pm.register_ocr_provider("myprov", DummyProvider)
        provider = build_provider({"ocr_provider": "myprov"}, plugin_manager=pm)
        assert isinstance(provider, DummyProvider)
