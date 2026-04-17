from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
import tomllib

import yaml

from rally.domain.flow import flow_agent_key_to_slug
from rally.domain.rooted_path import HOME_ROOT, PathRoot, parse_rooted_path
from rally.errors import RallyConfigError
from rally.services.agent_skill_validation import validate_flow_agent_skill_surfaces
from rally.services.builtin_assets import (
    RallyBuiltinAssets,
    reject_reserved_builtin_skill_shadow,
    resolve_rally_builtin_assets,
)
from rally.services.skill_bundles import (
    MANDATORY_SKILL_NAMES,
    resolve_skill_bundle_source,
    validate_system_skill_name,
)
from rally.services.workspace import WorkspaceContext, workspace_context_from_root

DoctrineEmitKind = str


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
) -> None:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    repo_root = workspace_context.workspace_root
    config_path = workspace_context.pyproject_path
    if not config_path.is_file():
        raise RallyConfigError(f"Rally workspace pyproject is missing: `{config_path}`.")

    builtins = resolve_rally_builtin_assets(workspace=workspace_context)
    allowed_skills_by_agent_key, system_skills_by_agent_key = (
        _load_flow_agent_skill_tiers(repo_root=repo_root, flow_name=flow_name)
    )
    skill_names = _union_flow_skill_names(
        allowed_skills_by_agent_key=allowed_skills_by_agent_key,
        system_skills_by_agent_key=system_skills_by_agent_key,
    )
    expected_agent_slugs = _load_flow_agent_slugs(repo_root=repo_root, flow_name=flow_name)
    reject_reserved_builtin_skill_shadow(
        workspace_root=repo_root,
        builtins=builtins,
    )
    _validate_prompt_rooted_paths(
        workspace=workspace_context,
        flow_name=flow_name,
        skill_names=skill_names,
        builtins=builtins,
    )

    doctrine_skill_targets = tuple(
        skill_name
        for skill_name in skill_names
        if _should_emit_skill_build(
            workspace=workspace_context,
            repo_root=repo_root,
            skill_name=skill_name,
            builtins=builtins,
        )
    )

    _emit_doctrine_targets(
        config_path=config_path,
        builtins=builtins,
        emit_kind="docs",
        target_names=(flow_name,),
        failure_label=f"flow `{flow_name}`",
    )
    # Doctrine owns the full compiled agent package, including optional peer
    # files such as `SOUL.md`. Rally only prunes retired legacy artifacts and
    # validates the package boundary before runtime code consumes it.
    _prune_retired_compiled_agent_artifacts(
        repo_root / "flows" / flow_name / "build" / "agents",
        expected_agent_slugs=expected_agent_slugs,
    )
    _validate_emitted_agent_packages(repo_root / "flows" / flow_name / "build" / "agents")
    validate_flow_agent_skill_surfaces(
        flow_file=repo_root / "flows" / flow_name / "flow.yaml",
        build_agents_dir=repo_root / "flows" / flow_name / "build" / "agents",
        allowed_skills_by_agent_key=allowed_skills_by_agent_key,
        system_skills_by_agent_key=system_skills_by_agent_key,
    )

    if not doctrine_skill_targets:
        return

    _emit_doctrine_targets(
        config_path=config_path,
        builtins=builtins,
        emit_kind="skill",
        target_names=doctrine_skill_targets,
        failure_label="Doctrine skill package(s)",
    )


def _union_flow_skill_names(
    *,
    allowed_skills_by_agent_key: dict[str, tuple[str, ...]],
    system_skills_by_agent_key: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    skill_names: set[str] = set(MANDATORY_SKILL_NAMES)
    for names in allowed_skills_by_agent_key.values():
        skill_names.update(names)
    for names in system_skills_by_agent_key.values():
        skill_names.update(names)
    return tuple(sorted(skill_names))


def _load_flow_agent_slugs(*, repo_root: Path, flow_name: str) -> tuple[str, ...]:
    flow_file = repo_root / "flows" / flow_name / "flow.yaml"
    if not flow_file.is_file():
        raise RallyConfigError(f"Flow definition does not exist: `{flow_file}`.")

    payload = yaml.safe_load(flow_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyConfigError(f"`{flow_file}` must decode to a mapping.")
    raw_agents = payload.get("agents")
    if not isinstance(raw_agents, dict):
        raise RallyConfigError(f"`{flow_file}` must define an `agents` mapping.")

    agent_slugs: list[str] = []
    for agent_key, raw_agent in raw_agents.items():
        if not isinstance(agent_key, str):
            raise RallyConfigError(f"`agents` keys in `{flow_file}` must be strings.")
        if not isinstance(raw_agent, dict):
            raise RallyConfigError(f"Agent `{agent_key}` in `{flow_file}` must decode to a mapping.")
        agent_slugs.append(flow_agent_key_to_slug(agent_key))
    return tuple(sorted(agent_slugs))


def _load_flow_agent_skill_tiers(
    *,
    repo_root: Path,
    flow_name: str,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    flow_file = repo_root / "flows" / flow_name / "flow.yaml"
    if not flow_file.is_file():
        raise RallyConfigError(f"Flow definition does not exist: `{flow_file}`.")

    payload = yaml.safe_load(flow_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyConfigError(f"`{flow_file}` must decode to a mapping.")
    raw_agents = payload.get("agents")
    if not isinstance(raw_agents, dict):
        raise RallyConfigError(f"`{flow_file}` must define an `agents` mapping.")

    allowed_skills_by_agent_key: dict[str, tuple[str, ...]] = {}
    system_skills_by_agent_key: dict[str, tuple[str, ...]] = {}
    for agent_key, raw_agent in raw_agents.items():
        if not isinstance(agent_key, str):
            raise RallyConfigError(f"`agents` keys in `{flow_file}` must be strings.")
        if not isinstance(raw_agent, dict):
            raise RallyConfigError(f"Agent `{agent_key}` in `{flow_file}` must decode to a mapping.")
        allowed_skills = _require_flow_agent_string_list(
            raw_agent,
            key="allowed_skills",
            agent_key=agent_key,
            flow_file=flow_file,
        )
        system_skills = _require_flow_agent_string_list(
            raw_agent,
            key="system_skills",
            agent_key=agent_key,
            flow_file=flow_file,
        )
        seen: set[str] = set()
        for skill_name in system_skills:
            if skill_name in seen:
                raise RallyConfigError(
                    f"`system_skills` for agent `{agent_key}` in `{flow_file}` "
                    f"must not repeat `{skill_name}`."
                )
            seen.add(skill_name)
            validate_system_skill_name(skill_name)
        overlap = sorted(set(allowed_skills) & set(system_skills))
        if overlap:
            joined = ", ".join(f"`{name}`" for name in overlap)
            raise RallyConfigError(
                f"Agent `{agent_key}` in `{flow_file}` lists {joined} in both "
                "`allowed_skills` and `system_skills`. A skill belongs to exactly one tier."
            )
        allowed_skills_by_agent_key[agent_key] = allowed_skills
        system_skills_by_agent_key[agent_key] = system_skills
    return allowed_skills_by_agent_key, system_skills_by_agent_key


def _require_flow_agent_string_list(
    raw_agent: dict,
    *,
    key: str,
    agent_key: str,
    flow_file: Path,
) -> tuple[str, ...]:
    raw_value = raw_agent.get(key)
    if raw_value is None or (
        not isinstance(raw_value, list)
        or not all(isinstance(item, str) and item for item in raw_value)
    ):
        raise RallyConfigError(
            f"Agent `{agent_key}` in `{flow_file}` must define `{key}` as a list of non-empty strings."
        )
    return tuple(raw_value)


def _should_emit_skill_build(
    *,
    workspace: WorkspaceContext,
    repo_root: Path,
    skill_name: str,
    builtins: RallyBuiltinAssets,
) -> bool:
    bundle = resolve_skill_bundle_source(
        repo_root=repo_root,
        skill_name=skill_name,
        builtins=builtins,
    )
    return bundle.kind == "doctrine"


def _emit_doctrine_targets(
    *,
    config_path: Path,
    builtins: RallyBuiltinAssets,
    emit_kind: DoctrineEmitKind,
    target_names: tuple[str, ...],
    failure_label: str,
) -> None:
    try:
        from doctrine.diagnostics import DoctrineError
        from doctrine.emit_common import load_emit_targets
        from doctrine.emit_docs import emit_target
        from doctrine.emit_skill import emit_target_skill
    except ImportError as exc:
        raise RallyConfigError(f"Failed to import Doctrine while rebuilding {failure_label}: {exc}.") from exc

    try:
        provided_prompt_roots = _provided_prompt_roots_for_config(
            config_path=config_path,
            builtins=builtins,
        )
        emit_targets = load_emit_targets(
            config_path,
            provided_prompt_roots=provided_prompt_roots,
        )
        for target_name in target_names:
            target = emit_targets.get(target_name)
            if target is None:
                raise RallyConfigError(f"Doctrine emit target `{target_name}` is missing from `{config_path}`.")
            if emit_kind == "docs":
                emit_target(target)
            elif emit_kind == "skill":
                emit_target_skill(target)
            else:
                raise AssertionError(f"Unknown Doctrine emit kind: {emit_kind}")
    except DoctrineError as exc:
        raise RallyConfigError(f"Failed to rebuild {failure_label} with Doctrine: {exc}") from exc


def _provided_prompt_roots_for_config(
    *,
    config_path: Path,
    builtins: RallyBuiltinAssets,
) -> tuple[object, ...]:
    configured_roots = _configured_additional_prompt_roots(config_path)
    builtin_root = builtins.stdlib_prompts_root.resolve()
    if builtin_root in configured_roots:
        return ()
    for configured_root in configured_roots:
        if configured_root.parts[-3:] == ("stdlib", "rally", "prompts"):
            raise RallyConfigError(
                f"`{config_path}` must not configure Rally stdlib prompt root `{configured_root}`. "
                "Rally passes its stdlib prompt root to Doctrine during framework-managed builds."
            )
    return builtins.provided_prompt_roots()


def _configured_additional_prompt_roots(config_path: Path) -> set[Path]:
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RallyConfigError(f"`{config_path}` must contain valid TOML.") from exc
    compile_config = raw.get("tool", {}).get("doctrine", {}).get("compile", {})
    if not isinstance(compile_config, dict):
        return set()
    raw_roots = compile_config.get("additional_prompt_roots", [])
    if raw_roots is None:
        return set()
    if not isinstance(raw_roots, list) or not all(isinstance(root, str) for root in raw_roots):
        raise RallyConfigError("`tool.doctrine.compile.additional_prompt_roots` must be a list of strings.")
    return {
        (config_path.parent / root).resolve() if not Path(root).is_absolute() else Path(root).resolve()
        for root in raw_roots
    }


def _prune_retired_compiled_agent_artifacts(
    build_agents_root: Path,
    *,
    expected_agent_slugs: tuple[str, ...],
) -> None:
    if not build_agents_root.is_dir():
        return
    expected_dirs = set(expected_agent_slugs)
    for existing_dir in sorted(build_agents_root.iterdir()):
        if not existing_dir.is_dir() or existing_dir.name in expected_dirs:
            continue
        shutil.rmtree(existing_dir)
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
    builtins: RallyBuiltinAssets,
) -> None:
    prompt_roots: list[Path] = [
        workspace.workspace_root / "flows" / flow_name / "prompts",
        builtins.stdlib_prompts_root,
    ]
    for skill_name in skill_names:
        bundle = resolve_skill_bundle_source(
            repo_root=workspace.workspace_root,
            skill_name=skill_name,
            builtins=builtins,
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
