# pytest-local

Use this skill when a Rally flow turn needs deterministic local pytest
verification inside a prepared repo.

## What It Does

- runs `python -m pytest` from the prepared repo root
- captures the exact command and result for proof or repro writeups
- keeps verification local and deterministic

## Use It For

- reproducing the seeded bug
- proving the local fix
- collecting the exact failing or passing test command for the next owner

## Do Not Use It For

- broad environment repair
- long-running non-pytest validation
