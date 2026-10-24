"""未改変の配布EXEを外側から準備・観測・回収し、受入証拠を監査する検証CLI。

製品コードをimport/patchしない。EXEへnonceや試験引数を渡さず、完全copyした配布tree
（配布元は起動しない）をそのまま起動する。単体試験・fixture・故障注入の成功は、実配布EXEの
人手passの代わりにならない。未実施(not-run)をpassへ補完することも一切しない。

サブコマンド::

    prepare  --distribution <dir> --case <ID>   完全copy・hash固定・合成設定/PDFの準備
    start    --run <dir>                        所有プロセスとして起動し外部観測を保存
    peer     --run <dir> [--with-run <dir>]     同じownerへ2つ目を起動(混在確認)
    inspect  --run <dir>                        PID/foreground/window/tree/原本の観測
    stop     --run <dir>                        PID+生成時刻を再照合して回収
    audit    --phase-dir <dir> <mode>           証拠の読取専用監査
    fault    --run <dir> --kind <種別>          設定障害(外部lock/tmp衝突)の保持
    serve-ocr --run <dir>                       loopbackの合成OCRを待機させる
    resume-save / resume-check                  中断・再開の台帳

audit のモード(相互排他。すべて証拠を読むだけで台帳を書き換えない)::

    --allow-pending            途中記録用の構造監査(未実施を許容するがdoneは満たさない)
    --require-pass ID,ID,...   担当IDを全subrowへ展開し、実測根拠付きpassを全件要求
    --build-only               06-BUILD-EVIDENCE.jsonの2run/配布tree/hashを読取照合
    --preparation-only         06-PROTECTION-EVIDENCE.jsonと準備記録を照合
    --for-handoff              引渡し準備監査(親の4ゲートだけpendingを許容)
    (指定なし)                  親ゲート実走後の最終監査

どのモードの成功出力もphase_complete=false / release_allowed=falseで、完了・出荷の判断は
親が行う。証拠の入力schemaは06-UAT-PREPARATION.mdの「証拠schema」を正本とする。
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from ctypes import wintypes as wt
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:  # pytest(tests パッケージ)と script 直接実行の双方を受ける
    from tests import release_fake_ocr
except ImportError:  # pragma: no cover - script 実行時
    import release_fake_ocr

REPO = Path(__file__).resolve().parents[1]

EVIDENCE_KINDS = ("production-exe", "python-real", "fault-injection", "unit", "manual")
ROLES = ("final-release-candidate", "technical-tracer-real-exe", "same-version-copy")
STATUSES = ("not-run", "pass", "fail", "blocked")
PRODUCTION_PREFIX = "PageFolio.Startup"  # 実製品の固定namespace(startup_win32.py)
PROTECTED_FALLBACK = (
    "pagefolio_settings.json",
    "ocr_custom_prompt.md",
    "ocr_summary_prompt.md",
)
SETTINGS_NAME = "pagefolio_settings.json"
# 明示fixture overlayとして配布copyへ書いてよい名前(合成設定・2prompt・tmp衝突用)
OVERLAY_ALLOWED = frozenset((*PROTECTED_FALLBACK, SETTINGS_NAME + ".tmp"))

MANUAL = "06-MANUAL-EVIDENCE.json"
BUILD = "06-BUILD-EVIDENCE.json"
PROTECTION = "06-PROTECTION-EVIDENCE.json"
PREPARATION = "06-UAT-PREPARATION.md"
QUALITY = "06-EVIDENCE.json"
GATE = "06-RELEASE-GATE.md"
RESUME = "06-RESUME-STATE.json"

TASK_IDS = {
    "06-05-02": (
        "W01,W02,W03,W04,W05a,W05b,W05c,W12a,W12b,W12c,X01,X02,X03,X04,X05,X06"
    ).split(","),
    "06-06-01": (
        "W06,W07a,W07b,W08a,W08b,W08c,W08d,W09a,W09b,W09c,W09d,W10a,W10b,W11,WR-01"
    ).split(","),
}
ALL_IDS = tuple(sum(TASK_IDS.values(), []))
# audit側の宣言下限。カードの全展開は06-05-01のTestCaseCoverageが担う。
CASE_MINIMUM = {
    "W01": {"conditions": {"normal", "zoomed"}},
    "W02": {"conditions": {"settings", "thumb", "preview"}},
    "W12a": {"min_rows": 9, "exe": False},
    "W12b": {"subject": True},
}
PARENT_GATES = ("code-review", "secure-phase", "validate-phase", "verification")
REQUIRED_UNRESOLVED = (
    "DEP-05-REGRESSION",
    "owner_missing",
    "notice-foreground-mismatch",
    "tcl-warning",
    "edge-unclassified",
)
REQUIRED_THREATS = tuple(f"T-06-{n:02d}" for n in range(1, 15))
FAULT_IDS = ("X01", "X02", "X03", "X04", "X05")


class SupportError(Exception):
    """検証支援の安全性または前提の失敗。"""


class IsolationError(SupportError):
    """隔離copy・配布manifestの不一致。"""


class OwnershipError(SupportError):
    """所有プロセス・既存ownerの不一致。"""


class NotEstablished(SupportError):
    """障害や接続が成立せず、準備未完了(not-run)として停止すべき状態。"""

    def __init__(self, message, record=None):
        super().__init__(message)
        self.record = record or {}


# ---------------------------------------------------------------------------
# 基本ヘルパー
# ---------------------------------------------------------------------------
def _now():
    return datetime.now(timezone.utc).isoformat()


def sha_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_sha(value):
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SupportError(
            f"JSONを読めません: {path}: {type(error).__name__}"
        ) from error
    if not isinstance(value, dict):
        raise SupportError(f"JSONのtopがobjectではありません: {path}")
    return value


def _is_reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _no_links(path):
    for item in reversed((Path(path), *Path(path).parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if _is_reparse(info):
            raise IsolationError(f"リンク/reparse pointは使用できません: {item}")


def _overlap(left, right):
    left, right = Path(left).resolve(), Path(right).resolve()
    return left == right or left in right.parents or right in left.parents


def walk_tree(root, *, locked_ok=frozenset(), locked=None):
    """(files{相対名: sha256}, dirs[相対名])。リンク/reparse/特殊ファイルは拒否。

    locked_okに挙げた相対名だけは、外部handle(設定障害X03の排他lock)でhashを読めなくても
    例外にせず、lockedへ記録してfilesから除く。それ以外の読取失敗は従来どおり例外にする。
    """
    root = Path(root)
    files, dirs = {}, []

    def visit(directory):
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda e: e.name)
        for entry in entries:
            info = entry.stat(follow_symlinks=False)
            if _is_reparse(info):
                raise IsolationError(f"リンク/reparse pointがあります: {entry.path}")
            rel = Path(entry.path).relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                dirs.append(rel)
                visit(entry.path)
            elif stat.S_ISREG(info.st_mode):
                try:
                    files[rel] = sha_file(entry.path)
                except PermissionError:
                    if rel not in locked_ok or locked is None:
                        raise
                    locked.append(rel)
            else:
                raise IsolationError(f"通常ファイルでない項目があります: {entry.path}")

    visit(root)
    return files, sorted(dirs)


def stat_tree(root):
    """相対名 -> (size, mtime_ns)。読取専用監査が何も変えないことの確認用。"""
    root = Path(root)
    result = {}
    if not root.exists():
        return result
    for current, names, files in os.walk(root):
        for name in (*names, *files):
            path = Path(current) / name
            info = path.lstat()
            result[path.relative_to(root).as_posix()] = (info.st_size, info.st_mtime_ns)
    return result


def tree_sha(files, dirs):
    return canonical_sha({"files": files, "dirs": sorted(dirs)})


def read_constants(repo):
    """製品をimportせず、ASTから版と保護名だけを読む。"""
    wanted = {
        "APP_VERSION",
        "SETTINGS_FILE",
        "CUSTOM_PROMPT_FILE",
        "SUMMARY_PROMPT_FILE",
    }
    values = {}
    tree = ast.parse((Path(repo) / "pagefolio/constants.py").read_text("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    values[target.id] = ast.literal_eval(node.value)
    if values.keys() != wanted:
        raise SupportError("版/保護名のリテラルが不足しています")
    protected = tuple(values[k] for k in sorted(wanted - {"APP_VERSION"}))
    return values["APP_VERSION"], protected


def collect_environment():
    """観測者(このPython/Tk)の環境。EXE内蔵の版とは別欄にする。"""
    env = {
        "os": platform.platform(),
        "observer_python": sys.version,
        "observer_tk": None,
        "elevated": None,
        "session_id": None,
    }
    try:
        import tkinter

        env["observer_tk"] = str(tkinter.TkVersion)
    except Exception as error:  # noqa: BLE001 - 観測不能を記録して続行
        env["observer_tk"] = f"unavailable:{type(error).__name__}"
    if os.name == "nt":
        env["elevated"] = bool(ctypes.windll.shell32.IsUserAnAdmin())
        session = wt.DWORD()
        api = _api()
        api.k.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
        env["session_id"] = session.value
    return env


# ---------------------------------------------------------------------------
# Win32
# ---------------------------------------------------------------------------
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
FILE_MAP_READ = 0x0004
STILL_ACTIVE = 259
WM_CLOSE = 0x0010
ERROR_FILE_NOT_FOUND = 2
ERROR_ACCESS_DENIED = 5
ERROR_SHARING_VIOLATION = 32
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
DELETE = 0x00010000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
OPEN_EXISTING = 3
_INVALID = ctypes.c_void_p(-1).value
_API = None


class _Api:
    pass


def _api():
    global _API
    if _API is not None:
        return _API
    api = _Api()
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    u = ctypes.WinDLL("user32", use_last_error=True)
    a = ctypes.WinDLL("advapi32", use_last_error=True)
    h = wt.HANDLE
    ft = ctypes.POINTER(wt.FILETIME)
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.OpenProcess.restype = h
    k.CloseHandle.argtypes = [h]
    k.CloseHandle.restype = wt.BOOL
    k.GetProcessTimes.argtypes = [h, ft, ft, ft, ft]
    k.GetProcessTimes.restype = wt.BOOL
    k.GetExitCodeProcess.argtypes = [h, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.QueryFullProcessImageNameW.argtypes = [
        h,
        wt.DWORD,
        wt.LPWSTR,
        ctypes.POINTER(wt.DWORD),
    ]
    k.QueryFullProcessImageNameW.restype = wt.BOOL
    k.ProcessIdToSessionId.argtypes = [wt.DWORD, ctypes.POINTER(wt.DWORD)]
    k.ProcessIdToSessionId.restype = wt.BOOL
    k.TerminateProcess.argtypes = [h, wt.UINT]
    k.TerminateProcess.restype = wt.BOOL
    k.WaitForSingleObject.argtypes = [h, wt.DWORD]
    k.WaitForSingleObject.restype = wt.DWORD
    k.OpenMutexW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
    k.OpenMutexW.restype = h
    k.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
    k.OpenFileMappingW.restype = h
    k.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
    k.CreateMutexW.restype = h
    k.CreateFileW.argtypes = [
        wt.LPCWSTR,
        wt.DWORD,
        wt.DWORD,
        ctypes.c_void_p,
        wt.DWORD,
        wt.DWORD,
        h,
    ]
    k.CreateFileW.restype = h
    a.OpenProcessToken.argtypes = [h, wt.DWORD, ctypes.POINTER(h)]
    a.OpenProcessToken.restype = wt.BOOL
    a.GetTokenInformation.argtypes = [
        h,
        ctypes.c_int,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
    ]
    a.GetTokenInformation.restype = wt.BOOL
    u.GetForegroundWindow.restype = wt.HWND
    u.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    u.GetWindowThreadProcessId.restype = wt.DWORD
    api.enum_proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    u.EnumWindows.argtypes = [api.enum_proc, wt.LPARAM]
    u.EnumWindows.restype = wt.BOOL
    u.IsWindowVisible.argtypes = [wt.HWND]
    u.IsWindowVisible.restype = wt.BOOL
    u.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    u.GetWindowTextW.restype = ctypes.c_int
    u.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    u.GetClassNameW.restype = ctypes.c_int
    u.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    u.GetWindowRect.restype = wt.BOOL
    u.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    u.PostMessageW.restype = wt.BOOL
    api.k, api.u, api.a = k, u, a
    _API = api
    return api


def _filetime(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def _filetime_iso(value):
    moment = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=value // 10
    )
    return moment.isoformat()


def _creation(handle):
    api = _api()
    stamps = [wt.FILETIME() for _ in range(4)]
    if not api.k.GetProcessTimes(handle, *(ctypes.byref(s) for s in stamps)):
        raise ctypes.WinError(ctypes.get_last_error())
    return _filetime(stamps[0])


def _image(handle):
    api = _api()
    size = wt.DWORD(32768)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not api.k.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
        return None
    return buffer.value


def _norm_path(value):
    return os.path.normcase(os.path.abspath(value)) if value else None


def _elevated(handle):
    api = _api()
    token = wt.HANDLE()
    if not api.a.OpenProcessToken(handle, 0x0008, ctypes.byref(token)):
        return None
    try:
        value = wt.DWORD()
        size = wt.DWORD()
        if not api.a.GetTokenInformation(
            token, 20, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(size)
        ):
            return None
        return bool(value.value)
    finally:
        api.k.CloseHandle(token)


def process_identity(pid):
    """PID+生成時刻+image+session。開けない(消滅/権限)ならNone。"""
    api = _api()
    handle = api.k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        code = wt.DWORD()
        api.k.GetExitCodeProcess(handle, ctypes.byref(code))
        session = wt.DWORD()
        api.k.ProcessIdToSessionId(pid, ctypes.byref(session))
        created = _creation(handle)
        return {
            "pid": pid,
            "created": created,
            "created_iso": _filetime_iso(created),
            "image": _image(handle),
            "session_id": session.value,
            "elevated": _elevated(handle),
            "alive": code.value == STILL_ACTIVE,
        }
    finally:
        api.k.CloseHandle(handle)


def same_process(record, identity):
    return bool(
        identity
        and record["created"] == identity["created"]
        and _norm_path(record["image"]) == _norm_path(identity["image"])
    )


def windows_of(pid):
    api = _api()
    found = []

    def callback(hwnd, _):
        owner = wt.DWORD()
        api.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title = ctypes.create_unicode_buffer(256)
            cls = ctypes.create_unicode_buffer(128)
            api.u.GetWindowTextW(hwnd, title, 256)
            api.u.GetClassNameW(hwnd, cls, 128)
            rect = wt.RECT()
            api.u.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append(
                {
                    "hwnd": int(hwnd or 0),
                    "visible": bool(api.u.IsWindowVisible(hwnd)),
                    "title": title.value,
                    "class": cls.value,
                    "rect": [rect.left, rect.top, rect.right, rect.bottom],
                }
            )
        return True

    api.u.EnumWindows(api.enum_proc(callback), 0)
    return found


def foreground_info():
    api = _api()
    hwnd = api.u.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "pid": None, "title": ""}
    owner = wt.DWORD()
    api.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    title = ctypes.create_unicode_buffer(256)
    api.u.GetWindowTextW(hwnd, title, 256)
    return {"hwnd": int(hwnd), "pid": owner.value, "title": title.value}


def probe_owner(prefix=PRODUCTION_PREFIX):
    """固定namespaceのowner mutex/state mappingを読取だけで確認する。

    生成も取得もしない。開けた/アクセス拒否/調査不能はすべて「ownerあり」として扱う。
    """
    api = _api()
    found = []
    for kind, name, opener, access in (
        ("mutex", f"Local\\{prefix}.Owner", api.k.OpenMutexW, SYNCHRONIZE),
        ("mapping", f"Local\\{prefix}.State", api.k.OpenFileMappingW, FILE_MAP_READ),
    ):
        ctypes.set_last_error(0)
        handle = opener(access, False, name)
        if handle:
            api.k.CloseHandle(handle)
            found.append({"kind": kind, "name": name, "state": "open"})
            continue
        error = ctypes.get_last_error()
        if error == ERROR_ACCESS_DENIED:
            found.append({"kind": kind, "name": name, "state": "access-denied"})
        elif error != ERROR_FILE_NOT_FOUND:
            found.append({"kind": kind, "name": name, "state": f"error-{error}"})
    return found


# ---------------------------------------------------------------------------
# 隔離copy
# ---------------------------------------------------------------------------
def read_distribution(dist):
    """配布treeを同梱release-reportのmanifestと全名/全hashで照合して返す。"""
    dist = Path(dist)
    _no_links(dist)
    report = read_json(dist / "release-report.json")
    files, dirs = walk_tree(dist)
    manifest = report.get("distribution_manifest")
    directories = report.get("distribution_directories")
    if (
        report.get("success") is not True
        or report.get("status") != "VERIFIED_BUILD"
        or not isinstance(manifest, dict)
        or not isinstance(directories, list)
    ):
        raise IsolationError("検証済みbuildのreportではありません")
    expected = {**manifest, "release-report.json": files.get("release-report.json")}
    if expected != files or sorted(directories) != dirs:
        raise IsolationError("配布treeが同梱reportのmanifestと一致しません")
    if "PageFolio.exe" not in files:
        raise IsolationError("PageFolio.exeがありません")
    return {
        "report": report,
        "files": files,
        "dirs": dirs,
        "exe_sha256": files["PageFolio.exe"],
        "tree_sha256": tree_sha(files, dirs),
        "version": report.get("version"),
        "run_id": report.get("run_id"),
    }


def _manifest_path(run):
    return Path(run) / "manifest.json"


def load_run(run):
    run = Path(run)
    path = _manifest_path(run)
    if not path.is_file():
        raise SupportError(f"run manifestがありません: {run}")
    return read_json(path)


def save_run(manifest):
    write_json(_manifest_path(manifest["run"]), manifest)


def _check_case(case):
    if not isinstance(case, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", case):
        raise SupportError(f"ケースIDが不正です: {case!r}")


def snapshot_originals(repo):
    """元repoの設定/2prompt/pluginsを内容を出さずexists+hashで記録する。"""
    repo = Path(repo)
    _, protected = read_constants(repo)
    result = {}
    for name in protected:
        path = repo / name
        result[name] = {
            "exists": path.exists(),
            "sha256": sha_file(path) if path.is_file() else None,
        }
    plugins = repo / "plugins"
    result["plugins"] = (
        {
            p.relative_to(plugins).as_posix(): sha_file(p)
            for p in sorted(plugins.rglob("*"))
            if p.is_file()
        }
        if plugins.is_dir()
        else None
    )
    return result


def verify_copy(manifest):
    """配布manifest(不変)とfixture overlay(可変)を別々に照合する。"""
    copy = Path(manifest["copy"])
    distribution = manifest["distribution_manifest"]
    overlay = manifest["overlay"]
    locked = []
    files, dirs = walk_tree(copy, locked_ok=frozenset(overlay), locked=locked)
    # 外部lock中は内容を確認できない。宣言済みoverlayの期待値とみなし、別欄に残す。
    for name in locked:
        expected = overlay[name]
        files[name] = expected if expected is not None else "<locked-absent-declared>"
    changed = sorted(r for r, h in distribution.items() if files.get(r) != h)
    missing_dirs = sorted(set(manifest["distribution_dirs"]) - set(dirs))
    extra_dirs = sorted(set(dirs) - set(manifest["distribution_dirs"]))
    undeclared = sorted(r for r in files if r not in distribution and r not in overlay)
    overlay_changed = sorted(
        name for name, expected in overlay.items() if files.get(name) != expected
    )
    return {
        "ok": not (changed or missing_dirs or extra_dirs or undeclared),
        "distribution_changed": changed,
        "missing_dirs": missing_dirs,
        "extra_dirs": extra_dirs,
        "undeclared": undeclared,
        "overlay_changed": overlay_changed,
        "locked_unverified": sorted(locked),
        "tree_sha256": tree_sha(files, dirs),
        "exe_sha256": files.get("PageFolio.exe"),
    }


def _source_unchanged(manifest):
    files, dirs = walk_tree(manifest["source"]["distribution"])
    return (
        tree_sha(files, dirs) == manifest["source"]["tree_sha256"]
        and files.get("PageFolio.exe") == manifest["source"]["exe_sha256"]
    )


def declare_overlay(run, changes, reason):
    """明示fixture overlayを書き込む。値None=不存在。配布manifestとは別に管理する。"""
    manifest = load_run(run)
    run = Path(run)
    copy = Path(manifest["copy"])
    for name in changes:
        if name not in OVERLAY_ALLOWED:
            raise IsolationError(f"overlayに許可されない名前です: {name}")
        if name in manifest["distribution_manifest"]:
            raise IsolationError(f"配布manifestの項目はoverlayにできません: {name}")
    for name, data in changes.items():
        target = copy / name
        source = run / "overlay-source" / name
        _no_links(target)
        if data is None:
            if target.exists():
                target.unlink()
            if source.exists():
                source.unlink()
            manifest["overlay"][name] = None
        else:
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(data)
            target.write_bytes(data)
            manifest["overlay"][name] = hashlib.sha256(data).hexdigest()
        manifest["overlay_log"].append(
            {
                "at": _now(),
                "name": name,
                "sha256": manifest["overlay"][name],
                "reason": reason,
            }
        )
    save_run(manifest)
    return manifest


def prepare(
    distribution,
    case,
    *,
    entry="production-exe",
    evidence_kind="production-exe",
    role="final-release-candidate",
    base=None,
    run_id=None,
    repo=None,
    overlays=None,
):
    """配布treeを検証して完全copyし、run manifestを作る。配布元は起動しない。"""
    repo = Path(repo or REPO)
    _check_case(case)
    if evidence_kind not in EVIDENCE_KINDS:
        raise SupportError(f"証拠種別が不正です: {evidence_kind}")
    if role not in ROLES:
        raise SupportError(f"roleが不正です: {role}")
    dist = Path(distribution).resolve()
    info = read_distribution(dist)
    base = Path(base) if base else repo / ".planning" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    _no_links(base)
    run_id = run_id or uuid.uuid4().hex
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise SupportError("run IDは32桁hexである必要があります")
    run = (base / f"release-uat-{run_id}").resolve()
    if _overlap(run, dist):
        raise IsolationError("run領域と配布元が重なっています")
    if run.exists():
        raise IsolationError(f"runが既に存在します: {run}")
    run.mkdir()
    (run / "evidence").mkdir()
    (run / "fixtures").mkdir()
    version, protected = read_constants(repo)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "run": str(run),
        "case": case,
        "entry": entry,
        "evidence_kind": evidence_kind,
        "role": role,
        "status": "preparing",
        "created_at": _now(),
        "environment": collect_environment(),
        "source": {
            "distribution": str(dist),
            "version": info["version"],
            "exe_sha256": info["exe_sha256"],
            "tree_sha256": info["tree_sha256"],
            "report_run_id": info["run_id"],
            "app_version_in_repo": version,
            "embedded": {
                "python": info["report"].get("python"),
                "dependencies": info["report"].get("dependencies"),
            },
        },
        "copy": str(run / "dist"),
        "distribution_manifest": info["files"],
        "distribution_dirs": info["dirs"],
        "overlay": {},
        "overlay_log": [],
        "fixtures": {},
        "processes": [],
        "observations": [],
        "snapshots": [],
        "case_history": [],
        "generation": 1,
        "protected_names": list(protected),
        "repo": str(repo),
    }
    save_run(manifest)
    try:
        shutil.copytree(dist, run / "dist", symlinks=False)
        copied, copied_dirs = walk_tree(run / "dist")
        if copied != info["files"] or copied_dirs != info["dirs"]:
            raise IsolationError("copy後のtreeが配布manifestと一致しません")
        if not _source_unchanged(manifest):
            raise IsolationError("copy中に配布元が変化しました")
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = repr(error)
        save_run(manifest)
        raise
    manifest["status"] = "prepared"
    save_run(manifest)
    if overlays:
        manifest = declare_overlay(run, overlays, "prepare時の明示fixture")
    return manifest


def add_fixture_pdf(run, kind):
    """合成PDFをrun/fixturesへ作る。OCR用1page画像とW03用3page編集用は別物。"""
    manifest = load_run(run)
    run = Path(run)
    if kind == "ocr-one-page":
        path = run / "fixtures" / "ocr-one-page.pdf"
        facts = release_fake_ocr.make_one_page_image_pdf(path)
        if facts["pages"] != 1 or facts["has_embedded_text"]:
            raise NotEstablished("埋込文字のない1page画像PDFになっていません", facts)
    elif kind == "edit-three-page":
        path = run / "fixtures" / "edit-three-page.pdf"
        facts = release_fake_ocr.make_text_pdf(path, pages=3)
    else:
        raise SupportError(f"未知のfixture: {kind}")
    manifest["fixtures"][kind] = {"path": str(path), **facts}
    save_run(manifest)
    return manifest["fixtures"][kind]


def ocr_settings(url, *, timeout=release_fake_ocr.PROVIDER_TIMEOUT):
    """既存Ollama設定でloopbackの合成OCRへ向ける。隔離copyにだけ置く。"""
    return {
        "lang": "ja",
        "ocr_provider": "ollama",
        "ollama_url": url,
        "ollama_model": release_fake_ocr.MODEL,
        "ocr_concurrency": 1,
        "ocr_timeout": timeout,
        "ocr_fallback_enabled": False,
        "ocr_fallback_chain": [],
    }


def prepare_ocr_connection(run, server):
    """1page画像PDF・並列1・summary非実行の接続準備。EXE側のUI操作はカードに記す。"""
    pdf = add_fixture_pdf(run, "ocr-one-page")
    settings = json.dumps(ocr_settings(server.url), ensure_ascii=False, indent=2)
    declare_overlay(
        run,
        {SETTINGS_NAME: settings.encode("utf-8")},
        "合成OCR接続: ollama設定(loopback)・ocr_concurrency=1",
    )
    return {
        "pdf": pdf,
        "server_url": server.url,
        "expected_posts": 1,
        "target_pages": 1,
        "ocr_concurrency": 1,
        "summary_executed": False,
        "note": "UIで対象1pageを選び、必要ならforce OCRで実行する(EXE側の人手操作)",
    }


def build_connection_entry(run, summary, *, user_answer, kind="ocr-single"):
    """server summaryと利用者回答から、PROTECTION証拠のconnection行を組み立てる。"""
    manifest = load_run(run)
    events = summary["events"]
    received = [e for e in events if e["event"] == "received"]
    entry = {
        "purpose": "connection-preparation",
        "kind": kind,
        "run_id": manifest["run_id"],
        "binary_sha256": manifest["source"]["exe_sha256"],
        "tree_sha256": manifest["source"]["tree_sha256"],
        "observed_at": _now(),
        "server": {
            "posts": summary["posts"],
            "attempts_by_image": summary["attempts_by_image"],
            "retransmissions": summary["retransmissions"],
            "rejected": len(summary["rejected"]),
            "expired": summary["expired"],
            "attempts": [
                {k: e.get(k) for k in ("attempt_id", "image_sha256", "page_id")}
                for e in received
            ],
            "events": [
                {k: e.get(k) for k in ("event", "attempt_id", "time")} for e in events
            ],
        },
        "user_answer": user_answer,
    }
    return entry


# ---------------------------------------------------------------------------
# 所有プロセス
# ---------------------------------------------------------------------------
def _live_records(manifest):
    live = []
    for record in manifest["processes"]:
        if record.get("exit") is not None:
            continue
        ident = process_identity(record["pid"])
        if ident and ident["alive"] and same_process(record, ident):
            live.append(record)
    return live


def _record_for(child, manifest, role, exe, extra=None):
    ident = process_identity(child.pid)
    if ident is None:
        raise OwnershipError("起動したprocessの同一性を取得できません")
    record = {
        "role": role,
        "pid": child.pid,
        "created": ident["created"],
        "created_iso": ident["created_iso"],
        "image": ident["image"],
        "session_id": ident["session_id"],
        "elevated": ident["elevated"],
        "exe_sha256": sha_file(exe),
        "argv": [str(exe)],
        "started_at": _now(),
        "parent_pid": os.getpid(),
        "exit": None,
        **(extra or {}),
    }
    if _norm_path(ident["image"]) != _norm_path(exe):
        # 自分で起動した子なので、この所有handleを通じてだけ回収する。
        child.kill()
        record["exit"] = "image-mismatch-killed"
        manifest["processes"].append(record)
        save_run(manifest)
        raise OwnershipError("起動したprocessのimageが想定EXEと一致しません")
    return record


def _launch(manifest, exe, popen):
    """引数なしで起動する。nonceや試験引数は渡さない。"""
    return popen(
        [str(exe)],
        cwd=manifest["copy"],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start(run, *, popen=subprocess.Popen, owner_prefix=PRODUCTION_PREFIX, settle=3.0):
    """未改変EXEを引数なしで起動する。既存owner/差分があれば何も送らず拒否する。"""
    manifest = load_run(run)
    if manifest["status"] not in ("prepared", "stopped"):
        raise OwnershipError(f"startできる状態ではありません: {manifest['status']}")
    if _live_records(manifest):
        raise OwnershipError("前回の所有processが生存しています。先にstopしてください")
    check = verify_copy(manifest)
    if not check["ok"] or check["overlay_changed"]:
        raise IsolationError(f"copyが配布manifest/overlayと一致しません: {check}")
    if not _source_unchanged(manifest):
        raise IsolationError("配布元が変化しています")
    owner = probe_owner(owner_prefix)
    if owner:
        manifest["last_refusal"] = {
            "at": _now(),
            "reason": "existing-owner",
            "owner": owner,
        }
        save_run(manifest)
        raise OwnershipError(f"既存のproduction ownerがあります: {owner}")
    exe = Path(manifest["copy"]) / "PageFolio.exe"
    snapshot(run, "before-start")
    manifest = load_run(run)
    before = foreground_info()
    child = _launch(manifest, exe, popen)
    record = _record_for(child, manifest, "primary", exe)
    record["foreground_before"] = before
    manifest["processes"].append(record)
    manifest["status"] = "running"
    save_run(manifest)
    if settle:
        time.sleep(settle)
    inspect(run, label="after-start")
    return record


def peer(run, *, with_run=None, popen=subprocess.Popen, owner_prefix=PRODUCTION_PREFIX):
    """自分が起動した一次ownerが生存・一致している時だけ、2つ目を起動する。"""
    manifest = load_run(run)
    live = [r for r in _live_records(manifest) if r["role"] == "primary"]
    if not live:
        raise OwnershipError(
            "同一性を確認できた一次ownerがありません。peerを起動しません"
        )
    if not probe_owner(owner_prefix):
        raise OwnershipError("ownerが未確立です(一次の起動安定後に実行してください)")
    source = load_run(with_run) if with_run else manifest
    check = verify_copy(source)
    if not check["ok"]:
        raise IsolationError("peer側のcopyが配布manifestと一致しません")
    exe = Path(source["copy"]) / "PageFolio.exe"
    child = _launch(source, exe, popen)
    extra = {
        "peer_source": {
            "run_id": source["run_id"],
            "role": source["role"],
            "version": source["source"]["version"],
            "exe_sha256": source["source"]["exe_sha256"],
        }
    }
    record = _record_for(child, manifest, "peer", exe, extra)
    manifest["processes"].append(record)
    manifest["subject"] = {
        "role": manifest["role"],
        "version": manifest["source"]["version"],
        "exe_sha256": manifest["source"]["exe_sha256"],
    }
    manifest["peer"] = extra["peer_source"]
    save_run(manifest)
    return record


def snapshot(run, label):
    manifest = load_run(run)
    repo = Path(manifest.get("repo") or REPO)
    item = {
        "label": label,
        "at": _now(),
        "copy": verify_copy(manifest),
        "source_distribution_tree_sha256": manifest["source"]["tree_sha256"],
        "source_unchanged": _source_unchanged(manifest),
        "originals": snapshot_originals(repo)
        if (repo / "pagefolio").is_dir()
        else None,
    }
    manifest["snapshots"].append(item)
    save_run(manifest)
    return item


def inspect(run, label="inspect"):
    """生PID・生成時刻・session・foreground・window・tree/原本を外部から観測する。"""
    manifest = load_run(run)
    processes = []
    for record in manifest["processes"]:
        ident = process_identity(record["pid"])
        state = "gone"
        if ident is not None:
            state = "same" if same_process(record, ident) else "mismatch"
        alive = bool(ident and ident["alive"] and state == "same")
        processes.append(
            {
                "role": record["role"],
                "pid": record["pid"],
                "created": record["created"],
                "identity": state,
                "alive": alive,
                "session_id": ident["session_id"] if ident else None,
                "elevated": ident["elevated"] if ident else None,
                "windows": windows_of(record["pid"]) if alive else [],
            }
        )
    foreground = foreground_info()
    owners = {p["pid"]: p["role"] for p in processes if p["alive"]}
    foreground["owned_by"] = owners.get(foreground["pid"])
    observation = {
        "label": label,
        "at": _now(),
        "monotonic": time.monotonic(),
        "processes": processes,
        "foreground": foreground,
        "owner_probe": probe_owner(),
        "observer": {
            "python": sys.version,
            "tk": manifest["environment"].get("observer_tk"),
        },
        "exe_embedded": manifest["source"]["embedded"],
        "copy": verify_copy(manifest),
    }
    index = len(manifest["observations"]) + 1
    manifest["observations"].append(observation)
    save_run(manifest)
    write_json(Path(run) / "evidence" / f"inspect-{index:03d}.json", observation)
    return observation


def _terminate_owned(record):
    api = _api()
    handle = api.k.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE,
        False,
        record["pid"],
    )
    if not handle:
        return "gone"
    try:
        if _creation(handle) != record["created"] or _norm_path(
            _image(handle)
        ) != _norm_path(record["image"]):
            return "identity-mismatch"
        if not api.k.TerminateProcess(handle, 1):
            return "terminate-failed"
        api.k.WaitForSingleObject(handle, 5000)
        return "terminated"
    finally:
        api.k.CloseHandle(handle)


def stop(run, *, timeout=10.0, force=True):
    """記録した所有processだけを、PID+生成時刻+imageの再照合後に回収する。

    通常終了(WM_CLOSE)を先に試し、残る場合だけ診断を保存してから所有handleで終了する。
    名前による一括killは行わない。同一性が一致しないprocessには触れない。
    """
    manifest = load_run(run)
    api = _api()
    results = []
    for record in manifest["processes"]:
        if record.get("exit") is not None:
            continue
        ident = process_identity(record["pid"])
        if ident is None or not ident["alive"]:
            record["exit"] = "already-exited"
            results.append({"pid": record["pid"], "result": "already-exited"})
            continue
        if not same_process(record, ident):
            record["exit"] = "identity-mismatch-untouched"
            results.append({"pid": record["pid"], "result": "identity-mismatch"})
            continue
        for window in windows_of(record["pid"]):
            api.u.PostMessageW(window["hwnd"], WM_CLOSE, 0, 0)
        deadline = time.monotonic() + timeout
        outcome = None
        while time.monotonic() < deadline:
            ident = process_identity(record["pid"])
            if ident is None or not ident["alive"] or not same_process(record, ident):
                outcome = "closed"
                break
            time.sleep(0.1)
        if outcome is None:
            write_json(
                Path(run) / "evidence" / f"stop-diagnostics-{record['pid']}.json",
                {
                    "at": _now(),
                    "record": record,
                    "windows": windows_of(record["pid"]),
                    "foreground": foreground_info(),
                    "copy": verify_copy(manifest),
                },
            )
            outcome = _terminate_owned(record) if force else "left-running"
        record["exit"] = outcome
        results.append({"pid": record["pid"], "result": outcome})
    manifest["status"] = (
        "stopped"
        if not any(r["result"] in ("left-running", "terminate-failed") for r in results)
        else "stop-failed"
    )
    save_run(manifest)
    snapshot(run, "after-stop")
    return results


def reset_for_case(run, new_case):
    """同一Gで所有copyを再利用する。変更や同一性不明なら新copyを要求する。"""
    manifest = load_run(run)
    _check_case(new_case)
    if _live_records(manifest):
        raise OwnershipError("所有processが生存中です。先にstopしてください")
    check = verify_copy(manifest)
    if not check["ok"] or not _source_unchanged(manifest):
        raise IsolationError(
            "copyまたは配布元が変化しています。新しいcopyを作ってください"
        )
    run = Path(run)
    copy = Path(manifest["copy"])
    for name, expected in manifest["overlay"].items():
        target = copy / name
        source = run / "overlay-source" / name
        if expected is None:
            if target.exists():
                target.unlink()
        else:
            target.write_bytes(source.read_bytes())
    again = verify_copy(manifest)
    if not again["ok"] or again["overlay_changed"]:
        raise IsolationError(
            "overlay復元後の再照合に失敗しました。新しいcopyが必要です"
        )
    manifest["case_history"].append(
        {
            "case": manifest["case"],
            "until": _now(),
            "generation": manifest["generation"],
        }
    )
    manifest["case"] = new_case
    manifest["generation"] += 1
    manifest["processes"] = []
    manifest["status"] = "prepared"
    save_run(manifest)
    return manifest


# ---------------------------------------------------------------------------
# 設定障害の準備(外部lock/tmp衝突)
# ---------------------------------------------------------------------------
def _create_file(path, access, share):
    api = _api()
    ctypes.set_last_error(0)
    handle = api.k.CreateFileW(str(path), access, share, None, OPEN_EXISTING, 0, None)
    if handle in (None, 0, _INVALID):
        return None, ctypes.get_last_error()
    return handle, 0


def probe_open(
    path, access, share=FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
):
    """非破壊の開閉だけで制限成立を観測する。DELETE accessも削除はしない。"""
    handle, error = _create_file(path, access, share)
    if handle is not None:
        _api().k.CloseHandle(handle)
    return {"ok": handle is not None, "win32_error": error, "access": hex(access)}


class FaultPreparation:
    """設定障害を保持するobject。close()で外部handleを解放する。"""

    def __init__(self, kind, settings_path):
        self.kind = kind
        self.settings = Path(settings_path)
        self.handle = None
        self.record = {}

    def close(self):
        if self.handle is not None:
            _api().k.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _hold(path, access, share):
    handle, error = _create_file(path, access, share)
    if handle is None:
        raise NotEstablished(f"外部handleを取得できません: win32={error}")
    return handle


def prepare_settings_fault(copy_dir, kind):
    """合成JSON/隔離copyだけで設定障害を作り、外部の観測記録を返す。

    成立を外部probeで確認できなければNotEstablished(not-run)。製品コード・実ACLは触らない。
    """
    if kind not in ("missing", "corrupt", "unreadable", "save-write", "save-replace"):
        raise SupportError(f"未対応の障害: {kind}")
    copy_dir = Path(copy_dir)
    settings = copy_dir / SETTINGS_NAME
    tmp = copy_dir / (SETTINGS_NAME + ".tmp")
    fault = FaultPreparation(kind, settings)
    ident = process_identity(os.getpid())
    base = {
        "kind": kind,
        "settings_path": str(settings),
        "observer": {"pid": os.getpid(), "created": ident["created"]},
        "observed_at": _now(),
    }
    try:
        if kind == "missing":
            established = not settings.exists() and not tmp.exists()
            fault.record = {**base, "settings_exists": settings.exists()}
        elif kind == "corrupt":
            data = b'{"theme": "dark", "font_size": '  # 閉じていない不正JSON
            settings.write_bytes(data)
            try:
                json.loads(data.decode("utf-8"))
                parsed = True
            except ValueError:
                parsed = False
            established = not parsed
            fault.record = {
                **base,
                "bytes_sha256": hashlib.sha256(data).hexdigest(),
                "json_parseable": parsed,
            }
        elif kind == "unreadable":
            _require_settings(settings)
            before = sha_file(settings)
            fault.handle = _hold(settings, GENERIC_READ, 0)
            probe = probe_open(
                settings, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE
            )
            established = (
                not probe["ok"] and probe["win32_error"] == ERROR_SHARING_VIOLATION
            )
            fault.record = {
                **base,
                "handle": {"access": hex(GENERIC_READ), "share": hex(0)},
                "probe_read": probe,
                "original_sha256": before,
            }
        elif kind == "save-write":
            _require_settings(settings)
            before = sha_file(settings)
            with tmp.open("xb") as stream:  # 同名tmpの排他的作成衝突を作る
                stream.write(b"uat-owned-tmp")
            try:
                with tmp.open("xb"):
                    collided = False
            except FileExistsError:
                collided = True
            established = collided and sha_file(settings) == before
            fault.record = {
                **base,
                "original_sha256": before,
                "tmp": {
                    "exists": tmp.exists(),
                    "sha256": sha_file(tmp),
                    "owner": "release_uat_support",
                    "exclusive_create_collision": collided,
                },
                "note": "書込開始前の失敗(tmp衝突)であり、書込途中失敗ではない",
            }
        else:  # save-replace
            _require_settings(settings)
            before = sha_file(settings)
            share = FILE_SHARE_READ | FILE_SHARE_WRITE  # DELETE共有を許さない
            fault.handle = _hold(settings, GENERIC_READ | GENERIC_WRITE, share)
            delete_probe = probe_open(settings, DELETE)
            read_probe = probe_open(settings, GENERIC_READ)
            established = (
                not delete_probe["ok"]
                and delete_probe["win32_error"] == ERROR_SHARING_VIOLATION
                and read_probe["ok"]
            )
            fault.record = {
                **base,
                "handle": {
                    "access": hex(GENERIC_READ | GENERIC_WRITE),
                    "share": hex(share),
                },
                "probe_delete": delete_probe,
                "probe_read": read_probe,
                "original_sha256": before,
            }
    except NotEstablished:
        fault.close()
        raise
    except Exception:
        fault.close()
        raise
    fault.record["established"] = bool(established)
    if not established:
        fault.close()
        raise NotEstablished(f"{kind}の成立を外部probeで確認できません", fault.record)
    return fault


def _require_settings(settings):
    if not settings.is_file():
        raise NotEstablished("対象の合成設定がありません(先にoverlayで置く)")


# ---------------------------------------------------------------------------
# 中断・再開
# ---------------------------------------------------------------------------
def save_resume_state(phase_dir, *, run, completed, pending, last_answer, extra=None):
    """中断時にcompleted/pending行・run ID・対象hash・環境・最後の回答を保存する。"""
    manifest = load_run(run)
    state = {
        "saved_at": _now(),
        "run_id": manifest["run_id"],
        "generation": manifest["generation"],
        "exe_sha256": manifest["source"]["exe_sha256"],
        "tree_sha256": manifest["source"]["tree_sha256"],
        "environment": manifest["environment"],
        "owned_processes": [
            {k: r[k] for k in ("role", "pid", "created", "exit")}
            for r in manifest["processes"]
        ],
        "completed": sorted(completed),
        "pending": sorted(pending),
        "last_answer": last_answer,
        **(extra or {}),
    }
    path = Path(phase_dir) / RESUME
    history = read_json(path)["history"] if path.exists() else []
    history.append(state)
    write_json(path, {"schema_version": 1, "history": history})
    return state


def check_resume(phase_dir, current):
    """保存した最新状態と現状を照合する。同一なら未実施から続行、差分は新世代。"""
    path = Path(phase_dir) / RESUME
    if not path.exists():
        return {"same": False, "action": "no-state", "differences": ["保存状態なし"]}
    state = read_json(path)["history"][-1]
    differences = [
        f"{key}: {state.get(key)!r} -> {current.get(key)!r}"
        for key in ("run_id", "exe_sha256", "tree_sha256")
        if state.get(key) != current.get(key)
    ]
    for key, value in (current.get("environment") or {}).items():
        if key in ("observer_python", "observer_tk", "os") and (
            state["environment"].get(key) != value
        ):
            differences.append(f"environment.{key}が変化")
    return {
        "same": not differences,
        "action": "continue-pending" if not differences else "new-generation",
        "pending": state["pending"] if not differences else [],
        "differences": differences,
    }


def supersede_rows(manual, *, generation, reason, ids=None):
    """元のpassを消さずsuperseded_by/reasonを追記し、新世代のnot-run行を作る。"""
    result = json.loads(json.dumps(manual))
    for case in result.get("cases", []):
        if ids is not None and case["id"] not in ids:
            continue
        added = []
        for sub in case["subrows"]:
            if sub.get("superseded_by"):
                continue
            sub["superseded_by"] = generation
            sub["supersede_reason"] = reason
            fresh = {
                k: v
                for k, v in sub.items()
                if k not in ("superseded_by", "supersede_reason")
            }
            fresh.update(
                status="not-run",
                answer="",
                observations={},
                binary_sha256="",
                run_id="",
                observed_at="",
                generation=generation,
            )
            added.append(fresh)
        case["subrows"].extend(added)
    return result


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------
class Audit:
    def __init__(self, mode):
        self.mode = mode
        self.reasons = []
        self.extra = {}

    def fail(self, message):
        self.reasons.append(message)

    @property
    def ok(self):
        return not self.reasons

    def report(self):
        return {
            "mode": self.mode,
            "ok": self.ok,
            "exit_code": 0 if self.ok else 1,
            "reasons": self.reasons,
            "phase_complete": False,
            "release_allowed": False,
            **self.extra,
        }


def expand_ids(spec, audit):
    if spec is None or not str(spec).strip():
        audit.fail("--require-passのID指定が空です")
        return []
    ids = []
    for raw in str(spec).split(","):
        item = raw.strip()
        if not item:
            audit.fail("--require-passに空のID要素があります")
        elif item not in ALL_IDS:
            audit.fail(f"未知のIDです: {item}")
        elif item not in ids:
            ids.append(item)
    return ids


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _need(audit, path, name):
    file = Path(path) / name
    if not file.is_file():
        audit.fail(f"{name}がありません")
        return None
    try:
        return read_json(file)
    except SupportError as error:
        audit.fail(str(error))
        return None


def load_target(phase_dir, audit):
    build = _need(audit, phase_dir, BUILD)
    if build is None:
        return None
    final = build.get("final_release")
    if not isinstance(final, dict):
        audit.fail(f"{BUILD}にfinal_releaseがありません")
        return None
    target = {
        "exe_sha256": final.get("exe_sha256"),
        "tree_sha256": final.get("tree_sha256"),
        "version": build.get("version"),
        "input_manifest_sha256": final.get("input_manifest_sha256"),
    }
    if not all(_text(v) for v in target.values()):
        audit.fail(f"{BUILD}の対象hash/版が欠落しています")
        return None
    return target


def _check_subrow(case_id, sub, target, audit, *, strict):
    where = f"{case_id}/{sub.get('subrow', '?')}"
    if not _text(sub.get("subrow")) or not _text(sub.get("entry")):
        audit.fail(f"{where}: subrow/entryが欠落しています")
        return
    status = sub.get("status")
    if status not in STATUSES:
        audit.fail(f"{where}: statusが不正です: {status!r}")
        return
    kind = sub.get("evidence_kind")
    if kind not in EVIDENCE_KINDS:
        audit.fail(f"{where}: 証拠種別が不正です: {kind!r}")
        return
    if case_id == "W12b":
        _check_w12b(where, sub, target, audit)
    if status != "pass":
        if strict:
            audit.fail(f"{where}: {status}でありpassではありません")
        return
    if kind == "unit":
        audit.fail(f"{where}: 単体試験は人手/実機passの根拠にできません")
    if sub["entry"] == "production-exe" and kind != "production-exe":
        audit.fail(f"{where}: {kind}の証拠を実配布EXEのpassへ昇格できません")
    answer = sub.get("answer")
    if not _text(answer) or case_id not in answer:
        audit.fail(f"{where}: ケースID付きの利用者回答がありません")
    required = sub.get("required_observations")
    observations = sub.get("observations")
    if not isinstance(required, list) or not required:
        audit.fail(f"{where}: 必須観測の宣言がありません")
    elif not isinstance(observations, dict) or any(
        not observations.get(name) for name in required
    ):
        audit.fail(f"{where}: 必須観測が不足しています")
    for field in ("run_id", "observed_at"):
        if not _text(sub.get(field)):
            audit.fail(f"{where}: {field}がありません")
    env = sub.get("environment")
    if not isinstance(env, dict) or any(
        env.get(k) in (None, "") for k in ("os", "elevated", "session_id")
    ):
        audit.fail(f"{where}: 環境(os/権限/session)が不足しています")
    if target is not None:
        if (
            kind == "production-exe"
            and sub.get("binary_sha256") != target["exe_sha256"]
        ):
            audit.fail(f"{where}: binary hashが最終EXEと一致しません")
        if (
            kind in ("python-real", "fault-injection")
            and sub.get("input_manifest_sha256") != target["input_manifest_sha256"]
        ):
            audit.fail(f"{where}: 入力manifest hashが現行buildと一致しません")


def _check_w12b(where, sub, target, audit):
    subject = sub.get("subject")
    peer_row = sub.get("peer")
    if not isinstance(subject, dict):
        audit.fail(f"{where}: 主対象(subject)が欠落しています")
        return
    if subject.get("role") != "final-release-candidate":
        audit.fail(f"{where}: 主対象がfinal-release-candidateではありません")
    if target is not None and (
        subject.get("binary_sha256") != target["exe_sha256"]
        or subject.get("version") != target["version"]
    ):
        audit.fail(f"{where}: 主対象が最終hash/版と一致しません")
    if not isinstance(peer_row, dict):
        if sub.get("status") == "pass":
            audit.fail(f"{where}: peerの記録がありません")
        return
    role = peer_row.get("role")
    if role == "technical-tracer-real-exe":
        provenance = peer_row.get("provenance")
        if (
            not _text(peer_row.get("binary_sha256"))
            or peer_row.get("binary_sha256") == subject.get("binary_sha256")
            or not _text(peer_row.get("version"))
            or peer_row.get("version") == subject.get("version")
            or not isinstance(provenance, dict)
            or not provenance.get("run_id")
            or not provenance.get("source_manifest_sha256")
        ):
            audit.fail(f"{where}: tracer peerの来歴/別版/別hashが不十分です")
    elif role == "same-version-copy":
        if (
            peer_row.get("binary_sha256") != subject.get("binary_sha256")
            or peer_row.get("version") != subject.get("version")
            or peer_row.get("claims_other_version")
        ):
            audit.fail(f"{where}: 同版copyを別版として扱うことはできません")
    elif role == "python-entry":
        if peer_row.get("entry") not in ("script", "module"):
            audit.fail(f"{where}: python-entry peerのentryが不正です")
    else:
        audit.fail(f"{where}: peer roleが不正です: {role!r}")


def _active(case):
    return [s for s in case.get("subrows", []) if not s.get("superseded_by")]


def check_manual(phase_dir, ids, audit, *, strict, target):
    manual = _need(audit, phase_dir, MANUAL)
    if manual is None:
        return
    cases = {c.get("id"): c for c in manual.get("cases", []) if isinstance(c, dict)}
    for case_id in ids:
        case = cases.get(case_id)
        if case is None:
            audit.fail(f"{case_id}: ケースが宣言されていません")
            continue
        rows = _active(case)
        if not rows:
            audit.fail(f"{case_id}: 有効なsubrowがありません")
            continue
        for sub in case.get("subrows", []):
            if sub.get("superseded_by") and not _text(sub.get("supersede_reason")):
                audit.fail(f"{case_id}: superseded行に理由がありません")
        spec = CASE_MINIMUM.get(case_id, {})
        if spec.get("exe", True) and not any(
            s.get("entry") == "production-exe" for s in rows
        ):
            audit.fail(f"{case_id}: 実配布EXE入口のsubrowが宣言されていません")
        if len(rows) < spec.get("min_rows", 1):
            audit.fail(f"{case_id}: subrow宣言が不足しています({len(rows)}行)")
        conditions = {s.get("condition") for s in rows}
        if not spec.get("conditions", set()) <= conditions:
            audit.fail(f"{case_id}: 条件宣言が不足しています")
        if spec.get("subject") and any(not s.get("subject") for s in rows):
            audit.fail(f"{case_id}: 主対象が欠落したsubrowがあります")
        for sub in rows:
            _check_subrow(case_id, sub, target, audit, strict=strict)


def _hash_matches(path, expected):
    return path.is_file() and sha_file(path) == expected


def check_build(phase_dir, repo, audit):
    """06-BUILD-EVIDENCE.jsonを実ディスクと読取照合する。buildは呼ばず何も変えない。"""
    build = _need(audit, phase_dir, BUILD)
    if build is None:
        return None
    version, protected = read_constants(repo)
    final = build.get("final_release")
    if not isinstance(final, dict):
        audit.fail("final_releaseがありません")
        return None
    if build.get("version") != version:
        audit.fail(f"証拠の版({build.get('version')})がAPP_VERSION({version})と不一致")
    if build.get("release_allowed") is not False or "uat_status" not in build:
        audit.fail("release_allowed=false/uat_statusの別欄がありません")
    runs = [
        r
        for r in final.get("runs", [])
        if isinstance(r, dict)
        and r.get("role") == "final-release"
        and not r.get("tracer")
    ]
    ids = [r.get("run_id") for r in runs]
    if not all(_text(i) for i in ids):
        audit.fail("run IDが欠落しています")
        return None
    if len(runs) < 2 or len(set(ids)) < 2:
        audit.fail("最終版の初回/再buildの異なる2runが揃っていません")
        return None
    if len(runs) > 2:
        audit.fail("最終版のbuild runが3つ以上あります(2回で確定する契約)")
        return None
    by_order = {r.get("order"): r for r in runs}
    if set(by_order) != {"initial", "rebuild"}:
        audit.fail("初回(initial)と再build(rebuild)のorderが揃っていません")
        return None
    first, second = by_order["initial"], by_order["rebuild"]
    output_root = Path(final.get("output_root", ""))
    final_dir = Path(final.get("final_dir", ""))
    if not output_root.is_dir() or not final_dir.is_dir():
        audit.fail("output-root/最終先が存在しません")
        return None
    if first.get("cli_argv") != second.get("cli_argv") or not first.get("cli_argv"):
        audit.fail("2回のCLI引数が同一ではありません")
    if first.get("input_manifest_sha256") != second.get("input_manifest_sha256"):
        audit.fail("2回の入力manifest hashが一致しません")
    if second.get("input_manifest_sha256") != final.get("input_manifest_sha256"):
        audit.fail("最終入力manifest hashが記録と一致しません")
    reports = {}
    for label, run in (("initial", first), ("rebuild", second)):
        if (
            run.get("pyinstaller_exit") != 0
            or run.get("pyinstaller_executed") is not True
        ):
            audit.fail(f"{label}: 実PyInstaller成功の記録がありません")
        report_path = output_root / ".release-work" / str(run["run_id"]) / "report.json"
        if _norm_path(run.get("report_path")) != _norm_path(report_path):
            audit.fail(f"{label}: 記録時と現在のreport pathが一致しません")
        if not _hash_matches(report_path, run.get("report_sha256")):
            audit.fail(f"{label}: 外部reportが存在しないかhash不一致です")
            continue
        report = read_json(report_path)
        reports[label] = report
        argv = report.get("argv") or []
        if (
            report.get("run_id") != run["run_id"]
            or report.get("success") is not True
            or report.get("status") != "VERIFIED_BUILD"
            or report.get("version") != version
            or "--clean" not in argv
            or "PyInstaller" not in argv
            or (report.get("builder") or {}).get("exit") != 0
        ):
            audit.fail(f"{label}: 外部reportの成功/版/引数/exitが不整合です")
        if canonical_sha(report.get("input_manifest")) != run.get(
            "input_manifest_sha256"
        ):
            audit.fail(f"{label}: reportの入力manifestと記録hashが不一致です")
    files, dirs = walk_tree(final_dir)
    before = stat_tree(final_dir)
    if tree_sha(files, dirs) != final.get("tree_sha256") or files.get(
        "PageFolio.exe"
    ) != final.get("exe_sha256"):
        audit.fail("最終配布のtree/EXE hashが記録と一致しません")
    if second.get("tree_sha256") != final.get("tree_sha256"):
        audit.fail("再build runの記録hashが最終treeと一致しません")
    embedded = read_json(final_dir / "release-report.json")
    if embedded.get("run_id") != second["run_id"]:
        audit.fail("同梱reportが最終(再build)runのものではありません")
    if "rebuild" in reports and reports["rebuild"].get(
        "embedded_report_sha256"
    ) != files.get("release-report.json"):
        audit.fail("同梱reportのhashが外部reportの記録と一致しません")
    history = output_root / ".release-history" / str(second["run_id"])
    if not history.is_dir():
        audit.fail("旧tree(history)が保持されていません")
    else:
        h_files, h_dirs = walk_tree(history)
        if tree_sha(h_files, h_dirs) != first.get("tree_sha256"):
            audit.fail("historyのtreeが初回runの記録hashと一致しません")
        if read_json(history / "release-report.json").get("run_id") != first["run_id"]:
            audit.fail("historyの同梱reportが初回runのものではありません")
        _check_protected_absent(h_files, protected, audit, "history")
    _check_protected_absent(files, protected, audit, "最終配布")
    repo = Path(repo)
    canon = {
        "ocr_custom_prompt_sample.md": repo
        / "distribution/samples/ocr_custom_prompt_sample.md",
        "ocr_summary_prompt_sample.md": repo
        / "distribution/samples/ocr_summary_prompt_sample.md",
        "はじめに.md": repo / "distribution/はじめに.md",
        "docs/CONFIGURATION.md": repo / "docs/CONFIGURATION.md",
    }
    recorded = final.get("bundled_sha256") or {}
    for name, source in canon.items():
        if not source.is_file() or files.get(name) != sha_file(source):
            audit.fail(f"同梱{name}が正本/現行ファイルとSHA-256不一致です")
        if recorded.get(name) != files.get(name):
            audit.fail(f"同梱{name}の記録hashが不足/不一致です")
    if before != stat_tree(final_dir):
        audit.fail("監査中に最終配布のmtime/sizeが変化しました")
    return {
        "exe_sha256": final.get("exe_sha256"),
        "tree_sha256": final.get("tree_sha256"),
        "version": version,
        "input_manifest_sha256": final.get("input_manifest_sha256"),
        "final_run_id": second["run_id"],
    }


def _check_protected_absent(files, protected, audit, label):
    names = {n.casefold() for n in protected}
    leaked = sorted(r for r in files if Path(r).name.casefold() in names)
    if leaked:
        audit.fail(f"{label}に保護名のファイルが混入しています: {leaked}")


def _walk_values(value, key):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key and isinstance(v, str):
                yield v
            yield from _walk_values(v, key)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item, key)


def _cmp_entries(before, after):
    return before == after and isinstance(before, dict) and bool(before)


def check_preparation(phase_dir, repo, audit):
    build = check_build(phase_dir, repo, Audit("build"))
    target = build
    if target is None:
        audit.fail("build証拠が不成立のためpreparationを確定できません")
    prot = _need(audit, phase_dir, PROTECTION)
    prep = Path(phase_dir) / PREPARATION
    if not prep.is_file():
        audit.fail(f"{PREPARATION}がありません")
    if prot is None or not prep.is_file():
        return
    _, protected = read_constants(repo)
    exe = target["exe_sha256"] if target else None
    ref = prot.get("build_ref") or {}
    if target and (
        ref.get("exe_sha256") != exe
        or ref.get("final_run_id") != target["final_run_id"]
    ):
        audit.fail("保護証拠が最終buildのrun/EXEを参照していません")
    stops = {s.get("name", "").casefold(): s for s in prot.get("protection_stop", [])}
    for name in protected:
        item = stops.get(name.casefold())
        if (
            not item
            or item.get("builder_started") is not False
            or not isinstance(item.get("exit_code"), int)
            or item["exit_code"] == 0
            or not _cmp_entries(item.get("before"), item.get("after"))
        ):
            audit.fail(f"保護名{name}: build開始前の停止/前後hash一致の記録が不足です")
    launch = prot.get("launch") or {}
    cases = launch.get("cases") or []
    if not cases or not _hash_matches_all(cases, exe):
        audit.fail("起動時保持の記録が不足/対象hash不一致です")
    for case in cases:
        if case.get("hash_before") != case.get("hash_stable"):
            audit.fail(f"起動時保持: {case.get('name')}が起動安定後に変化しています")
        if case.get("name") in ("corrupt", "unreadable") and (
            case.get("hash_after_exit") != case.get("hash_before")
        ):
            audit.fail(f"起動時保持: {case.get('name')}が終了後に変化しています")
    update = prot.get("update") or {}
    collision = update.get("collision") or {}
    if not (
        collision.get("stopped_before_choice") is True
        and collision.get("old_before") == collision.get("old_after")
        and collision.get("new_before") == collision.get("new_after")
        and collision.get("old_before")
    ):
        audit.fail("更新: 同名衝突時の選択前停止/両方保持の記録が不足です")
    clean = update.get("no_collision") or {}
    if not (
        clean.get("copied_hash_match") is True and clean.get("old_preserved") is True
    ):
        audit.fail("更新: 衝突なしのコピー後一致/旧保持の記録が不足です")
    connections = prot.get("connection") or []
    kinds = {c.get("kind") for c in connections}
    connection_runs = set()
    for item in connections:
        connection_runs.add(item.get("run_id"))
        _check_connection(item, exe, audit)
    if not {"ocr-single", "w05b-modal"} <= kinds:
        audit.fail("実接続(ocr-single)とnative modal(w05b-modal)の両方が必要です")
    faults = prot.get("faults") or {}
    for fault_id in FAULT_IDS:
        _check_fault(fault_id, faults.get(fault_id), exe, audit)
    manual = Path(phase_dir) / MANUAL
    if manual.is_file():
        for case in read_json(manual).get("cases", []):
            if case.get("id") in ("W04", "W05b"):
                for sub in case.get("subrows", []):
                    if sub.get("run_id") in connection_runs:
                        audit.fail("接続実証のrunをW04/W05b本受入へ転記できません")
    prep_text = prep.read_text(encoding="utf-8")
    evidence_runs = {r for r in _walk_values(prot, "run_id") if r}
    for run_id in sorted(evidence_runs):
        if run_id not in prep_text:
            audit.fail(f"{PREPARATION}に保護証拠のrun参照がありません: {run_id}")
    for ref_id in re.findall(r"run-ref:\s*([0-9a-f]{32})", prep_text):
        if ref_id not in evidence_runs:
            audit.fail(f"{PREPARATION}のrun参照が保護証拠にありません: {ref_id}")


def _hash_matches_all(cases, exe):
    return exe is not None and all(c.get("binary_sha256") == exe for c in cases)


def _check_connection(item, exe, audit):
    name = f"接続({item.get('kind')})"
    server = item.get("server") or {}
    attempts = server.get("attempts") or []
    events = [e.get("event") for e in server.get("events", [])]
    ok = (
        item.get("purpose") == "connection-preparation"
        and _text(item.get("run_id"))
        and item.get("binary_sha256") == exe
        and _text(item.get("user_answer"))
        and _text(item.get("observed_at"))
        and server.get("posts") == 1
        and len(attempts) == 1
        and attempts[0].get("page_id")
        and attempts[0].get("image_sha256")
        and not server.get("retransmissions")
        and not server.get("expired")
        and not server.get("rejected")
        and events.count("received") == 1
        and events.count("completed") == 1
        and (item.get("kind") != "w05b-modal" or events.count("released") == 1)
    )
    if not ok:
        audit.fail(f"{name}: 同page-attempt1件の待機→完了/利用者回答/hashが不足です")
    if item.get("kind") == "w05b-modal" and not (
        item.get("modal_shown") is True
        and item.get("peer_returned_to_modal") is True
        and item.get("answered_no") is True
        and item.get("same_request_completed") is True
    ):
        audit.fail(f"{name}: native modal→peer→いいえ→同処理完了の観測が不足です")


def _check_fault(fault_id, item, exe, audit):
    where = f"障害{fault_id}"
    if not isinstance(item, dict):
        audit.fail(f"{where}: 成立の外部観測がありません")
        return
    base = (
        item.get("established") is True
        and _text(item.get("method"))
        and _text(item.get("run_id"))
        and item.get("binary_sha256") == exe
        and _text(item.get("observed_at"))
        and isinstance(item.get("observation"), dict)
        and bool(item["observation"])
    )
    if not base:
        audit.fail(f"{where}: 未成立/hash不一致/外部観測の欠落です")
        return
    obs = item["observation"]
    if fault_id == "X01" and obs.get("settings_absent_until_stable") is not True:
        audit.fail(f"{where}: 起動安定時まで設定が不存在だった観測がありません")
    if fault_id == "X02" and (
        not obs.get("original_before")
        or obs.get("original_before") != obs.get("original_after")
    ):
        audit.fail(f"{where}: 原本hashの前後一致がありません")
    if fault_id in ("X03", "X04"):
        holder = obs.get("holder") or {}
        if not (
            holder.get("pid")
            and holder.get("created")
            and obs.get("probe_denied") is True
        ):
            audit.fail(f"{where}: 外部holder(PID+生成時刻)/probe拒否の観測がありません")


# -- 品質・引渡し・最終 ---------------------------------------------------------
def load_gate(phase_dir, audit):
    path = Path(phase_dir) / GATE
    if not path.is_file():
        audit.fail(f"{GATE}がありません")
        return None
    match = re.search(
        r"```json release-gate\s*\n(.*?)\n```", path.read_text("utf-8"), re.S
    )
    if not match:
        audit.fail(f"{GATE}にrelease-gateのJSONブロックがありません")
        return None
    try:
        data = json.loads(match.group(1))
    except ValueError:
        audit.fail(f"{GATE}のJSONを解釈できません")
        return None
    return data if isinstance(data, dict) else None


def check_quality(phase_dir, target, audit):
    quality = _need(audit, phase_dir, QUALITY)
    if quality is None or target is None:
        return None
    inputs = quality.get("inputs") or {}
    for key in ("exe_sha256", "tree_sha256", "version", "input_manifest_sha256"):
        if inputs.get(key) != target.get(key):
            audit.fail(f"品質証拠の入力({key})が現行buildと一致しません")
    q = quality.get("quality") or {}
    for step in ("ruff_check", "ruff_format", "ast"):
        if (q.get(step) or {}).get("exit") != 0:
            audit.fail(f"品質: {step}が成功していません")
    py = q.get("pytest") or {}
    if not (
        py.get("exit") == 0
        and py.get("failed") == 0
        and py.get("errors") == 0
        and py.get("crashed") is False
        and py.get("excluded") is False
        and py.get("single_process") is True
        and isinstance(py.get("passed"), int)
        and py["passed"] > 0
        and _text(py.get("log_sha256"))
    ):
        audit.fail(
            "品質: 全件pytestが失敗0/ERROR0/クラッシュ0/除外なしで完走していません"
        )
    p4 = quality.get("phase4") or {}
    if (
        p4.get("fresh") is not True
        or not _text(p4.get("covered_digest"))
        or (p4.get("covered_digest") != p4.get("current_digest"))
    ):
        audit.fail("Phase4の鮮度がcovered_digestで確認できません(stale)")
    unresolved = {
        u.get("id"): u for u in quality.get("unresolved", []) if isinstance(u, dict)
    }
    for uid in REQUIRED_UNRESOLVED:
        item = unresolved.get(uid)
        if item is None:
            audit.fail(f"未解除事項{uid}が台帳から欠落しています")
        elif not _text(item.get("evaluation")):
            audit.fail(f"未解除事項{uid}に根拠付きの評価がありません")
        elif item.get("status") == "resolved":
            ev = item.get("evidence") or {}
            if not (_text(ev.get("path")) and _text(ev.get("sha256"))):
                audit.fail(f"未解除事項{uid}をresolvedにする根拠がありません")
    return quality


def _check_unresolved_final(quality, audit):
    """最終監査は未解除事項ごとの根拠付き評価(解消またはユーザー明示承認)を要求する。"""
    for item in quality.get("unresolved", []):
        state, uid = item.get("status"), item.get("id")
        if state == "resolved":
            continue  # 根拠はcheck_qualityで検査済み
        approval = item.get("approval") or {}
        if state == "accepted-by-user" and _text(approval.get("quote")):
            continue
        audit.fail(f"未解除事項{uid}が最終監査で根拠付きに評価されていません({state})")


def _check_gates(gate, quality, audit, *, final):
    gates = {
        g.get("id"): g for g in gate.get("parent_gates", []) if isinstance(g, dict)
    }
    seen = [g.get("id") for g in gate.get("parent_gates", []) if isinstance(g, dict)]
    if sorted(seen) != sorted(PARENT_GATES):
        audit.fail(f"親ゲートが4件(重複・未知なし)ではありません: {seen}")
    digest = canonical_sha((quality or {}).get("inputs") or {})
    for gid in PARENT_GATES:
        item = gates.get(gid)
        if item is None:
            continue
        status = item.get("status")
        if status in ("fail", "needs-fix"):
            audit.fail(f"親ゲート{gid}が{status}です")
        elif status == "pending":
            if final:
                audit.fail(f"親ゲート{gid}がpendingです(最終監査は実走結果を要求)")
            elif not all(
                _text(item.get(k)) for k in ("owner", "command", "expected_report")
            ):
                audit.fail(f"親ゲート{gid}の担当/実行手段/期待報告が欠落しています")
        elif status == "pass":
            _check_gate_report(gid, item, digest, audit)
        else:
            audit.fail(f"親ゲート{gid}のstatusが不正です: {status!r}")
    threats = {t.get("id"): t for t in gate.get("threats", []) if isinstance(t, dict)}
    for threat_id in REQUIRED_THREATS:
        item = threats.get(threat_id)
        if item is None:
            audit.fail(f"脅威{threat_id}が登録されていません")
            continue
        severity, state = item.get("severity"), item.get("status")
        if severity == "high" and state == "open":
            audit.fail(f"既知のhigh脅威{threat_id}が未解消です")
        if final and severity == "high" and state != "mitigated":
            audit.fail(f"high脅威{threat_id}が未評価/未解消です(ASVS1)")
    for cond in gate.get("release_conditions", []):
        if cond.get("status") != "pass" or not _text(cond.get("evidence")):
            audit.fail(f"リリース条件{cond.get('id')}が根拠付きpassではありません")
    if not gate.get("release_conditions"):
        audit.fail("リリース条件の台帳が空です")
    if final:
        nyquist = gate.get("nyquist") or {}
        if not (nyquist.get("ran") is True and nyquist.get("passed") is True):
            audit.fail("Nyquist(validate-phase)の実走合格がありません")


def _check_gate_report(gid, item, digest, audit):
    report = item.get("report") or {}
    if not (
        _text(report.get("path"))
        and _text(report.get("sha256"))
        and report.get("exit") == 0
        and _text(report.get("at"))
        and report.get("verdict") == "pass"
    ):
        audit.fail(f"親ゲート{gid}: 報告path/hash/exit/時刻/判定が不足の偽passです")
    elif report.get("target_inputs_sha256") != digest:
        audit.fail(f"親ゲート{gid}: 対象入力が現行の品質入力と一致しません")


def audit_handoff(phase_dir, repo, audit, *, final):
    build = check_build(phase_dir, repo, audit)
    check_preparation(phase_dir, repo, audit)
    check_manual(phase_dir, ALL_IDS, audit, strict=True, target=build)
    quality = check_quality(phase_dir, build, audit)
    if final and quality is not None:
        _check_unresolved_final(quality, audit)
    gate = load_gate(phase_dir, audit)
    if gate is not None:
        _check_gates(gate, quality, audit, final=final)
    audit.extra["handoff_ready"] = audit.ok and not final
    audit.extra["final_audit_passed"] = audit.ok and final


def run_audit(phase_dir, *, mode, repo=None, require=None):
    """証拠を読むだけで判定する。読取・解釈の失敗は例外にせず不合格(fail closed)。"""
    audit = Audit(mode)
    try:
        _run_audit(audit, Path(phase_dir), mode, Path(repo or REPO), require)
    except (
        SupportError,
        OSError,
        KeyError,
        TypeError,
        AttributeError,
        ValueError,
    ) as e:
        audit.fail(f"証拠を解釈できません: {type(e).__name__}: {e}")
    return audit


def _run_audit(audit, phase_dir, mode, repo, require):
    if mode == "allow-pending":
        target = load_target(phase_dir, Audit("target"))
        check_manual(phase_dir, ALL_IDS, audit, strict=False, target=target)
        audit.extra.update(structural_only=True, task_ready=False)
    elif mode == "require-pass":
        ids = expand_ids(require, audit)
        target = load_target(phase_dir, audit)
        if ids:
            check_manual(phase_dir, ids, audit, strict=True, target=target)
        audit.extra.update(ids=ids, task_ready=audit.ok)
    elif mode == "build-only":
        check_build(phase_dir, repo, audit)
    elif mode == "preparation-only":
        check_preparation(phase_dir, repo, audit)
    elif mode == "for-handoff":
        audit_handoff(phase_dir, repo, audit, final=False)
    elif mode == "final":
        audit_handoff(phase_dir, repo, audit, final=True)
    else:
        raise SupportError(f"未知のaudit mode: {mode}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _json_out(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _cmd_audit(args):
    modes = {
        "allow_pending": args.allow_pending,
        "require_pass": args.require_pass is not None,
        "build_only": args.build_only,
        "preparation_only": args.preparation_only,
        "for_handoff": args.for_handoff,
    }
    chosen = [k for k, v in modes.items() if v]
    mode = chosen[0].replace("_", "-") if chosen else "final"
    audit = run_audit(
        args.phase_dir, mode=mode, repo=args.repo, require=args.require_pass
    )
    _json_out(audit.report())
    return 0 if audit.ok else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--distribution", type=Path, required=True)
    p.add_argument("--case", required=True)
    p.add_argument("--entry", default="production-exe")
    p.add_argument("--evidence-kind", default="production-exe", choices=EVIDENCE_KINDS)
    p.add_argument("--role", default="final-release-candidate", choices=ROLES)
    p.add_argument("--base", type=Path)
    p.add_argument(
        "--pdf", choices=("ocr-one-page", "edit-three-page"), action="append"
    )
    for name in ("start", "peer", "inspect", "stop", "serve-ocr", "fault"):
        q = sub.add_parser(name)
        q.add_argument("--run", type=Path, required=True)
        if name == "peer":
            q.add_argument("--with-run", type=Path)
        if name == "stop":
            q.add_argument("--no-force", action="store_true")
        if name == "serve-ocr":
            q.add_argument("--mode", choices=release_fake_ocr.MODES, default="hold")
            q.add_argument("--serve-seconds", type=float, default=3600.0)
        if name == "fault":
            q.add_argument(
                "--kind",
                required=True,
                choices=(
                    "missing",
                    "corrupt",
                    "unreadable",
                    "save-write",
                    "save-replace",
                ),
            )
            q.add_argument("--hold-seconds", type=float, default=600.0)
    a = sub.add_parser("audit")
    a.add_argument("--phase-dir", type=Path, required=True)
    a.add_argument("--repo", type=Path)
    group = a.add_mutually_exclusive_group()
    group.add_argument("--allow-pending", action="store_true")
    group.add_argument("--require-pass")
    group.add_argument("--build-only", action="store_true")
    group.add_argument("--preparation-only", action="store_true")
    group.add_argument("--for-handoff", action="store_true")
    r = sub.add_parser("resume-check")
    r.add_argument("--phase-dir", type=Path, required=True)
    r.add_argument("--run", type=Path, required=True)
    return parser


def _serve_ocr(args):
    manifest = load_run(args.run)
    evidence = Path(args.run) / "evidence"
    server = release_fake_ocr.FakeOcrServer(
        mode=args.mode,
        run_id=manifest["run_id"],
        log_path=evidence / "fake-ocr-events.jsonl",
        release_flag=Path(args.run) / "release.flag",
    ).start()
    info = prepare_ocr_connection(args.run, server)
    _json_out(info)
    stop_flag = Path(args.run) / "stop-fake-ocr.flag"
    deadline = time.monotonic() + args.serve_seconds
    try:
        while time.monotonic() < deadline and not stop_flag.exists():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        summary = server.summary()
        server.stop()
        write_json(evidence / "fake-ocr-summary.json", summary)
    return 0


def _fault(args):
    manifest = load_run(args.run)
    if args.kind in ("unreadable", "save-write", "save-replace"):
        settings = Path(manifest["copy"]) / SETTINGS_NAME
        if not settings.exists():
            declare_overlay(
                args.run, {SETTINGS_NAME: b'{"theme": "dark"}'}, "障害準備用の合成設定"
            )
    if args.kind == "missing":
        declare_overlay(args.run, {SETTINGS_NAME: None}, "設定不存在")
    try:
        fault = prepare_settings_fault(manifest["copy"], args.kind)
    except NotEstablished as error:
        _json_out(
            {
                "established": False,
                "status": "not-run",
                "reason": str(error),
                "record": error.record,
            }
        )
        return 3
    copy_dir = Path(manifest["copy"])
    if args.kind == "corrupt":  # 作った実bytesをoverlayの正本として宣言する
        declare_overlay(
            args.run,
            {SETTINGS_NAME: (copy_dir / SETTINGS_NAME).read_bytes()},
            "破損JSON",
        )
    elif args.kind == "save-write":
        tmp = SETTINGS_NAME + ".tmp"
        declare_overlay(args.run, {tmp: (copy_dir / tmp).read_bytes()}, "tmp衝突")
    _json_out(fault.record)
    flag = Path(args.run) / "release-fault.flag"
    deadline = time.monotonic() + args.hold_seconds
    try:
        while time.monotonic() < deadline and not flag.exists():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        fault.close()
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare(
                args.distribution,
                args.case,
                entry=args.entry,
                evidence_kind=args.evidence_kind,
                role=args.role,
                base=args.base,
            )
            for kind in args.pdf or []:
                add_fixture_pdf(manifest["run"], kind)
            _json_out(load_run(manifest["run"]))
        elif args.command == "start":
            _json_out(start(args.run))
        elif args.command == "peer":
            _json_out(peer(args.run, with_run=args.with_run))
        elif args.command == "inspect":
            _json_out(inspect(args.run))
        elif args.command == "stop":
            _json_out(stop(args.run, force=not args.no_force))
        elif args.command == "serve-ocr":
            return _serve_ocr(args)
        elif args.command == "fault":
            return _fault(args)
        elif args.command == "audit":
            return _cmd_audit(args)
        elif args.command == "resume-check":
            manifest = load_run(args.run)
            _json_out(
                check_resume(
                    args.phase_dir,
                    {
                        "run_id": manifest["run_id"],
                        "exe_sha256": manifest["source"]["exe_sha256"],
                        "tree_sha256": manifest["source"]["tree_sha256"],
                        "environment": manifest["environment"],
                    },
                )
            )
    except SupportError as error:
        print(f"停止: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
