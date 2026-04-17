---
title: "Rally - Skill Scoping Tiers"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: authoring_guide
related:
  - docs/RALLY_AGENT_ALLOWED_SKILL_ENFORCEMENT.md
  - docs/RALLY_MEMORY.md
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL.md
  - src/rally/services/skill_bundles.py
  - src/rally/services/flow_loader.py
  - src/rally/services/flow_build.py
  - src/rally/services/agent_skill_validation.py
  - src/rally/services/home_materializer.py
  - src/rally/services/workspace.py
---

# Skill scoping

Rally agents see skills from one of four tiers. Each tier has a different
source of truth and a different authoring surface. Picking the right tier is
part of flow design — mixing tiers silently is what this document is here to
prevent.

## The four tiers

| Tier | Source | Authoring surface | Example |
|------|--------|-------------------|---------|
| **Mandatory** | `rally-kernel` shipped with the Rally distribution | None — injected on every agent | `rally-kernel` |
| **System (stdlib opt-in)** | Shipped with Rally, listed in `RALLY_BUILTIN_SKILL_NAMES` | Per-agent `system_skills:` in `flow.yaml` + bound in the prompt | `rally-memory` |
| **Flow-local** | `skills/<name>/` under the workspace root (Markdown or Doctrine) | Per-agent `allowed_skills:` in `flow.yaml` + bound in the prompt | `demo-git`, `repo-search` |
| **External** | Registered directory outside the workspace (Markdown or prebuilt Doctrine) | Workspace-level `[tool.rally.workspace.external_skill_roots]` in `pyproject.toml` + per-agent `external_skills: [alias:skill]` in `flow.yaml` | `psmobile:device-farm` |

The mandatory tier is always on — nothing to configure. The other three tiers
are per-agent allowlists; all are validated against the compiled `AGENTS.md`
readback so the runtime allowlist and the prompt surface cannot drift.

## Why `system_skills` is its own field

Before this split, `allowed_skills` mixed stdlib and flow-local names. That
caused three concrete problems:

- **Reader confusion** — a stranger reading `flow.yaml` could not tell whether
  `rally-memory` was a shipped Rally capability or a local skill.
- **Misleading errors** — a typo like `rally-memry` in `allowed_skills` failed
  with "`skills/rally-memry` does not exist", pointing the author at the flow
  tree instead of the stdlib registry.
- **No visible opt-in story** — `rally-memory` is shipped stdlib but no flow
  used it. The opt-in path was theoretical.

Splitting the field keeps the tier visible at a glance and lets the loader
emit tier-specific errors (`Unknown Rally stdlib skill ...; available:
rally-memory`).

## Adding a system skill to an agent

The architect agent in `flows/software_engineering_demo` opts into
`rally-memory` as a working example. To add a system skill to an agent,
edit both sides of the Doctrine boundary and let the validator enforce the
readback.

### 1. Flow.yaml

```yaml
agents:
  01_architect:
    timeout_sec: 900
    allowed_skills: [demo-git, repo-search]
    system_skills: [rally-memory]
    allowed_mcps: []
```

Every agent must declare `system_skills:` — even as an empty list. An empty
list is the right default; it is what every other agent in the demo flow
carries.

### 2. Prompt binding

The Doctrine prompt source must bind the stdlib skill into the agent's
`skills` block. In `flows/software_engineering_demo/prompts/AGENTS.prompt`:

```
from rally.memory import RallyMemorySkill

skills RepoWorkSkillsWithMemory[RepoWorkSkills]: "Skills And Tools"
    inherit {rally_kernel, demo_git, repo_search}

    skill rally_memory: RallyMemorySkill
        requirement: Advisory

agent Architect:
    ...
    skills: RepoWorkSkillsWithMemory
```

### 3. Readback validation

`rally build` runs Doctrine, then
`validate_flow_agent_skill_surfaces` compares the compiled `AGENTS.md`
Skills section against `MANDATORY ∪ allowed_skills ∪ system_skills` for each
agent. If they drift, the build fails loud.

### 4. Runtime mount

`home_materializer._agent_skill_names` (in
`src/rally/services/home_materializer.py`) unions all three tiers when it
mounts the per-agent skill view. System skills show up in the same
`home/skills/` path as flow-local skills — the tier distinction is an
authoring concept, not a runtime one.

## Adding an external skill to an agent

External skills live in another directory on disk — typically a peer workspace
like `~/workspace/psmobile/skills/` — and are referenced from this workspace
without vendoring. The tier exists so teams can share skill bundles across
workspace repos while keeping the "where did this come from?" visible at a
glance.

Rally does not build external Doctrine sources. If the external skill is
authored in Doctrine, its owning repo must already have `build/SKILL.md`
committed. This keeps each workspace's build graph bounded to its own tree.

### 1. Register the root in `pyproject.toml`

```toml
[tool.rally.workspace]
version = 1

[tool.rally.workspace.external_skill_roots]
psmobile = "~/workspace/psmobile/skills"
```

The alias (`psmobile`) must match `[a-z][a-z0-9_-]*` and must not be one of
the reserved tier/path-root names (`rally`, `stdlib`, `system`, `flow`,
`home`, `workspace`, `host`, `local`, `builtin`, `builtins`). The path may
use `~` but must resolve to an absolute directory that exists and that lives
outside the current workspace root.

### 2. Flow.yaml

```yaml
agents:
  01_architect:
    timeout_sec: 900
    allowed_skills: [demo-git, repo-search]
    system_skills: [rally-memory]
    external_skills: [psmobile:device-farm]
    allowed_mcps: []
```

Unlike `system_skills`, `external_skills:` is optional — omit the field when
the agent has no external skills. When present, every entry must be a fully
qualified `<alias>:<skill-name>` pair; unqualified names are a hard error so
the reader never has to guess which root a skill came from.

### 3. Prompt binding

The Doctrine prompt source binds the external skill by its unqualified
name, the same way it binds flow-local skills. The alias is an authoring
concern, not a runtime one.

### 4. Readback validation

`validate_flow_agent_skill_surfaces` compares the compiled `AGENTS.md`
Skills section against `MANDATORY ∪ allowed_skills ∪ system_skills ∪
external_skills` (with external entries normalized to their unqualified
names) for each agent.

### 5. Runtime mount

`home_materializer._resolve_agent_skill_sources` looks the alias up in the
workspace's `external_skill_roots`, resolves the bundle from
`<root>/<skill-name>/`, and mounts it under the agent's per-agent skill
view using the unqualified name. Two skills with the same unqualified name
coming from different tiers is a load-time error.

## Failure modes

These are the errors you will see if you wire this up wrong. Each one points
at a specific fix.

### Unknown stdlib name

```
Unknown Rally stdlib skill `rally-memry` in `system_skills`.
Available stdlib skills: `rally-memory`.
```

You typed a name that is not in `RALLY_BUILTIN_SKILL_NAMES`. Fix: check the
registry (`src/rally/services/builtin_assets.py`) and correct the spelling.

### Mandatory skill listed in system_skills

```
`rally-kernel` is a mandatory Rally stdlib skill and is injected automatically;
remove it from `system_skills`.
```

`rally-kernel` is always on; listing it here is redundant and rejected.

### Overlap between tiers

```
Agent `01_architect` lists `rally-memory` in both `allowed_skills` and
`system_skills`. A skill belongs to exactly one tier.
```

A skill is stdlib or flow-local — not both.

### Readback drift

```
Compiled skill readback for agent `01_architect` in `.../AGENTS.md` does not
match `allowed_skills` + `system_skills` in `flow.yaml`.
Expected ...; found ....
```

The prompt source and `flow.yaml` disagree. Fix both sides until the compiled
Skills section matches the flow allowlist union.

### Unknown flow-local skill

```
Allowed skill does not exist: `.../skills/custom-skill`.
```

A name in `allowed_skills` has no `skills/<name>/` directory. Either create
the skill bundle or remove the name.

### Unknown external skill root alias

```
Unknown external skill root alias `psmobile` in `external_skills` for agent
`01_architect`. Registered aliases: `acme`. Register it under
`[tool.rally.workspace.external_skill_roots]` in pyproject.toml.
```

The flow references an alias that is not declared in the workspace manifest.
Fix: register it in `pyproject.toml` (or correct the typo).

### Unqualified external skill name

```
External skill name `device-farm` must be of the form `<alias>:<skill-name>`.
```

Every entry in `external_skills:` must carry its alias — the tier exists to
make skill origin visible, so unqualified names are rejected.

### Reserved external skill root alias

```
External skill root alias `rally` in `.../pyproject.toml` is reserved. Pick a
different name.
```

Aliases collide with Rally's own path-root and tier vocabulary when they use
reserved words. Rename the root.

### External skill directory missing

```
External skill `psmobile:device-farm` does not exist at
`/Users/.../psmobile/skills/device-farm`.
```

The skill directory is absent under its registered root. Either create the
bundle at that path or remove the reference.

### External Doctrine skill without a prebuilt markdown

```
External Doctrine skill `psmobile:device-farm` is missing `build/SKILL.md`.
Build it inside its own workspace before referencing it from here.
```

Rally refuses to compile Doctrine across workspace boundaries. Run the
external workspace's build so its `build/SKILL.md` is committed, then rerun.

### Runtime-name collision across tiers

```
Agent `01_architect` expects two skills named `device-farm` ...
```

The unqualified name appears under two tiers (e.g. a local `skills/device-farm`
and an external `psmobile:device-farm`). Since the runtime directory name is
always unqualified, rename one side.

## Related

- **Per-agent enforcement mechanics** — see
  [RALLY_AGENT_ALLOWED_SKILL_ENFORCEMENT.md](RALLY_AGENT_ALLOWED_SKILL_ENFORCEMENT.md).
- **Why `rally-memory` exists and what it does** — see
  [RALLY_MEMORY.md](RALLY_MEMORY.md).
- **Where the registry lives** —
  `RALLY_BUILTIN_SKILL_NAMES` and `MANDATORY_SKILL_NAMES` in
  `src/rally/services/builtin_assets.py` and
  `src/rally/services/skill_bundles.py`.
