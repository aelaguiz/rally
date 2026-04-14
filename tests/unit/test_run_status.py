from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.errors import RallyUsageError
from rally.services.run_status import show_status


class RunStatusTests(unittest.TestCase):
    def test_show_status_without_active_runs_suggests_starting_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            result = show_status(repo_root=repo_root)

            self.assertEqual(
                result.message,
                "No active runs.\nNext: start one with `rally run <flow>`.",
            )

    def test_show_status_lists_active_runs_with_next_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(
                repo_root=repo_root,
                run_id="DMO-1",
                flow_name="demo",
                flow_code="DMO",
                status="paused",
                current_agent_key="02_change_engineer",
                turn_index=1,
            )
            self._write_run(
                repo_root=repo_root,
                run_id="POM-2",
                flow_name="poem_loop",
                flow_code="POM",
                status="blocked",
                current_agent_key="01_poem_writer",
                turn_index=3,
                blocker_reason="Need the poem type.",
            )

            result = show_status(repo_root=repo_root)

            self.assertIn("Active runs:", result.message)
            self.assertIn("`DMO-1` flow `demo` status `paused` turn `1` agent `02_change_engineer`", result.message)
            self.assertIn("Next: `rally resume DMO-1` or `rally resume DMO-1 --step`", result.message)
            self.assertIn("`POM-2` flow `poem_loop` status `blocked` turn `3` agent `01_poem_writer`", result.message)
            self.assertIn("Next: `rally resume POM-2 --edit` or `rally resume POM-2 --restart`", result.message)

    def test_show_status_for_active_blocked_run_includes_reason_and_issue_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(
                repo_root=repo_root,
                run_id="DMO-1",
                flow_name="demo",
                flow_code="DMO",
                status="blocked",
                current_agent_key="02_change_engineer",
                turn_index=4,
                blocker_reason="Guarded repo is dirty.",
                last_turn_kind="handoff",
            )

            result = show_status(repo_root=repo_root, run_id="DMO-1")

            self.assertIn("Run `DMO-1`", result.message)
            self.assertIn("Storage: `active`", result.message)
            self.assertIn("Status: `blocked`", result.message)
            self.assertIn("Current Agent: `02_change_engineer`", result.message)
            self.assertIn("Issue File: `runs/active/DMO-1/home/issue.md`", result.message)
            self.assertIn("Last Result: `handoff`", result.message)
            self.assertIn("Blocker: Guarded repo is dirty.", result.message)
            self.assertIn("Next: `rally resume DMO-1 --edit` or `rally resume DMO-1 --restart`", result.message)

    def test_show_status_for_archived_run_marks_it_archived(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(
                repo_root=repo_root,
                run_id="DMO-1",
                flow_name="demo",
                flow_code="DMO",
                status="done",
                current_agent_key=None,
                turn_index=5,
                done_summary="Shipped the fix.",
                archived=True,
            )

            result = show_status(repo_root=repo_root, run_id="DMO-1")

            self.assertIn("Storage: `archive`", result.message)
            self.assertIn("Status: `done`", result.message)
            self.assertIn("Summary: Shipped the fix.", result.message)
            self.assertIn(
                "Next: archived runs do not resume; inspect `runs/archive/DMO-1/home/issue.md`",
                result.message,
            )

    def test_show_status_rejects_unknown_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            with self.assertRaisesRegex(RallyUsageError, "Use `rally status` to list active runs"):
                show_status(repo_root=repo_root, run_id="DMO-9")

    def _write_run(
        self,
        *,
        repo_root: Path,
        run_id: str,
        flow_name: str,
        flow_code: str,
        status: str,
        current_agent_key: str | None,
        turn_index: int,
        blocker_reason: str | None = None,
        done_summary: str | None = None,
        last_turn_kind: str | None = None,
        archived: bool = False,
    ) -> None:
        parent = repo_root / "runs" / ("archive" if archived else "active") / run_id
        home_dir = parent / "home"
        home_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / "issue.md").write_text("# Issue\n", encoding="utf-8")
        (parent / "run.yaml").write_text(
            textwrap.dedent(
                f"""\
                id: {run_id}
                flow_name: {flow_name}
                flow_code: {flow_code}
                adapter_name: codex
                start_agent_key: 01_scope_lead
                created_at: "2026-04-14T00:00:00Z"
                issue_file: home/issue.md
                """
            ),
            encoding="utf-8",
        )
        current_agent_yaml = "null" if current_agent_key is None else current_agent_key
        current_agent_slug_yaml = "null" if current_agent_key is None else current_agent_key.lower()
        blocker_yaml = "null" if blocker_reason is None else blocker_reason
        done_yaml = "null" if done_summary is None else done_summary
        last_turn_yaml = "null" if last_turn_kind is None else last_turn_kind
        (parent / "state.yaml").write_text(
            textwrap.dedent(
                f"""\
                status: {status}
                current_agent_key: {current_agent_yaml}
                current_agent_slug: {current_agent_slug_yaml}
                turn_index: {turn_index}
                updated_at: "2026-04-14T01:00:00Z"
                last_turn_kind: {last_turn_yaml}
                blocker_reason: {blocker_yaml}
                done_summary: {done_yaml}
                """
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
