---
title: "Rally - Base Agent And Final Output Pivot"
date: 2026-04-13
status: archived
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: archived_plan
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
---

# Archived Plan

This file is kept as planning history only.
It is not live design truth.

# Outcome

This plan led to the current Rally shape:

- one shared Rally base agent
- one shared note path through `rally-kernel` and `rally issue note`
- one final JSON result for control
- one launch env contract with `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`,
  `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`

The older shared file-state idea from early drafts did not ship as a Rally-owned surface.

# Live Truth

Use these docs instead:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
