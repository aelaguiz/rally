from __future__ import annotations

import tempfile
import textwrap
import unittest
from datetime import UTC, datetime
from pathlib import Path

from rally.errors import RallyStateError
from rally.services.issue_ledger import (
    ORIGINAL_ISSUE_END_MARKER,
    append_issue_edit_diff,
    append_issue_note,
    extract_original_issue_text,
    load_original_issue_text,
)


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
            self.assertIn(
                f"Original operator brief.\n\n{ORIGINAL_ISSUE_END_MARKER}\n\n---\n\n## Rally Note",
                issue_text,
            )
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

    def test_append_issue_note_adds_turn_line_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- keep this context",
                turn_index=3,
                now=datetime(2026, 4, 13, 19, 31, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertIn("- Turn: `3`", issue_text)

    def test_append_issue_note_renders_structured_fields_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- keep this context",
                note_fields=(
                    ("kind", "producer_handoff"),
                    ("lane", "producer"),
                    ("artifact", "section_plan"),
                ),
                now=datetime(2026, 4, 13, 19, 31, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertIn("- Field kind: `producer_handoff`", issue_text)
            self.assertIn("- Field lane: `producer`", issue_text)
            self.assertIn("- Field artifact: `section_plan`", issue_text)
            self.assertLess(
                issue_text.index("- Field kind: `producer_handoff`"),
                issue_text.index("- Field lane: `producer`"),
            )
            self.assertLess(
                issue_text.index("- Field lane: `producer`"),
                issue_text.index("- Field artifact: `section_plan`"),
            )

    def test_append_issue_note_uses_one_divider_between_each_rally_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- first",
                now=datetime(2026, 4, 13, 19, 30, tzinfo=UTC),
            )
            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- second",
                now=datetime(2026, 4, 13, 19, 31, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertEqual(issue_text.count("\n---\n\n## Rally Note\n"), 2)

    def test_append_issue_note_does_not_add_leading_divider_to_empty_issue_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            issue_file.write_text("", encoding="utf-8")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- first",
                now=datetime(2026, 4, 13, 19, 30, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertTrue(issue_text.startswith("## Rally Note\n"))
            self.assertFalse(issue_text.startswith("---"))

    def test_append_issue_note_rejects_non_positive_turn_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")

            with self.assertRaisesRegex(RallyStateError, "Turn index must be 1 or greater"):
                append_issue_note(
                    repo_root=repo_root,
                    run_id="FLW-1",
                    note_markdown="### Note\n- invalid turn",
                    turn_index=0,
                )

    def test_append_issue_note_rejects_duplicate_structured_field_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")

            with self.assertRaisesRegex(RallyStateError, "Note field `kind` is duplicated"):
                append_issue_note(
                    repo_root=repo_root,
                    run_id="FLW-1",
                    note_markdown="### Note\n- invalid fields",
                    note_fields=(("kind", "first"), ("kind", "second")),
                )

    def test_append_issue_note_rejects_invalid_structured_field_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="FLW-1")

            with self.assertRaisesRegex(RallyStateError, "Note field keys must match"):
                append_issue_note(
                    repo_root=repo_root,
                    run_id="FLW-1",
                    note_markdown="### Note\n- invalid fields",
                    note_fields=(("Bad-Key", "producer"),),
                )

    def test_append_issue_note_inserts_hidden_original_issue_marker_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")

            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- first",
                now=datetime(2026, 4, 13, 19, 30, tzinfo=UTC),
            )
            append_issue_note(
                repo_root=repo_root,
                run_id="FLW-1",
                note_markdown="### Note\n- second",
                now=datetime(2026, 4, 13, 19, 31, tzinfo=UTC),
            )

            issue_text = issue_file.read_text(encoding="utf-8")
            self.assertEqual(issue_text.count(ORIGINAL_ISSUE_END_MARKER), 1)

    def test_extract_original_issue_text_uses_hidden_marker_when_present(self) -> None:
        issue_text = textwrap.dedent(
            f"""\
            # Brief

            Original operator brief.

            {ORIGINAL_ISSUE_END_MARKER}

            ---

            ## Rally Run Started
            - Run ID: `FLW-1`
            """
        )

        self.assertEqual(
            extract_original_issue_text(issue_text),
            "# Brief\n\nOriginal operator brief.\n",
        )

    def test_extract_original_issue_text_falls_back_to_legacy_rally_block_boundary(self) -> None:
        issue_text = textwrap.dedent(
            """\
            # Brief

            Original operator brief.

            ---

            ## Rally Run Started
            - Run ID: `FLW-1`
            """
        )

        self.assertEqual(
            extract_original_issue_text(issue_text),
            "# Brief\n\nOriginal operator brief.\n",
        )

    def test_load_original_issue_text_prefers_earliest_snapshot_over_live_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            issue_file = self._write_run(repo_root=repo_root, run_id="FLW-1")
            history_dir = issue_file.parent.parent / "issue_history"
            (history_dir / "20260413T193000000000Z-issue.md").write_text(
                "# Brief\n\nOriginal operator brief.\n",
                encoding="utf-8",
            )
            issue_file.write_text(
                textwrap.dedent(
                    f"""\
                    # Brief

                    Updated operator brief.

                    {ORIGINAL_ISSUE_END_MARKER}

                    ---

                    ## user edited issue.md
                    - Run ID: `FLW-1`
                    """
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                load_original_issue_text(repo_root=repo_root, run_id="FLW-1"),
                "# Brief\n\nOriginal operator brief.\n",
            )

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
            self.assertIn("\n---\n\n## user edited issue.md", issue_text)
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
