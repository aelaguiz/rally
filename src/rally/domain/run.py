from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SLEEPING = "sleeping"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass(frozen=True)
class RunRequest:
    flow_name: str
    brief_file: Path


@dataclass(frozen=True)
class ResumeRequest:
    run_id: str
