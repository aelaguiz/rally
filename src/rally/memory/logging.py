from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
from typing import Literal, Mapping


MemoryAction = Literal["search", "use", "save", "refresh"]

MEMORY_EVENT_MODE_ENV = "RALLY_MEMORY_EVENT_MODE"
MEMORY_EVENT_MODE_ADAPTER = "adapter"
_MEMORY_ACTIONS = {"search", "use", "save", "refresh"}
_SHELL_NAMES = {"bash", "sh", "zsh"}


@dataclass(frozen=True)
class ParsedMemoryCommand:
    action: MemoryAction
    query: str | None = None
    memory_id: str | None = None


@dataclass(frozen=True)
class MemoryTraceSummary:
    code: str
    message: str
    detail_lines: tuple[str, ...] = ()
    level: str = "info"


def should_record_memory_events(*, env: Mapping[str, str] | None = None) -> bool:
    resolved_env = os.environ if env is None else env
    mode = resolved_env.get(MEMORY_EVENT_MODE_ENV, "").strip().lower()
    return mode != MEMORY_EVENT_MODE_ADAPTER


def parse_memory_command(raw_command: str) -> ParsedMemoryCommand | None:
    for tokens in _token_levels(raw_command):
        parsed = _parse_memory_tokens(tokens)
        if parsed is not None:
            return parsed
    return None


def summarize_memory_command(
    parsed: ParsedMemoryCommand,
    *,
    status: str,
    output_text: str | None = None,
) -> MemoryTraceSummary:
    if status == "failed":
        return MemoryTraceSummary(
            code="MEM ERR",
            message=f"Memory {parsed.action} failed.",
            detail_lines=_tail_lines(output_text),
            level="error",
        )
    if status == "declined":
        return MemoryTraceSummary(
            code="MEM NO",
            message=f"Memory {parsed.action} was blocked.",
            detail_lines=_tail_lines(output_text),
            level="warning",
        )
    if status == "completed":
        return _completed_summary(parsed, output_text=output_text)
    return MemoryTraceSummary(
        code="MEM",
        message=_start_message(parsed),
    )


def count_summary_text(*, indexed: int, updated: int, unchanged: int, removed: int) -> str:
    return (
        f"Indexed {indexed} new, {updated} updated, "
        f"{unchanged} unchanged, {removed} removed."
    )


def _completed_summary(
    parsed: ParsedMemoryCommand,
    *,
    output_text: str | None,
) -> MemoryTraceSummary:
    if parsed.action == "search":
        return _search_summary(parsed, output_text=output_text)
    if parsed.action == "use":
        return _use_summary(parsed, output_text=output_text)
    if parsed.action == "save":
        return _save_summary(output_text=output_text)
    return _refresh_summary(output_text=output_text)


def _search_summary(
    parsed: ParsedMemoryCommand,
    *,
    output_text: str | None,
) -> MemoryTraceSummary:
    lines = _non_empty_lines(output_text)
    if not lines:
        return MemoryTraceSummary(code="MEM OK", message="Finished memory search.")
    if lines[0] == "No scoped memories found.":
        return MemoryTraceSummary(code="MEM OK", message=lines[0])
    hit_lines = _search_hit_lines(lines)
    if hit_lines:
        noun = "hit" if len(hit_lines) == 1 else "hits"
        return MemoryTraceSummary(
            code="MEM OK",
            message=f"Found {len(hit_lines)} memory {noun}.",
            detail_lines=tuple(hit_lines[:3]),
        )
    query = parsed.query.strip() if parsed.query else "the task"
    return MemoryTraceSummary(
        code="MEM OK",
        message=f"Finished memory search for {query!r}.",
        detail_lines=tuple(lines[:3]),
    )


def _use_summary(
    parsed: ParsedMemoryCommand,
    *,
    output_text: str | None,
) -> MemoryTraceSummary:
    lines = _non_empty_lines(output_text)
    memory_id = parsed.memory_id
    detail_lines: list[str] = []
    if lines:
        match = re.match(r"^Memory `([^`]+)` from `([^`]+)`$", lines[0])
        if match is not None:
            memory_id = memory_id or match.group(1)
            detail_lines.append(_truncate(match.group(2)))
    lesson = _section_first_line(output_text or "", "# Lesson")
    if lesson is not None:
        detail_lines.append(_truncate(lesson))
    if memory_id is None:
        return MemoryTraceSummary(
            code="MEM OK",
            message="Loaded memory.",
            detail_lines=tuple(detail_lines[:3]),
        )
    return MemoryTraceSummary(
        code="MEM OK",
        message=f"Loaded memory `{memory_id}`.",
        detail_lines=tuple(detail_lines[:3]),
    )


def _save_summary(*, output_text: str | None) -> MemoryTraceSummary:
    lines = _non_empty_lines(output_text)
    if not lines:
        return MemoryTraceSummary(code="MEM OK", message="Saved memory.")
    match = re.match(r"^(Created|Updated) memory `([^`]+)` at `([^`]+)`\.\s*(.*)$", lines[0])
    if match is None:
        return MemoryTraceSummary(
            code="MEM OK",
            message="Saved memory.",
            detail_lines=tuple(lines[:3]),
        )
    detail_lines = [_truncate(match.group(3))]
    summary = match.group(4).strip()
    if summary:
        detail_lines.append(_truncate(summary))
    return MemoryTraceSummary(
        code="MEM OK",
        message=f"{match.group(1)} memory `{match.group(2)}`.",
        detail_lines=tuple(detail_lines[:3]),
    )


def _refresh_summary(*, output_text: str | None) -> MemoryTraceSummary:
    lines = _non_empty_lines(output_text)
    if not lines:
        return MemoryTraceSummary(code="MEM OK", message="Refreshed scoped memory index.")
    first_line = lines[0]
    if not first_line.startswith("Refreshed scoped memory index."):
        return MemoryTraceSummary(
            code="MEM OK",
            message="Refreshed scoped memory index.",
            detail_lines=tuple(lines[:3]),
        )
    detail_lines = []
    count_summary = _count_summary_from_line(first_line)
    if count_summary is not None:
        detail_lines.append(count_summary)
    return MemoryTraceSummary(
        code="MEM OK",
        message="Refreshed scoped memory index.",
        detail_lines=tuple(detail_lines[:3]),
    )


def _start_message(parsed: ParsedMemoryCommand) -> str:
    if parsed.action == "search":
        query = parsed.query.strip() if parsed.query else "this task"
        return f"Search memory for {query!r}."
    if parsed.action == "use":
        if parsed.memory_id is not None:
            return f"Use memory `{parsed.memory_id}`."
        return "Use memory."
    if parsed.action == "save":
        return "Save memory."
    return "Refresh memory."


def _search_hit_lines(lines: list[str]) -> list[str]:
    results: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^\d+\.\s+(\S+)\s+\(([0-9.]+)\)$", lines[index])
        if match is None:
            index += 1
            continue
        memory_id = match.group(1)
        title = lines[index + 1] if index + 1 < len(lines) else memory_id
        results.append(_truncate(f"{memory_id}: {title}"))
        index += 3
    return results


def _section_first_line(raw_text: str, header: str) -> str | None:
    active = False
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == header:
            active = True
            continue
        if active and line.startswith("# "):
            return None
        if active:
            return line
    return None


def _count_summary_from_line(line: str) -> str | None:
    marker = "Indexed "
    index = line.find(marker)
    if index < 0:
        return None
    return _truncate(line[index:])


def _tail_lines(raw_text: str | None) -> tuple[str, ...]:
    lines = _non_empty_lines(raw_text)
    return tuple(lines[-3:])


def _non_empty_lines(raw_text: str | None) -> list[str]:
    if raw_text is None:
        return []
    return [_truncate(line.strip()) for line in raw_text.splitlines() if line.strip()]


def _token_levels(raw_command: str) -> tuple[list[str], ...]:
    pending = [raw_command]
    seen: set[str] = set()
    token_lists: list[list[str]] = []
    while pending:
        command = pending.pop(0).strip()
        if not command or command in seen:
            continue
        seen.add(command)
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        if not tokens:
            continue
        token_lists.append(tokens)
        nested = _nested_shell_command(tokens)
        if nested is not None:
            pending.append(nested)
    return tuple(token_lists)


def _nested_shell_command(tokens: list[str]) -> str | None:
    if len(tokens) < 3:
        return None
    shell_name = Path(tokens[0]).name
    if shell_name not in _SHELL_NAMES:
        return None
    if tokens[1] not in {"-c", "-lc"}:
        return None
    return tokens[2]


def _parse_memory_tokens(tokens: list[str]) -> ParsedMemoryCommand | None:
    for index, token in enumerate(tokens[:-2]):
        if not _is_rally_cli_token(token):
            continue
        if tokens[index + 1] != "memory":
            continue
        action = tokens[index + 2]
        if action not in _MEMORY_ACTIONS:
            return None
        args = tokens[index + 3 :]
        if action == "search":
            return ParsedMemoryCommand(action="search", query=_option_value(args, "--query"))
        if action == "use":
            return ParsedMemoryCommand(action="use", memory_id=_positional_argument(args))
        if action == "save":
            return ParsedMemoryCommand(action="save")
        return ParsedMemoryCommand(action="refresh")
    return None


def _option_value(tokens: list[str], option_name: str) -> str | None:
    for index, token in enumerate(tokens):
        if token == option_name and index + 1 < len(tokens):
            return tokens[index + 1]
    return None


def _positional_argument(tokens: list[str]) -> str | None:
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in {"--run-id", "--agent-slug", "--query", "--limit", "--text", "--file"}:
            skip_next = True
            continue
        if token.startswith("--"):
            continue
        return token
    return None


def _is_rally_cli_token(token: str) -> bool:
    if token in {"$RALLY_CLI_BIN", "${RALLY_CLI_BIN}", "rally"}:
        return True
    return Path(token).name == "rally"


def _truncate(text: str, *, limit: int = 140) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
