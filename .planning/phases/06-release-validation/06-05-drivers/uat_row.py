# ruff: noqa
"""06-05-02 の1行(ケースID/subrow)を、利用者が自分のPowerShellで実行する人手受入driver。

対象: G1 = W01 / W02 (Python入口 script|module と 実配布EXE)。
Python入口は既存harness(tests/test_startup_windows.py --uat)、実EXEは tests/release_uat_support.py の
隔離copy(prepare/start/peer/inspect/stop)を使う。製品は import/patch せず、EXEへ試験引数を渡さない。

usage (リポジトリ直下で):
  .venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-drivers/uat_row.py --row W01/normal@script
  ... --row W01/zoomed@script
  ... --row W01/normal@production-exe
  ... --row W01/normal@script --selftest      (機構確認用。canned回答。証拠にしない)

利用者の入力はすべて逐語で session JSON の raw_inputs に保存する(貼り付けを疑う入力は一度拒否して取り直し、
拒否した入力も保存する)。回答はキーボードで短く入力する。右クリック貼り付け/Ctrl+Vは使わない。
session JSON は 06-05-evidence/ に保存し、selftest は 06-05-evidence/selftest/ に分ける。
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import re
import subprocess
import sys
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
    def __init__(self, spec, selftest):
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
        p = self.prompter
        p.show(f"== {self.spec} (Python入口 {self.entry}) を開始します ==")
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
                say(
                    "このあと二次起動します。マウスで入力欄などをクリックしないでください。"
                )
            p.enter("準備ができたら Enter を押してください。この直後に二次起動します。")
            self.step("peer")
            peer = harness("peer", "--run", run, "--entry", self.entry, timeout=60)
            self.session["harness_peer"] = {
                k: peer[k] for k in ("returncode", "stderr_tail", "json")
            }
            time.sleep(1.5)
            after = main_windows(pids)
            fg1 = S.foreground_info()
            self.step("after-peer", windows=after, foreground=fg1)
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
        out = (
            out_dir
            / f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        S.write_json(out, self.session)
        say(f"記録を保存しました: {out}")
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True, help="例: W01/normal@script")
    ap.add_argument(
        "--selftest", action="store_true", help="機構確認用(canned回答・証拠にしない)"
    )
    args = ap.parse_args()
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
