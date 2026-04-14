from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from rally._package_release import load_package_release_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DOCTRINE_INSTALL_TARGET = "git+https://github.com/aelaguiz/doctrine.git@v1.0.1"


class PackagedInstallTests(unittest.TestCase):
    def test_built_wheel_runs_installed_cli_and_keeps_emit_support_files_in_host_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir).resolve()
            host_root = temp_root / "host"
            venv_root = temp_root / "venv"
            wheel_path = self._latest_wheel()

            metadata_text = self._wheel_metadata_text(wheel_path)
            self.assertIn("Requires-Dist: doctrine<2,>=1.0.1", metadata_text)

            self._create_venv(venv_root)
            python_bin = self._venv_python(venv_root)
            rally_bin = self._venv_rally(venv_root)
            self._run([str(python_bin), "-m", "pip", "install", self._doctrine_install_target()])
            self._run([str(python_bin), "-m", "pip", "install", str(wheel_path)])

            help_result = self._run([str(rally_bin), "--help"], cwd=temp_root)
            self.assertIn("usage: rally", help_result.stdout)
            self.assertIn("run", help_result.stdout)
            self.assertIn("resume", help_result.stdout)

            self._write_host_workspace(host_root)

            version_result = self._run_python(
                python_bin=python_bin,
                cwd=host_root,
                source=textwrap.dedent(
                    f"""\
                    import rally
                    print(rally.__version__)
                    """
                ),
            )
            self.assertNotEqual(version_result.stdout.strip(), "0.0.0")

            run_result = self._run([str(rally_bin), "run", "demo"], cwd=host_root, check=False)
            self.assertEqual(run_result.returncode, 2)
            self.assertIn("waiting for `", run_result.stderr)
            self.assertIn("home/issue.md", run_result.stderr)
            self.assertIn("rally resume DMO-1", run_result.stderr)

            run_dir = host_root / "runs" / "active" / "DMO-1"
            self.assertTrue((run_dir / "run.yaml").is_file())
            self.assertTrue((run_dir / "state.yaml").is_file())
            self.assertTrue((run_dir / "logs" / "rendered.log").is_file())
            self.assertIn("status: pending", (run_dir / "state.yaml").read_text(encoding="utf-8"))
            rendered_log = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            self.assertIn("Prepared run home shell", rendered_log)
            self.assertIn("waiting for `home/issue.md`", rendered_log)

            self.assertTrue((host_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").is_file())
            self.assertTrue((host_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((host_root / "skills" / "rally-memory" / "SKILL.md").is_file())

            self._run(
                [
                    str(python_bin),
                    "-m",
                    "doctrine.emit_docs",
                    "--pyproject",
                    str(host_root / "pyproject.toml"),
                    "--target",
                    "demo",
                ],
                cwd=host_root,
            )

            contract_path = host_root / "flows" / "demo" / "build" / "agents" / "scope_lead" / "AGENTS.contract.json"
            contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
            final_output = contract_payload["final_output"]

            self.assertEqual(
                final_output["schema_file"],
                "stdlib/rally/schemas/rally_turn_result.schema.json",
            )
            self.assertEqual(
                final_output["example_file"],
                "stdlib/rally/examples/rally_turn_result.example.json",
            )
            self.assertNotIn("../rally/", contract_path.read_text(encoding="utf-8"))

    def _latest_wheel(self) -> Path:
        metadata = load_package_release_metadata(REPO_ROOT)
        wheel_prefix = metadata.distribution_name.replace("-", "_")
        wheels = sorted(
            REPO_ROOT.glob(f"dist/{wheel_prefix}-*.whl"),
            key=lambda path: path.stat().st_mtime,
        )
        if not wheels:
            self.fail("No Rally wheel found under dist/. Build Rally before running the packaged-install proof.")
        return wheels[-1]

    def _wheel_metadata_text(self, wheel_path: Path) -> str:
        with zipfile.ZipFile(wheel_path) as archive:
            metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            return archive.read(metadata_name).decode("utf-8")

    def _create_venv(self, venv_root: Path) -> None:
        self._run([sys.executable, "-m", "venv", str(venv_root)])

    def _doctrine_install_target(self) -> str:
        explicit_target = os.environ.get("RALLY_TEST_DOCTRINE_SOURCE")
        if explicit_target:
            return explicit_target
        return PUBLIC_DOCTRINE_INSTALL_TARGET

    def _venv_python(self, venv_root: Path) -> Path:
        if sys.platform == "win32":
            return venv_root / "Scripts" / "python.exe"
        return venv_root / "bin" / "python"

    def _venv_rally(self, venv_root: Path) -> Path:
        if sys.platform == "win32":
            return venv_root / "Scripts" / "rally.exe"
        return venv_root / "bin" / "rally"

    def _run_python(self, *, python_bin: Path, cwd: Path, source: str) -> subprocess.CompletedProcess[str]:
        return self._run([str(python_bin), "-c", source], cwd=cwd)

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True,
        )

    def _write_host_workspace(self, host_root: Path) -> None:
        (host_root / "flows" / "demo" / "prompts").mkdir(parents=True)
        (host_root / "flows" / "demo" / "flow.yaml").write_text(
            textwrap.dedent(
                """\
                name: demo
                code: DMO
                start_agent: 01_scope_lead
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: []
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
        (host_root / "flows" / "demo" / "prompts" / "AGENTS.prompt").write_text(
            textwrap.dedent(
                """\
                import rally.base_agent
                import rally.turn_results


                agent ScopeLead[rally.base_agent.RallyManagedBaseAgent]:
                    role: "Finish the task and stop."
                    inherit read_first
                    inherit how_to_take_a_turn
                    workflow: "Finish"
                        "Finish the task and stop."
                    inherit rally_contract
                    inputs[rally.base_agent.RallyManagedInputs]: "Inputs"
                        inherit rally_workspace_dir
                        inherit rally_run_id
                        inherit rally_flow_code
                        inherit rally_agent_slug
                        inherit issue_ledger
                    outputs[rally.base_agent.RallyManagedOutputs]: "Outputs"
                        inherit issue_note
                        turn_result: "Turn Result"
                            rally.turn_results.RallyTurnResult
                    skills: rally.base_agent.RallyManagedSkills
                    final_output: rally.turn_results.RallyTurnResult
                """
            ),
            encoding="utf-8",
        )
        (host_root / "pyproject.toml").write_text(
            textwrap.dedent(
                """\
                [project]
                name = "demo-host"
                version = "0.1.0"
                requires-python = ">=3.14"

                [tool.rally.workspace]
                version = 1

                [tool.doctrine.compile]
                additional_prompt_roots = ["stdlib/rally/prompts"]

                [tool.doctrine.emit]

                [[tool.doctrine.emit.targets]]
                name = "demo"
                entrypoint = "flows/demo/prompts/AGENTS.prompt"
                output_dir = "flows/demo/build/agents"
                """
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
