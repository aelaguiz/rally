---
title: "Rally - Doctrine Elegance Rewrite Plan - Architecture Plan"
date: 2026-04-16
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - ../doctrine/docs/DOCTRINE_HIGH_VALUE_AUTHORING_ELEGANCE_WINS_2026-04-16.md
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/AUTHORING_PATTERNS.md
  - README.md
  - pyproject.toml
  - docs/RALLY_PORTING_GUIDE.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - flows/software_engineering_demo/prompts/AGENTS.prompt
  - flows/software_engineering_demo/prompts/shared/review.prompt
  - flows/poem_loop/prompts/AGENTS.prompt
  - flows/poem_loop/prompts/shared/review.prompt
  - flows/_stdlib_smoke/prompts/AGENTS.prompt
---

# TL;DR

## Outcome

Rewrite the Rally prompt source so stdlib and the example flows use the new
Doctrine syntax where it is a real readability win, keep the deliberate long
forms where titles or ordering still matter, and add clear source comments that
teach the shared patterns.

## Problem

Rally prompt source still carries repeated `inherit` runs, repeated review
identity binds, repeated long module prefixes, and long IO wrapper blocks that
Doctrine now lets us write more cleanly. The example flows also still teach
older verbose forms in places where Rally should now show the cleaner pattern.

## Approach

Use the audit as input evidence, then implement the rewrite by owner layer:
Rally stdlib first, shared review carrier files next, flow entry prompts after
that, and a final conditional sweep for cases where shorthand might change
visible titles or hurt readability. Add teaching comments at the first useful
owner in stdlib and examples so later authors can see when each shorthand fits
and when it does not.

## Plan

1. Rewrite the strong stdlib candidates and add shared pattern comments there.
2. Sweep the shared review carrier files and the flow entry prompts across
   `software_engineering_demo`, `poem_loop`, and `_stdlib_smoke`.
3. Close the full audit scope by handling or explicitly keeping every
   conditional and no-hit case with comments where the keep decision matters.
4. Rebuild the affected flows with the paired Doctrine compiler and inspect the
   generated readback and contract files.

## Non-negotiables

- No hand edits under `flows/*/build/**`.
- No semantic drift in prompt meaning, routing, review bindings, or visible
  headings that still matter.
- No forced `self:` usage where Rally has no real local-root payoff.
- No title-losing IO shorthand where a wrapper title is still teaching useful
  meaning.
- Comments must explain the shared pattern once at the right owner, not turn
  the prompt tree into narration spam.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-16
recommended_flow: research -> deep dive -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

If we rewrite the Rally prompt source to use the Doctrine 2026-04-16 elegance
syntax only where it is a net win, keep the deliberate long forms where titles
or ordering still matter, and add pattern comments in the shared owners and
first useful examples, then the source tree will become shorter and easier to
teach without changing emitted behavior or compiler-owned readback in harmful
ways.

## 0.2 In scope

- Implement the full source-level cleanup already identified in the audit
  across:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
  - `stdlib/rally/prompts/rally/turn_results.prompt`
  - `flows/software_engineering_demo/prompts/AGENTS.prompt`
  - `flows/software_engineering_demo/prompts/shared/review.prompt`
  - `flows/software_engineering_demo/prompts/shared/skills.prompt`
  - `flows/software_engineering_demo/prompts/shared/outputs.prompt`
  - `flows/poem_loop/prompts/AGENTS.prompt`
  - `flows/poem_loop/prompts/shared/inputs.prompt`
  - `flows/poem_loop/prompts/shared/outputs.prompt`
  - `flows/poem_loop/prompts/shared/review.prompt`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- Use the shipped Doctrine wins that actually fit Rally:
  - import alias and symbol imports
  - grouped `inherit { ... }`
  - identity shorthand for `fields:` and `final_output.review_fields:`
  - one-line first-class `inputs` and `outputs` wrapper refs
- Add many short source comments that explain the shared rewrite patterns in
  Rally stdlib and the example flows.
- Rebuild the affected flows with the paired Doctrine compiler and inspect the
  generated readback.

Implementation framing:

- The deliverable is the prompt-source rewrite plus rebuild proof.
- Keeping this plan doc tidy is bookkeeping, not a success condition.

Allowed architectural convergence scope:

- touch the closely related shared prompt modules in the same flow family when
  they own the repeated pattern
- add or adjust prompt comments in those source files
- regenerate compiler-owned build output by rebuild only

Compatibility posture:

- preserve the current prompt meaning and current generated behavior
- do a clean source-only cutover with no runtime bridge, no fallback, and no
  second syntax owner path

## 0.3 Out of scope

- editing `../doctrine`
- Rally runtime, loader, runner, CLI, tests, or adapter changes
- hand-editing `flows/*/build/**`
- inventing new prompt patterns that are not part of the shipped Doctrine wave
- forcing `self:` into Rally just because it exists
- rewriting low-value sites when that would only reshuffle authored order or
  erase a useful wrapper title

## 0.4 Definition of done (acceptance evidence)

- Every direct candidate from the current audit is implemented in source.
- Every conditional or low-value candidate is either implemented after local
  review or explicitly kept with a clear source comment or doc note saying why.
- The shared pattern comments exist in the Rally stdlib owners and the first
  useful example owners for each syntax family.
- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
  succeeds.
- Generated readback under `flows/*/build/**` is rebuilt, not hand edited, and
  spot inspection shows the intended wording and headings still make sense.
- Review carrier metadata files still reflect the same review binding meaning
  after the source cleanup.

## 0.5 Key invariants (fix immediately if violated)

- No new parallel prompt or docs truth surfaces.
- No manual edits to compiler-owned build output.
- No silent heading drift where Rally still relies on wrapper titles like
  `Saved Run Note` or `Turn Result`.
- No silent routing or review binding drift.
- No fake elegance wins that make the source shorter but harder to read.
- No fallback or shim path. This is a prompt-source cleanup only.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Preserve meaning and emitted behavior.
2. Cover the full current audit scope without dropping the lower-value cases.
3. Land the highest-value elegance wins first.
4. Teach the new patterns with comments in the right shared owners.
5. Avoid churn where the new syntax is legal but not actually better.

## 1.2 Constraints

- Rally root rules say prompt source lives in `.prompt` files and build output
  is generated readback only.
- Prompt and stdlib changes should use the smallest useful proof path:
  rebuild the affected flows and inspect the generated readback.
- The repo wants plain English and lean always-on comments, so the comment plan
  must be useful, not noisy.
- The current Doctrine tree is dirty, but this plan can still target the syntax
  already present in that worktree because the audit grounded itself in that
  source.

## 1.3 Architectural principles (rules we will enforce)

- Put shared pattern comments in the smallest honest owner:
  - Rally stdlib for framework-wide rules
  - shared review prompt files for review-family rules
  - first useful example entry prompt for flow-local pattern examples
- Use grouped `inherit { ... }` only for plain inherited accounting runs.
- Use one-line IO wrapper refs only when the wrapper has one direct ref and no
  local title or local prose that still matters.
- Use review identity shorthand only for real identity binds. Keep explicit
  `semantic: path` when the path is not the same as the semantic name.
- Use import alias or symbol imports only when they clearly reduce repeated
  module noise.
- Keep deliberate long forms when they protect title ownership, local wording,
  or authored order that still helps the reader.

## 1.4 Known tradeoffs (explicit)

- Some grouped-inherit wins are real but low-value because they move an
  `override` line out of the middle of the authored order. Those should be
  inspected one by one, not auto-applied.
- Some `outputs` wrapper shorthands would shorten the file but would also give
  up a useful wrapper title. Those are not automatic wins.
- Adding more comments helps teach the patterns, but too many comments would
  fight the same context-budget rules Rally already uses. The plan needs many
  comments, but they should still sit at shared anchors rather than on every
  line.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- The current audit proves that Rally can use four of the five new Doctrine
  syntax wins.
- Stdlib is already fairly tight. Most of the repetition lives in the example
  flows and their shared review prompt files.
- The source prompt tree has repeated families:
  - repeated plain `inherit` runs
  - repeated identity binds in `fields:` and `final_output.review_fields:`
  - repeated long module prefixes
  - repeated single-ref IO wrapper blocks
- Some shared and example files still teach the older long forms instead of the
  new Doctrine surface Rally should now prefer.

## 2.2 What’s broken / missing (concrete)

- Repeated long forms make the shared prompt files and example entry prompts
  harder to scan than they need to be.
- Review families repeat identity bindings that can now be shorter without
  losing meaning.
- Several example flows still show longer import and IO-wrapper patterns in
  places where the cleaner Doctrine form is now the better example.
- The conditional keep cases need one consistent policy so we do not shorten a
  file at the cost of title loss or worse authored order.

## 2.3 Constraints implied by the problem

- The implementation pass must preserve the full audit coverage, not cherry-pick
  only the easy wins.
- The fix must stay source-owned. It cannot move into runtime code or hide
  behind generated build output.
- The pass must keep the deliberate no-hit story for `self:` and
  `review override fields`.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/DOCTRINE_HIGH_VALUE_AUTHORING_ELEGANCE_WINS_2026-04-16.md`
  is the main feature-wave truth. It names the shipped syntax surface, the
  limits, and the intended use.
- `../doctrine/docs/LANGUAGE_REFERENCE.md` is the public source for the exact
  authored forms and their limits.
- `../doctrine/docs/AUTHORING_PATTERNS.md` explains when the shorthand is a net
  win and when the multiline form should stay.
- The related Doctrine examples ground the same conclusions:
  - import alias and symbol import examples
  - grouped output and IO inheritance examples
  - split review output examples
  - `self:` examples that Rally currently does not need

Adopted stance:

- follow the Doctrine wave as authored
- do not invent a Rally-specific shorthand policy beyond the shipped Doctrine
  rules

Rejected stance:

- do not treat every legal shorthand as mandatory
- do not introduce `self:` into Rally without a real local-root repetition win

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors:
  - `README.md:162-170` says `rally run` and `rally resume` rebuild flows
    before launch.
  - `README.md:221-222` gives the direct emit command for the shipped flow
    targets:
    - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
  - `pyproject.toml` owns the Doctrine emit targets and compile roots.
  - `tests/unit/test_flow_build.py` is the runtime-facing proof that Rally
    uses the Doctrine API to build flow assets.
- Canonical owner path to reuse:
  - prompt source in `stdlib/rally/prompts/**` and `flows/*/prompts/**`
  - generated confirmation only in `flows/*/build/**`
- Adjacent surfaces tied to the same contract family:
  - generated `flows/*/build/agents/*/AGENTS.md` readback
  - generated `flows/*/build/agents/*/final_output.contract.json`
  - prompt-source comments that teach the shared pattern choices
- Compatibility posture:
  - preserve the current prompt meaning and current generated behavior while
    doing a clean source-only cutover to the cleaner Doctrine syntax in owned
    source files
- Existing patterns to reuse:
  - the file-level audit already captured in Section 6 and Appendix A
  - Rally stdlib as the shared owner for framework-wide authoring patterns
  - shared review prompt files as the owner for review-family pattern teaching
- Prompt surfaces / authoring contract to reuse:
  - `.prompt` files remain the only instruction source of truth
  - `flows/*/build/**` remains compiler-owned readback only
- Existing grounding / tool / file exposure:
  - the Rally repo already carries the emit command, prompt source, generated
    readback, and build test coverage needed to prove this cleanup
- Duplicate or drifting paths relevant to this change:
  - older verbose prompt forms still live in stdlib and the example flows
  - hand-edited build output would create a fake parallel truth path and stays
    forbidden
- Behavior-preservation signals already available:
  - the direct `doctrine.emit_docs` rebuild for `_stdlib_smoke`, `poem_loop`,
    and `software_engineering_demo`
  - readback inspection of generated `AGENTS.md`
  - reviewer metadata inspection of generated `final_output.contract.json`
  - `tests/unit/test_flow_build.py` if rebuild work exposes a broader issue

## 3.3 Decision gaps that must be resolved before implementation

No user blocker remains.

The current audit plus the user follow-up already settle the remaining choices:

- full scope means direct candidates, conditional candidates, and explicit
  no-hit cases all stay in scope for review
- the conditional class is resolved this way:
  - apply the rewrite only if it preserves meaningful headings and does not
    make the authored order worse
  - otherwise keep the current form and add a short comment where the keep
    decision teaches a pattern
- `self:` stays unused unless a real local-root call site appears during the
  implementation sweep

<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `stdlib/rally/prompts/rally/`
  - Rally-owned shared prompt source
- `flows/software_engineering_demo/prompts/`
  - example flow entry prompt plus shared helper modules
- `flows/poem_loop/prompts/`
  - example flow entry prompt plus shared helper modules
- `flows/_stdlib_smoke/prompts/`
  - stdlib proof flow entry prompt
- `flows/*/build/**`
  - compiler-owned readback

## 4.2 Control paths (runtime)

1. Source `.prompt` files compile through Doctrine emit targets.
2. Rally uses the generated build output, not the source files, at run time.
3. Review carrier metadata and readback both come from the generated build
   packages.
4. The current change surface is authoring-only. No Rally runtime path changes
   are needed unless rebuild inspection exposes a compiler or contract issue.
5. The main safety edge is build-time drift, not execution-time drift:
   headings, review bindings, and wrapper ownership can silently change if the
   new shorthand is used in the wrong place.

## 4.3 Object model + key abstractions

- Rally stdlib provides the shared base input, output, and turn-result owners.
- Flow entry prompts inherit from that stdlib and add flow-owned route fields,
  review families, and outputs.
- Shared review prompt files own the reusable review carrier shapes and final
  response shapes for each flow family.
- The Doctrine wave adds four Rally-relevant authoring levers:
  - alias and symbol imports
  - grouped `inherit { ... }`
  - identity shorthand inside review-binding maps
  - one-line first-class IO wrapper refs
- The source repetition clusters around:
  - inherited keyed items
  - review binding maps
  - first-class IO wrapper sections
  - repeated module prefixes

## 4.4 Observability + failure behavior today

- The source audit is strong enough to drive implementation.
- The main proof surface is generated build output and metadata after rebuild.
- The failure mode we care about is not runtime crash. It is silent readback or
  heading drift after a source rewrite.
- The most likely risky spots are already known:
  - titled wrappers like `Saved Run Note`
  - grouped-inherit sites that currently read well because `override` sits in
    the middle of the authored order
  - reviewer outputs with two direct refs under one wrapper title

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not applicable. This is prompt-source and generated-readback work only.

<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

Keep the same file ownership:

- source rewrites stay in `stdlib/rally/prompts/**` and `flows/*/prompts/**`
- generated confirmation stays in `flows/*/build/**`
- the prompt tree layout and generated build layout stay the same

## 5.2 Control paths (future)

Keep the same build path:

1. source prompt files change
2. Doctrine rebuilds the affected flows
3. generated readback and metadata reflect the new source shape
4. Rally runtime stays unchanged

## 5.3 Object model + abstractions (future)

- Shared stdlib files become the main teaching anchors for:
  - one-line first-class IO wrappers
  - grouped `inherit { ... }`
- Shared review prompt files become the main teaching anchors for:
  - identity shorthand in review binding maps
  - when explicit paths must stay explicit
- Flow entry prompts become the first useful example owners for:
  - import alias cleanup
  - grouped inherited slot runs
  - direct review-field shorthand usage in real Rally families
- Conditional cases that keep the long form must say why in source comments or
  in this plan.
- There is one chosen contract posture:
  - preserve the current emitted behavior
  - shorten only the authored source where Doctrine now has a better built-in
    form
  - keep existing long forms where title ownership, explicit mapping, or local
    reading order are still part of the meaning

## 5.4 Invariants and boundaries

- The compiler-owned build output remains generated only.
- The emitted wrapper titles that Rally still relies on must stay stable.
- Review binding meaning must stay stable in both generated readback and
  metadata.
- No new local doctrine pattern is allowed. Every rewrite must lower to the
  existing Doctrine surface already present in the current `../doctrine`
  worktree.
- No new runtime helper, parser, shim, or sidecar is allowed for this cleanup.
- No new parallel prompt truth path is allowed. Prompt source stays in
  `.prompt` files and proof stays in generated readback.
- Comments stay in source owners only. Do not add commentary to generated
  readback by hand.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not applicable.

<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| stdlib | `stdlib/rally/prompts/rally/base_agent.prompt` | `RallyManagedInputs`, `RallyRuntimeEnvInputs`, `RallyManagedOutputs` | shared IO wrappers are partly verbose; `RallyManagedOutputs` uses a titled wrapper that still teaches meaning | rewrite the safe single-ref wrappers to one-line refs; keep `RallyManagedOutputs` long; add owner comments | stdlib should teach when IO shorthand is safe and when title-bearing wrappers should stay explicit | no external contract change; authored source only | rebuild all three targets; inspect shared headings in generated `AGENTS.md` |
| stdlib | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultSchema`, `RallyTurnResultJson`, `RallyTurnResult` | one strong repeated `inherit` run and two lower-value grouped-inherit candidates | convert the strong schema case; inspect and resolve the two conditional sites; add owner comments | this is the shared turn-result owner and should model the cleanest safe grouped-inherit pattern | no external contract change; emitted shape must stay stable | rebuild all three targets; inspect turn-result headings and schema readback |
| stdlib | `stdlib/rally/prompts/rally/review_results.prompt` | whole file review-owner pass | no current direct shorthand win identified | keep as-is unless symmetry comments are clearly needed | avoid churn where there is no real elegance gain | none | no direct proof beyond whole-target rebuild |
| software_engineering_demo | `flows/software_engineering_demo/prompts/AGENTS.prompt` | import block; demo input wrapper; three turn-result schemas; role inherit runs; `EngineeringReviewFamily.fields`; three reviewer `final_output.review_fields`; titled reviewer-output keep cases | the main example file still carries repeated module prefixes, repeated inherit runs, identity review binds, and some safe verbose wrappers | apply import cleanup, grouped inherit, review-field shorthand, and safe one-line wrappers; keep multi-ref titled reviewer outputs long; add example comments | this is the biggest example owner and should teach the new surface without losing wrapper meaning | no external contract change; same generated reviewer/output meaning | rebuild target; inspect generated `AGENTS.md` and reviewer `final_output.contract.json` |
| software_engineering_demo | `flows/software_engineering_demo/prompts/shared/review.prompt` | import block; review schema; response tails; final response; `EngineeringReviewJson` keep review | shared review carrier still uses longer inherit runs and import noise | apply grouped inherit and import cleanup; resolve low-value json case explicitly; add family comment | review-family owners should teach shorthand once instead of repeating local reviewer explanations | no external contract change; same review binding meaning | rebuild target; inspect reviewer `AGENTS.md` and `final_output.contract.json` |
| software_engineering_demo | `flows/software_engineering_demo/prompts/shared/skills.prompt` | import block | single-use import remains verbose | convert to symbol import | lower noise in a single-owner helper file | none | rebuild target for readback parity |
| software_engineering_demo | `flows/software_engineering_demo/prompts/shared/outputs.prompt` | import block | single-use import remains verbose | convert to symbol import | lower noise in a single-owner helper file | none | rebuild target for readback parity |
| poem_loop | `flows/poem_loop/prompts/AGENTS.prompt` | import block; `PoemLoopInputs`; `MuseInputs`; `WriterInputs`; turn-result schemas; role inherit runs; `PoemReview.fields`; critic `final_output.review_fields`; titled output keep cases | clean example flow still teaches older verbose forms in multiple spots | apply import cleanup, grouped inherit, safe one-line wrappers, and review-field shorthand; keep title-bearing multi-ref cases long; add example comments | `poem_loop` is the clearest human-scale example of the new authoring style | no external contract change; same readback and review meaning | rebuild target; inspect generated `AGENTS.md` and critic contract |
| poem_loop | `flows/poem_loop/prompts/shared/inputs.prompt` | import block | single-use import remains verbose | convert to symbol import | lower noise in a helper owner | none | rebuild target for readback parity |
| poem_loop | `flows/poem_loop/prompts/shared/outputs.prompt` | import block | single-use import remains verbose | convert to symbol import | lower noise in a helper owner | none | rebuild target for readback parity |
| poem_loop | `flows/poem_loop/prompts/shared/review.prompt` | import block; review schema; response tails; final response; `PoemReviewJson` keep review | shared review carrier still uses longer inherit runs and import noise | apply grouped inherit and import cleanup; resolve low-value json case explicitly; add family comment | review-family owner should carry the pattern once for the flow | no external contract change; same review binding meaning | rebuild target; inspect reviewer readback and contracts |
| _stdlib_smoke | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | import block; three turn-result schemas; smoke review schema and responses; `SmokeReview.fields`; agent inherit runs; reviewer `final_output.review_fields`; titled output keep cases | stdlib smoke file mixes several direct wins with a few explicit keeps | apply import cleanup, grouped inherit, safe one-line wrappers, review-field shorthand, and comments; keep long forms where wrapper title or order still matters | this file is the compact proof bed for the shared patterns | no external contract change; same reviewer meaning | rebuild target; inspect smoke generated `AGENTS.md` and reviewer contract |
| generated proof | `flows/*/build/**` | generated `AGENTS.md`; reviewer `final_output.contract.json` | build output currently reflects the pre-rewrite source | rebuild only; never hand edit; inspect for drift | generated artifacts are the proof surface for this prompt-only cleanup | compiler-owned outputs only | direct rebuild plus readback inspection |
| explicit keeps | same file families above | `self:` and `review override fields` | Doctrine supports them, but Rally has no current call site | keep as explicit no-hit unless a real source call site appears during implementation | forcing unused syntax would be churn, not elegance | none | no direct test; audit closure only |

## 6.2 Migration notes
* Canonical owner path / shared code path:
  * source edits stay in `stdlib/rally/prompts/**` and `flows/*/prompts/**`
  * generated proof stays in `flows/*/build/**`
* Deprecated APIs (if any):
  * none; this is a source cleanup with contract preservation
* Delete list (what must be removed):
  * no runtime or source owner deletion is planned
  * if a local comment becomes redundant after a clearer shared owner comment is
    added, remove the redundant copy during implementation
* Adjacent surfaces tied to the same contract family:
  * generated `AGENTS.md` readback
  * generated reviewer `final_output.contract.json`
  * shared helper prompt files in the same flow family
  * first useful example comments that teach the pattern
* Compatibility posture / cutover plan:
  * preserve the existing generated contract and visible headings
  * do a hard source-level cutover to cleaner Doctrine syntax only where it is
    behavior-preserving
  * keep explicit long forms where the shorthand would change meaning, title
    ownership, or local reading order
* Capability-replacing harnesses to delete or justify:
  * none; this plan uses Doctrine authoring features directly and does not add
    helpers, parsers, or runtime scaffolding
* Live docs/comments/instructions to update or delete:
  * source comments in stdlib and example prompt owners must be added or
    sharpened where they teach the new pattern
  * Appendix A remains the imported audit ledger and should not be deleted
    during implementation
* Behavior-preservation signals for refactors:
  * `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
  * generated `AGENTS.md` readback inspection
  * generated reviewer `final_output.contract.json` inspection
  * `uv run pytest tests/unit -q` only if rebuild exposes a broader issue

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope |
| --- | --- | --- | --- | --- |
| stdlib | `stdlib/rally/prompts/rally/base_agent.prompt` | one-line IO wrapper refs plus keep-comments for titled wrappers | keeps the framework-wide owner from teaching two conflicting IO styles without explanation | include |
| stdlib | `stdlib/rally/prompts/rally/turn_results.prompt` | grouped inherit plus keep-comments around lower-value order-sensitive sites | keeps the shared turn-result owner honest about when grouped inherit helps and when it does not | include |
| review families | `flows/software_engineering_demo/prompts/shared/review.prompt` | grouped inherit and review-family comment | keeps reviewer agents from each re-teaching the same mapping rule | include |
| review families | `flows/poem_loop/prompts/shared/review.prompt` | grouped inherit and review-family comment | same contract family needs the same pattern story | include |
| review families | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | grouped inherit and review-field shorthand comments in the smoke owner | compact proof flow should reflect the same shared pattern set | include |
| example entry prompts | `flows/software_engineering_demo/prompts/AGENTS.prompt` | import cleanup, grouped inherit, review-field shorthand, safe IO shorthand | largest example flow should not drift from the shared style | include |
| example entry prompts | `flows/poem_loop/prompts/AGENTS.prompt` | import cleanup, grouped inherit, review-field shorthand, safe IO shorthand | clearest small example should teach the new patterns directly | include |
| helper imports | `flows/software_engineering_demo/prompts/shared/skills.prompt`, `flows/software_engineering_demo/prompts/shared/outputs.prompt`, `flows/poem_loop/prompts/shared/inputs.prompt`, `flows/poem_loop/prompts/shared/outputs.prompt` | symbol imports | keeps helper files from lagging behind the lower-noise import style | include |
| no-hit syntax | all prompt families | `self:` and `review override fields` | prevents fake adoption of a legal syntax with no current Rally payoff | include as explicit keep |
| broader docs | `docs/RALLY_PORTING_GUIDE.md` and related docs | porting-rule update about the new syntax | useful later, but not required to land the prompt-source rewrite safely | defer |

<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: build this cleanup foundation-first. `Work` explains the unit, but the
> ship-blocking obligations live in `Checklist (must all be done)` and
> `Exit criteria (all required)`. This plan preserves the current emitted
> contract, does a source-only cutover to the cleaner Doctrine syntax where it
> is actually better, keeps explicit long forms where title ownership or local
> reading order still matters, and uses generated build output as the main proof
> surface. Comments belong at the canonical owner, not everywhere.

## Phase 1 — Rewrite Rally stdlib anchors and add shared pattern comments

Status: COMPLETE

Goal:

- Land the strongest shared-owner rewrites first.
- Teach the two framework-wide patterns in Rally stdlib before the examples use
  them.

Work:

- Rewrite `RallyManagedInputs` and `RallyRuntimeEnvInputs` in
  `stdlib/rally/prompts/rally/base_agent.prompt` to one-line IO wrapper refs.
- Keep `RallyManagedOutputs` in the long form.
- Rewrite `RallyTurnResultSchema` in
  `stdlib/rally/prompts/rally/turn_results.prompt` to grouped inherit.
- Inspect the conditional grouped-inherit sites in `turn_results.prompt` and
  decide apply vs keep.
- Add source comments that explain:
  - one-line IO wrapper rules
  - grouped inherit rules
  - why titled wrappers may stay long

Checklist (must all be done):

- [x] `RallyManagedInputs` uses one-line wrapper refs.
- [x] `RallyRuntimeEnvInputs` uses one-line wrapper refs.
- [x] `RallyManagedOutputs` is either intentionally unchanged or documented as a
      deliberate keep.
- [x] `RallyTurnResultSchema` uses grouped inherit.
- [x] conditional grouped-inherit sites in `turn_results.prompt` are reviewed
      and resolved
- [x] pattern comments are added in stdlib where a reader first needs them
- [x] all three flow targets are rebuilt after the stdlib edits
- [x] generated `AGENTS.md` readback is inspected for stdlib-owned headings and
      wording that depend on these shared owners

Verification:

- rebuild all three flow targets with the paired Doctrine compiler
- inspect generated `AGENTS.md` readback for the stdlib-owned headings and
  wording that depend on these shared owners

Docs/comments:

- add comments in `base_agent.prompt` that explain when first-class IO wrapper
  shorthand is safe
- add comments in `turn_results.prompt` that explain when grouped inherit is a
  good win and when a longer form may still read better

Exit criteria (all required):

- the shared stdlib source is shorter where the win is obvious
- no titled wrapper meaning is lost
- the generated readback still makes sense at the shared-owner level
- the stdlib owner comments now teach both the safe shorthand and the explicit
  keep cases

Rollback:

- revert the stdlib prompt source changes
- rebuild the affected flows so generated readback returns to the prior state

## Phase 2 — Rewrite shared review carrier families and add review-pattern comments

Status: COMPLETE

Goal:

- Clean up the shared review-family owners before changing the larger entry
  prompts.

Work:

- Update `flows/software_engineering_demo/prompts/shared/review.prompt`
- Update `flows/poem_loop/prompts/shared/review.prompt`
- Update the smoke review carrier declarations inside
  `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- Apply grouped inherit to the review schema and final-response tails.
- Apply grouped inherit to the clean response tails.
- Add review-family comments that explain:
  - identity shorthand vs explicit path bindings
  - why the carrier still keeps explicit path forms where names differ
  - why some json-shape conditional sites may stay long

Checklist (must all be done):

- [x] `EngineeringReviewSchema` uses grouped inherit.
- [x] `EngineeringReviewResponse` grouped-inherit tails are applied.
- [x] `EngineeringReviewFinalResponse` grouped inherit is applied.
- [x] `PoemReviewSchema` uses grouped inherit.
- [x] `PoemReviewResponse` grouped-inherit tails are applied.
- [x] `PoemReviewFinalResponse` grouped inherit is applied.
- [x] `SmokeReviewSchema` uses grouped inherit.
- [x] `SmokeReviewResponse` grouped inherit is applied.
- [x] `SmokeReviewFinalResponse` grouped inherit is applied.
- [x] review-family source comments explain the binding patterns once per family
- [x] all three flow targets are rebuilt after the review-family edits
- [x] generated reviewer `AGENTS.md` files are inspected for readback drift
- [x] generated reviewer `final_output.contract.json` files are inspected and
      still express the same review-field meaning

Verification:

- rebuild all three flow targets
- inspect generated reviewer `AGENTS.md` files
- inspect generated `final_output.contract.json` for reviewer agents and confirm
  the review-field meaning is still the same

Docs/comments:

- comment the first review family owner in each flow group, not every reviewer
  call site

Exit criteria (all required):

- shared review-family owners show the new syntax clearly
- the generated review carrier and control-ready metadata still agree with the
  old meaning
- each review family teaches identity shorthand versus explicit mapping in the
  shared owner instead of forcing local repetition

Rollback:

- revert the shared review-source edits
- rebuild the affected flows

## Phase 3 — Rewrite the flow entry prompts and shared helper imports

Status: COMPLETE

Goal:

- Apply the main direct candidates in each example flow entry prompt and helper
  prompt file.

Work:

- Update `flows/software_engineering_demo/prompts/AGENTS.prompt`
- Update `flows/software_engineering_demo/prompts/shared/skills.prompt`
- Update `flows/software_engineering_demo/prompts/shared/outputs.prompt`
- Update `flows/poem_loop/prompts/AGENTS.prompt`
- Update `flows/poem_loop/prompts/shared/inputs.prompt`
- Update `flows/poem_loop/prompts/shared/outputs.prompt`
- Update `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- Apply:
  - import alias and symbol-import cleanup
  - one-line IO wrapper refs where no title is lost
  - grouped inherit on long inherited-slot runs and schema-field runs
  - identity shorthand in `fields:` and `final_output.review_fields:`
- Add teaching comments in the first useful example owner for each pattern.

Checklist (must all be done):

- [x] `software_engineering_demo` direct import cleanup is applied
- [x] `software_engineering_demo` direct grouped-inherit and review-field
      rewrites are applied
- [x] `poem_loop` direct import cleanup is applied
- [x] `poem_loop` direct grouped-inherit, IO wrapper, and review-field rewrites
      are applied
- [x] `_stdlib_smoke` direct import cleanup is applied
- [x] `_stdlib_smoke` direct grouped-inherit, IO wrapper, and review-field
      rewrites are applied
- [x] shared helper import cleanups in the helper prompt files are applied
- [x] first useful example comments are added without duplicating the stdlib
      comments word for word
- [x] all three flow targets are rebuilt after the entry-prompt and helper
      edits
- [x] generated readback is inspected for the example entry sections that
      changed
- [x] generated reviewer metadata is inspected again after the entry-prompt
      rewrites

Verification:

- rebuild all three flow targets
- inspect the generated readback for the source sections that changed
- inspect review metadata again after the entry-prompt rewrites

Docs/comments:

- comment one safe one-line IO wrapper example in the examples
- comment one safe grouped-inherit example in the examples
- comment one mixed review-binding example in the examples
- comment why titled wrapper keep cases stay long

Exit criteria (all required):

- the direct candidates across all example flows are done
- the source reads more cleanly
- the example comments show how to use the syntax in Rally, not just in
  Doctrine examples
- helper prompt files no longer lag behind the cleaner import style used by the
  main examples

Rollback:

- revert the flow-entry and helper prompt edits
- rebuild the affected flows

## Phase 4 — Resolve the conditional and explicit keep cases

Status: COMPLETE

Goal:

- Finish the full audit scope honestly instead of stopping after the easy wins.

Work:

- Inspect each conditional site named in the imported audit.
- Apply the rewrite only when it is still a net readability win.
- Otherwise keep the current form and record the reason in a nearby source
  comment or in this doc if the keep reason is cross-file.
- Inspect the explicit no-hit surfaces:
  - `self:`
  - `review override fields`
  - titled wrappers with multiple direct refs
  - low-value grouped-inherit cases around `override`

Checklist (must all be done):

- [x] every conditional site from the imported audit is reviewed
- [x] every conditional site is resolved as apply or keep
- [x] every explicit keep that teaches a pattern has a clear source comment or
      doc note
- [x] the no-hit `self:` story is explicitly preserved
- [x] the no-hit `review override fields` story is explicitly preserved
- [x] all three flow targets are rebuilt after the conditional-sweep edits
- [x] generated headings and sections that could drift from keep-case choices
      are inspected directly

Verification:

- rebuild all three flow targets
- inspect any generated headings or sections that could drift if a conditional
  shorthand changed title ownership or authored order

Docs/comments:

- add short keep-comments for cases like `Saved Run Note`, `Turn Result`, and
  the reviewer output wrappers with two direct refs

Exit criteria (all required):

- the full current audit scope is closed
- there are no remaining silent “maybe later” syntax cases in these file
  families
- every explicit keep that matters to reader understanding is justified at the
  source owner or in this plan

Rollback:

- revert the conditional-site source edits
- rebuild the affected flows

## Phase 5 — Final rebuild, readback audit, and plan closeout

Status: COMPLETE

Goal:

- Prove the source rewrite is clean and leave the work ready for implementation
  audit or closeout.

Work:

- run the paired Doctrine rebuild for all three flow targets
- inspect generated `AGENTS.md` files across the affected flow agents
- inspect generated `final_output.contract.json` files for the reviewer agents
- confirm no prompt-source file was skipped from the direct candidate set
- update this plan doc with implementation truth and any reopened phase only if
  the proof finds a real issue

Checklist (must all be done):

- [x] the three flow targets rebuild cleanly
- [x] generated readback inspection is done for the affected agents
- [x] review metadata inspection is done for the affected reviewer agents
- [x] no manual edits exist under `flows/*/build/**`
- [x] this doc and the final source truth still agree about direct,
      conditional, and no-hit cases

Verification:

- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
- spot inspection of:
  - `flows/software_engineering_demo/build/agents/*/AGENTS.md`
  - `flows/poem_loop/build/agents/*/AGENTS.md`
  - `flows/_stdlib_smoke/build/agents/*/AGENTS.md`
  - reviewer `final_output.contract.json` files in those same build trees

Docs/comments:

- adjust comments only if rebuild inspection shows a source comment is now
  misleading

Exit criteria (all required):

- the source cleanup is fully implemented
- build output is regenerated and sane
- the plan can move to implementation audit with no hidden open fronts
- the implementation result still matches the scope, contract posture, and
  explicit keep decisions recorded in this plan

Rollback:

- revert the prompt-source changes
- rebuild the affected flows

<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Main proof path

- Sync the repo env with `uv sync --dev`.
- Rebuild the three affected flow targets with:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`

## 8.2 Readback inspection

- inspect the generated `AGENTS.md` files for the agents touched by the source
  rewrites
- inspect the generated `final_output.contract.json` files for the reviewer
  agents
- confirm that titled sections such as `Saved Run Note` or `Turn Result` still
  appear where the source intentionally kept the long form

## 8.3 Optional extra proof

- If the rebuild surfaces an unexpected loader or contract issue, run
  `uv run pytest tests/unit -q`.
- If the rebuild is clean and no runtime code changed, the prompt-source proof
  path is the main signal.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout

- This is a source-only cleanup with regenerated build output.
- There is no staged runtime rollout.
- After merge, the normal Rally build path keeps rebuilding flows before launch.

## 9.2 Ops

- The main operator risk is stale generated output after source edits.
- The plan already forbids manual edits to build output and requires a rebuild.

## 9.3 Telemetry

- No new telemetry surface is needed.
- Generated metadata inspection is enough for this change.

# 10) Decision Log (append-only)

- 2026-04-16: The user first asked for a `miniarch-step new` artifact, then
  corrected to `reformat`. The doc therefore stayed in place instead of
  creating a second plan file.
- 2026-04-16: After the first reformat pass, the user corrected the framing.
  The North Star is the repo state after the prompt-source rewrite and rebuild
  proof. Document conversion is bookkeeping only, not part of the deliverable
  outcome or acceptance target.
- 2026-04-16: Full scope means direct candidates, conditional candidates, and
  explicit no-hit cases all remain in scope for review.
- 2026-04-16: The plan preserves the no-hit story for `self:` and
  `review override fields` unless a real Rally call site appears during
  implementation.
- 2026-04-16: Pattern comments are part of the requested behavior. They belong
  in shared stdlib owners and first useful example owners, not in generated
  readback.
- 2026-04-16: The main proof path is rebuild plus readback inspection, not
  runtime code tests, unless the rebuild exposes a broader contract issue.
- 2026-04-16: The deep-dive pass is complete. Sections 4 through 6 now treat
  this work as a pure prompt-source cleanup with contract preservation, no new
  runtime helpers, and generated build artifacts as the main proof surface.
- 2026-04-16: Broader docs follow-through, including any porting-guide wording
  about the new Doctrine syntax, is deferred. The required implementation scope
  in this plan remains prompt source, source comments, rebuild, and readback
  inspection only.
- 2026-04-16: The phase-plan pass is complete. Section 7 is now the
  authoritative execution checklist, with per-phase proof obligations moved
  into `Checklist` and `Exit criteria` so implementation can be audited phase by
  phase without guessing.
- 2026-04-16: The implementation pass is complete. Rally stdlib, the shared
  review owners, and the example flow entry prompts now use the new Doctrine
  shorthand where it is a real readability win, while explicit keep comments
  preserve `Saved Run Note`, `Turn Result`, and multi-output reviewer wrappers.
- 2026-04-16: The no-hit surfaces stayed no-hit. This pass did not add a Rally
  call site that benefits from `self:`, and it did not find a clean Rally use
  for `review override fields`.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-16
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

# Appendix A) Imported Notes (unplaced; do not delete)

The following body preserves the imported audit detail so the reformat does not
drop any original findings.

## Imported source body

# Rally Audit For Doctrine Elegance Wins

This audit is based on Rally prompt source plus the shipped Doctrine changes in
`../doctrine/docs/DOCTRINE_HIGH_VALUE_AUTHORING_ELEGANCE_WINS_2026-04-16.md`.

Plain answer: Rally can use four of the five new Doctrine syntax wins right
now. The best wins are grouped `inherit { ... }`, review-field identity sugar,
one-line IO wrapper refs, and a small import cleanup. `self:` is shipped, but I
do not see a good Rally call site today.

Stdlib is already fairly clean. The bigger payoff is in the example flows,
mostly in the shared review carriers and the main `AGENTS.prompt` entry files.

## Doctrine wins that matter here

- `import module as alias`
- `from module import Name`
- `from module import Name as Alias`
- grouped `inherit {a, b, c}`
- bare identity entries in `review.fields`
- bare identity entries in `review override fields`
- bare identity entries in `final_output.review_fields`
- one-line `key: DeclRef` and `override key: DeclRef` inside `inputs` and
  `outputs`
- `self:path.to.child`

## What I would do first

1. Rewrite every `fields:` and `review_fields:` block that has identity binds.
2. Rewrite long runs of plain `inherit` lines.
3. Rewrite one-line IO wrapper refs where the wrapper is only a direct ref.
4. Do a smaller import cleanup pass.
5. Skip `self:` for now.

## One clear example for each good win

Grouped inherit:

```prompt
output schema RallyTurnResultSchema[BaseRallyTurnResultSchema]: "Rally Turn Result Schema"
    inherit {kind, summary, reason, sleep_duration_seconds}
```

Review field identity sugar:

```prompt
fields:
    verdict
    reviewed_artifact
    analysis: analysis_performed
    readback: findings_first
    current_artifact
    blocked_gate: failure_detail.blocked_gate
    failing_gates: failure_detail.failing_gates
    next_owner
```

One-line IO wrapper ref:

```prompt
inputs RallyManagedInputs: "Inputs"
    issue_ledger: RallyIssueLedger
```

Import cleanup:

```prompt
import rally.base_agent as base
import rally.turn_results as turn_results
import shared.review as review
```

## Stdlib

### `stdlib/rally/prompts/rally/base_agent.prompt`

Strong candidates:

- `RallyManagedInputs` at `:85-87`
  - rewrite `issue_ledger` to `issue_ledger: RallyIssueLedger`
- `RallyRuntimeEnvInputs` at `:90-101`
  - rewrite all four entries to one-line refs:
    `rally_workspace_dir: RallyWorkspaceDir`
    `rally_run_id: RallyRunId`
    `rally_flow_code: RallyFlowCode`
    `rally_agent_slug: RallyAgentSlug`

Not a clean candidate:

- `RallyManagedOutputs` at `:145-147`
  - leave this alone
  - the wrapper title is `"Saved Run Note"`, so the phase 5 shorthand would
    change the visible heading

### `stdlib/rally/prompts/rally/turn_results.prompt`

Strong candidate:

- `RallyTurnResultSchema` at `:40-44`
  - rewrite to `inherit {kind, summary, reason, sleep_duration_seconds}`

Valid but low-value only:

- `RallyTurnResultJson` at `:68-71`
- `RallyTurnResult` at `:85-88`

These can also use grouped `inherit`, but only if we are fine with changing the
current authored order around the `override` line. I would not spend churn on
them first.

### `stdlib/rally/prompts/rally/review_results.prompt`

No good call sites in this wave.

- no import cleanup worth doing
- no `review.fields` or `final_output.review_fields`
- no clean `self:` use
- no strong grouped-inherit win

## `software_engineering_demo`

### `flows/software_engineering_demo/prompts/AGENTS.prompt`

Import cleanup at `:1-14`:

- alias the repeated module prefixes:
  - `rally.base_agent`
  - `rally.turn_results`
  - `shared.review`
  - `shared.contracts`
  - `shared.outputs`
- use symbol imports where only one declaration is needed:
  - `shared.decisions.ArchitectureChoice`

One-line IO wrapper refs:

- `SoftwareEngineeringDemoInputs` at `:17-21`
  - `demo_repo_root: shared.inputs.DemoRepoRoot`
- `Architect` outputs at `:212-214`
  - `override issue_note: shared.outputs.ArchitectIssueNote`
- `Developer` outputs at `:262-264`
  - `override issue_note: shared.outputs.DeveloperIssueNote`
- `QaDocsTester` outputs at `:312-314`
  - `override issue_note: shared.outputs.QaIssueNote`

Grouped inherit:

- `ArchitectTurnResultSchema` at `:24-33`
  - `inherit {kind, summary, reason, sleep_duration_seconds}`
- `DeveloperTurnResultSchema` at `:58-67`
  - same grouped inherit
- `QaDocsTurnResultSchema` at `:92-101`
  - same grouped inherit
- `SoftwareEngineeringRole` at `:126-129`
  - `inherit {rally_contract, read_first, how_to_take_a_turn}`
- `Architect` at `:202-207`
  - `inherit {rally_contract, read_first, how_to_take_a_turn, system_context, issue_truth, repo_rules}`
- `ArchitectReviewer` at `:225-230`
  - same grouped inherit
- `Developer` at `:253-258`
  - same grouped inherit
- `DeveloperReviewer` at `:275-280`
  - same grouped inherit
- `QaDocsTester` at `:303-308`
  - same grouped inherit
- `QaReviewer` at `:325-330`
  - same grouped inherit

Review field identity sugar:

- `EngineeringReviewFamily.fields` at `:139-147`
  - bare names:
    `verdict`
    `reviewed_artifact`
    `current_artifact`
    `next_owner`
  - keep explicit mappings for:
    `analysis: analysis_performed`
    `readback: findings_first`
    `blocked_gate: failure_detail.blocked_gate`
    `failing_gates: failure_detail.failing_gates`
- `ArchitectReviewer.final_output.review_fields` at `:238-248`
  - same bare-name rewrite
- `DeveloperReviewer.final_output.review_fields` at `:288-298`
  - same bare-name rewrite
- `QaReviewer.final_output.review_fields` at `:338-348`
  - same bare-name rewrite

### `flows/software_engineering_demo/prompts/shared/review.prompt`

Import cleanup:

- line `:1`
  - `import rally.review_results as review_results`
  - or symbol-import the three base declarations

Grouped inherit:

- `EngineeringReviewSchema` at `:4-11`
  - `inherit {verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail}`
- `EngineeringReviewResponse` at `:77-100`
  - group the first clean tail to
    `inherit {requirement, verdict, findings_first, failure_detail}`
  - group the closing tail to
    `inherit {trust_surface, standalone_read}`
- `EngineeringReviewFinalResponse` at `:103-115`
  - `inherit {target, shape, requirement, verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail, trust_surface, standalone_read}`

Lower-value only:

- `EngineeringReviewJson` at `:23-26`

That one is legal to tighten too, but the payoff is much smaller than the
schema and response blocks above.

### `flows/software_engineering_demo/prompts/shared/skills.prompt`

Import cleanup:

- line `:1`
  - use `from rally.base_agent import RallyKernelSkill`

### `flows/software_engineering_demo/prompts/shared/outputs.prompt`

Import cleanup:

- line `:1`
  - use `from rally.base_agent import RallyIssueNoteAppend`

## `poem_loop`

### `flows/poem_loop/prompts/AGENTS.prompt`

Import cleanup at `:1-9`:

- alias the repeated prefixes:
  - `rally.base_agent`
  - `rally.turn_results`
  - `shared.inputs`
  - `shared.outputs`
  - `shared.contracts`
  - `shared.review`

One-line IO wrapper refs:

- `PoemLoopInputs` at `:12-16`
  - `poem_draft_file: shared.inputs.PoemDraftFile`
- `MuseInputs` at `:32-37`
  - `previous_poem_review: PreviousPoemReview`
- `WriterInputs` at `:40-45`
  - `previous_muse_turn: PreviousMuseTurn`
- `PoemWriter` outputs at `:209-214`
  - `override issue_note: shared.outputs.WriterIssueNote`
  - `poem_draft: shared.outputs.PoemDraft`

Grouped inherit:

- `MuseInputs` at `:33-34`
  - `inherit {issue_ledger, poem_draft_file}`
- `WriterInputs` at `:41-42`
  - same grouped inherit
- `MuseTurnResultSchema` at `:54-57`
  - `inherit {kind, summary, reason, sleep_duration_seconds}`
- `PoemWriterTurnResultSchema` at `:126-129`
  - same grouped inherit
- `PoemLoopRole` at `:168-170`
  - `inherit {rally_contract, read_first, how_to_take_a_turn}`
- `Muse` at `:178-183`
  - `inherit {rally_contract, read_first, how_to_take_a_turn, system_context, ground_truth, primary_path}`
- `PoemWriter` at `:200-205`
  - same grouped inherit
- `PoemCritic` at `:259-264`
  - same grouped inherit

Review field identity sugar:

- `PoemReview.fields` at `:229-237`
  - bare names:
    `verdict`
    `reviewed_artifact`
    `current_artifact`
    `next_owner`
  - keep explicit:
    `analysis: analysis_performed`
    `readback: findings_first`
    `failing_gates: failure_detail.failing_gates`
    `blocked_gate: failure_detail.blocked_gate`
- `PoemCritic.final_output.review_fields` at `:275-283`
  - same bare-name rewrite

### `flows/poem_loop/prompts/shared/review.prompt`

Import cleanup:

- line `:1`
  - `import rally.review_results as review_results`
  - or symbol-import the three base declarations

Grouped inherit:

- `PoemReviewSchema` at `:4-11`
  - `inherit {verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail}`
- `PoemReviewResponse` at `:40-62`
  - group the first clean tail to
    `inherit {requirement, verdict, findings_first, failure_detail}`
  - group the closing tail to
    `inherit {trust_surface, standalone_read}`
- `PoemReviewFinalResponse` at `:65-77`
  - `inherit {target, shape, requirement, verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail, trust_surface, standalone_read}`

Lower-value only:

- `PoemReviewJson` at `:23-26`

### `flows/poem_loop/prompts/shared/inputs.prompt`

Import cleanup:

- line `:1`
  - use `from shared.outputs import PoemDraftDocument`

### `flows/poem_loop/prompts/shared/outputs.prompt`

Import cleanup:

- line `:1`
  - use `from rally.base_agent import RallyIssueNoteAppend`

## `_stdlib_smoke`

### `flows/_stdlib_smoke/prompts/AGENTS.prompt`

Import cleanup at `:1-3`:

- alias the repeated prefixes:
  - `rally.base_agent`
  - `rally.review_results`
  - `rally.turn_results`

One-line IO wrapper refs:

- `PlanAuthor` inputs at `:258-265`
  - `work_brief: WorkBrief`
  - `routing_facts: RoutingFacts`
- `PlanAuthor` outputs at `:266-270`
  - `repair_plan: RepairPlan`
- `RouteRepair` inputs at `:287-291`
  - `previous_plan_author_turn: PreviousPlanAuthorTurn`

Grouped inherit:

- `PlanAuthorTurnResultSchema` at `:49-52`
  - `inherit {kind, summary, reason, sleep_duration_seconds}`
- `RouteRepairTurnResultSchema` at `:91-94`
  - same grouped inherit
- `CloseoutTurnResultSchema` at `:121-124`
  - same grouped inherit
- `SmokeReviewSchema` at `:157-163`
  - `inherit {verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail}`
- `SmokeReviewResponse` at `:185-193`
  - `inherit {verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail, trust_surface, standalone_read}`
- `SmokeReviewFinalResponse` at `:197-208`
  - `inherit {target, shape, requirement, verdict, reviewed_artifact, analysis_performed, findings_first, current_artifact, next_owner, failure_detail, trust_surface, standalone_read}`
- `PlanAuthor` at `:251-253`
  - `inherit {rally_contract, read_first, how_to_take_a_turn}`
- `RouteRepair` at `:281-283`
  - same grouped inherit
- `Closeout` at `:304-306`
  - same grouped inherit

Review field identity sugar:

- `SmokeReview.fields` at `:226-234`
  - bare names:
    `verdict`
    `reviewed_artifact`
    `current_artifact`
    `next_owner`
  - keep explicit:
    `analysis: analysis_performed`
    `readback: findings_first`
    `blocked_gate: failure_detail.blocked_gate`
    `failing_gates: failure_detail.failing_gates`
- `RepairPlanReviewer.final_output.review_fields` at `:325-335`
  - same bare-name rewrite

## `self:` audit

I do not see a good Rally use today.

- There are no current same-declaration addressable path runs like
  `Root:path.to.child`, `{{Root:path.to.child}}`, or repeated nested readable
  refs that would get shorter and clearer with `self:`.
- Most Rally cross-links are plain declaration refs like `shared.review...` or
  agent keys like `{{Muse:key}}`, not addressable child-path refs.
- I would not add `self:` just to prove we can. Wait until Rally has a real
  workflow, schema, document, or skill body that repeats the same declaration
  root.

I also do not see any Rally prompt that uses `override fields:` today, so that
shipped shorthand has no current call site here.

## Low-value places I would skip for now

- mixed two-line inherit blocks around one `override`, such as:
  - `stdlib/rally/prompts/rally/turn_results.prompt:68-71`
  - `stdlib/rally/prompts/rally/turn_results.prompt:85-88`
  - `flows/software_engineering_demo/prompts/shared/review.prompt:23-26`
  - `flows/poem_loop/prompts/shared/review.prompt:23-26`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt:140-143`
- wrapper titles that are doing real naming work, such as
  `stdlib/rally/prompts/rally/base_agent.prompt:145-147`
- reviewer output blocks with two direct refs under one wrapper title, such as:
  - `flows/software_engineering_demo/prompts/AGENTS.prompt:235-237`
  - `flows/poem_loop/prompts/AGENTS.prompt:269-271`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt:322-324`

## Bottom line

If you want the highest elegance gain for the least churn, do this in order:

1. all review `fields:` and `final_output.review_fields:` blocks
2. all long grouped-inherit runs in flow entry prompts and shared review files
3. all safe one-line IO wrapper refs
4. import alias and symbol cleanup
5. leave `self:` for a later real use case

# Appendix B) Conversion Notes

- This doc was reformatted in place from an audit into the canonical
  miniarch-step artifact because the user explicitly asked for reformat and to
  keep the work in place.
- That reformat is not the goal of the work. The deliverable remains the
  prompt-source cleanup, the pattern comments, and the rebuild proof.
- The main plan sections now carry the implementation policy, sequencing, and
  proof path.
- Appendix A keeps the imported audit detail so no original direct, conditional,
  or no-hit finding was lost during the conversion.
- The full-scope implementation policy is stricter than the old audit summary:
  every conditional and no-hit case now has to be closed explicitly during the
  implementation sweep.
