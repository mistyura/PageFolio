"""W12c専用。本人によるExplorer/端末起動を外部観測し、所有一次だけ回収する。"""

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / ".planning/phases/06-release-validation"
sys.path.insert(0, str(ROOT))
from tests import release_uat_support as support  # noqa: E402

BASE_SPEC = importlib.util.spec_from_file_location(
    "w12b_collection", PHASE / "06-05-w12b-driver.py"
)
require_base = BASE_SPEC is not None and BASE_SPEC.loader is not None
if not require_base:
    raise RuntimeError("W12b共通採取module欠落")
base = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(base)

ROWS = {
    "explorer-python@script": ("explorer", "python", "script"),
    "terminal-python@script": ("terminal", "python", "script"),
    "explorer-exe@production-exe": ("explorer", "exe", "production-exe"),
    "terminal-exe@production-exe": ("terminal", "exe", "production-exe"),
}
PREPARE_SECONDS = 20
LAUNCH_SECONDS = 38
INPUT_SECONDS = 12
STOP_BUDGET = 15
INSPECT_BUDGET = 8
MARGIN = 10


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def now():
    return datetime.now(UTC).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance():
    saved = base.provenance()
    saved["w12b_helper_sha256"] = saved.pop("helper_sha256")
    saved["helper_sha256"] = sha(PHASE / "06-05-record-w12c.cjs")
    saved["collection_doc_sha256"] = sha(PHASE / "06-W12C-COLLECTION.md")
    python_paths = {
        name: ROOT / ".venv/Scripts" / name for name in ("python.exe", "pythonw.exe")
    }
    require(
        all(
            item.is_file()
            and not item.is_symlink()
            and item.resolve().is_relative_to(ROOT.resolve())
            for item in python_paths.values()
        ),
        "固定Python実行体path/link不正",
    )
    saved["python_executables"] = {
        name: sha(item) for name, item in python_paths.items()
    }
    return saved


def verify_provenance(saved):
    require(saved == provenance(), "現行source/collector/原本/親fresh変化")


def powershell_arg(value):
    return "'" + str(value).replace("'", "''") + "'"


def python_peer_fixture(run, owner):
    peer = Path(run) / ("peer-" + uuid4().hex)
    peer.mkdir()
    (peer / "plugins").mkdir()
    (peer / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    for name in ("ocr_custom_prompt.md", "ocr_summary_prompt.md"):
        (peer / name).write_text("isolated test prompt", encoding="utf-8")
    (peer / "expected-owner.json").write_text(
        json.dumps({"pid": owner["pid"], "process_created": owner["created"]}),
        encoding="utf-8",
    )
    return peer


def make_shortcut(link, target, arguments):
    """実Explorerクリック用.lnkを作る。起動自体は利用者本人だけが行う。"""
    env = os.environ.copy()
    env.update(
        PF_LINK=str(link),
        PF_TARGET=str(target),
        PF_ARGUMENTS=subprocess.list2cmdline(arguments),
        PF_CWD=str(ROOT),
    )
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:PF_LINK);"
        "$s.TargetPath=$env:PF_TARGET;$s.Arguments=$env:PF_ARGUMENTS;"
        "$s.WorkingDirectory=$env:PF_CWD;$s.Save()"
    )
    powershell = (
        Path(os.environ["SystemRoot"])
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    require(powershell.is_file(), "PowerShell欠落")
    result = subprocess.run(  # noqa: S603 -- 固定PowerShellと環境変数で一時.lnkだけ作る。
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    require(
        result.returncode == 0 and link.is_file(), f"shortcut作成失敗: {result.stderr}"
    )
    return sha(link)


def route_artifact(route, kind, run, peer=None):
    if kind == "python":
        py = (
            ROOT
            / ".venv/Scripts"
            / ("pythonw.exe" if route == "explorer" else "python.exe")
        )
        require(py.is_file(), "固定Python実行体欠落")
        args = [
            str(ROOT / "tests/test_startup_windows.py"),
            "_test_scenario_bootstrap",
            str(peer),
            "fixed-production",
            "entry-script",
        ]
        target = py
    else:
        target = Path(run) / "dist/PageFolio.exe"
        require(target.is_file(), "隔離EXE欠落")
        args = []
    result = {
        "route": route,
        "kind": kind,
        "target": str(target),
        "target_sha256": sha(target),
        "arguments": args,
    }
    if route == "explorer" and kind == "python":
        link = Path(run) / "W12c-Python.lnk"
        result.update(
            shortcut=str(link), shortcut_sha256=make_shortcut(link, target, args)
        )
        result["instruction"] = f"Explorerで {link} をダブルクリックしてください"
    elif route == "explorer":
        result["instruction"] = f"Explorerで {target} をダブルクリックしてください"
    else:
        command = "& " + " ".join(powershell_arg(x) for x in [target, *args])
        result["terminal_command"] = command
        result["instruction"] = f"PowerShell端末で次を本人が実行: {command}"
    return result


def verify_route_target(artifact):
    require(
        sha(artifact["target"]) == artifact["target_sha256"],
        "本人起動用実行体bytes変化",
    )


def exe_processes(exe):
    """外部の生存process一覧。見逃した短命processを捏造しない。"""
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    array = (ctypes.c_ulong * 8192)()
    needed = ctypes.c_ulong()
    psapi.EnumProcesses.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
    psapi.EnumProcesses.restype = ctypes.c_int
    require(
        psapi.EnumProcesses(array, ctypes.sizeof(array), ctypes.byref(needed)),
        "EXE process列挙不能",
    )
    expected = os.path.normcase(os.path.abspath(exe))
    found = []
    for pid in array[: needed.value // ctypes.sizeof(ctypes.c_ulong)]:
        identity = support.process_identity(pid)
        if (
            identity
            and identity["image"]
            and os.path.normcase(os.path.abspath(identity["image"])) == expected
        ):
            found.append(identity)
    return found


def collect(row, final_distribution):
    require(row in ROWS, "W12c行ID不正")
    route, kind, entry = ROWS[row]
    saved = provenance()
    final = Path(final_distribution).resolve()
    build = json.loads((PHASE / "06-BUILD-EVIDENCE.json").read_text(encoding="utf-8"))
    designated = Path(
        build["final_release"]
        .get("loss_incident", {})
        .get("restored_final_dir", build["final_release"]["final_dir"])
    ).resolve()
    require(final == designated, "世代5最終配布元path不一致")
    info = support.read_distribution(final)
    require(
        build["generation"] == 5
        and build["version"] == "v1.10.2"
        and info["exe_sha256"] == build["final_release"]["exe_sha256"]
        and info["tree_sha256"] == build["final_release"]["tree_sha256"],
        "最終配布tree/hash不一致",
    )
    machine = {
        "schema": "w12c-machine-v1",
        "row": "W12c/" + row,
        "route": route,
        "kind": kind,
        "entry": entry,
        "provenance": saved,
        "events": [],
        "api_return": {
            "status": "unsupported",
            "reason": "未改変EXE内部API戻りを外部取得できない",
        },
    }
    run = None
    try:
        require(not support.probe_owner(), "既存production owner不在を確認できない")
        if kind == "python":
            run = ROOT / ".planning/tmp" / ("pagefolio-uat-" + uuid4().hex)
            started = base._command(
                "start",
                run,
                ("--w12a-primary", "script", "--production", "--w12b-mixed"),
            )
            owner = started["expected_owner"]
            pid, created = owner["pid"], owner["process_created"]
            due = owner["manual_deadline"]["due_monotonic"]
        else:
            run = Path(
                support.prepare(
                    final,
                    "W12c",
                    role="final-release-candidate",
                    overlays={support.SETTINGS_NAME: None},
                )["run"]
            )
            started = support.start(run)
            pid, created = started["pid"], started["created"]
            due = time.monotonic() + 120
        machine.update(run=str(run), owner={"pid": pid, "created": str(created)})
        machine["events"].append({"step": "start", "at": now(), "owner": started})
        require(
            time.monotonic()
            + PREPARE_SECONDS
            + LAUNCH_SECONDS
            + INPUT_SECONDS
            + INSPECT_BUDGET
            + STOP_BUDGET
            + MARGIN
            < due,
            "操作/回収期限余白不足",
        )
        peer = (
            python_peer_fixture(run, {"pid": pid, "created": created})
            if kind == "python"
            else None
        )
        machine["launch_route"] = route_artifact(route, kind, run, peer)
        machine["peer_fixture"] = str(peer) if peer else None
        verify_provenance(saved)
        print(
            "一次画面の実入力欄を選び、20秒以内に入力状態を準備してください。",
            flush=True,
        )
        time.sleep(PREPARE_SECONDS)
        machine["events"].append({"step": "input-preparation", "at": now()})
        require(
            time.monotonic()
            + LAUNCH_SECONDS
            + INPUT_SECONDS
            + INSPECT_BUDGET
            + STOP_BUDGET
            + MARGIN
            < due,
            "起動前の回収期限余白不足",
        )
        verify_provenance(saved)
        verify_route_target(machine["launch_route"])
        identity = support.process_identity(pid)
        require(
            identity
            and identity["alive"]
            and identity["created"] == created
            and support.probe_owner(),
            "一次owner身元/固定namespace不一致",
        )
        machine["input_target_before"] = support.foreground_info()
        require(
            machine["input_target_before"]["pid"] == pid
            and machine["input_target_before"]["hwnd"] > 0,
            "一次入力先が前景にない",
        )
        print(machine["launch_route"]["instruction"], flush=True)
        print(
            "起動直後に同じ一次入力欄へ戻り、本人が実キー入力してください。", flush=True
        )
        launch_at = time.monotonic()
        seen_exe = []
        audit = None
        while time.monotonic() - launch_at < LAUNCH_SECONDS:
            require(
                time.monotonic() + INPUT_SECONDS + INSPECT_BUDGET + STOP_BUDGET + MARGIN
                < due,
                "二次待機中の回収期限余白不足",
            )
            if kind == "python":
                audit_file = peer / "resource-audit.json"
                result_file = peer / "result.json"
                if audit_file.is_file() and result_file.is_file():
                    audit = json.loads(audit_file.read_text(encoding="utf-8"))
                    machine["peer_result"] = json.loads(
                        result_file.read_text(encoding="utf-8")
                    )
                    break
            else:
                found = exe_processes(Path(run) / "dist/PageFolio.exe")
                seen_exe.extend(
                    x for x in found if x["pid"] != pid and x not in seen_exe
                )
                current = [support.process_identity(x["pid"]) for x in seen_exe]
                require(
                    all(
                        item is None or item["created"] == original["created"]
                        for original, item in zip(seen_exe, current, strict=True)
                    ),
                    "二次PID再利用",
                )
                if seen_exe and not any(item and item["alive"] for item in current):
                    break
            time.sleep(0.05 if kind == "python" else 0.25)
        machine["peer_identity"] = audit or {
            "observed_processes": seen_exe,
            "status": "external-only",
        }
        verify_route_target(machine["launch_route"])
        if kind == "python":
            require(
                audit is not None and machine["peer_result"].get("constructed") == 0,
                "Python二次が期限内に完了しない",
            )
            require(
                audit.get("verified_owner", {}).get("pid") == pid
                and audit["verified_owner"].get("process_created") == created
                and audit.get("owner_result") == "existing",
                "Python二次owner不一致",
            )
            machine["api_return"] = audit.get("allow_foreground") or {
                "status": "unsupported"
            }
        else:
            require(seen_exe, "EXE二次PIDを外部観測できない")
            require(
                all(
                    not (identity := support.process_identity(item["pid"]))
                    or not identity["alive"]
                    for item in seen_exe
                ),
                "EXE二次が期限内に終了しない。所有外PIDは停止しない",
            )
        machine["events"].append({"step": "peer-observed", "at": now()})
        machine["actual_foreground"] = support.foreground_info()
        machine["owner_after_peer"] = support.process_identity(pid)
        machine["events"].append({"step": "foreground", "at": now()})
        require(
            machine["owner_after_peer"]
            and machine["owner_after_peer"]["alive"]
            and machine["owner_after_peer"]["created"] == created,
            "二次後一次owner同一性不一致",
        )
        require(
            time.monotonic() + INPUT_SECONDS + INSPECT_BUDGET + STOP_BUDGET + MARGIN
            < due,
            "入力観察/回収期限余白不足",
        )
        time.sleep(INPUT_SECONDS)
        machine["input_target_after"] = support.foreground_info()
        machine["events"].append({"step": "input-observed", "at": now()})
        require(
            machine["input_target_after"]["pid"] == pid
            and machine["input_target_after"]["hwnd"]
            == machine["input_target_before"]["hwnd"],
            "実入力先の前景同一性不一致",
        )
        require(
            time.monotonic() + INSPECT_BUDGET + STOP_BUDGET + MARGIN < due,
            "inspect/stop期限余白不足",
        )
        machine["inspection"] = (
            base._command("inspect", run, timeout=INSPECT_BUDGET)
            if kind == "python"
            else support.inspect(run)
        )
        machine["events"].append({"step": "inspect", "at": now()})
    except Exception as error:
        machine["error"] = str(error)
        machine["events"].append({"step": "failed", "at": now()})
        raise
    finally:
        if run is not None:
            try:
                machine["stop"] = (
                    base._command("stop", run, timeout=STOP_BUDGET)
                    if kind == "python"
                    else support.stop(run)
                )
                machine["events"].append({"step": "stop", "at": now()})
            except Exception as error:
                machine["stop_error"] = str(error)
        try:
            verify_provenance(saved)
            if machine.get("launch_route"):
                verify_route_target(machine["launch_route"])
            machine["provenance_after_stop"] = {"matched": True}
        except Exception as error:
            machine["provenance_after_stop"] = {"matched": False, "error": str(error)}
        machine["finished_at"] = now()
        if run is not None and Path(run).is_dir():
            (Path(run) / "w12c-machine.json").write_text(
                json.dumps(machine, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "run": str(run),
                    "row": machine["row"],
                    "error": machine.get("error"),
                    "api_return": machine["api_return"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return machine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--row", required=True, choices=sorted(ROWS))
    parser.add_argument("--final-distribution", required=True)
    args = parser.parse_args()
    collect(args.row, args.final_distribution)


if __name__ == "__main__":
    main()
