from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

from rally.adapters.claude_code.adapter import CLAUDE_CODE_ADAPTER, _build_mcp_config, _write_claude_mcp_config
from rally.adapters.codex.adapter import CODEX_ADAPTER, _write_codex_config
from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
)
from rally.domain.run import RunRecord
from rally.services.run_events import RunEventRecorder
from rally.services.workspace import WorkspaceContext


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
                    command = "uv"
                    args = ["run", "fixture-repo-mcp", "--repo", "home:repos/demo_repo"]
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

            self.assertIn("project_doc_max_bytes = 0", config_text)
            self.assertIn('command = "uv"', config_text)
            self.assertIn(
                f'args = ["run", "fixture-repo-mcp", "--repo", "{run_home / "repos" / "demo_repo"}"]',
                config_text,
            )
            self.assertIn(f'cwd = "{expected_cwd}"', config_text)
            self.assertIn("required = true", config_text)

    def test_codex_readiness_uses_run_home_codex_home_when_servers_are_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body=(
                    'command = "uv"\n'
                    'args = ["run", "fixture-repo-mcp", "--repo", "home:repos/demo_repo"]\n'
                    'cwd = "host:/tmp/fixture-repo"\n'
                    'transport = "stdio"\n'
                ),
            )
            flow = _demo_flow(
                workspace_root=workspace_root,
                allowed_mcps=("fixture-repo",),
                runtime_env={"PROJECT_ROOT": "workspace:fixtures/project"},
            )
            _write_codex_config(workspace_root=workspace_root, run_home=run_home, flow=flow)

            fake_subprocess = _FakeCodexReadinessSubprocess()
            failure = CODEX_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            self.assertIsNone(failure)
            self.assertEqual(fake_subprocess.codex_home_values, {str(run_home.resolve())})
            self.assertEqual(fake_subprocess.flow_env_values, {str(workspace_root / "fixtures" / "project")})
            self.assertEqual(fake_subprocess.codex_commands[:2], [["codex", "mcp", "list", "--json"], ["codex", "mcp", "get", "fixture-repo", "--json"]])

    def test_codex_readiness_reports_run_home_materialization_when_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body='command = "uv"\nargs = ["run", "fixture-repo-mcp"]\ntransport = "stdio"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",))
            fake_subprocess = _FakeCodexReadinessSubprocess()

            failure = CODEX_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "run_home_materialization")
            self.assertFalse(fake_subprocess.calls)

    def test_codex_readiness_reports_codex_config_visibility_when_get_lacks_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body='command = "uv"\nargs = ["run", "fixture-repo-mcp"]\ntransport = "stdio"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",))
            _write_codex_config(workspace_root=workspace_root, run_home=run_home, flow=flow)

            fake_subprocess = _FakeCodexReadinessSubprocess(get_payload_overrides={"fixture-repo": {"name": "fixture-repo"}})
            failure = CODEX_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "codex_config_visibility")
            self.assertEqual(failure.mcp_name, "fixture-repo")

    def test_codex_readiness_reports_codex_auth_status_for_non_usable_streamable_http_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="issues-http",
                body='url = "https://example.com/issues"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("issues-http",))
            _write_codex_config(workspace_root=workspace_root, run_home=run_home, flow=flow)

            fake_subprocess = _FakeCodexReadinessSubprocess(auth_status_by_name={"issues-http": "unsupported"})
            failure = CODEX_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "codex_auth_status")
            self.assertEqual(failure.mcp_name, "issues-http")
            self.assertIn("unsupported", failure.reason)

    def test_codex_readiness_reports_command_startability_when_stdio_command_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body='command = "missing-fixture-mcp"\nargs = ["--repo", "home:repos/demo_repo"]\ntransport = "stdio"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",))
            _write_codex_config(workspace_root=workspace_root, run_home=run_home, flow=flow)

            fake_subprocess = _FakeCodexReadinessSubprocess()
            failure = CODEX_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "command_startability")
            self.assertEqual(failure.mcp_name, "fixture-repo")
            self.assertIn("missing-fixture-mcp", failure.reason)

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

    def test_claude_readiness_reports_run_home_materialization_when_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body='command = "uv"\nargs = ["run", "fixture-repo-mcp"]\ntransport = "stdio"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",), adapter_name="claude_code")
            fake_subprocess = _FakeClaudeReadinessSubprocess()

            failure = CLAUDE_CODE_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(adapter_name="claude_code"),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            # Rally must block before launch when the Claude bootstrap file is
            # missing, because the user cannot recover from a hidden adapter
            # config failure after the turn has already started.
            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "run_home_materialization")
            self.assertFalse(fake_subprocess.calls)

    def test_claude_readiness_uses_generated_mcp_config_when_servers_are_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body=(
                    'command = "uv"\n'
                    'args = ["run", "fixture-repo-mcp", "--repo", "home:repos/demo_repo"]\n'
                    'cwd = "host:/tmp/fixture-repo"\n'
                    'transport = "stdio"\n'
                ),
            )
            flow = _demo_flow(
                workspace_root=workspace_root,
                allowed_mcps=("fixture-repo",),
                adapter_name="claude_code",
                runtime_env={"PROJECT_ROOT": "workspace:fixtures/project"},
            )
            _write_claude_mcp_config(workspace_root=workspace_root, run_home=run_home, flow=flow)
            fake_subprocess = _FakeClaudeReadinessSubprocess()

            failure = CLAUDE_CODE_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(adapter_name="claude_code"),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            # A healthy Claude readiness probe should treat a timed-out stdio
            # launcher as "started" and use the generated run-home config.
            self.assertIsNone(failure)
            self.assertEqual(fake_subprocess.commands, [["uv", "run", "fixture-repo-mcp", "--repo", str(run_home / "repos" / "demo_repo")]])
            self.assertEqual(fake_subprocess.cwd_values, {str(Path("/tmp/fixture-repo").resolve(strict=False))})
            self.assertEqual(fake_subprocess.flow_env_values, {str(workspace_root / "fixtures" / "project")})

    def test_claude_readiness_reports_command_startability_when_stdio_command_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            run_dir = workspace_root / "runs" / "DMO-1"
            run_home = run_dir / "home"
            _write_server_toml(
                run_home=run_home,
                mcp_name="fixture-repo",
                body='command = "missing-fixture-mcp"\nargs = ["--repo", "home:repos/demo_repo"]\ntransport = "stdio"\n',
            )
            flow = _demo_flow(workspace_root=workspace_root, allowed_mcps=("fixture-repo",), adapter_name="claude_code")
            _write_claude_mcp_config(workspace_root=workspace_root, run_home=run_home, flow=flow)
            fake_subprocess = _FakeClaudeReadinessSubprocess()

            failure = CLAUDE_CODE_ADAPTER.check_turn_readiness(
                repo_root=workspace_root,
                workspace=_demo_workspace_context(workspace_root=workspace_root),
                run_dir=run_dir,
                run_home=run_home,
                flow=flow,
                run_record=_demo_run_record(adapter_name="claude_code"),
                agent=next(iter(flow.agents.values())),
                turn_index=1,
                recorder=RunEventRecorder(run_dir=run_dir, run_id="DMO-1", flow_code="DMO"),
                subprocess_run=fake_subprocess,
            )

            # A missing required MCP launcher should block before Rally invokes
            # Claude, so the operator sees a clear MCP failure instead of a
            # generic adapter crash later in the turn.
            self.assertIsNotNone(failure)
            assert failure is not None
            self.assertEqual(failure.failed_check, "command_startability")
            self.assertEqual(failure.mcp_name, "fixture-repo")
            self.assertIn("missing-fixture-mcp", failure.reason)


def _demo_flow(
    *,
    workspace_root: Path,
    allowed_mcps: tuple[str, ...],
    adapter_name: str = "codex",
    runtime_env: dict[str, str] | None = None,
) -> FlowDefinition:
    flow_root = workspace_root / "flows" / "demo"
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
        system_skills=(),
        external_skills=(),
        allowed_mcps=allowed_mcps,
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
        build_agents_dir=flow_root / "build" / "agents",
        setup_home_script=None,
        start_agent_key=agent.key,
        max_command_turns=8,
        guarded_git_repos=(),
        runtime_env=runtime_env or {},
        host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
        agents={agent.key: agent},
        adapter=AdapterConfig(name=adapter_name, args={}),
    )


def _write_server_toml(*, run_home: Path, mcp_name: str, body: str) -> None:
    server_root = run_home / "mcps" / mcp_name
    server_root.mkdir(parents=True, exist_ok=True)
    (server_root / "server.toml").write_text(body, encoding="utf-8")


def _demo_run_record(*, adapter_name: str = "codex") -> RunRecord:
    return RunRecord(
        id="DMO-1",
        flow_name="demo",
        flow_code="DMO",
        adapter_name=adapter_name,
        start_agent_key="01_scope_lead",
        created_at="2026-04-14T00:00:00Z",
    )


def _demo_workspace_context(*, workspace_root: Path) -> WorkspaceContext:
    return WorkspaceContext(
        workspace_root=workspace_root,
        pyproject_path=workspace_root / "pyproject.toml",
        flows_dir=workspace_root / "flows",
        skills_dir=workspace_root / "skills",
        mcps_dir=workspace_root / "mcps",
        stdlib_dir=workspace_root / "stdlib",
        runs_dir=workspace_root / "runs",
        cli_bin=Path("/usr/bin/rally"),
    )


class _FakeCodexReadinessSubprocess:
    def __init__(
        self,
        *,
        auth_status_by_name: dict[str, str] | None = None,
        get_payload_overrides: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.auth_status_by_name = auth_status_by_name or {}
        self.get_payload_overrides = get_payload_overrides or {}
        self.calls: list[dict[str, object]] = []
        self.codex_commands: list[list[str]] = []
        self.codex_home_values: set[str] = set()
        self.flow_env_values: set[str] = set()

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": command, "kwargs": kwargs})
        if command[:3] == ["codex", "mcp", "list"]:
            return self._handle_mcp_list(command=command, kwargs=kwargs)
        if command[:3] == ["codex", "mcp", "get"]:
            return self._handle_mcp_get(command=command, kwargs=kwargs)
        executable = command[0]
        if executable.startswith("missing-"):
            raise FileNotFoundError(executable)
        raise subprocess.TimeoutExpired(cmd=command, timeout=float(kwargs["timeout"]))

    def _handle_mcp_list(self, *, command: list[str], kwargs: dict[str, object]) -> subprocess.CompletedProcess[str]:
        self._record_codex_call(command=command, kwargs=kwargs)
        payload = [
            {
                "name": name,
                "enabled": True,
                "disabled_reason": None,
                "transport": self._render_transport(server),
                "startup_timeout_sec": server.get("startup_timeout_sec"),
                "tool_timeout_sec": server.get("tool_timeout_sec"),
                "auth_status": self.auth_status_by_name.get(name, "unsupported" if server.get("command") else "oauth"),
            }
            for name, server in self._load_mcp_servers(kwargs).items()
        ]
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=json.dumps(payload), stderr="")

    def _handle_mcp_get(self, *, command: list[str], kwargs: dict[str, object]) -> subprocess.CompletedProcess[str]:
        self._record_codex_call(command=command, kwargs=kwargs)
        server_name = command[3]
        if server_name in self.get_payload_overrides:
            payload = self.get_payload_overrides[server_name]
        else:
            servers = self._load_mcp_servers(kwargs)
            payload = {
                "name": server_name,
                "enabled": True,
                "disabled_reason": None,
                "transport": self._render_transport(servers[server_name]),
                "enabled_tools": None,
                "disabled_tools": None,
                "startup_timeout_sec": servers[server_name].get("startup_timeout_sec"),
                "tool_timeout_sec": servers[server_name].get("tool_timeout_sec"),
            }
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=json.dumps(payload), stderr="")

    def _record_codex_call(self, *, command: list[str], kwargs: dict[str, object]) -> None:
        self.codex_commands.append(command)
        env = kwargs["env"]
        assert isinstance(env, dict)
        self.codex_home_values.add(str(env["CODEX_HOME"]))
        project_root = env.get("PROJECT_ROOT")
        if isinstance(project_root, str):
            self.flow_env_values.add(project_root)
        assert Path(str(kwargs["cwd"])).resolve() == Path(str(env["CODEX_HOME"])).resolve()

    @staticmethod
    def _load_mcp_servers(kwargs: dict[str, object]) -> dict[str, dict[str, object]]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        config = tomllib.loads((Path(str(env["CODEX_HOME"])) / "config.toml").read_text(encoding="utf-8"))
        servers = config.get("mcp_servers")
        assert isinstance(servers, dict)
        return {
            str(name): server
            for name, server in servers.items()
            if isinstance(name, str) and isinstance(server, dict)
        }

    @staticmethod
    def _render_transport(server: dict[str, object]) -> dict[str, object]:
        if isinstance(server.get("url"), str):
            return {
                "type": "streamable_http",
                "url": server["url"],
                "bearer_token_env_var": server.get("bearer_token_env_var"),
                "http_headers": server.get("http_headers"),
                "env_http_headers": server.get("env_http_headers"),
            }
        raw_args = server.get("args")
        args = raw_args if isinstance(raw_args, list) else []
        return {
            "type": "stdio",
            "command": server.get("command"),
            "args": args,
            "env": server.get("env"),
            "env_vars": server.get("env_vars") if isinstance(server.get("env_vars"), list) else [],
            "cwd": server.get("cwd"),
        }


class _FakeClaudeReadinessSubprocess:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.commands: list[list[str]] = []
        self.cwd_values: set[str] = set()
        self.flow_env_values: set[str] = set()

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": command, "kwargs": kwargs})
        self.commands.append(command)
        self.cwd_values.add(str(Path(str(kwargs["cwd"])).resolve(strict=False)))
        env = kwargs.get("env")
        assert isinstance(env, dict)
        project_root = env.get("PROJECT_ROOT")
        if isinstance(project_root, str):
            self.flow_env_values.add(project_root)
        executable = command[0]
        if executable.startswith("missing-"):
            raise FileNotFoundError(executable)
        raise subprocess.TimeoutExpired(cmd=command, timeout=float(kwargs["timeout"]))


if __name__ == "__main__":
    unittest.main()
