# Changelog

All notable Rally release changes live here.
This file is the portable release history. `docs/VERSIONING.md` is the
evergreen policy guide.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

## Unreleased

Use this section for work that is not public yet.

### Added
- `rally run <flow> --detach` and `rally resume <id> --detach` start a Rally
  run in the background via a double-fork. The parent prints the grandchild
  pid and returns immediately; the detached worker continues the normal loop
  with stdio redirected into `runs/active/<id>/logs/stdout.log` and
  `stderr.log`.
- `rally stop <run-id>` asks a run to stop at the next turn boundary by
  writing `control/stop.requested`. The runner loop observes the file,
  finalizes the run as `STOPPED`, appends a "Rally Stopped" entry to
  `issue.md`, and emits a `STOPPED` event. Idempotent.
- `rally stop <run-id> --now [--grace <secs>]` escalates to `SIGTERM`, then
  `SIGKILL` after the grace window, targeting the run's recorded process or
  process group.
- `rally watch <run-id> [--since N] [--follow]` renders
  `logs/events.jsonl` for one run; `--follow` polls for new events until the
  run reaches a terminal status.
- Reconciled status (CRASHED / ORPHANED / STALE) surfaces in `rally status`
  for runs whose recorded state no longer matches the live process.
- Per-run `heartbeat.json` (updated every 15s by a background thread) and
  `done.json` clean-exit sentinel — their combination lets the reconciler
  distinguish orderly termination from a crash.
- New event codes: `DETACH`, `STOPPED`, `STOP_REQUESTED`, `HEARTBEAT`,
  `CRASH_DETECTED`.

### Changed
- `runs/active/<id>/state.yaml` and `run.yaml` writes are now atomic
  (tempfile + fsync + `os.replace` + directory fsync). State gains
  `schema_version` (default 2), `pid`, `process_create_time`, and `pgid`
  fields. `schema_version: 1` (pre-detach) state is tolerated and upgraded
  on the next write.
- Per-flow lock migrated from O_EXCL+PID-file to `fcntl.flock`. The lock is
  now held on an open file description, so it automatically releases on
  process death and survives `fork` into detached children — closing the
  old PID lock file as a side effect used to orphan the lock.
- `rally status` uses a reconciler that computes status from
  `(state.yaml + heartbeat.json + done.json + probe(pid))`. Stored terminal
  states (DONE / BLOCKED / STOPPED) remain sticky; all other computed
  statuses are presentation-only and never persisted.

### Added (deps)
- `psutil>=6,<7` for durable `(pid, create_time)` process identity. Isolated
  to `rally.services.process_identity`; no other module imports `psutil`.

## v1.0.0 - 2026-04-17

Release kind: Breaking
Release channel: stable
Release version: v1.0.0
Affected surfaces: Rally package metadata Doctrine floor, supported Doctrine package line, host-repo prompt compatibility inherited from Doctrine 3.0, and host-repo readers of emitted Doctrine contracts and `## Outputs` Markdown.
Who must act: (1) host authors whose `.prompt` files still use retired Doctrine 2.x forms that Doctrine 3.0 rejects, especially `required:` or `optional:` inside `output schema` fields and route fields (Doctrine emits `E236` and `E237`); (2) downstream readers of emitted `AGENTS.contract.json`, which Doctrine 2.0 retired in favor of `final_output.contract.json` plus `schemas/<output-slug>.schema.json`; (3) downstream snapshot, parser, or scraper users of emitted `## Outputs` Markdown, the old `_ordered list_` or `_unordered list_` helper lines, and the old compiler-owned review-semantics and single-child `* Binding` wrappers; (4) host repos that still ship a `doctrine` or `doctrine-agents<2` pin alongside Rally.
Who does not need to act: users who resolve `doctrine-agents` only through Rally's declared range, users who consume `schemas/<output-slug>.schema.json` wire shape, and users who stay on a source checkout with an editable `../doctrine` that already tracks Doctrine 3.0 syntax.
Upgrade steps: (1) install `rally-agents` v1.0.0 so Rally pulls `doctrine-agents>=2.0.0,<3`; (2) refresh any lockfile or dependency pin that still points at `doctrine` or `doctrine-agents<2` to `doctrine-agents>=2.0.0,<3`; (3) in host `.prompt` files, replace authored `required:` and `optional:` inside `output schema` fields and route fields with `nullable` where the field may be `null` (Doctrine compile errors cite `E236` and `E237`); (4) stop reading emitted `AGENTS.contract.json` — read `final_output.contract.json` for final-output, review-control, and the new top-level `route` and `io` metadata, and read `schemas/<output-slug>.schema.json` for structured-output wire shape; (5) refresh downstream emitted-Markdown snapshots and parsers to the new `## Outputs` grouped-contract layout (no `_ordered list_` or `_unordered list_` helper lines, compacted review-semantics and single-child `* Binding` wrappers); (6) run `uv run rally run <flow>` (or the host equivalent) once after the upgrade to regenerate emitted build artifacts under the new Doctrine output shapes.
Verification: make verify
Support-surface version changes: minimum Doctrine release v1.0.2 -> v2.0.0; supported Doctrine package line `doctrine-agents>=1.0.2,<2` -> `doctrine-agents>=2.0.0,<3`; inherited Doctrine language 2.2 -> 3.0; emitted `AGENTS.contract.json` retired in Rally-managed host builds; emitted `schemas/<output-slug>.schema.json` is now the sole structured-output wire contract; workspace manifest 1 (unchanged); compiled contract version 1 (unchanged)

### Changed
- Raised Rally's public Doctrine floor to `doctrine-agents>=2.0.0,<3` so Rally
  installs resolve against the Doctrine 2.0 release line and pick up the new
  Doctrine language (3.0), retired authored `required:` and `optional:` inside
  `output schema` fields, the new grouped `## Outputs` Markdown layout, and the
  retired `AGENTS.contract.json` by default.
- Updated `docs/VERSIONING.md` and `README.md` to carry the new minimum
  Doctrine release and supported package line so host repos see the new floor
  in one place.

## v0.1.1 - 2026-04-14

Release kind: Non-breaking
Release channel: stable
Release version: v0.1.1
Affected surfaces: external host-workspace bootstrap, Rally package metadata, and clean package install proof.
Who must act: users who install Rally from package indexes and maintainers who cut Rally releases.
Who does not need to act: users staying on a source checkout and users who already work from unreleased repo commits.
Upgrade steps: Install `rally-agents` v0.1.1. Refresh lockfiles or dependency pins that still mention the old `doctrine` distribution name. The Rally CLI stays `rally`.
Verification: make verify
Support-surface version changes: workspace manifest 1 (unchanged); compiled contract version 1 (unchanged); minimum Doctrine release v1.0.2 (unchanged)

### Added
- Added `rally workspace sync` so a host repo can sync Rally-owned built-ins
  into `stdlib/rally/`, `skills/rally-kernel/`, and `skills/rally-memory/`
  before the first `rally run` or manual `doctrine.emit_docs`.

### Changed
- Updated the external host-repo setup story and Rally design docs to use
  `rally workspace sync` as the front door for host-local built-ins.
- Removed Rally's own `[tool.uv.sources]` override for Doctrine so Rally
  resolves the public `doctrine-agents` release by default and sibling repos
  can choose their own local editable Doctrine source cleanly.

### Fixed
- Switched Rally's public Doctrine dependency to
  `doctrine-agents>=1.0.2,<2`, which matches the first clean renamed-package
  Doctrine release on PyPI.
- Removed the package-proof path that preinstalled Doctrine from git before
  installing Rally, so `make verify-package`, `make verify`, and CI now prove
  clean consumer installs.

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

### YANKED
- Superseded by `v0.1.1` because `v0.1.0` still depended on the old
  `doctrine` package line and failed fresh package installs.
