from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from rally.adapters.registry import get_adapter
from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FieldPath,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
    ReviewContract,
    ReviewFinalResponseContract,
    ReviewOutcomeContract,
    ReviewOutputContract,
    flow_agent_key_to_slug,
    normalize_flow_code,
)
from rally.domain.rooted_path import (
    FLOW_ROOT,
    HOME_ROOT,
    HOST_ROOT,
    WORKSPACE_ROOT,
    PathRoot,
    RootedPath,
    maybe_parse_rooted_path,
    parse_rooted_path,
    resolve_rooted_path,
)
from rally.errors import RallyConfigError

SUPPORTED_FINAL_OUTPUT_CONTRACT_VERSIONS = frozenset({1})
_FLOW_RUNTIME_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FLOW_RUNTIME_ENV_ALLOWED_ROOTS = frozenset({HOME_ROOT, FLOW_ROOT, WORKSPACE_ROOT, HOST_ROOT})
_RESERVED_FLOW_RUNTIME_ENV_KEYS = frozenset({"CODEX_HOME", "ENABLE_CLAUDEAI_MCP_SERVERS"})


def load_flow_code(*, repo_root: Path, flow_name: str) -> str:
    _flow_root, flow_file, payload = _load_flow_payload(repo_root=repo_root, flow_name=flow_name)
    _require_matching_flow_name(flow_name=flow_name, flow_file=flow_file, payload=payload)
    return _require_flow_code(payload=payload, flow_file=flow_file)


def load_flow_definition(
    *,
    repo_root: Path,
    flow_name: str,
) -> FlowDefinition:
    flow_root, flow_file, payload = _load_flow_payload(repo_root=repo_root, flow_name=flow_name)
    _require_matching_flow_name(flow_name=flow_name, flow_file=flow_file, payload=payload)
    flow_code = _require_flow_code(payload=payload, flow_file=flow_file)

    build_agents_dir = flow_root / "build" / "agents"
    compiled_agents = _load_compiled_agents(
        repo_root=repo_root,
        build_agents_dir=build_agents_dir,
    )

    agents_payload = _require_mapping(payload, "agents", context="flow.yaml")
    agents: dict[str, FlowAgent] = {}
    for agent_key, agent_payload in agents_payload.items():
        if not isinstance(agent_key, str):
            raise RallyConfigError(f"`agents` keys in `{flow_file}` must be strings.")
        agent_mapping = _require_mapping_value(agent_payload, context=f"agent `{agent_key}`")
        expected_slug = flow_agent_key_to_slug(agent_key)
        compiled = compiled_agents.get(expected_slug)
        if compiled is None:
            raise RallyConfigError(
                f"Compiled agent contract missing for flow agent `{agent_key}`. "
                f"Expected `{build_agents_dir / expected_slug / 'final_output.contract.json'}`."
            )
        agents[agent_key] = FlowAgent(
            key=agent_key,
            # The compiled contract slug is the carried source of truth once the
            # loader has validated it against the flow-owned agent key.
            slug=compiled.slug,
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
    max_command_turns = _require_int(runtime_payload, "max_command_turns", context="runtime")
    if max_command_turns < 1:
        raise RallyConfigError("`runtime.max_command_turns` must be an integer >= 1.")
    guarded_git_repos = _require_run_home_relative_paths(
        runtime_payload,
        "guarded_git_repos",
        context="runtime",
    )
    runtime_env = _load_runtime_env(runtime_payload=runtime_payload)
    adapter_args = _require_mapping(runtime_payload, "adapter_args", context="runtime")
    get_adapter(adapter_name).validate_args(args=adapter_args)
    prompt_input_command_raw = runtime_payload.get("prompt_input_command")
    prompt_input_command = None
    if prompt_input_command_raw is not None:
        if not isinstance(prompt_input_command_raw, str) or not prompt_input_command_raw:
            raise RallyConfigError("`runtime.prompt_input_command` must be a non-empty string when present.")
        prompt_input_command = _resolve_rooted_existing_file(
            raw_value=prompt_input_command_raw,
            repo_root=repo_root,
            flow_root=flow_root,
            context="runtime.prompt_input_command",
            allowed_roots={FLOW_ROOT},
            example="flow:setup/prompt_inputs.py",
        )
    prompt_entrypoint = _resolve_repo_relative_file(
        repo_root=repo_root,
        relative_path=f"flows/{flow_name}/prompts/AGENTS.prompt",
        context="flow prompt entrypoint",
    )

    setup_home_script_raw = payload.get("setup_home_script")
    setup_home_script = None
    if setup_home_script_raw is not None:
        if not isinstance(setup_home_script_raw, str) or not setup_home_script_raw:
            raise RallyConfigError("`setup_home_script` must be a non-empty string when present.")
        setup_home_script = _resolve_rooted_existing_file(
            raw_value=setup_home_script_raw,
            repo_root=repo_root,
            flow_root=flow_root,
            context="setup_home_script",
            allowed_roots={FLOW_ROOT},
            example="flow:setup/prepare_home.sh",
        )
    host_inputs = _load_host_inputs(payload=payload)

    return FlowDefinition(
        name=flow_name,
        code=flow_code,
        root_dir=flow_root,
        flow_file=flow_file,
        prompt_entrypoint=prompt_entrypoint,
        build_agents_dir=build_agents_dir,
        setup_home_script=setup_home_script,
        start_agent_key=start_agent_key,
        max_command_turns=max_command_turns,
        guarded_git_repos=guarded_git_repos,
        runtime_env=runtime_env,
        host_inputs=host_inputs,
        agents=agents,
        adapter=AdapterConfig(name=adapter_name, args=adapter_args, prompt_input_command=prompt_input_command),
    )


def _load_flow_payload(*, repo_root: Path, flow_name: str) -> tuple[Path, Path, Mapping[str, Any]]:
    flow_root = repo_root / "flows" / flow_name
    flow_file = flow_root / "flow.yaml"
    if not flow_file.is_file():
        raise RallyConfigError(f"Flow definition does not exist: `{flow_file}`.")
    return flow_root, flow_file, _load_yaml_mapping(flow_file)


def _require_matching_flow_name(*, flow_name: str, flow_file: Path, payload: Mapping[str, Any]) -> None:
    flow_payload_name = _require_string(payload, "name", context="flow.yaml")
    if flow_payload_name != flow_name:
        raise RallyConfigError(
            f"Flow name mismatch in `{flow_file}`: expected `{flow_name}`, found `{flow_payload_name}`."
        )


def _require_flow_code(*, payload: Mapping[str, Any], flow_file: Path) -> str:
    raw_flow_code = _require_string(payload, "code", context="flow.yaml")
    try:
        return normalize_flow_code(raw_flow_code)
    except ValueError as exc:
        raise RallyConfigError(f"`code` in `{flow_file}` must be exactly three uppercase ASCII letters.") from exc


def _load_compiled_agents(
    *,
    repo_root: Path,
    build_agents_dir: Path,
) -> dict[str, CompiledAgentContract]:
    if not build_agents_dir.is_dir():
        raise RallyConfigError(f"Compiled agent directory is missing: `{build_agents_dir}`.")

    compiled_agents: dict[str, CompiledAgentContract] = {}
    for agent_dir in sorted(build_agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        markdown_path = agent_dir / "AGENTS.md"
        metadata_file = agent_dir / "final_output.contract.json"
        if not markdown_path.is_file() or not metadata_file.is_file():
            raise RallyConfigError(
                f"Compiled agent directory `{agent_dir}` must contain both `AGENTS.md` and `final_output.contract.json`."
            )
        contract = _load_compiled_agent_contract(
            repo_root=repo_root,
            agent_dir=agent_dir,
            markdown_path=markdown_path,
            metadata_file=metadata_file,
        )
        if contract.slug in compiled_agents:
            raise RallyConfigError(
                f"Duplicate compiled agent slug `{contract.slug}` under `{build_agents_dir}`."
            )
        compiled_agents[contract.slug] = contract

    if not compiled_agents:
        raise RallyConfigError(f"No compiled agents were found under `{build_agents_dir}`.")
    return compiled_agents


def _load_host_inputs(*, payload: Mapping[str, Any]) -> FlowHostInputs:
    raw_host_inputs = payload.get("host_inputs")
    if raw_host_inputs is None:
        return FlowHostInputs(required_env=(), required_files=(), required_directories=())
    host_inputs_payload = _require_mapping(payload, "host_inputs", context="flow.yaml")
    return FlowHostInputs(
        required_env=_require_unique_string_list(
            host_inputs_payload,
            "required_env",
            context="host_inputs",
        ),
        required_files=_require_unique_rooted_path_list(
            host_inputs_payload,
            "required_files",
            context="host_inputs",
            allowed_roots={WORKSPACE_ROOT, HOST_ROOT},
            example="host:~/config/.env",
        ),
        required_directories=_require_unique_rooted_path_list(
            host_inputs_payload,
            "required_directories",
            context="host_inputs",
            allowed_roots={WORKSPACE_ROOT, HOST_ROOT},
            example="workspace:fixtures/data",
        ),
    )


def _load_runtime_env(*, runtime_payload: Mapping[str, Any]) -> dict[str, str]:
    raw_env = runtime_payload.get("env")
    if raw_env is None:
        return {}
    env_payload = _require_mapping(runtime_payload, "env", context="runtime")

    runtime_env: dict[str, str] = {}
    for key, value in env_payload.items():
        if not isinstance(key, str) or not _FLOW_RUNTIME_ENV_KEY_RE.fullmatch(key):
            raise RallyConfigError(
                "`runtime.env` keys must be env var names like `PROJECT_ROOT`."
            )
        if key.startswith("RALLY_") or key in _RESERVED_FLOW_RUNTIME_ENV_KEYS:
            raise RallyConfigError(f"`runtime.env.{key}` is reserved for Rally or the adapter.")
        if not isinstance(value, str) or not value:
            raise RallyConfigError(f"`runtime.env.{key}` must be a non-empty string in runtime.")
        maybe_parse_rooted_path(
            value,
            context=f"`runtime.env.{key}`",
            allowed_roots=_FLOW_RUNTIME_ENV_ALLOWED_ROOTS,
            example="workspace:fixtures/project",
        )
        runtime_env[key] = value
    return runtime_env


def _load_compiled_agent_contract(
    *,
    repo_root: Path,
    agent_dir: Path,
    markdown_path: Path,
    metadata_file: Path,
) -> CompiledAgentContract:
    payload = _load_json_mapping(metadata_file)
    contract_version = _require_int(payload, "contract_version", context=str(metadata_file))
    if contract_version not in SUPPORTED_FINAL_OUTPUT_CONTRACT_VERSIONS:
        raise RallyConfigError(
            f"Unsupported final-output contract version `{contract_version}` in `{metadata_file}`."
        )

    agent_payload = _require_mapping(payload, "agent", context=str(metadata_file))
    slug = _require_string(agent_payload, "slug", context=f"{metadata_file} agent")
    if slug != agent_dir.name:
        raise RallyConfigError(
            f"Compiled agent slug mismatch for `{metadata_file}`: directory is `{agent_dir.name}` but contract says `{slug}`."
        )

    final_output_payload = _require_mapping(payload, "final_output", context=str(metadata_file))
    if not final_output_payload.get("exists"):
        raise RallyConfigError(
            f"Compiled agent `{slug}` does not declare a final output in `{metadata_file}`."
        )

    generated_schema_file = _resolve_agent_relative_existing_file(
        agent_dir=agent_dir,
        raw_value=_require_string(
            final_output_payload,
            "emitted_schema_relpath",
            context=f"{metadata_file} final_output",
        ),
        context=f"{metadata_file} final_output.emitted_schema_relpath",
    )

    format_mode = _require_string(final_output_payload, "format_mode", context=f"{metadata_file} final_output")
    if format_mode != "json_object":
        raise RallyConfigError(
            f"Compiled agent `{slug}` must use `json_object` final output mode, found `{format_mode}`."
        )

    final_output = FinalOutputContract(
        exists=True,
        contract_version=contract_version,
        declaration_key=_require_string(
            final_output_payload,
            "declaration_key",
            context=f"{metadata_file} final_output",
        ),
        declaration_name=_require_string(
            final_output_payload,
            "declaration_name",
            context=f"{metadata_file} final_output",
        ),
        format_mode=format_mode,
        schema_profile=_require_string(
            final_output_payload,
            "schema_profile",
            context=f"{metadata_file} final_output",
        ),
        generated_schema_file=generated_schema_file,
        metadata_file=metadata_file,
    )
    review = _load_review_contract(payload=payload, contract_path=metadata_file)
    if review is None:
        _validate_turn_result_schema(generated_schema_file)
    else:
        _validate_review_native_contract(
            slug=slug,
            contract_path=metadata_file,
            final_output=final_output,
            review=review,
        )

    return CompiledAgentContract(
        name=_require_string(agent_payload, "name", context=f"{metadata_file} agent"),
        slug=slug,
        entrypoint=_resolve_repo_relative_file(
            repo_root=repo_root,
            relative_path=_require_string(agent_payload, "entrypoint", context=f"{metadata_file} agent"),
            context=f"{metadata_file} agent.entrypoint",
        ),
        markdown_path=markdown_path,
        metadata_file=metadata_file,
        contract_version=contract_version,
        final_output=final_output,
        review=review,
    )


def _validate_turn_result_schema(schema_file: Path) -> None:
    payload = _load_json_mapping(schema_file)
    properties = payload.get("properties")
    required = payload.get("required")
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise RallyConfigError(
            f"Turn-result schema `{schema_file}` must declare object properties and required fields."
        )
    expected_fields = {"kind", "next_owner", "summary", "reason", "sleep_duration_seconds"}
    if set(required) != expected_fields:
        raise RallyConfigError(
            f"Turn-result schema `{schema_file}` must require {sorted(expected_fields)}."
        )
    kind_field = properties.get("kind")
    if not isinstance(kind_field, Mapping):
        raise RallyConfigError(f"Turn-result schema `{schema_file}` must define `properties.kind`.")


def _validate_review_native_contract(
    *,
    slug: str,
    contract_path: Path,
    final_output: FinalOutputContract,
    review: ReviewContract,
) -> None:
    if not review.final_response.control_ready:
        raise RallyConfigError(
            f"Compiled review agent `{slug}` is not control-ready in `{contract_path}`."
        )
    if review.final_response.mode not in {"carrier", "split"}:
        raise RallyConfigError(
            f"Compiled review agent `{slug}` uses unsupported final review mode "
            f"`{review.final_response.mode}` in `{contract_path}`."
        )
    if review.final_response.mode == "carrier":
        if review.comment_output.declaration_key != final_output.declaration_key:
            raise RallyConfigError(
                f"Compiled review agent `{slug}` says the final response is the review carrier, "
                f"but `{contract_path}` points final_output at `{final_output.declaration_key}`."
            )
        return
    if review.final_response.declaration_key != final_output.declaration_key:
        raise RallyConfigError(
            f"Compiled review agent `{slug}` split final response does not match "
            f"`final_output` in `{contract_path}`."
        )


def _load_review_contract(
    *,
    payload: Mapping[str, Any],
    contract_path: Path,
) -> ReviewContract | None:
    raw_review = payload.get("review")
    if raw_review is None:
        return None
    review_payload = _require_mapping(payload, "review", context=str(contract_path))
    if not _require_bool(review_payload, "exists", context=f"{contract_path} review"):
        raise RallyConfigError(f"Compiled review block in `{contract_path}` must set `exists: true`.")

    comment_output_payload = _require_mapping(review_payload, "comment_output", context=f"{contract_path} review")
    final_response_payload = _require_mapping(review_payload, "final_response", context=f"{contract_path} review")
    outcomes_payload = _require_mapping(review_payload, "outcomes", context=f"{contract_path} review")

    return ReviewContract(
        exists=True,
        comment_output=ReviewOutputContract(
            declaration_key=_require_optional_string(
                comment_output_payload,
                "declaration_key",
                context=f"{contract_path} review.comment_output",
            ),
            declaration_name=_require_optional_string(
                comment_output_payload,
                "declaration_name",
                context=f"{contract_path} review.comment_output",
            ),
        ),
        carrier_fields=_require_field_paths(
            review_payload,
            "carrier_fields",
            context=f"{contract_path} review",
        ),
        final_response=ReviewFinalResponseContract(
            mode=_require_string(final_response_payload, "mode", context=f"{contract_path} review.final_response"),
            declaration_key=_require_optional_string(
                final_response_payload,
                "declaration_key",
                context=f"{contract_path} review.final_response",
            ),
            declaration_name=_require_optional_string(
                final_response_payload,
                "declaration_name",
                context=f"{contract_path} review.final_response",
            ),
            review_fields=_require_field_paths(
                final_response_payload,
                "review_fields",
                context=f"{contract_path} review.final_response",
            ),
            control_ready=_require_bool(
                final_response_payload,
                "control_ready",
                context=f"{contract_path} review.final_response",
            ),
        ),
        outcomes={
            outcome_key: ReviewOutcomeContract(
                exists=_require_bool(outcome_payload, "exists", context=f"{contract_path} review.outcomes.{outcome_key}"),
                verdict=_require_string(
                    outcome_payload,
                    "verdict",
                    context=f"{contract_path} review.outcomes.{outcome_key}",
                ),
                route_behavior=_require_string(
                    outcome_payload,
                    "route_behavior",
                    context=f"{contract_path} review.outcomes.{outcome_key}",
                ),
            )
            for outcome_key, outcome_payload in _iter_review_outcomes(
                outcomes_payload=outcomes_payload,
                contract_path=contract_path,
            )
        },
    )


def _iter_review_outcomes(
    *,
    outcomes_payload: Mapping[str, Any],
    contract_path: Path,
) -> tuple[tuple[str, Mapping[str, Any]], ...]:
    pairs: list[tuple[str, Mapping[str, Any]]] = []
    for outcome_key, outcome_value in outcomes_payload.items():
        if not isinstance(outcome_key, str) or not outcome_key:
            raise RallyConfigError(f"`review.outcomes` keys in `{contract_path}` must be non-empty strings.")
        pairs.append(
            (
                outcome_key,
                _require_mapping_value(
                    outcome_value,
                    context=f"{contract_path} review.outcomes.{outcome_key}",
                ),
            )
        )
    return tuple(pairs)


def _require_field_paths(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str,
) -> dict[str, FieldPath]:
    mapping = _require_mapping(payload, key, context=context)
    paths: dict[str, FieldPath] = {}
    for field_name, raw_path in mapping.items():
        if not isinstance(field_name, str) or not field_name:
            raise RallyConfigError(f"`{key}` keys in {context} must be non-empty strings.")
        if not isinstance(raw_path, str) or not raw_path:
            raise RallyConfigError(f"`{key}.{field_name}` must be a non-empty string in {context}.")
        parts = tuple(raw_path.split("."))
        if any(not part for part in parts):
            raise RallyConfigError(f"`{key}.{field_name}` in {context} must not contain empty path parts.")
        paths[field_name] = parts
    return paths


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


def _resolve_agent_relative_existing_file(*, agent_dir: Path, raw_value: str, context: str) -> Path:
    raw_path = Path(raw_value)
    if raw_path.is_absolute():
        raise RallyConfigError(f"{context} must be relative to the compiled agent directory: `{raw_value}`.")
    candidate = (agent_dir / raw_path).resolve()
    try:
        candidate.relative_to(agent_dir.resolve())
    except ValueError as exc:
        raise RallyConfigError(f"{context} must not escape its compiled agent directory: `{raw_value}`.") from exc
    if not candidate.is_file():
        raise RallyConfigError(f"{context} does not exist: `{candidate}`.")
    return candidate


def _resolve_repo_relative_file(*, repo_root: Path, relative_path: str, context: str) -> Path:
    if Path(relative_path).is_absolute():
        raise RallyConfigError(f"{context} must be repo-root-relative, not absolute: `{relative_path}`.")
    candidate = (repo_root / relative_path).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RallyConfigError(
            f"{context} escapes the Rally workspace root: `{relative_path}`."
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


def _require_optional_string(payload: Mapping[str, Any], key: str, *, context: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RallyConfigError(f"`{key}` must be a non-empty string or null in {context}.")
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, context: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise RallyConfigError(f"`{key}` must be a boolean in {context}.")
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


def _require_unique_string_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str,
) -> tuple[str, ...]:
    value = payload.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RallyConfigError(f"`{key}` must be a list of non-empty strings in {context}.")

    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RallyConfigError(f"`{key}[{index}]` must be a non-empty string in {context}.")
        normalized = item.strip()
        if normalized in seen:
            raise RallyConfigError(f"`{key}` must not repeat `{normalized}` in {context}.")
        seen.add(normalized)
        items.append(normalized)
    return tuple(items)


def _require_unique_rooted_path_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str,
    allowed_roots: set[PathRoot],
    example: str,
) -> tuple[RootedPath, ...]:
    value = payload.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RallyConfigError(f"`{key}` must be a list of rooted Rally paths in {context}.")

    items: list[RootedPath] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RallyConfigError(f"`{key}[{index}]` must be a non-empty rooted Rally path in {context}.")
        rooted_path = parse_rooted_path(
            item,
            context=f"`{key}[{index}]` in {context}",
            allowed_roots=allowed_roots,
            example=example,
        )
        normalized = str(rooted_path)
        if normalized in seen:
            raise RallyConfigError(f"`{key}` must not repeat `{normalized}` in {context}.")
        seen.add(normalized)
        items.append(rooted_path)
    return tuple(items)


def _require_run_home_relative_paths(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str,
) -> tuple[Path, ...]:
    value = payload.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RallyConfigError(f"`{key}` must be a list of `home:` paths in {context}.")

    paths: list[Path] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RallyConfigError(f"`{key}[{index}]` must be a non-empty `home:` path in {context}.")
        rooted_path = parse_rooted_path(
            item,
            context=f"`{key}[{index}]` in {context}",
            allowed_roots={HOME_ROOT},
            example="home:repos/demo_repo",
        )
        normalized = str(rooted_path)
        if normalized in seen:
            raise RallyConfigError(f"`{key}` must not repeat `{normalized}` in {context}.")
        seen.add(normalized)
        paths.append(Path(rooted_path.path_text))
    return tuple(paths)


def _resolve_rooted_existing_file(
    *,
    raw_value: str,
    repo_root: Path,
    flow_root: Path,
    context: str,
    allowed_roots: set[PathRoot],
    example: str,
) -> Path:
    if raw_value.startswith("flows/") or raw_value.startswith("stdlib/rally/"):
        return _resolve_repo_relative_file(
            repo_root=repo_root,
            relative_path=raw_value,
            context=context,
        )
    rooted_path = parse_rooted_path(
        raw_value,
        context=context,
        allowed_roots=allowed_roots,
        example=example,
    )
    candidate = resolve_rooted_path(
        rooted_path,
        workspace_root=repo_root,
        flow_root=flow_root,
        context=context,
    )
    if not candidate.is_file():
        raise RallyConfigError(f"{context} does not exist: `{candidate}`.")
    return candidate
