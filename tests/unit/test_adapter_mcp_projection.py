from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.adapters.claude_code.adapter import _build_mcp_config
from rally.adapters.codex.adapter import _write_codex_config
from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
)


class AdapterMcpProjectionTests(unittest.TestCase):
    def test_codex_writes_config_from_run_home_mcp_copy_and_expands_rooted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_home = workspace_root / "runs" / "DMO-1" / "home"
            expected_cwd = str(Path("/tmp/fixture-repo").resolve(strict=False))
            server_root = run_home / "mcps" / "fixture-repo"
            server_root.mkdir(parents=True)
            (server_root / "server.toml").write_text(
                textwrap.dedent(
                    """\
                    command = "uvx"
                    args = ["fixture-repo-mcp", "--repo", "home:repos/demo_repo"]
                    cwd = "host:/tmp/fixture-repo"
                    transport = "stdio"
                    """
                ),
                encoding="utf-8",
            )

            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",))

            _write_codex_config(
                workspace_root=workspace_root,
                run_home=run_home,
                flow=flow,
            )

            config_text = (run_home / "config.toml").read_text(encoding="utf-8")

            self.assertIn('command = "uvx"', config_text)
            self.assertIn(
                f'args = ["fixture-repo-mcp", "--repo", "{run_home / "repos" / "demo_repo"}"]',
                config_text,
            )
            self.assertIn(f'cwd = "{expected_cwd}"', config_text)

    def test_claude_builds_mcp_config_from_run_home_mcp_copy_and_expands_rooted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_home = workspace_root / "runs" / "DMO-1" / "home"
            expected_cwd = str(Path("/tmp/fixture-repo").resolve(strict=False))
            server_root = run_home / "mcps" / "fixture-repo"
            server_root.mkdir(parents=True)
            (server_root / "server.toml").write_text(
                textwrap.dedent(
                    """\
                    command = "uvx"
                    args = ["fixture-repo-mcp", "--repo", "home:repos/demo_repo"]
                    cwd = "host:/tmp/fixture-repo"
                    transport = "stdio"
                    env = { PROJECT_ROOT = "workspace:fixtures/project" }
                    """
                ),
                encoding="utf-8",
            )

            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",))

            config = _build_mcp_config(
                workspace_root=workspace_root,
                run_home=run_home,
                flow=flow,
            )

            server = config["mcpServers"]["fixture-repo"]
            self.assertEqual(server["command"], "uvx")
            self.assertEqual(
                server["args"],
                ["fixture-repo-mcp", "--repo", str(run_home / "repos" / "demo_repo")],
            )
            self.assertEqual(server["cwd"], expected_cwd)
            self.assertEqual(
                server["env"]["PROJECT_ROOT"],
                str(workspace_root / "fixtures" / "project"),
            )


def _demo_flow(*, workspace_root: Path, allowed_mcps: tuple[str, ...]) -> FlowDefinition:
    flow_root = workspace_root / "flows" / "demo"
    prompt_path = flow_root / "prompts" / "AGENTS.prompt"
    markdown_path = flow_root / "build" / "agents" / "scope_lead" / "AGENTS.md"
    contract_path = flow_root / "build" / "agents" / "scope_lead" / "AGENTS.contract.json"
    final_output = FinalOutputContract(
        exists=True,
        declaration_key="DemoTurnResult",
        declaration_name="DemoTurnResult",
        format_mode="json_schema",
        schema_profile="OpenAIStructuredOutput",
        schema_file=workspace_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json",
        example_file=workspace_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json",
    )
    agent = FlowAgent(
        key="01_scope_lead",
        slug="scope_lead",
        timeout_sec=60,
        allowed_skills=(),
        allowed_mcps=allowed_mcps,
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
