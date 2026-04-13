---
name: repo-search
description: "Use `rg` and exact file reads to ground a Rally turn in the prepared repo."
---

# repo-search

Use this skill when a Rally turn needs exact file-level grounding inside a
prepared repo.

## What It Does

- Find the exact files, symbols, and tests that matter for the current bug.
- Prefer `rg` for search and `rg --files` for inventory.
- Show the exact paths the next person should read now.

## Use It For

- Finding the seeded bug location.
- Finding the matching test coverage.
- Confirming the exact repo files named in a handoff.

## Do Not Use It For

- Broad architecture redesign.
- Environment repair that is not needed for the current repo search.
