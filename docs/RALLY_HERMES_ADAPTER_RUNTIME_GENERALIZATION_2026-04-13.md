---
title: "Rally - Hermes Adapter Runtime Generalization - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/codex/event_stream.py
  - src/rally/adapters/codex/session_store.py
  - ../hermes-agent
---

# TL;DR

## Outcome

Rally can accept `runtime.adapter: hermes` beside `codex` through one clean
adapter boundary. The runtime stays simple, flow-wide, CLI-first, and
filesystem-first. Adding a second harness no longer means threading Codex-only
rules through shared runtime code.

## Problem

Today Rally is only generic on paper. `flow.yaml` already has
`runtime.adapter`, but the live runtime is still built around Codex launch,
Codex home setup, Codex sessions, Codex event parsing, and Codex result
loading. That makes `hermes` impossible to add cleanly and makes future
adapter work likely to copy the same mistake.

## Approach

Turn adapters into first-class runtime owners. Move launch, per-adapter home
setup, session handling, event parsing, and adapter-local bootstrap behind a
small shared adapter contract. Keep one shared Rally run model, one issue
ledger, one generic final JSON loader, and one flow-wide adapter choice.
Implement Hermes as a real second adapter through a library-backed path, not
as a Codex alias or a thin CLI scrape.

## Plan

1. Lock the adapter boundary and the shared runtime responsibilities.
2. Audit every Codex-only seam in flow loading, run-home setup, runner,
   logging, and tests.
3. Refactor Rally so shared runtime code calls an adapter interface instead of
   Codex helpers directly.
4. Re-home existing Codex behavior behind that interface without changing Rally
   behavior.
5. Add a Hermes adapter that keeps Rally's run-home, note, and final-output
   rules intact.
6. Prove Codex still works and prove Hermes can run through the same Rally
   front door.

## Non-negotiables

- No second turn-ending control path. Rally still ends turns with notes plus
  one final JSON result.
- No Codex aliasing or adapter-name shims. `hermes` must be a real adapter.
- No hidden adapter state outside the run home.
- No silent widening of skill, MCP, or tool access because a harness has its
  own defaults.
- No mixed per-agent adapter story in v1. Adapter choice stays flow-wide.
- No "best effort" parse path for final results. The run must either return a
  valid final result or fail loud.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: not started
deep_dive_pass_2: not started
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support `runtime.adapter: hermes` beside `runtime.adapter: codex`
without losing its current runtime model and without leaving Codex-only logic
spread through shared runtime code.

This claim is true only if all of this is true:

- `flow.yaml` can name `hermes` and Rally accepts it through the same flow load
  and run entrypoints it already uses for Codex.
- Shared runtime code no longer imports or calls Codex helpers directly where
  an adapter boundary should own the work.
- Codex still works after the refactor through the same public CLI and run-home
  contract.
- Hermes uses the same Rally issue-ledger, turn-result, and run-state model
  rather than inventing its own side channel.
- Adapter-local state, config, sessions, auth links, and logs live under the
  prepared run home.
- The new design makes a third adapter easier to add without reopening the
  runtime shape again.

## 0.2 In scope

- Define a first-class Rally adapter boundary and adapter registry.
- Keep adapter choice flow-wide in `flow.yaml`.
- Refactor Codex launch, session, result, event, and home rules behind that
  boundary.
- Add a real Hermes adapter under `src/rally/adapters/hermes/`.
- Decide which home-materialization work is shared and which parts are
  adapter-owned.
- Decide the strict final-result path Hermes must satisfy for Rally to treat it
  as supported.
- Preserve Rally's current note, final JSON, run id, issue-ledger, and
  filesystem-first rules.
- Update the main Rally design docs so they describe a multi-adapter runtime
  honestly.
- Add proof that existing Codex behavior still works and that Hermes can run
  through the same Rally front door.

Allowed architectural convergence scope:

- split Codex-only helpers out of shared runtime code
- rename shared runtime modules or types so the ownership line is clear
- add adapter-private home subdirectories under the run home
- translate Rally MCP and skill allowlists into the Hermes shape if that is
  required to preserve Rally policy
- adjust run-event and session storage ownership so it is adapter-neutral at
  the shared boundary and adapter-specific below it
- update or delete stale docs and comments that still teach a Codex-only
  runtime shape

## 0.3 Out of scope

- Mixed-adapter flows where one flow uses both Codex and Hermes in the same
  run.
- A generic ACP client layer unless the plan later proves it is the cleanest
  v1 path.
- A plugin or marketplace model for adapters.
- Changing Doctrine prompt language or compiler behavior for this work.
- Adding a third adapter in the same change.
- Relaxing Rally's final-output discipline into best-effort parsing.

## 0.4 Definition of done (acceptance evidence)

The work is done only when all of this is true:

- Rally validates supported adapter names instead of carrying a generic string
  that only one runtime path can handle.
- Shared runtime code calls an adapter contract for launch, session reuse,
  turn execution, adapter bootstrap, and event handling, while Rally keeps one
  shared final-response loader.
- Codex is still a first-class adapter after that refactor.
- Hermes is a first-class adapter, not a Codex alias and not a local spike.
- A Rally run can reach a truthful stop point with Hermes through the same
  `rally run` or `rally resume` front door.
- The run home still owns the whole working world, including adapter-local
  state.
- Rally still ends turns with one validated final JSON result.
- Rally's skill and MCP allowlists still hold when Hermes is the adapter.
- The main Rally design docs and runtime-detail docs match the shipped design.

Behavior-preservation evidence:

- `uv run pytest tests/unit -q` stays green through the refactor
- existing Codex-focused unit tests keep passing or move cleanly behind
  adapter-neutral seams
- new unit coverage proves adapter validation, adapter dispatch, and
  adapter-owned home/session/event behavior
- one honest Hermes proof exists through Rally, or the exact blocker is named
  plainly in this doc before the work is called complete

## 0.5 Key invariants (fix immediately if violated)

- One flow has one adapter.
- The shared runtime does not know Codex or Hermes wire details it does not
  need to know.
- Adapter-local state lives inside the run home.
- Notes stay context-only.
- Final JSON stays the only turn-ending control path.
- No adapter may widen tool, skill, MCP, or auth access past Rally policy.
- No silent fallback or compatibility shim masks a broken adapter contract.
- No second adapter may force Rally into a GUI, daemon, DB-first, or
  machine-global control plane.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make the second adapter fit the existing Rally model instead of warping the
   runtime around one harness.
2. Keep the shared runtime smaller and clearer after the refactor, not larger.
3. Preserve current Codex behavior while opening the path for Hermes and later
   adapters.
4. Keep adapter-local rules behind adapter-owned code and run-home layout.
5. Fail loud on unsupported or half-supported adapter states.

## 1.2 Constraints

- `src/rally/services/runner.py` currently imports and calls Codex helpers
  directly.
- `src/rally/services/home_materializer.py` always writes Codex config and
  Codex auth links today.
- `src/rally/adapters/codex/*` already owns useful behavior that should be
  preserved, not rewritten for style.
- The Hermes audit already found real risks around strict final JSON, skill
  sync, MCP translation, approvals, and event/session wiring.
- Rally's master design still says Codex is the first adapter target, so the
  docs need a truthful next step instead of a hidden runtime widening.

## 1.3 Architectural principles (rules we will enforce)

- Shared runtime code depends on an adapter contract, not on Codex helpers.
- Each adapter owns only its own wire format, launch rules, session rules,
  adapter-local state, and adapter-local bootstrap.
- Rally owns the run model, issue ledger, final-result contract, and shared
  CLI behavior.
- Keep one front door for runs and resumes.
- Keep one run-home story and let adapters live inside it, not beside it.
- Prefer hard cutover to the adapter boundary over compatibility glue.

## 1.4 Known tradeoffs (explicit)

- A library-backed Hermes adapter is cleaner than a CLI scrape, but it creates
  tighter repo-to-repo coupling.
- A very small adapter interface is elegant, but it cannot be so small that
  shared runtime code has to peek back into adapter internals.
- Keeping v1 flow-wide avoids scope creep, but it delays any future
  mixed-adapter flow story.
- Strong final JSON enforcement may slow the first Hermes path, but weak final
  parsing would undercut Rally's core runtime rule.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- `flow.yaml` already carries `runtime.adapter`, and Rally domain types treat
  the adapter name as data.
- The live runtime still hard-wires Codex launch, Codex result loading, Codex
  sessions, Codex event parsing, and Codex home materialization.
- The Hermes audit already shows that prompt authoring is mostly ready, but the
  runtime is not.
- Rally documents still describe a Codex-first vertical slice rather than a
  clean multi-adapter runtime.

## 2.2 What’s broken / missing (concrete)

- Rally cannot honestly accept `runtime.adapter: hermes` today.
- The current generic adapter field hides a single-adapter runtime.
- Codex-only code is mixed into shared runtime modules where a future adapter
  should not have to thread through it.
- Hermes has real integration questions that need one clear owner path instead
  of ad hoc patches.

## 2.3 Constraints implied by the problem

- The fix has to preserve the current Codex proof path.
- The second adapter must keep Rally filesystem-first and run-home-first.
- The shared final-result contract cannot become adapter-specific.
- If Hermes cannot satisfy Rally's final-result rule cleanly, the plan must say
  so plainly and design a fail-loud boundary rather than a fuzzy parser.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md` — adopt the core shape from
  the audit: Hermes should be a real second adapter, not a Codex alias, and
  Rally should treat this as the first real test of adapter generalization.
  Reject the idea that the adapter field is already "done" because
  `flow.yaml` carries a generic string.
- `../hermes-agent/hermes_cli/main.py` plus `../hermes-agent/cli.py` — reject
  the Hermes CLI as Rally's supported adapter surface. `cmd_chat()` gates on
  provider setup, runs `sync_skills(quiet=True)` on every CLI launch, and
  quiet single-query mode prints the final response plus a trailing
  `session_id:` line. That is workable for manual use, but it is not a clean
  machine contract for Rally.
- `../hermes-agent/run_agent.py` — adopt the Python agent surface as the most
  credible Hermes v1 entry point. `AIAgent.run_conversation()` returns
  `final_response`, `last_reasoning`, token and cost data, and exposes
  callback-friendly state. That gives Rally a better place to enforce strict
  final-result validation and map Hermes progress into Rally events.
- `../hermes-agent/hermes_constants.py` and `../hermes-agent/hermes_state.py`
  — adopt `HERMES_HOME` as the adapter-local state root and keep it inside the
  Rally run home. `get_subprocess_home()` shows Hermes already supports a
  nested `HERMES_HOME/home` for subprocess `HOME`, and `state.db` shows Hermes
  keeps its own session index there.
- `../hermes-agent/tools/skills_sync.py` — reject any design that points
  Hermes at the shared Rally run-home root and lets bundled skill sync run
  uncontrolled. The sync code copies bundled Hermes skills into
  `HERMES_HOME/skills/`, which would widen Rally's skill surface past the flow
  allowlist.
- `../hermes-agent/toolsets.py`, `../hermes-agent/tools/mcp_tool.py`, and
  `../hermes-agent/tools/approval.py` — adopt these as real runtime
  constraints, not adapter trivia. Hermes toolsets are broader than Rally's
  current flow contract, MCP config comes from `config.yaml -> mcp_servers`,
  and dangerous terminal commands can trigger approval flows. Rally must
  translate or clamp those surfaces instead of inheriting Hermes defaults.
- `../hermes-agent/acp_adapter/server.py` — reject ACP as the first
  implementation step, but keep it as a later rich-event path. The ACP
  adapter already maps tool, thinking, message, usage, and approval events,
  but Rally has no ACP client today, so ACP adds more moving parts than the
  first adapter needs.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/runner.py` — current front door for run and resume
    turn execution. It imports `CodexEventStreamParser`,
    `build_codex_launch_env`, `load_agent_final_response`, and Codex session
    helpers directly. This is the main seam that must stop knowing adapter
    wire details.
  - `src/rally/services/home_materializer.py` — current run-home owner. It
    syncs compiled agents, allowlisted skills, and allowlisted MCPs, then
    always writes Codex config and Codex auth links. This is the shared home
    path we should reuse, but its adapter bootstrap work must split out.
  - `src/rally/services/flow_loader.py` and `src/rally/domain/flow.py` —
    current flow contract. `runtime.adapter` is already real data, but the
    loader does not validate a supported adapter set yet.
  - `src/rally/adapters/codex/launcher.py` — current env contract and adapter
    launch archaeology.
  - `src/rally/adapters/codex/result_contract.py` plus
    `stdlib/rally/prompts/rally/turn_results.prompt` — shared final JSON rule
    currently enforced through the Codex adapter path. The rule itself is
    Rally-owned and should stay shared after adapter generalization.
  - `src/rally/adapters/codex/event_stream.py` — current event normalization
    owner. This shows parser logic should live under the adapter, while
    `src/rally/services/run_events.py` stays the shared event sink.
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` and
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — durable docs still describe a
    Codex-first vertical slice and need truthful follow-through once the new
    adapter boundary lands.
- Canonical path / owner to reuse:
  - `src/rally/services/runner.py` — keep as the shared orchestration owner
    for flow load, run state, issue ledger, and turn-result handling. Do not
    move Rally's whole run model into adapters.
  - `src/rally/services/home_materializer.py` — keep as the shared run-home
    owner for layout, compiled agents, allowlisted skills and MCPs, and shared
    issue and home rules. Move only adapter-local config, auth, and bootstrap
    into adapter-owned hooks.
  - `src/rally/adapters/` — canonical owner for adapter-specific launch,
    result loading, event parsing, session storage, and adapter bootstrap.
  - `src/rally/services/flow_loader.py` — canonical place to validate
    supported adapters so bad config fails before runtime.
  - `src/rally/services/run_events.py` — canonical shared event sink. Adapters
    should emit into Rally events, not invent a second logging plane.
- Existing patterns to reuse:
  - `src/rally/adapters/codex/session_store.py` — existing per-agent session
    storage under the run home; likely pattern to generalize behind an
    adapter-owned session layer.
  - `tests/unit/test_runner.py` — strongest current proof that run and resume,
    issue-ledger writes, handoffs, and adapter launch behavior stay intact
    while shared runtime is refactored.
  - `tests/unit/test_launcher.py` — pattern for adapter env and launch-record
    tests.
  - `tests/unit/test_flow_loader.py` — pattern for front-door validation of
    runtime config and compiled-contract rules.
  - `tests/unit/test_codex_event_stream.py` — pattern for keeping parser tests
    inside the adapter tree.
  - `tests/unit/test_run_events.py` — preservation signal that the shared
    event sink can stay stable while adapter parsers change.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — Rally already teaches
    agents to use the shared kernel skill, read run identity from env, and end
    the turn through one final JSON path. This prompt should stay
    adapter-neutral.
  - `skills/rally-kernel/SKILL.md` — Rally already owns the rule that notes
    are context-only and that the adapter return path carries the final JSON.
    This stays shared.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — the shared turn-result
    schema is already expressed once in the standard library. The second
    adapter should consume the same contract instead of creating a parallel
    one.
- Native model or agent capabilities to lean on:
  - current Codex integration — Rally already proves it can inject compiled
    prompt readback, pass run env, and require one strict JSON final response
    without extra sidecar files
  - Hermes `AIAgent.run_conversation()` — Hermes already exposes a Python
    conversation API with structured return fields and callbacks. Rally should
    use that native surface before adding a CLI scraper, ACP client, or extra
    wrapper layer.
- Existing grounding / tool / file exposure:
  - `runs/<run-id>/home/` — already acts as the whole working world for a
    Rally run
  - `home/issue.md` plus `rally issue note` — already give Rally one
    sanctioned shared note surface
  - flow allowlists materialized into `home/skills/` and `home/mcps/` — Rally
    already projects skill and MCP policy into the run home
  - `RALLY_BASE_DIR`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`,
    and `RALLY_TURN_NUMBER` — already give the agent a stable runtime identity
    surface
  - launch records, per-agent logs, and session files — already keep run
    archaeology bundled under the run tree
- Duplicate or drifting paths relevant to this change:
  - `src/rally/services/runner.py`,
    `src/rally/services/home_materializer.py`,
    `src/rally/services/flow_loader.py`,
    `src/rally/adapters/codex/*`,
    `stdlib/rally/prompts/rally/base_agent.prompt`, and the Phase 4 and master
    design docs each carry part of today's adapter story
  - the field `runtime.adapter` is generic in `flow.yaml`, but shared runtime
    imports are still Codex-only. That split is current drift.
  - the durable docs still teach a Codex-first runtime truth even though the
    flow contract already hints at a wider adapter model
- Capability-first opportunities before new tooling:
  - use the existing Rally final JSON contract and run-home model as the fixed
    shared surface. Do not invent a second shared handoff or state file for
    Hermes.
  - use Hermes's Python API and callbacks before adopting the CLI path or ACP.
    The repo evidence already shows those surfaces exist.
  - keep `HERMES_HOME` nested inside the run home so Rally can translate
    allowlisted skills and MCPs into Hermes's world instead of letting Hermes
    discover machine-global defaults
  - keep the shared prompt and kernel-skill contract adapter-neutral. This
    change is a runtime generalization task, not a prompt-language task.
- Behavior-preservation signals already available:
  - `uv run pytest tests/unit -q` — shared regression floor; it passed before
    this research pass
  - `tests/unit/test_runner.py` — protects run and resume, handoff chaining,
    issue ledger writes, and adapter launch shape
  - `tests/unit/test_flow_loader.py` — protects runtime config and compiled
    contract validation
  - `tests/unit/test_launcher.py` — protects env and adapter-launch
    archaeology
  - `tests/unit/test_codex_event_stream.py` — protects current Codex event
    normalization during extraction
  - `tests/unit/test_run_events.py` — protects the shared event sink while
    adapter-specific parsers move

## 3.3 Decision gaps that must be resolved before implementation

- Resolved by deep-dive pass 1: the adapter boundary should be first-class and
  small. Repo evidence checked: `src/rally/services/runner.py`,
  `src/rally/services/home_materializer.py`,
  `src/rally/services/flow_loader.py`, and `src/rally/domain/flow.py`.
  Needed answer: use an adapter registry plus a runtime adapter contract that
  covers adapter arg validation, adapter-home bootstrap, session load/save,
  turn-artifact preparation, turn execution, and event emission.
- Resolved by deep-dive pass 1: shared runtime keeps the run state machine,
  issue ledger, command turn caps, and shared final-response loader. Repo
  evidence checked: `src/rally/services/runner.py`,
  `src/rally/services/run_events.py`,
  `stdlib/rally/prompts/rally/turn_results.prompt`, and
  `src/rally/adapters/codex/result_contract.py`. Needed answer: adapters
  produce one candidate final-response file, and Rally validates it once.
- Resolved by deep-dive pass 1: shared home materialization should keep run
  layout, compiled-agent sync, and allowlisted skill and MCP projection, while
  adapter-local config and auth move behind adapter hooks. Repo evidence
  checked: `src/rally/services/home_materializer.py`,
  `../hermes-agent/tools/skills_sync.py`, and
  `../hermes-agent/tools/mcp_tool.py`. Needed answer: keep Rally's policy in
  the shared layer and let adapters translate it for their own runtime.
- Resolved by deep-dive pass 1: Hermes v1 should be library-backed, use
  `HERMES_HOME` under the run home, disable interactive approval prompts, and
  fail loud on invalid final JSON. Repo evidence checked:
  `../hermes-agent/run_agent.py`, `../hermes-agent/hermes_constants.py`,
  `../hermes-agent/tools/approval.py`, and
  `../hermes-agent/acp_adapter/server.py`. Needed answer: no CLI scrape and no
  ACP client in v1.
- No user blocker question remains after deep-dive pass 1.
- Deep-dive pass 2 still needs to harden the delete list, the doc-sync set,
  and the proof matrix before phase planning begins.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Shared runtime orchestration lives in `src/rally/services/`, mainly
  `runner.py`, `home_materializer.py`, `run_events.py`, and `flow_loader.py`.
- The only real adapter tree today is `src/rally/adapters/codex/`.
- `flows/*/flow.yaml` already carries `runtime.adapter`, `runtime.adapter_args`,
  and `runtime.max_command_turns`, but only the Codex path is implemented.
- The run home layout is shared and fixed under `runs/<run-id>/home/`:
  `agents/`, `skills/`, `mcps/`, `sessions/`, `artifacts/`, `repos/`, and
  `issue.md`.
- Codex-specific files are written at the shared run-home root today:
  `config.toml`, plus `auth.json` and `.credentials.json` symlinks copied from
  `~/.codex`.
- Codex turn artifacts live under `home/sessions/<agent-slug>/turn-<n>/` as
  `exec.jsonl`, `stderr.log`, and `last_message.json`.
- Shared run logs live under `runs/<run-id>/logs/`:
  `events.jsonl`, `agents/*.jsonl`, `rendered.log`, and `adapter_launch/*.json`.

## 4.2 Control paths (runtime)

1. `run_flow()` and `resume_run()` rebuild the flow through Doctrine, load the
   compiled flow definition, and create or reload the run record.
2. `prepare_run_home_shell()` creates the shared run-home shell.
   `materialize_run_home()` then enforces `home/issue.md`, syncs compiled
   agents, copies the union of allowlisted skills and MCPs plus
   `rally-kernel`, writes Codex config, seeds Codex auth links, and runs the
   flow setup script once.
3. `_execute_single_turn()` resolves the current agent, builds the prompt,
   loads the previous Codex session, prepares turn artifacts, and invokes
   `_invoke_codex()`.
4. `_invoke_codex()` shells out to
   `codex exec --json --dangerously-bypass-approvals-and-sandbox -C <run-home> --output-schema <schema> -o <last-message-file> ...`,
   writes the launch proof file, and streams or captures stdout and stderr.
5. `CodexEventStreamParser` turns Codex JSON events into Rally `EventDraft`s,
   which `RunEventRecorder` writes into run and agent logs plus the rendered
   transcript.
6. The runner records the Codex session id, loads the final response from
   `last_message.json`, updates run state from the parsed Rally turn result,
   and appends issue-ledger blocks.
7. If Codex exits non-zero or times out, the runner blocks the run from a
   Codex-shaped failure path that reads stderr or the last stdout line.

## 4.3 Object model + key abstractions

- `FlowDefinition.adapter` stores `AdapterConfig(name, prompt_input_command, args)`.
  This is generic in data shape only.
- `FlowAgent`, `CompiledAgentContract`, `RunRecord`, `RunState`, and
  `TurnResult` are Rally-owned and already adapter-neutral enough.
- Codex-specific abstractions leak into shared runtime code today:
  `CodexSessionRecord`, `TurnArtifactPaths`, `CodexEventStreamParser`,
  `_CodexInvocation`, `build_codex_launch_env()`, and
  `load_agent_final_response()` from the Codex tree.
- The current runner therefore depends on subprocess return codes, stderr, and
  Codex JSON event shapes instead of an adapter-neutral execution contract.
- `load_agent_final_response()` is conceptually Rally-owned logic, but it is
  currently stored under `src/rally/adapters/codex/`, which hides the real
  ownership line.

## 4.4 Observability + failure behavior today

- `RunEventRecorder` is the shared event sink and writes the canonical run and
  agent logs plus `rendered.log`.
- Codex launch archaeology is written to `logs/adapter_launch/turn-<n>-<agent>.json`
  with the exact command, cwd, timeout, and filtered env.
- Codex session ids are captured from `thread.started` or `thread.resumed`
  events, then saved per agent in `home/sessions/<agent>/session.yaml`.
- Shared runner errors still use Codex-shaped wording such as "Launching
  Codex.", "Resuming Codex session", and "codex exec timed out".
- Invalid or missing final JSON is a hard runtime failure through
  `RallyStateError`, not a soft parse warning.
- There is no adapter-neutral event or failure surface yet. The shared
  runtime understands Codex stderr, Codex stdout, and Codex event frames
  directly.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No new UI layer is needed.

Current operator-facing surfaces are:

- `rally run <flow>`
- `rally resume <run-id>`
- the startup summary in `src/rally/terminal/display.py`, which already shows
  the adapter name from flow metadata
- live rendered events whose detail lines and lifecycle messages still include
  Codex-specific language

The important current truth is that the public commands are already adapter
agnostic, but some runtime messages are not.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Add one shared adapter boundary under `src/rally/adapters/`:
  - `base.py` for the adapter protocol plus shared adapter dataclasses
  - `registry.py` for supported adapter lookup and flow-loader validation
- Keep `src/rally/adapters/codex/`, but make it a full adapter implementation
  instead of a bag of helpers imported by shared runtime code.
- Add `src/rally/adapters/hermes/` as a full adapter implementation.
- Move the generic final-response loader out of the Codex tree into a shared
  Rally-owned module, because Rally owns final turn-result validation.
- Keep the shared run-home layout exactly where Rally already keeps it:
  `home/agents/`, `home/skills/`, `home/mcps/`, `home/artifacts/`,
  `home/repos/`, and `home/issue.md`.
- Keep Codex's exact launch rule: `CODEX_HOME` stays the shared run home.
  Codex session artifacts may keep using `home/sessions/`.
- Give Hermes an adapter-local root at `home/hermes/` and set
  `HERMES_HOME=home/hermes/`. Under that root:
  - `home/hermes/home/` is the subprocess `HOME`
  - `home/hermes/config.yaml` is Hermes config
  - `home/hermes/state.db` is Hermes state
  - `home/hermes/sessions/` holds Hermes-native session files
  - `home/hermes/skills/` and related runtime files are adapter-owned copies
    or links derived from Rally policy
- Keep shared run archaeology under `runs/<run-id>/logs/`. Each adapter writes
  one proof file per turn into `logs/adapter_launch/`, but the payload may be
  adapter-specific.

## 5.2 Control paths (future)

1. `load_flow_definition()` validates `runtime.adapter` through
   `src/rally/adapters/registry.py` and rejects unsupported adapter names or
   bad adapter args before runtime begins.
2. `run_flow()` and `resume_run()` keep ownership of flow locks, run ids,
   issue-ledger entry, and command-level run orchestration.
3. `materialize_run_home()` keeps ownership of shared layout, compiled-agent
   sync, allowlisted skill sync, allowlisted MCP sync, and setup-script
   execution, then calls `adapter.prepare_home(...)` for adapter-local config,
   auth, and translation work.
4. `_execute_single_turn()` resolves the adapter once from the flow and then
   uses the adapter contract to:
   - load the previous adapter session
   - prepare per-turn artifacts
   - execute the turn
   - record the new session id when one exists
5. During execution, the adapter emits Rally `EventDraft`s into the shared
   `RunEventRecorder`. Shared runtime no longer parses adapter wire formats
   directly.
6. After execution, shared runtime reads the adapter-provided
   `last_message.json` through one generic final-response loader and then
   keeps ownership of turn-result routing, run-state updates, issue-ledger
   writes, and command stop conditions.
7. Codex continues to use native `--output-schema` enforcement.
8. Hermes uses the library path: the adapter calls `AIAgent.run_conversation()`,
   takes `final_response`, writes it to `last_message.json`, and then relies on
   the same Rally final-response validation path. Missing or invalid JSON
   blocks the run loudly.
9. Hermes does not use `hermes chat -q -Q` in the supported path, and v1 does
   not add an ACP client.

## 5.3 Object model + abstractions (future)

- Add a small `RuntimeAdapter` protocol with these responsibilities:
  - validate adapter-specific args
  - prepare adapter-local home state
  - load and save adapter session state
  - prepare turn artifacts
  - execute one turn and emit `EventDraft`s
- Add shared adapter dataclasses:
  - `AdapterSessionRecord` with at least `session_id`, `updated_at`, and any
    adapter-private metadata pointer the adapter needs
  - `TurnArtifacts` with at least `turn_dir` and `last_message_file`, plus any
    adapter-private raw-output files the adapter wants to keep
  - `TurnExecution` with `ok`, `session_id`, and `failure_reason`
- `registry.py` becomes the only owner of supported adapter names and adapter
  factories.
- `runner.py` stops importing Codex classes directly. It depends only on the
  registry, the adapter protocol, Rally domain types, and the shared
  final-response loader.
- `home_materializer.py` stops knowing what `config.toml`, Codex auth symlinks,
  or Hermes `config.yaml` mean. It only knows when to call adapter bootstrap.
- `flow_loader.py` remains the front door for adapter validation, which keeps
  unsupported adapter names and bad adapter args out of the run path.

## 5.4 Invariants and boundaries

- Rally owns:
  - flow loading
  - run creation and resumption
  - flow locks
  - run state transitions
  - issue-ledger writes
  - command turn caps
  - the shared final JSON contract
  - the shared final-response loader
  - the shared event sink
- Adapters own:
  - adapter arg validation details
  - adapter-local home bootstrap
  - session storage format
  - turn artifact layout
  - launch or runtime invocation
  - translation from adapter-native progress into `EventDraft`s
- Shared allowlists remain Rally-owned. Adapters may translate those allowlists
  into their own runtime shape, but they may not widen skill, MCP, tool, auth,
  or approval access beyond Rally policy.
- Hermes v1 must run in a non-interactive Rally-managed mode. It must not stop
  for approval prompts. If Hermes cannot be put into that mode explicitly, the
  adapter is not supported.
- Codex keeps its exact current launch rule.
- No per-agent mixed-adapter path exists in v1.
- No new sidecar handoff artifact, parser shim, CLI scrape layer, or ACP client
  is allowed in v1.

## 5.5 UI surfaces (ASCII mockups, if UI work)

The operator surface stays:

- `rally run <flow>`
- `rally resume <run-id>`
- `rally issue note`

Required text-level changes only:

- shared lifecycle messages in the runner should stop naming Codex when the
  message is really adapter-neutral
- adapter-owned messages may still name the concrete adapter
- `logs/adapter_launch/` remains the launch-proof location for every adapter
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Adapter registry | `src/rally/adapters/registry.py` | new | Missing | Add supported-adapter lookup and adapter factory ownership | Flow loading and runner dispatch need one front door | `get_adapter(name)` plus adapter validation hooks | new adapter-registry tests |
| Adapter contract | `src/rally/adapters/base.py` | new | Missing | Add protocol plus shared adapter dataclasses | Shared runtime needs one stable seam | `RuntimeAdapter`, `AdapterSessionRecord`, `TurnArtifacts`, `TurnExecution` | new contract coverage plus `tests/unit/test_runner.py` |
| Flow loading | `src/rally/services/flow_loader.py` | `load_flow_definition()` | Reads any adapter string and raw args | Validate supported adapter names and adapter-specific args | Stop carrying a fake-generic runtime.adapter field | flow-loader validation through registry | `tests/unit/test_flow_loader.py` |
| Shared runtime | `src/rally/services/runner.py` | top-level imports, `_execute_single_turn()`, `_invoke_codex()` | Imports and calls Codex helpers directly | Resolve adapter once and dispatch through the adapter contract | Shared runtime must stop knowing Codex wire rules | adapter-neutral turn execution path | `tests/unit/test_runner.py` |
| Shared final response loader | `src/rally/adapters/codex/result_contract.py` | `load_agent_final_response()` | Rally-owned final JSON validation lives under the Codex tree | Move to a shared Rally-owned module and update imports | Final JSON validation is not Codex-specific | generic `load_agent_final_response()` on `last_message.json` | `tests/unit/test_result_contract.py`, `tests/unit/domain/test_turn_result_contracts.py`, `tests/unit/test_runner.py` |
| Shared home materialization | `src/rally/services/home_materializer.py` | `materialize_run_home()`, `_write_codex_config()`, `_seed_codex_auth()` | Shared home setup writes Codex config and auth directly | Keep shared sync/setup work and call adapter bootstrap hooks for adapter-local config and auth | Hermes cannot reuse Codex bootstrap, and shared policy should stay shared | `adapter.prepare_home(...)` after shared sync | new home-materialization coverage plus `tests/unit/test_runner.py` |
| Codex adapter | `src/rally/adapters/codex/launcher.py`, `session_store.py`, `event_stream.py` | current modules | Useful Codex behavior exists but is partly orchestrated from shared runtime | Wrap these under a first-class Codex adapter implementation | Preserve current behavior while removing shared-runtime leaks | Codex adapter owns launch, session, artifacts, and event mapping | `tests/unit/test_launcher.py`, `tests/unit/test_codex_event_stream.py`, `tests/unit/test_runner.py` |
| Hermes adapter | `src/rally/adapters/hermes/adapter.py` and supporting modules | new | Missing | Implement library-backed Hermes adapter, nested `HERMES_HOME`, adapter-local config/session/event mapping, and `last_message.json` writeback | Support Hermes cleanly without a CLI scrape | Hermes adapter owns `AIAgent` bridge, session store, artifacts, home bootstrap, and event mapping | new Hermes adapter tests plus `tests/unit/test_runner.py` |
| Event sink | `src/rally/services/run_events.py` | `EventDraft` and `RunEventRecorder` | Already shared but only fed by Codex parser today | Keep unchanged at the sink boundary and confirm both adapters emit into it | Avoid a second logging plane | adapters emit `EventDraft`s; recorder stays shared | `tests/unit/test_run_events.py`, `tests/unit/test_runner.py` |
| CLI display | `src/rally/terminal/display.py` and shared runner lifecycle messages | adapter summary and launch messages | Startup summary is adapter-aware, but some lifecycle text is Codex-only | Keep the small shared operator surface and remove stale Codex-only wording where it is really generic | Multi-adapter runtime should not mislabel shared actions | adapter-neutral lifecycle text with adapter-specific detail only where truthful | targeted display coverage if needed |
| Runtime docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` | current runtime narrative | Durable docs still teach a Codex-first runtime | Update docs in the same pass as the code change | Keep durable repo truth aligned with shipped behavior | doc updates only | doc review |

## 6.2 Migration notes

Canonical owner path / shared code path:

- Shared runtime stays in `src/rally/services/runner.py`,
  `src/rally/services/home_materializer.py`, and
  `src/rally/services/run_events.py`.
- Adapter-specific mechanics move under `src/rally/adapters/<name>/`.
- Shared final-response validation moves out of the Codex tree into a Rally
  shared module.

Deprecated APIs (if any):

- direct Codex imports from `src/rally/services/runner.py`
- direct Codex bootstrap helpers inside `src/rally/services/home_materializer.py`
- using `src/rally/adapters/codex/result_contract.py` as if it were
  adapter-specific

Delete list (what must be removed; include superseded shims/parallel paths if any):

- `_invoke_codex()` and `_CodexInvocation` from shared `runner.py`
- `_write_codex_config()` and `_seed_codex_auth()` from shared
  `home_materializer.py`
- any compatibility branch in shared runtime that switches on `"codex"` versus
  `"hermes"` instead of dispatching through the registry
- any Hermes CLI wrapper or ACP bridge added as a parallel v1 path

Capability-replacing harnesses to delete or justify:

- reject `hermes chat -q -Q` as the supported adapter path
- reject a v1 ACP client path unless later planning proves the Python adapter
  surface cannot satisfy Rally's event and result needs

Live docs/comments/instructions to update or delete:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- any shared runner comments or log messages that still name Codex when the
  behavior is actually adapter-neutral

Behavior-preservation signals for refactors:

- `uv run pytest tests/unit -q`
- `tests/unit/test_runner.py`
- `tests/unit/test_flow_loader.py`
- `tests/unit/test_result_contract.py`
- `tests/unit/domain/test_turn_result_contracts.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_codex_event_stream.py`
- `tests/unit/test_run_events.py`

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Runtime dispatch | `src/rally/services/runner.py` | resolve one adapter once and execute through the adapter contract | stops new harnesses from reopening shared-runtime branches | include |
| Flow validation | `src/rally/services/flow_loader.py` | validate adapter names and adapter args through the registry | keeps unsupported adapters out of the run path | include |
| Home bootstrap | `src/rally/services/home_materializer.py` | keep shared policy sync in Rally and push adapter-local bootstrap behind hooks | prevents Codex bootstrap from becoming framework law | include |
| Final-response loading | shared Rally-owned loader | every adapter writes one `last_message.json` and Rally validates it once | preserves one turn-ending control path | include |
| Adapter logs | `logs/adapter_launch/` plus adapter event emitters | each adapter owns its own launch proof and event mapping into `EventDraft` | keeps run archaeology bundled without a second log plane | include |
| Operator wording | shared runner lifecycle messages and display text | adapter-neutral wording in shared text; adapter name only when truthful | keeps the CLI small and honest as adapters grow | include |
| Per-agent capability enforcement | run-home skill and MCP isolation rules | keep current union-of-flow allowlist model until a later runtime plan changes it on purpose | this plan should not widen into per-agent isolation work | defer |
| ACP integration | Hermes ACP server and any future Rally ACP client | rich event transport only if the library path later proves insufficient | avoid an unnecessary v1 control surface | exclude |
<!-- arch_skill:block:call_site_audit:end -->

# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

Phase planning is intentionally deferred until `research` and `deep-dive`
resolve the adapter boundary, the Hermes integration plane, and the final-result
contract.

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- Keep `uv run pytest tests/unit -q` as the shared proof floor.
- Prefer adapter-neutral runtime tests plus adapter-specific tests at the new
  boundary.
- Add tests only where they protect shipped behavior or the new adapter
  contract.

## 8.2 Integration tests (flows)

- Use the smallest honest Rally-run proof for adapter dispatch once the design
  is implemented.
- Prefer one flow or fixture that proves the shared run path can use Hermes
  without creating a second operator surface.

## 8.3 E2E / device tests (realistic)

- Manual CLI proof is enough unless the implementation reveals a stronger
  existing harness.
- Do not build a custom end-to-end harness just to say the second adapter
  exists.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land the adapter boundary before landing Hermes-specific behavior on top of
  Codex-only shared runtime code.
- Keep the existing Codex path working while Hermes support is still partial.
- Do not claim Hermes is supported until the strict final-result rule and
  run-home policy are real.

## 9.2 Telemetry changes

- Reuse current Rally run events, adapter launch records, agent logs, and run
  state where possible.
- Add only the adapter-aware event or launch fields needed to keep run
  archaeology honest.

## 9.3 Operational runbook

- The operator surface should stay `rally run` and `rally resume`.
- Unsupported adapter states should fail loud with a clear message that names
  the broken adapter contract.
- Any new adapter-local files should live in the run tree and be inspectable
  without extra tools.

# 10) Decision Log (append-only)

## 2026-04-13 - Bootstrap the Hermes adapter plan from the audit

Context

The repo already has a grounded Hermes audit, but it is not yet a canonical
full-arch implementation plan.

Options

- Treat the audit as the whole plan.
- Create a new canonical plan doc and fold the audit into later research and
  deep-dive work.

Decision

Create a canonical full-arch plan doc. Treat the audit as strong input, not as
the final planning artifact.

Consequences

- The audit stays useful as evidence and as a pressure test.
- This plan becomes the one planning source of truth.
- Later `arch-step` commands should deepen this doc instead of starting a new
  sidecar plan.

Follow-ups

- Confirm the North Star.
- Run `research` against this doc.

## 2026-04-13 - Make adapters first-class runtime owners

Context

Deep-dive pass 1 confirmed that Rally already has a generic adapter field in
`flow.yaml`, but the live runtime still imports Codex helpers directly from
shared runtime code. The main choice was whether to add Hermes with another
branch or to make adapters first-class.

Options

- Keep Codex logic in shared runtime and add one Hermes branch beside it.
- Add a Hermes CLI scrape path as the fastest second harness.
- Add a small adapter registry and protocol, move wire details under
  `src/rally/adapters/<name>/`, keep one shared final-response loader, and use
  a library-backed Hermes adapter.

Decision

Choose the registry-and-protocol path. Shared runtime keeps the run model,
issue ledger, and final turn-result handling. Codex remains a first-class
adapter behind that boundary. Hermes v1 uses the Python `AIAgent` surface, a
nested `HERMES_HOME`, and the same Rally final JSON rule.

Consequences

- Shared runtime gets smaller and clearer.
- Codex-specific wording, imports, and bootstrap logic have to move out of
  shared runtime code.
- Hermes support becomes a real runtime addition instead of a wrapper spike.
- ACP and a Hermes CLI scrape stay out of v1.

Follow-ups

- Use deep-dive pass 2 to harden the delete list and proof matrix.
- Use phase planning to sequence the adapter extraction before Hermes-specific
  work.
