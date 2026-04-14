from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from rally.services.run_events import EventDraft


@dataclass
class ClaudeCodeEventStreamParser:
    turn_index: int
    agent_key: str
    agent_slug: str
    session_id: str | None = None
    _tool_uses: dict[str, tuple[str, dict[str, object]]] = field(default_factory=dict)

    def consume_stdout_line(self, raw_line: str) -> list[EventDraft]:
        stripped = raw_line.strip()
        if not stripped:
            return []
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return [
                self._draft(
                    kind="warning",
                    code="WARN",
                    message="Claude Code wrote a non-JSON line to stdout.",
                    level="warning",
                    data={"raw": stripped},
                )
            ]
        if not isinstance(payload, dict):
            return [
                self._draft(
                    kind="debug",
                    code="RAW",
                    message="Claude Code wrote a non-object JSON payload.",
                    data={"raw": payload},
                )
            ]
        return self._consume_payload(payload)

    def flush(self) -> list[EventDraft]:
        return []

    def _consume_payload(self, payload: dict[str, Any]) -> list[EventDraft]:
        type_name = _string_value(payload.get("type")) or "adapter.raw"
        session_id = _string_value(payload.get("session_id"))
        if session_id is not None:
            self.session_id = session_id

        if type_name == "system" and payload.get("subtype") == "init":
            session_label = self.session_id or "unknown"
            return [
                self._draft(
                    kind="lifecycle",
                    code="SESSION",
                    message=f"Started Claude Code session `{session_label}`.",
                    data={"type": type_name, "session_id": self.session_id},
                )
            ]

        if type_name == "assistant":
            message = payload.get("message")
            if not isinstance(message, dict):
                return []
            return self._assistant_message_drafts(message)

        if type_name == "user":
            message = payload.get("message")
            if not isinstance(message, dict):
                return []
            return self._tool_result_drafts(message)

        if type_name == "result":
            usage = payload.get("usage")
            drafts: list[EventDraft] = []
            if isinstance(usage, dict):
                drafts.append(
                    self._draft(
                        kind="status",
                        code="USAGE",
                        message=_usage_message(usage),
                        data={"type": type_name, "usage": usage},
                    )
                )
            return drafts

        if type_name == "rate_limit_event":
            return []

        return [
            self._draft(
                kind="debug",
                code="RAW",
                message=f"Claude Code event `{type_name}`.",
                data=payload,
            )
        ]

    def _assistant_message_drafts(self, message: dict[str, Any]) -> list[EventDraft]:
        content = message.get("content")
        if not isinstance(content, list):
            return []
        drafts: list[EventDraft] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = _string_value(item.get("type"))
            if item_type == "thinking":
                thinking = _string_value(item.get("thinking"))
                if thinking:
                    drafts.append(
                        self._draft(
                            kind="reasoning",
                            code="THINK",
                            message=thinking,
                            data={"item_type": item_type},
                        )
                    )
                continue
            if item_type == "text":
                text = _string_value(item.get("text"))
                if text:
                    drafts.append(
                        self._draft(
                            kind="assistant",
                            code="ASSIST",
                            message=text,
                            data={"item_type": item_type},
                        )
                    )
                continue
            if item_type == "tool_use":
                tool_id = _string_value(item.get("id"))
                tool_name = _string_value(item.get("name")) or "tool"
                tool_input = item.get("input")
                if isinstance(tool_id, str) and isinstance(tool_input, dict):
                    self._tool_uses[tool_id] = (tool_name, dict(tool_input))
                drafts.append(
                    self._draft(
                        kind="tool",
                        code="TOOL",
                        message=_tool_start_message(tool_name=tool_name, tool_input=tool_input),
                        data={"item_type": item_type, "tool_name": tool_name},
                    )
                )
        return drafts

    def _tool_result_drafts(self, message: dict[str, Any]) -> list[EventDraft]:
        content = message.get("content")
        if not isinstance(content, list):
            return []
        drafts: list[EventDraft] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if _string_value(item.get("type")) != "tool_result":
                continue
            tool_id = _string_value(item.get("tool_use_id"))
            tool_name, tool_input = self._tool_uses.pop(tool_id or "", ("tool", {}))
            drafts.append(
                self._draft(
                    kind="tool",
                    code="TOOL OK",
                    message=_tool_result_message(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        result_payload=item,
                    ),
                    data={"tool_name": tool_name},
                )
            )
        return drafts

    def _draft(
        self,
        *,
        kind: str,
        code: str,
        message: str,
        level: str = "info",
        data: dict[str, object] | None = None,
    ) -> EventDraft:
        return EventDraft(
            source="claude_code",
            kind=kind,
            code=code,
            message=message,
            level=level,
            data=data or {},
            turn_index=self.turn_index,
            agent_key=self.agent_key,
            agent_slug=self.agent_slug,
        )


def extract_structured_output(stdout_text: str) -> dict[str, object] | None:
    structured_output: dict[str, object] | None = None
    for line in stdout_text.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "result":
            if isinstance(payload.get("structured_output"), dict):
                structured_output = dict(payload["structured_output"])
                continue
            raw_result = payload.get("result")
            parsed_result = _parse_json_object(raw_result)
            if parsed_result is not None:
                structured_output = parsed_result
                continue
        if payload.get("type") != "assistant":
            continue
        message = payload.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "tool_use" or item.get("name") != "StructuredOutput":
                text_payload = item.get("text")
                parsed_text = _parse_json_object(text_payload)
                if parsed_text is not None:
                    structured_output = parsed_text
                continue
            tool_input = item.get("input")
            if isinstance(tool_input, dict):
                structured_output = dict(tool_input)
    return structured_output


def _usage_message(usage: dict[str, object]) -> str:
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    cache_tokens = int(usage.get("cache_read_input_tokens", 0) or 0)
    return (
        f"Claude Code used {input_tokens} input token(s), "
        f"{output_tokens} output token(s), and {cache_tokens} cached token(s)."
    )


def _tool_start_message(*, tool_name: str, tool_input: object) -> str:
    if isinstance(tool_input, dict):
        command = _string_value(tool_input.get("command"))
        if tool_name == "Bash" and command:
            return command
        file_path = _string_value(tool_input.get("file_path"))
        if file_path is not None and tool_name in {"Read", "Edit", "Write"}:
            return f"{tool_name} `{file_path}`."
        query = _string_value(tool_input.get("pattern")) or _string_value(tool_input.get("query"))
        if query is not None and tool_name in {"Grep", "Glob", "ToolSearch", "WebSearch"}:
            return f"{tool_name} `{query}`."
        skill_name = _string_value(tool_input.get("skill_name"))
        if tool_name == "Skill" and skill_name is not None:
            return f"Run skill `{skill_name}`."
    return f"Run {tool_name}."


def _tool_result_message(
    *,
    tool_name: str,
    tool_input: dict[str, object],
    result_payload: dict[str, object],
) -> str:
    if tool_name == "Bash":
        command = _string_value(tool_input.get("command"))
        if command is not None:
            return f"Finished `{command}`."
    if tool_name in {"Read", "Edit", "Write"}:
        file_path = _string_value(tool_input.get("file_path"))
        if file_path is not None:
            return f"{tool_name} finished for `{file_path}`."
    content = _string_value(result_payload.get("content"))
    if content:
        first_line = content.strip().splitlines()[0]
        return _truncate(first_line, 140)
    return f"{tool_name} finished."


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _parse_json_object(raw_value: object) -> dict[str, object] | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    payload = _parse_json_mapping(raw_value)
    if payload is not None:
        return payload
    fenced = _unwrap_json_code_fence(raw_value)
    if fenced is None:
        return None
    return _parse_json_mapping(fenced)


def _parse_json_mapping(raw_text: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return dict(payload)


def _unwrap_json_code_fence(raw_text: str) -> str | None:
    stripped = raw_text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return None
    lines = stripped.splitlines()
    if len(lines) < 3:
        return None
    opening = lines[0].strip()
    if opening not in {"```", "```json"}:
        return None
    return "\n".join(lines[1:-1]).strip()
