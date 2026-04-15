# Worklog

Plan doc: `docs/RALLY_STDLIB_PROMPT_SURFACE_REFRESH_2026-04-15.md`

## Initial entry
- Run started.
- Current phase: Phase 1 (Shared AGENTS base and shared labels)

## Phase 1-6 Progress Update
- Work completed:
  - Rewrote the shared Rally AGENTS surface to render `Rally Context`, `Read First`, and `Shared Rules` in one stable shared order.
  - Renamed the shared ledger and generic note bindings to `Shared Ledger File` and `Saved Run Note`.
  - Flattened the shared generic note shell and the shared producer final JSON shell inside current compiler support.
  - Rewrote the shared `rally-kernel` and `rally-memory` skill packages around the live move first.
  - Rebuilt shipped flows and shared skills, synced bundled assets, and updated the wording assertions that still expected the old surface.
- Tests run + results:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo` — passed
  - `uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory` — passed
  - `uv run python tools/sync_bundled_assets.py` — passed
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_bundled_assets.py -q` — `110 passed`
  - `uv run pytest tests/unit -q` — `289 passed`
- Issues / deviations:
  - Phase 4 is blocked on the installed `doctrine-agents` `1.0.2` parser rejecting imported ordinary-output inheritance in Rally's prompt graph.
- Next steps:
  - Leave `.codex/implement-loop-state.019d90dd-56b8-70a3-a407-4ea5b05d93a6.json` armed and let the fresh `audit-implementation` pass decide whether only Phase 4 reopens.

## Phase 4-6 Progress Update
- Work completed:
  - Removed the local `Standalone Read` shells from the flow-local note outputs in `poem_loop` and `software_engineering_demo`.
  - Replaced the copied local `append_with` literals with addressable refs to the shared stdlib note output.
  - Rebuilt the affected flows and re-ran the final bundled sync and proof stack against the fully landed source truth.
- Tests run + results:
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target poem_loop --target software_engineering_demo` — passed
  - `uv run python tools/sync_bundled_assets.py` — passed
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/test_flow_build.py tests/unit/test_bundled_assets.py -q` — `110 passed`
  - `uv run pytest tests/unit -q` — `289 passed`
- Issues / deviations:
  - Imported ordinary-output inheritance is still unavailable in the installed `doctrine-agents` `1.0.2` build, so Phase 4 landed through shared addressable refs plus removal of the old local shell instead of `output Child[Parent]`.
- Next steps:
  - Keep `.codex/implement-loop-state.019d90dd-56b8-70a3-a407-4ea5b05d93a6.json` armed and let the next fresh `audit-implementation` pass confirm the reopened frontier is now actually complete.
