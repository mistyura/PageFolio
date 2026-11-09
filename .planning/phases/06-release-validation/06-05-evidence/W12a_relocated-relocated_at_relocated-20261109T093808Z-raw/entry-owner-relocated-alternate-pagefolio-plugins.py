# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""プラグインシステム — 基底クラスとプラグインマネージャー"""

import importlib
import importlib.util
import logging
import os

from pagefolio.constants import PLUGINS_DIR

logger = logging.getLogger(__name__)

# 組み込み OCR プロバイダ名（ocr.py:build_provider の分岐と一致させること・D-08）
_BUILTIN_PROVIDER_NAMES = frozenset(
    {"claude", "gemini", "lmstudio", "tesseract", "ollama", "runpod", "off"}
)


def _get_plugins_dir():
    """プラグインディレクトリのパスを返す（プロジェクトルート内）"""
    import sys

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, PLUGINS_DIR)


class PDFEditorPlugin:
    """プラグイン基底クラス。プラグインはこのクラスを継承して作成する。"""

    name = "Unnamed Plugin"
    version = "0.0.0"
    description = ""
    author = ""

    def on_load(self, app):
        """プラグインがロードされた時に呼ばれる"""
        pass

    def on_unload(self, app):
        """プラグインがアンロードされた時に呼ばれる"""
        pass

    def on_file_open(self, app, path):
        """ファイルが開かれた後に呼ばれる"""
        pass

    def on_file_save(self, app, path):
        """ファイルが保存された後に呼ばれる"""
        pass

    def on_page_rotate(self, app, pages, degrees):
        """ページが回転された後に呼ばれる"""
        pass

    def on_page_delete(self, app, pages):
        """ページが削除された後に呼ばれる"""
        pass

    def on_page_crop(self, app, page_index):
        """ページがトリミングされた後に呼ばれる"""
        pass

    def on_page_change(self, app, page_index):
        """表示ページが変更された時に呼ばれる"""
        pass

    def on_insert(self, app, paths, insert_at):
        """ページが挿入された後に呼ばれる"""
        pass

    def on_merge(self, app, paths):
        """PDFが結合された後に呼ばれる"""
        pass

    def build_ui(self, app, parent):
        """プラグイン独自のUIを構築する。parentはtk.Frameを受け取る。"""
        pass


class PluginManager:
    """プラグインの検出・読み込み・管理を行うマネージャー"""

    def __init__(self):
        self._plugins = {}  # {plugin_id: plugin_instance}
        self._plugin_modules = {}  # {plugin_id: module}
        self._disabled = set()  # 無効化されたプラグインIDのセット
        # OCR プロバイダ登録辞書 {name: OCRProvider サブクラス}
        self._provider_registry = {}
        # name -> plugin_id の対応（owner 判明分のみ・D-09 の unload 解除で使用）
        self._provider_owners = {}
        # on_load(app) 実行中のプラグイン ID（register_ocr_provider の owner 追跡用）
        self._loading_plugin_id = None

    @property
    def plugins(self):
        """有効なプラグイン一覧を返す"""
        return {k: v for k, v in self._plugins.items() if k not in self._disabled}

    @property
    def all_plugins(self):
        """全プラグイン一覧を返す（無効含む）"""
        return dict(self._plugins)

    def is_enabled(self, plugin_id):
        return plugin_id in self._plugins and plugin_id not in self._disabled

    def discover_plugins(self):
        """プラグインディレクトリからプラグインファイルを検出する"""
        plugins_dir = _get_plugins_dir()
        if not os.path.isdir(plugins_dir):
            return []
        found = []
        for name in sorted(os.listdir(plugins_dir)):
            if name.startswith("_") or not name.endswith(".py"):
                continue
            plugin_id = name[:-3]  # .py を除去
            found.append((plugin_id, os.path.join(plugins_dir, name)))
        return found

    def load_plugin(self, plugin_id, filepath, app=None):
        """プラグインファイルを読み込み、登録する"""
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]
        try:
            spec = importlib.util.spec_from_file_location(
                f"pagefolio_plugin_{plugin_id}", filepath
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._plugin_modules[plugin_id] = module

            # モジュール内で PDFEditorPlugin を継承したクラスを探す
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PDFEditorPlugin)
                    and attr is not PDFEditorPlugin
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                return None

            instance = plugin_class()
            self._plugins[plugin_id] = instance
            if app and plugin_id not in self._disabled:
                self._loading_plugin_id = plugin_id
                try:
                    instance.on_load(app)
                except Exception as e:
                    # WR-04: on_load 失敗も enable_plugin と同様に log-and-continue し、
                    # is_enabled()/plugins の状態と戻り値の整合を保つ
                    logger.exception("プラグイン on_load 失敗 (%s): %s", plugin_id, e)
                finally:
                    self._loading_plugin_id = None
            return instance
        except Exception as e:
            logger.exception("プラグインロード失敗 (%s): %s", plugin_id, e)
            return None

    def unload_plugin(self, plugin_id, app=None):
        """プラグインをアンロードする"""
        if plugin_id in self._plugins:
            if app:
                try:
                    self._plugins[plugin_id].on_unload(app)
                except Exception as e:
                    logger.exception("プラグインアンロード失敗 (%s): %s", plugin_id, e)
            del self._plugins[plugin_id]
            self._plugin_modules.pop(plugin_id, None)
            # unload されたプラグインが登録した OCR プロバイダを registry から解除する
            # （settings の ocr_provider は触らない・副作用なし・D-09）
            owned_names = [
                name
                for name, owner in self._provider_owners.items()
                if owner == plugin_id
            ]
            for name in owned_names:
                self._provider_registry.pop(name, None)
                self._provider_owners.pop(name, None)

    def enable_plugin(self, plugin_id, app=None):
        """プラグインを有効化する"""
        self._disabled.discard(plugin_id)
        if plugin_id in self._plugins and app:
            self._loading_plugin_id = plugin_id
            try:
                self._plugins[plugin_id].on_load(app)
            except Exception as e:
                logger.exception("プラグイン有効化失敗 (%s): %s", plugin_id, e)
            finally:
                self._loading_plugin_id = None

    def disable_plugin(self, plugin_id, app=None):
        """プラグインを無効化する"""
        if plugin_id in self._plugins and app:
            try:
                self._plugins[plugin_id].on_unload(app)
            except Exception as e:
                logger.exception("プラグイン無効化失敗 (%s): %s", plugin_id, e)
        self._disabled.add(plugin_id)

    def load_all(self, app=None, disabled_ids=None):
        """全プラグインを検出・読み込みする"""
        if disabled_ids:
            self._disabled = set(disabled_ids)
        for plugin_id, filepath in self.discover_plugins():
            self.load_plugin(plugin_id, filepath, app)

    def fire_event(self, event_name, *args, **kwargs):
        """有効な全プラグインにイベントを通知する"""
        for _plugin_id, plugin in self.plugins.items():
            method = getattr(plugin, event_name, None)
            if method:
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    logger.exception(
                        "プラグインイベント %s 発火失敗: %s", event_name, e
                    )

    def register_ocr_provider(self, name: str, cls) -> None:
        """OCR プロバイダをレジストリに登録する。

        プラグインの on_load(app) 内で次のように呼び出す:
            app.plugin_manager.register_ocr_provider("myprovider", MyProvider)

        重複名ポリシー（D-08）:
          - 組み込みプロバイダ名（claude/gemini/lmstudio/tesseract/ollama/runpod/off）
            との衝突は logger.warning のうえ拒否する（登録されない）。
          - プラグイン同士の重複名は logger.warning のうえ後勝ちで上書きする。

        引数:
          name: プロバイダ識別名（例: "my_ocr"）。build_provider から参照される。
          cls:  OCRProvider のサブクラス（インスタンスではなくクラスを渡すこと）

        例外:
          TypeError — cls が OCRProvider のサブクラスでない場合
        """
        # 循環 import 回避のため関数内 import
        from pagefolio.ocr_providers import OCRProvider

        if not (isinstance(cls, type) and issubclass(cls, OCRProvider)):
            raise TypeError(f"{cls} は OCRProvider のサブクラスでなければなりません")

        if name in _BUILTIN_PROVIDER_NAMES:
            logger.warning(
                "OCR プロバイダ登録拒否: '%s' は組み込みプロバイダ名と衝突します",
                name,
            )
            return

        if name in self._provider_registry:
            logger.warning(
                "OCR プロバイダ '%s' は既に登録済みです。後勝ちで上書き: %s -> %s",
                name,
                self._provider_registry[name].__name__,
                cls.__name__,
            )

        self._provider_registry[name] = cls
        owner = self._loading_plugin_id
        if owner is not None:
            self._provider_owners[name] = owner
        logger.debug("OCR プロバイダ登録: %s -> %s", name, cls.__name__)

    def get_ocr_provider(self, name):
        """登録済み OCR プロバイダクラスを返す（未登録は None）。

        プラグイン作者/呼び出し側は `_provider_registry` へ直接アクセスせず
        本メソッド経由で参照すること（D-10）。
        """
        return self._provider_registry.get(name)

    def list_ocr_providers(self):
        """登録済み OCR プロバイダ名の一覧を返す（D-10）。"""
        return list(self._provider_registry.keys())

    def get_disabled_ids(self):
        """無効化されたプラグインIDリストを返す"""
        return list(self._disabled)
