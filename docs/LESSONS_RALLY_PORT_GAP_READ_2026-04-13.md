---
title: "Lessons Rally Port Gap Read"
date: 2026-04-13
status: reference
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: port_audit
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_AGENT_ALLOWED_SKILL_ENFORCEMENT_PLAN_2026-04-13.md
  - docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13.md
  - src/rally/services/runner.py
  - src/rally/services/issue_ledger.py
  - src/rally/services/home_materializer.py
  - src/rally/services/flow_loader.py
---

# Summary

If we port Lessons into Rally idioms instead of trying to preserve Paperclip's
runtime shell, the true Rally-core gap list is short.

I overstated Paperclip control-plane features that we can simply collapse away
in a linear, single-run, `issue.md`-centric Rally flow.
The list is even shorter now that per-agent skill isolation shipped on
2026-04-14. The remaining runtime gap is MCP handling, not skill handling.

# Drops Out

- Rally does not need Paperclip's issue/comment/assignment/project/workspace
  control plane. In a Rally port, the baton is just final JSON `next_owner`,
  and same-owner continuation already works because `handoff` can target any
  agent, including the same one
  (`src/rally/services/runner.py:1252`,
  `src/rally/services/runner.py:1447`).
- Rally does not need heartbeats, wake queues, or missed-handoff sweeps. The
  Lessons lead's heartbeat logic exists because Paperclip has async idle
  ownership; Rally runs synchronously until `done`, `blocker`, or the command
  cap
  (`/Users/aelaguiz/workspace/paperclip_agents/doctrine/prompts/lessons/agents/lessons_project_lead/AGENTS.prompt:71`,
  `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:47`).
- Rally does not need parallel mutable workspaces, assignment governance, or
  "same project `in_progress` issues" logic. One active run per flow and no
  parallel execution side-step that whole class of problems
  (`docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:38`).
- Rally does not need separate Paperclip issue comments as first-class
  objects. If we adopt an `issue.md` convention, the durable handoff/verdict
  surface is just appended note blocks in `home/issue.md`; Rally already
  snapshots the whole file after each append
  (`src/rally/services/issue_ledger.py:64`).
- Rally does not need a generic shared file-state carrier for this port. In an
  `issue.md`-only Lessons flow, "current artifact" becomes "latest typed lane
  block in `issue.md`," and invalidation becomes reduction logic in the flow's
  parser, not runtime state
  (`docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md:64`).

# Needs Porting, But Not Rally Core

- A shared Lessons `issue.md` block grammar. Each lane still needs a stable
  structure for plan, producer handoff, critic verdict, metadata follow-up,
  and route-only turns. This replaces Paperclip comments plus the old
  multi-file carrier. Current `rally issue note` is already enough to append
  arbitrary Markdown bodies and preserve snapshots
  (`src/rally/services/issue_ledger.py:21`,
  `src/rally/services/issue_ledger.py:198`).
- A Lessons prompt-input reducer. Rally already supports one flow-level
  `prompt_input_command` that gets `RALLY_AGENT_KEY`, `RALLY_RUN_HOME`, and
  `RALLY_ISSUE_PATH` and can emit arbitrary JSON
  (`src/rally/services/runner.py:811`). That script can derive the things
  Paperclip used to give the agents: route-only facts, producer-handoff
  completeness, active review mode, failing gates, metadata route facts,
  symbolic root resolution, and downstream invalidation state
  (`/Users/aelaguiz/workspace/paperclip_agents/doctrine/prompts/lessons/common/control_plane.prompt:5`,
  `/Users/aelaguiz/workspace/paperclip_agents/doctrine/prompts/lessons/contracts/materialization.prompt:9`).
- A Rally-native Lessons coordination shell. The substantive lesson rules in
  the prompts mostly survive; what changes is the shared wrapper in
  `lessons.common.role_home`, which currently assumes Paperclip issues,
  comments, and reassignment
  (`/Users/aelaguiz/workspace/paperclip_agents/doctrine/prompts/lessons/common/role_home.prompt:23`).
  That should become Rally kernel + `issue.md` convention + final JSON.
- A flow setup script for the attached checkout and tools. Rally already has
  the right hook for this via `setup_home_script`; that is where the `psmobile`
  checkout, helpers, env files, and auth wiring should be staged
  (`src/rally/services/home_materializer.py:340`).
- A real Lessons flow definition in `flow.yaml` with the role graph and
  per-agent allowlists. Rally already supports arbitrary multi-agent graphs and
  per-agent allowed skill lists; that is config work, not a runtime feature
  gap (`src/rally/services/flow_loader.py:29`).
- A small shared parser/helper library in Rally stdlib would help. Things like
  "latest current block," "latest accepted review," and "current metadata
  mode" should probably be reused, but that belongs in `stdlib/rally/` or the
  Lessons flow, not the runtime core.

# True Rally Runtime Gaps

- Per-agent skill isolation is no longer a runtime gap. Rally now refreshes
  one stable skill view per agent under `home/sessions/<agent>/skills/` and
  switches the live `home/skills/` tree before each turn
  (`docs/RALLY_MASTER_DESIGN_2026-04-12.md:196`,
  `docs/RALLY_AGENT_ALLOWED_SKILL_ENFORCEMENT_PLAN_2026-04-13.md:26`).
- Per-agent MCP handling is still the clear runtime gap. Rally still copies
  the union of all allowed MCPs into shared `home/mcps/`
  (`src/rally/services/home_materializer.py:407`), while the live runtime docs
  still call out per-agent `allowed_mcps` enforcement and per-agent MCP
  isolation as follow-up work
  (`docs/RALLY_MASTER_DESIGN_2026-04-12.md:219`,
  `docs/RALLY_MASTER_DESIGN_2026-04-12.md:613`). The narrower Codex readiness
  gap is now closed: Rally marks the shared Codex-visible MCP set as
  `required = true`, checks it before the turn starts, and keeps the same
  access story for child agents from that prepared run home
  (`docs/RALLY_MASTER_DESIGN_2026-04-12.md:366`,
  `docs/RALLY_MASTER_DESIGN_2026-04-12.md:384`).
- First-class structured note metadata would be useful, but it is not
  required. We can store fenced JSON or YAML inside note bodies today. A typed
  `rally issue note` mode would reduce brittle parsing, but I would treat it
  as a quality upgrade, not a blocker.
- Declarative prompt-input contracts would also be useful, but not required.
  Right now `prompt_input_command` is one untyped JSON blob pipe
  (`src/rally/services/runner.py:811`,
  `src/rally/services/flow_loader.py:65`). Lessons can work with that. If we
  want safer support later, Rally could validate required prompt-input
  sections against compiled metadata.

# Not Rally

- `route_only`, `review_family`, `current none`, `current artifact`,
  `carry active_mode`, and `invalidate ... via
  coordination_handoff.current_truth.invalidations` are authored-language
  concerns, not Rally runtime concerns. Rally only cares about the compiled
  agent readback, the final JSON schema, and the flow graph
  (`src/rally/services/flow_loader.py:133`). If the paired Doctrine snapshot
  can compile those constructs, Rally needs nothing special. If it cannot,
  that is a Doctrine-first blocker.
- `SOUL.md` is not a Rally blocker. Home sync already copies the entire
  compiled agent directory, not just `AGENTS.md`
  (`src/rally/services/home_materializer.py:267`).

# Closeout

The corrected exhaustive read is: most of the Lessons support work belongs in
a Rally-native Lessons flow, its shared prompt library, and its issue-state
reducer. The strongest remaining runtime feature gap is broader per-agent MCP
handling, not the now-shipped Codex required-MCP readiness slice. Per-agent
skill isolation is already shipped. Everything else from Paperclip that looked
scary in the first pass mostly disappears once you take Rally's linear,
synchronous, `issue.md`-first design seriously.
