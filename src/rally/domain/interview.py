from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class InterviewRequest:
    run_id: str
    agent_slug: str | None = None
    fork: bool = False


@dataclass(frozen=True)
class InterviewCommandResult:
    run_id: str
    agent_slug: str
    interview_id: str
    mode: str
    message: str


@dataclass(frozen=True)
class InterviewLaunch:
    command: tuple[str, ...]
    cwd: str
    env: dict[str, str]


@dataclass(frozen=True)
class InterviewReply:
    session_id: str | None
    text: str
    command: tuple[str, ...]
    cwd: str
    env: dict[str, str]
    raw_event_lines: tuple[str, ...]
    stderr_text: str


TextDeltaCallback = Callable[[str], None]
