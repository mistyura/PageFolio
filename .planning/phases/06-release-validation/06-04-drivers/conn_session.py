# ruff: noqa
"""06-04-02 接続実証セッション(利用者が自分の端末で実行する)。

未改変の実配布EXEのcopyを起動し、loopbackの合成OCR(待機型)へ接続させる。利用者が
OCR開始・閉じる確認・「いいえ」・結果表示を操作し、スクリプトは待機中の peer 起動と
待機の解放、外部観測(window/foreground)、server記録を行う。

usage:
  python conn_session.py --t2 <t2_root> --scenario ocr-single
  python conn_session.py --t2 <t2_root> --scenario w05b-modal
  python conn_session.py --t2 <t2_root> --scenario ocr-single --selftest   (機構確認用。証拠にしない)

利用者の入力はすべて逐語で session-<scenario>.json の user_inputs に保存する。
selftest の run は証拠に使わない(selftest=true を記録)。
"""

import argparse
import base64
import io
import json
import sys
import threading
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from tests import release_fake_ocr as F  # noqa: E402
from tests import release_uat_support as S  # noqa: E402

BUILD = S.read_json(
    REPO / ".planning/phases/06-release-validation/06-BUILD-EVIDENCE.json"
)
FINAL = Path(BUILD["final_release"]["final_dir"])
PROVIDER_TIMEOUT = 600
HOLD_LIMIT = 420
WAIT_RECEIVE = 1200


def now():
    return datetime.now(timezone.utc).isoformat()


def say(text=""):
    print(text, flush=True)


class Session:
    def __init__(self, args):
        self.args = args
        self.scenario = args.scenario
        self.selftest = args.selftest
        self.inputs = []
        self.steps = []
        self.server = None
        self.run_dir = None
        self.runs = Path(args.t2) / ("selftest-runs" if args.selftest else "runs")

    def step(self, name, **fields):
        self.steps.append({"at": now(), "step": name, **fields})

    def ask(self, prompt, canned="(selftest)"):
        say(prompt)
        if self.selftest:
            value = canned
        else:
            value = input("> ")
        self.inputs.append(
            {"at": now(), "prompt": prompt.strip().splitlines()[0], "text": value}
        )
        return value

    def wait_event(self, server, name, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(e["event"] == name for e in server.summary()["events"]):
                return True
            time.sleep(0.2)
        return False

    def windows(self, run):
        manifest = S.load_run(run)
        out = {}
        for record in manifest["processes"]:
            if record.get("exit") is None:
                out[f"{record['role']}:{record['pid']}"] = S.windows_of(record["pid"])
        return out

    def run(self):
        manifest = S.prepare(FINAL, f"conn-{self.scenario}", base=self.runs)
        run = Path(manifest["run"])
        evidence = run / "evidence"
        server = F.FakeOcrServer(
            mode="hold",
            run_id=manifest["run_id"],
            log_path=evidence / "fake-ocr-events.jsonl",
            release_flag=run / "release.flag",
            provider_timeout=PROVIDER_TIMEOUT,
            hold_limit=HOLD_LIMIT,
        ).start()
        self.server = server
        self.run_dir = run
        result = {
            "scenario": self.scenario,
            "selftest": self.selftest,
            "run_id": manifest["run_id"],
            "run": str(run),
            "binary_sha256": manifest["source"]["exe_sha256"],
            "tree_sha256": manifest["source"]["tree_sha256"],
            "server_url": server.url,
            "hold_limit_seconds": HOLD_LIMIT,
            "provider_timeout_seconds": PROVIDER_TIMEOUT,
            "started_at": now(),
        }
        try:
            pdf = S.add_fixture_pdf(run, "ocr-one-page")
            settings = json.dumps(
                S.ocr_settings(server.url, timeout=PROVIDER_TIMEOUT),
                ensure_ascii=False,
                indent=2,
            )
            S.declare_overlay(
                run,
                {S.SETTINGS_NAME: settings.encode("utf-8")},
                "合成OCR接続: ollama設定(loopback)・並列1",
            )
            result["pdf"] = pdf
            result["settings_keys"] = sorted(json.loads(settings))
            S.start(run, settle=5.0)
            self.step(
                "started", windows=self.windows(run), foreground=S.foreground_info()
            )
            say("")
            say("== PageFolio を起動しました (配布EXEの隔離コピー) ==")
            say(f"開くPDF: {pdf['path']}")
            if not self.selftest:
                try:
                    subprocess.run(
                        ["clip"],
                        input=pdf["path"].encode("ascii"),
                        check=False,
                        timeout=10,
                    )
                    say(
                        "(PDFのパスはクリップボードにコピー済みです。ファイル選択画面で貼り付けできます)"
                    )
                except Exception:
                    pass
            say("手順:")
            say(
                "  1. PageFolio の画面へ上のPDFを開く (ドラッグ&ドロップ、または ファイルを開く)"
            )
            say("  2. ページ1 (唯一のページ) だけを選択した状態にする")
            say(
                "  3. 右ペインの OCR から『🔠 現在ページをテキスト抽出』を押し、OCRダイアログを開く"
            )
            say(
                "  4. 『埋め込みテキストを無視して OCR を実行』は ON のままで構いません。サマリは実行しない"
            )
            say(
                "  5. 『▶ 読み取り実行』を押す  (押すと待機状態になります。最大7分待ちます)"
            )
            if self.selftest:
                self.drive_selftest(server)
            if not self.wait_event(server, "received", WAIT_RECEIVE):
                result["outcome"] = "no-request-received"
                return result, server, run
            say("")
            say("[OK] 合成OCRサーバーが要求を1件受信し、待機に入りました。")
            self.step(
                "received", windows=self.windows(run), foreground=S.foreground_info()
            )
            if self.scenario == "w05b-modal":
                self.w05b(run, server, result)
            else:
                self.ocr_single(run, server, result)
            return result, server, run
        finally:
            pass

    def drive_selftest(self, server):
        def post():
            time.sleep(2)
            from PIL import Image

            buffer = io.BytesIO()
            Image.new("RGB", (64, 64), "white").save(buffer, "PNG")
            url = (
                "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
            )
            body = json.dumps(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": url}}
                            ],
                        }
                    ]
                }
            ).encode()
            req = urllib.request.Request(
                server.url + "/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(req, timeout=60).read()
            except Exception:
                pass

        threading.Thread(target=post, daemon=True).start()

    def launch_peer(self, run, result):
        try:
            record = S.peer(run)
            time.sleep(4)
            obs = S.inspect(run, "after-peer")
            result["peer"] = {
                "record_pid": record["pid"],
                "launched_at": record["started_at"],
                "processes": obs["processes"],
                "foreground": obs["foreground"],
                "owner_probe": obs["owner_probe"],
            }
            self.step("peer", windows=self.windows(run), foreground=obs["foreground"])
        except S.SupportError as error:
            result["peer_error"] = str(error)

    def release(self, run, server, result):
        (run / "release.flag").write_text("release\n", encoding="utf-8")
        ok = self.wait_event(server, "completed", 60)
        result["release_at"] = now()
        result["completed_seen"] = ok

    def ocr_single(self, run, server, result):
        time.sleep(2)
        self.launch_peer(run, result)
        say(
            "[OK] 2つ目の起動(peer)を行いました。PageFolioの画面が前面に残るか確認してください。"
        )
        time.sleep(1)
        self.release(run, server, result)
        say("[OK] 待機を解放しました。")
        answer = self.ask(
            "OCRダイアログの結果欄に『PageFolio UAT 合成OCR結果』が表示されましたか?\n"
            "見えた内容・気づいた点をそのまま入力してください (例: 表示された / 表示されない):"
        )
        result["user_answer"] = answer
        result["expected_text"] = F.RESULT_TEXT

    def w05b(self, run, server, result):
        say("次に、OCRダイアログの『✕ 閉じる』を押してください。")
        say(
            "『OCR 実行中です…閉じますか?』の確認ダイアログが出たら、まだボタンは押さないでください。"
        )
        a1 = self.ask("確認ダイアログが表示されたら、見えたことを入力して Enter:")
        main_pid = S.load_run(run)["processes"][0]["pid"]
        before = S.windows_of(main_pid)
        result["modal_windows_before_peer"] = before
        result["modal_user_answer"] = a1
        self.step("modal-up", windows=self.windows(run), foreground=S.foreground_info())
        self.launch_peer(run, result)
        after = S.windows_of(main_pid)
        result["modal_windows_after_peer"] = after
        result["foreground_after_peer"] = S.foreground_info()
        say("[OK] 2つ目の起動(peer)を行いました。")
        a2 = self.ask(
            "確認ダイアログは消えずに(または同じものが)前面に出ていますか? 見えたことを入力:\n"
            "(まだボタンは押さないでください)"
        )
        result["peer_return_user_answer"] = a2
        a3 = self.ask(
            "確認ダイアログの『いいえ』を押してください。OCRダイアログが残り、処理が続いていれば、\n"
            "その状態を入力して Enter:"
        )
        result["no_user_answer"] = a3
        self.step("answered-no", windows=self.windows(run))
        time.sleep(1)
        self.release(run, server, result)
        say("[OK] 待機を解放しました。")
        a4 = self.ask(
            "OCRダイアログの結果欄に『PageFolio UAT 合成OCR結果』が表示されましたか? (同じ処理が完了したか)\n"
            "見えた内容を入力:"
        )
        result["user_answer"] = a4
        result["expected_text"] = F.RESULT_TEXT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t2", required=True)
    ap.add_argument("--scenario", choices=("ocr-single", "w05b-modal"), required=True)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    session = Session(args)
    result = {"scenario": args.scenario, "selftest": args.selftest}
    try:
        result, _server, _run = session.run()
    except KeyboardInterrupt:
        result["interrupted"] = True
    except Exception as error:
        result["error"] = repr(error)
        say(f"エラー: {error!r}")
    finally:
        server = session.server
        run_dir = session.run_dir
        result.setdefault("run", str(run_dir) if run_dir else None)
        stop = None
        if run_dir is not None and run_dir.is_dir():
            try:
                stop = S.stop(run_dir, timeout=12.0)
            except Exception as error:
                stop = repr(error)
            verify = S.verify_copy(S.load_run(run_dir))
        else:
            verify = None
        summary = server.summary() if server else None
        if server:
            server.stop()
        result.update(
            finished_at=now(),
            stop=stop,
            verify_after={
                k: verify[k] for k in ("ok", "overlay_changed", "distribution_changed")
            }
            if verify
            else None,
            owner_after=S.probe_owner(),
            user_inputs=session.inputs,
            steps=session.steps,
            server_summary=summary,
        )
        if run_dir is not None and run_dir.is_dir():
            out = run_dir / "evidence" / f"session-{args.scenario}.json"
            S.write_json(out, result)
            say(f"\n記録を保存しました: {out}")
        say("終了しました。PageFolio は自動で閉じました。結果を担当へ伝えてください。")


if __name__ == "__main__":
    main()
