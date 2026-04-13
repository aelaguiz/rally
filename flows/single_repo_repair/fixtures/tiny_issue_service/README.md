# tiny_issue_service

This fixture repo exists only to give the Rally single-repo repair flow a
concrete target repo on disk.

## Seeded bug

`paginate_issues()` computes the page start offset incorrectly. Page 1 skips
the first issue instead of returning the first window.

## Local verification

Run the deterministic local check from the repo root:

```bash
uv run pytest
```
