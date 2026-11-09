"""v3の遅延回答・期限・失敗回収をGUIなしで検査する。"""

import copy
import hashlib
import json
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta

import pytest

from tests.test_w05c_evidence import NODE, PHASE, helper_fixture
from tests.w05c_runner import (
    BUDGET,
    INPUTS,
    SCHEMA,
    guard_after_no_peer,
    run_collection,
    validate_plan,
)


class Clock:
    def __init__(self):
        self.value = 0.0

    def now(self):
        return self.value

    def sleep(self, value):
        self.value += value


class Driver:
    def __init__(self, clock, *, no_at=10, fail=None):
        self.clock, self.no_at, self.fail = clock, no_at, fail
        self.calls = []
        self.log = []

    def call(self, action):
        self.calls.append((action, self.clock.now()))
        if action == self.fail:
            raise OSError(action)

    def start(self):
        self.call("start")
        self.log = [
            {
                "event": "watchdog_registered",
                "delay_ms": 120000,
                "registered_monotonic": 0,
                "due_monotonic": 120,
                "clock": time.get_clock_info("monotonic").implementation,
            },
            {"event": "native_shown"},
        ]

    def events(self):
        if self.clock.now() >= self.no_at and not any(
            e["event"] == "marker_created" for e in self.log
        ):
            self.log.extend(
                [
                    {"event": "native_no"},
                    {"event": "marker_created", "monotonic": self.no_at},
                ]
            )
        return self.log

    def peer(self):
        self.call("peer")

    def check(self, stage):
        self.call(stage)

    def inspect(self):
        self.call("inspect")

    def collect(self):
        self.call("collect")

    def seal(self):
        self.call("seal")
        return {"status": "machine_collected_pending_answer"}

    def failed(self, error):
        self.call("failed")

    def recover(self):
        self.call("recover")


def test_no_answer_dependency_and_observation_window():
    clock = Clock()
    driver = Driver(clock)
    result = run_collection(
        driver, {"observation_seconds": 10}, now=clock.now, sleep=clock.sleep
    )
    assert result["status"] == "machine_collected_pending_answer"
    assert [c[0] for c in driver.calls] == [
        "start",
        "peer",
        "before_peer",
        "peer",
        "before_stop",
        "inspect",
        "collect",
        "seal",
    ]
    assert driver.calls[-3][1] >= 20
    assert clock.now() < 120


@pytest.mark.parametrize("no_at", [0, 100, float("inf")])
def test_early_late_or_absent_no_never_retries(no_at):
    clock = Clock()
    driver = Driver(clock, no_at=no_at)
    with pytest.raises(AssertionError):
        run_collection(
            driver, {"observation_seconds": 10}, now=clock.now, sleep=clock.sleep
        )
    assert sum(c[0] == "peer" for c in driver.calls) <= 1
    assert driver.calls[-1][0] == "recover"
    assert "seal" not in [c[0] for c in driver.calls]


@pytest.mark.parametrize(
    "fail",
    ["start", "peer", "before_peer", "before_stop", "inspect", "collect", "seal"],
)
def test_failure_is_not_retried_or_accepted(fail):
    clock = Clock()
    driver = Driver(clock, fail=fail)
    with pytest.raises(OSError):
        run_collection(
            driver, {"observation_seconds": 10}, now=clock.now, sleep=clock.sleep
        )
    names = [c[0] for c in driver.calls]
    assert names.count(fail) == 1
    assert ("recover" in names) is (fail not in {"collect", "seal"})
    assert names.count("collect") <= 1


def test_plan_source_drift_and_unprepared_rejected(tmp_path):
    plan_dir = tmp_path / ".planning"
    plan_dir.mkdir()
    for name in INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("source", encoding="utf-8")
    plan = {
        "schema": SCHEMA,
        "entry": "script",
        "permissions_ready": True,
        "budget_evidence": "非GUI fixture。実試行の再開根拠ではない",
        "budgets": BUDGET,
        "observation_seconds": 10,
        "source_inputs": {n: hashlib.sha256(b"source").hexdigest() for n in INPUTS},
    }
    target = plan_dir / "plan.json"
    target.write_bytes(json.dumps(plan, indent=2).replace("\n", "\r\n").encode())
    checked = validate_plan(target, tmp_path)
    assert (
        hashlib.sha256(checked["original_json"].encode()).hexdigest()
        == checked["plan_sha256"]
    )
    (tmp_path / INPUTS[0]).write_text("changed", encoding="utf-8")
    with pytest.raises(AssertionError, match="採取入力変更"):
        validate_plan(target, tmp_path)
    plan["permissions_ready"] = False
    target.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(AssertionError, match="起動前準備"):
        validate_plan(target, tmp_path)


def v3_fixture(tmp_path):
    phase, filename = helper_fixture(tmp_path)
    shutil.copyfile(PHASE / "06-05-w05c-v3.cjs", phase / "06-05-w05c-v3.cjs")
    answer_path = phase / "06-05-evidence" / filename
    answer = json.loads(answer_path.read_text(encoding="utf-8"))
    from pathlib import Path

    run = Path(answer["run"])
    owner = run / "uat-owner-native-quit"
    base = datetime(2026, 11, 5, tzinfo=UTC)

    def utc(seconds):
        return (base + timedelta(seconds=seconds)).isoformat()

    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))

    original_plan = {
        "schema": SCHEMA,
        "observation_seconds": 10,
        "source_inputs": {
            "frozen.py": hashlib.sha256(
                (phase.parents[2] / "frozen.py").read_bytes()
            ).hexdigest()
        },
    }
    original_json = json.dumps(original_plan)
    plan_hash = hashlib.sha256(original_json.encode()).hexdigest()
    plan = {**original_plan, "plan_sha256": plan_hash, "original_json": original_json}
    manifest = read(run / "manifest.json")
    manifest.update(w05c_schema=SCHEMA, entry="script", w05c_plan=plan)
    write(run / "manifest.json", manifest)
    write(owner / "w05c-plan.json", plan)
    events = [
        json.loads(line)
        for line in (owner / "w05c-events.jsonl").read_text().splitlines()
    ]
    registered = dict(
        events[0],
        event="watchdog_registered",
        registered_monotonic=0,
        due_monotonic=120,
        delay_ms=120000,
        clock=time.get_clock_info("monotonic").implementation,
    )
    events.insert(1, registered)
    for i, e in enumerate(events, 1):
        e.update(
            seq=i, monotonic=i * 4, utc=utc(i * 4), schema=SCHEMA, plan_sha256=plan_hash
        )
        if e["event"] == "peer_after_answer":
            e["event"] = "peer_after_no"
    answer.update(schema=SCHEMA, answer_captured_at=utc(200))
    answer["peers"]["after_no"] = answer["peers"].pop("after_answer")
    answer["answer_original"] += "回収前に見た。"
    answer["answer_semantics"]["approved_at"] = utc(201)
    answer["answer_semantics"]["observed_before_collection"] = {
        "confirmed": True,
        "quote": "回収前に見た",
    }
    answer["adoption"]["approved_at"] = utc(202)
    obs = run / "observation.md"
    obs.write_text(f"回答原文: 「{answer['answer_original']}」", encoding="utf-8")
    answer["observation_record_sha256"] = hashlib.sha256(obs.read_bytes()).hexdigest()
    lines = [json.dumps(e) + "\n" for e in events]
    (owner / "w05c-events.jsonl").write_bytes("".join(lines).encode())
    final = read(owner / "w05c-observer-final.json")
    final.update(
        schema=SCHEMA,
        plan_sha256=plan_hash,
        events=len(events),
        written=len(events),
        sha256=hashlib.sha256("".join(lines).encode()).hexdigest(),
    )
    write(owner / "w05c-observer-final.json", final)
    ident = {
        "schema": SCHEMA,
        "run_id": run.name,
        "pid": 123,
        "process_created": 456789,
        "entry": "script",
        "manual": True,
        "plan_sha256": plan_hash,
        "observation_seconds": 10,
        "peers": answer["peers"],
    }
    for stage, request in [("before_peer", "before-peer"), ("before_stop", "request")]:
        snap = read(run / f"w05c-check-{stage}.json")["snapshot"]
        event = next(e for e in events if e.get("request_id") == request)
        snap.update(
            schema=SCHEMA,
            plan_sha256=plan_hash,
            events=event["seq"],
            log_sha256=hashlib.sha256(
                "".join(lines[: event["seq"]]).encode()
            ).hexdigest(),
        )
        write(
            run / f"w05c-v3-{stage}.json",
            {
                "ok": True,
                "schema": SCHEMA,
                "run_id": run.name,
                "identity": ident,
                "snapshot": snap,
            },
        )
    write(owner / "w05c-pre-collection.json", snap)
    for stage in ("before", "after"):
        dest = run / f"w05c-collection-{stage}"
        shutil.copyfile(
            owner / "w05c-pre-collection.json", dest / "w05c-pre-collection.json"
        )
        write(
            dest / "copies.json",
            {
                "run_id": run.name,
                "files": {
                    "w05c-pre-collection.json": hashlib.sha256(
                        (dest / "w05c-pre-collection.json").read_bytes()
                    ).hexdigest()
                },
            },
        )
        state = read(dest / "owner.json")
        state["utc"] = utc(53 if stage == "before" else 66)
        write(dest / "owner.json", state)
    (run / "w05c-v3-peer-started").write_text(plan_hash, encoding="utf-8")
    (run / "w05c-v3-commands.jsonl").write_text("{}\n", encoding="utf-8")
    collection = {
        "schema": SCHEMA,
        "status": "machine_collected_pending_answer",
        "run_id": run.name,
        "plan_sha256": plan_hash,
        "identity": ident,
        "completed_at": utc(70),
        "files": {
            str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in run.rglob("*")
            if p.is_file() and p != obs
        },
    }
    collection_path = run / "w05c-v3-collection.json"
    write(collection_path, collection)
    answer["collection_sha256"] = hashlib.sha256(
        collection_path.read_bytes()
    ).hexdigest()
    write(answer_path, answer)
    ident = {**ident, "collection_sha256": answer["collection_sha256"]}
    payload = {
        "mode": "adoption",
        "events": events,
        "snapshot": snap,
        "final": final,
        "identity": ident,
        "answer": answer,
        "collection": collection,
    }
    return phase, filename, payload


def validate(payload):
    return subprocess.run(  # noqa: S603 — 純粋validatorへJSONだけを渡す。
        [NODE, str(PHASE / "06-05-w05c-v3.cjs")],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )


@pytest.mark.parametrize("schema", ["v2", "v3"])
@pytest.mark.parametrize("decision", ["不採用", "deny", "unknown", True, 1, {}, None])
@pytest.mark.parametrize("dry_run", [False, True])
def test_adoption_requires_explicit_acceptance(tmp_path, schema, decision, dry_run):
    if schema == "v3":
        phase, filename, payload = v3_fixture(tmp_path)
        answer = payload["answer"]
    else:
        phase, filename = helper_fixture(tmp_path)
        answer = json.loads(
            (phase / "06-05-evidence" / filename).read_text(encoding="utf-8")
        )
    answer["adoption"]["decision"] = decision
    (phase / "06-05-evidence" / filename).write_text(
        json.dumps(answer, ensure_ascii=False), encoding="utf-8"
    )
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    if schema == "v3":
        rejected = validate(payload)
        assert rejected.returncode != 0, "否認・未知の採用判断を受理した"
        assert rejected.stderr.strip() == "W05c v3: adoption missing/early"
    command = [NODE, str(phase / "06-05-record-w05c-python.cjs"), filename]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(  # noqa: S603 — 隔離fixtureで否認時の書込禁止を検証する。
        command,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0, "正式helperが否認・未知の採用判断を受理した"
    assert "Error: adoption approval missing" in result.stderr.splitlines()
    assert before == {
        str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("arrival", ["early", "late"])
def test_answer_v3_adoption_and_formal_dry_run(tmp_path, arrival):
    phase, filename, payload = v3_fixture(tmp_path)
    if arrival == "early":
        marker = next(e for e in payload["events"] if e["event"] == "marker_created")
        payload["answer"]["answer_captured_at"] = marker["utc"]
        payload["answer"]["answer_semantics"]["approved_at"] = marker["utc"]
        (phase / "06-05-evidence" / filename).write_text(
            json.dumps(payload["answer"], ensure_ascii=False), encoding="utf-8"
        )
    assert validate(payload).returncode == 0
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = subprocess.run(  # noqa: S603 — 隔離fixtureの正式helperをdry-runする。
        [NODE, str(phase / "06-05-record-w05c-python.cjs"), filename, "--dry-run"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    preview = json.loads(result.stdout)
    assert "No後" in preview["preparation_note"]
    assert "No後" in preview["edit_state_basis"]
    assert (
        payload["answer"]["answer_semantics"]["answered_no"]["quote"]
        in preview["answered_no_basis"]
    )
    assert before == {
        str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "damage",
    [
        "missing_no",
        "missing_marker",
        "wrong_owner",
        "wrong_hwnd",
        "watchdog",
        "late_stop",
        "short_observation",
        "v2_mix",
        "wrong_plan",
        "wrong_run_answer",
        "no_answer",
        "unconfirmed",
        "post_collection_observation",
        "unsealed",
        "collection_owner",
        "answer_before_marker",
        "adoption_before_seal",
    ],
)
def test_v3_rejects_incomplete_or_mixed_evidence(tmp_path, damage):
    _, _, p = v3_fixture(tmp_path)
    if damage in {"missing_no", "missing_marker", "watchdog", "v2_mix"}:
        name = {
            "missing_no": "native_no",
            "missing_marker": "marker_created",
            "watchdog": "stop_enter",
            "v2_mix": "peer_after_no",
        }[damage]
        next(e for e in p["events"] if e["event"] == name)["event"] = {
            "watchdog": "watchdog_enter",
            "v2_mix": "peer_after_answer",
        }.get(damage, "missing")
    elif damage == "wrong_owner":
        p["events"][5]["pid"] += 1
    elif damage == "wrong_hwnd":
        next(e for e in p["events"] if e["event"] == "native_no")["hwnd"] += 1
    elif damage == "late_stop":
        p["events"][-1]["monotonic"] = 120
    elif damage == "short_observation":
        p["identity"]["observation_seconds"] = 30
    elif damage == "wrong_plan":
        p["events"][0]["plan_sha256"] = "other"
    elif damage == "wrong_run_answer":
        p["answer"]["answer_run_id"] = "other"
    elif damage == "no_answer":
        p["answer"] = None
    elif damage == "unconfirmed":
        p["answer"]["answer_semantics"]["single_window"]["confirmed"] = False
    elif damage == "post_collection_observation":
        del p["answer"]["answer_semantics"]["observed_before_collection"]
    elif damage == "unsealed":
        p["collection"]["status"] = "collecting"
    elif damage == "collection_owner":
        p["collection"]["identity"]["pid"] += 1
    elif damage == "answer_before_marker":
        p["answer"]["answer_captured_at"] = p["events"][0]["utc"]
    elif damage == "adoption_before_seal":
        marker = next(e for e in p["events"] if e["event"] == "marker_created")
        p["answer"]["answer_captured_at"] = marker["utc"]
        p["answer"]["answer_semantics"]["approved_at"] = marker["utc"]
        p["answer"]["adoption"]["approved_at"] = marker["utc"]
    original = copy.deepcopy(p)
    assert validate(p).returncode != 0
    assert p == original


def test_v3_machine_accepts_without_answer_but_does_not_adopt(tmp_path):
    _, _, payload = v3_fixture(tmp_path)
    payload.pop("answer")
    payload["mode"] = "machine"
    assert validate(payload).returncode == 0


@pytest.mark.parametrize(
    "damage",
    [
        "sealed_bytes",
        "answer_run",
        "observation_missing",
        "failed_collection",
        "plan_fields",
    ],
)
def test_v3_formal_helper_rejects_without_writes(tmp_path, damage):
    from pathlib import Path

    phase, filename, payload = v3_fixture(tmp_path)
    answer_path = phase / "06-05-evidence" / filename
    answer = payload["answer"]
    run = Path(answer["run"])
    if damage == "sealed_bytes":
        (run / "w05c-v3-commands.jsonl").write_text("changed", encoding="utf-8")
    elif damage == "answer_run":
        answer["answer_run_id"] = "other"
    elif damage == "observation_missing":
        del answer["answer_semantics"]["observed_before_collection"]
    elif damage == "failed_collection":
        (run / "w05c-v3-failed.json").write_text("{}", encoding="utf-8")
    elif damage == "plan_fields":
        path = run / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["w05c_plan"]["observation_seconds"] = 0
        path.write_text(json.dumps(manifest), encoding="utf-8")
    answer_path.write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = subprocess.run(  # noqa: S603 — 隔離fixtureの正式helperをdry-runする。
        [NODE, str(phase / "06-05-record-w05c-python.cjs"), filename, "--dry-run"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert before == {
        str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


def test_undo_change_never_counts_as_kept_state(tmp_path):
    _, _, payload = v3_fixture(tmp_path)
    next(e for e in payload["events"] if e["event"] == "ask_return")["state"][
        "undo"
    ] = 2
    assert validate(payload).returncode != 0


def test_recovery_attempted_even_if_failure_record_write_fails():
    clock = Clock()
    driver = Driver(clock, no_at=100, fail="failed")
    with pytest.raises(OSError, match="failed"):
        run_collection(
            driver, {"observation_seconds": 10}, now=clock.now, sleep=clock.sleep
        )
    assert driver.calls[-1][0] == "recover"


def test_after_no_peer_never_repeats_or_runs_after_cleanup(tmp_path, monkeypatch):
    from tests import w05c_runner

    ident = {"schema": SCHEMA}
    monkeypatch.setattr(w05c_runner, "identity", lambda *args: ident)
    monkeypatch.setattr(w05c_runner, "read_events", lambda *args: [])
    record = {
        "ok": True,
        "identity": ident,
        "result": {"due_monotonic": time.monotonic() + 120},
    }
    (tmp_path / "w05c-v3-before_peer.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    ident["plan_sha256"] = "plan"
    record["identity"] = ident
    (tmp_path / "w05c-v3-before_peer.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    guard_after_no_peer(tmp_path, {"fixture": str(tmp_path)})
    with pytest.raises(FileExistsError):
        guard_after_no_peer(tmp_path, {"fixture": str(tmp_path)})
    monkeypatch.setattr(
        w05c_runner, "read_events", lambda *args: [{"event": "cleanup_enter"}]
    )
    with pytest.raises(AssertionError, match="回収開始後"):
        guard_after_no_peer(tmp_path, {"fixture": str(tmp_path)})
