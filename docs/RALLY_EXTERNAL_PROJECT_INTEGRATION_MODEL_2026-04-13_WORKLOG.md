---
title: "Rally - External Project Integration Model - Worklog"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: implementation_worklog
related:
  - docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - ../paperclip_agents
---

# Worklog

Plan doc: `docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL_2026-04-13.md`

## Initial entry

- Run started.
- Current phase: Phase 1 - Lock workspace discovery and built-in asset boundaries.

## Phase 1 (Lock workspace discovery and built-in asset boundaries) Progress Update

- Work completed:
  - Added `[tool.rally.workspace]` to Rally root `pyproject.toml`.
  - Added `src/rally/services/workspace.py` with `WorkspaceContext`, workspace discovery, and framework-root lookup.
  - Added `src/rally/services/framework_assets.py` with reserved-path sync and drift checks for `stdlib/rally/**` and `skills/rally-kernel/**`.
  - Cut CLI entrypoints over to one workspace resolver.
- Tests run + results:
  - `uv sync --dev` — passed and synced the local Rally env with `doctrine`.
  - `uv run pytest tests/unit -q` — passed with the new workspace and framework-asset coverage included.
- Issues / deviations:
  - None in this phase.
- Next steps:
  - Cut the runtime services and adapter envs over to `WorkspaceContext`.

## Phase 2 (Cut the runtime over to `WorkspaceContext`) Progress Update

- Work completed:
  - Threaded `WorkspaceContext` through CLI, runner, build, loader, home materialization, and Codex launch env paths.
  - Removed the sibling `../doctrine` runtime lookup in favor of `python -m doctrine.emit_docs --pyproject <workspace-pyproject> --target <flow>`.
  - Replaced `RALLY_BASE_DIR` with `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN`.
- Tests run + results:
  - `uv run pytest tests/unit/test_runner.py -q` — passed.
  - `uv run pytest tests/unit -q` — passed.
  - `uv run rally run poem_loop` from Rally root — reached the expected wait state with `home/issue.md` under `runs/active/POM-1/`.
  - `uv run rally resume POM-1` from Rally root — proved full home materialization plus adapter launch records under `runs/active/POM-1/logs/adapter_launch/`.
- Issues / deviations:
  - The local proof run was stopped after launch-env confirmation so the poem loop would not keep spending turns on unrelated poem iteration.
  - The proof run state was then marked `blocked` and the stop was recorded in the issue log so the run files stayed honest.
- Next steps:
  - Sync prompt, readback, and doc wording to the new workspace model.

## Phase 3 (Sync prompt, readback, and docs truth) Progress Update

- Work completed:
  - Updated Rally stdlib prompts, `flows/poem_loop/prompts/**`, and `skills/rally-kernel/SKILL.md` to use `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN`.
  - Rebuilt `_stdlib_smoke` and `poem_loop` readback from the workspace manifest.
  - Updated the touched Rally design docs so they no longer teach the old repo-root model.
- Tests run + results:
  - `uv run python -c "from pathlib import Path; from rally.services.flow_build import ensure_flow_agents_built; root = Path('.').resolve(); ensure_flow_agents_built(repo_root=root, flow_name='_stdlib_smoke'); ensure_flow_agents_built(repo_root=root, flow_name='poem_loop')"` — passed and refreshed generated readback.
  - `uv run pytest tests/unit/test_flow_loader.py -q` — covered by the green full unit pass.
  - `uv run pytest tests/unit/test_runner.py -q` — passed.
- Issues / deviations:
  - None in this phase.
- Next steps:
  - Port one real external workspace and prove it from that repo root.

## Phase 4 (Prove one real external workspace in ../paperclip_agents) Progress Update

- Work completed:
  - Added `../paperclip_agents/pyproject.toml` with `[tool.rally.workspace]`, Rally and Doctrine path sources, and Rally-native emit config for `poem_loop`.
  - Copied authored `flows/poem_loop/**` source into `../paperclip_agents/flows/poem_loop/`.
  - Let Rally sync `../paperclip_agents/stdlib/rally/**` and `../paperclip_agents/skills/rally-kernel/**` during the proof run.
  - Created one external run at `../paperclip_agents/runs/active/POM-1/` and proved the shared note path there.
- Tests run + results:
  - `uv lock` from `../paperclip_agents` — passed and created the root lockfile.
  - `uv run pytest -q` from `../paperclip_agents` — passed (`29 passed, 2 subtests passed`).
  - `uv run rally run poem_loop` from `../paperclip_agents` — reached the expected wait state and created `runs/active/POM-1/home/issue.md` there.
  - `uv run rally issue note --run-id POM-1 --text 'External workspace note proof from Rally.'` from `../paperclip_agents` — passed after seeding `home/issue.md`.
- Issues / deviations:
  - The external proof used the wait-state run plus note append instead of a full live agent turn because Phase 4 only needed build, built-in sync, run-home materialization, and workspace-local note routing.
- Next steps:
  - Replace the reduced external proof with a resumed launched turn under `../paperclip_agents/runs/**`.

## Phase 4 (Prove one real external workspace in ../paperclip_agents) Progress Update

- Work completed:
  - Resumed the same external run with `uv run rally resume POM-1` from `../paperclip_agents`.
  - Proved external home setup with `READY`, `.rally_home_ready`, `home/config.toml`, synced compiled agents, and synced `skills/rally-kernel/SKILL.md` under `../paperclip_agents/runs/active/POM-1/home/`.
  - Proved external launched runtime behavior with `logs/adapter_launch/turn-001-poem_writer.json`, `Rally Run Started`, one writer note, and one `Rally Turn Result` inside the external run home and issue log.
  - Stopped the external proof run after the writer handoff and critic launch so the poem loop would not keep spending turns on unrelated poem iteration.
  - Marked the external proof run `blocked` and recorded the stop in the external issue log so the run state stayed honest.
- Tests run + results:
  - `uv run rally resume POM-1` from `../paperclip_agents` — passed through `READY`, launched turn 1, wrote `artifacts/poem.md`, appended the writer note, recorded the handoff, and launched turn 2.
  - External evidence inspection — confirmed:
    - `../paperclip_agents/runs/active/POM-1/home/.rally_home_ready`
    - `../paperclip_agents/runs/active/POM-1/logs/adapter_launch/turn-001-poem_writer.json`
    - `../paperclip_agents/runs/active/POM-1/home/issue.md`
    - `../paperclip_agents/runs/active/POM-1/logs/rendered.log`
- Issues / deviations:
  - The proof run was interrupted after the resumed launched turn was recorded because completing the poem loop is outside this architecture change.
- Next steps:
  - Await the next fresh `audit-implementation` pass from `implement-loop`.
