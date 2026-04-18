---
title: "Turn Result Contract"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_PRINCIPLES.md
  - stdlib/rally/prompts/rally/turn_results/AGENTS.prompt
  - stdlib/rally/prompts/rally/review_results/AGENTS.prompt
---

# Turn Result Contract

Every non-review turn in Rally ends with one final JSON object. This
document is the canonical definition of that object: the four kinds it
can take, the five required base keys, the optional passive
diagnostics field, how routing works, and how the review verdict
contract differs.

The stdlib source is
[`stdlib/rally/prompts/rally/turn_results/AGENTS.prompt`](../stdlib/rally/prompts/rally/turn_results/AGENTS.prompt).
The review verdict source is
[`stdlib/rally/prompts/rally/review_results/AGENTS.prompt`](../stdlib/rally/prompts/rally/review_results/AGENTS.prompt).

## The Four Kinds

Every non-review turn emits exactly one of four `kind` values:

| Kind       | Meaning                                                 | Required extras                                  |
| ---------- | ------------------------------------------------------- | ------------------------------------------------ |
| `handoff`  | Pass control to another agent in the same flow.         | `next_owner` (route selector).                   |
| `done`     | The flow is complete on this run.                       | `summary` (short prose).                         |
| `blocker`  | Cannot proceed. Human or upstream needs to act.         | `reason` (short prose).                          |
| `sleep`    | Pause this agent for a fixed duration, then resume.     | `reason` and `sleep_duration_seconds >= 1`.      |

Rally routes on `kind`. A turn result with any other value fails validation.

## The Five Required Base Keys

Every non-review turn result carries the same five top-level keys. Missing
any one is a hard parse error. They live in
`BaseRallyTurnResultSchema`:

- **`kind`** — one of `handoff`, `done`, `blocker`, `sleep`.
- **`next_owner`** — route selector. `null` on `done`, `blocker`, `sleep`.
- **`reason`** — short prose. Required on `blocker` and `sleep`. `null`
  on `handoff` and `done`.
- **`sleep_duration_seconds`** — int `>= 1` on `sleep`. `null` otherwise.
- **`summary`** — short prose. Required on `done`. Optional elsewhere.

Always send every control field. Use `null` for fields that do not apply
to the current kind. Domain fields (`revision_goal`, `reviewed_artifact`,
whatever your agent produces) extend the schema beyond these five, as
typed siblings on the schema — not as prose smuggled into `summary`.

## The Optional `agent_issues` Field

`agent_issues` is passive diagnostics. It is a free-form string or the
literal `"none"`. It does not alter routing or the turn's kind. Rally
collects it into the run log for later inspection.

Use `agent_issues` when the agent wants to surface a non-blocking concern
(a warning, a doubt, a suggestion for the operator) without changing
control flow. Do not use it for anything load-bearing.

## The Route Field

On `handoff`, `next_owner` names the next agent by its **short name** —
the bare name from the `flow.yaml` `agents:` map, not a dotted locator.

The route-selector shape is authored with `route field next_route:`. Each
member maps a short name to a compiled Doctrine agent name:

```
route field next_route: "Next Route"
    architect_reviewer: "Send the issue to ArchitectReviewer." -> ArchitectReviewer
    nullable
    note: "Use null only when the turn blocks or sleeps."
```

Rally's contract loader validates that each short name maps to exactly
one agent in the flow. A mismatch fails load with a clear error.

## The Review Verdict Contract

Review turns parse differently from producer turns. The schema is
`BaseRallyReviewFinalResponseSchema`. A review turn result carries:

- **`verdict`** — `accept` or `changes_requested`.
- **`reviewed_artifact`** — what the reviewer looked at.
- **`analysis_performed`** — short prose naming what checks ran.
- **`findings_first`** — the readback Rally surfaces next.
- **`current_artifact`** — what the next owner must work from.
- **`failure_detail.blocked_gate`**,
  **`failure_detail.failing_gates`** — only when `verdict` is
  `changes_requested`.
- **`next_owner`** — short-name route selector, like non-review turns.

Rally's runtime exposes reviewed state as `LoadedReviewTruth`. Downstream
agents see `reviewed_artifact`, `analysis`, `current_artifact`,
`next_owner`, and any blocked / failing gates — all typed, all loaded
from the review JSON.

## Local Override Pattern

When a specific agent needs a narrower schema (for example, one where
`next_owner` is never null), override the base schema in the flow's
shared prompt and point the agent's `final_output` at the override.

The base shape in
`stdlib/rally/prompts/rally/turn_results/AGENTS.prompt` uses
`inherit {kind, summary, reason, sleep_duration_seconds, agent_issues}`.
A flow-local override can tighten any of those, add fields, or constrain
the route field.

See `flows/poem_loop/prompts/AGENTS.prompt` for `MuseTurnResultSchema`,
`PoemWriterTurnResultSchema`, and `PoemCriticTurnResultSchema` — three
role-specific overrides that all inherit from the stdlib base.

## What Rally Validates

- The five base keys are present on non-review turns.
- `kind` is one of the four allowed values.
- `next_owner` is a short name that maps to exactly one agent in the flow.
- `sleep_duration_seconds` is `>= 1` on `sleep`, `null` otherwise.
- Review turns parse the verdict contract into `LoadedReviewTruth`.
- Rally rejects a flow whose `final_output` clause points at a schema
  that does not inherit the base.

## Common Mistakes

- Using a dotted locator (`flows.myflow.agents.architect_reviewer`) in
  `next_owner`. Use the short name `architect_reviewer` instead.
- Putting control state into `summary`. `summary` is human-readable
  prose; Rally does not parse it.
- Writing `next_owner: null` on a `handoff`. Use a valid short name.
- Writing `next_owner: "some_agent"` on `done`. Leave it `null`.
- Adding a sixth required base key on every agent. Put domain fields on
  the agent's local override schema instead.

## Related Docs

- [RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md) — notes-are-advisory, final-JSON-is-control.
- [RALLY_COMMUNICATION_MODEL.md](RALLY_COMMUNICATION_MODEL.md) — how turns chain.
- [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md) — how `final_output` is declared on an `agent` block.
