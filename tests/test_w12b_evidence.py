"""W12bの採用境界を隔離runだけで検証する。実GUI/EXEは起動しない。"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning/phases/06-release-validation"
HELPER = PHASE / "06-05-record-w12b.cjs"
CREATED = 133123456789012345


def sha(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def fixture(tmp_path):
    root = tmp_path / "project"
    phase = root / ".planning/phases/06-release-validation"
    evidence = phase / "06-05-evidence"
    evidence.mkdir(parents=True)
    for name in (
        "06-05-record-w12b.cjs",
        "06-05-w12b-driver.py",
        "06-05-w12a-driver.py",
    ):
        shutil.copyfile(PHASE / name, phase / name)
    sources = {}
    for name in (
        "pagefolio.py",
        "pagefolio/__main__.py",
        "tests/test_startup_windows.py",
        ".planning/phases/06-release-validation/06-05-w12a-driver.py",
    ):
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        if not file.exists():
            file.write_text(name, encoding="utf-8")
        sources[name] = sha(file.read_bytes())
    collectors = {
        p.relative_to(root).as_posix(): sha(p.read_bytes())
        for p in phase.glob("06-05-*")
        if p.suffix in {".py", ".cjs"}
    }
    parent = root / ".planning/phases/04-startup-control/04-VERIFICATION.md"
    parent.parent.mkdir(parents=True)
    parent.write_text('status: passed\ncovered_digest: "fixture"\n', encoding="utf-8")
    p4 = {
        "status": "passed",
        "covered_digest": "fixture",
        "report_sha256": sha(parent.read_bytes()),
    }
    profile = tmp_path / "user"
    cli = profile / ".codex/gsd-core/bin/gsd-tools.cjs"
    cli.parent.mkdir(parents=True)
    cli.write_text(
        'process.stdout.write(JSON.stringify({status:"passed"}));\n', encoding="utf-8"
    )
    dist = root / "final"
    dist.mkdir()
    (dist / "PageFolio.exe").write_bytes(b"fixed-final-exe")
    (dist / "release-report.json").write_text("{}\n", encoding="utf-8")
    files = {p.name: sha(p.read_bytes()) for p in sorted(dist.iterdir())}
    tree = sha(
        json.dumps(
            {"dirs": [], "files": files}, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )
    save(
        phase / "06-BUILD-EVIDENCE.json",
        {
            "generation": 5,
            "version": "v1.10.2",
            "final_release": {
                "final_dir": str(root / "lost-original-output"),
                "loss_incident": {"restored_final_dir": str(dist)},
                "exe_sha256": files["PageFolio.exe"],
                "tree_sha256": tree,
                "input_manifest_sha256": "inputhash",
            },
        },
    )
    run = root / ".planning/tmp" / ("release-uat-" + "a" * 32)
    peer = run / ("peer-" + "b" * 32)
    peer.mkdir(parents=True)
    api = {"pid": 1234, "allowed": True, "os_error": 0}
    # 実起動に合わせ、peer_identity.pid(2345)はvenv launcher、実二次はその子。
    audit = {
        "pid": 2346,
        "parent_pid": 2345,
        "session_id": 1,
        "owner_result": "existing",
        "verified_owner": {"pid": 1234, "process_created": CREATED},
        "allow_foreground": api,
    }
    save(peer / "resource-audit.json", audit)
    save(peer / "result.json", {"constructed": 0, "result": "completed"})
    save(peer / "expected-owner.json", {"pid": 1234, "process_created": CREATED})
    save(
        run / "manifest.json",
        {
            "run": str(run),
            "case": "W12b",
            "status": "stopped",
            "source": {
                "exe_sha256": files["PageFolio.exe"],
                "tree_sha256": tree,
                "version": "v1.10.2",
            },
            "copy": str(run / "dist"),
            "environment": {"os": "Windows 11", "elevated": False, "session_id": 1},
            "overlay": {"pagefolio_settings.json": None},
            "overlay_log": [
                {
                    "name": "pagefolio_settings.json",
                    "sha256": None,
                    "at": "2026-01-01T00:00:00+00:00",
                }
            ],
            "processes": [
                {
                    "role": "primary",
                    "pid": 1234,
                    "created": CREATED,
                    "started_at": "2026-01-01T00:00:01+00:00",
                    "exit": "closed",
                }
            ],
            "snapshots": [
                {
                    "source_unchanged": True,
                    "copy": {
                        "ok": True,
                        "distribution_changed": [],
                        "missing_dirs": [],
                        "extra_dirs": [],
                        "undeclared": [],
                        "overlay_changed": ["pagefolio_settings.json"],
                        "locked_unverified": [],
                    },
                }
            ],
        },
    )
    now = datetime.now(UTC)

    def at(seconds):
        return (now + timedelta(seconds=seconds)).isoformat()

    row = "W12b/exe-script@production-exe"
    direct = row + ": はい/はい/はい"
    machine = {
        "schema": "w12b-machine-v1",
        "row": row,
        "run": str(run),
        "primary": "final",
        "secondary": "script",
        "error": None,
        "provenance": {
            "source_inputs": sources,
            "collector_inputs": collectors,
            "original_plugins": {},
            "originals": {
                n: None
                for n in (
                    "pagefolio_settings.json",
                    "ocr_custom_prompt.md",
                    "ocr_summary_prompt.md",
                )
            },
            "phase04": p4,
            "helper_sha256": sha((phase / HELPER.name).read_bytes()),
        },
        "events": [
            {"step": "start", "at": at(0), "owner": {"pid": 1234}},
            {"step": "state-preparation", "at": at(20)},
            {"step": "peer", "at": at(20.5)},
            {"step": "foreground", "at": at(20.7)},
            {"step": "direct-answer", "at": at(21.2)},
            {"step": "inspect", "at": at(21.6)},
            {"step": "stop", "at": at(21.8)},
        ],
        "prepeer_seconds": 20,
        "direct_answer_text": direct,
        "direct_answer_at": at(21.1),
        "api_return": api,
        "owner": {"pid": 1234, "created": str(CREATED)},
        "owner_after_peer": {
            "pid": 1234,
            "created": CREATED,
            "alive": True,
            "session_id": 1,
            "elevated": False,
        },
        "after_peer": {"pid": 1234, "hwnd": 5678},
        "peer_identity": {
            "entry": "script",
            "pid": 2345,
            "fixture": str(peer),
            "result": {"constructed": 0},
            "audit": audit,
        },
        "inspection": {
            "processes": [
                {
                    "role": "primary",
                    "pid": 1234,
                    "identity": "same",
                    "alive": True,
                    "session_id": 1,
                }
            ],
            "foreground": {"pid": 9999},
        },
        "stop": [{"pid": 1234, "result": "closed"}],
        "provenance_after_stop": {"matched": True},
        "finished_at": at(22),
    }
    save(run / "w12b-machine.json", machine)
    card = {
        "subrow": "exe-script@production-exe",
        "card": row,
        "entry": "production-exe",
        "condition": "exe-script",
        "evidence_kind": "production-exe",
        "status": "not-run",
        "generation": 5,
        "release_requirement": "required",
        "subject": {
            "role": "final-release-candidate",
            "binary_sha256": files["PageFolio.exe"],
            "version": "v1.10.2",
        },
        "peer": {"role": "python-entry", "entry": "script"},
        "required_observations": [
            "single_primary_screen",
            "same_session_return",
            "primary_state_kept",
            "api_return",
            "actual_foreground",
            "peer_identity",
        ],
    }
    save(
        phase / "06-MANUAL-EVIDENCE.json",
        {"cases": [{"id": "W12b", "subrows": [card]}]},
    )
    (phase / "06-UAT.md").write_text(
        "本受入は必須108行中0行pass・108行not-run・W11対象外2行not-run。\n"
        "### W12b/exe-script@production-exe\n- **状態**: not-run\n",
        encoding="utf-8",
    )
    answer = {
        "schema": "w12b-answer-v1",
        "condition": "exe-script@production-exe",
        "row": row,
        "run": str(run),
        "machine_sha256": sha((run / "w12b-machine.json").read_bytes()),
        "direct_answer": {
            "source": "user-direct",
            "row": row,
            "text": direct,
            "source_ref": "console-observation",
            "captured_at": at(21.3),
            "observations": {
                "single_primary_screen": "はい",
                "same_session_return": "はい",
                "primary_state_kept": "はい",
            },
        },
        "adoption": {
            "decision": "採用",
            "approved_by": "利用者",
            "source": "user-direct",
            "source_ref": "chat-after-recovery",
            "text": "採用",
            "approved_at": at(300),
            "answer_sha256": sha(direct.encode()),
        },
    }
    name = "W12b_exe-script_at_production-exe-20261107T120000Z.json"
    save(evidence / name, answer)
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
    if file == "w12b-machine.json":
        edit(case, "answer", ["machine_sha256"], sha(target.read_bytes()))


def edit_audit(case, key, value):
    """二次のresource-audit.jsonとmachine埋込auditを同じ値に揃えて変更する。"""
    edit(case, "peer-" + "b" * 32 + "/resource-audit.json", [key], value)
    edit(case, "w12b-machine.json", ["peer_identity", "audit", key], value)


def test_w12b_python_peer_dry_run_and_single_write(tmp_path):
    case = fixture(tmp_path)
    before = snapshot(case)
    result = invoke(case)
    assert result.returncode == 0, result.stderr
    assert snapshot(case) == before
    result = invoke(case, dry=False)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (case[1] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    row = ledger["cases"][0]["subrows"][0]
    assert row["status"] == "pass" and row["answer"].startswith(
        "W12b/exe-script@production-exe"
    )
    assert "1行pass・107行not-run" in (case[1] / "06-UAT.md").read_text(
        encoding="utf-8"
    )
    assert (
        case[1] / "06-05-evidence" / case[3].replace(".json", "-raw") / "copies.json"
    ).is_file()
    assert row["observations"]["peer_identity"] == {
        "entry": "script",
        "pid": 2345,
        "fixture": "peer-" + "b" * 32,
        "audit_pid": 2346,
        "audit_parent_pid": 2345,
    }


def test_w12b_accepts_direct_python_peer_without_launcher(tmp_path):
    case = fixture(tmp_path)
    # launcherを介さない環境ではPopen.pidが実二次PIDそのものになる。
    edit_audit(case, "pid", 2345)
    edit_audit(case, "parent_pid", 4321)
    before = snapshot(case)
    result = invoke(case)
    assert result.returncode == 0, result.stderr
    assert snapshot(case) == before


def test_w12b_mixed_start_refuses_existing_production_owner(tmp_path, monkeypatch):
    from tests import release_uat_support as support
    from tests import test_startup_windows as windows

    run = tmp_path / "project/.planning/tmp" / ("pagefolio-uat-" + "a" * 32)
    monkeypatch.setattr(windows, "_ROOT", tmp_path / "project")
    monkeypatch.setattr(
        support, "probe_owner", lambda: [{"kind": "mutex", "state": "open"}]
    )
    with pytest.raises(AssertionError, match="既存production owner"):
        windows._uat_harness(
            [
                "start",
                "--run",
                str(run),
                "--w12a-primary",
                "script",
                "--production",
                "--w12b-mixed",
            ]
        )
    assert not run.exists()


def test_w12b_exe_primary_declares_settings_overlay_before_start(tmp_path, monkeypatch):
    script = PHASE / "06-05-w12b-driver.py"
    spec = importlib.util.spec_from_file_location("w12b_overlay_test", script)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    case = fixture(tmp_path)
    root, phase = case[:2]
    final = root / "final"
    build = json.loads((phase / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8"))
    run = root / ".planning/tmp" / ("release-uat-" + "c" * 32)
    run.mkdir(parents=True)
    calls = []
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "PHASE", phase)
    monkeypatch.setattr(driver, "provenance", lambda: {})
    monkeypatch.setattr(driver, "verify_provenance", lambda _saved: None)
    monkeypatch.setattr(
        driver.support,
        "read_distribution",
        lambda _path: {
            "exe_sha256": build["final_release"]["exe_sha256"],
            "tree_sha256": build["final_release"]["tree_sha256"],
        },
    )

    def prepare(_distribution, _case, **kwargs):
        assert kwargs["overlays"] == {driver.support.SETTINGS_NAME: None}
        calls.append("prepare-with-settings-overlay")
        return {"run": str(run)}

    def start(_run):
        calls.append("start")
        raise RuntimeError("synthetic-start-stop")

    monkeypatch.setattr(driver.support, "prepare", prepare)
    monkeypatch.setattr(driver.support, "start", start)
    monkeypatch.setattr(driver.support, "stop", lambda _run: calls.append("stop"))
    with pytest.raises(RuntimeError, match="synthetic-start-stop"):
        driver.collect("exe-script@production-exe", final, prepeer_seconds=0)
    assert calls == ["prepare-with-settings-overlay", "start", "stop"]


def test_w12b_short_owner_deadline_stops_before_peer(tmp_path, monkeypatch):
    script = PHASE / "06-05-w12b-driver.py"
    spec = importlib.util.spec_from_file_location("w12b_driver_test", script)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    root = tmp_path / "project"
    phase = root / ".planning/phases/06-release-validation"
    phase.mkdir(parents=True)
    final = root / "final"
    final.mkdir()
    save(
        phase / "06-BUILD-EVIDENCE.json",
        {
            "generation": 5,
            "final_release": {
                "final_dir": str(final),
                "exe_sha256": "exe",
                "tree_sha256": "tree",
            },
        },
    )
    monkeypatch.setattr(driver, "ROOT", root)
    monkeypatch.setattr(driver, "PHASE", phase)
    monkeypatch.setattr(driver, "provenance", lambda: {})
    monkeypatch.setattr(driver, "verify_provenance", lambda _saved: None)
    monkeypatch.setattr(
        driver.support,
        "read_distribution",
        lambda _path: {"exe_sha256": "exe", "tree_sha256": "tree"},
    )
    peer = root / ".planning/tmp" / ("release-uat-" + "b" * 32)
    peer.mkdir(parents=True)
    monkeypatch.setattr(
        driver.support, "prepare", lambda *_args, **_kwargs: {"run": str(peer)}
    )
    monkeypatch.setattr(driver.support, "load_run", lambda _run: {})
    monkeypatch.setattr(driver.support, "verify_copy", lambda _manifest: {"ok": True})
    monkeypatch.setattr(driver.support, "_source_unchanged", lambda _manifest: True)
    calls = []

    def command(action, run, extra=(), timeout=30):
        calls.append(action)
        if action == "start":
            run.mkdir(parents=True)
            return {
                "expected_owner": {
                    "pid": 1234,
                    "process_created": CREATED,
                    "manual_deadline": {"due_monotonic": driver.time.monotonic() + 5},
                }
            }
        if action == "stop":
            return {"result.json": {"result": "primary"}}
        raise AssertionError("期限不足でpeer/inspectを実行しない")

    monkeypatch.setattr(driver, "_command", command)
    monkeypatch.setattr(driver.support, "stop", lambda _run: calls.append("peer-stop"))
    with pytest.raises(RuntimeError, match="owner期限余白不足"):
        driver.collect("script-exe@script", final)
    assert calls == ["start", "stop", "peer-stop"]
    machine_files = list(
        (root / ".planning/tmp").glob("pagefolio-uat-*/w12b-machine.json")
    )
    assert len(machine_files) == 1
    assert json.loads(machine_files[0].read_text(encoding="utf-8"))["error"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: edit(
            c,
            "w12b-machine.json",
            ["api_return"],
            {"status": "unsupported", "reason": "EXE内部未取得"},
        ),
        lambda c: edit(c, "w12b-machine.json", ["owner_after_peer", "pid"], 999),
        lambda c: edit(c, "w12b-machine.json", ["after_peer", "pid"], 999),
        lambda c: edit(
            c, "w12b-machine.json", ["provenance_after_stop", "matched"], False
        ),
        lambda c: edit(
            c,
            "w12b-machine.json",
            ["direct_answer_text"],
            "W12b/exe-script@production-exe: いいえ/はい/はい",
        ),
        lambda c: edit(
            c,
            "answer",
            ["direct_answer", "text"],
            "W12b/exe-module@production-exe: はい",
        ),
        lambda c: edit(c, "answer", ["adoption", "decision"], "不採用"),
        lambda c: edit(c, "answer", ["adoption", "decision"], True),
        lambda c: edit(c, "answer", ["adoption", "text"], "採用しない"),
        lambda c: edit(
            c, "answer", ["adoption", "approved_at"], "2000-01-01T00:00:00Z"
        ),
        lambda c: (c[0] / "tests/new_input.py").write_text("new", encoding="utf-8"),
        lambda c: (c[0] / "pagefolio_settings.json").write_text(
            "changed", encoding="utf-8"
        ),
        lambda c: (c[1] / "06-05-extra.cjs").write_text("new", encoding="utf-8"),
        lambda c: (c[1] / HELPER.name).write_bytes(
            (c[1] / HELPER.name).read_bytes() + b"\n// changed\n"
        ),
        lambda c: (c[2] / "manifest.json").write_text("{}", encoding="utf-8"),
        lambda c: edit(c, "manifest.json", ["snapshots", 0, "copy", "ok"], False),
        lambda c: edit(
            c, "manifest.json", ["snapshots", 0, "copy", "undeclared"], ["rogue.dat"]
        ),
        lambda c: edit(
            c, "manifest.json", ["snapshots", 0, "copy", "extra_dirs"], ["rogue"]
        ),
        lambda c: edit(
            c,
            "manifest.json",
            ["snapshots", 0, "copy", "distribution_changed"],
            ["PageFolio.exe"],
        ),
        lambda c: edit(c, "manifest.json", ["overlay"], {}),
        lambda c: save(
            c[2] / ("peer-" + "b" * 32) / "expected-owner.json",
            {"pid": 1234, "process_created": CREATED + 1},
        ),
        lambda c: edit_audit(c, "parent_pid", 999),
        lambda c: edit_audit(c, "parent_pid", None),
        lambda c: edit_audit(c, "pid", 1234),
        lambda c: (
            edit(c, "w12b-machine.json", ["peer_identity", "pid"], None),
            edit_audit(c, "parent_pid", None),
        ),
        lambda c: (
            edit(c, "w12b-machine.json", ["peer_identity", "pid"], 1234),
            edit_audit(c, "parent_pid", 1234),
        ),
        lambda c: edit(
            c, "w12b-machine.json", ["peer_identity", "audit", "session_id"], 2
        ),
        lambda c: (c[0] / "final/PageFolio.exe").write_bytes(b"modified"),
    ],
)
def test_w12b_rejects_without_any_write(tmp_path, mutation):
    case = fixture(tmp_path)
    mutation(case)
    before = snapshot(case)
    for dry in (True, False):
        result = invoke(case, dry=dry)
        assert result.returncode != 0, result.stdout
        assert snapshot(case) == before
