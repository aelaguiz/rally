from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
)
from rally.domain.run import RunRecord
from rally.services.home_materializer import prepare_interview_home
from rally.services.run_store import create_run, load_run_state
from rally.services.workspace import workspace_context_from_root


class PrepareInterviewHomeTests(unittest.TestCase):
    def test_prepare_interview_home_skips_issue_gate_and_run_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow = _demo_flow(repo_root=repo_root)
            record = create_run(repo_root=repo_root, flow=flow)
            run_dir = repo_root / "runs" / "active" / record.id
            state_before = (run_dir / "state.yaml").read_text(encoding="utf-8")
            adapter_calls: list[tuple[Path, str]] = []

            class _StubAdapter:
                def prepare_home(
                    self,
                    *,
                    repo_root: Path,
                    workspace,
                    run_home: Path,
                    flow: FlowDefinition,
                    run_record: RunRecord,
                    event_recorder,
                ) -> None:
                    del workspace, flow, event_recorder
                    adapter_calls.append((run_home, run_record.id))

            with (
                patch("rally.services.home_materializer.sync_workspace_builtins"),
                patch("rally.services.home_materializer._refresh_agent_skill_views"),
                patch("rally.services.home_materializer._copy_allowed_mcps"),
                patch("rally.services.home_materializer.get_adapter", return_value=_StubAdapter()),
            ):
                run_home = prepare_interview_home(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    flow=flow,
                    run_record=record,
                )

            self.assertEqual(run_home, run_dir / "home")
            self.assertTrue((run_home / "interviews").is_dir())
            self.assertTrue((run_home / "agents" / "scope_lead" / "AGENTS.md").is_file())
            self.assertTrue((run_home / "agents" / "scope_lead" / "INTERVIEW.md").is_file())
            self.assertFalse((run_home / "issue.md").exists())
            self.assertFalse((run_home / ".rally_home_ready").exists())
            self.assertEqual(adapter_calls, [(run_home, record.id)])
            self.assertEqual((run_dir / "state.yaml").read_text(encoding="utf-8"), state_before)
            self.assertEqual(load_run_state(run_dir=run_dir).turn_index, 0)


def _demo_flow(*, repo_root: Path) -> FlowDefinition:
    flow_root = repo_root / "flows" / "demo"
    prompt_path = flow_root / "prompts" / "AGENTS.prompt"
    agent_dir = flow_root / "build" / "agents" / "scope_lead"
    agent_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = agent_dir / "AGENTS.md"
    markdown_path.write_text("compiled agent\n", encoding="utf-8")
    (agent_dir / "INTERVIEW.md").write_text("compiled interview\n", encoding="utf-8")
    contract_path = agent_dir / "AGENTS.contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    final_output = FinalOutputContract(
        exists=True,
        declaration_key="DemoTurnResult",
        declaration_name="DemoTurnResult",
        format_mode="json_schema",
        schema_profile="OpenAIStructuredOutput",
        schema_file=repo_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json",
        example_file=repo_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json",
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
            contract_path=contract_path,
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
        host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
        agents={agent.key: agent},
        adapter=AdapterConfig(name="codex", prompt_input_command=None, args={}),
    )


if __name__ == "__main__":
    unittest.main()
