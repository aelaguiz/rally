from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.adapters.codex.result_contract import load_turn_result
from rally.domain.turn_result import HandoffTurnResult
from rally.errors import RallyStateError


class ResultContractTests(unittest.TestCase):
    def test_load_turn_result_accepts_fenced_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """```json
{"kind":"handoff","next_owner":"change_engineer","summary":null,"reason":null,"sleep_duration_seconds":null}
```
""",
                encoding="utf-8",
            )

            result = load_turn_result(last_message_file=last_message)

            self.assertEqual(result, HandoffTurnResult(next_owner="change_engineer"))

    def test_load_turn_result_rejects_non_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text("not json\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyStateError, "does not contain valid JSON"):
                load_turn_result(last_message_file=last_message)


if __name__ == "__main__":
    unittest.main()
