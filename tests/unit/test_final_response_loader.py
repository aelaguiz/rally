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
    RouteBranchContract,
    RouteChoiceMemberContract,
    RouteContract,
    RouteSelectorContract,
    RouteTargetContract,
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

    def test_load_agent_final_response_routes_producer_handoff_from_route_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "kind": "handoff",
  "next_route": "poem_critic",
  "summary": null,
  "reason": null,
  "sleep_duration_seconds": null
}
""",
                encoding="utf-8",
            )

            loaded = load_agent_final_response(
                compiled_agent=_producer_agent_contract(
                    selector_field=("next_route",),
                    route_members={"poem_critic": "PoemCritic"},
                ),
                last_message_file=last_message,
            )

            self.assertEqual(loaded.turn_result, HandoffTurnResult(next_owner="PoemCritic"))
            self.assertIsNone(loaded.review_truth)

    def test_load_agent_final_response_routes_cross_module_producer_handoff_by_target_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "kind": "handoff",
  "next_route": "section_dossier_engineer",
  "summary": null,
  "reason": null,
  "sleep_duration_seconds": null
}
""",
                encoding="utf-8",
            )

            loaded = load_agent_final_response(
                compiled_agent=_producer_agent_contract(
                    selector_field=("next_route",),
                    route_members={},
                    route_targets={
                        "section_dossier_engineer": RouteTargetContract(
                            key="agents.section_dossier_engineer.SectionDossierEngineer",
                            name="SectionDossierEngineer",
                            title="Section Dossier Engineer",
                            module_parts=("agents", "section_dossier_engineer"),
                        )
                    },
                ),
                last_message_file=last_message,
            )

            self.assertEqual(loaded.turn_result, HandoffTurnResult(next_owner="SectionDossierEngineer"))
            self.assertIsNone(loaded.review_truth)

    def test_load_agent_final_response_rejects_unknown_route_member(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "kind": "handoff",
  "next_route": "unknown_member",
  "summary": null,
  "reason": null,
  "sleep_duration_seconds": null
}
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyStateError, "unknown route member `unknown_member`"):
                load_agent_final_response(
                    compiled_agent=_producer_agent_contract(
                        selector_field=("next_route",),
                        route_members={"poem_critic": "PoemCritic"},
                    ),
                    last_message_file=last_message,
                )

    def test_load_agent_final_response_rejects_handoff_without_selected_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "kind": "handoff",
  "next_route": null,
  "summary": null,
  "reason": null,
  "sleep_duration_seconds": null
}
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyStateError, "cannot leave route field `next_route` empty"):
                load_agent_final_response(
                    compiled_agent=_producer_agent_contract(
                        selector_field=("next_route",),
                        route_members={"poem_critic": "PoemCritic"},
                    ),
                    last_message_file=last_message,
                )

    def test_load_agent_final_response_rejects_non_handoff_with_selected_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            last_message = Path(temp_dir) / "last_message.json"
            last_message.write_text(
                """{
  "kind": "done",
  "next_route": "poem_critic",
  "summary": "done",
  "reason": null,
  "sleep_duration_seconds": null
}
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyStateError, "must not select route field `next_route`"):
                load_agent_final_response(
                    compiled_agent=_producer_agent_contract(
                        selector_field=("next_route",),
                        route_members={"poem_critic": "PoemCritic"},
                    ),
                    last_message_file=last_message,
                )


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


def _producer_agent_contract(
    *,
    selector_field: tuple[str, ...],
    route_members: dict[str, str],
    route_targets: dict[str, RouteTargetContract] | None = None,
) -> CompiledAgentContract:
    branches: list[RouteBranchContract] = []
    branch_targets = route_targets or {
        member_wire: RouteTargetContract(
            key=target_name,
            name=target_name,
            title=target_name,
            module_parts=(),
        )
        for member_wire, target_name in route_members.items()
    }
    for member_wire, target in branch_targets.items():
        branches.append(
            RouteBranchContract(
                target=target,
                label=f"Route to {target.name}.",
                summary=f"Route to {target.name}.",
                choice_members=(
                    RouteChoiceMemberContract(
                        member_key=member_wire,
                        member_title=target.name,
                        member_wire=member_wire,
                    ),
                ),
            )
        )

    return CompiledAgentContract(
        name="PoemWriter",
        slug="poem_writer",
        entrypoint=Path("/tmp/prompts/AGENTS.prompt"),
        markdown_path=Path("/tmp/build/poem_writer/AGENTS.md"),
        metadata_file=Path("/tmp/build/poem_writer/final_output.contract.json"),
        contract_version=1,
        final_output=FinalOutputContract(
            exists=True,
            contract_version=1,
            declaration_key="PoemWriterTurnResult",
            declaration_name="PoemWriterTurnResult",
            format_mode="json_object",
            schema_profile="OpenAIStructuredOutput",
            generated_schema_file=Path("/tmp/schema.json"),
            metadata_file=Path("/tmp/build/poem_writer/final_output.contract.json"),
        ),
        route=RouteContract(
            exists=True,
            behavior="conditional",
            has_unrouted_branch=True,
            unrouted_review_verdicts=(),
            selector=RouteSelectorContract(
                surface="final_output",
                field_path=selector_field,
                null_behavior="no_route",
            ),
            branches=tuple(branches),
        ),
    )
