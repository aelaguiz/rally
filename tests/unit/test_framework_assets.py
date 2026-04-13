from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.framework_assets import ensure_framework_builtins
from rally.services.workspace import workspace_context_from_root


class FrameworkAssetsTests(unittest.TestCase):
    def test_ensure_framework_builtins_materializes_missing_reserved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            framework_root = root / "framework"
            workspace_root = root / "workspace"
            (framework_root / "stdlib" / "rally" / "prompts").mkdir(parents=True)
            (framework_root / "skills" / "rally-kernel").mkdir(parents=True)
            (framework_root / "stdlib" / "rally" / "prompts" / "base.prompt").write_text(
                "prompt\n",
                encoding="utf-8",
            )
            (framework_root / "skills" / "rally-kernel" / "SKILL.md").write_text(
                "# Rally Kernel\n",
                encoding="utf-8",
            )
            workspace_root.mkdir()
            workspace = workspace_context_from_root(
                workspace_root,
                cli_bin=workspace_root / "bin" / "rally",
                framework_root=framework_root,
            )

            ensure_framework_builtins(workspace)

            self.assertEqual(
                (workspace_root / "stdlib" / "rally" / "prompts" / "base.prompt").read_text(encoding="utf-8"),
                "prompt\n",
            )
            self.assertEqual(
                (workspace_root / "skills" / "rally-kernel" / "SKILL.md").read_text(encoding="utf-8"),
                "# Rally Kernel\n",
            )

    def test_ensure_framework_builtins_rejects_local_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            framework_root = root / "framework"
            workspace_root = root / "workspace"
            (framework_root / "skills" / "rally-kernel").mkdir(parents=True)
            (framework_root / "skills" / "rally-kernel" / "SKILL.md").write_text(
                "# Rally Kernel\n",
                encoding="utf-8",
            )
            (framework_root / "stdlib" / "rally").mkdir(parents=True)
            (workspace_root / "skills" / "rally-kernel").mkdir(parents=True)
            (workspace_root / "skills" / "rally-kernel" / "SKILL.md").write_text(
                "# Edited\n",
                encoding="utf-8",
            )
            workspace = workspace_context_from_root(
                workspace_root,
                cli_bin=workspace_root / "bin" / "rally",
                framework_root=framework_root,
            )

            with self.assertRaisesRegex(RallyConfigError, "edited locally"):
                ensure_framework_builtins(workspace)


if __name__ == "__main__":
    unittest.main()
