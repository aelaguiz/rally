from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from rally.domain.flow import FlowDefinition
from rally.domain.rooted_path import FLOW_ROOT, HOME_ROOT, HOST_ROOT, WORKSPACE_ROOT, PathRoot, expand_rooted_string
from rally.services.workspace import WorkspaceContext

_FLOW_RUNTIME_ENV_ALLOWED_ROOTS: tuple[PathRoot, ...] = (HOME_ROOT, FLOW_ROOT, WORKSPACE_ROOT, HOST_ROOT)


def resolve_flow_runtime_env(
    *,
    flow: FlowDefinition,
    workspace: WorkspaceContext,
    run_home: Path,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for key, value in flow.runtime_env.items():
        resolved[key] = expand_rooted_string(
            value,
            workspace_root=workspace.workspace_root,
            flow_root=flow.root_dir,
            run_home=run_home,
            allowed_roots=_FLOW_RUNTIME_ENV_ALLOWED_ROOTS,
            context=f"runtime.env.{key}",
            example="workspace:fixtures/project",
        )
    return resolved


def build_flow_subprocess_env(
    *,
    flow: FlowDefinition,
    workspace: WorkspaceContext,
    run_home: Path,
    extra_env: Mapping[str, str] | None = None,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env.update(resolve_flow_runtime_env(flow=flow, workspace=workspace, run_home=run_home))
    if extra_env is not None:
        env.update(extra_env)
    return env
