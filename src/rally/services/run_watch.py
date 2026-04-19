"""Tail a run's ``logs/events.jsonl`` for operators watching a live flow.

Deliberately small. The heavy lifting is already done: each event is a
single JSON object on one line, the file is append-only, and
``render_plain_event_line`` already exists. ``watch_run`` just reads,
renders, and — when ``follow`` is true — sleeps for a short poll interval
between reads until EOF stays EOF for longer than some caller's patience.

We poll rather than use inotify/FSEvents because the rest of Rally is
deliberately filesystem-observable-from-anywhere: no backend-specific
machinery is allowed to creep in.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable, Iterator, TextIO

from rally.domain.run import RUN_STATUS_TERMINAL, RunStatus
from rally.errors import RallyUsageError
from rally.services.run_events import RunEvent, render_plain_event_line
from rally.services.run_store import find_run_dir, load_run_state


_TOOL_END_CODES = {
    "TOOL OK",
    "CMD OK",
    "CMD ERR",
    "CMD NO",
    "MCP OK",
    "MCP ERR",
    "COLLAB OK",
    "COLLAB ERR",
}


class _TurnProgress:
    """Tracks the currently-executing turn for an operator-friendly footer.

    Reset on every `TURN` event. Grows on every tool-end event. Rendered
    compactly after every tool-end so the operator always sees current
    progress without needing to re-read the stream.
    """

    __slots__ = ("turn_index", "agent_slug", "tools", "errors")

    def __init__(self) -> None:
        self.turn_index: int | None = None
        self.agent_slug: str | None = None
        self.tools = 0
        self.errors = 0

    def begin(self, event: RunEvent) -> None:
        self.turn_index = event.turn_index
        self.agent_slug = event.agent_slug or event.agent_key
        self.tools = 0
        self.errors = 0

    def note_tool(self, event: RunEvent) -> None:
        self.tools += 1
        if event.level == "error" or event.code.endswith(" ERR") or event.code.endswith(" NO"):
            self.errors += 1

    def render(self) -> str | None:
        if self.turn_index is None or self.tools == 0:
            return None
        pieces = [f"turn {self.turn_index}"]
        if self.agent_slug:
            pieces.insert(0, self.agent_slug)
        pieces.append(f"{self.tools} tools")
        if self.errors:
            pieces.append(f"{self.errors} err")
        return "· " + " · ".join(pieces)

__all__ = [
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "watch_run",
]


DEFAULT_POLL_INTERVAL_SECONDS: float = 0.5


def watch_run(
    *,
    repo_root: Path,
    run_id: str,
    since: int = 0,
    follow: bool = False,
    stream: TextIO,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> int:
    """Print rendered events for ``run_id`` to ``stream``.

    ``since`` skips the first N events; useful for operators who want
    "just the new stuff." ``follow`` polls the file for new lines until
    the run reaches a terminal status or the operator interrupts.

    Returns the number of events printed.
    """
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_id)
    events_path = run_dir / "logs" / "events.jsonl"

    printed = 0
    position = 0
    skip_remaining = max(0, since)
    progress = _TurnProgress()

    for event, offset in _read_events_from(events_path, position):
        position = offset
        if skip_remaining > 0:
            skip_remaining -= 1
            continue
        printed += _render_watch_event(event, stream=stream, progress=progress)

    if not follow:
        return printed

    try:
        while not _is_run_terminal(run_dir):
            time.sleep(poll_interval_seconds)
            for event, offset in _read_events_from(events_path, position):
                position = offset
                if skip_remaining > 0:
                    skip_remaining -= 1
                    continue
                printed += _render_watch_event(event, stream=stream, progress=progress)
    except KeyboardInterrupt:
        # Operators Ctrl-C out of `watch`; that is not an error.
        return printed

    return printed


def _render_watch_event(
    event: RunEvent, *, stream: TextIO, progress: _TurnProgress
) -> int:
    if event.code == "TURN":
        progress.begin(event)
    if event.code == "SUMMARY" and event.kind == "summary":
        receipt = event.data.get("receipt")
        if isinstance(receipt, str) and receipt.strip():
            stream.write("\n")
            stream.write(receipt.rstrip())
            stream.write("\n\n")
            stream.flush()
            return 1
    stream.write(render_plain_event_line(event))
    stream.write("\n")
    if event.code in _TOOL_END_CODES:
        progress.note_tool(event)
        rendered = progress.render()
        if rendered:
            stream.write(f"  {rendered}\n")
    stream.flush()
    return 1


def _read_events_from(
    events_path: Path, start_offset: int
) -> Iterator[tuple[RunEvent, int]]:
    if not events_path.is_file():
        return
    with events_path.open("r", encoding="utf-8") as handle:
        handle.seek(start_offset)
        # Use explicit readline so we can safely call tell() between reads;
        # the `for line in handle` iterator buffers ahead and disables tell.
        while True:
            line_start = handle.tell()
            line = handle.readline()
            if not line:
                return
            if not line.endswith("\n"):
                # Partial write in progress — rewind so the next poll picks
                # up the incomplete line whole.
                handle.seek(line_start)
                return
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                # Skip the bad line so a corrupt row does not stall the
                # tail. We could log this, but watch is read-only by design.
                continue
            event = _event_from_payload(payload)
            if event is not None:
                yield event, handle.tell()


def _event_from_payload(payload: dict[str, object]) -> RunEvent | None:
    try:
        return RunEvent(
            ts=str(payload["ts"]),
            run_id=str(payload["run_id"]),
            flow_code=str(payload["flow_code"]),
            source=str(payload["source"]),
            kind=str(payload["kind"]),
            code=str(payload["code"]),
            message=str(payload["message"]),
            level=str(payload.get("level", "info")),
            data=dict(payload.get("data") or {}),
            turn_index=_optional_int(payload.get("turn_index")),
            agent_key=_optional_str(payload.get("agent_key")),
            agent_slug=_optional_str(payload.get("agent_slug")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return None


def _is_run_terminal(run_dir: Path) -> bool:
    try:
        state = load_run_state(run_dir=run_dir)
    except Exception:
        return False
    return state.status in RUN_STATUS_TERMINAL
