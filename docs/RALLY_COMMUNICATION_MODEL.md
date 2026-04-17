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
  - stdlib/rally/prompts/rally/memory.prompt
  - stdlib/rally/prompts/rally/review_results.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - skills/rally-kernel/prompts/SKILL.prompt
  - src/rally/cli.py
  - src/rally/adapters/base.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/final_response_loader.py
---

# Summary

Rally uses one simple communication model:

- notes for context
- one final JSON result for control
- one optional generated previous-turn appendix for readback only when the
  compiled contract asks for prior outputs

There is no separate handoff artifact.
There is no second return path.
The final JSON still ends the turn through one shared final-response path after
adapter execution.
Many producer turns use the shared Rally base result plus a flow-local route
field.
Producer routing comes from Doctrine route metadata in
`final_output.contract.json`.
The shared base result also carries an optional passive `agent_issues` field
for one short issue summary or the literal `none`. It never changes control
flow.
Non-review flows can opt out locally by declaring their own output shape over
the shared schema. That opt-out stays in prompt source, not runtime config.
Review-native turns may use control-ready Doctrine review JSON instead.
Rally also copies that full final JSON into the matching `Rally Turn Result`
block in `home:issue.md`.
When Doctrine emits `io.previous_turn_inputs`, Rally also renders one
`## Previous Turn Inputs` appendix from the exact prior turn artifacts and
injects it beside `AGENTS.md`. That appendix is context only, not control.

# Shipped Rules

- Every Rally-managed agent inherits the shared base agent in `stdlib/rally/prompts/rally/base_agent.prompt`.
- Every Rally-managed agent gets the shared `rally-kernel` skill.
- The shared note path is `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`.
- The shared read-first path is `"$RALLY_CLI_BIN" issue current --run-id "$RALLY_RUN_ID"`.
- Rally injects `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and `RALLY_TURN_NUMBER`.
- A flow may also add extra startup and launch env vars through `runtime.env` in `flow.yaml`.
- `rally.turn_results` is the shared producer base JSON, with five control keys plus optional passive `agent_issues`.
- Flow producer outputs may inherit that base JSON, add a route field, and let
  Doctrine emit the route selector metadata Rally will read.
- A non-review flow can opt out locally by declaring its own output shape over the shared schema instead of using the shared shape-level wording.
- Review-native turns may declare a different final JSON when Doctrine emits control-ready review metadata.
- Notes keep context only. Notes never carry `next_owner`, `done`, `blocker`, or `sleep` truth.
- Notes may carry flat string fields such as `kind=...` or `lane=...` when later turns need stable labels.
- Rally, not the agent, adds the turn number to in-turn note blocks.
- Rally writes `previous_turn_inputs.md` under the current turn only when the
  compiled contract asks for previous-turn readback.

# Shipped Surfaces

- `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared read-first and turn rules
  - required env vars
  - required `rally-kernel` skill
  - shared advisory issue-note output that shells through the Rally CLI
- `stdlib/rally/prompts/rally/memory.prompt`
  - shared memory skill meaning and memory entry shape
- `stdlib/rally/prompts/rally/turn_results.prompt`
  - the shared final JSON contract, authored with Doctrine `output schema`,
    including the optional passive `agent_issues` field for non-review turns
- `stdlib/rally/prompts/rally/review_results.prompt`
  - the shared review final JSON family for review-native turns
- `flows/_stdlib_smoke/prompts/AGENTS.prompt`
  - the shipped local non-review opt-out proof surface
  - `SmokeTurnResultJson` reuses the shared schema while keeping local final-output wording
- `skills/rally-kernel/SKILL.md`
  - teaches note procedure and note examples
- `src/rally/cli.py`
  - ships `rally issue current` for the bounded shared read path
  - ships `rally issue note`, including repeatable `--field key=value`
- `src/rally/services/issue_ledger.py`
  - owns the bounded current view, note append, flat note-field header lines, issue-history snapshots, Markdown `---` dividers, and optional turn labels
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
- inspect shared-default readback plus the `_stdlib_smoke` opt-out readback
- inspect emitted `AGENTS.md`, emitted schema files under `schemas/`, and
  `final_output.contract.json`
- inspect `home/sessions/<agent>/turn-<n>/previous_turn_inputs.md` when the
  flow uses previous-turn inputs
- run the focused Rally unit tests for note writes, shared launch-env setup,
  flow loading, and turn-result parsing

# Canonical Homes

Use these docs as the live design set:

- `docs/RALLY_MASTER_DESIGN.md`
- `docs/RALLY_RUNTIME.md`

Treat older planning notes as history only.
