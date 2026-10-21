"""通常pytest外で本番5秒→10秒と閉鎖後15秒を実測する。"""

import importlib.util
import json
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path
from uuid import uuid4


def _require(condition, message="本番通知の受入不合格"):
    if not condition:
        raise RuntimeError(message)


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "notice_scenarios", root / "tests/test_startup_windows.py"
    )
    scenarios = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scenarios)
    from pagefolio.startup_win32 import Win32Backend, _bind

    before = scenarios._fingerprints()
    fixture = root / ".planning/tmp" / ("notice-production-" + uuid4().hex)
    fixture.mkdir(parents=True)
    namespace = uuid4().hex
    children = []
    backend = Win32Backend(namespace)
    try:
        owner, owner_path = scenarios._spawn(fixture, namespace, "initializing-owner")
        children.append(owner)
        scenarios._wait_file(owner, owner_path / "ready")
        child, child_path = scenarios._spawn(
            fixture, namespace, "notice-production-timeout"
        )
        children.append(child)
        out, err = child.communicate(timeout=17)
        _require(child.returncode == 0, err)
        result = json.loads(out.strip().splitlines()[-1])
        audit = json.loads((child_path / "resource-audit.json").read_text())
        snapshot = audit["snapshot"]
        _require(result["result"] == "expired" and result["constructed"] == 0)
        _require(14900 <= result["elapsed"] <= 15500)
        _require(snapshot["deadline_tick"] - snapshot["shown_tick"] == 10000)
        _require(
            audit["foreground_before_show"] == audit["foreground_after_show"]
            and audit["foreground_before_close"] == audit["foreground_after_close"]
        )
        foreground = _bind(backend.api.u, "GetForegroundWindow", wt.HWND)
        observed = set()
        started = time.monotonic()
        while time.monotonic() - started < 15:
            observed.add(foreground())
            _require(not backend.api.IsWindow(snapshot["hwnd"]))
            _require(child.poll() is not None)
            time.sleep(0.05)
        _require(not backend.api.IsWindow(snapshot["hwnd"]))
        owner.communicate(timeout=2)
        _require(owner.returncode == 0)
        _require(scenarios._fingerprints() == before)
        record = {
            "result": result,
            "audit": audit,
            "fixture": str(fixture),
            "post_close_observation_seconds": time.monotonic() - started,
            "post_close_foreground_hwnds": sorted(observed),
            "remaining_children": 0,
            "originals_unchanged": True,
            "stderr": err,
        }
        output = Path(__file__).with_name("04-04-NOTICE-RUNTIME.json")
        output.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "pass",
                    "elapsed_ms": result["elapsed"],
                    "output": str(output),
                }
            )
        )
    finally:
        scenarios._reclaim(children)
        backend.close()
        _require(scenarios._fingerprints() == before)


if __name__ == "__main__":
    main()
