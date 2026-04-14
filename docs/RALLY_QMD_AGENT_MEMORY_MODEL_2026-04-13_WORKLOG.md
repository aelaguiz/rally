# Worklog

Plan doc: docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md

## Initial entry
- Run started.
- Current phase: Phase 1 - Land the shared Doctrine memory contract.

## Phase 1 (Land the shared Doctrine memory contract) Progress Update
- Work completed:
  - Added the shared Rally memory prompt module and the new `rally-memory` Doctrine skill source.
  - Extended the shared base agent with the shared issue ledger, `RALLY_AGENT_SLUG`, and the shared memory workflows.
  - Moved `poem_loop` and `software_engineering_demo` off local generic issue-ledger inputs.
  - Wired `rally-memory` into the built-in skill bundle, framework sync, and workspace checks.
  - Updated unit-test fixtures so built-in skill tests now include both `rally-kernel` and `rally-memory`.
- Tests run + results:
  - Not run yet in this pass. Next proof is Doctrine emit plus targeted unit tests.
- Issues / deviations:
  - None yet. The next compile pass will show whether the new prompt graph needs more cleanup.
- Next steps:
  - Rebuild the affected flows and skill readback.
  - Run targeted unit tests for the new built-in skill contract.

## Phase 2 (Land the runtime data plane and scope truth) Progress Update
- Work completed:
  - Added `src/rally/domain/memory.py`.
  - Added `src/rally/services/memory_store.py`, `src/rally/services/memory_index.py`, and `src/rally/services/memory_runtime.py`.
  - Added the pinned QMD bridge workspace under `tools/qmd_bridge/`.
  - Extended `src/rally/cli.py` with `memory search`, `memory use`, `memory save`, and `memory refresh`.
  - Tightened `src/rally/services/flow_loader.py` so the compiled slug is the carried source of truth after validation.
- Tests run + results:
  - `uv run pytest tests/unit/test_memory_store.py tests/unit/test_memory_index.py tests/unit/test_memory_runtime.py tests/unit/test_cli.py tests/unit/test_flow_loader.py tests/unit/test_launcher.py -q`
  - Passed in the focused sweep that later expanded to the full runtime and memory test set.
- Issues / deviations:
  - None.
- Next steps:
  - Wire visible memory records through the issue ledger and the canonical event stream.

## Phase 3 (Wire visibility and ambient runtime behavior) Progress Update
- Work completed:
  - Added `Memory Used` and `Memory Saved` append paths in `src/rally/services/issue_ledger.py`.
  - Added `memory_used` and `memory_saved` to `src/rally/services/run_events.py`.
  - Kept `memory search` out of the issue ledger.
  - Deleted the stale `src/rally/services/event_log.py` path.
- Tests run + results:
  - `uv run pytest tests/unit/test_issue_ledger.py tests/unit/test_run_events.py tests/unit/test_runner.py -q`
  - Passed in the focused sweep that later expanded to the full runtime and memory test set.
- Issues / deviations:
  - None.
- Next steps:
  - Sync the plan and live docs to the shipped memory path.

## Phase 4 (Prove one flow and sync live truth) Progress Update
- Work completed:
  - Rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`.
  - Synced the master design, Phase 4 runtime doc, and CLI/logging doc to the shipped memory path.
  - Captured a bridge smoke proof with repo-local `XDG_CACHE_HOME`.
- Tests run + results:
  - `uv run pytest tests/unit/test_memory_store.py tests/unit/test_memory_index.py tests/unit/test_memory_runtime.py tests/unit/test_cli.py tests/unit/test_issue_ledger.py tests/unit/test_run_events.py tests/unit/test_launcher.py tests/unit/test_flow_loader.py tests/unit/test_flow_build.py tests/unit/test_framework_assets.py tests/unit/test_runner.py -q`
  - `130 passed in 2.09s`
  - `uv run pytest tests/unit -q`
  - `158 passed in 1.43s`
- Additional proof:
  - Bridge smoke refresh on an empty scoped collection returned zero-doc success.
  - The smoke confirmed `before=missing` and `after=missing` for `~/.cache/qmd/`.
- Issues / deviations:
  - One honest proof gap remains: no live Codex flow has yet used `rally memory save`, `rally memory search`, and `rally memory use` during an actual flow turn.
  - The current bridge smoke did not force first model download because the collection was empty.
- Next steps:
  - Run one narrow live `poem_loop` memory proof when it is worth paying the first real embed/search cost.

## Current-head verification recheck
- `uv sync --dev`
  - success
- `uv run pytest tests/unit -q`
  - `159 passed in 1.35s`
- bridge smoke on current head:
  - command: `XDG_CACHE_HOME="$PWD/runs/memory/qmd/cache" node tools/qmd_bridge/main.mjs refresh`
  - result: `{"collections":1,"indexed":0,"updated":0,"unchanged":0,"removed":0,"needsEmbedding":0,"docsProcessed":0,"chunksEmbedded":0,"embedErrors":0}`
  - cache check: `before=missing`, `after=missing` for `~/.cache/qmd/`

## Phase 4 follow-through after fresh audit reopened the live proof gap
- Work completed:
  - Reused active run `POM-1` through the real Rally front door with `rally resume POM-1 --edit`.
  - Appended a proof note through the issue editor path instead of hand-editing run state.
  - Captured the missing real `poem_loop` proof:
    - turn 7 saved scoped memory with `rally memory save`
    - turn 9 searched that memory and then used it with `rally memory use`
    - `Memory Saved` and `Memory Used` landed in `home/issue.md`
    - the writer still wrote the normal issue note and normal handoff JSON
    - the critic accepted on turn 10 and the run ended `done`
  - Hardened `src/rally/services/memory_index.py` after the live proof exposed two real issues:
    - bridge stdout on first live `save` and `search` could include non-JSON noise before the final JSON object
    - QMD search returned virtual `qmd:/...` paths, so search hits were not printing the canonical memory id or a short snippet
  - Updated `tests/unit/test_memory_index.py` to cover noisy bridge stdout and virtual-path search hits.
- Tests run + results:
  - `uv run pytest tests/unit/test_memory_index.py tests/unit/test_memory_runtime.py tests/unit/test_cli.py -q`
  - `27 passed in 0.11s`
  - `uv run pytest tests/unit -q`
  - `159 passed in 1.35s`
- Additional proof:
  - `uv run rally memory search --run-id POM-1 --agent-slug poem_writer --query 'stronger image or ending for poem critique'`
  - Output now shows the canonical memory id, the lesson title, and the short `When This Matters` snippet.
  - `~/.cache/qmd/` remains missing after the proof pass.
- Issues / deviations:
  - A one-off raw bridge inspection command was started without forced `XDG_CACHE_HOME` during debugging. It created `~/.cache/qmd/`. I removed that cache and rechecked that `~/.cache/qmd/` is now missing again.
- Next steps:
  - Hand control back to the next fresh audit so it can decide whether Phase 4 is now closed.
