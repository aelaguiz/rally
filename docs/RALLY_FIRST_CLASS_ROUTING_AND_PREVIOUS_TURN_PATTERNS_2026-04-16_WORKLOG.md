---
title: "Rally - First-Class Routing And Previous-Turn Patterns - Worklog"
date: 2026-04-16
doc_path: docs/RALLY_FIRST_CLASS_ROUTING_AND_PREVIOUS_TURN_PATTERNS_2026-04-16.md
status: active
---

# Worklog

## 2026-04-16

- Armed `.codex/implement-loop-state.019d9680-edca-7863-a42b-9ebc3cfaaaea.json`
  for the active doc and session.
- Re-read the approved plan, Section 5 target architecture, Section 6
  call-site audit, and Section 7 phase obligations before code edits.
- Preflighted the controller runtime:
  - `~/.codex/hooks.json` is present and points at the installed
    `arch_controller_stop_hook.py` runner through `python3 <path>`.
  - `codex features list` shows `codex_hooks` enabled.
  - the installed runner exists and supports session-scoped controller state.
- Started Phase 1 implementation.
- Completed Phase 1 producer route-first cutover in Rally runtime, shared
  producer prompt source, and the shipped `poem_loop`,
  `software_engineering_demo`, and `_stdlib_smoke` producer outputs.
- Completed Phase 2 previous-turn runtime support:
  - added typed emitted `io` contracts to `src/rally/domain/flow.py`
  - loaded `io.previous_turn_inputs`, `io.outputs`, and
    `io.output_bindings` in `src/rally/services/flow_loader.py`
  - added Rally-owned `RallyPreviousTurnOutput` source comments in
    `stdlib/rally/prompts/rally/base_agent.prompt`
  - added `src/rally/services/previous_turn_inputs.py` as the one previous-turn
    resolver and appendix renderer
  - saved `previous_turn_inputs.md` under the current turn in
    `src/rally/adapters/base.py`
  - appended and saved the exact previous-turn appendix in
    `src/rally/services/runner.py`
- Added focused Phase 2 tests:
  - loader coverage for emitted `io`
  - resolver coverage for `default_final_output`, `output_decl`, and
    `output_binding`
  - fail-loud coverage for missing metadata, unreadable artifacts,
    contract-mode mismatches, and note-backed reopen
  - runner coverage for saved `previous_turn_inputs.md`
- Phase 2 proof passed:
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py -q`
    -> `112 passed`
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py tests/unit/test_issue_ledger.py tests/unit/test_cli.py -q`
    -> `176 passed`
  - rebuilt `poem_loop`, `software_engineering_demo`, and `_stdlib_smoke`
    after the shared prompt change
- Attempted Phase 3 `_stdlib_smoke` previous-turn proof and stopped on a
  Doctrine compiler bug instead of adding a Rally workaround.
  Repro:
  - add `RallyPreviousTurnOutput` to `_stdlib_smoke` `RouteRepair`
  - rebuild `_stdlib_smoke`
  - Doctrine crashes in
    `emit_docs._build_previous_turn_contexts() ->
    _compiler/flow.py:_collect_flow_from_workflow_body()`
  - current failure point is `../doctrine/doctrine/_compiler/flow.py:335`
    where the collector assumes every non-section and non-skill workflow item
    has `target_unit` plus `workflow_decl`
  - ordinary readable workflow steps do not, so previous-turn predecessor
    extraction crashes before emit finishes
- Doctrine feature request to consider:
  - fix previous-turn predecessor extraction so flow-graph collection skips or
    safely handles readable workflow items while building emit-time flow facts
    for `RallyPreviousTurnOutput`
  - keep the owner in Doctrine compiler flow extraction, not a Rally prompt or
    runtime workaround
- Fresh child audit confirmed the remaining approved frontier is still Phase 3
  through Phase 5 and did not reopen Phase 1 or Phase 2.
- Re-checked the audit evidence anchors:
  - `_stdlib_smoke` still emits `io.previous_turn_inputs: []`
  - `poem_loop` still has no `Muse` role and `PoemWriter` still emits
    `io.previous_turn_inputs: []`
  - the required live docs still teach producer `next_owner` and
    `AGENTS.md`-only prompt injection
- Reproduced the Phase 3 blocker again without editing Rally or Doctrine:
  - built a temporary `_stdlib_smoke`-shaped prompt package
  - added the planned `PreviousPlanAuthorTurn` input to `RouteRepair`
  - loaded Rally stdlib through Doctrine provided prompt roots
  - Doctrine emit failed with:
    - `AttributeError: 'ReadableBlock' object has no attribute 'target_unit'`
- This confirms the earliest incomplete phase is still blocked in Doctrine
  emit for the current `_stdlib_smoke` previous-turn proof shape.
- Stopped again at Phase 3:
  - user direction in this thread says Rally should stop and surface Doctrine
    gaps instead of adding Rally-local glue
  - Rally repo rules also forbid editing `../doctrine` in a Rally turn unless
    the user clearly asks for Doctrine changes here
  - later approved phases remain unshipped, but they are not reachable in the
    ordered implementation frontier while Phase 3 is still blocked
- Fresh authoritative audit still leaves the same ordered frontier:
  - Phase 3 `_stdlib_smoke` previous-turn JSON proof
  - Phase 4 `poem_loop` `Muse` loop proof
  - Phase 5 live-doc/readback convergence
- Re-read the fresh audit block and current repo evidence before taking any new
  code action:
  - no earlier phase was reopened
  - the earliest incomplete phase is still the `_stdlib_smoke` Doctrine emit
    blocker
  - the later phases remain approved but unreachable in order while that
    blocker stands
- No new Rally code change was reachable in this pass without either:
  - editing `../doctrine`, which this Rally turn is not allowed to do
  - or adding a Rally workaround, which the user and plan both forbid
- Stopped again with the same Doctrine-first conclusion instead of widening
  Rally beyond the approved owner path.
- User asked for a fresh Doctrine recheck before re-arming the loop.
- Rechecked the local Doctrine workspace without editing it:
  - `git -C /Users/aelaguiz/workspace/doctrine status --short` shows a dirty
    local checkout with parser, grammar, compiler, and test changes
  - rebuilding `poem_loop` now fails in
    `../doctrine/doctrine/_compiler/indexing.py:651` with
    `Unsupported declaration type: Tree`
  - rebuilding `_stdlib_smoke` now fails the same way
  - `CompilationSession(parse_file(...))` still works for import-free Doctrine
    examples such as `examples/07_handoffs/prompts/AGENTS.prompt`
  - `CompilationSession(parse_file(...))` fails the same way for imported
    prompts such as `examples/04_inheritance/prompts/AGENTS.prompt`
- This means the old previous-turn blocker is no longer the current frontier.
  The local Doctrine checkout now has a broader import/index regression that
  blocks Rally rebuilds before Phase 3 and Phase 4 proof can run.
- Disarmed `.codex/implement-loop-state.019d9680-edca-7863-a42b-9ebc3cfaaaea.json`
  again because the user asked to re-arm only if the Doctrine fix was real,
  and the current local framework state is still blocked.
- User asked to try again after more local Doctrine work.
- Rechecked the local framework state:
  - `_stdlib_smoke` now rebuilds cleanly again
  - import-heavy Doctrine examples now compile again
  - `poem_loop` no longer fails on the old import/index regression
- Tried the planned `Muse` reject-loop shape in Rally source first:
  - added `Muse`
  - made `Muse` the start agent
  - tried both zero-config and explicit previous-turn review input forms for
    `PreviousPoemReview`
- Current local Doctrine still blocks that shape:
  - zero-config `PreviousPoemReview` fails with no reachable predecessor final
    output
  - explicit `output: shared.review.PoemReviewFinalResponse` fails with no
    reachable predecessor agent
  - both failures happen while compiling `Muse`, which means Doctrine previous-
    turn predecessor analysis still does not model the `PoemCritic` review
    reject route into `Muse`
- Reverted the unshipped `poem_loop` `Muse` edits so Rally does not keep a
  broken half-state that blocks normal rebuilds and test setup.
- Restored the shipped Phase 1 route-first producer shape on `poem_loop` and
  rebuilt the working flows:
  - `rebuilt _stdlib_smoke`
  - `rebuilt poem_loop`
- Confirmed Phase 3 is now truly landed:
  - `flows/_stdlib_smoke/build/agents/route_repair/final_output.contract.json`
    now carries `io.previous_turn_inputs[0] = PreviousPlanAuthorTurn`
  - focused runner proof for the exact injected JSON still passes
- Current credible proof passed:
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py -q`
    -> `137 passed`
- Updated the authoritative audit block:
  - Phase 3 is now complete
  - remaining frontier is Phase 4 and Phase 5
  - Phase 4 is blocked on a Doctrine feature gap in review-route predecessor
    analysis, not on Rally runtime work
- User asked to try again after the new local Doctrine review-route fix.
- Rechecked the new Doctrine bug note and focused owner paths:
  - `docs/bugs/previous-turn-review-route-predecessor-gap.md` is now marked
    resolved
  - Doctrine now carries the new review-route flow extraction and emit tests
- Re-landed the planned `poem_loop` `Muse` loop in Rally:
  - `flow.yaml` now starts at `00_muse`
  - `Muse` routes to `PoemWriter` through `final_output.route`
  - `PoemWriter` reads `PreviousMuseTurn`
  - `Muse` reads `PreviousPoemReview` through explicit
    `shared.review.PoemReviewFinalResponse`
  - `PoemCritic` reject paths now route back to `Muse`
- Rebuilt `poem_loop` and inspected the emitted contracts:
  - `muse/final_output.contract.json` now carries
    `io.previous_turn_inputs[0] = PreviousPoemReview`
  - `poem_writer/final_output.contract.json` now carries
    `io.previous_turn_inputs[0] = PreviousMuseTurn`
  - `poem_critic/final_output.contract.json` now advertises the reject route to
    `Muse`
- Updated focused loader and runner tests for the shipped `Muse -> Writer ->
  Critic` and `Critic -> Muse -> Writer` paths, including previous-turn
  appendix artifacts for the dependent turns.
- Phase 4 required proof passed:
  - rebuild: `poem_loop`
  - `uv run pytest tests/unit/test_runner.py tests/unit/test_flow_loader.py tests/unit/test_flow_build.py -q`
    -> `115 passed`
- Updated the authoritative audit block again:
  - Phase 4 is now complete
  - remaining ordered frontier is Phase 5 docs convergence
- Updated the six live docs named by the plan:
  - `docs/RALLY_MASTER_DESIGN.md`
  - `docs/RALLY_RUNTIME.md`
  - `docs/RALLY_COMMUNICATION_MODEL.md`
  - `docs/RALLY_PORTING_GUIDE.md`
  - `docs/RALLY_CLI_AND_LOGGING.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md`
- The doc pass now teaches one aligned story:
  - producer routing comes from Doctrine route metadata
  - review routing still comes from review fields
  - prompt build is `AGENTS.md` plus the generated previous-turn appendix when
    declared
  - `previous_turn_inputs.md` is a turn-local archaeology file
  - notes stay context only
- Final rebuild and proof passed:
  - `rebuilt _stdlib_smoke`
  - `rebuilt poem_loop`
  - `rebuilt software_engineering_demo`
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_previous_turn_inputs.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_shared_prompt_ownership.py tests/unit/test_issue_ledger.py tests/unit/test_cli.py -q`
    -> `188 passed`
- Updated the authoritative audit block one last time:
  - Verdict is now `COMPLETE`
  - Phase 5 is now complete
