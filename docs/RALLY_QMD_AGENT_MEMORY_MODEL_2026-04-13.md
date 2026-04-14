---
title: "Rally - QMD Agent Memory Model - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: new_system
related:
  - README.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - skills/rally-kernel/prompts/SKILL.prompt
  - flows/poem_loop/prompts/shared/inputs.prompt
  - flows/software_engineering_demo/prompts/shared/inputs.prompt
  - flows/poem_loop/prompts/shared/outputs.prompt
  - src/rally/domain/flow.py
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/framework_assets.py
  - src/rally/services/home_materializer.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/run_events.py
  - src/rally/services/skill_bundles.py
  - src/rally/adapters/codex/launcher.py
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
- Two live flows already carry their own local issue-ledger inputs and note structures. That proves Doctrine can express the shape, but it also shows how memory would drift if Rally adds it as runtime-only behavior.
- QMD is a good fit for search, but its raw CLI and MCP defaults still write under `~/.cache/qmd/` unless Rally forces a repo-local cache root.
- Rally is Python and QMD is Node, so the runtime needs one pinned bridge path instead of ambient `qmd` installs or raw CLI calls.

Approach
- Put the agent-facing memory contract in Doctrine source first.
- Make Rally runtime back that contract with repo-local storage, QMD indexing, CLI commands, and visible event/readback paths.
- Reuse the compiled Doctrine agent slug as the only agent-scope truth and project that same slug into `RALLY_AGENT_SLUG` for runtime use.
- Converge flow-local issue-ledger and generic memory patterns back into the shared stdlib instead of letting each flow tell its own memory story.

Plan
- Lock the North Star and owner split around Doctrine-first memory.
- Keep the QMD dependency pinned to a small repo-owned Node bridge that uses `@tobilu/qmd` `v2.1.0`.
- Add the shared stdlib pieces: issue-ledger input, memory document, shared skill, and shared read-order blocks.
- Update the built-in skill emit and sync path so `rally-memory` is treated like `rally-kernel`.
- Land the runtime backing, then visibility, then one narrow flow proof, then sync live docs.

Non-negotiables
- Doctrine owns the agent-facing memory contract.
- Rally owns storage, indexing, CLI behavior, issue appends, and runtime events.
- The compiled Doctrine agent slug is the source of truth for agent scope.
- Markdown memory files are the source of truth. QMD is only a rebuildable search index.
- No hidden memory prose outside the declared `.prompt` graph.
- No per-flow generic memory lifecycle rules once the shared stdlib contract exists.
- Memory never carries routing, `done`, `blocker`, or `sleep` truth.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-13
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit checked the full approved Phase 4 frontier against the live `POM-1` run artifacts, current memory code and tests, synced docs, current generated readback, and a fresh `uv run pytest tests/unit -q` pass.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None. The fresh audit confirmed the previously reopened Phase 4 frontier is now closed:
  - `runs/active/POM-1/home/issue.md` shows `Memory Saved` on turn 7, `Memory Used` on turn 9, the normal writer notes, the normal handoff JSON, and `done` on turn 10
  - `runs/active/POM-1/logs/events.jsonl` shows `memory_saved` and `memory_used` on the canonical event stream while search stays out of visible memory events
  - `runs/active/POM-1/state.yaml` ends at `status: done`
  - `runs/memory/entries/POM/poem_writer/mem_pom_poem_writer_when_a_poem_critique_asks_for_one_stronger_image.md` is the durable markdown truth
  - `src/rally/services/memory_index.py` plus `tests/unit/test_memory_index.py` now cover noisy bridge stdout and virtual `qmd:/...` search hits
  - `uv run rally memory search --run-id POM-1 --agent-slug poem_writer --query 'stronger image or ending for poem critique'` now prints the canonical memory id, title, and short snippet
  - `uv run pytest tests/unit -q` passed fresh at `159 passed in 1.29s`

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
deep_dive_pass_2: done 2026-04-13
external_research_grounding: done 2026-04-13
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

## 0.0 Implementation Status (current repo truth)

This section is the current truth for the repo after the implementation pass.
Sections 2, 4, and 6 below keep the implementation-start audit snapshot so the design trail stays readable.

What is shipped now:
- shared memory contract in `stdlib/rally/prompts/rally/memory.prompt`
- shared issue-ledger input and `RALLY_AGENT_SLUG` exposure in the shared base agent
- built-in `rally-memory` skill source plus emitted readback beside `rally-kernel`
- built-in skill wiring through `skill_bundles.py`, `flow_build.py`, `framework_assets.py`, and `workspace.py`
- repo-local markdown memory truth under `runs/memory/entries/<flow_code>/<agent_slug>/`
- repo-local QMD state under `runs/memory/qmd/index.sqlite` and `runs/memory/qmd/cache/`
- pinned Node bridge under `tools/qmd_bridge/` on `@tobilu/qmd` `2.1.0`
- Rally CLI front doors for `memory search`, `memory use`, `memory save`, and `memory refresh`
- visible `Memory Used` and `Memory Saved` issue-ledger records
- visible `memory_used` and `memory_saved` runtime events
- compiled-slug-backed memory scope carried through `flow_loader.py`
- deletion of the stale `src/rally/services/event_log.py` path

Proof already captured:
- rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
- focused test sweep covering flow build, framework assets, flow loading, CLI, issue ledger, run events, runner, and the new memory services
- full unit suite at current head
- one bridge smoke proof that kept `~/.cache/qmd/` untouched on an empty scoped refresh
- one real `POM-1` `poem_loop` proof that saved memory on turn 7, searched and used it on turn 9, and still ended `done` on turn 10
- current `rally memory search` output that shows the canonical memory id, lesson title, and short snippet
- fresh audit rerun with `uv run pytest tests/unit -q` still green at `159 passed in 1.29s`

Fresh audit check:
- the authoritative Implementation Audit block above has now been rerun against the full approved frontier
- no approved code frontier remains open for this plan

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

This section states the target rules the implementation is checked against.
See Section 0.0 for the current shipped state.

## 0.2 In scope

- one built-in Rally memory model for cross-run learning
- the design trail and implementation ledger for that model
- one shared stdlib issue-ledger input for all Rally-managed agents
- one shared stdlib memory module, likely `stdlib/rally/prompts/rally/memory.prompt`
- one shared memory skill in the Rally-managed skill set
- one shared memory entry document shape authored in Doctrine
- one shared read-order and turn-sequence contract authored in Doctrine
- exposing `RALLY_AGENT_SLUG` to prompts as the runtime projection of the compiled agent slug
- repo-local markdown memory files under `runs/`
- repo-local QMD index and cache roots under `runs/`
- Rally CLI memory commands for search, use, save, and refresh
- visible `memory_used` and `memory_saved` runtime records
- normalized `Memory Used` and `Memory Saved` issue-ledger records
- convergence work needed to remove flow-local generic issue-ledger and memory patterns once the shared stdlib contract exists
- docs and readback updates needed to keep the repo truthful

## 0.3 Out of scope

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
- the built-in skill pipeline emits and syncs `rally-memory` beside `rally-kernel`
- compiled readback for `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` shows the shared issue-ledger and memory contract honestly
- the QMD wrapper is grounded against one real pinned dependency path, not a missing local checkout
- the runtime saves memory under repo-local markdown paths and forces QMD state to stay repo-local
- memory scope resolves by flow plus compiled agent slug
- one narrow real-flow proof shows a relevant memory can be found, used, and saved without changing note or routing semantics
- `memory_used` and `memory_saved` show up in Rally logs and append trusted readback into `home/issue.md`
- the master design, runtime design docs, shared prompt source, and compiled readback all say the same thing about notes, memory, and turn control

Current status in this pass:
- every acceptance item above is now landed in code and backed by current proof
- the narrow live-flow memory proof, docs sync, and visibility checks are all closed on the shipped path

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
- `stdlib/rally/prompts/rally/base_agent.prompt` already owns the shared Rally-managed input and skill surface, but today it only exposes three env vars and `rally-kernel` even though the runtime already sets more Rally env vars.
- `stdlib/rally/prompts/rally/issue_ledger.prompt` and `stdlib/rally/prompts/rally/notes.prompt` already own the issue-append target shape, but they still do not own a shared issue file input.
- `src/rally/domain/flow.py`, `src/rally/services/flow_loader.py`, and the compiled `AGENTS.contract.json` files already carry the concrete agent slug.
- `src/rally/adapters/codex/launcher.py` already injects `RALLY_AGENT_SLUG` and `RALLY_TURN_NUMBER`; the shared prompt contract does not use them yet.
- `src/rally/services/runner.py` and `src/rally/services/home_materializer.py` already pass helper env vars such as `RALLY_AGENT_KEY`, `RALLY_ISSUE_PATH`, `RALLY_RUN_HOME`, and `RALLY_FLOW_HOME` to prompt-input and setup commands.
- `flows/poem_loop` and `flows/software_engineering_demo` already prove Doctrine can express structured issue-ledger inputs, but both patterns are still flow-local.
- `src/rally/services/skill_bundles.py`, `src/rally/services/flow_build.py`, `src/rally/services/framework_assets.py`, and `src/rally/services/home_materializer.py` already define how Rally built-in skills are emitted, synced, and materialized, but only `rally-kernel` is wired today.
- The repo no longer carries `for_reference_only/qmd/`, so the old QMD path claims are not grounded locally anymore.
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

# 2) Problem Statement (implementation-start state + why change)

## 2.1 What exists today

- Rally's master design already points toward built-in memory as a later step.
- The shared base agent already gives all Rally-managed agents a small inherited contract.
- The shared note path already exists through the issue-ledger target and `rally-kernel`.
- Rally runtime already prepares `home/issue.md` and already injects `RALLY_AGENT_SLUG` into Codex launches.
- Compiled Doctrine contracts already include the concrete agent slug.
- `poem_loop` and `software_engineering_demo` already use local `issue.md` inputs as the shared ledger input.
- `README.md` still points at QMD as the target search layer for future memory.
- The old local `for_reference_only/qmd/` checkout is no longer present in this repo.

## 2.2 What’s broken / missing (concrete)

- There is still no cross-run memory surface.
- The shared stdlib does not yet expose the issue ledger to every Rally-managed agent.
- The shared stdlib does not yet expose the current agent slug to prompts.
- The shared stdlib does not yet define a memory entry shape, a shared memory skill, or a shared memory read order.
- Two live flows still carry their own generic issue-ledger inputs instead of inheriting that from the stdlib.
- The built-in skill pipeline does not yet know about `rally-memory`.
- There is no Rally-owned CLI for memory search, use, save, and refresh.
- There is no repo-local QMD contract yet.
- There is no pinned repo-owned QMD bridge yet, so Rally still has no clean way to call the QMD SDK from Python.
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

- `README.md` — keeps the product-level claim that Rally memory should use markdown files plus QMD search.
- QMD's official `v2.1.0` README says the SDK `createStore()` path requires an explicit `dbPath`, supports inline config or `configPath`, and supports collection add, search, update, and embed calls. That is the clean embed seam for Rally.
- QMD's official README says the CLI and MCP defaults still use `~/.cache/qmd/` for the index, model cache, and daemon PID path. QMD's latest `v2.1.0` release also says model cache now respects `XDG_CACHE_HOME`.
- npm's official `npm ci` docs say installs stay frozen to `package-lock.json`. That fits a small repo-owned Node bridge better than floating `npx` installs.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — says Rally is Doctrine-native, filesystem-first, and that `home/issue.md` is the shared run ledger.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — is the current shared base contract for inherited inputs and skills.
  - `stdlib/rally/prompts/rally/issue_ledger.prompt` — already owns the issue-ledger append target shape.
  - `stdlib/rally/prompts/rally/notes.prompt` — already maps shared note output onto the issue-ledger append target.
  - `src/rally/services/flow_build.py` — already emits Doctrine flow docs and built-in Doctrine skills through the workspace toolchain.
  - `src/rally/services/framework_assets.py` — already syncs reserved framework-owned built-ins into external workspaces.
  - `src/rally/services/home_materializer.py` — already enforces `home/issue.md` and already materializes mandatory ambient skills.
  - `src/rally/services/skill_bundles.py` — already defines the built-in skill list and skill source kinds.
  - `src/rally/domain/flow.py` and `src/rally/services/flow_loader.py` — already model flow agents, compiled agents, and agent slugs.
  - `src/rally/adapters/codex/launcher.py` — already injects `RALLY_AGENT_SLUG`.
  - `flows/poem_loop/prompts/shared/inputs.prompt`, `flows/software_engineering_demo/prompts/shared/inputs.prompt`, and `flows/poem_loop/prompts/shared/outputs.prompt` — already prove that Doctrine can carry structured issue-ledger inputs and structured note documents.

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
  - `skills/rally-kernel/prompts/SKILL.prompt` — should stay the note-only boundary.
  - new `skills/rally-memory/prompts/SKILL.prompt` — should teach the front-door memory commands and when to use them.

- Native model or agent capabilities to lean on:
  - Rally-managed agents already know how to read shared file inputs, follow ordered readable workflow fields, use shared skills, and end turns with strict final JSON.
  - The useful model behavior here is still judgment: choose whether a found memory matters and whether a learned lesson is worth saving.

- Existing grounding / tool / file exposure:
  - `home/issue.md` already exists as the shared run ledger in the runtime.
  - `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and `RALLY_TURN_NUMBER` already exist for launched agents.
  - `RALLY_AGENT_KEY`, `RALLY_ISSUE_PATH`, `RALLY_RUN_HOME`, and `RALLY_FLOW_HOME` already exist for prompt-input and setup helper commands.
  - `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"` already exists as the shared note front door.

- Duplicate or drifting paths relevant to this change:
  - `flows/poem_loop/prompts/shared/inputs.prompt` still defines a local `issue.md` input instead of inheriting the shared issue ledger.
  - `flows/software_engineering_demo/prompts/shared/inputs.prompt` does the same thing for a second live flow.
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

None. The locked QMD seam now lives in the external research block below.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:external_research:start -->
# External Research (best-in-class references; plan-adjacent)

> Goal: anchor the plan in idiomatic, broadly accepted practices where applicable. This section intentionally avoids project-specific internals.

## Topics researched (and why)
- QMD embed seam — Rally is Python, QMD is Node, and the plan needed one clean way to pin and call QMD without inheriting raw CLI defaults.
- Repo-local cache and model state — Rally forbids hidden home-dir state, so the plan needed a sourced cache-root rule.
- Collection scoping and rebuild path — the plan wants one shared store, per-flow-agent scope, and markdown files as the durable truth.

## Findings + how we apply them

### QMD embed seam
- Best practices (synthesized):
  - Use the QMD SDK when another app owns the runtime. The official README shows `createStore()` with explicit `dbPath`, inline config, `configPath`, and DB-only reopen.
  - Keep the bridge small. Let the host app own policy, paths, and commands.
- Adopt for this plan:
  - Pin QMD to `@tobilu/qmd` `v2.1.0`.
  - Add a tiny repo-owned Node bridge at `tools/qmd_bridge/package.json`, `tools/qmd_bridge/package-lock.json`, and `tools/qmd_bridge/main.mjs`.
  - Have `src/rally/services/memory_index.py` call that bridge, not raw `qmd` CLI or QMD MCP.
- Reject for this plan:
  - Do not make raw `qmd` CLI calls the main runtime seam.
  - Do not run the QMD MCP daemon inside Rally as the memory backend.
  - Do not rely on floating `npx` installs at runtime.
- Pitfalls / footguns:
  - Raw CLI defaults still assume `~/.cache/qmd/index.sqlite`.
  - `qmd mcp --http --daemon` writes its PID under `~/.cache/qmd/`.
  - Floating installs hide the exact package version Rally is using.
- Sources:
  - QMD README `v2.1.0` — https://github.com/tobi/qmd/blob/v2.1.0/README.md — official SDK and CLI guidance from the project
  - QMD Releases `v2.1.0` — https://github.com/tobi/qmd/releases/tag/v2.1.0 — latest release on April 5, 2026, with path-related fixes
  - npm `npm ci` docs — https://docs.npmjs.com/cli/v8/commands/npm-ci/ — official frozen-install guidance for lockfile-based Node workspaces

### Repo-local cache and model state
- Best practices (synthesized):
  - QMD's CLI defaults place the index and model cache under `~/.cache/qmd/`.
  - QMD honors `XDG_CACHE_HOME`, and the latest release calls out a fix so model cache now follows that setting too.
  - Apps that forbid hidden home-dir state should force the cache root on every call, not only in docs.
- Adopt for this plan:
  - Force `XDG_CACHE_HOME` to `runs/memory/qmd/cache` for every bridge call.
  - Set SDK `dbPath` to `runs/memory/qmd/index.sqlite`.
  - Treat "no new writes under `~/.cache/qmd/`" as a required proof for the first runtime pass.
- Reject for this plan:
  - Do not rely on default cache roots.
  - Do not keep a second QMD cache or model root under the operator's home directory.
  - Do not keep a separate Rally-owned QMD config directory when inline SDK config is enough.
- Pitfalls / footguns:
  - First use downloads models from HuggingFace, so the first proof needs network and enough disk.
  - Missing `XDG_CACHE_HOME` on any bridge call sends QMD back to home-dir cache defaults.
- Sources:
  - QMD README `v2.1.0` — https://github.com/tobi/qmd/blob/v2.1.0/README.md — official default paths, model cache notes, and env var support
  - QMD Releases `v2.1.0` — https://github.com/tobi/qmd/releases/tag/v2.1.0 — latest release note that model cache now respects `XDG_CACHE_HOME`

### Collection scoping and rebuild path
- Best practices (synthesized):
  - QMD already supports multi-collection stores, scoped search, collection updates, and DB reopen.
  - When source files live on disk, the index should be treated as rebuildable from those files.
  - Scope should stay native to the retrieval tool when the tool already has collections.
- Adopt for this plan:
  - Keep one DB at `runs/memory/qmd/index.sqlite`.
  - Use one collection per `flow_code` plus compiled `agent_slug`.
  - Keep markdown truth under `runs/memory/entries/<flow_code>/<agent_slug>/`.
  - Make `rally memory refresh` rebuild QMD state from those markdown files.
- Reject for this plan:
  - Do not create one separate QMD DB per run or per agent.
  - Do not add a Rally-side search shim that re-implements collection scope in Python.
- Pitfalls / footguns:
  - Model changes can force re-embed work, so v1 should keep one fixed model choice.
  - Search and refresh calls should always pass the scoped collection list, not rely on default collections.
- Sources:
  - QMD README `v2.1.0` — https://github.com/tobi/qmd/blob/v2.1.0/README.md — official SDK collection, search, update, and reopen behavior

## Adopt / Reject summary
- Adopt:
  - a repo-owned Node bridge with a lockfile-backed `@tobilu/qmd` `v2.1.0` dependency
  - SDK `createStore()` with explicit `dbPath` and inline config
  - forced `XDG_CACHE_HOME` under `runs/memory/qmd/cache`
  - one shared DB plus one collection per flow-agent scope
- Reject:
  - raw CLI or MCP daemon as Rally's core QMD seam
  - home-dir cache defaults
  - a separate QMD config directory in Rally's runtime layout
  - floating runtime installs with no lockfile

## Decision gaps that must be resolved before implementation
- None.
<!-- arch_skill:block:external_research:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (implementation-start snapshot)

This section keeps the repo snapshot from when the work started.
Use Section 0.0, the phase status blocks, and the worklog for the current shipped state.

## 4.1 On-disk structure

- Shared Rally prompt source lives under `stdlib/rally/prompts/rally/`.
  - `base_agent.prompt` defines Rally-managed env inputs, the required `rally-kernel` skill, and the shared note output.
  - `issue_ledger.prompt` defines the issue-ledger append target.
  - `notes.prompt` maps the shared note output onto that target.
  - there is no shared memory prompt module yet.
- Shared Rally skills live under `skills/`.
  - `rally-kernel` source lives in `skills/rally-kernel/prompts/SKILL.prompt`.
  - `rally-memory` does not exist yet.
- Runtime seams live under `src/rally/services/` and `src/rally/adapters/`.
  - `flow_build.py`, `framework_assets.py`, and `skill_bundles.py` already define how built-in skills are emitted, synced, and treated as mandatory.
  - `home_materializer.py` prepares `home/issue.md`, syncs compiled agents, and materializes mandatory skills.
  - `flow_loader.py` loads compiled agents and flow agent metadata.
  - `launcher.py` builds the Codex env.
  - `issue_ledger.py` and `run_events.py` are already real runtime surfaces.
  - there are no `memory_store.py` or `memory_index.py` services yet.
- There is no repo-owned Node bridge for QMD yet.
- `runs/` exists, but there is no checked-in cross-run memory root under it yet.
- There is no local QMD reference tree in the repo anymore.
- `flows/poem_loop` and `flows/software_engineering_demo` still carry local issue-ledger inputs as flow-local prompt source.

## 4.2 Control paths (runtime)

- Rally startup already requires a non-empty `home/issue.md`.
- Rally-managed agents already get:
  - `RALLY_WORKSPACE_DIR`
  - `RALLY_CLI_BIN`
  - `RALLY_RUN_ID`
  - `RALLY_FLOW_CODE`
  - `RALLY_AGENT_SLUG`
  - `RALLY_TURN_NUMBER`
  - the ambient `rally-kernel` skill
  - one final JSON control path through `rally.turn_results`
- Prompt-input commands and setup scripts already get `RALLY_AGENT_KEY`, `RALLY_ISSUE_PATH`, `RALLY_RUN_HOME`, and `RALLY_FLOW_HOME`.
- The shared prompt contract does not yet expose `RALLY_AGENT_SLUG` or the issue ledger to agents.
- Two flows (`poem_loop` and `software_engineering_demo`) work around that gap with their own local issue-ledger inputs.
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
  - `skills/rally-memory/prompts/SKILL.prompt`
  - emitted readback at `skills/rally-memory/build/SKILL.md`
- Wire the built-in skill pipeline through:
  - `src/rally/services/skill_bundles.py`
  - `src/rally/services/flow_build.py`
  - `src/rally/services/framework_assets.py`
- Keep durable memory source files under:
  - `runs/memory/entries/<flow_code>/<agent_slug>/<memory_id>.md`
  - this shared root sits beside `runs/active/` and `runs/archive/`
- Add one small repo-owned QMD bridge workspace under:
  - `tools/qmd_bridge/package.json`
  - `tools/qmd_bridge/package-lock.json`
  - `tools/qmd_bridge/main.mjs`
- Keep one shared Rally-owned QMD state root under:
  - `runs/memory/qmd/index.sqlite`
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
   - `src/rally/services/memory_index.py` talks only to the pinned Node bridge, which opens QMD through SDK `createStore()` with explicit `dbPath` and forced `XDG_CACHE_HOME`.

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
    - required file input for run-home-relative `issue.md`
    - maps to the runtime ledger at `home/issue.md`
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
- Python code never shells to ambient `qmd`, `npx`, or QMD MCP. It only talks to the pinned repo-owned bridge.
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
# 6) Call-Site Audit (implementation-start inventory)

## 6.1 Change map (table)
| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Shared issue contract | `stdlib/rally/prompts/rally/issue_ledger.prompt` | shared issue target only | defines append target only; no shared file input | add shared `RallyIssueLedger` file input for run-home-relative `issue.md` and keep the append target here | the shared issue ledger must be native to the stdlib, not flow-local | shared issue-ledger input and target contract | readback inspection, flow build tests |
| Shared base agent | `stdlib/rally/prompts/rally/base_agent.prompt` | `RallyManagedInputs`, `RallyManagedSkills`, `RallyManagedBaseAgent` | exposes base dir, run id, flow code, note output, and `rally-kernel` only | import issue-ledger and memory modules; add `RallyAgentSlug`; inherit the shared issue ledger; add shared read-order fields; add `rally-memory` to `RallyManagedSkills` | the shared Rally contract must carry the generic memory lifecycle | Rally-managed shared issue, slug, skill, and read-order contract | readback inspection |
| Shared memory contract | `stdlib/rally/prompts/rally/memory.prompt` | new module | missing | add `RallyMemorySkill`, `RallyMemoryEntryDocument`, and shared read-order / turn-sequence workflow fields | memory shape and timing should live in Doctrine source | shared memory prompt contract | flow build tests, readback inspection |
| Shared note path | `stdlib/rally/prompts/rally/notes.prompt` | `RallyIssueNote` | note-only append output | keep note-only role explicit and point to the memory split when helpful | notes and memory must not collapse together | note-only shared output contract | readback inspection |
| Shared memory skill | `skills/rally-memory/prompts/SKILL.prompt` | new Doctrine skill package | missing | add the thin shared skill that teaches `search`, `use`, `save`, and `refresh` through Rally CLI | the skill should reinforce the shared authored contract, not replace it | `rally-memory` skill contract | skill/readback inspection, flow build tests |
| Shared kernel skill | `skills/rally-kernel/prompts/SKILL.prompt` | note guidance | teaches note path and final JSON | clarify that notes are run-local and cross-run memory belongs to `rally-memory` | keeps note and memory boundaries explicit | note-only contract | skill inspection |
| Built-in skill pipeline | `src/rally/services/skill_bundles.py`, `src/rally/services/flow_build.py`, `src/rally/services/framework_assets.py`, `src/rally/services/workspace.py` | built-in skill list, emit path, framework sync, workspace copy | the built-in path only knows about `rally-kernel` today | register, emit, sync, and materialize `rally-memory` as a Rally built-in beside `rally-kernel` | memory should be shared Rally behavior, not a per-flow allowlist detail | built-in `rally-memory` lifecycle contract | `tests/unit/test_flow_build.py`, `tests/unit/test_framework_assets.py`, `tests/unit/test_runner.py` |
| Flow-local generic ledger inputs | `flows/poem_loop/prompts/shared/inputs.prompt`, `flows/software_engineering_demo/prompts/shared/inputs.prompt` | `IssueLedger` | both flows define local `issue.md` inputs | remove the generic local issue-ledger inputs and inherit the shared stdlib input instead | avoid a second generic ledger story | shared issue-ledger contract adoption | compile/readback inspection |
| Flow-local ledger prose | `flows/poem_loop/prompts/**`, `flows/software_engineering_demo/prompts/**` | issue-ledger wording | flow prose still carries some generic ledger explanation | keep `issue.md` as the run-home-relative prompt path, but move the generic ledger contract into stdlib and leave only flow-local meaning in the flows | keep flow prose aligned with Rally truth | synced flow prompt contract | compile/readback inspection |
| Flow readback | `flows/_stdlib_smoke/build/**`, `flows/poem_loop/build/**`, and `flows/software_engineering_demo/build/**` | compiled agents | current readback does not show shared memory contract | rebuild after stdlib changes and inspect representative agents | readback must tell the truth about the shared contract | rebuilt compiled readback | `tests/unit/test_flow_build.py` plus readback inspection |
| Flow loader | `src/rally/services/flow_loader.py` | slug loading | derives `FlowAgent.slug` from flow key, then validates against compiled artifacts | tighten the loader so the compiled contract slug is treated as the carried source of truth after validation | runtime scope should follow Doctrine identity, not a second long-lived derivation | compiled-slug-backed flow-agent identity contract | `tests/unit/test_flow_loader.py` |
| Flow domain | `src/rally/domain/flow.py` | `CompiledAgentContract.slug`, `FlowAgent.slug` | already models agent slug | preserve the compiled slug as the canonical carried identity and document the boundary with small code comments if needed | one source of truth for agent scope | canonical slug contract | `tests/unit/test_flow_loader.py` |
| Launcher | `src/rally/adapters/codex/launcher.py` | `build_codex_launch_env` | already injects `RALLY_AGENT_SLUG` | keep env injection, but treat it as a projection of compiled slug and extend tests around that meaning if needed | no new identity source should appear | runtime slug projection contract | `tests/unit/test_launcher.py` |
| CLI | `src/rally/cli.py` | command surface | only `run` and `resume` are live | add `memory search`, `memory use`, `memory save`, and `memory refresh` | memory must be a first-class Rally surface | memory CLI contract | CLI unit tests |
| Pure domain | `src/rally/domain/memory.py` | new domain contracts | missing | add `MemoryScope`, `MemoryEntry`, `MemorySearchHit`, `MemorySaveOutcome`, and `MemoryEvent` | keep policy out of CLI parsing and file glue | typed memory domain contract | domain unit tests |
| Source-of-truth service | `src/rally/services/memory_store.py` | new service | missing | write and update markdown memory files under `runs/memory/entries/...` and validate body shape against the shared contract | markdown must stay the durable truth | markdown memory store contract | store unit tests |
| QMD bridge workspace | `tools/qmd_bridge/package.json`, `tools/qmd_bridge/package-lock.json`, `tools/qmd_bridge/main.mjs` | pinned Node bridge | missing | pin `@tobilu/qmd` `v2.1.0`, open QMD through SDK `createStore()`, and expose a tiny bridge API to Python | Rally is Python and QMD is Node; the SDK avoids raw CLI defaults and keeps the seam explicit | pinned QMD bridge contract | bridge smoke proof |
| QMD wrapper | `src/rally/services/memory_index.py` | new service | missing | force `XDG_CACHE_HOME`, pass explicit `dbPath`, call the repo-owned bridge, and own collection sync plus scoped search, use, and refresh | raw QMD defaults violate Rally path rules and Python cannot import the Node SDK directly | repo-local QMD wrapper contract | index unit tests |
| Issue ledger | `src/rally/services/issue_ledger.py` | trusted appends | supports notes and issue edit records | add normalized `Memory Used` and `Memory Saved` append paths | use and save must show up in the shared ledger | memory issue-ledger contract | `tests/unit/test_issue_ledger.py` |
| Runtime events | `src/rally/services/run_events.py` | `RunEventRecorder` | live structured event stream | add `memory_used` and `memory_saved` events here, not in a second event path | memory events should use the same live runtime surface | canonical memory event contract | `tests/unit/test_run_events.py`, `tests/unit/test_runner.py` |
| Stale event path | `src/rally/services/event_log.py` | `append_event` | unused helper writer | delete it or leave it untouched but do not use it for memory; converge memory events onto `run_events.py` | avoid a second event writer path | delete or explicit non-owner status | event-path audit during implementation |
| Runner | `src/rally/services/runner.py` | launch and turn orchestration | already carries agent slug through turns and env | keep runner orchestration-only; do not move memory store or QMD logic into it | avoid a god module | orchestration boundary | `tests/unit/test_runner.py` |
| Live docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` | memory, ledger, CLI truth | do not yet describe the Doctrine-first memory split | sync these docs when memory ships | keep live docs aligned with shipped truth | live docs sync | docs review |

## 6.2 Migration notes

* Canonical owner path / shared code path:
  - shared issue-ledger contract: `stdlib/rally/prompts/rally/issue_ledger.prompt`
  - shared Rally-managed base contract: `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared memory contract: `stdlib/rally/prompts/rally/memory.prompt`
  - shared note-only contract: `stdlib/rally/prompts/rally/notes.prompt`
  - user-facing memory guidance: `skills/rally-memory/prompts/SKILL.prompt`
  - built-in skill pipeline: `src/rally/services/skill_bundles.py`, `src/rally/services/flow_build.py`, `src/rally/services/framework_assets.py`, and `src/rally/services/workspace.py`
  - front-door commands: `src/rally/cli.py`
  - durable markdown truth: `src/rally/services/memory_store.py`
  - pinned QMD bridge: `tools/qmd_bridge/package.json`, `tools/qmd_bridge/package-lock.json`, and `tools/qmd_bridge/main.mjs`
  - repo-local QMD wrapper: `src/rally/services/memory_index.py`
  - trusted issue readback: `src/rally/services/issue_ledger.py`
  - canonical runtime events: `src/rally/services/run_events.py`

* Deprecated APIs (if any):
  - none yet; this is future-state design

* Delete list (what must be removed; include superseded shims/parallel paths if any):
  - the flow-local generic `IssueLedger` inputs in `flows/poem_loop/prompts/shared/inputs.prompt` and `flows/software_engineering_demo/prompts/shared/inputs.prompt`
  - any future flow-local generic memory timing prose once the shared stdlib memory contract exists
  - any direct raw `qmd` invocation from prompts or skills
  - any floating `npx @tobilu/qmd` runtime path with no pinned lockfile
  - any direct agent write path to durable memory markdown files
  - any attempt to treat `RALLY_AGENT_SLUG` as a second identity source unrelated to the compiled contract slug
  - the unused `src/rally/services/event_log.py` path if memory work would otherwise bless it as a second event writer

* Capability-replacing harnesses to delete or justify:
  - do not add retrieval wrappers, parser sidecars, fuzzy memory selectors, or synthetic memory orchestrators that replace agent judgment

* Live docs/comments/instructions to update or delete:
  - sync `docs/RALLY_MASTER_DESIGN_2026-04-12.md` when memory ships
  - sync `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` when issue-ledger and event surfaces change
  - sync `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` when the memory CLI and visible readback land
  - rebuild compiled readback for `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
  - add only small high-leverage code comments at the canonical boundaries where future drift would be costly

* Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_build.py` must keep proving Rally compiles flows through Doctrine
  - `tests/unit/test_framework_assets.py` must keep proving framework-owned built-ins stay synchronized
  - `tests/unit/test_flow_loader.py` must keep proving compiled agent contracts and final-output contracts load correctly
  - `tests/unit/test_launcher.py` must keep proving `RALLY_AGENT_SLUG` env injection
  - `tests/unit/test_cli.py` must keep proving the CLI surface stays small and explicit
  - `tests/unit/test_issue_ledger.py` must keep proving trusted issue append behavior
  - `tests/unit/test_run_events.py` and `tests/unit/test_runner.py` must keep proving the live runtime event path
  - `tests/unit/domain/test_turn_result_contracts.py` must keep proving final JSON remains the only turn-ending control surface

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)
| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared issue ledger | `stdlib/rally/prompts/rally/issue_ledger.prompt`, `flows/poem_loop/prompts/shared/inputs.prompt`, `flows/software_engineering_demo/prompts/shared/inputs.prompt` | one inherited shared issue-ledger input | prevents each flow from teaching a different shared ledger path | include |
| Shared read order | `stdlib/rally/prompts/rally/base_agent.prompt`, new `stdlib/rally/prompts/rally/memory.prompt` | shared read-first and turn-sequence workflow fields | keeps generic memory timing out of flow-local prose | include |
| Shared skills | `stdlib/rally/prompts/rally/base_agent.prompt`, `skills/rally-kernel/`, new `skills/rally-memory/`, `src/rally/services/skill_bundles.py`, `src/rally/services/flow_build.py`, `src/rally/services/framework_assets.py`, `src/rally/services/workspace.py` | Rally-managed ambient skills declared in stdlib and wired through the built-in skill pipeline | prevents flow-local allowlist drift and hidden runtime behavior | include |
| Shared document shapes | new `stdlib/rally/prompts/rally/memory.prompt`, `flows/poem_loop/prompts/shared/outputs.prompt` | author durable markdown shapes in Doctrine `document` blocks | prevents runtime-only format rules | include |
| Agent identity | `src/rally/domain/flow.py`, `src/rally/services/flow_loader.py`, `src/rally/adapters/codex/launcher.py` | compiled contract slug as source of truth, env as projection | prevents a second identity meaning from growing in runtime code | include |
| Runtime events | `src/rally/services/run_events.py`, `src/rally/services/event_log.py` | one canonical live event path | prevents memory from blessing a second event writer | include |
| Future shared memory | any later cross-flow or cross-agent memory feature | broader scope or promoted memory | this is new product behavior, not required for v1 | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks or runtime shims. The system must work correctly or fail loudly. The authoritative checklist names the chosen work only. It does not hold unresolved branches or "if needed" placeholders.

## Phase 1 - Land the shared Doctrine memory contract

Status
- COMPLETE

Completed work
- Added `stdlib/rally/prompts/rally/memory.prompt`.
- Extended the shared base agent with the shared issue-ledger input, `RALLY_AGENT_SLUG`, shared read-order fields, and `rally-memory`.
- Added `skills/rally-memory/prompts/SKILL.prompt`.
- Updated `skills/rally-kernel/prompts/SKILL.prompt` to keep notes run-local and memory cross-run.
- Converged `poem_loop` and `software_engineering_demo` off local generic issue-ledger inputs.
- Wired `rally-memory` through the built-in skill path and rebuilt the affected flow and skill readback.

Proof captured
- `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` rebuild/readback
- `tests/unit/test_flow_build.py`
- `tests/unit/test_framework_assets.py`
- `tests/unit/test_runner.py`

Goal
- Make the agent-facing memory model native to the shared Rally stdlib before any runtime memory backing is treated as complete.

Work
- Extend `stdlib/rally/prompts/rally/issue_ledger.prompt` with the shared issue-ledger input for run-home-relative `issue.md`.
- Add `stdlib/rally/prompts/rally/memory.prompt` with:
  - `RallyMemorySkill`
  - `RallyMemoryEntryDocument`
  - shared read-first and turn-sequence workflow fields
- Extend `stdlib/rally/prompts/rally/base_agent.prompt` so every Rally-managed agent inherits:
  - the shared issue-ledger input
  - `RALLY_AGENT_SLUG`
  - the shared memory skill
  - the shared read-order fields
- Update `skills/rally-kernel/prompts/SKILL.prompt` to keep notes and memory separate.
- Add `skills/rally-memory/prompts/SKILL.prompt` as the thin shared front-door skill.
- Register `rally-memory` through the built-in skill path in `skill_bundles.py`, `flow_build.py`, `framework_assets.py`, and `workspace.py`.
- Converge `poem_loop` and `software_engineering_demo` away from their local generic issue-ledger inputs and onto the shared stdlib contract.
- Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` after the prompt changes.

Verification (required proof)
- Recompile the affected flows with the paired Doctrine compiler.
- Inspect representative readback for:
  - inherited issue-ledger input
  - inherited `RALLY_AGENT_SLUG`
  - visible `rally-memory` guidance
  - shared read-order fields
  - unchanged final JSON control rules
- Keep `tests/unit/test_flow_build.py`, `tests/unit/test_framework_assets.py`, and `tests/unit/domain/test_turn_result_contracts.py` green.

Docs/comments (propagation; only if needed)
- Add one small code comment at the shared memory prompt boundary only if the authored contract would otherwise be easy to bypass later.

Exit criteria
- The shared Rally stdlib, not flow-local prompts, owns the generic memory contract.
- Compiled readback shows the shared contract honestly.
- No live flow still carries its own generic issue-ledger input.
- `rally-memory` is wired through the same built-in skill path that already carries `rally-kernel`.

Rollback
- Revert the shared stdlib memory contract together if the change would leave a mix of shared and flow-local generic memory rules alive.

## Phase 2 - Land the runtime data plane and scope truth

Status
- COMPLETE

Completed work
- Added `src/rally/domain/memory.py`, `src/rally/services/memory_store.py`, `src/rally/services/memory_index.py`, and `src/rally/services/memory_runtime.py`.
- Added the pinned QMD bridge workspace at `tools/qmd_bridge/`.
- Extended `src/rally/cli.py` with `memory search`, `memory use`, `memory save`, and `memory refresh`.
- Tightened `src/rally/services/flow_loader.py` so the compiled slug is the carried source of truth after validation.

Proof captured
- `tests/unit/test_memory_store.py`
- `tests/unit/test_memory_index.py`
- `tests/unit/test_memory_runtime.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_flow_loader.py`
- `tests/unit/test_launcher.py`
- bridge smoke proof with repo-local `XDG_CACHE_HOME`

Goal
- Back the shared authored memory contract with one repo-local runtime path and one clear identity path.

Work
- Add `src/rally/domain/memory.py` with the memory domain contracts.
- Add `src/rally/services/memory_store.py` so markdown files under `runs/memory/entries/<flow_code>/<agent_slug>/` become the durable truth.
- Add `tools/qmd_bridge/package.json`, `tools/qmd_bridge/package-lock.json`, and `tools/qmd_bridge/main.mjs` as a tiny repo-owned bridge pinned to `@tobilu/qmd` `v2.1.0`.
- Add `src/rally/services/memory_index.py` so Rally owns:
  - forced repo-local QMD paths
  - explicit SDK `dbPath`
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
- Run one bridge smoke proof with `XDG_CACHE_HOME="$PWD/runs/memory/qmd/cache"` and the pinned Node workspace, then confirm `~/.cache/qmd/` stays untouched.
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

Status
- COMPLETE

Completed work
- Extended `src/rally/services/issue_ledger.py` with normalized `Memory Used` and `Memory Saved` append paths.
- Extended `src/rally/services/run_events.py` with `memory_used` and `memory_saved`.
- Kept `memory search` out of the issue ledger.
- Deleted the stale `src/rally/services/event_log.py` path.

Proof captured
- `tests/unit/test_issue_ledger.py`
- `tests/unit/test_run_events.py`
- `tests/unit/test_runner.py`
- CLI and memory-runtime tests that prove search leaves the issue ledger alone while use/save append visible records

Goal
- Make real memory actions visible on Rally-owned surfaces.

Work
- Extend `src/rally/services/issue_ledger.py` with normalized `Memory Used` and `Memory Saved` append paths.
- Extend `src/rally/services/run_events.py` with `memory_used` and `memory_saved` runtime events.
- Keep `memory search` out of the issue ledger.
- Delete `src/rally/services/event_log.py` if it would otherwise remain as a stale parallel event path.
- Keep `src/rally/services/runner.py` orchestration-only. Do not move store or QMD logic into it.

Verification (required proof)
- Add focused unit tests for:
  - `Memory Used` issue append formatting
  - `Memory Saved` issue append formatting
  - `memory_used` and `memory_saved` event payloads
- Add one CLI-level proof that `memory search` stays out of the issue ledger while `memory use` and `memory save` land there.
- Keep `tests/unit/test_issue_ledger.py`, `tests/unit/test_run_events.py`, and `tests/unit/test_runner.py` green.

Docs/comments (propagation; only if needed)
- Add one small code comment in `issue_ledger.py` marking memory readback as trusted runtime readback, not instruction text.

Exit criteria
- Memory use and save are first-class visible Rally events.
- The issue ledger records only actual use and save actions.

Rollback
- Revert the visibility wiring together if memory actions can happen without visible Rally-owned records or if search starts polluting the issue ledger.

## Phase 4 - Prove one flow and sync live truth

Status
- COMPLETE

Completed work
- Rebuilt the affected flows and inspected representative readback again.
- Synced the live docs in this pass so the master design, runtime doc, and CLI/logging doc match the shipped memory path.
- Ran the full unit suite and kept the memory-specific proof green.
- Captured the missing real `poem_loop` proof on `POM-1`:
  - turn 7 saved scoped memory through `rally memory save`
  - turn 9 searched that memory and then used it through `rally memory use`
  - `Memory Saved` and `Memory Used` landed in `home/issue.md`
  - `memory_saved` and `memory_used` landed in the canonical event stream
  - the writer still wrote the normal issue note and normal handoff JSON
  - the run still ended `done` on turn 10 after critic acceptance
- Hardened `src/rally/services/memory_index.py` after the live proof exposed two real issues:
  - tolerate noisy bridge stdout by decoding the last JSON object on stdout
  - recover canonical search hit ids and snippets from markdown source files when QMD returns virtual `qmd:/...` paths

Missing (code)
- None.
- Fresh audit on 2026-04-13 confirmed this phase is closed.

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
- Recompile `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`, then inspect representative readback.
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
- Keep `tests/unit/test_framework_assets.py` green so framework-owned built-ins stay synchronized.
- Keep `tests/unit/test_flow_loader.py` green so compiled agent contracts and slug handling stay strict.
- Keep `tests/unit/test_launcher.py` green so `RALLY_AGENT_SLUG` stays projected into the adapter env.
- Keep `tests/unit/test_cli.py` green and add memory CLI coverage.
- Keep `tests/unit/test_issue_ledger.py` green so trusted issue appends and snapshots stay correct.
- Keep `tests/unit/test_run_events.py` and `tests/unit/test_runner.py` green so the live runtime event path stays canonical.
- Add small tests for repo-local QMD path forcing, memory file write and update rules, and memory scope resolution.
- Add small tests for `memory_used` / `memory_saved` payloads and issue-ledger formatting.

## 8.2 Integration tests (flows)

- Recompile `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` and inspect representative generated agents for the shared memory contract.
- Add one narrow Rally integration check that proves memory lookup and save do not change note or routing behavior.
- Add one narrow Rally integration check that proves `memory search` stays out of the issue ledger while `memory use` and `memory save` land there through the front door.

## 8.3 E2E / device tests (realistic)

- Keep E2E scope small in v1.
- One believable real-flow proof is enough if it covers save, later retrieval, and visible runtime records.

## 8.4 Execution proof captured in this pass

- full unit suite:
  - `uv run pytest tests/unit -q`
  - `159 passed in 1.35s`
- focused memory and runtime sweep:
  - `tests/unit/test_memory_store.py`
  - `tests/unit/test_memory_index.py`
  - `tests/unit/test_memory_runtime.py`
  - `tests/unit/test_cli.py`
  - `tests/unit/test_issue_ledger.py`
  - `tests/unit/test_run_events.py`
  - `tests/unit/test_launcher.py`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_flow_build.py`
  - `tests/unit/test_framework_assets.py`
  - `tests/unit/test_runner.py`
- bridge smoke:
  - empty scoped refresh through `node tools/qmd_bridge/main.mjs refresh`
  - result: `{"collections":1,"indexed":0,"updated":0,"unchanged":0,"removed":0,"needsEmbedding":0,"docsProcessed":0,"chunksEmbedded":0,"embedErrors":0}`
  - confirmed no new `~/.cache/qmd/` path was created
- targeted hardening proof after the live flow run:
  - `uv run pytest tests/unit/test_memory_index.py tests/unit/test_memory_runtime.py tests/unit/test_cli.py -q`
  - `27 passed in 0.11s`
  - `uv run rally memory search --run-id POM-1 --agent-slug poem_writer --query 'stronger image or ending for poem critique'`
  - search now prints the canonical memory id plus a short title and short snippet
- real flow proof:
  - `POM-1` used the real `poem_loop` path on Codex
  - turn 7 saved memory
  - turn 9 searched and used that memory
  - turn 10 ended `done`

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Keep the pinned QMD bridge seam fixed from the first runtime pass. Do not reopen the dependency choice unless upstream behavior changes.
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
  - the old artifact missed the second live flow-local issue-ledger path in `software_engineering_demo`
  - the old artifact cited a local QMD checkout that no longer exists in this repo
  - the old artifact used skill source paths that do not match Rally's current Doctrine-first skill pipeline
  - the old artifact pointed memory events at a stale placeholder path instead of the live runtime event path
- Integrated repairs:
  - kept the Doctrine-first memory contract, but replaced the reopened QMD placeholder with a pinned bridge design based on current upstream docs
  - added an external research block with source-backed adopt and reject guidance for the QMD seam, cache root, and collection scope
  - rewrote Section 3, Section 5, and Section 6 so the plan now names the repo-owned Node bridge, explicit `dbPath`, forced `XDG_CACHE_HOME`, and one-DB-per-system layout
  - updated Section 7, Section 8, Section 9, and Section 10 so the phase order no longer waits on a missing grounding pass and instead starts from the locked QMD seam
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

## 2026-04-13 - Pin QMD to a repo-owned Node bridge on `@tobilu/qmd` `v2.1.0`

Context
- The old local `for_reference_only/qmd/*` grounding tree is gone.
- QMD's official `v2.1.0` README says the SDK path needs an explicit `dbPath` and can run with inline config.
- QMD's raw CLI and MCP defaults still write under `~/.cache/qmd/`, which breaks Rally's repo-local rule if Rally uses them as-is.
- GitHub releases show `v2.1.0` is the latest release as of April 5, 2026.

Decision
- Pin QMD through a tiny repo-owned Node bridge at `tools/qmd_bridge/`.
- Commit `package.json` and `package-lock.json`.
- Call the QMD SDK through that bridge, not through raw CLI or MCP.

Consequences
- Rally gets one exact QMD dependency path instead of ambient installs.
- `src/rally/services/memory_index.py` stays small and talks only to the bridge.
- The plan no longer needs a separate pre-implementation grounding phase.

## 2026-04-13 - Force repo-local QMD state with explicit `dbPath` and `XDG_CACHE_HOME`

Context
- QMD's official README says the SDK requires explicit `dbPath`.
- The official README says the CLI defaults store the index in `~/.cache/qmd/index.sqlite` and models in `~/.cache/qmd/models/`.
- The latest release says model cache now respects `XDG_CACHE_HOME`.

Decision
- Set QMD SDK `dbPath` to `runs/memory/qmd/index.sqlite`.
- Force `XDG_CACHE_HOME` to `runs/memory/qmd/cache` on every bridge call.
- Drop the separate `runs/memory/qmd/config/` path from the plan and use inline SDK config in v1.

Consequences
- Rally keeps the index and model cache repo-local.
- The first runtime proof must show that `~/.cache/qmd/` stays untouched.

## 2026-04-13 - Keep built-in memory guidance in Doctrine skill source, not hand-written `SKILL.md`

Context
- Rally's built-in `rally-kernel` skill is authored in `skills/rally-kernel/prompts/SKILL.prompt`.
- Flow build, framework sync, and run-home materialization already follow that built-in skill path.

Decision
- Author `rally-memory` as a Doctrine skill in `skills/rally-memory/prompts/SKILL.prompt`.
- Wire it through the same built-in skill pipeline as `rally-kernel`.

Consequences
- The plan now names the real emit, sync, and runtime copy owners for the new skill.
- The skill path stays consistent with Rally's current source-of-truth rules.

## 2026-04-13 - Keep the shared prompt input path as `issue.md`, not `home/issue.md`

Context
- Rally's runtime ledger lives at `home/issue.md`.
- Flow prompt source already uses run-home-relative `issue.md` file inputs.

Decision
- Keep the shared prompt contract on `issue.md` as the run-home-relative file path.
- Explain in prose that this maps to runtime `home/issue.md`.

Consequences
- The plan now matches current Doctrine file-input usage.
- The shared stdlib can replace flow-local inputs without changing the run-home-relative prompt shape.

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

## 2026-04-13 - Keep `run_events.py` as the only live memory event writer

Context
- Rally already had one real event stream in `src/rally/services/run_events.py`.
- `src/rally/services/event_log.py` was stale and unused.

Decision
- Record `memory_used` and `memory_saved` only through `RunEventRecorder`.
- Delete `src/rally/services/event_log.py` instead of blessing a second path.

Consequences
- Memory visibility now follows the same event path as the rest of the runtime.
- The repo has one less stale runtime surface to explain.

## 2026-04-13 - Let the bridge create the repo-local QMD DB parent path itself

Context
- Rally needs the QMD seam to fail loud, but it should not require hidden setup outside the repo.
- The bridge is the one place that always knows whether it is opening or creating the QMD store.

Decision
- Let `tools/qmd_bridge/main.mjs` create the parent directory for `runs/memory/qmd/index.sqlite` before it opens the store.

Consequences
- The bridge stays self-contained.
- Rally can rebuild repo-local QMD state from a clean checkout without a separate directory-prep step.
