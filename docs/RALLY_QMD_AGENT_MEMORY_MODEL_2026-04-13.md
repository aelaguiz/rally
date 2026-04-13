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
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - skills/rally-kernel/SKILL.md
  - flows/poem_loop/prompts/shared/inputs.prompt
  - flows/poem_loop/prompts/shared/outputs.prompt
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/run_events.py
  - src/rally/adapters/codex/launcher.py
  - for_reference_only/qmd/README.md
  - for_reference_only/qmd/src/store.ts
  - for_reference_only/qmd/src/collections.ts
  - for_reference_only/qmd/src/llm.ts
---

# TL;DR

Outcome
- Add one built-in Rally memory model that is native to Doctrine authoring and native to Rally runtime.
- Give every Rally-managed agent one shared issue-ledger input, one shared memory skill, one shared memory entry shape, and one shared read order for when memory belongs in the turn.
- Keep durable memory in repo-local markdown files and use QMD only as the search index over those files.
- Make `memory use` and `memory save` visible Rally events that also append trusted readback into `home/issue.md`.

Problem
- Rally does not have cross-run memory yet.
- The shared Rally stdlib still does not give every agent the issue ledger, the current agent slug, or a shared memory contract.
- One flow already carries its own local issue-ledger input and note structures, which is useful proof that Doctrine can express this shape, but it also shows how memory would drift if Rally adds it as runtime-only behavior.
- QMD is a good fit for search, but its default cache and config paths break Rally's repo-local rules if Rally uses it raw.

Approach
- Put the agent-facing memory contract in Doctrine source first.
- Make Rally runtime back that contract with repo-local storage, QMD indexing, CLI commands, and visible event/readback paths.
- Reuse the compiled Doctrine agent slug as the only agent-scope truth and project that same slug into `RALLY_AGENT_SLUG` for runtime use.
- Converge flow-local issue-ledger and generic memory patterns back into the shared stdlib instead of letting each flow tell its own memory story.

Plan
- Lock the North Star and owner split around Doctrine-first memory.
- Add the shared stdlib pieces: issue-ledger input, memory document, memory skill, and shared read-order blocks.
- Rerun the deep-dive around runtime, call sites, and deletes using that contract.
- Land the runtime backing, then visibility, then one narrow flow proof, then sync live docs.

Non-negotiables
- Doctrine owns the agent-facing memory contract.
- Rally owns storage, indexing, CLI behavior, issue appends, and runtime events.
- The compiled Doctrine agent slug is the source of truth for agent scope.
- Markdown memory files are the source of truth. QMD is only a rebuildable search index.
- No hidden memory prose outside the declared `.prompt` graph.
- No per-flow generic memory lifecycle rules once the shared stdlib contract exists.
- Memory never carries routing, `done`, `blocker`, or `sleep` truth.

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

Rally can add built-in cross-run memory without turning memory into a custom side system if it does all of the following at the same time:

- authors the shared memory contract in Doctrine stdlib
- gives every Rally-managed agent the shared issue ledger as an inherited input
- gives every Rally-managed agent a shared memory skill, shared memory entry shape, and shared read order
- keeps Rally runtime responsible for storage, search, issue append, and event visibility
- keeps the durable memory source of truth in repo-local markdown files
- treats `RALLY_AGENT_SLUG` as a runtime projection of the compiled Doctrine agent slug, not as a second identity source
- keeps flow-local prompts focused on flow-local work instead of generic memory rules

This claim is false if any of the following stay true after the work lands:

- a flow still needs its own generic issue-ledger input or generic memory timing rules
- the memory entry shape only exists in runtime docs or Python validators and not in shared prompt source
- Rally invents a second agent identity source for memory scope
- memory reaches agents through hidden launch-time prose instead of the shared `.prompt` graph
- QMD still writes state under `~/.cache`, `~/.config`, or other hidden global paths
- memory use or save can happen without a Rally-owned visible record
- memory can change routing, `done`, `blocker`, or `sleep` truth

This section describes the target state Rally should reach after implementation.
It does not claim the current repo already behaves this way.

## 0.2 In scope

- one built-in Rally memory model for cross-run learning
- future-state design for later implementation of that model
- one shared stdlib issue-ledger input for all Rally-managed agents
- one shared stdlib memory module, likely `stdlib/rally/prompts/rally/memory.prompt`
- one shared memory skill in the Rally-managed skill set
- one shared memory entry document shape authored in Doctrine
- one shared read-order and turn-sequence contract authored in Doctrine
- exposing `RALLY_AGENT_SLUG` to prompts as the runtime projection of the compiled agent slug
- repo-local markdown memory files under `runs/`
- repo-local QMD config, index, and model cache under `runs/`
- Rally CLI memory commands for search, use, save, and refresh
- visible `memory_used` and `memory_saved` runtime records
- normalized `Memory Used` and `Memory Saved` issue-ledger records
- convergence work needed to remove flow-local generic issue-ledger and memory patterns once the shared stdlib contract exists
- docs and readback updates needed to keep the repo truthful

## 0.3 Out of scope

- implementing the full memory system in this planning pass
- cross-flow shared memory in v1
- cross-agent shared memory in v1
- hidden launch-time memory snippets
- DB-only memory truth
- non-QMD retrieval stacks
- automatic memory writing with no agent judgment
- new dashboards, boards, or memory review UIs
- widening memory into a general repo knowledge base
- leaving both shared-stdlib memory rules and flow-local generic memory rules alive in parallel

## 0.4 Definition of done (acceptance evidence)

- Rally has one documented memory model with one clear owner split: Doctrine for agent-facing contract, Rally for runtime backing.
- `RallyManagedInputs` includes the shared issue ledger and the current agent slug.
- `RallyManagedSkills` includes `rally-memory` beside `rally-kernel`.
- the shared stdlib defines the memory entry body shape and shared read-order blocks
- compiled readback for `_stdlib_smoke` and `poem_loop` shows the shared issue-ledger and memory contract honestly
- the runtime saves memory under repo-local markdown paths and forces QMD state to stay repo-local
- memory scope resolves by flow plus compiled agent slug
- one narrow real-flow proof shows a relevant memory can be found, used, and saved without changing note or routing semantics
- `memory_used` and `memory_saved` show up in Rally logs and append trusted readback into `home/issue.md`
- the master design, runtime design docs, shared prompt source, and compiled readback all say the same thing about notes, memory, and turn control

This is acceptance evidence for the later implementation.
It is not a claim about the current repo state.

## 0.5 Key invariants (fix immediately if violated)

- Doctrine owns the shared issue-ledger, memory-skill, memory-shape, and read-order contract.
- Rally owns memory storage, memory indexing, memory CLI behavior, issue appends, and runtime event visibility.
- The compiled Doctrine agent slug is the only source of truth for agent scope.
- `RALLY_AGENT_SLUG` is a runtime mirror of that compiled slug, not a new meaning.
- Markdown memory files are the only durable memory truth.
- QMD state used by Rally stays repo-local.
- Memory lookup is explicit agent behavior taught by shared prompt source and shared skills.
- Flow-local prompts may add flow-local memory fields only when they are truly flow-specific. They must not restate the generic memory lifecycle.
- Run-local notes stay run-local. Cross-run memory stays reusable.
- Memory may shape execution, but it never becomes route truth or terminal-control truth.
- If QMD is missing or misconfigured, memory commands fail loud instead of silently switching stores.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make the memory contract native to Doctrine instead of runtime-only.
2. Keep one source of truth for agent scope and one source of truth for durable memory.
3. Keep memory use and save easy to inspect from Rally's front-door surfaces.
4. Prevent per-flow drift by moving generic issue-ledger and memory rules into the shared stdlib.
5. Keep the runtime backing thin, explicit, and repo-local.
6. Keep every saved memory short, concrete, and easy to audit on disk.

## 1.2 Constraints

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` already says Rally is Doctrine-native and that `home/issue.md` is the shared run ledger.
- `src/rally/services/home_materializer.py` already enforces `home/issue.md` as Rally's one sanctioned shared startup input.
- `stdlib/rally/prompts/rally/base_agent.prompt` already owns the shared Rally-managed input and skill surface, but today it only exposes three env vars and `rally-kernel`.
- `stdlib/rally/prompts/rally/issue_ledger.prompt` and `stdlib/rally/prompts/rally/notes.prompt` already own the issue-append target shape.
- `src/rally/domain/flow.py`, `src/rally/services/flow_loader.py`, and the compiled `AGENTS.contract.json` files already carry the concrete agent slug.
- `src/rally/adapters/codex/launcher.py` already injects `RALLY_AGENT_SLUG`; the shared prompt contract just does not use it yet.
- `flows/poem_loop` already proves Doctrine can express structured issue-ledger inputs and structured issue-note documents, but that pattern is still flow-local.
- `src/rally/services/home_materializer.py` still treats `rally-kernel` as the only mandatory ambient skill.
- QMD supports explicit path control, but its defaults still point at global cache and config directories.
- Rally is Python and QMD is Node, so the runtime boundary must stay narrow and explicit.

## 1.3 Architectural principles (rules we will enforce)

- Put agent-facing memory behavior in shared prompt source before adding runtime glue.
- Reuse first-class Doctrine inputs, skills, documents, and shared workflow bodies before inventing Rally-only prompt patterns.
- Treat the compiled Doctrine agent slug as the source of truth and mirror it into runtime env only for access.
- Keep `home/issue.md` as the shared run ledger. Do not let each flow define a generic ledger path.
- Keep runtime front doors small: `search`, `use`, `save`, and `refresh`.
- Keep `search` as discovery only. Treat `use` and `save` as the trusted visible actions.
- Use the existing Rally event and issue-ledger paths instead of new side channels.
- Delete or converge duplicate live paths instead of leaving them in parallel.

## 1.4 Known tradeoffs (explicit)

- A richer shared stdlib contract will make compiled readback longer, but it will also remove per-flow drift.
- Moving the issue-ledger input into the shared base contract means some flows will need cleanup even if they do not care about memory yet.
- Keeping the memory body shape in Doctrine means the runtime has to validate and preserve that shape instead of treating memory as arbitrary markdown.
- Treating the compiled agent slug as the source of truth may force small flow-loader cleanup so runtime identity is carried from compiled contracts instead of local derivation alone.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally's master design already points toward built-in memory as a later step.
- The shared base agent already gives all Rally-managed agents a small inherited contract.
- The shared note path already exists through the issue-ledger target and `rally-kernel`.
- Rally runtime already prepares `home/issue.md` and already injects `RALLY_AGENT_SLUG` into Codex launches.
- Compiled Doctrine contracts already include the concrete agent slug.
- `poem_loop` already uses structured Doctrine documents for issue notes and a local issue-ledger input.
- QMD exists locally as a reference repo and is a good fit for markdown search.

## 2.2 What’s broken / missing (concrete)

- There is still no cross-run memory surface.
- The shared stdlib does not yet expose the issue ledger to every Rally-managed agent.
- The shared stdlib does not yet expose the current agent slug to prompts.
- The shared stdlib does not yet define a memory entry shape, a shared memory skill, or a shared memory read order.
- One flow still carries its own generic issue-ledger input instead of inheriting that from the stdlib.
- There is no Rally-owned CLI for memory search, use, save, and refresh.
- There is no repo-local QMD contract yet.
- There is no visible `memory_used` or `memory_saved` record yet.

## 2.3 Constraints implied by the problem

- Memory must not become a hidden runtime overlay.
- The design must separate run-local notes from reusable cross-run memory.
- The design must extend the current base-agent and shared-skill pattern instead of creating a second instruction system.
- The design must reuse the compiled agent slug instead of inventing a new identity meaning.
- Memory introspection must use Rally CLI, Rally events, and Rally issue append paths, not raw QMD calls or direct file writes from agents.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `for_reference_only/qmd/README.md` — adopt QMD as the search engine shape because it already supports markdown collections, keyword and vector search, reranking, and JSON output.
- `for_reference_only/qmd/src/store.ts` and `for_reference_only/qmd/src/index.ts` — adopt QMD's explicit path configuration surface because Rally needs to force repo-local paths.
- `for_reference_only/qmd/src/collections.ts` and `for_reference_only/qmd/src/llm.ts` — reject QMD's default path behavior because the defaults still fall back to home-dir cache and config locations that Rally forbids.
- No web research is needed for this pass. The local QMD checkout is enough to settle the storage and path-ownership question.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — says Rally is Doctrine-native, filesystem-first, and that `home/issue.md` is the shared run ledger.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — is the current shared base contract for inherited inputs and skills.
  - `stdlib/rally/prompts/rally/issue_ledger.prompt` — already owns the issue-ledger append target shape.
  - `stdlib/rally/prompts/rally/notes.prompt` — already maps shared note output onto the issue-ledger append target.
  - `src/rally/services/home_materializer.py` — already enforces `home/issue.md` and already materializes mandatory ambient skills.
  - `src/rally/domain/flow.py` and `src/rally/services/flow_loader.py` — already model flow agents, compiled agents, and agent slugs.
  - `src/rally/adapters/codex/launcher.py` — already injects `RALLY_AGENT_SLUG`.
  - `flows/poem_loop/prompts/shared/inputs.prompt` and `flows/poem_loop/prompts/shared/outputs.prompt` — already prove that Doctrine can carry structured issue-ledger inputs and structured note documents.

- Canonical path / owner to reuse:
  - `stdlib/rally/prompts/rally/issue_ledger.prompt` — should own the shared issue-ledger input and the shared issue-ledger target contract.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — should own inherited Rally-managed inputs, inherited Rally-managed skills, and shared read-order fields.
  - new `stdlib/rally/prompts/rally/memory.prompt` — should own the shared memory document, shared memory skill declaration, and shared memory read-order workflow blocks.
  - `src/rally/cli.py` — should own the front-door memory commands.
  - `src/rally/services/issue_ledger.py` and `src/rally/services/run_events.py` — should own trusted readback and visible event records for real memory actions.

- Existing patterns to reuse:
  - `flows/poem_loop/prompts/shared/outputs.prompt` — shows Rally can author durable markdown structures with Doctrine `document` blocks instead of prose-only format rules.
  - `../doctrine/examples/21_first_class_skills_blocks/prompts/AGENTS.prompt` — shows the native way to express a shared skill block.
  - `../doctrine/examples/23_first_class_io_blocks/prompts/AGENTS.prompt` and `../doctrine/examples/25_abstract_agent_io_override/prompts/AGENTS.prompt` — show the native way to share inputs and outputs through abstract agent contracts.
  - `../doctrine/examples/12_role_home_composition/prompts/AGENTS.prompt` — shows the native pattern for shared read-order and turn-sequence workflow fields without inventing new syntax.

- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — should carry inherited issue-ledger input, inherited agent-slug input, shared read-order blocks, and the required skill set.
  - `skills/rally-kernel/SKILL.md` — should stay the note-only boundary.
  - new `skills/rally-memory/SKILL.md` — should teach the front-door memory commands and when to use them.

- Native model or agent capabilities to lean on:
  - Rally-managed agents already know how to read shared file inputs, follow ordered readable workflow fields, use shared skills, and end turns with strict final JSON.
  - The useful model behavior here is still judgment: choose whether a found memory matters and whether a learned lesson is worth saving.

- Existing grounding / tool / file exposure:
  - `home/issue.md` already exists as the shared run ledger in the runtime.
  - `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, and `RALLY_AGENT_SLUG` already exist or can exist as env inputs.
  - `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"` already exists as the shared note front door.

- Duplicate or drifting paths relevant to this change:
  - `flows/poem_loop/prompts/shared/inputs.prompt` still defines a local `issue.md` input instead of inheriting the shared issue ledger.
  - generic note behavior lives in the shared stdlib, but there is no matching shared memory contract yet.
  - `src/rally/services/event_log.py` is an unused event writer while the live runtime already uses `src/rally/services/run_events.py`.

- Capability-first opportunities before new tooling:
  - add the shared issue-ledger input to the stdlib instead of teaching each flow to locate the issue ledger differently
  - add shared read-order and memory document structures in Doctrine instead of encoding those rules only in Python or only in skill prose
  - reuse the compiled agent slug and existing env injection instead of inventing a new scope resolver

- Behavior-preservation signals already available:
  - `tests/unit/test_flow_build.py` — protects the Doctrine emit path for Rally flows.
  - `tests/unit/test_flow_loader.py` — protects compiled agent loading and final-output contract loading.
  - `tests/unit/test_launcher.py` — protects `RALLY_AGENT_SLUG` env injection.
  - `tests/unit/test_issue_ledger.py` — protects trusted issue append behavior and snapshots.
  - `tests/unit/test_run_events.py` and `tests/unit/test_runner.py` — protect the live event and runner paths.
  - `tests/unit/domain/test_turn_result_contracts.py` — protects the final JSON control boundary.

## 3.3 Decision gaps that must be resolved before implementation

- No user blocker question remains.
- The main plan-shaping choices are now locked:
  - the shared issue-ledger input lives in `stdlib/rally/prompts/rally/issue_ledger.prompt`
  - the shared memory contract lives in a new `stdlib/rally/prompts/rally/memory.prompt`
  - `stdlib/rally/prompts/rally/base_agent.prompt` inherits the issue ledger, the current agent slug, shared read-order fields, and the `rally-memory` skill
  - the compiled Doctrine agent slug is the source of truth and `RALLY_AGENT_SLUG` is its runtime mirror
  - one shared repo-local QMD store lives under `runs/memory/qmd/` with one collection per flow-agent scope
  - `memory search` is discovery only, while `memory use` and `memory save` are the visible trusted actions
  - `poem_loop` must converge onto the shared issue-ledger contract and stop carrying a generic local issue input
- No unresolved plan-shaping decisions remain in this artifact.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Shared Rally prompt source lives under `stdlib/rally/prompts/rally/`.
  - `base_agent.prompt` defines Rally-managed env inputs, the required `rally-kernel` skill, and the shared note output.
  - `issue_ledger.prompt` defines the issue-ledger append target.
  - `notes.prompt` maps the shared note output onto that target.
  - there is no shared memory prompt module yet.
- Shared Rally skills live under `skills/`.
  - `rally-kernel` exists.
  - `rally-memory` does not exist yet.
- Runtime seams live under `src/rally/services/` and `src/rally/adapters/`.
  - `home_materializer.py` prepares `home/issue.md`, syncs compiled agents, and materializes mandatory skills.
  - `flow_loader.py` loads compiled agents and flow agent metadata.
  - `launcher.py` builds the Codex env.
  - `issue_ledger.py` and `run_events.py` are already real runtime surfaces.
  - there are no `memory_store.py` or `memory_index.py` services yet.
- `runs/` exists, but there is no checked-in cross-run memory root under it yet.
- `flows/poem_loop` still carries a local issue-ledger input and custom note structures as flow-local prompt source.

## 4.2 Control paths (runtime)

- Rally startup already requires a non-empty `home/issue.md`.
- Rally-managed agents already get:
  - `RALLY_WORKSPACE_DIR`
  - `RALLY_CLI_BIN`
  - `RALLY_RUN_ID`
  - `RALLY_FLOW_CODE`
  - `RALLY_AGENT_SLUG`
  - the ambient `rally-kernel` skill
  - one final JSON control path through `rally.turn_results`
- The shared prompt contract does not yet expose `RALLY_AGENT_SLUG` or the issue ledger to agents.
- One flow (`poem_loop`) works around that gap with its own local issue-ledger input.
- There is no current memory path for:
  - memory discovery
  - memory retrieval as a visible runtime event
  - memory save as a visible runtime event
  - repo-local memory source-file storage
  - QMD index refresh

## 4.3 Object model + key abstractions

- Rally already has:
  - `CompiledAgentContract` with `slug`
  - `FlowAgent` with `slug`
  - strict final-output contract loading
  - run ids, run status, and runner event records
- Rally does not yet model:
  - `MemoryScope`
  - `MemoryEntry`
  - `MemorySearchHit`
  - `MemorySaveOutcome`
  - `MemoryEvent`
- The prompt stdlib already models:
  - shared env inputs
  - shared skill blocks
  - shared note outputs
  - flow-local `document` structures in `poem_loop`
- The prompt stdlib does not yet model:
  - shared issue-ledger input
  - shared memory document shape
  - shared memory read-order blocks

## 4.4 Observability + failure behavior today

- `issue_ledger.py` already appends trusted notes and snapshots the issue log.
- `run_events.py` already writes structured event records and per-agent logs.
- `launcher.py` and `test_launcher.py` already prove that `RALLY_AGENT_SLUG` is injected.
- There are still no:
  - `memory_used` events
  - `memory_saved` events
  - `Memory Used` issue-ledger records
  - `Memory Saved` issue-ledger records
  - repo-local memory files
  - QMD state managed by Rally
- If Rally called raw QMD today, it would still fall back to global paths. That would violate Rally's repo-local rule.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No GUI work is in scope.
- The relevant operator surface is CLI plus run-directory artifacts.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Keep the shared Rally issue-ledger contract in:
  - `stdlib/rally/prompts/rally/issue_ledger.prompt`
- Extend the shared base agent in:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
- Add one shared memory prompt module:
  - `stdlib/rally/prompts/rally/memory.prompt`
- Keep the note-only surface in:
  - `stdlib/rally/prompts/rally/notes.prompt`
- Add one shared memory skill package:
  - `skills/rally-memory/SKILL.md`
- Keep durable memory source files under:
  - `runs/memory/entries/<flow_code>/<agent_slug>/<memory_id>.md`
- Keep one shared Rally-owned QMD state root under:
  - `runs/memory/qmd/index.sqlite`
  - `runs/memory/qmd/config/`
  - `runs/memory/qmd/cache/`
- Add runtime backing under:
  - `src/rally/domain/memory.py`
  - `src/rally/services/memory_store.py`
  - `src/rally/services/memory_index.py`

## 5.2 Control paths (future)

1. Doctrine stdlib owns the shared agent-facing memory contract.
   - `issue_ledger.prompt` defines the shared issue-ledger input and append target.
   - `memory.prompt` defines the shared memory document, the shared memory skill declaration, and the shared read-order and turn-sequence workflow blocks.
   - `base_agent.prompt` imports those pieces and makes them part of the inherited Rally-managed contract.

2. Every Rally-managed agent inherits the shared contract.
   - The issue ledger is always available as a shared input.
   - The current agent slug is always available as a shared env input.
   - `rally-memory` is part of `RallyManagedSkills`.
   - Shared read-order fields tell the agent to read the issue first, check memory when it matters, do the flow-local job, and save a reusable lesson before the turn ends when needed.
   - Flow-local prompts keep their own job logic, artifacts, and review rules. They do not restate the generic memory lifecycle.

3. Rally runtime backs the shared contract.
   - The flow loader and runner keep the compiled Doctrine agent slug as the agent-scope truth.
   - `RALLY_AGENT_SLUG` is a runtime mirror of that compiled slug.
   - The memory CLI resolves current scope from `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, and `RALLY_AGENT_SLUG` by default.

4. `rally memory search` is discovery only.
   - It searches only the current flow-agent collection.
   - It may write low-level runtime telemetry.
   - It does not append to the issue ledger.

5. `rally memory use` is the front door for actual retrieval.
   - It returns the selected memory.
   - It records a `memory_used` runtime event.
   - It appends a normalized `Memory Used` record into `home/issue.md`.

6. `rally memory save` is the front door for durable learning.
   - It accepts memory content that matches the shared memory document body shape.
   - It writes or updates one markdown memory file.
   - It refreshes only the current flow-agent collection in QMD.
   - It records a `memory_saved` runtime event with `created` or `updated`.
   - It appends a normalized `Memory Saved` record into `home/issue.md`.

7. `rally memory refresh` is the repair path.
   - It rebuilds QMD state from markdown memory files.
   - It never invents semantic truth outside those source files.

8. Routing, `done`, `blocker`, and `sleep` still come only from the final JSON result.

## 5.3 Object model + abstractions (future)

- Shared Doctrine contract
  - `RallyIssueLedger` input
    - required file input for `home/issue.md`
  - `RallyAgentSlug` input
    - env input for `RALLY_AGENT_SLUG`
    - documented as the runtime mirror of the compiled agent slug
  - `RallyMemorySkill`
    - shared skill declaration for `rally-memory`
  - shared read-order fields
    - likely named workflow fields such as `read_first` and `how_to_take_a_turn`
    - these carry the generic memory order in authored form
  - `RallyMemoryEntryDocument`
    - shared document shape for the memory body:
      - `# Lesson`
      - `# When This Matters`
      - `# What To Do`

- Runtime memory objects
  - `MemoryScope`
    - `flow_code`
    - `agent_slug`
  - `MemoryEntry`
    - runtime-managed frontmatter:
      - `id`
      - `flow_code`
      - `agent_slug`
      - `created_at`
      - `updated_at`
      - `source_run_id`
    - body validated against `RallyMemoryEntryDocument`
  - `MemorySearchHit`
    - `memory_id`
    - `path`
    - `title`
    - `snippet`
    - `score`
  - `MemorySaveOutcome`
    - `created`
    - `updated`
  - `MemoryEvent`
    - `kind`
    - `run_id`
    - `flow_code`
    - `agent_slug`
    - `memory_id`
    - `recorded_at`
    - `outcome` for save events

- QMD store contract
  - one shared repo-local store
  - one collection per flow-agent scope
  - one root context per collection that explains the scope in plain language

## 5.4 Invariants and boundaries

- Doctrine owns the shared issue-ledger input, shared memory skill, shared memory body shape, and shared read-order blocks.
- Rally owns memory file writes, memory file updates, QMD configuration, CLI behavior, event records, and issue appends.
- The compiled Doctrine agent slug is the source of truth for agent scope.
- `FlowAgent.slug` and `RALLY_AGENT_SLUG` must reflect that compiled slug, not a parallel meaning.
- `home/issue.md` stays the shared run ledger.
- Flow-local prompts do not carry generic issue-ledger lookup rules once the shared stdlib input exists.
- Flow-local prompts do not carry generic memory timing rules once the shared read-order blocks exist.
- Agents never write memory files directly.
- Agents never call raw QMD directly.
- `search` is discovery only.
- Only `use` and `save` append trusted issue-ledger readback.
- Memory records are context only. They are never route truth.
- No cross-flow or cross-agent memory sharing in v1.
- No fallback paths to global QMD state.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- No GUI work is in scope.
- The relevant future operator surface is CLI plus run-directory artifacts:

```text
rally memory search --run-id POM-7 --query "tighten the next revision"
  1. mem_pom_poem_critic_revision_guard
     Ask for one concrete revision target before you ask for a full rewrite.

rally memory use --run-id POM-7 mem_pom_poem_critic_revision_guard
  -> returns the selected memory
  -> logs memory_used
  -> appends "Memory Used" to home/issue.md

rally memory save --run-id POM-7 <<'EOF'
# Lesson
When a draft misses the mark, give one concrete revision target before you ask for a rewrite.

# When This Matters
Use this after a weak draft, a vague critique, or any case where the writer needs a clearer next step.

# What To Do
Write the memory, then hand off with normal final JSON.
EOF
  -> writes or updates one markdown memory file
  -> refreshes the scoped QMD collection
  -> logs memory_saved(created|updated)
  -> appends "Memory Saved" to home/issue.md
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)
| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Shared issue contract | `stdlib/rally/prompts/rally/issue_ledger.prompt` | shared issue target only | defines append target only; no shared file input | add shared `RallyIssueLedger` file input for `home/issue.md` and keep the append target here | the shared issue ledger must be native to the stdlib, not flow-local | shared issue-ledger input and target contract | readback inspection, flow build tests |
| Shared base agent | `stdlib/rally/prompts/rally/base_agent.prompt` | `RallyManagedInputs`, `RallyManagedSkills`, `RallyManagedBaseAgent` | exposes base dir, run id, flow code, note output, and `rally-kernel` only | import issue-ledger and memory modules; add `RallyAgentSlug`; inherit the shared issue ledger; add shared read-order fields; add `rally-memory` to `RallyManagedSkills` | the shared Rally contract must carry the generic memory lifecycle | Rally-managed shared issue, slug, skill, and read-order contract | readback inspection |
| Shared memory contract | `stdlib/rally/prompts/rally/memory.prompt` | new module | missing | add `RallyMemorySkill`, `RallyMemoryEntryDocument`, and shared read-order / turn-sequence workflow fields | memory shape and timing should live in Doctrine source | shared memory prompt contract | flow build tests, readback inspection |
| Shared note path | `stdlib/rally/prompts/rally/notes.prompt` | `RallyIssueNote` | note-only append output | keep note-only role explicit and point to the memory split when helpful | notes and memory must not collapse together | note-only shared output contract | readback inspection |
| Shared memory skill | `skills/rally-memory/SKILL.md` | new skill package | missing | add the thin shared skill that teaches `search`, `use`, `save`, and `refresh` through Rally CLI | the skill should reinforce the shared authored contract, not replace it | `rally-memory` skill contract | skill/readback inspection |
| Shared kernel skill | `skills/rally-kernel/SKILL.md` | note guidance | teaches note path and final JSON | clarify that notes are run-local and cross-run memory belongs to `rally-memory` | keeps note and memory boundaries explicit | note-only contract | skill inspection |
| Flow-local proof input | `flows/poem_loop/prompts/shared/inputs.prompt` | `IssueLedger` | defines a local `issue.md` input | remove the generic local issue-ledger input and inherit the shared stdlib input instead | avoid a second generic ledger story | shared issue-ledger contract adoption | compile/readback inspection |
| Flow-local proof prose | `flows/poem_loop/prompts/shared/contracts.prompt` and `flows/poem_loop/prompts/AGENTS.prompt` | issue-ledger and primary-path prose | still talks about `issue.md` as the shared ledger | update to `home/issue.md` and the inherited shared issue contract | keep the flow proof aligned with Rally truth | synced flow prompt contract | compile/readback inspection |
| Flow readback | `flows/_stdlib_smoke/build/**` and `flows/poem_loop/build/**` | compiled agents | current readback does not show shared memory contract | rebuild after stdlib changes and inspect representative agents | readback must tell the truth about the shared contract | rebuilt compiled readback | `tests/unit/test_flow_build.py` plus readback inspection |
| Flow loader | `src/rally/services/flow_loader.py` | slug loading | derives `FlowAgent.slug` from flow key, then validates against compiled artifacts | tighten the loader so the compiled contract slug is treated as the carried source of truth after validation | runtime scope should follow Doctrine identity, not a second long-lived derivation | compiled-slug-backed flow-agent identity contract | `tests/unit/test_flow_loader.py` |
| Flow domain | `src/rally/domain/flow.py` | `CompiledAgentContract.slug`, `FlowAgent.slug` | already models agent slug | preserve the compiled slug as the canonical carried identity and document the boundary with small code comments if needed | one source of truth for agent scope | canonical slug contract | `tests/unit/test_flow_loader.py` |
| Launcher | `src/rally/adapters/codex/launcher.py` | `build_codex_launch_env` | already injects `RALLY_AGENT_SLUG` | keep env injection, but treat it as a projection of compiled slug and extend tests around that meaning if needed | no new identity source should appear | runtime slug projection contract | `tests/unit/test_launcher.py` |
| CLI | `src/rally/cli.py` | command surface | only `run` and `resume` are live | add `memory search`, `memory use`, `memory save`, and `memory refresh` | memory must be a first-class Rally surface | memory CLI contract | CLI unit tests |
| Pure domain | `src/rally/domain/memory.py` | new domain contracts | missing | add `MemoryScope`, `MemoryEntry`, `MemorySearchHit`, `MemorySaveOutcome`, and `MemoryEvent` | keep policy out of CLI parsing and file glue | typed memory domain contract | domain unit tests |
| Source-of-truth service | `src/rally/services/memory_store.py` | new service | missing | write and update markdown memory files under `runs/memory/entries/...` and validate body shape against the shared contract | markdown must stay the durable truth | markdown memory store contract | store unit tests |
| QMD wrapper | `src/rally/services/memory_index.py` | new service | missing | own repo-local QMD paths, collection sync, scoped search, use, and refresh | raw QMD defaults violate Rally path rules | repo-local QMD wrapper contract | index unit tests |
| Issue ledger | `src/rally/services/issue_ledger.py` | trusted appends | supports notes and issue edit records | add normalized `Memory Used` and `Memory Saved` append paths | use and save must show up in the shared ledger | memory issue-ledger contract | `tests/unit/test_issue_ledger.py` |
| Runtime events | `src/rally/services/run_events.py` | `RunEventRecorder` | live structured event stream | add `memory_used` and `memory_saved` events here, not in a second event path | memory events should use the same live runtime surface | canonical memory event contract | `tests/unit/test_run_events.py`, `tests/unit/test_runner.py` |
| Stale event path | `src/rally/services/event_log.py` | `append_event` | unused helper writer | delete it or leave it untouched but do not use it for memory; converge memory events onto `run_events.py` | avoid a second event writer path | delete or explicit non-owner status | event-path audit during implementation |
| Home materialization | `src/rally/services/home_materializer.py` | `_MANDATORY_SKILLS` and skill copy path | `rally-kernel` is the only mandatory ambient skill | materialize `rally-memory` as a Rally-managed ambient skill beside `rally-kernel` | memory should be shared Rally behavior, not per-flow allowlist config | ambient skill materialization contract | materializer tests |
| Runner | `src/rally/services/runner.py` | launch and turn orchestration | already carries agent slug through turns and env | keep runner orchestration-only; do not move memory store or QMD logic into it | avoid a god module | orchestration boundary | `tests/unit/test_runner.py` |
| Live docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` | memory, ledger, CLI truth | do not yet describe the Doctrine-first memory split | sync these docs when memory ships | keep live docs aligned with shipped truth | live docs sync | docs review |

## 6.2 Migration notes

* Canonical owner path / shared code path:
  - shared issue-ledger contract: `stdlib/rally/prompts/rally/issue_ledger.prompt`
  - shared Rally-managed base contract: `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared memory contract: `stdlib/rally/prompts/rally/memory.prompt`
  - shared note-only contract: `stdlib/rally/prompts/rally/notes.prompt`
  - user-facing memory guidance: `skills/rally-memory/SKILL.md`
  - front-door commands: `src/rally/cli.py`
  - durable markdown truth: `src/rally/services/memory_store.py`
  - repo-local QMD wrapper: `src/rally/services/memory_index.py`
  - trusted issue readback: `src/rally/services/issue_ledger.py`
  - canonical runtime events: `src/rally/services/run_events.py`

* Deprecated APIs (if any):
  - none yet; this is future-state design

* Delete list (what must be removed; include superseded shims/parallel paths if any):
  - the flow-local generic `IssueLedger` input in `flows/poem_loop/prompts/shared/inputs.prompt`
  - any future flow-local generic memory timing prose once the shared stdlib memory contract exists
  - any direct raw `qmd` invocation from prompts or skills
  - any direct agent write path to durable memory markdown files
  - any attempt to treat `RALLY_AGENT_SLUG` as a second identity source unrelated to the compiled contract slug
  - the unused `src/rally/services/event_log.py` path if memory work would otherwise bless it as a second event writer

* Capability-replacing harnesses to delete or justify:
  - do not add retrieval wrappers, parser sidecars, fuzzy memory selectors, or synthetic memory orchestrators that replace agent judgment

* Live docs/comments/instructions to update or delete:
  - sync `docs/RALLY_MASTER_DESIGN_2026-04-12.md` when memory ships
  - sync `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` when issue-ledger and event surfaces change
  - sync `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` when the memory CLI and visible readback land
  - rebuild compiled readback for `_stdlib_smoke` and `poem_loop`
  - add only small high-leverage code comments at the canonical boundaries where future drift would be costly

* Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_build.py` must keep proving Rally compiles flows through Doctrine
  - `tests/unit/test_flow_loader.py` must keep proving compiled agent contracts and final-output contracts load correctly
  - `tests/unit/test_launcher.py` must keep proving `RALLY_AGENT_SLUG` env injection
  - `tests/unit/test_issue_ledger.py` must keep proving trusted issue append behavior
  - `tests/unit/test_run_events.py` and `tests/unit/test_runner.py` must keep proving the live runtime event path
  - `tests/unit/domain/test_turn_result_contracts.py` must keep proving final JSON remains the only turn-ending control surface

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)
| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared issue ledger | `stdlib/rally/prompts/rally/issue_ledger.prompt`, `flows/poem_loop/prompts/shared/inputs.prompt` | one inherited shared issue-ledger input | prevents each flow from teaching a different shared ledger path | include |
| Shared read order | `stdlib/rally/prompts/rally/base_agent.prompt`, new `stdlib/rally/prompts/rally/memory.prompt` | shared read-first and turn-sequence workflow fields | keeps generic memory timing out of flow-local prose | include |
| Shared skills | `stdlib/rally/prompts/rally/base_agent.prompt`, `skills/rally-kernel/`, new `skills/rally-memory/`, `src/rally/services/home_materializer.py` | Rally-managed ambient skills declared in stdlib and materialized by Rally | prevents flow-local allowlist drift and hidden runtime behavior | include |
| Shared document shapes | new `stdlib/rally/prompts/rally/memory.prompt`, `flows/poem_loop/prompts/shared/outputs.prompt` | author durable markdown shapes in Doctrine `document` blocks | prevents runtime-only format rules | include |
| Agent identity | `src/rally/domain/flow.py`, `src/rally/services/flow_loader.py`, `src/rally/adapters/codex/launcher.py` | compiled contract slug as source of truth, env as projection | prevents a second identity meaning from growing in runtime code | include |
| Runtime events | `src/rally/services/run_events.py`, `src/rally/services/event_log.py` | one canonical live event path | prevents memory from blessing a second event writer | include |
| Future shared memory | any later cross-flow or cross-agent memory feature | broader scope or promoted memory | this is new product behavior, not required for v1 | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks or runtime shims. The system must work correctly or fail loudly. The authoritative checklist names the chosen work only. It does not hold unresolved branches or "if needed" placeholders.

## Phase 1 - Land the shared Doctrine memory contract

Goal
- Make the agent-facing memory model native to the shared Rally stdlib before any runtime memory backing is treated as complete.

Work
- Extend `stdlib/rally/prompts/rally/issue_ledger.prompt` with the shared issue-ledger input for `home/issue.md`.
- Add `stdlib/rally/prompts/rally/memory.prompt` with:
  - `RallyMemorySkill`
  - `RallyMemoryEntryDocument`
  - shared read-first and turn-sequence workflow fields
- Extend `stdlib/rally/prompts/rally/base_agent.prompt` so every Rally-managed agent inherits:
  - the shared issue-ledger input
  - `RALLY_AGENT_SLUG`
  - the shared memory skill
  - the shared read-order fields
- Update `skills/rally-kernel/SKILL.md` to keep notes and memory separate.
- Add `skills/rally-memory/SKILL.md` as the thin shared front-door skill.
- Converge `poem_loop` away from its local generic issue-ledger input and onto the shared stdlib contract.
- Rebuild `_stdlib_smoke` and `poem_loop` after the prompt changes.

Verification (required proof)
- Recompile the affected flows with the paired Doctrine compiler.
- Inspect representative readback for:
  - inherited issue-ledger input
  - inherited `RALLY_AGENT_SLUG`
  - visible `rally-memory` guidance
  - shared read-order fields
  - unchanged final JSON control rules
- Keep `tests/unit/test_flow_build.py` and `tests/unit/domain/test_turn_result_contracts.py` green.

Docs/comments (propagation; only if needed)
- Add one small code comment at the shared memory prompt boundary only if the authored contract would otherwise be easy to bypass later.

Exit criteria
- The shared Rally stdlib, not flow-local prompts, owns the generic memory contract.
- Compiled readback shows the shared contract honestly.
- No flow still carries its own generic issue-ledger input.

Rollback
- Revert the shared stdlib memory contract together if the change would leave a mix of shared and flow-local generic memory rules alive.

## Phase 2 - Land the runtime data plane and scope truth

Goal
- Back the shared authored memory contract with one repo-local runtime path and one clear identity path.

Work
- Add `src/rally/domain/memory.py` with the memory domain contracts.
- Add `src/rally/services/memory_store.py` so markdown files under `runs/memory/entries/<flow_code>/<agent_slug>/` become the durable truth.
- Add `src/rally/services/memory_index.py` so Rally owns:
  - forced repo-local QMD paths
  - one shared store under `runs/memory/qmd/`
  - one collection per flow-agent scope
  - scoped search, retrieval, and refresh behavior
- Extend `src/rally/cli.py` with `memory search`, `memory use`, `memory save`, and `memory refresh`.
- Tighten `src/rally/services/flow_loader.py` so the runtime carries the compiled Doctrine slug as the source-of-truth agent identity after validation.
- Keep `src/rally/adapters/codex/launcher.py` as the env projection layer, not a second identity source.

Verification (required proof)
- Add focused unit tests for:
  - repo-local QMD path forcing
  - memory file write and update behavior
  - scope resolution by flow plus compiled agent slug
  - `memory save` created-versus-updated outcomes
- Keep `tests/unit/test_launcher.py` and `tests/unit/test_flow_loader.py` green.
- Run one CLI-level proof that a scoped memory can be saved, searched, used, and refreshed without touching global QMD paths.

Docs/comments (propagation; only if needed)
- Add one small code comment in `memory_store.py` that markdown is the only durable memory truth.
- Add one small code comment in `flow_loader.py` or `launcher.py` if needed to mark the compiled slug as the source of truth.

Exit criteria
- Rally has one working repo-local memory store and one working repo-local QMD wrapper.
- The runtime carries one agent-scope truth.
- Memory CLI exists and works through Rally-owned services only.

Rollback
- Revert the data-plane changes together if they require global QMD state, direct agent file writes, or a second agent identity meaning to work.

## Phase 3 - Wire visibility and ambient runtime behavior

Goal
- Make real memory actions visible on Rally-owned surfaces and materialize the shared memory skill the same way Rally already materializes `rally-kernel`.

Work
- Extend `src/rally/services/issue_ledger.py` with normalized `Memory Used` and `Memory Saved` append paths.
- Extend `src/rally/services/run_events.py` with `memory_used` and `memory_saved` runtime events.
- Keep `memory search` out of the issue ledger.
- Extend `src/rally/services/home_materializer.py` so `rally-memory` is materialized as a Rally-managed ambient skill.
- Delete `src/rally/services/event_log.py` if it would otherwise remain as a stale parallel event path.
- Keep `src/rally/services/runner.py` orchestration-only. Do not move store or QMD logic into it.

Verification (required proof)
- Add focused unit tests for:
  - `Memory Used` issue append formatting
  - `Memory Saved` issue append formatting
  - `memory_used` and `memory_saved` event payloads
  - ambient `rally-memory` materialization
- Add one CLI-level proof that `memory search` stays out of the issue ledger while `memory use` and `memory save` land there.
- Keep `tests/unit/test_issue_ledger.py`, `tests/unit/test_run_events.py`, and `tests/unit/test_runner.py` green.

Docs/comments (propagation; only if needed)
- Add one small code comment in `issue_ledger.py` marking memory readback as trusted runtime readback, not instruction text.

Exit criteria
- Memory use and save are first-class visible Rally events.
- The issue ledger records only actual use and save actions.
- `rally-memory` is materialized like other Rally-managed ambient behavior.

Rollback
- Revert the visibility wiring together if memory actions can happen without visible Rally-owned records or if search starts polluting the issue ledger.

## Phase 4 - Prove one flow and sync live truth

Goal
- Finish with one believable end-to-end proof and one truthful repo-wide story about built-in memory.

Work
- Add one narrow Rally proof for `poem_loop` that covers:
  - scoped memory save
  - later scoped memory retrieval
  - visible `memory_used` and `memory_saved` records
  - unchanged note and final-result control behavior
- Rebuild the affected flows and inspect representative readback again.
- Sync live docs that would otherwise drift:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- Delete any remaining flow-local generic memory path, raw QMD prompt usage, or stale event path that survived earlier phases.

Verification (required proof)
- Run the existing contract tests plus the new memory unit coverage.
- Recompile `_stdlib_smoke` and `poem_loop`, then inspect representative readback.
- Run one narrow real-flow proof that memory recall and learning work without changing routing, `done`, `blocker`, or `sleep` truth.

Docs/comments (propagation; only if needed)
- Delete stale live wording instead of preserving old memory explanations beside the shipped design.

Exit criteria
- The acceptance evidence in Section 0.4 is materially satisfied.
- One real Rally flow proves the memory model end to end.
- Shared prompt source, runtime surfaces, compiled readback, and live docs all tell the same story.

Rollback
- Preserve failed run artifacts for archaeology and revert any half-cut memory path that leaves hidden state, mixed issue semantics, or stale live docs behind.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Keep the proof set small and real. Prefer existing signals before adding new ones.

## 8.1 Unit tests (contracts)

- Keep `tests/unit/test_flow_build.py` green so Rally still rebuilds flows through Doctrine.
- Keep `tests/unit/test_flow_loader.py` green so compiled agent contracts and slug handling stay strict.
- Keep `tests/unit/test_launcher.py` green so `RALLY_AGENT_SLUG` stays projected into the adapter env.
- Keep `tests/unit/test_issue_ledger.py` green so trusted issue appends and snapshots stay correct.
- Keep `tests/unit/test_run_events.py` and `tests/unit/test_runner.py` green so the live runtime event path stays canonical.
- Add small tests for repo-local QMD path forcing, memory file write and update rules, and memory scope resolution.
- Add small tests for `memory_used` / `memory_saved` payloads and issue-ledger formatting.

## 8.2 Integration tests (flows)

- Recompile `_stdlib_smoke` and `poem_loop` and inspect representative generated agents for the shared memory contract.
- Add one narrow Rally integration check that proves memory lookup and save do not change note or routing behavior.
- Add one narrow Rally integration check that proves `memory search` stays out of the issue ledger while `memory use` and `memory save` land there through the front door.

## 8.3 E2E / device tests (realistic)

- Keep E2E scope small in v1.
- One believable real-flow proof is enough if it covers save, later retrieval, and visible runtime records.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land the shared authored contract before treating runtime memory as complete.
- Roll out the runtime backing behind Rally-owned CLI and issue/event paths only.
- Prove the feature on one Rally flow before widening it.
- Fail loud while the feature is still narrow.

## 9.2 Telemetry changes

- Record `memory_used` and `memory_saved` through `RunEventRecorder`.
- Keep low-level search telemetry out of the issue ledger.
- Append normalized `Memory Used` and `Memory Saved` records into `home/issue.md` for real use and save actions only.
- Keep telemetry about visible behavior and ownership, not about hidden scoring tricks.

## 9.3 Operational runbook

- Rebuild QMD state from markdown files if the index drifts or is cleared.
- Repair memory through Rally CLI, not by hand-editing QMD state.
- If the shared skill or shared stdlib contract drifts from runtime behavior, fix the shared contract first and then sync runtime backing. Do not paper over the gap with hidden prompt injection.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self cold read 1, self cold read 2, self integrator
- Scope checked:
  - frontmatter, `planning_passes`, `# TL;DR`, `# 0)` through `# 10)`, and helper blocks
  - cross-section agreement on Doctrine-versus-Rally ownership, agent slug truth, issue-ledger ownership, event path ownership, command surface, phase order, and verification burden
- Findings summary:
  - the old artifact still treated memory as mostly runtime behavior instead of a shared authored contract
  - the old artifact still described `RALLY_AGENT_SLUG` as if it were a new identity source even though runtime injection already exists
  - the old artifact missed the current `home/issue.md` runtime truth and the flow-local `poem_loop` drift
  - the old artifact pointed memory events at a stale placeholder path instead of the live runtime event path
- Integrated repairs:
  - rewrote TL;DR, Section 0, and Section 1 around a Doctrine-first memory contract
  - rewrote Section 3 to anchor the plan in the current shared stdlib, current runtime slug injection, current issue-ledger runtime, and current flow-local drift
  - reran the deep-dive in Sections 4 through 6 around the new owner split and current code truth
  - updated Section 7, Section 8, Section 9, and Section 10 so the new architecture and phase order stay aligned
- Remaining inconsistencies:
  - none found
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
- The user wants built-in Rally memory that uses QMD.
- Rally forbids hidden global state and prefers filesystem truth.

Decision
- Keep markdown memory files as the durable truth.
- Use QMD only as the search layer.

Consequences
- Rally needs explicit repo-local QMD paths.
- Rally needs a clean memory file contract.

## 2026-04-13 - Make memory use and save first-class visible runtime records

Context
- The user wants memory retrieval and storage to be fully visible in Rally's CLI and issue ledger.

Decision
- Treat `memory use` and `memory save` as first-class visible runtime actions.
- Append normalized issue records for those actions through Rally-owned front-door paths.

Consequences
- Rally needs clear runtime events and issue-ledger record shapes for those actions.

## 2026-04-13 - Use one shared repo-local QMD store with one collection per flow-agent scope

Context
- The user wants memory to stay per flow and per agent in v1.
- QMD already supports collections as a native scope boundary.

Decision
- Use one shared QMD store under `runs/memory/qmd/`.
- Use one collection per flow-agent scope.
- Keep markdown source files under `runs/memory/entries/<flow_code>/<agent_slug>/`.

Consequences
- Rally keeps one index and one model-cache root.
- Scope filtering stays native to QMD instead of becoming a Rally-side search shim.

## 2026-04-13 - Keep search as discovery and make use and save the visible front doors

Context
- The user wants memory actions that matter to be visible, but the issue ledger should not fill up with tentative search traffic.

Decision
- Keep `rally memory search` as discovery only.
- Treat `rally memory use` and `rally memory save` as the visible trusted actions.

Consequences
- The issue ledger stays focused on memory that actually shaped the turn.

## 2026-04-13 - Put the agent-facing memory contract in Doctrine stdlib first

Context
- The current Rally stdlib already owns inherited env inputs, skills, and note behavior.
- One flow already proves Doctrine can express structured issue-ledger and note shapes.
- A runtime-only memory design would leave memory feeling custom and would invite per-flow drift.

Decision
- Put the shared issue-ledger input, shared memory skill, shared memory entry document, and shared read-order blocks into Doctrine stdlib.
- Keep Rally runtime responsible for backing that contract, not inventing a second agent-facing one.

Consequences
- Shared prompt source becomes the place where agents learn when memory belongs in the turn.
- Flow-local prompts should stop carrying generic memory rules.

## 2026-04-13 - Treat the compiled Doctrine agent slug as the source of truth

Context
- Compiled `AGENTS.contract.json` files already carry the concrete agent slug.
- Rally runtime already injects `RALLY_AGENT_SLUG`.

Decision
- Treat the compiled Doctrine agent slug as the source-of-truth identity for memory scope.
- Treat `RALLY_AGENT_SLUG` as the runtime mirror of that slug, not as a second meaning.

Consequences
- Loader and launcher behavior must preserve that single-source-of-truth rule.
- Memory scope will stay aligned with compiled prompt output.

## 2026-04-13 - Sequence the rollout as shared contract, then runtime backing, then proof

Context
- The user asked for a more Doctrine-native and less custom design.
- Prompt and runtime sides both matter, but the shared authored contract should decide the shape first.

Decision
- Sequence the work as:
  - shared authored contract
  - runtime data plane and scope truth
  - visibility and ambient behavior
  - one narrow flow proof plus live-doc sync

Consequences
- The phase plan starts with the shared stdlib contract instead of a runtime-only memory implementation.
- The deep-dive and call-site audit now treat flow-local generic ledger and memory patterns as drift to remove.
