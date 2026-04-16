from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class TurnResultKind(StrEnum):
    HANDOFF = "handoff"
    DONE = "done"
    BLOCKER = "blocker"
    SLEEP = "sleep"


@dataclass(frozen=True)
class HandoffTurnResult:
    next_owner: str
    summary: None = None
    reason: None = None
    sleep_duration_seconds: None = None
    kind: TurnResultKind = TurnResultKind.HANDOFF


@dataclass(frozen=True)
class DoneTurnResult:
    summary: str
    next_owner: None = None
    reason: None = None
    sleep_duration_seconds: None = None
    kind: TurnResultKind = TurnResultKind.DONE


@dataclass(frozen=True)
class BlockerTurnResult:
    reason: str
    next_owner: None = None
    summary: None = None
    sleep_duration_seconds: None = None
    kind: TurnResultKind = TurnResultKind.BLOCKER


@dataclass(frozen=True)
class SleepTurnResult:
    reason: str
    sleep_duration_seconds: int
    next_owner: None = None
    summary: None = None
    kind: TurnResultKind = TurnResultKind.SLEEP


TurnResult = HandoffTurnResult | DoneTurnResult | BlockerTurnResult | SleepTurnResult


def parse_turn_result(
    payload: Mapping[str, object],
    *,
    handoff_next_owner: str | None = None,
) -> TurnResult:
    kind = payload.get("kind")
    if kind == TurnResultKind.HANDOFF:
        next_owner = handoff_next_owner if handoff_next_owner is not None else _require_string(payload, "next_owner")
        return HandoffTurnResult(next_owner=next_owner)
    if kind == TurnResultKind.DONE:
        return DoneTurnResult(summary=_require_string(payload, "summary"))
    if kind == TurnResultKind.BLOCKER:
        return BlockerTurnResult(reason=_require_string(payload, "reason"))
    if kind == TurnResultKind.SLEEP:
        sleep_duration_seconds = payload.get("sleep_duration_seconds")
        if not isinstance(sleep_duration_seconds, int) or sleep_duration_seconds < 1:
            raise ValueError("Sleep turn result requires `sleep_duration_seconds` as an integer >= 1.")
        return SleepTurnResult(
            reason=_require_string(payload, "reason"),
            sleep_duration_seconds=sleep_duration_seconds,
        )
    raise ValueError(f"Unsupported turn result kind: `{kind}`.")


def _require_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Turn result requires non-empty string field `{field_name}`.")
    return value
