---
title: "Rally Communication Model"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - skills/rally-kernel/SKILL.md
  - src/rally/cli.py
  - src/rally/adapters/base.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/final_response_loader.py
---

# Summary

Rally uses one simple communication model:

- notes for context
- one final JSON result for control

There is no separate handoff artifact.
There is no second return path.
The final JSON still ends the turn through one shared final-response path after
adapter execution.
Many turns use one flat five-key object.
Review-native turns may use control-ready Doctrine review JSON instead.
Rally also copies that full final JSON into the matching `Rally Turn Result`
block in `home:issue.md`.

# Shipped Rules

- Every Rally-managed agent inherits the shared base agent in `stdlib/rally/prompts/rally/base_agent.prompt`.
- Every Rally-managed agent gets the shared `rally-kernel` skill.
- The shared note path is `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`.
- Rally injects `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and `RALLY_TURN_NUMBER`.
- A flow may also add extra startup and launch env vars through `runtime.env` in `flow.yaml`.
- `rally.turn_results` is the classic shared five-key control JSON.
- Review-native turns may declare a different final JSON when Doctrine emits control-ready review metadata.
- Notes keep context only. Notes never carry `next_owner`, `done`, `blocker`, or `sleep` truth.
- Notes may carry flat string fields such as `kind=...` or `lane=...` when later turns need stable labels.
- Rally, not the agent, adds the turn number to in-turn note blocks.

# Shipped Surfaces

- `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared Rally rules
  - required env vars
  - required `rally-kernel` skill
  - shared advisory issue-note output
- `stdlib/rally/prompts/rally/notes.prompt`
  - one shared note output that shells through the Rally CLI
- `stdlib/rally/prompts/rally/turn_results.prompt`
  - the classic shared final JSON contract
- `skills/rally-kernel/SKILL.md`
  - teaches when to leave a note, when to add flat note fields, and how to end a turn with the declared final JSON
- `src/rally/cli.py`
  - ships `rally issue note`, including repeatable `--field key=value`
- `src/rally/services/issue_ledger.py`
  - owns note append, flat note-field header lines, issue-history snapshots, Markdown `---` dividers, and optional turn labels
- `src/rally/adapters/base.py`
  - builds the shared Rally launch env map, including the active turn number for note labeling
- `src/rally/services/final_response_loader.py`
  - keeps one shared final JSON read path after adapter execution

# Doctrine Note

Some authored reviews may still use local Doctrine review-state syntax when the
compiler requires it.
That is local review syntax.
It is not a Rally communication path.

Rally now may also read a review-native final JSON directly when Doctrine marks
it control-ready.
That still stays on the same one final-return path.

# Proof

The proof path is:

- rebuild the affected flows with the paired Doctrine compiler into `flows/*/build/agents/*`
- inspect emitted `AGENTS.md` and `AGENTS.contract.json`
- run the focused Rally unit tests for note writes, shared launch-env setup,
  flow loading, and turn-result parsing

# Canonical Homes

Use these docs as the live design set:

- `docs/RALLY_MASTER_DESIGN.md`
- `docs/RALLY_RUNTIME.md`

Treat older planning notes as history only.
