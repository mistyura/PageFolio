"""設定読込障害の実 App 経路と原本保護。"""

import json
import tkinter as tk
from tkinter import ttk

import fitz
import pytest

import pagefolio.plugins as plugins_mod
import pagefolio.settings as settings_mod


@pytest.fixture
def isolated_app(monkeypatch, tmp_path):
    """設定・外部プロンプト・プラグインの解決先を分離する。"""
    settings_path = tmp_path / "pagefolio_settings.json"
    plugins_path = tmp_path / "plugins"
    plugins_path.mkdir()
    monkeypatch.setattr(settings_mod, "_get_settings_path", lambda: str(settings_path))
    monkeypatch.setattr(settings_mod, "_get_base_dir", lambda: str(tmp_path))
    monkeypatch.setattr(plugins_mod, "_get_plugins_dir", lambda: str(plugins_path))
    yield settings_path


class TestLoadTracer:
    def test_corrupt_settings_show_one_real_toast_and_keep_pdf_editable(
        self, isolated_app, monkeypatch, record_property
    ):
        import pagefolio.app as app_mod

        settings_path = isolated_app
        original = b'{"secret": "sentinel-private-2048", bad json'
        settings_path.write_bytes(original)
        root = tk.Tk()
        root.withdraw()
        app = None
        built = []
        original_build = app_mod.PDFEditorApp._build_ui

        def observed_build(self):
            built.append(getattr(self, "_toast", None))
            return original_build(self)

        monkeypatch.setattr(app_mod.PDFEditorApp, "_build_ui", observed_build)
        try:
            app = app_mod.PDFEditorApp(root)
            assert built == [None]
            assert app._settings_autosave_blocked
            assert len(app._config_notices) == 1
            assert app._toast._active_category is None

            root.update_idletasks()
            assert app._toast._active_category == "config"
            assert app._toast._retry_btn is None
            assert app._toast._frame.winfo_exists()
            assert app._toast._duration_after is not None
            assert root.grab_current() is None
            assert "sentinel-private-2048" not in app._toast._msg_var.get()

            entry = ttk.Entry(root)
            entry.pack()
            root.deiconify()
            root.update()
            entry.focus_force()
            root.update()
            focused = root.focus_get()
            app._show_next_config_notice()
            root.update_idletasks()
            if focused is not None:
                assert focused is entry
                assert root.focus_get() is entry
                record_property("focus_check", "verified")
            else:
                record_property("focus_check", "unverified: Tk returned None")
            assert root.grab_current() is None

            app.doc = fitz.open()
            app.doc.new_page()
            app._rotate_selected(90)
            assert app.doc[0].rotation == 90
            app._save_window_state()
            assert settings_path.read_bytes() == original
            assert not settings_path.with_suffix(".json.bak").exists()
            for widget in app._toast._frame.winfo_children():
                if isinstance(widget, ttk.Button) and widget.cget("text") == "✕":
                    widget.invoke()
                    break
            assert not app._config_notices
        finally:
            if app is not None:
                if getattr(app, "_toast", None) is not None:
                    app._toast._destroy_frame()
                if getattr(app, "_config_notice_after", None) is not None:
                    root.after_cancel(app._config_notice_after)
                if getattr(app, "_thumb_scroll_after", None) is not None:
                    root.after_cancel(app._thumb_scroll_after)
                app._clear_undo_stacks()
                if app.doc is not None:
                    app.doc.close()
            for callback_id in root.tk.call("after", "info"):
                root.after_cancel(callback_id)
            try:
                root.destroy()
            except tk.TclError:
                root.tk.call("destroy", ".")

    def test_config_message_keys_match_languages_without_secret_interpolation(self):
        from pagefolio.lang import LANG

        keys = (
            "config_load_corrupt",
            "config_load_unreadable",
            "config_save_failed",
            "config_save_blocked_unreadable",
        )
        for language in ("ja", "en"):
            for key in keys:
                assert LANG[language][key]
                assert "{" not in LANG[language][key]
                assert "sentinel-private-2048" not in LANG[language][key]


class TestLoadBoundaries:
    @pytest.mark.parametrize(
        ("content", "status"),
        [
            (b"{bad", "corrupt"),
            (b"\xff", "corrupt"),
            (b"[]", "corrupt"),
            (b'{"font_size": true}', "corrupt"),
            (b'{"font_size": 0}', "corrupt"),
            (b'{"lang": "fr"}', "corrupt"),
            (b'{"theme": false}', "corrupt"),
            (b'{"prompt_templates": []}', "corrupt"),
            (b'{"prompt_templates": {"active": 3}}', "corrupt"),
            (b'{"prompt_templates": {"items": []}}', "corrupt"),
            (b'\xef\xbb\xbf{"lang":"en"}', "ok"),
        ],
    )
    def test_file_classification(self, isolated_app, content, status):
        isolated_app.write_bytes(content)
        result = settings_mod._load_settings_result()
        assert result.status == status
        assert isinstance(result.settings, dict)

    def test_missing_and_open_race_are_silent(self, isolated_app, monkeypatch):
        assert settings_mod._load_settings_result().status == "missing"

        def vanished(*args, **kwargs):
            raise FileNotFoundError("disappeared after path lookup")

        monkeypatch.setattr(settings_mod, "open", vanished, raising=False)
        assert settings_mod._load_settings_result().status == "missing"

    @pytest.mark.parametrize(
        "error",
        [PermissionError(13, "secret"), OSError(5, "secret"), RuntimeError("secret")],
    )
    def test_read_failures_are_unreadable_without_leaking_values(
        self, isolated_app, monkeypatch, caplog, error
    ):
        def fail_open(*args, **kwargs):
            raise error

        monkeypatch.setattr(settings_mod, "open", fail_open, raising=False)
        with caplog.at_level("DEBUG", logger="pagefolio.settings"):
            result = settings_mod._load_settings_result()
        assert result.status == "unreadable"
        assert "secret" not in caplog.text

    def test_partial_dict_keeps_unknown_keys_and_compatibility(self, isolated_app):
        isolated_app.write_text(
            json.dumps({"lang": "en", "future_setting": {"keep": True}}),
            encoding="utf-8",
        )
        result = settings_mod._load_settings_result()
        assert result.status == "ok"
        assert result.settings["font_size"] == 12
        assert result.settings["future_setting"] == {"keep": True}
        assert isinstance(settings_mod._load_settings(), dict)


class TestLoadProtection:
    def test_missing_file_starts_without_notice_and_can_save(self, isolated_app):
        import pagefolio.app as app_mod

        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = app_mod.PDFEditorApp(root)
            root.update_idletasks()
            assert app._settings_load_status == "missing"
            assert not app._config_notices
            assert app._toast._active_category is None
            assert not app._settings_autosave_blocked
            app._save_window_state()
            assert isolated_app.is_file()
        finally:
            if app is not None:
                app._clear_undo_stacks()
            for callback_id in root.tk.call("after", "info"):
                root.after_cancel(callback_id)
            try:
                root.destroy()
            except tk.TclError:
                root.tk.call("destroy", ".")

    @pytest.mark.parametrize("confirm", [None, False, True])
    def test_exit_preserves_corrupt_original_and_cancel_keeps_work(
        self, isolated_app, monkeypatch, confirm
    ):
        import pagefolio.app as app_mod

        original = b"{broken original"
        isolated_app.write_bytes(original)
        root = tk.Tk()
        root.withdraw()
        app = None
        saves = []
        monkeypatch.setattr(
            app_mod, "_save_settings", lambda settings: saves.append(settings)
        )
        if confirm is not None:
            monkeypatch.setattr(app_mod.messagebox, "askyesno", lambda *args: confirm)
        try:
            app = app_mod.PDFEditorApp(root)
            if confirm is not None:
                app.doc = fitz.open()
                app.doc.new_page()
            before_settings = dict(app.settings)
            app._save_window_state()
            assert app.settings == before_settings
            app._quit()
            assert saves == []
            assert isolated_app.read_bytes() == original
            assert not isolated_app.with_suffix(".json.bak").exists()
            if confirm is False:
                assert root.winfo_exists()
                assert app.doc is not None and not app.doc.is_closed
                assert app.settings == before_settings
        finally:
            if app is not None:
                if getattr(app, "_toast", None) is not None:
                    app._toast._destroy_frame()
                app._clear_undo_stacks()
                if app.doc is not None and not app.doc.is_closed:
                    app.doc.close()
            try:
                for callback_id in root.tk.call("after", "info"):
                    root.after_cancel(callback_id)
                root.destroy()
            except tk.TclError:
                pass

    def test_load_notice_is_registered_once(self, isolated_app):
        import pagefolio.app as app_mod

        isolated_app.write_bytes(b"{invalid")
        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = app_mod.PDFEditorApp(root)
            app._enqueue_config_notice("config_load_corrupt")
            app._show_next_config_notice()
            app._show_next_config_notice()
            assert len(app._config_notices) == 1
            assert app._config_notice_seq == 1
        finally:
            if app is not None:
                app._toast._destroy_frame()
                app._clear_undo_stacks()
            for callback_id in root.tk.call("after", "info"):
                root.after_cancel(callback_id)
            try:
                root.destroy()
            except tk.TclError:
                root.tk.call("destroy", ".")
