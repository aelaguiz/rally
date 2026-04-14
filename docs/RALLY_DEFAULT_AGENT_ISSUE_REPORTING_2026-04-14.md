---
title: "Rally - Default Agent Issue Reporting - Architecture Plan"
date: 2026-04-14
status: complete
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - stdlib/rally/schemas/rally_turn_result.schema.json
  - stdlib/rally/examples/rally_turn_result.example.json
  - skills/rally-kernel/prompts/SKILL.prompt
  - src/rally/domain/turn_result.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/runner.py
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/AGENT_IO_DESIGN_NOTES.md
---

# TL;DR

- Outcome: By default, Rally-managed turns that use the shared `rally.turn_results` contract should emit one short `agent_issues` field in their final JSON. The field should say what confused the agent this turn, or `none`. Rally should carry that field into the normalized run record in `home:issue.md` so a later reader can see the issue trail without opening raw adapter files. Local flows can opt out by using their own non-review final-output contract instead of inheriting the shared shape-level guidance.
- Problem: Rally today has one control JSON and optional notes. That keeps turn control clean, but it does not give the framework one default place for agents to say what confused them. The current note path is advisory and only meant for extra run context. Doctrine also only allows one final `TurnResponse`, so a second final message would be the wrong design boundary.
- Approach: Extend the shared Doctrine `rally.turn_results` contract with one passive diagnostics field instead of adding a second output path. Keep routing and run-state control on the current five control keys. Preserve `agent_issues` as side data on the runtime path from `last_message.json` into `home:issue.md`. Make local opt-out a Doctrine-authored contract choice, not a Rally runtime flag.
- Plan: Confirm that the shared final contract is the right owner, then audit every prompt, schema, runtime, doc, and test surface that still assumes the old five-key shape. After that, ship the smallest end-to-end slice: shared Doctrine contract, one explicit local opt-out proof surface, runtime preservation into `issue.md`, aligned docs, and focused proof.
- Non-negotiables: No second turn-ending path. No new default note-only truth surface for issue reporting. No prose scraping to recover agent confusion after the turn. Keep client override local and Doctrine-authored. Keep the control meaning of `kind`, `next_owner`, `summary`, `reason`, and `sleep_duration_seconds` unchanged.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-14
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit against the full approved Section 7 frontier found the
  shared prompt contract, local opt-out lane, runtime preservation, bundled
  assets, generated readback, live docs, and packaged-install proof aligned.
- No execution-side scope cuts, weakened acceptance criteria, or hidden
  unfinished phase obligations were found in the current implementation.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None.
- Evidence anchors:
  - `stdlib/rally/prompts/rally/base_agent.prompt:88`
  - `skills/rally-kernel/prompts/SKILL.prompt:54`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt:32`
  - `flows/_stdlib_smoke/build/agents/plan_author/AGENTS.md:177`
  - `src/rally/services/final_response_loader.py:23`
  - `src/rally/services/runner.py:1340`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md:255`
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md:33`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:131`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md:32`
  - `tests/unit/test_flow_loader.py:234`
  - `tests/unit/test_final_response_loader.py:126`
  - `tests/unit/test_runner.py:169`
- Proof rerun in this audit:
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `uv run pytest tests/integration/test_packaged_install.py -q`
- Result:
  - bundled sync check passed
  - `245 passed in 5.88s`
  - package build succeeded
  - `2 passed in 9.69s`

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-14
external_research_grounding: skipped 2026-04-14 (repo evidence sufficient)
deep_dive_pass_2: done 2026-04-14
recommended_flow: implement
note: This block tracks stage order only. Repo evidence settled the design without a separate external research pass, and the consistency pass makes the doc decision-complete.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

When this plan is complete, a Rally-managed turn that ends with the shared
`rally.turn_results` contract will still use one final JSON control path, and
that shared default will ask for one short `agent_issues` field. Rally will
keep that field alive when it turns the raw final response into the normalized
`Rally Turn Result` record in `home:issue.md`. That field will never change who
works next, whether the run is done, or whether the run is blocked.

## 0.2 In scope

- Put default agent issue reporting on the shared `rally.turn_results`
  contract in `stdlib/rally/prompts/rally/turn_results.prompt` and its schema.
- Keep the shared field small and plain. The default contract should ask for a
  short problem summary or the literal `none`.
- Preserve that field through Rally runtime loading and issue-ledger writeback
  so later readers can see it in `home:issue.md`.
- Update the shared Rally prompt guidance and docs so the new field is
  explained in one place.
- Keep a simple local opt-out path for clients that do not want this default,
  and prove that path in prompt source instead of a runtime switch.

## 0.3 Out of scope

- A second final output message.
- A new required `rally issue note` on every turn.
- Any parser or summarizer that tries to recover agent confusion from prose
  after the fact.
- A new database, dashboard, or analytics service for doctrine feedback.
- Broad review-family redesign unless research proves one shared helper is
  needed to keep review-native turns honest.

## 0.4 Definition of done (acceptance evidence)

- This plan is confirmed and decision-complete after the consistency pass.
- The shared `rally.turn_results` prompt, schema, and example all show the new
  `agent_issues` field.
- Rebuilt flow readback shows that Rally-managed agents using the shared turn
  result contract now expose that field in their final-output contract.
- Rebuilt flow readback also shows one explicit local opt-out surface that does
  not inherit the shared issue-report wording.
- Rally runtime tests prove that the field is accepted, does not affect turn
  control, and is preserved in normalized `home:issue.md` records.
- The master design, Phase 3 doc, Phase 4 doc, and CLI/logging doc all tell
  the same story about one shared default control path plus one passive
  issue-report field, while keeping the current review-native exception
  explicit.

## 0.5 Key invariants (fix immediately if violated)

- One final JSON path only.
- `agent_issues` is diagnostics only. It never controls routing, done, blocked,
  or sleep behavior.
- No new default note path for this feature.
- No silent drop of `agent_issues` between `last_message.json` and
  `home:issue.md`.
- No new parallel schema or runtime flag just to dodge the shared contract.
- No fallbacks or runtime shims.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep Rally's one-final-output rule intact.
2. Make agent confusion easy to read in the normal run record.
3. Keep the shared contract small and easy for agents to follow.
4. Keep local opt-out simple and local.
5. Avoid new runtime behavior when Doctrine can express the contract cleanly.

## 1.2 Constraints

- Doctrine `final_output:` can only point at one emitted `TurnResponse`.
- The current shared turn-result schema is a strict five-key JSON object with
  `additionalProperties: false`.
- `src/rally/services/flow_loader.py` currently hard-validates non-review turn
  result schemas by exact required control fields. That means this change
  cannot widen the required field set without changing Rally runtime
  validation.
- That same validator only locks the required control-key set. It does not
  reject extra optional properties, so an optional diagnostics field can fit
  the current gate without a `flow_loader.py` source change.
- Doctrine renders output-shape guidance into the final-output contract. That
  means a local output declaration that still points at the shared
  `RallyTurnResultJson` shape will still inherit the shared issue-report
  wording.
- `src/rally/domain/turn_result.py` only models control fields today.
- `src/rally/services/runner.py` writes normalized turn-result records into
  `home:issue.md`, but it only keeps control data for non-review turns.
- `src/rally/services/final_response_loader.py` has two seams today:
  `load_agent_final_response(...)` is the live runtime path, while
  `load_turn_result(...)` is a small control-only helper used by tests.
- The shared note path already exists, but Rally docs say notes are optional
  run context, not the canonical control result.
- Local flows already override the concrete `turn_result` output declaration in
  Doctrine. That means override behavior should stay a prompt-contract concern,
  not a new runtime mode.

## 1.3 Architectural principles (rules we will enforce)

- Put the default on the shared Doctrine contract before adding runtime-only
  behavior.
- Keep control parsing and diagnostics parsing separate in runtime code.
- Keep one shared source of truth for the default field shape and wording.
- Let local flows opt out through their own prompt contract, not through a new
  Rally runtime switch.
- Prefer a small typed field over a second prose path.

## 1.4 Known tradeoffs (explicit)

- Adding one field to the shared final JSON is broader than adding a local note
  pattern, but it keeps the default on the real canonical output path.
- Keeping `agent_issues` outside the `TurnResult` dataclasses preserves control
  purity, but it means runtime code must carry one extra passive value beside
  the parsed turn result.
- Making `agent_issues` optional in the schema preserves local opt-out and the
  current loader contract, but it means the shared default is enforced by
  prompt doctrine rather than by a new required JSON key.
- Making the shared field an optional non-empty string means omission can stay
  the local opt-out signal, while the literal `none` stays the shared "I
  checked and there was no issue" signal.
- Keeping opt-out at the prompt-contract layer means at least one local flow
  should prove the shape-level override path explicitly, which adds a small
  authored proof surface even though runtime stays simpler.
- Using the literal `none` as the shared default readback is slightly less
  compact than `null`, but it gives later readers a clearer signal that the
  agent checked and found no problem.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Rally-managed agents already share one final JSON contract through
`rally.turn_results`. Rally also gives them one advisory issue-note output
through `rally.notes.RallyIssueNote`. The runtime reads the final JSON from
`last_message.json`, parses control fields, and writes a normalized
`Rally Turn Result` block into `home:issue.md`.

## 2.2 What’s broken / missing (concrete)

- There is no framework-default field for agents to say what confused them on
  this turn.
- The advisory note path is not a stable default feedback signal, and current
  guidance says to skip notes when a later reader does not need extra context.
- If we only change prose and do not change the canonical output contract,
  Rally will keep dropping that feedback from the normalized turn-result view.
- A second final assistant message would violate Doctrine's current
  final-output model and Rally's one-control-path rule.

## 2.3 Constraints implied by the problem

- The clean owner is likely the shared final JSON contract, not a second output
  path.
- If local flows must be able to do nothing here, the schema cannot require
  `agent_issues` without also widening Rally's non-review final-response
  validator.
- Because Doctrine renders shape-level guidance in final-output readback, local
  output declarations that still use the shared `RallyTurnResultJson` shape are
  not a true opt-out path on their own.
- Runtime code must preserve the new field without letting it leak into control
  semantics.
- Docs must stop calling the shared result a fixed five-key object once this
  lands.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- Adopt: Doctrine's language docs say `final_output:` names one emitted
  `TurnResponse`, while side artifacts stay ordinary outputs. That makes a
  second final assistant message the wrong tool for this change.
- Adopt: Doctrine agent inheritance and output override rules already let flows
  change the concrete `turn_result` output declaration locally. That means the
  override story should stay prompt-authored, not runtime-configured.
- Reject: A default second prose note as the main issue-reporting surface. It
  would move canonical truth away from the final turn contract and back into an
  optional side path.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `stdlib/rally/prompts/rally/turn_results.prompt` — the shared Doctrine
    final-output contract already owns the standard non-review turn-result
    wording.
  - `stdlib/rally/schemas/rally_turn_result.schema.json` and
    `stdlib/rally/examples/rally_turn_result.example.json` — the shared schema
    and example are the current machine and human contract for non-review final
    JSON.
  - `src/rally/services/flow_loader.py:332-344` — Rally currently hard-validates
    non-review final-response schemas by exact required control fields:
    `kind`, `next_owner`, `summary`, `reason`, and `sleep_duration_seconds`.
    That means a new diagnostics field must stay optional unless we also choose
    to change runtime validation.
  - `../doctrine/tests/test_final_output.py:111-196` — Doctrine renders
    shape-level explanation blocks into the final-output contract. That means a
    local output declaration that still uses the shared
    `rally.turn_results.RallyTurnResultJson` shape will still inherit the
    shared issue-report wording.
  - `src/rally/domain/turn_result.py` — Rally's `TurnResult` dataclasses are
    control-only today.
  - `src/rally/services/final_response_loader.py:36-49` — the loader already
    separates raw payload from parsed control, which is the right seam for one
    passive diagnostics field.
  - `src/rally/services/runner.py:789-820` and
    `src/rally/services/runner.py:1327-1365` — Rally already has one canonical
    non-review path from loaded final response to normalized `Rally Turn Result`
    blocks in `home:issue.md`.
  - `stdlib/rally/prompts/rally/base_agent.prompt`,
    `stdlib/rally/prompts/rally/notes.prompt`, and
    `skills/rally-kernel/prompts/SKILL.prompt` — Rally already distinguishes
    one final JSON control path from one optional note path.
- Canonical path / owner to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt` +
    `stdlib/rally/schemas/rally_turn_result.schema.json` +
    `src/rally/services/final_response_loader.py` +
    `src/rally/services/runner.py` — this is the existing owner path for shared
    non-review turn-result authoring, validation, load, and normalization.
- Existing patterns to reuse:
  - `flows/software_engineering_demo/prompts/AGENTS.prompt:164-233` and
    `flows/poem_loop/prompts/AGENTS.prompt:43-53` — live flows already reuse
    the shared `rally.turn_results.RallyTurnResult` directly.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt:18-53` and
    `flows/_stdlib_smoke/prompts/AGENTS.prompt:76-145` — local flows already
    define their own concrete `Turn Result` outputs and set `final_output:` to
    those local declarations, but they still reuse the shared
    `RallyTurnResultJson` shape today, so they are not yet an explicit opt-out
    proof surface.
  - `src/rally/services/final_response_loader.py:46-49` plus
    `src/rally/services/runner.py:794-803` — review-native turns already prove
    Rally can preserve passive final-response data beside parsed control.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt` — shared final JSON
    guidance is where the default "say the issue or `none`" wording should live.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — shared Rally rules should
    explain that `agent_issues` is diagnostics only.
  - `skills/rally-kernel/prompts/SKILL.prompt` — shared turn skill wording must
    stay aligned with the new default.
- Native model or agent capabilities to lean on:
  - Rally-managed agent turns already emit structured JSON through Doctrine
    schema-backed `final_output`. This feature should use that native structured
    output path instead of asking the model to hide diagnostics in prose notes.
- Existing grounding / tool / file exposure:
  - `home:issue.md` — the shared run ledger already gives later readers the
    canonical place to inspect the normalized turn record.
  - `rally.notes.RallyIssueNote` — the optional note path already exists for
    extra detail when the short diagnostics field is not enough.
- Downstream readers to protect:
  - `flows/software_engineering_demo/setup/prompt_inputs.py` plus
    `tests/unit/test_software_engineering_demo_prompt_inputs.py` read prior
    `Rally Turn Result` blocks, but today they only key off the block title and
    the `Agent:` line. That means an added `Agent Issues:` detail line should
    be low risk as long as block titles and existing fields stay stable.
- Duplicate or drifting paths relevant to this change:
  - `src/rally/_bundled/stdlib/rally/prompts/rally/turn_results.prompt`,
    `src/rally/_bundled/stdlib/rally/schemas/rally_turn_result.schema.json`, and
    `src/rally/_bundled/skills/rally-kernel/SKILL.md` — bundled Rally-owned
    copies can drift if source changes land without bundle sync.
  - `skills/rally-kernel/build/SKILL.md` and `flows/*/build/**` — generated
    readback will drift until the affected flow and skill outputs are rebuilt.
  - `tests/integration/test_packaged_install.py:226-228` proves an external
    workspace can still compile against the shared `rally.turn_results`
    contract, so it is a useful packaging proof surface after the shared
    contract changes.
- Capability-first opportunities before new tooling:
  - Shared schema-backed `final_output` plus existing issue-ledger normalization
    already give Rally the right carrier. No new parser, wrapper, sidecar, or
    note-only channel is needed.
- Behavior-preservation signals already available:
  - `src/rally/services/flow_loader.py:332-344` and the flow-loader unit suite
    already protect the current non-review control schema boundary.
  - The existing runner and final-response loader unit suites already protect
    the path from `last_message.json` to normalized run state.

## 3.3 Decision gaps that must be resolved before implementation

- None for research-stage blockers. Repo evidence plus approved intent settle
  the design enough for `deep-dive`:
  - `agent_issues` should be an optional property on the shared schema so
    Rally's current exact-required-fields validator keeps working and local
    flows can still opt out.
  - The shared Rally prompt contract should still tell agents to emit a short
    issue summary or the literal `none` by default.
  - A true local opt-out should use a local non-review final-output contract
    with a local `output shape` that reuses the shared
    `rally.turn_results.RallyTurnResultSchema` but does not inherit the shared
    shape-level issue-report wording.
  - The audit list must include the live docs and generated readback surfaces
    that still say the shared turn result is a fixed five-key object.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- The shared authored non-review final-output contract lives in
  `stdlib/rally/prompts/rally/turn_results.prompt`.
- Its machine contract lives beside it in
  `stdlib/rally/schemas/rally_turn_result.schema.json` and
  `stdlib/rally/examples/rally_turn_result.example.json`.
- Rally ships bundled copies of that stdlib prompt and the shared skill under
  `src/rally/_bundled/**`, and external workspaces receive those built-ins
  through `rally workspace sync` and bundled-asset sync.
- Live flows take two shapes today:
  - `flows/software_engineering_demo/prompts/AGENTS.prompt` and
    `flows/poem_loop/prompts/AGENTS.prompt` directly import the shared
    `rally.turn_results.RallyTurnResult`.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt` defines local `Turn Result`
    outputs, but those local outputs still point at the shared
    `rally.turn_results.RallyTurnResultJson` shape.
- Generated readback already repeats the current story in
  `flows/software_engineering_demo/build/agents/**`,
  `flows/poem_loop/build/agents/**`, and `skills/rally-kernel/build/SKILL.md`.
- Runtime normalization lives under `src/rally/services/flow_loader.py`,
  `src/rally/services/final_response_loader.py`,
  `src/rally/services/runner.py`, and `src/rally/services/issue_ledger.py`.
- Live design truth for the communication model lives in the master design,
  Phase 3, Phase 4, and CLI/logging docs.

## 4.2 Control paths (runtime)

1. Doctrine emits `AGENTS.contract.json` for each compiled agent, including the
   final-response schema path for non-review turns.
2. `src/rally/services/flow_loader.py` loads that compiled contract and, for
   non-review turns, hard-validates the schema by exact required control keys.
   That gate does not inspect the full property map, so today it would allow an
   extra optional property even though no such property exists yet.
3. The adapter writes the turn-ending JSON to `last_message.json`.
4. `src/rally/services/final_response_loader.py` loads that raw payload.
   Runtime turns use `load_agent_final_response(...)`, while the older
   `load_turn_result(...)` helper only returns the parsed control result.
5. `src/rally/domain/turn_result.py` parses only the control fields into a
   `TurnResult`.
6. `src/rally/services/runner.py` appends any review-native note, then writes a
   normalized `Rally Turn Result` block into `home:issue.md`.
7. For non-review turns, raw payload fields outside the control model are not
   preserved in that normalized issue-ledger block today.

## 4.3 Object model + key abstractions

- `rally.turn_results.RallyTurnResultSchema` is the shared non-review machine
  contract.
- `rally.turn_results.RallyTurnResultJson` is the shared shape-level human
  contract layered on top of that schema.
- `rally.turn_results.RallyTurnResult` is the shared concrete output
  declaration that direct-import flows use as their final output.
- `TurnResult` dataclasses model `handoff`, `done`, `blocker`, and `sleep`
  control only.
- `LoadedFinalResponse` already carries both the raw payload and the parsed
  `TurnResult`, plus optional review note markdown for review-native turns.
- `append_issue_event(...)` in `src/rally/services/issue_ledger.py` is the one
  generic issue-ledger writer; non-review turn-result details are assembled by
  the runner before that call.
- `_append_issue_records_for_turn_result(...)` in `src/rally/services/runner.py`
  is the narrow place that decides which detail lines show up in normalized
  `Rally Turn Result` blocks.
- Doctrine output-shape guidance is part of the final-output contract. So any
  local output that still uses the shared `RallyTurnResultJson` shape inherits
  the shared wording.

## 4.4 Observability + failure behavior today

- `last_message.json` preserves the raw final payload, but later readers are
  expected to use `home:issue.md` as the canonical run ledger.
- `home:issue.md` records the normalized turn result and any optional notes.
- Current normalized non-review turn records show control facts only.
- A bad final JSON fails loud when parsing or validation breaks.
- The only known downstream parser for non-review turn-result blocks keys off
  block titles and `Agent:` lines, not the full detail list.
- Generated readback, bundled copies, shared skill readback, and live docs all
  still carry the old five-key wording, so the current repo tells that story in
  more than one place.
- There is no explicit local opt-out proof surface yet. `_stdlib_smoke` proves
  local output declarations, but not a shape-level override that avoids shared
  issue-report wording.

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not a UI change.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- The shared authored owner stays `stdlib/rally/prompts/rally/turn_results.prompt`.
- The shared schema and example stay beside it in `stdlib/rally/schemas/` and
  `stdlib/rally/examples/`.
- Bundled Rally-owned copies under `src/rally/_bundled/**` stay part of the
  shipped source-of-truth sync story and must be refreshed when the shared
  source changes.
- Direct-import flows keep using the shared `rally.turn_results.RallyTurnResult`
  output and inherit the new default automatically.
- The explicit opt-out path lives in prompt source: a local flow defines its
  own local `output shape` and local final-output declaration, but that local
  shape reuses the shared `rally.turn_results.RallyTurnResultSchema` instead of
  duplicating the machine schema.
- Generated readback, bundled copies, and packaged-install compile output
  remain proof surfaces, not authored source. They should be rebuilt or synced,
  never hand-edited.
- Runtime preservation stays on the current
  `final_response_loader.py -> runner.py -> issue_ledger.py` path.
- Shared docs stay in the current master design, Phase 3, Phase 4, and
  CLI/logging files. No new design doc family is needed for the shipped state.

## 5.2 Control paths (future)

1. A flow that imports the shared `rally.turn_results.RallyTurnResult` directly
   inherits the new default issue-report wording and emits `agent_issues` or
   `none`.
2. A flow that wants no default issue-report guidance defines a local output
   shape and local final-output declaration, reuses
   `rally.turn_results.RallyTurnResultSchema`, and omits the shared
   shape-level wording.
3. `src/rally/services/flow_loader.py` stays source-stable. Its current
   required-fields gate already allows an extra optional property while still
   locking the control keys.
4. `src/rally/services/final_response_loader.py` still parses control through
   `TurnResult`, but `load_agent_final_response(...)` also extracts optional
   `agent_issues` as one non-empty string. Missing means "no diagnostics
   carried." The legacy `load_turn_result(...)` helper stays control-only.
5. `src/rally/services/runner.py` writes `Agent Issues: ...` into the
   normalized `Rally Turn Result` block when `agent_issues` is present,
   including the literal `none`, and does nothing special when absent.
6. `src/rally/services/issue_ledger.py` stays generic. It still just formats
   detail lines it receives from the runner.
7. `rally.notes.RallyIssueNote` remains optional for extra detail. It is not
   the default reporting path for this feature.
8. Bundled-asset sync plus flow rebuild refresh the shipped and generated
   readback surfaces so the repo tells one consistent story. External-workspace
   compile proof still goes through the current packaged-install path.

## 5.3 Object model + abstractions (future)

- Keep `TurnResult` as the control-only model.
- Extend `LoadedFinalResponse` with `agent_issues: str | None` so the loader
  can preserve the new field without changing routing semantics.
- Keep the shared Doctrine schema as the one source of truth for field shape,
  but make `agent_issues` optional and string-only so Rally's current
  non-review final-response validator does not need a same-slice widening just
  to preserve local opt-out.
- If a local flow wants to opt out, it should do so with a local output shape
  that reuses the shared schema but not the shared shape-level explanation, not
  through a new runtime-only setting.
- Keep `load_turn_result(...)` unchanged as a control-only helper. The passive
  diagnostics field belongs on the richer runtime return object, not the
  control-only convenience API.
- `src/rally/services/issue_ledger.py` should stay generic. The runner owns the
  turn-result-specific detail lines, including the new passive diagnostics line.

## 5.4 Invariants and boundaries

- `agent_issues` never affects control routing.
- `agent_issues` is optional at the schema layer but defaulted in shared prompt
  guidance.
- When present, `agent_issues` is one short string. The shared default uses the
  literal `none` when there was no issue.
- Shared direct-import use means default issue reporting. Local opt-out is a
  prompt-contract decision, not a runtime flag.
- Rally never scrapes note prose to rebuild `agent_issues`.
- The shared field stays short and human-readable.
- The default stays in shared prompt source, not in adapter-specific code.
- Review-native turns keep their own control-ready review shapes unless the
  research pass proves one shared helper is needed.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not a UI change.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared prompt contract | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultSchema`, `RallyTurnResultJson`, `RallyTurnResult` | Shared final JSON explains a fixed five-key control object and owns the default human wording | Add `agent_issues` contract text, keep control semantics explicit, and tell shared users to emit one short issue or `none` | Put the default on the canonical Doctrine surface | Shared final JSON now carries passive diagnostics without changing control | Flow compile readback tests |
| Shared schema + example | `stdlib/rally/schemas/rally_turn_result.schema.json`, `stdlib/rally/examples/rally_turn_result.example.json` | shared machine contract | Strict five-key schema and example | Add optional `agent_issues` as a non-empty string property and update the example payload | Keep local opt-out and current runtime validation honest while reserving omission for opt-out | Shared schema adds one passive optional string field | `tests/unit/test_flow_loader.py`, `tests/unit/test_final_response_loader.py`, readback inspection |
| Shared Rally guidance | `stdlib/rally/prompts/rally/base_agent.prompt`, `skills/rally-kernel/prompts/SKILL.prompt` | `rally_contract`, final JSON guidance | Tells agents to end with the shared five-key result | Explain the new default field, the literal `none`, and its passive meaning | Make the default easy to follow in every shared Rally-managed turn | Shared wording for `agent_issues` | Shared skill/readback inspection |
| Direct-import adopters | `flows/software_engineering_demo/prompts/AGENTS.prompt`, `flows/poem_loop/prompts/AGENTS.prompt` | `turn_result`, `final_output` | Directly import `rally.turn_results.RallyTurnResult` | No authored source change expected; rebuild readback and confirm the default propagates | These flows are the real proof that the shared default lands automatically | no local contract change | Flow build inspection |
| Local opt-out proof surface | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | `PlanAuthorTurnResult`, `RouteRepairTurnResult`, `CloseoutTurnResult` | Local outputs still use the shared `RallyTurnResultJson` shape, so they would inherit shared issue-report wording | Add one local output shape that reuses `rally.turn_results.RallyTurnResultSchema`, then repoint these local turn-result outputs at that local shape | Proves that clients can override the default cleanly with Doctrine features instead of runtime switches | local non-review output shape reuses shared schema but owns its own human contract | Flow build inspection |
| Runtime schema gate | `src/rally/services/flow_loader.py` | `_validate_turn_result_schema(...)` | Requires an exact set of required control fields for non-review final JSON | No source change expected. Keep the required control fields unchanged and prove the optional diagnostics field still passes the current gate | Preserve local override and avoid unnecessary runtime widening | Exact required control keys stay the same | `tests/unit/test_flow_loader.py` |
| Control-only domain model | `src/rally/domain/turn_result.py` | `TurnResult`, `parse_turn_result(...)` | Models and parses control only | No source change expected. Keep `agent_issues` outside the control model | Preserve routing purity and avoid widening control APIs | `TurnResult` stays control-only | domain tests plus loader tests |
| Runtime parse path | `src/rally/services/final_response_loader.py` | `LoadedFinalResponse`, `load_agent_final_response(...)`, `load_turn_result(...)` | Keeps raw payload, parsed control, and optional review note | Extend `LoadedFinalResponse` and `load_agent_final_response(...)` with passive `agent_issues`; keep `load_turn_result(...)` control-only | Preserve diagnostics without changing the smaller helper API | Loader exposes passive `agent_issues` on the rich runtime return object only | `tests/unit/test_final_response_loader.py` |
| Runtime ledger writeback | `src/rally/services/runner.py` | `_append_issue_records_for_turn_result(...)` | Writes control facts only into `home:issue.md` | Include `Agent Issues: ...` when present and leave the line absent when not provided | Make the issue trail readable in the canonical run log | Normalized `Rally Turn Result` shows passive diagnostics | `tests/unit/test_runner.py`, `tests/unit/test_issue_ledger.py` |
| Generic issue writer | `src/rally/services/issue_ledger.py` | `append_issue_event(...)` | Formats generic issue blocks from supplied detail lines | No source change expected | Keep formatting generic and prevent turn-result special cases from leaking into the generic writer | issue writer stays generic | `tests/unit/test_issue_ledger.py` |
| Downstream issue-log reader | `flows/software_engineering_demo/setup/prompt_inputs.py`, `tests/unit/test_software_engineering_demo_prompt_inputs.py` | `latest_turn_agent(...)`, `review_facts(...)` | Reads prior `Rally Turn Result` blocks to find the last agent | Likely no source change; add or update proof so an extra `Agent Issues:` line does not break the reader | Protect the only known downstream parser | existing parser remains compatible with richer block details | `tests/unit/test_software_engineering_demo_prompt_inputs.py` |
| Generated readback | `flows/software_engineering_demo/build/agents/**`, `flows/poem_loop/build/agents/**`, `skills/rally-kernel/build/SKILL.md` | emitted markdown and contract readback | Generated outputs still tell the old five-key story | Rebuild after source edits and inspect the changed readback | Prevent stale emitted docs from contradicting source | emitted readback matches the shared default and local opt-out story | Flow/skill compile inspection |
| Bundled copies | `src/rally/_bundled/**`, `tools/sync_bundled_assets.py`, `tests/unit/test_bundled_assets.py` | bundled stdlib and skill copies | Packaged built-ins mirror repo-root source | Sync bundled copies after shared-source changes and keep drift check green | Prevent installed-package drift | Bundled copies match repo-root source | `tests/unit/test_bundled_assets.py` |
| External compile proof | `tests/integration/test_packaged_install.py` | packaged install compile flow | Confirms an external workspace can compile against Rally built-ins | Likely no source change; keep it green after the shared contract expands | Protect the shipped workspace story | external compile still resolves the shared turn-result contract | `tests/integration/test_packaged_install.py` |
| Live docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` | communication model text | Several docs still describe a five-key shared result | Update the live story in one pass | Prevent doc drift | Shared final JSON story includes passive `agent_issues` and local prompt-level opt-out | Docs inspection after code change |

## 6.2 Migration notes

- Canonical owner path should stay the shared `rally.turn_results` contract.
- Deprecated APIs: none planned. Keep `TurnResult`, `load_turn_result(...)`,
  and `append_issue_event(...)` in place.
- Delete list:
  - any live doc wording that says the shared result is fixed to five keys once
    the shipped schema changes
  - any generated readback or bundled copy that still tells the old five-key
    story after rebuild or sync
- Explicit opt-out path:
  use a local output shape that reuses `rally.turn_results.RallyTurnResultSchema`
  instead of the shared `RallyTurnResultJson` shape. Do not add a runtime flag.
- Capability-replacing harnesses to delete or justify:
  none. Do not add a recovery parser, sidecar note format, or second end-turn
  helper for this feature.
- Keep bundled copies under `src/rally/_bundled/**` and generated readback
  under `skills/*/build/**` and `flows/*/build/**` aligned through the normal
  sync and compile paths. Do not hand-edit generated readback.
- Live instructions to sync: shared Rally base prompt, shared Rally skill
  wording, generated skill readback, bundled copies, and the live design docs
  listed above.
- Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_loader.py` for the non-review schema gate
  - `tests/unit/test_final_response_loader.py` for passive final-response
    extraction beside control parse
  - `tests/unit/test_runner.py` and `tests/unit/test_issue_ledger.py` for
    normalized issue-log writeback
  - `tests/unit/test_software_engineering_demo_prompt_inputs.py` for the one
    known downstream reader of `Rally Turn Result` blocks
  - `tests/unit/test_bundled_assets.py` plus
    `uv run python tools/sync_bundled_assets.py --check` for packaged drift
  - `tests/integration/test_packaged_install.py` for external-workspace compile
    proof

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Shared direct-import flows | `flows/software_engineering_demo/prompts/AGENTS.prompt`, `flows/poem_loop/prompts/AGENTS.prompt` | inherit the shared default issue-report contract through direct import | keeps the framework default real instead of local and duplicated | include |
| Local opt-out proof | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | use a local output shape that reuses the shared schema but not the shared shape-level wording | proves client override is real without runtime switches or schema duplication | include |
| Downstream issue-log readers | `flows/software_engineering_demo/setup/prompt_inputs.py` | tolerate a richer `Rally Turn Result` detail list without new parsing rules | prevents hidden breakage in the one known reader of these blocks | include |
| Review-native turns | `shared.review.*` users | add `agent_issues` to review-native final responses | this change is about the shared non-review contract, not review carriers | exclude |
| Bundled assets | `src/rally/_bundled/**` | keep packaged built-ins synced with repo-root source | prevents installed runtime drift after source edits | include |
| Generated readback | `skills/*/build/**`, `flows/*/build/**` | rebuild affected readback in the same pass | prevents stale emitted contract text from contradicting source | include |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).
>
> These phases are execution order inside one branch or stack. Phase 3 is the
> first ship gate.

## Phase 1 - Shared contract and prompt-level opt-out

Status: complete 2026-04-14 after audit reopen repair.
Proof:
- Rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo` with
  `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`.
- Rebuilt `rally-kernel` with
  `uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel`.
- Synced bundled copies with `uv run python tools/sync_bundled_assets.py`.
- Cold-read the emitted readback and confirmed shared flows picked up default
  `agent_issues` guidance from the shared Rally rules while `_stdlib_smoke`
  kept local control wording in its opt-out final-output lane.

- Goal:
  Put the default issue-reporting rule on the shared Doctrine contract and add
  one real local opt-out surface in prompt source.
- Work:
  - Update `stdlib/rally/prompts/rally/turn_results.prompt` so the shared
    contract explains `agent_issues`, keeps control semantics explicit, and
    tells shared users to emit one short issue or `none`.
  - Update `stdlib/rally/schemas/rally_turn_result.schema.json` and
    `stdlib/rally/examples/rally_turn_result.example.json` to add optional
    string `agent_issues`.
  - Update `stdlib/rally/prompts/rally/base_agent.prompt` and
    `skills/rally-kernel/prompts/SKILL.prompt` so shared Rally guidance matches
    the new final JSON story.
  - In `flows/_stdlib_smoke/prompts/AGENTS.prompt`, add one local output shape
    that reuses `rally.turn_results.RallyTurnResultSchema` and repoint
    `PlanAuthorTurnResult`, `RouteRepairTurnResult`, and `CloseoutTurnResult`
    at that local shape.
  - Rebuild the affected flow and skill readback and sync bundled copies under
    `src/rally/_bundled/**`.
- Verification (required proof):
  - Recompile the affected readback and inspect:
    `flows/software_engineering_demo/build/agents/**`,
    `flows/poem_loop/build/agents/**`,
    `flows/_stdlib_smoke/build/agents/**`, and
    `skills/rally-kernel/build/SKILL.md`.
  - Run `uv run python tools/sync_bundled_assets.py --check`.
- Docs/comments (propagation; only if needed):
  - No live docs yet. Limit wording changes to shared prompt and skill source in
    this phase.
- Exit criteria:
  - Shared direct-import flows show default `agent_issues` guidance in emitted
    readback.
  - `_stdlib_smoke` shows one local non-review opt-out shape that reuses the
    shared schema without inheriting shared issue wording.
  - Bundled copies are in sync with repo-root source.
- Rollback:
  - Revert the shared prompt, schema, example, guidance, and `_stdlib_smoke`
    changes together before runtime work lands.

## Phase 2 - Runtime preservation and compatibility proof

Status: complete 2026-04-14.
Proof:
- Ran the focused proof set:
  `uv run pytest tests/unit/domain/test_turn_result_contracts.py tests/unit/test_final_response_loader.py tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_issue_ledger.py tests/unit/test_software_engineering_demo_prompt_inputs.py -q`
- Result: `104 passed in 3.61s`

- Goal:
  Preserve `agent_issues` from raw final JSON into normalized `home:issue.md`
  without widening control models or breaking known readers.
- Work:
  - Extend `LoadedFinalResponse` plus
    `load_agent_final_response(...)` in
    `src/rally/services/final_response_loader.py` to carry passive
    `agent_issues: str | None`.
  - Keep `src/rally/domain/turn_result.py`,
    `src/rally/services/flow_loader.py`,
    `src/rally/services/issue_ledger.py`, and
    `load_turn_result(...)` control-only.
  - Update `_append_issue_records_for_turn_result(...)` in
    `src/rally/services/runner.py` to add `Agent Issues: ...` when the passive
    field is present.
  - Add or update focused tests in
    `tests/unit/domain/test_turn_result_contracts.py`,
    `tests/unit/test_final_response_loader.py`,
    `tests/unit/test_runner.py`,
    `tests/unit/test_issue_ledger.py`,
    `tests/unit/test_flow_loader.py`, and
    `tests/unit/test_software_engineering_demo_prompt_inputs.py`.
- Verification (required proof):
  - Run the focused unit proof set for the control-only domain boundary,
    loader, runner, generic issue-ledger behavior, flow-loader schema
    validation, and the downstream issue-log reader.
- Docs/comments (propagation; only if needed):
  - Add one short code comment at the loader boundary only if the passive-field
    split is not clear from the final code.
- Exit criteria:
  - A shared turn result with `agent_issues` reaches normalized
    `home:issue.md`.
  - The exact required control keys still define the non-review gate.
  - The known downstream reader still parses the latest `Rally Turn Result`
    block correctly.
- Rollback:
  - Revert runtime preservation and test updates together. Do not leave the
    shared contract shipped without runtime carry-through.

## Phase 3 - Live docs and final proof

Status: complete 2026-04-14 after audit reopen repair.
Proof:
- Ran `uv run python tools/sync_bundled_assets.py --check`.
- Ran `uv run pytest tests/unit -q` and got `245 passed in 6.31s`.
- Ran `uv build` to produce the required packaged artifacts under `dist/`.
- Ran `uv run pytest tests/integration/test_packaged_install.py -q` and got
  `2 passed in 10.49s`.
- Updated the live doc set so it now says the shared default lives on the
  shared non-review contract and local non-review opt-out stays a prompt-level
  output-shape choice over the shared schema.
- Re-read the rebuilt emitted output and confirmed the shared-default flows and
  `_stdlib_smoke` still tell the same repaired story.

- Goal:
  Make every shipped Rally truth surface tell the same story and prove the
  packaged workspace path still works.
- Work:
  - Update `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` to replace stale five-key-only
    wording with the new shared-contract story while keeping the existing
    review-native exception explicit.
  - Rebuild affected flow and skill readback one more time after the final
    source edits.
  - Run the final proof set:
    `uv run python tools/sync_bundled_assets.py --check`,
    `uv run pytest tests/unit -q`, and
    `uv run pytest tests/integration/test_packaged_install.py -q`.
- Verification (required proof):
  - Inspect final readback for the shared-default flows and `_stdlib_smoke`.
  - Keep bundled sync, full unit coverage, and packaged-install compile proof
    green in the same pass.
- Docs/comments (propagation; only if needed):
  - Remove or rewrite every touched live doc line that still describes the
    shared result as fixed to five keys, while preserving the current
    review-native exception text.
- Exit criteria:
  - Source, generated readback, bundled copies, runtime behavior, packaged
    compile proof, and live docs all agree on one shared default plus local
    prompt-level opt-out for non-review turns, while keeping the current
    review-native exception.
- Rollback:
  - Back out the shared contract, runtime, bundled sync, generated readback,
    and live-doc changes together. Do not leave a mixed story behind.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- Add or update tests for shared turn-result schema handling.
- Keep `tests/unit/domain/test_turn_result_contracts.py` green so the control
  model stays control-only.
- Add focused tests for `load_agent_final_response(...)` and any new passive
  `agent_issues` extraction.
- Add focused tests for normalized `Rally Turn Result` writeback so the issue
  field is preserved when present and ignored when absent.
- Keep `tests/unit/test_issue_ledger.py` green so the generic ledger writer
  still accepts the richer turn-result detail list.
- Keep `tests/unit/test_flow_loader.py` green so the exact required control-key
  contract does not drift.
- Keep the downstream reader proof green so an added `Agent Issues:` line does
  not break flow-local parsing.
- Keep `tests/unit/test_bundled_assets.py` green once bundled copies are
  refreshed.

## 8.2 Integration tests (flows)

- Recompile the affected flow build output and inspect the generated readback,
  especially the shared default flows, `_stdlib_smoke`, and the shared
  `rally-kernel` skill readback.
- Keep the packaged-install compile proof green so the shipped built-ins still
  work in an external workspace.
- Keep the proof set lean. Do not add a new harness just for doctrine feedback.

## 8.3 E2E / device tests (realistic)

- No dedicated E2E run is required in the authoritative checklist for this
  change.
- Rely on the focused runtime tests, compile readback, bundled sync proof, and
  packaged-install proof as the ship gate.
- A manual Rally run can still be a final spot-check after those proofs pass,
  but it is not required to declare the slice complete.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Ship this as one shared contract cutover.
- Execute the phases on one branch or stack. Phase 3 is the first ship gate.
- Do not add a feature flag.
- Update all Rally-owned shared surfaces in the same pass so the framework does
  not tell two stories.

## 9.2 Telemetry changes

- No new store is planned.
- `home:issue.md` is the primary readable record for this feature.
- If later work wants aggregate doctrine feedback, it should start from the
  normalized run record this plan creates instead of inventing a second source
  of truth.

## 9.3 Operational runbook

- Operators should keep reading `home:issue.md` as the main run log.
- After this ships, a `Rally Turn Result` block should show both control
  outcome and any short `agent_issues` text for shared turn-result turns.
- Review-native turns keep their current review JSON path. This change only
  adds issue reporting to the shared non-review turn-result contract.
- A missing field after ship is a bug in prompt readback, runtime preservation,
  or both.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, `# 0)` through `# 10)`, helper blocks, and
    execution-readiness state
  - architecture, call-site audit, phase plan, verification, rollout, and
    cleanup alignment
- Findings summary:
  - readiness state drift: the planning helper block and older follow-up text
    no longer matched the now-complete phase plan
  - authoritative proof drift: the phase plan did not name the control-only
    domain test or the generic issue-ledger test even though earlier sections
    treated those as protected boundaries
  - cleanup drift: the final doc sweep and ship gate wording needed to keep the
    existing review-native exception explicit
- Integrated repairs:
  - marked the external research pass as skipped by repo evidence and updated
    the helper block to point straight to `implement`
  - made the doc's done state explicitly decision-complete after the
    consistency pass
  - restored the control-only domain and generic issue-ledger proof surfaces to
    Section 7 and Section 8
  - made Section 7 and Section 9 explicit that the phases are one branch or
    stack and that Phase 3 is the first ship gate
  - tightened the final doc-sweep and operational language to preserve the
    current review-native exception
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

## 2026-04-14 - Put default issue reporting on the shared final contract

### Context

The user wants Rally agents to say what confused them by default, but also
wants the design to stay elegant and Doctrine-first. Rally already has one
shared final JSON path and one optional issue-note path. Doctrine's current
`final_output` model only allows one emitted `TurnResponse`.

### Options

- Add a second final assistant message for issue reporting.
- Make default issue reporting a required note on every turn.
- Extend the shared final JSON contract with one passive diagnostics field and
  preserve it into the normalized issue ledger.

### Decision

Draft this plan around the shared final JSON contract. Keep one final output.
Add one passive `agent_issues` field. Preserve it into `home:issue.md` through
the current runtime normalization path.

### Consequences

- Shared turn-result docs, schema, and runtime assumptions all need updates.
- Runtime must keep control parsing separate from passive diagnostics data.
- The issue-note path stays available for extra detail but stops being the
  default answer to this problem.

### Follow-ups

- Confirm the North Star.
- Completed in this doc: `research` locked the exact opt-out shape and full
  call-site audit.

## 2026-04-14 - Make opt-out a local shape-level override

### Context

The research pass confirmed that Rally should keep one shared default non-review
contract and one runtime control path. The deep-dive pass then confirmed a
Doctrine detail that matters for override design: shape-level explanation text
renders into the final-output contract, so a local output declaration that still
uses the shared shape is not a true opt-out.

### Options

- Keep the shared shape and try to override only the concrete output
  declaration.
- Add a Rally runtime flag to suppress issue reporting for some flows.
- Keep the shared schema, but let opt-out flows define a local output shape and
  local final-output contract.

### Decision

Keep the shared schema and shared default. Put opt-out at the prompt-contract
layer by defining a local output shape that reuses
`rally.turn_results.RallyTurnResultSchema` without inheriting the shared
shape-level wording.

### Consequences

- The shared default remains strong for direct-import users.
- Client override stays local and Doctrine-authored.
- `_stdlib_smoke` becomes the right proof surface for the local override path.

### Follow-ups

- Completed in this doc: `phase-plan` turned the shared-default lane and local
  opt-out lane into the implementation checklist in Section 7.

## 2026-04-14 - Keep diagnostics on the rich loader path, not the control model

### Context

The second deep-dive pass confirmed that the runtime already has one rich
non-review path from raw final payload to normalized issue-ledger writeback:
`load_agent_final_response(...)` returns `LoadedFinalResponse`, and the runner
already owns the detail lines for `Rally Turn Result` blocks. It also confirmed
that `flow_loader.py` does not need a source change if the new field stays
optional.

### Options

- Add `agent_issues` to the `TurnResult` dataclasses and widen all control
  helpers.
- Put `agent_issues` only on the rich runtime return object and keep
  `TurnResult` plus `load_turn_result(...)` control-only.
- Add a second parser or sidecar loader just for diagnostics.

### Decision

Keep `TurnResult` and `load_turn_result(...)` control-only. Add passive
`agent_issues: str | None` only to `LoadedFinalResponse` and preserve it
through the runner into `home:issue.md` as `Agent Issues: ...`.

### Consequences

- Routing code stays untouched and easier to trust.
- The live runtime path gains the data needed for issue-ledger preservation.
- Omission stays available for local opt-out, while the shared prompt default
  can still require the literal `none` when there was no issue.

### Follow-ups

- Completed in this doc: `phase-plan` turned the loader, runner, and readback
  proof into the implementation checklist in Section 7.

## 2026-04-14 - Close planning and treat Phase 3 as the ship gate

### Context

The end-to-end consistency pass found no architecture blocker, but it did find
readiness drift. The helper planning block still implied more planning was
pending, the authoritative checklist had dropped two required proof surfaces,
and the final cleanup story needed to keep the current review-native exception
explicit.

### Options

- Keep the helper block and older follow-ups as historical text even though the
  doc now has a complete implementation checklist.
- Treat external research as optional in this case, restore the missing proof
  surfaces, and make the first ship gate explicit.

### Decision

Treat the external research pass as optional and skipped for this doc because
repo evidence already settled the design. Keep the execution order in one
branch or stack, restore the missing proof surfaces, and make Phase 3 the first
ship gate.

### Consequences

- The artifact now has one clear readiness state.
- Implementation can start from Section 7 without hidden planning work.
- The final doc sweep must keep the current review-native exception explicit.

### Follow-ups

- Implement from Section 7.

## 2026-04-14 - Implementation completed on one branch with no scope cuts

### Context

The implementation pass landed the shared default issue-reporting field,
preserved it through the runtime, rebuilt the affected emitted readback, synced
bundled assets, and updated the live design docs. The only proof-time issue was
that the packaged-install test expected fresh `dist/` artifacts, so the final
proof pass had to run `uv build` before the packaged-install test.

### Options

- Leave the packaged-install proof as a red failure caused by missing build
  artifacts.
- Build the repo-owned artifacts, rerun the packaged-install proof, and record
  that precondition in the implementation worklog.

### Decision

Build the wheel and sdist with `uv build`, then rerun
`tests/integration/test_packaged_install.py` as part of the same ship-gate
pass.

### Consequences

- The implementation finished with the planned proof set green.
- The authoritative checklist in Section 7 now matches the code and proof
  state.
- A fresh implementation audit can now focus on behavior, drift, and
  follow-through instead of missing execution steps.

### Follow-ups

- Run the fresh hook-owned implementation audit.

## 2026-04-14 - Repair the audit reopen without changing plan scope

### Context

The fresh audit reopened Phase 1 and Phase 3 for completion drift, not runtime
breakage. The missing work was one shared base-agent guidance update plus live
doc language that still failed to say the approved local non-review opt-out
story.

### Options

- Treat the kernel skill as enough shared guidance and leave the base agent
  generic.
- Restore the approved guidance in `base_agent.prompt`, update the live docs to
  name the prompt-level opt-out path, and rerun the reopened proof from that
  repaired source.

### Decision

Restore the approved base-agent guidance, keep local opt-out defined at the
prompt-contract layer over the shared schema, and rerun the rebuilt readback,
bundled sync check, full unit suite, build, and packaged-install proof.

### Consequences

- Phase 1 and Phase 3 are complete again from repaired source.
- The repo now tells one consistent story: shared non-review turns default to
  `agent_issues`, review-native turns still use their own review JSON, and
  local non-review opt-out stays a prompt-authored output-shape choice instead
  of a runtime flag.
- The authoritative audit block still belongs to the next fresh audit pass.

### Follow-ups

- Run the fresh hook-owned implementation audit.
