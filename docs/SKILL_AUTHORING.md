---
title: "Skill Authoring"
status: active
doc_type: authoring_guide
related:
  - docs/SKILL_SCOPING.md
  - docs/FLOW_YAML_REFERENCE.md
  - docs/RALLY_PRINCIPLES.md
  - skills/rally-kernel/prompts/SKILL.prompt
  - skills/demo-git/prompts/SKILL.prompt
  - skills/repo-search/SKILL.md
  - src/rally/services/flow_build.py
---

# Skill Authoring

A Rally skill is a reusable capability an agent can call. This document
covers how to author a **flow-local** skill: where the files live, what
shape they take, how Rally binds the skill to an agent, and how to
verify the binding.

For the four-tier model (mandatory, system, flow-local, external) and
when each tier applies, see
[SKILL_SCOPING.md](SKILL_SCOPING.md). Everything below assumes you have
already decided the new capability belongs in the **flow-local** tier.

## Directory Layouts

A flow-local skill lives under the workspace's top-level `skills/`
directory. Rally supports two authoring surfaces:

**Markdown skill** — a single `SKILL.md` with frontmatter. The simplest
form:

```text
skills/<name>/
└── SKILL.md
```

See [`skills/repo-search/SKILL.md`](../skills/repo-search/SKILL.md) for a
working example (a 30-line skill that teaches `rg`-based repo search).
Markdown skills need no emit target — the file ships as-is.

**Doctrine skill** — a `skill package` declaration plus any bundled
references and scripts:

```text
skills/<name>/
├── prompts/
│   ├── SKILL.prompt
│   ├── references/
│   │   └── <ref>.md
│   └── scripts/
│       └── <script>.py
└── build/              # compiler-owned; gitignored
```

See [`skills/rally-kernel/prompts/SKILL.prompt`](../skills/rally-kernel/prompts/SKILL.prompt)
for a short Doctrine skill and
[`skills/demo-git/prompts/SKILL.prompt`](../skills/demo-git/prompts/SKILL.prompt)
for a longer one with bundled references and a helper script.

Pick Markdown when the skill is a few paragraphs of guidance. Pick
Doctrine when you want typed `when_to_use` / `hard_rules` / `workflow`
blocks, bundled reference files, or the compiler's structural checks.

## Doctrine `SKILL.prompt` Shape

Every Doctrine skill opens with `skill package <Name>` and a `metadata`
block:

```
skill package DemoGitSkill: "Demo Git"
    metadata:
        name: "demo-git"
        description: "Short, action-oriented description (one sentence)."
```

The `metadata.name` must match the `skills/<name>/` directory name and
the `allowed_skills` entry in `flow.yaml`. Rally validates both.

Common body blocks:

| Block               | Shape                            | Purpose                                                 |
| ------------------- | -------------------------------- | ------------------------------------------------------- |
| `when_to_use`       | `bullets cases:`                 | List the concrete triggers for calling the skill.       |
| `when_not_to_use`   | `bullets cases:`                 | List anti-triggers.                                     |
| `hard_rules` / `non_negotiables` | `bullets rules:`   | Rules the caller must not violate.                      |
| `first_move`        | `sequence steps:`                | Ordered steps at the start of skill use.                |
| `workflow`          | `sequence steps:` + `code` blocks | The main body.                                         |
| `output_expectations` | `bullets rules:`               | What the caller should (and should not) produce.        |
| `reference_map`     | `bullets references:`            | Pointers to bundled reference files or scripts.         |

`code` blocks live inline and carry `language:` plus a triple-quoted
`text:` payload. Use them for exact command examples the caller should
copy.

## Markdown `SKILL.md` Shape

Markdown skills open with YAML frontmatter:

```yaml
---
name: repo-search
description: "One-sentence skill summary."
---
```

Then plain Markdown body — headings, bullets, code fences. Rally does
not impose structural constraints, but follow the same conceptual
layout: what it does, when to use, when not to use, the workflow.

## Registering The Skill

**Doctrine skills** need an emit target in `pyproject.toml`:

```toml
[[tool.doctrine.emit.targets]]
name = "demo_git"
entrypoint = "skills/demo-git/prompts/SKILL.prompt"
output_dir = "skills/demo-git/build"
```

The `output_dir` (`skills/<name>/build/`) is compiler-owned — never
hand-edit it. See
[`skills/demo-git/build/`](../skills/demo-git/build/) for the shape of
an emitted skill.

**Markdown skills** need no emit target. Rally reads `SKILL.md`
directly.

Both kinds must be **allowlisted** on an agent in `flow.yaml`:

```yaml
agents:
  01_architect:
    timeout_sec: 900
    allowed_skills: [demo-git, repo-search]
    system_skills: []
    allowed_mcps: []
```

See [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md#the-agents-map) for
the full per-agent field set.

## How Rally Binds A Skill

At load time, Rally:

1. Reads the agent's `allowed_skills` and `system_skills` from
   `flow.yaml`.
2. Looks each name up in the workspace skill registry (flow-local
   skills under `skills/`, system skills like `rally-memory`,
   external-root aliases).
3. Validates the name resolves to exactly one registered skill.
4. Materializes the skill's content into the run's agent home so the
   adapter sees it at runtime.

An unknown name fails load with a clear error —
`Skill does not exist: <name>` for flow-local,
`Unknown stdlib skill: <name>` for system. See
[ERROR_REFERENCE.md](ERROR_REFERENCE.md) for the full list.

## Testing The Binding

The canonical build entrypoint is
[`src/rally/services/flow_build.py`](../src/rally/services/flow_build.py).
`ensure_flow_assets_built` rebuilds every emit target the flow
depends on (including allowlisted skills) and validates the registry.

A one-liner you can run from the workspace root:

```bash
uv run python -c "from pathlib import Path; \
from rally.services.flow_build import ensure_flow_assets_built; \
ensure_flow_assets_built(flow_name='<your_flow>', repo_root=Path('.'))"
```

It is what `rally run` and `rally resume` call internally. If your
skill fails to compile, if `pyproject.toml` is missing the emit target,
or if the agent's `allowed_skills` references a non-existent skill,
this call fails with the same error Rally would surface at run time.

`make emit` is the batch equivalent — it runs every declared emit
target.

## Authoring Principles

- **One skill, one job.** A skill teaches one reusable capability. If
  you find yourself writing "and also..." clauses, split the skill.
- **Be concrete in `when_to_use`.** List exact triggers, not
  categories. "You need the current branch" beats "repo inspection".
- **Keep `hard_rules` short and operational.** One line per rule.
  Every rule must be checkable.
- **Bundle scripts only when the CLI surface is stable.** A Python
  helper under `scripts/` is appropriate when multiple callers need
  the same JSON output. See
  [`skills/demo-git/prompts/scripts/demo_git.py`](../skills/demo-git/prompts/scripts/demo_git.py).
- **Cite a real path in every workflow step.** Vague instructions
  ("inspect the repo") produce vague calls. Name the command.
- **Do not duplicate stdlib rules.** If the stdlib already teaches
  a rule (notes are advisory, final JSON is control), do not paraphrase
  it in the skill. See
  [RALLY_PRINCIPLES.md §5](RALLY_PRINCIPLES.md#5-do-not-repeat-law-across-layers).

## What A Skill Is Not

- **Not a policy layer.** Skills do not decide when a turn is done,
  blocks, or routes. Those belong on the agent's turn result.
- **Not a shared ledger.** Skills do not write to `home:issue.md` to
  coordinate with other agents. Use the typed-handoff pattern
  (`target: File` with a flow-owned `home:` path).
- **Not a config surface.** Skills do not accept flow-level settings.
  Put flow config in `flow.yaml`.

## Related Docs

- [SKILL_SCOPING.md](SKILL_SCOPING.md) — the four tiers and when each applies.
- [FLOW_YAML_REFERENCE.md](FLOW_YAML_REFERENCE.md) — where `allowed_skills` lives.
- [ERROR_REFERENCE.md](ERROR_REFERENCE.md) — skill-related load errors and remedies.
- [RALLY_PRINCIPLES.md](RALLY_PRINCIPLES.md) — allowlist discipline and no-duplication.
