from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rally.errors import RallyStateError


@dataclass(frozen=True)
class CodexSessionRecord:
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


def load_session(*, run_home: Path, agent_slug: str) -> CodexSessionRecord | None:
    session_file = _session_file(run_home=run_home, agent_slug=agent_slug)
    if not session_file.is_file():
        return None
    payload = yaml.safe_load(session_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RallyStateError(f"Session file `{session_file}` must load to a YAML map.")
    return CodexSessionRecord(
        session_id=str(payload["session_id"]),
        agent_slug=str(payload["agent_slug"]),
        cwd=str(payload["cwd"]),
        updated_at=str(payload["updated_at"]),
    )


def record_session(
    *,
    run_home: Path,
    agent_slug: str,
    session_id: str,
    cwd: Path,
    now: datetime | None = None,
) -> CodexSessionRecord:
    record = CodexSessionRecord(
        session_id=session_id,
        agent_slug=agent_slug,
        cwd=str(cwd.resolve()),
        updated_at=(now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
    )
    session_file = _session_file(run_home=run_home, agent_slug=agent_slug)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(yaml.safe_dump(asdict(record), sort_keys=False), encoding="utf-8")
    return record


def prepare_turn_artifacts(*, run_home: Path, agent_slug: str, turn_index: int) -> TurnArtifactPaths:
    turn_dir = run_home / "sessions" / agent_slug / f"turn-{turn_index:03d}"
    turn_dir.mkdir(parents=True, exist_ok=True)
    return TurnArtifactPaths(
        turn_dir=turn_dir,
        exec_jsonl_file=turn_dir / "exec.jsonl",
        stderr_file=turn_dir / "stderr.log",
        last_message_file=turn_dir / "last_message.json",
    )


def _session_file(*, run_home: Path, agent_slug: str) -> Path:
    return run_home / "sessions" / agent_slug / "session.yaml"
