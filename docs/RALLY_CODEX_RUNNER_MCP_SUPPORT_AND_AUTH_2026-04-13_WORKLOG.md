# Worklog

Plan doc: [docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13.md](/Users/aelaguiz/workspace/rally2/docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13.md:1)

## 2026-04-14 - Implement loop resumed from reopened Phase 2
- Loop state stayed armed at
  `.codex/implement-loop-state.019d8c6f-4e46-7d02-aaa8-c27f370a6a94.json`.
- Fixed the Codex readiness `failed_check` values so they now match the plan's
  closed four-check set:
  `run_home_materialization`,
  `codex_config_visibility`,
  `codex_auth_status`,
  and `command_startability`.
- Tightened the streamable HTTP auth rule so Rally now blocks every non-usable
  auth state instead of only `not_logged_in`.
- Added direct adapter tests for all four readiness checks and kept the runner
  blocker tests in place.

## 2026-04-14 - Phase 2 proof
- Ran:
  `uv run pytest tests/unit/test_adapter_mcp_projection.py tests/unit/test_runner.py -q`
- Result:
  `55 passed in 2.77s`

## 2026-04-14 - Direct Codex proof: projected auth still works from changed `CODEX_HOME`
- Setup:
  - made a temporary `CODEX_HOME`
  - linked `auth.json` and `.credentials.json` from `~/.codex`
  - wrote a minimal `config.toml`
- Ran:
  `CODEX_HOME=<temp> codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <temp> --json 'Reply with exactly READY.'`
- Result:
  - exit code `0`
  - stdout included an `agent_message` item with text `READY`
- Why it matters:
  this proves Codex still works when Rally points `CODEX_HOME` at the prepared
  run home and projects file-backed auth there.

## 2026-04-14 - Direct Codex proof: broken required MCP fails early
- Setup:
  - made a temporary `CODEX_HOME`
  - linked the same projected auth files
  - wrote `config.toml` with a required stdio MCP:
    - name: `broken-required`
    - command: `missing-fixture-mcp`
    - `required = true`
- Ran:
  `CODEX_HOME=<temp> codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <temp> --json 'Reply with exactly READY.'`
- Result:
  - exit code `1`
  - stderr included:
    `required MCP servers failed to initialize: broken-required: No such file or directory (os error 2)`
- Why it matters:
  this proves the native Codex `required = true` path fails before useful agent
  work starts when the required MCP cannot launch.

## 2026-04-14 - Direct Codex proof: child-agent parity on the same prepared run home
- Setup:
  - made a temporary `CODEX_HOME`
  - linked the same projected auth files
  - wrote a temporary FastMCP stdio server with one tool, `record`
  - configured that server as required in `config.toml`
  - made the tool append JSON lines to `proof.log`
- Ran:
  `CODEX_HOME=<temp> codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <temp> --json`
  with a prompt that told the parent agent to:
  - call `record` with `caller=parent`
  - spawn exactly one child agent
  - tell the child to call the same `record` tool with `caller=child`
  - wait for the child result
  - reply with `PARENT_CHILD_PROOF_OK`
- Result:
  - exit code `0`
  - `proof.log` contained:
    - `{"caller": "parent", "token": "same-home-proof"}`
    - `{"caller": "child", "token": "same-home-proof"}`
  - stdout contained:
    - an MCP tool call to `record`
    - a `spawn_agent` tool call
    - final text `PARENT_CHILD_PROOF_OK`
- Why it matters:
  this proves the parent and child agent both saw the same MCP server from the
  same prepared `CODEX_HOME`.

## 2026-04-14 - Final verification after code and doc sync
- Ran:
  `uv run pytest tests/unit -q`
- Result:
  `230 passed in 5.40s`
