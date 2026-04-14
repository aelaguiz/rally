# Changelog

All notable Rally release changes live here.
This file is the portable release history. `docs/VERSIONING.md` is the
evergreen policy guide.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

Use this section for work that is not public yet.

### Added
- Added repo-owned release helpers under `src/rally/release_flow.py` and
  `src/rally/_release_flow/**`.
- Added `Makefile` targets for `release-prepare`, `release-tag`,
  `release-draft`, and `release-publish`.
- Added repo-owned package release metadata under `src/rally/_package_release.py`.
- Added `Makefile` targets for `build-dist` and `verify-package`.
- Added split GitHub workflows for PR checks, dependency review, scorecards,
  and release publishing.
- Added public `SUPPORT.md` and `SECURITY.md` files.

### Changed
- Switched Rally package version truth to explicit `[project].version` in
  `pyproject.toml`.
- Moved package-index environment names under `[tool.rally.package]` so the
  workflow, release helper, and docs all read one package-publish owner path.
- Rewrote Rally's versioning and release docs around the Doctrine-style public
  release model.
- Reworked `publish.yml` to read package metadata first and use the same
  environment names and project URLs for TestPyPI and PyPI publishes.

### Fixed
- Switched Rally's public Doctrine dependency to
  `doctrine-agents>=1.0.2,<2`, which matches the first clean renamed-package
  Doctrine release on PyPI.
- Removed the package-proof path that preinstalled Doctrine from git before
  installing Rally, so `make verify-package`, `make verify`, and CI now prove
  clean consumer installs.

When you cut a public release:

1. Copy the release entry template below.
2. Replace the placeholders.
3. Move the real change notes into the new release section.
4. Leave `## Unreleased` at the top for the next cycle.

Public release entries must replace every placeholder before `make release-tag`
or `make release-draft` runs. The helper rejects placeholder release-header
text and breaking releases with no real upgrade steps.

### Release Entry Template

```md
## vX.Y.Z - YYYY-MM-DD

Release kind: Non-breaking
Release channel: stable
Release version: vX.Y.Z
Affected surfaces: ...
Who must act: ...
Who does not need to act: ...
Upgrade steps: ...
Verification: ...
Support-surface version changes: none

### Added
- Describe backward-compatible user-facing additions.

### Changed
- Describe user-visible behavior or workflow changes.

### Deprecated
- Describe soft-deprecated public surfaces and early move guidance.

### Removed
- Describe removed public surfaces.

### Fixed
- Describe important fixes that matter to users or maintainers.

### YANKED
- Use this only when a bad public release was superseded later.
```

## v0.1.0 - 2026-04-14

Release kind: Non-breaking
Release channel: stable
Release version: v0.1.0
Affected surfaces: packaged runtime assets, explicit package metadata, the public release flow, and external host-repo setup.
Who must act: maintainers cutting Rally releases and users installing Rally as a Python package.
Who does not need to act: users who stay on unreleased commits and users who are not consuming Rally through package installers yet.
Upgrade steps: Install `rally-agents` v0.1.0. The CLI stays `rally`. If you were running from a source checkout only, switch to the published package and follow the README host-repo setup flow.
Verification: make verify
Support-surface version changes: workspace manifest 1 (unchanged); compiled contract version 1 (unchanged); minimum Doctrine release v1.0.1

### Added
- Shipped Rally's packaged built-ins under `src/rally/_bundled/` so installed
  runtimes no longer depend on a Rally source checkout.
- Added a built-artifact external-user proof that installs the wheel, runs
  `rally --help`, runs `rally run demo`, and verifies host `doctrine.emit_docs`
  stays inside the host project root.
- Added a repo-owned public release flow with `make release-prepare`,
  `make release-tag`, `make release-draft`, and `make release-publish`.
- Added public support and security docs plus GitHub workflow hardening
  surfaces for release and dependency review.

### Changed
- Moved Rally release policy and compatibility guidance into the canonical
  `docs/VERSIONING.md` and `CHANGELOG.md` pair.
- Switched Rally package metadata to explicit `[project].version`.
- Published Rally on package indexes under distribution name `rally-agents`
  while keeping the import package and CLI name `rally`.
- Replaced the tag-push-only publish path with a GitHub release
  publish workflow that rebuilds artifacts, reruns the external-user smoke
  proof, uploads release assets, and can publish to package indexes through
  Trusted Publishing.

### Fixed
- Stopped Rally-native stdlib support files from escaping host project roots in
  external Doctrine emit targets.
