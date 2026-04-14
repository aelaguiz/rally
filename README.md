# Rally

[![CI](https://img.shields.io/github/actions/workflow/status/aelaguiz/rally/pr.yml?branch=main&label=pr)](https://github.com/aelaguiz/rally/actions/workflows/pr.yml)
[![PyPI](https://img.shields.io/pypi/v/rally)](https://pypi.org/project/rally/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/aelaguiz/rally/badge)](https://scorecard.dev/viewer/?uri=github.com/aelaguiz/rally)

[Website](https://pokerskill.com) · [Doctrine](https://github.com/aelaguiz/doctrine)
[Design](docs/RALLY_MASTER_DESIGN_2026-04-12.md) · [Versioning](docs/VERSIONING.md) · [Changelog](CHANGELOG.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)

Stop building serious agent workflows out of Markdown, hope, and hidden state.

Rally lets you program real multi-agent workflows like software. You write the
flow in Doctrine, a typed Python-like DSL with inheritance. Rally compiles that
source into agent-readable `AGENTS.md`, runs it from a small CLI, keeps the
whole run on disk, and routes every turn from strict JSON instead of prose.

> Status: early, real, and opinionated. The current runtime is Codex-first and
> usable today. First-class Claude Code support and repo-local built-in memory
> are next, and both already have concrete design docs in this repo.

## Live Demo

Rally running the shipped `poem_loop` flow from the real CLI.

![Rally poem loop live demo](docs/assets/poem-loop-demo-run.png)

## Rally In One Line

Rally is orchestration, governance, and harnessing for coding agents, but the
control lives in typed flow code and plain repo files.

## Why Rally Exists

Most agent stacks still make you choose between:

- a giant pile of hand-written Markdown
- a big app server with hidden state
- one clever personal agent that is hard to turn into a repeatable team flow

Rally takes a different bet:

- workflows are code
- routing is typed
- runs are files
- notes are visible
- the runtime stays small
- debugging should feel like normal engineering

Strong source. Boring runtime. Honest files.

## Who It Is For

Use Rally if you want:

- repeatable multi-agent coding workflows
- clear owners, clear artifacts, and clear stop points
- flows you can diff, test, review, and refactor like software
- a runtime you can inspect with `rg`, `git`, `cat`, and unit tests
- a system that does not hide the truth in a dashboard or a database

## What Makes Rally Different

- **Programmable workflows.** Rally is about repeatable flows with real owner
  changes, review steps, and current artifacts. It is not just a chat wrapper.
- **A typed DSL behind the flow.** Doctrine gives Rally named workflows,
  inheritance, typed inputs and outputs, review rules, and compile-time
  failures when the flow lies.
- **Filesystem-first runtime.** Every run gets one home, one live
  `home:issue.md`, one clear log trail, and one honest resume path.
- **Built for coding agents.** The runtime is CLI-first, repo-local, and easy
  to test. It fits Codex now and is being opened cleanly for Claude Code next.
- **Memory belongs in the product.** Rally's memory direction is repo-local
  Markdown plus search, not a hidden SaaS sidecar. That work is active, and the
  rule is the same: visible files, visible events, no side door.
- **Easy to debug.** If something important happened, you should be able to
  find it under `runs/`.

## Where Rally Fits

| If you want... | Use... |
| --- | --- |
| a company of agents with org charts, budgets, approvals, and a dashboard | [Paperclip](https://github.com/paperclipai/paperclip) |
| one strong general agent with chat, tools, memory, messaging, and subagents | [Hermes Agent](https://github.com/NousResearch/hermes-agent) |
| a programmable multi-agent workflow for real coding work | Rally |

Rally borrows good lessons from both:

- From Paperclip: issue-led work, resumable runs, exact owner changes, and
  durable history
- From Hermes: strong agent ergonomics, respect for local workflows, and memory
  as a first-class concern

But Rally cuts the company shell and the one-agent shell. The flow is the
product.

## Why This Angle Matters Now

A lot of the market is circling the same words: orchestration, guardrails,
observability, governance, memory.

Those are real needs. Rally just answers them in a different way:

- **Orchestration:** write the flow as code instead of hiding it in runtime
  glue
- **Governance:** route from one trusted JSON result, with one clear owner at a
  time
- **Harness:** give every run one prepared home with only the allowed skills,
  MCPs, repos, and files
- **Memory:** keep it repo-local and visible when it lands, not hidden behind a
  mystery store

Most tools make the runtime smarter. Rally makes the authored workflow
stronger.

## Doctrine Is The Unfair Advantage

Doctrine is Rally's authoring layer.

It is a typed, Python-like DSL with inheritance. It lets you define:

- named workflows
- abstract and concrete agents
- typed inputs and outputs
- review rules
- shared laws and shared sections

A tiny example:

```prompt
workflow RepairLoop: "Repair Loop"
    "Read `home:issue.md` first."
    "Keep the plan in `home:artifacts/repair_plan.md`."

output ArchitectTurnResult: "Architect Turn Result"
    target: TurnResponse
    shape: rally.turn_results.RallyTurnResultJson

agent Architect:
    workflow: RepairLoop
    final_output: ArchitectTurnResult
```

Humans and coding agents edit that source. Rally runs the compiled readback
that agents already know how to read today.

That split matters:

- one rule change lands once
- reviewers can inspect source and readback side by side
- routing and final output stay typed
- the runtime does not have to scrape prose and guess what the flow meant

In authored source, Rally paths are rooted. Use `home:...`, `flow:...`,
`workspace:...`, or `host:...`. Rally internals may also use `stdlib:...`.
Do not use bare relative paths in `flow.yaml`, prompt `path:` fields, or MCP
path values. Inside shell commands that already run in the prepared home, plain
paths like `repos/demo_repo` are still fine. Prompt support files still use the
current compiler-relative form. If rooted support-file paths are missing, Rally
stops there and names the Doctrine gap instead of editing `../doctrine`.

## A Rally Repo Stays Small On Purpose

```text
flows/     authored flows and compiled readback
stdlib/    Rally's shared Doctrine prompt source
skills/    skill packages
mcps/      MCP definitions
runs/      repo-local runtime state
```

A run looks like this:

```text
runs/active/POM-1/
  run.yaml
  state.yaml
  issue_history/
  logs/
  home/
    issue.md
    agents/
    skills/
    mcps/
    repos/
    sessions/
    artifacts/
```

If you need to know what happened, it should be in that tree.

## Small Operator Surface

Rally is meant to be simple to run:

```bash
uv run rally run <flow>
uv run rally resume <RUN_ID>
uv run rally issue note --run-id <RUN_ID> --text "..."
```

That is the point. Complex workflows should not need a giant control plane to
stay operable.

## Install Rally

Rally is an ordinary Python package with one CLI:

```bash
uv tool install rally
rally --help
```

Rally requires Python 3.14 or newer and currently supports
`doctrine>=1.0.1,<2`.

If you want Rally inside a repo-local environment instead of a tool install:

```bash
uv add --dev rally
uv run rally --help
```

Versioning and upgrade rules live in [docs/VERSIONING.md](docs/VERSIONING.md).
Release history lives in [CHANGELOG.md](CHANGELOG.md).

## Use Rally In Another Repo

Your host repo is the Rally workspace. Add the fixed top-level folders:

```text
flows/
skills/
mcps/
stdlib/
runs/
```

Then add the workspace and emit config to `pyproject.toml`:

```toml
[project]
name = "demo-host"
version = "0.1.0"
requires-python = ">=3.14"

[tool.rally.workspace]
version = 1

[tool.doctrine.compile]
additional_prompt_roots = ["stdlib/rally/prompts"]

[tool.doctrine.emit]

[[tool.doctrine.emit.targets]]
name = "demo"
entrypoint = "flows/demo/prompts/AGENTS.prompt"
output_dir = "flows/demo/build/agents"
```

Author your flow under `flows/demo/`, then run it:

```bash
rally run demo
```

On the first build or run, Rally syncs its own built-ins into your workspace
under `stdlib/rally/`, `skills/rally-kernel/`, and `skills/rally-memory/`.
Do not point support files at `../rally/stdlib/...`. Rally copies the support
files into the host workspace so Doctrine emit stays inside the project root.

If Rally opens `home:issue.md`, write the issue there and resume:

```bash
rally resume DMO-1
```

## Work On Rally Itself

If you are changing Rally, use a normal repo checkout:

```bash
git clone https://github.com/aelaguiz/rally.git
cd rally
uv sync --dev
```

Run the smallest shipped demo:

```bash
uv run rally run poem_loop
```

Run the unit tests:

```bash
uv run pytest tests/unit -q
```

Cut a public release with the repo-owned flow:

```bash
make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable
make release-tag RELEASE=v0.1.0 CHANNEL=stable
make release-draft RELEASE=v0.1.0 CHANNEL=stable PREVIOUS_TAG=auto
make release-publish RELEASE=v0.1.0
```

The full rules live in [docs/VERSIONING.md](docs/VERSIONING.md). The release
history lives in [CHANGELOG.md](CHANGELOG.md).

## What Ships Today

Rally already has:

- Doctrine-authored flows and generated readback under `flows/*/build/**`
- a working Codex-first runtime path
- repo-local run homes, issue history, logs, and restartable runs
- strict final JSON turn results
- review-native flow support
- flow-local setup hooks and prompt-input reducers
- guarded git repo checks
- unit coverage around flow loading, build orchestration, runner behavior, and
  result loading

Two demo flows are in the repo today:

- `poem_loop` for the smallest end-to-end loop
- `software_engineering_demo` for a richer multi-role coding flow

## What Is Next

Rally is moving toward:

- first-class Claude Code support on the same front door
- repo-local built-in memory with visible use and save events
- a cleaner multi-adapter boundary
- more real flows that prove the model on harder work

The key rule does not change: no hidden side doors, no second turn-ending path,
and no drift between what the flow says and what the runtime does.

## Open Source On Purpose

Rally is MIT licensed. See [LICENSE](LICENSE).

Open source matters here because trust is the product. You should be able to
inspect:

- what the agent saw
- what files were current
- why ownership changed
- what ended the turn
- what the runtime wrote to disk

If that story depends on a hidden DB, a dashboard, or hand-wavy prompt magic,
Rally failed its own pitch.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version:

- use `uv`
- keep prompt source in `.prompt`
- do not hand-edit generated readback
- prove the smallest real path for the change

## Questions and contributions

- Use [Discussions](https://github.com/aelaguiz/rally/discussions) for
  questions and design talk.
- Use [Issues](https://github.com/aelaguiz/rally/issues) for clear bugs or
  scoped proposals.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and proof commands.
- See [SUPPORT.md](SUPPORT.md) for help paths and [SECURITY.md](SECURITY.md)
  for private vulnerability reports.

## Read Next

- [docs/VERSIONING.md](docs/VERSIONING.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md)
- [docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md](docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md)
- [docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md](docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md)
- [docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md](docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md)
- [docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md](docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md)
- [SUPPORT.md](SUPPORT.md)
- [SECURITY.md](SECURITY.md)
- [Doctrine](https://github.com/aelaguiz/doctrine)
