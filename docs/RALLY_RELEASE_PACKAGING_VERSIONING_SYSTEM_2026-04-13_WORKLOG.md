# Worklog

Plan doc: /Users/aelaguiz/workspace/rally/docs/RALLY_RELEASE_PACKAGING_VERSIONING_SYSTEM_2026-04-13.md

## Initial entry
- Run started.
- Current phase: Phase 1 - Add one package metadata owner path.
- Loop state armed: `.codex/implement-loop-state.019d89d8-293c-7c73-9895-6764d88aa619.json`

## 2026-04-14 - Package metadata path landed and Phase 3 is at the real stop point
- Added the remaining repo-owned package metadata and smoke-proof files:
  - `pyproject.toml`
  - `src/rally/_package_release.py`
  - `tests/unit/test_package_release.py`
  - `src/rally/_release_flow/parsing.py`
  - `src/rally/_release_flow/ops.py`
  - `Makefile`
- Reworked `.github/workflows/publish.yml` to follow the Doctrine metadata-job
  pattern.
  - added a `metadata` job
  - made the publish jobs read environment names and project URLs from
    package metadata
  - made the build job run `make verify` so the release workflow uses the same
    front-door proof as maintainers
- Applied the GitHub environment setup in `aelaguiz/rally` to match Doctrine's
  live repo convention:
  - `testpypi`: no protection rules
  - `pypi`: required reviewer `aelaguiz`, `prevent_self_review = false`,
    `can_admins_bypass = false`
- Updated the package distribution name to `rally-agents` while keeping the
  import path and CLI name `rally`.
- Rewrote the human release docs so they now teach one front door and one
  explicit first-publish pause:
  - `docs/VERSIONING.md`
  - `README.md`
  - `CONTRIBUTING.md`
  - `CHANGELOG.md`
- Re-ran the required local proof:
  - `uv sync --dev`
  - `uv run pytest tests/unit/test_package_release.py -q`
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - `make verify-package`
  - `make verify`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
- Result: all local proof passed.
- Tried the required remote dry run:
  - `gh workflow run publish.yml --ref feat/rally-package-release-parity -f ref=feat/rally-package-release-parity -f publish_target=none`
- Result: blocked by GitHub because the branch is still local only.
  - error: `HTTP 422: No ref found for: feat/rally-package-release-parity`
- Current phase: Phase 3 - local code and docs are done; waiting for the user
  PyPI publisher setup and a pushed ref for the workflow dry run.

## 2026-04-14 - Publish name corrected to `rally-agents`
- Updated the package distribution name to `rally-agents` after the real PyPI
  and TestPyPI setup confirmed that `rally` was not the publishable project
  name.
- Kept the import package and CLI name as `rally`, which matches the Doctrine
  pattern where distribution name and import name can differ.
- Updated the package metadata, install docs, release worksheet text, release
  tests, and publish-setup checklist to use `rally-agents` where the package
  distribution name matters.
- Fixed the runtime version lookup in `src/rally/__init__.py` so installed
  wheels report the real package version from distribution `rally-agents`.
- Fixed the packaged-install regression to derive the wheel filename from the
  repo-owned package metadata instead of hard-coding `dist/rally-*.whl`.
- Re-ran the renamed package proof:
  - `uv sync --dev`
  - `uv run pytest tests/unit/test_package_release.py -q`
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - `make verify-package`
  - `make verify`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
- Result: all passed with artifacts named `rally_agents-0.1.0*`.

## 2026-04-14 - Doctrine packaging fix confirmed
- Doctrine now publishes package metadata as `1.0.1`, which matches the live
  public release line in `../doctrine/docs/VERSIONING.md`.
- Raised Rally's minimum Doctrine floor to `doctrine>=1.0.1,<2`.
- Removed the temporary `--no-deps` workaround from
  `tests/integration/test_packaged_install.py`.
- Rebuilt Rally artifacts and reran the clean packaged-install proof with
  normal dependency resolution. It passed.
- Re-ran `uv run python tools/sync_bundled_assets.py --check` and
  `uv run pytest tests/unit -q`. Both passed.
- Current phase: Phase 3 - Prove and document the public release path.

## 2026-04-14 - Phase 2 cleanup and release proof refresh
- Removed the last leftover `framework_root` compatibility arguments from the
  runtime path helpers and flow-loading entry points. A repo-wide
  `rg -n "framework_root" src tests tools` now returns no matches.
- Added a unit check that bundle drift ignores Python cache files and confirmed
  the sync tool now passes `--check` even if a stray `__pycache__` file appears
  under `src/rally/_bundled/`.
- Re-synced `src/rally/_bundled/` in normal mode so the local bundle tree is
  clean again.
- Re-ran the release proof path:
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv run pytest tests/integration/test_packaged_install.py -q`
  - `uv build`
- Refreshed artifact inspection after the rebuild:
  - the wheel contains Rally's bundled stdlib and built-in skills
  - the sdist contains `CHANGELOG.md`, `docs/VERSIONING.md`, and the bundled
    assets tree
- Fetched `origin/main` so the latest upstream tip is available locally. Merge
  is still deferred until a safer checkpoint because this implementation branch
  has a large dirty worktree.
- Current phase: Phase 3 - Prove and document the public release path.

## 2026-04-14 - Public Doctrine source and installed CLI proof
- Removed the repo-local Doctrine fallback from
  `tests/integration/test_packaged_install.py`. The packaged-install proof now
  defaults to the public Doctrine tag source
  `git+https://github.com/aelaguiz/doctrine.git@v1.0.1`.
- Extended the packaged-install proof so it now runs the installed `rally`
  console script with `--help` before it syncs built-ins and runs the host
  emit proof.
- Updated `docs/VERSIONING.md` and `.github/workflows/publish.yml` to use that
  same exact Doctrine source for the release proof command.
- Re-ran the full release proof path:
  - `uv sync --dev`
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `RALLY_TEST_DOCTRINE_SOURCE=git+https://github.com/aelaguiz/doctrine.git@v1.0.1 uv run pytest tests/integration/test_packaged_install.py -q`
- Result: all commands passed. The packaged-install proof now covers a real
  installed Rally CLI path plus the in-root host `doctrine.emit_docs` path.
- Current phase: Phase 3 - Prove and document the public release path.

## 2026-04-14 - Installed `rally run demo` proof
- Reworked `tests/integration/test_packaged_install.py` so it no longer uses
  direct bundled-asset sync as the main external-user proof step.
- The packaged-install proof now:
  - installs Doctrine from the public `v1.0.1` git tag source
  - installs the built Rally wheel
  - checks `rally --help`
  - runs `rally run demo` inside a temp host workspace
  - confirms that command creates `runs/active/DMO-1`, leaves the run pending,
    writes the expected run-home logs, and syncs Rally's built-ins into the
    host workspace before stopping for `home/issue.md`
  - keeps the existing `doctrine.emit_docs` proof in the same release slice
- Re-ran the approved Phase 3 proof sequence:
  - `uv run python tools/sync_bundled_assets.py --check`
  - `uv run pytest tests/unit -q`
  - `uv build`
  - `RALLY_TEST_DOCTRINE_SOURCE=git+https://github.com/aelaguiz/doctrine.git@v1.0.1 uv run pytest tests/integration/test_packaged_install.py -q`
- Result: all commands passed with the installed `rally run demo` path in
  place.
- Current phase: Phase 3 - Prove and document the public release path.

## 2026-04-14 - Plan reopened for exact Doctrine convention parity
- Reopened the canonical release-system plan so it no longer stops at
  "good enough standalone Rally release tooling."
- Rewrote the plan North Star, research grounding, target architecture,
  call-site audit, phase plan, verification strategy, rollout plan, and
  runbook around exact Doctrine convention parity.
- Locked the intended parity surfaces:
  - explicit `[project].version`
  - Doctrine-shaped `docs/VERSIONING.md`
  - Doctrine-shaped `CHANGELOG.md`
  - `Makefile` with `release-prepare`, `release-tag`, `release-draft`, and
    `release-publish`
  - repo-owned `src/rally/release_flow.py` and `src/rally/_release_flow/**`
  - signed annotated tag checks and `git verify-tag`
  - GitHub draft-review-publish flow through `gh`
- Locked the one allowed Rally-only extension:
  - `.github/workflows/publish-to-pypi.yml` as a narrow Trusted Publishing
    transport workflow triggered by `make release-publish`
- Grounded the reopened plan against:
  - local Doctrine release files and helper modules
  - local `gh` command behavior
  - PyPA `pyproject.toml` guidance
  - PEP 440 version normalization
  - PyPA Trusted Publishing guidance for the PyPI transport leg
- No code changed in this planning pass. This was a docs-only reopen.
- Current phase: Phase 2 - Mirror Doctrine's version files and release docs.

## 2026-04-14 - Doctrine GitHub hardening imported into the Rally plan
- Reviewed the Doctrine CI and GitHub hardening plan and pulled the matching
  Rally surfaces into the canonical plan.
- Added Rally-specific governance and trust-surface scope:
  - protected `main`
  - stable split PR checks
  - CODEOWNERS
  - PR template
  - Dependabot
  - dependency review
  - scorecards
  - CodeQL baseline
  - private vulnerability reporting
  - automated security fixes
  - `SECURITY.md`
  - `SUPPORT.md`
- Reworked the publish target in the plan so Rally now aims for a
  `release.published` `.github/workflows/publish.yml` transport workflow,
  rather than the earlier `publish-to-pypi.yml` idea.
- Explicitly excluded Doctrine-only hardening items that do not fit Rally:
  - VS Code lane
  - package rename
  - merge queue
- No code changed in this pass. This was a docs-only plan expansion.
- Current phase: Phase 2 - Mirror Doctrine's version files and release docs.

## 2026-04-14 - Research and deep-dive pass against the live Doctrine repo
- Re-grounded the canonical plan against the current `../doctrine` repo, not
  just the earlier doctrine hardening notes.
- Pulled in the live Doctrine anchors that are now the stable cross-repo
  convention source:
  - `pyproject.toml`
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `Makefile`
  - `doctrine/release_flow.py`
  - `doctrine/_release_flow/**`
  - `.github/workflows/pr.yml`
  - `.github/workflows/publish.yml`
  - `README.md`
- Updated the Rally plan so it now targets the same workflow filenames and
  topology where the surface is shared:
  - `.github/workflows/pr.yml` instead of a Rally-only PR workflow name
  - `release.published` plus `workflow_dispatch` in `publish.yml`
  - README docs-map parity for versioning, changelog, support, and security
- Explicitly marked Doctrine `SECURITY.md` and `SUPPORT.md` as owner-path
  anchors but not final wording anchors yet, because they still carry pre-1.0
  text in the current doctrine tree.
- No code changed in this pass. This was a docs-only research plus deep-dive
  repair.
- Current phase: Phase 2 - Mirror Doctrine's version files and release docs.

## 2026-04-14 - Doctrine-parity release stack landed and live repo settings applied
- Replaced Rally's dynamic package-version path with explicit
  `[project].version = "0.1.0"` in `pyproject.toml`.
- Rewrote the public release surfaces so they now follow the Doctrine-shaped
  file roles and release format:
  - `docs/VERSIONING.md`
  - `CHANGELOG.md`
  - `README.md`
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `SUPPORT.md`
- Added the repo-owned Doctrine-style release helper stack:
  - `Makefile`
  - `src/rally/release_flow.py`
  - `src/rally/_release_flow/common.py`
  - `src/rally/_release_flow/models.py`
  - `src/rally/_release_flow/parsing.py`
  - `src/rally/_release_flow/tags.py`
  - `src/rally/_release_flow/ops.py`
  - `tests/unit/test_release_flow.py`
- Added the planned GitHub repo surfaces:
  - `.github/CODEOWNERS`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/dependabot.yml`
  - `.github/workflows/pr.yml`
  - `.github/workflows/dependency-review.yml`
  - `.github/workflows/scorecards.yml`
  - `.github/workflows/publish.yml`
- Applied the matching live GitHub repo settings with `gh api`:
  - squash-only merges
  - auto-merge enabled
  - auto-delete merged branches enabled
  - branch update support enabled
  - GitHub Actions switched from `all` to `selected`
  - SHA pinning required for allowed actions
  - allowed action patterns limited to the pinned third-party actions in repo
  - private vulnerability reporting enabled
  - vulnerability alerts enabled
  - automated security fixes enabled
  - CodeQL default setup configured
  - active `main` ruleset added with:
    - pull requests required
    - zero required approvals
    - conversation resolution required
    - strict required status checks
    - linear history required
    - force pushes blocked
    - deletions blocked
    - stable required checks:
      - `bundled-assets`
      - `unit`
      - `packaged-install`
      - `security / dependency-review`
- Re-ran the full local proof path:
  - `uv sync --dev`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
  - `make verify`
- Result: all local proof passed, including:
  - bundled-asset drift check
  - release-flow unit coverage
  - full unit suite
  - wheel and sdist build
  - external-user packaged-install proof against Doctrine `v1.0.1`
- Remaining reachable frontier:
  - run one live `publish.yml` dry run from a pushed branch or merged ref
  - the current branch is local only, so that proof is not reachable yet
- Current phase: Phase 6 - Prove full parity and release readiness.

## 2026-04-14 - Phase 3 release front door repaired against the public Doctrine floor
- The fresh implementation audit found that the repo-owned release front door
  was no longer runnable because `[tool.uv.sources].doctrine` still forced the
  local `../doctrine` checkout, and that sibling now reports package metadata
  name `doctrine-agents`.
- I reproduced the break exactly:
  - `uv sync --dev`
  - `uv run pytest tests/unit/test_release_flow.py -q`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
  - all failed before Rally code ran because `uv` rejected the editable
    sibling override for `doctrine`.
- I checked the live Doctrine public floor and confirmed the real public
  release `v1.0.1` still installs as package `doctrine`, while the local
  sibling repo has already moved on to unreleased `doctrine-agents`.
- Fixed the repo-local source of truth by changing `[tool.uv.sources]` from
  the sibling path override to the public Doctrine git tag source:
  - `doctrine = { git = "https://github.com/aelaguiz/doctrine.git", tag = "v1.0.1" }`
- Kept Rally's declared public dependency line at `doctrine>=1.0.1,<2`, which
  matches the approved minimum public Doctrine floor.
- Re-ran the approved local release-front-door proof:
  - `uv sync --dev`
  - `make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable`
  - `make verify`
- Result: all passed again. The repo-owned release helper is runnable in the
  real repo, and the full local verify path is green.
- Re-checked the live GitHub workflow surface after the local fix:
  - `gh api repos/aelaguiz/rally/actions/workflows`
  - `gh run list --workflow pr.yml ...`

## 2026-04-14 - Live PR gate and publish dry-run proof completed
- Merged PR `#5` (`release: align rally with doctrine conventions`) into
  `main` after the live required checks passed under the active ruleset.
- The live PR proof now exists in GitHub, not just locally:
  - `bundled-assets`
  - `unit`
  - `packaged-install`
  - `security / dependency-review`
- After merge, `gh api repos/aelaguiz/rally/actions/workflows` showed the new
  default-branch workflow set live on `main`:
  - `dependency-review.yml`
  - `pr.yml`
  - `publish.yml`
  - `scorecards.yml`
- Ran the publish transport dry run on `main`:
  - `gh workflow run publish.yml --ref main -f ref=main -f publish_target=none`
  - workflow run `24403594896`
  - result: success
  - the `build` job passed bundled-assets, unit, build, and packaged-install,
    then stored the distribution artifacts
  - the TestPyPI and PyPI publish jobs skipped cleanly because the dry run used
    `publish_target=none`
- Followed the README host-repo path by hand in a temp external workspace from
  the built wheel:
  - installed Rally `0.1.0` plus Doctrine `v1.0.1` into an isolated venv
  - ran `rally run demo` with the venv `bin/` on `PATH`
  - confirmed Rally created `DMO-1`, synced `stdlib/rally/`,
    `skills/rally-kernel/`, and `skills/rally-memory/` into the host repo,
    and stopped at the documented pending `home/issue.md` step
- Current phase: complete pending fresh implementation audit.

## 2026-04-14 - CodeQL gate completed and final live readiness proof landed
- The fresh audit reopened Phase 4 and Phase 6 because the split PR gate was
  live, but the `main` ruleset still did not require CodeQL after the baseline
  turned green.
- I verified the baseline first:
  - `gh api repos/aelaguiz/rally/code-scanning/default-setup`
  - `gh run list --workflow CodeQL --branch main --limit 5 --json ...`
  - result: CodeQL default setup was configured and the latest `main` run was
    green
- I updated the active `main` ruleset to add a real `code_scanning` rule for
  `CodeQL` with thresholds:
  - alerts: `errors`
  - security alerts: `medium_or_higher`
- I did not keep `Analyze (...)` as required status checks. GitHub's code
  scanning merge protection is the right surface here, and open Dependabot PRs
  already showed those raw `Analyze (...)` contexts are not a stable required
  check contract.
- Opened proof PR `#9` from branch `codeql-required-gate-proof` after one
  local targeted check:
  - `uv run pytest tests/unit/test_bundled_assets.py -q`
- The finished live-gate proof is now real:
  - PR `#9` started `BLOCKED` while:
    - `Analyze (actions)` was pending
    - `Analyze (javascript-typescript)` was pending
    - `Analyze (python)` was pending
  - the same PR became `CLEAN` only after all three CodeQL analyses passed,
    together with:
    - `bundled-assets`
    - `unit`
    - `packaged-install`
    - `security / dependency-review`
- Merged PR `#9` into `main`, so the final readiness proof now exists on the
  default branch, not only in a temporary proof branch.
- Current phase: complete pending fresh implementation audit.
  - `gh run list --workflow publish.yml ...`
- Result: the default branch still exposes only `ci.yml` and CodeQL, and both
  `pr.yml` and `publish.yml` still return `404` on `main`.
- Current reachable frontier:
  - Phase 3 is closed again.
  - Phase 4 and Phase 5 are still blocked on landing the branch changes on the
    default branch, because their proof requires live workflows on `main`.
- Current phase: Phase 4 - Harden GitHub governance and PR CI.
