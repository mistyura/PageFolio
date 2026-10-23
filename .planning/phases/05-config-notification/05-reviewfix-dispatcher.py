"""レビュー修正の固定runnerを非表示で逐次起動する。"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

PHASE = Path(__file__).resolve().parent
ROOT = PHASE.parents[2]
TEMP = Path("C:/Users/shdwf/AppData/Local/Temp").resolve()
QUEUE = PHASE / "05-reviewfix-dispatch"
QUEUE.mkdir(exist_ok=True)
completed = set()
deadline = time.monotonic() + 3600
while time.monotonic() < deadline and not (QUEUE / "stop").exists():
    for source in sorted(QUEUE.glob("job-*.json")):
        if source.name.endswith(".result.json") or source.name in completed:
            continue
        job = json.loads(source.read_text(encoding="utf-8"))
        evidence = Path(job["evidence"]).resolve()
        temporary = Path(job["temporary"]).resolve()
        selectors = job["selectors"]
        if evidence.parent != PHASE or not evidence.name.startswith("05-reviewfix-"):
            raise ValueError("証拠先が担当範囲外")
        if temporary.parent != TEMP or not temporary.name.startswith("pf_reviewfix_"):
            raise ValueError("一時先が担当範囲外")
        if not isinstance(selectors, list) or not all(
            isinstance(item, str)
            and re.fullmatch(r"tests/[A-Za-z0-9_./:\[\]-]+", item)
            and ".." not in item
            for item in selectors
        ):
            raise ValueError("selectorが不正")
        command = [
            sys.executable,
            str(PHASE / "05-02-verify.py"),
            str(evidence),
            str(temporary),
            *selectors,
        ]
        result = subprocess.run(  # noqa: S603 - 固定runnerと検証済みpath/selectorのみ
            command, cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW
        )
        (QUEUE / (source.stem + ".result.json")).write_text(
            json.dumps({"exit_code": result.returncode}), encoding="utf-8"
        )
        completed.add(source.name)
(QUEUE / "stopped").write_text("stopped", encoding="utf-8")
