---
title: "Rally CLI and Logging"
date: 2026-04-13
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/cli.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/run_events.py
  - src/rally/terminal/display.py
  - src/rally/adapters/codex/event_stream.py
  - src/rally/adapters/codex/launcher.py
  - tests/unit/test_cli.py
  - tests/unit/test_issue_ledger.py
  - tests/unit/test_launcher.py
  - tests/unit/test_run_events.py
  - tests/unit/test_codex_event_stream.py
---

# Summary

This file keeps the concrete CLI and logging rules in one place.
Use it with the master design and the Phase 4 runtime doc.
If this file and the code disagree, the code wins.

# What Rally Ships Today

## CLI

The current checked-in CLI is small and explicit.

### `rally run`

Current shape:

```bash
rally run <flow_name> [--new]
```

What it does today:

- loads the flow through `src/rally/services/flow_loader.py`
- creates a real active run
- when `--new` is passed, asks before it archives the current active run for the same flow
- creates the run shell under `runs/active/<run-id>/home/`
- opens the editor for a missing or blank `home/issue.md` on a real TTY when an editor is available
- strips the starter prompt back out before saving the issue
- still fails loud unless `home/issue.md` ends up with non-empty text
- prepares the full run home only after `home/issue.md` is ready
- opens a live color stream on a TTY
- falls back to plain text when stdout is not a TTY
- runs the current agent turn through Codex
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
rally resume <run-id>
```

What it does today:

- reloads the stored run
- opens the same issue editor path as `rally run` when `home/issue.md` is missing or blank on a real TTY
- refuses archived runs
- refuses done or blocked runs
- resumes sleeping runs only after their wake time
- reuses the saved Codex session id when one exists
- opens the same live stream rules as `rally run`
- advances the current agent by one turn

### `rally issue note`

Current shape:

```bash
rally issue note --run-id <run-id> [--text <markdown> | --file <path>]
```

If neither `--text` nor `--file` is passed, it reads from stdin.

What it does today:

- reads note text from one source
- rejects an empty note body
- appends a Rally-stamped note block to the run's `home/issue.md`
- writes a full snapshot into the run's `issue_history/`
- prints the updated issue path and snapshot path

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
After that, Rally appends:

- note blocks from `rally issue note`
- run-start records
- turn-result records
- blocked, sleeping, or done status records when they apply

The current note block format is:

```md
## Rally Note
- Run ID: `<run-id>`
- Time: `<utc-iso8601>`
- Source: `rally issue note`

<note body>
```

Snapshot behavior today:

- after each Rally-owned note append, Rally writes the full updated issue file
  into the run's `issue_history/`
- snapshot filenames use the UTC pattern
  `YYYYMMDDTHHMMSSffffffZ-issue.md`

## Codex Launch Env

The current Codex launch helper is small and real.

`src/rally/adapters/codex/launcher.py` builds only these env vars today:

- `CODEX_HOME`
- `RALLY_BASE_DIR`
- `RALLY_RUN_ID`
- `RALLY_FLOW_CODE`
- `RALLY_AGENT_SLUG`

The runner uses those values with this Codex launch shape:

```bash
codex exec \
  --json \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C <run-home> \
  --output-schema <schema-file> \
  -o <last-message-file>
```

The runtime also:

- injects the compiled `AGENTS.md` readback directly on stdin
- appends runtime prompt inputs when the flow declares a prompt-input command
- sets `project_doc_max_bytes = 0`
- saves the Codex session id per agent for later resume

## MCP Readiness Gap

Today Rally writes MCP entries into `config.toml` and seeds Codex auth links
into the run home.
That is only bootstrap behavior.
It is not yet the finished rule.

Rally does not yet prove that a required MCP can start, that its auth is
present and still valid, or that child agents will keep the same access.
The next runtime pass should add one clear readiness check and one clear
failure record that names the broken MCP and the reason.

## Logging Today

Current logging is richer, but still file-first.

What exists today:

- `run.yaml`
- `state.yaml`
- `home/issue.md`
- `issue_history/` full snapshots after Rally-owned issue writes
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
- Codex session start or resume events
- assistant output lines when Codex emits text chunks
- reasoning lines when Codex emits reasoning chunks
- tool start, success, and failure summaries when Codex exposes tool events
- token-use summaries
- stderr lines, warnings, and hard errors

Unknown Codex JSON events still stay in the raw per-turn `exec.jsonl` file.
Rally keeps them out of the live stream unless they look like warnings or
errors.

## Renderer Rules

The live operator view is a polished stream, not a full-screen TUI.

Today it does this:

- `rally run` and `rally resume` use the same renderer choice
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
- agent labels: blue
- reasoning: dim white
- tools: yellow
- final success state: green
- warnings: amber
- failures: red

## Remaining Gaps

The main operator-side gaps are now:

- a standalone `rally archive` command
- deeper stale-run diagnosis
- a replay or viewer command that can reload old history from `logs/events.jsonl`

# Canonical Reading Order

Use the docs in this order:

1. `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
2. this doc
3. `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
4. the current code in `src/rally/cli.py`, `src/rally/services/issue_ledger.py`,
   and `src/rally/adapters/codex/launcher.py`

That gives you:

- the stable law
- the detailed CLI and logging contract
- the runtime status
- the final truth of what is really shipped today
