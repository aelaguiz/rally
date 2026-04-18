# Worklog

Plan doc: docs/RALLY_DOCTRINE_AUTHORING_ELEGANCE_AUDIT_2026-04-16.md

## Initial entry
- Run started.
- Current phase: Phase 1 — Rewrite Rally stdlib anchors and add shared pattern comments.

## Phase 1
- Rewrote the Rally stdlib pass-through wrappers in
  `stdlib/rally/prompts/rally/base_agent.prompt` to one-line refs where the
  wrapper only forwards one declaration.
- Kept `RallyManagedOutputs` explicit and added a source comment that explains
  why `Saved Run Note` still keeps the longer form.
- Rewrote `RallyTurnResultSchema` in
  `stdlib/rally/prompts/rally/turn_results.prompt` to grouped inherit.
- Kept the conditional grouped-inherit sites around `override` explicit and
  documented why that order still reads better.
- Proof:
  - `uv sync --dev`
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
  - inspected generated `AGENTS.md` readback for shared headings like
    `Saved Run Note` and `Turn Result`

## Phase 2
- Rewrote the shared review carriers in:
  - `flows/software_engineering_demo/prompts/shared/review.prompt`
  - `flows/poem_loop/prompts/shared/review.prompt`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- Grouped the review-schema and final-response inherited tails.
- Switched identity review binds to bare names and added comments that explain
  when identity shorthand is safe versus when explicit semantic-path binds must
  stay.
- Kept the review JSON wrapper declarations explicit where the schema override
  is the main thing readers need to notice.
- Proof:
  - rebuilt all three flow targets
  - inspected reviewer `AGENTS.md`
  - inspected reviewer `final_output.contract.json`

## Phase 3
- Rewrote the main flow entry prompts and helper imports in:
  - `flows/software_engineering_demo/prompts/AGENTS.prompt`
  - `flows/software_engineering_demo/prompts/shared/skills.prompt`
  - `flows/software_engineering_demo/prompts/shared/outputs.prompt`
  - `flows/poem_loop/prompts/AGENTS.prompt`
  - `flows/poem_loop/prompts/shared/inputs.prompt`
  - `flows/poem_loop/prompts/shared/outputs.prompt`
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
- Applied alias imports, symbol imports, grouped inherit, one-line wrapper refs,
  and identity `fields` shorthand where Rally kept the same meaning.
- Added example-level comments that show the safe shorthand patterns without
  copying the stdlib comments word for word.

## Phase 4
- Closed the conditional sweep instead of stopping at the easy wins.
- Added explicit keep comments for:
  - `Saved Run Note`
  - `Turn Result`
  - reviewer output wrappers that carry two direct outputs
- Preserved the audit no-hit story for `self:` and `review override fields`
  because this pass still found no clean Rally call site for either feature.

## Phase 5
- Final proof command:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo`
- Readback spot checks:
  - `flows/software_engineering_demo/build/agents/architect/AGENTS.md`
  - `flows/software_engineering_demo/build/agents/architect_reviewer/AGENTS.md`
  - `flows/poem_loop/build/agents/muse/AGENTS.md`
  - `flows/poem_loop/build/agents/poem_writer/AGENTS.md`
  - `flows/_stdlib_smoke/build/agents/plan_author/AGENTS.md`
  - `flows/_stdlib_smoke/build/agents/route_repair/AGENTS.md`
- Review metadata spot checks:
  - `flows/software_engineering_demo/build/agents/architect_reviewer/final_output.contract.json`
  - `flows/poem_loop/build/agents/poem_critic/final_output.contract.json`
  - `flows/_stdlib_smoke/build/agents/repair_plan_reviewer/final_output.contract.json`
- Result:
  - all three rebuild targets emitted cleanly
  - generated headings still carry the intended titled sections
  - reviewer carrier fields and `review_fields` still resolve to the same
    underlying paths after the shorthand cleanup
