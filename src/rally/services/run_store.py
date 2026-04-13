from __future__ import annotations

import os
import re
import shutil
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

import yaml

from rally.domain.flow import FlowDefinition
from rally.domain.run import RunRecord, RunState, RunStatus
from rally.errors import RallyStateError

_RUN_ID_RE = re.compile(r"^(?P<flow_code>[A-Z0-9]+)-(?P<sequence>\d+)$")


def active_runs_dir(repo_root: Path) -> Path:
    return repo_root / "runs" / "active"


def archive_runs_dir(repo_root: Path) -> Path:
    return repo_root / "runs" / "archive"


def find_run_dir(*, repo_root: Path, run_id: str) -> Path:
    candidates = (
        active_runs_dir(repo_root) / run_id,
        archive_runs_dir(repo_root) / run_id,
        repo_root / "runs" / run_id,
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise RallyStateError(f"Run directory does not exist for `{run_id}`.")


def create_run(
    *,
    repo_root: Path,
    flow: FlowDefinition,
    now: datetime | None = None,
) -> RunRecord:
    timestamp = _render_time(now)
    active_run = find_active_run_for_flow(repo_root=repo_root, flow_code=flow.code)
    if active_run is not None:
        raise RallyStateError(
            f"Flow `{flow.name}` already has an active run: `{active_run.id}`."
        )

    run_id = allocate_run_id(repo_root=repo_root, flow_code=flow.code)
    run_dir = active_runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    record = RunRecord(
        id=run_id,
        flow_name=flow.name,
        flow_code=flow.code,
        adapter_name=flow.adapter.name,
        start_agent_key=flow.start_agent_key,
        created_at=timestamp,
    )
    state = RunState(
        status=RunStatus.PENDING,
        current_agent_key=flow.start_agent_key,
        current_agent_slug=flow.agent(flow.start_agent_key).slug,
        turn_index=0,
        updated_at=timestamp,
    )
    write_run_record(run_dir=run_dir, record=record)
    write_run_state(run_dir=run_dir, state=state)
    return record


def find_active_run_for_flow(*, repo_root: Path, flow_code: str) -> RunRecord | None:
    runs_dir = active_runs_dir(repo_root)
    if not runs_dir.is_dir():
        return None
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        record = load_run_record(run_dir=run_dir)
        if record.flow_code == flow_code:
            return record
    return None


def archive_run(*, repo_root: Path, run_id: str) -> Path:
    active_run_dir = active_runs_dir(repo_root) / run_id
    if not active_run_dir.is_dir():
        raise RallyStateError(f"Active run directory does not exist for `{run_id}`.")

    archived_run_dir = archive_runs_dir(repo_root) / run_id
    if archived_run_dir.exists():
        raise RallyStateError(f"Archive run directory already exists for `{run_id}`.")

    archived_run_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(active_run_dir), str(archived_run_dir))
    return archived_run_dir


def allocate_run_id(*, repo_root: Path, flow_code: str) -> str:
    highest = 0
    for run_dir in _iter_known_run_dirs(repo_root):
        match = _RUN_ID_RE.match(run_dir.name)
        if match is None or match.group("flow_code") != flow_code:
            continue
        highest = max(highest, int(match.group("sequence")))
    return f"{flow_code}-{highest + 1}"


def load_run_record(*, run_dir: Path) -> RunRecord:
    payload = _load_yaml_map(run_dir / "run.yaml")
    return RunRecord(
        id=_require_string(payload, "id", context=str(run_dir / "run.yaml")),
        flow_name=_require_string(payload, "flow_name", context=str(run_dir / "run.yaml")),
        flow_code=_require_string(payload, "flow_code", context=str(run_dir / "run.yaml")),
        adapter_name=_require_string(payload, "adapter_name", context=str(run_dir / "run.yaml")),
        start_agent_key=_require_string(payload, "start_agent_key", context=str(run_dir / "run.yaml")),
        created_at=_require_string(payload, "created_at", context=str(run_dir / "run.yaml")),
        issue_file=_require_string(payload, "issue_file", context=str(run_dir / "run.yaml")),
    )


def write_run_record(*, run_dir: Path, record: RunRecord) -> Path:
    path = run_dir / "run.yaml"
    _write_yaml_map(path, asdict(record))
    return path


def load_run_state(*, run_dir: Path) -> RunState:
    payload = _load_yaml_map(run_dir / "state.yaml")
    status_raw = _require_string(payload, "status", context=str(run_dir / "state.yaml"))
    try:
        status = RunStatus(status_raw)
    except ValueError as exc:
        raise RallyStateError(
            f"Run state file `{run_dir / 'state.yaml'}` has unsupported status `{status_raw}`."
        ) from exc
    return RunState(
        status=status,
        current_agent_key=_optional_string(payload, "current_agent_key"),
        current_agent_slug=_optional_string(payload, "current_agent_slug"),
        turn_index=_require_int(payload, "turn_index", context=str(run_dir / "state.yaml")),
        updated_at=_require_string(payload, "updated_at", context=str(run_dir / "state.yaml")),
        last_turn_kind=_optional_string(payload, "last_turn_kind"),
        sleep_until=_optional_string(payload, "sleep_until"),
        sleep_reason=_optional_string(payload, "sleep_reason"),
        blocker_reason=_optional_string(payload, "blocker_reason"),
        done_summary=_optional_string(payload, "done_summary"),
    )


def write_run_state(*, run_dir: Path, state: RunState) -> Path:
    path = run_dir / "state.yaml"
    payload = asdict(state)
    payload["status"] = state.status.value
    _write_yaml_map(path, payload)
    return path


@contextmanager
def flow_lock(*, repo_root: Path, flow_code: str) -> Iterator[Path]:
    locks_dir = repo_root / "runs" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_path = locks_dir / f"{flow_code}.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RallyStateError(
            f"Flow `{flow_code}` is already locked by another Rally command."
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield lock_path
    finally:
        lock_path.unlink(missing_ok=True)


def _iter_known_run_dirs(repo_root: Path) -> Iterator[Path]:
    for parent in (active_runs_dir(repo_root), archive_runs_dir(repo_root), repo_root / "runs"):
        if not parent.is_dir():
            continue
        for candidate in sorted(parent.iterdir()):
            if candidate.is_dir():
                yield candidate


def _load_yaml_map(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RallyStateError(f"State file does not exist: `{path}`.")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RallyStateError(f"State file `{path}` is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise RallyStateError(f"State file `{path}` must load to a YAML map.")
    return payload


def _write_yaml_map(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _render_time(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_string(payload: dict[str, object], field: str, *, context: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RallyStateError(f"{context} requires non-empty string field `{field}`.")
    return value.strip()


def _optional_string(payload: dict[str, object], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RallyStateError(f"Optional field `{field}` must be null or a non-empty string.")
    return value.strip()


def _require_int(payload: dict[str, object], field: str, *, context: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or value < 0:
        raise RallyStateError(f"{context} requires non-negative integer field `{field}`.")
    return value
