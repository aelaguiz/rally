from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

import yaml

from rally.errors import RallyConfigError
from rally.services.skill_bundles import MANDATORY_SKILL_NAMES, resolve_skill_bundle_source

BuildSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def ensure_flow_assets_built(
    *,
    repo_root: Path,
    flow_name: str,
    subprocess_run: BuildSubprocessRunner = subprocess.run,
) -> None:
    config_path = repo_root / "pyproject.toml"
    if not config_path.is_file():
        raise RallyConfigError(f"Rally pyproject is missing: `{config_path}`.")

    doctrine_root = (repo_root.parent / "doctrine").resolve()
    if not doctrine_root.is_dir():
        raise RallyConfigError(f"Paired Doctrine repo is missing: `{doctrine_root}`.")
    if not (doctrine_root / "pyproject.toml").is_file():
        raise RallyConfigError(f"Doctrine pyproject is missing: `{doctrine_root / 'pyproject.toml'}`.")

    doctrine_skill_targets = tuple(
        skill_name
        for skill_name in _load_flow_skill_names(repo_root=repo_root, flow_name=flow_name)
        if resolve_skill_bundle_source(repo_root=repo_root, skill_name=skill_name).kind == "doctrine"
    )

    _run_doctrine_emit(
        repo_root=repo_root,
        doctrine_root=doctrine_root,
        config_path=config_path,
        subprocess_run=subprocess_run,
        module_name="doctrine.emit_docs",
        target_names=(flow_name,),
        failure_label=f"flow `{flow_name}`",
    )

    if not doctrine_skill_targets:
        return

    _run_doctrine_emit(
        repo_root=repo_root,
        doctrine_root=doctrine_root,
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


def _run_doctrine_emit(
    *,
    repo_root: Path,
    doctrine_root: Path,
    config_path: Path,
    subprocess_run: BuildSubprocessRunner,
    module_name: str,
    target_names: tuple[str, ...],
    failure_label: str,
) -> None:
    command = [
        "uv",
        "run",
        "--project",
        str(doctrine_root),
        "--locked",
        "python",
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
            cwd=repo_root,
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
