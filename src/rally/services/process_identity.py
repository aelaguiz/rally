"""Durable process identity for Rally runs.

A bare PID is not a durable identity: PIDs are reused after the previous
owner exits, so ``os.kill(pid, 0)`` can report "alive" for a totally
unrelated process that happens to reuse the number. We need ``(pid,
create_time)`` — the process's kernel-reported start time, which is
immutable across the process's lifetime and effectively unique.

Detached Rally runs record this tuple in ``state.yaml`` (and the heartbeat
file). The reconciler probes it on every status read to distinguish:

  * ALIVE — process still running and matches the recorded tuple.
  * DEAD  — no process with that pid at all.
  * REUSED — a process with that pid exists but its start time differs, so
    the original Rally child died and something unrelated took the pid.

Only psutil is used from this module; no other code should import psutil
directly. That way the dependency is swappable if we ever need to move off
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

import psutil

__all__ = [
    "CREATE_TIME_EPSILON_SECONDS",
    "LivenessStatus",
    "ProcessIdentity",
    "capture_self",
    "is_zombie",
    "probe",
]


# psutil's create_time() is derived from ``/proc/[pid]/stat`` on Linux and
# can jitter by a jiffy or two depending on clock source / rounding. Allow a
# very small window when comparing — a REUSED process always differs by
# hundreds of milliseconds at minimum, so this is safe.
CREATE_TIME_EPSILON_SECONDS: Final[float] = 0.5


class LivenessStatus(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"
    REUSED = "reused"


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    create_time: float

    @classmethod
    def from_psutil(cls, process: psutil.Process) -> "ProcessIdentity":
        return cls(pid=process.pid, create_time=process.create_time())


def capture_self() -> ProcessIdentity:
    """Capture the current process's durable identity."""
    return ProcessIdentity.from_psutil(psutil.Process())


def probe(identity: ProcessIdentity) -> LivenessStatus:
    """Return the current liveness status for ``identity``."""
    try:
        process = psutil.Process(identity.pid)
    except psutil.NoSuchProcess:
        return LivenessStatus.DEAD
    try:
        current_create_time = process.create_time()
    except psutil.NoSuchProcess:
        return LivenessStatus.DEAD
    except psutil.AccessDenied:
        # If the kernel will not tell us the create_time (can happen in
        # sandboxes for processes we don't own), assume the pid is not ours.
        return LivenessStatus.REUSED
    if abs(current_create_time - identity.create_time) > CREATE_TIME_EPSILON_SECONDS:
        return LivenessStatus.REUSED
    # Zombie processes still count as "alive" for our purposes: state-wise
    # they have not yet been reaped, and any pid reuse must wait for that.
    # We deliberately do NOT filter on process.status() here.
    return LivenessStatus.ALIVE


def is_zombie(identity: ProcessIdentity) -> bool:
    """Return True when the pid exists but is a zombie awaiting reap.

    The reconciler treats zombies as ALIVE (pid reuse is still blocked), but
    the stop path wants to know whether the process is still executing: a
    zombie is not, so signaling it further is pointless.
    """
    try:
        process = psutil.Process(identity.pid)
        return process.status() == psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
