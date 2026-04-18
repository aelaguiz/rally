"""Reconciler: compute a run's current status from authoritative inputs.

Rally records ``status`` in ``state.yaml``, but a stored string cannot tell
you whether the recorded RUNNING process is still alive, whether the
heartbeat is fresh, or whether the pid has been reused by an unrelated
process. The reconciler takes the stored state and combines it with the
heartbeat, the done-marker, and a live probe of the recorded ``(pid,
create_time)`` to return a :class:`ReconciledStatus` — a superset of
:class:`RunStatus` that includes the purely-computed values CRASHED,
ORPHANED, and STALE.

Design notes:

* **Pure function.** ``reconcile`` never writes to disk. Computed-only
  values like CRASHED are not persisted; they are recomputed on every read.
  The user "accepts" a CRASHED run by explicitly resuming it.

* **Terminal states are sticky.** If ``status`` is already DONE, BLOCKED, or
  STOPPED, the reconciler passes it through even if the pid is long gone —
  the run is finished and its story is written.

* **Pre-detach state files are legal.** A v1 ``state.yaml`` has no pid
  fields. For those we trust the stored status as-is and return NO identity
  / heartbeat information — operators see the legacy behavior.

* **done.json wins over a dead pid.** There is an unavoidable race: the
  runner can finalize state + write done.json and then exit. A reader
  sampling the run right at that moment sees RUNNING + dead pid + done
  marker present. We prefer "the run finished" over "the run crashed" in
  that window.

The reconciler is invoked on every ``rally status`` call and anywhere else
the operator asks "what is the real state of this run?" — it is therefore
O(1) plus one ``psutil.Process`` probe, with no I/O beyond the stat/read
of the run directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rally.domain.run import (
    RUN_STATUS_TERMINAL,
    ReconciledStatus,
    RunState,
    RunStatus,
)
from rally.services.heartbeat import (
    DEFAULT_STALE_THRESHOLD_SECONDS,
    HeartbeatReader,
    HeartbeatSnapshot,
    is_heartbeat_stale,
)
from rally.services.process_identity import (
    LivenessStatus,
    ProcessIdentity,
    probe,
)
from rally.services.run_store import load_run_state

__all__ = [
    "ReconciledRun",
    "done_marker_path",
    "reconcile",
    "stop_requested_path",
]


def done_marker_path(run_dir: Path) -> Path:
    """Return the path of the clean-exit sentinel for ``run_dir``."""
    return run_dir / "done.json"


def stop_requested_path(run_dir: Path) -> Path:
    """Return the path of the cooperative-stop request file for ``run_dir``."""
    return run_dir / "control" / "stop.requested"


@dataclass(frozen=True)
class ReconciledRun:
    """Result of reconciling a run directory against live system state.

    ``status`` is the authoritative computed status callers should display.
    The remaining fields are diagnostics — present so ``rally status`` can
    render them without re-reading the same inputs.
    """

    status: ReconciledStatus
    state: RunState
    identity: ProcessIdentity | None
    liveness: LivenessStatus | None
    heartbeat: HeartbeatSnapshot | None
    heartbeat_stale: bool
    done_marker_present: bool
    stop_requested: bool


def reconcile(
    run_dir: Path,
    *,
    now: datetime | None = None,
    stale_threshold_seconds: float = DEFAULT_STALE_THRESHOLD_SECONDS,
) -> ReconciledRun:
    """Compute the reconciled status of ``run_dir``.

    ``now`` and ``stale_threshold_seconds`` exist for test determinism; in
    production callers omit them.
    """
    state = load_run_state(run_dir=run_dir)
    return reconcile_from_state(
        run_dir=run_dir,
        state=state,
        now=now,
        stale_threshold_seconds=stale_threshold_seconds,
    )


def reconcile_from_state(
    *,
    run_dir: Path,
    state: RunState,
    now: datetime | None = None,
    stale_threshold_seconds: float = DEFAULT_STALE_THRESHOLD_SECONDS,
) -> ReconciledRun:
    """Variant that accepts an already-loaded ``state`` to avoid a reread."""
    heartbeat = HeartbeatReader.read(run_dir)
    done_present = done_marker_path(run_dir).is_file()
    stop_requested = stop_requested_path(run_dir).is_file()
    reference_now = (now or datetime.now(UTC)).astimezone(UTC)
    heartbeat_stale = bool(
        heartbeat is not None
        and is_heartbeat_stale(
            heartbeat,
            threshold_seconds=stale_threshold_seconds,
            now=reference_now,
        )
    )

    identity: ProcessIdentity | None = None
    liveness: LivenessStatus | None = None
    if state.pid is not None and state.process_create_time is not None:
        identity = ProcessIdentity(
            pid=state.pid,
            create_time=state.process_create_time,
        )
        liveness = probe(identity)

    status = _compute_status(
        state=state,
        identity=identity,
        liveness=liveness,
        heartbeat_stale=heartbeat_stale,
        done_marker_present=done_present,
    )
    return ReconciledRun(
        status=status,
        state=state,
        identity=identity,
        liveness=liveness,
        heartbeat=heartbeat,
        heartbeat_stale=heartbeat_stale,
        done_marker_present=done_present,
        stop_requested=stop_requested,
    )


def _compute_status(
    *,
    state: RunState,
    identity: ProcessIdentity | None,
    liveness: LivenessStatus | None,
    heartbeat_stale: bool,
    done_marker_present: bool,
) -> ReconciledStatus:
    stored = state.status

    # Terminal stored statuses are sticky. The run is finished; do not
    # second-guess it.
    if stored in RUN_STATUS_TERMINAL:
        return ReconciledStatus(stored.value)

    # Without a recorded identity this is either a foreground run or a
    # pre-detach (v1) state file. Either way we have no basis to override
    # the stored status — trust what the writer saw.
    if identity is None or liveness is None:
        return ReconciledStatus(stored.value)

    if liveness is LivenessStatus.DEAD:
        # done.json wins over a dead pid — finalization-race tolerance.
        if done_marker_present:
            return ReconciledStatus(stored.value)
        return ReconciledStatus.CRASHED

    if liveness is LivenessStatus.REUSED:
        # Pid still exists, but belongs to someone else.
        return ReconciledStatus.ORPHANED

    # liveness is ALIVE from here on.
    if stored is RunStatus.RUNNING and heartbeat_stale:
        return ReconciledStatus.STALE

    return ReconciledStatus(stored.value)
