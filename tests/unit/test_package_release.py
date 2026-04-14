from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from rally._package_release import (
    load_doctrine_dependency_line,
    load_package_release_metadata,
    resolve_distribution_artifact,
    write_github_outputs,
)


class PackageReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_package_release_metadata_reads_explicit_release_fields(self) -> None:
        self._write_pyproject(
            """\
            [project]
            name = "rally-agents"
            version = "0.1.2"

            [tool.rally.package]
            import_name = "rally"
            pypi_environment = "pypi"
            testpypi_environment = "testpypi"
            """
        )

        metadata = load_package_release_metadata(self.root)

        self.assertEqual(metadata.distribution_name, "rally-agents")
        self.assertEqual(metadata.version, "0.1.2")
        self.assertEqual(metadata.import_name, "rally")
        self.assertEqual(metadata.pypi_environment, "pypi")
        self.assertEqual(metadata.testpypi_environment, "testpypi")
        self.assertEqual(metadata.pypi_project_url, "https://pypi.org/project/rally-agents/")
        self.assertEqual(
            metadata.testpypi_project_url,
            "https://test.pypi.org/project/rally-agents/",
        )

    def test_load_package_release_metadata_requires_tool_rally_package_table(self) -> None:
        self._write_pyproject(
            """\
            [project]
            name = "rally-agents"
            version = "0.1.2"
            """
        )

        with self.assertRaisesRegex(RuntimeError, r"must contain a `\[tool.rally.package\]` table"):
            load_package_release_metadata(self.root)

    def test_load_package_release_metadata_requires_named_release_fields(self) -> None:
        self._write_pyproject(
            """\
            [project]
            name = "rally-agents"
            version = "0.1.2"

            [tool.rally.package]
            import_name = "rally"
            pypi_environment = "pypi"
            """
        )

        with self.assertRaisesRegex(
            RuntimeError,
            r"`\[tool.rally.package\]\.testpypi_environment` must be a non-empty string",
        ):
            load_package_release_metadata(self.root)

    def test_resolve_distribution_artifact_requires_exactly_one_match(self) -> None:
        dist_dir = self.root / "dist"
        dist_dir.mkdir()
        (dist_dir / "rally_agents-0.1.2-py3-none-any.whl").write_text("", encoding="utf-8")

        resolved = resolve_distribution_artifact(dist_dir=dist_dir, artifact_type="wheel")

        self.assertTrue(resolved.name.endswith(".whl"))

    def test_load_doctrine_dependency_line_reads_public_dependency(self) -> None:
        self._write_pyproject(
            """\
            [project]
            name = "rally-agents"
            version = "0.1.2"
            dependencies = [
                "doctrine-agents>=1.0.2,<2",
                "rich>=15.0.0,<16",
            ]

            [tool.rally.package]
            import_name = "rally"
            pypi_environment = "pypi"
            testpypi_environment = "testpypi"
            """
        )

        self.assertEqual(
            load_doctrine_dependency_line(self.root),
            "doctrine-agents>=1.0.2,<2",
        )

    def test_write_github_outputs_uses_metadata_fields(self) -> None:
        self._write_pyproject(
            """\
            [project]
            name = "rally-agents"
            version = "0.1.2"

            [tool.rally.package]
            import_name = "rally"
            pypi_environment = "pypi"
            testpypi_environment = "testpypi"
            """
        )
        output_path = self.root / "github-output.txt"

        write_github_outputs(
            metadata=load_package_release_metadata(self.root),
            output_path=output_path,
        )

        text = output_path.read_text(encoding="utf-8")
        self.assertIn("distribution_name=rally-agents", text)
        self.assertIn("import_name=rally", text)
        self.assertIn("pypi_project_url=https://pypi.org/project/rally-agents/", text)

    def _write_pyproject(self, text: str) -> None:
        (self.root / "pyproject.toml").write_text(
            textwrap.dedent(text),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
