"""Stop a detached (or foreground) Rally run, cooperatively or forcibly.

Two mechanisms, layered:

1. **Cooperative stop** — write ``control/stop.requested`` into the run
   directory. The runner loop checks this file at the top of each turn
   iteration and finalizes the run as STOPPED. Safe, composable, always the
   preferred path. Idempotent.

2. **Hard stop** — send SIGTERM to the run's process (or process group, for
   detached runs whose runner is its own pgid leader), wait for the grace
   window, then SIGKILL anything still alive. Reserved for wedged runs that
   cannot be coaxed out by the cooperative path.

This module is deliberately import-light: the CLI calls straight into these
functions with just the repo root and the run id.
"""

from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path

from rally.errors import RallyStateError, RallyUsageError
from rally.services.atomic_io import write_atomic
from rally.services.process_identity import (
    LivenessStatus,
    ProcessIdentity,
    is_zombie,
    probe,
)
from rally.services.reconcile import done_marker_path, stop_requested_path
from rally.services.run_store import find_run_dir, load_run_state

__all__ = [
    "DEFAULT_GRACE_SECONDS",
    "StopOutcome",
    "clear_stop_request",
    "is_stop_requested",
    "kill_run",
    "request_stop",
]


DEFAULT_GRACE_SECONDS: float = 10.0


@dataclass(frozen=True)
class StopOutcome:
    """Result of a stop attempt, for CLI display + test assertions."""

    run_id: str
    action: str  # "requested" | "already-terminal" | "already-requested" | "killed" | "no-process" | "escalated"
    message: str


def is_stop_requested(run_dir: Path) -> bool:
    """Return True if a cooperative stop file is present."""
    return stop_requested_path(run_dir).is_file()


def clear_stop_request(run_dir: Path) -> None:
    """Remove the cooperative-stop marker, if any. Idempotent."""
    target = stop_requested_path(run_dir)
    try:
        target.unlink()
    except FileNotFoundError:
        return


def request_stop(*, repo_root: Path, run_id: str) -> StopOutcome:
    """Ask ``run_id`` to stop at the next turn boundary. Idempotent.

    Writes ``control/stop.requested`` atomically. If the run's stored status
    is already terminal, no file is written — the caller is told nothing
    more is needed.
    """
    run_dir = _resolve_run_dir(repo_root=repo_root, run_id=run_id)
    state = load_run_state(run_dir=run_dir)
    if state.status.value in {"done", "blocked", "stopped"}:
        return StopOutcome(
            run_id=run_id,
            action="already-terminal",
            message=f"Run `{run_id}` is already `{state.status.value}`; no stop needed.",
        )

    target = stop_requested_path(run_dir)
    if target.is_file():
        return StopOutcome(
            run_id=run_id,
            action="already-requested",
            message=(
                f"Stop was already requested for run `{run_id}`. "
                "It will transition on the next turn boundary."
            ),
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(target, "stop\n")
    return StopOutcome(
        run_id=run_id,
        action="requested",
        message=(
            f"Requested cooperative stop for run `{run_id}`. "
            "The runner will finalize STOPPED at the next turn boundary."
        ),
    )


def kill_run(
    *,
    repo_root: Path,
    run_id: str,
    grace_seconds: float = DEFAULT_GRACE_SECONDS,
) -> StopOutcome:
    """Hard-stop ``run_id`` by signaling its recorded pid / pgid.

    Sends SIGTERM, waits up to ``grace_seconds`` for the process to exit,
    and then sends SIGKILL if necessary. If the run has no recorded pid (a
    foreground run that was already exited, or a pre-detach state file),
    we cannot kill anything — the caller is told so explicitly.
    """
    run_dir = _resolve_run_dir(repo_root=repo_root, run_id=run_id)
    state = load_run_state(run_dir=run_dir)
    if state.pid is None or state.process_create_time is None:
        return StopOutcome(
            run_id=run_id,
            action="no-process",
            message=(
                f"Run `{run_id}` has no recorded process identity; there is "
                "nothing to signal."
            ),
        )

    identity = ProcessIdentity(pid=state.pid, create_time=state.process_create_time)
    liveness = probe(identity)
    if liveness is not LivenessStatus.ALIVE:
        return StopOutcome(
            run_id=run_id,
            action="no-process",
            message=(
                f"Run `{run_id}` recorded pid `{state.pid}` is `{liveness.value}`; "
                "nothing to signal."
            ),
        )

    target_pgid = state.pgid if state.pgid is not None else None
    use_pgid = target_pgid is not None and target_pgid == state.pid

    _signal(state.pid, target_pgid=target_pgid if use_pgid else None, sig=signal.SIGTERM)
    if _wait_until_dead(identity, deadline_seconds=max(0.0, grace_seconds)):
        return StopOutcome(
            run_id=run_id,
            action="killed",
            message=(
                f"Run `{run_id}` received SIGTERM and exited within "
                f"`{grace_seconds:.1f}s`."
            ),
        )

    _signal(state.pid, target_pgid=target_pgid if use_pgid else None, sig=signal.SIGKILL)
    return StopOutcome(
        run_id=run_id,
        action="escalated",
        message=(
            f"Run `{run_id}` did not exit after SIGTERM and was sent SIGKILL. "
            "Reconciler will report CRASHED unless the runner wrote a done "
            "marker first."
        ),
    )


def _resolve_run_dir(*, repo_root: Path, run_id: str) -> Path:
    try:
        return find_run_dir(repo_root=repo_root, run_id=run_id)
    except RallyStateError as exc:
        raise RallyUsageError(
            f"Run `{run_id}` does not exist. Use `rally status` to list active runs."
        ) from exc


def _signal(pid: int, *, target_pgid: int | None, sig: int) -> None:
    """Deliver ``sig`` to the pid, or the pgid when safe. Errors suppressed."""
    try:
        if target_pgid is not None:
            os.killpg(target_pgid, sig)
        else:
            os.kill(pid, sig)
    except ProcessLookupError:
        # Already gone; nothing to do.
        return
    except PermissionError:
        # The CLI lacks permission. Fall through — caller will surface the
        # ensuing "not dead" outcome as SIGKILL-escalated, which mirrors
        # what a real permission issue would look like to the user.
        return


def _wait_until_dead(
    identity: ProcessIdentity,
    *,
    deadline_seconds: float,
    poll_interval_seconds: float = 0.1,
) -> bool:
    """Poll ``probe`` until the process is not ALIVE or we run out of time.

    Zombie processes count as dead here: the process is no longer executing
    code and signaling it again is pointless. (The reconciler treats zombies
    as ALIVE because pid reuse is still blocked until the parent reaps them,
    but for the stop path we only care about "is it doing anything.")
    """
    deadline = time.monotonic() + deadline_seconds
    while True:
        status = probe(identity)
        if status is not LivenessStatus.ALIVE:
            return True
        if is_zombie(identity):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval_seconds)
