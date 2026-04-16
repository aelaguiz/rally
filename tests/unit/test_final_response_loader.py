from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.domain.flow import (
    CompiledAgentContract,
    FinalOutputContract,
    ReviewContract,
    ReviewFinalResponseContract,
    ReviewOutcomeContract,
    ReviewOutputContract,
)
from rally.domain.turn_result import BlockerTurnResult, DoneTurnResult, HandoffTurnResult
from rally.errors import RallyStateError
from rally.services.final_response_loader import load_agent_final_response, load_turn_result


class FinalResponseLoaderTests(unittest.TestCase):
    def test_load_turn_result_reads_shared_loader_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                '{"kind":"handoff","next_owner":"change_engineer","summary":null,"reason":null,"sleep_duration_seconds":null}\n',
                encoding="utf-8",
            )

            result = load_turn_result(last_message_file=last_message)

            self.assertEqual(result, HandoffTurnResult(next_owner="change_engineer"))

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

    def test_load_agent_final_response_maps_review_carrier_to_done_and_returns_review_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "verdict": "accept",
  "reviewed_artifact": "home:artifacts/poem.md",
  "analysis_performed": "The draft now feels finished.",
  "findings_first": "The poem is ready to keep."
}
""",
                encoding="utf-8",
            )

            loaded = load_agent_final_response(
                compiled_agent=_review_agent_contract(mode="carrier"),
                last_message_file=last_message,
            )

            self.assertEqual(loaded.turn_result, DoneTurnResult(summary="The poem is ready to keep."))
            self.assertIsNotNone(loaded.review_truth)
            self.assertEqual(loaded.review_truth.verdict, "accept")
            self.assertEqual(loaded.review_truth.reviewed_artifact, "home:artifacts/poem.md")
            self.assertEqual(loaded.review_truth.readback, "The poem is ready to keep.")
            self.assertIsNone(loaded.review_truth.next_owner)

    def test_load_agent_final_response_maps_review_blocked_gate_to_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "verdict": "changes_requested",
  "reviewed_artifact": "home:artifacts/poem.md",
  "analysis_performed": "The review could not start.",
  "findings_first": "The poem draft is missing.",
  "failure_detail": {
    "blocked_gate": "The poem draft is missing."
  }
}
""",
                encoding="utf-8",
            )

            loaded = load_agent_final_response(
                compiled_agent=_review_agent_contract(mode="carrier"),
                last_message_file=last_message,
            )

            self.assertEqual(loaded.turn_result, BlockerTurnResult(reason="The poem draft is missing."))
            self.assertIsNotNone(loaded.review_truth)
            self.assertEqual(loaded.review_truth.blocked_gate, "The poem draft is missing.")

    def test_load_agent_final_response_maps_split_control_ready_review_to_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "verdict": "changes_requested",
  "reviewed_artifact": "home:artifacts/poem.md",
  "analysis_performed": "The middle image still needs work.",
  "findings_first": "The poem needs one more draft.",
  "current_artifact": "home:artifacts/poem.md",
  "next_owner": "poem_writer",
  "blocked_gate": null
}
""",
                encoding="utf-8",
            )

            loaded = load_agent_final_response(
                compiled_agent=_review_agent_contract(mode="split"),
                last_message_file=last_message,
            )

            self.assertEqual(loaded.turn_result, HandoffTurnResult(next_owner="poem_writer"))
            self.assertIsNotNone(loaded.review_truth)
            self.assertEqual(loaded.review_truth.next_owner, "poem_writer")
            self.assertEqual(loaded.review_truth.current_artifact, "home:artifacts/poem.md")


if __name__ == "__main__":
    unittest.main()


def _review_agent_contract(*, mode: str) -> CompiledAgentContract:
    if mode == "carrier":
        carrier_fields = {
            "verdict": ("verdict",),
            "reviewed_artifact": ("reviewed_artifact",),
            "analysis": ("analysis_performed",),
            "readback": ("findings_first",),
            "blocked_gate": ("failure_detail", "blocked_gate"),
        }
        final_response = ReviewFinalResponseContract(
            mode="carrier",
            declaration_key="PoemReviewResponse",
            declaration_name="PoemReviewResponse",
            review_fields={},
            control_ready=True,
        )
    else:
        carrier_fields = {
            "verdict": ("verdict",),
            "reviewed_artifact": ("reviewed_artifact",),
            "analysis": ("analysis_performed",),
            "readback": ("findings_first",),
            "current_artifact": ("current_artifact",),
            "next_owner": ("next_owner",),
            "blocked_gate": ("blocked_gate",),
            "failing_gates": ("failing_gates",),
        }
        final_response = ReviewFinalResponseContract(
            mode="split",
            declaration_key="PoemReviewControl",
            declaration_name="PoemReviewControl",
            review_fields={
                "verdict": ("verdict",),
                "reviewed_artifact": ("reviewed_artifact",),
                "analysis": ("analysis_performed",),
                "readback": ("findings_first",),
                "current_artifact": ("current_artifact",),
                "next_owner": ("next_owner",),
                "blocked_gate": ("blocked_gate",),
                "failing_gates": ("failing_gates",),
            },
            control_ready=True,
        )
    return CompiledAgentContract(
        name="PoemCritic",
        slug="poem_critic",
        entrypoint=Path("/tmp/prompts/AGENTS.prompt"),
        markdown_path=Path("/tmp/build/poem_critic/AGENTS.md"),
        metadata_file=Path("/tmp/build/poem_critic/final_output.contract.json"),
        contract_version=1,
        final_output=FinalOutputContract(
            exists=True,
            contract_version=1,
            declaration_key="PoemReviewResponse" if mode == "carrier" else "PoemReviewControl",
            declaration_name="PoemReviewResponse" if mode == "carrier" else "PoemReviewControl",
            format_mode="json_object",
            schema_profile="OpenAIStructuredOutput",
            generated_schema_file=Path("/tmp/schema.json"),
            metadata_file=Path("/tmp/build/poem_critic/final_output.contract.json"),
        ),
        review=ReviewContract(
            exists=True,
            comment_output=ReviewOutputContract(
                declaration_key="PoemReviewResponse",
                declaration_name="PoemReviewResponse",
            ),
            carrier_fields=carrier_fields,
            final_response=final_response,
            outcomes={
                "accept": ReviewOutcomeContract(exists=True, verdict="accept", route_behavior="never"),
                "changes_requested": ReviewOutcomeContract(
                    exists=True,
                    verdict="changes_requested",
                    route_behavior="always",
                ),
                "blocked": ReviewOutcomeContract(
                    exists=True,
                    verdict="changes_requested",
                    route_behavior="never",
                ),
            },
        ),
    )
