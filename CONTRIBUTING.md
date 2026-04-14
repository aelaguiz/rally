# Contributing

Thanks for working on Rally.

Rally is small on purpose. Keep it that way.

## First steps

Run these first:

```bash
git status --short
rg --files flows stdlib skills mcps docs
uv sync --dev
uv run pytest tests/unit -q
```

## Repo shape

Rally keeps five fixed top-level folders:

- `flows/` for authored flows and generated readback
- `stdlib/` for shared Rally prompt source
- `skills/` for skill packages
- `mcps/` for MCP definitions
- `runs/` for repo-local runtime state

## Source of truth

- Write prompt source in `.prompt` files.
- Treat `flows/*/build/**` as generated readback, not hand-written source.
- Keep runtime rules in Rally runtime files, not in copied prompt prose.
- Keep run truth on disk under `runs/`.

## Proof paths

Pick the smallest proof that matches the change:

- prompt change: rebuild the affected flow or skill and inspect the generated readback
- runtime change: prove it through `uv run rally ...` or the owning unit tests
- fixture repo change: run that fixture repo's tests from that repo root

## Before you call work done

- Run `uv run pytest tests/unit -q`.
- Say what changed.
- Say what you checked.
- Say what is still blocked or not yet proved.

## Release work

Rally uses the repo-owned release flow:

```bash
make release-prepare RELEASE=v0.1.0 CLASS=additive CHANNEL=stable
make release-tag RELEASE=v0.1.0 CHANNEL=stable
make release-draft RELEASE=v0.1.0 CHANNEL=stable PREVIOUS_TAG=auto
make release-publish RELEASE=v0.1.0
```

Release rules live in `docs/VERSIONING.md`.
Release history lives in `CHANGELOG.md`.

## Read next

- `AGENTS.md`
- `README.md`
- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
