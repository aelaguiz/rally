from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import io
from typing import Mapping
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from rally.services.run_events import EventConsumer, RunEvent, should_render_event


@dataclass(frozen=True)
class AgentDisplayIdentity:
    key: str
    slug: str


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
    agent_identities: tuple[AgentDisplayIdentity, ...]


_DEFAULT_AGENT_STYLE = "bold bright_white on blue"
_AGENT_BACKGROUND_PALETTE = (
    "#005f87",
    "#5f005f",
    "#005f5f",
    "#5f0000",
    "#3f5f00",
    "#5f3f00",
)
_TIMESTAMP_WIDTH = 8
_AGENT_WIDTH = 20
_CODE_WIDTH = 9


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
        self._agent_styles = _build_agent_style_lookup(context.agent_identities)
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
        self._console.print(_render_event_text(event, agent_styles=self._agent_styles))

    def close(self) -> None:
        self._console.print(Rule(style="dim"))


def _render_event_text(event: RunEvent, *, agent_styles: Mapping[str, str]) -> Text:
    line = Text()
    line.append(_render_event_main_row(event, agent_styles=agent_styles))
    for detail_line in _detail_lines(event):
        line.append("\n")
        line.append(_render_event_detail_row(detail_line, event=event))
    return line


def _render_event_main_row(event: RunEvent, *, agent_styles: Mapping[str, str]) -> Text:
    line = Text()
    line.append(Text(f"{_short_time(event.ts):<{_TIMESTAMP_WIDTH}}", style="dim"))
    line.append("  ")

    agent_label = event.agent_key or event.agent_slug or "rally"
    line.append(
        Text(
            f"{agent_label:<{_AGENT_WIDTH}}",
            style=_agent_style(event, agent_styles=agent_styles),
        )
    )
    line.append("  ")
    line.append(Text(f"{event.code:<{_CODE_WIDTH}}", style=_code_style(event)))
    line.append("  ")
    message = " ".join(event.message.splitlines()) if event.message.strip() else "-"
    line.append(Text(message, style=_message_style(event)))
    return line


def _render_event_detail_row(detail_line: str, *, event: RunEvent) -> Text:
    line = Text()
    line.append(Text(" " * _TIMESTAMP_WIDTH, style="dim"))
    line.append("  ")
    line.append(Text(" " * _AGENT_WIDTH))
    line.append("  ")
    line.append(Text(" " * _CODE_WIDTH))
    line.append("  ")
    line.append(Text("└ ", style=_detail_style(event)))
    line.append(Text(detail_line, style=_detail_style(event)))
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


def _build_agent_style_lookup(agent_identities: tuple[AgentDisplayIdentity, ...]) -> dict[str, str]:
    style_lookup: dict[str, str] = {}
    for index, identity in enumerate(agent_identities):
        background = _AGENT_BACKGROUND_PALETTE[index % len(_AGENT_BACKGROUND_PALETTE)]
        style = f"bold bright_white on {background}"
        style_lookup[identity.key] = style
        style_lookup[identity.slug] = style
    return style_lookup


def _agent_style(event: RunEvent, *, agent_styles: Mapping[str, str]) -> str:
    if event.agent_key or event.agent_slug:
        for agent_name in (event.agent_key, event.agent_slug):
            if agent_name is None:
                continue
            style = agent_styles.get(agent_name)
            if style is not None:
                return style
        return _DEFAULT_AGENT_STYLE
    return "bold cyan"


def _detail_lines(event: RunEvent) -> tuple[str, ...]:
    raw_lines = event.data.get("detail_lines")
    if not isinstance(raw_lines, list):
        return ()
    detail_lines = [str(line).strip() for line in raw_lines if str(line).strip()]
    return tuple(detail_lines)


def _trace_class(event: RunEvent) -> str | None:
    raw_value = event.data.get("trace_class")
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()
    return None


def _is_memory_event(event: RunEvent) -> bool:
    return _trace_class(event) == "memory" or event.kind == "memory"


def _code_style(event: RunEvent) -> str:
    if event.level == "error":
        return "bold red"
    if event.level == "warning":
        return "bold bright_yellow"
    if _is_memory_event(event):
        return "bold #00d7af"
    trace_class = _trace_class(event)
    if trace_class == "thinking":
        return "bold magenta"
    if trace_class == "tool":
        return "bold bright_blue"
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
    if _is_memory_event(event):
        return "#5fd7d7"
    trace_class = _trace_class(event)
    if trace_class == "thinking":
        return "magenta"
    if trace_class == "tool":
        return "bright_blue"
    return {
        "assistant": "white",
        "lifecycle": "cyan",
        "reasoning": "bright_black",
        "status": "green",
        "tool": "yellow",
    }.get(event.kind, "white")


def _detail_style(event: RunEvent) -> str:
    if event.level == "error":
        return "red"
    if event.level == "warning":
        return "bright_yellow"
    if _is_memory_event(event):
        return "dim #5fd7d7"
    trace_class = _trace_class(event)
    if trace_class == "thinking":
        return "dim magenta"
    if trace_class == "tool":
        return "dim bright_blue"
    return "dim white"


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
