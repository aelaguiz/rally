# Rally Run Timing

Rally is self-diagnosable. Every run emits a **per-handoff receipt** showing
where the last turn spent its time and where the run stands cumulatively, plus
four persistent artifacts on disk that every other surface reads from:

- `runs/<RUN>/timing.json` — cumulative snapshot. Overwritten at every
  terminal turn event (handoff, done, blocker, sleep).
- `runs/<RUN>/timing_turns.jsonl` — append-only, one line per completed turn.
- `runs/<RUN>/tool_calls.jsonl` — one line per paired tool call, with duration
  and a secret-scrubbed input digest.
- `runs/timings.ndjson` — workspace-level log, one line per completed run.

Timing is **always on**. There is no flag to enable it. The feature takes no
configuration.

## What fires the receipt

After every terminal turn kind (`handoff`, `done`, `blocker`, `sleep`), the
runner:

1. Reads `logs/events.jsonl` and computes a fresh `RunTiming` snapshot.
2. Overwrites `timing.json`. Appends the turn to `timing_turns.jsonl`.
   Rewrites `tool_calls.jsonl`. On `done`, appends a line to
   workspace-level `timings.ndjson`.
3. Emits a `SUMMARY` event (`kind=summary`, `code=SUMMARY`) through the
   normal event chain so displays and external watchers see it inline.

The receipt renders **before** routing to the next agent, so a user who stops
a run mid-flow at a handoff already has the accurate cumulative picture in
front of them — no separate "end of run" event is required.

## Receipt format

```
CUR-8 · turn 2 complete · track_scoper → track_scope_critic

this turn   12m16s  (7m10s tools · 5m06s model)   44 tools   26,503 out · 2.73M cached
            hot tools:    Bash 7m25s × 44 (16% err) · Glob 16s × 3 · Read 0.5s × 6
            hot commands: cd repos/psmo && …  27×  7m09s  3 err
                          python authoring_lens/cli.py …  2×  0.3s  2 err
                          uv run python scripts/catalog  5×  1.4s  1 err

cumulative  15m25s wall · 15m25s active · 0s idle
            2 turns · 2 agents · 62 tools · 7 errors (11.3%) · 35,389 out · 3.37M cached

artifacts   runs/active/CUR-8/timing.json
```

The first block (`this turn`) covers the turn that just finished. The second
block (`cumulative`) covers the whole run so far. The artifacts line points
to the authoritative file on disk.

At `done`, the header becomes `CUR-8 · done`. At `blocker`, it becomes
`CUR-8 · blocked`. At `sleep`, `CUR-8 · sleeping`.

## `timing.json` schema

Full serialization of the `RunTiming` dataclass
(`src/rally/domain/timing.py`). Top-level fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `run_id` | string | Rally run id. |
| `flow_code` | string | Three-letter flow code. |
| `run_status` | string | `running`, `done`, `blocked`, `sleeping`. |
| `last_turn_index` | int | Most recent turn index seen in events. |
| `wall_ms` | int | First event → last event in this run, in milliseconds. |
| `active_ms` | int | Sum of `turn.wall_ms` across all turns. |
| `idle_ms` | int | `wall_ms - active_ms - setup_ms`, clamped to 0. |
| `setup_ms` | int | Time spent inside `SETUP`/`SETUP OK` pairs. |
| `tokens` | object | Cumulative tokens across all `USAGE` events. |
| `turns[]` | list | Per-turn rollups (see below). |
| `per_agent[]` | list | Per-agent aggregate (across all turns the agent ran). |
| `top_tools[]` | list | Overall top tools by `total_ms`. |
| `top_commands[]` | list | Overall top commands by `input_digest`. |
| `flags[]` | list | Anomaly flags. See **Flags** below. |

Each `turns[]` entry:

| Field | Meaning |
| --- | --- |
| `turn_index` | 1-based turn index. |
| `agent_key`, `agent_slug` | The agent that ran the turn. |
| `kind` | `handoff`, `done`, `blocker`, `sleep`, or `interrupted`. |
| `started_at`, `ended_at` | ISO-8601 UTC timestamps. |
| `wall_ms`, `tool_ms`, `model_ms` | Time breakdown for the turn. |
| `tools_called`, `errors` | Count of paired tool calls and errors. |
| `tokens` | Token totals for this turn only. |
| `hot_tools[]`, `hot_commands[]` | Top-N rollups for the turn. |

## `tool_calls.jsonl` schema

One line per paired tool call:

| Field | Meaning |
| --- | --- |
| `turn_index` | Turn the call belongs to. |
| `agent_slug` | Agent that made the call. |
| `tool_name` | Normalized tool name (`Bash`, `Read`, etc.). |
| `tool_use_id` | Pairing key from the adapter. |
| `sub_kind` | `bash`, `read`, `edit`, `search`, `fetch`, `skill`, `sub_agent`, `mcp`, or `other`. |
| `dur_ms` | `ts_end − ts_start` in milliseconds. |
| `is_error` | Boolean. Tool ended in an error. |
| `exit_code` | Shell exit code when parseable, else `null`. |
| `input_digest` | First 120 chars of the tool's primary input, secret-scrubbed. |
| `output_tail` | First line of the tool's error output, if the call errored. |
| `ts_start`, `ts_end` | ISO-8601 UTC timestamps. |

## `timings.ndjson` schema (workspace-level)

One line per completed run, appended at `done`:

| Field | Meaning |
| --- | --- |
| `run_id`, `flow_code`, `run_status` | Run identity. |
| `last_turn_index` | Final turn index. |
| `wall_ms`, `active_ms`, `idle_ms`, `setup_ms` | Time budget. |
| `tokens` | Serialized `TurnTokens`. |
| `errors`, `tools_called` | Totals across the run. |
| `ts` | When the line was written. |

## Flags

Flags are **rule-based anomalies**, not model inferences. Every flag is a
`TimingFlag(code, severity, message, evidence)` record and is rendered inline
under the receipt. Rules live in `src/rally/services/run_timing_flags.py` and
are evaluated on every terminal turn event.

| Code | Severity | Trigger | Example message |
| --- | --- | --- | --- |
| `command_always_fails` | error | ≥2 calls of the same `input_digest` with 100% error rate | `` `python bad.py` 2/2 calls failed `` |
| `tool_error_rate` | warning | Any `(agent, tool)` with ≥3 calls and >10% error rate | `track_scoper Bash error rate 16% (7/44)` |
| `single_call_hot` | warning | Any single tool call longer than 60s | `Bash took 68s: ` `` `pytest -k slow` `` |
| `model_spin` | warning | Any turn with 0 tool calls and >120s wall time | `turn 2 (writer) ran 180s with 0 tool calls` |
| `retry_group` | info | Same `(turn, tool, input_digest)` fires ≥2× in one turn | `turn 3: ` `` `uv sync` ``  `fired 3× — possible retry` |
| `high_idle` | info | `wall / active > 3` and the run is not in step mode | `wall/active ratio 4.2× — run was mostly idle` |

Flags are sorted `error` → `warning` → `info`. The receipt renders up to six
flags; the rest are summarised as `(+N more)`.

`high_idle` is suppressed when the run was started with `--step`, because
step-mode wall time is dominated by the operator waiting between turns.

Each flag carries an `evidence` object with the raw numbers used to fire
the rule — handy when you want to dig without re-reading events.

## Cross-run trends

`runs/timings.ndjson` grows one line per completed run. View it with:

```
rally runs time                 # last 20 completed runs, all flows
rally runs time --flow CUR      # filter to one flow
rally runs time --last 5        # only the five most recent
```

The command prints a recent-run table plus p50 / p90 / mean for wall, active,
errors, tools, output tokens, and cached tokens. It never writes; the file
is produced by the normal per-handoff pipeline on `done`.

## Secret scrubbing

Before any `input_digest` is written to an event, a shared helper strips
likely secrets. Patterns redacted:

- `--password=…`, `--token=…`, `--secret=…`, `--api-key=…` flag values
- `-H "Authorization: …"` headers
- `API_KEY=…`, `GH_TOKEN=…`, `GITHUB_TOKEN=…`, `AWS_SECRET_ACCESS_KEY=…`,
  `AWS_SESSION_TOKEN=…`, `OPENAI_API_KEY=…`, `ANTHROPIC_API_KEY=…` assignments
- `AKIA…` AWS access key prefixes
- `xoxb-…` / `xoxa-…` / `xoxp-…` / `xoxr-…` / `xoxs-…` Slack tokens
- `sk-…` OpenAI-style API keys

The shared regex set lives in `src/rally/services/tool_digest.py`.

## Surfaces that read from timing

- **Per-handoff stream receipts** — rendered inline by
  `src/rally/terminal/summary.py`, consumed by `PlainStreamDisplay` and
  `RichStreamDisplay`.
- **`rally status`** — reads `timing.json` mid-run to show a three-line time
  footprint. Silently omitted when `timing.json` is not yet present.
- **`rally watch`** — live per-turn counter using `TOOL OK` events, replaced
  by the full receipt at every handoff.
- **`rally runs time`** — workspace-wide trend view over `runs/timings.ndjson`
  (filterable by flow, windowable with `--last`).

## Implementation map

| File | Role |
| --- | --- |
| `src/rally/services/run_timing.py` | Aggregator (`compute_run_timing`, `write_run_timing`, `update_tool_calls`). |
| `src/rally/services/run_timing_flags.py` | Anomaly rule functions returning `TimingFlag` records. |
| `src/rally/domain/timing.py` | `RunTiming`, `TurnTiming`, `AgentTiming`, `ToolCallRollup`, `CommandRollup`, `TurnTokens`, `TimingFlag` dataclasses. |
| `src/rally/services/tool_digest.py` | Shared `make_input_digest` helper with secret scrub. |
| `src/rally/adapters/claude_code/event_stream.py` | Emits enriched `TOOL` / `TOOL OK` events carrying `tool_use_id`, `input_digest`, `is_error`, `exit_code`. |
| `src/rally/adapters/codex/event_stream.py` | Same enrichment for `CMD` / `MCP` / `COLLAB` events. |
| `src/rally/terminal/summary.py` | `format_summary(timing, *, turn, style)` renderer. |
| `src/rally/services/runner.py` | Fires the timing pipeline at every terminal turn event. |
| `src/rally/services/run_status.py` | Adds the three-line time footprint to `rally status <RUN>`. |
| `src/rally/services/run_watch.py` | Live per-turn counter and inline receipt rendering for `rally watch`. |
| `src/rally/services/run_trends.py` | `rally runs time` — reads `timings.ndjson` and prints trends. |

## Invariants

- **Never control truth.** Timing data never drives routing. Routing lives in
  the final JSON turn result, always.
- **Derived, never primary.** The timing snapshot is recomputed from
  `events.jsonl` at every terminal turn. It is an index over primary data, not
  a new authoritative store.
- **Idempotent.** `update_tool_calls` rewrites `tool_calls.jsonl` from scratch
  on every call. A partial write never leaves a half-populated file.
- **Fail silent, not fail loud.** If timing aggregation raises, the run
  continues and the receipt is simply not emitted. Telemetry must never break
  a run.
