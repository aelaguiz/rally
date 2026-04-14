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
Verdict (code): NOT COMPLETE
Manual QA: pending (non-blocking)

## Code blockers (why code is not done)
- Phase 1, Phase 2, Phase 3, and Phase 5 have fresh proof. On 2026-04-14,
  `make verify` passed, `make release-prepare RELEASE=v0.1.0 CLASS=additive
  CHANNEL=stable` passed, PR `#5` merged through the split PR checks, and
  `publish.yml` dry run `24403594896` succeeded on `main`.
- The false-complete problem moved later. The current completion rewrite made
  Phase 4 and Phase 6 look done even though the approved Phase 4 plan still
  required CodeQL to become a required gate after the baseline turned green.
- On 2026-04-14, `gh api repos/aelaguiz/rally/code-scanning/default-setup`
  showed CodeQL configured, and `gh run list --workflow CodeQL --branch main`
  showed a successful `main` CodeQL run. But
  `gh api repos/aelaguiz/rally/rulesets/15059522` still required only
  `bundled-assets`, `unit`, `packaged-install`, and
  `security / dependency-review`.
- PR `#5` still merged while `Analyze (python)` failed, so the live PR proof
  was taken against a weaker ruleset than the approved plan allowed.
- The real remaining frontier is the final governance and readiness frontier:
  finish Phase 4 by making CodeQL required, then rerun Phase 6's live
  PR/readiness proof under that final ruleset.

## Reopened phases (false-complete fixes)
- Phase 4 (Harden GitHub governance and PR CI) — reopened because:
  - CodeQL default setup is green on `main`, but no CodeQL check is required
    in the live `main` ruleset yet
- Phase 6 (Prove full parity and release readiness) — reopened because:
  - the local verify path and publish dry run are real, but the final live PR
    readiness proof still reflects the weaker pre-CodeQL ruleset

## Missing items (code gaps; evidence-anchored; no tables)
- CodeQL is still missing from the live required-check set.
  - Evidence anchors:
    - `gh api repos/aelaguiz/rally/code-scanning/default-setup` on 2026-04-14
    - `gh run list --workflow CodeQL --branch main --limit 10 --json ...` on
      2026-04-14
    - `gh api repos/aelaguiz/rally/rulesets/15059522` on 2026-04-14
    - `gh pr view 5 --json statusCheckRollup` on 2026-04-14
  - Plan expects:
    - Phase 4 says to enable CodeQL default setup, then make it a required
      gate after the baseline is green.
  - Code reality:
    - CodeQL default setup is configured and the latest `main` run succeeded,
      but the active ruleset still does not require any CodeQL check. PR `#5`
      still merged with a failing `Analyze (python)` run.
  - Fix:
    - add the stable CodeQL check name or names to the `main` ruleset and
      prove a PR cannot merge until they pass.
- Final readiness proof still needs one rerun under the finished ruleset.
  - Evidence anchors:
    - `gh pr view 5 --json statusCheckRollup` on 2026-04-14
    - `gh api repos/aelaguiz/rally/rulesets/15059522` on 2026-04-14
    - `gh run view 24403594896 --json jobs,...` on 2026-04-14
  - Plan expects:
    - Phase 6 says to confirm the hardened repo settings still line up with
      the named required checks after the workflow split, along with the local
      release proof and publish dry run.
  - Code reality:
    - the local verify path and publish dry run are real, but the only live PR
      proof happened before CodeQL became required, so final readiness is not
      proven yet.
  - Fix:
    - after the ruleset adds CodeQL, rerun one live PR proof and refresh the
      final readiness proof with that result.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- Walk the first real signed-tag release once before the first public Rally
  release.
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
- Replacing Rally's dynamic public package version source with Doctrine-style
  explicit package version truth in `pyproject.toml`.
- Adding a Rally-owned release helper stack that mirrors Doctrine's:
  `release-prepare`, `release-tag`, `release-draft`, and `release-publish`.
- Adding a Rally `Makefile` that exposes the same release targets and adjacent
  operator commands Doctrine already uses.
- Adding Rally GitHub governance settings that mirror Doctrine's planned
  maintainer-first defaults where Rally has the same surface:
  - ruleset-protected `main`
  - PR-required merges
  - strict status checks
  - linear history
  - squash-only merge policy
  - auto-merge
  - auto-delete merged head branches
  - zero required human approvals
- Adding Rally repo-owned trust surfaces that Doctrine's hardening plan also
  expects:
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
- Rewriting `CHANGELOG.md` so release entries use the same fixed header and
  payload shape Doctrine requires, with Rally-specific support-surface fields
  where Rally has real version lines.
- Defining Rally's narrow support-surface version lines clearly:
  `[tool.rally.workspace].version` and compiled agent `contract_version`.
- Replacing the current tag-push GitHub Actions publish path as Rally's
  canonical public release flow with a Doctrine-style GitHub draft-and-publish
  process through `gh`.
- Adding a release-published build-and-publish workflow so GitHub release
  publication, attached assets, smoke proof, and PyPI upload follow the same
  hardened repo story Doctrine is adopting.
- Keeping the packaged built-ins, external-user install path, and host-repo
  proof that already landed.
- External-user proof that runs from built artifacts in a clean temp
  environment and exercises the same path a real user would take.
- Test and CI changes needed to keep release metadata, package artifacts,
  release-helper behavior, and external-user setup honest.

Allowed architectural convergence scope:

- keeping the packaged built-in and runtime cutover work already done
- removing `setuptools-scm` and moving Rally back to explicit package versions
- adding repo-owned Rally release helper modules and Make targets that mirror
  Doctrine's structure
- deleting or reducing release automation that conflicts with the Doctrine-style
  public operator flow
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
- Rally currently uses `dynamic = ["version"]` plus `setuptools-scm`, while
  Doctrine uses explicit `[project].version`.
- Rally currently has `.github/workflows/publish.yml` as a tag-triggered public
  publish path, while Doctrine is now converging on a `release.published` plus
  `workflow_dispatch` publish workflow behind the same repo-owned Make and
  `release_flow` control plane.
- Rally's `docs/VERSIONING.md` and `CHANGELOG.md` are much lighter than
  Doctrine's required release surfaces.
- Rally's `README.md` front door and public trust-doc routing are lighter than
  Doctrine's current README-plus-doc-pair pattern.
- Rally currently has no `.github/CODEOWNERS`, no PR template, no
  `.github/dependabot.yml`, no split PR CI workflow, no public `SECURITY.md`,
  and no public `SUPPORT.md`.
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

- Replacing `setuptools-scm` with explicit package versions gives up one modern
  convenience, but it buys exact Doctrine operator parity and simpler release
  auditing.
- Replacing the tag-push GitHub Actions publish path with repo-owned release
  commands adds local operator steps, but it removes one big Rally-vs-Doctrine
  mental-model split.
- Rally will still need one or two Rally-specific release-note fields for real
  Rally support surfaces, but those should fit inside Doctrine's broader
  release structure instead of becoming a second format.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally is already a real `src/rally/` runtime package with packaged built-ins,
  a working installed CLI, and a credible external-user artifact proof.
- Rally already declares `doctrine>=1.0.1,<2` and proves that floor through the
  packaged-install test.
- Rally already has a canonical `docs/VERSIONING.md`, `CHANGELOG.md`, and a
  publish workflow, but those surfaces are Rally-local and lighter than
  Doctrine's release system.
- Rally currently has no repo-owned GitHub hardening surfaces beyond the one
  publish workflow: no CODEOWNERS, no PR template, no Dependabot config, no
  PR CI workflow split, and no public security or support docs.
- Doctrine already has a repo-owned public release system with explicit version
  truth, Make targets, signed-tag preflight, GitHub draft releases, and release
  tests.

## 2.2 What's broken / missing (concrete)

- Rally's installed-package story now works, but the public release system does
  not feel like Doctrine's.
- Rally still has no `Makefile` release commands, no repo-owned release helper
  modules, no signed-tag verification gates, and no GitHub draft-release
  helper path.
- Rally still relies on dynamic package version truth instead of Doctrine-style
  explicit package versions.
- Rally's changelog and version-policy docs still do not use Doctrine's fixed
  release-entry and release-note shapes.
- Rally's narrow support-surface versions are real but under-documented.
- Rally's GitHub repo governance and trust surfaces are too thin for the same
  maintained-1.x posture Doctrine is moving toward.
- A Doctrine user still has to learn a second release system to ship Rally.

## 2.3 Constraints implied by the problem

- The fix has to cover version files, release helper scripts, Make targets,
  docs, changelog, signing rules, GitHub release flow, GitHub governance, PR
  CI, security docs, and real external-user proof together.
- The final Rally story should feel like a Doctrine extension, not a sibling
  product with a different release grammar.
- The plan must preserve the packaged-runtime and external-user proof that
  already landed.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal "ground truth")

## 3.1 External anchors (papers, systems, prior art)

- Doctrine is the primary convention anchor for this reopened plan.
- The relevant external standard is not "what is modern Python release tooling
  in the abstract," but "what public release grammar does Doctrine teach its
  users today?"
- For stable cross-repo conventions, the highest-confidence Doctrine anchors
  are the versioned repo surfaces that already exist in tree today:
  - `pyproject.toml`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `Makefile`
  - `doctrine/release_flow.py`
  - `doctrine/_release_flow/**`
  - `.github/workflows/pr.yml`
  - `.github/workflows/publish.yml`
  - `README.md`
- For in-flight hardening copy, use Doctrine's file ownership and workflow
  topology first, but do not cargo-cult wording that is still obviously in
  motion. The current `SECURITY.md` and `SUPPORT.md` files in Doctrine are good
  owner-path anchors, but not yet final text anchors.
- Standard Python packaging still matters for built artifacts and version
  normalization, so the parity plan stays grounded in the public packaging
  rules as well:
  - the PyPA `pyproject.toml` guide treats explicit `[project].version` as a
    normal first-class metadata shape, so moving away from dynamic version
    derivation is standards-compliant even if it gives up a convenience tool
  - PEP 440 defines the package-version forms that should map to Rally's public
    tags:
    - `vX.Y.Z` -> `X.Y.Z`
    - `vX.Y.Z-beta.N` -> `X.Y.ZbN`
    - `vX.Y.Z-rc.N` -> `X.Y.ZrcN`
  - the local `gh` CLI already exposes the exact release flags Doctrine is
    built around:
    - `gh release create --draft --verify-tag --generate-notes`
    - `gh release edit --draft=false`
    - `gh workflow run ...`
    - `gh run watch --exit-status`
- Standard Python publish guidance still matters for the PyPI leg. The narrow
  Rally-only publish extension should use Trusted Publishing with OIDC and
  environment approval in GitHub Actions, but that workflow should be only the
  transport for PyPI upload, not Rally's canonical public release owner.
- Doctrine's current GitHub hardening direction is also part of the parity
  target for Rally where the same repo surface exists:
  - ruleset-protected `main`
  - maintainer-first PR governance with zero required approvals
  - split PR workflows with stable required job names
  - full-length SHA pinning for third-party actions
  - least-privilege workflow permissions
  - CODEOWNERS routing
  - dependency review
  - CodeQL default setup after baseline cleanup
  - weekly scorecards
  - private vulnerability reporting
  - automated security fixes
- Doctrine2's live policy split between public release version, language
  version, and narrow support-surface versions still matters. Rally should copy
  that framing, but with Rally's real support-surface lines instead of a fake
  language version.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `pyproject.toml` in Rally — currently uses `dynamic = ["version"]`,
    `setuptools-scm`, package data for `_bundled/**`, and
    `doctrine>=1.0.1,<2`. It also exposes one narrow Rally support-surface
    version already: `[tool.rally.workspace].version = 1`.
  - `src/rally/__init__.py` — currently reads Rally's installed version from
    package metadata.
  - `docs/VERSIONING.md` in Rally — now exists, but it is a lightweight local
    version-policy document, not a Doctrine-shaped release-policy document.
  - `CHANGELOG.md` in Rally — currently has a generic `## Unreleased` shape,
    not Doctrine's fixed release-section shape.
  - `README.md` in Rally — currently documents install and host-repo setup, but
    it does not yet use Doctrine's short docs-map pattern for versioning,
    changelog, support, and security surfaces.
  - `.github/workflows/publish.yml` in Rally — currently owns the public tag
    push -> build -> test -> publish path.
  - `.github/` in Rally — currently has only that publish workflow and no
    CODEOWNERS, PR template, Dependabot config, dependency-review workflow, or
    scorecards workflow.
  - public trust docs in Rally — `SECURITY.md` and `SUPPORT.md` do not exist
    yet.
  - `tests/integration/test_packaged_install.py` in Rally — already proves the
    installed `rally` front door and external host-repo path from built
    artifacts.
  - `../doctrine/Makefile` — Doctrine exposes the exact public operator
    commands Rally now needs to mirror:
    `release-prepare`, `release-tag`, `release-draft`, and `release-publish`.
  - `../doctrine/docs/VERSIONING.md` — Doctrine defines the public section
    order, release classes, fixed changelog header shape, signed-tag rules, bad
    release correction rules, and "what not to infer" wording Rally now needs
    to mirror closely.
  - `../doctrine/CHANGELOG.md` — Doctrine already has the fixed public release
    template Rally should reuse, including the portable-history framing and the
    release-entry header order.
  - `../doctrine/README.md` — Doctrine already has the short badge row, docs
    map, versioning/changelog links, and support/security references that Rally
    should mirror where the surface is shared.
  - `../doctrine/doctrine/release_flow.py` plus
    `../doctrine/doctrine/_release_flow/{ops,tags,parsing,models,common}.py` —
    Doctrine already has the exact helper structure Rally should copy.
  - `../doctrine/tests/test_release_flow.py` — Doctrine already has the exact
    release-preflight test family Rally should mirror.
  - `../doctrine/.github/workflows/pr.yml` — Doctrine now has the split PR
    workflow shape Rally should copy where the surface is shared:
    pinned actions, least-privilege permissions, concurrency by PR number, and
    stable named lanes.
  - `../doctrine/.github/workflows/publish.yml` — Doctrine now has the publish
    workflow shape Rally should copy where the surface is shared:
    `release.published` plus `workflow_dispatch`, build from the release ref,
    smoke-test the built wheel from a temp project, upload release assets, and
    publish through Trusted Publishing.
  - `../doctrine/SECURITY.md` and `../doctrine/SUPPORT.md` — Doctrine now has
    the public file pair Rally should also ship, but the current wording still
    carries pre-1.0 text, so the stable convention is the file pair and routing
    purpose, not the literal copy.
  - `src/rally/services/flow_loader.py` plus `src/rally/domain/flow.py` —
    Rally already has a real narrow support-surface version to document and
    maybe gate in release tooling: compiled agent `contract_version`.
  - `../doctrine/doctrine/_diagnostic_smoke/emit_checks.py` plus
    `../doctrine/docs/COMPILER_ERRORS.md` — Doctrine intentionally rejects
    emitted support files outside the target project root with `E519`, and
    Rally's packaged-install proof now already covers that path.
- Canonical path / owner to reuse:
  - `pyproject.toml` should stay the one owner for Rally package metadata,
    dependency floors, console entry points, and workspace version truth.
  - `docs/VERSIONING.md` should stay the one owner for Rally public release
    policy and support-surface version framing.
  - `CHANGELOG.md` should stay the one owner for portable release history.
  - `src/rally/release_flow.py` plus `src/rally/_release_flow/**` should own
    the release helper stack once added.
- Existing patterns to reuse:
  - Rally's packaged-runtime proof and workspace-only runtime path stay in
    place as foundation.
  - Doctrine's `Makefile`, `release_flow.py`, `_release_flow/*`, and
    `tests/test_release_flow.py` are the direct parity template.
  - Doctrine's `pr.yml` and `publish.yml` are the workflow-topology template to
    copy, but Rally should swap in Rally-owned proof lanes and drop
    Doctrine-specific lanes such as VS Code.
  - Doctrine's `README.md` plus the `VERSIONING.md` and `CHANGELOG.md` pair are
    the docs-surface template to copy for stable cross-repo package and release
    conventions.
- Prompt surfaces / agent contract to reuse:
  - Not central. This reopened plan is about release operators, version files,
    and packaging truth, not prompt behavior.
- Native model or agent capabilities to lean on:
  - Not central here. This is repo-owned release tooling and docs work.
- Existing grounding / tool / file exposure:
  - `uv build`, `uv run pytest tests/unit -q`, and the clean temp-environment
    packaged-install proof already give Rally the release artifact checks it
    needs.
  - Doctrine's Make targets, helper modules, and release tests already give
    Rally a concrete parity blueprint instead of an abstract design target.
- Duplicate or drifting paths relevant to this change:
  - Rally currently teaches one release path in `docs/VERSIONING.md` and
    `.github/workflows/publish.yml`, while Doctrine teaches a different one in
    `docs/VERSIONING.md` and `Makefile`.
  - Rally currently derives versions dynamically, while Doctrine requires
    explicit package-version truth in `pyproject.toml`.
  - Rally currently uses a free-form changelog, while Doctrine uses a fixed
    release-section schema.
  - Rally currently lacks Doctrine's short docs-map pattern in `README.md` for
    release history, version policy, support, and security surfaces.
  - Rally currently has no repo-owned release-flow tests, while Doctrine does.
  - Rally currently has no PR CI split, no CODEOWNERS, and no public security
    docs, while Doctrine's hardening plan now treats those as first-class trust
    surfaces.
  - `tool.uv.sources.doctrine = { path = "../doctrine", editable = true }` is
    still only a contributor convenience and must stay outside Rally's public
    release contract.
- Capability-first opportunities before new tooling:
  - The packaged-runtime and external-user proof work is already done. The next
    leverage point is not more packaging machinery; it is copying Doctrine's
    existing release helper shape.
- Behavior-preservation signals already available:
  - `uv run pytest tests/unit -q` already protects core workspace, flow build,
    flow load, and runner behavior.
  - `uv build` plus `tests/integration/test_packaged_install.py` already
    protect the built-artifact path.
  - Doctrine's `tests/test_release_flow.py` gives a concrete parity target for
    Rally's future release-flow tests.

## 3.3 Decision gaps that must be resolved before implementation

- The user resolved the key gap by reopening the plan with an explicit new
  requirement: exact convention parity with Doctrine.
- That means:
  - Rally should stop using `setuptools-scm` as the public release-version
    source.
  - Rally should adopt explicit `[project].version` truth in `pyproject.toml`.
  - Rally should add the same public Make targets Doctrine uses.
  - Rally should add a repo-owned `release_flow` helper stack that mirrors
    Doctrine's module split.
  - Rally should move away from tag-push-only GitHub Actions as the canonical
    public release flow and mirror Doctrine's `release.published` plus
    `workflow_dispatch` publish workflow shape.
  - Rally should mirror Doctrine's release doc and changelog shape.
  - Rally should mirror Doctrine's README docs-map pattern and public
    support/security file ownership, while keeping Rally-specific wording honest
    to Rally's own current product state.
  - Rally should document real Rally narrow support-surface versions instead of
    inventing a fake language-version line.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Rally now has the right packaged-runtime base:
  - `src/rally/_bundled/**` ships built-ins inside the wheel
  - `tools/sync_bundled_assets.py` owns bundle sync and drift checks
  - `tests/integration/test_packaged_install.py` proves the installed artifact
    path from a clean temp environment
- Rally's public release surfaces still differ from Doctrine's:
  - `pyproject.toml` uses `dynamic = ["version"]` and `setuptools-scm`
  - `docs/VERSIONING.md` is a lighter Rally-local version policy
  - `CHANGELOG.md` is a generic changelog, not a fixed release-entry file
  - `README.md` does not yet use Doctrine's tighter docs-map and release-doc
    routing pattern
  - `.github/workflows/publish.yml` is the current public release owner
- Rally's GitHub repo surfaces are still sparse:
  - no `.github/CODEOWNERS`
  - no `.github/PULL_REQUEST_TEMPLATE.md`
  - no `.github/dependabot.yml`
  - no PR CI workflow
  - no public `SECURITY.md`
  - no public `SUPPORT.md`
- Rally has no `Makefile`, no `src/rally/release_flow.py`, and no
  `src/rally/_release_flow/**` helper stack.
- Rally already has real narrow support-surface versions that should become
  first-class release doc truth:
  - `[tool.rally.workspace].version = 1`
  - compiled agent `contract_version = 1`

## 4.2 Control paths (release and publish)

1. Rally's package version is derived from git state through `setuptools-scm`.
2. Local release guidance in `docs/VERSIONING.md` says to update docs, build,
   run the packaged-install proof, and then push a signed annotated tag.
3. `.github/workflows/publish.yml` owns the public tag push -> build -> verify
   -> publish path.
4. There is no Doctrine-style `release.published` build-and-publish transport
   workflow shape yet, and there is no matching `workflow_dispatch` dry-run
   path.
5. There is no Rally-owned `release-prepare` worksheet command.
6. There is no Rally-owned `release-tag` preflight command.
7. There is no Rally-owned `release-draft` GitHub draft-release step.
8. There is no Rally-owned `release-publish` step that reviews draft notes and
   then publishes.
9. The packaged-install proof is good, but it lives beside the release flow
   rather than inside a Doctrine-style release helper system.
10. Rally has no stable required PR checks or split workflow names to anchor a
   ruleset on `main`.
11. Rally has no CODEOWNERS, PR template, or public security/support docs to
    signal maintained-project posture.

## 4.3 Object model + key abstractions

- Rally has one public release line today, but it is derived dynamically rather
  than declared explicitly.
- Rally has one explicit Doctrine floor: `doctrine>=1.0.1,<2`.
- Rally already has real narrow support-surface versions:
  - workspace manifest version
  - compiled agent contract version
- Rally has no repo-owned release models for:
  - parsed release tags
  - release plans and worksheets
  - fixed changelog release entries
  - support-surface version state
  - GitHub draft/publish command building
- Rally has no repo-owned model yet for:
  - stable required PR checks
  - label taxonomy
  - CODEOWNERS routing
  - security and support ownership
  - README docs-map ownership for release and trust surfaces
- Rally's runtime package and external-user proof are good enough to serve as a
  stable base while the release system is replaced.

## 4.4 Observability + failure behavior today

- Bundle drift and artifact-install failures now fail loud.
- Release-flow drift still fails late:
  - version/doc shape mismatches are found by human review
  - signing and tag verification are not gated by Rally-owned commands
  - GitHub draft-release behavior is not exercised locally
  - changelog format drift is not machine-checked
  - Rally-vs-Doctrine convention drift is visible only by comparison
- GitHub-hardening drift also fails late:
  - there is no ruleset-backed required-check contract on `main`
  - no machine-owned CODEOWNERS or Dependabot config exists
  - action pinning and permissions are not reviewed under a stable policy
  - the README/docs/support/security front door cannot yet drift-check against
    the same stable cross-repo pattern Doctrine is converging on

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
- Add one Doctrine-style Rally release helper stack:
  - `Makefile`
  - `src/rally/release_flow.py`
  - `src/rally/_release_flow/common.py`
  - `src/rally/_release_flow/models.py`
  - `src/rally/_release_flow/parsing.py`
  - `src/rally/_release_flow/tags.py`
  - `src/rally/_release_flow/ops.py`
  - `tests/unit/test_release_flow.py`
- Add one Doctrine-aligned GitHub hardening surface set:
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/dependency-review.yml`
  - `.github/workflows/scorecards.yml`
  - `SECURITY.md`
  - `SUPPORT.md`
- Add one Doctrine-shaped Rally publish transport workflow:
  - `.github/workflows/publish.yml`
- Rewrite Rally's public release files to Doctrine shape:
  - `pyproject.toml` with explicit `[project].version`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `CONTRIBUTING.md` if it contains release instructions
- Rewrite `README.md`, `SECURITY.md`, and `SUPPORT.md` so the public docs map,
  release links, and help paths follow the same stable cross-repo pattern.

## 5.2 Control paths (future)

1. Operator updates code and docs, including `pyproject.toml`,
   `docs/VERSIONING.md`, and `CHANGELOG.md`.
2. Maintainer keeps GitHub repo settings aligned with the plan:
   - ruleset-protected `main`
   - require PR before merge
   - require conversation resolution
   - require strict status checks
   - require linear history
   - block force pushes and deletions
   - zero required approvals
   - squash-only merges
   - allow auto-merge
   - auto-delete merged branches
3. Pull requests land through split stable checks such as:
   - `.github/workflows/pr.yml` is the one PR workflow file, matching
     Doctrine's workflow split and concurrency shape.
   - Rally's PR jobs are Rally-specific, but they stay stable and
     human-readable, for example:
     - `bundled-assets`
     - `unit`
     - `packaged-install`
   - `security / dependency-review`
4. Operator runs `make release-prepare RELEASE=vX.Y.Z CLASS=... CHANNEL=...`.
   - Rally validates release tag shape, release class, package-version mapping,
     workspace version state, compiled contract version state, Doctrine floor
     state, and changelog entry shape.
   - Rally prints a Doctrine-style worksheet with exact next commands.
5. Operator runs the required proof commands.
6. Operator runs `make release-tag RELEASE=vX.Y.Z CHANNEL=...`.
   - Rally requires a clean worktree.
   - Rally requires a git signing key.
   - Rally creates and pushes one signed annotated tag.
7. Operator runs `make release-draft RELEASE=vX.Y.Z CHANNEL=... PREVIOUS_TAG=auto`.
   - Rally requires the pushed tag to be annotated and to pass
     `git verify-tag`.
   - Rally creates a GitHub draft release through `gh release create`.
8. Operator reviews the GitHub draft release.
9. Operator runs `make release-publish RELEASE=vX.Y.Z`.
   - Rally publishes the reviewed GitHub draft release with
     `gh release edit --draft=false`.
10. GitHub `publish.yml` runs on `release.published`.
   - The workflow checks out the release tag.
   - The workflow builds wheel and sdist.
   - The workflow runs the external-user smoke proof from built artifacts.
   - The workflow uploads those assets to the published GitHub release.
   - The workflow publishes the same artifacts to PyPI with Trusted Publishing.
   - The same workflow also supports `workflow_dispatch` with the Doctrine-style
     dry-run shape:
     - `ref`
     - `publish_target = none|testpypi|pypi`
11. The packaged-runtime and external-user proof path stays unchanged and
   remains one required verify step inside this operator flow.
12. The one intentional Rally-vs-Doctrine difference is narrow and explicit:
   Rally has no `LANGUAGE_VERSION=` input because Rally does not have a
   Doctrine-style language-version line. The helper reads Rally's real support
   surfaces instead.

## 5.3 Object model + abstractions (future)

- `ReleaseTag` mirrors Doctrine's public tag parsing:
  - stable `vX.Y.Z`
  - beta `vX.Y.Z-beta.N`
  - rc `vX.Y.Z-rc.N`
- `ReleasePlan` mirrors Doctrine's worksheet model, but Rally's real
  support-surface version lines replace Doctrine's language-version state:
  - current package version
  - requested package version
  - workspace version state
  - compiled contract version state
  - Doctrine floor state
  - Doctrine package constraint state
  - published-release workflow name
  - required PR check names
  - README docs-map state
  - changelog status
- `ReleaseEntry` mirrors Doctrine's parsed changelog/release-note header shape.
- `common.py`, `models.py`, `parsing.py`, `tags.py`, and `ops.py` mirror
  Doctrine's helper split so a Doctrine user can find the same jobs in Rally.
- The packaged-runtime services stay in place and are not re-abstracted during
  this release-system cutover.

## 5.4 Invariants and boundaries

- Public release version truth lives in explicit `[project].version`.
- Public release tags are signed annotated tags only.
- GitHub release publication only happens from a verified pushed public tag.
- Rally's public release doc and changelog keep the same section shape and
  release header discipline Doctrine uses.
- Rally does not invent a fake language-version line.
- Rally documents the real support-surface versions it already has:
  workspace manifest version and compiled contract version.
- Rally's only allowed release-flow extension beyond Doctrine is the
  release-published build-and-PyPI workflow that exists because Rally ships a
  PyPI package.
- Rally copies Doctrine's workflow topology and docs routing pattern, but not
  doctrine-specific lanes or stale pre-1.0 wording.
- The built-artifact external-user proof stays a release gate.
- The explicit Doctrine floor stays a release gate.
- The canonical public release path is repo-owned and operator-driven, not tag
  push driven through GitHub Actions.
- Required PR checks use stable human-readable names so a GitHub ruleset can
  anchor them without drift.

## 5.5 UI surfaces (ASCII mockups, if UI work)

- Operator-facing release flow:

```text
make release-prepare ...  -> worksheet + required updates + exact proof commands
run proof                 -> bundle check + unit suite + built-artifact proof
make release-tag ...      -> signed annotated tag + push
make release-draft ...    -> verified GitHub draft release
review draft release
make release-publish ...  -> publish GitHub release
publish.yml              -> build assets + smoke test + attach + publish
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File / Symbol | Current owner | Current problem | Change needed | Why | Future owner / contract | Proof |
| ---- | ------------- | ------------- | --------------- | ------------- | --- | ----------------------- | ----- |
| Public version truth | `pyproject.toml` | dynamic version via `setuptools-scm` | Rally package version does not follow Doctrine's explicit package-version rule | Replace `dynamic = ["version"]` with explicit `version = "X.Y.Z"` and remove `setuptools-scm` | Exact operator parity needs the same visible version truth Doctrine uses | `pyproject.toml` owns Rally public package version and Doctrine floor | release-flow unit tests + `uv build` |
| Release command surface | `Makefile` | missing | Rally has no Doctrine-style public release commands | Add `release-prepare`, `release-tag`, `release-draft`, and `release-publish`, plus adjacent `setup`, `test`, `tests`, `verify`, and `check` targets where they help parity | Doctrine users should see the same command family | `Makefile` is Rally's public repo release front door | local make-target proof |
| Release CLI | `src/rally/release_flow.py` | missing | Rally has no repo-owned release helper CLI | Add the same `prepare`, `tag`, `draft`, and `publish` subcommands Doctrine uses | Rally needs one repo-owned command family behind the Make targets | `python -m rally.release_flow ...` | unit tests |
| Release common helpers | `src/rally/_release_flow/common.py` | missing | shared subprocess/error handling would otherwise sprawl | Add common checked-command helpers and release-specific failure formatting | Keep the release helper small and consistent | shared helper module | unit tests |
| Release models | `src/rally/_release_flow/models.py` | missing | no typed owner for parsed tags, release plans, or support-surface state | Add Rally release models mirroring Doctrine's shape | Keep release parsing and worksheet rendering coherent | `ReleaseTag`, `ReleasePlan`, `ReleaseEntry`, support-surface state models | unit tests |
| Release parsing | `src/rally/_release_flow/parsing.py` | missing | Rally has no parser for fixed changelog entries, current support-surface versions, or package-version truth | Add parsers for `CHANGELOG.md`, `docs/VERSIONING.md`, `pyproject.toml`, workspace version, and compiled contract version | Doctrine-style release gates need machine-readable file truth | parsing helpers own file-state truth | unit tests |
| Tag rules | `src/rally/_release_flow/tags.py` | missing | Rally has no repo-owned tag parsing, signing checks, or pushed-tag checks | Mirror Doctrine's tag parsing and `git verify-tag` preflight logic | Signed public release rules must fail loud before GitHub publication | tag helpers own release-tag and signing checks | unit tests |
| Release operations | `src/rally/_release_flow/ops.py` | missing | Rally has no worksheet, tag, draft, or publish operations | Mirror Doctrine's release ops and extend them with Rally artifact attach + PyPI publish steps | One operator flow should own the whole release | ops own prepare/tag/draft/publish behavior | unit tests + manual rehearsal |
| Release tests | `tests/unit/test_release_flow.py` | missing | Rally has no release-flow preflight coverage | Add Doctrine-style release tests adapted to Rally's real support surfaces | Release drift should fail in unit tests, not only at ship time | release-flow test suite | `uv run pytest tests/unit/test_release_flow.py -q` |
| Version policy doc | `docs/VERSIONING.md` | Rally-local simplified doc | section order and payload do not match Doctrine | Rewrite to Doctrine-style structure, with Rally support-surface lines replacing language-version claims | Users should not learn a second release doc shape | canonical version-policy doc | doc parser tests + review |
| Release history | `CHANGELOG.md` | generic changelog | no fixed public release section schema | Rewrite to Doctrine-style release entries and release-note header lines | Release notes and tags need machine-checked structure | canonical release history | parser tests |
| Public docs | `README.md`, `CONTRIBUTING.md` | mixed release instructions | docs still teach Rally-specific release steps and do not mirror Doctrine's docs-map pattern | Rewrite release guidance around `make release-*`, the Doctrine-style docs map, and the same short versioning/changelog/support/security routing pattern | One front-door operator story | README + contributing docs | manual doc pass |
| PR CI workflow | `.github/workflows/pr.yml` | missing | Rally has no stable PR gate or required-check names | Add a PR workflow with stable job names for bundled-asset drift, unit tests, and packaged-install proof | Rulesets need stable required checks and contributors need visible lanes | canonical PR gate | workflow review + CI run |
| Dependency review workflow | `.github/workflows/dependency-review.yml` | missing | Rally has no repo-owned supply-chain gate on dependency changes | Add `security / dependency-review` using GitHub's dependency review action | Catch vulnerable dependency changes before merge | security workflow | workflow review |
| Scorecards workflow | `.github/workflows/scorecards.yml` | missing | Rally has no periodic supply-chain hardening signal | Add weekly and manual scorecards workflow | Catch permission and action-pinning drift | non-blocking security workflow | workflow review |
| Publish workflow | `.github/workflows/publish.yml` | tag-push publish owner | current workflow owns the whole release path and starts from tag push | Replace it with Doctrine's current publish topology: `release.published` plus `workflow_dispatch`, build from the chosen ref, run temp-project external-user smoke, upload release assets, and publish to TestPyPI or PyPI | Canonical public release path should match Doctrine's operator flow while still shipping Rally artifacts | release transport only | workflow review + rehearsal |
| CODEOWNERS | `.github/CODEOWNERS` | missing | workflow, docs, and release changes have no routing owner | Add maintainer-first CODEOWNERS entries for repo root, docs, workflows, runtime, and authored content roots | GitHub routing and future ruleset growth need explicit owners | code-owner routing file | review |
| PR template | `.github/PULL_REQUEST_TEMPLATE.md` | missing | Rally PRs have no stable release-facing checklist | Add structured sections for summary, user impact, checks run, docs touched, release-note label, and follow-ups | Keeps PR review and release-note hygiene consistent | PR authoring surface | review |
| Dependabot | `.github/dependabot.yml` | missing | Rally has no repo-owned update automation for actions or Python deps | Add updates for GitHub Actions and Python package surfaces | Keeps pinned actions and package inputs moving | dependency update config | review |
| Security docs | `SECURITY.md`, `SUPPORT.md` | missing | Rally has no public security or support contract | Add the same public file pair Doctrine now ships, but write Rally-specific wording that matches Rally's real maturity and support truth | Public trust surface should match a maintained project without copying stale doctrine copy | public trust docs | review |
| Packaged-install proof | `tests/integration/test_packaged_install.py` | existing artifact proof | already good, but not yet wired into a Doctrine-style worksheet | Keep it and make it one required release verify command | External-user proof must stay a gate under the new flow | built-artifact proof stays canonical | integration test |
| Support-surface version truth | `pyproject.toml`, `src/rally/services/flow_loader.py`, `src/rally/domain/flow.py` | scattered current truth | Rally's workspace and compiled-contract versions are real but under-documented | Pull them into version docs and release-prepare parsing | Exact parity needs real narrow support-surface lines | version docs + parsing helpers | unit tests |
| Docs-map parity | `README.md`, `docs/VERSIONING.md`, `CHANGELOG.md`, `SECURITY.md`, `SUPPORT.md` | scattered public docs | Rally lacks Doctrine's stable docs entry pattern for release and trust surfaces | Make the public docs row and support/security references line up across the repo | Stable cross-repo conventions should be visible from the first page | public docs entry surface | manual doc pass |
| Repo settings | GitHub repo settings and rulesets | manual repo state | Rally currently has no documented hardened repo settings target | Add maintainer-first ruleset, squash-only merge policy, auto-merge, branch deletion cleanup, private vulnerability reporting, automated security fixes, and CodeQL default setup baseline | Public repo trust should not live in tribal knowledge | ops runbook + repo settings | manual settings audit |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - packaged-runtime foundation stays under `src/rally/_bundled/**`,
    `tools/sync_bundled_assets.py`, and `tests/integration/test_packaged_install.py`
  - public release ownership moves to `Makefile`,
    `src/rally/release_flow.py`, and `src/rally/_release_flow/**`
  - public release doc ownership stays in `docs/VERSIONING.md` and
    `CHANGELOG.md`
- Deprecated flows:
  - `dynamic = ["version"]` in Rally `pyproject.toml`
  - `[tool.setuptools_scm]`
  - `.github/workflows/publish.yml` as Rally's canonical public release path
- New repo-owned surfaces to add:
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/dependency-review.yml`
  - `.github/workflows/scorecards.yml`
  - `SECURITY.md`
  - `SUPPORT.md`
- Delete list:
  - Rally-only release wording that points users at tag-push GitHub Actions as
    the main public release path
  - generic changelog release sections that do not match Doctrine's fixed
    release-entry shape
  - any remaining doc wording that treats Rally's release version like a
    Doctrine language version
  - mutable action-tag references in required workflows once SHA pinning lands
- Live docs/comments/instructions to update or delete:
  - `README.md`
  - `CONTRIBUTING.md`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - release helper docstrings and help text
  - `.github/workflows/publish.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/dependency-review.yml`
  - `.github/workflows/scorecards.yml`
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - `SECURITY.md`
  - `SUPPORT.md`
- Behavior-preservation signals for refactors:
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `uv run pytest tests/integration/test_packaged_install.py -q`
  - new `tests/unit/test_release_flow.py`

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Version truth | `pyproject.toml`, `docs/VERSIONING.md`, `CHANGELOG.md` | explicit release-version truth with fixed file roles | Prevents package-version, tag, and doc drift | include |
| Release operator flow | `Makefile`, `src/rally/release_flow.py`, `src/rally/_release_flow/**` | Doctrine-style `prepare/tag/draft/publish` flow | Prevents Rally from teaching a second public release grammar | include |
| GitHub publication | release helper ops, `.github/workflows/publish.yml`, `gh` commands | Doctrine-style draft-review-publish plus release-published transport workflow | Prevents silent drift between tags, releases, release assets, and published artifacts | include |
| GitHub governance | ruleset, merge policy, CODEOWNERS, PR template | maintainer-first protected main | Prevents direct drift around review and required checks | include |
| PR CI | `.github/workflows/pr.yml`, required check names | split stable lanes with strict permissions and pinned actions | Prevents ruleset drift and opaque CI failures | include |
| Security hardening | dependabot, dependency review, scorecards, CodeQL, vulnerability reporting | repo trust surfaces as first-class release support | Prevents supply-chain and maintenance drift | include |
| Public docs map | README plus versioning/changelog/support/security docs | short stable docs routing from the repo front door | Prevents release and trust docs from drifting into buried side paths | include |
| Support-surface versions | workspace version, compiled contract version | explicit narrow version lines in docs and parser checks | Prevents hidden support-surface breaks from shipping as trivia | include |
| Packaged-runtime proof | bundle sync + built-artifact install proof | keep current artifact gate intact during release-flow rewrite | Prevents the release-system rewrite from regressing the user-facing install path | include |
| Contributor-only convenience | `pyproject.toml` `[tool.uv.sources]` | keep local Doctrine path as dev-only | Prevents local sibling checkout shortcuts from becoming public release law | exclude |
| Doctrine-only hardening items | VS Code lane, package rename, merge queue | do not cargo-cult surfaces Rally does not have | Prevents fake parity through irrelevant work | exclude |
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

Status: REOPENED (audit found missing code work)

Missing (code):
- The split PR workflow cutover is real, but the last planned hardening step
  is still missing. Phase 4 said to make CodeQL a required gate after the
  baseline turned green.
- On 2026-04-14, `gh run list --workflow CodeQL --branch main --limit 10
  --json ...` showed successful `main` runs, but
  `gh api repos/aelaguiz/rally/rulesets/15059522` still did not require any
  CodeQL check.
- PR `#5` merged while `Analyze (python)` failed, so the live gate is still
  weaker than the approved Phase 4 target.

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
- The active `main` ruleset still requires the same stable required checks on
  the default branch.

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

Status: COMPLETED

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

Status: REOPENED (audit found missing code work)

Missing (code):
- The local verify path, publish dry run, and host-repo manual path are real,
  but the final readiness proof still sits on the weaker pre-CodeQL ruleset.
- Phase 6 required the hardened repo settings to line up with the named
  required checks after the workflow split. Because CodeQL is not required
  yet, PR `#5` does not satisfy that final live-gate proof.
- After Phase 4 lands the CodeQL required gate, rerun one live PR proof under
  the finished ruleset and then refresh the readiness proof.

Completion proof already landed for the rest of this phase:
- Local release proof stayed green after the clean-checkout repair:
  - `make verify`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
- The live PR gate proof completed through merged PR `#5` on 2026-04-14.
- The live publish transport proof completed through workflow run
  `24403594896` on `main` with `publish_target=none`.
- The README host-repo path was followed by hand in a temp external workspace
  from the built wheel:
  - installed `rally==0.1.0` plus Doctrine `v1.0.1` into an isolated venv
  - ran `rally run demo` with the venv `bin/` on `PATH`
  - confirmed Rally created `DMO-1`, synced `stdlib/rally/`,
    `skills/rally-kernel/`, and `skills/rally-memory/` into the host repo,
    and stopped cleanly at the documented `home/issue.md` step

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
