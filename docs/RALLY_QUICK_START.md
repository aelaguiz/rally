---
title: "Rally Quick Start"
status: active
doc_type: tutorial
related:
  - README.md
  - docs/RALLY_PRINCIPLES.md
  - docs/FLOW_YAML_REFERENCE.md
  - docs/TURN_RESULT_CONTRACT.md
  - flows/software_engineering_demo/
---

# Rally Quick Start

This walks you from an empty repo to a first Rally run you can inspect
on disk. It keeps the scaffold minimal: one flow, one agent, one
turn-result schema, one setup script. If you want to jump straight into
a shipped example, read
[`flows/software_engineering_demo/`](../flows/software_engineering_demo/)
instead.

## Prerequisites

- Python 3.14 or newer.
- `uv` (or a plain virtualenv).
- `rally-agents` installed, either as a tool or as a dev dep:

```bash
uv tool install rally-agents
# or, inside a repo-local env:
uv add --dev rally-agents
```

Confirm:

```bash
rally --help
```

## Step 1 — Scaffold The Workspace

A Rally workspace is your host repo with the fixed top-level folders
and `pyproject.toml` config:

```text
your-repo/
├── flows/
├── skills/
├── mcps/
├── stdlib/
├── runs/
└── pyproject.toml
```

In `pyproject.toml`:

```toml
[project]
name = "hello-rally"
version = "0.1.0"
requires-python = ">=3.14"

[tool.rally.workspace]
version = 1

[tool.doctrine.emit]

[[tool.doctrine.emit.targets]]
name = "hello"
entrypoint = "flows/hello/prompts/AGENTS.prompt"
output_dir = "flows/hello/build/agents"
```

## Step 2 — Write `flow.yaml`

Create `flows/hello/flow.yaml`:

```yaml
name: hello
code: HLO
start_agent: 01_greeter
agents:
  01_greeter:
    timeout_sec: 300
    allowed_skills: []
    system_skills: []
    allowed_mcps: []
runtime:
  adapter: codex
  max_command_turns: 4
  adapter_args:
    model: gpt-5.4
```

The `code: HLO` is the per-flow lock identifier. `start_agent` points at
the `agents:` map key. Every agent lists its allowlists explicitly —
`[]` is legal and common for a first agent.

## Step 3 — Write `AGENTS.prompt`

Create `flows/hello/prompts/AGENTS.prompt`:

```
import rally.base_agent as base
import rally.turn_results as turn_results

agent Greeter[base.RallyBaseAgent]: "Greeter"
    role: "Say hello and mark the flow done."

    final_output FinalAnswer: "Final Answer"
        target: turn_results.RallyTurnResult
```

The `import rally.base_agent` and `import rally.turn_results` pull in
the stdlib rules every Rally agent inherits — base role discipline and
the five-base-key turn-result schema.

## Step 4 — Run It

```bash
rally run hello
```

Rally:

1. Acquires the per-flow lock at `runs/locks/HLO.lock`.
2. Emits `flows/hello/build/agents/greeter/` (the compiled agent home).
3. Creates `runs/active/HLO-1/` (the run directory).
4. Runs the adapter with the agent home.
5. Parses the final JSON.
6. If the turn returns `kind: "done"`, moves the run to
   `runs/completed/HLO-1/`.

If the adapter asks for the issue body first, Rally blocks and tells
you where to write it:

```bash
# Write the issue:
echo "Say hello to the world." > runs/active/HLO-1/home/issue.md
# Resume:
rally resume HLO-1
```

## Step 5 — Inspect The Run

Every Rally run leaves its state on disk. Walk through it:

```bash
ls runs/active/HLO-1/
# state.yaml           current run status
# home/                shared ledger and per-session artifacts
# ...

cat runs/active/HLO-1/home/issue.md
# The issue the agent saw.

ls runs/active/HLO-1/home/sessions/greeter/
# turn-001/            first turn's input + output
# ...

cat runs/active/HLO-1/home/sessions/greeter/turn-001/final.json
# The final JSON Rally parsed — the control surface.
```

Nothing here is hidden. The four truth surfaces
([RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md#1-filesystem-is-the-source-of-truth))
are all files you just read.

## Step 6 — Add A Second Agent (Optional)

Open `flow.yaml` and add:

```yaml
agents:
  01_greeter:
    # ...as before...
  02_farewell:
    timeout_sec: 300
    allowed_skills: []
    system_skills: []
    allowed_mcps: []
```

Open `AGENTS.prompt` and add a route + a second agent:

```
agent Greeter[base.RallyBaseAgent]: "Greeter"
    role: "Greet and hand off to Farewell."

    final_output FinalAnswer: "Final Answer"
        target: turn_results.RallyTurnResult
        route: next_route

    route field next_route: "Next Route"
        farewell: "Hand off to Farewell." -> Farewell
        nullable

agent Farewell[base.RallyBaseAgent]: "Farewell"
    role: "Say goodbye and mark the flow done."

    final_output FinalAnswer: "Final Answer"
        target: turn_results.RallyTurnResult
```

Re-run:

```bash
rally run hello
```

The first turn emits `kind: "handoff"` with `next_owner: "farewell"`,
Rally routes to `Farewell`, and the second turn emits `kind: "done"`.

## Step 7 — Step Through It

`--step` runs exactly one turn, writes the next agent into run state as
`paused`, and returns. It is the best mode for learning what Rally
does at each step:

```bash
rally run hello --step
# Look at the first turn's final.json.
rally resume HLO-1 --step
# Look at the second turn's final.json.
```

## Next Steps

- [RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md) — the twelve rules every
  Rally flow obeys.
- [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md) — every flow.yaml
  field.
- [TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md) — the control
  surface in detail.
- [SKILL_AUTHORING.md](SKILL_AUTHORING.md) — how to add reusable
  capability.
- [flows/software_engineering_demo/](../flows/software_engineering_demo/)
  — a real six-agent flow with reviewers, memory, and a setup script.

If you want an interactive guide while you author, install the
`rally-learn` skill:

```bash
npx skills add . -g -a codex -y
```

Rally ships it as a first-party installable skill that teaches flow
authoring end-to-end.
