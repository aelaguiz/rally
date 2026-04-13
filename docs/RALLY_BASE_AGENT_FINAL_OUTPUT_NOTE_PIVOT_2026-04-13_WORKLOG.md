# Worklog

Plan doc: docs/RALLY_BASE_AGENT_FINAL_OUTPUT_NOTE_PIVOT_2026-04-13.md

## Initial entry

- Run started.
- Current phase: Phase 1 - Land the shared stdlib contract.

## 2026-04-13 - Authored cutover pass

- Added `stdlib/rally/prompts/rally/base_agent.prompt` with inherited env-var inputs and Rally-managed `rally-kernel` doctrine.
- Rewrote `stdlib/rally/prompts/rally/turn_results.prompt` and `stdlib/rally/prompts/rally/currentness.prompt`.
- Deleted the old authored `notes.prompt`, `handoffs.prompt`, and `issue_ledger.prompt` surfaces.
- Migrated `_stdlib_smoke` and `single_repo_repair` prompt entrypoints plus the touched `single_repo_repair` role prompts to the new base-agent and currentness model.
- Recompiled both flows with the paired Doctrine compiler into `build/agents/*` using:
  `uv run --project ../doctrine -- python - <<'PY' ... emit_target(...) ... PY`
- Inspected representative emitted readback and contracts for `_stdlib_smoke` `PlanAuthor` and `single_repo_repair` `ScopeLead`.
- User-directed rule applied: `rally-kernel` is Rally-managed ambient capability and should not require per-flow `allowed_skills` entries.
