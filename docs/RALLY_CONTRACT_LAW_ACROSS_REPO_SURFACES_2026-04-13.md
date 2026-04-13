---
title: "Rally - Contract Law Across Repo Surfaces"
date: 2026-04-13
status: archived
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: archived_analysis
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
---

# Archived Analysis

This file captured an earlier repo audit.
It is kept for history only.

Live Rally truth is simpler now:

- prompts live under `flows/*/prompts/**` and `stdlib/rally/prompts/**`
- generated readback lives under `flows/*/build/**`
- notes are context only
- final JSON is the only control path
- Rally loads `AGENTS.contract.json`, not a second sidecar format

Use the live design docs for current repo law.
