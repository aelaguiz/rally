from __future__ import annotations

import unittest

from rally.domain.turn_result import HandoffTurnResult, SleepTurnResult, parse_turn_result


class TurnResultContractsTests(unittest.TestCase):
    def test_parse_turn_result_handoff(self) -> None:
        result = parse_turn_result({"kind": "handoff", "next_owner": "change_engineer"})
        self.assertEqual(result, HandoffTurnResult(next_owner="change_engineer"))

    def test_parse_turn_result_sleep(self) -> None:
        result = parse_turn_result(
            {"kind": "sleep", "reason": "wait for build", "sleep_duration_seconds": 5}
        )
        self.assertEqual(
            result,
            SleepTurnResult(reason="wait for build", sleep_duration_seconds=5),
        )

    def test_parse_turn_result_rejects_missing_next_owner(self) -> None:
        with self.assertRaisesRegex(ValueError, "next_owner"):
            parse_turn_result({"kind": "handoff"})


if __name__ == "__main__":
    unittest.main()
