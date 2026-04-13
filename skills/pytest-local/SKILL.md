---
name: pytest-local
description: "Run `uv run pytest` in a prepared repo when a Rally turn needs a local repro or proof."
---

# pytest-local

Use this skill when a Rally turn needs a repeatable local pytest check inside a
prepared repo.

## What It Does

- Run `uv run pytest` from the prepared repo root.
- Capture the exact command and result for test notes or repro steps.
- Keep the check local and repeatable.

## Use It For

- Reproducing the seeded bug.
- Proving the local fix.
- Collecting the exact failing or passing test command for the next person.

## Do Not Use It For

- Broad environment repair.
- Long-running non-pytest validation.
