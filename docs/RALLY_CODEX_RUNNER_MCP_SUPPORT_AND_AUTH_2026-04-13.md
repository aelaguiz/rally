---
title: "Rally - Codex Runner MCP Support And Auth"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - src/rally/adapters/codex/adapter.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - src/rally/services/flow_loader.py
  - src/rally/domain/flow.py
  - tests/unit/test_adapter_mcp_projection.py
  - tests/unit/test_runner.py
  - tests/unit/test_launcher.py
---

# Summary

This doc tracks the remaining Codex MCP readiness gap in Rally.

Rally already copies allowed MCP definitions into the run home, writes the
Codex-native `config.toml`, projects file-backed auth into the run home, and
launches Codex with `CODEX_HOME=<run_home>`.
What is still missing is one honest readiness rule for required MCPs.

## Current status

What ships today:

- `src/rally/adapters/codex/adapter.py` writes `home/config.toml` from the
  Rally-owned `home/mcps/` snapshot.
- The same adapter projects `auth.json` and `.credentials.json` into the run
  home.
- Codex still launches with `CODEX_HOME=<run_home>`.
- `tests/unit/test_adapter_mcp_projection.py` and runner tests cover the
  current projection path.
- `uv run pytest tests/unit -q` passes on current head.

What is still missing:

- Rally does not yet prove before the turn that a required MCP can start.
- Rally does not yet prove that projected auth is present and still usable.
- Rally does not yet prove that child runners keep the same MCP access story as
  the parent runner.
- Rally does not yet emit one clear blocker that names the broken MCP and the
  reason.

## Current shipped behavior

- Rally owns the policy snapshot under `home/mcps/`.
- The Codex adapter owns native Codex file prep inside the run home.
- Current runtime docs still record the MCP readiness rule as unfinished:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`

That is the live repo truth today.
If this doc and the code disagree, the code and those live runtime docs win.

## Direction

Keep the boundary simple:

- Rally owns policy, run-home prep, and blocker reporting.
- The Codex adapter owns native config generation, auth projection, launch, and
  startup classification.
- Rally should not grow a shared MCP or auth broker.
- Any Codex auth mode broader than the current file-backed projection needs its
  own direct proof before Rally claims to support it.

## Proof bar

This topic is done only when Rally has all of these:

- a direct Codex proof that projected auth works from a changed `CODEX_HOME`
- a direct Codex proof that a broken required MCP fails before work starts
- Rally-side tests for config projection and startup-blocker handling
- one honest proof that a parent runner and a child runner keep the same
  allowed MCP story

## Why this stays separate

This topic is still a real runtime gap, not just old history.
It stays as its own doc because readers may look for the open Codex MCP story
directly, while the master design and CLI docs stay focused on the broader
runtime.
