# ruff: noqa: E501
"""UIスレッド診断(読み取り専用)。debug: w02-preview-peer-expired 用。

背景: W02/preview@module で、一次PageFolioのTkメインスレッドが要求受理後の約15.5秒間、50ms周期の
`_poll`(Tcl after)を実行せず、二次起動の5秒の締切を超えた(近因は確定・根因は未確定)。
保全証拠には「UIスレッドがその間なにをしていたか」の記録が無い。この模組は、駆動(uat_row.py)が
隔離PageFolio(一次)のUIスレッドを外から約100msごとに観測し、次の4つを判別できる材料を残す。

  A. UIスレッドがネイティブ待機でブロックされている(ctx切替が止まり、CPUも進まない)
  B. メッセージは捌いているがTclのタイマーが発火しない(ctx切替は進む・WM_NULLに応答する)
  C. CPUを消費している(スレッドCPU時間/サイクルが進む)
  D. モーダルループ(GetGUIThreadInfoのメニュー/移動サイズ/ポップアップのフラグ)

実測で分かったこと(使い捨てTcl/Tkプロセス): 待機理由(wait_reason)はTkのidleのメッセージ待ちもtime.sleepで塞がれた
状態も同じ UserRequest で、単独では判別材料にならない。判別に効くのは ctx切替の増加(idle: 毎秒50〜80、塞がれる: 0)・
スレッドCPU/サイクルの増加・WM_NULLの応答・IsHungAppWindow・GetGUIThreadInfoのflag・他スレッドのCPU時間。

使うAPIはすべて読み取りだけ。製品のprocess/threadを止めない・書き込まない・前景も入力も変えない。
  - OpenProcess は PROCESS_QUERY_LIMITED_INFORMATION のみ。OpenThread は2種類だけ:
    THREAD_QUERY_LIMITED_INFORMATION(CPU時間)と、THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT(0x48。
    ThreadLastSystemCall の読み取り専用。実測: LIMITED だけでは STATUS_ACCESS_DENIED)。
    SUSPEND_RESUME / SET_CONTEXT / TERMINATE などの権限は一度も要求しない。
  - GetGUIThreadInfo / GetThreadTimes / QueryThreadCycleTime / NtQuerySystemInformation(SystemProcessInformation) /
    NtQueryInformationThread(ThreadLastSystemCall=21) / GetProcessTimes / GetExitCodeProcess / K32GetProcessMemoryInfo /
    EnumWindows / GetClassNameW / InternalGetWindowText / IsWindow / IsWindowVisible / GetWindowThreadProcessId /
    IsHungAppWindow / GetTickCount64。
  - SendMessageTimeoutW(WM_NULL) だけは入力を作らないがUIスレッドへメッセージを1通送るため、
    別フラグ(--wm-null-probe。既定OFF)のときだけ呼ぶ。OFFのときは1回も呼ばない。
  - SendInput / SetForegroundWindow / SetCursorPos / keybd_event / mouse_event / SuspendThread / GetThreadContext /
    DebugActiveProcess は一切使わない(check_offline が本ファイルのコードを静的に検査する)。
    THREAD_GET_CONTEXT は「ThreadLastSystemCall を読むための権限ビット」であり、コンテキストの取得は行わない。

外部見張り(--external-wake-ms。既定OFF。debug: w02-preview-peer-expired の対策の実機検証。利用者が範囲を限って承認済み):
  これまでの診断は「眺めるだけ」だったが、この機能だけは一次PageFolioのUIスレッドへ外から介入する。介入は次の1つに限る。
    PostThreadMessageW(UIスレッドのtid, WM_NULL, 0, 0)  を、100〜150msごとに「投稿」する(送信ではない。相手の処理を待たない)。
  根拠: 停止の機構は「Tcl通知器がタイムアウトの無い GetMessageW で眠る」ことで、投稿されたスレッドメッセージ1通で復帰する
  (使い捨てTclプロセスで再現・確認済み)。WM_NULL は何もしないメッセージで、アプリの状態は変えない。
  投稿の前に毎回、宛先 tid が「対象 pid(作成時刻が expected_created と一致)の生きたスレッド」であることを確かめ、
  確かめられなければ投稿しない(verify_post_target)。SendMessage 系・前景/入力系のAPIは使わない(check_offline が静的に検査する)。
  OFF のときはスレッドも作らず、PostThreadMessageW を一度も呼ばない。--wm-null-probe(SendMessageTimeoutW)とは併用しない。

待ち先の特定(ThreadLastSystemCall。実機実測で確認済み): 待機中のスレッドの「最後のシステムコール番号と第1引数」が読める。
ブロック中の SendMessage は NtUserMessageCall で、第1引数が宛先の窓ハンドル(HWND)。これを IsWindow /
GetWindowThreadProcessId / GetClassNameW / InternalGetWindowText(メッセージを送らずに窓構造体から読む)で
宛先の所有 pid/tid・クラス・タイトルに解決し、宛先スレッドの状態/待機理由/ctx切替(同じ NtQuerySystemInformation の
スナップショットから)と、宛先スレッド自身の最後のシステムコール(さらにHWNDなら次の宛先へ。最大3段)を残す。
システムコール番号→名前は、この機械の ntdll.dll / win32u.dll のスタブ(mov eax, imm32)から作る。

時刻の整合: 各サンプルに壁時計(uat_row.now() と同じ書式のISO)・単調時計の経過(InputMonitor と同じ起点)・
GetTickCount64(製品の tick_ms と同じ時計。stderrの deadline=/tick= と直接比べられる)・phase を持たせる。
"""

import ast
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import struct
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PURPOSE = "debug-frequency"
DEBUG_SESSION = "w02-preview-peer-expired"
DEBUG_DIRNAME = "debug-w02-preview-peer-expired"

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
THREAD_QUERY_LIMITED_INFORMATION = 0x0800
THREAD_QUERY_INFORMATION = 0x0040
THREAD_GET_CONTEXT = 0x0008
# ThreadLastSystemCall(NtQueryInformationThread class 21)に必要な最小の権限(実測で確認)。
# SUSPEND_RESUME(0x2)・SET_CONTEXT(0x10)・TERMINATE(0x1)・SET_INFORMATION(0x20) などは含めない。
THREAD_SYSCALL_ACCESS = THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT
THREAD_LAST_SYSCALL_CLASS = 21
STATUS_UNSUCCESSFUL = 0xC0000001  # スレッドが待機中でないとき(正常。エラーにしない)
STATUS_ACCESS_DENIED = 0xC0000022
STILL_ACTIVE = 259
# SYSTEM_THREAD_INFORMATION.WaitTime は KeTickCount(1 tick = 15.625ms)。実測: 値 x 15.625 = その待機が始まった
# GetTickCount64 と一致した(待機の長さ = tick_ms - wait_time x 15.625)。
KE_TICK_MS = 15.625

# GetGUIThreadInfo.flags
GUI_CARETBLINKING = 0x1
GUI_INMOVESIZE = 0x2
GUI_INMENUMODE = 0x4
GUI_SYSTEMMENUMODE = 0x8
GUI_POPUPMENUMODE = 0x10
GUI_16BITTASK = 0x20
GUI_FLAG_NAMES = (
    (GUI_CARETBLINKING, "caret-blinking"),
    (GUI_INMOVESIZE, "in-move-size"),
    (GUI_INMENUMODE, "in-menu-mode"),
    (GUI_SYSTEMMENUMODE, "system-menu-mode"),
    (GUI_POPUPMENUMODE, "popup-menu-mode"),
    (GUI_16BITTASK, "16bit-task"),
)
MODAL_FLAGS = GUI_INMOVESIZE | GUI_INMENUMODE | GUI_SYSTEMMENUMODE | GUI_POPUPMENUMODE

THREAD_STATE_NAMES = {
    0: "Initialized",
    1: "Ready",
    2: "Running",
    3: "Standby",
    4: "Terminated",
    5: "Waiting",
    6: "Transition",
    7: "DeferredReady",
    8: "GateWaitObsolete",
    9: "WaitingForProcessInSwap",
}
WAIT_REASON_NAMES = {
    0: "Executive",
    1: "FreePage",
    2: "PageIn",
    3: "PoolAllocation",
    4: "DelayExecution",
    5: "Suspended",
    6: "UserRequest",
    7: "WrExecutive",
    8: "WrFreePage",
    9: "WrPageIn",
    10: "WrPoolAllocation",
    11: "WrDelayExecution",
    12: "WrSuspended",
    13: "WrUserRequest",
    14: "WrEventPair",
    15: "WrQueue",
    16: "WrLpcReceive",
    17: "WrLpcReply",
    18: "WrVirtualMemory",
    19: "WrPageOut",
    20: "WrRendezvous",
    21: "WrKeyedEvent",
    22: "WrTerminated",
    23: "WrProcessInSwap",
    24: "WrCpuRateControl",
    25: "WrCalloutStack",
    26: "WrKernel",
    27: "WrResource",
    28: "WrPushLock",
    29: "WrMutex",
    30: "WrQuantumEnd",
    31: "WrDispatchInt",
    32: "WrPreempted",
    33: "WrYieldExecution",
    34: "WrFastMutex",
    35: "WrGuardedMutex",
    36: "WrRundown",
    37: "WrAlertByThreadId",
    38: "WrDeferredPreempt",
}

# WM_NULL を送るphase(それ以前は何も送らない)。peer前の待ち時間で窓が止まり始める可能性も見るため
# awaiting-enter から。
WM_NULL_PHASES = ("awaiting-enter", "peer", "diag-hold", "post-peer")

# 外部見張り(PostThreadMessageW)。WM_NULL は何もしないメッセージ。
WM_NULL = 0
WAKE_PERIOD_RANGE_MS = (
    100,
    150,
)  # 利用者が承認した周期の範囲(CLIはこの範囲だけ受け付ける)
WAKE_MAX_POSTS = 6000  # 1回の観測での投稿の上限(スレッドのメッセージキューの既定上限10000件に届かせない安全弁)
# 失敗/拒否の内訳として残す件数の上限(件数そのものは全件数える)
WAKE_FAILURE_LOG_MAX = 50
WAKE_LONG_GAP_LOG_MAX = 20
# 見張りが「期待どおりに動いた」とみなす最低限の目安(この回の結果を見張りありとして読んでよいか。除外はせず、印を付けるだけ)
WAKE_MIN_POSTS = 20  # 成功した投稿の最小件数(周期120msなら約2.4秒分。実際の1回は数分)
WAKE_MAX_FAIL_RATIO = 0.02  # 失敗してよい割合の上限(最低2件までは許す)
WAKE_MAX_GAP_FACTOR = 5  # 成功した投稿の最大間隔の上限(周期の何倍まで)
WAKE_MAX_SKIPPED = 10  # 見送り(UIスレッド未特定など)の上限
# 「タイムアウトの無い GetMessage で待っている」とみなす最後のシステムコールと、停止とみなす待機の長さ。
# 見張り周期(100〜150ms)の約3倍。健全なTclはここに現れない(実測: 通常の待機は NtUserMsgWaitForMultipleObjectsEx)。
GETMESSAGE_CALL = "NtUserGetMessage"
GETMESSAGE_STALL_MS = 400

# 判別のしきい値(実測: Tkのidleはctx切替が毎秒約78、afterコールバックでsleepして塞ぐと0。タグは判別の材料で根因の断定ではない)
STALL_MIN_S = 1.0  # ctx切替が連続して増えない区間をこれ以上で無スケジュール区間とする
CPU_SHARE_BUSY = 0.30  # 区間の壁時計に対しスレッドCPU時間がこの割合以上 = CPU消費中
CTX_PER_S_ALIVE = 5.0  # 区間でctx切替が毎秒これ以上 = スレッドは動いている
CTX_PER_S_FLAT = 2.0  # 区間でctx切替が毎秒これ未満 = スレッドはほぼ起床していない
MODAL_ROW_RATIO = 0.5  # 区間の行のうちモーダルflagの割合がこれ以上 = モーダルループ

SAMPLE_COLUMNS = (
    "seq",
    "t",
    "tick_ms",
    "elapsed_s",
    "phase",
    "cost_ms",
    "tid",
    "hwnd",
    "gui_flags",
    "hwnd_active",
    "hwnd_focus",
    "hwnd_capture",
    "hwnd_menu_owner",
    "hwnd_move_size",
    "cpu_kernel_ms",
    "cpu_user_ms",
    "cycles_m",
    "state",
    "wait_reason",
    "ctx_switches",
    "wait_time_ms",
    "page_faults",
    "pf_gmpi",
    "hard_faults",
    "working_set_kb",
    "threads",
    "io_read",
    "io_write",
    "io_other",
    "others_cpu_ms",
    "busy_threads",
    "hung",
    "gone",
    "errors",
    # 以下は待ち先診断で追加した列(末尾に追記。古いサイドカーは列が少ないだけで同じ読み方ができる)
    "syscall",  # UIスレッドの最後のシステムコール名(待機中のみ)
    "sc_arg",  # その第1引数(整数)
    "sc_status",  # NtQueryInformationThread のステータス(0=成功、0xC0000001=待機中でない)
    "sc_wait_ms",  # 現在の待機の長さ(ThreadLastSystemCall の WaitTime=100ns単位 を ms にした値)
    "wait_target",  # 第1引数が窓なら宛先の解決結果(dict。連鎖は next に入る)
    "others_ctx",  # UI以外のスレッドの [tid, ctx切替, 待機理由] の配列
    # 以下は外部見張りで追加した列(末尾に追記。見張りOFFの回は空)
    "wake_ok",  # この時点までに成功した WM_NULL 投稿の累計
    "wake_fail",  # この時点までの投稿の失敗 + 宛先確認の拒否の累計
)


def wall_now():
    """uat_row.now() と同じ書式(phase_log / InputMonitor の t と文字列で突き合わせられる)。"""
    return datetime.now(timezone.utc).isoformat()


def decode_gui_flags(flags):
    if flags is None:
        return []
    return [name for bit, name in GUI_FLAG_NAMES if flags & bit]


# ---------------------------------------------------------------------------
# SystemProcessInformation の解析(純関数。x64のレイアウト)
# ---------------------------------------------------------------------------
_SPI_HEAD = struct.Struct("<II")  # NextEntryOffset, NumberOfThreads
_SPI_THREAD = struct.Struct("<qqqI4xQQQiiIII4x")  # SYSTEM_THREAD_INFORMATION(80 bytes)
SPI_PROCESS_SIZE = 256  # SYSTEM_PROCESS_INFORMATION の固定部。Threads[] はここから
SPI_THREAD_SIZE = _SPI_THREAD.size


def _read_image_name(buf, offset, base_address):
    """SYSTEM_PROCESS_INFORMATION.ImageName(UNICODE_STRING。Buffer はバッファ内を指す絶対アドレス)を読む。

    base_address(バッファ先頭の実アドレス)が分からない場合や範囲外の場合は None。
    """
    if base_address is None:
        return None
    length, _maximum = struct.unpack_from("<HH", buf, offset + 56)
    (pointer,) = struct.unpack_from("<Q", buf, offset + 64)
    if not length or not pointer:
        return None
    start = pointer - base_address
    if start < 0 or start + length > len(buf):
        return None
    return bytes(buf[start : start + length]).decode("utf-16-le", errors="replace")


def parse_system_process_information(buf, pid, base_address=None):
    """NtQuerySystemInformation(SystemProcessInformation) のバッファから pid の1件を取り出す。

    戻り値: {"process": {...}, "threads": {tid: {...}}}。見つからなければ None。
    読むのはバッファだけ。オフセットは x64 の SYSTEM_PROCESS_INFORMATION / SYSTEM_THREAD_INFORMATION。
    base_address を渡すと process["image"](イメージ名)も読む(別プロセスを開かずに実行ファイル名が分かる)。
    """
    offset = 0
    total = len(buf)
    while offset + SPI_PROCESS_SIZE <= total:
        next_offset, thread_count = _SPI_HEAD.unpack_from(buf, offset)
        (unique_pid,) = struct.unpack_from("<Q", buf, offset + 80)
        if unique_pid == pid:
            (hard_faults,) = struct.unpack_from("<I", buf, offset + 16)
            create_time, user_time, kernel_time = struct.unpack_from(
                "<qqq", buf, offset + 32
            )
            (handles,) = struct.unpack_from("<I", buf, offset + 96)
            (page_faults,) = struct.unpack_from("<I", buf, offset + 128)
            (working_set,) = struct.unpack_from("<Q", buf, offset + 144)
            read_ops, write_ops, other_ops = struct.unpack_from(
                "<qqq", buf, offset + 208
            )
            process = {
                "threads": thread_count,
                "hard_faults": hard_faults,
                "create_time": create_time,
                "user_100ns": user_time,
                "kernel_100ns": kernel_time,
                "handles": handles,
                "page_faults": page_faults,
                "working_set": working_set,
                "read_ops": read_ops,
                "write_ops": write_ops,
                "other_ops": other_ops,
                "image": _read_image_name(buf, offset, base_address),
            }
            threads = {}
            base = offset + SPI_PROCESS_SIZE
            for index in range(thread_count):
                at = base + index * SPI_THREAD_SIZE
                if at + SPI_THREAD_SIZE > total:
                    break
                (
                    kernel,
                    user,
                    created,
                    wait_time,
                    start_address,
                    _client_pid,
                    client_tid,
                    _priority,
                    _base_priority,
                    ctx,
                    state,
                    wait_reason,
                ) = _SPI_THREAD.unpack_from(buf, at)
                threads[client_tid] = {
                    "kernel_100ns": kernel,
                    "user_100ns": user,
                    "create_time": created,
                    "wait_time": wait_time,
                    "start_address": start_address,
                    "ctx": ctx,
                    "state": THREAD_STATE_NAMES.get(state, f"state-{state}"),
                    "wait_reason": WAIT_REASON_NAMES.get(
                        wait_reason, f"wait-{wait_reason}"
                    ),
                }
            return {"process": process, "threads": threads}
        if next_offset == 0:
            break
        offset += next_offset
    return None


def build_fake_system_process_information(entries, base_address=0):
    """テスト用: entries=[{"pid","threads":[{...}],"image":str,...}] から SYSTEM_PROCESS_INFORMATION 列を組む。

    image を持つ entry は、ImageName.Buffer を base_address + (バッファ内オフセット) にする(実機と同じ形)。
    """
    out = bytearray()
    for index, entry in enumerate(entries):
        threads = entry.get("threads", [])
        image = entry.get("image")
        image_bytes = image.encode("utf-16-le") if image else b""
        fixed = SPI_PROCESS_SIZE + SPI_THREAD_SIZE * len(threads)
        size = fixed + len(image_bytes)
        block = bytearray(size)
        last = index == len(entries) - 1
        struct.pack_into("<II", block, 0, 0 if last else size, len(threads))
        if image_bytes:
            block[fixed:size] = image_bytes
            struct.pack_into("<HH", block, 56, len(image_bytes), len(image_bytes))
            struct.pack_into("<Q", block, 64, base_address + len(out) + fixed)
        struct.pack_into("<I", block, 16, entry.get("hard_faults", 0))
        struct.pack_into("<qqq", block, 32, entry.get("create_time", 0), 0, 0)
        struct.pack_into("<Q", block, 80, entry["pid"])
        struct.pack_into("<I", block, 96, entry.get("handles", 0))
        struct.pack_into("<I", block, 128, entry.get("page_faults", 0))
        struct.pack_into("<Q", block, 144, entry.get("working_set", 0))
        struct.pack_into("<qqq", block, 208, *entry.get("io", (0, 0, 0)))
        for t_index, thread in enumerate(threads):
            _SPI_THREAD.pack_into(
                block,
                SPI_PROCESS_SIZE + t_index * SPI_THREAD_SIZE,
                thread.get("kernel", 0),
                thread.get("user", 0),
                thread.get("created", 0),
                thread.get("wait_time", 0),
                0x1000,
                entry["pid"],
                thread["tid"],
                8,
                8,
                thread.get("ctx", 0),
                thread.get("state", 5),
                thread.get("wait", 13),
            )
        out += block
    return bytes(out)


# ---------------------------------------------------------------------------
# 実Win32(読み取り専用)
# ---------------------------------------------------------------------------
class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("flags", wt.DWORD),
        ("hwndActive", wt.HWND),
        ("hwndFocus", wt.HWND),
        ("hwndCapture", wt.HWND),
        ("hwndMenuOwner", wt.HWND),
        ("hwndMoveSize", wt.HWND),
        ("hwndCaret", wt.HWND),
        ("rcCaret", wt.RECT),
    ]


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _THREAD_LAST_SYSCALL(ctypes.Structure):
    """THREAD_LAST_SYSCALL_INFORMATION(Windows 10 RS3 以降の x64。24 bytes)。"""

    _fields_ = [
        ("FirstArgument", ctypes.c_void_p),
        ("SystemCallNumber", ctypes.c_ushort),
        ("Pad", ctypes.c_ushort * 3),
        ("WaitTime", ctypes.c_uint64),  # 100ns単位(実測)
    ]


def _filetime_int(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


# ---------------------------------------------------------------------------
# システムコール番号 -> 名前(この機械の ntdll.dll / win32u.dll のスタブから作る)
# ---------------------------------------------------------------------------
# 第1引数が窓ハンドル(HWND)のシステムコール。ブロック中の SendMessage は NtUserMessageCall(hwnd, msg, ...)。
# これ以外のシステムコールの第1引数は、IsWindow が真のときだけ「推定(speculative)」として窓に解決する。
HWND_FIRST_ARG_CALLS = frozenset(
    {
        "NtUserMessageCall",
        "NtUserSendEventMessage",
        "NtUserSetFocus",
        "NtUserSetParent",
        "NtUserDestroyWindow",
        "NtUserEnableWindow",
        "NtUserSetWindowLong",
        "NtUserSetWindowLongPtr",
        "NtUserSetForegroundWindow",
        "NtUserSetActiveWindow",
        "NtUserShowWindow",
        "NtUserShowWindowAsync",
        "NtUserSetWindowPos",
        "NtUserSetCapture",
        "NtUserRedrawWindow",
        "NtUserMoveWindow",
        "NtUserSetWindowPlacement",
        "NtUserSetWindowRgn",
    }
)
HWND_MIN_KNOWN = 0x100
HWND_MIN_SPECULATIVE = 0x10000
# 待機の種別ラベル(システムコール名から)
MESSAGE_LOOP_CALLS = frozenset(
    {
        "NtUserGetMessage",
        "NtUserRealInternalGetMessage",
        "NtUserPeekMessage",
        "NtUserRealWaitMessageEx",
        "NtUserWaitMessage",
    }
)


def hwnd_from_arg(value, minimum=HWND_MIN_KNOWN):
    """システムコールの第1引数(ポインタ幅の整数)を窓ハンドル候補にする。窓ハンドルは32bit値(符号拡張あり)。"""
    if not value:
        return None
    number = int(value)
    if number >> 32 not in (0, 0xFFFFFFFF):
        return None
    low = number & 0xFFFFFFFF
    return low if low >= minimum else None


def _pe_syscall_stubs(path):
    """PEファイルのエクスポートから、x64 の syscall スタブ(mov r10,rcx; mov eax,imm32)を持つ名前を取る。

    -> [(syscall番号, 名前)]。ファイルを読むだけ。
    """
    data = Path(path).read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:  # PE32+
        raise OSError(0, f"not a PE32+ file: {path}")
    exp_rva, _exp_size = struct.unpack_from("<II", data, opt + 112)
    sections = []
    for index in range(nsec):
        vsize, va, rsize, raw = struct.unpack_from(
            "<IIII", data, opt + optsz + 40 * index + 8
        )
        sections.append((va, max(vsize, rsize), raw))

    def rva_to_offset(rva):
        for va, size, raw in sections:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError(rva)

    base = rva_to_offset(exp_rva)
    n_funcs, n_names, a_funcs, a_names, a_ords = struct.unpack_from(
        "<IIIII", data, base + 20
    )
    names = struct.unpack_from(f"<{n_names}I", data, rva_to_offset(a_names))
    ordinals = struct.unpack_from(f"<{n_names}H", data, rva_to_offset(a_ords))
    funcs = struct.unpack_from(f"<{n_funcs}I", data, rva_to_offset(a_funcs))
    out = []
    for name_rva, ordinal in zip(names, ordinals, strict=False):
        start = rva_to_offset(name_rva)
        name = data[start : data.index(b"\0", start)].decode("ascii", "replace")
        try:
            code_at = rva_to_offset(funcs[ordinal])
        except ValueError:
            continue  # フォワーダ等
        code = data[code_at : code_at + 8]
        if code[:4] == b"\x4c\x8b\xd1\xb8":
            out.append((struct.unpack_from("<I", code, 4)[0], name))
    return out


def load_syscall_names(system_root=None):
    """システムコール番号 -> 名前 の辞書と、その由来の情報を返す。失敗しても例外にせず空の辞書を返す。

    番号はOSのビルドごとに変わるため、実行中のこの機械の ntdll.dll / win32u.dll から作る。
    同じ番号に複数の名前があるときは Nt* を Zw* より、win32u を ntdll より優先する。
    """
    info = {"files": [], "entries": 0, "error": None}
    ranked = {}
    try:
        root = Path(system_root or os.environ.get("SystemRoot") or "C:\\Windows")
        for dll in ("ntdll.dll", "win32u.dll"):
            path = root / "System32" / dll
            stubs = _pe_syscall_stubs(path)
            info["files"].append({"file": dll, "stubs": len(stubs)})
            for number, name in stubs:
                key = (
                    0 if name.startswith("Nt") else 1,
                    0 if dll == "win32u.dll" else 1,
                    name,
                )
                if number not in ranked or key < ranked[number][0]:
                    ranked[number] = (key, name)
    except Exception as error:
        info["error"] = repr(error)
    names = {number: item[1] for number, item in ranked.items()}
    info["entries"] = len(names)
    return names, info


def syscall_label(names, number):
    """番号 -> 表示名。名前が引けないときは syscall-0x....。"""
    if number is None:
        return None
    return names.get(number) or f"syscall-{number:#x}"


def _raise_last(api):
    code = ctypes.get_last_error()
    raise OSError(0, f"{api} failed", None, code)


class Win32Native:
    """UIスレッド診断が使う読み取り専用のネイティブ層。偽物(FakeNative)と差し替え可能。"""

    def __init__(self):
        if ctypes.sizeof(ctypes.c_void_p) != 8:
            raise OSError("64bit Pythonのみ対応(SystemProcessInformationのレイアウト)")
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        self.nt = ctypes.WinDLL("ntdll", use_last_error=False)
        self._bind()
        self.open_log = []  # (kind, access) 開いた権限の記録(最小権限の確認用)
        self.wm_null_calls = 0
        self.post_calls = (
            0  # PostThreadMessageW(WM_NULL) を呼んだ回数(外部見張り。OFFなら0のまま)
        )
        self._process = None
        self._pid = None
        self._handle_lock = (
            threading.Lock()
        )  # サンプラと外部見張りの2スレッドが同じtidのハンドルを開かないように
        self._threads = {}
        self._sc_threads = {}  # tid -> ThreadLastSystemCall 用のハンドル(開けなかった tid は None)
        self._sc_errors = {}
        self._buf = ctypes.create_string_buffer(1 << 20)
        self._snap_ok = False
        self._snap_base = None

    def _bind(self):
        k, u, nt = self.k, self.u, self.nt
        k.GetTickCount64.restype = ctypes.c_ulonglong
        k.GetTickCount64.argtypes = []
        k.OpenProcess.restype = wt.HANDLE
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenThread.restype = wt.HANDLE
        k.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.CloseHandle.restype = wt.BOOL
        k.CloseHandle.argtypes = [wt.HANDLE]
        ft = ctypes.POINTER(wt.FILETIME)
        k.GetProcessTimes.restype = wt.BOOL
        k.GetProcessTimes.argtypes = [wt.HANDLE, ft, ft, ft, ft]
        k.GetThreadTimes.restype = wt.BOOL
        k.GetThreadTimes.argtypes = [wt.HANDLE, ft, ft, ft, ft]
        k.GetExitCodeProcess.restype = wt.BOOL
        k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
        k.GetExitCodeThread.restype = wt.BOOL
        k.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
        k.GetProcessIdOfThread.restype = wt.DWORD
        k.GetProcessIdOfThread.argtypes = [wt.HANDLE]
        k.QueryThreadCycleTime.restype = wt.BOOL
        k.QueryThreadCycleTime.argtypes = [
            wt.HANDLE,
            ctypes.POINTER(ctypes.c_ulonglong),
        ]
        k.K32GetProcessMemoryInfo.restype = wt.BOOL
        k.K32GetProcessMemoryInfo.argtypes = [
            wt.HANDLE,
            ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
            wt.DWORD,
        ]
        enum_proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        self._enum_proc = enum_proc
        u.EnumWindows.restype = wt.BOOL
        u.EnumWindows.argtypes = [enum_proc, wt.LPARAM]
        u.GetWindowThreadProcessId.restype = wt.DWORD
        u.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
        u.IsWindowVisible.restype = wt.BOOL
        u.IsWindowVisible.argtypes = [wt.HWND]
        u.GetClassNameW.restype = ctypes.c_int
        u.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
        u.GetGUIThreadInfo.restype = wt.BOOL
        u.GetGUIThreadInfo.argtypes = [wt.DWORD, ctypes.POINTER(_GUITHREADINFO)]
        u.IsHungAppWindow.restype = wt.BOOL
        u.IsHungAppWindow.argtypes = [wt.HWND]
        u.IsWindow.restype = wt.BOOL
        u.IsWindow.argtypes = [wt.HWND]
        u.IsWindowEnabled.restype = wt.BOOL
        u.IsWindowEnabled.argtypes = [wt.HWND]
        u.GetWindow.restype = wt.HWND
        u.GetWindow.argtypes = [wt.HWND, wt.UINT]
        # InternalGetWindowText は窓構造体からタイトルを直接読む(GetWindowText と違い、窓へメッセージを送らない)。
        try:
            self._internal_get_window_text = u.InternalGetWindowText
            self._internal_get_window_text.restype = ctypes.c_int
            self._internal_get_window_text.argtypes = [
                wt.HWND,
                wt.LPWSTR,
                ctypes.c_int,
            ]
        except AttributeError:
            self._internal_get_window_text = None
        u.SendMessageTimeoutW.restype = ctypes.c_ssize_t
        u.SendMessageTimeoutW.argtypes = [
            wt.HWND,
            wt.UINT,
            wt.WPARAM,
            wt.LPARAM,
            wt.UINT,
            wt.UINT,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        # 外部見張り用。投稿のみ(送信ではない)。post_wm_null だけが呼ぶ。
        u.PostThreadMessageW.restype = wt.BOOL
        u.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
        nt.NtQuerySystemInformation.restype = ctypes.c_long
        nt.NtQuerySystemInformation.argtypes = [
            wt.ULONG,
            ctypes.c_void_p,
            wt.ULONG,
            ctypes.POINTER(wt.ULONG),
        ]
        nt.NtQueryInformationThread.restype = ctypes.c_long
        nt.NtQueryInformationThread.argtypes = [
            wt.HANDLE,
            wt.ULONG,
            ctypes.c_void_p,
            wt.ULONG,
            ctypes.POINTER(wt.ULONG),
        ]

    # -- 基本 -----------------------------------------------------------------
    def tick_ms(self):
        return int(self.k.GetTickCount64())

    def open_target(self, pid):
        """最小権限(PROCESS_QUERY_LIMITED_INFORMATION)でプロセスを開く。作成時刻(FILETIME整数)を返す。"""
        self.close_target()
        access = PROCESS_QUERY_LIMITED_INFORMATION
        self.open_log.append(("process", access))
        handle = self.k.OpenProcess(access, False, pid)
        if not handle:
            _raise_last("OpenProcess")
        self._process, self._pid = handle, pid
        created, exited, kernel, user = (wt.FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            _raise_last("GetProcessTimes")
        return {"created": _filetime_int(created)}

    def close_target(self):
        if self._process:
            self.k.CloseHandle(self._process)
        self._process = None
        for handle in self._threads.values():
            if handle:
                self.k.CloseHandle(handle)
        self._threads = {}
        for handle in self._sc_threads.values():
            if handle:
                self.k.CloseHandle(handle)
        self._sc_threads = {}
        self._sc_errors = {}

    def close(self):
        self.close_target()

    def process_alive(self):
        if not self._process:
            return None
        code = wt.DWORD()
        if not self.k.GetExitCodeProcess(self._process, ctypes.byref(code)):
            _raise_last("GetExitCodeProcess")
        return code.value == STILL_ACTIVE

    # -- UIスレッドの特定 --------------------------------------------------------
    def find_ui_thread(self, pid):
        """pid所有のトップレベル窓から、UIスレッド(窓を持つスレッド)を決める。

        可視のTkTopLevel > 可視 > TkTopLevel > 任意 の順。窓が無ければ None。
        EnumWindows/IsWindowVisible/GetClassNameW はメッセージを送らない。
        """
        found = []

        def callback(hwnd, _lparam):
            owner = wt.DWORD()
            tid = self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid:
                cls = ctypes.create_unicode_buffer(128)
                self.u.GetClassNameW(hwnd, cls, 128)
                found.append(
                    (
                        int(hwnd or 0),
                        int(tid),
                        cls.value,
                        bool(self.u.IsWindowVisible(hwnd)),
                    )
                )
            return True

        self.u.EnumWindows(self._enum_proc(callback), 0)
        if not found:
            return None

        def rank(item):
            _hwnd, _tid, cls, visible = item
            return (0 if visible else 2) + (0 if cls == "TkTopLevel" else 1)

        hwnd, tid, cls, visible = sorted(found, key=rank)[0]
        return {
            "tid": tid,
            "hwnd": hwnd,
            "class": cls,
            "visible": visible,
            "source": "window",
        }

    def gui_thread_info(self, tid):
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not self.u.GetGUIThreadInfo(tid, ctypes.byref(info)):
            _raise_last("GetGUIThreadInfo")
        return {
            "flags": int(info.flags),
            "active": int(info.hwndActive or 0),
            "focus": int(info.hwndFocus or 0),
            "capture": int(info.hwndCapture or 0),
            "menu_owner": int(info.hwndMenuOwner or 0),
            "move_size": int(info.hwndMoveSize or 0),
        }

    def _thread_handle(self, tid):
        with self._handle_lock:
            handle = self._threads.get(tid)
            if handle:
                return handle
            access = THREAD_QUERY_LIMITED_INFORMATION
            self.open_log.append(("thread", access))
            handle = self.k.OpenThread(access, False, tid)
            if not handle:
                _raise_last("OpenThread")
            self._threads[tid] = handle
            return handle

    def thread_cpu(self, tid):
        handle = self._thread_handle(tid)
        created, exited, kernel, user = (wt.FILETIME() for _ in range(4))
        if not self.k.GetThreadTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            _raise_last("GetThreadTimes")
        cycles = ctypes.c_ulonglong(0)
        if not self.k.QueryThreadCycleTime(handle, ctypes.byref(cycles)):
            _raise_last("QueryThreadCycleTime")
        return {
            "kernel_100ns": _filetime_int(kernel),
            "user_100ns": _filetime_int(user),
            "cycles": int(cycles.value),
        }

    def system_snapshot(self, pid):
        self._snap_ok = False
        size = len(self._buf)
        for _ in range(6):
            need = wt.ULONG(0)
            status = self.nt.NtQuerySystemInformation(
                5, self._buf, size, ctypes.byref(need)
            )
            if status == 0:
                break
            if (status & 0xFFFFFFFF) == 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH
                size = max(int(need.value) + 65536, size * 2)
                self._buf = ctypes.create_string_buffer(size)
                continue
            raise OSError(
                0, f"NtQuerySystemInformation status=0x{status & 0xFFFFFFFF:08X}"
            )
        else:
            raise OSError(0, "NtQuerySystemInformation: buffer growth failed")
        self._snap_ok = True
        self._snap_base = ctypes.addressof(self._buf)
        return parse_system_process_information(self._buf, pid, self._snap_base)

    def other_process_snapshot(self, pid):
        """直前の system_snapshot と同じバッファから、別の pid の1件を取り出す(別プロセスは開かない)。"""
        if not self._snap_ok:
            return None
        return parse_system_process_information(self._buf, pid, self._snap_base)

    def process_memory(self):
        if not self._process:
            return None
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(_PROCESS_MEMORY_COUNTERS)
        if not self.k.K32GetProcessMemoryInfo(
            self._process, ctypes.byref(counters), counters.cb
        ):
            _raise_last("K32GetProcessMemoryInfo")
        return {
            "page_faults": int(counters.PageFaultCount),
            "working_set": int(counters.WorkingSetSize),
        }

    def is_hung(self, hwnd):
        return bool(self.u.IsHungAppWindow(hwnd))

    # -- 待ち先の診断(読み取り専用) ---------------------------------------------------
    def _syscall_handle(self, tid):
        """ThreadLastSystemCall 用に THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT だけで開く(キャッシュ)。"""
        if tid in self._sc_threads:
            handle = self._sc_threads[tid]
            if handle:
                return handle
            raise OSError(0, "OpenThread failed", None, self._sc_errors.get(tid, 5))
        if (
            len(self._sc_threads) >= 96
        ):  # 異常に増えたら捨てる(他プロセスのスレッドを辿った分)
            for old in self._sc_threads.values():
                if old:
                    self.k.CloseHandle(old)
            self._sc_threads = {}
        access = THREAD_SYSCALL_ACCESS
        self.open_log.append(("thread-syscall", access))
        handle = self.k.OpenThread(access, False, tid)
        if not handle:
            code = ctypes.get_last_error()
            self._sc_threads[tid] = None
            self._sc_errors[tid] = code
            raise OSError(0, "OpenThread failed", None, code)
        self._sc_threads[tid] = handle
        return handle

    def thread_syscall(self, tid):
        """待機中のスレッドの最後のシステムコール番号と第1引数。待機中でなければ status が非0(エラーではない)。

        スレッドは止めない。THREAD_GET_CONTEXT は ThreadLastSystemCall を読むための権限ビットで、
        コンテキストの取得や停止は行わない。
        """
        handle = self._syscall_handle(tid)
        info = _THREAD_LAST_SYSCALL()
        returned = wt.ULONG(0)
        status = (
            self.nt.NtQueryInformationThread(
                handle,
                THREAD_LAST_SYSCALL_CLASS,
                ctypes.byref(info),
                ctypes.sizeof(info),
                ctypes.byref(returned),
            )
            & 0xFFFFFFFF
        )
        if status != 0:
            return {
                "status": status,
                "number": None,
                "first_arg": None,
                "wait_100ns": None,
            }
        return {
            "status": 0,
            "number": int(info.SystemCallNumber),
            "first_arg": int(info.FirstArgument or 0),
            "wait_100ns": int(info.WaitTime),
        }

    def process_windows(self, pid, limit=24):
        """pid 所有のトップレベル窓の一覧(モーダルダイアログ等が居ないかを見る材料)。メッセージは送らない。

        EnumWindows / GetWindowThreadProcessId / GetClassNameW / InternalGetWindowText / IsWindowVisible /
        IsWindowEnabled / GetWindow(GW_OWNER) はいずれも窓プロシージャを呼ばない。
        """
        found = []

        def callback(hwnd, _lparam):
            owner = wt.DWORD()
            tid = self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and len(found) < limit:
                cls = ctypes.create_unicode_buffer(128)
                self.u.GetClassNameW(hwnd, cls, 128)
                title = None
                if self._internal_get_window_text is not None:
                    buffer = ctypes.create_unicode_buffer(256)
                    self._internal_get_window_text(hwnd, buffer, 256)
                    title = buffer.value
                found.append(
                    {
                        "hwnd": int(hwnd or 0),
                        "tid": int(tid),
                        "class": cls.value,
                        "title": title,
                        "visible": bool(self.u.IsWindowVisible(hwnd)),
                        "enabled": bool(self.u.IsWindowEnabled(hwnd)),
                        "owner": int(self.u.GetWindow(hwnd, 4) or 0),  # GW_OWNER
                    }
                )
            return True

        self.u.EnumWindows(self._enum_proc(callback), 0)
        return found

    def window_info(self, hwnd):
        """窓ハンドルの所有 pid/tid・クラス・タイトルなど。窓でなければ None。メッセージは送らない。

        IsWindow / GetWindowThreadProcessId / GetClassNameW / IsWindowVisible / IsHungAppWindow /
        InternalGetWindowText はいずれも相手の窓プロシージャを呼ばない(宛先がブロック中でも戻る)。
        """
        if not self.u.IsWindow(hwnd):
            return None
        owner = wt.DWORD()
        tid = self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        cls = ctypes.create_unicode_buffer(128)
        self.u.GetClassNameW(hwnd, cls, 128)
        title = None
        if self._internal_get_window_text is not None:
            buffer = ctypes.create_unicode_buffer(256)
            self._internal_get_window_text(hwnd, buffer, 256)
            title = buffer.value
        return {
            "hwnd": int(hwnd),
            "pid": int(owner.value),
            "tid": int(tid),
            "class": cls.value,
            "title": title,
            "visible": bool(self.u.IsWindowVisible(hwnd)),
            "hung": bool(self.u.IsHungAppWindow(hwnd)),
        }

    def wm_null(self, hwnd, timeout_ms):
        """SendMessageTimeoutW(WM_NULL)。--wm-null-probe のときだけ呼ばれる。

        SMTO_ABORTIFHUNG(0x2): 5秒以上応答の無いスレッドには待たずに戻る(キューに積まない)。
        """
        self.wm_null_calls += 1
        out = ctypes.c_size_t(0)
        ctypes.set_last_error(0)
        started = time.perf_counter()
        ret = self.u.SendMessageTimeoutW(
            hwnd, 0, 0, 0, 0x0002, int(timeout_ms), ctypes.byref(out)
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        error = ctypes.get_last_error()
        if ret:
            result = "ok"
        elif error == 1460:  # ERROR_TIMEOUT
            result = "timeout"
        elif error == 1400:  # ERROR_INVALID_WINDOW_HANDLE
            result = "invalid-window"
        else:
            result = "failed"
        return {"result": result, "elapsed_ms": round(elapsed_ms, 1), "error": error}

    # -- 外部見張り(--external-wake-ms。投稿のみ) -----------------------------------------
    def verify_post_target(self, tid, hwnd, expected_created):
        """投稿の宛先 tid が「対象 pid(作成時刻が一致)の生きたスレッド」であることを、投稿の直前に確かめる(読み取りのみ)。

        1. 保持しているプロセスのハンドルの作成時刻(GetProcessTimes)が expected_created と一致し、生きている
           (ハンドルを持っている間は pid は再利用されない)。
        2. スレッドのハンドル(THREAD_QUERY_LIMITED_INFORMATION。保持中は tid も再利用されない)の
           GetProcessIdOfThread が対象 pid で、GetExitCodeThread が STILL_ACTIVE。
        3. 窓が分かっていて実在するなら、GetWindowThreadProcessId(hwnd) が (tid, 対象 pid) であること
           (窓が別スレッド/別プロセスへ移っていたら拒否する)。
        戻り値: {"ok": bool, "reason": 拒否の理由またはNone, ...}。例外にはしない(呼び出し側が拒否として記録する)。
        """
        if not self._process or not self._pid:
            return {"ok": False, "reason": "no-process-handle"}
        if expected_created is None:
            return {"ok": False, "reason": "no-expected-creation-time"}
        created, exited, kernel, user = (wt.FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(
            self._process,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return {
                "ok": False,
                "reason": f"GetProcessTimes-failed:{ctypes.get_last_error()}",
            }
        if _filetime_int(created) != int(expected_created):
            return {"ok": False, "reason": "process-creation-time-mismatch"}
        code = wt.DWORD()
        if not self.k.GetExitCodeProcess(self._process, ctypes.byref(code)):
            return {
                "ok": False,
                "reason": f"GetExitCodeProcess-failed:{ctypes.get_last_error()}",
            }
        if code.value != STILL_ACTIVE:
            return {"ok": False, "reason": "process-exited"}
        try:
            handle = self._thread_handle(tid)
        except OSError as error:
            return {
                "ok": False,
                "reason": f"OpenThread-failed:{getattr(error, 'winerror', None)}",
            }
        thread_pid = int(self.k.GetProcessIdOfThread(handle))
        if thread_pid != self._pid:
            return {
                "ok": False,
                "reason": "thread-not-in-target-process",
                "thread_pid": thread_pid,
            }
        thread_code = wt.DWORD()
        if not self.k.GetExitCodeThread(handle, ctypes.byref(thread_code)):
            return {
                "ok": False,
                "reason": f"GetExitCodeThread-failed:{ctypes.get_last_error()}",
            }
        if thread_code.value != STILL_ACTIVE:
            return {"ok": False, "reason": "thread-exited"}
        if hwnd and self.u.IsWindow(hwnd):
            owner = wt.DWORD()
            window_tid = int(self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner)))
            if window_tid != int(tid) or int(owner.value) != self._pid:
                return {"ok": False, "reason": "window-owner-mismatch"}
        return {"ok": True, "reason": None}

    def post_wm_null(self, tid):
        """PostThreadMessageW(tid, WM_NULL, 0, 0)。投稿だけ(相手の処理を待たない)。SendMessage は使わない。

        スレッドメッセージ(hwnd=NULL)なので、受け側はメッセージ取得(GetMessage/PeekMessage)から戻るだけで、
        窓プロシージャにも届かず、アプリの状態は変わらない。
        """
        self.post_calls += 1
        ctypes.set_last_error(0)
        ok = bool(self.u.PostThreadMessageW(int(tid), WM_NULL, 0, 0))
        return {"ok": ok, "error": 0 if ok else ctypes.get_last_error()}


# ---------------------------------------------------------------------------
# stderr のtail(一次側の「起動terminal」を実時間で拾う)と解析(純関数)
# ---------------------------------------------------------------------------
RE_TERMINAL = re.compile(
    r"terminal: (?P<id>[0-9a-fA-F]+) / (?P<result>\w+) / deadline=(?P<deadline>\d+) / tick=(?P<tick>\d+)"
)
RE_ACCEPTED = re.compile(r"accepted: (?P<id>[0-9a-fA-F]+) / deadline=(?P<deadline>\d+)")
RE_OS_ERROR = re.compile(r"os_error=(?P<err>\d+)")


def parse_log_events(text):
    """stderr全文から要求関連のイベントを抜く(DEBUG:の二重行は同一内容として1件にまとめる)。"""
    events = []
    seen = set()
    for line in text.splitlines():
        match = RE_TERMINAL.search(line)
        if match:
            key = ("terminal", match["id"], match["tick"])
            if key not in seen:
                seen.add(key)
                events.append(
                    {
                        "kind": "terminal",
                        "id": match["id"],
                        "result": match["result"],
                        "deadline_tick": int(match["deadline"]),
                        "tick_ms": int(match["tick"]),
                    }
                )
            continue
        match = RE_ACCEPTED.search(line)
        if match:
            key = ("accepted", match["id"], match["deadline"])
            if key not in seen:
                seen.add(key)
                events.append(
                    {
                        "kind": "accepted",
                        "id": match["id"],
                        "deadline_tick": int(match["deadline"]),
                    }
                )
            continue
        match = RE_OS_ERROR.search(line)
        if match:
            key = ("os_error", line.strip())
            if key not in seen:
                seen.add(key)
                events.append({"kind": "os_error", "os_error": int(match["err"])})
    return events


class LogTail:
    """追記されるログを読み取り専用で追う。"""

    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self._carry = b""
        self.error = None

    def poll(self):
        """-> 新しく読めた完結行のリスト(文字列)。"""
        try:
            with self.path.open("rb") as handle:
                handle.seek(self.offset)
                data = handle.read()
        except FileNotFoundError:
            return []
        except OSError as error:
            self.error = repr(error)
            return []
        if not data:
            return []
        self.offset += len(data)
        data = self._carry + data
        *lines, self._carry = data.split(b"\n")
        return [line.decode("utf-8", errors="replace") for line in lines]


# ---------------------------------------------------------------------------
# 待ち先の解決(ネイティブ層は引数。読み取りだけ)
# ---------------------------------------------------------------------------
def _compact_thread(thread, tick_ms):
    """SYSTEM_THREAD_INFORMATION の1件から、待ち先スレッドの状態を短くまとめる。"""
    if not thread:
        return None
    since = None
    waited = None
    if thread.get("wait_time"):
        since = round(thread["wait_time"] * KE_TICK_MS)
        if tick_ms is not None:
            waited = max(0, tick_ms - since)
    return {
        "state": thread.get("state"),
        "wait_reason": thread.get("wait_reason"),
        "ctx": thread.get("ctx"),
        "wait_since_tick_ms": since,
        "waited_ms": waited,
        "cpu_ms": round(
            ((thread.get("kernel_100ns") or 0) + (thread.get("user_100ns") or 0)) / 1e4,
            1,
        ),
    }


def describe_wait_target(
    native,
    names,
    arg,
    call_name,
    primary_pid,
    primary_threads,
    primary_image=None,
    tick_ms=None,
    depth=3,
    seen=None,
):
    """システムコールの第1引数(窓ハンドル候補)を、宛先の窓・所有者・待ち先スレッドの状態に解決する。

    - 既知のHWND先頭引数のシステムコール(HWND_FIRST_ARG_CALLS)は by="known-call"。窓でなければ valid=False を残す。
    - それ以外のシステムコールは by="speculative"。IsWindow が真で、値が十分大きいときだけ採用する。
    - 宛先スレッドが待機中なら、その最後のシステムコールも読み、さらにHWNDなら次の宛先へ辿る(depth段まで。
      循環は seen で止める)。個々の失敗は errors に残し、例外にしない。
    """
    seen = set() if seen is None else seen
    known = call_name in HWND_FIRST_ARG_CALLS
    hwnd = hwnd_from_arg(arg, HWND_MIN_KNOWN if known else HWND_MIN_SPECULATIVE)
    if hwnd is None:
        return None
    by = "known-call" if known else "speculative"
    if hwnd in seen:
        return {"hwnd": hwnd, "by": by, "cycle": True}
    seen.add(hwnd)
    errors = []
    try:
        info = native.window_info(hwnd)
    except Exception as error:
        info = None
        errors.append(f"window_info:{error!r}")
    if info is None:
        if not known:
            return None
        out = {"hwnd": hwnd, "by": by, "valid": False}
        if errors:
            out["errors"] = errors
        return out
    out = {
        "hwnd": hwnd,
        "by": by,
        "valid": True,
        "pid": info["pid"],
        "tid": info["tid"],
        "class": info["class"],
        "title": info["title"],
        "visible": info["visible"],
        "hung": info["hung"],
        "same_process": info["pid"] == primary_pid,
        "image": None,
        "thread": None,
    }
    threads = {}
    try:
        if info["pid"] == primary_pid:
            threads = primary_threads or {}
            out["image"] = primary_image
        else:
            other = native.other_process_snapshot(info["pid"])
            if other:
                threads = other["threads"]
                out["image"] = other["process"].get("image")
            else:
                errors.append("process-not-in-snapshot")
    except Exception as error:
        errors.append(f"process_snapshot:{error!r}")
    thread = threads.get(info["tid"])
    out["thread"] = _compact_thread(thread, tick_ms)
    if depth > 1 and thread and thread.get("state") == "Waiting":
        try:
            sc = native.thread_syscall(info["tid"])
        except Exception as error:
            out["thread_syscall"] = {"error": UiThreadProbe._err_text(error)}
        else:
            if sc["status"] != 0:
                out["thread_syscall"] = {"status": sc["status"]}
            else:
                name = syscall_label(names, sc["number"])
                out["thread_syscall"] = {
                    "name": name,
                    "arg": sc["first_arg"],
                    "wait_ms": round(sc["wait_100ns"] / 1e4, 1),
                }
                following = describe_wait_target(
                    native,
                    names,
                    sc["first_arg"],
                    name,
                    primary_pid,
                    primary_threads,
                    primary_image,
                    tick_ms,
                    depth - 1,
                    seen,
                )
                if following:
                    out["next"] = following
    if errors:
        out["errors"] = errors
    return out


def target_chain(target):
    """wait_target の連鎖(next をたどった一覧)。"""
    chain = []
    seen = 0
    while target and seen < 8:
        chain.append(target)
        target = target.get("next")
        seen += 1
    return chain


def format_wait_target(target):
    """wait_target を1行の読める文にする(報告・集計用)。"""
    parts = []
    for hop in target_chain(target):
        if not hop.get("valid", True):
            parts.append(f"hwnd {hop['hwnd']:#x}(窓として無効)")
            continue
        thread = hop.get("thread") or {}
        text = (
            f"hwnd {hop['hwnd']:#x} [{hop.get('class')} {hop.get('title')!r}] "
            f"pid {hop.get('pid')}/tid {hop.get('tid')} {hop.get('image') or '?'}"
            f"{'(同一プロセス)' if hop.get('same_process') else ''}"
            f" 状態={thread.get('state')}/{thread.get('wait_reason')} ctx={thread.get('ctx')}"
        )
        if hop.get("by") == "speculative":
            text += " (推定)"
        tsc = hop.get("thread_syscall") or {}
        if tsc.get("name"):
            text += f" 待機={tsc['name']}"
        parts.append(text)
    return " => ".join(parts)


def wait_target_key(target):
    """同じ待ち先かどうかの鍵(窓ハンドルの値ではなく、所有者とクラス/タイトルで見る)。"""
    return tuple(
        (hop.get("pid"), hop.get("tid"), hop.get("class"), hop.get("title"))
        for hop in target_chain(target)
    )


def collect_wait_targets(rows, limit=6):
    """行の wait_target を、同じ待ち先ごとにまとめる(行数の多い順)。"""
    groups = {}
    for row in rows:
        target = row.get("wait_target")
        if not target:
            continue
        key = (row.get("syscall"), wait_target_key(target))
        item = groups.get(key)
        if item is None:
            item = {
                "syscall": row.get("syscall"),
                "rows": 0,
                "first_t": row.get("t"),
                "last_t": row.get("t"),
                "text": format_wait_target(target),
                "target": target,
            }
            groups[key] = item
        item["rows"] += 1
        item["last_t"] = row.get("t")
    ordered = sorted(groups.values(), key=lambda g: -g["rows"])
    return ordered[:limit]


def others_ctx_delta(rows, limit=8):
    """UI以外のスレッドごとの ctx 切替の増分(最初と最後の行の差)。増えたものだけ、増分の多い順。"""
    with_ctx = [r for r in rows if r.get("others_ctx")]
    if len(with_ctx) < 2:
        return {}
    first = {tid: ctx for tid, ctx, _wait in with_ctx[0]["others_ctx"]}
    last = {tid: ctx for tid, ctx, _wait in with_ctx[-1]["others_ctx"]}
    delta = {
        str(tid): last[tid] - first[tid]
        for tid in last
        if tid in first and last[tid] != first[tid]
    }
    ordered = sorted(delta.items(), key=lambda kv: -kv[1])[:limit]
    return dict(ordered)


def wait_kind(syscalls, targets):
    """区間の待機の種別ラベル(根因の断定ではなく分類)。syscalls は {名前: 行数}。"""
    if not syscalls:
        return None
    top = max(syscalls.items(), key=lambda kv: kv[1])[0]
    if top == "NtUserMessageCall":
        valid = [t for t in targets or [] if t["target"].get("valid")]
        return "blocking-sendmessage" if valid else "blocking-sendmessage(宛先不明)"
    if top in MESSAGE_LOOP_CALLS:
        return "message-loop"
    if top.startswith("NtUserMsgWaitForMultipleObjectsEx"):
        return "msgwait"
    if top.startswith(("NtWait", "NtDelayExecution", "NtRemoveIoCompletion")):
        return "kernel-wait"
    return f"other:{top}"


# ---------------------------------------------------------------------------
# 外部見張りの結果の集計(1回ごとの全記録は残さない: 件数 + 失敗/拒否の内訳 + 間隔の統計)
# ---------------------------------------------------------------------------
class WakeLog:
    def __init__(
        self,
        period_ms,
        failure_limit=WAKE_FAILURE_LOG_MAX,
        long_gap_limit=WAKE_LONG_GAP_LOG_MAX,
    ):
        self.period_ms = period_ms
        self.failure_limit = failure_limit
        self.long_gap_limit = long_gap_limit
        self.ok = 0
        self.failed = 0  # PostThreadMessageW が失敗(戻り値0)
        self.refused = 0  # 宛先の確認に失敗して投稿しなかった
        self.skipped = (
            Counter()
        )  # UIスレッド未特定・対象消滅・上限など(投稿しない。失敗ではない)
        self.by_error = Counter()  # 失敗(winerror)と拒否(理由)の内訳
        self.by_phase = Counter()  # 成功した投稿の phase 別件数
        self.failures = []  # 失敗/拒否の先頭 failure_limit 件
        self.first_ok = None
        self.last_ok = None
        self.long_gaps = []  # 成功した投稿の間隔が周期の2倍を超えたもの
        self._last_mono_ms = None
        self._gap_n = 0
        self._gap_sum = 0.0
        self._gap_max = 0.0
        self._gap_over = 0
        self._lock = threading.Lock()

    def counts(self):
        with self._lock:
            return self.ok, self.failed + self.refused

    def success(self, t, tick_ms, phase, mono_ms):
        with self._lock:
            self.ok += 1
            self.by_phase[phase or ""] += 1
            item = {"t": t, "tick_ms": tick_ms, "phase": phase}
            if self.first_ok is None:
                self.first_ok = item
            self.last_ok = item
            if self._last_mono_ms is not None:
                gap = mono_ms - self._last_mono_ms
                self._gap_n += 1
                self._gap_sum += gap
                self._gap_max = max(self._gap_max, gap)
                if gap > 2 * self.period_ms:
                    self._gap_over += 1
                    if len(self.long_gaps) < self.long_gap_limit:
                        self.long_gaps.append(
                            {
                                "t": t,
                                "tick_ms": tick_ms,
                                "phase": phase,
                                "gap_ms": round(gap, 1),
                            }
                        )
            self._last_mono_ms = mono_ms

    def _fail(self, kind, key, t, tick_ms, phase, detail):
        self.by_error[key] += 1
        if len(self.failures) < self.failure_limit:
            self.failures.append(
                {
                    "kind": kind,
                    "t": t,
                    "tick_ms": tick_ms,
                    "phase": phase,
                    "error": key,
                    **detail,
                }
            )

    def failure(self, t, tick_ms, phase, error):
        with self._lock:
            self.failed += 1
            self._fail("post-failed", f"winerror={error}", t, tick_ms, phase, {})

    def refusal(self, t, tick_ms, phase, reason):
        with self._lock:
            self.refused += 1
            self._fail("refused", str(reason), t, tick_ms, phase, {})

    def skip(self, reason):
        with self._lock:
            self.skipped[reason] += 1

    def summary(self):
        with self._lock:
            return {
                "period_ms": self.period_ms,
                "posts_ok": self.ok,
                "posts_failed": self.failed,
                "refused": self.refused,
                "skipped": dict(self.skipped),
                "by_error": dict(self.by_error),
                "by_phase": dict(self.by_phase),
                "failures": list(self.failures),
                "first_ok": self.first_ok,
                "last_ok": self.last_ok,
                "interval_ms": {
                    "count": self._gap_n,
                    "mean": round(self._gap_sum / self._gap_n, 1)
                    if self._gap_n
                    else None,
                    "max": round(self._gap_max, 1) if self._gap_n else None,
                    "over_2x_period": self._gap_over,
                },
                "long_gaps": list(self.long_gaps),
            }


def wake_health(summary, period_ms):
    """見張りの結果が「期待どおりに動いた」と読めるかの目安(純関数)。除外ではなく、報告に印を付けるための判定。

    reasons が空 = healthy。投稿が少なすぎる・拒否や失敗が多い・投稿の間隔が開いた・見送りが多い、のどれかがあれば理由を列挙する。
    見張りが動いていない回の結果を『見張りありでも停止した』と読み違えないためのもの。
    """
    reasons = []
    ok = summary.get("posts_ok") or 0
    failed = summary.get("posts_failed") or 0
    if ok < WAKE_MIN_POSTS:
        reasons.append(f"posts_ok={ok}<{WAKE_MIN_POSTS}")
    if summary.get("refused"):
        reasons.append(f"refused={summary['refused']}")
    if failed > max(2, int(WAKE_MAX_FAIL_RATIO * ok)):
        reasons.append(f"posts_failed={failed}")
    longest = (summary.get("interval_ms") or {}).get("max")
    if longest is not None and period_ms and longest > WAKE_MAX_GAP_FACTOR * period_ms:
        reasons.append(
            f"post_interval_max={longest}ms>{WAKE_MAX_GAP_FACTOR}x{period_ms}ms"
        )
    skipped = sum((summary.get("skipped") or {}).values())
    if skipped > WAKE_MAX_SKIPPED:
        reasons.append(f"skipped={skipped}")
    return {"healthy": not reasons, "reasons": reasons}


# ---------------------------------------------------------------------------
# サンプラ
# ---------------------------------------------------------------------------
class UiThreadProbe:
    """一次PageFolioのUIスレッドを外から約100msごとに観測する(読み取り専用)。"""

    def __init__(
        self,
        native,
        pid,
        expected_created=None,
        interval=0.1,
        clock=time.monotonic,
        wall=wall_now,
        t0=None,
        phase_fn=None,
        wm_null=False,
        wm_null_interval=0.5,
        wm_null_timeout_ms=200,
        wm_null_phases=WM_NULL_PHASES,
        tail_path=None,
        ui_refresh_s=1.0,
        max_rows=40000,
        syscalls=True,
        syscall_names=None,
        target_depth=3,
        stall_snap_marks=(1.0, 5.0, 15.0),
        max_stall_snaps=8,
        external_wake_ms=None,
        wake_max_posts=WAKE_MAX_POSTS,
    ):
        self.native = native
        self.pid = pid
        self.expected_created = expected_created
        self.interval = interval
        self.clock = clock
        self.wall = wall
        self._t0 = t0
        self.phase_fn = phase_fn or (lambda: "")
        self.wm_null = wm_null
        self.wm_null_interval = wm_null_interval
        self.wm_null_timeout_ms = wm_null_timeout_ms
        self.wm_null_phases = tuple(wm_null_phases)
        self.tail = LogTail(tail_path) if tail_path else None
        self.ui_refresh_s = ui_refresh_s
        self.max_rows = max_rows
        self.syscalls = syscalls
        self._names = syscall_names
        self.syscall_info = (
            {"source": "injected", "entries": len(syscall_names)}
            if syscall_names is not None
            else None
        )
        self.target_depth = target_depth
        self.stall_snap_marks = tuple(stall_snap_marks)
        self.max_stall_snaps = max_stall_snaps
        self.stall_snapshots = []
        self._flat_ctx = None
        self._flat_since = None
        self._flat_done = set()
        self._sc_unavailable = {}
        self.rows = []
        self.wm_null_log = []
        self.log_events = []
        self.ui_log = []
        self.open_failures = []
        self.errors = []
        self.error_counts = Counter()
        self.anchors = []
        self.target = {
            "pid": pid,
            "expected_created": expected_created,
            "created": None,
            "identity_verified": None,
        }
        self.truncated = False
        self.gone_at = None
        self.gone_rows_dropped = 0
        self.max_gap_s = 0.0
        self._seq = 0
        self._last_c = None
        self._ui = None
        self._ui_checked = None
        self._gone = False
        self._invalid = False
        self._seen_log_keys = set()
        self.external_wake_ms = external_wake_ms
        self.wake_max_posts = wake_max_posts
        self.wake_log = WakeLog(external_wake_ms) if external_wake_ms else None
        self._stop = threading.Event()
        self._thread = None
        self._wm_thread = None
        self._wake_thread = None
        self._lock = threading.Lock()
        self.started_at = None
        self.stopped_at = None

    # -- 制御 -----------------------------------------------------------------
    def anchor(self):
        """tick(製品と同じ時計)と壁時計・単調時計を同時に読んだ組。3回読んで最小幅を採る。"""
        best = None
        for _ in range(3):
            c1 = self.clock()
            tick = self.native.tick_ms()
            wall = self.wall()
            c2 = self.clock()
            if best is None or (c2 - c1) < best[0]:
                best = (c2 - c1, {"tick_ms": tick, "t": wall, "mono": c1})
        return best[1]

    def _ensure_names(self):
        if self._names is None:
            names, info = load_syscall_names()
            self._names = names
            self.syscall_info = {"source": "ntdll.dll+win32u.dll", **info}
            if info.get("error"):
                self.errors.append(f"load_syscall_names:{info['error']}")
        return self._names

    def start(self):
        self.started_at = self.wall()
        if self.syscalls:
            self._ensure_names()
        try:
            self.anchors.append(self.anchor())
        except Exception as error:
            self._note_error("anchor", error)
        self._open_target()
        self.sample_once()
        self._thread = threading.Thread(
            target=self._run, name="uat-ui-thread-probe", daemon=True
        )
        self._thread.start()
        if self.wm_null:
            self._wm_thread = threading.Thread(
                target=self._run_wm_null, name="uat-wm-null-probe", daemon=True
            )
            self._wm_thread.start()
        if self.external_wake_ms:
            self._wake_thread = threading.Thread(
                target=self._run_wake, name="uat-external-wake", daemon=True
            )
            self._wake_thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        if self._wm_thread is not None:
            self._wm_thread.join(timeout=self.wm_null_timeout_ms / 1000 + 2)
        if self._wake_thread is not None:
            self._wake_thread.join(timeout=3)
        try:
            self.anchors.append(self.anchor())
        except Exception as error:
            self._note_error("anchor", error)
        if self.tail is not None:
            self._poll_tail()  # 最後にもう一度
        if self.stopped_at is None:
            self.stopped_at = self.wall()
        try:
            self.native.close()
        except Exception as error:
            self._note_error("close", error)

    def _open_target(self):
        try:
            info = self.native.open_target(self.pid)
            self.target["created"] = info.get("created")
            if self.expected_created is not None and info.get("created") is not None:
                verified = int(info["created"]) == int(self.expected_created)
                self.target["identity_verified"] = verified
                if not verified:
                    self._invalid = True
                    self.open_failures.append(
                        {
                            "api": "identity",
                            "error": "process creation time mismatch (pid reuse?)",
                            "t": self.wall(),
                        }
                    )
        except Exception as error:
            self.open_failures.append(
                {"api": "OpenProcess", "error": self._err_text(error), "t": self.wall()}
            )
            self._note_error("OpenProcess", error)

    def _run(self):
        nxt = self.clock()
        while not self._stop.is_set():
            self.sample_once()
            nxt += self.interval
            delay = nxt - self.clock()
            if delay < -self.interval * 5:  # 大きく遅れたら追いつこうとして連打しない
                nxt = self.clock()
                delay = 0.0
            self._stop.wait(max(0.0, delay))

    def _run_wm_null(self):
        while not self._stop.is_set():
            ui = self._ui
            phase = self.phase_fn()
            if (
                ui
                and ui.get("hwnd")
                and phase in self.wm_null_phases
                and not self._gone
            ):
                try:
                    result = self.native.wm_null(ui["hwnd"], self.wm_null_timeout_ms)
                    record = {
                        "t": self.wall(),
                        "tick_ms": self.native.tick_ms(),
                        "phase": phase,
                        "hwnd": ui["hwnd"],
                        **result,
                    }
                except Exception as error:
                    record = {
                        "t": self.wall(),
                        "phase": phase,
                        "hwnd": ui["hwnd"],
                        "result": "exception",
                        "error": self._err_text(error),
                    }
                    self._note_error("SendMessageTimeoutW", error)
                with self._lock:
                    if len(self.wm_null_log) < self.max_rows:
                        self.wm_null_log.append(record)
            self._stop.wait(self.wm_null_interval)

    # -- 外部見張り(--external-wake-ms) ---------------------------------------------
    def _run_wake(self):
        period = self.external_wake_ms / 1000.0
        nxt = time.perf_counter()
        while not self._stop.is_set():
            self.wake_once(time.perf_counter() * 1000.0)
            nxt += period
            delay = nxt - time.perf_counter()
            if delay < -period * 5:  # 大きく遅れたら追いつこうとして連打しない
                nxt = time.perf_counter()
                delay = 0.0
            self._stop.wait(max(0.0, delay))

    def wake_once(self, mono_ms=None):
        """外部見張りの1回分: 宛先の確認(verify_post_target) -> PostThreadMessageW(tid, WM_NULL)。

        確認できなければ投稿しない(拒否として理由を残す)。SendMessage 系は呼ばない。結果は wake_log に集計する。
        """
        log = self.wake_log
        if log is None:
            return
        mono = time.perf_counter() * 1000.0 if mono_ms is None else mono_ms
        t = self.wall()
        try:
            tick = self.native.tick_ms()
        except Exception as error:
            self._note_error("GetTickCount64", error)
            tick = None
        phase = self.phase_fn()
        if self._gone:
            log.skip("target-gone")
            return
        if self._invalid or self.target.get("identity_verified") is not True:
            log.refusal(t, tick, phase, "identity-unverified")
            return
        ui = self._ui
        if not ui or not ui.get("tid"):
            log.skip("ui-thread-unknown")
            return
        if log.ok + log.failed >= self.wake_max_posts:
            log.skip("post-limit")
            return
        tid, hwnd = ui["tid"], ui.get("hwnd")
        try:
            check = self.native.verify_post_target(tid, hwnd, self.expected_created)
        except Exception as error:
            self._note_error("verify_post_target", error)
            check = {"ok": False, "reason": f"verify-exception:{self._err_text(error)}"}
        if not check.get("ok"):
            if check.get("reason") in ("process-exited", "thread-exited"):
                log.skip("target-exited")  # 終了は安全上の拒否ではない(見送りに数える)
                return
            log.refusal(t, tick, phase, check.get("reason") or "verify-failed")
            return
        try:
            result = self.native.post_wm_null(tid)
        except Exception as error:
            self._note_error("PostThreadMessageW", error)
            log.failure(t, tick, phase, getattr(error, "winerror", None) or repr(error))
            return
        if result.get("ok"):
            log.success(t, tick, phase, mono)
        else:
            log.failure(t, tick, phase, result.get("error"))

    def wake_summary(self):
        if self.wake_log is None:
            return None
        summary = self.wake_log.summary()
        return {
            "enabled": True,
            "api": "PostThreadMessageW(ui_tid, WM_NULL, 0, 0) from the driver process (post only; no SendMessage; no foreground/input API)",
            "before_every_post": "verify_post_target: process creation time == expected_created, process alive, "
            "GetProcessIdOfThread(tid) == target pid, thread alive, window owner == (tid, pid)",
            "max_posts": self.wake_max_posts,
            "target": {
                "pid": self.pid,
                "ui_thread": dict(self._ui) if self._ui else None,
            },
            "health": wake_health(summary, self.external_wake_ms),
            **summary,
        }

    # -- エラーの扱い ------------------------------------------------------------
    @staticmethod
    def _err_text(error):
        code = getattr(error, "winerror", None)
        return f"winerror={code}" if code else repr(error)

    def _note_error(self, api, error):
        key = f"{api}:{self._err_text(error)}"
        self.error_counts[key] += 1
        if key not in self.errors and len(self.errors) < 30:
            self.errors.append(key)
        return key

    def _call(self, errs, api, fn, *args):
        try:
            return fn(*args)
        except Exception as error:
            self._note_error(api, error)
            errs.append(api)
            return None

    # -- 1回の観測 ---------------------------------------------------------------
    def sample_once(self):
        n = self.native
        c0 = self.clock()
        if self._t0 is None:
            self._t0 = c0
        if self._last_c is not None:
            self.max_gap_s = max(self.max_gap_s, c0 - self._last_c)
        self._last_c = c0
        errs = []
        row = dict.fromkeys(SAMPLE_COLUMNS)
        self._seq += 1
        row["seq"] = self._seq
        row["t"] = self.wall()
        row["elapsed_s"] = round(c0 - self._t0, 3)
        row["phase"] = self.phase_fn()
        row["tick_ms"] = self._call(errs, "GetTickCount64", n.tick_ms)
        if self.wake_log is not None:
            row["wake_ok"], row["wake_fail"] = self.wake_log.counts()
        if self._invalid:
            row["errors"] = ["identity-mismatch"]
            return self._store(row, c0)

        alive = self._call(errs, "GetExitCodeProcess", n.process_alive)
        snap = None
        before = len(errs)
        snap = self._call(errs, "NtQuerySystemInformation", n.system_snapshot, self.pid)
        snap_ok = len(errs) == before
        if alive is False or (snap_ok and snap is None and alive is not True):
            row["gone"] = True
            if not self._gone:
                self._gone = True
                self.gone_at = row["t"]
            row["errors"] = errs or None
            return self._store(row, c0)

        # UIスレッドの特定(1秒ごとに見直す。一度見つけたら窓が消えても直前の値を保つ)
        if self._ui is None or (c0 - self._ui_checked) >= self.ui_refresh_s:
            self._ui_checked = c0
            found = self._call(errs, "EnumWindows", n.find_ui_thread, self.pid)
            if found is None and snap and snap["threads"] and self._ui is None:
                oldest = min(
                    snap["threads"].items(), key=lambda kv: kv[1]["create_time"]
                )
                found = {
                    "tid": oldest[0],
                    "hwnd": 0,
                    "class": "",
                    "visible": False,
                    "source": "oldest-thread",
                }
            if found and (
                self._ui is None
                or found["tid"] != self._ui["tid"]
                or found["hwnd"] != self._ui["hwnd"]
            ):
                self.ui_log.append({"t": row["t"], "tick_ms": row["tick_ms"], **found})
            if found:
                self._ui = found
        ui = self._ui
        if ui:
            tid, hwnd = ui["tid"], ui["hwnd"]
            row["tid"], row["hwnd"] = tid, hwnd
            gui = self._call(errs, "GetGUIThreadInfo", n.gui_thread_info, tid)
            if gui:
                row["gui_flags"] = gui["flags"]
                row["hwnd_active"] = gui["active"]
                row["hwnd_focus"] = gui["focus"]
                row["hwnd_capture"] = gui["capture"]
                row["hwnd_menu_owner"] = gui["menu_owner"]
                row["hwnd_move_size"] = gui["move_size"]
            cpu = self._call(errs, "GetThreadTimes", n.thread_cpu, tid)
            thread = snap["threads"].get(tid) if snap else None
            if cpu:
                row["cpu_kernel_ms"] = round(cpu["kernel_100ns"] / 1e4, 1)
                row["cpu_user_ms"] = round(cpu["user_100ns"] / 1e4, 1)
                row["cycles_m"] = round(cpu["cycles"] / 1e6, 3)
            elif thread:  # 開けない場合はNTの値で代える
                row["cpu_kernel_ms"] = round(thread["kernel_100ns"] / 1e4, 1)
                row["cpu_user_ms"] = round(thread["user_100ns"] / 1e4, 1)
            if thread:
                row["state"] = thread["state"]
                row["wait_reason"] = thread["wait_reason"]
                row["ctx_switches"] = thread["ctx"]
                row["wait_time_ms"] = thread["wait_time"]
            if hwnd:
                row["hung"] = self._call(errs, "IsHungAppWindow", n.is_hung, hwnd)
            if self.syscalls:
                self._sample_syscall(errs, row, tid, snap)
                self._track_flat(c0, row, snap)
        if snap:
            ui_tid = ui["tid"] if ui else None
            row["others_ctx"] = [
                [tid2, t["ctx"], t["wait_reason"]]
                for tid2, t in sorted(snap["threads"].items())
                if tid2 != ui_tid
            ]
            others = [t for tid2, t in snap["threads"].items() if tid2 != ui_tid]
            row["others_cpu_ms"] = round(
                sum(t["kernel_100ns"] + t["user_100ns"] for t in others) / 1e4, 1
            )
            row["busy_threads"] = sum(
                1
                for t in others
                if t["state"] in ("Running", "Ready", "Standby", "DeferredReady")
            )
            proc = snap["process"]
            row["page_faults"] = proc["page_faults"]
            row["hard_faults"] = proc["hard_faults"]
            row["working_set_kb"] = proc["working_set"] // 1024
            row["threads"] = proc["threads"]
            row["io_read"], row["io_write"], row["io_other"] = (
                proc["read_ops"],
                proc["write_ops"],
                proc["other_ops"],
            )
        mem = self._call(errs, "K32GetProcessMemoryInfo", n.process_memory)
        if mem:
            row["pf_gmpi"] = mem["page_faults"]
            if row["working_set_kb"] is None:
                row["working_set_kb"] = mem["working_set"] // 1024
        if self.tail is not None:
            self._poll_tail(row)
        row["errors"] = errs or None
        row["cost_ms"] = round((self.clock() - c0) * 1000, 2)
        return self._store(row, c0)

    def _sample_syscall(self, errs, row, tid, snap):
        """UIスレッドの最後のシステムコール(名前・第1引数)と、第1引数が窓なら宛先への解決。"""
        n = self.native
        if tid in self._sc_unavailable:
            return
        try:
            sc = n.thread_syscall(tid)
        except Exception as error:
            # 開けない(権限など)。毎サンプル失敗を数えないよう、このスレッドは以後試さない。
            self._sc_unavailable[tid] = self._err_text(error)
            self._note_error("ThreadLastSystemCall", error)
            errs.append("ThreadLastSystemCall")
            return
        row["sc_status"] = sc["status"]
        if sc["status"] != 0:
            return  # 待機中でない(STATUS_UNSUCCESSFUL など)。エラーではない
        names = self._ensure_names()
        name = syscall_label(names, sc["number"])
        row["syscall"] = name
        row["sc_arg"] = sc["first_arg"]
        row["sc_wait_ms"] = round(sc["wait_100ns"] / 1e4, 1)
        try:
            row["wait_target"] = describe_wait_target(
                n,
                names,
                sc["first_arg"],
                name,
                self.pid,
                snap["threads"] if snap else None,
                snap["process"].get("image") if snap else None,
                row["tick_ms"],
                self.target_depth,
            )
        except Exception as error:
            self._note_error("describe_wait_target", error)
            errs.append("describe_wait_target")

    def _track_flat(self, c0, row, snap):
        """UIスレッドのctx切替が増えない時間を測り、1秒/5秒を超えたら全スレッドの最後のシステムコールを1回記録する。"""
        ctx = row.get("ctx_switches")
        if ctx is None:
            return
        if ctx != self._flat_ctx:
            self._flat_ctx = ctx
            self._flat_since = c0
            self._flat_done = set()
            return
        flat_s = c0 - self._flat_since
        for mark in self.stall_snap_marks:
            if (
                flat_s >= mark
                and mark not in self._flat_done
                and len(self.stall_snapshots) < self.max_stall_snaps
            ):
                self._flat_done.add(mark)
                self.stall_snapshots.append(
                    self._snapshot_threads(row, snap, flat_s, mark)
                )

    def _snapshot_threads(self, row, snap, flat_s, mark):
        names = self._ensure_names()
        threads = []
        for tid, thread in sorted((snap or {"threads": {}})["threads"].items())[:40]:
            item = {
                "tid": tid,
                "ui": tid == row.get("tid"),
                "state": thread["state"],
                "wait_reason": thread["wait_reason"],
                "ctx": thread["ctx"],
                "start_address": f"{thread['start_address']:#x}",
            }
            if thread["state"] == "Waiting" and tid not in self._sc_unavailable:
                try:
                    sc = self.native.thread_syscall(tid)
                    if sc["status"] == 0:
                        item["syscall"] = syscall_label(names, sc["number"])
                        item["arg"] = sc["first_arg"]
                        item["wait_ms"] = round(sc["wait_100ns"] / 1e4, 1)
                    else:
                        item["sc_status"] = sc["status"]
                except Exception as error:
                    self._sc_unavailable[tid] = self._err_text(error)
                    item["sc_error"] = self._err_text(error)
            threads.append(item)
        windows = None
        try:
            windows = self.native.process_windows(self.pid)
        except Exception as error:
            self._note_error("process_windows", error)
        return {
            "t": row["t"],
            "tick_ms": row["tick_ms"],
            "phase": row["phase"],
            "ui_ctx_flat_s": round(flat_s, 2),
            "mark_s": mark,
            "gui_flags": row.get("gui_flags"),
            "hwnd_active": row.get("hwnd_active"),
            "hwnd_focus": row.get("hwnd_focus"),
            "threads": threads,
            "windows": windows,
        }

    def _store(self, row, c0):
        if row.get("cost_ms") is None:
            row["cost_ms"] = round((self.clock() - c0) * 1000, 2)
        if row.get("gone") and self._gone:
            gone_rows = sum(1 for r in self.rows[-3:] if r.get("gone"))
            if gone_rows >= 3:
                self.gone_rows_dropped += 1
                return row
        if len(self.rows) >= self.max_rows:
            self.truncated = True
            return row
        self.rows.append(row)
        return row

    def _poll_tail(self, row=None):
        for line in self.tail.poll():
            for event in parse_log_events(line):
                key = json.dumps(event, sort_keys=True)
                if key in self._seen_log_keys:
                    continue
                self._seen_log_keys.add(key)
                self.log_events.append(
                    {
                        **event,
                        "seen_t": row["t"] if row else self.wall(),
                        "seen_tick_ms": row["tick_ms"]
                        if row
                        else self.native.tick_ms(),
                    }
                )

    # -- 結果 ------------------------------------------------------------------
    def table(self):
        """サイドカー用: 列名 + 行配列(読みやすさより容量を優先)。"""
        return {
            "columns": list(SAMPLE_COLUMNS),
            "rows": [[row.get(col) for col in SAMPLE_COLUMNS] for row in self.rows],
        }

    def summary(self, tick_window=None):
        costs = [r["cost_ms"] for r in self.rows if r.get("cost_ms") is not None]
        wm = summarize_wm_null(self.wm_null_log)
        return {
            "enabled": True,
            "purpose": PURPOSE,
            "acceptance": False,
            "method": "read-only external sampling: GetGUIThreadInfo / GetThreadTimes / "
            "QueryThreadCycleTime / NtQuerySystemInformation(SystemProcessInformation) / "
            "K32GetProcessMemoryInfo / IsHungAppWindow / EnumWindows+GetClassNameW / GetTickCount64 / "
            "NtQueryInformationThread(ThreadLastSystemCall) / IsWindow / InternalGetWindowText"
            " (OpenProcess=PROCESS_QUERY_LIMITED_INFORMATION, OpenThread=THREAD_QUERY_LIMITED_INFORMATION and "
            "THREAD_QUERY_INFORMATION|THREAD_GET_CONTEXT; "
            "no SendInput/SetForegroundWindow/SetCursorPos/keybd_event/mouse_event/SuspendThread/GetThreadContext/DebugActiveProcess"
            + (
                "; external_wake=ON: PostThreadMessageW(WM_NULL) only (post, not send)"
                if self.external_wake_ms
                else ""
            )
            + ")",
            "interval_s": self.interval,
            "options": {
                "wm_null_probe": self.wm_null,
                "wm_null_interval_s": self.wm_null_interval if self.wm_null else None,
                "wm_null_timeout_ms": self.wm_null_timeout_ms if self.wm_null else None,
                "wm_null_phases": list(self.wm_null_phases) if self.wm_null else None,
                "external_wake_ms": self.external_wake_ms,
            },
            "external_wake": self.wake_summary(),
            "getmessage": summarize_getmessage(self.rows),
            "target": dict(self.target),
            "open_failures": list(self.open_failures),
            "errors": list(self.errors),
            "error_counts": dict(self.error_counts),
            "ui_thread_log": list(self.ui_log),
            "anchors": list(self.anchors),
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "gone_at": self.gone_at,
            "gone_rows_dropped": self.gone_rows_dropped,
            "truncated": self.truncated,
            "samples": len(self.rows),
            "max_gap_s": round(self.max_gap_s, 3),
            "cost_ms": {
                "avg": round(sum(costs) / len(costs), 2) if costs else None,
                "max": max(costs) if costs else None,
            },
            "wm_null": wm,
            "log_events_seen_live": list(self.log_events),
            "phase_stats": phase_stats(self.rows, self.wm_null_log),
            "stall_episodes": find_stall_episodes(self.rows, self.wm_null_log),
            "syscall_probe": {
                "enabled": self.syscalls,
                "thread_access": f"THREAD_QUERY_INFORMATION|THREAD_GET_CONTEXT ({THREAD_SYSCALL_ACCESS:#x}) 読み取り専用。"
                "SuspendThread/GetThreadContext/DebugActiveProcess は使わない",
                "names": self.syscall_info,
                "unavailable_threads": dict(self._sc_unavailable),
                "stall_snapshots": list(self.stall_snapshots),
                "wait_targets_seen": collect_wait_targets(self.rows),
                "syscall_counts": dict(
                    Counter(
                        r["syscall"] for r in self.rows if r.get("syscall")
                    ).most_common(12)
                ),
            },
        }


# ---------------------------------------------------------------------------
# 解析(純関数。サンプル行 = SAMPLE_COLUMNS の dict)
# ---------------------------------------------------------------------------
def _cpu_ms(row):
    k, u = row.get("cpu_kernel_ms"), row.get("cpu_user_ms")
    if k is None or u is None:
        return None
    return k + u


def _delta(first, last, key):
    a, b = first.get(key), last.get(key)
    if a is None or b is None:
        return None
    return b - a


def _is_modal(row):
    flags = row.get("gui_flags")
    if flags is not None and flags & MODAL_FLAGS:
        return True
    return bool(row.get("hwnd_menu_owner") or row.get("hwnd_move_size"))


def summarize_wm_null(log, tick_from=None, tick_to=None):
    items = [
        r
        for r in log
        if (tick_from is None or (r.get("tick_ms") or 0) >= tick_from)
        and (tick_to is None or (r.get("tick_ms") or 0) <= tick_to)
    ]
    counts = Counter(r.get("result") for r in items)
    times = [r["elapsed_ms"] for r in items if r.get("elapsed_ms") is not None]
    return {
        "count": len(items),
        "by_result": dict(counts),
        "max_elapsed_ms": max(times) if times else None,
    }


def getmessage_runs(rows):
    """UIスレッドの最後のシステムコールが NtUserGetMessage の連続したサンプル = タイムアウトの無い GetMessage で待っていた区間。

    健全なTclの待機は NtUserMsgWaitForMultipleObjectsEx(タイムアウト付き)で、ここには現れない。
    length_ms は区間の長さ: 区間の最初〜最後のサンプルの tick 差と、観測できた現在の待機の長さ(sc_wait_ms の最大)の大きいほう。
    syscall 列が無い古い診断の行は、そもそも判定できない(runs=0 と区別するため呼び出し側が syscall の有無を見る)。
    """
    runs = []
    current = []

    def to_run(items):
        waits = [r["sc_wait_ms"] for r in items if r.get("sc_wait_ms") is not None]
        first, last = items[0], items[-1]
        span = (last.get("tick_ms") or 0) - (first.get("tick_ms") or 0)
        max_wait = max(waits) if waits else None
        run = {
            "start_t": first.get("t"),
            "start_tick_ms": first.get("tick_ms"),
            "end_tick_ms": last.get("tick_ms"),
            "rows": len(items),
            "span_ms": span,
            "max_wait_ms": max_wait,
            "length_ms": round(max(span, max_wait or 0), 1),
            "phases": sorted({r.get("phase") or "" for r in items}),
        }
        posts = [r.get("wake_ok") for r in items if r.get("wake_ok") is not None]
        if len(posts) >= 2:
            run["wake_posts_during"] = posts[-1] - posts[0]
        return run

    for row in rows:
        if not row.get("gone") and row.get("syscall") == GETMESSAGE_CALL:
            current.append(row)
        elif current:
            runs.append(to_run(current))
            current = []
    if current:
        runs.append(to_run(current))
    return runs


def summarize_getmessage(rows, stall_ms=GETMESSAGE_STALL_MS):
    """getmessage_runs の要約。stalls = 長さが stall_ms 以上の区間の数(見張り周期の約3倍以上)。"""
    runs = getmessage_runs(rows)
    lengths = [r["length_ms"] for r in runs]
    stall_runs = [r for r in runs if r["length_ms"] >= stall_ms]
    return {
        "syscall_columns": any(r.get("syscall") for r in rows),
        "runs": len(runs),
        "rows": sum(r["rows"] for r in runs),
        "max_length_ms": max(lengths) if lengths else 0,
        "max_rows": max((r["rows"] for r in runs), default=0),
        "stall_threshold_ms": stall_ms,
        "stalls": len(stall_runs),
        # 停止の最中にも見張りの投稿が流れていた(区間内に2回以上投稿が成功した)件数 = 投稿しても解消しなかった停止。
        # 見張りなしの回は投稿の累計が無いので常に0。
        "stalls_while_posting": sum(
            1 for r in stall_runs if (r.get("wake_posts_during") or 0) >= 2
        ),
        "longest": sorted(runs, key=lambda r: -r["length_ms"])[:5],
    }


def aggregate_rows(rows, wm_log=None):
    """連続する行の集計(区間のctx切替率・CPU割合・状態の分布など)。"""
    rows = [r for r in rows if not r.get("gone")]
    if not rows:
        return {"rows": 0}
    first, last = rows[0], rows[-1]
    duration = max(0.0, (last.get("elapsed_s") or 0) - (first.get("elapsed_s") or 0))
    d_ctx = _delta(first, last, "ctx_switches")
    cpu_first, cpu_last = _cpu_ms(first), _cpu_ms(last)
    d_cpu = None if cpu_first is None or cpu_last is None else cpu_last - cpu_first
    d_cycles = _delta(first, last, "cycles_m")
    d_others = _delta(first, last, "others_cpu_ms")
    busy = [r["busy_threads"] for r in rows if r.get("busy_threads") is not None]
    flag_counts = Counter()
    for r in rows:
        for name in decode_gui_flags(r.get("gui_flags")) or ["none"]:
            flag_counts[name] += 1
    states = Counter(r.get("state") for r in rows if r.get("state"))
    waits = Counter(r.get("wait_reason") for r in rows if r.get("wait_reason"))
    ws = [r["working_set_kb"] for r in rows if r.get("working_set_kb") is not None]
    modal_rows = sum(1 for r in rows if _is_modal(r))
    out = {
        "rows": len(rows),
        "first": {"t": first.get("t"), "tick_ms": first.get("tick_ms")},
        "last": {"t": last.get("t"), "tick_ms": last.get("tick_ms")},
        "duration_s": round(duration, 3),
        "ctx_switch_delta": d_ctx,
        "ctx_per_s": round(d_ctx / duration, 2)
        if d_ctx is not None and duration
        else None,
        "cpu_ms_delta": None if d_cpu is None else round(d_cpu, 1),
        "cpu_share": round(d_cpu / 1000 / duration, 3)
        if d_cpu is not None and duration
        else None,
        "cycles_m_delta": None if d_cycles is None else round(d_cycles, 3),
        "others_cpu_ms_delta": None if d_others is None else round(d_others, 1),
        "others_cpu_share": round(d_others / 1000 / duration, 3)
        if d_others is not None and duration
        else None,
        "busy_other_threads_max": max(busy) if busy else None,
        "page_fault_delta": _delta(first, last, "page_faults"),
        "hard_fault_delta": _delta(first, last, "hard_faults"),
        "working_set_kb": {"min": min(ws), "max": max(ws)} if ws else None,
        "states": dict(states),
        "wait_reasons": dict(waits),
        "gui_flags_rows": dict(flag_counts),
        "modal_rows": modal_rows,
        "hung_rows": sum(1 for r in rows if r.get("hung")),
        "tids": sorted({r["tid"] for r in rows if r.get("tid")}),
        "max_cost_ms": max(
            (r["cost_ms"] for r in rows if r.get("cost_ms") is not None), default=None
        ),
    }
    syscalls = Counter(r.get("syscall") for r in rows if r.get("syscall"))
    if syscalls:
        out["syscalls"] = dict(syscalls.most_common(8))
        targets = collect_wait_targets(rows)
        if targets:
            out["wait_targets"] = targets
        out["wait_kind"] = wait_kind(out["syscalls"], targets)
    ctx_delta = others_ctx_delta(rows)
    if ctx_delta:
        out["others_ctx_delta"] = ctx_delta
    if wm_log is not None:
        out["wm_null"] = summarize_wm_null(
            wm_log, first.get("tick_ms"), last.get("tick_ms")
        )
    return out


def classify_aggregate(agg, request_late=False):
    """判別の材料(A〜D)をタグで返す。根因の断定ではない。各タグに根拠の数値を付ける。"""
    tags = []
    if not agg or agg.get("rows", 0) < 2 or not agg.get("duration_s"):
        return tags
    ctx = agg.get("ctx_per_s")
    cpu = agg.get("cpu_share")
    wm = agg.get("wm_null") or {}
    by_result = wm.get("by_result") or {}
    wm_total = wm.get("count") or 0
    wm_ok = by_result.get("ok", 0)
    modal_ratio = agg["modal_rows"] / agg["rows"]
    if modal_ratio >= MODAL_ROW_RATIO:
        tags.append(
            {
                "tag": "D:modal-loop",
                "evidence": f"gui_flagsのモーダル(menu/system-menu/popup/move-size)が{agg['modal_rows']}/{agg['rows']}行 "
                f"flags={agg['gui_flags_rows']}",
            }
        )
    if cpu is not None and cpu >= CPU_SHARE_BUSY:
        tags.append(
            {
                "tag": "C:cpu-consumed",
                "evidence": f"スレッドCPU時間が区間の{cpu * 100:.0f}% "
                f"(cpu_ms_delta={agg['cpu_ms_delta']} cycles_m_delta={agg['cycles_m_delta']})",
            }
        )
    others_share = agg.get("others_cpu_share")
    if (
        ctx is not None
        and ctx < CTX_PER_S_FLAT
        and others_share is not None
        and others_share >= CPU_SHARE_BUSY
    ):
        tags.append(
            {
                "tag": "C:other-thread-cpu",
                "evidence": f"UIスレッドは起床していない(ctx {ctx}/s)のに、他スレッドのCPU時間が区間の"
                f"{others_share * 100:.0f}% (others_cpu_ms_delta={agg['others_cpu_ms_delta']} "
                f"busy_other_threads_max={agg['busy_other_threads_max']}) = 別スレッドが走っている間UIが待っている",
            }
        )
    if (
        ctx is not None
        and ctx < CTX_PER_S_FLAT
        and (cpu is None or cpu < CPU_SHARE_BUSY)
    ):
        detail = (
            f"ctx切替 {ctx}/s(ほぼ起床せず) states={agg['states']} wait_reasons={agg['wait_reasons']}"
            f" hung_rows={agg['hung_rows']}/{agg['rows']}"
        )
        if wm_total:
            detail += f" WM_NULL ok={wm_ok}/{wm_total}"
        tags.append({"tag": "A:native-wait", "evidence": detail})
        if agg.get("wait_kind"):
            texts = [t["text"] for t in agg.get("wait_targets") or []]
            tags.append(
                {
                    "tag": f"A:{agg['wait_kind']}",
                    "evidence": f"最後のシステムコール {agg.get('syscalls')}"
                    + (f" / 待ち先 {texts[0]}" if texts else ""),
                }
            )
    if (
        request_late
        and ctx is not None
        and ctx >= CTX_PER_S_ALIVE
        and (cpu is None or cpu < CPU_SHARE_BUSY)
        and modal_ratio < MODAL_ROW_RATIO
        and (not wm_total or wm_ok / wm_total >= 0.8)
    ):
        tags.append(
            {
                "tag": "B:pumping-but-timer-silent",
                "evidence": f"要求が遅れたが、ctx切替 {ctx}/s・CPU{(cpu or 0) * 100:.0f}%・"
                f"hung_rows={agg['hung_rows']}・WM_NULL ok={wm_ok}/{wm_total}(メッセージは捌いている)",
            }
        )
    return tags


def phase_stats(rows, wm_log=None):
    by_phase = {}
    order = []
    for row in rows:
        phase = row.get("phase") or ""
        if phase not in by_phase:
            by_phase[phase] = []
            order.append(phase)
        by_phase[phase].append(row)
    return {phase: aggregate_rows(by_phase[phase], wm_log) for phase in order}


def episode_wait_summary(agg):
    """無スケジュール区間の「何を待っていたか」を短くまとめる(システムコール列が無ければ None)。"""
    if not agg or not agg.get("syscalls"):
        return None
    targets = agg.get("wait_targets") or []
    return {
        "kind": agg.get("wait_kind"),
        "syscalls": agg["syscalls"],
        "targets": [
            {"rows": t["rows"], "syscall": t["syscall"], "text": t["text"]}
            for t in targets
        ],
        "others_ctx_delta": agg.get("others_ctx_delta"),
    }


def find_stall_episodes(rows, wm_log=None, min_s=STALL_MIN_S):
    """UIスレッドのctx切替が連続して増えない区間(=起床していない区間)を取り出す。"""
    episodes = []
    run = []
    prev = None

    def flush():
        if len(run) >= 2:
            span = (run[-1].get("elapsed_s") or 0) - (run[0].get("elapsed_s") or 0)
            if span >= min_s:
                agg = aggregate_rows(run, wm_log)
                episodes.append(
                    {
                        "start_t": run[0].get("t"),
                        "end_t": run[-1].get("t"),
                        "start_tick_ms": run[0].get("tick_ms"),
                        "end_tick_ms": run[-1].get("tick_ms"),
                        "start_elapsed_s": run[0].get("elapsed_s"),
                        "end_elapsed_s": run[-1].get("elapsed_s"),
                        "phases": sorted({r.get("phase") or "" for r in run}),
                        "aggregate": agg,
                        "tags": classify_aggregate(agg),
                        "wait": episode_wait_summary(agg),
                    }
                )

    for row in rows:
        flat = (
            prev is not None
            and not row.get("gone")
            and row.get("ctx_switches") is not None
            and prev.get("ctx_switches") is not None
            and row["ctx_switches"] == prev["ctx_switches"]
        )
        if flat:
            if not run:
                run.append(prev)
            run.append(row)
        else:
            flush()
            run = []
        prev = row
    flush()
    return episodes


# ---------------------------------------------------------------------------
# 要求の「受理→処理」タイムライン(stderrの tick を壁時計へ換算する)
# ---------------------------------------------------------------------------
def tick_to_iso(tick, anchor):
    base = datetime.fromisoformat(anchor["t"])
    return (base + timedelta(milliseconds=tick - anchor["tick_ms"])).isoformat()


def build_request_timeline(
    primary_text, peer_text, anchors, live_events=None, peer_result=None
):
    """一次/二次のstderrから、要求の受理・締切・一次の処理を tick と壁時計で並べる。

    - 二次の「accepted: <id> / deadline=<tick>」: 一次が受理した要求の締切tick。
      startup_win32.request_activation は deadline = started_tick + 5000 なので、開始tickは導出(派生値)。
    - 一次の「terminal: <id> / <result> / deadline=<tick> / tick=<tick>」: 一次のTkスレッドが要求を
      最終処理(完了/期限切れ等)したtick。tick - deadline が締切からの遅れ。
    - tick→壁時計は、driverが同時に読んだ(GetTickCount64, 壁時計)の組(開始/終了)で換算する。
    """
    primary = parse_log_events(primary_text or "")
    peer = parse_log_events(peer_text or "")
    anchor0 = anchors[0] if anchors else None
    anchor1 = anchors[-1] if len(anchors) > 1 else None

    def wall(tick):
        if anchor0 is None or tick is None:
            return None
        return tick_to_iso(tick, anchor0)

    drift_ms = None
    if anchor0 and anchor1 and anchor1 is not anchor0:
        t0 = datetime.fromisoformat(anchor0["t"])
        t1 = datetime.fromisoformat(anchor1["t"])
        wall_dt = (t1 - t0).total_seconds() * 1000
        tick_dt = anchor1["tick_ms"] - anchor0["tick_ms"]
        drift_ms = round(wall_dt - tick_dt, 1)
    live_terminal = {
        (e["id"], e["tick_ms"]): e
        for e in (live_events or [])
        if e["kind"] == "terminal"
    }
    requests = {}
    for event in peer:
        if event["kind"] == "accepted":
            item = requests.setdefault(event["id"], {"id": event["id"]})
            item["peer_accepted_deadline_tick"] = event["deadline_tick"]
    for event in primary:
        if event["kind"] == "terminal":
            item = requests.setdefault(event["id"], {"id": event["id"]})
            item["primary_terminal_result"] = event["result"]
            item["primary_terminal_tick"] = event["tick_ms"]
            item["deadline_tick"] = event["deadline_tick"]
    out = []
    for item in requests.values():
        deadline = item.get("deadline_tick", item.get("peer_accepted_deadline_tick"))
        started = None if deadline is None else deadline - 5000
        terminal = item.get("primary_terminal_tick")
        record = {
            "request_id": item["id"],
            "deadline_tick": deadline,
            "request_started_tick_derived": started,
            "request_started_derivation": "deadline_tick - 5000 (startup_win32.request_activation)",
            "accepted_tick_note": "一次が要求を受理(accepted返信)したtickはstderrに出ない。"
            "通常行ではpeer elapsedが63〜94msなので、開始tickから約0.1秒以内と推定される(推定)",
            "peer_accepted_logged": "peer_accepted_deadline_tick" in item,
            "primary_terminal_result": item.get("primary_terminal_result"),
            "primary_terminal_tick": terminal,
            "primary_lateness_ms": None
            if terminal is None or deadline is None
            else terminal - deadline,
            "primary_processed_before_deadline": None
            if terminal is None or deadline is None
            else terminal <= deadline,
            "wall": {
                "request_started": wall(started),
                "deadline": wall(deadline),
                "primary_terminal": wall(terminal),
            },
        }
        seen = live_terminal.get((item["id"], terminal))
        if seen:
            record["terminal_first_seen_by_driver"] = {
                "t": seen["seen_t"],
                "tick_ms": seen["seen_tick_ms"],
                "lag_ms_after_logged_tick": None
                if terminal is None
                else seen["seen_tick_ms"] - terminal,
            }
        out.append(record)
    os_errors = [e["os_error"] for e in peer if e["kind"] == "os_error"]
    return {
        "requests": out,
        "peer_os_errors": os_errors,
        "peer_result": peer_result,
        "anchors": list(anchors),
        "tick_wall_drift_ms_between_anchors": drift_ms,
        "late": any(r["primary_processed_before_deadline"] is False for r in out),
    }


def analyze_request_window(rows, wm_log, timeline):
    """遅れた要求(受理〜一次の処理)の区間で、UIスレッドの状態を集計してタグ付けする。"""
    out = []
    for request in (timeline or {}).get("requests", []):
        started = request.get("request_started_tick_derived")
        terminal = request.get("primary_terminal_tick")
        deadline = request.get("deadline_tick")
        if started is None or terminal is None:
            continue
        window = [
            r
            for r in rows
            if r.get("tick_ms") is not None and started <= r["tick_ms"] <= terminal
        ]
        agg = aggregate_rows(window, wm_log)
        late = bool(
            request.get("primary_lateness_ms") and request["primary_lateness_ms"] > 0
        )
        out.append(
            {
                "request_id": request["request_id"],
                "window_tick_ms": [started, terminal],
                "late": late,
                "aggregate": agg,
                "tags": classify_aggregate(agg, request_late=late),
                "rows_at": {
                    "request_started": nearest_row(rows, started),
                    "deadline": nearest_row(rows, deadline),
                    "primary_terminal": nearest_row(rows, terminal),
                },
            }
        )
    return out


def nearest_row(rows, tick):
    best = None
    for row in rows:
        t = row.get("tick_ms")
        if t is None or tick is None:
            continue
        if best is None or abs(t - tick) < abs(best["tick_ms"] - tick):
            best = row
    if best is None:
        return None
    keep = (
        "t",
        "tick_ms",
        "phase",
        "gui_flags",
        "state",
        "wait_reason",
        "ctx_switches",
        "cpu_kernel_ms",
        "cpu_user_ms",
        "others_cpu_ms",
        "hung",
    )
    out = {k: best.get(k) for k in keep}
    out["offset_ms"] = best["tick_ms"] - tick  # 目的のtickからの距離(符号付き)
    return out


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_samples_sidecar(path, probe):
    """サンプルをJSON Linesで保存する(1行目=列定義と対象、以降=行配列、最後=wm_null/ログ)。"""
    table = probe.table()
    lines = [
        json.dumps(
            {
                "kind": "header",
                "purpose": PURPOSE,
                "acceptance": False,
                "columns": table["columns"],
                "target": probe.target,
                "anchors": probe.anchors,
            },
            ensure_ascii=False,
        )
    ]
    lines += [json.dumps(row, ensure_ascii=False) for row in table["rows"]]
    lines += [
        json.dumps({"kind": "wm_null", **item}, ensure_ascii=False)
        for item in probe.wm_null_log
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {
        "file": Path(path).name,
        "rows": len(table["rows"]),
        "wm_null_rows": len(probe.wm_null_log),
        "sha256": file_sha256(path),
        "format": "JSON Lines: 1行目=header(columns)、続く行=サンプル配列(columns順)、"
        "kind=wm_null の行=WM_NULL応答",
    }


def load_samples(path):
    """write_samples_sidecar の逆。-> (header, rows(dict), wm_null_rows)。"""
    header = None
    rows = []
    wm = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict) and value.get("kind") == "header":
            header = value
        elif isinstance(value, dict) and value.get("kind") == "wm_null":
            wm.append(value)
        elif isinstance(value, list) and header:
            rows.append(dict(zip(header["columns"], value, strict=False)))
    return header, rows, wm


# ---------------------------------------------------------------------------
# 頻度の集計(--summarize-diag)
# ---------------------------------------------------------------------------
def summarize_sessions(directory):
    """診断ディレクトリのセッションJSONから、再走ごとの結果と頻度表を作る(読み取りのみ)。"""
    directory = Path(directory)
    rows = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            rows.append({"file": path.name, "error": repr(error)})
            continue
        diag = data.get("ui_thread_diag") or {}
        peer = ((data.get("harness_peer") or {}).get("json") or {}).get("result") or {}
        focus = ((data.get("harness_inspect") or {}).get("json") or {}).get(
            "focus-result.json"
        ) or {}
        episodes = diag.get("stall_episodes") or []
        induce_request = ((data.get("diagnostics") or {}).get("induce")) or {}
        induce_result = data.get("induce_assessment") or {}
        diagnostics = data.get("diagnostics") or {}
        # GetMessage 区間はサイドカー(全サンプル)から数える。古い診断にも同じ基準で当てられる。
        getmessage = None
        sidecar_name = (diag.get("samples_file") or {}).get("file")
        if sidecar_name and (directory / sidecar_name).is_file():
            try:
                _header, sample_rows, _wm = load_samples(directory / sidecar_name)
                getmessage = summarize_getmessage(sample_rows)
            except Exception as error:
                getmessage = {"error": repr(error)}
        elif diag.get("getmessage"):
            getmessage = diag["getmessage"]
        wake = diag.get("external_wake") or {}
        rows.append(
            {
                "file": path.name,
                "external_wake_ms": diagnostics.get("external_wake"),
                "syscall_probe": bool(diagnostics.get("syscall_probe")),
                "getmessage": getmessage,
                "wake": {
                    "posts_ok": wake.get("posts_ok"),
                    "posts_failed": wake.get("posts_failed"),
                    "refused": wake.get("refused"),
                    "skipped": wake.get("skipped"),
                    "by_error": wake.get("by_error"),
                    "healthy": (wake.get("health") or {}).get("healthy"),
                    "unhealthy_reasons": (wake.get("health") or {}).get("reasons"),
                    "max_interval_ms": (wake.get("interval_ms") or {}).get("max"),
                    "over_2x_period": (wake.get("interval_ms") or {}).get(
                        "over_2x_period"
                    ),
                }
                if wake
                else None,
                "row": data.get("row"),
                "run": f"{(data.get('diagnostics') or {}).get('run_index')}/{(data.get('diagnostics') or {}).get('run_total')}",
                "started_at": data.get("started_at"),
                "outcome": data.get("outcome"),
                "procedure_verdict": data.get("procedure_verdict"),
                "wm_null_probe": (diag.get("options") or {}).get("wm_null_probe"),
                "peer_result": peer.get("result"),
                "peer_elapsed_ms": peer.get("elapsed"),
                "focus_correct": focus.get("focus_correct"),
                "samples": diag.get("samples"),
                "stall_episodes": len(episodes),
                "longest_stall_s": max(
                    (e["aggregate"].get("duration_s") or 0 for e in episodes), default=0
                ),
                "late_request": bool((diag.get("request_timeline") or {}).get("late")),
                "diag_error": data.get("ui_thread_diag_error"),
                "induce_requested": bool(induce_request.get("requested")),
                "induced": induce_result.get("induced"),
                "induce_reasons": induce_result.get("reasons"),
                "induce_switcher_s": induce_result.get("switcher_visible_s"),
                "induce_quiet_s": induce_result.get("quiet_s"),
                "stalls": [
                    {
                        "start_t": e.get("start_t"),
                        "duration_s": (e.get("aggregate") or {}).get("duration_s"),
                        "phases": e.get("phases"),
                        "wait": e.get("wait"),
                        "tags": [t["tag"] for t in e.get("tags") or []],
                    }
                    for e in episodes
                ],
                "syscall_counts": (diag.get("syscall_probe") or {}).get(
                    "syscall_counts"
                ),
                "wait_targets_seen": [
                    {
                        "rows": t.get("rows"),
                        "syscall": t.get("syscall"),
                        "text": t.get("text"),
                    }
                    for t in (diag.get("syscall_probe") or {}).get("wait_targets_seen")
                    or []
                ],
            }
        )
    valid = [r for r in rows if "error" not in r and r.get("outcome") is not None]
    clean = [r for r in valid if r.get("procedure_verdict") == "clean"]
    failed = [
        r
        for r in clean
        if r.get("peer_result") not in (None, "completed") or r.get("late_request")
    ]
    induced = [r for r in clean if r.get("induced") is True]
    induced_failed = [r for r in induced if r in failed]
    wake_on = [r for r in valid if r.get("external_wake_ms")]
    wake_off = [r for r in valid if not r.get("external_wake_ms")]
    return {
        "directory": str(directory),
        "sessions": rows,
        "total": len(valid),
        "clean_procedure": len(clean),
        "peer_not_completed_or_late_among_clean": len(failed),
        "induce_requested": sum(1 for r in valid if r.get("induce_requested")),
        "induced_clean": len(induced),
        "peer_not_completed_or_late_among_induced": len(induced_failed),
        "groups": {
            "external_wake_off": {
                "all": group_stats(wake_off, failed),
                "induced_clean": group_stats(
                    [r for r in wake_off if r in induced], failed
                ),
            },
            "external_wake_on": {
                "period_ms": sorted({r["external_wake_ms"] for r in wake_on}),
                "all": group_stats(wake_on, failed),
                "induced_clean": group_stats(
                    [r for r in wake_on if r in induced], failed
                ),
            },
        },
        "note": "発生頻度の確認用(受入証拠ではない)。procedure_verdict=clean の回だけを母数にする。"
        "誘発手順(--induce-switcher)の回は、手順が成立(induced=true)した回だけを誘発の母数にする。"
        "groups は外部見張り(--external-wake-ms)の有無で分けた集計。GetMessage の区間は syscall 列のあるセッションだけで数える。",
    }


def group_stats(items, failed=()):
    """外部見張りの有無で分けたセッション群の集計(件数と最大値だけ)。"""
    gm_items = [
        r
        for r in items
        if (r.get("getmessage") or {}).get("syscall_columns")
        and "error" not in (r.get("getmessage") or {})
    ]
    wake_items = [r for r in items if r.get("wake")]

    def total(key, source=items):
        return sum((r.get(key) or 0) for r in source)

    out = {
        "sessions": len(items),
        "peer_not_completed_or_late": sum(1 for r in items if r in failed),
        "ctx_stall_episodes": total("stall_episodes"),
        "sessions_with_ctx_stall": sum(1 for r in items if r.get("stall_episodes")),
        "longest_ctx_stall_s": max(
            (r.get("longest_stall_s") or 0 for r in items), default=0
        ),
        "getmessage_sessions": len(gm_items),
        "getmessage_runs": sum(r["getmessage"]["runs"] for r in gm_items),
        "getmessage_stalls": sum(r["getmessage"]["stalls"] for r in gm_items),
        "sessions_with_getmessage_seen": sum(
            1 for r in gm_items if r["getmessage"]["runs"]
        ),
        "sessions_with_getmessage_stall": sum(
            1 for r in gm_items if r["getmessage"]["stalls"]
        ),
        "getmessage_stalls_while_posting": sum(
            r["getmessage"].get("stalls_while_posting", 0) for r in gm_items
        ),
        "max_getmessage_ms": max(
            (r["getmessage"]["max_length_ms"] for r in gm_items), default=0
        ),
        "max_getmessage_rows": max(
            (r["getmessage"]["max_rows"] for r in gm_items), default=0
        ),
        "getmessage_stall_threshold_ms": GETMESSAGE_STALL_MS,
    }
    if wake_items:
        intervals = [
            r["wake"]["max_interval_ms"]
            for r in wake_items
            if r["wake"].get("max_interval_ms") is not None
        ]
        out["wake"] = {
            "sessions": len(wake_items),
            "posts_ok": total("posts_ok", [r["wake"] for r in wake_items]),
            "posts_failed": total("posts_failed", [r["wake"] for r in wake_items]),
            "refused": total("refused", [r["wake"] for r in wake_items]),
            "max_post_interval_ms": max(intervals) if intervals else None,
            "sessions_with_long_post_gap": sum(
                1 for r in wake_items if r["wake"].get("over_2x_period")
            ),
            # 見張りが期待どおりに動いたと読めない回(投稿が少ない・拒否/失敗が多い・間隔が開いた)。除外はせず数えて示す。
            "unhealthy_sessions": [
                r["file"] for r in wake_items if r["wake"].get("healthy") is False
            ],
        }
    return out


# ---------------------------------------------------------------------------
# 機構確認(窓も入力も作らない / 前景も変えない)
# ---------------------------------------------------------------------------
FORBIDDEN_NAMES = (
    "SendInput",
    "SetForegroundWindow",
    "SetCursorPos",
    "keybd_event",
    "mouse_event",
    "SuspendThread",
    "ResumeThread",
    "DebugActiveProcess",
    "GetThreadContext",
    "SetThreadContext",
    "Wow64GetThreadContext",
    "Wow64SuspendThread",
    "NtGetContextThread",
    "NtSetContextThread",
    "NtSuspendThread",
    "NtResumeThread",
    "NtDebugActiveProcess",
    "GetWindowTextW",
    "GetWindowTextA",
    "SetWindowPos",
    "ShowWindow",
    "PostMessageW",
    "PostMessageA",
    "PostThreadMessageA",
    "SendMessageW",
    "SendMessageA",
    "SendMessageTimeoutA",
    "SendNotifyMessageW",
    "SendNotifyMessageA",
    "SendMessageCallbackW",
    "SendMessageCallbackA",
    "AttachThreadInput",
    "SwitchToThisWindow",
    "LockSetForegroundWindow",
    "AllowSetForegroundWindow",
    "EnableWindow",
    "SetWindowsHookExW",
    "SetFocus",
    "SetActiveWindow",
    "BringWindowToTop",
    "TerminateProcess",
    "TerminateThread",
    "WriteProcessMemory",
    "ReadProcessMemory",
    "CreateRemoteThread",
)


def used_native_names(source):
    """ソースのコード部分(文字列・コメントを除く)で参照されている属性名/名前の集合。"""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


# 外部見張りの経路(宛先の確認 -> 投稿)に属する関数。ここで使ってよい Win32 API(ctypes の属性名)はこれだけ。
WAKE_PATH_FUNCTIONS = (
    "Win32Native.verify_post_target",
    "Win32Native.post_wm_null",
    "UiThreadProbe.wake_once",
    "UiThreadProbe._run_wake",
)
WAKE_ALLOWED_APIS = frozenset(
    {
        "PostThreadMessageW",  # 投稿(送信ではない)。メッセージは WM_NULL(=0)だけ
        "GetProcessTimes",  # 作成時刻の確認(読み取り)
        "GetExitCodeProcess",
        "GetProcessIdOfThread",
        "GetExitCodeThread",
        "GetWindowThreadProcessId",
        "IsWindow",
    }
)
# PostThreadMessageW を呼んでよい関数: 見張りの投稿(post_wm_null)と、機構確認で幽霊を作る _live_ghost だけ。
POST_THREAD_MESSAGE_CALLERS = frozenset({"Win32Native.post_wm_null", "_live_ghost"})
_API_LIKE = re.compile(r"[A-Z][A-Za-z0-9]*")


def function_nodes(source):
    """モジュール直下の関数と、クラスのメソッドを「クラス名.メソッド名」で引ける辞書にする(静的検査用)。"""
    tree = ast.parse(source)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    found[f"{node.name}.{item.name}"] = item
    return found


def api_like_attributes(node):
    """関数の中で参照している、Win32 API らしい属性名(先頭大文字・小文字を含む。DWORD や WM_NULL のような定数は除く)。"""
    return {
        n.attr
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute)
        and _API_LIKE.fullmatch(n.attr)
        and any(ch.islower() for ch in n.attr)
    }


# 偽ネイティブ用のシステムコール名(番号はこのテストの中だけの約束。実機の番号表は別に確認する)
FAKE_SYSCALL_NAMES = {
    0x14E1: "NtUserMsgWaitForMultipleObjectsEx",
    0x1005: "NtUserMessageCall",
    0x1004: "NtUserGetMessage",
    0x4: "NtWaitForSingleObject",
}


class FakeNative:
    """偽のネイティブ層。実プロセスにも窓にも触れない。"""

    def __init__(self, pid=222, tid=7):
        self.pid = pid
        self.tid = tid
        self.ticks = 1000
        self.fail = set()
        self.alive = True
        self.exists = True
        self.created = 123456789
        self.ui = {
            "tid": tid,
            "hwnd": 900,
            "class": "TkTopLevel",
            "visible": True,
            "source": "window",
        }
        self.flags = 0
        self.ctx = 100
        self.kernel = 0
        self.user = 0
        self.cycles = 0
        self.state = "Waiting"
        self.wait = "WrUserRequest"
        self.page_faults = 5000
        self.hard_faults = 10
        self.working_set = 100 * 1024 * 1024
        self.hung = False
        self.menu_owner = 0
        self.wm_null_calls = 0
        self.wm_null_result = {"result": "ok", "elapsed_ms": 0.1, "error": 0}
        # 外部見張り(投稿)用
        self.post_calls = 0
        self.posted = []  # 投稿の宛先 tid(WM_NULL のみ)
        self.post_result = {"ok": True, "error": 0}
        self.verify_calls = []  # (tid, hwnd, expected_created)
        self.verify_result = {"ok": True, "reason": None}
        self.other_user = 0
        self.other_state = "Waiting"
        self.other_ctx = 1
        self.open_log = []
        self.closed = False
        # 待ち先診断用: tid -> (status, syscall番号, 第1引数, 待機の長さ[100ns])
        self.syscalls = {
            tid: (
                0,
                0x14E1,
                2,
                5000,
            ),  # NtUserMsgWaitForMultipleObjectsEx(Tclの通常待機)
            tid + 1: (0, 0x4, 2, 5000),  # NtWaitForSingleObject 相当
        }
        self.syscall_denied = set()
        self.syscall_calls = 0
        self.windows = {}  # hwnd -> window_info の結果
        self.processes = {}  # pid -> {"image": str, "threads": {tid: thread dict}}
        self.image = "python.exe"

    def _maybe(self, api):
        if api in self.fail:
            raise OSError(0, f"{api} failed", None, 5)

    def tick_ms(self):
        return self.ticks

    def open_target(self, pid):
        self.open_log.append(("process", PROCESS_QUERY_LIMITED_INFORMATION))
        self._maybe("OpenProcess")
        return {"created": self.created}

    def close(self):
        self.closed = True

    def process_alive(self):
        self._maybe("GetExitCodeProcess")
        return self.alive

    def thread_syscall(self, tid):
        self.syscall_calls += 1
        if tid in self.syscall_denied:
            raise OSError(0, "OpenThread failed", None, 5)
        self._maybe("ThreadLastSystemCall")
        entry = ("thread-syscall", THREAD_SYSCALL_ACCESS)
        if entry not in self.open_log:
            self.open_log.append(entry)
        status, number, arg, wait = self.syscalls.get(
            tid, (STATUS_UNSUCCESSFUL, None, None, None)
        )
        return {
            "status": status,
            "number": number,
            "first_arg": arg,
            "wait_100ns": wait,
        }

    def window_info(self, hwnd):
        self._maybe("window_info")
        info = self.windows.get(hwnd)
        return dict(info) if info else None

    def process_windows(self, pid, limit=24):
        return [
            {
                "hwnd": 900,
                "tid": self.tid,
                "class": "TkTopLevel",
                "title": "PageFolio",
                "visible": True,
                "enabled": True,
                "owner": 0,
            }
        ]

    def other_process_snapshot(self, pid):
        proc = self.processes.get(pid)
        if proc is None:
            return None
        return {"process": {"image": proc["image"]}, "threads": proc["threads"]}

    def find_ui_thread(self, pid):
        self._maybe("EnumWindows")
        return dict(self.ui) if self.ui else None

    def gui_thread_info(self, tid):
        self._maybe("GetGUIThreadInfo")
        return {
            "flags": self.flags,
            "active": 900,
            "focus": 901,
            "capture": 0,
            "menu_owner": self.menu_owner,
            "move_size": 0,
        }

    def thread_cpu(self, tid):
        self._maybe("GetThreadTimes")
        return {
            "kernel_100ns": self.kernel,
            "user_100ns": self.user,
            "cycles": self.cycles,
        }

    def system_snapshot(self, pid):
        self._maybe("NtQuerySystemInformation")
        if not self.exists:
            return None
        return {
            "process": {
                "threads": 9,
                "hard_faults": self.hard_faults,
                "create_time": 0,
                "user_100ns": 0,
                "kernel_100ns": 0,
                "handles": 100,
                "page_faults": self.page_faults,
                "working_set": self.working_set,
                "read_ops": 1,
                "write_ops": 2,
                "other_ops": 3,
                "image": self.image,
            },
            "threads": {
                self.tid: {
                    "kernel_100ns": self.kernel,
                    "user_100ns": self.user,
                    "create_time": 1,
                    "wait_time": 0,
                    "start_address": 0,
                    "ctx": self.ctx,
                    "state": self.state,
                    "wait_reason": self.wait,
                },
                self.tid + 1: {
                    "kernel_100ns": 0,
                    "user_100ns": self.other_user,
                    "create_time": 5,
                    "wait_time": 0,
                    "start_address": 0,
                    "ctx": self.other_ctx,
                    "state": self.other_state,
                    "wait_reason": "WrUserRequest",
                },
            },
        }

    def process_memory(self):
        self._maybe("K32GetProcessMemoryInfo")
        return {"page_faults": self.page_faults, "working_set": self.working_set}

    def is_hung(self, hwnd):
        self._maybe("IsHungAppWindow")
        return self.hung

    def wm_null(self, hwnd, timeout_ms):
        self.wm_null_calls += 1
        return dict(self.wm_null_result)

    def verify_post_target(self, tid, hwnd, expected_created):
        self.verify_calls.append((tid, hwnd, expected_created))
        self._maybe("verify_post_target")
        return dict(self.verify_result)

    def post_wm_null(self, tid):
        self.post_calls += 1
        self.posted.append(tid)
        self._maybe("PostThreadMessageW")
        return dict(self.post_result)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def make_rows(spec):
    """解析の単体確認用に、(elapsed_s, ctx, cpu_ms, flags, state, wait, hung)から行を作る。"""
    rows = []
    for index, item in enumerate(spec):
        elapsed, ctx, cpu, flags, state, wait, hung = item
        rows.append(
            {
                "seq": index + 1,
                "t": f"2026-01-01T00:00:{elapsed:06.3f}+00:00",
                "tick_ms": 1_000_000 + int(elapsed * 1000),
                "elapsed_s": elapsed,
                "phase": "peer",
                "cost_ms": 1.0,
                "tid": 7,
                "hwnd": 900,
                "gui_flags": flags,
                "cpu_kernel_ms": 0.0,
                "cpu_user_ms": cpu,
                "cycles_m": cpu,
                "state": state,
                "wait_reason": wait,
                "ctx_switches": ctx,
                "page_faults": 1000,
                "hard_faults": 0,
                "working_set_kb": 1000,
                "hung": hung,
            }
        )
    return rows


def check_offline(say=print):
    """偽ネイティブ・偽時計・合成バッファによる確認。窓にも実プロセスにも触れない。"""
    failures = []

    def check(name, condition, detail=""):
        say(
            f"  [{'ok' if condition else 'FAIL'}] {name}"
            + (f" ... {detail}" if not condition and detail else "")
        )
        if not condition:
            failures.append(name)

    say("-- 静的検査(本ファイルのコード) --")
    source = Path(__file__).read_text(encoding="utf-8")
    used = used_native_names(source)
    # 禁止名は FORBIDDEN_NAMES の定義(文字列)としては現れるが、コードの名前/属性としては現れない
    hit = sorted(set(FORBIDDEN_NAMES) & used)
    check("入力/前景/書き込み/停止系のAPI名をコードで参照していない", not hit, str(hit))
    opens = {"OpenProcess": [], "OpenThread": []}
    assigned = {}
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in opens
        ):
            first = node.args[0] if node.args else None
            opens[node.func.attr].append(getattr(first, "id", None))
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "access"
            and isinstance(node.value, ast.Name)
        ):
            assigned.setdefault(node.value.id, 0)
            assigned[node.value.id] += 1
    check(
        "OpenProcess は1か所(LIMITED_INFORMATION)、OpenThread は2か所(LIMITED_INFORMATION と ThreadLastSystemCall 用の最小権限)だけ",
        PROCESS_QUERY_LIMITED_INFORMATION == 0x1000
        and THREAD_QUERY_LIMITED_INFORMATION == 0x0800
        and opens == {"OpenProcess": ["access"], "OpenThread": ["access", "access"]}
        and assigned
        == {
            "PROCESS_QUERY_LIMITED_INFORMATION": 1,
            "THREAD_QUERY_LIMITED_INFORMATION": 1,
            "THREAD_SYSCALL_ACCESS": 1,
        },
        f"opens={opens} assigned={assigned}",
    )
    dangerous_thread_bits = (
        0x0001  # TERMINATE
        | 0x0002  # SUSPEND_RESUME
        | 0x0010  # SET_CONTEXT
        | 0x0020  # SET_INFORMATION
        | 0x0080  # SET_THREAD_TOKEN
        | 0x0100  # IMPERSONATE
        | 0x0200  # DIRECT_IMPERSONATION
        | 0x0400  # SET_LIMITED_INFORMATION
        | 0x10000  # DELETE
        | 0x40000  # WRITE_DAC
        | 0x80000  # WRITE_OWNER
    )
    check(
        "ThreadLastSystemCall 用の権限は THREAD_QUERY_INFORMATION|THREAD_GET_CONTEXT(0x48)ちょうどで、停止/書き込み系のビットを含まない",
        THREAD_SYSCALL_ACCESS == 0x48
        and THREAD_SYSCALL_ACCESS == (THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT)
        and not (THREAD_SYSCALL_ACCESS & dangerous_thread_bits),
        hex(THREAD_SYSCALL_ACCESS),
    )
    check(
        "GetThreadContext/SuspendThread/ResumeThread/SetThreadContext 系と GetWindowText(メッセージを送る)を禁止名に含めている",
        {
            "GetThreadContext",
            "SuspendThread",
            "ResumeThread",
            "SetThreadContext",
            "NtSuspendThread",
            "GetWindowTextW",
        }
        <= set(FORBIDDEN_NAMES),
    )

    say(
        "-- 外部見張りの静的検査(投稿の経路が PostThreadMessageW(WM_NULL) だけであること) --"
    )
    funcs = function_nodes(source)
    post_calls_by_func = {}
    post_refs_other = set()
    for qual, fn in funcs.items():
        calls = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "PostThreadMessageW"
        ]
        call_func_ids = {id(c.func) for c in calls}
        if calls:
            post_calls_by_func[qual] = calls
        if any(
            isinstance(n, ast.Attribute)
            and n.attr == "PostThreadMessageW"
            and id(n) not in call_func_ids
            for n in ast.walk(fn)
        ):
            post_refs_other.add(qual)
    check(
        "PostThreadMessageW を呼ぶ関数は Win32Native.post_wm_null(見張りの投稿)と _live_ghost(機構確認で幽霊を作る)だけ",
        set(post_calls_by_func) == POST_THREAD_MESSAGE_CALLERS,
        str(sorted(post_calls_by_func)),
    )
    post_call = (post_calls_by_func.get("Win32Native.post_wm_null") or [None])[0]
    post_args = list(getattr(post_call, "args", []))
    check(
        "見張りの投稿は1か所で、メッセージは定数 WM_NULL(=0)・wParam/lParam は 0",
        len(post_calls_by_func.get("Win32Native.post_wm_null", [])) == 1
        and WM_NULL == 0
        and len(post_args) == 4
        and isinstance(post_args[1], ast.Name)
        and post_args[1].id == "WM_NULL"
        and all(isinstance(a, ast.Constant) and a.value == 0 for a in post_args[2:]),
        ast.dump(post_call) if post_call is not None else "no call",
    )
    check(
        "PostThreadMessageW を呼び出さずに参照する(型の宣言)のは Win32Native._bind と _live_ghost だけ",
        post_refs_other <= {"Win32Native._bind", "_live_ghost"},
        str(sorted(post_refs_other)),
    )
    post_wm_callers = sorted(
        qual
        for qual, fn in funcs.items()
        if not qual.startswith(("check_", "_live", "FakeNative"))
        and any(
            isinstance(n, ast.Attribute) and n.attr == "post_wm_null"
            for n in ast.walk(fn)
        )
    )
    check(
        "post_wm_null を呼ぶのは UiThreadProbe.wake_once だけ(宛先の確認の後)",
        post_wm_callers == ["UiThreadProbe.wake_once"],
        str(post_wm_callers),
    )
    dangerous = set(FORBIDDEN_NAMES) | {
        "SendMessageTimeoutW",
        "wm_null",
        "OpenProcess",
        "OpenThread",
        "SendMessageW",
        "PostMessageW",
    }
    wake_funcs_ok = all(name in funcs for name in WAKE_PATH_FUNCTIONS)
    wake_apis = {}
    wake_dangerous = {}
    for name in WAKE_PATH_FUNCTIONS:
        fn = funcs.get(name)
        if fn is None:
            continue
        wake_apis[name] = sorted(api_like_attributes(fn))
        names = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)} | {
            n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
        }
        if names & dangerous:
            wake_dangerous[name] = sorted(names & dangerous)
    check(
        "見張りの経路(宛先の確認と投稿)が使う Win32 API は、許可した読み取り API と PostThreadMessageW だけ",
        wake_funcs_ok
        and all(set(apis) <= WAKE_ALLOWED_APIS for apis in wake_apis.values())
        and "PostThreadMessageW" in wake_apis.get("Win32Native.post_wm_null", []),
        str(wake_apis),
    )
    check(
        "見張りの経路は SendMessage 系・前景/入力系・停止/書き込み系の名前を参照しない(送信の wm_null も呼ばない)",
        wake_funcs_ok and not wake_dangerous,
        str(wake_dangerous),
    )
    check(
        "見張りの周期は利用者が承認した 100〜150ms の範囲",
        WAKE_PERIOD_RANGE_MS == (100, 150),
    )

    say("-- SystemProcessInformation の解析(合成バッファ) --")
    buf = build_fake_system_process_information(
        [
            {"pid": 4, "threads": [{"tid": 8}]},
            {
                "pid": 222,
                "threads": [
                    {
                        "tid": 7,
                        "ctx": 55,
                        "state": 5,
                        "wait": 13,
                        "kernel": 20000,
                        "user": 30000,
                    },
                    {"tid": 9, "ctx": 3, "state": 2, "wait": 0, "created": 99},
                ],
                "page_faults": 4242,
                "hard_faults": 17,
                "working_set": 8192 * 1024,
                "io": (11, 22, 33),
                "handles": 321,
                "create_time": 77,
            },
            {"pid": 300, "threads": []},
        ]
    )
    parsed = parse_system_process_information(buf, 222)
    check("pidの1件を取り出す(前後のprocessを飛ばす)", parsed is not None)
    process = (parsed or {}).get("process", {})
    threads = (parsed or {}).get("threads", {})
    check(
        "process: page_faults/hard_faults/working_set/io/handles/threads",
        process.get("page_faults") == 4242
        and process.get("hard_faults") == 17
        and process.get("working_set") == 8192 * 1024
        and (
            process.get("read_ops"),
            process.get("write_ops"),
            process.get("other_ops"),
        )
        == (11, 22, 33)
        and process.get("handles") == 321
        and process.get("threads") == 2,
        str(process),
    )
    check(
        "thread: tid/ctx/state/wait_reason/kernel/user",
        threads.get(7, {}).get("ctx") == 55
        and threads[7]["state"] == "Waiting"
        and threads[7]["wait_reason"] == "WrUserRequest"
        and threads[7]["kernel_100ns"] == 20000
        and threads[7]["user_100ns"] == 30000
        and threads.get(9, {}).get("state") == "Running"
        and threads[9]["create_time"] == 99,
        str(threads),
    )
    check("存在しないpidは None", parse_system_process_information(buf, 999) is None)
    check(
        "末尾のprocess(スレッド0)も読める",
        parse_system_process_information(buf, 300)["threads"] == {},
    )
    check(
        "空/短いバッファでも例外にしない",
        parse_system_process_information(b"", 1) is None,
    )
    image_buf = build_fake_system_process_information(
        [
            {"pid": 4, "threads": [{"tid": 8}], "image": "System"},
            {"pid": 222, "threads": [{"tid": 7}, {"tid": 9}], "image": "python.exe"},
            {"pid": 300, "threads": []},
        ],
        base_address=0x7000_0000,
    )
    with_base = parse_system_process_information(image_buf, 222, 0x7000_0000)
    check(
        "イメージ名: base_address を渡すと UNICODE_STRING(バッファ内ポインタ)から読め、別プロセスを開かずに実行ファイル名が分かる",
        with_base["process"]["image"] == "python.exe"
        and parse_system_process_information(image_buf, 4, 0x7000_0000)["process"][
            "image"
        ]
        == "System"
        and parse_system_process_information(image_buf, 300, 0x7000_0000)["process"][
            "image"
        ]
        is None
        and sorted(with_base["threads"]) == [7, 9],
        str(with_base["process"]),
    )
    check(
        "イメージ名: base_address なし/範囲外のポインタなら None(例外にしない)",
        parse_system_process_information(image_buf, 222)["process"]["image"] is None
        and parse_system_process_information(image_buf, 222, 0x1)["process"]["image"]
        is None,
    )

    say("-- サンプラ(偽ネイティブ・偽時計) --")

    def new_probe(native=None, **kw):
        native = native or FakeNative()
        kw.setdefault("syscall_names", FAKE_SYSCALL_NAMES)
        clock = FakeClock()
        phase = {"v": "peer"}
        probe = UiThreadProbe(
            native,
            222,
            expected_created=native.created,
            clock=clock,
            wall=lambda: f"2026-01-01T00:00:{clock.t:09.6f}+00:00",
            t0=0.0,
            phase_fn=lambda: phase["v"],
            **kw,
        )
        probe._open_target()
        return probe, native, clock, phase

    probe, native, clock, phase = new_probe()
    row = probe.sample_once()
    check(
        "1サンプルに flags/focus/cpu/wait/ctx/page_faults/threads/hung/tick/phase が入る",
        row["gui_flags"] == 0
        and row["hwnd_focus"] == 901
        and row["cpu_user_ms"] == 0.0
        and row["state"] == "Waiting"
        and row["wait_reason"] == "WrUserRequest"
        and row["ctx_switches"] == 100
        and row["page_faults"] == 5000
        and row["pf_gmpi"] == 5000
        and row["threads"] == 9
        and row["hung"] is False
        and row["tick_ms"] == 1000
        and row["phase"] == "peer"
        and row["tid"] == 7
        and row["hwnd"] == 900
        and row["others_cpu_ms"] == 0.0
        and row["busy_threads"] == 0
        and not row["errors"],
        str(row),
    )
    probe_b, native_b, _clock_b, _phase_b = new_probe()
    native_b.other_user = 500_000  # 他スレッドのCPU 50ms
    native_b.other_state = "Running"
    row_busy = probe_b.sample_once()
    check(
        "他スレッドのCPU時間と実行中スレッド数を別列に残す(UIスレッドは含めない)",
        row_busy["others_cpu_ms"] == 50.0
        and row_busy["busy_threads"] == 1
        and row_busy["cpu_user_ms"] == 0.0,
        str({k: row_busy[k] for k in ("others_cpu_ms", "busy_threads", "cpu_user_ms")}),
    )

    check(
        "対象の同一性(作成時刻)を検証済みと記録",
        probe.target["identity_verified"] is True,
    )
    clock.advance(0.1)
    phase["v"] = "post-peer"
    native.ticks += 100
    row2 = probe.sample_once()
    check(
        "phase の切替とelapsed_sがサンプルに反映される",
        row2["phase"] == "post-peer" and row2["elapsed_s"] == 0.1 and row2["seq"] == 2,
    )
    check(
        "壁時計はuat_row.now()と同じ書式(+00:00付きISO)",
        bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?\+00:00", row2["t"])),
        row2["t"],
    )
    check(
        "WM_NULL既定OFF: start()してもnative.wm_nullを呼ばない",
        native.wm_null_calls == 0 and probe._wm_thread is None,
    )

    probe, native, clock, phase = new_probe()
    native.fail = {
        "GetGUIThreadInfo",
        "GetThreadTimes",
        "IsHungAppWindow",
        "K32GetProcessMemoryInfo",
    }
    row = probe.sample_once()
    check(
        "個々のAPIが失敗しても他の列は埋まり、例外にならない",
        row["gui_flags"] is None
        and row["cpu_user_ms"] == 0.0  # NTの値で代替
        and row["ctx_switches"] == 100
        and row["page_faults"] == 5000
        and row["pf_gmpi"] is None
        and sorted(row["errors"])
        == sorted(
            [
                "GetGUIThreadInfo",
                "GetThreadTimes",
                "IsHungAppWindow",
                "K32GetProcessMemoryInfo",
            ]
        ),
        str(row),
    )
    check(
        "失敗はerror_countsに種類別に残る",
        probe.error_counts.get("GetGUIThreadInfo:winerror=5") == 1,
        str(dict(probe.error_counts)),
    )

    probe, native, clock, phase = new_probe()
    native.fail = {"OpenProcess"}
    probe2 = UiThreadProbe(native, 222, clock=clock, wall=lambda: "t", t0=0.0)
    probe2._open_target()
    row = probe2.sample_once()
    check(
        "OpenProcess失敗: open_failuresに記録し、NT/窓の観測は続ける",
        len(probe2.open_failures) == 1
        and probe2.open_failures[0]["api"] == "OpenProcess"
        and row["ctx_switches"] == 100
        and row["gui_flags"] == 0,
        str(probe2.open_failures),
    )

    native = FakeNative()
    native.created = 1
    probe = UiThreadProbe(
        native, 222, expected_created=2, clock=FakeClock(), wall=lambda: "t", t0=0.0
    )
    probe._open_target()
    row = probe.sample_once()
    check(
        "作成時刻が違う(PID再利用)なら対象にしない",
        probe.target["identity_verified"] is False
        and row["errors"] == ["identity-mismatch"]
        and row["ctx_switches"] is None,
    )

    probe, native, clock, phase = new_probe()
    native.alive = False
    for _ in range(6):
        clock.advance(0.1)
        probe.sample_once()
    check(
        "対象プロセスが終了: goneを記録し、終了後の行は3件で打ち切る",
        probe.gone_at is not None
        and sum(1 for r in probe.rows if r.get("gone")) == 3
        and probe.gone_rows_dropped == 3,
        f"gone_at={probe.gone_at} rows={len(probe.rows)} dropped={probe.gone_rows_dropped}",
    )

    probe, native, clock, phase = new_probe()
    native.ui = None
    row = probe.sample_once()
    check(
        "窓が無ければ最古スレッドをUIスレッドとする(oldest-thread)",
        row["tid"] == 7 and probe.ui_log[0]["source"] == "oldest-thread",
        str(probe.ui_log),
    )
    native.ui = {
        "tid": 7,
        "hwnd": 950,
        "class": "TkTopLevel",
        "visible": True,
        "source": "window",
    }
    clock.advance(2.0)
    row = probe.sample_once()
    check(
        "窓が現れたら切り替え、変更をui_thread_logに記録",
        row["hwnd"] == 950
        and probe.ui_log[-1]["hwnd"] == 950
        and len(probe.ui_log) == 2,
    )
    native.ui = None
    clock.advance(2.0)
    row = probe.sample_once()
    check("窓が消えても直前のUIスレッドを保つ", row["tid"] == 7 and row["hwnd"] == 950)

    # WM_NULL: フラグONでもphase外では呼ばない/phase内では呼ぶ
    probe, native, clock, phase = new_probe(wm_null=True, wm_null_interval=0.01)
    probe.sample_once()
    phase["v"] = "start-harness"
    probe._thread = None
    probe._wm_thread = threading.Thread(target=probe._run_wm_null, daemon=True)
    probe._wm_thread.start()
    time.sleep(0.15)
    calls_outside = native.wm_null_calls
    phase["v"] = "peer"
    time.sleep(0.15)
    probe._stop.set()
    probe._wm_thread.join(timeout=2)
    check(
        "WM_NULL ON: phase外(start-harness)では呼ばず、peerで呼んでログに残す",
        calls_outside == 0
        and native.wm_null_calls > 0
        and probe.wm_null_log
        and probe.wm_null_log[0]["phase"] == "peer",
        f"outside={calls_outside} total={native.wm_null_calls}",
    )

    say("-- 外部見張り(偽ネイティブ: 宛先の確認・投稿・失敗・拒否・集計) --")
    # OFF(既定): スレッドも作らず、投稿も確認も一度も呼ばない
    probe = UiThreadProbe(
        FakeNative(),
        222,
        expected_created=FakeNative().created,
        interval=0.05,
        phase_fn=lambda: "peer",
        syscall_names=FAKE_SYSCALL_NAMES,
    )
    native_off = probe.native
    probe.start()
    time.sleep(0.25)
    probe.wake_once()  # ログが無ければ何もしない
    probe.stop()
    off_summary = probe.summary()
    check(
        "見張りOFF(既定): スレッドを作らず、投稿・宛先の確認を1回も呼ばず、行の wake 列は空、summary は external_wake=None",
        probe._wake_thread is None
        and probe.wake_log is None
        and native_off.post_calls == 0
        and native_off.verify_calls == []
        and off_summary["external_wake"] is None
        and off_summary["options"]["external_wake_ms"] is None
        and all(r.get("wake_ok") is None for r in probe.rows)
        and len(probe.rows) >= 3,
        f"rows={len(probe.rows)} post={native_off.post_calls}",
    )

    probe, native, clock, phase = new_probe(external_wake_ms=120)
    probe.sample_once()  # UIスレッド(tid=7, hwnd=900)を特定する
    phase["v"] = "awaiting-enter"
    probe.wake_once(1000.0)
    phase["v"] = "peer"
    probe.wake_once(1120.0)
    probe.wake_once(1250.0)
    row = probe.sample_once()
    wake = probe.wake_summary()
    check(
        "見張りON: 毎回、宛先の確認(tid=7, hwnd=900, 作成時刻)の後に tid=7 へだけ投稿し、件数・phase別・間隔の統計を残す",
        native.posted == [7, 7, 7]
        and native.verify_calls == [(7, 900, native.created)] * 3
        and wake["posts_ok"] == 3
        and wake["posts_failed"] == 0
        and wake["refused"] == 0
        and wake["by_phase"] == {"awaiting-enter": 1, "peer": 2}
        and wake["interval_ms"]["count"] == 2
        and wake["interval_ms"]["max"] == 130.0
        and wake["interval_ms"]["over_2x_period"] == 0
        and row["wake_ok"] == 3
        and row["wake_fail"] == 0,
        str(wake),
    )
    probe.wake_once(1900.0)  # 周期(120)の2倍を超える間隔 = 見張りが止まっていた印
    wake = probe.wake_summary()
    check(
        "見張りON: 成功した投稿の間隔が周期の2倍を超えたら over_2x_period と long_gaps に残す",
        wake["interval_ms"]["over_2x_period"] == 1
        and wake["long_gaps"][0]["gap_ms"] == 650.0
        and wake["interval_ms"]["max"] == 650.0,
        str(wake["long_gaps"]),
    )

    probe, native, clock, phase = new_probe(external_wake_ms=120)
    probe.sample_once()
    native.verify_result = {"ok": False, "reason": "thread-not-in-target-process"}
    probe.wake_once(0.0)
    wake = probe.wake_summary()
    check(
        "宛先の確認に失敗したら投稿しない(post_calls=0)。拒否として理由を残し、行の wake_fail に数える",
        native.post_calls == 0
        and wake["posts_ok"] == 0
        and wake["refused"] == 1
        and wake["by_error"] == {"thread-not-in-target-process": 1}
        and wake["failures"][0]["kind"] == "refused"
        and probe.sample_once()["wake_fail"] == 1,
        str(wake),
    )
    native.verify_result = {"ok": False, "reason": "process-exited"}
    probe.wake_once(50.0)
    check(
        "対象が終了していた(process-exited / thread-exited)ときは、拒否ではなく見送り(target-exited)に数え、投稿しない",
        native.post_calls == 0
        and probe.wake_summary()["skipped"] == {"target-exited": 1}
        and probe.wake_summary()["refused"] == 1,
        str(probe.wake_summary()["skipped"]),
    )
    native.verify_result = {"ok": True, "reason": None}
    native.post_result = {"ok": False, "error": 1444}  # ERROR_INVALID_THREAD_ID
    probe.wake_once(100.0)
    wake = probe.wake_summary()
    check(
        "PostThreadMessageW が失敗したら failed として winerror 別に数え、続行する(例外にしない)",
        native.post_calls == 1
        and wake["posts_failed"] == 1
        and wake["by_error"].get("winerror=1444") == 1
        and wake["posts_ok"] == 0,
        str(wake),
    )
    native.fail = {"verify_post_target"}
    probe.wake_once(200.0)
    native.fail = {"PostThreadMessageW"}
    native.verify_result = {"ok": True, "reason": None}
    probe.wake_once(300.0)
    wake = probe.wake_summary()
    check(
        "宛先の確認や投稿が例外を投げても落ちず、拒否/失敗として記録する(確認が例外なら投稿しない)",
        native.post_calls == 2
        and wake["refused"] == 2
        and wake["posts_failed"] == 2
        and "verify-exception:winerror=5" in wake["by_error"]
        and "winerror=5" in wake["by_error"],
        str(wake),
    )

    mismatch_native = FakeNative()
    mismatch_native.created = 1
    mismatch_probe = UiThreadProbe(
        mismatch_native,
        222,
        expected_created=2,
        clock=FakeClock(),
        wall=lambda: "t",
        t0=0.0,
        external_wake_ms=120,
    )
    mismatch_probe._open_target()
    mismatch_probe.sample_once()
    mismatch_probe.wake_once(0.0)
    no_expected = FakeNative()
    no_expected_probe = UiThreadProbe(
        no_expected,
        222,
        clock=FakeClock(),
        wall=lambda: "t",
        t0=0.0,
        external_wake_ms=120,
    )
    no_expected_probe._open_target()
    no_expected_probe.sample_once()
    no_expected_probe.wake_once(0.0)
    check(
        "対象の作成時刻が一致しない(PID再利用)/期待する作成時刻が無いときは、確認も投稿もせず拒否する(identity-unverified)",
        mismatch_native.post_calls == 0
        and mismatch_native.verify_calls == []
        and mismatch_probe.wake_summary()["by_error"] == {"identity-unverified": 1}
        and no_expected.post_calls == 0
        and no_expected_probe.wake_summary()["by_error"] == {"identity-unverified": 1},
    )

    probe, native, clock, phase = new_probe(external_wake_ms=120, wake_max_posts=2)
    probe.sample_once()
    for index in range(4):
        probe.wake_once(index * 120.0)
    check(
        "投稿の上限(キュー溢れの安全弁): 上限に達したら投稿せず post-limit として数える",
        native.post_calls == 2 and probe.wake_summary()["skipped"] == {"post-limit": 2},
    )
    probe, native, clock, phase = new_probe(external_wake_ms=120)
    probe.wake_once(0.0)  # UIスレッドが未特定
    probe.sample_once()
    probe._gone = True  # 対象が消えた
    probe.wake_once(120.0)
    check(
        "UIスレッド未特定/対象消滅のときは投稿せず skipped に数える(失敗ではない)",
        native.post_calls == 0
        and probe.wake_summary()["skipped"]
        == {"ui-thread-unknown": 1, "target-gone": 1}
        and probe.wake_summary()["posts_failed"] == 0,
        str(probe.wake_summary()["skipped"]),
    )

    probe, native, clock, phase = new_probe(external_wake_ms=100)
    probe.sample_once()
    probe._wake_thread = threading.Thread(target=probe._run_wake, daemon=True)
    probe._wake_thread.start()
    time.sleep(0.55)
    probe._stop.set()
    probe._wake_thread.join(timeout=2)
    wake = probe.wake_summary()
    check(
        "見張りのスレッドは約100msごとに投稿し、止めると終わる(0.55秒で4〜7回・宛先は tid=7 だけ)",
        4 <= wake["posts_ok"] <= 7
        and set(native.posted) == {7}
        and not probe._wake_thread.is_alive()
        and (wake["interval_ms"]["max"] or 0) < 400,
        str(wake["interval_ms"]) + f" posts={wake['posts_ok']}",
    )
    json.dumps(probe.summary(), ensure_ascii=False)
    check(
        "見張りONの summary がJSON化でき、options と external_wake と getmessage を持つ",
        probe.summary()["options"]["external_wake_ms"] == 100
        and probe.summary()["external_wake"]["posts_ok"] == wake["posts_ok"]
        and "getmessage" in probe.summary(),
    )

    say("-- GetMessage 区間(タイムアウトの無い待機)の検出(合成の行) --")

    def gm_rows(spec):
        out = []
        for index, (call, wait_ms) in enumerate(spec):
            out.append(
                {
                    "seq": index + 1,
                    "t": f"2026-01-01T00:00:{index * 0.05:06.3f}+00:00",
                    "tick_ms": 1_000_000 + index * 50,
                    "phase": "post-peer",
                    "syscall": call,
                    "sc_wait_ms": wait_ms,
                    "wake_ok": index // 2,
                }
            )
        return out

    healthy_gm = gm_rows([("NtUserMsgWaitForMultipleObjectsEx", 30.0)] * 20)
    healed = gm_rows(
        [("NtUserMsgWaitForMultipleObjectsEx", 30.0)] * 5
        + [(GETMESSAGE_CALL, 40.0), (GETMESSAGE_CALL, 90.0)]
        + [("NtUserMsgWaitForMultipleObjectsEx", 30.0)] * 5
        + [(GETMESSAGE_CALL, 20.0)]
    )
    stuck = gm_rows(
        [("NtUserMsgWaitForMultipleObjectsEx", 30.0)] * 3
        + [(GETMESSAGE_CALL, 100.0 + 50 * i) for i in range(120)]
        + [("NtUserMsgWaitForMultipleObjectsEx", 30.0)] * 3
    )
    sum_healthy = summarize_getmessage(healthy_gm)
    sum_healed = summarize_getmessage(healed)
    sum_stuck = summarize_getmessage(stuck)
    check(
        "健全な行は GetMessage 区間なし。健全な待機(MsgWait)は GetMessage に数えない",
        sum_healthy["runs"] == 0
        and sum_healthy["stalls"] == 0
        and sum_healthy["syscall_columns"] is True,
    )
    check(
        "見張りで解消された短い GetMessage(2行・最大待機90ms と 1行)は区間2件・停止0件",
        sum_healed["runs"] == 2
        and sum_healed["rows"] == 3
        and sum_healed["stalls"] == 0
        and sum_healed["max_length_ms"] == 90.0
        and getmessage_runs(healed)[0].get("wake_posts_during") == 1,
        str(sum_healed),
    )
    check(
        "GetMessage に120行(待機が最大6050ms)居続けた区間は停止1件(しきい値400ms)・最大長6050ms",
        sum_stuck["runs"] == 1
        and sum_stuck["stalls"] == 1
        and sum_stuck["max_rows"] == 120
        and sum_stuck["max_length_ms"] == 6050.0,
        str(sum_stuck),
    )
    still_rows = [
        dict(r, wake_ok=7) for r in stuck
    ]  # 投稿の累計が増えない(見張りが止まっていた)停止
    check(
        "停止のうち『投稿が流れている最中』を区別する: 投稿の累計が区間内で増えている停止は stalls_while_posting=1、増えていない停止は0",
        sum_stuck["stalls_while_posting"] == 1
        and summarize_getmessage(still_rows)["stalls"] == 1
        and summarize_getmessage(still_rows)["stalls_while_posting"] == 0
        and sum_healed["stalls_while_posting"] == 0,
        str(
            (
                sum_stuck["stalls_while_posting"],
                summarize_getmessage(still_rows)["stalls_while_posting"],
            )
        ),
    )
    good = {
        "posts_ok": 400,
        "posts_failed": 0,
        "refused": 0,
        "skipped": {},
        "interval_ms": {"max": 140.0},
    }
    check(
        "見張りの動作の目安(wake_health): 正常は healthy。投稿が少ない・拒否がある・失敗が多い・間隔が周期の5倍超・見送りが多いのどれかで理由つきの not healthy",
        wake_health(good, 120)["healthy"] is True
        and wake_health({**good, "posts_ok": 5}, 120)["healthy"] is False
        and wake_health({**good, "refused": 1}, 120)["reasons"] == ["refused=1"]
        and wake_health({**good, "posts_failed": 9}, 120)["healthy"] is False
        and wake_health({**good, "posts_failed": 8}, 120)["healthy"] is True
        and wake_health({**good, "interval_ms": {"max": 700.0}}, 120)["healthy"]
        is False
        and wake_health({**good, "interval_ms": {"max": 600.0}}, 120)["healthy"] is True
        and wake_health({**good, "skipped": {"ui-thread-unknown": 11}}, 120)["healthy"]
        is False,
        str(wake_health({**good, "posts_ok": 5, "refused": 1}, 120)),
    )
    check(
        "syscall 列が無い古い診断の行は syscall_columns=False(GetMessage 区間0件と区別できる)",
        summarize_getmessage([{"tick_ms": 1, "ctx_switches": 5}])["syscall_columns"]
        is False,
    )

    say(
        "-- 待ち先の診断(偽ネイティブ: ThreadLastSystemCall・宛先窓・連鎖・他スレッドctx) --"
    )
    check(
        "窓ハンドルの切り出し: 0/小さい値/上位32bitが不正な値は除き、符号拡張は下位32bitにする",
        hwnd_from_arg(0) is None
        and hwnd_from_arg(0x50) is None
        and hwnd_from_arg(0x2000A) == 0x2000A
        and hwnd_from_arg(0x1_0000_0001) is None
        and hwnd_from_arg(0xFFFF_FFFF_FFFF_FFFD) == 0xFFFF_FFFD
        and hwnd_from_arg(0x2000A, HWND_MIN_SPECULATIVE) == 0x2000A
        and hwnd_from_arg(0x1234, HWND_MIN_SPECULATIVE) is None,
    )
    real_names, real_info = load_syscall_names()
    check(
        "この機械の ntdll.dll/win32u.dll からシステムコール番号表を作れる(NtUserMessageCall・NtUserGetMessage・NtWaitForSingleObject・NtClose を含む)",
        real_info["error"] is None
        and real_info["entries"] > 500
        and {
            "NtUserMessageCall",
            "NtUserGetMessage",
            "NtUserMsgWaitForMultipleObjectsEx",
            "NtWaitForSingleObject",
            "NtClose",
        }
        <= set(real_names.values()),
        str(real_info),
    )
    missing, missing_info = load_syscall_names("Z:/no-such-windows-root")
    check(
        "番号表を作れなくても例外にならず、空の表とエラー情報を返す",
        missing == {} and missing_info["error"] is not None,
    )

    waiting = {
        "kernel_100ns": 10000,
        "user_100ns": 20000,
        "create_time": 1,
        "wait_time": 1,
        "start_address": 0,
        "ctx": 12,
        "state": "Waiting",
        "wait_reason": "UserRequest",
    }

    probe, native, clock, phase = new_probe()
    row = probe.sample_once()
    check(
        "Tclの通常待機: 最後のシステムコール名/第1引数/待機の長さ/他スレッドのctx切替が列に入り、宛先窓は無し",
        row["syscall"] == "NtUserMsgWaitForMultipleObjectsEx"
        and row["sc_arg"] == 2
        and row["sc_status"] == 0
        and row["sc_wait_ms"] == 0.5
        and row["wait_target"] is None
        and row["others_ctx"] == [[8, 1, "WrUserRequest"]]
        and not row["errors"],
        str(row),
    )
    check(
        "ThreadLastSystemCall 用に開いた権限は 0x48(QUERY_INFORMATION|GET_CONTEXT)だけ",
        [x for x in native.open_log if x[0] == "thread-syscall"]
        == [("thread-syscall", 0x48)],
        str(native.open_log),
    )

    def blocked_probe():
        probe, native, clock, phase = new_probe()
        native.syscalls[7] = (0, 0x1005, 0x2000A, 25_000_000)
        native.windows[0x2000A] = {
            "hwnd": 0x2000A,
            "pid": 900,
            "tid": 91,
            "class": "MSCTFIME UI",
            "title": "",
            "visible": False,
            "hung": False,
        }
        native.processes[900] = {"image": "ctfmon.exe", "threads": {91: dict(waiting)}}
        native.syscalls[91] = (0, 0x1005, 0x20010, 10_000_000)
        native.windows[0x20010] = {
            "hwnd": 0x20010,
            "pid": 7000,
            "tid": 70,
            "class": "XamlExplorerHostIslandWindow",
            "title": "タスクの切り替え",
            "visible": True,
            "hung": False,
        }
        native.processes[7000] = {
            "image": "explorer.exe",
            "threads": {70: dict(waiting)},
        }
        native.syscalls[70] = (0, 0x14E1, 3, 1)
        return probe, native, clock, phase

    probe, native, clock, phase = blocked_probe()
    row = probe.sample_once()
    target = row["wait_target"] or {}
    check(
        "ブロック中のSendMessage(NtUserMessageCall): 第1引数を窓に解決し、宛先の所有pid/tid・クラス・イメージ名・スレッド状態・待機の長さを残す",
        row["syscall"] == "NtUserMessageCall"
        and row["sc_arg"] == 0x2000A
        and row["sc_wait_ms"] == 2500.0
        and target.get("valid") is True
        and target.get("by") == "known-call"
        and (target.get("pid"), target.get("tid")) == (900, 91)
        and target.get("class") == "MSCTFIME UI"
        and target.get("image") == "ctfmon.exe"
        and target.get("same_process") is False
        and target["thread"]["state"] == "Waiting"
        and target["thread"]["ctx"] == 12
        and target["thread"]["waited_ms"] == 984
        and target["thread_syscall"]["name"] == "NtUserMessageCall",
        str(target),
    )
    nxt = target.get("next") or {}
    check(
        "連鎖: 宛先スレッドもSendMessageで待っていれば、その宛先(explorer.exe の切替UI窓)まで辿り、終点で止まる",
        nxt.get("image") == "explorer.exe"
        and nxt.get("title") == "タスクの切り替え"
        and nxt.get("class") == "XamlExplorerHostIslandWindow"
        and nxt["thread_syscall"]["name"] == "NtUserMsgWaitForMultipleObjectsEx"
        and "next" not in nxt,
        str(nxt),
    )
    text = format_wait_target(target)
    check(
        "報告用の1行表現に両方の宛先(ctfmon.exe => explorer.exe)が入り、wait_target はJSON化できる",
        "ctfmon.exe" in text
        and "explorer.exe" in text
        and "=>" in text
        and bool(json.dumps(row, ensure_ascii=False)),
        text,
    )

    probe, native, clock, phase = blocked_probe()
    native.syscalls[7] = (0, 0x1005, 0x2000B, 100)
    native.windows[0x2000B] = {
        "hwnd": 0x2000B,
        "pid": 222,
        "tid": 8,
        "class": "TkChild",
        "title": "same-process",
        "visible": True,
        "hung": False,
    }
    row = probe.sample_once()
    target = row["wait_target"] or {}
    check(
        "宛先が同じプロセス(PageFolio自身の別スレッドの窓)なら same_process=true で、自プロセスのスレッド状態/イメージ名を使う",
        target.get("same_process") is True
        and target.get("image") == "python.exe"
        and target["thread"]["ctx"] == 1
        and target["thread_syscall"]["name"] == "NtWaitForSingleObject",
        str(target),
    )

    probe, native, clock, phase = blocked_probe()
    native.syscalls[91] = (0, 0x1005, 0x20010, 1)
    native.syscalls[70] = (0, 0x1005, 0x2000A, 1)  # 70 -> 0x2000A に戻る(循環)
    row = probe.sample_once()
    target = row["wait_target"] or {}
    check(
        "循環(A->B->A)は cycle=true で止まり、無限に辿らない",
        (target.get("next") or {}).get("next", {}).get("cycle") is True
        and (target["next"]["next"].get("hwnd")) == 0x2000A,
        str(target),
    )

    probe, native, clock, phase = blocked_probe()
    native.syscalls[7] = (0, 0x4, 0x2000A, 1)
    spec = probe.sample_once()["wait_target"] or {}
    native.syscalls[7] = (0, 0x4, 0x30000, 1)
    none_spec = probe.sample_once()["wait_target"]
    native.syscalls[7] = (0, 0x1005, 0x2FFFF, 1)
    invalid_known = probe.sample_once()["wait_target"] or {}
    check(
        "推定(speculative): HWND先頭引数と分かっていない呼出しでも、窓として実在する値なら宛先を残し(by=speculative)、窓でなければ残さない。既知の呼出しで窓でなければ valid=false",
        spec.get("by") == "speculative"
        and spec.get("image") == "ctfmon.exe"
        and none_spec is None
        and invalid_known.get("valid") is False
        and invalid_known.get("by") == "known-call",
        f"{spec} / {none_spec} / {invalid_known}",
    )

    probe, native, clock, phase = new_probe()
    native.syscalls.pop(7)
    row = probe.sample_once()
    check(
        "待機中でない(STATUS_UNSUCCESSFUL): sc_status に残し、syscall は空で、エラーにしない",
        row["sc_status"] == STATUS_UNSUCCESSFUL
        and row["syscall"] is None
        and not row["errors"]
        and probe.errors == [],
        str(row),
    )

    probe, native, clock, phase = new_probe()
    native.syscall_denied = {7}
    first_row = probe.sample_once()
    clock.advance(0.1)
    second_row = probe.sample_once()
    check(
        "スレッドを開けない(権限不足など): 1回だけエラーに記録し、以後は試さず、他の列は埋まる",
        first_row["errors"] == ["ThreadLastSystemCall"]
        and not second_row["errors"]
        and native.syscall_calls == 1
        and second_row["ctx_switches"] == 100
        and probe.summary()["syscall_probe"]["unavailable_threads"]
        == {7: "winerror=5"},
        f"{first_row['errors']} {second_row['errors']} calls={native.syscall_calls}",
    )

    probe, native, clock, phase = new_probe(syscalls=False)
    row = probe.sample_once()
    check(
        "syscalls=False: ThreadLastSystemCall を一度も呼ばず、列も空",
        native.syscall_calls == 0
        and row["syscall"] is None
        and row["wait_target"] is None,
    )

    probe, native, clock, phase = blocked_probe()
    for _ in range(60):
        probe.sample_once()
        clock.advance(0.1)
        native.ticks += 100
        native.other_ctx += 3
    snaps = probe.stall_snapshots
    marks = [x["mark_s"] for x in snaps]
    ui_entry = next((t for t in snaps[0]["threads"] if t["ui"]), {}) if snaps else {}
    other_entry = (
        next((t for t in snaps[0]["threads"] if not t["ui"]), {}) if snaps else {}
    )
    check(
        "UIのctx切替が1秒/5秒止まったら、全スレッドの最後のシステムコールを1回ずつ記録する(UIとそれ以外を区別)",
        marks == [1.0, 5.0]
        and ui_entry.get("syscall") == "NtUserMessageCall"
        and other_entry.get("syscall") == "NtWaitForSingleObject"
        and len(snaps[0]["threads"]) == 2
        and snaps[0]["windows"][0]["class"] == "TkTopLevel"
        and snaps[0]["windows"][0]["enabled"] is True
        and snaps[0]["hwnd_focus"] == 901,
        str(snaps)[:400],
    )
    episodes = find_stall_episodes(probe.rows)
    tags = [t["tag"] for t in episodes[0]["tags"]] if episodes else []
    wait = episodes[0]["wait"] if episodes else {}
    check(
        "無スケジュール区間に wait(種別=blocking-sendmessage・最後のシステムコール・宛先の文・他スレッドのctx増分)とタグが付く",
        len(episodes) == 1
        and wait.get("kind") == "blocking-sendmessage"
        and wait["syscalls"] == {"NtUserMessageCall": episodes[0]["aggregate"]["rows"]}
        and "ctfmon.exe" in wait["targets"][0]["text"]
        and "8" in (wait.get("others_ctx_delta") or {})
        and "A:blocking-sendmessage" in tags
        and "A:native-wait" in tags,
        f"{tags} {wait}",
    )
    summary_json = json.dumps(probe.summary(), ensure_ascii=False)
    check(
        "summary に syscall_probe(権限・番号表の由来・stall_snapshots・wait_targets_seen・syscall_counts)が入りJSON化できる",
        json.loads(summary_json)["syscall_probe"]["syscall_counts"]
        == {"NtUserMessageCall": 60}
        and json.loads(summary_json)["syscall_probe"]["wait_targets_seen"][0]["rows"]
        == 60
        and "0x48" in json.loads(summary_json)["syscall_probe"]["thread_access"],
    )

    tmp3 = Path(__file__).with_name("__diag_check_tmp3__")
    tmp3.mkdir(exist_ok=True)
    try:
        summary = probe.summary()
        summary["request_timeline"] = {"late": True}
        (tmp3 / "i.json").write_text(
            json.dumps(
                {
                    "row": "W02/preview@module",
                    "outcome": "answered",
                    "procedure_verdict": "clean",
                    "diagnostics": {
                        "run_index": 1,
                        "run_total": 2,
                        "induce": {"requested": True},
                    },
                    "induce_assessment": {
                        "induced": True,
                        "reasons": [],
                        "switcher_visible_s": 0.7,
                        "quiet_s": 20.1,
                    },
                    "harness_peer": {
                        "json": {"result": {"result": "expired", "elapsed": 15000}}
                    },
                    "ui_thread_diag": summary,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (tmp3 / "j.json").write_text(
            json.dumps(
                {
                    "row": "W02/preview@module",
                    "outcome": "answered",
                    "procedure_verdict": "clean",
                    "diagnostics": {"induce": {"requested": True}},
                    "induce_assessment": {
                        "induced": False,
                        "reasons": ["switcher-too-short"],
                    },
                    "harness_peer": {
                        "json": {"result": {"result": "expired", "elapsed": 9000}}
                    },
                    "ui_thread_diag": {"stall_episodes": []},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        report = summarize_sessions(tmp3)
        first = next(r for r in report["sessions"] if r["file"] == "i.json")
        check(
            "頻度の集計: 無スケジュール区間ごとの待ち先(種別・宛先)と、誘発手順の成立/不成立を回ごとに出し、誘発が成立した回だけを誘発の母数にする",
            first["stalls"][0]["wait"]["kind"] == "blocking-sendmessage"
            and "ctfmon.exe" in first["stalls"][0]["wait"]["targets"][0]["text"]
            and first["induced"] is True
            and report["induce_requested"] == 2
            and report["induced_clean"] == 1
            and report["peer_not_completed_or_late_among_induced"] == 1
            and report["peer_not_completed_or_late_among_clean"] == 2,
            str({k: v for k, v in report.items() if k != "sessions"}),
        )
    finally:
        for path in tmp3.glob("*"):
            path.unlink()
        tmp3.rmdir()

    # 外部見張りの有無で分けた集計(サイドカーから GetMessage 区間を数える)
    tmp4 = Path(__file__).with_name("__diag_check_tmp4__")
    tmp4.mkdir(exist_ok=True)
    try:
        import types

        def write_side(name, rows_):
            fake_probe = types.SimpleNamespace(
                table=lambda: {
                    "columns": [
                        "seq",
                        "t",
                        "tick_ms",
                        "phase",
                        "syscall",
                        "sc_wait_ms",
                        "wake_ok",
                    ],
                    "rows": [
                        [
                            r["seq"],
                            r["t"],
                            r["tick_ms"],
                            r["phase"],
                            r["syscall"],
                            r["sc_wait_ms"],
                            r["wake_ok"],
                        ]
                        for r in rows_
                    ],
                },
                target={},
                anchors=[],
                wm_null_log=[],
            )
            return write_samples_sidecar(tmp4 / name, fake_probe)

        def write_session(
            name, wake_ms, side, stalls, peer, extra_diag=None, wake=None
        ):
            if side and wake_ms is None:  # 見張りなしの回の行には投稿の累計が無い
                side = [dict(r, wake_ok=None) for r in side]
            info = write_side(f"{name}.ui-samples.jsonl", side) if side else None
            diag_ = {"stall_episodes": [{"aggregate": {"duration_s": 14.5}}] * stalls}
            if info:
                diag_["samples_file"] = info
            if wake:
                diag_["external_wake"] = wake
            (tmp4 / f"{name}.json").write_text(
                json.dumps(
                    {
                        "row": "W02/preview@module",
                        "outcome": "answered",
                        "procedure_verdict": "clean",
                        "diagnostics": {
                            "run_index": 1,
                            "run_total": 3,
                            "external_wake": wake_ms,
                            "syscall_probe": bool(side),
                            "induce": {"requested": True},
                            **(extra_diag or {}),
                        },
                        "induce_assessment": {"induced": True, "reasons": []},
                        "harness_peer": {
                            "json": {"result": {"result": peer, "elapsed": 90}}
                        },
                        "ui_thread_diag": diag_,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        write_session("a-off-stuck", None, stuck, 1, "expired")
        write_session("b-off-clean", None, healthy_gm, 0, "completed")
        write_session(
            "c-off-old", None, None, 0, "completed"
        )  # syscall 列なしの古い診断
        write_session(
            "d-on-healed",
            120,
            healed,
            0,
            "completed",
            wake={
                "posts_ok": 300,
                "posts_failed": 0,
                "refused": 0,
                "interval_ms": {"max": 141.2, "over_2x_period": 0},
            },
        )
        write_session(
            "e-on-clean",
            120,
            healthy_gm,
            0,
            "completed",
            wake={
                "posts_ok": 250,
                "posts_failed": 1,
                "refused": 0,
                "interval_ms": {"max": 160.0, "over_2x_period": 0},
                "health": {"healthy": False, "reasons": ["refused=1"]},
            },
        )
        # 投稿が流れている最中(wake_ok が増えている)に GetMessage 停止が起きた回 = 投稿しても解消しなかった停止
        write_session(
            "f-on-stuck-posting",
            120,
            stuck,
            1,
            "expired",
            wake={
                "posts_ok": 200,
                "posts_failed": 0,
                "refused": 0,
                "interval_ms": {"max": 130.0, "over_2x_period": 0},
                "health": {"healthy": True, "reasons": []},
            },
        )
        report = summarize_sessions(tmp4)
        g_off = report["groups"]["external_wake_off"]
        g_on = report["groups"]["external_wake_on"]
        check(
            "集計(見張りなし群): 3回(うち syscall 列ありは2回)。GetMessage 停止1件(最大6050ms)・ctx停止区間1件・二次起動の未完了1件",
            g_off["all"]["sessions"] == 3
            and g_off["all"]["getmessage_sessions"] == 2
            and g_off["all"]["getmessage_stalls"] == 1
            and g_off["all"]["max_getmessage_ms"] == 6050.0
            and g_off["all"]["max_getmessage_rows"] == 120
            and g_off["all"]["sessions_with_getmessage_stall"] == 1
            and g_off["all"]["ctx_stall_episodes"] == 1
            and g_off["all"]["longest_ctx_stall_s"] == 14.5
            and g_off["all"]["peer_not_completed_or_late"] == 1
            and "wake" not in g_off["all"],
            str(g_off["all"]),
        )
        check(
            "集計(見張りあり群): 3回・周期120ms。GetMessage 停止1件(投稿が流れている最中の停止)・見えた回2回・投稿 750件(失敗1)・最大間隔160ms・動作が期待どおりでない回は e-on-clean.json の1回",
            g_on["period_ms"] == [120]
            and g_on["all"]["sessions"] == 3
            and g_on["all"]["getmessage_stalls"] == 1
            and g_on["all"]["getmessage_stalls_while_posting"] == 1
            and g_on["all"]["sessions_with_getmessage_seen"] == 2
            and g_on["all"]["max_getmessage_ms"] == 6050.0
            and g_on["induced_clean"]["sessions"] == 3
            and g_on["all"]["wake"]["posts_ok"] == 750
            and g_on["all"]["wake"]["posts_failed"] == 1
            and g_on["all"]["wake"]["max_post_interval_ms"] == 160.0
            and g_on["all"]["wake"]["sessions_with_long_post_gap"] == 0
            and g_on["all"]["wake"]["unhealthy_sessions"] == ["e-on-clean.json"]
            and g_on["all"]["peer_not_completed_or_late"] == 1
            and g_off["all"]["getmessage_stalls_while_posting"] == 0,
            str(g_on),
        )
        json.dumps(report, ensure_ascii=False)
    finally:
        for path in tmp4.glob("*"):
            path.unlink()
        tmp4.rmdir()

    # tail と timeline
    tmp = Path(__file__).with_name("__diag_check_tmp__")
    tmp.mkdir(exist_ok=True)
    try:
        log = tmp / "stderr.log"
        log.write_bytes("".encode())
        tail = LogTail(log)
        check(
            "tail: ファイルが空/未作成でも例外にしない",
            tail.poll() == [] and LogTail(tmp / "none").poll() == [],
        )
        with log.open("ab") as handle:
            handle.write(
                "起動terminal: ab12 / expired / deadline=2000 / tick=12500\nDEBUG:x:起動terminal: ab12 / expired / deadline=2000 / tick=12500\n半".encode()
            )
        lines = tail.poll()
        check(
            "tail: 完結した行だけ返し、末尾の途中行は持ち越す",
            len(lines) == 2 and tail._carry != b"",
        )
        with log.open("ab") as handle:
            handle.write("端\n".encode())
        check("tail: 持ち越した行は次回に完結して返る", tail.poll() == ["半端"])

        probe, native, clock, phase = new_probe(tail_path=log)
        # 既に書かれた2行は同一イベントとして1件
        native.ticks = 12600
        probe.sample_once()
        terminals = [e for e in probe.log_events if e["kind"] == "terminal"]
        check(
            "生ログのterminalをリアルタイムに検出(DEBUG二重行は1件)、検出時のtickを残す",
            len(terminals) == 1
            and terminals[0]["seen_tick_ms"] == 12600
            and terminals[0]["tick_ms"] == 12500,
            str(probe.log_events),
        )
    finally:
        for path in tmp.glob("*"):
            path.unlink()
        tmp.rmdir()

    primary = "起動terminal: ab12 / expired / deadline=2000 / tick=12578\nDEBUG:pagefolio.startup_win32:起動terminal: ab12 / expired / deadline=2000 / tick=12578\n"
    peer = "前面化許可委譲: True / 0\n起動accepted: ab12 / deadline=2000\n起動連絡失敗: os_error=233\n"
    anchors = [
        {"tick_ms": 1000, "t": "2026-01-01T00:00:00+00:00", "mono": 0.0},
        {"tick_ms": 21000, "t": "2026-01-01T00:00:20.004+00:00", "mono": 20.0},
    ]
    timeline = build_request_timeline(
        primary,
        peer,
        anchors,
        live_events=[
            {
                "kind": "terminal",
                "id": "ab12",
                "tick_ms": 12578,
                "seen_t": "x",
                "seen_tick_ms": 12640,
            }
        ],
        peer_result={"result": "expired", "elapsed": 15078},
    )
    request = timeline["requests"][0]
    check(
        "timeline: 締切/導出した開始tick/一次の処理tick/遅れ(ms)",
        request["deadline_tick"] == 2000
        and request["request_started_tick_derived"] == -3000
        and request["primary_terminal_tick"] == 12578
        and request["primary_lateness_ms"] == 10578
        and request["primary_processed_before_deadline"] is False
        and request["peer_accepted_logged"] is True
        and timeline["peer_os_errors"] == [233]
        and timeline["late"] is True,
        str(request),
    )
    check(
        "timeline: tick→壁時計の換算(開始アンカー基準)とアンカー間のずれ",
        request["wall"]["primary_terminal"].startswith("2026-01-01T00:00:11.578")
        and timeline["tick_wall_drift_ms_between_anchors"] == 4.0,
        f"{request['wall']} drift={timeline['tick_wall_drift_ms_between_anchors']}",
    )
    check(
        "timeline: 生ログ検出時刻と記録tickの差(検出遅れ)",
        request["terminal_first_seen_by_driver"]["lag_ms_after_logged_tick"] == 62,
    )
    ok_timeline = build_request_timeline(
        "起動terminal: cd34 / completed / deadline=5000 / tick=1060\n",
        "起動accepted: cd34 / deadline=5000\n",
        anchors,
    )
    check(
        "timeline: 締切内に処理された要求は late=False",
        ok_timeline["late"] is False
        and ok_timeline["requests"][0]["primary_lateness_ms"] == -3940,
    )

    say("-- 判別(A〜D)の分類(合成の行) --")
    # 健全: ctxが毎0.1秒で+2、CPU微小
    healthy = make_rows(
        [
            (i * 0.1, 100 + i * 2, 1.0 + i * 0.1, 0, "Waiting", "WrUserRequest", False)
            for i in range(40)
        ]
    )
    check(
        "健全(ctx 20/s・CPU小)は無スケジュール区間なし・タグなし",
        find_stall_episodes(healthy) == []
        and classify_aggregate(aggregate_rows(healthy)) == [],
    )

    blocked = make_rows(
        [
            (i * 0.1, 500, 5.0, 0, "Waiting", "WrDelayExecution", i >= 50)
            for i in range(80)
        ]
    )
    episodes = find_stall_episodes(blocked)
    tags = [t["tag"] for t in episodes[0]["tags"]] if episodes else []
    check(
        "A: ctx停止・CPU進まず・Waiting = native-wait(WrDelayExecution・hung行も記録)",
        len(episodes) == 1
        and tags == ["A:native-wait"]
        and episodes[0]["aggregate"]["wait_reasons"] == {"WrDelayExecution": 80}
        and episodes[0]["aggregate"]["hung_rows"] == 30,
        str(episodes),
    )

    pumping = make_rows(
        [
            (i * 0.1, 100 + i * 3, 2.0 + i * 0.2, 0, "Waiting", "WrUserRequest", False)
            for i in range(100)
        ]
    )
    wm_ok = [
        {"tick_ms": r["tick_ms"], "result": "ok", "elapsed_ms": 0.2}
        for r in pumping[::5]
    ]
    agg = aggregate_rows(pumping, wm_ok)
    check(
        "B: 要求が遅れ、ctxは進みCPU小・WM_NULL応答あり = pumping-but-timer-silent",
        [t["tag"] for t in classify_aggregate(agg, request_late=True)]
        == ["B:pumping-but-timer-silent"]
        and classify_aggregate(agg, request_late=False) == [],
        str(classify_aggregate(agg, request_late=True)),
    )
    wm_bad = [
        {"tick_ms": r["tick_ms"], "result": "timeout", "elapsed_ms": 200.0}
        for r in pumping[::5]
    ]
    check(
        "B: WM_NULLが応答しなければBにしない",
        "B:pumping-but-timer-silent"
        not in [
            t["tag"]
            for t in classify_aggregate(
                aggregate_rows(pumping, wm_bad), request_late=True
            )
        ],
    )

    busy = make_rows(
        [
            (i * 0.1, 500 + (i % 2), 5.0 + i * 80.0, 0, "Running", "Executive", False)
            for i in range(40)
        ]
    )
    check(
        "C: CPU時間が区間の大半 = cpu-consumed",
        "C:cpu-consumed"
        in [t["tag"] for t in classify_aggregate(aggregate_rows(busy))],
        str(classify_aggregate(aggregate_rows(busy))),
    )

    modal = make_rows(
        [
            (
                i * 0.1,
                100 + i * 2,
                1.0,
                GUI_INMENUMODE | GUI_POPUPMENUMODE if 5 <= i < 35 else 0,
                "Waiting",
                "WrUserRequest",
                False,
            )
            for i in range(40)
        ]
    )
    tags = [t["tag"] for t in classify_aggregate(aggregate_rows(modal[5:35]))]
    starved = make_rows(
        [(i * 0.1, 500, 5.0, 0, "Waiting", "WrUserRequest", False) for i in range(40)]
    )
    for index, r in enumerate(starved):
        r["others_cpu_ms"] = 10.0 + index * 90.0
        r["busy_threads"] = 1
    starved_tags = [t["tag"] for t in classify_aggregate(aggregate_rows(starved))]
    check(
        "C(他スレッド): UIは起床せず他スレッドがCPUを使う区間 = other-thread-cpu(GIL待ち等の手掛かり)",
        starved_tags == ["C:other-thread-cpu", "A:native-wait"]
        or sorted(starved_tags) == ["A:native-wait", "C:other-thread-cpu"],
        str(starved_tags),
    )
    check(
        "D: メニュー/ポップアップflagの区間 = modal-loop",
        "D:modal-loop" in tags,
        str(tags),
    )
    check(
        "flagの復号(menu=4, popup=16, move-size=2)",
        decode_gui_flags(GUI_INMENUMODE | GUI_POPUPMENUMODE | GUI_INMOVESIZE)
        == ["in-move-size", "in-menu-mode", "popup-menu-mode"],
    )

    short = make_rows(
        [(i * 0.1, 500, 5.0, 0, "Waiting", "WrUserRequest", False) for i in range(8)]
    )
    check(
        "1秒未満のctx停止は無スケジュール区間にしない", find_stall_episodes(short) == []
    )

    # 要求窓の解析
    window_rows = make_rows(
        [
            (i * 0.1, 500, 5.0, 0, "Waiting", "WrDelayExecution", False)
            for i in range(160)
        ]
    )
    started = window_rows[10]["tick_ms"]
    terminal = window_rows[150]["tick_ms"]
    tl = {
        "requests": [
            {
                "request_id": "r1",
                "deadline_tick": started + 5000,
                "request_started_tick_derived": started,
                "primary_terminal_tick": terminal,
                "primary_lateness_ms": terminal - (started + 5000),
            }
        ]
    }
    analysis = analyze_request_window(window_rows, [], tl)
    check(
        "要求窓: 受理〜処理の区間で集計し、遅れていればタグ付け",
        analysis
        and analysis[0]["late"] is True
        and analysis[0]["tags"][0]["tag"] == "A:native-wait"
        and analysis[0]["rows_at"]["primary_terminal"]["tick_ms"] == terminal,
        str(analysis),
    )

    say("-- サイドカーの保存/読み込み --")
    tmpdir = Path(__file__).with_name("__diag_check_tmp2__")
    tmpdir.mkdir(exist_ok=True)
    try:
        probe, native, clock, phase = new_probe()
        probe.sample_once()
        clock.advance(0.1)
        native.ticks += 100
        probe.sample_once()
        probe.wm_null_log.append(
            {
                "t": "x",
                "tick_ms": 1100,
                "phase": "peer",
                "hwnd": 900,
                "result": "ok",
                "elapsed_ms": 0.1,
                "error": 0,
            }
        )
        info = write_samples_sidecar(tmpdir / "s.jsonl", probe)
        header, rows, wm = load_samples(tmpdir / "s.jsonl")
        check(
            "サイドカーが往復する(列/行数/wm_null/sha256)",
            header["columns"] == list(SAMPLE_COLUMNS)
            and len(rows) == 2
            and rows[1]["tick_ms"] == 1100
            and len(wm) == 1
            and info["rows"] == 2
            and info["sha256"] == file_sha256(tmpdir / "s.jsonl"),
            str(info),
        )
        try:
            json.dumps(probe.summary(), ensure_ascii=False)
            serial = True
        except TypeError:
            serial = False
        check("summaryがJSON化できる", serial)
        session = {
            "row": "W02/preview@module",
            "started_at": "x",
            "outcome": "answered",
            "procedure_verdict": "clean",
            "diagnostics": {"run_index": 1, "run_total": 2},
            "harness_peer": {
                "json": {"result": {"result": "expired", "elapsed": 15078}}
            },
            "ui_thread_diag": {**probe.summary(), "request_timeline": {"late": True}},
        }
        (tmpdir / "a.json").write_text(
            json.dumps(session, ensure_ascii=False), encoding="utf-8"
        )
        session2 = {
            **session,
            "harness_peer": {
                "json": {"result": {"result": "completed", "elapsed": 63}}
            },
            "ui_thread_diag": {**probe.summary(), "request_timeline": {"late": False}},
        }
        (tmpdir / "b.json").write_text(
            json.dumps(session2, ensure_ascii=False), encoding="utf-8"
        )
        report = summarize_sessions(tmpdir)
        check(
            "頻度の集計: clean回のうちpeerが完了しなかった/遅れた回数",
            report["total"] == 2
            and report["clean_procedure"] == 2
            and report["peer_not_completed_or_late_among_clean"] == 1,
            str(report),
        )
    finally:
        for path in tmpdir.glob("*"):
            path.unlink()
        tmpdir.rmdir()

    return failures


# ---------------------------------------------------------------------------
# 実機の機構確認: 自分で起動した使い捨てのTclプロセスを観測する
# ---------------------------------------------------------------------------
# 使い捨てプロセスは Tk の窓を作らない(Tk の窓は作成だけで前景を奪うことを実測したため)。
# Tcl の通知器(after / vwait)は製品と同じ機構で、非表示の STATIC 窓を1つ作ってUIスレッド特定と
# SendMessageTimeoutW(WM_NULL) の宛先に使う(非表示窓は前景にならない)。
# 場面: idle(健全) → blocked-sleep(afterコールバック内で time.sleep 6秒) → cpu-busy(1.5秒のCPU消費)
#       → modal-popup(Win32ポップアップメニューのモーダルループ。画面外座標に出す)
#       → native-wait-event(WaitForSingleObjectでメッセージを捌かずに待つ)
#       → other-thread-busy(UIスレッドは待ち、別スレッドが1.5秒CPUを使う) → memory-touch(64MBに触れる)
TARGET_SCRIPT = r"""
import ctypes as ct, json, os, sys, threading, time, tkinter as tk
from ctypes import wintypes as wt
tmp, mode = sys.argv[1], sys.argv[2]
u = ct.WinDLL("user32", use_last_error=True)
k = ct.WinDLL("kernel32", use_last_error=True)
k.GetTickCount64.restype = ct.c_ulonglong
k.GetCurrentThreadId.restype = wt.DWORD
k.CreateEventW.restype = wt.HANDLE
k.CreateEventW.argtypes = [ct.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
k.WaitForSingleObject.restype = wt.DWORD
k.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
u.CreateWindowExW.restype = wt.HWND
u.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ct.c_int, ct.c_int, ct.c_int, ct.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
u.CreatePopupMenu.restype = wt.HMENU
u.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ct.c_size_t, wt.LPCWSTR]
u.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ct.c_int, ct.c_int, ct.c_int, wt.HWND, ct.c_void_p]
u.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
interp = tk.Tcl()
hwnd = u.CreateWindowExW(0, "STATIC", "pf-diag-target", 0, -30000, 0, 100, 100, None, None, None, None)
interp.setvar("done", "")
timeline = []
keep = []
def tick():
    return int(k.GetTickCount64())
def beat():
    interp.call("after", 50, beat_name)
beat_name = interp.register(beat)
def sc_blocked():
    time.sleep(6.0)
def sc_cpu():
    end = time.perf_counter() + 1.5
    n = 0
    while time.perf_counter() < end:
        n += 1
def sc_popup():
    menu = u.CreatePopupMenu()
    u.AppendMenuW(menu, 0, 1, "x")
    def close_menu():
        u.PostMessageW(hwnd, 0x1E, 0, 0)
        u.PostMessageW(hwnd, 0x100, 0x1B, 0)
        u.PostMessageW(hwnd, 0x101, 0x1B, 0)
    threading.Timer(1.2, close_menu).start()
    u.TrackPopupMenu(menu, 0x100 | 0x80, -30000, 0, 0, hwnd, None)
def sc_wait():
    event = k.CreateEventW(None, True, False, None)
    k.WaitForSingleObject(event, 1500)
def sc_other():
    def burn():
        end = time.perf_counter() + 1.5
        while time.perf_counter() < end:
            pass
    worker = threading.Thread(target=burn)
    worker.start()
    time.sleep(1.5)
    worker.join()
def sc_mem():
    block = bytearray(64 * 1024 * 1024)
    for i in range(0, len(block), 4096):
        block[i] = 1
    keep.append(block)
if mode == "idle":
    scenarios = []
else:
    scenarios = [("blocked-sleep", sc_blocked), ("cpu-busy", sc_cpu), ("modal-popup", sc_popup), ("native-wait-event", sc_wait), ("other-thread-busy", sc_other), ("memory-touch", sc_mem)]
state = {"i": 0}
def step():
    if state["i"] >= len(scenarios):
        timeline.append({"name": "end", "start_tick": tick(), "end_tick": tick()})
        with open(os.path.join(tmp, "timeline.json"), "w", encoding="utf-8") as f:
            json.dump({"timeline": timeline, "main_tid": int(k.GetCurrentThreadId()), "hwnd": int(hwnd or 0)}, f)
        interp.setvar("done", "1")
        return
    name, fn = scenarios[state["i"]]
    state["i"] += 1
    start = tick()
    fn()
    end = tick()
    timeline.append({"name": name, "start_tick": start, "end_tick": end})
    if name == "blocked-sleep":
        sys.stderr.write("DEBUG:target:terminal: " + "ab" * 16 + " / expired / deadline=%d / tick=%d\n" % (start + 100, end))
        sys.stderr.flush()
    interp.call("after", 1500, step_name)
step_name = interp.register(step)
def wait_go():
    if os.path.exists(os.path.join(tmp, "go")):
        timeline.append({"name": "go", "start_tick": tick(), "end_tick": tick()})
        interp.call("after", 1500, step_name)
    else:
        interp.call("after", 20, wait_name)
wait_name = interp.register(wait_go)
interp.call("after", 50, beat_name)
interp.call("after", 20, wait_name)
with open(os.path.join(tmp, "ready.json"), "w", encoding="utf-8") as f:
    json.dump({"pid": os.getpid(), "main_tid": int(k.GetCurrentThreadId()), "hwnd": int(hwnd or 0)}, f)
interp.call("vwait", "done")
"""


# 待ち先の連鎖の確認用: 使い捨てプロセス3つ(窓はすべて非表示のトップレベルSTATIC/自作クラス。前景は変えない)。
#   A: 観測対象(PageFolioの代役)。非表示窓を1つ作り、go が出たら B の窓へ SendMessage して戻らない。
#   B: 自作窓クラスの窓を持ち、メッセージを捌くが、A のメッセージ(0x0407)を受けた窓プロシージャの中で
#      C の窓へ SendMessage して戻らない(=Bのスレッドも NtUserMessageCall で待つ)。
#   C: 非表示窓を作って、メッセージを捌かずに眠る。
CHAIN_SCRIPT = r"""
import ctypes as ct, json, os, sys, time
from ctypes import wintypes as wt
role, tmp = sys.argv[1], sys.argv[2]
u = ct.WinDLL("user32", use_last_error=True)
k = ct.WinDLL("kernel32", use_last_error=True)
k.GetCurrentThreadId.restype = wt.DWORD
u.CreateWindowExW.restype = wt.HWND
u.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ct.c_int, ct.c_int, ct.c_int, ct.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
u.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u.SendMessageW.restype = ct.c_ssize_t
u.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u.DefWindowProcW.restype = ct.c_ssize_t
def path(name):
    return os.path.join(tmp, name)
def ready(hwnd):
    with open(path(role + ".tmp"), "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "tid": int(k.GetCurrentThreadId()), "hwnd": int(hwnd or 0)}, f)
    os.replace(path(role + ".tmp"), path(role + ".json"))
def wait_for(name):
    while not os.path.exists(path(name)):
        time.sleep(0.05)
def read(name):
    wait_for(name)
    with open(path(name), encoding="utf-8") as f:
        return json.load(f)
if role == "C":
    hwnd = u.CreateWindowExW(0, "STATIC", "pf-chain-C", 0, -30000, 0, 50, 50, None, None, None, None)
    ready(hwnd)
    time.sleep(300)
elif role == "B":
    WNDPROC = ct.WINFUNCTYPE(ct.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
    class WNDCLASSW(ct.Structure):
        _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ct.c_int), ("cbWndExtra", ct.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HANDLE), ("hCursor", wt.HANDLE), ("hbrBackground", wt.HANDLE), ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]
    target = {}
    def proc(hwnd, msg, wparam, lparam):
        if msg == 0x0407:
            u.SendMessageW(target["hwnd"], 0x0409, 0, 0)
            return 0
        return u.DefWindowProcW(hwnd, msg, wparam, lparam)
    callback = WNDPROC(proc)
    wc = WNDCLASSW()
    wc.lpfnWndProc = callback
    wc.lpszClassName = "PfChainB"
    u.RegisterClassW.argtypes = [ct.POINTER(WNDCLASSW)]
    assert u.RegisterClassW(ct.byref(wc))
    hwnd = u.CreateWindowExW(0, "PfChainB", "pf-chain-B", 0, -30000, 0, 50, 50, None, None, None, None)
    target["hwnd"] = read("C.json")["hwnd"]
    ready(hwnd)
    msg = wt.MSG()
    while u.GetMessageW(ct.byref(msg), None, 0, 0) > 0:
        u.DispatchMessageW(ct.byref(msg))
elif role == "A":
    hwnd = u.CreateWindowExW(0, "STATIC", "pf-chain-A", 0, -30000, 0, 50, 50, None, None, None, None)
    ready(hwnd)
    wait_for("go")
    u.SendMessageW(read("B.json")["hwnd"], 0x0407, 0, 0)
"""


def _live_chain(say, check):
    """使い捨てプロセス A -> B -> C のブロッキング SendMessage の連鎖を、実APIで解決できるか確認する。"""
    import subprocess
    import sys
    import tempfile

    say(
        "-- 実API(使い捨てプロセス A -> B -> C のブロッキング SendMessage 連鎖・約6秒) --"
    )
    procs = {}
    info = {}
    with tempfile.TemporaryDirectory(prefix="pf-diag-chain-") as tmp:
        try:
            for role in "CBA":
                procs[role] = subprocess.Popen(  # noqa: S603
                    [sys.executable, "-I", "-c", CHAIN_SCRIPT, role, tmp],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                ready = Path(tmp) / f"{role}.json"
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and not ready.exists():
                    if procs[role].poll() is not None:
                        break
                    time.sleep(0.05)
                if not ready.exists():
                    check(f"使い捨てプロセス {role} が起動して準備完了になる", False)
                    return
                info[role] = json.loads(ready.read_text(encoding="utf-8"))
            native = Win32Native()
            probe = UiThreadProbe(
                native,
                info["A"]["pid"],
                interval=0.1,
                phase_fn=lambda: "peer",
                stall_snap_marks=(1.0,),
            )
            probe.start()
            time.sleep(0.8)
            go_mono = time.monotonic()
            (Path(tmp) / "go").write_text("go", encoding="utf-8")
            time.sleep(3.6)
            probe.stop()
            rows = [r for r in probe.rows if not r.get("gone")]
            before = [r for r in rows if r["elapsed_s"] < 0.7]
            blocked = [r for r in rows if r.get("syscall") == "NtUserMessageCall"]
            last = blocked[-1] if blocked else {}
            target = last.get("wait_target") or {}
            nxt = target.get("next") or {}
            check(
                "A: go の前は NtUserMessageCall ではなく、go の後に NtUserMessageCall の待機が10行以上ある",
                bool(before)
                and all(r.get("syscall") != "NtUserMessageCall" for r in before)
                and len(blocked) >= 10,
                f"before={[r.get('syscall') for r in before[:3]]} blocked={len(blocked)}",
            )
            check(
                "A: 第1引数 = B の窓ハンドル(ブロック中の SendMessage の宛先)",
                bool(blocked)
                and all(r["sc_arg"] == info["B"]["hwnd"] for r in blocked),
                f"args={sorted({r['sc_arg'] for r in blocked})} B={info['B']['hwnd']}",
            )
            check(
                "宛先1段目(B): 所有 pid/tid・クラス・タイトル・イメージ名・スレッド状態(Waiting/WrUserRequest)が実機で解決される",
                target.get("valid") is True
                and target.get("pid") == info["B"]["pid"]
                and target.get("tid") == info["B"]["tid"]
                and target.get("class") == "PfChainB"
                and target.get("title") == "pf-chain-B"
                and str(target.get("image") or "").lower() == "python.exe"
                and target.get("same_process") is False
                and (target.get("thread") or {}).get("state") == "Waiting"
                and (target.get("thread") or {}).get("wait_reason") == "WrUserRequest",
                str(target),
            )
            check(
                "連鎖: B のスレッドも NtUserMessageCall で待ち、その第1引数 = C の窓ハンドル",
                (target.get("thread_syscall") or {}).get("name") == "NtUserMessageCall"
                and (target.get("thread_syscall") or {}).get("arg")
                == info["C"]["hwnd"],
                str(target.get("thread_syscall")),
            )
            check(
                "宛先2段目(C): 所有 pid/tid・タイトルが解決され、C のスレッドは眠って(NtWait*)終点になる。C はメッセージを捌かないのに窓の情報は取れる",
                nxt.get("valid") is True
                and nxt.get("pid") == info["C"]["pid"]
                and nxt.get("tid") == info["C"]["tid"]
                and nxt.get("title") == "pf-chain-C"
                and str(nxt.get("class")).lower() == "static"
                and str((nxt.get("thread_syscall") or {}).get("name")).startswith(
                    "NtWait"
                )
                and "next" not in nxt,
                str(nxt),
            )
            elapsed_after_go = (last.get("elapsed_s") or 0) - (go_mono - probe._t0)
            wait_s = (last.get("sc_wait_ms") or 0) / 1000
            check(
                "待機の長さ(ThreadLastSystemCall の WaitTime は100ns単位)が実時間と合う",
                bool(blocked)
                and 0.5 * elapsed_after_go <= wait_s <= elapsed_after_go + 0.15,
                f"wait_s={wait_s} elapsed_after_go={elapsed_after_go}",
            )
            snap = probe.stall_snapshots[0] if probe.stall_snapshots else {}
            ui_entry = next((t for t in snap.get("threads", []) if t.get("ui")), {})
            check(
                "UIスレッドが1秒止まった時点の全スレッド スナップショット(各スレッドの最後のシステムコール)が残る",
                ui_entry.get("syscall") == "NtUserMessageCall"
                and ui_entry.get("arg") == info["B"]["hwnd"]
                and len(snap.get("threads", [])) >= 1
                and any(
                    w.get("title") == "pf-chain-A" and w.get("enabled") is True
                    for w in snap.get("windows") or []
                ),
                str(snap)[:300],
            )
            summary = probe.summary()
            episodes = summary["stall_episodes"]
            wait = (episodes[0]["wait"] if episodes else None) or {}
            wait_text = " ".join(t["text"] for t in wait.get("targets", []))
            check(
                "無スケジュール区間の wait: 種別=blocking-sendmessage、宛先に pf-chain-B と pf-chain-C の両方が入る",
                wait.get("kind") == "blocking-sendmessage"
                and "pf-chain-B" in wait_text
                and "pf-chain-C" in wait_text
                and "A:blocking-sendmessage" in [t["tag"] for t in episodes[0]["tags"]],
                str(wait)[:300],
            )
            check(
                "サンプラは宛先が応答しなくてもブロックしない(1サンプルの最大コスト<250ms)",
                (summary["cost_ms"]["max"] or 0) < 250 and summary["max_gap_s"] < 0.5,
                f"{summary['cost_ms']} max_gap_s={summary['max_gap_s']}",
            )
            allowed = {("process", 0x1000), ("thread", 0x800), ("thread-syscall", 0x48)}
            check(
                "開いた権限は PROCESS_QUERY_LIMITED / THREAD_QUERY_LIMITED / 0x48(THREAD_QUERY_INFORMATION|THREAD_GET_CONTEXT)だけ",
                set(native.open_log) <= allowed
                and ("thread-syscall", 0x48) in set(native.open_log),
                str(sorted(set(native.open_log))),
            )
            check(
                "APIエラーなし・ThreadLastSystemCall を開けなかったスレッドなし",
                not probe.errors
                and not summary["syscall_probe"]["unavailable_threads"],
                f"errors={probe.errors} unavailable={summary['syscall_probe']['unavailable_threads']}",
            )
            say(
                f"     (参考) A の待ち先: {format_wait_target(target)}"
                f" / 待機 {last.get('sc_wait_ms')}ms / 行のコスト {summary['cost_ms']}"
            )
        finally:
            for proc in procs.values():
                proc.kill()
            for proc in procs.values():
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
            check(
                "後始末: 使い捨てプロセスをすべて終了させた",
                all(proc.poll() is not None for proc in procs.values()),
            )


# 幽霊メッセージの再現用の使い捨てプロセス(Tclのみ。Tkの窓は作らない。非表示の窓を1つ持つだけで前景は変えない)。
# 製品の停止の機構(Tcl通知器の「PeekMessage(PM_NOREMOVE)が真 -> GetMessageW が空で無期限に眠る」)を、同じスレッドの
# WH_GETMESSAGE フックで人工的に作る: 親が投稿した餌メッセージ(WM_APP+7)を、Tclの PeekMessage が選んだ直後に
# フックが PeekMessage(PM_REMOVE) で取り除くので、直後の GetMessageW は何も見つけられずブロックする。
# 心拍: Tcl の after 50 で hb.txt に clock milliseconds を書く(止まれば after の連鎖が止まっている印)。
GHOST_SCRIPT = r"""
import ctypes, ctypes.wintypes as wt, json, os, sys, threading, time, tkinter
tmp = sys.argv[1]
u = ctypes.WinDLL("user32", use_last_error=True)
k = ctypes.WinDLL("kernel32", use_last_error=True)
BAIT = 0x8000 + 7
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HANDLE), ("hIcon", wt.HANDLE), ("hCursor", wt.HANDLE), ("hbrBackground", wt.HANDLE), ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]
u.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u.DefWindowProcW.restype = LRESULT
u.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
u.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
u.CreateWindowExW.restype = wt.HWND
u.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
u.SetWindowsHookExW.restype = wt.HHOOK
u.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
u.CallNextHookEx.restype = LRESULT
u.PeekMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]
u.PeekMessageW.restype = wt.BOOL
k.GetCurrentThreadId.restype = wt.DWORD
k.GetModuleHandleW.restype = wt.HMODULE
counts = {"ghosted": 0, "bait_seen": 0}
busy = {"v": False}
holder = {}
@WNDPROC
def wndproc(hwnd, msg, wparam, lparam):
    return u.DefWindowProcW(hwnd, msg, wparam, lparam)
@HOOKPROC
def hookproc(code, wparam, lparam):
    try:
        if code >= 0 and not busy["v"]:
            msg = wt.MSG.from_address(lparam)
            if msg.message == BAIT:
                counts["bait_seen"] += 1
                if wparam == 0:
                    busy["v"] = True
                    try:
                        other = wt.MSG()
                        if u.PeekMessageW(ctypes.byref(other), None, BAIT, BAIT, 1):
                            counts["ghosted"] += 1
                    finally:
                        busy["v"] = False
    except Exception:
        pass
    return u.CallNextHookEx(holder.get("h"), code, wparam, lparam)
hinst = k.GetModuleHandleW(None)
cls = WNDCLASSW()
cls.lpfnWndProc = wndproc
cls.hInstance = hinst
cls.lpszClassName = "PfGhostWnd"
u.RegisterClassW(ctypes.byref(cls))
hwnd = u.CreateWindowExW(0, "PfGhostWnd", "pf-ghost", 0x80000000, 0, 0, 10, 10, None, None, hinst, None)
tid = k.GetCurrentThreadId()
holder["h"] = u.SetWindowsHookExW(3, hookproc, None, tid)
tcl = tkinter.Tcl()
def dump():
    while True:
        time.sleep(0.2)
        try:
            with open(os.path.join(tmp, "counts.json"), "w", encoding="utf-8") as f:
                json.dump(counts, f)
        except Exception:
            pass
threading.Thread(target=dump, daemon=True).start()
with open(os.path.join(tmp, "ready.tmp"), "w", encoding="utf-8") as f:
    json.dump({"pid": os.getpid(), "tid": int(tid), "hwnd": int(hwnd or 0)}, f)
os.replace(os.path.join(tmp, "ready.tmp"), os.path.join(tmp, "ready.json"))
tcl.setvar("hbpath", os.path.join(tmp, "hb.txt"))
tcl.eval("set fh [open $hbpath w]; proc beat {} {global fh; puts $fh [clock milliseconds]; flush $fh; after 50 beat}; after 50 beat; vwait forever")
"""


def _beat_times(path):
    out = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.split("\n")[:-1]:  # 末尾の書きかけの行は読まない
        try:
            out.append(int(line))
        except ValueError:
            pass
    return out


def _max_beat_gap(beats, lo, hi):
    """[lo, hi](epoch ms)の間の心拍の最大の空き(lo からの最初の心拍までと、最後の心拍から hi までを含む)。"""
    inside = [b for b in beats if lo <= b <= hi]
    points = [lo, *inside, hi]
    return max(b - a for a, b in zip(points, points[1:], strict=False))


def _live_ghost(say, check):
    """使い捨てTclプロセスに幽霊メッセージを起こし、別プロセスの外部見張り(PostThreadMessageW)が1周期内に解消することを確かめる。

    見張りなし: 幽霊で GetMessage に居続け、心拍が止まる(手動の WM_NULL 投稿で復帰する)。
    見張りあり(周期120ms): 同じ幽霊が3回起きても、心拍の空きは周期程度に収まり、GetMessage 区間は停止(>=400ms)にならない。
    宛先の確認(別プロセスのスレッド・作成時刻違い・窓の持ち主違い)の拒否も実APIで確かめる。
    """
    import contextlib
    import shutil
    import subprocess
    import sys
    import tempfile

    say(
        "-- 実API(使い捨てTclプロセス + 幽霊メッセージ。別プロセスの外部見張りが1周期内に解消するか・約15秒) --"
    )
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.PostThreadMessageW.restype = wt.BOOL
    user32.GetDesktopWindow.restype = wt.HWND
    bait = 0x8000 + 7
    procs = []

    def start_child(tmp):
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-I", "-c", GHOST_SCRIPT, str(tmp)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        procs.append(proc)
        ready = Path(tmp) / "ready.json"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not ready.exists():
            if proc.poll() is not None:
                return None
            time.sleep(0.05)
        if not ready.exists():
            return None
        info = json.loads(ready.read_text(encoding="utf-8"))
        time.sleep(0.3)
        return info

    def counts_of(tmp):
        try:
            return json.loads((Path(tmp) / "counts.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def identity_of(pid):
        native_id = Win32Native()
        try:
            return native_id.open_target(pid)["created"]
        finally:
            native_id.close()

    @contextlib.contextmanager
    def ghost_dir(prefix):
        """作業ディレクトリ。抜けるときに、その中で起動した子プロセスを先に終了させる(開いたファイルを残さない)。"""
        with tempfile.TemporaryDirectory(
            prefix=prefix, ignore_cleanup_errors=True
        ) as directory:
            first = len(procs)
            try:
                yield directory
            finally:
                for proc in procs[first:]:
                    proc.kill()
                for proc in procs[first:]:
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        pass
                # 終了直後はファイルハンドルの解放が少し遅れることがある。短く繰り返して消す(消えなくても検査は失敗にしない)。
                for _ in range(30):
                    try:
                        shutil.rmtree(directory)
                        break
                    except FileNotFoundError:
                        break
                    except OSError:
                        time.sleep(0.1)

    try:
        # --- 見張りなし(基準): 幽霊で止まり、手動の投稿メッセージで復帰する ---
        with ghost_dir("pf-diag-ghost-off-") as tmp:
            info = start_child(tmp)
            check(
                "幽霊の使い捨てプロセス(見張りなし)が起動して準備完了になる",
                info is not None,
            )
            if info is None:
                return
            native = Win32Native()
            phase = {"v": "baseline"}
            probe = UiThreadProbe(
                native,
                info["pid"],
                expected_created=identity_of(info["pid"]),
                interval=0.05,
                phase_fn=lambda: phase["v"],
            )
            probe.start()
            time.sleep(1.0)
            phase["v"] = "ghost"
            bait_ms = time.time() * 1000
            user32.PostThreadMessageW(info["tid"], bait, 0, 0)
            time.sleep(2.8)
            release_ms = time.time() * 1000
            phase["v"] = "released"
            user32.PostThreadMessageW(
                info["tid"], 0, 0, 0
            )  # 手動の WM_NULL(復帰の確認)
            time.sleep(1.0)
            probe.stop()
            time.sleep(0.3)
            beats = _beat_times(Path(tmp) / "hb.txt")
            ghost_gap = _max_beat_gap(beats, bait_ms, release_ms - 100)
            after_release = [b for b in beats if release_ms <= b <= release_ms + 600]
            summary = probe.summary()
            gm = summary["getmessage"]
            check(
                "見張りなし: 幽霊が起き(餌がフックに取り除かれ)、Tclの心拍が2秒以上止まり、GetMessage に2秒以上居続ける",
                counts_of(tmp).get("ghosted", 0) >= 1
                and ghost_gap >= 2000
                and gm["stalls"] >= 1
                and gm["max_length_ms"] >= 2000,
                f"counts={counts_of(tmp)} ghost_gap={ghost_gap} gm={ {k: gm[k] for k in ('runs', 'rows', 'stalls', 'max_length_ms')} }",
            )
            check(
                "見張りなし: 手動の投稿(WM_NULL)で心拍が再開する(投稿メッセージで復帰する性質)",
                len(after_release) >= 3,
                f"beats_after_release={len(after_release)}",
            )
            check(
                "見張りなし: 見張りは作られず、投稿を1回も呼ばない",
                probe.wake_log is None
                and native.post_calls == 0
                and summary["external_wake"] is None,
            )
            say(
                f"     (参考) 見張りなし: 心拍の最大の空き={ghost_gap:.0f}ms GetMessage={ {k: gm[k] for k in ('runs', 'rows', 'stalls', 'max_length_ms')} }"
            )

        # --- 見張りあり(別プロセス・120ms): 同じ幽霊が3回起きても1周期程度で解消する ---
        with ghost_dir("pf-diag-ghost-on-") as tmp:
            info = start_child(tmp)
            check(
                "幽霊の使い捨てプロセス(見張りあり)が起動して準備完了になる",
                info is not None,
            )
            if info is None:
                return
            created = identity_of(info["pid"])
            native = Win32Native()
            phase = {"v": "baseline"}
            probe = UiThreadProbe(
                native,
                info["pid"],
                expected_created=created,
                interval=0.05,
                phase_fn=lambda: phase["v"],
                external_wake_ms=120,
            )
            probe.start()
            time.sleep(1.0)
            windows = []
            for index in range(3):
                phase["v"] = f"ghost-{index + 1}"
                start_ms = time.time() * 1000
                user32.PostThreadMessageW(info["tid"], bait, 0, 0)
                time.sleep(1.2)
                windows.append((start_ms, start_ms + 1000))
            phase["v"] = "done"
            ui = dict(probe._ui or {})
            foreign_tid = threading.get_native_id()
            gate_ok = native.verify_post_target(ui.get("tid"), ui.get("hwnd"), created)
            gate_foreign = native.verify_post_target(foreign_tid, None, created)
            gate_created = native.verify_post_target(
                ui.get("tid"), ui.get("hwnd"), created + 1
            )
            gate_window = native.verify_post_target(
                ui.get("tid"), int(user32.GetDesktopWindow() or 0), created
            )
            posts_before_stop = native.post_calls
            probe.stop()
            time.sleep(0.3)
            beats = _beat_times(Path(tmp) / "hb.txt")
            gaps = [_max_beat_gap(beats, lo, hi) for lo, hi in windows]
            summary = probe.summary()
            gm = summary["getmessage"]
            wake = summary["external_wake"]
            ghosted = counts_of(tmp).get("ghosted", 0)
            check(
                "見張りあり(別プロセスの投稿): 幽霊が3回起きても(フックが餌を取り除いた回数=3)、Tclの心拍の空きは各回500ms以内に収まる(見張りなしは2秒以上)",
                ghosted == 3
                and all(g <= 500 for g in gaps)
                and info["pid"] != os.getpid(),
                f"ghosted={ghosted} gaps={gaps}",
            )
            check(
                "見張りあり: GetMessage に居続けた停止(>=400ms)は0件で、見えた GetMessage 区間も短い(最大400ms未満)",
                gm["stalls"] == 0 and gm["max_length_ms"] < GETMESSAGE_STALL_MS,
                str({k: gm[k] for k in ("runs", "rows", "stalls", "max_length_ms")}),
            )
            check(
                "見張りあり: 約6秒で30回以上投稿し、失敗0・拒否0・投稿の最大間隔は周期の4倍(480ms)未満。投稿は成功+失敗の件数と一致(余計な投稿なし)",
                wake["posts_ok"] >= 30
                and wake["posts_failed"] == 0
                and wake["refused"] == 0
                and (wake["interval_ms"]["max"] or 0) < 480
                and wake["health"]["healthy"] is True
                and native.post_calls == wake["posts_ok"] + wake["posts_failed"]
                and posts_before_stop <= native.post_calls,
                str(
                    {
                        k: wake[k]
                        for k in (
                            "posts_ok",
                            "posts_failed",
                            "refused",
                            "interval_ms",
                            "by_phase",
                        )
                    }
                ),
            )
            check(
                "宛先の確認(実API): 正しい tid/窓/作成時刻は通り、別プロセスのスレッド・作成時刻違い・窓の持ち主違い(デスクトップ窓)は拒否される",
                gate_ok.get("ok") is True
                and gate_foreign.get("ok") is False
                and gate_foreign.get("reason") == "thread-not-in-target-process"
                and gate_created.get("ok") is False
                and gate_created.get("reason") == "process-creation-time-mismatch"
                and gate_window.get("ok") is False
                and gate_window.get("reason") == "window-owner-mismatch",
                str((gate_ok, gate_foreign, gate_created, gate_window)),
            )
            allowed = {("process", 0x1000), ("thread", 0x800), ("thread-syscall", 0x48)}
            check(
                "見張りありでも開いた権限は PROCESS_QUERY_LIMITED / THREAD_QUERY_LIMITED / 0x48 だけ・APIエラーなし",
                set(native.open_log) <= allowed and not probe.errors,
                f"{sorted(set(native.open_log))} errors={probe.errors}",
            )
            say(
                f"     (参考) 見張りあり(120ms): 心拍の最大の空き={[round(g) for g in gaps]}ms "
                f"GetMessage={ {k: gm[k] for k in ('runs', 'rows', 'stalls', 'max_length_ms')} } "
                f"投稿={wake['posts_ok']}回 間隔={wake['interval_ms']}"
            )
    finally:
        for proc in procs:
            proc.kill()
        for proc in procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        check(
            "後始末: 幽霊の使い捨てプロセスをすべて終了させた",
            all(proc.poll() is not None for proc in procs),
        )


def _parse_iso(text):
    return datetime.fromisoformat(text)


def _window_rows(rows, start_tick, end_tick, trim_ms=300):
    lo, hi = start_tick + trim_ms, end_tick - trim_ms
    return [
        r for r in rows if r.get("tick_ms") is not None and lo <= r["tick_ms"] <= hi
    ]


def check_live(say=print):
    """使い捨てTclプロセス(自分で起動・Tkの窓なし)を実APIで観測して、サンプラを確認する。

    約45秒かかる(Tcl場面20秒 + ブロッキングSendMessage連鎖6秒 + 幽霊メッセージ/外部見張り15秒ほか)。
    前景は変えない(前後でGetForegroundWindowを比較する)。
    """
    import subprocess
    import sys
    import tempfile

    failures = []

    def check(name, condition, detail=""):
        say(
            f"  [{'ok' if condition else 'FAIL'}] {name}"
            + (f" ... {detail}" if detail and not condition else "")
        )
        if not condition:
            failures.append(name)

    user32 = ctypes.WinDLL("user32")
    user32.GetForegroundWindow.restype = wt.HWND
    fg_before = int(user32.GetForegroundWindow() or 0)

    def spawn(tmp, mode):
        err = (Path(tmp) / "stderr.log").open("w", encoding="utf-8")
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-I", "-c", TARGET_SCRIPT, str(tmp), mode],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        deadline = time.monotonic() + 20
        ready = Path(tmp) / "ready.json"
        while time.monotonic() < deadline and not ready.exists():
            if proc.poll() is not None:
                break
            time.sleep(0.05)
        if not ready.exists() or not ready.read_text(encoding="utf-8").strip():
            proc.kill()
            err.close()
            return None, None, err
        time.sleep(0.1)
        return proc, json.loads(ready.read_text(encoding="utf-8")), err

    say("-- 実API(使い捨てTclプロセス・WM_NULL ON・約20秒) --")
    with tempfile.TemporaryDirectory(prefix="pf-diag-live-") as tmp:
        proc, ready, err = spawn(tmp, "full")
        if proc is None:
            check("使い捨てTclプロセスを起動できる", False, "ready.json が出ない")
            return failures
        native = Win32Native()
        probe = UiThreadProbe(
            native,
            ready["pid"],
            interval=0.1,
            wm_null=True,
            wm_null_interval=0.25,
            wm_null_timeout_ms=200,
            tail_path=Path(tmp) / "stderr.log",
            phase_fn=lambda: "awaiting-enter",
        )
        probe.start()
        (Path(tmp) / "go").write_text("go", encoding="utf-8")
        timeline_path = Path(tmp) / "timeline.json"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not timeline_path.exists():
            time.sleep(0.1)
        time.sleep(0.8)  # 終了後の gone 行も見る
        probe.stop()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        err.close()
        done = (
            json.loads(timeline_path.read_text(encoding="utf-8"))
            if timeline_path.exists()
            else None
        )
        check("使い捨てプロセスが場面を最後まで実行した", done is not None)
        if done is None:
            return failures
        scen = {item["name"]: item for item in done["timeline"]}
        rows = probe.rows
        live = [r for r in rows if not r.get("gone")]
        summary = probe.summary()

        check(
            "UIスレッドを窓から特定(tid一致・source=window)",
            bool(probe.ui_log)
            and probe.ui_log[0]["tid"] == ready["main_tid"]
            and probe.ui_log[0]["source"] == "window"
            and probe.ui_log[0]["hwnd"] == ready["hwnd"],
            str(probe.ui_log[:1]),
        )
        check(
            "OpenProcess/OpenThread は最小権限だけ(process 0x1000・thread 0x800・ThreadLastSystemCall 用の thread 0x48)",
            set(native.open_log)
            <= {("process", 0x1000), ("thread", 0x800), ("thread-syscall", 0x48)}
            and ("thread-syscall", 0x48) in set(native.open_log)
            and bool(native.open_log),
            str(set(native.open_log)),
        )
        check("APIエラーなし(全列が実機で読めた)", not probe.errors, str(probe.errors))
        check(
            "サンプラ自身: 平均コスト<25ms・最大の空き<0.5秒",
            (summary["cost_ms"]["avg"] or 99) < 25 and summary["max_gap_s"] < 0.5,
            f"cost_ms={summary['cost_ms']} max_gap_s={summary['max_gap_s']}",
        )
        say(
            f"     (参考) samples={summary['samples']} cost_ms={summary['cost_ms']} max_gap_s={summary['max_gap_s']}"
        )

        base_lo = scen["go"]["start_tick"] + 300
        base_hi = scen["blocked-sleep"]["start_tick"] - 200
        base = aggregate_rows(
            [r for r in live if base_lo <= (r.get("tick_ms") or 0) <= base_hi],
            probe.wm_null_log,
        )
        check(
            "健全時(idle): ctx切替が毎秒8以上・CPU割合<20%・無スケジュール区間なし",
            (base.get("ctx_per_s") or 0) >= 8
            and (base.get("cpu_share") or 0) < 0.2
            and not [
                e
                for e in summary["stall_episodes"]
                if e["end_tick_ms"] <= base_hi + 100
            ],
            str(base),
        )
        say(
            f"     (参考) idle: ctx/s={base.get('ctx_per_s')} cpu_share={base.get('cpu_share')} states={base.get('states')} wait_reasons={base.get('wait_reasons')} wm_null={base.get('wm_null')}"
        )

        b = scen["blocked-sleep"]
        b_rows = _window_rows(live, b["start_tick"], b["end_tick"], 200)
        b_agg = aggregate_rows(b_rows, probe.wm_null_log)
        b_eps = [
            e
            for e in summary["stall_episodes"]
            if e["start_tick_ms"] < b["end_tick"] and e["end_tick_ms"] > b["start_tick"]
        ]
        check(
            "A: afterコールバック内のsleep 6秒を無スケジュール区間(native-wait)として検出",
            len(b_eps) == 1
            and (b_eps[0]["aggregate"]["duration_s"] or 0) >= 4.5
            and "A:native-wait" in [t["tag"] for t in b_eps[0]["tags"]],
            str(b_eps),
        )
        check(
            "A: 状態=Waiting・CPUはほぼ進まない・hung判定が立つ(待機理由はidleと同じUserRequestでも区別できる)",
            set(b_agg["states"]) == {"Waiting"}
            and (b_agg.get("cpu_share") or 0) < 0.1
            and b_agg["hung_rows"] >= 1,
            str(b_agg),
        )
        say(
            f"     (参考) blocked: ctx/s={b_agg.get('ctx_per_s')} states={b_agg['states']} wait_reasons={b_agg['wait_reasons']} hung_rows={b_agg['hung_rows']}/{b_agg['rows']} wm_null={b_agg.get('wm_null')}"
        )
        idle_calls = Counter(
            r.get("syscall")
            for r in live
            if base_lo <= (r.get("tick_ms") or 0) <= base_hi
        )
        block_calls = Counter(r.get("syscall") for r in b_rows)
        idle_top = idle_calls.most_common(1)[0][0] if idle_calls else None
        block_top = block_calls.most_common(1)[0][0] if block_calls else None
        check(
            "最後のシステムコール: idle は Tcl の MsgWait(NtUserMsgWaitForMultipleObjectsEx)、afterコールバック内の sleep は NtWait* で、待機理由が同じ UserRequest でも見分けられる",
            idle_top == "NtUserMsgWaitForMultipleObjectsEx"
            and str(block_top).startswith("NtWait"),
            f"idle={idle_calls.most_common(3)} blocked={block_calls.most_common(3)}",
        )
        say(
            f"     (参考) syscall idle={idle_calls.most_common(2)} blocked={block_calls.most_common(2)}"
        )
        check(
            "実機で ThreadLastSystemCall を全スレッド分開けた(開けなかったスレッドなし)",
            not summary["syscall_probe"]["unavailable_threads"],
            str(summary["syscall_probe"]["unavailable_threads"]),
        )
        wm_in = b_agg.get("wm_null") or {}
        check(
            "A: ブロック中のWM_NULLは応答せず(timeout/中断)、ok割合<50%",
            (wm_in.get("count") or 0) >= 4
            and wm_in.get("by_result", {}).get("ok", 0) / max(1, wm_in["count"]) < 0.5,
            str(wm_in),
        )
        after_block = [
            x
            for x in probe.wm_null_log
            if b["end_tick"] <= (x.get("tick_ms") or 0) <= b["end_tick"] + 1400
        ]
        check(
            "ブロック解除後はWM_NULLが再びokになる",
            any(x.get("result") == "ok" for x in after_block),
            str(after_block[:3]),
        )

        c = scen["cpu-busy"]
        c_agg = aggregate_rows(
            _window_rows(live, c["start_tick"], c["end_tick"], 200), probe.wm_null_log
        )
        check(
            "C: 1.5秒のCPU消費をスレッドCPU割合40%以上・タグC・サイクル増加で検出",
            (c_agg.get("cpu_share") or 0) >= 0.4
            and "C:cpu-consumed" in [t["tag"] for t in classify_aggregate(c_agg)]
            and (c_agg.get("cycles_m_delta") or 0) > 500,
            str(c_agg),
        )
        say(
            f"     (参考) cpu-busy: cpu_share={c_agg.get('cpu_share')} cycles_m_delta={c_agg.get('cycles_m_delta')} states={c_agg['states']} ctx/s={c_agg.get('ctx_per_s')}"
        )

        m = scen["modal-popup"]
        m_rows = [
            r
            for r in live
            if m["start_tick"] <= (r.get("tick_ms") or 0) <= m["end_tick"]
        ]
        modal_rows = [
            r
            for r in m_rows
            if r.get("gui_flags") and r["gui_flags"] & GUI_POPUPMENUMODE
        ]
        m_agg = aggregate_rows(modal_rows, probe.wm_null_log)
        check(
            "D: ポップアップのモーダルループ中に popup-menu-mode(0x10)を観測しタグD",
            len(modal_rows) >= 5
            and "D:modal-loop" in [t["tag"] for t in classify_aggregate(m_agg)],
            f"popup rows={len(modal_rows)} flags={m_agg.get('gui_flags_rows')}",
        )
        say(
            f"     (参考) modal: flags_seen={sorted({r['gui_flags'] for r in m_rows if r.get('gui_flags') is not None})} menu_owner_rows={sum(1 for r in m_rows if r.get('hwnd_menu_owner'))} hung_rows={m_agg.get('hung_rows')} wm_null={m_agg.get('wm_null')}"
        )
        calm = _window_rows(
            live, scen["cpu-busy"]["end_tick"], scen["modal-popup"]["start_tick"], 200
        )
        check(
            "モーダル前(idle)はflagが0",
            bool(calm) and all((r.get("gui_flags") or 0) == 0 for r in calm),
        )

        w = scen["native-wait-event"]
        w_agg = aggregate_rows(
            _window_rows(live, w["start_tick"], w["end_tick"], 200), probe.wm_null_log
        )
        check(
            "メッセージを捌かない待機(WaitForSingleObject)はctx停止で見分けられる",
            (w_agg.get("ctx_per_s") if w_agg.get("ctx_per_s") is not None else 99)
            < CTX_PER_S_FLAT
            and set(w_agg["states"]) == {"Waiting"},
            str(w_agg),
        )
        say(
            f"     (参考) native-wait-event: wait_reasons={w_agg['wait_reasons']} (idle={base.get('wait_reasons')}) ctx/s={w_agg.get('ctx_per_s')} wm_null={w_agg.get('wm_null')}"
        )

        o = scen["other-thread-busy"]
        o_agg = aggregate_rows(
            _window_rows(live, o["start_tick"], o["end_tick"], 200), probe.wm_null_log
        )
        check(
            "C(他スレッド): UIスレッドが待つ間に別スレッドがCPUを使うと、UIはctx停止・他スレッドCPU割合が高い(タグC:other-thread-cpu)",
            (o_agg.get("ctx_per_s") if o_agg.get("ctx_per_s") is not None else 99)
            < CTX_PER_S_FLAT
            and (o_agg.get("others_cpu_share") or 0) >= 0.5
            and "C:other-thread-cpu" in [t["tag"] for t in classify_aggregate(o_agg)],
            str(o_agg),
        )
        say(
            f"     (参考) other-thread-busy: ui ctx/s={o_agg.get('ctx_per_s')} ui cpu_share={o_agg.get('cpu_share')} others_cpu_share={o_agg.get('others_cpu_share')} busy_other_threads_max={o_agg.get('busy_other_threads_max')} wm_null={o_agg.get('wm_null')}"
        )

        t = scen["memory-touch"]
        t_rows = [
            r
            for r in live
            if t["start_tick"] - 300 <= (r.get("tick_ms") or 0) <= t["end_tick"] + 900
        ]
        t_agg = aggregate_rows(t_rows, probe.wm_null_log)
        check(
            "ページフォルトとワーキングセットの増加(64MBに触れた)を観測",
            (t_agg.get("page_fault_delta") or 0) >= 8000
            and (
                (t_agg["working_set_kb"]["max"] - t_agg["working_set_kb"]["min"])
                >= 30 * 1024
            ),
            str(t_agg),
        )
        both = [
            r
            for r in live
            if r.get("page_faults") is not None and r.get("pf_gmpi") is not None
        ]
        check(
            "ページフォルトの2系統(NTスナップショット/GetProcessMemoryInfo)が整合",
            bool(both)
            and all(abs(r["page_faults"] - r["pf_gmpi"]) < 3000 for r in both),
            str(
                max((abs(r["page_faults"] - r["pf_gmpi"]) for r in both), default=None)
            ),
        )
        say(
            f"     (参考) memory-touch: page_fault_delta={t_agg.get('page_fault_delta')} hard_fault_delta={t_agg.get('hard_fault_delta')} working_set_kb={t_agg.get('working_set_kb')}"
        )

        terminals = [e for e in probe.log_events if e["kind"] == "terminal"]
        lag = None
        if terminals:
            lag = terminals[0]["seen_tick_ms"] - terminals[0]["tick_ms"]
        check(
            "stderrのterminal行を実時間で検出(検出遅れ0〜400ms)",
            len(terminals) == 1 and lag is not None and 0 <= lag <= 400,
            f"events={probe.log_events} lag={lag}",
        )
        say(f"     (参考) terminal検出遅れ={lag}ms")

        anchor0 = probe.anchors[0]
        diffs = []
        for r in live:
            expect = _parse_iso(tick_to_iso(r["tick_ms"], anchor0))
            diffs.append(abs((_parse_iso(r["t"]) - expect).total_seconds() * 1000))
        check(
            "時計の整合: 各サンプルのGetTickCount64と壁時計の差が50ms以内",
            bool(diffs) and max(diffs) <= 50,
            f"max={max(diffs) if diffs else None}ms",
        )
        say(
            f"     (参考) tick-壁時計の差 max={max(diffs):.1f}ms avg={sum(diffs) / len(diffs):.1f}ms"
        )
        check(
            "終了後の観測: gone を記録して落ちない",
            probe.gone_at is not None and any(r.get("gone") for r in rows),
            f"gone_at={probe.gone_at}",
        )
        check(
            "WM_NULL ON: 宛先は非表示窓で、応答/タイムアウトをログに残す",
            len(probe.wm_null_log) >= 10
            and native.wm_null_calls == len(probe.wm_null_log),
            f"calls={native.wm_null_calls} log={len(probe.wm_null_log)}",
        )

        empty = build_request_timeline("", "", probe.anchors)
        check("timeline(空ログ)でも落ちない", empty["requests"] == [])
        full = build_request_timeline(
            (Path(tmp) / "stderr.log").read_text(encoding="utf-8", errors="replace"),
            "peer: accepted: "
            + "ab" * 16
            + " / deadline=%d\n" % (b["start_tick"] + 100),
            probe.anchors,
            live_events=probe.log_events,
        )
        req = full["requests"][0] if full["requests"] else {}
        check(
            "実ログ→timeline: 一次のterminal tickと締切からの遅れが出る",
            req.get("primary_terminal_tick") == b["end_tick"]
            and (req.get("primary_lateness_ms") or 0) > 5000
            and full["late"] is True,
            str(req),
        )

    say("-- 実API(WM_NULL OFF・約3秒) --")
    with tempfile.TemporaryDirectory(prefix="pf-diag-live-off-") as tmp:
        proc, ready, err = spawn(tmp, "idle")
        if proc is None:
            check("使い捨てTclプロセス(idle)を起動できる", False)
        else:
            native = Win32Native()
            probe = UiThreadProbe(
                native,
                ready["pid"],
                interval=0.1,
                wm_null=False,
                phase_fn=lambda: "peer",
            )
            probe.start()
            (Path(tmp) / "go").write_text("go", encoding="utf-8")
            time.sleep(2.0)
            probe.stop()
            proc.kill()
            err.close()
            check(
                "WM_NULL OFF: native.wm_null を1回も呼ばず、ログも空",
                native.wm_null_calls == 0
                and probe.wm_null_log == []
                and probe._wm_thread is None
                and len(probe.rows) >= 15,
                f"calls={native.wm_null_calls} rows={len(probe.rows)}",
            )

    say("-- 失敗経路(実API) --")
    native = Win32Native()
    probe = UiThreadProbe(native, 0x7FFFFFF0, interval=0.05, phase_fn=lambda: "peer")
    try:
        probe.start()
        time.sleep(0.4)
        probe.stop()
        survived = True
    except Exception as error:
        survived = False
        say(f"     例外: {error!r}")
    check(
        "存在しないPID: 例外にならず open_failures を記録し gone 行になる",
        survived
        and bool(probe.open_failures)
        and any(r.get("gone") for r in probe.rows),
        f"{probe.open_failures} rows={len(probe.rows)}",
    )
    native = Win32Native()
    probe = UiThreadProbe(native, 4, interval=0.05, phase_fn=lambda: "peer")
    try:
        probe.start()
        time.sleep(0.4)
        probe.stop()
        survived = True
    except Exception as error:
        survived = False
        say(f"     例外: {error!r}")
    check(
        "権限の足りない対象(PID 4 System): 例外にならず続行する",
        survived and len(probe.rows) >= 3,
        f"rows={len(probe.rows)}",
    )
    first = probe.rows[0] if probe.rows else {}
    say(
        f"     (参考) PID 4: open_failures={probe.open_failures} errors={probe.errors[:3]} "
        f"例={ {k: v for k, v in first.items() if k in ('tid', 'state', 'ctx_switches', 'page_faults', 'gone')} }"
    )

    _live_chain(say, check)
    _live_ghost(say, check)

    fg_after = int(user32.GetForegroundWindow() or 0)
    say(f"     (参考) 前景窓: 前={fg_before} 後={fg_after}")
    check(
        "前景窓が変わっていない(使い捨てプロセスはTkの窓を作らない)",
        fg_before == fg_after,
    )
    return failures
