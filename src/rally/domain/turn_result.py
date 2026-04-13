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
    kind: TurnResultKind = TurnResultKind.HANDOFF


@dataclass(frozen=True)
class DoneTurnResult:
    summary: str
    kind: TurnResultKind = TurnResultKind.DONE


@dataclass(frozen=True)
class BlockerTurnResult:
    reason: str
    kind: TurnResultKind = TurnResultKind.BLOCKER


@dataclass(frozen=True)
class SleepTurnResult:
    reason: str
    sleep_duration_seconds: int
    kind: TurnResultKind = TurnResultKind.SLEEP


TurnResult = HandoffTurnResult | DoneTurnResult | BlockerTurnResult | SleepTurnResult


def parse_turn_result(payload: Mapping[str, object]) -> TurnResult:
    kind = payload.get("kind")
    if kind == TurnResultKind.HANDOFF:
        return HandoffTurnResult(next_owner=_require_string(payload, "next_owner"))
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
