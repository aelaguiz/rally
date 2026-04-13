---
title: "Rally - Claude Code First-Class Adapter Support - Architecture Plan"
date: 2026-04-13
status: active
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
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/domain/flow.py
  - src/rally/domain/run.py
  - src/rally/services/flow_loader.py
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/services/run_store.py
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
subscription login. That matters for a later fully isolated mode, but it should
not block pragmatic first-class support if Rally can use the user's existing
Claude login the same way the user already runs Claude locally.

## Approach

Use the current Hermes runtime-generalization work as the shared adapter
boundary plan, then fold Claude-specific truth into that same runtime story.
Start Claude support with the Claude Code CLI, not the SDK. Use the user's
existing Claude login and config for v1 unless a tighter adapter-owned auth mode
is needed later. Keep one shared Rally turn-result path, generate only the
adapter artifacts Rally actually needs, and avoid taking on auth complexity that
does not buy practical value yet.

## Plan

1. Establish the shared adapter boundary, registry, and Rally-owned
   final-response loader without widening the supported runtime yet.
2. Cut Codex over to that shared adapter contract while preserving current
   run-home layout, launch behavior, and refresh-on-resume bootstrap.
3. Add the CLI-backed `claude_code` adapter with stdin prompt delivery, strict
   MCP and tool clamps, truthful event mapping, and the ambient-auth v1 path.
4. Delete superseded shared-runtime paths, prove both adapters through Rally,
   and sync the surviving runtime docs to one honest multi-adapter story.

## Non-negotiables

- No second turn-ending control path. Rally still ends a turn with notes plus
  one final JSON result.
- `claude_code` must be a real adapter, not a Codex alias and not a thin shell
  rename.
- Do not add per-run Claude login or token bootstrap if Rally can use the
  user's existing Claude auth safely for local support.
- Clamp ambient Claude behavior with explicit flags and generated config where
  Claude supports it. Do not make perfect clean-room Claude isolation a v1
  blocker.
- No mixed per-agent adapter story in v1. Adapter choice stays flow-wide.
- No "best effort" final-result parse path. Claude runs must satisfy the same
  strict final JSON rule as Codex runs.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: done 2026-04-13
deep_dive_pass_2: done 2026-04-13
recommended_flow: planning complete -> implement or implement-loop
note: External grounding is already folded here through `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`. The planning arc is complete when the consistency helper below says the doc is decision-complete. This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support `runtime.adapter: claude_code` beside `runtime.adapter:
codex` without breaking its current runtime model, without leaving Codex-only
logic spread through shared runtime code, and without making isolated Claude
auth a gating requirement for pragmatic local support.

This claim is true only if all of this is true:

- `flow.yaml` can name `claude_code` and Rally accepts it through the same flow
  load and run entrypoints it already uses for Codex.
- Shared runtime code no longer imports or calls Codex helpers directly where
  an adapter boundary should own the work.
- Codex still works after the refactor through the same public CLI and run-home
  contract.
- Claude Code uses the same Rally issue-ledger, turn-result, and run-state
  model rather than inventing a second side channel.
- The supported Claude path has one explicit v1 auth story, and that story can
  be "use the user's existing Claude login and config" if that is the most
  practical local path.
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
- Support one explicit Claude auth story for v1, with ambient existing Claude
  auth allowed if it is the most practical path.
- Generate only the Claude adapter artifacts Rally actually needs inside the
  run home, such as strict MCP config.
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
- update or delete stale docs and comments that still teach a Codex-only or
  Hermes-only runtime shape

## 0.3 Out of scope

- Mixed-adapter flows where one flow uses both Codex and Claude in the same
  run.
- A Claude SDK-first implementation for v1.
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
- The supported Claude path has one documented supported auth mode for v1, and
  that mode works in real local use without extra per-run login steps.
- Rally still ends turns with one validated final JSON result.
- Rally's skill and MCP allowlists still hold when Claude is the adapter.
- The main Rally design docs and runtime-detail docs match the shipped design.

Behavior-preservation evidence:

- `uv run pytest tests/unit -q` stays green through the refactor
- existing Codex-focused unit tests keep passing or move cleanly behind
  adapter-neutral seams
- new unit coverage proves adapter validation, adapter dispatch, and
  adapter-owned home, session, result, and event behavior
- one honest Claude proof exists through Rally using the supported v1 auth
  story, or the exact blocker is named plainly in this doc before the work is
  called complete

## 0.5 Key invariants (fix immediately if violated)

- One flow has one adapter.
- Notes stay context-only.
- Final JSON stays the only turn-ending control path.
- Claude v1 must clamp every ambient Claude surface that the CLI lets Rally
  clamp, and the docs must name the remaining ambient dependency honestly.
- No adapter may widen tool, skill, MCP, or auth access past Rally policy.
- No silent fallback or compatibility shim masks a broken adapter contract.
- No docs keep teaching a narrower runtime story than the shipped code.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make Claude support fit Rally's current runtime law instead of teaching
   Rally to special-case a second runner.
2. Keep Codex stable while opening a clean path for Claude.
3. Make the supported Claude path honest about which parts use ambient user
   state and which parts Rally owns.
4. Keep the operator surface small: same CLI, same run-home model, same final
   result rule.
5. Remove stale doc truth in the same pass so the design docs match the code.

## 1.2 Constraints

- `src/rally/services/runner.py` still launches Codex directly today.
- `src/rally/services/home_materializer.py` still writes Codex config and auth
  links only.
- The Claude audit already proved a fresh `CLAUDE_CONFIG_DIR` loses normal
  subscription login on this machine, which matters only if we choose an
  isolated Claude mode.
- Using the user's existing Claude login likely means v1 cannot rely on
  `--bare`, so some ambient Claude behavior must be clamped with the flags
  Claude exposes rather than assumed away.
- Claude Code has stronger CLI support than the older Hermes assumptions, but
  its config and auth model still differ from Codex.
- Rally's current design docs still talk about a Codex-first vertical slice and
  a Hermes second-adapter plan, not a shipped Codex plus Claude runtime.

## 1.3 Architectural principles (rules we will enforce)

- Shared runtime code depends on an adapter contract, not on Codex or Claude
  helpers directly.
- Shared runtime owns only the adapter artifacts and state it truly needs.
- Do not force isolated auth or config ownership where ambient user auth is the
  more practical supported path.
- Clamp ambient Claude behavior where flags allow it, and document any
  remaining ambient dependency instead of pretending v1 is fully isolated.
- Rally keeps one shared turn-result rule even when adapters differ in output
  envelope shape.
- Folded docs must tell the same runtime story as the shipped code.

## 1.4 Known tradeoffs (explicit)

- CLI-first Claude support is simpler and closer to Rally's current runtime,
  but it gives less native structure than a future SDK path.
- Using ambient existing Claude auth is easier for local users, but it means
  Rally should be explicit that not every Claude file lives inside the run
  home in v1 and that some ambient Claude behavior may remain unless flags can
  clamp it.
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
- Claude support has no current adapter, no documented v1 auth stance, no
  settled prompt-delivery rule, and no generated MCP config path.
- The runtime docs do not yet say whether Claude changes the current Hermes
  plan, folds into it, or replaces parts of its adapter story.

## 2.3 Constraints implied by the problem

- We need one canonical adapter story, not a Codex plan plus a separate Claude
  story that drifts.
- The Claude path must be explicit about supported auth behavior from the
  start, even if the v1 answer is "use the user's existing Claude login."
- We cannot call the Claude path first-class until the code and docs agree on
  what "supported" means.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- Official Claude Code CLI, headless, auth, settings, permissions, MCP,
  environment, memory, subagent, and SDK docs, folded through
  `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`
  — adopt CLI-first Claude support for v1; adopt JSON-schema output, stream
  output, resume, MCP config injection, and tool gating as the native
  capability baseline; reject SDK-first as the default first move because the
  current user-approved direction is to piggyback on the user's existing Claude
  login when practical.
- `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`
  — adopt as the folded external-research digest and local proof pack for this
  plan; it already captured the official Claude surfaces plus local CLI checks,
  including the auth and `CLAUDE_CONFIG_DIR` findings.
- `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
  — adopt the shared adapter-boundary direction; reject treating Claude support
  as a one-off runtime path outside that boundary; keep this Claude plan as the
  canonical driver for Claude-specific scope while converging the shared
  adapter story back into one truthful runtime design.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/flow_loader.py`
    — defines the current flow contract for `runtime.adapter`,
    `runtime.adapter_args`, and `runtime.prompt_input_command`.
  - `src/rally/domain/flow.py`
    — defines `AdapterConfig` and keeps adapter choice generic in the flow
    model even though the runtime path is still Codex-shaped.
  - `src/rally/services/runner.py`
    — is the current shared orchestration owner, but still imports Codex
    launch, event, session, and result helpers directly; also builds the agent
    prompt from compiled `AGENTS.md` plus runtime prompt inputs.
  - `src/rally/services/home_materializer.py`
    — owns the shared run-home shell, agent sync, skill and MCP allowlist
    copying, current Codex config generation, and current Codex auth seeding.
  - `src/rally/domain/run.py` and `src/rally/services/run_store.py`
    — define the persisted `run.yaml` and `state.yaml` contract, including the
    stored adapter name Rally already exposes to operators.
  - `src/rally/adapters/codex/launcher.py`
    — defines the current launch-env contract and adapter launch proof shape.
  - `src/rally/adapters/codex/session_store.py`
    — defines per-agent session storage and turn artifact paths.
  - `src/rally/adapters/codex/result_contract.py`
    — proves Rally already has a shared turn-result rule once an adapter can
    produce one valid final JSON object file.
- Canonical path / owner to reuse:
  - Keep shared orchestration in `src/rally/services/runner.py` and shared
    run-home preparation in `src/rally/services/home_materializer.py`, while
    moving adapter-specific launch, session, event, and result-envelope work
    below `src/rally/adapters/<adapter>/`.
- Existing patterns to reuse:
  - `src/rally/adapters/codex/launcher.py`,
    `src/rally/adapters/codex/event_stream.py`,
    `src/rally/adapters/codex/session_store.py`, and
    `src/rally/adapters/codex/result_contract.py`
    — already split the main adapter concerns into useful seams that a shared
    adapter contract can wrap instead of rewriting the runtime from scratch.
  - `src/rally/services/home_materializer.py`
    — already copies allowlisted skills and MCPs into the run home and is the
    right shared place to decide what remains generic versus adapter-owned.
  - `src/rally/services/runner.py`
    — already injects compiled prompt readback plus runtime prompt inputs on
    stdin, which means Claude support does not need a new prompt authoring
    surface to get started.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
    — defines the shared Rally-managed note, run-home, and final-JSON rules.
  - `stdlib/rally/prompts/rally/turn_results.prompt`
    — defines the default shared Rally turn-result contract.
  - `skills/rally-kernel/prompts/SKILL.prompt`
    — defines the shared Rally skill that preserves the one-note, one-final-JSON
    rule and keeps route truth out of notes.
- Native model or agent capabilities to lean on:
  - Claude Code CLI
    — already supports `-p`, `--output-format json`, `--output-format
    stream-json`, `--json-schema`, `--resume`, `--continue`, `--mcp-config`,
    `--strict-mcp-config`, `--tools`, and `--allowedTools`, so Rally should
    use those native surfaces before inventing wrappers or parser-heavy side
    paths.
- Existing grounding / tool / file exposure:
  - `src/rally/services/runner.py`
    — `_build_agent_prompt()` and `_load_prompt_inputs()` already give the
    runner one clean way to inject compiled prompt text and runtime grounding.
  - `src/rally/services/home_materializer.py`
    — already projects allowlisted skills and MCPs into the run home, so Claude
    support should adapt that path instead of inventing a second capability
    projection system.
- Duplicate or drifting paths relevant to this change:
  - `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
    — overlaps the shared adapter-boundary story and will need convergence so
    Claude support does not live in a separate runtime narrative.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
    — still teach a Codex-first runtime truth and will need sync in the same
    change once the code lands.
- Capability-first opportunities before new tooling:
  - Use Claude's native JSON-schema output and result envelope instead of
    scraping assistant prose.
  - Use the current Rally stdin prompt injection path instead of adding a
    second Claude-only prompt graph or instruction layer.
  - Use generated Claude MCP config plus existing skill and tool allowlists
    before inventing a second control plane for Claude capabilities.
  - Accept ambient existing Claude auth for v1 rather than inventing token
    bootstrap or isolated auth machinery that the user has already said does
    not buy enough practical value yet.
- Behavior-preservation signals already available:
  - `tests/unit/test_runner.py`
    — protects the shared run and resume flow.
  - `tests/unit/test_launcher.py`
    — protects current launch-env and launch-record behavior.
  - `tests/unit/test_codex_event_stream.py`
    — protects current Codex event mapping behavior.
  - `tests/unit/test_result_contract.py`
    — protects the shared turn-result parsing rule.
  - `tests/unit/test_flow_loader.py`
    — protects flow config loading and adapter config parsing.
  - `tests/unit/test_run_store.py`
    — protects persisted run metadata, including truthful adapter names in
    `run.yaml`.
  - `tests/unit/test_run_events.py`
    — protects run-event rendering and display behavior.

## 3.3 Decision gaps that must be resolved before implementation

- None at the end of this research pass. The confirmed v1 auth story is
  "use the user's existing Claude login and config," and the practical design
  consequence is to clamp ambient Claude behavior where flags allow it and
  document any remaining ambient dependency instead of blocking on full
  isolation.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Shared runtime ownership is split across:
  - `src/rally/services/runner.py`
  - `src/rally/services/home_materializer.py`
  - `src/rally/services/flow_loader.py`
  - `src/rally/services/run_events.py`
  - `src/rally/cli.py`
- Codex-specific helper code already exists under:
  - `src/rally/adapters/codex/launcher.py`
  - `src/rally/adapters/codex/event_stream.py`
  - `src/rally/adapters/codex/result_contract.py`
  - `src/rally/adapters/codex/session_store.py`
- The problem is not that Codex code is missing a folder. The problem is that
  shared services still import those Codex modules directly and therefore still
  own Codex wire behavior in practice.
- Shared run-home layout today is created in
  `src/rally/services/home_materializer.py` and includes:
  - `home/agents/`
  - `home/skills/`
  - `home/mcps/`
  - `home/sessions/`
  - `home/artifacts/`
  - `home/repos/`
  - `home/issue.md`
- Current adapter-specific files are still written at the shared run-home root:
  - Codex config at `home/config.toml`
  - Codex auth links at `home/auth.json` and `home/.credentials.json`
- Run metadata already persists `adapter_name` in `run.yaml` through
  `src/rally/domain/run.py` and `src/rally/services/run_store.py`, so the
  operator-visible run record already expects truthful adapter names.

## 4.2 Control paths (runtime)

Today the live control path is:

1. `load_flow_definition()` reads `runtime.adapter` and raw `adapter_args`, but
   does not validate adapter names through a supported-adapter registry.
2. `materialize_run_home()` prepares the shared run-home shell, copies compiled
   agents, projects allowlisted skills and MCPs, then writes Codex config and
   Codex auth directly before the one-time home-ready early return.
3. `_execute_single_turn()` in `runner.py` prepares turn artifacts through the
   Codex session store, builds the agent prompt from the compiled `AGENTS.md`
   plus any runtime prompt inputs, loads a Codex session if one exists, and
   invokes Codex directly.
4. `_invoke_codex()` builds one Codex-specific command line, one Codex-specific
   launch env, and one Codex-specific launch proof file.
5. Shared runner code parses Codex stdout through `CodexEventStreamParser`,
   writes Codex-shaped raw artifacts, stores the Codex session id, and then
   reads the final JSON from `last_message.json` through a loader that still
   lives under the Codex tree.
6. Shared Rally code then takes back over for run-state updates, issue-ledger
   writes, handoff routing, done and blocker handling, and the command-level
   stop result.

The public CLI front door is already adapter-neutral. The execution path behind
it is not.

## 4.3 Object model + key abstractions

- `FlowDefinition.adapter` stores `AdapterConfig(name, prompt_input_command,
  args)` in `src/rally/domain/flow.py`. That part is already generic enough.
- `RunRecord`, `RunState`, `TurnResult`, and compiled-agent metadata are also
  Rally-owned and already close to adapter-neutral.
- The abstractions that still leak Codex into shared runtime are:
  - `CodexEventStreamParser`
  - `build_codex_launch_env()`
  - `write_codex_launch_record()`
  - `load_session()`
  - `record_session()`
  - `prepare_turn_artifacts()`
  - `_invoke_codex()`
  - `load_agent_final_response()` via the Codex import path
- `_build_agent_prompt()` and `_load_prompt_inputs()` in `runner.py` already
  define one strong shared prompt path: Rally composes the compiled prompt text
  plus runtime prompt inputs before any adapter launch.

## 4.4 Observability + failure behavior today

- `RunEventRecorder` is the shared sink and already gives Rally one run log,
  one rendered log, and one event display path.
- `src/rally/cli.py` and `src/rally/terminal/display.py` already render
  `adapter`, `model`, and `thinking` from flow config at the shared CLI layer.
- `logs/adapter_launch/turn-<n>-<agent>.json` is already the operator-visible
  proof surface for exact adapter launch inputs.
- `home/sessions/<agent>/turn-<n>/exec.jsonl`,
  `home/sessions/<agent>/turn-<n>/stderr.log`, and
  `home/sessions/<agent>/turn-<n>/last_message.json` are already the stable
  turn-artifact paths.
- Invalid or missing final JSON is already a hard runtime failure through
  `RallyStateError`.
- Adapter-native stdout is currently replayed through Codex-owned parsing and
  Codex-owned `source="codex"` stderr events in shared `runner.py`.
- Failure wording and some lifecycle messages are still Codex-specific in
  shared runtime code even when the underlying action is really adapter-neutral.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface is needed.

The operator-facing surfaces that matter are:

- `rally run <flow>`
- `rally resume <run-id>`
- `rally issue note`
- the startup header in `src/rally/terminal/display.py`
- live rendered run events

The important current truth is that the front door already shows adapter name,
model, and thinking fields, but the runner and docs still assume a Codex-first
runtime underneath.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Add one shared adapter boundary under `src/rally/adapters/`:
  - `base.py` for the adapter protocol plus shared adapter dataclasses
  - `registry.py` for supported-adapter lookup and adapter-specific arg
    validation
- Keep `src/rally/adapters/codex/`, but add
  `src/rally/adapters/codex/adapter.py` as the first-class Codex adapter
  entrypoint.
- Add `src/rally/adapters/claude_code/` with at least:
  - `adapter.py`
  - `event_stream.py`
  - `session_store.py`
  - `launcher.py`
- Move the generic final-response loader out of the Codex tree into
  `src/rally/services/final_response_loader.py`, because Rally owns the final
  turn-result rule after an adapter has produced one valid final JSON object.
- Keep the shared run-home shell exactly where Rally already keeps it:
  `home/agents/`, `home/skills/`, `home/mcps/`, `home/sessions/`,
  `home/artifacts/`, `home/repos/`, and `home/issue.md`.
- Preserve native adapter file placement when the adapter CLI contract requires
  it. For Codex, that means the adapter may keep using `home/config.toml`,
  `home/auth.json`, and `home/.credentials.json` because `CODEX_HOME` points at
  the run-home root.
- Add a minimal Claude adapter-private root only for artifacts Rally actually
  needs, for example `home/claude_code/`, and keep it small:
  - generated `mcp.json` for `--mcp-config`
  - optional generated settings or helper files only if later implementation
    proves they are needed
- Do not move Claude auth under the run home in v1. The supported Claude path
  uses the user's existing Claude login and config.

## 5.2 Control paths (future)

1. `load_flow_definition()` validates `runtime.adapter` through
   `src/rally/adapters/registry.py` and rejects unsupported adapter names or
   bad adapter args before runtime begins.
2. `run_flow()` and `resume_run()` keep ownership of flow locks, run ids,
   issue-ledger entry, and command-level orchestration.
3. `materialize_run_home()` keeps ownership of shared layout, compiled-agent
   sync, skill projection, MCP projection, and setup-script execution. It then
   calls `adapter.prepare_home(...)` before the one-time home-ready early
   return so each adapter can refresh the adapter-specific artifacts it needs
   on every start and resume.
4. `_execute_single_turn()` resolves the adapter once from the flow and then
   uses the adapter contract to:
   - load any previous session
   - prepare per-turn artifacts
   - execute the turn
   - emit Rally `EventDraft`s
   - save a new session id when one exists
5. After the adapter finishes, shared Rally code reads one
   `last_message.json` file through the shared final-response loader and keeps
   ownership of turn-result routing, run-state updates, issue-ledger writes,
   and command stop conditions.
6. Codex continues to use its current native `--output-schema` path.
7. Claude uses the Claude Code CLI in `-p` mode, with the Rally prompt passed
   on stdin, not through a second prompt-file layer. The supported v1 Claude
   execution shape is:
   - `--output-format stream-json --verbose` for live event mapping
   - `--json-schema <schema>` for strict structured output
   - `--permission-mode dontAsk` for non-interactive runs
   - `--resume <session-id>` when resuming a saved agent session
   - `--strict-mcp-config --mcp-config <generated-json>` so Rally owns the MCP
     surface for the run
   - explicit `--tools` and `--allowedTools` flags so Rally clamps built-in
     tool access instead of relying on the user's global Claude defaults
   - no `--bare` and no `CLAUDE_CONFIG_DIR` override in the supported v1 path,
     because v1 intentionally uses the user's existing Claude login and config
8. The Claude adapter parses the stream-json event feed, writes the final
   structured output to `last_message.json`, records the session id, and maps
   Claude progress into Rally `EventDraft`s.

## 5.3 Object model + abstractions (future)

- Add a small `RuntimeAdapter` protocol with these responsibilities:
  - validate adapter-specific args
  - prepare adapter-local home artifacts
  - load and save adapter session state
  - prepare turn artifacts
  - execute one turn and emit `EventDraft`s
- Add shared adapter dataclasses:
  - `AdapterSessionRecord` with at least `session_id`, `updated_at`, and any
    adapter-private metadata pointer the adapter needs
  - `TurnArtifacts` with at least `turn_dir`, `exec_jsonl_file`,
    `stderr_file`, and `last_message_file`
  - `TurnExecution` with `returncode`, `session_id`, `stdout_text`,
    `stderr_text`, and any adapter-owned structured payload the shared runtime
    needs
- `registry.py` becomes the only owner of supported adapter names and adapter
  factories.
- `runner.py` stops importing Codex classes directly. It depends only on the
  registry, the adapter protocol, Rally domain types, and the shared
  final-response loader.
- `home_materializer.py` stops knowing what Codex config files or Claude CLI
  flags mean. It only knows when to call adapter bootstrap.
- Keep shared adapter args where they already fit:
  - `model`
  - `reasoning_effort`
- Let the registry map those shared args into adapter-native flags:
  - Codex maps `reasoning_effort` to its current config form
  - Claude maps `reasoning_effort` to Claude CLI `--effort`
- Keep adapter-specific args validated below the registry boundary:
  - Codex keeps `project_doc_max_bytes`
  - Claude may add only the extra args it really needs, such as
    `max_budget_usd` or a stricter permission-mode override

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
  - adapter-local home artifacts
  - session storage format
  - turn artifact preparation
  - launch or runtime invocation
  - translation from adapter-native progress into `EventDraft`s, including
    truthful adapter source names
- Shared allowlists remain Rally-owned. Adapters may translate those allowlists
  into their own runtime shape, but they may not widen tool, skill, MCP, or
  auth access beyond Rally policy.
- Claude v1 keeps the user's existing login and config, but the adapter must
  still clamp the parts Claude exposes as runtime flags:
  - built-in tools via `--tools`
  - auto-approved built-in tools via `--allowedTools`
  - MCP servers via `--strict-mcp-config --mcp-config`
- Claude v1 does not yet claim that Rally suppresses ambient `CLAUDE.md`,
  plugins, hooks, or auto memory. The supported story is narrower: Rally
  clamps the surfaces Claude exposes as runtime flags and documents the
  remaining ambient dependency honestly.
- V1 does not require `--bare`, does not claim full clean-room Claude
  isolation, and must document that remaining ambient dependency plainly.
- No per-agent mixed-adapter path exists in v1.
- No new sidecar handoff artifact, prompt graph, parser shim, or wrapper path
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
- the startup header may keep showing `model`, `thinking`, and `adapter`, but
  the values must now be truthful for both Codex and Claude
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Adapter registry | `src/rally/adapters/registry.py` | new | Missing | Add supported-adapter lookup plus adapter-specific arg validation | Flow loading and runner dispatch need one front door | `get_adapter(name, args)` and validation hooks | new registry coverage |
| Adapter contract | `src/rally/adapters/base.py` | new | Missing | Add protocol plus shared adapter dataclasses | Shared runtime needs one stable seam | `RuntimeAdapter`, `AdapterSessionRecord`, `TurnArtifacts`, `TurnExecution` | new contract coverage plus `tests/unit/test_runner.py` |
| Flow loading | `src/rally/services/flow_loader.py` | `load_flow_definition()` | Reads any adapter string and raw args | Validate supported adapters and adapter args through the registry | Stop carrying a fake-generic runtime adapter field | registry-backed validation | `tests/unit/test_flow_loader.py` |
| Flow model | `src/rally/domain/flow.py` | `AdapterConfig` | Carries generic name, prompt_input_command, and args | Keep the model, but let the registry define which args are shared vs adapter-specific | Preserve the existing flow contract where possible | `AdapterConfig` stays generic; validation moves out | `tests/unit/test_flow_loader.py` |
| Run metadata | `src/rally/domain/run.py`, `src/rally/services/run_store.py` | `RunRecord.adapter_name`, `create_run()`, `load_run_record()` | Run records already persist the adapter name but do not need to know adapter internals | Keep the stored adapter name truthful, stable, and adapter-neutral while preserving the same run record shape | The operator-visible run record is already part of Rally archaeology | unchanged `RunRecord` shape with stricter supported-adapter truth upstream | `tests/unit/test_run_store.py`, targeted runner coverage |
| Shared runtime | `src/rally/services/runner.py` | imports, `_execute_single_turn()`, `_build_agent_prompt()`, `_capture_completed_invocation()`, `_stream_codex_invocation()`, `_emit_stderr_events()` | Imports Codex helpers directly, launches Codex directly, and emits Codex-labeled stderr from shared runtime | Resolve one adapter and dispatch through the adapter contract while keeping shared prompt assembly and turn routing in Rally | Shared runtime must stop knowing Codex wire rules or hard-coding Codex event sources | adapter-neutral execution path with shared prompt-building and adapter-owned event emission | `tests/unit/test_runner.py`, `tests/unit/test_run_events.py` |
| Codex-only arg plumbing | `src/rally/services/runner.py`, `src/rally/services/home_materializer.py` | `_project_doc_max_bytes()`, `_write_codex_config()` | `project_doc_max_bytes` is validated and consumed from shared runtime in two Codex-specific places | Move Codex-only arg handling behind the Codex adapter and or registry-backed adapter validation | Shared runtime should not keep Codex-only flag knowledge after cutover | Codex adapter owns native config and launch translation for `project_doc_max_bytes` | `tests/unit/test_runner.py`, `tests/unit/test_launcher.py` |
| Shared final-response loader | `src/rally/services/final_response_loader.py` | new | Shared final-response loading still lives under the Codex tree | Move it into `src/rally/services/` and update imports | Final JSON validation is Rally-owned, not Codex-owned | generic `load_agent_final_response()` on `last_message.json` | renamed loader tests plus `tests/unit/test_runner.py` |
| Shared home materialization | `src/rally/services/home_materializer.py` | `materialize_run_home()`, `_home_ready_marker()`, `_write_codex_config()`, `_seed_codex_auth()` | Shared home setup writes Codex config and auth directly and refreshes them before the home-ready early return | Keep shared sync/setup work and call adapter bootstrap hooks in that same refresh-on-start-or-resume slot | Claude cannot reuse Codex bootstrap and shared policy should stay shared | `adapter.prepare_home(...)` runs before the one-time setup guard returns | new home-materialization coverage plus `tests/unit/test_runner.py` |
| Codex adapter | `src/rally/adapters/codex/adapter.py` plus current Codex modules | new entrypoint | Useful Codex behavior exists but is partly orchestrated from shared runtime | Wrap current Codex modules under one first-class adapter implementation | Preserve current behavior while removing shared-runtime leaks | Codex adapter owns launch, session, artifacts, and event mapping | `tests/unit/test_launcher.py`, `tests/unit/test_codex_event_stream.py`, `tests/unit/test_runner.py` |
| Claude adapter | `src/rally/adapters/claude_code/adapter.py`, `event_stream.py`, `session_store.py`, `launcher.py` | new | Missing | Implement CLI-backed Claude adapter with stdin prompt injection, stream-json event mapping, strict MCP config generation, tool clamping, ambient-auth v1 launch rules, and structured-output writeback | Support Claude cleanly through Rally's existing front door without inventing isolated auth machinery for v1 | Claude adapter owns CLI shape, result envelope parsing, session store, and event mapping | new Claude adapter tests plus `tests/unit/test_runner.py` |
| Launch proof | `logs/adapter_launch/` plus adapter launch writers | Codex-only launch proof shape | Shared proof location already exists | Keep one proof location and let adapters write truthful launch records | Preserve operator archaeology | shared path, adapter-specific payloads | `tests/unit/test_launcher.py`, new Claude launch tests |
| Session artifacts | `home/sessions/<agent>/` | currently Codex-shaped by ownership, generic by path | Shared path already exists | Keep the same stable operator path for Claude too, even if adapter-local metadata differs | Avoid a second user-facing artifact layout | shared session artifact root, adapter-owned contents | `tests/unit/test_runner.py`, new Claude session tests |
| Prompt delivery | `src/rally/services/runner.py` and Claude launcher | Rally prompt is already built once in shared runtime | Reuse the built prompt and pass it to Claude on stdin; do not add a second prompt-file source in v1 | Preserve one prompt source and avoid prompt drift | shared prompt string -> adapter stdin | `tests/unit/test_runner.py`, new Claude launch tests |
| Tool and MCP policy | Claude launcher plus generated `home/claude_code/mcp.json` | No Claude path exists | Derive Claude built-in tool clamp from Rally policy and generate strict MCP config under the run home | Keep Rally policy as SSOT even with ambient Claude auth | `--tools`, `--allowedTools`, `--strict-mcp-config`, generated MCP JSON | new Claude launcher and home tests |
| CLI display | `src/rally/cli.py`, `src/rally/terminal/display.py`, `src/rally/services/run_events.py` | Header already shows model, thinking, adapter and event rendering already accepts generic sources | Keep the small shared display surface, but make the values, labels, and adapter event sources truthful for Claude too | Avoid adapter-specific UI drift | shared display context plus adapter-owned `EventDraft.source` values | `tests/unit/test_run_events.py`, targeted CLI tests if needed |
| Runtime docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md` | Durable docs still teach Codex-first or Hermes-only-next truth | Update docs in the same pass as the code change and fold the Claude audit truth into the surviving runtime story | Keep durable repo truth aligned with shipped behavior | doc convergence only | doc review |

## 6.2 Migration notes

Canonical owner path / shared code path:

- Shared runtime stays in `src/rally/services/runner.py`,
  `src/rally/services/home_materializer.py`, `src/rally/services/run_events.py`,
  and the new `src/rally/services/final_response_loader.py`.
- Adapter-specific mechanics live under `src/rally/adapters/<name>/`.
- Shared prompt assembly stays in Rally and adapters consume the resulting
  prompt string instead of owning prompt authoring.

Deprecated APIs (if any):

- direct Codex imports from `src/rally/services/runner.py`
- direct Codex bootstrap helpers inside `src/rally/services/home_materializer.py`
- importing shared final-response loading from
  `src/rally/adapters/codex/result_contract.py`

Delete list (what must be removed; include superseded shims/parallel paths if any):

- `_invoke_codex()` and `_CodexInvocation` from shared `runner.py`
- `_project_doc_max_bytes()` from shared `runner.py`
- shared-runtime Codex-specific stderr emission paths after adapter-owned event
  emission exists
- `_write_codex_config()` and `_seed_codex_auth()` from shared
  `home_materializer.py`
- `src/rally/adapters/codex/result_contract.py` after shared loader extraction
- `tests/unit/test_result_contract.py` if coverage is renamed to the new shared
  owner path
- any shared-runtime branch that switches on adapter name instead of dispatching
  through the adapter registry
- any Claude v1 prompt-file layer added only because we assumed stdin would not
  work

Capability-replacing harnesses to delete or justify:

- reject any Claude wrapper path that scrapes assistant prose instead of using
  `--json-schema`
- reject any second prompt layer or sidecar instruction file that duplicates
  Rally's existing prompt assembly path
- reject any attempt to solve v1 by forcing isolated Claude auth bootstrap
  unless later planning proves ambient existing auth is not practically usable

Live docs/comments/instructions to update or delete:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
- any shared runner comments or lifecycle messages that still name Codex when
  the behavior is actually adapter-neutral

Behavior-preservation signals for refactors:

- `uv run pytest tests/unit -q`
- `tests/unit/test_flow_loader.py` for supported-adapter validation and arg
  rejection
- `tests/unit/test_runner.py` for run/resume control flow, stop conditions, and
  session reuse
- `tests/unit/test_run_store.py` for truthful adapter name persistence in
  `run.yaml`
- new `tests/unit/test_home_materializer.py` for shared-vs-adapter bootstrap
  behavior
- renamed shared-loader tests for final JSON validation
- `tests/unit/test_launcher.py` and `tests/unit/test_codex_event_stream.py`
  for Codex preservation after extraction
- `tests/unit/test_run_events.py` for shared event sink and display behavior
- new Claude adapter tests for stream-json parsing, structured-output writeback,
  MCP config generation, and session storage
- one small live Codex Rally run after the refactor
- one honest Claude Rally run using the supported v1 auth path

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Runtime dispatch | `src/rally/services/runner.py` | resolve one adapter once and execute through the adapter contract | stops future harnesses from reopening shared-runtime branches | include |
| Flow validation | `src/rally/services/flow_loader.py` | validate adapter names and args through the registry | keeps unsupported adapters out of the run path | include |
| Home bootstrap | `src/rally/services/home_materializer.py` | keep shared policy sync in Rally and push adapter-specific artifacts behind hooks | prevents Codex bootstrap from becoming framework law | include |
| Prompt delivery | shared prompt assembly plus adapter stdin consumption | build the prompt once in Rally and feed it to every adapter | prevents adapter-specific prompt drift | include |
| Final-response loading | shared Rally-owned loader | every adapter writes one `last_message.json` and Rally validates it once | preserves one turn-ending control path | include |
| Tool and MCP policy | Claude launcher plus generated MCP JSON | derive runtime capability clamps from Rally policy instead of ambient Claude defaults | prevents silent widening when Claude is the adapter | include |
| Operator wording | shared runner lifecycle messages and display text | adapter-neutral wording in shared text; adapter name only when truthful | keeps the CLI small and honest as adapters grow | include |
| Live runtime docs | master design, runtime slice, CLI/logging, Hermes generalization, Claude audit | teach one shared runtime boundary plus adapter-owned wire details | prevents the docs from freezing the old Codex-only split into repo law | include |
| Per-agent capability enforcement | run-home skill and MCP isolation rules | keep the current union-of-flow allowlist model until a later runtime plan changes it on purpose | this plan should not widen into per-agent isolation work | defer |
| Isolated Claude auth | `CLAUDE_CONFIG_DIR`-owned Claude state | add a tighter isolated auth mode only if later work proves it buys practical value beyond the ambient v1 path | avoid taking on auth complexity the user explicitly rejected for v1 | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns and gotchas in code comments at the canonical boundary when that comment will help later readers.

## Phase 1 - Shared adapter groundwork and front-door validation

- Goal:
  Establish one shared adapter boundary and move shared final-response loading
  into Rally without widening the supported runtime before the code is ready.
- Work:
  Add `src/rally/adapters/base.py` with the adapter protocol and shared adapter
  dataclasses.
  Add `src/rally/adapters/registry.py` with supported-adapter lookup, shared
  arg handling for `model` and `reasoning_effort`, and adapter-specific
  validation hooks.
  Move final JSON loading from
  `src/rally/adapters/codex/result_contract.py` to
  `src/rally/services/final_response_loader.py`.
  Rename the owning unit test file to match the new shared loader owner.
  Update `src/rally/services/flow_loader.py` so adapter names and adapter args
  are validated through the registry.
  Keep the registry truthful in this phase: `codex` is supported and
  `claude_code` is not registered yet.
- Verification (required proof):
  `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_run_store.py tests/unit/test_final_response_loader.py -q`
- Docs/comments (propagation; only if needed):
  Add one short code comment where shared runtime stops owning adapter-specific
  final-response parsing if that boundary is not obvious from the extracted
  module names alone.
- Exit criteria:
  The shared adapter boundary exists.
  Flow loading rejects unsupported adapter names and bad adapter args.
  Shared final-response loading no longer lives under the Codex tree.
  Rally still only accepts adapters it can truthfully execute.
- Rollback:
  Revert the registry and shared-loader extraction as one patch if flow loading
  or final-result parsing regresses.

## Phase 2 - Cut Codex over to the shared adapter contract

- Goal:
  Move the shipped Codex path behind the shared adapter seam while preserving
  current run-home layout, launch behavior, event rendering, and resume
  behavior.
- Work:
  Add `src/rally/adapters/codex/adapter.py` as the Codex adapter entrypoint
  over the current Codex modules.
  Refactor `src/rally/services/runner.py` to resolve one adapter and delegate
  session loading, turn-artifact preparation, launch, event emission,
  stdout/stderr handling, and session save.
  Refactor `src/rally/services/home_materializer.py` so shared sync and setup
  stay in Rally while `adapter.prepare_home(...)` runs before the one-time
  home-ready early return on every start and resume.
  Move Codex-only `project_doc_max_bytes` handling out of shared `runner.py`
  and shared `home_materializer.py`.
  Preserve Codex root-home file placement under `home/` because `CODEX_HOME`
  points at the run-home root today.
  Delete `_invoke_codex()`, `_CodexInvocation`, `_project_doc_max_bytes()`,
  shared Codex stderr emission, `_write_codex_config()`, and `_seed_codex_auth()`
  from shared modules once Codex owns those paths.
- Verification (required proof):
  `uv run pytest tests/unit/test_runner.py tests/unit/test_launcher.py tests/unit/test_codex_event_stream.py tests/unit/test_run_events.py tests/unit/test_home_materializer.py -q`
  One small live Codex Rally run after the cutover.
- Docs/comments (propagation; only if needed):
  Add one short code comment at the adapter dispatch boundary in
  `src/rally/services/runner.py`.
  Add one short code comment at the shared-vs-adapter bootstrap split in
  `src/rally/services/home_materializer.py`.
- Exit criteria:
  Shared runtime no longer imports Codex helper modules directly.
  Codex still runs through `rally run` and `rally resume`.
  Run archaeology still shows truthful adapter names, launch records, and
  session artifacts.
- Rollback:
  Revert the Codex cutover as one patch if live Codex behavior or targeted unit
  coverage regresses.

## Phase 3 - Add the Claude adapter and guarded `claude_code` enablement

- Goal:
  Add the supported Claude v1 path without widening Rally policy or pretending
  Claude is isolated when it is not.
- Work:
  Add `src/rally/adapters/claude_code/adapter.py`,
  `src/rally/adapters/claude_code/launcher.py`,
  `src/rally/adapters/claude_code/session_store.py`, and
  `src/rally/adapters/claude_code/event_stream.py`.
  Implement Claude launch with stdin prompt delivery, `-p`,
  `--output-format stream-json --verbose`, `--json-schema`,
  `--permission-mode dontAsk`, `--strict-mcp-config`, explicit `--tools`,
  explicit `--allowedTools`, optional `--resume`, and adapter-native model and
  effort mapping.
  Generate strict Claude MCP config under `home/claude_code/mcp.json`.
  Parse Claude event output into Rally `EventDraft`s with truthful
  `source="claude_code"` event ownership.
  Write Claude `structured_output` to the shared `last_message.json` path and
  save Claude session ids in the shared session-artifact tree.
  Register `claude_code` in the registry only after the adapter implementation
  and its coverage are in place.
  Keep the supported v1 auth story explicit: use the user's existing Claude
  login and config, do not set `CLAUDE_CONFIG_DIR`, and do not rely on
  `--bare`.
- Verification (required proof):
  `uv run pytest tests/unit/test_claude_code_adapter.py tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_run_events.py tests/unit/test_home_materializer.py -q`
  One honest Claude Rally run using the supported v1 auth path.
- Docs/comments (propagation; only if needed):
  Update any adapter-facing comments that still imply Codex is the only real
  runtime path.
- Exit criteria:
  Rally can truthfully load `runtime.adapter: claude_code`.
  Claude runs through the same Rally front door and shared final JSON rule.
  Live truth does not claim isolated Claude auth or a second prompt path.
- Rollback:
  Keep the registry Codex-only if Claude proof or ambient-auth usability fails.

## Phase 4 - Cleanup, docs convergence, and final proof

- Goal:
  Leave Rally with one honest multi-adapter runtime story and no stale
  Codex-only or Hermes-only live truth.
- Work:
  Delete the old Codex result-contract module and any superseded shared-runtime
  helper or renamed test file left behind by earlier phases.
  Update `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
  `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`,
  `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`,
  `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, and
  `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md` so they
  teach the shipped adapter boundary, the Codex preservation path, and the
  Claude v1 ambient-auth stance.
  Remove or rewrite shared runner comments and lifecycle text that still teach
  Codex-only behavior.
  Run the full unit suite and both live adapter proofs.
- Verification (required proof):
  `uv run pytest tests/unit -q`
  One small live Codex Rally run.
  One honest Claude Rally run using the supported v1 auth path.
  One cold-read sync check across the surviving runtime docs.
- Docs/comments (propagation; only if needed):
  The surviving runtime docs above are updated in the same pass.
- Exit criteria:
  Shipped code, this plan, and the surviving runtime docs tell the same story.
  No deprecated shared-runtime path or stale live doc remains.
- Rollback:
  Reopen the plan and keep the doc changes local if the final proof or doc sync
  fails.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- run the smallest phase-local unit subset at each phase gate
- finish with `uv run pytest tests/unit -q` after cleanup and doc sync
- the minimum proof matrix is:
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_run_store.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_runner.py`
  - `tests/unit/test_launcher.py`
  - `tests/unit/test_codex_event_stream.py`
  - `tests/unit/test_home_materializer.py`
  - `tests/unit/test_run_events.py`
  - `tests/unit/test_claude_code_adapter.py`

## 8.2 Integration tests (flows)

- prove one small live Codex Rally run after the Codex cutover
- prove one honest Claude Rally run through the same `rally` CLI front door
  after the Claude adapter lands

## 8.3 E2E / device tests (realistic)

- use the supported v1 Claude auth path in the live Claude proof
- confirm run archaeology still reads cleanly from `runs/<run-id>/`
- do one final cold-read doc sync check across the surviving runtime docs

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- keep Codex working first
- add Claude as a new validated adapter
- advertise ambient existing Claude login as the supported v1 local path
- do not advertise isolated Claude auth until Rally really ships it

## 9.2 Telemetry changes

- reuse Rally's current run-event and launch-record proof paths where they stay
  truthful
- add adapter-specific proof artifacts only where shared ones are not enough

## 9.3 Operational runbook

- supported Claude runs need a clear operator preflight: the user's normal
  local Claude login must already work before Rally starts the run
- supported Claude runs need an explicit v1 auth story and a clear note about
  which Claude behavior Rally clamps and which ambient behavior remains
- unsupported auth shapes should fail loud with a clear blocker

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, TL;DR, Sections 0 through 10, planning-pass state, and helper-block drift
  - agreement across runtime boundary, call-site audit, phase order, verification burden, rollout truth, and approved exceptions
- Findings summary:
  - the staged implementation order is consistent end to end
  - the ambient-auth Claude v1 stance is now consistent across TL;DR, North Star, target architecture, phase plan, rollout, and the decision log
  - the run-metadata owner path and Phase 3 doc update obligation needed to be pulled into grounding and related references
- Integrated repairs:
  - updated frontmatter related references to include `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `src/rally/domain/run.py`, and `src/rally/services/run_store.py`
  - updated planning-pass guidance to show that planning is complete and the next move is implementation, not another planning stage
  - updated research grounding to include the persisted run-metadata owner path and the Phase 3 runtime-doc drift surface
  - updated the operational runbook to describe the actual Claude v1 operator preflight instead of a vague auth-setup phrase
  - removed stale decision-log follow-up drift by making the remaining follow-ups match the current completed planning state
- Remaining inconsistencies:
  - none
- Unresolved decisions:
  - none
- Unauthorized scope cuts:
  - none
- Decision-complete:
  - yes
- Decision: proceed to implement? yes
<!-- arch_skill:block:consistency_pass:end -->

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
- The current draft treats ambient existing Claude auth as the pragmatic v1
  default unless later planning finds a concrete product reason to require
  tighter isolation.
- Later planning passes must still converge the docs so Rally ends with one
  truthful runtime design.

Follow-ups

- Confirm this North Star before deeper planning.

## 2026-04-13 - Choose the ambient-auth Claude CLI cut for v1

Context

- Local Claude proof showed that a fresh `CLAUDE_CONFIG_DIR` loses the user's
  existing subscription login.
- The user explicitly rejected per-run auth bootstrap and flow-home login
  complexity for v1.
- The current Rally runner already succeeds by sending the compiled prompt on
  stdin, which Claude's headless CLI also supports.

Options

- require isolated Claude auth and a run-home-owned Claude config before
  calling Claude support first-class
- ship v1 with the user's existing Claude login and config, clamp the Claude
  surfaces that runtime flags can clamp, and defer isolated auth

Decision

- Choose the ambient-auth Claude CLI path for v1. Keep Claude CLI-first, pass
  the Rally prompt on stdin, use strict JSON-schema output, strict generated
  MCP config, explicit tool clamps, and non-interactive permission mode, but do
  not set `CLAUDE_CONFIG_DIR` or require `--bare` in the supported v1 path.

Consequences

- Claude support can land beside Codex without taking on isolated auth work
  first.
- The docs must be honest that v1 is not a full clean-room Claude runtime.
- The adapter contract still has to keep shared Rally policy in charge of
  notes, final JSON, issue-ledger writes, event sinks, and capability limits.

Follow-ups

- Keep the Claude v1 auth stance locked while the remaining planning passes
  harden sequencing and implementation details.

## 2026-04-13 - Preserve native adapter home paths and refresh adapter bootstrap on resume

Context

- `materialize_run_home()` already refreshes Codex config and auth before the
  one-time home-ready early return.
- Codex currently uses `CODEX_HOME=<run-home>`, which makes root-level files
  such as `home/config.toml` part of the native Codex contract.
- Claude v1 needs generated MCP config on every start and resume, but it does
  not need Rally to move Claude auth under the run home.

Options

- force every adapter-specific file under a new adapter subdirectory and treat
  the current Codex root files as temporary
- preserve native adapter file placement where the runner requires it, while
  moving the shared bootstrap decision behind `adapter.prepare_home(...)`

Decision

- Preserve native adapter file placement where required by the adapter CLI.
  Codex may keep root-level home files because `CODEX_HOME` points there.
  Claude may use `home/claude_code/` for generated files Rally owns. In both
  cases, adapter bootstrap belongs in the refresh-on-start-or-resume slot
  before the home-ready early return.

Consequences

- The Codex cutover can stay behavior-preserving instead of inventing a second
  Codex home layout.
- Shared home materialization becomes truly adapter-neutral without losing the
  current refresh-on-resume behavior.
- The phase plan has to sequence shared bootstrap extraction before Claude
  delivery so the second adapter lands on the clean seam.

Follow-ups

- Preserve this bootstrap-order decision through implementation and docs sync.

## 2026-04-13 - Sequence shared groundwork, Codex cutover, then Claude enablement

Context

- Deep-dive pass 2 confirmed that the current runtime still depends on Codex
  helpers in shared modules.
- The doc now also locks two practical constraints: Codex root-home file
  placement must stay behavior-preserving, and Claude v1 uses ambient existing
  auth rather than isolated bootstrap.
- `flow.yaml` already carries `runtime.adapter`, but Rally must not claim
  `claude_code` support before the runtime can actually execute it.

Options

- add Claude directly on top of the current shared-runtime Codex wiring
- establish the shared adapter boundary, cut Codex over first, then register
  Claude only after its adapter and proofs are in place

Decision

- Choose the staged cutover path. First land the shared adapter boundary and
  Rally-owned final-response loader. Next move the shipped Codex path behind
  that boundary without changing Codex behavior. Then add and register
  `claude_code`. Finish by deleting superseded paths and syncing the surviving
  runtime docs.

Consequences

- The phase plan now has one clear implementation order instead of a generic
  "runtime boundary and Claude delivery" bucket.
- Rally does not have to carry a half-shared, half-Codex runtime while Claude
  support is landing.
- The final doc sync pass can update live docs against shipped code instead of
  against an intermediate runtime shape.

Follow-ups

- Keep the staged cutover order locked during implementation so Claude does not
  land on top of the old Codex-only shared runtime.
