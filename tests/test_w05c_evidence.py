"""合成証拠と隔離fixtureでW05cの欠落・回収混同を拒否する。"""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.w05c_evidence import QuitEvidence, native_event

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning/phases/06-release-validation"
NODE = shutil.which("node")


def valid_evidence():
    start = datetime(2026, 11, 5, tzinfo=UTC)
    identity = {
        "run_id": "pagefolio-uat-test",
        "pid": 123,
        "process_created": 456789,
        "entry": "script",
        "manual": True,
        "peers": {
            "during_confirm": "peer-" + "a" * 32,
            "after_answer": "peer-" + "b" * 32,
        },
    }
    state = {
        "root_alive": True,
        "pages": 3,
        "rotations": [90, 90, 0],
        "undo": 3,
        "redo": 0,
    }
    names = [
        "observer_started",
        "quit_enter",
        "ask_enter",
        "native_shown",
        "peer_during_confirm",
        "native_no",
        "ask_return",
        "quit_return",
        "marker_created",
        "peer_after_answer",
        "pre_collection",
        "stop_enter",
        "cleanup_enter",
        "observer_closed",
    ]
    events = []
    for i, name in enumerate(names, 1):
        events.append(
            {
                "run_id": identity["run_id"],
                "pid": 123,
                "process_created": 456789,
                "seq": i,
                "utc": (start + timedelta(seconds=i)).isoformat(),
                "monotonic": float(i),
                "event": name,
                "hwnd": 789,
                "state": dict(state),
            }
        )
    for event in events:
        if event["event"].startswith("peer_"):
            label = event["event"].removeprefix("peer_")
            event["peer"] = {
                "dir": identity["peers"][label],
                "pid": 123,
                "process_created": 456789,
                "constructed": 0,
                "status_preserved": True,
            }
    events[6]["result"] = False
    events[10].update(request_id="request", elapsed=11)
    snapshot = {
        "run_id": identity["run_id"],
        "pid": 123,
        "process_created": 456789,
        "request_id": "request",
        "marker": True,
        "marker_sha256": "marker-hash",
        "stop": False,
        "stop_all": False,
        "state": state,
        "events": 11,
        "errors": [],
        "log_sha256": "log-hash",
    }
    final = {
        "run_id": identity["run_id"],
        "pid": 123,
        "process_created": 456789,
        "events": len(events),
        "written": len(events),
        "pending": 0,
        "errors": [],
        "sha256": "final-hash",
    }
    answer = {
        "answer_original": "いいえ。閉じた。1と2が横、3が縦、3ページ、1画面。",
        "answer_run_id": identity["run_id"],
        "answer_source": "利用者の直接回答",
        "answer_captured_at": (start + timedelta(seconds=9.2)).isoformat(),
        "answer_semantics": {
            "approved_by": "利用者",
            "approved_at": (start + timedelta(seconds=9.4)).isoformat(),
        },
    }
    for key, quote in {
        "answered_no": "いいえ",
        "confirm_closed": "閉じた",
        "three_pages": "3ページ",
        "rotations_kept": "1と2が横、3が縦",
        "single_window": "1画面",
    }.items():
        answer["answer_semantics"][key] = {"confirmed": True, "quote": quote}
    return {
        "events": events,
        "snapshot": snapshot,
        "final": final,
        "answer": answer,
        "identity": identity,
    }


def validate(payload):
    assert NODE, "検査にはnodeが必要"
    return subprocess.run(  # noqa: S603 — 固定validatorへJSONデータだけを渡す。
        [NODE, str(PHASE / "06-05-w05c-evidence.cjs")],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        check=False,
    )


def test_complete_evidence_and_original_wording_accepted():
    payload = valid_evidence()
    before = copy.deepcopy(payload)
    result = validate(payload)
    assert result.returncode == 0, result.stderr
    assert payload == before


@pytest.mark.parametrize(
    "missing",
    [
        "native_no",
        "ask_return",
        "marker_created",
        "peer_during_confirm",
        "peer_after_answer",
        "pre_collection",
        "observer_closed",
    ],
)
def test_missing_event_rejected(missing):
    payload = valid_evidence()
    payload["events"] = [e for e in payload["events"] if e["event"] != missing]
    for i, event in enumerate(payload["events"], 1):
        event["seq"] = i
    assert validate(payload).returncode != 0


@pytest.mark.parametrize(
    "damage",
    [
        "stop_before_no",
        "wrong_hwnd",
        "wrong_owner",
        "wrong_run",
        "reverse_clock",
        "missing_seq",
        "recording_error",
        "pending",
        "deadline",
        "answer_run",
        "answer_quote",
        "answer_time",
        "semantic_missing",
        "edited_pages",
        "peer_primary",
        "diagnostic",
        "old_module",
        "watchdog",
        "tk_error",
        "no_false",
        "snapshot_stop",
    ],
)
def test_invalid_evidence_rejected_without_mutation(tmp_path, damage):
    p = valid_evidence()
    if damage == "stop_before_no":
        p["events"][4]["event"] = "stop_enter"
    elif damage == "wrong_hwnd":
        p["events"][5]["hwnd"] += 1
    elif damage == "wrong_owner":
        p["events"][5]["process_created"] += 1
    elif damage == "wrong_run":
        p["events"][5]["run_id"] = "other"
    elif damage == "reverse_clock":
        p["events"][5]["monotonic"] = 0
    elif damage == "missing_seq":
        p["events"][5]["seq"] += 1
    elif damage == "recording_error":
        p["final"]["errors"].append("write failed")
    elif damage == "pending":
        p["final"]["pending"] = 1
    elif damage == "deadline":
        p["events"][10]["elapsed"] = 120
    elif damage == "answer_run":
        p["answer"]["answer_run_id"] = "old-run"
    elif damage == "answer_quote":
        p["answer"]["answer_semantics"]["answered_no"]["quote"] = "はい"
    elif damage == "answer_time":
        p["answer"]["answer_captured_at"] = p["events"][11]["utc"]
    elif damage == "semantic_missing":
        p["answer"]["answer_semantics"].pop("approved_by")
    elif damage == "edited_pages":
        p["events"][7]["state"]["pages"] = 4
    elif damage == "peer_primary":
        p["events"][9]["peer"]["constructed"] = 1
    elif damage == "diagnostic":
        p["identity"]["diagnostic_only"] = True
    elif damage == "old_module":
        p["identity"]["entry"] = "module"
    elif damage in {"watchdog", "tk_error"}:
        p["events"][11]["event"] = (
            "watchdog_enter" if damage == "watchdog" else "tk_error"
        )
    elif damage == "no_false":
        p["events"][6]["result"] = True
    elif damage == "snapshot_stop":
        p["snapshot"]["stop"] = True
    ledger = tmp_path / "ledger.json"
    ledger.write_text('{"status":"not-run"}', encoding="utf-8")
    before = ledger.read_bytes()
    assert validate(p).returncode != 0
    assert ledger.read_bytes() == before


def test_wrapper_preserves_result_exception_and_edit_state(tmp_path):
    observer = QuitEvidence(tmp_path, {"pid": 1, "process_created": 2})
    app = SimpleNamespace(
        root=SimpleNamespace(winfo_exists=lambda: 1),
        doc=[SimpleNamespace(rotation=90)],
        _undo_stack=[1],
        _redo_stack=[],
    )

    def original():
        return False

    assert original() is observer.wrap(original, "ask", app)()
    problem = ValueError("元例外")

    def fail():
        raise problem

    with pytest.raises(ValueError) as caught:
        observer.wrap(fail, "ask", app)()
    assert caught.value is problem
    assert app.doc[0].rotation == 90 and len(app._undo_stack) == 1


def test_flush_and_final_pending_accounting(tmp_path):
    observer = QuitEvidence(tmp_path, {"pid": 1, "process_created": 2})
    observer.emit("native_no", hwnd=3)
    assert not (tmp_path / "w05c-events.jsonl").exists(), "callback内でI/Oしない"
    observer.close()
    final = json.loads((tmp_path / "w05c-observer-final.json").read_text())
    assert final["pending"] == 0 and not final["errors"]
    assert (
        final["sha256"]
        == hashlib.sha256((tmp_path / "w05c-events.jsonl").read_bytes()).hexdigest()
    )
    observer.close()
    assert final == json.loads((tmp_path / "w05c-observer-final.json").read_text())


def test_flush_error_is_recorded_and_never_success(tmp_path):
    observer = QuitEvidence(tmp_path, {"pid": 1, "process_created": 2})
    (tmp_path / "w05c-events.jsonl").mkdir()
    observer.emit("native_no")
    observer.flush()
    assert observer.errors and observer.written == 0
    observer.close()
    final = json.loads((tmp_path / "w05c-observer-final.json").read_text())
    assert final["errors"] and final["pending"] == 2 and final["sha256"] is None


@pytest.mark.parametrize("fail", [False, True])
def test_native_callback_always_delegates_without_io(tmp_path, fail):
    observer = QuitEvidence(tmp_path, {"pid": 1, "process_created": 2})
    received = []

    def forward(*args):
        received.append(args)
        return 42

    if fail:

        def broken(*args, **kwargs):
            raise OSError("採取失敗")

        observer.emit = broken
    assert native_event(observer, 10, 0x111, 7, 0, 905, None, forward) == 42
    assert received == [(10, 0x111, 7, 0)]
    assert not list(tmp_path.iterdir())
    assert bool(observer.errors) is fail


def helper_fixture(tmp_path, damage=None):
    """正式helper自身を隔離した正負対照。既存の台帳を使わない。"""
    import os

    p = valid_evidence()
    root = tmp_path / "repo"
    phase = root / ".planning/phases/06-release-validation"
    phase.mkdir(parents=True)
    for name in ("06-05-record-w05c-python.cjs", "06-05-w05c-evidence.cjs"):
        shutil.copyfile(PHASE / name, phase / name)
    evidence = phase / "06-05-evidence"
    evidence.mkdir()
    run = root / ".planning/tmp" / p["identity"]["run_id"]
    owner = run / "uat-owner-native-quit"
    owner.mkdir(parents=True)
    answer = p["answer"]
    answer.update(
        case="W05c",
        condition="quit-no",
        row="W05c/quit-no@script",
        entry="script",
        run=str(run),
        peers=p["identity"]["peers"],
        adoption={
            "approved_by": "利用者",
            "approved_at": answer["answer_captured_at"],
            "decision": "採用",
        },
    )
    obs = run / "observation.md"
    obs.write_text(f"回答原文: 「{answer['answer_original']}」", encoding="utf-8")
    answer.update(
        observation_record=str(obs.relative_to(root)),
        observation_record_sha256=hashlib.sha256(obs.read_bytes()).hexdigest(),
    )
    filename = "W05c_quit-no_at_script-20261105T000001Z.json"
    answer_path = evidence / filename

    def write(path, obj):
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    write(answer_path, answer)
    write(
        run / "manifest.json",
        {
            "case": "native-quit",
            "role": "uat-owner-native-quit",
            "expected_owner": {"pid": 123, "process_created": 456789, "manual": True},
            "fixture": str(owner),
        },
    )
    focus = {
        "state_preserved": True,
        "document_pages": 3,
        "page_rotations": [90, 90, 0],
    }
    primary = {
        "result": "primary",
        "constructed": 1,
        "restored": 2,
        "status_preserved": True,
    }
    write(
        run / "inspection.json",
        {
            "originals_unchanged": True,
            "result.json": primary,
            "focus-result.json": focus,
        },
    )
    for name in (
        "ready",
        "focus-ready",
        "quit-cancelled",
        "stderr.log",
        "stdout.log",
        "traceback.log",
    ):
        (owner / name).touch()
    for name, obj in {
        "result.json": primary,
        "focus-result.json": focus,
        "resource-audit.json": {},
        "initializing.json": {},
    }.items():
        write(owner / name, obj)
    for label, dirname in answer["peers"].items():
        peer = run / dirname
        peer.mkdir()
        write(peer / "result.json", {"constructed": 0, "status_preserved": True})
        write(peer / "expected-owner.json", {"pid": 123, "process_created": 456789})
        write(peer / "resource-audit.json", {})
        for name in ("stderr.log", "stdout.log", "traceback.log"):
            (peer / name).touch()
        at = 5 if label == "during_confirm" else 11
        os.utime(peer / "result.json", (at, at))
    for name, at in {
        "focus-ready": 1,
        "quit-cancelled": 9,
        "focus-result.json": 10,
    }.items():
        os.utime(owner / name, (at, at))
    frozen = root / "frozen.py"
    frozen.write_text("# frozen\n", encoding="utf-8")
    os.utime(frozen, (0, 0))
    final_dir = root / "distribution"
    final_dir.mkdir()
    write(
        final_dir / "release-report.json",
        {
            "run_id": "rebuild",
            "input_manifest": {
                "frozen.py": hashlib.sha256(frozen.read_bytes()).hexdigest()
            },
        },
    )
    write(
        phase / "06-BUILD-EVIDENCE.json",
        {
            "generation": 5,
            "final_release": {
                "final_dir": str(final_dir),
                "runs": [{"order": "rebuild", "run_id": "rebuild"}],
            },
        },
    )
    write(
        phase / "06-MANUAL-EVIDENCE.json",
        {
            "cases": [
                {
                    "id": "W05c",
                    "subrows": [
                        {
                            "card": answer["row"],
                            "status": "not-run",
                            "generation": 5,
                            "release_requirement": "required",
                        }
                    ],
                }
            ]
        },
    )
    (phase / "06-UAT.md").write_bytes(
        f"### {answer['row']}\n- **状態**: not-run\n".encode()
    )
    events = p["events"]
    early = copy.deepcopy(events[10])
    early["request_id"] = "before-peer"
    events.insert(9, early)
    start = datetime(2026, 11, 5, tzinfo=UTC)
    for i, event in enumerate(events, 1):
        event.update(
            seq=i, monotonic=float(i), utc=(start + timedelta(seconds=i)).isoformat()
        )
    if damage == "late_marker":
        events[8]["event"] = "stop_enter"
    elif damage == "missing_no":
        events[5]["event"] = "other"
    log_lines = [json.dumps(e) + "\n" for e in events]
    raw = "".join(log_lines).encode()
    (owner / "w05c-events.jsonl").write_bytes(raw)
    p["final"].update(
        events=len(events), written=len(events), sha256=hashlib.sha256(raw).hexdigest()
    )
    write(owner / "w05c-observer-final.json", p["final"])
    snapshot = p["snapshot"]
    snapshot.update(
        events=12,
        log_sha256=hashlib.sha256("".join(log_lines[:12]).encode()).hexdigest(),
        marker_sha256=hashlib.sha256(b"").hexdigest(),
    )
    write(owner / "w05c-pre-collection.json", snapshot)
    (owner / "w05c-pre-collection-stack.log").write_text("stack", encoding="utf-8")
    first = dict(
        snapshot,
        request_id="before-peer",
        events=10,
        log_sha256=hashlib.sha256("".join(log_lines[:10]).encode()).hexdigest(),
    )
    record = {
        "ok": True,
        "run_id": run.name,
        "answer_path": str(answer_path),
        "answer_record": {k: v for k, v in answer.items() if k != "peers"},
    }
    write(run / "w05c-check-before_peer.json", dict(record, snapshot=first))
    write(run / "w05c-check-before_stop.json", dict(record, snapshot=snapshot))
    for stage in ("before", "after"):
        dest = run / ("w05c-collection-" + stage)
        dest.mkdir()
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
        write(
            dest / "owner.json",
            {
                "pid": 123,
                "process_created": 456789,
                "already_exited": False,
                "exited": True,
                "utc": (
                    start + timedelta(seconds=12.5 if stage == "before" else 16)
                ).isoformat(),
            },
        )
    return phase, filename


@pytest.mark.parametrize("damage", [None, "late_marker", "missing_no"])
def test_formal_helper_dry_run_never_writes(tmp_path, damage):
    phase, filename = helper_fixture(tmp_path, damage)
    before = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    result = subprocess.run(  # noqa: S603 — 隔離した既存helperを既知の引数で起動する。
        [NODE, str(phase / "06-05-record-w05c-python.cjs"), filename, "--dry-run"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (damage is None), result.stderr
    after = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native機構の対照")
@pytest.mark.parametrize("observed", [False, True])
def test_native_observer_control_preserves_quit_decision(tmp_path, observed):
    from tests import test_startup_windows as h

    children = []
    try:
        namespace = uuid4().hex
        owner, fixture = h._spawn(
            tmp_path, namespace, "focus-owner-native-quit", w05c_observe=observed
        )
        children.append(owner)
        h._wait_file(owner, fixture / "focus-ready")
        peer, _ = h._spawn(tmp_path, namespace, "entry-script")
        children.append(peer)
        assert h._finish(peer)["constructed"] == 0
        h._wait_file(owner, fixture / "quit-cancelled")
        focus = json.loads((fixture / "focus-result.json").read_text())
        assert focus["document_pages"] == 3
        assert focus["page_rotations"] == [90, 90, 0]
        assert focus["state_preserved"]
        if observed:
            from tests.w05c_evidence import save

            save(
                fixture / "w05c-snapshot-request.json",
                {"request_id": "control", "stage": "before_stop"},
            )
            h._wait_file(owner, fixture / "w05c-pre-collection.json")
            snapshot = json.loads((fixture / "w05c-pre-collection.json").read_text())
            prefix = b"".join(
                (fixture / "w05c-events.jsonl")
                .read_bytes()
                .splitlines(keepends=True)[: snapshot["events"]]
            )
            assert hashlib.sha256(prefix).hexdigest() == snapshot["log_sha256"]
            assert snapshot["marker"] and not snapshot["stop"]
            assert snapshot["state"]["pages"] == 3
        if observed:
            from tests.w05c_evidence import collect

            expected = json.loads((fixture / "ready").read_text())
            collect(
                tmp_path,
                {
                    "fixture": str(fixture),
                    "expected_owner": expected,
                    "namespace": namespace,
                },
            )
            before = json.loads(
                (tmp_path / "w05c-collection-before/owner.json").read_text()
            )
            after = json.loads(
                (tmp_path / "w05c-collection-after/owner.json").read_text()
            )
            assert not before["already_exited"] and after["exited"]
            assert before["windows"], "外部から同ownerの窓を読み取る"
        else:
            (fixture / "stop").touch()
        assert h._finish(owner)["constructed"] == 1
        if observed:
            final = json.loads((fixture / "w05c-observer-final.json").read_text())
            assert not final["errors"] and final["pending"] == 0
            events = [
                json.loads(line)
                for line in (fixture / "w05c-events.jsonl").read_text().splitlines()
            ]
            names = [e["event"] for e in events]
            assert (
                names.index("native_no")
                < names.index("ask_return")
                < names.index("marker_created")
                < names.index("stop_enter")
            )
            assert (
                next(e for e in events if e["event"] == "ask_return")["result"] is False
            )
            assert not any(
                e["event"] in {"acquisition_error", "tk_error"} for e in events
            )
        else:
            assert not (fixture / "w05c-events.jsonl").exists()
    finally:
        h._reclaim(children)
