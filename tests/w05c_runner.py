"""W05c v3の単発採取。チャット回答を待たず機械原本を固定する。"""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tests.w05c_evidence import digest, save

ROOT = Path(__file__).resolve().parents[1]
PHASE = Path(".planning/phases/06-release-validation")
SCHEMA = "w05c-v3"
INPUTS = (
    "tests/w05c_runner.py",
    "tests/w05c_evidence.py",
    "tests/test_startup_windows.py",
    str(PHASE / "06-05-w05c-v3.cjs"),
    str(PHASE / "06-05-w05c-evidence.cjs"),
    str(PHASE / "06-05-record-w05c-python.cjs"),
)
BUDGET = {"peer": 20, "snapshot": 10, "inspect": 3, "collect": 20, "margin": 5}
TERMINAL = {
    "watchdog_enter",
    "stop_enter",
    "cleanup_enter",
    "root_destroy_enter",
    "observer_closed",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan(path, root=ROOT):
    path = path.resolve()
    assert path.is_relative_to((root / ".planning").resolve()), "planはrepo内だけ"
    plan = read(path)
    assert plan["schema"] == SCHEMA and plan["entry"] == "script"
    assert plan["permissions_ready"] is True and plan["budget_evidence"], (
        "起動前準備が未完了"
    )
    assert plan["budgets"] == BUDGET, "既存commandの上限を短縮/延長しない"
    observation = plan["observation_seconds"]
    assert isinstance(observation, (int, float)) and math.isfinite(observation)
    assert 10 <= observation <= 30, "観察区間が範囲外"
    assert set(plan["source_inputs"]) == set(INPUTS), "採取入力集合の不一致"
    for source, expected in plan["source_inputs"].items():
        assert digest(root / source) == expected, f"採取入力変更: {source}"
    return {
        **plan,
        "plan_sha256": digest(path),
        "original_json": path.read_bytes().decode("utf-8"),
    }


def read_events(fixture):
    raw = (fixture / "w05c-events.jsonl").read_bytes()
    assert raw.endswith(b"\n"), "不完全なイベント末尾"
    return [json.loads(line) for line in raw.splitlines()]


def identity(run, manifest):
    assert manifest.get("w05c_schema") == SCHEMA and manifest["entry"] == "script"
    assert manifest["case"] == "native-quit" and not manifest.get("diagnostic_only")
    expected = manifest["expected_owner"]
    assert expected["manual"] is True
    fixture = run / "uat-owner-native-quit"
    assert Path(manifest["fixture"]).resolve() == fixture.resolve()
    plan = manifest["w05c_plan"]
    assert read(fixture / "w05c-plan.json") == plan
    peers = {}
    for label in ("during_confirm", "after_no"):
        p = fixture / f"w05c-peer-{label}.json"
        if p.exists():
            peers[label] = read(p)["dir"]
    return {
        "schema": SCHEMA,
        "run_id": run.name,
        "pid": expected["pid"],
        "process_created": expected["process_created"],
        "manual": True,
        "entry": "script",
        "plan_sha256": plan["plan_sha256"],
        "observation_seconds": plan["observation_seconds"],
        "peers": peers,
    }


def validate_machine(events, snapshot, final, ident, stage):
    node = shutil.which("node")
    assert node, "nodeが必要"
    checked = subprocess.run(  # noqa: S603 — 固定validatorにJSONだけを渡す。
        [node, str(ROOT / PHASE / "06-05-w05c-v3.cjs")],
        input=json.dumps(
            {
                "events": events,
                "snapshot": snapshot,
                "final": final,
                "identity": ident,
                "stage": stage,
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        timeout=5,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr
    return json.loads(checked.stdout)


def machine_checkpoint(run, manifest, stage):
    """回答と無関係な同ownerのsnapshotを1回だけ固定する。"""
    from pagefolio.startup_win32 import Win32Backend

    assert stage in {"before_peer", "before_stop"}
    target = run / f"w05c-v3-{stage}.json"
    assert not target.exists(), "同じ段階は再実行しない"
    ident = identity(run, manifest)
    fixture = Path(manifest["fixture"])
    backend = Win32Backend(manifest["namespace"])
    try:
        with backend._validate_peer(ident["pid"], ident["process_created"]):
            request = {"request_id": uuid4().hex, "stage": stage}
            save(fixture / "w05c-snapshot-request.json", request)
            until = time.monotonic() + 3
            snapshot = None
            while time.monotonic() < until:
                p = fixture / "w05c-pre-collection.json"
                if (
                    p.exists()
                    and (value := read(p))["request_id"] == request["request_id"]
                ):
                    snapshot = value
                    break
                time.sleep(0.02)
            assert snapshot is not None, "snapshot応答なし"
            raw = (fixture / "w05c-events.jsonl").read_bytes().splitlines(keepends=True)
            prefix = b"".join(raw[: snapshot["events"]])
            assert hashlib.sha256(prefix).hexdigest() == snapshot["log_sha256"]
            assert digest(fixture / "quit-cancelled") == snapshot["marker_sha256"]
            result = validate_machine(
                [json.loads(line) for line in prefix.splitlines()],
                snapshot,
                None,
                ident,
                stage,
            )
            record = {
                "ok": True,
                "schema": SCHEMA,
                "run_id": run.name,
                "identity": ident,
                "snapshot": snapshot,
                "result": result,
            }
            save(target, record)
            return record
    except Exception as e:
        if not target.exists():
            save(
                target,
                {"ok": False, "schema": SCHEMA, "run_id": run.name, "error": str(e)},
            )
        raise
    finally:
        backend.close()


def guard_after_no_peer(run, manifest):
    checked = read(run / "w05c-v3-before_peer.json")
    assert checked["ok"] is True and checked["identity"] == identity(run, manifest)
    events = read_events(Path(manifest["fixture"]))
    assert not any(e["event"] in TERMINAL for e in events), "回収開始後のpeer禁止"
    assert time.monotonic() + BUDGET["peer"] < checked["result"]["due_monotonic"], (
        "peer予算不足"
    )
    # 失敗したpeerも再実行しない。別processの二重起動も排除する。
    with (run / "w05c-v3-peer-started").open("x", encoding="utf-8") as stream:
        stream.write(checked["identity"]["plan_sha256"])


def run_collection(driver, plan, *, now=time.monotonic, sleep=time.sleep):
    """仮想時計/fake driverでも同じ単発状態遷移を検査できる。"""
    collection_started = False
    try:
        before = now()
        driver.start()
        events = driver.events()
        reg = next(e for e in events if e["event"] == "watchdog_registered")
        assert reg["clock"] == time.get_clock_info("monotonic").implementation
        assert before <= reg["registered_monotonic"] <= now(), (
            "時計基準/登録時刻の不一致"
        )
        assert (
            reg["delay_ms"] == 120000
            and reg["due_monotonic"] == reg["registered_monotonic"] + 120
        )
        due = reg["due_monotonic"]
        after_budget = (
            2 * BUDGET["snapshot"]
            + BUDGET["peer"]
            + BUDGET["inspect"]
            + BUDGET["collect"]
            + BUDGET["margin"]
            + plan["observation_seconds"]
        )

        def waiting_for(name, reserve):
            while True:
                current = driver.events()
                assert not any(
                    e["event"] in TERMINAL or e["event"].endswith("_error")
                    for e in current
                ), "先行回収/観測エラー"
                assert now() + reserve < due, "残時間不足"
                found = next((e for e in current if e["event"] == name), None)
                if found:
                    return found
                sleep(0.05)

        waiting_for("native_shown", after_budget + BUDGET["peer"])
        assert not any(e["event"] == "native_no" for e in driver.events()), (
            "確認中peer以前のNo"
        )
        driver.peer()
        marker = waiting_for("marker_created", after_budget)
        driver.check("before_peer")
        driver.peer()
        # peer採取時間も観察時間に含めるが、最低観察区間を切り詰めない。
        while now() < marker["monotonic"] + plan["observation_seconds"]:
            waiting_for(
                "marker_created",
                BUDGET["snapshot"]
                + BUDGET["inspect"]
                + BUDGET["collect"]
                + BUDGET["margin"],
            )
            sleep(0.05)
        driver.check("before_stop")
        driver.inspect()
        assert now() + BUDGET["collect"] + BUDGET["margin"] < due, "回収予算不足"
        collection_started = True
        driver.collect()
        return driver.seal()
    except Exception as e:
        try:
            driver.failed(e)
        finally:
            if not collection_started:
                # 既知ownerだけを回収。失敗したstopの再試行はしない。
                driver.recover()
        raise


class LocalDriver:
    def __init__(self, plan_path, plan, run):
        self.plan_path, self.plan, self.run = plan_path, plan, run
        self.fixture = run / "uat-owner-native-quit"

    def command(self, action, extra=(), timeout=20):
        result = subprocess.run(  # noqa: S603 — shellなしの固定harnessコマンド。
            [
                sys.executable,
                str(ROOT / "tests/test_startup_windows.py"),
                "--uat",
                action,
                "--run",
                str(self.run),
                "--entry",
                "script",
                *extra,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=timeout,
            check=False,
        )
        if self.run.exists():
            with (self.run / "w05c-v3-commands.jsonl").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(
                    json.dumps(
                        {
                            "action": action,
                            "extra": list(extra),
                            "code": result.returncode,
                            "utc": datetime.now(UTC).isoformat(),
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                        }
                    )
                    + "\n"
                )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def start(self):
        self.command(
            "start", ("--case", "native-quit", "--w05c-plan", str(self.plan_path))
        )
        until = time.monotonic() + 1
        while time.monotonic() < until:
            path = self.fixture / "w05c-events.jsonl"
            if path.exists() and any(
                e["event"] == "watchdog_registered" for e in self.events()
            ):
                return
            time.sleep(0.02)
        raise AssertionError("ownerのwatchdog登録記録がない")

    def events(self):
        return read_events(self.fixture)

    def peer(self):
        self.command("peer", timeout=BUDGET["peer"])

    def check(self, stage):
        self.command(
            "w05c-machine-check", ("--stage", stage), timeout=BUDGET["snapshot"]
        )

    def inspect(self):
        self.command("inspect", timeout=BUDGET["inspect"])

    def collect(self):
        self.command("stop", timeout=BUDGET["collect"])

    def seal(self):
        manifest = read(self.run / "manifest.json")
        ident = identity(self.run, manifest)
        checked = read(self.run / "w05c-v3-before_stop.json")
        final = read(self.fixture / "w05c-observer-final.json")
        assert digest(self.fixture / "w05c-events.jsonl") == final["sha256"]
        validate_machine(self.events(), checked["snapshot"], final, ident, "final")
        assert read(self.run / "w05c-collection-after/owner.json")["exited"] is True
        assert read(self.run / "inspection.json")["originals_unchanged"] is True
        files = {
            str(p.relative_to(self.run)): digest(p)
            for p in self.run.rglob("*")
            if p.is_file()
        }
        record = {
            "schema": SCHEMA,
            "status": "machine_collected_pending_answer",
            "run_id": self.run.name,
            "plan_sha256": self.plan["plan_sha256"],
            "identity": ident,
            "completed_at": datetime.now(UTC).isoformat(),
            "files": files,
        }
        assert not (self.run / "w05c-v3-collection.json").exists()
        save(self.run / "w05c-v3-collection.json", record)
        return record

    def failed(self, error):
        if self.run.exists():
            save(
                self.run / "w05c-v3-failed.json",
                {
                    "schema": SCHEMA,
                    "error": str(error),
                    "utc": datetime.now(UTC).isoformat(),
                },
            )

    def recover(self):
        manifest_path = self.run / "manifest.json"
        if manifest_path.exists() and read(manifest_path).get("expected_owner"):
            try:
                self.collect()
            except Exception as e:
                save(self.run / "w05c-v3-recovery-failed.json", {"error": str(e)})


def main():
    parser = argparse.ArgumentParser(description="W05cの単発採取。事前planが必要")
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    plan = validate_plan(args.plan)
    # planは一度しか使わない。起動失敗を含め自動再試行しない。
    with args.plan.with_suffix(".claimed").open("x", encoding="utf-8") as stream:
        stream.write(datetime.now(UTC).isoformat())
    run = ROOT / ".planning/tmp" / ("pagefolio-uat-" + uuid4().hex)
    result = run_collection(LocalDriver(args.plan.resolve(), plan, run), plan)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
