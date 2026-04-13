from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from rally.domain.turn_result import TurnResult, parse_turn_result
from rally.errors import RallyStateError


def load_turn_result(*, last_message_file: Path) -> TurnResult:
    payload = load_turn_result_payload(last_message_file=last_message_file)
    try:
        return parse_turn_result(payload)
    except ValueError as exc:
        raise RallyStateError(
            f"Final JSON in `{last_message_file}` is not a valid Rally turn result: {exc}"
        ) from exc


def load_turn_result_payload(*, last_message_file: Path) -> Mapping[str, object]:
    if not last_message_file.is_file():
        raise RallyStateError(f"Final output file does not exist: `{last_message_file}`.")
    raw_text = last_message_file.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise RallyStateError(f"Final output file `{last_message_file}` is empty.")

    normalized = _strip_json_fence(raw_text)
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise RallyStateError(
            f"Final output file `{last_message_file}` does not contain valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise RallyStateError(f"Final output file `{last_message_file}` must contain a JSON object.")
    return payload


def _strip_json_fence(raw_text: str) -> str:
    if not raw_text.startswith("```"):
        return raw_text
    lines = raw_text.splitlines()
    if len(lines) < 3:
        return raw_text
    if not lines[0].startswith("```") or lines[-1].strip() != "```":
        return raw_text
    return "\n".join(lines[1:-1]).strip()
