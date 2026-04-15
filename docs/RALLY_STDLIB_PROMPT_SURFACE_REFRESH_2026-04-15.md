---
title: "Rally - Stdlib Prompt Surface Refresh - Architecture Plan"
date: 2026-04-15
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_PORTING_GUIDE.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/memory.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - skills/rally-kernel/prompts/SKILL.prompt
  - skills/rally-memory/prompts/SKILL.prompt
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/AGENT_IO_DESIGN_NOTES.md
  - ../doctrine/docs/AUTHORING_PATTERNS.md
---

# TL;DR

## Outcome

Refresh Rally's shared prompt surface so every Rally-managed agent starts with one clear line about what Rally is, sees a smaller and more positive shared rule set, and reads cleaner emitted Markdown with less duplication and flatter sections where current Doctrine already supports that shape.

## Problem

The current stdlib output is accurate, but it is too framework-heavy for a first-time agent, too negative in its opening shared block, too repetitive in inputs and outputs, and too full of authoring-note exposition and nested headings.

## Approach

Use only Doctrine features that ship today. Tighten Rally's shared prompt source, remove authoring-only exposition from emitted readback, and use current Doctrine features such as `properties`, `render_profile`, direct `output[...]` inheritance, and short-form `final_output`. Do not depend on new Doctrine compiler work, new syntax, or future schema surfaces in this pass.

## Plan

1. Rewrite Rally's shared AGENTS base and shared binding labels around one action-first Rally context sentence.
2. Normalize the shared first-screen order across shipped flows.
3. Use current Doctrine authoring features to shrink the shared note and shared final-output shells.
4. Move flow-local note outputs and shared skill packages onto the smaller shared pattern.
5. Rebuild flows and skills, sync bundled assets, update docs and tests, and prove the new emitted surface.

## Non-negotiables

- Start with what the agent should do.
- Keep the reading level at about 7th grade.
- Keep one shared ledger at `home:issue.md` and one final JSON control path.
- Remove authoring-note exposition from emitted readback.
- Use only current supported Doctrine language features.
- No new coordination plane, no fallback layer, and no second output path.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-15
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- none. Checked the Phase 4 note outputs at `flows/poem_loop/prompts/shared/outputs.prompt:42` and `flows/software_engineering_demo/prompts/shared/outputs.prompt:47`, representative emitted readback at `flows/poem_loop/build/agents/poem_writer/AGENTS.md:209` and `flows/software_engineering_demo/build/agents/architect/AGENTS.md:236`, the shipped prompt-surface assertions at `tests/unit/test_flow_loader.py:334` and `tests/unit/test_runner.py:738`, and a fresh `uv run pytest tests/unit -q` proof (`289 passed`).

## Reopened phases (false-complete fixes)
- none

## Missing items (code gaps; evidence-anchored; no tables)
- none

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- none
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-15
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-15
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can ship a materially cleaner shared agent surface without changing the runtime model or adding Doctrine features: every Rally-managed `AGENTS.md` and shared `SKILL.md` can start with one short Rally context sentence, keep shared instructions action-first and positive, remove authoring-only exposition, and use the cleanest Markdown shapes the current Doctrine language already supports.

This claim is false if any of these remain true after the work:

- the first shared Rally block still starts with framework exposition instead of one short pickup sentence
- shared note and final-output sections still carry authoring-note exposition that is not part of the agent's live job
- shared notes and shared final-output contracts still ignore the compact current-language patterns Doctrine already supports
- the plan still depends on unsupported Doctrine language or compiler work
- the new shape requires a second control path, a second shared ledger, or runtime fallback behavior

## 0.2 In scope

- Rally stdlib prompt source under `stdlib/rally/prompts/rally/`
- Rally shared skill prompt source for `rally-kernel` and `rally-memory`
- Rally emitted `AGENTS.md` readback across shipped flows that use the shared stdlib
- Rally emitted `SKILL.md` readback for the shared bundled skills
- Doctrine authoring choices that Rally can adopt right now:
  - imports
  - inheritance
  - abstract agents and shared workflows
  - reusable outputs
  - `document`
  - readable blocks such as `definitions`, `properties`, `table`, `sequence`, and `callout`
  - authored `render_profile`
  - semantic render-profile lowering for `analysis.stages`, `review.contract_checks`, and `control.invalidations`
  - direct `output[...]` inheritance
  - short-form `final_output: OutputName`
  - block-form `final_output` only when a split review final really needs `review_fields`
- Rally bundled asset sync and readback propagation
- Tests and docs in Rally that describe or lock the emitted prompt surface

Allowed architectural convergence scope:

- refactor Rally shared prompt source to keep one explanation of Rally and one shared wording style
- refactor Rally flow-local prompt source to reuse shared inherited outputs and clearer binding labels
- update or delete stale Rally docs, comments, and tests that describe the old emitted shape

## 0.3 Out of scope

- changing Rally's runtime ownership model
- changing the meaning of notes, memory, `handoff`, `done`, `blocker`, or `sleep`
- adding a new coordination plane, handoff file, note database, or note parser
- changing flow-local product behavior outside of the shared Rally surface cleanup
- adding prompt-side hacks that only make Rally look cleaner while leaving Doctrine's repeated emission problem in place
- inventing new product features, new skills, or new agent modes
- any Doctrine compiler or renderer change
- grouped ordinary input or output contract rendering that Doctrine does not ship today
- Doctrine-authored structured-output schema declarations or inherited JSON payload fields
- blocking Rally prompt cleanup on future Doctrine work
- pretending `render_profile` can flatten compiler-owned final-output tables or remove fixed wrapper sections when the current compiler does not allow that

## 0.4 Definition of done (acceptance evidence)

Acceptance evidence for this plan is not just "the prose sounds better." The emitted surface has to match the target output below.

### North-star shared Rally line

Every Rally-managed agent home should start its shared section with one line close to this:

```md
Rally runs this flow. Read `home:issue.md` first, use it as the shared ledger for this run, leave a note only when later readers need it, and end the turn with the final JSON this role declares.
```

That line may be polished, but it must stay:

- one line
- action-first
- correct about Rally's real runtime model
- free of Doctrine and compiler jargon

### North-star rendered output: shared AGENTS intro

Current shape to replace:

```md
## Rally Rules

Rally owns the run home, the note path, and the final JSON for this turn.
End the turn with the final JSON shape this turn declares.
Many Rally turns use `rally.turn_results.RallyTurnResult`.
Review-native turns may end with Doctrine review JSON that Rally can read.
Use `home:issue.md` as the shared run ledger for this run.
...
Do not edit `home:issue.md` directly.
```

Target shape:

```md
## Rally Context

Rally runs this flow. Read `home:issue.md` first, use it as the shared ledger for this run, leave a note only when later readers need it, and end the turn with the final JSON this role declares.

## Read First

1. Read `home:issue.md`.
2. Read this role's local rules, files, and outputs.
3. Check `rally-memory` only when past work could help.

## Shared Rules

- Use `home:issue.md` as the shared ledger for this run.
- Leave one short note only when later readers need saved context.
- Use `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"` for that note.
- Keep route truth in final JSON.
- Read shared skills from `home:skills/`.
```

The exact headings may change, but the target properties are fixed:

- shared Rally explanation comes first
- shared rules are shorter and more positive
- hard bans remain only where they prevent real drift or bad state
- no authoring-note exposition

### North-star rendered output: shared Inputs

Current shape to replace:

```md
## Inputs

### Issue Ledger

#### Issue Ledger

- Source: File
- Path: `home:issue.md`
- Shape: Markdown Document
- Requirement: Required

Use `home:issue.md` as the shared run ledger.
```

Target shape:

```md
## Inputs

### Shared Ledger File

#### Issue Ledger

- Source: File
- Path: `home:issue.md`
- Shape: Markdown Document
- Requirement: Required

Use `home:issue.md` as the shared ledger for this run.
```

This is the best current-language target. The current Doctrine input renderer still emits the binding heading and the declaration heading, so the Rally job is to make those two headings do different work instead of repeating the same words.

Required target properties:

- use a clearer binding label when current Doctrine would otherwise repeat the same heading text
- keep the contract bullets short
- keep the live instruction to one short line

### North-star rendered output: shared note output

Current shape to replace:

```md
### Issue Note

#### Issue Note

- Target: Rally Issue Note Append
- Append With: `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`
- Shape: Markdown Document
- Requirement: Advisory

##### Purpose

Leave one short note when a later reader needs context.
Use the shared Rally CLI path instead of editing `home:issue.md` yourself.

##### Run-Local Boundary

Use notes for this run only.
Use `rally-memory` only for cross-run lessons.
```

Target shape:

```md
### Saved Run Note

#### Issue Note

- Target: Rally Issue Note Append
- Append With: `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`
- Shape: Markdown Document
- Requirement: Advisory

- Change Summary: Say what changed when a later reader needs it.
- Proof Run: Name the proof only when it matters.
- Next Step: Name the next useful move when one exists.
```

Doctrine-first authored pattern to prefer today:

```prompt
render_profile CompactRallyNote:
    properties -> sentence
    guarded_sections -> concise_explanatory_shell


output RallyIssueNote: "Issue Note"
    target: rally.issue_ledger.RallyIssueNoteAppend
        append_with: "\"$RALLY_CLI_BIN\" issue note --run-id \"$RALLY_RUN_ID\""
    shape: MarkdownDocument
    render_profile: CompactRallyNote
    requirement: Advisory

    properties saved_context: "Saved Context"
        change_summary: "Change Summary"
            "Say what changed when a later reader needs it."

        proof_run: "Proof Run"
            "Name the proof only when it matters."

        next_step: "Next Step"
            "Name the next useful move when one exists."
```

That pattern is the best current syntax-side move because Doctrine already proves `properties` plus `render_profile` on markdown-bearing outputs. It keeps the note flat after the contract bullets and removes the extra authored sections that do not help the agent act.

Required target properties:

- use flat property bullets after the contract bullets
- remove `Purpose`, `Run-Local Boundary`, and `Standalone Read` as authoring-note exposition when they do not add execution truth
- keep the command path visible

### North-star rendered output: shared final output

Current shape to replace:

```md
## Final Output

### Rally Turn Result

> **Final answer contract**
> End the turn with one final assistant message that follows this schema.

| Contract | Value |
| --- | --- |
| Message type | Final assistant message |
| Format | Structured JSON |
| Shape | Rally Turn Result JSON |
| Schema | Rally Turn Result Schema |
...

#### Payload Fields
...

#### Example
...

#### What `kind` Means
...
```

Current-language target to prefer with shipped features:

````md
## Final Output

### Rally Turn Result

> **Final answer contract**
> End the turn with one final assistant message that follows this schema.

| Contract | Value |
| --- | --- |
| Message type | Final assistant message |
| Format | Structured JSON |
| Shape | Rally Turn Result JSON |
| Schema | Rally Turn Result Schema |
| Profile | OpenAIStructuredOutput |
| Schema file | `schemas/rally_turn_result.schema.json` |
| Example file | `examples/rally_turn_result.example.json` |
| Requirement | Required |

#### Payload Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `kind` | `string` | `handoff`, `done`, `blocker`, or `sleep` |
| `next_owner` | `string \| null` | Owner key for `handoff`; otherwise `null` |
| `summary` | `string \| null` | Short closeout text for `done`; otherwise `null` |
| `reason` | `string \| null` | Block or sleep reason when needed; otherwise `null` |
| `sleep_duration_seconds` | `integer \| null` | Seconds for `sleep`; otherwise `null` |

#### Example

```json
{
  "kind": "done",
  "next_owner": null,
  "summary": "Finished the assigned work.",
  "reason": null,
  "sleep_duration_seconds": null
}
```

#### Field Notes

- Send all five keys every time.
- Use `null` for keys that do not apply.
- Use owner keys like `change_engineer`, not display names.
````

Current-language syntax to prefer today:

```prompt
output shape RallyTurnResultJson: "Rally Turn Result JSON"
    kind: JsonObject
    schema: RallyTurnResultSchema
    example_file: "examples/rally_turn_result.example.json"

    field_notes: "Field Notes"
        "Send all five keys every time."
        "Use `null` for keys that do not apply."
        "Use owner keys like `change_engineer`, not display names."


output RallyTurnResult: "Rally Turn Result"
    target: TurnResponse
    shape: RallyTurnResultJson
    requirement: Required


agent SomeRallyAgent:
    outputs: "Outputs"
        RallyTurnResult
    final_output: RallyTurnResult
```

Required target properties:

- the default Rally path uses short-form `final_output: RallyTurnResult`
- the current shipped Doctrine target keeps the fixed contract table and payload table, because that is what Doctrine emits today
- JSON-facing notes live on the `output shape`, not on a verbose `final_output` block
- block-form `final_output` stays reserved for split review finals that truly need `review_fields`
- no unsupported structured-schema syntax appears in Rally source

### North-star rendered output: shared skill output

Current shape to replace:

```md
# Rally Kernel

Use this skill on Rally-managed turns when you need Rally's shared note and end-turn rules.
Rally loads this skill on every Rally-managed turn. Flows do not need to list it by hand.

## When to use
...

## When not to use
...

## Non-negotiables
...
```

Target shape:

```md
# Rally Kernel

Use this skill when you need to leave a Rally note or end the turn with the final JSON this role declares.

## Quick Model

Rally keeps one shared ledger at `home:issue.md`.
Read it first.
Leave a note only when later readers need saved context.
End the turn with the declared final JSON.

## When To Use It

- Leave one short note for this run.
- Add flat note labels when the flow needs them.
- End the turn with valid Rally JSON.
```

Required target properties:

- start with the agent's live move, not package exposition
- remove sections whose main job is to explain the authoring system to us
- keep only the contract the agent needs on the turn

### Verification evidence

The work is done only when all of these are true:

- Rally emitted `AGENTS.md` in shipped flows matches the north-star shape above
- Rally emitted `SKILL.md` for `rally-kernel` and `rally-memory` matches the same writing standard
- Rally uses current Doctrine compact patterns where they help, especially `properties`, `render_profile`, direct `output[...]` inheritance, and short-form `final_output`
- Rally prompt source does not depend on unsupported Doctrine syntax or local Doctrine forks
- Rally tests prove the new shared wording propagates into flow build output and bundled assets

## 0.5 Key invariants (fix immediately if violated)

- Keep one shared ledger at `home:issue.md`.
- Keep one final JSON control path.
- Keep notes as context only.
- Keep memory as context only.
- Say the move before the guardrail.
- Remove authoring-only exposition from emitted readback.
- Use the cleanest current Doctrine pattern before adding more prose.
- Use clearer binding labels when current Doctrine would otherwise repeat the same heading text.
- Accept current compiler-owned wrapper sections where current syntax cannot flatten them.
- No runtime shim, fallback layer, or second coordination plane.
- No unsupported Doctrine language or compiler work in this pass.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make the first shared Rally block useful to a first-time agent in one read.
2. Remove duplication and authoring-note exposition from emitted readback.
3. Use Doctrine-native authoring and rendering features before inventing custom Rally-only patterns.
4. Keep the shared writing small, direct, positive, and at about a 7th-grade reading level.
5. Keep Rally and Doctrine checked-in truth aligned on the new output shape.

## 1.2 Constraints

- `stdlib/rally/prompts/rally/` is Rally's shared prompt source of truth.
- `flows/*/build/**` is generated readback, not authored source.
- Rally's runtime meaning for notes, memory, and final JSON cannot change in this pass.
- Shared skills are bundled assets and must stay aligned with emitted build output.
- Doctrine is the owner of prompt language and Markdown emission behavior.

## 1.3 Architectural principles (rules we will enforce)

- One explanation of Rally, shared once, in shared source.
- Prefer the flattest current Doctrine pattern that still keeps meaning clear.
- Use clearer binding labels when a shared binding and declaration would otherwise repeat the same name.
- Keep compiler-owned truth in Doctrine; keep Rally-specific wording in Rally stdlib source.
- Remove text that explains the authoring system to the agent when it does not change the agent's live move.

## 1.4 Known tradeoffs (explicit)

- Cleaner emission will create snapshot and string-assert churn in Rally.
- Some current Doctrine wrapper headings and contract tables will remain, because this pass does not change Doctrine.
- Some metadata may move from titled sections into short bullet lines or shape-level field notes, which changes exact readback shape but not meaning.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Rally already has the right runtime model: one shared ledger at `home:issue.md`, notes for context, and one final JSON result for control. That model is described clearly in docs, but the emitted shared prompt surface does not present it in the cleanest order or the cleanest Markdown shape.

## 2.2 What’s broken / missing (concrete)

- the first shared Rally block is framework-first instead of action-first
- the shared wording spends too much early space on bans and framework exposition
- ordinary inputs and outputs repeat the same slot name and definition name as stacked headings
- structure-backed outputs create `#####` and `######` ladders
- shared note and final-output blocks include authoring-only exposition that is not part of the agent's live job
- the shared skill output has the same problem

## 2.3 Constraints implied by the problem

- Rally has to stay inside current Doctrine support for this pass
- some current compiler-owned duplication will remain even after the Rally cleanup
- the new shape has to stay honest about the real runtime model

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

Doctrine is the framework owner for this prompt surface, so the key external anchors for Rally are Doctrine's shipped language docs, checked-in examples, and tests for the features we plan to use:

- `../doctrine/docs/LANGUAGE_REFERENCE.md`
  - proves current shipped support for `document`, readable blocks, `render_profile`, `final_output`, and direct `output[...]` inheritance
- `../doctrine/docs/AGENT_IO_DESIGN_NOTES.md`
  - explains how output inheritance, final output, and render profiles fit together
- `../doctrine/docs/AUTHORING_PATTERNS.md`
  - says to keep a separate `final_output` only when a host truly needs a second machine surface
- `../doctrine/examples/64_render_profiles_and_properties/*`
  - proves compact `properties` plus `render_profile` on markdown-bearing outputs
- `../doctrine/examples/76_final_output_prose_basic/*`
  - proves the clean short-form `final_output: OutputName` path for prose
- `../doctrine/examples/79_final_output_json_schema/*`
  - proves the clean short-form `final_output: OutputName` path for JSON final output with schema and example on the `output shape`
- `../doctrine/examples/104_review_final_output_json_schema_blocked_control_ready/*`, `105_review_split_final_output_json_schema_control_ready/*`, `106_review_split_final_output_json_schema_partial/*`
  - prove when block-form `final_output` plus `review_fields` is worth the extra surface
- `../doctrine/examples/107_*` through `111_*` plus `../doctrine/tests/test_output_inheritance.py`
  - show repo-present output inheritance and inherited final outputs in the current code and tests

## 3.2 Internal ground truth (code as spec)

Rally-side truth:

- `stdlib/rally/prompts/rally/base_agent.prompt`
  - owns the shared Rally context block and shared AGENTS section order
- `stdlib/rally/prompts/rally/memory.prompt`
  - owns Rally's shared read-first and turn-flow wording
- `stdlib/rally/prompts/rally/notes.prompt`
  - currently emits note-purpose and run-boundary exposition that can be cut down or moved into compact note fields
- `stdlib/rally/prompts/rally/turn_results.prompt`
  - currently keeps the JSON contract in a file-backed schema and uses a long `What \`kind\` Means` block that can be simplified
- `skills/rally-kernel/prompts/SKILL.prompt` and `skills/rally-memory/prompts/SKILL.prompt`
  - currently carry too much package and authoring exposition for the first screen
- `flows/poem_loop/build/**`, `flows/software_engineering_demo/build/**`, and `flows/_stdlib_smoke/build/**`
  - prove the current duplicate same-name headings, deep structure ladders, and shared wording drift in emitted readback
- `tests/unit/test_flow_loader.py`, `tests/unit/test_flow_build.py`, and `tests/unit/test_bundled_assets.py`
  - lock parts of the current emitted shape and will need updates when the shared surface changes

Doctrine-side truth:

- `../doctrine/doctrine/_compiler/compile/outputs.py`
  - ordinary outputs still lower to loose bullets plus support items, which sets the limit for this Rally-only pass
- `../doctrine/doctrine/_compiler/compile/final_output.py`
  - final output has a fixed wrapper, fixed contract table, fixed payload table, and fixed support-item lowering
- `../doctrine/doctrine/_compiler/compile/records.py`
  - generic record lowering turns many authored items into titled sections, which drives heading ladders
- `../doctrine/doctrine/_renderer/blocks.py` and `../doctrine/doctrine/renderer.py`
  - render titled sections as nested headings, so repeated compiled sections become repeated heading stacks
- `../doctrine/tests/test_final_output.py`
  - proves the current fixed final-output wrapper and the routes Doctrine already supports
- `../doctrine/tests/test_output_inheritance.py`
  - proves direct output inheritance and inherited final outputs are live in code today

## 3.3 Decision gaps that must be resolved before implementation

This research closed the key gaps for this pass:

- settled: "full Rally stdlib" includes both shared `AGENTS.md` output and shared `SKILL.md` output
- settled: Rally can improve a lot with current Doctrine syntax, especially `properties`, `render_profile`, direct `output[...]` inheritance, and short-form `final_output`
- settled: Rally must stay inside current Doctrine support for this pass
- settled: some duplicate headings and fixed final-output wrapper sections remain acceptable when the current compiler owns them
- settled: no Doctrine compiler, renderer, or future syntax work is in scope here
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Authored shared Rally prompt source lives in `stdlib/rally/prompts/rally/`.
  The files that own this pass are `base_agent.prompt`, `memory.prompt`, `notes.prompt`, `turn_results.prompt`, and `issue_ledger.prompt`.
- Shipped flow entrypoints live in `flows/<flow>/prompts/AGENTS.prompt`.
  `poem_loop`, `software_engineering_demo`, and `_stdlib_smoke` all import `rally.base_agent` and build local agents on top of `RallyManagedBaseAgent`.
- Flow-local note structures live in `flows/poem_loop/prompts/shared/outputs.prompt` and `flows/software_engineering_demo/prompts/shared/outputs.prompt`.
  `_stdlib_smoke` is the smallest shipped flow that still renders the shared generic note and turn-result surfaces.
- Shared skill source lives in `skills/rally-kernel/prompts/SKILL.prompt` and `skills/rally-memory/prompts/SKILL.prompt`.
- Generated readback lives in `flows/*/build/agents/*/AGENTS.md`, `flows/*/build/agents/*/AGENTS.contract.json`, and `skills/*/build/SKILL.md`.
- Packaged built-ins live under `src/rally/_bundled/stdlib/rally/` and `src/rally/_bundled/skills/`.
  Those copies are package assets, not authored source.
- `pyproject.toml` is the emit map for all shipped flows and shared skills.

## 4.2 Control paths (runtime)

- `src/rally/services/runner.py` calls `ensure_flow_assets_built()` before `load_flow_definition()` on both `run` and `resume`.
- `src/rally/services/flow_build.py` owns the front-door rebuild path:
  - sync Rally built-ins into external workspaces
  - validate rooted prompt paths
  - run `python -m doctrine.emit_docs --target <flow>`
  - render role `SOUL.prompt` sidecars
  - run `python -m doctrine.emit_skill --target <skill>` for Doctrine-backed skills
- `src/rally/services/flow_loader.py` then reads compiled `build/agents/*/AGENTS.md` and `AGENTS.contract.json`.
  The runtime does not read `.prompt` files directly once the build exists.
- `src/rally/services/bundled_assets.py` owns packaged built-ins.
  `sync_bundled_assets()` rebuilds the expected package tree from source and skill emit targets, then compares or replaces `src/rally/_bundled/`.
- `src/rally/services/workspace_sync.py` copies bundled built-ins into non-Rally workspaces.
  That means stdlib prompt changes only become packaged truth after rebuild plus bundle sync.

## 4.3 Object model + key abstractions

- `rally.base_agent.RallyManagedBaseAgent` is the shared top-level contract.
  It wires in `rally_contract`, `read_first`, `how_to_take_a_turn`, shared inputs, shared skills, and the default shared note output.
- `RallyManagedInputs` currently exposes four env vars plus the shared `issue_ledger`.
- `RallyManagedOutputs` currently exposes one generic `issue_note`.
- `rally.issue_ledger.RallyIssueLedger` and `rally.issue_ledger.RallyIssueNoteAppend` are the stable runtime objects behind `home:issue.md` and the note append command.
- `rally.notes.RallyIssueNote` and `rally.turn_results.RallyTurnResult` are the shared authored contracts most producer roles use.
- Flow-local note outputs currently repeat the same append target in `shared/outputs.prompt` and add role-specific structures there.
- Short-form `final_output: OutputName` is already common in shipped flows.
  `poem_loop` and `software_engineering_demo` already use it for most agents, while `_stdlib_smoke` proves that local turn-result outputs can still target the shared JSON shape.
- Shared section order is not owned in one place today.
  `RallyManagedBaseAgent` defines the shared pieces, but each flow decides rendered order by the order it inherits `rally_contract`, `read_first`, and `how_to_take_a_turn`.
  `_stdlib_smoke` already diverges from `poem_loop` and `software_engineering_demo`.
- The skill packages mirror the same Rally rules again as separate emit targets, so the same shared story is maintained in two authored places today: stdlib prompt source and shared skill prompt source.

## 4.4 Observability + failure behavior today

- The problem is readback drift, not runtime misrouting.
  The current emitted `AGENTS.md` and `SKILL.md` surface is accurate, but it opens with framework-first prose, repeats binding and declaration headings, and uses long note and final-output shells.
- The emitted flows prove the drift in concrete ways today:
  - `flows/poem_loop/build/agents/poem_writer/AGENTS.md` and `flows/software_engineering_demo/build/agents/developer/AGENTS.md` still open with `## Rally Rules`, then `## Read First`
  - `flows/_stdlib_smoke/build/agents/plan_author/AGENTS.md` opens with `## Read First`, then `## Plan`, then `## Rally Rules`
  - `_stdlib_smoke` still shows the pure generic `### Issue Note` then `#### Issue Note` stack
  - producer flows still carry the long shared final-output shell with `#### What \`kind\` Means`
- The emitted shared skills prove the same first-screen problem:
  - `skills/rally-kernel/build/SKILL.md` still opens with package exposition and long guardrail lists before the simplest live move
  - `skills/rally-memory/build/SKILL.md` still opens with one positive line, one `Do not` line, and a package-exposition line instead of one clean action-first shared model
- Build and sync failures already fail loud through `RallyConfigError` in `flow_build.py`, `flow_loader.py`, and `bundled_assets.py`.
- Current proof surfaces already cover the change:
  - `tests/unit/test_flow_loader.py` asserts representative emitted `AGENTS.md` headings and final-output sections
  - `tests/unit/test_runner.py` asserts prompt text passed into live runs
  - `tests/unit/test_flow_build.py` guards flow and skill emit behavior
  - `tests/unit/test_bundled_assets.py` guards bundled-package sync
- Because runtime reads compiled artifacts, stale `flows/*/build/**`, `skills/*/build/**`, or `src/rally/_bundled/**` trees are the main way source truth can lag behind live truth.

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not applicable.
This is emitted Markdown surface work, not UI screen work.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Keep the same file layout and runtime ownership.
  This pass changes authored prompt source plus regenerated readback and bundled copies. It does not add new runtime modules.
- `stdlib/rally/prompts/rally/base_agent.prompt`, `memory.prompt`, `notes.prompt`, and `turn_results.prompt` stay the single source of truth for shared Rally wording and shared default contract shape.
- `skills/rally-kernel/prompts/SKILL.prompt` and `skills/rally-memory/prompts/SKILL.prompt` stay separate skill emit targets, but their first-screen copy aligns with the same action-first shared story.
- Flow entrypoints keep only flow-local role, grounding, and review content.
  They should stop carrying accidental shared-order drift.
- Flow-local note structures stay in `flows/*/prompts/shared/outputs.prompt`, but they should shrink to role-specific structure and any truly local note guidance.
- `flows/*/build/**`, `skills/*/build/**`, and `src/rally/_bundled/**` remain generated copies only.

## 5.2 Control paths (future)

- No runtime control path changes are allowed in this pass.
- `runner.py`, `flow_build.py`, `flow_loader.py`, `bundled_assets.py`, and `workspace_sync.py` stay behaviorally the same.
- The implementation path is source edit -> `doctrine.emit_docs` and `doctrine.emit_skill` rebuild -> bundled-asset sync -> test proof.
- The note append path stays `rally.issue_ledger.RallyIssueNoteAppend`.
- The turn-ending path stays one final JSON response through the declared final output.

## 5.3 Object model + abstractions (future)

- `RallyManagedBaseAgent` becomes the owner of the shared first-screen contract.
  The shared surface should render in one stable order:
  1. `Rally Context`
  2. `Read First`
  3. `Shared Rules`
- `RallyManagedBaseAgent` owns the shared content and names for those blocks, but current Doctrine still renders inherited blocks in the order each flow entrypoint pulls them in.
  That means order normalization is not a runtime or compiler task in this pass.
  It is an authored prompt task across `flows/_stdlib_smoke/prompts/AGENTS.prompt`, `flows/poem_loop/prompts/AGENTS.prompt`, and `flows/software_engineering_demo/prompts/AGENTS.prompt`.
  `_stdlib_smoke` must use the same order so the smallest regression flow checks the canonical shared layout.
- `RallyManagedInputs` owns the default shared input binding labels.
  The `issue_ledger` binding becomes a purpose-first label like `Shared Ledger File` so the renderer no longer shows `Issue Ledger` twice for the same input.
- `RallyManagedOutputs` owns the default generic note binding.
  The generic binding becomes a purpose-first label like `Saved Run Note` so generic flows no longer emit `Issue Note` and `Issue Note` as stacked headings.
- `rally.notes.RallyIssueNote` owns the shared note shell.
  It should collapse to the append command plus flat saved-context properties using current Doctrine features such as `properties` and `render_profile`.
  It should not emit titled meta sections like `Purpose`, `Run-Local Boundary`, or `Standalone Read`.
- Flow-local issue-note outputs in `flows/*/prompts/shared/outputs.prompt` should inherit the shared append-target contract from `rally.notes.RallyIssueNote` and add only role-specific structure plus any one-line local readback note they truly need.
- `rally.turn_results.RallyTurnResultJson` owns shared field guidance, schema, and example truth.
  Producer agents should keep using short-form `final_output: rally.turn_results.RallyTurnResult`.
  Block-form `final_output` stays reserved for review flows that truly need `review_fields`.
- `RallyReadFirst`, `RallyHowToTakeATurn`, `RallyKernel`, and `RallyMemory` all move to the same action-first writing style and shorter first-screen sections, but they keep the same CLI boundaries, examples, and runtime meaning.
- `_stdlib_smoke` is the canonical regression flow for the shared generic surface.
  `poem_loop` and `software_engineering_demo` then prove that the same shared cleanup still works with role-specific note structures and review-native finals.

## 5.4 Invariants and boundaries

- Keep one shared ledger at `home:issue.md`.
- Keep one final JSON control path.
- Keep `rally.issue_ledger.RallyIssueNoteAppend` as the note append target.
- Keep generated readback and bundled copies out of authored source ownership.
- Keep shared Rally wording in stdlib and shared skill prompt source, not in runtime code.
- Keep flow-local prompts focused on flow-local behavior.
- Do not add a Rally-only formatting shim or a Doctrine fork.
- Do not require new Doctrine language, compiler, or renderer support for this pass.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not applicable.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared AGENTS surface | `stdlib/rally/prompts/rally/base_agent.prompt` | `RallyManagedBaseAgent`, `RallyManagedInputs`, `RallyManagedOutputs` | shared first screen is accurate but opens with `Rally Rules`, repeats generic binding labels, and leaves section order partly flow-owned | rewrite the shared intro into `Rally Context`, keep `Read First`, shorten shared rules, and rename the shared ledger and generic note bindings to purpose-first labels | first-time agents need one pickup story and cleaner headings | same runtime ledger and note contract, cleaner emitted section order and binding labels | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Shared read-first and memory language | `stdlib/rally/prompts/rally/memory.prompt` | `RallyReadFirst`, `RallyHowToTakeATurn`, `RallyMemorySkill` | helpful shared guidance exists, but the first screen is still longer and more negative than needed | rewrite the shared workflows and memory skill intro in the same action-first style as the new base surface | keep the shared story consistent across AGENTS and shared skills | same memory scope and CLI behavior, smaller readback | `tests/unit/test_flow_loader.py`, emitted `skills/rally-memory/build/SKILL.md` |
| Shared note contract | `stdlib/rally/prompts/rally/notes.prompt` | `RallyIssueNote` | generic note readback emits titled meta sections instead of a compact saved-context shell | move to a compact note contract using shipped Doctrine features, with the append command plus flat saved-context fields only | remove authoring-note exposition from emitted readback | same append target and note meaning, flatter note contract | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Shared final JSON contract | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultJson`, `RallyTurnResult` | final-output readback is correct but over-explains `kind` in a long titled block | keep shared guidance on the JSON shape, example, and field notes; keep short-form final-output use as the default producer path | make the end-turn contract easier to scan without changing runtime meaning | same schema and final JSON shape | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Poem flow shared ordering | `flows/poem_loop/prompts/AGENTS.prompt` | `PoemLoopRole`, `PoemWriter`, `PoemCritic`, `PoemLoopInputs` | shared Rally blocks render in a cleaner order than smoke, but the order is still maintained manually in each agent body | keep one canonical shared inherit order and let the shared ledger binding label come from stdlib | stop flow-local order drift and duplicated binding naming | same flow behavior, cleaner emitted headings | `tests/unit/test_flow_loader.py` |
| Poem flow note output | `flows/poem_loop/prompts/shared/outputs.prompt` | `WriterIssueNote` | writer note repeats the shared append target and adds its own local standalone shell | reuse the shared stdlib append path and keep only the writer-specific structure plus any truly local one-line guidance | remove duplicate shared note shell text | same writer note path and structure, shared append path, less duplicated prose | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Demo flow shared ordering | `flows/software_engineering_demo/prompts/AGENTS.prompt` | `SoftwareEngineeringRole`, `Architect`, `Developer`, `QaDocsTester`, `Critic`, `SoftwareEngineeringDemoInputs` | shared Rally blocks render in one order today, but the order still lives in local inherit lists and can drift | standardize local inherit order and let shared binding labels come from stdlib | keep the multi-role demo on the same shared surface as other flows | same flow behavior, cleaner emitted headings | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Demo flow note outputs | `flows/software_engineering_demo/prompts/shared/outputs.prompt` | `ArchitectIssueNote`, `DeveloperIssueNote`, `QaIssueNote` | each note repeats the shared append target and local standalone shell | reuse the shared stdlib append path and keep only role-specific structures plus any truly local one-line guidance | remove duplicated shared note shell text from three role outputs | same note paths and role-specific structures, shared append path, less duplicated prose | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Smoke flow generic surface | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | `PlanAuthor`, `RouteRepair`, `Closeout` | smoke flow still renders the old shared order and the generic `Issue Note` / `Issue Note` stack | align inherit order with the canonical shared order and let the renamed generic note binding prove the generic fix | keep one small regression flow that shows the pure shared surface clearly | same smoke behavior, cleaner generic readback | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Shared skill packages | `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt` | package top matter, first-screen sections, workflow wording | skill docs still frontload package exposition and long guardrail lists | rewrite skill packages around the live move first, then the quick model, then use/avoid/workflow details | make shared skills match the new stdlib writing standard | same CLI contracts and examples, cleaner `SKILL.md` | emitted `skills/*/build/SKILL.md`, `tests/unit/test_bundled_assets.py` |
| Generated flow readback | `flows/_stdlib_smoke/build/**`, `flows/poem_loop/build/**`, `flows/software_engineering_demo/build/**` | compiled `AGENTS.md` and `AGENTS.contract.json` | generated readback still reflects the old shared wording and heading shape | regenerate all shipped flow builds after source edits | runtime reads compiled artifacts, not prompt source | same compiled contracts, updated Markdown readback | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Generated skill readback | `skills/rally-kernel/build/**`, `skills/rally-memory/build/**` | emitted `SKILL.md` and references | build output still reflects the old first-screen shared story | regenerate both shared skill builds after source edits | packaged and live workspace skills must match the new source truth | same skill package behavior, updated Markdown readback | `tests/unit/test_bundled_assets.py` |
| Packaged built-ins | `src/rally/_bundled/stdlib/rally/**`, `src/rally/_bundled/skills/rally-kernel/**`, `src/rally/_bundled/skills/rally-memory/**` | bundled copies | packaged assets drift until bundle sync runs | sync bundled assets after the source and build output land | external workspaces consume bundled copies | same packaged assets, updated bundled truth | `tests/unit/test_bundled_assets.py` |
| Live docs | `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_PORTING_GUIDE.md` | prompt-surface and shared-contract descriptions | docs can drift if they still quote or describe the old shared surface | update only the surviving doc lines that describe shared prompt readback or shared skill shape | keep design docs aligned with shipped truth | same docs role, updated shared-surface truth | doc inspection after rebuild |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - shared AGENTS wording and default generic bindings: `stdlib/rally/prompts/rally/base_agent.prompt`
  - shared read-first, turn, and memory wording: `stdlib/rally/prompts/rally/memory.prompt`
  - shared generic note shell: `stdlib/rally/prompts/rally/notes.prompt`
  - shared final JSON wording: `stdlib/rally/prompts/rally/turn_results.prompt`
  - role-specific note structure: `flows/*/prompts/shared/outputs.prompt`
  - shared skill first-screen wording: `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt`
- Deprecated APIs (if any):
  - none
- Delete list (what must be removed):
  - titled meta sections such as `Purpose`, `Run-Local Boundary`, and generic `Standalone Read` blocks when the same truth can live in a flatter shared note contract
  - the long titled `What \`kind\` Means` shell once its guidance is moved onto the JSON shape in a compact form
- any flow-local duplicated shared note shell text left behind after the shared note cleanup lands
- Capability-replacing harnesses to delete or justify:
  - none
  - this is prompt-source cleanup inside current Doctrine support, not a tooling project
- Live docs/comments/instructions to update or delete:
  - `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, and `docs/RALLY_PORTING_GUIDE.md` when they describe the shared emitted surface
  - bundled copies under `src/rally/_bundled/**` after source edits land
- Explicit non-change surfaces for this pass:
  - `src/rally/services/runner.py`, `src/rally/services/flow_build.py`, `src/rally/services/flow_loader.py`, `src/rally/services/bundled_assets.py`, and `src/rally/services/workspace_sync.py`
  - these files define the rebuild, load, and sync proof path, but the target architecture does not require runtime behavior changes there
- Behavior-preservation signals for refactors:
  - rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
  - rebuild `rally-kernel` and `rally-memory`
  - inspect representative emitted `AGENTS.md` and `SKILL.md`
  - run `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py`, `tests/unit/test_flow_build.py`, and `tests/unit/test_bundled_assets.py`

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Shared generic flow | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | canonical shared block order plus renamed generic note binding | smallest shipped flow should prove the pure shared surface without extra local noise | include |
| Producer + review flow | `flows/poem_loop/prompts/AGENTS.prompt`, `flows/poem_loop/prompts/shared/outputs.prompt` | canonical shared block order plus shared note cleanup through the stdlib append path | proves the cleanup still works with one local note structure and one review-native final | include |
| Multi-role review flow | `flows/software_engineering_demo/prompts/AGENTS.prompt`, `flows/software_engineering_demo/prompts/shared/outputs.prompt` | canonical shared block order plus shared note cleanup through the stdlib append path | prevents shared wording drift across the heaviest shipped flow | include |
| Shared skill packages | `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt` | action-first first screen and smaller shared guardrail copy | keeps AGENTS and SKILL readback from teaching two different shared Rally stories | include |
| Packaged copies | `src/rally/_bundled/**` | sync the same built truth after source edits | external workspaces must not keep the old shared surface | include |
| Runtime services | `src/rally/services/*.py` rebuild, load, and sync code | runtime behavior change | the architecture proof path already exists; widening into runtime edits would be scope creep unless source cleanup uncovers a real build bug | exclude |
| Broader public docs | `README.md` and unrelated docs | quote the new emitted readback directly | avoid widening this pass into general docs cleanup when the file does not actually describe the shared prompt surface | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; split Section 7 into the smallest reasonable sequence of coherent self-contained units that can be completed, verified, and built on later. If two decompositions are both valid, bias toward more phases than fewer. `Work` explains the unit; `Checklist (must all be done)` is the authoritative must-do list inside the phase; `Exit criteria (all required)` names the concrete done conditions. Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns or sharp edges only at the canonical boundary when a short comment would prevent future drift.

## Phase 1 — Shared AGENTS base and shared labels

* Goal:
  Put one clean shared Rally story and one set of shared binding names in stdlib.
* Work:
  Update the Rally-owned AGENTS surfaces in `stdlib/rally/prompts/rally/base_agent.prompt`, `memory.prompt`, and any shared input label source they depend on so the shared content, shared input label, and shared generic note label all match the target readback.
* Status: COMPLETE
* Completed work:
  - Rewrote the shared AGENTS surface so emitted flow readback now opens with `Rally Context`, then `Read First`, then `Shared Rules`.
  - Renamed the shared ledger input binding to `Shared Ledger File`.
  - Renamed the shared generic note binding to `Saved Run Note`.
  - Kept the shared ledger path, note append path, env var meaning, and final JSON meaning unchanged.
* Checklist (must all be done):
  - Rewrite the shared Rally intro so the first shared block is `Rally Context` with one short action-first pickup line.
  - Keep the shared read-first and turn-flow wording short, positive, and accurate about `home:issue.md`, notes, memory, and final JSON.
  - Rename the shared ledger input binding to a purpose-first label such as `Shared Ledger File`.
  - Rename the generic shared note binding to a purpose-first label such as `Saved Run Note`.
  - Keep the ledger path, note append path, env var meanings, and final JSON meaning unchanged.
* Verification (required proof):
  Rebuild `_stdlib_smoke` and inspect `flows/_stdlib_smoke/build/agents/plan_author/AGENTS.md` to confirm the new shared intro and renamed generic bindings render at all.
* Docs/comments (propagation; only if needed):
  None in this phase unless a touched live doc literally quotes the old shared binding names.
* Exit criteria (all required):
  - Stdlib source owns the new shared AGENTS wording and shared binding labels.
  - No runtime-owned meaning changed.
  - `_stdlib_smoke` readback proves the new shared words and labels compile.
* Rollback:
  Revert only the stdlib AGENTS-surface prompt edits.

## Phase 2 — Flow entrypoint order normalization

* Goal:
  Make all shipped flows render the same shared first-screen order under current Doctrine.
* Work:
  Normalize the inherit order in `flows/_stdlib_smoke/prompts/AGENTS.prompt`, `flows/poem_loop/prompts/AGENTS.prompt`, and `flows/software_engineering_demo/prompts/AGENTS.prompt` so the shared block order is `Rally Context`, then `Read First`, then `Shared Rules`.
* Status: COMPLETE
* Completed work:
  - Normalized `_stdlib_smoke` to inherit `rally_contract`, then `read_first`, then `how_to_take_a_turn`.
  - Kept `poem_loop` and `software_engineering_demo` on that same shared first-screen order.
  - Verified the representative emitted agents from all three shipped flows now render the same shared first-screen order.
* Checklist (must all be done):
  - Update `_stdlib_smoke` so it no longer opens with `Read First` before the shared Rally block.
  - Keep `poem_loop` and `software_engineering_demo` on the same shared order as `_stdlib_smoke`.
  - Leave flow-local role, grounding, review, and artifact sections in place after the shared blocks.
  - Do not widen this phase into runtime service edits or unrelated flow rewrites.
* Verification (required proof):
  Rebuild `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`, then inspect one representative agent readback from each flow to confirm the same shared first-screen order.
* Docs/comments (propagation; only if needed):
  None in this phase.
* Exit criteria (all required):
  - All shipped flows render the same shared first-screen order.
  - No flow loses local role or review content while order is normalized.
* Rollback:
  Revert only the flow entrypoint order changes.

## Phase 3 — Shared generic note and final JSON shells

* Goal:
  Flatten the shared generic note and shared producer final-output shells as far as current Doctrine support allows.
* Work:
  Update `stdlib/rally/prompts/rally/notes.prompt` and `stdlib/rally/prompts/rally/turn_results.prompt` to use the compact current-language patterns already approved in Section 0.4.
* Status: COMPLETE
* Completed work:
  - Replaced the old generic note meta sections with one compact shared note shell that keeps the append command visible and moves the note guidance into flat saved-context properties.
  - Replaced the long `What \`kind\` Means` shell with compact `Field Notes` on the shared JSON shape.
  - Kept the shared note target, schema file, example file, and final JSON semantics unchanged.
* Checklist (must all be done):
  - Replace the generic note meta sections with one compact shared note shell that keeps the append command visible and removes authoring-only exposition.
  - Keep the generic note on `rally.issue_ledger.RallyIssueNoteAppend`.
  - Move the shared final JSON guidance onto the JSON shape in the approved compact form.
  - Keep producer roles on short-form `final_output: rally.turn_results.RallyTurnResult`.
  - Keep the same schema file, example file, and `kind` semantics.
* Verification (required proof):
  Rebuild `_stdlib_smoke` and inspect its generic note section plus its producer final-output section to confirm the old titled shells are gone or reduced as far as the current compiler allows.
* Docs/comments (propagation; only if needed):
  None in this phase.
* Exit criteria (all required):
  - The generic note section no longer emits the old `Purpose`, `Run-Local Boundary`, or generic `Standalone Read` shell.
  - The shared producer final-output section keeps the same contract but uses the smaller approved guidance form.
* Rollback:
  Revert only the shared note and shared final-output prompt edits.

## Phase 4 — Flow-local shared note cleanup and remaining local cleanup

* Goal:
  Make flow-local note outputs carry only local structure and the shared stdlib append path instead of re-explaining the shared note shell.
* Work:
  Update `flows/poem_loop/prompts/shared/outputs.prompt` and `flows/software_engineering_demo/prompts/shared/outputs.prompt` to reuse the shared stdlib append path and keep only role-specific structure plus any truly local one-line note guidance.
* Status: COMPLETE
* Completed work:
  - Removed the local `Standalone Read` note shells from `poem_loop` and `software_engineering_demo`.
  - Replaced the copied local `append_with` literals with addressable refs to `rally.notes.RallyIssueNote:target.append_with`, so the shared append command now stays rooted in stdlib source.
  - Kept the role-specific note structures local and left producer and review-native final outputs unchanged.
* Checklist (must all be done):
  - Point `WriterIssueNote` at the shared stdlib append path and keep only writer-specific fields and any truly local note guidance.
  - Point `ArchitectIssueNote`, `DeveloperIssueNote`, and `QaIssueNote` at the shared stdlib append path and keep only role-specific fields and any truly local note guidance.
  - Keep review-native finals unchanged where they already use the right review output.
  - Confirm no producer flow regresses away from short-form final output while this cleanup lands.
* Verification (required proof):
  Rebuild `poem_loop` and `software_engineering_demo`, then inspect representative note sections and producer final-output sections to confirm the shared shell is no longer duplicated locally.
* Docs/comments (propagation; only if needed):
  None in this phase unless a touched flow doc literally quotes one of the old local note shells.
* Exit criteria (all required):
  - Flow-local note outputs add local structure only.
  - No shipped flow still repeats the generic shared note shell in local prompt source.
  - Producer and review-native final outputs still match their current runtime contracts.
* Rollback:
  Revert only the flow-local shared note cleanup changes.

## Phase 5 — Shared skill package rewrite

* Goal:
  Make the shared skill packages teach the same smaller, action-first Rally story as the AGENTS surface.
* Work:
  Update `skills/rally-kernel/prompts/SKILL.prompt` and `skills/rally-memory/prompts/SKILL.prompt` so each skill opens with the live move first and keeps the quick model, workflow, and examples without extra package exposition.
* Status: COMPLETE
* Completed work:
  - Rewrote `rally-kernel` so it opens with the live move, then a quick model, then the note and final-JSON workflow.
  - Rewrote `rally-memory` so it opens with the live memory move and keeps notes and final JSON clearly out of memory scope.
  - Kept the existing CLI examples and runtime boundaries intact.
* Checklist (must all be done):
  - Rewrite `rally-kernel` so it leads with when to use the skill, then the quick model, then the note and final-JSON workflow.
  - Rewrite `rally-memory` so it leads with the live memory move and keeps notes or final JSON clearly out of memory scope.
  - Keep the existing CLI examples and references unless one is no longer needed after the copy cleanup.
  - Keep the same runtime boundaries around notes, memory, and final JSON.
* Verification (required proof):
  Rebuild `rally-kernel` and `rally-memory`, then inspect `skills/rally-kernel/build/SKILL.md` and `skills/rally-memory/build/SKILL.md`.
* Docs/comments (propagation; only if needed):
  None in this phase.
* Exit criteria (all required):
  - Both shared skills open with the live move first.
  - Both emitted `SKILL.md` files match the smaller shared writing standard.
  - No CLI contract or runtime boundary drifted.
* Rollback:
  Revert only the shared skill prompt edits.

## Phase 6 — Rebuild, bundled sync, docs sync, and proof

* Goal:
  Make source, generated readback, bundled copies, tests, and surviving docs agree on one shipped truth.
* Work:
  Rebuild all touched flow and skill output, sync bundled assets, update wording assertions that still encode the old readback, update the surviving design docs that still describe the old shared surface, and run the agreed proof path.
* Status: COMPLETE
* Completed work:
  - Rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`.
  - Rebuilt `rally-kernel` and `rally-memory`.
  - Synced bundled built-ins under `src/rally/_bundled/**`.
  - Updated wording assertions in `tests/unit/test_flow_loader.py` and `tests/unit/test_runner.py`.
  - Searched `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, and `docs/RALLY_PORTING_GUIDE.md` for old shared-surface wording and found no surviving live-doc lines that required edits in this pass.
  - Ran the targeted proof stack and the full Rally unit suite clean.
  - Re-ran the final rebuild, bundled sync, representative readback inspection, and proof after the Phase 4 flow-local note cleanup landed.
* Checklist (must all be done):
  - Run `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`.
  - Run `uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory`.
  - Run `uv run python tools/sync_bundled_assets.py`.
  - Update wording assertions in `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py`, and any other unit test that still expects the old shared readback.
  - Update only the surviving live doc lines in `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, and `docs/RALLY_PORTING_GUIDE.md` when they still describe the old shared surface.
  - Inspect representative generated Markdown under `flows/*/build/**`, `skills/*/build/**`, and `src/rally/_bundled/**`.
  - Run `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_bundled_assets.py -q`.
  - Run `uv run pytest tests/unit -q`.
* Verification (required proof):
  The rebuild commands succeed, bundled sync succeeds, representative emitted Markdown matches the target shape, the targeted unit proof passes, and the full Rally unit suite passes.
* Docs/comments (propagation; only if needed):
  Update only the surviving live docs that still describe the old shared emitted surface. Delete or rewrite stale lines in the same pass instead of leaving both stories alive.
* Exit criteria (all required):
  - Generated flow output, generated skill output, and bundled copies all match the new source truth.
  - The targeted proof and full Rally unit suite both pass.
  - Surviving docs that still describe the shared prompt surface match the new emitted truth.
* Rollback:
  Revert generated output, bundled copies, tests, and doc sync together with the source edits that caused drift.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

Prefer existing Rally readback assertions. Update them to prove the new emitted structure instead of preserving the old noisy headings, especially in `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py`, `tests/unit/test_flow_build.py`, and `tests/unit/test_bundled_assets.py`.

## 8.2 Integration tests (flows)

Rebuild Rally's shipped flows and shared skills, then inspect emitted `AGENTS.md`, `AGENTS.contract.json`, `SKILL.md`, and bundled copies under `src/rally/_bundled/**`.

## 8.3 E2E / device tests (realistic)

Not applicable. This work changes emitted prompt and skill readback, not device or UI behavior.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Hard cutover. The new emitted prompt surface becomes the only shipped shape once Rally checks are green.

## 9.2 Telemetry changes

None expected. This plan should not add runtime telemetry.

## 9.3 Operational runbook

Rebuild Rally flow output, rebuild shared skills, sync bundled assets, update surviving docs and tests that still describe the old surface, run Rally checks, inspect the emitted Markdown, and then commit Rally in one aligned pass.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: cold-read pass A, cold-read pass B, self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, `# 0)` through `# 10)`, `planning_passes`, and the owned helper blocks
  - outcome, requested behavior scope, allowed convergence scope, canonical owner paths, required deletes, phase order, verification burden, and rollout truth
- Findings summary:
  - TL;DR plan shape lagged behind the sharper Section 7 phase split
  - Section 8 and Section 9 under-described the shared-skill and bundled proof that Section 7 already required
- Integrated repairs:
  - aligned TL;DR plan with the owner-layer phase split
  - aligned Section 8 and Section 9 with the actual rebuild, bundled-sync, doc-sync, and proof path
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

## 2026-04-15 - Keep this pass inside shipped Doctrine support

### Context

The first draft assumed Rally should change Doctrine when the current renderer blocked the ideal north star. After the Doctrine research pass, the user narrowed the scope: unsupported Doctrine features are out of scope, and the plan should do the best possible work inside the language Doctrine ships today.

### Options

1. Keep the earlier cross-repo plan and change Doctrine too.
2. Limit the plan to Rally prompt authoring and shipped Doctrine features only.
3. Pause until Doctrine ships cleaner ordinary-output and structured-schema support.

### Decision

Use option 2.

### Consequences

- the north-star examples must stay honest about current Doctrine wrapper sections and contract tables
- grouped ordinary contract rendering and Doctrine-authored structured schemas are out of scope
- the implementation and verification surface stays in Rally

### Follow-ups

- confirm that the Section 0.4 targets are the right best-possible current-language shapes
- use the deep-dive pass to map which shared bindings and flow-local prompts still need reshaping inside Rally

## 2026-04-15 - North Star approved for full planning

### Context

The plan started in `draft` while the North Star was still being shaped. The user then explicitly asked to ramp back up on this plan and run `$arch-step auto-plan`, which is the approval needed to move past the North Star gate and continue the planning arc on this same artifact.

### Options

1. Keep the doc in `draft` and block `auto-plan`.
2. Mark the doc `active` and let the planning controller continue from this artifact.

### Decision

Use option 2.

### Consequences

- this doc is now the approved planning source of truth for the stdlib prompt surface refresh
- later planning stages should refine the existing research and architecture sections instead of creating a second plan

### Follow-ups

- run the `auto-plan` parent pass against this doc
- let the installed Stop hook continue from the first incomplete planning stage after the parent pass arms controller state

## 2026-04-15 - Keep shared order and generic note shell in stdlib

### Context

Deep-dive pass 1 showed two real sources of drift:

- shared section order changes by flow because each flow chooses its own inherit order for `rally_contract`, `read_first`, and `how_to_take_a_turn`
- flow-local note outputs repeat the shared note append target and shared shell text instead of inheriting one shared contract

### Options

1. Leave shared order and note shell partly flow-owned.
2. Move the shared first-screen order and the generic note shell back to stdlib, then let flows add only local structure where needed.

### Decision

Use option 2.

### Consequences

- `RallyManagedBaseAgent`, `RallyManagedInputs`, `RallyManagedOutputs`, and `rally.notes.RallyIssueNote` become the main owners of shared content, shared labels, and the generic shared note shell
- flow entrypoints still need one canonical inherit order because current Doctrine renders inherited blocks in local order
- flow-local note outputs only add role-specific structure and any truly local one-line guidance

### Follow-ups

- use `phase-plan` to turn the source-only cleanup into explicit implementation units
- keep Section 7 focused on source edits, rebuild, bundle sync, and readback proof instead of runtime changes

## 2026-04-15 - Split execution by owner layer, then prove once

### Context

The first phase outline was directionally right, but it still mixed together distinct owner layers:

- shared stdlib wording and labels
- flow entrypoint order normalization
- shared generic note and final-output shell cleanup
- flow-local note inheritance
- shared skill package cleanup
- final rebuild, bundle sync, docs sync, and proof

Deep-dive pass 2 showed that keeping those layers separate removes ambiguity and keeps runtime-service changes out of scope.

### Options

1. Keep the older four coarse phases.
2. Split execution into smaller owner-layer phases, then end with one rebuild and proof phase.

### Decision

Use option 2.

### Consequences

- implementation can move one owned layer at a time without mixing prompt-source cleanup with build or runtime questions
- rebuild and proof stay concentrated in one final alignment phase
- `implement` and later audit work can judge completeness against one sharper checklist

### Follow-ups

- run `consistency-pass` after this phase plan to confirm the artifact is ready for `implement-loop`

## 2026-04-15 - Keep Phase 4 blocked on the installed Doctrine parser gap

### Context

The approved plan expected flow-local issue-note outputs to inherit the shared note contract so Rally could stop repeating the same append target and shared note shell in multiple flow-local prompt files. In the real Rally build environment, `uv run python -m doctrine.emit_docs` uses the installed `.venv` package `doctrine-agents` `1.0.2`, not the newer local Doctrine docs tree. That compiler rejects imported ordinary-output inheritance in Rally's prompt graph with `E101 parse error` at `flows/poem_loop/prompts/shared/outputs.prompt:41` on `output WriterIssueNote[rally.notes.RallyIssueNote]`.

### Decision

Do not fake Phase 4 by copying the shared note contract again in Rally-owned prompt source. Leave Phase 4 blocked on the missing Doctrine parser support for imported ordinary-output inheritance, keep the landed shared-surface cleanup that does compile and test cleanly, and let fresh audit reopen only that missing code front.

## 2026-04-15 - Use shared addressable refs to finish Phase 4 under Doctrine 1.0.2

### Context

Fresh audit reopened Phase 4 because the flow-local note outputs still copied the shared append command and still emitted local `Standalone Read` shells. The installed Rally build compiler remained `doctrine-agents` `1.0.2`, so imported ordinary-output inheritance still was not the live path. A second pass found a shipped current-language alternative that compiles on this build: local outputs can keep their own local structures, drop the local `Standalone Read` shell, and point `append_with` at `rally.notes.RallyIssueNote:target.append_with`.

### Decision

Use the shared addressable-ref path for the append command and remove the local `Standalone Read` shell. That keeps the shared append command rooted in stdlib source, keeps flow-local outputs focused on local structure, and stays inside the installed Doctrine feature set instead of inventing a Rally workaround.
