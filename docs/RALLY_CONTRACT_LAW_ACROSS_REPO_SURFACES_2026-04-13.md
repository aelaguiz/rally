---
title: "Rally - Contract Law Across Repo Surfaces - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - AGENTS.md
  - README.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md
  - docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - skills/rally-kernel/SKILL.md
  - flows/single_repo_repair/flow.yaml
  - flows/single_repo_repair/prompts/AGENTS.prompt
  - flows/single_repo_repair/setup/prepare_home.sh
  - src/rally/services/flow_loader.py
  - src/rally/cli.py
---

# TL;DR

Outcome
- Make Rally's base-dir, run-home, flow-home, run-identity, and instruction-source rules read as one law across the repo.
- A fresh reader should be able to answer the same contract questions from one clear owning surface instead of stitching together conflicting docs.
- Delete or rewrite stale competing wording in the same pass instead of leaving "old but still useful" parallel truth behind.

Problem
- Rally already has strong design rules, but they are split across AGENTS, README, master design, phase docs, prompt source, skills, setup scripts, and partial runtime code.
- Some files describe target state as if it already ships.
- Some core rules, such as flow code ownership and the exact path contract for note writes versus setup writes, do not yet read as one consistent repo-wide contract.

Approach
- Pick one clear owner for each rule, then converge every other live surface onto that owner.
- Separate current-state truth from target-state truth everywhere.
- Keep this effort docs-first and contract-first: no new harnesses, wrappers, CI doc gates, or repo-policing scripts.
- If a rule cannot be stated honestly without a small source-of-truth contract edit, make that narrow owner-path edit instead of writing around it in prose.

Plan
- Lock the law and the owner map first.
- Clean the repo-wide guidance surfaces next: `AGENTS.md`, `README.md`, and the master design.
- Clean the instruction-bearing surfaces after that: shared prompt source, skills, flow prompt source, and generated readback when prompt source changes.
- Clean active phase and planning docs last so they stop overstating shipped behavior and stop carrying stale rival rules.

Non-negotiables
- No new harnesses, wrappers, grep gates, or CI doc-policing surfaces for this effort.
- No parallel law surfaces that answer the same question differently.
- No hand-edited generated readback.
- No prose workaround when the real owner surface should carry the rule.
- No phase doc or planning doc may describe unshipped runtime behavior as current state.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-13
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can make its repo-root, run-home, flow-home, run-identity, and instruction-surface rules read as one law without adding new runtime machinery, if it does all of the following in one convergent pass:

- names one clear owner for each rule
- rewrites or deletes every live competing explanation that disagrees
- labels shipped behavior versus target behavior honestly
- keeps prompt rules in prompt source, skill rules in skills, runtime facts in runtime owners, and generated readback as generated only
- allows only narrow source-of-truth contract edits when the law cannot be stated honestly otherwise

This claim is false if any of the following remain true after the work lands:

- the same contract question still gets different answers from two live Rally surfaces
- a phase doc, README, or planning doc still presents target runtime behavior as current reality
- agents are told one path rule in prompts or skills while runtime or setup surfaces rely on a different unstated rule
- Rally still claims a required flow-code law without a clear owner path for that law
- generated readback, phase plans, or helper docs still act like rival sources of truth for lasting repo rules

## 0.2 In scope

- the repo-wide law for:
  - fixed top-level Rally folders
  - repo root versus run home versus flow home
  - what `flow.yaml` owns
  - what prompt source owns
  - what skills own
  - what generated readback is and is not
  - what env vars agents may trust
  - what notes control versus what final JSON controls
  - what is current shipped behavior versus target design
- cleanup and convergence across:
  - `AGENTS.md`
  - `README.md`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - active phase and planning docs that still shape live understanding
  - shared Rally prompt source under `stdlib/rally/prompts/`
  - Rally skills under `skills/`
  - flow prompt source under `flows/*/prompts/`
- regenerated readback inspection for any prompt-source change
- narrow source-of-truth contract edits if needed to make the repo's stated law honest
  - example class: a field or contract the docs say is required but the owning surface does not yet declare

## 0.3 Out of scope

- new runtime harnesses, wrappers, schedulers, or execution modes
- grep-based drift gates, doc-audit scripts, CI policing, or repo-shape tests
- broad runtime feature work unrelated to contract clarity
- adding another permanent "law doc" beside the surviving canonical homes
- preserving stale rival explanations for archaeology
- hand-editing `flows/*/build/**`

## 0.4 Definition of done (acceptance evidence)

- A fresh reader can answer the main Rally contract questions from one clear owner per question:
  - repo root and fixed folder rules
  - run-home and flow-home meaning
  - agent run-identity contract
  - note path versus final-JSON control path
  - source-versus-generated prompt boundaries
  - current shipped state versus target design state
- `AGENTS.md`, the master design, README, active phase docs, prompt source, skills, and any touched runtime contract comments all tell the same story.
- Any prompt-source change is recompiled and the generated readback matches the new source.
- No live doc still overclaims unshipped behavior as current state.
- Any narrow source-of-truth contract hole exposed by this sweep is either fixed at the owner path or named plainly as the blocker.

## 0.5 Key invariants (fix immediately if violated)

- One contract question gets one owning answer.
- Docs do not patch around source-of-truth gaps with rival prose.
- Prompt instruction law stays in `.prompt` source, not in runtime config or setup scripts.
- `flow.yaml` stays runtime contract, not instruction prose.
- Generated readback stays generated only.
- Current state and target state must be labeled plainly and never blurred together.
- This effort must not answer drift with harnesses, wrappers, or doc-policing gates.
- If lasting truth must move, it moves into a surviving canonical home and the stale surface shrinks or is deleted.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make the law easy for a fresh reader or agent to follow without cross-reading contradictory files.
2. Keep one owner per rule and remove rival truth.
3. Be honest about shipped behavior versus target design.
4. Use the smallest owning surface for each rule.
5. Avoid architecture theater such as new enforcement harnesses for a docs-and-contract problem.

## 1.2 Constraints

- `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` are Rally's fixed top-level folders.
- `flows/*/build/**` is generated readback, not hand-written source.
- `flow.yaml` owns runtime facts, not agent doctrine.
- Prompt and skill edits may require rebuild proof and readback inspection.
- Some active docs already mix current state with target-state plans, so cleanup must distinguish those two clearly.
- Some contract questions touch both docs and owning source surfaces, so docs-only prose may not be enough.

## 1.3 Architectural principles (rules we will enforce)

- Prefer one surviving owner path over cross-file repeated explanations.
- If a rule belongs to a source surface, put it there and make other surfaces point to it or align with it.
- Delete stale rival truth instead of leaving parallel explanations behind.
- Separate "ships today" from "target design" in every live doc that matters.
- If a law needs a narrow source-of-truth fix, make that fix instead of keeping the repo inconsistent on purpose.
- Do not add harnesses, wrappers, or CI gates to compensate for unclear contract writing.

## 1.4 Known tradeoffs (explicit)

- This cleanup may widen across many files because the drift is cross-cutting.
- Tightening the law may expose real source-of-truth gaps that need small owner-path edits.
- Some existing docs will likely get shorter because they should stop restating rules owned elsewhere.
- Active phase docs may need to lose stale "current state" wording even if the design idea itself still stands.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally has a strong top-level design in `AGENTS.md`, the master design, and several phase docs.
- Rally has shared prompt law in `stdlib/rally/prompts/` and shared skill law in `skills/`.
- Rally has a partial runtime in `src/rally/` plus flow runtime config in `flows/*/flow.yaml`.
- Rally already has at least one clear pattern: the design layer is stricter than the runtime layer.

## 2.2 What’s broken / missing (concrete)

- The same contract question still needs cross-reading to answer.
- Some docs talk about future runtime behavior as if it already exists.
- Some core law surfaces appear to be missing or only partially owned in source.
- Some path rules differ by surface, especially around run identity, note writes, and setup-time paths.
- There is no single cleanup pass yet that treats this as a full contract-convergence problem across the repo.

## 2.3 Constraints implied by the problem

- The fix must be convergence work, not a new product feature.
- The work must clean the surviving live surfaces in the same pass rather than adding one more overlay.
- The effort must stay docs-first and contract-first, but it may need narrow owner-path edits where the repo cannot be honest otherwise.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- No web research is needed for this plan. The problem is repo-local contract drift, not outside best practice uncertainty.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `AGENTS.md` — defines the repo-root law for fixed top-level folders, source-of-truth boundaries, build-and-verify rules, and the docs map that names the master design as the main design source.
  - `README.md` — is the main reader-facing Rally story and already explains the intended model for repo root, run home, run ids, `rally issue note`, and the Codex launch contract, but it also frames itself as target-v1 shape rather than shipped-state truth.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — is the lasting design law for Rally's ownership split, run-home model, launch contract, and operator surface.
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md` — is the active communication child plan and should only carry still-open Phase 3 detail that stays aligned with the master design.
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` — is the active runtime child plan and should only carry still-open Phase 4 detail that stays aligned with the master design.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — is the shared prompt-law home for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, and the rule that Rally-managed agents use the shared kernel skill rather than direct `issue.md` edits.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — is the shared authored final-JSON control contract and already states that `handoff` uses `next_owner`.
  - `skills/rally-kernel/SKILL.md` — is the shared skill-law home for durable notes through `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"` and for keeping note prose separate from turn control.
  - `flows/single_repo_repair/flow.yaml` — is the real flow-owned runtime config surface today and already owns adapter choice, timeouts, allowlists, and `project_doc_max_bytes: 0`.
  - `flows/single_repo_repair/prompts/AGENTS.prompt` and `flows/_stdlib_smoke/prompts/AGENTS.prompt` — are the real flow-local prompt sources that consume shared Rally law today.
  - `flows/single_repo_repair/setup/prepare_home.sh` — is the real flow-home setup owner today and shows the current setup-only env contract through `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH`.
  - `src/rally/services/flow_loader.py` — is the strongest shipped runtime contract owner today because it validates compiled-agent contracts, schema paths, and `handoff` requiring `next_owner`.
  - `src/rally/cli.py` — is the strongest shipped CLI truth today because it proves that real run execution, resume, and `issue note` are not fully implemented yet.

- Canonical path / owner to reuse:
  - `AGENTS.md` — should stay the owner for repo-root rules, folder shape, owner-path rules, and the "smallest owner" doctrine.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — should stay the owner for Rally's lasting design law, ownership split, operator surface, and the stable meaning of repo root, run home, and run ids.
  - `README.md` — should stay the reader-facing orientation surface, but only with wording that is honest about what ships today versus what is planned.
  - `stdlib/rally/prompts/rally/base_agent.prompt` and `skills/rally-kernel/SKILL.md` — should stay the shared agent-facing law for run identity, notes, and final JSON.
  - `flows/*/flow.yaml` — should stay the owner for flow runtime config and allowlists only.
  - `flows/*/prompts/**` — should stay the owner for flow-local instruction doctrine only.
  - `src/rally/services/flow_loader.py`, `src/rally/cli.py`, and later owning runtime seams — should stay the owner for what the runtime actually enforces.

- Existing patterns to reuse:
  - `AGENTS.md` — already uses the "smallest owner" rule; this plan should reuse that discipline instead of inventing a new doc taxonomy.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` plus active child docs — already express a master-doc plus child-doc pattern; the cleanup should reuse that rather than inventing another permanent law home.
  - `stdlib/rally/prompts/rally/base_agent.prompt` plus `skills/rally-kernel/SKILL.md` — already show the intended split between shared prompt doctrine and shared skill doctrine.
  - `tests/unit/test_flow_loader.py` — already protects one kind of contract truth by validating schema and repo-root ownership without scraping Markdown.

- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — shared env and note/final-JSON doctrine.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — shared final-output doctrine.
  - `skills/rally-kernel/SKILL.md` — shared note behavior and end-turn guidance.
  - `flows/single_repo_repair/prompts/AGENTS.prompt` and `flows/_stdlib_smoke/prompts/AGENTS.prompt` — concrete downstream prompt consumers that must stay aligned with the shared law.

- Native model or agent capabilities to lean on:
  - The repo already relies on authored prompt structure, env-var grounding, explicit file surfaces, and schema-backed final JSON. This cleanup does not need extra deterministic scaffolding because the problem is not missing model capability; it is cross-surface contract drift.

- Existing grounding / tool / file exposure:
  - `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` are already authored in the shared base-agent prompt.
  - `project_doc_max_bytes: 0` in `flows/single_repo_repair/flow.yaml` already proves Rally prefers explicit context over ambient project-doc bleed-through.
  - `runs/active/` and `runs/archive/` already exist at repo root, so live docs that still claim those directories are missing are stale.

- Duplicate or drifting paths relevant to this change:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` and `README.md` both describe a required three-letter flow code, but `flows/single_repo_repair/flow.yaml` does not declare `code`, and `src/rally/services/flow_loader.py` does not read or validate one. This is a real owner-path gap, not just wording drift.
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `stdlib/rally/prompts/rally/base_agent.prompt`, and `skills/rally-kernel/SKILL.md` all describe a shared `rally issue note` path and env injection, but `src/rally/cli.py` still only ships `run` and `resume` preflight/error surfaces, and `src/rally/adapters/codex/launcher.py` is still a placeholder. These docs must stay explicit about target state versus shipped state.
  - `flows/single_repo_repair/prompts/AGENTS.prompt` and `flows/_stdlib_smoke/prompts/AGENTS.prompt` import `rally.currentness`, `pyproject.toml` already points Doctrine at `stdlib/rally/prompts` as a shared prompt root, and multiple docs describe `stdlib/rally/prompts/rally/currentness.prompt`, but the checked-in `stdlib/rally/prompts/rally/` directory currently contains only `base_agent.prompt` and `turn_results.prompt`. That is a real shared-source gap at the exact owner path.
  - `flows/single_repo_repair/setup/prepare_home.sh` uses `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH`, while the Phase 3 note-write law says the durable note write path should resolve by `RALLY_RUN_ID` inside Rally-owned code rather than through a write-capable issue path. The cleanup needs to state setup-only versus agent-facing path rules plainly so these do not look like one mixed contract.
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` still contains stale now-false current-state claims such as "no `src/rally/`, no `tests/`, and no checked-in `runs/` placeholder directories yet." This is pure doc drift and should not survive the cleanup.
  - `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md` currently speaks as if shared run identity and future-facing note path are current agent-facing facts. That is only safe if the doc labels target-state dependence plainly; otherwise it becomes a rival live law surface.

- Capability-first opportunities before new tooling:
  - Use the existing owner split in `AGENTS.md` and the master design to converge wording before touching any runtime owner surface.
  - Use existing prompt-law and skill-law surfaces for agent-facing rules instead of inventing new wrappers or helper docs.
  - Use narrow source-of-truth edits only where the repo's stated law cannot be true otherwise, rather than building enforcement harnesses around the mismatch.

- Behavior-preservation signals already available:
  - `uv run python -m unittest discover -s tests/unit -q` — current lightweight contract signal; it passed during this research pass.
  - `tests/unit/test_flow_loader.py` — protects compiled-agent contract loading, repo-root-relative schema/example ownership, and `handoff` requiring `next_owner`.
  - `tests/unit/domain/test_turn_result_contracts.py` — protects the parsed turn-result contract for `handoff`, `done`, `blocker`, and `sleep`.
  - `uv run python -m rally run single_repo_repair --brief-file ... --preflight-only` — current runtime preflight signal for the loader boundary; it passed in the earlier audit pass.

## 3.3 Decision gaps that must be resolved before implementation

- No architecture-shaping blocker remains for planning.
- The North Star is confirmed.
- The owner-path decisions that shape implementation are now locked:
  - the required three-letter flow code belongs in `flows/*/flow.yaml`, with matching owner-path updates in `src/rally/domain/flow.py::FlowDefinition` and `src/rally/services/flow_loader.py`
  - shared currentness law belongs in `stdlib/rally/prompts/rally/currentness.prompt`
  - setup-only env vars stay separate from the agent-facing durable-note path
- The remaining work is sequencing, delete-or-rewrite inventory, and narrow owner-path edits where the repo cannot state the law honestly otherwise.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Repo-root law currently lives across:
  - `AGENTS.md`
  - `README.md`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - active child docs in `docs/`
  - shared prompt source under `stdlib/rally/prompts/rally/`
  - shared skills under `skills/`
  - flow runtime and prompt surfaces under `flows/`
  - partial runtime owners under `src/rally/`
- The checked-in shared Rally prompt tree currently contains:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
  - `stdlib/rally/prompts/rally/turn_results.prompt`
- `pyproject.toml` already points Doctrine at `stdlib/rally/prompts` through `tool.doctrine.compile.additional_prompt_roots`, so that tree is the real checked-in compile root for shared Rally prompt modules.
- The checked-in shared skill tree currently contains:
  - `skills/rally-kernel/SKILL.md`
  - `skills/repo-search/SKILL.md`
  - `skills/pytest-local/SKILL.md`
- Generated readback exists under:
  - `flows/_stdlib_smoke/build/agents/*`
  - `flows/single_repo_repair/build/agents/*`
  - these generated files are present in the worktree even though `flows/*/build/` is gitignored and marked generated.
- Runnable flow-owned surfaces currently exist only for `single_repo_repair`:
  - `flows/single_repo_repair/flow.yaml`
  - `flows/single_repo_repair/prompts/**`
  - `flows/single_repo_repair/setup/prepare_home.sh`
  - `flows/single_repo_repair/fixtures/**`
- Repo-local runtime roots already exist:
  - `runs/active/`
  - `runs/archive/`
- Partial runtime code already exists under `src/rally/`, including:
  - `cli.py`
  - domain contracts under `domain/`
  - flow loading under `services/flow_loader.py`
  - placeholder runtime seams under `services/` and `adapters/codex/`

## 4.2 Control paths (runtime)

- Repo-root guidance path today:
  - `AGENTS.md` sets the folder shape, owner rules, and docs map.
  - `README.md` explains Rally's intended model to readers.
  - the master design and child docs explain the larger architecture and phases.
- Agent-facing shared doctrine path today:
  - `stdlib/rally/prompts/rally/base_agent.prompt` injects `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
  - `skills/rally-kernel/SKILL.md` teaches note writes through `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"` and separates notes from final JSON control.
  - `stdlib/rally/prompts/rally/turn_results.prompt` defines the shared final-JSON control surface.
- Flow-local doctrine path today:
  - `flows/*/prompts/**` imports shared Rally prompt modules and defines local flow doctrine.
  - `flows/single_repo_repair/prompts/AGENTS.prompt` and `flows/_stdlib_smoke/prompts/AGENTS.prompt` both import `rally.currentness`, even though that checked-in source file is not present in this repo.
- Runtime enforcement path today:
  - `src/rally/services/flow_loader.py` loads `flow.yaml`, resolves prompt entrypoints, loads compiled `AGENTS.contract.json`, and validates that the shared turn-result schema requires `next_owner` for `handoff`.
  - `src/rally/cli.py` only ships `run` and `resume`.
  - `rally run ... --preflight-only` is the only real shipped path.
  - normal `run`, `resume`, `issue note`, launch env injection, run-home materialization, and runner orchestration are still unimplemented or placeholder.
- Flow setup path today:
  - `flows/single_repo_repair/setup/prepare_home.sh` is a separate setup-only control path.
  - it uses `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH` directly and appends setup notes into the issue file.
  - this is a different path contract from the agent-facing note-write path described in the shared prompt and skill law.

## 4.3 Object model + key abstractions

- Current explicit domain objects and contracts already include:
  - `FlowDefinition`
  - `FlowAgent`
  - `CompiledAgentContract`
  - `FinalOutputContract`
  - `AdapterConfig`
  - `RunRequest`
  - `ResumeRequest`
  - typed turn-result variants for `handoff`, `done`, `blocker`, and `sleep`
- Current explicit runtime nouns in docs and prompt law include:
  - repo root
  - flow root
  - run home
  - flow home setup
  - run identity
  - prompt source
  - generated readback
  - note path
  - final-JSON control path
  - currentness
- The main structural gap is not missing terminology. It is that a few owner paths are still incomplete or not honest yet:
  - flow code is described as required in docs, but `flows/single_repo_repair/flow.yaml` has no `code`, `src/rally/domain/flow.py::FlowDefinition` has no `code`, and `src/rally/services/flow_loader.py` does not validate one
  - currentness is treated as a shared Rally prompt module by live flow imports and the existing Doctrine compile root, but `stdlib/rally/prompts/rally/currentness.prompt` is missing from checked-in source
  - the setup-only env contract and the agent-facing note-write contract are not yet stated as two different lanes
  - current-state versus target-state wording is not kept clean across the live doc set

## 4.4 Observability + failure behavior today

- Existing proof and visibility surfaces today are:
  - `uv run python -m unittest discover -s tests/unit -q`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/domain/test_turn_result_contracts.py`
  - `rally run ... --preflight-only`
  - direct inspection of prompt source, generated readback, setup scripts, and docs
- Actual runtime failure behavior today is explicit in code:
  - `rally run` without `--preflight-only` fails with "Run execution is not implemented yet."
  - `rally resume` fails with "Resume is not implemented yet."
  - placeholder runtime seams are still empty ownership-boundary modules.
- Actual doc drift is also visible today:
  - some phase docs still describe current-state absences that are no longer true
  - some planning docs speak as if future-facing note and env surfaces already ship
  - some docs and prompt sources still point at `currentness.prompt` even though that checked-in source is absent

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- The lasting law should live in one surviving owner path per question:
  - `AGENTS.md`
    - fixed repo folders
    - smallest-owner doctrine
    - docs map
    - build-and-verify rules
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
    - Rally's lasting design law
    - repo root versus run home meaning
    - ownership split
    - operator surface
  - active child docs in `docs/`
    - only still-open phase detail
    - must be labeled as target-state or in-progress design, not as shipped truth
  - `README.md`
    - reader-facing orientation only
    - honest shipped-state versus target-state wording
  - `stdlib/rally/prompts/rally/*.prompt`
    - shared agent-facing doctrine
  - `skills/*.md`
    - shared skill behavior
  - `flows/*/flow.yaml`
    - flow runtime config only
  - `flows/*/prompts/**`
    - flow-local doctrine only
  - `flows/*/setup/*.sh`
    - setup-only flow-home preparation contract only
  - `src/rally/**`
    - actual enforced runtime truth
- Generated readback should remain in `flows/*/build/**` as inspection-only output after rebuild.
- This plan doc remains temporary planning state and must not become a permanent rival law surface.
- The shared currentness law must live in `stdlib/rally/prompts/rally/currentness.prompt` because live flow prompt source imports `rally.currentness` and Doctrine already treats `stdlib/rally/prompts` as the shared prompt root.

## 5.2 Control paths (future)

- A reader should be able to answer every contract question through one clean route:
  - repo law -> `AGENTS.md`
  - lasting product/design law -> master design
  - active deeper plan detail -> aligned child docs
  - shared agent law -> shared prompt source plus shared skills
  - flow-local law -> `flows/*/prompts/**`
  - flow runtime facts -> `flows/*/flow.yaml`
  - setup-only flow-home facts -> `flows/*/setup/*.sh`
  - actual shipped enforcement -> owning runtime code under `src/rally/**`
  - generated readback -> rebuild and inspect only
- The contract must distinguish three separate path lanes clearly:
  - run-home meaning and run-identity law
  - setup-only flow-home prep env vars
  - agent-facing durable-note writes through the Rally CLI path
- The target rule for the setup-versus-agent split is:
  - setup scripts may use setup-only env vars such as `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH`
  - shared agent-facing law must not teach those setup-only env vars as the durable-note write path
  - durable notes for agents remain `rally issue note --run-id "$RALLY_RUN_ID"` when that runtime path ships
- Live docs must plainly say whether they describe current behavior or target behavior.
- No child doc may describe unshipped runtime behavior as current state.

## 5.3 Object model + abstractions (future)

- The repo should treat these as first-class and non-overlapping:
  - repo root
  - flow root
  - run home
  - flow home setup
  - flow code
  - run id
  - run identity env vars
  - setup-only env vars
  - agent-facing note path
  - final-JSON control path
  - currentness law
  - prompt source
  - generated readback
- The target owner map for the current exposed gaps is:
  - flow code
    - is owned by `flows/*/flow.yaml`
    - is represented on `src/rally/domain/flow.py::FlowDefinition`
    - is validated by `src/rally/services/flow_loader.py` at flow-load time
  - currentness law
    - is owned by `stdlib/rally/prompts/rally/currentness.prompt`
    - is compiled through the existing shared prompt root in `pyproject.toml`
    - is consumed by flow prompt source through `import rally.currentness`
    - must not be carried by phase-doc prose or generated readback as the only surviving source
  - note path versus setup-only path
    - is split explicitly between shared agent-facing prompt/skill law and setup-only script law
    - shared agent-facing law stays in `stdlib/rally/prompts/rally/base_agent.prompt` plus `skills/rally-kernel/SKILL.md`
    - setup-only env law stays in `flows/*/setup/*.sh` plus the small number of design docs that explain that boundary
- Each of those should have one owning explanation and no live rival explanation.

## 5.4 Invariants and boundaries

- No live doc may answer a contract question differently from its owner.
- No plan doc or child phase doc may blur current and target state.
- No generated file may become the lasting home for authored law.
- No docs-only prose patch may hide a real owner-path contract hole.
- Flow code must not remain "required by docs only."
- Shared currentness law must not remain "referenced everywhere but absent in source."
- Setup-only env vars must not be taught as agent-facing note-write law.
- Flow code must not be inferred from flow name, agent keys, or docs when `flow.yaml` is the declared owner.
- No new harnesses, wrappers, grep gates, or policing tests may be introduced for this cleanup.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Repo law | `AGENTS.md` | repo-root rules, source-of-truth map, docs map | strong core law but not yet reflected everywhere | tighten the owner map and point more explicitly at surviving law homes | make repo-wide contract readable from one law surface | repo law map | none by default |
| Reader-facing orientation | `README.md` | Rally model, run-home model, operator surface, shipped-state wording | strong orientation but mixes stable story with target-v1 promises | rewrite shipped-versus-target wording and align owner-path references | stop overclaim drift | reader-facing contract | none by default |
| Lasting design law | `docs/RALLY_MASTER_DESIGN_2026-04-12.md` | ownership split, operator surface, run-home law, flow-code law | strong but ahead of some owners | align wording with actual owner map and narrow owner-path fixes | keep one lasting design law | master design law | none by default |
| Active communication child doc | `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md` | note path, env contract, currentness wording | mixes future path and still-open phase detail | relabel target-state detail and delete stale rival current-state wording | stop phase doc from acting like shipped truth | active child-doc contract | none by default |
| Active runtime child doc | `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` | runtime inventory and current-state claims | contains stale now-false current-state claims | rewrite stale inventory and keep only still-open phase detail | stop wrong live doc truth | active child-doc contract | none by default |
| Active planning child doc | `docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md` | currentness, note path, env injection, runtime status | still contains some already-drifted or now-duplicated law | shrink or relabel so it stops competing with lasting law homes | stop planning doc from becoming long-lived law | planning child-doc contract | none by default |
| Active planning child doc | `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md` | assumptions about shared run identity and note path | depends on future-facing shared law surfaces | relabel current-state assumptions or point them at target-state owners explicitly | stop accidental live-law drift | planning child-doc contract | none by default |
| Shared prompt law | `stdlib/rally/prompts/rally/base_agent.prompt` | shared env and note/final-JSON doctrine | already carries key law | align wording with surviving owner map only if needed | keep agent-facing law in prompt source | shared base-agent contract | compile inspection if changed |
| Shared prompt law | `stdlib/rally/prompts/rally/turn_results.prompt` | shared final-output doctrine | already the final-JSON owner | check wording against master design and keep it narrow | keep one final-control contract | shared turn-result contract | compile inspection if changed |
| Shared prompt compile root | `pyproject.toml` | `tool.doctrine.compile.additional_prompt_roots` | already points at `stdlib/rally/prompts` | preserve this as the one shared prompt-root contract and align docs to it | keeps shared prompt ownership explicit | shared compile-root contract | compile inspection if prompt tree changes |
| Shared prompt law gap | `stdlib/rally/prompts/rally/currentness.prompt` | shared currentness owner | referenced in docs and prompt source, missing in checked-in source | restore the source at this exact owner path; do not leave docs or generated readback as the only surviving source | remove source hole | shared currentness contract | compile inspection and targeted prompt proof |
| Shared skills | `skills/rally-kernel/SKILL.md` | durable-note and end-turn guidance | partly aligned with target contract | align wording with surviving law and current-vs-target honesty | keep skill law clean and shared | shared skill contract | none by default |
| Other shared skills | `skills/repo-search/SKILL.md`, `skills/pytest-local/SKILL.md` | feature-local skills | not law owners for this change | exclude unless owner-map cleanup reveals stale Rally-law wording inside them | avoid needless churn | no contract change expected | none |
| Flow runtime contract | `flows/single_repo_repair/flow.yaml` | runtime facts for the runnable flow | owns timeouts and allowlists, but does not own `code` yet | add a required `code` field for the validated three-letter flow code | stop docs-only law | flow runtime contract | `tests/unit/test_flow_loader.py` |
| Flow-local prompt source | `flows/single_repo_repair/prompts/AGENTS.prompt` | shared imports and flow-local doctrine | consumes shared law and imports missing `rally.currentness` source | align with the repaired shared law and rebuild readback | keep flow-local doctrine honest | flow prompt contract | compile inspection |
| Flow-local prompt source | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | shared imports and smoke-law doctrine | consumes shared law and imports missing `rally.currentness` source | align with the repaired shared law and rebuild readback | keep smoke proof honest | smoke prompt contract | compile inspection |
| Generated readback | `flows/_stdlib_smoke/build/**`, `flows/single_repo_repair/build/**` | compiled AGENTS and contracts | present and used by loader but generated only | rebuild after prompt-source changes and inspect representative outputs | keep generated readback derived | no hand-written contract | preflight plus readback inspection |
| Setup contract | `flows/single_repo_repair/setup/prepare_home.sh` | setup-only env usage and setup-note append | uses `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH` directly | document and align setup-only versus agent-facing path contracts; edit only if wording cannot stay honest otherwise | stop mixed path doctrine | setup-only env contract | targeted checks only if changed |
| Runtime owner | `src/rally/cli.py` | `run`, `resume`, future `issue note` surface | only preflight and not-implemented errors are shipped today | keep messages and docs honest; add narrow contract comments or surfaces only if later stages decide they are required | keep shipped truth and docs aligned | CLI contract | targeted unit tests if changed |
| Runtime owner | `src/rally/services/flow_loader.py` | flow and compiled-contract loading | strongest shipped validator today; no flow-code ownership yet | load, validate, and surface the `code` value from `flow.yaml` while keeping existing compiled-contract checks | keep runtime truth and docs aligned | loader contract | `tests/unit/test_flow_loader.py` |
| Runtime owner | `src/rally/domain/flow.py` | `FlowDefinition` | no field for flow code today | add `code` so the declared flow runtime contract has a typed home in the domain model | keep owner-path fix coherent | flow domain contract | `tests/unit/test_flow_loader.py` plus targeted domain tests if added |
| Runtime proof | `tests/unit/test_flow_loader.py` | loader contract coverage | covers slug mapping, schema ownership, and `handoff` requiring `next_owner` | extend coverage for missing, malformed, and surfaced flow `code` | keep the new owner-path fix honest without inventing doc harnesses | loader proof contract | this file |
| Runtime placeholder | `src/rally/adapters/codex/launcher.py` and sibling placeholder seams | launch/env contract and runtime implementation status | placeholder only | keep docs explicit that this is target-state work, not shipped truth | stop docs from overclaiming | placeholder status contract | none unless changed |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - repo-root rules -> `AGENTS.md`
  - lasting design law -> master design
  - shared prompt compile root -> `pyproject.toml`
  - shared agent-facing law -> shared prompt source plus shared skills
  - shared currentness law -> `stdlib/rally/prompts/rally/currentness.prompt`
  - flow code -> `flows/*/flow.yaml` + `src/rally/domain/flow.py::FlowDefinition` + `src/rally/services/flow_loader.py`
  - flow runtime facts -> `flow.yaml`
  - actual shipped enforcement -> owning runtime code
- Deprecated APIs (if any):
  - none yet, but stale doc-only contract answers should be treated as retired live truth once the surviving owner is cleaned
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - stale child-doc wording that presents target runtime behavior as current state
  - stale doc claims that repo paths or runtime modules are missing when they are present
  - any surviving wording that leaves `currentness.prompt` implied but source-less after the owner-path decision is made
  - any surviving wording that treats the three-letter flow code as docs-only law instead of a `flow.yaml` contract
  - any surviving wording that teaches setup-only env vars as agent-facing note-write law
- Capability-replacing harnesses to delete or justify:
  - none should be introduced for this work
- Live docs/comments/instructions to update or delete:
  - `AGENTS.md`
  - `README.md`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md`
  - `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md`
  - shared prompt source and shared skill source if wording changes there
- Behavior-preservation signals for refactors:
  - `uv run python -m unittest discover -s tests/unit -q`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/domain/test_turn_result_contracts.py`
  - readback rebuild plus representative inspection when prompt source changes

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Reader-facing docs | `README.md` | explicit shipped-state versus target-state labels | prevents README from competing with runtime truth | include |
| Lasting design docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md` | one owner per contract question | prevents child docs from becoming rival law homes | include |
| Active child docs | `docs/RALLY_PHASE_3_...`, `docs/RALLY_PHASE_4_...`, `docs/RALLY_BASE_AGENT_...`, `docs/RALLY_QMD_...` | target-state labeling plus shrink-to-owner discipline | prevents plans from acting like shipped law | include |
| Shared prompt source | `stdlib/rally/prompts/rally/*.prompt` | shared law stays in prompt source, generated readback stays derived | prevents prompt-law drift into docs or build outputs | include |
| Shared compile root | `pyproject.toml` | one declared shared prompt root for Rally stdlib modules | prevents hidden second prompt-source paths | include |
| Flow prompt source | `flows/single_repo_repair/prompts/**`, `flows/_stdlib_smoke/prompts/**` | consume shared Rally law only through real prompt owners | prevents flow-local drift and hidden source gaps | include |
| Generated readback | `flows/*/build/**` | inspect-after-rebuild only | prevents hand-written rival truth | include |
| Flow runtime contract | `flows/*/flow.yaml` | runtime facts only, including the required three-letter flow code | prevents docs-only runtime law | include |
| Setup scripts | `flows/*/setup/*.sh` | setup-only env contract separate from agent-facing law | prevents mixed path doctrine | include |
| Runtime owners | `src/rally/cli.py`, `src/rally/services/flow_loader.py` | docs must reflect what code actually enforces | prevents overclaim drift | include |
| Feature-local skills | `skills/repo-search/SKILL.md`, `skills/pytest-local/SKILL.md` | no repo-law restatement unless needed | avoids widening scope for no contract gain | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with the smallest credible signal. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Lock the owner map and lasting law homes

Goal
- Write the locked owner map into the lasting law homes and remove any ambiguity about who owns each Rally contract question.

Work
- Clean `AGENTS.md`, the master design, and this plan so they agree on:
  - repo-root rules
  - the shared prompt-root rule that already lives in `pyproject.toml`
  - owner-path rules
  - current-state versus target-state wording
  - the rule that this plan doc is temporary planning state, not a new lasting law home

Verification (smallest signal)
- Cold-read the law homes and confirm they tell the same story, and that their owner map still points at the existing shared prompt root in `pyproject.toml`.

Docs/comments (propagation; only if needed)
- None beyond the cleaned law homes in this phase.

Exit criteria
- The locked owner map is written plainly enough that later cleanup can converge every other file onto it without guessing.

Rollback
- Revert partial wording changes that create new rival law surfaces.

## Phase 2 - Clean the reader-facing and agent-facing contract surfaces

Goal
- Make `README.md`, shared prompt source, shared skills, and flow prompt source tell the same story as the lasting law homes.

Work
- Rewrite stale or rival wording in `README.md`, `stdlib/rally/prompts/rally/`, `skills/`, and `flows/*/prompts/**`.
- Restore `stdlib/rally/prompts/rally/currentness.prompt` at the exact shared owner path and align downstream flow prompt source with that surviving shared law.
- Rebuild affected generated readback if prompt source changes.

Verification (smallest signal)
- Recompile `_stdlib_smoke` and `single_repo_repair` and inspect representative generated readback.

Docs/comments (propagation; only if needed)
- Update only the touched live instruction surfaces. Delete stale wording instead of preserving it beside the new contract.

Exit criteria
- Reader-facing and agent-facing contract surfaces align with the owner map, the shared currentness source exists at the exact owner path, and no touched prompt surface still carries rival law.

Rollback
- Revert any prompt or skill edit that cannot be rebuilt or that weakens the owner split.

## Phase 3 - Clean active child docs and planning docs

Goal
- Stop active plans from overclaiming shipped behavior or acting like rival law surfaces.

Work
- Rewrite, shrink, or retire stale contract wording in active child docs and still-live planning docs.
- Make every surviving doc label current behavior versus target design clearly.

Verification (smallest signal)
- Cold-read the surviving docs against the owner map and confirm no current-state overclaim remains.

Docs/comments (propagation; only if needed)
- Delete stale plan-only law that has moved into lasting homes.

Exit criteria
- Surviving active docs add useful depth without answering the same law question differently.

Rollback
- Revert any cleanup that removes still-needed active detail before it has a surviving home.

## Phase 4 - Patch narrow owner-path contract holes exposed by the sweep

Goal
- Fix only the smallest real source-of-truth gaps that stop the repo from stating the law honestly.

Work
- Add the required three-letter `code` field to runnable `flows/*/flow.yaml` contracts, starting with `flows/single_repo_repair/flow.yaml`.
- Add `code` to `src/rally/domain/flow.py::FlowDefinition` and load and validate it in `src/rally/services/flow_loader.py`.
- Extend `tests/unit/test_flow_loader.py` so missing, malformed, and surfaced flow-code behavior is covered.
- Touch setup-script wording only if that narrow edit is still needed to keep the setup-only env lane honest.

Verification (smallest signal)
- Run `tests/unit/test_flow_loader.py`.
- Re-run `rally run single_repo_repair --brief-file ... --preflight-only` after the flow runtime contract changes.
- Re-run rebuild proof if prompt source changed in the same phase.

Docs/comments (propagation; only if needed)
- Sync any touched live docs or instruction surfaces in the same pass.

Exit criteria
- No known contract hole remains patched only in prose, and flow code no longer survives as docs-only law.

Rollback
- Revert any owner-path change that widens into harness work, new runtime modes, or non-requested feature scope.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Avoid verification bureaucracy. Prefer the smallest existing signal. Default to a few strong checks, not doc-policing machinery.

## 8.1 Unit tests (contracts)

- Run `tests/unit/test_flow_loader.py` when the flow-code owner path changes.
- Run targeted unit tests only if another real owner-path contract changes.
- Do not add doc-policing tests, stale-term greps, or repo-shape gates for this effort.

## 8.2 Integration tests (flows)

- Recompile affected flow prompt source and inspect representative generated readback whenever prompt source changes.
- Run `rally run single_repo_repair --brief-file ... --preflight-only` when `flow.yaml` or `flow_loader.py` changes.
- Use existing preflight or contract checks only where they prove a touched owner-path rule.

## 8.3 E2E / device tests (realistic)

- No E2E or device proof is needed unless the sweep lands a real runtime behavior change.
- The main non-code proof is a short cold-read contract pass across the surviving live law homes.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land this as a hard-cutover cleanup of live contract wording.
- Update or delete stale rival truth in the same pass instead of carrying mixed wording across releases.

## 9.2 Telemetry changes

- No new telemetry is planned for this work.

## 9.3 Operational runbook

- If prompt source changes, rebuild affected readback and inspect it.
- If the flow runtime contract changes, rerun the existing preflight path before closing the sweep.
- If the cleanup exposes a real source-of-truth gap that this pass cannot safely fix, stop and name the blocker plainly.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, `# 0)` through `# 10)`, and helper-block drift
  - owner-map consistency across Sections 3, 5, 6, and 7
  - verification and rollout alignment with the authoritative phase plan
- Findings summary:
  - Section 7 still spoke as if the owner map needed to be decided, even though Section 3 had already locked it.
  - Section 7 treated the known owner-path holes as generic examples instead of exact required work.
  - Sections 8 and 9 needed more exact proof signals to match the locked flow-code and shared-currentness work.
- Integrated repairs:
  - rewrote Phase 1 so it applies the locked owner map instead of re-deciding it
  - rewrote Phase 2 to restore `stdlib/rally/prompts/rally/currentness.prompt` explicitly and tied its proof to the two affected flow builds
  - rewrote Phase 4 to name the exact flow-code contract work and the exact proof path
  - tightened Sections 8 and 9 so verification and runbook steps match the authoritative checklist
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

## 2026-04-13 - Treat this as a docs-first law pass, not a harness effort

Context
- The user asked for a plan that makes Rally's conventions read like law across the whole repo.
- The user explicitly said they are not asking for harness work in this effort.

Options
- Add new enforcement harnesses, wrappers, or CI doc gates.
- Do a docs-and-contract convergence pass and allow only narrow owner-path edits if needed.

Decision
- Treat this as a docs-first and contract-first convergence effort.
- Do not add new harnesses, wrappers, grep gates, or repo-policing scripts.
- Allow only the smallest real owner-path edit when the repo cannot state the law honestly otherwise.

Consequences
- The work will focus on cleaning and aligning live law surfaces.
- The plan must distinguish source-of-truth cleanup from new runtime feature work.
- Some source-of-truth gaps may still need small edits, but only at the real owner path.

Follow-ups
- Confirm this North Star.
- Use later planning stages to make the owner map exhaustive and the change inventory complete.

## 2026-04-13 - Do not keep this plan doc as a permanent rival law surface

Context
- This command creates one canonical planning artifact.
- The user wants the repo itself to become clearer and more consistent, not to grow another lasting rules file.

Options
- Let this plan doc become another long-lived contract home.
- Use this plan doc to drive cleanup, then keep lasting truth in the surviving canonical homes.

Decision
- Treat this file as planning state only.
- Keep lasting law in `AGENTS.md`, the master design, reader-facing docs, prompt source, skills, and the real owning runtime contract surfaces.

Consequences
- Later cleanup must fold lasting truth back into the canonical homes.
- `arch-docs` or equivalent cleanup should retire or shrink plan-only law once the implementation is complete.

Follow-ups
- Confirm the owner map in later planning stages.
- Keep phase docs aligned or shrink them when their lasting law moves into the master design.

## 2026-04-13 - Keep one surviving owner per rule and split setup-only paths from agent-facing note law

Context
- The research pass showed that Rally already has stable law homes, but several contract questions still require cross-reading.
- The same pass also exposed two real owner-path gaps:
  - docs require a three-letter flow code, but `flow.yaml` and `flow_loader.py` do not own it yet
  - prompt source and docs depend on shared currentness law, but the checked-in `currentness.prompt` source is missing
- The setup script uses `RALLY_FLOW_HOME` and `RALLY_ISSUE_PATH`, while the shared agent-facing note law uses `RALLY_RUN_ID` plus `rally issue note`

Options
- Keep letting docs and plans answer these gaps with prose only.
- Add new enforcement harnesses or doc-policing machinery.
- Keep the cleanup docs-first, but require narrow owner-path fixes where the repo cannot state the law honestly.

Decision
- Keep one surviving owner path per contract question.
- Treat setup-only env vars and agent-facing note-write law as two separate lanes that must be stated separately.
- Treat shared currentness law as a repo-owned shared prompt surface with one honest checked-in owner path at `stdlib/rally/prompts/rally/currentness.prompt`.
- Treat flow code as a `flow.yaml` contract that must also be represented in `FlowDefinition` and validated in `flow_loader.py`, not as a docs-only rule.

Consequences
- Later stages must audit docs and prompt surfaces against this owner map instead of just tightening wording.
- Later stages need a real shared-source fix for `currentness.prompt`, not just doc cleanup.
- Later stages need a real owner-path fix for flow code, not just doc cleanup.

Follow-ups
- Use `phase-plan` to turn these owner-path decisions into an implementation checklist.
- Keep the controller on the same doc and let later deep-dive and phase-plan work finish the delete-or-rewrite inventory.

## 2026-04-13 - Use the existing shared prompt compile root as part of the law

Context
- Live flow prompt source already imports `rally.currentness`.
- `pyproject.toml` already declares `tool.doctrine.compile.additional_prompt_roots = ["stdlib/rally/prompts"]`.
- That means Rally already has a real checked-in compile-root contract for shared prompt modules.

Options
- Treat the missing `currentness.prompt` file as a docs-only problem.
- Add a second shared prompt root or another side-door source path.
- Use the existing shared prompt root as the exact owner lane and restore the missing module there.

Decision
- Keep `stdlib/rally/prompts` as the one shared Rally prompt root.
- Treat `stdlib/rally/prompts/rally/currentness.prompt` as the exact owner path for shared currentness law.
- Do not introduce a second shared prompt root, generated-only owner, or doc-only fallback.

Consequences
- Prompt-law cleanup stays on the existing Doctrine path instead of inventing Rally-specific indirection.
- Any prompt-source fix must rebuild flow readback from the existing compile root.

Follow-ups
- Carry this owner path into `phase-plan`.
- Keep generated readback inspection as proof, not as authored source.
