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
  - src/rally/services/event_log.py
  - src/rally/adapters/codex/launcher.py
  - tests/unit/test_cli.py
  - tests/unit/test_issue_ledger.py
  - tests/unit/test_launcher.py
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
rally run <flow_name> --brief-file <path> [--preflight-only]
```

What it does today:

- loads the flow through `src/rally/services/flow_loader.py`
- checks that the brief file exists
- prints a preflight success line only when `--preflight-only` is used
- otherwise creates a real active run
- prepares the run home
- runs the current agent turn through Codex
- prints the resulting run status line

Current limits:

- it does not archive old runs
- it does not try to auto-heal stale run state

### `rally resume`

Current shape:

```bash
rally resume <run-id>
```

What it does today:

- reloads the stored run
- refuses done or blocked runs
- resumes sleeping runs only after their wake time
- reuses the saved Codex session id when one exists
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

## Logging Today

Current logging is intentionally thin.

What exists today:

- `run.yaml`
- `state.yaml`
- `home/issue.md`
- `issue_history/` full snapshots after Rally-owned issue writes
- `logs/events.jsonl`
- `home/sessions/<agent>/session.yaml`
- `home/sessions/<agent>/turn-<n>/exec.jsonl`
- `home/sessions/<agent>/turn-<n>/stderr.log`
- `home/sessions/<agent>/turn-<n>/last_message.json`

What does not exist yet:

- `logs/rendered.log`
- filtered per-agent event logs under `logs/agents/`
- adapter-launch JSON summaries
- `rally archive`

# Detailed Contract Recovered From History

These details came from older master-design revisions.
Some are still good next steps, but they are not all shipped today.

## Small CLI, Loud Failure

The older design was very clear that the main operator surface should stay
small:

```bash
rally run <flow> <issue-file-or-brief>
rally resume <run-id>
rally archive <run-id>
```

The same older design was also clear that `run` should fail loud on dirty or
confusing state instead of trying to heal it in the background.

Examples the old design named:

- an existing active-flow lock
- a half-initialized run directory
- disagreement between `run.yaml`, `state.yaml`, and the filesystem
- a previous run that still needs explicit archive or closeout

The important rule was simple:
do not guess, do not auto-heal, and do not hide cleanup behind magic behavior.

## Explicit Archive

Older master-design text treated `archive` as an explicit operator action.
It was not meant to be background cleanup.

The intended archive rule was:

- preserve the run files
- report dirty state
- clear active-flow state only when it is safe
- refuse destructive cleanup

## Run-Local Log Layout

Older master-design text also had a much more specific logging layout.
The intended per-run shape was:

```text
runs/<run-id>/
  logs/
    events.jsonl
    rendered.log
    agents/
      <agent>.jsonl
    adapter_launch/
      <agent>.json
  issue_history/
    <timestamp>-issue.md
```

The intended meaning of those files was:

- `logs/events.jsonl`
  - the merged structured event stream for the whole run
- `logs/agents/*.jsonl`
  - filtered per-agent event history
- `logs/rendered.log`
  - a flattened human-readable view for grep and quick review
- `logs/adapter_launch/*.json`
  - the proof record for the actual launch contract used for each turn
- `issue_history/`
  - full issue-ledger snapshots after each Rally-owned append

The older logging contract was also more specific about completeness.
`events.jsonl` was meant to capture, at minimum:

- Rally lifecycle events
- setup-script start, finish, and output
- adapter wake and resume events
- reasoning trace events
- tool-call start, arguments, streamed output chunks, completion, and failure
- any other adapter-visible payload the operator could have watched live
- handoff events
- archive events
- warnings and hard errors

That older rule is still useful:
if the operator could have seen it happen in the runner, Rally should mirror it
into the run-local event history.

## Renderer Backed By History

Older master-design text did not want a dumb stdout tail.
It wanted the live renderer to be backed by the structured event history.

That old rule still matters because it explains why Rally wants both:

- structured append-only events for archaeology and filtering
- a human-readable rendered log for quick review

The renderer detail that was lost in the trim was this:
history should drive the UI, not the other way around.

## Renderer Behavior And Controls

The older master-design text also described the renderer behavior much more
concretely.
The intended rules were:

- `rally run` and `rally resume` should open the same renderer
- on startup, the renderer should load existing history from `logs/events.jsonl`
- after loading history, it should follow live events
- visibility toggles should apply to both past and future events

The intended keyboard controls were:

- `T`
  - toggle tool-call visibility
- `R`
  - toggle reasoning-trace visibility
- `Q`
  - quit the renderer without stopping the run

The intended renderer layout was:

- top status bar
  - run id, flow, current agent, run state, elapsed time
  - current filters such as `tools:on/off` and `reasoning:on/off`
- main event pane
  - chronological event stream with agent badges and timestamps
- bottom hint bar
  - compact key hints such as `T tools`, `R reasoning`, `Q quit`

## Renderer Color Rules

The old master design had explicit terminal color guidance.
Those colors were for the live renderer, not for `rendered.log`.

- timestamps
  - dim gray
- flow and lifecycle events
  - cyan
- current agent badges
  - blue
- reasoning traces
  - dim white
- tool calls
  - yellow
- successful tool completion
  - green
- warnings
  - amber
- failures and hard errors
  - red

## Renderer Line Format

The old master design also had a concrete event-line style.
Each line was meant to stay compact and easy to scan.

The intended shape was:

```text
14:41:10  01_core_dev_lead  WAKE      initial wake
14:41:14  01_core_dev_lead  REASON    tracing root cause in subscription flow
14:41:18  01_core_dev_lead  TOOL      rg -n "subscription" apps/mobile
14:41:19  01_core_dev_lead  TOOL OK   12 matches
14:44:02  01_core_dev_lead  HANDOFF   -> 02_bugfix_engineer  artifact=artifacts/fix-plan.md
```

The useful detail here is not the sample agent names.
It is the formatting rule:

- timestamp first
- stable agent label second
- short event code third
- compact human-readable payload last

That line shape belongs in the renderer and the plain-text rendered transcript.
The structured event file should still keep richer machine-readable payloads.

## Resume As Explicit Recovery

Older master-design text treated `resume` as the named recovery path after:

- a deliberate stop
- a crash
- an interrupted run

That older design also expected resume to stay honest about session reuse:

- resume only when the saved session still matches the same run and home
- keep resume separate from the initial wake path
- preserve the run directory and prior logs instead of rewriting history

# Current Gap List

This is the short list of the detail that exists in history and design docs but
is not yet real in code:

- `archive` command
- real `run` execution
- real `resume` execution
- active-run lock handling
- `run.yaml` and `state.yaml` write paths from the CLI
- `logs/events.jsonl`
- per-agent log mirrors
- `logs/rendered.log`
- adapter launch proof files
- renderer replay or whole-history viewing

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
