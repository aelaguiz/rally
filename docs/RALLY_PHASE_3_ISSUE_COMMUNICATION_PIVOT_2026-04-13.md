---
title: "Rally - Phase 3 Issue Communication Pivot Proposal"
date: 2026-04-13
status: proposal
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_proposal
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/handoffs.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/currentness.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - flows/_stdlib_smoke/prompts/AGENTS.prompt
  - flows/single_repo_repair/prompts/AGENTS.prompt
---

# TL;DR

Outcome
- Make Phase 3 the issue-communication pivot that removes the idea of a separate authored handoff object, ships one mandatory Rally issue skill that teaches agents to use the Rally CLI for durable notes, injects the current run id into every agent environment, and keeps the structured final turn result as the only routing and stop/sleep control surface.

Problem
- Rally currently has a checked-in doctrine-output experiment for `issue_ledger`, `notes`, and `handoffs`, but that shape hardens the wrong interface: it duplicates communication surfaces, tempts authored route truth outside the final turn result, and pushes issue-log materialization into Doctrine output contracts instead of Rally-owned behavior.

Approach
- Keep `rally.turn_results` as the only shared machine contract.
- Add one mandatory Rally issue skill that every agent always has.
- Make that skill thin: it teaches when to leave a durable note and tells the agent to use the Rally CLI, not to edit `issue.md` directly.
- Inject `RALLY_RUN_ID` into every agent environment so the CLI can resolve the active run home and the live `issue.md`.
- Extend the Rally CLI with a note command that validates the run id, resolves `home/issue.md`, and appends markdown as a Rally-owned ledger write.
- Update the stdlib and authored flows so durable notes are written through this skill-plus-CLI path and the final turn result remains the only route or terminal control signal.

Non-negotiables
- There is no such thing as a human handoff.
- There is no separate authored handoff object.
- Route truth lives only in the validated final turn result.
- Serialized notes preserve durable context only; they do not affect routing, stop/done state, blocker state, or sleep behavior.

# 0) Proposal Goal

Phase 3 should stop Rally from hardening the wrong communication model before the first runnable runtime phase lands.

The point of this phase is to lock the right communication interface before the broader runnable runtime phase lands.
That means Phase 3 is not just wording.
If Rally wants an always-present issue skill, Rally must also provide the real Rally-owned write path that skill uses.

The communication model after this phase should be:

1. Agents may write in-order serialized notes through a Rally-owned issue skill that calls the Rally CLI.
2. Agents must end the turn with one structured final turn result.
3. Rally-owned code appends both surfaces into `home/issue.md` in Rally-owned order.
4. Rally routes, stops, blocks, or sleeps only from the validated final turn result.

## 0.1 Canonical user asks and leverage claim

The repeated user asks this phase should satisfy are:

- "Leave a durable note on the current issue before you end the turn."
- "Record what you learned so the next agent can read it from `issue.md`."
- "Do not invent a handoff object; use Rally's issue note path and then return the final route decision."

The leverage claim is:

- Rally should solve durable issue communication once, in one always-present skill plus one CLI path, instead of re-explaining ad hoc note-writing behavior in every flow or pretending Doctrine outputs are a runtime append mechanism.

# 1) Problem Statement

## 1.1 What exists today

- `stdlib/rally/prompts/rally/turn_results.prompt` already gives Rally a shared structured end-of-turn contract.
- `stdlib/rally/prompts/rally/issue_ledger.prompt`, `notes.prompt`, and `handoffs.prompt` exist as an earlier doctrine-output experiment for durable issue-log communication.
- `_stdlib_smoke` and `single_repo_repair` still reflect that earlier experiment in their authored surfaces.
- The master design doc now says Phase 3 is the issue-communication pivot and Phase 4 is the first runnable runtime phase.
- The master design doc already points toward one always-present Rally issue skill, but the proposal needs to say clearly what that skill actually does.

## 1.2 What is wrong with the current communication shape

- It treats note-writing like a Doctrine output target instead of a Rally-owned capability.
- It leaves too much room for route-facing prose to look like a second routing surface.
- It encourages the repo to think in terms of "handoff artifact" instead of "serialized issue history plus structured route decision".
- It makes the issue-log materialization problem look like a compiler-output problem when it is really a Rally CLI and run-store problem.
- It does not give agents one obvious, always-available command for "leave a durable note on this run."

## 1.3 The core correction

Rally should make the following distinction explicit:

- Doctrine owns authored flow semantics and the structured final turn result contract.
- Rally owns the issue log, the ordering of issue-log appends, the env contract that exposes run identity, and the CLI capability agents use to write durable notes into that log.

That means:

- `rally.turn_results` survives.
- the doctrine-output note and handoff surfaces stop being the preferred design.
- Rally grows one issue capability under `skills/` that every Rally agent always has.
- that skill teaches agents to use the Rally CLI rather than writing `issue.md` directly.

# 2) Mechanism Choice

## 2.1 Why this should be a skill plus CLI

Per the intended shape of Rally and the `skill-authoring` guidance, the right mechanism here is not "more prompt prose" and not "a Doctrine output target."

It is:

- one reusable Rally issue skill because the workflow is repeated across many flows and many turns
- one Rally CLI write path because the skill needs a real Rally-owned implementation surface
- one run-id env contract because the skill should not guess filesystem paths

The split should be explicit:

- the skill teaches reusable behavior and invariants
- the CLI owns the write operation
- the run store owns run lookup and validation
- `rally.turn_results` owns route and terminal truth

## 2.2 What the skill should and should not own

The mandatory Rally issue skill should be deliberately thin.

It should own:

- when to preserve durable context
- the instruction to use the Rally CLI for issue-note writes
- the rule that notes are markdown and durable context only
- the rule that notes must not be used for routing or stop/sleep control
- the rule that agents must not edit `home/issue.md` directly

It should not own:

- path discovery
- run lookup
- append ordering
- file locking
- issue-history snapshots
- routing semantics

Those belong in Rally runtime code, exposed through the CLI.

# 3) Proposed Model

## 3.1 Two forward-communication primitives only

After Phase 3, Rally should treat the following as the only forward-communication primitives:

- serialized issue notes
- structured final turn results

Serialized issue notes are:

- durable context
- append-only
- ordered by Rally
- written through a Rally-owned skill that invokes a Rally-owned CLI command
- never trusted for routing or terminal control

Structured final turn results are:

- required at the end of Rally-managed turns
- schema-validated
- the only source of route/stop/blocker/sleep truth
- written back into `home/issue.md` by Rally as normalized runtime readback

## 3.2 Run-id-anchored note writes

Phase 3 should define one simple write contract for durable notes:

- Rally injects `RALLY_RUN_ID` into every agent process it launches.
- Agents use that run id when they call the Rally CLI to leave a note.
- The CLI resolves the run from Rally-owned state, not from a guessed file path.
- The CLI confirms the resolved run id and the live `home/issue.md` path before writing.
- The CLI appends a Rally-stamped markdown block to the issue log and snapshots `issue_history/`.

The important trust boundary is:

- the agent may supply markdown note content
- the agent does not get to choose the authoritative write target by path

That is why the env contract should expose run identity, not raw write authority.

## 3.3 Proposed CLI surface

The Phase 3 proposal should define a minimal CLI note surface, not a broad issue-log API.

The canonical command should be:

```bash
rally issue note --run-id "$RALLY_RUN_ID"
```

Behavior:

1. Read markdown note content from standard input.
2. Resolve `runs/<run-id>/run.yaml`.
3. Confirm `run.yaml.id` matches the requested run id.
4. Resolve the live issue path from Rally-owned run metadata and confirm it points at the current run's `home/issue.md`.
5. Acquire the Rally-owned append path for that issue log.
6. Append one markdown note block.
7. Snapshot the full post-append ledger into `issue_history/`.

The skill should teach the heredoc form as the default agent usage pattern:

```bash
rally issue note --run-id "$RALLY_RUN_ID" <<'EOF'
### Note
- Changed the parser edge case in `src/...`
- Verification still pending for the resume path
EOF
```

This keeps note-writing:

- shell-simple for agents
- markdown-native
- anchored to one explicit run identity
- implemented by Rally code instead of direct file writes

## 3.4 Proposed env contract

The required Phase 3 env injection is:

- `RALLY_RUN_ID=<stable-run-id>`

Rally should inject that env var into every managed agent launch.

The skill should treat `RALLY_RUN_ID` as required.
If it is missing, the agent should fail loud instead of guessing which run is active.

This proposal does not require a write-capable `RALLY_ISSUE_PATH` env var.
If Rally already exposes the issue path for read-only convenience, that is fine, but the write path should still be resolved and validated from `RALLY_RUN_ID` inside Rally-owned code.

## 3.5 What “handoff” means after the pivot

The word `handoff` may still appear as the name of the route-to-next-owner branch inside `rally.turn_results`.

It must not mean:

- a second authored note type
- a second trust surface
- a separate authored artifact class
- a second routing channel

In plain terms:

- if an agent wants to preserve context, it writes a serialized issue note
- if an agent wants Rally to wake the next owner, it returns the route branch in the structured final turn result

## 3.6 Currentness after the pivot

Phase 3 should keep currentness typed.
It should not let currentness collapse into prose.

The exact authored currentness helper may still need follow-up design work, but the phase should preserve these invariants:

- one current artifact or `current none`
- no routing from currentness prose
- no requirement for a separate authored handoff object just to carry currentness

# 4) Deliverables

Phase 3 should produce the following repo-level results:

- one new mandatory Rally issue skill under `skills/`
- one doc-backed statement that this skill is always available to Rally agents
- one Rally CLI note command for durable markdown issue writes
- one env contract that injects `RALLY_RUN_ID` into every agent launch
- one narrowed stdlib contract where `rally.turn_results` remains canonical
- updated authored examples and flow prompts that no longer require note or handoff output targets
- one master-design doc that links to this proposal and uses the new model consistently

The intended repo effect is:

- `skills/rally-issue/`
  - new mandatory Rally issue skill that teaches agents to use `rally issue note`
- `src/rally/cli/` and owning services
  - minimal Rally CLI support for `rally issue note`
- adapter launch contract
  - injects `RALLY_RUN_ID` for every Rally-managed agent process
- `stdlib/rally/prompts/rally/turn_results.prompt`
  - kept as the machine turn-result contract
- `stdlib/rally/prompts/rally/issue_ledger.prompt`
  - transitional only, or removed in the follow-through if no longer needed
- `stdlib/rally/prompts/rally/notes.prompt`
  - transitional only, or removed in the follow-through if no longer needed
- `stdlib/rally/prompts/rally/handoffs.prompt`
  - transitional only, or removed in the follow-through if no longer needed
- `flows/_stdlib_smoke/`
  - updated to prove the new model rather than the doctrine-output note/handoff model
- `flows/single_repo_repair/`
  - updated to match the same communication model

# 5) Acceptance Criteria

Phase 3 should be considered complete only when all of the following are true:

1. The master design doc says plainly that Rally has no human handoff primitive and no separate authored handoff object.
2. Rally’s canonical communication model is reduced to serialized notes plus the structured final turn result.
3. A mandatory Rally issue skill exists under `skills/`, is always available to Rally agents, and instructs agents to use the Rally CLI for durable notes.
4. Every Rally-managed agent launch receives `RALLY_RUN_ID`.
5. `rally issue note --run-id "$RALLY_RUN_ID"` is the canonical durable-note path and appends markdown into the current run's `home/issue.md`.
6. The CLI validates run identity and resolved issue path before writing, rather than trusting a direct path chosen by the agent.
7. Agents are no longer expected to use authored note or handoff output targets for durable issue communication.
8. The shared `rally.turn_results` contract remains the only machine routing surface.
9. `_stdlib_smoke` no longer depends on authored note or handoff output targets to express the intended design.
10. `single_repo_repair` no longer depends on authored note or handoff output targets to express the intended design.
11. Phase 4 still owns the broader runnable runtime vertical slice beyond this focused issue-note path.

# 6) Non-Goals

Phase 3 should not widen into any of the following:

- a generic Doctrine output materialization layer for notes or handoffs
- a second routing surface beyond the validated final turn result
- direct agent writes to `home/issue.md` by guessed filesystem path
- full owner-routing runtime execution
- broad session-resume implementation
- general adapter work beyond injecting `RALLY_RUN_ID` for managed agents
- a broad issue-log API beyond the minimal note-write path
- new artifact taxonomy design
- a second communication channel beyond serialized notes plus the final turn result

# 7) Suggested Follow-Through

Once this proposal is accepted, the next implementation work should be:

1. Author `skills/rally-issue/SKILL.md` as a thin always-present Rally skill that teaches the CLI note path and forbids direct `issue.md` mutation.
2. Add `RALLY_RUN_ID` injection to the Rally-managed agent launch contract.
3. Implement the minimal `rally issue note` CLI path and the owning run-resolution and append-validation logic.
4. Update `_stdlib_smoke` to prove the new communication model.
5. Update `single_repo_repair` to the same model.
6. Trim or retire the older doctrine-output communication surfaces that no longer fit.
7. Keep the broader runtime vertical slice work in Phase 4.
