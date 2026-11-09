"""W05b限定診断。既存隔離harnessのpeerと実foregroundを対応づける。"""

import argparse
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests import release_uat_support as support  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to((ROOT / ".planning/tmp").resolve()):
        parser.error("既存harnessの隔離runが必要です")
    output = run / "w05b-observation.json"
    if output.exists():
        parser.error("観測原本が存在します。上書きしません")
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    pid = manifest["expected_owner"]["pid"]
    records, errors = [], []
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            try:
                foreground = support.foreground_info()
                records.append(
                    {
                        "utc": datetime.now(timezone.utc).isoformat(),
                        "monotonic_ns": time.monotonic_ns(),
                        "hwnd": foreground["hwnd"],
                        "pid": foreground["pid"],
                    }
                )
            except Exception as error:
                errors.append(type(error).__name__)
            stop.wait(0.05)

    before = support.windows_of(pid)
    thread = threading.Thread(target=sample)
    thread.start()
    result = None
    try:
        time.sleep(0.5)
        # 実行ファイルとharnessは固定、runは上で隔離領域内に検証済み。
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(ROOT / "tests/test_startup_windows.py"),
                "--uat",
                "peer",
                "--run",
                str(run),
                "--entry",
                "module",
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=25,
        )
        (run / "w05b-peer.stdout.txt").write_bytes(result.stdout)
        (run / "w05b-peer.stderr.txt").write_bytes(result.stderr)
        time.sleep(4)
    finally:
        stop.set()
        thread.join()
        with output.open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "purpose": "source-diagnostic",
                    "acceptance": False,
                    "run": str(run),
                    "primary_pid": pid,
                    "windows_before": before,
                    "windows_after": support.windows_of(pid),
                    "samples": records,
                    "observation_errors": errors,
                    "peer_exit": result.returncode if result is not None else None,
                },
                stream,
                ensure_ascii=False,
                indent=2,
            )
    print(
        json.dumps({"output": str(output), "samples": len(records), "errors": errors})
    )
    return result.returncode if result is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
