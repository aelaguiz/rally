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

Approach: Replace checked-in bundled mirrors and sync-for-correctness habits with one canonical asset owner plus one resolver. Rally passes its stdlib prompt root to Doctrine through `ProvidedPromptRoot` and materializes required built-in skills from the same resolver.

Plan: Confirm this North Star, research current source/package/host paths, cut over Rally runtime and packaging, delete mirror paths, update docs and tests, then prove packaged and source workflows.

Non-negotiables: no dual live copies, no manual sync step required for correctness, no runtime fallback, no stale bundle mirror, and no Rally-side shim for a Doctrine gap.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-16
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
- Doctrine compile currently uses host-owned prompt roots listed in `pyproject.toml` plus runtime-owned prompt roots passed through `ProvidedPromptRoot`.
- The Python package currently includes `rally = ["_bundled/**/*"]` as package data.
- Some external host repos may already have synced `stdlib/rally` and `skills/rally-kernel` files.
- The plan must keep generated readback distinct from source truth.

## 1.3 Architectural principles (rules we will enforce)

- Built-in content has one owner and one resolver.
- Runtime setup can copy generated or local working files only from the owner, never from a second checked-in owner.
- Missing required built-ins are hard errors.
- Use Doctrine `ProvidedPromptRoot` for Rally-owned stdlib imports instead of host config paths or workspace copies.
- If Rally uncovers another generic Doctrine language or emit gap, stop in Rally and ask for that feature.
- Tests should prove behavior through build, package, and run paths, not through string absence or repo-shape policing.

## 1.4 Known tradeoffs (explicit)

- Keeping canonical source under top-level `stdlib/` and `skills/` matches Rally's current workspace shape, but packaged installs may need a better package resource story.
- Moving canonical source under `src/rally/...` may make packaging easier, but it could fight the fixed top-level workspace model and prompt authoring rules.
- Retiring `rally workspace sync` is a CLI break, but keeping a copy command would preserve the bad habit this plan removes.
- Direct host `python -m doctrine.emit_docs` becomes a non-framework-managed path for Rally stdlib imports unless Doctrine later adds a CLI provider-root input.

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

- No external system anchor is needed. The key fact is inside the local Doctrine worktree: Doctrine now has a public provider-root API for dependency-owned or embedding-runtime-supplied prompt roots.
- `../doctrine/docs/DEPENDENCY_PROMPT_ROOT_PROVIDERS_2026-04-16.md` is the design anchor. Adopt its model for Rally: Rally should pass its framework stdlib prompt root into Doctrine as a runtime-owned provider input, not copy that root into each host workspace and not ask host `pyproject.toml` files to name Rally install paths.

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
- `../doctrine/doctrine/project_config.py` now defines `ProvidedPromptRoot`, stores `provided_prompt_roots` on `ProjectConfig` and `CompileConfig`, validates provider names and paths, and keeps `[tool.doctrine.compile].additional_prompt_roots` as the host-owned TOML surface.
- `../doctrine/doctrine/_compiler/support.py` now merges the entrypoint `prompts/` root, host-configured `additional_prompt_roots`, and runtime-provided roots into one active import-root set. It fails loudly on duplicate active roots.
- `../doctrine/doctrine/_compiler/session.py` now accepts `provided_prompt_roots` in `CompilationSession`, `compile_prompt`, and `extract_target_flow_graph`. It also exposes `provided_prompt_root_for()` so emit code can label runtime roots without absolute machine paths.
- `../doctrine/doctrine/emit_common.py` now accepts `provided_prompt_roots` in `load_emit_targets()` and `resolve_direct_emit_target()`. It still requires configured emit entrypoints and output dirs to stay inside the target project root.
- `../doctrine/doctrine/emit_docs.py` now records provider-owned runtime package entrypoints with provider-relative labels such as `framework_stdlib:framework/stdlib/AGENTS.prompt`.
- `../doctrine/doctrine/compiler.py` exports `ProvidedPromptRoot`, so Rally can use the public Doctrine API.
- `../doctrine/docs/EMIT_GUIDE.md` documents the split between host-owned `additional_prompt_roots` and runtime-owned `provided_prompt_roots`.
- Focused Doctrine proof passed with `uv run --locked python -m unittest tests.test_project_config tests.test_import_loading tests.test_emit_docs tests.test_emit_flow`: 45 tests passed.

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
- Doctrine's provider-root API is the import-root boundary to reuse for Rally stdlib prompts.
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

- Use Doctrine `ProvidedPromptRoot` before any Rally script that mutates host workspaces, generates temporary pyprojects, rewrites host config with absolute install paths, or keeps a mirror in `_bundled`.
- Prefer Rally package-resource resolution for built-in skill runtime files over copying those skills into every host workspace as source.

Behavior-preservation signals already available:

- `tests/unit/test_bundled_assets.py` currently proves bundle sync behavior and can be redirected to prove one-copy built-in resolution.
- `tests/unit/test_workspace_sync.py` currently proves host sync behavior and can be redirected or deleted depending on whether `rally workspace sync` survives.
- `tests/unit/test_flow_build.py` proves flow builds restore built-ins before Doctrine emit today.
- `tests/unit/test_runner.py` proves run/resume rebuilds prompt source and materializes the mandatory `rally-kernel` skill.
- `tests/integration/test_packaged_install.py` proves installed Rally can sync built-ins, emit a host flow, and run package-level behavior.

## 3.3 Decision gaps that must be resolved before implementation

- No user decision gap remains from research. The old Doctrine blocker is resolved in the local `../doctrine` worktree.
- Later planning must treat these as fixed facts, not open choices:
  - Rally stdlib prompt imports should use Doctrine `ProvidedPromptRoot`.
  - Rally must keep Doctrine emit entrypoints and output dirs inside the host project.
  - Rally must not copy `stdlib/rally/prompts` into host workspaces for compiler correctness.
  - Rally must not write generated absolute Rally install paths into host project config.
  - Rally package release must require a Doctrine version that includes `ProvidedPromptRoot`; the current local proof is from the editable `../doctrine` checkout.

<!-- arch_skill:block:research_grounding:end -->

# 4) Current Architecture (as-is)

<!-- arch_skill:block:current_architecture:start -->

## 4.1 On-disk structure

- Authored Rally stdlib prompt source lives at `stdlib/rally/prompts/rally/*.prompt`.
- The current authored stdlib files are `base_agent.prompt`, `memory.prompt`, `review_results.prompt`, and `turn_results.prompt`.
- The checked-in package mirror lives at `src/rally/_bundled/stdlib/rally/prompts/rally/*.prompt`.
- The package mirror currently has extra stale-looking modules: `issue_ledger.prompt` and `notes.prompt` still exist under `_bundled`, while the current top-level `base_agent.prompt` owns those definitions directly.
- Authored Rally-owned skill source lives at `skills/rally-kernel/prompts/SKILL.prompt` and `skills/rally-memory/prompts/SKILL.prompt`.
- Generated skill readback lives at `skills/rally-kernel/build/**` and `skills/rally-memory/build/**`.
- The checked-in package mirror also ships `src/rally/_bundled/skills/rally-kernel/**`, which is a second copy of generated `rally-kernel` runtime skill output.
- Host workspaces can get copied `stdlib/rally/**` and `skills/rally-kernel/**` trees from `rally workspace sync`, `rally run`, or `rally resume`.
- `pyproject.toml` packages the mirror with `rally = ["_bundled/**/*"]`.
- `MANIFEST.in` also includes `src/rally/_bundled`.
- `tools/sync_bundled_assets.py` exists only to compare or rewrite the checked-in mirror from top-level source and generated skill output.

## 4.2 Control paths (runtime)

- Source checkout flow build:
  - `rally run` or `rally resume` calls `sync_workspace_builtins()`.
  - `sync_workspace_builtins()` is a no-op when the project name is `rally` or `rally-agents`.
  - `ensure_flow_assets_built()` calls Doctrine by subprocess: `python -m doctrine.emit_docs --pyproject <pyproject> --target <flow>`.
  - Source checkout Doctrine imports Rally stdlib through `[tool.doctrine.compile].additional_prompt_roots = ["stdlib/rally/prompts"]`.
  - Source checkout mandatory Doctrine skills such as `rally-kernel` are emitted before use.
- External host flow build:
  - `rally run`, `rally resume`, and `rally workspace sync` call `sync_workspace_builtins()`.
  - `ensure_workspace_builtins_synced()` copies from package resource `rally._bundled` into host `stdlib/rally` and `skills/rally-kernel`.
  - Host `pyproject.toml` then uses `additional_prompt_roots = ["stdlib/rally/prompts"]` so Doctrine can import `rally.*`.
  - `ensure_flow_assets_built()` still calls Doctrine by subprocess, so it has no way to pass `ProvidedPromptRoot`.
  - Mandatory built-in skill emission is skipped for external workspaces because the copied `skills/rally-kernel/SKILL.md` is treated as markdown skill source.
- Run-home materialization:
  - `materialize_run_home()` calls `sync_workspace_builtins()` again.
  - Compiled agents are copied from `flows/<flow>/build/agents/**` into `runs/<run-id>/home/agents/**`.
  - Per-agent skill views are copied from workspace `skills/<name>` directories into `runs/<run-id>/home/sessions/<agent>/skills/**`.
  - The live `home/skills/**` tree is refreshed from the selected agent's prebuilt skill view before adapter launch.
- CLI path:
  - `rally workspace sync` is an operator command that only copies built-ins and prints copied paths.
  - CLI help still tells host users to run `rally workspace sync` before first run.
- Release and package path:
  - `Makefile verify` runs `uv run python tools/sync_bundled_assets.py --check`.
  - `src/rally/_release_flow/ops.py` includes the same sync check in the release worksheet.
  - Packaged-install proof currently installs wheel or sdist, runs `rally workspace sync`, checks host copies, then emits and runs a host flow.

## 4.3 Object model + key abstractions

- `_BundleSpec` in `src/rally/services/bundled_assets.py` is the current asset map. It maps package mirror paths to workspace copy paths and either an authored source directory or a Doctrine emit target.
- `sync_bundled_assets()` builds a temp expected mirror and compares it to `src/rally/_bundled`.
- `ensure_workspace_builtins_synced()` copies from installed package resource `rally._bundled` into a workspace.
- `workspace_owns_rally_builtins()` decides whether to skip copying by reading only `[project].name`.
- `WorkspaceSyncResult` in `src/rally/services/workspace_sync.py` wraps the copy result for the CLI.
- `SkillBundleSource` in `src/rally/services/skill_bundles.py` assumes all skills are under workspace `skills/<name>`.
- `MANDATORY_SKILL_NAMES = ("rally-kernel",)` makes `rally-kernel` part of every agent's expected skill set.
- `resolve_rooted_path()` maps `stdlib:` to `workspace_root / "stdlib" / "rally"`.
- `_run_doctrine_emit()` hides Doctrine behind subprocess calls. That keeps the build CLI-shaped but blocks runtime-owned provider roots.
- Doctrine now provides the missing compiler-side object: `ProvidedPromptRoot`.

## 4.4 Observability + failure behavior today

- Missing package mirror files fail with messages such as `Bundled Rally asset is missing`.
- A stale package mirror can silently overwrite a host workspace during sync.
- Source checkout detection depends on project name, not on a verified Rally source checkout.
- Host workspaces can contain copied Rally-owned source that looks editable even when Rally intends it as framework output.
- Flow build failures surface as wrapped subprocess stderr from `doctrine.emit_docs` or `doctrine.emit_skill`.
- Missing skill runtime output fails in `SkillBundleSource.runtime_source_dir()` when `build/SKILL.md` is absent.
- There is no stable log field that says which built-in source path was used.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI is expected.

<!-- arch_skill:block:current_architecture:end -->

# 5) Target Architecture (to-be)

<!-- arch_skill:block:target_architecture:start -->

## 5.1 On-disk structure (future)

- Keep authored Rally stdlib source under top-level `stdlib/rally/prompts/**`.
- Keep authored Rally-owned skill source under top-level `skills/rally-*/prompts/**`.
- Keep generated readback under `skills/rally-*/build/**` and `flows/*/build/**`; it remains output, not editable source.
- Delete checked-in `src/rally/_bundled/**`.
- Delete `tools/sync_bundled_assets.py`.
- Remove `_bundled` package-data rules from `pyproject.toml` and `MANIFEST.in`.
- Package Rally built-ins into wheel and sdist as distribution output derived from the top-level source tree. The built distribution may contain a copy because packages must ship files, but the source checkout must not contain a second checked-in mirror.
- Host workspaces must not receive `stdlib/rally/**` or `skills/rally-kernel/**` copies for compiler correctness.
- If a host repo chooses to vendor Rally built-ins on purpose, that becomes host-owned source and is outside Rally's framework-managed single-copy path.

## 5.2 Control paths (future)

- Add one Rally built-in asset resolver. It returns the active stdlib prompt root and the active runtime skill bundle roots for the current environment.
- Source checkout mode:
  - The resolver points at top-level `stdlib/rally/prompts`.
  - The resolver points built-in Doctrine skills at top-level `skills/rally-*/build` after Rally emits them from `skills/rally-*/prompts`.
  - Source checkout detection must verify the expected source directories, not only `[project].name`.
- Packaged install mode:
  - The resolver points at installed distribution asset files produced from the same top-level source at build time.
  - Required built-in skill runtime bundles come from installed distribution assets, not from host workspace copies.
- Flow build:
  - `ensure_flow_assets_built()` stops calling `rally workspace sync`.
  - `ensure_flow_assets_built()` resolves Rally built-ins once.
  - It calls Doctrine through the Python API, not the CLI subprocess, so it can pass `ProvidedPromptRoot("rally_stdlib", <stdlib prompts path>)`.
  - It emits flow agents with `load_emit_targets(..., provided_prompt_roots=...)` and `emit_docs.emit_target(...)`.
  - It emits Doctrine-authored local skills with the same provider-root context when needed.
- Run and resume:
  - `rally run` and `rally resume` keep rebuilding flow assets before adapter launch.
  - They no longer sync built-ins into the workspace first.
  - Missing built-ins fail before any agent turn.
- Run-home materialization:
  - It copies compiled agent packages from workspace build output as it does today.
  - It copies built-in skills from the built-in resolver and workspace skills from the workspace resolver.
  - It rejects host workspace directories that shadow reserved Rally-owned skill names.
- CLI:
  - Retire `rally workspace sync` as a copy command.
  - CLI help should teach `rally run <flow>` and `rally resume <run-id>` as the supported framework-managed build/run path.
  - Direct `python -m doctrine.emit_docs` in a host repo is no longer the framework-managed Rally stdlib path because it cannot receive Rally's provider root from the CLI.

## 5.3 Object model + abstractions (future)

- New or renamed module: `src/rally/services/builtin_assets.py`.
- Core object: `RallyBuiltinAssets`.
  - `stdlib_prompts_root: Path`
  - `skill_runtime_dirs: dict[str, Path]`
  - `source_kind: "source_checkout" | "installed_distribution"`
- Core resolver function: `resolve_rally_builtin_assets(workspace: WorkspaceContext) -> RallyBuiltinAssets`.
- Doctrine boundary helper: `RallyBuiltinAssets.provided_prompt_roots()` returns a tuple containing `ProvidedPromptRoot("rally_stdlib", stdlib_prompts_root)`.
- Skill boundary:
  - `resolve_skill_bundle_source()` must accept the built-in asset set or move behind a new resolver that can distinguish workspace skills from Rally-owned built-in skills.
  - Reserved Rally-owned skill names, starting with `rally-kernel`, resolve from Rally built-ins unless the active workspace is the Rally source checkout.
  - External host workspaces that contain reserved Rally-owned skill directories fail loudly instead of shadowing framework assets.
- Doctrine emit boundary:
  - Replace `_run_doctrine_emit()` with a small Doctrine API facade.
  - The facade should keep one job: load a target with provider roots and call the matching Doctrine emit function.
  - Tests should patch this facade rather than asserting subprocess command arrays.
- Rooted path boundary:
  - `stdlib:` must resolve through the built-in asset resolver when runtime code needs a real stdlib file.
  - `stdlib:` must no longer assume `workspace_root / "stdlib" / "rally"` in external host workspaces.

## 5.4 Invariants and boundaries

- One editable owner: `stdlib/rally/prompts/**` and `skills/rally-*/prompts/**` in the Rally source checkout.
- One runtime resolver decides where built-ins are read from in this environment.
- No checked-in `_bundled` tree.
- No host workspace stdlib copy for compiler correctness.
- No generated absolute Rally install paths in host project config.
- Doctrine owns prompt imports and emitted output.
- Rally owns resolving its framework prompt root and passing it to Doctrine as `ProvidedPromptRoot`.
- Source checkout and installed package must render the same built-in prompt and skill content.
- Generated output may be copied into run homes, flow build dirs, skill build dirs, wheels, and sdists, but those outputs must be rebuilt or packaged from the single source owner.
- Missing required built-ins, missing provider-root support, or host shadowing of reserved Rally built-ins must fail loudly.
- No bridge or fallback path is approved.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI is expected.

<!-- arch_skill:block:target_architecture:end -->

# 6) Call-Site Audit (exhaustive change inventory)

<!-- arch_skill:block:call_site_audit:start -->

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Built-in assets | `src/rally/services/bundled_assets.py` | Whole module | Builds and reads checked-in `_bundled` mirrors. | Replace with `builtin_assets.py` or rewrite in place around one resolver. Remove mirror sync logic. | This is the main duplicate source path. | `resolve_rally_builtin_assets()`, `RallyBuiltinAssets`. | `tests/unit/test_bundled_assets.py` becomes resolver tests. |
| Built-in assets | `tools/sync_bundled_assets.py` | Script | Compares or rewrites `src/rally/_bundled`. | Delete. | A sync script is the gotcha this plan removes. | No replacement script. | Delete or rewrite tests that call `sync_bundled_assets()`. |
| Package data | `pyproject.toml` | `[tool.setuptools.package-data]` | Ships `_bundled/**/*`. | Remove `_bundled`; include built-in assets as distribution output derived from top-level source. | Package install must work without checked-in mirror. | Distribution asset paths owned by packaging config. | `tests/integration/test_packaged_install.py`, package release tests. |
| Package manifest | `MANIFEST.in` | `recursive-include src/rally/_bundled *` | Adds mirror to source distribution. | Remove `_bundled`; include required top-level built-in source and generated skill runtime output for distribution builds. | sdist must prove same single source. | Source-derived distribution files only. | Packaged install tests. |
| Workspace sync | `src/rally/services/workspace_sync.py` | Whole module | Copies built-ins into external workspaces. | Delete or reduce to a removed-command compatibility error owned by CLI. No copy path remains. | Host copies become another live-looking source. | No framework-managed workspace copy. | `tests/unit/test_workspace_sync.py`, `tests/unit/test_cli.py`. |
| CLI | `src/rally/cli.py` | `workspace sync` parser and `_workspace_sync_command()` | Exposes copy command and advertises it in help. | Remove copy command and update help/examples. | The operator surface should not teach manual sync. | `rally run` and `rally resume` are the supported build/run path. | `tests/unit/test_cli.py`. |
| Flow build | `src/rally/services/flow_build.py` | `ensure_flow_assets_built()` | Calls sync first, validates workspace stdlib, then shells out to Doctrine CLI. | Resolve built-ins first; pass `ProvidedPromptRoot` through Doctrine Python API; remove workspace sync. | Provider roots cannot be passed through the current Doctrine CLI. | Doctrine API facade with provider roots. | `tests/unit/test_flow_build.py`. |
| Flow build | `src/rally/services/flow_build.py` | `_run_doctrine_emit()` | Builds a subprocess command. | Replace with a typed emit facade for docs and skills. | Tests should prove behavior, not command spelling. | `emit_flow_docs_target()`, `emit_skill_target()` or equivalent. | Flow build unit tests. |
| Prompt validation | `src/rally/services/flow_build.py` | `_validate_prompt_rooted_paths()` | Scans workspace `stdlib/rally/prompts`. | Scan resolver-provided stdlib prompt root instead. | External host workspaces no longer contain stdlib. | Built-in resolver input. | Flow build rooted-path tests. |
| Runner | `src/rally/services/runner.py` | `run_flow()` and `resume_run()` | Calls `sync_workspace_builtins()` before build. | Remove sync; rely on `ensure_flow_assets_built()` to resolve and prove built-ins. | Build owns the preflight. | No workspace copy side effect. | Runner tests around missing/copied built-ins. |
| Home materialization | `src/rally/services/home_materializer.py` | `materialize_run_home()` | Calls `sync_workspace_builtins()` before copying agents and skills. | Remove sync; pass built-in resolver to skill materialization. | Run home should copy from the canonical resolver. | Built-in skill runtime source. | Runner and home materializer tests. |
| Skill resolution | `src/rally/services/skill_bundles.py` | `resolve_skill_bundle_source()` | Looks only under workspace `skills/<name>`. | Add built-in skill resolution and reserved-name shadow checks. | Mandatory `rally-kernel` should not require host workspace source. | Workspace skill vs Rally built-in skill boundary. | Skill bundle, runner, packaged install tests. |
| Rooted paths | `src/rally/domain/rooted_path.py` | `resolve_rooted_path()` for `stdlib:` | Resolves to `workspace_root / "stdlib" / "rally"`. | Accept a resolver-provided stdlib root or otherwise fail when `stdlib:` cannot be resolved. | `stdlib:` must work without host copies. | `stdlib_root` input or equivalent context object. | `tests/unit/test_rooted_path.py`, adapter MCP tests. |
| Flow loader | `src/rally/services/flow_loader.py` | `_resolve_rooted_existing_file()` | Allows bare `stdlib/rally/...` repo-relative files. | Route stdlib lookups through built-in resolver or remove the bare legacy path. | Bare stdlib paths imply host copies. | Rooted `stdlib:` or provider-root source identity. | Flow loader tests. |
| Adapters | `src/rally/adapters/codex/adapter.py`, `src/rally/adapters/claude_code/adapter.py` | `_expand_mcp_payload()` | Expands `stdlib:` through workspace-root behavior. | Pass the resolver-provided stdlib root when expanding internal MCP config. | Adapter-local MCP config must not require host stdlib copies. | Shared rooted-path expansion contract. | Adapter MCP projection tests. |
| Release proof | `Makefile` | `verify` | Runs `tools/sync_bundled_assets.py --check`. | Remove sync check; add package/resolver proof that built assets exist in wheel and sdist. | Drift check should be replaced by behavior proof. | Packaged resolver smoke. | Release/package tests. |
| Release flow | `src/rally/_release_flow/ops.py` | `render_release_worksheet()` | Lists bundle sync check. | Replace with package/resolver proof command. | Release guidance must stop teaching sync. | Updated release proof list. | `tests/unit/test_release_flow.py`. |
| Doctrine dependency | `pyproject.toml`, `docs/VERSIONING.md`, `CHANGELOG.md`, release tests | Doctrine package line | Current public floor is `doctrine-agents>=1.0.2,<2`. | Raise the floor once `ProvidedPromptRoot` is in a public Doctrine release. | Rally package cannot rely on editable `../doctrine`. | Public dependency includes provider-root API. | Package release and packaged install tests. |
| README | `README.md` | Host setup docs | Tells users to run `rally workspace sync` and add `additional_prompt_roots`. | Remove sync step for Rally stdlib; teach Rally-managed build/run path and provider-root-backed behavior. | Docs must not teach old copies. | Host pyproject no Rally stdlib prompt root. | Docs review only, plus packaged install fixture. |
| Runtime docs | `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_MEMORY.md`, `docs/RALLY_PORTING_GUIDE.md` | Built-in sync sections | Describe workspace copies as the front door. | Rewrite to say Rally resolves built-ins from source/package and passes stdlib to Doctrine. | Live docs would otherwise contradict runtime. | Single built-in resolver. | Docs inspection; no doc grep gate. |
| Packaged install proof | `tests/integration/test_packaged_install.py` | Host fixture | Runs `rally workspace sync`, expects host `stdlib/rally` and `skills/rally-kernel`, and manually calls Doctrine CLI. | Remove sync expectations; prove installed `rally run` builds via provider root and materializes required skill in run home. | This is the main external behavior proof. | Provider-root build through Rally. | Same integration test. |
| Unit tests | `tests/unit/test_bundled_assets.py` | Bundle sync tests | Prove copying and drift compare. | Rewrite to prove resolver source mode, installed-distribution mode, missing assets, and shadow failure. | Tests should guard behavior, not mirror files. | Built-in resolver contract. | Same file or renamed test. |
| Unit tests | `tests/unit/test_workspace_sync.py` | Workspace sync tests | Prove copy/no-op. | Delete with module or rewrite around removed CLI behavior if command leaves a message. | No workspace sync path remains. | None. | CLI tests cover removed command if kept. |
| Unit tests | `tests/unit/test_runner.py` | Built-in copy assertions | Expects workspace `skills/rally-kernel` and host stdlib copies. | Assert no host copies are required; assert run home gets `rally-kernel` from resolver. | Runtime behavior should stay but source path changes. | Built-in skill materialization. | Runner tests. |
| Generated readback | `flows/*/build/**`, `skills/rally-*/build/**` | Existing generated output | Output may repeat prompt text. | Keep generated output, rebuild affected outputs after source/import path changes, and do not treat it as source. | Plan removes live mirrors, not generated readback. | Generated output policy. | Recompile affected flows/skills. |
| Stale mirror files | `src/rally/_bundled/stdlib/rally/prompts/rally/issue_ledger.prompt`, `src/rally/_bundled/stdlib/rally/prompts/rally/notes.prompt` | Mirror-only modules | Still exist only in `_bundled` while top-level source now folds these definitions into `base_agent.prompt`. | Delete with `_bundled`. | Current drift proves the mirror is unsafe. | Git history is enough. | Resolver/package tests replace drift tests. |

## 6.2 Migration notes

Canonical owner path / shared code path:

- Rally stdlib source owner: `stdlib/rally/prompts/**`.
- Rally built-in skill source owner: `skills/rally-*/prompts/**`.
- Rally built-in runtime resolver owner: `src/rally/services/builtin_assets.py` or a direct rewrite of `bundled_assets.py` with the old mirror language removed.
- Doctrine import boundary: `ProvidedPromptRoot("rally_stdlib", <stdlib prompts root>)`.

Deprecated APIs and commands:

- `sync_bundled_assets()` and `tools/sync_bundled_assets.py`.
- `ensure_workspace_builtins_synced()`.
- `sync_workspace_builtins()` as a copy path.
- `rally workspace sync` as an operator workflow.

Delete list:

- `src/rally/_bundled/**`.
- `_bundled` package-data and manifest entries.
- Bundle sync script and release proof references.
- Tests whose only purpose is comparing source with `_bundled`.
- Host workspace copy expectations for `stdlib/rally/**` and `skills/rally-kernel/**`.

Adjacent surfaces tied to the same contract family:

- `README.md`, `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL.md`, `docs/RALLY_RUNTIME.md`, `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_MEMORY.md`, and `docs/RALLY_PORTING_GUIDE.md` must stop teaching workspace-copy correctness.
- Package release docs and release worksheet must replace bundle-sync proof with package/resolver proof.
- Packaged install fixture pyprojects must stop adding Rally stdlib through host-owned `additional_prompt_roots`.
- Source repo `pyproject.toml` may keep `additional_prompt_roots = ["stdlib/rally/prompts"]` for source-owned direct Doctrine commands. Host examples should not use it for Rally stdlib.

Compatibility posture / cutover plan:

- Clean cutover. No runtime bridge and no fallback to workspace copies.
- Preserve `rally run` and `rally resume` behavior: they still rebuild before launch and materialize required skills into the run home.
- Break the old host setup step: users should no longer run `rally workspace sync` for Rally built-ins.
- Direct host `python -m doctrine.emit_docs` with Rally stdlib imports is not the framework-managed path after this cutover unless Doctrine later adds a CLI provider-root input.

Capability-replacing harnesses to delete or justify:

- None. This is compiler and package resolution work, not model behavior work.

Live docs/comments/instructions to update or delete:

- Delete comments that describe package mirrors or bundle sync as clean-checkout proof.
- Add one short comment at the built-in resolver boundary explaining that the resolver owns the source/package split and must not grow fallback paths.
- Update CLI help so it does not advertise `workspace sync`.
- Update release docs and versioning docs when the Doctrine package floor changes.

Behavior-preservation signals for refactors:

- Existing flow build unit tests should prove flow emit still runs and validates generated package boundaries.
- Runner tests should prove `rally run` and `rally resume` still rebuild prompt source before launch and still materialize only allowed skills.
- Rooted path tests should prove `stdlib:` uses the resolver-provided root.
- Packaged install tests should prove wheel and sdist installs can build and run a host flow without host built-in copies.
- Doctrine-focused provider-root tests already passed in `../doctrine`.

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| --- | --- | --- | --- | --- |
| Built-in asset resolution | `src/rally/services/bundled_assets.py` | One `RallyBuiltinAssets` resolver | Removes mirror sync and workspace copy as hidden owners. | include |
| Doctrine emit | `src/rally/services/flow_build.py` | Python API with `ProvidedPromptRoot` | Keeps host config free of Rally install paths. | include |
| Skill materialization | `src/rally/services/skill_bundles.py`, `src/rally/services/home_materializer.py` | Reserved Rally built-in skill names resolve from built-ins | Prevents stale host vendored `rally-kernel` from shadowing Rally. | include |
| Rooted path expansion | `src/rally/domain/rooted_path.py`, adapter MCP expansion | Resolver-provided `stdlib:` root | Keeps internal stdlib paths working without host copies. | include |
| CLI surface | `src/rally/cli.py` | No copy-oriented workspace command | Avoids preserving the gotcha as an operator habit. | include |
| Package release | `pyproject.toml`, `MANIFEST.in`, `Makefile`, release flow | Distribution-output proof instead of source-mirror proof | Verifies installed behavior without keeping mirror source. | include |
| Optional memory skill | `skills/rally-memory/**`, `docs/RALLY_MEMORY.md` | Same built-in resolver rule if Rally ships it | Avoids solving only `rally-kernel` and recreating drift for memory later. | include |
| Manual pre-run emit command | New `rally build`-style CLI | Separate operator command for readback-only builds | Useful later, but not required to remove duplicate built-ins. | defer |

<!-- arch_skill:block:call_site_audit:end -->

# 7) Depth-First Phased Implementation Plan (authoritative)

<!-- arch_skill:block:phase_plan:start -->

> Rule: systematic build, foundational first; split Section 7 into the best sequence of coherent self-contained units, optimizing for phases that are fully understood, credibly testable, compliance-complete, and safe to build on later. If two decompositions are both valid, bias toward more phases than fewer. `Work` explains the unit and is explanatory only for modern docs. `Checklist (must all be done)` is the authoritative must-do list inside the phase. `Exit criteria (all required)` names the exhaustive concrete done conditions the audit must validate. Resolve adjacent-surface dispositions and compatibility posture before writing the checklist. Before a phase is valid, run an obligation sweep and move every required promise from architecture, call-site audit, migration notes, delete lists, verification commitments, docs/comments propagation, approved bridges, and required helper follow-through into `Checklist` or `Exit criteria`. Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). If a bridge is explicitly approved, timebox it and include removal work; otherwise plan either clean cutover or preservation work directly. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

Not started. `phase-plan` owns the authoritative checklist after research and deep dive settle the owner path and Doctrine boundary.

<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Avoid verification bureaucracy. Prefer existing credible signals that prove behavior. Do not add repo-shape policing, stale-term greps, file-absence gates, or doc-inventory tests as the main proof. For this refactor, prove preserved behavior through build, package, and run paths.

## 8.1 Unit tests (contracts)

Expected unit proof should include the built-in resolver, provider-root Doctrine emit facade, rooted `stdlib:` resolution, home materialization, skill bundle resolution, runner paths, and removed workspace-sync CLI behavior.

## 8.2 Integration tests (flows)

Expected integration proof should include wheel and sdist installs that build and run a host flow without host `stdlib/rally` or `skills/rally-kernel` copies. Source checkout proof should rebuild affected flows and built-in skills from top-level source.

## 8.3 E2E / device tests (realistic)

No device or UI E2E is expected. A live Rally run may be useful only if unit and integration proof leave a real adapter-risk gap.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Default posture is a clean cutover. Remove stale live truth instead of bridging old bundle behavior. If this would break existing host repos in a way repo evidence cannot settle, ask before planning a bridge.

## 9.2 Telemetry changes

No telemetry is expected. Existing command errors should be clear enough to show missing built-ins.

## 9.3 Operational runbook

Docs and CLI help must tell operators the new truth: where built-ins live, what is generated, and that `rally workspace sync` is retired as a copy command.

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

## 2026-04-16 - Doctrine provider-root support clears the research blocker

Context

The local `../doctrine` worktree now includes the dependency prompt-root provider support that this Rally plan needed. Focused Doctrine tests for project config, import loading, docs emit, and flow emit passed.

Options

- Keep the old blocker and wait for a separate Doctrine answer.
- Use the existing host-owned `additional_prompt_roots` path and require host config paths.
- Continue Rally planning against Doctrine `ProvidedPromptRoot` as the compiler input boundary.

Decision

Continue Rally planning. Treat Doctrine `ProvidedPromptRoot` as the chosen way for Rally to pass its stdlib prompt root into host flow compilation.

Consequences

Rally no longer needs to stop at research for a Doctrine feature request. The deep-dive must now design the Rally side: one built-in source owner, one resolver path, no checked-in `_bundled` mirror, no host stdlib copy for compiler correctness, and a package dependency floor once Doctrine releases the provider-root API.

Follow-ups

Let the armed `auto-plan` controller continue to `deep-dive`.

## 2026-04-16 - Deep-dive chooses resolver cutover and retires workspace sync

Context

Deep-dive traced current source, package, host workspace, flow build, run, resume, run-home, CLI, and release paths. The current checked-in mirror already differs from top-level stdlib source, which proves the mirror can drift in the exact way this plan must prevent.

Options

- Keep `rally workspace sync` and make it less important.
- Move authored source under `src/rally` to make package data easy.
- Keep top-level authored source, remove checked-in mirrors, and add one built-in resolver that serves source checkouts and installed packages.

Decision

Keep top-level `stdlib/` and `skills/` as authored source. Delete `_bundled` and bundle sync. Retire `rally workspace sync` as a copy command. Build host flows through Rally's Doctrine API boundary with `ProvidedPromptRoot`.

Consequences

The implementation must touch packaging, flow build, run-home skill materialization, rooted `stdlib:` resolution, CLI help, release proof, tests, and live docs in one coherent cutover. Direct host `python -m doctrine.emit_docs` is no longer the framework-managed path for Rally stdlib imports unless Doctrine later exposes provider roots in its CLI.

Follow-ups

Let the armed `auto-plan` controller continue to `phase-plan`.
