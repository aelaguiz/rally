# Rally

[![CI](https://img.shields.io/github/actions/workflow/status/aelaguiz/rally/pr.yml?branch=main&label=pr)](https://github.com/aelaguiz/rally/actions/workflows/pr.yml)
[![PyPI](https://img.shields.io/pypi/v/rally-agents)](https://pypi.org/project/rally-agents/)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/aelaguiz/rally/badge)](https://scorecard.dev/viewer/?uri=github.com/aelaguiz/rally)

[Doctrine](https://github.com/aelaguiz/doctrine) · [Contributing](CONTRIBUTING.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)
[Design](docs/RALLY_MASTER_DESIGN.md) · [Porting Guide](docs/RALLY_PORTING_GUIDE.md) · [Versioning](docs/VERSIONING.md) · [Changelog](CHANGELOG.md) · [Support](SUPPORT.md) · [Security](SECURITY.md)

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
`doctrine-agents>=1.0.2,<2`.
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

If you still have an older env or lockfile pinned to `doctrine`, refresh it to
`doctrine-agents>=1.0.2,<2`.

Versioning and upgrade rules live in [docs/VERSIONING.md](docs/VERSIONING.md).
Release history lives in [CHANGELOG.md](CHANGELOG.md).

## Use Rally In Another Repo

If you are porting an existing agent system into Rally, read
[docs/RALLY_PORTING_GUIDE.md](docs/RALLY_PORTING_GUIDE.md) first.
It explains what should move into `flow.yaml`, `home:issue.md`, setup scripts,
skills, and shared prompt owners, with example-driven guidance about what to
remove, what to keep, and where Rally expects the truth to live.

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

[tool.doctrine.emit]

[[tool.doctrine.emit.targets]]
name = "demo"
entrypoint = "flows/demo/prompts/AGENTS.prompt"
output_dir = "flows/demo/build/agents"
```

Author your flow under `flows/demo/`, then use Rally's build and run path:

```bash
rally run demo
```

Do not point support files at `../rally/stdlib/...`.
During Rally-managed builds, Rally resolves its stdlib and built-in skills
from the source checkout or installed package and passes the stdlib prompt
root into Doctrine. Host repos should not add Rally's stdlib under
`additional_prompt_roots`, and they should not vendor Rally-owned built-ins
unless they mean to own that copy on purpose.

If your flow needs stable launch env vars, put them in `flow.yaml` instead of
relying only on the shell that launches `rally`:

```yaml
name: demo
code: DMO
start_agent: 01_scope_lead
agents:
  01_scope_lead:
    timeout_sec: 900
    allowed_skills: []
    system_skills: []
    allowed_mcps: []
runtime:
  adapter: codex
  max_command_turns: 8
  env:
    PROJECT_ROOT: workspace:fixtures/project
    API_BASE_URL: https://example.test
  adapter_args:
    model: gpt-5.4
```

Rally applies `runtime.env` before startup host-input checks, to the setup
script, to the prompt-input command, and to the adapter launch. That means
`runtime.env` can satisfy `host_inputs.required_env` and `host:$VAR` paths
during preflight. Flow values win over duplicate shell env vars. Rally still
keeps its own `RALLY_*` keys and adapter keys reserved.

Use `rally run` as the supported build-and-run path:

```bash
rally run demo
rally run demo --from-file ./issue.md
```

`rally run` rebuilds the flow before launch.
`rally resume` rebuilds it before resume.
There is no host-side `workspace sync` step and no host-side
`doctrine.emit_docs` step for Rally stdlib imports in the supported path.
If you already wrote the starting issue somewhere else, `--from-file` copies
that file into the new run's `home/issue.md` and starts from there.
If you want one agent turn at a time, use `--step`:

```bash
rally run demo --step
rally resume DMO-1 --step
```

That runs one turn, writes the next agent into run state as `paused`, and
lets you choose when to take the next step.
If you want to see what is active before you resume, use:

```bash
rally status
rally status DMO-1
```

Host repos should not add `stdlib/rally/` or `skills/rally-*` just to make
Rally work, because Rally does not write those framework-owned paths during
managed builds and runs.
If you choose to vendor a Rally built-in on purpose, that copy is host-owned
and Rally will not keep it in sync.

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

To run the smallest shipped demo locally:

Build the checked-in flow and skill readback that Rally loads at runtime:

```bash
uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo
uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory --target demo-git
```

Then run the smallest shipped demo:

```bash
uv run rally run poem_loop
```

If you want to walk the flow one agent turn at a time:

```bash
uv run rally run poem_loop --step
uv run rally resume POM-1 --step
```

If Rally stops for issue text:

If you do not have an interactive editor configured, Rally will stop and tell you where the issue file lives. On a fresh repo, that path will be:

```text
runs/active/POM-1/home/issue.md
```

Write the issue there, then resume the run:

```bash
uv run rally resume POM-1
```

To check what Rally thinks is active or blocked:

```bash
uv run rally status
uv run rally status POM-1
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
make release-prepare RELEASE=vX.Y.Z CLASS=internal|additive|soft-deprecated|breaking CHANNEL=stable
make release-tag RELEASE=vX.Y.Z CHANNEL=stable
make release-draft RELEASE=vX.Y.Z CHANNEL=stable PREVIOUS_TAG=auto
make release-publish RELEASE=vX.Y.Z
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
- allowlisted skills (flow-local and stdlib, see
  [docs/SKILL_SCOPING.md](docs/SKILL_SCOPING.md)) and MCP materialization
  into the run home
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
- Use [SUPPORT.md](SUPPORT.md) when you are not sure which path fits.
- Use [SECURITY.md](SECURITY.md) for security reports.
- Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in project spaces.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and proof commands.

## Read Next

- [docs/VERSIONING.md](docs/VERSIONING.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/RALLY_MASTER_DESIGN.md](docs/RALLY_MASTER_DESIGN.md)
- [docs/RALLY_RUNTIME.md](docs/RALLY_RUNTIME.md)
- [docs/RALLY_CLI_AND_LOGGING.md](docs/RALLY_CLI_AND_LOGGING.md)
- [docs/RALLY_COMMUNICATION_MODEL.md](docs/RALLY_COMMUNICATION_MODEL.md)
- [docs/RALLY_MEMORY.md](docs/RALLY_MEMORY.md)
- [SUPPORT.md](SUPPORT.md)
- [SECURITY.md](SECURITY.md)
- [Doctrine](https://github.com/aelaguiz/doctrine)
- [CONTRIBUTING.md](CONTRIBUTING.md)

If this direction is useful, star the repo and watch releases.
