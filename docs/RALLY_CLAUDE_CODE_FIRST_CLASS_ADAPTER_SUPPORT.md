---
title: "Rally - Claude Code First-Class Adapter Support"
status: shipped
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_RUNTIME.md
  - src/rally/adapters/base.py
  - src/rally/adapters/registry.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/claude_code/adapter.py
  - src/rally/adapters/claude_code/launcher.py
  - src/rally/adapters/claude_code/event_stream.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/flow_loader.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - tests/unit/test_adapter_registry.py
  - tests/unit/test_claude_code_event_stream.py
  - tests/unit/test_claude_code_launcher.py
  - tests/unit/test_final_response_loader.py
  - tests/unit/test_runner.py
---

# TL;DR

## Outcome

Rally now supports `runtime.adapter: claude_code` beside `codex` through one
real adapter boundary. Claude support is now a shipped runtime path, not a doc
idea, not a shell alias, and not a local spike.

## Problem

The earlier draft was written while the runtime was still Codex-only in
practice. Shared runtime code launched Codex directly, wrote Codex bootstrap
files from shared services, and taught a future tense Claude plan instead of
the code that actually shipped.

## Approach

Keep one Rally-owned run model, one issue ledger, one prompt path, and one
final JSON path. Move adapter-specific launch, bootstrap, event parsing, and
session handling behind a shared adapter contract. Then land Claude on that
same boundary with the smallest honest v1 stance: use the user's existing
Claude login, clamp the runtime surfaces Claude exposes, and document the
remaining ambient dependency plainly.

## What shipped

1. Land the shared adapter boundary, registry, and Rally-owned final-response
   loader.
2. Cut Codex over to that shared boundary without changing its run-home
   contract.
3. Add the Claude CLI adapter with stdin prompt delivery, generated MCP
   config, strict tool clamps, and the same shared final JSON path.
4. Sync the surviving runtime docs to the code that actually shipped.

## Status

A fresh audit on 2026-04-13 cleared the full approved implementation frontier.
Phases 1 through 4 are closed in code.

What is truly done:

- `uv run pytest tests/unit -q` passes on current head
- `uv run pytest tests/unit/test_claude_code_event_stream.py
  tests/unit/test_runner.py tests/unit/test_claude_code_launcher.py -q`
  passed during the implementation proof
- a fresh real Claude Rally run completed through the shipped
  `claude_code` adapter, the real Claude CLI, and the user's existing local
  Claude login:
  - temp repo root:
    `/private/var/folders/cr/8sccc69d0rg1b8dsp42v7q900000gn/T/rally-claude-live-xkjjvb5h`
  - run id: `CLP-1`
  - status: `done`
  - summary: `live claude contract proof`
- a fresh real Codex Rally run completed through the shared adapter boundary on
  a tiny one-agent temp flow after the cutover
- the shared adapter boundary, shared final loader, and Codex cutover are all
  in the tree
- the shipped Claude contract now matches the approved Phase 3 plan:
  - `--permission-mode dontAsk`
  - explicit `--tools`
  - explicit `--allowedTools`
  - adapter-owned `src/rally/adapters/claude_code/session_store.py`
- the Claude fallback loader now accepts fenced JSON blocks from live Claude
  output in both `result.result` and assistant text content

Real remaining frontier:

- no code gap remains across the approved implementation frontier
- broader docs cleanup now happens separately from this shipped feature doc

Remaining honest v1 caveats:

- Claude still depends on the user's existing local Claude login and Claude's
  native session store outside the run home
- Claude init output still exposes bundled slash commands and bundled skills;
  Rally now clamps built-in tools and Claude.ai MCP servers, but it does not
  fully clean-room every ambient Claude surface yet

## Non-negotiables

- No second turn-ending control path. Rally still ends a turn with notes plus
  one final JSON result.
- `claude_code` must stay a real adapter, not a Codex alias.
- The shared prompt path stays in Rally. Do not add a second Claude-only prompt
  layer.
- The shared final JSON path stays `last_message.json`.
- Claude v1 must clamp the runtime surfaces Claude exposes. Where Claude does
  not expose a clamp, the doc must name the remaining ambient dependency
  honestly.
- Adapter choice stays flow-wide in v1.
