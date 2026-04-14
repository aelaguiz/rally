# Versioning

This file is the canonical home for Rally versioning, release rules, and
Doctrine compatibility guidance.

Current public Rally release version: v0.1.0
Current Rally package version: 0.1.1
Current workspace manifest version: 1
Current compiled agent contract version: 1
Current minimum Doctrine release: v1.0.2
Current supported Doctrine package line: doctrine-agents>=1.0.2,<2

## The Version Lines

### Rally Release Version

The Rally release version tracks one public shipped release or prerelease.

- Use signed annotated tags and matching GitHub releases as the public release
  record.
- Stable tags use `vX.Y.Z`.
- Beta tags use `vX.Y.Z-beta.N`.
- RC tags use `vX.Y.Z-rc.N`.
- Release major bumps cover any public surface that now needs user action,
  even when Rally's workspace or compiled-contract lines stay the same.
- Release minor bumps cover backward-compatible public additions and soft
  deprecations.
- Release patch bumps cover internal-only or other non-breaking public fixes.

### Narrow Support-Surface Versions

Rally also ships narrower version lines.

- `version` under `[tool.rally.workspace]` only versions the Rally workspace
  manifest contract. It is not the Rally release version.
- `contract_version` in compiled `AGENTS.contract.json` files only versions the
  compiled agent contract shape. It is not the Rally release version.
- The package metadata version in `pyproject.toml` versions the published
  Python package. It is not a Doctrine release or language version.
- `import_name`, `pypi_environment`, and `testpypi_environment` under
  `[tool.rally.package]` are part of the package publish path. Keep them
  explicit in `pyproject.toml`.
- The published distribution name is `rally-agents`, while the Python import
  package and CLI stay `rally`.
- The Doctrine dependency floor and package line only describe which public
  Doctrine release line Rally requires. They are not Rally release versions.
- For public stable releases, `vX.Y.Z` maps to package version `X.Y.Z`.
- For public beta releases, `vX.Y.Z-beta.N` maps to package version `X.Y.ZbN`.
- For public rc releases, `vX.Y.Z-rc.N` maps to package version `X.Y.ZrcN`.
- `make release-tag` and `make release-draft` fail if `[project].version` does
  not match that release-package version.

For the workspace manifest surface, use [README.md](../README.md).
For the compiled contract surface, use
[docs/RALLY_MASTER_DESIGN_2026-04-12.md](RALLY_MASTER_DESIGN_2026-04-12.md).

## Release Classes

Every public release uses one release class.

- `internal`: docs-only, tooling-only, packaging-only, refactor, or cleanup
  work that does not change a shipped public surface. Release kind:
  `Non-breaking`.
- `additive`: backward-compatible public additions. Release kind:
  `Non-breaking`.
- `soft-deprecated`: behavior still works, but Rally now tells users what to
  move away from and how to move early. Release kind: `Non-breaking`.
- `breaking`: any shipped public surface now needs user action. This includes
  CLI breaks, workspace-layout breaks, compiled-contract breaks, or external
  install and upgrade steps that now need human action. Release kind:
  `Breaking`.

Breaking releases outside the workspace or compiled-contract surface may keep
those narrower version lines unchanged.

## Required Breaking-Change Payload

Every breaking change must say:

- affected surface
- old behavior
- new behavior
- first affected version
- who must act
- who does not need to act
- exact upgrade steps
- before and after example when that helps
- verification step

Do not ship vague "this might break you" wording.

## Changelog Entry Shape

Before `make release-tag` or `make release-draft`, `CHANGELOG.md` must contain
one matching release section:

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
```

Beta and RC releases use the same shape, but `Release channel:` becomes
`beta.N` or `rc.N`, and `Release version:` uses the prerelease tag.

The helper reads that header back out of `CHANGELOG.md` for tag messages and
GitHub draft notes. Keep it exact.
Replace every placeholder before you tag or draft a public release. The helper
rejects `fill this in`, `update for this release`, `...`, and similar
placeholder text in public release entries. Breaking releases must carry real
upgrade steps.

## Release Process

1. Update `docs/VERSIONING.md` when the release rules or Doctrine
   compatibility guidance changed.
2. Update `pyproject.toml`. Set `[project].version` to the package version for
   the requested public release.
3. Update `CHANGELOG.md`. Add the next release section with the fixed release
   header and curated change notes.
4. Update the touched live docs and contributor instructions when the release
   changes their truth.
5. Run `make release-prepare RELEASE=vX.Y.Z CLASS=internal|additive|soft-deprecated|breaking CHANNEL=stable|beta|rc`.
6. Run the required proof for the touched surfaces. Every public release must
   also run `uv run pytest tests/unit/test_package_release.py -q`,
   `make build-dist`, `make verify-package`, and `make verify`.
7. Run `make release-tag RELEASE=vX.Y.Z CHANNEL=stable|beta|rc`.
8. Run `make release-draft RELEASE=vX.Y.Z CHANNEL=stable|beta|rc PREVIOUS_TAG=auto`.
9. Review the GitHub draft release body.
10. Run `make release-publish RELEASE=vX.Y.Z`.
11. The GitHub release publish workflow builds dist artifacts, smoke tests an
    external wheel and sdist install, reruns Rally's broader packaged-install
    proof, uploads release assets, and can publish through GitHub environments
    plus Trusted Publishing.
12. Before the first TestPyPI or PyPI publish for package `rally-agents`, stop and
    finish the setup checklist below.

The helper prints the fixed worksheet, the exact release-note header, the exact
changelog header, and the next commands to run.

## First Package-Index Publish Setup

Do this once before the first real TestPyPI or PyPI publish for `rally-agents`.

1. Create or confirm the GitHub environments in `aelaguiz/rally`.
   - `testpypi` should exist with no protection rules and no deployment branch
     policy. This is the low-friction rehearsal lane.
   - `pypi` should exist with one required reviewer: `aelaguiz`.
   - `pypi` should keep `prevent_self_review = false` so the solo maintainer
     flow does not deadlock.
   - `pypi` should keep `can_admins_bypass = false` so the approval gate stays
     real.
   - `pypi` should keep no deployment branch policy, which matches Doctrine's
     current repo convention.
   - If either environment is missing or reset, recreate it with that exact
     config.
2. Register the TestPyPI trusted publisher for `rally-agents`.
   - If the `rally-agents` project already exists on TestPyPI, open that project and
     go to `Manage -> Publishing`.
   - If the `rally-agents` project does not exist on TestPyPI yet, create a pending
     publisher for project name `rally-agents`.
   - Add a GitHub Actions publisher with:
     - owner: `aelaguiz`
     - repository name: `rally`
     - workflow name: `.github/workflows/publish.yml`
     - environment name: `testpypi`
3. Register the PyPI trusted publisher for `rally-agents`.
   - If the `rally-agents` project already exists on PyPI, open that project and go
     to `Manage -> Publishing`.
   - If the `rally-agents` project does not exist on PyPI yet, create a pending
     publisher for project name `rally-agents`.
   - Add a GitHub Actions publisher with:
     - owner: `aelaguiz`
     - repository name: `rally`
     - workflow name: `.github/workflows/publish.yml`
     - environment name: `pypi`
4. Keep the workflow and repo metadata aligned.
   - `pyproject.toml` must keep `[tool.rally.package].testpypi_environment =
     "testpypi"` and `[tool.rally.package].pypi_environment = "pypi"`.
   - `.github/workflows/publish.yml` must stay the workflow file registered
     with both publishers.
5. Prove the transport before the first real publish.
   - Run one dry run:
     `gh workflow run publish.yml --ref <ref> -f ref=<ref> -f publish_target=none`
   - Then do the first real TestPyPI publish from a reviewed ref before the
     first real PyPI publish.

Do not change the environment names, repo, or workflow path in one place and
forget the others. Trusted Publishing matches those values exactly.

## Signed Tag And GitHub Rules

- Public beta, rc, and stable tags must be signed annotated tags.
- `make release-tag` fails if the git worktree is dirty or tag signing is not
  configured.
- `make release-tag` and `make release-draft` fail if `[project].version` in
  `pyproject.toml` does not match the requested release's package version.
- `make release-draft` and `make release-publish` fail if the current public
  release tag is missing, lightweight, fails `git verify-tag`, is not pushed
  to `origin`, or points to a different tag object on `origin` than the
  verified local tag.
- Beta and RC GitHub releases must be marked as prereleases and must not be
  marked as the latest release.
- Stable releases publish from signed annotated `vX.Y.Z` tags.
- Every public release must say whether it is `Breaking` or `Non-breaking`.
- Stable public releases are immutable once published.

## Doctrine Compatibility

- Rally depends on one explicit minimum Doctrine public release. Today that
  floor is `v1.0.2`.
- Rally's public package metadata must keep `doctrine-agents>=1.0.2,<2` until the
  compatibility policy changes in the same release.
- If the Doctrine floor changes, update all of these together:
  - `pyproject.toml`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `tests/integration/test_packaged_install.py`
- `make verify-package` must prove clean wheel and sdist installs from fresh
  temp environments with no manual Doctrine preinstall.
- `make verify` must keep Rally's richer host-workspace packaged-install proof
  green on top of that clean-install smoke.
- If an older env or lockfile still points at package `doctrine`, refresh it
  to `doctrine-agents>=1.0.2,<2`.
- Rally's release version is not Doctrine's release version and not Doctrine's
  language version.

## Bad Release Correction

If a public release is wrong:

- do not move a stable tag
- do not replace stable release assets in place
- fix forward with a new version
- mark the older release as `YANKED` or superseded in `CHANGELOG.md`
- update GitHub release notes only to clarify the public record

## Breaking-Change Duties

- Do not ship silent breakage.
- If a change breaks host-repo setup, workspace layout, `rally` CLI behavior,
  compiled contract files, or another stable public surface, update this file
  in the same change.
- Say who is affected.
- Say what changed.
- Give exact upgrade steps.
- Keep code, docs, release notes, and contributor instructions aligned.
- Keep the built-artifact install proof green when shipped packaging or release
  behavior changes.

## What Not To Infer

- Do not infer Doctrine language compatibility from the Rally release version.
- Do not infer Doctrine language compatibility from Rally's
  `contract_version`.
- Do not infer Rally release compatibility from `[tool.rally.workspace].version`
  alone.
- Do not treat the package metadata version in `pyproject.toml` as the
  Doctrine release or language version. It only versions the published Rally
  Python package.

## Related Docs

- [../README.md](../README.md): repo entry docs
- [../CHANGELOG.md](../CHANGELOG.md): portable release history
- [../SUPPORT.md](../SUPPORT.md): support paths
- [../SECURITY.md](../SECURITY.md): private vulnerability reporting
- [RALLY_MASTER_DESIGN_2026-04-12.md](RALLY_MASTER_DESIGN_2026-04-12.md):
  current runtime design
