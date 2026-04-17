---
title: "Rally - First-Class Routing And Previous-Turn Patterns - Architecture Plan"
date: 2026-04-16
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_PORTING_GUIDE.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - stdlib/rally/prompts/rally/review_results.prompt
  - flows/_stdlib_smoke/prompts/AGENTS.prompt
  - flows/poem_loop/prompts/AGENTS.prompt
  - flows/software_engineering_demo/prompts/AGENTS.prompt
  - src/rally/domain/flow.py
  - src/rally/domain/turn_result.py
  - src/rally/services/flow_loader.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/runner.py
  - ../doctrine/docs/FIRST_CLASS_SELECTED_ROUTE_FINAL_OUTPUTS_2026-04-16.md
  - ../doctrine/docs/PREVIOUS_TURN_OUTPUT_INPUT_SOURCE_REFERENCES_2026-04-16.md
---

# TL;DR

## Outcome

Rally natively uses Doctrine's new route and previous-turn output contracts in
its runtime, its stdlib, and its shipped example flows.

Producer turns route through Doctrine route truth instead of payload
`next_owner` copies. Later agents can read the prior selected output in native
JSON or native text when Rally can reopen it honestly.

This plan limits previous-turn reopen to the immediate previous turn only.
Supported readback stays narrow: exact previous final JSON plus file-backed
structured JSON or readable text. Note-backed or other unsupported targets
fail loud.

The implementation stays Doctrine-first. Rally adopts Doctrine's intended
contract shape cleanly, and Rally stops for Doctrine feature work instead of
patching around framework gaps.

## Problem

Rally still treats producer routing as payload truth in `kind` plus
`next_owner`. Rally also injects only compiled `AGENTS.md`, so Doctrine's new
`io` contract for previous-turn inputs is not usable end to end.

That leaves Rally behind Doctrine, keeps old patterns alive in Rally examples,
and blocks a clean "agent B reads agent A's previous output" story.

## Approach

Teach Rally runtime to consume the richer single emitted contract file.

Use Doctrine route truth as the native producer routing source. Add Rally-owned
support for `RallyPreviousTurnOutput`. Rework Rally stdlib and Rally example
flows so they teach the new preferred pattern, not the old one.

Build one deterministic previous-turn appendix from emitted `io` metadata and
exact prior turn artifacts only. Do not scrape notes, summarize JSON, or infer
extra readback modes.

Keep review turns on the current review JSON path until Doctrine exposes a
clean review-side route-field surface.

Check every Rally move against Doctrine's intended owner path. If Rally hits a
missing Doctrine feature, stop and surface that framework gap instead of
inventing a Rally-local bridge.

## Plan

1. Add typed Rally loader and runtime support for Doctrine's emitted `route`
   selector data and top-level `io` block.
2. Cut Rally producer turn results over to the new route-first pattern in
   stdlib and runtime.
3. Add previous-turn packet injection in native form, with JSON kept as JSON
   and readable text kept as readable text.
4. Migrate Rally examples and proofs, including a new `Muse` loop in
   `poem_loop`.
5. Rewrite Rally docs and heavily comment the Rally stdlib so the shipped path
   is clear.

## Non-negotiables

- One runtime contract file: `final_output.contract.json`.
- No second routing model inside Rally.
- No prompt-side markdown summary of prior JSON outputs.
- No Rally-side workaround that fights Doctrine's intended shape.
- If Doctrine support is missing, stop in Rally and surface a Doctrine feature
  request.
- No new legacy Rally examples that teach producer `next_owner` copies as the
  preferred path.
- Review turns may keep `next_owner` only where Doctrine still requires the
  current review contract.
- Rally stdlib prompt source must carry strong comments at the canonical
  teaching boundaries.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-16
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit reran the final focused proof:
  - rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py tests/unit/test_issue_ledger.py tests/unit/test_cli.py -q`
    -> `188 passed`
  and also reran the full required Rally unit suite:
  - `uv run pytest tests/unit -q` -> `317 passed`
  The rebuilt flows, emitted contracts, runtime/test surfaces, and the six
  named live docs all match the approved plan.

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
deep_dive_pass_1: done 2026-04-16
external_research_grounding: done 2026-04-16 (not needed; Rally plus Doctrine repo grounding was sufficient)
deep_dive_pass_2: done 2026-04-16
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

If Rally adopts Doctrine's landed `route field` and previous-turn `io`
contracts as first-class runtime truth, then Rally can:

- route producer turns from Doctrine route metadata instead of payload
  `next_owner`
- let agent `t+1` read agent `t`'s selected prior output in native JSON or
  native text
- teach the new pattern through Rally stdlib, `_stdlib_smoke`, `poem_loop`,
  and `software_engineering_demo`

This claim is false if any of these stay true after the work:

- Rally producer routing still depends on payload `next_owner` as the main
  source of truth
- Rally still injects only `AGENTS.md`
- Rally examples still teach old producer routing as the preferred path
- previous-turn JSON is still flattened into prose before the next agent sees
  it

## 0.2 In scope

- Rally runtime support for Doctrine top-level `route.selector` and top-level
  `io` metadata in `final_output.contract.json`
- Rally runtime support for `RallyPreviousTurnOutput`
- native previous-turn prompt packets for:
  - the immediate previous turn only
  - exact previous final-output JSON
  - explicit prior selected file-backed structured JSON outputs
  - explicit prior selected file-backed readable text outputs
- Rally stdlib producer contract updates in `rally.turn_results`
- Rally stdlib source comments that explain the new preferred producer routing
  and previous-turn patterns
- Rally example migrations for:
  - `_stdlib_smoke`
  - `poem_loop`
  - `software_engineering_demo`
- a new `Muse` path in `poem_loop` so the shipped flow proves previous-turn
  JSON handoff and route-first producer control
- Rally docs updates in:
  - `docs/RALLY_MASTER_DESIGN.md`
  - `docs/RALLY_RUNTIME.md`
  - `docs/RALLY_COMMUNICATION_MODEL.md`
  - `docs/RALLY_PORTING_GUIDE.md`
  - `docs/RALLY_CLI_AND_LOGGING.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md`
- tests and proof paths needed to show behavior stayed correct while the
  routing owner changed

Allowed architectural convergence scope:

- refactor Rally producer control parsing so it reads route truth from Doctrine
  contract metadata
- reshape Rally-owned producer turn-result prompt source
- delete or rewrite Rally-owned example patterns that keep old producer routing
  alive
- add high-value prompt comments in Rally stdlib where future readers would
  otherwise drift back to the old pattern

Compatibility posture for this draft:

- clean cutover for Rally-owned producer patterns in stdlib and shipped Rally
  examples
- preserve the current review final JSON path until Doctrine adds clean review
  parity
- do not add a long-lived Rally-side producer bridge that keeps two preferred
  routing stories alive

## 0.3 Out of scope

- new Doctrine language work unless Rally uncovers a real Doctrine blocker
- review-side `final_output.route` authoring in Doctrine v1
- GUI, dashboard, or extra control-plane work
- parser-heavy extraction from prose outputs
- a second runtime sidecar contract file
- Rally-local shims that hide Doctrine feature gaps
- previous-turn reopen beyond the immediate previous turn
- note-backed previous-output reopen until Rally has declaration-keyed note
  artifacts
- speculative new example flows beyond what is needed to prove the pattern in
  Rally's shipped examples

## 0.4 Definition of done (acceptance evidence)

- Rally runtime loads Doctrine's richer single-file contract and uses it during
  producer routing and previous-turn readback
- Rally producer routing works from Doctrine route truth on Rally-owned
  producer outputs
- Rally can inject previous-turn JSON in native JSON form
- Rally can inject readable previous outputs in native readable form where that
  support is in scope
- Rally supports only immediate previous-turn reopen, and only for exact
  previous final JSON plus file-backed structured or readable outputs
- `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` all teach the
  new preferred producer routing path
- `poem_loop` has a real `Muse -> Writer -> Critic` proof path that uses
  previous-turn JSON
- Rally docs teach one clear producer story, one clear review story, and one
  clear previous-turn input story
- `docs/RALLY_CLI_AND_LOGGING.md` and
  `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` match that same shipped
  truth in the same pass
- Rally stdlib prompt source is heavily commented at the main pattern
  boundaries
- focused Rally tests and rebuild proofs pass
- every Rally-side design choice stays consistent with Doctrine's authored
  language and emitted-contract intent
- any missing Doctrine support discovered during the work is surfaced as a
  clear Doctrine feature request instead of being patched around in Rally
- unsupported previous-turn cases fail loud, including:
  - missing `io` or binding metadata
  - unreadable prior artifacts
  - contract-mode mismatches after reopen
  - note-backed or other unsupported target kinds

Behavior-preservation evidence:

- existing producer flows still reach the same next owner decisions after the
  routing owner moves
- review flows still route and finish through the current review control path
- guarded run behavior, issue-ledger behavior, and final JSON stop states stay
  intact

## 0.5 Key invariants (fix immediately if violated)

- One producer routing owner: Doctrine route contract, not copied payload
  `next_owner`
- One review routing owner for now: Rally review fields
- One runtime contract file
- No Rally-side laundering of Doctrine gaps into local runtime hacks
- No silent fallback from missing route metadata to guessed routing
- Structured prior outputs stay structured
- Readable prior outputs stay readable
- No new parallel example patterns that teach the old producer path
- No low-comment Rally stdlib rewrite that hides the new patterns from future
  readers

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make Rally use Doctrine's landed contract shapes as the real runtime owner.
2. Keep the Rally design maximally elegant per Doctrine intent.
3. Make Rally's shipped examples teach the best path by default.
4. Keep producer control and review control separate where Doctrine still
   separates them.
5. Keep prior-output readback honest. Do not fake structure.
6. Leave strong code comments in Rally stdlib at the main pattern seams.

## 1.2 Constraints

- Rally only loads one emitted runtime contract file today.
- Rally producer turns still parse `kind` plus payload `next_owner`.
- Rally prompt assembly still injects only `AGENTS.md`.
- Doctrine review-driven agents do not support `final_output.route` in v1.
- Rally docs currently teach the old producer control shape.
- This work must not degrade into "make Rally work somehow." It must stay
  aligned with Doctrine's intended ownership and emitted-contract shape.
- The previous-turn path in this plan stops at the immediate previous turn and
  exact reopenable artifacts only.

## 1.3 Architectural principles (rules we will enforce)

- Route producer turns from Doctrine route metadata.
- Keep review turns on the current review path until Doctrine offers clean
  parity.
- If Rally hits a Doctrine gap, stop and surface the needed Doctrine feature
  instead of inventing a local workaround.
- Reopen prior outputs from the actual immediately previous turn only.
- Prefer one clear preferred pattern in Rally-owned examples.
- Comment the canonical Rally stdlib boundaries where future ports will copy
  from.

## 1.4 Known tradeoffs (explicit)

- A clean producer cutover is sharper than a long compatibility bridge, but it
  keeps Rally's shipped patterns honest.
- Review and producer lanes will still differ for one phase because Doctrine
  v1 differs there.
- Some desired elegance may depend on Doctrine support that is not shipped yet.
  If that happens, the right move is to stop and name the Doctrine feature.
- Adding strong stdlib comments adds prompt-source prose, but this is one of
  the few places where the extra cost pays for itself by preventing drift.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Rally has a solid run model, a single final JSON read path, and Doctrine-built
agent packages. Rally also already ships review-native final JSON support.

Doctrine has now landed first-class route-field final outputs and additive
previous-turn `io` metadata.

## 2.2 What's broken / missing (concrete)

- Rally producer routing still centers payload `next_owner`
- Rally stdlib still teaches the old producer turn-result shape
- Rally examples still model old producer routing patterns
- Rally does not load or use Doctrine's `io` block
- Rally does not inject prior outputs into the next prompt in native form

## 2.3 Constraints implied by the problem

- The new runtime owner path must stay single-file and Doctrine-native.
- The fix must cover runtime, stdlib, examples, docs, and comments together.
- Rally must not pretend review parity exists where Doctrine does not yet ship
  it.
- Rally must not compensate for missing Doctrine semantics with shadow
  contracts, guessed metadata, or extra control planes.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal "ground truth")

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/FIRST_CLASS_SELECTED_ROUTE_FINAL_OUTPUTS_2026-04-16.md` —
  adopt — this is the Doctrine design note for first-class producer routing
  through `final_output.route` and emitted route metadata. Rally should consume
  this shape instead of copying producer route truth into payload
  `next_owner`.
- `../doctrine/docs/PREVIOUS_TURN_OUTPUT_INPUT_SOURCE_REFERENCES_2026-04-16.md`
  — adopt — this is the Doctrine design note for previous-turn input sources
  and the additive top-level `io` contract. Rally should reopen prior output
  through this emitted metadata instead of inventing a second handoff sidecar.
- No outside prior-art system is needed yet — reject for now — the deciding
  truth is shipped Doctrine plus shipped Rally behavior, and outside analogies
  would not settle ownership boundaries better than the local repos do.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/domain/turn_result.py` — producer handoff parsing still
    requires payload `next_owner`.
  - `src/rally/services/final_response_loader.py` — producer final JSON still
    routes through `parse_turn_result`, while review final JSON routes through
    review fields.
  - `src/rally/services/flow_loader.py` — compiled producer schemas are still
    validated against the old `kind` plus `next_owner` turn-result surface.
  - `src/rally/domain/flow.py` — `CompiledAgentContract` still stops at
    `final_output` and `review`; there is no typed `route` or `io` surface
    yet.
  - `src/rally/services/runner.py` — prompt assembly still injects only
    compiled `AGENTS.md`.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — Rally's shared producer
    contract still teaches `handoff` plus `next_owner`.
  - `stdlib/rally/prompts/rally/review_results.prompt` — Rally's shared review
    lane still teaches review-side `next_owner`, which remains the honest
    review control surface for now.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — Rally stdlib base does
    not define `RallyPreviousTurnOutput`.
  - `../doctrine/doctrine/emit_docs.py` — Doctrine already emits top-level
    `route.selector`, `route.branches`, and top-level
    `io.previous_turn_inputs`, `io.outputs`, and `io.output_bindings`.
  - `../doctrine/tests/test_emit_docs.py` — Doctrine already proves emitted
    previous-turn IO metadata and output bindings.
  - `../doctrine/doctrine/_compiler/validate/agents.py` — Doctrine v1 still
    rejects `final_output.route` on review-driven agents.
- Canonical path / owner to reuse:
  - `../doctrine/doctrine/emit_docs.py` plus the Doctrine route and
    previous-turn docs — Doctrine owns authored semantics and emitted metadata
    shape for producer route truth and previous-turn IO.
  - `src/rally/services/flow_loader.py`,
    `src/rally/services/final_response_loader.py`, and
    `src/rally/services/runner.py` — Rally should only load, validate, and
    execute Doctrine's emitted truth. Rally should not re-author route
    semantics or create a second prior-output contract.
- Adjacent surfaces tied to the same contract family:
  - `stdlib/rally/prompts/rally/base_agent.prompt`,
    `stdlib/rally/prompts/rally/turn_results.prompt`, and
    `stdlib/rally/prompts/rally/review_results.prompt` — the canonical shared
    prompt owners must move with the runtime or Rally will teach two different
    stories.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`,
    `flows/poem_loop/prompts/AGENTS.prompt`, and
    `flows/software_engineering_demo/prompts/AGENTS.prompt` — the shipped
    examples are the main proof and teaching surfaces for the migration.
  - `flows/*/build/**` — build readback must be regenerated and inspected
    after prompt changes because Doctrine owns the emitted contract.
  - `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`,
    `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_PORTING_GUIDE.md`,
    `docs/RALLY_CLI_AND_LOGGING.md`, and
    `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` — the docs set
    currently teaches the old producer story and must converge in the same
    pass.
- Compatibility posture (separate from `fallback_policy`):
  - clean cutover for Rally-owned producer patterns — Doctrine already has a
    first-class route surface, so keeping payload `next_owner` as a parallel
    preferred producer path would preserve duplicate truth instead of
    protecting behavior.
  - preserve the current review final JSON lane for now — Doctrine v1 does not
    yet support review-side `final_output.route`, so this is a real framework
    boundary, not a Rally preference.
- Existing patterns to reuse:
  - `../doctrine/examples/120_route_field_final_output_contract` and
    `../doctrine/examples/121_nullable_route_field_final_output_contract` —
    reuse as the canonical route-field producer examples when shaping Rally's
    producer contract and example rebuild checks.
  - `../doctrine/tests/test_emit_docs.py` — reuse as the contract-grounding
    proof for previous-turn `io` emission instead of guessing what Rally
    should load.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt` — reuse its simple
    route-choice example, but remove the old payload `next_owner` copy once
    Rally can route from Doctrine metadata directly.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt` — canonical producer
    final-output owner to rewrite and heavily comment.
  - `stdlib/rally/prompts/rally/review_results.prompt` — canonical review lane
    to keep separate and explicitly documented as separate.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — canonical place to add
    Rally-owned previous-turn source support and source comments.
  - `flows/poem_loop/prompts/AGENTS.prompt` — best place to prove real
    previous-turn JSON reuse with the planned `Muse -> Writer -> Critic` loop.
- Native model or agent capabilities to lean on:
  - Doctrine plus the adapters already give Rally structured JSON final outputs
    through `TurnResponse`; no prose summarizer is needed to carry prior
    structured output forward.
  - Rally already passes exact compiled prompt text and can reopen exact files
    under the run home; readable previous-turn inputs can stay readable
    without a translation layer.
- Existing grounding / tool / file exposure:
  - `src/rally/adapters/base.py` and `src/rally/services/final_response_loader.py`
    — Rally already has one stable per-turn `last_message.json` path and one
    JSON loader for final outputs.
  - `home:issue.md` and the existing run-home materialization rules keep
    shared context and per-turn artifacts local to the run; previous-turn
    support does not need a new global store.
- Duplicate or drifting paths relevant to this change:
  - `src/rally/domain/turn_result.py` plus
    `stdlib/rally/prompts/rally/turn_results.prompt` plus flow-local producer
    outputs — these currently duplicate producer route truth outside
    Doctrine's emitted `route` contract.
  - `docs/RALLY_MASTER_DESIGN.md` and `docs/RALLY_COMMUNICATION_MODEL.md` —
    these still describe the old producer-control surface and only
    `AGENTS.md` injection.
- Capability-first opportunities before new tooling:
  - load Doctrine's emitted `route` and `io` metadata directly — this removes
    the need for a Rally-local routing shim or prompt-side handoff parser.
  - inject exact previous-turn JSON or text from existing run artifacts — this
    removes the need for a summarizer, converter, or second handoff file
    format.
- Behavior-preservation signals already available:
  - `tests/unit/domain/test_turn_result_contracts.py` — protects current
    turn-result parsing behavior while the producer owner path changes.
  - `tests/unit/test_flow_loader.py` — protects contract loading and schema
    validation behavior.
  - `tests/unit/test_final_response_loader.py` — protects final JSON loading
    and review parsing behavior.
  - `tests/unit/test_runner.py` — protects run-home prompt assembly, session
    artifacts, and example-flow execution paths.
  - Doctrine example rebuilds and emitted `final_output.contract.json`
    inspection — protect the Doctrine-first contract shape Rally plans to
    consume.

## 3.3 Decision gaps that must be resolved before implementation

- None today. Repo evidence already settles the main planning choices:
  Doctrine owns producer route and previous-turn metadata, Rally should take a
  clean producer cutover, and review lanes should stay on the current review
  path until Doctrine ships review-side route-field parity. If a later
  deep-dive pass proves that the elegant Rally design needs review-side
  `final_output.route` or richer emitted metadata than Doctrine ships today,
  stop there and surface the exact Doctrine feature request instead of
  widening Rally.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Authored Rally prompt source lives in:
  - `stdlib/rally/prompts/rally/*.prompt`
  - `flows/*/prompts/**`
- Doctrine build output lives in `flows/*/build/agents/<slug>/` with:
  - `AGENTS.md`
  - `final_output.contract.json`
  - `schemas/*.schema.json`
  - optional peer files such as `SOUL.md`
- Run-local runtime state lives under `runs/<run-id>/home/` with:
  - `agents/<slug>/AGENTS.md` as the copied compiled readback
  - `sessions/<slug>/turn-###/last_message.json`, `exec.jsonl`, and
    `stderr.log` as per-turn adapter artifacts
  - `issue.md` plus `issue_history/` as the shared run ledger
- Current Rally builds already can contain Doctrine `route` metadata. For
  example, `_stdlib_smoke` `plan_author` and `poem_loop` `poem_critic` already
  emit `route.exists: true`. Current Rally builds do not emit useful `io`
  metadata because Rally stdlib does not yet declare `RallyPreviousTurnOutput`.

## 4.2 Control paths (runtime)

1. Build path
   - `src/rally/services/flow_build.py` rebuilds a flow through Doctrine into
     `flows/<flow>/build/agents/**`.
2. Load path
   - `src/rally/services/flow_loader.py` loads `flow.yaml`, then each compiled
     agent package.
   - It loads `final_output` and optional `review`.
   - For producer agents it still validates the emitted schema as the classic
     five-control-key shape, including `next_owner`.
   - It ignores emitted producer `route.selector` and any top-level `io`
     block.
3. Prompt path
   - `src/rally/services/runner.py` copies compiled readback into the run
     home.
   - `_build_agent_prompt()` returns only the compiled `AGENTS.md` text.
4. Final JSON path
   - adapters write one `last_message.json` per turn
   - `src/rally/services/final_response_loader.py` loads that JSON
   - producer turns call `parse_turn_result()` and therefore still require
     payload `kind` plus payload `next_owner` for handoffs
   - review turns use emitted review field paths and already support
     control-ready review JSON
5. Route execution path
   - `src/rally/services/runner.py` turns
     `HandoffTurnResult.next_owner` into the next `FlowAgent` through
     `_resolve_next_agent()`
   - `home:issue.md` gets a `Rally Turn Result` block with the full payload,
     but that ledger is history and summary, not a typed readback source
6. Missing path today
   - there is no previous-turn selector resolver
   - there is no output-binding loader
   - there is no previous-output readback dispatcher
   - there is no declaration-keyed mirror path for note outputs

## 4.3 Object model + key abstractions

- `src/rally/domain/flow.py`
  - `CompiledAgentContract` holds `final_output` and `review` only
  - there is no typed `route` model
  - there is no typed `io` model
- `src/rally/domain/turn_result.py`
  - producer runtime control is reduced to:
    - `HandoffTurnResult(next_owner)`
    - `DoneTurnResult(summary)`
    - `BlockerTurnResult(reason)`
    - `SleepTurnResult(reason, sleep_duration_seconds)`
- `src/rally/services/final_response_loader.py`
  - review already has a richer `LoadedReviewTruth`
  - producer turns do not have an equivalent route-aware truth object
- `src/rally/services/issue_ledger.py`
  - `IssueCurrentView` exposes latest turn result, latest note, and latest
    blocked block
  - it is not keyed by output identity
  - Rally notes are append-only ledger blocks, not declaration-keyed output
    artifacts

Result: Rally has one small runtime state machine, but its producer handoff
path still depends on payload-owned routing truth instead of Doctrine's emitted
route truth.

## 4.4 Observability + failure behavior today

- Loader failures are loud for:
  - missing compiled package files
  - bad flow config
  - missing emitted schemas
  - bad review metadata
  - unsupported `format_mode`
- Runtime failures are loud for:
  - missing or invalid `last_message.json`
  - bad `next_owner`
  - missing review fields
  - sleep requests
- The quiet drift today is producer routing:
  - Doctrine can emit a real `route` block
  - Rally still ignores it and routes from payload `next_owner`
- Previous-turn support is absent end to end:
  - no Rally stdlib source
  - no emitted `io` read path in Rally builds
  - no runtime reopen path for prior outputs

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope. The operator surfaces remain the CLI, run files, and
compiled build readback.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

The future on-disk shape stays intentionally small:

- keep one emitted metadata file:
  - `final_output.contract.json`
- keep one emitted schema path family:
  - `schemas/*.schema.json`
- keep `AGENTS.md` as the only static compiled instruction readback file
- add no second runtime metadata sidecar

The only new run-local artifact this plan allows is one derived turn-local
appendix file for archaeology:

- `home/sessions/<agent>/turn-###/previous_turn_inputs.md`

That file is not authored instruction and not a second control path. It is the
saved copy of the exact previous-turn appendix Rally injects for that turn when
the compiled agent declares previous-turn inputs.

## 5.2 Control paths (future)

### Producer routing

Rally-owned producer control moves to one route-first shape:

- `kind`, `summary`, `reason`, and `sleep_duration_seconds` stay as Rally's
  stop, blocker, and sleep fields
- payload `next_owner` leaves the Rally-owned producer contract
- handoff-capable producer outputs add a nullable route field, then bind it
  with `final_output.route`

That gives Rally one producer story:

- `kind == "handoff"` means Rally should route
- the selected next owner comes from Doctrine `route.selector` and
  `route.branches`
- `null` route on a nullable route field means no route was selected on that
  turn

After the cutover, Rally-owned producer prompts and shipped examples do not use
payload `next_owner` at all.

### Load and validate

`src/rally/services/flow_loader.py` becomes the single Rally loader for the
richer Doctrine file. It will load:

- `final_output`
- `route`
- `review`
- `io`

Producer validation changes with that load:

- producer contracts that route must have emitted `route.selector`
- producer contracts keep Rally's classic stop, blocker, and sleep fields
- producer contracts no longer require payload `next_owner`
- review contracts keep the current review validation path

### Final JSON parsing and route execution

`src/rally/services/final_response_loader.py` becomes route-aware for producer
turns:

1. load the raw payload once
2. read the Rally stop fields from the payload
3. if the compiled producer contract has `route.selector` and the payload says
   `kind == "handoff"`, resolve the selected branch from the emitted
   `field_path` and `branches`
4. return the same small runtime `TurnResult` objects Rally already uses, with
   `HandoffTurnResult.next_owner` derived from Doctrine metadata instead of
   payload `next_owner`
5. fail loud on contradictions such as:
   - `handoff` with no selected route
   - non-handoff with a selected route
   - unknown route member
   - `null` where the selector says `null_behavior: invalid`

`src/rally/services/runner.py` keeps the same state machine. The runtime still
routes by turning a `HandoffTurnResult` into the next `FlowAgent`. The only
owner change is how that `HandoffTurnResult` is derived.

### Previous-turn inputs

`stdlib/rally/prompts/rally/base_agent.prompt` adds
`input source RallyPreviousTurnOutput` as the Rally-owned source declaration.

`src/rally/services/runner.py` then builds previous-turn inputs in one strict
path:

1. look only at the immediate previous turn in the same run
2. load the previous agent's compiled `io` and exact turn artifacts
3. resolve each current-agent `io.previous_turn_inputs` entry by
   `selector_kind`
4. use the previous agent's `io.outputs` and `io.output_bindings` to map
   explicit declaration selectors and binding selectors back to one emitted
   output contract
5. reopen the exact prior artifact that the emitted metadata points at
   according to that resolved output contract
6. validate that the reopened artifact still matches the current input's
   derived contract mode
7. render one deterministic appendix in current-input order and append it after
   compiled `AGENTS.md`
8. save the same appendix into
   `home/sessions/<agent>/turn-###/previous_turn_inputs.md`

The runtime appendix is data only. It should use one predictable shape:

```md
## Previous Turn Inputs

### Previous Turn Result
- Source Agent: `poem_writer`
- Selector Kind: `default_final_output`
- Output Key: `PoemWriterTurnResult`
- Contract Mode: `structured_json`

```json
{ ...exact previous JSON... }
```
```

For readable text, keep the same header lines and render the exact text body in
one fenced text block. Do not summarize or restate it.

The resolver supports only these selector kinds:

- `default_final_output`
- `output_decl`
- `output_binding`

Each kind must resolve through emitted contract truth:

- `default_final_output`
  - reopen the previous turn's actual `final_output`
  - for structured JSON final outputs, read `last_message.json`
- `output_decl`
  - resolve the selected declaration key through the previous agent's
    `io.outputs`
- `output_binding`
  - resolve the selected binding path through the previous agent's
    `io.output_bindings`, then join back to `io.outputs` by declaration key

The readback dispatcher is intentionally narrow and explicit:

- `structured_json` from `TurnResponse`
  - valid only when the selected declaration is the actual previous
    `final_output`
  - reopen the previous turn's `last_message.json`
- `structured_json` from file-backed outputs
  - reopen the declared file path before the current turn starts and keep it as
    JSON
- `readable_text` from file-backed outputs
  - reopen the declared file path before the current turn starts and keep it as
    readable text
- `readable_text` from Rally note targets
  - unsupported in this plan
- every other target or readback mode
  - fail loud with the exact unsupported combination

This plan does not turn `home:issue.md` into a previous-output database.
Previous-turn readback comes from exact prior turn artifacts, not by scraping
the ledger.

The note-target exclusion is deliberate. Today's note path writes append-only
ledger blocks through `rally issue note`, but it does not record which output
declaration produced which note body. Without declaration-keyed note artifacts,
Rally cannot reopen a prior note output exactly. The clean future path would be
declaration-keyed output mirrors, not ledger scraping, but that is outside this
plan.

### Review routing

Review routing stays where it is today:

- review final JSON still routes through emitted review field paths
- review turns do not use `final_output.route` until Doctrine supports that
  cleanly

## 5.3 Object model + abstractions (future)

`src/rally/domain/flow.py` grows typed metadata for the richer Doctrine file:

- `RouteSelectorContract`
- `RouteChoiceMemberContract`
- `RouteBranchContract`
- `RouteContract`
- `PreviousTurnInputContract`
- `OutputReadbackContract`
- `OutputBindingContract`
- `IoContract`

`CompiledAgentContract` then carries:

- `final_output`
- `route`
- `review`
- `io`

`src/rally/domain/turn_result.py` stays the small runtime state type. Rally
does not add a second state machine. `HandoffTurnResult.next_owner` remains the
runtime handoff value, but it becomes derived truth, not wire truth.

To keep the runner from getting even larger, previous-turn resolution and
appendix rendering should live in a dedicated Rally service module rather than
being inlined into `runner.py`.

## 5.4 Invariants and boundaries

- Doctrine owns authored route and previous-turn meaning.
- Rally owns loading, exact artifact reopen, appendix rendering, and next-agent
  execution.
- Rally-owned producer prompts and examples do not carry payload `next_owner`
  after this cutover.
- Review routing stays on review fields until Doctrine changes.
- Previous-turn selectors always mean the exact immediately previous turn in
  the same run.
- `AGENTS.md` stays the only static compiled instruction readback file.
- The runtime previous-turn appendix is data only. It is not a second authored
  instruction source.
- Unsupported readback modes or target kinds fail loud.
- `home:issue.md` remains history and summary, not the typed previous-output
  store.
- Note-backed previous-output reopen stays out until Rally has
  declaration-keyed note artifacts.

If this split stops being enough for a clean implementation, the plan must stop
and ask for Doctrine support instead of widening Rally.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI work is expected.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Domain metadata | `src/rally/domain/flow.py` | `CompiledAgentContract`, `FinalOutputContract` | Loads only `final_output` and `review`. | Add typed `route` and `io` metadata models. | Rally must load the full Doctrine file instead of only the old subset. | `RouteContract` and `IoContract` become part of the compiled agent model. | `tests/unit/domain/test_flow_contracts.py`, `tests/unit/test_flow_loader.py` |
| Producer schema validation | `src/rally/services/flow_loader.py` | `_load_compiled_agent_contract()`, `_validate_turn_result_schema()` | Producer schemas must include `next_owner`. | Validate route-first producer schemas, parse `route` and `io`, and reject handoff producers with no emitted route selector. | One producer routing owner after cutover. | Producer loader understands `route.selector`, `route.branches`, `io.previous_turn_inputs`, `io.outputs`, and `io.output_bindings`. | `tests/unit/test_flow_loader.py` |
| Producer runtime parse | `src/rally/services/final_response_loader.py` | `load_agent_final_response()`, `load_turn_result()` | Producer handoffs read payload `next_owner`; review path is already richer. | Derive producer handoffs from emitted route metadata while keeping the review path as-is. | Rally must route from Doctrine truth, not copied wire fields. | Route-aware producer final-response loader. | `tests/unit/test_final_response_loader.py` |
| Runtime result types | `src/rally/domain/turn_result.py` | `parse_turn_result()`, `HandoffTurnResult` | `parse_turn_result()` requires `next_owner` on producer handoffs. | Remove payload `next_owner` from the producer parse path and keep `HandoffTurnResult` as derived runtime truth. | Keep one small runtime state type without a second state machine. | `HandoffTurnResult(next_owner)` stays, but `next_owner` becomes derived. | `tests/unit/domain/test_turn_result_contracts.py` |
| Prompt build | `src/rally/services/runner.py` | `_build_agent_prompt()` | Injects only compiled `AGENTS.md`. | Append the deterministic previous-turn appendix when the compiled agent declares previous-turn inputs. | Otherwise `RallyPreviousTurnOutput` never reaches the model. | Prompt text becomes `AGENTS.md` plus a runtime-built previous-turn appendix. | `tests/unit/test_runner.py` |
| Previous-turn resolver | `src/rally/services/previous_turn_inputs.py` | new service module | No resolver exists. | Add one dedicated service that resolves the immediate previous turn, reopens exact artifacts, and renders the appendix. | Keep `runner.py` from growing further and keep the reopen rules in one owner. | Immediate-previous-turn resolver plus appendix renderer. | `tests/unit/test_runner.py` |
| Turn artifact layout | `src/rally/adapters/base.py` | `TurnArtifactPaths`, `prepare_adapter_turn_artifacts()` | Tracks `last_message.json`, `exec.jsonl`, and `stderr.log`. | Add `previous_turn_inputs.md` as the saved copy of the runtime appendix. | Keep run archaeology bundled under the existing turn folder. | One new turn-local appendix artifact path. | `tests/unit/test_runner.py`, `docs/RALLY_CLI_AND_LOGGING.md` |
| Note path boundary | `src/rally/cli.py`, `src/rally/services/issue_ledger.py`, `skills/rally-kernel/prompts/SKILL.prompt` | `rally issue note`, `append_issue_note()` | Notes append to `home:issue.md` and may carry flat labels, but they are not tied back to emitted output declarations. | Keep the note path unchanged in this plan and explicitly reject note-backed previous-output reopen. | Scraping the ledger would create a shadow output store and lose exact declaration identity. | No new note-readback contract in this plan. | `tests/unit/test_issue_ledger.py`, `tests/unit/test_cli.py`, docs alignment |
| State transition and logs | `src/rally/services/runner.py` | `_state_from_turn_result()`, `_turn_result_issue_detail_lines()`, `_resolve_next_agent()` | Routes producer handoffs from payload-owned `next_owner` and logs that field. | Keep the state machine but treat producer handoff targets as route-derived and keep issue logs honest about the new path. | Logging must match the new owner path. | Same runtime state machine, route-derived producer handoffs. | `tests/unit/test_runner.py` |
| Rally stdlib source | `stdlib/rally/prompts/rally/base_agent.prompt` | shared base source declarations | No previous-turn source exists. | Add `input source RallyPreviousTurnOutput` and comment it heavily. | Rally should own Rally-specific source behavior in one shared layer. | New Rally-owned input source declaration. | `tests/unit/test_shared_prompt_ownership.py`, Doctrine rebuild proof |
| Rally stdlib producer family | `stdlib/rally/prompts/rally/turn_results.prompt` | `BaseRallyTurnResultSchema`, `RallyTurnResult` | Shared producer shape still teaches `next_owner`. | Rewrite the producer family around Rally status fields plus a route field and strong teaching comments. | Shipped Rally examples should inherit the new preferred path by default. | Route-first shared producer output family. | `tests/unit/test_shared_prompt_ownership.py`, `tests/unit/test_flow_build.py`, rebuilt flow checks |
| Rally stdlib review family | `stdlib/rally/prompts/rally/review_results.prompt` | review output family | Review lane already owns review control. | Keep the lane, but update comments so producer and review routing stay clearly separate. | Review parity is a real Doctrine boundary today. | Review stays on review fields. | Rebuilt flow checks, docs alignment |
| Smoke example | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | `PlanAuthorTurnResult`, `RouteRepairTurnResult` | Copies `route.next_owner.key` into payload `next_owner`. | Switch both producer handoff paths to `final_output.route` and route-field outputs. | `_stdlib_smoke` should be the smallest proof of route-first producer control. | Route-first producer example. | rebuilt `_stdlib_smoke`, `tests/unit/test_flow_build.py` |
| Poem loop example | `flows/poem_loop/prompts/AGENTS.prompt` and related role/shared prompts | `PoemWriter`, `PoemCritic` | Writer still hands off through payload `next_owner`; no `Muse`; no previous-turn input. | Add `Muse`, move producer routing to route-first outputs, and add previous-turn JSON inputs where Writer and Muse need them. | `poem_loop` is the main real proof for previous-turn JSON. | `Muse -> Writer -> Critic` route-first proof path. | rebuilt `poem_loop`, `tests/unit/test_runner.py`, `tests/unit/test_flow_loader.py` |
| Software engineering example | `flows/software_engineering_demo/prompts/AGENTS.prompt` and shared prompt files | producer agents using `rally.turn_results.RallyTurnResult` | Producers still inherit the old `next_owner` shape. | Move producer agents to the route-first shared family and keep review agents on review fields. | The full demo should teach the same producer story as stdlib and smoke. | Route-first producers, unchanged review lane. | rebuilt `software_engineering_demo`, `tests/unit/test_runner.py`, prompt-input tests as needed |
| Built readback | `flows/_stdlib_smoke/build/**`, `flows/poem_loop/build/**`, `flows/software_engineering_demo/build/**` | generated `AGENTS.md`, schemas, `final_output.contract.json` | Current builds still teach the old producer path and do not prove previous-turn IO. | Rebuild and inspect the emitted route selector and IO blocks after every source change. | Doctrine is the source of truth for emitted behavior. | No hand-edited build output; all proof comes from rebuilds. | `tests/unit/test_flow_build.py`, rebuild inspection |
| Runtime and design docs | `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_PORTING_GUIDE.md`, `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` | current producer routing and prompt-build claims | Several docs still teach the classic producer `next_owner` story and AGENTS-only prompt injection. | Rewrite the producer story, previous-turn appendix story, kept review lane, new turn artifact, and the example proofs. | Live docs must not preserve stale owner claims after the cutover. | One clear producer story, one clear review story, one clear previous-turn story. | Docs proof by aligned readback and updated examples |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - Doctrine owns authored `final_output.route` and `RallyPreviousTurnOutput`.
  - Rally owns one load path in `flow_loader.py`, one producer parse path in
    `final_response_loader.py`, and one previous-turn appendix path in the
    runtime.
- Deprecated APIs (if any):
  - Rally-owned producer `next_owner` in `rally.turn_results`
  - flow-local producer payload `next_owner` copies in shipped examples
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - old producer `next_owner` field ownership in stdlib prompt source
  - old producer `next_owner` copies in `_stdlib_smoke`, `poem_loop`, and
    `software_engineering_demo`
  - doc claims that Rally producer routing reads only the classic five keys
  - doc claims that runner prompt build is compiled `AGENTS.md` only
- Adjacent surfaces tied to the same contract family:
  - built example packages under `flows/*/build/**`
  - unit tests that assert producer `next_owner`
  - docs that describe turn-result and turn-artifact behavior
  - note-path docs and tests that must keep saying notes are context only
- Compatibility posture / cutover plan:
  - clean cutover for Rally-owned producer paths
  - keep review routing on the current review lane
  - support previous-turn reopen for exact prior final JSON and file-backed
    outputs only
  - fail loud on note-backed or otherwise unsupported previous-output target
    kinds instead of adding a shim
- Capability-replacing harnesses to delete or justify:
  - do not add a second routing resolver outside the compiled contract loader
  - do not add a prose summarizer for previous JSON outputs
  - do not use `home:issue.md` as a fake typed previous-output store
- Live docs/comments/instructions to update or delete:
  - producer comments in `turn_results.prompt`
  - review-lane boundary comments in `review_results.prompt`
  - communication and runtime docs that still teach AGENTS-only prompt build
  - showcase docs that would otherwise keep the old example story alive
- Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/domain/test_turn_result_contracts.py`
  - `tests/unit/test_runner.py`
  - `tests/unit/test_flow_build.py`
  - Doctrine rebuild inspection for the three shipped example flows

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared producer control | `stdlib/rally/prompts/rally/turn_results.prompt` plus all shipped producer outputs | Route-first producer handoff through `final_output.route` | Prevents Rally from teaching both route metadata and payload `next_owner` as equal owners. | include |
| Shared review control | `stdlib/rally/prompts/rally/review_results.prompt` and shipped review outputs | Keep review fields as the only review routing owner | Prevents false review parity claims while Doctrine v1 still differs. | include |
| Previous-turn source | `stdlib/rally/prompts/rally/base_agent.prompt` and runtime appendix path | `RallyPreviousTurnOutput` plus exact-artifact reopen | Prevents flow-local custom handoff files or ad hoc selectors. | include |
| Example proofs | `_stdlib_smoke`, `poem_loop`, `software_engineering_demo` | Same route-first producer pattern and one real previous-turn JSON proof | Prevents one flow from teaching the old story while another teaches the new one. | include |
| Turn archaeology | `src/rally/adapters/base.py`, `docs/RALLY_CLI_AND_LOGGING.md` | Save the injected previous-turn appendix under the turn folder | Prevents hidden runtime behavior with no file proof. | include |
| Issue ledger | `src/rally/services/issue_ledger.py` | Keep ledger as history and summary only | Prevents `issue.md` from turning into a shadow previous-output database. | exclude |
| Note-backed prior outputs | `src/rally/cli.py`, `src/rally/services/issue_ledger.py`, `skills/rally-kernel/prompts/SKILL.prompt` | Keep notes as context only; do not infer prior-output identity from ledger blocks | Prevents a fake readback path that cannot prove which declaration wrote which note. | exclude |
| Note-only skill path | `skills/rally-kernel/prompts/SKILL.prompt` | Keep note skill focused on notes only | Prevents previous-turn readback from leaking into the note skill. | exclude |
| Unsupported prior-output targets | future note-backed or other non-file targets | fail-loud unsupported target handling | Prevents a partial reopen path from pretending it is generic. | include |
| External ports outside this repo | other repos and old migrated flows | update only after Rally ships the new owner path | Prevents this plan from widening into cross-repo migration work. | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; split Section 7 into the best sequence of coherent self-contained units, optimizing for phases that are fully understood, credibly testable, compliance-complete, and safe to build on later. If two decompositions are both valid, bias toward more phases than fewer. `Work` explains the unit and is explanatory only for modern docs. `Checklist (must all be done)` is the authoritative must-do list inside the phase. `Exit criteria (all required)` names the exhaustive concrete done conditions the audit must validate. Resolve adjacent-surface dispositions and compatibility posture before writing the checklist. Before a phase is valid, run an obligation sweep and move every required promise from architecture, call-site audit, migration notes, delete lists, verification commitments, docs/comments propagation, approved bridges, and required helper follow-through into `Checklist` or `Exit criteria`. The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). If a bridge is explicitly approved, timebox it and include removal work; otherwise plan either clean cutover or preservation work directly. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 — Producer Route-First Cutover Across Runtime And Shipped Sources

Status: COMPLETE

Completed work:
- Cut Rally runtime, shared producer prompt source, and shipped producer flows
  over to Doctrine route-first producer routing.
- Kept review routing on the current review-field lane while removing
  Rally-owned producer `next_owner` assumptions from touched runtime, prompt
  source, and producer build truth.

* Goal:
  - Make Rally-owned producer routing use Doctrine route truth end to end, with
    no producer `next_owner` story left in Rally runtime, Rally stdlib, or the
    shipped example flows.
* Work:
  - This phase cuts over the producer lane as one unit so Rally does not carry
    a long-lived second producer routing model while later phases build on it.
* Checklist (must all be done):
  - Add typed producer route metadata to `src/rally/domain/flow.py`.
  - Parse emitted producer `route` metadata from
    `final_output.contract.json` in `src/rally/services/flow_loader.py`.
  - Reject producer handoff contracts that still try to route without emitted
    `route.selector` truth.
  - Keep review contract loading and validation unchanged.
  - Update producer final-response parsing in
    `src/rally/services/final_response_loader.py` so handoffs derive from
    Doctrine `route.selector` and `route.branches`.
  - Fail loud on producer route contradictions, including:
    - `handoff` with no selected route
    - non-handoff with a selected route
    - unknown route members
    - `null` where `null_behavior` says `invalid`
  - Update `src/rally/domain/turn_result.py` and
    `src/rally/services/runner.py` so producer routing, run-state updates, and
    issue-log summaries no longer depend on payload `next_owner`.
  - Rewrite `stdlib/rally/prompts/rally/turn_results.prompt` around the
    route-first producer pattern with strong comments at the shared boundary.
  - Update `stdlib/rally/prompts/rally/review_results.prompt` comments so the
    review lane stays clearly separate from the producer lane.
  - Migrate Rally-owned producer prompt source in:
    - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
    - `flows/poem_loop/prompts/AGENTS.prompt`
    - `flows/software_engineering_demo/prompts/AGENTS.prompt`
  - Remove Rally-owned producer `next_owner` assumptions from touched runtime
    code, shared prompt source, shipped example prompt source, and affected
    unit tests.
  - Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
    after the prompt-source cutover.
* Verification (required proof):
  - `uv run pytest tests/unit/domain/test_flow_contracts.py tests/unit/domain/test_turn_result_contracts.py tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py -q`
  - Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`.
  - Inspect emitted `final_output.contract.json` for the shipped producer
    agents and confirm producer route selectors exist where handoffs exist.
* Docs/comments (propagation; only if needed):
  - Add or refresh short comments at the producer route-loading boundary, the
    producer final-response parse boundary, and the shared stdlib producer
    boundary.
* Exit criteria (all required):
  - Rally-owned producer routing in runtime comes only from Doctrine route
    metadata.
  - Route-less producer handoffs and producer route contradictions fail loud.
  - No Rally-owned shared producer prompt or shipped producer example still
    teaches payload `next_owner`.
  - Review routing still works through the current review-field lane.
  - Rebuilt shipped flows reflect the producer cutover in emitted route
    metadata.
  - Phase verification passes.
* Rollback:
  - Revert the producer route-first cutover as one unit across runtime, shared
    prompt source, shipped example source, and regenerated build output.

## Phase 2 — Previous-Turn IO Load Path And Runtime Appendix Support

Status: COMPLETE

Completed work:
- Added typed emitted `io` metadata models and loader support, the dedicated
  previous-turn resolver, and the saved `previous_turn_inputs.md` turn
  artifact.
- Added `RallyPreviousTurnOutput` to Rally stdlib and updated prompt assembly
  so Rally appends and saves one deterministic previous-turn appendix with
  fail-loud unsupported reopen handling.
- Fresh focused proof passed:
  `uv run pytest tests/unit/test_flow_loader.py
  tests/unit/test_final_response_loader.py
  tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py
  tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py -q`
  -> `135 passed`

* Goal:
  - Make Rally load Doctrine's additive `io` metadata and build one exact
    previous-turn appendix path for supported prior-output kinds.
* Work:
  - This phase adds the previous-turn runtime owner path without widening Rally
    into a second contract file, a note scraper, or a prose summarizer.
* Checklist (must all be done):
  - Add typed `io` metadata to `src/rally/domain/flow.py`.
  - Parse emitted `io.previous_turn_inputs`, `io.outputs`, and
    `io.output_bindings` in `src/rally/services/flow_loader.py`.
  - Add `input source RallyPreviousTurnOutput` to
    `stdlib/rally/prompts/rally/base_agent.prompt` with strong source comments,
    and keep it opt-in instead of adding it to `RallyManagedInputs`.
  - Add a dedicated previous-turn resolver and appendix renderer under a Rally
    service module instead of inlining the logic into `runner.py`.
  - Extend `src/rally/adapters/base.py` turn artifacts with
    `previous_turn_inputs.md`.
  - Update `src/rally/services/runner.py` to:
    - read current-agent previous-turn requests from emitted `io`
    - resolve `default_final_output`, `output_decl`, and `output_binding`
      selectors through emitted contract truth
    - reopen only the actual immediately previous turn
    - append the deterministic previous-turn appendix after compiled
      `AGENTS.md`
    - save the same appendix into the current turn folder
  - Support only these readback paths:
    - exact previous final JSON from `last_message.json`
    - file-backed structured JSON
    - file-backed readable text
  - Fail loud on:
    - missing `io`, output, or binding metadata
    - unreadable prior artifacts
    - contract-mode mismatches after reopen
    - note-backed previous-output reopen
    - every other unsupported target or readback mode
  - Add or update focused unit tests for:
    - `io` load-path parsing
    - `output_decl` selector resolution
    - `output_binding` selector resolution
    - previous-turn appendix rendering
    - file-backed structured JSON reopen
    - file-backed readable text reopen
    - saved `previous_turn_inputs.md` artifacts
    - fail-loud missing metadata, unreadable artifact, contract-mode mismatch,
      and unsupported note-backed reopen
* Verification (required proof):
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py tests/unit/test_issue_ledger.py tests/unit/test_cli.py -q`
  - Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`.
* Docs/comments (propagation; only if needed):
  - Add or refresh short comments at the new previous-turn resolver boundary,
    the turn-artifact boundary, and the shared base prompt source declaration.
* Exit criteria (all required):
  - Rally loads `io` from the same `final_output.contract.json` file.
  - Rally can render and save the previous-turn appendix for supported
    selector kinds and readback modes.
  - Supported previous-turn reopen is limited to the immediate previous turn,
    exact previous final JSON, and file-backed structured or readable outputs.
  - Rally does not scrape `home:issue.md` for previous-output readback.
  - Missing metadata, unreadable artifacts, contract-mode mismatches,
    note-backed reopen, and every other unsupported target or readback mode
    fail loud with explicit errors.
  - Phase verification passes.
* Rollback:
  - Revert the IO load-path work, appendix renderer, turn-artifact change, and
    shared source declaration as one unit.

## Phase 3 — `_stdlib_smoke` Previous-Turn JSON Proof

Status: COMPLETE

* Goal:
  - Make the smallest shipped Rally flow prove the immediate previous-final JSON
    path in a simple route-first producer flow.
* Work:
  - This phase adds one minimal, easy-to-debug previous-turn JSON example
    before the richer `poem_loop` proof.
* Checklist (must all be done):
  - Update `_stdlib_smoke` so one downstream producer turn reads the immediate
    previous producer final output through `RallyPreviousTurnOutput`.
  - Keep `_stdlib_smoke` on the route-first producer pattern from Phase 1.
  - Rebuild `_stdlib_smoke`.
  - Add or update focused tests that prove Rally injects the exact previous
    JSON into the downstream turn for this flow.
  - Inspect emitted `_stdlib_smoke` `final_output.contract.json` files and
    confirm the previous-turn input is present in `io.previous_turn_inputs`.
* Verification (required proof):
  - `uv run pytest tests/unit/test_runner.py tests/unit/test_flow_build.py -q`
  - Rebuild `_stdlib_smoke`.
* Docs/comments (propagation; only if needed):
  - Add or refresh short comments in the smoke flow only where they teach the
    minimal previous-turn JSON pattern clearly.
* Exit criteria (all required):
  - `_stdlib_smoke` proves the immediate previous-final JSON path end to end.
  - The smoke proof uses Rally's real previous-turn appendix path, not a local
    helper or sidecar.
  - Phase verification passes.
* Rollback:
  - Revert the smoke-only previous-turn proof changes and rebuild output.

## Phase 4 — `poem_loop` Muse Loop And Main Previous-Turn Proof

Status: COMPLETE

* Goal:
  - Make `poem_loop` the main real proof for previous-turn JSON across both the
    normal and reject loops.
* Work:
  - This phase upgrades the shipped poem example into the primary Rally proof
    for route-first producer control plus previous-turn JSON reuse.
* Checklist (must all be done):
  - Add `Muse` to `flows/poem_loop` and make the flow start with `Muse`.
  - Keep the producer lane route-first across `Muse` and `PoemWriter`.
  - Make `PoemWriter` read the immediate previous `Muse` output through
    `RallyPreviousTurnOutput`.
  - Make `Muse` read the immediate previous `PoemCritic` review JSON on reject
    loops through `RallyPreviousTurnOutput`.
  - Keep `PoemCritic` on the current review lane.
  - Update only these poem prompt owners in this plan so the loop stays plain,
    consistent, and well-commented:
    - `flows/poem_loop/prompts/AGENTS.prompt`
    - `flows/poem_loop/prompts/shared/contracts.prompt`
    - `flows/poem_loop/prompts/shared/inputs.prompt`
    - `flows/poem_loop/prompts/shared/outputs.prompt`
    - `flows/poem_loop/prompts/shared/review.prompt`
    - `flows/poem_loop/prompts/roles/poem_writer.prompt`
    - `flows/poem_loop/prompts/roles/poem_critic.prompt`
    - `flows/poem_loop/prompts/roles/muse.prompt`
  - Rebuild `poem_loop`.
  - Add or update focused tests for:
    - `Muse -> Writer -> Critic`
    - `Critic -> Muse -> Writer`
    - previous-turn appendix content for the poem loop turns that depend on it
* Verification (required proof):
  - `uv run pytest tests/unit/test_runner.py tests/unit/test_flow_loader.py tests/unit/test_flow_build.py -q`
  - Rebuild `poem_loop`.
* Docs/comments (propagation; only if needed):
  - Add or refresh short comments in `poem_loop` prompt source where the
    `Muse` loop would otherwise be hard to follow.
* Exit criteria (all required):
  - `poem_loop` proves the planned `Muse -> Writer -> Critic` path.
  - `poem_loop` proves the reject path that sends control from `Critic` back
    to `Muse`.
  - The proof uses exact previous-turn JSON and route-first producer control.
  - Phase verification passes.
* Rollback:
  - Revert the `Muse` loop and poem-only previous-turn changes as one unit.

## Phase 5 — Docs, Showcase Truth, And Final Proof Sweep

Status: COMPLETE

* Goal:
  - Leave Rally's live docs, shared comments, and shipped build truth aligned
    with the new producer and previous-turn patterns.
* Work:
  - This phase removes stale guidance and makes the repo teach one clear
    producer story, one clear review story, and one clear previous-turn story.
* Checklist (must all be done):
  - Update these live docs so they match the shipped behavior:
    - `docs/RALLY_MASTER_DESIGN.md`
    - `docs/RALLY_RUNTIME.md`
    - `docs/RALLY_COMMUNICATION_MODEL.md`
    - `docs/RALLY_PORTING_GUIDE.md`
    - `docs/RALLY_CLI_AND_LOGGING.md`
    - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md`
  - Make the docs say:
    - producer routing comes from Doctrine route metadata
    - review routing still comes from review fields
    - prompt build is compiled `AGENTS.md` plus the runtime previous-turn
      appendix when declared
    - `previous_turn_inputs.md` is a turn-local archaeology file
    - notes are context only and are not used for previous-output reopen
  - Remove stale producer `next_owner` guidance from live docs and touched
    comments.
  - Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` one
    last time and inspect the emitted contracts and build readback.
  - Run the full Rally unit suite.
* Verification (required proof):
  - `uv run pytest tests/unit -q`
  - Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`.
* Docs/comments (propagation; only if needed):
  - This whole phase is the required doc and comment propagation pass.
* Exit criteria (all required):
  - All six named live docs align with the shipped runtime and stdlib behavior
    in the same pass.
  - No touched live doc still teaches producer payload `next_owner` as Rally's
    producer routing owner.
  - The same doc pass teaches:
    - compiled `AGENTS.md` plus the runtime previous-turn appendix
    - `previous_turn_inputs.md` as archaeology only
    - notes as context only, not previous-output readback
  - The shipped builds and final emitted contracts match the docs.
  - The full Rally unit suite passes.
* Rollback:
  - Revert the doc sweep and final rebuild outputs together if the final proof
    surface does not hold.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Runtime proof

- focused unit tests for loader, final-response parsing, and runner prompt
  assembly
- assert fail-loud producer route checks for route-less handoffs and route
  contradictions
- assert the runtime previous-turn appendix content and saved
  `previous_turn_inputs.md` artifact when a flow declares previous-turn inputs
- assert `default_final_output`, `output_decl`, and `output_binding`
  resolution for the supported immediate-previous-turn paths
- assert file-backed structured JSON and readable text reopen, plus fail-loud
  errors for missing metadata, unreadable artifacts, contract-mode mismatch,
  note-backed reopen, and every other unsupported target kind
- Doctrine rebuild and emitted-contract inspection wherever Rally now depends
  on Doctrine-owned routing or previous-turn metadata

## 8.2 Flow proof

- rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
- inspect emitted `final_output.contract.json`, emitted schemas, and generated
  `AGENTS.md`
- confirm the Rally design still matches Doctrine's emitted intent after each
  migrated example change

## 8.3 Real-path proof

- one `_stdlib_smoke` path where the downstream producer reads the immediate
  previous final JSON
- one real `poem_loop` path where `Muse` sends structured guidance to `Writer`
- one real `poem_loop` reject path where `Critic` sends control to `Muse`
- one Rally example path that shows producer routing without payload
  `next_owner`

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout

This draft assumes one Rally-owned producer cutover in source, tests, docs,
and emitted build output.

## 9.2 Ops stance

Fail loud on missing route metadata, route contradictions, missing `io`
metadata, missing output or binding metadata, unreadable prior artifacts, and
contract-mode mismatches after reopen.

Fail loud on missing Doctrine support too. The right response is a Doctrine
feature request, not a hidden Rally fallback.

## 9.3 Telemetry

No new telemetry surface is expected. Existing Rally logs and rebuild proofs
should stay enough.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - `# TL;DR`, Sections `0` through `10`, `planning_passes`, and the helper
    blocks
  - previous-turn support boundary, producer route fail-loud rules, docs
    convergence scope, and phase-to-verification alignment
- Findings summary:
  - the top-level spine did not fully state the immediate-previous-turn-only
    boundary or the exact supported readback kinds
  - Section 7 stranded some fail-loud route and previous-turn obligations
    outside the authoritative checklist and exit surfaces
  - Phase 4 poem prompt ownership and the required docs convergence set were
    still too open-ended
- Integrated repairs:
  - promoted the exact previous-turn boundary into `TL;DR`, Section `0`,
    constraints, acceptance evidence, and rollback-safe phase text
  - added explicit Phase 1 and Phase 2 checklist and exit coverage for route
    contradictions, supported selector kinds and readback modes, and fail-loud
    metadata or artifact errors
  - named the approved `poem_loop` prompt owners, expanded the required docs
    set, and marked external research grounding done-not-needed for this
    repo-local plan
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

- 2026-04-16: Draft plan chooses Doctrine's emitted route and `io` contracts as
  the Rally runtime source of truth for this feature.
- 2026-04-16: Draft plan chooses a clean cutover for Rally-owned producer
  routing patterns instead of a long-lived producer bridge.
- 2026-04-16: Draft plan keeps review routing on the current review final JSON
  path until Doctrine exposes clean review-side route-field support.
- 2026-04-16: Draft plan chooses `poem_loop` plus a new `Muse` agent as the
  main previous-turn JSON proof path.
- 2026-04-16: Draft plan requires heavy comments in Rally stdlib prompt source
  so the new patterns stay teachable in the canonical owner layer.
- 2026-04-16: Draft plan requires Doctrine-first validation. If the elegant
  Rally design hits a Doctrine gap, Rally stops and surfaces the needed
  Doctrine feature instead of adding a Rally-local workaround.
- 2026-04-16: Deep-dive pass 1 chooses a route-first Rally-owned producer
  family: keep Rally status fields, remove payload `next_owner`, and bind
  producer handoffs through `final_output.route`.
- 2026-04-16: Deep-dive pass 1 chooses one runtime previous-turn path:
  runner appends a deterministic previous-turn appendix built from emitted `io`
  metadata and exact prior turn artifacts, then saves the same appendix under
  the current turn folder for proof.
- 2026-04-16: Deep-dive pass 1 keeps `home:issue.md` as history and summary
  only. Previous-turn readback will not scrape the ledger or overload the note
  path.
- 2026-04-16: Deep-dive pass 2 narrows previous-turn readable support to exact
  previous final JSON plus file-backed outputs. Note-backed outputs stay out
  because Rally's current note path is append-only and not declaration-keyed.
- 2026-04-16: Phase plan lands the full Rally-owned producer cutover before the
  main previous-turn proof work so no long-lived producer bridge survives
  between runtime and shipped prompt source.
- 2026-04-16: Phase plan uses `_stdlib_smoke` as the smallest previous-turn
  JSON proof before the richer `poem_loop` `Muse` loop proof.
- 2026-04-16: Consistency pass locks the previous-turn support boundary at the
  immediate previous turn only, with exact previous final JSON plus
  file-backed structured or readable outputs as the only supported reopenable
- 2026-04-16: Implementation completed Phase 1 and Phase 2 in Rally with
  passing unit proof and rebuilt emitted contracts for the shipped flow set.
- 2026-04-16: Phase 3 is blocked on a Doctrine compiler bug, not a Rally
  design gap. `emit_docs._build_previous_turn_contexts()` now asks
  `_compiler/flow.py` to extract target flow graphs for previous-turn facts,
  but `_collect_flow_from_workflow_body()` still assumes every non-section and
  non-skill workflow item has `target_unit` plus `workflow_decl`. Ordinary
  readable workflow steps do not, so previous-turn emit crashes before Rally
  can adopt the `_stdlib_smoke` proof flow. Rally should not patch around this.
  Doctrine needs to make previous-turn predecessor extraction skip or safely
  handle readable workflow items during flow-graph collection.
  paths in this plan.
- 2026-04-16: Consistency pass makes `docs/RALLY_CLI_AND_LOGGING.md` and
  `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` required same-pass
  convergence surfaces and marks outside external research as not needed for
  this Rally-plus-Doctrine repo-local plan.
