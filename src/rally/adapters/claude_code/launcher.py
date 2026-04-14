from __future__ import annotations

from pathlib import Path

from rally.adapters.base import build_rally_launch_env, write_adapter_launch_record

_DISABLED_CLAUDE_AI_MCP = "false"


def build_claude_code_launch_env(
    *,
    workspace_dir: Path,
    cli_bin: Path,
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
        "ENABLE_CLAUDEAI_MCP_SERVERS": _DISABLED_CLAUDE_AI_MCP,
    }


def write_claude_code_launch_record(
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
        extra_env_keys=("ENABLE_CLAUDEAI_MCP_SERVERS",),
    )
