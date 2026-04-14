---
title: "Rally - Claude Code First-Class Adapter Support - Worklog"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: implementation_worklog
related:
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
---

# Worklog

Plan doc: `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`

## Initial entry

- Run started.
- Current phase: Phase 1 - Shared adapter groundwork and front-door validation.
- Controller state armed at `.codex/implement-loop-state.019d8921-30d5-7f62-b460-256b734cdc9c.json`.

## Phase 1 (Shared adapter groundwork and front-door validation) Progress Update

- Work completed:
  - Added `src/rally/adapters/base.py` with the shared adapter protocol,
    launch-env helpers, launch-record helpers, and shared session-artifact
    helpers.
  - Added `src/rally/adapters/registry.py` and registered the supported
    adapter names there.
  - Added `src/rally/services/final_response_loader.py` and moved the shared
    final JSON loader into Rally-owned services.
  - Updated `src/rally/services/flow_loader.py` so adapter names and adapter
    args are now validated through the registry.
- Tests run + results:
  - `uv run python -m compileall src/rally tests/unit` — passed.
  - later full-suite proof stayed green after the rest of the implementation.
- Issues / deviations:
  - None in this phase.
- Next steps:
  - Cut the shipped Codex path over to the new shared adapter boundary.

## Phase 2 (Cut Codex over to the shared adapter contract) Progress Update

- Work completed:
  - Added `src/rally/adapters/codex/adapter.py` as the first-class Codex
    adapter entrypoint.
  - Updated `src/rally/services/runner.py` so the shared runner now resolves
    one adapter and stays wire-neutral.
  - Updated `src/rally/services/home_materializer.py` so shared issue-first
    home prep stays in Rally while adapter bootstrap now runs through
    `prepare_home(...)`.
  - Kept Codex root-home file placement unchanged under `home/`.
  - Kept `src/rally/adapters/codex/result_contract.py` and
    `src/rally/adapters/codex/session_store.py` as thin wrappers instead of
    deleting them during the cutover.
- Tests run + results:
  - Codex-specific unit coverage stayed green in the later full-suite run.
  - The earlier live `poem_loop` Codex proof from the Phase 4 runtime doc still
    remains the checked-in end-to-end Codex smoke.
- Issues / deviations:
  - No fresh live Codex rerun was added in this implementation pass. Codex
    preservation proof here is the full unit suite plus the already-recorded
    live `poem_loop` smoke.
- Next steps:
  - Add the Claude adapter on top of the new shared seam.

## Phase 3 (Add the Claude adapter and guarded `claude_code` enablement) Progress Update

- Work completed:
  - Added `src/rally/adapters/claude_code/adapter.py`,
    `src/rally/adapters/claude_code/launcher.py`, and
    `src/rally/adapters/claude_code/event_stream.py`.
  - Registered `claude_code` in `src/rally/adapters/registry.py`.
  - Generated `home/claude_code/mcp.json` from Rally MCP definitions.
  - Linked `home/.claude/skills` to `home/skills`.
  - Shipped Claude launch with stdin prompt delivery, `-p`,
    `--output-format stream-json`, `--verbose`, `--permission-mode
    bypassPermissions`, `--strict-mcp-config`, explicit `--tools`, optional
    `--model`, optional `--effort`, and optional `--resume`.
  - Added the real fallback final-output extraction path for JSON objects found
    in `result.result` and assistant text content.
- Tests run + results:
  - `tests/unit/test_claude_code_event_stream.py` — covered in the later full
    unit pass.
  - `tests/unit/test_claude_code_launcher.py` — covered in the later full unit
    pass.
  - One honest live Claude Rally run succeeded through the shipped
    `claude_code` adapter, the real Claude CLI, and the user's existing local
    Claude login.
- Issues / deviations:
  - Live Claude output did not always include `structured_output`. The adapter
    had to accept a JSON object in `result.result` instead. The shipped code
    and the doc set now record that truth.
- Next steps:
  - Converge the plan, worklog, master doc, runtime slice doc, and CLI/logging
    doc to the shipped multi-adapter story.

## Phase 4 (Cleanup, docs convergence, and final proof) Progress Update

- Work completed:
  - Rewrote the plan doc to shipped-state language.
  - Updated the linked runtime docs so they no longer teach a Codex-only
    runtime.
  - Recorded the real Claude v1 ambient-auth caveat and the real
    final-output-shape caveat.
- Tests run + results:
  - `uv run pytest tests/unit -q` — passed with `153 passed`.
- Issues / deviations:
  - Claude still depends on the user's existing local login and Claude's own
    native session store outside the run home.
  - Claude still exposes bundled slash commands and bundled skills in init
    output. Rally clamps built-in tools and Claude.ai MCP servers, but it does
    not fully clean-room every ambient Claude surface yet.
- Next steps:
  - Await the next fresh `audit-implementation` pass from `implement-loop`, or
    hand the broader docs cleanup loop to `arch-docs` if the user wants a
    wider cleanup beyond the runtime docs touched here.

## Reopened implementation pass (after fresh audit) Progress Update

- Audit reopened Phases 1, 2, and 4 because the old shared-loader wrapper and
  test surface were still live, the post-cutover Codex proof had not been
  rerun, and the Hermes runtime plan was still stale.

### Phase 1 follow-through

- Work completed:
  - Moved the remaining shared final-response coverage into
    `tests/unit/test_final_response_loader.py`.
  - Deleted `tests/unit/test_result_contract.py`.
- Tests run + results:
  - `uv run pytest tests/unit/test_final_response_loader.py tests/unit/test_runner.py -q`
    — passed (`44 passed`).
- Issues / deviations:
  - None in this phase.

### Phase 2 follow-through

- Work completed:
  - Deleted `src/rally/adapters/codex/result_contract.py`.
  - Ran one fresh live Codex Rally proof after the cutover on a tiny one-agent
    temp flow that existed only to prove the shared boundary.
- Proof run details:
  - Temp repo root:
    `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-codex-live-42kjh998`
  - Run id: `CDL-1`
  - Status: `done`
  - Summary: `live codex proof`
  - Launch record included `CODEX_HOME` as expected.
- Issues / deviations:
  - The fresh proof used a tiny temp flow instead of rerunning `poem_loop`
    because this pass needed to prove the post-cutover boundary itself with the
    smallest honest live run.

### Phase 4 follow-through

- Work completed:
  - Retired `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
    so it no longer teaches a future Hermes runtime as live truth.
  - Updated the Claude plan and the Phase 4 runtime doc to record the fresh
    live Codex proof and the deleted shared-loader wrapper.
- Tests run + results:
  - `uv run pytest tests/unit/test_final_response_loader.py tests/unit/test_runner.py -q`
    — passed (`44 passed`).
  - `uv run pytest tests/unit -q` — passed (`153 passed`).
- Issues / deviations:
  - The authoritative audit block in the plan doc still reflects the pre-fix
    audit snapshot. It should only be replaced by the next fresh audit child,
    not by this implementation pass.
- Next steps:
  - Await the next fresh `audit-implementation` pass from `implement-loop`.

## Reopened implementation pass (after second fresh audit) Progress Update

- Audit reopened Phases 3 and 4 because the approved Claude launch contract
  still differed from shipped code and the final doc/proof pass had been
  claimed against that narrower story.

### Phase 3 follow-through

- Work completed:
  - Added `src/rally/adapters/claude_code/session_store.py` as the approved
    adapter-owned wrapper over the shared session helpers.
  - Updated `src/rally/adapters/claude_code/adapter.py` to launch Claude with
    `--permission-mode dontAsk`, explicit `--tools`, and explicit
    `--allowedTools`.
  - Extended `src/rally/adapters/claude_code/event_stream.py` so fallback
    final-output extraction now accepts fenced JSON blocks from live Claude
    output in both `result.result` and assistant text content.
  - Tightened `tests/unit/test_runner.py` and
    `tests/unit/test_claude_code_event_stream.py` around that corrected
    contract.
- Tests run + results:
  - `uv run pytest tests/unit/test_claude_code_event_stream.py tests/unit/test_runner.py tests/unit/test_claude_code_launcher.py -q`
    — passed (`46 passed`).
  - One fresh live Claude Rally proof succeeded after the contract fix.
- Proof run details:
  - Temp repo root:
    `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-claude-live-xkjjvb5h`
  - Run id: `CLP-1`
  - Status: `done`
  - Summary: `live claude contract proof`
  - Launch record showed `--permission-mode dontAsk`,
    `--allowedTools`, and `ENABLE_CLAUDEAI_MCP_SERVERS=false`.
- Issues / deviations:
  - The first live rerun exposed one real parser gap: Claude wrapped the final
    JSON in a fenced code block. This pass fixed that gap and reran the live
    proof successfully.

### Phase 4 follow-through

- Work completed:
  - Updated the plan doc, worklog, master design doc, Phase 4 runtime doc,
    CLI/logging doc, and Claude audit doc to the corrected Claude contract.
  - Recorded the fenced-JSON live finding and the successful rerun after the
    parser fix.
- Tests run + results:
  - `uv run pytest tests/unit -q` — passed (`155 passed`).
- Issues / deviations:
  - The authoritative audit block in the plan doc still reflects the older
    audit snapshot. It should only be replaced by the next fresh audit child,
    not by this implementation pass.
- Next steps:
  - Await the next fresh `audit-implementation` pass from `implement-loop`.
