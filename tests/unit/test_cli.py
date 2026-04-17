from __future__ import annotations

import io
import os
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rally.cli import main
from rally.services.workspace import workspace_context_from_root


class CliTests(unittest.TestCase):
    def test_top_level_help_includes_quickstart_examples(self) -> None:
        stdout = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("Run filesystem-first Rally workflows from the repo root.", help_text)
        self.assertNotIn("rally workspace sync", help_text)
        self.assertIn("rally run demo --from-file ./issue.md", help_text)
        self.assertIn("rally status", help_text)
        self.assertIn("status              Show active runs or inspect one run.", help_text)

    def test_run_help_includes_examples_and_next_step(self) -> None:
        stdout = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["run", "--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("Create a Rally run shell for one flow", help_text)
        self.assertIn("--from-file", help_text)
        self.assertIn("--model", help_text)
        self.assertIn("--thinking", help_text)
        self.assertIn("rally run demo --from-file ./issue.md", help_text)
        self.assertIn("rally run demo --model gpt-5.4 --thinking high", help_text)
        self.assertIn("rally run demo --step", help_text)
        self.assertIn("Next: Rally will either start the run", help_text)

    def test_resume_help_includes_override_flags(self) -> None:
        stdout = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["resume", "--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("Resume one Rally run by id.", help_text)
        self.assertIn("--model", help_text)
        self.assertIn("--thinking", help_text)
        self.assertIn("rally resume DMO-1 --model gpt-5.4 --thinking low", help_text)

    def test_status_help_includes_examples(self) -> None:
        stdout = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["status", "--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("Inspect Rally run state from repo files.", help_text)
        self.assertIn("rally status DMO-1", help_text)

    def test_run_command_calls_runner_without_external_brief_flag(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-1` created."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-1` created.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertFalse(run_flow_mock.call_args.kwargs["request"].start_new)
        self.assertFalse(run_flow_mock.call_args.kwargs["request"].step)

    def test_run_command_passes_new_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-2` created."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo", "--new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-2` created.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertTrue(run_flow_mock.call_args.kwargs["request"].start_new)
        self.assertFalse(run_flow_mock.call_args.kwargs["request"].step)

    def test_run_command_passes_step_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-3` paused."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo", "--step"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-3` paused.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertFalse(run_flow_mock.call_args.kwargs["request"].start_new)
        self.assertTrue(run_flow_mock.call_args.kwargs["request"].step)

    def test_run_command_passes_model_and_thinking_overrides_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-4` created."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo", "--model", "gpt-5.4-mini", "--thinking", "high"])

        self.assertEqual(exit_code, 0)
        request = run_flow_mock.call_args.kwargs["request"]
        self.assertEqual(request.flow_name, "demo")
        self.assertEqual(request.model_override, "gpt-5.4-mini")
        self.assertEqual(request.reasoning_effort_override, "high")

    def test_run_command_passes_from_file_to_runner_as_absolute_path(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with tempfile.TemporaryDirectory() as temp_dir:
            current_dir = Path.cwd()
            issue_path = Path(temp_dir).resolve() / "issue.md"
            issue_path.write_text("Seed issue text.\n", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
                    "rally.cli.run_flow",
                    return_value=SimpleNamespace(message="Run `DMO-4` created."),
                ) as run_flow_mock:
                    with redirect_stdout(stdout):
                        exit_code = main(["run", "demo", "--from-file", "./issue.md"])
            finally:
                os.chdir(current_dir)

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-4` created.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].issue_seed_path, issue_path)

    def test_run_command_rejects_removed_brief_flag(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["run", "demo", "--brief-file", "brief.md"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--brief-file", stderr.getvalue())

    def test_run_command_rejects_removed_preflight_flag(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["run", "demo", "--preflight-only"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--preflight-only", stderr.getvalue())

    def test_resume_command_passes_edit_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.resume_run",
            return_value=SimpleNamespace(message="Run `DMO-1` resumed."),
        ) as resume_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["resume", "DMO-1", "--edit"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-1` resumed.", stdout.getvalue())
        self.assertEqual(resume_run_mock.call_args.kwargs["request"].run_id, "DMO-1")
        self.assertTrue(resume_run_mock.call_args.kwargs["request"].edit_issue)
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].restart)
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].step)

    def test_resume_command_passes_restart_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.resume_run",
            return_value=SimpleNamespace(message="Run `DMO-2` restarted."),
        ) as resume_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["resume", "DMO-1", "--restart"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-2` restarted.", stdout.getvalue())
        self.assertEqual(resume_run_mock.call_args.kwargs["request"].run_id, "DMO-1")
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].edit_issue)
        self.assertTrue(resume_run_mock.call_args.kwargs["request"].restart)
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].step)

    def test_resume_command_passes_step_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.resume_run",
            return_value=SimpleNamespace(message="Run `DMO-1` paused."),
        ) as resume_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["resume", "DMO-1", "--step"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-1` paused.", stdout.getvalue())
        self.assertEqual(resume_run_mock.call_args.kwargs["request"].run_id, "DMO-1")
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].edit_issue)
        self.assertFalse(resume_run_mock.call_args.kwargs["request"].restart)
        self.assertTrue(resume_run_mock.call_args.kwargs["request"].step)

    def test_resume_command_passes_model_and_thinking_overrides_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.resume_run",
            return_value=SimpleNamespace(message="Run `DMO-1` resumed."),
        ) as resume_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["resume", "DMO-1", "--model", "sonnet", "--thinking", "low"])

        self.assertEqual(exit_code, 0)
        request = resume_run_mock.call_args.kwargs["request"]
        self.assertEqual(request.run_id, "DMO-1")
        self.assertEqual(request.model_override, "sonnet")
        self.assertEqual(request.reasoning_effort_override, "low")

    def test_resume_command_rejects_edit_and_restart_together(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["resume", "DMO-1", "--edit", "--restart"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--restart", stderr.getvalue())

    def test_status_command_lists_active_runs_without_run_id(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.show_status",
            return_value=SimpleNamespace(message="Active runs:\n- `DMO-1`"),
        ) as show_status_mock:
            with redirect_stdout(stdout):
                exit_code = main(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Active runs:", stdout.getvalue())
        self.assertEqual(show_status_mock.call_args.kwargs["repo_root"], workspace.workspace_root)
        self.assertIsNone(show_status_mock.call_args.kwargs["run_id"])

    def test_status_command_reads_one_run(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.show_status",
            return_value=SimpleNamespace(message="Run `DMO-1`\nStatus: `paused`"),
        ) as show_status_mock:
            with redirect_stdout(stdout):
                exit_code = main(["status", "DMO-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Status: `paused`", stdout.getvalue())
        self.assertEqual(show_status_mock.call_args.kwargs["repo_root"], workspace.workspace_root)
        self.assertEqual(show_status_mock.call_args.kwargs["run_id"], "DMO-1")

    def test_run_command_passes_detach_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-3` detached."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo", "--detach"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(run_flow_mock.call_args.kwargs["request"].detach)

    def test_resume_command_passes_detach_flag_to_runner(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.resume_run",
            return_value=SimpleNamespace(message="Run `DMO-3` detached."),
        ) as resume_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["resume", "DMO-3", "--detach"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(resume_run_mock.call_args.kwargs["request"].detach)

    def test_stop_command_defaults_to_cooperative_request(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.request_stop",
            return_value=SimpleNamespace(message="Requested cooperative stop for run `DMO-1`."),
        ) as request_stop_mock, patch(
            "rally.cli.kill_run",
        ) as kill_run_mock:
            with redirect_stdout(stdout):
                exit_code = main(["stop", "DMO-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("cooperative stop", stdout.getvalue())
        self.assertEqual(request_stop_mock.call_args.kwargs["run_id"], "DMO-1")
        self.assertEqual(
            request_stop_mock.call_args.kwargs["repo_root"], workspace.workspace_root
        )
        kill_run_mock.assert_not_called()

    def test_stop_command_now_flag_hard_stops_with_grace(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.kill_run",
            return_value=SimpleNamespace(message="Run `DMO-1` received SIGTERM and exited."),
        ) as kill_run_mock, patch("rally.cli.request_stop") as request_stop_mock:
            with redirect_stdout(stdout):
                exit_code = main(["stop", "DMO-1", "--now", "--grace", "3"])

        self.assertEqual(exit_code, 0)
        self.assertIn("SIGTERM", stdout.getvalue())
        self.assertEqual(kill_run_mock.call_args.kwargs["run_id"], "DMO-1")
        self.assertEqual(kill_run_mock.call_args.kwargs["grace_seconds"], 3.0)
        request_stop_mock.assert_not_called()

    def test_stop_command_unknown_run_surfaces_usage_error(self) -> None:
        from rally.errors import RallyUsageError

        stderr = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.request_stop",
            side_effect=RallyUsageError("Run `XYZ-9` does not exist."),
        ):
            with redirect_stderr(stderr):
                exit_code = main(["stop", "XYZ-9"])

        self.assertNotEqual(exit_code, 0)
        self.assertIn("XYZ-9", stderr.getvalue())

    def test_workspace_sync_command_is_removed(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["workspace", "sync"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_issue_current_prints_bounded_current_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            issue_file.write_text(
                textwrap.dedent(
                    """\
                    # Brief

                    Fix the pagination bug.

                    ---

                    ## Rally Note
                    - Run ID: `FLW-1`
                    - Source: `rally issue note`

                    ### Note
                    - latest context
                    """
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)):
                with redirect_stdout(stdout):
                    exit_code = main(["issue", "current", "--run-id", "FLW-1"])

            # The shared read path should show the live request and newest note
            # without making the caller reread the full append-only ledger.
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Rally Issue Current View", rendered)
            self.assertIn("## Opening Issue", rendered)
            self.assertIn("Fix the pagination bug.", rendered)
            self.assertIn("## Latest Rally Note", rendered)
            self.assertIn("latest context", rendered)
            self.assertIn("## Full Ledger", rendered)

    def test_issue_note_reads_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            stdout = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), patch(
                "sys.stdin", io.StringIO("### Note\n- stdin path\n")
            ):
                with redirect_stdout(stdout):
                    exit_code = main(["issue", "note", "--run-id", "FLW-1"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Appended note for run `FLW-1`", stdout.getvalue())
            self.assertIn("stdin path", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_reads_inline_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "Short note"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Short note", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_adds_structured_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)):
                exit_code = main(
                    [
                        "issue",
                        "note",
                        "--run-id",
                        "FLW-1",
                        "--field",
                        "kind=producer_handoff",
                        "--field",
                        "lane=producer",
                        "--text",
                        "Short note",
                    ]
                )

            self.assertEqual(exit_code, 0)
            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertIn("- Field kind: `producer_handoff`", issue_text)
            self.assertIn("- Field lane: `producer`", issue_text)

    def test_issue_note_uses_turn_number_from_env_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), patch.dict(
                os.environ,
                {"RALLY_TURN_NUMBER": "4"},
                clear=False,
            ):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "Short note"])

            self.assertEqual(exit_code, 0)
            self.assertIn("- Turn: `4`", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_omits_turn_line_without_turn_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), patch.dict(
                os.environ,
                {},
                clear=True,
            ):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "Short note"])

            self.assertEqual(exit_code, 0)
            self.assertNotIn("- Turn:", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_rejects_invalid_turn_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")
            stderr = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), patch.dict(
                os.environ,
                {"RALLY_TURN_NUMBER": "not-a-number"},
                clear=False,
            ), redirect_stderr(stderr):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "Short note"])

            self.assertEqual(exit_code, 2)
            self.assertIn("`RALLY_TURN_NUMBER` must be an integer", stderr.getvalue())

    def test_issue_note_rejects_malformed_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")
            stderr = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "issue",
                        "note",
                        "--run-id",
                        "FLW-1",
                        "--field",
                        "kind",
                        "--text",
                        "Short note",
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("Note fields must use `key=value`.", stderr.getvalue())

    def test_issue_note_reads_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            note_file = repo_root / "note.md"
            note_file.write_text("### Note\n- file path\n", encoding="utf-8")

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)):
                exit_code = main(
                    ["issue", "note", "--run-id", "FLW-1", "--file", str(note_file)]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("file path", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_reports_bad_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")
            stderr = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), redirect_stderr(stderr):
                exit_code = main(["issue", "note", "--run-id", "FLW-9", "--text", "Short note"])

            self.assertEqual(exit_code, 2)
            self.assertIn("Run file does not exist", stderr.getvalue())

    def test_issue_note_rejects_empty_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")
            stderr = io.StringIO()

            with patch("rally.cli.resolve_workspace", return_value=self._workspace(repo_root)), redirect_stderr(stderr):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "   "])

            self.assertEqual(exit_code, 2)
            self.assertIn("Note body is empty", stderr.getvalue())

    def _write_run(self, *, repo_root: Path, run_id: str) -> Path:
        run_dir = repo_root / "runs" / run_id
        home_dir = run_dir / "home"
        history_dir = run_dir / "issue_history"
        home_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        issue_path = home_dir / "issue.md"
        issue_path.write_text("# Brief\n", encoding="utf-8")
        (run_dir / "run.yaml").write_text(
            textwrap.dedent(
                f"""\
                id: {run_id}
                issue_file: home/issue.md
                """
            ),
            encoding="utf-8",
        )
        return issue_path

    def _workspace(self, repo_root: Path):
        return workspace_context_from_root(
            repo_root,
            cli_bin=repo_root / "bin" / "rally",
        )


if __name__ == "__main__":
    unittest.main()
