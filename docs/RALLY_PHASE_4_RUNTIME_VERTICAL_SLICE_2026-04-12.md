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
  - flows/poem_loop/flow.yaml
  - flows/poem_loop/prompts/AGENTS.prompt
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - src/rally/services/flow_loader.py
  - src/rally/cli.py
  - src/rally/services/issue_ledger.py
  - src/rally/adapters/codex/launcher.py
---

# Summary

Phase 4 now has a proved Codex vertical slice.
Rally can create a real run, prepare a real run home, launch real Codex turns,
read strict final JSON results, including control-ready review finals, and drive the authored flow to a real done
state.

Use `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` for the focused command and
logging contract.

What is real today:

- per-command Doctrine rebuild for the current flow before Rally loads compiled agents
- flow loading plus compiled `AGENTS.contract.json` checks
- flow codes and run ids shaped like `<FLOW_CODE>-<n>`
- one active run per flow with a flow lock
- run directories under `runs/active/<run-id>/`
- home materialization for agents, repos, config, auth links, and setup
- Rally-managed agents, skills, MCPs, config, and auth links refreshed on each start or resume
- flow-validated skills and MCPs copied into the run home, but still as the per-flow union rather than per-agent-isolated subsets
- `rally run`
- `rally run --new`
- `rally resume`
- `rally resume --edit`
- `rally resume --restart`
- one shared interactive issue-ready gate for `run` and `resume`
- live operator stream on a TTY with plain fallback off TTY
- strict final-turn JSON parsing
- chained multi-turn execution across handoffs
- per-flow `runtime.max_command_turns` caps for one command
- Codex session save and reuse across chained turns
- `home/issue.md` plus `issue_history/`
- the opening brief lives in `home/issue.md`, not a shared sidecar brief file
- `logs/events.jsonl`
- `logs/agents/<agent>.jsonl`
- `logs/rendered.log`
- `logs/adapter_launch/`
- run state in `state.yaml`
- Codex launch with dangerous bypass, explicit `cwd`, explicit `CODEX_HOME`, and explicit Rally env vars

What is outside Phase 4:

- `rally archive`
- stale-run cleanup and diagnosis beyond the current lock and state checks
- per-agent runtime enforcement for `allowed_skills` and `allowed_mcps`
- a Codex-native MCP auth and readiness contract that proves required MCPs
  work for both top-level and child agents and fails loud when auth or launch
  state is broken

# Stable Rules

- Notes are context only.
- Final JSON is the only turn-ending control path.
- Many turns use the shared five-key Rally turn result.
- Review-native turns may use control-ready Doctrine review JSON instead.
- `AGENTS.md` is injected instruction readback only.
- `AGENTS.contract.json` is the compiler-owned metadata file Rally loads.
- Rally does not ship a shared file-state carrier.
- If an authored review needs local review-state syntax, that is local Doctrine review syntax only.
- There is no separate handoff artifact.
- Rally launches Codex with dangerous bypass for Rally-managed turns.

# Current Code Surface

The current checked-in runtime surface is:

- `src/rally/services/flow_build.py`
  - rebuilds one flow's compiled agents through Doctrine `emit_docs`
  - uses one named emit target per flow from Rally's `pyproject.toml`
  - fails loud if Doctrine is missing, the target is missing, or the compile fails
- `src/rally/services/flow_loader.py`
  - loads `flow.yaml`
  - requires compiled `build/agents/*`
  - requires `AGENTS.contract.json`
  - validates flow codes, `runtime.max_command_turns`, prompt-input commands, and the shared turn-result schema
- `src/rally/cli.py`
  - ships real `run`
  - ships real `resume`
  - ships `resume --edit`
  - ships `resume --restart`
  - ships `issue note`
  - stamps `- Turn: \`N\`` on in-turn notes automatically when Rally launched that turn
- `src/rally/services/run_store.py`
  - allocates run ids
  - writes `run.yaml` and `state.yaml`
  - finds active and archived runs
  - enforces one active run per flow
  - owns flow locks
- `src/rally/services/home_materializer.py`
  - prepares the run-home layout
  - refreshes `home/agents/`, `home/skills/`, `home/mcps/`, `config.toml`, and auth links on each start or resume
  - runs flow setup only when the run home first becomes ready
- `src/rally/services/issue_ledger.py`
  - appends Rally-stamped notes and runtime event blocks
  - inserts one hidden original-issue marker before the first Rally-owned block
  - can recover the original issue from the earliest issue snapshot
  - snapshots the full issue log after each append
- `src/rally/services/run_events.py`
  - writes canonical run events
  - fans them out to whole-run logs, agent logs, and the rendered transcript
- `src/rally/terminal/display.py`
  - renders the live color stream on a TTY
  - shows a richer startup summary with run, flow, model, thinking level, adapter, and agent facts
  - falls back to plain text when needed
- `src/rally/adapters/codex/launcher.py`
  - builds `CODEX_HOME`, `RALLY_BASE_DIR`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and `RALLY_TURN_NUMBER`
  - writes one adapter launch proof file per turn
- `src/rally/adapters/codex/event_stream.py`
  - normalizes Codex JSONL into Rally event records
- `src/rally/adapters/codex/result_contract.py`
  - reads the last assistant message
  - accepts plain JSON or fenced JSON
  - returns one validated Rally turn result
- `src/rally/adapters/codex/session_store.py`
  - saves one session id per agent
  - writes per-turn `exec.jsonl`, `stderr.log`, and `last_message.json`
- `src/rally/services/runner.py`
  - rebuilds the current flow under the flow lock before loading compiled agents
  - wires run creation, resume, prompt injection, Codex launch, result handling, state writes, and issue/event logging
  - lets a blocked run retry after `resume --edit` saves a non-empty issue
  - lets `resume --restart` archive the old run and start a fresh run from the original issue
  - appends a `user edited issue.md` diff block to `home/issue.md` when `resume --edit` changed the issue text
  - appends Rally-owned ledger blocks with Markdown `---` dividers and turn labels on turn-scoped records
  - keeps chaining turns after handoffs until Rally reaches `done`, `blocker`, a runtime failure, a sleep request, or the command turn cap

The live smoke now proves the full `poem_loop` loop:
`poem_writer -> poem_critic -> poem_writer -> done`.
That loop now runs in one Rally command unless a real stop point interrupts it.

`poem_loop` keeps the human issue and durable notes on `home/issue.md` and keeps
the only file artifact at `artifacts/poem.md`.
It also uses the same chained handoff model and per-command turn cap.

# Proof Path

Use the smallest honest proof for each layer:

- prompt or stdlib change
  - rebuild the affected flow with the paired Doctrine compiler
  - inspect `flows/*/build/agents/*`
- runtime change
  - run the owning unit tests
- run-loop change
  - prove it through the `rally run` shell-create path and the `rally resume` launch path

The current core proof set is:

- flow rebuild for `_stdlib_smoke`
- flow rebuild for `poem_loop`
- `tests/unit/test_flow_loader.py`
- `tests/unit/domain/test_turn_result_contracts.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_result_contract.py`
- `tests/unit/test_issue_ledger.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_run_events.py`
- `tests/unit/test_codex_event_stream.py`
- `tests/unit/test_runner.py`
- one live end-to-end `poem_loop` run on Codex that reached `done`

# Next Work

The next honest work is Phase 5 work:

1. add a standalone `rally archive` command
2. add better stale-run diagnosis
3. add a replay or viewer command for old runs
4. prove the new narrow flow on a live Codex run

# Live Truth

Use this doc with:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`

Treat older planning docs as history only.
