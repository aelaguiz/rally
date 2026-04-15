from __future__ import annotations

import tempfile
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path

from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
)
from rally.errors import RallyStateError
from rally.services.run_store import archive_run, create_run, list_active_run_records, load_run_record


class RunStoreTests(unittest.TestCase):
    def test_create_run_omits_legacy_brief_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            flow = _demo_flow(repo_root=repo_root)

            record = create_run(repo_root=repo_root, flow=flow)

            run_yaml = (repo_root / "runs" / "active" / record.id / "run.yaml").read_text(encoding="utf-8")
            self.assertNotIn("brief_file", run_yaml)
            self.assertIn("issue_file: home/issue.md", run_yaml)

    def test_load_run_record_tolerates_legacy_brief_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "active" / "DMO-7"
            run_dir.mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: DMO-7
                    flow_name: demo
                    flow_code: DMO
                    adapter_name: codex
                    start_agent_key: 01_scope_lead
                    brief_file: /tmp/legacy-brief.md
                    created_at: "2026-04-13T00:00:00Z"
                    issue_file: home/issue.md
                    """
                ),
                encoding="utf-8",
            )

            record = load_run_record(run_dir=run_dir)

            self.assertEqual(record.id, "DMO-7")
            self.assertEqual(record.flow_name, "demo")
            self.assertEqual(record.issue_file, "home/issue.md")

    def test_load_run_record_rejects_invalid_flow_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "active" / "DMO-7"
            run_dir.mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: DMO-7
                    flow_name: demo
                    flow_code: DEMO
                    adapter_name: codex
                    start_agent_key: 01_scope_lead
                    created_at: "2026-04-13T00:00:00Z"
                    issue_file: home/issue.md
                    """
                ),
                encoding="utf-8",
            )

            # Resume should fail on a bad stored flow code before it builds lock
            # paths or adapter env from that value.
            with self.assertRaisesRegex(RallyStateError, "exactly three uppercase ASCII letters"):
                load_run_record(run_dir=run_dir)

    def test_archive_run_moves_active_run_to_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            flow = _demo_flow(repo_root=repo_root)

            record = create_run(repo_root=repo_root, flow=flow)
            archived_dir = archive_run(repo_root=repo_root, run_id=record.id)

            self.assertFalse((repo_root / "runs" / "active" / record.id).exists())
            self.assertEqual(archived_dir, repo_root / "runs" / "archive" / record.id)
            self.assertTrue((archived_dir / "run.yaml").is_file())
            self.assertTrue((archived_dir / "state.yaml").is_file())

    def test_create_run_after_archive_uses_next_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            flow = _demo_flow(repo_root=repo_root)

            first = create_run(repo_root=repo_root, flow=flow)
            archive_run(repo_root=repo_root, run_id=first.id)
            second = create_run(repo_root=repo_root, flow=flow)

            self.assertEqual(first.id, "DMO-1")
            self.assertEqual(second.id, "DMO-2")

    def test_list_active_run_records_returns_sorted_active_runs_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            flow = _demo_flow(repo_root=repo_root)

            first = create_run(repo_root=repo_root, flow=flow)
            second = create_run(repo_root=repo_root, flow=replace(flow, code="POM", name="poem"))
            archive_run(repo_root=repo_root, run_id=first.id)

            records = list_active_run_records(repo_root=repo_root)

            self.assertEqual([record.id for record in records], [second.id])


def _demo_flow(*, repo_root: Path) -> FlowDefinition:
    flow_root = repo_root / "flows" / "demo"
    prompt_path = flow_root / "prompts" / "AGENTS.prompt"
    markdown_path = flow_root / "build" / "agents" / "scope_lead" / "AGENTS.md"
    metadata_file = flow_root / "build" / "agents" / "scope_lead" / "final_output.contract.json"
    final_output = FinalOutputContract(
        exists=True,
        contract_version=1,
        declaration_key="DemoTurnResult",
        declaration_name="DemoTurnResult",
        format_mode="json_object",
        schema_profile="OpenAIStructuredOutput",
        generated_schema_file=flow_root
        / "build"
        / "agents"
        / "scope_lead"
        / "schemas"
        / "rally_turn_result.schema.json",
        metadata_file=metadata_file,
    )
    agent = FlowAgent(
        key="01_scope_lead",
        slug="scope_lead",
        timeout_sec=60,
        allowed_skills=(),
        allowed_mcps=(),
        compiled=CompiledAgentContract(
            name="ScopeLead",
            slug="scope_lead",
            entrypoint=prompt_path,
            markdown_path=markdown_path,
            metadata_file=metadata_file,
            contract_version=1,
            final_output=final_output,
        ),
    )
    return FlowDefinition(
        name="demo",
        code="DMO",
        root_dir=flow_root,
        flow_file=flow_root / "flow.yaml",
        prompt_entrypoint=prompt_path,
        build_agents_dir=flow_root / "build" / "agents",
        setup_home_script=None,
        start_agent_key=agent.key,
        max_command_turns=8,
        guarded_git_repos=(),
        runtime_env={},
        host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
        agents={agent.key: agent},
        adapter=AdapterConfig(name="codex", args={}),
    )


if __name__ == "__main__":
    unittest.main()
