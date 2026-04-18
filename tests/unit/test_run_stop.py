from __future__ import annotations

import multiprocessing as mp
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path

from rally.domain.run import RunState, RunStatus
from rally.errors import RallyUsageError
from rally.services.process_identity import ProcessIdentity, capture_self
from rally.services.reconcile import stop_requested_path
from rally.services.run_stop import (
    clear_stop_request,
    is_stop_requested,
    kill_run,
    request_stop,
)
from rally.services.run_store import (
    active_runs_dir,
    flow_lock_path,
    write_run_state,
)


def _sleep_forever() -> None:
    # Swallow SIGTERM so the test can assert the SIGKILL escalation path.
    signal.signal(signal.SIGTERM, lambda *_args: None)
    while True:
        time.sleep(3600)


def _exit_on_sigterm() -> None:
    # Explicitly default SIGTERM — the Python process terminates on receipt.
    # A custom handler + time.sleep has been observed to race on macOS fork.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    while True:
        time.sleep(3600)


def _make_repo_with_run(
    tmp: Path,
    *,
    run_id: str = "DMO-1",
    status: RunStatus = RunStatus.RUNNING,
    identity: ProcessIdentity | None = None,
    pgid: int | None = None,
) -> Path:
    run_dir = active_runs_dir(tmp) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    # Touch the flow lock dir so imports work (not required for these tests).
    flow_lock_path(repo_root=tmp, flow_code="DMO")
    state = RunState(
        status=status,
        current_agent_key="writer",
        current_agent_slug="writer",
        turn_index=0,
        updated_at="2026-04-17T12:00:00Z",
        pid=identity.pid if identity else None,
        process_create_time=identity.create_time if identity else None,
        pgid=pgid,
    )
    write_run_state(run_dir=run_dir, state=state)
    return run_dir


class RequestStopTests(unittest.TestCase):
    def test_writes_stop_marker_for_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_repo_with_run(repo_root, status=RunStatus.RUNNING)
            outcome = request_stop(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(outcome.action, "requested")
            self.assertTrue(is_stop_requested(run_dir))
            self.assertIn("cooperative stop", outcome.message)

    def test_second_request_reports_already_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _make_repo_with_run(repo_root, status=RunStatus.RUNNING)
            request_stop(repo_root=repo_root, run_id="DMO-1")
            outcome = request_stop(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(outcome.action, "already-requested")

    def test_terminal_run_short_circuits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_repo_with_run(repo_root, status=RunStatus.DONE)
            outcome = request_stop(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(outcome.action, "already-terminal")
            self.assertFalse(is_stop_requested(run_dir))

    def test_unknown_run_raises_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(RallyUsageError):
                request_stop(repo_root=Path(temp_dir), run_id="XYZ-9")

    def test_clear_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_repo_with_run(repo_root, status=RunStatus.RUNNING)
            request_stop(repo_root=repo_root, run_id="DMO-1")
            self.assertTrue(stop_requested_path(run_dir).is_file())
            clear_stop_request(run_dir)
            clear_stop_request(run_dir)
            self.assertFalse(stop_requested_path(run_dir).is_file())


class KillRunTests(unittest.TestCase):
    def test_reports_no_process_when_pid_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _make_repo_with_run(repo_root, status=RunStatus.RUNNING, identity=None)
            outcome = kill_run(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(outcome.action, "no-process")

    def test_reports_no_process_when_pid_is_dead(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            stale = ProcessIdentity(pid=(1 << 31) - 1, create_time=1.0)
            _make_repo_with_run(repo_root, status=RunStatus.RUNNING, identity=stale)
            outcome = kill_run(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(outcome.action, "no-process")

    def test_sigterm_path_kills_a_graceful_child(self) -> None:
        ctx = mp.get_context("fork")
        proc = ctx.Process(target=_exit_on_sigterm)
        proc.start()
        # Let the child reach signal.signal() before we probe.
        time.sleep(0.3)
        try:
            self.assertIsNotNone(proc.pid)
            from rally.services.process_identity import psutil
            identity = ProcessIdentity.from_psutil(psutil.Process(proc.pid))
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_root = Path(temp_dir)
                _make_repo_with_run(repo_root, status=RunStatus.RUNNING, identity=identity)
                outcome = kill_run(repo_root=repo_root, run_id="DMO-1", grace_seconds=5.0)
                self.assertEqual(outcome.action, "killed")
        finally:
            proc.kill()
            proc.join(timeout=5.0)

    def test_sigkill_escalation_when_sigterm_is_swallowed(self) -> None:
        ctx = mp.get_context("fork")
        proc = ctx.Process(target=_sleep_forever)
        proc.start()
        try:
            self.assertIsNotNone(proc.pid)
            from rally.services.process_identity import psutil
            identity = ProcessIdentity.from_psutil(psutil.Process(proc.pid))
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_root = Path(temp_dir)
                _make_repo_with_run(repo_root, status=RunStatus.RUNNING, identity=identity)
                outcome = kill_run(
                    repo_root=repo_root,
                    run_id="DMO-1",
                    grace_seconds=0.5,
                )
                self.assertEqual(outcome.action, "escalated")
            # Give the kernel a moment to reap.
            proc.join(timeout=5.0)
            self.assertFalse(proc.is_alive())
        finally:
            if proc.is_alive():
                proc.kill()
                proc.join(timeout=5.0)


if __name__ == "__main__":
    unittest.main()
