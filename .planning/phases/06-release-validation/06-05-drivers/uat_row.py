# ruff: noqa
"""06-05-02 の1行(ケースID/subrow)を、利用者が自分のPowerShellで実行する人手受入driver。

対象: G1 = W01 / W02 (Python入口 script|module と 実配布EXE)。
Python入口は既存harness(tests/test_startup_windows.py --uat)、実EXEは tests/release_uat_support.py の
隔離copy(prepare/start/peer/inspect/stop)を使う。製品は import/patch せず、EXEへ試験引数を渡さない。

usage (リポジトリ直下で):
  .venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-drivers/uat_row.py --row W01/normal@script
  ... --row W01/zoomed@script
  ... --row W01/normal@production-exe
  ... --row W01/normal@script --selftest      (機構確認用。canned回答。証拠にしない。
                                                隔離PageFolioを実際に起動して前面化する)
  ... --check-monitor                         (入力監視ロジックの機構確認。窓も入力も作らず
                                                前景も変えない。偽サンプラ+読み取り専用APIの短いポーリングのみ)

利用者の入力はすべて逐語で session JSON の raw_inputs に保存する(貼り付けを疑う入力は一度拒否して取り直し、
拒否した入力も保存する)。回答はキーボードで短く入力する。右クリック貼り付け/Ctrl+Vは使わない。
session JSON は 06-05-evidence/ に保存し、selftest は 06-05-evidence/selftest/ に分ける。

手順汚染の検出(debug: preview-focus-not-restored で追加):
Python入口の行は、隔離PageFolioの起動から二次起動(peer)の完了までの間、マウスのボタン押下エッジ
(押下時刻・ポインタ位置・押下先の窓・前景窓)と前景窓の切替、PageFolioが前面にある間のキー押下(キー番号のみ)を
読み取り専用のポーリングで記録する。PageFolio上にボタン押下があれば、その行は「手順汚染(再走が必要)」として
session JSON の procedure_verdict / focus_attribution に明示し、focus_correct=false を製品失敗とみなさない。
(ttk Button は押下だけで入力先を取るため、PageFolio内の1回の押下で復帰先の記憶が変わる。製品の復帰は記憶どおり。)
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from tests import release_uat_support as S  # noqa: E402

PHASE = REPO / ".planning/phases/06-release-validation"
EVIDENCE = PHASE / "06-05-evidence"
BUILD = S.read_json(PHASE / "06-BUILD-EVIDENCE.json")
FINAL = Path(BUILD["final_release"]["final_dir"])
EXE_SHA = BUILD["final_release"]["exe_sha256"]
GUARD = "PASTE-GUARD-do-not-paste"
HARNESS = [sys.executable, str(REPO / "tests" / "test_startup_windows.py"), "--uat"]


def now():
    return datetime.now(timezone.utc).isoformat()


def say(text=""):
    print(text, flush=True)


# ---------------------------------------------------------------------------
# 外部観測(window状態・foreground・process)
# ---------------------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [WNDENUM, wt.LPARAM]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.IsIconic.argtypes = [wt.HWND]
user32.IsZoomed.argtypes = [wt.HWND]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]


def top_windows(pids):
    """指定PIDが所有するトップレベルwindowの状態を外部から読む(state/rect/visible/iconic/zoomed)。"""
    pids = set(pids)
    found = []

    def callback(hwnd, _):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value in pids:
            title = ctypes.create_unicode_buffer(256)
            cls = ctypes.create_unicode_buffer(128)
            user32.GetWindowTextW(hwnd, title, 256)
            user32.GetClassNameW(hwnd, cls, 128)
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append(
                {
                    "hwnd": int(hwnd or 0),
                    "pid": owner.value,
                    "title": title.value,
                    "class": cls.value,
                    "visible": bool(user32.IsWindowVisible(hwnd)),
                    "iconic": bool(user32.IsIconic(hwnd)),
                    "zoomed": bool(user32.IsZoomed(hwnd)),
                    "rect": [rect.left, rect.top, rect.right, rect.bottom],
                }
            )
        return True

    user32.EnumWindows(WNDENUM(callback), 0)
    return found


def main_windows(pids):
    """タイトルが空でない可視/最小化のtop-level(通常はPageFolio本体と所有ダイアログ)。"""
    return [
        w for w in top_windows(pids) if w["title"] and (w["visible"] or w["iconic"])
    ]


def pids_with_marker(marker):
    """コマンドラインに marker を含むprocess(隔離harnessが起動した子孫)のPIDと生成時刻。"""
    script = (
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*"
        + marker.replace("'", "''")
        + "*' } | ForEach-Object { '{0} {1}' -f $_.ProcessId, $_.ProcessId }"
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    ).stdout
    pids = []
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            pids.append(int(parts[0]))
    return sorted(set(pids))


def alive_identities(pids):
    result = []
    for pid in pids:
        ident = S.process_identity(pid)
        if ident and ident["alive"]:
            result.append({"pid": pid, **{k: ident[k] for k in ("created", "image")}})
    return result


# ---------------------------------------------------------------------------
# 手順汚染の検出(読み取り専用の入力監視)
# ---------------------------------------------------------------------------
# 背景(debug: preview-focus-not-restored): ttk Button は ButtonPress だけで ttk::clickToFocus により
# Tk の入力先を取る。prepared〜peer の間に PageFolio 内を1回押すだけで、復帰先の記憶が preview_canvas
# から btn_open へ変わり、二次起動の復帰は記憶どおり btn_open へ戻る(製品は仕様どおりで欠陥ではない)。
# 利用者の自己申告ではこの押下を拾えない(実測済み)ため、外部から押下エッジを記録して、手順汚染を
# 製品失敗と区別する。
#
# 使うWin32 APIは読み取りだけ(GetAsyncKeyState / GetCursorPos / WindowFromPoint / GetAncestor /
# GetForegroundWindow / GetWindowText 等)。SendInput・SetCursorPos・SetForegroundWindow など、
# 入力や前景を変える呼出しは一切しない。
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.GetAncestor.restype = wt.HWND
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wt.HWND

# GetAsyncKeyState は論理ではなく物理ボタンの状態を返す(左右入替設定でも物理側)。
# どのボタンでもPageFolio上なら汚染とみなすため3つとも見る。
MOUSE_VKS = {0x01: "left", 0x02: "right", 0x04: "middle"}
# 入力先を変えないキー(修飾・ロック)は除く。0x01-0x07 はマウス/未定義なので 0x08 から。
_MODIFIER_VKS = {
    0x10,  # SHIFT
    0x11,  # CONTROL
    0x12,  # MENU(Alt)
    0x14,  # CAPITAL
    0x5B,  # LWIN
    0x5C,  # RWIN
    0x90,  # NUMLOCK
    0x91,  # SCROLL
    0xA0,
    0xA1,  # L/R SHIFT
    0xA2,
    0xA3,  # L/R CONTROL
    0xA4,
    0xA5,  # L/R MENU
}
_ALT_VKS = (0x12, 0xA4, 0xA5)
KEY_VKS = tuple(vk for vk in range(0x08, 0xFF) if vk not in _MODIFIER_VKS)

# 行の流れ(phase)。Enter 後の peer 完了までは復帰直前の記憶と復帰後の settled_focus に影響しうるため、
# 次の3つのphaseでのPageFolio上の押下を「手順汚染」とする。post-peer 以降(F5観察など)は参考記録のみ。
CONTAMINATING_PHASES = ("start-harness", "awaiting-enter", "peer")
MONITOR_INTERVAL_S = 0.008
MONITOR_MAX_GAP_S = 0.5  # これを超える観測の空きがあれば「清浄」を保証しない
MONITOR_EVENT_CAP = 1000


def describe_hwnd(hwnd):
    """windowの識別情報(hwnd/pid/title/class)。取得に失敗しても例外にしない。"""
    if not hwnd:
        return {"hwnd": 0, "pid": None, "title": "", "class": ""}
    owner = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    title = ctypes.create_unicode_buffer(256)
    cls = ctypes.create_unicode_buffer(128)
    user32.GetWindowTextW(hwnd, title, 256)
    user32.GetClassNameW(hwnd, cls, 128)
    return {
        "hwnd": int(hwnd),
        "pid": owner.value,
        "title": title.value,
        "class": cls.value,
    }


class Win32Sampler:
    """読み取り専用の観測面。入力も前景も変えない。"""

    def buttons(self):
        return {
            name: bool(user32.GetAsyncKeyState(vk) & 0x8000)
            for vk, name in MOUSE_VKS.items()
        }

    def cursor(self):
        point = wt.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return [int(point.x), int(point.y)]

    def window_at(self, pos):
        child = user32.WindowFromPoint(wt.POINT(pos[0], pos[1]))
        root = user32.GetAncestor(child, 2) if child else None  # GA_ROOT
        info = describe_hwnd(root or child)
        info["child_hwnd"] = int(child or 0)
        return info

    def foreground(self):
        return int(user32.GetForegroundWindow() or 0)

    def describe(self, hwnd):
        return describe_hwnd(hwnd)

    def keys_down(self):
        down = {vk for vk in KEY_VKS if user32.GetAsyncKeyState(vk) & 0x8000}
        alt = any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in _ALT_VKS)
        return down, alt


class EdgeTracker:
    """状態列から押下/離上のエッジを取り出す(純関数的。窓にも入力にも触れない)。"""

    def __init__(self):
        self.prev_buttons = None
        self.prev_keys = None

    def feed_buttons(self, buttons):
        """-> [(button, kind)]。kind は down / up / held-at-start。

        最初の観測は基準線。すでに押されていたボタンは held-at-start とし、押下エッジに数えない。
        """
        if self.prev_buttons is None:
            self.prev_buttons = dict(buttons)
            return [(name, "held-at-start") for name, down in buttons.items() if down]
        edges = []
        for name, down in buttons.items():
            was = self.prev_buttons.get(name, False)
            if down and not was:
                edges.append((name, "down"))
            elif was and not down:
                edges.append((name, "up"))
        self.prev_buttons = dict(buttons)
        return edges

    def feed_keys(self, down):
        """-> 新しく押されたVKのリスト。down=None は「いまキーを見ていない」(基準線を捨てる)。

        PageFolioが前面になった瞬間にすでに押されていたキー(Alt+Tab の離し途中など)は基準線として
        扱い、押下エッジに数えない。
        """
        if down is None:
            self.prev_keys = None
            return []
        if self.prev_keys is None:
            self.prev_keys = set(down)
            return []
        new = sorted(set(down) - self.prev_keys)
        self.prev_keys = set(down)
        return new


class InputMonitor:
    """マウスのボタン押下エッジ・前景窓の切替・PageFolio前面中のキー押下を記録する。

    判定(PageFolio上か)は summary() で、起動後に分かる所有PIDを使って事後にまとめて行う。
    """

    def __init__(self, sampler=None, interval=MONITOR_INTERVAL_S, clock=time.monotonic):
        self.sampler = sampler if sampler is not None else Win32Sampler()
        self.interval = interval
        self.clock = clock
        self.tracker = EdgeTracker()
        self.mouse_events = []
        self.fg_transitions = []
        self.key_events = []
        self.errors = []
        self.phase_log = []
        self.samples = 0
        self.max_gap_s = 0.0
        self.truncated = False
        self.started_at = None
        self.stopped_at = None
        self._phase = "init"
        self._owned = frozenset()
        self._t0 = None
        self._last_t = None
        self._fg_hwnd = None
        self._fg_info = {}
        self._seq = 0
        self._stop = threading.Event()
        self._thread = None

    # -- 制御 -----------------------------------------------------------------
    def set_phase(self, phase):
        self._phase = phase
        self.phase_log.append({"t": now(), "phase": phase})

    def set_owned_pids(self, pids):
        self._owned = frozenset(pids)

    def start(self):
        self.started_at = now()
        self.poll_once()  # 基準線(最初の状態)。失敗は errors に残る
        self._thread = threading.Thread(
            target=self._run, name="uat-input-monitor", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        if self.stopped_at is None:
            self.stopped_at = now()

    def _run(self):
        while not self._stop.is_set():
            self.poll_once()
            time.sleep(self.interval)

    # -- 1回の観測 ---------------------------------------------------------------
    def _append(self, items, record):
        if len(items) < MONITOR_EVENT_CAP:
            items.append(record)
        else:
            self.truncated = True

    def _stamp(self, t):
        self._seq += 1
        return {
            "seq": self._seq,
            "t": now(),
            "elapsed_s": round(t - self._t0, 3),
            "phase": self._phase,
        }

    def poll_once(self):
        s = self.sampler
        try:
            t = self.clock()
            if self._t0 is None:
                self._t0 = t
            if self._last_t is not None:
                self.max_gap_s = max(self.max_gap_s, t - self._last_t)
            self._last_t = t
            self.samples += 1
            for name, kind in self.tracker.feed_buttons(s.buttons()):
                pos = s.cursor()
                record = {
                    **self._stamp(t),
                    "kind": kind,
                    "button": name,
                    "pos": pos,
                    "under": s.window_at(pos),
                    "foreground": self._fg_info,
                }
                self._append(self.mouse_events, record)
            fg = s.foreground()
            if fg != self._fg_hwnd:
                info = s.describe(fg)
                if self._fg_hwnd is not None:  # 最初の観測は遷移に数えない
                    self._append(
                        self.fg_transitions,
                        {**self._stamp(t), "from": self._fg_info, "to": info},
                    )
                self._fg_hwnd, self._fg_info = fg, info
            if self._fg_info.get("pid") in self._owned:
                down, alt = s.keys_down()
                new = self.tracker.feed_keys(down)
                if not alt:  # Alt+Tab などのシステムショートカットは入力先を変えない
                    for vk in new:
                        self._append(
                            self.key_events,
                            {**self._stamp(t), "vk": vk, "foreground": self._fg_info},
                        )
            else:
                self.tracker.feed_keys(None)
        except Exception as error:
            if len(self.errors) < 20:
                self.errors.append(repr(error))

    # -- 結果 ------------------------------------------------------------------
    def summary(self):
        owned = set(self._owned)

        def marked(events):
            out = []
            for event in list(events):
                item = dict(event)
                pid = (item.get("under") or item.get("foreground") or {}).get("pid")
                item["on_pagefolio"] = pid in owned
                out.append(item)
            return out

        return {
            "enabled": True,
            "method": "read-only polling: GetAsyncKeyState/GetCursorPos/WindowFromPoint/"
            "GetAncestor/GetForegroundWindow (no SendInput/SetCursorPos/SetForegroundWindow)",
            "interval_s": self.interval,
            "samples": self.samples,
            "max_gap_s": round(self.max_gap_s, 3),
            "errors": list(self.errors),
            "truncated": self.truncated,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "owned_pids": sorted(owned),
            "contaminating_phases": list(CONTAMINATING_PHASES),
            "phase_log": list(self.phase_log),
            "mouse_events": marked(self.mouse_events),
            "foreground_transitions": list(self.fg_transitions),
            "key_events": marked(self.key_events),
        }


def assess_procedure(summary, focus_result):
    """監視結果と focus-result から、手順の汚染有無と focus_correct の帰属を決める(純関数)。

    procedure_verdict:
      contaminated       PageFolio上にボタン押下がある(再走が必要。製品失敗ではない)
      monitor-incomplete 監視に error/観測の空き/打切りがあり、清浄を保証できない
      keys-suspect       PageFolio前面中にキー押下がある(Tab等で入力先が動きうる)
      clean              上のどれでもない
      not-monitored      入力監視をしていない行(実EXE行など)
    focus_attribution は focus_correct を製品の合否として読んでよいかを別に持つ:
      product-focus-ok / product-focus-failure-candidate は clean のときだけ。
    """
    if not summary or not summary.get("enabled"):
        return {
            "procedure_verdict": "not-monitored",
            "rerun_required": False,
            "reason": "この行では入力監視をしていない",
            "pagefolio_presses_before_peer_done": [],
            "pagefolio_keys_before_peer_done": [],
            "focus_attribution": "not-judged-not-monitored",
        }
    phases = set(summary.get("contaminating_phases") or CONTAMINATING_PHASES)
    presses = [
        e
        for e in summary.get("mouse_events", [])
        if e.get("kind") == "down"
        and e.get("on_pagefolio")
        and e.get("phase") in phases
    ]
    keys = [e for e in summary.get("key_events", []) if e.get("phase") in phases]
    if presses:
        verdict = "contaminated"
        reason = (
            f"peer完了までの間にPageFolio上でマウスのボタン押下を{len(presses)}回検出"
            "(手順汚染。製品失敗と区別して再走する)"
        )
    elif (
        summary.get("errors")
        or summary.get("samples", 0) <= 0
        or summary.get("truncated")
        or summary.get("max_gap_s", 0) > MONITOR_MAX_GAP_S
    ):
        verdict = "monitor-incomplete"
        reason = (
            f"監視に抜けがあり清浄を保証できない(errors={len(summary.get('errors', []))}・"
            f"samples={summary.get('samples')}・max_gap_s={summary.get('max_gap_s')}・"
            f"truncated={summary.get('truncated')})"
        )
    elif keys:
        verdict = "keys-suspect"
        reason = (
            f"PageFolioが前面の間にキー押下を{len(keys)}回検出"
            "(Tab/Space等は入力先を動かしうるため判定に使わない)"
        )
    else:
        verdict = "clean"
        reason = "peer完了までの間にPageFolio上のボタン押下・キー押下は検出されなかった"
    fc = (focus_result or {}).get("focus_correct")
    if verdict != "clean":
        attribution = f"not-judged-{verdict}"
    elif fc is True:
        attribution = "product-focus-ok"
    elif fc is False:
        attribution = "product-focus-failure-candidate"
    else:
        attribution = "no-focus-result"
    return {
        "procedure_verdict": verdict,
        "rerun_required": verdict != "clean",
        "reason": reason,
        "pagefolio_presses_before_peer_done": presses,
        "pagefolio_keys_before_peer_done": keys,
        "focus_correct_as_recorded": fc,
        "focus_attribution": attribution,
    }


# ---------------------------------------------------------------------------
# 入力(貼り付け対策・逐語保存)
# ---------------------------------------------------------------------------
class Prompter:
    def __init__(self, selftest, canned=None):
        self.selftest = selftest
        self.canned = list(canned or [])
        self.inputs = []
        self.shown = {GUARD}

    def show(self, text):
        say(text)
        # 画面に出した行そのもの(パス等)を貼り付けた入力は拒否対象にする
        for token in re.findall(r"[A-Za-z]:\\[^\s]+|\S{12,}", text):
            self.shown.add(token.strip())

    def set_guard_clipboard(self):
        if self.selftest:
            return
        try:
            subprocess.run(
                ["clip"], input=GUARD.encode("ascii"), check=False, timeout=10
            )
        except Exception as error:
            say(f"(クリップボードの無害化に失敗: {error!r})")

    def enter(self, message):
        """確認用のEnter待ち。入力内容は見ない(誤貼り付けがあっても観測に使わない)。"""
        self.show(message)
        if self.selftest:
            self.inputs.append(
                {"at": now(), "key": "enter", "text": "", "selftest": True}
            )
            return
        text = input("Enterキーを押してください > ")
        self.inputs.append(
            {"at": now(), "key": "enter", "text": text, "role": "continue"}
        )

    def ask(self, key, question, choices=None):
        self.show(question)
        self.set_guard_clipboard()
        for attempt in (1, 2):
            if self.selftest:
                text = self.canned.pop(0) if self.canned else "(selftest)"
            else:
                text = input("> ")
            clean = text.strip()
            reason = None
            if not clean:
                reason = "empty"
            elif clean in self.shown or clean == GUARD:
                reason = "equals-on-screen-text"
            elif len(clean) > 80 or "\n" in text or "\r" in text:
                reason = "too-long-or-multiline"
            record = {
                "at": now(),
                "key": key,
                "attempt": attempt,
                "text": text,
                "rejected": reason,
            }
            self.inputs.append(record)
            if reason is None:
                return clean
            if attempt == 1:
                say(
                    "入力が空か、画面の文字・貼り付けと思われます。キーボードで短く入力し直してください。"
                )
                self.set_guard_clipboard()
        record["accepted_after_rejection"] = True
        return clean


def parse_json_line(text):
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError("JSONが出力に見つかりません: " + text[-300:])


def harness(*args, timeout=90):
    done = subprocess.run(
        [*HARNESS, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    return {
        "argv": list(args),
        "returncode": done.returncode,
        "stdout_tail": done.stdout[-1500:],
        "stderr_tail": done.stderr[-1500:],
        "json": parse_json_line(done.stdout) if done.returncode == 0 else None,
    }


# ---------------------------------------------------------------------------
# 行定義(G1: W01 / W02)
# ---------------------------------------------------------------------------
W02_TARGETS = {
    "settings": "設定ダイアログの入力欄",
    "thumb": "左ペインのサムネイル欄",
    "preview": "中央のプレビュー",
}


class Row:
    def __init__(self, spec, selftest, sampler=None):
        match = re.fullmatch(r"(W0[12])/([a-z]+)@(script|module|production-exe)", spec)
        if not match:
            raise SystemExit(f"未対応の行です(G1のW01/W02のみ): {spec}")
        self.case, self.cond, self.entry = match.groups()
        if (self.case, self.cond) not in (
            ("W01", "normal"),
            ("W01", "zoomed"),
            ("W02", "settings"),
            ("W02", "thumb"),
            ("W02", "preview"),
        ):
            raise SystemExit(f"未対応の条件です: {spec}")
        self.spec = spec
        self.selftest = selftest
        self.sampler = (
            sampler  # None なら実Win32(読み取り専用)。機構確認で偽サンプラを注入する
        )
        self.monitor = None
        self.started = now()
        self.session = {
            "row": spec,
            "case": self.case,
            "condition": self.cond,
            "entry": self.entry,
            "selftest": selftest,
            "started_at": self.started,
            "target_exe_sha256": EXE_SHA,
            "steps": [],
        }
        if self.case == "W01":
            canned = [
                "通常" if self.cond != "zoomed" else "最大化",
                "同じ" if self.entry == "production-exe" else "はい",
                "1つ",
                "見える",
            ]
        elif self.cond == "settings":
            canned = ["出た", "入った", "保たれた", "1つ"]
        else:
            canned = ["出た", "変わった", "戻った", "保たれた", "1つ"]
        self.prompter = Prompter(selftest, canned=[*canned, "なし"])

    def step(self, name, **fields):
        self.session["steps"].append({"at": now(), "step": name, **fields})

    # -- 質問 ---------------------------------------------------------------
    def questions(self, exe):
        p = self.prompter
        a = {}
        label = f"{self.case} {self.cond} {self.entry}"
        say("")
        say(f"== {label} の結果を、キーボードで短く答えてください ==")
        if self.case == "W01":
            want = "通常" if self.cond == "normal" else "最大化"
            a["state_after"] = p.ask(
                "state_after",
                f"1/4 PageFolioの画面は今どの状態ですか? 「通常」「最大化」「最小化」のどれかを入力(期待: {want})",
            )
            if exe:
                a["geometry"] = p.ask(
                    "geometry",
                    "2/4 最小化する前と同じ位置・大きさに戻りましたか? 「同じ」「違う」「分からない」",
                )
            else:
                a["geometry"] = p.ask(
                    "geometry",
                    "2/4 画面は欠けず見やすい位置・大きさで出ていますか? 「はい」「いいえ」",
                )
            a["single"] = p.ask(
                "single", "3/4 PageFolioの画面は1つだけですか? 「1つ」「複数」"
            )
            a["status"] = p.ask(
                "status",
                "4/4 画面上部(ヘッダー)のステータス表示は見えますか? 「見える」「見えない」",
            )
        elif self.cond == "settings":
            target = W02_TARGETS[self.cond]
            a["foreground"] = p.ask(
                "foreground",
                "1/4 二次起動のあと、PageFolioの画面は前面に出ましたか? 「出た」「出ない」",
            )
            a["input"] = p.ask(
                "input",
                f"2/4 {target}に、キーボードで1文字(例: x)を押しました。元の入力先に入りましたか?"
                " 「入った」「入らない」「押していない」(押さなかった場合は理由を一言)",
            )
            a["kept"] = p.ask(
                "kept",
                "3/4 入力済みの文字・選択・カーソルは保たれていましたか?"
                " 「保たれた」「変わった」「分からない」",
            )
            a["single"] = p.ask(
                "single", "4/4 PageFolioの画面は1つだけですか? 「1つ」「複数」"
            )
        else:
            # thumb / preview: これらのCanvasは文字キーを受けないため、x ではなく
            # 製品の既定ショートカット F5(閲覧/編集モード切替)で「キー入力がPageFolioに届いたか」を見る。
            # 入力先がCanvasのままだったことは自動harnessのfocus-result(focus_correct/settled_focus)が証拠。
            target = W02_TARGETS[self.cond]
            a["foreground"] = p.ask(
                "foreground",
                "1/5 二次起動のあと、PageFolioの画面は前面に出ましたか? 「出た」「出ない」",
            )
            a["key_reached"] = p.ask(
                "key_reached",
                "2/5 F5を1回押したとき、ヘッダーのモード表示ボタンの文字(閲覧モード/編集モード)は変わりましたか?"
                " 「変わった」「変わらない」「押していない」(押さなかった場合は理由を一言)",
            )
            a["restored"] = p.ask(
                "restored",
                "3/5 F5をもう1回押したとき、モード表示は元の文字に戻りましたか?"
                " 「戻った」「戻らない」「押していない」",
            )
            a["kept"] = p.ask(
                "kept",
                f"4/5 {target}で、選択中のサムネイル/表示ページは変わらず保たれていましたか?"
                " 「保たれた」「変わった」「分からない」(PDFが開いていない場合は「PDFなし」)",
            )
            a["single"] = p.ask(
                "single", "5/5 PageFolioの画面は1つだけですか? 「1つ」「複数」"
            )
        a["note"] = p.ask("note", "最後に気づいたことを一言(なければ「なし」)")
        return a

    def key_step(self):
        """W02の観察手順。settingsは文字入力(x)、thumb/previewはF5(モード切替)で行う。

        thumb/previewのCanvasは文字キーを受けず、利用者に効果が見えないためxは使わない。
        """
        p = self.prompter
        say("")
        if self.cond == "settings":
            say(
                "PageFolioが前面に出ていたら、キーボードで x を1文字だけ押してください(マウスは使わない)。"
            )
            say(
                "前面に出なかった場合は何も押さず、そのように答えてください。押したあとにこの端末へ戻って答えます。"
            )
        else:
            say(
                "PageFolioが前面に出ていたら、キーボードで F5 を1回だけ押してください"
                "(閲覧モード/編集モードの切替。ヘッダーのモード表示ボタン「👁 閲覧モード」「📝 編集モード」の文字が変わります)。"
                "マウスは使わない。"
            )
            say(
                "文字が変わったのを見たら、F5 をもう1回だけ押して元の表示に戻し、戻ったのを確認してください。"
            )
            say(
                "前面に出なかった場合は何も押さず、そのように答えてください。押したあとにこの端末へ戻って答えます。"
            )
            self.step("key-probe-instructed", key="F5", presses=2)
        p.enter("操作が終わったら Enter を押してください。")

    # -- Python入口 -----------------------------------------------------------
    def run_python(self):
        """Python入口。入力監視(読み取り専用)を全体に被せ、判定は session JSON に残す。"""
        self.monitor = InputMonitor(self.sampler)
        self.monitor.set_phase("start-harness")
        self.monitor.start()
        try:
            self._run_python()
        finally:
            self.close_monitor()

    def close_monitor(self):
        """監視を止め、手順の汚染有無と focus_correct の帰属を session に書く。"""
        monitor = self.monitor
        if monitor is None:
            return
        monitor.stop()
        summary = monitor.summary()
        inspect_json = (self.session.get("harness_inspect") or {}).get("json") or {}
        assessment = assess_procedure(summary, inspect_json.get("focus-result.json"))
        self.session["input_monitor"] = summary
        self.session["procedure_assessment"] = assessment
        self.session["procedure_verdict"] = assessment["procedure_verdict"]
        self.session["focus_attribution"] = assessment["focus_attribution"]
        say("")
        say(f"== 入力監視の結果: {assessment['procedure_verdict']} ==")
        say(assessment["reason"])
        for event in assessment["pagefolio_presses_before_peer_done"]:
            under = event.get("under") or {}
            say(
                f"  - PageFolio上の押下: {event['t']} / {event['button']}ボタン / 位置 {event['pos']}"
                f" / 押下先「{under.get('title', '')}」 / phase={event['phase']}"
            )
        for event in assessment["pagefolio_keys_before_peer_done"]:
            say(f"  - PageFolio前面中のキー押下: {event['t']} / キー番号 {event['vk']}")
        if assessment["rerun_required"]:
            say(
                "この回の focus_correct は製品の合否として読みません(手順汚染は製品失敗と区別して記録します)。"
                "同じコマンドで再走してください。PageFolioの画面内は一切クリックしないでください。"
            )

    def _run_python(self):
        p = self.prompter
        monitor = self.monitor
        p.show(f"== {self.spec} (Python入口 {self.entry}) を開始します ==")
        say(
            "【入力監視】この行の間、マウスのボタン押下(位置・押下先の窓)と前面の窓の切替、"
            "PageFolioが前面にある間のキー押下(キー番号のみ)を記録します。入力内容や画面は記録しません。"
        )
        self.step("start-harness")
        start = harness("start", "--case", self.cond)
        self.session["harness_start"] = {
            k: start[k] for k in ("returncode", "stderr_tail")
        }
        if start["returncode"] != 0 or not start["json"]:
            self.session["outcome"] = "start-failed"
            say("隔離PageFolioを起動できませんでした。担当へ伝えてください。")
            return
        manifest = start["json"]
        run = manifest["run"]
        self.session["run"] = run
        self.session["harness_manifest"] = {
            k: manifest.get(k)
            for k in ("run", "namespace", "case", "launcher_pid", "source_commit")
        }
        marker = Path(run).name
        pids = pids_with_marker(marker)
        monitor.set_owned_pids(pids)
        self.session["owned_pids"] = alive_identities(pids)
        try:
            before = main_windows(pids)
            fg0 = S.foreground_info()
            self.step("prepared", windows=before, foreground=fg0, pids=pids)
            say("")
            if self.case == "W01":
                if not any(w["iconic"] for w in before):
                    self.session["outcome"] = "preparation-not-established"
                    say(
                        "最小化された状態を確認できませんでした(準備不成立)。担当へ伝えてください。"
                    )
                    return
                say("隔離PageFolioは最小化された状態です(タスクバーに残っています)。")
            else:
                if not any(w["visible"] for w in before):
                    self.session["outcome"] = "preparation-not-established"
                    say(
                        "PageFolioの画面が見える状態を確認できませんでした(準備不成立)。"
                    )
                    return
                say(f"隔離PageFolioに操作先({W02_TARGETS[self.cond]})が準備済みです。")
                say("")
                say(
                    "【重要】このあと二次起動します。Enter を押すまで、PageFolio の画面内は一切クリックしないでください"
                    "(ボタン・サムネイル・プレビュー・余白も含みます)。"
                )
                if fg0.get("pid") in pids:
                    say(
                        "いまPageFolioが前面に出ています。この PowerShell へはタイトルバーをクリックするか Alt+Tab で戻ってください"
                        "(隠れているときはタスクバーの PowerShell のボタンでも構いません)。"
                    )
                else:
                    say(
                        "PageFolio以外が前面です。PageFolioの画面内はクリックせず、この PowerShell で Enter を押してください"
                        "(PowerShell へ戻るときはタイトルバーか Alt+Tab を使います)。"
                    )
                say(
                    "PageFolio内を1回押しただけで入力先が変わり、結果を製品の判定に使えなくなります(その回は再走になります)。"
                )
            monitor.set_phase("awaiting-enter")
            p.enter("準備ができたら Enter を押してください。この直後に二次起動します。")
            monitor.set_phase("peer")
            self.step("peer")
            peer = harness("peer", "--run", run, "--entry", self.entry, timeout=60)
            self.session["harness_peer"] = {
                k: peer[k] for k in ("returncode", "stderr_tail", "json")
            }
            time.sleep(1.5)
            after = main_windows(pids)
            fg1 = S.foreground_info()
            self.step("after-peer", windows=after, foreground=fg1)
            monitor.set_phase("post-peer")
            early = assess_procedure(monitor.summary(), None)
            if early["procedure_verdict"] == "contaminated":
                # 手順汚染が確定。利用者に以降の観察・回答を求めず、focus-result だけ記録して終える。
                self.session["outcome"] = "procedure-contaminated"
                inspected = harness("inspect", "--run", run, timeout=60)
                self.session["harness_inspect"] = {
                    k: inspected[k] for k in ("returncode", "stderr_tail", "json")
                }
                say("")
                say(
                    "【手順汚染】Enter までの間にPageFolio内でマウスのボタン押下を検出しました。"
                    "この回は再走が必要です。以降のF5操作や質問への回答は要りません。"
                )
                return
            if self.case == "W02":
                self.key_step()
            answers = self.questions(exe=False)
            self.session["answers"] = answers
            inspected = harness("inspect", "--run", run, timeout=60)
            self.session["harness_inspect"] = {
                k: inspected[k] for k in ("returncode", "stderr_tail", "json")
            }
            self.session["outcome"] = "answered"
        finally:
            self.cleanup_python(run, pids)

    def cleanup_python(self, run, pids):
        stop = harness("stop", "--run", run, timeout=60)
        self.session["harness_stop"] = {
            k: stop[k] for k in ("returncode", "stderr_tail")
        }
        deadline = time.monotonic() + 20
        remaining = alive_identities(pids)
        while remaining and time.monotonic() < deadline:
            time.sleep(0.5)
            remaining = alive_identities(pids)
        terminated = []
        for (
            item
        ) in remaining:  # 起動時に記録した所有PIDだけを、生成時刻+imageの一致を見て回収
            ident = S.process_identity(item["pid"])
            if ident and ident["alive"] and S.same_process(item, ident):
                terminated.append(
                    {"pid": item["pid"], "result": S._terminate_owned(item)}
                )
        self.session["cleanup"] = {
            "left_after_harness_stop": remaining,
            "terminated_owned": terminated,
            "alive_after": alive_identities(pids),
        }
        if not self.selftest:
            say("")
            say("隔離PageFolioを回収しました。")

    # -- 実EXE ---------------------------------------------------------------
    def run_exe(self):
        p = self.prompter
        p.show(f"== {self.spec} (実配布EXEの隔離copy) を開始します ==")
        # 実EXE行は利用者がPageFolio内を操作する手順(PDFを開く・操作先を作る)なので入力監視の対象外。
        self.session["input_monitor"] = {
            "enabled": False,
            "reason": "実EXE行は利用者がPageFolio内を操作する手順のため監視しない",
        }
        self.session["procedure_verdict"] = "not-monitored"
        manifest = S.prepare(FINAL, self.case)
        run = Path(manifest["run"])
        self.session["run"] = str(run)
        self.session["run_id"] = manifest["run_id"]
        self.session["binary_sha256"] = manifest["source"]["exe_sha256"]
        self.session["tree_sha256"] = manifest["source"]["tree_sha256"]
        self.session["environment"] = manifest["environment"]
        started = False
        try:
            pdf = None
            if self.case == "W02" and self.cond != "settings":
                pdf = S.add_fixture_pdf(run, "edit-three-page")
                self.session["fixture_pdf"] = pdf
            record = S.start(run, settle=5.0)
            started = True
            pids = [record["pid"]]
            self.session["primary"] = {
                k: record[k] for k in ("pid", "created", "image")
            }
            wins = main_windows(pids)
            self.step("started", windows=wins, foreground=S.foreground_info())
            say("")
            say("== PageFolio(配布EXEの隔離copy)を起動しました ==")
            say(
                "【重要】LLM設定(🤖)は開かないでください。プロバイダも変更しないでください。"
            )
            if self.case == "W01":
                if self.cond == "normal":
                    say(
                        "1. 画面は最大化せず、今のままにしてください。ヘッダーの文字と、画面の位置・大きさを覚えてください。"
                    )
                else:
                    say(
                        "1. 画面を最大化してください(タイトルバーをダブルクリック、または最大化ボタン)。ヘッダーの文字を覚えてください。"
                    )
                p.enter("覚えたら Enter を押してください。")
                before = main_windows(pids)
                self.step(
                    "before-minimize", windows=before, foreground=S.foreground_info()
                )
                say("2. 最小化してください(タスクバーに残ります)。")
                p.enter(
                    "最小化したら Enter を押してください。この直後に二次起動します。"
                )
                if self.selftest:
                    for w in main_windows(pids):
                        user32.ShowWindow(w["hwnd"], 6)  # SW_MINIMIZE(機構確認のみ)
                    time.sleep(1)
                minimized = main_windows(pids)
                self.step("minimized", windows=minimized)
                if not any(w["iconic"] for w in minimized):
                    self.session["warning_not_minimized"] = True
                    say(
                        "(最小化された窓を外部観測で確認できませんでした。記録に残して続行します)"
                    )
            else:
                if self.cond == "settings":
                    say(
                        "1. 「⚙ 設定」を開き、入力欄の1つに文字を入れ、一部を選択してカーソルを置いてください(LLM設定は開かない)。"
                    )
                else:
                    say(
                        "1. 次のPDFを「ファイルを開く」で開いてください(パスはクリップボードにコピー済み)。"
                    )
                    say(f"   {pdf['path']}")
                    if not self.selftest:
                        try:
                            subprocess.run(
                                ["clip"],
                                input=str(pdf["path"]).encode("ascii", "ignore"),
                                check=False,
                                timeout=10,
                            )
                        except Exception:
                            pass
                    if self.cond == "thumb":
                        say("2. 左ペインのサムネイルでページを1つ選択してください。")
                    else:
                        say("2. 中央のプレビューをクリックして操作先にしてください。")
                p.enter(
                    "操作先ができたら Enter を押してください。この直後に二次起動します。"
                )
                self.step(
                    "target-ready",
                    windows=main_windows(pids),
                    foreground=S.foreground_info(),
                )
            fg0 = S.foreground_info()
            peer = S.peer(run)
            self.session["peer"] = {k: peer[k] for k in ("pid", "created", "image")}
            time.sleep(4)
            obs = S.inspect(run, "after-peer")
            pids_all = [record["pid"], peer["pid"]]
            after = main_windows(pids_all)
            self.step(
                "after-peer",
                windows=after,
                foreground=obs["foreground"],
                owner_probe=obs["owner_probe"],
                foreground_before_peer=fg0,
            )
            if self.case == "W02":
                self.key_step()
            answers = self.questions(exe=True)
            self.session["answers"] = answers
            self.session["outcome"] = "answered"
        finally:
            stop = None
            if started:
                try:
                    stop = S.stop(run, timeout=12.0)
                except Exception as error:
                    stop = repr(error)
            try:
                verify = S.verify_copy(S.load_run(run))
            except Exception as error:
                verify = repr(error)
            self.session["stop"] = stop
            self.session["verify_after"] = (
                {
                    k: verify[k]
                    for k in (
                        "ok",
                        "overlay_changed",
                        "distribution_changed",
                        "undeclared",
                        "extra_dirs",
                        "missing_dirs",
                        "exe_sha256",
                        "tree_sha256",
                    )
                }
                if isinstance(verify, dict)
                else verify
            )
            try:
                self.session["source_distribution_unchanged"] = S._source_unchanged(
                    S.load_run(run)
                )
            except Exception as error:
                self.session["source_distribution_unchanged"] = repr(error)
            self.session["owner_after"] = S.probe_owner()
            if not self.selftest:
                say("")
                say(
                    "PageFolioを回収しました(終了確認が出ても押さずにそのままで構いません。自動で回収されます)。"
                )

    def compose_answer(self):
        a = self.session.get("answers") or {}
        if not a:
            return ""
        parts = [f"{k}={v}" for k, v in a.items() if k != "note"]
        return (
            f"{self.case} {self.cond} {self.entry}："
            + "・".join(parts)
            + f"（メモ: {a.get('note', '')}）"
        )

    def finish(self):
        self.session["finished_at"] = now()
        self.session["raw_inputs"] = self.prompter.inputs
        self.session["composed_answer"] = self.compose_answer()
        out_dir = EVIDENCE / ("selftest" if self.selftest else "")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = self.spec.replace("/", "_").replace("@", "_at_")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = out_dir / f"{slug}-{stamp}.json"
        serial = 1
        while out.exists():  # 既存の記録(原本)を上書きしない。再走は常に別ファイル
            serial += 1
            out = out_dir / f"{slug}-{stamp}-{serial}.json"
        S.write_json(out, self.session)
        say(f"記録を保存しました: {out}")
        return out


# ---------------------------------------------------------------------------
# 入力監視の機構確認(--check-monitor)
# ---------------------------------------------------------------------------
class _FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt=0.01):
        self.t += dt


class _FakeSampler:
    """偽の観測面。実windowにも入力にも触れない。"""

    def __init__(self, windows):
        self.btn = {"left": False, "right": False, "middle": False}
        self.pos = [10, 10]
        self.fg = 100
        self.windows = windows
        self.under = windows[100]
        self.keys = set()
        self.alt = False
        self.fail = False

    def buttons(self):
        if self.fail:
            raise RuntimeError("fake sampler failure")
        return dict(self.btn)

    def cursor(self):
        return list(self.pos)

    def window_at(self, pos):
        return dict(self.under)

    def foreground(self):
        return self.fg

    def describe(self, hwnd):
        return dict(
            self.windows.get(
                hwnd, {"hwnd": hwnd, "pid": None, "title": "", "class": ""}
            )
        )

    def keys_down(self):
        return set(self.keys), self.alt


def check_monitor():
    """入力監視ロジックの機構確認。窓も入力も作らず、前景も変えない。

    (1) 偽サンプラで、押下エッジ・押下先の判定・手順判定・focus 帰属を確認する。
    (2) 実APIは読み取りだけを短くポーリングし、動作と(subprocess待機中も止まらないこと)を確認する。
    SendInput / SetCursorPos / SetForegroundWindow は呼ばない。
    """
    failures = []

    def check(name, condition, detail=""):
        say(
            f"  [{'ok' if condition else 'FAIL'}] {name}"
            + (f" ... {detail}" if not condition and detail else "")
        )
        if not condition:
            failures.append(name)

    ps = {"hwnd": 100, "pid": 111, "title": "Windows PowerShell", "class": "Console"}
    pf = {"hwnd": 200, "pid": 222, "title": "PageFolio", "class": "TkTopLevel"}
    windows = {100: ps, 200: pf}

    def new_monitor(owned=(222,), phase="awaiting-enter"):
        sampler = _FakeSampler(windows)
        clock = _FakeClock()
        monitor = InputMonitor(sampler, clock=clock)
        monitor.set_owned_pids(owned)
        monitor.set_phase(phase)
        monitor.poll_once()  # 基準線
        return monitor, sampler, clock

    def tick(monitor, clock, dt=0.01):
        clock.advance(dt)
        monitor.poll_once()

    def click(monitor, sampler, clock, under, button="left", up_under=None):
        sampler.under, sampler.pos = under, [300, 400]
        sampler.btn[button] = True
        tick(monitor, clock)
        sampler.under, sampler.pos = up_under or under, [900, 100]
        sampler.btn[button] = False
        tick(monitor, clock)

    def verdict(monitor, fc=None):
        focus = None if fc is None else {"focus_correct": fc}
        return assess_procedure(monitor.summary(), focus)

    say("== 入力監視の機構確認(窓も入力も作らない) ==")
    say("-- 偽サンプラ --")
    m, s, c = new_monitor()
    tick(m, c)
    a = verdict(m)
    check(
        "介入なし: clean・押下0",
        a["procedure_verdict"] == "clean" and not m.mouse_events,
    )

    m, s, c = new_monitor()
    click(m, s, c, ps)
    a = verdict(m)
    check(
        "PowerShell上の押下は記録するが汚染ではない",
        a["procedure_verdict"] == "clean"
        and [e["kind"] for e in m.summary()["mouse_events"]] == ["down", "up"]
        and not any(e["on_pagefolio"] for e in m.summary()["mouse_events"]),
    )

    m, s, c = new_monitor()
    click(m, s, c, pf, up_under=ps)  # PageFolio内で押して外で離す(btn_open再現と同じ形)
    a = verdict(m, fc=False)
    press = a["pagefolio_presses_before_peer_done"]
    check(
        "PageFolio内で押して外で離す: contaminated",
        a["procedure_verdict"] == "contaminated"
        and len(press) == 1
        and a["rerun_required"],
    )
    check(
        "押下の位置・押下先・phase・押下ボタンを記録",
        bool(press)
        and press[0]["pos"] == [300, 400]
        and press[0]["under"]["pid"] == 222
        and press[0]["phase"] == "awaiting-enter"
        and press[0]["button"] == "left",
    )
    check(
        "離上は別windowで記録され、押下のon_pagefolioに影響しない",
        [e["under"]["pid"] for e in m.summary()["mouse_events"]] == [222, 111],
    )
    check(
        "contaminated のとき focus_correct=false を製品失敗扱いにしない",
        a["focus_attribution"] == "not-judged-contaminated",
    )

    m, s, c = new_monitor(phase="post-peer")
    click(m, s, c, pf)
    a = verdict(m)
    check(
        "peer完了後(post-peer)の押下は参考記録のみで汚染にしない",
        a["procedure_verdict"] == "clean"
        and any(e["on_pagefolio"] for e in m.summary()["mouse_events"]),
    )

    m, s, c = new_monitor(owned=(), phase="start-harness")
    click(m, s, c, pf)
    m.set_owned_pids([222])  # 所有PIDは起動後に分かる。事後にまとめて判定する
    check(
        "所有PID確定前の押下も事後判定でcontaminated",
        verdict(m)["procedure_verdict"] == "contaminated",
    )

    for button in ("right", "middle"):
        m, s, c = new_monitor()
        click(m, s, c, pf, button=button)
        check(
            f"{button}ボタンでもcontaminated",
            verdict(m)["procedure_verdict"] == "contaminated",
        )

    m, s, c = new_monitor()
    s.btn["left"] = True  # 監視開始時にすでに押されていた
    m2 = InputMonitor(s, clock=c)
    m2.set_owned_pids([222])
    m2.set_phase("awaiting-enter")
    m2.poll_once()
    s.btn["left"] = False
    tick(m2, c)
    check(
        "開始時に押下中のボタンは held-at-start で、押下エッジに数えない",
        [e["kind"] for e in m2.mouse_events] == ["held-at-start", "up"]
        and verdict(m2)["procedure_verdict"] == "clean",
    )

    m, s, c = new_monitor()
    s.fg = 200
    tick(m, c)
    s.fg = 100
    tick(m, c)
    tr = m.summary()["foreground_transitions"]
    check(
        "前景遷移を記録(最初の観測は遷移に数えない)",
        [(t["from"]["pid"], t["to"]["pid"]) for t in tr] == [(111, 222), (222, 111)],
    )

    m, s, c = new_monitor()
    s.fg = 200
    tick(m, c)  # PageFolioが前面になった(基準線)
    s.keys = {0x09}
    tick(m, c)
    a = verdict(m)
    check(
        "PageFolio前面中のTab押下: keys-suspect",
        a["procedure_verdict"] == "keys-suspect" and a["rerun_required"],
    )

    m, s, c = new_monitor()
    s.fg = 200
    tick(m, c)  # PageFolioが前面になった(基準線)
    s.keys, s.alt = {0x09}, True  # Alt+Tab
    tick(m, c)
    check(
        "Alt+Tab(Alt押下中のTab)は入力先を変えないので数えない",
        verdict(m)["procedure_verdict"] == "clean" and not m.key_events,
    )

    m, s, c = new_monitor()
    s.fg = 200
    s.keys = {0x09}  # PageFolioが前面になった時点ですでに押されていたキーは基準線
    tick(m, c)
    tick(m, c)
    check(
        "前面化の時点で押下中だったキーは押下エッジに数えない",
        verdict(m)["procedure_verdict"] == "clean" and not m.key_events,
    )

    m, s, c = new_monitor()
    s.keys = {0x09}  # PageFolioが前面でない間のキーは見ない
    tick(m, c)
    tick(m, c)
    check("PageFolioが前面でない間のキーは記録しない", not m.key_events)

    m, s, c = new_monitor()
    s.fail = True
    tick(m, c)
    check(
        "監視のerrorはmonitor-incomplete",
        verdict(m)["procedure_verdict"] == "monitor-incomplete",
    )
    m, s, c = new_monitor()
    tick(m, c, dt=MONITOR_MAX_GAP_S + 0.1)
    check(
        "観測の空きが大きいとmonitor-incomplete",
        verdict(m)["procedure_verdict"] == "monitor-incomplete",
    )
    empty = InputMonitor(_FakeSampler(windows), clock=_FakeClock())
    check(
        "観測0回はmonitor-incomplete",
        verdict(empty)["procedure_verdict"] == "monitor-incomplete",
    )

    m, s, c = new_monitor()
    tick(m, c)
    check(
        "clean + focus_correct=True: product-focus-ok",
        verdict(m, True)["focus_attribution"] == "product-focus-ok",
    )
    check(
        "clean + focus_correct=False: product-focus-failure-candidate(Aの反証候補)",
        verdict(m, False)["focus_attribution"] == "product-focus-failure-candidate",
    )
    check(
        "clean + focus結果なし: no-focus-result",
        verdict(m, None)["focus_attribution"] == "no-focus-result",
    )
    check(
        "監視なしの行: not-monitored",
        assess_procedure({"enabled": False}, {"focus_correct": False})[
            "procedure_verdict"
        ]
        == "not-monitored",
    )
    try:
        json.dumps(m.summary(), ensure_ascii=False)
        serializable = True
    except TypeError:
        serializable = False
    check("summaryはJSON化できる", serializable)
    check(
        "KEY_VKS: Tab/Space/Enter/F5を含み、マウス・修飾キーを除く",
        {0x09, 0x20, 0x0D, 0x74} <= set(KEY_VKS)
        and not ({0x01, 0x02, 0x04, 0x10, 0x11, 0x12, 0xA0, 0xA5} & set(KEY_VKS)),
    )

    say("-- 実API(読み取りだけ・約0.6秒) --")
    sampler = Win32Sampler()
    held = sampler.buttons()
    pos = sampler.cursor()
    fg = sampler.describe(sampler.foreground())
    under = sampler.window_at(pos)
    check(
        "実API: buttons/cursor/foreground/window_at が返る",
        set(held) == {"left", "right", "middle"}
        and len(pos) == 2
        and "pid" in fg
        and "pid" in under,
    )
    say(
        f"     (参考) 現在の前面: pid={fg['pid']} 「{fg['title']}」 / ポインタ下: pid={under['pid']} 「{under['title']}」 / 押下中: {held}"
    )
    monitor = InputMonitor()
    monitor.set_phase("check")
    monitor.start()
    subprocess.run(
        [sys.executable, "-c", "import time; time.sleep(0.6)"],
        check=False,
        stdin=subprocess.DEVNULL,
    )
    monitor.stop()
    real = monitor.summary()
    check(
        "実監視: subprocess待機中も観測が止まらない",
        real["samples"] >= 20 and not real["errors"] and real["max_gap_s"] < 0.25,
        f"samples={real['samples']} errors={real['errors']} max_gap_s={real['max_gap_s']}",
    )
    check(
        "実監視: 監視スレッドが停止している",
        monitor._thread is not None and not monitor._thread.is_alive(),
    )
    say(
        f"     (参考) samples={real['samples']} max_gap_s={real['max_gap_s']} 押下エッジ={len(real['mouse_events'])}"
    )

    say("")
    if failures:
        say(f"機構確認: 失敗 {len(failures)} 件 -> {failures}")
        return 1
    say("機構確認: すべて合格")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", help="例: W01/normal@script")
    ap.add_argument(
        "--selftest", action="store_true", help="機構確認用(canned回答・証拠にしない)"
    )
    ap.add_argument(
        "--check-monitor",
        action="store_true",
        help="入力監視ロジックの機構確認(窓も入力も作らず前景も変えない)",
    )
    args = ap.parse_args()
    if args.check_monitor:
        raise SystemExit(check_monitor())
    if not args.row:
        ap.error("--row が必要です(例: --row W02/preview@script)")
    row = Row(args.row, args.selftest)
    try:
        if row.entry == "production-exe":
            row.run_exe()
        else:
            row.run_python()
    except KeyboardInterrupt:
        row.session["outcome"] = "interrupted"
        say("中断されました。")
    except Exception as error:
        row.session["outcome"] = "error"
        row.session["error"] = repr(error)
        say(f"エラー: {error!r}")
    finally:
        row.finish()
    say("")
    say(
        f"終了しました。チャットに「{row.spec} 完了」のように短く伝えてください(記録は自動で保存済み)。"
    )


if __name__ == "__main__":
    main()
