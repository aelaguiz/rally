from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

import yaml

from rally.errors import RallyConfigError
from rally.services.framework_assets import ensure_framework_builtins
from rally.services.skill_bundles import MANDATORY_SKILL_NAMES, resolve_skill_bundle_source
from rally.services.workspace import WorkspaceContext, workspace_context_from_root

BuildSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def ensure_flow_assets_built(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    flow_name: str,
    subprocess_run: BuildSubprocessRunner = subprocess.run,
) -> None:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    repo_root = workspace_context.workspace_root
    config_path = workspace_context.pyproject_path
    if not config_path.is_file():
        raise RallyConfigError(f"Rally workspace pyproject is missing: `{config_path}`.")

    ensure_framework_builtins(workspace_context)

    doctrine_skill_targets = tuple(
        skill_name
        for skill_name in _load_flow_skill_names(repo_root=repo_root, flow_name=flow_name)
        if _should_emit_skill_build(
            workspace=workspace_context,
            repo_root=repo_root,
            skill_name=skill_name,
        )
    )

    _run_doctrine_emit(
        workspace=workspace_context,
        config_path=config_path,
        subprocess_run=subprocess_run,
        module_name="doctrine.emit_docs",
        target_names=(flow_name,),
        failure_label=f"flow `{flow_name}`",
    )

    if not doctrine_skill_targets:
        return

    _run_doctrine_emit(
        workspace=workspace_context,
        config_path=config_path,
        subprocess_run=subprocess_run,
        module_name="doctrine.emit_skill",
        target_names=doctrine_skill_targets,
        failure_label="Doctrine skill package(s)",
    )


def _load_flow_skill_names(*, repo_root: Path, flow_name: str) -> tuple[str, ...]:
    flow_file = repo_root / "flows" / flow_name / "flow.yaml"
    if not flow_file.is_file():
        raise RallyConfigError(f"Flow definition does not exist: `{flow_file}`.")

    payload = yaml.safe_load(flow_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyConfigError(f"`{flow_file}` must decode to a mapping.")
    raw_agents = payload.get("agents")
    if not isinstance(raw_agents, dict):
        raise RallyConfigError(f"`{flow_file}` must define an `agents` mapping.")

    skill_names = set(MANDATORY_SKILL_NAMES)
    for agent_key, raw_agent in raw_agents.items():
        if not isinstance(agent_key, str):
            raise RallyConfigError(f"`agents` keys in `{flow_file}` must be strings.")
        if not isinstance(raw_agent, dict):
            raise RallyConfigError(f"Agent `{agent_key}` in `{flow_file}` must decode to a mapping.")
        raw_skills = raw_agent.get("allowed_skills", [])
        if not isinstance(raw_skills, list) or not all(isinstance(skill, str) and skill for skill in raw_skills):
            raise RallyConfigError(
                f"Agent `{agent_key}` in `{flow_file}` must define `allowed_skills` as a list of strings."
            )
        skill_names.update(raw_skills)
    return tuple(sorted(skill_names))


def _should_emit_skill_build(
    *,
    workspace: WorkspaceContext,
    repo_root: Path,
    skill_name: str,
) -> bool:
    bundle = resolve_skill_bundle_source(repo_root=repo_root, skill_name=skill_name)
    if bundle.kind != "doctrine":
        return False
    if skill_name in MANDATORY_SKILL_NAMES and workspace.workspace_root != workspace.framework_root:
        return False
    return True


def _run_doctrine_emit(
    *,
    workspace: WorkspaceContext,
    config_path: Path,
    subprocess_run: BuildSubprocessRunner,
    module_name: str,
    target_names: tuple[str, ...],
    failure_label: str,
) -> None:
    command = [
        sys.executable,
        "-m",
        module_name,
        "--pyproject",
        str(config_path),
    ]
    for target_name in target_names:
        command.extend(["--target", target_name])
    try:
        completed = subprocess_run(
            command,
            cwd=workspace.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RallyConfigError(f"Failed to start Doctrine rebuild for {failure_label}: {exc}.") from exc

    if completed.returncode == 0:
        return

    detail = completed.stderr.strip() or completed.stdout.strip() or f"{module_name} failed."
    raise RallyConfigError(f"Failed to rebuild {failure_label} with `{module_name}`: {detail}")


def _coerce_workspace(*, workspace: WorkspaceContext | None, repo_root: Path | None) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyConfigError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyConfigError("`ensure_flow_assets_built` needs a workspace root.")
    return workspace_context_from_root(repo_root)
