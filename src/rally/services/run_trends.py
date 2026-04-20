"""Longitudinal trend reporting over `runs/timings.ndjson`.

Every completed run appends one line to `runs/timings.ndjson`. This module
reads that file, optionally filters by flow, and prints p50 / p90 / mean
summaries plus a short recent-run table. Pure reader — never writes.

The file may not exist yet (no run has finished in this workspace). That
case renders a friendly "no completed runs" message and returns 0 so this
command can be wired into CI without a failure.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RunTrendsResult:
    message: str


def show_run_trends(
    *,
    repo_root: Path,
    flow_code: str | None = None,
    limit: int | None = 20,
) -> RunTrendsResult:
    """Render the `rally runs time` report for the workspace."""
    path = repo_root / "runs" / "timings.ndjson"
    rows = list(_load_rows(path))
    if flow_code is not None:
        needle = flow_code.upper()
        rows = [r for r in rows if (r.get("flow_code") or "").upper() == needle]
    rows.sort(key=lambda r: str(r.get("ts") or ""))
    if not rows:
        return RunTrendsResult(
            message=_render_empty(path=path, flow_code=flow_code),
        )

    tail = rows if (limit is None or limit <= 0) else rows[-limit:]
    return RunTrendsResult(
        message=_render_report(
            path=path,
            flow_code=flow_code,
            rows=tail,
            total_available=len(rows),
        )
    )


def _load_rows(path: Path) -> Iterable[dict]:
    if not path.is_file():
        return []
    results: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                results.append(payload)
    return results


def _render_empty(*, path: Path, flow_code: str | None) -> str:
    if not path.is_file():
        return (
            "No completed Rally runs yet.\n"
            f"Expected `{path}` to exist once a run reaches `done`.\n"
            "Next: run a flow with `rally run <flow>`."
        )
    scope = f" for flow `{flow_code.upper()}`" if flow_code else ""
    return f"No completed Rally runs{scope} in `{path}`."


def _render_report(
    *,
    path: Path,
    flow_code: str | None,
    rows: list[dict],
    total_available: int,
) -> str:
    lines: list[str] = []
    scope = f" (flow `{flow_code.upper()}`)" if flow_code else ""
    shown = len(rows)
    if shown < total_available:
        header = f"Rally run trends{scope} — showing last {shown} of {total_available} completed runs"
    else:
        header = f"Rally run trends{scope} — {shown} completed {'run' if shown == 1 else 'runs'}"
    lines.append(header)
    lines.append(f"Source: `{path}`")
    lines.append("")
    lines.append("Recent runs:")
    for row in reversed(rows):
        lines.append(f"  {_format_row_line(row)}")
    lines.append("")
    lines.extend(_render_stats(rows))
    return "\n".join(lines)


def _format_row_line(row: dict) -> str:
    run_id = str(row.get("run_id") or "?")
    status = str(row.get("run_status") or "?")
    wall = _fmt_duration(int(row.get("wall_ms") or 0))
    active = _fmt_duration(int(row.get("active_ms") or 0))
    tools = int(row.get("tools_called") or 0)
    errors = int(row.get("errors") or 0)
    tokens = row.get("tokens") or {}
    cached = _fmt_count(int(tokens.get("cache_read_input_tokens") or 0))
    out_tok = _fmt_count(int(tokens.get("output_tokens") or 0))
    ts = str(row.get("ts") or "")
    ts_short = ts[:10] if len(ts) >= 10 else ts
    return (
        f"{run_id:<10} {status:<9} {wall:>7} wall · {active:>7} active · "
        f"{tools:>4} tools · {errors:>3} err · {out_tok:>6} out · {cached:>6} cached"
        + (f"  ({ts_short})" if ts_short else "")
    )


def _render_stats(rows: Sequence[dict]) -> list[str]:
    wall = [int(r.get("wall_ms") or 0) for r in rows]
    active = [int(r.get("active_ms") or 0) for r in rows]
    errors = [int(r.get("errors") or 0) for r in rows]
    tools = [int(r.get("tools_called") or 0) for r in rows]
    cached = [int((r.get("tokens") or {}).get("cache_read_input_tokens") or 0) for r in rows]
    output_tokens = [int((r.get("tokens") or {}).get("output_tokens") or 0) for r in rows]

    out: list[str] = ["Stats:"]
    out.append(_stat_line_duration("wall    ", wall))
    out.append(_stat_line_duration("active  ", active))
    out.append(_stat_line_count("errors  ", errors))
    out.append(_stat_line_count("tools   ", tools))
    out.append(_stat_line_count_bytes("cached  ", cached, formatter=_fmt_count))
    out.append(_stat_line_count_bytes("output  ", output_tokens, formatter=_fmt_count))
    return out


def _stat_line_duration(label: str, values: Sequence[int]) -> str:
    p50, p90, mean = _percentiles(values)
    return (
        f"  {label}  p50 {_fmt_duration(p50):>7} · p90 {_fmt_duration(p90):>7} · "
        f"mean {_fmt_duration(int(round(mean))):>7}"
    )


def _stat_line_count(label: str, values: Sequence[int]) -> str:
    p50, p90, mean = _percentiles(values)
    return f"  {label}  p50 {p50:>6} · p90 {p90:>6} · mean {mean:>6.1f}"


def _stat_line_count_bytes(
    label: str, values: Sequence[int], *, formatter
) -> str:
    p50, p90, mean = _percentiles(values)
    return (
        f"  {label}  p50 {formatter(p50):>7} · p90 {formatter(p90):>7} · "
        f"mean {formatter(int(round(mean))):>7}"
    )


def _percentiles(values: Sequence[int]) -> tuple[int, int, float]:
    if not values:
        return 0, 0, 0.0
    sorted_values = sorted(values)
    p50 = _percentile(sorted_values, 0.50)
    p90 = _percentile(sorted_values, 0.90)
    mean = sum(values) / len(values)
    return p50, p90, mean


def _percentile(sorted_values: Sequence[int], q: float) -> int:
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return int(sorted_values[0])
    index = q * (len(sorted_values) - 1)
    lo = int(index)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = index - lo
    return int(round(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac))


def _fmt_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s" if seconds < 10 else f"{int(round(seconds))}s"
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def _fmt_count(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        k = n / 1000
        return f"{k:.1f}k" if k < 10 else f"{int(round(k))}k"
    m = n / 1_000_000
    return f"{m:.2f}M" if m < 10 else f"{m:.1f}M"
