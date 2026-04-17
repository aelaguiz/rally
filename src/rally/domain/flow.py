from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from rally.domain.rooted_path import RootedPath

_FLOW_KEY_PREFIX_RE = re.compile(r"^\d+_")
_FLOW_CODE_RE = re.compile(r"^[A-Z]{3}$")
FieldPath = tuple[str, ...]


def flow_agent_key_to_slug(agent_key: str) -> str:
    slug = _FLOW_KEY_PREFIX_RE.sub("", agent_key)
    if not slug:
        raise ValueError("Flow agent key must resolve to a non-empty compiled slug.")
    return slug


def normalize_flow_code(flow_code: str) -> str:
    normalized = flow_code.strip()
    if not _FLOW_CODE_RE.fullmatch(normalized):
        raise ValueError("Flow code must be exactly three uppercase ASCII letters.")
    return normalized


@dataclass(frozen=True)
class AdapterConfig:
    name: str
    args: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


@dataclass(frozen=True)
class FinalOutputContract:
    exists: bool
    contract_version: int
    declaration_key: str | None
    declaration_name: str | None
    format_mode: str | None
    schema_profile: str | None
    generated_schema_file: Path | None
    metadata_file: Path | None


@dataclass(frozen=True)
class IoTargetContract:
    key: str
    title: str
    config: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))


@dataclass(frozen=True)
class IoShapeContract:
    name: str
    title: str


@dataclass(frozen=True)
class IoSchemaContract:
    name: str
    title: str
    profile: str


@dataclass(frozen=True)
class PreviousTurnInputContract:
    input_key: str
    input_name: str
    selector_kind: str
    selector_text: str
    resolved_declaration_key: str | None
    resolved_declaration_name: str | None
    derived_contract_mode: str
    requirement: str
    target: IoTargetContract | None = None
    shape: IoShapeContract | None = None
    schema: IoSchemaContract | None = None
    binding_path: FieldPath | None = None


@dataclass(frozen=True)
class EmittedOutputContract:
    declaration_key: str
    declaration_name: str
    title: str
    target: IoTargetContract
    derived_contract_mode: str
    readback_mode: str
    requires_final_output: bool
    shape: IoShapeContract | None = None
    schema: IoSchemaContract | None = None


@dataclass(frozen=True)
class OutputBindingContract:
    binding_path: FieldPath
    declaration_key: str


@dataclass(frozen=True)
class IoContract:
    previous_turn_inputs: tuple[PreviousTurnInputContract, ...]
    outputs: tuple[EmittedOutputContract, ...]
    output_bindings: tuple[OutputBindingContract, ...]


@dataclass(frozen=True)
class RouteChoiceMemberContract:
    member_key: str
    member_title: str
    member_wire: str


@dataclass(frozen=True)
class RouteTargetContract:
    key: str
    name: str
    title: str
    module_parts: tuple[str, ...]


@dataclass(frozen=True)
class RouteBranchContract:
    target: RouteTargetContract
    label: str
    summary: str
    choice_members: tuple[RouteChoiceMemberContract, ...]


@dataclass(frozen=True)
class RouteSelectorContract:
    surface: str
    field_path: FieldPath
    null_behavior: str


@dataclass(frozen=True)
class RouteContract:
    exists: bool
    behavior: str
    has_unrouted_branch: bool
    unrouted_review_verdicts: tuple[str, ...]
    branches: tuple[RouteBranchContract, ...]
    selector: RouteSelectorContract | None = None


@dataclass(frozen=True)
class ReviewOutputContract:
    declaration_key: str | None
    declaration_name: str | None


@dataclass(frozen=True)
class ReviewFinalResponseContract:
    mode: str
    declaration_key: str | None
    declaration_name: str | None
    review_fields: Mapping[str, FieldPath]
    control_ready: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_fields", MappingProxyType(dict(self.review_fields)))


@dataclass(frozen=True)
class ReviewOutcomeContract:
    exists: bool
    verdict: str
    route_behavior: str


@dataclass(frozen=True)
class ReviewContract:
    exists: bool
    comment_output: ReviewOutputContract
    carrier_fields: Mapping[str, FieldPath]
    final_response: ReviewFinalResponseContract
    outcomes: Mapping[str, ReviewOutcomeContract]

    def __post_init__(self) -> None:
        object.__setattr__(self, "carrier_fields", MappingProxyType(dict(self.carrier_fields)))
        object.__setattr__(self, "outcomes", MappingProxyType(dict(self.outcomes)))


@dataclass(frozen=True)
class CompiledAgentContract:
    name: str
    slug: str
    entrypoint: Path
    markdown_path: Path
    metadata_file: Path
    contract_version: int
    final_output: FinalOutputContract
    io: IoContract | None = None
    route: RouteContract | None = None
    review: ReviewContract | None = None


@dataclass(frozen=True)
class FlowAgent:
    key: str
    slug: str
    timeout_sec: int
    allowed_skills: tuple[str, ...]
    system_skills: tuple[str, ...]
    allowed_mcps: tuple[str, ...]
    compiled: CompiledAgentContract


@dataclass(frozen=True)
class FlowHostInputs:
    required_env: tuple[str, ...]
    required_files: tuple[RootedPath, ...]
    required_directories: tuple[RootedPath, ...]


@dataclass(frozen=True)
class FlowDefinition:
    name: str
    code: str
    root_dir: Path
    flow_file: Path
    build_agents_dir: Path
    setup_home_script: Path | None
    start_agent_key: str
    max_command_turns: int
    guarded_git_repos: tuple[Path, ...]
    runtime_env: Mapping[str, str]
    host_inputs: FlowHostInputs
    agents: Mapping[str, FlowAgent]
    adapter: AdapterConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_env", MappingProxyType(dict(self.runtime_env)))
        object.__setattr__(self, "agents", MappingProxyType(dict(self.agents)))

    def agent(self, agent_key: str) -> FlowAgent:
        return self.agents[agent_key]

    def agent_by_slug(self, agent_slug: str) -> FlowAgent:
        for agent in self.agents.values():
            if agent.slug == agent_slug:
                return agent
        raise KeyError(agent_slug)
