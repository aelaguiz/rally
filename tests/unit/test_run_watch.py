from __future__ import annotations

import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from rally.domain.run import RunState, RunStatus
from rally.errors import RallyStateError
from rally.services.run_watch import watch_run
from rally.services.run_store import active_runs_dir, flow_lock_path, write_run_state


def _make_run(tmp: Path, *, run_id: str = "DMO-1", status: RunStatus = RunStatus.RUNNING) -> Path:
    run_dir = active_runs_dir(tmp) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    flow_lock_path(repo_root=tmp, flow_code="DMO")
    write_run_state(
        run_dir=run_dir,
        state=RunState(
            status=status,
            current_agent_key="writer",
            current_agent_slug="writer",
            turn_index=0,
            updated_at="2026-04-17T12:00:00Z",
        ),
    )
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    return run_dir


def _append_event(
    run_dir: Path,
    *,
    code: str,
    message: str,
    ts: str = "2026-04-17T12:00:00Z",
) -> None:
    events_path = run_dir / "logs" / "events.jsonl"
    payload = {
        "ts": ts,
        "run_id": "DMO-1",
        "flow_code": "DMO",
        "source": "rally",
        "kind": "lifecycle",
        "code": code,
        "message": message,
        "level": "info",
        "data": {},
        "turn_index": None,
        "agent_key": None,
        "agent_slug": None,
    }
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


class WatchRunTests(unittest.TestCase):
    def test_prints_existing_events_without_follow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_run(repo_root)
            _append_event(run_dir, code="RUN", message="Created run `DMO-1`.")
            _append_event(run_dir, code="HANDOFF", message="writer → reviewer.")

            out = io.StringIO()
            printed = watch_run(
                repo_root=repo_root, run_id="DMO-1", stream=out, follow=False
            )

            self.assertEqual(printed, 2)
            output = out.getvalue()
            self.assertIn("RUN ", output)
            self.assertIn("HANDOFF", output)
            self.assertIn("Created run `DMO-1`.", output)

    def test_since_skips_leading_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_run(repo_root)
            for idx in range(3):
                _append_event(run_dir, code="TICK", message=f"event-{idx}")

            out = io.StringIO()
            printed = watch_run(
                repo_root=repo_root, run_id="DMO-1", since=2, stream=out, follow=False
            )

            self.assertEqual(printed, 1)
            self.assertIn("event-2", out.getvalue())
            self.assertNotIn("event-0", out.getvalue())
            self.assertNotIn("event-1", out.getvalue())

    def test_missing_events_file_prints_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            _make_run(repo_root)
            out = io.StringIO()
            printed = watch_run(
                repo_root=repo_root, run_id="DMO-1", stream=out, follow=False
            )
            self.assertEqual(printed, 0)
            self.assertEqual(out.getvalue(), "")

    def test_unknown_run_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = io.StringIO()
            with self.assertRaises(RallyStateError):
                watch_run(
                    repo_root=Path(temp_dir),
                    run_id="XYZ-9",
                    stream=out,
                    follow=False,
                )

    def test_follow_stops_when_run_reaches_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            run_dir = _make_run(repo_root, status=RunStatus.RUNNING)
            _append_event(run_dir, code="RUN", message="started")

            done = threading.Event()

            def finalize() -> None:
                time.sleep(0.2)
                _append_event(run_dir, code="DONE", message="finished")
                write_run_state(
                    run_dir=run_dir,
                    state=RunState(
                        status=RunStatus.DONE,
                        current_agent_key="writer",
                        current_agent_slug="writer",
                        turn_index=1,
                        updated_at="2026-04-17T12:00:10Z",
                    ),
                )
                done.set()

            out = io.StringIO()
            writer = threading.Thread(target=finalize)
            writer.start()
            try:
                printed = watch_run(
                    repo_root=repo_root,
                    run_id="DMO-1",
                    stream=out,
                    follow=True,
                    poll_interval_seconds=0.05,
                )
            finally:
                writer.join(timeout=5.0)

            self.assertTrue(done.is_set())
            self.assertGreaterEqual(printed, 2)
            self.assertIn("RUN ", out.getvalue())
            self.assertIn("DONE", out.getvalue())


if __name__ == "__main__":
    unittest.main()
