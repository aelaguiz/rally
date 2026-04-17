from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rally.errors import RallyConfigError
from rally.services.builtin_assets import (
    RallyBuiltinAssets,
    reject_reserved_builtin_skill_shadow,
    resolve_rally_builtin_assets,
)


class _FakeDistFile:
    def __init__(self, relative_path: str, located: Path) -> None:
        self._relative_path = relative_path
        self._located = located

    def as_posix(self) -> str:
        return self._relative_path

    def locate(self) -> Path:
        return self._located


class _FakeDistribution:
    def __init__(self, files: tuple[_FakeDistFile, ...]) -> None:
        self.files = files


class BuiltinAssetsTests(unittest.TestCase):
    def test_resolver_reads_rally_source_checkout_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            self._write_source_checkout(repo_root)

            assets = resolve_rally_builtin_assets(workspace_root=repo_root)

            self.assertEqual(assets.source_kind, "source_checkout")
            self.assertEqual(assets.source_root, repo_root)
            self.assertEqual(assets.stdlib_prompts_root, repo_root / "stdlib" / "rally" / "prompts")
            self.assertEqual(assets.skill_runtime_dir("rally-kernel"), repo_root / "skills" / "rally-kernel" / "build")

    def test_resolver_reads_installed_distribution_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir).resolve()
            fake_dist = self._write_distribution_assets(install_root)

            with patch("rally.services.builtin_assets._resolve_source_checkout_root", return_value=None), patch(
                "rally.services.builtin_assets.distribution",
                return_value=fake_dist,
            ):
                assets = resolve_rally_builtin_assets(workspace_root=install_root / "host")

            self.assertEqual(assets.source_kind, "installed_distribution")
            self.assertEqual(assets.stdlib_prompts_root, install_root / "rally_assets" / "stdlib" / "rally" / "prompts")
            self.assertEqual(
                assets.skill_runtime_dir("rally-memory"),
                install_root / "rally_assets" / "skills" / "rally-memory",
            )

    def test_installed_distribution_missing_required_skill_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir).resolve()
            base_agent = install_root / "rally_assets" / "stdlib" / "rally" / "prompts" / "rally" / "base_agent.prompt"
            base_agent.parent.mkdir(parents=True)
            base_agent.write_text("# Base\n", encoding="utf-8")
            fake_dist = _FakeDistribution(
                (
                    _FakeDistFile("rally_assets/stdlib/rally/prompts/rally/base_agent.prompt", base_agent),
                )
            )

            with patch("rally.services.builtin_assets._resolve_source_checkout_root", return_value=None), patch(
                "rally.services.builtin_assets.distribution",
                return_value=fake_dist,
            ):
                with self.assertRaisesRegex(RallyConfigError, "missing built-in asset"):
                    resolve_rally_builtin_assets(workspace_root=install_root / "host")

    def test_external_workspace_cannot_shadow_reserved_builtin_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir).resolve()
            framework_root = temp_root / "framework"
            workspace_root = temp_root / "host"
            skill_dir = workspace_root / "skills" / "rally-kernel"
            skill_dir.mkdir(parents=True)
            assets = RallyBuiltinAssets(
                stdlib_root=framework_root / "stdlib" / "rally",
                stdlib_prompts_root=framework_root / "stdlib" / "rally" / "prompts",
                skill_runtime_dirs={"rally-kernel": framework_root / "skills" / "rally-kernel" / "build"},
                source_kind="source_checkout",
                source_root=framework_root,
            )

            with self.assertRaisesRegex(RallyConfigError, "shadows Rally-owned built-in skill"):
                reject_reserved_builtin_skill_shadow(workspace_root=workspace_root, builtins=assets)

    def _write_source_checkout(self, repo_root: Path) -> None:
        (repo_root / "pyproject.toml").parent.mkdir(parents=True)
        (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally-agents'\n", encoding="utf-8")
        (repo_root / "stdlib" / "rally" / "prompts" / "rally").mkdir(parents=True)
        (repo_root / "stdlib" / "rally" / "prompts" / "rally" / "base_agent.prompt").write_text(
            "# Base\n",
            encoding="utf-8",
        )
        for skill_name in ("rally-kernel", "rally-memory"):
            prompt_file = repo_root / "skills" / skill_name / "prompts" / "SKILL.prompt"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text("skill package Test\n", encoding="utf-8")
            build_file = repo_root / "skills" / skill_name / "build" / "SKILL.md"
            build_file.parent.mkdir(parents=True)
            build_file.write_text("---\nname: test\ndescription: Test.\n---\n", encoding="utf-8")

    def _write_distribution_assets(self, install_root: Path) -> _FakeDistribution:
        files: list[_FakeDistFile] = []
        paths = (
            "rally_assets/stdlib/rally/prompts/rally/base_agent.prompt",
            "rally_assets/skills/rally-kernel/SKILL.md",
            "rally_assets/skills/rally-memory/SKILL.md",
        )
        for relative_path in paths:
            located = install_root / relative_path
            located.parent.mkdir(parents=True, exist_ok=True)
            located.write_text("---\nname: test\ndescription: Test.\n---\n", encoding="utf-8")
            files.append(_FakeDistFile(relative_path, located))
        return _FakeDistribution(tuple(files))


if __name__ == "__main__":
    unittest.main()
