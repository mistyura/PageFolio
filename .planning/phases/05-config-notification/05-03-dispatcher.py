"""固定の検証runnerだけを非表示で逐次起動する。任意commandは受け付けない。"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

PHASE = Path(__file__).resolve().parent
ROOT = PHASE.parents[2]
TEMP = Path("C:/Users/shdwf/AppData/Local/Temp").resolve()
QUEUE = PHASE / "05-03-dispatch"
QUEUE.mkdir(exist_ok=True)
STATUS = QUEUE / "status.json"
RUNNER = PHASE / "05-02-verify.py"
deadline = time.monotonic() + 1800
completed = {
    result.name.removesuffix(".result.json") + ".json"
    for result in QUEUE.glob("job-*.result.json")
}


def save(state, **extra):
    STATUS.write_text(
        json.dumps({"state": state, **extra}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


save("waiting_for_start", signal=str(QUEUE / "resume"))
while not (QUEUE / "resume").exists():
    if (QUEUE / "stop").exists() or time.monotonic() >= deadline:
        save("stopped_before_start")
        raise SystemExit(0)
    time.sleep(0.2)
save("ready")
while time.monotonic() < deadline and not (QUEUE / "stop").exists():
    for job_path in sorted(QUEUE.glob("job-*.json")):
        if job_path.name.endswith(".result.json") or job_path.name in completed:
            continue
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
            if set(job) != {"evidence", "temporary", "selectors"}:
                raise ValueError("jobの項目が不正")
            evidence = Path(job["evidence"]).resolve()
            temporary = Path(job["temporary"]).resolve()
            selectors = job["selectors"]
            if evidence.parent != PHASE or not evidence.name.startswith("05-03-"):
                raise ValueError("証拠先が担当範囲外")
            if temporary.parent != TEMP or not temporary.name.startswith("pf_0503_"):
                raise ValueError("専用一時先が担当範囲外")
            if not isinstance(selectors, list) or not all(
                isinstance(item, str)
                and re.fullmatch(r"tests/[A-Za-z0-9_./:\[\]-]+", item)
                and ".." not in item
                for item in selectors
            ):
                raise ValueError("pytest selectorが不正")
            command = [
                sys.executable,
                str(RUNNER),
                str(evidence),
                str(temporary),
                *selectors,
            ]
            save("running", job=job_path.name, command=command)
            result = subprocess.run(  # noqa: S603 - 固定runnerと検証済みpath/selectorのみ
                command, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW
            )
            (QUEUE / (job_path.stem + ".result.json")).write_text(
                json.dumps({"exit_code": result.returncode}), encoding="utf-8"
            )
            completed.add(job_path.name)
            save("ready", completed=sorted(completed))
        except Exception as e:
            save("job_error", job=job_path.name, error=repr(e))
            raise
    time.sleep(0.2)
save("stopped", completed=sorted(completed))
