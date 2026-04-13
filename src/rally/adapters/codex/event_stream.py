from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

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
        lowered = type_name.lower()

        if type_name == "thread.started":
            self.session_id = _string_value(payload.get("thread_id")) or self.session_id
            session_label = self.session_id or "unknown"
            return self._flush_text_buffers() + [
                self._draft(
                    kind="lifecycle",
                    code="SESSION",
                    message=f"Started Codex session `{session_label}`.",
                    data={"type": type_name, "thread_id": self.session_id},
                )
            ]
        if type_name == "thread.resumed":
            self.session_id = _string_value(payload.get("thread_id")) or self.session_id
            session_label = self.session_id or "unknown"
            return self._flush_text_buffers() + [
                self._draft(
                    kind="lifecycle",
                    code="SESSION",
                    message=f"Resumed Codex session `{session_label}`.",
                    data={"type": type_name, "thread_id": self.session_id},
                )
            ]

        channel = _text_channel(type_name=type_name, payload=payload)
        if channel is not None:
            chunk = _text_chunk(payload)
            if chunk:
                return self._buffer_text(channel=channel, chunk=chunk, payload=payload)

        if _is_tool_payload(type_name=type_name, payload=payload):
            return self._flush_text_buffers() + [_tool_draft(self._draft, type_name=type_name, payload=payload)]

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

    def _buffer_text(self, *, channel: str, chunk: str, payload: dict[str, Any]) -> list[EventDraft]:
        buffer_name = "_reasoning_buffer" if channel == "reasoning" else "_assistant_buffer"
        current = getattr(self, buffer_name)
        current += chunk
        drafts: list[EventDraft] = []
        while "\n" in current:
            line, current = current.split("\n", 1)
            if line.strip():
                drafts.append(
                    self._draft(
                        kind=channel,
                        code="REASON" if channel == "reasoning" else "ASSIST",
                        message=line.strip(),
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
            drafts.append(
                self._draft(
                    kind="reasoning",
                    code="REASON",
                    message=self._reasoning_buffer.strip(),
                )
            )
        self._assistant_buffer = ""
        self._reasoning_buffer = ""
        return drafts

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


def _is_tool_payload(*, type_name: str, payload: dict[str, Any]) -> bool:
    lowered = type_name.lower()
    if "tool" in lowered:
        return True
    return any(key in payload for key in ("tool_name", "call_id", "command"))


def _tool_draft(build_draft, *, type_name: str, payload: dict[str, Any]) -> EventDraft:
    lowered = type_name.lower()
    tool_name = _string_value(payload.get("tool_name")) or _string_value(payload.get("name")) or "tool"
    detail = _string_value(payload.get("command")) or _best_message(payload) or type_name
    if any(token in lowered for token in ("error", "fail")):
        return build_draft(
            kind="tool",
            code="TOOL ERR",
            message=f"{tool_name}: {detail}",
            level="error",
            data=payload,
        )
    if any(token in lowered for token in ("complete", "done", "finish", "success")):
        return build_draft(
            kind="tool",
            code="TOOL OK",
            message=f"{tool_name}: {detail}",
            data=payload,
        )
    return build_draft(
        kind="tool",
        code="TOOL",
        message=f"{tool_name}: {detail}",
        data=payload,
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
