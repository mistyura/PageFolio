# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""エントリーポイント — python -m pagefolio"""

import sys


def main(*, backend_factory=None):
    coordinator = None
    root = None
    try:
        if sys.platform == "win32":
            from pagefolio.startup_win32 import Win32Backend, _tick_ms

            started_tick = _tick_ms()
            from pagefolio.startup_control import StartupCoordinator

            coordinator = StartupCoordinator((backend_factory or Win32Backend)())
            outcome = coordinator.claim()
            if not outcome.primary:
                if outcome.result == "existing":
                    outcome = coordinator.request_activation(started_tick)
                if not outcome.primary:
                    if outcome.result not in {"completed", "foreground_denied"}:
                        coordinator.backend.show_notice(outcome.result)
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
            root.after_idle(lambda: coordinator.attach_tk(root))
        root.mainloop()
        return "primary"
    finally:
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
    main()
