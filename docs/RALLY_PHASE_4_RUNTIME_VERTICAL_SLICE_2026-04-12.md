---
title: "Rally - Phase 4 Runtime Vertical Slice"
date: 2026-04-12
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_status
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - flows/poem_loop/flow.yaml
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - src/rally/adapters/base.py
  - src/rally/adapters/registry.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/claude_code/adapter.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - src/rally/cli.py
---

# Summary

Phase 4 began as the first real Codex runtime slice.
The shipped runtime now extends that slice through one shared adapter boundary
with `codex` and `claude_code`.

Rally can now:

- create a real run
- prepare a real run home
- launch real turns through either supported adapter
- read one strict final JSON result through one shared loader
- drive authored flows to real handoff, done, blocker, or sleep states through
  one shared run model

Use `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` for the focused command and
logging contract.

What is real today:

- per-command Doctrine rebuild for the current flow before Rally loads compiled
  agents
- flow loading plus compiled `AGENTS.contract.json` checks
- one shared adapter boundary under `src/rally/adapters/base.py` and
  `src/rally/adapters/registry.py`
- supported adapters: `codex` and `claude_code`
- one active run per flow with a flow lock
- shared issue-first home prep plus adapter-owned bootstrap refresh on every
  start or resume
- one shared prompt path
- one shared final JSON path at `last_message.json`
- shared session-artifact paths under `home/sessions/<agent>/`
- shared launch proof under `logs/adapter_launch/`
- `rally run`
- `rally run --new`
- `rally resume`
- `rally resume --edit`
- `rally resume --restart`
- live operator stream on a TTY with plain fallback off TTY
- chained multi-turn execution across handoffs
- per-flow `runtime.max_command_turns`
- `home/issue.md` plus `issue_history/`
- `rally issue note --field key=value`
- `logs/events.jsonl`
- `logs/agents/<agent>.jsonl`
- `logs/rendered.log`
- run state in `state.yaml`
- Codex root-home bootstrap through `CODEX_HOME=<run-home>`
- Claude generated bootstrap through `home/claude_code/mcp.json`,
  `home/.claude/skills`, and `ENABLE_CLAUDEAI_MCP_SERVERS=false`

What is still outside Phase 4:

- `rally archive`
- deeper stale-run diagnosis
- per-agent runtime enforcement for `allowed_skills` and `allowed_mcps`
- a full adapter-native MCP auth and readiness contract
- run-home-owned Claude auth

# Stable Rules

- Notes are context only.
- Notes may carry flat string header fields for stable labels.
- Final JSON is the only turn-ending control path.
- Many turns use the shared five-key Rally turn result.
- Review-native turns may use control-ready Doctrine review JSON instead.
- `AGENTS.md` is injected instruction readback only.
- `AGENTS.contract.json` is the compiler-owned metadata file Rally loads.
- There is no separate handoff artifact.
- Shared runtime owns prompt assembly, home policy, state routing, and the
  final JSON read path.
- Adapters own launch rules, adapter-local bootstrap, event parsing, and
  session handling.

# Current Code Surface

The current checked-in runtime surface is:

- `src/rally/services/flow_build.py`
  - rebuilds one flow's compiled agents through Doctrine
- `src/rally/services/flow_loader.py`
  - loads `flow.yaml`
  - validates supported adapter names and adapter args through the registry
  - validates `runtime.max_command_turns`, prompt-input commands, and guarded
    repo paths
- `src/rally/cli.py`
  - ships real `run`
  - ships real `resume`
  - ships `resume --edit`
  - ships `resume --restart`
  - ships `issue note`
- `src/rally/services/run_store.py`
  - allocates run ids
  - writes `run.yaml` and `state.yaml`
  - finds active and archived runs
  - enforces one active run per flow
  - owns flow locks
- `src/rally/services/home_materializer.py`
  - prepares the shared run-home layout
  - enforces non-empty `home/issue.md`
  - syncs built-in framework assets
  - copies compiled agents plus allowlisted skills and MCPs
  - calls `adapter.prepare_home(...)`
  - runs flow setup only when the run home first becomes ready
- `src/rally/services/issue_ledger.py`
  - appends Rally-stamped notes and runtime event blocks
  - inserts the original-issue marker
  - snapshots the full issue log after each append
- `src/rally/services/run_events.py`
  - writes canonical run events
  - fans them out to whole-run logs, agent logs, and the rendered transcript
- `src/rally/services/final_response_loader.py`
  - reads one final JSON object from `last_message.json`
  - parses either the shared Rally turn result or review-native control-ready
    finals
- `src/rally/adapters/base.py`
  - defines `RallyAdapter`, `AdapterSessionRecord`, `TurnArtifactPaths`, and
    `AdapterInvocation`
  - provides shared launch-env, launch-record, session, and turn-artifact
    helpers
- `src/rally/adapters/registry.py`
  - registers `codex` and `claude_code`
- `src/rally/adapters/codex/adapter.py`
  - owns the Codex launch shape, root-home bootstrap, event replay, and
    session reuse
- `src/rally/adapters/claude_code/adapter.py`
  - owns the Claude launch shape, generated MCP config, tool clamp, event
    replay, and session reuse
- `src/rally/adapters/claude_code/event_stream.py`
  - parses Claude stream-json events
  - extracts final JSON from `structured_output`, `result.result`, assistant
    text JSON, or `StructuredOutput` tool payloads
- `src/rally/services/runner.py`
  - rebuilds the current flow under the flow lock before loading compiled
    agents
  - wires run creation, resume, prompt injection, adapter launch, final-result
    handling, state writes, and issue/event logging
  - keeps chaining turns after handoffs until Rally reaches a real stop point

The live smoke still proves the full `poem_loop` loop on Codex:
`poem_writer -> poem_critic -> poem_writer -> done`.

This implementation pass also added:

- one honest live Claude proof through Rally
- one fresh post-cutover live Codex proof on a tiny one-agent temp flow

# Proof Path

Use the smallest honest proof for each layer:

- prompt or stdlib change
  - rebuild the affected flow with the paired Doctrine compiler
  - inspect `flows/*/build/agents/*`
- runtime change
  - run the owning unit tests
- adapter change
  - prove the adapter-specific tests plus the shared runner tests

The current core proof set is:

- `tests/unit/test_adapter_registry.py`
- `tests/unit/test_final_response_loader.py`
- `tests/unit/test_runner.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_codex_event_stream.py`
- `tests/unit/test_claude_code_event_stream.py`
- `tests/unit/test_claude_code_launcher.py`
- `uv run pytest tests/unit -q` with `155 passed`
- one earlier live end-to-end `poem_loop` run on Codex
- one fresh live Codex Rally run on the shared adapter boundary with result
  `done` and summary `live codex proof`
- one fresh live Claude Rally run using the supported v1 auth path with result
  `done` and summary `live claude contract proof`
- the Claude fallback extractor now accepts fenced JSON blocks from live Claude
  output in `result.result` and assistant text content

# Next Work

The next honest work after this slice is:

1. add a standalone `rally archive` command
2. add better stale-run diagnosis
3. add a replay or viewer command for old runs
4. add one real adapter-native MCP readiness contract
5. decide later whether isolated Claude auth is worth the extra complexity

# Live Truth

Use this doc with:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`

Treat older planning docs as history only.
