# ruff: noqa
"""preview 復帰後の入力先が右ペインのボタンになる件 (debug: preview-focus-not-restored) の観測用driver。

diag_owner.py で隔離PageFolio(一次)を起動し、本番の起動経路のまま二次起動(peer)で復帰させ、
入力先の移動・FocusIn/FocusOut・キー/マウス入力・前景/OS入力先/ポインタ位置の時系列
(focus-trace.json) と復帰結果 (focus-result.json) を回収して、この目録へ保存する。
製品と tests/ は import/patch/変更しない (Phase 4 の covered_files を動かさない)。
06-05 の証拠ディレクトリへは何も書かない (G1 の合否には使わない診断)。

利用者の操作は 06-05 の uat_row.py と同じ流れ:
  1. 隔離PageFolioが起動する (前面に出ることがある)
  2. PowerShell へ戻って Enter (戻り方はいつもどおりでよい。PageFolio 内をクリックしない)
  3. 二次起動 -> PageFolio が前面に復帰
  4. 戻り方と、Enter 前の操作を短く答える

usage (リポジトリ直下で):
  .venv\\Scripts\\python.exe .planning\\debug\\preview-focus-not-restored-evidence\\diag_preview_focus.py --case preview
  .venv\\Scripts\\python.exe .planning\\debug\\preview-focus-not-restored-evidence\\diag_preview_focus.py --case thumb   (対照)
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWNER = OUT / "diag_owner.py"
ORIGINALS = ("pagefolio_settings.json", "ocr_custom_prompt.md", "ocr_summary_prompt.md")

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.IsWindow.argtypes = [wt.HWND]
user32.GetForegroundWindow.restype = wt.HWND


def now():
    return datetime.now(timezone.utc).isoformat()


def say(text=""):
    print(text, flush=True)


def fingerprints():
    return {
        name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
        if (REPO / name).exists()
        else None
        for name in ORIGINALS
    }


def window_info(hwnd):
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    title = ctypes.create_unicode_buffer(256)
    cls = ctypes.create_unicode_buffer(128)
    pid = wt.DWORD()
    user32.GetWindowTextW(hwnd, title, 256)
    user32.GetClassNameW(hwnd, cls, 128)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {
        "hwnd": int(hwnd),
        "title": title.value,
        "class": cls.value,
        "pid": pid.value,
    }


def summarize(result, trace):
    say("")
    say("== 結果 ==")
    if result:
        say(f"  result          : {result.get('result')}")
        say(f"  expected_focus  : {result.get('expected_focus')}")
        say(f"  immediate_focus : {result.get('immediate_focus')}")
        say(f"  settled_focus   : {result.get('settled_focus')}")
        say(f"  focus_correct   : {result.get('focus_correct')}")
    else:
        say("  focus-result.json が得られませんでした")
    if not trace:
        say("  focus-trace.json が得られませんでした")
        return
    say("")
    say("== 入力先・入力の時系列 (秒は owner の観測開始から) ==")
    keep = {
        "FocusIn",
        "FocusOut",
        "ButtonPress",
        "ButtonRelease",
        "KeyPress",
        "KeyRelease",
        "tcl-focus",
        "restore-before",
        "restore-result",
        "restore-after",
        "settled",
        "error",
    }
    last = None
    for e in trace:
        kind = e["kind"]
        if kind in keep:
            detail = {k: v for k, v in e.items() if k not in ("t", "kind")}
            say(
                f"  {e['t']:7.3f} {kind:15s} {json.dumps(detail, ensure_ascii=False)[:230]}"
            )
        elif kind == "change":
            key = (e.get("foreground"), e.get("tk_focus"), e.get("os_focus_widget"))
            if key != last:
                last = key
                say(
                    f"  {e['t']:7.3f} {'change':15s} fg={e.get('foreground')} "
                    f"tk_focus={e.get('tk_focus')} os_focus_widget={e.get('os_focus_widget')}"
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["preview", "thumb"], default="preview")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    before = fingerprints()
    namespace = uuid4().hex
    (REPO / ".planning" / "tmp").mkdir(parents=True, exist_ok=True)
    fixture = Path(
        tempfile.mkdtemp(prefix="pagefolio-diag-", dir=REPO / ".planning" / "tmp")
    )
    (fixture / "plugins").mkdir()
    (fixture / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    session = {
        "purpose": "debug preview-focus-not-restored: 入力先の移動を観測する診断 (G1 の合否には使わない)",
        "case": args.case,
        "namespace": namespace,
        "fixture": str(fixture),
        "started_at": now(),
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "tests_dirty_vs_head": bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--", "tests", "pagefolio"],
                cwd=REPO,
                capture_output=True,
                text=True,
            ).stdout.strip()
        ),
        "steps": [],
        "answers": {},
    }
    out_path = OUT / f"diag-{args.case}-{stamp}.json"
    say(f"== 診断 {args.case} を開始します ==")
    owner = None
    try:
        with (
            (fixture / "owner.out").open("w", encoding="utf-8") as out,
            (fixture / "owner.err").open("w", encoding="utf-8") as err,
        ):
            owner = subprocess.Popen(
                [
                    sys.executable,
                    str(OWNER),
                    "--role",
                    "owner",
                    "--fixture",
                    str(fixture),
                    "--namespace",
                    namespace,
                    "--case",
                    args.case,
                ],
                cwd=REPO,
                stdout=out,
                stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        session["owner_pid"] = owner.pid
        deadline = time.monotonic() + 40
        while not (fixture / "ready").exists() and time.monotonic() < deadline:
            if owner.poll() is not None:
                break
            time.sleep(0.05)
        if not (fixture / "ready").exists():
            say("隔離PageFolioを起動できませんでした。担当へ伝えてください。")
            session["outcome"] = "start-failed"
            session["owner_err_tail"] = (fixture / "owner.err").read_text(
                encoding="utf-8", errors="replace"
            )[-1500:]
            return 1
        session["steps"].append(
            {
                "at": now(),
                "step": "prepared",
                "foreground": window_info(user32.GetForegroundWindow()),
            }
        )
        say("")
        say(
            f"隔離PageFolioに操作先({'中央のプレビュー' if args.case == 'preview' else '左ペインのサムネイル欄'})が準備済みです。"
        )
        say("このあと二次起動します。マウスで入力欄などをクリックしないでください。")
        say(
            "(この Enter は PowerShell へ戻って押してください。戻り方はいつもどおりで構いません)"
        )
        input("準備ができたら Enter を押してください。この直後に二次起動します。 > ")
        session["steps"].append(
            {
                "at": now(),
                "step": "peer",
                "foreground": window_info(user32.GetForegroundWindow()),
            }
        )
        peer = subprocess.run(
            [
                sys.executable,
                str(OWNER),
                "--role",
                "peer",
                "--fixture",
                str(fixture),
                "--namespace",
                namespace,
                "--case",
                args.case,
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=40,
        )
        session["peer"] = {
            "returncode": peer.returncode,
            "stdout": peer.stdout[-600:],
            "stderr_tail": peer.stderr[-800:],
        }
        time.sleep(1.5)
        session["steps"].append(
            {
                "at": now(),
                "step": "after-peer",
                "foreground": window_info(user32.GetForegroundWindow()),
            }
        )
        say("")
        say(
            "二次起動を実行しました。PageFolioは前面に出ましたか? まだ何も触らないでください。"
        )
        session["answers"]["foreground"] = input("「出た」「出ない」 > ").strip()
        say("")
        say("Enter を押す前、PageFolio から PowerShell へはどうやって戻りましたか?")
        session["answers"]["switch_method"] = input(
            "例: 「PowerShellのウィンドウをクリック」「Alt+Tab」「タスクバーをクリック」「その他(一言)」 > "
        ).strip()
        say("")
        say(
            "Enter を押す前に、PageFolio の画面の中で、キー・マウス・ホイールの操作を何かしましたか?"
        )
        session["answers"]["extra_ops"] = input(
            "例: 「していない」「Tabを押した」「クリックした(どこ)」「ホイールを回した」 > "
        ).strip()
        session["outcome"] = "answered"
    finally:
        (fixture / "stop").touch()
        if owner is not None:
            try:
                owner.wait(timeout=15)
            except subprocess.TimeoutExpired:
                # この診断が起動した owner だけを終了する (他の process には触れない)。
                owner.kill()
                owner.wait(timeout=10)
                session["owner_killed"] = True
            session["owner_returncode"] = owner.returncode
        for name, key in (
            ("focus-result.json", "focus_result"),
            ("focus-trace.json", "focus_trace"),
        ):
            path = fixture / name
            if path.exists() and path.stat().st_size:
                session[key] = json.loads(path.read_text(encoding="utf-8"))
        session["owner_err_tail"] = (
            (fixture / "owner.err").read_text(encoding="utf-8", errors="replace")[-800:]
            if (fixture / "owner.err").exists()
            else ""
        )
        hwnds = {
            e.get("foreground")
            for e in (session.get("focus_trace") or [])
            if e.get("foreground")
        }
        session["foreground_windows"] = {str(h): window_info(h) for h in sorted(hwnds)}
        session["originals_unchanged"] = fingerprints() == before
        session["finished_at"] = now()
        out_path.write_text(
            json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        shutil.rmtree(fixture, ignore_errors=True)
    summarize(session.get("focus_result"), session.get("focus_trace"))
    say("")
    say(f"診断結果を保存しました: {out_path}")
    say("このファイルのパスを担当へ伝えてください (中身を貼り付ける必要はありません)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
