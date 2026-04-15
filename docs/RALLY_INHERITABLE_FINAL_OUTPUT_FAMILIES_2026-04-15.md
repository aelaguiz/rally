---
title: "Rally - Inheritable Final Output Families - Architecture Plan"
date: 2026-04-15
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/PRINCIPLES.md
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - stdlib/rally/prompts/rally/turn_results.prompt
  - flows/poem_loop/prompts/shared/review.prompt
  - flows/software_engineering_demo/prompts/shared/review.prompt
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/runner.py
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/REVIEW_SPEC.md
  - ../doctrine/examples/79_final_output_output_schema/prompts/AGENTS.prompt
  - ../doctrine/examples/105_review_split_final_output_output_schema_control_ready/prompts/AGENTS.prompt
---

# TL;DR

## Outcome

Rally will standardize on one final-output-first machine path with two shared,
inheritable JSON families:

1. a producer control family for `handoff`, `done`, `blocker`, and `sleep`
2. a review final-output family for structured review truth and routing

Shipped flows will extend those families instead of inventing one-off final
JSON shapes. Review turns will stop treating a markdown note as the main source
of machine truth.

## Problem

Rally's current review path is backwards. Reviews already end in structured
JSON, but Rally turns that JSON into a markdown note and treats the note like
the hot read path. That creates duplicate truth, weakens machine readability,
and makes inheritance harder than it should be.

## Approach

Keep producer control and review output as two separate base families. Make
both families inheritable through Doctrine's output-schema and output
inheritance. Then teach Rally runtime to treat the final output payload and the
compiler metadata as the only machine truth it needs for routing, ledger
writeback, and later readers.

## Plan

1. Refactor the shared producer turn-result contract into a base family plus a
   default leaf.
2. Add one shared review final-output family that uses split `final_output`
   plus `review_fields`.
3. Move shipped review flows onto that shared review family.
4. Change Rally runtime so final output stays the machine source of truth for
   both producer and review turns.
5. Rewrite ledger writeback, tests, comments, and docs so they all follow that
   same one-path story.

## Non-negotiables

- No markdown scraping for machine truth.
- No duplicate control truth in `home:issue.md`.
- Producer control field names stay stable.
- Review turns use a separate review JSON family, not a merged
  `kind`-plus-`verdict` schema.
- The shared final-output families must be inheritable by Rally users.
- Comments and docs at the canonical boundaries must be updated in the same
  pass.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-15
Verdict (code): COMPLETE
Manual QA: complete (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit against the full approved Phase 1-6 frontier found no
  missing code work.

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
external_research_grounding: not needed
deep_dive_pass_2: done 2026-04-15
recommended_flow: research -> deep dive -> deep dive again -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can move to a cleaner and more extensible final-output model if it does
all of these things in one story:

1. keep one shared producer control JSON family with stable control fields
2. add one shared review final-output JSON family for structured review truth
3. use Doctrine inheritance so flows extend those families instead of cloning
   schemas
4. make final output, not markdown notes, the source of machine truth for
   runtime control and ledger writeback
5. update docs, comments, tests, and bundled assets so they all describe the
   same path

This claim is false if any of these stay true after the work:

- review turns still need markdown notes to carry machine truth
- shipped flows still copy final-output contracts instead of inheriting them
- producer turns need renamed control fields or flow-local loader hacks
- review turns carry both `verdict` and producer `kind` in one merged control
  schema
- Rally still writes the same outcome into `home:issue.md` in more than one
  machine-truth shape
- live docs or boundary comments still teach the old note-first review story

## 0.2 In scope

- Refactor `rally.turn_results` into a base producer family plus a default leaf
  contract.
- Add one shared Rally review final-output family in stdlib.
- Use Doctrine split `final_output` plus `review_fields` for the shared review
  family.
- Migrate shipped review flows in `poem_loop` and
  `software_engineering_demo` to that shared review family.
- Keep shipped producer flows on the shared producer family.
- Change Rally runtime loader and writeback so final output is the machine
  source of truth for both producer and review turns.
- Keep review routing behavior stable while the machine-truth path changes.
- Update generated output, bundled assets, focused tests, and live docs tied to
  this contract family.
- Add or update short code comments at the canonical boundaries where this
  design would be easy to misunderstand later.

Compatibility posture:

- Producer control JSON keeps the current field names and meanings.
- Review final output does a clean cutover from note-first machine truth to
  final-output-first machine truth.
- No note-first bridge or shipped-flow dual path is allowed.
- The generic loader may still parse both carrier and split review finals as a
  Doctrine compatibility boundary, not as a Rally rollout bridge.

Allowed architectural convergence scope:

- widen across stdlib prompts, flow prompts, runtime loader code, ledger
  writeback, bundled assets, and tests when needed to keep one final-output
  story
- remove duplicate review-note writeback or duplicate ledger control records
  when they only exist to support the old machine-truth path

### Intended contract shapes

The intended producer shape is one shared control base plus a default shared
leaf. Flow authors may inherit the base and add fields, but they do not rename
the control core.

```prompt
output schema BaseRallyTurnResultSchema: "Base Rally Turn Result Schema"
    field kind: "Kind"
        type: string
        enum:
            handoff
            done
            blocker
            sleep
        required

    field next_owner: "Next Owner"
        type: string
        optional

    field summary: "Summary"
        type: string
        optional

    field reason: "Reason"
        type: string
        optional

    field sleep_duration_seconds: "Sleep Duration Seconds"
        type: integer
        optional


output shape BaseRallyTurnResultJson: "Base Rally Turn Result JSON"
    kind: JsonObject
    schema: BaseRallyTurnResultSchema


output BaseRallyTurnResult: "Base Rally Turn Result"
    target: TurnResponse
    shape: BaseRallyTurnResultJson
    requirement: Required


output RallyTurnResult[BaseRallyTurnResult]: "Rally Turn Result"
    inherit target
    inherit requirement
    override shape: RallyTurnResultJson
```

The intended review shape is a separate shared review family. It stays
review-shaped. It does not carry producer `kind`.

```prompt
output schema BaseRallyReviewSchema: "Base Rally Review Schema"
    field verdict: "Verdict"
        type: string
        enum:
            accept
            changes_requested
        required

    field reviewed_artifact: "Reviewed Artifact"
        type: string
        required

    field analysis_performed: "Analysis Performed"
        type: string
        required

    field findings_first: "Findings First"
        type: string
        required

    field current_artifact: "Current Artifact"
        type: string
        optional

    field next_owner: "Next Owner"
        type: string
        optional

    field failure_detail: "Failure Detail"
        type: object
        optional

        field blocked_gate: "Blocked Gate"
            type: string
            optional

        field failing_gates: "Failing Gates"
            type: array
            items: string
            optional


output shape BaseRallyReviewJson: "Base Rally Review JSON"
    kind: JsonObject
    schema: BaseRallyReviewSchema


output BaseRallyReviewResponse: "Base Rally Review Response"
    target: TurnResponse
    shape: BaseRallyReviewJson
    requirement: Required
```

Review agents should use split `final_output` so Rally can read structured
review truth from the final output path itself.

```prompt
agent SomeReviewer:
    review: SomeReview
    outputs: "Outputs"
        SomeReviewComment
        SomeReviewFinal
    final_output:
        output: SomeReviewFinal
        review_fields:
            verdict: verdict
            reviewed_artifact: reviewed_artifact
            analysis: analysis_performed
            readback: findings_first
            current_artifact: current_artifact
            next_owner: next_owner
            blocked_gate: failure_detail.blocked_gate
            failing_gates: failure_detail.failing_gates
```

That is the intended Rally shape:

- producer turns inherit one shared control family
- review turns inherit one shared review family
- both end through the final output path
- Rally runtime reads machine truth from final output payload plus compiler
  metadata
- markdown notes, if they still exist, are human projections only

## 0.3 Out of scope

- changing Rally memory or resolver behavior
- changing adapter launch rules
- changing the one-ledger model itself
- adding new run states, new turn kinds, or new review verdicts
- adding GUI, dashboard, or DB-backed control surfaces
- adding flow-local prompt reducers, runtime shims, or other side-door machine
  truth paths

## 0.4 Definition of done (acceptance evidence)

This work is done when all of these are true:

- Rally ships one shared producer final-output family and one shared review
  final-output family.
- Shipped review flows use the shared review family through inheritance and
  split `final_output`.
- Rally runtime reads machine truth from final-output payload plus
  `final_output.contract.json`, not from rendered markdown notes.
- Review turns can route, block, or finish from the structured final output
  alone.
- `home:issue.md` gets one main record per turn from that same machine-truth
  path.
- Focused loader, runner, bundled-asset, and readback tests pass.
- Focused workspace-sync and packaged-install proof pass.
- Live docs and code comments at the main boundaries explain the new path
  clearly and in plain English.

Proof should include:

- Doctrine emit proof for the shared producer family, the shared review family,
  a minimal shared review-family smoke proof, and at least one shipped review
  flow
- loader and final-response tests for inherited producer outputs and split
  review outputs
- runner tests that show review turns no longer depend on a markdown review
  note for machine control
- bundled-asset and workspace-sync proof for the new shared stdlib surface
- packaged-install proof for the changed shipped package surface
- one readback spot check for a producer flow and one for a review flow

## 0.5 Key invariants (fix immediately if violated)

- Final output is the only machine-truth path.
- Producer control fields stay stable and shared.
- Review JSON stays review-shaped and separate from producer control JSON.
- One turn creates one main machine-truth ledger record.
- No flow-local schema forks when a shared family should own the contract.
- No stale docs or comments that teach the old note-first review path.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. One machine-truth path for final outputs.
2. Shared inheritance for both producer and review contracts.
3. No duplicate truth in ledger writeback.
4. Stable producer control behavior during the refactor.
5. Clear comments and docs at the new boundaries.

## 1.2 Constraints

- Doctrine must stay the authoring source for structured final outputs.
- Producer control fields must keep current names and meaning.
- Review routing must keep current behavior.
- Rally must stay CLI-first and file-first.
- The design must stay extendable for Rally users, not only Rally demos.

## 1.3 Architectural principles (rules we will enforce)

- Keep one owner for each kind of machine truth.
- Prefer inheritance over copied schema families.
- Keep producer and review control languages separate.
- Let runtime read compiler-owned metadata, not markdown renderings.
- Write comments only at the sharp edges where drift is likely.

## 1.4 Known tradeoffs (explicit)

- Two base families are a little more typing than one merged schema, but they
  avoid mixed control languages and duplicated truth.
- Split review final output keeps Doctrine review semantics clean, but it means
  Rally must read both the payload and the compiler metadata carefully.
- A hard cutover is cleaner than a bridge, but it forces docs and tests to move
  in the same pass.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Producer turns end with `rally.turn_results.RallyTurnResult`.
- Review turns already end with structured JSON and compiler metadata.
- Rally maps review JSON into a runtime-written markdown review note.
- Flow prompts still teach readers to trust the newest review note.

## 2.2 What’s broken / missing (concrete)

- Reviews have structured machine truth, but Rally projects it into markdown
  and then leans on the markdown.
- Shared producer control JSON is not yet shaped as a reusable base family.
- There is no shared review final-output family for flow authors to inherit.
- Ledger writeback and docs still reflect the older note-first review story.

## 2.3 Constraints implied by the problem

- The fix must preserve current producer routing behavior.
- The fix must preserve current review routing behavior.
- The fix must remove duplicate truth instead of adding a new bridge layer.
- The fix must stay simple enough that flow authors can inherit it cleanly.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/LANGUAGE_REFERENCE.md` — adopt — Doctrine already has
  inherited `output schema`, inherited `output shape`, inherited `output`, and
  split review `final_output` with `review_fields`. Rally does not need a new
  side path for this.
- `../doctrine/docs/REVIEW_SPEC.md` — adopt — Doctrine already treats split
  review final output as a first-class pattern and emits `control_ready`
  metadata for it.
- `../doctrine/docs/EMIT_GUIDE.md` — adopt — Doctrine already emits
  `final_output.contract.json` beside `AGENTS.md` and the schema file. Rally
  should keep using that compiler-owned metadata instead of inventing a second
  machine contract.
- `../doctrine/examples/79_final_output_output_schema/prompts/AGENTS.prompt`
  — adopt — this is the right shared-base-plus-child pattern for Rally's
  producer family.
- `../doctrine/examples/105_review_split_final_output_output_schema_control_ready/prompts/AGENTS.prompt`
  — adopt — this is the right split review final-output pattern for Rally's
  review family.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/domain/flow.py` — Rally already has typed runtime objects for
    `final_output`, review `carrier_fields`, split `review_fields`, and
    `control_ready`.
  - `src/rally/services/flow_loader.py` — Rally already loads
    `final_output.contract.json`, builds those typed contracts, and rejects
    review finals that are not `control_ready`.
  - `src/rally/services/final_response_loader.py` — producer turns already use
    final JSON as machine truth, and review turns already support both
    carrier-mode and split-mode field mapping.
  - `src/rally/services/runner.py` — the current runtime still turns review
    JSON back into markdown and then writes extra ledger records from the same
    turn result.
- Canonical path / owner to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt` — shared home for the
    producer control family.
  - `stdlib/rally/prompts/rally/` — right home for the new shared review
    family so shipped flows stop cloning it.
  - `src/rally/services/final_response_loader.py` — right place for final
    output parsing and review control mapping.
  - `src/rally/services/runner.py` — right place for ledger writeback rules
    once final output becomes the one machine-truth path.
- Adjacent surfaces tied to the same contract family:
  - `flows/poem_loop/prompts/shared/review.prompt` — current flow-local review
    family that should move onto the shared review base.
  - `flows/software_engineering_demo/prompts/shared/review.prompt` — same
    duplicated review family problem on the engineering side.
  - `flows/poem_loop/build/agents/poem_critic/final_output.contract.json` —
    live proof that shipped review agents already emit compiler-owned review
    metadata.
  - `flows/software_engineering_demo/build/agents/architect_reviewer/final_output.contract.json`
    — same proof for the engineering review lane.
  - `tests/unit/test_flow_loader.py` — coverage for review metadata loading and
    `control_ready` enforcement.
  - `tests/unit/test_final_response_loader.py` — coverage for carrier-mode and
    split-mode review loading.
  - `tests/unit/test_runner.py` — coverage for the current ledger writeback
    shapes that will need a deliberate cutover.
  - `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`,
    `docs/RALLY_COMMUNICATION_MODEL.md` — live docs that must stay aligned with
    the new final-output-first story.
- Compatibility posture (separate from `fallback_policy`):
  - clean cutover — producer control fields stay the same, review machine
    truth moves from note-first to final-output-first, and no bridge keeps the
    old note-owned path alive.
- Existing patterns to reuse:
  - `../doctrine/examples/79_final_output_output_schema/prompts/AGENTS.prompt`
    — producer base-plus-child inheritance.
  - `../doctrine/examples/105_review_split_final_output_output_schema_control_ready/prompts/AGENTS.prompt`
    — split review `final_output` with explicit `review_fields`.
  - Rally already did the broader compiler-owned JSON port, so this refactor
    should extend that line instead of starting a new one.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt` — current producer field
    meanings for `handoff`, `done`, `blocker`, and `sleep`.
  - `flows/poem_loop/prompts/shared/review.prompt` — current review field set
    for `verdict`, `reviewed_artifact`, `analysis_performed`,
    `findings_first`, `current_artifact`, `next_owner`, and `failure_detail`.
  - `flows/software_engineering_demo/prompts/shared/review.prompt` — same
    review field set on the engineering side with different contract gates.
- Native model or agent capabilities to lean on:
  - Doctrine compiler output — structured JSON plus review metadata already
    gives Rally the machine truth it needs without markdown scraping or a new
    side parser.
- Existing grounding / tool / file exposure:
  - built agent packages already give Rally `AGENTS.md`, the emitted schema
    file, and `final_output.contract.json` in one place.
  - the adapter final message file already gives Rally direct JSON payload
    access for the last turn.
- Duplicate or drifting paths relevant to this change:
  - `flows/poem_loop/prompts/shared/review.prompt` and
    `flows/software_engineering_demo/prompts/shared/review.prompt` duplicate
    the same review output family shape instead of inheriting one shared base.
  - `src/rally/services/final_response_loader.py` still renders
    `review_note_markdown`, which keeps the note-first story alive.
  - `src/rally/services/runner.py` still writes a review note plus `Rally Turn
    Result` plus `Rally Done`, `Rally Blocked`, or `Rally Sleeping`, which
    duplicates turn truth in `home:issue.md`.
  - shipped review agents still emit `carrier` mode in build output today even
    though Rally runtime already knows how to load split review finals.
- Capability-first opportunities before new tooling:
  - use Doctrine output inheritance for the producer base family instead of
    cloning flow-local producer JSON shapes.
  - use Doctrine split review `final_output` with `review_fields` instead of
    turning review JSON into markdown and then re-reading the markdown.
  - keep ledger writeback as a projection from final JSON, not a second source
    of machine truth.
- Behavior-preservation signals already available:
  - `tests/unit/test_flow_loader.py` — protects `control_ready` review loading.
  - `tests/unit/test_final_response_loader.py` — protects carrier and split
    review parsing.
  - `tests/unit/test_runner.py` — shows the current ledger writeback behavior
    that this cutover must change on purpose.
  - shipped `final_output.contract.json` files under `flows/*/build/agents/*`
    — live emit proof for the current compiler contract.

## 3.3 Decision gaps that must be resolved before implementation

- None blocking the architecture line.
- Locked by repo truth plus user approval:
  - keep two base families, not one merged schema
  - do a hard cutover with no bridge
  - move review machine truth onto the final-output path
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Shared producer control JSON lives in
  `stdlib/rally/prompts/rally/turn_results.prompt`.
- Shipped review JSON still lives in flow-local prompt files:
  - `flows/poem_loop/prompts/shared/review.prompt`
  - `flows/software_engineering_demo/prompts/shared/review.prompt`
- Shipped producer agents use short-form
  `final_output: rally.turn_results.RallyTurnResult`.
- Shipped review agents still point `comment_output` and `final_output` at the
  same review response output, so emitted review metadata stays in carrier
  mode today.
- Each built agent package already carries the compiler-owned machine surfaces:
  - `AGENTS.md`
  - emitted schema under `schemas/`
  - `final_output.contract.json`

## 4.2 Current runtime flow

1. Doctrine emits the built agent package.
2. `src/rally/services/flow_loader.py` loads `final_output.contract.json` and
   builds typed producer or review contracts.
3. `src/rally/services/final_response_loader.py` reads the last JSON payload.
4. Producer turns go straight from payload to `parse_turn_result(...)`.
5. Review turns map review fields to a `TurnResult`, then also render
   `review_note_markdown`.
6. `src/rally/services/runner.py` writes runtime state, appends a review note
   when one exists, then appends `Rally Turn Result` plus extra
   `Rally Done`, `Rally Blocked`, or `Rally Sleeping` records from the same
   turn.

## 4.3 Ownership and key boundaries today

- Doctrine already owns final-output authoring, inheritance, schema emission,
  and review metadata emission.
- Rally stdlib owns the shared producer final-output contract, but it does not
  yet own a shared review final-output family.
- Flow-local review prompts still own the shared review output shape, so the
  same review family core is copied in more than one flow.
- `src/rally/domain/flow.py` already has the right typed contract boundaries:
  `FinalOutputContract`, `ReviewContract`, `ReviewFinalResponseContract`, and
  `control_ready`.
- `LoadedFinalResponse` still mixes two jobs:
  - machine truth for routing
  - rendered markdown for review note writeback

## 4.4 Failure behavior and proof today

- Flow load fails loud when a built agent package is missing
  `final_output.contract.json`.
- Flow load fails loud when a review final output is not `control_ready`.
- Final-response loading fails loud when the last message is not valid JSON.
- Review loading fails loud when a rejected review has no `next_owner` and no
  `blocked_gate`.
- Chained execution still blocks on sleep turn results.
- Focused tests already protect the key current paths:
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_runner.py`

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 Canonical owners

- `stdlib/rally/prompts/rally/turn_results.prompt` becomes the shared producer
  family home. It will own:
  - `BaseRallyTurnResultSchema`
  - `BaseRallyTurnResultJson`
  - `BaseRallyTurnResult`
  - `RallyTurnResult[BaseRallyTurnResult]`
- Add one new shared stdlib file at
  `stdlib/rally/prompts/rally/review_results.prompt`. It will own:
  - `BaseRallyReviewSchema`
  - `BaseRallyReviewJson`
  - `BaseRallyReviewResponse`
- Shipped flows should import that new shared family as Rally stdlib, not hide
  it behind one flow's local `shared.review` file.
- Flow-local review prompt files keep only flow-local review contracts, gates,
  examples, and two child outputs per flow:
  - one review carrier child output
  - one reusable split-final child output
- Agent prompt files only wire review agents to those flow-local child outputs.
  They do not invent per-agent split-final outputs.

## 5.2 Final-output-first control path

- Producer turns keep the same control meaning and field names. Rally still
  reads `kind`, `next_owner`, `summary`, `reason`, and
  `sleep_duration_seconds` from final JSON.
- Review turns cut to split `final_output`. Each review agent keeps a review
  carrier for Doctrine review semantics, but its machine-truth `final_output`
  becomes a separate structured JSON output that inherits the shared review
  family and binds `review_fields`.
- Shipped review agents should follow one exact pattern:
  - the `review` still names a `comment_output`
  - the agent `outputs:` list includes both the review carrier and the split
    final JSON output
  - the agent `final_output:` block points at the split final JSON output and
    binds `review_fields`
- Shipped review agents must emit:
  - `review.final_response.mode = split`
  - `review.final_response.control_ready = true`
- Rally runtime routes from the final-output payload plus compiler metadata
  only. It does not need rendered review markdown to decide what happens next.

## 5.3 Runtime object model

- Keep the current typed compiler metadata path in `flow.py` and
  `flow_loader.py`.
- Replace `LoadedFinalResponse.review_note_markdown` with a typed optional
  review view such as `review_truth`, carrying the resolved review fields Rally
  needs for writeback and status.
- Keep generic parser support for both carrier and split review finals at the
  loader boundary, because Doctrine supports both and Rally should not narrow
  Doctrine's generic compatibility surface here.
- Standardize Rally stdlib and shipped flows on split review final output so
  the framework path is one clear final-output-first story.

## 5.4 Ledger and writeback rules

- One successful turn writes one main runtime-owned ledger record.
- That record is derived from the final-output payload.
- Keep `Rally Turn Result` as the one runtime-owned successful-turn title for
  both producer and review turns.
- Keep `Rally Note` for agent-authored notes and explicit operator notes only.
- Runtime no longer appends a separate review note from
  `_append_review_note(...)`.
- Runtime no longer appends extra `Rally Done`, `Rally Blocked`, or
  `Rally Sleeping` records when the successful final-output record already
  carries that turn truth.
- The `Rally Turn Result` record may still include a short human summary plus
  the structured JSON body, but both must be projections from the same final
  payload.
- Early failures that happen before a valid final output still may append
  `Rally Blocked`, because there is no final-output record to carry that truth.

## 5.5 Invariants and boundaries

- Producer control fields stay fixed and inherited. Flows may add fields but
  do not rename the control core.
- Review final outputs stay review-shaped. They do not also carry producer
  `kind`.
- Compiler metadata plus final JSON are Rally's only machine control sources.
- Any human review render is a projection from the same payload. It is not a
  second source of truth.
- Shipped review flows use the shared review family instead of cloning it.

## 5.6 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Shared producer stdlib | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultSchema`, `RallyTurnResultJson`, `RallyTurnResult` | One shared producer leaf owns the whole control shape | Split into shared base family plus default leaf | Let flows inherit producer control cleanly | `BaseRallyTurnResult*` plus `RallyTurnResult[BaseRallyTurnResult]` | `tests/unit/test_flow_loader.py`, flow readback tests, packaged install tests |
| Shared review stdlib | `stdlib/rally/prompts/rally/review_results.prompt` | new file | No shared review final-output family exists today | Add one shared review JSON family in stdlib | Give Rally one canonical review final-output path | `BaseRallyReview*` family | emit proof, flow readback tests |
| Shared stdlib smoke | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | smoke flow outputs | Smoke flow proves the current shared producer leaf only | Extend smoke coverage to prove the new producer inheritance shape | Keep the shared producer family honest in the smallest shipped flow | inherited producer base family in real emit output | flow readback tests |
| Shared review smoke | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | smoke flow review probe | No shipped permanent proof names a minimal shared review-family emit surface before full flow migration | Add one small review-family probe to `_stdlib_smoke` | Make the shared review-family proof surface concrete before shipped-flow adoption | minimal split-review-family smoke proof | flow readback tests |
| Poem review prompt | `flows/poem_loop/prompts/shared/review.prompt` | `PoemReviewResponse`, `PoemReviewFinalResponse` | Local file owns the full review output shape | Convert the carrier to a child of the shared review family and add one reusable split-final child output | Remove flow drift and keep one flow-owned split-final output | `PoemReviewFinalResponse[BaseRallyReviewResponse]` | `tests/unit/test_flow_loader.py`, emit readback checks |
| Poem review agent | `flows/poem_loop/prompts/AGENTS.prompt` | `review PoemReview`, `agent PoemCritic` | `comment_output` and `final_output` are the same carrier output | Keep the review carrier and wire the agent to `shared.review.PoemReviewFinalResponse` through `outputs:` and `final_output.review_fields` | Put review truth in turn output, not in the comment path | split review final output, control-ready | `tests/unit/test_flow_loader.py`, `tests/unit/test_final_response_loader.py` |
| Engineering review prompt | `flows/software_engineering_demo/prompts/shared/review.prompt` | `EngineeringReviewResponse`, `EngineeringReviewFinalResponse` | Local file owns the full review output shape | Convert the carrier to a child of the shared review family and add one reusable split-final child output for the flow | Remove flow drift and avoid three parallel engineering split outputs | `EngineeringReviewFinalResponse[BaseRallyReviewResponse]` | `tests/unit/test_flow_loader.py`, emit readback checks |
| Engineering review agents | `flows/software_engineering_demo/prompts/AGENTS.prompt` | `ArchitectReviewer`, `DeveloperReviewer`, `QaReviewer` | Each reviewer ends on the same carrier output it uses for review semantics | Keep the review carrier and wire all three reviewers to `shared.review.EngineeringReviewFinalResponse` through `outputs:` and `final_output.review_fields` | Standardize all shipped review lanes on one review final-output pattern without reintroducing drift | split review final output, control-ready | `tests/unit/test_flow_loader.py`, `tests/unit/test_final_response_loader.py` |
| Compiler metadata load | `src/rally/services/flow_loader.py` | `_load_compiled_agent_contract`, review final-response load | Already loads `review_fields` and `control_ready` | Keep as canonical loader path; update only if the new shared outputs require metadata-name expectation changes | Reuse the canonical path instead of inventing a new loader | same `final_output.contract.json` contract | `tests/unit/test_flow_loader.py` |
| Final response load | `src/rally/services/final_response_loader.py` | `LoadedFinalResponse`, `load_agent_final_response`, `_render_review_note_markdown` | Loads machine truth, then also renders markdown review notes | Add typed review truth and remove review-note rendering from the runtime control path | End note-first review handling | `LoadedFinalResponse.review_truth` replaces `review_note_markdown` | `tests/unit/test_final_response_loader.py` |
| Runner writeback | `src/rally/services/runner.py` | `_append_review_note`, `_append_issue_records_for_turn_result`, `_render_turn_result_payload_markdown` | Writes review note plus turn result plus extra status records | Collapse to one final-output-derived ledger record per successful turn; keep separate blocker only before valid final output exists | Remove duplicate truth in `home:issue.md` | one final-output-first writeback path | `tests/unit/test_runner.py` |
| Flow build proof | `src/rally/services/flow_build.py` | `_validate_emitted_agent_packages` | Validates built packages contain `AGENTS.md`, schema, and `final_output.contract.json` | Keep package validation as the canonical gate and extend proof to the new shared stdlib surfaces and split review outputs | Prevent stale built packages from hiding contract drift | same package shape, stronger split-review emit proof | `tests/unit/test_flow_build.py`, emit proof |
| Issue ledger format | `src/rally/services/issue_ledger.py` | `_RALLY_BLOCK_TITLES`, `append_issue_event(...)` | Supports many runtime block titles, including review notes under `Rally Note` | Keep operator note support, but stop using runtime review notes as a machine path | Preserve notes while deleting duplicate review control records | no new ledger file; one main runtime record per successful turn | `tests/unit/test_runner.py` |
| Generated build output | `flows/*/build/agents/*` | built schemas and `final_output.contract.json` | Shipped review agents emit carrier mode today | Re-emit after prompt changes and inspect split review metadata | Built packages must match source | `mode: split`, `control_ready: true` for shipped review agents | flow emit proof |
| Bundled stdlib | `src/rally/_bundled/stdlib/rally/prompts/rally/*` | bundled prompt copies | Bundled assets only know the current shared producer file | Sync bundled stdlib after the new review file and producer-base refactor land | Packaged Rally must ship the same stdlib story as source | bundled `turn_results.prompt` and new bundled `review_results.prompt` | `tests/unit/test_bundled_assets.py`, `tests/unit/test_workspace_sync.py` |
| Live docs | `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_PORTING_GUIDE.md`, `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` | current design and teaching text | Current docs still leave room for the old note-first review story | Rewrite to final-output-first review truth and shared family inheritance | Keep repo teaching aligned with code | one final-output-first machine path in docs | doc review |
| Release and package proof | `tests/integration/test_packaged_install.py` and build/readback proof paths | packaged stdlib and built agent package checks | Current proof does not cover the new shared review family | Extend proof to include the new stdlib file and one split review package | Prevent silent drift in shipped assets | packaged review-family stdlib plus split review metadata | integration and readback proof |

## 6.2 Migration notes

* Canonical owner path / shared code path:
  `stdlib/rally/prompts/rally/turn_results.prompt`,
  `stdlib/rally/prompts/rally/review_results.prompt`,
  `src/rally/services/final_response_loader.py`, and
  `src/rally/services/runner.py`.
* Deprecated APIs (if any):
  `LoadedFinalResponse.review_note_markdown`,
  `_append_review_note(...)`, and carrier-mode final output in shipped review
  flows.
* Delete list (what must be removed; include superseded shims/parallel paths if any):
  runtime-written review notes as a control path, flow-local clones of the
  shared review output core, shipped review agents that end on carrier-mode
  final output, and tests that assert duplicate successful-turn ledger
  records.
* Adjacent surfaces tied to the same contract family:
  built agent packages, bundled stdlib, flow readback, loader tests,
  final-response loader tests, runner tests, packaged install proof, and live
  docs.
* Compatibility posture / cutover plan:
  clean cutover. Producer control fields stay the same. Shipped review flows
  move to split final output in one pass. No note-first bridge and no
  shipped-flow dual path stay alive. The generic loader may still parse carrier
  and split review finals as a Doctrine compatibility boundary.
* Capability-replacing harnesses to delete or justify:
  rendered review markdown as runtime control truth, and any doc or prompt
  language that tells Rally to recover machine truth from review notes.
* Live docs/comments/instructions to update or delete:
  runtime docs, CLI/logging docs, communication docs, master design, porting
  guide, flow showcase docs, and boundary comments in final-response load and
  runner writeback code.
* Behavior-preservation signals for refactors:
  flow-loader review metadata tests, final-response loader review parsing
  tests, runner ledger writeback tests, emit readback for shipped flows, and
  packaged install proof.

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared producer contract | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | inherited producer base family | Proves the new producer family in the smallest shipped flow | include |
| Poem review lane | `flows/poem_loop/prompts/shared/review.prompt`; `flows/poem_loop/prompts/AGENTS.prompt` | shared review family plus split final output | Prevents one shipped flow from keeping the old carrier path | include |
| Engineering review lanes | `flows/software_engineering_demo/prompts/shared/review.prompt`; `flows/software_engineering_demo/prompts/AGENTS.prompt` | shared review family plus split final output | Prevents three reviewer lanes from teaching a second review path | include |
| Runtime read path | `src/rally/services/final_response_loader.py` | typed review truth instead of rendered review note markdown | Keeps runtime on one machine-truth path | include |
| Runtime writeback | `src/rally/services/runner.py` | one successful-turn ledger record from final output | Prevents duplicate runtime truth in `home:issue.md` | include |
| Bundled asset sync | `src/rally/_bundled/stdlib/rally/prompts/rally/*` | bundle the new review stdlib file with the producer refactor | Prevents packaged Rally from shipping stale prompt surfaces | include |
| Live docs | `docs/RALLY_MASTER_DESIGN.md`; `docs/RALLY_RUNTIME.md`; `docs/RALLY_CLI_AND_LOGGING.md`; `docs/RALLY_COMMUNICATION_MODEL.md`; `docs/RALLY_PORTING_GUIDE.md`; `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md` | final-output-first review story | Prevents repo docs from teaching dead note-first behavior | include |
| Old arch records | `docs/RALLY_STDLIB_PROMPT_SURFACE_REFRESH_2026-04-15.md` | optional wording cleanup only if touched by the same contract family later | This is a planning record, not the live runtime teaching surface | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: build the foundation first and keep each phase small enough to finish,
> prove, and build on later. `Work` explains the unit. `Checklist (must all be
> done)` is the real must-do list. `Exit criteria (all required)` names what
> has to be true before the phase is done. No bridge path. No unresolved
> branches. Update live docs and sharp-edge comments in the phase that changes
> what is real.

## Phase 1 — Refactor the shared producer family

Status: COMPLETE

Completed work:
- Added `BaseRallyTurnResultSchema`, `BaseRallyTurnResultJson`, and `BaseRallyTurnResult` to `stdlib/rally/prompts/rally/turn_results.prompt`.
- Kept `RallyTurnResult` as the default shared leaf and moved it onto the new base family with the same five control fields.
- Added one `_stdlib_smoke` inherited producer proof through `CloseoutTurnResult`.
- Added a focused flow-loader readback test for the inherited producer smoke output.

* Goal:
  Move Rally's producer control output from one shared leaf to one shared base
  family plus the current default leaf, without changing producer control
  meaning.
* Work:
  Refactor `stdlib/rally/prompts/rally/turn_results.prompt` so it owns the
  shared producer base family and still exports the current `RallyTurnResult`
  leaf. Extend `_stdlib_smoke` so the repo has one small shipped proof that
  real producer inheritance works.
* Checklist (must all be done):
  - add `BaseRallyTurnResultSchema`
  - add `BaseRallyTurnResultJson`
  - add `BaseRallyTurnResult`
  - make `RallyTurnResult` inherit the base family
  - keep the current producer control fields and field meanings unchanged
  - update `_stdlib_smoke` so at least one emitted agent uses the inherited
    producer family in real flow source
  - keep prompt readback plain and short
* Verification (required proof):
  - emit `_stdlib_smoke`
  - inspect one built producer schema and one `final_output.contract.json`
  - run focused flow readback proof for the smoke flow
* Docs/comments (propagation; only if needed):
  - add one short boundary comment in the shared producer prompt if the base
    and leaf split would be easy to misread later
* Exit criteria (all required):
  - producer inheritance works in emitted build output
  - producer control fields did not drift
  - Rally now has one shared producer base family plus the default leaf
* Rollback:
  Revert the producer prompt refactor and the smoke-flow adoption together.

## Phase 2 — Add the shared review family in stdlib

Status: COMPLETE

Completed work:
- Added `stdlib/rally/prompts/rally/review_results.prompt` with `BaseRallyReviewSchema`, `BaseRallyReviewJson`, and `BaseRallyReviewResponse`.
- Kept review truth separate from producer control.
- Added one `_stdlib_smoke` review probe with split `final_output` and `review_fields`.
- Added a focused flow-loader smoke test for split review metadata and control-ready output.

* Goal:
  Create one shared review final-output family in Rally stdlib that shipped
  flows can inherit instead of cloning the same review core.
* Work:
  Add `stdlib/rally/prompts/rally/review_results.prompt` with the shared review
  schema, JSON shape, and response output. Keep it review-shaped, separate from
  producer `kind`, and add one minimal shared review-family probe in
  `_stdlib_smoke` so this phase has a named proof surface.
* Checklist (must all be done):
  - add `BaseRallyReviewSchema`
  - add `BaseRallyReviewJson`
  - add `BaseRallyReviewResponse`
  - keep the shared review field set aligned with Rally runtime needs:
    `verdict`, `reviewed_artifact`, `analysis_performed`, `findings_first`,
    `current_artifact`, `next_owner`, and `failure_detail`
  - keep producer and review families separate in stdlib
  - extend `_stdlib_smoke` with one minimal review-family probe
  - make the new file readable enough that later flow authors can extend it
    without cloning it
* Verification (required proof):
  - emit `_stdlib_smoke`
  - inspect emitted review schema shape and metadata expectations
* Docs/comments (propagation; only if needed):
  - add one short comment or note in the shared review prompt that says why
    review truth stays separate from producer control
* Exit criteria (all required):
  - Rally stdlib has one canonical shared review family
  - no merged review-plus-producer schema was introduced
* Rollback:
  Remove the new stdlib review file if later phases are not ready to adopt it.

## Phase 3 — Move shipped review flows to the shared split-final path

Status: COMPLETE

Completed work:
- Moved `poem_loop` review output shape onto the shared review family and added `PoemReviewFinalResponse`.
- Moved `software_engineering_demo` review output shape onto the shared review family and added `EngineeringReviewFinalResponse`.
- Switched `PoemCritic`, `ArchitectReviewer`, `DeveloperReviewer`, and `QaReviewer` to split review final output with explicit `review_fields`.
- Updated focused flow-loader proof so the shipped review flows now assert split, control-ready metadata.
- Fixed `software_engineering_demo` shared contract wording so the flow reads review truth from the newest `Rally Turn Result` block instead of a removed runtime review note.

* Goal:
  Make shipped flows prove the shared review-family and split-final-output
  pattern in real source and real build output.
* Work:
  Refactor `poem_loop` and `software_engineering_demo` so flow-local review
  files keep only local review contracts, gates, and child extensions. Each
  flow-local shared review file owns one reusable split-final child output
  beside the review carrier, and each shipped review agent points
  `final_output:` at that flow-owned split output with explicit
  `review_fields`.
* Checklist (must all be done):
  - `flows/poem_loop/prompts/shared/review.prompt` inherits the shared review
    family instead of owning the full review core
  - `flows/poem_loop/prompts/shared/review.prompt` adds
    `PoemReviewFinalResponse`
  - `flows/software_engineering_demo/prompts/shared/review.prompt` inherits the
    shared review family instead of owning the full review core
  - `flows/software_engineering_demo/prompts/shared/review.prompt` adds one
    shared `EngineeringReviewFinalResponse`
  - `PoemCritic` keeps a review carrier and wires to
    `shared.review.PoemReviewFinalResponse`
  - `ArchitectReviewer`, `DeveloperReviewer`, and `QaReviewer` keep their
    review carriers and wire to `shared.review.EngineeringReviewFinalResponse`
  - each shipped review agent emits `mode = split`
  - each shipped review agent emits `control_ready = true`
  - no shipped review agent still ends on carrier-mode final output
* Verification (required proof):
  - emit `poem_loop`
  - emit `software_engineering_demo`
  - inspect one built review `AGENTS.md` readback per flow
  - inspect each review agent `final_output.contract.json`
  - run focused flow-loader proof for split review metadata
* Docs/comments (propagation; only if needed):
  - update flow-local prompt wording only where it still teaches the old
    carrier-equals-final path
* Exit criteria (all required):
  - shipped review flows inherit the shared family
  - shipped review flows emit split, control-ready final output metadata
* Rollback:
  Revert the flow prompt migrations together if either shipped flow cannot emit
  the new shape cleanly.

## Phase 4 — Refactor final-response loading to typed review truth

Status: COMPLETE

Completed work:
- Replaced `LoadedFinalResponse.review_note_markdown` with typed review truth in `src/rally/services/final_response_loader.py`.
- Added `LoadedReviewTruth` and kept carrier-plus-split review support only at the generic loader boundary.
- Removed `_render_review_note_markdown(...)` from the runtime control path.
- Re-anchored `tests/unit/test_final_response_loader.py` on typed review truth instead of rendered markdown.

* Goal:
  Make Rally's load path treat final output as the only machine-truth path for
  reviews before writeback changes land.
* Work:
  Replace rendered review markdown in `LoadedFinalResponse` with typed review
  truth derived from the final-output payload plus compiler metadata. Keep the
  current producer path stable. Keep support for both carrier and split review
  finals at the generic loader boundary as a Doctrine compatibility boundary,
  even though Rally stdlib and shipped flows standardize on split mode.
* Checklist (must all be done):
  - replace `LoadedFinalResponse.review_note_markdown` with typed review truth
  - remove `_render_review_note_markdown(...)` from the runtime control path
  - keep producer parsing on the fixed shared control fields
  - keep review parsing fail-loud on missing required route or blocked truth
  - keep generic support for both carrier and split review finals at the loader
    boundary only
  - do not reintroduce a shipped-flow dual path or note-first bridge
  - update loader tests to assert typed review truth instead of rendered review
    markdown
* Verification (required proof):
  - run focused `tests/unit/test_final_response_loader.py`
  - run focused `tests/unit/test_flow_loader.py` review metadata tests
* Docs/comments (propagation; only if needed):
  - update sharp-edge code comments at the final-response load boundary
* Exit criteria (all required):
  - runtime no longer depends on rendered review markdown for machine control
  - loader tests prove split review truth directly
* Rollback:
  Revert the loader refactor if typed review truth cannot preserve current
  routing behavior.

## Phase 5 — Cut runner writeback to one successful-turn record

Status: COMPLETE

Completed work:
- Refactored `src/rally/services/runner.py` so each successful producer or review turn writes one `Rally Turn Result` block.
- Removed `_append_review_note(...)` from the successful review path.
- Stopped appending extra successful-turn `Rally Done`, `Rally Blocked`, and `Rally Sleeping` records when the turn result already carries that truth.
- Updated focused runner assertions to prove the one-record rule on producer, review, and sleep-result paths.

* Goal:
  Make `home:issue.md` carry one runtime-owned successful-turn record per turn,
  derived from final output.
* Work:
  Refactor `src/rally/services/runner.py` so successful producer and review
  turns write one `Rally Turn Result` record with a short human summary plus
  the structured JSON body. Remove `_append_review_note(...)` from successful
  review turns. Stop appending extra `Rally Done`, `Rally Blocked`, or
  `Rally Sleeping` records when the successful final-output record already
  carries that truth. Keep early blocker records only when no valid final
  output exists.
* Checklist (must all be done):
  - successful producer turns write one `Rally Turn Result`
  - successful review turns write one `Rally Turn Result`
  - `_append_review_note(...)` is removed from the successful review path
  - extra successful-turn `Rally Done`, `Rally Blocked`, and `Rally Sleeping`
    records are removed where the turn result already carries that truth
  - early failures before valid final output still can append `Rally Blocked`
  - runner tests are updated to assert the new one-record rule
  - issue-ledger title handling still supports explicit notes and lifecycle
    events that remain in scope
* Verification (required proof):
  - run focused `tests/unit/test_runner.py`
  - spot-check one producer and one review issue-ledger fixture or rendered
    output in test assertions
* Docs/comments (propagation; only if needed):
  - update boundary comments at the writeback helpers so future edits do not
    reintroduce duplicate truth
* Exit criteria (all required):
  - successful turns no longer duplicate runtime truth in the ledger
  - review writeback is fully final-output-first
* Rollback:
  Revert the runner writeback refactor if one-record writeback breaks current
  route or blocker behavior.

## Phase 6 — Sync bundled assets, live docs, and final proof

Status: COMPLETE

Completed work:
- Synced bundled `turn_results.prompt` and new `review_results.prompt`.
- Extended build, bundled-asset, workspace-sync, and packaged-install tests to cover the shared review family ship surface.
- Updated the live design, runtime, CLI/logging, communication, showcase, and porting docs to the final-output-first story.
- Rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` after the cutover.
- Updated `poem_loop` source and emitted readback so turn history now points at `Rally Turn Result`.
- Switched the packaged-install proof to the local Doctrine checkout used by the dev runner, then proved the shipped package surface on that compiler path.
- Did one manual review-ledger spot check against the review-turn ledger text asserted in `tests/unit/test_runner.py`.
- Re-emitted `software_engineering_demo` after the shared contract wording fix so shipped readback now matches the final-output-first story.

* Goal:
  Make the repo ship and teach one final-output-first story, then prove the
  cutover on the real shipped surfaces.
* Work:
  Sync bundled stdlib assets and emitted readback, update live design,
  runtime, CLI/logging, communication, showcase, and porting docs, extend
  packaged-install and build proof where needed, and run the focused final
  proof surface.
* Checklist (must all be done):
  - sync bundled `turn_results.prompt` and new `review_results.prompt`
  - sync any changed built readback used as shipped proof
  - update `docs/RALLY_MASTER_DESIGN.md`
  - update `docs/RALLY_RUNTIME.md`
  - update `docs/RALLY_CLI_AND_LOGGING.md`
  - update `docs/RALLY_COMMUNICATION_MODEL.md`
  - update `docs/RALLY_PORTING_GUIDE.md`
  - update `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md`
  - extend packaged-install and build proof to cover the new shared review
    family and split review package shape
  - run the focused proof surface end to end
  - do one manual review-ledger spot check at the end
* Verification (required proof):
  - local Doctrine emit proof for shared contracts and shipped flows
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_runner.py`
  - `tests/unit/test_flow_build.py` where package validation changed
  - `tests/unit/test_bundled_assets.py`
  - `tests/unit/test_workspace_sync.py`
  - `tests/integration/test_packaged_install.py`
* Docs/comments (propagation; only if needed):
  - keep only live docs and high-leverage boundary comments aligned; do not
    widen into a general docs cleanup pass
* Exit criteria (all required):
  - source, build output, bundled assets, tests, and live docs all tell the
    same final-output-first story
  - the focused proof surface is green
  - one manual ledger check confirms the review path reads cleanly
* Rollback:
  Revert doc and bundled sync together with the final proof updates if the code
  cutover is not ready to ship.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Programmatic proof

- shared producer family emit proof
- shared review family emit proof
- `_stdlib_smoke` emit/readback proof
- shipped flow emit proof
- flow-loader review metadata tests
- final-response loader tests
- runner writeback tests
- flow-build package-shape proof when touched
- bundled-asset tests
- workspace-sync tests
- packaged-install proof for the changed shipped package surface

## 8.2 Manual proof

- inspect one producer `final_output.contract.json`
- inspect one review `final_output.contract.json`
- inspect one review run ledger and confirm one `Rally Turn Result` tells the
  final-output-first story clearly

## 8.3 Failure signals

- review routing depends on markdown notes
- shipped flows no longer inherit shared final-output families
- shipped review agents still emit carrier-mode final output
- successful turns still write duplicate runtime truth in `home:issue.md`
- producer control fields drift
- docs still disagree about where machine truth lives

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout

- hard cutover in one repo pass
- no note-first bridge
- no shipped-flow dual path
- generic loader support for both Doctrine review modes stays only at the
  compatibility boundary

## 9.2 Ops

- use focused runtime and readback tests as the main cutover guard
- keep manual checks small and only at the review ledger boundary

## 9.3 Telemetry

- existing event logs are enough for this refactor
- no new telemetry surface is needed

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter and helper-block drift
  - TL;DR, Sections 0 through 10
  - target architecture, call-site audit, phase plan, verification, rollout,
    and live-doc follow-through
- Findings summary:
  - the doc had one unresolved compatibility wording gap around carrier versus
    split review support
  - the helper block still implied an external-research stage that this plan
    did not need
  - the split review-output owner model was not exact enough
  - the live-doc and proof surfaces missed one focused doc and one concrete
    review-family smoke proof
- Integrated repairs:
  - tightened the compatibility rule to ban note-first bridges and
    shipped-flow dual paths while keeping generic loader support for both
    Doctrine review modes at the compatibility boundary
  - marked `external_research_grounding: not needed` and aligned the helper
    block sequence with the actual planning path
  - chose one exact owner model for split review outputs:
    flow-local shared review files own the child outputs and agent files only
    wire to them
  - added `_stdlib_smoke` as the named minimal review-family proof surface
  - added `docs/RALLY_CLI_AND_LOGGING.md` to the live-doc update surface
  - aligned Section 0, Section 7, and Section 8 on workspace-sync and
    packaged-install proof
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

- 2026-04-15: Chose two shared final-output families, not one merged schema.
  Reason: keep producer control and review truth separate while still giving
  Rally one final-output-first machine path.
- 2026-04-15: Chose `stdlib/rally/prompts/rally/review_results.prompt` as the
  shared review-family home. Reason: keep producer and review shared families
  side by side in stdlib and stop cloning the review core in flow-local files.
- 2026-04-15: Chose split review `final_output` for shipped review agents.
  Reason: review truth must live in the turn output path, while the review
  carrier stops being Rally's machine-truth path.
- 2026-04-15: Chose `Rally Turn Result` as the one successful-turn runtime
  ledger record for both producer and review turns. Reason: keep one hot
  runtime record per successful turn and reserve `Rally Note` for explicit
  notes instead of review control truth.
- 2026-04-15: Chose hard cutover with no runtime bridge. Reason: duplicate
  truth is the problem, so no note-first bridge or shipped-flow dual path is
  allowed. Generic loader support for both Doctrine review modes stays only at
  the compatibility boundary.
- 2026-04-15: Chose docs and boundary comments as required same-pass work.
  Reason: this change is easy to misunderstand later if the repo leaves stale
  teaching behind.
