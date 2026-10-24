# ruff: noqa
"""06-04-02 自動部分: 保護停止・起動時保持・更新コピー・設定障害の成立を実EXEのcopyで観測する。

製品をimport/patchしない。tests/release_uat_support.py の公開関数だけを使い、
最終buildの配布(06-BUILD-EVIDENCE.json の final_dir)は直接起動せず完全copyだけを起動する。

usage: t2_driver.py <t2_root> protect|launch|update|faults
"""

import ctypes
import hashlib
import json
import shutil
import subprocess
import sys
import time
import uuid
from ctypes import wintypes as wt
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from tests import release_uat_support as S  # noqa: E402

PY = REPO / ".venv/Scripts/python.exe"
BUILD = S.read_json(
    REPO / ".planning/phases/06-release-validation/06-BUILD-EVIDENCE.json"
)
FINAL = Path(BUILD["final_release"]["final_dir"])
OUTROOT = Path(BUILD["final_release"]["output_root"])
REBUILD_ID = [r for r in BUILD["final_release"]["runs"] if r["order"] == "rebuild"][0][
    "run_id"
]
HISTORY = OUTROOT / ".release-history" / REBUILD_ID
VERSION, PROTECTED = S.read_constants(REPO)
T2 = Path(sys.argv[1])
RUNS = T2 / "runs"
RESULT = T2 / "t2-result.json"
TMP = S.SETTINGS_NAME + ".tmp"


def rid():
    return uuid.uuid4().hex


def load():
    return json.loads(RESULT.read_text("utf-8")) if RESULT.exists() else {}


def save(data):
    S.write_json(RESULT, data)


def tree_entries(root):
    root = Path(root)
    out = {}
    if root.exists():
        for p in sorted(root.rglob("*")):
            out[p.relative_to(root).as_posix()] = {
                "kind": "dir" if p.is_dir() else "file",
                "sha256": S.sha_file(p) if p.is_file() else None,
                "size": p.stat().st_size,
            }
    return out


def names_hash(copy):
    """保護名+tmpのhash。外部lockで読めないものは'<locked>'(別途holder経由で読む)。"""
    result = {}
    for n in (*PROTECTED, TMP):
        p = Path(copy) / n
        if not p.is_file():
            result[n] = None
            continue
        try:
            result[n] = S.sha_file(p)
        except PermissionError:
            result[n] = "<locked>"
    return result


def read_via_handle(handle):
    """排他lockの保持者(この観測process)が、自分のhandleから内容を読んでhashする。"""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    h = wt.HANDLE
    k.SetFilePointerEx.argtypes = [h, ctypes.c_longlong, ctypes.c_void_p, wt.DWORD]
    k.SetFilePointerEx.restype = wt.BOOL
    k.ReadFile.argtypes = [
        h,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
        ctypes.c_void_p,
    ]
    k.ReadFile.restype = wt.BOOL
    if not k.SetFilePointerEx(handle, 0, None, 0):
        return None
    buf = ctypes.create_string_buffer(1 << 20)
    got = wt.DWORD(0)
    if not k.ReadFile(handle, buf, len(buf), ctypes.byref(got), None):
        return None
    return hashlib.sha256(buf.raw[: got.value]).hexdigest()


def effective(hashes, holder_hash):
    """'<locked>'をholder経由の実hashへ置換した対照表。"""
    return {
        n: (holder_hash if v == "<locked>" and n == S.SETTINGS_NAME else v)
        for n, v in hashes.items()
    }


def stage_protect():
    data = load()
    items = []
    for name in PROTECTED:
        run_id = rid()
        root = T2 / "protect" / run_id
        out = root / "out"
        target = out / f"PageFolio-{VERSION}"
        target.mkdir(parents=True)
        (target / name).write_bytes(f"UAT synthetic protected file: {name}\n".encode())
        before = tree_entries(out)
        argv = [
            str(PY),
            str(REPO / "tools/build_release.py"),
            "--output-root",
            str(out),
        ]
        t0 = time.monotonic()
        r = subprocess.run(
            argv, cwd=REPO, capture_output=True, stdin=subprocess.DEVNULL, timeout=300
        )
        after = tree_entries(out)
        started = (out / ".release-work").exists() or any(
            p.name.startswith(".PageFolio-") for p in out.iterdir()
        )
        items.append(
            {
                "name": name,
                "run_id": run_id,
                "cli_argv": argv,
                "exit_code": r.returncode,
                "builder_started": bool(started),
                "stderr": r.stderr.decode("utf-8", "replace").strip(),
                "stdout": r.stdout.decode("utf-8", "replace").strip(),
                "before": before,
                "after": after,
                "elapsed_seconds": time.monotonic() - t0,
                "output_root": str(out),
                "placed": f"PageFolio-{VERSION}/{name}",
            }
        )
        print(
            name,
            r.returncode,
            started,
            r.stderr.decode("utf-8", "replace").strip()[:120],
        )
    data["protection_stop"] = items
    save(data)


def hold_session(case, *, overlays=None, faults=(), settle=8.0, stop_timeout=12.0):
    """隔離copyを作り、(任意の障害を保持して)未改変EXEを起動して観測し回収する。"""
    m = S.prepare(FINAL, case, base=RUNS, overlays=overlays)
    run, copy = Path(m["run"]), Path(m["copy"])
    rec = {
        "run_id": m["run_id"],
        "run": str(run),
        "case": case,
        "faults": list(faults),
        "binary_sha256": m["source"]["exe_sha256"],
        "tree_sha256": m["source"]["tree_sha256"],
        "fault_records": {},
    }
    held = []
    settings = copy / S.SETTINGS_NAME
    try:
        rec["hash_pre_fault"] = names_hash(copy)
        for kind in faults:
            f = S.prepare_settings_fault(copy, kind)
            held.append(f)
            rec["fault_records"][kind] = f.record
            if kind == "corrupt":
                S.declare_overlay(
                    run, {S.SETTINGS_NAME: settings.read_bytes()}, "破損JSON"
                )
            elif kind == "save-write":
                S.declare_overlay(run, {TMP: (copy / TMP).read_bytes()}, "tmp衝突")
        holder = next((f for f in held if f.handle is not None), None)
        rec["hash_before"] = names_hash(copy)
        rec["hash_before_effective"] = effective(
            rec["hash_before"], read_via_handle(holder.handle) if holder else None
        )
        rec["probe_owner_before"] = S.probe_owner()
        S.start(run, settle=settle)
        rec["hash_stable"] = names_hash(copy)
        rec["hash_stable_effective"] = effective(
            rec["hash_stable"], read_via_handle(holder.handle) if holder else None
        )
        if "unreadable" in faults:
            rec["probe_during_run"] = S.probe_open(
                settings, S.GENERIC_READ, S.FILE_SHARE_READ | S.FILE_SHARE_WRITE
            )
        if "save-replace" in faults:
            rec["probe_delete_during_run"] = S.probe_open(settings, S.DELETE)
            rec["probe_read_during_run"] = S.probe_open(settings, S.GENERIC_READ)
        if "save-write" in faults:
            tmp = copy / TMP
            rec["tmp_during_run"] = {
                "exists": tmp.exists(),
                "sha256": S.sha_file(tmp) if tmp.is_file() else None,
            }
        obs = S.inspect(run, "stable")
        rec["inspect_stable"] = {
            "processes": obs["processes"],
            "foreground": obs["foreground"],
            "copy_ok": obs["copy"]["ok"],
            "locked_unverified": obs["copy"].get("locked_unverified"),
            "owner_probe": obs["owner_probe"],
        }
        rec["observed_at"] = obs["at"]
        rec["stop"] = S.stop(run, timeout=stop_timeout)
        rec["stop_diagnostics"] = sorted(
            p.name for p in (run / "evidence").glob("stop-diagnostics-*.json")
        )
        rec["hash_after_exit_with_hold"] = names_hash(copy)
        rec["holder_hash_after_exit"] = (
            read_via_handle(holder.handle) if holder else None
        )
    finally:
        for f in held:
            f.close()
    rec["hash_after_exit"] = names_hash(copy)
    after = S.verify_copy(S.load_run(run))
    rec["verify_after"] = {
        k: after[k]
        for k in ("ok", "overlay_changed", "distribution_changed", "locked_unverified")
    }
    rec["source_unchanged"] = S._source_unchanged(S.load_run(run))
    rec["owner_after"] = S.probe_owner()
    return rec


def stage_launch():
    data = load()
    valid = json.dumps({"lang": "ja", "theme": "dark"}).encode("utf-8")
    prompts = {
        "ocr_custom_prompt.md": (FINAL / "ocr_custom_prompt_sample.md").read_bytes(),
        "ocr_summary_prompt.md": (FINAL / "ocr_summary_prompt_sample.md").read_bytes(),
    }
    cases = [
        {
            **hold_session(
                "launch-normal", overlays={S.SETTINGS_NAME: valid, **prompts}
            ),
            "name": "normal",
        },
        {
            **hold_session(
                "launch-corrupt", overlays=dict(prompts), faults=("corrupt",)
            ),
            "name": "corrupt",
        },
        {
            **hold_session(
                "launch-unreadable",
                overlays={S.SETTINGS_NAME: valid, **prompts},
                faults=("unreadable",),
            ),
            "name": "unreadable",
        },
    ]
    data["launch"] = {"cases": cases}
    save(data)
    for c in cases:
        print(
            c["name"],
            c["hash_before_effective"] == c["hash_stable_effective"],
            c["stop"],
        )


def guide_update_copy(old, new):
    """はじめに.md 手順2-3: 旧から3名だけを新へコピー。同名があれば何もコピーせず停止する。"""
    old, new = Path(old), Path(new)
    wanted = [n for n in PROTECTED if (old / n).is_file()]
    collisions = [n for n in wanted if (new / n).exists()]
    if collisions:
        return {"stopped_before_choice": True, "collisions": collisions, "copied": []}
    for n in wanted:
        shutil.copyfile(old / n, new / n)
    return {"stopped_before_choice": False, "collisions": [], "copied": wanted}


def stage_update():
    data = load()
    results = {}
    user_files = {
        S.SETTINGS_NAME: json.dumps(
            {"lang": "ja", "theme": "dark", "marker": "old-user"}
        ).encode(),
        "ocr_custom_prompt.md": b"# old user custom prompt (synthetic)\n",
        "ocr_summary_prompt.md": b"# old user summary prompt (synthetic)\n",
    }
    for scenario in ("collision", "no_collision"):
        run_id = rid()
        old_m = S.prepare(
            HISTORY, f"update-old-{scenario}", base=RUNS, overlays=dict(user_files)
        )
        new_m = S.prepare(FINAL, f"update-new-{scenario}", base=RUNS)
        old, new = Path(old_m["copy"]), Path(new_m["copy"])
        if scenario == "collision":
            S.declare_overlay(
                new_m["run"],
                {
                    S.SETTINGS_NAME: json.dumps(
                        {"lang": "ja", "marker": "new-existing"}
                    ).encode()
                },
                "新側に既存の同名",
            )
        old_before, new_before = names_hash(old), names_hash(new)
        proc = guide_update_copy(old, new)
        old_after, new_after = names_hash(old), names_hash(new)
        entry = {
            "run_id": run_id,
            "old_copy_run": old_m["run_id"],
            "new_copy_run": new_m["run_id"],
            "procedure": "はじめに.md 手順2-3の非上書きコピーを検証担当が手で行う操作として模擬(製品機能ではない)",
            "old_source": "initial runのtree(.release-history)",
            "result": proc,
            "old_before": old_before,
            "old_after": old_after,
            "new_before": new_before,
            "new_after": new_after,
            "old_tree_sha256_source": old_m["source"]["tree_sha256"],
            "new_tree_sha256_source": new_m["source"]["tree_sha256"],
        }
        if scenario == "no_collision":
            entry["copied_hash_match"] = bool(proc["copied"]) and all(
                new_after[n] == old_before[n] for n in proc["copied"]
            )
            entry["old_preserved"] = old_before == old_after
        else:
            entry["stopped_before_choice"] = proc["stopped_before_choice"]
        results[scenario] = entry
        print(scenario, proc)
    data["update"] = results
    save(data)


def stage_faults():
    data = load()
    valid = json.dumps({"lang": "ja", "theme": "dark"}).encode("utf-8")
    sessions = {
        "X01": hold_session(
            "fault-x01-missing", overlays={S.SETTINGS_NAME: None}, faults=("missing",)
        ),
        "X02": hold_session("fault-x02-corrupt", faults=("corrupt",)),
        "X03": hold_session(
            "fault-x03-unreadable",
            overlays={S.SETTINGS_NAME: valid},
            faults=("unreadable",),
        ),
        "X04-write": hold_session(
            "fault-x04-save-write",
            overlays={S.SETTINGS_NAME: valid},
            faults=("save-write",),
        ),
        "X04-replace": hold_session(
            "fault-x04-save-replace",
            overlays={S.SETTINGS_NAME: valid},
            faults=("save-replace",),
        ),
        "X05": hold_session(
            "fault-x05-combined",
            overlays={S.SETTINGS_NAME: valid},
            faults=("save-write", "unreadable"),
        ),
    }
    data["fault_sessions"] = sessions
    save(data)
    for k, v in sessions.items():
        print(
            k,
            [r.get("established") for r in v["fault_records"].values()],
            v["stop"],
            v["stop_diagnostics"],
        )


if __name__ == "__main__":
    {
        "protect": stage_protect,
        "launch": stage_launch,
        "update": stage_update,
        "faults": stage_faults,
    }[sys.argv[2]]()
