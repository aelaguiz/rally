# Worklog

Plan doc: [docs/RALLY_MULTI_FILE_AGENT_PACKAGE_SUPPORT_2026-04-15.md](/Users/aelaguiz/workspace/rally/docs/RALLY_MULTI_FILE_AGENT_PACKAGE_SUPPORT_2026-04-15.md)

## Initial entry
- Run started.
- Current phase: Phase 2: Cut Rally Build Over To Compiler-Owned Packages.

## Phase 2 (Cut Rally Build Over To Compiler-Owned Packages) Progress Update
- Work completed:
  - Removed Rally's role-local `SOUL.prompt` render path from
    `src/rally/services/flow_build.py`.
  - Kept one Doctrine build call per flow and updated the package-boundary
    comment there.
  - Replaced the build test so it proves Rally preserves compiler-owned peer
    files instead of rendering `SOUL.md` itself.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_build.py tests/unit/test_flow_loader.py tests/unit/test_adapter_mcp_projection.py tests/unit/test_run_store.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py -q` — passed (`126 passed`)
- Issues / deviations:
  - None inside the Rally-owned build path.
- Next steps:
  - Remove the dead flow metadata field and tighten package-boundary wording.

## Phase 3 (Remove Stale Flow Metadata) Progress Update
- Work completed:
  - Removed `FlowDefinition.prompt_entrypoint`.
  - Removed the loader's hard-coded flow prompt-entrypoint requirement.
  - Updated direct `FlowDefinition(...)` fixtures in unit tests.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_build.py tests/unit/test_flow_loader.py tests/unit/test_adapter_mcp_projection.py tests/unit/test_run_store.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py -q` — passed (`126 passed`)
- Issues / deviations:
  - None.
- Next steps:
  - Finish package-boundary wording in load, copy, runtime, and docs surfaces.

## Phase 4 (Tighten Loader And Run-Home Package Semantics) Progress Update
- Work completed:
  - Added package-boundary comments in loader, run-home sync, and runtime
    prompt assembly.
  - Added explicit tests that compiler-owned peer files do not widen the
    runtime prompt surface.
  - Added domain-level flow-contract tests so Rally now proves the compiled
    package contract and the removal of flow-level prompt-entrypoint metadata.
  - Synced Rally bundled built-ins after the proof run exposed stale bundled
    stdlib prompt output.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py tests/unit/test_bundled_assets.py -q` — passed (`109 passed`)
- Issues / deviations:
  - None in the Rally-owned package path.
- Next steps:
  - Align the shipped docs to the package model before touching `../psflows`.

## Phase 5 (Align Rally Docs And Porting Guidance) Progress Update
- Work completed:
  - Updated `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_RUNTIME.md`, and
    `docs/RALLY_PORTING_GUIDE.md` to describe compiled agent packages as the
    Rally-consumed unit.
  - Updated the porting guide to show `prompts/agents/<slug>/` as the
    best-case authored home and `prompts/AGENTS.prompt` as a thin build handle
    when needed.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_build.py tests/unit/test_flow_loader.py tests/unit/test_adapter_mcp_projection.py tests/unit/test_run_store.py tests/unit/test_runner.py tests/unit/domain/test_flow_contracts.py -q` — passed (`127 passed`)
  - `uv run pytest tests/unit -q` — failed only in untracked
    `tests/unit/test_shared_prompt_ownership.py`, which expects prompt text
    from a separate parallel change (`2 failed, 292 passed`)
- Issues / deviations:
  - The full unit suite is not clean because of an unrelated untracked test
    file already in the worktree.
- Next steps:
  - Check whether the real-flow proof in `../psflows` is safe to land.

## Phase 6 (Prove The Final Shape On A Real Flow) Progress Update
- Work completed:
  - Changed `../psflows/pyproject.toml` so the lessons emit target writes to
    `flows/lessons/build`, which lets imported `agents/<slug>` packages land
    at `build/agents/<slug>/`.
  - Kept `../psflows/flows/lessons/prompts/AGENTS.prompt` as a thin build
    handle and removed the old `prompts/roles/**` tree after moving that role
    content into `prompts/agents/**`.
  - Rebuilt lessons emitted output and confirmed the nested stale
    `build/agents/agents/**` path is gone.
  - Updated `../psflows/tests/test_lessons_flow_scaffold.py` to prove the
    `roles/` tree and stale nested build path are both gone.
- Tests run + results:
  - `uv sync --dev` — passed.
  - `uv run rally workspace sync` — passed.
  - `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target lessons` — passed (`lessons: emitted 44 file(s) to /Users/aelaguiz/workspace/psflows/flows/lessons/build`).
  - `uv run pytest tests/test_lessons_flow_scaffold.py -q` — passed (`1 passed`).
  - Temporary real run-home materialization for lessons — passed; confirmed:
    `runs/LES-PROOF-PKG/home/agents/project_lead/AGENTS.md`,
    `runs/LES-PROOF-PKG/home/agents/project_lead/final_output.contract.json`,
    and `runs/LES-PROOF-PKG/home/agents/section_dossier_engineer/SOUL.md`.
  - `uv run pytest -q` in `../psflows` — passed (`10 passed`).
- Issues / deviations:
  - A first manual run-home check failed because `materialize_run_home(...)`
    snapshots issue history and expects a real Rally `run.yaml`; the follow-up
    proof used a temporary normal Rally run record and then cleaned it up.
- Next steps:
  - Let the fresh audit child re-run against the updated plan and code truth.

## Phase 6 (Reopened Proof Repair) Progress Update
- Work completed:
  - Deleted `../psflows/flows/lessons/prompts/shared/routing.prompt`.
  - Removed the lessons compile-time owner-stub dependency by moving the
    remaining route guidance onto plain role names and exact Rally
    `next_owner` keys.
  - Repaired the fresh lessons build break by making
    `../psflows/flows/lessons/prompts/contracts/copy_grounding.prompt`
    own a standalone `CopyGroundingWorkflow` instead of the broken inherited
    patch shape.
  - Dropped the stale grounding reroute stubs in
    `../psflows/flows/lessons/prompts/contracts/copy_grounding.prompt` and
    `../psflows/flows/lessons/prompts/contracts/metadata_wording.prompt`.
- Tests run + results:
  - `uv run pytest tests/test_lessons_flow_scaffold.py -q` — passed (`1 passed`).
  - `uv run pytest -q` in `../psflows` — passed (`10 passed`).
  - Temporary real run-home materialization for lessons — passed; confirmed:
    `runs/LES-PROOF-PKG/home/agents/project_lead/AGENTS.md`,
    `runs/LES-PROOF-PKG/home/agents/project_lead/final_output.contract.json`,
    and `runs/LES-PROOF-PKG/home/agents/section_dossier_engineer/SOUL.md`.
- Issues / deviations:
  - The fresh audit summary named `lead_outputs.prompt`, but the live failure
    on the current worktree had already moved to a Doctrine workflow override
    mismatch in `copy_grounding.prompt`. I fixed the actual fresh failure from
    the current repo state instead of forcing the older intermediate state
    back into place.
- Next steps:
  - Let the fresh audit child update the authoritative audit block if it now
    agrees the reopened Phase 6 frontier is clean.
