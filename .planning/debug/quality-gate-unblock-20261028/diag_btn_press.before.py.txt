# ruff: noqa
"""決定的再現 (debug: preview-focus-not-restored, 分岐 A の機構検証)。

「Enter を押す前に PageFolio の右ペイン (ファイルを開く = btn_open) を押した/Tab を押した」だけで、
原失敗の署名 (immediate_focus=None / settled_focus=btn_open) が出るかを、本番の起動経路
(diag_owner.py -> pagefolio.py -> __main__.main -> StartupCoordinator/FocusRestorer) のまま、
実OSのマウス/キー入力 (mouse_event / keybd_event) で再現する。製品と tests/ と diag_owner.py は変更しない。

流れ (controller):
  1. owner (本ファイルの --role owner。diag_owner.prepare を呼んだ上で btn_open の座標を書き出す) を起動
  2. PageFolio を前面化 (preview_canvas に入力先がある状態)
  3. 介入 (--intervene) を実OS入力で与える
  4. 前景 decoy 窓 (PowerShell 相当) を出し、その子孫として peer (二次起動) を実行 = 本物の非アクティブ化→復帰
  5. focus-result.json / focus-trace.json を回収して保存

--intervene:
  none                    対照 (介入なし)
  hover                   ポインタを btn_open 上へ置くだけ (押さない)
  press-release-outside   btn_open 上でボタンを押し、外へ移動してから離す (ttk Button は invoke しない)
  tab                     キーボードの Tab を 1 回 (preview_canvas からの既定の入力先移動)

usage (リポジトリ直下で):
  .venv\\Scripts\\python.exe .planning\\debug\\preview-focus-not-restored-evidence\\diag_btn_press.py --intervene press-release-outside
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


# ---------------------------------------------------------------- owner side
def owner_main():
    """diag_owner.prepare に btn_open 座標の書き出しを足して diag_owner.main へ委譲する。"""
    sys.path.insert(0, str(HERE))
    import diag_owner

    original_prepare = diag_owner.prepare

    def find_open_button(app):
        pending = [app.root]
        while pending:
            w = pending.pop()
            pending.extend(w.winfo_children())
            if w.winfo_class() == "TButton" and str(w.cget("text")) == app._t(
                "btn_open"
            ):
                return w
        return None

    def prepare(app, fixture, case):
        original_prepare(app, fixture, case)
        root = app.root
        invoked = []

        def install_invoke_probe():
            b = find_open_button(app)
            if b is None:
                root.after(100, install_invoke_probe)
                return

            def probe_command():
                invoked.append(time.monotonic())
                (fixture / "btn_open_invoked").write_text(
                    str(len(invoked)), encoding="utf-8"
                )

            b.configure(command=probe_command)

        root.after(100, install_invoke_probe)
        beats = []

        def heartbeat():
            beats.append(round(time.monotonic(), 2))
            (fixture / "heartbeat.txt").write_text(
                " ".join(map(str, beats[-40:])), encoding="utf-8"
            )
            root.after(500, heartbeat)

        root.after(500, heartbeat)

        def poll():
            if (fixture / "do-synthetic").exists():
                (fixture / "do-synthetic").unlink()
                b = find_open_button(app)
                b.event_generate("<Enter>")
                b.event_generate("<ButtonPress-1>", x=10, y=10)
                root.update()
                # 押したまま外へ出て離す (ttk Button は !active なので invoke しない)
                # 実マウスの Leave は Button1 押下中の修飾 (state=0x100) を持つ → <B1-Leave> で !pressed
                b.event_generate("<Leave>", state=0x100)
                b.event_generate("<ButtonRelease-1>", x=-200, y=-200)
                root.update()
                (fixture / "synthetic-done").write_text("1", encoding="utf-8")
            if (fixture / "geom-request").exists():
                (fixture / "geom-request").unlink()
                root.update_idletasks()
                b = find_open_button(app)
                canvas = app.preview_canvas
                data = {
                    "btn_open": str(b),
                    "btn_rect": [
                        b.winfo_rootx(),
                        b.winfo_rooty(),
                        b.winfo_width(),
                        b.winfo_height(),
                    ],
                    "btn_mapped": bool(b.winfo_ismapped()),
                    "btn_takefocus": str(b.cget("takefocus")),
                    "canvas_rect": [
                        canvas.winfo_rootx(),
                        canvas.winfo_rooty(),
                        canvas.winfo_width(),
                        canvas.winfo_height(),
                    ],
                    "under_cursor": str(
                        root.winfo_containing(
                            root.winfo_pointerx(), root.winfo_pointery()
                        )
                    ),
                    "pointer": [root.winfo_pointerx(), root.winfo_pointery()],
                    "top_hwnd": app._startup_focus.backend._top_level_hwnd(root),
                    "tk_focus_next_of_preview": str(canvas.tk_focusNext()),
                }
                # Tab 経路の予測 (入力先は変えない問い合わせ)
                (fixture / "geometry.json").write_text(
                    json.dumps(data), encoding="utf-8"
                )
            root.after(50, poll)

        root.after(50, poll)

    diag_owner.prepare = prepare
    diag_owner.main()


# ------------------------------------------------------------ controller side
u = ctypes.windll.user32
u.GetForegroundWindow.restype = ctypes.c_void_p
u.GetAncestor.restype = ctypes.c_void_p
u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u.WindowFromPoint.restype = ctypes.c_void_p
u.WindowFromPoint.argtypes = [wt.POINT]
u.SetForegroundWindow.argtypes = [ctypes.c_void_p]
u.FindWindowW.restype = ctypes.c_void_p
u.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
GA_ROOT = 2
u.GetWindowTextW.argtypes = [ctypes.c_void_p, wt.LPWSTR, ctypes.c_int]
u.GetClassNameW.argtypes = [ctypes.c_void_p, wt.LPWSTR, ctypes.c_int]


def now():
    return datetime.now(timezone.utc).isoformat()


def window_title(hwnd):
    if not hwnd:
        return None
    buf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(ctypes.c_void_p(hwnd), buf, 256)
    cls = ctypes.create_unicode_buffer(128)
    u.GetClassNameW(ctypes.c_void_p(hwnd), cls, 128)
    return {"hwnd": int(hwnd), "title": buf.value, "class": cls.value}


def alt_tap():
    u.keybd_event(0x12, 0, 0, 0)
    u.keybd_event(0x12, 0, 2, 0)


def root_at(x, y):
    h = u.WindowFromPoint(wt.POINT(int(x), int(y)))
    return u.GetAncestor(h, GA_ROOT) if h else None


def click_down():
    u.mouse_event(0x0002, 0, 0, 0, 0)


def click_up():
    u.mouse_event(0x0004, 0, 0, 0, 0)


def key_tap(vk):
    u.keybd_event(vk, 0, 0, 0)
    time.sleep(0.03)
    u.keybd_event(vk, 0, 2, 0)


DECOY = r"""
import ctypes, subprocess, sys, tkinter as tk, json
py, owner, fixture, ns, out = sys.argv[1:6]
import time as _tt
def LOG(m):
    with open(out + '.log', 'a', encoding='utf-8') as f:
        f.write(f'{_tt.monotonic():.2f} {m}' + chr(10))
LOG('decoy-start')
import faulthandler
_fh = open(out + '.fault', 'w')
faulthandler.dump_traceback_later(15, file=_fh, exit=False)
r = tk.Tk(); r.title('decoy'); r.geometry('300x200+60+60'); r.update()
u = ctypes.windll.user32
u.GetAncestor.restype = ctypes.c_void_p; u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u.SetForegroundWindow.argtypes = [ctypes.c_void_p]
h = u.GetAncestor(r.winfo_id(), 2)
u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0)
u.SetForegroundWindow(h)
LOG('decoy-fg-set')
def go():
    LOG('go-start')
    import time as _t
    o = open(out + '.peer.out', 'w', encoding='utf-8'); e = open(out + '.peer.err', 'w', encoding='utf-8')
    t0 = _t.monotonic()
    LOG('peer-popen')
    p = subprocess.Popen([py, owner, '--role', 'peer', '--fixture', fixture, '--namespace', ns, '--case', 'preview'], stdout=o, stderr=e)
    state = 'timeout'
    while _t.monotonic() - t0 < 30:
        if p.poll() is not None:
            state = 'exited'
            break
        r.update()
        _t.sleep(0.05)
    LOG('peer-' + state)
    if state == 'timeout':
        p.kill()
    o.close(); e.close()
    open(out, 'w', encoding='utf-8').write(json.dumps({'state': state, 'rc': p.returncode, 'elapsed': round(_t.monotonic() - t0, 2), 'out': open(out + '.peer.out', encoding='utf-8', errors='replace').read()[-400:], 'err': open(out + '.peer.err', encoding='utf-8', errors='replace').read()[-600:]}))
    r.destroy()
import time as _t2
_t0 = _t2.monotonic()
_n = 0
while _t2.monotonic() - _t0 < 3:
    r.update()
    _n += 1
    _t2.sleep(0.05)
LOG('pumped-%d' % _n)
go()
"""


def run_one(intervene, out_dir, deactivate="decoy"):
    scratch = REPO / ".planning" / "tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="pagefolio-btnpress-", dir=scratch))
    (fixture / "plugins").mkdir()
    (fixture / "pagefolio_settings.json").write_text(
        '{"lang":"ja","ocr_provider":"off"}', encoding="utf-8"
    )
    ns = uuid4().hex
    py = sys.executable
    session = {
        "purpose": "debug preview-focus-not-restored: 分岐A機構の決定的再現 (G1 の合否には使わない)",
        "intervene": intervene,
        "started_at": now(),
        "namespace": ns,
        "steps": [],
    }
    point = wt.POINT()
    u.GetCursorPos(ctypes.byref(point))
    saved_cursor = (point.x, point.y)
    prev_fg = u.GetForegroundWindow()
    session["deactivate"] = deactivate
    session["prev_foreground"] = window_title(prev_fg)
    owner = None
    try:
        with (
            (fixture / "o.out").open("w", encoding="utf-8") as out,
            (fixture / "o.err").open("w", encoding="utf-8") as err,
        ):
            owner = subprocess.Popen(
                [
                    py,
                    str(HERE / "diag_btn_press.py"),
                    "--role",
                    "owner",
                    "--fixture",
                    str(fixture),
                    "--namespace",
                    ns,
                    "--case",
                    "preview",
                ],
                cwd=REPO,
                stdout=out,
                stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        dl = time.monotonic() + 40
        while not (fixture / "ready").exists() and time.monotonic() < dl:
            if owner.poll() is not None:
                break
            time.sleep(0.05)
        if not (fixture / "ready").exists():
            session["outcome"] = "start-failed"
            session["owner_err_tail"] = (fixture / "o.err").read_text(
                encoding="utf-8", errors="replace"
            )[-1500:]
            return session
        pf = u.FindWindowW("TkTopLevel", "PageFolio")
        ok = False
        for attempt in range(1, 7):
            alt_tap()
            u.SetForegroundWindow(pf)
            time.sleep(1.0)
            ok = u.GetForegroundWindow() == pf
            session["steps"].append(
                {
                    "at": now(),
                    "step": "pf-foreground",
                    "attempt": attempt,
                    "ok": ok,
                    "foreground": window_title(u.GetForegroundWindow()),
                }
            )
            if ok:
                break
        def get_geom():
            g = fixture / "geometry.json"
            if g.exists():
                g.unlink()
            (fixture / "geom-request").touch()
            for _ in range(60):
                if g.exists():
                    try:
                        return json.loads(g.read_text(encoding="utf-8"))
                    except ValueError:
                        pass
                time.sleep(0.05)
            return None

        geom = get_geom()
        for attempt in range(1, 8):
            if intervene not in ("hover", "press-release-outside"):
                break
            bx, by, bw, bh = geom["btn_rect"]
            u.SetCursorPos(bx + bw // 2, by + bh // 2)
            time.sleep(0.4)
            geom = get_geom()
            session.setdefault("aim", []).append(
                {
                    "attempt": attempt,
                    "btn_rect": geom["btn_rect"],
                    "under_cursor": geom["under_cursor"],
                    "pointer": geom["pointer"],
                }
            )
            if geom["under_cursor"] == geom["btn_open"]:
                break
        session["geometry"] = geom
        bx, by, bw, bh = geom["btn_rect"]
        cx, cy = bx + bw // 2, by + bh // 2
        cax, cay, caw, cah = geom["canvas_rect"]
        ox, oy = cax + caw // 2, cay + cah // 2
        aimed = geom["under_cursor"] == geom["btn_open"]
        session["aimed_at_btn_open"] = aimed
        # 安全確認: 押す座標・離す座標が PageFolio 自身の上にあること (他アプリを押さない)
        safe = u.GetForegroundWindow() == pf and (
            intervene in ("none", "tab", "synthetic-press-release-outside")
            or (aimed and root_at(cx, cy) == pf and root_at(ox, oy) == pf)
        )
        session["safe_to_input"] = bool(safe)
        if not safe:
            session["outcome"] = "aborted-unsafe"
            return session
        if intervene == "hover":
            u.SetCursorPos(cx, cy)
            time.sleep(0.8)
        elif intervene == "press-release-outside":
            u.SetCursorPos(cx, cy)
            time.sleep(0.5)
            click_down()
            time.sleep(0.4)
            u.SetCursorPos(ox, oy)
            time.sleep(0.4)
            click_up()
            time.sleep(0.6)
        elif intervene == "tab":
            key_tap(0x09)
            time.sleep(0.6)
        elif intervene == "synthetic-press-release-outside":
            (fixture / "do-synthetic").touch()
            for _ in range(60):
                if (fixture / "synthetic-done").exists():
                    break
                time.sleep(0.05)
            session["synthetic_done"] = (fixture / "synthetic-done").exists()
            time.sleep(0.6)
        session["steps"].append({"at": now(), "step": f"intervened:{intervene}"})
        if deactivate == "prev":
            # 既存の前景窓 (開始時の前景=端末) へ前景を戻し、その配下の制御プロセスから peer を実行
            # (実 UAT で PowerShell が前景のまま peer を起動する流れに相当。新規窓を作らない)
            for attempt in range(1, 6):
                alt_tap()
                u.SetForegroundWindow(prev_fg)
                time.sleep(0.8)
                if u.GetForegroundWindow() == prev_fg:
                    break
            session["prev_foreground_ok"] = u.GetForegroundWindow() == prev_fg
            t0 = time.monotonic()
            try:
                pr = subprocess.run(
                    [
                        py,
                        str(HERE / "diag_owner.py"),
                        "--role",
                        "peer",
                        "--fixture",
                        str(fixture),
                        "--namespace",
                        ns,
                        "--case",
                        "preview",
                    ],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                )
                session["peer"] = {
                    "state": "exited",
                    "rc": pr.returncode,
                    "out": pr.stdout[-400:],
                    "err": pr.stderr[-600:],
                    "elapsed": round(time.monotonic() - t0, 2),
                }
            except subprocess.TimeoutExpired:
                session["peer"] = {"state": "timeout"}
            session["btn_open_invoked"] = (fixture / "btn_open_invoked").exists()
            time.sleep(1.2)
            session["outcome"] = "done"
            return session
        # 本物の非アクティブ化→復帰: 前景 decoy (PowerShell 相当) の子孫として peer を実行
        try:
            d = subprocess.run(
                [
                    py,
                    "-c",
                    DECOY,
                    py,
                    str(HERE / "diag_owner.py"),
                    str(fixture),
                    ns,
                    str(fixture / "decoy.json"),
                ],
                capture_output=True,
                text=True,
                timeout=100,
            )
            session["decoy_rc"] = d.returncode
            session["decoy_stderr"] = d.stderr[-300:]
        except subprocess.TimeoutExpired as exc:
            session["decoy_timeout"] = True
            session["decoy_exc_stderr"] = (exc.stderr or b"")[-600:].decode(
                "utf-8", "replace"
            ) if isinstance(exc.stderr, bytes) else str(exc.stderr)[-600:]
        fault = fixture / "decoy.json.fault"
        session["decoy_fault"] = (
            fault.read_text(encoding="utf-8", errors="replace")[-1500:]
            if fault.exists()
            else None
        )
        logf = fixture / "decoy.json.log"
        session["decoy_log"] = (
            logf.read_text(encoding="utf-8") if logf.exists() else None
        )
        session["btn_open_invoked"] = (fixture / "btn_open_invoked").exists()
        if (fixture / "decoy.json").exists():
            session["peer"] = json.loads(
                (fixture / "decoy.json").read_text(encoding="utf-8")
            )
        time.sleep(0.8)
        session["outcome"] = "done"
    finally:
        u.SetCursorPos(*saved_cursor)
        (fixture / "stop").touch()
        if owner is not None:
            try:
                owner.wait(timeout=15)
            except subprocess.TimeoutExpired:
                owner.kill()
                owner.wait(timeout=10)
                session["owner_killed"] = True
            session["owner_returncode"] = owner.returncode
        for name, key in (
            ("focus-result.json", "focus_result"),
            ("focus-trace.json", "focus_trace"),
        ):
            p = fixture / name
            if p.exists() and p.stat().st_size:
                session[key] = json.loads(p.read_text(encoding="utf-8"))
        hb = fixture / "heartbeat.txt"
        session["heartbeat_tail"] = (
            hb.read_text(encoding="utf-8")[-200:] if hb.exists() else None
        )
        session["owner_err_tail"] = (
            (fixture / "o.err").read_text(encoding="utf-8", errors="replace")[-600:]
            if (fixture / "o.err").exists()
            else ""
        )
        session["finished_at"] = now()
        import shutil

        shutil.rmtree(fixture, ignore_errors=True)
    return session


def summarize(session):
    print(f"-- intervene={session['intervene']} outcome={session.get('outcome')}")
    fr = session.get("focus_result")
    if fr:
        print(f"   result={fr.get('result')} immediate={fr.get('immediate_focus')}")
        print(f"   settled={fr.get('settled_focus')}  focus_correct={fr.get('focus_correct')}")
    keep = {
        "FocusIn",
        "FocusOut",
        "ButtonPress",
        "ButtonRelease",
        "KeyPress",
        "tcl-focus",
        "restore-before",
        "restore-result",
        "settled",
    }
    for e in session.get("focus_trace") or []:
        if e["kind"] in keep:
            if e["kind"] in ("FocusIn", "FocusOut") and e["args"][0] in (
                ".",
                ".!panedwindow",
                ".!panedwindow.!frame2",
                ".!panedwindow.!frame2.!frame2",
                ".!panedwindow.!frame3",
                ".!panedwindow.!frame3.!canvas",
                ".!panedwindow.!frame3.!canvas.!frame",
                ".!panedwindow.!frame3.!canvas.!frame.!frame2",
            ):
                continue
            detail = {k: v for k, v in e.items() if k not in ("t", "kind")}
            if e["kind"] in ("restore-before", "settled"):
                detail = {
                    k: detail[k]
                    for k in ("tk_focus", "lastfor", "record", "last_widget")
                    if k in detail
                }
            print(f"   {e['t']:7.3f} {e['kind']:14s} {json.dumps(detail, ensure_ascii=False)[:260]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["owner", "controller"], default="controller")
    parser.add_argument(
        "--intervene",
        choices=[
            "none",
            "hover",
            "press-release-outside",
            "tab",
            "synthetic-press-release-outside",
        ],
        default="press-release-outside",
    )
    parser.add_argument("--tag", default="")
    parser.add_argument("--deactivate", choices=["decoy", "prev"], default="decoy")
    args, _ = parser.parse_known_args()
    if args.role == "owner":
        owner_main()
        return 0
    session = run_one(args.intervene, HERE, args.deactivate)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    prefix = f"probe-{args.tag}-" if args.tag else "probe-"
    path = HERE / f"{prefix}{args.intervene}-{stamp}.json"
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    summarize(session)
    print(f"saved: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
