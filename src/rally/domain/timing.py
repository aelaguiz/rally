from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCallRollup:
    tool_name: str
    count: int
    total_ms: int
    error_count: int

    @property
    def error_rate(self) -> float:
        return (self.error_count / self.count) if self.count else 0.0


@dataclass(frozen=True)
class CommandRollup:
    input_digest: str
    tool_name: str
    count: int
    total_ms: int
    error_count: int


@dataclass(frozen=True)
class TurnTokens:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass(frozen=True)
class TurnTiming:
    turn_index: int
    agent_key: str | None
    agent_slug: str | None
    kind: str
    started_at: str
    ended_at: str
    wall_ms: int
    tool_ms: int
    model_ms: int
    tools_called: int
    errors: int
    tokens: TurnTokens
    hot_tools: list[ToolCallRollup] = field(default_factory=list)
    hot_commands: list[CommandRollup] = field(default_factory=list)


@dataclass(frozen=True)
class AgentTiming:
    agent_slug: str
    agent_key: str | None
    turns: int
    wall_ms: int
    tool_ms: int
    model_ms: int
    tools_called: int
    errors: int
    tokens: TurnTokens


@dataclass(frozen=True)
class TimingFlag:
    code: str
    severity: str
    message: str
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RunTiming:
    run_id: str
    flow_code: str
    run_status: str
    last_turn_index: int
    wall_ms: int
    active_ms: int
    idle_ms: int
    setup_ms: int
    tokens: TurnTokens
    turns: list[TurnTiming] = field(default_factory=list)
    per_agent: list[AgentTiming] = field(default_factory=list)
    top_tools: list[ToolCallRollup] = field(default_factory=list)
    top_commands: list[CommandRollup] = field(default_factory=list)
    flags: list[TimingFlag] = field(default_factory=list)
