"""Background heartbeat for detached Rally runs.

A detached run writes ``heartbeat.json`` on a cadence while it is making
progress. The reconciler reads this file alongside ``state.yaml`` to
distinguish:

  * a live run making progress (fresh heartbeat, matching process identity)
  * a live process that has wedged (fresh identity, stale heartbeat → STALE)
  * a dead process (identity does not probe as ALIVE → CRASHED)

Heartbeats run on a background thread so a long LLM call inside the main
turn loop does not falsely mark the run as stalled. The thread uses a
``threading.Event`` for prompt cooperative shutdown.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rally.services.atomic_io import write_atomic
from rally.services.process_identity import ProcessIdentity, capture_self

__all__ = [
    "DEFAULT_INTERVAL_SECONDS",
    "DEFAULT_STALE_THRESHOLD_SECONDS",
    "HEARTBEAT_SCHEMA_VERSION",
    "HeartbeatReader",
    "HeartbeatSnapshot",
    "HeartbeatThread",
    "heartbeat_path",
    "is_heartbeat_stale",
    "write_heartbeat",
]


DEFAULT_INTERVAL_SECONDS: float = 15.0
DEFAULT_STALE_THRESHOLD_SECONDS: float = 45.0  # 3x interval
HEARTBEAT_SCHEMA_VERSION: int = 1


def heartbeat_path(run_dir: Path) -> Path:
    return run_dir / "heartbeat.json"


@dataclass(frozen=True)
class HeartbeatSnapshot:
    pid: int
    create_time: float
    ts: str
    turn_index: int | None
    schema_version: int

    @property
    def identity(self) -> ProcessIdentity:
        return ProcessIdentity(pid=self.pid, create_time=self.create_time)


def write_heartbeat(
    run_dir: Path,
    *,
    identity: ProcessIdentity,
    turn_index: int | None,
    now: datetime | None = None,
) -> None:
    payload = {
        "schema_version": HEARTBEAT_SCHEMA_VERSION,
        "pid": identity.pid,
        "create_time": identity.create_time,
        "ts": (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "turn_index": turn_index,
    }
    write_atomic(heartbeat_path(run_dir), json.dumps(payload, sort_keys=True) + "\n")


class HeartbeatReader:
    """Read heartbeat.json, tolerating transient write races."""

    @staticmethod
    def read(run_dir: Path) -> HeartbeatSnapshot | None:
        path = heartbeat_path(run_dir)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return HeartbeatSnapshot(
                pid=int(payload["pid"]),
                create_time=float(payload["create_time"]),
                ts=str(payload["ts"]),
                turn_index=(
                    int(payload["turn_index"])
                    if payload.get("turn_index") is not None
                    else None
                ),
                schema_version=int(payload.get("schema_version", HEARTBEAT_SCHEMA_VERSION)),
            )
        except (KeyError, TypeError, ValueError):
            return None


class HeartbeatThread:
    """Background thread that rewrites heartbeat.json every ``interval`` seconds.

    Usage:

        thread = HeartbeatThread(run_dir=run_dir, get_turn_index=lambda: state.turn_index)
        thread.start()
        try:
            run_loop()
        finally:
            thread.stop()

    The thread writes once immediately on start so readers see a fresh
    heartbeat before the first sleep interval elapses.
    """

    def __init__(
        self,
        *,
        run_dir: Path,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        identity: ProcessIdentity | None = None,
        get_turn_index: Callable[[], int] | None = None,
    ) -> None:
        self._run_dir = run_dir
        self._interval = max(0.1, float(interval_seconds))
        self._identity = identity or capture_self()
        self._get_turn_index = get_turn_index
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def identity(self) -> ProcessIdentity:
        return self._identity

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("HeartbeatThread has already been started.")
        # Write once synchronously so readers never see a missing heartbeat.
        self._write_once()
        thread = threading.Thread(
            target=self._run,
            name=f"rally-heartbeat-{self._identity.pid}",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._write_once()

    def _write_once(self) -> None:
        turn_index: int | None
        if self._get_turn_index is None:
            turn_index = None
        else:
            try:
                turn_index = self._get_turn_index()
            except Exception:
                turn_index = None
        try:
            write_heartbeat(
                self._run_dir,
                identity=self._identity,
                turn_index=turn_index,
            )
        except OSError:
            # Filesystem hiccups must not kill the thread; keep trying.
            pass


def is_heartbeat_stale(
    snapshot: HeartbeatSnapshot,
    *,
    threshold_seconds: float = DEFAULT_STALE_THRESHOLD_SECONDS,
    now: datetime | None = None,
) -> bool:
    """Return True if ``snapshot.ts`` is older than ``threshold_seconds``."""
    raw_ts = snapshot.ts
    if raw_ts.endswith("Z"):
        raw_ts = raw_ts[:-1] + "+00:00"
    try:
        hb_dt = datetime.fromisoformat(raw_ts).astimezone(UTC)
    except ValueError:
        # Unparseable timestamp — treat as stale so the reconciler surfaces it.
        return True
    reference = (now or datetime.now(UTC)).astimezone(UTC)
    return (reference - hb_dt).total_seconds() > threshold_seconds
