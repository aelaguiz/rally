---
title: "Rally Principles"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_PORTING_GUIDE.md
  - README.md
---

# Rally Principles

This document is the definitive list of Rally's authoring principles. Every
recommendation in the other enduring docs descends from one of these rules.
If a choice in Rally feels hard, the answer is usually in here.

The `rally-learn` skill (installed via `npx skills add .`) mirrors this file
into `references/principles.md` so that agents being taught Rally see the
same rules. Keep the two in sync: this file is the source, the emitted
skill content is the teaching version.

## The Core Split

Rally is a filesystem-first agent harness. Doctrine is the authoring
language underneath. The split is load-bearing.

- **Rally's job:** materialize `flow.yaml`, wire Doctrine-compiled assets,
  run adapters, keep run state on disk.
- **Doctrine's job:** compile the authored prompts and contracts Rally
  runs.

If a rule is really about runtime state — scheduling, locking, tool
orchestration, detach — it belongs in Rally. If it is about how an agent
thinks about its job, it belongs in authored Doctrine.

## The Twelve Principles

### 1. Filesystem is the source of truth

State lives in `flow.yaml`, in files under `runs/`, and in compiled
artifacts under `build/`. Prompts are not state. If a reader cannot
reconstruct the run by reading the filesystem, Rally has failed you — or
you have written state where state does not belong.

This shows up as the four runtime truth surfaces:

- `flow.yaml` — the flow-level config.
- `home:issue.md` — the shared run ledger.
- The latest turn result JSON (`runs/active/<ID>/home/sessions/<slug>/turn-<NNN>/final.json`).
- The compiled `AGENTS.md` + `final_output.contract.json` +
  `schemas/*.schema.json` under `flows/<flow>/build/agents/<slug>/`.

### 2. The harness is thin; flows do the thinking

Rally does not reason about your domain. It does not decide what a turn
means. It loads `flow.yaml`, builds the agent home, runs the adapter,
parses the final JSON, and moves on. Every decision — what to output,
whom to route to, when to block or sleep — belongs to the agent.

See `src/rally/services/turn_runner.py`. There is no "mode" layer in
Rally. There is only the turn result.

### 3. Notes are advisory; final JSON is control

`home:issue.md` is a shared run ledger for breadcrumbs, scratch work, and
context a later reader might need. Turn results — the parsed JSON Rally
reads after every turn — are the control surface. Rally routes on the
JSON. It does not route on notes.

See `skills/rally-kernel/prompts/SKILL.prompt` (notes are explicitly
advisory) and the Required / Advisory distinction on previous-turn-input
declarations.

### 4. Every typed handoff must use a file

When one agent hands Required output to the next, that handoff must use
`target: File` with a `home:` path the flow owns. Notes carry no
declaration identity. Rally refuses to reopen a note-backed Required
input on the next turn.

See `src/rally/services/previous_turn_inputs.py` — the guard raises a
clear error if the previous-turn target is a note.

### 5. Do not repeat law across layers

If `stdlib/rally/prompts/rally/` teaches a rule, do not copy it into
flow-shared prompts or per-role prompts. Pick one owner per rule: stdlib,
flow-shared, or role-specific. Every copy burns always-on prompt budget
and creates drift the next time the rule changes.

Flows inherit stdlib via `import rally.base_agent as base` and never
paraphrase.

### 6. Export what you import; import what you export

Under Doctrine v4, a flow is one namespace rooted at the directory
holding its `AGENTS.prompt` or `SKILL.prompt`. Same-flow symbols resolve
by bare name — no `import` needed. Cross-flow symbols need both `export`
on the declaration and `import` in the consumer.

This is why stdlib modules under `stdlib/rally/prompts/rally/` each live
in their own directory with `AGENTS.prompt` at root, and the
cross-flow-consumed symbols carry `export`.

### 7. Cite a real path when you teach

Every claim about Rally behavior should anchor to a real file:
`src/rally/services/...`, `docs/RALLY_*.md`,
`flows/software_engineering_demo/...`,
`stdlib/rally/prompts/rally/...`, or `skills/rally-*/`. Vague guidance
produces "go read the code" pushback and trains authors to distrust the
docs.

### 8. When Rally refuses, re-author the surface

When Rally's loader or runtime refuses ("note-backed reopen not
supported," "unknown owner," "missing `system_skills`," "active run
already holds the lock"), it is not a bug to work around. It is a
constraint that keeps the four truth surfaces honest. Fix the authored
surface. Do not bypass the guard.

The error messages are the teaching surface; they point at the right fix.

### 9. Skills are allowlists, not suggestion boxes

Every skill in an agent's `allowed_skills:` list is validated at load
time and burns always-on prompt budget. Adding "related" skills the
agent will not actually call is pure drift. Add a skill to an agent only
if that agent will call it.

See `src/rally/services/agent_skill_validator.py` and
`docs/SKILL_SCOPING.md`.

### 10. One active run per flow

Rally enforces one active run per flow with a per-flow lock at
`runs/locks/<FLOW_CODE>.lock`. The lock survives fork and releases on
process death. Two instances of the same flow cannot run at once, by
design.

See `src/rally/services/run_lock.py`. If you need parallel runs, make
two flows. Do not try to defeat the lock.

### 11. Generated readback is compiler-owned

Files under `build/**` — the emitted `AGENTS.md`,
`final_output.contract.json`, `schemas/*.schema.json` — are produced by
Doctrine emit. They are not hand-editable. Re-emit from source.

See `src/rally/services/flow_build.py:ensure_flow_assets_built`. `rally
run` and `rally resume` call this before loading, so most authors never
need to emit by hand.

### 12. Memory is durable context, not control

The `rally-memory` system skill stores agent observations across runs.
It is searchable, durable, and per-agent-slug. It never carries control
truth — no `done`, no `blocker`, no `sleep_duration_seconds`, no
routing decision. Those live in turn results, on the current turn.

See `skills/rally-memory/prompts/SKILL.prompt` and `docs/RALLY_MEMORY.md`.

## Do / Do Not

**Do:**

- Keep state on disk in the four truth surfaces.
- Keep Rally thin. Put domain thinking in the agent.
- Use `target: File` for every Required handoff.
- Cite one real path for every rule you teach.
- Allowlist only the skills an agent will actually call.
- Respect the per-flow lock.

**Do not:**

- Encode state in prompts when it belongs on disk.
- Add a Rally-level policy layer for domain decisions.
- Use notes for typed handoffs.
- Hand-edit anything under `build/`.
- Bloat `allowed_skills` with skills the agent never calls.
- Work around Rally refusals instead of re-authoring the surface.

## Related Docs

- [RALLY_MASTER_DESIGN.md](RALLY_MASTER_DESIGN.md) — constitutional runtime design.
- [RALLY_RUNTIME.md](RALLY_RUNTIME.md) — runtime surfaces and lifecycle.
- [RALLY_PORTING_GUIDE.md](RALLY_PORTING_GUIDE.md) — the anti-patterns these principles prevent.
- [TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md) — the control surface in detail.
- [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md) — the flow-level truth surface in detail.
- [SKILL_SCOPING.md](SKILL_SCOPING.md) — the allowlist rule in detail.
- [RALLY_MEMORY.md](RALLY_MEMORY.md) — memory discipline in detail.
