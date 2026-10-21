---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-10-21T16:38:49.068Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | tests/test_pdf_ops.py |  | merge_undo pin test assertion target corrected from PLAN.md's stated app._redo_stack[-1] to app._undo_stack[-1] (mechanically the only reachable stack); verification intent unchanged (see 01-06-SUMMARY.md Deviations) | fixed |  | 2026-08-10T14:40:54.388Z | 2026-08-10T14:41:14.203Z |
| 2 | 04 | deviation | .planning/phases/04-startup-control/04-05-SUMMARY.md |  | 承認済み再計画によりW人手最終受入をPhase6へ移管。全必須passまでリリース停止。 | open |  | 2026-10-21T16:38:49.068Z |  |

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
  }
]
````
