"""保存失敗時の画面維持を未判定として保持し、未実施の外部障害観測だけを続行。"""

import json
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
T2 = Path(
    "C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g4_07447e7e5cfc42988b80fb84c58293ae"
)
driver = HERE / "06-04-drivers/t2_driver.py"
sys.argv = [str(driver), str(T2), "faults"]
scope = runpy.run_path(str(driver), run_name="g4_resume")
data = scope["load"]()
if "fault_sessions" in data:
    raise RuntimeError("fault_sessions already recorded")
names = {
    "fault-x01-missing": "X01",
    "fault-x02-corrupt": "X02",
    "fault-x03-unreadable": "X03",
    "fault-x04-save-write": "X04-write",
}
sessions = {}
for p in T2.glob("g4-attempt-*.json"):
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec["case"] in names:
        key = names[rec["case"]]
        if key in sessions:
            raise RuntimeError("duplicate attempt: " + key)
        sessions[key] = rec
if set(sessions) != set(names.values()):
    raise RuntimeError("missing original observations")


def validate(rec):
    if rec["owner_after"] or not rec["source_unchanged"]:
        raise RuntimeError("owner/source invariant failed")
    if rec["hash_before_effective"] != rec["hash_stable_effective"]:
        raise RuntimeError("protected content changed during startup")
    if any(p["result"] not in ("closed", "terminated") for p in rec["stop"]):
        raise RuntimeError("cleanup failed")
    # terminated は正常終了/passに変換しない。X04の操作受入は未実施。
    if "save-replace" not in rec["faults"] and "save-write" not in rec["faults"]:
        if any(p["result"] != "closed" for p in rec["stop"]):
            raise RuntimeError("unexpected stop")


for rec in sessions.values():
    validate(rec)
valid = json.dumps({"lang": "ja", "theme": "dark"}).encode("utf-8")
for key, case, faults in (
    ("X04-replace", "fault-x04-save-replace", ("save-replace",)),
    ("X05", "fault-x05-combined", ("save-write", "unreadable")),
):
    rec = scope["hold_session"](
        case, overlays={scope["S"].SETTINGS_NAME: valid}, faults=faults
    )
    with (T2 / ("g4-attempt-" + rec["run_id"] + ".json")).open(
        "x", encoding="utf-8"
    ) as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    validate(rec)
    sessions[key] = rec
    print(key, rec["run_id"], rec["stop"], flush=True)
data["fault_sessions"] = sessions
data["g4_fault_resume_note"] = (
    "最初の追加guardは保存失敗時の初回終了保留(D19)を一律正常終了要求で停止。"
    "X01/X02/X03/X04-writeは再実行せず原記録を採用。"
    "未実施X04-replace/X05のみ続行。強制終了は観測のままで人手受入ではない。"
)
scope["save"](data)
print("fault observations recorded; human acceptance remains not-run", flush=True)
