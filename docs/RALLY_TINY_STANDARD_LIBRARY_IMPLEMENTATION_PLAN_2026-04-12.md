---
title: "Rally - Tiny Standard Library - Architecture Plan"
date: 2026-04-12
status: superseded
fallback_policy: forbidden
owners: ["aelaguiz"]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - ../doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md
---

Superseded note on 2026-04-12: the master design now separates durable
handoffs/currentness from end-of-turn runtime results. `lifecycle.prompt` was
removed from the current Rally stdlib, and end-of-turn outcomes now belong to a
strict adapter-enforced JSON return contract rather than a Doctrine lifecycle
module. References below to `lifecycle.prompt` are historical.

# TL;DR

- Outcome: Rally gets the first real Doctrine-native stdlib under repo-root `stdlib/rally/`, sized exactly to the master design: handoffs, currentness conventions, and lifecycle outcomes.
- Assumption: Doctrine lands the cross-root import contract from [../doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md](/Users/aelaguiz/workspace/doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md), specifically repo-level `additional_prompt_roots` with ordinary absolute imports and no alias dialect.
- Key architecture choice: because the assumed Doctrine support extends ordinary module resolution rather than introducing alias-prefixed imports, the importable package should be `rally.*`, which means the actual files should live under `stdlib/rally/prompts/rally/`, not directly under `stdlib/rally/prompts/`.
- Scope: implement only the tiny shared stdlib surface defined in the master design, plus the smallest local smoke proof needed to show that the modules compose and stay small. Do not build the example flow, runner, or runtime archive/session surfaces yet.
- Non-negotiables: no giant base-agent framework, no universal artifact taxonomy, no runtime shims, no copied prompt truth, no fake currentness DSL that pretends Doctrine has generics it does not have. Flow-owned artifacts stay flow-owned.

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can ship a very small, useful Doctrine-native standard library now if it
keeps the reusable surface narrow: one shared handoff contract, one thin
currentness-convention module, and one small lifecycle-status module, all
imported as ordinary Doctrine source from repo-root `stdlib/rally/`.

## 0.2 In scope

- Add the first Rally stdlib prompt tree under repo root.
- Add the Rally repo-level Doctrine compile config needed to consume that
  stdlib from future flow entrypoints.
- Implement the three modules named by the master design:
  - `rally.handoffs`
  - `rally.currentness`
  - `rally.lifecycle`
- Keep the stdlib surface small and flow-oriented:
  - shared issue-ledger handoff/status target
  - shared outputs for current-artifact and no-current handoffs
  - light shared lifecycle outputs for `done`, `blocker`, and `sleep`
  - thin currentness conventions that make the authored law forms explicit
- Add the smallest local smoke surface needed to prove imports and composition
  once the Doctrine support lands.

## 0.3 Out of scope

- Building the Rally runner, session management, scheduler, wake queue, or CLI.
- Building the first illustrative product flow beyond a tiny stdlib smoke.
- A universal artifact family or file taxonomy.
- A giant stdlib parent agent hierarchy.
- New Doctrine semantics beyond the assumed cross-root import support.
- Any workaround that copies stdlib source into flow-local trees.

## 0.4 Definition of done (acceptance evidence)

- Rally has one canonical stdlib tree under repo-root `stdlib/rally/`.
- The Rally repo declares the stdlib root through the assumed Doctrine compile
  config.
- The stdlib exports importable modules under the `rally.*` namespace.
- `handoffs.prompt`, `currentness.prompt`, and `lifecycle.prompt` exist as
  real Doctrine source and stay within the light-touch scope described in the
  master design.
- A minimal local smoke entrypoint can import the stdlib and compile once the
  Doctrine cross-root import support lands.
- The master design and any local docs touched by implementation reflect the
  actual importable layout and no longer imply a conflicting package shape.

## 0.5 Key invariants (fix immediately if violated)

- `stdlib/rally/` is Rally-owned Doctrine source, not generated output.
- The importable package name is `rally.*`, not bare `handoffs` /
  `currentness` / `lifecycle`.
- The stdlib owns handoff and lifecycle conventions, not concrete flow-owned
  artifacts.
- `currentness.prompt` stays intentionally thin; do not invent a fake reusable
  law macro system.
- `handoffs.prompt` and `lifecycle.prompt` may share a custom Rally runtime
  target, but they must not drag in runner/session behavior.
- No broad inheritance-first framework. Prefer imported declarations and
  narrowly reusable outputs.
- If a design choice would force hidden runtime policy or copied prompt truth,
  stop and fail loudly.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
mini_plan_pass: done 2026-04-12
recommended_flow: arch-step implement docs/RALLY_TINY_STANDARD_LIBRARY_IMPLEMENTATION_PLAN_2026-04-12.md
note: This mini-plan assumes ../doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md lands first or in lockstep. No code execution belongs to this pass.
-->
<!-- arch_skill:block:planning_passes:end -->

# 1) Key Design Considerations (what matters most)

- The stdlib must stay small enough to remain obviously reusable Doctrine
  source, not a hidden Rally framework.
- The importable namespace must stay explicit as `rally.*` under ordinary
  cross-root imports so future flows do not depend on bare module names.
- Flow-owned artifact files stay outside the stdlib; the stdlib only owns the
  reusable handoff, currentness, and lifecycle contracts.
- `currentness.prompt` must remain convention-oriented instead of pretending
  Doctrine ships generic law macros.
- Verification should use the smallest real Doctrine compile path, not a
  custom Rally harness.

# 2) Problem Statement (existing architecture + why change)

Rally started this pass as a design-only repo with no prompt sources, no
compile config, and no local proof that the tiny standard library described in
the master design could even be authored cleanly.

The master design already had the right conceptual split, but the provisional
source layout under `stdlib/rally/prompts/*.prompt` was too imprecise for the
assumed Doctrine cross-root import contract. Under ordinary additional prompt
roots, that layout would force bare imports like `import handoffs`, which is
both collision-prone and weaker than the intended Rally-owned namespace.

This implementation therefore needs to do three concrete things:

- establish the first real stdlib source tree and repo-level compile config
- author the tiny reusable Doctrine surface without overbuilding into runner
  work
- prove the resulting modules compile through a real Rally flow entrypoint

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md) - adopt: repo-root `stdlib/rally/` ownership, tiny stdlib scope, composition-first reuse, flow-owned concrete artifacts, and the three-module split of handoffs/currentness/lifecycle. Reject: treating the provisional `stdlib/rally/prompts/*.prompt` sketch as a locked importable package shape when the assumed Doctrine import contract now says ordinary module identity remains relative to a configured `prompts/` root.
- [../doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md](/Users/aelaguiz/workspace/doctrine/docs/DOCTRINE_CROSS_ROOT_STANDARD_LIBRARY_IMPORT_SUPPORT_2026-04-12.md) - adopt: repo-level compile config via `[tool.doctrine.compile].additional_prompt_roots`, ordinary absolute imports across configured roots, relative imports staying inside the importer's root, and no alias-prefixed stdlib dialect. This directly shapes the Rally importable layout.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md) - the current repo's only real product/design artifact. It is the source of truth for the tiny stdlib's intended responsibility split and non-goals.
  - Repo file inventory on 2026-04-12 shows Rally is currently design-only: no `pyproject.toml`, no `stdlib/`, no `flows/`, and no existing prompt sources. The first stdlib implementation will therefore create the canonical owner paths from scratch rather than migrate live code.
- Canonical path / owner to reuse:
  - [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md) - keeps the conceptual ownership split and should be reconciled to the final importable file layout if that layout becomes more precise than the provisional sketch.
- Existing patterns to reuse:
  - The master design already says "composition first, inheritance second." The implementation should therefore prefer imported declarations and reusable outputs over base agents or a heavy inheritance stack.
- Prompt surfaces / agent contract to reuse:
  - The master design's provisional stdlib sketch defines three reusable surfaces:
    - shared handoff outputs and trusted carriers
    - shared currentness conventions around `current artifact ... via ...` and `current none`
    - shared lifecycle outcomes for `done`, `blocker`, and `sleep`
- Existing grounding / tool / file exposure:
  - Rally currently has only local markdown docs. There is no existing code or harness to preserve, so the implementation must create the first canonical structure directly.
- Duplicate or drifting paths relevant to this change:
  - The master design's provisional source tree shows files directly under `stdlib/rally/prompts/`, but the assumed Doctrine import contract does not add a package alias system. If Rally keeps that direct layout, consuming flows would import bare module names like `handoffs`, which is both less explicit and collision-prone. The implementation plan should therefore converge on `stdlib/rally/prompts/rally/*.prompt` and repair local docs if needed.
- Capability-first opportunities before new tooling:
  - The tiny stdlib can be implemented entirely with existing Doctrine declaration families plus the assumed cross-root import support. No extra wrapper generator, manifest compiler, or preprocessing layer is justified.
- Behavior-preservation signals already available:
  - The repository is currently empty of stdlib code, so the relevant preservation signal is architectural rather than behavioral: keep the stdlib small, keep concrete artifacts flow-owned, and avoid inventing fake generic law abstractions that Doctrine does not ship.

## 3.3 Decision gaps that must be resolved before implementation

- None at mini-plan level. The implementation-shaping decisions are now fixed:
  - use repo-root `pyproject.toml` with `[tool.doctrine.compile].additional_prompt_roots = ["stdlib/rally/prompts"]`
  - make the importable namespace `rally.*` by storing the actual modules under `stdlib/rally/prompts/rally/`
  - keep `currentness.prompt` thin and convention-oriented rather than pretending it can abstract arbitrary `law` statements
  - add one tiny local smoke entrypoint for proof, not the first full example flow
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Rally currently has:
  - [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md)
- Rally currently does not have:
  - `pyproject.toml`
  - `stdlib/`
  - `flows/`
  - any `.prompt` source

## 4.2 Control paths (runtime)

- There is no local Doctrine compile contract declared yet.
- There is no local stdlib import surface yet.
- The only current source of truth for the stdlib is the prose design in the
  master design doc.

## 4.3 Object model + key abstractions

- Today the stdlib exists only as three conceptual buckets in the master
  design:
  - handoffs
  - currentness conventions
  - lifecycle outcomes
- No concrete Doctrine declarations have been authored yet, so the first
  implementation pass will also establish the canonical declaration names.

## 4.4 Observability + failure behavior today

- No compile smoke exists because there are no prompts yet.
- No repo-local import contract exists because there is no `pyproject.toml`.
- The main current risk is structural drift: implementing a package layout that
  conflicts with the assumed Doctrine cross-root contract or bloating the
  stdlib beyond the tiny scope in the design.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

Rally should gain this minimal source layout:

```text
pyproject.toml
stdlib/
  rally/
    prompts/
      rally/
        handoffs.prompt
        currentness.prompt
        lifecycle.prompt
flows/
  _stdlib_smoke/
    prompts/
      AGENTS.prompt
```

Important detail:

- `stdlib/rally/` remains the Rally-owned stdlib home.
- `stdlib/rally/prompts/` is the configured additional Doctrine prompt root.
- `stdlib/rally/prompts/rally/` is the actual importable package namespace, so
  future flow entrypoints can write `import rally.handoffs`, not bare
  `import handoffs`.

## 5.2 Control paths (future)

- Repo compile config:
  - add `[tool.doctrine.compile]`
  - set `additional_prompt_roots = ["stdlib/rally/prompts"]`
- Import model:
  - future flow entrypoints under `flows/<flow>/prompts/` import the stdlib via
    ordinary absolute imports:
    - `import rally.handoffs`
    - `import rally.currentness`
    - `import rally.lifecycle`
- Stdlib module split:
  - `rally.handoffs`
    - owns the custom Rally issue-ledger append target
    - owns the reusable handoff outputs for:
      - one current artifact remains current
      - no durable artifact remains current
    - owns the trusted carrier field names that downstream turns can rely on
  - `rally.currentness`
    - imports the shared handoff contracts
    - owns the explicit currentness conventions for how consuming flows should
      author `current artifact ... via ...` and `current none`
    - stays thin because Doctrine does not ship generic law macros
  - `rally.lifecycle`
    - reuses the same Rally issue-ledger append target
    - owns the shared lifecycle outputs for:
      - `done`
      - `blocker`
      - `sleep`
    - carries only the minimal explanation and sleep-duration fields the Rally
      runtime needs to interpret

## 5.3 Object model + abstractions (future)

The implementation should settle on concrete reusable declarations with these
boundaries:

- `handoffs.prompt`
  - one `output target` for Rally issue-ledger append/status writes
  - one shared current-artifact handoff output
  - one shared no-current handoff output
  - minimal shared fields:
    - what changed
    - current artifact when one exists
    - what to use now
    - next owner
  - `trust_surface` for the portable carrier fields only
- `currentness.prompt`
  - no fake abstraction over arbitrary artifact refs
  - a thin reusable convention surface that names the exact handoff outputs and
    the exact law forms consuming flows should use with them
  - if it needs reusable declarations at all, keep them lightweight and
    documentation-adjacent rather than inheritance-heavy
- `lifecycle.prompt`
  - one `done` output with human-readable completion summary
  - one `blocker` output with human-readable failure/explanation
  - one `sleep` output with human-readable explanation plus requested duration

## 5.4 Invariants and boundaries

- The stdlib does not own concrete artifact files like `repair_plan.md` or
  `verification.md`.
- The stdlib does not own flow rosters, runtime configs, session state, or
  wake scheduling behavior.
- The only shared runtime contract it owns is the authored Doctrine surface the
  runtime will inspect.
- Composition first:
  - consuming flows import `rally.*`
  - do not require all Rally agents to inherit from one giant abstract parent
- The smoke flow is verification only. It must not quietly grow into the first
  real example flow or a second framework inside the repo.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Repo compile contract | `pyproject.toml` | `[tool.doctrine.compile].additional_prompt_roots` | File absent | Add repo-level Doctrine compile config pointing at `stdlib/rally/prompts` | Future flow entrypoints need one canonical stdlib root | Rally declares one additional prompt root for stdlib imports | Targeted compile smoke once Doctrine support lands |
| Stdlib package namespace | `stdlib/rally/prompts/rally/` | importable package root | Path absent | Create `rally/` package directory under the configured prompt root | Preserve `rally.*` namespace under ordinary Doctrine imports | `import rally.handoffs`, `import rally.currentness`, `import rally.lifecycle` | Targeted compile smoke |
| Shared handoff contracts | `stdlib/rally/prompts/rally/handoffs.prompt` | custom output target + shared handoff outputs | File absent | Add the Rally issue-ledger target plus current/no-current handoff outputs and carrier fields | This is the real reusable stdlib surface flows will depend on | Shared Rally handoff declarations | Targeted compile smoke |
| Thin currentness conventions | `stdlib/rally/prompts/rally/currentness.prompt` | currentness convention declarations / prose owner | File absent | Add a thin convention module that imports the shared handoff surface and names the required authored currentness patterns | Keep currentness explicit without inventing unsupported generic abstractions | Shared currentness convention surface | Targeted compile smoke |
| Shared lifecycle outputs | `stdlib/rally/prompts/rally/lifecycle.prompt` | `done` / `blocker` / `sleep` outputs | File absent | Add the minimal lifecycle status outputs and fields | Standardize flow-ending / sleep signaling without extra runtime config | Shared lifecycle declarations | Targeted compile smoke |
| Smoke proof | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | minimal consuming flow | Path absent | Add one tiny smoke entrypoint that imports and uses the stdlib | Prove imports and composition without building the first real example flow | Minimal local verification-only consumer | Targeted compile smoke |
| Design reconciliation | `docs/RALLY_MASTER_DESIGN_2026-04-12.md` | provisional stdlib layout wording | Provisional sketch says modules directly under `stdlib/rally/prompts/` | Update only if needed so design truth matches final importable package shape | Avoid local doc drift once layout is concrete | Canonical importable layout if implementation sharpens it | Docs only |

## 6.2 Migration notes

* Canonical owner path / shared code path:
  - `stdlib/rally/prompts/rally/` is the importable stdlib package root.
* Deprecated APIs (if any):
  - none; this is the first implementation.
* Delete list (what must be removed; include superseded shims/parallel paths if any):
  - do not add parallel copies of stdlib modules under `flows/**/prompts/`
  - do not add a second package layout that keeps bare `handoffs.prompt` /
    `currentness.prompt` / `lifecycle.prompt` directly under the configured
    root
* Capability-replacing harnesses to delete or justify:
  - do not add preprocessors, codegen, or copied bundle steps
* Live docs/comments/instructions to update or delete:
  - reconcile the master design if the concrete package path is sharper than
    the provisional sketch
* Behavior-preservation signals for refactors:
  - keep the stdlib tiny
  - keep flow-owned artifacts outside the stdlib
  - keep the smoke flow obviously verification-only

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Package layout | `stdlib/rally/prompts/rally/*` | namespace-under-root layout | Prevent bare-module collisions under ordinary multi-root imports | include |
| Reuse model | stdlib prompt modules | composition-first imported declarations | Prevent a heavy base-agent framework | include |
| Currentness abstraction | `rally.currentness` | convention module, not fake generic law DSL | Prevent overbuilding against Doctrine features that do not exist | include |
| Proof surface | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | tiny consumer smoke instead of first full example flow | Keep scope narrow while still proving imports | include |
| Product flows | future `flows/*` | real example flow after stdlib lands | Prevent scope bleed in this pass | defer |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with the smallest credible signal. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 — Stdlib foundation

Status: COMPLETE

Completed work:

- Added repo-root `pyproject.toml` with
  `[tool.doctrine.compile].additional_prompt_roots = ["stdlib/rally/prompts"]`.
- Created `stdlib/rally/prompts/rally/` and implemented
  `handoffs.prompt`, `currentness.prompt`, and `lifecycle.prompt`.
- Kept concrete artifacts flow-owned and the currentness surface thin.

* Goal:
  Create the canonical Rally stdlib package and repo compile contract with the
  smallest reusable Doctrine surface that matches the master design.
* Work:
  - Add repo-root `pyproject.toml` with `[tool.doctrine.compile].additional_prompt_roots = ["stdlib/rally/prompts"]`.
  - Create `stdlib/rally/prompts/rally/`.
  - Implement `handoffs.prompt` with:
    - the Rally issue-ledger append target
    - one current-artifact handoff output
    - one no-current handoff output
    - minimal shared fields and trusted carriers
  - Implement `lifecycle.prompt` with:
    - `done`
    - `blocker`
    - `sleep`
    outputs against the same Rally target.
  - Implement `currentness.prompt` as a thin convention module that imports the
    shared handoff surface and makes the authored currentness forms explicit
    without inventing unsupported abstractions.
* Verification (smallest signal):
  - Each prompt file parses cleanly once the assumed Doctrine support is
    available.
  - Static review confirms the importable namespace is `rally.*` and that no
    flow-owned artifact contract leaked into the stdlib.
* Docs/comments (propagation; only if needed):
  - Add brief prompt comments only at the canonical boundaries where the module
    split or thin-currentness choice would otherwise be easy to misread.
* Exit criteria:
  - The repo has one canonical stdlib prompt tree and one repo-level compile
    contract.
  - The stdlib surface is still clearly tiny and modular.
* Rollback:
  - Remove the new stdlib tree and repo compile config together if the
    structure proves incompatible with the assumed Doctrine import contract.

## Phase 2 — Smoke proof and design reconciliation

Status: COMPLETE

Completed work:

- Added `flows/_stdlib_smoke/prompts/AGENTS.prompt` as a verification-only
  consumer of `rally.handoffs`, `rally.currentness`, and `rally.lifecycle`.
- Verified `PlanAuthor`, `RouteRepair`, and `Closeout` compile against the
  provisional local Doctrine branch in `../doctrine`.
- Reconciled the master design so the source layout reflects the actual
  `rally.*` package namespace under the configured prompt root.

* Goal:
  Prove that future Rally flows can consume the stdlib through ordinary imports
  and keep local docs aligned with the concrete package shape.
* Work:
  - Add `flows/_stdlib_smoke/prompts/AGENTS.prompt` as a minimal verification
    consumer.
  - Use the smoke entrypoint to prove:
    - importing `rally.handoffs`
    - importing `rally.currentness`
    - importing `rally.lifecycle`
    - one current-artifact handoff path
    - one no-current path
    - one lifecycle status output
  - Reconcile [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md) if the final importable package path needs to be made more precise than the provisional sketch.
* Verification (smallest signal):
  - Run one targeted Doctrine compile or corpus-style smoke against the local
    smoke entrypoint after the assumed Doctrine support lands.
  - Manual audit confirms the smoke flow stayed verification-only and did not
    quietly become the first real example flow.
* Docs/comments (propagation; only if needed):
  - Repair the master design only where the now-concrete import path or module
    responsibilities would otherwise leave a stale claim.
* Exit criteria:
  - The stdlib is locally consumable through ordinary imports.
  - Rally docs no longer imply a conflicting package shape.
* Rollback:
  - Drop the smoke entrypoint if it starts dragging in product-flow behavior or
    runner assumptions instead of staying a verification surface.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- Prefer the Doctrine compiler itself as the contract proof instead of adding
  Rally-local harnesses.
- Keep proof to the smallest live surface that exercises cross-root imports and
  the authored stdlib declarations.

## 8.2 Integration tests (flows)

- Primary proof:
  `cd /Users/aelaguiz/workspace/doctrine && uv run --locked python - <<'PY' ...`
- The verification compiles the Rally smoke entrypoint at
  `../rally/flows/_stdlib_smoke/prompts/AGENTS.prompt` and then compiles the
  concrete agents `PlanAuthor`, `RouteRepair`, and `Closeout`.
- This is enough to prove:
  - Rally repo config is discovered from the smoke source path
  - cross-root imports resolve through `stdlib/rally/prompts`
  - the three stdlib modules compose in one real entrypoint

## 8.3 E2E / device tests (realistic)

- Not applicable in this pass.
- There is no Rally runner or product flow yet, so end-to-end behavior remains
  out of scope.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- This is source-only rollout inside the Rally repo.
- Future flows should import the stdlib through:
  - `import rally.handoffs`
  - `import rally.currentness`
  - `import rally.lifecycle`

## 9.2 Telemetry changes

- None.
- This pass adds authored source and compile config only.

## 9.3 Operational runbook

- When cross-root import support is needed locally, verify from the Doctrine
  repo so its locked environment and compiler code are the active truth:
  `cd /Users/aelaguiz/workspace/doctrine && uv run --locked python - <<'PY' ...`
- Use the Rally smoke entrypoint as the default minimal proof surface before
  building any first real flow.

# 10) Decision Log (append-only)

## 2026-04-12 - Use a namespaced package under the configured prompt root

Context

- The assumed Doctrine support adds cross-root imports through
  `[tool.doctrine.compile].additional_prompt_roots`, but it does not add a
  separate alias dialect for standard libraries.

Options

- Keep the files directly under `stdlib/rally/prompts/` and accept bare module
  imports.
- Create a real `rally/` package directory under the configured prompt root and
  import the stdlib as `rally.*`.

Decision

- Create `stdlib/rally/prompts/rally/` and treat `rally.*` as the canonical
  importable namespace.

Consequences

- Rally gets an explicit, collision-resistant stdlib namespace.
- The master design must stop implying the earlier bare-module layout.

Follow-ups

- Future Rally flows should import the stdlib only through `rally.*`.

## 2026-04-12 - Keep the smoke proof on the honest local no-current path

Context

- The first compile attempt failed with Doctrine `E339` because the shared
  imported `RallyNoCurrentArtifactHandoff.next_owner` field did not
  structurally bind a routed owner in the smoke flow.

Options

- Invent new Doctrine support or a Rally shim for generic routed-owner binding.
- Add a flow-local wrapper output only for the smoke proof.
- Keep the shared stdlib untouched and prove the honest local no-current path.

Decision

- Keep the stdlib generic and keep the smoke proof on the local no-current
  path, where the same owner stays responsible until a durable artifact exists.

Consequences

- The smoke still proves `current none` plus the shared no-current handoff.
- The tiny stdlib pass does not claim a generic reusable routed-owner binding
  contract that the current authored surface does not actually provide.

Follow-ups

- If a real Rally flow later needs shared no-current outputs on semantic
  reroutes, decide then whether that binding should stay flow-owned or justify a
  Doctrine-side reusable authoring surface.
