# Rally

[![CI](https://img.shields.io/github/actions/workflow/status/aelaguiz/rally/pr.yml?branch=main&label=pr)](https://github.com/aelaguiz/rally/actions/workflows/pr.yml)
[![PyPI](https://img.shields.io/pypi/v/rally-agents)](https://pypi.org/project/rally-agents/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/aelaguiz/rally/badge)](https://scorecard.dev/viewer/?uri=github.com/aelaguiz/rally)

[Doctrine](https://github.com/aelaguiz/doctrine) · [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)
[Design](docs/RALLY_MASTER_DESIGN_2026-04-12.md) · [Versioning](docs/VERSIONING.md) · [Changelog](CHANGELOG.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)

Build strong, stable coding-agent workflows from plain repo files.

Rally is the filesystem-first agent harness for coding-agent workflows you can inspect, recover, and trust. It keeps the run on disk inside the repo, routes each turn from strict JSON, and makes handoffs, blockers, artifacts, and stop reasons obvious instead of burying them in a hidden control plane.

If you already care about agents and want stronger workflow discipline, Rally is the front door. Doctrine sits underneath as the code-like authoring layer that keeps those workflows structured instead of collapsing into markdown sprawl.

> Flows are code. Runs are files.

> Status: early, real, and already useful. Codex and Claude Code support ship today. Repo-local searchable memory and allowlisted MCP surfaces ship today. The checked-in demo flows still default to Codex.

## Live demo

Rally running the shipped `poem_loop` flow from the real CLI.

![Rally poem loop live demo](docs/assets/poem-loop-demo-run.png)

Why teams reach for Rally:

- strong, stable coding-agent workflows instead of workflow theater
- run history lives under `runs/`
- turn control comes from strict JSON, not prose guessing
- the operator can inspect `issue.md`, artifacts, logs, and sessions on disk
- resume paths stay honest because the state is visible
- Doctrine under the hood keeps the workflow authorable and maintainable like code

## Doctrine and Rally

- Use Rally when you want to run a strong, stable workflow with repo-local state and strict turn routing.
- Use Doctrine when you want to author and validate the workflow underneath it.
- Keep the split crisp: Doctrine is how you author it. Rally is how you run it.

## What Rally is for

Use Rally if you want:

- repeatable coding-agent workflows
- clear owners, clear artifacts, and clear stop points
- repo-local runtime state instead of a hidden control plane
- workflows you can diff, test, and review like software
- a harness that is small enough to inspect with normal developer tools

## Install Rally

Rally is an ordinary Python package with one CLI:

```bash
uv tool install rally-agents
rally --help
```

Rally requires Python 3.14 or newer and currently supports
`doctrine>=1.0.1,<2`.
The name split is on purpose:

- GitHub repo and source checkout: `rally`
- Published package: `rally-agents`
- Python import: `rally`
- CLI command: `rally`

If you want Rally inside a repo-local environment instead of a tool install:

```bash
uv add --dev rally-agents
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

Author your flow under `flows/demo/`, then sync Rally's built-ins into the
workspace:

```bash
rally workspace sync
```

That writes Rally-owned built-ins into `stdlib/rally/`,
`skills/rally-kernel/`, and `skills/rally-memory/`.
Do not point support files at `../rally/stdlib/...`.
Rally copies the support files into the host workspace so Doctrine emit stays
inside the project root.

If you want a manual build before the first run, emit from the host repo after
the sync:

```bash
uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target demo
```

Then run the flow:

```bash
rally run demo
```

`rally run` and `rally resume` still refresh those built-ins before each
start or resume.

In most host repos, treat the synced built-ins as generated framework files and
ignore them in git unless you are choosing to vendor them on purpose:

```gitignore
stdlib/rally/
skills/rally-kernel/
skills/rally-memory/
```

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

Source contributors still work in repo `rally`. Only the published package
uses the name `rally-agents`.

Run the smallest shipped demo:

Build the checked-in flow and skill readback that Rally loads at runtime:

```bash
uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo
uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory --target demo-git
```

Run the smallest shipped demo:

```bash
uv run rally run poem_loop
```

Run the unit tests:

If you do not have an interactive editor configured, Rally will stop and tell you where the issue file lives. On a fresh repo, that path will be:

```text
runs/active/POM-1/home/issue.md
```

Write the issue there, then resume the run:

```bash
uv run rally resume POM-1
```

Run the unit tests any time with:

```bash
uv run pytest tests/unit -q
```

Cut a public release with the repo-owned flow:

```bash
make build-dist
make verify-package
make verify
make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable
make release-tag RELEASE=v0.1.0 CHANNEL=stable
make release-draft RELEASE=v0.1.0 CHANNEL=stable PREVIOUS_TAG=auto
make release-publish RELEASE=v0.1.0
```

The full rules live in [docs/VERSIONING.md](docs/VERSIONING.md). The release
history lives in [CHANGELOG.md](CHANGELOG.md). The first TestPyPI and PyPI
setup steps also live in `docs/VERSIONING.md`.

## What ships today

Rally already has:

- Doctrine-authored flows and generated readback under `flows/*/build/**`
- live Codex and Claude Code adapter paths
- repo-local run homes, issue history, logs, and restartable runs
- strict `handoff`, `done`, `blocker`, and `sleep` turn results
- repo-local searchable memory
- allowlisted skills and MCP materialization into the run home
- two demo flows:
  - `poem_loop`
  - `software_engineering_demo`

## Why this angle matters

A lot of agent tooling still hides the important truth in dashboards, opaque state, or giant piles of copied prompt prose.

Rally takes a different bet:

- keep the runtime small
- keep the run visible
- keep ownership changes explicit
- keep the stop rules typed
- keep recovery paths boring and honest

If the story only works when the control plane is hidden, the runtime is not trustworthy enough yet.

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
- [docs/RALLY_CLI_AND_LOGGING_2026-04-13.md](docs/RALLY_CLI_AND_LOGGING_2026-04-13.md)
- [docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md](docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md)
- [SUPPORT.md](SUPPORT.md)
- [SECURITY.md](SECURITY.md)
- [docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md](docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md)
- [Doctrine](https://github.com/aelaguiz/doctrine)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Questions and contributions

- Use [Discussions](https://github.com/aelaguiz/rally/discussions) for questions and design talk.
- Use [Issues](https://github.com/aelaguiz/rally/issues) for clear bugs or scoped proposals.
- Use [SUPPORT.md](SUPPORT.md) when you are not sure which path fits.
- Use [SECURITY.md](SECURITY.md) for security reports.
- Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in project spaces.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for the bootstrap and proof commands.

If this direction is useful, star the repo and watch releases.
