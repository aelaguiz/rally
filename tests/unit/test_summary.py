from __future__ import annotations

import unittest

from rally.domain.timing import (
    AgentTiming,
    CommandRollup,
    RunTiming,
    TimingFlag,
    ToolCallRollup,
    TurnTiming,
    TurnTokens,
)
from rally.terminal.summary import format_summary


def _mk_timing(turns: list[TurnTiming], *, status: str = "running", run_id: str = "TEST-01") -> RunTiming:
    per_agent: dict[str, dict] = {}
    for turn in turns:
        slot = per_agent.setdefault(
            turn.agent_slug or "?",
            {"turns": 0, "tools_called": 0, "errors": 0, "wall_ms": 0, "tool_ms": 0, "model_ms": 0, "tokens": TurnTokens()},
        )
        slot["turns"] += 1
        slot["tools_called"] += turn.tools_called
        slot["errors"] += turn.errors
        slot["wall_ms"] += turn.wall_ms
        slot["tool_ms"] += turn.tool_ms
        slot["model_ms"] += turn.model_ms
    per_agent_list = [
        AgentTiming(
            agent_slug=slug,
            agent_key=None,
            turns=slot["turns"],
            wall_ms=slot["wall_ms"],
            tool_ms=slot["tool_ms"],
            model_ms=slot["model_ms"],
            tools_called=slot["tools_called"],
            errors=slot["errors"],
            tokens=slot["tokens"],
        )
        for slug, slot in per_agent.items()
    ]
    tokens = TurnTokens()
    for t in turns:
        tokens = TurnTokens(
            input_tokens=tokens.input_tokens + t.tokens.input_tokens,
            output_tokens=tokens.output_tokens + t.tokens.output_tokens,
            cache_read_input_tokens=tokens.cache_read_input_tokens + t.tokens.cache_read_input_tokens,
            cache_creation_input_tokens=tokens.cache_creation_input_tokens + t.tokens.cache_creation_input_tokens,
        )
    wall_ms = sum(t.wall_ms for t in turns)
    return RunTiming(
        run_id=run_id,
        flow_code="TST",
        run_status=status,
        last_turn_index=turns[-1].turn_index if turns else 0,
        wall_ms=wall_ms,
        active_ms=wall_ms,
        idle_ms=0,
        setup_ms=0,
        tokens=tokens,
        turns=turns,
        per_agent=per_agent_list,
        top_tools=[],
        top_commands=[],
        flags=[],
    )


class FormatSummaryTests(unittest.TestCase):
    def test_handoff_header_shows_transition(self) -> None:
        turn1 = TurnTiming(
            turn_index=1, agent_key="a1", agent_slug="scope", kind="handoff",
            started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:03:09Z",
            wall_ms=189_000, tool_ms=2_000, model_ms=187_000,
            tools_called=18, errors=0,
            tokens=TurnTokens(output_tokens=8886, cache_read_input_tokens=641_000),
            hot_tools=[ToolCallRollup("Bash", 18, 2000, 0)],
            hot_commands=[],
        )
        turn2 = TurnTiming(
            turn_index=2, agent_key="a2", agent_slug="build", kind="handoff",
            started_at="2026-04-19T12:03:10Z", ended_at="2026-04-19T12:03:20Z",
            wall_ms=10_000, tool_ms=0, model_ms=10_000, tools_called=0, errors=0,
            tokens=TurnTokens(), hot_tools=[], hot_commands=[],
        )
        timing = _mk_timing([turn1, turn2])
        out = format_summary(timing, turn=turn1, style="plain")
        self.assertIn("TST · turn 1 complete · scope → build", out)
        self.assertIn("this turn", out)
        self.assertIn("cumulative", out)
        self.assertIn("artifacts", out)
        self.assertIn("Bash", out)

    def test_done_header(self) -> None:
        turn = TurnTiming(
            turn_index=1, agent_key="a", agent_slug="scope", kind="done",
            started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:00:05Z",
            wall_ms=5000, tool_ms=1000, model_ms=4000,
            tools_called=2, errors=0, tokens=TurnTokens(),
            hot_tools=[], hot_commands=[],
        )
        timing = _mk_timing([turn], status="done")
        out = format_summary(timing, turn=turn, style="plain")
        self.assertIn("TST · done", out)

    def test_blocker_header(self) -> None:
        turn = TurnTiming(
            turn_index=1, agent_key=None, agent_slug="a", kind="blocker",
            started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:00:01Z",
            wall_ms=1000, tool_ms=0, model_ms=1000,
            tools_called=0, errors=0, tokens=TurnTokens(),
            hot_tools=[], hot_commands=[],
        )
        timing = _mk_timing([turn], status="blocked")
        out = format_summary(timing, turn=turn, style="plain")
        self.assertIn("TST · blocked", out)

    def test_errors_rendered_with_rate(self) -> None:
        turn = TurnTiming(
            turn_index=1, agent_key=None, agent_slug="a", kind="handoff",
            started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:00:10Z",
            wall_ms=10_000, tool_ms=5_000, model_ms=5_000,
            tools_called=10, errors=2, tokens=TurnTokens(),
            hot_tools=[ToolCallRollup("Bash", 10, 5000, 2)],
            hot_commands=[CommandRollup("git status", "Bash", 3, 1500, 1)],
        )
        timing = _mk_timing([turn])
        out = format_summary(timing, turn=turn, style="plain")
        self.assertIn("2 err", out)
        self.assertIn("20%", out)
        self.assertIn("hot tools", out)
        self.assertIn("hot commands", out)

    def test_flags_block_shown_when_timing_has_flags(self) -> None:
        turn = TurnTiming(
            turn_index=1, agent_key=None, agent_slug="a", kind="handoff",
            started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:00:05Z",
            wall_ms=5000, tool_ms=1000, model_ms=4000,
            tools_called=2, errors=1, tokens=TurnTokens(),
            hot_tools=[], hot_commands=[],
        )
        timing = _mk_timing([turn])
        timing = RunTiming(
            run_id=timing.run_id,
            flow_code=timing.flow_code,
            run_status=timing.run_status,
            last_turn_index=timing.last_turn_index,
            wall_ms=timing.wall_ms,
            active_ms=timing.active_ms,
            idle_ms=timing.idle_ms,
            setup_ms=timing.setup_ms,
            tokens=timing.tokens,
            turns=timing.turns,
            per_agent=timing.per_agent,
            top_tools=timing.top_tools,
            top_commands=timing.top_commands,
            flags=[
                TimingFlag(
                    code="command_always_fails",
                    severity="error",
                    message="`python bad.py` 2/2 calls failed",
                ),
                TimingFlag(
                    code="retry_group",
                    severity="info",
                    message="turn 1: `pytest -k foo` fired 3× — possible retry",
                ),
            ],
        )
        out = format_summary(timing, turn=turn, style="plain")
        self.assertIn("command_always_fails", out)
        self.assertIn("retry_group", out)
        self.assertIn("⚑", out)

    def test_no_turn_renders_only_cumulative(self) -> None:
        timing = _mk_timing([
            TurnTiming(
                turn_index=1, agent_key=None, agent_slug="a", kind="handoff",
                started_at="2026-04-19T12:00:00Z", ended_at="2026-04-19T12:00:02Z",
                wall_ms=2000, tool_ms=0, model_ms=2000, tools_called=0, errors=0,
                tokens=TurnTokens(), hot_tools=[], hot_commands=[],
            )
        ])
        out = format_summary(timing, turn=None, style="plain")
        self.assertIn("cumulative", out)
        self.assertNotIn("this turn", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
