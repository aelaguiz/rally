"""Aggregate `events.jsonl` into per-turn and per-run timing summaries.

`compute_run_timing(run_dir)` reads the event stream, pairs tool-start and
tool-end events by `tool_use_id`, rolls up token totals, and returns a
`RunTiming` snapshot. `write_run_timing` persists the snapshot to
`timing.json` (overwritten) plus incremental artifacts (`timing_turns.jsonl`,
`tool_calls.jsonl`, and at run-end `runs/timings.ndjson`).

All tool-completion events — `TOOL OK` (Claude Code), `CMD OK` / `CMD ERR`
(Codex commands), `MCP OK` / `MCP ERR`, `COLLAB OK` / `COLLAB ERR` — are
treated uniformly because both adapter projections carry `tool_name`,
`tool_use_id`, `is_error`, and `input_digest` after the enrichment landed in
Phase 1.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Iterator

from rally.domain.timing import (
    AgentTiming,
    CommandRollup,
    RunTiming,
    TimingFlag,
    ToolCallRollup,
    TurnTiming,
    TurnTokens,
)

_TOOL_START_CODES = frozenset({"TOOL", "CMD", "MCP", "COLLAB", "SEARCH", "PATCH"})
_TOOL_END_CODES = frozenset(
    {
        "TOOL OK",
        "CMD OK",
        "CMD ERR",
        "CMD NO",
        "MCP OK",
        "MCP ERR",
        "MCP NO",
        "COLLAB OK",
        "COLLAB ERR",
        "COLLAB NO",
        "SEARCH OK",
        "PATCH OK",
        "PATCH ERR",
    }
)
_TERMINAL_TURN_KINDS = frozenset({"handoff", "done", "blocker", "sleep"})


def _parse_ts(ts: str) -> datetime:
    value = ts.rstrip("Z")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _ms_between(start: datetime, end: datetime) -> int:
    return max(0, int(round((end - start).total_seconds() * 1000)))


def _iter_events(events_file: Path) -> Iterator[dict]:
    if not events_file.exists():
        return
    with events_file.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError:
                continue


def _usage_tokens(usage: dict) -> TurnTokens:
    def _int(key: str) -> int:
        raw = usage.get(key)
        try:
            return int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            return 0

    cache_creation = _int("cache_creation_input_tokens")
    if not cache_creation:
        nested = usage.get("cache_creation")
        if isinstance(nested, dict):
            cache_creation = sum(
                int(v) for v in nested.values() if isinstance(v, (int, float))
            )
    return TurnTokens(
        input_tokens=_int("input_tokens"),
        output_tokens=_int("output_tokens"),
        cache_read_input_tokens=_int("cache_read_input_tokens") or _int("cached_input_tokens"),
        cache_creation_input_tokens=cache_creation,
    )


def _add_tokens(a: TurnTokens, b: TurnTokens) -> TurnTokens:
    return TurnTokens(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        cache_read_input_tokens=a.cache_read_input_tokens + b.cache_read_input_tokens,
        cache_creation_input_tokens=a.cache_creation_input_tokens + b.cache_creation_input_tokens,
    )


def compute_run_timing(run_dir: Path, *, step_mode: bool = False) -> RunTiming:
    from rally.services.run_timing_flags import evaluate_flags

    events_file = run_dir / "logs" / "events.jsonl"
    tool_calls: list[dict] = list(_extract_tool_calls(events_file))

    turns: list[TurnTiming] = []
    run_id: str | None = None
    flow_code: str | None = None
    run_start: datetime | None = None
    run_end: datetime | None = None
    setup_start: datetime | None = None
    setup_ms = 0
    last_turn_index = 0
    run_status = "running"

    current_turn: dict | None = None

    def _finalize_turn(end_ts: datetime, kind: str) -> None:
        if current_turn is None:
            return
        start = current_turn["start"]
        wall_ms = _ms_between(start, end_ts)
        turn_calls = [
            tc
            for tc in tool_calls
            if tc["turn_index"] == current_turn["turn_index"]
            and tc["end"] is not None
        ]
        tool_ms = sum(tc["dur_ms"] for tc in turn_calls)
        tools_called = len(turn_calls)
        errors = sum(1 for tc in turn_calls if tc["is_error"])
        hot_tools = _rollup_tools(turn_calls, limit=8)
        hot_commands = _rollup_commands(turn_calls, limit=5)
        turns.append(
            TurnTiming(
                turn_index=current_turn["turn_index"],
                agent_key=current_turn["agent_key"],
                agent_slug=current_turn["agent_slug"],
                kind=kind,
                started_at=current_turn["start"].isoformat().replace("+00:00", "Z"),
                ended_at=end_ts.isoformat().replace("+00:00", "Z"),
                wall_ms=wall_ms,
                tool_ms=tool_ms,
                model_ms=max(0, wall_ms - tool_ms),
                tools_called=tools_called,
                errors=errors,
                tokens=current_turn["tokens"],
                hot_tools=hot_tools,
                hot_commands=hot_commands,
            )
        )

    for event in _iter_events(events_file):
        code = event.get("code")
        ts_raw = event.get("ts")
        if not isinstance(ts_raw, str):
            continue
        ts = _parse_ts(ts_raw)
        if run_start is None:
            run_start = ts
        run_end = ts
        if run_id is None:
            rid = event.get("run_id")
            if isinstance(rid, str):
                run_id = rid
        if flow_code is None:
            fc = event.get("flow_code")
            if isinstance(fc, str):
                flow_code = fc
        if code == "SETUP":
            setup_start = ts
        elif code == "SETUP OK" and setup_start is not None:
            setup_ms += _ms_between(setup_start, ts)
            setup_start = None
        elif code == "TURN":
            if current_turn is not None:
                _finalize_turn(ts, kind="interrupted")
            turn_index = event.get("turn_index") or 0
            current_turn = {
                "turn_index": int(turn_index),
                "agent_key": event.get("agent_key"),
                "agent_slug": event.get("agent_slug"),
                "start": ts,
                "tokens": TurnTokens(),
            }
            last_turn_index = max(last_turn_index, int(turn_index))
        elif code == "USAGE" and current_turn is not None:
            usage = (event.get("data") or {}).get("usage")
            if isinstance(usage, dict):
                current_turn["tokens"] = _add_tokens(current_turn["tokens"], _usage_tokens(usage))
        elif code in {"HANDOFF", "DONE", "BLOCKED", "SLEEP"} and current_turn is not None:
            kind_map = {"HANDOFF": "handoff", "DONE": "done", "BLOCKED": "blocker", "SLEEP": "sleep"}
            kind = kind_map[code]
            _finalize_turn(ts, kind=kind)
            current_turn = None
            if kind in _TERMINAL_TURN_KINDS:
                run_status = {
                    "handoff": "running",
                    "done": "done",
                    "blocker": "blocked",
                    "sleep": "sleeping",
                }[kind]

    if current_turn is not None and run_end is not None:
        _finalize_turn(run_end, kind="interrupted")

    wall_ms = _ms_between(run_start, run_end) if run_start and run_end else 0
    active_ms = sum(turn.wall_ms for turn in turns)
    idle_ms = max(0, wall_ms - active_ms - setup_ms)

    per_agent = _aggregate_per_agent(turns)
    top_tools = _rollup_tools(tool_calls, limit=10)
    top_commands = _rollup_commands(tool_calls, limit=10)
    total_tokens = TurnTokens()
    for turn in turns:
        total_tokens = _add_tokens(total_tokens, turn.tokens)

    preliminary = RunTiming(
        run_id=run_id or "",
        flow_code=flow_code or "",
        run_status=run_status,
        last_turn_index=last_turn_index,
        wall_ms=wall_ms,
        active_ms=active_ms,
        idle_ms=idle_ms,
        setup_ms=setup_ms,
        tokens=total_tokens,
        turns=turns,
        per_agent=per_agent,
        top_tools=top_tools,
        top_commands=top_commands,
        flags=[],
    )
    flags = evaluate_flags(preliminary, tool_calls, step_mode=step_mode)
    return RunTiming(
        run_id=preliminary.run_id,
        flow_code=preliminary.flow_code,
        run_status=preliminary.run_status,
        last_turn_index=preliminary.last_turn_index,
        wall_ms=preliminary.wall_ms,
        active_ms=preliminary.active_ms,
        idle_ms=preliminary.idle_ms,
        setup_ms=preliminary.setup_ms,
        tokens=preliminary.tokens,
        turns=preliminary.turns,
        per_agent=preliminary.per_agent,
        top_tools=preliminary.top_tools,
        top_commands=preliminary.top_commands,
        flags=flags,
    )


def _extract_tool_calls(events_file: Path) -> Iterable[dict]:
    """Yield paired tool-call records (start + end) from the event stream."""
    open_calls: dict[str, dict] = {}
    fallback: dict[tuple[str | None, str], list[dict]] = defaultdict(list)
    records: list[dict] = []
    for event in _iter_events(events_file):
        code = event.get("code")
        data = event.get("data") or {}
        ts_raw = event.get("ts")
        if not isinstance(ts_raw, str):
            continue
        ts = _parse_ts(ts_raw)
        if code in _TOOL_START_CODES:
            tool_use_id = _str(data.get("tool_use_id"))
            tool_name = _str(data.get("tool_name")) or code.lower()
            record = {
                "turn_index": event.get("turn_index") or 0,
                "agent_slug": event.get("agent_slug"),
                "tool_name": tool_name,
                "tool_use_id": tool_use_id,
                "input_digest": _str(data.get("input_digest")),
                "sub_kind": _str(data.get("sub_kind")),
                "start": ts,
                "end": None,
                "dur_ms": 0,
                "is_error": False,
                "exit_code": None,
                "output_tail": None,
            }
            records.append(record)
            if tool_use_id:
                open_calls[tool_use_id] = record
            else:
                fallback[(event.get("agent_slug"), tool_name)].append(record)
        elif code in _TOOL_END_CODES:
            tool_use_id = _str(data.get("tool_use_id"))
            tool_name = _str(data.get("tool_name"))
            match: dict | None = None
            if tool_use_id and tool_use_id in open_calls:
                match = open_calls.pop(tool_use_id)
            elif tool_name:
                queue = fallback.get((event.get("agent_slug"), tool_name))
                if queue:
                    match = queue.pop(0)
            if match is None:
                continue
            match["end"] = ts
            match["dur_ms"] = _ms_between(match["start"], ts)
            match["is_error"] = bool(data.get("is_error"))
            if "exit_code" in data and isinstance(data["exit_code"], int):
                match["exit_code"] = data["exit_code"]
            output_tail = _str(data.get("output_tail"))
            if output_tail:
                match["output_tail"] = output_tail
            # If end carried a more specific tool_name (digest missing on start),
            # fill it in.
            if tool_name and not match.get("tool_name"):
                match["tool_name"] = tool_name
    for record in records:
        yield record


def _rollup_tools(calls: list[dict], *, limit: int) -> list[ToolCallRollup]:
    by_name: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_ms": 0, "err": 0})
    for tc in calls:
        if tc["end"] is None:
            continue
        slot = by_name[tc["tool_name"] or "?"]
        slot["count"] += 1
        slot["total_ms"] += tc["dur_ms"]
        if tc["is_error"]:
            slot["err"] += 1
    rolled = [
        ToolCallRollup(
            tool_name=name,
            count=slot["count"],
            total_ms=slot["total_ms"],
            error_count=slot["err"],
        )
        for name, slot in by_name.items()
    ]
    rolled.sort(key=lambda r: (-r.total_ms, -r.count))
    return rolled[:limit]


def _rollup_commands(calls: list[dict], *, limit: int) -> list[CommandRollup]:
    by_digest: dict[tuple[str, str], dict] = defaultdict(lambda: {"count": 0, "total_ms": 0, "err": 0})
    for tc in calls:
        if tc["end"] is None:
            continue
        digest = tc.get("input_digest")
        if not digest:
            continue
        key = (tc["tool_name"] or "?", digest)
        slot = by_digest[key]
        slot["count"] += 1
        slot["total_ms"] += tc["dur_ms"]
        if tc["is_error"]:
            slot["err"] += 1
    rolled = [
        CommandRollup(
            tool_name=key[0],
            input_digest=key[1],
            count=slot["count"],
            total_ms=slot["total_ms"],
            error_count=slot["err"],
        )
        for key, slot in by_digest.items()
    ]
    rolled.sort(key=lambda r: (-r.total_ms, -r.count))
    return rolled[:limit]


def _aggregate_per_agent(turns: list[TurnTiming]) -> list[AgentTiming]:
    by_slug: dict[str, dict] = defaultdict(
        lambda: {
            "agent_key": None,
            "turns": 0,
            "wall_ms": 0,
            "tool_ms": 0,
            "model_ms": 0,
            "tools_called": 0,
            "errors": 0,
            "tokens": TurnTokens(),
        }
    )
    for turn in turns:
        slug = turn.agent_slug or "?"
        slot = by_slug[slug]
        slot["agent_key"] = turn.agent_key or slot["agent_key"]
        slot["turns"] += 1
        slot["wall_ms"] += turn.wall_ms
        slot["tool_ms"] += turn.tool_ms
        slot["model_ms"] += turn.model_ms
        slot["tools_called"] += turn.tools_called
        slot["errors"] += turn.errors
        slot["tokens"] = _add_tokens(slot["tokens"], turn.tokens)
    agents = [
        AgentTiming(
            agent_slug=slug,
            agent_key=slot["agent_key"],
            turns=slot["turns"],
            wall_ms=slot["wall_ms"],
            tool_ms=slot["tool_ms"],
            model_ms=slot["model_ms"],
            tools_called=slot["tools_called"],
            errors=slot["errors"],
            tokens=slot["tokens"],
        )
        for slug, slot in by_slug.items()
    ]
    agents.sort(key=lambda a: -a.wall_ms)
    return agents


def _str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def write_run_timing(run_dir: Path, timing: RunTiming, *, final: bool) -> None:
    timing_path = run_dir / "timing.json"
    timing_path.write_text(json.dumps(asdict(timing), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if timing.turns:
        last_turn = timing.turns[-1]
        turns_log = run_dir / "timing_turns.jsonl"
        with turns_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(last_turn), sort_keys=True) + "\n")
    if final:
        _append_workspace_ndjson(run_dir, timing)


def _append_workspace_ndjson(run_dir: Path, timing: RunTiming) -> None:
    # run_dir is .../runs/active/<RUN> or .../runs/archive/<RUN>; timings file
    # lives at .../runs/timings.ndjson regardless.
    runs_root = run_dir.parent.parent if run_dir.parent.name in {"active", "archive"} else run_dir.parent
    target = runs_root / "timings.ndjson"
    summary = {
        "run_id": timing.run_id,
        "flow_code": timing.flow_code,
        "run_status": timing.run_status,
        "last_turn_index": timing.last_turn_index,
        "wall_ms": timing.wall_ms,
        "active_ms": timing.active_ms,
        "idle_ms": timing.idle_ms,
        "setup_ms": timing.setup_ms,
        "tokens": asdict(timing.tokens),
        "errors": sum(agent.errors for agent in timing.per_agent),
        "tools_called": sum(agent.tools_called for agent in timing.per_agent),
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")


def update_tool_calls(run_dir: Path, *, since_turn: int) -> None:
    """Append tool-call records from turns >= since_turn to tool_calls.jsonl.

    Idempotent: rewrites the file from events.jsonl each time. Cheap because
    the aggregator already walks events.jsonl; we just reuse the extraction.
    """
    events_file = run_dir / "logs" / "events.jsonl"
    target = run_dir / "tool_calls.jsonl"
    records = [tc for tc in _extract_tool_calls(events_file) if tc["end"] is not None]
    lines = []
    for tc in records:
        if tc["turn_index"] < since_turn:
            continue
        payload = {
            "turn_index": tc["turn_index"],
            "agent_slug": tc["agent_slug"],
            "tool_name": tc["tool_name"],
            "tool_use_id": tc["tool_use_id"],
            "sub_kind": tc["sub_kind"],
            "dur_ms": tc["dur_ms"],
            "is_error": tc["is_error"],
            "exit_code": tc["exit_code"],
            "input_digest": tc["input_digest"],
            "output_tail": tc["output_tail"],
            "ts_start": tc["start"].isoformat().replace("+00:00", "Z"),
            "ts_end": tc["end"].isoformat().replace("+00:00", "Z"),
        }
        lines.append(json.dumps(payload, sort_keys=True))
    # Rewrite from scratch — deterministic and avoids partial-write races.
    target.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
