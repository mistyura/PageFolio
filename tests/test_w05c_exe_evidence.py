"""W05c 実 EXE 採用 helper の隔離された契約試験。実 EXE は起動しない。"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests import release_uat_support as support

SOURCE = (
    Path(__file__).resolve().parents[1]
    / ".planning/phases/06-release-validation/06-05-record-w05c-exe.cjs"
)
NAME = "W05c_quit-no_at_production-exe-20261106T120000Z.json"
RUN_ID = "a" * 32
HASH = "b" * 64
TREE = "c" * 64
INPUT = "d" * 64
CREATED = 134383350518202484
PEER_CREATED = 134383350518202999


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def seal(fixture):
    run = fixture["run"]
    answer = fixture["answer"]
    manifest = fixture["manifest"]
    for stage, entry in answer["inspections"].items():
        file = run / "evidence" / f"inspect-{entry['index']:03d}.json"
        write_json(file, fixture["observations"][stage])
        entry["sha256"] = digest(file.read_bytes())
    manifest["observations"] = list(fixture["observations"].values())
    manifest_file = run / "manifest.json"
    write_json(manifest_file, manifest)
    finalized = datetime(2026, 11, 6, 12, 0, 8, 500000, tzinfo=timezone.utc)
    os.utime(manifest_file, (finalized.timestamp(), finalized.timestamp()))
    answer["manifest_sha256"] = digest(manifest_file.read_bytes())
    answer["originals_sha256"] = digest(
        json.dumps(
            manifest["snapshots"][0]["originals"],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    )
    answer["adoption"]["answer_sha256"] = digest(
        answer["direct_answer"]["text"].encode()
    )
    write_json(fixture["phase"] / "06-05-evidence" / NAME, answer)


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "project"
    phase = root / ".planning/phases/06-release-validation"
    run = root / ".planning/tmp" / f"release-uat-{RUN_ID}"
    dist = root / "distribution" / "PageFolio-v1.10.2"
    phase.mkdir(parents=True)
    (run / "dist").mkdir(parents=True)
    dist.mkdir(parents=True)
    shutil.copyfile(SOURCE, phase / SOURCE.name)
    exe = b"fixed executable fixture"
    exe_hash = digest(exe)
    (run / "dist" / "PageFolio.exe").write_bytes(exe)
    (run / "fixtures").mkdir()
    fixture_pdf = b"three-page PDF fixture"
    (run / "fixtures" / "edit-three-page.pdf").write_bytes(fixture_pdf)
    (dist / "PageFolio.exe").write_bytes(exe)
    write_json(
        dist / "release-report.json",
        {
            "run_id": RUN_ID,
            "version": "v1.10.2",
            "distribution_manifest": {"PageFolio.exe": exe_hash},
        },
    )
    write_json(
        phase / "06-BUILD-EVIDENCE.json",
        {
            "generation": 5,
            "version": "v1.10.2",
            "final_release": {
                "exe_sha256": exe_hash,
                "tree_sha256": TREE,
                "input_manifest_sha256": INPUT,
                "runs": [{"run_id": RUN_ID}],
                "final_dir": str(dist),
            },
        },
    )
    write_json(
        phase / "06-PROTECTION-EVIDENCE.json",
        {
            "generation": 5,
            "build_ref": {
                "final_run_id": RUN_ID,
                "exe_sha256": exe_hash,
                "tree_sha256": TREE,
            },
        },
    )
    row = {
        "card": "W05c/quit-no@production-exe",
        "subrow": "quit-no@production-exe",
        "entry": "production-exe",
        "evidence_kind": "production-exe",
        "status": "not-run",
        "generation": 5,
        "expected_binary_sha256": exe_hash,
        "release_requirement": "required",
        "required_observations": [
            "quit_confirm_shown",
            "answered_no",
            "edit_state_kept",
            "owner_kept",
            "stop_outcome",
            "foreground_after",
        ],
    }
    write_json(
        phase / "06-MANUAL-EVIDENCE.json",
        {
            "cases": [
                {"id": "W05c", "subrows": [row]},
                {
                    "id": "W05b",
                    "subrows": [{"card": "W05b/sentinel", "status": "not-run"}],
                },
            ]
        },
    )
    (phase / "06-UAT.md").write_text(
        "本受入は必須108行中0行pass・108行not-run・W11対象外2行not-run。\n"
        "### W05c/quit-no@production-exe\n"
        "- **状態**: not-run / 準備: 未準備\n\n### next\n",
        encoding="utf-8",
    )
    original = {
        "pagefolio_settings.json": {"exists": False, "sha256": None},
        "ocr_custom_prompt.md": {"exists": False, "sha256": None},
        "ocr_summary_prompt.md": {"exists": False, "sha256": None},
        "plugins": None,
    }
    owner = {
        "role": "primary",
        "pid": 101,
        "created": CREATED,
        "exit": "closed",
        "started_at": "2026-11-06T11:59:52Z",
    }
    peer = {
        "role": "peer",
        "pid": 202,
        "created": PEER_CREATED,
        "exit": "already-exited",
        "peer_source": {
            "run_id": RUN_ID,
            "role": "final-release-candidate",
            "exe_sha256": exe_hash,
        },
    }
    manifest = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "run": str(run),
        "copy": str(run / "dist"),
        "case": "W05c",
        "entry": "production-exe",
        "evidence_kind": "production-exe",
        "role": "final-release-candidate",
        "status": "stopped",
        "generation": 1,
        "fixtures": {
            "edit-three-page": {
                "pages": 3,
                "path": str(run / "fixtures" / "edit-three-page.pdf"),
            }
        },
        "overlay": {"pagefolio_settings.json": None},
        "overlay_log": [
            {
                "name": "pagefolio_settings.json",
                "sha256": None,
                "at": "2026-11-06T11:59:51Z",
            }
        ],
        "source": {
            "version": "v1.10.2",
            "exe_sha256": exe_hash,
            "tree_sha256": TREE,
            "distribution": str(dist),
            "report_run_id": RUN_ID,
        },
        "processes": [owner, peer],
        "environment": {"os": "Windows", "session_id": 1, "elevated": False},
        "observations": [],
        "snapshots": [
            {
                "label": "before-start",
                "at": "2026-11-06T11:59:50Z",
                "originals": original,
                "source_unchanged": True,
                "copy": {"ok": True},
            },
            {
                "label": "before-stop",
                "at": "2026-11-06T12:00:07Z",
                "originals": original,
                "source_unchanged": True,
                "copy": {"ok": True},
            },
            {
                "label": "after-stop",
                "at": "2026-11-06T12:00:08Z",
                "originals": original,
                "source_unchanged": True,
                "copy": {"ok": True},
            },
        ],
    }
    labels = ["before_confirm", "during_confirm", "after_no", "after_peer"]
    observations = {}
    for i, label in enumerate(labels, 1):
        primary = {
            "role": "primary",
            "pid": 101,
            "created": CREATED,
            "identity": "same",
            "alive": True,
            "windows": [{"visible": True, "class": "TkTopLevel"}],
        }
        if i == 2:
            primary["windows"].append({"visible": True, "class": "#32770"})
        processes = [primary]
        if i > 1:
            processes.append(
                {
                    "role": "peer",
                    "pid": 202,
                    "created": PEER_CREATED,
                    "identity": "gone" if i == 4 else "same",
                    "alive": i != 4,
                    "windows": [],
                }
            )
        observations[label] = {
            "at": f"2026-11-06T12:00:0{i}Z",
            "processes": processes,
            "foreground": {"owned_by": "primary", "pid": 101},
            "owner_probe": [{"kind": "mutex", "state": "open"}],
            "copy": {"ok": True},
        }
    observations["after_peer"]["foreground"] = {
        "owned_by": None,
        "pid": 404,
        "title": "ChatGPT",
    }
    text = "いいえを押し、確認が消え、編集と画面と一次ownerが残った"
    answer = {
        "schema": "w05c-exe-v1",
        "case": "W05c",
        "row": row["card"],
        "entry": "production-exe",
        "condition": "quit-no",
        "collection_status": "machine_collected_pending_answer",
        "run": str(run),
        "owner_created": str(CREATED),
        "peer_created": str(PEER_CREATED),
        "binary_sha256": exe_hash,
        "fixture_sha256": digest(fixture_pdf),
        "tree_sha256": TREE,
        "input_manifest_sha256": INPUT,
        "inspections": {label: {"index": i} for i, label in enumerate(labels, 1)},
        "peer_constructed": 0,
        "peer_constructed_basis": "external-no-new-primary-window-and-same-owner",
        "confirm_disappeared_before_collection": True,
        "confirm_disappeared_basis": "direct-user-observation",
        "direct_answer": {
            "source": "user-direct",
            "source_ref": "chat message 123",
            "question": "終了確認が消え、編集とownerを確認しましたか？",
            "text": text,
            "captured_at": "2026-11-06T12:00:03.500Z",
            "quit_confirm_shown": True,
            "answered_no": True,
            "confirm_disappeared": True,
            "edit_state_kept": True,
            "owner_kept": True,
            "foreground_after": True,
            "observed_before_collection": True,
        },
        "adoption": {
            "decision": "採用",
            "approved_by": "利用者",
            "source": "user-direct",
            "source_ref": "chat message 456",
            "text": "採用してよい",
            "approved_at": "2026-11-06T12:00:10Z",
        },
        "stop_outcome": "closed",
        "stop_observed_at": "2026-11-06T12:00:09Z",
    }
    result = {
        "root": root,
        "phase": phase,
        "run": run,
        "manifest": manifest,
        "observations": observations,
        "answer": answer,
    }
    seal(result)
    return result


def snapshot(root):
    return {
        str(p.relative_to(root)): digest(p.read_bytes())
        for p in root.rglob("*")
        if p.is_file()
    }


def invoke(bundle, *args):
    node = shutil.which("node")
    assert node is not None
    return subprocess.run(  # noqa: S603 - 固定した隔離fixture内のhelperだけを実行
        [node, str(bundle["phase"] / SOURCE.name), NAME, *args],
        cwd=bundle["root"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_dry_run_is_read_only_and_accepts_normal_or_forced_stop(bundle):
    before = snapshot(bundle["root"])
    result = invoke(bundle, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert snapshot(bundle["root"]) == before
    bundle["manifest"]["processes"][0]["exit"] = "terminated"
    bundle["answer"]["stop_outcome"] = "terminated"
    seal(bundle)
    assert invoke(bundle, "--dry-run").returncode == 0


def test_adoption_changes_only_target_row_and_keeps_raw_copy(bundle):
    before = json.loads(
        (bundle["phase"] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    result = invoke(bundle)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (bundle["phase"] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    row = ledger["cases"][0]["subrows"][0]
    assert ledger["cases"][1] == before["cases"][1]
    assert row["status"] == "pass"
    assert bundle["observations"]["after_no"]["foreground"]["pid"] == 101
    assert bundle["observations"]["after_peer"]["foreground"]["pid"] == 404
    assert [entry["key"] for entry in row["raw_inputs"]] == ["answer", "adoption"]
    assert row["observations"]["stop_outcome"]["value"] == "closed"
    assert row["binary_sha256"] == bundle["answer"]["binary_sha256"]
    assert (
        bundle["phase"]
        / "06-05-evidence"
        / NAME.replace(".json", "-raw")
        / "copies.json"
    ).is_file()
    assert invoke(bundle).returncode != 0


def test_adopted_row_satisfies_shared_uat_audit_without_changing_answer(bundle):
    result = invoke(bundle)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (bundle["phase"] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    row = ledger["cases"][0]["subrows"][0]
    audit = support.Audit("require-pass")
    support._check_subrow(
        "W05c",
        row,
        {"exe_sha256": bundle["answer"]["binary_sha256"]},
        audit,
        strict=True,
    )
    assert audit.ok, audit.reasons
    assert row["raw_inputs"][0]["text"] == bundle["answer"]["direct_answer"]["text"]


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["answer"]["adoption"].update(decision=False),
        lambda b: b["answer"]["adoption"].update(decision="不採用"),
        lambda b: b["answer"]["adoption"].update(decision="unknown"),
        lambda b: b["answer"]["adoption"].update(approved_at="2026-11-06T12:00:07Z"),
        lambda b: b["answer"]["adoption"].update(source_ref="chat message 123"),
        lambda b: b["answer"]["direct_answer"].update(source="agent-paraphrase"),
        lambda b: b["answer"]["direct_answer"].update(edit_state_kept=False),
        lambda b: b["answer"].update(binary_sha256=HASH),
        lambda b: b["answer"].update(schema="w05c-v3"),
        lambda b: b["answer"].update(peer_constructed=1),
        lambda b: b["observations"]["after_no"]["processes"][0].update(pid=999),
        lambda b: b["observations"]["after_peer"]["processes"][0].update(alive=False),
        lambda b: b["observations"]["after_peer"]["processes"][1].update(alive=True),
        lambda b: b["observations"]["after_no"].update(
            foreground={"owned_by": None, "pid": 404, "title": "ChatGPT"}
        ),
        lambda b: b["observations"]["after_no"]["processes"][0]["windows"].append(
            {"visible": True, "class": "#32770"}
        ),
        lambda b: b["observations"]["after_no"].update(at="2026-11-06T12:00:01Z"),
        lambda b: b["answer"]["direct_answer"].update(
            captured_at="2026-11-06T12:00:09Z"
        ),
        lambda b: b["manifest"]["snapshots"][2].update(
            originals={
                **copy.deepcopy(b["manifest"]["snapshots"][0]["originals"]),
                "plugins": {"unsafe": HASH},
            }
        ),
        lambda b: b["manifest"]["processes"][0].update(created=CREATED + 10000),
    ],
)
def test_rejected_evidence_never_writes(bundle, change):
    change(bundle)
    seal(bundle)
    before = snapshot(bundle["root"])
    result = invoke(bundle)
    assert result.returncode != 0
    assert snapshot(bundle["root"]) == before


def test_rejects_run_outside_owned_tree(bundle):
    original = copy.deepcopy(bundle["answer"])
    bundle["answer"]["run"] = str(bundle["root"] / "other")
    seal(bundle)
    before = snapshot(bundle["root"])
    assert invoke(bundle).returncode != 0
    assert snapshot(bundle["root"]) == before
    assert original["run"] != bundle["answer"]["run"]


@pytest.mark.parametrize(
    "approved_at",
    [
        "2026-11-06T12:00:04.500Z",  # 最終inspect後・回収前
        "2026-11-06T12:00:07.500Z",  # before-stop後・after-stop前
        "2026-11-06T12:00:08.250Z",  # snapshot後・最終manifest書込前
        "2026-11-06T12:00:08.750Z",  # manifest後・stop観測時刻前
        "2026-11-06T12:00:09Z",  # stop観測と同時は「後」ではない
    ],
)
def test_adoption_before_complete_collection_is_rejected_without_writes(
    bundle, approved_at
):
    bundle["answer"]["adoption"]["approved_at"] = approved_at
    seal(bundle)
    before = snapshot(bundle["root"])
    assert invoke(bundle).returncode != 0
    assert snapshot(bundle["root"]) == before


@pytest.mark.parametrize("text", ["採用", "採用。", "採用してよい", "採用してよい。"])
def test_exact_affirmative_adoption_is_allowed_in_dry_run(bundle, text):
    bundle["answer"]["adoption"]["text"] = f"  {text}  "
    seal(bundle)
    before = snapshot(bundle["root"])
    result = invoke(bundle, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert snapshot(bundle["root"]) == before


def test_adoption_original_text_is_kept_when_whitespace_is_trimmed_for_judgment(bundle):
    original = "  採用  "
    bundle["answer"]["adoption"]["text"] = original
    seal(bundle)
    result = invoke(bundle)
    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (bundle["phase"] / "06-MANUAL-EVIDENCE.json").read_text(encoding="utf-8")
    )
    assert ledger["cases"][0]["subrows"][0]["raw_inputs"][1]["text"] == original


@pytest.mark.parametrize(
    "text",
    [
        "不採用",
        "採用しない",
        "まだ採用できない",
        "採用してよいか不明",
        "採用してよい？",
    ],
)
def test_negative_or_ambiguous_adoption_is_read_only_rejected(bundle, text):
    bundle["answer"]["adoption"]["text"] = text
    seal(bundle)
    before = snapshot(bundle["root"])
    for args in (("--dry-run",), ()):
        assert invoke(bundle, *args).returncode != 0
        assert snapshot(bundle["root"]) == before
