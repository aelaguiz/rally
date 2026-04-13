---
title: "Rally - External Project Integration Model - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
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

## Plan

1. Add one workspace manifest, one workspace resolver, and one fail-loud
   built-in asset boundary.
2. Move CLI, build, load, run, issue-ledger, home setup, and adapter envs onto
   that shared workspace contract.
3. Update shared prompts, generated readback, and live docs so they all teach
   the same root model.
4. Prove the contract in both this Rally repo and one external repo, starting
   with `../paperclip_agents` after a Rally-native flow port lands there.

## Non-negotiables

- No command may depend on the Rally source checkout being the workspace.
- No hidden machine-global Rally state.
- `runs/` stays in the workspace repo, not in the Rally install tree.
- `paperclip_agents` is a proof target, not a framework primitive.
- There must be one front-door workspace-root rule, not one rule per command.
- If Doctrine cannot consume Rally's built-in shared assets cleanly through the
  chosen boundary, we stop and name that Doctrine gap instead of patching
  around it in Rally.

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

Rally can treat a non-Rally repo as the workspace root and still compile,
load, run, materialize, and archive flows with the same CLI and runtime model
it uses for its own dogfood repo.

This claim is true only if all of this is true:

- a user can run Rally against `../paperclip_agents` after a Rally-native flow
  is ported there
- the ported repo owns its own `flows/`, `skills/`, `mcps/`, and `runs/`
- Rally no longer derives the active workspace from `src/rally/cli.py` or any
  similar package-relative path
- the current Rally repo still works as a normal workspace under the same
  rules
- shared Rally-owned built-ins cross the boundary through one explicit Rally
  mechanism, not through accidental relative-path reach-back into the source
  checkout

## 0.2 In scope

- Define the Rally workspace root as a first-class runtime concept, separate
  from the Rally framework install root.
- Decide which assets belong to the workspace repo and which assets belong to
  Rally itself.
- Update CLI root resolution so `rally` acts on a chosen workspace, not on the
  package location.
- Update build, load, run-store, home-materialization, and adapter-launch code
  to follow that workspace root.
- Decide the clean path for Rally-owned shared assets such as `stdlib/rally/`
  schemas, examples, and prompt imports when the workspace is not the Rally
  source repo.
- Keep the current Rally repo working as one valid workspace.
- Add proof that one external repo can host Rally-native flows after porting,
  starting with `../paperclip_agents`.
- Update the Rally design docs that currently teach "repo root is Rally home."

Allowed architectural convergence scope:

- add one explicit workspace discovery rule backed by the root
  `pyproject.toml` workspace manifest
- add one Rally-owned built-in sync or validation boundary for
  `stdlib/rally/**` and `skills/rally-kernel/**` so host repos do not need the
  Rally source tree vendored into them
- rename or tighten env meanings so the runtime uses `RALLY_WORKSPACE_DIR` and
  `RALLY_CLI_BIN`
- reshape tests and fixtures so they prove both dogfood and external-workspace
  use

## 0.3 Out of scope

- A GUI, dashboard, or hosted control plane.
- A plugin marketplace or remote workspace registry.
- Making `paperclip_agents` names or domain concepts into Rally primitives.
- Supporting many scattered asset roots for one run with no single workspace
  owner.
- A hidden fallback that quietly snaps back to the Rally source repo when
  workspace detection fails.
- Requiring a proprietary host repo to vendor the whole Rally runtime source
  tree just to use Rally.

## 0.4 Definition of done (acceptance evidence)

The work is done only when all of this is true:

- Rally has one clear workspace-root contract that applies to CLI, build,
  load, run storage, home setup, and adapter launch.
- No supported command still derives workspace truth from the Rally package
  file location.
- No supported command still depends on a sibling `../doctrine` checkout.
- The current Rally repo can still compile and run its own flows as one
  workspace.
- A second repo can host Rally-native flows and `runs/` inside its own tree.
- One real external proof exists for `../paperclip_agents`, or the exact
  remaining blocker for that proof is named plainly in this doc.
- Rally-owned shared assets use one clean cross-boundary path.
- The issue-ledger model still starts from `home/issue.md`.
- Rally unit tests cover the new root rules and keep current behavior safe.

Behavior-preservation evidence:

- current flow build still works for Rally's own workspace
- current run layout still lands under workspace-local `runs/`
- current `home/issue.md`, note, and final-JSON rules still hold

## 0.5 Key invariants (fix immediately if violated)

- One run always has one workspace root.
- The workspace repo owns authored flow assets and `runs/`.
- Rally-owned built-ins cross the boundary through one explicit rule.
- Framework-owned built-in paths are reserved and fail loud on host drift.
- No hidden `~/.rally`, `~/.config`, or similar Rally control plane appears.
- No special case says "if this is the Rally repo, do something different."
- No silent fallback to the Rally source tree after workspace lookup fails.
- No dual source of truth between workspace assets and Rally-owned built-ins.
- `paperclip_agents` stays a pressure test, not framework law.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Make an external repo feel like a first-class Rally workspace.
2. Keep one mental model for this repo and outside repos.
3. Keep Rally filesystem-first and CLI-first.
4. Keep host-repo setup small and explicit.
5. Preserve current Rally behavior while the root model changes.

## 1.2 Constraints

- `src/rally/cli.py` currently derives repo root from the package file path.
- `src/rally/services/flow_loader.py` loads `flows/<flow>/...` from one
  `repo_root`.
- `src/rally/services/run_store.py` writes `runs/` under that same root.
- `src/rally/services/home_materializer.py` copies skills and MCPs from
  repo-root `skills/` and `mcps/`.
- `src/rally/services/flow_build.py` rebuilds from the workspace
  `pyproject.toml`, but today that workspace is assumed to be the Rally repo.
- `tests/unit/test_flow_loader.py` explicitly rejects support files that escape
  the current repo root.
- `docs/RALLY_MASTER_DESIGN_2026-04-12.md` still teaches "Repo root is Rally
  home."
- `../paperclip_agents` has no root `pyproject.toml` today; it only has
  `doctrine/pyproject.toml`, so the proof target will need a real
  workspace-root manifest.

## 1.3 Architectural principles (rules we will enforce)

- Separate framework-install paths from workspace-owned paths.
- Give each asset class one clear owner.
- Resolve workspace root the same way across CLI, build, load, and run code.
- Keep one workspace-local `runs/` story.
- Keep the current Rally repo as a normal workspace, not as a privileged mode.
- Fail loud when the workspace contract is missing or ambiguous.

## 1.4 Known tradeoffs (explicit)

- Keeping fixed top-level workspace folders is simple, but it asks each host
  repo to accept Rally's on-disk shape.
- Direct package-owned support files would be cleaner, but current Doctrine
  emitted-contract rules reject support files outside the host project root.
  The clean first pass is framework-owned built-ins that sync into workspace
  paths before build and run.
- An explicit workspace manifest rule is less magical than pure cwd guessing,
  but it adds one setup step for host repos.
- Using root `pyproject.toml` as the one workspace manifest is clean, but the
  first external proof must add that file to `../paperclip_agents` because it
  does not exist there today.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally's master design says the repo root is Rally home.
- The CLI gets its root from `Path(__file__).resolve().parents[2]`.
- Flow loading assumes `flows/` lives under one repo root.
- Run storage assumes `runs/` lives under that same root.
- Home materialization assumes repo-root `skills/` and `mcps/`.
- Flow build assumes the active workspace `pyproject.toml` is the Rally repo's
  `pyproject.toml`.
- The port-gap read already shows that much of a Rally-native port can live in
  flow prompts and setup code, but root ownership is still a real runtime
  boundary.

## 2.2 What’s broken / missing (concrete)

- Rally cannot honestly treat `../paperclip_agents` as the repo that owns the
  authored flow and run state.
- A proprietary host repo would need awkward vendoring, symlinks, or command
  tricks to act like a Rally workspace.
- Built-in Rally assets and workspace assets are not cleanly separated.
- The docs teach a dogfood-only story instead of a framework adoption story.

## 2.3 Constraints implied by the problem

- The fix must stay filesystem-first and easy to inspect in git.
- The host repo must own its own `runs/` and authored flow assets.
- Rally still needs a clean built-in asset story for shared prompt and schema
  surfaces.
- If the clean built-in asset story needs generic compiler help, that is a
  Doctrine-first blocker.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/EMIT_GUIDE.md` — adopt host-repo `pyproject.toml` emit
  targets and `[tool.doctrine.compile].additional_prompt_roots`; reject any
  Rally design that still needs the Rally source checkout as the compile root.
  Doctrine already supports compile config rooted in the host repo.
- `../doctrine/doctrine/project_config.py` and
  `../doctrine/tests/test_project_config.py` — adopt compile config resolved
  relative to the host repo `pyproject.toml`, including a real `prompts/` dir
  outside the host project root; this makes Rally-owned prompt imports
  feasible across the workspace boundary.
- `../doctrine/doctrine/emit_contract.py` and
  `../doctrine/tests/test_project_config.py` — reject a design that leaves
  emitted `schema_file` and `example_file` outside the host project root under
  the current contract model; Doctrine fails loud on support files that
  serialize outside the target project root.
- `../paperclip_agents/README.md` and `../paperclip_agents/PRINCIPLES.md` —
  adopt the pressure-test idea that a host repo should own its own doctrine
  and repo-local skills; reject making `paperclip_agents` layout itself into
  Rally framework law.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/cli.py` — current command entrypoint; it hard-derives
    `repo_root` from the installed package path, so workspace discovery is not
    a first-class contract yet.
  - `src/rally/services/flow_build.py` — current compile owner; it reads
    `repo_root/pyproject.toml` but also hardcodes a sibling `../doctrine`
    checkout, so external installed use is not clean yet.
  - `src/rally/services/flow_loader.py` — current flow load contract; it
    resolves `flows/`, prompt entrypoints, build readback, `setup_home_script`,
    and final-output support files relative to one `repo_root`, and rejects
    files that escape that root.
  - `src/rally/services/run_store.py` — current run identity and archive
    owner; it writes `runs/active`, `runs/archive`, and `runs/locks` under the
    same `repo_root`.
  - `src/rally/services/home_materializer.py` — current run-home materializer;
    it copies `skills/` and `mcps/` from `repo_root`, writes `config.toml`
    from repo-local MCP definitions, and seeds the run home under
    workspace-local `runs/`.
  - `src/rally/adapters/codex/launcher.py` — current adapter env surface; it
    exports `RALLY_BASE_DIR` from `repo_root`, so any workspace split must keep
    this env contract honest.
  - `stdlib/rally/prompts/rally/base_agent.prompt` — current shared prompt
    contract; it explicitly tells agents that `RALLY_BASE_DIR` is the Rally
    repo root, so the prompt layer also carries the old root model.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` and
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` — current durable docs still
    teach repo-root-is-home and workspace-local `runs/`.
- Canonical path / owner to reuse:
  - `src/rally/cli.py` — natural front-door owner for workspace discovery
    because all user-visible commands already start here.
  - `src/rally/services/flow_build.py`,
    `src/rally/services/flow_loader.py`,
    `src/rally/services/run_store.py`,
    `src/rally/services/home_materializer.py`, and
    `src/rally/adapters/codex/launcher.py` — should consume one resolved
    workspace root, not each invent their own root logic.
  - workspace `pyproject.toml` — should own Doctrine compile and emit config
    for host-repo flows.
  - Rally-owned built-in asset boundary — still needs one explicit owner
    instead of ad hoc relative paths.
- Existing patterns to reuse:
  - `tests/unit/test_flow_build.py` — temp workspace plus paired Doctrine
    compile proof.
  - `tests/unit/test_flow_loader.py` — path-resolution and escape-boundary
    proof for compiled contracts.
  - `tests/unit/test_run_store.py` — workspace-local `runs/active` and
    `runs/archive` truth.
  - `tests/unit/test_launcher.py` — adapter env contract proof.
  - `docs/LESSONS_RALLY_PORT_GAP_READ_2026-04-13.md` — already narrows the
    external port story to a few real runtime gaps instead of a fake
    control-plane rewrite.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — shared run identity and
    note/final-JSON contract; it must change with the new workspace meaning.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — shared final-output
    rule remains Rally-owned and should stay reusable across workspaces.
- Native model or agent capabilities to lean on:
  - Codex runtime plus Rally launch env — agents already get `cwd`,
    `CODEX_HOME`, `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`; no
    new deterministic wrapper is needed to explain workspace identity once the
    env contract is fixed.
- Existing grounding / tool / file exposure:
  - `home/issue.md` and the run home — current shared input/output surface
    already fits a workspace-root model.
  - `rally issue note` through `rally-kernel` — the front-door note path is
    already workspace-local.
  - workspace `pyproject.toml` plus Doctrine compile config — current way to
    add cross-root prompt imports without inventing a new prompt registry.
- Duplicate or drifting paths relevant to this change:
  - `src/rally/cli.py`,
    `src/rally/services/flow_build.py`,
    `src/rally/services/flow_loader.py`,
    `src/rally/services/run_store.py`,
    `src/rally/services/home_materializer.py`,
    `src/rally/adapters/codex/launcher.py`,
    `stdlib/rally/prompts/rally/base_agent.prompt`, and
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md` all carry their own version of
    root ownership today.
  - `tests/unit/test_flow_loader.py` and Doctrine emit-contract rules both
    enforce in-root support files, but at different layers; those boundaries
    must converge.
- Capability-first opportunities before new tooling:
  - workspace `pyproject.toml` plus Doctrine
    `additional_prompt_roots` — may solve prompt import sharing without a new
    Rally prompt registry.
  - workspace-local `runs/` plus the current run-store model — already gives
    the right ownership shape for external repos once workspace discovery is
    fixed.
  - current Codex env surface — may only need one renamed or redefined
    workspace env, not a new runtime sidecar.
- Behavior-preservation signals already available:
  - `tests/unit/test_flow_build.py` — build orchestration
  - `tests/unit/test_flow_loader.py` — load contract and support-file
    boundaries
  - `tests/unit/test_run_store.py` — run id, archive, and run-path behavior
  - `tests/unit/test_launcher.py` — adapter env truth

## 3.3 Decision gaps that must be resolved before implementation

- Resolved in deep-dive pass 1: Rally-owned built-in prompts, schemas,
  examples, and mandatory skills stay framework-owned, but Rally syncs them
  into fixed workspace paths before build and run so compiled contracts stay
  project-root-relative.
- Resolved in deep-dive pass 1: external-workspace builds should use the host
  workspace `pyproject.toml` and environment, not a sibling `../doctrine`
  checkout lookup.
- Resolved in deep-dive pass 1: the agent-facing env contract should replace
  `RALLY_BASE_DIR` with explicit workspace and CLI env vars.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- This repo is both the Rally framework source tree and the only workspace the
  runtime knows how to use today.
- `pyproject.toml` at the repo root owns Doctrine emit targets for flows in
  this same repo.
- Authored flows live under repo-root `flows/`.
- Built-in shared prompts, schemas, and examples live under repo-root
  `stdlib/rally/`.
- The mandatory built-in skill lives under repo-root `skills/rally-kernel/`.
- Run state lives under repo-root `runs/`.
- There is no workspace marker or workspace object separate from the package
  checkout itself.
- `../paperclip_agents` already has repo `skills/` and authored doctrine under
  `doctrine/prompts/`, but it does not yet match the Rally workspace layout
  this runtime expects.
- `../paperclip_agents` has `doctrine/pyproject.toml` for its current
  Paperclip-managed Doctrine emit flow, but it does not have a root
  `pyproject.toml` that could act as a Rally workspace manifest.

## 4.2 Control paths (runtime)

- `src/rally/cli.py` starts every command by calling `_repo_root()`, which
  returns the package checkout path from `Path(__file__).resolve().parents[2]`.
- `src/rally/services/runner.py` passes that same root into build, load, run
  storage, archive, issue-ledger, and home-materialization paths.
- `src/rally/services/flow_build.py` reads `<repo_root>/pyproject.toml` but
  also hardcodes a sibling `../doctrine` checkout for the compiler process.
- `src/rally/services/flow_loader.py` resolves `flows/<flow>/...`, compiled
  readback, prompt entrypoints, and final-output support files from the same
  root and rejects paths that escape it.
- `src/rally/services/home_materializer.py` copies allowed skills and MCPs
  from repo-root `skills/` and `mcps/`, and it treats repo-root
  `skills/rally-kernel/` as mandatory.
- `src/rally/adapters/codex/launcher.py` exports that same root as
  `RALLY_BASE_DIR`.
- `stdlib/rally/prompts/rally/notes.prompt` tells agents to append notes
  through `"$RALLY_BASE_DIR/rally" issue note ...`, which assumes the root
  itself contains the runnable Rally CLI path.

## 4.3 Object model + key abstractions

- `repo_root` is overloaded. It means framework checkout, workspace root,
  built-in asset root, and run-state root all at once.
- There is no `WorkspaceContext`, workspace manifest, or built-in asset owner
  separate from that overloaded root.
- `FlowDefinition` and `RunRecord` already model workspace-like paths such as
  `flows/...` and `runs/...`, but they are created from the overloaded root.
- `CompiledAgentContract` stores project-relative `schema_file` and
  `example_file` paths, and `flow_loader` enforces that those paths stay under
  the same root.

## 4.4 Observability + failure behavior today

- Rally fails loud on missing flow files, missing compiled readback, missing
  skills or MCPs, missing sibling Doctrine checkout, and support files that
  escape the current root.
- Launch records and tests treat `RALLY_BASE_DIR` as the one root truth.
- Build succeeds only when the current root also has a sibling Doctrine repo,
  which is an accidental local-dev assumption rather than a real workspace
  contract.
- User-facing wording still says "Rally repo root," which will be wrong once a
  non-Rally host repo is a first-class workspace.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- One host repo is one Rally workspace.
- The workspace root is the nearest `pyproject.toml` that contains a
  `[tool.rally.workspace]` table. That same file also owns
  `[tool.doctrine.compile]` and `[tool.doctrine.emit]` for Rally-native flows.
  This keeps one clear front door without adding a second config file.
- Fixed top-level workspace folders stay:
  - `flows/`
  - `skills/`
  - `mcps/`
  - `stdlib/`
  - `runs/`
- Workspace-owned authored truth stays in:
  - `flows/**`
  - `skills/**` for host-repo skills
  - `mcps/**`
  - `runs/**`
- Rally framework-owned built-ins stay canonical in the installed Rally
  package, but Rally syncs them into fixed workspace paths before build and
  run:
  - `stdlib/rally/**`
  - `skills/rally-kernel/**`
- The sync rule is byte-checked and fail-loud:
  - missing framework-owned files are materialized into the workspace
  - matching files are left alone
  - conflicting files block the command with a clear error
- In this Rally repo, the framework source tree and the workspace still happen
  to be the same tree, so the sync step becomes validation or a no-op. In an
  external repo such as `../paperclip_agents`, the same paths are materialized
  into that repo.
- In `../paperclip_agents`, the first proof pass adds a root `pyproject.toml`
  and `flows/**` tree for Rally-native work. The existing
  `doctrine/pyproject.toml` stays legacy until the port fully retires the old
  Paperclip-managed path.

## 5.2 Control paths (future)

- `rally` resolves the workspace once at CLI entry and passes a shared
  `WorkspaceContext` through the runtime.
- A front-door built-in sync or validation step runs before build and run
  paths. If materialized built-ins are missing, stale, or locally edited,
  Rally fails loud instead of silently guessing.
- Flow build runs Doctrine from Rally's installed Python environment with an
  explicit workspace manifest, e.g. `python -m doctrine.emit_docs --pyproject
  <workspace-pyproject> --target <flow>`. Rally stops looking for a sibling
  `../doctrine` checkout.
- Flow load, run storage, issue ledger, home materialization, and adapter
  launch read workspace-root or run-home paths only.
- Compiled agent contracts keep workspace-relative `schema_file` and
  `example_file` paths, so the current loader safety checks still make sense.
- The shared note path stops shelling through `"$RALLY_BASE_DIR/rally"` and
  instead uses an explicit CLI env var such as `RALLY_CLI_BIN`.

## 5.3 Object model + abstractions (future)

- Add a small `WorkspaceContext` owner, likely under
  `src/rally/services/workspace.py`, that holds:
  - `workspace_root`
  - `pyproject_path`
  - fixed layout paths for `flows`, `skills`, `mcps`, `stdlib`, and `runs`
  - the resolved Rally CLI executable path
- Add one built-in asset owner, likely under
  `src/rally/services/framework_assets.py`, that materializes framework-owned
  built-ins into the workspace and validates drift.
- Rename service parameters and helpers from `repo_root` to `workspace_root`
  or `WorkspaceContext` so the code matches the real contract.
- Keep `FlowDefinition`, `RunRecord`, and compiled contract shapes mostly the
  same. They already fit a workspace-root model once the root is honest.

## 5.4 Invariants and boundaries

- One command and one run always use exactly one workspace root.
- No command may discover flows, skills, MCPs, or runs from the Rally package
  checkout path.
- No command may depend on a sibling `../doctrine` checkout.
- Built-in synced files are generated inputs, not host-authored truth. Local
  edits to them fail loud.
- `stdlib/rally/**` and `skills/rally-kernel/**` are reserved framework-owned
  names. Host workspaces may not override them.
- The agent-facing env contract becomes explicit:
  - `RALLY_WORKSPACE_DIR` points at the workspace root
  - `RALLY_CLI_BIN` points at the Rally CLI executable path
  - `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, `RALLY_AGENT_SLUG`, and
    `RALLY_TURN_NUMBER` stay
- `RALLY_BASE_DIR` is removed so the runtime stops overloading one vague name.
- `home/issue.md` stays the one shared ledger.
- There is no silent fallback to the Rally source repo when workspace
  resolution fails.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| CLI root discovery | `src/rally/cli.py` | `_repo_root`, `_run_command`, `_resume_command`, `_issue_note_command` | CLI derives root from package path | Resolve the nearest workspace from `pyproject.toml` and pass one `WorkspaceContext` | External repos must be first-class workspaces | `[tool.rally.workspace]` plus `resolve_workspace(...)` | `tests/unit/test_cli.py` plus new workspace-resolution tests |
| Workspace owner | `src/rally/services/workspace.py` | new module | missing | add one owner for workspace discovery, layout paths, and manifest validation | every root-heavy service needs one shared truth | `WorkspaceContext` | new workspace-resolution tests plus touched service tests |
| Framework built-ins | `src/rally/services/framework_assets.py` | new module | missing | add byte-checked sync and drift validation for `stdlib/rally/**` and `skills/rally-kernel/**` | external workspaces need built-ins without source-tree reach-back or silent overwrite | reserved built-in path contract | new framework-asset tests plus `tests/unit/test_runner.py` |
| Build orchestration | `src/rally/services/flow_build.py` | `ensure_flow_agents_built` | Uses workspace `pyproject.toml` but also hardcodes sibling `../doctrine` | Run Doctrine from Rally's installed Python environment, validate workspace manifest, and sync built-ins before emit | External workspaces will not have a sibling Doctrine repo | `python -m doctrine.emit_docs --pyproject <workspace-pyproject> --target <flow>` | `tests/unit/test_flow_build.py` |
| Flow loading | `src/rally/services/flow_loader.py` | `_load_flow_payload`, `_resolve_repo_relative_file`, compiled support-file load | Resolves everything from `repo_root` and says "Rally repo root" in errors | Resolve from workspace root, keep support files in workspace, and update wording | The root is a workspace, not the Rally package tree | workspace-relative flow and support-file contract | `tests/unit/test_flow_loader.py` |
| Run storage | `src/rally/services/run_store.py` | `active_runs_dir`, `archive_runs_dir`, `flow_lock`, `find_run_dir` | Stores runs under `repo_root/runs/**` | Keep the same on-disk layout but rename the owner and callers to workspace root | The storage layout is right; the owner concept is wrong | workspace-local `runs/**` contract | `tests/unit/test_run_store.py` |
| Issue ledger | `src/rally/services/issue_ledger.py` | `append_issue_note`, `append_issue_event`, `_resolve_issue_file` | Resolves runs and issue files from `repo_root` | Move callers and wording onto workspace root | `rally issue note` must work from any workspace | workspace-root note path contract | `tests/unit/test_issue_ledger.py` |
| Home materialization | `src/rally/services/home_materializer.py` | `_copy_allowed_skills_and_mcps`, `_write_codex_config`, `_run_setup_script` | Copies local skills and MCPs from repo root and requires repo-root `skills/rally-kernel` | Sync framework-owned built-ins into workspace, then materialize from workspace paths | Runtime must not depend on the Rally source tree | built-in sync plus workspace-owned materialization | `tests/unit/test_runner.py` |
| Adapter env | `src/rally/adapters/codex/launcher.py` | `build_codex_launch_env`, `write_codex_launch_record` | Exports `RALLY_BASE_DIR` as the root truth | Export explicit workspace and CLI env vars; drop `RALLY_BASE_DIR` | Agents need honest workspace and CLI paths | `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN` | `tests/unit/test_launcher.py`, `tests/unit/test_runner.py` |
| Shared prompt contract | `stdlib/rally/prompts/rally/base_agent.prompt`, `stdlib/rally/prompts/rally/notes.prompt` | `RallyBaseDir`, note `append_with` path | Teaches "Rally repo root" and shells to `"$RALLY_BASE_DIR/rally"` | Teach workspace-root meaning and use explicit CLI env | Packaged Rally cannot rely on a root-local binary path | workspace env contract in stdlib prompts | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Workspace manifest | `pyproject.toml` | workspace-level config | Today it only carries Doctrine compile and emit config for this repo | Add the Rally workspace table and keep Rally-native Doctrine compile and emit config in the same root file | One front-door root rule beats ad hoc cwd logic | `[tool.rally.workspace]`, `[tool.doctrine.compile]`, `[tool.doctrine.emit]` | build and workspace-resolution tests |
| External proof target | `../paperclip_agents/pyproject.toml`, `../paperclip_agents/flows/**`, `../paperclip_agents/runs/**` | new workspace files | target repo has no root manifest and no Rally-native flow tree yet | add the workspace-root manifest and one Rally-native flow there for proof | the proof target must satisfy the same contract as every other workspace | first real external workspace | external proof plus local inspection |
| Live docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`, `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md` | root-model and note-path prose | Still says repo root is Rally home and shows the old note command path | Rewrite docs to teach the workspace contract and explicit CLI env | Leaving the old wording would preserve a dead design | workspace-root docs truth | docs inspection |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - `src/rally/services/workspace.py` should become the one root-resolution
    owner.
  - `src/rally/services/framework_assets.py` should become the one built-in
    sync owner.
  - CLI should resolve the workspace once and pass that result into build,
    load, run-store, issue-ledger, home-materialization, and adapter launch.
  - workspace-root `pyproject.toml` should become the one manifest for Rally
    workspace identity and Rally-native Doctrine compile/emit config.
- Deprecated APIs (if any):
  - `src/rally/cli.py::_repo_root`
  - sibling `../doctrine` discovery in `src/rally/services/flow_build.py`
  - `RALLY_BASE_DIR`
  - using `../paperclip_agents/doctrine/pyproject.toml` as the future
    Rally-native workspace manifest
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - package-relative workspace discovery
  - note path `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`
  - wording that says the active root is the Rally repo root
  - sibling `../doctrine` runtime lookup
- Capability-replacing harnesses to delete or justify:
  - none; this change is root ownership and asset materialization, not a new
    harness
- Live docs/comments/instructions to update or delete:
  - `stdlib/rally/prompts/rally/base_agent.prompt`
  - `stdlib/rally/prompts/rally/notes.prompt`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`
  - `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md`
- Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_build.py`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_run_store.py`
  - `tests/unit/test_issue_ledger.py`
  - `tests/unit/test_launcher.py`
  - `tests/unit/test_runner.py`
  - one real external proof against `../paperclip_agents` after a Rally-native
    flow lands there

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Runtime services | `src/rally/services/**` and `src/rally/adapters/codex/launcher.py` `repo_root` parameters | use one `WorkspaceContext` owner | stops each service from inventing its own root story | include |
| Built-in assets | `stdlib/rally/**`, `skills/rally-kernel/**`, `src/rally/services/home_materializer.py`, `tests/unit/test_runner.py` fixture copy helpers | sync framework-owned built-ins into fixed workspace paths | keeps external workspaces honest without package-path reach-back | include |
| Shared prompts and notes | `stdlib/rally/prompts/rally/base_agent.prompt`, `stdlib/rally/prompts/rally/notes.prompt`, compiled readback checks | explicit workspace and CLI env vars | prevents dead repo-root assumptions from living inside agent doctrine | include |
| Workspace proof target | `../paperclip_agents/doctrine/pyproject.toml` and new `../paperclip_agents/pyproject.toml` | promote root manifest ownership for Rally-native flows | keeps external proof under the same root rule instead of a nested special case | include |
| Live docs | root-model and note-path docs listed above | teach workspace root instead of repo root | prevents design drift between code and docs | include |
| External proof target | `../paperclip_agents/paperclip_home/**` and old Paperclip control-plane surfaces | do not pull Paperclip runtime layout into Rally core | keeps the proof target from defining framework law | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria +
> explicit verification plan (tests optional). Refactors, consolidations, and
> shared-path extractions must preserve existing behavior with credible
> evidence proportional to the risk. For agent-backed systems, prefer prompt,
> grounding, and native-capability changes before new harnesses or scripts. No
> fallbacks/runtime shims - the system must work correctly or fail loudly
> (delete superseded paths). The authoritative checklist must name the actual
> chosen work, not unresolved branches or "if needed" placeholders. Prefer
> programmatic checks per phase; defer manual/UI verification to finalization.
> Avoid negative-value tests and heuristic gates (deletion checks, visual
> constants, doc-driven gates, keyword or absence gates, repo-shape policing).
> Also: document new patterns/gotchas in code comments at the canonical
> boundary (high leverage, not comment spam).

## Phase 1 - Lock workspace discovery and built-in asset boundaries

* Goal: Make workspace identity explicit and give Rally one honest owner for
  built-in assets before the wider runtime changes.
* Work:
  - add `[tool.rally.workspace]` to this repo root `pyproject.toml`
  - add `src/rally/services/workspace.py` with `WorkspaceContext`, nearest-root
    discovery from the root `pyproject.toml`, fixed layout paths, and fail-loud
    manifest validation
  - add `src/rally/services/framework_assets.py` with reserved-path sync and
    drift checks for `stdlib/rally/**` and `skills/rally-kernel/**`
  - update CLI entrypoints so workspace discovery happens once and downstream
    callers stop inventing their own root
* Verification (required proof):
  - add targeted unit coverage for missing-manifest, ambiguous-root, and
    reserved-path drift cases
  - run the smallest affected proof set for the new boundary, including
    `tests/unit/test_cli.py` and the new workspace or framework-asset tests
* Docs/comments (propagation; only if needed):
  - add one short comment in `workspace.py` on why workspace root and framework
    root are different things
  - add one short comment in `framework_assets.py` on why reserved built-ins
    fail loud on local edits
* Exit criteria:
  - CLI can resolve one `WorkspaceContext` from the workspace manifest
  - built-in sync or validation works in this repo without a source-tree
    special case
  - new root discovery does not still start from the package checkout path
* Rollback:
  - revert the new workspace and framework-asset modules together and restore
    the old CLI root path if this phase fails before downstream services depend
    on the new contract

## Phase 2 - Cut the runtime over to `WorkspaceContext`

* Goal: Move build, load, run storage, issue-ledger, home setup, and adapter
  envs onto one workspace contract with no sibling `../doctrine` dependency.
* Work:
  - thread `WorkspaceContext` or explicit workspace-root paths through
    `runner.py`, `flow_build.py`, `flow_loader.py`, `run_store.py`,
    `issue_ledger.py`, `home_materializer.py`, and
    `adapters/codex/launcher.py`
  - replace sibling `../doctrine` lookup with installed-environment build
    calls such as `python -m doctrine.emit_docs --pyproject
    <workspace-pyproject> --target <flow>`
  - keep compiled support files project-root-relative and keep `runs/**`
    inside the workspace
  - replace `RALLY_BASE_DIR` with `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN`
* Verification (required proof):
  - run the touched runtime contract tests:
    `tests/unit/test_flow_build.py`,
    `tests/unit/test_flow_loader.py`,
    `tests/unit/test_run_store.py`,
    `tests/unit/test_issue_ledger.py`,
    `tests/unit/test_launcher.py`, and
    `tests/unit/test_runner.py`
  - run `uv run pytest tests/unit -q`
  - run one dogfood Rally proof in this repo that prepares or resumes a run and
    confirms `home/issue.md`, launch envs, and `runs/**` still live under the
    workspace root
* Docs/comments (propagation; only if needed):
  - add one short comment at the adapter env boundary on why `RALLY_CLI_BIN`
    exists
* Exit criteria:
  - no runtime service still depends on package-relative root discovery
  - no runtime service still depends on a sibling `../doctrine` checkout
  - launch records and run files show workspace-local paths and the new env
    names
* Rollback:
  - revert the runtime cutover as one slice; do not leave mixed root contracts,
    mixed env names, or half-migrated build rules behind

## Phase 3 - Sync prompt, readback, and docs truth

* Goal: Make shared prompts, generated build output, and live Rally docs all
  say the same thing as the new runtime.
* Work:
  - update `stdlib/rally/prompts/rally/base_agent.prompt` and
    `stdlib/rally/prompts/rally/notes.prompt` to teach workspace-root meaning
    and use `RALLY_CLI_BIN`
  - rebuild the affected flow readback in this repo from the workspace
    manifest and inspect the generated output
  - rewrite the live docs in Section 6 so they stop saying the Rally repo root
    is the active home
* Verification (required proof):
  - rebuild the affected flows, at least `_stdlib_smoke` and `poem_loop`, with
    Doctrine from the workspace manifest and inspect `flows/*/build/**`
  - rerun the prompt-sensitive proof set, including
    `tests/unit/test_flow_loader.py` and `tests/unit/test_runner.py`
* Docs/comments (propagation; only if needed):
  - update the master design, CLI/logging, phase 3, phase 4, and memory-model
    docs in the same pass so no live doc keeps the dead root story
* Exit criteria:
  - generated readback matches the edited prompt source
  - no live prompt or Rally design doc still tells agents or operators that
    the Rally repo root is the active workspace
* Rollback:
  - revert the prompt and doc cutover together; do not keep the new runtime
    with old prompt wording or stale design docs

## Phase 4 - Prove one real external workspace in `../paperclip_agents`

* Goal: Show that a non-Rally repo can own its own Rally workspace, built
  output, and `runs/**` under the same contract as this repo.
* Work:
  - add `../paperclip_agents/pyproject.toml` with `[tool.rally.workspace]` and
    Rally-native Doctrine compile or emit config
  - add one Rally-native `flows/**` tree there as part of the agent port
  - run Rally against that repo so build, home setup, notes, and `runs/**`
    all land inside `../paperclip_agents`
  - keep `../paperclip_agents/doctrine/pyproject.toml` as legacy only during
    the port; do not let it become a second workspace rule
* Verification (required proof):
  - from `../paperclip_agents`, run the smallest real Rally build or run proof
    path for the ported flow
  - confirm compiled readback, synced built-ins, and `runs/**` all land in the
    external repo
  - if that repo gets its own root `pyproject.toml` and `uv.lock` as part of
    the port, run its root `uv run pytest` from that repo root
* Docs/comments (propagation; only if needed):
  - add only the minimum setup or port note needed in the external repo; do
    not create a second Rally control-plane story there
* Exit criteria:
  - `../paperclip_agents` works as a Rally workspace under the same root rule
    as this repo
  - if the proof stops, the remaining blocker is named plainly as a Doctrine
    gap or a port gap, not hidden behind Rally fallback logic
* Rollback:
  - revert the external proof changes in that repo and keep Rally's workspace
    contract clean; do not add host-specific branches to paper over a failed
    proof
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Keep the proof set lean. Prefer current unit tests, build checks, and one real
external-workspace proof over new ceremony.

## 8.1 Unit tests (contracts)

- cover workspace discovery from root `pyproject.toml`
- cover reserved built-in sync, validation, and conflict failures
- cover root-aware build, flow loading, run storage, issue-ledger, launcher,
  and runner behavior

## 8.2 Integration tests (flows)

- prove this Rally repo still builds and runs as a workspace under the new
  root rule
- rebuild the affected flows after stdlib prompt changes and inspect generated
  readback
- prove a temp or real external workspace can build and run through the same
  root model without a sibling `../doctrine` checkout

## 8.3 E2E / device tests (realistic)

- run one real proof against `../paperclip_agents` after a Rally-native flow is
  ready there
- confirm `home/issue.md`, synced built-ins, launch envs, and `runs/**` all
  stay inside that repo

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- land the new root model in Rally first
- keep this repo working as the dogfood workspace during the change
- then prove one external workspace without adding a second product mode

## 9.2 Telemetry changes

- no product telemetry work is required
- normal Rally logs should record the chosen workspace root and any root
  resolution failure

## 9.3 Operational runbook

- operators should be able to tell which repo is the workspace from the
  command line, run files, and launch logs

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter, `planning_passes`, `# TL;DR`, and `# 0)` through `# 10)`
  - outcome, scope, owner path, migration, verification, rollout, and helper-block agreement
- Findings summary:
  - the main artifact now says the same thing end to end about the root
    `pyproject.toml` workspace manifest, the fail-loud built-in sync boundary,
    the `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN` env contract, and the need
    for one real `../paperclip_agents` proof
  - `external_research_grounding: not started` remains a warn-only bookkeeping
    note, not a plan blocker, and the Decision Log now explains why
- Integrated repairs:
  - tightened Section 0 allowed convergence scope so it matches the chosen
    root `pyproject.toml` workspace contract and fail-loud built-in sync model
  - tightened Section 1 tradeoff wording so it no longer implies a separate
    config-file branch that the target architecture did not choose
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

- 2026-04-13: Rally must stop treating its own source checkout as the only
  valid workspace.
- 2026-04-13: External-project support must keep one workspace-root model, not
  add a separate plugin or hosted mode.
- 2026-04-13: `paperclip_agents` is a proof target only. It does not define
  framework law.
- 2026-04-13: If Rally's built-in shared asset boundary needs generic compiler
  help, we stop and name that Doctrine gap instead of baking a Rally-only
  workaround into the plan.
- 2026-04-13: Deep-dive pass 1 chose a workspace-first design where
  framework-owned built-ins sync into fixed workspace paths before build and
  run, instead of letting build or runtime reach back into the Rally source
  tree.
- 2026-04-13: Deep-dive pass 1 chose explicit env names
  `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN` and retired `RALLY_BASE_DIR`.
- 2026-04-13: Deep-dive pass 2 chose root `pyproject.toml` as the one Rally
  workspace manifest and kept Rally-native Doctrine compile/emit config in
  that same file.
- 2026-04-13: Deep-dive pass 2 chose byte-checked, fail-loud built-in sync for
  `stdlib/rally/**` and `skills/rally-kernel/**` instead of silent overwrite
  or package-path reach-back.
- 2026-04-13: Deep-dive pass 2 chose Rally's installed Doctrine dependency as
  the build owner and retired the sibling `../doctrine` runtime lookup.
- 2026-04-13: Phase planning proceeded without a separate `external-research`
  pass because the remaining design choices were already settled from Rally,
  Doctrine, and `paperclip_agents` repo evidence in Section 3. A real external
  proof is still required in implementation.
