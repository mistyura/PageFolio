"""所有run内でのみ生成し、照合後に版付き配布を公開するCLI。"""

from __future__ import annotations

import argparse
import ast
import ctypes
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

SAMPLES = ("ocr_custom_prompt_sample.md", "ocr_summary_prompt_sample.md")


class BuildError(Exception):
    """配布を公開できない安全性または検証の失敗。"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _no_links(path):
    """resolve前に存在する全祖先をlstat。調査不能も拒否する。"""
    for item in reversed((path, *path.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & (
            stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise BuildError(f"リンク/reparse pointは使用できません: {item}")


def _overlap(left, right):
    return left == right or left in right.parents or right in left.parents


def _constants(repo):
    wanted = {
        "APP_VERSION",
        "SETTINGS_FILE",
        "CUSTOM_PROMPT_FILE",
        "SUMMARY_PROMPT_FILE",
    }
    values = {}
    tree = ast.parse((repo / "pagefolio/constants.py").read_text("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    values[target.id] = ast.literal_eval(node.value)
    if values.keys() != wanted or any(not isinstance(v, str) for v in values.values()):
        raise BuildError("版/保護名の文字列リテラルが不足しています")
    if not re.fullmatch(
        r"v[0-9]+(?:\.[0-9]+){2}(?:[-.][A-Za-z0-9]+)*", values["APP_VERSION"]
    ):
        raise BuildError("版番号を安全な配布名にできません")
    protected = [values[k] for k in wanted if k != "APP_VERSION"]
    if any(Path(n).name != n or n in (".", "..") for n in protected):
        raise BuildError("保護名が単一ファイル名ではありません")
    return values["APP_VERSION"], protected


def _git(repo, *args):
    executable = shutil.which("git")
    if executable is None:
        raise BuildError("gitが見つかりません")
    result = subprocess.run(  # noqa: S603
        [executable, "-C", str(repo), *args],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        shell=False,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return result


def _guard(repo, output, operations):
    _no_links(output)
    if output == repo or output == Path(output.anchor):
        raise BuildError("repo root/ドライブルートは出力先にできません")
    protected = [
        repo / n
        for n in (
            "pagefolio",
            "distribution",
            "tools",
            "tests",
            "docs",
            ".git",
            "dist/PageFolio",
        )
    ]
    # 操作先だけで比較するため、既定distと兄弟の旧dist/PageFolioは共存できる。
    tracked = _git(repo, "ls-files", "-z")
    if tracked.returncode == 0:
        protected.extend(
            repo / p for p in tracked.stdout.decode("utf-8").split("\0") if p
        )
    for target in operations:
        _no_links(target)
        resolved = target.resolve()
        if resolved == output or output not in resolved.parents:
            raise BuildError(f"操作先が所有出力領域外です: {target}")
        if any(_overlap(resolved, p.resolve()) for p in protected):
            raise BuildError(f"ソース/旧配布との衝突: {target}")


def _snapshot(path, protected):
    _no_links(path)
    if not path.exists():
        return None
    if not path.is_dir():
        raise BuildError(f"出力先はdirectoryである必要があります: {path}")
    files, directories = {}, []
    names = {name.casefold() for name in protected}

    def visit(directory):
        for item in sorted(directory.iterdir()):
            if item.name.casefold() in names:
                raise BuildError(
                    f"保護対象があります。別の空フォルダーを指定してください: {item}"
                )
            _no_links(item)
            rel = item.relative_to(path).as_posix()
            if item.is_dir():
                directories.append(rel)
                visit(item)
            elif item.is_file():
                files[rel] = _hash(item)
            else:
                raise BuildError(f"調査不能な出力項目: {item}")

    visit(path)
    return {"files": files, "directories": sorted(directories)}


def _read_report(path):
    _no_links(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildError(f"前回のreportを読めません: {path}") from error
    if not isinstance(value, dict):
        raise BuildError(f"前回のreportの形式が不正です: {path}")
    return value


def _managed(final, output, snapshot):
    """空でない既存先は、前回の検証済みmanifestと全名/bytesが一致する場合だけ許可。"""
    files = snapshot["files"]
    embedded_hash = files.get("release-report.json")
    if embedded_hash is None:
        raise BuildError(
            "前回の管理済み配布ではありません。別の空フォルダーを指定してください"
        )
    embedded = _read_report(final / "release-report.json")
    run_id = embedded.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise BuildError("同梱reportのrun_idが不正です")
    external = _read_report(output / ".release-work" / run_id / "report.json")
    manifest = embedded.get("distribution_manifest")
    directories = embedded.get("distribution_directories")
    consistent = (
        isinstance(manifest, dict)
        and isinstance(directories, list)
        and embedded.get("success") is True
        and external.get("success") is True
        and embedded.get("status") == "VERIFIED_BUILD"
        and external.get("status") == "VERIFIED_BUILD"
        and external.get("run_id") == run_id
        and external.get("distribution_manifest") == manifest
        and external.get("distribution_directories") == directories
        and external.get("embedded_report_sha256") == embedded_hash
        and {**manifest, "release-report.json": embedded_hash} == files
        and sorted(directories) == snapshot["directories"]
    )
    if not consistent:
        raise BuildError(
            "既存配布が前回の検証済みmanifestと一致しません。"
            "未知/改変/欠落があるため別の空フォルダーを指定してください"
        )


def _existing(final, output, protected):
    snapshot = _snapshot(final, protected)
    if snapshot and (snapshot["files"] or snapshot["directories"]):
        _managed(final, output, snapshot)
    return snapshot


def _identity():
    """PID再利用と区別できる自身の生成時刻。"""
    if os.name != "nt":
        return {"pid": os.getpid(), "created": time.time_ns()}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    return {"pid": os.getpid(), "created": _creation_time(kernel.GetCurrentProcess())}


def _creation_time(handle):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
    values = [ctypes.c_ulonglong() for _ in range(4)]
    if not kernel.GetProcessTimes(int(handle), *(ctypes.byref(v) for v in values)):
        raise ctypes.WinError(ctypes.get_last_error())
    return values[0].value


def _builder(argv, *, cwd, log, report):
    """固定argv。所有Popenのhandleを保持し、有限時間で回収する。"""
    started = time.monotonic()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log.open("wb") as stream:
        child = subprocess.Popen(  # noqa: S603
            argv,
            cwd=cwd,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        created = _creation_time(child._handle) if os.name == "nt" else time.time_ns()
        report["builder"] = {"pid": child.pid, "created": created, "started_at": _now()}
        try:
            code = child.wait(timeout=1800)
            report["builder"]["exit"] = code
            if code != 0:
                raise BuildError(f"PyInstaller失敗: exit={code}")
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            report["builder"]["interrupted"] = type(error).__name__
            try:
                if child.poll() is None:
                    if os.name == "nt":
                        if _creation_time(child._handle) != created:
                            raise BuildError("子processの生成時刻が一致しません")
                        taskkill = (
                            Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"
                        )
                        cleanup = subprocess.run(  # noqa: S603
                            [str(taskkill), "/PID", str(child.pid), "/T", "/F"],
                            stdin=subprocess.DEVNULL,
                            stdout=stream,
                            stderr=subprocess.STDOUT,
                            shell=False,
                            timeout=30,
                            creationflags=flags,
                        )
                        if cleanup.returncode != 0 and child.poll() is None:
                            raise BuildError("所有process treeを回収できません")
                    else:
                        child.kill()
                    child.wait(timeout=30)
                report["builder"]["reclaimed"] = True
            except Exception as cleanup_error:
                report["builder"]["cleanup_error"] = repr(cleanup_error)
                report["keep_lock"] = True
            raise
        finally:
            report["builder"]["elapsed_seconds"] = time.monotonic() - started


def _inputs(repo):
    paths = [
        repo / "pagefolio.py",
        repo / "pagefolio.ico",
        repo / "requirements.txt",
        repo / "tools/build_release.py",
        repo / "docs/CONFIGURATION.md",
    ]
    paths.extend((repo / "pagefolio").rglob("*.py"))
    paths.extend((repo / "distribution").rglob("*.md"))
    result = {}
    for path in sorted(set(paths)):
        if path.is_file():
            _no_links(path)
            result[path.relative_to(repo).as_posix()] = _hash(path)
    return result


def run_build(output_root, *, repo=None, builder=None):
    """同じ入口を実CLIと隔離実ディスク試験から使う。失敗時も生成物を保持。"""
    repo = Path(repo or Path(__file__).resolve().parents[1]).resolve()
    output = Path(os.path.abspath(output_root))
    run_id = uuid.uuid4().hex
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "success": False,
        "status": "INCOMPLETE",
        "started_at": _now(),
        "stage": "preflight",
        "artifact_role": "technical-tracer",
        "release_allowed": False,
        "manual_uat": "not-run",
        "clean_private_directories": True,
        "pyinstaller_clean_cache": True,
    }
    run = None
    lock = None
    lock_bytes = None
    try:
        version, protected = _constants(repo)
        final = output / f"PageFolio-{version}"
        run_target = output / ".release-work" / run_id
        history = output / ".release-history" / run_id
        lock_target = output / f".PageFolio-{version}.lock"
        operations = (final, run_target, history, lock_target)
        _guard(repo, output, operations)
        for name in (".release-work", ".release-history"):
            owned = output / name
            _no_links(owned)
            if owned.exists() and not owned.is_dir():
                raise BuildError(f"所有領域名が通常directoryではありません: {owned}")
        snapshot = _existing(final, output, protected)
        input_manifest = _inputs(repo)
        sources = {name: repo / "distribution/samples" / name for name in SAMPLES}
        sources["はじめに.md"] = repo / "distribution/はじめに.md"
        sources["docs/CONFIGURATION.md"] = repo / "docs/CONFIGURATION.md"
        for source in sources.values():
            _no_links(source)
            _hash(source)
        output.mkdir(parents=True, exist_ok=True)
        _guard(repo, output, operations)
        lock_bytes = json.dumps(
            {**_identity(), "run_id": run_id}, sort_keys=True
        ).encode()
        try:
            with lock_target.open("xb") as stream:
                lock = lock_target
                stream.write(lock_bytes)
        except FileExistsError as error:
            raise BuildError(
                "同じ最終先のlockが存在します。所有者を確認するまで奪いません: "
                f"{lock_target}"
            ) from error
        run_target.mkdir(parents=True)
        run = run_target
        (run / "INCOMPLETE").write_text("検証未完了", encoding="utf-8")
        (run / "build.log").touch()
        report.update(
            version=version,
            output=str(final),
            run=str(run),
            old_output=str(history) if final.exists() else None,
            input_manifest=input_manifest,
            external_report=str(run / "report.json"),
            source_commit=None,
        )
        git_head = _git(repo, "rev-parse", "HEAD")
        if git_head.returncode == 0:
            report["source_commit"] = git_head.stdout.decode().strip()
            report["dirty_sha256"] = hashlib.sha256(
                _git(repo, "diff", "HEAD", "--binary").stdout
            ).hexdigest()
        report["dependencies"] = {
            name: importlib.metadata.version(name)
            for name in (
                "PyInstaller",
                "pyinstaller-hooks-contrib",
                "PyMuPDF",
                "Pillow",
                "tkinterdnd2",
            )
        }
        report["python"] = sys.version
        report["executable"] = str(Path(sys.executable).resolve())
        argv = [
            str(Path(sys.executable).resolve()),
            "-m",
            "PyInstaller",
            "--clean",
            "--onedir",
            "--noconsole",
            "--name",
            "PageFolio",
            "--icon",
            str(repo / "pagefolio.ico"),
            "--specpath",
            str(run / "spec"),
            "--workpath",
            str(run / "work"),
            "--distpath",
            str(run / "dist"),
            str(repo / "pagefolio.py"),
        ]
        report.update(stage="build", argv=argv)
        _write_json(run / "report.json", report)
        (builder or _builder)(argv, cwd=repo, log=run / "build.log", report=report)
        stage = run / "dist/PageFolio"
        _guard(repo, output, (*operations, stage))
        if not (stage / "PageFolio.exe").is_file():
            raise BuildError("生成EXEがありません")
        report["stage"] = "copy"
        for name, source in sources.items():
            target = stage / name
            _no_links(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if _hash(source) != _hash(target):
                raise BuildError(f"同梱SHA-256不一致: {name}")
        if input_manifest != _inputs(repo):
            raise BuildError("build中に入力が変化しました")
        built = _snapshot(stage, protected)
        report.update(
            stage="verify",
            distribution_manifest=built["files"],
            distribution_directories=built["directories"],
        )
        embedded = dict(
            report,
            success=True,
            status="VERIFIED_BUILD",
            stage="complete",
            finished_at=_now(),
        )
        _write_json(stage / "release-report.json", embedded)
        report["embedded_report_sha256"] = _hash(stage / "release-report.json")
        expected = _snapshot(stage, protected)
        report["stage"] = "publish"
        _guard(repo, output, (*operations, stage))
        if (
            lock.read_bytes() != lock_bytes
            or _existing(final, output, protected) != snapshot
        ):
            raise BuildError("公開前に出力またはlockが変化しました")
        # 初回の空directoryも履歴として残す。二つのrenameは一括atomicではない。
        if final.exists():
            history.parent.mkdir(parents=True, exist_ok=True)
            final.rename(history)
            report["old_output"] = str(history)
        try:
            stage.rename(final)
            report["stage"] = "post-publish-verify"
            if _snapshot(final, protected) != expected:
                raise BuildError("公開後のSHA-256照合に失敗しました")
            done = dict(
                report,
                success=True,
                status="VERIFIED_BUILD",
                stage="complete",
                finished_at=_now(),
            )
            _write_json(run / "report.json", done)
            report.update(done)
        except Exception as publish_error:
            try:
                if final.exists() and not stage.exists():
                    final.rename(stage)
                if history.exists() and not final.exists():
                    history.rename(final)
            except Exception as rollback_error:
                report["rollback_error"] = repr(rollback_error)
            raise publish_error
        (run / "INCOMPLETE").unlink()
    except (Exception, KeyboardInterrupt) as error:
        report.update(
            success=False,
            status="INCOMPLETE",
            failed_stage=report["stage"],
            error=repr(error),
            finished_at=_now(),
        )
        if run is not None:
            try:
                (run / "INCOMPLETE").write_text(str(error), encoding="utf-8")
                _write_json(run / "report.json", report)
            except Exception as report_error:
                report["report_error"] = repr(report_error)
                try:
                    with (run / "build.log").open("a", encoding="utf-8") as stream:
                        stream.write(
                            "\n" + repr(error) + "\nreport: " + repr(report_error)
                        )
                except Exception as log_error:
                    report["log_error"] = repr(log_error)
    finally:
        if lock is not None and not report.get("keep_lock"):
            try:
                _no_links(lock)
                if lock.read_bytes() != lock_bytes:
                    raise BuildError("所有lockが変化したため保持しました")
                lock.unlink()
            except Exception as lock_error:
                report.update(
                    success=False, status="INCOMPLETE", lock_error=repr(lock_error)
                )
    return report


def main(argv=None, *, builder=None, repo=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    result = run_build(args.output_root, repo=repo, builder=builder)
    if result["success"]:
        print(f"ビルド照合成功: {result['output']}")
        print(
            "配布元を直接起動せず完全copy上で実機確認してください。出荷承認・実機合格は未実施です。"
        )
        return 0
    reason = result.get("error", result.get("lock_error"))
    print(f"ビルド失敗 [{result['stage']}]: {reason}", file=sys.stderr)
    if "run" in result:
        print(f"失敗物とログを保持: {result['run']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
