---
title: "Rally CLI and Logging"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - src/rally/cli.py
  - src/rally/adapters/base.py
  - src/rally/adapters/claude_code/launcher.py
  - src/rally/adapters/claude_code/event_stream.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/run_events.py
  - src/rally/services/final_response_loader.py
  - src/rally/terminal/display.py
  - src/rally/adapters/codex/launcher.py
  - tests/unit/test_cli.py
  - tests/unit/test_issue_ledger.py
  - tests/unit/test_launcher.py
  - tests/unit/test_run_events.py
  - tests/unit/test_codex_event_stream.py
  - tests/unit/test_claude_code_event_stream.py
  - tests/unit/test_claude_code_launcher.py
---

# Summary

This file keeps the concrete CLI and logging rules in one place.
Use it with the master design and the runtime doc.
If this file and the code disagree, the code wins.
Non-review flows can still opt out of the shared `agent_issues` default by
declaring their own output shape over the shared schema in prompt source. CLI
and runtime still read one final JSON path either way.

# What Rally Ships Today

## CLI

The current checked-in CLI is small and explicit.

### `rally workspace sync`

Current shape:

```bash
rally workspace sync
```

What it does today:

- resolves the current Rally workspace from `pyproject.toml`
- syncs Rally-owned built-ins into the workspace at
  `stdlib/rally/`, `skills/rally-kernel/`, and `skills/rally-memory/`
- prints one short result line with the synced paths
- does not create a run
- does not create `runs/active/<run-id>/`
- does not prepare a run home
- does not launch an adapter

Current limits:

- it only syncs Rally-owned built-ins
- it does not rebuild a flow or skill
- it does not replace `rally run` or `rally resume`

If the current workspace is the Rally source repo itself, the command is a
no-op and says the workspace already owns those built-ins.

### `rally run`

Current shape:

```bash
rally run <flow_name> [--new]
```

What it does today:

- reads the flow code from `flow.yaml`
- takes the flow lock and rebuilds that flow's compiled agents through Doctrine
- loads the rebuilt flow through `src/rally/services/flow_loader.py`
- creates a real active run
- when `--new` is passed, asks before it archives the current active run for the same flow
- creates the run shell under `runs/active/<run-id>/home/`
- opens the editor for a missing or blank `home/issue.md` on a real TTY when an editor is available
- strips the starter prompt back out before saving the issue
- still fails loud unless `home/issue.md` ends up with non-empty text
- prepares the full run home only after `home/issue.md` is ready
- refreshes `home/agents/`, `home/sessions/<agent>/skills/`, `home/mcps/`,
  and adapter-owned bootstrap files from current repo state before the next
  turn starts
- activates the current agent's live `home/skills/` tree before that turn
- runs flow setup only the first time the run home becomes ready
- loads any flow-declared runtime prompt-input sections before each turn
- blocks `handoff` or `done` when a flow-declared guarded git repo is missing,
  not a git work tree, or dirty
- opens a live color stream on a TTY
- falls back to plain text when stdout is not a TTY
- keeps running turns through the selected adapter across handoffs
- stops only when the run reaches `done`, hits a blocker, hits a runtime failure such as a timeout, or hits the per-command turn cap
- prints the resulting run status line

Current limits:

- it does not ship a standalone `rally archive` command yet
- it does not try to auto-heal stale run state

If the issue file is missing or blank on a real TTY, `rally run` opens the
editor and keeps going after the operator saves real issue text.
If the shell is not interactive, no editor is available, or the editor closes
without real issue text, `rally run` stops with exit code `2` after creating
the run shell. The operator writes `home/issue.md` and then uses
`rally resume <run-id>`.
If `--new` finds an active run for that flow, Rally asks before it archives
that run. If the operator says yes, Rally moves that run under
`runs/archive/` and starts a fresh active run. If the shell is not
interactive, Rally refuses `--new` because it cannot ask.

### `rally resume`

Current shape:

```bash
rally resume <run-id> [--edit|--restart]
```

What it does today:

- reloads the stored run
- takes the flow lock and rebuilds that run's flow through Doctrine before loading compiled agents
- when `--edit` is passed, opens the current `home/issue.md` in place before Rally tries the turn
- when `--restart` is passed, asks before Rally archives the old run and starts a fresh run from the original issue
- opens the same issue editor path as `rally run` when `home/issue.md` is missing or blank on a real TTY
- refuses archived runs
- refuses done runs for plain resume
- lets a blocked run try again after `--edit` saves a non-empty issue
- lets a blocked or done run restart from the original issue when `--restart` is confirmed
- can still resume a legacy sleeping run after its wake time
- reuses the saved adapter session id when one exists
- opens the same live stream rules as `rally run`
- keeps going across handoffs until Rally reaches a real stop point
- refreshes `home/agents/`, `home/sessions/<agent>/skills/`, `home/mcps/`,
  and adapter-owned bootstrap files before the next turn starts
- activates the current agent's live `home/skills/` tree before that turn
- does not rerun flow setup after the run home is already ready
- reloads any flow-declared runtime prompt-input sections before each turn
- blocks `handoff` or `done` when a flow-declared guarded git repo is missing,
  not a git work tree, or dirty

If `--edit` is passed, Rally edits the real `home/issue.md` file.
It does not seed or strip the starter prompt for that path.
If the operator saves a blank issue, Rally stops and waits for a non-empty
`home/issue.md`.
If the shell is not interactive or no editor is available, Rally refuses
`resume --edit`.
If the operator changed the issue text, Rally appends one
`## user edited issue.md` block to the end of `home/issue.md` with a fenced
unified diff before the run resumes.
If `--restart` is passed, Rally refuses to edit in place. It asks for
confirmation on a real TTY, archives the old run, restores only the original
issue into a fresh run with a new run id, and starts that new run from turn 0.

### `runtime.max_command_turns`

Each flow now sets `runtime.max_command_turns` in `flow.yaml`.
This is a hard cap on how many turns one `rally run` or `rally resume`
command can start before Rally stops and blocks the run.

The cap is checked before the next turn starts.
If Rally hits it, Rally keeps the next agent as current, writes a clear
`Rally Blocked` record, and tells the operator why it stopped.

### `runtime.prompt_input_command`

A flow may declare one `runtime.prompt_input_command` in `flow.yaml`.

What Rally does today:

- runs that command before each turn
- runs it from the flow root, not from the run home
- expects one JSON object whose top-level keys become appended prompt-input
  section titles
- passes current run facts through env vars:
  - `RALLY_AGENT_KEY`
  - `RALLY_AGENT_SLUG`
  - `RALLY_CLI_BIN`
  - `RALLY_FLOW_CODE`
  - `RALLY_ISSUE_PATH`
  - `RALLY_RUN_HOME`
  - `RALLY_RUN_ID`
  - `RALLY_WORKSPACE_DIR`
- writes one `INPUTS` lifecycle event before the command and one `INPUTS OK`
  or failure event after it

Today Rally uses that path in `software_engineering_demo` to feed grounding
with current branch facts, carry-forward source, and review-basis facts.

### `runtime.guarded_git_repos`

A flow may declare one or more run-home-relative repo paths in
`runtime.guarded_git_repos`.

What Rally does today:

- checks those paths before it accepts `handoff` or `done`
- treats a missing dir, a non-git dir, or a dirty worktree as a blocker
- writes the failure into `home/issue.md` as `Rally Blocked`
- leaves the current agent as current so the operator can inspect the same turn

Today `software_engineering_demo` uses this to guard `repos/demo_repo`.

### `rally issue note`

Current shape:

```bash
rally issue note --run-id <run-id> [--field key=value ...] [--text <markdown> | --file <path>]
```

If neither `--text` nor `--file` is passed, it reads from stdin.

What it does today:

- reads note text from one source
- accepts repeatable flat note fields through `--field key=value`
- rejects malformed note fields, duplicate keys, invalid key names, empty values, and field values that break the one-line header format
- rejects an empty note body
- appends a Rally-stamped note block to the run's `home/issue.md`
- adds `- Turn: \`N\`` automatically when Rally launched the current turn
- writes a full snapshot into the run's `issue_history/`
- prints the updated issue path and snapshot path

### `rally memory`

Current shape:

```bash
rally memory search --run-id <run-id> [--agent-slug <slug>] --query "<text>" [--limit N]
rally memory use --run-id <run-id> [--agent-slug <slug>] <memory-id>
rally memory save --run-id <run-id> [--agent-slug <slug>] [--text "<markdown>" | --file <path>]
rally memory refresh --run-id <run-id> [--agent-slug <slug>]
```

What it does today:

- resolves memory scope from the run's flow code plus the compiled agent slug carried into runtime state
- lets `--agent-slug` override the current agent when the operator needs a different scoped memory view
- keeps durable memory truth in markdown files under `runs/memory/entries/<flow_code>/<agent_slug>/`
- keeps QMD state repo-local under `runs/memory/qmd/index.sqlite` and `runs/memory/qmd/cache/`
- calls QMD only through the pinned bridge at `tools/qmd_bridge/`
- fails loud if the bridge is missing, returns bad JSON, or QMD fails

`rally memory search` today:

- searches only the current flow-agent scope
- prints a short ranked hit list with the canonical memory id, lesson title, and a short `When This Matters` snippet
- does not append to `home/issue.md`
- writes a first-class memory event in the canonical runtime stream

`rally memory use` today:

- reads one scoped markdown memory file
- prints the memory body
- writes a first-class memory event in the canonical runtime stream
- does not append to `home/issue.md`

`rally memory save` today:

- reads memory markdown from stdin, `--text`, or `--file`
- requires the shared three-section body with `# Lesson`, `# When This Matters`, and `# What To Do`
- writes or updates one markdown memory file
- refreshes only the scoped QMD collection
- writes a first-class memory event in the canonical runtime stream
- does not append to `home/issue.md`

`rally memory refresh` today:

- rebuilds the scoped QMD collection from the markdown source files
- is the repair path when QMD state drifts or is cleared
- writes a first-class memory event in the canonical runtime stream

### Exit behavior

The CLI error model is already simple:

- success returns exit code `0`
- Rally-owned errors print `error: ...` to stderr and return exit code `2`

## Issue Ledger And Snapshots

Rally writes both the issue ledger and `logs/events.jsonl`.

`src/rally/services/issue_ledger.py` enforces a narrow contract:

- the run must exist at either `runs/active/<run-id>/run.yaml` or `runs/archive/<run-id>/run.yaml`
- the `id` in `run.yaml` must match the requested run id
- Rally only writes to the run's `home/issue.md`
- Rally rejects any other `issue_file` path even if `run.yaml` names it

The issue file starts with the operator brief exactly as entered.
Rally does not also write a shared `operator_brief.md` sidecar or accept a
separate startup brief path.
When Rally appends its first own block, it inserts one hidden Markdown comment,
`<!-- RALLY_ORIGINAL_ISSUE_END -->`, right before that first block. Rally uses
that marker, or the earliest issue snapshot when one exists, to recover the
original issue for `resume --restart`.
After that, Rally appends:

- note blocks from `rally issue note`
- review-note blocks from `rally runtime review` when Rally consumes a review-native final response
- `resume --edit` diff blocks when the operator changed `home/issue.md`
- run-start records
- turn-result records, including `Agent Issues: ...` when a shared final response sends that passive field
- blocked or done status records when they apply

Rally writes one Markdown thematic break, `---`, between Rally-owned blocks.
It does not add a leading divider at the top of the file.

If an agent returns `kind: sleep`, Rally records that sleep request in the
turn-result block and then blocks the run.
It does not write a `Rally Sleeping` record for new chained runs yet.

The current Rally note block format is:

```md
## Rally Note
- Run ID: `<run-id>`
- Turn: `<turn-number>`
- Time: `<utc-iso8601>`
- Source: `rally issue note` or `rally runtime review`
- Field kind: `producer_handoff`  optional on `rally issue note` blocks
- Field lane: `producer`  optional on `rally issue note` blocks

<note body>
```

Turn-scoped runtime blocks use the same optional `- Turn:` metadata line.
That includes `Rally Turn Result`, `Rally Done`, `Rally Blocked`, and
`Rally Sleeping` when the block belongs to one active turn.
Non-turn blocks such as `Rally Run Started`, `Rally Archived`, and
`user edited issue.md` stay unnumbered.

Snapshot behavior today:

- after each Rally-owned note append, Rally writes the full updated issue file
  into the run's `issue_history/`
- snapshot filenames use the UTC pattern
  `YYYYMMDDTHHMMSSffffffZ-issue.md`

## Adapter Launch Env

The current shared launch-env path is small and real.

`src/rally/adapters/base.py` builds these shared env vars today:

- `RALLY_WORKSPACE_DIR`
- `RALLY_CLI_BIN`
- `RALLY_RUN_ID`
- `RALLY_FLOW_CODE`
- `RALLY_AGENT_SLUG`
- `RALLY_TURN_NUMBER`

Adapter-specific launchers then add their own narrow extras:

- Codex adds `CODEX_HOME`
- Claude adds `ENABLE_CLAUDEAI_MCP_SERVERS=false`

The runner uses those values with these current launch shapes:

```bash
codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C <run-home> \
  --output-schema <schema-file> \
  -o <last-message-file>
```

```bash
claude -p \
  --output-format stream-json \
  --verbose \
  --permission-mode dontAsk \
  --mcp-config <run-home>/claude_code/mcp.json \
  --strict-mcp-config \
  --tools <explicit-list> \
  --allowedTools <explicit-list> \
  --json-schema <schema-text>
```

The runtime also:

- injects the refreshed run-home `AGENTS.md` readback directly on stdin
- appends runtime prompt inputs when the flow declares a prompt-input command
- keeps Codex project-doc discovery off with `project_doc_max_bytes = 0`
- saves one adapter session id per agent for later resume
- uses `RALLY_TURN_NUMBER` so in-turn `rally issue note` calls can stamp the
  right turn without asking the agent to manage that metadata

## MCP Readiness

Today Rally refreshes adapter bootstrap on each `run` or `resume`.
For Codex that still means `config.toml` plus auth links.
For Claude that now means generated `home/claude_code/mcp.json`, the
`home/.claude/skills` link, and `ENABLE_CLAUDEAI_MCP_SERVERS=false`.
For Codex, Rally now also runs one readiness check before agent work starts.
It marks the projected Codex MCP set as `required = true`, checks visibility
through `codex mcp get/list`, blocks any non-usable streamable HTTP auth
state, and probes stdio launchers with a short bounded start check.

If one of those checks fails, Rally blocks before the turn starts and writes
one failure record that names the broken MCP and the failed check. Broader
per-agent MCP isolation is still later work.

## Logging Today

Current logging is richer, but still file-first.

What exists today:

- `run.yaml`
- `state.yaml`
- `home/issue.md`
- `issue_history/` full snapshots after Rally-owned issue writes
- `runs/memory/entries/` durable memory markdown
- `runs/memory/qmd/index.sqlite`
- `runs/memory/qmd/cache/`
- `logs/events.jsonl`
- `logs/agents/<agent>.jsonl`
- `logs/rendered.log`
- `logs/adapter_launch/turn-<n>-<agent>.json`
- `home/sessions/<agent>/session.yaml`
- `home/sessions/<agent>/turn-<n>/exec.jsonl`
- `home/sessions/<agent>/turn-<n>/stderr.log`
- `home/sessions/<agent>/turn-<n>/last_message.json`

What does not exist yet:

- a standalone `rally archive` command

## Event Coverage Today

The shipped event path now follows one rule:
if Rally can show it live, Rally should write it to run-local files from the
same event stream.

That event stream now covers:

- Rally lifecycle events such as run create, resume, home prep, setup, prompt-input load, launch, and final turn status
- first-class memory rows for `search`, `use`, `save`, and `refresh`
- adapter session start or resume events
- assistant output lines when an adapter emits text chunks
- reasoning summary lines when an adapter exposes them
- tool start, success, and failure summaries when an adapter exposes them
- token-use summaries
- stderr lines, warnings, and hard errors

Unknown adapter JSON events still stay in the raw per-turn `exec.jsonl` file.
Rally keeps them out of the live stream unless they look like warnings or
errors.

## Renderer Rules

The live operator view is a polished stream, not a full-screen TUI.

Today it does this:

- `rally run` and `rally resume` use the same renderer choice
- the startup header shows run id, flow, flow code, model, thinking level, adapter, start agent, and agent count
- TTY output gets Rich color and spacing
- non-TTY output falls back to plain text with the same event order
- `logs/rendered.log` uses the same line format as the plain fallback

The line format stays compact:

```text
14:41:10  01_scope_lead        TOOL      rg -n "page" src
14:41:11  01_scope_lead        TOOL OK   shell: 12 matches
14:41:12  01_scope_lead        HANDOFF   Handed off to `02_change_engineer`.
```

The color rules are still simple:

- timestamps: dim
- Rally lifecycle: cyan
- agent labels: per-agent background colors in flow order on a TTY
- reasoning summaries: magenta, with indented detail lines when an adapter
  sends more than one summary line
- memory rows: teal, with short detail lines for hits, memory ids, paths, or index counts
- tool traces: bright blue, with indented detail lines for short args, results, exit codes, or changed paths
- final success state: green
- warnings: amber
- failures: red

`logs/rendered.log` still keeps the plain one-line format. The rich detail rows
only show up in the live TTY stream.

Rally shows the reasoning summary that the adapter stream exposes today. It
does not show raw chain-of-thought.

## Remaining Gaps

The main operator-side gaps are now:

- a standalone `rally archive` command
- deeper stale-run diagnosis
- a replay or viewer command that can reload old history from `logs/events.jsonl`

# Canonical Reading Order

Use the docs in this order:

1. `docs/RALLY_MASTER_DESIGN.md`
2. this doc
3. `docs/RALLY_RUNTIME.md`
4. the current code in `src/rally/cli.py`, `src/rally/services/issue_ledger.py`,
   `src/rally/adapters/base.py`, and the adapter launchers

That gives you:

- the stable law
- the detailed CLI and logging contract
- the runtime status
- the final truth of what is really shipped today
