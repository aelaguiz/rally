---
title: "Rally - Per-Agent Allowed Skill Enforcement"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE.md
  - docs/SKILL_SCOPING.md
  - src/rally/domain/flow.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/skill_bundles.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/claude_code/adapter.py
  - tests/unit/test_runner.py
---

# TL;DR

- Outcome: In a Rally run, each agent should only see `rally-kernel` and the skills in that agent's own `allowed_skills`. No other skill should be present on the adapter-facing skill path for that turn.
- Problem this change fixed: `flow.yaml` already stored per-agent
  `allowed_skills`, but `src/rally/services/home_materializer.py` used to copy
  the per-flow union into shared `home/skills/`, and both Codex and Claude
  used that broader path.
- Approach: Keep `flow.yaml` as the one source of truth, build per-agent skill views inside the run home, keep `home/skills/` as the one live adapter path, and switch that live path before each turn.
- What shipped: Keep the shared Rally runtime in charge, split run-home skill refresh from per-turn skill activation, then prove first-run and resume behavior with unit coverage and synced design docs.
- Non-negotiables: No second skill registry. No prompt-only fake enforcement. No adapter-facing path that still exposes the per-flow union. The one mandatory Rally built-in stays available on every turn. Tests and docs ship in the same pass.

## Status

Implemented on 2026-04-15.
No approved code gap remains for this change.

Current proof on this head:

- `uv sync --dev`
- `uv run pytest tests/unit -q` -> `305 passed`
- `uv run pytest tests/integration/test_packaged_install.py -q` -> `2 passed`
