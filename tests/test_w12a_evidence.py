"""W12a正式採用の境界を隔離ファイルだけで検証する。"""

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
HELPER = ROOT / ".planning/phases/06-release-validation/06-05-record-w12a.cjs"
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
    shutil.copyfile(HELPER, phase / HELPER.name)
    userprofile = tmp_path / "user"
    cli = userprofile / ".codex/gsd-core/bin/gsd-tools.cjs"
    cli.parent.mkdir(parents=True)
    cli.write_text(
        'process.stdout.write(JSON.stringify({status:"passed"}));\n', encoding="utf-8"
    )
    source_inputs = {}
    for name in (
        "pagefolio.py",
        "pagefolio/__main__.py",
        "tests/test_startup_windows.py",
        ".planning/phases/06-release-validation/06-05-w12a-driver.py",
    ):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(name, encoding="utf-8")
        source_inputs[name] = sha(p.read_bytes())
    report = root / ".planning/phases/04-startup-control/04-VERIFICATION.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        'status: passed\ncovered_digest: "v4:sha256:fixture"\n', encoding="utf-8"
    )
    p4 = {
        "status": "passed",
        "covered_digest": "v4:sha256:fixture",
        "report_sha256": sha(report.read_bytes()),
    }
    run = root / ".planning/tmp" / ("pagefolio-uat-" + "a" * 32)
    run.mkdir(parents=True)
    primary = run / "entry-owner-script"
    peer = run / ("peer-" + "b" * 32)
    for directory in (primary, peer):
        directory.mkdir()
    owner = {"pid": 1234, "process_created": CREATED, "manual": True}
    now = datetime.now(UTC)

    def at(seconds):
        return (now + timedelta(seconds=seconds)).isoformat()

    manifest = {
        "w12a_schema": "w12a-v1",
        "w12a_primary": "script",
        "w12a_peer_entry": "module",
        "role": "entry-owner-script",
        "run": str(run),
        "namespace": "fixture",
        "fixture": str(primary),
        "expected_owner": owner,
        "environment": {"os": "Windows", "is_admin": False, "session_id": 1},
        "originals_before": {
            "pagefolio_settings.json": None,
            "ocr_custom_prompt.md": None,
            "ocr_summary_prompt.md": None,
        },
        "source_commit": "fixture",
        "formal_provenance": {
            "source_inputs": source_inputs,
            "original_plugins": {},
            "phase04": p4,
            "w12a_helper_sha256": sha((phase / HELPER.name).read_bytes()),
        },
    }
    save(run / "manifest.json", manifest)
    save(primary / "ready", {"pid": 1234, "process_created": CREATED})
    owner_result = {
        "constructed": 1,
        "restored": 1,
        "status_preserved": True,
        "result": "primary",
    }
    save(primary / "result.json", owner_result)
    save(primary / "resource-audit.json", {"pid": 1234})
    save(peer / "result.json", {"constructed": 0, "result": "completed"})
    save(
        peer / "resource-audit.json",
        {
            "pid": 2345,
            "verified_owner": {"pid": 1234, "process_created": CREATED},
            "owner_result": "existing",
            "allow_foreground": {"pid": 1234, "allowed": True, "os_error": 0},
            "terminal_result": "completed",
        },
    )
    save(peer / "expected-owner.json", owner)
    (peer / "stdout.log").write_text("{}", encoding="utf-8")
    (peer / "stderr.log").write_text("", encoding="utf-8")
    (run / "w12a-peer-started").write_text("module", encoding="utf-8")
    foreground = {
        "entry": "module",
        "owner_verified": True,
        "hwnd": 5678,
        "pid": 1234,
        "peer_fixture": str(peer),
        "at_utc": at(1),
    }
    save(run / "w12a-after-peer.json", foreground)
    save(
        run / "inspection.json",
        {
            "manifest": manifest,
            "originals_unchanged": True,
            "result.json": owner_result,
        },
    )
    save(run / "provenance-before-stop.json", {"matched": True})
    events = [
        {
            "step": "start",
            "at_utc": at(0),
            "role": "entry-owner-script",
            "owner": owner,
        },
        {"step": "peer", "at_utc": at(1.1), "result": {"constructed": 0}},
        {"step": "foreground", "at_utc": at(1.2), "snapshot": foreground},
        {"step": "inspect", "at_utc": at(1.3), "originals_unchanged": True},
        {"step": "stop", "at_utc": at(1.4), "originals_unchanged": True},
    ]
    driver = {
        "schema": "w12a-driver-v1",
        "run": str(run),
        "primary": "script",
        "secondary": "module",
        "events": events,
        "finished_at": at(2),
    }
    save(run / "w12a-driver.json", driver)
    save(
        phase / "06-BUILD-EVIDENCE.json",
        {
            "generation": 5,
            "version": "v1.10.2",
            "final_release": {"input_manifest_sha256": "buildhash"},
        },
    )
    row = {
        "subrow": "script-module@script",
        "card": "W12a/script-module@script",
        "entry": "script",
        "condition": "script-module",
        "evidence_kind": "python-real",
        "status": "not-run",
        "generation": 5,
        "release_requirement": "required",
        "required_observations": [
            "one_primary_screen",
            "secondary_returns_to_primary",
            "state_kept",
            "api_return",
            "actual_foreground",
        ],
    }
    save(
        phase / "06-MANUAL-EVIDENCE.json", {"cases": [{"id": "W12a", "subrows": [row]}]}
    )
    (phase / "06-UAT.md").write_text(
        "本受入は必須108行中0行pass・108行not-run・W11対象外2行not-run。\n"
        "### W12a/script-module@script\n- **状態**: not-run\n",
        encoding="utf-8",
    )
    human = {
        "source": "user-direct",
        "row": row["card"],
        "text": "W12a/script-module@script: 画面1つ、同じ一次へ戻り、編集状態保持。",
        "source_ref": "chat-observation",
        "captured_at": at(3),
        "observations": {
            "one_primary_screen": "はい",
            "secondary_returns_to_primary": "はい",
            "state_kept": "はい",
        },
    }
    answer = {
        "schema": "w12a-answer-v1",
        "primary": "script",
        "secondary": "module",
        "row": row["card"],
        "run": str(run),
        "manifest_sha256": sha((run / "manifest.json").read_bytes()),
        "owner_process_created": str(CREATED),
        "direct_answer": human,
        "adoption": {
            "decision": "採用",
            "approved_by": "利用者",
            "source": "user-direct",
            "source_ref": "chat-adoption",
            "text": "採用",
            "answer_sha256": sha(human["text"].encode()),
            "approved_at": at(300),
        },
    }
    name = "W12a_script-module_at_script-20261106T120000Z.json"
    save(evidence / name, answer)
    return root, phase, run, name, userprofile


def invoke(case, *, dry=True):
    root, phase, _, name, profile = case
    environment = os.environ.copy()
    environment["USERPROFILE"] = str(profile)
    return subprocess.run(  # noqa: S603 -- 隔離fixture内に複製した固定helperのみ。
        [
            shutil.which("node"),
            str(phase / HELPER.name),
            name,
            *(["--dry-run"] if dry else []),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        check=False,
    )


def snapshot(case):
    root = case[0]
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_dry_run_and_single_row_write(tmp_path):
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
    assert ledger["cases"][0]["subrows"][0]["status"] == "pass"
    assert "pass" in (case[1] / "06-UAT.md").read_text(encoding="utf-8")
    from tests.release_uat_support import _check_subrow

    class Audit:
        def __init__(self):
            self.failures = []

        def fail(self, message):
            self.failures.append(message)

    audit = Audit()
    _check_subrow(
        "W12a",
        ledger["cases"][0]["subrows"][0],
        {"input_manifest_sha256": "buildhash"},
        audit,
        strict=True,
    )
    assert not audit.failures


def test_formal_cli_provenance_is_rechecked_without_gui(tmp_path, monkeypatch):
    from tests import test_startup_windows as windows

    case = fixture(tmp_path)
    root, _, _, _, profile = case
    monkeypatch.setattr(windows.Path, "home", lambda: profile)
    saved = {
        "source_inputs": windows._formal_source_inputs(root),
        "original_plugins": windows._formal_original_plugins(root),
        "phase04": windows._formal_parent_gate(root),
        "w12a_helper_sha256": windows._w12a_helper_sha256(root),
    }
    assert saved["phase04"]["status"] == "passed"
    assert saved["source_inputs"]["pagefolio.py"] == sha(
        (root / "pagefolio.py").read_bytes()
    )
    windows._check_formal_provenance({"formal_provenance": saved}, root)
    (root / "pagefolio.py").write_text("changed", encoding="utf-8")
    with pytest.raises(AssertionError, match="Python入力"):
        windows._check_formal_provenance({"formal_provenance": saved}, root)


def test_w12a_stop_recovers_even_after_original_changes(tmp_path, monkeypatch):
    from tests import test_startup_windows as windows

    root = tmp_path / "project"
    run = root / ".planning/tmp" / ("pagefolio-uat-" + "a" * 32)
    fixture_dir = run / "entry-owner-script"
    fixture_dir.mkdir(parents=True)
    original = {"pagefolio_settings.json": "before"}
    manifest = {
        "case": "entry-owner",
        "w12a_schema": "w12a-v1",
        "w12a_primary": "script",
        "role": "entry-owner-script",
        "run": str(run),
        "namespace": "fixture",
        "fixture": str(fixture_dir),
        "expected_owner": {"pid": 1234, "process_created": CREATED},
        "originals_before": original,
        "formal_provenance": {},
    }
    save(run / "manifest.json", manifest)
    save(fixture_dir / "ready", {"pid": 1234, "process_created": CREATED})
    save(fixture_dir / "result.json", {"result": "primary"})
    monkeypatch.setattr(windows, "_ROOT", root)
    monkeypatch.setattr(
        windows, "_fingerprints", lambda: {"pagefolio_settings.json": "changed"}
    )
    windows._uat_harness(["stop", "--run", str(run)])
    assert (fixture_dir / "stop").exists()
    assert (
        json.loads((run / "provenance-before-stop.json").read_text(encoding="utf-8"))[
            "matched"
        ]
        is False
    )
    assert (
        json.loads((run / "inspection.json").read_text(encoding="utf-8"))[
            "originals_unchanged"
        ]
        is False
    )


def test_w12a_driver_insufficient_deadline_stops_without_peer(tmp_path, monkeypatch):
    from datetime import datetime

    driver_path = ROOT / ".planning/phases/06-release-validation/06-05-w12a-driver.py"
    spec = importlib.util.spec_from_file_location("w12a_driver_test", driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    monkeypatch.setattr(driver, "ROOT", tmp_path)
    calls = []

    def fake_command(action, run, extra=(), **_kwargs):
        calls.append(action)
        if action == "start":
            run.mkdir(parents=True)
            now = driver.time.monotonic()
            return {
                "role": "entry-owner-script",
                "expected_owner": {
                    "manual_deadline": {
                        "delay_ms": 120000,
                        "registered_monotonic": now - 115,
                        "ready_monotonic": now,
                        "due_monotonic": now + 5,
                    }
                },
            }
        if action == "stop":
            return {"originals_unchanged": True}
        raise AssertionError("期限不足でpeer/inspectを呼ばない")

    monkeypatch.setattr(driver, "command", fake_command)
    with pytest.raises(RuntimeError, match="余白不足"):
        driver.collect("script", "module")
    assert calls == ["start", "stop"]
    assert datetime.fromisoformat(
        json.loads(
            next(
                tmp_path.glob(".planning/tmp/pagefolio-uat-*/w12a-driver.json")
            ).read_text(encoding="utf-8")
        )["finished_at"]
    )


def test_relocated_copy_hash_is_checked(tmp_path):
    case = fixture(tmp_path)
    root, phase, run, old_name, profile = case
    peer = run / ("peer-" + "b" * 32)
    alternate = peer / "alternate"
    (alternate / "pagefolio").mkdir(parents=True)
    shutil.copyfile(root / "pagefolio.py", alternate / "pagefolio.py")
    shutil.copyfile(root / "pagefolio/__main__.py", alternate / "pagefolio/__main__.py")
    overwrite(run / "w12a-after-peer.json", "entry", "relocated")
    manifest_path = run / "manifest.json"
    overwrite(manifest_path, "w12a_peer_entry", "relocated")
    overwrite(run / "w12a-driver.json", "secondary", "relocated")
    driver = json.loads((run / "w12a-driver.json").read_text(encoding="utf-8"))
    driver["events"][2]["snapshot"]["entry"] = "relocated"
    save(run / "w12a-driver.json", driver)
    (run / "w12a-peer-started").write_text("relocated", encoding="utf-8")
    inspected = json.loads((run / "inspection.json").read_text(encoding="utf-8"))
    inspected["manifest"]["w12a_peer_entry"] = "relocated"
    save(run / "inspection.json", inspected)
    ledger_path = phase / "06-MANUAL-EVIDENCE.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    row = ledger["cases"][0]["subrows"][0]
    row["card"] = "W12a/script-relocated@script"
    row["subrow"] = "script-relocated@script"
    row["condition"] = "script-relocated"
    save(ledger_path, ledger)
    (phase / "06-UAT.md").write_text(
        "本受入は必須108行中0行pass・108行not-run・W11対象外2行not-run。\n"
        "### W12a/script-relocated@script\n- **状態**: not-run\n",
        encoding="utf-8",
    )
    answer_path = phase / "06-05-evidence" / old_name
    answer = json.loads(answer_path.read_text(encoding="utf-8"))
    answer["secondary"] = "relocated"
    answer["row"] = row["card"]
    answer["direct_answer"]["row"] = row["card"]
    answer["direct_answer"]["text"] = "W12a/script-relocated@script: 3点ともはい。"
    answer["adoption"]["answer_sha256"] = sha(answer["direct_answer"]["text"].encode())
    answer["manifest_sha256"] = sha(manifest_path.read_bytes())
    new_name = old_name.replace("script-module", "script-relocated")
    save(answer_path.with_name(new_name), answer)
    answer_path.unlink()
    relocated_case = (root, phase, run, new_name, profile)
    assert invoke(relocated_case).returncode == 0
    (alternate / "pagefolio/__main__.py").write_text("changed", encoding="utf-8")
    before = snapshot(relocated_case)
    for dry in (True, False):
        result = invoke(relocated_case, dry=dry)
        assert result.returncode != 0
        assert snapshot(relocated_case) == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: edit(
            c, "direct_answer", "observations", "state_kept", value="いいえ"
        ),
        lambda c: edit(c, "adoption", "decision", value="不採用"),
        lambda c: edit(c, "adoption", "decision", value=True),
        lambda c: edit(c, "adoption", "text", value="採用しない"),
        lambda c: edit(c, "adoption", "text", value="まだ採用できない"),
        lambda c: edit(c, "adoption", "text", value="採用してよいか不明"),
        lambda c: edit(c, "adoption", "approved_at", value="2000-01-01T00:00:00Z"),
        lambda c: edit(c, "owner_process_created", value="133123456789012346"),
        lambda c: edit(c, "primary", value="module"),
        lambda c: edit(c, "manifest_sha256", value="0" * 64),
        lambda c: overwrite(c[2] / "w12a-after-peer.json", "pid", 999),
        lambda c: overwrite(
            c[2] / ("peer-" + "b" * 32) / "resource-audit.json",
            "verified_owner",
            {"pid": 999, "process_created": CREATED},
        ),
        lambda c: overwrite(
            c[2] / ("peer-" + "b" * 32) / "resource-audit.json",
            "allow_foreground",
            {"pid": 1234, "allowed": "yes", "os_error": 0},
        ),
        lambda c: overwrite(c[2] / "provenance-before-stop.json", "matched", False),
        lambda c: (c[0] / "pagefolio.py").write_text("changed", encoding="utf-8"),
        lambda c: (c[0] / "tests/added.py").write_text("added", encoding="utf-8"),
        lambda c: (c[0] / "tests/test_startup_windows.py").unlink(),
        lambda c: (c[1] / HELPER.name).write_bytes(
            (c[1] / HELPER.name).read_bytes() + b"\n// changed\n"
        ),
        lambda c: edit(
            c, "direct_answer", "text", value="W12a/module-module@module: 3点ともはい。"
        ),
        lambda c: (
            c[0] / ".planning/phases/04-startup-control/04-VERIFICATION.md"
        ).write_text("status: stale\ncovered_digest: changed\n", encoding="utf-8"),
        lambda c: (c[2] / "w12a-peer-started").write_text("script", encoding="utf-8"),
        lambda c: edit(c, "run", value=str(c[0] / ".." / "outside")),
    ],
)
def test_rejection_is_no_write(tmp_path, mutation):
    case = fixture(tmp_path)
    mutation(case)
    before = snapshot(case)
    for dry in (True, False):
        result = invoke(case, dry=dry)
        assert result.returncode != 0
        assert snapshot(case) == before


def edit(case, *keys, value):
    p = case[1] / "06-05-evidence" / case[3]
    data = json.loads(p.read_text(encoding="utf-8"))
    item = data
    for key in keys[:-1]:
        item = item[key]
    item[keys[-1]] = value
    save(p, data)


def overwrite(path, key, value):
    data = json.loads(path.read_text(encoding="utf-8"))
    data[key] = value
    save(path, data)
