"""修正箇所だけを無効化した隔離コピーと実製品で、同じ再現を比較する。"""

# ruff: noqa: S101

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run():
    repo = Path(__file__).resolve().parents[4]
    source_path = repo / "pagefolio/startup_wake.py"
    helper = repo / "tests/startup_wake_child.py"
    source = source_path.read_text(encoding="utf-8")
    site = "self._api.PostThreadMessageW(self._thread_id, 0, 0, 0)"
    assert source.count(site) == 1
    wrapper = (
        "import importlib.util,runpy,sys;"
        "spec=importlib.util.spec_from_file_location("
        "'pagefolio.startup_wake',sys.argv[1]);"
        "module=importlib.util.module_from_spec(spec);"
        "sys.modules[spec.name]=module;spec.loader.exec_module(module);"
        "sys.argv=[sys.argv[2],'wake'];runpy.run_path(sys.argv[0],run_name='__main__')"
    )
    results = {}
    with tempfile.TemporaryDirectory(prefix="pf-wake-guardrail-") as temp:
        mutant = Path(temp) / "startup_wake.py"
        mutant.write_text(source.replace(site, "True"), encoding="utf-8")
        for label, module in (("post_removed", mutant), ("product", source_path)):
            child = subprocess.run(  # noqa: S603
                [sys.executable, "-c", wrapper, str(module), str(helper)],
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            assert child.returncode == 0, child.stdout + child.stderr
            data = json.loads(child.stdout)
            assert data["removed"] == 1 and data["worker_stopped"], data
            results[label] = data
    assert results["post_removed"]["first_beat_after_ghost_ms"] > 600, results
    assert results["product"]["first_beat_after_ghost_ms"] < 400, results
    assert results["post_removed"]["posted"] == 0, results
    assert results["product"]["posted"] > 0, results
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
