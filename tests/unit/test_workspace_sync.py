from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.services.workspace import workspace_context_from_root
from rally.services.workspace_sync import sync_workspace_builtins


class WorkspaceSyncTests(unittest.TestCase):
    def test_sync_workspace_builtins_copies_framework_assets_into_external_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir(parents=True)
            (workspace_root / "pyproject.toml").write_text(
                "[project]\nname = 'demo-host'\n",
                encoding="utf-8",
            )

            result = sync_workspace_builtins(workspace=self._workspace(workspace_root))

            self.assertFalse(result.already_owned)
            # The live workspace sync should mirror package install behavior:
            # only the required kernel skill is copied by default.
            self.assertEqual(
                result.synced_paths,
                (
                    "stdlib/rally",
                    "skills/rally-kernel",
                ),
            )
            self.assertIn("Synced Rally built-ins into", result.message)
            self.assertTrue(
                (workspace_root / "stdlib" / "rally" / "prompts" / "rally" / "turn_results.prompt").is_file()
            )
            self.assertTrue(
                (workspace_root / "stdlib" / "rally" / "prompts" / "rally" / "review_results.prompt").is_file()
            )
            self.assertFalse(
                (workspace_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").exists()
            )
            self.assertFalse(
                (workspace_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json").exists()
            )
            self.assertTrue((workspace_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertFalse((workspace_root / "skills" / "rally-memory").exists())

            second_result = sync_workspace_builtins(workspace=self._workspace(workspace_root))

            self.assertFalse(second_result.already_owned)
            self.assertEqual(second_result.synced_paths, result.synced_paths)

    def test_sync_workspace_builtins_is_a_noop_for_rally_source_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve() / "workspace"
            workspace_root.mkdir(parents=True)
            (workspace_root / "pyproject.toml").write_text(
                "[project]\nname = 'rally-agents'\n",
                encoding="utf-8",
            )

            result = sync_workspace_builtins(workspace=self._workspace(workspace_root))

            self.assertTrue(result.already_owned)
            self.assertEqual(result.synced_paths, ())
            self.assertIn("already owns Rally built-ins", result.message)
            self.assertFalse((workspace_root / "stdlib").exists())
            self.assertFalse((workspace_root / "skills").exists())

    def _workspace(self, workspace_root: Path):
        return workspace_context_from_root(
            workspace_root,
            cli_bin=workspace_root / "bin" / "rally",
        )


if __name__ == "__main__":
    unittest.main()
