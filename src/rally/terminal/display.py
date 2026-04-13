from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import io
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from rally.services.run_events import EventConsumer, RunEvent, should_render_event


@dataclass(frozen=True)
class DisplayContext:
    run_id: str
    flow_name: str
    flow_code: str
    adapter_name: str
    model_name: str | None
    reasoning_effort: str | None
    start_agent_key: str
    agent_count: int


def build_terminal_display(*, stream: TextIO, context: DisplayContext) -> EventConsumer:
    if _is_tty(stream):
        return RichStreamDisplay(stream=stream, context=context)
    return PlainStreamDisplay(stream=stream, context=context)


class PlainStreamDisplay:
    def __init__(self, *, stream: TextIO, context: DisplayContext) -> None:
        self._stream = stream
        self._stream.write(_render_plain_header(context))
        self._stream.write("\n")
        self._stream.flush()

    def emit(self, event: RunEvent) -> None:
        if not should_render_event(event):
            return
        from rally.services.run_events import render_plain_event_line

        self._stream.write(render_plain_event_line(event))
        self._stream.write("\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.flush()


class RichStreamDisplay:
    def __init__(self, *, stream: TextIO, context: DisplayContext) -> None:
        self._console = Console(file=stream, force_terminal=True, soft_wrap=True)
        self._console.print(
            Panel.fit(
                _render_rich_header(context),
                title="Rally Live",
                border_style="cyan",
            )
        )

    def emit(self, event: RunEvent) -> None:
        if not should_render_event(event):
            return
        self._console.print(_render_event_text(event))

    def close(self) -> None:
        self._console.print(Rule(style="dim"))


def _render_event_text(event: RunEvent) -> Text:
    timestamp = Text(f"{_short_time(event.ts):<8}", style="dim")
    timestamp.append("  ")

    agent_label = event.agent_key or event.agent_slug or "rally"
    agent = Text(f"{agent_label:<20}", style=_agent_style(event))
    agent.append("  ")

    code = Text(f"{event.code:<9}", style=_code_style(event))
    code.append("  ")

    message = Text(" ".join(event.message.splitlines()) if event.message.strip() else "-", style=_message_style(event))

    line = Text()
    line.append(timestamp)
    line.append(agent)
    line.append(code)
    line.append(message)
    return line


def _render_plain_header(context: DisplayContext) -> str:
    return (
        f"Rally {context.run_id}  {context.flow_name} ({context.flow_code})  "
        f"model={_display_value(context.model_name)}  "
        f"thinking={_display_value(context.reasoning_effort)}  "
        f"adapter={context.adapter_name}  "
        f"start={context.start_agent_key}  "
        f"agents={context.agent_count}"
    )


def _render_rich_header(context: DisplayContext) -> str:
    return (
        f"[bold cyan]{context.run_id}[/bold cyan]  "
        f"[bold]{context.flow_name}[/bold]\n"
        f"[dim]Flow code {context.flow_code}[/dim]\n"
        f"[dim]Model {_display_value(context.model_name)} | "
        f"Thinking {_display_value(context.reasoning_effort)} | "
        f"Adapter {context.adapter_name}[/dim]\n"
        f"[dim]Start {context.start_agent_key} | Agents {context.agent_count}[/dim]"
    )


def _display_value(raw_value: str | None) -> str:
    if raw_value is None or not raw_value.strip():
        return "adapter default"
    return raw_value.strip()


def _agent_style(event: RunEvent) -> str:
    if event.agent_key or event.agent_slug:
        return "bold bright_white on blue"
    return "bold cyan"


def _code_style(event: RunEvent) -> str:
    if event.level == "error":
        return "bold red"
    if event.level == "warning":
        return "bold bright_yellow"
    return {
        "assistant": "bold white",
        "lifecycle": "bold cyan",
        "reasoning": "bold bright_black",
        "status": "bold green",
        "tool": "bold yellow",
    }.get(event.kind, "bold white")


def _message_style(event: RunEvent) -> str:
    if event.level == "error":
        return "red"
    if event.level == "warning":
        return "bright_yellow"
    return {
        "assistant": "white",
        "lifecycle": "cyan",
        "reasoning": "bright_black",
        "status": "green",
        "tool": "yellow",
    }.get(event.kind, "white")


def _is_tty(stream: TextIO) -> bool:
    if type(stream) is io.StringIO:
        return False
    isatty = getattr(stream, "isatty", None)
    if callable(isatty):
        try:
            return bool(isatty())
        except OSError:
            return False
    return False


def _short_time(raw_value: str) -> str:
    if raw_value.endswith("Z"):
        raw_value = f"{raw_value[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw_value).astimezone(UTC).strftime("%H:%M:%S")
    except ValueError:
        return raw_value
