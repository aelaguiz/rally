from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SLEEPING = "sleeping"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass(frozen=True)
class RunRequest:
    flow_name: str
    start_new: bool = False
    step: bool = False
    issue_seed_path: Path | None = None


@dataclass(frozen=True)
class ResumeRequest:
    run_id: str
    edit_issue: bool = False
    restart: bool = False
    step: bool = False


@dataclass(frozen=True)
class RunRecord:
    id: str
    flow_name: str
    flow_code: str
    adapter_name: str
    start_agent_key: str
    created_at: str
    issue_file: str = "home/issue.md"


@dataclass(frozen=True)
class RunState:
    status: RunStatus
    current_agent_key: str | None
    current_agent_slug: str | None
    turn_index: int
    updated_at: str
    last_turn_kind: str | None = None
    sleep_until: str | None = None
    sleep_reason: str | None = None
    blocker_reason: str | None = None
    done_summary: str | None = None
