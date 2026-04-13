from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

from rally.errors import RallyConfigError
from rally.services.framework_assets import ensure_framework_builtins
from rally.services.workspace import WorkspaceContext, workspace_context_from_root

BuildSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def ensure_flow_agents_built(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    flow_name: str,
    subprocess_run: BuildSubprocessRunner = subprocess.run,
) -> None:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    config_path = workspace_context.pyproject_path
    if not config_path.is_file():
        raise RallyConfigError(f"Rally workspace pyproject is missing: `{config_path}`.")
    ensure_framework_builtins(workspace_context)

    command = [
        sys.executable,
        "-m",
        "doctrine.emit_docs",
        "--pyproject",
        str(config_path),
        "--target",
        flow_name,
    ]
    try:
        completed = subprocess_run(
            command,
            cwd=workspace_context.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RallyConfigError(f"Failed to start Doctrine rebuild for `{flow_name}`: {exc}.") from exc

    if completed.returncode == 0:
        return

    detail = completed.stderr.strip() or completed.stdout.strip() or "Doctrine emit_docs failed."
    raise RallyConfigError(f"Failed to rebuild flow `{flow_name}` with Doctrine emit_docs: {detail}")


def _coerce_workspace(*, workspace: WorkspaceContext | None, repo_root: Path | None) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyConfigError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyConfigError("`ensure_flow_agents_built` needs a workspace root.")
    return workspace_context_from_root(repo_root)
