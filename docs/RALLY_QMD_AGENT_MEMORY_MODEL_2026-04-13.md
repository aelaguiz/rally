---
title: "Rally - QMD Agent Memory Model - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: new_system
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - skills/rally-kernel/SKILL.md
  - src/rally/cli.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/issue_ledger.py
  - for_reference_only/qmd/README.md
  - for_reference_only/qmd/src/store.ts
  - for_reference_only/qmd/src/collections.ts
  - for_reference_only/qmd/src/llm.ts
---

# TL;DR

Outcome
- Add a built-in Rally memory model that gives each flow-agent pair a repo-local memory bank.
- Tell every Rally-managed agent to look for relevant memory after it reads the issue and before it starts real work.
- Tell every Rally-managed agent to save a memory at turn end when it learned something hard that should stop the same mistake next time, especially after rework or repeat fixes.
- Make memory use and memory save first-class visible runtime events, not hidden side effects.

Problem
- Rally has run-local notes and one final JSON result, but it does not yet have a cross-run memory layer.
- The master design says memory should come later, but the repo already has the base-agent and skill pattern that memory should plug into.
- QMD is a good fit for search, but its default home-dir cache and config paths break Rally's repo-local rules if Rally uses it raw.
- The repo is still early and not all of the runtime is built yet, so this doc is designing the future-state model ahead of implementation.

Approach
- Keep memory as Rally-owned runtime and skill behavior, not as hidden prose injected outside the `.prompt` graph.
- Store durable memory as markdown files under `runs/` so the files stay the source of truth and QMD stays a search index over those files.
- Add one always-present Rally memory skill plus Rally CLI memory commands that wrap QMD with explicit repo-local paths for config, index, and model cache.
- Scope every lookup and save to the current flow and current agent through a Rally-owned identity surface such as `RALLY_AGENT_SLUG`.
- Record memory use and memory save in Rally's visible runtime surfaces and append them into the issue through Rally-owned front-door paths.

Plan
- Lock the memory boundary, file layout, and save/update rules first.
- Add the Rally-owned QMD wrapper, memory CLI, and visible event surfaces next.
- Add agent scope injection, the ambient memory skill, and shared base-agent memory instructions after that.
- Prove the model on one narrow Rally flow, then sync the live docs.

Non-negotiables
- Markdown memory files are the source of truth. QMD's SQLite data is a rebuildable cache.
- No hidden global QMD state under `~/.cache`, `~/.config`, or similar paths.
- No hidden memory prose injection outside the declared `.prompt` graph.
- Memory never carries routing, `done`, `blocker`, or `sleep` truth.
- V1 memory scope is one flow plus one agent, not a shared global brain.
- Agents should save only reusable lessons, not raw session logs.
- Memory use and memory save must be visible in Rally's CLI and issue history through front-door mechanisms.
- This document designs the target state first. The repo does not need to already contain all of these runtime pieces today.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
deep_dive_pass_2: done 2026-04-13
external_research_grounding: not started
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can add a built-in QMD-backed memory layer without breaking its core rules if it does all of the following at the same time:

- keeps durable memory as repo-local markdown files
- uses QMD only as the search engine over those files
- gives every Rally-managed agent a shared memory skill and clear base-agent instructions
- makes agents look up memory by explicit action after reading the issue
- makes agents save reusable lessons by explicit action before the turn ends when needed
- keeps memory scoped to the current flow and current agent
- makes memory use and memory save visible in Rally's runtime and issue ledger

This claim is false if any of the following stay true after the work lands:

- Rally depends on `~/.cache/qmd`, `~/.config/qmd`, or other hidden global state
- memory reaches agents through hidden injected prose instead of prompt-plus-skill behavior
- memory lookup or save cannot be scoped to the current flow and current agent
- memory can change routing, `done`, `blocker`, or `sleep` control
- reusable lessons still live only in run-local notes and disappear from later runs
- memory use or creation happens as a hidden side effect with no Rally-owned visible record

This section describes the target state Rally should reach after later implementation work.
It does not claim the current repo already behaves this way.

## 0.2 In scope

- one built-in Rally memory model for cross-run learning
- future-state design for later implementation of that memory model
- repo-local memory files under `runs/`
- markdown memory files as the durable source of truth
- QMD as a project dependency and the search layer over those files
- Rally-owned wrapper behavior that forces QMD config, index, and model-cache paths to stay repo-local
- one always-present `rally-memory` skill or equivalent Rally-managed memory skill
- base-agent instructions that tell agents to:
  - read the issue first
  - look up relevant memory before they execute
  - save reusable lessons at turn end when the lesson is worth keeping
  - always save a memory when they were brought back to fix their own earlier miss and the lesson is reusable
- explicit runtime identity for memory scope, likely including `RALLY_FLOW_CODE` plus a new agent identity such as `RALLY_AGENT_SLUG`
- Rally CLI memory commands for search, use, save, and refresh
- clear separation between run-local issue notes and cross-run memory
- first-class CLI-visible memory events for memory use and memory save
- automatic issue append behavior, through Rally-owned front-door paths, when a memory is used or saved
- docs alignment with the master design and the base-agent note pivot

## 0.3 Out of scope

- implementing the full memory system in this `new` planning pass
- cross-flow shared memory in v1
- cross-agent shared memory in v1
- hidden launch-time memory snippets injected as extra prose
- DB-only memory truth
- a non-QMD retrieval stack
- full automatic memory writing by Rally without agent judgment
- broad product features such as memory dashboards, boards, or review UIs
- widening the memory model into a generic knowledge base for arbitrary repo content

## 0.4 Definition of done (acceptance evidence)

- Rally has one documented built-in memory model that fits its repo-local and filesystem-first rules.
- Every Rally-managed agent gets one Rally-owned memory skill and base-agent instructions for turn-start lookup and turn-end save decisions.
- Memory source files live under the repo root and can be read without QMD.
- Rally-owned memory commands force QMD to use repo-local config, index, and model-cache paths.
- Memory lookup and memory save are scoped by flow plus agent.
- The smallest useful proof shows one Rally flow can read a relevant prior memory and save a new reusable memory without changing note or routing semantics.
- Memory use and memory save show up as first-class visible items in Rally's CLI/runtime readback.
- When a memory is used or saved, Rally appends a normalized record into the issue through the same front-door ledger path Rally uses for other trusted runtime records.
- The master design and child docs say the same thing about notes, memory, and turn-end control.

This is acceptance evidence for the later implementation.
It is not a claim about the current repo state.

## 0.5 Key invariants (fix immediately if violated)

- Markdown memory files are the source of truth.
- QMD state used by Rally stays repo-local.
- Memory scope is one flow plus one agent in v1.
- Memory lookup is explicit agent behavior taught by the prompt and skill, not hidden runtime prose.
- Memory may influence execution, but it never becomes route truth or terminal-control truth.
- Run-local notes stay for run-local context. Memory stays for reusable cross-run lessons.
- Agents save only high-value lessons that should change future behavior.
- Rework after an earlier miss should produce a memory unless the matching memory is already present and updated.
- If QMD is missing or misconfigured, Rally memory operations fail loud instead of silently switching stores.
- If a memory is used or saved, Rally records that event through the visible CLI/runtime path and appends it into the issue.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Preserve Rally's repo-local and no-side-door rules.
2. Make memory use and memory save easy to inspect.
3. Capture reusable agent learning across runs.
4. Keep memory quality high by tight scope and selective saves.
5. Keep the integration simple by wrapping QMD behind Rally-owned surfaces.
6. Keep every saved memory easy to audit on disk.

## 1.2 Constraints

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` already says built-in memory should be the next move after Phase 5.
- `stdlib/rally/prompts/rally/base_agent.prompt` already gives Rally a shared place to inject always-on behavior.
- `skills/rally-kernel/SKILL.md` already shows the pattern for a Rally-owned ambient skill that teaches shared turn behavior.
- `src/rally/cli.py`, `src/rally/services/home_materializer.py`, `src/rally/services/run_store.py`, `src/rally/services/issue_ledger.py`, and `src/rally/services/runner.py` are still early, so the design should stay clean instead of bending around missing code.
- QMD supports explicit `dbPath` and `configPath`, but its defaults still point at home-dir cache and config locations.
- Rally is a Python project and QMD is a Node tool, so the boundary has to stay small and clear.
- The memory path must fit Rally's future CLI and issue-ledger design instead of inventing a side channel.
- This plan is intentionally ahead of implementation. Missing runtime pieces in the current repo are design inputs, not reasons to collapse the target design down to today's partial state.

## 1.3 Architectural principles (rules we will enforce)

- The `.prompt` graph tells agents when to use memory.
- Rally runtime and CLI own how memory is stored and searched.
- Rally runtime and CLI own how memory events are shown and appended into the issue.
- Markdown stays the source of truth; QMD indexes that truth.
- Rally wraps QMD; agents should not depend on raw QMD global behavior.
- Memory scope stays per flow and per agent in v1.
- Saved memories must be short, concrete, and reusable.

## 1.4 Known tradeoffs (explicit)

- A Rally CLI wrapper around QMD is simpler than a direct QMD library embed, but it adds a subprocess boundary and path-env setup work.
- One shared repo-local QMD store with one collection per flow-agent scope keeps one index and one model cache, but Rally has to keep collection config in sync.
- Tight per-flow and per-agent scope protects relevance, but it also limits recall breadth in v1.
- Agent-driven save behavior keeps judgment in the loop, but it may miss lessons if the prompt and skill rules are weak.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- The master design says memory should become built-in Rally behavior later.
- The Rally base agent already injects shared run identity and Rally-owned skill guidance.
- The Rally kernel skill already covers run-local notes and valid final JSON.
- The runtime seams that would own persistent memory storage and materialization still exist only as early boundaries.
- The local QMD reference repo shows that QMD can index markdown and search it well, but it is not yet wired into Rally.

## 2.2 What’s broken / missing (concrete)

- There is no cross-run memory surface today.
- There is no Rally-owned search or save path for reusable agent lessons.
- There is no agent identity env surface for per-agent memory scope.
- There is no repo-local QMD config, index, or model-cache contract.
- There is no memory file schema or save rule that keeps quality high.
- There is no clear line yet between run-local notes and cross-run memory.
- There is no visible runtime or issue-ledger record for memory use or creation.

This is exactly why the plan is future-state design work rather than a description of current behavior.

## 2.3 Constraints implied by the problem

- Memory must not become a hidden instruction overlay.
- The design must keep run-local notes and cross-run memory separate.
- The design should extend the current base-agent and ambient-skill pattern instead of inventing a second system.
- Memory introspection has to use Rally's front-door CLI and issue paths, not direct QMD or file side effects.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `for_reference_only/qmd/README.md` — adopt QMD as the search engine shape for markdown-backed memory because it already supports keyword search, vector search, reranking, JSON output, and agent-facing retrieval workflows; reject using QMD raw with its default global state because Rally requires repo-local state and visible front-door behavior.
- `for_reference_only/qmd/src/index.ts` — adopt QMD's explicit `createStore({ dbPath, configPath | config })` surface as proof that Rally can force repo-local paths instead of depending on implicit home-dir defaults.
- `for_reference_only/qmd/src/store.ts`, `for_reference_only/qmd/src/collections.ts`, and `for_reference_only/qmd/src/llm.ts` — reject QMD's default path behavior for Rally because the defaults still fall back to `INDEX_PATH` or `~/.cache/qmd/*.sqlite`, `QMD_CONFIG_DIR` or `~/.config/qmd/*.yml`, and model cache under `XDG_CACHE_HOME` or `~/.cache/qmd/models`.
- No web research is needed for this pass. The local QMD checkout is enough to ground the storage and path-ownership questions.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — defines the core Rally rules this memory design must keep: repo-local state, filesystem-first truth, no side-door instruction sources, typed turn control, append-only issue history, and the explicit future direction of built-in turn-start memory lookup plus turn-end learning.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — is the current shared prompt hook for always-on Rally behavior and already owns `RALLY_BASE_DIR`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, plus the pattern for a Rally-managed ambient skill.
  - `skills/rally-kernel/SKILL.md` — is the live pattern for a Rally-owned ambient skill: flows do not allowlist it by hand, it teaches a shared CLI front door, and it keeps notes separate from control truth.
  - `src/rally/cli.py` — is the existing front-door CLI boundary. Future `rally memory ...` commands should land here instead of teaching agents to call raw QMD or mutate files directly.
  - `src/rally/services/issue_ledger.py` — is the owning boundary for normalized issue append behavior and should also own the trusted append path for `memory used` and `memory saved` readback.
  - `src/rally/services/run_store.py`, `src/rally/services/home_materializer.py`, and `src/rally/services/runner.py` — are the runtime seams that should own repo-local memory paths, prepared-home materialization, and turn orchestration once the feature is implemented.
  - `flows/single_repo_repair/flow.yaml` — shows the current runtime contract for a Rally flow and already sets `project_doc_max_bytes: 0`, which means memory cannot sneak in as ambient project-doc discovery; it has to come through explicit Rally-owned prompt, skill, and CLI paths.

- Canonical path / owner to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — should remain the one shared prompt surface that tells agents when memory recall and memory save belong in the turn.
  - `skills/` with the `rally-kernel` pattern — should remain the user-facing skill layer for how the agent uses the shared memory path.
  - `src/rally/cli.py` — should remain the one front-door operator and agent surface for memory search, retrieval, save, refresh, and any visible memory-event readback.
  - `src/rally/services/issue_ledger.py` — should remain the one owner for appending normalized issue records when memory is used or created.

- Existing patterns to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — inherited env-var inputs plus required ambient skills are already the pattern for future `RALLY_AGENT_SLUG` or equivalent agent identity.
  - `skills/rally-kernel/SKILL.md` — thin shared skill guidance is already the pattern for teaching when to use a Rally-owned CLI surface without turning the skill into a second runtime.
  - `docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md` — already established the split between run-local notes, final JSON control, and Rally-owned front-door runtime behavior. Memory should extend that split instead of replacing it.

- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — should carry the turn-start rule to check memory after reading the issue and before real execution.
  - future `skills/rally-memory/SKILL.md` or equivalent Rally memory skill — should teach lookup, save, and the rule for when a reused lesson or repeat-fix lesson belongs in memory.
  - `skills/rally-kernel/SKILL.md` — stays the run-local note contract, so memory does not collapse back into notes.

- Native model or agent capabilities to lean on:
  - The current Rally base-agent plus skill model already supports explicit ordered instructions, env-var grounding, and CLI usage. There is no repo evidence that memory needs hidden prompt overlays, fuzzy wrappers, or model-substituting sidecars.
  - The useful model behavior here is judgment: the agent decides whether a found memory is relevant and whether a learned lesson is worth saving. QMD should supply recall, not replace that judgment.

- Existing grounding / tool / file exposure:
  - `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` already exist in the shared base-agent contract.
  - The future memory design can reuse that pattern and add one explicit agent identity env var instead of inferring scope from cwd or file layout.
  - `project_doc_max_bytes: 0` in `flows/single_repo_repair/flow.yaml` means Rally already prefers explicit context surfaces over ambient doc injection.

- Duplicate or drifting paths relevant to this change:
  - Run-local notes in `home/issue.md` versus future cross-run memory files under `runs/` — these must stay separate so reusable lessons do not blur into one-run context.
  - Direct QMD calls or direct file writes versus Rally CLI and issue-ledger front doors — letting both stay live would create hidden behavior and drift.
  - QMD's home-dir defaults versus Rally's repo-local state rule — this is the main path-ownership conflict the design must resolve.

- Capability-first opportunities before new tooling:
  - Use `stdlib/rally/prompts/rally/base_agent.prompt` to tell agents when to check memory and when to save it.
  - Use a thin Rally memory skill to teach how to use the front-door commands instead of adding hidden launch-time prose.
  - Use Rally CLI plus `issue_ledger` readback to make memory events visible before adding any extra viewer, dashboard, or sidecar control plane.

- Behavior-preservation signals already available:
  - `tests/unit/domain/test_turn_result_contracts.py` — protects the rule that routed control still comes only from validated final JSON with one `next_owner`.
  - `tests/unit/test_flow_loader.py` — protects the flow-loader and final-output contract boundary, including the requirement that `handoff` requires `next_owner`.
  - Those tests matter here because memory must not weaken the current note/final-result control split while the feature is added later.

## 3.3 Decision gaps that must be resolved before implementation

- No user blocker question remains.
- The main plan-shaping choices are already locked:
  - durable memory source files live under `runs/memory/entries/<flow_code>/<agent_slug>/`
  - one shared repo-local QMD store lives under `runs/memory/qmd/`
  - QMD scope is one collection per flow-agent pair
  - launcher/runtime injects `RALLY_AGENT_SLUG`
  - issue-ledger readback distinguishes discovery from actual use by recording `Memory Used` and `Memory Saved`
  - the implementation order is data plane, then visibility, then shared agent contract, then one narrow proof flow
- No unresolved plan-shaping decisions remain in this artifact.
- The remaining work is implementation against the chosen boundaries, not more architecture selection.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Shared Rally prompt doctrine lives under `stdlib/rally/prompts/rally/`.
  - `stdlib/rally/prompts/rally/base_agent.prompt` already injects `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`, and requires the ambient `rally-kernel` skill.
- Shared Rally skills live under `skills/`.
  - `skills/rally-kernel/SKILL.md` exists.
  - There is no `skills/rally-memory/` package yet.
- Runtime seams live under `src/rally/services/` and `src/rally/adapters/`.
  - `src/rally/cli.py` exists but only exposes `run` and `resume`.
  - `src/rally/services/issue_ledger.py`, `home_materializer.py`, `run_store.py`, `event_log.py`, and `runner.py` are still placeholder boundaries.
- `runs/` exists at repo root, but there is no checked-in cross-run memory root under it yet.
- QMD is present only as a local reference repo under `for_reference_only/qmd/`. It is not yet a Rally dependency or a Rally-owned runtime surface.

## 4.2 Control paths (runtime)

- Rally-managed agents currently get:
  - shared run identity through `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`
  - the ambient `rally-kernel` skill
  - one final JSON control path through `rally.turn_results`
- Agents can leave run-local notes through the future-facing Rally CLI note path and end turns with final JSON.
- There is no current memory path for:
  - memory discovery
  - memory retrieval as a visible event
  - memory save as a visible event
  - memory source-file storage
  - memory index rebuild or refresh
- There is no `RALLY_AGENT_SLUG` env surface yet, so current runtime identity is not enough to scope memory per flow and per agent.
- If Rally called raw QMD today without a wrapper, QMD would still fall back to global cache and config defaults. That is incompatible with Rally's repo-local rule.

## 4.3 Object model + key abstractions

- Rally already has typed flow and turn-result contracts:
  - `src/rally/domain/flow.py` defines `FlowDefinition`, `FlowAgent`, and compiled agent contract types.
  - `src/rally/domain/run.py` defines `RunRequest`, `ResumeRequest`, and `RunStatus`.
  - `src/rally/domain/turn_result.py` defines the strict tagged turn-result model and already requires structural `next_owner` for `handoff`.
- Rally does not yet model:
  - `MemoryScope`
  - `MemoryEntry`
  - `MemorySearchHit`
  - `MemorySaveOutcome`
  - `MemoryEvent`
- QMD already models collections, paths, and search results, but Rally does not yet own a wrapper contract around those primitives.

## 4.4 Observability + failure behavior today

- `tests/unit/domain/test_turn_result_contracts.py` and `tests/unit/test_flow_loader.py` already protect the current control boundary: route truth still comes from validated final JSON, not notes or prose.
- The repo does not yet have:
  - memory events in `logs/events.jsonl`
  - normalized issue readback for memory use or memory save
  - any CLI-visible memory item
  - any memory source files to inspect on disk
- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` and `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` already define `home/issue.md` and `issue_history/` as the semantic ledger and archaeology path for trusted runtime records, but the code is not there yet.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
- The relevant future operator surface is CLI plus run-directory artifacts.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Keep durable memory source files under one Rally-owned repo-local root:
  - `runs/memory/entries/<flow_code>/<agent_slug>/<memory_id>.md`
- Keep one shared Rally-owned QMD state root:
  - `runs/memory/qmd/index.sqlite`
  - `runs/memory/qmd/config/index.yml`
  - `runs/memory/qmd/cache/` as the forced `XDG_CACHE_HOME` root for QMD cache and model files
- Add one Rally memory skill:
  - `skills/rally-memory/SKILL.md`
- Extend the shared base-agent prompt:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
- Add one pure memory contract module:
  - `src/rally/domain/memory.py`
- Add one source-of-truth memory service:
  - `src/rally/services/memory_store.py`
- Add one QMD wrapper service:
  - `src/rally/services/memory_index.py`

These are target-state structures to implement later.

## 5.2 Control paths (future)

1. The Codex launch harness injects `RALLY_AGENT_SLUG=<agent-slug>` on every Rally-managed turn alongside the existing run and flow env vars.
2. The shared base agent tells the agent:
   - read the issue first
   - then check memory for the current flow-agent scope before real execution
   - then continue with the turn
3. The `rally-memory` skill teaches the front-door commands:
   - `rally memory search`
   - `rally memory use`
   - `rally memory save`
   - `rally memory refresh`
4. `rally memory search` is discovery only.
   - It searches only the current flow-agent collection in the shared QMD store.
   - It may write structured telemetry to `logs/events.jsonl`.
   - It does not append to `home/issue.md` by itself.
5. `rally memory use` is the front door for actual retrieval.
   - It returns the full selected memory to the caller.
   - It writes a structured `memory_used` event through `event_log.py`.
   - It appends a normalized `Memory Used` record into `home/issue.md` through `issue_ledger.py`.
6. `rally memory save` is the front door for durable learning.
   - It writes or updates one markdown memory file through `memory_store.py`.
   - It refreshes only the current flow-agent collection in the shared QMD store through `memory_index.py`.
   - It writes a structured `memory_saved` event with outcome `created` or `updated`.
   - It appends a normalized `Memory Saved` record into `home/issue.md`.
7. `rally memory refresh` is the repair and rebuild path for operators or controlled runtime maintenance.
   - It rebuilds QMD state from markdown memory files.
   - It does not invent or modify semantic truth outside those source files.
8. Routing, `done`, `blocker`, and `sleep` still come only from the final JSON result.

## 5.3 Object model + abstractions (future)

- `MemoryScope`
  - fields: `flow_code`, `agent_slug`
  - v1 scope is exactly one flow plus one agent
- `MemoryEntry`
  - durable markdown source file with frontmatter for:
    - `id`
    - `flow_code`
    - `agent_slug`
    - `created_at`
    - `updated_at`
    - `source_run_id`
  - body sections should stay short and concrete:
    - `# Lesson`
    - `# When This Matters`
    - `# What To Do`
- `MemorySearchHit`
  - returned by `rally memory search`
  - includes `memory_id`, `path`, `title`, snippet, and score
- `MemorySaveOutcome`
  - `created` or `updated`
- `MemoryEvent`
  - structured runtime record with shared fields:
    - `kind`
    - `run_id`
    - `flow_code`
    - `agent_slug`
    - `memory_id`
    - `recorded_at`
  - `memory_saved` also carries `outcome=created|updated`
  - separate from the markdown memory file itself
- issue-ledger memory record
  - normalized readback derived from `MemoryEvent`
  - `Memory Used` records: agent, memory id, title, and a short note on why it mattered
  - `Memory Saved` records: agent, memory id, title, and save outcome
- QMD store contract
  - one shared repo-local store
  - one QMD collection per flow-agent scope
  - one root context per collection that explains the scope in plain language

## 5.4 Invariants and boundaries

- Markdown memory files are the only durable truth.
- QMD is only the search layer and rebuildable cache.
- One shared QMD store is the chosen architecture.
- One QMD collection per flow-agent pair is the chosen scope boundary.
- No raw QMD calls from agents.
- No direct memory-file writes from agents.
- Agents use Rally CLI front doors only.
- Search is discovery only.
- Only `memory_used` and `memory_saved` generate issue-ledger readback automatically.
- Memory event records are trusted runtime readback, not extra instruction overlays.
- No control truth in memory files or memory events.
- No cross-flow or cross-agent memory sharing in v1.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- No GUI work is in scope.
- CLI/readback is the user-facing visibility surface:

```text
rally memory search --run-id FLW-7 --agent scope_lead --query "repeat fix after resume"
  1. mem_flw_scope_lead_repeat_fix_guard
     When a fix comes back after review, save the lesson before handoff.

rally memory use --run-id FLW-7 --agent scope_lead mem_flw_scope_lead_repeat_fix_guard
  -> returns the selected memory
  -> logs memory_used
  -> appends "Memory Used" to home/issue.md

rally memory save --run-id FLW-7 --agent scope_lead --file /tmp/memory.md
  -> writes or updates one markdown memory file
  -> refreshes the scoped QMD collection
  -> logs memory_saved(created|updated)
  -> appends "Memory Saved" to home/issue.md
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## Change map (table)
| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Shared agent contract | `stdlib/rally/prompts/rally/base_agent.prompt` | `RallyManagedInputs`, `RallyManagedBaseAgent` | injects `RALLY_BASE_DIR`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, and `rally-kernel`; no memory behavior or agent slug | add `RALLY_AGENT_SLUG` env input and explicit turn-start / turn-end memory doctrine | memory scope needs agent identity and shared prompt timing | shared base-agent memory contract | rebuilt readback inspection |
| Shared skill surface | `skills/rally-memory/SKILL.md` | new skill package | missing | add a thin ambient memory skill with search/use/save/refresh guidance | keep memory use on one shared front door | `rally-memory` skill contract | skill/readback inspection |
| Existing shared skill | `skills/rally-kernel/SKILL.md` | note guidance | run-local notes only | clarify boundary against cross-run memory so the two surfaces do not drift together | note vs memory split must stay explicit | note-only contract | skill/readback inspection |
| CLI | `src/rally/cli.py` | command parsing | only `run` and `resume` | add `memory search`, `memory use`, `memory save`, `memory refresh` | make memory a first-class visible CLI surface | memory CLI contract | CLI unit tests |
| Pure domain | `src/rally/domain/memory.py` | new domain contracts | missing | add `MemoryScope`, `MemoryEntry`, `MemorySearchHit`, `MemorySaveOutcome`, `MemoryEvent` | keep memory policy out of CLI and filesystem code | typed memory contracts | domain unit tests |
| Source-of-truth service | `src/rally/services/memory_store.py` | new service | missing | write and update markdown memory files under `runs/memory/entries/...` | markdown must stay the source of truth | memory file contract | store unit tests |
| QMD wrapper service | `src/rally/services/memory_index.py` | new service | missing | own repo-local QMD env, config sync, scoped collections, search, retrieval, and refresh | raw QMD defaults violate Rally path rules | repo-local QMD wrapper contract | index unit tests |
| Ledger readback | `src/rally/services/issue_ledger.py` | append formatting | placeholder; note and final-result readback only in design docs | add normalized `Memory Used` and `Memory Saved` record append paths | used/saved memory must show up in the issue through the front door | memory ledger record contract | issue-ledger tests |
| Structured eventing | `src/rally/services/event_log.py` | event writes | placeholder | add `memory_used` and `memory_saved` structured events | memory should be visible like other runtime activity | event-log schema | event-log tests |
| Launch env | `src/rally/adapters/codex/launcher.py` | env construction | placeholder; no agent slug injection | inject `RALLY_AGENT_SLUG` for every turn | memory scope must not be guessed from cwd or path | launch contract | launcher tests |
| Turn orchestration | `src/rally/services/runner.py` | orchestration rules | placeholder | keep runner out of memory storage details; it should only preserve the turn contract while memory CLI commands operate through their owning services | prevent `runner.py` from becoming a god module | orchestration boundary | runner tests |
| Home materialization | `src/rally/services/home_materializer.py` | skill materialization | placeholder; design says allowlist-only | materialize Rally-managed ambient skills, including `rally-memory`, without requiring per-flow allowlist entries | memory should be built-in like `rally-kernel` | ambient skill materialization rule | materializer tests |
| Flow contract | `flows/single_repo_repair/flow.yaml` | per-agent allowlists | no ambient memory skill today | consume as input; do not add `rally-memory` to per-agent allowlists | memory is Rally-managed ambient behavior, not flow-local config | no flow contract change | flow-loader coverage |
| Real flow readback | `flows/single_repo_repair/prompts/AGENTS.prompt` and `build/agents/*` | shared inherited behavior | will not mention memory until prompt changes land | rebuild after base-agent changes so readback shows the new shared contract honestly | real flow must inherit the built-in memory contract | compiled readback | compile/readback inspection |
| Smoke flow readback | `flows/_stdlib_smoke/prompts/AGENTS.prompt` and `build/agents/*` | stdlib smoke | will not mention memory until prompt changes land | rebuild after base-agent changes | keep stdlib proof surface aligned | compiled readback | compile/readback inspection |
| Master design | `docs/RALLY_MASTER_DESIGN_2026-04-12.md` | future-direction note and runtime tables | mentions future memory direction, but not the chosen architecture | update after implementation so master design reflects the chosen memory root, issue events, and CLI surface | keep master design aligned with shipped truth | live design doc | docs review |
| Runtime design doc | `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` | issue/event model | defines issue ledger and structured events but not memory event types | update if implementation lands memory events on the same surfaces | keep runtime docs aligned with shipped event model | live runtime doc | docs review |

## Migration notes
* Canonical owner path / shared code path:
  - prompt timing and agent behavior: `stdlib/rally/prompts/rally/base_agent.prompt`
  - user-facing memory guidance: `skills/rally-memory/SKILL.md`
  - front-door commands: `src/rally/cli.py`
  - durable markdown truth: `src/rally/services/memory_store.py`
  - repo-local QMD wrapper and scoped collections: `src/rally/services/memory_index.py`
  - normalized issue readback: `src/rally/services/issue_ledger.py`
  - structured event visibility: `src/rally/services/event_log.py`
* Deprecated APIs (if any):
  - none yet; this is additive future-state design
* Delete list (what must be removed; include superseded shims/parallel paths if any):
  - any direct raw `qmd` invocation from agent prompts or skills
  - any direct agent write path to memory markdown files
  - any hidden prompt overlay that injects memory prose outside the `.prompt` graph
  - any future attempt to treat run-local notes as cross-run memory
* Capability-replacing harnesses to delete or justify:
  - do not add fuzzy retrieval wrappers, parser sidecars, or synthetic memory orchestrators that replace agent judgment
* Live docs/comments/instructions to update or delete:
  - sync the master design and runtime design docs when memory ships
  - sync `docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md` if shipped memory changes how the note vs memory split is explained
  - add short code comments only at the memory store, QMD wrapper, and issue-ledger boundaries where front-door behavior could be bypassed
* Behavior-preservation signals for refactors:
  - `tests/unit/domain/test_turn_result_contracts.py` must keep proving that routing still comes from final JSON only
  - `tests/unit/test_flow_loader.py` must keep proving that flow loading and handoff schema validation stay strict
  - memory additions must not weaken the note/final-result control split

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)
| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared ambient skills | `skills/rally-kernel/`, new `skills/rally-memory/`, `src/rally/services/home_materializer.py` | Rally-managed ambient skills materialize without per-flow allowlist entries | prevents each flow from growing its own local memory story | include |
| Shared prompt doctrine | `stdlib/rally/prompts/rally/base_agent.prompt` | turn-start recall and turn-end save live in the shared base agent | prevents flow-local drift and hidden memory overlays | include |
| Flow proof surfaces | `flows/_stdlib_smoke/*`, `flows/single_repo_repair/*` | rebuild on the shared memory contract | prevents stdlib drift from real-flow drift | include |
| Ledger readback | `src/rally/services/issue_ledger.py` | memory events use the same trusted append path as other runtime records | prevents side-channel history and missing introspection | include |
| Structured eventing | `src/rally/services/event_log.py` | memory events use the same run-local structured event stream as other runtime activity | keeps CLI/readback archaeology consistent | include |
| QMD store topology | new `src/rally/services/memory_index.py` | one shared store with one collection per flow-agent scope | avoids duplicate stores, duplicate model caches, and non-native path filtering | include |
| Future cross-scope sharing | any later cross-flow or cross-agent memory feature | shared or promoted memory scopes | this is new product behavior, not required for v1 memory | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with the smallest credible signal. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Lock the memory data plane and CLI contract

Goal
- Land the durable memory-file contract, the repo-local QMD wrapper, and the front-door CLI shape before any shared prompt starts teaching agents to use memory.

Work
- Add `src/rally/domain/memory.py` with `MemoryScope`, `MemoryEntry`, `MemorySearchHit`, `MemorySaveOutcome`, and `MemoryEvent`.
- Add `src/rally/services/memory_store.py` so markdown files under `runs/memory/entries/<flow_code>/<agent_slug>/` become the only durable memory truth.
- Add `src/rally/services/memory_index.py` so Rally, not agents, owns:
  - forced repo-local QMD paths
  - one shared store under `runs/memory/qmd/`
  - one collection per flow-agent scope
  - scoped search, retrieval, and refresh behavior
- Extend `src/rally/cli.py` with `memory search`, `memory use`, `memory save`, and `memory refresh`.
- Keep this phase strict about boundaries:
  - no raw `qmd` calls from prompts or skills
  - no direct memory-file writes from agents
  - no global QMD fallback paths
- Define the save/update rule now so `memory save` can return `created` or `updated` without leaving duplicate memories as a later cleanup problem.

Verification (smallest signal)
- Add focused unit tests for:
  - repo-local QMD path forcing
  - flow-agent scope resolution
  - markdown file write and update behavior
  - `memory save` created-versus-updated outcomes
- Run one CLI-level proof that a scoped memory can be saved, searched, used, and refreshed without touching `~/.cache` or `~/.config`.

Docs/comments (propagation; only if needed)
- Add one short code comment in `memory_store.py` stating that markdown is the only durable truth.
- Add one short code comment in `memory_index.py` stating that Rally forces all QMD state under `runs/`.

Exit criteria
- Rally has one working repo-local memory store and one working repo-local QMD wrapper.
- The memory CLI exists and uses only Rally-owned services.
- A saved memory round-trips through save, search, and use inside one flow-agent scope.

Rollback
- Revert the memory data-plane changes together if the implementation needs global QMD state, direct agent file writes, or duplicate durable sources of truth to function.

## Phase 2 - Wire visibility, issue readback, and runtime scope

Goal
- Make every real memory use and save action visible on Rally-owned runtime surfaces and scope those actions with explicit run plus agent identity.

Work
- Extend `src/rally/services/issue_ledger.py` with normalized `Memory Used` and `Memory Saved` append paths.
- Extend `src/rally/services/event_log.py` with structured `memory_used` and `memory_saved` events.
- Keep `memory search` as discovery only:
  - it may emit structured telemetry
  - it must not append into `home/issue.md`
- Extend `src/rally/adapters/codex/launcher.py` to inject `RALLY_AGENT_SLUG` beside the existing run and flow env vars.
- Extend `src/rally/services/home_materializer.py` so `rally-memory` is materialized as a Rally-managed ambient skill rather than a per-flow allowlist item.
- Keep `src/rally/services/runner.py` orchestration-only. Memory writes, issue append logic, and QMD refresh logic should stay in their owning services.

Verification (smallest signal)
- Add focused unit tests for:
  - `Memory Used` issue append formatting
  - `Memory Saved` issue append formatting
  - `memory_used` and `memory_saved` event payloads
  - `RALLY_AGENT_SLUG` launch injection
  - ambient `rally-memory` materialization without `flow.yaml` allowlist changes
- Add one CLI-level proof that `memory search` stays out of the issue ledger while `memory use` and `memory save` show up there.

Docs/comments (propagation; only if needed)
- Add one short code comment in `issue_ledger.py` marking memory readback as trusted runtime readback, not instruction text.
- Add one short code comment in `launcher.py` marking `RALLY_AGENT_SLUG` as the only supported agent-scope input for memory.

Exit criteria
- Memory use and save are first-class visible Rally events.
- The issue ledger records only actual use and save actions.
- Agent scope is explicit and does not depend on cwd or path guessing.

Rollback
- Revert the visibility wiring together if memory actions can happen without visible Rally-owned records or if search starts polluting the issue ledger.

## Phase 3 - Roll the shared agent contract forward

Goal
- Teach Rally-managed agents when to recall memory and when to save it through one shared prompt-plus-skill contract.

Work
- Add `skills/rally-memory/SKILL.md` as the thin shared memory skill that teaches `search`, `use`, `save`, and `refresh`.
- Update `skills/rally-kernel/SKILL.md` so the note-only boundary stays explicit and memory does not blur back into run-local notes.
- Update `stdlib/rally/prompts/rally/base_agent.prompt` so every Rally-managed agent:
  - reads the issue first
  - checks memory after reading the issue and before real execution
  - saves reusable lessons at turn end when they are worth keeping
  - always saves a reusable lesson after repeat-fix or rework cases
- Rebuild `_stdlib_smoke` and `single_repo_repair` with the paired Doctrine compiler and inspect the generated readback.
- Keep `flows/*/flow.yaml` unchanged for memory allowlists so the ambient-skill rule stays honest.

Verification (smallest signal)
- Recompile `_stdlib_smoke` and `single_repo_repair`, then inspect representative generated agents for:
  - inherited base-agent memory doctrine
  - visible `rally-memory` guidance
  - unchanged final-JSON control rules
- Keep `tests/unit/domain/test_turn_result_contracts.py` and `tests/unit/test_flow_loader.py` green to prove memory did not weaken the current control boundary.

Docs/comments (propagation; only if needed)
- Update prompt-adjacent docs only where the old note-versus-memory story would otherwise stay live.

Exit criteria
- Shared Rally prompt source and shared Rally skills tell one consistent memory story.
- Rebuilt readback shows the memory contract in real compiled agents.
- No flow needs a local memory prompt workaround.

Rollback
- Revert prompt, skill, and readback changes together if the shared contract starts introducing side-door prose or weakens the final-JSON control boundary.

## Phase 4 - Prove one narrow flow and sync live repo truth

Goal
- Finish with one believable Rally proof path and one honest repo-wide story about how built-in memory works.

Work
- Add one narrow Rally integration proof for `single_repo_repair` that covers:
  - scoped memory save
  - later scoped memory retrieval
  - visible `memory_used` and `memory_saved` records
  - unchanged note and final-result control behavior
- Prove the search boundary:
  - discovery can be logged
  - only use and save reach the issue ledger
- Sync the live docs that would otherwise drift:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md`
- Delete any raw `qmd` prompt usage, direct memory-file write path, or other side-door memory experiment that appears during implementation.

Verification (smallest signal)
- Run the existing contract tests plus the new memory unit coverage.
- Recompile `_stdlib_smoke` and `single_repo_repair` and inspect representative readback.
- Run one narrow real-flow proof that memory recall and learning work without changing routing, `done`, `blocker`, or `sleep` truth.

Docs/comments (propagation; only if needed)
- Delete stale wording rather than preserving old memory explanations beside the shipped design.

Exit criteria
- The acceptance evidence in Section 0.4 is materially satisfied.
- One real Rally flow proves the memory model end to end.
- Live design docs, shared prompt source, generated readback, and runtime seams all tell the same story.

Rollback
- Preserve failed run artifacts for archaeology and revert any half-cut memory path that leaves hidden state, mixed issue semantics, or stale live docs behind.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Avoid verification bureaucracy. Prefer the smallest existing signal. Keep the proof set small and phase-scoped.

## 8.1 Unit tests (contracts)

- Keep `tests/unit/domain/test_turn_result_contracts.py` and `tests/unit/test_flow_loader.py` green so memory does not weaken the current control boundary.
- Add small tests for repo-local QMD path forcing, flow-agent scope resolution, memory file write and update rules, and normalized `Memory Used` / `Memory Saved` records.
- Add small tests for `memory_used` / `memory_saved` event payloads, `RALLY_AGENT_SLUG` launch injection, and ambient `rally-memory` materialization.

## 8.2 Integration tests (flows)

- Recompile `_stdlib_smoke` and `single_repo_repair` and inspect representative generated agents for the shared memory contract.
- Add one narrow Rally integration check that proves memory lookup and save do not change note or routing behavior.
- Add one narrow Rally integration check that proves `memory search` stays out of the issue ledger while `memory_used` and `memory_saved` land there through the front door.

## 8.3 E2E / device tests (realistic)

- Keep E2E scope small in v1. A single real-flow proof is enough if it covers lookup, save, and repo-local storage.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land the design and storage boundary first.
- Roll out memory on one Rally flow before widening it.
- Keep failure behavior loud while the feature is still narrow.
- Keep memory events visible from day one so operators can inspect what was recalled and what was learned.

## 9.2 Telemetry changes

- Record `memory_used` and `memory_saved` in Rally-owned logs when the runtime surfaces exist.
- If Rally keeps search telemetry, keep it in `logs/events.jsonl` only and keep it out of the issue ledger.
- Record normalized `Memory Used` and `Memory Saved` records in the issue ledger when those actions happen.
- Keep the logs about behavior and path ownership, not about hidden scoring magic.

## 9.3 Operational runbook

- Rebuild QMD state from markdown files if the index drifts or is cleared.
- Keep operator repair steps repo-local and explicit.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self cold read 1, self cold read 2, self-integrator
- Scope checked:
  - frontmatter, `planning_passes`, `# TL;DR`, `# 0)` through `# 10)`, and helper blocks
  - cross-section agreement on memory event naming, command surface, canonical owner path, execution order, verification burden, rollout obligations, and live-doc sync
- Findings summary:
  - the artifact still mixed `creation` language with the chosen `memory_saved` event contract
  - Section `0.2` still listed `get` even though the chosen CLI and phase plan use `use`
  - Section `3.3` still read like mid-plan status instead of implementation readiness
  - Section `8)` still implied a smaller proof burden than the phase plan now requires
- Integrated repairs:
  - aligned `# TL;DR`, `# 0)`, `# 1)`, and the memory-event decision entry around `use` and `save`
  - replaced the stray `get` command reference with the chosen `use` front door
  - rewrote Section `3.3` so it now states that plan-shaping decisions are resolved and implementation can proceed against the locked architecture
  - aligned the Section `8)` preamble with the phase-scoped proof burden already encoded in Section `7)`
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

## 2026-04-13 - Keep markdown as memory truth and QMD as the search layer

Context
- The user wants a built-in Rally memory model that uses QMD.
- Rally's design rules forbid hidden global state and prefer filesystem truth.
- QMD can search markdown well, but its default cache and config locations are outside the repo.

Options
- Make QMD's SQLite data the source of truth.
- Keep markdown files as truth and use QMD as the search index.
- Inject memory as hidden extra prose at launch without a Rally-owned wrapper.

Decision
- Keep markdown memory files as the durable source of truth and use QMD only as the search layer.
- Wrap QMD behind Rally-owned paths and commands.
- Make memory lookup and save explicit prompt-plus-skill behavior instead of hidden injected prose.

Consequences
- Rally needs a clear repo-local path contract for QMD config, index, and model cache.
- Rally likely needs a new agent identity env surface for memory scope.
- Memory entries must stay short and structured enough to be useful on disk and in search.

Follow-ups
- Confirm the North Star for scope and boundaries.
- Resolve the exact path layout, agent identity key, and QMD store shape in research and deep dive.

## 2026-04-13 - Treat this artifact as future-state design, not current-state readback

Context
- The user explicitly said not everything is built yet and that this work is design ahead of implementation.
- Rally's current repo already has clear partial-runtime seams, but many of the memory surfaces do not exist yet.

Options
- Write the plan as if the current repo already has the memory runtime.
- Write the plan as a future-state target that later stages will implement.

Decision
- Treat this artifact as future-state architecture for later implementation.
- Keep current-state gaps visible in Sections 2 and 4 instead of shrinking the design to today's partial code.

Consequences
- Later `research`, `deep-dive`, and `phase-plan` passes should refine the target design without pretending the code already exists.
- Missing implementation in the current repo is not a blocker for the architecture shape itself.

Follow-ups
- Keep later planning and implementation passes honest about which parts are designed, which parts are built, and which proofs have actually run.

## 2026-04-13 - Make memory events first-class visible runtime records

Context
- The user wants memory retrieval and storage to be fully introspectable in Rally's future CLI.
- The user wants memory use and memory save to show up in the issue through front-door mechanisms.
- Rally already treats issue appends and other trusted runtime records as Rally-owned surfaces.

Options
- Let memory search and save happen quietly, with no visible runtime record.
- Show memory events only in ad hoc debug logs.
- Make memory use and memory save first-class visible Rally events and append normalized issue records through the trusted ledger path.

Decision
- Treat memory use and memory save as first-class visible runtime events.
- Append normalized issue records for those events through Rally-owned front-door paths.
- Keep those event records separate from routing, notes, and the memory-file source of truth.

Consequences
- Rally needs a clear CLI/readback shape for memory events.
- `issue_ledger` becomes part of the memory design, not just the note design.
- The plan needs proof that memory events are visible and front-door only.

Follow-ups
- Define the event record shape in deep dive.
- Decide whether plain search queries without actual memory use should stay out of the issue.

## 2026-04-13 - Use one shared repo-local QMD store with one collection per flow-agent scope

Context
- The user wants memory to stay per agent and per flow.
- QMD already supports collections as a native scope boundary.
- Rally also needs one repo-local place for forced QMD config, index, and model cache state.

Options
- One QMD store per flow-agent scope.
- One shared QMD store with one collection per flow-agent scope.
- One shared QMD store with one global collection and path filtering.

Decision
- Use one shared QMD store under `runs/memory/qmd/`.
- Use one QMD collection per flow-agent scope.
- Keep markdown source files under `runs/memory/entries/<flow_code>/<agent_slug>/`.

Consequences
- Rally keeps one index and one model-cache root instead of many small copies.
- Scope filtering stays native to QMD instead of becoming a Rally-side search shim.
- Rally must keep collection config in sync with the markdown entry tree.

Follow-ups
- Define the exact `memory_index.py` wrapper contract in implementation planning.
- Add narrow tests that prove the wrapper never falls back to global QMD paths.

## 2026-04-13 - Keep search as discovery and make use/save the visible front doors

Context
- The user wants memory retrieval and storage to be first-class visible items.
- The user also wants used and saved memory to land in the issue through Rally-owned front doors.
- Rally should not flood the issue with every tentative search query.

Options
- Append every search, use, and save action into the issue.
- Keep search as discovery, then log and append only real use and save actions.
- Hide the whole memory path behind silent runtime helpers.

Decision
- Keep `rally memory search` as discovery only.
- Treat `rally memory use` and `rally memory save` as the visible front doors.
- Append normalized issue records only for `Memory Used` and `Memory Saved`.

Consequences
- The issue stays focused on memory that actually changed the turn.
- Rally can still keep low-level search telemetry in `logs/events.jsonl` without turning it into issue noise.
- CLI readback stays honest because the memory actions that matter are visible on the same trusted path every time.

Follow-ups
- Define the exact issue-ledger record format for `Memory Used` and `Memory Saved`.
- Keep any future search telemetry out of route truth and terminal-control truth.

## 2026-04-13 - Sequence the memory rollout as data plane, then visibility, then shared agent contract

Context
- The repo is still early, so prompt text cannot honestly teach a memory workflow until the front-door runtime path exists.
- The user wants built-in memory behavior, visible memory events, and future shared-agent adoption, not a one-off local experiment.

Options
- Prompt-first rollout that teaches memory before the CLI and runtime surfaces exist.
- One big vertical slice that mixes storage, visibility, prompt rollout, and proof in one step.
- Depth-first rollout: lock the data plane first, then visibility and scope, then shared prompt and skill rollout, then one narrow proof.

Decision
- Sequence the implementation as:
  - data plane and CLI contract
  - visibility plus issue and event readback
  - shared prompt and skill rollout
  - one narrow proof flow plus doc sync

Consequences
- Agents only learn commands after those commands are real.
- The user-visible introspection requirement lands before broad prompt rollout.
- Proof stays narrow and believable because it sits on top of already-owned storage and visibility surfaces.

Follow-ups
- Keep Section 7 as the only execution checklist for this sequence.
- Make sure later implementation does not collapse the four phases back into one mixed cutover.
