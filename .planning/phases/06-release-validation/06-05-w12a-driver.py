"""W12aの一次・二次を一度ずつ起動し、所有runだけを有限時間で回収する。"""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "tests/test_startup_windows.py"


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return datetime.now(UTC).isoformat()


def command(action, run, extra=(), *, timeout=25):
    proc = subprocess.run(  # noqa: S603 -- 固定済みPython/harness/runのみ。
        [sys.executable, str(HARNESS), "--uat", action, "--run", str(run), *extra],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    ensure(proc.returncode == 0, f"{action}: {proc.stderr}")
    return json.loads(proc.stdout)


def reserve(deadline, seconds):
    """ownerの実watchdog期限から通常stopと余白を残す。"""
    ensure(
        time.monotonic() + seconds + 10 < deadline,
        "owner期限の余白不足。peer/待機を中止して通常回収",
    )


def collect(primary, secondary, *, prepeer_seconds=20, afterpeer_seconds=15):
    ensure(primary in {"script", "module", "relocated"}, "一次入口不正")
    ensure(secondary in {"script", "module", "relocated"}, "二次入口不正")
    ensure(0 <= prepeer_seconds <= 20 and 0 <= afterpeer_seconds <= 15, "観測時間不正")
    run = ROOT / ".planning/tmp" / ("pagefolio-uat-" + uuid4().hex)
    events = []
    owner_started = False
    try:
        print(
            "一次を隔離起動します。画面で状態を作り、二次起動まで観察してください。",
            flush=True,
        )
        manifest = command("start", run, ("--w12a-primary", primary), timeout=30)
        owner_started = True
        events.append(
            {
                "step": "start",
                "at_utc": utc(),
                "owner": manifest["expected_owner"],
                "role": manifest["role"],
            }
        )
        ensure(manifest["role"] == f"entry-owner-{primary}", "一次入口不一致")
        timer = manifest["expected_owner"].get("manual_deadline", {})
        ensure(timer.get("delay_ms") == 120000, "W12a owner期限が不正")
        deadline = timer.get("due_monotonic")
        ensure(
            isinstance(deadline, (int, float))
            and timer.get("registered_monotonic", float("inf"))
            <= timer.get("ready_monotonic", float("-inf"))
            <= deadline,
            "W12a owner時刻が不正",
        )
        reserve(deadline, prepeer_seconds + 20 + afterpeer_seconds + 5 + 15)
        print(
            f"一次={primary}、二次={secondary}。{prepeer_seconds}秒後に二次を一回起動します。",
            flush=True,
        )
        time.sleep(prepeer_seconds)
        reserve(deadline, 20 + afterpeer_seconds + 5 + 15)
        peer = command("peer", run, ("--entry", secondary), timeout=20)
        events.append({"step": "peer", "at_utc": utc(), "result": peer["result"]})
        foreground = json.loads(
            (run / "w12a-after-peer.json").read_text(encoding="utf-8")
        )
        events.append({"step": "foreground", "at_utc": utc(), "snapshot": foreground})
        print(
            f"前景を記録しました。{afterpeer_seconds}秒間、同じ一次画面と編集状態を直接確認してください。",
            flush=True,
        )
        reserve(deadline, afterpeer_seconds + 5 + 15)
        time.sleep(afterpeer_seconds)
        reserve(deadline, 5 + 15)
        inspected = command("inspect", run, timeout=5)
        events.append(
            {
                "step": "inspect",
                "at_utc": utc(),
                "originals_unchanged": inspected["originals_unchanged"],
            }
        )
    except Exception as error:
        events.append({"step": "failed", "at_utc": utc(), "error": str(error)})
        raise
    finally:
        if owner_started or (run / "manifest.json").is_file():
            try:
                stopped = command("stop", run, timeout=15)
                events.append(
                    {
                        "step": "stop",
                        "at_utc": utc(),
                        "originals_unchanged": stopped["originals_unchanged"],
                    }
                )
            except Exception as error:
                events.append(
                    {"step": "stop_failed", "at_utc": utc(), "error": str(error)}
                )
        if run.is_dir():
            (run / "w12a-driver.json").write_text(
                json.dumps(
                    {
                        "schema": "w12a-driver-v1",
                        "run": str(run),
                        "primary": primary,
                        "secondary": secondary,
                        "events": events,
                        "finished_at": utc(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps({"run": str(run), "events": events}, ensure_ascii=False),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description="W12a一次/二次を一runだけ採取")
    parser.add_argument(
        "--primary", required=True, choices=["script", "module", "relocated"]
    )
    parser.add_argument(
        "--secondary", required=True, choices=["script", "module", "relocated"]
    )
    args = parser.parse_args()
    collect(args.primary, args.secondary)


if __name__ == "__main__":
    main()
