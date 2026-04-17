from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    EmittedOutputContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
    IoContract,
    IoShapeContract,
    IoTargetContract,
    OutputBindingContract,
    PreviousTurnInputContract,
)
from rally.errors import RallyStateError
from rally.services.previous_turn_inputs import render_previous_turn_appendix


class PreviousTurnInputsTests(unittest.TestCase):
    def test_render_previous_turn_appendix_reads_exact_previous_final_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousTurnResult",
                            input_name="Previous Turn Result",
                            selector_kind="default_final_output",
                            selector_text="Exact previous final output",
                            resolved_declaration_key="SharedTurnResult",
                            derived_contract_mode="structured_json",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )

            appendix = render_previous_turn_appendix(
                workspace_root=repo_root,
                run_home=run_home,
                flow=flow,
                agent=current_agent,
                turn_index=2,
            )

            self.assertIn("## Previous Turn Inputs", appendix)
            self.assertIn("### Previous Turn Result", appendix)
            self.assertIn("- Previous Agent: `source_agent`", appendix)
            self.assertIn('"kind": "done"', appendix)
            self.assertIn('"summary": "ready"', appendix)

    def test_render_previous_turn_appendix_reads_file_backed_structured_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
                io=IoContract(
                    previous_turn_inputs=(),
                    outputs=(
                        self._output(
                            declaration_key="StateFile",
                            target_key="File",
                            target_title="File",
                            config={"path": "home:artifacts/state.json"},
                            derived_contract_mode="structured_json",
                            readback_mode="structured_json",
                            shape_name="StateJson",
                            shape_title="State JSON",
                        ),
                    ),
                    output_bindings=(),
                ),
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousState",
                            input_name="Previous State",
                            selector_kind="output_decl",
                            selector_text="shared.outputs.StateFile",
                            resolved_declaration_key="StateFile",
                            derived_contract_mode="structured_json",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )
            artifact_path = run_home / "artifacts" / "state.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(json.dumps({"status": "draft"}) + "\n", encoding="utf-8")

            appendix = render_previous_turn_appendix(
                workspace_root=repo_root,
                run_home=run_home,
                flow=flow,
                agent=current_agent,
                turn_index=2,
            )

            self.assertIn("### Previous State", appendix)
            self.assertIn("```json", appendix)
            self.assertIn('"status": "draft"', appendix)

    def test_render_previous_turn_appendix_reads_file_backed_readable_text_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
                io=IoContract(
                    previous_turn_inputs=(),
                    outputs=(
                        self._output(
                            declaration_key="DraftFile",
                            target_key="File",
                            target_title="File",
                            config={"path": "home:artifacts/draft.md"},
                            derived_contract_mode="readable_text",
                            readback_mode="readable_text",
                            shape_name="MarkdownDocument",
                            shape_title="Markdown Document",
                        ),
                    ),
                    output_bindings=(
                        OutputBindingContract(
                            binding_path=("draft",),
                            declaration_key="DraftFile",
                        ),
                    ),
                ),
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousDraft",
                            input_name="Previous Draft",
                            selector_kind="output_binding",
                            selector_text="source_agent.SourceOutputs:draft",
                            resolved_declaration_key="DraftFile",
                            derived_contract_mode="readable_text",
                            binding_path=("draft",),
                            shape_name="MarkdownDocument",
                            shape_title="Markdown Document",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )
            artifact_path = run_home / "artifacts" / "draft.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("# Draft\n\nLine one.\n", encoding="utf-8")

            appendix = render_previous_turn_appendix(
                workspace_root=repo_root,
                run_home=run_home,
                flow=flow,
                agent=current_agent,
                turn_index=2,
            )

            self.assertIn("### Previous Draft", appendix)
            self.assertIn("```markdown", appendix)
            self.assertIn("# Draft", appendix)

    def test_render_previous_turn_appendix_fails_when_io_outputs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousState",
                            input_name="Previous State",
                            selector_kind="output_decl",
                            selector_text="shared.outputs.StateFile",
                            resolved_declaration_key="StateFile",
                            derived_contract_mode="structured_json",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )

            with self.assertRaisesRegex(RallyStateError, "missing `io.outputs`"):
                render_previous_turn_appendix(
                    workspace_root=repo_root,
                    run_home=run_home,
                    flow=flow,
                    agent=current_agent,
                    turn_index=2,
                )

    def test_render_previous_turn_appendix_fails_on_contract_mode_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
                io=IoContract(
                    previous_turn_inputs=(),
                    outputs=(
                        self._output(
                            declaration_key="StateFile",
                            target_key="File",
                            target_title="File",
                            config={"path": "home:artifacts/state.json"},
                            derived_contract_mode="structured_json",
                            readback_mode="structured_json",
                            shape_name="StateJson",
                            shape_title="State JSON",
                        ),
                    ),
                    output_bindings=(),
                ),
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousState",
                            input_name="Previous State",
                            selector_kind="output_decl",
                            selector_text="shared.outputs.StateFile",
                            resolved_declaration_key="StateFile",
                            derived_contract_mode="readable_text",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )
            artifact_path = run_home / "artifacts" / "state.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(json.dumps({"status": "draft"}) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyStateError, "contract-mode mismatch"):
                render_previous_turn_appendix(
                    workspace_root=repo_root,
                    run_home=run_home,
                    flow=flow,
                    agent=current_agent,
                    turn_index=2,
                )

    def test_render_previous_turn_appendix_fails_on_note_backed_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
                io=IoContract(
                    previous_turn_inputs=(),
                    outputs=(
                        self._output(
                            declaration_key="rally.base_agent.RallyIssueNote",
                            target_key="RallyIssueNoteAppend",
                            target_title="Rally Issue Note Append",
                            config={},
                            derived_contract_mode="readable_text",
                            readback_mode="unsupported",
                            shape_name="MarkdownDocument",
                            shape_title="Markdown Document",
                        ),
                    ),
                    output_bindings=(),
                ),
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousNote",
                            input_name="Previous Note",
                            selector_kind="output_decl",
                            selector_text="rally.base_agent.RallyIssueNote",
                            resolved_declaration_key="rally.base_agent.RallyIssueNote",
                            derived_contract_mode="readable_text",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )

            with self.assertRaisesRegex(RallyStateError, "Note-backed previous output reopen is not supported"):
                render_previous_turn_appendix(
                    workspace_root=repo_root,
                    run_home=run_home,
                    flow=flow,
                    agent=current_agent,
                    turn_index=2,
                )

    def test_render_previous_turn_appendix_marks_first_turn_advisory_input_as_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousTurnResult",
                            input_name="Previous Turn Result",
                            selector_kind="default_final_output",
                            selector_text="Exact previous final output",
                            resolved_declaration_key="SharedTurnResult",
                            derived_contract_mode="structured_json",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))

            appendix = render_previous_turn_appendix(
                workspace_root=repo_root,
                run_home=run_home,
                flow=flow,
                agent=current_agent,
                turn_index=1,
            )

            self.assertIn("No previous turn is available yet.", appendix)

    def test_render_previous_turn_appendix_fails_when_file_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "DMO-1" / "home"
            previous_agent = self._agent(
                repo_root=repo_root,
                key="01_source_agent",
                slug="source_agent",
                final_output_key="SharedTurnResult",
                io=IoContract(
                    previous_turn_inputs=(),
                    outputs=(
                        self._output(
                            declaration_key="DraftFile",
                            target_key="File",
                            target_title="File",
                            config={"path": "home:artifacts/missing.md"},
                            derived_contract_mode="readable_text",
                            readback_mode="readable_text",
                            shape_name="MarkdownDocument",
                            shape_title="Markdown Document",
                        ),
                    ),
                    output_bindings=(),
                ),
            )
            current_agent = self._agent(
                repo_root=repo_root,
                key="02_reader_agent",
                slug="reader_agent",
                final_output_key="ReaderTurnResult",
                io=IoContract(
                    previous_turn_inputs=(
                        self._request(
                            input_key="PreviousDraft",
                            input_name="Previous Draft",
                            selector_kind="output_decl",
                            selector_text="shared.outputs.DraftFile",
                            resolved_declaration_key="DraftFile",
                            derived_contract_mode="readable_text",
                        ),
                    ),
                    outputs=(),
                    output_bindings=(),
                ),
            )
            flow = self._flow(repo_root=repo_root, agents=(previous_agent, current_agent))
            self._write_previous_turn(
                run_home=run_home,
                agent_slug=previous_agent.slug,
                payload={
                    "kind": "done",
                    "summary": "ready",
                    "reason": None,
                    "sleep_duration_seconds": None,
                },
            )

            with self.assertRaisesRegex(RallyStateError, "artifact does not exist"):
                render_previous_turn_appendix(
                    workspace_root=repo_root,
                    run_home=run_home,
                    flow=flow,
                    agent=current_agent,
                    turn_index=2,
                )

    def _flow(self, *, repo_root: Path, agents: tuple[FlowAgent, ...]) -> FlowDefinition:
        return FlowDefinition(
            name="demo",
            code="DMO",
            root_dir=repo_root / "flows" / "demo",
            flow_file=repo_root / "flows" / "demo" / "flow.yaml",
            build_agents_dir=repo_root / "flows" / "demo" / "build" / "agents",
            setup_home_script=None,
            start_agent_key=agents[0].key,
            max_command_turns=8,
            guarded_git_repos=(),
            runtime_env={},
            host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
            agents={agent.key: agent for agent in agents},
            adapter=AdapterConfig(name="codex", args={}),
        )

    def _agent(
        self,
        *,
        repo_root: Path,
        key: str,
        slug: str,
        final_output_key: str,
        io: IoContract | None = None,
    ) -> FlowAgent:
        compiled = CompiledAgentContract(
            name="".join(part.title() for part in slug.split("_")),
            slug=slug,
            entrypoint=repo_root / "flows" / "demo" / "prompts" / f"{slug}.prompt",
            markdown_path=repo_root / "runs" / "DMO-1" / "home" / "agents" / slug / "AGENTS.md",
            metadata_file=repo_root / "flows" / "demo" / "build" / "agents" / slug / "final_output.contract.json",
            contract_version=1,
            final_output=FinalOutputContract(
                exists=True,
                contract_version=1,
                declaration_key=final_output_key,
                declaration_name=final_output_key,
                format_mode="json_object",
                schema_profile="OpenAIStructuredOutput",
                generated_schema_file=repo_root / "flows" / "demo" / "build" / "agents" / slug / "schema.json",
                metadata_file=repo_root / "flows" / "demo" / "build" / "agents" / slug / "final_output.contract.json",
            ),
            io=io,
        )
        return FlowAgent(
            key=key,
            slug=slug,
            timeout_sec=60,
            allowed_skills=(),
            system_skills=(),
            external_skills=(),
            allowed_mcps=(),
            compiled=compiled,
        )

    def _request(
        self,
        *,
        input_key: str,
        input_name: str,
        selector_kind: str,
        selector_text: str,
        resolved_declaration_key: str,
        derived_contract_mode: str,
        binding_path: tuple[str, ...] | None = None,
        shape_name: str | None = None,
        shape_title: str | None = None,
    ) -> PreviousTurnInputContract:
        return PreviousTurnInputContract(
            input_key=input_key,
            input_name=input_name,
            selector_kind=selector_kind,
            selector_text=selector_text,
            resolved_declaration_key=resolved_declaration_key,
            resolved_declaration_name=resolved_declaration_key,
            derived_contract_mode=derived_contract_mode,
            requirement="Advisory",
            target=None,
            shape=IoShapeContract(name=shape_name, title=shape_title) if shape_name and shape_title else None,
            schema=None,
            binding_path=binding_path,
        )

    def _output(
        self,
        *,
        declaration_key: str,
        target_key: str,
        target_title: str,
        config: dict[str, object],
        derived_contract_mode: str,
        readback_mode: str,
        shape_name: str | None = None,
        shape_title: str | None = None,
        requires_final_output: bool = False,
    ) -> EmittedOutputContract:
        return EmittedOutputContract(
            declaration_key=declaration_key,
            declaration_name=declaration_key,
            title=declaration_key,
            target=IoTargetContract(
                key=target_key,
                title=target_title,
                config=config,
            ),
            derived_contract_mode=derived_contract_mode,
            readback_mode=readback_mode,
            requires_final_output=requires_final_output,
            shape=IoShapeContract(name=shape_name, title=shape_title) if shape_name and shape_title else None,
            schema=None,
        )

    def _write_previous_turn(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        payload: dict[str, object],
    ) -> None:
        turn_dir = run_home / "sessions" / agent_slug / "turn-001"
        turn_dir.mkdir(parents=True, exist_ok=True)
        (turn_dir / "last_message.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
