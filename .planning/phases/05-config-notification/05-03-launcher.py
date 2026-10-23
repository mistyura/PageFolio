"""非表示で合図を待ち、前景条件を変えず既存の検証runnerを起動する。"""

import json
import subprocess
import sys
import time
from pathlib import Path

signal = Path(sys.argv[1]).resolve()
status_path = signal.with_suffix(".status.json")
runner = Path(__file__).with_name("05-02-verify.py")
deadline = time.monotonic() + 120


def save(state, **extra):
    status_path.write_text(
        json.dumps({"state": state, **extra}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if signal.exists():
    save("error", error="既存signalの再利用は禁止")
    raise SystemExit(1)
save("waiting", signal=str(signal), deadline_seconds=120)
while not signal.exists():
    if time.monotonic() >= deadline:
        save("signal_timeout")
        raise SystemExit(1)
    time.sleep(0.1)
command = [sys.executable, str(runner), *sys.argv[2:]]
save("running", command=command)
result = subprocess.run(  # noqa: S603 - 承認済みrunnerと親指定の検証引数だけを使う
    command,
    cwd=runner.parents[3],
    creationflags=subprocess.CREATE_NO_WINDOW,
)
save("completed", exit_code=result.returncode)
