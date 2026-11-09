"""W12b専用。未改変EXE/Pythonの一回限りの外部混在観測と所有run回収。"""

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / ".planning/phases/06-release-validation"
sys.path.insert(0, str(ROOT))
from tests import release_uat_support as support  # noqa: E402
from tests import test_startup_windows as windows  # noqa: E402

ROWS = {
    "exe-exe-samecopy@production-exe": ("final", "copy"),
    "exe-script@production-exe": ("final", "script"),
    "script-exe@script": ("script", "final"),
    "exe-module@production-exe": ("final", "module"),
    "module-exe@module": ("module", "final"),
    "exe-tracer@production-exe": ("final", "tracer"),
    "tracer-exe@tracer": ("tracer", "final"),
    "exe-relocated-copy@production-exe": ("final", "copy"),
    "relocated-copy-exe@relocated-copy": ("copy", "final"),
}
INSPECT_BUDGET = 8
STOP_BUDGET = 15
MARGIN = 10


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(UTC).isoformat()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def collector_inputs():
    """今後の06-05 helper追加も次のrunに固定する。"""
    result = {}
    for item in sorted(PHASE.glob("06-05-*")):
        if item.suffix not in {".py", ".cjs"}:
            continue
        require(item.is_file() and not item.is_symlink(), "collector link/特殊ファイル")
        result[item.relative_to(ROOT).as_posix()] = sha(item)
    return result


def provenance():
    sources = windows._formal_source_inputs()
    for name in sources:
        item = ROOT / name
        require(
            item.resolve().is_relative_to(ROOT.resolve()) and not item.is_symlink(),
            "Python source範囲外/link",
        )
    return {
        "source_inputs": sources,
        "collector_inputs": collector_inputs(),
        "original_plugins": windows._formal_original_plugins(),
        "originals": windows._fingerprints(),
        "phase04": windows._formal_parent_gate(),
        "helper_sha256": sha(PHASE / "06-05-record-w12b.cjs"),
    }


def verify_provenance(saved):
    require(saved == provenance(), "現行source/collector/原本/親freshが開始時と不一致")


def tracer_contract():
    canonical = PHASE / "06-W12B-NEW-TRACER-20261107.json"
    record = json.loads(canonical.read_text(encoding="utf-8"))
    base = PHASE / "06-resume-20261106/w12b-tracer-prepared"
    source = base / "new-tracer-source-manifest.json"
    external = base / "new-tracer-report.json"
    embedded = base / "new-tracer-embedded-report.json"
    require(
        record["source_manifest_sha256"] == sha(source), "tracer source manifest不一致"
    )
    require(record["external_report_sha256"] == sha(external), "tracer外部report不一致")
    require(record["embedded_report_sha256"] == sha(embedded), "tracer組込report不一致")
    inputs = json.loads(source.read_text(encoding="utf-8"))
    require(len(inputs) == 64, "tracer入力64件不一致")
    plan = json.loads((base / "build-plan.json").read_text(encoding="utf-8"))
    execution = json.loads((base / "build-execution.json").read_text(encoding="utf-8"))
    require(
        execution["plan_sha256"] == sha(base / "build-plan.json")
        and execution["source_archive_sha256"] == plan["source_archive_sha256"]
        and execution["verified_input_count"] == len(inputs)
        and plan["source_commit"] == record["source_commit"],
        "tracer build plan/execution不一致",
    )
    source_dir = Path(plan["source_dir"])
    for name, expected in inputs.items():
        target = (source_dir / name).resolve()
        require(
            target.is_relative_to(source_dir.resolve()) and target.is_file(),
            "tracer source範囲外/欠落",
        )
        require(sha(target) == expected, f"tracer source bytes変化: {name}")
    startup = (source_dir / "pagefolio/startup_win32.py").read_text(encoding="utf-8")
    require(
        "class Win32Backend" in startup
        and "AllowSetForegroundWindow" in startup
        and "_allow_foreground" in startup
        and "Owner" in startup
        and "State" in startup,
        "tracer source起動排他/固定namespace/protocol未確認",
    )
    for report in (external, embedded):
        item = json.loads(report.read_text(encoding="utf-8"))
        require(
            item["success"] is True
            and item["status"] == "VERIFIED_BUILD"
            and item["artifact_role"] == "technical-tracer"
            and item["run_id"] == record["run_id"]
            and item["source_commit"] == record["source_commit"]
            and item["dirty_sha256"] == record["dirty_sha256"]
            and item["version"] == record["version"]
            and item["distribution_manifest"] == record["distribution_manifest"],
            "tracer両reportの同世代対応不一致",
        )
    distribution = Path(record["retained_path"])
    info = support.read_distribution(distribution)
    require(
        info["exe_sha256"] == record["exe_sha256"]
        and {k: v for k, v in info["files"].items() if k != "release-report.json"}
        == record["distribution_manifest"],
        "tracer保持tree不一致",
    )
    return record


def _command(action, run, extra=(), timeout=30):
    result = subprocess.run(  # noqa: S603 -- 固定harnessだけを実行。
        [
            sys.executable,
            str(ROOT / "tests/test_startup_windows.py"),
            "--uat",
            action,
            "--run",
            str(run),
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    require(result.returncode == 0, f"{action}失敗: {result.stderr}")
    return json.loads(result.stdout)


def _direct_answer(row, seconds):
    """前景snapshot後だけに質問し、有限時間で回収へ進む。"""
    received = []

    def read():
        try:
            received.append(input(f"観察原文を「{row}: はい/はい/はい」の形で入力 > "))
        except EOFError:
            pass

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(seconds)
    return received[0] if received else None


def collect(row, final_distribution, *, prepeer_seconds=20, observe_seconds=12):
    require(row in ROWS, "W12b行ID不正")
    require(
        0 <= prepeer_seconds <= 20 and 0 <= observe_seconds <= 12,
        "準備/観察期限不正",
    )
    primary, secondary = ROWS[row]
    saved = provenance()
    tracer = tracer_contract() if "tracer" in (primary, secondary) else None
    final = Path(final_distribution).resolve()
    build = json.loads((PHASE / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8"))
    designated = Path(
        build["final_release"]
        .get("loss_incident", {})
        .get("restored_final_dir", build["final_release"]["final_dir"])
    ).resolve()
    require(final == designated, "最終配布元pathが世代5の復元正本と不一致")
    info = support.read_distribution(final)
    require(
        build["generation"] == 5
        and info["exe_sha256"] == build["final_release"]["exe_sha256"]
        and info["tree_sha256"] == build["final_release"]["tree_sha256"],
        "最終v1.10.2配布tree不一致",
    )
    peer_run = None
    primary_run = None
    python_owner = primary in {"script", "module"}
    machine = {
        "schema": "w12b-machine-v1",
        "row": f"W12b/{row}",
        "primary": primary,
        "secondary": secondary,
        "prepeer_seconds": prepeer_seconds,
        "started_at": now(),
        "provenance": saved,
        "tracer_contract": tracer,
        "events": [],
        "api_return": {
            "status": "unsupported",
            "reason": "未改変EXE内部の許可API戻りを外部取得できない",
        },
    }
    try:
        secondary_dist = (
            Path(tracer["retained_path"]) if secondary == "tracer" else final
        )
        if secondary in {"final", "copy", "tracer"}:
            peer_run = support.prepare(
                secondary_dist,
                "W12b",
                role="technical-tracer-real-exe"
                if secondary == "tracer"
                else "same-version-copy"
                if secondary == "copy"
                else "final-release-candidate",
            )["run"]
            peer_manifest = support.load_run(peer_run)
            require(
                support.verify_copy(peer_manifest)["ok"]
                and support._source_unchanged(peer_manifest),
                "二次配布copy/source変化",
            )
        verify_provenance(saved)
        if python_owner:
            primary_run = ROOT / ".planning/tmp" / ("pagefolio-uat-" + uuid4().hex)
            owner = _command(
                "start",
                primary_run,
                ("--w12a-primary", primary, "--production", "--w12b-mixed"),
            )
            pid = owner["expected_owner"]["pid"]
            created = owner["expected_owner"]["process_created"]
            due = owner["expected_owner"]["manual_deadline"]["due_monotonic"]
        else:
            distribution = (
                Path(tracer["retained_path"]) if primary == "tracer" else final
            )
            primary_run = support.prepare(
                distribution,
                "W12b",
                role="technical-tracer-real-exe"
                if primary == "tracer"
                else "same-version-copy"
                if primary == "copy"
                else "final-release-candidate",
                overlays={support.SETTINGS_NAME: None},
            )["run"]
            owner = support.start(primary_run)
            pid, created = owner["pid"], owner["created"]
            due = time.monotonic() + 120
        machine["run"] = str(primary_run)
        machine["peer_run"] = str(peer_run) if peer_run else None
        machine["owner"] = {"pid": pid, "created": str(created)}
        machine["events"].append({"step": "start", "at": now(), "owner": owner})
        require(
            time.monotonic()
            + prepeer_seconds
            + 18
            + observe_seconds
            + INSPECT_BUDGET
            + STOP_BUDGET
            + MARGIN
            < due,
            "owner期限余白不足",
        )
        print(
            f"{machine['row']}: 一次画面で編集/入力状態を作ってください。"
            f"{prepeer_seconds}秒後に二次を一回起動します。",
            flush=True,
        )
        time.sleep(prepeer_seconds)
        machine["events"].append({"step": "state-preparation", "at": now()})
        require(
            time.monotonic()
            + 18
            + observe_seconds
            + INSPECT_BUDGET
            + STOP_BUDGET
            + MARGIN
            < due,
            "二次前のowner期限余白不足",
        )
        verify_provenance(saved)
        live_owner = support.process_identity(pid)
        require(
            live_owner and live_owner["alive"] and live_owner["created"] == created,
            "一次owner PID/FILETIMEを確認できない。二次を起動しない",
        )
        if secondary in {"script", "module"}:
            require(support.probe_owner(), "EXE一次owner未確立")
            expected = {"pid": pid, "process_created": created}
            child, path = windows._spawn(
                Path(primary_run),
                "fixed-production",
                f"entry-{secondary}",
                fixture_name="peer-" + uuid4().hex,
                expected_owner=expected,
            )
            try:
                out, err = child.communicate(timeout=18)
                (path / "stdout.log").write_text(out, encoding="utf-8")
                (path / "stderr.log").write_text(err, encoding="utf-8")
                require(child.returncode == 0, "Python二次が正常終了しない")
                audit = json.loads(
                    (path / "resource-audit.json").read_text(encoding="utf-8")
                )
                machine["api_return"] = audit.get("allow_foreground") or {
                    "status": "unsupported",
                    "reason": "Python二次のAPI監査欠落",
                }
                machine["peer_identity"] = {
                    "entry": secondary,
                    "pid": child.pid,
                    "fixture": str(path),
                    "result": json.loads(
                        (path / "result.json").read_text(encoding="utf-8")
                    ),
                    "audit": audit,
                }
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        else:
            require(peer_run is not None, "EXE二次run欠落")
            if python_owner:
                peer_manifest = support.load_run(peer_run)
                require(support.verify_copy(peer_manifest)["ok"], "二次copy変化")
                require(support._source_unchanged(peer_manifest), "二次配布元変化")
                require(support.probe_owner(), "Python一次owner未確立")
                exe = Path(peer_manifest["copy"]) / "PageFolio.exe"
                child = support._launch(peer_manifest, exe, subprocess.Popen)
                record = support._record_for(child, peer_manifest, "peer", exe)
                peer_manifest["processes"].append(record)
                peer_manifest["status"] = "running"
                support.save_run(peer_manifest)
            else:
                record = support.peer(primary_run, with_run=peer_run)
            exit_deadline = min(due - 20, time.monotonic() + 18)
            while time.monotonic() < exit_deadline:
                identity = support.process_identity(record["pid"])
                if identity is None or not identity["alive"]:
                    break
                require(identity["created"] == record["created"], "二次PID再利用")
                time.sleep(0.05)
            else:
                raise RuntimeError("EXE二次が期限内に終了しない")
            machine["exe_peer_exit"] = {
                "at": now(),
                "identity": support.process_identity(record["pid"]),
            }
            machine["peer_identity"] = record
        machine["events"].append({"step": "peer", "at": now()})
        machine["after_peer"] = support.foreground_info()
        machine["after_peer_at"] = now()
        machine["owner_after_peer"] = support.process_identity(pid)
        machine["events"].append({"step": "foreground", "at": machine["after_peer_at"]})
        require(
            machine["owner_after_peer"]
            and machine["owner_after_peer"]["alive"]
            and machine["owner_after_peer"]["created"] == created
            and machine["after_peer"]["pid"] == pid
            and machine["after_peer"]["hwnd"] > 0,
            "二次後の一次同一性/実前景不一致",
        )
        require(
            time.monotonic() + observe_seconds + INSPECT_BUDGET + STOP_BUDGET + MARGIN
            < due,
            "観察/stop期限余白不足",
        )
        machine["direct_answer_text"] = _direct_answer(f"W12b/{row}", observe_seconds)
        machine["direct_answer_at"] = now() if machine["direct_answer_text"] else None
        machine["events"].append({"step": "direct-answer", "at": now()})
        require(
            time.monotonic() + INSPECT_BUDGET + STOP_BUDGET + MARGIN < due,
            "inspect/stop期限余白不足",
        )
        machine["inspection"] = (
            _command("inspect", primary_run, timeout=INSPECT_BUDGET)
            if python_owner
            else support.inspect(primary_run)
        )
        machine["events"].append({"step": "inspect", "at": now()})
    except Exception as error:
        machine["error"] = str(error)
        machine["events"].append({"step": "failed", "at": now()})
        raise
    finally:
        if primary_run is not None:
            try:
                machine["stop"] = (
                    _command("stop", primary_run, timeout=STOP_BUDGET)
                    if python_owner
                    else support.stop(primary_run)
                )
                machine["events"].append({"step": "stop", "at": now()})
            except Exception as error:
                machine["stop_error"] = str(error)
        if peer_run is not None and python_owner:
            try:
                machine["peer_stop"] = support.stop(peer_run)
            except Exception as error:
                machine["peer_stop_error"] = str(error)
        try:
            verify_provenance(saved)
            machine["provenance_after_stop"] = {"matched": True}
        except Exception as error:
            machine["provenance_after_stop"] = {"matched": False, "error": str(error)}
        machine["finished_at"] = now()
        if primary_run is not None and Path(primary_run).is_dir():
            target = Path(primary_run) / "w12b-machine.json"
            target.write_text(
                json.dumps(machine, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "run": str(primary_run),
                    "row": machine["row"],
                    "api_return": machine["api_return"],
                    "error": machine.get("error"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row", required=True, choices=ROWS)
    parser.add_argument("--final-distribution", required=True, type=Path)
    args = parser.parse_args()
    collect(args.row, args.final_distribution)


if __name__ == "__main__":
    main()
