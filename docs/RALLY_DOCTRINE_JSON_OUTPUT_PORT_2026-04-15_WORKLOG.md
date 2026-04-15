# Worklog

Plan doc: docs/RALLY_DOCTRINE_JSON_OUTPUT_PORT_2026-04-15.md

## Initial entry
- Run started.
- Current phase: Phase 1 — Add the Doctrine machine artifact Rally needs

## 2026-04-15 - Phase 1 complete
- Added `final_output.contract.json` to Doctrine `emit_docs` for agents that
  declare `final_output:` or a review contract.
- Kept emitted payload shape in `schemas/<output-slug>.schema.json`.
- Serialized final-output metadata plus review carrier or split metadata from
  Doctrine's compiled contract data instead of rebuilding it locally.
- Updated Doctrine emit tests, diagnostic smoke, package smoke, and checked-in
  build proof for examples 79 and 84.
- Proof:
  - `uv run --locked python -m unittest tests.test_emit_docs tests.test_final_output tests.test_package_release -q`
  - `make verify-diagnostics`
  - `make verify-package`
  - `make verify-examples`
- Advanced to Phase 2 — Port the shared framework producer contract.

## 2026-04-15 - Phases 2 and 3 complete
- Ported the shared Rally turn-result contract to Doctrine `output schema`
  with the same five-key payload and inline example.
- Deleted the shared raw schema and example sidecars.
- Rebuilt `_stdlib_smoke` and removed stale generated `AGENTS.contract.json`
  files.
- Ported poem and software-engineering review contracts to Doctrine
  `output schema`.
- Deleted demo review raw schema and example sidecars.
- Rebuilt `poem_loop` and `software_engineering_demo`, then inspected review
  `final_output.contract.json` files for carrier metadata and
  `control_ready: true`.
- Proof:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke`
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target poem_loop`
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target software_engineering_demo`

## 2026-04-15 - Phase 4 complete
- Cut Rally runtime loading from `AGENTS.contract.json` to
  `final_output.contract.json`.
- Replaced runtime contract fields with emitted schema and metadata paths.
- Retargeted Codex and Claude adapters to the emitted schema file.
- Updated synthetic compiled-agent fixtures to the new package shape.
- Updated Rally role-SOUL sidecar rendering to the current Doctrine compile
  helper surface after `root_concrete_agents` was removed.
- Proof:
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_run_store.py tests/unit/test_adapter_mcp_projection.py -q`
  - Result: `118 passed`

## 2026-04-15 - Phase 5 complete against dev Doctrine
- Synced bundled stdlib assets so Rally no longer ships the raw shared schema
  or example sidecars.
- Added flow-build cleanup and validation for the new emitted package shape.
- Retargeted release-flow parsing to `SUPPORTED_FINAL_OUTPUT_CONTRACT_VERSIONS`.
- Updated package and release tests toward `final_output.contract.json`.
- Rebuilt `dist/`.
- Operator correction: this WIP port uses editable `../doctrine`; public
  packaged Doctrine is not the proof target for this loop.
- Proof:
  - `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_package_release.py tests/unit/test_release_flow.py -q`
  - Result: `33 passed`
  - `make build-dist`
- Next:
  - Keep packaged-install proof in the release lane after public Doctrine
    catches up. Do not use it as the JSON-port blocker in this loop.

## 2026-04-15 - Phase 4 restored prompt input command
- Restored `runtime.prompt_input_command` support as a rooted flow-local script
  path.
- Restored runner prompt-input merging under `## Runtime Prompt Inputs`.
- Replaced the removal regression with positive loader and runner coverage.
- Proof:
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py -q`
  - Result: `97 passed`
- Next:
  - Update live docs for the new JSON package story, then rerun the final
    dev-Doctrine proof set.

## 2026-04-15 - Phase 6 complete against dev Doctrine
- Updated runtime, communication, versioning, and porting docs to the emitted
  schema plus `final_output.contract.json` story.
- Added the porting guide rule for inheritable and extendable Doctrine JSON
  output contracts.
- Rebuilt shipped Rally flow output against editable `../doctrine`.
- Spot-checked producer and review final-output package metadata.
- Proof:
  - `uv sync --dev` — passed
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo` — passed
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_run_store.py tests/unit/test_adapter_mcp_projection.py -q` — `119 passed`
  - `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_package_release.py tests/unit/test_release_flow.py -q` — `33 passed`
  - `uv run pytest tests/unit/test_package_release.py tests/unit/test_release_flow.py -q` — `18 passed`
  - `make build-dist` — passed
- Issue:
  - `uv run pytest tests/unit -q` failed in the untracked
    `tests/unit/test_shared_prompt_ownership.py` against dirty skill prompt
    files. That appears separate from this JSON-port surface, so this pass did
    not touch it.
