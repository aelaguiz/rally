---
title: "Rally - Software Engineering Flow Showcase"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_RUNTIME.md
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - pyproject.toml
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/SKILL_PACKAGE_AUTHORING.md
  - ../doctrine/docs/WORKFLOW_LAW.md
  - ../paperclip_agents/doctrine/prompts/core_dev/AGENTS.prompt
  - ../paperclip_agents/doctrine/prompts/core_dev/common/role_home.prompt
---

# TL;DR

## Outcome

Add a new Rally flow, `software_engineering_demo`, that starts from
`home/issue.md`, bootstraps a demo repo when none exists, keeps work growing on
top of the last accepted demo branch, and runs this loop:

`Architect -> ArchitectReviewer -> Developer -> DeveloperReviewer -> QaDocsTester -> QaReviewer`

The flow ends only when `QaReviewer` says the issue is truly done.

## Problem

Rally can run a simple Doctrine-authored flow today, but it does not yet have a
good demo for real software work. Rally now has a real mixed-skill path, with
Doctrine-authored `rally-kernel` readback living beside markdown skills, but it
still lacks the demo repo branch-history contract, per-turn commit rules, and
honest repo bootstrap for a repeatable engineering loop.

## Approach

Use the fullest clean Doctrine surface we already have for prompts: abstract
agents, shared workflows, typed inputs and outputs, routed review behavior,
Doctrine `review_family`, workflow law, and skill-package emit. Keep the shared
ledger in `home:issue.md` as the one cross-turn note surface. Make agents read
the repo and deterministic tools directly instead of injecting extra prompt
summaries each turn. Keep producer routing on Doctrine `final_output.route`,
keep review routing on split review JSON, then let Rally copy that JSON into
one `Rally Turn Result` block for each successful turn.

## What shipped

1. Reuse the shipped mixed-skill path and add `demo-git` as the showcase's
   second Doctrine-authored skill beside current markdown skills.
2. Add the demo repo bootstrap, dirty-git guardrails, and carry-forward branch
   history path.
3. Author the new flow as a Doctrine showcase with explicit reviewer lanes and
   the real skill mix it will use.
4. Prove the loop on a blank demo repo and then on a second issue that builds
   on the first run, then sync the live docs to shipped truth.

## Non-negotiables

- `home/issue.md` stays the only shared run ledger.
- No second handoff artifact, packet, or sidecar control path.
- Every producer turn goes straight to its matching reviewer.
- Only `QaReviewer` may end the flow as done.
- Every turn that changes the demo repo must commit before handoff.
- New issues must branch from the last accepted demo tip instead of starting
  from scratch.
- If planning finds a real Rally or Doctrine gap, we stop and talk about that
  gap before we plan around it.
- Doctrine source stays in `.prompt` files and generated readback stays
  generated.
- The demo stays self-contained to this repo and must not depend on hidden
  machine-global state.

## Status

Implemented on 2026-04-13.
The approved implementation frontier is complete.

Current proof keeps the showcase honest:

- Doctrine rebuilds landed for `_stdlib_smoke`, `poem_loop`,
  `software_engineering_demo`, and `demo-git`
- Rally now injects `AGENTS.md` plus a generated previous-turn appendix when a
  compiled contract asks for prior outputs
- the full unit suite passes on current head
- live `SED-3` and `SED-4` run artifacts proved the shipped loop
