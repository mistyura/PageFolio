# ruff: noqa
"""06-04-02: t2_driver / conn_session の生記録から 06-PROTECTION-EVIDENCE.json を組み立てる。

値は生記録(t2-result.json、session-*.json)から機械的に写すだけで、利用者の回答は逐語で保持し、
人手の判断(回答が成立を示すか)は --accept-user-answers を与えた場合に限り受け入れる。
未指定の接続は connection に入れず pending として明記する(成立済みにしない)。

usage:
  assemble_protection.py --t2 <t2_root> [--ocr-session <session-ocr-single.json>]
                         [--w05b-session <session-w05b-modal.json>] [--accept-user-answers]
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from tests import release_uat_support as S  # noqa: E402

PHASE = REPO / ".planning/phases/06-release-validation"
EVIDENCE = PHASE / "06-PROTECTION-EVIDENCE.json"
PREP = PHASE / "06-UAT-PREPARATION.md"
RAW_T2 = "06-04g2-t2-result.json"  # 世代2。世代1は06-04-t2-result.json(原本保持)
GEN1_RAW_T2 = "06-04-t2-result.json"
MARK_START = "<!-- run-refs:start (assemble_protection.py が生成。手で編集しない) -->"
MARK_END = "<!-- run-refs:end -->"
SETTINGS = S.SETTINGS_NAME


def short(h):
    return None if h is None else h[:16]


def build_protection_stop(t2):
    out = []
    for item in t2["protection_stop"]:
        out.append(
            {
                "name": item["name"],
                "run_id": item["run_id"],
                "cli_argv": item["cli_argv"],
                "exit_code": item["exit_code"],
                "builder_started": item["builder_started"],
                "stage": "preflight(build subprocess 開始前)"
                if "[preflight]" in item["stderr"]
                else "UNKNOWN",
                "stderr": item["stderr"],
                "elapsed_seconds": item["elapsed_seconds"],
                "placed": item["placed"],
                "output_root": item["output_root"],
                "before": item["before"],
                "after": item["after"],
            }
        )
    return out


def build_launch(t2):
    cases = []
    for case in t2["launch"]["cases"]:
        cases.append(
            {
                "name": case["name"],
                "run_id": case["run_id"],
                "binary_sha256": case["binary_sha256"],
                "tree_sha256": case["tree_sha256"],
                # 外部lock中は保持者(観測側)が自分のhandleから読んだhashを実hashとして使う(生値は *_raw)
                "hash_before": case["hash_before_effective"],
                "hash_stable": case["hash_stable_effective"],
                "hash_after_exit": case["hash_after_exit"],
                "hash_before_raw": case["hash_before"],
                "hash_stable_raw": case["hash_stable"],
                "hash_after_exit_with_hold_raw": case["hash_after_exit_with_hold"],
                "holder_hash_after_exit": case["holder_hash_after_exit"],
                "stop": case["stop"],
                "stop_diagnostics": case["stop_diagnostics"],
                "verify_after": case["verify_after"],
                "source_unchanged": case["source_unchanged"],
                "owner_probe_before": case["probe_owner_before"],
                "owner_probe_after": case["owner_after"],
                "observed_at": case["observed_at"],
                "inspect_stable": case["inspect_stable"],
                "note": (
                    "normal: 起動安定後(終了前)のhashは起動前と一致。終了後の差は終了時の正当なwindow保存(overlay変化)であり別時点"
                    if case["name"] == "normal"
                    else "corrupt/unreadable: 終了後も原本hashが起動前と一致(原本保持)"
                ),
            }
        )
    return {"cases": cases}


def build_update(t2):
    out = {}
    for scenario, v in t2["update"].items():
        base = {
            "procedure": v["procedure"],
            "old_source": v["old_source"],
            "copies": [
                {
                    "role": "old(initial run tree)",
                    "run_id": v["old_copy_run"],
                    "tree_sha256": v["old_tree_sha256_source"],
                },
                {
                    "role": "new(final)",
                    "run_id": v["new_copy_run"],
                    "tree_sha256": v["new_tree_sha256_source"],
                },
            ],
            "result": v["result"],
            "old_before": v["old_before"],
            "old_after": v["old_after"],
            "new_before": v["new_before"],
            "new_after": v["new_after"],
        }
        if scenario == "collision":
            base["stopped_before_choice"] = v["stopped_before_choice"]
        else:
            base["copied_hash_match"] = v["copied_hash_match"]
            base["old_preserved"] = v["old_preserved"]
        out[scenario] = base
    return out


def proc_summary(session):
    processes = session["inspect_stable"]["processes"]
    return {
        "processes": [
            {
                k: p[k]
                for k in (
                    "role",
                    "pid",
                    "created",
                    "session_id",
                    "elevated",
                    "identity",
                )
            }
            | {
                "visible_windows": [
                    (w["title"], w["class"]) for w in p["windows"] if w["visible"]
                ]
            }
            for p in processes
        ],
        "foreground": session["inspect_stable"]["foreground"],
        "stop": session["stop"],
        "stop_diagnostics": session["stop_diagnostics"],
        "verify_after": session["verify_after"],
        "source_unchanged": session["source_unchanged"],
        "owner_probe_after": session["owner_after"],
    }


NO_NOTICE = (
    "通知の文言・内部DEBUGログから障害の分類を推測しない。通知/操作時点の人手観測は06-05-02で行う。"
    "ここでは外部lock/tmp/hashの成立と、実EXEが当該条件下で起動・終了した事実だけを記録する"
)


def build_faults(t2):
    s = t2["fault_sessions"]
    exe = s["X01"]["binary_sha256"]
    faults = {}

    x1 = s["X01"]
    faults["X01"] = {
        "established": x1["fault_records"]["missing"]["established"],
        "method": "設定ファイルを置かない隔離copy(overlayで不存在を宣言)を未改変EXEで起動",
        "run_id": x1["run_id"],
        "binary_sha256": x1["binary_sha256"],
        "observed_at": x1["observed_at"],
        "observation": {
            "settings_absent_until_stable": x1["hash_before"][SETTINGS] is None
            and x1["hash_stable"][SETTINGS] is None,
            "settings_after_exit_sha256": x1["hash_after_exit"][SETTINGS],
            "after_exit_note": "終了時の正当なwindow保存による作成(別時点。失敗としない)",
            "fault_record": x1["fault_records"]["missing"],
            **proc_summary(x1),
            "note": NO_NOTICE,
        },
    }

    x2 = s["X02"]
    faults["X02"] = {
        "established": x2["fault_records"]["corrupt"]["established"]
        and not x2["fault_records"]["corrupt"]["json_parseable"],
        "method": "閉じていない不正JSONを隔離copyに配置(overlay宣言)して未改変EXEを起動",
        "run_id": x2["run_id"],
        "binary_sha256": x2["binary_sha256"],
        "observed_at": x2["observed_at"],
        "observation": {
            "original_before": x2["hash_before"][SETTINGS],
            "original_stable": x2["hash_stable"][SETTINGS],
            "original_after": x2["hash_after_exit"][SETTINGS],
            "json_parseable": x2["fault_records"]["corrupt"]["json_parseable"],
            "fault_record": x2["fault_records"]["corrupt"],
            **proc_summary(x2),
            "note": NO_NOTICE,
        },
    }

    x3 = s["X03"]
    rec3 = x3["fault_records"]["unreadable"]
    probe3 = x3["probe_during_run"]
    faults["X03"] = {
        "established": rec3["established"] is True
        and probe3["ok"] is False
        and probe3["win32_error"] == S.ERROR_SHARING_VIOLATION,
        "method": "観測側がCreateFileW(共有なし)で設定を保持。EXE稼働中も同等openがERROR_SHARING_VIOLATION(32)で拒否される外部probe",
        "run_id": x3["run_id"],
        "binary_sha256": x3["binary_sha256"],
        "observed_at": x3["observed_at"],
        "observation": {
            "holder": {
                "pid": rec3["observer"]["pid"],
                "created": rec3["observer"]["created"],
                **rec3["handle"],
            },
            "probe_denied": probe3["ok"] is False
            and probe3["win32_error"] == S.ERROR_SHARING_VIOLATION,
            "probe_during_run": probe3,
            "probe_before_launch": rec3["probe_read"],
            "original_before": x3["hash_before_effective"][SETTINGS],
            "original_stable": x3["hash_stable_effective"][SETTINGS],
            "original_after": x3["hash_after_exit"][SETTINGS],
            "holder_hash_after_exit": x3["holder_hash_after_exit"],
            **proc_summary(x3),
            "note": NO_NOTICE,
        },
    }

    w, r = s["X04-write"], s["X04-replace"]
    recw, recr = w["fault_records"]["save-write"], r["fault_records"]["save-replace"]
    write_denied = recw["tmp"]["exclusive_create_collision"] is True
    replace_denied = (
        r["probe_delete_during_run"]["ok"] is False
        and r["probe_delete_during_run"]["win32_error"] == S.ERROR_SHARING_VIOLATION
        and r["probe_read_during_run"]["ok"] is True
    )
    faults["X04"] = {
        "established": bool(
            recw["established"]
            and recr["established"]
            and write_denied
            and replace_denied
        ),
        "method": "write: 同名.tmpを先置きして排他作成(open x)の衝突を作る / replace: 設定を共有(DELETE除く)handleで保持しDELETE openが32で拒否される外部probe",
        "run_id": w["run_id"],
        "binary_sha256": w["binary_sha256"],
        "observed_at": w["observed_at"],
        "observation": {
            "holder": {
                "pid": recw["observer"]["pid"],
                "created": recw["observer"]["created"],
                "role": "tmp所有者/handle保持者(観測側)",
            },
            "probe_denied": bool(write_denied and replace_denied),
            "write": {
                "run_id": w["run_id"],
                "tmp_collision": recw["tmp"],
                "tmp_during_run": w["tmp_during_run"],
                "settings_before": w["hash_before_effective"][SETTINGS],
                "settings_after": w["hash_after_exit"][SETTINGS],
                "tmp_after_exit": w["hash_after_exit"][S.SETTINGS_NAME + ".tmp"],
                "note": recw["note"],
                **proc_summary(w),
            },
            "replace": {
                "run_id": r["run_id"],
                "handle": recr["handle"],
                "probe_delete_denied": r["probe_delete_during_run"],
                "probe_read_ok": r["probe_read_during_run"],
                "settings_before": r["hash_before_effective"][SETTINGS],
                "settings_after": r["hash_after_exit"][SETTINGS],
                "holder_hash_after_exit": r["holder_hash_after_exit"],
                **proc_summary(r),
            },
            "stop_fact": (
                "write/replace とも WM_CLOSE 後12秒以内にprocessが終わらず、診断保存後に所有handleで終了した(stop.result=terminated)。"
                "これは外部で観測した事実であり、製品が保存失敗後の終了で確認を保留する仕様どおりかの判定は06-05-02の人手行で行う"
            ),
            "note": NO_NOTICE
            + "。write(書込開始前の失敗)とreplaceは別条件で、通知文が同じでも同一原因とみなさない",
        },
    }

    x5 = s["X05"]
    rec5w, rec5u = x5["fault_records"]["save-write"], x5["fault_records"]["unreadable"]
    probe5 = x5["probe_during_run"]
    faults["X05"] = {
        "established": bool(
            rec5w["established"]
            and rec5u["established"]
            and probe5["ok"] is False
            and probe5["win32_error"] == S.ERROR_SHARING_VIOLATION
            and x5["tmp_during_run"]["exists"]
        ),
        "method": "X03(読込不能)とX04 write(tmp衝突)を同時に保持した隔離copyを未改変EXEで起動。FIFO・再構築・終了D19/D20の操作観測は06-05-02の人手行",
        "run_id": x5["run_id"],
        "binary_sha256": x5["binary_sha256"],
        "observed_at": x5["observed_at"],
        "observation": {
            "holder": {
                "pid": rec5u["observer"]["pid"],
                "created": rec5u["observer"]["created"],
                **rec5u["handle"],
            },
            "probe_denied": probe5["ok"] is False
            and probe5["win32_error"] == S.ERROR_SHARING_VIOLATION,
            "probe_during_run": probe5,
            "tmp_during_run": x5["tmp_during_run"],
            "tmp_collision": rec5w["tmp"],
            "settings_before": x5["hash_before_effective"][SETTINGS],
            "settings_stable": x5["hash_stable_effective"][SETTINGS],
            "settings_after": x5["hash_after_exit"][SETTINGS],
            "holder_hash_after_exit": x5["holder_hash_after_exit"],
            "tmp_after_exit": x5["hash_after_exit"][S.SETTINGS_NAME + ".tmp"],
            **proc_summary(x5),
            "note": NO_NOTICE,
        },
    }
    return faults


def load_session(path):
    data = json.loads(Path(path).read_text("utf-8"))
    if data.get("selftest"):
        raise SystemExit(f"selftestの記録は証拠にできません: {path}")
    if data.get("error") or data.get("interrupted") or data.get("outcome"):
        raise SystemExit(
            f"完了していないsessionです: {path}: {data.get('error') or data.get('outcome') or 'interrupted'}"
        )
    return data


def last_answer(session):
    items = session["user_inputs"]
    if not items or not items[-1]["text"].strip():
        raise SystemExit("利用者の最終回答がありません")
    return items[-1]["text"]


def build_connection(session, kind):
    run = Path(session["run"])
    entry = S.build_connection_entry(
        run, session["server_summary"], user_answer=last_answer(session), kind=kind
    )
    entry["session_file"] = str(
        run / "evidence" / f"session-{kind.replace('ocr-single', 'ocr-single')}.json"
    )
    entry["user_inputs"] = session["user_inputs"]
    entry["expected_text"] = session.get("expected_text")
    entry["peer"] = session.get("peer")
    entry["peer_error"] = session.get("peer_error")
    entry["steps"] = session["steps"]
    entry["stop"] = session.get("stop")
    entry["verify_after"] = session.get("verify_after")
    entry["owner_after"] = session.get("owner_after")
    entry["hold_limit_seconds"] = session.get("hold_limit_seconds")
    entry["provider_timeout_seconds"] = session.get("provider_timeout_seconds")
    entry["settings_keys"] = session.get("settings_keys")
    entry["pdf"] = session.get("pdf")
    entry["summary_executed"] = False
    entry["target_pages"] = 1
    entry["ocr_concurrency"] = 1
    if kind == "w05b-modal":
        main_pid = S.load_run(run)["processes"][0]["pid"]
        before = session.get("modal_windows_before_peer") or []
        after = session.get("modal_windows_after_peer") or []
        modal_before = [w for w in before if w["visible"] and w["class"] == "#32770"]
        modal_after = [w for w in after if w["visible"] and w["class"] == "#32770"]
        fg = session.get("foreground_after_peer") or {}
        steps = {st["step"]: st for st in session["steps"]}
        windows_no = (steps.get("answered-no") or {}).get("windows") or {}
        primary_windows = [
            w
            for k, ws in windows_no.items()
            if k.startswith("primary:")
            for w in ws
            if w["visible"]
        ]
        entry["modal_shown"] = bool(modal_before)
        entry["peer_returned_to_modal"] = bool(
            modal_before
            and modal_after
            and {w["hwnd"] for w in modal_before} & {w["hwnd"] for w in modal_after}
            and fg.get("pid") == main_pid
        )
        entry["answered_no"] = bool(
            modal_before
            and not any(w["class"] == "#32770" for w in primary_windows)
            and any("OCR" in w["title"] for w in primary_windows)
        )
        ev = [e["event"] for e in session["server_summary"]["events"]]
        entry["same_request_completed"] = (
            ev.count("received") == 1
            and ev.count("released") == 1
            and ev.count("completed") == 1
        )
        entry["derivation"] = {
            "modal_before_peer": modal_before,
            "modal_after_peer": modal_after,
            "foreground_after_peer": fg,
            "primary_windows_after_no": primary_windows,
            "rule": (
                "modal_shown=peer前にprimaryのvisible #32770がある / peer_returned_to_modal=同hwndがpeer後も存在かつforegroundがprimary / "
                "answered_no=modal消失かつOCR windowが残存 / same_request_completed=server 1受信・1解放・1完了"
            ),
        }
    return entry


def _collect_runs(ev, prefix):
    labels = {}
    for item in ev.get("protection_stop", []):
        labels[item["run_id"]] = f"{prefix}保護停止 {item['name']}"
    for case in ev.get("launch", {}).get("cases", []):
        labels[case["run_id"]] = f"{prefix}起動時保持 {case['name']}"
    for scenario, v in ev.get("update", {}).items():
        for c in v["copies"]:
            labels[c["run_id"]] = f"{prefix}更新 {scenario} {c['role']}"
    for item in ev.get("connection", []):
        labels[item["run_id"]] = f"{prefix}接続実証 {item['kind']}"
    for fid, v in ev.get("faults", {}).items():
        labels[v["run_id"]] = f"{prefix}障害 {fid}"
        obs = v["observation"]
        for sub in ("write", "replace"):
            if isinstance(obs.get(sub), dict) and obs[sub].get("run_id"):
                labels[obs[sub]["run_id"]] = f"{prefix}障害 {fid}-{sub}"
    return labels


def build_run_refs(evidence):
    labels = {}
    for gen in evidence.get("previous_generations", []):
        labels.update(
            _collect_runs(gen["evidence"], f"[世代{gen['generation']} superseded] ")
        )
    for item in evidence.get("protection_stop", []):
        labels[item["run_id"]] = f"保護停止 {item['name']}"
    for case in evidence.get("launch", {}).get("cases", []):
        labels[case["run_id"]] = f"起動時保持 {case['name']}"
    for scenario, v in evidence.get("update", {}).items():
        for c in v["copies"]:
            labels[c["run_id"]] = f"更新 {scenario} {c['role']}"
    for item in evidence.get("connection", []):
        labels[item["run_id"]] = f"接続実証 {item['kind']}"
    for fid, v in evidence.get("faults", {}).items():
        labels[v["run_id"]] = f"障害 {fid}"
        obs = v["observation"]
        for sub in ("write", "replace"):
            if isinstance(obs.get(sub), dict) and obs[sub].get("run_id"):
                labels[obs[sub]["run_id"]] = f"障害 {fid}-{sub}"
    return labels


def patch_prep(evidence):
    text = PREP.read_text("utf-8")
    labels = build_run_refs(evidence)
    lines = [MARK_START, "", "| run-ref | 用途 |", "|---|---|"]
    for run_id, label in labels.items():
        lines.append(f"| run-ref: {run_id} | {label} |")
    lines += ["", MARK_END]
    block = "\n".join(lines)
    if MARK_START in text:
        text = re.sub(
            re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
            lambda _m: block,
            text,
            flags=re.S,
        )
    else:
        raise SystemExit("UAT-PREPARATION.md に run-refs マーカーがありません")
    PREP.write_text(text, encoding="utf-8", newline="\n")
    return labels


def previous_generations():
    """世代1(78dcfe8時点)の証拠を原文のまま保持する。再実行時は既存の保持分を引き継ぐ。"""
    cur = json.loads(EVIDENCE.read_text("utf-8")) if EVIDENCE.exists() else None
    if cur is None:
        return []
    if cur.get("generation") == 2:
        return cur["previous_generations"]
    return [
        {
            "generation": 1,
            "status": "superseded",
            "superseded_reason": (
                "接続実証(06-04-02 human-check)で製品バグ発見: ocr_provider=ollama でも"
                "OCRダイアログがLM Studio(localhost:1234)へ送信。製品修正(52258de/7fb41a2)後、"
                "06-03 resume_contract に従い build/保護/接続を新世代で取り直した"
            ),
            "evidence_commit": "78dcfe8",
            "raw_observation_log": GEN1_RAW_T2,
            "old_t2_dir_preserved": (
                r"C:\Users\shdwf\AppData\Local\Temp\pf06_t2_f157d1e5a0454f7e89c363383182dff5"
            ),
            "failed_connection_attempts": [
                {
                    "attempt_run": "release-uat-c75a19aa09b84f1788c0dee965915dd7",
                    "kind": "ocr-single",
                    "status": "not-established",
                    "reason": (
                        "利用者がLLM設定でOllama->Geminiへ変更。ダイアログ表示は『ollama』のまま、"
                        "合成サーバーは要求0件、結果欄に画像の文字『PageFolio UAT / OCR TEST "
                        "0123456789』(実Geminiによる読取とみられる。送信は合成画像のみ)。"
                        "表示と実送信先の不一致。成立と記録しない"
                    ),
                },
                {
                    "attempt_run": "release-uat-034578b2c4b94c2aae9fa70afe620d25",
                    "kind": "ocr-single",
                    "status": "not-established",
                    "reason": (
                        "ocr_provider=ollama / ollama_url=http://127.0.0.1:17327 だが読取実行で"
                        "『LM Studio に接続できませんでした。URL: http://localhost:1234 … "
                        "[WinError 10061]』。製品バグ(_start_ocr がlm_studio_urlを渡し、"
                        "OCRDialog実行時再生成がurl_varでOllamaProviderを作る)。成立と記録しない"
                    ),
                },
            ],
            "evidence": cur,
        }
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t2", required=True)
    ap.add_argument("--ocr-session")
    ap.add_argument("--w05b-session")
    ap.add_argument("--accept-user-answers", action="store_true")
    ap.add_argument(
        "--supplement-json",
        help=(
            "接続行への補足(connection_supplements: kind->追記dict)と世代2の不成立試行"
            "(failed_connection_attempts)。既存キーの上書きは拒否する(生記録を弱めない)"
        ),
    )
    ap.add_argument(
        "--extra-json",
        help="証拠へ追記する最上位キー(connection_preflight, verification 等)のJSON",
    )
    args = ap.parse_args()
    t2_path = Path(args.t2) / "t2-result.json"
    t2 = json.loads(t2_path.read_text("utf-8"))
    build = S.read_json(PHASE / "06-BUILD-EVIDENCE.json")
    final = build["final_release"]
    final_run = [r for r in final["runs"] if r["order"] == "rebuild"][0]["run_id"]
    prev = previous_generations()
    evidence = {
        "generation": 2,
        "previous_generations": prev,
        "generation_note": (
            "製品修正(52258de/7fb41a2)後の新世代。世代1(78dcfe8)の証拠は"
            "previous_generationsへ原文保持し、上書きしない"
        ),
        "version": final.get("version") or build.get("version"),
        "status": "partial-pending-human-check",
        "release_allowed": False,
        "purpose_note": "build/保護/起動/更新/障害は自動実測。接続実証(connection)は利用者の回答を得るまで成立済みにしない",
        "build_ref": {
            "final_run_id": final_run,
            "exe_sha256": final["exe_sha256"],
            "tree_sha256": final["tree_sha256"],
        },
        "raw_observation_log": RAW_T2,
        "protection_stop": build_protection_stop(t2),
        "launch": build_launch(t2),
        "update": build_update(t2),
        "connection": [],
        "connection_pending": ["ocr-single", "w05b-modal"],
        "faults": build_faults(t2),
    }
    supplement = (
        json.loads(Path(args.supplement_json).read_text("utf-8"))
        if args.supplement_json
        else {}
    )
    for flag, kind in (
        (args.ocr_session, "ocr-single"),
        (args.w05b_session, "w05b-modal"),
    ):
        if not flag:
            continue
        if not args.accept_user_answers:
            raise SystemExit(
                "接続の記録には --accept-user-answers(回答を人が確認したことの明示)が必要です"
            )
        entry = build_connection(load_session(flag), kind)
        for key, value in (
            (supplement.get("connection_supplements") or {}).get(kind, {}).items()
        ):
            if key in entry:
                raise SystemExit(f"補足が既存キーを上書きします: {kind}.{key}")
            entry[key] = value
        evidence["connection"].append(entry)
        evidence["connection_pending"].remove(kind)
    if supplement.get("failed_connection_attempts"):
        evidence["failed_connection_attempts"] = supplement[
            "failed_connection_attempts"
        ]
    if not evidence["connection_pending"]:
        evidence["status"] = "complete"
        del evidence["connection_pending"]
    override = supplement.get("status_override")
    if override:
        # 機械判定の結果を人が読みで覆すためには使えない。completeより弱い状態への格下げ専用
        if override["status"] == "complete":
            raise SystemExit("status_override は complete にできません(格下げ専用)")
        evidence["status"] = override["status"]
        evidence["status_reason"] = override["reason"]
    if args.extra_json:
        evidence.update(json.loads(Path(args.extra_json).read_text("utf-8")))
    S.write_json(EVIDENCE, evidence)
    labels = patch_prep(evidence)
    print(
        f"wrote {EVIDENCE} ({len(labels)} runs referenced) status={evidence['status']}"
    )


if __name__ == "__main__":
    main()
