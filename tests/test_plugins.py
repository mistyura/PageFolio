"""PluginManager のテスト"""

import os
import sys
import textwrap

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
