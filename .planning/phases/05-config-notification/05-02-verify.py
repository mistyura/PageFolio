"""承認済み非表示runnerの前景確認・証拠保存を再利用する単発検証。"""

import json
import runpy
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
helpers = runpy.run_path(
    str(
        ROOT / ".planning/debug/simultaneous-owner-missing-evidence/run_resume_check.py"
    )
)
evidence = Path(sys.argv[1]).resolve()
temporary = Path(sys.argv[2]).resolve()
evidence.mkdir()
status = {"state": "preflight"}


def save_status():
    (evidence / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


save_status()
try:
    helpers["preflight"](evidence / "preflight.json")
    if temporary.exists():
        raise RuntimeError("既存basetempの再利用は禁止")
    command = [str(ROOT / ".venv/Scripts/python.exe"), "-m", "pytest"]
    command.extend(sys.argv[3:])
    command.extend(["-x", "-q", "--tb=short", "--basetemp=" + str(temporary)])
    status.update(state="running", command=command)
    save_status()
    started = time.monotonic()
    with (evidence / "pytest.txt").open("xb") as output:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    status.update(exit_code=result.returncode, seconds=time.monotonic() - started)
    status["artifacts"] = helpers["preserve"](temporary, evidence / "artifacts")
    status["state"] = "passed" if result.returncode == 0 else "failed"
    save_status()
except Exception as e:
    status.update(state="error", error=repr(e))
    save_status()
    raise
