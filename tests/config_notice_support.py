"""設定通知の実Appを私有一時領域で動かす。製品入口からは使用しない。"""

import builtins
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pagefolio.plugins as plugins_mod
import pagefolio.settings as settings_mod


def snapshot_originals():
    """利用者ファイルは内容を出力せず存在・相対名・hashだけを記録する。"""
    base = Path(settings_mod._get_base_dir())
    files = {
        "settings": Path(settings_mod._get_settings_path()),
        "ocr_prompt": base / settings_mod.CUSTOM_PROMPT_FILE,
        "summary_prompt": base / settings_mod.SUMMARY_PROMPT_FILE,
    }
    plugins = Path(plugins_mod._get_plugins_dir())
    result = {"plugins_exists": plugins.exists()}
    if plugins.is_dir():
        files.update(
            ("plugins/" + p.relative_to(plugins).as_posix(), p)
            for p in plugins.rglob("*")
            if p.is_file()
        )
    for name, path in files.items():
        result[name] = {
            "exists": path.exists(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None,
        }
    return result


class IsolatedConfigApp:
    """patchをApp import/初期化より先に適用し、必ず逆順で解放する。"""

    def __init__(self, scenario="missing", *, visible=False):
        if scenario not in {
            "missing",
            "read-corrupt",
            "read-unreadable",
            "save-write",
            "save-replace",
        }:
            raise ValueError("未対応の隔離scenario")
        self.scenario = scenario
        self.visible = visible
        self.root = None
        self.app = None
        self.originals_before = snapshot_originals()
        self.originals_after = None
        self.stack = ExitStack()
        self.temporary = self.stack.enter_context(
            TemporaryDirectory(prefix="pf_config_notice_")
        )
        self.base = Path(self.temporary)
        self.settings_path = self.base / "pagefolio_settings.json"
        self.plugins_path = self.base / "plugins"
        self.plugins_path.mkdir()
        self.stack.enter_context(
            patch.object(
                settings_mod, "_get_settings_path", lambda: str(self.settings_path)
            )
        )
        self.stack.enter_context(
            patch.object(settings_mod, "_get_base_dir", lambda: str(self.base))
        )
        self.stack.enter_context(
            patch.object(
                plugins_mod, "_get_plugins_dir", lambda: str(self.plugins_path)
            )
        )
        self.fault_enabled = True
        if scenario == "read-corrupt":
            self.settings_path.write_bytes(b'{"invalid isolated original')
        elif scenario != "missing":
            self.settings_path.write_text(
                json.dumps({"lang": "ja", "theme": "dark"}), encoding="utf-8"
            )
        if scenario in {"read-unreadable", "save-write"}:
            self.stack.enter_context(
                patch.object(settings_mod, "open", self._open, create=True)
            )
        if scenario == "save-replace":
            self._original_replace = settings_mod.os.replace
            self.stack.enter_context(
                patch.object(settings_mod.os, "replace", self._replace)
            )

    def _open(self, path, mode="r", *args, **kwargs):
        target = Path(path).resolve()
        if self.fault_enabled and (
            (
                self.scenario == "read-unreadable"
                and target == self.settings_path
                and mode.startswith("r")
            )
            or (
                self.scenario == "save-write"
                and target == Path(str(self.settings_path) + ".tmp")
                and mode == "x"
            )
        ):
            raise PermissionError(13, "isolated configuration fault")
        return builtins.open(path, mode, *args, **kwargs)

    def _replace(self, source, target, *args, **kwargs):
        if self.fault_enabled and Path(target).resolve() == self.settings_path:
            raise PermissionError(13, "isolated replace fault")
        return self._original_replace(source, target, *args, **kwargs)

    def start(self):
        import tkinter as tk

        from tkinterdnd2 import TkinterDnD

        from pagefolio.app import PDFEditorApp

        try:
            # 生成より先に退避し、破棄済みのTkをdefault rootへ戻さない。
            self.stack.enter_context(patch.object(tk, "_default_root", None))
            self.root = TkinterDnD.Tk()
            if not self.visible:
                self.root.withdraw()
            self.app = PDFEditorApp.__new__(PDFEditorApp)
            self.app.__init__(self.root)
            return self
        except Exception:
            self.close()
            raise

    def close(self):
        import tkinter as tk

        try:
            if self.root is not None:
                try:
                    if self.root.winfo_exists():
                        if self.app is not None:
                            if hasattr(self.app, "_config_notices"):
                                self.app._close_config_notices()
                        for token in self.root.tk.call("after", "info"):
                            self.root.after_cancel(token)
                        if self.app is not None:
                            if hasattr(self.app, "_undo_stack"):
                                self.app._clear_undo_stacks()
                            doc = getattr(self.app, "doc", None)
                            if doc is not None and not doc.is_closed:
                                doc.close()
                        self.root.destroy()
                except tk.TclError:
                    pass  # 製品の正常終了で既にrootが破棄された場合。
        finally:
            self.stack.close()
            self.originals_after = snapshot_originals()
        if self.originals_before != self.originals_after:
            raise AssertionError("隔離前後で利用者ファイルが変化した")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def create_isolated_app(scenario="missing", *, visible=False):
    return IsolatedConfigApp(scenario, visible=visible)
