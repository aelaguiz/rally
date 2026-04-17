from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from rally.domain.run import (
    RUN_STATE_SCHEMA_VERSION,
    ReconciledStatus,
    RunState,
    RunStatus,
)
from rally.services.heartbeat import (
    DEFAULT_STALE_THRESHOLD_SECONDS,
    HEARTBEAT_SCHEMA_VERSION,
    heartbeat_path,
    write_heartbeat,
)
from rally.services.process_identity import ProcessIdentity, capture_self
from rally.services.reconcile import (
    done_marker_path,
    reconcile,
    stop_requested_path,
)
from rally.services.run_store import write_run_state


_FIXED_NOW = datetime(2026, 4, 17, 12, 0, 0, tzinfo=UTC)


def _write_state(
    run_dir: Path,
    *,
    status: RunStatus,
    identity: ProcessIdentity | None,
) -> RunState:
    state = RunState(
        status=status,
        current_agent_key="writer",
        current_agent_slug="writer",
        turn_index=3,
        updated_at="2026-04-17T11:59:30Z",
        pid=identity.pid if identity else None,
        process_create_time=identity.create_time if identity else None,
        pgid=identity.pid if identity else None,
    )
    write_run_state(run_dir=run_dir, state=state)
    return state


def _write_fresh_heartbeat(run_dir: Path, identity: ProcessIdentity) -> None:
    write_heartbeat(
        run_dir,
        identity=identity,
        turn_index=3,
        now=_FIXED_NOW - timedelta(seconds=5),
    )


def _write_stale_heartbeat(run_dir: Path, identity: ProcessIdentity) -> None:
    write_heartbeat(
        run_dir,
        identity=identity,
        turn_index=3,
        now=_FIXED_NOW - timedelta(seconds=DEFAULT_STALE_THRESHOLD_SECONDS + 30),
    )


def _write_done_marker(run_dir: Path) -> None:
    done_marker_path(run_dir).write_text(
        json.dumps({"at": "2026-04-17T12:00:00Z"}), encoding="utf-8"
    )


def _write_stop_request(run_dir: Path) -> None:
    target = stop_requested_path(run_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")


class ReconcileTerminalStoredStatusTests(unittest.TestCase):
    """Terminal stored statuses pass through unchanged regardless of liveness."""

    def test_done_is_sticky_even_when_pid_long_gone(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            bogus = ProcessIdentity(pid=(1 << 31) - 1, create_time=0.0)
            _write_state(run_dir, status=RunStatus.DONE, identity=bogus)
            result = reconcile(run_dir, now=_FIXED_NOW)
            self.assertEqual(result.status, ReconciledStatus.DONE)

    def test_blocked_is_sticky(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            _write_state(run_dir, status=RunStatus.BLOCKED, identity=None)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.BLOCKED,
            )

    def test_stopped_is_sticky(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            _write_state(run_dir, status=RunStatus.STOPPED, identity=None)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.STOPPED,
            )


class ReconcileForegroundRunTests(unittest.TestCase):
    """With no pid recorded, stored status wins (foreground / v1 state.yaml)."""

    def test_running_without_pid_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            _write_state(run_dir, status=RunStatus.RUNNING, identity=None)
            result = reconcile(run_dir, now=_FIXED_NOW)
            self.assertEqual(result.status, ReconciledStatus.RUNNING)
            self.assertIsNone(result.identity)
            self.assertIsNone(result.liveness)

    def test_v1_state_yaml_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            # Hand-craft a v1-shaped state.yaml: no pid fields, no schema_version.
            (run_dir / "state.yaml").write_text(
                yaml.safe_dump(
                    {
                        "status": "running",
                        "current_agent_key": "writer",
                        "current_agent_slug": "writer",
                        "turn_index": 1,
                        "updated_at": "2026-04-17T11:00:00Z",
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            result = reconcile(run_dir, now=_FIXED_NOW)
            self.assertEqual(result.status, ReconciledStatus.RUNNING)
            self.assertEqual(result.state.schema_version, 1)
            self.assertIsNone(result.identity)


class ReconcileLiveProcessTests(unittest.TestCase):
    def test_running_with_live_pid_and_fresh_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            _write_state(run_dir, status=RunStatus.RUNNING, identity=identity)
            _write_fresh_heartbeat(run_dir, identity)
            result = reconcile(run_dir, now=_FIXED_NOW)
            self.assertEqual(result.status, ReconciledStatus.RUNNING)
            self.assertFalse(result.heartbeat_stale)
            self.assertIsNotNone(result.heartbeat)

    def test_paused_with_live_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            _write_state(run_dir, status=RunStatus.PAUSED, identity=identity)
            # PAUSED runs legitimately go quiet — staleness should not flip them.
            _write_stale_heartbeat(run_dir, identity)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.PAUSED,
            )

    def test_running_with_stale_heartbeat_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            _write_state(run_dir, status=RunStatus.RUNNING, identity=identity)
            _write_stale_heartbeat(run_dir, identity)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.STALE,
            )

    def test_stop_request_is_surfaced_as_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            _write_state(run_dir, status=RunStatus.RUNNING, identity=identity)
            _write_fresh_heartbeat(run_dir, identity)
            _write_stop_request(run_dir)
            result = reconcile(run_dir, now=_FIXED_NOW)
            # Status is still RUNNING until the loop observes the file; the
            # request itself is a diagnostic.
            self.assertEqual(result.status, ReconciledStatus.RUNNING)
            self.assertTrue(result.stop_requested)


class ReconcileDeadProcessTests(unittest.TestCase):
    def test_running_with_dead_pid_and_no_done_marker_is_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            dead = ProcessIdentity(pid=(1 << 31) - 1, create_time=1.0)
            _write_state(run_dir, status=RunStatus.RUNNING, identity=dead)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.CRASHED,
            )

    def test_running_with_dead_pid_but_done_marker_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            dead = ProcessIdentity(pid=(1 << 31) - 1, create_time=1.0)
            _write_state(run_dir, status=RunStatus.RUNNING, identity=dead)
            _write_done_marker(run_dir)
            # Finalization-race: loop wrote done.json but got scheduled out
            # before state.yaml could land DONE. Trust the done marker.
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.RUNNING,
            )

    def test_paused_with_dead_pid_and_no_done_marker_is_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            dead = ProcessIdentity(pid=(1 << 31) - 1, create_time=1.0)
            _write_state(run_dir, status=RunStatus.PAUSED, identity=dead)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.CRASHED,
            )


class ReconcileReusedPidTests(unittest.TestCase):
    def test_running_with_reused_pid_is_orphaned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            # Forge: real current pid, but a wildly wrong create_time. The
            # probe will report REUSED — our recorded identity doesn't match
            # the live process anymore.
            live = capture_self()
            stale_identity = ProcessIdentity(
                pid=live.pid,
                create_time=live.create_time - 3600.0,
            )
            _write_state(run_dir, status=RunStatus.RUNNING, identity=stale_identity)
            self.assertEqual(
                reconcile(run_dir, now=_FIXED_NOW).status,
                ReconciledStatus.ORPHANED,
            )


class ReconcileDiagnosticsTests(unittest.TestCase):
    def test_heartbeat_path_and_stop_path_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            self.assertEqual(heartbeat_path(run_dir), run_dir / "heartbeat.json")
            self.assertEqual(
                stop_requested_path(run_dir),
                run_dir / "control" / "stop.requested",
            )
            self.assertEqual(done_marker_path(run_dir), run_dir / "done.json")

    def test_reconcile_reports_heartbeat_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            _write_state(run_dir, status=RunStatus.RUNNING, identity=identity)
            _write_fresh_heartbeat(run_dir, identity)
            snapshot = reconcile(run_dir, now=_FIXED_NOW).heartbeat
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.pid, identity.pid)
            self.assertEqual(snapshot.schema_version, HEARTBEAT_SCHEMA_VERSION)


class ReconcileSchemaVersionTests(unittest.TestCase):
    def test_round_trip_preserves_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            _write_state(run_dir, status=RunStatus.RUNNING, identity=capture_self())
            result = reconcile(run_dir, now=_FIXED_NOW)
            self.assertEqual(result.state.schema_version, RUN_STATE_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
