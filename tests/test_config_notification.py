"""設定読込障害の実 App 経路と原本保護。"""

import json
import tkinter as tk
from collections import deque
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import Mock

import fitz
import pytest

import pagefolio.plugins as plugins_mod
import pagefolio.settings as settings_mod


@pytest.fixture
def save_app():
    from pagefolio.app import PDFEditorApp

    app = PDFEditorApp.__new__(PDFEditorApp)
    app.settings = {"lang": "ja", "theme": "dark"}
    app.lang = "ja"
    app.font_size = 12
    app._settings_load_status = "ok"
    app._settings_autosave_blocked = False
    app._settings_exit_save_failed = False
    app._config_notices = deque()
    app._config_notice_seq = 0
    app._config_load_notice_registered = False
    app._config_notice_after = None
    app._config_displayed_id = None
    app._config_notice_generation = 0
    app._config_notice_monitor = None
    app._config_notice_closed = False
    app.root = SimpleNamespace(
        geometry=lambda: "900x700+0+0",
        destroy=Mock(),
        after_idle=Mock(return_value="idle"),
        after_cancel=Mock(),
    )
    app.doc = None
    app.edit_mode = True
    app._save_sash_positions = Mock()
    app._clear_undo_stacks = Mock()
    app._rebuild_ui = Mock()
    app._set_status = Mock()
    return app


class _NoticeClock:
    """after/idle と単調時計を一緒に進める。実時間の sleep は不要。"""

    def __init__(self):
        self.now = 0
        self.sequence = 0
        self.pending = {}
        self.grab = None

    def after(self, delay, callback):
        self.sequence += 1
        self.pending[self.sequence] = (self.now + delay, callback)
        return self.sequence

    def after_idle(self, callback):
        return self.after(0, callback)

    def after_cancel(self, token):
        self.pending.pop(token, None)

    def advance(self, milliseconds=0):
        end = self.now + milliseconds
        while self.pending:
            token = min(self.pending, key=lambda t: (self.pending[t][0], t))
            due, callback = self.pending[token]
            if due > end:
                break
            self.now = due
            del self.pending[token]
            callback()
        self.now = end

    def grab_current(self):
        return self.grab

    def winfo_exists(self):
        return True


@pytest.fixture
def notice_app(save_app, monkeypatch):
    from pagefolio.toast import ToastManager

    app = save_app
    app.root = _NoticeClock()
    monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: app.root.now / 1000)

    def build_frame(manager, category, message, retry_cb):
        manager._frame = SimpleNamespace(destroy=Mock())
        manager._msg_var = SimpleNamespace(set=Mock())
        manager.message = message

    monkeypatch.setattr(ToastManager, "_build_frame", build_frame)
    app._toast = ToastManager(app)
    app._toast.on_idle = app._schedule_config_notice
    return app


class TestNotificationLifecycle:
    def _start(self, app, count=1):
        for _ in range(count):
            app._enqueue_config_notice("config_save_failed")
        app._schedule_config_notice()
        app.root.advance()

    @pytest.mark.parametrize("category", ["save_file", "print"])
    def test_interruption_preserves_remaining_time(self, notice_app, category):
        app = notice_app
        self._start(app)
        app.root.advance(4000)
        app._toast.show(category, "操作失敗", retry_cb=lambda: None)
        assert app._config_notices[0]["remaining_ms"] == 6000
        app.root.advance(20000)
        assert len(app._config_notices) == 1
        app._toast.dismiss(category)
        app.root.advance(5999)
        assert len(app._config_notices) == 1
        app.root.advance(1)
        assert not app._config_notices
        assert not app.root.pending

    def test_fifo_boundary_and_stale_close_never_consume_next(self, notice_app):
        app = notice_app
        self._start(app, 3)
        ids = [n["event_id"] for n in app._config_notices]
        assert len(set(ids)) == 3
        stale_close = app._toast._on_close
        stale_timer = app.root.pending[app._toast._duration_after][1]
        app.root.advance(9999)
        assert len(app._config_notices) == 3
        app.root.advance(1)
        assert app._config_notices[0]["event_id"] == ids[1]
        stale_close("expired")
        stale_timer()
        assert len(app._config_notices) == 2
        app._toast.dismiss(app._toast._active_category, reason="user")
        app.root.advance()
        assert app._config_notices[0]["event_id"] == ids[2]
        app.root.advance(10000)
        assert not app._config_notices

    def test_rebuild_preserves_time_language_and_rejects_old_callbacks(
        self, notice_app
    ):
        from pagefolio.toast import ToastManager

        app = notice_app
        self._start(app)
        old = app._toast
        old_close = old._on_close
        old_timer = app.root.pending[old._duration_after][1]
        app.root.advance(4000)
        app._prepare_config_notice_rebuild()
        app.lang = "en"
        app._toast = ToastManager(app)
        app._toast.on_idle = app._schedule_config_notice
        app._schedule_config_notice()
        app.root.advance()
        assert app._toast.message == app._t("config_save_failed")
        assert app._config_notices[0]["remaining_ms"] == 6000
        old_close("user")
        old_timer()
        assert len(app._config_notices) == 1
        app.root.advance(5999)
        assert len(app._config_notices) == 1
        app.root.advance(1)
        assert not app._config_notices

    def test_existing_operation_and_initial_nested_grab_hold_unshown_time(
        self, notice_app
    ):
        app = notice_app
        app._toast.show("print", "印刷失敗")
        outer, inner = object(), object()
        app.root.grab = inner
        self._start(app)
        app.root.advance(20000)
        assert app._toast._active_category == "print"
        app._toast.dismiss("print")
        app.root.grab = outer
        app.root.advance(20000)
        assert app._config_notices[0]["shown_at"] is None
        assert app._config_notices[0]["remaining_ms"] == 10000
        app.root.grab = None
        app.root.advance(100)
        app.root.advance(9999)
        assert len(app._config_notices) == 1
        app.root.advance(1)
        assert not app._config_notices

    def test_modal_suspends_display_and_nested_exit_does_not_resume(self, notice_app):
        app = notice_app
        self._start(app)
        app.root.advance(3900)
        app.root.grab = object()
        app.root.advance(100)
        assert app._config_notices[0]["remaining_ms"] == 6000
        assert app._toast._frame is None
        app.root.advance(20000)
        app.root.grab = object()
        app.root.advance(1000)
        assert app._toast._frame is None
        app.root.grab = None
        app.root.advance(100)
        app.root.advance(5999)
        assert len(app._config_notices) == 1
        app.root.advance(1)
        assert not app._config_notices

    def test_grab_at_expiry_keeps_event_until_release(self, notice_app):
        app = notice_app
        self._start(app)
        app.root.advance(9999)
        app.root.grab = object()
        app.root.advance(1)
        assert len(app._config_notices) == 1
        app.root.advance(20000)
        assert len(app._config_notices) == 1
        app.root.grab = None
        app.root.advance(100)
        assert not app._config_notices

    def test_shutdown_cancels_all_owned_callbacks(self, notice_app):
        app = notice_app
        self._start(app, 2)
        app._close_config_notices()
        app.root.advance(20000)
        assert len(app._config_notices) == 2
        assert not app.root.pending

    def test_real_rebuild_restores_same_notice_in_current_language(
        self, isolated_app, monkeypatch
    ):
        from tkinterdnd2 import TkinterDnD

        from pagefolio.app import PDFEditorApp

        isolated_app.write_bytes(b"{broken")
        clock = [0.0]
        monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
        root = TkinterDnD.Tk()
        root.withdraw()
        app = None
        try:
            app = PDFEditorApp(root)
            root.update_idletasks()
            old = app._toast
            old_frame = old._frame
            event_id = app._config_notices[0]["event_id"]
            clock[0] = 4.0
            app.lang = "en"
            app._rebuild_ui()
            root.update_idletasks()
            assert app._toast is not old
            assert not old_frame.winfo_exists()
            assert app._config_notices[0]["event_id"] == event_id
            assert app._config_notices[0]["remaining_ms"] == 6000
            assert app._toast._msg_var.get() == app._t("config_load_corrupt")
            assert root.grab_current() is None
            assert isolated_app.read_bytes() == b"{broken"
        finally:
            if app is not None:
                app._close_config_notices()
                app._clear_undo_stacks()
            root.destroy()


class TestSaveFlow:
    @pytest.mark.parametrize("status", ["corrupt", "unreadable"])
    def test_protected_explicit_save_rules(self, save_app, monkeypatch, status):
        app = save_app
        app._settings_load_status = status
        app._settings_autosave_blocked = True
        save = Mock(return_value=True)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        assert app._persist_settings(explicit=False) is False
        assert not app._config_notices
        assert app._persist_settings() is (status == "corrupt")
        assert save.call_count == (status == "corrupt")
        assert app._settings_autosave_blocked is (status == "unreadable")
        assert len(app._config_notices) == (status == "unreadable")

    def test_apply_failure_keeps_memory_and_original_without_success(
        self, save_app, isolated_app, monkeypatch
    ):
        app = save_app
        original = b"{corrupt"
        isolated_app.write_bytes(original)
        app._settings_load_status = "corrupt"
        app._settings_autosave_blocked = True

        def fail(*args):
            raise PermissionError(13, "secret")

        monkeypatch.setattr(settings_mod.os, "replace", fail)
        values = {"lang": "en", "font_size": 14, "theme": "light"}
        app._apply_settings(values)
        assert app.settings == values
        assert app.lang == "en" and app.font_size == 14
        assert app._settings_autosave_blocked
        assert isolated_app.read_bytes() == original
        assert len(app._config_notices) == 1
        assert app._config_notices[0]["message_key"] == "config_save_failed"
        app._set_status.assert_not_called()
        app._rebuild_ui.assert_called_once()

    def test_explicit_success_clears_protection_and_exit_flag_only(
        self, save_app, monkeypatch
    ):
        app = save_app
        app._settings_exit_save_failed = True
        app._settings_autosave_blocked = True
        app._settings_load_status = "corrupt"
        app._enqueue_config_notice("config_save_failed")
        monkeypatch.setattr("pagefolio.app._save_settings", lambda settings: True)
        assert app._persist_settings() is True
        assert not app._settings_exit_save_failed
        assert not app._settings_autosave_blocked
        assert len(app._config_notices) == 1


class TestExitSaveFailure:
    def test_no_confirmation_never_saves_or_clears_failure(self, save_app, monkeypatch):
        app = save_app
        app.doc = Mock()
        app._settings_exit_save_failed = True
        save = Mock(return_value=False)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr("pagefolio.app.messagebox.askyesno", lambda *a: False)
        app._quit()
        save.assert_not_called()
        assert app._settings_exit_save_failed
        app.root.destroy.assert_not_called()

    @pytest.mark.parametrize("document", [False, True])
    def test_first_failure_preserves_work_and_second_exit_skips_save(
        self, save_app, monkeypatch, document
    ):
        app = save_app
        if document:
            app.doc = Mock()
        save = Mock(return_value=False)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr("pagefolio.app.messagebox.askyesno", lambda *a: True)
        app._quit()
        assert app._settings_exit_save_failed
        assert len(app._config_notices) == 1
        app.root.destroy.assert_not_called()
        app._clear_undo_stacks.assert_not_called()
        if document:
            app.doc.close.assert_not_called()
        app._quit()
        save.assert_called_once()
        app.root.destroy.assert_called_once()

    def test_unreadable_exit_skips_collection_and_does_not_set_failure(self, save_app):
        app = save_app
        app._settings_autosave_blocked = True
        app._settings_load_status = "unreadable"
        app.root.geometry = Mock(side_effect=AssertionError("must not collect"))
        assert app._save_window_state() is True
        assert not app._settings_exit_save_failed
        assert not app._config_notices


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
            assert app._toast._active_category == "config_notice"
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
