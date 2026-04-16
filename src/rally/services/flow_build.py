from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from rally.domain.rooted_path import HOME_ROOT, PathRoot, parse_rooted_path
from rally.errors import RallyConfigError
from rally.services.bundled_assets import workspace_owns_rally_builtins
from rally.services.skill_bundles import MANDATORY_SKILL_NAMES, resolve_skill_bundle_source
from rally.services.workspace import WorkspaceContext, workspace_context_from_root
from rally.services.workspace_sync import sync_workspace_builtins

BuildSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class _PromptPathRule:
    field_name: str
    pattern: re.Pattern[str]
    allowed_roots: frozenset[PathRoot]
    example: str


_PROMPT_PATH_RULES = (
    _PromptPathRule(
        field_name="path",
        pattern=re.compile(r'^\s*path:\s*"(?P<value>[^"]+)"\s*$'),
        allowed_roots=frozenset({HOME_ROOT}),
        example="home:issue.md",
    ),
)

_SYMBOLIC_ARTIFACT_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*_root(?:/|$)")


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

    sync_workspace_builtins(workspace=workspace_context)
    skill_names = _load_flow_skill_names(repo_root=repo_root, flow_name=flow_name)
    _validate_prompt_rooted_paths(
        workspace=workspace_context,
        flow_name=flow_name,
        skill_names=skill_names,
    )

    doctrine_skill_targets = tuple(
        skill_name
        for skill_name in skill_names
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
    # Doctrine owns the full compiled agent package, including optional peer
    # files such as `SOUL.md`. Rally only prunes retired legacy artifacts and
    # validates the package boundary before runtime code consumes it.
    _prune_retired_compiled_agent_artifacts(repo_root / "flows" / flow_name / "build" / "agents")
    _validate_emitted_agent_packages(repo_root / "flows" / flow_name / "build" / "agents")

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
    bundle = resolve_skill_bundle_source(
        repo_root=repo_root,
        skill_name=skill_name,
    )
    if bundle.kind != "doctrine":
        return False
    if skill_name in MANDATORY_SKILL_NAMES:
        return workspace_owns_rally_builtins(pyproject_path=workspace.pyproject_path)
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


def _prune_retired_compiled_agent_artifacts(build_agents_root: Path) -> None:
    if not build_agents_root.is_dir():
        return
    for old_sidecar in build_agents_root.glob("*/AGENTS.contract.json"):
        old_sidecar.unlink()


def _validate_emitted_agent_packages(build_agents_root: Path) -> None:
    if not build_agents_root.is_dir():
        raise RallyConfigError(f"Doctrine emit did not create compiled agents under `{build_agents_root}`.")

    agent_dirs = [path for path in sorted(build_agents_root.iterdir()) if path.is_dir()]
    if not agent_dirs:
        raise RallyConfigError(f"Doctrine emit did not create any compiled agents under `{build_agents_root}`.")

    for agent_dir in agent_dirs:
        markdown_path = agent_dir / "AGENTS.md"
        metadata_file = agent_dir / "final_output.contract.json"
        if not markdown_path.is_file() or not metadata_file.is_file():
            raise RallyConfigError(
                f"Compiled agent directory `{agent_dir}` must contain `AGENTS.md` and `final_output.contract.json`."
            )
        payload = _load_final_output_metadata(metadata_file)
        final_output = payload.get("final_output")
        if not isinstance(final_output, dict) or final_output.get("exists") is not True:
            raise RallyConfigError(f"`{metadata_file}` must declare an existing final output.")
        emitted_schema_relpath = final_output.get("emitted_schema_relpath")
        if not isinstance(emitted_schema_relpath, str) or not emitted_schema_relpath:
            raise RallyConfigError(f"`{metadata_file}` must declare `final_output.emitted_schema_relpath`.")
        schema_path = (agent_dir / emitted_schema_relpath).resolve()
        try:
            schema_path.relative_to(agent_dir.resolve())
        except ValueError as exc:
            raise RallyConfigError(
                f"`{metadata_file}` final_output.emitted_schema_relpath must stay inside `{agent_dir}`."
            ) from exc
        if not schema_path.is_file():
            raise RallyConfigError(
                f"`{metadata_file}` points at missing emitted schema `{schema_path}`."
            )


def _load_final_output_metadata(metadata_file: Path) -> dict[str, object]:
    try:
        payload = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RallyConfigError(f"`{metadata_file}` must contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise RallyConfigError(f"`{metadata_file}` must contain a top-level object.")
    return payload

def _coerce_workspace(*, workspace: WorkspaceContext | None, repo_root: Path | None) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyConfigError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyConfigError("`ensure_flow_assets_built` needs a workspace root.")
    return workspace_context_from_root(repo_root)


def _validate_prompt_rooted_paths(
    *,
    workspace: WorkspaceContext,
    flow_name: str,
    skill_names: tuple[str, ...],
) -> None:
    prompt_roots: list[Path] = [
        workspace.workspace_root / "flows" / flow_name / "prompts",
        workspace.workspace_root / "stdlib" / "rally" / "prompts",
    ]
    for skill_name in skill_names:
        bundle = resolve_skill_bundle_source(
            repo_root=workspace.workspace_root,
            skill_name=skill_name,
        )
        if bundle.kind != "doctrine" or bundle.doctrine_entrypoint is None:
            continue
        prompt_roots.append(bundle.doctrine_entrypoint.parent)

    seen: set[Path] = set()
    for prompt_root in prompt_roots:
        resolved_root = prompt_root.resolve()
        if resolved_root in seen or not prompt_root.is_dir():
            continue
        seen.add(resolved_root)
        for prompt_file in sorted(prompt_root.rglob("*.prompt")):
            _validate_prompt_file_rooted_paths(prompt_file)


def _validate_prompt_file_rooted_paths(prompt_file: Path) -> None:
    for line_number, line in enumerate(prompt_file.read_text(encoding="utf-8").splitlines(), start=1):
        for rule in _PROMPT_PATH_RULES:
            match = rule.pattern.match(line)
            if match is None:
                continue
            value = match.group("value")
            if _SYMBOLIC_ARTIFACT_PATH_RE.match(value):
                continue
            parse_rooted_path(
                value,
                context=f"`{prompt_file}:{line_number}` {rule.field_name}",
                allowed_roots=rule.allowed_roots,
                example=rule.example,
            )
