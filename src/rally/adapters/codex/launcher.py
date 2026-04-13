from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from rally.errors import RallyStateError


def build_codex_launch_env(
    *,
    repo_root: Path,
    run_home: Path,
    run_id: str,
    flow_code: str,
    agent_slug: str,
) -> dict[str, str]:
    if not run_id.strip():
        raise RallyStateError("Run id must not be empty.")
    if not flow_code.strip():
        raise RallyStateError("Flow code must not be empty.")
    if not agent_slug.strip():
        raise RallyStateError("Agent slug must not be empty.")

    return {
        "CODEX_HOME": str(run_home.resolve()),
        "RALLY_BASE_DIR": str(repo_root.resolve()),
        "RALLY_RUN_ID": run_id,
        "RALLY_FLOW_CODE": flow_code,
        "RALLY_AGENT_SLUG": agent_slug,
    }


def write_codex_launch_record(
    *,
    run_dir: Path,
    turn_index: int,
    agent_slug: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout_sec: int,
) -> Path:
    launch_dir = run_dir / "logs" / "adapter_launch"
    launch_dir.mkdir(parents=True, exist_ok=True)
    record_file = launch_dir / f"turn-{turn_index:03d}-{agent_slug}.json"
    payload = {
        "ts": datetime.now(UTC).astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "command": command,
        "cwd": str(cwd.resolve()),
        "timeout_sec": timeout_sec,
        "env": {
            key: value
            for key, value in env.items()
            if key.startswith("RALLY_") or key == "CODEX_HOME"
        },
    }
    record_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record_file
