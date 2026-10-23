---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 2
total_count: 4
last_updated: 2026-10-23T17:37:48.421Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | tests/test_pdf_ops.py |  | merge_undo pin test assertion target corrected from PLAN.md's stated app._redo_stack[-1] to app._undo_stack[-1] (mechanically the only reachable stack); verification intent unchanged (see 01-06-SUMMARY.md Deviations) | fixed |  | 2026-08-10T14:40:54.388Z | 2026-08-10T14:41:14.203Z |
| 2 | 04 | deviation | .planning/phases/04-startup-control/04-05-SUMMARY.md |  | 承認済み再計画によりW人手最終受入をPhase6へ移管。全必須passまでリリース停止。 | open |  | 2026-10-21T16:38:49.068Z |  |
| 3 | 05 | unrun-verify | .planning/phases/05-config-notification/05-UAT.md |  | H01〜H12の利用者目視は未実施、禁止2件flagged-unverifiedを維持 | fixed |  | 2026-10-23T16:02:16.669Z | 2026-10-23T16:44:41.673Z |
| 4 | 05 | unrun-verify | .planning/phases/05-config-notification/05-VERIFICATION.md |  | 独立検証human_needed。通知をPDF編集内容の喪失と誤認させない／PDF破棄や再起動を促さない禁止2件の項目別判断待ち。既存H01-H14は14 pass、再実施不要 | open |  | 2026-10-23T17:37:48.421Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "01",
    "file": "tests/test_pdf_ops.py",
    "line": null,
    "description": "merge_undo pin test assertion target corrected from PLAN.md's stated app._redo_stack[-1] to app._undo_stack[-1] (mechanically the only reachable stack); verification intent unchanged (see 01-06-SUMMARY.md Deviations)",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-10T14:40:54.388Z",
    "resolved_at": "2026-08-10T14:41:14.203Z"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "04",
    "file": ".planning/phases/04-startup-control/04-05-SUMMARY.md",
    "line": null,
    "description": "承認済み再計画によりW人手最終受入をPhase6へ移管。全必須passまでリリース停止。",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-21T16:38:49.068Z",
    "resolved_at": null,
    "milestone": "v1.10.0"
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "05",
    "file": ".planning/phases/05-config-notification/05-UAT.md",
    "line": null,
    "description": "H01〜H12の利用者目視は未実施、禁止2件flagged-unverifiedを維持",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-23T16:02:16.669Z",
    "resolved_at": "2026-10-23T16:44:41.673Z",
    "milestone": "v1.10.0"
  },
  {
    "id": 4,
    "kind": "unrun-verify",
    "phase": "05",
    "file": ".planning/phases/05-config-notification/05-VERIFICATION.md",
    "line": null,
    "description": "独立検証human_needed。通知をPDF編集内容の喪失と誤認させない／PDF破棄や再起動を促さない禁止2件の項目別判断待ち。既存H01-H14は14 pass、再実施不要",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-23T17:37:48.421Z",
    "resolved_at": null,
    "milestone": "v1.10.0"
  }
]
````
