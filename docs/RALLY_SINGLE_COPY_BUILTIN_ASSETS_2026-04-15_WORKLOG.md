# Worklog

Plan doc: docs/RALLY_SINGLE_COPY_BUILTIN_ASSETS_2026-04-15.md

## Initial entry
- Run started.
- Current phase: Phase 1 through Phase 5 implementation frontier.

## Phase 1-3 (Resolver, Runtime Cutover, Legacy Deletes) Progress Update
- Work completed:
  - Added `src/rally/services/builtin_assets.py` as the single built-in resolver for source checkouts and installed packages.
  - Cut build, run, home materialization, rooted `stdlib:` resolution, and adapter MCP expansion over to that resolver.
  - Deleted `_bundled`, bundle-sync code, the workspace-sync copy command, and the old mirror-based release checks.
- Tests run + results:
  - `uv sync --dev` — environment already in sync.
- Issues / deviations:
  - None after the Doctrine provider-root cutover landed in the local dependency.
- Next steps:
  - Prove the new build boundary and package behavior.

## Phase 4 (Tests And Package Proof) Progress Update
- Work completed:
  - Updated unit and integration tests to cover resolver-backed built-ins, provider-root emit, rooted-path expansion, CLI removal of `workspace sync`, and packaged installs with no host vendored built-ins.
  - Added a regression test for stale compiled-agent directories so rebuilds delete retired generated agent packages.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_build.py -q` — `9 passed`.
  - `uv run pytest tests/unit -q` — `301 passed`.
  - `uv run pytest tests/integration/test_packaged_install.py -q` — `2 passed`.
- Issues / deviations:
  - None.
- Next steps:
  - Rebuild source readback and record the final package proof.

## Phase 5 (Docs, Readback, Final Proof) Progress Update
- Work completed:
  - Rebuilt `poem_loop` and `software_engineering_demo` through `ensure_flow_assets_built(...)`.
  - Rebuilt `_stdlib_smoke` with Doctrine emit because it is an emit target, not a Rally flow with `flow.yaml`.
  - Updated live docs that still taught deleted copy paths or retired shared prompt modules.
- Tests run + results:
  - `uv run python - <<'PY' ... ensure_flow_assets_built(..., flow_name='poem_loop'/'software_engineering_demo') ... PY` — rebuilt both flow readbacks; stale `flows/software_engineering_demo/build/agents/critic` was pruned.
  - `uv run python - <<'PY' ... emit_target(targets['_stdlib_smoke']) ... PY` — rebuilt `_stdlib_smoke`.
  - `make build-dist` — built wheel and sdist; built-in files now ship under `rally_assets/...`.
- Issues / deviations:
  - The first `_stdlib_smoke` rebuild attempt through `ensure_flow_assets_built()` failed because `_stdlib_smoke` is not a Rally flow and has no `flow.yaml`. Rebuilt it through Doctrine emit instead.
- Next steps:
  - Hand off to fresh `audit-implementation`.

## Phase 5 (README Audit Follow-Through) Progress Update
- Work completed:
  - Rewrote the README host integration section so it no longer teaches `workspace sync`, host-side `doctrine.emit_docs`, or a synced-builtins gitignore model.
  - Pointed host users back to Rally-managed `run` and `resume` as the supported build path.
- Tests run + results:
  - `uv run rally --help` — CLI surface still shows only `run`, `resume`, `status`, `issue`, and `memory`; no `workspace sync` command remains.
  - README section re-read after edit — host guidance now says Rally-managed builds do not write `stdlib/rally/` or `skills/rally-*` during normal host runs.
- Issues / deviations:
  - None.
- Next steps:
  - Hand off to fresh `audit-implementation`.

## Phase 5 (Porting Guide Audit Follow-Through) Progress Update
- Work completed:
  - Rewrote the porting guide host workflow so it now says to use Rally-managed build and run from the host repo.
  - Rewrote the host-repo verification checklist so it no longer starts with a sync-first built-ins step.
- Tests run + results:
  - `sed -n '596,616p' docs/RALLY_PORTING_GUIDE.md` — front-door host workflow now says Rally resolves its own stdlib and built-in skills during the host-repo path.
  - `sed -n '876,896p' docs/RALLY_PORTING_GUIDE.md` — verification loop now starts with `run the flow through Rally`.
  - `rg -n "sync Rally-owned built-ins first|sync built-ins|workspace sync" docs/RALLY_PORTING_GUIDE.md` — no matches.
- Issues / deviations:
  - None.
- Next steps:
  - Hand off to fresh `audit-implementation`.

## Fresh audit completion
- Proof run:
  - `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_rooted_path.py tests/unit/test_cli.py tests/unit/test_runner.py tests/integration/test_packaged_install.py -q` — `123 passed`.
- Verdict:
  - `audit-implementation` is complete; no phases were reopened.
