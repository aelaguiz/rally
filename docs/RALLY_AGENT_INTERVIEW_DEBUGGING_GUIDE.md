---
title: "Rally Agent Interview Debugging Guide"
status: shipped
doc_type: operator_guide
related:
  - README.md
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - src/rally/cli.py
  - src/rally/services/interview.py
  - src/rally/adapters/claude_code/interview.py
  - src/rally/adapters/codex/interview.py
  - src/rally/services/home_materializer.py
---

# Summary

Use `rally interview` when you want to talk to an agent about its doctrine
without letting that chat change the live run.

This guide explains:

- when to use a fresh interview
- when to use `--fork`
- what Rally writes under `home/interviews/`
- how Claude and Codex differ under the hood
- how to leave the chat and safely resume the real run

The CLI stays simple:

```bash
rally interview <run-id> [--agent <slug>] [--fork]
```

# What This Command Does

`rally interview` opens a read-only diagnostic chat for one agent in one run.

The agent gets a generated `INTERVIEW.md` sidecar that says, in plain words,
that it is in interview mode, that it must not do its normal job, and that it
should explain its real doctrine instead of following it.

This chat is not a Rally turn.
It does not write a turn result.
It does not hand off.
It does not mark the run done.
It does not append a note to `home:issue.md`.

The live work-session record at `home/sessions/<agent>/session.yaml` stays the
normal source of truth for later `rally resume`.

Assistant text streams back to the terminal as it arrives.
Rally also writes normalized interview rows into the run log so the chat shows
up in the same `logs/events.jsonl` archaeology path as the rest of the run.

# Pick The Right Mode

Use a fresh interview when:

- you want to ask about the agent's rules in general
- you do not need the live in-flight session state
- there is no saved live session yet
- you want the safest and simplest path

Use `--fork` when:

- you want to inspect what a saved live session already knows
- you need to ask why the agent got confused mid-run
- you want a safe branch of the live session
- you do not want to risk changing the session Rally will resume later

If `--fork` fails because there is no saved live session, use a fresh interview
or let the run reach that agent once and then try again.

# Basic Commands

Fresh interview for the current agent:

```bash
rally interview DMO-1
```

Fresh interview for one named agent:

```bash
rally interview DMO-1 --agent change_engineer
```

Fork the saved live session into interview mode:

```bash
rally interview DMO-1 --fork
```

Inside the chat:

- type a question and press Enter
- type `/exit` to stop
- `exit` and `quit` also stop

Good questions:

- `What part of your instructions is hard to follow?`
- `Which rule made you stop?`
- `What do you think home:issue.md is asking you to do?`
- `Which instruction conflicts with the current repo state?`

# How Rally Picks The Agent

If you pass `--agent <slug>`, Rally uses that slug.

If you do not pass `--agent`, Rally tries the run's current agent.

If the run has no current agent, Rally fails loud and tells you to pass
`--agent <slug>`.

Archived runs are rejected.

# Where The Files Go

Each interview gets its own run-owned folder:

```text
runs/active/<run-id>/home/interviews/<agent-slug>/<interview-id>/
```

Example:

```text
runs/active/DMO-1/home/interviews/change_engineer/interview-001/
```

Rally writes these files there:

- `prompt.md`
  - the exact compiled interview readback that was used for the chat
  - includes the generated interview doctrine plus run facts such as mode,
    agent slug, and the live session id when `--fork` was used
- `session.yaml`
  - Rally's diagnostic session record
  - includes `mode`, `diagnostic_session_id`, `source_session_id`, and `cwd`
- `launch.json`
  - the adapter launch proof for the first question
  - shows the command, cwd, and the small set of kept env vars such as
    `RALLY_*` and `CODEX_HOME` when relevant
- `transcript.jsonl`
  - normalized user and assistant messages in order
- `raw_events.jsonl`
  - raw adapter stream lines for the interview
  - Claude stores stream-json lines
  - Codex stores app-server JSON-RPC responses and notifications
- `stderr.log`
  - adapter stderr for the interview session

The live work-session files stay in:

```text
home/sessions/<agent>/
```

Do not confuse the interview record with the live session record.

Rally also appends interview rows to the normal run log:

- `runs/active/<run-id>/logs/events.jsonl`
  - normalized `USER`, `LAUNCH`, `ASSIST`, and `CLOSE` rows for the interview
- `runs/active/<run-id>/logs/rendered.log`
  - the same interview lifecycle and message summary in plain text

# How To Read The Artifacts

Start with `prompt.md`.
That tells you exactly what the agent was asked to do in interview mode.

Then read `session.yaml`.
That tells you whether the chat was fresh or forked and which diagnostic
session id Rally saved.

Then read `transcript.jsonl`.
That is the clean human chat log.

Then read `logs/events.jsonl` if you need the interview in the wider run
timeline.

Then read `raw_events.jsonl` and `stderr.log` only if you need adapter-level
detail.

Use `launch.json` when you need proof of the exact adapter launch boundary.

# Claude And Codex Differences

The human CLI is the same on both adapters.
The backend is different.

Claude path:

- Rally uses `claude -p`
- fresh interviews inject the interview doctrine as the system prompt
- later turns resume the saved diagnostic `session_id`
- fork mode uses `--resume <live-session> --fork-session`
- Rally clamps the tool surface to inspect-only tools and keeps `--bare`

Codex path:

- Rally keeps normal work turns on `codex exec`
- interview mode uses a diagnostic-only `codex app-server --listen stdio://`
  client
- fresh interviews start a new diagnostic thread with `thread/start`
- fork mode branches the saved live thread with `thread/fork`
- later questions stay on that saved diagnostic `thread_id`
- Rally keeps the thread in read-only sandbox mode under the run home

The point of this split is safety.
Rally does not fake Codex forking on top of the wrong surface.

# Fail-Loud Cases

`rally interview` should stop with a clear error when:

- the run id does not exist
- the run is archived
- the chosen agent slug is unknown
- there is no current agent and no `--agent` flag was given
- `--fork` was requested but no saved live session exists
- the adapter stream fails, exits early, or returns bad JSON

This is on purpose.
Rally should not silently heal diagnostic state.

# Safe Exit And Resume

When you are done:

1. Type `/exit`.
2. Inspect `home/interviews/...` if needed.
3. Resume the real run with the usual command.

Example:

```bash
rally resume DMO-1
```

The live run should resume from the normal live session record, not from the
diagnostic interview session.

# Practical Debug Flow

Use this short loop when an agent seems confused:

1. Start with `rally interview <run-id>`.
2. Ask what rule is hard to follow and what file it thinks matters most.
3. If you need live session context, rerun with `--fork`.
4. Inspect `prompt.md` and `transcript.jsonl`.
5. If the problem is instruction wording, fix the `.prompt` source and rebuild.
6. If the problem is runtime behavior, inspect `launch.json`, `raw_events.jsonl`,
   and `stderr.log`.
7. Resume the run with `rally resume <run-id>`.

# Related Docs

Use these docs with this guide:

- [README.md](../README.md)
- [RALLY_MASTER_DESIGN.md](RALLY_MASTER_DESIGN.md)
- [RALLY_RUNTIME.md](RALLY_RUNTIME.md)
- [RALLY_CLI_AND_LOGGING.md](RALLY_CLI_AND_LOGGING.md)
- [RALLY_COMMUNICATION_MODEL.md](RALLY_COMMUNICATION_MODEL.md)
