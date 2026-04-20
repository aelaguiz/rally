---
title: "flow.yaml Reference"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_PRINCIPLES.md
  - docs/SKILL_SCOPING.md
  - docs/TURN_RESULT_CONTRACT.md
  - src/rally/services/flow_loader.py
  - src/rally/domain/flow.py
---

# `flow.yaml` Reference

Every Rally flow has exactly one `flow.yaml` at its root. It is the
runtime truth surface: it names the flow, lists the agents, declares
their skill allowlists, and points at the setup script and adapter
config. The stdlib teaches turn behavior; `flow.yaml` teaches Rally
what to load.

The loader source is
[`src/rally/services/flow_loader.py`](../src/rally/services/flow_loader.py).
The frozen domain objects live at
[`src/rally/domain/flow.py`](../src/rally/domain/flow.py).

## Minimal Shape

```yaml
name: software_engineering_demo
code: SED
setup_home_script: flow:setup/prepare_home.sh
start_agent: 01_architect
agents:
  01_architect:
    timeout_sec: 900
    allowed_skills: [demo-git, repo-search]
    system_skills: [rally-memory]
    allowed_mcps: []
  02_architect_reviewer:
    timeout_sec: 900
    allowed_skills: [demo-git, repo-search]
    system_skills: []
    allowed_mcps: []
runtime:
  adapter: codex
  max_command_turns: 12
  guarded_git_repos:
    - home:repos/demo_repo
  adapter_args:
    model: gpt-5.4
    reasoning_effort: medium
```

## Top-Level Fields

| Field                | Type     | Required | Notes                                                                 |
| -------------------- | -------- | -------- | --------------------------------------------------------------------- |
| `name`               | string   | yes      | Flow name. Must match the flow directory name.                        |
| `code`               | string   | yes      | Exactly three uppercase ASCII letters. Used for the per-flow lock.    |
| `start_agent`        | string   | yes      | Key from `agents:` map. Names the first agent to run.                 |
| `agents`             | map      | yes      | Ordered map of agent keys to per-agent config.                        |
| `runtime`            | map      | yes      | Adapter name, tool budget, guarded repos, adapter args.               |
| `setup_home_script`  | string   | no       | Path scheme (`flow:`) pointing at a script that seeds `home:` once.   |

## The `code` Field

The three-letter code identifies the flow for Rally's per-flow lock
(`runs/locks/<CODE>.lock`) and several operator-visible surfaces.
Validation: exactly three uppercase ASCII letters. Shorter, longer, or
lowercase codes fail load.

## The `agents` Map

Keys follow the pattern `NN_<slug>` (e.g. `01_architect`,
`02_architect_reviewer`). Rally strips the numeric prefix to derive the
compiled slug, which appears in file paths and turn-result route
selectors.

Per-agent fields:

| Field             | Type          | Required | Notes                                                                 |
| ----------------- | ------------- | -------- | --------------------------------------------------------------------- |
| `timeout_sec`     | int           | yes      | Hard timeout for one turn. Exceeding it marks the turn `blocker`.     |
| `allowed_skills`  | list[string]  | yes      | Flow-local or external skill names the agent may call.                |
| `system_skills`   | list[string]  | yes      | Opt-in stdlib skills. Today: `rally-memory`. `[]` is legal.           |
| `allowed_mcps`    | list[string]  | yes      | MCP server names the agent may call. `[]` is legal.                   |
| `external_skills` | list[string]  | no       | External skills registered with a reserved alias prefix.              |

Rally validates every skill and MCP name against the workspace registry
at load time. An unknown name fails with a clear error.

## The `runtime` Block

| Field                | Type          | Required | Notes                                                               |
| -------------------- | ------------- | -------- | ------------------------------------------------------------------- |
| `adapter`            | string        | yes      | One of `codex`, `claude-code`. Adapter registry enforces.           |
| `max_command_turns`  | int           | yes      | Per-run tool budget for the adapter.                                |
| `guarded_git_repos`  | list[string]  | no       | Paths (usually under `home:`) that Rally treats as guarded repos.   |
| `adapter_args`       | map           | yes      | Free-form adapter config. Each adapter validates its own keys.      |
| `env`                | map           | no       | Extra env vars. `RALLY_*` and a reserved short list are rejected.   |

**`runtime.prompt_input_command` is rejected.** Rally does not support
per-turn input reducers. If you are tempted to add one, read
[RALLY_PORTING_GUIDE.md](RALLY_PORTING_GUIDE.md) — the reducer pattern
is a recurring porting anti-pattern. Put runtime truth on disk, not in
a computed prompt input.

## Path Schemes

Fields that accept a path use one of four schemes:

| Scheme        | Resolves to                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `home:<path>` | Inside the run's `home/` directory (`runs/active/<ID>/home/...`).           |
| `workspace:<path>` | Inside the workspace root (the directory containing `pyproject.toml`). |
| `host:<path>` | Inside the host repo (only under adapter host-binding).                     |
| `flow:<path>` | Inside the flow's own directory (`flows/<flow>/...`).                       |

The reserved `path:` key is **not** a path scheme. Using `path:` as a
map key inside a flow config fails load — Rally reserves that key for
internal typed surfaces.

## `runtime.env` Precedence

`runtime.env` is merged into the adapter's env. Reserved keys that Rally
or the adapter already owns are rejected at load:

- Anything starting with `RALLY_`.
- `CODEX_HOME`.
- `ENABLE_CLAUDEAI_MCP_SERVERS`.

Put flow-specific env vars here. Do not try to override Rally's own
env via this surface.

## External Skill Root Aliases

`[tool.rally.external_skills]` in `pyproject.toml` can register
external skill roots under a short alias. Aliases are validated:

- Pattern: `[a-z][a-z0-9_-]*`.
- Reserved: `rally`, `stdlib`, `system`, `flow`, `home`, `workspace`,
  `host`, `local`, `builtin`, `builtins`.

An external skill appears in an agent's `allowed_skills` as
`<alias>:<skill-name>`.

## The `setup_home_script` Field

Optional. When present, Rally runs the script exactly once per new run,
under the run's home directory, before the first turn. Use it to seed
repos, create directories, or write fixtures the flow depends on.

The script path uses the `flow:` scheme and must already exist at load
time.

## Validation Rules At A Glance

Rally's loader rejects a flow when:

- `code` is not three uppercase ASCII letters.
- `start_agent` is not a key in `agents:`.
- Any agent key is missing `timeout_sec`, `allowed_skills`,
  `system_skills`, or `allowed_mcps`.
- Any listed skill or MCP is not registered in the workspace.
- `runtime.adapter` is not a known adapter.
- `runtime.prompt_input_command` appears.
- `runtime.env` names a reserved key.
- `setup_home_script` points at a file that does not exist.
- An external skill alias collides with a reserved alias.
- The reserved `path:` key appears as a map key in a flow config.

## Related Docs

- [RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md) — filesystem-is-truth; one-active-run.
- [SKILL_SCOPING.md](SKILL_SCOPING.md) — the four-tier skill model.
- [TURN_RESULT_CONTRACT.md](TURN_RESULT_CONTRACT.md) — what every agent emits.
- [RALLY_MASTER_DESIGN.md](RALLY_MASTER_DESIGN.md) — the broader runtime picture.
- [RALLY_RUNTIME.md](RALLY_RUNTIME.md) — lifecycle of a run.
