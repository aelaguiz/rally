---
title: "Rally - Multi-File Agent Package Support - Architecture Plan"
date: 2026-04-15
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_PORTING_GUIDE.md
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - ../psflows/pyproject.toml
  - ../psflows/flows/lessons/flow.yaml
  - ../psflows/flows/lessons/prompts/AGENTS.prompt
  - ../psflows/flows/lessons/prompts/shared/routing.prompt
  - ../doctrine/docs/EMIT_GUIDE.md
  - ../doctrine/doctrine/emit_common.py
---

# TL;DR

## Outcome

Rally should support a clean per-agent package shape where one flow agent can
own one local `AGENTS.prompt` and may own one local `SOUL.prompt`, both compile
into the right `build/agents/<slug>/` directory, and the runtime can consume
that package without a giant concrete-owner wrapper file or a Rally-only
`SOUL` side path. One thin flow-facing build handle is allowed when Doctrine
target mode still needs it.

## Problem

The current best effort already preserves `AGENTS.md` and `SOUL.md` in compiled
and run-home agent directories, but the authored shape is still awkward. In
`../psflows`, the lessons flow has small role-local files, yet it still needs a
large `flows/lessons/prompts/AGENTS.prompt` that imports everything and declares
all concrete agents. It also needs naming-only agent stubs in
`shared/routing.prompt`. That is the real readability problem.

## Approach

Treat Doctrine's shipped runtime-package contract as fixed input, and treat
Rally as the runtime and build owner that should stop special-casing `SOUL`.
The target state is:

1. Doctrine already lets the nearest local agent package be the authored source
   of truth through imported runtime packages.
2. Doctrine still lets Rally build one whole flow through one thin front-door
   build handle instead of a per-agent target list.
3. Doctrine already emits one compiler-owned package directory per runtime
   agent, with the right peer files together in one place.
4. Rally consumes those compiler-owned package directories directly.
5. Rally keeps `AGENTS.md` as the formal runtime instruction contract unless a
   separate approved design changes that.
6. `SOUL.md` stays a compiler-owned peer artifact, not a Rally-only hack.

## Plan

1. Lock the plan and proof flow to the shipped Doctrine package contract.
2. Remove Rally-owned peer prompt emission while keeping one flow-facing build
   handle.
3. Remove stale flow metadata and tighten the compiled-package contract.
4. Update Rally docs and tests so the package story is consistent.
5. Prove the final authored and runtime shape on `../psflows/flows/lessons`.

## Non-negotiables

- No giant synthetic flow-level agent file should be required just to make real
  agent packages emit.
- No naming-only concrete agent stubs should survive in the final ideal shape.
- No Rally-only `SOUL` rendering path should survive in the final design.
- No hidden config plane or second package registry should be added to
  `flow.yaml`.
- `AGENTS.md` stays Rally's formal runtime instruction contract unless a later
  approved design changes that on purpose.
- Build and load failures must stay loud.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-15
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None. Fresh proof closed the full approved frontier through Phase 6:
  - `uv run pytest tests/unit/test_flow_build.py tests/unit/test_flow_loader.py tests/unit/test_adapter_mcp_projection.py tests/unit/test_run_store.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py tests/unit/test_bundled_assets.py -q` in Rally passed (`136 passed`).
  - `uv run pytest tests/test_lessons_flow_scaffold.py -q` and `uv run pytest -q` in `../psflows` passed (`1 passed`, `10 passed`).
  - A fresh temporary lessons run proved `materialize_run_home(...)` copies the compiled package into `home/agents/<slug>/` and preserves peer artifacts such as `SOUL.md`.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-15
external_research_grounding: skipped 2026-04-15 (local Doctrine and Rally grounding was enough)
deep_dive_pass_2: done 2026-04-15
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support the clean authored shape the lessons flow wants without
inventing a second runtime doctrine plane:

- each flow agent can live in its own local package directory
- that directory can own `AGENTS.prompt` and optional `SOUL.prompt`
- the flow may keep one thin `AGENTS.prompt` build handle that only imports
  those packages
- Doctrine can emit the package into `build/agents/<slug>/`
- Rally can load and copy that compiler-owned package directly
- the flow no longer needs one giant synthetic `AGENTS.prompt` just to declare
  every concrete emitted agent

This claim is false if any of these remain true in the finished design:

- a real flow still needs one giant flow-level `AGENTS.prompt` only because
  emit roots must be declared there
- Rally still has to render `SOUL.md` itself through a special local side path
- Rally needs a new package registry or hidden sidecar config to map agents to
  packages
- the final authored flow still needs naming-only concrete stubs for real
  owners
- the final runtime truth depends on something other than the compiler-owned
  agent package directory

## 0.2 In scope

- Rally architecture and code needed to consume a compiler-owned per-agent
  package shape
- Rally build, load, run-home sync, docs, and tests that currently assume the
  older flow-level emit story
- the current lessons-flow evidence in `../psflows` that shows where the
  authored shape still feels wrong
- one real-flow adoption proof, using `../psflows/flows/lessons` as the first
  target after Rally package cutover lands
- aligning Rally to Doctrine's shipped thin build-handle and runtime-package
  contract
- keeping Rally's agent key to slug rule simple and front-door

Allowed architectural convergence scope:

- refactor Rally build code so it consumes compiler-owned package directories
  instead of manual `SOUL` sidecars
- refactor Rally docs and tests so they describe one package shape truth
- add or reshape Rally internal types when needed to model a compiled agent
  package clearly

## 0.3 Out of scope

- implementing Doctrine changes in this repo
- widening Rally into a second prompt compiler
- adding a new flow-local registry of package paths in `flow.yaml`
- changing product behavior of existing Rally flows beyond the packaging and
  build contract
- changing `home:issue.md`, turn-result routing, or the current final JSON
  control path
- changing Rally to inject `SOUL.md` as a second formal runtime prompt surface
  in this plan

## 0.4 Definition of done (acceptance evidence)

The finished cross-repo state is done when all of this is true:

- one real flow, starting with `../psflows/flows/lessons`, can author each
  agent under a local package directory that owns `AGENTS.prompt` and optional
  `SOUL.prompt`
- that flow does not need one giant synthetic flow-level `AGENTS.prompt` to
  declare all concrete agents
- Rally build code no longer renders `SOUL.md` through
  `_sync_role_soul_sidecars(...)`
- Rally docs say the compiled agent package directory is the runtime package
  truth
- Rally unit tests prove the package contract and the build or load loud-fail
  behavior
- the emitted package lands under `build/agents/<slug>/` and the run-home copy
  lands under `home/agents/<slug>/`
- `AGENTS.md` remains the formal runtime contract and `SOUL.md` is a
  compiler-owned peer artifact

## 0.5 Key invariants (fix immediately if violated)

- No new hidden config plane.
- No permanent compatibility shim for both the old and new authored truths.
- No manual Rally-owned `SOUL` compiler path in the final design.
- No second runtime instruction contract beyond `AGENTS.md` in this plan.
- No silent fallback from package mode to giant synthetic flow assembly.
- Flow agent keys still map to slugs through one simple rule.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make the authored flow read naturally at the agent-package level.
2. Keep one clean compiler-owned package directory per runtime agent.
3. Avoid new Rally config planes or package registries.
4. Keep the runtime contract explicit and fail loud.
5. Preserve current Rally behavior outside this packaging gap.

## 1.2 Constraints

- Rally today calls `doctrine.emit_docs` once per flow target.
- Rally today keeps `AGENTS.md` as the formal runtime instruction contract.
- `../psflows` already has role-local `AGENTS.prompt` and `SOUL.prompt` files,
  so the missing piece is not "can the source express it at all."
- Doctrine now walks imported runtime packages from a selected build handle, but
  `emit_docs` still requires a configured `AGENTS.prompt` or `SOUL.prompt`
  entrypoint per target.
- The current lessons flow has not adopted that thin build-handle pattern yet.

## 1.3 Architectural principles (rules we will enforce)

- A compiled agent package directory is the unit Rally should consume.
- The compiler owns emitted prompt artifacts. Rally should not quietly act as a
  second prompt emitter for peer files.
- Keep the agent key to slug mapping front-door and simple.
- Keep one front-door Doctrine build call per flow. Rally should not enumerate
  per-agent package targets or own a second target-mapping plane.
- Package completeness errors must fail loud during build or load, not during a
  later agent turn.
- Use Doctrine's shipped package support directly instead of teaching Rally to
  patch around the older compiler gap.

## 1.4 Known tradeoffs (explicit)

- The cleanest authored shape depends more on using Doctrine's shipped contract
  than on adding new Rally logic.
- Rally can improve its build and package contract without widening its runtime
  prompt model.
- Keeping `AGENTS.md` as the formal runtime contract means `SOUL.md` stays a
  peer artifact, not an equal runtime carrier, even in the improved design.
- If Doctrine lands only a partial fix, Rally should not overcompensate with a
  large compatibility layer.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

The lessons flow in `../psflows` already does part of the right thing:

- each lessons role has a local `AGENTS.prompt`
- each lessons role has a local `SOUL.prompt`
- the compiled tree already lands at `build/agents/<slug>/AGENTS.md` and
  `build/agents/<slug>/SOUL.md`
- the run-home copy already preserves both files under `home/agents/<slug>/`

That means the visible runtime directory shape is already close to the ideal.

## 2.2 What’s broken / missing (concrete)

The authored source shape is still wrong in the place that matters most for
readability:

- `../psflows/flows/lessons/prompts/AGENTS.prompt` is still the one big file
  that imports every role file and declares every concrete agent
- that file is much larger than the role-local files it assembles, which is a
  useful signal that concrete-root ownership is sitting in the wrong place
- `../psflows/flows/lessons/prompts/shared/routing.prompt` still has naming-only
  concrete agent stubs just to make route and owner mentions work
- `../psflows/pyproject.toml` still points the `lessons` emit target at one
  flow-level `AGENTS.prompt`
- Rally still renders `SOUL.md` itself after `emit_docs`
- Rally docs still frame `AGENTS.md` as the only formal runtime contract and
  treat other artifacts as sidecars

## 2.3 Constraints implied by the problem

- The fix should attack root ownership and package emission, not just surface
  polish.
- The final design should not make Rally more magical or less explicit.
- The final design should avoid a second registry that maps flow agents to
  package roots.
- Doctrine's shipped package support should remove the need for the giant
  assembler, not ask Rally to simulate package emit locally.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

Doctrine is the framework owner for the authoring and emit side of this change.
For Rally, the main external anchors are Doctrine's shipped docs, tests, and
example corpus:

- `../doctrine/docs/EMIT_GUIDE.md`
  - adopt as the authoritative current emit contract
  - `emit_docs` is target-driven, accepts `AGENTS.prompt` or `SOUL.prompt`,
    and still gives one flow-facing build handle per target
  - imported runtime packages emit package-root `AGENTS.md`, optional sibling
    `SOUL.md`, and bundled peer files
  - `emit_flow` walks the same runtime frontier, so flow proof and docs proof
    stay aligned
- `../doctrine/doctrine/emit_common.py`,
  `../doctrine/tests/test_emit_docs.py`, and
  `../doctrine/tests/test_emit_flow.py`
  - adopt as the authoritative current runtime-frontier behavior
  - `collect_runtime_emit_roots(...)` walks direct roots plus imported runtime
    packages in first-seen order
  - emit tests prove paired package artifact emit and loud failure on bad
    runtime-package shapes
- `../doctrine/examples/115_runtime_agent_packages/**`
  - adopt as the canonical package-contract proof
  - it shows the thin build-handle pattern, optional sibling `SOUL.prompt`, and
    imported route targets without a giant concrete-owner wrapper
- `../doctrine/example_agents/harvested/**`
  - adopt as authoring-shape pressure, not as a direct API contract
  - the harvested corpus keeps pushing toward nearest-scope instruction files
    and package-local ownership, not one giant authored assembly file

## 3.2 Internal ground truth (code as spec)

Authoritative behavior anchors:

- `../psflows/pyproject.toml`
  - the `lessons` emit target still points at
    `flows/lessons/prompts/AGENTS.prompt`
  - this still gives lessons one compiler entrypoint today, but that entrypoint
    can become a thin build handle instead of a giant wrapper
- `../psflows/flows/lessons/prompts/AGENTS.prompt`
  - owns the shared abstract base and declares the emitted lessons agents
  - this is the large authored assembler the user wants to eliminate
- `../psflows/flows/lessons/prompts/shared/routing.prompt`
  - still carries naming-only concrete agent stubs for owner and route mentions
- `../doctrine/doctrine/emit_common.py`
  - `collect_runtime_emit_roots(...)` now walks imported runtime packages and
    requires each package root to define exactly one concrete agent
- `../doctrine/doctrine/emit_docs.py`
  - imported runtime packages emit package-root `AGENTS.md`, optional
    `SOUL.md`, and bundled peers
  - extra `.prompt` files under a runtime package fail loud
- `../doctrine/docs/EMIT_GUIDE.md` and
  `../doctrine/examples/115_runtime_agent_packages/**`
  - show the shipped thin build-handle contract Rally should consume
- `src/rally/services/flow_build.py`
  - `ensure_flow_assets_built(...)` now runs `doctrine.emit_docs` once per
    flow target, prunes retired legacy artifacts, and validates
    compiler-owned package directories without rendering peer prompt files
    itself
- `src/rally/services/flow_loader.py`
  - `_load_compiled_agents(...)` already treats `build/agents/<slug>/` as the
    real compiled package directory
  - `load_flow_definition(...)` now centers flow metadata on
    `build_agents_dir` plus compiled contracts instead of a required
    flow-level prompt-entrypoint field
- `src/rally/domain/flow.py`
  - `flow_agent_key_to_slug(...)` already gives Rally one simple flow-key to
    package-slug rule
- `src/rally/services/home_materializer.py`
  - `_sync_compiled_agents(...)` already copies each compiled agent directory
    into `home/agents/<slug>/` as a full directory, not as one file
- `src/rally/services/runner.py`
  - runtime prompt assembly still injects only `AGENTS.md`
- `docs/RALLY_MASTER_DESIGN.md`
  - Rally already states that only `AGENTS.md` is the formal runtime
    instruction contract, while other emitted files are compiler-owned readback

Canonical path and owner to reuse:

- `../doctrine/doctrine/emit_docs.py` plus `../doctrine/doctrine/emit_common.py`
  - Doctrine already owns package-root emit behavior
- `src/rally/services/flow_build.py`
  - Rally should keep owning build orchestration, but not peer prompt emission
- `src/rally/services/flow_loader.py` and `src/rally/services/home_materializer.py`
  - Rally should keep owning compiled-package validation and run-home package
    sync

Existing patterns to reuse:

- `src/rally/domain/flow.py`
  - keep the current `01_name -> name` flow-agent key to slug rule
- `src/rally/services/home_materializer.py`
  - keep full-directory package copy as the run-home sync path

Prompt surfaces and agent contract to reuse:

- `docs/RALLY_MASTER_DESIGN.md`
  - keep `AGENTS.md` as the one formal runtime instruction contract in this
    plan
- `src/rally/services/runner.py`
  - keep the runtime prompt injection scope unchanged unless a later approved
    design changes the contract on purpose

Existing grounding, tool, and file exposure:

- `home/agents/<slug>/`
  - Rally already preserves peer files in the run home because it copies the
    full compiled package directory
  - that means `AGENTS.md` can still tell the agent to read local peer files
    such as `SOUL.md` without widening Rally's formal runtime contract

Duplicate or drifting paths relevant to this change:

- `../psflows/flows/lessons/prompts/AGENTS.prompt`
  - giant flow-level assembler that should shrink into a thin build handle in
    the final shape
- `../psflows/flows/lessons/prompts/shared/routing.prompt`
  - fake concrete owner stubs that should go away in the final shape
- Rally-side duplicate ownership is now removed; the remaining authored drift
  lives in the proof flow.

Capability-first opportunities before new tooling:

- use compiler-owned package emit rather than adding a Rally package registry
- reuse existing package load and package copy paths rather than adding a new
  Rally resolver or sidecar compiler
- keep the runtime prompt contract narrow instead of inventing a second prompt
  carrier

Behavior-preservation signals already available:

- `tests/unit/test_flow_build.py`
  - covers current build behavior, including the current `SOUL.md` sidecar path
- `tests/unit/test_flow_loader.py`
  - covers compiled-agent loading and contract validation
- `tests/unit/test_runner.py`
  - covers run-home readback and prompt assembly behavior
- `tests/unit/domain/test_flow_contracts.py`
  - covers flow and compiled-contract model rules

## 3.3 Decision gaps that must be resolved before implementation

This research pass closed the Rally-side plan shape. No new user blocker
question is needed before deeper Rally planning continues.

Settled for this plan:

- keep `AGENTS.md` as the formal runtime instruction contract
- do not add a new package registry to `flow.yaml`
- keep the current flow-agent key to slug rule unless stronger repo evidence
  later proves it insufficient
- do not preserve Rally-owned `SOUL` emission as a compatibility layer
- allow one thin flow-facing build handle when Doctrine target mode needs a
  configured entrypoint
- treat Doctrine's runtime-package emit, optional sibling `SOUL` emit, and
  imported concrete owner refs as shipped inputs for this plan

Implementation ownership:

- Rally owns consuming and documenting the shipped Doctrine contract in this
  repo
- `../psflows` adoption can begin once Rally package cutover is real; no new
  Doctrine work is required for this plan

## 3.4 Shipped Doctrine fit for this plan

This is the Doctrine fit note for Rally, not a feature request. Doctrine already
ships the pieces this plan needs. Rally's job is to consume them honestly.

### What Doctrine already makes true

- A directory-backed `<module>/AGENTS.prompt` import is a runtime package root.
- A thin `AGENTS.prompt` build handle may import runtime packages and let them
  own the emitted runtime tree.
- `emit_docs` and `emit_flow` walk the same first-seen runtime frontier.
- A sibling `SOUL.prompt` beside a runtime package `AGENTS.prompt` is optional,
  and Doctrine emits `SOUL.md` only when it matches the same concrete agent.
- Imported concrete agents can be named directly in routes, so a flow does not
  need fake local concrete stubs just to point at a real owner.

### What is still wrong in lessons and Rally

- `../psflows/flows/lessons/prompts/AGENTS.prompt` is still a giant wrapper
  instead of a thin build handle.
- `../psflows/flows/lessons/prompts/shared/routing.prompt` still keeps fake
  concrete owner stubs.
- Rally's package cutover is done; the remaining gap is proving that contract
  on `../psflows/flows/lessons` after the parallel edits there settle.

### What success looks like with the shipped contract

- `../psflows/flows/lessons` replaces the giant wrapper with a thin build
  handle, not a duplicated concrete-owner list.
- `../psflows/flows/lessons/prompts/shared/routing.prompt` deletes the
  naming-only concrete stubs.
- A reader can understand one agent by opening only
  `prompts/agents/<slug>/AGENTS.prompt` and optional peer files in that same
  directory.
- Rally keeps one front-door build call per flow and stops owning any `SOUL`
  render path.
- The compiled output already arrives in the package shape Rally needs, so
  Rally does not invent a second target registry, a wrapper manifest, or a
  local prompt-emission workaround.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

Current authored and compiled shape for lessons:

```text
../psflows/flows/lessons/
  flow.yaml
  prompts/
    AGENTS.prompt
    shared/
      contracts.prompt
      review.prompt
      routing.prompt
      skills.prompt
      israeli_operating_system.prompt
      ...
    contracts/
      dossier.prompt
      lesson_plan.prompt
      ...
    roles/
      project_lead/
        AGENTS.prompt
        SOUL.prompt
      section_dossier_engineer/
        AGENTS.prompt
        SOUL.prompt
      ...
  build/
    agents/
      project_lead/
        AGENTS.md
        final_output.contract.json
        SOUL.md
      ...
```

Two concrete facts matter here:

- the compiled tree is already close to the desired package shape
- the authored concrete-root ownership still lives in one top-level
  `AGENTS.prompt`, not in the local agent directories that already hold the
  real role text

Rally's own shipped flows still follow the same single-entrypoint pattern under
`flows/<flow>/prompts/AGENTS.prompt`, so Rally also currently assumes a
flow-level authored entrypoint instead of per-agent package roots.

## 4.2 Control paths (runtime)

Today the build and runtime path is:

1. `../psflows/pyproject.toml` points the flow target at one top-level
   `AGENTS.prompt`.
2. Rally `ensure_flow_assets_built(...)` calls `doctrine.emit_docs` for that
   flow target.
3. Rally prunes retired legacy `AGENTS.contract.json` artifacts if they still
   exist from older builds, then validates the compiler-owned package
   directories Doctrine emitted.
4. Doctrine output naming is still entrypoint-driven, so `AGENTS.prompt`
   produces `AGENTS.md` and `final_output.contract.json`, plus optional peer
   files such as `SOUL.md` when the package declares them.
5. Doctrine already ships the thin runtime-package pattern, but lessons has not
   adopted it yet.
6. Rally build has one front-door handle per flow today: one emit target name,
   one `emit_docs` call, and one build output tree under `flows/<flow>/build/`.
7. Rally loader reads `build/agents/<slug>/AGENTS.md` and
   `final_output.contract.json` and centers flow metadata on
   `build_agents_dir` plus compiled contracts.
8. Run-home materialization copies each compiled agent directory into
   `home/agents/<slug>/`.
9. The runner injects `home/agents/<slug>/AGENTS.md` into the turn prompt.
10. Peer files such as `SOUL.md` make it into the run home only because Rally
   copies full directories, not because the runtime has a second prompt
   injection path.

## 4.3 Object model + key abstractions

Relevant Rally abstractions today:

- `FlowDefinition`
  - owns flow metadata, compiled agents, and `build_agents_dir`
- `FlowAgent`
  - binds flow key, slug, allowlists, and compiled contract
- `CompiledAgentContract`
  - formal contract from `final_output.contract.json`
  - already carries `entrypoint`, `markdown_path`, `metadata_file`,
    `final_output`, and optional review metadata
- compiled agent directory
  - already acts like the package directory in practice
  - Rally loads and copies it as one directory, but the package contract is
    still described inconsistently in code and docs
- `_sync_role_soul_sidecars(...)`
  - Rally-only bridge that re-compiles peer prompt files outside Doctrine's
    main emit path

## 4.4 Observability + failure behavior today

Good loud-fail behavior today:

- missing workspace `pyproject.toml` fails before build
- Doctrine emit failure fails `ensure_flow_assets_built(...)`
- missing `AGENTS.md` or `final_output.contract.json` fails in the loader
- slug mismatch fails in the loader
- missing emitted schema or bad schema path fails in the loader

Weakness today:

- the authored-shape problem now lives almost entirely in
  `../psflows/flows/lessons`
- the real-flow proof is blocked until the concurrent lessons edits settle

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

Ideal authored and compiled shape:

```text
flows/<flow>/
  flow.yaml
  prompts/
    AGENTS.prompt
    shared/
      ...
    contracts/
      ...
    agents/
      project_lead/
        AGENTS.prompt
        SOUL.prompt
      section_dossier_engineer/
        AGENTS.prompt
        SOUL.prompt
      ...
  build/
    agents/
      project_lead/
        AGENTS.md
        final_output.contract.json
        SOUL.md
      section_dossier_engineer/
        AGENTS.md
        final_output.contract.json
        SOUL.md
      ...
```

Important notes:

- The local agent directory is the authored unit.
- The compiled agent directory is the emitted unit Rally consumes.
- No giant flow-level wrapper prompt should survive in the final shape.
- One thin flow-facing build handle may survive when Doctrine target mode still
  needs a configured entrypoint.
- The giant synthetic concrete-agent assembly file is not acceptable in the
  final shape.
- This plan treats `prompts/agents/<slug>/` as the best-case authored target
  for the proof flow, while the thin build handle may still live at
  `prompts/AGENTS.prompt`.
- Rally's own shipped flows should target this same authored shape after the
  Rally package cutover lands. Doctrine is already ready for it.

## 5.2 Control paths (future)

Target build and runtime path:

1. Doctrine resolves the flow's concrete emitted agents from clean local agent
   package roots behind one thin flow-facing build handle.
2. Rally still invokes one flow-facing Doctrine build handle per flow.
   Doctrine resolves the package roots behind that one front-door build call.
3. Doctrine emits one compiled package directory per runtime agent directly
   into `build/agents/<slug>/`, with `AGENTS.md`,
   `final_output.contract.json`, and any optional peer files such as `SOUL.md`.
4. Rally build code only runs Doctrine emit. Rally does not render peer prompt
   files itself.
5. Rally loader treats `build/agents/<slug>/` as the authoritative compiled
   package directory, validates the required runtime pair
   `AGENTS.md` plus `final_output.contract.json`, and preserves any compiler-owned
   peer files without trying to own them.
6. Rally run-home sync copies the full compiled package directory into
   `home/agents/<slug>/`.
7. Rally runtime still injects only `AGENTS.md` as the formal instruction
   surface.
8. If the agent should read `SOUL.md`, that instruction lives inside
   `AGENTS.md`; Rally itself does not add a second prompt plane.
9. Missing required compiled artifacts fail at build or load time, not later
   during an agent turn.

## 5.3 Object model + abstractions (future)

Target Rally model:

- keep `01_name -> name` as the one agent key to slug mapping
- treat `build/agents/<slug>/` as a compiled agent package directory
- keep `final_output.contract.json` as the machine-readable contract for the
  package
- allow peer compiler-owned files such as `SOUL.md` to live in that package
  directory without Rally special-casing how they were made
- keep existing `CompiledAgentContract` and related flow types as the main
  loaded contract surface for this plan
- remove `FlowDefinition.prompt_entrypoint` in this plan instead of trying to
  redefine it around a no-longer-required flow-level prompt root

This plan does not need:

- a new package registry in `flow.yaml`
- a giant flow-level wrapper prompt that repeats concrete ownership
- per-agent emit-target enumeration in Rally
- a new manual `SOUL` compiler step
- a new second runtime instruction carrier
- a new `CompiledAgentPackage` wrapper type just to rename an already-clear
  directory boundary

## 5.4 Invariants and boundaries

- Doctrine owns authored package emit.
- Rally owns build orchestration, package validation, run-home sync, docs, and
  tests.
- The compiler, not Rally, owns peer package artifacts.
- `AGENTS.md` remains the one formal runtime instruction contract in this plan.
- The final design has one package truth per runtime agent.
- deterministic Rally code owns package rebuild, package validation, and
  package copy
- authored prompt content owns any instruction that tells the runtime agent to
  open peer files such as `SOUL.md`
- Rally keeps one front-door build handle per flow and does not learn a second
  target registry or package enumeration path
- no hidden registry, compatibility shim, or fallback side-emitter is allowed

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Doctrine shipped contract | `../doctrine/doctrine/emit_common.py`, `../doctrine/tests/test_emit_docs.py`, `../doctrine/tests/test_emit_flow.py` | `collect_runtime_emit_roots(...)`, runtime-package tests | Shipped Doctrine walks direct roots plus imported runtime packages in first-seen order and uses that same frontier for emit flow | Treat this as fixed external truth; do not design Rally around the old entrypoint-only assumption | Removes the stale dependency story and keeps Rally off workaround paths | Imported runtime-package frontier is authoritative | Doctrine emit tests and example 115 build contract |
| Doctrine shipped contract | `../doctrine/docs/EMIT_GUIDE.md`, `../doctrine/pyproject.toml`, `../psflows/pyproject.toml` | flow-facing emit handle | Shipped Doctrine still builds through one configured `AGENTS.prompt` or `SOUL.prompt` entrypoint per target, and that entrypoint may be a thin build handle | Keep one flow-facing build handle per flow in Rally and in the proof flow | Prevents per-agent target enumeration while avoiding the false `no top-level build handle` goal | Thin build-handle contract | Doctrine docs plus Rally build-path tests |
| Doctrine shipped contract | `../doctrine/doctrine/emit_docs.py`, `../doctrine/docs/EMIT_GUIDE.md`, `../doctrine/examples/115_runtime_agent_packages/**` | runtime-package emit layout | Shipped Doctrine emits package-root `AGENTS.md`, optional `SOUL.md`, and bundled peers for imported runtime packages | Consume those compiler-owned packages directly and stop Rally side-emission | Rally should use the compiler's package boundary instead of re-creating it | Compiled agent package directory contract | Doctrine emit tests plus Rally package tests |
| Doctrine shipped contract | `../doctrine/examples/115_runtime_agent_packages/prompts/writer_home/AGENTS.prompt`, `../doctrine/examples/70_route_only_declaration/prompts/IMPORTED_ROUTE_TITLES.prompt` | imported owner and route refs | Shipped Doctrine already lets imported concrete agents be named as route targets without fake local concrete stubs | Remove lessons routing stubs during adoption instead of preserving them as compiler workarounds | Keeps the authored model honest | Imported concrete owner-ref contract | Doctrine examples plus `psflows` adoption proof |
| Proof-flow authored source | `../psflows/flows/lessons/prompts/roles/**` | lessons authored package roots | Lessons keeps real role homes under `prompts/roles/` | Migrate the proof flow authored homes to `prompts/agents/<slug>/` and update local imports to match | The final shape hardens `agents/` as the best-case authored target for the proof flow | Lessons proof flow uses package-local `prompts/agents/<slug>/` roots | `psflows` adoption proof |
| Proof-flow emit wiring | `../psflows/pyproject.toml` | `tool.doctrine.emit.targets[name=\"lessons\"]` | Lessons still builds from `flows/lessons/prompts/AGENTS.prompt` | Rewire the lessons target to one thin Doctrine build handle that imports runtime packages without re-declaring concrete owners | The proof flow should keep the front-door build handle but lose duplicated concrete ownership | Lessons build wiring uses the shipped thin build-handle surface | `psflows` adoption proof plus Rally build smoke on the adopted flow |
| Proof-flow cleanup | `../psflows/flows/lessons/prompts/AGENTS.prompt` | giant wrapper prompt | Lessons still routes concrete-root ownership through one giant wrapper prompt | Replace that wrapper with a thin import-only build handle, or keep a tiny top-level `AGENTS.prompt` only if target mode still needs it | The real anti-pattern is duplicated concrete ownership, not every top-level build handle | Lessons authored shape has no giant wrapper and no duplicated concrete owner list | `psflows` adoption proof |
| Rally build | `src/rally/services/flow_build.py` | `ensure_flow_assets_built(...)`, `_sync_role_soul_sidecars(...)` | Runs one flow emit target, then manually renders `SOUL` sidecars and deletes stale sidecars | Remove Rally-owned `SOUL` sidecar rendering once Doctrine emits full packages, while keeping one front-door Doctrine build call per flow | Keep one compiler-owned package truth and remove duplicate emit ownership without adding package enumeration logic to Rally | Flow build only orchestrates compiler-owned package emit through one flow-facing handle | `tests/unit/test_flow_build.py` |
| Rally metadata | `src/rally/services/flow_loader.py`, `src/rally/domain/flow.py` | `load_flow_definition(...)`, `FlowDefinition.prompt_entrypoint` | Assumes `flows/<flow>/prompts/AGENTS.prompt` as required flow metadata | Remove `prompt_entrypoint` from this plan's runtime flow-definition contract and update direct test constructors | Avoid stale metadata when the runtime truth is the compiled package directory, not the authored build handle | Flow metadata centers on `build_agents_dir` plus compiled package contracts | `tests/unit/test_flow_loader.py`, `tests/unit/test_adapter_mcp_projection.py`, `tests/unit/test_run_store.py` |
| Rally load | `src/rally/services/flow_loader.py` | `_load_compiled_agents(...)` | Loads `AGENTS.md` plus `AGENTS.contract.json`; peer files are incidental | Tighten loader language around compiled agent package directories and loud-fail package completeness rules while preserving compiler-owned peer files | Make package contract explicit without widening runtime injection | Clear compiled package boundary | `tests/unit/test_flow_loader.py`, `tests/unit/domain/test_flow_contracts.py` |
| Rally runtime sync | `src/rally/services/home_materializer.py` | `_sync_compiled_agents(...)` | Copies whole directories already | Keep this as the package sync path and document it as such | This is already the right convergence point | No behavior change, clearer package contract | `tests/unit/test_runner.py` |
| Rally runtime prompting | `src/rally/services/runner.py` | `_build_agent_prompt(...)` | Injects `AGENTS.md` only | Keep as-is unless a separate approved design changes runtime contract scope | Avoid accidental runtime widening | No change in this plan | `tests/unit/test_runner.py` |
| Rally docs | `docs/RALLY_MASTER_DESIGN.md` | runtime contract and package language | Says only `AGENTS.md` is formal runtime contract; package shape is implicit and older sidecar language still leaks through | Update to describe compiled agent package directories and remove stale sidecar language | Docs should match final package truth | Architecture detail docs aligned | docs review plus any affected assertions |
| Rally docs | `docs/RALLY_RUNTIME.md` | flow build and runtime path | Describes build agents generically | Update to say Rally consumes compiler-owned agent packages and does not render `SOUL` itself | Keep runtime docs honest | Runtime doc aligned | docs review |
| Rally docs | `docs/RALLY_PORTING_GUIDE.md` | before/after authoring examples and port rules | Shows role-home port pattern but not the best-case package model | Add the clean before/after package example and delete stale wording that treats giant flow-level assembly as the desired end state | Future ports should target the clean shape | Porting guide aligned | docs review |
| Rally tests | `tests/unit/test_flow_build.py` | role `SOUL` sidecar test case | Asserts Rally renders `SOUL.md` into built agent dirs and deletes stale sidecars | Replace with compiler-owned package expectations once Doctrine emits peer files directly | Old test locks the behavior this plan is deleting | Build tests prove Rally stopped side-emitting peer prompt files | `tests/unit/test_flow_build.py` |
| Rally test fixtures | `tests/unit/test_adapter_mcp_projection.py`, `tests/unit/test_run_store.py` | direct `FlowDefinition(...)` fixtures | Construct `FlowDefinition` with `prompt_entrypoint` | Update fixture builders to the cleaned flow metadata contract | Prevent stale test-only shape from reintroducing dead metadata | Fixture contract aligned | those test files |

## 6.2 Migration notes

Canonical owner path / shared code path:

- Doctrine emit code owns package-root discovery and package artifact emission.
- Doctrine emit target plumbing already exposes one flow-facing build handle
  Rally can call once per flow.
- Rally `src/rally/services/flow_build.py` owns build orchestration only.
- Rally `src/rally/services/flow_loader.py` and
  `src/rally/services/home_materializer.py` own compiled-package validation and
  run-home package sync.

Deprecated APIs and surfaces:

- `FlowDefinition.prompt_entrypoint` in its current required form
- Rally-owned `_sync_role_soul_sidecars(...)`

Delete list:

- remove `_sync_role_soul_sidecars(...)` and its stale sidecar cleanup path
- remove tests that assert Rally itself creates `SOUL.md`
- remove stale doc wording that implies Rally owns peer prompt emission
- remove stale porting guidance that treats giant flow-level concrete-agent
  assembly as the desired end state

Capability-replacing harnesses to delete or justify:

- do not add a Rally package registry
- do not add a Rally package resolver
- do not add per-agent build-target enumeration in Rally
- do not add a Rally peer-prompt compiler or runtime side loader

Live docs, comments, and instructions to update or delete:

- `docs/RALLY_MASTER_DESIGN.md`
- `docs/RALLY_RUNTIME.md`
- `docs/RALLY_PORTING_GUIDE.md`
- any porting-guide example that still teaches `prompts/roles/` or a wrapper
  `prompts/AGENTS.prompt` with duplicated concrete ownership as the desired end
  state
- any touched code comments in `flow_build.py`, `flow_loader.py`, or
  `home_materializer.py` that still describe peer prompt emission as Rally work

Behavior-preservation signals for refactors:

- `tests/unit/test_flow_build.py`
- `tests/unit/test_flow_loader.py`
- `tests/unit/test_runner.py`
- `tests/unit/domain/test_flow_contracts.py`
- emitted readback and run-home inspection against the shipped Doctrine package
  contract

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Runtime package contract | `src/rally/services/flow_loader.py`, `src/rally/services/home_materializer.py`, `src/rally/services/runner.py` | Treat compiled agent directories as the package truth, with `AGENTS.md` as the only injected runtime surface | Keeps one package boundary across build, load, copy, and runtime prompt assembly | include |
| Build ownership | `src/rally/services/flow_build.py`, `tests/unit/test_flow_build.py` | Rally orchestrates Doctrine emit only; Rally does not emit peer prompt files | Prevents a second compiler path from creeping back in | include |
| Build entry surface | `src/rally/services/flow_build.py`, Doctrine emit target plumbing, `../psflows/pyproject.toml` | Keep one flow-facing Doctrine build handle per flow | Prevents a second target registry or package enumeration path from creeping into Rally | include |
| Flow metadata | `src/rally/domain/flow.py`, `tests/unit/test_adapter_mcp_projection.py`, `tests/unit/test_run_store.py` | Remove required flow-level prompt-entrypoint metadata from the package-mode contract | Prevents dead flow-wrapper assumptions from surviving in test fixtures and model types | include |
| Rally docs | `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_PORTING_GUIDE.md` | Describe compiled agent packages as the Rally-consumed unit and the best-case authoring target | Prevents future ports and doc readers from rebuilding the old story | include |
| Real flow adoption | `../psflows/flows/lessons/**` and future Rally flow examples | Switch to local agent package roots after Rally package cutover is real, using Doctrine's shipped thin build-handle contract | Keeps Rally from inventing a workaround while also dropping the stale external blocker | defer until Rally phases 2 through 5 land |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; split Section 7 into the
> smallest reasonable sequence of coherent self-contained units that can be
> completed, verified, and built on later. If two decompositions are both
> valid, bias toward more phases than fewer. `Work` explains the unit;
> `Checklist (must all be done)` is the authoritative must-do list inside the
> phase; `Exit criteria (all required)` names the concrete done conditions.
> Refactors, consolidations, and shared-path extractions must preserve existing
> behavior with credible evidence proportional to the risk. For agent-backed
> systems, prefer prompt, grounding, and native-capability changes before new
> harnesses or scripts. No fallbacks or runtime shims; the system must work
> correctly or fail loudly, with superseded paths deleted. The authoritative
> checklist must name the actual chosen work, not unresolved branches or
> placeholders. Prefer programmatic checks per phase; defer manual or UI
> verification to finalization. Avoid negative-value tests and heuristic gates.
> Also: document new patterns or gotchas in code comments at the canonical
> boundary when that meaningfully prevents drift.

## Phase 1: Lock The Shipped Doctrine Contract As Input

### Goal

Lock the plan and proof flow to Doctrine's shipped runtime-package contract so
Rally implementation starts from current framework truth, not a stale blocker.

### Work

Use Doctrine's shipped runtime-package frontier, paired package artifacts, one
flow-facing build handle per flow, and imported owner references as fixed input
for the Rally work.

### Checklist (must all be done)

- [x] restate the Rally plan so it treats Doctrine runtime packages as shipped
      truth, not pending dependency work
- [x] restate the proof-flow target so it allows one thin build handle and only
      forbids the giant concrete-owner wrapper
- [x] use the shipped Doctrine docs, tests, and example proof as the external
      fit gate for Rally implementation
- [x] make every later Rally phase consume that shipped contract directly

### Verification (required proof)

- the smallest matching Doctrine emit or flow tests for runtime-package emit,
  paired package artifacts, and owner references
- emitted readback inspection on the checked-in runtime-package example or a
  close equivalent fixture

### Docs/comments (propagation; only if needed)

- none in Rally; Doctrine docs and examples are already part of the external
  fit check

### Exit criteria (all required)

- the plan no longer treats Doctrine support as missing
- the thin build-handle contract is explicit and consistent across the artifact
- later Rally phases can proceed without inventing a framework workaround

### Rollback

- if the shipped Doctrine contract turns out to be narrower than documented,
  stop and repair the plan before landing Rally code

## Phase 2: Cut Rally Build Over To Compiler-Owned Packages

### Goal

Make Rally build flows through Doctrine only, with no Rally-owned peer prompt
emission.

Status: COMPLETE

### Work

Remove Rally's `SOUL` side path while preserving one front-door build call per
flow and keeping the build failure path loud.

Completed work:
- deleted Rally's role-local `SOUL.prompt` render path from
  `src/rally/services/flow_build.py`
- kept one Doctrine `emit_docs` call per flow and tightened the build comment
  at the package boundary
- updated `tests/unit/test_flow_build.py` so it proves Rally preserves
  compiler-owned peer files instead of rendering them itself

### Checklist (must all be done)

- [x] delete `_sync_role_soul_sidecars(...)` from
      `src/rally/services/flow_build.py`
- [x] remove code that walks `prompts/roles/*/SOUL.prompt` during Rally build
- [x] keep `ensure_flow_assets_built(...)` on one flow-facing Doctrine build
      call per flow instead of adding per-agent target enumeration
- [x] update `tests/unit/test_flow_build.py` so it proves Rally stopped
      rendering `SOUL.md` itself
- [x] check for any bundled or helper code that still assumes the deleted
      side-emission path and remove or update it in the same pass

### Verification (required proof)

- `uv run pytest tests/unit/test_flow_build.py -q`

### Docs/comments (propagation; only if needed)

- add or tighten one short code comment near the final build boundary if that
  boundary is otherwise easy to regress

### Exit criteria (all required)

- Rally no longer emits peer prompt files itself
- Rally still rebuilds each flow through one front-door Doctrine build call
- build failures still stop loud with useful error detail

### Rollback

- revert the Rally build-path change before landing if the Doctrine package
  output is not actually stable enough to consume

## Phase 3: Remove Stale Flow Metadata

### Goal

Delete flow metadata that only existed to support the old wrapper-based
authoring shape.

Status: COMPLETE

### Work

Remove `FlowDefinition.prompt_entrypoint` and any direct test or fixture usage
that depends on it, so Rally metadata centers on compiled package truth.

Completed work:
- removed `FlowDefinition.prompt_entrypoint` from `src/rally/domain/flow.py`
- removed the loader's hard-coded `flows/<flow>/prompts/AGENTS.prompt`
  metadata requirement
- updated direct `FlowDefinition(...)` fixtures in unit tests to use
  `build_agents_dir` plus compiled contracts only

### Checklist (must all be done)

- [x] remove `prompt_entrypoint` from `src/rally/domain/flow.py`
- [x] remove loader code in `src/rally/services/flow_loader.py` that resolves
      a required flow-level `prompts/AGENTS.prompt`
- [x] update every direct `FlowDefinition(...)` fixture in unit tests that
      still passes `prompt_entrypoint`
- [x] confirm no remaining Rally-owned runtime behavior depends on the removed
      metadata field

### Verification (required proof)

- `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_adapter_mcp_projection.py tests/unit/test_run_store.py -q`

### Docs/comments (propagation; only if needed)

- update or remove any touched code comments that still describe a required
  flow-level prompt-entrypoint field

### Exit criteria (all required)

- the dead flow-wrapper metadata is gone
- no direct test fixture keeps the old shape alive
- Rally metadata now centers on `build_agents_dir` plus compiled contracts

### Rollback

- revert this metadata cut if the actual Rally runtime still needs the field
  for a proven reason not captured in the plan

## Phase 4: Tighten Loader And Run-Home Package Semantics

### Goal

Make Rally's load, copy, and prompt assembly path describe one compiled package
boundary cleanly and consistently.

Status: COMPLETE

### Work

Tighten loader wording and contract checks around compiled package directories,
preserve whole-directory run-home sync, and keep runtime prompt injection scoped
to `AGENTS.md`.

Completed work:
- added package-boundary comments in `src/rally/services/flow_loader.py`,
  `src/rally/services/home_materializer.py`, and `src/rally/services/runner.py`
- added targeted tests that prove compiler-owned peer files do not widen the
  runtime prompt surface
- added domain-level package-contract tests in
  `tests/unit/domain/test_flow_contracts.py` so the cleaned package contract is
  proven alongside slug mapping
- kept the key-to-slug rule and whole-directory package copy path unchanged

### Checklist (must all be done)

- [x] update `src/rally/services/flow_loader.py` so compiled package
      directories are described as the authoritative loaded unit
- [x] keep the current key-to-slug rule as the only mapping rule
- [x] audit `src/rally/services/home_materializer.py` for stale non-package
      wording and keep whole-directory copy as the run-home sync path
- [x] audit `src/rally/services/runner.py` for stale wording while keeping
      runtime prompt injection scoped to `AGENTS.md`
- [x] update `tests/unit/test_flow_loader.py`,
      `tests/unit/test_runner.py`, and `tests/unit/domain/test_flow_contracts.py`
      so they prove the cleaned package contract without widening runtime
      prompt scope

### Verification (required proof)

- `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py -q`

### Docs/comments (propagation; only if needed)

- add or repair small comments at the package-validation or package-copy
  boundary only if they materially prevent drift

### Exit criteria (all required)

- loader, run-home sync, and prompt assembly all tell the same package story
- no new runtime instruction plane was added
- peer files are preserved as compiler-owned artifacts, not runtime-owned
  prompt surfaces

### Rollback

- revert local package-language changes if they no longer match the real
  Doctrine output contract

## Phase 5: Align Rally Docs And Porting Guidance

### Goal

Make Rally docs teach the clean package model and stop teaching the old manual
`SOUL` story or wrapper-first authored shape.

Status: COMPLETE

### Work

Update Rally design docs, runtime docs, and porting guidance so they describe
compiled agent packages as the Rally-consumed unit and the best-case authored
shape.

Completed work:
- updated `docs/RALLY_MASTER_DESIGN.md` to talk about compiled agent packages
  in `home/agents/`
- updated `docs/RALLY_RUNTIME.md` so build, load, and run-home language matches
  the shipped package contract
- updated `docs/RALLY_PORTING_GUIDE.md` so the best-case authored shape uses
  local `prompts/agents/<slug>/` homes plus one thin top-level build handle
  when needed

### Checklist (must all be done)

- [x] update `docs/RALLY_MASTER_DESIGN.md` package-language and remove stale
      sidecar wording
- [x] update `docs/RALLY_RUNTIME.md` so the build and run-home path matches the
      shipped package contract
- [x] update `docs/RALLY_PORTING_GUIDE.md` with a clean before or after package
      example
- [x] remove stale wording that treats giant flow-level concrete-agent assembly
      as the desired end state

### Verification (required proof)

- cold-read the touched docs against the shipped package contract

### Docs/comments (propagation; only if needed)

- these docs are the propagation work for this phase

### Exit criteria (all required)

- Rally docs tell one consistent package story
- future ports are guided toward the clean authored shape

### Rollback

- none; these docs should land with the code and package contract they describe

## Phase 6: Prove The Final Shape On A Real Flow

### Goal

Prove the authored and runtime package shape end to end on
`../psflows/flows/lessons` after Rally package cutover and docs alignment land.

Status: COMPLETE

Resolved in current pass:
- deleted `../psflows/flows/lessons/prompts/shared/routing.prompt`
  and moved the remaining route guidance onto plain owner names plus exact
  Rally `next_owner` keys
- restored fresh proof after a later lessons prompt edit drifted into a
  Doctrine workflow override mismatch in
  `../psflows/flows/lessons/prompts/contracts/copy_grounding.prompt`

### Work

Use `../psflows/flows/lessons` as the first real adoption target, migrate that
flow to package-local agent roots, delete the superseded wrapper surfaces, then
rebuild emitted readback, inspect compiled package directories, and prove the
run-home copy shape.

Completed work:
- kept `../psflows/flows/lessons/prompts/AGENTS.prompt` as a thin import-only
  build handle
- moved the role-owned authored source into
  `../psflows/flows/lessons/prompts/agents/<slug>/` and deleted the superseded
  `prompts/roles/` tree
- updated `../psflows/pyproject.toml` so the lessons emit target writes to
  `flows/lessons/build`, which lets imported `agents/<slug>` packages land at
  `build/agents/<slug>/`
- rebuilt lessons emitted readback and confirmed `AGENTS.md`, `SOUL.md`,
  `final_output.contract.json`, and schema files now land under
  `build/agents/<slug>/`
- proved a real run-home materialization copies the compiled package to
  `home/agents/<slug>/`
- updated the lessons scaffold test so it proves the `roles/` tree and stale
  nested `build/agents/agents/` path are gone
- deleted the superseded compile-time owner stubs in
  `../psflows/flows/lessons/prompts/shared/routing.prompt`
- converted the remaining lessons routing prose to plain owner names and exact
  Rally `next_owner` keys so the flow no longer depends on compile-time owner
  aliases
- made `CopyGroundingWorkflow` standalone and removed stale grounding reroute
  stubs so the lessons flow builds again from fresh repo state

### Checklist (must all be done)

- [x] use `../psflows/flows/lessons` as the proof flow
- [x] migrate the lessons authored source from `prompts/roles/` to
      `prompts/agents/`
- [x] update the lessons emit target wiring in `../psflows/pyproject.toml` to
      the final thin build handle
- [x] replace the superseded lessons flow-level concrete-agent assembly file at
      `../psflows/flows/lessons/prompts/AGENTS.prompt` with a thin import-only
      build handle, or keep a tiny top-level `AGENTS.prompt` only if target
      mode still needs it
- [x] delete the superseded naming-only owner stubs in
      `../psflows/flows/lessons/prompts/shared/routing.prompt`, or delete that
      whole file if nothing real still belongs there
- [x] confirm the compiled package lands under `build/agents/<slug>/`
- [x] confirm the run-home copy lands under `home/agents/<slug>/`
- [x] confirm Rally still builds that flow through one flow-facing Doctrine
      build handle

### Verification (required proof)

- emitted readback inspection
- the smallest matching Rally unit or integration proof
- one real run-home inspection

### Docs/comments (propagation; only if needed)

- update any surviving port or architecture note that still treats the final
  shape as theoretical

### Exit criteria (all required)

- the clean authored shape is real, not theoretical
- Rally consumes the compiler-owned package path end to end
- the front-door build contract is preserved in a real flow

### Rollback

- keep the flow on the old shape until the full package path is real
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Use the smallest proof that matches each phase:

- Doctrine fit proof: the smallest matching Doctrine emit or flow tests plus
  one emitted package proof on a real flow or close equivalent fixture
- package contract doc truth: cold-read plus targeted unit tests
- build-path changes: `tests/unit/test_flow_build.py`
- loader and runtime wording plus behavior: `tests/unit/test_flow_loader.py`,
  `tests/unit/test_runner.py`, and
  `tests/unit/domain/test_flow_contracts.py`
- final flow proof: emitted readback inspection plus one real compiled package
  and run-home check

Avoid:

- new grep-only hygiene gates
- new repo-shape policing tests
- a new Rally-owned pseudo-compiler just to prove package layout

# 9) Rollout / Ops / Telemetry

This is an internal architecture cleanup, not a user-facing runtime feature.

Rollout plan:

1. Treat Doctrine's shipped package contract as fixed input.
2. Lock the Rally plan to that shipped contract first.
3. Land Rally build cutover next.
4. Land Rally metadata cleanup and package-semantics cleanup after that.
5. Land docs updates in the same pass as the shipped Rally behavior they
   describe.
6. Cut `../psflows/flows/lessons` to the clean package shape only after the
   Rally package path is real.

Operational stance:

- fail loud during build or load if the compiled package contract is broken
- do not add runtime fallbacks
- do not add shadow registries or hidden path discovery

Telemetry:

- not needed beyond existing Rally build, load, and run failure surfaces

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, TL;DR, Sections 0 through 10, `planning_passes`, and helper
    block drift
- Findings summary:
  - `TL;DR > Outcome` overstated `SOUL` as always present even though the main
    plan treats it as optional
  - the artifact still treated shipped Doctrine package support as a missing
    external dependency
  - `0.2 In scope`, `0.4 Definition of done`, `7 > Phase 6`, and `9 > Rollout`
    drifted on whether one real-flow adoption proof was actually in scope
  - `5.1`, `6`, and `7` hardened `prompts/agents/` as the target shape without
    carrying the `roles/` to `agents/` migration and proof-flow emit rewiring
    all the way through the checklist
  - `planning_passes`, `8`, and `9` had helper or sequencing drift against the
    current architecture and phase plan
- Integrated repairs:
  - changed `TL;DR > Outcome` so `SOUL.prompt` is optional
  - reframed Doctrine support as shipped contract input instead of pending
    dependency work
  - marked external research as intentionally skipped because local Doctrine
    and Rally grounding was enough for this plan
  - made the lessons-flow adoption proof explicitly in scope and tied the final
    proof phase to `../psflows/flows/lessons`
  - added explicit proof-flow migration work for `prompts/roles/` to
    `prompts/agents/`, lessons emit-target rewiring, thin-build-handle cleanup,
    and owner-stub deletion
  - aligned Section 8 verification wording and Section 9 rollout sequencing
    with the authoritative phase plan
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

- 2026-04-15: Created the canonical plan doc. North Star is still draft.
- 2026-04-15: North Star moved to active when the user advanced the doc into
  `auto-plan`.
- 2026-04-15: Keep `AGENTS.md` as Rally's formal runtime instruction contract
  in this plan.
- 2026-04-15: Treat Doctrine as the owner of the authored package emit gap.
- 2026-04-15: Do not add a new `flow.yaml` package registry unless later repo
  evidence proves the current key to slug rule is insufficient.
- 2026-04-15: The final design must remove Rally-owned `SOUL` emission instead
  of preserving it as a compatibility layer.
- 2026-04-15: Research pass grounded the Doctrine dependency as three required
  framework features: package-root emit, paired package artifacts, and real
  owner references without fake concrete stubs.
- 2026-04-15: Deep-dive pass 1 resolved the Rally-side metadata shape: remove
  `FlowDefinition.prompt_entrypoint` in this plan and keep the existing
  compiled-contract types instead of adding a new package wrapper type.
- 2026-04-15: Deep-dive pass 2 resolved the Rally-side build entry shape: keep
  one front-door Doctrine build handle per flow and do not let Rally enumerate
  per-agent package targets.
- 2026-04-15: Phase planning locked the implementation order as dependency
  first, then Rally build, metadata cleanup, loader or runtime semantics, docs,
  and one real-flow proof.
- 2026-04-15: Consistency pass repaired the remaining scope and migration
  drift, made the lessons flow the explicit proof target, and found no
  remaining unresolved plan-shaping decision.
- 2026-04-15: Reframed the Doctrine dependency as a feature request centered on
  outcomes: local agent-package ownership, one flow-facing build handle,
  package-local peer artifact emit, and clean owner mentions without fake
  concrete stubs.
- 2026-04-15: Confirmed `../doctrine` already ships the needed runtime-package
  frontier, thin build-handle contract, optional sibling `SOUL` emit, and
  imported concrete owner refs.
- 2026-04-15: Refreshed this plan so Rally treats Doctrine support as shipped
  input, not pending dependency work.
- 2026-04-15: Tightened the target authored shape: forbid the giant
  concrete-owner wrapper, but allow one thin top-level build handle when target
  mode still needs it.
- 2026-04-15: Earlier decision-log entries that framed Doctrine as a pending
  dependency are now superseded by the shipped-contract confirmation above.
- 2026-04-15: Auto-plan re-check confirmed the controller prerequisites are in
  place, the artifact is already complete through `consistency-pass`, and the
  next valid step is `implement-loop`, not another planning stage.
- 2026-04-15: Earlier decision-log entries that described the order as
  dependency-first or described the Doctrine fit as a feature request are
  historical only; the live plan now starts from shipped Doctrine truth and
  proceeds with Rally build, metadata or runtime cleanup, docs, and the real
  flow adoption proof.
- 2026-04-15: Implement-loop parent pass completed Rally phases 2 through 5:
  Rally no longer emits `SOUL.md`, `FlowDefinition.prompt_entrypoint` is gone,
  package-boundary wording is aligned, and the package docs now teach the thin
  build-handle model.
- 2026-04-15: A targeted proof set for the touched Rally files passed, and the
  full Rally unit suite is only red because the untracked
  `tests/unit/test_shared_prompt_ownership.py` expects prompt text from a
  separate parallel change.
- 2026-04-15: Phase 6 stopped blocked because `../psflows` is already dirty in
  the exact lessons migration surface, including
  `flows/lessons/prompts/AGENTS.prompt` and generated build output.
