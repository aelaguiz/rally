"""Render a `RunTiming` snapshot into the per-handoff receipt block.

Pure function. Produces the text shown inline in the event stream at every
terminal turn (handoff, done, blocker, sleep). Two sections: "this turn" is
the just-finished turn; "cumulative" is the whole run so far. Both displays
(`PlainStreamDisplay`, `RichStreamDisplay`) render the same text — style is
reserved for future formatting.
"""
from __future__ import annotations

from typing import Literal

from rally.domain.timing import (
    CommandRollup,
    RunTiming,
    TimingFlag,
    ToolCallRollup,
    TurnTiming,
    TurnTokens,
)


def format_summary(
    timing: RunTiming,
    *,
    turn: TurnTiming | None,
    style: Literal["plain", "rich"] = "plain",
) -> str:
    """Return the multi-line receipt block for one terminal turn event.

    `turn` is the turn that just ended (used for the "this turn" section).
    Pass `None` to render only the cumulative block (e.g. when resuming).
    """
    del style  # Reserved for future rich styling; plain text today.
    lines: list[str] = []
    lines.append(_format_header(timing, turn))
    lines.append("")
    if turn is not None:
        lines.extend(_format_turn_block(turn))
        lines.append("")
    lines.extend(_format_cumulative_block(timing))
    if timing.flags:
        lines.extend(_format_flags_block(timing.flags))
    lines.append("")
    lines.append(_format_artifacts_line(timing))
    return "\n".join(lines)


def _format_flags_block(flags: list[TimingFlag]) -> list[str]:
    out: list[str] = []
    for i, flag in enumerate(flags[:6]):
        mark = {"error": "⚑", "warning": "⚑", "info": "•"}.get(flag.severity, "•")
        label = "flags" if i == 0 else "     "
        out.append(f"            {label} {mark} [{flag.code}] {flag.message}")
    if len(flags) > 6:
        out.append(f"                   (+{len(flags) - 6} more)")
    return out


def _format_header(timing: RunTiming, turn: TurnTiming | None) -> str:
    code = timing.flow_code or timing.run_id or "run"
    if turn is None:
        return f"{code} · {timing.run_status}"
    kind = turn.kind
    if kind == "handoff":
        next_agent = _next_agent_slug(timing, turn)
        lead = f"turn {turn.turn_index} complete"
        if turn.agent_slug and next_agent:
            return f"{code} · {lead} · {turn.agent_slug} → {next_agent}"
        if turn.agent_slug:
            return f"{code} · {lead} · {turn.agent_slug} → ?"
        return f"{code} · {lead}"
    if kind == "done":
        return f"{code} · done"
    if kind == "blocker":
        return f"{code} · blocked"
    if kind == "sleep":
        return f"{code} · sleeping"
    return f"{code} · turn {turn.turn_index} {kind}"


def _next_agent_slug(timing: RunTiming, turn: TurnTiming) -> str | None:
    try:
        index = timing.turns.index(turn)
    except ValueError:
        return None
    for successor in timing.turns[index + 1 :]:
        if successor.agent_slug:
            return successor.agent_slug
    return None


def _format_turn_block(turn: TurnTiming) -> list[str]:
    lines: list[str] = []
    head = (
        f"this turn   {_fmt_duration(turn.wall_ms)}"
        f"  ({_fmt_duration(turn.tool_ms)} tools · {_fmt_duration(turn.model_ms)} model)"
        f"   {turn.tools_called} tools"
    )
    tokens_part = _fmt_tokens_inline(turn.tokens)
    if tokens_part:
        head += f"   {tokens_part}"
    if turn.errors:
        head += f"   {turn.errors} err"
    lines.append(head)
    hot_tools_text = _fmt_hot_tools(turn.hot_tools)
    if hot_tools_text:
        lines.append(f"            hot tools:    {hot_tools_text}")
    hot_commands_text = _fmt_hot_commands(turn.hot_commands)
    if hot_commands_text:
        for i, entry in enumerate(hot_commands_text):
            label = "hot commands:" if i == 0 else "             "
            lines.append(f"            {label} {entry}")
    if not turn.errors and turn.tools_called:
        lines.append("            no errors")
    return lines


def _format_cumulative_block(timing: RunTiming) -> list[str]:
    lines: list[str] = []
    head = (
        f"cumulative  {_fmt_duration(timing.wall_ms)} wall"
        f" · {_fmt_duration(timing.active_ms)} active"
        f" · {_fmt_duration(timing.idle_ms)} idle"
    )
    lines.append(head)
    turns_count = len(timing.turns)
    agents_count = len(timing.per_agent)
    tools_called = sum(a.tools_called for a in timing.per_agent)
    errors = sum(a.errors for a in timing.per_agent)
    parts = [
        f"{turns_count} {_plural('turn', turns_count)}",
        f"{agents_count} {_plural('agent', agents_count)}",
        f"{tools_called} {_plural('tool', tools_called)}",
    ]
    if errors:
        rate = (errors / tools_called * 100) if tools_called else 0
        parts.append(f"{errors} errors ({rate:.1f}%)")
    else:
        parts.append("0 errors")
    tokens_part = _fmt_tokens_inline(timing.tokens)
    if tokens_part:
        parts.append(tokens_part)
    lines.append(f"            {' · '.join(parts)}")
    return lines


def _format_artifacts_line(timing: RunTiming) -> str:
    run_id = timing.run_id or "?"
    return f"artifacts   runs/active/{run_id}/timing.json"


def _fmt_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    seconds_total = ms / 1000
    if seconds_total < 60:
        if seconds_total < 10:
            return f"{seconds_total:.1f}s"
        return f"{int(round(seconds_total))}s"
    total_seconds = int(round(seconds_total))
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m{seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{seconds:02d}s"


def _fmt_tokens_inline(tokens: TurnTokens) -> str:
    parts: list[str] = []
    if tokens.output_tokens:
        parts.append(f"{_fmt_count(tokens.output_tokens)} out")
    cached = tokens.cache_read_input_tokens
    if cached:
        parts.append(f"{_fmt_count(cached)} cached")
    return " · ".join(parts)


def _fmt_count(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        thousands = n / 1000
        if thousands < 10:
            return f"{thousands:.1f}k"
        return f"{int(round(thousands))}k"
    millions = n / 1_000_000
    if millions < 10:
        return f"{millions:.2f}M"
    return f"{millions:.1f}M"


def _fmt_hot_tools(rollups: list[ToolCallRollup]) -> str:
    if not rollups:
        return ""
    entries: list[str] = []
    for r in rollups[:4]:
        entry = f"{r.tool_name} {_fmt_duration(r.total_ms)} × {r.count}"
        if r.error_count:
            pct = int(round(r.error_rate * 100))
            entry += f" ({pct}% err)"
        entries.append(entry)
    return " · ".join(entries)


def _fmt_hot_commands(rollups: list[CommandRollup]) -> list[str]:
    if not rollups:
        return []
    entries: list[str] = []
    for r in rollups[:4]:
        digest = _truncate(r.input_digest, 52)
        parts = [f"{digest}", f"{r.count}×", _fmt_duration(r.total_ms)]
        if r.error_count:
            parts.append(f"{r.error_count} err")
        entries.append("  ".join(parts))
    return entries


def _truncate(text: str, max_len: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def _plural(word: str, n: int) -> str:
    return word if n == 1 else f"{word}s"
