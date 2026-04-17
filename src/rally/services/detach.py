"""Double-fork detach for Rally background runs.

A detached Rally run is an ordinary Rally process with three changes:

1. It is not a child of the invoking shell (double-fork + ``setsid``), so
   closing the terminal does not send it SIGHUP.
2. Its standard streams are redirected into ``logs/stdout.log`` /
   ``logs/stderr.log`` inside the run directory, so anything the loop or
   the adapter writes survives the shell.
3. It is its own process-group leader (``setpgrp``), so ``rally stop --now``
   can ``killpg`` the whole subtree without racing against the shell's own
   pgid.

``spawn_detached`` handles all three, plus the subtle fd-inheritance dance:
the flow lock (``fcntl.flock`` on an open fd) is inherited by the
grandchild so the lock survives the hand-off. The parent exits via
``os._exit`` to skip atexit handlers (flushing Python's logging machinery
twice would clobber event logs).

Returns a ``DetachHandoff`` in the parent and ``None`` in the grandchild;
the caller switches on the return value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DetachHandoff",
    "spawn_detached",
]


@dataclass(frozen=True)
class DetachHandoff:
    """Parent-side handle to the spawned detached worker."""

    child_pid: int


def spawn_detached(run_dir: Path) -> DetachHandoff | None:
    """Double-fork so the caller detaches from its controlling terminal.

    Returns ``DetachHandoff`` in the original (parent) process and ``None``
    in the detached grandchild. The intermediate child is reaped by the
    parent before returning. Raises ``OSError`` if any fork fails.
    """
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    # Open the log files in the original parent so we surface any EACCES /
    # ENOSPC before forking. They are inherited by the grandchild.
    stdout_fd = os.open(
        logs_dir / "stdout.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644
    )
    stderr_fd = os.open(
        logs_dir / "stderr.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644
    )

    read_fd, write_fd = os.pipe()
    first = os.fork()
    if first != 0:
        # Original parent.
        os.close(write_fd)
        os.close(stdout_fd)
        os.close(stderr_fd)
        try:
            with os.fdopen(read_fd, "rb") as pipe_read:
                raw = pipe_read.read()
        finally:
            try:
                os.waitpid(first, 0)
            except ChildProcessError:
                pass
        if not raw:
            raise OSError("Detach intermediate child exited before reporting pid.")
        grandchild_pid = int(raw.strip())
        return DetachHandoff(child_pid=grandchild_pid)

    # Intermediate child. Must not raise past this point — any exception
    # would propagate into Python's atexit and disturb the parent's view.
    try:
        os.close(read_fd)
        os.setsid()
        second = os.fork()
        if second != 0:
            # Intermediate child: report grandchild pid and exit cleanly.
            try:
                os.write(write_fd, f"{second}\n".encode("ascii"))
            finally:
                os.close(write_fd)
                os.close(stdout_fd)
                os.close(stderr_fd)
            os._exit(0)
        # Grandchild: the detached worker.
        os.close(write_fd)
        try:
            os.setpgrp()
        except OSError:
            pass
        try:
            os.chdir(run_dir)
        except OSError:
            pass
        _redirect_stdio(stdout_fd=stdout_fd, stderr_fd=stderr_fd)
        return None
    except BaseException:
        os._exit(1)


def _redirect_stdio(*, stdout_fd: int, stderr_fd: int) -> None:
    """Point fd 0/1/2 at /dev/null and the run's log files.

    Uses ``os.dup2`` to overwrite the low fds in place so child processes
    (adapters invoked later) inherit the redirected streams.
    """
    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    try:
        os.dup2(devnull_fd, 0)
    finally:
        os.close(devnull_fd)
    os.dup2(stdout_fd, 1)
    os.dup2(stderr_fd, 2)
    if stdout_fd > 2:
        os.close(stdout_fd)
    if stderr_fd > 2:
        os.close(stderr_fd)
