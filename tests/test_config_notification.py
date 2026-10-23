"""設定読込障害の実 App 経路と原本保護。"""

import ast
import json
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import Mock

import fitz
import pytest

import pagefolio.plugins as plugins_mod
import pagefolio.settings as settings_mod
from tests.config_notice_support import create_isolated_app


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
        self.visible = True

    def winfo_viewable(self):
        return self.visible

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

    @pytest.mark.parametrize("started", [False, True])
    def test_hidden_root_preserves_fifo_and_visible_time(self, notice_app, started):
        app = notice_app
        app.root.visible = started
        self._start(app, 3)
        ids = [n["event_id"] for n in app._config_notices]
        if started:
            app.root.advance(4000)
        app.root.visible = False
        app._monitor_config_notice()
        app.root.advance(40000)
        assert [n["event_id"] for n in app._config_notices] == ids
        assert app._config_notices[0]["remaining_ms"] == (6000 if started else 10000)
        assert app._config_notices[0]["shown_at"] is None
        app.root.visible = True
        app._monitor_config_notice()
        app.root.advance()
        app.root.advance(app._config_notices[0]["remaining_ms"] - 1)
        assert len(app._config_notices) == 3
        app.root.advance(1)
        assert app._config_notices[0]["event_id"] == ids[1]
        app.root.advance(20000)
        assert not app._config_notices

    def test_hidden_at_deadline_is_not_consumed(self, notice_app):
        app = notice_app
        self._start(app)
        app.root.advance(9999)
        app.root.visible = False
        app.root.advance(1)
        assert len(app._config_notices) == 1
        app.root.advance(20000)
        assert len(app._config_notices) == 1

    @pytest.mark.parametrize("hide", ["withdraw", "iconify"])
    def test_real_root_visibility_suspends_same_event(
        self, monkeypatch, isolated_app, hide
    ):
        from pagefolio.app import PDFEditorApp

        clock = [0.0]
        monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
        isolated_app.write_bytes(b"{isolated broken settings")
        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = PDFEditorApp(root)
            root.update()
            assert not root.winfo_viewable()
            assert app._toast._frame is None
            root.deiconify()
            root.update()
            assert root.winfo_viewable()
            assert app._toast._frame.winfo_viewable()
            ids = [n["event_id"] for n in app._config_notices]
            close = app._toast._on_close
            generation = app._toast._generation
            clock[0] = 4.0
            # 子widgetのUnmapはroot非表示として扱わない。
            child = tk.Frame(root)
            app._on_config_root_visibility(SimpleNamespace(widget=child))
            assert app._toast._frame is not None
            child.destroy()
            getattr(root, hide)()
            root.update()
            assert not root.winfo_viewable()
            assert app._toast._frame is None
            assert app._config_notices[0]["remaining_ms"] == 6000
            clock[0] = 44.0
            app._monitor_config_notice()
            app._toast._expire(generation)
            close("expired")
            assert [n["event_id"] for n in app._config_notices] == ids
            assert app._config_notices[0]["remaining_ms"] == 6000
            root.deiconify()
            root.update()
            assert app._toast._frame.winfo_viewable()
            assert app._config_notices[0]["remaining_ms"] == 6000
            close("expired")
            assert [n["event_id"] for n in app._config_notices] == ids
        finally:
            if app is not None:
                app._close_config_notices()
                app._clear_undo_stacks()
            for token in root.tk.call("after", "info"):
                root.after_cancel(token)
            root.destroy()

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
        app = None
        try:
            app = PDFEditorApp(root)
            root.update()
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


class TestAppSaveOrigins:
    @pytest.mark.parametrize("status", ["ok", "corrupt", "unreadable"])
    @pytest.mark.parametrize("origin", ["language", "llm", "plugin"])
    def test_success_obeys_protection(
        self, save_app, isolated_app, monkeypatch, status, origin
    ):
        app = save_app
        isolated_app.write_bytes(b"{protected-original")
        app._settings_load_status = status
        app._settings_autosave_blocked = status != "ok"
        app._update_ocr_buttons_state = Mock()
        app._build_plugin_ui = Mock()
        app.plugin_manager = Mock()
        app.plugin_manager.get_disabled_ids.return_value = ["example"]
        save = Mock(wraps=settings_mod._save_settings)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        if origin == "language":
            app._toggle_lang()
        elif origin == "llm":
            assert app._apply_llm_settings_live({"ocr_provider": "off"}) is (
                status != "unreadable"
            )
        else:
            app._reload_plugins(persist=True)
        assert save.call_count == (status != "unreadable")
        assert app._settings_autosave_blocked is (status == "unreadable")
        if status == "unreadable":
            assert isolated_app.read_bytes() == b"{protected-original"
            assert len(app._config_notices) == 1
        else:
            assert json.loads(isolated_app.read_text(encoding="utf-8")) == app.settings
            assert not app._config_notices

    @pytest.mark.parametrize("status", ["ok", "corrupt", "unreadable"])
    @pytest.mark.parametrize("origin", ["language", "llm", "plugin"])
    def test_failure_keeps_applied_memory_and_one_event(
        self, save_app, monkeypatch, status, origin
    ):
        from pagefolio.dialogs.plugin import PluginDialog

        app = save_app
        app._settings_load_status = status
        app._settings_autosave_blocked = status != "ok"
        app._update_ocr_buttons_state = Mock()
        app._build_plugin_ui = Mock()
        app.plugin_manager = Mock()
        app.plugin_manager.get_disabled_ids.return_value = ["example"]
        save = Mock(return_value=False)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        if origin == "language":
            app._toggle_lang()
            assert app.settings["lang"] == app.lang == "en"
            app._rebuild_ui.assert_called_once()
        elif origin == "llm":
            assert app._apply_llm_settings_live({"ocr_provider": "off"}) is False
            assert app.settings["ocr_provider"] == "off"
            app._update_ocr_buttons_state.assert_called_once()
        else:
            dialog = SimpleNamespace(
                app=app,
                pm=app.plugin_manager,
                _check_vars={"example": SimpleNamespace(get=lambda: False)},
                destroy=Mock(),
            )
            PluginDialog._toggle(dialog, "example")
            PluginDialog._close(dialog)
            assert app.settings["disabled_plugins"] == ["example"]
            app.plugin_manager.disable_plugin.assert_called_once_with("example", app)
            app._build_plugin_ui.assert_called_once()
            dialog.destroy.assert_called_once()
        assert save.call_count == (status != "unreadable")
        assert len(app._config_notices) == 1
        assert app._config_notices[0]["message_key"] == (
            "config_save_blocked_unreadable"
            if status == "unreadable"
            else "config_save_failed"
        )
        assert app._settings_autosave_blocked is (status != "ok")
        app._set_status.assert_not_called()

    @pytest.mark.parametrize("status", ["corrupt", "unreadable"])
    def test_plugin_noop_rescan_close_preserves_original(
        self, save_app, isolated_app, monkeypatch, status
    ):
        from pagefolio.dialogs.plugin import PluginDialog

        original = b"{protected-original"
        isolated_app.write_bytes(original)
        app = save_app
        app._settings_load_status = status
        app._settings_autosave_blocked = True
        app.settings["disabled_plugins"] = ["example"]
        app._build_plugin_ui = Mock()
        app.plugin_manager = Mock(all_plugins={})
        app.plugin_manager.get_disabled_ids.return_value = ["example"]
        save = Mock(wraps=settings_mod._save_settings)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        dialog = SimpleNamespace(
            app=app, pm=app.plugin_manager, _refresh_list=Mock(), destroy=Mock()
        )
        app._reload_plugins()
        PluginDialog._rescan(dialog)
        PluginDialog._close(dialog)
        save.assert_not_called()
        assert not app._config_notices
        assert app._settings_autosave_blocked
        assert isolated_app.read_bytes() == original

    def test_changed_rescan_persists_once(self, save_app, monkeypatch):
        from pagefolio.dialogs.plugin import PluginDialog

        app = save_app
        app.settings["disabled_plugins"] = []
        app._build_plugin_ui = Mock()
        app.plugin_manager = Mock(all_plugins={})
        app.plugin_manager.get_disabled_ids.side_effect = [[], ["example"], ["example"]]
        save = Mock(return_value=True)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        dialog = SimpleNamespace(app=app, pm=app.plugin_manager, _refresh_list=Mock())
        PluginDialog._rescan(dialog)
        save.assert_called_once_with(app.settings)
        assert app.settings["disabled_plugins"] == ["example"]

    @pytest.mark.parametrize("origin", ["general", "llm"])
    def test_same_value_explicit_apply_retries(self, save_app, monkeypatch, origin):
        app = save_app
        app._update_ocr_buttons_state = Mock()
        save = Mock(side_effect=[False, True])
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        apply = (
            app._apply_settings if origin == "general" else app._apply_llm_settings_live
        )
        values = dict(app.settings)
        assert apply(dict(values)) is False
        assert apply(dict(values)) is True
        assert save.call_count == 2
        assert len(app._config_notices) == 1

    def test_plugin_failure_waits_for_real_modal_close(self, isolated_app, monkeypatch):
        from tkinterdnd2 import TkinterDnD

        from pagefolio.app import PDFEditorApp
        from pagefolio.dialogs.plugin import PluginDialog

        root = TkinterDnD.Tk()
        app = None
        dialog = None
        clock = [0.0]
        monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
        monkeypatch.setattr("pagefolio.app._save_settings", lambda settings: False)
        try:
            app = PDFEditorApp(root)
            dialog = PluginDialog(root, app)
            dialog.withdraw()
            dialog.grab_set()
            dialog.pm.disable_plugin = Mock()
            dialog.pm.get_disabled_ids = Mock(return_value=["example"])
            dialog._check_vars = {"example": SimpleNamespace(get=lambda: False)}
            dialog._toggle("example")
            root.update()
            clock[0] = 12.0
            app._show_next_config_notice()
            assert app._toast._frame is None
            assert app._config_notices[0]["remaining_ms"] == 10000
            dialog._close()
            dialog = None
            app._schedule_config_notice()
            root.update()
            assert app._toast._frame is not None
            assert app._config_notices[0]["remaining_ms"] == 10000
        finally:
            if dialog is not None:
                dialog.destroy()
            if app is not None:
                app._close_config_notices()
                app._clear_undo_stacks()
            root.destroy()


class TestLlmSaveOrigins:
    def _nested(self, app, monkeypatch, owner="callback"):
        from pagefolio.dialogs.settings import SettingsDialog

        captured = {}
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog",
            lambda *args, **kwargs: captured.update(kwargs),
        )
        app._update_ocr_buttons_state = Mock()
        app._session_api_keys = {"openai": "session-only-secret"}
        dialog = SimpleNamespace(
            current_settings={**app.settings, "theme": "light"},
            _font=app._font,
            callback=Mock(),
            _app=app,
            _session_api_keys=app._session_api_keys,
        )
        if owner == "callback":
            dialog._on_llm_apply = app._apply_llm_settings_live
        SettingsDialog._open_llm_config(dialog)
        assert captured["session_api_keys"] is app._session_api_keys
        return dialog, captured["on_apply"]

    def test_nested_apply_saves_once_without_general_settings(
        self, save_app, monkeypatch
    ):
        save = Mock(return_value=True)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        dialog, apply = self._nested(save_app, monkeypatch)
        apply({"ocr_provider": "off"})
        assert save.call_count == 1
        assert save.call_args.args[0]["theme"] == "dark"
        assert save_app.settings["ocr_provider"] == "off"
        assert dialog.current_settings["theme"] == "light"
        dialog.callback.assert_not_called()
        save_app._rebuild_ui.assert_not_called()

    @pytest.mark.parametrize("status", ["ok", "corrupt", "unreadable"])
    @pytest.mark.parametrize("saved", [True, False])
    @pytest.mark.parametrize("owner", ["callback", "app"])
    def test_nested_cancel_retains_llm_and_protects_original(
        self, save_app, isolated_app, monkeypatch, status, saved, owner
    ):
        app = save_app
        original = b"{protected-original"
        isolated_app.write_bytes(original)
        app._settings_load_status = status
        app._settings_autosave_blocked = status != "ok"
        save = Mock(wraps=settings_mod._save_settings)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        if not saved:
            monkeypatch.setattr(
                settings_mod.os, "replace", Mock(side_effect=PermissionError("private"))
            )
        dialog, apply = self._nested(app, monkeypatch, owner)
        assert apply({"ocr_provider": "off", "ocr_custom_prompt": "new"}) is (
            saved and status != "unreadable"
        )
        assert app.settings["theme"] == "dark"
        assert app.settings["ocr_custom_prompt"] == "new"
        assert dialog.current_settings["theme"] == "light"
        assert save.call_count == (status != "unreadable")
        assert len(app._config_notices) == (not saved or status == "unreadable")
        assert app._settings_autosave_blocked is (
            status != "ok" and (not saved or status == "unreadable")
        )
        if not saved or status == "unreadable":
            assert isolated_app.read_bytes() == original
        else:
            assert (
                json.loads(isolated_app.read_text(encoding="utf-8"))["theme"] == "dark"
            )
            assert "session-only-secret" not in isolated_app.read_text(encoding="utf-8")
        app._update_ocr_buttons_state.assert_called_once()
        dialog.callback.assert_not_called()
        app._rebuild_ui.assert_not_called()

    def test_ownerless_stub_updates_memory_only(self, monkeypatch):
        from pagefolio.dialogs.settings import SettingsDialog

        captured = {}
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog",
            lambda *a, **kw: captured.update(kw),
        )
        save = Mock(return_value=True)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        dialog = SimpleNamespace(
            current_settings={},
            _font=lambda *a: None,
            callback=Mock(),
            _on_llm_apply="not callable",
        )
        SettingsDialog._open_llm_config(dialog)
        assert captured["on_apply"]({"ocr_provider": "off"}) is False
        assert dialog.current_settings["ocr_provider"] == "off"
        save.assert_not_called()
        dialog.callback.assert_not_called()

    @pytest.mark.parametrize("status", ["ok", "corrupt", "unreadable"])
    @pytest.mark.parametrize("saved", [True, False])
    def test_ocr_apply_keeps_provider_prompt_keys_and_buttons(
        self, save_app, isolated_app, monkeypatch, status, saved
    ):
        from pagefolio.ocr_dialog import OCRDialog

        app = save_app
        app._settings_load_status = status
        app._settings_autosave_blocked = status != "ok"
        app._session_api_keys = {"openai": "session-only-secret"}
        app._update_ocr_buttons_state = Mock()
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        save = Mock(return_value=saved)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        marker = SimpleNamespace(max_concurrency=4)
        build = Mock(return_value=marker)
        monkeypatch.setattr("pagefolio.ocr.build_provider", build)
        dialog = SimpleNamespace(
            app=app,
            provider=None,
            concurrency=2,
            custom_prompt="old",
            _update_preset_note=Mock(),
            _refresh_provider_dependent_ui=Mock(),
            _sync_param_vars_from_settings=Mock(),
            _update_summary_btn_state=Mock(),
            _maybe_show_lang_fallback_notice=Mock(),
            progress_var=Mock(),
        )
        OCRDialog._apply_llm_settings(
            dialog, {"ocr_provider": "openai", "ocr_custom_prompt": "new"}
        )
        assert save.call_count == (status != "unreadable")
        assert len(app._config_notices) == (not saved or status == "unreadable")
        assert dialog.provider is marker
        assert dialog.custom_prompt == "new"
        assert build.call_args.kwargs["api_key"] == "session-only-secret"
        assert app._session_api_keys == {"openai": "session-only-secret"}
        dialog._sync_param_vars_from_settings.assert_called_once()
        dialog._refresh_provider_dependent_ui.assert_called_once()
        dialog._update_summary_btn_state.assert_called_once()
        app._update_ocr_buttons_state.assert_called_once()
        app._set_status.assert_not_called()

    def test_product_open_settings_injects_owner(self, save_app, monkeypatch):
        dialog = Mock()
        monkeypatch.setattr("pagefolio.app.SettingsDialog", dialog)
        save_app._open_settings()
        assert dialog.call_args.kwargs["app"] is save_app
        assert (
            dialog.call_args.kwargs["on_llm_apply"] == save_app._apply_llm_settings_live
        )

    @pytest.mark.parametrize("apply_inner", [True, False])
    @pytest.mark.parametrize("origin", ["settings", "ocr"])
    def test_real_nested_close_restores_outer_grab(
        self, save_app, isolated_app, monkeypatch, origin, apply_inner
    ):
        from pagefolio.dialogs.settings import SettingsDialog
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.toast import ToastManager

        root = tk.Tk()
        app = save_app
        app.root = root
        app._toast = ToastManager(app)
        app._toast.on_idle = app._schedule_config_notice
        app._update_ocr_buttons_state = Mock()
        clock = [0.0]
        monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
        monkeypatch.setattr("pagefolio.app._save_settings", lambda settings: False)
        captured = {}

        class NestedDialog(tk.Toplevel):
            def __init__(self, parent, settings, **kwargs):
                super().__init__(parent)
                self.withdraw()
                self.grab_set()
                captured.update(kwargs)

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog", NestedDialog
        )
        outer = None
        inner = None
        try:
            if origin == "settings":
                outer = SettingsDialog(
                    root,
                    app.settings,
                    Mock(),
                    app._font,
                    app=app,
                    on_llm_apply=app._apply_llm_settings_live,
                )
            else:
                outer = OCRDialog.__new__(OCRDialog)
                tk.Toplevel.__init__(outer, root)
                outer.app = app
                outer._started = False
                outer._done = False
                outer._summary_running = False
                outer._font = app._font
                outer.provider = SimpleNamespace(max_concurrency=1)
                outer.concurrency = 1
                outer.progress_var = Mock()
                for name in (
                    "_refresh_provider_dependent_ui",
                    "_sync_param_vars_from_settings",
                    "_maybe_show_lang_fallback_notice",
                    "_update_summary_btn_state",
                    "_update_preset_note",
                ):
                    setattr(outer, name, Mock())
            outer.withdraw()
            outer.grab_set()
            if not apply_inner:
                app._persist_settings()
            outer._open_llm_config()
            inner = outer._llm_config_dialog
            inner.destroy()
            inner = None
            if apply_inner:
                assert captured["on_apply"]({"ocr_provider": "off"}) is False
            assert root.grab_current() is outer
            root.update()
            clock[0] = 12.0
            app._show_next_config_notice()
            assert app._toast._frame is None
            assert app._config_notices[0]["remaining_ms"] == 10000
            outer.destroy()
            outer = None
            app._schedule_config_notice()
            root.update()
            assert app._toast._frame is not None
            assert app._config_notices[0]["remaining_ms"] == 10000
        finally:
            if inner is not None:
                inner.destroy()
            if outer is not None:
                outer.destroy()
            app._close_config_notices()
            root.destroy()

    @pytest.mark.parametrize("origin", ["settings", "ocr"])
    def test_nested_modal_keeps_event_after_inner_exit(
        self, notice_app, monkeypatch, origin
    ):
        app = notice_app
        app.root.grab = object()
        save = Mock(return_value=False)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        if origin == "settings":
            dialog, apply = self._nested(app, monkeypatch)
            apply({"ocr_provider": "off"})
        else:
            from pagefolio.ocr_dialog import OCRDialog

            dialog = SimpleNamespace(
                app=app,
                provider=SimpleNamespace(max_concurrency=1),
                concurrency=1,
                progress_var=Mock(),
                _refresh_provider_dependent_ui=Mock(),
                _sync_param_vars_from_settings=Mock(),
                _maybe_show_lang_fallback_notice=Mock(),
                _update_summary_btn_state=Mock(),
            )
            OCRDialog._apply_llm_settings(dialog, {"ocr_provider": "off"})
        app.root.advance(12000)
        app.root.grab = object()
        app.root.advance(12000)
        assert len(app._config_notices) == 1
        assert app._toast._frame is None
        app.root.grab = None
        app.root.advance(100)
        assert app._toast._frame is not None
        app.root.advance(9999)
        assert len(app._config_notices) == 1
        app.root.advance(1)
        assert not app._config_notices


class TestToolSaveOrigins:
    @pytest.mark.parametrize("close", ["save", "cancel", "wm"])
    def test_real_shortcuts_close_restores_outer_grab(
        self, save_app, monkeypatch, close
    ):
        from pagefolio.dialogs.settings import SettingsDialog
        from pagefolio.toast import ToastManager

        root = tk.Tk()
        app = save_app
        app.root = root
        app._default_shortcuts = {"open_file": "<Control-o>"}
        app._bind_shortcuts = Mock()
        app._toast = ToastManager(app)
        app._toast.on_idle = app._schedule_config_notice
        clock = [0.0]
        monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
        monkeypatch.setattr("pagefolio.app._save_settings", lambda values: False)
        outer = inner = None
        try:
            root.update()
            outer = SettingsDialog(root, app.settings, Mock(), app._font, app=app)
            outer._open_shortcuts_dialog()
            inner = outer._shortcuts_dialog
            assert root.grab_current() is inner
            # 子widgetの破棄は外側のgrabを復元してはならない。
            child = tk.Frame(inner)
            child.destroy()
            assert root.grab_current() is inner
            if close == "save":
                inner._on_save()
            else:
                app._persist_settings()
                if close == "cancel":
                    for widget in inner.winfo_children():
                        for button in widget.winfo_children():
                            if (
                                isinstance(button, ttk.Button)
                                and button.cget("text")
                                == inner._L["shortcuts_btn_cancel"]
                            ):
                                button.invoke()
                else:
                    root.tk.call(inner.protocol("WM_DELETE_WINDOW"))
            assert not inner.winfo_exists()
            inner = None
            assert root.grab_current() is outer
            clock[0] = 12.0
            app._show_next_config_notice()
            root.update()
            assert outer.winfo_exists()
            assert app._toast._frame is None
            assert len(app._config_notices) == 1
            assert app._config_notices[0]["remaining_ms"] == 10000
            outer.destroy()
            outer = None
            app._show_next_config_notice()
            root.update_idletasks()
            assert app._toast._frame is not None
            assert app._config_notices[0]["remaining_ms"] == 10000
        finally:
            if inner is not None and inner.winfo_exists():
                inner.destroy()
            if outer is not None:
                outer.destroy()
            app._close_config_notices()
            root.destroy()

    @pytest.mark.parametrize("status", ["ok", "corrupt", "unreadable"])
    @pytest.mark.parametrize("saved", [True, False])
    @pytest.mark.parametrize("origin", ["shortcuts", "mosaic", "zoom", "page_size"])
    def test_handler_preserves_memory_and_protection(
        self, save_app, isolated_app, monkeypatch, status, saved, origin
    ):
        from pagefolio.dialogs.shortcuts import ShortcutsDialog

        app = save_app
        original = b"{protected-original"
        isolated_app.write_bytes(original)
        app._settings_load_status = status
        app._settings_autosave_blocked = status != "ok"
        app._refresh_all = Mock()
        app._invalidate_thumb_cache = Mock()
        app._bind_shortcuts = Mock()
        app.selected_pages = {3, 25}
        save = Mock(wraps=settings_mod._save_settings)
        monkeypatch.setattr("pagefolio.app._save_settings", save)
        monkeypatch.setattr(settings_mod, "_save_settings", save)
        if not saved:
            monkeypatch.setattr(
                settings_mod.os, "replace", Mock(side_effect=PermissionError("private"))
            )
        if origin == "shortcuts":
            app._default_shortcuts = {"quit": "<F1>"}
            dialog = SimpleNamespace(
                _app=app,
                _capturing_cmd=None,
                _shortcuts={"quit": "<F2>"},
                destroy=Mock(),
            )
            ShortcutsDialog._on_save(dialog)
            assert app.settings["shortcuts"] == {"quit": "<F2>"}
            app._bind_shortcuts.assert_called_once()
            dialog.destroy.assert_called_once()
        elif origin == "mosaic":
            app.mosaic_block_var = SimpleNamespace(get=lambda: 16)
            app._on_mosaic_block_release()
            assert app.settings["mosaic_block"] == 16
        elif origin == "zoom":
            app.thumb_zoom_var = SimpleNamespace(get=lambda: 1.7)
            app._on_thumb_zoom_release()
            assert app.settings["thumb_zoom"] == 1.7
            app._invalidate_thumb_cache.assert_called_once()
            app._refresh_all.assert_called_once()
        else:
            app.page_size_var = SimpleNamespace(get=lambda: 30)
            app.current_page = 25
            app._on_page_size_change()
            assert app.settings["thumb_page_size"] == app._page_size == 30
            assert app._page_window_start == 0
            app._refresh_all.assert_called_once()
            app._invalidate_thumb_cache.assert_not_called()
        assert app.selected_pages == {3, 25}
        assert save.call_count == (status != "unreadable")
        assert len(app._config_notices) == (not saved or status == "unreadable")
        assert app._settings_autosave_blocked is (
            status != "ok" and (not saved or status == "unreadable")
        )
        if not saved or status == "unreadable":
            assert isolated_app.read_bytes() == original
        else:
            assert json.loads(isolated_app.read_text(encoding="utf-8")) == app.settings
        app._set_status.assert_not_called()

    def test_shortcuts_close_leaves_failed_event_for_display(
        self, notice_app, monkeypatch
    ):
        from pagefolio.dialogs.shortcuts import ShortcutsDialog

        app = notice_app
        outer = object()
        app.root.grab = object()
        app._default_shortcuts = {"quit": "<F1>"}
        app._bind_shortcuts = Mock()
        monkeypatch.setattr("pagefolio.app._save_settings", lambda settings: False)
        dialog = SimpleNamespace(
            _app=app,
            _capturing_cmd=None,
            _shortcuts={"quit": "<F2>"},
            destroy=lambda: setattr(app.root, "grab", outer),
        )
        ShortcutsDialog._on_save(dialog)
        assert len(app._config_notices) == 1
        app.root.advance(12000)
        assert app._toast._frame is None
        assert app._config_notices[0]["remaining_ms"] == 10000
        app.root.grab = None
        app._schedule_config_notice()
        app.root.advance()
        assert app._toast._frame is not None
        assert app._config_notices[0]["remaining_ms"] == 10000
        assert app.settings["shortcuts"] == {"quit": "<F2>"}
        app._set_status.assert_not_called()


class TestSaveOriginCoverage:
    def _exports(self):
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / "pagefolio/__init__.py").read_text(encoding="utf-8"))
        exports = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_EXPORTS"
                for target in node.targets
            ):
                for module, names in ast.literal_eval(node.value).items():
                    exports.update(
                        {
                            "pagefolio." + name: "pagefolio." + module + "." + name
                            for name in names
                        }
                    )
        assert (
            exports.get("pagefolio._save_settings")
            == "pagefolio.settings._save_settings"
        )
        return exports

    def _callers(self, source, module_name):
        tree = ast.parse(source)
        exports = self._exports()
        aliases = {}
        package = module_name.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    aliases[item.asname or item.name.split(".")[0]] = (
                        item.name if item.asname else item.name.split(".")[0]
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    parts = package.split(".")
                    module = ".".join(
                        parts[: len(parts) - node.level + 1]
                        + ([module] if module else [])
                    )
                for item in node.names:
                    if item.name == "*":
                        aliases.update(
                            {
                                key.rsplit(".", 1)[1]: value
                                for key, value in exports.items()
                                if key.rsplit(".", 1)[0] == module
                            }
                        )
                    else:
                        symbol = module + "." + item.name
                        aliases[item.asname or item.name] = exports.get(symbol, symbol)

        def resolve(node):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                symbol = resolve(node.value) + "." + node.attr
                return exports.get(symbol, symbol)
            return ""

        callers = set()
        scope = []

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()

            def visit_FunctionDef(self, node):
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node):
                if resolve(node.func) == "pagefolio.settings._save_settings":
                    callers.add(".".join(scope) or "<module>")
                self.generic_visit(node)

        Visitor().visit(tree)
        return callers

    @pytest.mark.parametrize(
        "statement,call",
        [
            ("from pagefolio.settings import _save_settings as save", "save"),
            ("import pagefolio.settings as config", "config._save_settings"),
            ("import pagefolio.settings", "pagefolio.settings._save_settings"),
            ("from pagefolio import _save_settings as save", "save"),
            ("import pagefolio as pf", "pf._save_settings"),
            ("from .settings import _save_settings", "_save_settings"),
            ("from pagefolio import *", "_save_settings"),
        ],
    )
    def test_inventory_resolves_alias_attribute_and_reexport(self, statement, call):
        source = statement + "\ndef operation():\n    " + call + "({})\n"
        assert self._callers(source, "pagefolio.consumer") == {"operation"}

    def test_only_app_owner_calls_low_level_save(self):
        root = Path(__file__).resolve().parents[1]
        callers = set()
        for directory in ("pagefolio", "plugins"):
            for path in (root / directory).rglob("*.py"):
                relative = path.relative_to(root).as_posix()
                module = relative.removesuffix(".py").replace("/", ".")
                callers.update(
                    (relative, caller)
                    for caller in self._callers(
                        path.read_text(encoding="utf-8-sig"), module
                    )
                )
        expected = {("pagefolio/app.py", "PDFEditorApp._persist_settings")}
        assert callers
        assert callers == expected


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
    isolated = create_isolated_app()
    try:
        yield isolated.settings_path
    finally:
        isolated.close()


class TestScenarioIsolation:
    @pytest.mark.parametrize(
        ("scenario", "status"),
        [("read-corrupt", "corrupt"), ("read-unreadable", "unreadable")],
    )
    def test_scenario_classifies_real_load_and_preserves_originals(
        self, scenario, status
    ):
        isolated = create_isolated_app(scenario)
        with isolated:
            assert isolated.app._settings_load_status == status
            assert Path(settings_mod._get_base_dir()) == isolated.base
            assert Path(plugins_mod._get_plugins_dir()) == isolated.plugins_path
        assert isolated.originals_before == isolated.originals_after
        assert not isolated.base.exists()

    @pytest.mark.parametrize("scenario", ["save-write", "save-replace"])
    def test_save_fault_only_changes_memory_then_recovers(self, scenario):
        isolated = create_isolated_app(scenario)
        with isolated:
            original = isolated.settings_path.read_bytes()
            app = isolated.app
            app.settings["thumb_page_size"] = 30
            assert app._persist_settings() is False
            assert isolated.settings_path.read_bytes() == original
            assert not Path(str(isolated.settings_path) + ".tmp").exists()
            assert app.settings["thumb_page_size"] == 30
            isolated.fault_enabled = False
            assert app._persist_settings() is True
            assert settings_mod._load_settings()["thumb_page_size"] == 30

    def test_prompt_and_plugin_resolvers_never_load_real_plugins(self, monkeypatch):
        loaded = []
        original_load = plugins_mod.PluginManager.load_plugin

        def observe(manager, plugin_id, path, *args, **kwargs):
            loaded.append(Path(path))
            return original_load(manager, plugin_id, path, *args, **kwargs)

        monkeypatch.setattr(plugins_mod.PluginManager, "load_plugin", observe)
        with create_isolated_app() as isolated:
            assert settings_mod.load_custom_prompt({}) == ""
            assert settings_mod.load_summary_prompt({}) == ""
            assert settings_mod.save_prompt_file(
                settings_mod.CUSTOM_PROMPT_FILE, "isolated OCR"
            )
            assert settings_mod.save_prompt_file(
                settings_mod.SUMMARY_PROMPT_FILE, "isolated summary"
            )
            assert (isolated.base / settings_mod.CUSTOM_PROMPT_FILE).read_text(
                encoding="utf-8"
            ) == "isolated OCR"
            assert (isolated.base / settings_mod.SUMMARY_PROMPT_FILE).read_text(
                encoding="utf-8"
            ) == "isolated summary"
            assert loaded == []

    def test_partial_initialization_exception_cleans_root_and_temporary(
        self, monkeypatch
    ):
        from pagefolio.app import PDFEditorApp

        def fail_build(app):
            app.root.after(10000, lambda: None)
            raise RuntimeError("isolated build failure")

        monkeypatch.setattr(PDFEditorApp, "_build_ui", fail_build)
        isolated = create_isolated_app("read-corrupt")
        with pytest.raises(RuntimeError, match="isolated build failure"):
            isolated.start()
        assert not isolated.base.exists()
        assert isolated.originals_before == isolated.originals_after


class TestConfigAcceptance:
    def test_corrupt_two_failures_rebuild_edit_recovery_and_exit(self, monkeypatch):
        with create_isolated_app("read-corrupt", visible=True) as isolated:
            app, root = isolated.app, isolated.root
            original = isolated.settings_path.read_bytes()
            app.doc = fitz.open()
            app.doc.new_page()
            app.edit_mode = True
            app.selected_pages = {0}
            app._rotate_selected(90)
            doc, undo, redo = app.doc, app._undo_stack, app._redo_stack
            history = tuple(undo)
            root.update()
            clock = [0.0]
            monkeypatch.setattr("pagefolio.app.time.monotonic", lambda: clock[0])
            app._config_notices[0]["shown_at"] = 0.0
            clock[0] = 4.0
            with monkeypatch.context() as fault:
                fault.setattr("pagefolio.app._save_settings", lambda values: False)
                values = dict(app.settings, font_size=14)
                app._apply_settings(values)
                app._apply_settings(values)
                app._toggle_lang()
            root.update_idletasks()
            assert app.lang == "en"
            assert [n["message_key"] for n in app._config_notices] == [
                "config_load_corrupt"
            ] + ["config_save_failed"] * 3
            ids = [n["event_id"] for n in app._config_notices]
            assert len(set(ids)) == 4
            assert app._config_notices[0]["remaining_ms"] == 6000
            assert app._toast._msg_var.get() == app._t("config_load_corrupt")
            assert isolated.settings_path.read_bytes() == original
            assert (
                app.doc is doc and app._undo_stack is undo and app._redo_stack is redo
            )
            assert tuple(undo) == history and app.selected_pages == {0}
            assert app.doc[0].rotation == 90
            seen = []
            while app._config_notices:
                seen.append(app._config_notices[0]["event_id"])
                app._toast.dismiss("config_notice", reason="user")
                root.update_idletasks()
            assert seen == ids
            assert app._persist_settings() is True
            assert not app._settings_autosave_blocked
            assert settings_mod._load_settings()["font_size"] == 14
            app._undo()
            assert app.doc[0].rotation == 0
            app._redo()
            assert app.doc[0].rotation == 90
            monkeypatch.setattr("pagefolio.app.messagebox.askyesno", lambda *args: True)
            app._quit()
            assert doc.is_closed

    @pytest.mark.parametrize("recover_explicitly", [False, True])
    def test_exit_no_first_failure_next_exit_and_explicit_flag_reset(
        self, monkeypatch, recover_explicitly
    ):
        with create_isolated_app("save-replace") as isolated:
            app, root = isolated.app, isolated.root
            app.doc = fitz.open()
            app.doc.new_page()
            doc = app.doc
            original = isolated.settings_path.read_bytes()
            monkeypatch.setattr(
                "pagefolio.app.messagebox.askyesno", lambda *args: False
            )
            app._quit()
            assert not app._settings_exit_save_failed and not app._config_notices
            monkeypatch.setattr("pagefolio.app.messagebox.askyesno", lambda *args: True)
            app._quit()
            assert app._settings_exit_save_failed and root.winfo_exists()
            assert app.doc is doc and not doc.is_closed
            assert len(app._config_notices) == 1
            monkeypatch.setattr(
                "pagefolio.app.messagebox.askyesno", lambda *args: False
            )
            app._quit()
            assert app._settings_exit_save_failed and root.winfo_exists()
            if recover_explicitly:
                isolated.fault_enabled = False
                assert app._persist_settings() is True
                assert not app._settings_exit_save_failed
                isolated.fault_enabled = True
                monkeypatch.setattr(
                    "pagefolio.app.messagebox.askyesno", lambda *args: True
                )
                app._quit()
                assert app._settings_exit_save_failed and root.winfo_exists()
                app._quit()
            else:
                monkeypatch.setattr(
                    "pagefolio.app.messagebox.askyesno", lambda *args: True
                )
                app._quit()
                assert isolated.settings_path.read_bytes() == original
            assert doc.is_closed

    def test_unreadable_permission_recovery_stays_blocked_until_restart(self):
        isolated = create_isolated_app("read-unreadable")
        with isolated:
            app = isolated.app
            original = isolated.settings_path.read_bytes()
            isolated.fault_enabled = False
            app.settings["lang"] = "en"
            assert app._persist_settings() is False
            assert [n["message_key"] for n in app._config_notices] == [
                "config_load_unreadable",
                "config_save_blocked_unreadable",
            ]
            assert isolated.settings_path.read_bytes() == original
            app._quit()
            assert app._settings_exit_save_failed is False
            assert app._config_notice_seq == 2
            from tkinterdnd2 import TkinterDnD

            from pagefolio.app import PDFEditorApp

            isolated.root = TkinterDnD.Tk()
            isolated.root.withdraw()
            isolated.app = PDFEditorApp(isolated.root)
            assert isolated.app._settings_load_status == "ok"
            assert isolated.app.lang == "ja"
            assert isolated.app._persist_settings() is True

    def test_hundred_failures_all_consume_fifo_with_nested_modal_and_operation(
        self, notice_app
    ):
        app = notice_app
        app.root.grab = object()
        for _index in range(100):
            app._enqueue_config_notice("config_save_failed")
        ids = [notice["event_id"] for notice in app._config_notices]
        app._schedule_config_notice()
        app.root.advance(20000)
        assert all(n["remaining_ms"] == 10000 for n in app._config_notices)
        app.root.grab = None
        app.root.advance(100)
        app.root.advance(4000)
        for category in ("save_file", "print"):
            app._toast.show(category, "操作通知", retry_cb=lambda: None)
            app.root.advance(20000)
            assert app._config_notices[0]["remaining_ms"] == 6000
            app._toast.dismiss(category)
            app.root.advance()
        app.root.grab = object()
        app.root.advance(100)
        remaining = app._config_notices[0]["remaining_ms"]
        app.root.advance(20000)
        app.root.grab = object()
        app.root.advance(20000)
        assert app._config_notices[0]["remaining_ms"] == remaining
        app.root.grab = None
        app.root.advance(100)
        seen = []
        while app._config_notices:
            current = app._config_notices[0]
            seen.append(current["event_id"])
            app.root.advance(current["remaining_ms"])
        assert seen == ids and len(set(seen)) == 100
        assert not app.root.pending


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
            assert app._toast._active_category is None
            root.deiconify()
            root.update()
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
            focused = root.focus_get()
            app._show_next_config_notice()
            root.update_idletasks()
            if focused is not None:
                assert root.focus_get() is focused
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
