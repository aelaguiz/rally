from __future__ import annotations

from pathlib import Path

from rally.errors import RallyStateError


def build_codex_launch_env(
    *,
    repo_root: Path,
    run_home: Path,
    run_id: str,
    flow_code: str,
) -> dict[str, str]:
    if not run_id.strip():
        raise RallyStateError("Run id must not be empty.")
    if not flow_code.strip():
        raise RallyStateError("Flow code must not be empty.")

    return {
        "CODEX_HOME": str(run_home.resolve()),
        "RALLY_BASE_DIR": str(repo_root.resolve()),
        "RALLY_RUN_ID": run_id,
        "RALLY_FLOW_CODE": flow_code,
    }
