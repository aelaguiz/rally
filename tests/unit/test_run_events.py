from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from rally.domain.memory import MemoryEntry, MemorySaveResult, MemoryScope
from rally.services.run_events import (
    RunEvent,
    RunEventRecorder,
    record_memory_saved,
    record_memory_used,
    render_plain_event_line,
)
from rally.terminal.display import (
    AgentDisplayIdentity,
    DisplayContext,
    _agent_style,
    _build_agent_style_lookup,
    _detail_lines,
    _message_style,
    _render_event_text,
    build_terminal_display,
)


class RunEventTests(unittest.TestCase):
    def test_recorder_writes_whole_run_and_agent_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)
            stream = io.StringIO()
            recorder = RunEventRecorder(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                consumer=build_terminal_display(
                    stream=stream,
                    context=_display_context(),
                ),
            )

            recorder.emit(
                source="rally",
                kind="lifecycle",
                code="RUN",
                message="Created run.",
            )
            recorder.emit(
                source="codex",
                kind="assistant",
                code="ASSIST",
                message="Looking at the parser.",
                agent_key="01_scope_lead",
                agent_slug="scope_lead",
                turn_index=1,
            )
            recorder.close()

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            rendered = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            agent_log = (run_dir / "logs" / "agents" / "scope_lead.jsonl").read_text(encoding="utf-8")

            self.assertIn('"code": "RUN"', events)
            self.assertIn('"code": "ASSIST"', agent_log)
            self.assertIn("Looking at the parser.", rendered)
            self.assertIn("Rally DMO-1", stream.getvalue())
            self.assertIn("model=gpt-5.4", stream.getvalue())
            self.assertIn("thinking=medium", stream.getvalue())
            self.assertIn("adapter=codex", stream.getvalue())
            self.assertIn("start=01_scope_lead", stream.getvalue())
            self.assertIn("agents=4", stream.getvalue())

    def test_render_plain_event_line_is_scan_friendly(self) -> None:
        line = render_plain_event_line(
            RunEvent(
                ts="2026-04-13T19:30:00Z",
                run_id="DMO-1",
                flow_code="DMO",
                source="rally",
                kind="status",
                code="DONE",
                message="Run finished cleanly.",
                level="info",
                data={},
                agent_key="01_scope_lead",
            )
        )

        self.assertIn("19:30:00", line)
        self.assertIn("01_scope_lead", line)
        self.assertIn("DONE", line)

    def test_render_plain_event_line_stays_single_line_when_trace_has_details(self) -> None:
        line = render_plain_event_line(
            RunEvent(
                ts="2026-04-13T19:30:00Z",
                run_id="DMO-1",
                flow_code="DMO",
                source="codex",
                kind="tool",
                code="CMD OK",
                message="rg -n page src",
                level="info",
                data={
                    "trace_class": "tool",
                    "detail_lines": ["exit code 0", "12 matches"],
                },
                agent_key="01_scope_lead",
            )
        )

        self.assertIn("rg -n page src", line)
        self.assertNotIn("exit code 0", line)
        self.assertNotIn("12 matches", line)

    def test_record_memory_used_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_used(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                entry=_memory_entry(run_dir),
                turn_index=2,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory_used"', events)
            self.assertIn('"memory_id": "mem_dmo_scope_lead_focus_the_fix"', events)

    def test_record_memory_saved_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_saved(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                save_result=MemorySaveResult(outcome="updated", entry=_memory_entry(run_dir)),
                turn_index=3,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory_saved"', events)
            self.assertIn('"outcome": "updated"', events)

    def test_build_terminal_display_uses_rich_on_tty_streams(self) -> None:
        stream = _FakeTtyStream()
        display = build_terminal_display(
            stream=stream,
            context=_display_context(),
        )

        display.emit(
            RunEvent(
                ts="2026-04-13T19:30:00Z",
                run_id="DMO-1",
                flow_code="DMO",
                source="rally",
                kind="assistant",
                code="ASSIST",
                message="Printing from the TTY path.",
                level="info",
                data={},
                agent_key="01_scope_lead",
            )
        )
        display.close()

        self.assertIn("Model gpt-5.4", stream.getvalue())
        self.assertIn("Thinking medium", stream.getvalue())
        self.assertIn("Adapter codex", stream.getvalue())
        self.assertIn("Start 01_scope_lead", stream.getvalue())
        self.assertIn("Agents 4", stream.getvalue())
        self.assertIn("Printing from the TTY path.", stream.getvalue())

    def test_plain_display_uses_adapter_defaults_when_model_or_thinking_missing(self) -> None:
        stream = io.StringIO()
        display = build_terminal_display(
            stream=stream,
            context=_display_context(model_name=None, reasoning_effort=None),
        )

        display.close()

        self.assertIn("model=adapter default", stream.getvalue())
        self.assertIn("thinking=adapter default", stream.getvalue())

    def test_agent_style_lookup_assigns_different_colors_by_flow_order(self) -> None:
        styles = _build_agent_style_lookup(_display_context().agent_identities)

        self.assertEqual(styles["01_scope_lead"], "bold bright_white on #005f87")
        self.assertEqual(styles["scope_lead"], "bold bright_white on #005f87")
        self.assertEqual(styles["02_change_engineer"], "bold bright_white on #5f005f")
        self.assertNotEqual(styles["01_scope_lead"], styles["02_change_engineer"])

    def test_agent_style_uses_same_color_for_key_and_slug(self) -> None:
        styles = _build_agent_style_lookup(_display_context().agent_identities)
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="codex",
            kind="assistant",
            code="ASSIST",
            message="Agent event.",
            level="info",
            data={},
            agent_key="03_proof_engineer",
            agent_slug="proof_engineer",
        )

        self.assertEqual(
            _agent_style(event, agent_styles=styles),
            "bold bright_white on #005f5f",
        )
        self.assertEqual(styles["03_proof_engineer"], styles["proof_engineer"])

    def test_agent_style_keeps_cyan_for_non_agent_events(self) -> None:
        styles = _build_agent_style_lookup(_display_context().agent_identities)
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="rally",
            kind="lifecycle",
            code="RUN",
            message="Created run.",
            level="info",
            data={},
        )

        self.assertEqual(_agent_style(event, agent_styles=styles), "bold cyan")

    def test_agent_style_falls_back_to_blue_for_unknown_agent(self) -> None:
        styles = _build_agent_style_lookup(_display_context().agent_identities)
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="codex",
            kind="assistant",
            code="ASSIST",
            message="Unknown agent event.",
            level="info",
            data={},
            agent_key="99_unknown_agent",
        )

        self.assertEqual(
            _agent_style(event, agent_styles=styles),
            "bold bright_white on blue",
        )

    def test_message_style_uses_magenta_for_thinking_traces(self) -> None:
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="codex",
            kind="reasoning",
            code="THINK",
            message="Check the route.",
            level="info",
            data={"trace_class": "thinking"},
            agent_key="01_scope_lead",
        )

        self.assertEqual(_message_style(event), "magenta")

    def test_message_style_uses_bright_blue_for_tool_traces(self) -> None:
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="codex",
            kind="tool",
            code="CMD OK",
            message="rg -n page src",
            level="info",
            data={"trace_class": "tool"},
            agent_key="01_scope_lead",
        )

        self.assertEqual(_message_style(event), "bright_blue")

    def test_rich_render_includes_detail_rows_for_trace_events(self) -> None:
        styles = _build_agent_style_lookup(_display_context().agent_identities)
        event = RunEvent(
            ts="2026-04-13T19:30:00Z",
            run_id="DMO-1",
            flow_code="DMO",
            source="codex",
            kind="tool",
            code="CMD OK",
            message="rg -n page src",
            level="info",
            data={
                "trace_class": "tool",
                "detail_lines": ["exit code 0", "12 matches"],
            },
            agent_key="01_scope_lead",
            agent_slug="scope_lead",
        )

        rendered = _render_event_text(event, agent_styles=styles)

        self.assertEqual(_detail_lines(event), ("exit code 0", "12 matches"))
        self.assertIn("rg -n page src", rendered.plain)
        self.assertIn("└ exit code 0", rendered.plain)
        self.assertIn("└ 12 matches", rendered.plain)


class _FakeTtyStream(io.StringIO):
    def isatty(self) -> bool:
        return True


def _display_context(
    *,
    model_name: str | None = "gpt-5.4",
    reasoning_effort: str | None = "medium",
) -> DisplayContext:
    return DisplayContext(
        run_id="DMO-1",
        flow_name="demo",
        flow_code="DMO",
        adapter_name="codex",
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        start_agent_key="01_scope_lead",
        agent_count=4,
        agent_identities=(
            AgentDisplayIdentity(key="01_scope_lead", slug="scope_lead"),
            AgentDisplayIdentity(key="02_change_engineer", slug="change_engineer"),
            AgentDisplayIdentity(key="03_proof_engineer", slug="proof_engineer"),
            AgentDisplayIdentity(key="04_acceptance_critic", slug="acceptance_critic"),
        ),
    )


def _memory_entry(run_dir: Path) -> MemoryEntry:
    return MemoryEntry(
        memory_id="mem_dmo_scope_lead_focus_the_fix",
        scope=MemoryScope(flow_code="DMO", agent_slug="scope_lead"),
        source_run_id="DMO-1",
        created_at="2026-04-13T20:00:00Z",
        updated_at="2026-04-13T20:05:00Z",
        lesson="Focus the fix before you widen scope.",
        when_this_matters="Use this when the first bug is still not fixed.",
        what_to_do="Fix the concrete bug, then widen only if proof shows a second issue.",
        path=run_dir / "memory.md",
    )


if __name__ == "__main__":
    unittest.main()
