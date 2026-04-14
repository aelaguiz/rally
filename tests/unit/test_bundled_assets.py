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

    def test_ensure_workspace_builtins_synced_skips_rally_source_workspace(self) -> None:
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
            shutil.copytree(Path(__file__).resolve().parents[2] / "stdlib", repo_root / "stdlib")
            shutil.copytree(Path(__file__).resolve().parents[2] / "skills", repo_root / "skills")
            shutil.copytree(Path(__file__).resolve().parents[2] / "src" / "rally" / "_bundled", repo_root / "src" / "rally" / "_bundled")

            pycache_dir = repo_root / "src" / "rally" / "_bundled" / "__pycache__"
            pycache_dir.mkdir(parents=True, exist_ok=True)
            (pycache_dir / "__init__.cpython-314.pyc").write_bytes(b"compiled")

            differences = sync_bundled_assets(repo_root=repo_root, check=True)

            self.assertEqual(differences, [])


if __name__ == "__main__":
    unittest.main()
