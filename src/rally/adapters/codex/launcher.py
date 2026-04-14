from __future__ import annotations

from pathlib import Path

from rally.adapters.base import build_rally_launch_env, write_adapter_launch_record
from rally.domain.flow import FlowDefinition
from rally.errors import RallyConfigError


def build_codex_launch_env(
    *,
    workspace_dir: Path,
    cli_bin: Path,
    run_home: Path,
    run_id: str,
    flow_code: str,
    agent_slug: str,
    turn_index: int,
) -> dict[str, str]:
    return {
        **build_rally_launch_env(
            workspace_dir=workspace_dir,
            cli_bin=cli_bin,
            run_id=run_id,
            flow_code=flow_code,
            agent_slug=agent_slug,
            turn_index=turn_index,
        ),
        "CODEX_HOME": str(run_home.resolve()),
    }


def codex_project_doc_max_bytes(*, flow: FlowDefinition) -> int:
    project_doc_max_bytes = flow.adapter.args.get("project_doc_max_bytes", 0)
    if not isinstance(project_doc_max_bytes, int) or project_doc_max_bytes < 0:
        raise RallyConfigError("`runtime.adapter_args.project_doc_max_bytes` must be a non-negative integer.")
    return project_doc_max_bytes


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
    return write_adapter_launch_record(
        run_dir=run_dir,
        turn_index=turn_index,
        agent_slug=agent_slug,
        command=command,
        cwd=cwd,
        env=env,
        timeout_sec=timeout_sec,
        extra_env_keys=("CODEX_HOME",),
    )
