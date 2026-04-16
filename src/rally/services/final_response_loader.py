from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from rally.domain.flow import (
    CompiledAgentContract,
    FieldPath,
    ReviewContract,
    RouteBranchContract,
    RouteContract,
    RouteSelectorContract,
)
from rally.domain.turn_result import (
    BlockerTurnResult,
    DoneTurnResult,
    HandoffTurnResult,
    TurnResult,
    parse_turn_result,
)
from rally.errors import RallyStateError


@dataclass(frozen=True)
class LoadedReviewTruth:
    verdict: str
    reviewed_artifact: str | None
    analysis: str | None
    readback: str | None
    current_artifact: str | None
    next_owner: str | None
    blocked_gate: str | None
    failing_gates: tuple[str, ...]


@dataclass(frozen=True)
class LoadedFinalResponse:
    payload: Mapping[str, object]
    turn_result: TurnResult
    review_truth: LoadedReviewTruth | None = None


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
            turn_result = _load_producer_turn_result(payload=payload, compiled_agent=compiled_agent)
            return LoadedFinalResponse(payload=payload, turn_result=turn_result)
        review_truth = _load_review_truth(payload=payload, review=compiled_agent.review)
        turn_result = _parse_review_turn_result(review_truth=review_truth)
        return LoadedFinalResponse(
            payload=payload,
            turn_result=turn_result,
            review_truth=review_truth,
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


def _load_producer_turn_result(
    *,
    payload: Mapping[str, object],
    compiled_agent: CompiledAgentContract,
) -> TurnResult:
    handoff_next_owner = _resolve_producer_handoff_next_owner(
        payload=payload,
        route=compiled_agent.route,
    )
    return parse_turn_result(payload, handoff_next_owner=handoff_next_owner)


def _resolve_producer_handoff_next_owner(
    *,
    payload: Mapping[str, object],
    route: RouteContract | None,
) -> str | None:
    kind = payload.get("kind")
    selector = route.selector if route is not None else None
    if selector is None:
        if kind == "handoff":
            raise ValueError("Producer handoff requires emitted `route.selector` truth.")
        return None

    selected_member = _extract_field_value(payload=payload, path=selector.field_path)
    if kind == "handoff":
        if selected_member is None:
            if selector.null_behavior == "invalid":
                raise ValueError(
                    f"Producer handoff must select route field `{'.'.join(selector.field_path)}`."
                )
            raise ValueError(
                f"Producer handoff cannot leave route field `{'.'.join(selector.field_path)}` empty."
            )
        return _resolve_branch_target(route=route, selector=selector, selected_member=selected_member)

    if selected_member is None and selector.null_behavior == "invalid":
        raise ValueError(
            f"Route selector `{'.'.join(selector.field_path)}` cannot be null when `kind` is `{kind}`."
        )
    if selected_member is not None:
        raise ValueError(
            f"Non-handoff producer result must not select route field `{'.'.join(selector.field_path)}`."
        )
    return None


def _resolve_branch_target(
    *,
    route: RouteContract,
    selector: RouteSelectorContract,
    selected_member: object,
) -> str:
    if not isinstance(selected_member, str) or not selected_member:
        raise ValueError(
            f"Route selector `{'.'.join(selector.field_path)}` must resolve to a non-empty string member."
        )
    branch = _find_route_branch(route=route, selected_member=selected_member)
    if branch is None:
        raise ValueError(
            f"Route selector `{'.'.join(selector.field_path)}` picked unknown route member `{selected_member}`."
        )
    return branch.target.key


def _find_route_branch(
    *,
    route: RouteContract,
    selected_member: str,
) -> RouteBranchContract | None:
    for branch in route.branches:
        for choice_member in branch.choice_members:
            if choice_member.member_wire == selected_member:
                return branch
    return None


def _strip_json_fence(raw_text: str) -> str:
    if not raw_text.startswith("```"):
        return raw_text
    lines = raw_text.splitlines()
    if len(lines) < 3:
        return raw_text
    if not lines[0].startswith("```") or lines[-1].strip() != "```":
        return raw_text
    return "\n".join(lines[1:-1]).strip()


def _load_review_truth(
    *,
    payload: Mapping[str, object],
    review: ReviewContract,
) -> LoadedReviewTruth:
    field_paths = _review_result_paths(review=review)
    verdict = _require_review_string(payload=payload, field_paths=field_paths, field_name="verdict")
    if verdict not in {"accept", "changes_requested"}:
        raise ValueError(f"Review verdict must be `accept` or `changes_requested`, found `{verdict}`.")

    return LoadedReviewTruth(
        verdict=verdict,
        reviewed_artifact=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="reviewed_artifact",
        ),
        analysis=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="analysis",
        ),
        readback=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="readback",
        ),
        current_artifact=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="current_artifact",
        ),
        next_owner=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="next_owner",
        ),
        blocked_gate=_optional_review_string(
            payload=payload,
            field_paths=field_paths,
            field_name="blocked_gate",
        ),
        failing_gates=_optional_review_list(
            payload=payload,
            field_paths=field_paths,
            field_name="failing_gates",
        ),
    )


def _parse_review_turn_result(*, review_truth: LoadedReviewTruth) -> TurnResult:
    if review_truth.blocked_gate is not None:
        return BlockerTurnResult(reason=review_truth.blocked_gate)

    if review_truth.next_owner is not None:
        return HandoffTurnResult(next_owner=review_truth.next_owner)

    if review_truth.verdict == "accept":
        return DoneTurnResult(summary=_review_done_summary(review_truth=review_truth))

    raise ValueError(
        "Review final response rejected work without a route or blocked gate. "
        "Rally needs routed rejects or blocked reviews."
    )


def _review_done_summary(*, review_truth: LoadedReviewTruth) -> str:
    for value in (review_truth.readback, review_truth.analysis):
        if value is not None:
            return value
    return "Review accepted."


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
