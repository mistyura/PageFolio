# ruff: noqa
"""06-04-02 接続実証セッション(利用者が自分の端末で実行する)。

未改変の実配布EXEのcopyを起動し、loopbackの合成OCR(待機型)へ接続させる。利用者が
OCR開始・閉じる確認・「いいえ」・結果表示を操作し、スクリプトは待機中の peer 起動と
待機の解放、外部観測(window/foreground)、server記録を行う。

usage:
  python conn_session.py --t2 <t2_root> --scenario ocr-single
  python conn_session.py --t2 <t2_root> --scenario ocr-single --check-routing-only   (事前確認のみ。EXEは起動しない)
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


def _norm_code(code):
    """co_filename・行番号表を除いた比較用の正規形。"""
    import types

    return (
        code.co_name,
        code.co_code,
        code.co_names,
        code.co_varnames,
        code.co_argcount,
        code.co_flags,
        tuple(
            _norm_code(k) if isinstance(k, types.CodeType) else k
            for k in code.co_consts
        ),
    )


def _module_of(rel):
    parts = list(Path(rel).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


KEY_MODULES = ("pagefolio.ocr", "pagefolio.ocr_dialog", "pagefolio.lang")


def routing_selfcheck(manifest, server):
    """配布copyの設定が、このEXE自身のコードでloopbackの合成OCRへ届くことを事前確認する。

    EXEは起動しない(読むだけ)。確認内容:
      1. copy内の pagefolio_settings.json が ollama + 合成サーバーURL(127.0.0.1)・並列1・fallback無効
      2. copy内のEXEが最終buildのEXEと同一SHA-256
      3. EXE内蔵のPYZから取り出した pagefolio.ocr / ocr_dialog / lang のバイトコードが、
         監査済みHEADのソースをコンパイルしたものと一致(=製品修正入りの実体)
      4. EXE内蔵の resolve_local_endpoint に上の設定を渡すと (合成サーバーURL, モデル) になる
         (lmstudio 側のURLは合成サーバーではない)
      5. 合成サーバーが /v1/models に応答する
    """
    import contextlib
    import os
    import tempfile
    from urllib.parse import urlparse

    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    checks = []

    def check(name, ok, detail=None):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    copy = Path(manifest["copy"])
    exe = copy / "PageFolio.exe"
    settings_path = copy / S.SETTINGS_NAME
    settings = json.loads(settings_path.read_text("utf-8"))
    check("設定: ocr_provider=ollama", settings.get("ocr_provider") == "ollama")
    check(
        "設定: ollama_url=合成サーバーURL",
        settings.get("ollama_url") == server.url,
        {"ollama_url": settings.get("ollama_url"), "server": server.url},
    )
    check(
        "設定: 接続先はloopback(127.0.0.1)",
        urlparse(server.url).hostname == "127.0.0.1",
        server.url,
    )
    check(
        "設定: 並列1・fallback無効",
        settings.get("ocr_concurrency") == 1
        and settings.get("ocr_fallback_enabled") is False,
    )
    exe_sha = S.sha_file(exe)
    check(
        "copy内EXE=最終buildのEXE",
        exe_sha == BUILD["final_release"]["exe_sha256"],
        exe_sha,
    )

    tmp = Path(tempfile.mkdtemp(prefix="pf_routing_"))
    endpoint = None
    try:
        pyz = tmp / "PYZ.pyz"
        pyz.write_bytes(CArchiveReader(str(exe)).extract("PYZ.pyz"))
        archive = ZlibArchiveReader(str(pyz))
        mismatched, compared, missing = [], 0, []
        for src in sorted((REPO / "pagefolio").rglob("*.py")):
            rel = src.relative_to(REPO).as_posix()
            mod = _module_of(rel)
            if mod not in archive.toc:
                missing.append(mod)
                continue
            mine = compile(src.read_bytes(), rel, "exec", dont_inherit=True)
            compared += 1
            if _norm_code(mine) != _norm_code(archive.extract(mod)):
                mismatched.append(mod)
        check(
            "EXE内蔵コード=HEADのソース(pagefolio全モジュール)",
            not mismatched and all(m in archive.toc for m in KEY_MODULES),
            {"compared": compared, "mismatched": mismatched, "not_in_pyz": missing},
        )
        ns = {"__name__": "pagefolio._dist_ocr_probe", "__file__": "<EXE PYZ>"}
        with contextlib.redirect_stderr(io.StringIO()):
            exec(archive.extract("pagefolio.ocr"), ns)
        resolve = ns["resolve_local_endpoint"]
        endpoint = resolve(settings, "ollama")
        check(
            "EXE内蔵resolve_local_endpoint(ollama)=合成サーバーURL・モデル",
            endpoint == (server.url, F.MODEL),
            endpoint,
        )
        lm = resolve(settings, "lmstudio")
        check(
            "lmstudio側URLは合成サーバーではない(旧不具合の経路と区別)",
            lm is not None and lm[0] != server.url,
            lm,
        )
        dialog_code = archive.extract("pagefolio.ocr_dialog")
        names = set()

        def walk(code):
            import types

            names.update(code.co_names)
            for k in code.co_consts:
                if isinstance(k, types.CodeType):
                    walk(k)

        walk(dialog_code)
        check(
            "EXE内蔵OCRDialogがresolve_local_endpointを参照",
            "resolve_local_endpoint" in names,
        )
    except Exception as error:
        check("EXE内蔵コードの確認が例外なく完了", False, repr(error))
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
    try:
        with urllib.request.urlopen(server.url + "/v1/models", timeout=10) as r:
            body = r.read().decode("utf-8", "replace")
        check("合成サーバーが/v1/modelsに応答", F.MODEL in body, body[:200])
    except Exception as error:
        check("合成サーバーが/v1/modelsに応答", False, repr(error))
    return {
        "ok": all(c["ok"] for c in checks),
        "at": now(),
        "exe_started": False,
        "resolved_endpoint": list(endpoint) if endpoint else None,
        "server_url": server.url,
        "checks": checks,
    }


def print_selfcheck(report):
    say("== 事前確認(EXEは起動していません) ==")
    for c in report["checks"]:
        say(f"  [{'OK' if c['ok'] else 'NG'}] {c['name']}")
    if report["ok"]:
        say("[OK] この配布コピーのOCR設定は、合成OCRサーバーへ届くことを確認しました。")
    else:
        say(
            "[NG] 事前確認に失敗したため、PageFolio は起動しません。担当へ伝えてください。"
        )


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
            report = routing_selfcheck(manifest, server)
            result["routing_selfcheck"] = report
            print_selfcheck(report)
            if self.args.check_routing_only:
                result["outcome"] = "routing-check-only"
                return result, server, run
            if not report["ok"]:
                result["outcome"] = "routing-selfcheck-failed"
                return result, server, run
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
            say("")
            say(
                "【重要】LLM設定(🤖)は開かないでください。プロバイダも変更しないでください。"
            )
            say(
                "        設定は合成OCRサーバーへ向けて準備済みです。変更すると接続実証になりません。"
            )
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
            "(画像の文字『OCR TEST 0123456789』が出た場合は合成サーバー以外が使われています。その旨をそのまま入力)\n"
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
    ap.add_argument(
        "--check-routing-only",
        action="store_true",
        help="事前確認だけ行う(EXEは起動しない)。証拠のconnectionには使わない",
    )
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
