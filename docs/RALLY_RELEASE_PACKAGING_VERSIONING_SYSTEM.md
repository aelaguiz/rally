---
title: "Rally - Release Packaging Versioning System"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - README.md
  - CHANGELOG.md
  - CONTRIBUTING.md
  - docs/VERSIONING.md
  - docs/RALLY_MASTER_DESIGN.md
  - pyproject.toml
  - Makefile
  - .github/workflows/publish.yml
  - src/rally/release_flow.py
  - src/rally/_release_flow/parsing.py
  - src/rally/_release_flow/ops.py
  - src/rally/_package_release.py
---

# Summary

This file records the shipped release and package path for Rally.
Use it with `docs/VERSIONING.md`.
If this file and the code disagree, the code wins.

# What Shipped

Rally now ships one public release path that matches Doctrine's shape closely.

- package version truth lives in `[project].version` in `pyproject.toml`
- package publish metadata lives under `[tool.rally.package]`
- the release helper stays front-door through `make release-prepare`,
  `make release-tag`, `make release-draft`, and `make release-publish`
- `make build-dist` builds the wheel and sdist
- `make verify-package` proves the built artifacts install and run outside the
  repo root
- `make verify` keeps the broader Rally proof path
- `.github/workflows/publish.yml` is the one release-owned publish workflow
- root community docs and trust surfaces now match the public repo posture:
  `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`,
  `.github/CODEOWNERS`, and the release workflow set

# Live Rules

## Version Lines

- `docs/VERSIONING.md` is the canonical home for current public version rules,
  current package version, current Doctrine floor, and tag mapping.
- Rally's public release version is not the same thing as the workspace
  manifest version or the compiled contract version.
- The published distribution name is `rally-agents`.
- The Python import package and CLI command stay `rally`.

## Release Shape

- Public releases use signed annotated tags.
- The GitHub release path goes through draft review, not a tag-push-only path.
- The publish workflow builds dist artifacts, runs the package proof, and then
  publishes through the configured GitHub environments and Trusted Publishing
  setup.
- The first package-index publish still depends on the one-time environment and
  publisher setup documented in `docs/VERSIONING.md`.

## Operator Path

The current operator path is:

1. update `pyproject.toml`, `CHANGELOG.md`, and any touched live docs
2. run `make release-prepare RELEASE=... CLASS=... CHANNEL=...`
3. run the proof path, including `make build-dist`, `make verify-package`, and
   `make verify`
4. run `make release-tag RELEASE=... CHANNEL=...`
5. run `make release-draft RELEASE=... CHANNEL=... PREVIOUS_TAG=auto`
6. review the GitHub draft release
7. run `make release-publish RELEASE=...`

# Proof

Current release and package proof lives in these front doors:

- `uv run pytest tests/unit/test_package_release.py -q`
- `uv run pytest tests/unit/test_release_flow.py -q`
- `make build-dist`
- `make verify-package`
- `make verify`

The publish workflow reruns the shipped package and release proof on the
release path.

# Reader Path

- Use `README.md` for the public install and release overview.
- Use `docs/VERSIONING.md` for current version rules and first-publish setup.
- Use `CHANGELOG.md` for release entries.
- Use this file when you need the narrower shipped contract for how Rally ties
  package metadata, release helpers, and publish workflow together.
