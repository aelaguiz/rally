from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rally.services.bundled_assets import ensure_workspace_builtins_synced, sync_bundled_assets


class BundledAssetsTests(unittest.TestCase):
    def test_ensure_workspace_builtins_synced_copies_builtins_into_external_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir(parents=True)
            pyproject_path = workspace_root / "pyproject.toml"
            pyproject_path.write_text("[project]\nname = 'demo-workspace'\n", encoding="utf-8")

            copied = ensure_workspace_builtins_synced(
                workspace_root=workspace_root,
                pyproject_path=pyproject_path,
            )

            self.assertEqual(
                copied,
                [
                    "stdlib/rally",
                    "skills/rally-kernel",
                    "skills/rally-memory",
                ],
            )
            self.assertTrue((workspace_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").is_file())
            self.assertTrue((workspace_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((workspace_root / "skills" / "rally-memory" / "SKILL.md").is_file())

    def test_ensure_workspace_builtins_synced_skips_current_rally_source_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir(parents=True)
            pyproject_path = workspace_root / "pyproject.toml"
            pyproject_path.write_text("[project]\nname = 'rally-agents'\n", encoding="utf-8")

            copied = ensure_workspace_builtins_synced(
                workspace_root=workspace_root,
                pyproject_path=pyproject_path,
            )

            self.assertEqual(copied, [])
            self.assertFalse((workspace_root / "stdlib").exists())
            self.assertFalse((workspace_root / "skills").exists())

    def test_ensure_workspace_builtins_synced_skips_legacy_rally_source_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir(parents=True)
            pyproject_path = workspace_root / "pyproject.toml"
            pyproject_path.write_text("[project]\nname = 'rally'\n", encoding="utf-8")

            copied = ensure_workspace_builtins_synced(
                workspace_root=workspace_root,
                pyproject_path=pyproject_path,
            )

            self.assertEqual(copied, [])
            self.assertFalse((workspace_root / "stdlib").exists())
            self.assertFalse((workspace_root / "skills").exists())

    def test_sync_bundled_assets_check_ignores_python_cache_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "repo"
            self._write_fixture_pyproject(repo_root=repo_root)
            shutil.copytree(Path(__file__).resolve().parents[2] / "stdlib", repo_root / "stdlib")
            shutil.copytree(Path(__file__).resolve().parents[2] / "skills", repo_root / "skills")
            shutil.copytree(Path(__file__).resolve().parents[2] / "src" / "rally" / "_bundled", repo_root / "src" / "rally" / "_bundled")

            pycache_dir = repo_root / "src" / "rally" / "_bundled" / "__pycache__"
            pycache_dir.mkdir(parents=True, exist_ok=True)
            (pycache_dir / "__init__.cpython-314.pyc").write_bytes(b"compiled")

            differences = sync_bundled_assets(repo_root=repo_root, check=True)

            self.assertEqual(differences, [])

    def _write_fixture_pyproject(self, *, repo_root: Path) -> None:
        repo_root.mkdir(parents=True, exist_ok=True)
        (repo_root / "pyproject.toml").write_text(
            "\n".join(
                (
                    "[project]",
                    "name = 'bundle-fixture'",
                    "version = '0.0.0'",
                    "",
                    "[tool.rally.workspace]",
                    "version = 1",
                    "",
                    "[tool.doctrine.compile]",
                    'additional_prompt_roots = ["stdlib/rally/prompts"]',
                    "",
                    "[tool.doctrine.emit]",
                    "",
                    "[[tool.doctrine.emit.targets]]",
                    'name = "rally-kernel"',
                    'entrypoint = "skills/rally-kernel/prompts/SKILL.prompt"',
                    'output_dir = "skills/rally-kernel/build"',
                    "",
                    "[[tool.doctrine.emit.targets]]",
                    'name = "rally-memory"',
                    'entrypoint = "skills/rally-memory/prompts/SKILL.prompt"',
                    'output_dir = "skills/rally-memory/build"',
                    "",
                )
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
