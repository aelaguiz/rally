from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rally.services.heartbeat import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_STALE_THRESHOLD_SECONDS,
    HEARTBEAT_SCHEMA_VERSION,
    HeartbeatReader,
    HeartbeatSnapshot,
    HeartbeatThread,
    heartbeat_path,
    is_heartbeat_stale,
    write_heartbeat,
)
from rally.services.process_identity import ProcessIdentity, capture_self


class HeartbeatWriteReadTests(unittest.TestCase):
    def test_write_heartbeat_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=UTC)
            write_heartbeat(run_dir, identity=identity, turn_index=7, now=now)

            snapshot = HeartbeatReader.read(run_dir)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.pid, identity.pid)
            self.assertAlmostEqual(snapshot.create_time, identity.create_time, places=3)
            self.assertEqual(snapshot.turn_index, 7)
            self.assertEqual(snapshot.ts, "2026-04-17T12:00:00Z")
            self.assertEqual(snapshot.schema_version, HEARTBEAT_SCHEMA_VERSION)
            self.assertEqual(snapshot.identity, ProcessIdentity(identity.pid, identity.create_time))

    def test_read_returns_none_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertIsNone(HeartbeatReader.read(Path(temp_dir)))

    def test_read_returns_none_on_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            heartbeat_path(run_dir).write_text("not json", encoding="utf-8")
            self.assertIsNone(HeartbeatReader.read(run_dir))

    def test_read_returns_none_on_wrong_schema_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            heartbeat_path(run_dir).write_text(json.dumps({"not": "valid"}), encoding="utf-8")
            self.assertIsNone(HeartbeatReader.read(run_dir))

    def test_write_heartbeat_overwrites_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            write_heartbeat(run_dir, identity=identity, turn_index=1)
            write_heartbeat(run_dir, identity=identity, turn_index=2)
            snapshot = HeartbeatReader.read(run_dir)
            assert snapshot is not None
            self.assertEqual(snapshot.turn_index, 2)

    def test_write_heartbeat_accepts_none_turn_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            identity = capture_self()
            write_heartbeat(run_dir, identity=identity, turn_index=None)
            snapshot = HeartbeatReader.read(run_dir)
            assert snapshot is not None
            self.assertIsNone(snapshot.turn_index)


class HeartbeatStalenessTests(unittest.TestCase):
    def _snapshot(self, *, ts: str) -> HeartbeatSnapshot:
        return HeartbeatSnapshot(
            pid=1,
            create_time=0.0,
            ts=ts,
            turn_index=None,
            schema_version=HEARTBEAT_SCHEMA_VERSION,
        )

    def test_fresh_heartbeat_is_not_stale(self) -> None:
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=UTC)
        ts = (now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
        self.assertFalse(is_heartbeat_stale(self._snapshot(ts=ts), now=now))

    def test_old_heartbeat_is_stale(self) -> None:
        now = datetime(2026, 4, 17, 12, 0, 0, tzinfo=UTC)
        ts = (now - timedelta(seconds=DEFAULT_STALE_THRESHOLD_SECONDS + 1)).isoformat().replace(
            "+00:00", "Z"
        )
        self.assertTrue(is_heartbeat_stale(self._snapshot(ts=ts), now=now))

    def test_unparseable_ts_is_stale(self) -> None:
        self.assertTrue(is_heartbeat_stale(self._snapshot(ts="not-a-timestamp")))


class HeartbeatThreadTests(unittest.TestCase):
    def test_thread_writes_initial_heartbeat_before_sleeping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            thread = HeartbeatThread(run_dir=run_dir, interval_seconds=60.0)
            thread.start()
            try:
                self.assertTrue(heartbeat_path(run_dir).is_file())
            finally:
                thread.stop()

    def test_thread_updates_heartbeat_on_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            counter = {"n": 0}

            def get_turn_index() -> int:
                counter["n"] += 1
                return counter["n"]

            thread = HeartbeatThread(
                run_dir=run_dir,
                interval_seconds=0.1,
                get_turn_index=get_turn_index,
            )
            thread.start()
            try:
                time.sleep(0.35)
            finally:
                thread.stop()

            snapshot = HeartbeatReader.read(run_dir)
            assert snapshot is not None
            self.assertGreaterEqual(counter["n"], 2)
            self.assertIsNotNone(snapshot.turn_index)

    def test_thread_stop_is_idempotent_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            thread = HeartbeatThread(run_dir=Path(temp_dir), interval_seconds=60.0)
            thread.start()
            start = time.monotonic()
            thread.stop(timeout=5.0)
            elapsed = time.monotonic() - start
            # Must not wait the full interval; wake is cooperative.
            self.assertLess(elapsed, 2.0)
            # Second stop is a no-op.
            thread.stop(timeout=1.0)

    def test_thread_cannot_be_started_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            thread = HeartbeatThread(run_dir=Path(temp_dir), interval_seconds=60.0)
            thread.start()
            try:
                with self.assertRaises(RuntimeError):
                    thread.start()
            finally:
                thread.stop()

    def test_defaults_are_reasonable(self) -> None:
        # Guard against accidental constant changes that would break the
        # "stale_threshold is 3x interval" invariant the reconciler relies on.
        self.assertAlmostEqual(DEFAULT_STALE_THRESHOLD_SECONDS, DEFAULT_INTERVAL_SECONDS * 3)


if __name__ == "__main__":
    unittest.main()
