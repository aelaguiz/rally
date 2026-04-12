# repo-search

Use this skill when a Rally flow turn needs exact file-level grounding inside a
prepared local repo.

## What It Does

- locate the exact files, symbols, and tests that matter for the current issue
- prefer `rg` for search and `rg --files` for inventory
- surface the exact paths the next owner should read now

## Use It For

- finding the seeded bug location
- finding the matching test coverage
- confirming the exact repo files named in a handoff

## Do Not Use It For

- broad architecture redesign
- environment repair that is not needed for the current repo search
