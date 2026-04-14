# Rally - Per-Agent Allowed Skill Enforcement - Worklog

## 2026-04-13

- Armed `.codex/implement-loop-state.019d89de-d828-7a01-9451-a967255e2862.json`
  for the live `implement-loop` session on branch
  `arch/allowed-skill-enforcement`.
- Split the shared runtime path so `src/rally/services/home_materializer.py`
  now refreshes stable per-agent skill views under
  `home/sessions/<agent>/skills/`, while `src/rally/services/runner.py` now
  activates the current agent's live `home/skills/` tree before prompt build
  and adapter launch.
- Kept the existing adapter contracts intact:
  - Codex still uses `CODEX_HOME=run_home` and `cwd=run_home`.
  - Claude still uses `.claude/skills -> home/skills`.
- Added targeted runner coverage for:
  - Codex per-turn skill isolation with a Doctrine skill on the second agent
  - Claude per-turn skill isolation with a markdown skill on the second agent
  - resume-time refresh of per-agent session skill views
- Regenerated the local ignored `skills/rally-memory/build/SKILL.md` during the
  first proof pass, then removed the test dependency on that file by teaching
  the runner fixtures to synthesize the built-in Doctrine readback they need.
- Re-emitted `flows/poem_loop/build/**` and
  `flows/software_engineering_demo/build/**` so generated readback matched the
  current stdlib skill contract.
- Synced the live runtime docs to the shipped behavior in:
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
- Fresh audit reopened Phase 3 for two remaining stale doc lines, then this
  pass fixed the named live-doc drift in:
  - `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
- Reran the stale-text search over the named live runtime docs after the reopen
  fix.
- Reran `uv run pytest tests/unit -q` after the reopen fix and kept the suite
  green at `204 passed`.
- Fresh audit reopened Phase 3 one more time for one remaining showcase line at
  `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md:305`.
- Fixed that line so it now says Rally refreshes
  `home/sessions/<agent>/skills/` on start or resume and activates live
  `home/skills/` before each turn.
- Reran the stale-text search over the four named live runtime docs after the
  final showcase fix and got no matches.
- Reran `uv run pytest tests/unit -q` after the final showcase fix and kept the
  suite green at `204 passed`.
- Verification:
  - `uv sync --dev`
  - `uv run pytest tests/unit/test_runner.py -q`
  - `uv run pytest tests/unit -q`
- Fresh-audit status:
  - implementation proof is clean
  - `implement-loop` state stays armed for the fresh `audit-implementation`
    child
