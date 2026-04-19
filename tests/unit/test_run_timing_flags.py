from __future__ import annotations

import unittest

from rally.domain.timing import AgentTiming, RunTiming, TurnTiming, TurnTokens
from rally.services.run_timing_flags import evaluate_flags


def _call(
    *,
    agent_slug: str = "a",
    tool_name: str = "Bash",
    digest: str | None = None,
    is_error: bool = False,
    turn_index: int = 1,
    dur_ms: int = 500,
    end: float = 1.0,
) -> dict:
    return {
        "agent_slug": agent_slug,
        "tool_name": tool_name,
        "input_digest": digest,
        "is_error": is_error,
        "turn_index": turn_index,
        "dur_ms": dur_ms,
        "end": end,
    }


def _empty_timing(*, active_ms: int = 0, wall_ms: int = 0) -> RunTiming:
    return RunTiming(
        run_id="TEST-01",
        flow_code="TST",
        run_status="done",
        last_turn_index=1,
        wall_ms=wall_ms,
        active_ms=active_ms,
        idle_ms=max(wall_ms - active_ms, 0),
        setup_ms=0,
        tokens=TurnTokens(),
    )


class ToolErrorRateTests(unittest.TestCase):
    def test_fires_on_high_error_rate(self) -> None:
        calls = [_call(is_error=True), _call(is_error=True), _call(), _call()]
        flags = evaluate_flags(_empty_timing(), calls)
        codes = {f.code for f in flags}
        self.assertIn("tool_error_rate", codes)

    def test_quiet_when_rate_below_threshold(self) -> None:
        calls = [_call(is_error=True)] + [_call() for _ in range(10)]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("tool_error_rate", {f.code for f in flags})

    def test_quiet_when_fewer_than_three_calls(self) -> None:
        calls = [_call(is_error=True), _call(is_error=True)]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("tool_error_rate", {f.code for f in flags})


class CommandAlwaysFailsTests(unittest.TestCase):
    def test_fires_when_every_call_fails(self) -> None:
        calls = [
            _call(digest="python bad.py", is_error=True),
            _call(digest="python bad.py", is_error=True),
        ]
        flags = evaluate_flags(_empty_timing(), calls)
        codes = {f.code for f in flags}
        self.assertIn("command_always_fails", codes)

    def test_quiet_when_one_call_succeeds(self) -> None:
        calls = [
            _call(digest="git status", is_error=True),
            _call(digest="git status", is_error=False),
        ]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("command_always_fails", {f.code for f in flags})

    def test_quiet_without_digest(self) -> None:
        calls = [_call(is_error=True), _call(is_error=True)]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("command_always_fails", {f.code for f in flags})


class RetryGroupTests(unittest.TestCase):
    def test_fires_when_same_digest_repeats_in_turn(self) -> None:
        calls = [
            _call(digest="pytest -k foo", turn_index=2),
            _call(digest="pytest -k foo", turn_index=2),
        ]
        flags = evaluate_flags(_empty_timing(), calls)
        codes = {f.code for f in flags}
        self.assertIn("retry_group", codes)

    def test_does_not_fire_across_turns(self) -> None:
        calls = [
            _call(digest="pytest", turn_index=1),
            _call(digest="pytest", turn_index=2),
        ]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("retry_group", {f.code for f in flags})


class SingleCallHotTests(unittest.TestCase):
    def test_fires_for_calls_longer_than_sixty_seconds(self) -> None:
        calls = [_call(dur_ms=61_000)]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertIn("single_call_hot", {f.code for f in flags})

    def test_quiet_for_fast_calls(self) -> None:
        calls = [_call(dur_ms=5_000)]
        flags = evaluate_flags(_empty_timing(), calls)
        self.assertNotIn("single_call_hot", {f.code for f in flags})


class ModelSpinTests(unittest.TestCase):
    def test_fires_when_turn_has_no_tools_and_long_wall(self) -> None:
        turn = TurnTiming(
            turn_index=1,
            agent_key="k",
            agent_slug="a",
            kind="handoff",
            started_at="",
            ended_at="",
            wall_ms=150_000,
            tool_ms=0,
            model_ms=150_000,
            tools_called=0,
            errors=0,
            tokens=TurnTokens(),
        )
        timing = RunTiming(
            run_id="T",
            flow_code="T",
            run_status="running",
            last_turn_index=1,
            wall_ms=150_000,
            active_ms=150_000,
            idle_ms=0,
            setup_ms=0,
            tokens=TurnTokens(),
            turns=[turn],
        )
        flags = evaluate_flags(timing, [])
        self.assertIn("model_spin", {f.code for f in flags})


class HighIdleTests(unittest.TestCase):
    def test_fires_when_wall_is_much_greater_than_active(self) -> None:
        flags = evaluate_flags(_empty_timing(active_ms=10_000, wall_ms=60_000), [])
        self.assertIn("high_idle", {f.code for f in flags})

    def test_suppressed_in_step_mode(self) -> None:
        flags = evaluate_flags(
            _empty_timing(active_ms=10_000, wall_ms=60_000),
            [],
            step_mode=True,
        )
        self.assertNotIn("high_idle", {f.code for f in flags})

    def test_quiet_when_wall_matches_active(self) -> None:
        flags = evaluate_flags(_empty_timing(active_ms=10_000, wall_ms=12_000), [])
        self.assertNotIn("high_idle", {f.code for f in flags})


class SortOrderTests(unittest.TestCase):
    def test_errors_sort_before_warnings_before_info(self) -> None:
        calls = [
            _call(digest="always_bad.py", is_error=True),
            _call(digest="always_bad.py", is_error=True),
            _call(dur_ms=61_000),
            _call(digest="retry.py", turn_index=4),
            _call(digest="retry.py", turn_index=4),
        ]
        flags = evaluate_flags(_empty_timing(), calls)
        severities = [f.severity for f in flags]
        self.assertEqual(
            severities,
            sorted(severities, key=lambda s: {"error": 0, "warning": 1, "info": 2}.get(s, 99)),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
