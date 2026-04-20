---
title: "Rally - Doctrine v5.0 Exemplar Adoption - Architecture Plan"
date: 2026-04-19
status: active
fallback_policy: forbidden
owners: [Amir Elaguizy]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md
  - ../doctrine/CHANGELOG.md
  - ../doctrine/docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md
  - ../doctrine/docs/AGENTS_MD_RENDER_OF_TYPED_CONTRACTS_2026-04-19.md
  - ../doctrine/skills/agent-linter/
  - ../doctrine/skills/doctrine-learn/
---

# TL;DR

**Outcome.** Rally compiles cleanly against Doctrine v5.0+, passes
`agent-linter` with zero findings on shipped flows, stdlib, and skills, and
`rally-learn` teaches current v5 canonical forms. All eight
Ship-Now/Plan-For findings from the 2026-04-19 audit land in one PR. Five
forward findings (F-9 through F-13) stay as comment markers at their
canonical sites, waiting on Doctrine P2–P7.

**Problem.** Rally was authored against Doctrine v4.0–v4.1. Doctrine v5.0
shipped today (2026-04-19) and makes three patterns breaking or non-canonical
that Rally still carries: `type: string` + `enum:` field bodies (E320 in
v5.0), coarse `accept ... when contract.passes` review checks (AL450), and
review contracts authored as `workflow` blocks instead of `schema ... gates:`
(AL245). Two stdlib carriers (`turn_results`, `review_results`) hit E320.
Every flow inherits them, so Rally will stop compiling on the next Doctrine
floor bump. Three secondary patterns (duplicated `review_fields:`, duplicated
turn-result scaffolds, missing `host_contract:` on skills) are DRY and
teaching wins that become the exemplar story.

**Approach.** One PR, eight coherent phases, foundational-first. Phase 1
lifts stdlib enums to top-level `enum` declarations so every downstream flow
inherits the canonical form. Phase 2 expands `contract.passes` to per-gate
`accept` lines across all five reviews. Phase 3 migrates poem_loop's
workflow-shaped contract to `schema ... gates:`. Phase 4 extracts the shared
eight-field `review_fields` decl. Phase 5 extracts the shared work-role
turn-result schema. Phase 6 adds `host_contract:` to the three Rally skills.
Phase 7 refreshes rally-learn teaching for v5. Phase 8 drops forward
comments at the P2–P7 landing sites and bumps the Doctrine floor.

**Plan.** 8 phases; each phase is independently testable by re-emitting the
affected flow/skill and running `uv run pytest tests/unit -q`. Ship once
and close the audit doc.

**Non-negotiables.**
- No fallbacks, no runtime shims, no v4/v5 bridges. Hard cutover on enum
  form.
- Zero behavior drift in review verdicts. Per-gate accepts must yield the
  same accept/reject outcomes as the old `contract.passes` on equivalent
  inputs. Verified by emitted-readback diff plus re-run of fixture flows.
- stdlib is the single owner of base fields. No flow redeclares base field
  types; all inherit.
- Rally owns one plan doc per change. This doc is the single source of
  truth for the adoption; no sidecar plans, no second checklist.
- Do not edit `../doctrine`. If a Doctrine gap surfaces, name it and stop.

# Planning Passes

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: not started
recommended_flow: research -> deep dive -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally's shipped `.prompt` source (flows, stdlib carriers, skill packages,
rally-learn references) compiles cleanly against Doctrine v5.0+, passes the
Doctrine `agent-linter` with zero findings in the set
`{AL100, AL110, AL200, AL220, AL245, AL270, AL280, AL330, AL450, AL930,
AL950}` on in-scope files, produces byte-stable `build/` readback for all
unchanged review verdicts on the shipped fixture flows, and teaches current
v5 canonical forms through `rally-learn` refs that the Doctrine
`doctrine-learn` skill would endorse as consistent.

This claim is falsifiable by:

1. Running the Doctrine compiler against the repo at the bumped floor
   version — compile must succeed.
2. Running `agent-linter` against each flow, each stdlib carrier, each
   skill — zero findings in the listed set.
3. Diffing pre/post emitted `AGENTS.md` and `schemas/*.schema.json` —
   differences must match expected v5 renderings (new `Valid values:`
   lines, per-gate accept readback, no inline enum field bodies).
4. Running `uv run pytest tests/unit -q` — must pass.

## 0.2 In scope

Requested behavior scope:

- `stdlib/rally/prompts/rally/turn_results/AGENTS.prompt`
- `stdlib/rally/prompts/rally/review_results/AGENTS.prompt`
- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt` (only if shared
  enum declarations land there)
- `flows/poem_loop/prompts/**` (AGENTS.prompt, shared/review.prompt, all
  roles)
- `flows/software_engineering_demo/prompts/**` (AGENTS.prompt,
  shared/review.prompt, all roles)
- `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- `skills/rally-kernel/prompts/SKILL.prompt`
- `skills/rally-memory/prompts/SKILL.prompt`
- `skills/demo-git/prompts/SKILL.prompt`
- `skills/rally-learn/prompts/SKILL.prompt`
- `skills/rally-learn/prompts/refs/*.prompt` (additive v5 teaching rows)

Architectural convergence scope:

- Extract shared `review_fields` declaration (F-4) into either
  `stdlib/rally/prompts/rally/review_results/AGENTS.prompt` or a new shared
  decl under the same directory, so both flows inherit one source.
- Extract shared work-role turn-result schema (F-5) into
  `flows/software_engineering_demo/prompts/shared/` to collapse the three
  near-duplicate schemas.
- Touch Rally Doctrine floor pin in `pyproject.toml` once v5.0 is
  available as a release artifact.
- Update `uv.lock` after the floor bump.

Docs that must stay in sync (touch only if stale after the change):

- `docs/TURN_RESULT_CONTRACT.md` — if it shows the old enum form, update.
- `docs/RALLY_COMMUNICATION_MODEL.md` — if it shows the old enum form,
  update.
- `docs/RALLY_RUNTIME.md` — if it references review verdict shape, verify.
- The audit doc `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`
  stays as the closing record, with findings marked landed.

Compatibility posture: **clean cutover**. Doctrine v5.0 deletes the old
enum-in-field form. There is no bridge. Rally's Doctrine pin bumps in the
same PR. `fallback_policy: forbidden`.

Capability-first stance: N/A. This is authoring work against a shipped
compiler, not agent-backed runtime behavior.

## 0.3 Out of scope

- Edits to `../doctrine`. If a Doctrine gap surfaces (e.g., review_family
  cannot express shared final_output.review_fields binding), name it
  plainly and either stop for discussion or pick the best available
  within-Rally expression and record the gap in Section 10.
- Adoption of P2–P7 forward features (`override gates:` in review_case,
  `typed_as:`, `receipt` family, skill `mode` binding, typed abstract
  parameters, declarative `rule`s). These are tracked as forward-comment
  markers only (Phase 8).
- Runtime, CLI, or tests changes beyond the minimum needed to ride the
  Doctrine bump.
- New flows, new skills, new agents, or new runtime features.
- Refactors of the `src/rally/**` Python runtime beyond what the floor
  bump forces.
- Rewriting unrelated docs under `docs/**`.

## 0.4 Definition of done (acceptance evidence)

All of the following must hold before the PR ships:

1. **Compile**: each flow re-emits without errors against Doctrine v5.0+.
   Evidence: `uv run python -m doctrine.emit_docs ...` or the Rally
   `ensure_flow_assets_built` helper succeeds for every flow.
2. **Lint**: `agent-linter` audit on each flow/stdlib/skill returns zero
   findings in the tracked set. Evidence: lint report appended to
   `WORKLOG_PATH`.
3. **Tests**: `uv run pytest tests/unit -q` passes. Evidence: test output
   in worklog.
4. **Readback diff**: `build/` output changes are bounded to expected v5
   shape deltas. Evidence: `git diff flows/*/build/` shows only
   - removed inline enum field bodies
   - new `Valid values:` lines
   - per-gate accept copy in review readback
   - shared decl replacements replace identical prose
5. **Behavior preservation on reviews**: a quick fixture run of the
   `_stdlib_smoke` flow reproduces prior accept/reject verdicts on
   identical inputs. Evidence: diff of `runs/<run>/turns/*.json` before
   and after.
6. **Floor bump**: Rally's `pyproject.toml` Doctrine pin is at the v5.0
   release. Evidence: `uv.lock` refreshed in same PR.
7. **Audit closure**: the audit doc gets a closing row per finding F-1
   through F-8 naming the commit that landed the fix.

Manual QA (non-blocking, finalization): none beyond the above.

## 0.5 Key invariants (fix immediately if violated)

- **No fallbacks or runtime shims.** Doctrine v5.0 enum form only.
- **No parallel paths.** One enum home per vocabulary; one review_fields
  decl; one work-role turn-result schema.
- **No silent behavior drift in reviews.** Per-gate accepts must match
  the old coarse verdict on equivalent inputs.
- **stdlib owns base field types.** Flow-local schemas inherit, never
  redeclare.
- **One plan doc.** This doc. No sidecars.
- **Do not edit `../doctrine`.** Name gaps; do not patch around them in
  Rally.
- **Fail loud.** If a compile or lint signal degrades, stop the phase.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. **v5.0 compile compatibility** — stdlib and all flows must compile.
2. **Zero behavior drift in review verdicts** — per-gate accepts preserve
   acceptance semantics.
3. **DRY wins where v5 supports it** — shared review_fields decl, shared
   work-role schema, host_contract on skills.
4. **Teaching parity** — `rally-learn` teaches current v5 canonical
   forms so framework users inherit best practice.
5. **Forward markers** — P2–P7 landing sites get short TODO comments so
   the next author sees the target shape.

## 1.2 Constraints

- Doctrine compiler hard rules (E320, E315, E316, E317, E318, E319 etc.)
  bind the authored surface. If a clean v5 expression does not exist for
  a Rally pattern, prefer the most canonical near-form and log the gap
  in Section 10.
- Emitted `AGENTS.md` is consumed by live Rally runs via the runtime
  prompt loader. Copy changes in emitted readback are acceptable when
  they replace inline prose with typed-output readback; otherwise, keep
  emitted prose stable where practical.
- `tests/unit/**` currently asserts on typed structure (loaded
  `flow.yaml`, emitted `final_output.contract.json` fields, emitted
  schema files). Name-stability of top-level enum declarations matters
  — if a test references `RallyTurnKind` or `ReviewVerdict` by name
  after the lift, pick names that read naturally.

## 1.3 Architectural principles (rules we will enforce)

- Enum-typed field form is the only form in shipped `.prompt` source.
- Review contracts live in `schema ... gates:`; never in `workflow` when
  they feed `review.contract:`.
- Review `contract_checks:` has one `accept` per gate.
- Shared field bindings (`review_fields:`) live in exactly one place
  that reviewer agents reference; they do not copy eight-line blocks.
- Turn-result route-field scaffolds that only differ by route target
  share a parent schema.
- Skill packages that consume host state declare `host_contract:`.
- `rally-learn` points at canonical Doctrine teaching for shared
  Doctrine topics; it does not re-teach framework rules.

## 1.4 Known tradeoffs (explicit, research-resolved)

- **`review_fields:` must stay inline per agent.** Doctrine v5 has no
  `final_output.review_fields: <SharedDecl>` binding-by-name form; the
  canonical Doctrine teaching (`../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`)
  shows the block inline on each agent's `final_output`. The real DRY
  lever is bare-name shorthand (`next_owner` instead of `next_owner:
  next_owner`) and leaning on `review_family.fields:` as the single
  place that types the shared vocabulary. Phase 4 collapses the eight
  repeated lines into short bare-name blocks; the `review_family.fields:`
  decl stays authoritative for the types.
- **Shared work-role turn-result schema** extracts the common base
  schema (`inherit {kind, summary, reason, sleep_duration_seconds,
  agent_issues}`) into a parent under `flows/software_engineering_demo/
  prompts/shared/`. Each role-specific schema inherits that parent and
  adds its own `route field next_route:`. If a Doctrine v5 constraint
  makes that split ungraceful, collapse to moving only the shared
  base-field inherit list into one comment/import — smaller win, still
  real.
- **`host_contract:` binding on skills is pure authoring.** The Rally
  runtime already injects `RALLY_CLI_BIN`, `RALLY_AGENT_SLUG`,
  `RALLY_RUN_ID`, and workspace paths via
  `src/rally/adapters/base.py` and
  `src/rally/services/home_materializer.py`. Phase 6 declares those
  slots on each skill package; the runtime contract does not change.
- **Per-gate accepts use per-gate rejects + final accept.** The
  canonical pattern in `../doctrine/skills/doctrine-learn/prompts/refs/
  reviews.prompt` is N per-gate `reject contract.<gate> when <basis>`
  lines plus a single catch-all `accept "..." when contract.passes` at
  the end. Phase 2 writes per-gate rejects where the gate's basis
  references a concrete artifact signal; the catch-all accept stays to
  preserve semantics if all gates pass.
- **Doctrine floor pin.** `pyproject.toml` resolves Doctrine through an
  editable `path = "../doctrine"` install. The floor bump is a pin
  update (`doctrine-agents>=4.0.0,<5` → `>=5.0.0,<6`) paired with a
  `uv.lock` refresh. No external tag dependency; this PR rides whatever
  `../doctrine` publishes as v5.0 when Doctrine cuts the release.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- stdlib carriers use `type: string` + `enum:` field bodies:
  - `stdlib/rally/prompts/rally/turn_results/AGENTS.prompt:10-16`
    (`kind` enum of 4 values)
  - `stdlib/rally/prompts/rally/review_results/AGENTS.prompt:9-13`
    (`verdict` enum of 2 values)
- All five reviews use coarse `accept ... when contract.passes`:
  - 3 in `flows/software_engineering_demo/prompts/shared/review.prompt`
  - 1 in `flows/poem_loop/prompts/shared/review.prompt`
  - 1 in `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- `flows/poem_loop/prompts/shared/review.prompt:27-35` uses
  `workflow PoemReviewContract` instead of `schema ... gates:`.
- Four identical eight-field `review_fields:` blocks repeat across
  reviewer agents; a fifth and sixth live in the `review_family` and
  `review` declarations themselves.
- Three near-identical work-role turn-result schemas in
  `flows/software_engineering_demo/prompts/AGENTS.prompt`.
- Three Rally skill packages consume host env vars and paths through
  prose, not through `host_contract:`.
- `rally-learn` references do not teach v5 canonical forms: no mention
  of `AL450`, `AL950`, enum-typed fields, or per-gate accepts.

## 2.2 What's broken / missing (concrete)

- Doctrine v5.0 ships `E320` on `type: string` + `enum:` in field
  bodies. Rally's next Doctrine floor bump fails compile. Blast radius:
  every flow (all inherit the stdlib carriers).
- `agent-linter` finding `AL450` flags `contract.passes` as coarse.
  Review debugging can't tell which gate failed from the emitted
  readback.
- `AL245` adjacent: workflow-shaped review contracts cannot emit typed
  `contract.<gate>` references, so poem_loop reviews can't line up
  prose with gate name.
- `AL200`/`AL220`/`AL280`: duplication that will grow with the next
  flow authored.
- `AL930`: skills hide host coupling in prose; compiler cannot validate.
- `AL110`-adjacent: rally-learn teaches stale conventions to framework
  users.

## 2.3 Constraints implied by the problem

- Rally must bump its Doctrine floor to v5.0 in the same change. No
  floor split.
- Review verdicts produced by the runtime must not drift when
  `contract.passes` becomes per-gate accepts.
- Extracting shared decls must not change the emitted schema
  contracts that `src/rally/**` parses.

# 3) Research Grounding (external + internal "ground truth")

<!-- arch_skill:block:research_grounding:start -->
Research resolved from repo evidence on 2026-04-19. Anchors below are
the authoritative references for each planning decision.
<!-- arch_skill:block:research_grounding:end -->

## 3.1 External anchors (Doctrine-side references)

- **`../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`** —
  canonical review-carrier teaching. Shows:
  - `final_output.review_fields:` is always an inline block on each
    reviewer agent; there is no `review_fields: <SharedDecl>` form.
  - Bare-name binds are the canonical shorthand (`next_owner` alone,
    no `: next_owner` trailing).
  - `review_family ... fields:` is the single place that types the
    shared review vocabulary; reviewer agents still restate which
    fields they bind inline, but the types come from the family.
  - AL450 canonical fix is N per-gate `reject contract.<gate> when
    <basis>` lines followed by a final catch-all `accept "..." when
    contract.passes`.
  - P2 override-gates pattern documented at lines 227–253 (forward
    feature — tracked as F-9 marker).
- **`../doctrine/examples/135_review_carrier_structured/prompts/AGENTS.prompt`** —
  shipped example. Confirms short bare-name `review_fields:` block
  (three fields in the example). Still uses `accept when contract.passes`
  alone, which predates full AL450 hardening — our plan adopts the
  hardened form.
- **`../doctrine/CHANGELOG.md`** (v5.0 section) — lists E320, E317–E319,
  E531/E532 as the new compiler errors that bind Rally's enum and
  review authoring. Matches the audit's Finding F-1 / F-2 / F-3 blast
  radius.
- **`../doctrine/pyproject.toml`** — Doctrine package version is
  currently `4.0.1`; v5.0 is WIP on the trunk. Rally resolves Doctrine
  through an editable `path = "../doctrine"` install so there is no
  external tag dependency.

## 3.2 Internal ground truth (Rally code as spec)

- **`stdlib/rally/prompts/rally/turn_results/AGENTS.prompt:10-16`** —
  current `kind` field uses `type: string` + `enum:` body. Canonical
  owner for Phase 1 `enum RallyTurnKind`. Every Rally flow inherits
  this carrier; lift is transitive.
- **`stdlib/rally/prompts/rally/review_results/AGENTS.prompt:9-13`** —
  current `verdict` field uses the same deprecated form. Canonical
  owner for Phase 1 `enum ReviewVerdict`.
- **`flows/software_engineering_demo/prompts/shared/review.prompt`** —
  three `schema ... gates:` review contracts (Architect, Developer, Qa)
  already use the modern schema form; only the coarse `accept when
  contract.passes` stays. `review_family EngineeringReviewFamily`
  declares the shared `fields:` block at lines 107–115 — this is the
  shared-vocabulary anchor that Phase 4 leans on.
- **`flows/poem_loop/prompts/shared/review.prompt:27-35`** — uses
  `workflow PoemReviewContract` instead of `schema ... gates:`.
  Phase 3 converts it to schema form; Phase 2's per-gate pattern then
  applies.
- **`flows/software_engineering_demo/prompts/AGENTS.prompt:140-273`** —
  three near-identical work-role turn-result schemas (Architect,
  Developer, QaDocs) differing only by `route field next_route:`
  target. Canonical shape for Phase 5 parent schema.
  `abstract agent SoftwareEngineeringRole[base.RallyManagedBaseAgent]`
  at line 140 is the matching abstract-agent anchor.
- **`src/rally/adapters/base.py`** — sets `RALLY_CLI_BIN`,
  `RALLY_AGENT_SLUG`, `RALLY_RUN_ID`, workspace paths on every
  spawned adapter process. Confirms Phase 6 `host_contract:` binding
  has no runtime scope expansion.
- **`src/rally/services/home_materializer.py`** — materializes
  `$RALLY_CLI_BIN` and run-home paths during prepared-home setup.
  Redundant confirmation of the above.
- **`src/rally/services/workspace.py`** — reads `RALLY_CLI_BIN`; fails
  loud if missing. This is the fail-loud boundary the skill
  `host_contract:` will pair with.
- **`pyproject.toml`** — Rally pins `doctrine-agents>=4.0.0,<5` with an
  editable install at `path = "../doctrine"`. Floor bump in Phase 8 is
  `>=5.0.0,<6` + `uv.lock` refresh.

## 3.3 Decision gaps — all resolved

- ✅ **`final_output.review_fields:` shared binding by name?** — **No
  such feature in Doctrine v5.0.** The block stays inline per reviewer
  agent. Phase 4's DRY win is using bare-name shorthand and letting
  `review_family.fields:` own the shared types. Evidence:
  `../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`.
- ✅ **Rally runtime inject of host-contract values?** — **Yes,
  already in place.** `src/rally/adapters/base.py` and
  `src/rally/services/home_materializer.py` set every slot a skill
  `host_contract:` needs. Phase 6 is pure authoring; no runtime
  change.
- ✅ **Doctrine v5.0 release tag?** — **Editable install; no external
  tag dependency.** `pyproject.toml` uses
  `path = "../doctrine"`. Phase 8 bumps the version pin
  (`<5` → `<6`) and refreshes `uv.lock` against whatever
  `../doctrine` ships as v5.0. If Doctrine hasn't cut v5.0 by the time
  Rally's PR is ready, the pin update lands in the same commit that
  Doctrine's v5.0 merges — this is the one and only external
  coordination point and it is tracked, not a blocker.

The plan is decision-complete. Implementation may proceed.

# 4) Current Architecture (as-is)

<!-- arch_skill:block:current_architecture:start -->
_Primary writer: `deep-dive` stage._
<!-- arch_skill:block:current_architecture:end -->

## 4.1 On-disk structure

_To be filled by `deep-dive`. Rally layout: flows/, stdlib/, skills/,
docs/, src/rally/. See AGENTS.md for the canonical folder contract._

## 4.2 Control paths (runtime)

_To be filled by `deep-dive`. Focus: how emitted `AGENTS.md`,
`final_output.contract.json`, `schemas/*.schema.json` feed
`src/rally/services/flow_build.py` and the runtime prompt loader._

## 4.3 Object model + key abstractions

_To be filled by `deep-dive`._

## 4.4 Observability + failure behavior today

_To be filled by `deep-dive`._

## 4.5 UI surfaces (ASCII mockups, if UI work)

N/A — no UI work in scope.

# 5) Target Architecture (to-be)

<!-- arch_skill:block:target_architecture:start -->
_Primary writer: `deep-dive` stage._
<!-- arch_skill:block:target_architecture:end -->

## 5.1 On-disk structure (future)

_To be filled by `deep-dive`. Expected: one new shared decl file (or
added declarations in existing carriers) for the shared review_fields
and shared work-role turn-result schema; no new directories._

## 5.2 Control paths (future)

_To be filled by `deep-dive`. No runtime control-path changes
expected._

## 5.3 Object model + abstractions (future)

_To be filled by `deep-dive`. New top-level enums: `RallyTurnKind`,
`ReviewVerdict`, possibly `EngineeringRouteTarget` if Phase 5 lifts
the route targets; new shared `review_fields` decl; new shared
work-role turn-result schema._

## 5.4 Invariants and boundaries

_To be filled by `deep-dive` from Section 0.5._

## 5.5 UI surfaces (ASCII mockups, if UI work)

N/A.

# 6) Call-Site Audit (exhaustive change inventory)

<!-- arch_skill:block:call_site_audit:start -->
_Primary writer: `deep-dive` stage. Will enumerate every touched file
with Area / File / Symbol / Current / Required / Why / New API / Tests
impacted._
<!-- arch_skill:block:call_site_audit:end -->

## 6.1 Change map (table)

_To be filled by `deep-dive`._

## 6.2 Migration notes

_To be filled by `deep-dive`. Expected:_

- _Canonical owner path for enum declarations: the stdlib carrier file
  that already owns the field._
- _Delete list: inline `enum:` blocks inside `field kind:` and `field
  verdict:`; inline prose bullets in skill packages that `host_contract:`
  replaces._
- _Adjacent surfaces: docs/TURN_RESULT_CONTRACT.md,
  docs/RALLY_COMMUNICATION_MODEL.md, skills/rally-learn/prompts/refs/*._
- _Compatibility posture: clean cutover on all breaking surfaces._
- _Behavior preservation: readback diff + fixture-flow verdict diff._

# 7) Depth-First Phased Implementation Plan (authoritative)

<!-- arch_skill:block:phase_plan:start -->
_Primary writer: `phase-plan` stage. Current contents are a seed
expressing the intended phase shape; `phase-plan` must finalize
Checklist and Exit criteria._
<!-- arch_skill:block:phase_plan:end -->

> Rule: systematic build, foundational first; split Section 7 into the best sequence of coherent self-contained units, optimizing for phases that are fully understood, credibly testable, compliance-complete, and safe to build on later. If two decompositions are both valid, bias toward more phases than fewer. `Work` explains the unit and is explanatory only for modern docs. `Checklist (must all be done)` is the authoritative must-do list inside the phase. `Exit criteria (all required)` names the exhaustive concrete done conditions the audit must validate. Resolve adjacent-surface dispositions and compatibility posture before writing the checklist.

## Phase 1 — Stdlib enum lift (F-1)

**Goal.** Lift the two stdlib carrier field enums to top-level Doctrine
v5 `enum` declarations so every downstream flow and shape compiles.

**Work.** Declare `RallyTurnKind` (`handoff`, `done`, `blocker`, `sleep`)
and `ReviewVerdict` (`accept`, `changes_requested`) as top-level
`enum Name: "Title"` blocks with `member: "member"` entries in the
owning stdlib carriers. Rewrite the two field bodies to
`type: RallyTurnKind` / `type: ReviewVerdict`. Leave all inherited
schemas, shapes, outputs, and `when verdict == ReviewVerdict.changes_requested`
predicates unchanged (they already reference the typed names).

**Checklist (must all be done).**
- Declare `export enum RallyTurnKind: "Rally Turn Kind"` at the top of
  `stdlib/rally/prompts/rally/turn_results/AGENTS.prompt` with the four
  canonical members.
- Replace the `field kind:` body to `type: RallyTurnKind` + `note:`.
  Remove the inline `enum:` block.
- Declare `export enum ReviewVerdict: "Review Verdict"` at the top of
  `stdlib/rally/prompts/rally/review_results/AGENTS.prompt` with the
  two canonical members.
- Replace the `field verdict:` body to `type: ReviewVerdict` + `note:`.
  Remove the inline `enum:` block.
- Re-emit `poem_loop`, `software_engineering_demo`, `_stdlib_smoke`
  via `ensure_flow_assets_built`.

**Verification (required proof).** `uv run python -c "from
rally.services.flow_build import ensure_flow_assets_built; ...` for each
of the three flows must succeed. `uv run pytest tests/unit -q` must
pass.

**Docs/comments (propagation; only if needed).** Update the one-line
"base field" comments in both carriers to match the new enum-first
shape; delete any stale `enum:` explanation in field notes.

**Exit criteria (all required).**
- Both carriers compile under editable `../doctrine` v5 without E101 /
  E320 errors.
- Every flow's `build/` re-emits with only expected deltas (new
  `Valid values:` lines in readback; no other semantic change).
- `tests/unit` is green.

**Rollback.** `git checkout stdlib/rally/prompts/rally/turn_results/`
and `git checkout stdlib/rally/prompts/rally/review_results/`. The rest
of Rally will break against v5 until Phase 1 lands, so rollback is
itself a blocker, not a safe fallback.

## Phase 2 — Per-gate rejects + catch-all accept (F-2)

**Goal.** Replace every coarse `accept ... when contract.passes` with a
per-gate reject block plus a single catch-all accept, so review readback
names the failing gate instead of hiding behind `contract.passes`.

**Work.** For each of the five reviews (PoemReview, ArchitectReview,
DeveloperReview, QaReview, SmokeReview), emit one
`reject contract.<gate> when <basis>` line per declared gate. Where the
gate contract has no obvious concrete basis beyond the model's narrative,
the reject body is a short human-readable phrase stating the gate label.
Keep a final catch-all `accept "..." when contract.passes` at the tail
so "all gates pass → accept" semantic is preserved exactly.

**Checklist (must all be done).**
- `flows/poem_loop/prompts/shared/review.prompt`: PoemReview
  `contract_checks` gets per-gate rejects for `brief_match`,
  `rationale_fit`, `finish_quality`, plus catch-all accept.
- `flows/software_engineering_demo/prompts/shared/review.prompt`:
  ArchitectReview per-gate rejects for `issue_understood`,
  `repo_plan_real`, `next_step_clear`.
- Same file: DeveloperReview per-gate rejects for
  `requested_change_present`, `proof_recorded`, `commit_state_clear`.
- Same file: QaReview per-gate rejects for `requirements_met`,
  `proof_real`, `finish_ready`.
- `flows/_stdlib_smoke/prompts/AGENTS.prompt`: SmokeReview per-gate
  reject for `artifact_named`, plus catch-all accept.

**Verification (required proof).** Re-emit the three flows. Diff the
emitted `build/` review readbacks — each review should now render N
reject lines + 1 accept line in the contract-checks section. `uv run
pytest tests/unit -q` passes.

**Docs/comments (propagation; only if needed).** None beyond the
authored review bodies.

**Exit criteria (all required).**
- No `accept ... when contract.passes` appears in Rally's shipped
  `.prompt` source except when paired with per-gate rejects.
- All three flows compile.
- Emitted review readback has one reject line per gate.

**Rollback.** `git checkout flows/*/prompts/shared/review.prompt
flows/_stdlib_smoke/prompts/AGENTS.prompt`.

## Phase 3 — Poem review schema+gates migration (F-3)

**Goal.** Convert `workflow PoemReviewContract` to `schema
PoemReviewContract` with a `gates:` block so it matches the
Engineering reviews' canonical form and Phase 2's per-gate rejects
compile against typed gate names.

**Work.** Replace the `workflow PoemReviewContract` block with a
`schema PoemReviewContract` block containing a `sections:` / `gates:`
pair. Gate names stay `brief_match`, `rationale_fit`, `finish_quality`.
Keep body text identical where possible so the readback diff is minimal.

**Checklist (must all be done).**
- `flows/poem_loop/prompts/shared/review.prompt:27-35` rewritten as
  `schema PoemReviewContract: "Poem Review Contract"` with `sections:`
  (one `summary` stub matching the Engineering reviews' pattern) and
  `gates:` (the three existing gates).
- `review PoemReview.contract:` still references `PoemReviewContract`.

**Verification (required proof).** Re-emit `poem_loop`. The emitted
review contract renders as `schema` with `gates:`. `uv run pytest
tests/unit -q` passes.

**Docs/comments (propagation; only if needed).** None.

**Exit criteria (all required).**
- `flows/poem_loop/prompts/shared/review.prompt` has no remaining
  `workflow <Name>Contract` blocks.
- The poem review compiles and emits with per-gate rejects from
  Phase 2.

**Rollback.** `git checkout flows/poem_loop/prompts/shared/review.prompt`.

## Phase 4 — Normalize review_fields shorthand (F-4)

**Goal.** Confirm every reviewer agent's inline `review_fields:` block
uses the canonical bare-name + typed-rename shorthand, and record the
cross-agent duplication as a Doctrine gap since v5 has no
`final_output.review_fields: <SharedDecl>` binding.

**Work.** The five reviewer agents (PoemCritic, ArchitectReviewer,
DeveloperReviewer, QaReviewer, RepairPlanReviewer) all already carry
the 8-line bare-name shorthand block. Phase 4 is an audit + Decision
Log entry pass: walk all five blocks, verify they are identical in
form (bare names where binds are identity; `alias: source` renames
where the review semantic name differs from the carrier field).
Add a short pattern-propagation comment at each `review_family
...fields:` block explaining why the agent-side final_output.review_fields
restates the same binding, so the next author understands the gap
before trying to share it.

**Checklist (must all be done).**
- Walk all five agent `final_output.review_fields:` blocks and confirm
  canonical shorthand.
- Add one-line pattern-propagation comment above `review_family
  EngineeringReviewFamily.fields:` in
  `flows/software_engineering_demo/prompts/shared/review.prompt`.
- Add a parallel comment above `review PoemReview.fields:` in
  `flows/poem_loop/prompts/shared/review.prompt`.
- Append a Section 10 Decision Log entry recording the Doctrine gap
  (tracked under F-4 forward) for a future `final_output.review_fields:
  <SharedDecl>` feature.

**Verification (required proof).** `uv run pytest tests/unit -q`
passes. Re-emit flows; readback changes should be limited to the
added comments.

**Docs/comments (propagation; only if needed).** Two single-line
comments at `review_family.fields:` / `review.fields:` anchors.

**Exit criteria (all required).**
- All five reviewer agent `review_fields` blocks use consistent
  shorthand form.
- Pattern-propagation comments live at the two review-vocabulary
  anchors.
- Decision Log has the F-4 Doctrine-gap entry.

**Rollback.** `git checkout flows/*/prompts/shared/review.prompt
docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md`.

## Phase 5 — Shared work-role turn-result schema (F-5)

**Goal.** Extract the repeated work-role turn-result schema pattern
(three near-identical schemas differing only by route target) in
`flows/software_engineering_demo/prompts/AGENTS.prompt` into one
parent schema under `flows/software_engineering_demo/prompts/shared/`.

**Work.** Create `flows/software_engineering_demo/prompts/shared/turn_results.prompt`
with an abstract schema that inherits the stdlib base fields and adds
the shared `field_notes` pattern. The three role schemas (Architect,
Developer, QaDocs) keep their flow-local `route field next_route:`
declarations and inherit the parent. The three shapes/outputs keep
their route-target-specific `field_notes` overrides and references.

**Checklist (must all be done).**
- Create `flows/software_engineering_demo/prompts/shared/turn_results.prompt`
  with the shared parent schema.
- Rewrite `ArchitectTurnResultSchema`, `DeveloperTurnResultSchema`,
  `QaDocsTurnResultSchema` to inherit from the new parent.
- Update the flow's top-level AGENTS.prompt import to add the new
  shared module.
- Verify emitted schemas JSON per role is byte-equivalent on the
  `kind`, `summary`, `reason`, `sleep_duration_seconds`, `agent_issues`
  field set (behavior preservation).

**Verification (required proof).** Re-emit
`software_engineering_demo`. Compare `build/agents/*/schemas/*.schema.json`
pre/post — the shared base fields must remain byte-identical per
role; only the schema authoring shrinks. `uv run pytest tests/unit -q`
passes.

**Docs/comments (propagation; only if needed).** Short header comment
on the new shared file explaining its role as the shared work-role
turn-result scaffold.

**Exit criteria (all required).**
- New shared file exists and compiles.
- All three role schemas inherit from the shared parent.
- Per-role emitted schema JSON preserves field definitions exactly.
- No duplicated `inherit {kind, summary, reason, sleep_duration_seconds,
  agent_issues}` lines in the flow root AGENTS.prompt.

**Rollback.** `git rm flows/software_engineering_demo/prompts/shared/turn_results.prompt`
and `git checkout flows/software_engineering_demo/prompts/AGENTS.prompt`.

## Phase 6 — Skills `host_contract:` (F-6)

**Goal.** Declare the Rally runtime host slots that each skill package
consumes via `host_contract:`, so the typed contract replaces ad-hoc
prose bullets and the compiler can validate env-var references.

**Work.** For each skill package, declare a `host_contract:` block
listing the env vars and paths it consumes. Reference those slots by
typed name in the skill body where they already appear inline. Delete
the prose "Fail loud if X is missing" bullets that the `host_contract`
now encodes.

**Checklist (must all be done).**
- `skills/rally-kernel/prompts/SKILL.prompt`: declare `host_contract:`
  with `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_WORKSPACE_DIR`. Rewrite
  the hard-rules and code blocks to reference slot names where
  applicable.
- `skills/rally-memory/prompts/SKILL.prompt`: declare `host_contract:`
  with `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_AGENT_SLUG`.
- `skills/demo-git/prompts/SKILL.prompt`: declare `host_contract:`
  with the demo repo path slot (and any other host-contract-relevant
  values the skill body spells in prose).
- Re-emit each skill bundle (via `ensure_flow_assets_built` through an
  adopting flow).

**Verification (required proof).** Re-emit `software_engineering_demo`
(adopts all three skills) and `poem_loop` / `_stdlib_smoke` (adopt
rally-kernel). Skill readback must render the new host_contract block
and the prose "Fail loud if X" redundancy must be gone. `uv run pytest
tests/unit -q` passes.

**Docs/comments (propagation; only if needed).** If any skill README
or prose doc spells the env vars redundantly, delete the redundancy.

**Exit criteria (all required).**
- All three skills have `host_contract:` declarations.
- Skill bodies reference slots by typed name.
- Redundant prose "fail loud if RALLY_X is missing" bullets are gone.
- Emitted skill readback shows the new typed-contract block.

**Rollback.** `git checkout skills/rally-kernel/ skills/rally-memory/
skills/demo-git/`.

## Phase 7 — rally-learn v5 teaching refresh (F-7)

**Goal.** Refresh `skills/rally-learn/prompts/` so framework users who
consult rally-learn see v5 canonical forms — enum-typed fields,
per-gate rejects, typed `schema ... gates:`, `review_family` with bare
name shorthand.

**Work.** Additive updates to the rally-learn refs that point at
canonical Doctrine teaching. Cross-link to
`../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt` and
`../doctrine/skills/doctrine-learn/prompts/refs/enums.prompt` (or
equivalent) so rally-learn becomes a Rally-specific teaching layer on
top of Doctrine's canonical teaching, not a duplicate.

**Checklist (must all be done).**
- `skills/rally-learn/prompts/SKILL.prompt`: add a v5-forms section
  pointing at the canonical Doctrine refs.
- If `skills/rally-learn/prompts/refs/` has stale teaching around
  `type: string + enum:` or `contract.passes`, update it to v5 canonical.
- Ensure any rally-learn example of turn-result schema or review uses
  the enum-typed form.

**Verification (required proof).** Re-emit rally-learn (via any
adopting flow). Readback shows v5 canonical references. `uv run pytest
tests/unit -q` passes.

**Docs/comments (propagation; only if needed).** None.

**Exit criteria (all required).**
- rally-learn teaching reflects Doctrine v5 canonical forms.
- No deprecated `type: string + enum:` shape in rally-learn examples.
- Rally-learn refs point at canonical Doctrine teaching instead of
  redefining it.

**Rollback.** `git checkout skills/rally-learn/`.

## Phase 8 — Forward markers + Doctrine floor bump (F-8 through F-13)

**Goal.** Leave a short comment marker at each P2–P7 landing site so
the next author can adopt the feature when Doctrine ships it. Bump
the Doctrine version pin. Close the audit doc.

**Work.** Add one-line `# TODO(doctrine v5 P2): override gates` /
similar comments at the five forward-finding landing sites. Bump
`pyproject.toml` `doctrine-agents>=4.0.0,<5` to `>=5.0.0,<6`. Refresh
`uv.lock`. Update
`docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` with a
"landed in commit X" row per finding F-1 through F-8.

**Checklist (must all be done).**
- Add forward-marker comments at P2 (override gates), P3 (typed_as:),
  P5 (typed abstract parameters), P6 (skill mode binding), P7 (`rule`
  primitive) landing sites across Rally source.
- Update `pyproject.toml` Doctrine pin to `>=5.0.0,<6`.
- Refresh `uv.lock` with `uv lock`.
- Update the audit doc with per-finding close rows.

**Verification (required proof).** `uv run pytest tests/unit -q`
passes. `uv sync --dev` resolves cleanly. Re-emit all three flows and
all three skills end-to-end clean.

**Docs/comments (propagation; only if needed).** Audit doc closing
rows; no other live docs need updates beyond what earlier phases did.

**Exit criteria (all required).**
- All three flows compile + lint clean.
- `pyproject.toml` is at v5 floor.
- `uv.lock` is refreshed.
- Audit doc has closing rows for F-1 through F-8.
- Forward-marker comments exist at the P2–P7 landing sites.

**Rollback.** `git checkout pyproject.toml uv.lock docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`.

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- `uv run pytest tests/unit -q` must pass after every phase.
- If `tests/unit/test_flow_loader.py` or similar asserts on
  `final_output.contract.json` field names, keep field names stable
  across the enum lift.

## 8.2 Integration tests (flows)

- Re-emit each flow (poem_loop, software_engineering_demo,
  _stdlib_smoke) and diff `build/` output. Expected deltas only.
- Behavior-preservation check: run `_stdlib_smoke` end-to-end with a
  fixture issue and confirm verdicts match pre-change output.

## 8.3 E2E / device tests (realistic)

N/A for this change.

**Rejected verification:**

- No keyword greps over prompts.
- No doc-audit scripts.
- No file-absence or stale-term checks.
- No new harnesses beyond what Rally already ships.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

One PR on a single branch off `main`. Includes:

- Phase 1–8 source changes
- Doctrine floor bump in `pyproject.toml`
- Refreshed `uv.lock`
- Emitted `build/` readback updates
- Closed audit doc entries

PR description links to this plan doc and to the audit doc.

## 9.2 Telemetry changes

None.

## 9.3 Operational runbook

- Live Rally runs cache emitted `AGENTS.md` per flow; the Rally runtime
  already re-emits via `ensure_flow_assets_built` on first use. Confirm
  no manual re-emit step is required in the deploy.
- If a downstream consumer pins a Rally minor, note the Doctrine floor
  bump in the Rally CHANGELOG (see `docs/VERSIONING.md`).

# 10) Decision Log (append-only)

## 2026-04-19 — Plan created from v5.0 adoption audit

**Context.** Doctrine shipped v5.0 on 2026-04-19. The audit
`docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` identified 13
findings (F-1 through F-13). Findings F-1 and F-2 are breaking;
F-3 through F-8 are shipped-today adoption; F-9 through F-13 wait on
Doctrine P2–P7.

**Options.**
1. Single bundled PR covering F-1 through F-8 plus forward markers for
   F-9 through F-13. (Chosen.)
2. Split F-1/F-2 (breaking) from F-3–F-8 (craft). Rejected: violates
   the AGENTS.md "one approved plan ships as one PR" rule.
3. Defer F-4–F-6 (DRY + host_contract) to a second release. Rejected:
   the audit and the AGENTS.md posture call for landing full scope.

**Decision.** One PR, eight phases, foundational-first. Hard cutover
on enum form. No bridge, no fallback.

**Consequences.**
- Rally's Doctrine floor bumps to v5.0 in the same change. Any
  downstream Rally consumer with a Doctrine-version pin must re-resolve.
- Framework users onboarding through `rally-learn` learn v5 canonical
  forms from the start.
- Three forward-looking features (F-9, F-11, F-12) now have comment
  markers at their landing sites so the next author sees the target.

**Follow-ups.** Revisit F-9 through F-13 when Doctrine phases P2–P7
ship. Consider a `RALLY_DOCTRINE_RULES.md` doc when P7 (`rule`
primitive) ships.

## 2026-04-19 — Research resolution (three open flags closed from repo evidence)

**Context.** Initial plan draft flagged three open questions on
`review_fields` binding, runtime env injection for `host_contract:`,
and Doctrine v5.0 tag availability. Resolved from repo evidence
without user interaction per AGENTS.md question policy.

**Resolutions.**
1. **`review_fields:` shared binding** — No Doctrine v5 feature binds
   `final_output.review_fields:` to a named shared decl. Canonical
   form (per `../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`)
   is inline bare-name shorthand on each reviewer, with the shared
   vocabulary typed once in `review_family.fields:`. Phase 4 rescoped
   from "extract to shared decl" to "shrink to bare-name shorthand."
2. **Runtime host injection** — `src/rally/adapters/base.py` and
   `src/rally/services/home_materializer.py` already set
   `RALLY_CLI_BIN`, `RALLY_AGENT_SLUG`, `RALLY_RUN_ID`, workspace
   paths. Phase 6 `host_contract:` is pure authoring; no runtime
   scope expansion, no scope flag.
3. **Doctrine v5.0 tag** — `pyproject.toml` uses
   `path = "../doctrine"` editable install. Floor pin update is local
   (`<5` → `<6`); external tag coordination is tracked but not a
   blocker for Rally's PR shape.

**Consequences.**
- Phase 2 sharpened to per-gate rejects + final catch-all accept (the
  doctrine-learn canonical pattern), not just "remove `contract.passes`."
- Phase 4 yields a smaller DRY win than the optimistic draft but
  still lands real teaching value and real line reduction.
- Phase 6 has no runtime-expansion risk; full scope is authoring.
- Plan status moved from `draft` to `active`; implementation begins
  from Phase 1.

**Follow-up.** None required to begin implementation.

## 2026-04-19 — F-4 Doctrine gap recorded (review_fields shared bind)

**Context.** Phase 4 implementation confirmed the five reviewer agents
(PoemCritic, ArchitectReviewer, DeveloperReviewer, QaReviewer,
RepairPlanReviewer) already carry the canonical 8-line bare-name +
typed-rename `final_output.review_fields:` shorthand. The shorthand is
identical across all five agents because Doctrine v5 exposes no
`final_output.review_fields: <SharedDecl>` bind that could let the
agents inherit a shared review-field vocabulary from
`review_family.fields:` (or the per-review `fields:` block).

**Gap.** `review_family.fields:` already types the shared review
vocabulary once, but each reviewer agent must still restate the same
shorthand in its `final_output.review_fields:` block. For a five-agent
exemplar this costs 5 × 8 = 40 lines of duplicated authoring with no
behavior difference and a real drift risk across flows.

**Decision.** Land Phase 4 as an audit + propagation-comment pass only.
Two pattern-propagation comments added (one each at
`flows/software_engineering_demo/prompts/shared/review.prompt`
`EngineeringReviewFamily.fields:` and
`flows/poem_loop/prompts/shared/review.prompt` `PoemReview.fields:`)
so the next author sees the intent before trying to share.

**Follow-up.** Tracked forward under F-4: when Doctrine ships
`final_output.review_fields: <SharedDecl>` (or an equivalent shared
binding), collapse the per-agent repeats into one shared ref per
review-family. Until then, Rally's exemplar accepts the duplication as
the canonical v5 form.

## 2026-04-19 — F-6 reclassified as Doctrine gap (host_contract env-var slot)

**Context.** Phase 6 called for declaring a typed `host_contract:` on
each Rally skill (`rally-kernel`, `rally-memory`, `demo-git`) carrying
the env-var / path facts each skill consumes (`RALLY_CLI_BIN`,
`RALLY_RUN_ID`, `RALLY_WORKSPACE_DIR`, `RALLY_AGENT_SLUG`, demo repo
path). Implementation walked Doctrine v5's `host_contract:` grammar at
`doctrine/doctrine/grammars/doctrine.lark` and found the slot-family
enum is closed to `input | output | document | analysis | schema |
table | final_output | receipt`. None of those match the env-var or
filesystem-path scalars Rally skills consume at runtime.

**Gap.** Doctrine v5.0 has no scalar / env-var / path host-slot family.
The audit's fix sketch (`cli_bin: "Path to rally CLI binary."` at
`docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md:246-252`) was
aspirational — it does not parse under v5.0 grammar.

**Decision.** Do not author non-parsing Doctrine. Leave each skill's
prose hard-rule for its env-var dependencies, and add a one-line
`# TODO(doctrine F-6):` forward-marker above each site so the next
author sees the intent and the gap. Phase 6 lands as forward markers
+ this log entry; real adoption waits on Doctrine shipping a
scalar/env-var host-slot family (or an equivalent runtime-fact slot).

**Consequences.**
- Rally skills keep prose "Fail loud if `$RALLY_X` is missing" bullets
  until the Doctrine gap closes.
- The audit F-6 closing row reflects "deferred — Doctrine gap" rather
  than "landed."
- The eight-phase plan shape is preserved; Phase 6 still lands work,
  just scoped to forward markers.

**Follow-up.** Tracked forward under F-6: when Doctrine adds a
scalar/env-var host-slot family, promote the three env-var rules to
typed `host_contract:` slots and delete the prose. Re-emit the three
skill bundles and verify the compiler enforces that Rally's runtime
provides the bound values.

## 2026-04-19 — F-7 deferred pending rally-learn branch merge

**Context.** Phase 7 called for refreshing
`skills/rally-learn/prompts/` with v5 canonical forms. The current
branch `feat/doctrine_v5_adoption` forked from `7b8c404` before commit
`6ad3062 feat: rally-learn skill, enduring docs, stdlib shared-rules
rename` landed on branch `feat/rally_perf`. As a result,
`skills/rally-learn/prompts/` source does not exist at HEAD of this
branch — only the locally-built `skills/rally-learn/build/` tree from
a prior checkout of `feat/rally_perf`.

**Gap.** The audit's F-7 evidence rows
(`docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md:260-289`) point
at paths that live on `feat/rally_perf`, not on this branch.
Implementation on this branch would have no source files to edit.

**Decision.** Defer F-7 to a follow-up PR that lands after
`feat/rally_perf` merges to main (or after the two feature branches
are reconciled). The V5 adoption PR lands F-1 through F-6 + F-8 on
this branch without F-7. The plan's "one-plan ships as one PR" rule
is honored for the scope that was actually implementable on this
branch; F-7 moves to its own small follow-up tied to the rally-learn
branch landing.

**Consequences.**
- The audit closing row for F-7 reads "deferred — depends on
  `feat/rally_perf` merge."
- Rally users consulting rally-learn after this PR lands will see v5
  canonical forms only once the rally-learn branch merges and its
  own v5 refresh lands.
- No rally-learn source is touched by this PR.

**Follow-up.** After `feat/rally_perf` merges to main, open a
follow-up branch that rebases onto main, edits
`skills/rally-learn/prompts/refs/*.prompt` per F-7 checklist, and
re-emits the skill bundle. Expected scope: ~3-4 refs updated, one
cross-link to Doctrine's `../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`,
no runtime changes.
