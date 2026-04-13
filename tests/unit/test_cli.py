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


class CliTests(unittest.TestCase):
    def test_run_command_calls_runner_without_external_brief_flag(self) -> None:
        stdout = io.StringIO()

        with patch("rally.cli._repo_root", return_value=Path("/tmp/repo")), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-1` created."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-1` created.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertFalse(run_flow_mock.call_args.kwargs["request"].start_new)

    def test_run_command_passes_new_flag_to_runner(self) -> None:
        stdout = io.StringIO()

        with patch("rally.cli._repo_root", return_value=Path("/tmp/repo")), patch(
            "rally.cli.run_flow",
            return_value=SimpleNamespace(message="Run `DMO-2` created."),
        ) as run_flow_mock:
            with redirect_stdout(stdout):
                exit_code = main(["run", "demo", "--new"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Run `DMO-2` created.", stdout.getvalue())
        self.assertEqual(run_flow_mock.call_args.kwargs["request"].flow_name, "demo")
        self.assertTrue(run_flow_mock.call_args.kwargs["request"].start_new)

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

        with patch("rally.cli._repo_root", return_value=Path("/tmp/repo")), patch(
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

    def test_resume_command_passes_restart_flag_to_runner(self) -> None:
        stdout = io.StringIO()

        with patch("rally.cli._repo_root", return_value=Path("/tmp/repo")), patch(
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

    def test_resume_command_rejects_edit_and_restart_together(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["resume", "DMO-1", "--edit", "--restart"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--restart", stderr.getvalue())

    def test_issue_note_reads_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            stdout = io.StringIO()

            with patch("rally.cli._repo_root", return_value=repo_root), patch(
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

            with patch("rally.cli._repo_root", return_value=repo_root):
                exit_code = main(["issue", "note", "--run-id", "FLW-1", "--text", "Short note"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Short note", issue_file.read_text(encoding="utf-8"))

    def test_issue_note_adds_structured_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            with patch("rally.cli._repo_root", return_value=repo_root):
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

            with patch("rally.cli._repo_root", return_value=repo_root), patch.dict(
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

            with patch("rally.cli._repo_root", return_value=repo_root), patch.dict(
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

            with patch("rally.cli._repo_root", return_value=repo_root), patch.dict(
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

            with patch("rally.cli._repo_root", return_value=repo_root), redirect_stderr(stderr):
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

            with patch("rally.cli._repo_root", return_value=repo_root):
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

            with patch("rally.cli._repo_root", return_value=repo_root), redirect_stderr(stderr):
                exit_code = main(["issue", "note", "--run-id", "FLW-9", "--text", "Short note"])

            self.assertEqual(exit_code, 2)
            self.assertIn("Run file does not exist", stderr.getvalue())

    def test_issue_note_rejects_empty_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")
            stderr = io.StringIO()

            with patch("rally.cli._repo_root", return_value=repo_root), redirect_stderr(stderr):
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


if __name__ == "__main__":
    unittest.main()
