---
title: "Rally - Phase 3 Communication Pivot"
date: 2026-04-13
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_status
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - skills/rally-kernel/SKILL.md
  - src/rally/cli.py
  - src/rally/services/issue_ledger.py
  - src/rally/adapters/codex/launcher.py
---

# Summary

Phase 3 changed Rally to one simple communication model:

- notes for context
- one final JSON result for control

There is no separate handoff artifact.
There is no second return path.

# Shipped Rules

- Every Rally-managed agent inherits the shared base agent in `stdlib/rally/prompts/rally/base_agent.prompt`.
- Every Rally-managed agent gets the shared `rally-kernel` skill.
- The shared note path is `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`.
- Rally injects `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
- `rally.turn_results` is the only shared control shape for `handoff`, `done`, `blocker`, and `sleep`.
- Notes keep context only. Notes never carry `next_owner`, `done`, `blocker`, or `sleep` truth.

# Shipped Surfaces

- `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared Rally rules
  - required env vars
  - required `rally-kernel` skill
  - shared advisory issue-note output
- `stdlib/rally/prompts/rally/notes.prompt`
  - one shared note output that shells through the Rally CLI
- `stdlib/rally/prompts/rally/turn_results.prompt`
  - one shared final JSON contract
- `skills/rally-kernel/SKILL.md`
  - teaches when to leave a note and how to end a turn with valid JSON
- `src/rally/cli.py`
  - ships `rally issue note`
- `src/rally/services/issue_ledger.py`
  - owns note append and issue-history snapshots
- `src/rally/adapters/codex/launcher.py`
  - builds the required launch env map

# Doctrine Note

Rally does not ship a shared file-state carrier.

Some authored reviews may still use local Doctrine review-state syntax when the
compiler requires it.
That is local review syntax.
It is not a Rally communication path.

# Proof

The Phase 3 proof path is:

- rebuild the affected flows with the paired Doctrine compiler into `flows/*/build/agents/*`
- inspect emitted `AGENTS.md` and `AGENTS.contract.json`
- run the focused Rally unit tests for note writes, launcher env setup, flow loading, and turn-result parsing

# Live Truth

Use these docs as the live design set:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`

Treat older planning notes as history only.
