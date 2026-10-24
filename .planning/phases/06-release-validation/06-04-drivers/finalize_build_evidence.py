# ruff: noqa
"""06-04-01 新世代(generation 2): build_driver.py assemble の生JSONに品質・依存・旧世代履歴を加えて 06-BUILD-EVIDENCE.json を書く。

usage: finalize_build_evidence.py <raw_json>

旧世代(1bdd572 の 06-BUILD-EVIDENCE.json 全体)は previous_generations[0].evidence に原文のまま保持する。
製品はimportしない。
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Users\shdwf\work\project\PageFolio")
EVID = REPO / ".planning/phases/06-release-validation/06-BUILD-EVIDENCE.json"
LOG_REL = ".planning/phases/06-release-validation/06-04g2-task1-full.txt"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *a],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def main() -> None:
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    # 旧世代: HEAD にコミットされている現行(=世代1)の証拠を原文のまま保持
    old_text = git(
        "show", "HEAD:.planning/phases/06-release-validation/06-BUILD-EVIDENCE.json"
    )
    old = json.loads(old_text)
    if "previous_generations" in old:
        raise SystemExit("STOP: HEADの証拠が既に世代2以降")
    head = git("rev-parse", "HEAD")
    d = dict(raw)
    d["generation"] = 2
    d["generation_note"] = (
        "製品修正(52258de ollama選択時の送信先修正 / 7fb41a2 LLM設定適用後のプロバイダ表示更新)後の新世代。"
        "世代1(1bdd572)のbuild/保護/接続は旧製品バイトに対するもので、接続実証で製品バグが見つかったため取り直した。"
        "世代1の証拠はprevious_generationsへ原文保持(上書きしない)。"
    )
    d["previous_generations"] = [
        {
            "generation": 1,
            "status": "superseded",
            "superseded_reason": (
                "接続実証(06-04-02 human-check)で製品バグ発見: ocr_provider=ollama でもOCRダイアログが"
                "LM Studio(localhost:1234)へ送信。06-03 resume_contract に従い新世代で取り直し。"
            ),
            "evidence_commit": "1bdd572",
            "protection_evidence_commit": "78dcfe8",
            "old_output_root_preserved": r"C:\Users\shdwf\AppData\Local\Temp\pf06_final_2f67e363e4ca4304b1ea6a9a11431358",
            "old_t2_dir_preserved": r"C:\Users\shdwf\AppData\Local\Temp\pf06_t2_f157d1e5a0454f7e89c363383182dff5",
            "evidence_sha256": hashlib.sha256(old_text.encode("utf-8")).hexdigest(),
            "evidence": old,
        }
    ]
    d["dependency"] = {
        "phase4": {
            "verification_status": "passed",
            "result": "21/21",
            "covered_digest": "v3:sha256:7436bfbe557b89884f4d6842c32f94a27f1f70da4e5c099e33745fc8700b4982",
            "verification_commit": "404538a",
            "verifier": "親orchestrator委任の再検証(製品修正52258de/7fb41a2後)",
            "status_command": "gsd-tools query verification status .planning/phases/04-startup-control",
            "status_at_task_start": "passed",
            "w_human_items": "Phase6移管/not-runのまま。fresh報告をW合格にしない",
        },
        "phase5": {
            "verification_status": "passed",
            "result": "23/23",
            "verification_commit": "94c5fb7",
            "covered_digest": "v3:sha256:5e1b3d4ce8b5f5eeed41dcf971459d5fc51edf2105dbbae328e9d52614470d31",
            "note": (
                "このdigestは当時未コミットだった別件の開発履歴.md/requirements.txtの内容を含む。"
                "両ファイルはその後 570b931 でコミットされた(製品・試験の.pyは不変)。"
            ),
        },
        "takeover_loser_expired": {
            "classification": "試験側の前提誤り(製品欠陥ではない)。.planning/debug/resolved/takeover-loser-expired.md",
            "fix_commit": "3e56452",
            "archive_commit": "40cc1be",
            "note": "世代1から引継ぎ。製品コード・5000ms期限は不変。",
        },
        "ocr_ollama_uses_lmstudio_url": {
            "classification": "製品バグ(接続実証で発見)。.planning/debug/resolved/ocr-ollama-uses-lmstudio-url.md",
            "fix_commits": ["52258de", "7fb41a2"],
            "archive_commit": "202b2c0",
            "changed_product_files": [
                "pagefolio/lang.py",
                "pagefolio/ocr.py",
                "pagefolio/ocr_dialog.py",
            ],
        },
    }
    d["failed_connection_attempts_gen1"] = [
        {
            "run_id": "release-uat-c75a19aa09b84f1788c0dee965915dd7",
            "status": "not-established",
            "reason": (
                "利用者がLLM設定でOllama->Geminiへ変更。OCRダイアログ表示は『ollama』のままで、合成サーバーは"
                "要求0件、結果欄に画像の文字『PageFolio UAT / OCR TEST 0123456789』が表示された"
                "(実Geminiによる読取とみられる。送信は合成画像のみ)。表示と実送信先の不一致"
                "(.planning/todos/pending/2026-10-24-ocr-dialog-provider-stale.md)。成立と記録しない。"
            ),
        },
        {
            "run_id": "release-uat-034578b2c4b94c2aae9fa70afe620d25",
            "status": "not-established",
            "reason": (
                "設定は ocr_provider=ollama / ollama_url=http://127.0.0.1:17327(合成サーバーは同ポートでLISTEN)だが、"
                "読取実行で『LM Studio に接続できませんでした。URL: http://localhost:1234 ... [WinError 10061]』。"
                "製品バグ(_start_ocr がlm_studio_urlを渡す/OCRDialog実行時再生成がurl_varでOllamaProviderを作る)。"
                "成立と記録しない。"
            ),
        },
    ]
    d["quality"] = {
        "head": head,
        "ruff_check": "All checks passed!",
        "ruff_format": "Python対象のみ(git ls-files '*.py'): 122 files already formatted。Markdownへは適用しない",
        "ast": "git ls-files '*.py' 122件(+pagefolio.py) 構文OK",
        "pytest": {
            "mode": "単一プロセス・native・除外なし",
            "result": "2014 passed, 1 warning in 710.70s (0:11:50)",
            "exit": 0,
            "passed": 2014,
            "failed": 0,
            "errors": 0,
            "crashed": False,
            "excluded": False,
            "single_process": True,
            "warning": "pymupdf DeprecationWarning(typing.ByteString)のみ。Tcl/unraisable警告なし(ログにtcl/unraisable/error/failedは0件)",
            "log": LOG_REL,
            "log_sha256": sha(REPO / LOG_REL),
            "run_window_local": "2026-10-24 約20:27:50 - 20:39:42 (+09:00)",
            "reuse": {
                "rule": "同一コード・入力・環境の成功はhash照合して再利用(06-04 execution_rules)",
                "tested_blobs": {
                    "pagefolio/ocr.py": git("rev-parse", "HEAD:pagefolio/ocr.py"),
                    "pagefolio/ocr_dialog.py": git(
                        "rev-parse", "HEAD:pagefolio/ocr_dialog.py"
                    ),
                    "pagefolio/lang.py": git("rev-parse", "HEAD:pagefolio/lang.py"),
                    "tests/test_ocr_local_endpoint.py": git(
                        "rev-parse", "HEAD:tests/test_ocr_local_endpoint.py"
                    ),
                    "tests/test_ocr_dialog_provider_refresh.py": git(
                        "rev-parse", "HEAD:tests/test_ocr_dialog_provider_refresh.py"
                    ),
                },
                "working_tree_equals_head_for_those": True,
                "changed_after_run_start": (
                    "run開始(約20:27:50)以降に更新された非.planning/.git/.venv/cache fileは開発履歴.mdのみ(文書)。"
                    ".venv内に17:30以降の更新fileなし。以後のcommit(7fb41a2以降)の.py差分は無く、"
                    "570b931/f169171は requirements.txt(依存版を導入済みの版へ同期)と開発履歴.md/.planningのみ"
                ),
                "dependency_versions": d["freeze"]["dependencies"],
                "fresh_run_skipped": True,
            },
        },
        "symptom_notes": "症状(1)TclError/症状(2)STATUS_BREAKPOINTの再発なし(当該2014件実行では0)。非再現を前提にした合格判断はしない。",
    }
    d["drivers"] = {
        "build_driver.py": {
            "path": ".planning/phases/06-release-validation/06-04-drivers/build_driver.py",
            "sha256": sha(
                REPO
                / ".planning/phases/06-release-validation/06-04-drivers/build_driver.py"
            ),
            "role": "freeze/CLI2回/assemble。製品をimportせず、tools.build_releaseの入力関数とtests.release_uat_supportのhash関数のみ使用。実buildは世代1のbuild_driver2.py(sha256 930f87c4...)と同一bytesで実行し、その後commit用に先頭へ`# ruff: noqa`を足してruff formatした(挙動不変、現sha256を本欄に記録)",
        },
        "finalize_build_evidence.py": {
            "path": ".planning/phases/06-release-validation/06-04-drivers/finalize_build_evidence.py",
            "role": "世代2の証拠組立。世代1の証拠をprevious_generationsへ原文保持",
        },
    }
    EVID.write_text(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("written", EVID.stat().st_size)


if __name__ == "__main__":
    main()
