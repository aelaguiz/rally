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
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/adapters/base.py
  - src/rally/adapters/registry.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/claude_code/adapter.py
  - src/rally/adapters/claude_code/launcher.py
  - src/rally/adapters/claude_code/event_stream.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - tests/unit/test_adapter_registry.py
  - tests/unit/test_claude_code_event_stream.py
  - tests/unit/test_claude_code_launcher.py
  - tests/unit/test_final_response_loader.py
  - tests/unit/test_runner.py
---

# TL;DR

## Outcome

Rally now supports `runtime.adapter: claude_code` beside `codex` through one
real adapter boundary. Claude support is now a shipped runtime path, not a doc
idea, not a shell alias, and not a local spike.

## Problem

The earlier draft was written while the runtime was still Codex-only in
practice. Shared runtime code launched Codex directly, wrote Codex bootstrap
files from shared services, and taught a future tense Claude plan instead of
the code that actually shipped.

## Approach

Keep one Rally-owned run model, one issue ledger, one prompt path, and one
final JSON path. Move adapter-specific launch, bootstrap, event parsing, and
session handling behind a shared adapter contract. Then land Claude on that
same boundary with the smallest honest v1 stance: use the user's existing
Claude login, clamp the runtime surfaces Claude exposes, and document the
remaining ambient dependency plainly.

## Plan

1. Land the shared adapter boundary, registry, and Rally-owned final-response
   loader.
2. Cut Codex over to that shared boundary without changing its run-home
   contract.
3. Add the Claude CLI adapter with stdin prompt delivery, generated MCP
   config, strict tool clamps, and the same shared final JSON path.
4. Sync the surviving runtime docs to the code that actually shipped.

## Implementation status

A fresh audit on 2026-04-13 cleared the full approved Section 7 frontier.
Phases 1 through 4 are now closed in code.

What is truly done:

- `uv run pytest tests/unit -q` passed with `155 passed`
- `uv run pytest tests/unit/test_claude_code_event_stream.py
  tests/unit/test_runner.py tests/unit/test_claude_code_launcher.py -q`
  passed with `46 passed`
- a fresh real Claude Rally run completed through the shipped
  `claude_code` adapter, the real Claude CLI, and the user's existing local
  Claude login:
  - temp repo root:
    `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-claude-live-xkjjvb5h`
  - run id: `CLP-1`
  - status: `done`
  - summary: `live claude contract proof`
- a fresh real Codex Rally run completed through the shared adapter boundary on
  a tiny one-agent temp flow after the cutover
- the shared adapter boundary, shared final loader, and Codex cutover are all
  in the tree
- the shipped Claude contract now matches the approved Phase 3 plan:
  - `--permission-mode dontAsk`
  - explicit `--tools`
  - explicit `--allowedTools`
  - adapter-owned `src/rally/adapters/claude_code/session_store.py`
- the Claude fallback loader now accepts fenced JSON blocks from live Claude
  output in both `result.result` and assistant text content

Real remaining frontier:

- no code gap remains across the approved ordered plan frontier
- broader docs cleanup, consolidation, or plan/worklog retirement belongs to
  `arch-docs`, not this implementation audit

Remaining honest v1 caveats:

- Claude still depends on the user's existing local Claude login and Claude's
  native session store outside the run home
- Claude init output still exposes bundled slash commands and bundled skills;
  Rally now clamps built-in tools and Claude.ai MCP servers, but it does not
  fully clean-room every ambient Claude surface yet

## Non-negotiables

- No second turn-ending control path. Rally still ends a turn with notes plus
  one final JSON result.
- `claude_code` must stay a real adapter, not a Codex alias.
- The shared prompt path stays in Rally. Do not add a second Claude-only prompt
  layer.
- The shared final JSON path stays `last_message.json`.
- Claude v1 must clamp the runtime surfaces Claude exposes. Where Claude does
  not expose a clamp, the doc must name the remaining ambient dependency
  honestly.
- Adapter choice stays flow-wide in v1.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-13
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- none

## Reopened phases (false-complete fixes)
- none

## Missing items (code gaps; evidence-anchored; no tables)
- none

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- none
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: done 2026-04-13
deep_dive_pass_2: done 2026-04-13
recommended_flow: planning complete 2026-04-13; fresh audit on 2026-04-13 cleared Phases 1 through 4
note: The planning arc is closed for this change. The approved Section 7 frontier is now closed in code. Use `arch-docs` only for any broader docs cleanup, consolidation, or plan/worklog retirement.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support `runtime.adapter: claude_code` beside `runtime.adapter:
codex` without breaking the Rally runtime model, without reopening Codex-only
branches in shared runtime code, and without making isolated Claude auth a v1
requirement.

This claim is true only if all of this is true:

- flow loading truthfully accepts both `codex` and `claude_code`
- shared runtime code no longer imports Codex launch or session helpers
  directly
- both adapters end on the same strict `last_message.json` final-result path
- Rally keeps one issue-ledger path and one command front door
- the Claude doc story names the ambient-auth caveat plainly instead of hiding
  it

## 0.2 In scope

- one shared adapter boundary and registry
- shared Rally-owned final-response loading
- Codex cutover to the shared boundary
- a real Claude CLI adapter under `src/rally/adapters/claude_code/`
- generated Claude MCP config under the run home
- shared prompt delivery on stdin
- shared run-home, issue-ledger, session-artifact, and run-state rules
- runtime doc convergence for the shipped multi-adapter story

## 0.3 Out of scope

- mixed-adapter flows
- Claude SDK-first runtime work
- run-home-owned Claude auth
- per-agent runtime capability isolation
- a third adapter

## 0.4 Definition of done (acceptance evidence)

The change is done only when all of this is true:

- Rally validates supported adapter names through one registry
- shared runtime depends on adapter interfaces instead of Codex helpers
- Codex still works through the same public front door
- Claude works through the same public front door
- the shared final JSON path still ends every turn
- the main runtime docs match the shipped code
- `uv run pytest tests/unit -q` passes
- one honest live Claude proof exists through Rally

## 0.5 Key invariants (fix immediately if violated)

- one flow has one adapter
- notes stay context-only
- final JSON stays the only turn-ending control path
- shared prompt assembly stays in Rally
- shared issue-first home prep stays in Rally
- shared adapter launch proof stays under `logs/adapter_launch/`
- shared session artifacts stay under `home/sessions/`
- docs must not teach a narrower runtime than the shipped code

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep one shared Rally runtime story.
2. Preserve Codex while landing Claude cleanly.
3. Keep the Claude v1 stance honest.
4. Keep the operator surface small.
5. Keep the durable docs aligned with code.

## 1.2 Constraints

- `flow.yaml` already carried `runtime.adapter` and `runtime.adapter_args`
- Rally already had one shared `WorkspaceContext`
- Rally already had one shared prompt-input path
- Rally already had one shared issue-first home-prep path
- a fresh `CLAUDE_CONFIG_DIR` still loses the user's existing Claude login on
  this machine
- Claude's real output shape can differ from the ideal `structured_output`
  shape in live Rally use

## 1.3 Architectural principles (rules we will enforce)

- shared runtime depends on an adapter contract
- adapters own only wire details and adapter-local bootstrap
- Rally owns prompt assembly, home policy, run routing, and final-result
  routing
- Rally stays filesystem-first
- v1 docs must state the real limitations, not the ideal ones

## 1.4 Known tradeoffs (explicit)

- Claude CLI-first is simpler than an SDK-first path, but it gives less native
  structure than a future SDK path might
- ambient-auth Claude support is practical for local use, but it is not a full
  clean-room story
- keeping Codex wrapper files thin instead of deleting every old import path
  reduced churn, but it leaves a little compatibility scaffolding in tree

# 2) Problem Statement (existing architecture + why change)

## 2.1 What ships now

- Rally now has one real adapter boundary instead of one Codex-shaped runtime
  with a generic adapter field on paper
- `runtime.adapter: codex` and `runtime.adapter: claude_code` now both work
- shared runtime code now owns prompt assembly, prompt-input loading,
  issue-ledger writes, state writes, and routing
- adapter code now owns adapter-specific bootstrap, launch, event parsing, and
  session handling

## 2.2 What changed from the earlier draft

- `src/rally/services/runner.py` no longer launches Codex directly
- `src/rally/services/home_materializer.py` no longer writes Codex bootstrap
  files from shared code
- `src/rally/services/final_response_loader.py` is now the shared final loader
- Claude now ships with generated `home/claude_code/mcp.json`, a
  `home/.claude/skills` symlink, strict built-in tool clamps, and the same
  shared `last_message.json` rule

## 2.3 Remaining limits that still matter

- adapter choice is still flow-wide
- Rally still copies the union of flow-allowed skills and MCPs into one shared
  run home
- Claude v1 still uses ambient Claude login and Claude's native session store
- Claude v1 still does not suppress every bundled Claude surface

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `docs/RALLY_CLAUDE_CODE_ADAPTER_AUDIT_2026-04-13.md`
  — folded external and local Claude CLI grounding for this change
- official Claude Code CLI docs and local CLI checks
  — confirmed `-p`, `--output-format stream-json`, `--json-schema`, `--resume`,
    `--mcp-config`, `--strict-mcp-config`, and tool clamp flags
- `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
  — earlier plan that pointed in the right direction on the shared adapter seam

## 3.2 Internal ground truth (code as spec)

- `src/rally/adapters/base.py`
  — shared adapter protocol, shared session helpers, shared launch-env
    projection, shared launch-record writing
- `src/rally/adapters/registry.py`
  — the one front door for supported adapter names
- `src/rally/services/final_response_loader.py`
  — the one shared final JSON loader
- `src/rally/services/flow_loader.py`
  — registry-backed adapter validation plus existing prompt-input and guarded
    repo rules
- `src/rally/services/home_materializer.py`
  — shared issue-first home prep and adapter bootstrap handoff
- `src/rally/services/runner.py`
  — shared turn loop, prompt assembly, prompt-input loading, routing, and
    result handling
- `src/rally/adapters/codex/adapter.py`
  — current Codex adapter owner
- `src/rally/adapters/claude_code/adapter.py`
  — current Claude adapter owner
- `src/rally/adapters/claude_code/event_stream.py`
  — real Claude stream-json parsing and final-output extraction fallback
- `tests/unit/test_adapter_registry.py`,
  `tests/unit/test_final_response_loader.py`,
  `tests/unit/test_claude_code_event_stream.py`,
  `tests/unit/test_claude_code_launcher.py`, and
  `tests/unit/test_runner.py`
  — current proof of the boundary and the Claude path

## 3.3 Resolved decisions and residual caveats

- no implementation-blocking design decision remains open in this doc
- Claude v1 keeps the ambient-auth stance from the audit
- the shipped Claude extractor now accepts a JSON object from:
  - `result.structured_output`
  - `result.result`
  - assistant text content
  - `StructuredOutput` tool input
- the shipped Claude extractor now also accepts fenced JSON blocks from live
  Claude output in:
  - `result.result`
  - assistant text content
- `src/rally/adapters/claude_code/session_store.py` now exists as a thin
  adapter-owned wrapper to the shared session-artifact helpers
- `src/rally/adapters/codex/session_store.py` still remains as a thin wrapper
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- shared runtime owners:
  - `src/rally/services/workspace.py`
  - `src/rally/services/runner.py`
  - `src/rally/services/home_materializer.py`
  - `src/rally/services/final_response_loader.py`
  - `src/rally/services/flow_loader.py`
  - `src/rally/services/issue_ledger.py`
  - `src/rally/services/run_events.py`
  - `src/rally/cli.py`
- shared adapter boundary:
  - `src/rally/adapters/base.py`
  - `src/rally/adapters/registry.py`
- adapter-specific code:
  - `src/rally/adapters/codex/`
  - `src/rally/adapters/claude_code/`
- stable run-home layout:
  - `home/agents/`
  - `home/skills/`
  - `home/mcps/`
  - `home/sessions/`
  - `home/artifacts/`
  - `home/repos/`
  - `home/issue.md`
- shared one-time setup guard:
  - `home/.rally_home_ready`
- adapter-owned files:
  - Codex keeps `home/config.toml`, `home/auth.json`, and
    `home/.credentials.json`
  - Claude keeps `home/claude_code/mcp.json`
  - Claude links `home/.claude/skills` to `home/skills`

## 4.2 Control paths (runtime)

1. `run_flow()` and `resume_run()` resolve one `WorkspaceContext`, lock the
   flow, build flow assets, and load the flow definition.
2. `load_flow_definition()` validates `runtime.adapter` and adapter args
   through the registry while preserving prompt-input and guarded-repo rules.
3. `prepare_run_home_shell()` creates the early run shell. Then
   `materialize_run_home()` enforces non-empty `home/issue.md`, syncs built-in
   framework assets, copies compiled agents plus allowlisted skills and MCPs,
   calls `adapter.prepare_home(...)`, runs the optional setup script once,
   snapshots the issue log, and writes `home/.rally_home_ready`.
4. `_load_prompt_inputs()` still runs `runtime.prompt_input_command` with the
   shared Rally env surface, including `RALLY_WORKSPACE_DIR`,
   `RALLY_CLI_BIN`, `RALLY_RUN_HOME`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
5. `_execute_single_turn()` resolves the adapter, builds the shared prompt,
   prepares turn artifacts, loads any saved adapter session, and invokes the
   adapter.
6. The adapter writes raw turn artifacts, emits adapter-native event drafts,
   and records the new session id when one exists.
7. Shared Rally code then loads `last_message.json`, routes the turn result,
   updates state, appends issue-ledger blocks, and decides whether the command
   stops or chains another turn.

## 4.3 Object model + key abstractions

- `FlowDefinition.adapter` still stores `AdapterConfig(name,
  prompt_input_command, args)`
- `RunRecord`, `RunState`, `TurnResult`, compiled-agent metadata, and
  `WorkspaceContext` remain Rally-owned and adapter-neutral
- shared adapter types now are:
  - `RallyAdapter`
  - `AdapterSessionRecord`
  - `TurnArtifactPaths`
  - `AdapterInvocation`
- `_build_agent_prompt()` and `_load_prompt_inputs()` remain the one shared
  prompt path
- `prepare_run_home_shell()` and `materialize_run_home()` remain the one shared
  home-prep path

## 4.4 Observability + failure behavior today

- `RunEventRecorder` stays the shared sink
- `logs/adapter_launch/turn-<n>-<agent>.json` stays the launch proof path
- `home/sessions/<agent>/turn-<n>/exec.jsonl`,
  `home/sessions/<agent>/turn-<n>/stderr.log`, and
  `home/sessions/<agent>/turn-<n>/last_message.json` stay the turn-artifact
  paths
- invalid or missing final JSON still fails loud through `RallyStateError`
- adapter-native stdout and stderr are now replayed with truthful
  `source="codex"` or `source="claude_code"` ownership
- missing or blank `home/issue.md`, setup-script failures, prompt-input
  failures, and dirty guarded repos still fail loud through shared Rally paths

## 4.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface was added.

The operator surface is still:

- `rally run <flow>`
- `rally resume <run-id>`
- `rally issue note`
- the shared startup header
- the shared live event stream
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

The shipped target now is:

- keep `src/rally/adapters/base.py` and `src/rally/adapters/registry.py` as
  the shared adapter seam
- keep one first-class adapter entrypoint per adapter
- keep the shared final loader in `src/rally/services/final_response_loader.py`
- keep the shared run-home shell unchanged
- keep `home/.rally_home_ready` as the one-time setup-script guard only
- preserve native adapter file placement where the adapter CLI requires it
- keep Claude auth out of the run home in v1

## 5.2 Control paths (future)

The steady-state control path is:

1. flow loading validates adapter truth through the registry
2. shared home prep stays in Rally
3. shared prompt assembly stays in Rally
4. adapters own launch, event parsing, and session handling
5. every adapter must end on the shared `last_message.json` path

Codex steady-state launch facts:

- `codex exec`
- `CODEX_HOME=<run-home>`
- explicit `cwd`
- strict output schema
- dangerous bypass

Claude steady-state launch facts:

- `claude -p`
- `--output-format stream-json`
- `--verbose`
- `--permission-mode dontAsk`
- `--mcp-config <run-home>/claude_code/mcp.json`
- `--strict-mcp-config`
- `--tools <explicit-list>`
- `--allowedTools <explicit-list>`
- `--json-schema <schema>`
- optional `--model`
- optional `--effort`
- optional `--resume <session-id>`
- launch env clamp: `ENABLE_CLAUDEAI_MCP_SERVERS=false`

## 5.3 Object model + abstractions (future)

- keep `RallyAdapter` small
- keep shared adapter dataclasses in `src/rally/adapters/base.py`
- keep `registry.py` as the only owner of supported adapter names
- keep shared adapter args where they already fit:
  - `model`
  - `reasoning_effort`
- keep adapter-specific args below the adapter boundary:
  - Codex keeps `project_doc_max_bytes`
  - Claude adds no extra adapter-specific args yet

## 5.4 Invariants and boundaries

Rally owns:

- flow loading
- run creation and resumption
- workspace resolution
- issue-first home prep
- prompt assembly and prompt-input loading
- state writes
- issue-ledger writes
- command turn caps
- shared final-result loading
- shared event sink

Adapters own:

- adapter arg validation
- adapter-local home bootstrap
- session load and save
- turn artifact preparation
- actual launch or runtime invocation
- translation from adapter-native progress into Rally events

Claude v1 must stay honest:

- use the user's existing Claude login
- do not set `CLAUDE_CONFIG_DIR`
- clamp built-in tools with explicit `--tools` and `--allowedTools`
- clamp MCP servers with generated `mcp.json`,
  `--strict-mcp-config`, and `ENABLE_CLAUDEAI_MCP_SERVERS=false`
- do not claim that Rally suppresses every bundled Claude surface

## 5.5 UI surfaces (ASCII mockups, if UI work)

The UI stays the same. The important steady-state rule is simple:
shared wording stays adapter-neutral, and adapter-specific wording appears only
where it is actually true.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | Files | Shipped result | Proof |
| --- | --- | --- | --- |
| Adapter boundary | `src/rally/adapters/base.py`, `src/rally/adapters/registry.py` | one shared adapter contract, one registry, one shared launch-env path | `tests/unit/test_adapter_registry.py`, `tests/unit/test_runner.py` |
| Flow validation | `src/rally/services/flow_loader.py` | `runtime.adapter` and adapter args are now registry-validated | `tests/unit/test_flow_loader.py`, full unit pass |
| Shared final-result path | `src/rally/services/final_response_loader.py` | Rally-owned final JSON loading now lives only in `services/` | `tests/unit/test_final_response_loader.py`, `tests/unit/test_runner.py` |
| Shared home bootstrap | `src/rally/services/home_materializer.py` | shared issue-first home prep stayed in Rally; adapter bootstrap moved behind `prepare_home(...)` | `tests/unit/test_runner.py`, full unit pass |
| Shared runner dispatch | `src/rally/services/runner.py` | shared runner now resolves one adapter and stays wire-neutral | `tests/unit/test_runner.py` |
| Codex cutover | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/codex/launcher.py` | Codex now runs behind the shared boundary without changing its root-home contract | `tests/unit/test_launcher.py`, `tests/unit/test_runner.py`, existing live `poem_loop` Codex proof |
| Claude support | `src/rally/adapters/claude_code/adapter.py`, `launcher.py`, `event_stream.py`, `session_store.py` | Claude now ships as a real adapter with generated MCP config, explicit tool clamp, session reuse, and shared `last_message.json` output | `tests/unit/test_claude_code_event_stream.py`, `tests/unit/test_claude_code_launcher.py`, `tests/unit/test_runner.py`, fresh live Claude proof |
| Launch and session archaeology | `logs/adapter_launch/`, `home/sessions/<agent>/` | both adapters now keep the same stable proof paths in the run home | launcher tests, runner tests |
| Docs convergence | master, Phase 3, Phase 4, CLI/logging, Hermes generalization, this plan, this worklog | the runtime doc set now reflects the shipped multi-adapter boundary; the old Hermes future-runtime plan is retired | current pass plus next audit |

## 6.2 Migration notes

Shared runtime now lives in:

- `src/rally/services/runner.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/final_response_loader.py`
- `src/rally/services/run_events.py`
- `src/rally/services/workspace.py`

Adapter-specific mechanics now live under `src/rally/adapters/<name>/`.

Deleted or moved from shared runtime:

- direct Codex launch wiring from `src/rally/services/runner.py`
- direct Codex bootstrap helpers from `src/rally/services/home_materializer.py`
- shared final-result ownership from the Codex tree

Intentionally kept in place:

- `src/rally/adapters/codex/session_store.py` as a thin wrapper to the shared
  session helpers

Important current Claude proof notes:

- `src/rally/adapters/claude_code/session_store.py` now exists as a thin
  wrapper to the shared session helpers
- Claude v1 now uses `--permission-mode dontAsk`
- Claude v1 now uses explicit `--tools` and `--allowedTools`
- Claude final output now accepts JSON from `result.result`, assistant text
  content, and fenced JSON blocks from those same surfaces, not only
  `structured_output`

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | Shipped pattern | Status | Note |
| --- | --- | --- | --- |
| Runtime dispatch | one adapter resolution path in `runner.py` | done | shared runtime no longer hard-codes Codex |
| Flow validation | registry-backed adapter validation | done | `codex` and `claude_code` are the only supported names |
| Workspace ownership | one shared `WorkspaceContext` and one shared Rally env projection | done | adapters consume it instead of rediscovering roots |
| Home bootstrap | shared policy in Rally, adapter bootstrap below the boundary | done | `prepare_home(...)` runs on every start and resume |
| Prompt delivery | one shared prompt string fed to adapters on stdin | done | no second prompt layer was added |
| Final-response loading | one shared `last_message.json` loader | done | both adapters now end on the same path |
| Tool and MCP policy | adapter-specific runtime translation from Rally policy | done | Claude now uses generated MCP JSON plus explicit tool clamp |
| Per-agent capability enforcement | one shared run-home union of allowed skills and MCPs | deferred | still outside this change |
| Isolated Claude auth | run-home-owned Claude auth | deferred | ambient existing Claude login stays the supported v1 path |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: keep the plan honest after implementation. Once code lands, Section 7
> must describe the work that actually shipped and the proof that actually ran.

## Phase 1 - Shared adapter groundwork and front-door validation

Status: DONE

- Work completed:
  - added `src/rally/adapters/base.py`
  - added `src/rally/adapters/registry.py`
  - added `src/rally/services/final_response_loader.py`
  - updated `src/rally/services/flow_loader.py` to validate adapters through
    the registry
- Verification:
  - `tests/unit/test_adapter_registry.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_flow_loader.py`
  - `uv run pytest tests/unit/test_final_response_loader.py tests/unit/test_runner.py -q`
    passed (`44 passed`)
- Current pass completed:
  - moved the remaining final-response coverage under
    `tests/unit/test_final_response_loader.py`
  - deleted `tests/unit/test_result_contract.py`

## Phase 2 - Cut Codex over to the shared adapter contract

Status: DONE

- Work completed:
  - added `src/rally/adapters/codex/adapter.py`
  - refactored `src/rally/services/runner.py` to dispatch through the adapter
    contract
  - refactored `src/rally/services/home_materializer.py` to delegate adapter
    bootstrap through `prepare_home(...)`
  - moved Codex-only config handling below the Codex adapter boundary
- Verification:
  - `tests/unit/test_runner.py`
  - `tests/unit/test_launcher.py`
  - `tests/unit/test_codex_event_stream.py`
  - `uv run pytest tests/unit/test_final_response_loader.py tests/unit/test_runner.py -q`
    passed (`44 passed`)
  - one fresh live Codex Rally proof succeeded after the cutover on a tiny
    temp flow:
    - temp repo root:
      `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-codex-live-42kjh998`
    - run id: `CDL-1`
    - status: `done`
    - summary: `live codex proof`
- Current pass completed:
  - deleted `src/rally/adapters/codex/result_contract.py`
  - reran and recorded one fresh live Codex Rally proof after the cutover

## Phase 3 - Add the Claude adapter and guarded `claude_code` enablement

Status: DONE

Earlier audit reopening that this pass closed:

- the approved Claude launch contract had not fully landed:
  - code used `--permission-mode bypassPermissions`
  - code omitted explicit `--allowedTools`
- the approved Claude-owned session path under
  `src/rally/adapters/claude_code/` had been replaced in place with shared
  base helpers

- Work completed:
  - added `src/rally/adapters/claude_code/adapter.py`
  - added `src/rally/adapters/claude_code/launcher.py`
  - added `src/rally/adapters/claude_code/event_stream.py`
  - registered `claude_code` in `src/rally/adapters/registry.py`
  - generated `home/claude_code/mcp.json`
  - linked `home/.claude/skills` to `home/skills`
  - shipped fallback final-output extraction for `result.result` and assistant
    text JSON
- Current pass completed:
  - added `src/rally/adapters/claude_code/session_store.py` as the approved
    adapter-owned session wrapper
  - changed Claude launch to `--permission-mode dontAsk`
  - kept explicit `--tools` and added explicit `--allowedTools`
  - taught the Claude fallback loader to accept fenced JSON blocks from live
    Claude output in `result.result` and assistant text content
- Verification:
  - `tests/unit/test_claude_code_event_stream.py`
  - `tests/unit/test_claude_code_launcher.py`
  - `tests/unit/test_runner.py`
  - `uv run pytest tests/unit/test_claude_code_event_stream.py
    tests/unit/test_runner.py tests/unit/test_claude_code_launcher.py -q`
    passed (`46 passed`)
  - one fresh honest live Claude Rally run using the supported v1 auth path:
    - temp repo root:
      `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-claude-live-xkjjvb5h`
    - run id: `CLP-1`
    - status: `done`
    - summary: `live claude contract proof`

## Phase 4 - Cleanup, docs convergence, and final proof

Status: DONE

Earlier audit reopening that this pass closed:

- final doc sync and final proof could not close while the approved Phase 3
  Claude contract still differed from shipped code
- this plan and the linked runtime docs had been rewritten to treat that
  narrower Phase 3 story as shipped truth, so the final proof had to be rerun
  against the approved contract

- Work completed:
  - updated this plan to match the shipped code
  - updated the linked runtime docs to the same multi-adapter story
  - recorded the real Claude output-shape caveat and the real ambient-auth
    caveat
- Current pass completed:
  - updated this plan, the worklog, the master design doc, the Phase 4 runtime
    doc, the CLI/logging doc, and the Claude audit doc to the corrected Claude
    contract
  - reran the final proof after the Claude contract aligned in code
- Verification:
  - `uv run pytest tests/unit -q` passed (`155 passed`)
  - fresh live Claude proof on the corrected Claude contract
  - fresh live Codex proof on the shipped adapter boundary
  - cold-read sync across the surviving runtime docs in this pass
- Earlier current pass completed:
  - deleted the old Codex final-response cleanup surfaces
  - retired `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
    as a stale future-runtime plan
  - recorded the fresh live Codex proof required by the final proof step
  - recorded the fresh live Claude contract proof required by the final proof
    step
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

Fresh full-suite proof for this pass:

- `uv run pytest tests/unit -q`
- result: `155 passed`

Key adapter-boundary coverage now lives in:

- `tests/unit/test_adapter_registry.py`
- `tests/unit/test_final_response_loader.py`
- `tests/unit/test_runner.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_codex_event_stream.py`
- `tests/unit/test_claude_code_event_stream.py`
- `tests/unit/test_claude_code_launcher.py`

## 8.2 Integration tests (flows)

- no separate integration harness was added in this pass
- the runner tests still cover both adapters through temporary Rally repos
- one fresh live Codex proof now exists on a tiny temp flow created only to
  prove the post-cutover boundary
- the earlier live `poem_loop` Codex proof remains the checked-in end-to-end
  Codex smoke

## 8.3 E2E / device tests (realistic)

Fresh realistic proof in this pass was a real Claude Rally run with:

- the shipped `claude_code` adapter
- the real `claude` CLI
- the user's existing local Claude login
- Rally-created run-home artifacts and shared final-result routing

Important live finding:

- the first rerun exposed a real parser gap: Claude wrapped the final JSON in a
  fenced code block
- the current adapter now accepts fenced JSON blocks from `result.result` and
  assistant text content, and the fresh rerun succeeded after that fix

Fresh realistic Codex proof in this pass was a real Codex Rally run with:

- the shipped shared adapter boundary
- the real `codex` CLI
- a tiny one-agent temp flow created only to prove the cutover itself
- run result `done` with summary `live codex proof`

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- `codex` and `claude_code` are both now supported adapter names
- Codex remains the existing stable path
- Claude is now the supported local v1 path for operators who already have a
  working local Claude login
- do not advertise isolated Claude auth until Rally really ships it

## 9.2 Telemetry changes

- Rally keeps the same run-event, rendered-log, launch-record, and
  session-artifact proof paths
- adapter-specific detail now shows up through truthful event `source` values
  and adapter-specific launch records

## 9.3 Operational runbook

Claude preflight:

- `claude auth status` should already show a working local login before Rally
  starts a Claude run

Expected Claude run-home artifacts:

- `home/claude_code/mcp.json`
- `home/.claude/skills` -> `home/skills`
- `home/sessions/<agent>/session.yaml`

Honest Claude v1 caveats:

- ambient Claude login is still required
- Claude's bundled slash commands and bundled skills may still appear in init
  output
- Rally clamps built-in tools, generated MCP config, and Claude.ai MCP
  servers, but not every ambient Claude surface

If `home/sessions/<agent>/turn-<n>/last_message.json` is missing after a
Claude turn, inspect `exec.jsonl` first. The shipped adapter already accepts
`structured_output`, `result.result`, assistant text JSON, and
`StructuredOutput` tool payloads, so a missing final file now means Claude did
not produce one valid final JSON object.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, TL;DR, Sections 0 through 10, planning-pass state, and helper-block drift
  - agreement across runtime boundary, call-site audit, phase order, verification burden, rollout truth, and approved exceptions
- Findings summary:
  - the shared adapter boundary is real in code
  - the phase plan now records the corrected Claude contract and the fresh
    proof from this pass
  - the ambient-auth Claude v1 stance is consistent across TL;DR, current architecture, target architecture, rollout, and the decision log
  - the real Claude output-shape drift is now recorded instead of hidden,
    including fenced JSON from the live Claude proof rerun
- Integrated repairs:
  - rewrote the internal grounding section to the shipped file owners
  - rewrote the current and target architecture sections to the shipped multi-adapter runtime
  - rewrote the call-site audit and phase plan to the corrected Claude file
    set and corrected proof
  - added updated implementation status and realistic proof notes
- Remaining inconsistencies:
  - none
- Unresolved decisions:
  - none
- Unauthorized scope cuts:
  - none in this follow-through pass
- Decision-complete:
  - yes
- Decision: implementation complete? yes
<!-- arch_skill:block:consistency_pass:end -->

# 10) Decision Log (append-only)

## 2026-04-13 - Claude support needs its own canonical plan

Context

- A shared adapter-boundary plan already existed.
- Claude Code had become a real second runner target with a different auth and
  runtime story.

Decision

- Keep one Claude-specific canonical plan so the Claude runtime truth could be
  settled cleanly, then fold the surviving truth back into the main runtime
  docs once code landed.

Consequences

- Claude support got one clear North Star instead of hiding inside a generic
  second-adapter draft.

## 2026-04-13 - Choose the ambient-auth Claude CLI cut for v1

Context

- A fresh `CLAUDE_CONFIG_DIR` lost the user's existing Claude login on this
  machine.
- The user did not want per-run Claude auth bootstrap complexity for v1.

Decision

- Use the Claude CLI path with the user's existing local Claude login.
- Do not set `CLAUDE_CONFIG_DIR`.
- Do not require `--bare`.

Consequences

- Claude could ship now.
- The docs had to state the ambient-auth caveat plainly.

## 2026-04-13 - Preserve native adapter home paths and refresh adapter bootstrap on resume

Context

- Codex already depended on `CODEX_HOME=<run-home>`.
- Claude needed generated run-home files but not run-home-owned auth.

Decision

- Keep native adapter file placement where the adapter CLI requires it.
- Run `adapter.prepare_home(...)` on every start and resume before the
  one-time setup-script guard returns.

Consequences

- Codex stayed behavior-preserving.
- Claude got generated runtime-owned files without forcing a fake Codex-like
  root layout.

## 2026-04-13 - Sequence shared groundwork, Codex cutover, then Claude enablement

Context

- Shared runtime still leaked Codex helper imports.
- Claude needed the clean boundary first.

Decision

- Land the shared adapter seam first.
- Move Codex behind it second.
- Register Claude only after the Claude adapter and proof existed.

Consequences

- Rally did not have to carry a half-shared, half-Codex runtime shape while
  Claude support was landing.
