# Worklog

Plan doc: docs/RALLY_AGENT_INTERVIEW_AND_SESSION_FORKING_2026-04-14.md

## Initial entry
- Run started.
- Current phase: Phase 1 - Build the shared interview readback and diagnostic-home seam.
- Preflight: implement-loop runtime support is present for session `019d8d7d-d359-7a01-9f9d-78b8595d039b`.
- Repo state aligned first: pulled `main`, switched to branch `rally-agent-interview-session-forking`, and retargeted the plan to the current canonical live docs.

## Phase 1 (Build the shared interview readback and diagnostic-home seam) Progress Update
- Work completed:
  - Added the shared interview prompt source and bundled copy.
  - Added shared `INTERVIEW.md` sidecar rendering in `src/rally/services/flow_build.py`.
  - Added `prepare_interview_home(...)` plus `home/interviews/` layout support in `src/rally/services/home_materializer.py`.
  - Added shared interview artifact and session helpers in `src/rally/adapters/base.py`.
  - Added focused unit coverage for the build path and diagnostic-home refresh path.
- Tests run + results:
  - `uv run pytest tests/unit/test_flow_build.py tests/unit/test_home_materializer.py -q` — passed
  - `uv run pytest tests/unit -q` — passed
- Issues / deviations:
  - The pulled `main` renamed the canonical live docs, so the plan was retargeted before code work started.
- Next steps:
  - Start Phase 2: add `rally interview`, the shared interview service, and the fresh Claude interview path.

## Phase 2 (Ship the shared `rally interview` command and fresh Claude path) Progress Update
- Work completed:
  - Added the top-level `rally interview <run-id> [--agent <slug>] [--fork]` CLI command.
  - Added `src/rally/services/interview.py` to own target-agent resolution, prompt build, interview artifact layout, and the chat loop outside the turn engine.
  - Added `src/rally/adapters/claude_code/interview.py` for Claude diagnostic turns with `--bare`, inspect-only tools, and saved diagnostic session reuse.
  - Added focused CLI coverage and interview service coverage in `tests/unit/test_cli.py` and `tests/unit/test_interview.py`.
  - Landed Claude `--fork` early on `--resume <live-session> --fork-session` while keeping the live session file untouched.
- Tests run + results:
  - `uv sync --dev` — completed, but it dropped the auto-discovered `rally` entrypoint from the venv, so later proof needed an explicit `RALLY_CLI_BIN`.
  - `uv run pytest tests/unit/test_cli.py tests/unit/test_interview.py -q` — passed
  - `RALLY_CLI_BIN=$PWD/.venv/bin/pytest uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_flow_loader.py tests/unit/test_runner.py -q` — passed
  - `RALLY_CLI_BIN=$PWD/.venv/bin/pytest uv run pytest tests/unit -q` — passed
- Issues / deviations:
  - Proof was blocked once because `uv sync --dev` left the venv without a `rally` executable on PATH and Doctrine briefly had to be reinstalled into the venv. The code changes themselves were not the cause of that failure.
- Next steps:
  - Start Phase 3: add the fresh Codex diagnostic path on `codex app-server`.

## Phase 3 (Add the fresh Codex interview path on native thread and turn APIs) Progress Update
- Work completed:
  - Added `src/rally/adapters/codex/interview.py` with the diagnostic-only `codex app-server` JSON-RPC client.
  - Widened `src/rally/services/interview.py` so the shared interview service now supports both `claude_code` and `codex`.
  - Kept the normal Codex work-turn path on `codex exec` and added one short code comment at the diagnostic transport boundary to make that split explicit.
  - Added focused Codex interview tests that prove fresh thread start and later `turn/start` reuse of the saved diagnostic thread id.
- Tests run + results:
  - `uv run pytest tests/unit/test_interview.py -q` — passed
- Issues / deviations:
  - None.
- Next steps:
  - Start Phase 4: add Codex fork support and close the shared live-session safety proof.

## Phase 4 (Add safe fork support and live-session protection on both adapters) Progress Update
- Work completed:
  - Added Codex fork support on native `thread/fork`.
  - Kept live work-session truth in `home/sessions/<agent>/session.yaml` and stored diagnostic session truth only under `home/interviews/...`.
  - Extended the interview tests so both adapters now prove forked diagnostic sessions stay separate from the live session record.
- Tests run + results:
  - `uv run pytest tests/unit/test_interview.py -q` — passed
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q` — passed
- Issues / deviations:
  - None.
- Next steps:
  - Start Phase 5: land the debugging guide, sync the live docs, and restore the planned front-door proof path.

## Phase 5 (Sync live docs and close with final proof) Progress Update
- Work completed:
  - Added `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`.
  - Updated `README.md`, `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, and `docs/RALLY_RUNTIME.md` so they all point to the guide and describe `rally interview` plus `home/interviews/`.
  - Fixed `src/rally/services/workspace.py` so Rally falls back to the repo-root `rally` wrapper when the editable venv does not have a generated CLI entrypoint.
- Tests run + results:
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q` — passed
  - `uv run pytest tests/unit -q` — passed with `263 passed`
- Issues / deviations:
  - Planned live manual CLI smoke on authenticated Claude and Codex adapters was not run in this pass and remains a non-blocking follow-up.
- Next steps:
  - Fresh audit or docs cleanup if needed. The approved code frontier is closed.

## Reopened audit follow-through (Phases 2 through 5) Progress Update
- Work completed:
  - Moved interview `launch.json` writes to the true pre-launch boundary before
    the first adapter call.
  - Added normalized interview `USER`, `LAUNCH`, `ASSIST`, and `CLOSE` rows to
    `logs/events.jsonl`, `logs/agents/<agent>.jsonl`, and `logs/rendered.log`
    without touching Rally turn state.
  - Added live assistant streaming to both adapters inside the shared
    interview chat loop, including fresh and forked interviews.
  - Tightened the debugging guide and the canonical runtime docs so they now
    explain the live stream and the normal run-log archaeology path.
- Tests run + results:
  - `uv sync --dev` — completed
  - `uv run pytest tests/unit/test_interview.py -q` — passed with `6 passed`
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q` — passed with `89 passed`
  - `uv run pytest tests/unit -q` — passed with `264 passed`
- Issues / deviations:
  - Planned live manual CLI smoke on authenticated Claude and Codex adapters
    is still pending and remains non-blocking.
- Next steps:
  - Manual fresh and fork `/exit` smoke on both live adapters when a
    credentialed environment is available.
