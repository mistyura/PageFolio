# ruff: noqa
"""06-04-01 driver (resume): freeze inputs, run the real CLI exactly twice, assemble BUILD-EVIDENCE.

usage: build_driver2.py freeze | initial <root> | rebuild <root> | assemble <root> [out_json]
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\shdwf\work\project\PageFolio")
sys.path.insert(0, str(REPO))
from tests import release_uat_support as S  # noqa: E402
from tools import build_release as B  # noqa: E402

PY = REPO / ".venv/Scripts/python.exe"


def now():
    return datetime.now(timezone.utc).isoformat()


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, check=True
    ).stdout


def old_dist_tree():
    files, dirs = S.walk_tree(REPO / "dist/PageFolio")
    return {
        "tree_sha256": S.tree_sha(files, dirs),
        "file_count": len(files),
        "exe_sha256": files["PageFolio.exe"],
    }


def freeze():
    root = Path(os.environ["LOCALAPPDATA"]) / "Temp" / f"pf06_final_{uuid.uuid4().hex}"
    root.mkdir()
    out, fz = root / "out", root / "freeze"
    out.mkdir()
    fz.mkdir()
    manifest = B._inputs(REPO)
    snap = fz / "source-snapshot"
    for rel in manifest:
        dst = snap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, dst)
    import importlib.metadata as md

    deps = {
        n: md.version(n)
        for n in (
            "PyInstaller",
            "pyinstaller-hooks-contrib",
            "PyMuPDF",
            "Pillow",
            "tkinterdnd2",
            "pytest",
            "ruff",
        )
    }
    status = git("status", "--short").decode("utf-8", "replace").splitlines()
    dirty_hashes = {}
    for line in status:
        if line.startswith("??"):
            continue
        p = line[3:].strip().strip('"')
        fp = REPO / p
        if fp.is_file():
            dirty_hashes[p] = S.sha_file(fp)
    info = {
        "frozen_at": now(),
        "head": git("rev-parse", "HEAD").decode().strip(),
        "branch": git("branch", "--show-current").decode().strip(),
        "dirty_tracked": dirty_hashes,
        "untracked_count": sum(1 for s in status if s.startswith("??")),
        "dirty_diff_sha256": hashlib.sha256(
            git("diff", "HEAD", "--binary")
        ).hexdigest(),
        "input_manifest": manifest,
        "input_manifest_sha256": S.canonical_sha(manifest),
        "input_file_count": len(manifest),
        "dependencies": deps,
        "python": sys.version,
        "source_snapshot": str(snap),
        "app_version": S.read_constants(REPO)[0],
        "settings_or_secrets_included": False,
        "old_dist_before": old_dist_tree(),
    }
    S.write_json(fz / "freeze.json", info)
    S.write_json(
        root / "state.json",
        {"root": str(root), "out": str(out), "freeze": str(fz), "runs": []},
    )
    print(root)
    print(info["head"], info["input_manifest_sha256"], info["input_file_count"])


def runs_dir(out):
    d = Path(out) / ".release-work"
    return {p.name for p in d.iterdir()} if d.is_dir() else set()


def run_cli(root, order):
    root = Path(root)
    state = S.read_json(root / "state.json")
    out, fz = Path(state["out"]), Path(state["freeze"])
    frozen = S.read_json(fz / "freeze.json")
    if S.canonical_sha(B._inputs(REPO)) != frozen["input_manifest_sha256"]:
        raise SystemExit("STOP: input manifest changed since freeze")
    if any(r["order"] == order for r in state["runs"]):
        raise SystemExit(f"STOP: {order} already executed (CLI is exactly 2 runs)")
    if order == "rebuild" and not any(
        r["order"] == "initial" and r["exit"] == 0 for r in state["runs"]
    ):
        raise SystemExit("STOP: initial not successful")
    before = runs_dir(out)
    argv = [str(PY), str(REPO / "tools/build_release.py"), "--output-root", str(out)]
    t0 = time.monotonic()
    started = now()
    r = subprocess.run(
        argv, cwd=REPO, capture_output=True, stdin=subprocess.DEVNULL, timeout=2400
    )
    elapsed = time.monotonic() - t0
    (fz / f"cli-{order}.stdout.txt").write_bytes(r.stdout)
    (fz / f"cli-{order}.stderr.txt").write_bytes(r.stderr)
    new = sorted(runs_dir(out) - before)
    rec = {
        "order": order,
        "cli_argv": argv,
        "exit": r.returncode,
        "started_at": started,
        "finished_at": now(),
        "elapsed_seconds": elapsed,
        "new_run_ids": new,
    }
    if r.returncode == 0 and len(new) == 1:
        rid = new[0]
        rp = out / ".release-work" / rid / "report.json"
        final = out / f"PageFolio-{frozen['app_version']}"
        files, dirs = S.walk_tree(final)
        rec.update(
            run_id=rid,
            report_path=str(rp),
            report_sha256=S.sha_file(rp),
            final_dir=str(final),
            tree_sha256=S.tree_sha(files, dirs),
            exe_sha256=files["PageFolio.exe"],
            file_count=len(files),
            bundled={
                k: files.get(k)
                for k in (
                    "ocr_custom_prompt_sample.md",
                    "ocr_summary_prompt_sample.md",
                    "はじめに.md",
                    "docs/CONFIGURATION.md",
                    "release-report.json",
                )
            },
        )
    state["runs"].append(rec)
    S.write_json(root / "state.json", state)
    print(
        json.dumps(
            {k: v for k, v in rec.items() if k != "bundled"},
            ensure_ascii=False,
            indent=2,
        )
    )
    return r.returncode


def assemble(root, out_path):
    root = Path(root)
    state = S.read_json(root / "state.json")
    fz = Path(state["freeze"])
    frozen = S.read_json(fz / "freeze.json")
    out = Path(state["out"])
    by = {r["order"]: r for r in state["runs"]}
    assert set(by) == {"initial", "rebuild"} and len(state["runs"]) == 2
    ver = frozen["app_version"]
    final = out / f"PageFolio-{ver}"
    files, dirs = S.walk_tree(final)
    runs = []
    for order in ("initial", "rebuild"):
        rec = by[order]
        rep = S.read_json(rec["report_path"])
        builder = rep.get("builder") or {}
        runs.append(
            {
                "role": "final-release",
                "order": order,
                "run_id": rec["run_id"],
                "cli_argv": rec["cli_argv"],
                "started_at": rec["started_at"],
                "finished_at": rec["finished_at"],
                "elapsed_seconds": rec["elapsed_seconds"],
                "cli_exit": rec["exit"],
                "pyinstaller_exit": builder.get("exit"),
                "pyinstaller_executed": builder.get("exit") is not None,
                "pyinstaller_argv": rep.get("argv"),
                "pyinstaller_version": (rep.get("dependencies") or {}).get(
                    "PyInstaller"
                ),
                "report_path": rec["report_path"],
                "report_sha256": rec["report_sha256"],
                "input_manifest_sha256": S.canonical_sha(rep["input_manifest"]),
                "tree_sha256": rec["tree_sha256"],
                "exe_sha256": rec["exe_sha256"],
                "file_count": rec["file_count"],
                "bundled_sha256": rec["bundled"],
                "source_commit": rep.get("source_commit"),
                "dirty_sha256": rep.get("dirty_sha256"),
                "dependencies": rep.get("dependencies"),
                "stdout_log": str(fz / f"cli-{order}.stdout.txt"),
                "stderr_log": str(fz / f"cli-{order}.stderr.txt"),
                "build_log": str(Path(rec["report_path"]).parent / "build.log"),
            }
        )
    canon = {
        "ocr_custom_prompt_sample.md": REPO
        / "distribution/samples/ocr_custom_prompt_sample.md",
        "ocr_summary_prompt_sample.md": REPO
        / "distribution/samples/ocr_summary_prompt_sample.md",
        "はじめに.md": REPO / "distribution/はじめに.md",
        "docs/CONFIGURATION.md": REPO / "docs/CONFIGURATION.md",
    }
    bundled = {k: files[k] for k in canon}
    match = {k: files[k] == S.sha_file(v) for k, v in canon.items()}
    old_sample = {
        n: S.sha_file(REPO / "dist/PageFolio" / n)
        for n in ("ocr_custom_prompt_sample.md", "ocr_summary_prompt_sample.md")
    }
    old_after = old_dist_tree()
    incomplete = sorted(str(p) for p in (out / ".release-work").glob("*/INCOMPLETE"))
    history = out / ".release-history" / by["rebuild"]["run_id"]
    hf, hd = S.walk_tree(history)
    ev = {
        "version": ver,
        "release_allowed": False,
        "uat_status": "not-run",
        "generated_at": now(),
        "note": "build成功はUAT合格・出荷承認を意味しない。実PyInstaller 2回(初回/再build)の生記録。verifyでは一切buildしない。",
        "freeze": {k: v for k, v in frozen.items() if k != "input_manifest"},
        "final_release": {
            "output_root": str(out),
            "final_dir": str(final),
            "exe_sha256": files["PageFolio.exe"],
            "tree_sha256": S.tree_sha(files, dirs),
            "input_manifest_sha256": frozen["input_manifest_sha256"],
            "bundled_sha256": bundled,
            "bundled_matches_canonical": match,
            "file_count": len(files),
            "runs": runs,
            "history_dir": str(history),
            "history_tree_sha256": S.tree_sha(hf, hd),
            "history_matches_initial_tree": S.tree_sha(hf, hd)
            == by["initial"]["tree_sha256"],
            "incomplete_markers": incomplete,
            "built_exe_auto_launched": False,
            "exe_bit_reproducibility": {
                "initial_exe_sha256": by["initial"]["exe_sha256"],
                "rebuild_exe_sha256": by["rebuild"]["exe_sha256"],
                "equal": by["initial"]["exe_sha256"] == by["rebuild"]["exe_sha256"],
                "required": False,
            },
        },
        "old_dist": {
            "before": frozen["old_dist_before"],
            "after": old_after,
            "unchanged": frozen["old_dist_before"] == old_after,
            "sample_sha256": old_sample,
            "samples_match_new_canonical": {
                n: old_sample[n] == S.sha_file(canon[n]) for n in old_sample
            },
        },
        "tracer_note": "06-01時点のtracer成果物とは別。最終runのbinaryを以後のUAT対象として固定。",
    }
    text = json.dumps(ev, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text[:2500])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "freeze":
        freeze()
    elif cmd in ("initial", "rebuild"):
        sys.exit(run_cli(sys.argv[2], cmd))
    elif cmd == "assemble":
        assemble(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
