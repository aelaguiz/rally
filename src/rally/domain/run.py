from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


# ``state.yaml`` schema version. Bump only for breaking shape changes. The
# v2 schema adds ``pid`` / ``process_create_time`` / ``pgid`` / ``schema_version``
# for detached-run bookkeeping. v1 state files (no version field, no pid
# fields) are still loadable.
RUN_STATE_SCHEMA_VERSION: int = 2


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SLEEPING = "sleeping"
    BLOCKED = "blocked"
    DONE = "done"
    STOPPED = "stopped"


class ReconciledStatus(StrEnum):
    """Status as computed by the reconciler — a superset of RunStatus.

    Values from RunStatus pass through unchanged. The three additional
    values are never stored in ``state.yaml``; they are derived from the
    combination of stored state, heartbeat freshness, process liveness, and
    the presence of the ``done.json`` marker.
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SLEEPING = "sleeping"
    BLOCKED = "blocked"
    DONE = "done"
    STOPPED = "stopped"
    CRASHED = "crashed"
    ORPHANED = "orphaned"
    STALE = "stale"


RUN_STATUS_TERMINAL: frozenset[RunStatus] = frozenset(
    {RunStatus.DONE, RunStatus.BLOCKED, RunStatus.STOPPED}
)


@dataclass(frozen=True)
class RunRequest:
    flow_name: str
    start_new: bool = False
    step: bool = False
    issue_seed_path: Path | None = None
    model_override: str | None = None
    reasoning_effort_override: str | None = None
    detach: bool = False


@dataclass(frozen=True)
class ResumeRequest:
    run_id: str
    edit_issue: bool = False
    restart: bool = False
    step: bool = False
    model_override: str | None = None
    reasoning_effort_override: str | None = None
    detach: bool = False


@dataclass(frozen=True)
class RunRecord:
    id: str
    flow_name: str
    flow_code: str
    adapter_name: str
    start_agent_key: str
    created_at: str
    issue_file: str = "home/issue.md"
    model_override: str | None = None
    reasoning_effort_override: str | None = None


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
    # Detached-run bookkeeping. All None for foreground runs and for state
    # files written by pre-detach Rally versions (v1 schema).
    pid: int | None = None
    process_create_time: float | None = None
    pgid: int | None = None
    schema_version: int = RUN_STATE_SCHEMA_VERSION
