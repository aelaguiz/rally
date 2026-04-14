---
title: "Rally - Hermes Adapter Runtime Generalization"
date: 2026-04-13
status: archived
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: archived_plan
related:
  - docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
---

# Archived Plan

This file is kept only as plan history.
It is not a source of live runtime truth.

Why it is archived:

- the shared adapter-boundary work it argued for is now shipped
- the live runtime now supports `codex` and `claude_code`
- the old Hermes plan still taught a future pre-cutover runtime shape that no
  longer matches the code
- no Hermes adapter is shipped in this repo today

Use these files for the current runtime truth:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`

If Hermes work is reopened later, start from the current shared adapter
boundary in the live docs above instead of reviving the old future-runtime plan
in this file.
