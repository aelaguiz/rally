---
title: "Rally - Software Engineering Flow Showcase - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
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

`Architect -> Critic -> Developer -> Critic -> QaDocsTester -> Critic`

The flow ends only when Critic says the issue is truly done.

## Problem

Rally can run a simple Doctrine-authored flow today, but it does not yet have a
good demo for real software work. Rally now has a real mixed-skill path, with
Doctrine-authored `rally-kernel` readback living beside markdown skills, but it
still lacks the demo repo branch-history contract, per-turn commit rules, and
honest repo bootstrap for a repeatable engineering loop.

## Approach

Use the fullest clean Doctrine surface we already have for prompts: abstract
agents, shared workflows, typed inputs and outputs, role `grounding`, routed
review behavior, Doctrine `review_family`, workflow law, and skill-package
emit. Pair that with Rally's existing `runtime.prompt_input_command` so
grounding can stand on real run facts like branch name, git cleanliness,
carry-forward source, and the latest accepted critic verdict. Keep
`route_only` as a small Critic-only escape hatch for control states that have
no real artifact to review.

## Plan

1. Reuse the shipped mixed-skill path and add `demo-git` as the showcase's
   second Doctrine-authored skill beside current markdown skills.
2. Add the demo repo bootstrap, runtime fact input path, dirty-git guardrails,
   and carry-forward branch history path.
3. Author the new flow as a Doctrine showcase with explicit grounding and the
   real skill mix it will use.
4. Prove the loop on a blank demo repo and then on a second issue that builds
   on the first run, then sync the live docs to shipped truth.

## Non-negotiables

- `home/issue.md` stays the only shared run ledger.
- No second handoff artifact, packet, or sidecar control path.
- Critic runs after every owner turn and is the only owner that can end the
  flow as done.
- Every turn that changes the demo repo must commit before handoff.
- New issues must branch from the last accepted demo tip instead of starting
  from scratch.
- If planning finds a real Rally or Doctrine gap, we stop and talk about that
  gap before we plan around it.
- Doctrine source stays in `.prompt` files and generated readback stays
  generated.
- The demo stays self-contained to this repo and must not depend on hidden
  machine-global state.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: skipped 2026-04-13 (repo-grounded planning was sufficient)
deep_dive_pass_2: done 2026-04-13
recommended_flow: deep dive -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can ship one self-contained software-engineering demo flow that feels
real, shows off the best current Doctrine surface, and exposes the next missing
Rally features by trying to use them in live flow code instead of in fake
examples.

This claim is true only if a user can:

- start the flow with a plain issue in `home/issue.md`
- get a usable demo repo even when no prior demo repo exists
- see each owner commit after a code-changing turn
- finish on Critic only when the issue is truly met
- start a later issue and branch from the last accepted demo work
- use at least one Doctrine-authored skill package and at least one normal
  markdown skill in the same flow

## 0.2 In scope

- A new flow at `flows/software_engineering_demo/` with code `SED`.
- Four concrete owners:
  - `architect`
  - `developer`
  - `qa_docs_tester`
  - `critic`
- A hard route shape where every specialist turn goes to Critic next.
- A demo repo at `home/repos/demo_repo`.
- First-run bootstrap that creates a blank demo repo when there is no accepted
  prior demo history.
- Later-run bootstrap that starts a new issue branch from the last accepted
  demo branch tip.
- One commit rule for every repo-changing turn.
- One Doctrine-authored demo git skill package with bundled helper files.
- Doctrine `grounding` for Architect, Developer, QaDocsTester, and Critic so
  each role says what facts it may trust before it acts.
- One flow-local `runtime.prompt_input_command` reducer that feeds grounding
  with current git, branch, carry-forward, and latest-review facts.
- Continued support for current markdown skills like `repo-search` and
  `pytest-local` beside Doctrine-authored `rally-kernel` and `demo-git`.
- Only the narrow mixed-skill runtime follow-up needed to use the shipped
  Doctrine skill path cleanly in this demo.
- Rally runtime work needed to fail loud on dirty git state at handoff when
  the flow requires a commit.
- Flow build, skill build, generated readback, tests, and one real demo proof
  path.
- Naming and documenting real Rally and Doctrine gaps that show up while we
  try to keep the design clean.
- Stopping to talk with the user when planning itself hits a real Rally or
  Doctrine gap.

Allowed architectural convergence scope:

- add or reshape Rally build and run-home copy code so prompt-authored skills
  can live beside markdown skills cleanly
- add the narrow carry-forward repo history, branch, and commit support needed
  for this flow
- add flow-local setup and helper code that stays inside Rally's repo-first,
  filesystem-first model
- update current design docs in the same pass when runtime truth changes

## 0.3 Out of scope

- A generic multi-repo workflow product.
- A GUI, dashboard, or database-owned control plane.
- A second shared brief file or a second trusted handoff surface.
- Silent cleanup, silent retries, or hidden git repair.
- Editing the paired Doctrine repo as part of normal Rally implementation.
- Generic concurrent active runs for one flow.
- A fake demo that skips real branch, commit, or repo state.

## 0.4 Definition of done (acceptance evidence)

The work is done only when all of this is true:

- `software_engineering_demo` compiles from `.prompt` source into generated
  flow readback.
- The new demo git skill compiles from `SKILL.prompt` into generated skill
  readback.
- Rally keeps copying both Doctrine-authored and markdown-authored skills into
  one run home.
- The flow uses Doctrine `grounding` to make each role's allowed facts
  explicit.
- The flow feeds grounding through `runtime.prompt_input_command` instead of
  a second control plane or repeated shell rediscovery in every role.
- A first run can create a blank demo repo and finish one issue through the
  full owner loop.
- The git history in that demo repo shows one commit after each code-changing
  owner turn.
- A second issue can start from the last accepted demo branch tip and create a
  new issue branch on top of earlier work.
- Critic is the only owner that can finish the flow with `done`.
- Rally unit tests pass for the touched runtime surfaces.
- The smallest honest live proof path runs and its result is written down.
- Any missing Doctrine or Rally features found during the work are named
  plainly in this doc instead of being patched around.
- If planning itself hits a real Rally or Doctrine gap, the planning pass stops
  there and that gap is discussed before work continues.

Behavior-preservation evidence:

- existing Rally flow build still works for `_stdlib_smoke` and `poem_loop`
- existing markdown skill copy still works
- existing Doctrine `rally-kernel` build and copy still work
- the current run, resume, and issue-ledger rules still hold

## 0.5 Key invariants (fix immediately if violated)

- `home/issue.md` is still the one shared run ledger.
- Final JSON is still the one trusted turn-ending control path.
- No hand-written build output under `flows/*/build/**`.
- No hidden Rally state under `~/.rally`, `~/.config`, or similar paths.
- No fake "commit succeeded" claim when the demo repo is still dirty.
- No new parallel skill system that makes Doctrine skills and markdown skills
  feel like two different products.
- No hidden fact sidecar outside `home/issue.md`, the current demo repo, and
  the flow's runtime prompt inputs.
- No branch reset that discards earlier accepted demo work.
- No planning-around of a real Rally or Doctrine gap without first stopping and
  talking about it.
- No Rally-side patch around a missing Doctrine feature when the clean answer
  is "Doctrine first."

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep the authored flow and skills elegant enough to feel like a Doctrine
   showcase, not a Rally workaround pile.
2. Make the demo honestly useful for repeated software issues, not a one-shot
   smoke test.
3. Surface real Rally gaps by trying to use the flow for real work.
4. Keep the runtime filesystem-first and repo-first.
5. Preserve current Rally behavior for existing flows, existing markdown
   skills, and the shipped Doctrine `rally-kernel` path.

## 1.2 Constraints

- The shared ledger must stay `home/issue.md`.
- The flow must stay self-contained to this repo.
- Rally still rebuilds flows from paired Doctrine targets in `pyproject.toml`.
- Rally currently copies the union of allowed skills into one run home.
- Rally already resolves skill roots as either markdown `SKILL.md` or Doctrine
  `prompts/SKILL.prompt`, and it validates emitted `build/SKILL.md` before
  materializing Doctrine skills.
- Doctrine `emit_skill` works through configured targets today. It does not
  yet have the direct `--entrypoint` and `--output-dir` mode that `emit_flow`
  has.

## 1.3 Architectural principles (rules we will enforce)

- Keep one flow-owned demo repo path: `home/repos/demo_repo`.
- Keep one branch per issue run, stacked on the last accepted demo tip.
- Keep one commit checkpoint per code-changing owner turn.
- Keep one flow skill story: Rally already loads markdown skills and
  Doctrine-emitted skills through one shared copy path, and the demo must keep
  using that one path.
- Express role facts with Doctrine `grounding` before adding repeated prose
  like "read the repo first" in every owner prompt.
- Use Rally `runtime.prompt_input_command` for branch, git, carry-forward, and
  latest-review facts instead of making each owner rediscover them alone.
- Reuse Doctrine features before adding local prompt prose or local control
  code.
- Keep `route_only` limited to Critic control states that truly have no real
  artifact to review.
- If planning finds a real Rally or Doctrine gap, stop and talk about it
  before choosing a workaround, fallback, or narrowed plan.
- Fail loud on dirty git state, missing compiled readback, and missing branch
  history facts.

## 1.4 Known tradeoffs (explicit)

- The cleanest long-term skill-build story may need a Doctrine improvement, but
  the first Rally pass can still use named `emit_skill` targets in
  `pyproject.toml`.
- The cleanest long-term carry-forward repo history story may become a reusable
  Rally service, but the first pass can truthfully bootstrap from existing run
  data under `runs/` if that keeps the design simple.
- Per-agent skill isolation is a real Rally gap today. The showcase should not
  pretend that gap is solved before it is solved.
- Accepted first-pass limit: authored role-local skill allowlists may stay true
  in flow source while runtime skill exposure is still the per-flow union in
  `home/skills/`. The plan should treat that as a real Rally gap, not as
  solved behavior.
- Current runtime now refreshes `home/agents/`, `home/skills/`, `home/mcps/`,
  and `config.toml` on every start or resume, while still keeping
  `setup_home_script` behind the one-time home-ready marker. That closes the
  earlier capability-refresh blocker and becomes a behavior we must keep.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally ships one simple runnable flow, `poem_loop`, that proves the
  issue-ledger-first loop.
- `src/rally/services/flow_build.py` now rebuilds flows with
  `doctrine.emit_docs` and rebuilds allowed Doctrine skill targets with
  `doctrine.emit_skill`.
- `src/rally/services/skill_bundles.py` now resolves skill roots as markdown
  or Doctrine sources and enforces that a skill declares exactly one source
  kind.
- `src/rally/services/home_materializer.py` copies allowed skills through that
  shared source-kind resolver and materializes Doctrine skills from `build/`.
- `src/rally/services/home_materializer.py` copies the per-flow union of
  allowed skills and MCPs into one run home.
- `src/rally/services/home_materializer.py` refreshes `home/agents/` on every
  start or resume, and it now refreshes skills, MCPs, and `config.toml` before
  it checks the home-ready marker.
- `setup_home_script` already gives a clean hook for run-home bootstrap.
- Rally already has a good front-door note skill in
  `skills/rally-kernel/prompts/SKILL.prompt`, emitted to
  `skills/rally-kernel/build/`.
- Doctrine already ships the language pieces we want for a richer demo:
  abstract agents, shared workflows, review families, workflow law, typed
  outputs, route semantics, `grounding`, and `skill package`.
- Rally already supports flow-level `runtime.prompt_input_command`, so the
  showcase can inject live run facts into the prompt without changing the core
  turn contract.

## 2.2 What’s broken / missing (concrete)

- There is no real software-engineering showcase flow in Rally yet.
- There is no clean demo-repo bootstrap and branch-history contract.
- There is no handoff-time git cleanliness rule for flows that require a
  commit after each turn.
- There is no proof flow today that pressures Critic-as-finisher across
  architect, developer, and QA/docs/test work on one shared issue ledger.

## 2.3 Constraints implied by the problem

- The flow must lean on real repo state, git state, and run-home state.
- The prompt design should use Doctrine features on purpose so missing support
  shows up fast.
- The flow should make "what facts count as real" explicit instead of burying
  that rule in repeated prose.
- The runtime changes must stay narrow and reusable. This demo should reveal
  missing framework seams, not add demo-only magic.
- The planning process itself must stop on real framework gaps instead of
  smoothing over them.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/LANGUAGE_REFERENCE.md` — adopt Doctrine-owned prompt
  features such as abstract agents, routed outputs, `review_family`,
  `grounding`, and `skill package`; reject inventing a second Rally-only
  prompt language — the showcase should push the shipped Doctrine surface
  first.
- `../doctrine/docs/LANGUAGE_REFERENCE.md` — keep `route_only` as a limited
  Critic adjunct for control-only states with no real artifact; reject making
  the main review loop `route_only` because the flow is supposed to be a real
  software review loop, not a routing demo.
- `../doctrine/docs/SKILL_PACKAGE_AUTHORING.md` — adopt `SKILL.prompt` plus
  source-root bundled files as the first Doctrine skill shape; reject adding a
  second Rally-only skill-package format — Doctrine already owns this package
  model.
- `../doctrine/doctrine/emit_skill.py` and `../doctrine/docs/EMIT_GUIDE.md` —
  adopt named-target `emit_skill` as the path Rally already ships for
  Doctrine-authored skills; reject adding a second skill registry in Rally;
  note a real Doctrine gap that does not block this plan: direct
  `emit_skill --entrypoint ... --output-dir ...` mode does not exist today.
- `../doctrine/docs/WORKFLOW_LAW.md` — adopt compiler-owned route semantics and
  output truth for the critic loop; reject prose-only routing for this showcase
  because the whole point is to show the richer Doctrine path.
- `../paperclip_agents/doctrine/prompts/core_dev/AGENTS.prompt` and
  `../paperclip_agents/doctrine/prompts/core_dev/common/role_home.prompt` —
  adopt the family pattern where specialist turns route through Critic; reject
  its extra artifact surfaces as-is because Rally must stay `home/issue.md`
  first.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/flow_build.py` — current canonical flow build path; it
    runs `doctrine.emit_docs` for flows and `doctrine.emit_skill` for allowed
    Doctrine skills today.
  - `src/rally/services/home_materializer.py` — current run-home sync and skill
    copy path; it refreshes `home/skills/`, `home/mcps/`, and `config.toml` on
    each start or resume, and still copies the union of all agent allowlists
    into one shared `home/skills/`.
  - `src/rally/services/skill_bundles.py` — current skill source-kind contract;
    it resolves markdown versus Doctrine roots and validates emitted Doctrine
    skill readback before runtime copy.
  - `src/rally/services/flow_loader.py` — current `flow.yaml` contract,
    including `allowed_skills`, `allowed_mcps`, `runtime.prompt_input_command`,
    and `setup_home_script`.
  - `src/rally/services/run_store.py` — active and archived run model, flow
    replacement, and monotonic run ids; archived runs already give a
    filesystem-first source for carry-forward demo repo history.
  - `src/rally/services/runner.py` — `rally run --new` archives the old active
    run before the next run starts, which gives the demo a real place to pick
    up prior repo state.
  - `src/rally/services/runner.py:_load_prompt_inputs` — Rally already runs
    the flow's prompt-input reducer per turn and passes `RALLY_AGENT_KEY`,
    `RALLY_AGENT_SLUG`, `RALLY_FLOW_CODE`, `RALLY_ISSUE_PATH`,
    `RALLY_RUN_HOME`, and `RALLY_RUN_ID`.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — current Rally-managed role
    contract, required `rally-kernel`, and shared note/final-JSON rules.
- Canonical path / owner to reuse:
  - `src/rally/services/flow_build.py` — already owns Doctrine flow and
    Doctrine skill build orchestration; the setup script should not become a
    second builder.
  - `src/rally/services/home_materializer.py` — should own copying skills into
    `home/skills/` and any future source-kind split between markdown skills and
    compiled Doctrine skills.
  - `src/rally/services/skill_bundles.py` — should stay the one place that
    decides whether a skill root is markdown or Doctrine.
  - `flows/*/setup/*.sh` through `setup_home_script` — should own demo repo
    bootstrap inside the run home; runtime files still must not author
    instructions.
  - `src/rally/services/run_store.py` plus archived run homes under
    `runs/archive/` — should own first-pass carry-forward source discovery for
    prior demo repo state.
- Existing patterns to reuse:
  - `pyproject.toml` emit targets plus `tests/unit/test_flow_build.py` — one
    named target per emitted flow already exists, and Rally already uses the
    same target model for `rally-kernel`; `demo-git` should reuse that model
    instead of adding a second registry.
  - `tests/unit/test_flow_loader.py` prompt-input coverage plus
    `src/rally/services/runner.py:_load_prompt_inputs` — the runtime fact pipe
    already exists, so grounding can use a flow-local reducer instead of a new
    runtime feature.
  - `tests/unit/test_runner.py` setup-home fixture path — existing proof path
    for flow setup and run-home behavior.
  - `src/rally/services/runner.py` plus `tests/unit/test_runner.py` archive
    behavior — existing filesystem-first replacement path for starting a new
    issue on top of earlier work.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — shared Rally-managed
    inputs, required kernel skill, and final JSON rules.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — shared turn-ending
    schema.
  - `flows/poem_loop/prompts/AGENTS.prompt` — current Doctrine-authored
    issue-ledger-first flow pattern.
  - `skills/rally-kernel/prompts/SKILL.prompt` plus
    `skills/rally-kernel/build/SKILL.md` — current front-door note boundary.
- Native model or agent capabilities to lean on:
  - Codex runtime plus Rally launch rules — shell access, repo file access, git
    commands, and direct `AGENTS.md` prompt injection already exist, so the
    showcase does not need a parser or wrapper to fake git work.
- Existing grounding / tool / file exposure:
  - `src/rally/services/home_materializer.py` — prepares `home/repos/`,
    `home/skills/`, `home/mcps/`, and `home/sessions/`.
  - `src/rally/services/home_materializer.py` — passes `RALLY_RUN_HOME`,
    `RALLY_WORKSPACE_DIR`, `RALLY_CLI_BIN`, `RALLY_RUN_ID`,
    `RALLY_FLOW_CODE`, and `RALLY_ISSUE_PATH` into `setup_home_script`.
  - `src/rally/services/flow_loader.py` — loads flow-owned `allowed_skills` and
    `setup_home_script`.
  - `src/rally/services/runner.py:_load_prompt_inputs` — appends flow-owned
    runtime JSON inputs to the compiled prompt before each turn.
- Duplicate or drifting paths relevant to this change:
  - `skills/*/SKILL.md` versus `skills/*/prompts/SKILL.prompt` — this is the
    mixed skill-source seam Rally now owns through `skill_bundles.py`.
  - `FlowAgent.allowed_skills` in `src/rally/domain/flow.py` versus the
    per-flow union copy in `src/rally/services/home_materializer.py` — authored
    role boundaries do not match runtime exposure today.
- `docs/LESSONS_RALLY_PORT_GAP_READ_2026-04-13.md` — this repo already argues
  for flow-local prompt-input reducers when a flow needs route or review facts,
  so the showcase can reuse that direction instead of inventing a new control
  path.
- Capability-first opportunities before new tooling:
  - reuse `setup_home_script` and archived run homes before adding a repo
    registry or database
  - reuse `pyproject.toml` emit targets before adding a Rally-side Doctrine
    skill registry
  - reuse Doctrine `review_family`, routed outputs, and workflow law before
    adding extra deterministic critic scaffolding
- Behavior-preservation signals already available:
  - `tests/unit/test_flow_build.py` — protects flow build orchestration
  - `tests/unit/test_flow_loader.py` — protects flow config loading and
    compiled contract checks
  - `tests/unit/test_runner.py` — protects setup execution, run-home
    preparation, run replacement, and current skill copy behavior
  - `tests/unit/test_run_store.py` — protects archive behavior and run-id
    allocation

## 3.3 Decision gaps that must be resolved before implementation

- No new blockers remain from deep-dive pass 2.
- The earlier capability-refresh gap is now resolved in
  `src/rally/services/home_materializer.py`, and
  `tests/unit/test_runner.py` now covers both capability refresh and stale
  capability removal on resume.
- Accepted first-pass limitation:
  - authored per-agent skill boundaries already exist, but Rally still copies
    the per-flow union of skills into one shared `home/skills/`
  - checked `src/rally/services/home_materializer.py`,
    `src/rally/domain/flow.py`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md` first
  - user accepted this as a known Rally limitation for the first demo, so the
    plan may continue while still recording it as unresolved framework work
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `pyproject.toml`
  - today it declares two Doctrine flow emit targets plus one Doctrine skill
    target:
    - `_stdlib_smoke`
    - `poem_loop`
    - `rally-kernel`
- `flows/<flow>/prompts/**`
  - Doctrine prompt source
- `flows/<flow>/build/agents/**`
  - generated flow readback that Rally loads at runtime
- `skills/<skill>/SKILL.md`
  - current markdown skill source shape
- `skills/<skill>/prompts/SKILL.prompt`
  - current Doctrine skill source shape
- `skills/<skill>/build/**`
  - generated Doctrine skill readback that Rally materializes at runtime
- `runs/active/<run-id>/home/`
  - current prepared run world
  - already includes `agents/`, `skills/`, `mcps/`, `sessions/`, `artifacts/`,
    and `repos/`
- `runs/archive/<run-id>/`
  - archived prior run homes already exist and keep full on-disk history

## 4.2 Control paths (runtime)

Current command path for one flow:

1. `src/rally/services/runner.py:run_flow` or `resume_run`
   - takes the flow lock
   - calls `src/rally/services/flow_build.py:ensure_flow_assets_built`
2. `ensure_flow_assets_built`
   - runs `doctrine.emit_docs` for one named flow target
   - runs `doctrine.emit_skill` for allowed Doctrine skills such as
     `rally-kernel`
3. `src/rally/services/flow_loader.py:load_flow_definition`
   - reads `flow.yaml`
   - validates compiled agent contracts
4. `src/rally/services/home_materializer.py:prepare_run_home_shell`
   - creates the run-home shell
5. `src/rally/services/home_materializer.py:materialize_run_home`
   - requires non-empty `home/issue.md`
   - syncs compiled agents into `home/agents/`
   - refreshes the union of allowed skills and MCPs into `home/skills/` and
     `home/mcps/` on every start or resume
   - resolves each skill root as markdown or Doctrine before copy
   - rewrites `config.toml` on every start or resume
   - runs `setup_home_script` once
6. `src/rally/services/runner.py:_execute_until_stop`
   - chains turns until `done`, `blocker`, runtime failure, or command turn cap
7. `src/rally/services/runner.py:_execute_single_turn`
   - builds the prompt from generated `AGENTS.md`
   - invokes Codex
   - parses final JSON
   - writes the next run state and issue-log records

Current fresh-run replacement path:

1. `rally run <flow> --new`
2. `src/rally/services/runner.py:_maybe_archive_replaced_run`
3. `src/rally/services/run_store.py:archive_run`
4. prior run moves to `runs/archive/<run-id>/`
5. new run starts at the next run id

## 4.3 Object model + key abstractions

- `src/rally/domain/flow.py:FlowAgent`
  - already models per-agent `allowed_skills` and `allowed_mcps`
- `src/rally/domain/flow.py:FlowDefinition`
  - owns the loaded runtime facts for one flow
- `src/rally/services/flow_build.py`
  - currently owns flow and Doctrine skill build orchestration
- `src/rally/services/home_materializer.py`
  - currently owns skill copy, MCP copy, config writing, auth links, and setup
- `src/rally/services/skill_bundles.py`
  - currently owns mixed skill source-kind resolution
- `src/rally/services/runner.py`
  - owns run chaining, turn execution, and turn-result acceptance
- `flows/*/setup/*.sh`
  - already own flow-local run-home bootstrap work

## 4.4 Observability + failure behavior today

- Rally already logs:
  - lifecycle events
  - per-agent logs
  - adapter launch records
  - issue-log snapshots
- Rally already fails loud on:
  - missing or blank `home/issue.md`
  - missing compiled agents
  - missing emitted Doctrine `build/SKILL.md` or missing markdown `SKILL.md`
  - setup-script failures
  - non-interactive `--new` confirmation path
- Rally does not yet log or enforce:
  - Doctrine skill-build origin
  - guarded git repo cleanliness before handoff or done
  - carry-forward demo repo source selection

## 4.5 UI surfaces (ASCII mockups, if UI work)

Not a UI feature. No mockup needed.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- `flows/software_engineering_demo/flow.yaml`
  - flow code `SED`
  - four concrete owners
  - new runtime field:
    - `guarded_git_repos`
    - first pass value: `["repos/demo_repo"]`
    - `prompt_input_command`
    - first pass value: `setup/prompt_inputs.py`
- `flows/software_engineering_demo/prompts/**`
  - Doctrine source for the showcase flow, including shared role grounding
    rules
- `flows/software_engineering_demo/build/agents/**`
  - generated flow readback
- `flows/software_engineering_demo/setup/prepare_home.sh`
  - flow-local demo repo bootstrap
- `flows/software_engineering_demo/setup/prompt_inputs.py`
  - flow-local runtime fact reducer for grounding
- `skills/demo-git/prompts/SKILL.prompt`
  - Doctrine skill-package source
- `skills/demo-git/build/**`
  - generated Doctrine skill-package readback
- markdown skills stay source-owned where they already live:
  - `skills/repo-search/SKILL.md`
  - `skills/pytest-local/SKILL.md`
- Doctrine `rally-kernel` stays source-owned where it already lives:
  - `skills/rally-kernel/prompts/SKILL.prompt`
  - `skills/rally-kernel/build/**`
- `pyproject.toml`
  - adds one flow emit target for `software_engineering_demo`
  - adds one Doctrine skill emit target per Doctrine-authored skill
  - first-pass naming rule:
    - skill target name matches the skill slug
    - example: `demo-git`

## 5.2 Control paths (future)

Future build and run path:

1. `ensure_flow_assets_built`
   - rebuilds the flow with `emit_docs`
   - reads flow-owned allowed skills from `flow.yaml`
   - rebuilds any allowed Doctrine skill root through `emit_skill`
2. `materialize_run_home`
   - keeps current refresh-on-resume behavior for skills, MCPs, and
     `config.toml`
   - resolves each skill source kind by root file presence:
     - `SKILL.md` only -> markdown skill source
     - `prompts/SKILL.prompt` only -> Doctrine skill source
     - both or neither -> fail loud
   - copies markdown skills from source roots
   - copies Doctrine skills from `skills/<skill>/build/`
3. `setup_home_script`
   - owns demo repo bootstrap inside `home/repos/demo_repo`
   - first run:
     - creates a blank git repo
     - creates the first commit so branch-based follow-up work is possible
   - later run:
     - scans archived `SED-*` runs under `runs/archive/`
     - picks the newest archived run whose state is `done` and whose demo repo
       exists
     - copies that repo, including `.git`, into the new run home
   - then creates one new issue branch for the current run
4. `runner._execute_single_turn`
   - calls the flow-owned `runtime.prompt_input_command`
   - appends runtime facts to the compiled prompt before the turn runs
   - first pass fact set should include:
     - current issue branch name
     - current git clean or dirty state for `repos/demo_repo`
     - carry-forward source run id, if one exists
     - latest accepted Critic block facts reduced from `home/issue.md`
   - grounding reads these facts as inputs; the reducer does not become a
     second instruction source
5. `runner._execute_single_turn`
   - remains the only turn-execution entrypoint
   - after Codex returns a non-sleep turn result and before Rally accepts that
     result as routable or final, Rally checks each `guarded_git_repos` path
   - if any guarded repo is dirty, Rally blocks the run instead of honoring the
     handoff or done result
6. Flow routing
   - Architect, Developer, and QaDocsTester always route to Critic next
   - Critic routes to the next real owner or finishes with `done`
   - if Critic hits a real control-only state with no artifact to review, it
     may use a narrow `route_only` branch instead of faking a review

## 5.3 Object model + abstractions (future)

- `src/rally/services/flow_build.py`
  - stays the canonical build owner for Rally-managed compiled artifacts
  - already owns doctrine-skill build orchestration
- `src/rally/services/home_materializer.py`
  - stays the canonical run-home copy owner
  - already owns runtime copy for mixed markdown and Doctrine skills
- `src/rally/services/skill_bundles.py`
  - stays the canonical source-kind resolver for mixed markdown and Doctrine
    skills
- `src/rally/domain/flow.py:FlowDefinition`
  - gains `guarded_git_repos`
- `src/rally/services/flow_loader.py`
  - validates `runtime.guarded_git_repos`
- `src/rally/services/runner.py`
  - gains one narrow guarded-repo cleanliness check
- `setup_home_script`
  - stays the owner of flow-local repo bootstrap logic
  - does not become a second instruction source or skill registry

Prompt versus deterministic split:

- Doctrine prompt source owns:
  - role homes
  - role grounding rules over `home/issue.md`, the current demo repo, the
    latest accepted Critic result, and runtime prompt facts
  - routed owner graph
  - critic review structure
  - limited Critic `route_only` control branches when there is no real
    artifact to judge
  - issue-ledger behavior guidance
- Deterministic Rally/runtime code owns:
  - runtime prompt fact reduction
  - build orchestration
  - source-kind resolution
  - guarded git cleanliness checks
  - archived-run discovery for carry-forward repo bootstrap
  - run-home copy rules

## 5.4 Invariants and boundaries

- Prompt and skill source of truth:
  - flow instructions live in `.prompt`
  - Doctrine skill packages live in `prompts/SKILL.prompt`
  - markdown skills live in `SKILL.md`
- Grounding fact boundary:
  - Doctrine grounding may rely on `home/issue.md`, the current demo repo,
    the latest accepted Critic notes in the ledger, and runtime prompt inputs
  - it must not rely on hidden sidecars or adapter-local state
- Runtime skill source-kind rule:
  - exactly one of markdown `SKILL.md` or Doctrine `prompts/SKILL.prompt`
    may define a skill root
- Prompt-input boundary:
  - `runtime.prompt_input_command` may reduce facts for the prompt
  - it does not author instructions or replace final JSON routing
- Build ownership:
  - Rally owns when build happens
  - Doctrine owns how prompt and skill compilation works
- Carry-forward repo history source:
  - first pass uses archived run homes only
  - no DB, registry, or second repo-history sidecar
- Git cleanliness:
  - guarded repos must be clean before Rally accepts handoff or done
- Capability refresh:
  - run-home skills, MCPs, and `config.toml` refresh on every `run` and
    `resume`
  - `setup_home_script` still stays one-time behind the home-ready marker
- Accepted first-pass limitation:
  - runtime skill exposure may still be the per-flow union
  - do not claim per-agent skill isolation at runtime

## 5.5 UI surfaces (ASCII mockups, if UI work)

Not a UI feature. No mockup needed.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Doctrine flow build target | `pyproject.toml` | `[[tool.doctrine.emit.targets]]` | only `_stdlib_smoke` and `poem_loop` flow targets exist | add `software_engineering_demo` target | Rally must compile the new flow | one named flow target per runnable flow | flow build tests |
| Doctrine skill build targets | `pyproject.toml` | `[[tool.doctrine.emit.targets]]` | `rally-kernel` Doctrine skill target already exists | add a second Doctrine skill target for `demo-git` | reuse the shipped `emit_skill` path instead of planning a new one | skill target name matches skill slug | flow build tests |
| Build orchestration | `src/rally/services/flow_build.py` | `ensure_flow_assets_built` | already rebuilds flows and allowed Doctrine skills before run start | extend existing orchestration to cover `demo-git` through flow allowlists | keep build ownership in one runtime path | build flow plus Doctrine skill packages from flow-owned allowlists | flow build tests |
| Flow runtime contract | `src/rally/domain/flow.py` | `FlowDefinition` | no guarded repo list | add `guarded_git_repos` to the loaded flow contract | runner needs a typed runtime source for git guards | `runtime.guarded_git_repos: [run-home-relative path, ...]` | flow loader tests |
| Flow loader | `src/rally/services/flow_loader.py` | `load_flow_definition` | validates adapter, turn cap, prompt inputs, and setup script only | load and validate `guarded_git_repos` and the new flow's prompt-input reducer path | keep new runtime facts in `flow.yaml`, not in code constants | non-empty list of run-home-relative repo paths plus one flow-local `runtime.prompt_input_command` path | flow loader tests |
| Skill source-kind resolution | `src/rally/services/skill_bundles.py`, `src/rally/services/home_materializer.py` | `resolve_skill_bundle_source`, `_copy_allowed_skills_and_mcps`, `materialize_run_home` | already resolves markdown versus Doctrine skill roots and copies Doctrine skills from `build/` | reuse the shipped mixed-skill path for `demo-git` and keep failure cases honest | keep one skill product story | exactly one source kind per skill root; Doctrine skills copy from `build/` | runner tests |
| Guarded git repo check | `src/rally/services/runner.py` | `_execute_single_turn` after `load_turn_result` and before accepted state write | no repo cleanliness check exists | block the run if any guarded repo is dirty | enforce the commit-after-turn rule honestly | guarded repo dirtiness blocks handoff or done | runner tests |
| Run replacement source | `src/rally/services/run_store.py`, `src/rally/services/runner.py` | `archive_run`, `_maybe_archive_replaced_run` | archives prior active run and increments run id | reuse archived runs as the carry-forward demo repo source | avoid a second repo-history registry | newest archived done `SED-*` run is the first-pass carry-forward source | runner tests, run store tests |
| Demo flow runtime config | `flows/software_engineering_demo/flow.yaml` | new file | flow does not exist | declare owners, allowlists, start owner, setup script, guarded repos, and turn cap | ship the showcase flow contract | `SED` runtime contract | flow loader and build tests |
| Prompt-input reducer | `flows/software_engineering_demo/setup/prompt_inputs.py` | new file | no flow-local runtime fact reducer exists | emit current branch, git, carry-forward, and latest-review facts for grounding | make grounding stand on real run facts instead of repeated rediscovery | one JSON fact payload appended through `runtime.prompt_input_command` | runner tests and live proof |
| Demo flow prompts | `flows/software_engineering_demo/prompts/**` | new files | flow does not exist | author shared role home, role grounding, owners, routes, Critic review, and a limited `route_only` control path if a true no-artifact state exists | showcase Doctrine features on a real software-work loop | new flow prompt graph | compile/readback inspection |
| Demo repo bootstrap | `flows/software_engineering_demo/setup/prepare_home.sh` | new file | no demo repo bootstrap exists | create or copy `home/repos/demo_repo`, then create the issue branch | make the demo real and repeatable | first-run blank repo, later-run copy from newest archived done run | runner tests and live proof |
| Doctrine skill package | `skills/demo-git/**` | new files | `rally-kernel` already proves Doctrine skills in Rally today | add a second script-backed Doctrine skill package for the demo | prove the showcase uses the shipped mixed-skill path, not a one-off | `prompts/SKILL.prompt` plus bundled references/scripts and generated `build/` | compile/readback inspection |
| Runtime docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` | live design docs | current docs do not describe Doctrine skill builds or guarded git repos | sync the docs in the same pass if runtime truth changes | keep repo truth aligned | updated runtime doc truth | doc inspection |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - build orchestration stays in `src/rally/services/flow_build.py`
  - skill copy stays in `src/rally/services/home_materializer.py`
  - turn-result acceptance and git guards stay in `src/rally/services/runner.py`
  - demo repo bootstrap stays in `flows/software_engineering_demo/setup/prepare_home.sh`
- Deprecated APIs (if any):
  - none in the first pass
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - no second skill registry
  - no repo-history DB or sidecar state
  - no flow-name hardcoding for demo repo support
  - no prose-only backup handoff path
- Capability-replacing harnesses to delete or justify:
  - do not add a git wrapper daemon, repo registry, or branch-tracking sidecar
    when existing git state plus archived runs already give enough truth
- Live docs/comments/instructions to update or delete:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - any new flow-local docs or comments that would otherwise claim per-agent
    runtime skill isolation was solved
- Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_build.py`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_runner.py`
  - `tests/unit/test_run_store.py`
  - existing `_stdlib_smoke` and `poem_loop` build/readback checks

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Doctrine skill builds | `src/rally/services/flow_build.py:ensure_flow_assets_built` | reuse existing Doctrine skill builds from flow-owned allowlists and `pyproject.toml` targets | avoids a second skill-build story | include |
| Mixed skill copy | `src/rally/services/skill_bundles.py`, `src/rally/services/home_materializer.py` | reuse the shipped source-kind resolver for markdown and Doctrine skills | avoids split runtime behavior for skills | include |
| Guarded git repos | `src/rally/services/flow_loader.py`, `src/rally/services/runner.py` | one reusable `guarded_git_repos` runtime field | avoids flow-name hardcoded git checks | include |
| Runtime fact input | `flows/software_engineering_demo/setup/prompt_inputs.py`, `src/rally/services/runner.py:_load_prompt_inputs` | one flow-local prompt-input reducer that feeds Doctrine grounding | avoids repeated "check branch/check repo/check latest critic note" prompt prose and shell rediscovery | include |
| Carry-forward repo source | `flows/software_engineering_demo/setup/prepare_home.sh` | scan archived done runs before inventing a registry | keeps the first pass filesystem-first | include |
| Critic control-only states | `flows/software_engineering_demo/prompts/**` | limited `route_only` branch only when there is no artifact to review | avoids forcing fake reviews while keeping the main loop artifact-based | include |
| Existing markdown skills | `skills/repo-search`, `skills/pytest-local` | convert to Doctrine `SKILL.prompt` | not required to ship the demo | defer |
| Per-agent skill isolation | `src/rally/services/home_materializer.py` | runtime role-local skill exposure | real gap, but user accepted it as first-pass limitation | defer |
| Generic previous-run helper | `src/rally/services/run_store.py` or new helper module | reusable helper for “newest archived done run with repo path” | may be useful later, but setup script can own the first pass | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 — Reuse the shipped mixed-skill foundation

* Goal:
  Reuse the shipped mixed-skill path, prove it stays clean, and add `demo-git`
  on top of it without breaking current flows.
* Status: IN PROGRESS
* Completed work:
  - verified the shipped mixed-skill path already exists through
    `skills/rally-kernel/prompts/SKILL.prompt`,
    `skills/rally-kernel/build/`, `flow_build.ensure_flow_assets_built`,
    `skill_bundles.resolve_skill_bundle_source`, and
    `home_materializer._copy_allowed_skills_and_mcps`
  - verified the `implement-loop` Stop-hook preflight is green for this Codex
    session and armed execution is allowed to start
* Work:
  - treat `skills/rally-kernel/prompts/SKILL.prompt` plus
    `skills/rally-kernel/build/` as shipped proof that Rally already supports
    Doctrine-authored skills
  - add the real `skills/demo-git/prompts/SKILL.prompt` source root and its
    `pyproject.toml` emit target so the showcase uses the same path for a
    second Doctrine skill
  - reuse `src/rally/services/flow_build.py`,
    `src/rally/services/skill_bundles.py`, and
    `src/rally/services/home_materializer.py` without reopening that design
    unless the demo exposes a real gap
  - keep `rally-kernel` mandatory and keep current markdown skills working
* Verification (required proof):
  - `uv run pytest tests/unit/test_flow_build.py -q`
  - `uv run pytest tests/unit/test_runner.py -q`
  - inspect emitted `skills/rally-kernel/build/**` as the baseline proof
  - inspect emitted `skills/demo-git/build/**`
* Docs/comments (propagation; only if needed):
  - update `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` for the mixed-skill source
    model and the refresh-on-resume rule once the code lands
* Exit criteria:
  - one run home still contains markdown skills plus Doctrine `rally-kernel`
    and Doctrine `demo-git` cleanly
  - `_stdlib_smoke` and `poem_loop` still build and current markdown skills
    still materialize correctly
* Rollback:
  - drop `demo-git` and keep using the shipped `rally-kernel` mixed-skill path

## Phase 2 — Demo repo bootstrap and dirty-git guardrails

* Goal:
  Make `software_engineering_demo` run against a real demo repo that stacks
  across issues and blocks dirty handoffs.
* Work:
  - add `guarded_git_repos` to the loaded flow contract in
    `src/rally/domain/flow.py` and `src/rally/services/flow_loader.py`
  - add the guarded-repo cleanliness check in `src/rally/services/runner.py`
    before Rally accepts handoff or done
  - add `flows/software_engineering_demo/setup/prepare_home.sh` so first run
    creates a blank repo plus seed commit, while later runs copy the newest
    archived done `SED-*` repo including `.git`
  - create one new issue branch per run and keep the carry-forward source
    filesystem-first with no registry or sidecar
  - keep the runtime facts needed for later grounding aligned with the real git
    and bootstrap rules so the flow does not teach against stale repo state
* Verification (required proof):
  - `uv run pytest tests/unit/test_flow_loader.py -q`
  - `uv run pytest tests/unit/test_runner.py -q`
  - inspect setup-script behavior in a prepared run home before the live proof
* Docs/comments (propagation; only if needed):
  - update the same live runtime docs for `guarded_git_repos`, archived-run
    carry-forward, and the one-time `setup_home_script` rule
  - add one short setup-script comment only where a failure mode would be hard
    to see later
* Exit criteria:
  - runtime can load guard config, block dirty handoffs, and prepare a real
    demo repo contract for first and later runs
* Rollback:
  - remove the guard field and demo bootstrap path and leave the new flow
    unshipped

## Phase 3 — Author the showcase flow and Doctrine skill surfaces

* Goal:
  Ship the actual `software_engineering_demo` flow and its authored skill
  surfaces as a Doctrine showcase.
* Work:
  - create `flows/software_engineering_demo/flow.yaml` with owners, allowlists,
    turn cap, setup script, guarded repo path, and
    `runtime.prompt_input_command: setup/prompt_inputs.py`
  - author `flows/software_engineering_demo/setup/prompt_inputs.py` so each
    turn gets the branch, git, carry-forward, and latest accepted Critic facts
    that grounding needs
  - author `flows/software_engineering_demo/prompts/**` with a shared role
    home, typed outputs, routed owner graph, Doctrine `grounding`, and
    Doctrine `review_family` so Critic reviews after every specialist turn and
    is the only finisher
  - keep any `route_only` use narrow and Critic-owned: only use it for a real
    control-only hold or repair state with no artifact to judge
  - finish `skills/demo-git` with the real bundled script and reference files
    the flow will use beside `repo-search`, `pytest-local`, and `rally-kernel`
  - add the flow emit target, compile the flow, and emit the Doctrine skill
    package readback
* Verification (required proof):
  - rebuild `software_engineering_demo` with Doctrine and inspect
    `flows/software_engineering_demo/build/**`
  - emit `demo-git` and inspect `skills/demo-git/build/**`
  - run the prompt-input reducer once in a prepared home and inspect the JSON
    fact payload it emits
* Docs/comments (propagation; only if needed):
  - add only high-leverage comments at the runtime or setup boundary when the
    rule would otherwise be easy to misread later
* Exit criteria:
  - source and generated readback match
  - role grounding is visible in source and generated readback
  - the authored flow has no unresolved routing, skill, or ownership choices
* Rollback:
  - keep the new flow present but not advertised until compile and readback are
    clean

## Phase 4 — End-to-end proof and truth sync

* Goal:
  Prove the showcase on real first and second issues and leave live docs aligned
  with shipped truth.
* Work:
  - run `uv run pytest tests/unit -q`
  - run one live issue from blank demo repo state
  - run one later issue from the last accepted demo tip and inspect branch plus
    commit history for stacked work and per-turn commits
  - record any remaining Rally or Doctrine gaps surfaced by the live run in
    this plan doc
  - sync `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` to the final shipped behavior
* Verification (required proof):
  - `uv run pytest tests/unit -q`
  - flow compile output
  - skill compile output
  - live Rally proof runs
  - git log and branch inspection in `home/repos/demo_repo`
* Docs/comments (propagation; only if needed):
  - remove stale claims about markdown-only skill handling or the old
    capability-refresh blocker
* Exit criteria:
  - the showcase works end to end, proof is written down, and remaining gaps
    are named plainly
* Rollback:
  - keep `software_engineering_demo` present but not advertised as the showcase
    until the proof is honest
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Build and compile proof

- rebuild the new flow with Doctrine and inspect generated readback
- inspect generated readback for role grounding and any narrow Critic
  `route_only` branch
- emit the Doctrine skill package and inspect generated readback

## 8.2 Runtime proof

- run `uv run pytest tests/unit -q`
- add or update only the tests needed for build, skill copy, prompt-input
  facts, setup, and git guard behavior

## 8.3 Live demo proof

- run the flow once with no prior demo repo
- run it again with a new issue and confirm a new branch was created on the
  last accepted tip
- inspect git log to confirm one commit after each code-changing owner turn
- inspect one live prompt-input payload or log trace to confirm grounding got
  the branch, git, carry-forward, and latest-review facts it expects

## 8.4 Proof we should not add

- no grep-only doc gates
- no fake tests that only check for string presence in prompts
- no second demo control plane just to simplify proof

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- ship the new flow as an optional demo flow
- keep `poem_loop` and current runtime paths working while the new flow lands

## 9.2 Ops truth

- log bootstrap source, branch name, and git guard failures through normal
  Rally logging paths
- keep carry-forward repo history easy to find in the run files and the demo
  repo itself

## 9.3 Telemetry stance

- no product telemetry work is needed
- file-first Rally logs are enough for this demo

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter and `planning_passes`
  - `# TL;DR`
  - `# 0)` through `# 10)`
  - helper-block drift
  - agreement between architecture, call-site audit, phase plan, verification,
    rollout, and approved exceptions
- Findings summary:
  - after the mixed-skill truth update, one real drift remained: target
    architecture still named the demo Doctrine skill as `skills/demo-git/SKILL.prompt`
    even though Rally's shipped pattern is `skills/<skill>/prompts/SKILL.prompt`
  - the approved first-pass exception for per-flow union runtime skill exposure
    remains visible, but it is an accepted limitation rather than an open
    blocker
- Integrated repairs:
  - normalized the Doctrine skill path across current architecture, target
    architecture, and runtime boundary rules to use `prompts/SKILL.prompt`
  - kept the accepted per-agent skill-isolation exception explicit across the
    artifact instead of treating it as a hidden open question
  - kept the shipped mixed-skill `rally-kernel` path, Doctrine `grounding`,
    prompt-input facts, and narrow Critic `route_only` use aligned across the
    main sections and decision log
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

- 2026-04-13: This showcase stays on `home/issue.md` only. There is no second
  handoff artifact.
- 2026-04-13: Critic runs after every owner turn and is the only owner that can
  finish the flow with `done`.
- 2026-04-13: The first demo must use one Doctrine-authored skill package and
  must keep existing markdown skills working in the same run.
- 2026-04-13: New issues must stack on the last accepted demo branch tip
  instead of restarting from a blank repo each time.
- 2026-04-13: If planning finds a real Rally or Doctrine gap, that gap must be
  discussed before the plan moves on.
- 2026-04-13: The first demo may keep per-flow union runtime skill exposure
  even though authored per-agent skill boundaries already exist. This is an
  accepted Rally limitation for the first pass, not solved behavior.
- 2026-04-13: Deep-dive pass 2 found a second Rally runtime gap: run homes
  refresh compiled agents on start or resume, but not skills, MCPs, or
  `config.toml` after first materialization. Planning stops here until the
  showcase policy for capability refresh is chosen.
- 2026-04-13: Verified current Rally runtime now refreshes skills, MCPs, and
  `config.toml` on `run` and `resume`, while setup still stays one-time behind
  the home-ready marker. The pass 2 blocker is closed.
- 2026-04-13: The authoritative execution frontier starts with mixed-skill
  runtime support, then repo bootstrap and git guards, then authored Doctrine
  flow surfaces, then live proof plus doc truth sync. The earlier docs-only
  contract-lock phase is planning work, not implementation work.
- 2026-04-13: External research was intentionally skipped for this doc because
  repo-grounded planning was sufficient. The consistency pass repaired
  `planning_passes` to match the chosen path and cleared the artifact for
  implementation.
- 2026-04-13: Doctrine `grounding` is part of the showcase plan. Rally's
  existing `runtime.prompt_input_command` will feed branch, git,
  carry-forward, and latest-review facts into that grounding instead of adding
  a second control plane.
- 2026-04-13: `route_only` stays a narrow Critic-only tool for control states
  that truly have no artifact to review. The main loop remains
  artifact-and-review first.
- 2026-04-13: Rally already ships Doctrine-native skill support. The plan now
  treats `skills/rally-kernel/prompts/SKILL.prompt` plus the current
  `emit_skill` and mixed-skill runtime path as existing truth, and only plans
  the extra `demo-git` skill plus any narrow follow-up that the showcase still
  exposes.
