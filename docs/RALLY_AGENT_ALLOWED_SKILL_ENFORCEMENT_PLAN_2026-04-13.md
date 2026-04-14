---
title: "Rally - Per-Agent Allowed Skill Enforcement - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/skill_bundles.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/claude_code/adapter.py
  - tests/unit/test_runner.py
---

# TL;DR

- Outcome: In a Rally run, each agent should only see `rally-kernel`, `rally-memory`, and the skills in that agent's own `allowed_skills`. No other skill should be present on the adapter-facing skill path for that turn.
- Problem this plan fixed: `flow.yaml` already stored per-agent
  `allowed_skills`, but `src/rally/services/home_materializer.py` used to copy
  the per-flow union into shared `home/skills/`, and both Codex and Claude
  used that broader path.
- Approach: Keep `flow.yaml` as the one source of truth, build per-agent skill views inside the run home, keep `home/skills/` as the one live adapter path, and switch that live path before each turn.
- Plan: Keep the shared Rally runtime in charge, split run-home skill refresh from per-turn skill activation, then prove first-run and resume behavior with unit coverage and synced design docs.
- Non-negotiables: No second skill registry. No prompt-only fake enforcement. No adapter-facing path that still exposes the per-flow union. Mandatory Rally built-ins stay available on every turn. Tests and docs ship in the same pass.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-14
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None. The full approved frontier is now complete.
  - Evidence anchors:
    - `src/rally/services/home_materializer.py:69`
    - `src/rally/services/home_materializer.py:316`
    - `src/rally/services/runner.py:652`
    - `tests/unit/test_runner.py:430`
    - `tests/unit/test_runner.py:538`
    - `tests/unit/test_runner.py:1050`
    - `docs/RALLY_MASTER_DESIGN_2026-04-12.md:190`
    - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:71`
    - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md:56`
    - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md:299`
  - Plan expects:
    - per-agent skill views refresh under `home/sessions/<agent>/skills/` on
      start and resume
    - the current agent's view activates into live `home/skills/` before each
      turn
    - Codex and Claude keep their existing adapter contracts while seeing only
      the current agent's allowed skills plus built-ins
    - the named live runtime docs stop saying per-agent skill enforcement is
      missing or that `home/skills/` is a shared per-flow union
    - `uv run pytest tests/unit -q` stays green
  - Code reality:
    - `src/rally/services/home_materializer.py` refreshes stable per-agent
      views and fails loud when a prebuilt view is missing or out of sync.
    - `src/rally/services/runner.py` activates the current view before turn
      artifacts, prompt build, and adapter launch.
    - `tests/unit/test_runner.py` proves Codex first-run skill isolation,
      Claude resume skill isolation, mixed markdown and Doctrine skill sources,
      resume refresh, and stale skill removal.
    - the four named live runtime docs now describe per-agent skill views plus
      per-turn `home/skills/` activation, with MCP isolation left as the later
      gap.
    - `uv sync --dev` and `uv run pytest tests/unit -q` passed on 2026-04-14;
      the unit suite reported `204 passed`.
  - Fix:
    - No code fix remains.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-13
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

If a flow says agent A may use skill `x` and agent B may not, Rally will launch
agent A with `x` available through the adapter's normal skill-loading path, and
agent B will not be able to see or load `x` through that same path on either
first run or resume.

## 0.2 In scope

- Runtime enforcement for per-agent `allowed_skills` in the shared Rally runtime.
- The adapter-facing skill surface for both shipped adapters: `codex` and `claude_code`.
- The shared runtime owner path that builds per-agent skill views and activates the current agent's view.
- Keeping `flow.yaml` as the one source of truth for authored allowlists.
- Preserving support for both markdown skills and Doctrine-built skills.
- Full unit coverage for first run, resume, built-in skills, and disallowed-skill absence on the real adapter-facing surface.
- Doc updates for the live runtime design set when shipped behavior changes.

## 0.3 Out of scope

- Doctrine language or compiler changes.
- A new flow field, registry, or second config file for skills.
- MCP isolation. Codex and Claude build MCP access from separate config files today, and this plan does not change that path.
- Changing how skills are authored under `skills/*`.
- Adapter auth changes that do not affect skill visibility.

## 0.4 Definition of done (acceptance evidence)

- Rally launches each agent against a skill surface that contains only mandatory built-ins plus that agent's own `allowed_skills`.
- The same rule holds on both fresh runs and resumed runs.
- Mixed skill sources still work: markdown `SKILL.md` and Doctrine `build/SKILL.md`.
- Unit tests prove both presence and absence on the adapter-facing surface for Codex and Claude Code.
- `uv run pytest tests/unit -q` passes.
- The live runtime docs say the same thing as the shipped code about per-agent skill access.

## 0.5 Key invariants (fix immediately if violated)

- `flow.yaml` stays the one allowlist source of truth.
- `rally-kernel` and `rally-memory` stay present on every Rally-managed turn.
- A disallowed skill must not be reachable from the current agent's normal skill-loading path.
- First run and resume must use the same enforcement rule.
- `home/skills/` stays the one live adapter-facing skill path.
- No silent fallback to a shared union when agent-scoped setup fails.
- If Rally cannot build the right skill surface, the turn must fail loud before adapter launch.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Real runtime enforcement over prompt-only wording.
2. One source of truth for allowlists.
3. One clean shared runtime story across Codex and Claude Code.
4. No breakage for markdown and Doctrine skill sources.
5. Small operator surface with no new knobs.

## 1.2 Constraints

- Rally's fixed top-level layout stays `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/`.
- Codex gets `CODEX_HOME=<run_home>`.
- Claude Code links `home/.claude/skills` to a Rally-owned path under the run home.
- Rally already refreshes run-home assets on both `run` and `resume`.
- The repo already treats per-agent skill enforcement as a missing runtime feature, not as solved behavior.

## 1.3 Architectural principles (rules we will enforce)

- Enforce skill visibility at the adapter-facing filesystem boundary.
- Keep one runtime owner path for resolving and materializing allowed skills.
- Keep built-in skills as a small explicit mandatory set, not as a side door for broader exposure.
- Reuse the existing skill source-kind resolver instead of adding a second skill system.
- Fail loud when a required skill cannot be materialized.

## 1.4 Known tradeoffs (explicit)

- Agent-scoped skill views may cost a little more copy time or disk space than one shared union.
- Per-agent views will duplicate some copied skill files inside the run home.
- Resume behavior may need extra care if adapter session reuse assumes a stable live `home/skills/` tree.
- This work may leave MCP isolation as a later follow-up, even if the skill pattern becomes reusable there.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

`src/rally/services/flow_loader.py` loads per-agent `allowed_skills` into
`FlowAgent.allowed_skills`. `src/rally/services/home_materializer.py` then
unions every agent's skills plus mandatory built-ins and copies that full set
into shared `home/skills/`. Codex launches with `CODEX_HOME` set to the run
home, and Claude Code links `home/.claude/skills` to that same shared skill
tree.

## 2.2 What’s broken / missing (concrete)

The authored allowlist is narrower than the runtime skill surface. An agent may
be told in prompt text to use only its own skills, but the adapter-facing disk
layout can still expose other skills from the same flow. That means Rally does
not yet truly enforce the contract it authors.

## 2.3 Constraints implied by the problem

The fix must preserve the current flow model, keep mixed skill sources working,
cover both adapters, and stay honest on first run and resume. The current agent
is only known inside the turn loop, after run-home refresh. That means the
design needs both a run-home refresh step and a per-turn activation step. It
also had to update the live design docs that still described this as an open
gap.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- None needed for this pass — adopt repo-first grounding — the open choices are
  in Rally-owned runtime code, not in missing outside research.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/flow_loader.py` — loads `allowed_skills` and
    `allowed_mcps` per agent from `flow.yaml`; this is the authored allowlist
    truth Rally already trusts.
  - `src/rally/domain/flow.py` — stores `FlowAgent.allowed_skills` on the
    runtime object model; per-agent allowlists are already first-class runtime
    data.
  - `src/rally/services/home_materializer.py` —
    `_refresh_agent_skill_views`, `_copy_allowed_mcps`, and
    `activate_agent_skills` now split run-home refresh from live turn
    activation; that is the shipped enforcement path.
  - `src/rally/services/runner.py` — `_execute_single_turn` resolves the
    current agent before adapter launch, so Rally already knows the exact
    `agent.slug` and turn boundary where per-agent skill activation could
    happen.
  - `src/rally/adapters/codex/launcher.py` — Codex gets
    `CODEX_HOME=<run_home>`, so its skill view comes from the run-home
    filesystem Rally shapes.
  - `src/rally/adapters/claude_code/adapter.py` — `_sync_claude_skills` links
    `home/.claude/skills` to `home/skills`, so Claude also reads a Rally-owned
    on-disk skill surface.
  - `src/rally/services/skill_bundles.py` — resolves markdown versus Doctrine
    skill roots and validates emitted Doctrine `build/SKILL.md`; mixed skill
    sources are already a shared runtime contract.
  - `src/rally/services/flow_build.py` — `_load_flow_skill_names` unions flow
    skills for build orchestration; that union is valid for rebuilds, but it is
    not the runtime enforcement owner path.

- Canonical path / owner to reuse:
  - Shared Rally runtime between `src/rally/services/runner.py` turn execution,
    `src/rally/services/home_materializer.py` run-home sync, and adapter-owned
    bootstrap paths — this boundary should own real skill exposure.
  - `flow.yaml` plus `FlowAgent.allowed_skills` should stay the one allowlist
    truth; prompts and compiled `AGENTS.md` should describe the contract, not
    enforce it.

- Existing patterns to reuse:
  - `src/rally/services/home_materializer.py:_sync_named_directories` — Rally
    already knows how to replace named run-home trees cleanly.
  - `src/rally/services/home_materializer.py:_sync_compiled_agents` — agent
    assets are already materialized per slug under `home/agents/`; skill
    isolation can reuse that same per-agent thinking.
  - `src/rally/adapters/base.py:build_rally_launch_env` — the shared launch env
    already carries `RALLY_AGENT_SLUG` and turn number.
  - `src/rally/adapters/base.py:write_adapter_launch_record` — Rally already
    records per-turn adapter `cwd` and env facts, which can help prove the new
    boundary.

- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — Rally already gives every
    agent the mandatory built-ins `rally-kernel` and `rally-memory`.
  - `flows/software_engineering_demo/flow.yaml` — real flow with different
    authored allowlists: Architect and Critic do not get `pytest-local`, while
    Developer and QA do.
  - `flows/software_engineering_demo/build/agents/developer/AGENTS.md`,
    `flows/software_engineering_demo/build/agents/architect/AGENTS.md`, and
    `flows/software_engineering_demo/build/agents/critic/AGENTS.md` — compiled
    prompts already describe role-local skill intent, so runtime drift is the
    mismatch to remove.

- Native model or agent capabilities to lean on:
  - `codex` runtime — already loads its working world from `CODEX_HOME`; no new
    parser, wrapper, or skill registry is needed if Rally shapes the right
    filesystem.
  - `claude_code` runtime — already reads skills through the Rally-owned
    `.claude/skills` link; the same filesystem-shaping approach can work here
    too.

- Existing grounding / tool / file exposure:
  - `RALLY_AGENT_SLUG` in the shared launch env — Rally already tells the
    adapter which agent is active.
  - `run_home` in `adapter.invoke(...)` and `adapter.prepare_home(...)` —
    adapters already get the run-home root Rally controls.
  - `logs/adapter_launch/*.json` — existing launch proof can show which skill
    root or env facts were active for a turn if we expose them there.

- Duplicate or drifting paths relevant to this change:
  - `FlowAgent.allowed_skills` versus live `home/skills/` — this plan removed
    the old per-flow-union drift by activating the current agent's prebuilt
    view before each turn.
  - `flows/software_engineering_demo/build/agents/*.md` versus shared
    `home/skills/` — compiled prompts already imply narrower skill use than the
    runtime enforces.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` — live docs still say this is an
    open gap, so they must change when runtime truth changes.

- Capability-first opportunities before new tooling:
  - Use Rally's existing per-turn knowledge of `agent.slug` instead of adding a
    second skill registry.
  - Use adapter-owned filesystem inputs that already exist
    (`CODEX_HOME`, `.claude/skills`) instead of adding wrappers or prompt-time
    parsing tricks.
  - Reuse the current mixed skill-source resolver instead of inventing a new
    skill packaging path.

- Behavior-preservation signals already available:
  - `tests/unit/test_runner.py` — proves built-in skill materialization,
    run-home refresh on resume, and current allowlist-driven add/remove behavior
    at the shared `home/skills/` path.
  - `tests/unit/test_runner.py` — rejects Doctrine skills that are missing
    emitted `build/SKILL.md`, which protects mixed skill-source behavior.
  - `uv run pytest tests/unit -q` — repo-sanctioned proof path for runtime
    changes.

## 3.3 Decision gaps that must be resolved before implementation

- None blocking before implementation.
- Chosen shape from repo truth:
  - build per-agent skill views under `home/sessions/<agent>/skills/` on
    `run` and `resume`
  - keep `home/skills/` as the one live adapter-facing skill tree
  - activate the current agent's view into `home/skills/` before each turn
- MCP isolation stays out of this pass because Codex and Claude already read
  MCP access from separate generated config files, not from `home/skills/`.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `flows/*/flow.yaml` stores per-agent `allowed_skills` and `allowed_mcps`.
- `skills/*` stores markdown or Doctrine-authored skill sources.
- `runs/active/<run-id>/home/agents/<agent-slug>/AGENTS.md` is already copied
  per agent.
- `runs/active/<run-id>/home/skills/` is one shared live skill tree for the
  whole flow.
- `runs/active/<run-id>/home/mcps/` is one shared live MCP tree for the whole
  flow.
- `runs/active/<run-id>/home/sessions/<agent>/session.yaml` plus
  `turn-<n>/...` already gives Rally one stable per-agent state area in the run
  home.
- `runs/active/<run-id>/home/.claude/skills` is a symlink to `home/skills/`.
- `runs/active/<run-id>/home/config.toml` and
  `runs/active/<run-id>/home/claude_code/mcp.json` are generated from the
  shared `home/mcps/` tree.

## 4.2 Control paths (runtime)

1. `run_flow()` and `resume_run()` rebuild the flow, load `FlowAgent` records,
   and call `materialize_run_home()`.
2. `materialize_run_home()` syncs compiled agents, copies the union of allowed
   skills into `home/skills/`, copies the union of allowed MCPs into
   `home/mcps/`, then lets the adapter refresh adapter-owned files.
3. `CodexAdapter.prepare_home()` writes `home/config.toml` from the shared MCP
   tree and seeds auth links. `ClaudeCodeAdapter.prepare_home()` writes
   `home/claude_code/mcp.json` and links `.claude/skills` to `home/skills/`.
4. `_execute_single_turn()` resolves the current agent only after run-home
   materialization. There is no step that swaps the live skill tree to match
   that current agent before prompt build or adapter launch.
5. `adapter.invoke(...)` launches both shipped adapters with `cwd=run_home`.
   Codex also gets `CODEX_HOME=run_home`. Session reuse is keyed by agent slug,
   not by a per-agent home root.

## 4.3 Object model + key abstractions

- `FlowAgent.allowed_skills` is already the authored runtime truth.
- `MANDATORY_SKILL_NAMES` adds `rally-kernel` and `rally-memory` on every run.
- `SkillBundleSource.runtime_source_dir()` is the one source-kind seam for
  markdown versus Doctrine skills.
- `flow_build._load_flow_skill_names()` uses a flow-wide union for build
  orchestration. That is correct for rebuilds, but it is too broad for runtime
  skill enforcement.
- `runner._execute_single_turn()` is the first place Rally knows the exact
  current agent for a handoff chain.

## 4.4 Observability + failure behavior today

Rally fails loud for missing skills, missing Doctrine skill builds, missing MCP
definitions, and dirty guarded repos. It does not fail when an agent can see
extra skills, because the shared `home/skills/` tree is the current runtime
shape. Existing tests prove built-in skill presence, resume-time refresh, stale
capability removal across commands, and Claude's skill symlink, but they do not
yet prove per-agent skill isolation inside one multi-turn run.

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not UI work.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- `home/skills/` stays the one live adapter-facing skill tree for both shipped
  adapters.
- `home/sessions/<agent>/skills/` becomes the per-agent stable skill view for
  that run. Each view contains only mandatory built-ins plus that agent's own
  `allowed_skills`.
- `home/mcps/`, `home/config.toml`, and `home/claude_code/mcp.json` stay on
  their current path in this pass.

## 5.2 Control paths (future)

1. On `run` and `resume`, Rally refreshes per-agent skill views into
   `home/sessions/<agent>/skills/` from the current repo and framework sources.
2. Before each turn, Rally activates the current agent's prebuilt view into the
   live `home/skills/` tree.
3. Prompt build and adapter launch happen only after that activation step.
4. Codex keeps `CODEX_HOME=run_home` and `cwd=run_home`. Claude keeps
   `.claude/skills -> home/skills`. No adapter-specific skill registry is
   added.
5. Resume follows the same rule: refresh per-agent views on `resume`, then
   activate the current agent's view before the resumed session is launched.

## 5.3 Object model + abstractions (future)

- `FlowAgent.allowed_skills` plus `MANDATORY_SKILL_NAMES` stay the one source
  for the exact runtime skill set.
- `home_materializer` should own view refresh because it already copies skills
  into the run home from repo and framework roots.
- `runner` should own live activation because it already resolves the current
  agent before each turn.
- Adapters should keep consuming the shared live `home/skills/` tree. They
  should not rebuild allowlist logic or point at a second path.

## 5.4 Invariants and boundaries

- `flow.yaml` remains the only authored allowlist source.
- `skill_bundles.py` remains the only source-kind resolver.
- `home/skills/` is the only live adapter-facing skill tree.
- `home/sessions/<agent>/skills/` is internal run-home state, not a second
  adapter-facing interface.
- `home_materializer` owns per-agent skill-view refresh on `run` and `resume`.
- `runner` owns per-turn live skill activation before prompt build and adapter
  launch.
- No adapter may quietly fall back to a broader shared skill tree.
- No second skill registry, no hidden adapter-only rules, and no prompt-only
  enforcement story.
- MCP config stays on its current separate path in this pass.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not UI work.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Flow allowlist truth | `src/rally/services/flow_loader.py`, `src/rally/domain/flow.py` | `allowed_skills`, `FlowAgent.allowed_skills` | Per-agent allowlists already load cleanly | Preserve as the only authored allowlist source | Avoid a second registry | No new flow field | `tests/unit/test_runner.py` flow fixture coverage |
| Build-time skill union | `src/rally/services/flow_build.py` | `_load_flow_skill_names()` | Unions flow skills for Doctrine rebuilds | Keep build union for emit only; do not reuse it as runtime enforcement | Separate build scope from runtime scope | Build union is emit-only, not live runtime truth | Existing flow-build tests |
| Skill source resolution | `src/rally/services/skill_bundles.py` | `resolve_skill_bundle_source()`, `runtime_source_dir()` | Resolves markdown and Doctrine skills from repo or framework roots | Reuse as the one skill source-kind seam | Keep one skill story for both source kinds | Same source-kind contract feeds each per-agent skill view | `tests/unit/test_runner.py`, Doctrine-skill failure tests |
| Run-home skill refresh | `src/rally/services/home_materializer.py` | `materialize_run_home()`, `_refresh_agent_skill_views()`, `_copy_allowed_mcps()`, `_sync_named_directories()` | Refreshes one stable skill view per agent under `home/sessions/<agent>/skills/` and refreshes shared `home/mcps/` | Keep skill refresh in shared runtime code and leave live activation to the turn runner | This is the main runtime owner path | Run-home refresh builds one stable skill view per agent | `tests/unit/test_runner.py` |
| Per-turn activation | `src/rally/services/runner.py` | `_execute_single_turn()` | Resolves current agent, then builds prompt and launches adapter with no skill activation step | Activate the current agent's prebuilt view into `home/skills/` before prompt build and adapter launch | Multi-turn handoffs only become honest here | Every turn uses the current agent's exact live skill tree | `tests/unit/test_runner.py` |
| Codex adapter contract | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/codex/launcher.py` | `prepare_home()`, `invoke()`, `build_codex_launch_env()` | Codex reads the run home through `CODEX_HOME` and `cwd=run_home` | Preserve this launch contract; do not add Codex-only skill config | Keep one shared runtime story | Codex keeps using the live `home/skills/` tree | Codex runner tests |
| Claude adapter contract | `src/rally/adapters/claude_code/adapter.py` | `prepare_home()`, `_sync_claude_skills()` | Claude links `.claude/skills` to shared `home/skills` | Preserve this link target; let per-turn activation change what that target contains | Keep one shared runtime story | Claude keeps using the live `home/skills/` tree | Claude runner tests |
| MCP config path | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/claude_code/adapter.py` | `_write_codex_config()`, `_build_mcp_config()` | Both adapters build MCP access from separate generated config files | Keep unchanged in this plan | Skill isolation can ship cleanly without MCP isolation | MCP path stays per-flow for now | Existing MCP config tests |
| Runtime docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md` | runtime design text | Several docs still say per-agent skill enforcement is a gap | Update in the same pass as code | Keep repo truth aligned | One truthful runtime story | Doc inspection |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - refresh per-agent skill views in `home_materializer`
  - activate the current view in `runner`
  - keep `home/skills/` as the one live adapter-facing tree
- Deprecated APIs (if any):
  - none
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - delete the runtime use of a flow-wide skill union as the source for live
    `home/skills/`
  - delete doc text that still says per-agent skill enforcement is missing once
    the code ships
- Capability-replacing harnesses to delete or justify:
  - none
  - do not add prompt-only policing, adapter-only registries, grep checks, or
    wrappers around existing skill loading
- Live docs/comments/instructions to update or delete:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
  - one short code comment at the skill activation boundary if the split
    between refresh and activation would be easy to break later
- Behavior-preservation signals for refactors:
  - `uv run pytest tests/unit -q`
  - existing `tests/unit/test_runner.py` coverage for built-ins, resume-time
    refresh, stale capability removal across commands, and Claude's skill link
  - targeted new runner tests for per-agent skill activation on Codex and
    Claude

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Shared skill enforcement | `src/rally/services/home_materializer.py`, `src/rally/services/runner.py` | Refresh per-agent skill views on `run` and `resume`, then activate one live view before each turn | Keeps Codex and Claude on one runtime rule | include |
| Shared live skill path | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/claude_code/adapter.py` | Keep `home/skills/` as the only live adapter-facing skill tree | Prevents adapter drift and second registries | include |
| Build versus runtime split | `src/rally/services/flow_build.py` | Keep flow-wide skill union for build only | Prevents build helpers from leaking back into runtime enforcement | include |
| MCP isolation | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/claude_code/adapter.py` | Separate per-agent MCP exposure | Same policy family, but not required to ship skill enforcement | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Refresh per-agent skill views in the run home

- Goal: Build one stable per-agent skill view for every agent under the current
  run home without changing the adapters' live skill path yet.
- Status: COMPLETE
- Completed work:
  - split `src/rally/services/home_materializer.py` into
    `_refresh_agent_skill_views`, `_copy_allowed_mcps`, and
    `activate_agent_skills`
  - refreshes one stable skill view per agent under
    `home/sessions/<agent>/skills/` on both `run` and `resume`
  - keeps missing skill, missing Doctrine build, and out-of-sync prebuilt
    skill-view failures loud
- Work:
  - refactor `src/rally/services/home_materializer.py` so skill refresh no
    longer writes the flow-wide union directly to live `home/skills/`
  - add shared helpers that resolve one agent's exact skill set from
    `FlowAgent.allowed_skills` plus `MANDATORY_SKILL_NAMES`
  - materialize those per-agent views under `home/sessions/<agent>/skills/`
    using the existing markdown-versus-Doctrine resolver in
    `src/rally/services/skill_bundles.py`
  - keep MCP copy behavior unchanged under `home/mcps/`
  - keep missing skill and missing Doctrine-build failures loud
- Verification (required proof):
  - targeted runner or home-materializer tests that prove per-agent skill-view
    directories are created on `run` and refreshed on `resume`
  - existing mixed-source failure coverage still passes for Doctrine skills
- Docs/comments (propagation; only if needed):
  - add one short code comment where the refresh logic splits from live
    activation if that boundary would be easy to blur later
- Exit criteria:
  - the run home contains one stable per-agent skill view for each flow agent
  - the exact contents of each view match mandatory built-ins plus that
    agent's own `allowed_skills`
  - MCP paths and adapter config generation still behave as they do today
- Rollback:
  - revert the new per-agent refresh helpers and restore the prior shared
    `home/skills/` materialization path

## Phase 2 - Activate the current agent's live skill tree before each turn

- Goal: Make `home/skills/` reflect only the current agent's allowed skills on
  every launched turn.
- Status: COMPLETE
- Completed work:
  - adds the runner-owned activation step before prompt build and adapter
    launch in `src/rally/services/runner.py`
  - keeps Codex on `CODEX_HOME=run_home`, keeps Claude on
    `.claude/skills -> home/skills`, and leaves session reuse by agent slug
    unchanged
  - added a short boundary comment where refresh and live activation split
- Work:
  - add a runner-owned activation step before prompt build and adapter launch
    in `src/rally/services/runner.py`
  - switch live `home/skills/` to the current agent's prebuilt view before
    `_build_agent_prompt(...)` and `adapter.invoke(...)`
  - preserve existing adapter contracts:
    - Codex still uses `CODEX_HOME=run_home` and `cwd=run_home`
    - Claude still uses `.claude/skills -> home/skills`
  - keep session reuse by agent slug unchanged
  - make activation fail loud if the current agent's prebuilt skill view is
    missing or incomplete
- Verification (required proof):
  - focused tests for a multi-turn run where one agent is allowed a skill and a
    later agent is not
  - focused tests that prove the live `home/skills/` tree changes with the
    current agent on both Codex and Claude paths
  - existing resume-time refresh and stale capability removal tests still pass
- Docs/comments (propagation; only if needed):
  - keep or add one high-leverage comment at the live activation boundary if it
    would otherwise be easy to reintroduce a flow-wide union
- Exit criteria:
  - each launched turn sees only mandatory built-ins plus the current agent's
    allowed skills through the normal adapter-facing path
  - no adapter-specific skill registry, wrapper, or extra config path is added
  - first run and resumed runs follow the same activation rule
- Rollback:
  - revert the activation step and restore the last known working shared live
    tree behavior

## Phase 3 - Sync tests, docs, and stale runtime truth

- Goal: Leave one truthful shipped story for runtime skill enforcement.
- Status: COMPLETE
- Completed work:
  - added Codex and Claude runner coverage for per-turn skill isolation and
    tightened resume refresh assertions around `home/sessions/<agent>/skills/`
  - made the runner fixtures self-contained for built-in Doctrine skills so the
    proof path does not depend on ignored local readback, then re-emitted
    `poem_loop` and `software_engineering_demo` readback against current
    Doctrine source
  - partially updated the stale live-doc sections the prior implementation audit
    named:
    - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
    - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
  - reran a stale-text search over the named live runtime docs after that pass,
    but the fresh audit below found another stale `home/skills/` refresh claim
  - fixed the remaining showcase live-truth line so it now says Rally refreshes
    `home/sessions/<agent>/skills/` on start or resume and activates live
    `home/skills/` before each turn
  - reran the stale-text search over the four named live runtime docs after the
    final showcase fix and got no matches
  - reran `uv run pytest tests/unit -q` after the reopen fix and kept the
    proof green
  - fresh implementation audit accepted the full approved frontier as complete:
    runtime code, tests, and named live runtime docs now match the shipped
    per-agent skill rule
  - verification ran clean:
    - `uv sync --dev`
    - `uv run pytest tests/unit/test_runner.py -q`
    - `uv run pytest tests/unit -q`
- Work:
  - update or replace existing tests that still encode the old shared-union
    runtime assumption
  - run the full unit proof path
  - update the live runtime docs:
    - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
    - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
    - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
    - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
  - remove or rewrite stale text that still calls per-agent skill enforcement a
    missing gap
- Verification (required proof):
  - `uv run pytest tests/unit -q`
  - readback inspection of the live runtime docs against the shipped code paths
- Docs/comments (propagation; only if needed):
  - sync the surviving runtime docs to current truth in the same pass
  - delete dead wording instead of preserving historical caveats in live docs
- Exit criteria:
  - unit tests pass
  - live docs describe the shipped per-agent runtime skill rule accurately
  - no stale runtime truth remains in the touched docs
- Rollback:
  - revert doc updates with the code if the runtime behavior does not ship
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

Prefer focused tests that prove the current agent can see its own skills and
cannot see disallowed ones on the real adapter-facing surface. Reuse existing
runner and home-materialization coverage before adding new helpers. The
highest-value checks are:

- per-agent view refresh under `home/sessions/<agent>/skills/`
- live `home/skills/` activation before each turn
- Codex and Claude both reading the same live tree through their current
  adapter contract

## 8.2 Integration tests (flows)

Keep at least one flow-backed test that exercises first run and resume across a
real flow definition with mixed skill sources. This should prove the runtime
contract, not just a helper in isolation. At least one test should cover a
multi-turn handoff where one agent is allowed a skill that the next agent is
not.

## 8.3 E2E / device tests (realistic)

A light demo-flow smoke check is enough if unit and runner tests already prove
the runtime boundary. Do not invent a new harness just for this plan.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Ship as one hard cutover in Rally runtime. Do not add a fallback flag that
keeps the shared-union path alive.

## 9.2 Telemetry changes

Use current launch records and runtime events where possible. If debugging
needs more signal, add a small fact about the resolved agent skill surface
rather than a new operator feature.

## 9.3 Operational runbook

If a skill is missing or unexpectedly present, inspect:

- the flow's `allowed_skills`
- the live `home/skills/` tree for the active turn
- the stored `home/sessions/<agent>/skills/` view for that agent
- the adapter launch record for the affected turn

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator, cold-read pass 1, cold-read pass 2
- Scope checked:
  - frontmatter, `# TL;DR`, and `# 0)` through `# 10)`
  - `planning_passes`, research, deep-dive blocks, phase plan, and Decision Log
  - agreement across owner path, live skill path, delete list, proof plan, and doc follow-through
- Findings summary:
  - the doc now says one consistent thing about the chosen runtime shape:
    per-agent views under `home/sessions/<agent>/skills/`, one live
    adapter-facing `home/skills/` tree, refresh on `run` and `resume`,
    activation before each turn
  - MCP isolation is consistently out of scope and does not conflict with the
    chosen skill design because MCP access already comes from separate generated
    config files
  - Section 3.3 had one stale phrase tied to deep-dive pass 1 instead of the
    current planning state
- Integrated repairs:
  - updated Section 3.3 from `None blocking after deep-dive pass 1.` to
    `None blocking before implementation.`
  - added this consistency-pass block after checking that Sections 5, 6, 7, 8,
    and 9 all still match the chosen owner path and proof burden
- Remaining inconsistencies:
  - none
- Unresolved decisions:
  - none
- Unauthorized scope cuts:
  - none
- Decision-complete:
  - yes
- Decision: proceed to implement? yes
<!-- arch_skill:block:consistency_pass:end -->

# 10) Decision Log (append-only)

## 2026-04-13 - Treat per-agent skill enforcement as a real runtime gap

Context

Rally already authors per-agent `allowed_skills`, but the shipped runtime still
copies the per-flow union into shared `home/skills/`, and both shipped adapters
read from that shared surface.

Options

- Keep the current shared-union runtime and rely on prompt wording.
- Add a second allowlist registry closer to the adapters.
- Enforce the authored allowlist through one shared runtime skill-surface path.

Decision

Plan around the third option. Keep `flow.yaml` as the one authored truth and
make runtime enforcement real at the adapter-facing filesystem boundary.

Consequences

The work must touch shared runtime code plus both shipped adapters, and it must
ship with tests and doc updates in the same pass.

Follow-ups

- Resolve the exact agent-scoped skill root during `research` and `deep-dive`.
- Decide whether MCP isolation can stay out of scope for this pass.

## 2026-04-13 - Keep one live `home/skills/` tree and switch it per turn

Context

The current agent is only known in `_execute_single_turn()`, after Rally has
already refreshed the run home. Both shipped adapters already read skills from
the run home: Codex through `CODEX_HOME=run_home`, and Claude through
`.claude/skills -> home/skills`.

Options

- Keep the shared flow-wide union in `home/skills/`.
- Give each agent its own full run home or adapter-specific skill root.
- Prebuild one skill view per agent inside the run home, then activate the
  current agent's view into `home/skills/` before each turn.

Decision

Choose the third option. Build stable per-agent skill views under
`home/sessions/<agent>/skills/`, keep `home/skills/` as the one live
adapter-facing tree, and switch that live tree before each turn.

Consequences

Rally keeps one shared adapter story and one live skill path. The runtime needs
both a refresh step on `run` and `resume` and an activation step inside the
turn loop. MCP isolation stays out of scope because current MCP access is built
from separate generated config files.

Follow-ups

- Phase-plan the exact helper split between `home_materializer` and `runner`.
- Add targeted Codex and Claude tests for per-turn skill activation.

## 2026-04-13 - Ship per-agent skill views and live turn activation

Context

The approved plan called for one shared runtime rule across Codex and Claude:
refresh stable per-agent skill views on `run` and `resume`, then activate the
current agent's live `home/skills/` tree before each turn.

Options

- keep the per-flow union in `home/skills/`
- add adapter-specific skill roots or registries
- ship the shared runtime split between per-agent view refresh and per-turn
  live activation

Decision

Shipped the third option. `home_materializer` now owns per-agent skill-view
refresh, `runner` now owns live turn activation, and both adapters keep using
the same live `home/skills/` path they already knew.

Consequences

The runtime now enforces `allowed_skills` at the adapter-facing filesystem
boundary on fresh runs and resumes. The remaining capability gap is per-agent
`allowed_mcps`, not skills.

Follow-ups

- Let the fresh `audit-implementation` child write the authoritative
  implementation-audit block for this plan.
