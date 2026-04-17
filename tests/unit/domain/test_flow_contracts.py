from __future__ import annotations

import unittest
from dataclasses import fields
from pathlib import Path

from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
    flow_agent_key_to_slug,
)


class FlowContractsTests(unittest.TestCase):
    def test_flow_agent_key_to_slug_strips_numeric_prefix(self) -> None:
        self.assertEqual(flow_agent_key_to_slug("01_scope_lead"), "scope_lead")

    def test_flow_agent_key_to_slug_preserves_plain_slug(self) -> None:
        self.assertEqual(flow_agent_key_to_slug("change_engineer"), "change_engineer")

    def test_flow_definition_centers_runtime_on_compiled_agent_packages(self) -> None:
        flow_root = Path("/repo/flows/demo")
        build_agents_dir = flow_root / "build" / "agents"
        compiled_package_dir = build_agents_dir / "scope_lead"
        metadata_file = compiled_package_dir / "final_output.contract.json"
        final_output = FinalOutputContract(
            exists=True,
            contract_version=1,
            declaration_key="DemoTurnResult",
            declaration_name="DemoTurnResult",
            format_mode="json_object",
            schema_profile="OpenAIStructuredOutput",
            generated_schema_file=compiled_package_dir / "schemas" / "demo_turn_result.schema.json",
            metadata_file=metadata_file,
        )
        agent = FlowAgent(
            key="01_scope_lead",
            slug="scope_lead",
            timeout_sec=60,
            allowed_skills=(),
            system_skills=(),
            allowed_mcps=(),
            compiled=CompiledAgentContract(
                name="ScopeLead",
                slug="scope_lead",
                entrypoint=flow_root / "prompts" / "AGENTS.prompt",
                markdown_path=compiled_package_dir / "AGENTS.md",
                metadata_file=metadata_file,
                contract_version=1,
                final_output=final_output,
            ),
        )
        flow = FlowDefinition(
            name="demo",
            code="DMO",
            root_dir=flow_root,
            flow_file=flow_root / "flow.yaml",
            build_agents_dir=build_agents_dir,
            setup_home_script=None,
            start_agent_key=agent.key,
            max_command_turns=8,
            guarded_git_repos=(),
            runtime_env={},
            host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
            agents={agent.key: agent},
            adapter=AdapterConfig(name="codex", args={}),
        )

        self.assertEqual(flow.build_agents_dir, build_agents_dir)
        self.assertEqual(flow.agent(agent.key), agent)
        self.assertEqual(flow.agent_by_slug(agent.slug), agent)
        self.assertEqual(agent.compiled.markdown_path.parent, compiled_package_dir)
        self.assertEqual(agent.compiled.metadata_file.parent, compiled_package_dir)
        self.assertEqual(agent.compiled.final_output.metadata_file, agent.compiled.metadata_file)

    def test_flow_definition_no_longer_exposes_flow_level_prompt_entrypoint(self) -> None:
        field_names = {field.name for field in fields(FlowDefinition)}

        self.assertIn("build_agents_dir", field_names)
        self.assertNotIn("prompt_entrypoint", field_names)

    def test_adapter_config_no_longer_exposes_prompt_input_command(self) -> None:
        field_names = {field.name for field in fields(AdapterConfig)}

        self.assertEqual(field_names, {"name", "args"})


if __name__ == "__main__":
    unittest.main()
