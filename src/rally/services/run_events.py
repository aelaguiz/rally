from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Mapping, Protocol


@dataclass(frozen=True)
class EventDraft:
    source: str
    kind: str
    code: str
    message: str
    level: str = "info"
    data: Mapping[str, object] = field(default_factory=dict)
    agent_key: str | None = None
    agent_slug: str | None = None
    turn_index: int | None = None


@dataclass(frozen=True)
class RunEvent:
    ts: str
    run_id: str
    flow_code: str
    source: str
    kind: str
    code: str
    message: str
    level: str
    data: dict[str, object]
    turn_index: int | None = None
    agent_key: str | None = None
    agent_slug: str | None = None


class EventConsumer(Protocol):
    def emit(self, event: RunEvent) -> None:
        """Handle one rendered event."""

    def close(self) -> None:
        """Release any consumer resources."""


class NullEventConsumer:
    def emit(self, event: RunEvent) -> None:
        del event

    def close(self) -> None:
        return None


class RunEventRecorder:
    def __init__(
        self,
        *,
        run_dir: Path,
        run_id: str,
        flow_code: str,
        consumer: EventConsumer | None = None,
    ) -> None:
        self._run_dir = run_dir
        self._run_id = run_id
        self._flow_code = flow_code
        self._consumer = consumer or NullEventConsumer()
        self._events_file = run_dir / "logs" / "events.jsonl"
        self._agent_logs_dir = run_dir / "logs" / "agents"
        self._rendered_log_file = run_dir / "logs" / "rendered.log"
        self._events_file.parent.mkdir(parents=True, exist_ok=True)
        self._agent_logs_dir.mkdir(parents=True, exist_ok=True)
        self._rendered_log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        *,
        source: str,
        kind: str,
        code: str,
        message: str,
        level: str = "info",
        data: Mapping[str, object] | None = None,
        turn_index: int | None = None,
        agent_key: str | None = None,
        agent_slug: str | None = None,
        now: datetime | None = None,
    ) -> RunEvent:
        event = RunEvent(
            ts=_render_time(now),
            run_id=self._run_id,
            flow_code=self._flow_code,
            source=source,
            kind=kind,
            code=code,
            message=message,
            level=level,
            data=dict(data or {}),
            turn_index=turn_index,
            agent_key=agent_key,
            agent_slug=agent_slug,
        )
        self._append_json(self._events_file, asdict(event))
        if agent_slug:
            self._append_json(self._agent_logs_dir / f"{agent_slug}.jsonl", asdict(event))
        if should_render_event(event):
            with self._rendered_log_file.open("a", encoding="utf-8") as handle:
                handle.write(render_plain_event_line(event))
                handle.write("\n")
        self._consumer.emit(event)
        return event

    def emit_draft(self, draft: EventDraft) -> RunEvent:
        return self.emit(
            source=draft.source,
            kind=draft.kind,
            code=draft.code,
            message=draft.message,
            level=draft.level,
            data=draft.data,
            turn_index=draft.turn_index,
            agent_key=draft.agent_key,
            agent_slug=draft.agent_slug,
        )

    def close(self) -> None:
        self._consumer.close()

    @staticmethod
    def _append_json(path: Path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True))
            handle.write("\n")
def render_plain_event_line(event: RunEvent) -> str:
    timestamp = _short_time(event.ts)
    agent_label = event.agent_key or event.agent_slug or "rally"
    message = " ".join(event.message.splitlines()) if event.message.strip() else "-"
    return f"{timestamp}  {agent_label:<20}  {event.code:<9}  {message}"


def should_render_event(event: RunEvent) -> bool:
    if event.kind == "debug":
        return event.level in {"warning", "error"}
    return True


def _render_time(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _short_time(raw_value: str) -> str:
    if raw_value.endswith("Z"):
        raw_value = f"{raw_value[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw_value).astimezone(UTC).strftime("%H:%M:%S")
    except ValueError:
        return raw_value
