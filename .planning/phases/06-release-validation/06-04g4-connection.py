"""実EXE接続driverに読み取り専用の前景時系列だけを追加する。"""

import importlib.util
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

driver = Path(__file__).parent / "06-04-drivers/conn_session.py"
spec = importlib.util.spec_from_file_location("g4_connection", driver)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.Session.launch_peer


def observed_peer(self, run, result):
    samples, errors = [], []
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            try:
                foreground = module.S.foreground_info()
                samples.append(
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "monotonic_ns": time.monotonic_ns(),
                        "hwnd": foreground["hwnd"],
                        "pid": foreground["pid"],
                    }
                )
            except Exception as error:
                errors.append(type(error).__name__)
            stop.wait(0.05)

    thread = threading.Thread(target=sample)
    thread.start()
    try:
        original(self, run, result)
    finally:
        stop.set()
        thread.join()
        result["foreground_trace"] = samples
        result["foreground_trace_errors"] = errors
        result["foreground_trace_interval_ms"] = 50


if __name__ == "__main__":
    module.Session.launch_peer = observed_peer
    module.main()
