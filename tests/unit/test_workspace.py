from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rally.errors import RallyConfigError
from rally.services.workspace import resolve_workspace


class WorkspaceTests(unittest.TestCase):
    def test_resolve_workspace_finds_manifest_from_child_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            (workspace_root / "pyproject.toml").write_text(
                "[tool.rally.workspace]\nversion = 1\n",
                encoding="utf-8",
            )
            child_dir = workspace_root / "flows" / "demo"
            child_dir.mkdir(parents=True)

            with patch.dict(os.environ, {"RALLY_CLI_BIN": "/tmp/rally"}, clear=False):
                workspace = resolve_workspace(start_path=child_dir)

            self.assertEqual(workspace.workspace_root, workspace_root)
            self.assertEqual(workspace.pyproject_path, workspace_root / "pyproject.toml")

    def test_resolve_workspace_rejects_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            search_root = Path(temp_dir).resolve()

            with patch.dict(os.environ, {"RALLY_CLI_BIN": "/tmp/rally"}, clear=False):
                with self.assertRaisesRegex(RallyConfigError, "No Rally workspace manifest"):
                    resolve_workspace(start_path=search_root)

    def test_resolve_workspace_rejects_nested_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            nested_root = workspace_root / "nested"
            nested_root.mkdir()
            for root in (workspace_root, nested_root):
                (root / "pyproject.toml").write_text(
                    "[tool.rally.workspace]\nversion = 1\n",
                    encoding="utf-8",
                )

            with patch.dict(os.environ, {"RALLY_CLI_BIN": "/tmp/rally"}, clear=False):
                with self.assertRaisesRegex(RallyConfigError, "Ambiguous Rally workspace root"):
                    resolve_workspace(start_path=nested_root / "flows")


if __name__ == "__main__":
    unittest.main()
