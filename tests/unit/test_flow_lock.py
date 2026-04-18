from __future__ import annotations

import multiprocessing as mp
import os
import tempfile
import time
import unittest
from pathlib import Path

from rally.errors import RallyStateError
from rally.services.run_store import (
    acquire_flow_lock_fd,
    flow_lock,
    flow_lock_path,
)


def _hold_lock_child(repo_root_str: str, hold_seconds: float, ready_path_str: str) -> None:
    # Runs in a subprocess: acquires the flock, signals readiness, sleeps.
    fd = acquire_flow_lock_fd(repo_root=Path(repo_root_str), flow_code="DMO")
    Path(ready_path_str).write_text("ready", encoding="utf-8")
    time.sleep(hold_seconds)
    os.close(fd)


class FlowLockTests(unittest.TestCase):
    def test_flow_lock_context_manager_roundtrips(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            with flow_lock(repo_root=repo_root, flow_code="DMO") as lock_path:
                self.assertTrue(lock_path.is_file())
                # PID is recorded for operator debugging (not for exclusion).
                self.assertEqual(lock_path.read_text(encoding="utf-8"), f"{os.getpid()}\n")
            # Lock file persists after release; that's fine — flock is by fd.
            self.assertTrue(lock_path.is_file())

    def test_flow_lock_reentrant_in_same_process_fails_fast(self) -> None:
        # fcntl.flock LOCK_EX is per-open-file-description, so a second
        # attempt from the same process acquiring a fresh fd must also fail.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                with self.assertRaises(RallyStateError) as ctx:
                    with flow_lock(repo_root=repo_root, flow_code="DMO"):
                        pass
                self.assertIn("already locked", str(ctx.exception))

    def test_flow_lock_released_after_context_exits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                pass
            # After exit, another acquisition must succeed.
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                pass

    def test_flow_lock_blocks_second_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            ready_path = Path(temp_dir) / "ready"
            ctx = mp.get_context("fork")
            proc = ctx.Process(
                target=_hold_lock_child,
                args=(str(repo_root), 1.5, str(ready_path)),
            )
            proc.start()
            try:
                # Wait for child to acquire.
                deadline = time.monotonic() + 5.0
                while not ready_path.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready_path.exists(), "child never acquired lock")

                with self.assertRaises(RallyStateError):
                    with flow_lock(repo_root=repo_root, flow_code="DMO"):
                        pass
            finally:
                proc.join(timeout=5.0)
                self.assertEqual(proc.exitcode, 0)

            # After the child exits, lock is free again.
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                pass

    def test_lock_released_on_process_death(self) -> None:
        # Even if the child is SIGKILLed mid-hold, the kernel releases flock.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            ready_path = Path(temp_dir) / "ready"
            ctx = mp.get_context("fork")
            proc = ctx.Process(
                target=_hold_lock_child,
                args=(str(repo_root), 60.0, str(ready_path)),
            )
            proc.start()
            try:
                deadline = time.monotonic() + 5.0
                while not ready_path.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready_path.exists())
                # Parent can't acquire.
                with self.assertRaises(RallyStateError):
                    with flow_lock(repo_root=repo_root, flow_code="DMO"):
                        pass
                # Kill the holder hard.
                proc.kill()
                proc.join(timeout=5.0)
            finally:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=5.0)

            # Kernel has released the lock; parent can acquire.
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                pass

    def test_acquire_flow_lock_fd_returns_usable_fd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            fd = acquire_flow_lock_fd(repo_root=repo_root, flow_code="DMO")
            try:
                # While fd is held, context-manager form must fail.
                with self.assertRaises(RallyStateError):
                    with flow_lock(repo_root=repo_root, flow_code="DMO"):
                        pass
            finally:
                os.close(fd)
            # After close, the context manager works again.
            with flow_lock(repo_root=repo_root, flow_code="DMO"):
                pass

    def test_flow_lock_path_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            path = flow_lock_path(repo_root=repo_root, flow_code="DMO")
            self.assertEqual(path, repo_root / "runs" / "locks" / "DMO.lock")
            self.assertTrue(path.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
