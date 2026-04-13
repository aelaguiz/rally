---
title: "Rally - Base Agent, Final Output, and Note Pivot - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - stdlib/rally/prompts/rally/turn_results.prompt
  - flows/_stdlib_smoke/prompts/AGENTS.prompt
  - flows/single_repo_repair/prompts/AGENTS.prompt
  - src/rally/services/flow_loader.py
  - src/rally/domain/turn_result.py
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
---

# TL;DR

Outcome
- Pivot Rally cleanly from the old authored note-and-handoff model to the new split model: every Rally agent inherits one Rally stdlib abstract base agent, uses one always-present Rally kernel skill for durable notes and end-turn help, writes durable notes only through Rally CLI, and ends turns only through schema-valid final JSON that Rally alone uses for routing, done, blocker, or sleep control.

Problem
- The repo is currently split across two communication models. The design docs now say final JSON is the only control surface and notes are durable context only, but the checked-in stdlib and flow doctrine still import shared note and handoff outputs, while the runtime domain and loader already assume `handoff` plus structural `next_owner` in the validated turn result.

Approach
- Add one Rally stdlib abstract base agent that all Rally agents must inherit from.
- Put the shared Rally doctrine there: what Rally is, the invariant that routing lives only in final JSON, the instruction to use the Rally kernel skill, and the run-identity contract for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
- Author the Rally kernel skill as a real skill package using the `skill-authoring` contract, and keep it thin: it teaches durable-note writes through `"$RALLY_BASE_DIR/rally" issue note` and helps the agent shape schema-valid final JSON without creating a second return path.
- Keep `rally.turn_results` as the shared machine control contract, and delete the old `issue_ledger` / `notes` / `handoffs` authored output path instead of hardening it further.
- Migrate `_stdlib_smoke` and `single_repo_repair` to inherit the new base agent and to stop depending on authored note or handoff outputs.
- Implement the missing Rally-owned runtime surfaces that this authored model requires: env injection plus the shared `"$RALLY_BASE_DIR/rally" issue note` CLI mutation path.

Plan
- Phase 1 authors the stdlib base agent, the Rally kernel skill contract, and the final-output wording/schema alignment.
- Phase 2 migrates the authored flow doctrine and compiled readback away from shared note and handoff outputs.
- Phase 3 lands the Rally-owned note CLI, run-resolution, append ordering, and env-injection runtime seams.
- Phase 4 reconciles docs, loader/runtime assumptions, and proof surfaces so the repo has one honest starting point for the broader runnable runtime work.

Non-negotiables
- There is no separate authored handoff object.
- Durable notes never decide ownership, done, blocker, or sleep state.
- The only turn-ending control surface is the adapter's strict final JSON return path.
- Every Rally-managed agent must inherit the Rally stdlib base agent.
- Every Rally-managed agent must have the Rally kernel skill available.
- Agents must not mutate `home/issue.md` directly.
- If Doctrine support is missing for the clean design, Rally stops and asks for Doctrine support first rather than adding a Rally-side workaround.

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

Rally can replace the old authored note-and-handoff communication model with one cleaner split without losing durable context or route clarity:

- every Rally-managed agent inherits one Rally stdlib abstract base agent
- agents use one always-present Rally kernel skill for note writes and end-turn help
- durable notes go only through `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`
- routing and terminal control come only from validated final JSON
- Rally records normalized readback into `home/issue.md`, but that ledger readback is not a second return path

This claim is false if any of the following remain true after the pivot lands:

- a Rally flow still requires a separate authored handoff output to route work
- a Rally agent can route or stop a run through note prose or ledger prose instead of final JSON
- a Rally flow agent does not inherit the shared Rally base agent
- an agent can only learn how to leave notes by repo-local prompt prose instead of the shared Rally kernel skill
- `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` are not injected on every Rally-managed agent launch
- the shared note write path is still "edit `issue.md` directly" instead of Rally CLI

## 0.2 In scope

- one Rally stdlib abstract base agent under `stdlib/rally/prompts/rally/`
- required inheritance of that base agent by Rally-managed concrete agents
- shared Rally doctrine in that base agent covering:
  - what Rally is
  - that final JSON is the only routing and stop/sleep control surface
  - that durable notes use the Rally kernel skill plus Rally CLI
  - how to read run identity from `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`
- encoding the base agent run-identity contract through inherited `EnvVar` inputs for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`
- one Rally kernel skill under `skills/` authored as a real skill package using `skill-authoring`
- the kernel skill contract for:
  - durable note writes via `"$RALLY_BASE_DIR/rally" issue note`
  - end-turn final-JSON help without creating a second return path
- deleting the old shared note and handoff outputs from the authored stdlib
- updates to `_stdlib_smoke` and `single_repo_repair` so they inherit the base agent and stop depending on authored note/handoff outputs
- Rally-owned runtime work needed for the new model:
  - `"$RALLY_BASE_DIR/rally" issue note`
  - run-id-based note resolution
  - validated note append ordering
  - `RALLY_BASE_DIR` / `RALLY_RUN_ID` / `RALLY_FLOW_CODE` injection
- compiled readback regeneration for affected flows after the Doctrine source changes
- docs alignment across the master design, the phase-3 child doc, and the phase-4 child doc

## 0.3 Out of scope

- a second runtime adapter
- a second user-facing note API beyond `"$RALLY_BASE_DIR/rally" issue note`
- parallel-agent execution, multi-owner routing, or any concurrency extension beyond the current single-owner turn contract
- human handoff, pickup, or takeover primitives
- direct agent writes to `home/issue.md`
- broad Phase 4 runner completion beyond the seams this pivot directly requires
- a Rally-specific Doctrine fork or Rally-side compiler workaround for missing generic language support
- widening the kernel skill into a general Rally operator manual

## 0.4 Definition of done (acceptance evidence)

- A Rally stdlib abstract base agent exists and concrete Rally agents inherit from it in `_stdlib_smoke` and `single_repo_repair`.
- The base agent doctrine explains Rally's communication model, the Rally kernel skill, and the `RALLY_BASE_DIR` / `RALLY_RUN_ID` / `RALLY_FLOW_CODE` run-identity contract.
- The Rally kernel skill exists as a real `SKILL.md` package and is clearly the shared note/write and end-turn-help surface.
- `stdlib/rally/prompts/rally/turn_results.prompt`, `src/rally/domain/turn_result.py`, and `src/rally/services/flow_loader.py` all agree that `handoff` requires structural `next_owner`.
- Rally no longer expects authored note or handoff outputs to carry route truth in `_stdlib_smoke` and `single_repo_repair`.
- `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"` exists as the canonical durable-note write path and supports stdin, file-path, and inline-text input.
- Runtime launch surfaces inject `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` for every Rally-managed agent process.
- The affected flows are recompiled with the paired Doctrine compiler and the generated readback reflects the new authored source.
- The master design and child docs stop blurring ledger readback with turn-control semantics.

## 0.5 Key invariants (fix immediately if violated)

- Route from validated final JSON, never from note prose.
- Notes preserve durable context only.
- Ledger readback in `home/issue.md` is a human-readable record, not a second return path.
- Every Rally-managed agent inherits the shared Rally base agent.
- The Rally kernel skill is always present for Rally-managed agents and is the only shared note/end-turn helper surface.
- `rally-kernel` is Rally-managed ambient capability and should not need per-flow `allowed_skills` entries in `flow.yaml`.
- Currentness stays typed and singular: one current artifact or `current none`, with no route truth on the currentness carrier.
- Agents fail loud if the required run-identity env vars are missing instead of guessing the active run.
- Rally owns note target resolution, append ordering, and issue-history snapshots.
- Superseded authored communication surfaces are deleted from the repo; git is the only archive.
- Doctrine stays generic: abstract-agent inheritance, `EnvVar` inputs, routed final-output semantics, and emitted metadata belong in Doctrine only when they are generic compiler capabilities.
- Rally does not paper over missing Doctrine support with Markdown scraping, side-door prompts, or repo-local hacks.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep one clean communication model: final JSON for control, notes for durable context.
2. Make the shared Rally agent contract explicit and inherited, not repeated ad hoc in every flow.
3. Keep the Rally kernel skill leverage-first and thin, per `skill-authoring`, instead of turning it into a giant repo manual.
4. Preserve the Doctrine/Rally ownership boundary rather than hiding missing support in runtime hacks.
5. Keep the runtime mutation surface shared between agents and operators through Rally CLI.

## 1.2 Constraints

- Doctrine already supports `abstract agent` inheritance and inherited shared doctrine across module boundaries.
- Doctrine already supports `EnvVar` input sources, but not a separate agent-level env metadata surface.
- Rally runtime code already enforces `handoff` plus `next_owner` in the parsed turn-result domain and in flow-loader schema validation.
- Rally runtime code does not yet implement `"$RALLY_BASE_DIR/rally" issue note`, note append behavior, or launch-time env injection.
- Current authored stdlib and flow prompt surfaces still import and depend on `issue_ledger`, `notes`, `handoffs`, and `currentness` in their older form.
- The repo already compiles and consumes `AGENTS.contract.json`; this pivot cannot assume a different emitted contract name unless Doctrine changes generically and Rally adopts it honestly.

## 1.3 Architectural principles (rules we will enforce)

- Put shared Rally agent doctrine in one stdlib abstract base agent, not in `flow.yaml`, not in repo-root Markdown, and not in duplicated flow-local prose.
- Author the Rally kernel skill as a real skill using the `skill-authoring` contract.
- Keep the base agent abstract and inheritance-only; concrete flow agents still own flow-specific role, workflow, inputs, outputs, and routing.
- Keep run identity explicit and typed where possible. Default to inherited `EnvVar` inputs if that keeps the contract cleaner.
- Keep final-output routing structural. Use `route.next_owner.key` for machine routing and never route from human-readable ledger prose.
- Delete superseded authored communication surfaces completely; do not archive them in-repo, keep compatibility stubs, or leave mixed models alive.

## 1.4 Known tradeoffs (explicit)

- Modeling `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` as inherited `EnvVar` inputs strengthens the authored contract, but it also means every Rally agent carries a small amount of runtime-facing input doctrine.
- Keeping `handoff` as the final-result branch label is acceptable if the docs and runtime are explicit that it is not an authored handoff artifact.
- The first pass of the base agent should stay thin. If it absorbs too much flow-specific policy, it will become a disguised repo manual instead of a shared stdlib abstraction.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` and `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md` already describe the target split: final JSON for control, notes for durable context, no separate authored handoff object.
- Doctrine already supports the generic authoring features the pivot wants: abstract-agent inheritance, cross-module inheritance, final-output metadata, routed owner reads, and `EnvVar` inputs.
- Rally runtime code already has partial Phase 1 surfaces under `src/rally/`, including:
  - a parsed turn-result domain with `handoff`, `done`, `blocker`, and `sleep`
  - a flow loader that consumes compiled `AGENTS.contract.json`
  - schema validation that already rejects `handoff` branches without `next_owner`
- The authored stdlib still carries the older communication model:
  - `issue_ledger.prompt` as a shared ledger target
  - `notes.prompt` as an authored note output
  - `handoffs.prompt` as authored route/currentness carriers
  - `currentness.prompt` wired directly to those handoff outputs
- `_stdlib_smoke` and `single_repo_repair` still import and emit those shared note/handoff outputs.

## 2.2 What’s broken / missing (concrete)

- `stdlib/rally/prompts/rally/turn_results.prompt` still says `handoff` should be used only when the turn also emitted a separate authored handoff output.
- `stdlib/rally/prompts/rally/currentness.prompt` still treats shared handoff outputs as the trustworthy currentness carrier.
- There is no shared Rally base agent, so the core Rally doctrine is still distributed across design docs and flow-local prompt text instead of inherited from the stdlib.
- There is no shipped Rally kernel skill yet.
- `src/rally/cli.py` exposes only `run` and `resume` preflight/error surfaces; it has no `issue note` command.
- `src/rally/services/issue_ledger.py`, `src/rally/adapters/codex/launcher.py`, `src/rally/adapters/codex/result_contract.py`, and `src/rally/services/runner.py` are still placeholder boundaries.
- The design docs still have some wording that can blur "ledger readback" with "turn control surface," especially when they render `handoff` records into `issue.md`.

## 2.3 Constraints implied by the problem

- The pivot must change authored doctrine and runtime seams together, because the repo already contains partial runtime code that assumes the newer final-result model.
- The cleanest authored solution is available now: use Doctrine abstract-agent inheritance instead of inventing a Rally-only notion of "base agent."
- The plan must preserve the Rally/Doctrine boundary: generic authoring and emitted metadata stay in Doctrine; note resolution, note writes, and ledger ordering stay in Rally.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- No external research is needed for this pass. The parallel-agent question is governed by repo-local Rally design docs plus the paired local Doctrine language and example corpus.
- Reject using Doctrine's compiler-side batch parallelism as evidence for runtime agent parallelism. `../doctrine/docs/README.md` and `../doctrine/CONTRIBUTING.md` talk about shared compile sessions and safe batch fanout in the compiler, not authored multi-owner turn semantics or Rally runtime concurrency.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
    - already defines Rally v1 as one active run per flow, one active owner at a time, and explicitly keeps parallel-agent execution out of scope while route truth comes only from the validated final turn result.
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
    - keeps the vertical slice intentionally narrow to one active owner at a time and explicitly excludes parallel-agent execution from the current runtime scope.
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
    - is the clearest Rally statement that durable notes are context only, while one structured final turn result is the only route and terminal control surface.
  - `stdlib/rally/prompts/rally/turn_results.prompt`
    - still carries stale wording that assumes a separate authored handoff output even though the intended control model is one final JSON result.
  - `stdlib/rally/schemas/rally_turn_result.schema.json`
    - already defines a singular `handoff` branch with one required `next_owner`, not a fanout or multi-owner route shape.
  - `src/rally/domain/turn_result.py`
    - already parses the runtime result as one of `handoff`, `done`, `blocker`, or `sleep`, with `handoff` requiring one `next_owner`.
  - `src/rally/services/flow_loader.py`
    - already rejects any final-result schema whose `handoff` branch does not require `next_owner`.
  - `src/rally/cli.py`
    - proves the runtime CLI surface exists today, but still lacks the shared `issue note` mutation path this plan needs.
  - `src/rally/services/issue_ledger.py`, `src/rally/services/runner.py`, `src/rally/adapters/codex/launcher.py`, `src/rally/adapters/codex/result_contract.py`
    - remain placeholder ownership boundaries, so note writes, ledger ordering, launch env injection, and routed wake behavior are still to be implemented.

- Canonical path / owner to reuse:
  - `../doctrine/docs/LANGUAGE_REFERENCE.md`, `../doctrine/docs/WORKFLOW_LAW.md`, `../doctrine/docs/AGENT_IO_DESIGN_NOTES.md`
    - Doctrine owns the authored route semantics. The shipped route surface is singular: `route "..." -> Agent` authored lines, derived `route.next_owner`, and `final_output:` attached to one emitted `TurnResponse`.
  - `src/rally/domain/turn_result.py` plus `src/rally/services/flow_loader.py`
    - Rally already owns the runtime interpretation of that singular routed result and should continue to do so instead of inventing a parallel-owner shadow contract in this pivot.

- Existing patterns to reuse:
  - `../doctrine/examples/04_inheritance/prompts/AGENTS.prompt`
    - imported abstract-agent inheritance is a shipped pattern, so the Rally stdlib base agent can be a real inherited Doctrine surface rather than flow-local duplicated prose.
  - `../doctrine/examples/08_inputs/prompts/AGENTS.prompt`
    - `EnvVar` inputs are already shipped and are the cleanest current authored surface for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
  - `../doctrine/examples/87_workflow_route_output_binding/prompts/AGENTS.prompt`
    - ordinary workflow-law outputs already bind one routed owner through compiler-owned `route.next_owner` and `route.next_owner.key`.
  - `../doctrine/examples/89_route_only_shared_route_semantics/prompts/AGENTS.prompt`
    - route-only local ownership still resolves one routed owner through `route.exists` and `route.next_owner`; it does not introduce multi-owner or parallel wake semantics.
  - `../doctrine/examples/90_split_handoff_and_final_output_shared_route_semantics/prompts/AGENTS.prompt`
    - Doctrine already supports the exact split Rally wants: one durable review carrier plus one separate schema-backed `final_output:` that consumes the same routed-owner semantics.
  - `../doctrine/docs/WORKFLOW_LAW.md` plus `../doctrine/docs/AGENT_IO_DESIGN_NOTES.md`
    - currentness in shipped Doctrine examples is still singular and trust-surface based: one current artifact or `current none`, not parallel branch-local currentness across multiple simultaneously active owners.

- Prompt surfaces / agent contract to reuse:
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
    - remains the smallest Rally proof surface and currently still imports the old shared note and handoff outputs.
  - `flows/single_repo_repair/prompts/AGENTS.prompt`
    - is the real Rally flow that still depends on the older authored note and handoff model and therefore must be cut over rather than widened for concurrency.
  - `flows/single_repo_repair/flow.yaml`
    - defines one roster, per-agent allowlists, and adapter args, but no concurrency or multi-owner runtime contract.

- Native model or agent capabilities to lean on:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
    - the Codex adapter already has a strict schema-backed final-output path, so this pivot can keep one end-of-turn control result instead of inventing deterministic orchestration or note-based fanout.

- Existing grounding / tool / file exposure:
  - `skills/repo-search/SKILL.md` and `skills/pytest-local/SKILL.md`
    - current Rally skills are per-turn execution helpers, not shared coordination surfaces between parallel owners.
  - `mcps/fixture-repo/server.toml`
    - current MCP materialization is likewise per-run and single-home, with no parallel-owner coordination layer.

- Duplicate or drifting paths relevant to this change:
  - `stdlib/rally/prompts/rally/{issue_ledger,notes,handoffs,currentness}.prompt`
    - the older authored note and handoff path is still live and drifts against the newer single-result routing model already enforced in runtime code.
  - Rally master and Phase 4 docs versus the current authored stdlib
    - repo truth already says one active owner and validated final JSON only, while the authored prompts still imply a second handoff carrier.

- Capability-first opportunities before new tooling:
  - finish the base-agent plus kernel-skill pivot on top of the existing single-owner routed final-output contract before inventing any concurrency scaffolding.
  - do not introduce concurrency scaffolding, extra note artifacts, or Rally-only shadow fields in this pivot.

- Behavior-preservation signals already available:
  - `tests/unit/domain/test_turn_result_contracts.py`
    - protects the current singular runtime turn-result parsing contract.
  - `tests/unit/test_flow_loader.py`
    - protects final-output contract loading and the requirement that `handoff` carry `next_owner`.
  - `../doctrine/docs/WORKFLOW_LAW.md` and `../doctrine/examples/{87_workflow_route_output_binding,89_route_only_shared_route_semantics,90_split_handoff_and_final_output_shared_route_semantics}/...`
    - are the shipped proof corpus for the current single-owner route semantics this plan should reuse instead of widening.

## 3.3 Decision gaps that must be resolved before implementation

No unresolved plan-shaping decisions remain in this artifact. This pass resolved the architecture choices that matter before implementation:

- Keep `stdlib/rally/prompts/rally/currentness.prompt` as the surviving typed currentness surface, but rewrite it so it carries only one current artifact or `current none` and never carries routing or ownership truth.
- Require the Rally base agent to inherit `EnvVar` inputs for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` rather than leaving that contract as prose-only doctrine.
- Keep `handoff` as the branch label in `rally.turn_results`; narrow its meaning to “route to the next owner through final JSON” and do not widen this pivot into a rename.
- Keep parallel-agent execution out of this plan entirely. The only requirement this plan needs is a clear single-owner boundary with no concurrency shim or pseudo-parallel contract.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `stdlib/rally/prompts/rally/` contains:
  - `turn_results.prompt`
  - `issue_ledger.prompt`
  - `notes.prompt`
  - `handoffs.prompt`
  - `currentness.prompt`
- `flows/_stdlib_smoke/prompts/AGENTS.prompt` and `flows/single_repo_repair/prompts/AGENTS.prompt`
  - import and emit the old shared note/handoff doctrine.
- `flows/*/build/agents/*/AGENTS.md` and `AGENTS.contract.json`
  - are the compiled readback that Rally runtime currently consumes.
- `skills/`
  - currently contains `repo-search/`, `pytest-local/`, and the newly drafted `rally-kernel/` skill package, but the authored flows do not yet depend on that shared skill contract.
- `src/rally/`
  - contains a partial runtime with loader/domain/test scaffolding but not the note-write or launch/injection implementation yet.

## 4.2 Control paths (runtime)

- Concrete flow agents emit schema-backed `TurnResponse` final outputs.
- Rally flow loading resolves compiled per-agent final-output contracts through `AGENTS.contract.json`.
- Flow loading rejects a handoff schema that does not require `next_owner`.
- Runtime note writes, env injection, adapter launch, and ledger append ordering are not yet implemented.
- The current routed-control model is singular at every layer:
  - Doctrine authored route semantics lower one `route.next_owner`
  - Rally turn-result schema carries one `next_owner`
  - Rally runtime parsing accepts one routed owner
- There is no current runtime surface for:
  - waking multiple owners from one turn
  - carrying multiple routed owners in final JSON
  - running multiple active owners in one Rally run home
  - reconciling currentness across parallel branches

## 4.3 Object model + key abstractions

- Runtime domain:
  - `TurnResultKind`
  - `HandoffTurnResult`
  - `DoneTurnResult`
  - `BlockerTurnResult`
  - `SleepTurnResult`
- Flow loading:
  - `FlowDefinition`
  - `FlowAgent`
  - `CompiledAgentContract`
  - `FinalOutputContract`
- Authored shared communication model:
  - `RallyIssueLedgerAppend`
  - `RallyIssueNote`
  - `RallyCurrentArtifactHandoff`
  - `RallyNoCurrentArtifactHandoff`
- Currentness semantics today are still effectively singular:
  - one current artifact or `current none`
  - trusted currentness is carried on shared handoff outputs today
  - no separate branch-scoped currentness abstraction exists in Rally or Doctrine
- Authored/runtime route contract today:
  - one concrete turn emits one final `TurnResponse`
  - one routed branch may bind one structural `next_owner`
  - one run keeps one active owner at a time per current Rally design doctrine

## 4.4 Observability + failure behavior today

- Loader preflight already fails loud when compiled contracts are missing or when the handoff result schema does not require `next_owner`.
- There is no runtime proof surface yet for:
  - `RALLY_BASE_DIR` / `RALLY_RUN_ID` / `RALLY_FLOW_CODE` injection
  - note writes through Rally CLI
  - note-before-final-response ledger ordering
  - issue-history snapshots after note appends
- There is also no proof surface or design contract yet for parallel-owner behavior, because Rally docs still explicitly exclude parallel-agent execution from the current runtime scope.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Add one new stdlib prompt module for the Rally base agent under `stdlib/rally/prompts/rally/`.
- Add one Rally kernel skill package under `skills/`.
- Delete the old authored communication modules under `stdlib/rally/prompts/rally/` once the new model is in place.
- Regenerate the affected compiled readback under:
  - `flows/_stdlib_smoke/build/agents/*`
  - `flows/single_repo_repair/build/agents/*`

## 5.2 Control paths (future)

- Concrete Rally agents inherit the Rally stdlib abstract base agent.
- The base agent carries shared Rally doctrine and the run-identity contract.
- Concrete agents still emit their flow-owned artifacts and one final turn result.
- When an agent wants to preserve durable context, it uses the Rally kernel skill, which invokes `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`.
- Rally runtime resolves the run from the supplied run id, validates the target ledger, appends the note, and snapshots history.
- The adapter returns one strict final JSON result through the declared final-output schema.
- Rally validates that JSON, appends normalized readback into `home/issue.md`, and routes only from structural `next_owner`.
- This pivot stays on one-owner-at-a-time execution:
  - one active owner per run turn
  - one routed `next_owner` in the final JSON contract
  - one wake target after each routed turn
- Parallel-agent execution is out of scope for this target architecture.

## 5.3 Object model + abstractions (future)

- One Rally stdlib abstract base agent:
  - shared Rally doctrine
  - shared run-identity contract
  - shared instruction to use the Rally kernel skill
- One Rally kernel skill:
  - note helper
  - end-turn helper
  - no direct file mutation
  - no route authority
- One shared final-output contract in `rally.turn_results`
- One surviving typed currentness helper in `currentness.prompt`:
  - one current artifact or `current none`
  - no `next_owner`
  - no routing authority
  - no branch fanout semantics
- Optional inherited `EnvVar` inputs on the base agent for:
  - `RALLY_BASE_DIR`
  - `RALLY_RUN_ID`
  - `RALLY_FLOW_CODE`
- One Rally CLI note-write surface:
  - stdin
  - `--file`
  - `--text`
- One tiny Rally internal adapter-backed strict-JSON helper seam for low-thinking maintenance tasks, not for routing or note writes
- Explicit non-goal for this target model:
  - no multi-owner `next_owners`
  - no fanout handoff object
  - no parallel currentness carrier
  - no second coordination channel beyond notes plus the final turn result

## 5.4 Invariants and boundaries

- The base agent is authored doctrine and belongs in the Rally stdlib, not in runtime config.
- The kernel skill is agent UX and belongs in `skills/`, not in flow-local prompt prose.
- `flow.yaml` continues to own runtime adapter settings and allowlists only.
- `flow.yaml` continues to own runtime adapter settings and flow-local allowlists. `rally-kernel` is Rally-provided ambient capability, not a per-flow allowlist entry.
- Doctrine owns abstract-agent inheritance, `EnvVar` inputs, routed final-output semantics, and emitted final-output metadata when they are generic features.
- Rally owns run resolution, note writes, ledger append ordering, issue-history snapshots, env injection at launch, and route dispatch from validated final JSON.
- There is no shared authored note output target and no shared authored handoff output target after cutover.
- No parallel runtime path, shadow route contract, or multi-owner compatibility shim is allowed in this pivot.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

This first-pass table is the initial change map and will need a deeper exhaustive sweep before implementation.

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stdlib final output | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultJson` explanation | Says `handoff` depends on a separate authored handoff output | Rewrite to final-JSON-only control contract | Remove mixed-model instruction | Shared final-output contract only | Flow compile checks, loader tests |
| Stdlib note model | `stdlib/rally/prompts/rally/issue_ledger.prompt` | `RallyIssueLedgerAppend` | Defines authored ledger target | Delete from the authored path | Notes move to Rally CLI | No authored ledger target for notes | Flow compile checks |
| Stdlib note model | `stdlib/rally/prompts/rally/notes.prompt` | `RallyIssueNote` | Notes are authored outputs | Delete from the authored path | Notes move to kernel skill + CLI | Kernel skill + `"$RALLY_BASE_DIR/rally" issue note` | Flow compile checks |
| Stdlib handoff model | `stdlib/rally/prompts/rally/handoffs.prompt` | shared handoff outputs | Carries trusted `next_owner` and currentness | Delete the shared handoff outputs and replace their surviving currentness role with a non-handoff typed currentness surface | Route truth must leave the authored handoff object entirely | No shared authored handoff object | Flow compile checks |
| Stdlib currentness model | `stdlib/rally/prompts/rally/currentness.prompt` | currentness conventions | Imports shared handoff outputs and treats them as the trustworthy currentness carrier | Keep the module but rewrite it as a singular non-routing currentness helper with no owner field | Currentness should stay typed without preserving the old handoff contract | One current artifact or `current none`, no route truth | Flow compile checks |
| Stdlib base doctrine | `stdlib/rally/prompts/rally/` | new base-agent module | No shared Rally base agent exists | Add abstract base agent | All Rally agents must inherit one shared contract | Abstract base agent + optional `EnvVar` inputs | Doctrine compile/readback inspection |
| Skill package | `skills/rally-kernel/SKILL.md` | new shared Rally kernel skill | No shared Rally kernel skill exists | Author one lean self-contained skill using `$skill-authoring` and ship `SKILL.md` first | Shared reusable note/end-turn UX should not live in flow-local prose | `rally-kernel` skill package | Skill readback review plus flow compile inspection |
| Runtime scope boundary | `flows/single_repo_repair/flow.yaml` and design docs | run roster / owner model | Current repo doctrine is singular-owner, but that rule is not yet called out in every relevant section of this plan | Keep one-owner-at-a-time explicit and do not add concurrency config or multi-owner routing to this pivot | Prevent accidental widening from “parallel agents” discussion into shipped scope | Single active owner + singular `next_owner` | Doc sync plus existing route-contract tests |
| Flow doctrine | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | agent declarations | Emits shared note/handoff outputs directly | Inherit new base agent and remove old note/handoff outputs | Smoke should prove the new model | Base-agent inheritance + final JSON only | Recompile smoke flow |
| Flow doctrine | `flows/single_repo_repair/prompts/AGENTS.prompt` | agent declarations | Emits shared note/handoff outputs directly | Inherit new base agent and remove old note/handoff outputs | Real Rally flow should match target model | Base-agent inheritance + final JSON only | Recompile real flow |
| Role prose | `flows/single_repo_repair/prompts/roles/*.prompt` | handoff/note wording | Still references artifacts or handoffs as note alternatives | Rewrite to kernel-skill and final-JSON model | Keep flow-local doctrine honest | Shared base agent + kernel skill wording | Flow compile/readback inspection |
| Runtime CLI | `src/rally/cli.py` | subcommands | No `issue note` surface | Add `rally issue note` | Shared mutation path for agents and operators | `"$RALLY_BASE_DIR/rally" issue note --run-id ...` | New CLI/unit tests |
| Runtime ledger | `src/rally/services/issue_ledger.py` | note append service | Stub only | Implement run resolution, append validation, and snapshots | Rally owns note writes and ordering | Ledger service | New service/unit tests |
| Runtime launch | `src/rally/adapters/codex/launcher.py` | launch contract | Stub only | Inject `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` | Base-agent and skill doctrine rely on it | Adapter launch env contract | New adapter/unit tests |
| Runtime docs/loader | `src/rally/services/flow_loader.py` and docs | final-output assumptions | Already assumes `handoff` + `next_owner`, but docs/readback still mixed | Keep loader strict and update docs around it | Remove repo-level contradiction | Final JSON is only route truth | Existing flow-loader tests plus doc sync |

## 6.2 Migration notes

- Canonical owner path:
  - stdlib abstract base agent for shared Rally agent doctrine
  - Rally kernel skill for agent-facing note/end-turn UX
  - `rally.turn_results` for machine control
  - Rally CLI/runtime for note writes and ledger ordering
- Delete list:
  - authored note output targets
  - authored handoff output targets
  - any currentness wording that still says `next_owner` or routing truth lives on a currentness carrier
  - any wording in this plan or related live docs that implies parallel wake, multi-owner route fanout, or a second coordination channel for this pivot
  - stale flow-local wording that suggests direct `issue.md` mutation or separate handoff artifacts
- Capability-replacing harnesses to delete or justify:
  - do not add orchestration wrappers, sidecar coordinators, or note-driven fanout logic to simulate parallel-agent execution in this pivot
- Live docs/instructions to update:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- Behavior-preservation signals:
  - Doctrine recompilation of affected flows
  - inspection of generated `AGENTS.md` and `AGENTS.contract.json`
  - existing Rally flow-loader and turn-result contract tests

## 6.3 Draft artifact path

- Draft the first-pass kernel skill directly on disk at `skills/rally-kernel/SKILL.md`.
- Keep the package lean per `$skill-authoring`: `SKILL.md` first, no `references/`
  or `scripts/` until review or execution failures prove they are needed.

## 6.4 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared agent contract | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | inherit one Rally stdlib base agent and remove authored note/handoff outputs | keeps the smallest Rally proof surface aligned with the new shared contract | include |
| Shared agent contract | `flows/single_repo_repair/prompts/AGENTS.prompt` | inherit one Rally stdlib base agent and remove authored note/handoff outputs | keeps the real Rally flow on the same contract as the smoke flow | include |
| Shared runtime communication | `flows/single_repo_repair/prompts/roles/*.prompt` | route through kernel-skill note path plus final JSON only | avoids flow-local drift back into handoff prose or direct file mutation | include |
| Shared runtime boundary | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` | keep the pivot explicitly single-owner | prevents the “parallel agents” research from silently widening live docs or future implementation scope | include |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with the smallest credible signal. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1: Land the shared stdlib contract

Status: COMPLETE

Goal
- Replace the mixed authored communication model with one shared Rally-owned authored contract before touching flow-local adopters.

Work
- Add the Rally stdlib abstract base agent under `stdlib/rally/prompts/rally/`.
- Encode inherited `EnvVar` inputs for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` on that base agent.
- Finalize the lean `skills/rally-kernel/SKILL.md` package using `$skill-authoring` as the shared note/end-turn helper surface.
- Rewrite `stdlib/rally/prompts/rally/turn_results.prompt` so `handoff` means only structural routing through final JSON.
- Rewrite `stdlib/rally/prompts/rally/currentness.prompt` so it remains typed but singular and non-routing.
- Delete `stdlib/rally/prompts/rally/notes.prompt` and `stdlib/rally/prompts/rally/handoffs.prompt` from the authored path once the replacement contract is in place.

Completed work:
- Added `stdlib/rally/prompts/rally/base_agent.prompt` with inherited env-var inputs for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`.
- Rewrote `turn_results.prompt` to remove the authored-handoff dependency and rewrote `currentness.prompt` around a non-routing `TurnResponse` currentness carrier.
- Deleted `notes.prompt`, `handoffs.prompt`, and the now-unused authored `issue_ledger.prompt`.
- Updated `skills/rally-kernel/SKILL.md` to state that Rally provides the skill automatically on Rally-managed turns instead of requiring per-flow allowlist entries.

Verification (smallest signal)
- Recompile `_stdlib_smoke` with the paired Doctrine compiler and inspect one representative generated agent for:
  - inherited base-agent doctrine
  - inherited env-var inputs
  - final-output contract still bound to the shared Rally turn-result schema

Docs/comments (propagation; only if needed)
- Update the master and phase-3 docs so they describe the new base-agent requirement and the surviving typed-currentness rule.

Exit criteria
- The Rally base agent, kernel skill, surviving currentness surface, and rewritten `rally.turn_results` contract all exist and there are no authored shared note/handoff outputs left in the stdlib path.

Rollback
- Revert the stdlib and skill changes together; do not leave a half-migrated authored contract in place.

## Phase 2: Cut Rally-managed flows over to the new authored model

Status: COMPLETE

Goal
- Move concrete Rally flows onto the new stdlib contract and remove the last flow-local dependencies on authored note/handoff outputs.

Work
- Migrate `flows/_stdlib_smoke/prompts/AGENTS.prompt` to inherit the new base agent and stop emitting shared note/handoff outputs.
- Migrate `flows/single_repo_repair/prompts/AGENTS.prompt` the same way.
- Rewrite affected role prompts under `flows/single_repo_repair/prompts/roles/` so they point at the kernel skill plus final JSON instead of handoff prose or direct `issue.md` mutation.
- Regenerate compiled readback for `_stdlib_smoke` and `single_repo_repair`.

Completed work:
- Migrated `_stdlib_smoke` and `single_repo_repair` to inherit `rally.base_agent.RallyManagedBaseAgent`, patch inherited env-var inputs, and emit `rally.currentness.RallyCurrentArtifactCarry` instead of shared note/handoff outputs.
- Replaced flow-local skill duplication with inherited Rally-managed skill blocks plus flow-local add-ons where needed.
- Rewrote the touched `single_repo_repair` role prompts to point at `rally-kernel` plus final JSON instead of issue-ledger-note and handoff prose.
- Recompiled both flow entrypoints with the paired Doctrine compiler into the canonical `build/agents/*` readback tree and inspected representative emitted agents and contracts.

Verification (smallest signal)
- Recompile both affected flows and inspect representative generated `AGENTS.md` plus `AGENTS.contract.json` files to confirm:
  - base-agent inheritance rendered correctly
  - no authored note/handoff outputs remain
  - final-output metadata still points at the shared schema-backed turn result

Docs/comments (propagation; only if needed)
- Update any touched flow-local instruction prose that would otherwise keep the old authored note/handoff story alive.

Exit criteria
- `_stdlib_smoke` and `single_repo_repair` both compile on the new shared contract and no Rally-managed flow still depends on authored note/handoff outputs.

Rollback
- Revert each flow as a complete authored-source-plus-build rollback; do not keep a mixed-model flow.

## Phase 3: Implement the Rally-owned runtime seams

Goal
- Make the new authored contract executable through one Rally-owned note path and one explicit launch-env contract.

Work
- Implement the `rally issue note` CLI surface in `src/rally/cli.py`.
- Implement run resolution, validated note append ordering, and issue-history snapshots in `src/rally/services/issue_ledger.py`.
- Implement launch env injection for `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` in `src/rally/adapters/codex/launcher.py`.
- Keep the runtime strict: note writes remain non-routing, and routing continues to come only from validated final JSON.

Verification (smallest signal)
- Add focused unit tests for:
  - CLI note command parsing
  - note append validation and ordering
  - launch env construction

Docs/comments (propagation; only if needed)
- Add a short code comment only at the canonical runtime boundary where env injection or note ordering would otherwise be easy to misuse.

Exit criteria
- Rally exposes the shared note-write path, resolves the target run deterministically, preserves append ordering, snapshots history, and injects the required env contract at launch.

Rollback
- Revert CLI, ledger, and launcher seam changes together if the shared mutation path is not yet correct.

## Phase 4: Reconcile repo truth and prove the cutover

Goal
- Leave one honest repo-wide story about the communication model and prove the shipped surfaces align with that story.

Work
- Align `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, and `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` with the shipped authored/runtime surfaces.
- Remove or rewrite stale wording that still implies authored note outputs, authored handoff outputs, or currentness/routing truth on note prose.
- Keep `src/rally/services/flow_loader.py` and the shared turn-result contract strict on structural `next_owner`.

Verification (smallest signal)
- Run the existing Rally contract tests plus the smallest new runtime unit tests added in Phase 3.
- Recompile `_stdlib_smoke` and `single_repo_repair` one final time and inspect representative readback so docs, authored source, generated readback, and runtime assumptions tell the same story.

Docs/comments (propagation; only if needed)
- Delete dead live wording rather than preserving legacy explanations in place.

Exit criteria
- Authored source, generated readback, runtime seams, and live design docs all align on one control model: notes for durable context, final JSON for control.

Rollback
- Revert docs and code together if the repo truth surfaces diverge again.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- Keep using the existing Rally contract tests as the first guardrail:
  - `tests/unit/domain/test_turn_result_contracts.py`
  - `tests/unit/test_flow_loader.py`
- Add only the smallest new unit tests for:
  - CLI note command parsing
  - note append validation
  - env injection into launch payloads

## 8.2 Integration tests (flows)

- Recompile `_stdlib_smoke` and `single_repo_repair` with the paired Doctrine compiler.
- Inspect the generated readback and compiled contracts for representative agents to confirm:
  - base-agent inheritance rendered correctly
  - no authored note/handoff outputs remain
  - final-output metadata still points at the correct schema-backed turn result

## 8.3 E2E / device tests (realistic)

- Do not invent a large new harness for this pivot alone.
- Once the note CLI exists, use the smallest realistic run-store proof to confirm note writes land in the right ledger and preserve ordering.
- Leave the broader end-to-end runnable-flow proof to the Phase 4 runtime vertical slice after this pivot is settled.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Cut over authored doctrine first.
- Then land the Rally runtime note and env seams.
- Keep the repo fail-loud during the transition: if a flow still depends on the old authored note/handoff model, it should be explicit rather than silently half-supported.

## 9.2 Telemetry changes

- Continue using loader/runtime failures as the primary truth surface during this pivot.
- Once launch and ledger services exist, capture:
  - note append attempts
  - note append success/failure
  - launch env proof for `RALLY_BASE_DIR` / `RALLY_RUN_ID` / `RALLY_FLOW_CODE`

## 9.3 Operational runbook

- Operators and agents both use `"$RALLY_BASE_DIR/rally" issue note`.
- Rally-managed agents read `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` from the environment, not from guessed file paths.
- If env injection is missing, the run is invalid and should fail loud.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter, `planning_passes`, `# TL;DR`, `# 0)` through `# 10)`
  - target architecture, call-site audit, phase plan, verification, rollout, and decision log alignment
- Findings summary:
  - Section `3.3` still read like open blockers even though the plan had already resolved the decisions it listed.
  - The target-architecture and consolidation sections still carried more future-parallel detail than this artifact needs after the scope was narrowed back to single-owner execution.
- Integrated repairs:
  - rewrote Section `3.3` so it now states there are no unresolved plan-shaping decisions remaining
  - narrowed the target-architecture wording to say parallel-agent execution is simply out of scope
  - removed the extra future-concurrency row from the consolidation sweep
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

## 2026-04-13 - Final JSON is the only turn-control surface

Context
- The repo contained both an older authored note/handoff model and a newer final-result routing model.

Options
- Keep both models alive and let flows mix them.
- Keep authored notes but route only from final JSON.
- Remove the separate authored handoff model and split durable notes from final control.

Decision
- Remove the separate authored handoff model and treat final JSON as the only routing and terminal control surface.

Consequences
- Notes must move to Rally CLI and Rally runtime ownership.
- Ledger readback must be documented as readback only, not a second control surface.

Follow-ups
- Rewrite the shared authored surfaces and flow doctrine accordingly.

## 2026-04-13 - Every Rally-managed agent must inherit one stdlib base agent

Context
- The intended Rally doctrine was still spread across design docs and repeated flow-local prompt text.

Options
- Keep repeating the Rally doctrine per flow.
- Put the doctrine only in the kernel skill.
- Put the doctrine in one stdlib abstract base agent and require inheritance by all Rally-managed agents.

Decision
- Put the shared Rally doctrine in one stdlib abstract base agent and require all Rally-managed agents to inherit from it, while keeping the kernel skill as the shared agent UX surface.

Consequences
- Flow doctrine gets simpler and more uniform.
- The base agent must stay thin and generic enough to belong in the Rally stdlib.
- The pivot now includes a Doctrine-level authored inheritance change, not only runtime and skill work.

Follow-ups
- Encode `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE` as inherited `EnvVar` inputs on the new Rally base agent.
- Recompile all affected flows after adoption.

## 2026-04-13 - `rally-kernel` is Rally-managed ambient capability

Context
- The base-agent doctrine needs every Rally-managed turn to have the Rally kernel skill available, but the user does not want that repeated in each flow runtime file.

Options
- Require every flow to add `rally-kernel` to `allowed_skills`.
- Treat `rally-kernel` as Rally-managed ambient capability and keep flow allowlists for flow-local skills only.

Decision
- Treat `rally-kernel` as Rally-managed ambient capability. Do not require per-flow `allowed_skills` entries for it.

Consequences
- Runtime launch and allowlist logic must provide `rally-kernel` automatically for Rally-managed turns.
- Flow doctrine can still reference the skill through inherited Rally stdlib doctrine without adding flow-local runtime clutter.

Follow-ups
- Keep Phase 3 runtime work explicit about the Rally-owned skill availability contract.
