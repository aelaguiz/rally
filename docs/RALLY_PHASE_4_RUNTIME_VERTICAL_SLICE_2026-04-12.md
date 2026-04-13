---
title: "Rally - Phase 4 Runtime Vertical Slice - Architecture Plan"
date: 2026-04-12
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: new_system
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - flows/single_repo_repair/flow.yaml
  - flows/single_repo_repair/prompts/AGENTS.prompt
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/handoffs.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
---

# TL;DR

Outcome
- Build the first runnable Rally runtime so `rally run single_repo_repair --brief-file flows/single_repo_repair/fixtures/briefs/single_repo_repair.md` completes the seeded-bug flow end to end on Codex, persists all Rally-owned state under `runs/`, routes route-to-next-owner outcomes only from schema-validated final JSON, preserves note-before-final-response ledger ordering, injects `RALLY_RUN_ID` and `RALLY_FLOW_CODE` through the launch harness on every turn, and resumes interrupted runs without creating a second run or leaking state outside the repo root.

Problem
- Rally now has the authored Phase 1 standard library, the authored Phase 2 single-repo repair flow, and compiled build readback, but it still has no runtime package, no CLI, no run-store, no ledger/session orchestration, no Codex adapter path, and its checked-in shared turn-result contract plus emitted build surfaces are still behind the latest routed-final-output definition.

Approach
- Implement a thin `src/rally/` runtime that treats Doctrine-authored assets as input, materializes one run home, launches Codex with an explicit contract, validates the shared `rally.turn_results` JSON, appends notes and normalized final-turn response records into `home/issue.md`, snapshots ledger history after every Rally-owned append, and routes ownership from validated `next_owner` keys rather than from any prose surface.
- Use a compatibility-first cutover: align the shared `rally.turn_results` handoff contract so machine routing lives in validated JSON, emit one compiler-owned per-agent `AGENT.json` sidecar adjacent to each `AGENTS.md` for final-output metadata, then make `flow_loader.py` consume those surfaces with no Markdown scraping.
- Keep the checked-in runtime modular from the first commit: pure domain contracts, narrow filesystem services, and adapter-only external IO, so `runner.py` stays orchestration-only instead of becoming a catch-all module.

Plan
- Slice Phase 4 into four implementation passes led from this repo: compatibility-first contract cutover across Rally stdlib plus paired Doctrine emit support, then run-store and home materialization, then the Codex adapter plus runner turn loop, then end-to-end happy-path and resume proof.
- Keep the slice intentionally narrow: one adapter, one flow family, one prepared home, one active owner, one active run per flow, and no new scheduler, GUI, database, or second runtime path.

Non-negotiables
- No routing from prose or note text.
- No side-door instruction surfaces; only compiled flow build output is injected.
- The launch harness must inject `RALLY_RUN_ID=<run-id>` and `RALLY_FLOW_CODE=<flow-code>` into every Rally-managed agent process. If it does not, the run is invalid.
- Notes preserve durable context only; they must not affect routing, currentness, or terminal control flow.
- There is no human handoff, human pickup record, or separate handoff artifact; Rally stamps normalized final-turn readback into `home/issue.md`.
- No god-module runtime surface; each module should have one clear reason to change.
- No Rally-owned state outside the repo root.
- No runtime fallbacks, no compatibility shims, and no Markdown scraping to paper over missing Doctrine support.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-12
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-12
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can add a thin Phase 4 runtime vertical slice that executes the authored `single_repo_repair` flow on Codex without changing authored flow semantics, by routing from validated `rally.turn_results` JSON, keeping the live ledger in `home/issue.md`, and keeping all Rally-owned runtime state inside this repo.

This claim is false if any of the following remain true after the slice lands:

- `rally run single_repo_repair --brief-file flows/single_repo_repair/fixtures/briefs/single_repo_repair.md` cannot complete the authored happy path from `01_scope_lead` back to `01_scope_lead`.
- routing still depends on prose or note text instead of schema-validated final JSON
- notes can change owner selection, currentness, or terminal control flow
- Rally writes its own control-plane state under `~/.rally`, `~/.config`, or similar global locations
- `rally resume <run-id>` creates a replacement run, rewrites prior ledger history, or discards prior logs

## 0.2 In scope

- a checked-in runtime package under `src/rally/`
- a real CLI entrypoint exposed from `pyproject.toml`
- `rally run` and `rally resume` as real commands for the `single_repo_repair` flow
- the shared `stdlib/rally` turn-result contract update so `handoff` carries structural `next_owner`
- paired Doctrine emit support plus rebuilt Rally flow build input so emitted agent directories include `AGENT.json`
- one-active-run-per-flow locking at `runs/active/<flow>.lock`
- run directory creation with `run.yaml`, `state.yaml`, `logs/`, `issue_history/`, and `home/`
- home materialization for compiled agents, allowlisted skills, allowlisted MCPs, and the prepared fixture repo
- the mandatory Rally kernel skill plus the minimal shared CLI note path and end-turn helper contract
- the shared `rally issue note` surface used by both agents and operators, with stdin, file-path, and inline-text note input
- the tiny adapter-backed helper seam for branch-name generation and markdown cleanup
- ledger append behavior for setup notes, agent-authored notes, normalized final-turn response records, and runner-generated terminal or status records
- note-before-final-response ordering when both are emitted in one turn
- routing from validated `final_output.next_owner`, where that value comes from the authored routed owner key rather than human-readable titles
- Codex launch proof surfaces: chosen `cwd`, `CODEX_HOME`, harness-injected `RALLY_RUN_ID`, harness-injected `RALLY_FLOW_CODE`, disabled ambient project-doc discovery, explicit compiled-doctrine injection, explicit MCP assembly, and explicit final-output JSON schema
- session sidecars and honest same-run resume behavior
- unit and end-to-end proof for happy-path, resume, failure-path, and `sleep` branch coverage
- a fail-loud Doctrine compatibility boundary for any machine-readable final-output and route metadata Rally needs

## 0.3 Out of scope

- a second runtime adapter
- a second fully supported flow family
- Doctrine compile orchestration inside Rally
- parallel-agent execution
- background wake scheduling or auto-resume services
- GUI, board, company, registry, marketplace, or database surfaces
- stronger built-in tool-isolation claims than the Codex adapter can actually prove
- broad refactors to authored flow doctrine beyond the minimum needed to consume the existing Phase 1 and Phase 2 assets honestly
- local runtime workarounds that guess semantics from generated Markdown when Doctrine support is missing

## 0.4 Definition of done (acceptance evidence)

- `rally run single_repo_repair --brief-file flows/single_repo_repair/fixtures/briefs/single_repo_repair.md` succeeds from a clean repo state when the required compiled build input is present.
- The run creates the Phase 4 run-home shape, preserves the original brief at the top of `home/issue.md`, and appends setup notes, agent notes, and normalized final-turn response records below it.
- Every Codex turn leaves an `adapter_launch` proof record showing the Rally-owned launch contract, including harness-injected `RALLY_RUN_ID`, harness-injected `RALLY_FLOW_CODE`, and explicit final-output schema injection.
- The shared `rally issue note` command is the durable-note write surface for both agents and operators and supports stdin, file-path, and inline-text note input.
- Happy-path routing follows the authored ownership chain `01_scope_lead -> 02_change_engineer -> 03_proof_engineer -> 04_acceptance_critic -> 01_scope_lead` and ends in `done`.
- An interrupted run after at least one routed turn can be resumed under the same run id with preserved logs, ledger history, and sessions.
- Failure paths such as invalid final JSON, missing compiled build input, missing current artifact, invalid next-owner key, or attempted home escape fail loudly and preserve archaeology.

## 0.5 Key invariants (fix immediately if violated)

- Route from validated final JSON, never from prose.
- Bind machine routing from structural owner keys, not display titles.
- The launch harness injects `RALLY_RUN_ID` and `RALLY_FLOW_CODE` on every Rally-managed turn, and Rally fails loud if either env var is missing from a launch.
- Notes are durable context only; they never carry trusted routing or currentness truth.
- If a turn emits both a note and a final turn result, append the note first and the normalized final-turn response second.
- The Rally kernel skill's end-turn helper is guidance only; the actual end-of-turn return path remains the adapter's strict final JSON surface.
- Keep `home/issue.md` as the semantic ledger and `issue_history/` as full-file archaeological snapshots after every Rally-owned append.
- Keep one active run per flow and clear the lock only on honest terminal outcomes.
- Keep all Rally-owned state inside this repo and all adapter-local state inside the run home.
- Keep module ownership explicit: domain contracts stay pure, services own one filesystem concern each, adapters own external runtime integration, and orchestration does not absorb their logic.
- Do not scrape generated `AGENTS.md` to reconstruct final-output or routing semantics.
- If Doctrine support is insufficient for the clean design, stop and land the Doctrine support instead of encoding a Rally-side hack.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Preserve the authored/runtime ownership boundary instead of making Phase 4 succeed by weakening the design.
2. Make the `single_repo_repair` happy path really runnable from `rally run`, not just locally simulated in prose.
3. Honor the new routing contract exactly: routing truth lives in schema-validated final JSON, not in prose.
4. Keep the runtime small, filesystem-native, and easy to excavate from one run directory.
5. Fail loudly on missing compiler/runtime prerequisites rather than smuggling in fallback behavior.

## 1.2 Constraints

- The repo root is fixed as Rally home and must retain the top-level shape `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/`.
- The current repo has authored doctrine and build readback but no `src/rally/`, no `tests/`, and no checked-in `runs/` placeholder directories yet.
- The active flow contract already declares per-agent skills, MCP allowlists, timeouts, and Codex adapter args in `flows/single_repo_repair/flow.yaml`.
- The checked-in authored flow still contains legacy note and handoff surfaces alongside review output and a schema-backed `final_output` contract, but Phase 4 must consume the pivoted model honestly: notes plus one schema-backed final turn result, not a second handoff artifact.
- The master design now assumes route-readable outputs are available from Doctrine, including on split `comment_output` plus `final_output` review paths.
- The checked-in shared `stdlib/rally` turn-result contract is still behind that latest routing definition today: the current handoff JSON schema lacks structural `next_owner`, and the current prompt surface does not yet bind `route.next_owner.key` into the handoff branch.
- The runtime may claim explicit instruction and MCP isolation only to the extent Codex can actually prove it.

## 1.3 Architectural principles (rules we will enforce)

- `flow.yaml` owns runtime contract and allowlists; compiled build output is injected doctrine readback, not authored runtime config.
- The runner treats generated `AGENTS.md` as injected instruction payload only, and treats emitted `AGENT.json` as compiler-owned metadata that points at the authored final-output contract.
- The shared `rally.turn_results` contract is the machine control surface: its `handoff` branch must carry structural `next_owner` via `route.next_owner.key`, and `AGENT.json` must never become a second routing truth path.
- The final-output contract is strict JSON with schema validation before runtime dispatch.
- The launch harness is responsible for injecting `RALLY_RUN_ID=<run-id>` and `RALLY_FLOW_CODE=<flow-code>` on every turn; agents must not infer active-run identity from cwd, path shape, or home layout.
- The Rally kernel skill should teach agents to use the same `rally issue note` executable surface operators use, and that command should accept stdin, file-path, and inline-text note input.
- On every turn, Rally appends any note first and then appends normalized final-turn readback derived from the validated JSON result. If the result is `handoff`, Rally routes from validated `next_owner`; it does not append a separate handoff artifact.
- `home/issue.md` is the live semantic ledger; `run.yaml`, `state.yaml`, `logs/`, `sessions/`, and locks are runtime sidecars.
- Every Rally-owned ledger append is followed by a full-copy snapshot in `issue_history/`.
- Keep policy and IO split by file: domain contracts stay free of filesystem and subprocess concerns, services own one runtime responsibility each, adapters translate to Codex, and `runner.py` coordinates rather than implements those details itself.
- If a module grows a second independent reason to change, split it before implementation continues instead of letting `runner.py`, `flow_loader.py`, or adapter files turn into kitchen-sink surfaces.
- Only allowlisted skills and MCP definitions are materialized into the run home.
- The runtime either works correctly from the declared assets or fails loudly. No side doors, no shims, no shadow routes.

## 1.4 Known tradeoffs (explicit)

- The first slice stays intentionally narrow to one adapter and one flow family, which delays generality but keeps the ownership boundary testable.
- The slice starts with cross-repo compatibility work in Rally stdlib plus the paired Doctrine emit path before runner code, which adds sequencing overhead but prevents the runtime from hard-coding stale routing semantics.
- `sleep` behavior will be implemented and unit-covered even if the seeded-bug end-to-end path never exercises it, because Phase 4 needs the runner branch but not a second scenario.
- Archive ergonomics may remain thin until after the runnable vertical slice is real.
- The emitted sidecar is intentionally metadata-only. That keeps routing truth in the shared `rally.turn_results` schema, but it means the loader must validate both surfaces together instead of relying on one file alone.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` defines the full Rally design, including Phase 4 checked-in structure, runtime-created run structure, required behavior, and acceptance criteria.
- `stdlib/rally/prompts/rally/` already contains shared authored surfaces for issue-ledger append, notes, handoffs, currentness, and turn results, but the note and handoff output shapes are transitional rather than the target runtime contract.
- `flows/single_repo_repair/` already contains the authored flow contract, prompts, compiled readback, home setup script, skills, MCP surface, brief, and seeded-bug fixture repo.
- The seeded bug is real and reproducible in the fixture repo.
- `pyproject.toml` currently sets the Doctrine compile prompt root but does not expose a runnable `rally` CLI yet.

## 2.2 What’s broken / missing (concrete)

- There is no runtime package to load flow definitions, create run directories, materialize run homes, or orchestrate turns.
- There is no implementation of active-flow locking, issue-ledger append behavior, issue-history snapshots, run-state persistence, or adapter-launch logging.
- There is no Codex adapter path that enforces `CODEX_HOME`, `cwd`, explicit instruction injection, MCP assembly, or strict final-output schema injection.
- There is no launch-harness path that proves every Rally-managed agent process receives `RALLY_RUN_ID=<run-id>` and `RALLY_FLOW_CODE=<flow-code>`.
- There is no runner implementation of the latest routing rules, especially routing from validated `next_owner`, note-before-final-response ordering, and notes that preserve context without affecting control flow.
- There is no resume path that reopens an existing run honestly under the same run id.
- The current checked-in build readback has no emitted `AGENT.json` sidecar, so Rally has no clean precompiled metadata contract for final-output schema resolution.
- The current checked-in shared `stdlib/rally/schemas/rally_turn_result.schema.json` still allows `handoff` results with `kind` only, so the authored machine contract does not yet match the latest master-design rule that `handoff` must carry structural `next_owner`.
- There is no checked-in unit or end-to-end proof that the runtime satisfies the authored flow contract.

## 2.3 Constraints implied by the problem

- Phase 4 must consume the current authored assets as inputs rather than retrofitting them to a weaker runtime.
- The runtime must preserve the latest routing model exactly or the repo will split between authored doctrine truth and runtime truth.
- The implementation needs one explicit compatibility boundary for the Doctrine outputs Rally relies on, because the design forbids scraping Markdown to recover semantic meaning.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- None required for this research pass. The authoritative planning inputs are repo-local Rally doctrine plus the paired local Doctrine compiler surfaces.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — defines the checked-in Phase 4 runtime package shape, runtime-created run structure, routed-final-output semantics, note-before-final-response ordering, resume behavior, and acceptance criteria.
  - `flows/single_repo_repair/flow.yaml` — defines the runtime contract Rally must consume as input: start agent, per-agent timeouts, skill/MCP allowlists, adapter selection, and `project_doc_max_bytes: 0`.
  - `flows/single_repo_repair/prompts/AGENTS.prompt` — defines the authored ownership chain, routed ownership edges, review split, note outputs, and per-agent `final_output`.
  - `flows/single_repo_repair/prompts/shared/{inputs,outputs,review}.prompt` — define the flow-owned artifacts, review contract, routed-next-owner expectations, and turn-result surfaces the runtime must honor.
  - `stdlib/rally/prompts/rally/{issue_ledger,handoffs,notes,currentness,turn_results}.prompt` — define the shared ledger append target, durable note boundary, typed currentness surface, transitional note and handoff authoring surfaces, and the schema-backed final turn result contract.
  - `stdlib/rally/schemas/rally_turn_result.schema.json` and `stdlib/rally/examples/rally_turn_result.example.json` — are the shared machine contract Rally must enforce, and they currently lag the latest master-design handoff rule because the handoff branch does not yet require `next_owner`.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt` — proves the Rally stdlib note, currentness, and `final_output` surfaces compile together on concrete agents while the note and handoff authoring surfaces remain transitional.
  - `flows/single_repo_repair/setup/prepare_home.sh` — defines the start-of-flow home setup contract and shows that setup notes append below the original brief.
  - `flows/single_repo_repair/fixtures/tiny_issue_service/README.md` and `flows/single_repo_repair/fixtures/tiny_issue_service/tests/test_pagination.py` — define the seeded bug and the deterministic local verification signal.
  - `pyproject.toml` — proves Rally still lacks the `src/rally/` runtime package and CLI entrypoint Phase 4 needs.
- Canonical path / owner to reuse:
  - `flows/single_repo_repair/flow.yaml` — remains the sole runtime config owner for flow roster, timeouts, allowlists, and adapter args.
  - `flows/single_repo_repair/build/` — remains the precompiled Doctrine build input Rally consumes; it is generated readback, not authored runtime config.
  - future `src/rally/flow_loader.py` — should be the only Rally boundary that resolves flow config plus emitted final-output metadata and the shared authored turn-result contract, and refuses to run when either surface is missing or incompatible.
- Existing patterns to reuse:
  - `../doctrine/doctrine/compiler.py` via `compile_prompt(...)` — already exposes compiled `final_output` metadata instead of requiring Markdown scraping.
  - `../doctrine/tests/test_final_output.py` — proves schema-backed `final_output` exposes `schema_name`, `schema_profile`, `schema_file`, and `example_file`, and fails loudly on invalid support files.
  - `../doctrine/examples/87_workflow_route_output_binding/prompts/AGENTS.prompt` — proves ordinary `TurnResponse` outputs can bind `route.next_owner.key`.
  - `../doctrine/examples/90_split_handoff_and_final_output_shared_route_semantics/prompts/AGENTS.prompt` — proves split durable review output plus separate JSON `final_output` can share route semantics and surface routed owner keys.
- Prompt surfaces / agent contract to reuse:
  - `flows/single_repo_repair/prompts/AGENTS.prompt` — current authored runtime contract for the concrete Phase 4 flow.
  - `flows/single_repo_repair/prompts/shared/review.prompt` — review-driven next-owner and current-artifact behavior.
  - `flows/single_repo_repair/prompts/shared/outputs.prompt` — per-agent schema-backed `TurnResponse` outputs.
- Native model or agent capabilities to lean on:
  - Codex structured-output support, as captured in `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, already gives Rally a strict final JSON path; Phase 4 should use that instead of inventing prompt-only parsing or wrapper logic.
- Existing grounding / tool / file exposure:
  - `skills/repo-search/SKILL.md` and `skills/pytest-local/SKILL.md` — already define the minimal home-local capabilities the flow expects.
  - `mcps/fixture-repo/server.toml` — already defines the tiny local MCP surface used to exercise allowlist materialization.
  - `flows/single_repo_repair/fixtures/tiny_issue_service/README.md` — already gives downstream turns a stable local bug description plus verification command.
- Duplicate or drifting paths relevant to this change:
- `flows/*/prompts/**` vs `flows/*/build/**` — authored source versus generated readback and compiler-owned sidecars; Rally must not promote Markdown readback into semantic truth.
  - `home/issue.md` versus `run.yaml` / `state.yaml` / `logs/` / `sessions/` — semantic ledger versus runtime plumbing; the split must stay explicit.
- `flows/*/build/agents/*/AGENTS.md` versus future compiler-owned `AGENT.json` sidecars — the Markdown remains instruction payload only; metadata resolution should come from compiler-owned structured data while routed owner truth stays in the shared authored/schema turn-result contract.
- Capability-first opportunities before new tooling:
  - use the existing Codex `final_output_json_schema` path instead of prompt parsing, transcript scraping, or deterministic wrappers
  - use the existing Doctrine route semantics instead of a new Rally routing DSL
  - use the existing setup script, skill allowlists, and MCP allowlists instead of a second global control plane
- Behavior-preservation signals already available:
  - `flows/single_repo_repair/fixtures/tiny_issue_service/tests/test_pagination.py` — protects the seeded bug and expected pagination windows
  - `flows/single_repo_repair/fixtures/tiny_issue_service/README.md` — names the deterministic local verification command
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` — defines the authored ownership chain and Phase 4 acceptance criteria the runtime must preserve

## 3.3 Decision gaps that must be resolved before implementation

- No unresolved plan-shaping decision remains. The remaining work is implementation of the already chosen compatibility-first cutover: align the shared `rally.turn_results` authored/schema contract so `handoff` carries structural `next_owner` from `route.next_owner.key`, emit one `AGENT.json` sidecar next to each emitted `AGENTS.md`, rebuild the affected flow outputs, then implement Rally against that boundary.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Rally repo today:
  - top-level permanent authored surfaces exist under `docs/`, `flows/`, `stdlib/`, `skills/`, and `mcps/`
  - there is no checked-in runtime package under `src/`
  - there are no checked-in `tests/` or `runs/` directories yet
  - `flows/single_repo_repair/build/agents/` contains only emitted `AGENTS.md` readback for the four concrete agents
  - `_stdlib_smoke` also has only `AGENTS.md` build readback, which proves the standard-library authored surfaces compile but does not yet give Rally a machine-readable runtime contract
  - `stdlib/rally/prompts/rally/turn_results.prompt` declares the shared schema-backed final output but does not yet author the latest routed handoff control field that the master design now expects
  - `stdlib/rally/schemas/rally_turn_result.schema.json` still models `handoff` as `{"kind": "handoff"}` without required `next_owner`
- Doctrine repo today:
  - `doctrine/compiler.py` already computes `CompiledFinalOutputSpec` in memory during compilation
  - `doctrine/emit_docs.py` writes emitted `AGENTS.md` files only; it does not currently emit a machine-readable sidecar alongside each emitted agent directory

## 4.2 Control paths (runtime)

- There is no real Rally runtime control path yet.
- The intended Phase 4 path exists only as authored contract and master-design prose:
  1. read `flow.yaml`
  2. validate compiled build input
  3. create one run directory and one active lock
  4. prepare one run home
  5. wake the current owner on Codex
  6. accept a strict final JSON result
  7. append notes and normalized final-turn response records into `home/issue.md`
  8. route to the next owner or terminate the run
- Current routing semantics are authored and compiler-owned, but no shipped Rally code consumes them yet.
- Current build input is insufficient for a clean runtime because it ships Markdown readback only, while Phase 4 requires emitted metadata plus the shared authored/schema final-turn contract without recompiling prompts or scraping `AGENTS.md`.
- The current shared turn-result schema is also insufficient for the latest routing plan because it cannot yet encode the structural `next_owner` key Rally is supposed to route from on `handoff`.

## 4.3 Object model + key abstractions

- Current explicit Rally-owned runtime input:
  - `flows/single_repo_repair/flow.yaml`
- Current Doctrine-owned authored/runtime surfaces already present:
  - shared issue-ledger append target
  - shared issue note output
  - shared currentness output
  - transitional handoff output shapes
  - schema-backed `TurnResponse` final outputs
  - routed ownership semantics readable from ordinary outputs and split `final_output`
- Current missing abstraction boundary:
  - there is no compiler-owned emitted JSON sidecar that turns in-memory compiled final-output metadata into a checked-in build artifact Rally can consume at runtime
  - the shared Rally-authored turn-result contract has not yet been updated so that `handoff` carries routed owner truth structurally inside the JSON schema itself and no separate handoff artifact is needed

## 4.4 Observability + failure behavior today

- There is no `events.jsonl`, rendered run log, adapter-launch log, `run.yaml`, `state.yaml`, active lock, or session sidecar surface in Rally.
- There is no runtime proof for:
  - invalid final JSON failure
  - invalid routed-owner failure
  - missing current artifact failure
  - missing build-metadata failure
  - attempted home-escape failure
- Doctrine itself already fails loudly on several final-output contract errors during compile time, but that failure surface is not yet available to Rally as precompiled runtime input.

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not applicable. Phase 4 is CLI-only runtime work.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Rally repo checked-in runtime package:
  - `src/rally/__init__.py`
  - `src/rally/__main__.py`
  - `src/rally/cli.py`
  - `src/rally/domain/{flow.py,run.py,turn_result.py}`
  - `src/rally/services/{flow_loader.py,run_store.py,issue_ledger.py,home_materializer.py,event_log.py,runner.py}`
  - `src/rally/adapters/codex/{__init__.py,launcher.py,result_contract.py,session_store.py}`
- Rally repo checked-in proof and runtime roots:
  - `tests/unit/`
  - `tests/e2e/`
  - `runs/active/`
  - `runs/archive/`
- Doctrine-emitted build input per agent directory:
  - `flows/<flow>/build/agents/<agent>/AGENTS.md`
  - `flows/<flow>/build/agents/<agent>/AGENT.json`
- `AGENT.json` is the one compiler-owned machine-readable sidecar Rally consumes in Phase 4.
- `AGENT.json` should minimally carry:
  - contract version
  - agent key / identity
  - final-output presence
  - final-output output key
  - final-output target kind
  - final-output format mode
  - schema profile
  - repo-root-relative schema file path
  - repo-root-relative example file path when present
- `AGENT.json` is runner-consumed metadata only; it is not injected as instructions and it does not author routed-owner truth on its own.
- Home materialization copies the whole emitted agent directory into `home/agents/<agent>/`, not only `AGENTS.md`, so all compiler-owned emitted readback and sidecars remain archaeologically visible inside the run.

## 5.2 Control paths (future)

1. `rally run <flow> --brief-file <path>` validates repo-root preconditions, build presence, and active-lock eligibility.
2. `cli.py` hands off to `services/flow_loader.py`, which loads `flow.yaml` plus each emitted `build/agents/<agent>/AGENT.json` into pure domain contracts.
3. `services/flow_loader.py` fails loudly if:
   - any concrete agent is missing `AGENTS.md`
   - any concrete agent is missing `AGENT.json`
   - `AGENT.json` has an unsupported contract version
   - `AGENT.json` lacks a schema-backed `TurnResponse` final output for Rally-managed turns
   - schema support files declared by the emitted metadata cannot be resolved honestly from repo-root-relative paths inside the repo root
   - the resolved final-output schema does not require structural `next_owner` on the `handoff` branch
4. `services/run_store.py` creates `runs/<run-id>/`, writes `run.yaml` and initial `state.yaml`, acquires `runs/active/<flow>.lock`, and writes the original brief to `home/issue.md`.
5. `services/home_materializer.py` runs the flow setup script once, allows it to append setup notes below the original brief, copies full emitted agent directories plus allowlisted skills and MCP definitions into `home/`, and prepares the writable target repo under `home/repos/`.
6. `services/runner.py` drives the state machine for the current owner and asks `adapters/codex/launcher.py` to launch Codex with:
   - Rally-chosen `cwd`
   - `CODEX_HOME=<run-home>`
   - `RALLY_RUN_ID=<run-id>` injected by the harness on every turn
   - `RALLY_FLOW_CODE=<flow-code>` injected by the harness on every turn
   - ambient project-doc discovery disabled
   - explicit compiled-doctrine injection from emitted `AGENTS.md`
   - explicit final-output JSON schema resolved through emitted `AGENT.json`
   - explicit MCP config assembled from allowlisted repo-local definitions
7. `adapters/codex/result_contract.py` validates the returned final JSON against the shared turn-result contract and returns a typed `TurnResult`.
8. If the turn emitted a note, `services/issue_ledger.py` appends it first and snapshots ledger history.
9. `services/issue_ledger.py` appends normalized final-turn readback derived from the validated `TurnResult` and snapshots ledger history again.
10. If the turn result is `handoff`, `services/runner.py` routes from validated `next_owner`, asks `services/run_store.py` to update `state.yaml`, and wakes the resolved next owner in the same run home.
11. On `done` or `blocker`, `services/runner.py` asks `services/run_store.py` to record terminal state, preserve the run directory, and clear the active lock.
12. On `sleep`, `services/runner.py` records the request, keeps the same owner, blocks inline in the simple model, and later wakes the same run again.
13. On interruption, `services/runner.py` preserves the run directory and asks `adapters/codex/session_store.py` to preserve sessions; `rally resume <run-id>` reopens the same run and continues from stored state instead of creating a replacement run.

## 5.3 Module boundaries + abstractions (future)

- `cli.py`
  - parses operator commands and prints user-facing errors
  - does not load YAML, touch run files, or launch adapters directly
- `domain/flow.py`
  - defines pure `FlowDefinition` and `CompiledAgentContract`
  - contains no filesystem access or subprocess logic
- `domain/run.py`
  - defines pure `RunRecord`, `RunState`, and related enums or invariants
  - contains no ledger rendering or adapter concerns
- `domain/turn_result.py`
  - defines pure `TurnResultContract` and typed `TurnResult`
  - owns tagged-union meaning, not filesystem append policy
- `services/flow_loader.py`
  - loads `flow.yaml`, emitted metadata, and referenced schema/example files
  - returns domain objects and exact blocker errors
- `services/run_store.py`
  - owns run-id creation, lock lifecycle, `run.yaml`, and `state.yaml`
  - does not render ledger text, parse final JSON, or assemble adapter launches
- `services/issue_ledger.py`
  - owns note append formatting, normalized final-turn readback rendering, and `issue_history/` snapshots
  - does not choose routes or clear locks
- `services/home_materializer.py`
  - owns home copy/setup/materialization only
  - does not parse final JSON or mutate run state beyond setup outputs
- `services/event_log.py`
  - owns append-only telemetry records only
  - does not decide behavior or write semantic ledger entries
- `services/runner.py`
  - owns orchestration and state-machine sequencing only
  - delegates file writes, schema parsing, and adapter-specific work to owning modules
- `adapters/codex/launcher.py`
  - owns process launch, environment construction, and adapter-local IO only
  - never mutates Rally run state or ledger files directly
- `adapters/codex/result_contract.py`
  - owns adapter-facing schema enforcement and final JSON translation into typed `TurnResult`
  - does not resolve locks, append ledgers, or copy homes
- `adapters/codex/session_store.py`
  - owns adapter session sidecars only
  - does not decide routing or currentness
- Dependency rules:
  - `cli.py` may call `services/*` but should not bypass them to raw files
  - `services/*` may depend on `domain/*` and adapters through narrow typed inputs and outputs
  - `adapters/*` may depend on `domain/*` but never on ledger or run-store internals
  - `domain/*` must not depend on `services/*` or `adapters/*`
  - `services/runner.py` is allowed to coordinate services and adapters, but any new logic with its own independent reason to change must move back into a narrower owning module

- `FlowDefinition`
  - loaded from `flow.yaml`
  - owns start agent, timeouts, allowlists, and adapter args
- `CompiledAgentContract`
  - loaded from `build/agents/<agent>/AGENT.json`
  - owns the final-output schema metadata Rally needs for strict adapter launch
  - is compiler-owned input, not Rally-authored config
- `TurnResultContract`
  - loaded from the schema file referenced by `CompiledAgentContract`
  - owns the strict tagged JSON union Rally validates, including `handoff.next_owner`
- `RunRecord`
  - stable run identity persisted to `run.yaml`
- `RunState`
  - small machine-readable current state persisted to `state.yaml`
- `LedgerAppend`
  - runner-owned append operation for notes, normalized final-turn response records, and snapshots
- `AdapterLaunchRecord`
  - explicit proof of the Codex launch contract per turn
- `CodexSessionRecord`
  - per-agent session sidecar for same-run resume
- `TurnResult`
  - strict tagged JSON union for `handoff`, `done`, `blocker`, and `sleep`

## 5.4 Invariants and boundaries

- Route only from validated `TurnResult.next_owner` on `handoff`.
- Treat `next_owner` as the structural agent key that came from compiler-owned route semantics, not as display text.
- Keep notes as advisory durable context only.
- Do not invent a separate handoff artifact; Rally stamps normalized final-turn readback into `home/issue.md`.
- Use emitted `AGENT.json` for runtime final-output metadata resolution and emitted `AGENTS.md` for explicit instruction injection.
- Keep `handoff.next_owner` in the shared `rally.turn_results` schema and validated final JSON, not in `AGENT.json` and not in prose.
- Never rebuild semantic truth by parsing generated `AGENTS.md`.
- Fail loudly if the flow roster, emitted agent contract, final-output schema metadata, or routed owner key cannot be resolved honestly.
- Fail loudly if `AGENT.json` points outside the repo root or if the resolved schema no longer matches the Rally handoff contract.
- Keep all agent-visible capabilities home-local and allowlist-driven.
- Keep all Rally-owned state under the repo root and all adapter-local state under the run home.
- Preserve the whole run directory for archaeology on both success and failure.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not applicable. The operator surface remains CLI plus run-directory artifacts.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Packaging | `pyproject.toml` | project metadata | no CLI entrypoint | add package metadata and `rally` console entrypoint | make Phase 4 runnable from repo root | `rally run`, `rally resume` | CLI smoke, e2e entry |
| Runtime package | `src/rally/__init__.py` | package root | missing | create package root | establish checked-in runtime ownership | importable `rally` package | unit import smoke |
| CLI | `src/rally/__main__.py`, `src/rally/cli.py` | command parsing | missing | add `run`, `resume`, and `issue note` commands with exact Phase 4 flags and note-input modes | operator and agent note surface must be real | CLI contract | CLI tests |
| Domain contracts | `src/rally/domain/{flow.py,run.py,turn_result.py}` | pure runtime contracts | missing | define pure typed contracts for flow loading, run state, and final turn results with no filesystem or adapter IO | keep policy separate from IO and make future extraction cheap | typed domain layer | domain unit tests |
| Flow loading | `src/rally/services/flow_loader.py` | flow/build preflight | missing | load `flow.yaml`, validate emitted agent directories, require `AGENT.json`, resolve repo-root-relative final-output schema support files, and fail loud on missing or incompatible compiler-owned metadata or unsupported sidecar version | preserve authored/runtime split without runtime recompilation | `FlowDefinition`, `CompiledAgentContract`, `TurnResultContract` loader | `test_flow_loader.py` |
| Run store | `src/rally/services/run_store.py` | run identity, lock, state | missing | create run ids, lock files, `run.yaml`, `state.yaml`, active-lock lifecycle | one-active-run-per-flow and resume depend on it | `RunRecord`, `RunState` | `test_run_store.py` |
| Ledger | `src/rally/services/issue_ledger.py` | append + snapshot behavior | missing | append setup notes, notes, normalized final-turn response records, and runner-generated terminal records; write `issue_history/` snapshots after every Rally-owned append | live semantic ledger is central Phase 4 truth | `LedgerAppend` contract | `test_issue_ledger.py` |
| Materialization | `src/rally/services/home_materializer.py` | home preparation | missing | copy full emitted agent directories, allowlisted skills, allowlisted MCPs, and fixture repo into `home/`; run `setup/prepare_home.sh` once | agents must live inside one prepared home and archaeology should keep compiler-owned sidecars | home materialization contract | `test_home_materializer.py` |
| Eventing | `src/rally/services/event_log.py` | run-local logs | missing | write `logs/events.jsonl`, per-agent logs, and `adapter_launch/*.json` | Phase 4 requires archaeological and launch-contract proof | event-log format | event/log tests |
| Runner orchestration | `src/rally/services/runner.py` | turn orchestration | missing | drive wake, `handoff`, done, blocker, sleep, state updates, normalized final-turn readback, and resume path while delegating IO and parsing to owning modules | keep the state machine explicit without creating a god module | runner state machine | runner tests, e2e |
| Codex adapter | `src/rally/adapters/codex/launcher.py` | process launch | missing | enforce `cwd`, `CODEX_HOME`, harness-injected `RALLY_RUN_ID`, harness-injected `RALLY_FLOW_CODE`, config override, explicit doctrine injection, MCP assembly, and output schema | honor no-side-door contract and make issue-note writes honest | launch contract | adapter launch tests |
| Internal helper seam | `src/rally/internal/*` or equivalent | tiny schema-bound maintenance tasks | missing | shell through the same adapter stack for low-thinking strict-JSON tasks such as branch-name generation and rough-input markdown cleanup | keep these transforms on a shared Rally-owned path instead of ad hoc parsing or wrapper scripts | narrow helper contract | helper seam tests |
| Result contract | `src/rally/adapters/codex/result_contract.py` | final JSON validation | missing | validate strict turn result and resolve routed owner keys | routing must be machine-shaped | `TurnResult` parser | `test_codex_result_contract.py` |
| Session store | `src/rally/adapters/codex/session_store.py` | resume sidecars | missing | persist and reload per-agent session metadata | resume must continue same run honestly | `CodexSessionRecord` | resume tests |
| Authored flow input | `flows/single_repo_repair/flow.yaml` | runtime contract | already defines start agent, allowlists, adapter args | consume as input; only edit if runtime validation exposes a real contract bug | Phase 4 should not weaken authored source | loader preflight | flow-loader tests |
| Emitted build input | `flows/single_repo_repair/build/agents/*/AGENTS.md` | explicit instruction readback | already emitted | keep as instruction payload only; do not parse for runtime semantics | preserve authored/runtime split | explicit doctrine injection | e2e behavior |
| Emitted build input | `flows/single_repo_repair/build/agents/*/AGENT.json` | compiler-owned sidecar | missing | add emitted per-agent JSON sidecar with final-output schema metadata | Rally needs precompiled semantic input | `CompiledAgentContract` | loader tests, e2e |
| Authored flow input | `flows/single_repo_repair/prompts/AGENTS.prompt` | routed ownership chain, notes, legacy handoff shapes, final outputs | already authored | consume as input while pivoting to notes plus one final turn result; do not rewrite to fit runtime shortcuts | preserve Phase 2 authored surfaces while honoring the Phase 3 pivot | compatibility boundary | e2e behavior |
| Stdlib authored contract | `stdlib/rally/prompts/rally/turn_results.prompt` | shared final-output doctrine | schema-backed control union exists but does not yet author handoff `next_owner` from `route.next_owner.key` | add the latest master-design route-control and normalized-readback pattern to the shared contract | machine routing must live in final JSON, not prose or sidecar metadata | shared `RallyTurnResultJson` authored contract | `_stdlib_smoke`, loader tests, e2e |
| Stdlib machine contract | `stdlib/rally/schemas/rally_turn_result.schema.json` | strict JSON schema | handoff requires only `kind` | require `next_owner` on `handoff` and keep the other tagged branches unchanged | Codex strict output must enforce the real routing contract | shared `TurnResultContract` | contract tests, adapter tests, e2e |
| Stdlib example | `stdlib/rally/examples/rally_turn_result.example.json` | payload example | does not yet demonstrate structural handoff owner | update the example to show `handoff.next_owner` using a structural agent key | keep emitted/readable contract aligned for operators and tests | example alignment | contract tests |
| Stdlib input | `stdlib/rally/prompts/rally/{issue_ledger,handoffs,notes,currentness,turn_results}.prompt` | shared authored contracts | already authored | consume as input; do not fork parallel runtime semantics | preserve Phase 1 authored surfaces | compatibility boundary | e2e + contract tests |
| Doctrine compiler | `../doctrine/doctrine/compiler.py` | `CompiledFinalOutputSpec` and serialization seam | final-output metadata exists only in memory | expose a serializable per-agent contract shape for emitted builds | Rally needs compiler-owned structured metadata at runtime | emitted `AGENT.json` schema | Doctrine unit tests |
| Doctrine emit path | `../doctrine/doctrine/emit_docs.py` | `emit_target()` | emits only `AGENTS.md` | emit `AGENT.json` alongside each `AGENTS.md` | make build output sufficient for Rally runtime | emitted build sidecar | Doctrine emit tests / smoke |
| Doctrine proof | `../doctrine/tests/test_final_output.py`, `../doctrine/tests/test_route_output_semantics.py`, `../doctrine/doctrine/diagnostic_smoke.py` | compiler and emit coverage | covers in-memory compile and rendered markdown behavior | extend to cover emitted machine-readable sidecar and route-aware final-output metadata | generic compiler support must stay proven | sidecar coverage | Doctrine tests |
| Tests | `tests/unit/*.py`, `tests/e2e/*.py` | proof surfaces | missing | add the small Phase 4 unit and e2e coverage set | Phase 4 needs believable proof, not prose | unit + e2e contracts | all new tests |
| Runtime placeholders | `runs/active/`, `runs/archive/` | repo-local runtime state roots | missing | add checked-in placeholder dirs | repo-root runtime state is part of the design | run-store contract | run-store tests |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - runtime truth flows through `src/rally/services/flow_loader.py`, `src/rally/services/runner.py`, and `src/rally/adapters/codex/result_contract.py`
  - pure runtime contracts live under `src/rally/domain/` and stay free of filesystem and adapter IO
  - authored machine-routing truth flows through `stdlib/rally/prompts/rally/turn_results.prompt` and `stdlib/rally/schemas/rally_turn_result.schema.json`
  - compiler-owned semantic truth for final-output launch contract flows through emitted `build/agents/<agent>/AGENT.json`
  - authored routing truth continues to live in flow doctrine and arrives at the runner only through validated final-output JSON
- Deprecated APIs (if any):
  - none in Rally yet; Phase 4 is additive inside this repo
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - any attempt to parse `AGENTS.md` for final-output or route semantics
  - any Rally-authored handwritten manifest that duplicates compiler-owned `AGENT.json`
- Capability-replacing harnesses to delete or justify:
  - do not add prompt parsers, transcript scrapers, routing wrappers, or helper manifests that stand in for Codex structured output or Doctrine route semantics
- Live docs/comments/instructions to update or delete:
  - update `pyproject.toml` to reflect the real CLI once added
  - add a short code comment at the compatibility boundary explaining why Rally consumes `AGENT.json` and never scrapes `AGENTS.md`
  - add a short code comment at the result-contract boundary explaining that `handoff.next_owner` lives in validated JSON, not in sidecar metadata or prose
  - add a short code comment at the ledger append boundary explaining note-before-final-response ordering and why notes are non-routing context
- Behavior-preservation signals for refactors:
  - seeded-bug happy path must remain the canonical preservation signal for the authored ownership chain
  - resume must preserve run id, logs, and ledger history
  - no-side-door instruction canary must remain absent from run-home agent surfaces and injected payload

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Doctrine emit surfaces | `../doctrine/doctrine/emit_docs.py` | emit one `AGENT.json` sidecar beside each emitted `AGENTS.md` | prevents Rally from inventing its own semantic manifest or scraping Markdown | include |
| Doctrine compiler surfaces | `../doctrine/doctrine/compiler.py` | serialize compiled final-output metadata through one compiler-owned contract | keeps final-output/schema truth in Doctrine instead of Rally | include |
| Doctrine proof surfaces | `../doctrine/tests/test_final_output.py`, `../doctrine/tests/test_route_output_semantics.py`, `../doctrine/doctrine/diagnostic_smoke.py` | sidecar coverage for route-aware final-output metadata | prevents silent compiler/runtime drift | include |
| Rally stdlib turn-result contract | `stdlib/rally/prompts/rally/turn_results.prompt`, `stdlib/rally/schemas/rally_turn_result.schema.json` | require structural `handoff.next_owner` in the shared JSON union | keeps machine routing in one authored schema instead of prose or metadata | include |
| Rally domain contracts | future `src/rally/domain/*` | keep pure runtime contracts separate from filesystem and adapter code | prevents `runner.py` and service files from becoming monolithic policy-plus-IO blobs | include |
| Rally flow loading | future `src/rally/services/flow_loader.py` | consume `flow.yaml` plus emitted `AGENT.json`, never prompt source or Markdown semantics | enforces the authored/runtime split at one canonical boundary | include |
| Rally home materialization | future `src/rally/services/home_materializer.py` | copy full emitted agent directories, not only `AGENTS.md` | preserves archaeology and future generic emitted sidecars without special cases | include |
| Rally runner orchestration | future `src/rally/services/runner.py` | keep orchestration thin and delegate IO, parsing, and rendering to owning modules | prevents a long-lived god module from becoming the de facto runtime framework | include |
| `_stdlib_smoke` build output | `flows/_stdlib_smoke/build/agents/*` | emit the same `AGENT.json` sidecar pattern | keeps the standard-library smoke aligned with the runtime contract surface | include |
| Additional Rally flow families | other future `flows/*` | adopt the same emitted sidecar contract only when they become supported runnable flows | avoids widening product scope during Phase 4 | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with the smallest credible signal. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Lock the compatibility boundary and checked-in runtime skeleton

Goal
- Land the shared machine-routing contract, the paired Doctrine emit sidecar, and the narrow checked-in runtime skeleton before any runner behavior exists.

Work
- Land the Rally stdlib turn-result update first so `stdlib/rally/prompts/rally/turn_results.prompt` authors handoff `next_owner: route.next_owner.key`, `stdlib/rally/schemas/rally_turn_result.schema.json` requires `next_owner` when `kind == handoff`, and the shared example reflects that structural owner key.
- Land the paired Doctrine emit support next so `flows/<flow>/build/agents/<agent>/AGENT.json` is emitted with a versioned per-agent contract that points at the authored final-output schema through repo-root-relative support-file paths.
- Recompile `_stdlib_smoke` and `single_repo_repair` only after both preceding contract changes land, so the checked-in Rally build input reflects the real compatibility boundary instead of a partial intermediate state.
- Extend `pyproject.toml` with the Phase 4 runtime package and console entrypoint.
- Create the initial modular `src/rally/` package layout with `domain/`, `services/`, and `adapters/` ownership boundaries plus the checked-in `runs/active/` and `runs/archive/` placeholders.
- Implement `domain/{flow.py,run.py,turn_result.py}` first so later services and adapters exchange typed contracts instead of ad hoc dicts.
- Implement `services/flow_loader.py` preflight that:
  - loads `flows/single_repo_repair/flow.yaml`
  - validates required compiled build presence, including emitted `AGENT.json`
  - validates the runtime can resolve the final-output and routing semantics it needs from compiler-owned build metadata plus the shared authored turn-result schema rather than scraping `AGENTS.md`
  - validates `AGENT.json` versioning and repo-root-relative support-file resolution
  - validates that the resolved handoff branch still requires structural `next_owner`
  - fails with an exact blocker message when the paired Doctrine surfaces are missing or incompatible
- Keep this phase strictly at the contract boundary: shared authored contract, emitted metadata contract, pure runtime contracts, checked-in Rally skeleton, and loader preflight only.

Verification (smallest signal)
- Targeted paired Doctrine proof for route-aware schema-backed `final_output` plus emitted-sidecar coverage, then recompile `_stdlib_smoke` and `single_repo_repair`, inspect that each emitted agent directory contains the expected `AGENT.json`, and confirm the shared turn-result schema now requires handoff `next_owner`.
- Unit coverage for the pure domain contracts plus flow-loader preflight, unsupported sidecar version, repo-root-relative path enforcement, and build-presence failure.
- One CLI smoke invocation that exits with a precise blocker instead of silently guessing when required semantic inputs are unavailable.

Docs/comments (propagation; only if needed)
- Add one short code comment at the compatibility boundary explaining that generated Markdown is instruction payload, `AGENT.json` is metadata, and routed owner truth still lives in validated final JSON.
- Add one short boundary comment in `services/runner.py` explaining that the file coordinates owned services and adapters rather than accumulating their logic.

Exit criteria
- The repo has a real importable `rally` package and CLI entrypoint.
- `_stdlib_smoke` and `single_repo_repair` both rebuild against the updated shared contract and emit `AGENT.json`.
- Flow preflight either resolves the required semantic inputs honestly from emitted `AGENT.json` plus the shared `rally.turn_results` schema, or fails loudly with an exact compatibility blocker.
- No Markdown-scraping fallback path exists.

Rollback
- If this phase can only succeed by inventing handwritten manifests, scraping `AGENTS.md`, letting `AGENT.json` become a second routing truth path, or adding compatibility shims, revert the local runtime wiring and move the missing support into Doctrine or the shared Rally stdlib first.

## Phase 2 - Create run storage, ledger, and home materialization

Goal
- Make one run directory and one prepared home real before adding turn orchestration.

Work
- Implement `run_store.py` for run id generation, active-lock lifecycle, `run.yaml`, and `state.yaml`.
- Implement `issue_ledger.py` for:
  - initial brief write
  - setup-note append
  - note append
  - normalized final-turn response append
  - runner-generated terminal record append
  - full-copy `issue_history/` snapshots after every Rally-owned append
- Implement the shared `rally issue note` CLI path on top of that ledger service, with stdin, file-path, and inline-text note input.
- Implement `home_materializer.py` to:
  - copy full emitted agent directories into `home/agents/`
  - materialize only allowlisted skills and MCPs into `home/skills/` and `home/mcps/`
  - prepare `home/repos/tiny_issue_service/`
  - run `setup/prepare_home.sh` once with the expected environment
- Implement `event_log.py` for structured events and per-agent/logical slices.
- Keep Phase 2 services single-purpose; do not let ledger formatting, run-state mutation, and home setup collapse into one filesystem utility module.

Verification (smallest signal)
- Unit coverage for lock acquisition and cleanup, run directory creation, ledger append plus snapshot behavior, and allowlist-only home materialization.
- CLI coverage for `rally issue note` stdin, file-path, and inline-text note input against the Rally-owned append path.
- One repo-local test that proves the original brief stays at the top of `home/issue.md` and setup notes append below it.

Docs/comments (propagation; only if needed)
- Add a short code comment at the ledger append boundary explaining why note ordering and snapshots are runner-owned.

Exit criteria
- A prepared run can be created with the expected run directory shape and home layout.
- Only allowlisted skills and MCP definitions appear in the run home.
- The live ledger and issue-history behavior match the Phase 4 design.

Rollback
- If run creation fails before the first turn, remove any partial active lock and preserve enough filesystem context to explain the failure plainly.

## Phase 3 - Implement the Codex adapter path and runner turn loop

Goal
- Execute Rally-managed turns honestly on Codex and drive same-run ownership transitions from validated final-output JSON.

Work
- Implement `adapters/codex/launcher.py` so every turn uses:
  - Rally-chosen `cwd`
  - `CODEX_HOME` rooted at the run home
  - `RALLY_RUN_ID=<run-id>` injected by the launch harness
  - `RALLY_FLOW_CODE=<flow-code>` injected by the launch harness
  - disabled ambient project-doc discovery
  - explicit compiled-doctrine injection
  - explicit MCP config from allowlisted repo-local definitions
  - explicit final-output JSON schema
- Implement `adapters/codex/result_contract.py` for strict turn-result validation and routed-owner resolution, including the rule that `handoff.next_owner` comes from validated JSON rather than sidecar metadata or prose.
- Implement `adapters/codex/session_store.py` for per-agent saved session sidecars and honest same-run resume.
- Implement the tiny adapter-backed helper seam for low-thinking strict-JSON tasks such as branch-name generation and rough-input markdown cleanup, keeping it out of the turn-routing path.
- Implement `services/runner.py` to:
  - launch the current owner
  - validate final turn results before dispatch
  - append notes without changing routing or currentness
  - append normalized final-turn readback for every turn
  - route `handoff` only from validated `next_owner`
  - enforce note-before-final-response ordering when both exist
  - update `state.yaml`
  - clear the active lock only on terminal outcomes
  - preserve runs and sessions on interruption
  - support `sleep` in logic and state even though the seeded-bug e2e path will not use it
- Keep `services/runner.py` orchestration-only; if schema resolution, ledger rendering, path derivation, or adapter launch construction starts living there, split it back into the owning service or adapter immediately.

Verification (smallest signal)
- Unit coverage for final-result validation, invalid routed-owner failure, note-before-final-response ordering, terminal-state lock clearing, resume state restoration, and `sleep` branch handling.
- A small runner-level integration test that proves notes do not affect owner selection or currentness, and that `handoff` routing does not fall back to sidecar metadata or prose.

Docs/comments (propagation; only if needed)
- Add one short boundary comment near routed-owner handling explaining why machine routing binds from structural keys rather than titles or prose.

Exit criteria
- The runner can execute turns in one prepared home and route to the next owner only from validated final JSON.
- Notes are persisted as context only.
- Resume reopens the same run with preserved logs, ledger history, and sessions.

Rollback
- On invalid final JSON, invalid owner keys, missing current artifacts, or home-escape attempts, preserve the run directory, record the blocker, and stop without silent continuation.

## Phase 4 - Prove the seeded-bug happy path, resume path, and failure boundaries

Goal
- Finish Phase 4 with believable end-to-end proof against the authored `single_repo_repair` flow instead of a synthetic near-match.

Work
- Add `tests/e2e/test_seeded_bug_happy_path.py` for the authored ownership chain and terminal `done` outcome.
- Add `tests/e2e/test_seeded_bug_resume.py` for interruption after at least one routed turn and same-run resume.
- Prove the canary no-side-door contract.
- Prove failure-path preservation for invalid final JSON, missing compiled build input, missing current artifact, invalid routed owner, and attempted home escape.
- Keep archive behavior thin unless needed for honest closeout of the finished run.

Verification (smallest signal)
- Real end-to-end `rally run` and `rally resume` proof against the `single_repo_repair` flow.
- One proof that `logs/adapter_launch/*.json` plus the prepared home surface are enough to show there was no instruction-side-door fallback, that the launch harness injected both `RALLY_RUN_ID` and `RALLY_FLOW_CODE`, and that the enforced schema still required structural handoff `next_owner`.
- Unit coverage already in place for `sleep`; no separate seeded-bug `sleep` scenario required.

Docs/comments (propagation; only if needed)
- If implementation changes any operator-facing runtime contract or file shape from the master design, sync the surviving live docs in the same pass.

Exit criteria
- The Phase 4 acceptance criteria from the master design are materially satisfied by code and proof surfaces in this repo.
- The run directory alone is sufficient to explain what happened, why routing occurred, what artifacts were current, and how the run ended.

Rollback
- Preserve all failed run directories for archaeology and do not auto-clean them into a misleading success state.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- `tests/unit/domain/test_flow_contracts.py`, `tests/unit/domain/test_run_contracts.py`, `tests/unit/domain/test_turn_result_contracts.py`
  - pure domain invariants stay stable without pulling in filesystem or adapter IO
- `tests/unit/test_flow_loader.py`
  - flow loading, sidecar-version preflight, repo-root-relative schema/example resolution, and fail-loud compatibility boundary
- `tests/unit/test_run_store.py`
  - run id creation, active-lock behavior, terminal lock clearing
- `tests/unit/test_issue_ledger.py`
  - brief-first ledger order, note append, normalized final-turn response append, terminal records, issue-history snapshots
- `tests/unit/test_home_materializer.py`
  - allowlist-only materialization and home setup integration
- `tests/unit/test_codex_result_contract.py`
  - strict final-output validation, structural `handoff.next_owner` enforcement, routed-owner resolution, and invalid-owner failure
- unit coverage for runner `sleep` branch, note-before-final-response ordering, and the orchestration-only dependency seams between runner, services, and adapters

## 8.2 Integration tests (flows)

- Keep compatibility proof narrow and contract-level before runner proof:
  - paired Doctrine proof for route-aware schema-backed `final_output`
  - emitted `AGENT.json` coverage
  - Rally rebuild proof for `_stdlib_smoke` and `single_repo_repair`
- Keep integration proof narrow and behavior-level:
  - runner state transitions from validated turn results
  - note persistence without routing side effects
  - resume state restoration across interrupted runs
- Do not add a second production adapter, parser layer, metadata-owned routing layer, or wrapper just to make integration tests easier.
- Do not solve modularity drift with one generic utils module or a shared god-object that bypasses the owning service boundaries.

## 8.3 E2E / device tests (realistic)

- One real `rally run single_repo_repair --brief-file ...` happy path.
- One interrupted-run `rally resume <run-id>` proof after at least one routed turn.
- One no-side-door canary proof.
- No negative-value gates:
  - no doc-inventory checks
  - no absence tests
  - no repo-shape policing
  - no heuristic routing validators outside the actual runtime path

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land Phase 4 behind the narrow scope of one adapter and one flow family only.
- Treat `single_repo_repair` as the only supported runnable flow until the vertical slice is clean.
- Keep `archive` as a thin follow-on command if it is not required for honest Phase 4 archaeology.

## 9.2 Telemetry changes

- `logs/events.jsonl` is the primary structured run telemetry.
- `logs/agents/*.jsonl` are per-agent filtered slices.
- `logs/adapter_launch/*.json` are the proof surface for the Codex launch contract, including the required harness-injected `RALLY_RUN_ID` and `RALLY_FLOW_CODE`.
- No external metrics backend is required for this slice.

## 9.3 Operational runbook

- Run Rally from repo root only.
- If `runs/active/single_repo_repair.lock` already exists, fail with the exact blocker instead of starting another run.
- If a run stops unexpectedly, inspect the preserved run directory, then use `rally resume <run-id>` rather than creating a replacement run.
- If a required compiler/runtime contract is missing, treat that as a real blocker and land the generic enabling support instead of carrying a local workaround.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self cold read 1, self cold read 2, self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, `# 0)` through `# 10)`, `planning_passes`, and helper blocks
  - cross-section agreement on routing truth, compatibility-first sequencing, verification burden, rollout obligations, and no-side-door boundaries
- Findings summary:
  - a few stale claims still over-assigned routed semantics to `AGENT.json`
  - `# TL;DR`, `# 0)`, and `# 7)` were not explicit enough yet that the first implementation move is the compatibility-first cutover across Rally stdlib plus paired Doctrine emit support
  - `# 3.3` still spoke as if deep-dive work remained instead of reflecting resolved planning status
- Integrated repairs:
  - aligned `# TL;DR`, `# 0.2`, and `# 1.4` with the compatibility-first cutover now encoded in `# 7)`
  - narrowed `AGENT.json` language across the artifact to metadata resolution rather than a second routing-truth surface
  - rewrote `# 3.3` to state that plan-shaping decisions are resolved and the remaining work is implementation against the chosen boundary
  - kept `# 8)` and `# 9)` aligned with the updated execution burden and proof surfaces
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

<!-- arch_skill:block:plan_enhancer:start -->
# Plan Enhancer Notes (authoritative)

## What I changed (plan upgrades)
- made the target runtime layout explicitly layered into `cli`, pure `domain`, narrow `services`, and adapter-only `adapters/codex`
- declared `services/runner.py` orchestration-only and pushed file ownership rules into the main plan so the runtime does not grow around one catch-all module
- updated the call-site audit and phase plan to build typed contracts first, then single-purpose services, then adapter and orchestration behavior on top
- extended verification so modularity is enforced through typed seams and focused unit coverage, not through style policing or repo heuristics

## Architecture verdict
- Canonical owner path: `src/rally/domain/*` for pure runtime contracts, `src/rally/services/*` for Rally-owned filesystem/runtime responsibilities, and `src/rally/adapters/codex/*` for Codex integration
- Capability-first path: keep Rally using Codex native structured-output capability; modularization is about clean ownership boundaries in Rally, not about adding wrappers around model behavior
- Is this now decision-complete and faithful to approved intent? yes
- Biggest remaining risks:
  - the first implementation pass could still let `services/runner.py` absorb path-building or formatting logic if the boundaries are not policed in code review
  - there is still paired Doctrine work in the first phase, so modular Rally code depends on landing that compatibility boundary cleanly first

## Hard architecture rules (real surfaces only)
- `domain/*` stays pure: no filesystem access, subprocess launch, or adapter mutation
- each `services/*` file owns one runtime concern and returns typed values rather than ad hoc dicts
- `services/runner.py` coordinates services and adapters but does not render ledger text, load YAML/schema files, or assemble adapter launches inline
- `adapters/codex/*` may translate to and from Codex, but they do not mutate Rally ledger files or run-store state directly
- no generic catch-all utils module is allowed to become a shadow owner for paths, schema loading, routing, or ledger formatting

## Call sites + migration
- Must-change call sites:
  - `src/rally/domain/{flow.py,run.py,turn_result.py}` — define pure contracts early so every later module shares the same typed surface
  - `src/rally/services/{flow_loader.py,run_store.py,issue_ledger.py,home_materializer.py,event_log.py,runner.py}` — keep runtime responsibilities narrow and explicit
  - `src/rally/adapters/codex/{launcher.py,result_contract.py,session_store.py}` — keep adapter concerns out of Rally services
- Deletes / cleanup (no parallel paths):
  - any future generic `utils.py` or ad hoc helper object that becomes a second owner for routing, path resolution, ledger formatting, or adapter launch policy — delete or split back into the owning module
- Live docs/comments to delete or rewrite:
  - this plan’s future implementation notes and module docstrings — rewrite if code lands with flatter or muddier ownership than the plan now requires

## Consolidation sweep (anti-blinders)
- Other places that should adopt the new central pattern:
  - `tests/unit/` layout — Proposed: include — mirror the domain/services/adapters split so tests reinforce the intended ownership model
  - future non-Codex adapters — Proposed: explicitly out of scope — preserve the layered shape later without widening Phase 4 product scope now

## Evidence (non-blocking)
- Behavior-preservation checks after refactor:
  - pure domain unit tests — prove contracts stay stable without filesystem or adapter coupling
  - runner integration tests — prove orchestration still works while delegating IO and parsing to owned modules
- Evidence we'll rely on:
  - `_stdlib_smoke` and `single_repo_repair` rebuild proof — show the compatibility boundary is honest before runtime code grows around it
  - focused unit tests per service and adapter — show each module keeps one runtime reason to change
- What we will not block on:
  - aesthetic package bikeshedding once the layered ownership rules are clear in the code and tests

## Blocker questions (ONLY if repo evidence cannot settle them)
- none
<!-- arch_skill:block:plan_enhancer:end -->

# 10) Decision Log (append-only)

## 2026-04-12 - Route from final JSON, not ledger prose

Context
- The master design now treats route-aware `final_output` as ready to implement, and the flow doctrine already models routed ownership edges separately from durable serialized notes.

Options
- Keep routing truth outside the final JSON and let notes or separate readback text imply where control goes next.
- Route from validated final-output JSON only and let Rally stamp normalized readback into `issue.md`.

Decision
- Route from validated final-output JSON only. There is no separate handoff artifact; Rally stamps normalized final-turn readback into `issue.md`.

Consequences
- The runtime must validate final-output JSON before dispatch.
- The runner must resolve `next_owner` structurally and fail loudly on invalid keys.
- Ledger append ordering and route handling must be implemented explicitly.

Follow-ups
- Verify the exact Doctrine-emitted surfaces Rally can consume without Markdown scraping.
- Add runner tests for invalid-owner failure and note-before-final-response ordering.

## 2026-04-12 - Notes stay non-routing and non-currentness

Context
- The shared stdlib now includes a dedicated issue-note surface with explicit guardrails against carrying routing or currentness truth.

Options
- Let notes influence pickup and routing when convenient.
- Keep notes as durable context only and preserve routing/currentness elsewhere.

Decision
- Notes preserve durable context only. They do not affect owner selection, currentness, or terminal control behavior.

Consequences
- The runner must append notes without changing state-machine decisions.
- Verification must include a proof that notes do not alter routing behavior.

Follow-ups
- Add ledger and runner coverage for note append behavior and note-before-final-response ordering.

## 2026-04-12 - No Markdown scraping fallback

Context
- Phase 4 needs machine-readable final-output and routing truth, while the design forbids reconstructing compiler meaning by scraping generated Markdown.

Options
- Scrape generated `AGENTS.md` until Doctrine emits more structure.
- Fail loudly and land the generic Doctrine support needed for a clean runtime boundary.

Decision
- No Markdown scraping fallback is allowed for Phase 4.

Consequences
- The first incremental implementation slice must make the compatibility boundary explicit.
- Missing compiler support is a real blocker, not a runtime excuse.

Follow-ups
- Confirm the paired Doctrine branch emits the required machine-readable semantic surfaces.

## 2026-04-12 - Use emitted AGENT.json as the Rally runtime final-output metadata sidecar

Context
- Doctrine already computes `CompiledFinalOutputSpec` in memory, and the current Rally build readback emits only `AGENTS.md`. Phase 4 needs a checked-in machine-readable sidecar for final-output schema metadata without recompiling prompts at runtime or scraping Markdown.

Options
- Teach Rally to scrape emitted `AGENTS.md` for final-output semantics.
- Teach Rally to compile prompts at runtime to recover semantic metadata.
- Extend Doctrine emit output so each agent directory ships `AGENT.json` beside `AGENTS.md`, then make Rally consume that sidecar.

Decision
- Use one compiler-owned emitted `AGENT.json` sidecar per agent directory as the Rally runtime final-output metadata contract.

Consequences
- Doctrine must serialize the relevant per-agent final-output metadata into emitted build output.
- Rally `flow_loader.py` becomes the single compatibility boundary that requires both `AGENTS.md` and `AGENT.json`.
- `home_materializer.py` must copy full emitted agent directories so the injected instruction payload and the emitted metadata sidecar stay archaeologically paired.
- Routed owner truth still has to live in the shared `rally.turn_results` schema rather than migrating into `AGENT.json`.

Follow-ups
- Extend Doctrine emit coverage to prove `AGENT.json` is written beside `AGENTS.md`.
- Recompile Rally flow build outputs once the paired Doctrine support lands.

## 2026-04-12 - Structural next_owner lives in the shared turn-result contract

Context
- The latest master design now makes routed ownership explicit: Rally should route from validated final JSON, and `handoff` must carry structural `next_owner` emitted from `route.next_owner.key`. The checked-in Rally stdlib schema is still behind that rule today.

Options
- Keep routed owner truth implicit in emitted metadata and infer the next owner from sidecar data.
- Keep routed owner truth outside the final JSON and let the final JSON only say `kind: handoff`.
- Put structural `next_owner` directly in the shared `rally.turn_results` JSON contract and let `AGENT.json` only point Rally at that schema.

Decision
- Put structural `next_owner` directly in the shared `rally.turn_results` JSON contract. Treat `AGENT.json` as metadata that identifies the enforced final-output schema, not as a second routing truth surface.

Consequences
- `stdlib/rally/prompts/rally/turn_results.prompt`, `stdlib/rally/schemas/rally_turn_result.schema.json`, and the shared example all need to align on the handoff branch.
- `flow_loader.py` and `result_contract.py` must validate that the resolved schema still requires `next_owner` on `handoff`.
- Rally should stamp normalized final-turn readback into `issue.md` and should not regain a separate handoff artifact.

Follow-ups
- Recompile Rally flow builds after the stdlib contract update and Doctrine emit support both land.
- Keep `_stdlib_smoke` proving the shared route-aware final-output contract, not a second handoff surface.

## 2026-04-12 - Phase 4 starts with compatibility-first cutover

Context
- The current repo is behind the latest routing contract in two separate places at once: the shared Rally stdlib handoff schema still omits structural `next_owner`, and Doctrine emit output still lacks `AGENT.json`. Starting runner work before fixing those boundaries would lock Rally runtime code to stale semantics.

Options
- Start implementing Rally runtime code first and patch the shared contract plus emitted metadata later.
- Land the shared Rally stdlib contract update, the paired Doctrine emit sidecar, and the Rally loader skeleton first, then build runner behavior on that fixed boundary.

Decision
- Phase 4 begins with a compatibility-first cutover: shared `rally.turn_results` alignment, paired Doctrine `AGENT.json` emit support, rebuild proof, then Rally loader skeleton and preflight.

Consequences
- Phase 1 spans Rally stdlib changes, paired Doctrine changes, and the narrow Rally preflight surface instead of pretending Rally runtime work can begin in isolation.
- `_stdlib_smoke` and `single_repo_repair` rebuild proof become part of the phase exit, not optional cleanup.
- Runner and adapter behavior should not be implemented against the pre-cutover schema.

Follow-ups
- Keep Section 7 and Section 8 aligned around that compatibility-first sequencing.

## 2026-04-12 - Keep the runtime layered and single-purpose from the first commit

Context
- There is no shipped Rally runtime yet, which makes this the cheapest moment to prevent the future implementation from collapsing into one oversized runner or a generic utility layer that owns everything by accident.

Options
- Start with a flatter package and clean it up later if it grows messy.
- Make the first implementation pass explicitly layered now: pure domain contracts, narrow services, adapter-only external IO, and an orchestration-only runner.

Decision
- Build the initial runtime as a layered package from the start: `cli`, pure `domain`, narrow `services`, and `adapters/codex`, with `services/runner.py` coordinating rather than absorbing owned logic.

Consequences
- The call-site audit and phase plan must name module ownership explicitly instead of only naming files.
- Unit coverage should mirror those seams so modularity is protected by typed boundaries and behavior-level tests rather than style policing.
- Future expansion can add flows or adapters without forcing a rewrite of one god module.

Follow-ups
- Keep code review focused on runner drift, generic-utils creep, and IO leaking into pure domain contracts during implementation.
