from __future__ import annotations

from dataclasses import dataclass
import json
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
    for line in _render_time_footprint(snapshot.run_dir):
        lines.append(line)
    lines.append(f"Next: {_render_next_action(snapshot=snapshot, repo_root=repo_root)}")
    return "\n".join(lines)


def _render_time_footprint(run_dir: Path) -> list[str]:
    """Return the three-line time footprint from `timing.json`, or empty.

    Omits silently when `timing.json` has not been written yet (the run has
    not completed its first terminal turn).
    """
    timing_path = run_dir / "timing.json"
    if not timing_path.exists():
        return []
    try:
        payload = json.loads(timing_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    wall_ms = int(payload.get("wall_ms") or 0)
    active_ms = int(payload.get("active_ms") or 0)
    idle_ms = int(payload.get("idle_ms") or 0)
    top_tools = payload.get("top_tools") or []
    tokens = payload.get("tokens") or {}
    errors = sum(int(a.get("errors") or 0) for a in payload.get("per_agent") or [])

    tool_parts: list[str] = []
    for tool in top_tools[:2]:
        tool_parts.append(f"{_fmt_duration(int(tool.get('total_ms') or 0))} {tool.get('tool_name') or '?'}")
    tool_line = " · ".join(tool_parts) if tool_parts else "no tool calls"

    token_parts: list[str] = []
    if int(tokens.get("output_tokens") or 0):
        token_parts.append(f"{_fmt_count(int(tokens['output_tokens']))} out")
    if int(tokens.get("cache_read_input_tokens") or 0):
        token_parts.append(f"{_fmt_count(int(tokens['cache_read_input_tokens']))} cached")
    token_line = " · ".join(token_parts) if token_parts else "no tokens recorded"

    return [
        f"Time:   {_fmt_duration(wall_ms)} wall ({_fmt_duration(active_ms)} active · {_fmt_duration(idle_ms)} idle)",
        f"Tools:  {tool_line}" + (f" · {errors} errors" if errors else ""),
        f"Tokens: {token_line}",
    ]


def _fmt_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s" if seconds < 10 else f"{int(round(seconds))}s"
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def _fmt_count(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        k = n / 1000
        return f"{k:.1f}k" if k < 10 else f"{int(round(k))}k"
    m = n / 1_000_000
    return f"{m:.2f}M" if m < 10 else f"{m:.1f}M"


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
