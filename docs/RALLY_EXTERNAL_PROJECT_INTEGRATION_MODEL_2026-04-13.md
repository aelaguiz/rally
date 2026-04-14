---
title: "Rally - External Project Integration Model"
date: 2026-04-13
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/LESSONS_RALLY_PORT_GAP_READ_2026-04-13.md
  - src/rally/cli.py
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/run_store.py
  - src/rally/adapters/codex/launcher.py
  - ../paperclip_agents
---

# TL;DR

## Outcome

Rally can run from another repo, such as `../paperclip_agents`, without
treating the Rally source tree as the only valid home. The host repo becomes
the Rally workspace. Rally itself provides the runtime and built-in shared
parts.

## Problem

Today Rally treats its own repo root as the place that owns `flows/`,
`skills/`, `mcps/`, `stdlib/`, and `runs/`. The CLI, build path, loader,
run-store, and home setup all lean on that assumption. That blocks a clean
external-project story and makes Rally feel trapped inside its own source tree.

## Approach

Split the current single "repo root" idea into two clear roots:

- the Rally framework root, which owns the installed runtime code and Rally's
  built-in shared assets
- the Rally workspace root, which is the repo being operated on and owns the
  authored flows, local skills, local MCPs, and `runs/`

Then move every build-time and run-time path decision onto that workspace
contract. Rally-owned built-ins should sync into fixed workspace paths before
build and run so the workspace stays self-contained. Build should invoke
Doctrine from Rally's installed environment against the workspace manifest, not
through a sibling source checkout. The current Rally repo should keep working
as one workspace, and an external repo should work the same way after it ports
one flow.

## What shipped

1. Add one workspace manifest, one workspace resolver, and one fail-loud
   built-in asset boundary.
2. Move CLI, build, load, run, issue-ledger, home setup, and adapter envs onto
   that shared workspace contract.
3. Update shared prompts, generated readback, and live docs so they all teach
   the same root model.
4. Prove the contract in both this Rally repo and one external repo, starting
   with `../paperclip_agents` after a Rally-native flow port lands there.

## Status

Phases 1 through 4 were implemented on 2026-04-13.
Fresh `audit-implementation` on 2026-04-13 found the full approved
implementation frontier code-complete.

Current proof keeps both paths honest:

- `uv run pytest tests/unit -q` passes on current head
- Rally also proved the workspace contract in `../paperclip_agents`

## Non-negotiables

- No command may depend on the Rally source checkout being the workspace.
- No hidden machine-global Rally state.
- `runs/` stays in the workspace repo, not in the Rally install tree.
- `paperclip_agents` is a proof target, not a framework primitive.
- There must be one front-door workspace-root rule, not one rule per command.
- If Doctrine cannot consume Rally's built-in shared assets cleanly through the
  chosen boundary, we stop and name that Doctrine gap instead of patching
  around it in Rally.


