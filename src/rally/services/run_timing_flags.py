"""Anomaly flag rules for run timing.

Pure functions. Each rule inspects a `RunTiming` (and the raw tool-call
records that produced it) and returns zero or more `TimingFlag`s. No I/O.

Rules shipped:

- `tool_error_rate` — any `(agent, tool)` with ≥3 calls and >10% error rate
- `command_always_fails` — any `input_digest` with ≥2 calls and 100% error
- `retry_group` — same `(turn, tool, input_digest)` appearing ≥2× in one turn
- `single_call_hot` — any tool call >60s
- `model_spin` — any turn with 0 tool calls and >120s active
- `high_idle` — wall/active >3× and the run is not step-paused
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from rally.domain.timing import RunTiming, TimingFlag


def evaluate_flags(
    timing: RunTiming,
    tool_calls: Iterable[dict],
    *,
    step_mode: bool = False,
) -> list[TimingFlag]:
    """Run every rule and return the union of flags, sorted by severity."""
    calls = [tc for tc in tool_calls if tc.get("end") is not None]
    flags: list[TimingFlag] = []
    flags.extend(_tool_error_rate(calls))
    flags.extend(_command_always_fails(calls))
    flags.extend(_retry_group(calls))
    flags.extend(_single_call_hot(calls))
    flags.extend(_model_spin(timing))
    flags.extend(_high_idle(timing, step_mode=step_mode))
    order = {"error": 0, "warning": 1, "info": 2}
    flags.sort(key=lambda f: order.get(f.severity, 99))
    return flags


def _tool_error_rate(calls: list[dict]) -> list[TimingFlag]:
    groups: dict[tuple[str | None, str], dict] = defaultdict(
        lambda: {"count": 0, "err": 0}
    )
    for tc in calls:
        key = (tc.get("agent_slug"), tc.get("tool_name") or "?")
        groups[key]["count"] += 1
        if tc.get("is_error"):
            groups[key]["err"] += 1
    out: list[TimingFlag] = []
    for (agent_slug, tool_name), slot in groups.items():
        if slot["count"] < 3:
            continue
        rate = slot["err"] / slot["count"]
        if rate <= 0.10:
            continue
        out.append(
            TimingFlag(
                code="tool_error_rate",
                severity="warning",
                message=(
                    f"{agent_slug or '?'} {tool_name} error rate "
                    f"{int(rate * 100)}% ({slot['err']}/{slot['count']})"
                ),
                evidence={
                    "agent_slug": agent_slug,
                    "tool_name": tool_name,
                    "count": slot["count"],
                    "error_count": slot["err"],
                    "error_rate": rate,
                },
            )
        )
    return out


def _command_always_fails(calls: list[dict]) -> list[TimingFlag]:
    groups: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "err": 0, "agent_slug": None}
    )
    for tc in calls:
        digest = tc.get("input_digest")
        if not digest:
            continue
        key = (tc.get("tool_name") or "?", digest)
        groups[key]["count"] += 1
        groups[key]["agent_slug"] = tc.get("agent_slug")
        if tc.get("is_error"):
            groups[key]["err"] += 1
    out: list[TimingFlag] = []
    for (tool_name, digest), slot in groups.items():
        if slot["count"] < 2 or slot["err"] != slot["count"]:
            continue
        out.append(
            TimingFlag(
                code="command_always_fails",
                severity="error",
                message=f"`{digest}` {slot['count']}/{slot['count']} calls failed",
                evidence={
                    "tool_name": tool_name,
                    "input_digest": digest,
                    "count": slot["count"],
                    "agent_slug": slot["agent_slug"],
                },
            )
        )
    return out


def _retry_group(calls: list[dict]) -> list[TimingFlag]:
    groups: dict[tuple[int, str, str], int] = defaultdict(int)
    for tc in calls:
        digest = tc.get("input_digest")
        if not digest:
            continue
        key = (int(tc.get("turn_index") or 0), tc.get("tool_name") or "?", digest)
        groups[key] += 1
    out: list[TimingFlag] = []
    for (turn_index, tool_name, digest), count in groups.items():
        if count < 2:
            continue
        out.append(
            TimingFlag(
                code="retry_group",
                severity="info",
                message=(
                    f"turn {turn_index}: `{digest}` fired {count}× — possible retry"
                ),
                evidence={
                    "turn_index": turn_index,
                    "tool_name": tool_name,
                    "input_digest": digest,
                    "count": count,
                },
            )
        )
    return out


def _single_call_hot(calls: list[dict]) -> list[TimingFlag]:
    out: list[TimingFlag] = []
    for tc in calls:
        dur_ms = int(tc.get("dur_ms") or 0)
        if dur_ms <= 60_000:
            continue
        digest = tc.get("input_digest") or ""
        out.append(
            TimingFlag(
                code="single_call_hot",
                severity="warning",
                message=(
                    f"{tc.get('tool_name') or '?'} took {dur_ms // 1000}s"
                    + (f": `{digest}`" if digest else "")
                ),
                evidence={
                    "tool_name": tc.get("tool_name"),
                    "agent_slug": tc.get("agent_slug"),
                    "turn_index": tc.get("turn_index"),
                    "dur_ms": dur_ms,
                    "input_digest": digest or None,
                },
            )
        )
    return out


def _model_spin(timing: RunTiming) -> list[TimingFlag]:
    out: list[TimingFlag] = []
    for turn in timing.turns:
        if turn.tools_called != 0:
            continue
        if turn.wall_ms <= 120_000:
            continue
        out.append(
            TimingFlag(
                code="model_spin",
                severity="warning",
                message=(
                    f"turn {turn.turn_index} ({turn.agent_slug or '?'}) ran "
                    f"{turn.wall_ms // 1000}s with 0 tool calls"
                ),
                evidence={
                    "turn_index": turn.turn_index,
                    "agent_slug": turn.agent_slug,
                    "wall_ms": turn.wall_ms,
                },
            )
        )
    return out


def _high_idle(timing: RunTiming, *, step_mode: bool) -> list[TimingFlag]:
    if step_mode:
        return []
    active = timing.active_ms
    wall = timing.wall_ms
    if active <= 0 or wall <= 0:
        return []
    ratio = wall / active
    if ratio <= 3.0:
        return []
    return [
        TimingFlag(
            code="high_idle",
            severity="info",
            message=f"wall/active ratio {ratio:.1f}× — run was mostly idle",
            evidence={
                "wall_ms": wall,
                "active_ms": active,
                "idle_ms": timing.idle_ms,
                "ratio": ratio,
            },
        )
    ]
