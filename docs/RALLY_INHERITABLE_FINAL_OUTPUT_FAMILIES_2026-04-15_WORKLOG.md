# Worklog

Plan doc: `docs/RALLY_INHERITABLE_FINAL_OUTPUT_FAMILIES_2026-04-15.md`

## Initial entry
- Run started.
- Current phase: Phase 1 (Refactor the shared producer family)

## Phase 1-3 Progress Update
- Work completed:
  - Refactored `stdlib/rally/prompts/rally/turn_results.prompt` into a shared producer base family plus the default `RallyTurnResult` leaf.
  - Added `_stdlib_smoke` producer inheritance proof through `CloseoutTurnResult`.
  - Added `stdlib/rally/prompts/rally/review_results.prompt` as the shared review family.
  - Added `_stdlib_smoke` split-review proof through `RepairPlanReviewer`.
  - Moved `poem_loop` and `software_engineering_demo` review prompts onto the shared review family.
  - Switched shipped review agents to split final output with explicit `review_fields`.
  - Added focused flow-loader assertions for the producer smoke probe, the review smoke probe, and shipped split-review metadata.
- Tests run + results:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop` — passed
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke` — passed
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target poem_loop --target software_engineering_demo` — passed
  - `uv run pytest tests/unit/test_flow_loader.py::FlowLoaderTests::test_poem_loop_compiled_readback_includes_kernel_skill_and_rationale_contract tests/unit/test_flow_loader.py::FlowLoaderTests::test_stdlib_smoke_closeout_uses_inherited_turn_result_family tests/unit/test_flow_loader.py::FlowLoaderTests::test_stdlib_smoke_review_probe_uses_split_final_output_on_shared_review_family tests/unit/test_flow_loader.py::FlowLoaderTests::test_software_engineering_demo_reviewers_use_split_control_ready_final_output tests/unit/test_flow_loader.py::FlowLoaderTests::test_load_flow_definition_uses_compiled_slug_mapping -q` — `5 passed`
- Issues / deviations:
  - Phase 4 is blocked in this pass because the clean loader cut really needs the Phase 5 runner writeback cut with it.
  - `src/rally/services/runner.py` is already dirty from parallel work in the current worktree, so I stopped before that shared owner path.
- Next steps:
  - Keep `.codex/implement-loop-state.019d91a3-dbb4-7dd2-92d0-bfc28ab077b0.json` armed.
  - Resume at Phase 4 once the runtime loader and runner cut can land together.

## Phase 4-6 Progress Update
- Work completed:
  - Replaced loader-owned review markdown with typed `LoadedReviewTruth` in `src/rally/services/final_response_loader.py`.
  - Refactored `src/rally/services/runner.py` so each successful turn writes one `Rally Turn Result` block and review turns no longer append `Rally Note`.
  - Synced bundled stdlib assets, including new `review_results.prompt`.
  - Extended bundled-asset, workspace-sync, flow-build, and packaged-install tests to cover the shared review-family ship surface.
  - Updated live docs to the final-output-first story in `RALLY_MASTER_DESIGN.md`, `RALLY_RUNTIME.md`, `RALLY_CLI_AND_LOGGING.md`, `RALLY_COMMUNICATION_MODEL.md`, `RALLY_PORTING_GUIDE.md`, and `RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md`.
  - Updated `poem_loop` prompt source and emitted readback so turn history points at `Rally Turn Result` instead of `Rally Note`.
  - Updated `software_engineering_demo` shared contract wording so review truth points at the newest `Rally Turn Result` block instead of a removed runtime review note.
  - Re-emitted `software_engineering_demo` so shipped engineering-demo readback matches the final-output-first story.
  - Switched the packaged-install proof to the local Doctrine checkout used by the dev runner.
  - Did one manual review-ledger spot check against the review-turn ledger text asserted in `tests/unit/test_runner.py`.
- Tests run + results:
  - `uv run python tools/sync_bundled_assets.py` — passed
  - `uv build` — passed
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo` — passed
  - `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_workspace_sync.py tests/unit/test_flow_build.py -q` — `17 passed`
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_bundled_assets.py tests/unit/test_workspace_sync.py -q` — `124 passed`
  - `uv run pytest tests/unit/test_flow_loader.py::FlowLoaderTests::test_poem_loop_compiled_readback_includes_kernel_skill_and_rationale_contract -q` — `1 passed`
  - `uv run pytest tests/unit/test_flow_loader.py::FlowLoaderTests::test_software_engineering_demo_reviewers_use_split_control_ready_final_output -q` — `1 passed`
  - `uv run pytest tests/integration/test_packaged_install.py -q` — `2 passed`
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_bundled_assets.py tests/unit/test_workspace_sync.py tests/integration/test_packaged_install.py -q` — `126 passed`
- Issues / deviations:
  - None.
- Next steps:
  - Keep `.codex/implement-loop-state.019d91a3-dbb4-7dd2-92d0-bfc28ab077b0.json` armed.
  - No approved implementation work remains in this plan.
