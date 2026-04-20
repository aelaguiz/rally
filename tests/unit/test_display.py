from __future__ import annotations

import io
import unittest

from rally.services.run_events import RunEvent
from rally.terminal.display import (
    AgentDisplayIdentity,
    DisplayContext,
    PlainStreamDisplay,
    RichStreamDisplay,
    _display_value,
    _is_tty,
    _render_plain_header,
    _short_time,
    _summary_receipt,
    build_terminal_display,
)


def _context(
    *,
    model_name: str | None = "gpt-5.4",
    reasoning_effort: str | None = "medium",
    adapter_name: str = "codex",
    run_id: str = "DMO-1",
    flow_name: str = "demo",
    flow_code: str = "DMO",
    start_agent_key: str = "01_scope_lead",
    agent_count: int = 4,
) -> DisplayContext:
    return DisplayContext(
        run_id=run_id,
        flow_name=flow_name,
        flow_code=flow_code,
        adapter_name=adapter_name,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        start_agent_key=start_agent_key,
        agent_count=agent_count,
        agent_identities=(
            AgentDisplayIdentity(key="01_scope_lead", slug="scope_lead"),
            AgentDisplayIdentity(key="02_change_engineer", slug="change_engineer"),
        ),
    )


def _event(
    *,
    kind: str = "assistant",
    code: str = "ASSIST",
    message: str = "Printing a line.",
    level: str = "info",
    data: dict | None = None,
    agent_key: str | None = "01_scope_lead",
    agent_slug: str | None = "scope_lead",
    ts: str = "2026-04-13T19:30:00Z",
) -> RunEvent:
    return RunEvent(
        ts=ts,
        run_id="DMO-1",
        flow_code="DMO",
        source="rally",
        kind=kind,
        code=code,
        message=message,
        level=level,
        data=dict(data or {}),
        agent_key=agent_key,
        agent_slug=agent_slug,
    )


class DisplayContractTests(unittest.TestCase):
    """Behavior tests for rally.terminal.display — the stdout contract for
    Rally's live run display. Protects two user-visible outcomes:

    1. Plain-stream rendering is scan-friendly and stable across refactors:
       CI log parsers, tail-to-terminal workflows, and the `runs/*/logs/
       rendered.log` file all depend on the exact shape emitted by
       `PlainStreamDisplay` and `_render_plain_header`. A silent layout
       regression (missing field, reordered column, dropped newline around
       the per-handoff SUMMARY receipt) would break every downstream reader
       without raising a visible error.

    2. The TTY vs. non-TTY dispatch stays correct: piping output to a file,
       redirecting to `rendered.log`, or running under CI must take the
       plain branch. If `_is_tty` drifts, users see ANSI escape sequences
       spilling into log files they grep later.
    """

    def test_render_plain_header_emits_fields_in_contract_order(self) -> None:
        rendered = _render_plain_header(_context())

        self.assertEqual(
            rendered,
            "Rally DMO-1  demo (DMO)  model=gpt-5.4  "
            "thinking=medium  adapter=codex  start=01_scope_lead  agents=4",
        )

    def test_display_value_falls_back_when_model_or_thinking_missing(self) -> None:
        for raw in (None, "", "   ", "\t"):
            with self.subTest(raw=raw):
                self.assertEqual(_display_value(raw), "adapter default")

    def test_display_value_strips_whitespace_on_real_values(self) -> None:
        self.assertEqual(_display_value("  gpt-5.4  "), "gpt-5.4")

    def test_render_plain_header_substitutes_adapter_default_for_missing_values(self) -> None:
        rendered = _render_plain_header(
            _context(model_name=None, reasoning_effort="   "),
        )

        self.assertIn("model=adapter default", rendered)
        self.assertIn("thinking=adapter default", rendered)

    def test_summary_receipt_returns_none_for_non_summary_events(self) -> None:
        for event in (
            _event(kind="assistant", code="SUMMARY", data={"receipt": "hi"}),
            _event(kind="summary", code="ASSIST", data={"receipt": "hi"}),
        ):
            with self.subTest(kind=event.kind, code=event.code):
                self.assertIsNone(_summary_receipt(event))

    def test_summary_receipt_returns_none_for_blank_or_missing_receipt(self) -> None:
        for raw in (None, "", "   ", 42):
            with self.subTest(raw=raw):
                event = _event(
                    kind="summary",
                    code="SUMMARY",
                    data={"receipt": raw} if raw is not None else {},
                )
                self.assertIsNone(_summary_receipt(event))

    def test_summary_receipt_rstrips_valid_payload(self) -> None:
        event = _event(
            kind="summary",
            code="SUMMARY",
            data={"receipt": "line one\nline two\n\n"},
        )

        self.assertEqual(_summary_receipt(event), "line one\nline two")

    def test_is_tty_treats_plain_stringio_as_non_tty(self) -> None:
        # StringIO has no isatty hint for downstream consumers; treating it
        # as non-TTY lets unit tests capture output without forcing the Rich
        # branch.
        self.assertFalse(_is_tty(io.StringIO()))

    def test_is_tty_honors_isatty_true_on_fake_tty_stream(self) -> None:
        class _FakeTty(io.StringIO):
            def isatty(self) -> bool:
                return True

        self.assertTrue(_is_tty(_FakeTty()))

    def test_is_tty_returns_false_when_isatty_raises_oserror(self) -> None:
        # Real pipes on closed fds raise OSError from isatty(). The display
        # must degrade to plain rather than crash the run.
        class _AngryStream(io.StringIO):
            def isatty(self) -> bool:
                raise OSError("fd is closed")

        self.assertFalse(_is_tty(_AngryStream()))

    def test_is_tty_returns_false_when_stream_has_no_isatty_method(self) -> None:
        class _NoIsatty:
            def write(self, _value: str) -> int:
                return 0

            def flush(self) -> None:
                pass

        self.assertFalse(_is_tty(_NoIsatty()))

    def test_short_time_parses_utc_suffix(self) -> None:
        self.assertEqual(_short_time("2026-04-13T19:30:00Z"), "19:30:00")

    def test_short_time_returns_raw_on_invalid_input(self) -> None:
        self.assertEqual(_short_time("not a time"), "not a time")


class PlainStreamDisplayTests(unittest.TestCase):
    """Protects the exact bytes that land in `rendered.log` and in any
    terminal where stdout is not a TTY. CI log parsers and human readers
    grep this stream; a silent reshape would not fail any downstream code
    loudly."""

    def test_init_writes_header_with_trailing_newline_and_flushes(self) -> None:
        stream = io.StringIO()

        PlainStreamDisplay(stream=stream, context=_context())

        text = stream.getvalue()
        self.assertTrue(text.startswith("Rally DMO-1  demo (DMO)"))
        self.assertTrue(text.endswith("\n"))

    def test_emit_writes_plain_event_line_with_trailing_newline(self) -> None:
        stream = io.StringIO()
        display = PlainStreamDisplay(stream=stream, context=_context())
        stream.seek(0)
        stream.truncate()

        display.emit(_event(message="Looking at the parser."))

        text = stream.getvalue()
        self.assertIn("19:30:00", text)
        self.assertIn("01_scope_lead", text)
        self.assertIn("ASSIST", text)
        self.assertIn("Looking at the parser.", text)
        self.assertTrue(text.endswith("\n"))

    def test_emit_renders_summary_receipt_surrounded_by_blank_lines(self) -> None:
        stream = io.StringIO()
        display = PlainStreamDisplay(stream=stream, context=_context())
        stream.seek(0)
        stream.truncate()

        display.emit(
            _event(
                kind="summary",
                code="SUMMARY",
                message="ignored",
                data={"receipt": "handoff: change_engineer\nduration: 4.2s"},
            ),
        )

        self.assertEqual(
            stream.getvalue(),
            "\nhandoff: change_engineer\nduration: 4.2s\n\n",
        )

    def test_emit_filters_debug_events_below_warning_level(self) -> None:
        stream = io.StringIO()
        display = PlainStreamDisplay(stream=stream, context=_context())
        stream.seek(0)
        stream.truncate()

        display.emit(
            _event(kind="debug", code="DBG", message="noisy trace", level="info"),
        )

        self.assertEqual(stream.getvalue(), "")

    def test_emit_renders_debug_events_at_warning_or_error_level(self) -> None:
        stream = io.StringIO()
        display = PlainStreamDisplay(stream=stream, context=_context())
        stream.seek(0)
        stream.truncate()

        display.emit(
            _event(
                kind="debug",
                code="DBG",
                message="something noteworthy",
                level="warning",
            ),
        )

        self.assertIn("something noteworthy", stream.getvalue())

    def test_close_flushes_the_stream(self) -> None:
        class _TrackingStream(io.StringIO):
            def __init__(self) -> None:
                super().__init__()
                self.flush_calls = 0

            def flush(self) -> None:
                self.flush_calls += 1
                super().flush()

        stream = _TrackingStream()
        display = PlainStreamDisplay(stream=stream, context=_context())
        init_flushes = stream.flush_calls

        display.close()

        self.assertEqual(stream.flush_calls, init_flushes + 1)


class BuildTerminalDisplayDispatchTests(unittest.TestCase):
    """Guards the non-TTY fallback: pipes, log files, and CI harnesses must
    receive the plain branch. An incorrect dispatch here would flood
    `rendered.log` with ANSI escapes, which users grep later."""

    def test_non_tty_stringio_stream_uses_plain_branch(self) -> None:
        stream = io.StringIO()

        display = build_terminal_display(stream=stream, context=_context())

        self.assertIsInstance(display, PlainStreamDisplay)

    def test_tty_stream_uses_rich_branch(self) -> None:
        class _FakeTty(io.StringIO):
            def isatty(self) -> bool:
                return True

        display = build_terminal_display(stream=_FakeTty(), context=_context())

        self.assertIsInstance(display, RichStreamDisplay)


if __name__ == "__main__":
    unittest.main()
