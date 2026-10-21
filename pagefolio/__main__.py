# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""エントリーポイント — python -m pagefolio"""

import sys


def main(*, backend_factory=None, notice_backend_factory=None):
    coordinator = None
    backend = None
    root = None
    focus = None
    try:
        if sys.platform == "win32":
            from pagefolio.startup_control import StartupCoordinator
            from pagefolio.startup_notice import show_startup_initialization_failure
            from pagefolio.startup_win32 import Win32Backend, _tick_ms

            try:
                started_tick = _tick_ms()
                backend = (backend_factory or Win32Backend)()
                coordinator = StartupCoordinator(backend)
            except OSError:
                # 例外本文は利用者向け案内や診断へ渡さない。
                close_failed = False
                if backend is not None:
                    try:
                        backend.close()
                    except Exception:
                        close_failed = True
                notice = show_startup_initialization_failure(
                    backend_factory=notice_backend_factory
                )
                return (
                    "notification_unavailable"
                    if close_failed or notice.result == "notification_unavailable"
                    else "check_failed"
                )
            outcome = coordinator.claim()
            if not outcome.primary:
                if outcome.result == "existing":
                    outcome = coordinator.request_activation(started_tick)
                if not outcome.primary:
                    if outcome.result not in {"completed", "foreground_denied"}:
                        notice = coordinator.backend.show_notice(outcome.result)
                        if (
                            getattr(notice, "result", None)
                            == "notification_unavailable"
                        ):
                            return "notification_unavailable"
                    return outcome.result

        # 所有権を確定するまで、編集画面やプラグインを import しない。
        import tkinter as tk

        from pagefolio.app import PDFEditorApp
        from pagefolio.file_drop import _setup_file_drop

        try:
            from tkinterdnd2 import TkinterDnD
        except ImportError:
            root_class = tk.Tk
        else:
            root_class = TkinterDnD.Tk
        # __init__ が途中で例外になっても、作成済みTkをfinallyで破棄する。
        root = root_class.__new__(root_class)
        if coordinator:
            coordinator.root = root
        root.__init__()
        app = PDFEditorApp(root)
        _setup_file_drop(app)
        if coordinator:
            from pagefolio.startup_focus import FocusRestorer

            focus = FocusRestorer(app, coordinator.backend)
            app._startup_focus = focus
            coordinator.backend.focus_restorer = focus
            root.after_idle(lambda: coordinator.attach_tk(root))
        root.mainloop()
        return "primary"
    finally:
        if focus is not None:
            focus.close()
        if root is not None:
            try:
                if root.winfo_exists():
                    root.destroy()
            except Exception as e:
                if coordinator:
                    coordinator.backend.logger.debug("起動rootの後始末: %s", e)
        if coordinator:
            coordinator.close()


if __name__ == "__main__":
    if main() == "notification_unavailable":
        sys.exit(1)
