from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.flow_build import ensure_flow_assets_built
from rally.services.workspace import workspace_context_from_root


class FlowBuildTests(unittest.TestCase):
    def test_ensure_flow_assets_built_runs_doctrine_emit_docs_for_flow_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0]["command"],
                [
                    sys.executable,
                    "-m",
                    "doctrine.emit_docs",
                    "--pyproject",
                    str(repo_root / "pyproject.toml"),
                    "--target",
                    "demo",
                ],
            )
            self.assertEqual(calls[0]["kwargs"]["cwd"], repo_root)
            self.assertTrue(calls[0]["kwargs"]["capture_output"])
            self.assertTrue(calls[0]["kwargs"]["text"])
            self.assertFalse(calls[0]["kwargs"]["check"])

    def test_ensure_flow_assets_built_runs_doctrine_emit_skill_for_doctrine_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'workspace'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=("demo-git", "repo-search"))
            self._write_doctrine_skill(repo_root=repo_root, skill_name="demo-git")
            self._write_markdown_skill(repo_root=repo_root, skill_name="repo-search")
            self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-memory")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(calls), 2)
            self.assertEqual(
                calls[0]["command"],
                [
                    sys.executable,
                    "-m",
                    "doctrine.emit_docs",
                    "--pyproject",
                    str(repo_root / "pyproject.toml"),
                    "--target",
                    "demo",
                ],
            )
            self.assertEqual(
                calls[1]["command"],
                [
                    sys.executable,
                    "-m",
                    "doctrine.emit_skill",
                    "--pyproject",
                    str(repo_root / "pyproject.toml"),
                    "--target",
                    "demo-git",
                ],
            )

    def test_ensure_flow_assets_built_emits_mandatory_doctrine_skills_in_rally_source_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text(
                "[project]\nname = 'rally'\n\n[tool.rally.workspace]\nversion = 1\n",
                encoding="utf-8",
            )
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-memory")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            # In the Rally source workspace, edits to built-in Doctrine skills
            # must rebuild their emitted bundles so live runs do not keep stale
            # `build/SKILL.md` output.
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["command"][2], "doctrine.emit_docs")
            self.assertEqual(
                calls[1]["command"],
                [
                    sys.executable,
                    "-m",
                    "doctrine.emit_skill",
                    "--pyproject",
                    str(repo_root / "pyproject.toml"),
                    "--target",
                    "rally-kernel",
                    "--target",
                    "rally-memory",
                ],
            )

    def test_ensure_flow_assets_built_skips_builtin_skill_emit_in_external_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "workspace"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'workspace'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=workspace_context_from_root(
                    repo_root,
                    cli_bin=repo_root / "bin" / "rally",
                ),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["command"][2], "doctrine.emit_docs")
            self.assertTrue((repo_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((repo_root / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertTrue((repo_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").is_file())

    def test_ensure_flow_assets_built_rejects_missing_workspace_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)

            with self.assertRaisesRegex(RallyConfigError, "workspace pyproject is missing"):
                ensure_flow_assets_built(repo_root=repo_root, flow_name="demo")

    def test_ensure_flow_assets_built_surfaces_emit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del kwargs
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr="Emit target `demo` is not defined in `pyproject.toml`.",
                )

            with self.assertRaisesRegex(RallyConfigError, "Emit target `demo` is not defined"):
                ensure_flow_assets_built(
                    workspace=self._workspace(repo_root),
                    flow_name="demo",
                    subprocess_run=fake_run,
                )

    def test_ensure_flow_assets_built_rejects_ambiguous_skill_source_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")
            self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-kernel")

            with self.assertRaisesRegex(RallyConfigError, "must define exactly one source kind"):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_rejects_skill_without_supported_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            (repo_root / "skills" / "rally-kernel").mkdir(parents=True)
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")

            with self.assertRaisesRegex(RallyConfigError, "must define either"):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_rejects_bare_relative_prompt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")

            prompt_root = repo_root / "flows" / "demo" / "prompts"
            prompt_root.mkdir(parents=True, exist_ok=True)
            (prompt_root / "AGENTS.prompt").write_text(
                textwrap.dedent(
                    """\
                    input IssueLedger: "Issue Ledger"
                        source: File
                            path: "issue.md"
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyConfigError, "rooted Rally path"):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_allows_symbolic_artifact_prompt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")

            prompt_root = repo_root / "flows" / "demo" / "prompts"
            prompt_root.mkdir(parents=True, exist_ok=True)
            (prompt_root / "AGENTS.prompt").write_text(
                textwrap.dedent(
                    """\
                    output SectionPlan: "Section Plan"
                        target: File
                            path: "section_root/_authoring/SECTION_PLAN.md"
                        shape: MarkdownDocument
                        requirement: Required
                    """
                ),
                encoding="utf-8",
            )
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["command"][2], "doctrine.emit_docs")

    def test_ensure_flow_assets_built_renders_role_soul_sidecars_into_agent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")
            self._write_shared_interview_prompt(repo_root=repo_root)
            self._write_role_soul_prompt(repo_root=repo_root, role_slug="scope_lead")
            stale_sidecar = repo_root / "flows" / "demo" / "build" / "agents" / "stale_role" / "SOUL.md"
            stale_sidecar.parent.mkdir(parents=True, exist_ok=True)
            stale_sidecar.write_text("stale\n", encoding="utf-8")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            soul_path = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "SOUL.md"
            self.assertTrue(soul_path.is_file())
            self.assertIn("You are Scope Lead.", soul_path.read_text(encoding="utf-8"))
            self.assertFalse(stale_sidecar.exists())

    def test_ensure_flow_assets_built_renders_shared_interview_sidecars_into_agent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-kernel")
            self._write_markdown_skill(repo_root=repo_root, skill_name="rally-memory")
            self._write_shared_interview_prompt(repo_root=repo_root)
            agent_dir = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead"
            agent_dir.mkdir(parents=True, exist_ok=True)
            (agent_dir / "AGENTS.md").write_text("compiled agent\n", encoding="utf-8")
            stale_sidecar = repo_root / "flows" / "demo" / "build" / "agents" / "stale_role" / "INTERVIEW.md"
            stale_sidecar.parent.mkdir(parents=True, exist_ok=True)
            stale_sidecar.write_text("stale\n", encoding="utf-8")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_assets_built(
                workspace=self._workspace(repo_root),
                flow_name="demo",
                subprocess_run=fake_run,
            )

            interview_path = agent_dir / "INTERVIEW.md"
            self.assertTrue(interview_path.is_file())
            self.assertIn("You are in interview mode for a Rally agent.", interview_path.read_text(encoding="utf-8"))
            self.assertFalse(stale_sidecar.exists())

    def _write_flow_file(self, *, repo_root: Path, allowed_skills: tuple[str, ...]) -> None:
        flow_root = repo_root / "flows" / "demo"
        flow_root.mkdir(parents=True)
        allowed_skills_yaml = "[" + ", ".join(allowed_skills) + "]"
        (flow_root / "flow.yaml").write_text(
            textwrap.dedent(
                f"""\
                name: demo
                code: DMO
                start_agent: 01_scope_lead
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: {allowed_skills_yaml}
                    allowed_mcps: []
                runtime:
                  adapter: codex
                  max_command_turns: 1
                  adapter_args:
                    model: gpt-5.4
                """
            ),
            encoding="utf-8",
        )

    def _write_markdown_skill(self, *, repo_root: Path, skill_name: str) -> None:
        skill_root = repo_root / "skills" / skill_name
        skill_root.mkdir(parents=True, exist_ok=True)
        (skill_root / "SKILL.md").write_text(
            textwrap.dedent(
                f"""\
                ---
                name: {skill_name}
                description: "A test skill."
                ---

                # {skill_name}
                """
            ),
            encoding="utf-8",
        )

    def _write_doctrine_skill(self, *, repo_root: Path, skill_name: str) -> None:
        skill_root = repo_root / "skills" / skill_name
        (skill_root / "prompts").mkdir(parents=True, exist_ok=True)
        (skill_root / "prompts" / "SKILL.prompt").write_text(
            textwrap.dedent(
                f"""\
                skill package TestSkill: "Test Skill"
                    metadata:
                        name: "{skill_name}"
                    "A test Doctrine skill."
                """
            ),
            encoding="utf-8",
        )

    def _write_role_soul_prompt(self, *, repo_root: Path, role_slug: str) -> None:
        role_root = repo_root / "flows" / "demo" / "prompts" / "roles" / role_slug
        role_root.mkdir(parents=True, exist_ok=True)
        (role_root / "SOUL.prompt").write_text(
            textwrap.dedent(
                """\
                agent ScopeLead:
                    role: "You are Scope Lead."
                    workflow: "Identity"
                        "Keep scope clear."
                """
            ),
            encoding="utf-8",
        )

    def _write_shared_interview_prompt(self, *, repo_root: Path) -> None:
        prompt_root = repo_root / "stdlib" / "rally" / "prompts" / "rally"
        prompt_root.mkdir(parents=True, exist_ok=True)
        (prompt_root / "interview_agent.prompt").write_text(
            textwrap.dedent(
                """\
                agent InterviewModeGuide:
                    role: "You are in interview mode for a Rally agent."
                    workflow: "Interview Mode"
                        "Stay in interview mode."
                """
            ),
            encoding="utf-8",
        )

    def _workspace(self, repo_root: Path):
        return workspace_context_from_root(
            repo_root,
            cli_bin=repo_root / "bin" / "rally",
        )


if __name__ == "__main__":
    unittest.main()
