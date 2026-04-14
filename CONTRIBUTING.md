# Contributing

Thanks for working on Rally.

Rally is small on purpose. Keep it that way.

## First steps

Run these first:

```bash
git status --short
rg --files flows stdlib skills mcps docs
```

Rally expects the Doctrine repo beside it at `../doctrine`. If it is missing, clone it first:

```bash
gh repo clone aelaguiz/doctrine ../doctrine
```

Then sync, build the checked-in readback, and run the unit tests:

```bash
uv sync --dev
uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo
uv run python -m doctrine.emit_skill --pyproject pyproject.toml --target rally-kernel --target rally-memory --target demo-git
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

## Questions, bugs, and proposals

- Use GitHub Discussions for questions and design talk.
- Use GitHub Issues for bugs and scoped feature requests.

## Before you call work done

- Run `uv run pytest tests/unit -q`.
- Say what changed.
- Say what you checked.
- Say what is still blocked or not yet proved.
