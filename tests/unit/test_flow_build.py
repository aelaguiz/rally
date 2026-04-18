from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

from doctrine.diagnostics import DoctrineError

from rally.errors import RallyConfigError
from rally.services.flow_build import ensure_flow_assets_built
from rally.services.workspace import workspace_context_from_root


class FlowBuildTests(unittest.TestCase):
    def test_ensure_flow_assets_built_uses_doctrine_api_with_provider_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            stale_contract = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "AGENTS.contract.json"
            stale_contract.write_text("stale\n", encoding="utf-8")
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertEqual(len(calls["load"]), 2)
            provider_roots = calls["load"][0]["provided_prompt_roots"]
            self.assertEqual(provider_roots[0].name, "rally_stdlib")
            self.assertEqual(provider_roots[0].path, repo_root / "stdlib" / "rally" / "prompts")
            self.assertEqual(calls["docs"], ["demo-target"])
            self.assertEqual(calls["skills"], ["rally-kernel-target"])
            self.assertFalse(stale_contract.exists())

    def test_external_workspace_uses_provider_root_without_workspace_builtin_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "workspace"
            repo_root.mkdir(parents=True)
            self._write_pyproject(repo_root=repo_root, project_name="demo-host")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertEqual(calls["docs"], ["demo-target"])
            self.assertEqual(calls["skills"], [])
            self.assertFalse((repo_root / "stdlib" / "rally").exists())
            self.assertFalse((repo_root / "skills" / "rally-kernel").exists())

    def test_external_workspace_reserved_builtin_skill_shadow_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "workspace"
            repo_root.mkdir(parents=True)
            self._write_pyproject(repo_root=repo_root, project_name="demo-host")
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            skill_file = repo_root / "skills" / "rally-kernel" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("---\nname: rally-kernel\ndescription: Shadow.\n---\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyConfigError, "shadows Rally-owned built-in skill"):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_emits_local_doctrine_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=("demo-git", "repo-search"))
            self._write_doctrine_skill(repo_root=repo_root, skill_name="demo-git")
            self._write_markdown_skill(repo_root=repo_root, skill_name="repo-search")
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertEqual(calls["docs"], ["demo-target"])
            self.assertEqual(calls["skills"], ["demo-git-target", "rally-kernel-target"])

    def test_ensure_flow_assets_built_rejects_missing_workspace_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)

            with self.assertRaisesRegex(RallyConfigError, "workspace pyproject is missing"):
                ensure_flow_assets_built(repo_root=repo_root, flow_name="demo")

    def test_ensure_flow_assets_built_surfaces_doctrine_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=())

            def fail_load_emit_targets(*args: object, **kwargs: object) -> dict[str, object]:
                del args, kwargs
                raise DoctrineError("Emit target `demo` is not defined in `pyproject.toml`.")

            with patch("doctrine.emit_common.load_emit_targets", side_effect=fail_load_emit_targets):
                with self.assertRaisesRegex(RallyConfigError, "Emit target `demo` is not defined"):
                    ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_rejects_bare_relative_prompt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            (repo_root / "flows" / "demo" / "prompts" / "AGENTS.prompt").write_text(
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

    def test_ensure_flow_assets_built_preserves_compiler_owned_peer_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            compiler_owned_soul = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "SOUL.md"
            compiler_owned_soul.write_text("Compiler-owned soul.\n", encoding="utf-8")
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertEqual(compiler_owned_soul.read_text(encoding="utf-8"), "Compiler-owned soul.\n")

    def test_ensure_flow_assets_built_prunes_retired_compiled_agent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=())
            stale_agent_dir = repo_root / "flows" / "demo" / "build" / "agents" / "critic"
            stale_agent_dir.mkdir(parents=True)
            (stale_agent_dir / "stale.txt").write_text("legacy\n", encoding="utf-8")
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertFalse(stale_agent_dir.exists())

    def test_ensure_flow_assets_built_includes_system_skills_in_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(
                repo_root=repo_root,
                allowed_skills=(),
                system_skills=("rally-memory",),
            )
            # Source checkouts resolve rally-memory as a Doctrine skill target,
            # so the builder must emit it alongside rally-kernel.
            self._add_doctrine_emit_target(
                repo_root=repo_root,
                name="rally-memory",
                entrypoint="skills/rally-memory/prompts/SKILL.prompt",
                output_dir="skills/rally-memory/build",
            )
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls, extra_emit_targets={"rally-memory": "rally-memory-target"}):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

            self.assertEqual(calls["docs"], ["demo-target"])
            self.assertEqual(calls["skills"], ["rally-kernel-target", "rally-memory-target"])

    def test_ensure_flow_assets_built_rejects_unknown_system_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(
                repo_root=repo_root,
                allowed_skills=(),
                system_skills=("rally-memry",),
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"Unknown Rally stdlib skill `rally-memry`",
            ):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_rejects_skill_tier_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(
                repo_root=repo_root,
                allowed_skills=("rally-memory",),
                system_skills=("rally-memory",),
            )

            with self.assertRaisesRegex(
                RallyConfigError,
                r"both `allowed_skills` and `system_skills`",
            ):
                ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def test_ensure_flow_assets_built_rejects_compiled_skill_surface_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root=repo_root)
            self._write_flow_file(repo_root=repo_root, allowed_skills=("demo-git",))
            self._write_doctrine_skill(repo_root=repo_root, skill_name="demo-git")
            agent_markdown = repo_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "AGENTS.md"
            agent_markdown.write_text(self._render_compiled_agent_markdown("Scope Lead", ()), encoding="utf-8")
            calls: dict[str, Any] = {"load": [], "docs": [], "skills": []}

            with self._patch_doctrine(calls):
                with self.assertRaisesRegex(RallyConfigError, "Compiled skill readback"):
                    ensure_flow_assets_built(workspace=self._workspace(repo_root), flow_name="demo")

    def _patch_doctrine(
        self,
        calls: dict[str, Any],
        *,
        extra_emit_targets: dict[str, str] | None = None,
    ) -> ExitStack:
        stack = ExitStack()

        def fake_load_emit_targets(config_path: Path, *, provided_prompt_roots: tuple[object, ...] = ()) -> dict[str, str]:
            calls["load"].append(
                {
                    "config_path": config_path,
                    "provided_prompt_roots": provided_prompt_roots,
                }
            )
            emit_targets = {
                "demo": "demo-target",
                "demo-git": "demo-git-target",
                "rally-kernel": "rally-kernel-target",
            }
            if extra_emit_targets:
                emit_targets.update(extra_emit_targets)
            return emit_targets

        def fake_emit_target(target: str) -> None:
            calls["docs"].append(target)

        def fake_emit_target_skill(target: str) -> None:
            calls["skills"].append(target)

        stack.enter_context(patch("doctrine.emit_common.load_emit_targets", side_effect=fake_load_emit_targets))
        stack.enter_context(patch("doctrine.emit_docs.emit_target", side_effect=fake_emit_target))
        stack.enter_context(patch("doctrine.emit_skill.emit_target_skill", side_effect=fake_emit_target_skill))
        return stack

    def _write_source_checkout(self, *, repo_root: Path) -> None:
        repo_root.mkdir(parents=True)
        self._write_pyproject(repo_root=repo_root, project_name="rally-agents")
        base_agent_dir = repo_root / "stdlib" / "rally" / "prompts" / "rally" / "base_agent"
        base_agent_dir.mkdir(parents=True)
        (base_agent_dir / "AGENTS.prompt").write_text(
            "# Base\n",
            encoding="utf-8",
        )
        self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-kernel")
        self._write_builtin_skill_build(repo_root=repo_root, skill_name="rally-kernel")
        self._write_doctrine_skill(repo_root=repo_root, skill_name="rally-memory")
        self._write_builtin_skill_build(repo_root=repo_root, skill_name="rally-memory")

    def _add_doctrine_emit_target(
        self,
        *,
        repo_root: Path,
        name: str,
        entrypoint: str,
        output_dir: str,
    ) -> None:
        pyproject_path = repo_root / "pyproject.toml"
        existing = pyproject_path.read_text(encoding="utf-8")
        pyproject_path.write_text(
            existing
            + textwrap.dedent(
                f"""\

                [[tool.doctrine.emit.targets]]
                name = "{name}"
                entrypoint = "{entrypoint}"
                output_dir = "{output_dir}"
                """
            ),
            encoding="utf-8",
        )

    def _write_pyproject(self, *, repo_root: Path, project_name: str) -> None:
        (repo_root / "pyproject.toml").write_text(
            textwrap.dedent(
                f"""\
                [project]
                name = '{project_name}'

                [tool.rally.workspace]
                version = 1

                [tool.doctrine.emit]

                [[tool.doctrine.emit.targets]]
                name = "demo"
                entrypoint = "flows/demo/prompts/AGENTS.prompt"
                output_dir = "flows/demo/build/agents"

                [[tool.doctrine.emit.targets]]
                name = "rally-kernel"
                entrypoint = "skills/rally-kernel/prompts/SKILL.prompt"
                output_dir = "skills/rally-kernel/build"

                [[tool.doctrine.emit.targets]]
                name = "demo-git"
                entrypoint = "skills/demo-git/prompts/SKILL.prompt"
                output_dir = "skills/demo-git/build"
                """
            ),
            encoding="utf-8",
        )

    def _write_flow_file(
        self,
        *,
        repo_root: Path,
        allowed_skills: tuple[str, ...],
        system_skills: tuple[str, ...] = (),
    ) -> None:
        flow_root = repo_root / "flows" / "demo"
        flow_root.mkdir(parents=True, exist_ok=True)
        allowed_skills_yaml = "[" + ", ".join(allowed_skills) + "]"
        system_skills_yaml = "[" + ", ".join(system_skills) + "]"
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
                    system_skills: {system_skills_yaml}
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
        (flow_root / "prompts").mkdir(parents=True, exist_ok=True)
        (flow_root / "prompts" / "AGENTS.prompt").write_text(
            'input IssueLedger: "Issue Ledger"\n    source: File\n        path: "home:issue.md"\n',
            encoding="utf-8",
        )
        self._write_emitted_agent_package(
            flow_root=flow_root,
            allowed_skills=allowed_skills,
            system_skills=system_skills,
        )

    def _write_emitted_agent_package(
        self,
        *,
        flow_root: Path,
        allowed_skills: tuple[str, ...],
        system_skills: tuple[str, ...] = (),
    ) -> None:
        agent_dir = flow_root / "build" / "agents" / "scope_lead"
        schema_dir = agent_dir / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "AGENTS.md").write_text(
            self._render_compiled_agent_markdown(
                "Scope Lead",
                allowed_skills,
                system_skills,
            ),
            encoding="utf-8",
        )
        (schema_dir / "rally_turn_result.schema.json").write_text(
            textwrap.dedent(
                """\
                {
                  "type": "object",
                  "required": ["kind", "next_owner", "summary", "reason", "sleep_duration_seconds"],
                  "properties": {
                    "kind": {"type": "string", "enum": ["handoff", "done", "blocker", "sleep"]},
                    "next_owner": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                    "sleep_duration_seconds": {"type": ["integer", "null"]}
                  }
                }
                """
            ),
            encoding="utf-8",
        )
        (agent_dir / "final_output.contract.json").write_text(
            json.dumps(
                {
                    "contract_version": 1,
                    "agent": {
                        "name": "ScopeLead",
                        "slug": "scope_lead",
                        "entrypoint": "flows/demo/prompts/AGENTS.prompt",
                    },
                    "final_output": {
                        "exists": True,
                        "declaration_key": "DemoTurnResult",
                        "declaration_name": "DemoTurnResult",
                        "format_mode": "json_object",
                        "schema_profile": "OpenAIStructuredOutput",
                        "emitted_schema_relpath": "schemas/rally_turn_result.schema.json",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _render_compiled_agent_markdown(
        self,
        title: str,
        allowed_skills: tuple[str, ...],
        system_skills: tuple[str, ...] = (),
    ) -> str:
        skill_lines = ["## Skills", "", "### rally-kernel", ""]
        for skill_name in (*allowed_skills, *system_skills):
            skill_lines.extend((f"### {skill_name}", ""))
        return f"# {title}\n\n" + "\n".join(skill_lines)

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

    def _write_builtin_skill_build(self, *, repo_root: Path, skill_name: str) -> None:
        build_file = repo_root / "skills" / skill_name / "build" / "SKILL.md"
        build_file.parent.mkdir(parents=True, exist_ok=True)
        build_file.write_text(
            textwrap.dedent(
                f"""\
                ---
                name: {skill_name}
                description: "A built-in test skill."
                ---
                """
            ),
            encoding="utf-8",
        )

    def _workspace(self, repo_root: Path):
        return workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally")


if __name__ == "__main__":
    unittest.main()
