---
title: "Rally Runtime"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_MEMORY.md
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

This file records the shipped Rally runtime.
Rally now runs through one shared adapter boundary with `codex` and
`claude_code`.

Rally can now:

- create a real run
- prepare a real run home
- launch real turns through either supported adapter
- read one strict final JSON result through one shared loader
- drive authored flows to real handoff, done, blocker, or sleep states through
  one shared run model

The current repo also ships Rally memory support on top of that runtime:

- shared Doctrine memory contract
- repo-local markdown memory truth
- repo-local QMD state
- Rally memory CLI
- visible memory runtime events

Use `docs/RALLY_CLI_AND_LOGGING.md` for the focused command and
logging contract.

What ships today:

- per-command Doctrine rebuild for the current flow before Rally loads
  compiled agent packages
- flow loading plus compiled agent-package checks:
  the required runtime pair `AGENTS.md` plus `final_output.contract.json`,
  plus emitted schema files and additive `io` metadata referenced by that
  contract
- one shared adapter boundary under `src/rally/adapters/base.py` and
  `src/rally/adapters/registry.py`
- supported adapters: `codex` and `claude_code`
- one active run per flow with a flow lock
- shared issue-first home prep plus adapter-owned bootstrap refresh on every
  start or resume
- one shared prompt assembly path: `AGENTS.md` plus an optional generated
  previous-turn appendix when the compiled contract asks for it
- one shared final JSON path at `last_message.json`
- shared session-artifact paths under `home/sessions/<agent>/`
- shared launch proof under `logs/adapter_launch/`
- run directories under `runs/active/<run-id>/`
- home materialization for agents, repos, config, auth links, and setup
- Rally-managed agents, skills, MCPs, config, and auth links refreshed on each start or resume
- flow-validated skills and MCPs copied into the run home, with markdown
  `SKILL.md` and Doctrine `prompts/SKILL.prompt` both supported
- per-agent skill views refreshed under `home/sessions/<agent>/skills/` and
  the live `home/skills/` tree activated per turn from that prebuilt view
- flow-level `setup_home_script`, `runtime.env`, and
  `runtime.guarded_git_repos`
- dirty guarded-repo failures that block `handoff` or `done` loud instead of
  letting Rally claim a clean finish
- `rally run`
- `rally run --from-file <path>`
- `rally run --new`
- `rally run --step`
- `rally run --model <name>`
- `rally run --thinking <level>`
- `rally resume`
- `rally resume --edit`
- `rally resume --restart`
- `rally resume --step`
- `rally resume --model <name>`
- `rally resume --thinking <level>`
- `rally status`
- current-command model and thinking flags that win over saved run overrides
- saved run overrides that win over `flow.yaml` until the operator changes them
- restart behavior that carries saved overrides into the fresh run unless the restart command passes new ones
- Rally resolves built-in stdlib and built-in skills during build and run
- host workspaces do not need Rally-owned built-in copies before the first run
- live operator stream on a TTY with plain fallback off TTY
- CLI help with short examples and next-step hints
- chained multi-turn execution across handoffs
- one-turn manual stepping that stops as `paused` instead of `blocked`
- per-flow `runtime.max_command_turns`
- per-run CLI model and thinking overrides saved in `run.yaml`
- `home/issue.md` plus `issue_history/`
- the opening brief lives in `home/issue.md`, not a shared sidecar brief file
- `rally issue note --field key=value`
- `rally issue current`
- shared issue-ledger input in the Rally stdlib
- optional Rally memory contract in the Rally stdlib
- `rally memory search`
- `rally memory use`
- `rally memory save`
- `rally memory refresh`
- durable memory markdown under `runs/memory/entries/<flow_code>/<agent_slug>/`
- repo-local QMD state under `runs/memory/qmd/index.sqlite` and `runs/memory/qmd/cache/`
- a pinned QMD bridge under `tools/qmd_bridge/`
- first-class memory rows for `search`, `use`, `save`, and `refresh` in the canonical runtime event stream
- `logs/events.jsonl`
- `logs/agents/<agent>.jsonl`
- `logs/rendered.log`
- run state in `state.yaml`
- Codex root-home bootstrap through `CODEX_HOME=<run-home>`
- Claude generated bootstrap through `home/claude_code/mcp.json`,
  `home/.claude/skills`, and `ENABLE_CLAUDEAI_MCP_SERVERS=false`
- Codex launch with dangerous bypass, explicit `cwd`, explicit `CODEX_HOME`, and explicit Rally env vars
- Codex pre-turn MCP readiness through `codex mcp get/list` plus a bounded
  stdio start check on the projected shared MCP set
- one live `software_engineering_demo` proof from a blank seeded repo
- one second `software_engineering_demo` proof that stacked `issue/sed-4` on
  top of accepted `issue/sed-3` history

What is not shipped yet:

- `rally archive`
- deeper stale-run diagnosis
- per-agent runtime enforcement for `allowed_mcps`
- run-home-owned Claude auth

# Stable Rules

- Notes are context only.
- Memory is context only.
- Notes may carry flat string header fields for stable labels.
- Final JSON is the only turn-ending control path.
- Many turns use the shared Rally turn result base with four control keys plus optional passive `agent_issues`.
- Producer schemas may add Doctrine-owned readback keys, including a typed route field when the flow hands off.
- A non-review flow can opt out locally by declaring its own output shape over the shared schema. That stays a prompt-contract choice, not a runtime flag.
- Review-native turns may use control-ready Doctrine review JSON instead.
- all four memory commands are visible Rally events.
- agent-run memory commands should render as memory rows, not generic shell rows.
- `AGENTS.md` is the main injected instruction readback.
- When the compiled contract emits `io.previous_turn_inputs`, Rally also injects
  one generated `## Previous Turn Inputs` appendix built from exact prior turn
  artifacts.
- `final_output.contract.json` is the compiler-owned metadata file Rally loads.
- Emitted schema files under `schemas/` are the payload wire contract.
- Other files in the compiled package stay compiler-owned peer artifacts.
- There is no separate handoff artifact.
- Shared runtime owns prompt assembly, home policy, state routing, and the
  final JSON read path.
- Adapters own launch rules, adapter-local bootstrap, event parsing, and
  session handling.

# Current Code Surface

The current checked-in runtime surface is:

- `src/rally/services/flow_build.py`
  - rebuilds one flow's compiled agent packages through Doctrine
  - trusts Doctrine for optional peer files such as `SOUL.md`
- `src/rally/services/flow_loader.py`
  - loads `flow.yaml`
  - validates supported adapter names and adapter args through the registry
  - validates `runtime.max_command_turns`, `runtime.env`, and guarded repo paths
  - treats each `build/agents/<slug>/` directory as one compiled agent package
  - requires `AGENTS.md`, emitted schema files, and
    `final_output.contract.json`
  - loads emitted route selector metadata and emitted `io.previous_turn_inputs`
  - validates flow codes, `runtime.max_command_turns`, `runtime.env`,
    `runtime.guarded_git_repos`, and the shared turn-result schema
  - carries the compiled slug forward as the source-of-truth agent identity after validation
- `src/rally/services/previous_turn_inputs.py`
  - resolves exact previous-turn inputs from emitted `io` metadata plus the
    prior turn artifacts
  - keeps structured previous outputs as JSON and readable outputs as text
  - fails loud on unsupported note-backed reopen or contract mismatches
- `src/rally/services/skill_bundles.py`
  - resolves markdown skill roots from `SKILL.md`
  - resolves Doctrine skill roots from `prompts/SKILL.prompt`
  - requires emitted Doctrine `build/SKILL.md` before materialization
- `src/rally/cli.py`
  - ships real `run`
  - ships real `resume`
  - ships `resume --edit`
  - ships `resume --restart`
  - lets the operator override model and thinking on `run` or `resume`
  - keeps those overrides in `run.yaml` for later resume or restart
  - ships `issue current`
  - ships `issue note`, including repeatable `--field key=value`
  - ships `memory search`, `memory use`, `memory save`, and `memory refresh`
  - stamps `- Turn: \`N\`` on in-turn notes automatically when Rally launched that turn
- `src/rally/memory/models.py`
  - defines `MemoryScope`, `MemoryEntry`, `MemorySearchHit`, `MemorySaveResult`, and `MemoryRefreshResult`
- `src/rally/memory/store.py`
  - keeps markdown under `runs/memory/entries/...` as the durable memory truth
- `src/rally/memory/index.py`
  - forces repo-local QMD paths
  - talks only to the pinned Node bridge
  - owns scoped refresh and search behavior
- `src/rally/memory/service.py`
  - resolves scope from run state and env
  - keeps memory CLI behavior thin and Rally-owned
- `src/rally/memory/events.py`
  - writes memory-specific runtime events through the shared run-event path
- `src/rally/services/run_store.py`
  - allocates run ids
  - writes `run.yaml` and `state.yaml`
  - persists optional saved model and thinking overrides in `run.yaml`
  - finds active and archived runs
  - enforces one active run per flow
  - owns flow locks
- `src/rally/services/home_materializer.py`
  - prepares the shared run-home layout
  - enforces non-empty `home/issue.md`
  - syncs built-in framework assets
  - copies whole compiled agent packages, refreshes per-agent skill views under
    `home/sessions/<agent>/skills/`, and copies allowlisted MCPs
  - calls `adapter.prepare_home(...)`
  - checks startup host inputs against the effective env from shell env plus
    optional `runtime.env`
  - runs flow setup only when the run home first becomes ready
- `src/rally/services/guarded_git_repos.py`
  - checks guarded run-home repo paths for missing dirs, non-git roots, and
    dirty worktrees
  - renders the blocker text Rally writes when those checks fail
- `src/rally/services/issue_ledger.py`
  - appends Rally-stamped notes and runtime event blocks
  - renders the bounded current issue view for the shared read-first path
  - inserts the original-issue marker
  - snapshots the full issue log after each append
- `src/rally/services/run_events.py`
  - writes canonical run events
  - fans memory activity through first-class memory rows for all four memory commands
  - fans them out to whole-run logs, agent logs, and the rendered transcript
- `tools/qmd_bridge/`
  - pins `@tobilu/qmd` `2.1.0`
  - opens QMD through the SDK with explicit `dbPath`
  - keeps the Python/Node seam narrow and explicit
- `src/rally/terminal/display.py`
  - renders the live color stream on a TTY
  - shows a richer startup summary with run, flow, model, thinking level, adapter, and agent facts
  - falls back to plain text when needed
- `src/rally/services/final_response_loader.py`
  - reads one final JSON object from `last_message.json`
  - parses either the shared Rally turn result or review-native control-ready
    finals
  - keeps the loaded payload ready for issue-ledger readback
  - keeps passive `agent_issues` when the shared shape sends it
- `src/rally/services/run_events.py`
  - writes the stable `RunEvent` log under `logs/events.jsonl`
  - mirrors raw adapter stdout JSON as non-rendered `RAWJSON` rows
  - mirrors the loaded `last_message.json` payload as a non-rendered
    `FINALJSON` row
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
- `src/rally/adapters/codex/event_stream.py`
  - normalizes Codex JSONL into Rally event records
- `src/rally/adapters/codex/launcher.py`
  - builds `CODEX_HOME`, `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and `RALLY_TURN_NUMBER`
  - writes one adapter launch proof file per turn
- `src/rally/services/flow_env.py`
  - expands optional `runtime.env` values from `flow.yaml`
  - applies that flow env to startup host-input checks, setup, and adapter launches
  - lets flow env override duplicate shell env while still keeping Rally and adapter keys last
- `src/rally/adapters/codex/session_store.py`
  - saves one session id per agent
  - writes per-turn `exec.jsonl`, `stderr.log`, and `last_message.json`
- `src/rally/services/runner.py`
  - rebuilds the current flow under the flow lock before loading compiled
  agents
  - wires run creation, resume, adapter launch, guarded-repo checks, result handling, state writes, and
    issue/event logging
  - appends the generated previous-turn appendix to the prompt when the
    compiled contract asks for prior outputs
  - validates `run --from-file` before archive or run creation, then copies
    that text into the new run's `home/issue.md`
  - lets a blocked run retry after `resume --edit` saves a non-empty issue
  - lets `resume --restart` archive the old run and start a fresh run from the
    original issue
  - appends a `user edited issue.md` diff block to `home/issue.md` when
    `resume --edit` changed the issue text
  - appends Rally-owned ledger blocks with Markdown `---` dividers and turn
    labels on turn-scoped records
  - keeps the quick summary lines on `Rally Turn Result` blocks, including
    structured review fields for review turns, and adds a pretty JSON copy of
    the full final message under them
  - lets `run --step` and `resume --step` stop clean after one turn and mark
    the run as `paused`
  - keeps chaining turns after handoffs until Rally reaches `done`, `blocker`,
    a runtime failure, a sleep request, or the command turn cap

- `flows/software_engineering_demo/setup/prepare_home.sh`
  - bootstraps a blank demo repo with a seed commit on first run
  - copies the newest archived done demo repo, including `.git`, on later runs
  - creates a new `issue/<run-id>` branch for each issue
- `skills/demo-git/prompts/**`
  - provides one Doctrine-authored git helper skill plus a small helper script
    and runnable reference examples for the demo repo

The live smoke now proves two real paths:

- the full `poem_loop` loop:
  `muse -> poem_writer -> poem_critic -> muse -> poem_writer -> poem_critic -> done`
- the full `software_engineering_demo` loop:
  `architect -> architect_reviewer -> developer -> developer_reviewer -> qa_docs_tester -> qa_reviewer`

Both loops now run in one Rally command unless a real stop point interrupts
them.

This implementation pass also added:

- one honest live Claude proof through Rally
- one fresh post-cutover live Codex proof on a tiny one-agent temp flow

`software_engineering_demo` now proves a real repo story too:

- `SED-3` started from a blank seeded repo and ended done with commit
  `0cd50ba`
- `SED-4` started from archived `SED-3` history on `issue/sed-4` and ended done
  with commit `53991c4` stacked on top of `0cd50ba`

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

- flow rebuild for `_stdlib_smoke`
- flow rebuild for `poem_loop`
- flow rebuild for `software_engineering_demo`
- Doctrine skill emit for `demo-git`
- `tests/unit/test_adapter_registry.py`
- `tests/unit/test_flow_build.py`
- `tests/unit/test_flow_loader.py`
- `tests/unit/domain/test_turn_result_contracts.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_final_response_loader.py`
- `tests/unit/test_issue_ledger.py`
- `tests/unit/test_runner.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_run_events.py`
- `tests/unit/test_codex_event_stream.py`
- `tests/unit/test_claude_code_event_stream.py`
- `tests/unit/test_claude_code_launcher.py`
- `tests/unit/memory/test_store.py`
- `tests/unit/memory/test_index.py`
- `tests/unit/memory/test_service.py`
- `tests/unit/memory/test_events.py`
- `tests/unit/test_flow_loader.py`
- `uv run pytest tests/unit -q`
- one bridge smoke proof that confirmed an empty scoped refresh does not create `~/.cache/qmd/`
- one earlier live end-to-end `poem_loop` run on Codex
- one later live `poem_loop` proof on Codex that saved memory on turn 7, searched and used it on turn 9, and still reached `done` on turn 10
- one live blank-repo `software_engineering_demo` run on Codex that reached
  `done`
- one live carry-forward `software_engineering_demo` run on Codex that reached
  `done`
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
4. enforce per-agent runtime MCP access instead of today's shared MCP config
5. decide later whether isolated Claude auth is worth the extra complexity

# Live Truth

Use this doc with:

- `docs/RALLY_MASTER_DESIGN.md`
- `docs/RALLY_COMMUNICATION_MODEL.md`
- `docs/RALLY_CLI_AND_LOGGING.md`
- `docs/RALLY_MEMORY.md`

Treat older planning docs as history only.
