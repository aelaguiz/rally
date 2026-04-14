from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from rally.adapters.base import AdapterReadinessFailure, SubprocessRunner

if TYPE_CHECKING:
    from rally.domain.flow import FlowDefinition


def allowed_mcp_names(flow: "FlowDefinition") -> tuple[str, ...]:
    return tuple(sorted({mcp for agent in flow.agents.values() for mcp in agent.allowed_mcps}))


def probe_timeout_sec(raw_value: object) -> float:
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool) and raw_value > 0:
        return float(min(raw_value, 5))
    return 5.0


def render_probe_failure(*, command: list[str], returncode: int, stdout: str | None, stderr: str | None) -> str:
    stderr_text = (stderr or "").strip()
    if stderr_text:
        return stderr_text
    stdout_text = (stdout or "").strip()
    if stdout_text:
        return stdout_text.splitlines()[-1]
    return f"`{' '.join(command)}` exited with code {returncode}."


def probe_stdio_startability(
    *,
    mcp_name: str,
    command_name: object,
    raw_args: object,
    raw_env: object,
    raw_cwd: object,
    run_home: Path,
    env: Mapping[str, str],
    subprocess_run: SubprocessRunner,
    config_label: str,
    timeout_sec: float,
) -> AdapterReadinessFailure | None:
    if not isinstance(command_name, str) or not command_name.strip():
        return AdapterReadinessFailure(
            failed_check="command_startability",
            reason=f"{config_label} did not expose a non-empty stdio command.",
            mcp_name=mcp_name,
        )

    if raw_args is None:
        args: list[str] = []
    elif isinstance(raw_args, list) and all(isinstance(item, str) for item in raw_args):
        args = list(raw_args)
    else:
        return AdapterReadinessFailure(
            failed_check="command_startability",
            reason=f"{config_label} returned non-string stdio args.",
            mcp_name=mcp_name,
        )
    command = [command_name, *args]

    probe_env = dict(env)
    if isinstance(raw_env, dict):
        for key, value in raw_env.items():
            if isinstance(key, str) and isinstance(value, str):
                probe_env[key] = value

    cwd = run_home
    if isinstance(raw_cwd, str) and raw_cwd.strip():
        cwd = Path(raw_cwd)

    try:
        completed = subprocess_run(
            command,
            input="",
            capture_output=True,
            text=True,
            cwd=cwd,
            env=probe_env,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        return AdapterReadinessFailure(
            failed_check="command_startability",
            reason=f"Command `{command_name}` was not found.",
            mcp_name=mcp_name,
        )
    except OSError as exc:
        return AdapterReadinessFailure(
            failed_check="command_startability",
            reason=f"Command `{command_name}` could not start: {exc}.",
            mcp_name=mcp_name,
        )
    return AdapterReadinessFailure(
        failed_check="command_startability",
        reason=render_probe_failure(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        ),
        mcp_name=mcp_name,
    )
