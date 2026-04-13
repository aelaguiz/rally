---
title: "Rally - Claude Code First-Class Adapter Support - Architecture Plan"
date: 2026-04-13
status: draft
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md
  - docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/codex/event_stream.py
  - src/rally/adapters/codex/result_contract.py
  - src/rally/adapters/codex/session_store.py
---

# TL;DR

## Outcome

Rally gains first-class `claude_code` support beside `codex` through one real
adapter boundary. Claude support is not a local spike, a config alias, or a
best-effort shell swap. It is a supported Rally runtime path with the same
run-home, issue-ledger, and strict final JSON rules Rally already enforces for
Codex.

## Problem

Rally is still Codex-only in live runtime code. The new Claude audit shows that
Claude Code now has a strong non-interactive CLI and SDK, but it also exposed a
hard constraint: a fresh `CLAUDE_CONFIG_DIR` loses the user's normal
subscription login. That means Rally cannot claim clean Claude support until it
solves adapter ownership, auth bootstrap, and doc truth together.

## Approach

Use the current Hermes runtime-generalization work as the shared adapter
boundary plan, then fold Claude-specific truth into that same runtime story.
Start Claude support with the Claude Code CLI, not the SDK. Require an explicit
supported auth path, keep adapter state under the run home, generate
adapter-owned prompt and MCP config artifacts, and keep one shared Rally
turn-result path.

## Plan

1. Lock the North Star for first-class Claude support, including the supported
   auth stance and fold-in scope.
2. Research the current adapter seams, Claude auth and config behavior, and the
   docs that still teach a Codex-only or Hermes-only story.
3. Deep-dive the runtime split so shared Rally code, Codex behavior, and the
   new Claude adapter all have clear owners.
4. Write the authoritative phase plan for adapter boundary work, Codex re-home,
   Claude adapter delivery, proofs, and docs convergence.
5. Implement through one canonical plan, then audit the result against both the
   Claude audit and Rally's stable runtime rules.

## Non-negotiables

- No second turn-ending control path. Rally still ends a turn with notes plus
  one final JSON result.
- `claude_code` must be a real adapter, not a Codex alias and not a thin shell
  rename.
- A supported Claude path must not depend on ambient `~/.claude` or
  `~/.claude.json` state.
- No ambient Claude hooks, plugins, auto memory, agent teams, or hidden project
  config in a supported Rally run.
- No mixed per-agent adapter story in v1. Adapter choice stays flow-wide.
- No "best effort" final-result parse path. Claude runs must satisfy the same
  strict final JSON rule as Codex runs.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: not started
external_research_grounding: not started
deep_dive_pass_2: not started
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support `runtime.adapter: claude_code` beside `runtime.adapter:
codex` without breaking its current runtime model, without leaving Codex-only
logic spread through shared runtime code, and without relying on ambient Claude
state outside the run home for a supported adapter path.

This claim is true only if all of this is true:

- `flow.yaml` can name `claude_code` and Rally accepts it through the same flow
  load and run entrypoints it already uses for Codex.
- Shared runtime code no longer imports or calls Codex helpers directly where
  an adapter boundary should own the work.
- Codex still works after the refactor through the same public CLI and run-home
  contract.
- Claude Code uses the same Rally issue-ledger, turn-result, and run-state
  model rather than inventing a second side channel.
- The supported Claude path has an explicit auth bootstrap story and does not
  quietly depend on ambient `~/.claude` login state.
- The main Rally design docs stop teaching a Codex-only or Hermes-only second
  adapter story and instead describe the shipped multi-adapter runtime truth.

## 0.2 In scope

- Define a first-class Rally adapter boundary and registry that can honestly
  own both `codex` and `claude_code`.
- Keep adapter choice flow-wide in `flow.yaml`.
- Refactor Codex launch, session, result, event, and home rules behind that
  boundary.
- Add a real Claude Code adapter under `src/rally/adapters/claude_code/`.
- Decide which home-materialization work is shared and which parts are
  adapter-owned for Claude.
- Support one explicit Claude auth story for supported runs.
- Generate adapter-owned Claude prompt and MCP config artifacts inside the run
  home.
- Keep Rally's current note, final JSON, run id, issue-ledger, and
  filesystem-first rules intact.
- Fold the new Claude audit into the runtime generalization work and align the
  main Rally design docs to one truthful runtime story.
- Add proof that existing Codex behavior still works and that Claude can run
  through the same Rally front door.

Allowed architectural convergence scope:

- split Codex-only helpers out of shared runtime code
- add adapter-private home subdirectories under the run home
- rename shared runtime modules or types so ownership is clear
- translate Rally MCP allowlists into a generated Claude JSON config
- generate Claude-specific prompt files from Rally's compiled prompt output
- update or delete stale docs and comments that still teach a Codex-only or
  Hermes-only runtime shape

## 0.3 Out of scope

- Mixed-adapter flows where one flow uses both Codex and Claude in the same
  run.
- A Claude SDK-first implementation for v1.
- Support claims for a Claude path that quietly depends on the user's default
  global login state.
- Claude subagents, agent teams, plugins, or remote-control features as part of
  Rally v1 support.
- Changing Doctrine prompt language or compiler behavior for this work.
- Relaxing Rally's final-output discipline into best-effort parsing.
- Adding a third adapter in the same change.

## 0.4 Definition of done (acceptance evidence)

The work is done only when all of this is true:

- Rally validates supported adapter names instead of carrying a generic string
  that only one runtime path can handle.
- Shared runtime code calls an adapter contract for launch, session reuse, turn
  execution, adapter bootstrap, and event handling, while Rally keeps one
  shared turn-result rule.
- Codex is still a first-class adapter after that refactor.
- Claude Code is a first-class adapter, not a spike and not a shell alias.
- A Rally run can reach a truthful stop point with Claude through the same
  `rally run` or `rally resume` front door.
- The supported Claude path keeps adapter-local state inside the run home and
  uses an explicit supported auth mode.
- Rally still ends turns with one validated final JSON result.
- Rally's skill and MCP allowlists still hold when Claude is the adapter.
- The main Rally design docs and runtime-detail docs match the shipped design.

Behavior-preservation evidence:

- `uv run pytest tests/unit -q` stays green through the refactor
- existing Codex-focused unit tests keep passing or move cleanly behind
  adapter-neutral seams
- new unit coverage proves adapter validation, adapter dispatch, and
  adapter-owned home, session, result, and event behavior
- one honest Claude proof exists through Rally in a supported auth mode, or the
  exact blocker is named plainly in this doc before the work is called complete

## 0.5 Key invariants (fix immediately if violated)

- One flow has one adapter.
- Notes stay context-only.
- Final JSON stays the only turn-ending control path.
- No supported Claude path depends on ambient `~/.claude` state.
- No ambient Claude hooks, plugins, auto memory, agent teams, or stray project
  config leak into a supported Rally run.
- No adapter may widen tool, skill, MCP, or auth access past Rally policy.
- No silent fallback or compatibility shim masks a broken adapter contract.
- No docs keep teaching a narrower runtime story than the shipped code.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make Claude support fit Rally's current runtime law instead of teaching
   Rally to special-case a second runner.
2. Keep Codex stable while opening a clean path for Claude.
3. Make the supported Claude path honest about auth and state ownership.
4. Keep the operator surface small: same CLI, same run-home model, same final
   result rule.
5. Remove stale doc truth in the same pass so the design docs match the code.

## 1.2 Constraints

- `src/rally/services/runner.py` still launches Codex directly today.
- `src/rally/services/home_materializer.py` still writes Codex config and auth
  links only.
- The Claude audit already proved a fresh `CLAUDE_CONFIG_DIR` loses normal
  subscription login on this machine.
- Claude Code has stronger CLI support than the older Hermes assumptions, but
  its config and auth model still differ from Codex.
- Rally's current design docs still talk about a Codex-first vertical slice and
  a Hermes second-adapter plan, not a shipped Codex plus Claude runtime.

## 1.3 Architectural principles (rules we will enforce)

- Shared runtime code depends on an adapter contract, not on Codex or Claude
  helpers directly.
- Adapter-owned state lives under the run home.
- Supported adapter modes use explicit auth bootstrap, not ambient machine
  state.
- Rally keeps one shared turn-result rule even when adapters differ in output
  envelope shape.
- Folded docs must tell the same runtime story as the shipped code.

## 1.4 Known tradeoffs (explicit)

- CLI-first Claude support is simpler and closer to Rally's current runtime,
  but it gives less native structure than a future SDK path.
- Requiring explicit Claude auth setup raises the bar for local use, but it is
  the cleanest way to keep Rally honest about run-home ownership.
- Keeping Claude subagents and agent teams out of v1 narrows scope, but it also
  avoids hidden work, extra token burn, and a second multi-agent model inside
  one Rally turn.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally already carries a generic `runtime.adapter` field in `flow.yaml`.
- Live runtime code still launches Codex directly and stores Codex-shaped
  sessions, events, and launch records.
- A Hermes runtime-generalization plan already exists and correctly points at a
  shared adapter boundary.
- The new Claude audit now adds a second concrete runner target with better
  current machine support than the earlier Hermes assumptions.

## 2.2 What’s broken / missing (concrete)

- `runtime.adapter` is generic on paper, but not in runtime behavior.
- Claude support has no current adapter, no supported auth story, no generated
  prompt file path, and no generated MCP config path.
- The runtime docs do not yet say whether Claude changes the current Hermes
  plan, folds into it, or replaces parts of its adapter story.

## 2.3 Constraints implied by the problem

- We need one canonical adapter story, not a Codex plan plus a separate Claude
  story that drifts.
- The Claude path must be explicit about supported auth modes from the start.
- We cannot call the Claude path first-class until the code and docs agree on
  what "supported" means.

# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

The first research pass should ground this plan against the current official
Claude Code CLI, auth, settings, MCP, permissions, and SDK docs already cited
in `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`.

## 3.2 Internal ground truth (code as spec)

The first research pass should treat these as the main repo anchors:

- `src/rally/services/runner.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/flow_loader.py`
- `src/rally/domain/flow.py`
- `src/rally/adapters/codex/*`
- `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
- `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`

## 3.3 Decision gaps that must be resolved before implementation

This draft assumes:

- `claude_code` is the adapter name
- CLI-first is the v1 Claude integration plane
- supported Claude runs require explicit auth bootstrap
- ambient default-login mode is local-spike only and not part of first-class
  support

If any of those assumptions are wrong, this North Star should be edited now,
before research and deep-dive turn them into a larger plan.

# 4) Current Architecture (as-is)

## 4.1 On-disk structure

The current runtime is split between shared services under `src/rally/services`
and Codex-only code under `src/rally/adapters/codex/`, but shared services
still know too much about Codex details.

## 4.2 Control paths (runtime)

Today Rally loads a flow, prepares a run home, builds a prompt, launches
Codex, parses Codex output, stores a Codex session id, and drives the issue log
through one Codex-shaped execution path.

## 4.3 Object model + key abstractions

`FlowDefinition.adapter` is generic on paper. The live launch, session, event,
and result abstractions are not yet generic in practice.

## 4.4 Observability + failure behavior today

Launch logs, session files, turn artifacts, and issue events already exist, but
they are still shaped around Codex output and Codex session behavior.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface is expected. The operator surface should stay the same Rally
CLI plus the usual run-home files.

# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

Rally should keep one shared run-home shell and add adapter-private state under
that home, including a Claude-owned config directory and generated adapter
artifacts.

## 5.2 Control paths (future)

Shared runtime code should resolve an adapter, ask that adapter to prepare its
home state, launch a turn, parse events, save session state, and hand back one
strict final response that Rally can validate.

## 5.3 Object model + abstractions (future)

Codex and Claude should both satisfy one adapter contract. Claude-specific
envelope parsing, auth bootstrap, prompt-file generation, and MCP JSON
generation should stay below that boundary.

## 5.4 Invariants and boundaries

The future design should keep one shared Rally run model, one issue-ledger,
one turn-result rule, one flow-wide adapter choice, and one explicit auth story
per supported Claude mode.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface is planned.

# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

The first deep-dive pass should make this section exhaustive. At minimum it
will need to inventory:

- flow loading and adapter validation
- shared runner execution seams
- run-home materialization
- Codex adapter helpers that should move behind a generic boundary
- new Claude adapter modules
- launch, session, event, and result artifact paths
- unit tests and runtime docs that still teach Codex-only or Hermes-only truth

## 6.2 Migration notes

The deep-dive pass should make the canonical owner path, delete list, doc sync
list, and behavior-preservation signals explicit.

# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

This section is draft-only in the `new` pass. Later planning commands should
turn it into the authoritative execution checklist.

## Phase 1 - Lock the adapter story

Goal

- Confirm the North Star, supported Claude auth stance, and the doc fold-in
  scope before deeper planning.

Work

- Confirm whether this doc should become the canonical plan for Claude support
  and how it should relate to the current Hermes runtime-generalization doc.

Verification (required proof)

- North Star is explicitly confirmed.

Docs/comments (propagation; only if needed)

- None yet beyond this plan doc.

Exit criteria

- The planning baseline is stable enough for research and deep-dive.

Rollback

- Revert this draft doc if the North Star itself is rejected.

## Phase 2 - Research and design convergence

Goal

- Ground the adapter plan in current code, current docs, and current Claude
  capabilities.

Work

- Research the live seams, Claude auth and config behavior, and the docs that
  must converge.

Verification (required proof)

- Research section is strong enough to support deep-dive without guesswork.

Docs/comments (propagation; only if needed)

- Keep the plan doc aligned as findings land.

Exit criteria

- Adapter naming, auth mode, and fold-in scope are all concrete.

Rollback

- Stop and revise the plan if research disproves the current North Star.

## Phase 3 - Runtime boundary and Claude delivery

Goal

- Re-home Codex behind the shared boundary and add the first supported Claude
  adapter path.

Work

- Implement adapter dispatch, adapter-owned home work, and the Claude
  launch, result, session, and event path.

Verification (required proof)

- Unit tests and one honest supported Claude proof.

Docs/comments (propagation; only if needed)

- Update runtime docs and any high-leverage boundary comments.

Exit criteria

- Codex and Claude both run through the same Rally front door.

Rollback

- Remove incomplete Claude support rather than keep a half-supported path.

## Phase 4 - Audit and doc truth sync

Goal

- Make the code and design docs tell one truthful runtime story.

Work

- Audit implementation completeness, sync the master docs, and delete stale
  narrower runtime truth.

Verification (required proof)

- Clean audit and aligned runtime docs.

Docs/comments (propagation; only if needed)

- Sync the surviving design docs in the same pass.

Exit criteria

- The shipped code, this plan, and Rally's main design docs agree.

Rollback

- Reopen the plan if the audit finds missing work or stale truth.

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- `uv run pytest tests/unit -q`
- adapter validation tests
- adapter dispatch tests
- Codex preservation tests
- Claude result, session, and event behavior tests

## 8.2 Integration tests (flows)

- the owning `rally` CLI path should prove one supported Claude run through the
  same entrypoint used for Codex

## 8.3 E2E / device tests (realistic)

- one honest local Claude proof in a supported auth mode
- final doc sync check across the master design and runtime-detail docs

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- keep Codex working first
- add Claude as a new validated adapter
- do not advertise unsupported ambient-login mode as a supported Rally path

## 9.2 Telemetry changes

- reuse Rally's current run-event and launch-record proof paths where they stay
  truthful
- add adapter-specific proof artifacts only where shared ones are not enough

## 9.3 Operational runbook

- supported Claude runs need an explicit auth setup story
- unsupported auth shapes should fail loud with a clear blocker

# 10) Decision Log (append-only)

## 2026-04-13 - Claude support needs its own canonical plan

Context

- A Hermes runtime-generalization plan already exists.
- A new Claude audit now adds a stronger second concrete runner target with a
  different auth and config story.

Options

- fold Claude into the existing Hermes plan without a separate canonical doc
- create a separate canonical plan for first-class Claude support and fold it
  back into the shared runtime story later

Decision

- Create a separate canonical full-arch plan for first-class Claude support,
  then use later planning passes to decide how it should fold into the shared
  runtime generalization and matching design docs.

Consequences

- Claude support gets its own clear North Star instead of hiding inside a
  Hermes-shaped story.
- Later planning passes must still converge the docs so Rally ends with one
  truthful runtime design.

Follow-ups

- Confirm this North Star before deeper planning.
