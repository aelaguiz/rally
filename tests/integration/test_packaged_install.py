from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from rally._package_release import load_doctrine_dependency_line, load_package_release_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTRINE_REPO_ROOT = REPO_ROOT.parent / "doctrine"
EXPECTED_DOCTRINE_PACKAGE_LINE = load_doctrine_dependency_line(REPO_ROOT)


class PackagedInstallTests(unittest.TestCase):
    def test_built_wheel_runs_installed_cli_and_uses_emitted_json_package_in_host_repo(self) -> None:
        self._assert_packaged_artifact_runtime("wheel")

    def test_built_sdist_runs_installed_cli_and_uses_emitted_json_package_in_host_repo(self) -> None:
        self._assert_packaged_artifact_runtime("sdist")

    def _assert_packaged_artifact_runtime(self, artifact_type: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir).resolve()
            host_root = temp_root / "host"
            venv_root = temp_root / "venv"
            artifact_path = self._latest_artifact(artifact_type)

            metadata_text = self._artifact_metadata_text(artifact_path=artifact_path, artifact_type=artifact_type)
            self.assertIn(self._expected_doctrine_metadata_line(), metadata_text)

            self._create_venv(venv_root)
            python_bin = self._venv_python(venv_root)
            rally_bin = self._venv_rally(venv_root)
            self._run([str(python_bin), "-m", "pip", "install", str(artifact_path)])
            self._install_dev_doctrine_checkout(python_bin=python_bin)

            help_result = self._run([str(rally_bin), "--help"], cwd=temp_root)
            self.assertIn("usage: rally", help_result.stdout)
            self.assertIn("run", help_result.stdout)
            self.assertIn("resume", help_result.stdout)
            self.assertIn("workspace", help_result.stdout)

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

            sync_result = self._run([str(rally_bin), "workspace", "sync"], cwd=host_root)
            self.assertIn("Synced Rally built-ins into", sync_result.stdout)
            self.assertFalse((host_root / "runs" / "active").exists())

            self.assertTrue((host_root / "stdlib" / "rally" / "prompts" / "rally" / "turn_results.prompt").is_file())
            self.assertTrue((host_root / "stdlib" / "rally" / "prompts" / "rally" / "review_results.prompt").is_file())
            self.assertFalse((host_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").exists())
            self.assertFalse((host_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json").exists())
            self.assertTrue((host_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertFalse((host_root / "skills" / "rally-memory").exists())

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

            agent_dir = host_root / "flows" / "demo" / "build" / "agents" / "scope_lead"
            contract_path = agent_dir / "final_output.contract.json"
            contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
            final_output = contract_payload["final_output"]

            self.assertEqual(
                final_output["emitted_schema_relpath"],
                "schemas/rally_turn_result.schema.json",
            )
            self.assertTrue((agent_dir / final_output["emitted_schema_relpath"]).is_file())
            self.assertFalse((agent_dir / "AGENTS.contract.json").exists())
            self.assertNotIn("../rally/", contract_path.read_text(encoding="utf-8"))

            review_agent_dir = host_root / "flows" / "demo" / "build" / "agents" / "scope_reviewer"
            review_contract_path = review_agent_dir / "final_output.contract.json"
            review_contract_payload = json.loads(review_contract_path.read_text(encoding="utf-8"))
            review_final_output = review_contract_payload["final_output"]

            self.assertEqual(
                review_final_output["emitted_schema_relpath"],
                "schemas/scope_review_final_response.schema.json",
            )
            self.assertTrue((review_agent_dir / review_final_output["emitted_schema_relpath"]).is_file())
            self.assertEqual(review_contract_payload["review"]["final_response"]["mode"], "split")
            self.assertTrue(review_contract_payload["review"]["final_response"]["control_ready"])
            self.assertNotIn("../rally/", review_contract_path.read_text(encoding="utf-8"))

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

    def _latest_artifact(self, artifact_type: str) -> Path:
        metadata = load_package_release_metadata(REPO_ROOT)
        wheel_prefix = metadata.distribution_name.replace("-", "_")
        if artifact_type == "wheel":
            artifacts = sorted(
                REPO_ROOT.glob(f"dist/{wheel_prefix}-*.whl"),
                key=lambda path: path.stat().st_mtime,
            )
        elif artifact_type == "sdist":
            artifacts = sorted(
                REPO_ROOT.glob(f"dist/{wheel_prefix}-*.tar.gz"),
                key=lambda path: path.stat().st_mtime,
            )
        else:
            self.fail(f"Unsupported artifact type `{artifact_type}`.")
        if not artifacts:
            self.fail(f"No Rally {artifact_type} artifact found under dist/. Build Rally before running the packaged-install proof.")
        return artifacts[-1]

    def _artifact_metadata_text(self, *, artifact_path: Path, artifact_type: str) -> str:
        if artifact_type == "wheel":
            with zipfile.ZipFile(artifact_path) as archive:
                metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
                return archive.read(metadata_name).decode("utf-8")
        if artifact_type == "sdist":
            with tarfile.open(artifact_path, "r:gz") as archive:
                metadata_name = next(member.name for member in archive.getmembers() if member.name.endswith("/PKG-INFO"))
                metadata_file = archive.extractfile(metadata_name)
                if metadata_file is None:
                    self.fail(f"Could not read `{metadata_name}` from `{artifact_path}`.")
                return metadata_file.read().decode("utf-8")
        self.fail(f"Unsupported artifact type `{artifact_type}`.")

    def _create_venv(self, venv_root: Path) -> None:
        self._run([sys.executable, "-m", "venv", str(venv_root)])

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

    def _install_dev_doctrine_checkout(self, *, python_bin: Path) -> None:
        self.assertTrue(
            DOCTRINE_REPO_ROOT.is_dir(),
            f"Expected local Doctrine checkout at `{DOCTRINE_REPO_ROOT}` for dev-runner proof.",
        )
        self._run([str(python_bin), "-m", "pip", "install", str(DOCTRINE_REPO_ROOT)])

    def _expected_doctrine_metadata_line(self) -> str:
        package_name, remainder = EXPECTED_DOCTRINE_PACKAGE_LINE.split(">=", 1)
        lower_bound, upper_bound = remainder.split(",<", 1)
        return f"Requires-Dist: {package_name}<{upper_bound},>={lower_bound}"

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
                  02_scope_reviewer:
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
                import rally.review_results
                import rally.turn_results


                input ScopeDraftFile: "Scope Draft File"
                    source: File
                        path: "home:artifacts/scope.md"
                    shape: MarkdownDocument
                    requirement: Required
                    basis_missing: "Basis Missing"
                    "Use the scope draft as the review subject."


                workflow ScopeReviewContract: "Scope Review Contract"
                    artifact_named: "Artifact Named"
                        "Check that the review names the scope draft path."


                output ScopeReviewResponse: "Scope Review Response"
                    target: TurnResponse
                    shape: rally.review_results.BaseRallyReviewJson
                    requirement: Required

                    verdict: "Verdict"
                        "Say whether the review accepts the scope draft or asks for changes."

                    reviewed_artifact: "Reviewed Artifact"
                        "Use `home:artifacts/scope.md`."

                    analysis_performed: "Review Summary"
                        "Explain the review in 2-4 plain sentences."

                    findings_first: "Findings First"
                        "Start with the main finding, then the next move."

                    current_artifact: "Current Artifact" when present(current_artifact):
                        "Use `home:artifacts/scope.md` when the scope draft still stands."

                    next_owner: "Next Owner" when present(next_owner):
                        "Use the next owner key when the review routes."

                    failure_detail: "Failure Detail" when verdict == ReviewVerdict.changes_requested:
                        blocked_gate: "Blocked Gate" when present(blocked_gate):
                            "Name the blocker when the review could not start."

                        failing_gates: "Failing Gates"
                            "List the exact failing review gates in authored order."

                    trust_surface:
                        current_artifact

                    standalone_read: "Standalone Read"
                        "This review should stand on its own."


                output ScopeReviewFinalResponse: "Scope Review Final Response"
                    target: TurnResponse
                    shape: rally.review_results.BaseRallyReviewJson
                    requirement: Required

                    verdict: "Verdict"
                        "Say whether the review accepts the scope draft or asks for changes."

                    reviewed_artifact: "Reviewed Artifact"
                        "Use `home:artifacts/scope.md`."

                    analysis_performed: "Review Summary"
                        "Explain the review in 2-4 plain sentences."

                    findings_first: "Findings First"
                        "Start with the main finding, then the next move."

                    current_artifact: "Current Artifact" when present(current_artifact):
                        "Use `home:artifacts/scope.md` when the scope draft still stands."

                    next_owner: "Next Owner" when present(next_owner):
                        "Use the next owner key when the review routes."

                    failure_detail: "Failure Detail" when verdict == ReviewVerdict.changes_requested:
                        blocked_gate: "Blocked Gate" when present(blocked_gate):
                            "Name the blocker when the review could not start."

                        failing_gates: "Failing Gates"
                            "List the exact failing review gates in authored order."

                    trust_surface:
                        current_artifact

                    standalone_read: "Standalone Read"
                        "This final JSON should be enough for Rally to read the review outcome."


                review ScopeReview: "Scope Review"
                    subject: ScopeDraftFile
                    contract: ScopeReviewContract
                    comment_output: ScopeReviewResponse

                    fields:
                        verdict: verdict
                        reviewed_artifact: reviewed_artifact
                        analysis: analysis_performed
                        readback: findings_first
                        current_artifact: current_artifact
                        blocked_gate: failure_detail.blocked_gate
                        failing_gates: failure_detail.failing_gates
                        next_owner: next_owner

                    basis_checks: "Basis Checks"
                        block "The scope draft is missing." when ScopeDraftFile.basis_missing

                    contract_checks: "Contract Checks"
                        accept "The scope review contract passes." when contract.passes

                    on_accept:
                        current artifact ScopeDraftFile via ScopeReviewResponse.current_artifact

                    on_reject:
                        current artifact ScopeDraftFile via ScopeReviewResponse.current_artifact


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


                agent ScopeReviewer[rally.base_agent.RallyManagedBaseAgent]:
                    role: "Review the scope draft and end with structured review JSON."
                    inherit read_first
                    inherit how_to_take_a_turn
                    inherit rally_contract
                    review: ScopeReview
                    inputs[rally.base_agent.RallyManagedInputs]: "Inputs"
                        inherit rally_workspace_dir
                        inherit rally_run_id
                        inherit rally_flow_code
                        inherit rally_agent_slug
                        inherit issue_ledger
                        scope_draft_file: "Scope Draft File"
                            ScopeDraftFile
                    outputs: "Outputs"
                        ScopeReviewResponse
                        ScopeReviewFinalResponse
                    skills: rally.base_agent.RallyManagedSkills
                    final_output:
                        output: ScopeReviewFinalResponse
                        review_fields:
                            verdict: verdict
                            reviewed_artifact: reviewed_artifact
                            analysis: analysis_performed
                            readback: findings_first
                            current_artifact: current_artifact
                            blocked_gate: failure_detail.blocked_gate
                            failing_gates: failure_detail.failing_gates
                            next_owner: next_owner
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
