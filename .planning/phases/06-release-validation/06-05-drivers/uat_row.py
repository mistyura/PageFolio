# ruff: noqa
"""06-05-02 の1行(ケースID/subrow)を、利用者が自分のPowerShellで実行する人手受入driver。

対象: G1 = W01 / W02、G2 = W03 / W04、G3 = W05a / W05b (script|module と 実配布EXE)。
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
  ... --check-w05b                            (W05b判定の機構確認。窓も入力も作らず前景も変えない。純関数に偽データを渡すだけ)
  ... --row W05b/ocr-close-confirm@script|module|production-exe
        (G3。hold中のOCRDialog閉じる確認へ二次起動後に自動復帰 → 利用者が「いいえ」→ 同じ要求が完了。
         production-exe は利用者が Explorer で隔離copyの PageFolio.exe を実ダブルクリックする。
         driver は二次起動を合成せず、外部観測だけを行う)

UIスレッド診断(debug: w02-preview-peer-expired。発生頻度の確認用。受入証拠ではない。任意・既定OFF):
  ... --row W02/preview@module --diagnose-ui-thread [--diag-run N --diag-runs M]
        隔離した一次PageFolioのUIスレッドを外から読み取り専用で約100msごとに観測し、06-05-evidence/
        debug-w02-preview-peer-expired/ に purpose="debug-frequency"・acceptance=false で保存する
        (既存の証拠原本には書かない)。実装と使うAPIは ui_thread_probe.py の冒頭に記載。
  ... --diagnose-ui-thread --wm-null-probe    (+ 一次の窓へ SendMessageTimeoutW(WM_NULL) を約0.5秒ごとに送る。
                                                既定OFF。OFFのときは1回も呼ばない)
  ... --induce-switcher                       (診断のみ。誘発手順: Alt+Tab の切替UIを0.5秒以上見せて PowerShell へ移り、
                                                約20秒静止してから Enter。手順の案内・不足分の自動待機・成立判定を
                                                session JSON に記録する。--diag-run/--diag-runs と併用)
  ... --external-wake-ms 120                  (診断のみ・既定OFF・100〜150。debug: w02-preview-peer-expired の対策の実機検証。
                                                この機能だけは眺めるだけではなく一次PageFolioのUIスレッドへ外から介入する:
                                                driver が PostThreadMessageW(UIスレッドのtid, WM_NULL) を指定msごとに「投稿」する。
                                                SendMessage・前景/入力APIは使わない。投稿の前に毎回、tid が対象pid(作成時刻一致)の
                                                生きたスレッドか確かめる。--wm-null-probe とは併用しない。session JSON に
                                                diagnostics.external_wake=<ms> を記録し、--summarize-diag が見張りの有無で分けて集計する)
  ... --diag-hold-s 30                        (診断のみ。二次起動が完了しなかった回に、利用者へ何も触らせず
                                                この秒数だけ一次の状態を観測し続ける。既定30、0で無効)
  ... --check-diagnostics                     (診断の機構確認。窓も入力も作らず前景も変えない。偽ネイティブ+
                                                使い捨てのTclプロセス(自分で起動・Tkの窓なし)を観測。約30秒)
  ... --summarize-diag [DIR]                  (診断ディレクトリのセッションJSONから発生頻度を集計。読み取りのみ)

利用者の入力はすべて逐語で session JSON の raw_inputs に保存する(貼り付けを疑う入力は一度拒否して取り直し、
拒否した入力も保存する)。回答はキーボードで短く入力する。右クリック貼り付け/Ctrl+Vは使わない。
session JSON は 06-05-evidence/ に保存し、selftest は 06-05-evidence/selftest/ に分ける。

手順汚染の検出(debug: preview-focus-not-restored で追加):
Python入口の行は、隔離PageFolioの起動から二次起動(peer)の完了までの間、マウスのボタン押下エッジ
(押下時刻・ポインタ位置・押下先の窓・前景窓)と前景窓の切替、PageFolioが前面にある間のキー押下(キー番号のみ)を
読み取り専用のポーリングで記録する。PageFolio上にボタン押下があれば、その行は「手順汚染(再走が必要)」として
session JSON の procedure_verdict / focus_attribution に明示し、focus_correct=false を製品失敗とみなさない。
(ttk Button は押下だけで入力先を取るため、PageFolio内の1回の押下で復帰先の記憶が変わる。製品の復帰は記憶どおり。)

W05b の手動切替の検出(debug: phase06-w05b-alttab-blindspot で追加):
上のキー記録(key_events)は『PageFolio前面中・Alt非押下中』のキーだけを残す設計で、Alt+Tab を構造的に取れない。
W05b(無操作の自動復帰)の判定のため、前景に関係なく Alt / Tab / Win の押下エッジを別系列(switch_key_events)に
残す(読み取りのみ)。さらに観測区間の前景遷移がタスク切替UI(XamlExplorerHostIslandWindow)や ForegroundStaging を
経由したら、キー記録がなくても不成立にする。
"""

import argparse
import ast
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
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
# 前景を人が動かす操作(Alt+Tab・Win+Tab・Win系ショートカット)の監視キー。key_events(PageFolio前面中の
# Alt以外のキー)とは目的が違う: これは前景に関係なく、Alt / Tab / Win の押下エッジを別系列
# (switch_key_events)に残す。W05bの『人が前景を動かしていない』判定の根拠であり、W01〜W05aの
# 手順汚染判定(assess_procedure)には使わない(あちらは awaiting-enter の Alt+Tab を指示している)。
SWITCH_KEY_VKS = {
    "alt": _ALT_VKS,
    "tab": (0x09,),
    "win": (0x5B, 0x5C),
}

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

    def switch_keys(self):
        """いま押されている切替キーの名前集合(alt / tab / win)。前景に関係なく読む。"""
        return {
            name
            for name, vks in SWITCH_KEY_VKS.items()
            if any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks)
        }


def switch_combo(name, down):
    """切替キーの押下エッジが、どの組合せの一部か(記録用の名前)。"""
    if name in ("alt", "tab") and {"alt", "tab"} <= set(down):
        return "alt-tab"
    if name in ("win", "tab") and {"win", "tab"} <= set(down):
        return "win-tab"
    return name


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
        self.switch_key_events = []
        self.switch_key_samples = 0
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
        self._prev_switch = None
        self._held_pending = False
        self._seq = 0
        self._stop = threading.Event()
        self._thread = None

    # -- 制御 -----------------------------------------------------------------
    def set_phase(self, phase):
        self._phase = phase
        # 次の観測で、この境界をまたいで押され続けている切替キーを held-at-phase-start として残す
        self._held_pending = True
        self.phase_log.append({"t": now(), "phase": phase})

    def set_owned_pids(self, pids):
        self._owned = frozenset(pids)

    def elapsed_now(self):
        """監視の起点(_t0)からの経過秒。前景遷移の elapsed_s と同じ時計。"""
        return None if self._t0 is None else round(self.clock() - self._t0, 3)

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

    def _poll_switch_keys(self, t):
        """前景に関係なく Alt / Tab / Win の押下エッジを switch_key_events に残す(読み取りだけ)。

        key_events は『PageFolio前面中・Alt非押下中』のキーだけを記録する設計で、Alt+Tab を構造的に
        取れない(前景がPageFolio以外の間は読まず、前面化の最初のサンプルは基準線、Alt中は除外)。
        W05bの『人が前景を動かしていない』判定にはそれでは足りないため、この系列を別に持つ。
        kind: down(押下エッジ) / held-at-start(監視開始時に押下中) /
              held-at-phase-start(phase切替の瞬間にすでに押下中。境界をまたぐ操作の取りこぼし防止)。
        sampler が switch_keys を持たなければ何もしない(summary の switch_key_capture が偽になる)。
        """
        read = getattr(self.sampler, "switch_keys", None)
        if read is None:
            return
        down = frozenset(read())
        self.switch_key_samples += 1
        previous, self._prev_switch = self._prev_switch, down
        pending, self._held_pending = self._held_pending, False
        if previous is None:
            found = [(name, "held-at-start") for name in sorted(down)]
        else:
            found = [(name, "down") for name in sorted(down - previous)]
            if pending:
                found += [
                    (name, "held-at-phase-start") for name in sorted(down & previous)
                ]
        for name, kind in found:
            self._append(
                self.switch_key_events,
                {
                    **self._stamp(t),
                    "kind": kind,
                    "key": name,
                    "combo": switch_combo(name, down),
                    "foreground": self._fg_info,
                },
            )

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
            self._poll_switch_keys(
                t
            )  # 前景が切り替わる前の状態(foreground=直前の前景)で残す
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
                # Alt+Tab などのシステムショートカットは『PageFolio内の入力先』を変えないのでここでは
                # 数えない(W01〜W05aの手順汚染判定の目的)。前景を動かす操作は switch_key_events に残す。
                if not alt:
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
            "GetAncestor/GetForegroundWindow (no SendInput/SetCursorPos/SetForegroundWindow); "
            "Alt/Tab/Win edges are watched regardless of the foreground window (switch_key_events)",
            "interval_s": self.interval,
            "samples": self.samples,
            "switch_key_capture": self.switch_key_samples > 0,
            "switch_key_samples": self.switch_key_samples,
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
            "switch_key_events": list(self.switch_key_events),
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
# W05b: hold中のOCRDialog閉じる確認へ二次起動後に自動復帰したことの外部観測
#
# 手動切替を自動復帰と解釈した過去の誤り(06-08-W05B-OBSERVATION.md)を繰り返さないため、
# 「確認ダイアログの同一native HWND/PIDが、無操作のまま実前景へ戻ったか」を連続監視の事実だけで決める。
# 判定は純関数 assess_w05b_return(窓にも入力にも触れない)。準備成功・機械成功は人手passではない。
# FakeOcrServerの待機90秒・provider 120秒・harness 120秒は延ばさない。
# ---------------------------------------------------------------------------
W05B_HOLD_LIMIT_S = 90.0  # FakeOcrServerの待機上限(延ばさない。記録のみ)
W05B_START_LATEST_S = 40.0  # Python入口: 要求受信から二次起動(Enter)まで
W05B_EXE_LAUNCH_LATEST_S = (
    55.0  # 配布版: 要求受信から実ダブルクリックによる二次起動の検出まで
)
W05B_NO_LATEST_S = 78.0  # 要求受信から「いいえ」確認まで(待機上限90秒の手前)
W05B_RELEASE_LATEST_S = 86.0  # 要求受信から待機解放まで(これを過ぎる前に必ず解放する)
W05B_QUIET_S = 3.0  # 自動復帰の観測後、音を鳴らすまで無操作で見届ける時間
W05B_KEEP_VIEW_S = 4.0  # 「いいえ」後に処理維持を目視してから解放するまでの時間
W05B_PEER_WAIT_S = (
    15.0  # 実ダブルクリックの二次起動の終了待ち(外部観測の上限。製品期限は不変)
)
W05B_NO_POST_TIMEOUT_S = 600.0  # 配布版: 利用者がOCRを開始するまでの待ち
W05B_OBSERVE_PHASES = ("peer", "w05b-quiet")
# Windows 11 の Alt+Tab / タスクビューは XamlExplorerHostIslandWindow(実測)。ForegroundStaging は数msの中継窓。
# 実測した82本の記録(証拠・診断)で、ForegroundStaging は必ず XamlExplorerHostIslandWindow と一組で現れ、
# 単独の遷移は無い。製品の自動復帰(過去pass 23行・W05bの直接遷移2回)にはどちらも現れない。
# W05bでは観測区間(peer, w05b-quiet)の遷移がこれらを経由したら、人の Alt+Tab とみなして不成立にする。
SWITCHER_CLASSES = ("XamlExplorerHostIslandWindow",)
STAGING_CLASSES = ("ForegroundStaging",)
W05B_LAUNCH_CLICK_GRACE_S = (
    0.25  # 起動した二次processの生成時刻の直後まで(=ダブルクリック本体)は押下に数えない
)
MODAL_CLASS = "#32770"  # OSのネイティブMessageBox
OCR_WINDOW_TITLE = "OCR"

user32.IsWindow.argtypes = [wt.HWND]
user32.IsWindow.restype = wt.BOOL


def find_modal(pids):
    """所有PIDが持つ可視のネイティブ確認ダイアログ(#32770)。無ければNone。"""
    for window in top_windows(pids):
        if window["class"] == MODAL_CLASS and window["visible"]:
            return window
    return None


def find_ocr_window(pids):
    """所有PIDのOCR画面(Tk Toplevel。タイトルOCR)。無ければNone。"""
    for window in top_windows(pids):
        if (
            window["title"] == OCR_WINDOW_TITLE
            and window["class"] != MODAL_CLASS
            and window["visible"]
        ):
            return window
    return None


def window_exists(hwnd):
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
_kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
_kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry)]
_kernel32.Process32FirstW.restype = wt.BOOL
_kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry)]
_kernel32.Process32NextW.restype = wt.BOOL
_kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
_kernel32.CloseHandle.restype = wt.BOOL


def processes_named(name):
    """実行ファイル名が一致するprocessの一覧(pid/親pid)。読み取り専用(Toolhelp snapshot)。"""
    snapshot = _kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if snapshot in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    entry = _ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    found = []
    try:
        ok = _kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == name.lower():
                found.append(
                    {
                        "pid": int(entry.th32ProcessID),
                        "ppid": int(entry.th32ParentProcessID),
                    }
                )
            ok = _kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        _kernel32.CloseHandle(snapshot)
    return found


def find_copy_processes(exe, exclude):
    """隔離copyの PageFolio.exe を実行imageに持つ生きたprocess(exclude以外)。生成時刻順。

    imageの絶対パスまで一致したものだけを返す(利用者が別の場所から起動したPageFolioは数えない)。
    """
    found = []
    for item in processes_named(Path(exe).name):
        if item["pid"] in exclude:
            continue
        ident = S.process_identity(item["pid"])
        if (
            ident
            and ident["alive"]
            and S._norm_path(ident["image"]) == S._norm_path(exe)
        ):
            found.append(
                {
                    **item,
                    **{
                        k: ident[k]
                        for k in (
                            "created",
                            "created_iso",
                            "image",
                            "session_id",
                            "elevated",
                        )
                    },
                }
            )
    found.sort(key=lambda item: item["created"])
    return found


class ProcessWatch:
    """検出直後に開いたhandleで、自分が起動していないprocessの終了コードを読む(読み取り専用)。"""

    def __init__(self, pid, created):
        api = S._api()
        self.api = api
        self.pid = pid
        self.state = "open"
        self.handle = api.k.OpenProcess(
            S.PROCESS_QUERY_LIMITED_INFORMATION | S.SYNCHRONIZE, False, pid
        )
        if not self.handle:
            self.state = "open-failed"
        elif S._creation(self.handle) != created:
            self.close()
            self.state = "identity-mismatch"

    def wait(self, timeout_s):
        if not self.handle:
            return {"state": self.state, "exit_code": None}
        waited = self.api.k.WaitForSingleObject(self.handle, int(timeout_s * 1000))
        if waited != 0:
            return {"state": "timeout", "exit_code": None}
        code = wt.DWORD()
        self.api.k.GetExitCodeProcess(self.handle, ctypes.byref(code))
        return {"state": "exited", "exit_code": int(code.value)}

    def close(self):
        if self.handle:
            self.api.k.CloseHandle(self.handle)
            self.handle = None


def parse_iso(value):
    return datetime.fromisoformat(value)


def seconds_since(moment):
    return (datetime.now(timezone.utc) - moment).total_seconds()


def received_at(server_summary):
    """FakeOcrServer.summary() の最初の受信(received)時刻。無ければNone。"""
    for event in server_summary.get("events", []):
        if event.get("event") == "received":
            return parse_iso(event["time"])
    return None


def assess_w05b_return(
    summary,
    modal,
    owned_pids,
    *,
    fg_before_peer,
    fg_peer_done,
    fg_quiet_end,
    quiet_end_elapsed,
    launch_created_iso=None,
):
    """確認ダイアログへの『自動復帰』が、無操作のまま成立したかを決める(純関数)。

    verdict=clean は次を全て満たすときだけ:
      - 二次起動の前は、確認ダイアログ自身が前景ではなかった(前景は別窓)
      - 観測区間(peer, w05b-quiet)に、同一HWND・同一PIDの確認ダイアログへの前景遷移がある
      - 復帰後に別の窓へ前景が移っていない(手動切替・奪取の疑いがない)
      - 二次起動直後と観測終端の実前景が、同一HWND・同一PIDの確認ダイアログである
      - 観測区間にマウスのボタン押下(どの窓でも)・PageFolio前面中のキー押下がない
        (配布版では、二次processの生成時刻直後までの押下=ダブルクリック本体は数えず別記する)
      - 観測区間の前景遷移が、タスク切替UI(XamlExplorerHostIslandWindow)・ForegroundStaging を
        経由していない(復帰遷移の from がそれらである場合を含む。人の Alt+Tab の形)
      - 観測区間に Alt / Tab / Win の押下エッジ(switch_key_events)がない
      - 入力監視にerror・観測の空き・打切りがなく、切替キーの捕捉が有効だった(switch_key_capture)
      - 捕捉の自己検証: セッション中にタスク切替UIが出た(指示されたAlt+Tab)なら、Alt/Tab/Winの押下が
        1つ以上記録されている(無ければ捕捉が盲目: switch-key-capture-blind)

    限界: 切替UIを出さない素早い Alt+Tab は 前景が null(hwnd=0)を一瞬挟んで直接遷移する形になり、
    製品の正当な復帰(過去のW03配布版passに同じ形がある)と遷移の形だけでは区別できない。その形は
    Alt キー押下エッジの捕捉(switch_key_events)でのみ拾える。捕捉が効かなければ
    switch-key-capture-missing で不成立にし、捕捉できていない状態を clean にしない。
    なお、実機で Alt+Tab を GetAsyncKeyState が読めることは、人の操作を要するため、この純関数や
    --check-* では確認できない(偽サンプラと実APIの呼出し経路のみ確認)。次回の実走で switch_key_events に
    指示された Alt+Tab の Alt/Tab が載ること、載らなければ switch-key-capture-blind で落ちることが、
    実機での確認になる。
    """
    reasons = []
    hwnd, pid = modal.get("hwnd"), modal.get("pid")
    owned = set(owned_pids)
    if pid not in owned:
        reasons.append("modal-not-owned-by-pagefolio")
    if (fg_before_peer or {}).get("hwnd") == hwnd:
        reasons.append("modal-was-already-foreground-before-peer")
    transitions = [
        t
        for t in summary.get("foreground_transitions", [])
        if t.get("phase") in W05B_OBSERVE_PHASES
    ]
    returned = [
        t
        for t in transitions
        if (t.get("to") or {}).get("hwnd") == hwnd
        and (t.get("to") or {}).get("pid") == pid
    ]
    first = returned[0] if returned else None
    if first is None:
        reasons.append("no-foreground-transition-to-modal")
    else:
        left = [
            t
            for t in transitions
            if t["seq"] > first["seq"] and (t.get("to") or {}).get("hwnd") != hwnd
        ]
        if left:
            reasons.append("foreground-left-modal-after-return")
    # 経由窓: 観測区間の遷移が切替UI/中継窓を from か to に持つなら人の Alt+Tab とみなす。
    # first.from が切替UIである場合(Enter 直後の Alt+Tab で、PowerShell→中継窓→切替UI が awaiting-enter、
    # 切替UI→確認 が peer と phase をまたぐ形)も、first 自体が観測区間の遷移なのでここで拾える。
    switch_ui = frozenset(SWITCHER_CLASSES + STAGING_CLASSES)
    via_switcher = [
        t
        for t in transitions
        if (t.get("to") or {}).get("class") in switch_ui
        or (t.get("from") or {}).get("class") in switch_ui
    ]
    if via_switcher:
        reasons.append("task-switcher-during-observation")
    for label, fg in (("peer-done", fg_peer_done), ("quiet-end", fg_quiet_end)):
        if (fg or {}).get("hwnd") != hwnd or (fg or {}).get("pid") != pid:
            reasons.append(f"foreground-not-modal-at-{label}")
    cutoff = None
    if launch_created_iso:
        cutoff = parse_iso(launch_created_iso).timestamp() + W05B_LAUNCH_CLICK_GRACE_S
    presses, launch_presses = [], []
    for event in summary.get("mouse_events", []):
        if event.get("kind") != "down" or event.get("phase") not in (
            W05B_OBSERVE_PHASES
        ):
            continue
        if cutoff is not None and parse_iso(event["t"]).timestamp() <= cutoff:
            launch_presses.append(event)
        else:
            presses.append(event)
    if presses:
        reasons.append("mouse-press-during-observation")
    keys = [
        e
        for e in summary.get("key_events", [])
        if e.get("phase") in W05B_OBSERVE_PHASES
    ]
    if keys:
        reasons.append("key-during-observation")
    switch_keys = [
        e
        for e in summary.get("switch_key_events", [])
        if e.get("phase") in W05B_OBSERVE_PHASES
    ]
    if switch_keys:
        reasons.append("switch-key-during-observation")
    if not summary.get("switch_key_capture"):
        reasons.append("switch-key-capture-missing")
    elif not summary.get("switch_key_events") and any(
        (t.get("to") or {}).get("class") in switch_ui
        or (t.get("from") or {}).get("class") in switch_ui
        for t in summary.get("foreground_transitions", [])
    ):
        # 自己検証: 指示された Alt+Tab(PowerShellへ移る操作)でタスク切替UIが出ているのに、セッション全体で
        # Alt/Tab/Win の押下が1つも記録されていないなら、キー捕捉は実際には効いていない(または切替UIが
        # キーボード以外で出された)。キーの不在を根拠にした clean を出さない。
        reasons.append("switch-key-capture-blind")
    if (
        summary.get("errors")
        or summary.get("samples", 0) <= 0
        or summary.get("truncated")
        or summary.get("max_gap_s", 0) > MONITOR_MAX_GAP_S
    ):
        reasons.append("monitor-incomplete")
    returned_at = first["elapsed_s"] if first else None
    unattended = (
        round(quiet_end_elapsed - returned_at, 3)
        if first is not None and quiet_end_elapsed is not None
        else None
    )
    return {
        "verdict": "clean" if not reasons else "not-established",
        "reasons": reasons,
        "modal": {"hwnd": hwnd, "pid": pid},
        "returned_transition": first,
        "returned_at_elapsed_s": returned_at,
        "observation_end_elapsed_s": quiet_end_elapsed,
        "unattended_seconds_after_return": unattended,
        "mouse_presses_during_observation": presses,
        "launch_presses_excused": launch_presses,
        "key_presses_during_observation": keys,
        "task_switcher_transitions_during_observation": via_switcher,
        "returned_via_task_switcher": bool(
            first is not None and (first.get("from") or {}).get("class") in switch_ui
        ),
        "switch_key_events_during_observation": switch_keys,
        "switch_key_capture": bool(summary.get("switch_key_capture")),
        "foreground_before_peer": fg_before_peer,
        "foreground_peer_done": fg_peer_done,
        "foreground_quiet_end": fg_quiet_end,
        "monitor": {
            "samples": summary.get("samples"),
            "max_gap_s": summary.get("max_gap_s"),
            "errors": summary.get("errors"),
            "truncated": summary.get("truncated"),
        },
        "note": "連続監視の事実のみ。利用者の自己申告(無操作)は別に直接回答で照合する。",
    }


W05B_REASON_TEXT = {
    "modal-not-owned-by-pagefolio": "確認ダイアログがPageFolioのものではない",
    "modal-was-already-foreground-before-peer": "二次起動の前から確認ダイアログが前面だった(自動復帰を示せない)",
    "no-foreground-transition-to-modal": "確認ダイアログへの前景遷移が記録されなかった(復帰せず)",
    "foreground-left-modal-after-return": "復帰後に別の窓へ前景が移った(手動切替・奪取の疑い)",
    "foreground-not-modal-at-peer-done": "二次起動の直後に確認ダイアログが前面ではなかった",
    "foreground-not-modal-at-quiet-end": "観測の終端で確認ダイアログが前面ではなかった",
    "mouse-press-during-observation": "無操作の観測中にマウスのボタン押下があった",
    "key-during-observation": "無操作の観測中にPageFolio前面でキー押下があった",
    "task-switcher-during-observation": "観測中の前景遷移がタスク切替UI/ForegroundStagingを経由した(手動のAlt+Tabの疑い)",
    "switch-key-during-observation": "無操作の観測中にAlt/Tab/Winキーの押下があった(手動切替の疑い)",
    "switch-key-capture-missing": "Alt/Tab/Winキーの捕捉が有効でなかったため、手動切替が無かったと言えない",
    "switch-key-capture-blind": "タスク切替UIは出ているのにAlt/Tab/Winキーの押下が1つも記録されない(捕捉が効いていない、またはキーボード以外で切替)ため、手動切替が無かったと言えない",
    "monitor-incomplete": "入力監視に抜けがあり、無操作を保証できない",
    "peer-failed-or-request-not-held": "二次起動が失敗した、または要求が待機中ではなかった",
    "request-not-held-after-peer": "二次起動の後に要求が待機中ではなかった",
    "extra-pagefolio-process": "想定外の追加のPageFolio.exeが起動していた",
}


def w05b_reasons_text(reasons):
    return "、".join(W05B_REASON_TEXT.get(r, r) for r in reasons)


# ---------------------------------------------------------------------------
def assess_exe_procedure(summary, foreground_correct):
    """W01の無操作観測中は、他ウィンドウへのクリックも区別して残す。"""
    result = assess_procedure(summary, {"focus_correct": foreground_correct})
    clicks = [
        e
        for e in summary.get("mouse_events", [])
        if e.get("kind") == "down" and e.get("phase") == "peer"
    ]
    result["all_window_presses_during_observation"] = clicks
    if clicks:
        result.update(
            procedure_verdict="contaminated",
            rerun_required=True,
            reason="無操作観測中のクリックを検出（他ウィンドウ上も含む）",
            focus_attribution="not-judged-contaminated",
        )
    return result


# 誘発手順(--induce-switcher。診断のみ)の判定: 入力監視の前景遷移から「切替UIを見せて PowerShell へ移り、
# 静止した」を事後に確かめる純関数。窓にも入力にも触れない。
# ---------------------------------------------------------------------------
INDUCE_VARIANT = "alt-tab-switcher-hold-then-quiet-wait"
INDUCE_SWITCHER_MIN_S = 0.5  # 切替UIが前景にあった時間の下限
INDUCE_WAIT_S = 20.0  # PowerShellへ移ってから二次起動(Enter)までの静止時間
INDUCE_QUIET_TOLERANCE_S = 0.5
INDUCE_MAX_ATTEMPTS = 3  # PageFolioが前面のままEnterされたときの取り直し回数
# SWITCHER_CLASSES / STAGING_CLASSES は W05b の判定(上)と共用するため W05B_OBSERVE_PHASES の近くで定義している。

INDUCE_INSTRUCTIONS = (
    "【誘発手順(診断・この回は次のとおりに操作してください)】",
    "  1. いま PageFolio が前面なら、Alt を押したまま Tab を1回押します(PageFolio の画面内はクリックしない)。",
    "     画面の中央に「タスクの切り替え」(アプリの一覧)が出て、この PowerShell(Windows Terminal)が選ばれた状態になります。",
    "     (PowerShell 以外が選ばれていたら、Alt を押したまま Tab をもう一度押して PowerShell を選びます。)",
    "  2. Alt を押し続けて、その一覧を約1秒そのまま見せてください(0.5秒より短いと、この回は誘発として数えません)。",
    "  3. 約1秒たったら Alt を離します。この PowerShell が前面になります。",
    "  4. そのまま何も触らず(マウスもキーボードも使わず)、約20秒待ちます。",
    "  5. 約20秒たったら、この PowerShell で Enter を押します(早く押しても、足りない分はこの画面が自動で待ちます)。",
    "  PageFolio が前面でなかったときは、先に Alt+Tab で PageFolio へ移り(一覧は短くて構いません)、そこから 1. を行ってください。",
    "  Enter の直後に二次起動します。そのあとも、案内が出るまで PageFolio の画面内をクリックしないでください。",
)

INDUCE_REASON_TEXT = {
    "pagefolio-still-foreground": "Enter の時点で PageFolio が前面のままでした",
    "no-departure": "PageFolio から他の窓へ移った記録がありません",
    "switcher-not-shown": "切替UI(タスクの切り替え)が前面に出た記録がありません(Alt を押したまま Tab で一覧を出してください)",
    "switcher-too-short": "切替UIの表示が短すぎました(0.5秒以上、約1秒を目安に)",
    "no-landing": "切替のあとに落ち着いた窓(PowerShell)の記録がありません",
    "quiet-wait-too-short": "PowerShell へ移ってからの静止時間が足りませんでした",
    "selftest": "selftest は誘発手順を実行しません",
}


def _window_brief(info, transition):
    return {
        "t": transition.get("t"),
        "elapsed_s": transition.get("elapsed_s"),
        "pid": info.get("pid"),
        "class": info.get("class"),
        "title": info.get("title"),
    }


def trace_departure(transitions, owned, now_elapsed=None):
    """最後に PageFolio から離れた経路を取り出す(純関数)。

    transitions: InputMonitor の前景遷移({t, elapsed_s, phase, from, to})。owned: PageFolioのpid集合。
    戻り値:
      pagefolio_foreground  最後の遷移の移動先が PageFolio(=いま PageFolio が前面)
      departed              PageFolio から他へ移り、その後 PageFolio へ戻っていない遷移がある
      switcher_visible_s    離れてから切替UI(XamlExplorerHostIslandWindow)が前景にあった合計秒
      switcher_titles       そのタイトル(「タスクの切り替え」「タスク ビュー」など)
      landing               切替UI・中継窓・null を除いた最後の移動先(PowerShell など)
      quiet_s               landing から now_elapsed までの秒数(now_elapsed が無ければ None)
      path                  離れてからの移動先の一覧(要約)
    """
    owned = set(owned)
    transitions = list(transitions)
    departure = None
    for index, transition in enumerate(transitions):
        origin = (transition.get("from") or {}).get("pid")
        dest = (transition.get("to") or {}).get("pid")
        if dest in owned:
            departure = None  # 戻ってきた: それ以前の離脱は無効
        elif origin in owned:
            departure = index
    last_dest = (transitions[-1].get("to") or {}) if transitions else {}
    out = {
        "pagefolio_foreground": bool(transitions) and last_dest.get("pid") in owned,
        "departed": departure is not None,
        "departure_t": None,
        "switcher_visible_s": 0.0,
        "switcher_titles": [],
        "landing": None,
        "quiet_s": None,
        "path": [],
    }
    if departure is None:
        return out
    path = transitions[departure:]
    out["departure_t"] = path[0].get("t")
    entered = None
    visible = 0.0
    landing = None
    for transition in path:
        dest = transition.get("to") or {}
        at = transition.get("elapsed_s") or 0.0
        out["path"].append(_window_brief(dest, transition))
        if dest.get("class") in SWITCHER_CLASSES:
            if entered is None:
                entered = at
            title = dest.get("title")
            if title and title not in out["switcher_titles"]:
                out["switcher_titles"].append(title)
        elif entered is not None:
            visible += at - entered
            entered = None
        if (
            dest.get("class") not in SWITCHER_CLASSES + STAGING_CLASSES
            and dest.get("pid") is not None
            and dest.get("pid") not in owned
        ):
            landing = _window_brief(dest, transition)
    if entered is not None and now_elapsed is not None:
        visible += max(0.0, now_elapsed - entered)
    out["switcher_visible_s"] = round(visible, 3)
    out["path"] = out["path"][:16]
    if landing is not None and not (
        (transitions[-1].get("to") or {}).get("class") in SWITCHER_CLASSES
    ):
        out["landing"] = landing
        if now_elapsed is not None and landing.get("elapsed_s") is not None:
            out["quiet_s"] = round(max(0.0, now_elapsed - landing["elapsed_s"]), 3)
    return out


def assess_induction(trace, wait_s=INDUCE_WAIT_S, switcher_min_s=INDUCE_SWITCHER_MIN_S):
    """trace_departure の結果から、誘発手順が成立したかを決める(純関数)。成立 = reasons が空。"""
    reasons = []
    if trace.get("pagefolio_foreground"):
        reasons.append("pagefolio-still-foreground")
    elif not trace.get("departed"):
        reasons.append("no-departure")
    else:
        visible = trace.get("switcher_visible_s") or 0.0
        if not trace.get("switcher_titles"):
            reasons.append("switcher-not-shown")
        elif visible < switcher_min_s:
            reasons.append("switcher-too-short")
        if trace.get("landing") is None:
            reasons.append("no-landing")
        elif (trace.get("quiet_s") or 0.0) < wait_s - INDUCE_QUIET_TOLERANCE_S:
            reasons.append("quiet-wait-too-short")
    return {
        "variant": INDUCE_VARIANT,
        "induced": not reasons,
        "reasons": reasons,
        "switcher_visible_s": trace.get("switcher_visible_s"),
        "switcher_titles": trace.get("switcher_titles"),
        "quiet_s": trace.get("quiet_s"),
        "landing": trace.get("landing"),
        "departure_t": trace.get("departure_t"),
        "path": trace.get("path"),
        "required": {"switcher_min_s": switcher_min_s, "quiet_wait_s": wait_s},
    }


def induce_reasons_text(reasons):
    return "・".join(INDUCE_REASON_TEXT.get(r, r) for r in reasons or [])


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
    "nested-settings": "内側のLLM設定を閉じた後の外側設定の入力欄",
    "thumb": "左ペインのサムネイル欄",
    "preview": "中央のプレビュー",
}


def diag_module():
    """UIスレッド診断(読み取り専用)の模組。診断を使うときだけ import する(通常の行には影響しない)。"""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(1, here)
    import ui_thread_probe

    return ui_thread_probe


class Row:
    def __init__(self, spec, selftest, sampler=None, diag=None):
        match = re.fullmatch(
            r"(W0[1234]|W05a|W05b)/([a-z0-9-]+)@(script|module|production-exe)", spec
        )
        if not match:
            raise SystemExit(f"未対応の行です(W01/W02/W03/W04/W05a/W05bのみ): {spec}")
        self.case, self.cond, self.entry = match.groups()
        if (self.case, self.cond) not in (
            ("W01", "normal"),
            ("W01", "zoomed"),
            ("W02", "settings"),
            ("W02", "thumb"),
            ("W02", "preview"),
            ("W03", "pdf-3page"),
            ("W04", "ocr-1page"),
            ("W05a", "nested-settings"),
            ("W05b", "ocr-close-confirm"),
        ):
            raise SystemExit(f"未対応の条件です: {spec}")
        if self.case == "W05b" and selftest:
            raise SystemExit(
                "W05bは--selftest非対応です(人手の実ボタン・実ダブルクリックを伴うGUI行を機構確認で起動しません)。"
                "判定ロジックの機構確認は --check-w05b を使います"
            )
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
        # UIスレッド診断(任意・既定OFF)。ONのときだけ追加フィールドを足す(通常の行のsessionは不変)。
        self.diag = diag
        self.probe = None
        if self.diag:
            if self.entry == "production-exe":
                raise SystemExit(
                    "UIスレッド診断はPython入口の行だけです(実EXE行は対象外)"
                )
            D = diag_module()
            self.session["purpose"] = D.PURPOSE
            self.session["acceptance"] = False
            self.session["debug_session"] = D.DEBUG_SESSION
            self.session["diagnostics"] = {
                "ui_thread": True,
                "wm_null_probe": bool(self.diag.get("wm_null")),
                "external_wake": self.diag.get("external_wake_ms"),
                "interval_ms": self.diag.get("interval_ms"),
                "run_index": self.diag.get("run_index"),
                "run_total": self.diag.get("run_total"),
                "hold_s": self.diag.get("hold_s"),
                "syscall_probe": True,
                "induce": {
                    "requested": bool(self.diag.get("induce")),
                    "variant": INDUCE_VARIANT if self.diag.get("induce") else "free",
                    "switcher_min_s": INDUCE_SWITCHER_MIN_S,
                    "quiet_wait_s": float(
                        self.diag.get("induce_wait_s") or INDUCE_WAIT_S
                    ),
                },
                "driver_sha256": D.file_sha256(__file__),
                "probe_sha256": D.file_sha256(D.__file__),
                "note": "発生頻度の確認用の診断実行。受入証拠ではない。製品コードは変更していない。"
                + (
                    f" 外部見張りON({self.diag.get('external_wake_ms')}ms): driverが一次のUIスレッドへ"
                    " PostThreadMessageW(WM_NULL)を投稿している(介入あり。見張りなしの回と混ぜて頻度を出さない)。"
                    if self.diag.get("external_wake_ms")
                    else ""
                ),
            }
        if self.case == "W01":
            canned = [
                "通常" if self.cond != "zoomed" else "最大化",
                "同じ" if self.entry == "production-exe" else "はい",
                "1つ",
                "見える",
            ]
            if self.entry == "production-exe":
                canned.append("同じ")
        elif self.case == "W03":
            canned = ["4343", "すべて横", "見える", "合成PDFのみ"]
        elif self.case == "W04":
            canned = ["はい", "見えた", "していない"]
        elif self.case == "W05a":
            canned = ["出た", "入った", "保たれた", "1つ"] + (
                ["はい"] if self.entry == "production-exe" else []
            )
        elif self.cond in {"settings", "nested-settings"}:
            canned = ["出た", "入った", "保たれた", "1つ"]
        else:
            canned = ["出た", "変わった", "戻った", "保たれた", "1つ"]
        self.prompter = Prompter(selftest, canned=[*canned, "なし"])

    def step(self, name, **fields):
        self.session["steps"].append({"at": now(), "step": name, **fields})

    def wait_json(self, path, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.is_file():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    pass
            time.sleep(0.05)
        raise S.NotEstablished(f"観測ファイルが期限内にできませんでした: {path.name}")

    def finish_python_ocr(self, manifest):
        fixture = Path(manifest["fixture"])
        self.session["ocr_before"] = self.wait_json(fixture / "manual-ocr-running.json")
        self.session["ocr_after_peer"] = self.wait_json(
            fixture / "manual-ocr-after-peer.json"
        )
        resumed = self.session["ocr_after_peer"]
        if (
            resumed["done"]
            or resumed["server"]["posts"] != 1
            or resumed["server"]["completed"]
        ):
            raise S.NotEstablished("同じOCR要求の待機中に復帰した証拠がありません")
        say(
            "OCR画面の処理中表示を見て、そのまま待ってください。8秒後に同じ要求を解放します。"
        )
        time.sleep(8)
        self.step("ocr-release")
        (fixture / "manual-ocr-release").touch()
        self.session["ocr_completed"] = self.wait_json(
            fixture / "manual-ocr-completed.json"
        )
        self.step("ocr-completed")
        if not self.selftest:
            import winsound

            winsound.Beep(880, 350)
        say(
            "処理が完了しました。OCR画面の結果を確認してからPowerShellへ戻って回答してください。"
        )

    def finish_exe_ocr(self, server):
        self.session["ocr_after_peer"] = server.summary()
        resumed = self.session["ocr_after_peer"]
        if resumed["posts"] != 1 or resumed["completed"] or resumed["expired"]:
            raise S.NotEstablished("OCRが待機中の復帰を確認できませんでした")
        say(
            "OCR画面の処理中表示を見て、そのまま待ってください。8秒後に同じ要求を解放します。"
        )
        time.sleep(8)
        self.step("ocr-release")
        server.release()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            summary = server.summary()
            if summary["completed"] or summary["expired"]:
                break
            time.sleep(0.05)
        ok, reasons = server.single_attempt_ok()
        self.session["ocr_completed"] = server.summary()
        if not ok:
            raise S.NotEstablished(f"OCR完了の通信記録が不成立: {reasons}")
        self.step("ocr-completed")
        time.sleep(
            1
        )  # 完了イベントをUIが表示する時間。成否は利用者の直接回答で判定する。

    # -- W05b ---------------------------------------------------------------
    def w05b_data(self):
        return self.session.setdefault(
            "w05b",
            {
                "budget": {
                    "hold_limit_s": W05B_HOLD_LIMIT_S,
                    "start_latest_s": W05B_START_LATEST_S,
                    "exe_launch_latest_s": W05B_EXE_LAUNCH_LATEST_S,
                    "no_latest_s": W05B_NO_LATEST_S,
                    "release_latest_s": W05B_RELEASE_LATEST_S,
                    "quiet_s": W05B_QUIET_S,
                    "keep_view_s": W05B_KEEP_VIEW_S,
                    "note": "FakeOcrServerの待機90秒・provider 120秒・harness 120秒は延長していない",
                },
                "design": {
                    "claim": "確認ダイアログの同一native HWND/PIDが、無操作のまま実前景へ自動復帰したか",
                    "evidence": "連続監視の前景遷移・入力押下・二次起動直後/観測終端の実前景(assess_w05b_return)",
                    "manual_switch_guard": "復帰後に別窓へ前景が移る/観測中の押下があれば不成立。直接回答でも自己申告を照合",
                    "auto_no": False,
                },
            },
        )

    def beep(self):
        if not self.selftest:
            import winsound

            winsound.Beep(880, 350)

    def w05b_briefing(self, exe):
        say("")
        say(
            "== W05b: 閉じる確認が出たままの二次起動 → 自動復帰 → 「いいえ」 → 同じ処理が完了 =="
        )
        say(
            "【先に最後まで読んでください】始まると時間制限があります(OCR要求の待機は90秒で、延ばせません)。"
        )
        if exe:
            say(
                "  1. Enterで隔離copyを準備します。表示されるフォルダをExplorerで開いたままにします(PageFolio.exe が見える状態。まだ起動しない)。"
            )
            say(
                "  2. 隔離PageFolioが起動します。LLM設定は開かず、プロバイダも変更しません。"
            )
            say(
                "  3. PDFを開き(パスはクリップボード)、唯一のページを選び「現在ページをテキスト抽出」→「▶ 読み取り実行」。サマリは実行しません。"
            )
            say(
                "  4. 処理中になったらOCR画面の「✕ 閉じる」を押し、『OCR 実行中です…閉じますか?』の確認が出たら、ボタンを押さずに止まります。"
            )
            say(
                f"  5. Alt+TabでExplorerへ移り、PageFolio.exe を実際にダブルクリックします(要求の受信から約{W05B_EXE_LAUNCH_LATEST_S:.0f}秒以内)。"
            )
            say(
                "  6. ダブルクリックしたら直ちにマウスから手を離し、音が鳴るまで何も操作しません。切替・クリック・キーはすべて不成立の原因です。"
                "(Alt+Tab・Winキーも不成立になります。キー押下とタスク切替UIの表示は外部から記録しています)"
            )
            say(
                "     確認画面が自動で前面に出てくるのを、ただ見ます(ご自身で前に出さない)。"
            )
        else:
            say(
                "  1. Enterで隔離PageFolioを起動します。OCR画面が処理中になり、『OCR 実行中です…閉じますか?』の確認が自動で出ます。"
            )
            say(
                "     確認画面のボタンは押さず、PageFolioの画面内は一切クリックしません。"
            )
            say(
                "  2. Altを押したままTabで、この黒いPowerShellを選び、案内を確認します(確認画面は前面から外れます)。"
            )
            say(
                f"  3. 要求の受信から約{W05B_START_LATEST_S:.0f}秒以内に、このPowerShellでEnterを押します。Enterの直後に二次起動します。"
            )
            say(
                "  4. Enterを押したら、マウスもキーボードも触らず、窓の切替もしません。音が鳴るまで何も操作しません。"
                "(Alt+Tab・Winキーも不成立になります。キー押下とタスク切替UIの表示は外部から記録しています)"
            )
            say(
                "     確認画面が自動で前面に出てくるのを、ただ見ます(ご自身で前に出さない)。"
            )
        n = 7 if exe else 5
        say(
            f"  {n}. 音が鳴ったら、前面の確認画面で「いいえ」を押します(要求の受信から約{W05B_NO_LATEST_S:.0f}秒以内)。"
        )
        say(
            f"  {n + 1}. 「いいえ」の後、OCR画面が閉じず処理中のままかを見ます。数秒後に待機が解放され、結果欄に"
            "『PageFolio UAT 合成OCR結果』が出て、もう一度音が鳴ります。"
        )
        say(
            f"  {n + 2}. 2度目の音で結果欄を見て、PowerShellへ戻り最初の質問に答えます。以降の質問は画面を見なくて構いません。"
        )
        if exe:
            say(f"  {n + 3}. 最後にPageFolio右上の×で終了します(終了確認は「はい」)。")

    def wait_modal(self, pids, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            modal = find_modal(pids)
            if modal:
                return modal
            time.sleep(0.05)
        raise S.NotEstablished("閉じる確認ダイアログを外部から確認できませんでした")

    def w05b_ask_result(self, answers):
        answers["result_shown"] = self.prompter.ask(
            "result_shown",
            "OCR画面の結果欄に「PageFolio UAT 合成OCR結果」が表示されましたか? 「見えた」「見えない」",
        )

    def w05b_ask_auto_return(self, answers):
        answers["auto_return"] = self.prompter.ask(
            "auto_return",
            "Enter(配布版はダブルクリック)のあと、あなたが何も操作していないのに、"
            "確認画面が自動で前面に出ましたか? 「自動で出た」「出なかった」「分からない」",
        )

    def w05b_ask_rest(self, answers, exe):
        p = self.prompter
        self.w05b_ask_auto_return(answers)
        answers["manual_switch"] = p.ask(
            "manual_switch",
            "Enter(配布版はダブルクリック)から音が鳴るまでの間に、ご自身で別の窓へ切り替えたり、"
            "確認画面を前に出したり、キー・クリックをしましたか? 「していない」「した」",
        )
        answers["answered_no"] = p.ask(
            "answered_no",
            "確認画面では「いいえ」を押しましたか? 「いいえを押した」「はいを押した」「押していない」",
        )
        answers["process_kept"] = p.ask(
            "process_kept",
            "「いいえ」の後、OCR画面は閉じず処理中の表示が続いていましたか? 「続いていた」「閉じた」「分からない」",
        )
        if exe:
            answers["real_double_click"] = p.ask(
                "real_double_click",
                "PageFolio.exe はExplorerで実際にダブルクリックして起動しましたか? 「ダブルクリックした」「別の方法」",
            )
        answers["summary_not_run"] = p.ask(
            "summary_not_run",
            "サマリは実行していませんか? 「していない」「実行した」",
        )
        answers["note"] = p.ask("note", "最後に気づいたことを一言(なければ「なし」)")

    def w05b_not_established(self, ret):
        """自動復帰が成立しなかった回。後続(いいえ・解放)へ進まず、見たままの直接回答だけ残す。"""
        self.session["outcome"] = "return-not-established"
        say("")
        say(
            f"【自動復帰が成立しませんでした】{w05b_reasons_text(ret['reasons'])}。"
            "この回は受入にしません(製品の不合格とも断定しません)。見えたことだけ答えてください。"
        )
        answers = {}
        self.w05b_ask_auto_return(answers)
        answers["note"] = self.prompter.ask(
            "note", "最後に気づいたことを一言(なければ「なし」)"
        )
        self.session["answers"] = answers

    def _run_python_w05b(self):
        """W05b(script/module)。自動Noは送らない。利用者が実ボタンで「いいえ」を押す。"""
        p = self.prompter
        monitor = self.monitor
        w = self.w05b_data()
        p.show(f"== {self.spec} (Python入口 {self.entry}) を開始します ==")
        self.w05b_briefing(exe=False)
        p.enter(
            "案内を読み終えたら Enter を押してください。隔離PageFolioを起動します(ここからOCR要求の待機時間が進みます)。"
        )
        monitor.set_phase("start-harness")
        self.step("start-harness")
        start = harness("start", "--case", "native-ocr")
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
        fixture = Path(manifest["fixture"])
        pids = pids_with_marker(Path(run).name)
        monitor.set_owned_pids(pids)
        self.session["owned_pids"] = alive_identities(pids)
        try:
            running = self.wait_json(fixture / "manual-ocr-running.json")
            self.session["ocr_before"] = running
            posted = received_at(running["server"])
            if posted is None or running["server"]["posts"] != 1:
                raise S.NotEstablished("OCR要求が1件だけ待機中になっていません")
            w["request_received_at"] = posted.isoformat()
            self.session["ocr_close_start"] = self.wait_json(
                fixture / "manual-ocr-close-start.json", timeout=10
            )
            modal = self.wait_modal(pids)
            w["modal_before"] = modal
            w["ocr_window_before"] = find_ocr_window(pids)
            if w["ocr_window_before"] is None:
                raise S.NotEstablished("OCR画面を外部から確認できませんでした")
            w["foreground_when_modal_seen"] = S.foreground_info()
            self.step(
                "modal-up",
                modal=modal,
                ocr_window=w["ocr_window_before"],
                foreground=w["foreground_when_modal_seen"],
            )
            say("")
            say(
                "【確認画面が出ました】ボタンは押さないでください。Altを押したままTabでこのPowerShellへ移り、"
                f"要求の受信から約{W05B_START_LATEST_S:.0f}秒以内にEnterを押してください。"
            )
            monitor.set_phase("awaiting-enter")
            p.enter(
                "PowerShellへ移って準備ができたら Enter を押してください。この直後に二次起動します。"
            )
            fg_before_peer = S.foreground_info()
            w["foreground_before_peer"] = fg_before_peer
            w["enter_elapsed_s"] = round(seconds_since(posted), 2)
            still = find_modal(pids)
            if still is None or still["hwnd"] != modal["hwnd"]:
                raise S.NotEstablished(
                    "Enterの時点で確認画面が残っていません(ボタンが押された可能性)。二次起動せず停止します"
                )
            if w["enter_elapsed_s"] > W05B_START_LATEST_S:
                raise S.NotEstablished(
                    f"要求の受信から{w['enter_elapsed_s']}秒かかりました(上限{W05B_START_LATEST_S:.0f}秒)。"
                    "待機上限を延ばさず、二次起動せず停止します。再走してください"
                )
            monitor.set_phase("peer")
            self.step("peer", foreground=fg_before_peer)
            peer = harness("peer", "--run", run, "--entry", self.entry, timeout=60)
            fg_peer_done = S.foreground_info()
            monitor.set_phase("w05b-quiet")
            w["foreground_peer_done"] = fg_peer_done
            self.session["harness_peer"] = {
                k: peer[k] for k in ("returncode", "stderr_tail", "json")
            }
            self.step("after-peer", windows=main_windows(pids), foreground=fg_peer_done)
            say("")
            say(
                "二次起動しました。何も操作せず、確認画面が前面にあるのを見て待ってください。音が鳴るまで操作しません。"
            )
            time.sleep(W05B_QUIET_S)
            fg_quiet_end = S.foreground_info()
            quiet_end = monitor.elapsed_now()
            w["foreground_quiet_end"] = fg_quiet_end
            self.session["ocr_after_peer"] = self.wait_json(
                fixture / "manual-ocr-after-peer.json"
            )
            resumed = self.session["ocr_after_peer"]
            summary = monitor.summary()
            ret = assess_w05b_return(
                summary,
                modal,
                pids,
                fg_before_peer=fg_before_peer,
                fg_peer_done=fg_peer_done,
                fg_quiet_end=fg_quiet_end,
                quiet_end_elapsed=quiet_end,
            )
            w["return_assessment"] = ret
            early = assess_procedure(summary, None)
            held = (
                not resumed["done"]
                and resumed["server"]["posts"] == 1
                and not resumed["server"]["completed"]
            )
            if peer["returncode"] != 0 or not held:
                ret["reasons"].append("peer-failed-or-request-not-held")
                ret["verdict"] = "not-established"
            if early["procedure_verdict"] != "clean":
                ret["reasons"].append(f"procedure-{early['procedure_verdict']}")
                ret["verdict"] = "not-established"
            if ret["verdict"] != "clean":
                self.w05b_not_established(ret)
                inspected = harness("inspect", "--run", run, timeout=60)
                self.session["harness_inspect"] = {
                    k: inspected[k] for k in ("returncode", "stderr_tail", "json")
                }
                return
            self.beep()
            w["beep_at"] = now()
            monitor.set_phase("w05b-answer")
            self.step("beep-return-verified")
            say("")
            say(
                "音が鳴りました。前面にある確認画面で「いいえ」を押してください"
                f"(要求の受信から約{W05B_NO_LATEST_S:.0f}秒以内。待機は延ばせません)。"
            )
            try:
                no = self.wait_json(
                    fixture / "manual-ocr-close-no.json",
                    timeout=max(1.0, W05B_NO_LATEST_S - seconds_since(posted)),
                )
            except S.NotEstablished as error:
                raise S.NotEstablished(
                    f"「いいえ」を期限内に確認できません: {error}"
                ) from None
            w["no_observed_at"] = now()
            w["no_elapsed_s"] = round(seconds_since(posted), 2)
            self.session["ocr_close_no"] = no
            self.step("answered-no")
            identity = ("dialog_id", "run_gen", "engine_id", "worker_ids")
            if not (
                no["dialog_exists"]
                and not no["cancelled"]
                and all(running[k] == no[k] for k in identity)
                and not no["done"]
                and not no["server"]["completed"]
                and no["server"]["posts"] == 1
            ):
                raise S.NotEstablished("「いいえ」の後に同じ処理が保持されていません")
            w["after_no_windows"] = {
                "modal": find_modal(pids),
                "ocr_window": find_ocr_window(pids),
            }
            say(
                "OCR画面が閉じず処理中のままか、見てください。数秒後に同じ要求を解放します。"
            )
            time.sleep(
                max(
                    0.0,
                    min(
                        W05B_KEEP_VIEW_S, W05B_RELEASE_LATEST_S - seconds_since(posted)
                    ),
                )
            )
            w["ocr_window_before_release"] = find_ocr_window(pids)
            if w["ocr_window_before_release"] is None:
                raise S.NotEstablished("解放の前にOCR画面が閉じました")
            w["release_elapsed_s"] = round(seconds_since(posted), 2)
            self.step("ocr-release")
            (fixture / "manual-ocr-release").touch()
            self.session["ocr_completed"] = self.wait_json(
                fixture / "manual-ocr-completed.json"
            )
            self.step("ocr-completed")
            self.beep()
            say("")
            say(
                "処理が完了しました。OCR画面の結果欄を見て、PowerShellへ戻り最初の質問に答えてください。"
            )
            answers = {}
            self.w05b_ask_result(answers)
            # 画面を見る質問が済んだので、先に隔離ownerを回収する(120秒の安全期限へ触れない)。
            stopped = harness("stop", "--run", run, timeout=60)
            self.session["harness_stop_early"] = {
                k: stopped[k] for k in ("returncode", "stderr_tail")
            }
            inspected = harness("inspect", "--run", run, timeout=60)
            self.session["harness_inspect"] = {
                k: inspected[k] for k in ("returncode", "stderr_tail", "json")
            }
            self.w05b_ask_rest(answers, exe=False)
            self.session["answers"] = answers
            self.session["outcome"] = "answered"
        finally:
            self.cleanup_python(run, pids)

    def exe_w05b(self, run, record, ocr_server, pids, exe_path):
        """W05b(配布EXE)。二次起動は利用者がExplorerで実ダブルクリックする。driverは合成しない。

        外部観測だけで、実ダブルクリックの二次process(親=explorer.exe・imageは隔離copy)の出現、
        確認ダイアログの同一HWND/PIDへの自動復帰、「いいえ」後の同一OCR window/同一要求の保持、
        解放後の同一attemptの完了を、時系列に結び付けて記録する。
        """
        p = self.prompter
        w = self.w05b_data()
        primary = record["pid"]
        monitor = InputMonitor()
        monitor.set_owned_pids(pids)
        monitor.set_phase("prelude")
        monitor.start()
        self.monitor = monitor
        pdf = self.session["fixture_pdf"]
        if not self.selftest:
            try:
                subprocess.run(
                    ["clip"],
                    input=str(pdf["path"]).encode("ascii", "ignore"),
                    check=False,
                    timeout=10,
                )
            except Exception as error:
                say(f"(クリップボードへのコピーに失敗: {error!r})")
        say("")
        say("== PageFolio(配布EXEの隔離copy)を起動しました ==")
        say("【重要】LLM設定(🤖)は開かないでください。プロバイダも変更しません。")
        say(
            "1. 次のPDFを「ファイルを開く」で開いてください(パスはクリップボードにコピー済み)。"
        )
        say(f"   {pdf['path']}")
        say(
            "2. 唯一のページを選び「現在ページをテキスト抽出」→「▶ 読み取り実行」を押します。サマリは実行しません。"
        )
        say(
            "3. 処理中になったらOCR画面の「✕ 閉じる」を押し、確認が出たらボタンを押さずに止まります。"
        )
        say(
            f"4. Alt+TabでExplorerへ移り、PageFolio.exe を実ダブルクリック(要求の受信から約{W05B_EXE_LAUNCH_LATEST_S:.0f}秒以内)。"
        )
        say(
            "5. ダブルクリックしたら直ちにマウスから手を離し、音が鳴るまで何も操作しません。"
            "この画面でEnterを押す必要はありません(driverが外部から観測して進めます)。"
        )
        posted = None
        modal = None
        known = {primary}
        began = time.monotonic()
        peer_item = None
        while peer_item is None:
            if posted is None:
                posted = received_at(ocr_server.summary())
                if posted is not None:
                    w["request_received_at"] = posted.isoformat()
                    self.step(
                        "received",
                        windows=main_windows(pids),
                        foreground=S.foreground_info(),
                    )
                    say(
                        f"[OK] OCR要求を受信しました。ここから約{W05B_EXE_LAUNCH_LATEST_S:.0f}秒以内に、"
                        "「✕ 閉じる」→確認画面で止まる→Explorerで PageFolio.exe をダブルクリック、まで進めてください。"
                    )
                elif time.monotonic() - began > W05B_NO_POST_TIMEOUT_S:
                    raise S.NotEstablished("OCR要求が始まりませんでした(10分)")
            elif modal is None:
                found_modal = find_modal(pids)
                if found_modal:
                    modal = found_modal
                    w["modal_before"] = modal
                    w["ocr_window_before"] = find_ocr_window(pids)
                    if w["ocr_window_before"] is None:
                        raise S.NotEstablished("OCR画面を外部から確認できませんでした")
                    w["foreground_when_modal_seen"] = S.foreground_info()
                    self.step(
                        "modal-up",
                        modal=modal,
                        ocr_window=w["ocr_window_before"],
                        foreground=w["foreground_when_modal_seen"],
                    )
                    say(
                        "[OK] 閉じる確認の画面を検出しました。ボタンは押さず、ExplorerでPageFolio.exeをダブルクリックしてください。"
                    )
            found = find_copy_processes(exe_path, known)
            if found:
                peer_item = found[0]
                break
            if posted is not None and seconds_since(posted) > W05B_EXE_LAUNCH_LATEST_S:
                raise S.NotEstablished(
                    f"要求の受信から{W05B_EXE_LAUNCH_LATEST_S:.0f}秒以内に二次起動を確認できません。"
                    "待機上限を延ばさず停止します。再走してください"
                )
            time.sleep(0.02)
        monitor.set_phase("peer")
        watch = ProcessWatch(peer_item["pid"], peer_item["created"])
        try:
            fg_before_peer = S.foreground_info()
            parent = S.process_identity(peer_item["ppid"])
            parent_valid = bool(parent and parent["created"] <= peer_item["created"])
            parent_image = parent["image"] if parent_valid else None
            launched_by = (
                "explorer-user-double-click"
                if parent_image and Path(parent_image).name.lower() == "explorer.exe"
                else "not-explorer"
            )
            w["peer"] = {
                "pid": peer_item["pid"],
                "created": peer_item["created"],
                "created_iso": peer_item["created_iso"],
                "image": peer_item["image"],
                "parent_pid": peer_item["ppid"],
                "parent_valid": parent_valid,
                "parent_image": parent_image,
                "launched_by": launched_by,
                "detected_at": now(),
                "detected_elapsed_s": monitor.elapsed_now(),
                "detection": "Toolhelp32 snapshot polling(20ms)。image絶対パスが隔離copyと一致",
                "driver_launched": False,
            }
            self.session["peer"] = {
                k: peer_item[k] for k in ("pid", "created", "image")
            }
            manifest = S.load_run(run)
            manifest["processes"].append(
                {
                    "role": "peer",
                    "pid": peer_item["pid"],
                    "created": peer_item["created"],
                    "created_iso": peer_item["created_iso"],
                    "image": peer_item["image"],
                    "session_id": peer_item["session_id"],
                    "elevated": peer_item["elevated"],
                    "exe_sha256": S.sha_file(exe_path),
                    "argv": [str(exe_path)],
                    "started_at": peer_item["created_iso"],
                    "parent_pid": peer_item["ppid"],
                    "exit": None,
                    "launched_by": launched_by,
                    "peer_source": {
                        "run_id": manifest["run_id"],
                        "role": manifest["role"],
                        "version": manifest["source"]["version"],
                        "exe_sha256": manifest["source"]["exe_sha256"],
                    },
                }
            )
            manifest["peer"] = manifest["processes"][-1]["peer_source"]
            manifest["subject"] = {
                "role": manifest["role"],
                "version": manifest["source"]["version"],
                "exe_sha256": manifest["source"]["exe_sha256"],
            }
            S.save_run(manifest)
            if modal is None:
                raise S.NotEstablished(
                    "確認画面が出る前に二次起動されました。停止します。再走してください"
                )
            if launched_by != "explorer-user-double-click":
                raise S.NotEstablished(
                    f"二次起動の親がExplorerではありません(親: {parent_image})。実ダブルクリックではないため停止します"
                )
            exit_info = watch.wait(W05B_PEER_WAIT_S)
        finally:
            watch.close()
        self.session["peer_exit"] = {
            "at": now(),
            "returncode": exit_info["exit_code"],
            "state": exit_info["state"],
        }
        if exit_info["state"] != "exited" or exit_info["exit_code"] != 0:
            raise S.NotEstablished(f"二次起動が正常終了しませんでした: {exit_info}")
        fg_peer_done = S.foreground_info()
        monitor.set_phase("w05b-quiet")
        time.sleep(W05B_QUIET_S)
        fg_quiet_end = S.foreground_info()
        quiet_end = monitor.elapsed_now()
        obs = S.inspect(run, "after-peer")
        resumed = ocr_server.summary()
        self.session["ocr_after_peer"] = resumed
        self.step(
            "after-peer",
            windows=main_windows([primary, peer_item["pid"]]),
            foreground=obs["foreground"],
            owner_probe=obs["owner_probe"],
            foreground_before_peer=fg_before_peer,
        )
        w["foreground_peer_done"] = fg_peer_done
        w["foreground_quiet_end"] = fg_quiet_end
        summary = monitor.summary()
        self.session["input_monitor"] = summary
        ret = assess_w05b_return(
            summary,
            modal,
            pids,
            fg_before_peer=fg_before_peer,
            fg_peer_done=fg_peer_done,
            fg_quiet_end=fg_quiet_end,
            quiet_end_elapsed=quiet_end,
            launch_created_iso=peer_item["created_iso"],
        )
        if resumed["posts"] != 1 or resumed["completed"] or resumed["expired"]:
            ret["reasons"].append("request-not-held-after-peer")
            ret["verdict"] = "not-established"
        extra = find_copy_processes(exe_path, {primary, peer_item["pid"]})
        if extra:
            w["extra_copy_processes"] = extra
            ret["reasons"].append("extra-pagefolio-process")
            ret["verdict"] = "not-established"
        w["return_assessment"] = ret
        self.session["procedure_assessment"] = ret
        self.session["procedure_verdict"] = ret["verdict"]
        if ret["verdict"] != "clean":
            self.w05b_not_established(ret)
            return
        self.beep()
        w["beep_at"] = now()
        monitor.set_phase("w05b-answer")
        self.step("beep-return-verified")
        say("")
        say(
            "音が鳴りました。前面にある確認画面で「いいえ」を押してください"
            f"(要求の受信から約{W05B_NO_LATEST_S:.0f}秒以内。待機は延ばせません)。"
        )
        modal_hwnd = modal["hwnd"]
        ocr_hwnd = (w.get("ocr_window_before") or {}).get("hwnd")
        while window_exists(modal_hwnd):
            if seconds_since(posted) > W05B_NO_LATEST_S:
                raise S.NotEstablished(
                    "「いいえ」を期限内に確認できません。待機上限を延ばさず停止します"
                )
            time.sleep(0.05)
        w["modal_gone_at"] = now()
        w["no_elapsed_s"] = round(seconds_since(posted), 2)
        self.step("answered-no", windows=main_windows(pids))
        time.sleep(0.5)  # 「はい」ならOCR画面もこの直後に破棄される
        after_no = ocr_server.summary()
        self.session["ocr_after_no"] = after_no
        ocr_now = find_ocr_window(pids)
        w["after_no_windows"] = {
            "modal_exists": window_exists(modal_hwnd),
            "ocr_window": ocr_now,
        }
        if (
            ocr_now is None
            or ocr_now["hwnd"] != ocr_hwnd
            or after_no["completed"]
            or after_no["expired"]
        ):
            raise S.NotEstablished(
                "「いいえ」の後にOCR画面が残っていない、または要求が完了/期限切れです"
            )
        say(
            "OCR画面が閉じず処理中のままか、見てください。数秒後に同じ要求を解放します。"
        )
        time.sleep(
            max(
                0.0,
                min(W05B_KEEP_VIEW_S, W05B_RELEASE_LATEST_S - seconds_since(posted)),
            )
        )
        ocr_before_release = find_ocr_window(pids)
        w["ocr_window_before_release"] = ocr_before_release
        if ocr_before_release is None or ocr_before_release["hwnd"] != ocr_hwnd:
            raise S.NotEstablished("解放の前にOCR画面が閉じました")
        w["release_elapsed_s"] = round(seconds_since(posted), 2)
        self.step("ocr-release")
        ocr_server.release()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            summary_now = ocr_server.summary()
            if summary_now["completed"] or summary_now["expired"]:
                break
            time.sleep(0.05)
        ok, reasons = ocr_server.single_attempt_ok()
        self.session["ocr_completed"] = ocr_server.summary()
        if not ok:
            raise S.NotEstablished(f"OCR完了の通信記録が不成立: {reasons}")
        self.step("ocr-completed")
        time.sleep(
            1
        )  # 完了イベントをUIが表示する時間。成否は利用者の直接回答で判定する。
        self.beep()
        say("")
        say(
            "処理が完了しました。OCR画面の結果欄を見て、PowerShellへ戻り最初の質問に答えてください。"
        )
        answers = {}
        self.w05b_ask_result(answers)
        self.w05b_ask_rest(answers, exe=True)
        self.session["answers"] = answers
        self.session["outcome"] = "answered"
        if not self.selftest:
            self.session["user_close"] = {"requested_at": now()}
            p.enter(
                "OCR画面を先に閉じ、最後にPageFolio右上の×を押し、終了確認は「はい」を選んでください。"
                "PageFolioが閉じたらPowerShellへ戻ってEnterを押してください。"
            )
            ident = S.process_identity(record["pid"])
            closed = ident is None or not ident["alive"]
            self.session["user_close"].update(
                observed_at=now(), closed=closed, pid=record["pid"]
            )
            if not closed:
                say(
                    "PageFolioの終了はまだ確認できていません。続いて終了要求を送ります。"
                    "確認画面が出たら「はい」を押してください。最終判定はこの後の回収結果で行います。"
                )

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
            if exe:
                a["status_kept"] = p.ask(
                    "status_kept",
                    "追加確認: ヘッダーのステータス文字は最小化前と同じですか? 「同じ」「違う」「分からない」",
                )
        elif self.case == "W03":
            a["page_counts"] = p.ask(
                "page_counts",
                "PageFolio上で行ったUndo→Redo→Undo→Redoの各直後のページ数を、順番に数字4つで入力してください（区切り不要）。未実施ならその旨を入力",
            )
            a["orientations"] = p.ask(
                "orientations",
                "4回とも1ページ目は横向きでしたか? 「すべて横」「違った」「分からない」",
            )
            a["edit_visible_after_restore"] = p.ask(
                "edit_visible_after_restore",
                "自動で戻った直後、最初のCtrl+Zを押す前は、3ページで1ページ目が横向きでしたか? 「はい」「違う」「分からない」",
            )
            a["original_pdf_untouched"] = p.ask(
                "original_pdf_untouched",
                "編集したのは準備済みの合成PDFだけですか? 「合成PDFのみ」「別のPDFも使った」",
            )
        elif self.case == "W04":
            a["progress_shown"] = p.ask(
                "progress_shown",
                "自動で戻ったOCR画面では、処理中の表示が続いていましたか? 「はい」「いいえ」「分からない」",
            )
            a["completed_shown"] = p.ask(
                "completed_shown",
                "その後、結果欄に「PageFolio UAT 合成OCR結果」が表示されましたか? 「見えた」「見えない」",
            )
            a["summary_not_run"] = p.ask(
                "summary_not_run",
                "サマリは実行していませんか? 「していない」「実行した」",
            )
        elif self.cond in {"settings", "nested-settings"}:
            target = W02_TARGETS[self.cond]
            probe_key = "2" if exe else "x"
            a["foreground"] = p.ask(
                "foreground",
                "1/4 二次起動のあと、PageFolioの画面は前面に出ましたか? 「出た」「出ない」",
            )
            a["input"] = p.ask(
                "input",
                f"2/4 {target}に、キーボードで {probe_key} を1文字押しました。元の入力先に入りましたか?"
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
            if self.case == "W05a" and exe:
                a["inner_closed"] = p.ask(
                    "inner_closed",
                    "二次起動の前に内側のLLM設定を何も変更せず閉じ、外側のフォントサイズ13が残っているのを確認しましたか? 「はい」「いいえ」",
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

    def induce_procedure(self, pids, sleep=time.sleep):
        """診断のみ(--induce-switcher): 誘発手順を案内し、Enter を待ち、静止時間の不足分を自動で待って、成立を記録する。

        成立条件: PageFolio から離れて以後戻らず、切替UIが0.5秒以上前景にあり、PowerShell 等に落ち着いてから
        wait_s 秒以上静止している。成立しなくても二次起動は進める(その回は誘発の母数に数えない)。
        自動待機中も phase は awaiting-enter のままなので、PageFolio 内のクリックは手順汚染として検出される。
        """
        p = self.prompter
        monitor = self.monitor
        owned = set(pids)
        wait_s = float(self.diag.get("induce_wait_s") or INDUCE_WAIT_S)
        gate = self.session["diagnostics"]["induce"].setdefault("gate", [])
        for line in INDUCE_INSTRUCTIONS:
            say(line)
        if self.selftest:
            p.enter("(selftest)Enter")
            gate.append({"at": now(), "action": "selftest-skip"})
            self.session["induce_assessment"] = {
                "variant": INDUCE_VARIANT,
                "induced": False,
                "reasons": ["selftest"],
            }
            return
        trace = None
        for attempt in range(1, INDUCE_MAX_ATTEMPTS + 1):
            p.enter(
                f"手順 4 まで終えて(PowerShell で約{wait_s:.0f}秒待って)から Enter を押してください。この直後に二次起動します。"
            )
            trace = trace_departure(
                list(monitor.fg_transitions), owned, monitor.elapsed_now()
            )
            if not trace["pagefolio_foreground"]:
                break
            gate.append(
                {
                    "at": now(),
                    "attempt": attempt,
                    "action": "pagefolio-still-foreground",
                }
            )
            if attempt < INDUCE_MAX_ATTEMPTS:
                say(
                    "PageFolio がまだ前面です(PowerShell へ移れていません)。Alt を押したまま Tab を押して、"
                    "切替UIを約1秒見せて PowerShell へ移り、約20秒待ってから、もう一度 Enter を押してください。"
                )
        waits = 0
        while (
            trace is not None
            and not trace["pagefolio_foreground"]
            and trace["landing"] is not None
            and (trace["quiet_s"] or 0.0) < wait_s
            and waits < 4
        ):
            remaining = wait_s - (trace["quiet_s"] or 0.0)
            gate.append(
                {"at": now(), "action": "auto-wait", "seconds": round(remaining, 2)}
            )
            say(
                f"【自動待機】PowerShell へ移ってからの静止時間があと約{remaining:.0f}秒足りないため、このまま待ちます。"
                "何も触らないでください(マウスもキーボードも使わず、PageFolio もクリックしない)。"
            )
            sleep(remaining + 0.3)
            trace = trace_departure(
                list(monitor.fg_transitions), owned, monitor.elapsed_now()
            )
            waits += 1
        assessment = assess_induction(trace, wait_s)
        self.session["induce_assessment"] = assessment
        say("")
        if assessment["induced"]:
            say(
                f"== 誘発手順の判定: 成立 == 切替UIの表示 {assessment['switcher_visible_s']} 秒"
                f"({'・'.join(assessment['switcher_titles'] or [])})・静止 {assessment['quiet_s']} 秒。"
                "このまま二次起動します。"
            )
        else:
            say(
                f"== 誘発手順の判定: 不成立 == {induce_reasons_text(assessment['reasons'])}。"
                "この回は誘発の母数に数えません(二次起動はこのまま進めます)。次の回は手順どおりに行ってください。"
            )

    def diag_hold_if_failed(self, peer, sleep=time.sleep):
        """診断のみ: 二次起動が完了しなかった回は、利用者に何も触らせず一定時間、一次の状態を観測し続ける。

        失敗回で「利用者が窓を前面にする(活性化)まで止まったままか、自然に復帰するか」を見分けるため。
        """
        if not self.diag:
            return False
        hold = float(self.diag.get("hold_s") or 0)
        result = ((((peer or {}).get("json")) or {}).get("result") or {}).get("result")
        if hold <= 0 or result == "completed":
            return False
        monitor = self.monitor
        monitor.set_phase("diag-hold")
        self.step("diag-hold", seconds=hold, peer_result=result)
        say("")
        say(
            f"【診断】二次起動が完了しませんでした(結果: {result})。"
            f"PageFolioには一切触れず(クリックもAlt+Tabもしないで)、この画面のまま約{hold:.0f}秒お待ちください。"
            "一次の状態を観測し続けます。終わると次の案内が出ます。"
        )
        sleep(hold)
        monitor.set_phase("post-peer")
        return True

    def key_step(self):
        """W02の観察手順。settingsは文字入力(x)、thumb/previewはF5(モード切替)で行う。

        thumb/previewのCanvasは文字キーを受けず、利用者に効果が見えないためxは使わない。
        """
        p = self.prompter
        say("")
        if self.cond in {"settings", "nested-settings"}:
            probe_key = "2" if self.entry == "production-exe" else "x"
            say(
                f"PageFolioが前面に出ていたら、キーボードで {probe_key} を1文字だけ押してください(マウスは使わない)。"
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
        self.monitor.set_phase(
            "w03-preparation"
            if self.case in {"W03", "W04"}
            else "w05b-briefing"
            if self.case == "W05b"
            else "start-harness"
        )
        self.monitor.start()
        try:
            if self.case == "W05b":
                self._run_python_w05b()
            else:
                self._run_python()
        finally:
            self.close_monitor()
            self.close_ui_probe()

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

    # -- UIスレッド診断(診断OFFの行では何もしない) -----------------------------------
    def start_ui_probe(self, manifest):
        """harness start が返した一次PageFolioのpidを、読み取り専用で観測し始める。失敗しても行は続ける。"""
        if not self.diag:
            return
        try:
            D = diag_module()
            expected = manifest.get("expected_owner") or {}
            pid = expected.get("pid")
            if not pid:
                self.session["ui_thread_diag"] = {
                    "enabled": True,
                    "started": False,
                    "reason": "manifest.expected_owner.pid がない",
                }
                say(
                    "(UIスレッド診断: 一次のpidが分からないため観測しません。行は通常どおり続行します)"
                )
                return
            monitor = self.monitor
            fixture = manifest.get("fixture")
            self.probe = D.UiThreadProbe(
                D.Win32Native(),
                int(pid),
                expected_created=expected.get("process_created"),
                interval=(self.diag.get("interval_ms") or 100) / 1000,
                t0=monitor._t0,
                phase_fn=lambda: monitor._phase,
                wm_null=bool(self.diag.get("wm_null")),
                tail_path=(Path(fixture) / "stderr.log") if fixture else None,
                external_wake_ms=self.diag.get("external_wake_ms"),
            )
            self.probe.start()
            self.step(
                "ui-probe-started",
                pid=int(pid),
                wm_null=bool(self.diag.get("wm_null")),
                external_wake_ms=self.diag.get("external_wake_ms"),
            )
        except Exception as error:
            self.probe = None
            self.session["ui_thread_diag_error"] = repr(error)
            say(
                f"(UIスレッド診断を開始できませんでした: {error!r}。行は通常どおり続行します)"
            )

    def stop_ui_probe(self):
        if not self.diag or self.probe is None:
            return
        try:
            self.probe.stop()
        except Exception as error:
            self.session["ui_thread_diag_error"] = repr(error)

    def close_ui_probe(self):
        """観測を止め、一次/二次のstderrから要求の受理→処理のタイムラインを作り、UIスレッドの状態を集計する。"""
        if not self.diag:
            return
        try:
            D = diag_module()
            probe = self.probe
            if probe is None:
                self.session.setdefault(
                    "ui_thread_diag", {"enabled": True, "started": False}
                )
                return
            if probe.stopped_at is None:
                probe.stop()
            summary = probe.summary()
            fixture = self.session.get("harness_start_fixture")
            peer_json = (self.session.get("harness_peer") or {}).get("json") or {}

            def read_log(directory):
                try:
                    return (Path(directory) / "stderr.log").read_text(
                        encoding="utf-8", errors="replace"
                    )
                except Exception:
                    return ""

            primary_text = read_log(fixture) if fixture else ""
            peer_text = (
                read_log(peer_json["fixture"]) if peer_json.get("fixture") else ""
            )
            timeline = D.build_request_timeline(
                primary_text,
                peer_text,
                probe.anchors,
                live_events=probe.log_events,
                peer_result=peer_json.get("result"),
            )
            summary["request_timeline"] = timeline
            summary["request_window_analysis"] = D.analyze_request_window(
                probe.rows, probe.wm_null_log, timeline
            )
            peer_result = peer_json.get("result") or {}
            summary["frequency_record"] = {
                "peer_result": peer_result.get("result"),
                "peer_elapsed_ms": peer_result.get("elapsed"),
                "primary_late": timeline.get("late"),
                "stall_episodes": len(summary["stall_episodes"]),
                "longest_stall_s": max(
                    (
                        e["aggregate"].get("duration_s") or 0
                        for e in summary["stall_episodes"]
                    ),
                    default=0,
                ),
                "wm_null_probe": bool(self.diag.get("wm_null")),
                "external_wake_ms": self.diag.get("external_wake_ms"),
                "getmessage_runs": (summary.get("getmessage") or {}).get("runs"),
                "getmessage_stalls": (summary.get("getmessage") or {}).get("stalls"),
                "getmessage_max_length_ms": (summary.get("getmessage") or {}).get(
                    "max_length_ms"
                ),
            }
            self.session["ui_thread_diag"] = summary
            self.report_ui_probe(summary)
        except Exception as error:
            self.session["ui_thread_diag_error"] = repr(error)
            say(
                f"(UIスレッド診断の集計に失敗しました: {error!r}。観測データは可能な範囲で保存します)"
            )

    def report_ui_probe(self, summary):
        freq = summary.get("frequency_record") or {}
        say("")
        say("== UIスレッド診断(読み取り専用・受入証拠ではありません) ==")
        cost = summary.get("cost_ms") or {}
        say(
            f"  サンプル {summary.get('samples')} 件 / 最大の観測の空き {summary.get('max_gap_s')} 秒 / "
            f"1回のコスト 平均 {cost.get('avg')} ms・最大 {cost.get('max')} ms / "
            f"エラー {len(summary.get('errors') or [])} 種"
        )
        say(
            f"  二次起動(peer)の結果: {freq.get('peer_result')} / {freq.get('peer_elapsed_ms')} ms"
        )
        timeline = summary.get("request_timeline") or {}
        for request in timeline.get("requests", []):
            lateness = request.get("primary_lateness_ms")
            if lateness is None:
                say(f"  一次の要求処理: 記録なし(要求 {request.get('request_id')})")
            elif lateness > 0:
                say(
                    f"  一次の要求処理: 締切より {lateness} ms 遅れ"
                    f"(結果 {request.get('primary_terminal_result')})"
                )
            else:
                say(
                    f"  一次の要求処理: 締切内(締切の {-lateness} ms 前・結果 {request.get('primary_terminal_result')})"
                )
        say(
            f"  UIスレッドの無スケジュール区間(ctx切替が{diag_module().STALL_MIN_S}秒以上増えない): "
            f"{freq.get('stall_episodes')} 件 / 最長 {freq.get('longest_stall_s')} 秒"
        )
        for episode in summary.get("stall_episodes") or []:
            wait = episode.get("wait") or {}
            say(
                f"    - {episode.get('start_t')} から {episode['aggregate'].get('duration_s')} 秒"
                f"(phase={'/'.join(episode.get('phases') or [])}) 種別={wait.get('kind')}"
                f" 最後のシステムコール={wait.get('syscalls')}"
            )
            for target in wait.get("targets") or []:
                say(f"        待ち先: {target['text']}")
            if wait.get("others_ctx_delta"):
                say(f"        他スレッドのctx増分: {wait['others_ctx_delta']}")
        gm = summary.get("getmessage") or {}
        if gm.get("syscall_columns"):
            say(
                f"  GetMessage(タイムアウト無しの待機)の区間: {gm.get('runs')} 件 / 見えた行 {gm.get('rows')} / "
                f"最長 {gm.get('max_length_ms')} ms / 停止({gm.get('stall_threshold_ms')}ms 以上) {gm.get('stalls')} 件"
            )
        wake = summary.get("external_wake")
        if wake:
            interval = wake.get("interval_ms") or {}
            say(
                f"  外部見張り({wake.get('period_ms')}ms): 投稿 成功 {wake.get('posts_ok')} / 失敗 {wake.get('posts_failed')} / "
                f"宛先の確認で拒否 {wake.get('refused')} / 見送り {wake.get('skipped') or {}} / "
                f"投稿の最大間隔 {interval.get('max')} ms(周期の2倍超 {interval.get('over_2x_period')} 回)"
            )
            for failure in (wake.get("failures") or [])[:5]:
                say(
                    f"    - {failure.get('kind')}: {failure.get('error')} ({failure.get('t')} phase={failure.get('phase')})"
                )
            health = wake.get("health") or {}
            if health.get("healthy"):
                say(
                    "  外部見張りの動作: 期待どおり(投稿が流れ、拒否・失敗が少なく、間隔も開いていません)"
                )
            else:
                say(
                    f"  【警告】外部見張りが期待どおりに動いていません: {health.get('reasons')}。"
                    "この回は『見張りありの結果』として読まず、担当へ伝えてください(その回の集計には印が付きます)。"
                )
        induce = self.session.get("induce_assessment")
        if induce:
            if induce.get("induced"):
                say(
                    f"  誘発手順: 成立(切替UI {induce.get('switcher_visible_s')} 秒・静止 {induce.get('quiet_s')} 秒)"
                )
            else:
                say(
                    f"  誘発手順: 不成立({induce_reasons_text(induce.get('reasons'))})。この回は誘発の母数に数えません"
                )

    def _run_python(self):
        p = self.prompter
        monitor = self.monitor
        p.show(f"== {self.spec} (Python入口 {self.entry}) を開始します ==")
        say(
            "【入力監視】この行の間、マウスのボタン押下(位置・押下先の窓)と前面の窓の切替、"
            "PageFolioが前面にある間のキー押下(キー番号のみ)を記録します。入力内容や画面は記録しません。"
        )
        if self.diag:
            label = ""
            if self.diag.get("run_index"):
                label = f"(診断 {self.diag['run_index']}/{self.diag.get('run_total') or '?'} 回目)"
            say(
                f"【診断実行{label}】この回は W02/preview の二次起動の期限切れ(debug: w02-preview-peer-expired)の"
                "発生頻度を見る診断です(受入証拠ではありません)。隔離PageFolioのUIスレッドを外から"
                + (
                    "観測します"
                    if self.diag.get("external_wake_ms")
                    else "読み取りだけで観測します"
                )
                + "(クリック・キー送信・前景変更はしません)。"
            )
            if self.diag.get("wm_null"):
                say(
                    "  WM_NULL送信: ON(隔離PageFolioの窓へ、入力にならない無害なメッセージを約0.5秒ごとに1通送ります)"
                )
            elif self.diag.get("external_wake_ms"):
                say(
                    f"  外部見張り: ON({self.diag['external_wake_ms']}ms)"
                    "(この診断だけは眺めるだけではありません。このスクリプトが隔離PageFolioのUIスレッドへ、"
                    "何も起こさない空のメッセージ WM_NULL を投稿(PostThreadMessageW)し続けます。"
                    "クリック・キー送信・前景変更・SendMessageはしません)"
                )
            else:
                say(
                    "  WM_NULL送信: OFF(メッセージも送らず、完全に外から眺めるだけです)"
                )
        self.step("start-harness")
        start = harness(
            "start",
            "--case",
            {"W03": "pdf", "W04": "ocr", "W05a": "nested"}.get(self.case, self.cond),
        )
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
        if self.diag:
            self.session["harness_start_fixture"] = manifest.get("fixture")
            self.start_ui_probe(manifest)
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
                if self.case == "W03":
                    say(
                        "合成PDFの回転・複製・削除が準備済みです。3ページと1ページ目の回転を目で確認してください。"
                    )
                    say(
                        "音の後はPageFolioのまま、Ctrl+Z → Ctrl+Y → Ctrl+Z → Ctrl+Yを1回ずつ押します。各回のページ数と1ページ目の向きを確認し、4回終わってからPowerShellへ戻って答えてください。"
                    )
                elif self.case == "W04":
                    say(
                        "1ページ画像PDFのOCR処理が待機中です。次のEnterで二次起動します。戻ったOCR画面の処理中表示を見て、結果が出て音が鳴るまで操作せず待ってください。"
                    )
                elif self.case == "W05a":
                    say(
                        "確認するのは設定画面の最下部にある英字 unsaved input の欄です。フォントサイズ欄ではありません。"
                    )
                    say(
                        "先にこのPowerShellでEnterを押し、音が鳴るまで何も入力しないでください。自動復帰した欄の文字・選択を見て、音の後にxだけを1回押し、ux inputに変わったか確認します。Tabや画面内クリックはしません。"
                    )
                else:
                    say(
                        f"隔離PageFolioに操作先({W02_TARGETS[self.cond]})が準備済みです。"
                    )
                say("")
                if self.case in {"W03", "W04"}:
                    say(
                        "準備は済んでいます。編集せずPowerShellへ戻りEnterを押してください。Enter後から音が鳴るまでは操作しません。"
                    )
                else:
                    say(
                        "【重要】このあと二次起動します。Enter を押すまで、PageFolio の画面内は一切クリックしないでください"
                        "(ボタン・サムネイル・プレビュー・余白も含みます)。"
                    )
                if self.case in {"W03", "W04"}:
                    pass
                elif self.diag and self.diag.get("induce"):
                    say(
                        "(誘発手順の回です。下の【誘発手順】のとおりに、Alt+Tab の切替UIを使って PowerShell へ移ってください。"
                        "タイトルバーのクリックやタスクバーは使わないでください)"
                    )
                elif fg0.get("pid") in pids:
                    say(
                        "いまPageFolioが前面に出ています。この PowerShell へはタイトルバーをクリックするか Alt+Tab で戻ってください"
                        "(隠れているときはタスクバーの PowerShell のボタンでも構いません)。"
                    )
                else:
                    say(
                        "PageFolio以外が前面です。PageFolioの画面内はクリックせず、この PowerShell で Enter を押してください"
                        "(PowerShell へ戻るときはタイトルバーか Alt+Tab を使います)。"
                    )
                if self.case not in {"W03", "W04"}:
                    say(
                        "PageFolio内を1回押しただけで入力先が変わり、結果を製品の判定に使えなくなります(その回は再走になります)。"
                    )
            monitor.set_phase(
                "w03-preparation" if self.case in {"W03", "W04"} else "awaiting-enter"
            )
            if self.diag and self.diag.get("induce") and self.case == "W02":
                self.induce_procedure(pids)
            else:
                p.enter(
                    "準備ができたら Enter を押してください。この直後に二次起動します。"
                )
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
            self.diag_hold_if_failed(peer)
            if self.case == "W04":
                self.finish_python_ocr(manifest)
            if self.case in {"W03", "W05a"} and not self.selftest:
                import winsound

                if self.case == "W05a":
                    time.sleep(3)
                winsound.Beep(880, 350)
            if self.case in {"W02", "W05a"}:
                self.key_step()
            answers = self.questions(exe=False)
            self.session["answers"] = answers
            inspected = harness("inspect", "--run", run, timeout=60)
            self.session["harness_inspect"] = {
                k: inspected[k] for k in ("returncode", "stderr_tail", "json")
            }
            self.session["outcome"] = "answered"
        finally:
            self.stop_ui_probe()
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
        if self.case == "W05b":
            self.w05b_briefing(exe=True)
            p.enter(
                "案内を読み終えたら Enter を押してください。隔離copyを準備します(まだPageFolioは起動しません)。"
            )
        # 準備操作中は監視しない。無操作peer区間だけ下で読み取り専用監視する。
        self.session["input_monitor"] = {
            "enabled": False,
            "reason": "実EXE行は利用者がPageFolio内を操作する手順のため監視しない",
        }
        self.session["procedure_verdict"] = "not-monitored"
        # 初回起動は設定不存在のまま。終了時の正当な設定作成を、配布物の変更と分けて記録する。
        manifest = S.prepare(FINAL, self.case, overlays={S.SETTINGS_NAME: None})
        run = Path(manifest["run"])
        self.session["run"] = str(run)
        self.session["run_id"] = manifest["run_id"]
        self.session["binary_sha256"] = manifest["source"]["exe_sha256"]
        self.session["tree_sha256"] = manifest["source"]["tree_sha256"]
        self.session["environment"] = manifest["environment"]
        started = False
        exe_monitor = None
        ocr_server = None
        try:
            pdf = None
            if self.case in {"W04", "W05b"}:
                from tests.release_fake_ocr import FakeOcrServer

                ocr_server = FakeOcrServer(
                    mode="hold",
                    run_id=manifest["run_id"],
                    log_path=run / "evidence" / f"{self.case.lower()}-server.jsonl",
                    provider_timeout=120,
                    expected_pages=1,
                ).start()
                self.session["ocr_preparation"] = S.prepare_ocr_connection(
                    run, ocr_server
                )
                pdf = self.session["ocr_preparation"]["pdf"]
                self.session["fixture_pdf"] = pdf
            elif (self.case == "W02" and self.cond != "settings") or self.case == "W03":
                pdf = S.add_fixture_pdf(run, "edit-three-page")
                self.session["fixture_pdf"] = pdf
            if self.case == "W05b":
                dist = Path(manifest["copy"])
                say("")
                say(
                    "Explorerで次のフォルダを開き、PageFolio.exe が見える状態にしてください(まだダブルクリックしません)。"
                )
                say(f"   {dist}")
                if not self.selftest:
                    try:
                        subprocess.run(
                            ["clip"],
                            input=str(dist).encode("ascii", "ignore"),
                            check=False,
                            timeout=10,
                        )
                    except Exception as error:
                        say(f"(クリップボードへのコピーに失敗: {error!r})")
                p.enter(
                    "Explorerの準備ができたら Enter を押してください。隔離PageFolioを起動します(まだOCR要求は始まりません)。"
                )
            record = S.start(run, settle=5.0)
            started = True
            pids = [record["pid"]]
            self.session["primary"] = {
                k: record[k] for k in ("pid", "created", "image")
            }
            wins = main_windows(pids)
            self.step("started", windows=wins, foreground=S.foreground_info())
            if self.case == "W05b":
                self.exe_w05b(
                    run,
                    record,
                    ocr_server,
                    pids,
                    Path(manifest["copy"]) / "PageFolio.exe",
                )
                return
            say("")
            say("== PageFolio(配布EXEの隔離copy)を起動しました ==")
            say(
                "このW05aに限り内側のLLM設定を開いて閉じます。何も変更せず、プロバイダも変更しません。"
                if self.case == "W05a"
                else "【重要】LLM設定(🤖)は開かないでください。プロバイダも変更しないでください。"
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
                if self.cond == "zoomed":
                    p.enter(
                        "まだ最小化せず、PageFolioを表示したままPowerShellへ切り替えて Enter を押してください。"
                    )
                before = main_windows(pids)
                self.step(
                    "before-minimize", windows=before, foreground=S.foreground_info()
                )
                if (
                    len(before) != 1
                    or before[0]["iconic"]
                    or before[0]["zoomed"] != (self.cond == "zoomed")
                ):
                    raise S.NotEstablished(
                        "最小化前の元状態が確認できないため、二次起動せず停止します"
                    )
                say(
                    "元の位置を記録しました。画面とヘッダーを覚えたら最小化してください(タスクバーに残ります)。"
                )
                say(
                    "【観測中は操作しない】次のEnterを押したらマウスから手を離してください。"
                    "音が鳴るまで切替・クリック・キー入力をせず、鳴ってからPowerShellへ戻って回答してください。"
                )
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
                    raise S.NotEstablished(
                        "最小化が確認できないため、二次起動せず停止します"
                    )
            else:
                if self.cond in {"settings", "nested-settings"}:
                    say(
                        "1. 「⚙ 設定」を開き、「フォントサイズ」の数字を 13 にしてください(適用は押さない)。"
                    )
                    if self.case == "W05a":
                        say(
                            "内側の「LLM設定」を開き、何も変更せず閉じてください。外側の13が残っていることを確認してから、次の選択操作へ進みます。"
                        )
                    say(
                        "2. 数字の欄で End → Shiftを押しながら左矢印 を1回押し、末尾の 3 だけ選択します。"
                        "そのまま Alt+Tab でPowerShellへ戻ってください。"
                    )
                    say(
                        "3. 次のEnterで設定画面が自動で戻ったら、13と末尾3の選択を目で確認し、音が鳴るまで操作しません。"
                        "マウスを使わず 2 を1回押して12になるか確認してから、PowerShellへ戻って回答してください。"
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
                    if self.case == "W03":
                        say(
                            "2. 1ページ目を右回転し、2ページ目を複製し、3ページ目を削除してください。保存しません。"
                        )
                        say(
                            "3. 3ページになり、1ページ目が横向きになったことを覚えてPowerShellへ戻ります。"
                        )
                        say(
                            "音の後はPageFolioのまま、Ctrl+Z → Ctrl+Y → Ctrl+Z → Ctrl+Yを1回ずつ押し、各回のページ数と1ページ目の向きを確認します。4回終わってからPowerShellへ戻ってください。"
                        )
                    elif self.case == "W04":
                        say(
                            "2. 唯一のページを選び「現在ページをテキスト抽出」→「読み取り実行」を押してください。サマリは実行しません。"
                        )
                        say(
                            "3. 処理中になったらPowerShellへ戻りEnter。自動で戻ったOCR画面の処理中表示を見て、合成OCR結果が出て音が鳴るまで操作せず待ってください。"
                        )
                    elif self.cond == "thumb":
                        say("2. 左ペインのサムネイルでページを1つ選択してください。")
                    else:
                        say("2. 中央のプレビューをクリックして操作先にしてください。")
                say(
                    "【観測中は操作しない】次のEnter後はマウスから手を離し、音が鳴るまで切替・クリック・キー入力をしないでください。"
                    "音の後、指定されたキー入力と画面確認を終えてからPowerShellへ戻ります。"
                )
                p.enter(
                    "操作先ができたら Enter を押してください。この直後に二次起動します。"
                )
                target_windows = main_windows(pids)
                self.step(
                    "target-ready",
                    windows=target_windows,
                    foreground=S.foreground_info(),
                )
                if self.cond in {"settings", "nested-settings"} and not any(
                    w["title"] == "設定" and not w["iconic"] for w in target_windows
                ):
                    raise S.NotEstablished(
                        "設定画面が開いていないため、二次起動せず停止します。"
                        "次回は設定画面で13の末尾3を選択してからPowerShellのEnterを押してください。"
                    )
                if ocr_server:
                    self.session["ocr_before"] = ocr_server.summary()
                    pending = self.session["ocr_before"]
                    if (
                        pending["posts"] != 1
                        or pending["completed"]
                        or pending["expired"]
                    ):
                        raise S.NotEstablished(
                            "OCRの1件の要求が待機中でないため、二次起動せず停止します"
                        )
            fg0 = S.foreground_info()
            exe_monitor = InputMonitor()
            exe_monitor.set_owned_pids(pids)
            exe_monitor.set_phase("peer")
            exe_monitor.start()
            peer_children = []

            def remember_peer(argv, **kwargs):
                child = subprocess.Popen(argv, **kwargs)
                peer_children.append(child)
                return child

            peer = S.peer(run, popen=remember_peer)
            self.session["peer"] = {k: peer[k] for k in ("pid", "created", "image")}
            # 二次起動の実終了後に観測する。外部観測の上限4秒・製品期限は延ばさない。
            code = peer_children[0].wait(timeout=4)
            self.session["peer_exit"] = {"at": now(), "returncode": code}
            if code != 0:
                raise S.NotEstablished(f"二次起動が正常終了しませんでした: {code}")
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
            if exe_monitor is not None:
                exe_monitor.stop()
                summary = exe_monitor.summary()
                assessment = assess_exe_procedure(
                    summary, obs["foreground"].get("owned_by") == "primary"
                )
                self.session["input_monitor"] = summary
                self.session["procedure_assessment"] = assessment
                self.session["procedure_verdict"] = assessment["procedure_verdict"]
                if ocr_server:
                    if assessment["procedure_verdict"] != "clean":
                        raise S.NotEstablished("OCR復帰観測の無操作・実前景が不成立")
                    self.finish_exe_ocr(ocr_server)
                if not self.selftest:
                    import winsound

                    winsound.Beep(880, 350)
                say(
                    "観測が終わりました。PageFolioのままで指定のキー入力をしてからPowerShellへ戻ってください。"
                    if self.case in {"W02", "W03", "W05a"}
                    else "観測が終わりました。PowerShellへ戻って回答してください。"
                )
            if self.case in {"W02", "W05a"}:
                self.key_step()
            answers = self.questions(exe=True)
            self.session["answers"] = answers
            self.session["outcome"] = "answered"
            if (
                self.case in {"W02", "W03", "W04", "W05a"}
                and self.cond != "settings"
                and not self.selftest
            ):
                self.session["user_close"] = {"requested_at": now()}
                p.enter(
                    "設定・OCR画面がある場合は先に閉じ、最後にPageFolio右上の×を押し、終了確認は「はい」を選んでください。"
                    "PageFolioが閉じたらPowerShellへ戻ってEnterを押してください。"
                )
                ident = S.process_identity(record["pid"])
                closed = ident is None or not ident["alive"]
                self.session["user_close"].update(
                    observed_at=now(), closed=closed, pid=record["pid"]
                )
                if not closed:
                    say(
                        "PageFolioの終了はまだ確認できていません。続いて終了要求を送ります。"
                        "確認画面が出たら「はい」を押してください。最終判定はこの後の回収結果で行います。"
                    )
        finally:
            if exe_monitor is not None:
                exe_monitor.stop()
                self.session["input_monitor"] = exe_monitor.summary()
            elif self.case == "W05b" and self.monitor is not None:
                self.monitor.stop()
                self.session["input_monitor_final"] = self.monitor.summary()
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
            if ocr_server:
                ocr_server.stop()
                self.session["ocr_final"] = ocr_server.summary()
            if not self.selftest:
                say("")
                say("PageFolioの回収記録を保存しました。")

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

    def evidence_dir(self):
        """保存先。診断実行は受入証拠と混ざらないよう debug-* の別サブフォルダに分ける。"""
        sub = "selftest" if self.selftest else ""
        if self.diag:
            return EVIDENCE / diag_module().DEBUG_DIRNAME / sub
        return EVIDENCE / sub

    def save_diag_artifacts(self, out):
        """診断実行の付属物(サンプル全件・隔離runのログの写し)を、セッションJSONの隣へ保存する。"""
        if not self.diag:
            return
        D = diag_module()
        if self.probe is not None:
            try:
                side = out.with_name(out.stem + ".ui-samples.jsonl")
                info = D.write_samples_sidecar(side, self.probe)
                diag = self.session.setdefault("ui_thread_diag", {})
                diag["samples_file"] = info
            except Exception as error:
                self.session["ui_thread_diag_error"] = repr(error)
        try:
            logs = out.with_name(out.stem + "-run-logs")
            sources = {
                "primary": self.session.get("harness_start_fixture"),
                "peer": (
                    ((self.session.get("harness_peer") or {}).get("json")) or {}
                ).get("fixture"),
            }
            copied = []
            for role, directory in sources.items():
                if not directory or not Path(directory).is_dir():
                    continue
                for name in (
                    "stderr.log",
                    "stdout.log",
                    "traceback.log",
                    "result.json",
                    "focus-result.json",
                    "resource-audit.json",
                ):
                    src = Path(directory) / name
                    if src.is_file():
                        logs.mkdir(parents=True, exist_ok=True)
                        dst = logs / f"{role}-{name}"
                        dst.write_bytes(src.read_bytes())
                        copied.append(dst.name)
            self.session["run_logs_copy"] = {
                "directory": logs.name if copied else None,
                "files": copied,
                "note": "隔離runの原本は .planning/tmp/ にも残る。ここはその写し(診断実行ごとに別ディレクトリ)",
            }
        except Exception as error:
            self.session["run_logs_copy"] = {"error": repr(error)}

    def finish(self):
        self.session["finished_at"] = now()
        self.session["raw_inputs"] = self.prompter.inputs
        self.session["composed_answer"] = self.compose_answer()
        out_dir = self.evidence_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = self.spec.replace("/", "_").replace("@", "_at_")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = out_dir / f"{slug}-{stamp}.json"
        serial = 1
        while out.exists():  # 既存の記録(原本)を上書きしない。再走は常に別ファイル
            serial += 1
            out = out_dir / f"{slug}-{stamp}-{serial}.json"
        self.save_diag_artifacts(out)
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
        self.switch_down = set()  # 前景に関係なく押されている切替キー(alt / tab / win)
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

    def switch_keys(self):
        return set(self.switch_down)


class _NoSwitchSampler(_FakeSampler):
    """切替キーの捕捉を持たない旧形の観測面(捕捉が無い状態を clean にしないことの確認用)。"""

    switch_keys = None


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

    m, s, c = new_monitor(phase="w03-preparation")
    click(m, s, c, pf)
    check(
        "W03準備中のクリックは復帰観測を汚染しない",
        verdict(m)["procedure_verdict"] == "clean",
    )
    m.set_phase("peer")
    click(m, s, c, pf)
    check(
        "W03もpeer中のクリックは拒否", verdict(m)["procedure_verdict"] == "contaminated"
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
    m, s, c = new_monitor(phase="peer")
    tick(m, c)
    check(
        "実EXE無操作で実前景一致",
        assess_exe_procedure(m.summary(), True)["focus_attribution"]
        == "product-focus-ok",
    )
    check(
        "実EXE無操作で実前景不一致は失敗候補",
        assess_exe_procedure(m.summary(), False)["focus_attribution"]
        == "product-focus-failure-candidate",
    )
    click(m, s, c, under=ps)
    check(
        "実EXE観測中のPowerShellクリックは手順汚染",
        assess_exe_procedure(m.summary(), False)["procedure_verdict"] == "contaminated",
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

    say(
        "-- 切替キー(Alt/Tab/Win)の捕捉: debug phase06-w05b-alttab-blindspot の再現と修正 --"
    )
    m, s, c = new_monitor()  # 基準線: PowerShell(非PageFolio)が前景
    s.switch_down = {"alt"}
    tick(m, c)
    s.switch_down = {"alt", "tab"}
    tick(m, c)
    s.switch_down = set()
    tick(m, c)
    sk = m.summary()["switch_key_events"]
    check(
        "再現: PowerShellが前景の間のAlt+Tabは、従来の key_events には入らない(構造上の盲点)",
        not m.key_events,
    )
    check(
        "修正: 同じAlt+Tabを switch_key_events に押下エッジとして残す(前景に関係なく・Alt→Tabの順・組合せ名つき)",
        [(e["key"], e["kind"], e["combo"]) for e in sk]
        == [("alt", "down", "alt"), ("tab", "down", "alt-tab")]
        and all(e["foreground"]["pid"] == 111 for e in sk)
        and all(e["phase"] == "awaiting-enter" for e in sk),
        str(sk),
    )
    check(
        "switch_key_capture=true・サンプル数が記録され、離上は押下エッジに数えない",
        m.summary()["switch_key_capture"] is True
        and m.summary()["switch_key_samples"] == m.summary()["samples"]
        and len(sk) == 2,
    )
    check(
        "手順汚染判定(assess_procedure)は不変: awaiting-enter のAlt+Tabは指示された操作なので clean のまま",
        verdict(m)["procedure_verdict"] == "clean",
    )

    m, s, c = new_monitor()
    s.fg = 200
    tick(m, c)  # PageFolioが前面
    s.keys, s.alt, s.switch_down = {0x09}, True, {"alt", "tab"}
    tick(m, c)
    check(
        "PageFolio前面中のAlt+Tabも switch_key_events に残り、key_events(alt除外)は従来どおり空",
        not m.key_events
        and [e["combo"] for e in m.switch_key_events] == ["alt-tab", "alt-tab"],
        str(m.switch_key_events),
    )

    m, s, c = new_monitor()
    for down in ({"win"}, {"win", "tab"}, set()):
        s.switch_down = down
        tick(m, c)
    check(
        "Winキー・Win+Tabも押下エッジに残す",
        [(e["key"], e["combo"]) for e in m.switch_key_events]
        == [("win", "win"), ("tab", "win-tab")],
        str(m.switch_key_events),
    )

    m, s, c = new_monitor()
    for down in ({"alt"}, {"alt"}, {"alt"}, set(), {"alt"}):
        s.switch_down = down
        tick(m, c)
    check(
        "押し続けは1回・離して再度押せば2回(エッジのみ)",
        [e["kind"] for e in m.switch_key_events] == ["down", "down"],
        str(m.switch_key_events),
    )

    s2 = _FakeSampler(windows)
    s2.switch_down = {"alt"}
    c2 = _FakeClock()
    m = InputMonitor(s2, clock=c2)
    m.set_owned_pids([222])
    m.set_phase("awaiting-enter")
    m.poll_once()
    s2.switch_down = set()
    tick(m, c2)
    check(
        "監視開始時に押下中のAltは held-at-start(押下エッジに数えない)",
        [(e["kind"], e["key"]) for e in m.switch_key_events]
        == [("held-at-start", "alt")],
    )

    m, s, c = new_monitor()
    s.switch_down = {"alt"}
    tick(m, c)
    m.set_phase("peer")
    tick(m, c)
    tick(m, c)
    held_events = [e for e in m.switch_key_events if e["kind"] == "held-at-phase-start"]
    check(
        "phase境界(awaiting-enter→peer)をまたいで押され続けたAltは、peerの held-at-phase-start として1回残る",
        len(held_events) == 1
        and held_events[0]["phase"] == "peer"
        and held_events[0]["key"] == "alt",
        str(m.switch_key_events),
    )

    m = InputMonitor(_NoSwitchSampler(windows), clock=_FakeClock())
    m.set_owned_pids([222])
    m.set_phase("awaiting-enter")
    m.poll_once()
    tick(m, m.clock)
    check(
        "切替キーの捕捉を持たない旧形のsamplerは例外にせず、switch_key_capture=false(捕捉無しをcleanにしない前提)",
        m.summary()["switch_key_capture"] is False
        and m.summary()["switch_key_events"] == []
        and not m.errors,
    )

    class _SwitchFails(_FakeSampler):
        def switch_keys(self):
            raise RuntimeError("fake switch_keys failure")

    m = InputMonitor(_SwitchFails(windows), clock=_FakeClock())
    m.set_owned_pids([222])
    m.set_phase("awaiting-enter")
    m.poll_once()
    check(
        "switch_keys の失敗は errors に残り monitor-incomplete",
        bool(m.errors) and verdict(m)["procedure_verdict"] == "monitor-incomplete",
    )

    m, s, c = new_monitor()
    m.switch_key_events = [{}] * MONITOR_EVENT_CAP
    s.switch_down = {"alt"}
    tick(m, c)
    check(
        "switch_key_events が上限に達したら truncated(清浄を保証しない)",
        m.truncated and verdict(m)["procedure_verdict"] == "monitor-incomplete",
    )

    # 読み取り専用の静的確認: 監視の3クラスが入力・前景を変えるAPIを使わない(GetAsyncKeyStateは使う)
    forbidden = {
        "SendInput",
        "SetCursorPos",
        "SetForegroundWindow",
        "keybd_event",
        "mouse_event",
        "SetWindowsHookEx",
        "SetWindowsHookExW",
        "BlockInput",
        "AttachThreadInput",
        "SendMessageW",
        "PostMessageW",
    }
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    used = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in (
            "Win32Sampler",
            "EdgeTracker",
            "InputMonitor",
        ):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name):
                    used.add(sub.id)
                elif isinstance(sub, ast.Attribute):
                    used.add(sub.attr)
    check(
        "静的確認: 監視(Win32Sampler/EdgeTracker/InputMonitor)は入力注入・前景変更APIを使わない",
        not (forbidden & used) and "GetAsyncKeyState" in used,
        str(sorted(forbidden & used)),
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
    check(
        "実API: switch_keys が alt/tab/win の部分集合を返す(押下は作らない)",
        set(sampler.switch_keys()) <= set(SWITCH_KEY_VKS),
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
        "実監視: 切替キー(Alt/Tab/Win)の捕捉が有効で、全サンプルで読めている(押下は作らない)",
        real["switch_key_capture"] is True
        and real["switch_key_samples"] == real["samples"],
        f"capture={real['switch_key_capture']} switch_samples={real['switch_key_samples']} samples={real['samples']}",
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


# ---------------------------------------------------------------------------
# W05b判定の機構確認(--check-w05b)
# ---------------------------------------------------------------------------
def check_w05b():
    """W05bの『自動復帰』判定の機構確認。窓も入力も作らず、前景も変えない。

    (1) 偽サンプラ+純関数 assess_w05b_return で、手動切替・押下・キー・復帰せず・監視の抜けを区別できるか。
    (2) 実APIは読み取りだけ: Toolhelpの列挙に自分自身が見えること、自分で起動した使い捨てPythonの
        終了コードを、検出直後に開いたhandleで読めること(起動した子は自分で回収する)。
    SendInput / SetForegroundWindow / 製品の起動は一切しない。
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
    chat = {"hwnd": 500, "pid": 444, "title": "Chat", "class": "Chrome"}
    modal = {"hwnd": 400, "pid": 222, "title": "確認", "class": MODAL_CLASS}
    # 実機(235255Z)と同じ形の経由窓: explorer.exe(pid 9)の ForegroundStaging と タスクの切り替え(Alt+Tab)
    stage = {"hwnd": 600, "pid": 9, "title": "", "class": "ForegroundStaging"}
    switcher = {
        "hwnd": 700,
        "pid": 9,
        "title": "タスクの切り替え",
        "class": "XamlExplorerHostIslandWindow",
    }
    windows = {100: ps, 200: pf, 400: modal, 500: chat, 600: stage, 700: switcher}

    def new_monitor(sampler_cls=_FakeSampler):
        sampler = sampler_cls(windows)
        clock = _FakeClock()
        monitor = InputMonitor(sampler, clock=clock)
        monitor.set_owned_pids([222])
        monitor.set_phase("awaiting-enter")
        monitor.poll_once()  # 基準線: PowerShellが前景
        return monitor, sampler, clock

    def tick(monitor, clock, n=1, dt=0.05):
        for _ in range(n):
            clock.advance(dt)
            monitor.poll_once()

    def assess(monitor, fg_before=ps, fg_done=modal, fg_end=modal, **kwargs):
        return assess_w05b_return(
            monitor.summary(),
            modal,
            [222],
            fg_before_peer=fg_before,
            fg_peer_done=fg_done,
            fg_quiet_end=fg_end,
            quiet_end_elapsed=monitor.elapsed_now(),
            **kwargs,
        )

    def scenario(
        after_return=None,
        press=None,
        keys=None,
        via=(),
        pulses=(),
        excursion=(),
        sampler_cls=_FakeSampler,
    ):
        """peer開始 → 自動復帰 → 観測。after_return/press/keys で逸脱を差し込む。

        via: 復帰の前に1サンプルずつ経由する窓のhwnd列(Alt+Tabなら [600, 700]=中継窓→切替UI)。
        pulses: peer開始直後に1サンプルずつ与える切替キーの押下集合の列(Alt+Tab なら
          [{"alt"}, {"alt", "tab"}, set()])。excursion: 復帰後に1サンプルずつ経由する窓のhwnd列。
        """
        m, s, c = new_monitor(sampler_cls)
        m.set_phase("peer")
        tick(m, c, 2)
        for down in pulses:
            s.switch_down = set(down)
            tick(m, c, 1)
        for hwnd_via in via:
            s.fg = hwnd_via
            tick(m, c, 1)
        s.fg = 400  # 自動復帰
        tick(m, c, 2)
        m.set_phase("w05b-quiet")
        tick(m, c, 4)
        if keys:
            s.keys = set(keys)
            tick(m, c, 2)
            s.keys = set()
        if press:
            s.under, s.pos = press, [10, 10]
            s.btn["left"] = True
            tick(m, c, 2)
            s.btn["left"] = False
            tick(m, c, 1)
        if after_return is not None:
            s.fg = after_return
            tick(m, c, 3)
        for hwnd_exc in excursion:
            s.fg = hwnd_exc
            tick(m, c, 1)
        if excursion:
            tick(m, c, 2)
        return m, s, c

    say("== W05b判定の機構確認(窓も入力も作らない) ==")
    say("-- 偽サンプラ・純関数 --")
    m, s, c = scenario()
    a = assess(m)
    check(
        "無操作で同一HWND/PIDへ自動復帰: clean",
        a["verdict"] == "clean" and not a["reasons"],
        a["reasons"],
    )
    check(
        "復帰時刻と無操作秒数を記録",
        a["returned_at_elapsed_s"] is not None
        and (a["unattended_seconds_after_return"] or 0) > 0.2,
        a,
    )

    m, s, c = scenario(after_return=500)
    a = assess(m, fg_end=chat)
    check(
        "復帰後に別窓へ切替(手動切替): 不成立",
        a["verdict"] == "not-established"
        and "foreground-left-modal-after-return" in a["reasons"]
        and "foreground-not-modal-at-quiet-end" in a["reasons"],
        a["reasons"],
    )

    m, s, c = new_monitor()
    m.set_phase("peer")
    tick(m, c, 3)
    m.set_phase("w05b-quiet")
    tick(m, c, 3)
    a = assess(m, fg_done=ps, fg_end=ps)
    check(
        "前景がPowerShellのまま(復帰せず): 不成立",
        a["verdict"] == "not-established"
        and "no-foreground-transition-to-modal" in a["reasons"],
        a["reasons"],
    )

    m, s, c = new_monitor()
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("peer")
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 2)
    a = assess(m, fg_before=modal)
    check(
        "二次起動の前から確認画面が前景: 自動復帰を示せず不成立",
        a["verdict"] == "not-established"
        and "modal-was-already-foreground-before-peer" in a["reasons"],
        a["reasons"],
    )

    m, s, c = scenario(press=chat)
    a = assess(m)
    check(
        "観測中に他の窓でもマウス押下: 不成立",
        a["verdict"] == "not-established"
        and "mouse-press-during-observation" in a["reasons"]
        and len(a["mouse_presses_during_observation"]) == 1,
        a["reasons"],
    )

    m, s, c = scenario(press=modal)
    a = assess(m)
    check(
        "観測中に確認画面上で押下(「いいえ」を早押し): 不成立",
        a["verdict"] == "not-established"
        and "mouse-press-during-observation" in a["reasons"],
        a["reasons"],
    )

    m, s, c = scenario(keys={0x4E})
    a = assess(m)
    check(
        "観測中に確認画面前面でキー押下: 不成立",
        a["verdict"] == "not-established" and "key-during-observation" in a["reasons"],
        a["reasons"],
    )

    m, s, c = scenario()
    a = assess(m, fg_done=chat)
    check(
        "二次起動直後の実前景が確認画面でない: 不成立",
        a["verdict"] == "not-established"
        and "foreground-not-modal-at-peer-done" in a["reasons"],
        a["reasons"],
    )

    m, s, c = scenario()
    s.fail = True
    tick(m, c, 2)
    a = assess(m)
    check(
        "入力監視にerror: 清浄を保証せず不成立",
        a["verdict"] == "not-established" and "monitor-incomplete" in a["reasons"],
        a["reasons"],
    )

    say(
        "-- 手動Alt+Tab(タスク切替UI経由)の回帰: debug phase06-w05b-alttab-blindspot --"
    )
    # 20261030T235255Z の形: Enter(peer開始)の直後に PowerShell→ForegroundStaging→タスクの切り替え→確認。
    # 修正前は、返却先が同一HWND・終端前景が確認画面・押下/キー無しなので、この形が clean になっていた。
    m, s, c = scenario(via=[600, 700])
    a = assess(m)
    check(
        "回帰(235255Z): Alt+Tab(中継窓→切替UI)経由で確認画面へ戻る: キー記録が空でも経由窓だけで不成立(修正前は他の全条件が満たされて clean)",
        a["verdict"] == "not-established"
        and "task-switcher-during-observation" in a["reasons"]
        and a["returned_via_task_switcher"] is True
        and a["returned_transition"]["from"]["class"] == "XamlExplorerHostIslandWindow"
        and len(a["task_switcher_transitions_during_observation"]) == 3,
        str(a["reasons"]),
    )
    m, s, c = scenario(via=[600, 700], pulses=[{"alt"}, {"alt", "tab"}, set()])
    a = assess(m)
    check(
        "回帰(235255Z・キー記録あり): 経由窓と切替キーの押下エッジの両方で不成立(捕捉は有効なので blind にはならない)",
        a["verdict"] == "not-established"
        and {"task-switcher-during-observation", "switch-key-during-observation"}
        <= set(a["reasons"])
        and "switch-key-capture-blind" not in a["reasons"],
        str(a["reasons"]),
    )
    m, s, c = scenario(via=[600, 700])
    a = assess(m)
    check(
        "回帰(235255Z): 経由した窓の記録(中継窓→切替UI→確認の3遷移)を判定結果に残す",
        [
            (t["from"]["class"], t["to"]["class"])
            for t in a["task_switcher_transitions_during_observation"]
        ]
        == [
            ("Console", "ForegroundStaging"),
            ("ForegroundStaging", "XamlExplorerHostIslandWindow"),
            ("XamlExplorerHostIslandWindow", MODAL_CLASS),
        ],
        str(a["task_switcher_transitions_during_observation"]),
    )
    # 20261030T235905Z の形(対照): 指示された Alt+Tab は Enter の前(awaiting-enter)に済ませ、
    # peer では PowerShell→確認 の直接遷移。キー(Alt/Tab)も awaiting-enter にだけ有る。
    m, s, c = new_monitor()
    for down in ({"alt"}, {"alt", "tab"}, set()):
        s.switch_down = set(down)
        tick(m, c, 1)
    for hwnd_setup in (600, 700, 600, 100):
        s.fg = hwnd_setup
        tick(m, c, 1)
    tick(m, c, 4)
    m.set_phase("peer")
    tick(m, c, 2)
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 4)
    a = assess(m)
    check(
        "対照(235905Z): Enter前(awaiting-enter)の Alt+Tab(切替UI経由で PowerShell へ移る指示操作)は数えず、peerでの直接復帰は clean",
        a["verdict"] == "clean"
        and a["reasons"] == []
        and a["returned_via_task_switcher"] is False
        and a["task_switcher_transitions_during_observation"] == []
        and a["switch_key_events_during_observation"] == []
        and a["switch_key_capture"] is True
        and len(m.switch_key_events) == 2,
        str(a["reasons"]),
    )
    # 20261031T000340Z の形: 直接遷移で復帰したあと、観測中に 確認→中継窓→切替UI→中継窓→PowerShell。
    m, s, c = scenario(excursion=[600, 700, 600, 100])
    a = assess(m, fg_end=ps)
    check(
        "対照(000340Z): 直接復帰のあと観測中に切替UIを経由して PowerShell へ移る: 不成立。従来の理由を保ち、経由窓の理由が加わる",
        a["verdict"] == "not-established"
        and {
            "foreground-left-modal-after-return",
            "foreground-not-modal-at-quiet-end",
            "task-switcher-during-observation",
        }
        <= set(a["reasons"])
        and a["returned_via_task_switcher"] is False,
        str(a["reasons"]),
    )
    # 復帰の前に切替UIを見せて PowerShell に戻り、そのあとで確認画面へ直接戻る形(手動切替が混じる)
    m, s, c = scenario(via=[600, 700, 600, 100])
    a = assess(m)
    check(
        "復帰の前に切替UIを経由して PowerShell へ戻った回(直接復帰を伴っても): 不成立",
        a["verdict"] == "not-established"
        and "task-switcher-during-observation" in a["reasons"]
        and a["returned_via_task_switcher"] is False,
        str(a["reasons"]),
    )
    # 自己検証: 指示された Alt+Tab で切替UIが出たのに Alt/Tab/Win の押下が1つも記録されない(=捕捉が効いていない)
    # セッションは、peerが直接復帰でも clean にしない。
    m, s, c = new_monitor()
    for hwnd_setup in (600, 700, 600, 100):
        s.fg = hwnd_setup
        tick(m, c, 1)
    tick(m, c, 4)
    m.set_phase("peer")
    tick(m, c, 2)
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 4)
    a = assess(m)
    check(
        "自己検証: 切替UIが出たセッションでキー押下が1つも無い(捕捉が盲目)なら、直接復帰でも switch-key-capture-blind で不成立",
        a["verdict"] == "not-established"
        and a["reasons"] == ["switch-key-capture-blind"],
        str(a["reasons"]),
    )
    # phaseをまたぐ形: 中継窓→切替UI が awaiting-enter、切替UI→確認 が peer(first.from が切替UI)
    m, s, c = new_monitor()
    for down in (
        {"alt"},
        {"alt", "tab"},
        set(),
    ):  # 指示された Alt+Tab のキー(捕捉は有効)
        s.switch_down = set(down)
        tick(m, c, 1)
    s.fg = 600
    tick(m, c, 1)
    s.fg = 700
    tick(m, c, 1)
    m.set_phase("peer")
    tick(m, c, 1)
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 4)
    a = assess(m)
    check(
        "phaseをまたぐ Alt+Tab(切替UI表示が awaiting-enter、確認への到着が peer): 到着遷移の from が切替UIなので不成立",
        a["verdict"] == "not-established"
        and a["returned_via_task_switcher"] is True
        and a["reasons"] == ["task-switcher-during-observation"]
        and len(a["task_switcher_transitions_during_observation"]) == 1,
        str(a["reasons"]),
    )
    # 切替キーの押下エッジ(前景遷移に切替UIが出ない短押しでも、Altが押された事実で落とす)
    m, s, c = scenario(pulses=[{"alt"}, {"alt", "tab"}, set()], via=[999])
    a = assess(m)
    check(
        "素早いAlt+Tab(切替UIを出さず前景がnullを一瞬挟んで復帰): 切替キーの押下エッジで不成立",
        a["verdict"] == "not-established"
        and "switch-key-during-observation" in a["reasons"]
        and "task-switcher-during-observation" not in a["reasons"]
        and [e["combo"] for e in a["switch_key_events_during_observation"]]
        == ["alt", "alt-tab"],
        str(a["reasons"]),
    )
    m, s, c = scenario(pulses=[{"alt"}, set()])
    a = assess(m)
    check(
        "Altだけの押下でも観測中は不成立(Alt+Esc等、切替UIを出さない前景操作を含む)",
        a["verdict"] == "not-established"
        and a["reasons"] == ["switch-key-during-observation"],
        str(a["reasons"]),
    )
    m, s, c = scenario(pulses=[{"win"}, {"win", "tab"}, set()])
    a = assess(m)
    check(
        "Winキー・Win+Tabの押下でも観測中は不成立",
        a["verdict"] == "not-established"
        and [e["combo"] for e in a["switch_key_events_during_observation"]]
        == ["win", "win-tab"],
        str(a["reasons"]),
    )
    # Altを押したまま Enter → 観測へ入った(phase境界をまたぐ)形
    m, s, c = new_monitor()
    s.switch_down = {"alt"}
    tick(m, c, 2)
    m.set_phase("peer")
    tick(m, c, 2)
    s.switch_down = set()
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 4)
    a = assess(m)
    check(
        "Altを押したまま観測へ入った(phase境界をまたぐ押下)は held-at-phase-start として不成立",
        a["verdict"] == "not-established"
        and [e["kind"] for e in a["switch_key_events_during_observation"]]
        == ["held-at-phase-start"],
        str(a["reasons"]),
    )
    # 観測のあと(w05b-answer: 音の後の「いいえ」を押す場面)の切替キーは観測区間に数えない
    m, s, c = scenario()
    m.set_phase("w05b-answer")
    s.switch_down = {"alt", "tab"}
    tick(m, c, 2)
    a = assess(m)
    check(
        "観測が終わった後(w05b-answer)の Alt+Tab は判定に影響しない",
        a["verdict"] == "clean" and a["switch_key_events_during_observation"] == [],
        str(a["reasons"]),
    )
    # 切替キーの捕捉が無い(旧形の監視)・summaryにcaptureが無い記録は clean にしない
    m, s, c = scenario(sampler_cls=_NoSwitchSampler)
    a = assess(m)
    check(
        "切替キーの捕捉が無い監視は、直接復帰でも clean にしない(switch-key-capture-missing)",
        a["verdict"] == "not-established"
        and a["reasons"] == ["switch-key-capture-missing"]
        and a["switch_key_capture"] is False,
        str(a["reasons"]),
    )
    m, s, c = scenario()
    legacy = m.summary()
    legacy.pop("switch_key_capture")
    legacy.pop("switch_key_events")
    legacy.pop("switch_key_samples")
    a = assess_w05b_return(
        legacy,
        modal,
        [222],
        fg_before_peer=ps,
        fg_peer_done=modal,
        fg_quiet_end=modal,
        quiet_end_elapsed=m.elapsed_now(),
    )
    check(
        "切替キー項目の無い旧形のsummary(Alt+Tab捕捉の導入前の記録)は clean にならない",
        a["verdict"] == "not-established"
        and "switch-key-capture-missing" in a["reasons"],
        str(a["reasons"]),
    )

    # 実記録の再生(読み取りのみ・証拠は書き換えない): 3 run の前景遷移・入力記録を判定に通す。
    #  - 記録そのものは Alt+Tab 捕捉の導入前なので switch-key-capture-missing になる(clean にならない)
    #  - 経由窓の判定だけを見るため、捕捉済み(イベント無し)と仮定した複製でも判定する
    sessions = {
        "235255Z": "W05b_ocr-close-confirm_at_script-20261030T235255Z.json",
        "235905Z": "W05b_ocr-close-confirm_at_script-20261030T235905Z.json",
        "000340Z": "W05b_ocr-close-confirm_at_script-20261031T000340Z.json",
    }
    replay = {}
    for label, file_name in sessions.items():
        path = EVIDENCE / file_name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        recorded = data["w05b"]["return_assessment"]
        replay[label] = (data, recorded)
    if len(replay) < len(sessions):
        check("実記録の再生(W05b 3 run): 証拠が無い環境ではskip", True)
    else:

        def replay_assess(label, capture):
            data, recorded = replay[label]
            summary = dict(data["input_monitor"])
            if capture:
                # 捕捉が有効だったと仮定した複製: 指示された Alt+Tab(awaiting-enter で PowerShell へ移る操作)の
                # Alt 押下エッジだけを1件足す。観測区間(peer, w05b-quiet)にはキー記録を足さない。
                setup_alt = {
                    "phase": "awaiting-enter",
                    "kind": "down",
                    "key": "alt",
                    "combo": "alt",
                }
                summary.update(switch_key_capture=True, switch_key_events=[setup_alt])
            w = data["w05b"]
            return assess_w05b_return(
                summary,
                w["modal_before"],
                summary["owned_pids"],
                fg_before_peer=w["foreground_before_peer"],
                fg_peer_done=w["foreground_peer_done"],
                fg_quiet_end=w["foreground_quiet_end"],
                quiet_end_elapsed=recorded["observation_end_elapsed_s"],
            )

        recorded_verdicts = {k: v[1]["verdict"] for k, v in replay.items()}
        check(
            "実記録の再生: 記録時の判定(修正前)は 235255Z=clean(誤判定)・235905Z=clean・000340Z=not-established",
            recorded_verdicts
            == {
                "235255Z": "clean",
                "235905Z": "clean",
                "000340Z": "not-established",
            },
            str(recorded_verdicts),
        )
        check(
            "実記録の再生: 3 run とも記録は Alt+Tab 捕捉の導入前なので、そのままでは clean にならない",
            all(
                "switch-key-capture-missing" in replay_assess(k, False)["reasons"]
                for k in replay
            ),
        )
        a = replay_assess("235255Z", True)
        check(
            "実記録の再生(235255Z・捕捉済みと仮定): 経由窓だけで不成立になる(修正前は clean だった)",
            a["verdict"] == "not-established"
            and a["reasons"] == ["task-switcher-during-observation"]
            and a["returned_via_task_switcher"] is True
            and a["returned_transition"]["from"]["class"]
            == "XamlExplorerHostIslandWindow",
            str(a["reasons"]),
        )
        a = replay_assess("235905Z", True)
        check(
            "実記録の再生(235905Z・捕捉済みと仮定): 直接遷移は記録どおり clean のまま",
            a["verdict"] == "clean" and a["reasons"] == [],
            str(a["reasons"]),
        )
        a = replay_assess("000340Z", True)
        check(
            "実記録の再生(000340Z・捕捉済みと仮定): 記録どおり不成立。従来の理由を保ち、経由窓の理由が加わる",
            a["verdict"] == "not-established"
            and set(replay["000340Z"][1]["reasons"]) <= set(a["reasons"])
            and "task-switcher-during-observation" in a["reasons"],
            str(a["reasons"]),
        )

    # 配布版: 二次processの生成時刻の直後までの押下(=ダブルクリック本体)だけは数えない。
    m, s, c = new_monitor()
    m.set_phase("peer")
    created = datetime.now(timezone.utc).isoformat()
    s.under, s.pos = ps, [10, 10]
    s.btn["left"] = True
    tick(m, c, 1)
    s.btn["left"] = False
    tick(m, c, 1)
    s.fg = 400
    tick(m, c, 2)
    m.set_phase("w05b-quiet")
    tick(m, c, 4)
    a = assess(m, launch_created_iso=created)
    check(
        "配布版: 生成時刻直後の押下はダブルクリック本体として別記し数えない",
        a["verdict"] == "clean"
        and len(a["launch_presses_excused"]) == 1
        and not a["mouse_presses_during_observation"],
        a["reasons"],
    )
    a = assess(
        m,
        launch_created_iso=(
            datetime.now(timezone.utc) - timedelta(seconds=5)
        ).isoformat(),
    )
    check(
        "配布版: 生成時刻より十分後の押下は数える",
        a["verdict"] == "not-established"
        and "mouse-press-during-observation" in a["reasons"],
        a["reasons"],
    )

    m, s, c = scenario()
    other = {"hwnd": 400, "pid": 999, "title": "確認", "class": MODAL_CLASS}
    a = assess_w05b_return(
        m.summary(),
        other,
        [222],
        fg_before_peer=ps,
        fg_peer_done=other,
        fg_quiet_end=other,
        quiet_end_elapsed=m.elapsed_now(),
    )
    check(
        "確認ダイアログの所有PIDがPageFolioでなければ不成立",
        "modal-not-owned-by-pagefolio" in a["reasons"],
        a["reasons"],
    )

    # 受信時刻の取り出し(純関数)
    summary = {
        "events": [
            {"event": "models", "time": "2026-10-31T00:00:00+00:00"},
            {"event": "received", "time": "2026-10-31T00:00:05+00:00"},
        ]
    }
    check(
        "受信時刻はreceivedイベントから取る",
        received_at(summary) == parse_iso("2026-10-31T00:00:05+00:00")
        and received_at({"events": []}) is None,
    )
    check(
        "待機予算は延長されていない(待機90秒>解放最終期限>いいえ期限>二次起動期限)",
        W05B_HOLD_LIMIT_S == 90.0
        and W05B_RELEASE_LATEST_S < W05B_HOLD_LIMIT_S
        and W05B_NO_LATEST_S < W05B_RELEASE_LATEST_S
        and W05B_START_LATEST_S < W05B_NO_LATEST_S
        and W05B_EXE_LAUNCH_LATEST_S < W05B_NO_LATEST_S,
    )

    say("-- 実API(読み取りのみ。使い捨てPythonは自分で起動して回収) --")
    me = os.getpid()
    names = processes_named(Path(sys.executable).name)
    check("Toolhelp列挙に自分自身が見える", any(x["pid"] == me for x in names))
    child = subprocess.Popen(
        [sys.executable, "-c", "import sys, time; time.sleep(1.5); sys.exit(3)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ident = S.process_identity(child.pid)
        check("使い捨て子のidentityを取得", bool(ident and ident["alive"]))
        if ident:
            found = find_copy_processes(ident["image"], {me})
            check(
                "image絶対パス一致でprocessを検出(自分を除外)",
                any(x["pid"] == child.pid for x in found)
                and all(x["pid"] != me for x in found),
            )
            watch = ProcessWatch(child.pid, ident["created"])
            info = watch.wait(15)
            watch.close()
            check(
                "検出直後のhandleで終了コードを読める",
                info == {"state": "exited", "exit_code": 3},
                info,
            )
            wrong = ProcessWatch(child.pid, ident["created"] + 1)
            check(
                "生成時刻が違えば別processとして扱う",
                wrong.state == "identity-mismatch",
            )
            wrong.close()
    finally:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)
    check("使い捨て子を回収済み", child.poll() is not None)
    check("存在しない窓はIsWindowが偽", window_exists(0) is False)

    say("")
    if failures:
        say(f"W05b機構確認: 失敗 {len(failures)} 件 -> {failures}")
        return 1
    say("W05b機構確認: すべて合格")
    return 0


# ---------------------------------------------------------------------------
# UIスレッド診断の機構確認(--check-diagnostics)
# ---------------------------------------------------------------------------
def check_diagnostics():
    """UIスレッド診断の機構確認。窓も入力も作らず、前景も変えない(約30秒)。

    (1) ui_thread_probe.check_offline: 偽ネイティブ・偽時計・合成バッファ(解析・失敗経路・分類・サイドカー)。
    (2) 入力監視(InputMonitor)との時計/phase の整合。
    (3) Row の配線: 診断OFFの行は不変、ONの行は保存先が分かれ purpose/acceptance を持つ、引数の組合せ検査。
        (3c) 外部見張り(--external-wake-ms): 引数(承認範囲100〜150・併用禁止)・session記録・配線・群ごとの集計。
    (4) ui_thread_probe.check_live: 使い捨てのTclプロセス(自分で起動・Tkの窓なし)を実APIで観測。
        幽霊メッセージ(Tcl通知器が GetMessage で眠る停止の再現)に対し、別プロセスの外部見張りが1周期内に解消することも確かめる。
    静的検査(ui_thread_probe.check_offline): 見張りの投稿経路が PostThreadMessageW(WM_NULL) だけで、
    SendMessage 系・前景/入力系・停止/書き込み系のAPIを使わないことを、ソースの構文木から確かめる。
    """
    D = diag_module()
    failures = []

    def check(name, condition, detail=""):
        say(
            f"  [{'ok' if condition else 'FAIL'}] {name}"
            + (f" ... {detail}" if not condition and detail else "")
        )
        if not condition:
            failures.append(name)

    say("== UIスレッド診断の機構確認(窓も入力も作らない・前景も変えない) ==")
    say("-- (1) 偽ネイティブ・解析・分類 --")
    failures += [f"offline: {name}" for name in D.check_offline(say)]

    say("-- (2) 入力監視との時計/phaseの整合 --")
    ps = {"hwnd": 100, "pid": 111, "title": "Windows PowerShell", "class": "Console"}
    pf = {"hwnd": 200, "pid": 222, "title": "PageFolio", "class": "TkTopLevel"}
    clock = _FakeClock()
    sampler = _FakeSampler({100: ps, 200: pf})
    monitor = InputMonitor(sampler, clock=clock)
    monitor.set_owned_pids((222,))
    monitor.set_phase("awaiting-enter")
    monitor.poll_once()  # 基準線(単調時計の起点 _t0)
    fake = D.FakeNative()
    probe = D.UiThreadProbe(
        fake,
        222,
        expected_created=fake.created,
        clock=clock,
        t0=monitor._t0,
        phase_fn=lambda: monitor._phase,
        wall=now,
    )
    probe._open_target()
    clock.advance(0.5)
    monitor.set_phase("peer")
    sampler.btn["left"] = True
    sampler.under = pf
    monitor.poll_once()
    row = probe.sample_once()
    mouse = monitor.mouse_events[-1]
    check(
        "同じ時刻の押下イベントとUIサンプルで elapsed_s と phase が一致する",
        mouse["elapsed_s"] == row["elapsed_s"] == 0.5
        and mouse["phase"] == row["phase"] == "peer",
        f"mouse={mouse['elapsed_s']}/{mouse['phase']} sample={row['elapsed_s']}/{row['phase']}",
    )
    phase_t = monitor.phase_log[-1]["t"]
    check(
        "サンプルの壁時計 t は phase_log と同じ書式で、phase切替より後",
        re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}\+00:00", row["t"])
        is not None
        and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}\+00:00", phase_t)
        is not None
        and row["t"] >= phase_t,
        f"t={row['t']} phase_log.t={phase_t}",
    )
    check(
        "アンカー(tick, 壁時計, 単調時計)を同時に読んだ組として取れる",
        set(probe.anchor()) == {"tick_ms", "t", "mono"},
    )

    say("-- (3) Rowの配線(診断OFFは不変・ONは別フォルダ) --")
    normal = Row("W02/preview@module", True)
    keys_before = set(normal.session)
    normal.start_ui_probe({"expected_owner": {"pid": 1}})
    normal.stop_ui_probe()
    normal.close_ui_probe()
    check(
        "診断OFFの行: sessionに診断フィールドが増えず、probeも作らない",
        set(normal.session) == keys_before
        and normal.probe is None
        and not (
            {"purpose", "acceptance", "diagnostics", "ui_thread_diag"}
            & set(normal.session)
        ),
        str(sorted(set(normal.session) ^ keys_before)),
    )
    check(
        "診断OFFの行: 保存先は従来どおり 06-05-evidence/(selftestは selftest/)",
        normal.evidence_dir() == EVIDENCE / "selftest"
        and Row("W02/preview@module", False).evidence_dir() == EVIDENCE,
    )
    diag_row = Row(
        "W02/preview@module",
        False,
        diag={
            "wm_null": False,
            "interval_ms": 100,
            "run_index": 2,
            "run_total": 8,
            "hold_s": 30.0,
        },
    )
    check(
        "診断ONの行: purpose=debug-frequency・acceptance=false・debug_session を持つ",
        diag_row.session.get("purpose") == "debug-frequency"
        and diag_row.session.get("acceptance") is False
        and diag_row.session.get("debug_session") == "w02-preview-peer-expired"
        and diag_row.session["diagnostics"]["run_index"] == 2
        and diag_row.session["diagnostics"]["wm_null_probe"] is False,
    )
    check(
        "診断ONの行: 保存先は 06-05-evidence/debug-w02-preview-peer-expired/(既存の原本と別)",
        diag_row.evidence_dir() == EVIDENCE / "debug-w02-preview-peer-expired"
        and diag_row.evidence_dir().parent == EVIDENCE
        and Row(
            "W02/preview@module", True, diag={"wm_null": True, "interval_ms": 100}
        ).evidence_dir()
        == EVIDENCE / "debug-w02-preview-peer-expired" / "selftest",
    )
    try:
        Row("W02/preview@production-exe", False, diag={"wm_null": False})
        refused = False
    except SystemExit:
        refused = True
    check("診断ONで実EXE行は拒否する", refused)
    parser = build_parser()
    for argv, name in (
        (["--row", "W02/preview@module", "--wm-null-probe"], "--wm-null-probe だけ"),
        (
            [
                "--row",
                "W02/preview@module",
                "--diagnose-ui-thread",
                "--diag-interval-ms",
                "5",
            ],
            "--diag-interval-ms が小さすぎる",
        ),
        (
            ["--row", "W02/preview@module", "--diag-run", "1"],
            "--diag-run だけ",
        ),
    ):
        try:
            validate_args(parser, parser.parse_args(argv))
            rejected = False
        except SystemExit:
            rejected = True
        check(f"引数の組合せ検査: {name}は拒否", rejected)
    ok_args = parser.parse_args(
        ["--row", "W02/preview@module", "--diagnose-ui-thread", "--wm-null-probe"]
    )
    check(
        "引数の組合せ検査: --diagnose-ui-thread --wm-null-probe は通り、既定の間隔は100ms",
        validate_args(parser, ok_args) is None and ok_args.diag_interval_ms == 100,
    )
    off_args = parser.parse_args(["--row", "W02/preview@module"])
    check(
        "診断のフラグを付けない呼出しは diag=None(従来どおり)",
        diag_options(off_args) is None
        and diag_options(ok_args)
        == {
            "wm_null": True,
            "external_wake_ms": None,
            "interval_ms": 100,
            "run_index": None,
            "run_total": None,
            "hold_s": 30.0,
            "induce": False,
            "induce_wait_s": 20.0,
        },
    )

    try:
        validate_args(
            parser,
            parser.parse_args(
                [
                    "--row",
                    "W02/preview@module",
                    "--diagnose-ui-thread",
                    "--diag-hold-s",
                    "500",
                ]
            ),
        )
        rejected = False
    except SystemExit:
        rejected = True
    check("引数の組合せ検査: --diag-hold-s が範囲外は拒否", rejected)

    naps = []
    hold_row = Row(
        "W02/preview@module",
        True,
        diag={"wm_null": False, "interval_ms": 100, "hold_s": 30.0},
    )
    hold_row.monitor = monitor
    monitor.set_phase("post-peer")
    held = hold_row.diag_hold_if_failed(
        {"json": {"result": {"result": "expired"}}}, sleep=naps.append
    )
    check(
        "診断のhold: 二次起動が完了しなかった回は30秒待ち、その間のphaseは diag-hold で、終わると post-peer へ戻る",
        held is True
        and naps == [30.0]
        and monitor.phase_log[-2]["phase"] == "diag-hold"
        and monitor.phase_log[-1]["phase"] == "post-peer",
        f"held={held} naps={naps} phases={[p['phase'] for p in monitor.phase_log[-3:]]}",
    )
    naps.clear()
    check(
        "診断のhold: 完了した回(completed)では待たない",
        hold_row.diag_hold_if_failed(
            {"json": {"result": {"result": "completed"}}}, sleep=naps.append
        )
        is False
        and naps == [],
    )
    check(
        "診断のhold: harnessのpeer自体が失敗した回(json=None)も待つ",
        hold_row.diag_hold_if_failed({"json": None}, sleep=naps.append) is True
        and naps == [30.0],
    )
    naps.clear()
    zero_row = Row(
        "W02/preview@module",
        True,
        diag={"wm_null": False, "interval_ms": 100, "hold_s": 0},
    )
    zero_row.monitor = monitor
    check(
        "診断のhold: --diag-hold-s 0 なら失敗回でも待たない",
        zero_row.diag_hold_if_failed(
            {"json": {"result": {"result": "expired"}}}, sleep=naps.append
        )
        is False
        and naps == [],
    )
    check(
        "診断OFFの行: diag_hold_if_failed は何もしない",
        normal.diag_hold_if_failed(
            {"json": {"result": {"result": "expired"}}}, sleep=naps.append
        )
        is False
        and naps == [],
    )

    say("-- (3b) 誘発手順(--induce-switcher)の引数・記録・判定 --")
    for argv, name in (
        (
            ["--row", "W02/preview@module", "--induce-switcher"],
            "--induce-switcher だけ",
        ),
        (
            [
                "--row",
                "W01/normal@script",
                "--diagnose-ui-thread",
                "--induce-switcher",
            ],
            "W01の行に --induce-switcher",
        ),
        (
            [
                "--row",
                "W02/preview@module",
                "--diagnose-ui-thread",
                "--induce-switcher",
                "--induce-wait-s",
                "1",
            ],
            "--induce-wait-s が小さすぎる",
        ),
    ):
        try:
            validate_args(parser, parser.parse_args(argv))
            rejected = False
        except SystemExit:
            rejected = True
        check(f"引数の組合せ検査: {name}は拒否", rejected)
    induce_args = parser.parse_args(
        [
            "--row",
            "W02/preview@module",
            "--diagnose-ui-thread",
            "--induce-switcher",
            "--diag-run",
            "3",
            "--diag-runs",
            "10",
        ]
    )
    check(
        "引数の組合せ検査: --diagnose-ui-thread --induce-switcher は通り、WM_NULLは既定OFFのまま・待ち時間は20秒",
        validate_args(parser, induce_args) is None
        and diag_options(induce_args)["induce"] is True
        and diag_options(induce_args)["wm_null"] is False
        and diag_options(induce_args)["induce_wait_s"] == 20.0
        and diag_options(induce_args)["run_index"] == 3,
        str(diag_options(induce_args)),
    )
    induce_row = Row("W02/preview@module", False, diag=diag_options(induce_args))
    plain_row = Row(
        "W02/preview@module",
        False,
        diag={"wm_null": False, "interval_ms": 100, "hold_s": 30.0},
    )
    check(
        "session.diagnostics に手順の種別を記録(誘発=alt-tab-switcher-hold-then-quiet-wait・通常=free)と syscall_probe・WM_NULL OFF",
        induce_row.session["diagnostics"]["induce"]["requested"] is True
        and induce_row.session["diagnostics"]["induce"]["variant"] == INDUCE_VARIANT
        and induce_row.session["diagnostics"]["induce"]["quiet_wait_s"] == 20.0
        and induce_row.session["diagnostics"]["induce"]["switcher_min_s"] == 0.5
        and induce_row.session["diagnostics"]["wm_null_probe"] is False
        and induce_row.session["diagnostics"]["syscall_probe"] is True
        and plain_row.session["diagnostics"]["induce"]["requested"] is False
        and plain_row.session["diagnostics"]["induce"]["variant"] == "free",
        str(induce_row.session["diagnostics"]),
    )

    def tr(t_text, elapsed, origin, dest, phase="awaiting-enter"):
        return {
            "t": t_text,
            "elapsed_s": elapsed,
            "phase": phase,
            "from": origin,
            "to": dest,
        }

    pf_win = {"pid": 222, "class": "TkTopLevel", "title": "PageFolio"}
    ps_win = {
        "pid": 111,
        "class": "CASCADIA_HOSTING_WINDOW_CLASS",
        "title": "Windows PowerShell",
    }
    stage_win = {"pid": 9, "class": "ForegroundStaging", "title": ""}
    switch_win = {
        "pid": 9,
        "class": "XamlExplorerHostIslandWindow",
        "title": "タスクの切り替え",
    }
    null_win = {"pid": None, "class": "", "title": ""}
    owned_pids = {222}

    def hold_switcher(shown_s):
        return [
            tr("t1", 1.0, ps_win, pf_win, "start-harness"),
            tr("t2", 5.0, pf_win, stage_win),
            tr("t3", 5.02, stage_win, switch_win),
            tr("t4", 5.02 + shown_s, switch_win, ps_win),
        ]

    good = trace_departure(hold_switcher(0.6), owned_pids, 26.0)
    verdict = assess_induction(good, 20.0)
    check(
        "判定(成立): PageFolio->中継窓->切替UI(0.6秒)->PowerShell で、そのまま20秒超静止",
        good["departed"]
        and not good["pagefolio_foreground"]
        and good["switcher_titles"] == ["タスクの切り替え"]
        and abs(good["switcher_visible_s"] - 0.6) < 0.001
        and good["landing"]["class"] == "CASCADIA_HOSTING_WINDOW_CLASS"
        and abs(good["quiet_s"] - (26.0 - 5.62)) < 0.001
        and verdict["induced"] is True
        and verdict["reasons"] == []
        and verdict["variant"] == INDUCE_VARIANT,
        str(verdict),
    )
    staged = hold_switcher(0.6)[:3] + [
        tr("t4", 5.62, switch_win, stage_win),
        tr("t5", 5.63, stage_win, ps_win),
    ]
    via_stage = trace_departure(staged, owned_pids, 30.0)
    check(
        "判定(成立): 切替UIから中継窓を経て PowerShell へ移る形(実機で見た形)も、切替UIの表示0.6秒・着地はPowerShell",
        abs(via_stage["switcher_visible_s"] - 0.6) < 0.001
        and via_stage["landing"]["elapsed_s"] == 5.63
        and assess_induction(via_stage, 20.0)["induced"] is True,
        str(via_stage),
    )
    direct = trace_departure(
        [
            tr("t1", 1.0, ps_win, pf_win, "start-harness"),
            tr("t2", 5.0, pf_win, null_win),
            tr("t3", 5.008, null_win, ps_win),
        ],
        owned_pids,
        30.0,
    )
    check(
        "判定(不成立): 切替UIを出さない短押しAlt+Tab(null経由)は switcher-not-shown",
        direct["departed"]
        and direct["switcher_titles"] == []
        and assess_induction(direct, 20.0)["reasons"] == ["switcher-not-shown"],
        str(assess_induction(direct, 20.0)),
    )
    check(
        "判定(不成立): 切替UIが0.3秒だけなら switcher-too-short、静止が足りなければ quiet-wait-too-short(両方同時もあり)",
        assess_induction(trace_departure(hold_switcher(0.3), owned_pids, 30.0), 20.0)[
            "reasons"
        ]
        == ["switcher-too-short"]
        and assess_induction(
            trace_departure(hold_switcher(0.6), owned_pids, 12.0), 20.0
        )["reasons"]
        == ["quiet-wait-too-short"]
        and assess_induction(
            trace_departure(hold_switcher(0.3), owned_pids, 12.0), 20.0
        )["reasons"]
        == ["switcher-too-short", "quiet-wait-too-short"],
    )
    back = trace_departure(
        hold_switcher(0.6) + [tr("t5", 8.0, ps_win, pf_win)], owned_pids, 30.0
    )
    again = trace_departure(
        hold_switcher(0.6)
        + [
            tr("t5", 8.0, ps_win, pf_win),
            tr("t6", 9.0, pf_win, stage_win),
            tr("t7", 9.02, stage_win, switch_win),
            tr("t8", 9.9, switch_win, ps_win),
        ],
        owned_pids,
        40.0,
    )
    check(
        "判定: Enter の時点で PageFolio が前面(戻った)なら pagefolio-still-foreground。取り直し後は最後の離脱だけを数える",
        back["pagefolio_foreground"] is True
        and assess_induction(back, 20.0)["reasons"] == ["pagefolio-still-foreground"]
        and abs(again["switcher_visible_s"] - 0.88) < 0.001
        and again["landing"]["elapsed_s"] == 9.9
        and abs(again["quiet_s"] - 30.1) < 0.001,
        f"{back['pagefolio_foreground']} {again['switcher_visible_s']} {again['quiet_s']}",
    )
    still_open = trace_departure(hold_switcher(0.6)[:3], owned_pids, 12.0)
    empty = trace_departure([], owned_pids, 12.0)
    check(
        "判定: 切替UIを出したまま(Altを離していない)は着地なし(no-landing)、遷移が無ければ no-departure。例外にならない",
        assess_induction(still_open, 20.0)["reasons"] == ["no-landing"]
        and assess_induction(empty, 20.0)["reasons"] == ["no-departure"]
        and still_open["switcher_visible_s"] > 6.9,
        f"{assess_induction(still_open, 20.0)['reasons']} {assess_induction(empty, 20.0)['reasons']}",
    )

    # 実記録の再生(読み取りのみ): 過去の診断再走9回の前景遷移で、判定が実機の形に耐えるか
    real_dir = EVIDENCE / D.DEBUG_DIRNAME
    real_files = sorted(real_dir.glob("W02_preview_at_module-20261025T07*Z.json"))
    if not real_files:
        check("実記録の再生(過去の診断再走): 証拠が無い環境ではskip", True)
    else:

        def elapsed_at(transitions, when):
            base = transitions[0]
            return (
                base["elapsed_s"]
                + (
                    datetime.fromisoformat(when) - datetime.fromisoformat(base["t"])
                ).total_seconds()
            )

        not_induced = 0
        replayed = 0
        positive = None
        for path in real_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            monitor_data = data.get("input_monitor") or {}
            transitions = monitor_data.get("foreground_transitions") or []
            owned_real = set(monitor_data.get("owned_pids") or [])
            peer_at = next(
                (
                    x["t"]
                    for x in monitor_data.get("phase_log", [])
                    if x["phase"] == "peer"
                ),
                None,
            )
            if not transitions or not peer_at:
                continue
            before_peer = [x for x in transitions if x["t"] < peer_at]
            if not before_peer:
                continue
            replayed += 1
            result = assess_induction(
                trace_departure(
                    before_peer, owned_real, elapsed_at(transitions, peer_at)
                ),
                20.0,
            )
            if not result["induced"]:
                not_induced += 1
            if path.name.startswith("W02_preview_at_module-20261025T074104Z"):
                # 陽性対照: この回の post-peer に、切替UIを0.58秒見せて PowerShell へ移る操作がある(07:40:36.8)。
                # その20秒後を仮のEnterとみなして判定する。
                cutoff = "2026-10-25T07:40:57.600000+00:00"
                upto = [x for x in transitions if x["t"] < cutoff]
                positive = trace_departure(
                    upto, owned_real, elapsed_at(transitions, cutoff)
                )
        check(
            "実記録の再生: 過去の診断再走(誘発手順を指示していない回)の peer 直前は、すべて誘発不成立と判定される",
            replayed >= 5 and not_induced == replayed,
            f"replayed={replayed} not_induced={not_induced}",
        )
        check(
            "実記録の再生(陽性対照): 07:40:36.8 の「PageFolio->切替UI(約0.58秒)->PowerShell」を、20秒静止後の判定で成立と読める",
            positive is not None
            and 0.55 <= positive["switcher_visible_s"] <= 0.62
            and positive["switcher_titles"] == ["タスクの切り替え"]
            and positive["landing"]["class"] == "CASCADIA_HOSTING_WINDOW_CLASS"
            and 19.9 <= positive["quiet_s"] <= 20.3
            and assess_induction(positive, 20.0)["induced"] is True,
            str(positive),
        )

    # induce_procedure(誘発手順の案内・Enter・自動待機・成立判定)を、偽の監視と偽のsleepで通す
    import contextlib
    import io

    def gate_row(transitions, now_t, selftest=False):
        row_ = Row(
            "W02/preview@module",
            selftest,
            diag={
                "wm_null": False,
                "interval_ms": 100,
                "hold_s": 30.0,
                "induce": True,
                "induce_wait_s": 20.0,
            },
        )
        gclock = _FakeClock()
        gclock.t = now_t
        gmonitor = InputMonitor(_FakeSampler({100: ps_win, 200: pf_win}), clock=gclock)
        gmonitor._t0 = 0.0
        gmonitor.fg_transitions = list(transitions)
        row_.monitor = gmonitor
        enters = []
        row_.prompter.enter = enters.append
        naps = []

        def nap(seconds):
            naps.append(seconds)
            gclock.advance(seconds)

        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            row_.induce_procedure([222], sleep=nap)
        return row_, enters, naps, sink.getvalue()

    row_a, enters_a, naps_a, out_a = gate_row(hold_switcher(0.6), 12.0)
    check(
        "induce_procedure: 静止が足りない(PowerShellへ移って6.4秒)ときは不足分(約13.6秒)を自動で待ち、待ったあとに成立と記録する",
        len(enters_a) == 1
        and len(naps_a) == 1
        and abs(naps_a[0] - (20.0 - (12.0 - 5.62) + 0.3)) < 0.01
        and row_a.session["induce_assessment"]["induced"] is True
        and [g["action"] for g in row_a.session["diagnostics"]["induce"]["gate"]]
        == ["auto-wait"]
        and "自動待機" in out_a
        and "誘発手順の判定: 成立" in out_a
        and "Alt を押したまま" in out_a,
        f"enters={len(enters_a)} naps={naps_a} {row_a.session.get('induce_assessment')}",
    )
    row_b, enters_b, naps_b, out_b = gate_row(hold_switcher(0.6), 30.0)
    check(
        "induce_procedure: 十分に静止していれば自動待機せず、そのまま成立",
        len(naps_b) == 0
        and row_b.session["induce_assessment"]["induced"] is True
        and "gate" in row_b.session["diagnostics"]["induce"]
        and row_b.session["diagnostics"]["induce"]["gate"] == [],
    )
    row_c, enters_c, naps_c, out_c = gate_row(
        [
            tr("t1", 1.0, ps_win, pf_win, "start-harness"),
            tr("t2", 5.0, pf_win, null_win),
            tr("t3", 5.008, null_win, ps_win),
        ],
        30.0,
    )
    check(
        "induce_procedure: 切替UIを出さなかった回は不成立(switcher-not-shown)と記録し、二次起動は止めない(例外にしない)",
        row_c.session["induce_assessment"]["induced"] is False
        and row_c.session["induce_assessment"]["reasons"] == ["switcher-not-shown"]
        and "不成立" in out_c
        and "母数に数えません" in out_c,
        out_c[-200:],
    )
    row_d, enters_d, naps_d, out_d = gate_row(
        [tr("t1", 1.0, ps_win, pf_win, "start-harness")], 30.0
    )
    check(
        "induce_procedure: Enter の時点で PageFolio が前面のままなら取り直しを促し(最大3回)、それでも前面なら不成立で進める",
        len(enters_d) == INDUCE_MAX_ATTEMPTS
        and naps_d == []
        and row_d.session["induce_assessment"]["reasons"]
        == ["pagefolio-still-foreground"]
        and [g["action"] for g in row_d.session["diagnostics"]["induce"]["gate"]]
        == ["pagefolio-still-foreground"] * INDUCE_MAX_ATTEMPTS
        and "もう一度 Enter" in out_d,
        f"enters={len(enters_d)} gate={row_d.session['diagnostics']['induce']['gate']}",
    )
    row_e, enters_e, naps_e, out_e = gate_row([], 30.0, selftest=True)
    check(
        "induce_procedure: selftest は手順を実行せず、不成立(selftest)と記録して待たない",
        naps_e == [] and row_e.session["induce_assessment"]["reasons"] == ["selftest"],
    )
    check(
        "診断OFFの行・誘発なしの診断行は induce_assessment を session に持たない",
        "induce_assessment" not in normal.session
        and "induce_assessment" not in plain_row.session,
    )

    say("-- (3c) 外部見張り(--external-wake-ms)の引数・記録・配線・集計 --")
    base = ["--row", "W02/preview@module"]
    for argv, name in (
        (
            [*base, "--external-wake-ms", "120"],
            "--external-wake-ms だけ(--diagnose-ui-thread なし)",
        ),
        (
            [
                *base,
                "--diagnose-ui-thread",
                "--wm-null-probe",
                "--external-wake-ms",
                "120",
            ],
            "--wm-null-probe(送信)との併用",
        ),
        (
            [*base, "--diagnose-ui-thread", "--external-wake-ms", "50"],
            "承認範囲(100〜150)より小さい値",
        ),
        (
            [*base, "--diagnose-ui-thread", "--external-wake-ms", "500"],
            "承認範囲(100〜150)より大きい値",
        ),
    ):
        try:
            validate_args(parser, parser.parse_args(argv))
            rejected = False
        except SystemExit:
            rejected = True
        check(f"引数の組合せ検査: {name}は拒否", rejected)
    edge_ok = []
    for value in ("100", "150"):
        edge_args = parser.parse_args(
            [*base, "--diagnose-ui-thread", "--external-wake-ms", value]
        )
        edge_ok.append(validate_args(parser, edge_args) is None)
    check("引数の組合せ検査: 承認範囲の端(100 と 150)は通る", edge_ok == [True, True])
    wake_args = parser.parse_args(
        [
            *base,
            "--diagnose-ui-thread",
            "--induce-switcher",
            "--external-wake-ms",
            "120",
            "--diag-run",
            "3",
            "--diag-runs",
            "30",
        ]
    )
    wake_options = diag_options(wake_args)
    check(
        "引数の組合せ検査: --diagnose-ui-thread --induce-switcher --external-wake-ms 120 は通り、送信の WM_NULL は OFF のまま・回数は 3/30",
        validate_args(parser, wake_args) is None
        and wake_options["external_wake_ms"] == 120
        and wake_options["wm_null"] is False
        and wake_options["induce"] is True
        and (wake_options["run_index"], wake_options["run_total"]) == (3, 30),
        str(wake_options),
    )
    wake_row = Row("W02/preview@module", False, diag=wake_options)
    check(
        "見張りONの行: session.diagnostics.external_wake=120(診断だけの行は None)・purpose=debug-frequency・acceptance=false・保存先は debug-* で受入証拠と分離",
        wake_row.session["diagnostics"]["external_wake"] == 120
        and plain_row.session["diagnostics"]["external_wake"] is None
        and induce_row.session["diagnostics"]["external_wake"] is None
        and wake_row.session["purpose"] == "debug-frequency"
        and wake_row.session["acceptance"] is False
        and wake_row.evidence_dir() == EVIDENCE / "debug-w02-preview-peer-expired"
        and "介入あり" in wake_row.session["diagnostics"]["note"]
        and "介入あり" not in plain_row.session["diagnostics"]["note"],
        str(wake_row.session["diagnostics"]),
    )

    def wired_run(options, seconds):
        """偽ネイティブ(Win32Native を差し替え)で start_ui_probe -> stop_ui_probe -> close_ui_probe を通す。"""
        fake_native = D.FakeNative()
        real_class = D.Win32Native
        D.Win32Native = lambda: fake_native
        row_ = Row("W02/preview@module", False, diag=options)
        row_.monitor = monitor
        sink = io.StringIO()
        try:
            with contextlib.redirect_stdout(sink):
                row_.start_ui_probe(
                    {
                        "expected_owner": {
                            "pid": 222,
                            "process_created": fake_native.created,
                        }
                    }
                )
                time.sleep(seconds)
                row_.stop_ui_probe()
                row_.close_ui_probe()
        finally:
            D.Win32Native = real_class
        return row_, fake_native, sink.getvalue()

    wired, wired_native, wired_out = wired_run(wake_options, 0.5)
    wired_diag = wired.session.get("ui_thread_diag") or {}
    started_step = next(
        (s for s in wired.session["steps"] if s["step"] == "ui-probe-started"), {}
    )
    check(
        "見張りONの配線: start_ui_probe が見張りのスレッドを作り、tid=7 へだけ投稿し、summary・frequency_record・steps・報告に残る",
        wired.probe is not None
        and wired.probe.external_wake_ms == 120
        and wired_native.post_calls >= 2
        and set(wired_native.posted) == {7}
        and wired_native.verify_calls
        and wired_native.verify_calls[0][2] == wired_native.created
        and (wired_diag.get("external_wake") or {}).get("posts_ok", 0) >= 2
        and (wired_diag.get("frequency_record") or {}).get("external_wake_ms") == 120
        and started_step.get("external_wake_ms") == 120
        and "外部見張り(120ms)" in wired_out
        and wired.session.get("ui_thread_diag_error") is None,
        f"posts={wired_native.post_calls} diag_error={wired.session.get('ui_thread_diag_error')} out={wired_out[-300:]}",
    )
    plain_wired, plain_native, plain_out = wired_run(diag_options(induce_args), 0.3)
    check(
        "見張りOFFの診断行の配線: 見張りのスレッドを作らず、投稿も宛先の確認も1回も呼ばず、summary の external_wake は None",
        plain_wired.probe is not None
        and plain_wired.probe._wake_thread is None
        and plain_native.post_calls == 0
        and plain_native.verify_calls == []
        and (plain_wired.session.get("ui_thread_diag") or {}).get("external_wake")
        is None
        and "外部見張り" not in plain_out,
        plain_out[-200:],
    )
    check(
        "見張りの経路は uat_row.py では PostThreadMessageW を直接呼ばない(投稿は ui_thread_probe の宛先確認つき経路だけ)",
        "PostThreadMessageW"
        not in D.used_native_names(Path(__file__).read_text(encoding="utf-8")),
    )

    tmp5 = Path(__file__).with_name("__diag_check_tmp5__")
    tmp5.mkdir(exist_ok=True)
    try:
        for name, wake_ms, wake in (
            ("off", None, None),
            (
                "on",
                120,
                {
                    "posts_ok": 400,
                    "posts_failed": 0,
                    "refused": 0,
                    "interval_ms": {"max": 150.0, "over_2x_period": 0},
                },
            ),
        ):
            (tmp5 / f"{name}.json").write_text(
                json.dumps(
                    {
                        "row": "W02/preview@module",
                        "outcome": "answered",
                        "procedure_verdict": "clean",
                        "diagnostics": {
                            "external_wake": wake_ms,
                            "syscall_probe": False,
                            "induce": {"requested": True},
                        },
                        "induce_assessment": {"induced": True, "reasons": []},
                        "harness_peer": {
                            "json": {"result": {"result": "completed", "elapsed": 80}}
                        },
                        "ui_thread_diag": {
                            "stall_episodes": [],
                            "external_wake": wake,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            summary_code = summarize_diag(tmp5)
        summary_text = sink.getvalue()
        check(
            "--summarize-diag: 見張りの有無で分けた群の集計(回数・ctx停止区間・GetMessage停止・投稿の成功/失敗/最大間隔)を出す",
            summary_code == 0
            and "[見張りなし・誘発成立かつclean] 回数 1" in summary_text
            and "[見張りあり(120ms)・誘発成立かつclean] 回数 1" in summary_text
            and "投稿: 1 回の回で 成功 400 / 失敗 0 / 拒否 0" in summary_text
            and "外部見張り 120ms: 投稿 成功 400" in summary_text,
            summary_text[-700:],
        )
    finally:
        for path in tmp5.glob("*"):
            path.unlink()
        tmp5.rmdir()
    check(
        "群の集計行: 回数0の群でも落ちない",
        format_group_stats("[x]", {}) == ["  [x] 回数 0"],
    )

    say("-- (4) 使い捨てTclプロセスの実観測 --")
    failures += [f"live: {name}" for name in D.check_live(say)]

    say("")
    if failures:
        say(f"診断の機構確認: 失敗 {len(failures)} 件 -> {failures}")
        return 1
    say("診断の機構確認: すべて合格")
    return 0


def summarize_diag(directory):
    """診断ディレクトリのセッションJSONから発生頻度を表示する(読み取りのみ)。"""
    D = diag_module()
    directory = Path(directory) if directory else EVIDENCE / D.DEBUG_DIRNAME
    if not directory.is_dir():
        say(f"診断ディレクトリがまだありません: {directory}")
        return 1
    report = D.summarize_sessions(directory)
    say(
        f"== 診断実行の集計(発生頻度の確認用。受入証拠ではない): {report['directory']} =="
    )
    for item in report["sessions"]:
        if "error" in item:
            say(f"  {item['file']}: 読み込み失敗 {item['error']}")
            continue
        say(
            f"  [{item['run']}] {item['file']}: outcome={item['outcome']} 手順={item['procedure_verdict']} "
            f"peer={item['peer_result']}/{item['peer_elapsed_ms']}ms 一次の遅れ={item['late_request']} "
            f"無スケジュール区間={item['stall_episodes']}件(最長{item['longest_stall_s']}s) "
            f"WM_NULL={item['wm_null_probe']} focus_correct={item['focus_correct']}"
        )
        if item.get("external_wake_ms"):
            wake = item.get("wake") or {}
            say(
                f"        外部見張り {item['external_wake_ms']}ms: 投稿 成功 {wake.get('posts_ok')} / 失敗 {wake.get('posts_failed')} / "
                f"拒否 {wake.get('refused')} / 投稿の最大間隔 {wake.get('max_interval_ms')} ms"
            )
        gm = item.get("getmessage") or {}
        if gm.get("syscall_columns"):
            say(
                f"        GetMessage 区間 {gm.get('runs')} 件(見えた行 {gm.get('rows')}) / 最長 {gm.get('max_length_ms')} ms / "
                f"停止(>= {gm.get('stall_threshold_ms')}ms) {gm.get('stalls')} 件"
            )
        if item.get("induce_requested"):
            if item.get("induced"):
                say(
                    f"        誘発手順: 成立(切替UI {item.get('induce_switcher_s')} 秒・静止 {item.get('induce_quiet_s')} 秒)"
                )
            else:
                say(
                    f"        誘発手順: 不成立({induce_reasons_text(item.get('induce_reasons'))})"
                )
        for stall in item.get("stalls") or []:
            wait = stall.get("wait") or {}
            say(
                f"        無スケジュール区間 {stall.get('start_t')} から {stall.get('duration_s')} 秒"
                f"(phase={'/'.join(stall.get('phases') or [])}) 種別={wait.get('kind') or '(システムコール未計測の旧診断)'}"
                f" 最後のシステムコール={wait.get('syscalls')}"
            )
            for target in wait.get("targets") or []:
                say(f"            待ち先: {target['text']}")
            if wait.get("others_ctx_delta"):
                say(f"            他スレッドのctx増分: {wait['others_ctx_delta']}")
        if item.get("wait_targets_seen") and not item.get("stalls"):
            for target in item["wait_targets_seen"]:
                say(
                    f"        (停止区間なしで観測された待ち先 {target['rows']} 行) {target['syscall']}: {target['text']}"
                )
    say(
        f"  回数 {report['total']} / 手順がcleanの回 {report['clean_procedure']} / "
        f"そのうち二次起動が完了しなかった(または一次が締切に間に合わなかった)回 "
        f"{report['peer_not_completed_or_late_among_clean']}"
    )
    if report.get("induce_requested"):
        say(
            f"  誘発手順の回 {report['induce_requested']} / 手順が成立しcleanの回 {report['induced_clean']} / "
            f"そのうち二次起動が完了しなかった(または一次が締切に間に合わなかった)回 "
            f"{report['peer_not_completed_or_late_among_induced']}"
        )
    groups = report.get("groups") or {}
    if groups:
        say("")
        say(
            "== 外部見張り(WM_NULL 投稿)の有無で分けた集計(介入ありの回となしの回を混ぜない) =="
        )
        on_periods = (groups.get("external_wake_on") or {}).get("period_ms") or []
        for key, label in (
            ("external_wake_off", "見張りなし"),
            ("external_wake_on", f"見張りあり({'/'.join(map(str, on_periods))}ms)"),
        ):
            for part, part_label in (
                ("induced_clean", "誘発成立かつclean"),
                ("all", "全回"),
            ):
                stats = (groups.get(key) or {}).get(part) or {}
                for text in format_group_stats(f"[{label}・{part_label}]", stats):
                    say(text)
        say(
            "  見方: 見張りなし群は元の停止(GetMessage に長く居続ける)の頻度、見張りあり群は同じ手順で停止が消えるか。"
            "GetMessage の区間は syscall 列のあるセッションだけで数えます(古い診断は『数えた回』に入りません)。"
        )
    return 0


def format_group_stats(label, stats):
    """summarize_diag の群ごとの集計行(純関数)。"""
    if not stats or not stats.get("sessions"):
        return [f"  {label} 回数 0"]
    lines = [
        f"  {label} 回数 {stats['sessions']} / 二次起動の未完了(または一次の遅れ) {stats['peer_not_completed_or_late']} 回 / "
        f"ctx停止区間 {stats['ctx_stall_episodes']} 件({stats['sessions_with_ctx_stall']} 回の回・最長 {stats['longest_ctx_stall_s']} 秒)"
    ]
    lines.append(
        f"      GetMessage の区間を数えた回 {stats['getmessage_sessions']} 回: 区間 {stats['getmessage_runs']} 件"
        f"({stats['sessions_with_getmessage_seen']} 回の回で観測)/ 停止(>= {stats['getmessage_stall_threshold_ms']}ms) "
        f"{stats['getmessage_stalls']} 件({stats['sessions_with_getmessage_stall']} 回の回)/ "
        f"最長 {stats['max_getmessage_ms']} ms・最長 {stats['max_getmessage_rows']} 行"
    )
    wake = stats.get("wake")
    if wake:
        lines.append(
            f"      投稿: {wake['sessions']} 回の回で 成功 {wake['posts_ok']} / 失敗 {wake['posts_failed']} / 拒否 {wake['refused']} / "
            f"投稿の最大間隔 {wake['max_post_interval_ms']} ms / 周期の2倍超の間隔があった回 {wake['sessions_with_long_post_gap']}"
        )
        lines.append(
            f"      停止のうち投稿が流れている最中のもの {stats.get('getmessage_stalls_while_posting', 0)} 件"
            f" / 見張りが期待どおりに動いたと読めない回 {len(wake.get('unhealthy_sessions') or [])} 回"
            + (
                f" {wake['unhealthy_sessions']}"
                if wake.get("unhealthy_sessions")
                else ""
            )
        )
    return lines


def build_parser():
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
    ap.add_argument(
        "--check-w05b",
        action="store_true",
        help="W05bの自動復帰判定の機構確認(窓も入力も作らず前景も変えない。製品は起動しない)",
    )
    ap.add_argument(
        "--diagnose-ui-thread",
        action="store_true",
        help="UIスレッド診断(読み取り専用。発生頻度の確認用で受入証拠ではない。"
        "出力は 06-05-evidence/debug-w02-preview-peer-expired/)",
    )
    ap.add_argument(
        "--wm-null-probe",
        action="store_true",
        help="--diagnose-ui-thread と併用。一次の窓へ SendMessageTimeoutW(WM_NULL) を約0.5秒ごとに送る(既定OFF)",
    )
    ap.add_argument(
        "--external-wake-ms",
        type=int,
        default=None,
        metavar="MS",
        help="--diagnose-ui-thread と併用(既定OFF)。debug: w02-preview-peer-expired の対策の実機検証。driver が一次PageFolioの"
        "UIスレッドへ PostThreadMessageW(WM_NULL) を指定msごとに投稿する(100〜150。SendMessage・前景/入力APIは使わない。"
        "--wm-null-probe とは併用しない)",
    )
    ap.add_argument(
        "--diag-interval-ms",
        type=int,
        default=100,
        help="UIスレッド診断のサンプル間隔(ms。20〜1000、既定100)",
    )
    ap.add_argument(
        "--diag-hold-s",
        type=float,
        default=30.0,
        help="診断のみ。二次起動が完了しなかった回に、利用者へ何も触らせずこの秒数だけ観測を続ける"
        "(0〜120、既定30、0で無効)",
    )
    ap.add_argument(
        "--induce-switcher",
        action="store_true",
        help="--diagnose-ui-thread と併用(W02の行のみ)。誘発手順(Alt+Tab の切替UIを0.5秒以上見せて PowerShell へ移り、"
        "約20秒静止してから Enter)を案内し、不足分の静止を自動で待ち、成立を session JSON に記録する",
    )
    ap.add_argument(
        "--induce-wait-s",
        type=float,
        default=INDUCE_WAIT_S,
        help="誘発手順の静止時間(PowerShell へ移ってから二次起動まで。5〜120、既定20)",
    )
    ap.add_argument("--diag-run", type=int, help="診断の何回目か(記録用)")
    ap.add_argument("--diag-runs", type=int, help="診断の全何回か(記録用)")
    ap.add_argument(
        "--check-diagnostics",
        action="store_true",
        help="UIスレッド診断の機構確認(窓も入力も作らず前景も変えない。約30秒)",
    )
    ap.add_argument(
        "--summarize-diag",
        nargs="?",
        const="",
        metavar="DIR",
        help="診断ディレクトリのセッションJSONから発生頻度を集計(読み取りのみ)",
    )
    return ap


def validate_args(ap, args):
    """診断フラグの組合せ検査(不正なら ap.error で終了)。"""
    if args.wm_null_probe and not args.diagnose_ui_thread:
        ap.error("--wm-null-probe は --diagnose-ui-thread と一緒に指定してください")
    if (args.diag_run or args.diag_runs) and not args.diagnose_ui_thread:
        ap.error(
            "--diag-run/--diag-runs は --diagnose-ui-thread と一緒に指定してください"
        )
    if not 20 <= args.diag_interval_ms <= 1000:
        ap.error("--diag-interval-ms は 20〜1000 で指定してください")
    if not 0 <= args.diag_hold_s <= 120:
        ap.error("--diag-hold-s は 0〜120 で指定してください")
    if args.diagnose_ui_thread and not args.row:
        ap.error("--diagnose-ui-thread には --row が必要です")
    if args.induce_switcher and not args.diagnose_ui_thread:
        ap.error("--induce-switcher は --diagnose-ui-thread と一緒に指定してください")
    if args.induce_switcher and args.row and not args.row.startswith("W02/"):
        ap.error("--induce-switcher は W02 の行だけです")
    if not 5 <= args.induce_wait_s <= 120:
        ap.error("--induce-wait-s は 5〜120 で指定してください")
    if args.external_wake_ms is not None:
        low, high = diag_module().WAKE_PERIOD_RANGE_MS
        if not args.diagnose_ui_thread:
            ap.error(
                "--external-wake-ms は --diagnose-ui-thread と一緒に指定してください"
            )
        if args.wm_null_probe:
            ap.error(
                "--external-wake-ms は --wm-null-probe と併用できません(送信と投稿を混ぜると効果を分けて読めません)"
            )
        if not low <= args.external_wake_ms <= high:
            ap.error(
                f"--external-wake-ms は {low}〜{high} で指定してください(利用者が承認した範囲)"
            )


def diag_options(args):
    if not args.diagnose_ui_thread:
        return None
    return {
        "wm_null": bool(args.wm_null_probe),
        "external_wake_ms": args.external_wake_ms,
        "interval_ms": args.diag_interval_ms,
        "run_index": args.diag_run,
        "run_total": args.diag_runs,
        "hold_s": args.diag_hold_s,
        "induce": bool(args.induce_switcher),
        "induce_wait_s": args.induce_wait_s,
    }


def main():
    ap = build_parser()
    args = ap.parse_args()
    validate_args(ap, args)
    if args.check_monitor:
        raise SystemExit(check_monitor())
    if args.check_w05b:
        raise SystemExit(check_w05b())
    if args.check_diagnostics:
        raise SystemExit(check_diagnostics())
    if args.summarize_diag is not None:
        raise SystemExit(summarize_diag(args.summarize_diag))
    if not args.row:
        ap.error("--row が必要です(例: --row W02/preview@script)")
    row = Row(args.row, args.selftest, diag=diag_options(args))
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
