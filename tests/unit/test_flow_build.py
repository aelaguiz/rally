from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.flow_build import ensure_flow_agents_built


class FlowBuildTests(unittest.TestCase):
    def test_ensure_flow_agents_built_runs_doctrine_emit_docs_for_flow_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            repo_root = root / "rally"
            doctrine_root = root / "doctrine"
            repo_root.mkdir(parents=True)
            doctrine_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            (doctrine_root / "pyproject.toml").write_text("[project]\nname = 'doctrine'\n", encoding="utf-8")
            calls: list[dict[str, object]] = []

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append({"command": command, "kwargs": kwargs})
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            ensure_flow_agents_built(
                repo_root=repo_root,
                flow_name="demo",
                subprocess_run=fake_run,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0]["command"],
                [
                    "uv",
                    "run",
                    "--project",
                    str(doctrine_root),
                    "--locked",
                    "python",
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

    def test_ensure_flow_agents_built_rejects_missing_doctrine_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyConfigError, "Paired Doctrine repo is missing"):
                ensure_flow_agents_built(repo_root=repo_root, flow_name="demo")

    def test_ensure_flow_agents_built_surfaces_emit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            repo_root = root / "rally"
            doctrine_root = root / "doctrine"
            repo_root.mkdir(parents=True)
            doctrine_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            (doctrine_root / "pyproject.toml").write_text("[project]\nname = 'doctrine'\n", encoding="utf-8")

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del kwargs
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr="Emit target `demo` is not defined in `pyproject.toml`.",
                )

            with self.assertRaisesRegex(RallyConfigError, "Emit target `demo` is not defined"):
                ensure_flow_agents_built(
                    repo_root=repo_root,
                    flow_name="demo",
                    subprocess_run=fake_run,
                )
