# Worklog

Plan doc: [docs/RALLY_DEFAULT_AGENT_ISSUE_REPORTING_2026-04-14.md](/Users/aelaguiz/workspace/rally3/docs/RALLY_DEFAULT_AGENT_ISSUE_REPORTING_2026-04-14.md:1)

## 2026-04-14 - Phase 1 and Phase 2 implementation
- Put default `agent_issues` guidance on the shared
  `rally.turn_results` contract in
  `stdlib/rally/prompts/rally/turn_results.prompt`.
- Added optional string `agent_issues` to the shared schema and example in
  `stdlib/rally/schemas/rally_turn_result.schema.json` and
  `stdlib/rally/examples/rally_turn_result.example.json`.
- Kept the shared base-agent rules generic so the opt-out stays on the shared
  turn-result shape instead of leaking into every Rally rule block.
- Added a local opt-out shape in
  `flows/_stdlib_smoke/prompts/AGENTS.prompt` that reuses the shared schema
  while keeping local control wording.
- Preserved passive `agent_issues` on `LoadedFinalResponse` in
  `src/rally/services/final_response_loader.py` and wrote
  `Agent Issues: ...` into normalized `Rally Turn Result` blocks in
  `src/rally/services/runner.py`.
- Added focused tests in
  `tests/unit/test_final_response_loader.py`,
  `tests/unit/test_flow_loader.py`,
  `tests/unit/test_runner.py`, and
  `tests/unit/test_software_engineering_demo_prompt_inputs.py`.
- Rebuilt the affected readback for `_stdlib_smoke`, `poem_loop`,
  `software_engineering_demo`, and `rally-kernel`.
- Synced bundled copies under `src/rally/_bundled/`.

## 2026-04-14 - Focused proof
- Ran:
  `uv run pytest tests/unit/domain/test_turn_result_contracts.py tests/unit/test_final_response_loader.py tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_issue_ledger.py tests/unit/test_software_engineering_demo_prompt_inputs.py -q`
- Result:
  `104 passed in 3.61s`

## 2026-04-14 - Final readback and ship-gate proof
- Read the emitted build output and confirmed:
  - shared direct-import flows show default `agent_issues` guidance on the
    shared non-review turn-result contract
  - `_stdlib_smoke` keeps local control wording in its opt-out lane instead of
    inheriting shared issue wording in Rally rules
- Ran:
  `uv run python tools/sync_bundled_assets.py --check`
- Result:
  passed
- Ran:
  `uv run pytest tests/unit -q`
- Result:
  `245 passed in 5.50s`
- Ran:
  `uv build`
- Result:
  built `dist/rally_agents-0.1.1.tar.gz` and
  `dist/rally_agents-0.1.1-py3-none-any.whl`
- Ran:
  `uv run pytest tests/integration/test_packaged_install.py -q`
- Result:
  `2 passed in 9.59s`
- Note:
  the packaged-install test first failed because `dist/` had no build
  artifacts. Building the repo-owned wheel and sdist was the right proof
  precondition, not a code workaround.

## 2026-04-14 - Audit reopen follow-through
- The fresh implementation audit reopened Phase 1 and Phase 3 for completion
  drift, not runtime breakage.
- Restored the approved shared guidance in
  `stdlib/rally/prompts/rally/base_agent.prompt` so the shared Rally rules now
  say that turns using `rally.turn_results.RallyTurnResult` should send one
  short `agent_issues` value or `none`.
- Updated the live docs so they now say a non-review flow can opt out locally
  by declaring its own output shape over the shared schema in prompt source.
- Added one readback guard in `tests/unit/test_flow_loader.py` so the shared
  base-agent guidance stays visible in compiled Rally-managed flow output.
- Rebuilt the affected readback for `_stdlib_smoke`, `poem_loop`,
  `software_engineering_demo`, and `rally-kernel`.
- Synced bundled copies under `src/rally/_bundled/`.
- Re-read emitted output and confirmed:
  - shared flows show the repaired base-agent guidance
  - `_stdlib_smoke` still keeps local control wording in its opt-out
    final-output lane
- Ran:
  `uv run python tools/sync_bundled_assets.py --check`
- Result:
  passed
- Ran:
  `uv run pytest tests/unit -q`
- Result:
  `245 passed in 6.31s`
- Ran:
  `uv build`
- Result:
  rebuilt `dist/rally_agents-0.1.1.tar.gz` and
  `dist/rally_agents-0.1.1-py3-none-any.whl`
- Ran:
  `uv run pytest tests/integration/test_packaged_install.py -q`
- Result:
  `2 passed in 10.49s`
