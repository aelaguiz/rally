---
title: "Rally - Single Copy Built-in Assets - Architecture Plan"
date: 2026-04-15
status: active
fallback_policy: forbidden
owners: [rally]
reviewers: []
doc_type: phased_refactor
related:
  - pyproject.toml
  - tools/sync_bundled_assets.py
  - src/rally/services/bundled_assets.py
  - src/rally/services/workspace_sync.py
  - src/rally/services/flow_build.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_MASTER_DESIGN.md
---

# TL;DR

Outcome: Rally has one source copy for each Rally-owned built-in asset. No developer has to update `stdlib/rally` and `src/rally/_bundled/...`, or skill source and a bundled copy, to make one real change.

Problem: Rally currently has authored built-ins plus packaged mirror files. A stale mirror can ship old prompts or skills even when the source was fixed.

Approach: Replace checked-in bundled mirrors and sync-for-correctness habits with one canonical asset owner plus one read path that works for source builds, packaged installs, flow builds, and run homes. If Doctrine cannot consume that owner directly, stop and request the missing Doctrine feature instead of adding a Rally workaround.

Plan: Confirm this North Star, research current source/package/host paths, choose the single owner path, cut over Rally runtime and packaging, delete mirror paths, update docs and tests, then prove packaged and source workflows.

Non-negotiables: no dual live copies, no manual sync step required for correctness, no runtime fallback, no stale bundle mirror, and no Rally-side shim for a Doctrine gap.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: not started
recommended_flow: research -> deep dive -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

After this change, Rally-owned stdlib prompts and built-in skills are edited from one source path only, while fresh source checkouts, packaged installs, host workspaces, flow builds, and run homes still get the same built-in content. A developer must not need `tools/sync_bundled_assets.py` or paired edits under `src/rally/_bundled/...` to make a built-in change real.

If research shows that clean one-copy behavior needs Doctrine support, Rally work stops. The required output is then a focused Doctrine feature request that states what generic Doctrine ability is missing and why Rally needs it. It must not prescribe the Doctrine implementation.

## 0.2 In scope

- Rally-owned stdlib prompt source under `stdlib/rally`.
- Rally-owned built-in skills, including `rally-kernel` and any optional Rally-owned skill that the package or workspace setup exposes.
- The checked-in bundle mirror under `src/rally/_bundled`.
- The package data rules in `pyproject.toml`.
- The Rally paths that copy, resolve, build, or materialize built-ins: `bundled_assets`, `workspace_sync`, `flow_build`, `home_materializer`, `runner`, and `skill_bundles`.
- The operator path for `rally workspace sync`, `rally run`, and `rally resume`.
- Host-workspace behavior where Rally currently copies built-ins before Doctrine emit or a run.
- Tests and docs that now assert or explain bundle sync behavior.
- Generated readback policy for built-in assets, so future readers know what is source and what is output.

Allowed architectural convergence scope:

- Delete mirror assets when they stop being the source of truth.
- Replace bundle-copy logic with a single resolver or package path if that keeps one owner.
- Change `rally workspace sync` if it currently exists mainly to hide the duplicate-copy problem.
- Move a canonical owner path only if research proves that is the cleanest way to keep one source copy and still honor Rally's fixed workspace folders.
- Rebuild affected flow and skill outputs when the source path or import path changes.

## 0.3 Out of scope

- Editing `../doctrine` in this Rally thread.
- Adding a Rally workaround for a Doctrine language, compile, or emitted-output gap.
- Keeping `_bundled` as a second live copy "just in case."
- Adding a new stale-check script as the main answer to drift.
- Changing product behavior of sample flows.
- Broad docs cleanup beyond docs that would become false after the asset cutover.
- Removing normal generated readback such as flow build output solely because it repeats source text. This plan targets duplicate live truth, not every generated artifact.

## 0.4 Definition of done (acceptance evidence)

- One Rally-owned source path owns each built-in stdlib prompt and built-in skill.
- No checked-in mirror copy can drift from that source and still ship.
- Packaged install behavior still exposes the required built-ins.
- Host workspaces can build and run Rally flows without a manual bundle-sync correctness step.
- Existing behavior is preserved for built-in prompt text and required built-in skills.
- The smallest useful tests pass for the changed layer, including unit tests around built-in resolution, workspace/run setup, flow build, and packaged install.
- Affected Doctrine flow or skill outputs are rebuilt from the single source path and inspected.
- Surviving docs and CLI help no longer teach a two-copy or manual-sync model.

## 0.5 Key invariants (fix immediately if violated)

- One source owner per Rally-owned built-in.
- Generated output may exist, but it must be reproducible output, not an editable mirror.
- Package install and source checkout must read the same built-in truth.
- `rally run` and `rally resume` must fail loudly if required built-ins cannot be read.
- No fallback path may mask a missing or stale built-in.
- No Rally-side shim may hide a missing generic Doctrine feature.
- Git history is enough for retired bundle files. Do not keep dead mirror paths for archaeology.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. One editable source copy for Rally-owned built-ins.
2. Packaged installs keep working without stale bundled mirrors.
3. Host workspaces can build and run without hidden sync requirements.
4. Doctrine remains the owner for prompt language and emitted build rules.
5. The migration deletes old truth instead of preserving a bridge.

## 1.2 Constraints

- Rally treats `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` as fixed workspace folders today.
- Doctrine compile currently uses prompt roots listed in `pyproject.toml`.
- The Python package currently includes `rally = ["_bundled/**/*"]` as package data.
- Some external host repos may already have synced `stdlib/rally` and `skills/rally-kernel` files.
- The plan must keep generated readback distinct from source truth.

## 1.3 Architectural principles (rules we will enforce)

- Built-in content has one owner and one resolver.
- Runtime setup can copy generated or local working files only from the owner, never from a second checked-in owner.
- Missing required built-ins are hard errors.
- If Doctrine needs a generic import-root or package-resource ability, stop in Rally and ask for that feature.
- Tests should prove behavior through build, package, and run paths, not through string absence or repo-shape policing.

## 1.4 Known tradeoffs (explicit)

- Keeping canonical source under top-level `stdlib/` and `skills/` matches Rally's current workspace shape, but packaged installs may need a better package resource story.
- Moving canonical source under `src/rally/...` may make packaging easier, but it could fight the fixed top-level workspace model and prompt authoring rules.
- Keeping `rally workspace sync` as a convenience command may still be useful, but it must not be required to repair stale source copies.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Rally has top-level built-in source under `stdlib/rally` and Rally-owned skill prompt source under `skills/rally-*`. The package also has checked-in built-in copies under `src/rally/_bundled`. `tools/sync_bundled_assets.py` compares or refreshes that package mirror. Runtime paths copy packaged built-ins into host workspaces before build or run work.

## 2.2 What’s broken / missing (concrete)

- The same built-in prompt can exist in source and in a checked-in package mirror.
- A developer can update one copy and forget the other.
- The release or host-workspace path can ship stale built-in rules.
- The correct action is easy to miss because the duplicate copy looks like normal source.
- Host-workspace sync can blur what is source, what is vendor copy, and what is generated output.

## 2.3 Constraints implied by the problem

- The fix must remove the need for paired edits.
- The fix must still support packaged installs.
- The fix must keep Doctrine as the prompt compiler owner.
- The fix must update docs that currently tell users to sync built-ins.
- The fix must not add more control planes, hidden cleanup, or silent repair behavior.

# 3) Research Grounding (external + internal “ground truth”)

<!-- arch_skill:block:research_grounding:start -->

## 3.1 External anchors (papers, systems, prior art)

- No external system anchor is needed yet. The blocking fact is internal: Doctrine already accepts external filesystem prompt roots, including absolute paths, but not dependency-owned or embedding-runtime-supplied prompt roots as a first-class public contract.

## 3.2 Internal ground truth (code as spec)

Authoritative behavior anchors:

- `src/rally/services/bundled_assets.py` defines the current two-copy path. `_BUNDLE_SPECS` maps authored `stdlib/rally` to packaged `src/rally/_bundled/stdlib/rally`, emits `rally-kernel` into `src/rally/_bundled/skills/rally-kernel`, and `sync_bundled_assets()` checks or rewrites that mirror.
- `src/rally/services/bundled_assets.py` also defines host workspace materialization. `ensure_workspace_builtins_synced()` reads from package resource `rally._bundled` and replaces host `stdlib/rally` plus `skills/rally-kernel`.
- `tools/sync_bundled_assets.py` is the explicit stale-mirror command. Its purpose is to keep checked-in `_bundled` assets aligned with top-level source.
- `pyproject.toml` includes `rally = ["_bundled/**/*"]` as package data, so the installable package ships the mirror, not the top-level source.
- `src/rally/services/workspace_sync.py` exposes `rally workspace sync` as the front door for copying built-ins into a host workspace.
- `src/rally/services/flow_build.py` calls `sync_workspace_builtins()` before every flow build, then calls `doctrine.emit_docs` against the host `pyproject.toml`. It also validates prompt roots under `flows/<flow>/prompts`, `stdlib/rally/prompts`, and Doctrine skill prompt roots.
- `src/rally/services/runner.py` calls `sync_workspace_builtins()` before `rally run` and `rally resume`.
- `src/rally/services/home_materializer.py` copies per-agent skill views from workspace skill directories resolved by `skill_bundles.py`.
- `src/rally/services/skill_bundles.py` requires each skill to exist under `skills/<name>` as either `SKILL.md` or `prompts/SKILL.prompt`. Mandatory `rally-kernel` is always part of the expected skill set.
- `src/rally/domain/rooted_path.py` resolves `stdlib:` paths to `workspace_root / "stdlib" / "rally"`, which makes the workspace copy the current runtime-facing stdlib location.
- `../doctrine/doctrine/project_config.py` resolves `[tool.doctrine.compile].additional_prompt_roots` as existing filesystem directories from the target `pyproject.toml`. The path resolver accepts absolute paths as well as paths relative to that `pyproject.toml`.
- `../doctrine/doctrine/_compiler/support.py` builds import roots from the entrypoint's `prompts/` root plus those filesystem prompt roots.
- `../doctrine/doctrine/emit_common.py` requires configured emit entrypoints and output dirs to stay inside the target project root. This is good and should stay; Rally's gap is not output placement but dependency-owned prompt-root input.
- `../doctrine/docs/EMIT_GUIDE.md` documents that additional prompt roots are filesystem directories relative to `pyproject.toml`, while emitted output stays relative to the entrypoint's local `prompts/` root.

Canonical path / owner to reuse:

- Top-level `stdlib/rally/prompts` is the current authored stdlib source in Rally's source checkout.
- Top-level `skills/rally-kernel/prompts/SKILL.prompt` is the current authored source for the mandatory Rally skill.
- A clean final design must choose one Rally-owned source path for package install and source checkout. The current `_bundled` path is not acceptable as a second source owner.

Adjacent surfaces tied to the same contract family:

- `README.md` tells users to run `rally workspace sync` and says it writes built-ins into `stdlib/rally`, `skills/rally-kernel`, and `skills/rally-memory`; that already disagrees with current tests that copy only `rally-kernel`.
- `docs/RALLY_CLI_AND_LOGGING.md` defines `rally workspace sync` as copying `stdlib/rally` and `skills/rally-kernel`.
- `docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL.md` says host repos use `rally workspace sync` so Doctrine emit stays inside the workspace.
- `docs/RALLY_MASTER_DESIGN.md` says Rally owns `stdlib/rally`, `rally-kernel`, `rally-memory`, and the workspace sync path.
- `src/rally/_release_flow/ops.py` includes `uv run python tools/sync_bundled_assets.py --check` in the release proof set.
- `tests/unit/test_bundled_assets.py`, `tests/unit/test_workspace_sync.py`, `tests/unit/test_flow_build.py`, `tests/unit/test_runner.py`, and `tests/integration/test_packaged_install.py` assert the current bundle-copy model.
- `skills/rally-kernel/build/**` and `flows/*/build/**` are generated readback. They can remain generated output, but they must not be treated as a second editable source.
- `skills/rally-kernel/legacy/SKILL.md` is another retired-looking skill copy. `deep-dive` must classify and likely delete or ignore it through the existing `**/legacy` rule rather than letting it become live truth.

Compatibility posture (separate from `fallback_policy`):

- Clean cutover for Rally source and packaged built-ins. The checked-in `_bundled` mirror should be deleted, not kept behind a fallback.
- Preserve user-facing flow behavior: existing host projects should still compile and run after the supported setup path, but not by relying on stale copied Rally prompt source.
- No timeboxed bridge is approved.

Existing patterns to reuse:

- `src/rally/services/bundled_assets.py` already uses `importlib.resources.files()` and `as_file()` to read package resources. That pattern can still be useful for package-owned runtime asset reads, but not as a second checked-in source tree.
- `src/rally/services/flow_build.py` already centralizes the build preflight before Doctrine emit.
- `src/rally/services/skill_bundles.py` already centralizes skill-source resolution and can become the boundary where Rally-owned built-in skills resolve differently from workspace-owned skills.
- Doctrine's existing project-root rule for entrypoints and output dirs should be preserved. Rally should not ask Doctrine to emit outside the host project.

Prompt surfaces / agent contract to reuse:

- This is not an agent behavior problem. Prompt/native-model capability does not remove the need for a compiler import root.

Native model or agent capabilities to lean on:

- Not applicable. The key boundary is compiler and package resource resolution, not model reasoning.

Existing grounding / tool / file exposure:

- `rally run` and `rally resume` already call the build path before adapter launch, so a future one-copy design can fail before any agent turn if required built-ins are unavailable.
- `rally workspace sync` already exists as an operator command, but research does not support keeping it as a hidden correctness repair for stale Rally-owned source.

Duplicate or drifting paths relevant to this change:

- `stdlib/rally/**` versus `src/rally/_bundled/stdlib/rally/**`.
- `skills/rally-kernel/prompts/**` plus generated `skills/rally-kernel/build/**` plus packaged `src/rally/_bundled/skills/rally-kernel/**`.
- `skills/rally-kernel/legacy/SKILL.md`.
- Host workspace copies of `stdlib/rally/**` and `skills/rally-kernel/**` created by `rally workspace sync`.

Capability-first opportunities before new tooling:

- Prefer a Doctrine prompt-root provider capability over Rally scripts that mutate host workspaces, generate temporary pyprojects, rewrite host config with absolute install paths, or keep a mirror in `_bundled`.
- Prefer Rally package-resource resolution for built-in skill runtime files over copying those skills into every host workspace as source.

Behavior-preservation signals already available:

- `tests/unit/test_bundled_assets.py` currently proves bundle sync behavior and can be redirected to prove one-copy built-in resolution.
- `tests/unit/test_workspace_sync.py` currently proves host sync behavior and can be redirected or deleted depending on whether `rally workspace sync` survives.
- `tests/unit/test_flow_build.py` proves flow builds restore built-ins before Doctrine emit today.
- `tests/unit/test_runner.py` proves run/resume rebuilds prompt source and materializes the mandatory `rally-kernel` skill.
- `tests/integration/test_packaged_install.py` proves installed Rally can sync built-ins, emit a host flow, and run package-level behavior.

## 3.3 Decision gaps that must be resolved before implementation

- Blocked on Doctrine feature support — repo evidence checked: Rally bundle sync, package data, host workspace sync, flow build, skill bundle resolution, Doctrine project config, Doctrine compile import roots, Doctrine emit project-root guards, and Doctrine emit guide — default recommendation: do Doctrine first — answer needed: add generic Doctrine support for dependency-provided or embedding-runtime-supplied prompt roots.

Doctrine feature request:

- What exists: Doctrine already supports cross-root imports through filesystem-backed `additional_prompt_roots`. Those roots may live outside the emitting project and can work for `emit_docs` and `emit_flow`.
- What is missing: Doctrine needs a first-class way for an emitting project to consume prompt roots supplied by installed dependencies or by an embedding runtime, without copying those prompt files into the target project, without requiring host-authored or generated absolute install paths in the host project's compile config, and without moving emit entrypoints or outputs outside the target project.
- Why: Rally's stdlib is a framework-owned prompt library. Host projects need to import it while keeping one Rally-owned source copy. A host project can point `additional_prompt_roots` at an external Rally checkout or installed package path today, but that makes the host config own machine-specific Rally install details. Rally should be able to provide its own framework prompt root as a dependency/runtime input instead of copying `stdlib/rally/prompts` into each host workspace or asking users to vendor a path.
- Why now: removing Rally's checked-in `_bundled` mirror only fixes source-repo drift. It does not solve host flow compilation elegantly unless Doctrine can treat Rally's stdlib as a framework-provided compile input rather than host-authored workspace source.
- Non-goal: do not weaken Doctrine's rule that configured emit entrypoints and output dirs stay inside the target project root.

<!-- arch_skill:block:research_grounding:end -->

# 4) Current Architecture (as-is)

<!-- arch_skill:block:current_architecture:start -->

## 4.1 On-disk structure

Not started. `deep-dive` owns the full file inventory.

## 4.2 Control paths (runtime)

Not started. `deep-dive` must trace build, run, resume, package install, and workspace sync paths.

## 4.3 Object model + key abstractions

Not started.

## 4.4 Observability + failure behavior today

Not started.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI is expected.

<!-- arch_skill:block:current_architecture:end -->

# 5) Target Architecture (to-be)

<!-- arch_skill:block:target_architecture:start -->

## 5.1 On-disk structure (future)

Not started. The target must leave one source owner for built-ins and no checked-in mirror that needs manual sync.

## 5.2 Control paths (future)

Not started. The future path must read built-ins through one resolver and fail loudly when the owner is missing.

## 5.3 Object model + abstractions (future)

Not started.

## 5.4 Invariants and boundaries

Not started.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI is expected.

<!-- arch_skill:block:target_architecture:end -->

# 6) Call-Site Audit (exhaustive change inventory)

<!-- arch_skill:block:call_site_audit:start -->

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Not started | Not started | Not started | Not started | Not started | Not started | Not started | Not started |

## 6.2 Migration notes

Not started. `deep-dive` must classify each duplicate path as source, generated output, vendor copy, or dead mirror.

<!-- arch_skill:block:call_site_audit:end -->

# 7) Depth-First Phased Implementation Plan (authoritative)

<!-- arch_skill:block:phase_plan:start -->

> Rule: systematic build, foundational first; split Section 7 into the best sequence of coherent self-contained units, optimizing for phases that are fully understood, credibly testable, compliance-complete, and safe to build on later. If two decompositions are both valid, bias toward more phases than fewer. `Work` explains the unit and is explanatory only for modern docs. `Checklist (must all be done)` is the authoritative must-do list inside the phase. `Exit criteria (all required)` names the exhaustive concrete done conditions the audit must validate. Resolve adjacent-surface dispositions and compatibility posture before writing the checklist. Before a phase is valid, run an obligation sweep and move every required promise from architecture, call-site audit, migration notes, delete lists, verification commitments, docs/comments propagation, approved bridges, and required helper follow-through into `Checklist` or `Exit criteria`. Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). If a bridge is explicitly approved, timebox it and include removal work; otherwise plan either clean cutover or preservation work directly. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

Not started. `phase-plan` owns the authoritative checklist after research and deep dive settle the owner path and Doctrine boundary.

<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Avoid verification bureaucracy. Prefer existing credible signals that prove behavior. Do not add repo-shape policing, stale-term greps, file-absence gates, or doc-inventory tests as the main proof. For this refactor, prove preserved behavior through build, package, and run paths.

## 8.1 Unit tests (contracts)

Expected unit proof will likely include the changed built-in resolver, workspace setup, flow build, home materialization, skill bundle resolution, and runner paths.

## 8.2 Integration tests (flows)

Expected integration proof will likely include packaged install behavior and affected Doctrine flow or skill emits from the single source path.

## 8.3 E2E / device tests (realistic)

No device or UI E2E is expected. A live Rally run may be useful only if unit and integration proof leave a real adapter-risk gap.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Default posture is a clean cutover. Remove stale live truth instead of bridging old bundle behavior. If this would break existing host repos in a way repo evidence cannot settle, ask before planning a bridge.

## 9.2 Telemetry changes

No telemetry is expected. Existing command errors should be clear enough to show missing built-ins.

## 9.3 Operational runbook

Docs and CLI help must tell operators the new truth: where built-ins live, what is generated, and whether `rally workspace sync` still exists.

# 10) Decision Log (append-only)

## 2026-04-15 - Draft North Star for single-copy built-ins

Context

Rally has source built-ins and checked-in bundled mirrors. The user asked for a plan that removes the sync gotcha and keeps only one copy of Rally skills, stdlib, and related built-ins.

Options

- Keep mirrors and rely on a sync check.
- Delete mirrors and make one canonical asset owner serve source, package, host, build, and run paths.
- If Doctrine cannot use the single owner, stop and request Doctrine support.

Decision

Draft the plan around one source owner and no manual sync-for-correctness path. Do not patch around a Doctrine gap inside Rally.

Consequences

Research must inspect packaging, host workspace builds, Doctrine prompt roots, generated readback, and skill emit behavior before implementation can start.

Follow-ups

Confirm or correct this North Star before running `miniarch-step research`.

## 2026-04-15 - Research stopped on Doctrine prompt-root support

Context

Research confirmed that Rally's checked-in `_bundled` mirror is only part of the problem. Doctrine can compile against external filesystem prompt roots today, but host flow compilation still has no first-class way to receive Rally's installed stdlib as a dependency-owned prompt root. Without that, Rally either copies `stdlib/rally/prompts` into the host workspace or asks the host config to name a Rally install path.

Options

- Keep copying Rally stdlib prompts into host workspaces before Doctrine emit.
- Ask host projects to put absolute Rally install paths in `additional_prompt_roots`.
- Build a Rally-side workaround that mutates host config, creates temporary config, or preserves another hidden copy.
- Stop and ask for a generic Doctrine feature for dependency-provided or embedding-runtime-supplied prompt roots.

Decision

Stop the auto-plan before deep dive and request Doctrine support first.

Consequences

Rally should not implement the single-copy built-in-assets plan until Doctrine can consume framework-owned prompt roots without copying them into each host workspace and without making host configs own Rally install paths.

Follow-ups

Use the feature request in Section 3.3 as the Doctrine work item.
