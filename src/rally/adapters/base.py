from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, Protocol

import yaml

from rally.domain.flow import normalize_flow_code
from rally.errors import RallyStateError
from rally.memory.logging import MEMORY_EVENT_MODE_ADAPTER, MEMORY_EVENT_MODE_ENV
from rally.services.run_events import RunEventRecorder

if TYPE_CHECKING:
    import subprocess

    from rally.domain.flow import FlowAgent, FlowDefinition
    from rally.domain.run import RunRecord
    from rally.services.workspace import WorkspaceContext


@dataclass(frozen=True)
class AdapterSessionRecord:
    session_id: str
    agent_slug: str
    cwd: str
    updated_at: str


@dataclass(frozen=True)
class TurnArtifactPaths:
    turn_dir: Path
    exec_jsonl_file: Path
    stderr_file: Path
    last_message_file: Path


@dataclass(frozen=True)
class InterviewArtifactPaths:
    interview_dir: Path
    prompt_file: Path
    session_file: Path
    launch_file: Path
    transcript_file: Path
    raw_events_file: Path
    stderr_file: Path


@dataclass(frozen=True)
class AdapterInvocation:
    returncode: int
    stdout_text: str
    stderr_text: str
    session_id: str | None


@dataclass(frozen=True)
class InterviewSessionRecord:
    interview_id: str
    adapter_name: str
    agent_slug: str
    mode: str
    diagnostic_session_id: str | None
    source_session_id: str | None
    cwd: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AdapterReadinessFailure:
    failed_check: str
    reason: str
    mcp_name: str | None = None


class RallyAdapter(Protocol):
    name: str
    display_name: str

    def validate_args(self, *, args: Mapping[str, object]) -> None:
        """Validate `runtime.adapter_args` for this adapter."""

    def prepare_home(
        self,
        *,
        repo_root: Path,
        workspace: "WorkspaceContext",
        run_home: Path,
        flow: "FlowDefinition",
        run_record: "RunRecord",
        event_recorder: RunEventRecorder | None,
    ) -> None:
        """Refresh adapter-owned run-home files."""

    def prepare_turn_artifacts(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        turn_index: int,
    ) -> TurnArtifactPaths:
        """Return the stable artifact paths for one turn."""

    def load_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
    ) -> AdapterSessionRecord | None:
        """Load the saved adapter session for one agent, if present."""

    def record_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        session_id: str,
        cwd: Path,
        now: datetime | None = None,
    ) -> AdapterSessionRecord:
        """Persist the adapter session for one agent."""

    def check_turn_readiness(
        self,
        *,
        repo_root: Path,
        workspace: "WorkspaceContext",
        run_dir: Path,
        run_home: Path,
        flow: "FlowDefinition",
        run_record: "RunRecord",
        agent: "FlowAgent",
        turn_index: int,
        recorder: RunEventRecorder,
        subprocess_run: "SubprocessRunner",
    ) -> AdapterReadinessFailure | None:
        """Return one blocker when adapter prerequisites are not ready."""

    def invoke(
        self,
        *,
        repo_root: Path,
        workspace: "WorkspaceContext",
        run_dir: Path,
        run_home: Path,
        flow: "FlowDefinition",
        run_record: "RunRecord",
        agent: "FlowAgent",
        prompt: str,
        previous_session: AdapterSessionRecord | None,
        artifacts: TurnArtifactPaths,
        recorder: RunEventRecorder,
        turn_index: int,
        subprocess_run: "SubprocessRunner",
    ) -> AdapterInvocation:
        """Run one adapter turn and return the process result."""


SubprocessRunner = Callable[..., "subprocess.CompletedProcess[str]"]


def build_rally_launch_env(
    *,
    workspace_dir: Path,
    cli_bin: Path,
    run_id: str,
    flow_code: str,
    agent_slug: str,
    turn_index: int,
) -> dict[str, str]:
    if not run_id.strip():
        raise RallyStateError("Run id must not be empty.")
    if not flow_code.strip():
        raise RallyStateError("Flow code must not be empty.")
    try:
        flow_code = normalize_flow_code(flow_code)
    except ValueError as exc:
        raise RallyStateError(str(exc)) from exc
    if not agent_slug.strip():
        raise RallyStateError("Agent slug must not be empty.")
    if turn_index < 1:
        raise RallyStateError("Turn index must be 1 or greater.")

    return {
        "RALLY_CLI_BIN": str(cli_bin.resolve()),
        "RALLY_RUN_ID": run_id,
        "RALLY_FLOW_CODE": flow_code,
        "RALLY_AGENT_SLUG": agent_slug,
        MEMORY_EVENT_MODE_ENV: MEMORY_EVENT_MODE_ADAPTER,
        "RALLY_TURN_NUMBER": str(turn_index),
        "RALLY_WORKSPACE_DIR": str(workspace_dir.resolve()),
    }


def write_adapter_launch_record(
    *,
    run_dir: Path,
    turn_index: int,
    agent_slug: str,
    command: list[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout_sec: int,
    extra_env_keys: tuple[str, ...] = (),
) -> Path:
    launch_dir = run_dir / "logs" / "adapter_launch"
    launch_dir.mkdir(parents=True, exist_ok=True)
    record_file = launch_dir / f"turn-{turn_index:03d}-{agent_slug}.json"
    keep_keys = {key for key in env if key.startswith("RALLY_")}
    keep_keys.update(extra_env_keys)
    payload = {
        "ts": datetime.now(UTC).astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "command": command,
        "cwd": str(cwd.resolve()),
        "timeout_sec": timeout_sec,
        "env": {
            key: env[key]
            for key in sorted(keep_keys)
            if key in env
        },
    }
    record_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record_file


def load_adapter_session(
    *,
    run_home: Path,
    agent_slug: str,
) -> AdapterSessionRecord | None:
    session_file = _session_file(run_home=run_home, agent_slug=agent_slug)
    if not session_file.is_file():
        return None
    payload = yaml.safe_load(session_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyStateError(f"Session file `{session_file}` must load to a YAML map.")
    return AdapterSessionRecord(
        session_id=str(payload["session_id"]),
        agent_slug=str(payload["agent_slug"]),
        cwd=str(payload["cwd"]),
        updated_at=str(payload["updated_at"]),
    )


def record_adapter_session(
    *,
    run_home: Path,
    agent_slug: str,
    session_id: str,
    cwd: Path,
    now: datetime | None = None,
) -> AdapterSessionRecord:
    record = AdapterSessionRecord(
        session_id=session_id,
        agent_slug=agent_slug,
        cwd=str(cwd.resolve()),
        updated_at=(now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
    )
    session_file = _session_file(run_home=run_home, agent_slug=agent_slug)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(yaml.safe_dump(asdict(record), sort_keys=False), encoding="utf-8")
    return record


def prepare_adapter_turn_artifacts(
    *,
    run_home: Path,
    agent_slug: str,
    turn_index: int,
) -> TurnArtifactPaths:
    turn_dir = run_home / "sessions" / agent_slug / f"turn-{turn_index:03d}"
    turn_dir.mkdir(parents=True, exist_ok=True)
    return TurnArtifactPaths(
        turn_dir=turn_dir,
        exec_jsonl_file=turn_dir / "exec.jsonl",
        stderr_file=turn_dir / "stderr.log",
        last_message_file=turn_dir / "last_message.json",
    )


def prepare_interview_artifacts(
    *,
    run_home: Path,
    agent_slug: str,
    interview_id: str,
) -> InterviewArtifactPaths:
    interview_dir = run_home / "interviews" / agent_slug / interview_id
    interview_dir.mkdir(parents=True, exist_ok=True)
    return InterviewArtifactPaths(
        interview_dir=interview_dir,
        prompt_file=interview_dir / "prompt.md",
        session_file=interview_dir / "session.yaml",
        launch_file=interview_dir / "launch.json",
        transcript_file=interview_dir / "transcript.jsonl",
        raw_events_file=interview_dir / "raw_events.jsonl",
        stderr_file=interview_dir / "stderr.log",
    )


def load_interview_session(*, interview_dir: Path) -> InterviewSessionRecord | None:
    session_file = interview_dir / "session.yaml"
    if not session_file.is_file():
        return None
    payload = yaml.safe_load(session_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyStateError(f"Interview session file `{session_file}` must load to a YAML map.")
    return InterviewSessionRecord(
        interview_id=str(payload["interview_id"]),
        adapter_name=str(payload["adapter_name"]),
        agent_slug=str(payload["agent_slug"]),
        mode=str(payload["mode"]),
        diagnostic_session_id=_optional_yaml_string(payload, "diagnostic_session_id"),
        source_session_id=_optional_yaml_string(payload, "source_session_id"),
        cwd=str(payload["cwd"]),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
    )


def record_interview_session(
    *,
    interview_dir: Path,
    interview_id: str,
    adapter_name: str,
    agent_slug: str,
    mode: str,
    cwd: Path,
    diagnostic_session_id: str | None = None,
    source_session_id: str | None = None,
    now: datetime | None = None,
) -> InterviewSessionRecord:
    existing = load_interview_session(interview_dir=interview_dir)
    created_at = existing.created_at if existing is not None else _render_timestamp(now)
    record = InterviewSessionRecord(
        interview_id=interview_id,
        adapter_name=adapter_name,
        agent_slug=agent_slug,
        mode=mode,
        diagnostic_session_id=diagnostic_session_id,
        source_session_id=source_session_id,
        cwd=str(cwd.resolve()),
        created_at=created_at,
        updated_at=_render_timestamp(now),
    )
    session_file = interview_dir / "session.yaml"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(yaml.safe_dump(asdict(record), sort_keys=False), encoding="utf-8")
    return record


def _session_file(*, run_home: Path, agent_slug: str) -> Path:
    return run_home / "sessions" / agent_slug / "session.yaml"


def _optional_yaml_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RallyStateError(f"Interview session field `{key}` must be a string when present.")
    return value


def _render_timestamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
