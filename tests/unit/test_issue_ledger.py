from __future__ import annotations

import tempfile
import textwrap
import unittest
from datetime import UTC, datetime
from pathlib import Path

from rally.errors import RallyStateError
from rally.services.issue_ledger import append_issue_edit_diff, append_issue_note


class IssueLedgerTests(unittest.TestCase):
    def test_append_issue_note_updates_issue_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            result = append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- parser fix landed\n",
                now=datetime(2026, 4, 13, 19, 30, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertEqual(result.issue_file, issue_file)
            self.assertTrue(result.snapshot_file.is_file())
            self.assertIn("## Rally Note", issue_text)
            self.assertIn("- Run ID: `FLW-1`", issue_text)
            self.assertIn("- Time: `2026-04-13T19:30:00Z`", issue_text)
            self.assertIn("### Note\n- parser fix landed\n", issue_text)
            self.assertEqual(result.snapshot_file.read_text(encoding="utf-8"), issue_text)

    def test_append_issue_note_rejects_missing_run_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            with self.assertRaisesRegex(RallyStateError, "Run file does not exist"):
                append_issue_note(repo_root=repo_root, run_id="FLW-1", note_markdown="### Note\n- hi")

    def test_append_issue_note_rejects_mismatched_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_dir = repo_root / "runs" / "FLW-1"
            home_dir = run_dir / "home"
            history_dir = run_dir / "issue_history"
            home_dir.mkdir(parents=True)
            history_dir.mkdir(parents=True)
            (home_dir / "issue.md").write_text("# Brief\n", encoding="utf-8")
            (run_dir / "run.yaml").write_text("id: FLW-2\nissue_file: home/issue.md\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyStateError, "has id `FLW-2`, not requested run `FLW-1`"):
                append_issue_note(repo_root=repo_root, run_id="FLW-1", note_markdown="### Note\n- hi")

    def test_append_issue_note_rejects_wrong_issue_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1", issue_file="elsewhere.md")

            with self.assertRaisesRegex(RallyStateError, "Rally only writes"):
                append_issue_note(repo_root=repo_root, run_id="FLW-1", note_markdown="### Note\n- hi")

    def test_append_issue_note_rejects_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_dir = repo_root / "runs" / "FLW-1"
            home_dir = run_dir / "home"
            history_dir = run_dir / "issue_history"
            home_dir.mkdir(parents=True)
            history_dir.mkdir(parents=True)
            (home_dir / "issue.md").write_text("# Brief\n", encoding="utf-8")
            (run_dir / "run.yaml").write_text("id: [\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyStateError, "is not valid YAML"):
                append_issue_note(repo_root=repo_root, run_id="FLW-1", note_markdown="### Note\n- hi")

    def test_append_issue_note_rejects_missing_issue_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_dir = repo_root / "runs" / "FLW-1"
            history_dir = run_dir / "issue_history"
            history_dir.mkdir(parents=True)
            (run_dir / "run.yaml").write_text("id: FLW-1\nissue_file: home/issue.md\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyStateError, "Issue log does not exist"):
                append_issue_note(repo_root=repo_root, run_id="FLW-1", note_markdown="### Note\n- hi")

    def test_append_issue_note_strips_only_outer_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="\n\n### Note\n- keep this line\n\n",
                now=datetime(2026, 4, 13, 19, 30, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertIn("### Note\n- keep this line\n", issue_text)

    def test_append_issue_edit_diff_appends_formatted_diff_block_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            result = append_issue_edit_diff(
                repo_root=repo_root,
                run_id="FLW-1",
                before_text="# Brief\n\nOriginal operator brief.\n",
                after_text="# Brief\n\nUpdated operator brief.\n",
                now=datetime(2026, 4, 13, 20, 15, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertEqual(result.issue_file, issue_file)
            self.assertTrue(result.snapshot_file.is_file())
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("- Source: `rally resume --edit`", issue_text)
            self.assertIn("```diff\n--- before/issue.md\n+++ after/issue.md\n", issue_text)
            self.assertIn("-Original operator brief.\n+Updated operator brief.\n", issue_text)
            self.assertEqual(result.snapshot_file.read_text(encoding="utf-8"), issue_text)

    def test_append_issue_edit_diff_rejects_noop_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")

            with self.assertRaisesRegex(RallyStateError, "requires changed text"):
                append_issue_edit_diff(
                    repo_root=repo_root,
                    run_id="FLW-1",
                    before_text="Same text.\n",
                    after_text="Same text.\n",
                )

    def _write_run(
        self,
        *,
        repo_root: Path,
        run_id: str,
        issue_file: str = "home/issue.md",
    ) -> Path:
        run_dir = repo_root / "runs" / run_id
        home_dir = run_dir / "home"
        history_dir = run_dir / "issue_history"
        home_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        issue_path = home_dir / "issue.md"
        issue_path.write_text("# Brief\n\nOriginal operator brief.\n", encoding="utf-8")
        (run_dir / "run.yaml").write_text(
            textwrap.dedent(
                f"""\
                id: {run_id}
                issue_file: {issue_file}
                """
            ),
            encoding="utf-8",
        )
        return issue_path


if __name__ == "__main__":
    unittest.main()
