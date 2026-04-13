from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

_FLOW_KEY_PREFIX_RE = re.compile(r"^\d+_")
FieldPath = tuple[str, ...]


def flow_agent_key_to_slug(agent_key: str) -> str:
    slug = _FLOW_KEY_PREFIX_RE.sub("", agent_key)
    if not slug:
        raise ValueError("Flow agent key must resolve to a non-empty compiled slug.")
    return slug


@dataclass(frozen=True)
class AdapterConfig:
    name: str
    prompt_input_command: Path | None
    args: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


@dataclass(frozen=True)
class FinalOutputContract:
    exists: bool
    declaration_key: str | None
    declaration_name: str | None
    format_mode: str | None
    schema_profile: str | None
    schema_file: Path | None
    example_file: Path | None


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
    contract_path: Path
    contract_version: int
    final_output: FinalOutputContract
    review: ReviewContract | None = None


@dataclass(frozen=True)
class FlowAgent:
    key: str
    slug: str
    timeout_sec: int
    allowed_skills: tuple[str, ...]
    allowed_mcps: tuple[str, ...]
    compiled: CompiledAgentContract


@dataclass(frozen=True)
class FlowDefinition:
    name: str
    code: str
    root_dir: Path
    flow_file: Path
    prompt_entrypoint: Path
    build_agents_dir: Path
    setup_home_script: Path | None
    start_agent_key: str
    max_command_turns: int
    agents: Mapping[str, FlowAgent]
    adapter: AdapterConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "agents", MappingProxyType(dict(self.agents)))

    def agent(self, agent_key: str) -> FlowAgent:
        return self.agents[agent_key]

    def agent_by_slug(self, agent_slug: str) -> FlowAgent:
        for agent in self.agents.values():
            if agent.slug == agent_slug:
                return agent
        raise KeyError(agent_slug)
