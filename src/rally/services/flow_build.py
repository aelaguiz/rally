from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from rally.domain.rooted_path import HOME_ROOT, PathRoot, parse_rooted_path
from rally.errors import RallyConfigError
from rally.services.bundled_assets import ensure_workspace_builtins_synced
from rally.services.skill_bundles import MANDATORY_SKILL_NAMES, resolve_skill_bundle_source
from rally.services.workspace import WorkspaceContext, workspace_context_from_root

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

    ensure_workspace_builtins_synced(
        workspace_root=workspace_context.workspace_root,
        pyproject_path=workspace_context.pyproject_path,
    )
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
    _sync_role_soul_sidecars(workspace=workspace_context, flow_name=flow_name)

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
    if skill_name in MANDATORY_SKILL_NAMES:
        return False
    bundle = resolve_skill_bundle_source(
        repo_root=repo_root,
        skill_name=skill_name,
    )
    if bundle.kind != "doctrine":
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


def _sync_role_soul_sidecars(*, workspace: WorkspaceContext, flow_name: str) -> None:
    roles_root = workspace.workspace_root / "flows" / flow_name / "prompts" / "roles"
    build_agents_root = workspace.workspace_root / "flows" / flow_name / "build" / "agents"
    expected_role_slugs: set[str] = set()

    if roles_root.is_dir():
        for role_dir in sorted(roles_root.iterdir()):
            if not role_dir.is_dir():
                continue
            soul_prompt = role_dir / "SOUL.prompt"
            if not soul_prompt.is_file():
                continue
            expected_role_slugs.add(role_dir.name)
            rendered = _render_sidecar_prompt(
                prompt_path=soul_prompt,
                project_config_path=workspace.pyproject_path,
                flow_name=flow_name,
            )
            target_dir = build_agents_root / role_dir.name
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "SOUL.md").write_text(rendered, encoding="utf-8")

    if not build_agents_root.is_dir():
        return

    for agent_dir in sorted(build_agents_root.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name in expected_role_slugs:
            continue
        for sidecar_name in ("SOUL.md", "SOUL.contract.json"):
            sidecar_path = agent_dir / sidecar_name
            if sidecar_path.is_file():
                sidecar_path.unlink()


def _render_sidecar_prompt(
    *,
    prompt_path: Path,
    project_config_path: Path,
    flow_name: str,
) -> str:
    try:
        from doctrine.compiler import CompilationSession
        from doctrine.diagnostics import DoctrineError
        from doctrine.emit_common import root_concrete_agents
        from doctrine.parser import parse_file
        from doctrine.project_config import load_project_config
        from doctrine.renderer import render_markdown
    except ImportError as exc:
        raise RallyConfigError(
            f"Failed to import Doctrine while rendering role sidecars for flow `{flow_name}`: {exc}."
        ) from exc

    try:
        prompt_file = parse_file(prompt_path)
        agent_names = root_concrete_agents(prompt_file)
        if len(agent_names) != 1:
            raise RallyConfigError(
                f"Role sidecar `{prompt_path}` must compile exactly one concrete agent, found {len(agent_names)}."
            )
        project_config = load_project_config(project_config_path)
        session = CompilationSession(prompt_file, project_config=project_config)
        compiled_agents = session.compile_agents(agent_names)
    except DoctrineError as exc:
        raise RallyConfigError(f"Failed to compile role sidecar `{prompt_path}`: {exc}") from exc

    return render_markdown(compiled_agents[0])


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
