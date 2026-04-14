---
title: "Rally - Codex Runner MCP Support And Auth"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT.md
  - src/rally/adapters/base.py
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

This file records the shipped Codex MCP readiness contract.
Use it with the master design, the Phase 4 runtime doc, and the CLI/logging
doc.
If this file and the code disagree, the code wins.

# What Shipped

Rally now does one honest readiness check before Codex-backed work starts.

- Rally copies the flow-wide allowed MCP set into `home/mcps/`
- Rally projects that shared set into Codex `config.toml`
- Codex sees that projected set as required for startup in this slice
- Rally stops the run before agent work starts when that required set is not
  usable
- the blocker names the broken check instead of failing later in agent work
- parent and child agents launched from the same prepared `CODEX_HOME` keep the
  same MCP access story

# Live Rules

## Scope Of This Slice

- In this shipped slice, `required MCP` means the shared Codex-visible MCP set
  Rally prepares in the run home.
- This is not broader per-agent MCP isolation.
- Per-agent MCP isolation is still a separate runtime question if Rally needs
  it later.

## Auth Claim

- Rally only claims the file-backed Codex auth projection it can prove from the
  prepared run home.
- The current projection uses the run-home `CODEX_HOME` plus linked auth files.
- Rally does not claim extra Codex auth modes here.

## Failure Path

- Rally fails loud before useful agent work starts when readiness fails.
- There is no silent retry loop, shim, or second fallback path.
- The blocker stays on the canonical Rally runner path, not a side system.

# Readiness Checks

The shipped readiness story covers four things:

- run-home materialization
- Codex config visibility
- Codex auth status
- command startability

If one of those fails, Rally blocks early and tells the operator what broke.

# Proof

The current proof path is:

- `uv run pytest tests/unit/test_adapter_mcp_projection.py tests/unit/test_runner.py -q`
- `uv run pytest tests/unit/test_launcher.py -q`
- `uv run pytest tests/unit -q`

Direct proof on this head also covers:

- projected file-backed auth still works from a changed `CODEX_HOME`
- a broken required MCP fails before useful agent work starts
- a child agent started from the same prepared home can use the same required
  MCP path as the parent

# Reader Path

- Use `docs/RALLY_MASTER_DESIGN.md` for the broader runtime model.
- Use `docs/RALLY_RUNTIME.md` for the
  shipped runtime surface.
- Use `docs/RALLY_CLI_AND_LOGGING.md` for the operator-facing run
  and blocker path.
- Use this file when you need the narrower shipped contract for Codex MCP
  readiness, auth projection, and early blocking.
