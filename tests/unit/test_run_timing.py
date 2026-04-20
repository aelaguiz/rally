from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rally.services.run_timing import (
    compute_run_timing,
    update_tool_calls,
    write_run_timing,
)


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_events(run_dir: Path, events: list[dict]) -> None:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )


def _mk_run_dir(root: Path, run_id: str = "TEST-01") -> Path:
    run_dir = root / "runs" / "active" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class ComputeRunTimingTests(unittest.TestCase):
    def test_single_turn_with_one_tool_call(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "run_id": "TEST-01", "flow_code": "TST",
                 "turn_index": 1, "agent_key": "a_key", "agent_slug": "a_slug", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=1)), "code": "TOOL", "run_id": "TEST-01",
                 "turn_index": 1, "agent_slug": "a_slug",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "input_digest": "ls"}},
                {"ts": _ts(t0 + timedelta(seconds=3)), "code": "TOOL OK", "run_id": "TEST-01",
                 "turn_index": 1, "agent_slug": "a_slug",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "is_error": False}},
                {"ts": _ts(t0 + timedelta(seconds=4)), "code": "USAGE", "run_id": "TEST-01",
                 "turn_index": 1, "agent_slug": "a_slug",
                 "data": {"usage": {"input_tokens": 100, "output_tokens": 50}}},
                {"ts": _ts(t0 + timedelta(seconds=5)), "code": "HANDOFF", "run_id": "TEST-01",
                 "turn_index": 1, "agent_slug": "a_slug", "data": {}},
            ]
            _write_events(run_dir, events)

            timing = compute_run_timing(run_dir)

            self.assertEqual(timing.run_id, "TEST-01")
            self.assertEqual(timing.flow_code, "TST")
            self.assertEqual(timing.run_status, "running")
            self.assertEqual(len(timing.turns), 1)
            turn = timing.turns[0]
            self.assertEqual(turn.kind, "handoff")
            self.assertEqual(turn.wall_ms, 5000)
            self.assertEqual(turn.tool_ms, 2000)
            self.assertEqual(turn.model_ms, 3000)
            self.assertEqual(turn.tools_called, 1)
            self.assertEqual(turn.errors, 0)
            self.assertEqual(turn.tokens.input_tokens, 100)
            self.assertEqual(turn.tokens.output_tokens, 50)
            self.assertEqual(len(turn.hot_tools), 1)
            self.assertEqual(turn.hot_tools[0].tool_name, "Bash")
            self.assertEqual(turn.hot_tools[0].count, 1)

    def test_error_tool_counts_and_rate(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1,
                 "agent_slug": "a", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=1)), "code": "TOOL", "turn_index": 1,
                 "agent_slug": "a",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "input_digest": "git status"}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "TOOL OK", "turn_index": 1,
                 "agent_slug": "a",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "is_error": True, "exit_code": 2}},
                {"ts": _ts(t0 + timedelta(seconds=5)), "code": "DONE", "turn_index": 1,
                 "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            self.assertEqual(timing.run_status, "done")
            self.assertEqual(timing.turns[0].errors, 1)
            self.assertEqual(timing.top_tools[0].error_count, 1)

    def test_turn_kinds_map_to_run_status(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        cases = {
            "HANDOFF": "running",
            "DONE": "done",
            "BLOCKED": "blocked",
            "SLEEP": "sleeping",
        }
        for terminal_code, expected_status in cases.items():
            with TemporaryDirectory() as tmp:
                run_dir = _mk_run_dir(Path(tmp), run_id=f"T-{terminal_code}")
                events = [
                    {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a", "data": {}},
                    {"ts": _ts(t0 + timedelta(seconds=1)), "code": terminal_code,
                     "turn_index": 1, "agent_slug": "a", "data": {}},
                ]
                _write_events(run_dir, events)
                timing = compute_run_timing(run_dir)
                self.assertEqual(
                    timing.run_status,
                    expected_status,
                    msg=f"{terminal_code} should yield {expected_status}",
                )

    def test_per_agent_rollup_aggregates_across_turns(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "scope", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "HANDOFF",
                 "turn_index": 1, "agent_slug": "scope", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=3)), "code": "TURN",
                 "turn_index": 2, "agent_slug": "build", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=7)), "code": "DONE",
                 "turn_index": 2, "agent_slug": "build", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            slugs = {a.agent_slug: a for a in timing.per_agent}
            self.assertEqual(set(slugs.keys()), {"scope", "build"})
            self.assertEqual(slugs["scope"].turns, 1)
            self.assertEqual(slugs["build"].turns, 1)

    def test_tool_without_tool_use_id_pairs_by_name_queue(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=1)), "code": "CMD",
                 "turn_index": 1, "agent_slug": "a",
                 "data": {"tool_name": "Bash", "input_digest": "pwd"}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "CMD OK",
                 "turn_index": 1, "agent_slug": "a",
                 "data": {"tool_name": "Bash", "is_error": False}},
                {"ts": _ts(t0 + timedelta(seconds=3)), "code": "HANDOFF",
                 "turn_index": 1, "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            self.assertEqual(timing.turns[0].tools_called, 1)
            self.assertEqual(timing.turns[0].tool_ms, 1000)

    def test_interrupted_turn_is_finalized(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "HEARTBEAT",
                 "turn_index": 1, "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            self.assertEqual(len(timing.turns), 1)
            self.assertEqual(timing.turns[0].kind, "interrupted")


class WriteRunTimingTests(unittest.TestCase):
    def test_write_creates_timing_json_and_turns_log(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a",
                 "run_id": "TEST-01", "flow_code": "TST", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "HANDOFF",
                 "turn_index": 1, "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            write_run_timing(run_dir, timing, final=False)

            self.assertTrue((run_dir / "timing.json").exists())
            self.assertTrue((run_dir / "timing_turns.jsonl").exists())
            self.assertFalse((run_dir.parent.parent / "timings.ndjson").exists())

            data = json.loads((run_dir / "timing.json").read_text())
            self.assertEqual(data["run_id"], "TEST-01")

    def test_write_final_appends_workspace_ndjson(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a",
                 "run_id": "TEST-01", "flow_code": "TST", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "DONE",
                 "turn_index": 1, "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            timing = compute_run_timing(run_dir)
            write_run_timing(run_dir, timing, final=True)

            ndjson_path = run_dir.parent.parent / "timings.ndjson"
            self.assertTrue(ndjson_path.exists())
            line = ndjson_path.read_text().strip().splitlines()[0]
            parsed = json.loads(line)
            self.assertEqual(parsed["run_id"], "TEST-01")
            self.assertEqual(parsed["run_status"], "done")

    def test_update_tool_calls_is_idempotent(self) -> None:
        t0 = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp:
            run_dir = _mk_run_dir(Path(tmp))
            events = [
                {"ts": _ts(t0), "code": "TURN", "turn_index": 1, "agent_slug": "a", "data": {}},
                {"ts": _ts(t0 + timedelta(seconds=1)), "code": "TOOL",
                 "turn_index": 1, "agent_slug": "a",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "input_digest": "ls"}},
                {"ts": _ts(t0 + timedelta(seconds=2)), "code": "TOOL OK",
                 "turn_index": 1, "agent_slug": "a",
                 "data": {"tool_name": "Bash", "tool_use_id": "t1", "is_error": False}},
                {"ts": _ts(t0 + timedelta(seconds=3)), "code": "HANDOFF",
                 "turn_index": 1, "agent_slug": "a", "data": {}},
            ]
            _write_events(run_dir, events)
            update_tool_calls(run_dir, since_turn=0)
            first = (run_dir / "tool_calls.jsonl").read_text()
            update_tool_calls(run_dir, since_turn=0)
            second = (run_dir / "tool_calls.jsonl").read_text()
            self.assertEqual(first, second)
            lines = [ln for ln in first.splitlines() if ln]
            self.assertEqual(len(lines), 1)
            parsed = json.loads(lines[0])
            self.assertEqual(parsed["tool_name"], "Bash")
            self.assertEqual(parsed["dur_ms"], 1000)
            self.assertEqual(parsed["input_digest"], "ls")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
