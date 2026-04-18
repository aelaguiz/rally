from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rally.domain.run import ReconciledStatus, RunRecord, RunState, RunStatus
from rally.errors import RallyStateError, RallyUsageError
from rally.services.reconcile import ReconciledRun, reconcile_from_state
from rally.services.run_store import (
    active_runs_dir,
    archive_runs_dir,
    find_run_dir,
    list_active_run_records,
    load_run_record,
    load_run_state,
)


@dataclass(frozen=True)
class StatusCommandResult:
    message: str


@dataclass(frozen=True)
class _RunSnapshot:
    record: RunRecord
    state: RunState
    run_dir: Path
    archived: bool
    reconciled: ReconciledRun | None


def show_status(*, repo_root: Path, run_id: str | None = None) -> StatusCommandResult:
    if run_id is None:
        return StatusCommandResult(message=_render_active_runs(repo_root=repo_root))
    snapshot = _load_run_snapshot(repo_root=repo_root, run_id=run_id)
    return StatusCommandResult(message=_render_run_details(repo_root=repo_root, snapshot=snapshot))


def _render_active_runs(*, repo_root: Path) -> str:
    snapshots: list[_RunSnapshot] = []
    for record in list_active_run_records(repo_root=repo_root):
        run_dir = active_runs_dir(repo_root) / record.id
        state = load_run_state(run_dir=run_dir)
        reconciled = reconcile_from_state(run_dir=run_dir, state=state)
        snapshots.append(
            _RunSnapshot(
                record=record,
                state=state,
                run_dir=run_dir,
                archived=False,
                reconciled=reconciled,
            )
        )
    if not snapshots:
        return "No active runs.\nNext: start one with `rally run <flow>`."

    lines = ["Active runs:"]
    for snapshot in snapshots:
        lines.append(
            " ".join(
                (
                    f"- `{snapshot.record.id}`",
                    f"flow `{snapshot.record.flow_name}`",
                    f"status `{_render_status(snapshot)}`",
                    f"turn `{snapshot.state.turn_index}`",
                    f"agent `{_render_agent(snapshot.state.current_agent_key)}`",
                    f"updated `{snapshot.state.updated_at}`",
                )
            )
        )
        lines.append(f"  Next: {_render_next_action(snapshot=snapshot, repo_root=repo_root)}")
    return "\n".join(lines)


def _render_run_details(*, repo_root: Path, snapshot: _RunSnapshot) -> str:
    issue_path = snapshot.run_dir / Path(snapshot.record.issue_file)
    lines = [
        f"Run `{snapshot.record.id}`",
        f"Flow: `{snapshot.record.flow_name}` (`{snapshot.record.flow_code}`)",
        f"Storage: `{'archive' if snapshot.archived else 'active'}`",
        f"Status: `{_render_status(snapshot)}`",
        f"Current Agent: `{_render_agent(snapshot.state.current_agent_key)}`",
        f"Turn: `{snapshot.state.turn_index}`",
        f"Updated: `{snapshot.state.updated_at}`",
        f"Issue File: `{_render_repo_relative_path(path=issue_path, repo_root=repo_root)}`",
    ]
    if snapshot.record.model_override is not None:
        lines.append(f"Model Override: `{snapshot.record.model_override}`")
    if snapshot.record.reasoning_effort_override is not None:
        lines.append(f"Thinking Override: `{snapshot.record.reasoning_effort_override}`")
    if snapshot.state.last_turn_kind is not None:
        lines.append(f"Last Result: `{snapshot.state.last_turn_kind}`")
    if snapshot.state.blocker_reason is not None:
        lines.append(f"Blocker: {snapshot.state.blocker_reason}")
    if snapshot.state.done_summary is not None:
        lines.append(f"Summary: {snapshot.state.done_summary}")
    if snapshot.state.sleep_until is not None:
        lines.append(f"Sleep Until: `{snapshot.state.sleep_until}`")
    if snapshot.state.sleep_reason is not None:
        lines.append(f"Sleep Reason: {snapshot.state.sleep_reason}")
    reconciled = snapshot.reconciled
    if reconciled is not None:
        if reconciled.state.pid is not None:
            liveness = reconciled.liveness.value if reconciled.liveness is not None else "unknown"
            lines.append(f"PID: `{reconciled.state.pid}` (`{liveness}`)")
        if reconciled.heartbeat is not None:
            freshness = "stale" if reconciled.heartbeat_stale else "fresh"
            lines.append(f"Last Heartbeat: `{reconciled.heartbeat.ts}` (`{freshness}`)")
        if reconciled.stop_requested:
            lines.append("Stop Requested: `yes`")
    lines.append(f"Next: {_render_next_action(snapshot=snapshot, repo_root=repo_root)}")
    return "\n".join(lines)


def _load_run_snapshot(*, repo_root: Path, run_id: str) -> _RunSnapshot:
    try:
        run_dir = find_run_dir(repo_root=repo_root, run_id=run_id)
    except RallyStateError as exc:
        raise RallyUsageError(
            f"Run `{run_id}` does not exist. Use `rally status` to list active runs."
        ) from exc
    record = load_run_record(run_dir=run_dir)
    state = load_run_state(run_dir=run_dir)
    archived = run_dir.is_relative_to(archive_runs_dir(repo_root))
    reconciled = None if archived else reconcile_from_state(run_dir=run_dir, state=state)
    return _RunSnapshot(
        record=record,
        state=state,
        run_dir=run_dir,
        archived=archived,
        reconciled=reconciled,
    )


def _render_next_action(*, snapshot: _RunSnapshot, repo_root: Path) -> str:
    run_id = snapshot.record.id
    if snapshot.archived:
        issue_path = snapshot.run_dir / Path(snapshot.record.issue_file)
        return (
            "archived runs do not resume; inspect "
            f"`{_render_repo_relative_path(path=issue_path, repo_root=repo_root)}`"
        )
    reconciled_status = (
        snapshot.reconciled.status if snapshot.reconciled is not None else None
    )
    if reconciled_status is ReconciledStatus.STOPPED:
        return f"`rally resume {run_id}` or `rally resume {run_id} --restart`"
    if reconciled_status is ReconciledStatus.CRASHED:
        return (
            f"`rally status {run_id}` then `rally resume {run_id} --restart` "
            "once the cause is understood"
        )
    if reconciled_status is ReconciledStatus.ORPHANED:
        return (
            f"PID recorded for `{run_id}` was reused; "
            f"use `rally resume {run_id} --restart`"
        )
    if reconciled_status is ReconciledStatus.STALE:
        return (
            f"heartbeat for `{run_id}` is stale; check process health or "
            f"`rally resume {run_id} --restart`"
        )
    status = snapshot.state.status
    if status == RunStatus.PENDING:
        return f"`rally resume {run_id}`"
    if status == RunStatus.PAUSED:
        return f"`rally resume {run_id}` or `rally resume {run_id} --step`"
    if status == RunStatus.BLOCKED:
        return f"`rally resume {run_id} --edit` or `rally resume {run_id} --restart`"
    if status == RunStatus.DONE:
        return f"`rally resume {run_id} --restart`"
    if status == RunStatus.STOPPED:
        return f"`rally resume {run_id}` or `rally resume {run_id} --restart`"
    if status == RunStatus.SLEEPING:
        if snapshot.state.sleep_until is not None:
            return f"`rally resume {run_id}` after `{snapshot.state.sleep_until}`"
        return f"`rally resume {run_id}`"
    return "wait for the active Rally command to finish"


def _render_status(snapshot: _RunSnapshot) -> str:
    if snapshot.reconciled is not None:
        return snapshot.reconciled.status.value
    return snapshot.state.status.value


def _render_agent(agent_key: str | None) -> str:
    return agent_key or "none"


def _render_repo_relative_path(*, path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
