"""W12c本人経路と実入力の正式採用境界を隔離して検証する。"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests import test_w12b_evidence as w12b

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning/phases/06-release-validation"
HELPER = PHASE / "06-05-record-w12c.cjs"
CREATED = w12b.CREATED


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    w12b.save(path, value)


def fixture(tmp_path, route="terminal"):
    root, phase, run, _, profile = w12b.fixture(tmp_path)
    for name in ("06-05-w12c-driver.py", "06-05-record-w12c.cjs"):
        shutil.copyfile(PHASE / name, phase / name)
    shutil.copyfile(PHASE / "06-W12C-COLLECTION.md", phase / "06-W12C-COLLECTION.md")
    peer = run / ("peer-" + "b" * 32)
    audit_path = peer / "resource-audit.json"
    audit = {
        "process_created": CREATED + 1,
        **json.loads(audit_path.read_text(encoding="utf-8")),
    }
    save(audit_path, audit)
    now = datetime.now(UTC)

    def at(seconds):
        return (now + timedelta(seconds=seconds)).isoformat()

    observed_time = now.timestamp() + 34.9
    os.utime(audit_path, (observed_time, observed_time))
    os.utime(peer / "result.json", (observed_time, observed_time))

    manifest = {
        "run": str(run),
        "namespace": "fixed-production",
        "case": "preview",
        "role": "entry-owner-script",
        "fixture": str(run / "entry-owner-script"),
        "w12a_schema": "w12a-v1",
        "w12a_primary": "script",
        "w12b_mixed": True,
        "expected_owner": {
            "pid": 1234,
            "process_created": CREATED,
            "manual": True,
        },
        "environment": {"session_id": 1},
        "originals_before": {
            n: None
            for n in (
                "pagefolio_settings.json",
                "ocr_custom_prompt.md",
                "ocr_summary_prompt.md",
            )
        },
    }
    save(run / "manifest.json", manifest)
    owner_fixture = run / "entry-owner-script"
    owner_fixture.mkdir()
    save(owner_fixture / "ready", {"pid": 1234, "process_created": CREATED})
    save(
        owner_fixture / "result.json",
        {"constructed": 1, "restored": 1, "result": "primary"},
    )
    save(owner_fixture / "resource-audit.json", {"pid": 1234})
    save(run / "inspection.json", {"originals_unchanged": True})
    save(run / "provenance-before-stop.json", {"matched": True})
    py_dir = root / ".venv/Scripts"
    py_dir.mkdir(parents=True)
    for name in ("python.exe", "pythonw.exe"):
        (py_dir / name).write_bytes(b"fixed-" + name.encode())
    py = py_dir / ("pythonw.exe" if route == "explorer" else "python.exe")
    args = [
        str(root / "tests/test_startup_windows.py"),
        "_test_scenario_bootstrap",
        str(peer),
        "fixed-production",
        "entry-script",
    ]
    artifact = {
        "route": route,
        "kind": "python",
        "target": str(py),
        "target_sha256": sha(py.read_bytes()),
        "arguments": args,
    }
    if route == "explorer":
        link = run / "W12c-Python.lnk"
        link.write_bytes(b"isolated-shortcut")
        artifact.update(shortcut=str(link), shortcut_sha256=sha(link.read_bytes()))
    else:
        artifact["terminal_command"] = "& " + " ".join(
            "'" + str(part).replace("'", "''") + "'" for part in [py, *args]
        )
    collectors = {
        p.relative_to(root).as_posix(): sha(p.read_bytes())
        for p in phase.glob("06-05-*")
        if p.suffix in {".py", ".cjs"}
    }
    row = f"W12c/{route}-python@script"
    machine = {
        "schema": "w12c-machine-v1",
        "row": row,
        "run": str(run),
        "route": route,
        "kind": "python",
        "entry": "script",
        "owner": {"pid": 1234, "created": str(CREATED)},
        "owner_after_peer": {
            "pid": 1234,
            "created": CREATED,
            "alive": True,
            "session_id": 1,
        },
        "launch_route": artifact,
        "peer_fixture": str(peer),
        "peer_identity": audit,
        "peer_result": {"constructed": 0, "result": "completed"},
        "api_return": audit["allow_foreground"],
        "actual_foreground": {"pid": 9999, "hwnd": 9998},
        "input_target_before": {"pid": 1234, "hwnd": 5678},
        "input_target_after": {"pid": 1234, "hwnd": 5678},
        "inspection": {"originals_unchanged": True},
        "stop": {"result.json": {"result": "primary"}},
        "provenance_after_stop": {"matched": True},
        "events": [
            {"step": "start", "at": at(0)},
            {"step": "input-preparation", "at": at(20)},
            {"step": "peer-observed", "at": at(35)},
            {"step": "foreground", "at": at(35.1)},
            {"step": "input-observed", "at": at(47.1)},
            {"step": "inspect", "at": at(48)},
            {"step": "stop", "at": at(49)},
        ],
        "finished_at": at(50),
        "provenance": {
            "source_inputs": json.loads(
                (run / "w12b-machine.json").read_text(encoding="utf-8")
            )["provenance"]["source_inputs"],
            "collector_inputs": collectors,
            "originals": {
                n: None
                for n in (
                    "pagefolio_settings.json",
                    "ocr_custom_prompt.md",
                    "ocr_summary_prompt.md",
                )
            },
            "original_plugins": {},
            "phase04": json.loads(
                (run / "w12b-machine.json").read_text(encoding="utf-8")
            )["provenance"]["phase04"],
            "helper_sha256": sha((phase / HELPER.name).read_bytes()),
            "w12b_helper_sha256": sha((phase / "06-05-record-w12b.cjs").read_bytes()),
            "collection_doc_sha256": sha(
                (phase / "06-W12C-COLLECTION.md").read_bytes()
            ),
            "python_executables": {
                n: sha((py_dir / n).read_bytes()) for n in ("python.exe", "pythonw.exe")
            },
        },
    }
    manifest["formal_provenance"] = {
        "source_inputs": machine["provenance"]["source_inputs"],
        "original_plugins": machine["provenance"]["original_plugins"],
        "phase04": machine["provenance"]["phase04"],
    }
    save(run / "manifest.json", manifest)
    save(run / "w12c-machine.json", machine)
    card = {
        "subrow": f"{route}-python@script",
        "card": row,
        "entry": "script",
        "condition": f"{route}-python",
        "evidence_kind": "python-real",
        "status": "not-run",
        "generation": 5,
        "required_observations": [
            "launch_route",
            "api_return",
            "actual_foreground",
            "real_input_target_kept",
        ],
    }
    save(
        phase / "06-MANUAL-EVIDENCE.json",
        {"cases": [{"id": "W12c", "subrows": [card]}]},
    )
    (phase / "06-UAT.md").write_text(
        "本受入は必須108行中0行pass・108行not-run・W11対象外2行not-run。\n"
        f"### {row}\n- **状態**: not-run\n",
        encoding="utf-8",
    )
    route_word = "Explorer" if route == "explorer" else "端末"
    direct = f"{row}: {route_word}から起動した/同じ入力先に実入力した/画面は1つ"
    answer = {
        "schema": "w12c-answer-v1",
        "condition": f"{route}-python@script",
        "row": row,
        "run": str(run),
        "machine_sha256": sha((run / "w12c-machine.json").read_bytes()),
        "direct_answer": {
            "source": "user-direct",
            "row": row,
            "text": direct,
            "source_ref": "chat-after-recovery-observation",
            "captured_at": at(300),
            "observations": {
                "launch_route": route,
                "real_input_target_kept": "はい",
                "one_primary_screen": "はい",
            },
        },
        "adoption": {
            "decision": "採用",
            "approved_by": "利用者",
            "source": "user-direct",
            "source_ref": "chat-after-recovery-adoption",
            "text": "採用",
            "approved_at": at(600),
            "answer_sha256": sha(direct.encode()),
        },
    }
    name = f"W12c_{route}-python_at_script-20261107T120000Z.json"
    save(phase / "06-05-evidence" / name, answer)
    return root, phase, run, name, profile


def invoke(case, dry=True):
    root, phase, _, name, profile = case
    env = os.environ.copy()
    env["USERPROFILE"] = str(profile)
    return subprocess.run(  # noqa: S603 -- 隔離fixture内の固定helperのみ。
        [
            shutil.which("node"),
            str(phase / HELPER.name),
            name,
            *(["--dry-run"] if dry else []),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def snapshot(case):
    return {
        p.relative_to(case[0]).as_posix(): p.read_bytes()
        for p in case[0].rglob("*")
        if p.is_file()
    }


def edit(case, file, path, value):
    target = (
        case[1] / "06-05-evidence" / case[3] if file == "answer" else case[2] / file
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    save(target, data)
    if file == "w12c-machine.json":
        edit(case, "answer", ["machine_sha256"], sha(target.read_bytes()))


@pytest.mark.parametrize("route", ["explorer", "terminal"])
def test_w12c_python_route_dry_run_and_single_write(tmp_path, route):
    case = fixture(tmp_path, route)
    before = snapshot(case)
    result = invoke(case)
    assert result.returncode == 0, result.stderr
    assert snapshot(case) == before
    result = invoke(case, dry=False)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (case[1] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    assert ledger["cases"][0]["subrows"][0]["status"] == "pass"
    assert "1行pass・107行not-run" in (case[1] / "06-UAT.md").read_text(
        encoding="utf-8"
    )
    assert (
        case[1] / "06-05-evidence" / case[3].replace(".json", "-raw") / "copies.json"
    ).is_file()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: edit(c, "w12c-machine.json", ["input_target_after", "hwnd"], 6666),
        lambda c: edit(c, "w12c-machine.json", ["actual_foreground", "hwnd"], 0),
        lambda c: edit(
            c, "w12c-machine.json", ["api_return"], {"status": "unsupported"}
        ),
        lambda c: edit(c, "w12c-machine.json", ["launch_route", "route"], "explorer"),
        lambda c: edit(
            c, "w12c-machine.json", ["provenance_after_stop", "matched"], False
        ),
        lambda c: os.utime(c[2] / ("peer-" + "b" * 32) / "resource-audit.json", (1, 1)),
        lambda c: edit(
            c, "w12c-machine.json", ["launch_route", "terminal_command"], "& 'other'"
        ),
        lambda c: edit(c, "answer", ["direct_answer", "text"], "別行: はい"),
        lambda c: edit(c, "answer", ["adoption", "text"], "採用しない"),
        lambda c: edit(
            c, "answer", ["adoption", "approved_at"], "2000-01-01T00:00:00Z"
        ),
        lambda c: (c[1] / HELPER.name).write_bytes(
            (c[1] / HELPER.name).read_bytes() + b"\n// mutation"
        ),
        lambda c: (c[1] / "06-05-extra.cjs").write_text("new", encoding="utf-8"),
        lambda c: (c[0] / "tests/new_input.py").write_text("new", encoding="utf-8"),
        lambda c: (c[0] / "final/PageFolio.exe").write_bytes(b"changed"),
        lambda c: (c[0] / ".venv/Scripts/python.exe").write_bytes(b"changed"),
        lambda c: (c[1] / "06-W12C-COLLECTION.md").write_bytes(b"changed"),
    ],
)
def test_w12c_rejects_without_any_write(tmp_path, mutation):
    case = fixture(tmp_path)
    mutation(case)
    before = snapshot(case)
    for dry in (True, False):
        result = invoke(case, dry=dry)
        assert result.returncode != 0, result.stdout
        assert snapshot(case) == before


@pytest.mark.parametrize("route", ["explorer", "terminal"])
def test_w12c_exe_rows_remain_unsupported(tmp_path, route):
    case = fixture(tmp_path, route)
    edit(case, "answer", ["condition"], f"{route}-exe@production-exe")
    edit(case, "answer", ["row"], f"W12c/{route}-exe@production-exe")
    edit(case, "w12c-machine.json", ["row"], f"W12c/{route}-exe@production-exe")
    edit(case, "w12c-machine.json", ["kind"], "exe")
    edit(case, "w12c-machine.json", ["entry"], "production-exe")
    edit(case, "w12c-machine.json", ["api_return"], {"status": "unsupported"})
    old = case[1] / "06-05-evidence" / case[3]
    new_name = f"W12c_{route}-exe_at_production-exe-20261107T120000Z.json"
    old.rename(old.with_name(new_name))
    case = (*case[:3], new_name, case[4])
    before = snapshot(case)
    for dry in (True, False):
        result = invoke(case, dry=dry)
        assert result.returncode != 0
        assert "unsupported" in result.stderr
        assert snapshot(case) == before


@pytest.mark.parametrize("route", ["explorer", "terminal"])
def test_w12c_python_target_bytes_change_rejects_dry_and_write(tmp_path, route):
    case = fixture(tmp_path, route)
    target = (
        case[0]
        / ".venv/Scripts"
        / ("pythonw.exe" if route == "explorer" else "python.exe")
    )
    target.write_bytes(b"mutated-executable")
    before = snapshot(case)
    for dry in (True, False):
        result = invoke(case, dry=dry)
        assert result.returncode != 0
        assert snapshot(case) == before


def test_w12c_driver_refuses_existing_owner_without_start(tmp_path, monkeypatch):
    script = PHASE / "06-05-w12c-driver.py"
    spec = importlib.util.spec_from_file_location("w12c_driver_test", script)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    case = fixture(tmp_path)
    root, phase, _, _, _ = case
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "PHASE", phase)
    monkeypatch.setattr(driver, "provenance", lambda: {})
    monkeypatch.setattr(driver.support, "probe_owner", lambda: [{"state": "open"}])
    monkeypatch.setattr(
        driver.support,
        "read_distribution",
        lambda _p: {
            "exe_sha256": json.loads(
                (phase / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8")
            )["final_release"]["exe_sha256"],
            "tree_sha256": json.loads(
                (phase / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8")
            )["final_release"]["tree_sha256"],
        },
    )
    with pytest.raises(RuntimeError, match="既存production owner"):
        driver.collect("terminal-python@script", root / "final")


def test_w12c_short_deadline_recovers_owner_before_any_route(tmp_path, monkeypatch):
    script = PHASE / "06-05-w12c-driver.py"
    spec = importlib.util.spec_from_file_location("w12c_deadline_test", script)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    case = fixture(tmp_path)
    root, phase, _, _, _ = case
    build = json.loads((phase / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "PHASE", phase)
    monkeypatch.setattr(driver, "provenance", lambda: {})
    monkeypatch.setattr(driver, "verify_provenance", lambda _saved: None)
    monkeypatch.setattr(driver.support, "probe_owner", lambda: [])
    monkeypatch.setattr(
        driver.support,
        "read_distribution",
        lambda _p: {
            "exe_sha256": build["final_release"]["exe_sha256"],
            "tree_sha256": build["final_release"]["tree_sha256"],
        },
    )
    calls = []

    def command(action, run, extra=(), timeout=30):
        calls.append(action)
        if action == "start":
            run.mkdir()
            return {
                "expected_owner": {
                    "pid": 1234,
                    "process_created": CREATED,
                    "manual_deadline": {"due_monotonic": driver.time.monotonic() + 5},
                }
            }
        if action == "stop":
            return {"result.json": {"result": "primary"}}
        raise AssertionError("期限不足ならinspect/peerに進まない")

    monkeypatch.setattr(driver.base, "_command", command)
    with pytest.raises(RuntimeError, match="操作/回収期限余白不足"):
        driver.collect("terminal-python@script", root / "final")
    assert calls == ["start", "stop"]
    machine_files = list(
        (root / ".planning/tmp").glob("pagefolio-uat-*/w12c-machine.json")
    )
    assert len(machine_files) == 1
    assert json.loads(machine_files[0].read_text(encoding="utf-8"))["error"]


@pytest.mark.parametrize("changed", ["python", "instructions"])
def test_w12c_post_start_input_change_still_recovers_owner(
    tmp_path, monkeypatch, changed
):
    script = PHASE / "06-05-w12c-driver.py"
    spec = importlib.util.spec_from_file_location("w12c_drift_test", script)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    case = fixture(tmp_path)
    root, phase, _, _, _ = case
    build = json.loads((phase / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8"))
    target = (
        root / ".venv/Scripts/python.exe"
        if changed == "python"
        else phase / "06-W12C-COLLECTION.md"
    )
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "PHASE", phase)
    monkeypatch.setattr(driver, "PREPARE_SECONDS", 0)
    monkeypatch.setattr(
        driver,
        "provenance",
        lambda: (
            {"input_sha256": sha(target.read_bytes())}
            if changed == "instructions"
            else {}
        ),
    )
    monkeypatch.setattr(driver.support, "probe_owner", lambda: [])
    monkeypatch.setattr(
        driver.support,
        "read_distribution",
        lambda _p: {
            "exe_sha256": build["final_release"]["exe_sha256"],
            "tree_sha256": build["final_release"]["tree_sha256"],
        },
    )
    calls = []

    def command(action, run, extra=(), timeout=30):
        calls.append(action)
        if action == "start":
            run.mkdir()
            return {
                "expected_owner": {
                    "pid": 1234,
                    "process_created": CREATED,
                    "manual_deadline": {"due_monotonic": driver.time.monotonic() + 120},
                }
            }
        if action == "stop":
            return {"result.json": {"result": "primary"}}
        raise AssertionError("入力改変後にinspect/peerへ進まない")

    def change_after_start(_seconds):
        target.write_bytes(b"changed-after-start")

    monkeypatch.setattr(driver.base, "_command", command)
    monkeypatch.setattr(driver.time, "sleep", change_after_start)
    with pytest.raises(RuntimeError, match="変化"):
        driver.collect("terminal-python@script", root / "final")
    assert calls == ["start", "stop"]
    machine_files = list(
        (root / ".planning/tmp").glob("pagefolio-uat-*/w12c-machine.json")
    )
    assert len(machine_files) == 1
    machine = json.loads(machine_files[0].read_text(encoding="utf-8"))
    assert machine["stop"] == {"result.json": {"result": "primary"}}
    assert machine["provenance_after_stop"]["matched"] is False
