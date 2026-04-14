---
title: "Rally - Release Packaging Versioning System - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - README.md
  - pyproject.toml
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL_2026-04-13.md
  - ../doctrine/docs/VERSIONING.md
  - ../doctrine2/docs/LANGUAGE_VERSIONING_AND_BREAKING_CHANGE_POLICY_2026-04-13.md
  - src/rally/services/workspace.py
  - src/rally/services/flow_build.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
---

# TL;DR

Outcome

Rally will keep the packaged-runtime work that now makes external install work,
but it will reopen the release system until it matches Doctrine's public
conventions closely enough that the two repos feel like one family. The
operator-facing release flow, tag rules, changelog shape, version-policy doc,
signed-tag checks, GitHub draft-release flow, release helper commands, PR gate,
workflow hardening, and public trust surfaces will all line up with Doctrine's
live conventions where Rally has the same kind of surface. Rally will still
name its own real support-surface versions, such as workspace and
compiled-contract versions, instead of pretending it has a Doctrine-style
language version.

Problem

Rally's packaging and external-user runtime path are now in much better shape,
but the release system still feels like a different product than Doctrine.
Rally currently uses dynamic package versioning through `setuptools-scm`, a
tag-push GitHub Actions publish flow, a short custom `docs/VERSIONING.md`, and
a generic `CHANGELOG.md`. Doctrine uses explicit package versions in
`pyproject.toml`, fixed changelog and release-note shapes, signed annotated
tags, `git verify-tag`, repo-owned `make release-prepare|tag|draft|publish`
commands, and GitHub draft releases through `gh`. A user who knows Doctrine
should not need a second release mental model for Rally. The same mismatch now
shows up in GitHub repo hygiene too: Rally has no CODEOWNERS, no PR CI split,
no dependency-review or scorecards workflow, no documented security or support
surface, and only one tag-push publish workflow.

Approach

Keep the packaged built-in and external-install work that already landed, then
replace Rally's release and versioning layer with a repo-owned flow that
mirrors Doctrine's conventions. That means explicit package version truth in
`pyproject.toml`, a Doctrine-shaped `docs/VERSIONING.md`, a Doctrine-shaped
`CHANGELOG.md`, Rally-owned `release_flow` helpers and Make targets, signed tag
and pushed-tag checks, GitHub draft and publish commands through `gh`, and one
Rally-specific extension point for package artifacts and PyPI upload that stays
behind the same operator commands. It also means matching Doctrine's repo
governance where Rally has the same need: PR-first main protection, stable
required checks, pinned GitHub Actions, CODEOWNERS, Dependabot, dependency
review, CodeQL baseline, and public `SECURITY.md` and `SUPPORT.md` files.

Plan

Do this in six steps: keep the packaged-runtime foundation green, rewrite
Rally's version lines and public release docs to match Doctrine's shape, add a
repo-owned Doctrine-style Rally release helper stack and Make targets, harden
GitHub governance and PR CI, cut over the GitHub release and publish path, then
prove the full release and trust surface end to end.

Non-negotiables

- No source-checkout-only install story.
- No packaged runtime asset may live only outside the published distribution.
- No Rally-only release command family when Doctrine already has a strong
  public convention to copy.
- No dynamic Rally package-version truth if the goal is exact Doctrine-style
  operator parity.
- No free-form Rally changelog or version-policy shape that drifts from
  Doctrine's public release format.
- No tag-push-only GitHub Actions publish path as Rally's canonical public
  release flow.
- No unsigned or lightweight public Rally release tags.
- No unpinned third-party GitHub action in a required Rally workflow.
- No public Rally repo without CODEOWNERS, a PR template, and documented
  security and support paths once this plan lands.
- No Rally release without both the built-artifact external-user proof and the
  Doctrine-style release preflight proof.
- No Rally version field may be confused with a Doctrine language version.
- No vague Doctrine compatibility range in place of one explicit tested minimum
  Doctrine release version.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-14
Verdict (code): COMPLETE
Manual QA: pending (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit confirmed the full approved ordered frontier through Phase
  6 is now complete in repo code, GitHub workflow state, GitHub release state,
  and package-index state.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- Do one cold read of the rendered GitHub release page plus the PyPI and
  TestPyPI project pages now that the live release exists.
- Do one rendered GitHub README cold read so the badge row and docs map are
  checked in the public repo view.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-14
external_research_grounding: not needed
deep_dive_pass_2: done 2026-04-14
recommended_flow: deep dive -> deep dive again -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

If Rally ships exact Doctrine-convention parity at the release layer, then a
user who already knows Doctrine should be able to move to Rally and see the
same public release model:

- the same release-tag shapes
- the same signed annotated tag requirement
- the same `make release-prepare`, `make release-tag`, `make release-draft`,
  and `make release-publish` operator flow
- the same GitHub draft-release review step
- the same fixed changelog and release-note header shape
- the same package-version-to-tag discipline
- the same "public release version plus narrower support-surface versions"
  framing in `docs/VERSIONING.md`
- the same maintainer-first GitHub posture on shared repo surfaces:
  - protected `main`
  - PR-first merges
  - stable required checks
  - pinned required workflows
  - CODEOWNERS
  - public security/support docs

At the same time, a fresh external Rally user should still be able to install
from built artifacts, run `rally`, and use a host repo without cloning this
repo.

## 0.2 In scope

- One canonical Rally public release-version policy that mirrors Doctrine's
  operator conventions.
- One explicit Rally compatibility story for Doctrine that keeps Rally release
  versions separate from Doctrine release and language versions.
- One explicit minimum Doctrine release version that Rally declares in package
  metadata, docs, release notes, and external-user tests. The current floor
  for this plan is Doctrine `v1.0.1`.
- Keeping Doctrine-style explicit package version truth in `pyproject.toml`.
- Keeping a Rally-owned release helper stack that mirrors Doctrine's:
  `release-prepare`, `release-tag`, `release-draft`, and `release-publish`.
- Keeping a Rally `Makefile` that exposes the same release targets and adjacent
  operator commands Doctrine already uses.
- Adding one Rally-owned package-release metadata surface that mirrors
  Doctrine's package metadata pattern closely enough that workflow environment
  names, package-index URLs, and project import details do not drift.
- Adding one explicit operator pause before the first package-index publish so
  the maintainer can create the right TestPyPI and PyPI Trusted Publishers and
  matching GitHub environments with repo-owned instructions in hand.
- Keeping Rally GitHub governance settings aligned with Doctrine's
  maintainer-first defaults where Rally has the same surface:
  - ruleset-protected `main`
  - PR-required merges
  - strict status checks
  - linear history
  - squash-only merge policy
  - auto-merge
  - auto-delete merged head branches
  - zero required human approvals
- Keeping Rally repo-owned trust surfaces aligned with the Doctrine surfaces
  Rally already shares:
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - PR CI workflows with stable required job names
  - dependency review
  - scorecards
  - `SECURITY.md`
  - `SUPPORT.md`
- Rewriting `docs/VERSIONING.md` so its section order, version-line framing,
  release rules, changelog requirements, and signed-tag rules line up with
  Doctrine's structure.
- Keeping `CHANGELOG.md` on the same fixed Doctrine-style release header and
  payload shape that already landed, and fixing any last package-release wording
  drift in the same doc sweep.
- Defining Rally's narrow support-surface version lines clearly:
  `[tool.rally.workspace].version` and compiled agent `contract_version`.
- Keeping Rally's canonical public release flow on the Doctrine-style GitHub
  draft-and-publish process through `gh`, not a tag-push-only GitHub Actions
  path.
- Keeping the release-published build-and-publish workflow so GitHub release
  publication, attached assets, smoke proof, and PyPI upload follow the same
  hardened repo story Doctrine uses.
- Keeping the packaged built-ins, external-user install path, and host-repo
  proof that already landed.
- External-user proof that runs from built artifacts in a clean temp
  environment and exercises the same path a real user would take.
- Test and CI changes needed to keep release metadata, package artifacts,
  release-helper behavior, and external-user setup honest.

Allowed architectural convergence scope:

- keeping the packaged built-in and runtime cutover work already done
- keeping explicit package-version truth and the landed Rally release helper
  stack
- adding repo-owned package metadata and package-proof commands that mirror
  Doctrine's remaining release structure
- deleting or reducing duplicated workflow settings that conflict with the
  Doctrine-style repo-owned metadata model
- tightening the first-release package-index setup docs so the repo tells the
  operator exactly when to stop and what to configure
- tightening docs, changelog, GitHub release flow, and proof commands so Rally
  and Doctrine read as one family

## 0.3 Out of scope

- Changing Doctrine's release system. Rally must adapt to Doctrine's live
  conventions, not ask Doctrine to bend back toward Rally's older shortcuts.
- Inventing a fake Rally "language version" just to match Doctrine wording.
- Copying Doctrine-only hardening items that do not fit Rally, such as a VS
  Code lane, a package rename, or merge queue policy.
- A GUI release dashboard, hosted control plane, or custom package registry.
- Long-tail compatibility shims for old source-tree-only usage.
- Supporting every historical local repo layout forever.
- Broad new product features unrelated to release, packaging, versioning, or
  external-user setup.

## 0.4 Definition of done (acceptance evidence)

- A built Rally wheel and sdist contain every runtime-owned asset needed by an
  installed Rally runtime.
- A clean temp environment can install Rally from the built artifact and run
  `rally --help` and `rally run demo` without the Rally source repo present.
- A clean temp host repo can follow one short documented setup flow and reach a
  real compile or run proof through the installed Rally package.
- A clean temp host repo can run a Doctrine emit target that uses Rally-owned
  stdlib support files without any schema or example file escaping the host
  project root or tripping Doctrine `E519`.
- Rally has a `Makefile` with the same public release target names Doctrine
  uses.
- Rally has a repo-owned `release_flow` helper stack with the same command
  family Doctrine uses and comparable preflight checks.
- Rally public releases use signed annotated tags only, and Rally release
  tooling checks `git verify-tag` and pushed-tag truth before GitHub draft or
  publish steps.
- Rally's `docs/VERSIONING.md` has the same section shape and operator guidance
  pattern Doctrine uses, while accurately naming Rally's real version lines.
- Rally's `CHANGELOG.md` has Doctrine-style release sections with fixed release
  header fields.
- Rally's public package version is explicit in `pyproject.toml` and must match
  the requested release tag's package-version mapping.
- Rally's GitHub release flow uses the same draft-review-publish shape Doctrine
  uses.
- Rally's main branch is guarded by repo rules, and Rally's required checks are
  stable, split, and pinned.
- Rally publishes `SECURITY.md` and `SUPPORT.md` that read like a maintained
  1.x project.
- Rally has CODEOWNERS, a structured PR template, Dependabot updates, and
  dependency review.
- Rally's package artifact upload and PyPI publish happen behind that same
  operator flow instead of a separate tag-push-only release path.
- Rally has a repo-owned package metadata helper and `publish.yml` reads its
  package-index environment names and URLs from that helper instead of
  duplicating them in YAML.
- Rally has a Doctrine-style `make verify-package` front door that proves the
  built package from a clean temp environment before public release.
- `docs/VERSIONING.md` includes an explicit stop point before the first public
  index release and gives the operator the exact TestPyPI and PyPI setup steps
  Rally needs, matching Doctrine's release discipline.

Behavior-preservation evidence:

- current repo-local workspace behavior still works after the release-system
  cutover
- existing unit coverage for workspace, flow build, flow load, and runner paths
  stays green
- the packaged-install test keeps proving the built runtime path without
  needing a source checkout
- new release-flow tests prove tag, changelog, package-version, and GitHub
  draft/publish rules

## 0.5 Key invariants (fix immediately if violated)

- No source-checkout dependency in the installed runtime path.
- No runtime-owned asset exists only outside the published distribution.
- No dual source of truth for the Rally public release version.
- No Rally version field stands in for a Doctrine language version.
- No Rally release flow deviates from Doctrine's public operator conventions
  without a written Rally-specific reason tied to a real Rally-only surface.
- No open-ended Doctrine dependency story where Rally really needs one explicit
  minimum tested Doctrine release.
- No second release checklist outside the canonical docs and repo commands.
- No tag-push-only GitHub Actions path remains Rally's canonical public release
  flow.
- No unsigned or lightweight public release tag.
- No protected Rally main branch that still allows direct drift around CI.
- No required Rally workflow should depend on mutable action tags alone.
- No host-repo emit target or emitted contract may point a support file at
  `../rally/...` or any other path outside the host project root.
- No release without external-user proof from the built artifact.
- No silent breaking change in packaging, install, release, or upgrade
  behavior.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Doctrine users should see the same release mental model when they use Rally.
2. The packaged-runtime and external-user proof that already landed must stay
   green during the release-system rewrite.
3. Rally's packaging, versioning, changelog, README, and release docs should
   read like the Rally half of one shared Doctrine-plus-Rally product story.
4. Doctrine users should also see the same repo-governance posture where the
   surface is shared: PR-first main protection, stable required checks, pinned
   workflows, CODEOWNERS, and public security docs.
5. Rally's public release version and Rally's narrow support-surface versions
   must be easy to tell apart from Doctrine's release and language versions.
6. Signed-tag, changelog, GitHub draft, publish, and PyPI transport rules must
   fail loud before a bad release can ship.
7. Rally must keep one explicit minimum tested Doctrine release version.
8. Release truth, tag truth, docs truth, changelog truth, artifact truth, and
   required-check truth must stay aligned.
9. The proof path must still look like a real user flow, not just unit mocks.

## 1.2 Constraints

- Rally's packaged built-ins, workspace-only runtime path, and external-user
  artifact proof are already in flight and must not be backed out.
- Rally already has explicit `[project].version`, a `Makefile`, a release
  helper stack, split PR checks, and public trust docs. This work must not
  regress those Doctrine-style surfaces.
- Rally's `.github/workflows/publish.yml` already follows Doctrine's broad
  `release.published` plus `workflow_dispatch` topology, but it still keeps
  package-index environment names and URLs in YAML instead of repo-owned
  metadata.
- Rally still lacks Doctrine's separate package metadata helper and
  `make verify-package` front door.
- Rally does have real narrow support-surface versions today:
  `[tool.rally.workspace].version = 1` and compiled agent `contract_version = 1`.
- Doctrine's live policy direction separates public release version, language
  version, and narrow support-surface versions. Rally must copy that structure
  without inventing a fake language version.
- Rally still needs one exact minimum Doctrine public release floor. The
  current anchor is `v1.0.1`.

## 1.3 Architectural principles (rules we will enforce)

- Treat Rally as an installable product first.
- Ship every runtime-owned asset inside the published distribution.
- Use one source of truth for the Rally public release version.
- Keep Rally release versioning separate from Doctrine release and language
  versioning.
- Declare one explicit minimum Doctrine release dependency and test against it.
- Prefer Doctrine's public release conventions over fresh Rally-only release
  invention.
- Keep operator-facing release commands and release-file shapes aligned with
  Doctrine unless Rally has a real surface difference to document.
- Keep GitHub governance, CI naming, and trust surfaces aligned with Doctrine's
  maintainer-first hardening direction where Rally has the same class of repo
  surface.
- Prove packaging through built artifacts, not only editable installs.
- Fail loud on unsupported version, tag, changelog, signing, or asset states.

## 1.4 Known tradeoffs (explicit)

- Adding a Rally package metadata helper adds one more owned release file, but
  it removes duplicated package-index settings from workflow YAML and matches
  Doctrine's pattern.
- Adding a separate `make verify-package` command adds one more operator entry
  point, but it makes built-package proof discoverable and keeps Rally's public
  release surface closer to Doctrine's.
- Making the first package-index publish pause for TestPyPI and PyPI setup adds
  one manual step, but that setup already exists in the real world and should
  be made explicit instead of living in operator memory.
- Rally will still need one or two Rally-specific release-note fields for real
  Rally support surfaces, but those should fit inside Doctrine's broader
  release structure instead of becoming a second format.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally is already a real `src/rally/` runtime package with packaged built-ins,
  a working installed CLI, and a credible external-user artifact proof.
- Rally already declares `doctrine>=1.0.1,<2` and proves that floor through the
  packaged-install test.
- Rally already has explicit package-version truth in `pyproject.toml`, a
  Doctrine-style `Makefile`, `src/rally/release_flow.py`,
  `src/rally/_release_flow/**`, split PR checks, public trust docs, and a
  Doctrine-shaped `publish.yml`.
- Doctrine already has those same broad release surfaces, plus one extra
  package-release metadata layer in `doctrine/_package_release.py` and
  `[tool.doctrine.package]`, plus a first-class `make verify-package` proof
  command.
- Doctrine's `docs/VERSIONING.md` also includes one operator move Rally still
  does not spell out yet: before the first real package-index release, stop and
  register GitHub Trusted Publishers on TestPyPI and PyPI for the
  `.github/workflows/publish.yml` workflow and matching environments.

## 2.2 What's broken / missing (concrete)

- This plan doc is stale. Its later sections still say major parity work is
  missing even though that work already landed in Rally.
- Rally still has no Rally-owned package-release metadata helper or
  `[tool.rally.package]` equivalent.
- Rally's `publish.yml` still duplicates package-index environment names and
  the TestPyPI URL instead of reading those settings from repo-owned metadata.
- Rally still has no Doctrine-style `make verify-package` front door that
  proves the built package from a clean temp environment.
- Rally's docs still do not include the explicit pause and step-by-step setup
  for the first TestPyPI and PyPI publish, so the first real index release
  would still depend on operator memory.

## 2.3 Constraints implied by the problem

- The fix now has to preserve the Doctrine-style release stack already on
  `main`, not reopen work that is already done.
- The remaining truth must live in repo-owned metadata, helper code, docs, and
  workflows. Do not add a second anti-drift harness just to keep duplicated
  settings aligned.
- The final Rally story should feel like a Doctrine extension, not a sibling
  product with a different release grammar.
- The docs must pause at the right moment and tell the operator how to create
  the TestPyPI and PyPI publishers and GitHub environments, because that part
  is a human setup step, not repo code.
- The plan must preserve the packaged-runtime and external-user proof that
  already landed.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal "ground truth")

## 3.1 External anchors (papers, systems, prior art)

- Doctrine is still the primary convention anchor for this plan.
- This refresh reviewed the full Python source and test tree under
  `../doctrine/doctrine` and `../doctrine/tests` so the release conventions
  were read in the context of Doctrine's full repo style, not as isolated
  snippets.
- The direct parity anchors for Rally are the stable Doctrine repo surfaces
  that define public release and repo rules today:
  - `pyproject.toml`
  - `Makefile`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `SUPPORT.md`
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/publish.yml`
  - `doctrine/release_flow.py`
  - `doctrine/_release_flow/**`
  - `doctrine/_package_release.py`
  - `tests/test_release_flow.py`
  - `tests/test_package_release.py`
- The most important live Doctrine conventions for the remaining Rally work are
  now clear:
  - public package version is explicit in `[project].version`
  - package-release metadata lives in repo config and is read through a helper
    module instead of being duplicated in workflow YAML
  - `make build-dist` and `make verify-package` are first-class operator proof
    commands beside `make release-*`
  - `publish.yml` supports `workflow_dispatch` with
    `publish_target=none|testpypi|pypi`
  - `publish.yml` reads package-index environment names and project URLs from
    metadata emitted by `python -m doctrine._package_release metadata`
  - `docs/VERSIONING.md` tells the maintainer to stop before the first real
    index publish and create GitHub Trusted Publishers on both TestPyPI and
    PyPI for `.github/workflows/publish.yml` and the matching environments
- Standard Python packaging rules still matter where Doctrine uses them:
  - PEP 440 defines the package-version mapping from public tags
  - Trusted Publishing with OIDC is the package-index publish path
  - `gh release create --draft --verify-tag --generate-notes`,
    `gh release edit --draft=false`, `gh workflow run`, and
    `gh run watch --exit-status` are the live operator commands behind the
    release flow
- Doctrine's GitHub hardening posture is also part of the parity target where
  Rally has the same repo surface:
  - ruleset-protected `main`
  - split PR workflows with stable required job names
  - pinned actions
  - least-privilege workflow permissions
  - CODEOWNERS
  - dependency review
  - scorecards
  - private vulnerability reporting
  - automated security fixes
- Doctrine's broader version-policy split still matters. Rally should mirror
  the framing for public release version plus narrower support-surface versions,
  but it should keep using Rally's real support lines instead of inventing a
  fake language version.

## 3.2 Internal ground truth (code as spec)

- Rally's current code and docs on 2026-04-14 already show that most of the
  broad parity plan landed:
  - `pyproject.toml` already has explicit `version = "0.1.0"` and
    `doctrine>=1.0.1,<2`
  - `Makefile` already exposes `setup`, `tests`, `verify`,
    `release-prepare`, `release-tag`, `release-draft`, and
    `release-publish`
  - `src/rally/release_flow.py` and `src/rally/_release_flow/**` already exist
  - `tests/unit/test_release_flow.py` already exists
  - `.github/workflows/pr.yml`, `dependency-review.yml`, `scorecards.yml`, and
    `publish.yml` already exist
  - `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`,
    `.github/dependabot.yml`, `SECURITY.md`, and `SUPPORT.md` already exist
  - `tests/integration/test_packaged_install.py` still proves the installed
    `rally` front door and host-repo flow from built artifacts
- The remaining Rally-vs-Doctrine drift is now concentrated in a smaller set of
  files:
  - `pyproject.toml` has no `[tool.rally.package]` metadata block yet
  - there is no Rally helper that matches Doctrine's
    `python -m doctrine._package_release metadata` bridge into GitHub Actions
  - `Makefile` has `verify`, but not Doctrine's separate `build-dist` and
    `verify-package` front doors
  - `.github/workflows/publish.yml` hard-codes `testpypi`, `pypi`, and the
    TestPyPI legacy URL instead of loading package-index settings from
    repo-owned metadata
  - `docs/VERSIONING.md` does not yet stop the operator and give the exact
    first-release package-index setup instructions the way Doctrine does
- Canonical owner paths that should stay true:
  - `pyproject.toml` owns Rally package metadata, dependency floors, console
    entry points, and workspace version truth
  - `docs/VERSIONING.md` owns Rally public release policy and support-surface
    version framing
  - `CHANGELOG.md` owns portable release history
  - `src/rally/release_flow.py` and `src/rally/_release_flow/**` own release
    helper behavior
  - one new Rally package-release helper should own package metadata export for
    workflows instead of duplicating that data in YAML
- Existing patterns to keep:
  - Rally's packaged-runtime proof and workspace-only runtime path stay in
    place as the foundation
  - Doctrine's `Makefile`, `release_flow.py`, `_release_flow/*`,
    `_package_release.py`, `tests/test_release_flow.py`, and
    `tests/test_package_release.py` are the direct parity template for the
    remaining work
  - Doctrine's `publish.yml` metadata job is the direct template for removing
    duplicate environment and URL truth from Rally's workflow
- Duplicate or drifting paths that still matter:
  - Rally package-index settings live only in `publish.yml`, while Doctrine
    keeps that truth in repo metadata plus a helper bridge
  - Rally uses one broad `make verify`, while Doctrine also exposes package-only
    proof through `make verify-package`
  - Rally's first package-index setup steps are still implicit, while Doctrine
    documents them in `docs/VERSIONING.md`
  - at research time, this plan artifact still carried the older Rally state in
    Section 7 and needed a later phase-plan refresh before deeper planning
    could be trusted
- Behavior-preservation signals already available:
  - `uv run pytest tests/unit -q` protects core Rally behavior
  - `uv build` plus `tests/integration/test_packaged_install.py` protect the
    built-artifact path
  - `tests/unit/test_release_flow.py` already protects the landed release flow
  - Doctrine's `tests/test_package_release.py` gives a concrete template for
    the missing package-metadata and package-proof coverage

## 3.3 Decision gaps that must be resolved before implementation

- There is no unresolved direction question left at research level.
- The user already resolved the key remaining product decision:
  this plan must include an explicit later pause where Rally tells the operator
  exactly how to set up TestPyPI and PyPI for this project, the same way
  Doctrine does.
- At research time, the remaining planning work was to narrow the doc onto one
  concrete implementation frontier, not reopen the broad parity direction:
  - add Rally-owned package-release metadata and a helper bridge for workflows
  - add a Doctrine-style `build-dist` and `verify-package` package proof path
  - move `publish.yml` package-index settings to repo-owned metadata
  - make the first package-index setup step explicit in `docs/VERSIONING.md`
  - remove any small remaining drift between Rally's live repo surfaces and
    Doctrine's release conventions
- That deep-dive and phase-plan refresh is now complete. The remaining work is
  implementation, not another architecture choice.
<!-- arch_skill:block:research_grounding:end -->

> 2026-04-14 research refresh note:
> At research time, Section 7 still reflected older repo truth.
> The phase-plan refresh on 2026-04-14 replaced it with the smaller remaining
> package-release frontier.

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Rally already has the broad Doctrine-style release surface in repo:
  - `pyproject.toml` owns `[project].version`, the Doctrine dependency floor,
    the console entry point, and `[tool.rally.workspace].version`
  - `Makefile` owns `setup`, `tests`, `verify`, `release-prepare`,
    `release-tag`, `release-draft`, and `release-publish`
  - `src/rally/release_flow.py` and `src/rally/_release_flow/**` own the
    release prepare, tag, draft, and publish flow
  - `tests/unit/test_release_flow.py` covers the release helper stack
  - `.github/workflows/pr.yml`, `dependency-review.yml`, `scorecards.yml`, and
    `publish.yml` already exist
  - `README.md`, `CONTRIBUTING.md`, `docs/VERSIONING.md`, `CHANGELOG.md`,
    `SECURITY.md`, and `SUPPORT.md` already expose the public release and trust
    surfaces
- Rally already has the packaged-runtime base that makes installed use real:
  - `src/rally/_bundled/**` ships built-ins inside the package
  - `tools/sync_bundled_assets.py` owns bundle sync and drift checks
  - `tests/integration/test_packaged_install.py` proves the installed artifact
    path from a clean temp environment
- The remaining package-publish owner path is still split:
  - `[project].version` lives in `pyproject.toml`
  - publish environment names still live only in
    `.github/workflows/publish.yml`
  - there is no `[tool.rally.package]` table in `pyproject.toml`
  - there is no `src/rally/_package_release.py` helper module
  - there is no `tests/unit/test_package_release.py`
- Package proof is also split:
  - `make verify` runs `uv build` and the wheel-only
    `tests/integration/test_packaged_install.py`
  - `publish.yml` rebuilds artifacts and reruns that wheel proof
  - there is no package-only unit suite for package metadata export
  - there is no Doctrine-style `build-dist` command
  - there is no Doctrine-style `verify-package` front door
  - there is no sdist smoke proof outside the repo root

## 4.2 Control paths (runtime)

1. The operator updates `pyproject.toml`, `docs/VERSIONING.md`,
   `CHANGELOG.md`, and any touched public docs.
2. `make release-prepare` runs `python -m rally.release_flow prepare`.
   - `src/rally/_release_flow/parsing.py` reads package version truth from
     `[project].version`
   - the same parser reads support-surface truth from
     `docs/VERSIONING.md`, `pyproject.toml`, and
     `src/rally/services/flow_loader.py`
   - `src/rally/_release_flow/ops.py` renders one release worksheet with fixed
     verify commands
3. `make release-tag`, `make release-draft`, and `make release-publish` own
   tag signing, GitHub draft creation, and GitHub release publication.
4. `make verify` is Rally's current broad proof front door.
   - it checks bundled assets
   - it runs `tests/unit/test_release_flow.py`
   - it runs the full `tests/unit` suite
   - it builds dist artifacts
   - it runs the wheel-only packaged-install regression
   - it does not separate package-only smoke from Rally's richer host-workspace
     proof
5. `.github/workflows/publish.yml` runs on `release.published` and on
   `workflow_dispatch`.
   - the build job checks out Rally and the Doctrine floor, syncs dev deps,
     checks bundled assets, runs unit tests, builds the dist artifacts, runs
     the packaged-install proof, and stores the artifacts
   - `publish-testpypi` still hard-codes `environment: testpypi`
   - `publish-pypi` still hard-codes `environment: pypi`
   - there is no metadata job that exports package publish settings from
     repo-owned metadata into workflow outputs
6. `docs/VERSIONING.md` documents the repo-owned release flow, but its final
   publish step still ends with "when the repo settings are ready" instead of a
   real first-publish setup pause with exact TestPyPI and PyPI steps.

## 4.3 Object model + key abstractions

- Rally already has repo-owned release models:
  - `ReleaseTag`
  - `ReleasePlan`
  - `ReleaseEntry`
- Rally already models its real narrow support-surface versions:
  - workspace manifest version from `[tool.rally.workspace].version`
  - compiled contract version from
    `SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS`
- Rally does not yet have a first-class package-release abstraction for:
  - publish import name
  - TestPyPI environment name
  - PyPI environment name
  - derived package project URLs
  - wheel and sdist artifact resolution
  - package smoke commands outside the repo root
- That missing abstraction leaves package publish truth split across:
  - `pyproject.toml` for distribution name and version
  - `.github/workflows/publish.yml` for environment names
  - `tests/integration/test_packaged_install.py` for wheel smoke logic
  - `docs/VERSIONING.md` for a vague first-publish setup note

## 4.4 Observability + failure behavior today

- Release tag, changelog, and package-version drift already fail loud through
  the current `release_flow` helper stack.
- Bundled-asset drift and the wheel-host packaged install path already fail
  loud through `make verify` and `publish.yml`.
- Package publish metadata drift still fails late:
  - if workflow environment names ever change, the truth lives in workflow YAML
    instead of repo metadata
  - the first missing Trusted Publisher or GitHub environment setup will only
    show up when a real publish job runs
  - there is no repo-owned metadata command that can print or validate those
    package publish settings before GitHub Actions starts
- Sdist regressions still fail late because Rally does not yet smoke test the
  sdist outside the repo root.
- Package smoke and Rally-runtime smoke are not separated yet, so maintainers
  cannot ask one small question such as "does the sdist install cleanly outside
  the repo root?" without running the broader Rally regression.
- The docs still hide part of the real release path behind "repo settings are
  ready," so operator setup failure is still partially tribal knowledge.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Keep the packaged-runtime foundation that already works:
  - `src/rally/_bundled/**`
  - `tools/sync_bundled_assets.py`
  - `tests/integration/test_packaged_install.py`
- Keep the current Doctrine-style Rally release helper stack:
  - `Makefile`
  - `src/rally/release_flow.py`
  - `src/rally/_release_flow/common.py`
  - `src/rally/_release_flow/models.py`
  - `src/rally/_release_flow/parsing.py`
  - `src/rally/_release_flow/tags.py`
  - `src/rally/_release_flow/ops.py`
  - `tests/unit/test_release_flow.py`
- Add one package-release owner path that mirrors Doctrine's remaining pattern:
  - `pyproject.toml` with new `[tool.rally.package]`
  - `src/rally/_package_release.py`
  - `tests/unit/test_package_release.py`
- Extend the current operator surface instead of inventing a second one:
  - `Makefile` adds `build-dist`, `verify-package-wheel`,
    `verify-package-sdist`, and `verify-package`
  - `.github/workflows/publish.yml` adds a metadata job and reads package
    publish settings from repo metadata
- Rewrite the release docs that still carry the last package-publish drift:
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `CONTRIBUTING.md`
- Keep the already-landed GitHub trust surfaces in place. This deep-dive pass
  does not reopen CODEOWNERS, PR workflow, dependency review, scorecards,
  security, or support ownership.

## 5.2 Control paths (future)

1. `pyproject.toml` becomes the single repo-owned source for Rally package
   metadata.
   - `[project].name` stays the distribution name
   - `[project].version` stays the package version truth
   - `[tool.rally.package]` owns `import_name`, `pypi_environment`, and
     `testpypi_environment`
2. `src/rally/_package_release.py` becomes the package publish bridge.
   - `python -m rally._package_release metadata --format github-output` writes
     the package metadata and derived project URLs for GitHub Actions
   - `python -m rally._package_release smoke --artifact-type wheel|sdist`
     installs one built artifact outside the repo root and proves the installed
     package path
3. `make release-prepare` keeps the current Rally release flow, but its
   worksheet now points at the package-release proof front door and the
   first-publish setup step.
   - release version, changelog, workspace version, compiled contract version,
     and Doctrine floor still stay under `release_flow`
   - package version lookup inside `release_flow` now delegates to the
     package-release helper instead of re-parsing package truth on its own
4. `make build-dist` becomes the explicit dist-build command.
5. `make verify-package` becomes the explicit package proof command.
   - it builds the wheel and sdist
   - it smoke tests both artifact types outside the repo root
   - it is the Doctrine-style package smoke front door, not the whole Rally
     runtime regression
6. `make verify` stays Rally's broad umbrella proof.
   - it keeps bundled-assets drift checks
   - it adds `tests/unit/test_package_release.py`
   - it calls `make verify-package`
   - it keeps the full unit suite
   - it keeps the richer packaged-install regression that proves the host-repo
     path from the built artifact
7. `.github/workflows/publish.yml` keeps the current release-owned topology,
   but not the current duplicated settings.
   - a new metadata job checks out the requested ref and runs
     `python -m rally._package_release metadata --format github-output`
   - the build job uses the same ref, runs Rally's umbrella proof so bundled
     assets, unit tests, Doctrine-style package smoke, and the richer
     packaged-install regression all stay covered, then uploads the built
     artifacts
   - the publish jobs read their environment names and project URLs from the
     metadata job outputs
   - the TestPyPI upload endpoint may stay literal in YAML, matching Doctrine's
     current workflow
8. `docs/VERSIONING.md` becomes explicit about the first real package-index
   publish.
   - before the first TestPyPI or PyPI release, the operator stops
   - the doc gives the exact steps to create GitHub Trusted Publishers on
     TestPyPI and PyPI for `.github/workflows/publish.yml`
   - the doc gives the exact steps to create the matching GitHub environments
   - this is the point where implementation must pause and hand the user the
     Rally-specific setup steps
9. The public release command family stays the same as Doctrine's:
   `release-prepare`, `release-tag`, `release-draft`, `release-publish`
10. The one intentional Rally-vs-Doctrine difference stays narrow and explicit:
    Rally has no `LANGUAGE_VERSION=` input because Rally has no Doctrine-style
    language version line.

## 5.3 Object model + abstractions (future)

- `ReleaseTag`, `ReleasePlan`, and `ReleaseEntry` stay in
  `src/rally/_release_flow/**` and keep owning tag parsing, worksheet logic,
  changelog validation, and GitHub release commands.
- `PackageReleaseMetadata` becomes the new package publish abstraction in
  `src/rally/_package_release.py`.
  - distribution name comes from `[project].name`
  - version comes from `[project].version`
  - import name comes from `[tool.rally.package].import_name`
  - package-index environment names come from `[tool.rally.package]`
  - project URLs are derived from the distribution name
- `src/rally/_package_release.py` also owns:
  - dist artifact resolution for wheel and sdist
  - GitHub output writing for workflow metadata
  - package smoke commands outside the repo root
- `Makefile` owns the split between package-only proof and Rally-runtime proof.
  - `verify-package` asks "do the wheel and sdist install and run outside the
    repo root?"
  - `verify` asks the broader Rally question that also covers bundled assets,
    unit coverage, and the host-workspace runtime path
- `src/rally/_release_flow/parsing.py` should treat the package helper as the
  package metadata authority instead of reading `[project].version` directly on
  its own.
- `tests/integration/test_packaged_install.py` remains the richer Rally
  regression anchor for the host-workspace path even after the package helper
  lands. Rally's package smoke must not water that proof down to a generic
  import-only check.

## 5.4 Invariants and boundaries

- Public release version truth lives in explicit `[project].version`.
- Package publish metadata truth lives in `[tool.rally.package]`.
- Public release tags are signed annotated tags only.
- GitHub release publication only happens from a verified pushed public tag.
- Rally's public release doc and changelog keep the same section shape and
  release header discipline Doctrine uses.
- Rally does not invent a fake language-version line.
- Rally documents the real support-surface versions it already has:
  workspace manifest version and compiled contract version.
- `publish.yml` may not hard-code package publish environment names once the
  helper exists.
- `make verify-package` must smoke both wheel and sdist artifacts outside the
  repo root.
- Rally's richer host-workspace proof from the built artifact stays a release
  gate even after `verify-package` lands.
- `publish.yml` must keep both proof layers: Doctrine-style package smoke and
  Rally's richer host-workspace regression.
- The first real package-index publish must stop for explicit TestPyPI and PyPI
  setup. No "repo settings are ready" hand-wave remains in the final docs.
- Rally copies Doctrine's workflow topology and docs routing pattern, but not
  Doctrine-only language-version or package-name surfaces.
- The explicit Doctrine floor stays a release gate.
- The canonical public release path is repo-owned and operator-driven, not tag
  push driven through GitHub Actions.
- No new anti-drift harness or second config file should exist just to keep the
  package publish settings in sync.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- Operator-facing release flow:

```text
make release-prepare ...  -> worksheet + package-proof commands + first-publish stop point
make build-dist           -> wheel + sdist
make verify-package       -> wheel smoke + sdist smoke outside repo root
make verify               -> bundled-assets + unit + verify-package + richer wheel-host regression
make release-tag ...      -> signed annotated tag + push
make release-draft ...    -> verified GitHub draft release
review draft release
make release-publish ...  -> publish GitHub release
publish.yml metadata      -> load package publish settings from repo metadata
publish.yml build         -> make verify + attach assets
first real index publish  -> pause and set up TestPyPI / PyPI publishers
publish.yml publish       -> approve environment and publish
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Package publish metadata | `pyproject.toml` | `[tool.rally.package]` (new) | `[project].version` exists, but package publish settings live only in workflow YAML | Add `[tool.rally.package]` with `import_name`, `pypi_environment`, and `testpypi_environment` | Make package publish settings repo-owned and helper-readable | `pyproject.toml` becomes the only package publish metadata source outside derived URLs | `tests/unit/test_package_release.py`, `tests/unit/test_release_flow.py` |
| Package metadata helper | `src/rally/_package_release.py` | new module and CLI | No Rally helper owns package metadata export, artifact resolution, or package smoke | Add `PackageReleaseMetadata`, metadata export, GitHub output writing, and wheel or sdist smoke commands | Mirror Doctrine's remaining package-release pattern without a second config surface | `python -m rally._package_release metadata|smoke` owns package publish bridge behavior | `tests/unit/test_package_release.py` |
| Release-flow package parsing | `src/rally/_release_flow/parsing.py` | `load_package_metadata_version` | Reads `[project].version` directly and knows nothing about package publish metadata | Delegate package version lookup to the package helper and keep release errors wrapped in Rally's release error surface | Remove duplicate parsing and keep one package metadata owner path | `release_flow` reads package metadata through `rally._package_release` | `tests/unit/test_release_flow.py` |
| Release worksheet | `src/rally/_release_flow/ops.py` | `render_release_worksheet` | Prints a proof list built around `uv build` and the wheel-only packaged-install test | Update the worksheet to point at `build-dist`, `verify-package`, package-release unit tests, the richer Rally regression, and the first-publish setup stop point | The worksheet should teach the same operator flow the docs teach | Worksheet becomes the fixed release-proof and first-publish reminder surface | `tests/unit/test_release_flow.py` |
| Operator command surface | `Makefile` | `verify`, `build-dist`, `verify-package-wheel`, `verify-package-sdist`, `verify-package` | `verify` exists, but there is no package-only front door and no clean split between package smoke and Rally-runtime smoke | Add the Doctrine-style package proof commands and redefine `verify` as the broader umbrella that includes them | Give Rally the same package command family Doctrine users expect without dropping the richer runtime proof | `make verify-package` becomes the explicit package proof path and `make verify` stays the broader Rally release proof | local make proof, `tests/unit/test_release_flow.py` |
| Wheel-host regression | `tests/integration/test_packaged_install.py` | `PackagedInstallTests` | Proves the built wheel and host-repo path, but only through a standalone integration test | Keep this proof as Rally's richer regression anchor and align the package command surface around it or shared helper code | Rally's real runtime path is broader than a generic import smoke | The wheel-host path stays a required built-artifact regression | `tests/integration/test_packaged_install.py` |
| Package-release unit coverage | `tests/unit/test_package_release.py` | new test module | Rally has no unit contract for package metadata and GitHub output behavior | Add tests for metadata loading, required fields, artifact resolution, and GitHub outputs | Catch package metadata drift before GitHub Actions does | `tests/unit/test_package_release.py` becomes the package metadata contract suite | `tests/unit/test_package_release.py` |
| Publish transport workflow | `.github/workflows/publish.yml` | `metadata`, `build`, `publish-testpypi`, `publish-pypi` | Workflow topology is broadly right, but environment names are hard-coded and there is no metadata job | Add a metadata job, feed publish environment names and URLs from helper outputs, and run Rally's umbrella proof in the build job so package smoke and the richer runtime regression both stay covered | Remove duplicated publish settings and mirror Doctrine's metadata-driven workflow shape without weakening Rally's release proof | Workflow reads repo-owned metadata instead of hard-coded env-name truth and still proves the full built-artifact path | workflow dry run on `main` |
| Versioning doc | `docs/VERSIONING.md` | `Release Process`, package proof lines, first-publish step | Explains the release flow, but still ends with "when repo settings are ready" and omits package-release proof commands | Add the package metadata surface, add `build-dist` and `verify-package`, and add the exact first-publish setup steps for TestPyPI, PyPI, and GitHub environments | This is where the operator needs the explicit pause and instructions | `docs/VERSIONING.md` becomes the human source of truth for first package-index publish setup | doc review, `tests/unit/test_release_flow.py` if worksheet text changes |
| Contributor docs | `README.md`, `CONTRIBUTING.md` | release and package proof instructions | Surface `make release-*`, but not the package proof front door or the first-publish setup pointer | Add `build-dist` and `verify-package` where they belong and route first-publish setup to `docs/VERSIONING.md` | Keep operator docs aligned without duplicating the full setup checklist | README and contributing docs become pointers, not a second package publish checklist | manual doc review |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - package release metadata should live in `pyproject.toml` plus
    `src/rally/_package_release.py`
  - public release orchestration should stay in `Makefile`,
    `src/rally/release_flow.py`, and `src/rally/_release_flow/**`
  - `publish.yml` should stay the publish transport, not the source of package
    publish metadata truth
  - `docs/VERSIONING.md` should stay the one human-owned first-publish setup
    checklist
- Deprecated flows:
  - hard-coded package publish environment names in `publish.yml`
  - release docs that end the publish path with "when repo settings are ready"
  - package proof instructions that bypass a repo-owned `verify-package`
    command
- Delete list:
  - duplicated package publish environment-name truth in workflow YAML
  - vague first-publish wording that leaves TestPyPI and PyPI setup outside the
    repo
  - any package-proof instructions that tell operators to hand-compose the
    build and smoke sequence instead of using `build-dist` or `verify-package`
- Capability-replacing harnesses to delete or justify:
  - none; this plan is not agent-behavior work
- Live docs/comments/instructions to update or delete:
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `CONTRIBUTING.md`
  - `Makefile` help text
  - `src/rally/release_flow.py` help text if package proof commands are named
  - `.github/workflows/publish.yml`
- Behavior-preservation signals for refactors:
  - `uv run pytest tests/unit -q`
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - `uv run pytest tests/unit/test_package_release.py -q`
  - `make verify-package`
  - `make verify`
  - one `workflow_dispatch` publish dry run with `publish_target=none`

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Package publish metadata | `pyproject.toml`, `src/rally/_package_release.py`, `src/rally/_release_flow/parsing.py`, `.github/workflows/publish.yml` | one helper-backed package metadata source | Prevents workflow, release-flow, and docs drift around package publish settings | include |
| Package proof commands | `Makefile`, `docs/VERSIONING.md`, `README.md`, `CONTRIBUTING.md`, `.github/workflows/publish.yml` | `build-dist` plus `verify-package` as the package proof front door, with `verify` as the broader Rally proof | Prevents hand-written proof drift and keeps Rally aligned with Doctrine's command surface without losing Rally-specific runtime coverage | include |
| Rally-specific host-workspace proof | `tests/integration/test_packaged_install.py`, `make verify`, release worksheet, `.github/workflows/publish.yml` | keep the richer built-artifact host-repo proof even after package helper work lands | Prevents Doctrine-style package smoke from under-covering Rally's real runtime path | include |
| New required PR lane for package proof | `.github/workflows/pr.yml` | separate `verify-package` required check | Current `unit` and `packaged-install` surfaces already cover the code path, and adding a new required lane would widen the operator surface without a repo-grounded need | exclude |
| First-publish setup outside `docs/VERSIONING.md` | ad hoc notes, scripts, or hidden checklists | out-of-band setup instructions | Would create a second truth surface for a human step that should live in one canonical doc | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Keep the packaged-runtime foundation green

Status: COMPLETED

* Goal:
  Preserve the built-artifact install path and workspace-only runtime behavior
  while the release system is reopened.
* Work:
  - Keep `src/rally/_bundled/**`, `tools/sync_bundled_assets.py`, and
    `src/rally/services/bundled_assets.py` as the artifact foundation.
  - Keep the workspace-only built-in path and in-root support-file behavior.
  - Keep the installed-package proof path that reaches `rally run demo` and
    `doctrine.emit_docs`.
* Verification (required proof):
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `RALLY_TEST_DOCTRINE_SOURCE=git+https://github.com/aelaguiz/doctrine.git@v1.0.1 uv run pytest tests/integration/test_packaged_install.py -q`
* Docs/comments (propagation; only if needed):
  - none beyond keeping current docs honest while later phases rewrite the
    release system
* Exit criteria:
  - The built-artifact install path stays green while release-system work lands.
* Rollback:
  - Do not regress the packaged-runtime path while changing release tooling.

## Phase 2 - Mirror Doctrine's version files and release docs

Status: COMPLETED

* Goal:
  Make Rally's visible version files read like Doctrine's, while still naming
  Rally's real support-surface versions.
* Work:
  - Rewrite `docs/VERSIONING.md` to match Doctrine's section order and release
    guidance pattern.
  - Define Rally's version lines:
    - public Rally release version
    - package metadata version
    - workspace manifest version
    - compiled agent contract version
    - Doctrine minimum supported release floor
    - Doctrine package constraint line
  - Add explicit current-version lines near the top of `docs/VERSIONING.md`:
    - `Current public Rally release version: vX.Y.Z`
    - `Current Rally package version: X.Y.Z`
    - `Current workspace manifest version: 1`
    - `Current compiled agent contract version: 1`
    - `Current minimum Doctrine release: v1.0.1`
    - `Current supported Doctrine package line: doctrine>=1.0.1,<2`
  - Replace `dynamic = ["version"]` with explicit package version truth in
    `pyproject.toml`.
  - Remove `[tool.setuptools_scm]` from `pyproject.toml`.
  - Rewrite `CHANGELOG.md` to Doctrine-style release sections and fixed release
    header fields.
  - Keep the release header close to Doctrine's exact field order:
    - `Release kind`
    - `Release channel`
    - `Release version`
    - `Affected surfaces`
    - `Who must act`
    - `Who does not need to act`
    - `Upgrade steps`
    - `Verification`
    - `Support-surface version changes`
  - Update `README.md` and `CONTRIBUTING.md` so public release instructions
    point to the same file roles and command names Doctrine users expect.
  - Update `README.md` so the top docs map follows the same stable cross-repo
    pattern as Doctrine:
    - docs or design entry
    - versioning
    - changelog
    - support
    - security
* Verification (required proof):
  - Add and run parser-style unit tests for:
    - package version parsing
    - changelog release section parsing
    - workspace version parsing
    - compiled contract version parsing
    - Doctrine floor line parsing
    - Doctrine package constraint parsing
  - `uv run pytest tests/unit/test_release_flow.py -q`
* Docs/comments (propagation; only if needed):
  - Rewrite the touched docs in the same pass. Do not leave mixed Rally and
    Doctrine release wording alive at the same time.
* Exit criteria:
  - Rally's public version files use Doctrine-style structure and explicit
    package-version truth.
  - Rally's real support-surface versions are documented clearly.
* Rollback:
  - Revert `pyproject.toml`, `docs/VERSIONING.md`, `CHANGELOG.md`, `README.md`,
    and `CONTRIBUTING.md` together.

## Phase 3 - Add the Doctrine-style Rally release helper stack

Status: COMPLETED

* Goal:
  Give Rally the same repo-owned release command family Doctrine already has.
* Work:
  - Add `Makefile` with the public targets:
    - `release-prepare`
    - `release-tag`
    - `release-draft`
    - `release-publish`
  - Keep the command names the same as Doctrine. The only planned argument
    difference is that Rally has no `LANGUAGE_VERSION=` input.
  - Make `release-prepare` require:
    - `RELEASE`
    - `CLASS`
    - `CHANNEL`
  - Add `src/rally/release_flow.py` with `prepare`, `tag`, `draft`, and
    `publish` subcommands.
  - Add `src/rally/_release_flow/common.py`.
  - Add `src/rally/_release_flow/models.py`.
  - Add `src/rally/_release_flow/parsing.py`.
  - Add `src/rally/_release_flow/tags.py`.
  - Add `src/rally/_release_flow/ops.py`.
  - Mirror Doctrine's preflight behavior:
    - release tag parsing and channel checks
    - release-class move validation
    - clean worktree requirement
    - git signing-key requirement
    - `git verify-tag`
    - pushed-tag object match on `origin`
    - changelog entry validation
    - package-version-to-tag validation
  - Adapt Doctrine's worksheet model to Rally's real support surfaces instead of
    a fake language version.
  - Add `tests/unit/test_release_flow.py` that mirrors Doctrine's release-flow
    coverage.
  - Keep the helper output close to Doctrine:
    - fixed worksheet heading
    - exact next commands
    - fixed release-note header lines
    - loud release errors for tag, signing, changelog, or package-version
      drift
* Verification (required proof):
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - `uv run pytest tests/unit -q`
  - run one local `make release-prepare ...` proof once the helper lands
* Docs/comments (propagation; only if needed):
  - Keep help text and docstrings aligned with Doctrine's command wording where
    the behavior is the same.
* Exit criteria:
  - Rally has the same public release command family Doctrine uses.
  - Rally release preflight failures happen before tagging or GitHub release
    work.
* Rollback:
  - Revert `Makefile`, release helper modules, and release-flow tests together.

## Phase 4 - Harden GitHub governance and PR CI

Status: COMPLETED

Completion proof already landed for the split PR and ruleset cutover:
- PR `#5` ran the split PR checks against the live `main` ruleset and showed
  the planned required names:
  - `bundled-assets`
  - `unit`
  - `packaged-install`
  - `security / dependency-review`
- The PR could not merge while those required checks were pending or failed,
  then merged cleanly once the repaired branch re-ran green on 2026-04-14.
- After merge, `gh api repos/aelaguiz/rally/actions/workflows` shows the live
  default-branch workflow set includes:
  - `.github/workflows/dependency-review.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/publish.yml`
  - `.github/workflows/scorecards.yml`
- After the CodeQL baseline turned green on `main`, the live `main` ruleset
  gained a real `code_scanning` rule for `CodeQL` with thresholds:
  - alerts: `errors`
  - security alerts: `medium_or_higher`
- This uses GitHub's code-scanning merge protection surface instead of
  unstable `Analyze (...)` required status contexts.
- PR `#9` proved the final gate behavior under the finished ruleset:
  - it was `BLOCKED` while `Analyze (actions)`,
    `Analyze (javascript-typescript)`, and `Analyze (python)` were still
    pending
  - it became `CLEAN` only after all three CodeQL analyses passed, alongside
    the split PR checks

* Goal:
  Make Rally's GitHub repo posture read like Doctrine's maintainer-first
  hardened posture where Rally has the same kind of surface.
* Work:
  - Add `.github/CODEOWNERS` with maintainer-first routing for:
    - `*`
    - `.github/**`
    - `docs/**`
    - `src/**`
    - `flows/**`
    - `stdlib/**`
    - `skills/**`
    - `mcps/**`
  - Add `.github/PULL_REQUEST_TEMPLATE.md` with:
    - summary
    - user-facing impact
    - checks run
    - docs/examples touched
    - versioning or release-note label
    - risk or follow-up notes
  - Add `.github/dependabot.yml` for:
    - GitHub Actions
    - root Python package surfaces
  - Add `.github/workflows/pr.yml` for pull requests to `main` with
    concurrency by PR number and these stable jobs:
    - `bundled-assets`
    - `unit`
    - `packaged-install`
  - Make `packaged-install` no-op only when the diff is clearly outside
    runtime, release, packaging, or docs surfaces that affect the external-user
    path.
  - Add `.github/workflows/dependency-review.yml` with required job name:
    - `security / dependency-review`
  - Add `.github/workflows/scorecards.yml` as weekly and manual only. Keep it
    non-blocking at first.
  - Pin every third-party action to a full commit SHA with the release tag in a
    trailing comment.
  - Set workflow permissions to least privilege by default.
  - Document and apply the maintainer-first repo settings:
    - ruleset-protected `main`
    - require PR before merge
    - require conversation resolution
    - require strict status checks
    - require linear history
    - block force pushes
    - block deletions
    - zero required approvals
    - squash-only merges
    - auto-merge on
    - auto-delete merged branches on
  - Enable private vulnerability reporting.
  - Enable automated security fixes.
  - Enable CodeQL default setup, then make it a required gate after the
    baseline is green.
* Verification (required proof):
  - Open one PR and confirm the split checks appear with the planned names.
  - Confirm an out-of-date or failing PR cannot merge under the ruleset.
  - Confirm actions are pinned and workflow permissions are explicit in repo.
  - Confirm private vulnerability reporting and automated security fixes show as
    enabled in repo settings.
* Docs/comments (propagation; only if needed):
  - Update `README.md` and `CONTRIBUTING.md` if they mention PR flow or CI.
* Exit criteria:
  - Rally has a stable maintainer-first PR gate with visible required checks.
  - Rally's repo trust surfaces no longer look under-owned.
* Rollback:
  - Do not turn on required checks in a ruleset until the named workflows are
    live and green.

## Phase 5 - Cut over GitHub draft, publish, and public trust surfaces

Status: COMPLETE

Completion proof:
- After PR `#5` merged on 2026-04-14, `gh api repos/aelaguiz/rally/actions/workflows`
  shows `.github/workflows/publish.yml` active on `main`.
- The `workflow_dispatch` dry run on `main` succeeded:
  - workflow run: `24403594896`
  - result: `build` job passed
  - proof inside the run:
    - bundled-assets check passed
    - unit tests passed
    - source and wheel build passed
    - packaged-install proof passed
    - distribution artifacts were stored
    - publish legs were skipped cleanly because `publish_target=none`
- The public trust surfaces this phase owned now live on `main` together:
  - `README.md`
  - `SECURITY.md`
  - `SUPPORT.md`
  - `CHANGELOG.md`
  - `docs/VERSIONING.md`
- The first live TestPyPI rehearsal completed from this branch:
  - workflow run: `24412949483`
  - result: `metadata`, `build`, and `publish-testpypi` all passed
  - release proof and Trusted Publishing both succeeded for distribution
    `rally-agents`
- The first live GitHub release publish completed from the signed tag:
  - signed annotated tag: `v0.1.0`
  - GitHub release URL:
    `https://github.com/aelaguiz/rally/releases/tag/v0.1.0`
  - release workflow run: `24413066602`
  - result: `metadata`, `build`, and `publish-pypi` all passed
  - uploaded release assets:
    - `rally_agents-0.1.0.tar.gz`
    - `rally_agents-0.1.0-py3-none-any.whl`

Manual QA (non-blocking):
- Do one cold read of the published GitHub release page plus the PyPI and
  TestPyPI project pages.

* Goal:
  Make the public GitHub release path, artifact publication path, and public
  trust docs follow the Doctrine-style operator story instead of the current
  tag-push workflow.
* Work:
  - Replace `.github/workflows/publish.yml` with Doctrine's current publish
    workflow topology:
    - `on: release` with `types: [published]`
    - `on: workflow_dispatch`
    - input `ref`
    - input `publish_target = none|testpypi|pypi`
  - The workflow must:
    - check out the chosen release tag or requested ref
    - build wheel and sdist
    - run the external-user smoke proof from built artifacts
    - upload wheel and sdist assets to the GitHub release
    - publish the same artifacts to PyPI with Trusted Publishing
  - Keep `make release-draft` focused on the GitHub draft release and notes.
  - Keep `make release-publish` focused on publishing the draft release, then
    waiting for the release-published workflow outcome.
  - Keep TestPyPI dry runs in the same `publish.yml` workflow through
    `workflow_dispatch`, matching Doctrine's current shape, instead of adding a
    second publish workflow.
  - Add `SECURITY.md` and `SUPPORT.md` with maintained-project wording.
  - Keep prerelease rules aligned with Doctrine:
    - beta and rc releases are GitHub prereleases
    - beta and rc releases are not marked latest
  - Keep stable-release immutability rules aligned with Doctrine's docs.
  - Add a short public badge row to `README.md` once the real surfaces exist:
    - CI
    - PyPI
    - Python version
    - license
    - optional scorecards
* Verification (required proof):
  - Add unit tests for generated `gh release` command shape.
  - Add unit tests for prerelease vs stable release behavior.
  - Review the `publish.yml` workflow for:
    - least-privilege permissions
    - pinned actions
    - protected `pypi` environment
    - Trusted Publishing
    - `workflow_dispatch` dry-run inputs
  - Re-run `uv build` and the packaged-install proof through the new helper
    verify commands.
* Docs/comments (propagation; only if needed):
  - Update release docs so the public steps are `make release-*`, not tag push
    plus GitHub Actions.
  - Update `README.md`, `SECURITY.md`, and `SUPPORT.md` together.
* Exit criteria:
  - Rally's canonical public release path is repo-owned and matches Doctrine's
    draft-review-publish model.
  - GitHub releases attach the exact shipped artifacts.
  - PyPI publish runs through Trusted Publishing.
  - Rally's public trust docs read like a maintained project.
* Rollback:
  - Do not cut over the public docs until the new release helper path is
    passing locally.

## Phase 6 - Prove full parity and release readiness

Status: COMPLETE

Completion proof already landed for the rest of this phase:
- Local release proof stayed green after the clean-checkout repair:
  - `make verify`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
- The live PR gate proof completed through merged PR `#5` on 2026-04-14.
- The live publish transport proof completed through workflow run
  `24403594896` on `main` with `publish_target=none`.
- The README host-repo path was followed by hand in a temp external workspace
  from the built wheel:
  - installed `rally-agents==0.1.0` plus Doctrine `v1.0.1` into an isolated
    venv
  - ran `rally run demo` with the venv `bin/` on `PATH`
  - confirmed Rally created `DMO-1`, synced `stdlib/rally/`,
    `skills/rally-kernel/`, and `skills/rally-memory/` into the host repo,
    and stopped cleanly at the documented `home/issue.md` step
- Final live-gate proof landed through PR `#9` on 2026-04-14:
  - the PR started `BLOCKED` under the finished ruleset while CodeQL was
    still running
  - the PR became `CLEAN` only after the split PR checks and all three live
    CodeQL analyses passed
  - PR `#9` then merged to `main`, so the final readiness proof is now on the
    default branch rather than only in local notes
- The live signed-tag release walk now completed end to end:
  - `make release-tag RELEASE=v0.1.0 CHANNEL=stable`
  - `make release-draft RELEASE=v0.1.0 CHANNEL=stable PREVIOUS_TAG=auto`
  - `make release-publish RELEASE=v0.1.0`
- The protected `pypi` environment gate was exercised for the release run and
  approved through the GitHub Actions pending-deployments API.
- Both package indexes now show the published package version:
  - TestPyPI JSON: `rally-agents 0.1.0`
  - PyPI JSON: `rally-agents 0.1.0`

Manual QA (non-blocking):
- Do one rendered GitHub README cold read now that the badge row and docs map
  are live on the public repo.

* Goal:
  Prove that Rally now feels like a Doctrine-aligned extension at release time,
  while keeping the external-user install path green.
* Work:
  - Run the packaged-runtime proof path.
  - Run the new release-flow unit suite.
  - Run one local Rally release rehearsal through:
    - `make release-prepare ...`
    - `make release-tag ...` dry-run-equivalent coverage in unit tests
    - `make release-draft ...` command-shape coverage in unit tests
    - `make release-publish ...` command-shape coverage plus watched workflow
      coverage
  - Follow the README host-repo flow by hand once after the release-doc cutover.
  - Confirm the hardened repo settings still line up with the named required
    checks after the workflow split.
* Verification (required proof):
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `RALLY_TEST_DOCTRINE_SOURCE=git+https://github.com/aelaguiz/doctrine.git@v1.0.1 uv run pytest tests/integration/test_packaged_install.py -q`
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - one successful `make release-prepare ...` rehearsal in the real repo
  - one successful publish-workflow dry run or first real release rehearsal
    after the cutover
* Docs/comments (propagation; only if needed):
  - none beyond any last doc truth fixes found during the rehearsal
* Exit criteria:
  - A Doctrine user can look at Rally's release files and commands and see the
    same operator conventions.
  - A Doctrine user can also look at Rally's GitHub repo posture and see the
    same maintainer-first hardening direction.
  - The built-artifact external-user path is still green.
* Rollback:
  - Do not ship the parity cutover until both the release helper tests and the
    built-artifact proof are green.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

Keep the proof set lean, operator-real, and parity-focused. The release-system
rewrite is only done when the built-artifact user path still works and the new
Doctrine-style release helper rules fail loudly in unit tests.

## 8.1 Unit tests (contracts)

- `tests/unit/test_release_flow.py` becomes the main release-system contract
  suite. It should cover:
  - release-tag parsing and channel matching
  - release-class bump rules
  - package-version-to-tag mapping under PEP 440
  - explicit `[project].version` parsing
  - fixed changelog header parsing and placeholder rejection
  - workspace version parsing from `[tool.rally.workspace].version`
  - compiled contract version parsing from the real owning Rally code path
  - Doctrine floor and Doctrine package constraint parsing from
    `docs/VERSIONING.md`
  - clean-worktree failure
  - signing-key failure
  - annotated-tag requirement
  - `git verify-tag` failure
  - pushed-tag mismatch failure
  - generated `gh release create` command shape
  - generated `gh release edit --draft=false` command shape
  - generated post-publish workflow wait behavior
- Keep `uv run pytest tests/unit -q` as the wider behavior-preservation suite.
- Keep `uv run python tools/sync_bundled_assets.py --check` as the bundle-drift
  gate.

## 8.2 Integration tests (flows)

- Keep `tests/integration/test_packaged_install.py` as the built-artifact
  external-user proof.
- That proof must continue to cover:
  - built wheel install
  - install against Doctrine `v1.0.1`
  - `rally --help`
  - `rally run demo`
  - workspace-local built-in sync
  - host `doctrine.emit_docs`
  - no support file escaping the host project root
- Add one repo-local release rehearsal command path:
  - `make release-prepare RELEASE=... CLASS=... CHANNEL=...`
- Add one PR-CI acceptance path:
  - split required checks appear with stable names
  - repeated pushes cancel stale PR runs
- Add one release-workflow acceptance path:
  - `release.published` build runs from the release tag
  - `workflow_dispatch` can run the same workflow against a chosen ref
  - GitHub release assets are attached by the workflow
  - the same version is published to PyPI

## 8.3 Final human rehearsal

- One human-supervised first release after the cutover should walk the full
  operator flow:
  - update `pyproject.toml`
  - update `docs/VERSIONING.md`
  - update `CHANGELOG.md`
  - `make release-prepare ...`
  - run proof
  - `make release-tag ...`
  - `make release-draft ...`
  - review GitHub draft
  - `make release-publish ...`
- One README-guided host-repo setup should be followed by hand from a fresh
  temp workspace after docs are rewritten.
- One README cold read should confirm the docs map exposes versioning,
  changelog, support, and security from the top-level repo entry.
- One repo-settings pass should confirm:
  - main ruleset is active
  - private vulnerability reporting is on
  - automated security fixes are on
  - CodeQL default setup is live or explicitly queued behind baseline cleanup

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Land the parity work in this order:

1. keep the packaged-runtime proof green
2. rewrite version files and release docs
3. land the release helper stack and its unit suite
4. land the GitHub governance and PR CI hardening surfaces
5. cut over the GitHub release and publish path
6. delete the old tag-push release ownership path
7. run one supervised first release rehearsal before public use
8. once doctrine-side trust-doc wording settles, do one final wording-alignment
   pass across README, SECURITY.md, and SUPPORT.md

Do not publish new docs that teach `make release-*` until the helper and proof
path are real in repo.

## 9.2 Telemetry changes

No new product telemetry is expected. Release proof should rely on:

- local test and make-target signals
- GitHub draft-release state
- one watched release-published workflow run
- repo settings state for rulesets and security features

No extra runtime telemetry system should be added for release work.

## 9.3 Operational runbook

Canonical operator runbook:

1. Update:
   - `pyproject.toml`
   - `docs/VERSIONING.md`
   - `CHANGELOG.md`
   - any touched public docs
2. Run:
   - `make release-prepare RELEASE=vX.Y.Z CLASS=internal|additive|soft-deprecated|breaking CHANNEL=stable|beta|rc`
3. Run the printed proof commands.
4. Run:
   - `make release-tag RELEASE=vX.Y.Z CHANNEL=stable|beta|rc`
5. Run:
   - `make release-draft RELEASE=vX.Y.Z CHANNEL=stable|beta|rc PREVIOUS_TAG=auto`
6. Review the GitHub draft release.
7. Run:
   - `make release-publish RELEASE=vX.Y.Z`
8. Approve the `pypi` environment if GitHub asks for manual approval.
9. Confirm:
   - GitHub release is published
   - release assets match the reviewed draft assets
   - `publish.yml` passed
   - PyPI publish passed
10. Optional dry run before the first public cut:
   - run `publish.yml` by `workflow_dispatch` with `publish_target=testpypi`
     against the chosen ref
11. Periodically confirm:
   - required check names still match the ruleset
   - action pins are still on full SHAs
   - private vulnerability reporting is still enabled
   - automated security fixes are still enabled

Intentional Rally-specific note:

- Rally keeps the same public command family as Doctrine.
- Rally does not take `LANGUAGE_VERSION=` because Rally has no Doctrine-style
  language-version line.
- Rally's only extra release step is the release-published workflow that builds
  assets and ships them to PyPI after GitHub release publication.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, `# 0)` through `# 10)`, `planning_passes`, and helper-block drift
  - alignment across outcome, scope, owner path, required deletes, execution order, verification, rollout, and approved exceptions
  - parity claims against Doctrine's live versioned repo surfaces for release docs, release helpers, README routing, and workflow topology
- Findings summary:
  - the main plan now says one coherent thing end to end about exact
    Doctrine-convention parity for Rally's release, packaging, versioning,
    README routing, and shared GitHub trust surfaces
  - the last real drift was in the helper block itself: it still described the
    earlier pre-reopen consistency pass instead of the later Doctrine-live
    research and deep-dive repairs
- Integrated repairs:
  - refreshed this helper block so it now points at the current plan truth:
    live Doctrine repo surfaces are the convention anchor, `.github/workflows/pr.yml`
    and `.github/workflows/publish.yml` are the target workflow files, README
    docs-map parity is part of the public release surface, and `SECURITY.md`
    plus `SUPPORT.md` copy the file pair and routing purpose without copying
    stale Doctrine wording
  - confirmed the append-only Decision Log is still consistent because the
    later 2026-04-14 parity entries explicitly supersede the older
    `setuptools-scm` and tag-push release direction
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

## 2026-04-13 - Make external-user install the first-class release goal

Context

Rally's core runtime shape is already good, but the user asked for a release,
packaging, and versioning system that is very easy to use and fully solves the
rough edges an external user would hit.

Options

- Keep the current repo-first story and add a light release note layer later.
- Plan around packaging first, but leave external-user proof as a follow-up.
- Make external-user install, packaging, versioning, and Doctrine alignment one
  integrated release-system plan.

Decision

Plan the release system around the real external-user path from day one, and
tie Rally's version and compatibility model to the Doctrine2 policy boundary
instead of treating packaging, release tags, and compatibility as separate
cleanup jobs.

Consequences

- The plan must cover package layout, version truth, release flow, docs, and
  external-user tests together.
- The eventual implementation may need wider convergence than a small metadata
  tweak.

Follow-ups

- Ground the packaging and publish path against official PyPA guidance.

## 2026-04-14 - Reopen the plan for exact Doctrine convention parity

Context

The earlier plan solved the external-user packaging path, but the user wants
the full release system reopened until Rally looks and feels like a Doctrine
extension at release time too.

Options

- Keep the current Rally release tooling and only tighten docs.
- Copy Doctrine's public command family and doc shape, but keep Rally's dynamic
  versioning and tag-push publish workflow.
- Reopen the plan fully so version files, changelog, helper scripts, signing
  checks, GitHub draft flow, and PyPI publish transport all line up with
  Doctrine's conventions.

Decision

Reopen the plan fully. Rally should match Doctrine's public release grammar as
closely as possible:

- explicit `[project].version`
- Doctrine-shaped `docs/VERSIONING.md`
- Doctrine-shaped `CHANGELOG.md`
- `Makefile` with `release-prepare`, `release-tag`, `release-draft`, and
  `release-publish`
- repo-owned `src/rally/release_flow.py` plus `src/rally/_release_flow/**`
- signed annotated tags and `git verify-tag`
- GitHub draft-review-publish flow through `gh`

The only allowed Rally-only extension is a `release.published`
`.github/workflows/publish.yml` transport workflow that builds release assets,
attaches them to the GitHub release, and ships them to PyPI, because Rally
ships a PyPI package and Doctrine does not.

Consequences

- Rally drops `setuptools-scm` and dynamic public version truth.
- Rally deletes or demotes the old tag-push publish workflow as the canonical
  public path.
- Rally must document its real narrow support-surface versions instead of
  inventing a fake language-version line.
- The release helper suite now becomes a first-class implementation phase, not
  a follow-up polish item.

Follow-ups

- Rewrite Sections 8 through 10 so the plan is internally consistent again.
- Ground the PyPI transport detail against Trusted Publishing guidance.
- Fold Doctrine's CI and GitHub hardening plan into Rally where the repo
  surfaces match.
- Ground the Rally-to-Doctrine compatibility boundary against the Doctrine2
  policy doc.
- Resolve the version-source, build-backend, exact Doctrine minimum version,
  and external-user bootstrap decisions before implementation.

## 2026-04-14 - Import Doctrine CI and GitHub hardening where Rally has the same surface

Context

Doctrine's parity work now also covers repo governance, PR CI, supply-chain
checks, and public trust docs. Rally should not stop at release-command parity
if the repo still looks looser on GitHub.

Options

- Keep Rally's plan focused only on release files and helper scripts.
- Copy Doctrine's whole hardening plan literally, including surfaces Rally does
  not have.
- Import the same GitHub hardening direction where Rally has the same class of
  surface and explicitly exclude Doctrine-only items that do not fit Rally.

Decision

Import the Doctrine hardening direction where it fits Rally:

- maintainer-first protected `main`
- split stable PR checks
- CODEOWNERS
- PR template
- Dependabot
- dependency review
- scorecards
- CodeQL baseline
- private vulnerability reporting
- automated security fixes
- maintained-project `SECURITY.md` and `SUPPORT.md`
- release-published build-and-publish workflow

Do not copy Doctrine-only items that do not fit Rally, such as a VS Code lane,
a package rename, or merge queue policy.

Consequences

- The plan now covers repo settings and trust surfaces, not just release files.
- Rally's phase plan grows by one governance/PR-CI phase and one trust-surface
  expansion in the publish phase.
- The release parity claim is now stronger and more honest: Rally should read
  like a Doctrine extension both in release commands and in GitHub posture.

Follow-ups

- Keep the PR check names stable enough for a ruleset to anchor them.
- Keep required workflows pinned and least-privilege from the first pass.

## 2026-04-14 - Anchor cross-repo conventions to Doctrine's live versioned surfaces

Context

Doctrine hardening is still landing in real time. Rally needs stable
cross-repo conventions, especially for packaging, versioning, release docs,
README routing, and release workflows, without overfitting to wording that is
still moving.

Options

- Treat the Doctrine hardening notes as the main source of truth, even when the
  repo files have not landed yet.
- Freeze Rally's plan to only the older release-command parity work and ignore
  the new Doctrine repo surfaces until later.
- Anchor Rally to the Doctrine repo surfaces that are already versioned and
  present now, and treat the still-moving copy as secondary.

Decision

Anchor Rally's stable cross-repo conventions to Doctrine's live versioned repo
surfaces:

- `pyproject.toml`
- `docs/VERSIONING.md`
- `CHANGELOG.md`
- `Makefile`
- `doctrine/release_flow.py`
- `doctrine/_release_flow/**`
- `.github/workflows/pr.yml`
- `.github/workflows/publish.yml`
- `README.md`

Treat `SECURITY.md` and `SUPPORT.md` as stable owner-path conventions, but not
as final text conventions yet, because their current wording still reflects
Doctrine's pre-1.0 state.

Consequences

- Rally now targets the same `release.published` plus `workflow_dispatch`
  publish workflow topology Doctrine already has in repo.
- Rally now targets `.github/workflows/pr.yml` instead of a Rally-only PR
  workflow filename.
- Rally now treats the README docs map, versioning file, changelog, support
  doc, and security doc as one visible package-and-release surface.
- Rally avoids copying transient doctrine wording while still staying aligned
  on file ownership and workflow shape.

Follow-ups

- Keep comparing Rally against the live Doctrine repo, not against stale notes.
- Once Doctrine finalizes its support/security wording, do one wording-aligned
  pass across the matching Rally docs.

## 2026-04-14 - Lock the Doctrine floor to v1.0.1

Context

The earlier research pass had one blocker: Rally needed one exact minimum
Doctrine public release version before the planning controller could continue.

Options

- Keep the blocker open until Rally can infer the floor from package metadata.
- Use the new public Doctrine release anchor in `../doctrine`.
- Guess a version line from the Doctrine language version.

Decision

Use Doctrine public release `v1.0.1` as Rally's minimum dependency floor for
first public ship.

Consequences

- Rally can now continue the full planning arc without guessing at the
  dependency floor.
- Later phases must wire `v1.0.1` into Rally package metadata, docs, release
  notes, and external-user tests.
- Rally must keep treating Doctrine package metadata `0.0.0` as non-public
  placeholder truth.

Follow-ups

- Deep-dive the exact dependency-spec form Rally should publish.
- Carry `v1.0.1` through the phase plan, verification matrix, and release
  docs.

## 2026-04-14 - Use a generated in-package built-in bundle and workspace-only runtime lookup

Context

Rally's current runtime expects built-ins near a filesystem framework root, but
the wheel ships only `src/rally/**`. The plan needed one concrete package shape
that keeps built-ins installable without leaving authored source unclear.

Options

- Keep top-level built-ins only and continue runtime filesystem discovery.
- Move all authored built-in source directly under `src/rally/**`.
- Keep top-level authored built-ins in the Rally workspace, but generate a
  packaged `_bundled/**` snapshot that the installed runtime syncs into the
  workspace before build or run.

Decision

Keep authored built-in source in Rally's fixed top-level workspace folders and
generate one in-package bundle under `src/rally/_bundled/**`. The installed
runtime reads packaged built-ins through `importlib.resources`, syncs them into
the workspace, and then uses workspace paths only.

Consequences

- Release artifacts can ship the built-ins the runtime needs.
- Runtime code can delete framework-root fallback behavior.
- Build and CI need one bundle-sync step and one stale-bundle failure mode.

Follow-ups

- Add the bundled-assets owner module.
- Add `tools/sync_bundled_assets.py` as the only bundle writer.
- Wire the front-door workspace sync into runner and build paths.
- Update tests to cover workspace-only runtime behavior after sync.

## 2026-04-14 - Keep the stock setuptools backend and commit the generated bundle

Context

Deep-dive pass 1 locked the need for an in-package built-in bundle, but it had
not yet resolved whether Rally should mutate the bundle at build time or keep a
checked-in generated snapshot.

Options

- Add a custom build backend or `setup.py` hook that copies bundle files during
  wheel and sdist build.
- Keep plain `setuptools.build_meta`, commit the generated bundle, and use one
  explicit sync tool plus drift checks.
- Move authored built-ins under `src/rally/**` and stop generating a bundle.

Decision

Keep the stock `setuptools.build_meta` backend. Commit the generated
`src/rally/_bundled/**` tree, make `tools/sync_bundled_assets.py` the only
writer for it, and use CI plus release workflow check mode to fail on drift.

Consequences

- Packaging stays standard and readable.
- Build artifacts do not depend on hidden filesystem mutation during wheel
  creation.
- Contributors must run the sync tool when authored built-ins change.

Follow-ups

- Add `MANIFEST.in` and package-data config for bundled assets.
- Add bundled-assets drift tests and artifact-build proof.

## 2026-04-14 - Use tag-derived Rally versions and one transitive Doctrine floor

Context

Rally needs a public release version source, a standard publish path, and a
clear external install story that does not ask host repos to reason about
Doctrine separately.

Options

- Keep a hand-edited version string in `pyproject.toml`.
- Add a custom Rally-only release helper stack.
- Use signed git tags as public release truth, derive package version with
  `setuptools-scm`, and carry Doctrine through Rally's dependency metadata.

Decision

Use tag-derived Rally versions through `setuptools-scm` and publish one
transitive compatibility contract in Rally package metadata:
`doctrine>=1.0.1,<2`.

Consequences

- Host repos can install Rally as one dependency and get a tested Doctrine
  floor automatically.
- Rally release truth moves onto signed tags, changelog entries, and version
  docs instead of a placeholder package string.
- Release automation can stay standard and GitHub Actions driven.

Follow-ups

- Add `docs/VERSIONING.md` and `CHANGELOG.md`.
- Add the tag-driven publish workflow.
- Carry the dependency contract through tests and public docs.

## 2026-04-14 - Sequence implementation around artifact truth first

Context

Deep-dive resolved the architecture, but the plan still needed one explicit
execution order that would keep package truth, runtime cutover, and public docs
from drifting apart during implementation.

Options

- Cut runtime lookup over first, then fix package contents later.
- Rewrite docs and release workflow first, then make the artifact path real.
- Make the artifact honest first, then cut runtime over, then land external-user
  proof and public release surfaces.

Decision

Sequence the work as: artifact and metadata foundation, runtime cutover to
workspace-only built-ins, then external-user proof plus public release docs and
workflow.

Consequences

- Early work can prove that the wheel and sdist really ship the built-ins
  before runtime code deletes the old fallback path.
- Public docs and publish automation do not move ahead of the real packaged
  install path.
- Section 7 can stay short, ordered, and fully authoritative.

Follow-ups

- Implement Section 7 in order without adding alternate execution paths.
- Keep Section 8 aligned with artifact-content proof and bundled-asset drift
  checks.

## 2026-04-14 - Treat out-of-root support-file emit failures as a ship blocker

Context

An external-user failure surfaced after the first consistency pass: a separate
host repo can still end up with a Doctrine emit target or emitted contract that
points a support file at `../rally/stdlib/rally/schemas/rally_turn_result.schema.json`.
Doctrine intentionally rejects that with `E519` because support files must stay
under the target project root.

Options

- Treat it as a separate Doctrine problem and leave Rally's release plan alone.
- Add a Rally-side workaround that still teaches external repos to point at
  sibling `../rally/...` paths.
- Make it a required Rally external-user proof case and solve it by syncing
  Rally-owned support files into the host workspace before emit.

Decision

Treat this as part of Rally's release and packaging plan. Rally must make the
external-user emit path work without any support file escaping the host project
root, and it must prove that in the packaged-install integration path.

Consequences

- Phase 2 now has to cover workspace-local support-file readiness before
  Doctrine emit.
- Phase 3 and Section 8 now have to prove a real host-repo emit path that does
  not trigger `E519`.
- Rally stays within Doctrine's current compiler rules instead of planning a
  Doctrine-side exception.

Follow-ups

- Add explicit host-emit proof to `tests/integration/test_packaged_install.py`.
- Remove external-host examples or docs that point support files at
  `../rally/stdlib/...`.

## 2026-04-14 - Make package-index setup an explicit operator pause

Context

Live Doctrine review showed one remaining convention Rally still does not teach
well: before the first real package-index publish, the maintainer must stop,
set up GitHub Trusted Publishers on TestPyPI and PyPI, and wire those up to the
same `publish.yml` workflow and matching GitHub environments. Doctrine already
makes that setup part of the documented release flow. Rally does not.

Options

- Keep the package-index setup as tribal knowledge outside the repo.
- Add a Rally-only script or hidden harness to paper over the setup drift.
- Make the setup an explicit doc and operator step, then keep the workflow
  settings in repo-owned metadata so the docs, helper code, and workflow read
  from the same truth.

Decision

Make the first package-index publish an explicit operator pause. Rally will add
repo-owned package metadata for package-index settings, and `docs/VERSIONING.md`
will later tell the maintainer exactly when to stop and how to configure
TestPyPI, PyPI, and the matching GitHub environments before the first real
publish.

Consequences

- The first real Rally package-index publish will wait on a human setup step.
- Rally's workflow can stop duplicating package-index settings in YAML.
- The plan must include a later point where implementation pauses and gives the
  user the exact setup steps for this repo.

Follow-ups

- Add a Rally package metadata block in `pyproject.toml`.
- Add a Rally helper that exports that metadata to GitHub Actions.
- Rewrite the first-publish section of `docs/VERSIONING.md`.

## 2026-04-14 - Narrow the remaining release architecture onto package metadata

Context

Deep Doctrine review and the first deep-dive pass showed that Rally already has
most of the broad release parity work on `main`: explicit package version
truth, release helpers, split PR checks, trust docs, and the draft-and-publish
release flow. The remaining drift is not another full release-system rebuild.
It is one smaller owner-path problem around package publish metadata, package
proof, and the first real package-index setup step.

Options

- Keep package publish settings split between `pyproject.toml`,
  `publish.yml`, and docs.
- Add a second Rally-only config file or script just for package publish state.
- Put the remaining package publish truth in `pyproject.toml` plus one
  `rally._package_release` helper, then make the workflow and docs read from
  that path.

Decision

Narrow the remaining architecture onto one package-release owner path:
`pyproject.toml` plus `src/rally/_package_release.py`. `release_flow` keeps
owning tag, changelog, and GitHub release behavior. The package helper owns the
publish metadata bridge and package smoke front door. `docs/VERSIONING.md`
owns the human first-publish setup checklist.

Consequences

- The next deep-dive pass and the fresh phase plan can focus on a much smaller
  frontier.
- `publish.yml` should stop carrying package publish environment names as its
  own truth.
- Rally can stay aligned with Doctrine without reopening already-landed trust
  surfaces or release commands.

Follow-ups

- Add `[tool.rally.package]` to `pyproject.toml`.
- Add `build-dist` and `verify-package` to the `Makefile`.
- Add a metadata job to `.github/workflows/publish.yml`.

## 2026-04-14 - Keep Doctrine-style package smoke and Rally's richer runtime proof

Context

Deep-dive pass 2 resolved the last architecture-hardening question: whether the
new Doctrine-style `verify-package` command should replace Rally's current
built-wheel host-workspace regression, or live beside it.

Options

- Make `verify-package` the only package and release proof.
- Keep only Rally's existing packaged-install regression and skip the
  Doctrine-style package proof split.
- Add `verify-package` for wheel and sdist package smoke outside the repo root,
  and keep Rally's existing built-artifact host-workspace regression inside the
  broader `make verify` path.

Decision

Keep both proof layers.

- `make verify-package` becomes the Doctrine-style package proof front door.
- `make verify` remains Rally's broader release proof and must keep the richer
  host-workspace regression that proves `rally run demo`, built-in sync, and
  host `doctrine.emit_docs`.
- `publish.yml` should run the broader Rally proof so both layers stay covered
  on release builds.

Consequences

- Rally aligns with Doctrine's package command surface without weakening its
  real runtime proof.
- Sdist smoke gets its own explicit home.
- Release docs and worksheets must teach both layers clearly so operators do
  not confuse package smoke with full Rally runtime proof.

Follow-ups

- Add `tests/unit/test_package_release.py`.
- Update the release worksheet in `src/rally/_release_flow/ops.py`.
- Update `docs/VERSIONING.md`, `README.md`, and `CONTRIBUTING.md` so the proof
  split is explicit.

## 2026-04-14 - Make Section 7 track only the remaining package-release frontier

Context

The older Section 7 mixed historical broad-parity work with the still-open
package-release slice. That made the execution checklist partly archival and
partly actionable, which is the wrong shape for `implement` and
`consistency-pass`.

Options

- Keep the old broad phase history in Section 7 and rely on readers to infer
  which parts are already landed.
- Delete the historical context entirely and keep only a short loose reminder of
  the remaining work.
- Rewrite Section 7 so it tracks only the still-open package-release phases,
  while leaving the already-landed context in Sections 4-6 and the decision
  log.

Decision

Rewrite Section 7 to track only the remaining package-release frontier.

- Phase 1 owns the package metadata helper and package metadata tests.
- Phase 2 owns the `build-dist` and `verify-package` split plus worksheet
  cutover.
- Phase 3 owns the metadata-driven publish workflow and first-publish doc
  cutover.
- Phase 4 starts only after the user completes the TestPyPI and PyPI setup from
  Phase 3.

Consequences

- Section 7 is now the one actionable checklist again.
- Already-landed PR gating, trust surfaces, and broad release parity stay as
  repo context, not live checklist items.
- The user setup pause is now an explicit blocking phase boundary instead of an
  implied later reminder.

Follow-ups

- Keep Section 8 and Section 9 aligned with the narrowed four-phase frontier.
- Stop in Phase 3 and hand the user the exact Rally-specific TestPyPI and PyPI
  setup steps before any real package-index publish.

## 2026-04-14 - Retire the old tag-derived version branch

Context

The consistency cold read found one remaining live contradiction in the
decision log. Most of the artifact now says Rally uses explicit
`[project].version` truth and has dropped `setuptools-scm`, but one older
decision entry still described the abandoned tag-derived version branch as if it
were active plan truth.

Options

- Leave the old entry alone and rely on readers to infer that it is stale.
- Rewrite the old entry in place and lose the append-only record of the branch.
- Append one explicit superseding decision that retires the old branch while
  preserving the history.

Decision

Append the superseding decision and keep the log append-only.

- Rally's active plan uses explicit `[project].version` truth.
- `setuptools-scm` and tag-derived package versions are retired for this plan.
- The old `2026-04-14 - Use tag-derived Rally versions and one transitive
  Doctrine floor` entry remains as historical branch context only, not current
  plan truth.

Consequences

- The artifact now says one consistent thing end to end about version truth.
- Later implementation work must not reintroduce dynamic package-version logic.
- The explicit Doctrine floor still stands, but it now travels with explicit
  package metadata rather than a tag-derived version source.

Follow-ups

- Keep `pyproject.toml`, `release_flow`, tests, and docs aligned on explicit
  package version truth during implementation.

## 2026-04-14 - Keep the approved six-phase frontier as the audit baseline

Context

Local execution notes later narrowed this doc around a smaller package-release
follow-up. That rewrite changed Section 7, Section 8, and Section 9 as if the
approved six-phase parity plan had been replaced.

Options

- Treat the package-release follow-up as the new authoritative frontier for
  this doc.
- Audit against the approved six-phase frontier, then move any extra
  package-release work to a separate or explicitly reopened plan.

Decision

Keep the approved six-phase frontier as the implementation-audit baseline for
this artifact.

- Fresh GitHub proof closes Phase 4 through Phase 6 on the live repo.
- Fresh local proof shows the current worktree still preserves that completed
  implementation.
- The narrower package-release follow-up does not reopen this completed plan by
  itself.

Consequences

- The authoritative audit block now stays `COMPLETE`.
- Any later package-release follow-up must use a new or explicitly reopened
  plan instead of narrowing this completed artifact in place.

Follow-ups

- Use `arch-docs` for any cleanup or retirement work on this completed plan.

## 2026-04-14 - Keep the package distribution name as `rally-agents`

Context

The first real TestPyPI and PyPI setup found a naming constraint that the
earlier local implementation had not modeled yet. The published project had to
be registered as `rally-agents`, not `rally`.

Options

- Keep publishing metadata as `rally` and treat the package-index setup as a
  one-off exception.
- Rename the Python import package and CLI to `rally-agents`.
- Keep the runtime import package and CLI as `rally`, but publish the
  distribution as `rally-agents`, matching Doctrine's split between
  distribution name and import name.

Decision

Keep the runtime import package and CLI as `rally`, but publish the
distribution as `rally-agents`.

- `[project].name` is `rally-agents`.
- `[tool.rally.package].import_name` stays `rally`.
- PyPI and TestPyPI project URLs derive from `rally-agents`.
- Install docs use `rally-agents`, while command examples still use `rally`.

Consequences

- Rally now matches the real package-index registrations instead of a local
  placeholder name.
- The package helper and release docs must keep telling readers that the
  distribution name differs from the import package and CLI.
- The release workflow can publish to the registered `rally-agents` projects
  without inventing a second naming convention.

Follow-ups

- Keep `pyproject.toml`, `docs/VERSIONING.md`, `README.md`, `CHANGELOG.md`,
  and package-release tests aligned on the `rally-agents` distribution name.

## 2026-04-14 - Reopen the live publish proof after the `rally-agents` cutover

Context

The `rally-agents` package-name cutover landed after the earlier audit marked
this artifact complete. The repo now has the metadata, docs, workflow, and
GitHub environments, but it still has only `workflow_dispatch` dry runs with
`publish_target=none`.

Options

- Keep treating the artifact as complete because the dry runs stayed green.
- Explicitly reopen the tail of this artifact until the live release and
  package-index path is exercised.

Decision

Explicitly reopen the tail of this artifact.

- Phase 5 stays reopened until one real GitHub release publish run attaches
  the built artifacts and drives the live publish path.
- Phase 6 stays reopened until one live package-index publish proof lands for
  `rally-agents` and the first signed-tag release walk is complete.

Consequences

- The authoritative audit block is now `NOT COMPLETE`.
- Phase 5 and Phase 6 are the only reopened phases.
- Phase 1 through Phase 4 stay complete.

Follow-ups

- Keep the earlier broad-parity proof intact.
- Finish the first live release walk instead of reopening the already-landed
  governance and doc cutover work.

## 2026-04-14 - Close the reopened live publish frontier with the first public release

Context

The earlier audit reopened Phase 5 and Phase 6 because Rally still lacked one
real signed release, one real `release.published` workflow run, and one live
package-index publish for `rally-agents`.

Options

- Stop after the local proof and the `publish_target=none` dry run.
- Close the reopened frontier by running the first real TestPyPI rehearsal and
  the first real signed public release.

Decision

Close the reopened frontier with live proof.

- Pushed branch commit `32a628e` and ran TestPyPI rehearsal workflow
  `24412949483`, which published `rally-agents 0.1.0` to TestPyPI.
- Created and pushed signed annotated tag `v0.1.0`.
- Created the GitHub draft release, published it, and watched release workflow
  `24413066602` complete successfully.
- Approved the protected `pypi` environment and confirmed the release workflow
  published `rally-agents 0.1.0` to PyPI and attached both dist assets to the
  GitHub release.

Consequences

- The reopened implementation frontier is now closed in code and ops reality.
- The authoritative audit block now matches the live release proof.
- Rally now has one real public release that proves the full Doctrine-aligned
  release path instead of only dry runs.

Follow-ups

- Do one cold read of the public GitHub release page plus the PyPI and
  TestPyPI project pages.
