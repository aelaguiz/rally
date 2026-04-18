---
title: "Rally Error Reference"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_PRINCIPLES.md
  - docs/FLOW_YAML_REFERENCE.md
  - docs/TURN_RESULT_CONTRACT.md
  - docs/SKILL_SCOPING.md
  - docs/RALLY_PORTING_GUIDE.md
  - src/rally/cli.py
  - src/rally/services/flow_loader.py
---

# Rally Error Reference

This document catalogs the enduring error categories Rally produces at
load time or runtime. Every entry describes the symptom, the root cause,
and the exact remedy. These are **constraints, not bugs** — Rally fails
loud because the failure points at the right fix.

If your error does not appear here, read the message out loud: Rally
errors are written to name the surface that needs editing.

---

## Active-Run Refusals

Rally enforces one active run per flow via a lock at
`runs/locks/<FLOW_CODE>.lock`. A second run against the same flow is
refused. The refusal message names the current status and the next
move.

| Current status | Remedy                                                                 |
| -------------- | ---------------------------------------------------------------------- |
| `RUNNING`      | `rally stop <id>` to stop it, or wait.                                  |
| `PAUSED`       | `rally resume <id>` to continue, or `rally stop <id>`.                  |
| `SLEEPING`     | Wait. The run wakes automatically when the sleep elapses.               |
| `BLOCKED`      | `rally run <flow> --edit` to acknowledge the blocker and continue.      |
| `CRASHED`      | `rally run <flow> --restart` to reclaim the flow with a fresh run.      |
| `ORPHANED`     | `rally run <flow> --restart` (pid was reused by the OS).                |
| `STOPPED`      | `rally run <flow> --restart` to reclaim the flow.                       |

See [RALLY_BACKGROUND_EXECUTION.md](RALLY_BACKGROUND_EXECUTION.md) for
the reconciled-status table and
[src/rally/cli.py](../src/rally/cli.py) for the refusal surface.

---

## `Unknown stdlib skill: <name>`

Root cause: the agent's `system_skills:` list names a skill that Rally
does not ship. Today Rally ships one opt-in stdlib skill:
`rally-memory`.

Remedy:

- If you meant `rally-memory`, check spelling.
- If you meant an external skill, move it to `external_skills:` or
  `allowed_skills:` (depending on tier).
- If you meant a flow-local skill, move it to `allowed_skills:`.

See [SKILL_SCOPING.md](SKILL_SCOPING.md) for the four tiers.

---

## `Skill does not exist: <name>`

Root cause: an `allowed_skills:` entry is not registered in the workspace
skill registry. Either the skill directory is missing, its `SKILL.prompt`
fails to compile, or the workspace `pyproject.toml` does not include its
emit target.

Remedy:

- Verify the skill directory exists under `skills/<name>/` or
  `flows/<flow>/skills/<name>/`.
- Verify `pyproject.toml` has a matching
  `[[tool.doctrine.emit.targets]]` entry.
- Re-emit with `make emit`.

---

## `Note-backed previous output reopen is not supported for <input>`

Root cause: a downstream agent's previous-turn input points at an
upstream output whose `target:` is `base.RallyIssueNoteAppend`. Notes
carry no declaration identity; Rally cannot reopen a typed handoff from
a shared ledger block.

Remedy: change the upstream output to `target: File` with a `home:`
path the flow owns. That path carries declaration identity and readback
is exact.

See [docs/TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md),
[RALLY_PORTING_GUIDE.md](RALLY_PORTING_GUIDE.md#4-do-not-put-required-typed-handoffs-on-the-note-target),
and the guard at
[src/rally/services/previous_turn_inputs.py](../src/rally/services/previous_turn_inputs.py).

---

## `Missing export: <symbol>`

Root cause: a cross-flow import names a symbol that its source does not
`export`. Under Doctrine v4, same-flow symbols resolve by bare name, but
cross-flow symbols must be marked `export` on the declaration and
`import`ed on the consumer.

Remedy:

- If the symbol is consumed across flows, add `export` to its
  declaration.
- If the symbol is consumed inside the same flow, remove the `import`
  (it is unnecessary).

---

## `Could not resolve flow root`

Root cause: running `python -m doctrine.emit_docs` directly on a Rally
flow without the Rally stdlib wired. Rally's `pyproject.toml` declares
`additional_prompt_roots = ["stdlib/rally/prompts"]`, but that only
applies when emission runs through Rally's helper.

Remedy: use `ensure_flow_assets_built` (or `rally run` / `rally
resume`, which call it implicitly):

```bash
uv run python -c "from pathlib import Path; \
from rally.services.flow_build import ensure_flow_assets_built; \
ensure_flow_assets_built(flow_name='software_engineering_demo', repo_root=Path('.'))"
```

Do not call `doctrine.emit_docs` directly on a Rally flow unless you
know what you are doing.

---

## `Reserved path: key`

Root cause: a flow-level YAML or prompt uses `path:` as a map key.
Rally reserves `path:` for internal typed surfaces (final output
contracts, schema metadata).

Remedy: rename the key. If you need a file path in `flow.yaml`, use one
of the four path schemes (`home:`, `workspace:`, `host:`, `flow:`)
directly in the string value, not as a key.

See [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md#path-schemes).

---

## `runtime.prompt_input_command is not supported`

Root cause: `flow.yaml` declares a per-turn input reducer. Rally does
not support per-turn computed prompt inputs — the pattern creates a
shadow state machine that drifts from the four truth surfaces.

Remedy: remove the field. Put runtime truth on disk (`home:issue.md`,
the latest turn result, or a setup script that writes a file agents can
read), not in a computed prompt reducer.

See [RALLY_PORTING_GUIDE.md](RALLY_PORTING_GUIDE.md#1-do-not-build-a-second-state-machine-or-mode-gate-system-on-top-of-rally).

---

## `runtime.env.<KEY> is reserved`

Root cause: `flow.yaml`'s `runtime.env:` names a key Rally or the
adapter already owns. Reserved prefixes and names:

- Any key starting with `RALLY_`.
- `CODEX_HOME`.
- `ENABLE_CLAUDEAI_MCP_SERVERS`.

Remedy: rename the env var. If you need Rally-visible context, use a
non-`RALLY_`-prefixed name.

---

## `External skill root alias <alias> is reserved`

Root cause: `pyproject.toml`'s `[tool.rally.external_skills]` registers
an alias that collides with Rally's reserved alias list: `rally`,
`stdlib`, `system`, `flow`, `home`, `workspace`, `host`, `local`,
`builtin`, `builtins`.

Remedy: pick a different alias. External skill aliases must start with
a lowercase letter and use only lowercase letters, digits, hyphens, or
underscores.

---

## `Flow code must be exactly three uppercase ASCII letters`

Root cause: `flow.yaml`'s `code:` is not three uppercase ASCII letters.
The code is used for the per-flow lock path, so the constraint is
enforced at load.

Remedy: pick a three-letter uppercase code (e.g. `SED`, `PLP`, `HLO`).

---

## `Unknown owner in next_owner: <name>`

Root cause: a turn result's `next_owner` field references an agent
short name that does not exist in the flow's `agents:` map.

Remedy:

- If this is a typo, fix the turn result (or the route field's enum).
- If you meant to route to an agent in a different flow, you cannot —
  Rally routes inside one flow only.

See [TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md#the-route-field).

---

## `Turn-result schema must require [kind, summary, reason, sleep_duration_seconds]`

Root cause: a flow-local turn-result schema override does not require
all five base keys. Rally validates the emitted JSON Schema against the
stdlib base contract and refuses a narrower-than-base schema.

Remedy: make the override inherit `BaseRallyTurnResultSchema` (via
`output schema ...[BaseRallyTurnResultSchema]`) and use
`inherit {kind, summary, reason, sleep_duration_seconds, agent_issues}`.

---

## Related Docs

- [RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md) — when-Rally-refuses-re-author-the-surface.
- [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md) — every loader rule in one place.
- [TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md) — what a valid final JSON looks like.
- [SKILL_SCOPING.md](SKILL_SCOPING.md) — the four skill tiers.
- [RALLY_PORTING_GUIDE.md](RALLY_PORTING_GUIDE.md) — the anti-patterns that trigger most refusals.
