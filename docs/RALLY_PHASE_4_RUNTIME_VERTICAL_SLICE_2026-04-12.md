---
title: "Rally - Phase 4 Runtime Vertical Slice"
date: 2026-04-12
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_status
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - flows/single_repo_repair/flow.yaml
  - flows/single_repo_repair/prompts/AGENTS.prompt
  - stdlib/rally/prompts/rally/base_agent.prompt
  - stdlib/rally/prompts/rally/turn_results.prompt
  - src/rally/services/flow_loader.py
  - src/rally/cli.py
  - src/rally/services/issue_ledger.py
  - src/rally/adapters/codex/launcher.py
---

# Summary

Phase 4 is still in progress.
The repo now has the first real runtime seams, but not the full run loop yet.

What is real today:

- Rally loads flow config plus compiled `AGENTS.contract.json` from `flows/<flow>/build/agents/*`.
- Rally ships `rally issue note`.
- Rally appends notes into `home/issue.md` and snapshots `issue_history/`.
- Rally builds the required Codex launch env map.

What is still pending:

- real `rally run`
- real `rally resume`
- run storage and locking
- home materialization
- event logging
- strict adapter result handling
- session restore
- runner orchestration

# Stable Rules

- Notes are context only.
- Final JSON is the only turn-ending control path.
- `AGENTS.md` is injected instruction readback only.
- `AGENTS.contract.json` is the compiler-owned metadata file Rally loads.
- Rally does not ship a shared file-state carrier.
- If an authored review needs local review-state syntax, that is local Doctrine review syntax only.
- There is no separate handoff artifact.

# Current Code Surface

The current checked-in runtime surface is:

- `src/rally/services/flow_loader.py`
  - loads `flow.yaml`
  - requires compiled `build/agents/*`
  - requires `AGENTS.contract.json`
  - validates the shared turn-result schema
- `src/rally/cli.py`
  - ships preflight-only `run`
  - keeps `resume` stubbed
  - ships `issue note`
- `src/rally/services/issue_ledger.py`
  - appends Rally-stamped note blocks
  - snapshots the full issue log after each append
- `src/rally/adapters/codex/launcher.py`
  - builds `CODEX_HOME`, `RALLY_BASE_DIR`, `RALLY_RUN_ID`, and `RALLY_FLOW_CODE`

The current placeholder boundaries are:

- `src/rally/services/run_store.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/event_log.py`
- `src/rally/services/runner.py`
- `src/rally/adapters/codex/result_contract.py`
- `src/rally/adapters/codex/session_store.py`

# Proof Path

Use the smallest honest proof for each layer:

- prompt or stdlib change
  - rebuild the affected flow with the paired Doctrine compiler
  - inspect `flows/*/build/agents/*`
- runtime loader change
  - run the flow-loader and turn-result unit tests
- note-path change
  - prove it through `rally issue note` and the owning unit tests

The current core proof set is:

- flow rebuild for `_stdlib_smoke`
- flow rebuild for `single_repo_repair`
- `tests/unit/test_flow_loader.py`
- `tests/unit/domain/test_turn_result_contracts.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_issue_ledger.py`
- `tests/unit/test_launcher.py`

# Next Runtime Work

The next honest implementation steps are:

1. make `run_store.py` real
2. make `home_materializer.py` real
3. make `result_contract.py` real
4. make `runner.py` real
5. wire `run` and `resume` to those owned services

# Live Truth

Use this doc with:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md`

Treat older planning docs as history only.
