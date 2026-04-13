from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from rally.domain.flow import CompiledAgentContract, FieldPath, ReviewContract
from rally.domain.turn_result import (
    BlockerTurnResult,
    DoneTurnResult,
    HandoffTurnResult,
    TurnResult,
    parse_turn_result,
)
from rally.errors import RallyStateError


@dataclass(frozen=True)
class LoadedFinalResponse:
    payload: Mapping[str, object]
    turn_result: TurnResult
    review_note_markdown: str | None = None


def load_turn_result(*, last_message_file: Path) -> TurnResult:
    payload = load_turn_result_payload(last_message_file=last_message_file)
    try:
        return parse_turn_result(payload)
    except ValueError as exc:
        raise RallyStateError(
            f"Final JSON in `{last_message_file}` is not a valid Rally turn result: {exc}"
        ) from exc


def load_agent_final_response(
    *,
    compiled_agent: CompiledAgentContract,
    last_message_file: Path,
) -> LoadedFinalResponse:
    payload = load_turn_result_payload(last_message_file=last_message_file)
    try:
        if compiled_agent.review is None:
            return LoadedFinalResponse(payload=payload, turn_result=parse_turn_result(payload))
        turn_result = _parse_review_turn_result(payload=payload, review=compiled_agent.review)
        return LoadedFinalResponse(
            payload=payload,
            turn_result=turn_result,
            review_note_markdown=_render_review_note_markdown(payload=payload, review=compiled_agent.review),
        )
    except ValueError as exc:
        raise RallyStateError(
            f"Final JSON in `{last_message_file}` is not a valid Rally final response: {exc}"
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


def _parse_review_turn_result(
    *,
    payload: Mapping[str, object],
    review: ReviewContract,
) -> TurnResult:
    field_paths = _review_result_paths(review=review)
    verdict = _require_review_string(payload=payload, field_paths=field_paths, field_name="verdict")
    if verdict not in {"accept", "changes_requested"}:
        raise ValueError(f"Review verdict must be `accept` or `changes_requested`, found `{verdict}`.")

    blocked_gate = _optional_review_string(payload=payload, field_paths=field_paths, field_name="blocked_gate")
    if blocked_gate is not None:
        return BlockerTurnResult(reason=blocked_gate)

    next_owner = _optional_review_string(payload=payload, field_paths=field_paths, field_name="next_owner")
    if next_owner is not None:
        return HandoffTurnResult(next_owner=next_owner)

    if verdict == "accept":
        return DoneTurnResult(summary=_review_done_summary(payload=payload, field_paths=field_paths))

    raise ValueError(
        "Review final response rejected work without a route or blocked gate. "
        "Rally needs routed rejects or blocked reviews."
    )


def _review_done_summary(
    *,
    payload: Mapping[str, object],
    field_paths: Mapping[str, FieldPath],
) -> str:
    for field_name in ("readback", "analysis"):
        value = _optional_review_string(payload=payload, field_paths=field_paths, field_name=field_name)
        if value is not None:
            return value
    return "Review accepted."


def _render_review_note_markdown(
    *,
    payload: Mapping[str, object],
    review: ReviewContract,
) -> str:
    field_paths = _review_result_paths(review=review)
    verdict = _require_review_string(payload=payload, field_paths=field_paths, field_name="verdict")
    lines: list[str] = []

    readback = _optional_review_string(payload=payload, field_paths=field_paths, field_name="readback")
    if readback is not None:
        lines.extend(["### Findings First", readback, ""])

    lines.extend(
        [
            "### Review Verdict",
            f"- Verdict: `{verdict}`",
        ]
    )
    reviewed_artifact = _optional_review_string(
        payload=payload,
        field_paths=field_paths,
        field_name="reviewed_artifact",
    )
    if reviewed_artifact is not None:
        lines.append(f"- Reviewed Artifact: `{reviewed_artifact}`")
    current_artifact = _optional_review_string(
        payload=payload,
        field_paths=field_paths,
        field_name="current_artifact",
    )
    if current_artifact is not None:
        lines.append(f"- Current Artifact: `{current_artifact}`")
    next_owner = _optional_review_string(payload=payload, field_paths=field_paths, field_name="next_owner")
    if next_owner is not None:
        lines.append(f"- Next Owner: `{next_owner}`")
    blocked_gate = _optional_review_string(
        payload=payload,
        field_paths=field_paths,
        field_name="blocked_gate",
    )
    if blocked_gate is not None:
        lines.append(f"- Blocked Gate: {blocked_gate}")
    lines.append("")

    analysis = _optional_review_string(payload=payload, field_paths=field_paths, field_name="analysis")
    if analysis is not None:
        lines.extend(["### Review Summary", analysis, ""])

    failing_gates = _optional_review_list(payload=payload, field_paths=field_paths, field_name="failing_gates")
    if failing_gates:
        lines.append("### Failing Gates")
        lines.extend(f"- `{gate}`" for gate in failing_gates)
        lines.append("")

    return "\n".join(_trim_blank_edges(lines))


def _review_result_paths(*, review: ReviewContract) -> Mapping[str, FieldPath]:
    if review.final_response.mode == "carrier":
        return review.carrier_fields
    return review.final_response.review_fields


def _optional_review_string(
    *,
    payload: Mapping[str, object],
    field_paths: Mapping[str, FieldPath],
    field_name: str,
) -> str | None:
    path = field_paths.get(field_name)
    if path is None:
        return None
    value = _extract_field_value(payload=payload, path=path)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Review field `{field_name}` must be a non-empty string when present.")
    return value


def _require_review_string(
    *,
    payload: Mapping[str, object],
    field_paths: Mapping[str, FieldPath],
    field_name: str,
) -> str:
    value = _optional_review_string(payload=payload, field_paths=field_paths, field_name=field_name)
    if value is None:
        raise ValueError(f"Review field `{field_name}` is required for Rally control.")
    return value


def _optional_review_list(
    *,
    payload: Mapping[str, object],
    field_paths: Mapping[str, FieldPath],
    field_name: str,
) -> tuple[str, ...]:
    path = field_paths.get(field_name)
    if path is None:
        return ()
    value = _extract_field_value(payload=payload, path=path)
    if value is None:
        return ()
    if isinstance(value, str) and value.strip():
        return (value,)
    if not isinstance(value, list):
        raise ValueError(f"Review field `{field_name}` must be a string, a string list, or absent.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Review field `{field_name}` must contain only non-empty strings.")
        items.append(item)
    return tuple(items)


def _extract_field_value(*, payload: Mapping[str, object], path: FieldPath) -> object | None:
    current: object = payload
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _trim_blank_edges(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    return trimmed
