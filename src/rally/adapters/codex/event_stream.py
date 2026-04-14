from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from rally.memory.logging import parse_memory_command, summarize_memory_command
from rally.services.run_events import EventDraft


@dataclass
class CodexEventStreamParser:
    turn_index: int
    agent_key: str
    agent_slug: str
    session_id: str | None = None
    _assistant_buffer: str = ""
    _reasoning_buffer: str = ""

    def consume_stdout_line(self, raw_line: str) -> list[EventDraft]:
        stripped = raw_line.strip()
        if not stripped:
            return []
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return self._flush_text_buffers() + [
                self._draft(
                    kind="warning",
                    code="WARN",
                    message="Codex wrote a non-JSON line to stdout.",
                    level="warning",
                    data={"raw": stripped},
                )
            ]
        if not isinstance(payload, dict):
            return self._flush_text_buffers() + [
                self._draft(
                    kind="debug",
                    code="RAW",
                    message="Codex wrote a non-object JSON payload.",
                    data={"raw": payload},
                )
            ]
        return self._consume_payload(payload)

    def flush(self) -> list[EventDraft]:
        return self._flush_text_buffers()

    def _consume_payload(self, payload: dict[str, Any]) -> list[EventDraft]:
        type_name = str(payload.get("type", "adapter.raw"))

        if type_name in {"thread.started", "thread.resumed"}:
            self.session_id = _string_value(payload.get("thread_id")) or self.session_id
            session_label = self.session_id or "unknown"
            verb = "Started" if type_name == "thread.started" else "Resumed"
            return self._flush_text_buffers() + [
                self._draft(
                    kind="lifecycle",
                    code="SESSION",
                    message=f"{verb} Codex session `{session_label}`.",
                    data={"type": type_name, "thread_id": self.session_id},
                )
            ]

        item_drafts = self._consume_item_payload(type_name=type_name, payload=payload)
        if item_drafts is not None:
            return self._flush_text_buffers() + item_drafts

        if type_name == "turn.completed":
            usage = payload.get("usage")
            if isinstance(usage, dict):
                return self._flush_text_buffers() + [
                    self._draft(
                        kind="status",
                        code="USAGE",
                        message=_usage_message(usage),
                        data={"type": type_name, "usage": usage},
                    )
                ]

        if type_name in {"turn.failed", "error"}:
            return self._flush_text_buffers() + [
                self._draft(
                    kind="warning",
                    code="ERROR",
                    message=_error_message(type_name=type_name, payload=payload),
                    level="error",
                    data=payload,
                )
            ]

        channel = _text_channel(type_name=type_name, payload=payload)
        if channel is not None:
            chunk = _text_chunk(payload)
            if chunk:
                return self._buffer_text(channel=channel, chunk=chunk, payload=payload)

        if _is_tool_payload(type_name=type_name, payload=payload):
            return self._flush_text_buffers() + [
                _tool_draft(self._draft, type_name=type_name, payload=payload)
            ]

        if _looks_like_warning(type_name=type_name, payload=payload):
            return self._flush_text_buffers() + [
                self._draft(
                    kind="warning",
                    code="WARN",
                    message=_best_message(payload) or f"Codex warning `{type_name}`.",
                    level="warning",
                    data=payload,
                )
            ]

        if _looks_like_error(type_name=type_name, payload=payload):
            return self._flush_text_buffers() + [
                self._draft(
                    kind="warning",
                    code="ERROR",
                    message=_best_message(payload) or f"Codex error `{type_name}`.",
                    level="error",
                    data=payload,
                )
            ]

        return self._flush_text_buffers() + [
            self._draft(
                kind="debug",
                code="RAW",
                message=f"Codex event `{type_name}`.",
                data=payload,
            )
        ]

    def _consume_item_payload(
        self,
        *,
        type_name: str,
        payload: dict[str, Any],
    ) -> list[EventDraft] | None:
        phase = _item_phase(type_name)
        if phase is None:
            return None

        item = payload.get("item")
        if not isinstance(item, dict):
            return [
                self._draft(
                    kind="warning",
                    code="WARN",
                    message=f"Codex `{type_name}` event is missing `item` details.",
                    level="warning",
                    data=payload,
                )
            ]

        item_type = _string_value(item.get("type"))
        if item_type is None:
            return [
                self._draft(
                    kind="warning",
                    code="WARN",
                    message=f"Codex `{type_name}` event is missing `item.type`.",
                    level="warning",
                    data=payload,
                )
            ]

        item_id = _string_value(item.get("id"))
        if item_type == "agent_message":
            return self._agent_message_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "reasoning":
            return self._reasoning_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "command_execution":
            return self._command_execution_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "mcp_tool_call":
            return self._mcp_tool_call_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "collab_tool_call":
            return self._collab_tool_call_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "web_search":
            return self._web_search_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "file_change":
            return self._file_change_drafts(
                item=item,
                item_id=item_id,
                item_phase=phase,
                event_type=type_name,
            )
        if item_type == "error":
            message = _string_value(item.get("message"))
            if message is None:
                return []
            return [
                self._draft(
                    kind="warning",
                    code="ERROR",
                    message=message,
                    level="error",
                    data={
                        "type": type_name,
                        "item_type": item_type,
                        "item_id": item_id,
                        "item_phase": phase,
                    },
                )
            ]
        return [
            self._draft(
                kind="debug",
                code="RAW",
                message=f"Codex item `{item_type}` in `{type_name}`.",
                data=payload,
            )
        ]

    def _agent_message_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        if item_phase == "started":
            return []
        text = _string_value(item.get("text"))
        if text is None:
            return []
        return [
            self._draft(
                kind="assistant",
                code="ASSIST",
                message=text,
                data={
                    "type": event_type,
                    "item_type": "agent_message",
                    "item_id": item_id,
                    "item_phase": item_phase,
                },
            )
        ]

    def _reasoning_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        text = _string_value(item.get("text"))
        if text is None:
            return []
        message, detail_lines = _split_message_and_details(text)
        return [
            self._trace_draft(
                kind="reasoning",
                code="THINK",
                message=message,
                trace_class="thinking",
                item_type="reasoning",
                item_id=item_id,
                item_phase=item_phase,
                status=None,
                detail_lines=detail_lines,
                extra_data={"type": event_type},
            )
        ]

    def _command_execution_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        status = _normalized_status(item.get("status"), fallback=item_phase)
        message = _string_value(item.get("command")) or "command"
        memory_command = parse_memory_command(message)
        if memory_command is not None:
            summary = summarize_memory_command(
                memory_command,
                status=status,
                output_text=_string_value(item.get("aggregated_output")),
            )
            return [
                self._trace_draft(
                    kind="memory",
                    code=summary.code,
                    message=summary.message,
                    level=summary.level,
                    trace_class="memory",
                    item_type="command_execution",
                    item_id=item_id,
                    item_phase=item_phase,
                    status=status,
                    detail_lines=list(summary.detail_lines),
                    extra_data={"type": event_type, "action": memory_command.action},
                )
            ]
        detail_lines: list[str] = []
        if status in {"completed", "failed", "declined"}:
            exit_code = item.get("exit_code")
            if isinstance(exit_code, int):
                detail_lines.append(f"exit code {exit_code}")
            detail_lines.extend(_tail_output_lines(item.get("aggregated_output")))
        return [
            self._trace_draft(
                kind="tool",
                code=_command_code(status),
                message=_truncate(message),
                level=_status_level(status),
                trace_class="tool",
                item_type="command_execution",
                item_id=item_id,
                item_phase=item_phase,
                status=status,
                detail_lines=detail_lines,
                extra_data={"type": event_type},
            )
        ]

    def _mcp_tool_call_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        status = _normalized_status(item.get("status"), fallback=item_phase)
        server = _string_value(item.get("server")) or "mcp"
        tool = _string_value(item.get("tool")) or "tool"
        detail_lines: list[str] = []
        argument_summary = _json_preview(item.get("arguments"))
        if argument_summary is not None:
            detail_lines.append(f"args: {argument_summary}")
        result_summary = _mcp_result_summary(item.get("result"))
        if result_summary is not None:
            detail_lines.append(result_summary)
        error_summary = _mcp_error_summary(item.get("error"))
        if error_summary is not None:
            detail_lines.append(error_summary)
        return [
            self._trace_draft(
                kind="tool",
                code=_status_code(base="MCP", status=status),
                message=f"{server}.{tool}",
                level=_status_level(status),
                trace_class="tool",
                item_type="mcp_tool_call",
                item_id=item_id,
                item_phase=item_phase,
                status=status,
                detail_lines=detail_lines,
                extra_data={"type": event_type},
            )
        ]

    def _collab_tool_call_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        status = _normalized_status(item.get("status"), fallback=item_phase)
        tool = _string_value(item.get("tool")) or "collab"
        detail_lines: list[str] = []
        receiver_thread_ids = item.get("receiver_thread_ids")
        if isinstance(receiver_thread_ids, list):
            detail_lines.append(f"targets: {len(receiver_thread_ids)}")
        prompt = _string_value(item.get("prompt"))
        if prompt is not None:
            detail_lines.append(f"prompt: {_truncate(prompt)}")
        states_summary = _agents_states_summary(item.get("agents_states"))
        if states_summary is not None:
            detail_lines.append(states_summary)
        return [
            self._trace_draft(
                kind="tool",
                code=_status_code(base="COLLAB", status=status),
                message=tool,
                level=_status_level(status),
                trace_class="tool",
                item_type="collab_tool_call",
                item_id=item_id,
                item_phase=item_phase,
                status=status,
                detail_lines=detail_lines,
                extra_data={"type": event_type},
            )
        ]

    def _web_search_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        query = _string_value(item.get("query")) or "search"
        status = "completed" if item_phase == "completed" else "in_progress"
        return [
            self._trace_draft(
                kind="tool",
                code=_status_code(base="SEARCH", status=status),
                message=query,
                trace_class="tool",
                item_type="web_search",
                item_id=item_id,
                item_phase=item_phase,
                status=status,
                detail_lines=[],
                extra_data={"type": event_type},
            )
        ]

    def _file_change_drafts(
        self,
        *,
        item: dict[str, Any],
        item_id: str | None,
        item_phase: str,
        event_type: str,
    ) -> list[EventDraft]:
        status = _normalized_status(item.get("status"), fallback=item_phase)
        changes = _file_change_lines(item.get("changes"))
        count = len(changes)
        noun = "file" if count == 1 else "files"
        message = f"Updated {count} {noun}." if count else "Updated files."
        if status == "failed":
            message = f"Patch failed after {count} {noun}." if count else "Patch failed."
        return [
            self._trace_draft(
                kind="tool",
                code=_status_code(base="PATCH", status=status),
                message=message,
                level=_status_level(status),
                trace_class="tool",
                item_type="file_change",
                item_id=item_id,
                item_phase=item_phase,
                status=status,
                detail_lines=changes,
                extra_data={"type": event_type},
            )
        ]

    def _buffer_text(self, *, channel: str, chunk: str, payload: dict[str, Any]) -> list[EventDraft]:
        buffer_name = "_reasoning_buffer" if channel == "reasoning" else "_assistant_buffer"
        current = getattr(self, buffer_name)
        current += chunk
        drafts: list[EventDraft] = []
        while "\n" in current:
            line, current = current.split("\n", 1)
            stripped = line.strip()
            if not stripped:
                continue
            if channel == "reasoning":
                drafts.append(
                    self._trace_draft(
                        kind="reasoning",
                        code="THINK",
                        message=stripped,
                        trace_class="thinking",
                        item_type="reasoning",
                        item_id=None,
                        item_phase="delta",
                        status=None,
                        detail_lines=[],
                        extra_data={"type": payload.get("type")},
                    )
                )
            else:
                drafts.append(
                    self._draft(
                        kind="assistant",
                        code="ASSIST",
                        message=stripped,
                        data={"type": payload.get("type")},
                    )
                )
        setattr(self, buffer_name, current)
        return drafts

    def _flush_text_buffers(self) -> list[EventDraft]:
        drafts: list[EventDraft] = []
        if self._assistant_buffer.strip():
            drafts.append(
                self._draft(
                    kind="assistant",
                    code="ASSIST",
                    message=self._assistant_buffer.strip(),
                )
            )
        if self._reasoning_buffer.strip():
            message, detail_lines = _split_message_and_details(self._reasoning_buffer.strip())
            drafts.append(
                self._trace_draft(
                    kind="reasoning",
                    code="THINK",
                    message=message,
                    trace_class="thinking",
                    item_type="reasoning",
                    item_id=None,
                    item_phase="delta",
                    status=None,
                    detail_lines=detail_lines,
                    extra_data=None,
                )
            )
        self._assistant_buffer = ""
        self._reasoning_buffer = ""
        return drafts

    def _trace_draft(
        self,
        *,
        kind: str,
        code: str,
        message: str,
        trace_class: str,
        item_type: str,
        item_id: str | None,
        item_phase: str,
        status: str | None,
        detail_lines: list[str],
        level: str = "info",
        extra_data: dict[str, Any] | None = None,
    ) -> EventDraft:
        data: dict[str, Any] = {
            "trace_class": trace_class,
            "item_type": item_type,
            "item_id": item_id,
            "item_phase": item_phase,
        }
        if status is not None:
            data["status"] = status
        if detail_lines:
            data["detail_lines"] = detail_lines
        if extra_data:
            data.update(extra_data)
        return self._draft(
            kind=kind,
            code=code,
            message=message,
            level=level,
            data=data,
        )

    def _draft(
        self,
        *,
        kind: str,
        code: str,
        message: str,
        level: str = "info",
        data: dict[str, Any] | None = None,
    ) -> EventDraft:
        return EventDraft(
            source="codex",
            kind=kind,
            code=code,
            message=message,
            level=level,
            data=data or {},
            turn_index=self.turn_index,
            agent_key=self.agent_key,
            agent_slug=self.agent_slug,
        )


def _best_message(payload: dict[str, Any]) -> str | None:
    for key in ("message", "error", "detail", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _item_phase(type_name: str) -> str | None:
    if type_name == "item.started":
        return "started"
    if type_name == "item.updated":
        return "updated"
    if type_name == "item.completed":
        return "completed"
    return None


def _error_message(*, type_name: str, payload: dict[str, Any]) -> str:
    if type_name == "turn.failed":
        error = payload.get("error")
        if isinstance(error, dict):
            return _best_message(error) or "Codex turn failed."
        return _best_message(payload) or "Codex turn failed."
    return _best_message(payload) or "Codex reported an error."


def _normalized_status(raw_value: object, *, fallback: str) -> str:
    status = _string_value(raw_value)
    if status is not None:
        return status
    if fallback == "completed":
        return "completed"
    return "in_progress"


def _command_code(status: str) -> str:
    if status == "completed":
        return "CMD OK"
    if status == "failed":
        return "CMD ERR"
    if status == "declined":
        return "CMD NO"
    return "CMD"


def _status_code(*, base: str, status: str) -> str:
    if status == "completed":
        return f"{base} OK"
    if status == "failed":
        return f"{base} ERR"
    if status == "declined":
        return f"{base} NO"
    return base


def _status_level(status: str) -> str:
    if status == "failed":
        return "error"
    if status == "declined":
        return "warning"
    return "info"


def _split_message_and_details(raw_text: str) -> tuple[str, list[str]]:
    lines = [_truncate(line.strip()) for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return "-", []
    return lines[0], lines[1:4]


def _tail_output_lines(raw_value: object) -> list[str]:
    if not isinstance(raw_value, str):
        return []
    lines = [_truncate(line.strip()) for line in raw_value.splitlines() if line.strip()]
    return lines[-2:]


def _json_preview(raw_value: object) -> str | None:
    if raw_value is None:
        return None
    try:
        return _truncate(json.dumps(raw_value, sort_keys=True, separators=(",", ":")))
    except TypeError:
        text = str(raw_value).strip()
        return _truncate(text) if text else None


def _mcp_result_summary(raw_value: object) -> str | None:
    if not isinstance(raw_value, dict):
        return None
    structured = raw_value.get("structured_content")
    structured_preview = _json_preview(structured)
    if structured_preview is not None:
        return f"result: {structured_preview}"
    content = raw_value.get("content")
    if isinstance(content, list):
        noun = "block" if len(content) == 1 else "blocks"
        return f"result: {len(content)} content {noun}"
    return None


def _mcp_error_summary(raw_value: object) -> str | None:
    if not isinstance(raw_value, dict):
        return None
    message = _string_value(raw_value.get("message"))
    if message is None:
        return None
    return f"error: {message}"


def _agents_states_summary(raw_value: object) -> str | None:
    if not isinstance(raw_value, dict) or not raw_value:
        return None
    counts: dict[str, int] = {}
    for state in raw_value.values():
        if not isinstance(state, dict):
            continue
        status = _string_value(state.get("status"))
        if status is None:
            continue
        counts[status] = counts.get(status, 0) + 1
    if not counts:
        return None
    parts = [f"{status}={counts[status]}" for status in sorted(counts)]
    return "states: " + ", ".join(parts)


def _file_change_lines(raw_value: object) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    lines: list[str] = []
    for change in raw_value:
        if not isinstance(change, dict):
            continue
        path = _string_value(change.get("path"))
        if path is None:
            continue
        kind = _string_value(change.get("kind")) or "update"
        prefix = {"add": "A", "delete": "D", "update": "M"}.get(kind, "?")
        lines.append(f"{prefix} {path}")
        if len(lines) == 3:
            break
    return lines


def _truncate(text: str, *, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _is_tool_payload(*, type_name: str, payload: dict[str, Any]) -> bool:
    lowered = type_name.lower()
    if "tool" in lowered:
        return True
    return any(key in payload for key in ("tool_name", "call_id", "command"))


def _tool_draft(build_draft, *, type_name: str, payload: dict[str, Any]) -> EventDraft:
    lowered = type_name.lower()
    tool_name = _string_value(payload.get("tool_name")) or _string_value(payload.get("name")) or "tool"
    command = _string_value(payload.get("command"))
    memory_command = parse_memory_command(command or "")
    detail = command or _best_message(payload) or type_name
    if memory_command is not None:
        status = "in_progress"
        if any(token in lowered for token in ("error", "fail")):
            status = "failed"
        elif any(token in lowered for token in ("complete", "done", "finish", "success")):
            status = "completed"
        summary = summarize_memory_command(
            memory_command,
            status=status,
            output_text=_best_message(payload),
        )
        data = {
            "trace_class": "memory",
            "type": type_name,
            "action": memory_command.action,
        }
        if summary.detail_lines:
            data["detail_lines"] = list(summary.detail_lines)
        return build_draft(
            kind="memory",
            code=summary.code,
            message=summary.message,
            level=summary.level,
            data=data,
        )
    data = {"trace_class": "tool", "type": type_name}
    if any(token in lowered for token in ("error", "fail")):
        return build_draft(
            kind="tool",
            code="TOOL ERR",
            message=f"{tool_name}: {detail}",
            level="error",
            data=data,
        )
    if any(token in lowered for token in ("complete", "done", "finish", "success")):
        return build_draft(
            kind="tool",
            code="TOOL OK",
            message=f"{tool_name}: {detail}",
            data=data,
        )
    return build_draft(
        kind="tool",
        code="TOOL",
        message=f"{tool_name}: {detail}",
        data=data,
    )


def _usage_message(usage: dict[str, Any]) -> str:
    input_tokens = _int_value(usage.get("input_tokens"))
    output_tokens = _int_value(usage.get("output_tokens"))
    cached_tokens = _int_value(usage.get("cached_input_tokens"))
    return (
        "Token use: "
        f"{input_tokens} input, "
        f"{output_tokens} output, "
        f"{cached_tokens} cached."
    )


def _looks_like_warning(*, type_name: str, payload: dict[str, Any]) -> bool:
    lowered = type_name.lower()
    level = _string_value(payload.get("level"))
    return "warning" in lowered or level == "warning"


def _looks_like_error(*, type_name: str, payload: dict[str, Any]) -> bool:
    lowered = type_name.lower()
    level = _string_value(payload.get("level"))
    return "error" in lowered or level == "error"


def _text_channel(*, type_name: str, payload: dict[str, Any]) -> str | None:
    lowered = type_name.lower()
    if "reason" in lowered:
        return "reasoning"
    role = _string_value(payload.get("role"))
    if role == "reasoning":
        return "reasoning"
    if not any(token in lowered for token in ("delta", "text", "message", "content", "assistant")):
        return None
    if role in {None, "assistant"}:
        return "assistant"
    return None


def _text_chunk(payload: dict[str, Any]) -> str | None:
    for key in ("delta", "text", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _string_value(raw_value: object) -> str | None:
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()
    return None


def _int_value(raw_value: object) -> int:
    if isinstance(raw_value, int):
        return raw_value
    return 0
