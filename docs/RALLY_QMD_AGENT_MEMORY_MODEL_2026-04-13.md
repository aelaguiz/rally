---
title: "Rally - QMD Agent Memory Model"
date: 2026-04-13
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - README.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
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

# TL;DR

Outcome
- Add one built-in Rally memory model that is native to Doctrine authoring and native to Rally runtime.
- Give every Rally-managed agent one shared issue-ledger input, one shared memory skill, and one shared memory entry shape without tying memory to note behavior.
- Keep durable memory in repo-local markdown files and use QMD only as the search index over those files.
- Make `memory use` and `memory save` visible Rally events without appending trusted readback into `home/issue.md`.

Problem
- Rally does not have cross-run memory yet.
- The shared Rally stdlib still does not give every agent the issue ledger, the current agent slug, or a shared memory contract.
- Two live flows already carry their own local issue-ledger inputs and note structures. That proves Doctrine can express the shape, but it also shows how memory would drift if Rally adds it as runtime-only behavior.
- QMD is a good fit for search, but its raw CLI and MCP defaults still write under `~/.cache/qmd/` unless Rally forces a repo-local cache root.
- Rally is Python and QMD is Node, so the runtime needs one pinned bridge path instead of ambient `qmd` installs or raw CLI calls.

Approach
- Put the agent-facing memory contract in Doctrine source first.
- Make Rally runtime back that contract with repo-local storage, QMD indexing, CLI commands, and visible runtime event paths.
- Reuse the compiled Doctrine agent slug as the only agent-scope truth and project that same slug into `RALLY_AGENT_SLUG` for runtime use.
- Converge flow-local issue-ledger and generic memory patterns back into the shared stdlib instead of letting each flow tell its own memory story.

What shipped
- Lock the North Star and owner split around Doctrine-first memory.
- Keep the QMD dependency pinned to a small repo-owned Node bridge that uses `@tobilu/qmd` `v2.1.0`.
- Add the shared stdlib pieces: issue-ledger input, memory document, and shared skill.
- Update the built-in skill emit and sync path so `rally-memory` is treated like `rally-kernel`.
- Land the runtime backing, then visibility, then one narrow flow proof, then sync live docs.

Non-negotiables
- Doctrine owns the agent-facing memory contract.
- Rally owns storage, indexing, CLI behavior, durable memory files, and runtime events.
- The compiled Doctrine agent slug is the source of truth for agent scope.
- Markdown memory files are the source of truth. QMD is only a rebuildable search index.
- No hidden memory prose outside the declared `.prompt` graph.
- No per-flow generic memory lifecycle rules once the shared stdlib contract exists.
- Memory never carries routing, `done`, `blocker`, or `sleep` truth.



## Current Status

This section is the current truth for the repo after the implementation pass.

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
