# Rally Tiny Standard Library Worklog

Plan: [RALLY_TINY_STANDARD_LIBRARY_IMPLEMENTATION_PLAN_2026-04-12.md](/Users/aelaguiz/workspace/rally/docs/RALLY_TINY_STANDARD_LIBRARY_IMPLEMENTATION_PLAN_2026-04-12.md)

Superseded note on 2026-04-12: the later master-design update removed
`stdlib/rally/prompts/rally/lifecycle.prompt` from the current Rally stdlib and
reframed end-of-turn outcomes as an adapter-enforced structured return contract.
The implementation notes below remain as historical record of the earlier
three-module pass.

## 2026-04-12 - Implementation pass

- Branch: `arch-rally-tiny-stdlib`
- Scope: ship the tiny Rally stdlib defined in the plan and verify it against
  the provisional cross-root import support in `../doctrine`.

Completed work:

- Added repo compile config in [pyproject.toml](/Users/aelaguiz/workspace/rally/pyproject.toml).
- Added the stdlib prompt modules:
  - [handoffs.prompt](/Users/aelaguiz/workspace/rally/stdlib/rally/prompts/rally/handoffs.prompt)
  - [currentness.prompt](/Users/aelaguiz/workspace/rally/stdlib/rally/prompts/rally/currentness.prompt)
  - [lifecycle.prompt](/Users/aelaguiz/workspace/rally/stdlib/rally/prompts/rally/lifecycle.prompt)
- Added the verification-only smoke entrypoint:
  [AGENTS.prompt](/Users/aelaguiz/workspace/rally/flows/_stdlib_smoke/prompts/AGENTS.prompt)
- Reconciled the master design package layout in
  [RALLY_MASTER_DESIGN_2026-04-12.md](/Users/aelaguiz/workspace/rally/docs/RALLY_MASTER_DESIGN_2026-04-12.md).

Verification:

- Ran a direct compile against the provisional local Doctrine branch:

```bash
cd /Users/aelaguiz/workspace/doctrine
uv run --locked python - <<'PY'
from pathlib import Path
from doctrine.parser import parse_file
from doctrine.compiler import CompilationSession

prompt_path = Path('../rally/flows/_stdlib_smoke/prompts/AGENTS.prompt').resolve()
session = CompilationSession(parse_file(prompt_path))
for agent in ('PlanAuthor', 'RouteRepair', 'Closeout'):
    session.compile_agent(agent)
PY
```

- Result: passed after one smoke-flow correction.

Issues encountered:

- The initial smoke flow tried to prove a generic reroute with the shared
  `RallyNoCurrentArtifactHandoff` output and failed with Doctrine `E339`
  because routed `next_owner` fields must structurally bind the concrete route
  target.
- Resolved by keeping the smoke proof on the local no-current path instead of
  inventing new Rally or Doctrine machinery inside this pass.

Current truth:

- The tiny Rally stdlib exists and compiles against the provisional local
  cross-root import implementation.
- The importable namespace is `rally.*`.
- The smoke proof is verification-only and does not widen into runner or
  product-flow work.
