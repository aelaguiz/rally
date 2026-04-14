---
title: "Rally Memory"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - README.md
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/issue_ledger.prompt
  - stdlib/rally/prompts/rally/notes.prompt
  - skills/rally-kernel/prompts/SKILL.prompt
  - flows/poem_loop/prompts/shared/inputs.prompt
  - flows/software_engineering_demo/prompts/shared/inputs.prompt
  - flows/poem_loop/prompts/shared/outputs.prompt
  - src/rally/domain/flow.py
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/framework_assets.py
  - src/rally/services/home_materializer.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/run_events.py
  - src/rally/services/skill_bundles.py
  - src/rally/adapters/codex/launcher.py
---

# Summary

This file records the shipped Rally memory model.
Rally now gives every Rally-managed agent one shared memory contract, one
shared memory skill, and one repo-local memory store that stays separate from
turn routing and note control.

# Live Rules

- Doctrine owns the agent-facing memory contract.
- Rally owns storage, indexing, CLI behavior, durable memory files, and
  runtime events.
- The compiled Doctrine agent slug is the source of truth for agent scope.
- Markdown memory files are the source of truth.
- QMD is only a rebuildable search index over those files.
- Memory never carries `done`, `blocker`, `sleep`, or route truth.

# Shipped Surface

What is shipped now:
- shared memory contract in `stdlib/rally/prompts/rally/memory.prompt`
- shared issue-ledger input and `RALLY_AGENT_SLUG` exposure in the shared base agent
- built-in `rally-memory` skill source plus emitted readback beside `rally-kernel`
- built-in skill wiring through `skill_bundles.py`, `flow_build.py`, `framework_assets.py`, and `workspace.py`
- repo-local markdown memory truth under `runs/memory/entries/<flow_code>/<agent_slug>/`
- repo-local QMD state under `runs/memory/qmd/index.sqlite` and `runs/memory/qmd/cache/`
- pinned Node bridge under `tools/qmd_bridge/` on `@tobilu/qmd` `2.1.0`
- Rally CLI front doors for `memory search`, `memory use`, `memory save`, and `memory refresh`
- memory-specific runtime events and durable markdown files, with no memory-specific issue-ledger records
- visible `memory_used` and `memory_saved` runtime events
- compiled-slug-backed memory scope carried through `flow_loader.py`
- deletion of the stale `src/rally/services/event_log.py` path

Proof already captured:
- rebuilt `_stdlib_smoke`, `poem_loop`, and `software_engineering_demo`
- focused test sweep covering flow build, framework assets, flow loading, CLI, issue ledger, run events, runner, and the new memory services
- full unit suite at current head
- one bridge smoke proof that kept `~/.cache/qmd/` untouched on an empty scoped refresh
- one real `POM-1` `poem_loop` proof that saved memory on turn 7, searched and used it on turn 9, and still ended `done` on turn 10
- current `rally memory search` output that shows the canonical memory id, lesson title, and short snippet
- `uv run pytest tests/unit -q` passes on current head

Fresh audit check:
- the full approved frontier has been rerun against current repo truth
- no approved code frontier remains open for this change
