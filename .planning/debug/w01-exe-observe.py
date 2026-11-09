"""W01実EXEの外部診断。前景/入力を読むだけで、受入passには使わない。"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".planning/phases/06-release-validation/06-05-drivers"))
import uat_row as U  # noqa: E402


def main():
    s = {
        "purpose": "debug-w01-exe-foreground",
        "acceptance": False,
        "started_at": U.now(),
        "steps": [],
    }
    p = U.Prompter(False)
    monitor = None
    run = None
    started = False

    def observe(label):
        result = U.S.inspect(run, label)
        s["steps"].append({"at": U.now(), "label": label, "observation": result})

    try:
        manifest = U.S.prepare(U.FINAL, "W01", overlays={U.S.SETTINGS_NAME: None})
        run = Path(manifest["run"])
        s["run"] = str(run)
        s["binary_sha256"] = manifest["source"]["exe_sha256"]
        primary = U.S.start(run, settle=5)
        started = True
        s["primary"] = primary
        p.show("これは原因調査です。PageFolioをまだ最小化しないでください。")
        p.show(
            "通常の大きさで表示されていることを確認し、位置・大きさとヘッダー文字を覚えてください。"
        )
        p.enter("PageFolioを表示したままPowerShellへ切り替え、Enterを押してください。")
        before = U.main_windows([primary["pid"]])
        s["before_minimize"] = before
        if len(before) != 1 or before[0]["iconic"] or before[0]["zoomed"]:
            raise U.S.NotEstablished(
                "通常表示の元状態を確認できません。二次起動せず終了します。"
            )
        p.show("ここでPageFolioの「－」ボタンを押して最小化してください。")
        p.show("次のEnter後は20秒間、切替・クリック・キー入力をしないでください。")
        p.show("20秒経ったらPowerShellへ戻ってください。観測は14秒で終わります。")
        p.enter("最小化したらPowerShellへ戻り、Enterを押してください。")
        minimized = U.main_windows([primary["pid"]])
        s["minimized"] = minimized
        if len(minimized) != 1 or not minimized[0]["iconic"]:
            raise U.S.NotEstablished("最小化を確認できません。二次起動せず終了します。")
        monitor = U.InputMonitor()
        monitor.set_owned_pids([primary["pid"]])
        monitor.set_phase("peer")
        monitor.start()
        s["foreground_before_peer"] = U.S.foreground_info()
        origin = time.monotonic()
        s["peer"] = U.S.peer(run)
        for seconds in (4, 10, 14):
            time.sleep(max(0, origin + seconds - time.monotonic()))
            observe(f"peer-plus-{seconds}s")
        monitor.stop()
        s["input_monitor"] = monitor.summary()
        p.show("観測が終わりました。PowerShellへ戻って回答してください。")
        s["answers"] = {
            "visible": p.ask(
                "visible", "何が手前に見えましたか？ PageFolio / PowerShell / その他"
            ),
            "operation": p.ask(
                "operation",
                "観測中に切替・クリック・キー入力をしましたか？ した / していない",
            ),
            "note": p.ask("note", "ほかに気づいた点があれば短く。なければ「なし」"),
        }
        s["outcome"] = "observed"
    except Exception as error:
        s["outcome"] = "error"
        s["error"] = repr(error)
        U.say(f"準備または観測のエラー: {error!r}")
    finally:
        if monitor is not None:
            monitor.stop()
            s["input_monitor"] = monitor.summary()
        if started:
            try:
                s["stop"] = U.S.stop(run, timeout=12)
                s["verify_after"] = U.S.verify_copy(U.S.load_run(run))
                s["source_distribution_unchanged"] = U.S._source_unchanged(
                    U.S.load_run(run)
                )
                s["owner_after"] = U.S.probe_owner()
            except Exception as error:
                s["cleanup_error"] = repr(error)
        s["raw_inputs"] = p.inputs
        s["finished_at"] = U.now()
        folder = ROOT / ".planning/debug/w01-exe-foreground-evidence"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        with (folder / f"observe-{stamp}.json").open("x", encoding="utf-8") as out:
            json.dump(s, out, ensure_ascii=False, indent=2)
        U.say(
            "診断が終了しました。PowerShellを閉じ、チャットへ「診断完了」と回答してください。"
        )


if __name__ == "__main__":
    main()
