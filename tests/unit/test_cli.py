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

from rally.domain.memory import MemoryEntry, MemoryRefreshResult, MemorySaveResult, MemoryScope, MemorySearchHit
from rally.cli import main
from rally.services.workspace import workspace_context_from_root


class CliTests(unittest.TestCase):
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

    def test_memory_search_prints_hits(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.search_memory",
            return_value=(
                MemorySearchHit(
                    memory_id="mem_flw_scope_lead_focus_the_fix",
                    path=Path("/tmp/repo/runs/memory/entries/FLW/scope_lead/mem_flw_scope_lead_focus_the_fix.md"),
                    title="Focus the fix",
                    snippet="Fix the concrete bug before widening scope.",
                    score=0.83,
                ),
            ),
        ) as search_memory_mock:
            with redirect_stdout(stdout):
                exit_code = main(["memory", "search", "--run-id", "FLW-1", "--query", "focus the fix"])

        self.assertEqual(exit_code, 0)
        self.assertIn("mem_flw_scope_lead_focus_the_fix", stdout.getvalue())
        self.assertEqual(search_memory_mock.call_args.kwargs["run_id"], "FLW-1")

    def test_memory_use_prints_memory_body(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.use_memory",
            return_value=self._memory_entry(Path("/tmp/repo")),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "use", "--run-id", "FLW-1", "mem_flw_scope_lead_focus_the_fix"])

        self.assertEqual(exit_code, 0)
        self.assertIn("# Lesson", stdout.getvalue())
        self.assertIn("Focus the fix before widening scope.", stdout.getvalue())

    def test_memory_save_reads_stdin_and_reports_outcome(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))
        save_result = MemorySaveResult(outcome="created", entry=self._memory_entry(Path("/tmp/repo")))
        refresh_result = MemoryRefreshResult(
            collections=1,
            indexed=1,
            updated=0,
            unchanged=0,
            removed=0,
            needs_embedding=0,
            docs_processed=0,
            chunks_embedded=0,
            embed_errors=0,
        )

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.save_memory",
            return_value=(save_result, refresh_result),
        ) as save_memory_mock, patch("sys.stdin", io.StringIO(self._memory_body())):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "save", "--run-id", "FLW-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created memory", stdout.getvalue())
        self.assertIn("mem_flw_scope_lead_focus_the_fix", stdout.getvalue())
        self.assertEqual(save_memory_mock.call_args.kwargs["run_id"], "FLW-1")

    def test_memory_refresh_reports_counts(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.refresh_memory",
            return_value=MemoryRefreshResult(
                collections=1,
                indexed=1,
                updated=2,
                unchanged=3,
                removed=0,
                needs_embedding=0,
                docs_processed=5,
                chunks_embedded=7,
                embed_errors=0,
            ),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "refresh", "--run-id", "FLW-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Refreshed scoped memory index.", stdout.getvalue())
        self.assertIn("1 new, 2 updated, 3 unchanged, 0 removed", stdout.getvalue())

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
            framework_root=Path(__file__).resolve().parents[2],
        )

    def _memory_entry(self, repo_root: Path) -> MemoryEntry:
        return MemoryEntry(
            memory_id="mem_flw_scope_lead_focus_the_fix",
            scope=MemoryScope(flow_code="FLW", agent_slug="scope_lead"),
            source_run_id="FLW-1",
            created_at="2026-04-13T20:00:00Z",
            updated_at="2026-04-13T20:05:00Z",
            lesson="Focus the fix before widening scope.",
            when_this_matters="Use this when the first bug is still not fixed.",
            what_to_do="Fix the concrete bug, then widen only if proof shows a second issue.",
            path=repo_root / "runs" / "memory" / "entries" / "FLW" / "scope_lead" / "mem_flw_scope_lead_focus_the_fix.md",
        )

    def _memory_body(self) -> str:
        return textwrap.dedent(
            """\
            # Lesson
            Focus the fix before widening scope.

            # When This Matters
            Use this when the first bug is still not fixed.

            # What To Do
            Fix the concrete bug, then widen only if proof shows a second issue.
            """
        )


if __name__ == "__main__":
    unittest.main()
