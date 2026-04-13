from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    flow_agent_key_to_slug,
)
from rally.errors import RallyConfigError

SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS = frozenset({1})


def load_flow_definition(*, repo_root: Path, flow_name: str) -> FlowDefinition:
    flow_root = repo_root / "flows" / flow_name
    flow_file = flow_root / "flow.yaml"
    if not flow_file.is_file():
        raise RallyConfigError(f"Flow definition does not exist: `{flow_file}`.")

    payload = _load_yaml_mapping(flow_file)
    flow_payload_name = _require_string(payload, "name", context="flow.yaml")
    if flow_payload_name != flow_name:
        raise RallyConfigError(
            f"Flow name mismatch in `{flow_file}`: expected `{flow_name}`, found `{flow_payload_name}`."
        )

    build_agents_dir = flow_root / "build" / "agents"
    compiled_agents = _load_compiled_agents(repo_root=repo_root, build_agents_dir=build_agents_dir)

    agents_payload = _require_mapping(payload, "agents", context="flow.yaml")
    agents: dict[str, FlowAgent] = {}
    for agent_key, agent_payload in agents_payload.items():
        if not isinstance(agent_key, str):
            raise RallyConfigError(f"`agents` keys in `{flow_file}` must be strings.")
        agent_mapping = _require_mapping_value(agent_payload, context=f"agent `{agent_key}`")
        agent_slug = flow_agent_key_to_slug(agent_key)
        compiled = compiled_agents.get(agent_slug)
        if compiled is None:
            raise RallyConfigError(
                f"Compiled agent contract missing for flow agent `{agent_key}`. "
                f"Expected `{build_agents_dir / agent_slug / 'AGENTS.contract.json'}`."
            )
        agents[agent_key] = FlowAgent(
            key=agent_key,
            slug=agent_slug,
            timeout_sec=_require_int(agent_mapping, "timeout_sec", context=f"agent `{agent_key}`"),
            allowed_skills=_require_string_list(agent_mapping, "allowed_skills", context=f"agent `{agent_key}`"),
            allowed_mcps=_require_string_list(agent_mapping, "allowed_mcps", context=f"agent `{agent_key}`"),
            compiled=compiled,
        )

    start_agent_key = _require_string(payload, "start_agent", context="flow.yaml")
    if start_agent_key not in agents:
        raise RallyConfigError(
            f"Start agent `{start_agent_key}` from `{flow_file}` is not declared under `agents`."
        )

    runtime_payload = _require_mapping(payload, "runtime", context="flow.yaml")
    adapter_name = _require_string(runtime_payload, "adapter", context="runtime")
    adapter_args = _require_mapping(runtime_payload, "adapter_args", context="runtime")
    prompt_entrypoint = _resolve_repo_relative_file(
        repo_root=repo_root,
        relative_path=f"flows/{flow_name}/prompts/AGENTS.prompt",
        context="flow prompt entrypoint",
    )

    setup_home_script_rel = payload.get("setup_home_script")
    setup_home_script = None
    if setup_home_script_rel is not None:
        if not isinstance(setup_home_script_rel, str) or not setup_home_script_rel:
            raise RallyConfigError("`setup_home_script` must be a non-empty string when present.")
        setup_home_script = _resolve_flow_relative_file(
            flow_root=flow_root,
            relative_path=setup_home_script_rel,
            context="setup_home_script",
        )

    return FlowDefinition(
        name=flow_name,
        root_dir=flow_root,
        flow_file=flow_file,
        prompt_entrypoint=prompt_entrypoint,
        build_agents_dir=build_agents_dir,
        setup_home_script=setup_home_script,
        start_agent_key=start_agent_key,
        agents=agents,
        adapter=AdapterConfig(name=adapter_name, args=adapter_args),
    )


def _load_compiled_agents(*, repo_root: Path, build_agents_dir: Path) -> dict[str, CompiledAgentContract]:
    if not build_agents_dir.is_dir():
        raise RallyConfigError(f"Compiled agent directory is missing: `{build_agents_dir}`.")

    compiled_agents: dict[str, CompiledAgentContract] = {}
    for agent_dir in sorted(build_agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        markdown_path = agent_dir / "AGENTS.md"
        contract_path = agent_dir / "AGENTS.contract.json"
        if not markdown_path.is_file() or not contract_path.is_file():
            raise RallyConfigError(
                f"Compiled agent directory `{agent_dir}` must contain both `AGENTS.md` and `AGENTS.contract.json`."
            )
        contract = _load_compiled_agent_contract(
            repo_root=repo_root,
            agent_dir=agent_dir,
            markdown_path=markdown_path,
            contract_path=contract_path,
        )
        if contract.slug in compiled_agents:
            raise RallyConfigError(
                f"Duplicate compiled agent slug `{contract.slug}` under `{build_agents_dir}`."
            )
        compiled_agents[contract.slug] = contract

    if not compiled_agents:
        raise RallyConfigError(f"No compiled agents were found under `{build_agents_dir}`.")
    return compiled_agents


def _load_compiled_agent_contract(
    *,
    repo_root: Path,
    agent_dir: Path,
    markdown_path: Path,
    contract_path: Path,
) -> CompiledAgentContract:
    payload = _load_json_mapping(contract_path)
    contract_version = _require_int(payload, "contract_version", context=str(contract_path))
    if contract_version not in SUPPORTED_COMPILED_AGENT_CONTRACT_VERSIONS:
        raise RallyConfigError(
            f"Unsupported compiled agent contract version `{contract_version}` in `{contract_path}`."
        )

    agent_payload = _require_mapping(payload, "agent", context=str(contract_path))
    slug = _require_string(agent_payload, "slug", context=f"{contract_path} agent")
    if slug != agent_dir.name:
        raise RallyConfigError(
            f"Compiled agent slug mismatch for `{contract_path}`: directory is `{agent_dir.name}` but contract says `{slug}`."
        )

    final_output_payload = _require_mapping(payload, "final_output", context=str(contract_path))
    if not final_output_payload.get("exists"):
        raise RallyConfigError(
            f"Compiled agent `{slug}` does not declare a final output in `{contract_path}`."
        )

    schema_file = _resolve_repo_relative_file(
        repo_root=repo_root,
        relative_path=_require_string(final_output_payload, "schema_file", context=f"{contract_path} final_output"),
        context=f"{contract_path} final_output.schema_file",
    )
    example_file = _resolve_repo_relative_file(
        repo_root=repo_root,
        relative_path=_require_string(final_output_payload, "example_file", context=f"{contract_path} final_output"),
        context=f"{contract_path} final_output.example_file",
    )

    format_mode = _require_string(final_output_payload, "format_mode", context=f"{contract_path} final_output")
    if format_mode != "json_schema":
        raise RallyConfigError(
            f"Compiled agent `{slug}` must use `json_schema` final output mode, found `{format_mode}`."
        )

    _validate_handoff_requires_next_owner(schema_file)

    return CompiledAgentContract(
        name=_require_string(agent_payload, "name", context=f"{contract_path} agent"),
        slug=slug,
        entrypoint=_resolve_repo_relative_file(
            repo_root=repo_root,
            relative_path=_require_string(agent_payload, "entrypoint", context=f"{contract_path} agent"),
            context=f"{contract_path} agent.entrypoint",
        ),
        markdown_path=markdown_path,
        contract_path=contract_path,
        contract_version=contract_version,
        final_output=FinalOutputContract(
            exists=True,
            declaration_key=_require_string(
                final_output_payload,
                "declaration_key",
                context=f"{contract_path} final_output",
            ),
            declaration_name=_require_string(
                final_output_payload,
                "declaration_name",
                context=f"{contract_path} final_output",
            ),
            format_mode=format_mode,
            schema_profile=_require_string(
                final_output_payload,
                "schema_profile",
                context=f"{contract_path} final_output",
            ),
            schema_file=schema_file,
            example_file=example_file,
        ),
    )


def _validate_handoff_requires_next_owner(schema_file: Path) -> None:
    payload = _load_json_mapping(schema_file)
    branches = payload.get("oneOf")
    if not isinstance(branches, list):
        raise RallyConfigError(
            f"Turn-result schema `{schema_file}` must use top-level `oneOf` branches."
        )
    for branch in branches:
        if not isinstance(branch, Mapping):
            continue
        properties = branch.get("properties")
        if not isinstance(properties, Mapping):
            continue
        kind = properties.get("kind")
        if not isinstance(kind, Mapping) or kind.get("const") != "handoff":
            continue
        required = branch.get("required")
        if isinstance(required, list) and "next_owner" in required:
            return
        break
    raise RallyConfigError(
        f"Turn-result schema `{schema_file}` must require `next_owner` for `handoff`."
    )


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise RallyConfigError(f"`{path}` must contain a top-level mapping.")
    return payload


def _load_json_mapping(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise RallyConfigError(f"`{path}` must contain a top-level object.")
    return payload


def _resolve_repo_relative_file(*, repo_root: Path, relative_path: str, context: str) -> Path:
    if Path(relative_path).is_absolute():
        raise RallyConfigError(f"{context} must be repo-root-relative, not absolute: `{relative_path}`.")
    candidate = (repo_root / relative_path).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RallyConfigError(
            f"{context} escapes the Rally repo root: `{relative_path}`."
        ) from exc
    if not candidate.is_file():
        raise RallyConfigError(f"{context} does not exist: `{candidate}`.")
    return candidate


def _resolve_flow_relative_file(*, flow_root: Path, relative_path: str, context: str) -> Path:
    candidate = (flow_root / relative_path).resolve()
    try:
        candidate.relative_to(flow_root.resolve())
    except ValueError as exc:
        raise RallyConfigError(
            f"{context} escapes the flow root `{flow_root}`: `{relative_path}`."
        ) from exc
    if not candidate.is_file():
        raise RallyConfigError(f"{context} does not exist: `{candidate}`.")
    return candidate


def _require_mapping(payload: Mapping[str, Any], key: str, *, context: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise RallyConfigError(f"`{key}` must be a mapping in {context}.")
    return value


def _require_mapping_value(value: object, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RallyConfigError(f"{context} must be a mapping.")
    return value


def _require_string(payload: Mapping[str, Any], key: str, *, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise RallyConfigError(f"`{key}` must be a non-empty string in {context}.")
    return value


def _require_int(payload: Mapping[str, Any], key: str, *, context: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise RallyConfigError(f"`{key}` must be an integer in {context}.")
    return value


def _require_string_list(payload: Mapping[str, Any], key: str, *, context: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RallyConfigError(f"`{key}` must be a list of non-empty strings in {context}.")
    return tuple(value)
