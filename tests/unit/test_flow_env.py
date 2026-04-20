from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rally.domain.flow import AdapterConfig, FlowDefinition, FlowHostInputs
from rally.errors import RallyConfigError
from rally.services.flow_env import build_flow_subprocess_env, resolve_flow_runtime_env
from rally.services.workspace import WorkspaceContext


def _make_workspace(workspace_root: Path) -> WorkspaceContext:
    return WorkspaceContext(
        workspace_root=workspace_root,
        pyproject_path=workspace_root / "pyproject.toml",
        flows_dir=workspace_root / "flows",
        skills_dir=workspace_root / "skills",
        mcps_dir=workspace_root / "mcps",
        stdlib_dir=workspace_root / "stdlib",
        runs_dir=workspace_root / "runs",
        cli_bin=workspace_root / "bin" / "rally",
    )


def _make_flow(*, flow_root: Path, runtime_env: dict[str, str], guarded: tuple[Path, ...] = ()) -> FlowDefinition:
    return FlowDefinition(
        name="demo",
        code="DMO",
        root_dir=flow_root,
        flow_file=flow_root / "flow.yaml",
        build_agents_dir=flow_root / "build" / "agents",
        setup_home_script=None,
        start_agent_key="01_demo_agent",
        max_command_turns=8,
        guarded_git_repos=guarded,
        runtime_env=runtime_env,
        host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
        agents={},
        adapter=AdapterConfig(name="codex", args={}),
    )


class ResolveFlowRuntimeEnvTests(unittest.TestCase):
    # Protects the contract that each rooted root in runtime.env resolves against
    # the correct base. If home/flow/workspace/host drift, flows silently launch
    # with paths pointing at the wrong tree — hard for an operator to see.

    def test_home_flow_workspace_roots_resolve_against_their_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "runs" / "active" / "DMO-1" / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={
                    "RALLY_ISSUE": "home:issue.md",
                    "FLOW_FIXTURE": "flow:fixtures/project",
                    "WORKSPACE_PY": "workspace:pyproject.toml",
                },
            )
            workspace = _make_workspace(workspace_root)

            env = resolve_flow_runtime_env(flow=flow, workspace=workspace, run_home=run_home)

            self.assertEqual(env["RALLY_ISSUE"], str(run_home / "issue.md"))
            self.assertEqual(env["FLOW_FIXTURE"], str(flow_root / "fixtures" / "project"))
            self.assertEqual(env["WORKSPACE_PY"], str(workspace_root / "pyproject.toml"))

    def test_host_root_expands_env_var_against_os_environ(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={"RALLY_TOOL": "host:$RALLY_TEST_TOOL_BIN/bin/tool"},
            )
            workspace = _make_workspace(workspace_root)

            with patch.dict("os.environ", {"RALLY_TEST_TOOL_BIN": "/opt/rally-test"}, clear=False):
                env = resolve_flow_runtime_env(flow=flow, workspace=workspace, run_home=run_home)

            self.assertEqual(env["RALLY_TOOL"], "/opt/rally-test/bin/tool")

    def test_stdlib_root_is_rejected_for_runtime_env(self) -> None:
        # stdlib: is valid for Rally internals but intentionally excluded from
        # flow runtime.env. A flow pulling stdlib paths through env would couple
        # itself to Rally's internal layout.
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={"RALLY_STDLIB": "stdlib:prompts/foo.prompt"},
            )
            workspace = _make_workspace(workspace_root)

            with self.assertRaises(RallyConfigError) as ctx:
                resolve_flow_runtime_env(flow=flow, workspace=workspace, run_home=run_home)
            self.assertIn("runtime.env.RALLY_STDLIB", str(ctx.exception))


class BuildFlowSubprocessEnvTests(unittest.TestCase):
    # Protects the subprocess env layering: base < flow runtime.env < extra_env.
    # An adapter depending on this order would otherwise launch with stale or
    # wrong values without any loud failure.

    def test_flow_runtime_env_overrides_base_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={"RALLY_ISSUE": "home:issue.md", "SHARED": "flow:shared"},
            )
            workspace = _make_workspace(workspace_root)

            env = build_flow_subprocess_env(
                flow=flow,
                workspace=workspace,
                run_home=run_home,
                base_env={"SHARED": "from-base", "OTHER": "kept"},
            )

            self.assertEqual(env["SHARED"], str(flow_root / "shared"))
            self.assertEqual(env["OTHER"], "kept")
            self.assertEqual(env["RALLY_ISSUE"], str(run_home / "issue.md"))

    def test_extra_env_overrides_flow_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={"RALLY_ISSUE": "home:issue.md"},
            )
            workspace = _make_workspace(workspace_root)

            env = build_flow_subprocess_env(
                flow=flow,
                workspace=workspace,
                run_home=run_home,
                base_env={},
                extra_env={"RALLY_ISSUE": "/explicit/override.md"},
            )

            self.assertEqual(env["RALLY_ISSUE"], "/explicit/override.md")

    def test_merge_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            flow_root = workspace_root / "flows" / "demo"
            flow_root.mkdir(parents=True)
            run_home = workspace_root / "home"
            run_home.mkdir(parents=True)

            flow = _make_flow(
                flow_root=flow_root,
                runtime_env={"RALLY_ISSUE": "home:issue.md"},
            )
            workspace = _make_workspace(workspace_root)

            first = build_flow_subprocess_env(
                flow=flow,
                workspace=workspace,
                run_home=run_home,
                base_env={"BASE": "1"},
                extra_env={"EXTRA": "2"},
            )
            second = build_flow_subprocess_env(
                flow=flow,
                workspace=workspace,
                run_home=run_home,
                base_env={"BASE": "1"},
                extra_env={"EXTRA": "2"},
            )

            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
