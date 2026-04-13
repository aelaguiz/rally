from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from rally.services.run_events import RunEvent, RunEventRecorder, render_plain_event_line
from rally.terminal.display import DisplayContext, build_terminal_display


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
                    context=DisplayContext(run_id="DMO-1", flow_name="demo", flow_code="DMO"),
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

    def test_build_terminal_display_uses_rich_on_tty_streams(self) -> None:
        stream = _FakeTtyStream()
        display = build_terminal_display(
            stream=stream,
            context=DisplayContext(run_id="DMO-1", flow_name="demo", flow_code="DMO"),
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

        self.assertIn("Printing from the TTY path.", stream.getvalue())


class _FakeTtyStream(io.StringIO):
    def isatty(self) -> bool:
        return True


if __name__ == "__main__":
    unittest.main()
